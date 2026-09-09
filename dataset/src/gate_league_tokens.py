"""Gate: every league the model assigns must be a league, or a declared non-competition.

REAL_LEAGUES has been computed in service/build_read_model.py since the day the
club table was built -- three functions above the code that assigned a league
called `NOT` to 132,038 stint keys, more than the NFL's 114,369. Nothing compared
the two. This is that comparison.

  P1  Every distinct `league` on a stint or person_season claim must be either a
      league the CLUB TABLE holds, or a single-word token the rebuild declaration
      names on purpose (COACHES, IND, DRAFT -- each declared with its reason).
      A token that is neither is a parser artefact, and `NOT` was one for a day.

  P2  No store may be mapped to a token the declaration does not name. The rule
      that reads the declaration lives in service/league_tokens.py; P2 checks the
      model against it, so the two cannot drift the way the two copies of that
      rule drifted before they were unified.

The exemption list is DERIVED from the declaration, never typed here. A new
non-competition token is declared once, in prose, and this gate follows.

  python3 src/gate_league_tokens.py           exit 1 = FAIL
  python3 src/gate_league_tokens.py --self-test  proves it can fail
"""
import os, sys, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, league_tokens as LT
import clubs as ac


def real_leagues():
    C = ac.Clubs()
    return {lg["league"] for c in C.T["clubs"] for s in c["segments"] for lg in s["leagues"]}


def allowed():
    """Leagues the club table holds, plus the non-competition tokens the declaration
    names on purpose. Read, never typed."""
    return real_leagues() | LT.declared_non_leagues(paths.INDEX_REBUILD_DECL)


def main():
    ok = allowed()
    conn = sqlite3.connect(paths.READ_MODEL)
    found = {r[0]: r[1] for r in conn.execute(
        "select league, count(*) from claim where scope in ('stint','person_season') "
        "and league is not null and league != '' group by league")}
    if "--self-test" in sys.argv:
        # PROVE IT CAN FAIL: withhold a real league from the allowed set and require
        # that the gate notices. Nothing is written; only this dict is narrowed.
        victim = next((l for l in sorted(found) if l in ok), None)
        if victim is None:
            print("self-test INCONCLUSIVE: the model holds no league that is currently allowed")
            sys.exit(1)
        bad = {l: n for l, n in found.items() if l not in (ok - {victim})}
        print(f"self-test: withheld {victim!r} from the allowed set -> {len(bad)} token(s) rejected"
              + (" -- the gate fails when it should" if bad else
                 " -- SELF-TEST DID NOT FAIL: the gate cannot fail and proves nothing"))
        sys.exit(0 if bad else 1)

    if not found:
        print("REFUSED: the model holds no stint league at all. An empty denominator is not a pass.")
        sys.exit(2)
    bad = {l: n for l, n in found.items() if l not in ok}
    print(f"{len(found)} distinct league tokens on stint/person_season claims")
    print(f"  club table holds        : {sorted(l for l in found if l in real_leagues())}")
    print(f"  declared non-competition: {sorted(l for l in found if l in LT.declared_non_leagues(paths.INDEX_REBUILD_DECL) and l not in real_leagues())}")
    for l, n in sorted(bad.items(), key=lambda x: -x[1]):
        print(f"  NOT A LEAGUE AND NOT DECLARED: {l!r} on {n:,} claims")
    print("PASS" if not bad else "FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
