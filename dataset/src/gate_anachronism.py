"""Gate: a value whose measure did not exist yet cannot be `observed`.

Green Bay 1950 lists Tobin Rote with a passer Rating of 26.7. The formula was
adopted in 1973. The number is real - StatsCrew computed it - but it is not an
observation of 1950, and it sits in the same table as his 224 attempts, in the
same format, with nothing marking the difference.

This is the third instance of one shape:
  1. the 1980 hearing's estimated column - the document SAYS it is a projection
  2. the NFLPA's flat $45,000 per assistant - an estimating fill, and the word
     "approximately" is right there
  3. this - and the source says NOTHING. No hedge, no footnote, no formatting.

Which makes it the hardest of the three: the first two announce themselves.

The rule: for any claim, if the predicate's measure was introduced AFTER the
season the claim describes, kind must be `source_derived` (or `derived`), never
`observed`.

  python3 src/gate_anachronism.py       exit 1 = FAIL
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")


def introduced():
    d = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
    out = {}
    for col, spec in d.get("stat_columns", {}).get("measure_introduced", {}).items():
        if spec.get("year"):
            out[col] = spec["year"]
            out[col.lower().replace(" ", "_").replace("%", "pct")] = spec["year"]
    return out


def check_store(path, intro):
    bad = []
    try: d = json.load(open(path))
    except Exception: return bad
    if not isinstance(d, dict): return bad
    for c in d.get("claims") or []:
        if not isinstance(c, dict): continue
        pred = str(c.get("predicate", ""))
        yr = intro.get(pred) or intro.get(pred.lower())
        if not yr: continue
        season = c.get("observed_at")
        if not isinstance(season, int): continue
        if season < yr and c.get("kind") == "observed":
            bad.append({"store": os.path.basename(path), "predicate": pred,
                        "season": season, "measure_introduced": yr,
                        "kind": c.get("kind"), "value": c.get("value")})
    return bad


def main():
    intro = introduced()
    if not intro:
        print("no dated measures declared - nothing to check"); return 0
    print("measures with an introduction year:",
          {k: v for k, v in intro.items() if " " not in k and k[0].isupper()})
    bad = []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        bad += check_store(f, intro)
    print(f"claims checked across {len(glob.glob(os.path.join(BASE,'build','*.json')))} stores")
    print(f"anachronistic claims filed as OBSERVED: {len(bad)}")
    for b in bad[:10]:
        print(f"  [FAIL] {b['store']}: {b['predicate']}={b['value']} at season "
              f"{b['season']}, but the measure dates from {b['measure_introduced']}")
    if bad:
        print(f"\nGATE FAILED: {len(bad)} computed values are filed as observations.")
        return 1
    print("\nGATE PASSED: no value is claimed as observed before its measure existed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
