"""Question 4: what would parsing a class ADD that the archive does not already hold?

THE FIRST ANSWER WAS WRONG AND IS RECORDED AS SUCH. Taking the denominator from the
index's own roster-membership predicates gave 100.0% coverage of birth date, college and
home town in EVERY era, pre-1950 included. That is a selection effect, not a fact: those
season keys come from PFA, and PFA supplies those same three fields for the same men, so
the measurement asked 'of the men PFA knows, how many have PFA's fields'. The denominator
must not be supplied by the source being measured -- the same trap as
`deciders-must-read-the-base-state`.

What replaces it: split the archive's people by whether PFA knows them at all, which is
independent of any document, and measure coverage on each side. Then count how many people
each GUIDE-DERIVED predicate actually covers, because the answer to 'what would parsing
add' turns out not to be more birth dates but fields the store has almost no predicate for.

  python3 src/census_value.py
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
IDX = os.path.join(BASE, "build-reports", "person-index.json")
OUT = os.path.join(BASE, "build-reports", "corpus-census-value.json")

FIELDS = {
    "birth_date":  ("birth_date", "pfa.birth_date", "nflverse.birth_date", "wikipedia.birth_date"),
    "college":     ("college", "pfa.college"),
    "hometown":    ("hometown", "pfa.birth_place", "statscrew.birth_place", "wikipedia.birth_place"),
    "high_school": ("pfa.high_school", "high_school", "statscrew.high_school", "wikipedia.high_school"),
    "height":      ("pfa.height",),
    "photograph":  ("has_photograph", "wikipedia.photograph"),
}


def main():
    print("loading index...", flush=True)
    idx = json.load(open(IDX))
    grp = collections.defaultdict(collections.Counter)
    guide_preds, all_preds = collections.Counter(), collections.Counter()
    bare = 0
    decades = collections.Counter()
    for pid, rec in idx.items():
        p = rec.get("person") or {}
        for k in p:
            all_preds[k] += 1
            if k.startswith("guide."): guide_preds[k] += 1
        g = "known_to_pfa" if any(k.startswith("pfa.") for k in p) else "not_known_to_pfa"
        grp[g]["men"] += 1
        for f, ks in FIELDS.items():
            if any(p.get(k) for k in ks): grp[g][f] += 1
        if g == "not_known_to_pfa":
            if not p: bare += 1
            for v in p.values():
                for s in (v if isinstance(v, list) else [v]):
                    if isinstance(s, str):
                        for tok in s.split("|"):
                            if len(tok) == 4 and tok.isdigit(): decades[int(tok) // 10 * 10] += 1

    res = {"_date": "2026-09-07",
           "_superseded_measurement": {
               "what": "coverage by era, denominator = men with a roster-membership season key",
               "result": "100.0% birth_date/college/hometown in every era including pre-1950",
               "why_wrong": "selection effect -- those season keys come from PFA and PFA supplies "
                            "those same fields for those same men; the denominator was supplied "
                            "by the source being measured"},
           "coverage_by_pfa_knowledge": {},
           "people_with_no_recorded_fact_and_not_known_to_pfa": bare,
           "decade_of_facts_for_men_not_known_to_pfa": {str(k): v for k, v in sorted(decades.items())},
           "guide_derived_predicates": dict(guide_preds.most_common()),
           "predicates_absent_entirely": ["off-season occupation", "fraternity", "nickname",
                                          "physical description (eye/hair colour)", "street address"],
           "total_people": len(idx)}
    for g, c in grp.items():
        n = c["men"]
        res["coverage_by_pfa_knowledge"][g] = {
            "men": n, **{f: {"held": c[f], "missing": n - c[f],
                             "pct_held": round(100 * c[f] / n, 1) if n else 0} for f in FIELDS}}
    IO.dump_atomic(res, OUT, indent=1)

    print(f"\n{'group':18} {'men':>6} " + " ".join(f"{f:>12}" for f in FIELDS))
    for g in ("known_to_pfa", "not_known_to_pfa"):
        r = res["coverage_by_pfa_knowledge"][g]
        print(f"{g:18} {r['men']:>6} " + " ".join(f"{r[f]['pct_held']:>11.1f}%" for f in FIELDS))
    print(f"\nmen not known to PFA with NO recorded fact at all: {bare}")
    print("their facts by decade:", dict(list(res['decade_of_facts_for_men_not_known_to_pfa'].items())[:6]))
    print("\nguide-derived predicates (people covered):")
    for k, v in guide_preds.most_common(10): print(f"  {v:6} {k}")


if __name__ == "__main__":
    main()
