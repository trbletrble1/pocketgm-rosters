"""What is IN the Madden roster files? Field census across the family.

We tested PSKI, PHCL, PFMK and PHED because appearance was the question. Those
files carry ~110 fields per player and nobody has looked at the other hundred.

Characterises from the DATA, not from what the four-letter codes are assumed to
mean: fill rate, cardinality, range, and whether the values look like a rating
(0-99), a small enum, an identifier, or free text.

Characterisation only. Extracts nothing.
"""
import os, sys, csv, glob, json, collections, statistics

ROOT = os.path.expanduser("~/Documents/pgm3-sources/madden")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def shape(vals):
    """What KIND of thing is this column, judged by its values?"""
    nonblank = [v for v in vals if v not in ("", None)]
    if not nonblank: return "empty", {}
    nums, txt = [], 0
    for v in nonblank:
        try: nums.append(float(v))
        except ValueError: txt += 1
    n = len(nonblank); card = len(set(nonblank))
    info = {"fill": round(100.0 * n / len(vals), 1), "distinct": card}
    if txt > n * 0.2:
        info["example"] = sorted(set(nonblank))[:3]
        return "text", info
    lo, hi = min(nums), max(nums)
    info.update({"min": lo, "max": hi})
    if card <= 2: return "flag", info
    if 0 <= lo and hi <= 99 and card > 20: return "rating-like (0-99)", info
    if card <= 40 and hi <= 100: return "small enum", info
    if hi > 1000: return "identifier / large int", info
    return "numeric", info


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "*PLAY.csv"))) + \
            sorted(glob.glob(os.path.join(ROOT, "*PLAY*.csv")))
    files = sorted(set(files))
    print(f"PLAY files: {len(files)}")
    percol = collections.defaultdict(list)
    infiles = collections.Counter()
    rows_total = 0
    for f in files:
        try:
            r = list(csv.DictReader(open(f, encoding="utf-8", errors="replace")))
        except Exception as e:
            print(f"  {os.path.basename(f)}: {type(e).__name__}"); continue
        rows_total += len(r)
        cols = r[0].keys() if r else []
        for c in cols: infiles[c] += 1
        for row in r:
            for c in cols:
                percol[c].append(row.get(c, ""))
    print(f"total player rows across the family: {rows_total}")
    print(f"distinct field codes: {len(percol)}")
    print(f"fields present in ALL {len(files)} files: "
          f"{sum(1 for c,n in infiles.items() if n==len(files))}\n")
    out = {}
    rows = []
    for c, vals in percol.items():
        kind, info = shape(vals)
        out[c] = {"kind": kind, "in_files": infiles[c], **info}
        rows.append((c, kind, info.get("fill", 0), info.get("distinct", 0),
                     info.get("min"), info.get("max"), info.get("example")))
    order = {"text": 0, "identifier / large int": 1, "rating-like (0-99)": 2,
             "small enum": 3, "numeric": 4, "flag": 5, "empty": 6}
    rows.sort(key=lambda r: (order.get(r[1], 9), -r[2]))
    print(f"{'code':<7}{'kind':<22}{'fill%':>7}{'distinct':>9}{'min':>7}{'max':>7}  example")
    for c, k, fl, d, lo, hi, ex in rows:
        print(f"{c:<7}{k:<22}{fl:>7}{d:>9}"
              f"{('' if lo is None else lo):>7}{('' if hi is None else hi):>7}  "
              f"{'' if ex is None else ex}")
    json.dump(out, open(os.path.join(BASE, "build-reports", "madden-fields.json"), "w"), indent=1)
    print(f"\nwrote build-reports/madden-fields.json")


if __name__ == "__main__":
    main()
