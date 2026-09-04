"""Full-population field fill rates, read from the cached pages. No network.

Report 06 measured four teams per league-year. The sweep cached every team of
every season, so this replaces a sample with a census.
"""
import os, re, html, sys, json, collections, glob
CACHE = os.environ.get("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
COLS = ["#", "Birth Date", "Height", "Weight", "College", "Hometown", "GP", "GS"]

def parse(page):
    t = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    hdr = [html.unescape(re.sub(r"<[^>]+>", "", h)).strip()
           for h in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)]
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if hdr and len(cells) == len(hdr):
            rows.append(dict(zip(hdr, cells)))
    return hdr, rows

def main():
    per = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    absent = collections.defaultdict(set)
    teams = collections.Counter()
    for f in sorted(glob.glob(os.path.join(CACHE, "R_*.html"))):
        m = re.search(r"R_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
        if not m: continue
        year = int(m.group(2))
        hdr, rows = parse(open(f, encoding="utf-8", errors="replace").read())
        if not rows: continue
        teams[year] += 1
        for c in COLS:
            if c not in hdr:
                absent[year].add(c); continue
            for r in rows:
                per[year][c][1] += 1
                if r.get(c, "") != "": per[year][c][0] += 1
    out = {}
    for y in sorted(per):
        out[str(y)] = {"teams": teams[y],
                       "players": max(v[1] for v in per[y].values()),
                       "fill": {c: round(100.0 * v[0] / v[1], 1) for c, v in per[y].items() if v[1]},
                       "columns_absent": sorted(absent[y])}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..",
                                     "build-reports", "field-census.json"), "w"),
              indent=1, sort_keys=True)
    print(f"{'year':>5} {'tm':>3} {'players':>7} " + " ".join(f"{c[:9]:>9}" for c in COLS))
    for y in sorted(out):
        r = out[y]
        cells = []
        for c in COLS:
            v = r["fill"].get(c)
            cells.append("     ABS " if c in r["columns_absent"] else
                         (f"{v:8.1f} " if v is not None else "       - "))
        print(f"{y:>5} {r['teams']:3d} {r['players']:7d} " + "".join(cells))
    print(f"\nseasons {len(out)}  total player-rows {sum(r['players'] for r in out.values()):,}")

if __name__ == "__main__":
    main()
