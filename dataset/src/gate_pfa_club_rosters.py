"""Gate: what the PFA club-roster ingest must not do. Held on the STORE.

  R1  TIER 2 IS NEVER USED. Every stint claim was placed by an exact name on the
      club-season or by a surname and forename initial ON that club-season. "Exact and
      unique anywhere in the archive" is inadmissible for a club-season placement --
      Andy King, Jim Talbot, the 1934 Cincinnati Reds, and it would be worst here,
      among 1930s and 1940s men with common names.
  R2  NO SECOND CLUB IS CREATED FROM A SECOND NAME. Every club-name claim is scoped to
      the club_season of a club the table already holds, and names the club id it
      belongs to. Charlotte Purols and Charlotte Bantams are one club.
  R3  A TYPO AND AN ALTERNATIVE NAME ARE FILED APART. Every club-name claim carries a
      `kind` from the closed vocabulary and a `_basis` saying how it was decided. An
      edit distance is reported as a shape, never asserted as a correction.
  R4  EVERY CLAIM'S SOURCE_RECORD IS IN THE STORE'S OWN TABLE -- RS-G3 is a standing red
      at 414 and a rise hides inside it.
  R5  NOBODY IS PROMOTED HERE. Every unmatched man is a lead carrying his roster line
      and his no-match evidence.

  python3 src/gate_pfa_club_rosters.py [--selftest]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
STORE = os.path.join(BASE, "build", "pfa-club-rosters.json")
# THREE ADMISSIBLE TIERS, none of them tier 2. The third is a man this ingest raised and
# promote_players promoted: matched on the EXACT printed name on the EXACT club-season
# through the promotion store, which is the lead's own identity and not a name join.
TIERS = ("exact name on the club-season", "surname and forename initial, on the club-season",
         "this ingest's own lead, promoted by promote_players.py",
         # Ryan, 2026-09-11. Not tier 2: a source-native id, and gate_code_identity C1
         # re-derives every one of these from the base state.
         "PFA's own player code, held by exactly one man of that name")
KINDS = ("declared typo", "typo by shape", "set differently", "a second name")
FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def main(argv):
    if "--selftest" in argv: return selftest()
    if not os.path.exists(STORE):
        print("  the store is not built; nothing to hold"); print("\nPFA CLUB ROSTER GATE: pass"); return 0
    d = json.load(open(STORE)); cl = d["claims"]
    print(f"{len(cl):,} claims, {len(d['leads']):,} leads")

    stints = [c for c in cl if c["subject"][0] == "stint"]
    off = [c for c in stints if not str(c.get("_joined_on", "")).startswith(TIERS)
           or "unique in the archive" in str(c.get("_joined_on", ""))]
    check(not off, f"R1 all {len(stints):,} stint claims used tier 1 or tier 3, never tier 2"
          + ("" if not off else f" -- {len(off)} did not: {sorted({c.get('_joined_on') for c in off})[:3]}"))

    T = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    ids = {c["id"] for c in T["clubs"]}
    nm = [c for c in cl if c["predicate"] == "pfa.club_name_as_printed"]
    bad = [c for c in nm if c["subject"][0] != "club_season" or c["subject"][1] not in ids]
    check(not bad, f"R2 all {len(nm)} club-name claims sit on a club the table already holds"
          + ("" if not bad else f" -- {len(bad)} do not"))
    made = [c for c in T["clubs"] if (c.get("_document") or {}).get("source_id") == "pfa-club-rosters"]
    check(not made, f"R2 no club was created by this ingest"
          + ("" if not made else f" -- {len(made)} were"))

    nokind = [c for c in nm if not any(c["value"].get("kind", "").startswith(k) for k in KINDS)
              or not c["value"].get("_basis")]
    check(not nokind, f"R3 every club-name claim carries a kind from the vocabulary and a basis"
          + ("" if not nokind else f" -- {len(nokind)} do not"))

    table = set(d.get("source_records") or ())
    orphan = collections.Counter(c["source_record"] for c in cl if c.get("source_record") not in table)
    check(not orphan, f"R4 every claim's source_record is in the store's own table"
          + ("" if not orphan else f" -- {sum(orphan.values()):,} name {len(orphan):,} that are not"))

    noev = [L for L in d["leads"] if not L.get("no_archive_match_evidence") or not L.get("roster_line")]
    check(not noev, f"R5 all {len(d['leads']):,} leads carry a roster line and no-match evidence"
          + ("" if not noev else f" -- {len(noev)} do not"))
    promoted = [c for c in cl if c.get("_promoted")]
    check(not promoted, "R5 nobody is promoted in this ingest")

    if FAILS:
        print(f"\nPFA CLUB ROSTER GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nPFA CLUB ROSTER GATE: pass"); return 0


def selftest():
    ok = True
    for label, c, want_fail in (
            ("R1 a tier-2 placement", {"subject": ["stint"], "_joined_on": "exact and unique in the archive"}, True),
            ("R1 a tier-1 placement", {"subject": ["stint"], "_joined_on": TIERS[0]}, False),
            ("R1 a tier-3 placement", {"subject": ["stint"], "_joined_on": TIERS[1]}, False)):
        failed = (not str(c.get("_joined_on", "")).startswith(TIERS)
                  or "unique in the archive" in str(c.get("_joined_on", "")))
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    for label, v, want_fail in (
            ("R3 a name claim with no kind", {"_basis": "x"}, True),
            ("R3 a name claim with no basis", {"kind": "declared typo: ..."}, True),
            ("R3 a name claim with both", {"kind": "a second name one source prints", "_basis": "edit distance 7"}, False)):
        failed = not any(v.get("kind", "").startswith(k) for k in KINDS) or not v.get("_basis")
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
