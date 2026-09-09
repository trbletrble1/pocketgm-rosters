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
            # A COACHING-ONLY MAN IS ONE WITH COACHING SEASONS AND NO PLAYING ONES.
            # Ruled 2026-09-09: that is the SHAPE, not a `COACHES|` key prefix. This read
            # `all(k.startswith("COACHES|"))` over `seasons` -- it saw only the stores that
            # name no league, missed every PFA coaching-only man, and produced NOTHING at
            # all once the coaching seasons moved to their own dict.
            if p.get("coaching_seasons") and not p.get("seasons")]
    era = collections.defaultdict(list)
    for g in only:
        ys = [int(str(k.split("|")[1]).lstrip("y")[:4]) for k in T.people[g]["coaching_seasons"]]
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
    def first_year(g): return min(int(str(k.split("|")[1]).lstrip("y")[:4]) for k in T.people[g]["coaching_seasons"])
    print("FIFTEEN MEN WHO ONLY EVER COACHED\n")
    for i, g in enumerate(sorted(chosen, key=first_year), 1):
        # THE WRITER RAISES FOR 997 OF THE 2,138, and that is reported rather than
        # crashed on: render_coaching_only hands a coaching-only lead fact
        # (`coached_one_season`, `coached_long`, `coached_one_club`,
        # `coached_across_leagues`) to coach_lead, which reads `f["coaching"]` -- a key
        # only the played-then-coached fact carries. Pre-existing in bio_write; it became
        # reachable when the coaching-only men entered the bio corpus on 2026-09-09.
        # Saying which men cannot be written is worth more than a traceback.
        try:
            print(f"{i}. {write(select(T, g))}\n")
        except KeyError as e:
            print(f"{i}. [{T.people[g]['name']}: the writer raises KeyError {e} -- "
                  f"bio_write.coach_lead expects a `coaching` key the coaching-only facts do not carry]\n")
    grant = next(g for g, p in T.people.items() if p["name"] == "Bud Grant")
    print("\nAND BUD GRANT, who is not one of them: he played six seasons before he coached,")
    print("so the generator has always made him a bio.\n")
    print(f"16. {write(select(T, grant))}")


if __name__ == "__main__":
    main()
