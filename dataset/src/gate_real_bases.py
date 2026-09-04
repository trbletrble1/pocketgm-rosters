"""Gate: all four §9.6 bases must be reachable IN THE BUILT DATA, not only in a fixture.

The selftest proves the gate can fail. This proves the distinction exists in the
sources. They are different claims and both are needed.
"""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from resolve_store import load

BASE = os.path.join(HERE, "..")
STORES = ["nfl-1950.json", "wfl-1974.json"]

def main():
    pol = json.load(open(os.path.join(BASE, "policy", "resolution.json")))
    decl = [os.path.join(BASE, "declarations", "statscrew.json")]
    seen = collections.Counter()
    per_pred = {}
    for f in STORES:
        path = os.path.join(BASE, "build", f)
        if not os.path.exists(path):
            print(f"  MISSING store {f} - run the ingest first"); return 1
        s = load(path, decl)
        s.universe = {tuple(x) for x in json.load(open(path)).get("universe", [])}
        scope_of = {}
        for c in s.claims:
            subj = tuple(c["subject"]) if isinstance(c["subject"], list) else c["subject"]
            scope_of.setdefault(c["predicate"], subj[0])
        by_scope = collections.defaultdict(set)
        for u in s.universe: by_scope[u[0]].add(u)
        for pred, sc in scope_of.items():
            cnt = collections.Counter()
            for subj in by_scope[sc]:
                cnt[s.resolve(subj, pred, pol)["basis"]] += 1
            per_pred[(f, pred)] = cnt
            seen.update(cnt)

    print("bases reached across the built corpus:")
    for b in ("observed", "absent", "unknown", "contested"):
        print(f"  {b:10s} {seen.get(b,0):6d}")

    missing = [b for b in ("observed","absent","unknown","contested") if not seen.get(b)]
    if missing:
        print(f"\nFAIL: bases never reached in real data: {missing}")
        print("      (a basis that only a fixture can produce is not evidence the")
        print("       distinction exists in the sources)")
        return 1

    # the sharp one: state 1 and state 2 must be DISTINGUISHABLE within one predicate,
    # i.e. some predicate must show both `unknown` and `absent`.
    both = [(f, p) for (f, p), c in per_pred.items() if c.get("unknown") and c.get("absent")]
    if not both:
        print("\nFAIL: no single predicate shows BOTH unknown and absent.")
        print("      'column missing entirely' and 'column present, cell blank' are")
        print("      then not demonstrably distinguishable in the built data.")
        return 1
    print(f"\nunknown AND absent co-occur in {len(both)} predicate(s):")
    for f, p in both:
        c = per_pred[(f, p)]
        print(f"  {f} / {p}: observed {c.get('observed',0)}, absent {c.get('absent',0)}, "
              f"unknown {c.get('unknown',0)}, contested {c.get('contested',0)}")
    print("\nPASS: four bases reachable in real data, and states 1 and 2 distinguishable")
    return 0

if __name__ == "__main__":
    sys.exit(main())
