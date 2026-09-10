"""Gate: the hunting CSV and the hunting markdown are one list, or the run failed.

WHY. `what-to-look-for.csv` exists so the list can be sorted and filtered. A CSV that
has drifted from the document beside it is worse than no CSV: it looks authoritative and
is checked by nobody. The two are written by one run from one `ranked_rows()` call, and
this holds the property on the FILES, so a hand-edited CSV fails too.

SIX PROPERTIES:

  C1  same number of rows.
  C2  same order and the same rank on every row.
  C3  `adds`, `kind` and `what_would_fix_it` are identical, row for row.
  C4  the CSV round-trips: every record has exactly ten fields, and re-reading the file
      returns what was written. A comma or a newline inside a field that was not quoted
      would silently shift every later column.
  C5  ABSENT IS NOT ZERO. No cell holds `n/a`, `None`, `-` or a bare `0` where the
      measurement did not ask the question: a forename row has no fact count, an
      off-the-table club-season has no fact count, an outside-the-span club-season has
      neither a men count nor a fact count.
  C6  the parts recompose the markdown's one string -- for a club-season AND for a
      forename row -- so splitting them into columns did not lose or invent anything.
  C7  A FORENAME ROW CARRIES THE NAME, and nothing else does. It is the one field those
      rows exist for, and the first CSV dropped it: `club` held the club-season key and
      the man himself was only in the markdown's prose, so `P_002717` read as a row about
      APFA|1920|DE1 rather than about Gates. The converse is held too, because a name
      leaking onto a club-season row is the same defect facing the other way.

  python3 src/gate_hunting_csv.py [--selftest]
"""
import os, re, sys, csv, io, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DOCS = os.path.expanduser("~/Dropbox/Football Archive/docs")
MD = os.path.join(DOCS, "what-to-look-for.md")
CSVP = os.path.join(DOCS, "what-to-look-for.csv")
HEADER = ["rank", "adds", "kind", "year", "name", "club", "league", "men_held",
          "facts_missing", "missing_breakdown", "what_would_fix_it"]
NEVER = {"n/a", "N/A", "na", "None", "null", "-", "—"}

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def md_rows(text):
    """The ranked table's rows: | # | adds | kind | gap | held | fix |"""
    out = []
    for line in text.splitlines():
        if not line.startswith("| ") or not re.match(r"^\| \d+ \|", line): continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 6: continue
        out.append({"rank": cells[0], "adds": cells[1].strip("*"), "kind": cells[2],
                    "gap": cells[3], "note": cells[4], "fix": cells[5]})
    return out


def csv_records(raw):
    return list(csv.reader(io.StringIO(raw)))


def recompose(r):
    """The markdown's one string, from the CSV's parts, by the writer's own rules."""
    if r["kind"] == "a name":
        return f'**{r["name"]}** — {r["club"]}'
    year, club, league = r["year"], r["club"], r["league"]
    if not league:
        return f"{year} {club}"
    return f"{year} {club} ({league})"


def x_rows(path):
    """The spreadsheet's list sheet, as the CSV would render it."""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=False)
    ws = wb["The list"]
    rows = [[("" if c.value is None else str(c.value)) for c in r] for r in ws.iter_rows()]
    head = rows[0]
    body = []
    for r in rows[1:]:
        if not r[0] or r[0] == "TOTAL" or str(r[0]).startswith("Empty cells"): break
        body.append(r)
    return head, body, wb


def c8_the_spreadsheet_is_the_same_list(csv_path, x_path):
    """C8 -- THE FOURTH RENDERING MATCHES THE THIRD, row for row.

    The spreadsheet is written from csv_rows() in the same run, so it CANNOT diverge --
    and that is exactly the kind of claim that stops being true the moment someone adds
    a sort or a filter to the writer. Held on the FILES, like every other property here."""
    import csv as _csv
    with open(csv_path, newline="") as fh:
        crows = list(_csv.reader(fh))
    chead, cbody = crows[0], crows[1:]
    xhead, xbody, wb = x_rows(x_path)
    bad = []
    if xhead != chead: bad.append(f"header differs: {xhead} vs {chead}")
    if len(xbody) != len(cbody):
        bad.append(f"row count differs: xlsx {len(xbody)}, csv {len(cbody)}")
    for i, (a, b) in enumerate(zip(xbody, cbody), 1):
        if a[0] != b[0]:
            bad.append(f"row {i}: rank {a[0]!r} vs {b[0]!r}"); break
        if a != b:
            diff = [(chead[j], a[j], b[j]) for j in range(min(len(a), len(b))) if a[j] != b[j]]
            bad.append(f"row {i} differs: {diff[:2]}"); break
    sheets = wb.sheetnames
    if sheets[:3] != ["Start here", "The list", "Typos"]:
        bad.append(f"sheets are {sheets}, expected Start here / The list / Typos")
    ws = wb["The list"]
    if ws.freeze_panes != "A2": bad.append("the header is not frozen")
    if not ws.auto_filter.ref: bad.append("there is no autofilter")
    # the totals must be FORMULAS, not numbers this run happened to produce
    tot = [c for r in ws.iter_rows() for c in r
           if isinstance(c.value, str) and c.value.startswith("=SUM(")]
    if len(tot) != 2: bad.append(f"expected 2 =SUM() totals, found {len(tot)}")
    return bad


