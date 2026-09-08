"""Every stint subject in every build store resolves to a person.

build_person_index reads a stint as ["stint", PERSON, club, season] and resolves
PERSON either as a global P_ id or as a (store, local) pair through identity.json.
A stint whose s[1] is anything else -- a league code, a club, a name -- is skipped
in silence: no error, no count, no line. The builder's own comment records the
first time this happened (statistics stores adopting the global id, Junior Seau
"no statistics are recorded"); the second time was afl-1926.json and
nfl-1934-cincinnati.json putting the LEAGUE in s[1] with the person as a sidecar
field, and the rebuild produced 0 AFL|1926 seasons and 0 NFL|1934|CIN while
reporting REBUILD OK and P3 green. P3 compares before with after; it cannot see
a store that never entered at all.

This is the check that would have caught both. It replicates the builder's
resolution step exactly and runs over EVERY store, so a third instance fails by
filename before a rebuild ever runs.

DO NOT RETIRE THIS AS A DUPLICATE. gate_person_index.static_checks() calls
check() here as its P4 and refuses a rebuild for any failing store not declared
in declarations/person-index-rebuild.json. It also imports resolve_person from
build_person_index, so the gate and the builder share ONE resolver and cannot
disagree. One property, one check, two entry points.

  python3 src/gate_stint_subjects.py [--selftest]
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from build_person_index import resolve_person


def load_loc2g():
    idm = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
    return {(s, p): g for g, v in idm.items() for s, p in v["local"]}


def scan(loc2g, stores=None):
    """-> {store: (stints, unresolved, example)} for every store holding a stint claim."""
    out = {}
    for f in sorted(stores or glob.glob(os.path.join(BASE, "build", "*.json"))):
        st = os.path.basename(f)[:-5]
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict) or "claims" not in d:
            continue
        n = bad = 0; ex = None
        for c in d["claims"]:
            s = c.get("subject")
            if not (isinstance(s, list) and len(s) == 4 and s[0] == "stint"):
                continue
            n += 1
            pid = s[1]
            g = resolve_person(st, pid, loc2g)              # the builder's own resolver: gate and builder cannot disagree
            if not g:
                bad += 1; ex = ex or s
        if n:
            out[st] = (n, bad, ex)
    return out


def check(loc2g, stores=None):
    res = scan(loc2g, stores)
    fails = [f"{st}: {bad:,} of {n:,} stint subjects do not resolve to a person, e.g. {ex}"
             for st, (n, bad, ex) in res.items() if bad]
    return res, fails


def selftest():
    loc2g = load_loc2g()
    res, base = check(loc2g)
    print("SELFTEST"); print(f"baseline failures: {len(base)}\n")
    # write a temp store with the exact defect shape and confirm it fails BY NAME
    tmp = os.path.join(BASE, "build", "zz-selftest-stint.json")
    json.dump({"claims": [{"subject": ["stint", "NFL", "CHI", "1950"], "predicate": "x", "value": 1,
                           "person": "P_000001"}]}, open(tmp, "w"))
    try:
        _, fails = check(loc2g, [tmp])
        ok = len(fails) == 1 and "zz-selftest-stint" in fails[0]
        print(f"  {'OK  ' if ok else 'BAD '} a store with the league in s[1] fails by filename -> {fails}")
        json.dump({"claims": [{"subject": ["stint", "P_000001", "CHI", "1950"], "predicate": "x", "value": 1}]},
                  open(tmp, "w"))
        _, fails2 = check(loc2g, [tmp])
        ok2 = not fails2
        print(f"  {'OK  ' if ok2 else 'BAD '} the same store with the person in s[1] passes")
    finally:
        os.remove(tmp)
    print(f"\nselftest {'PASSED' if ok and ok2 else 'FAILED'}")
    return ok and ok2


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    res, fails = check(load_loc2g())
    print(f"stores holding stint claims: {len(res)}   stint subjects: {sum(n for n, _, _ in res.values()):,}")
    for f in fails: print("  FAIL ", f)
    print(f"\n{'GATE PASSED' if not fails else f'{len(fails)} store(s) FAIL'} -- every stint subject resolves to a person"
          if not fails else f"\n{len(fails)} store(s) FAIL")
    sys.exit(1 if fails else 0)
