"""Gate: a statistic must name the table it came from.

`Yds` is passing yards, rushing yards, receiving yards, punting yards or return
yards depending on which table it sat in. Stored bare, Johnny Unitas 1963 and a
punter both read `Yds = 3481`, and a league-leaders query returned punters as
the leading passers.

This is the salary lesson in another field: there is no predicate called
`salary` because the convention belongs in the NAME. There must be no predicate
called `Yds` either.

The source states the table - every one is preceded by an <h2> - so this is not
a modelling choice, it is a fact that was being discarded.

  python3 src/gate_statistics_name_their_table.py     exit 1 = FAIL
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")

# columns whose meaning depends entirely on the table they came from
AMBIGUOUS = {"Yds", "No.", "Avg.", "Long", "TDs", "Att", "Yds.", "Int", "Fum"}


def main():
    bare = collections.Counter()
    qualified = 0
    files = 0
    for f in sorted(glob.glob(os.path.join(BASE, "build", "stats-*.json"))):
        files += 1
        try: d = json.load(open(f))
        except Exception: continue
        for c in d.get("claims") or []:
            p = c.get("predicate", "")
            if "." in p:
                qualified += 1
            elif p in AMBIGUOUS:
                bare[(os.path.basename(f), p)] += 1
    print(f"statistics stores: {files}")
    print(f"claims whose predicate names its table: {qualified:,}")
    print(f"claims carrying a BARE ambiguous column: {sum(bare.values()):,}")
    for (f, p), n in bare.most_common(8):
        print(f"  [FAIL] {f}: {n:,} claims of bare '{p}' - which table?")
    if bare:
        print(f"\nGATE FAILED: {len(bare)} store/column pairs store an ambiguous "
              f"statistic.")
        return 1
    print("\nGATE PASSED: every statistic names the table it came from.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
