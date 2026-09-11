"""Gate: PFA's own player code decides identity, both ways. Held on the base state.

  C1  A PLACEMENT BY CODE MATCHES EXACTLY ONE CANDIDATE. Every pfa-club-rosters stint claim
      joined on CODE_TIER is re-derived from the read model: among the held men carrying
      the printed name (outside this store), exactly one holds the code -- and he is the man
      placed. Refuses an empty population.
  C2  A PROMOTION AS A NEW PERSON MATCHES NONE. Every promotion made by the code rules
      holds a code that NO OTHER man in the archive holds, and no two new people share one.
      This is the property that stops the 36 duplicates measured before the rule was
      applied. Refuses an empty population.
  C3  NEITHER RULE REACHES AN EXCLUDED LEAGUE. Ryan, 2026-09-11: the code rules are applied
      in scope; the 3,536 people made on excluded leagues on 9 September are their own ruling.
  C4  A MAN WITH NO FORENAME IS NOT MINTED ONTO A HELD ROSTER, and none of the 27 removed on
      2026-09-11 comes back (build-reports/index-orphans-2026-09-11.json).

All rest on src/pfa_codes.py and on the ingest's own name set -- one implementation, not
a second copy for the gate to test instead of the rule.

    python3 src/gate_code_identity.py [--selftest]
"""
import os, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, pfa_codes
import ingest_pfa_club_rosters as ING

STORE = os.path.join(BASE, "build", "pfa-club-rosters.json")
PROM = os.path.join(BASE, "build", "player-promotions.json")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def c1(claims, everywhere, hold):
    # THE ROSTER LINE ONLY. Every stint claim from a placed row carries the tier, and most
    # of them -- pfa.age_in_season, pfa.roster.weight -- hold a bare string. The first run of
    # this gate read them as the line and crashed; it is the line that carries the code.
    placed = [c for c in claims if c.get("predicate") == "pfa.club_roster_line"
              and (c.get("subject") or [""])[0] == "stint"
              and str(c.get("_joined_on", "")).startswith(ING.CODE_TIER)]
    if not placed:
        check(False, "C1 a placement by code matches exactly one candidate -- NO placement by "
                     "code in the store, so there is nothing to hold"); return
    bad = []
    for c in placed:
        v = c.get("value") or {}; code = v.get("pfa_code"); pid = c["subject"][1]
        named = everywhere.get(ING.norm(v.get("Player", "")), set())
        on = {p for p in named if p in hold.get(code, ())}
        if not code or len(named) < 2 or on != {pid}:
            bad.append((v.get("Player"), code, pid, sorted(on)))
    check(not bad, f"C1 all {len(placed)} placements by code match exactly one man of that name, "
                   f"and he is the man placed" + ("" if not bad else f" -- {len(bad)} do not: {bad[:3]}"))


def c2(promotions, hold):
    new = [p for p in promotions if p.get("_new_by_code")]
    if not new:
        check(False, "C2 a promotion as a new person matches no one -- NO promotion by the code "
                     "rules, so there is nothing to hold"); return
    bad, by = [], collections.defaultdict(set)
    for p in new:
        code = p["_new_by_code"].get("pfa_code"); by[code].add(p["person_id"])
        others = set(hold.get(code, ())) - {p["person_id"]}
        if not code or others: bad.append((p.get("name"), code, sorted(others)))
    check(not bad, f"C2 all {len(new)} new people by code hold a code NO OTHER man holds"
          + ("" if not bad else f" -- {len(bad)} do not: {bad[:3]}"))
    dup = {c: sorted(ps) for c, ps in by.items() if len(ps) > 1}
    check(not dup, f"C2 no two new people share a PFA code"
          + ("" if not dup else f" -- {len(dup)} codes are shared: {list(dup.items())[:3]}"))


def c3(claims, promotions, excluded):
    """C3 NEITHER RULE REACHES AN EXCLUDED LEAGUE (Ryan, 2026-09-11). The leak of 9 September
    -- 3,536 people on excluded leagues -- is its own ruling; this route must not add to it."""
    if not excluded:
        check(False, "C3 no code rule reaches an excluded league -- the exclusion list is EMPTY"); return
    bad = [("placed", (c.get("value") or {}).get("Player"), (c.get("value") or {}).get("league"))
           for c in claims if c.get("predicate") == "pfa.club_roster_line"
           and str(c.get("_joined_on", "")).startswith(ING.CODE_TIER)
           and (c.get("value") or {}).get("league") in excluded]
    bad += [("new person", p.get("name"), s.get("league")) for p in promotions if p.get("_new_by_code")
            for s in p.get("playing_seasons") or [] if s.get("league") in excluded]
    check(not bad, "C3 no placement by code and no new person by code is on an excluded league"
          + ("" if not bad else f" -- {len(bad)} are: {bad[:3]}"))


ORPHANS = os.path.join(BASE, "build-reports", "index-orphans-2026-09-11.json")


