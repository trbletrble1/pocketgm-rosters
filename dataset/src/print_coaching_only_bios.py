"""Fifteen men who only ever coached, spread across the eras.

Bud Grant is printed after them, and apart from them, because he is NOT one:
he played six seasons for Philadelphia and Winnipeg before he coached, so the
generator always made him a bio. He is here because Ryan asked to see him.

  python3 src/print_coaching_only_bios.py [--seed 5]
"""
import os, sys, json, random, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from bio_select import Tables, select, career
from bio_write import write


def main():
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 5
    T = Tables()
    only = [g for g, p in T.people.items()
            if p.get("seasons") and all(k.startswith("COACHES|") for k in p["seasons"])]
    era = collections.defaultdict(list)
    for g in only:
        ys = [int(k.split("|")[1][1:5]) for k in T.people[g]["seasons"]]
        era[(min(ys) // 10) * 10].append(g)
    levy = next(g for g in only if T.people[g]["name"] == "Marv Levy")
    random.seed(seed)
    chosen, decades = [levy], sorted(era)
    for d in decades:
        pool = sorted(x for x in era[d] if x not in chosen)
        if pool: chosen.append(random.choice(pool))
    for d in decades:                       # a second from the fuller decades
        if len(chosen) >= 15: break
        pool = sorted(x for x in era[d] if x not in chosen)
        if len(era[d]) >= 30 and pool: chosen.append(random.choice(pool))
    while len(chosen) < 15:
        pool = sorted(x for x in only if x not in chosen)
        chosen.append(random.choice(pool))
    chosen = chosen[:15]
    def first_year(g): return min(int(k.split("|")[1][1:5]) for k in T.people[g]["seasons"])
    print("FIFTEEN MEN WHO ONLY EVER COACHED\n")
    for i, g in enumerate(sorted(chosen, key=first_year), 1):
        print(f"{i}. {write(select(T, g))}\n")
    grant = next(g for g, p in T.people.items() if p["name"] == "Bud Grant")
    print("\nAND BUD GRANT, who is not one of them: he played six seasons before he coached,")
    print("so the generator has always made him a bio.\n")
    print(f"16. {write(select(T, grant))}")


if __name__ == "__main__":
    main()
