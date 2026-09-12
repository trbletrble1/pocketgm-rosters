"""Gate: the Neft 1920s pass claims only what two readers read alike, cites it, carries its lineage, and keeps its
hands off the merge questions. Ryan, 2026-09-12.

  N0  THE STORE EXISTS AND HOLDS CLAIMS. A gate over nothing passes, which is how gate_pfa printed PASS over an
      empty dict; this one refuses.
  N1  EVERY FACT IS WHAT BOTH READERS READ. For each neft.roster.height / neft.roster.weight claim, the gate finds
      the man's line in BOTH readings (build/neft-readings-1920s/A and /B) by page, club block and printed name,
      and the claimed value must equal each reader's value. For each college claim, the register entry must
      carry that college in both readings. Re-derived here from the readings, never taken from the ingest.
  N2  EVERY CLAIM CITES A PRINTED PAGE AND CARRIES THE LINEAGE NOTE and the two-reader record.
  N3  NO CLAIM LANDS ON A MERGE QUESTION. The ruling's own examples -- the two Lyons, LeJeune and Jean, the two
      Spagnas -- are looked up here BY NAME, not read from the ingest's list.
  N4  EVERY STINT CLAIM STANDS ON THE ROSTER ITS TIER NAMES. Tiers 1-2: the man is held on the club-season, by
      another store. The printed move: he is held on the club the move names, that season. The adjacent season:
      he is held on the same club the season before or after. No other tier is allowed.
  N5  NO COLLEGE CLAIM IS A PRINTED 'none'.

    python3 src/gate_neft_ingest.py [--selftest]
"""
import os, re, sys, json, sqlite3, copy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

# The pass is chosen by --store (default: pass 1). Both reading folders are loaded, because pass 2 joins its 1930-32
# colleges through the 1920-32 register that pass 1's readers read; their page files never collide.
STORE = sys.argv[sys.argv.index("--store") + 1] if "--store" in sys.argv else "neft-early-years-1978-1920s"
PATH = os.path.join(BASE, "build", STORE + ".json")
READING_DIRS = [os.path.join(BASE, "build", d) for d in ("neft-readings-1920s", "neft-readings-1930s")]
NEFT_STORES = "neft-early-years-1978%"   # the base state leaves out EVERY Neft pass, not just this one
MERGE_QUESTIONS = ["Babe Lyon", "George Lyon", "Walt LeJeune", "Walt Jean", "Butch Spagna", "Joe Spagna"]
TIERS = {"exact_full_name_on_the_club_season", "surname_unique_on_the_club_season",
         "named_in_the_printed_move", "the_clubs_adjacent_season"}
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)
    return ok


def clean(s):
    if s is None: return None
    s = str(s).replace("&amp;", "&").replace("’", "'").replace("”", '"').replace("“", '"').replace("''", '"')
    return re.sub(r"\s+", " ", s).strip() or None


def load_readings():
    R = {"A": {}, "B": {}}
    for base in READING_DIRS:
        if base.endswith("1930s") and not STORE.endswith("1930s"): continue
        for r in R:
            d = os.path.join(base, r)
            if not os.path.isdir(d): raise SystemExit(f"MISSING INPUT: {d}")
            for f in os.listdir(d):
                if f.endswith(".json"): R[r][f[:-5]] = json.load(open(os.path.join(d, f)))
    return R


def line_value(R, reader, pdf, club, name, field):
    page = R[reader].get(f"p{pdf}")
    if not page: return "NO PAGE"
    hits = [m for c in page.get("clubs", []) if clean(c["club_as_printed"]) == clean(club)
            for m in c["men"] if clean(m["name_as_printed"]) == clean(name)]
    vals = {clean(m.get(field)) for m in hits}
    return vals.pop() if len(vals) == 1 else ("NO LINE" if not vals else "TWO LINES DIFFER")


def reg_name(s):
    """A register name as READ, not as FILED. One reader kept a remark like '(Also known as Wrinkle Meat)' in the name
    and the other moved it to the note (Stan Powell, Howard Yerges -- the gate's first run). The remark is dropped,
    and a trailing comma; a nickname in parentheses, '(Hawk)', stays. The same rule as the ingest's register key,
    written here on its own so the gate does not borrow the code it checks."""
    s = re.sub(r"\((?:[^)]*\b(?:played|born|also|know|known)\b[^)]*)\)", "", clean(s) or "", flags=re.I)
    return re.sub(r"[,\s]+$", "", re.sub(r"\s+", " ", s)).strip().lower()


def register_has(R, reader, pdf, name, college):
    page = R[reader].get(f"r{pdf}")
    return bool(page) and any(reg_name(e.get("name_as_printed")) == reg_name(name) and e.get("college_cell") == "printed"
                              and clean(college) in [clean(x) for x in (e.get("college_as_printed") or "").split(",")]
                              for e in page.get("entries", []))


