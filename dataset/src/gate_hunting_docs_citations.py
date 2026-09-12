"""Gate: a regenerated hunting document carries the newspaper-citation columns, or fails.

Ryan, 2026-09-11. The five columns -- written_up, newspaper_citations, cited_with_page, papers, links --
were added to the three hunting documents by hand, and src/write_hunting_docs.py regenerates all three.
A regeneration that does not know them drops them in silence: the fourth shape in the precedents, a field
going stale because the data around it changed.

This gate RUNS a writer and inspects what it writes. It never writes the real documents: HOME is pointed
at a scratch folder, so `~/Dropbox/Football Archive/docs` resolves inside it, and the sweep's report
folder is linked in read-only so the writer can read it.

  H1  the CSV header carries all five columns
  H2  the spreadsheet's "The list" header carries all five
  H3  the markdown table header carries its four (written up, newspaper citations (with a page), papers, links)
  H4  every row carries a written_up value from the declared vocabulary -- no row is silently empty
  H5  the three renderings agree row by row: same row count, and the CSV's five cells equal the spreadsheet's

  python3 src/gate_hunting_docs_citations.py [--script PATH]   exit 1 = FAIL
"""
import os, sys, csv, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
NEW = ["written_up", "newspaper_citations", "cited_with_page", "papers", "links"]
MD_NEW = ["written up", "newspaper citations (with a page)", "papers", "links"]
VOCAB = {"both", "Wikipedia", "fandom", "nobody", "not joined to one club-season", "not in the sweep's per-row report"}
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def main():
    script = sys.argv[sys.argv.index("--script") + 1] if "--script" in sys.argv else os.path.join(HERE, "write_hunting_docs.py")
    real_reports = os.path.expanduser("~/Dropbox/Football Archive/reports")
    home = tempfile.mkdtemp(prefix="gate-hunting-docs-", dir=os.environ.get("GATE_SCRATCH") or None)
    docs = os.path.join(home, "Dropbox", "Football Archive", "docs"); os.makedirs(docs)
    os.symlink(real_reports, os.path.join(home, "Dropbox", "Football Archive", "reports"))
    print(f"writer: {script}\nwriting into scratch: {docs} (the real documents are not touched)")
    p = subprocess.run([sys.executable, script], env={**os.environ, "HOME": home}, capture_output=True, text=True)
    if p.returncode != 0:
        check(False, f"H0 the writer ran (exit {p.returncode}): {(p.stderr or p.stdout)[-400:]}")
        return 1
    c = list(csv.reader(open(os.path.join(docs, "what-to-look-for.csv"), newline="")))
    head, body = c[0], c[1:]
    check(all(n in head for n in NEW), f"H1 the CSV header carries the citation columns (missing: {[n for n in NEW if n not in head]})")
    from openpyxl import load_workbook
    ws = load_workbook(os.path.join(docs, "what-to-look-for.xlsx"))["The list"]
    xh = [x.value for x in ws[1]]
    check(all(n in xh for n in NEW), f"H2 the spreadsheet header carries the citation columns (missing: {[n for n in NEW if n not in xh]})")
    md = open(os.path.join(docs, "what-to-look-for.md")).read().split("\n")
    th = next((l for l in md if l.startswith("| # | one document adds")), "")
    check(all(f" {n} |" in th for n in MD_NEW), f"H3 the markdown table header carries its four citation columns "
                                                 f"(missing: {[n for n in MD_NEW if f' {n} |' not in th]})")
    if "written_up" in head:
        i = head.index("written_up")
        bad = [r[0] for r in body if r[i] not in VOCAB]
        check(not bad, f"H4 every row carries a written_up value from the vocabulary ({len(body)} rows; {len(bad)} not: {bad[:5]})")
    else:
        check(False, "H4 every row carries a written_up value -- there is no written_up column at all")
    if all(n in head for n in NEW) and all(n in xh for n in NEW):
        xs = [[("" if v is None else str(v)) for v in row] for row in ws.iter_rows(min_row=2, max_row=len(body) + 1, values_only=True)]
        mism = [b[0] for b, x in zip(body, xs) if [b[head.index(n)] for n in NEW] != [x[xh.index(n)] for n in NEW]]
        md_rows = sum(1 for l in md if l.startswith("| ") and l.split("|")[1].strip().isdigit())
        check(not mism and md_rows == len(body) == len(xs),
              f"H5 the three renderings agree: CSV {len(body)} rows, spreadsheet {len(xs)}, markdown {md_rows}; "
              f"{len(mism)} rows whose citation cells differ between CSV and spreadsheet {mism[:5]}")
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
