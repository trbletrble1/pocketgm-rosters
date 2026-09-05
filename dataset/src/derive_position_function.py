"""What does a position CODE do? Derived from the statistics that co-occur with it.

No source we hold states what `ROE-RDE-LO` means. StatsCrew prints the code bare;
the guides have no legend that survives OCR. So the English NAME is not available
as a claim from anything.

But the FUNCTION is, and it is what a bio actually needs: knowing a man is a
linebacker is what tells the sentence to reach for tackles rather than yards.

Method: for every position code, measure which statistical columns the men who
held it actually recorded. That is reproducible from the cache by anyone, and it
is `source_derived` with a stated basis - not a guess about football.

  python3 src/derive_position_function.py [--write]
"""
import os, sys, json, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
IDX.pop("_clubs", None)

# the columns that separate one kind of footballer from another
MARKERS = ["Att", "Comp", "Yds", "TDs", "Rec", "Tackle", "Solo", "Int", "Sacked",
           "FGA", "FGM", "Punts", "No.", "Brup", "FF"]


def main():
    write = "--write" in sys.argv
    agg = collections.defaultdict(lambda: collections.Counter())
    n = collections.Counter()
    for g, p in IDX.items():
        for k, d in p.get("seasons", {}).items():
            st, stats = d.get("stint", {}), d.get("stats", {})
            v = st.get("position")
            codes = []
            for one in (v if isinstance(v, list) else [v]):
                if isinstance(one, dict): one = one.get("code")
                if one: codes.append(str(one))
            if not codes or not stats: continue
            for c in codes:
                n[c] += 1
                for m in MARKERS:
                    val = stats.get(m)
                    try:
                        if val not in (None, "") and float(str(val).replace(",", "")) > 0:
                            agg[c][m] += 1
                    except ValueError:
                        pass
    out = {}
    for c, cnt in agg.items():
        if n[c] < 15: continue
        prof = {m: round(cnt[m] / n[c], 3) for m in MARKERS if cnt[m]}
        top = sorted(prof.items(), key=lambda x: -x[1])[:4]
        # the salient statistic: what these men most often actually record
        salient = None
        for m in ("Tackle", "Rec", "Comp", "FGM", "Punts", "Yds"):
            if prof.get(m, 0) >= 0.4: salient = m; break
        out[c] = {"seasons": n[c], "profile": dict(top), "salient_column": salient}
    print(f"position codes with >=15 recorded seasons: {len(out)}  "
          f"(of {len(n)} codes seen)")
    print(f"\n{'code':<10}{'seasons':>8}  salient   profile")
    for c, v in sorted(out.items(), key=lambda x: -x[1]["seasons"])[:22]:
        prof = " ".join(f"{k}={x:.2f}" for k, x in v["profile"].items())
        print(f"{c:<10}{v['seasons']:>8}  {str(v['salient_column']):<9} {prof}")
    if write:
        p = os.path.join(BASE, "declarations", "position_function.json")
        json.dump({"_what": "position code -> what the men who held it actually "
                            "recorded. DERIVED from co-occurring statistics, not "
                            "from any source that states a meaning.",
                   "_method": "for each code, the share of its recorded seasons "
                              "carrying a non-zero value in each marker column",
                   "_not_a_translation": "this says what a code DOES, not what it "
                                         "is called. No held source states the "
                                         "English name of a position code.",
                   "_measured": "2026-09-05",
                   "codes": out}, open(p, "w"), indent=1)
        print(f"\nwrote declarations/position_function.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