def main(argv):
    if "--selftest" in argv: return selftest()
    for p in (MD, CSVP):
        if not os.path.exists(p):
            check(False, f"{os.path.basename(p)} does not exist"); return 1
    md = md_rows(open(MD).read())
    raw = open(CSVP).read()
    rec = csv_records(raw)
    # STOP HERE IF THE SHAPE IS WRONG. Zipping an 11-name header over 10-field records
    # shifts every column and drops the last, and the gate died on a KeyError instead of
    # reporting a stale file. A gate that crashes tells you less than one that fails.
    if not check(bool(rec) and rec[0] == HEADER,
                 f"the header is the {len(HEADER)} declared columns"
                 + ("" if not rec else f" -- found {rec[0]}")):
        print(f"\nHUNTING CSV GATE: {len(FAILS)} FAILURE(S)"); return 1
    rows = [dict(zip(HEADER, r)) for r in rec[1:]]
    print(f"markdown {len(md):,} rows, csv {len(rows):,} rows")

    check(len(md) == len(rows), f"C1 same number of rows ({len(md):,} vs {len(rows):,})")

    n = min(len(md), len(rows))
    bad_rank = [i for i in range(n) if md[i]["rank"] != rows[i]["rank"]]
    check(not bad_rank, f"C2 same order and rank on all {n:,} rows"
          + ("" if not bad_rank else f" -- {len(bad_rank)} differ, first at row {bad_rank[0]+1}"))

    for field, mdk in (("adds", "adds"), ("kind", "kind"), ("what_would_fix_it", "fix")):
        off = [i for i in range(n) if rows[i][field] != md[i][mdk]]
        check(not off, f"C3 `{field}` identical on all {n:,} rows"
              + ("" if not off else
                 f" -- {len(off)} differ, first at row {off[0]+1}: "
                 f"csv {rows[off[0]][field]!r} vs md {md[off[0]][mdk]!r}"))

    widths = collections.Counter(len(r) for r in rec)
    check(set(widths) == {len(HEADER)},
          f"C4 every record has {len(HEADER)} fields ({dict(widths)})")
    out = io.StringIO(); csv.writer(out, lineterminator="\n").writerows(rec)
    check(out.getvalue() == raw, "C4 the file round-trips through csv.reader byte for byte")
    stray = [(i, k) for i, r in enumerate(rows, 1) for k, v in r.items() if "\n" in v or "\r" in v]
    check(not stray, f"C4 no field holds a newline" + ("" if not stray else f" -- {stray[:3]}"))

    junk = [(i, k, v) for i, r in enumerate(rows, 1) for k, v in r.items() if v.strip() in NEVER]
    check(not junk, f"C5 no cell holds a placeholder for absence"
          + ("" if not junk else f" -- {len(junk)}, first {junk[0]}"))
    wrong_zero = []
    for i, r in enumerate(rows, 1):
        if r["kind"] == "a name" and (r["facts_missing"] != "" or r["men_held"] != ""):
            wrong_zero.append((i, "a forename row carries a count"))
        if r["kind"] == "off the table" and r["facts_missing"] != "":
            wrong_zero.append((i, "an off-the-table row carries a fact count"))
        if r["kind"] == "outside the span" and (r["men_held"] != "" or r["facts_missing"] != ""):
            wrong_zero.append((i, "an outside-the-span row carries a count"))
        if r["kind"] == "empty" and r["facts_missing"] != "":
            wrong_zero.append((i, "an empty club-season carries a fact count"))
    check(not wrong_zero, f"C5 absent is empty, not zero"
          + ("" if not wrong_zero else f" -- {len(wrong_zero)}, first {wrong_zero[0]}"))

    missing_name = [i + 1 for i in range(len(rows))
                    if rows[i]["kind"] == "a name" and not rows[i]["name"].strip()]
    stray_name = [i + 1 for i in range(len(rows))
                  if rows[i]["kind"] != "a name" and rows[i]["name"].strip()]
    named = sum(1 for r in rows if r["kind"] == "a name")
    check(not missing_name and not stray_name,
          f"C7 all {named} forename rows carry a name and no other row does"
          + ("" if not (missing_name or stray_name) else
             f" -- {len(missing_name)} forename rows have none {missing_name[:4]}, "
             f"{len(stray_name)} other rows carry one {stray_name[:4]}"))

    off, done = [], collections.Counter()
    for i in range(n):
        want = recompose(rows[i])
        if want is None: continue
        done["a name" if rows[i]["kind"] == "a name" else "club-season"] += 1
        got = md[i]["gap"].replace("`", "")
        if want != got: off.append((i + 1, want, got))
    # SAY HOW MANY WERE COMPARED. A gate that passes because it checked nothing reads the
    # same as one that passes because everything held; RS-G6 spent a week green on that.
    check(not off, f"C6 the parts recompose the markdown's string on "
                   f"{done['club-season']:,} club-season rows and {done['a name']} "
                   f"forename rows" + ("" if not off else f" -- {len(off)} do not, first {off[0]}"))

    # C8 -- the spreadsheet is the same list, held on the FILE like everything else here
    xp = os.path.join(os.path.dirname(CSVP), "what-to-look-for.xlsx")
    if not os.path.exists(xp):
        check(False, "C8 what-to-look-for.xlsx does not exist")
    else:
        bad = c8_the_spreadsheet_is_the_same_list(CSVP, xp)
        check(not bad, f"C8 the spreadsheet is the same {len(rows):,} rows, same order, "
                       f"same rank" + ("" if not bad else f" -- {bad[:2]}"))

    if FAILS:
        print(f"\nHUNTING CSV GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nHUNTING CSV GATE: pass"); return 0


