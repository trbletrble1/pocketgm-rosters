"""Gate: no claim resolves to a club-season whose league differs from the claim's own.

Ryan's ruling, 2026-09-11. It is the FOURTH time a join has thrown the league away: HOU 1984,
the disagreement claims hardcoding NFL-{year}, the gate's own copy of the resolver, and the
coaching join -- where `CHI` in a 1974 WFL coaching cell became the 1920 Decatur Staleys
because the code was looked up without its league. So the gate holds the PROPERTY, over
every claim in the read model, and names none of the instances.

  L1  EVERY CLAIM WITH A LEAGUE AND A CLUB SITS ON A CLUB THAT PLAYS IN THAT LEAGUE THAT
      YEAR -- any of the club's leagues that year, because the table lawfully gives a club
      two (Regina is CFL 1945-2025 and WIFU 1946-60). `IND` is the declared token for a club
      asserting no league and matches the table's empty league; COACHES and SALARIES are
      declared non-competitions and carry no club-season to differ from.
      Refuses an empty population.

It reads the claims and the club table, never the resolver: a gate with its own copy of the
resolver tests the copy, and that was the third instance.

    python3 src/gate_claim_league.py [--selftest]
"""
import os, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

NO_CLUB_SEASON = {"COACHES", "SALARIES"}
NO_LEAGUE = {"IND": ""}
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def leagues_by_club_year(table):
    out = collections.defaultdict(set)
    for cl in table["clubs"]:
        for s in cl["segments"]:
            for l in s["leagues"]:
                for y in range(l.get("first") or 0, (l.get("last") or 0) + 1):
                    out[(cl["id"], y)].add(l.get("league") or "")
    return out


def l1(rows, lby):
    """rows: (league, year, club_id, store, predicate, n)."""
    total = bad = 0
    classes = collections.Counter()
    for lg, y, cid, store, pred, n in rows:
        if lg in NO_CLUB_SEASON: continue
        total += n
        want = NO_LEAGUE.get(lg, lg)
        have = lby.get((cid, y), set())
        if want not in have:
            bad += n
            classes[(lg, "/".join(sorted(have)) or "no season that year", store)] += n
    if not total:
        check(False, "L1 every claim sits on a club of its own league -- NO claim carries both a "
                     "league and a club, so there is nothing to hold"); return classes
    check(not bad, f"L1 all {total:,} claims with a league and a club sit on a club that plays in "
                   f"that league that year" + ("" if not bad else
                   f" -- {bad:,} do not, in {len(classes)} (league, club's league, store) classes"))
    for (lg, have, store), n in classes.most_common(15):
        print(f"         {n:>7,}  claim {lg:<6} club plays {have:<22} {store}")
    return classes


def codes_by_year(table):
    """(code, year) -> the set of leagues played by every club the table holds under that
    code that year -- its segment code or the PFA code it carries."""
    out = collections.defaultdict(set)
    for cl in table["clubs"]:
        for s in cl["segments"]:
            for code in {s.get("code"), s.get("pfa_code")} - {None}:
                for l in s["leagues"]:
                    for y in range(l.get("first") or 0, (l.get("last") or 0) + 1):
                        out[(code, y)].add(l.get("league") or "")
    return out


