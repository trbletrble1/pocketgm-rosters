"""Gate: a regenerated hunting document carries the newspaper-citation columns, joined on the club-season.

Ryan, 2026-09-11 and 2026-09-12. The five columns -- written_up, newspaper_citations, cited_with_page, papers,
links -- were added to the three hunting documents by hand, and src/write_hunting_docs.py regenerates all
three. A regeneration that does not know them drops them in silence; one that joins them on the printed
club text loses them whenever the text changes -- 1924 Pottsville, with 21 page-numbered citations, went
from "outside the span" to a held club-season in a day.

This gate RUNS a writer and inspects what it writes. It never writes the real documents: HOME is pointed
at a scratch folder, so `~/Dropbox/Football Archive/docs` resolves inside it, and the sweep's report
folder is linked in read-only so the writer can read it.

  H1  the CSV header carries all five columns
  H2  the spreadsheet's "The list" header carries all five
  H3  the markdown table header carries its four (written up, newspaper citations (with a page), papers, links)
  H4  every row carries a written_up value -- one the sweep's report uses, or the "not in the report" marker
  H5  the three renderings agree row by row: same row count, and the CSV's five cells equal the spreadsheet's
  H6  THE CLUB-SEASON DECIDES: every row whose club-seasons are a row of the sweep's report carries that
      report row's five values exactly, and none of them is marked "not in the report". The report's
      club-seasons are read here from its own club_id and printed keys, each club with its own year --
      not taken from the writer, so the writer's join cannot mark its own work.

  python3 src/gate_hunting_docs_citations.py [--script PATH]   exit 1 = FAIL
"""
import os, re, sys, csv, glob, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
NEW = ["written_up", "newspaper_citations", "cited_with_page", "papers", "links"]
MD_NEW = ["written up", "newspaper citations (with a page)", "papers", "links"]
MARKER = "not in the sweep's per-row report"
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def report():
    per = sorted(glob.glob(os.path.expanduser("~/Dropbox/Football Archive/reports/*-wikipedia-newspaper-citations.csv")))
    rows = list(csv.DictReader(open(per[-1], newline=""))) if per else []
    return (os.path.basename(per[-1]) if per else None), rows


def ident_of(r):
    """A report row's identity, worked out here and not taken from the writer: the season keys it prints in
    brackets when it names a man's club-seasons, else its one (club id, year). Never a pairing of ids with years."""
    ks = frozenset(re.findall(r"\[([^\]|]+\|\d{4}\|[^\]]+)\]", r.get("club") or ""))
    if ks: return ("keys", r.get("name") or "", ks)          # the man AND his keys: several men share one key
    ids = [x for x in (r.get("club_id") or "").split(";") if x]
    if len(ids) == 1 and str(r.get("year") or "").isdigit(): return ("pair", frozenset({(ids[0], int(r["year"]))}))
    return None


def row_ident(r):
    if r.get("keys"): return ("keys", r.get("name") or "", frozenset(r["keys"]))
    if r.get("pairs"): return ("pair", frozenset(r["pairs"]))
    return None


def main():
    script = sys.argv[sys.argv.index("--script") + 1] if "--script" in sys.argv else os.path.join(HERE, "write_hunting_docs.py")
    name, rep = report()
    vocab = {r["written_up"] for r in rep if r.get("written_up")} | {MARKER}
    real_reports = os.path.expanduser("~/Dropbox/Football Archive/reports")
    home = tempfile.mkdtemp(prefix="gate-hunting-docs-", dir=os.environ.get("GATE_SCRATCH") or None)
    docs = os.path.join(home, "Dropbox", "Football Archive", "docs"); os.makedirs(docs)
    os.symlink(real_reports, os.path.join(home, "Dropbox", "Football Archive", "reports"))
    print(f"writer: {script}\nreport: {name} ({len(rep)} rows)\nwriting into scratch: {docs} (the real documents are not touched)")
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
        bad = [r[0] for r in body if r[i] not in vocab]
        check(not bad, f"H4 every row carries a written_up value the report uses, or the marker ({len(body)} rows; {len(bad)} not: {bad[:5]})")
    else:
        check(False, "H4 every row carries a written_up value -- there is no written_up column at all")
    if all(n in head for n in NEW) and all(n in xh for n in NEW):
        xs = [[("" if v is None else str(v)) for v in row] for row in ws.iter_rows(min_row=2, max_row=len(body) + 1, values_only=True)]
        mism = [b[0] for b, x in zip(body, xs) if [b[head.index(n)] for n in NEW] != [x[xh.index(n)] for n in NEW]]
        md_rows = sum(1 for l in md if l.startswith("| ") and l.split("|")[1].strip().isdigit())
        check(not mism and md_rows == len(body) == len(xs),
              f"H5 the three renderings agree: CSV {len(body)} rows, spreadsheet {len(xs)}, markdown {md_rows}; "
              f"{len(mism)} rows whose citation cells differ between CSV and spreadsheet {mism[:5]}")
    # H6 -- in process, on the writer the gate was given, against the report read here.
    by_ident = {}
    for r in rep:
        k = ident_of(r)
        if k: by_ident.setdefault(k, r)
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("writer_under_test", script); W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    rows = W.ranked_rows()
    if hasattr(W, "attach_citations"): W.attach_citations(rows)
    covered = [r for r in rows if row_ident(r) in by_ident]
    wrong = [(r["gap"][:40], (r.get("cite") or {}).get("written_up"), by_ident[row_ident(r)]["written_up"])
             for r in covered if [(r.get("cite") or {}).get(n) for n in NEW] != [by_ident[row_ident(r)][n] for n in NEW]]
    check(bool(covered) and not wrong,
          f"H6 every row whose club-seasons are a report row carries that row's values ({len(covered)} such rows; "
          f"{len(wrong)} do not: {wrong[:4]})")
    # H7 -- A REPORT ROW FEEDS AT MOST ONE ROW. Two rows taking one report row's values means one of them borrowed
    # them: 1926 `BKN`, an off-the-table code two clubs carry, was once resolved to one of those clubs and took
    # that club-season's citations.
    fed = {}
    for r in rows:
        k = row_ident(r)
        if k in by_ident: fed.setdefault(k, []).append(r["gap"][:40])
    shared = {str(k[1:])[:80]: v for k, v in fed.items() if len(v) > 1}
    check(not shared, f"H7 no report row feeds two rows ({len(shared)} do: {list(shared.items())[:3]})")
    pot = [r for r in rows if "Pottsville Maroons" in str(r.get("club")) and str(r.get("year")) == "1924"]
    for r in pot:
        print(f"         1924 Pottsville: kind '{r['kind']}', club-seasons {r.get('pairs')}, "
              f"written_up {(r.get('cite') or {}).get('written_up')}, citations {(r.get('cite') or {}).get('newspaper_citations')} "
              f"({(r.get('cite') or {}).get('cited_with_page')} with a page), joined on {r.get('cite_join')}")
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
