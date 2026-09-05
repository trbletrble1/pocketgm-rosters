"""Gate: a global person is formed by a source-native id, never by a name.

The defect: person ids were store-local AND collided. p_000190 was Joe Kapp in
cfl-1966, Chick Maggioli in nfl-1950 and Greg Dortch in nfl-2024.

Two properties, over every global person:
  1. NO MERGE WITHOUT A SOURCE-NATIVE ID. A group holding more than one local
     record must be held together by a slug. A group with no slug is a singleton.
  2. NO SLUG HOLDS TWO MEN. Every local record in a group resolves to the same
     slug (or the p-/c- pair the source itself cross-references).

And a regression case built from the collision that started it.

  python3 src/gate_identity.py        exit 1 = FAIL
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
P = os.path.join(BASE, "build-reports", "identity.json")


def main():
    if not os.path.exists(P):
        print("FAIL: build-reports/identity.json missing - run unify_identity.py --write")
        return 1
    idm = json.load(open(P))
    bad_merge, multi_slug = [], []
    for gid, v in idm.items():
        slugs, loc = v["slugs"], v["local"]
        if len(loc) > 1 and not slugs:
            bad_merge.append((gid, len(loc)))
        # a group may hold p- and c- for one man; anything else is two men
        bodies = {s.split("-", 1)[1] for s in slugs}
        if len(bodies) > 1:
            multi_slug.append((gid, slugs))
    # regression: the collision that started this must NOT be one person
    byslug = {s: g for g, v in idm.items() for s in v["slugs"]}
    kapp = byslug.get("p-kappjoe001")
    magg = byslug.get("p-maggichi001")
    dort = byslug.get("p-dortcgre001")
    collided = len({kapp, magg, dort}) != 3

    print(f"global persons: {len(idm)}")
    print(f"  groups merged with NO source-native id: {len(bad_merge)}")
    for g, n in bad_merge[:5]: print(f"     [FAIL] {g}: {n} local records, no slug")
    print(f"  groups holding two different slug bodies: {len(multi_slug)}")
    for g, s in multi_slug[:5]: print(f"     [FAIL] {g}: {s}")
    print(f"  regression p_000190 (Kapp / Maggioli / Dortch) still distinct: "
          f"{'NO' if collided else 'yes'}")
    if kapp:
        n = len(idm[kapp]["local"])
        print(f"  Kapp spans {n} stores as one person ({kapp})")
        if n < 2:
            print("     [FAIL] Kapp did not unify")
            collided = True
    fail = bad_merge or multi_slug or collided
    print("\n" + ("GATE FAILED" if fail else "GATE PASSED: every merge rests on a "
                                             "source-native id, and no slug holds two men"))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