def audit(store, R, conn):
    claims = store.get("claims", [])
    check(bool(claims), f"N0 the store holds claims ({len(claims):,})")
    bad1 = []
    for c in claims:
        pdf = int(c["source_record"].rsplit("#p", 1)[1]) + 2 if "#p" in str(c.get("source_record")) else None
        if c["predicate"] in ("neft.roster.height", "neft.roster.weight"):
            ros = next((x for x in claims if x["predicate"] == "neft.roster_as_printed" and x["subject"] == c["subject"]
                        and x["source_record"] == c["source_record"]), None)
            if not ros: bad1.append((c["subject"], "no roster line beside the fact")); continue
            fld = "hgt" if c["predicate"].endswith("height") else "wgt"
            for r in ("A", "B"):
                v = line_value(R, r, pdf, ros["value"]["club_as_printed"], ros["value"]["name_as_printed"], fld)
                if v != clean(c["value"]): bad1.append((ros["value"]["name_as_printed"], fld, r, v, c["value"]))
        elif c["predicate"] == "neft.college_as_printed":
            for r in ("A", "B"):
                if not register_has(R, r, pdf, c.get("_name_as_printed"), c["value"]):
                    bad1.append((c.get("_name_as_printed"), "college", r, c["value"]))
    check(not bad1, f"N1 every height, weight and college is what both readers read ({len(bad1)} not: {bad1[:3]})")
    bad2 = [c.get("source_record") for c in claims
            if not re.search(r"#p\d+$", str(c.get("source_record"))) or not c.get("_lineage")
            or sorted((c.get("_read_by") or {}).get("readers", [])) != ["A", "B"]]
    check(not bad2, f"N2 every claim cites a printed page, carries the lineage and both readers ({len(bad2)} do not)")
    ids = {p for (p,) in conn.execute(f"select id from person where index_name in ({','.join('?' * len(MERGE_QUESTIONS))})",
                                      MERGE_QUESTIONS)}
    bad3 = sorted({c.get("person") for c in claims if c.get("person") in ids})
    check(len(ids) >= 6 and not bad3, f"N3 no claim on the merge questions ({len(ids)} ids found by name; {len(bad3)} touched: {bad3})")
    bad4 = []
    for c in claims:
        if c["predicate"] != "neft.roster_as_printed": continue
        v = c["value"]; pid = c["person"]; tier = v.get("_join_tier"); on = v.get("_joined_on") or {}
        if tier not in TIERS: bad4.append((pid, "tier", tier)); continue
        def held(cid, yr):
            return conn.execute("select 1 from claim where scope='stint' and club_id=? and year=? and person=? "
                                "and store not like ? limit 1", (cid, yr, pid, NEFT_STORES)).fetchone() is not None
        if tier in ("exact_full_name_on_the_club_season", "surname_unique_on_the_club_season"):
            ok = held(on.get("club_id"), on.get("year"))
        elif tier == "named_in_the_printed_move":
            via = on.get("via") or {}
            ok = held(via.get("club_id"), via.get("year")) and not held(on.get("club_id"), on.get("year"))
        else:
            ok = any(held(on.get("club_id"), yy) for yy in (on.get("via") or {}).get("adjacent_years", []))
        if not ok: bad4.append((pid, tier, on))
    check(not bad4, f"N4 every stint claim stands on the roster its tier names ({len(bad4)} do not: {bad4[:3]})")
    bad5 = [c["person"] for c in claims if c["predicate"] == "neft.college_as_printed" and clean(c["value"]).lower() == "none"]
    check(not bad5, f"N5 no college claim is a printed 'none' ({len(bad5)})")
    # N6 -- RULING TWO'S REFUSAL, RECOUNTED HERE. A man placed by a SURNAME on the club his printed move names stands
    # only if that club-season's roster (other stores, not this one) holds exactly one man of the surname.
    bad6 = []
    for c in claims:
        v = c["value"] if isinstance(c.get("value"), dict) else {}
        via = (v.get("_joined_on") or {}).get("via") or {}
        if c["predicate"] != "neft.roster_as_printed" or v.get("_join_tier") != "named_in_the_printed_move" \
                or via.get("basis") != "surname_unique_on_the_club_season": continue
        sur = re.sub(r"[^a-z']", "", (clean(v["name_as_printed"]) or "").split()[-1].lower())
        men = {p for (p,) in conn.execute(
            "select distinct c.person from claim c join person_name n on n.person=c.person where c.scope='stint' "
            "and c.club_id=? and c.year=? and c.store not like ? and lower(n.name) like ?",
            (via.get("club_id"), via.get("year"), NEFT_STORES, f"% {sur}"))}
        if len(men) != 1 or c["person"] not in men: bad6.append((v["name_as_printed"], via.get("club_id"), sorted(men)[:3]))
    check(not bad6, f"N6 every surname placement on the club a move names stands on exactly one man of that surname "
                    f"({len(bad6)} do not: {bad6[:3]})")
    # N7 -- NO NEFT CLAIM IN THE COLLEGE FAMILY. Filed there first, Neft's abbreviations ('Washington & Jeff.', 'Miami-Ohio',
    # 'N.Y.U.') made at least 91 fabricated college contests, because the declared college reading does not fold them.
    fams = json.load(open(os.path.join(BASE, "service", "declarations", "predicate-families.json")))["families"]
    col = set(fams.get("college", {}).get("predicates", []))
    bad7 = sorted({c["predicate"] for c in claims if c["predicate"] in col})
    check(not bad7, f"N7 no Neft claim is filed in the college family until a reading folds Neft's forms ({bad7})")
    # N8 -- NEFT'S COMBINED CLUB IS HELD, NOT PLACED. A roster headed by two clubs (1934 "CINCINNATI REDS -- ST. LOUIS
    # GUNNERS") puts no man on either archive club (Ryan, 2026-09-11). Found before pass 2 wrote a claim: the city
    # fallback had resolved the header as Cincinnati.
    bad8 = sorted({(c["value"] or {}).get("club_as_printed") for c in claims
                   if isinstance(c.get("value"), dict) and re.search(r"\s[—–-]+\s", (c["value"].get("club_as_printed") or ""))})
    check(not bad8, f"N8 no claim sits on a header naming two clubs ({bad8[:2]})")


