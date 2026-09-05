"""Generate the stat-column declaration FROM THE CENSUS. Never hand-pasted.

The declaration keys on FILL BY ERA, not presence. `Tackle` sits in every era's
header and is 0% filled through the 1970s and 88% in the 2020s - tackles became
an official NFL statistic in 1994. A declaration keyed on presence would call it
universal and be wrong in every season before 1980.

Reads the cache only.  python3 src/declare_stat_columns.py [--write]
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from measure_stats_census import tables
CACHE = os.environ.get("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))

CALCULATED = {"Comp %", "Yds/Att", "TD %", "Int %", "Rating", "X/CP %", "FG %"}


def main():
    write = "--write" in sys.argv
    fill = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    present = collections.defaultdict(set)
    league_of = {}
    for f in glob.glob(os.path.join(CACHE, "S_*.html")):
        m = re.match(r"S_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
        if not m: continue
        year = int(m.group(2)); dec = (year // 10) * 10
        for hdr, rows in tables(open(f, encoding="utf-8", errors="replace").read()):
            for c in hdr:
                if c == "Player": continue
                present[c].add(year)
                for r in rows:
                    fill[c][dec][1] += 1
                    if r.get(c, "") != "": fill[c][dec][0] += 1
    out = {}
    for c, decs in fill.items():
        yrs = sorted(present[c])
        byd = {str(d): round(100.0 * a / b, 1) for d, (a, b) in sorted(decs.items()) if b}
        # the era where a column STARTS carrying values, not where it appears
        first_filled = next((d for d in sorted(decs) if decs[d][1] and
                             100.0 * decs[d][0] / decs[d][1] >= 5.0), None)
        out[c] = {"present_first": yrs[0], "present_last": yrs[-1],
                  "present_years": len(yrs),
                  "fill_by_decade": byd,
                  "first_decade_with_values": first_filled,
                  "calculated": c in CALCULATED}
    era_presence = {c: [v["present_first"], v["present_last"]]
                    for c, v in out.items() if v["present_years"] < 100}
    late = {c: v["first_decade_with_values"] for c, v in out.items()
            if v["first_decade_with_values"] and v["first_decade_with_values"] >= 1960
            and v["present_years"] >= 100}
    print(f"columns: {len(out)}")
    print(f"era-native BY PRESENCE (absent from whole eras): {len(era_presence)}")
    for c, (a, b) in sorted(era_presence.items()): print(f"   {c:<12} {a}-{b}")
    print(f"\npresent throughout but EMPTY until late - era-native by FILL: {len(late)}")
    for c, d in sorted(late.items(), key=lambda x: -x[1]):
        print(f"   {c:<12} first decade with values: {d}s   {out[c]['fill_by_decade']}")
    if write:
        decl_p = os.path.join(BASE, "declarations", "statscrew.json")
        d = json.load(open(decl_p))
        sc = d["stat_columns"]
        sc["columns"] = out
        sc["era_native_by_presence"] = era_presence
        sc["era_native_by_fill"] = late
        sc["_generated"] = ("by src/declare_stat_columns.py from the cache, 2026-09-05. "
                            "NOT hand-pasted: a hand-written census is how a conditional "
                            "figure came to sit in a field read as absolute (report 22).")
        sc["_the_rule"] = ("PRESENCE is nearly constant across eras; FILL is what is "
                           "era-native. Declare and check fill_by_decade. A check keyed "
                           "on presence would call Tackle universal and be wrong in every "
                           "season before 1980.")
        sc.pop("era_native_columns", None)
        json.dump(d, open(decl_p, "w"), indent=1)
        print("\ndeclaration written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