def l2(keys, pseudo, cby):
    """L2 NO INDEX KEY PUTS A CLUB-SEASON IN A LEAGUE ITS CLUB DOES NOT PLAY -- which is how one
    club-season comes to be held twice: `USFL|2022|US2BIS` beside `USFL2|2022|US2BIS`.

    THE FIRST VERSION WAS WRONG AND THE LIVE RUN SHOWED IT: it called a (year, code) under two
    tokens a split, and flagged 195 -- but a code is not a club across leagues. In 1926 `BKN`
    is the NFL Lions AND the AFL Horsemen, two club-seasons, both real. So the test is the
    table's: the key's code names clubs that year, and NONE of them plays the key's league.
    Read from the club table, never from the resolver or from the label declaration."""
    n = 0; bad = collections.Counter()
    for k in keys:
        p = str(k).split("|", 2)
        if len(p) != 3 or p[0] in pseudo or not p[1].lstrip("y")[:4].isdigit(): continue
        lg, y, code = p[0], int(p[1].lstrip("y")[:4]), p[2]
        have = cby.get((code, y))
        if have is None: continue                      # a code the table cannot place: gate_club_table_reach's
        n += 1
        if NO_LEAGUE.get(lg, lg) not in have: bad[(lg, y, code, "/".join(sorted(have)))] += 1
    if not n:
        check(False, "L2 no key puts a club-season in a league its club does not play -- NO key to check"); return bad
    check(not bad, f"L2 all {n:,} placed season keys name a league their club plays that year"
          + ("" if not bad else f" -- {sum(bad.values()):,} keys in {len(bad)} club-seasons do not: "
                                f"{[k for k, _ in bad.most_common(6)]}"))
    return bad


def selftest():
    global FAILS
    ok = True
    lby = {("club-decatur-staleys-1920", 1974): {"NFL"}, ("club-chicago-fire-1974", 1974): {"WFL"},
           ("club-regina", 1950): {"CFL", "WIFU"}, ("club-frankford", 1922): {""}}

    def expect(label, rows, want_fail):
        global FAILS
        nonlocal ok
        FAILS = []; l1(rows, lby); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")

    expect("L1 a 1974 WFL coaching claim on the Decatur Staleys",
           [("WFL", 1974, "club-decatur-staleys-1920", "pfa-coaches", "pfa.coaching_season", 3)], True)
    expect("L1 nothing to check", [], True)
    expect("L1 the same claim on the Chicago Fire",
           [("WFL", 1974, "club-chicago-fire-1974", "pfa-coaches", "pfa.coaching_season", 3)], False)
    expect("L1 a WIFU claim on a club the table gives CFL and WIFU",
           [("WIFU", 1950, "club-regina", "pfa-stats-1950s", "rushing.Yds", 1)], False)
    expect("L1 an IND claim on a club asserting no league",
           [("IND", 1922, "club-frankford", "frankford-book-ind", "roster", 1)], False)

    cby = {("US2BIS", 2022): {"USFL2"}, ("BKN", 1926): {"NFL", "AFL"}, ("WFLNYS", 1974): {"WFL"}}

    def expect2(label, keys, want_fail):
        global FAILS
        nonlocal ok
        FAILS = []; l2(keys, {"COACHES"}, cby); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    expect2("L2 the 2022 Stallions under 1983's USFL", ["USFL|2022|US2BIS", "USFL2|2022|US2BIS"], True)
    expect2("L2 no keys", [], True)
    expect2("L2 the Stallions under USFL2 only", ["USFL2|2022|US2BIS"], False)
    expect2("L2 1926 BKN under NFL and AFL -- two clubs, one code", ["NFL|1926|BKN", "AFL|1926|BKN"], False)
    expect2("L2 a pseudo token beside a league", ["COACHES|1974|WFLNYS", "WFL|1974|WFLNYS"], False)
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    table = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    lby = leagues_by_club_year(table)
    c = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    rows = c.execute("SELECT league, year, club_id, store, predicate, count(*) FROM claim "
                     "WHERE league IS NOT NULL AND club_id IS NOT NULL AND year IS NOT NULL "
                     "GROUP BY 1,2,3,4,5").fetchall()
    l1(rows, lby)
    import league_tokens as LT
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); idx.pop("_clubs", None)
    l2((k for r in idx.values() if isinstance(r, dict) for k in (r.get("seasons") or {})),
       LT.pseudo_leagues(os.path.join(BASE, "declarations", "person-index-rebuild.json")), codes_by_year(table))
    if FAILS:
        print(f"\nCLAIM LEAGUE GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCLAIM LEAGUE GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
