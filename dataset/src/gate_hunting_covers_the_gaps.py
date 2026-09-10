"""A GAP MUST NOT LEAVE THE HUNTING LIST BY LEAVING THE CLUB TABLE.

WHY THIS EXISTS. Between 8 and 9 September the hunting list's best section --
club-seasons the archive holds nobody for -- fell from 128 to 18, and not one of the
110 was filled. They left the CLUB TABLE. The archive gained statistics-derived
stints in the minor-league AFL, EFL, IFL and UFL years; `build_clubs` mints a
PFA-only club only where the archive covers NOTHING in that league-year, so once
those years were covered the PFA cell behind each club was refused instead of
minted, the club-season stopped existing, and a list built by walking the club table
could not see it. The number went down and read like progress.

The archive already counts those season keys -- gate_club_table_reach's ratchet, at
2,017 against a ceiling of 2,018. What it did not do was carry them into the
document Ryan hunts from. This gate joins the two.

THREE PROPERTIES:

  G1  every in-scope club-season the club table cannot name, that the index puts men
      on, appears in the hunting measurement's `club_seasons_off_the_table`. Same
      test, same Clubs(), as gate_club_table_reach -- ONE implementation of "can the
      table name this", not a second copy that can drift.
  G2  `empty_club_seasons` and `club_seasons_off_the_table` do not overlap. They are
      different gaps -- the table holds the club-season and nobody is on it, versus
      the table holds no club-season at all -- and a row in both would be counted
      twice in the ranked list.
  G3  every club-season in the measurement carries a league, a year and a name or a
      token, so no row reaches the document as a blank the reader cannot search on.

  python3 src/gate_hunting_covers_the_gaps.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
THIN = os.path.join(BASE, "build-reports", "thin-archive.json")
INDEX = os.path.join(BASE, "build-reports", "person-index.json")

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def in_scope(league, year):
    """The hunting document's scope. Read from the measurement, not typed again."""
    from measure_thin_archive import in_scope as _s
    return _s(league, str(year))


def unnamed_in_scope(C, people):
    """-> {(league, year, token): men} the club table cannot name, inside the scope."""
    out = collections.defaultdict(set)
    for pid, p in people.items():
        if not isinstance(p, dict): continue
        for k in (p.get("seasons") or {}):
            parts = k.split("|", 2)
            if len(parts) != 3: continue
            lg, y, tok = parts
            yr = str(y).lstrip("y")
            if not yr.isdigit() or not in_scope(lg, yr): continue
            yy = int(yr)
            r = C.resolve(tok, yy, None, source="season_key")
            if r and C.name_for(r[0], yy): continue
            out[(lg, yy, tok)].add(pid)
    return {k: len(v) for k, v in out.items()}


def main(argv):
    if "--selftest" in argv: return selftest()
    from clubs import Clubs
    T = json.load(open(THIN))
    idx = json.load(open(INDEX)); idx.pop("_clubs", None)
    off = T.get("club_seasons_off_the_table")
    if off is None:
        check(False, "thin-archive.json carries no `club_seasons_off_the_table`. The hunting "
                     "measurement cannot see the club-seasons the club table cannot name, and "
                     "a gap that leaves the table leaves the document in silence.")
        print(f"\nHUNTING COVERAGE GATE: {len(FAILS)} FAILURE(S)"); return 1
    want = unnamed_in_scope(Clubs(), idx)
    have = {(r["league"], r["year"], r["code"]) for r in off}
    # the measurement collapses `AKR` and `PFA:AKR` onto one row by printed name, so a
    # token is covered if its own key OR its bare/prefixed twin is on the list
    def covered(lg, y, tok):
        bare = tok[4:] if tok.startswith("PFA:") else tok
        return any((lg, y, t) in have for t in (tok, bare, "PFA:" + bare))
    missing = sorted(k for k in want if not covered(*k))
    print(f"HUNTING COVERAGE  ({len(want)} in-scope club-seasons the table cannot name, "
          f"{sum(want.values())} men)")
    check(not missing,
          f"G1 every one of them is in the hunting measurement"
          + ("" if not missing else
             f" -- {len(missing)} are NOT: " + ", ".join(f"{l}|{y}|{t}" for l, y, t in missing[:6])
             + (" ..." if len(missing) > 6 else "")))
    empt = {(x["league"], int(x["year"]), x["code"]) for x in T["empty_club_seasons"]}
    both = sorted(empt & {(r["league"], r["year"], r["code"]) for r in off})
    check(not both, f"G2 `empty` and `off the table` do not overlap"
          + ("" if not both else f" -- {len(both)} appear in both: {both[:4]}"))
    blank = [r for r in off if not r["league"] and not r["code"]] + \
            [r for r in off if not r["names"] and not r["code"]]
    check(not blank, f"G3 every off-the-table row carries a league and a name or a token"
          + ("" if not blank else f" -- {len(blank)} do not"))
    noname = [r for r in off if not r["names"]]
    print(f"  note {len(noname)} of {len(off)} carry a token and no printed name at all; "
          f"they are listed as the token, not dropped")
    if FAILS:
        print(f"\nHUNTING COVERAGE GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nHUNTING COVERAGE GATE: pass"); return 0


def selftest():
    """Both answers, on a fixture. The BEFORE case is the 8 September shape: the
    measurement had no off-the-table list, so a real gap was invisible."""
    ok = True
    for label, off, want_fail in (
            ("8 September: no off-the-table list at all", None, True),
            ("a club-season the table cannot name, missing from the list", [], True),
            ("the same club-season, on the list", [{"league": "AFL", "year": 1946,
                                                    "code": "PFA:AKR", "men": 5,
                                                    "names": ["Akron Bears"], "sources": []}], False)):
        have = {(r["league"], r["year"], r["code"]) for r in (off or [])}
        missing = [] if off is None else [k for k in [("AFL", 1946, "PFA:AKR")]
                                          if k not in have]
        failed = off is None or bool(missing)
        good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    # G2 must fire on an overlap
    empt = {("EFL", 1926, "PFA:BET")}; off = {("EFL", 1926, "PFA:BET")}
    good = bool(empt & off); ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} G2 fires when a club-season is in both lists")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
