"""Column census for StatsCrew team-season statistics pages.

Reports the shape BEFORE anything is ingested, the way the roster census did.

Two things this must get right, both already established:
  - the <tbody><td> parse trap: per-player rows carry no <tr>, so a naive row
    regex returns only the Totals line. Cells are chunked by header length.
  - the column vocabulary is ERA-NATIVE. No `Sacked` in 1950; `X/CA` present
    then and gone now. Declared per era, not inferred from whichever page
    happened to be parsed first.

  python3 src/measure_stats_census.py [--write]
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
CACHE = os.environ.get("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))

# A table is named by the columns it carries, because the pages do not label them.
SIGNATURES = [
    ("passing",   {"Att", "Comp", "Ints"}),
    ("rushing",   {"No.", "Yds", "Avg.", "TDs"}),
    ("kicking",   {"X/CA", "FG/FGA"}),
    ("punting",   {"Punts", "Avg."}),
    ("defense",   {"Sacks", "Ints"}),
    ("returns",   {"Ret", "Yds"}),
]


def tables(html):
    """-> [(headers, [row dicts])]. Chunks cells by header length: these tables
    emit <tbody><td> with NO <tr>, so a row regex sees only Totals."""
    # Strip COMMENTS as well as scripts. These pages carry commented-out
    # grouping header rows - <!-- <th colspan=7>Tackles</th> ... --> - and
    # reading them as columns invented a "Tackles" column filled 84% in the
    # 1920s, half a century before tackles were recorded. The live header is
    # "Tackle", singular.
    t = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    # THE SOURCE NAMES EACH TABLE and I discarded it. Every table is preceded by
    # an <h2>: Passing, Rushing, Receiving, Kicking, Punting, Punt Returns, Kick
    # Returns, Interceptions, Defense and Fumbles, Total Scoring. Without it a
    # `Yds` claim is passing yards, rushing yards or punting yards and nothing
    # says which - Johnny Unitas and a punter both stored "Yds = 3481".
    out = []
    chunks = t.split("<table")
    heads = []
    for ch in chunks[:-1] if len(chunks) > 1 else chunks:
        hs = re.findall(r"<h2[^>]*>(.*?)</h2>", ch, re.S)
        heads.append(re.sub("<[^>]+>", "", hs[-1]).strip().rstrip(":") if hs else None)
    for i, blk in enumerate(chunks[1:]):
        blk = blk.split("</table>")[0]
        # A MULTI-LEVEL HEADER. The scoring table carries a grouping row
        #   <th colspan=8>Touchdowns</th><th colspan=5>Other</th><th>Total</th>
        # above the real column row. Flattening both gave 19 "columns" for a
        # 15-column table, and every value shifted: Billy Grimes 1950 came out
        # as Touchdowns=5, Other=1, Total=2, Player=0. Take the LAST <tr> of
        # the <thead> - that is the column row.
        head = blk.split("</thead>")[0] if "</thead>" in blk else blk
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", head, re.S)
        src_row = trs[-1] if trs else head
        hdr = [re.sub("<[^>]+>", "", x).strip()
               for x in re.findall(r"<th[^>]*>(.*?)</th>", src_row, re.S)]
        # An unclosed <th> makes the regex swallow the NEXT tag, so a literal
        # '<th class="dt-center"' arrived as a column name. A column name that
        # contains markup is a parse artefact, not a column.
        hdr = [c for c in hdr if c and "<" not in c and len(c) < 24]
        if not hdr:
            continue
        cells = [re.sub("<[^>]+>", "", x).strip()
                 for x in re.findall(r"<td[^>]*>(.*?)</td>", blk, re.S)]
        n = len(hdr)
        rows = [dict(zip(hdr, cells[i:i + n])) for i in range(0, len(cells) - n + 1, n)]
        rows = [r for r in rows if r.get(hdr[0], "").lower() != "totals"]
        out.append((hdr, rows, heads[i] if i < len(heads) else None))
    return out


def main():
    write = "--write" in sys.argv
    files = sorted(glob.glob(os.path.join(CACHE, "S_*.html")))
    per_year_cols = collections.defaultdict(collections.Counter)   # year -> col -> pages
    per_year_pages = collections.Counter()
    per_year_rows = collections.Counter()
    per_year_tables = collections.Counter()
    fill = collections.defaultdict(lambda: [0, 0])                 # (year,col) -> filled,total
    tiny = []
    for f in files:
        m = re.match(r"S_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
        if not m: continue
        team, year = m.group(1), int(m.group(2))
        h = open(f, encoding="utf-8", errors="replace").read()
        if len(h) < 5000: tiny.append((len(h), team, year))
        per_year_pages[year] += 1
        tbs = tables(h)
        per_year_tables[year] += len(tbs)
        for hdr, rows in tbs:
            per_year_rows[year] += len(rows)
            for c in hdr:
                if c: per_year_cols[year][c] += 1
            for r in rows:
                for c in hdr:
                    if not c: continue
                    fill[(year, c)][1] += 1
                    if r.get(c, "") != "": fill[(year, c)][0] += 1
    years = sorted(per_year_pages)
    if not years:
        print("no stats pages cached yet"); return 0
    print(f"team-season stat pages read: {sum(per_year_pages.values())}  "
          f"years {years[0]}-{years[-1]}")
    print(f"tables parsed: {sum(per_year_tables.values())}   "
          f"player rows: {sum(per_year_rows.values())}")
    if tiny:
        print(f"\npages under 5KB (look at these): {len(tiny)}")
        for n, t, y in sorted(tiny)[:8]: print(f"   {n:>7}b {t} {y}")

    # ERA-NATIVE VOCABULARY: when does each column appear and disappear?
    allcols = collections.Counter()
    for y in years: allcols.update(per_year_cols[y])
    print(f"\ndistinct column names across the corpus: {len(allcols)}")
    print(f"\n{'column':<14}{'first':>7}{'last':>7}{'yrs':>6}   fill%")
    span = {}
    for c, _ in allcols.most_common(40):
        ys = [y for y in years if c in per_year_cols[y]]
        if not ys: continue
        f_, t_ = 0, 0
        for y in ys:
            a, b = fill[(y, c)]; f_ += a; t_ += b
        span[c] = {"first": ys[0], "last": ys[-1], "years": len(ys),
                   "fill": round(100.0 * f_ / t_, 1) if t_ else None}
        print(f"{c:<14}{ys[0]:>7}{ys[-1]:>7}{len(ys):>6}   "
              f"{span[c]['fill'] if span[c]['fill'] is not None else '-'}")
    if write:
        json.dump({"pages": sum(per_year_pages.values()), "years": [years[0], years[-1]],
                   "column_span": span,
                   "columns_by_year": {str(y): sorted(per_year_cols[y]) for y in years}},
                  open(os.path.join(BASE, "build-reports", "stats-census.json"), "w"), indent=1)
        print("\nwrote build-reports/stats-census.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
