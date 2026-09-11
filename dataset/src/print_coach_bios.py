"""Twenty bios for reading the coaching rule against: ten men the merge of
2026-09-06 put back together, ten who coached and were never merged.

  python3 src/print_coach_bios.py [--seed 7]
"""
import os, sys, json, random

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from bio_select import Tables, select, career
from bio_write import write

NAMED = ["Mike Ditka", "Tom Landry", "Tom Flores", "Marty Schottenheimer"]


def main():
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 7
    T = Tables()
    M = json.load(open(os.path.join(BASE, "declarations", "person-merge-decisions.json")))   # the decisions, in git
    merged = {d["canonical_person"] for d in M["merges"]}
    def coached_and_played(g):
        c = career(T.people[g]); return bool(c["played"] and c["coached"])
    have = {g for g in T.people if coached_and_played(g) and select(T, g)}
    named = [next(g for g in have if T.people[g]["name"] == n) for n in NAMED]
    random.seed(seed)
    pool_m = sorted((have & merged) - set(named))
    pool_u = sorted(have - merged)
    pick_m = named + random.sample([g for g in pool_m], 6)
    pick_u = random.sample(pool_u, 10)
    print("TEN MEN THE MERGE PUT BACK TOGETHER")
    print("(the first four are the men Ryan named as at risk; the other six are a seeded draw)\n")
    for i, g in enumerate(pick_m, 1): print(f"{i}. {write(select(T, g))}\n")
    print("\nTEN WHO COACHED AND WERE NEVER MERGED\n")
    for i, g in enumerate(pick_u, 11): print(f"{i}. {write(select(T, g))}\n")


if __name__ == "__main__":
    main()
