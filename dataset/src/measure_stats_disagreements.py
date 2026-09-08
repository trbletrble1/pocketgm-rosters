"""What kind of thing each PFA-against-StatsCrew statistical disagreement is.

CLASSIFY ONLY. Nothing is resolved, nothing is removed, nothing is rewritten. Both
figures stand in the archive exactly as they were written.

NOT EVERY DIFFERENCE IS A DIFFERENCE ABOUT FOOTBALL:

  an absence written as a number  StatsCrew holds `0` for a column and era it did not
                                  record -- longest plays before the 1940s -- and PFA
                                  holds a real figure. Zero is not its answer; it is
                                  the absence of one, written in the same ink.
  a rounding difference           `.Avg.` and the percentage columns, where the two
                                  compilations round the same underlying pair of
                                  numbers differently. 22.3 against 22.2.
  a difference of fact            383 receiving yards against 283. This is the number
                                  worth knowing and it is the smallest.

  python3 src/measure_stats_disagreements.py
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
REPORT = os.path.join(BASE, "build-reports", "pfa-stats-ingest.json")
OUT = os.path.join(BASE, "build-reports", "stats-disagreement-kinds.json")

# columns whose value is computed from two others, so the two compilations can differ
# by rounding alone without differing about anything
DERIVED = ("Avg.", "%", "Rating", "Yds/Att")


def clean(x):
    return str(x).replace("&nbsp;", " ").replace("\xa0", " ").strip().rstrip("t")


def as_num(x):
    try:
        return float(clean(x))
    except Exception:
        return None


def kind(d):
    pfa = clean(d["pfa"])
    theirs = [clean(v) for v in d["statscrew"]]
    pred = d["predicate"]
    col = pred.split(".", 1)[1] if "." in pred else pred
    pn = as_num(pfa)
    tn = [as_num(v) for v in theirs]
    tn = [v for v in tn if v is not None]

    # ONE SIDE HOLDS NOTHING AT ALL
    if not pfa:
        return "PFA holds nothing where StatsCrew holds a figure"
    if all(not v for v in theirs):
        return "StatsCrew holds nothing where PFA holds a figure"

    # ZERO AGAINST A REAL FIGURE, in a column where zero is how an absence was written
    if tn and all(v == 0 for v in tn) and pn not in (None, 0):
        return ("an absence written as a number: StatsCrew holds 0, PFA holds a figure"
                if col in ("Long",) else
                "StatsCrew holds 0 where PFA holds a figure")
    if pn == 0 and tn and all(v != 0 for v in tn):
        return "PFA holds 0 where StatsCrew holds a figure"

    # ROUNDING, and only on a column that is computed from two others
    if pn is not None and tn and any(c in col for c in DERIVED):
        if min(abs(pn - v) for v in tn) <= 0.15:
            return "a rounding difference on a computed column"
        return "a computed column differing by more than rounding"

    if pn is not None and tn:
        return "A DIFFERENCE OF FACT"
    return "one side is not a number"


def main():
    r = json.load(open(REPORT))
    ds = r["disagreements"]
    total = r.get("disagreements_total", len(ds))
    n = collections.Counter()
    by_pred = collections.defaultdict(collections.Counter)
    facts = []
    for d in ds:
        k = kind(d)
        n[k] += 1
        by_pred[k][d["predicate"]] += 1
        if k == "A DIFFERENCE OF FACT":
            facts.append(d)

    print(f"{total:,} disagreements recorded; {len(ds):,} carried in the report and "
          "classified here\n")
    for k, c in n.most_common():
        print(f"   {c:>7,}  {100.0*c/len(ds):>5.1f}%  {k}")
    print(f"\n   the columns behind each kind:")
    for k, c in n.most_common():
        top = ", ".join(f"{p} {v:,}" for p, v in by_pred[k].most_common(4))
        print(f"      {k[:52]:52s} {top}")

    print(f"\nA DIFFERENCE OF FACT: {len(facts):,} of {len(ds):,} classified "
          f"({100.0*len(facts)/len(ds):.1f}%)")
    pre = sum(1 for d in facts if d.get("shared_lineage_before_1933"))
    print(f"   of those, before 1933 (shared lineage): {pre:,}")
    print("   examples:")
    for d in sorted(facts, key=lambda z: z["year"])[:12]:
        print(f"      {d['year']} {d['predicate']:26s} PFA {d['pfa']:>7}  "
              f"StatsCrew {','.join(d['statscrew'])}")
    json.dump({"kinds": dict(n), "classified": len(ds), "total": total,
               "differences_of_fact": facts[:2000]}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
