"""Ingest the 49 saved Pro-Football-Reference NFL Draft Listing pages.

Years 1960-1990 and 2005-2025. THE PRIZE IS 1960-1973: nflverse begins at 1974, so
those fourteen drafts are coverage nothing else in the archive holds.

Columns are read from PFR's own `data-stat` attributes, never from position. The
table is identified by id="drafts"; all 49 files carry it in the open HTML, which
was checked rather than assumed -- PFR comment-wraps many of its tables, and a
parser that only handled the open case would silently return nothing on the others.

Names carry trailing '*' (Pro Bowl) and '+' (All-Pro). Those marks are stripped for
matching, and no honour is derived from them: PFR gives pro_bowls and
all_pros_first_team as their own columns, and reading a count off a punctuation
mark when the count is printed beside it would be inventing a worse version of a
fact already held.
"""
import os, re, csv, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
DIR = "/Users/ryannecci/Documents/pgm3-sources/1979PFR"
SRC_ID = "pfr-draft-listing"
from ingest_nflverse import norm, build_index

CELL = re.compile(r'<t[dh][^>]*data-stat="([^"]+)"[^>]*>(.*?)</t[dh]>', re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)


def text(x):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", x)).strip()


def parse_page(html):
    m = re.search(r'<table[^>]*id="drafts"(.*?)</table>', html, re.S)
    if not m:
        return []
    out = []
    for r in ROW.finditer(m.group(1)):
        cells = {k: text(v) for k, v in CELL.findall(r.group(1))}
        if not cells.get("player") or not cells.get("draft_round"):
            continue
        if not cells["draft_round"].isdigit():
            continue                      # repeated header rows inside the body
        out.append(cells)
    return out


def main(write=True):
    import write_bios as W
    by_name = build_index(W.IDX, W.seasons)
    files = sorted(glob.glob(os.path.join(DIR, "*NFL Draft Listing*.html")))
    claims, unresolved = [], []
    how = collections.Counter(); byyear = collections.Counter(); rows_total = 0
    for f in files:
        y = int(re.search(r"(\d{4}) NFL Draft", os.path.basename(f)).group(1))
        for c in parse_page(open(f, encoding="utf-8", errors="replace").read()):
            rows_total += 1
            nm = re.sub(r"[*+\s]+$", "", c["player"])
            cands = by_name.get(norm(nm), [])
            win = [p for p in cands
                   if (lambda ys: ys and min(ys) - 1 <= y <= max(ys))(
                       [s["year"] for s in W.seasons(W.IDX[p])])]
            pid = win[0] if len(win) == 1 else None
            if not pid:
                how["no_name_match" if not cands else
                    ("ambiguous_namesakes" if len(win) > 1 else "no_career_window")] += 1
                unresolved.append({"source_id": SRC_ID, "name_as_printed": nm, "year": y,
                                   "draft_round": c["draft_round"], "draft_pick": c.get("draft_pick"),
                                   "team": c.get("team"), "IS_NOT_RESOLVED": True})
                continue
            how["resolved"] += 1; byyear[y] += 1
            v = {"year": y, "round": int(c["draft_round"]),
                 "overall_pick": int(c["draft_pick"]) if c.get("draft_pick", "").isdigit() else None,
                 "team": c.get("team", ""), "position_as_printed": c.get("pos", ""),
                 "college_as_printed": c.get("college_id", "")}
            claims.append({"source_record": f"{SRC_ID}#{y}-{c['draft_pick']}",
                           "source_id": SRC_ID, "stated_by": "Pro-Football-Reference",
                           "attribution": [f"{y} NFL Draft Listing, Pro-Football-Reference"],
                           "subject": ["person", pid], "predicate": "pfr.draft_selection",
                           "value": v, "kind": "observed", "observed_at": "held-2026-09"})
    out = {"claims": claims, "unresolved": unresolved,
           "counts": {"files": len(files), "rows_read": rows_total,
                      "resolved": len(claims), "unresolved": len(unresolved),
                      "by_resolution": dict(how),
                      "resolved_by_year": {str(k): v for k, v in sorted(byyear.items())}}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfr-drafts.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    print(f"  files {c['files']}   rows read {c['rows_read']:,}")
    for k, v in sorted(c["by_resolution"].items(), key=lambda x: -x[1]):
        print(f"     {v:6,}  {k}")
    ys = sorted(int(y) for y in c["resolved_by_year"])
    pre = sum(v for y, v in c["resolved_by_year"].items() if int(y) < 1974)
    print(f"  years {min(ys)}-{max(ys)}   resolved before 1974 (new coverage): {pre:,}")