def selftest():
    ok = True
    good = [HEADER, ["1", "a whole team", "empty", "1926", "", "Bethlehem Bears", "EFL",
                     "0", "", "", "Anything, comma and all"]]
    buf = io.StringIO(); csv.writer(buf, lineterminator="\n").writerows(good)
    raw = buf.getvalue()
    for label, text, want_fail in (
            ("C4 a quoted comma round-trips", raw, False),
            ("C4 an unquoted comma shifts the columns",
             raw.replace('"Anything, comma and all"', "Anything, comma and all"), True)):
        rec = csv_records(text)
        failed = set(len(r) for r in rec) != {len(HEADER)}
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    for label, row, want_fail in (
            ("C5 a forename row with a 0 fact count",
             {"kind": "a name", "facts_missing": "0", "men_held": ""}, True),
            ("C5 a forename row with both empty",
             {"kind": "a name", "facts_missing": "", "men_held": ""}, False),
            ("C5 an n/a placeholder",
             {"kind": "empty", "facts_missing": "n/a", "men_held": "0"}, True)):
        failed = (row.get("facts_missing", "").strip() in NEVER
                  or (row["kind"] == "a name" and (row["facts_missing"] or row["men_held"])))
        g = bool(failed) == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    for label, r, want_fail in (
            ("C7 a forename row with no name", {"kind": "a name", "name": ""}, True),
            ("C7 a forename row with one", {"kind": "a name", "name": "Gates"}, False),
            ("C7 a club-season row carrying a name", {"kind": "thin", "name": "Gates"}, True),
            ("C7 a club-season row without one", {"kind": "thin", "name": ""}, False)):
        failed = ((r["kind"] == "a name" and not r["name"].strip())
                  or (r["kind"] != "a name" and bool(r["name"].strip())))
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    for label, r, gap, want_fail in (
            ("C6 parts that recompose", {"kind": "empty", "year": "1926", "club": "X", "league": "EFL"}, "1926 X (EFL)", False),
            ("C6 parts that do not", {"kind": "empty", "year": "1926", "club": "X", "league": "EFL"}, "1926 Y (EFL)", True),
            ("C6 a forename row recomposes", {"kind": "a name", "name": "Gates", "club": "APFA|1920|DE1"}, "**Gates** — APFA|1920|DE1", False)):
        failed = recompose(r) != gap
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected "
              f"{'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
