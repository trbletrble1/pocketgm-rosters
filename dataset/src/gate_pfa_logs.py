"""Gate: what the PFA log ingest must not do.

FIVE PROPERTIES, held on the STORES rather than on the run that made them, so a
hand-edited store fails too.

  L1  A BLANK IS NOT A ZERO. No statistic value is the empty string, and no column
      appears both in `statistics` and in `columns_printed_blank`. TAR is blank in
      every receiving row to 1989 and X2/X2A in every 1980s scoring row; reading those
      as zeros would put 16,187 invented figures into the 1970s alone. AND THE ERA
      FACTS ARE NOT MONOTONIC, measured 2026-09-10 across all 33,747 pages: KICKOFF
      RETURNS.FC is blank on every 1970s row and carries 7,297 values in the 1980s;
      SCORING.X2 is blank in the 1970s and carries 4,173 values in the 1960s, because
      the AFL had the two-point conversion and the NFL did not. So the blank columns
      are recorded PER ROW and never inferred from the decade -- which is what makes
      this property hold on any decade rather than on the one it was written for.
  L2  THE CLUB CODE COMES FROM THE TABLE. Every stint subject's code resolves through
      Clubs() for that year AND THAT LEAGUE -- the season key carries both, and asking
      without the league cannot separate two clubs that share a code. An invented code resolves to nothing and no other gate
      catches it (docs/DATASET_PRECEDENTS.md).
  L3  THE COVERAGE LIMIT REACHES THE READER. Every derived game claim carries the
      note saying the set is assembled from coverage and is not a schedule PFA
      published, ON THE CLAIM -- `note` is served on every claim, a declaration is not.
  L4  ONLY OVERSHOOTS ARE WRITTEN AS DISAGREEMENTS. A sum that falls SHORT of the
      season page is a floor -- PFA's per-game sack rows are partial because sacks
      were not official until 1982 -- and must not be filed as a conflict.
  L6  EVERY CLAIM'S SOURCE_RECORD IS IN THE STORE'S OWN TABLE. RS-G3 holds this across
      the model and it is a STANDING RED at 414, so a rise is easy to publish and hard
      to see: the first run of this ingest named a derived record per game and
      registered none, RS-G3 went 414 -> 2,448, and the build published because the
      two standing reds are forced past. Held here on the store, before any build.
  L5  THE JOIN IS THE PFA CODE. Every claim's source_record names a log page, and the
      person on the subject is the person the archive already binds to that page's
      player page. A name join would not survive this.

  python3 src/gate_pfa_logs.py [--selftest]
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
# THE STORES ARE DISCOVERED, NOT LISTED. They were a hand-written tuple naming the
# 1970s, so the first store of any other decade would have been SILENTLY UNGATED --
# the gate would have passed by not looking. Ruled by the archive's own habit: a gate
# derives its population, it does not carry a copy of it.
def _stores():
    import glob
    out = []
    for pat in ("pfa-postseason-*.json", "pfa-gamelogs-*.json"):
        for f in sorted(glob.glob(os.path.join(BASE, "build", pat))):
            out.append(os.path.basename(f)[:-5])
    return tuple(out)


STORES = _stores()
SCHEDULE_PHRASE = "ASSEMBLED FROM COVERAGE"

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def blanks(claims):
    """-> (values that are empty strings, columns in both statistics and blank)."""
    empty, both = 0, 0
    for c in claims:
        v = c.get("value")
        if not isinstance(v, dict): continue
        st = v.get("statistics") or v.get("columns") or {}
        bl = set(v.get("columns_printed_blank") or ())
        empty += sum(1 for x in st.values() if isinstance(x, str) and not x.strip())
        both += len(set(st) & bl)
    return empty, both


def codes(claims):
    """(code, year, LEAGUE) off every stint subject.

    THE LEAGUE WAS BEING THROWN AWAY. A stint's season key is `NFL-1984` and this read
    the year out of it and dropped the rest, then asked the club table to place `HOU`
    in 1984 with no league -- which it cannot, because the Houston Oilers and a USFL
    club of the same code both existed. The gate then failed the ingest for writing
    exactly the rows it should have written. Two implementations of one rule, and the
    fix went into one of them; this is the other."""
    out = collections.Counter()
    for c in claims:
        s = c.get("subject")
        if isinstance(s, list) and s and s[0] == "stint" and len(s) >= 4:
            key = str(s[3])
            y = re.search(r"(\d{4})", key)
            lg = key.split("-")[0] if "-" in key else None
            if y: out[(str(s[2]), int(y.group(1)), lg)] += 1
    return out


def main(argv):
    if "--selftest" in argv: return selftest()
    from clubs import Clubs
    C = Clubs()
    found = 0
    for name in STORES:
        p = os.path.join(BASE, "build", name + ".json")
        if not os.path.exists(p):
            print(f"  --   {name}: not built yet"); continue
        found += 1
        d = json.load(open(p)); cl = d["claims"]
        print(f"{name}: {len(cl):,} claims")

        empty, both = blanks(cl)
        check(empty == 0 and both == 0,
              f"L1 a blank is not a zero ({empty} empty-string values, {both} columns in both lists)")

        bad = [k for k in codes(cl) if not C.resolve(k[0], k[1], k[2], source="season_key")]
        check(not bad, f"L2 every club code resolves through the club table"
              + ("" if not bad else f" -- {len(bad)} do not: {bad[:5]}"))

        derived = [c for c in cl if c.get("predicate") == "pfa.game_as_logged"]
        missing = [c for c in derived if SCHEDULE_PHRASE not in (c.get("note") or "")]
        if derived:
            check(not missing, f"L3 all {len(derived):,} derived game claims carry the coverage "
                               f"limit in `note`" + ("" if not missing else f" -- {len(missing)} do not"))

        conf = [c for c in cl if c.get("predicate") == "pfa.game_logs_exceed_the_season_page"]
        wrong = [c for c in conf
                 if _num(c["value"].get("the_game_logs_sum_to")) is None
                 or _num(c["value"].get("the_season_page_prints")) is None
                 or _num(c["value"]["the_game_logs_sum_to"]) <= _num(c["value"]["the_season_page_prints"])]
        if conf:
            check(not wrong, f"L4 all {len(conf)} disagreements OVERSHOOT the season page"
                  + ("" if not wrong else f" -- {len(wrong)} do not and are floors, not conflicts"))

        import paths
        conn = sqlite3.connect("file:" + paths.READ_MODEL + "?mode=ro", uri=True)
        bound = {}
        for sr, pid in conn.execute(
                "select distinct source_record, person from claim where source_record "
                "like 'pro-football-archives#players/%' and person is not null"):
            m = re.search(r"players/[a-z]/([a-z0-9]+)\.html", sr)
            if m: bound.setdefault(m.group(1), set()).add(pid)
        off = 0; checked = 0
        for c in cl:
            sr = c.get("source_record") or ""
            m = re.search(r"#(?:gamelogs|playoffs)/[a-z]/([a-z0-9]+)\.html$", sr)
            s = c.get("subject")
            if not m or not (isinstance(s, list) and s[0] == "stint"): continue
            checked += 1
            if bound.get(m.group(1)) != {s[1]}: off += 1
        check(off == 0, f"L5 all {checked:,} page-sourced claims sit on the person the archive "
                        f"already binds to that PFA code" + ("" if not off else f" -- {off} do not"))

        table = set(d.get("source_records") or ())
        orphan = collections.Counter(c["source_record"] for c in cl
                                     if c.get("source_record") not in table)
        check(not orphan, f"L6 every claim's source_record is in the store's own table"
              + ("" if not orphan else
                 f" -- {sum(orphan.values()):,} claims name {len(orphan):,} records that are "
                 f"not: {list(orphan)[:3]}. RS-G3 is a standing red at 414 and a rise "
                 f"hides in it."))
    if not found:
        print("  no PFA log store is built; nothing to hold")
    if FAILS:
        print(f"\nPFA LOG GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nPFA LOG GATE: pass"); return 0


def _num(x):
    try: return float(str(x).rstrip("t"))
    except Exception: return None


def selftest():
    """Both answers on fixtures, one per property."""
    ok = True
    cases = [
        ("L1 an empty-string statistic",
         [{"value": {"statistics": {"TAR": ""}, "columns_printed_blank": []}}], True),
        ("L1 a column in both lists",
         [{"value": {"statistics": {"TD": "1"}, "columns_printed_blank": ["TD"]}}], True),
        ("L1 a clean row",
         [{"value": {"statistics": {"TD": "1"}, "columns_printed_blank": ["TAR"]}}], False),
    ]
    for label, cl, want_fail in cases:
        e, b = blanks(cl); failed = bool(e or b); good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    for label, note, want_fail in (
            ("L3 a derived game with no coverage note", "", True),
            ("L3 a derived game carrying it", "ASSEMBLED FROM COVERAGE, NOT A SCHEDULE", False)):
        failed = SCHEDULE_PHRASE not in note; good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    for label, logs, page, want_fail in (
            ("L4 a short sum filed as a disagreement", 2.0, 5.0, True),
            ("L4 a genuine overshoot", 6.0, 4.0, False)):
        failed = logs <= page; good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
