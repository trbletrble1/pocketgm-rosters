"""Gate: no photograph may be attached to a person on an ambiguous name.

The failure this prevents is silent. 1,263 photos carry a name shared by 2,993
men. Attaching one to the likeliest of them renders a real person's face on
another man's page, and nothing anywhere reports an error. A gap is recoverable;
a wrong face at scale is not.

Two properties over build/photos.json:
  1. every denoted name resolves to EXACTLY ONE person in the universe;
  2. every denotation records the tier-3 discriminator, so no consumer can
     mistake a name-unique match for a source-native id.

  python3 src/gate_photo_denotation.py       exit 1 = FAIL
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from denote_photos import person_universe

REQUIRED = ["name", "verified_unique_in_person_universe"]


def main():
    p = os.path.join(BASE, "build", "photos.json")
    if not os.path.exists(p):
        print("FAIL: build/photos.json missing - run denote_photos.py --write"); return 1
    store = json.load(open(p))
    n2g = person_universe()
    g2names = collections.defaultdict(set)
    for n, gs in n2g.items():
        for g in gs: g2names[g].add(n)

    ambiguous, wrong_disc = [], []
    dens = store.get("denotations") or []
    for d in dens:
        g = d.get("person")
        if list(d.get("discriminator") or []) != REQUIRED:
            wrong_disc.append((d.get("matched_against"), d.get("discriminator")))
        # the name this denotation used must denote exactly one person
        for nm in g2names.get(g, set()):
            if len(n2g.get(nm, ())) > 1:
                ambiguous.append((d.get("matched_against"), nm, len(n2g[nm])))
    print(f"photo denotations: {len(dens)}")
    print(f"  attached on an AMBIGUOUS name: {len(ambiguous)}")
    for a in ambiguous[:5]: print(f"     [FAIL] {a[0]} -> '{a[1]}' denotes {a[2]} men")
    print(f"  missing the tier-3 discriminator: {len(wrong_disc)}")
    for w in wrong_disc[:5]: print(f"     [FAIL] {w[0]}: {w[1]}")
    if ambiguous or wrong_disc:
        print("\nGATE FAILED"); return 1
    print("\nGATE PASSED: every photo rests on a name verified unique, and says so")
    return 0


if __name__ == "__main__":
    sys.exit(main())
