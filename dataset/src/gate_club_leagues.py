"""Gate for patch 3 of the club job: a coaching season's league comes from the club table.

  L1  wherever the archive's own playing keys give a (club, year) a league, the table gives the same one
  L2  every coaching club-season either has a league from the table, or its token is in the table's
      unresolved list -- never a silent None
  L3  the three bio prints reprint identical to the baseline (gate_coach_runs R4 runs them)

  python3 src/gate_club_leagues.py
"""
import os, sys, json, collections, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from bio_select import Tables, career, IDX
from clubs import Clubs

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def main():
    T = Tables(); C = Clubs()
    # the old derivation, rebuilt here as the property to hold: the archive's own playing keys
    pk = collections.defaultdict(collections.Counter)
    for p in T.people.values():
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2)
            if lg not in ("COACHES", "SALARIES"): pk[(club, int(y[1:5]) if y.startswith("y") else int(y))][lg] += 1
    playing = {k: v.most_common(1)[0][0] for k, v in pk.items()}
    print("L1  the table never contradicts a playing key")
    seasons = [(p["name"], s["club"], s["year"]) for p in T.people.values() for s in career(p)["coached"]]
    contra = [(n, c, y, playing[(c, y)], T.league_of(c, y)) for n, c, y in seasons if (c, y) in playing and T.league_of(c, y) not in (None, playing[(c, y)])]
    answered = sum(1 for n, c, y in seasons if (c, y) in playing)
    check(not contra, f"{answered:,} coaching club-seasons have a playing-key league; the table agrees on all of them" if not contra else f"{len(contra)} contradictions: {contra[:5]}")
    print("L2  no silent None")
    listed = {r["string"] for r in C.T["unresolved"]["strings"]}
    silent = sorted({(c, y) for n, c, y in seasons if T.league_of(c, y) is None and c not in listed})
    none = sorted({(c, y) for n, c, y in seasons if T.league_of(c, y) is None})
    check(not silent, f"{len(seasons):,} coaching club-seasons; {len(seasons) - len(none)} carry a league; {len(none)} do not and every one of those tokens is in the table's unresolved list" if not silent else f"{len(silent)} have no league and are not listed: {silent[:5]}")
    print("L3  the bio prints")
    out = subprocess.run([sys.executable, os.path.join(HERE, "gate_coach_runs.py")], capture_output=True, text=True).stdout
    check("COACH RUNS GATE: pass" in out, "gate_coach_runs passes (R4: three prints identical to baseline)" if "COACH RUNS GATE: pass" in out else out[-800:])
    print()
    if fails: print(f"CLUB LEAGUES GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print("CLUB LEAGUES GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main())
