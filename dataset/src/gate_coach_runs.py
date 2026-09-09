"""Gate for patch 1 of the club job: coaching runs group on the club table's id.

  R1  every coaching season-year lands in exactly one run for its club and standing: none lost, none doubled
  R2  runs are maximal: no two runs of one club id and standing touch or overlap
  R3  every coaching token the table cannot place is counted and PRINTED (the table's census), never silent
  R4  the printed bios are byte-identical to the baseline taken before the patch
      (build-reports/bios-baseline-2026-09-06/), for the twenty coach bios, the fifteen coaching-only
      bios and the fifty player bios

  python3 src/gate_coach_runs.py
"""
import os, sys, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
BASELINE = os.path.join(BASE, "build-reports", "bios-baseline-2026-09-06")
from bio_select import Tables, career, coach_runs, club_id, _club_table, head_standing
from clubs import report

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def main():
    T = Tables(); n_men = 0; lost = []; touching = []
    for g, p in T.people.items():
        c = career(p)
        if not c["coached"]: continue
        n_men += 1
        # HEAD STANDING IS ASKED OF bio_select, NOT RE-TYPED HERE. This line carried its
        # own copy -- `bool(stint.get("is_head_coach"))` -- and on 2026-09-09 coach_runs
        # started also reading PFA's printed position, where 706 men are HEAD COACH. The
        # gate then compared the builder against a rule the builder no longer follows and
        # reported 727 men losing a year. Not one had. A gate with its own copy of the
        # rule tests the copy.
        want = collections.Counter((s["year"], head_standing(s["stint"]), club_id(s["club"], s["year"]))
                                   for s in c["coached"])
        runs = coach_runs(c)
        got = collections.Counter((y, r["head"], r["club_id"]) for r in runs for y in r["years"])
        if set(want) != set(got) or any(v != 1 for v in got.values()): lost.append((g, p["name"]))
        for a in runs:
            for b in runs:
                if a is not b and a["club_id"] == b["club_id"] and a["head"] == b["head"] and b["first"] - a["last"] <= 1 and a["first"] <= b["first"]:
                    touching.append((g, p["name"], a["club_id"], a["first"], a["last"], b["first"], b["last"]))
    print("R1  every coaching year is in exactly one run")
    check(not lost, f"{n_men:,} coached men; every (year, standing, club) is in exactly one run" if not lost else f"{len(lost)} men lose or double a year: {lost[:5]}")
    print("R2  runs are maximal")
    check(not touching, "no two runs of one club and standing touch" if not touching else f"{len(touching)} touching pairs: {touching[:3]}")
    print("R3  unplaced tokens are loud")
    rows = _club_table().census()
    report(_club_table())
    check(all(r[4] >= 1 for r in rows), f"{len(rows)} token(s) the table could not place, {sum(r[4] for r in rows):,} lookups, all printed above")
    print("R4  the bios reprint identical to the baseline")
    for script, fn in (("print_coach_bios.py", "coach-bios.txt"), ("print_coaching_only_bios.py", "coaching-only.txt"), ("print_bios.py", "bios.txt")):
        out = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, text=True).stdout
        base = open(os.path.join(BASELINE, fn)).read() if os.path.exists(os.path.join(BASELINE, fn)) else None
        if base is None: check(False, f"{fn}: no baseline at {BASELINE}"); continue
        same = out == base
        if not same:
            a, b = base.splitlines(), out.splitlines()
            first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            print(f"        first difference at line {first + 1}:\n        - {a[first] if first < len(a) else '<end>'}\n        + {b[first] if first < len(b) else '<end>'}")
        check(same, f"{script}: {len(out.splitlines())} lines, identical to baseline" if same else f"{script}: DIFFERS from baseline")
    print()
    if fails:
        print(f"COACH RUNS GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print("COACH RUNS GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main())