def c4(promotions, removed):
    """C4 A MAN WITH NO FORENAME IS NOT MINTED ONTO A HELD ROSTER (Ryan, 2026-09-11). Every
    decision made under the rule records the roster it found; a no-forename promotion that
    found one is the Behman-beside-Bull-Behman defect. And none of the 27 removed that day
    comes back -- a refusal that a later run quietly undoes is not a refusal."""
    under = [p for p in promotions if "_club_season_roster_at_decision" in p]
    bad = [(p.get("name"), p["_club_season_roster_at_decision"]) for p in under
           if p.get("forename_unknown") and p["_club_season_roster_at_decision"]]
    check(not bad, f"C4 no promotion with no forename was made onto a held roster ({len(under)} "
                   f"decisions carry the roster they found)" + ("" if not bad else f" -- {len(bad)}: {bad[:3]}"))
    back = sorted({p["person_id"] for p in promotions} & set(removed))
    check(not back, f"C4 none of the {len(removed)} people removed on 2026-09-11 is promoted again"
          + ("" if not back else f" -- {back[:5]}"))


def selftest():
    global FAILS
    ok = True

    def expect(label, fn, want_fail):
        global FAILS
        nonlocal ok
        FAILS = []; fn()
        got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if got else 'pass'}")

    named = {"joe johnson": {"P_1", "P_2"}}
    claim = lambda pid: {"predicate": "pfa.club_roster_line",
                         "subject": ["stint", pid, "X", "AFL-1934"], "_joined_on": ING.CODE_TIER,
                         "value": {"Player": "Joe Johnson", "pfa_code": "john01000"}}
    expect("C1 the code is held by BOTH candidates", lambda: c1([claim("P_1")], named, {"john01000": {"P_1", "P_2"}}), True)
    expect("C1 the code is the OTHER candidate's", lambda: c1([claim("P_1")], named, {"john01000": {"P_2"}}), True)
    expect("C1 nothing placed by code", lambda: c1([], named, {}), True)
    expect("C1 the code is exactly the man placed", lambda: c1([claim("P_1")], named, {"john01000": {"P_1"}}), False)
    age = {"predicate": "pfa.age_in_season", "subject": ["stint", "P_1", "X", "AFL-1934"],
           "_joined_on": ING.CODE_TIER, "value": "23"}
    expect("C1 a string-valued claim beside the line is not read as the line",
           lambda: c1([claim("P_1"), age], named, {"john01000": {"P_1"}}), False)

    prom = lambda pid, code: {"person_id": pid, "name": "Jack Roberts", "_new_by_code": {"pfa_code": code}}
    expect("C2 the new man's code is held by someone else", lambda: c2([prom("P_9", "robe04200")], {"robe04200": {"P_3"}}), True)
    expect("C2 two new men share a code", lambda: c2([prom("P_9", "robe04300"), prom("P_10", "robe04300")], {}), True)
    expect("C2 nobody promoted by code", lambda: c2([], {}), True)
    expect("C2 a code nobody else holds", lambda: c2([prom("P_9", "robe04300")], {"robe04300": {"P_9"}}), False)

    cofl = {"predicate": "pfa.club_roster_line",
            "subject": ["stint", "P_1", "PFA:ORL", "COFL-1966"], "_joined_on": ING.CODE_TIER,
            "value": {"Player": "Bill Johnson", "league": "COFL", "pfa_code": "john03200"}}
    expect("C3 a placement by code on an excluded league", lambda: c3([cofl], [], {"COFL"}), True)
    expect("C3 a new person by code on an excluded league",
           lambda: c3([], [{"name": "X", "_new_by_code": {"pfa_code": "x"},
                            "playing_seasons": [{"league": "ACFL"}]}], {"ACFL"}), True)
    expect("C3 an empty exclusion list", lambda: c3([], [], set()), True)
    expect("C3 both rules in scope", lambda: c3([{**cofl, "value": {**cofl["value"], "league": "AFL"}}], [], {"COFL"}), False)

    behman = {"person_id": "P_054559", "name": "Behman", "forename_unknown": True,
              "_club_season_roster_at_decision": 31}
    expect("C4 a surname-only man minted onto a roster of 31", lambda: c4([behman], []), True)
    expect("C4 a removed man promoted again",
           lambda: c4([{**behman, "_club_season_roster_at_decision": 0}], ["P_054559"]), True)
    expect("C4 a surname-only man on an empty club-season",
           lambda: c4([{**behman, "person_id": "P_9", "_club_season_roster_at_decision": 0}], ["P_054559"]), False)
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    d = json.load(open(STORE))
    c1(d["claims"], ING.names_elsewhere(conn), pfa_codes.holders(conn, exclude_stores={ING.SRC_ID}))
    proms = json.load(open(PROM)).get("promotions", [])
    c2(proms, pfa_codes.holders(conn))
    c3(d["claims"], proms, ING.EXCLUDED)
    if not os.path.exists(ORPHANS):
        raise SystemExit(f"{ORPHANS} is absent -- C4 cannot tell whether a removed man came back, "
                         "and an absent list must not read as an empty one")
    c4(proms, list(json.load(open(ORPHANS))["entries"]))
    if FAILS:
        print(f"\nCODE IDENTITY GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCODE IDENTITY GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