def main():
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    R = load_readings()
    if not os.path.exists(PATH):
        check(False, f"N0 the store exists ({PATH})")
        print(f"\nGATE FAILED ({len(FAILS)})"); return 1
    store = json.load(open(PATH))
    if "--selftest" in sys.argv:
        print("SELFTEST -- each planted fault must be caught:")
        def planted(name, mutate):
            FAILS.clear(); s = copy.deepcopy(store); mutate(s)
            print(f"-- {name}"); audit(s, R, conn)
            caught = bool(FAILS); print(f"   {'CAUGHT' if caught else 'MISSED'}"); return caught
        def first(s, pred): return next(c for c in s["claims"] if c["predicate"] == pred)
        results = [
            planted("N0 an empty store", lambda s: s.__setitem__("claims", [])),
            planted("N1 a weight one reader did not read", lambda s: first(s, "neft.roster.weight").__setitem__("value", "999")),
            planted("N1 a college neither reader read", lambda s: first(s, "neft.college_as_printed").__setitem__("value", "Nowhere State")),
            planted("N2 a claim without its lineage", lambda s: first(s, "neft.roster_as_printed").pop("_lineage")),
            planted("N3 a claim on Walt Jean", lambda s: first(s, "neft.roster_as_printed").__setitem__(
                "person", next(p for (p,) in conn.execute("select id from person where index_name='Walt Jean'")))),
            planted("N4 a stint joined by an undeclared tier", lambda s: first(s, "neft.roster_as_printed")["value"].__setitem__(
                "_join_tier", "exact_and_unique_in_the_archive")),
            planted("N5 a printed none claimed as a college", lambda s: first(s, "neft.college_as_printed").__setitem__("value", "none")),
            planted("N7 a Neft college filed back in the college family", lambda s: first(s, "neft.college_as_printed").__setitem__(
                "predicate", "college")),
            planted("N8 a line placed from the combined 1934 header", lambda s: first(s, "neft.roster_as_printed")["value"].__setitem__(
                "club_as_printed", "CINCINNATI REDS — ST. LOUIS GUNNERS")),
            # The fault is BUILT, not found: a store may hold no surname placement to spoil (pass 2 holds none), and a
            # selftest that cannot plant its fault proves nothing -- found when this crashed on the pass-2 store.
            planted("N6 a surname move placement on a club holding no man of that surname", lambda s: first(
                s, "neft.roster_as_printed")["value"].update(
                _join_tier="named_in_the_printed_move",
                _joined_on={"club_id": "club-x", "year": 1930,
                            "via": {"club_id": "club-no-such-club", "year": 1930, "basis": "surname_unique_on_the_club_season"}})),
        ]
        FAILS.clear()
        print(f"\nSELFTEST {'PASSED' if all(results) else 'FAILED'}: {sum(results)} of {len(results)} faults caught")
        return 0 if all(results) else 1
    audit(store, R, conn)
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
