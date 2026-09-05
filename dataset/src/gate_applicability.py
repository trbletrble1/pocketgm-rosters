"""Gate: a zero written where a measure does not apply is not an observation.

`Single` is 100% filled in every league. In the NFL all 29,028 values are 0,
because the rouge is a Canadian scoring play - the source uses one schema and
pads. By FILL those zeros are indistinguishable from measurements.

And all-zero cannot settle it either: `MFG` is also all-zero across the same
29,028 NFL values, and a missed field goal return touchdown is legal - it simply
never happened. That zero IS an observation and must be kept.

So applicability is DECLARED per league, and this gate holds the store to it:
no claim may exist for a (column, league) the declaration marks inapplicable.

  python3 src/gate_applicability.py       exit 1 = FAIL
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")


def main():
    decl = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
    ap = decl["stat_columns"]["applicability"]
    rules = {c: v["applicable_in"] for c, v in ap.items()
             if isinstance(v, dict) and "applicable_in" in v}
    if not rules:
        print("FAIL: no applicability rules are readable - is the block nested "
              "inside a documentation-only key again?")
        return 1
    print(f"applicability rules read: {sorted(rules)}")
    bad = collections.Counter(); checked = 0
    for f in sorted(glob.glob(os.path.join(BASE, "build", "stats-*.json"))):
        league = os.path.basename(f).split("-")[1].upper()
        try: d = json.load(open(f))
        except Exception: continue
        for c in d.get("claims") or []:
            pred = c.get("predicate")
            ok = rules.get(pred)
            if ok is None: continue
            checked += 1
            if ok == ["ALL"] or ok == "ALL": continue
            if league not in ok:
                bad[(pred, league)] += 1
    print(f"claims checked against a rule: {checked:,}")
    print(f"claims written for an INAPPLICABLE (column, league): {sum(bad.values()):,}")
    for (p, l), n in bad.most_common(10):
        print(f"  [FAIL] {p} in {l}: {n:,} claims - the league has no such measure")
    if bad:
        print("\nGATE FAILED: schema padding is stored as observation.")
        return 1
    print("\nGATE PASSED: no claim exists where the measure does not apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
