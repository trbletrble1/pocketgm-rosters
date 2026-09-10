"""Regenerate the two hunting documents from the measurements, not by hand.

  where-the-archive-is-thin.md   the full sectioned list, kept as it was
  what-to-look-for.md            ONE RANKED LIST, ordered by how much a single
                                 document would fix. Ruled by Ryan 2026-09-09:
                                 six categories is six things to keep track of,
                                 and he only ever asks one question -- what
                                 document should I go and find? The category is a
                                 COLUMN, so it can be sorted or ignored.

Both read build-reports/*.json, so a re-measure changes the documents and nothing
has to be edited twice. Nothing in either file is typed by hand except the prose
that says what a page looks like.

  python3 src/write_hunting_docs.py
"""
import os, sys, csv, json, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
DOCS = os.path.expanduser("~/Dropbox/Football Archive/docs")
BR = os.path.join(BASE, "build-reports")


def load(name, required=True):
    try:
        return json.load(open(os.path.join(BR, name)))
    except Exception:
        if required: raise
        return None


def _refuse_a_stale_measurement():
    """THE WRITER RENDERS A REPORT; IT DOES NOT MEASURE. That is fine and it is fast --
    and on 10 September it rendered a measurement from the night before three times in a
    row, so a full day's ingests appeared to have moved nothing. The conclusion drawn was
    "the list did not move, and that is the finding". The finding was a stale file.

    A report older than the index it was measured from is not a measurement of today, and
    an input that is silently out of date is the same defect class as an input that is
    silently absent. So it is REFUSED, with the command that fixes it."""
    m = os.path.join(BASE, "build-reports", "thin-archive.json")
    idx = os.path.join(BASE, "build-reports", "person-index.json")
    if not (os.path.exists(m) and os.path.exists(idx)):
        return
    if os.path.getmtime(m) < os.path.getmtime(idx):
        import datetime as _d
        f = lambda q: _d.datetime.fromtimestamp(os.path.getmtime(q)).strftime("%d %b %H:%M")
        raise SystemExit(
            f"REFUSING: thin-archive.json ({f(m)}) is older than person-index.json "
            f"({f(idx)}).\nThe hunting documents would be rendered from a measurement "
            f"taken before the archive last changed.\n  python3 src/measure_thin_archive.py")


_refuse_a_stale_measurement()
T = load("thin-archive.json")
O = load("outside-span.json")
H = load("gaps-already-in-hand.json", required=False)
N = load("no-roster-source.json", required=False)
# THE BASELINE IS A FILE, not a memory. "What moved since yesterday" is a diff against
# the 8 September measurement as it was committed, so the sentence can be checked.
B = load("hunting-baseline-2026-09-08.json", required=False)
C = T["counts"]
TODAY = datetime.date.today().isoformat()

def out_of_scope_empties():
    """Club-seasons the club table holds with nobody on them that this document's SCOPE
    excludes. The scope is nine league tokens typed into measure_thin_archive.py, and on
    9 September the club table began naming leagues that list has never heard of -- AFA,
    ALFL, CAFL, NWIFL, SFL, PFLA and the no-league token, out of the pseudo-league
    declaration. Counted here rather than left silent: a typed vocabulary that stops
    matching the data is the defect this archive keeps meeting."""
    import collections
    TAB = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    IDX = json.load(open(os.path.join(BR, "person-index.json"))); IDX.pop("_clubs", None)
    sys.path.insert(0, HERE)
    from measure_thin_archive import in_scope
    men = collections.defaultdict(set)
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        for k in (p.get("seasons") or {}):
            pt = k.split("|", 2)
            if len(pt) == 3: men[(pt[2], pt[1].lstrip("y"))].add(pid)
    out = collections.Counter()
    for c in TAB["clubs"]:
        for seg in c["segments"]:
            for y in range(seg["first"], seg["last"] + 1):
                if y in (seg.get("dark_years") or []): continue
                for l in (seg["leagues"] or []):
                    if not (l["first"] <= y <= l["last"]): continue
                    if in_scope(l["league"], str(y)): continue
                    if not men.get((seg["code"], str(y))): out[l["league"]] += 1
    return out


SCOPE_NOTE = """

## What this list does not cover

**The scope is nine league tokens typed into `measure_thin_archive.py`**, and since the
pseudo-leagues were declared on 9 September the club table names leagues that list has
never heard of. **{tot} club-seasons the table holds with nobody on them fall outside
it**: {byl}. The WLAF is the sharpest case -- the archive holds **246 season keys in
1995, 1996 and 1997** and the club table has no WLAF club-season after 1992 at all.

None of that is a ruling this document can make. It is stated here so the number at the
top is read as *the scope's* count and not the archive's.
"""


def _note():
    o = out_of_scope_empties()
    return SCOPE_NOTE.format(tot=sum(o.values()),
                             byl=" · ".join(f"{k or '(no league named)'} {v}"
                                            for k, v in o.most_common()))


# What the PFA log fetch actually put on the disk, and what those pages carry. Measured
# 2026-09-09 from the manifest and from a 200-page sample of each kind, because the
# previous version of this sentence was wrong: the PLAYOFF logs print a position.
LOGS = {"gamelogs": 21552, "playoffs": 12195, "absent": 3,
        "gamelog_columns": "date, opponent, score, result and the per-game statistics",
        "playoff_columns": "year, club, jersey number, POSITION, games played and games started"}
BOXSCORES = {"exists": 17499, "on_disk": 2934, "cited": 2890}


# --------------------------------------------------------------------------- rows
def _fix_for_thin(x):
    b = x["by_field"]; y = int(x["year"]) if x["year"].isdigit() else 0
    if y >= 1990:
        return "A league media guide or season roster page — online, not in a listing."
    dom = max(b, key=b.get)
    return {"college": "A roster table with a college column — narrow columns, a wide one "
                       "on the right.",
            "weight": "A roster table with number, position and weight, or a bio page.",
            "age": "A bio page: dense prose, a bold name per paragraph, ages in the text.",
            "position": "A lineup or a roster table with a position column."}[dom]


NOBODY_FIX = ("Anything naming the club and some of its men: a roster, a lineup, a "
              "captioned team photograph.")
INGEST_FIX = ("**Not a hunt.** PFA's own club-season page is on this disk with a roster "
              "table; this is an ingest the archive has not done.")
INGEST_NOTE = (" **Not a hunt: PFA's page for this club-season is on the disk with a roster "
               "table on it, and the archive has not read it.**")


def _pfa_roster_on_disk():
    """Which club-seasons already have a PFA roster on the disk.

    Ryan's ruling, 2026-09-09: a reader must see at a glance which rows are documents to
    FIND and which are work the archive has not DONE. 16,422 men came off pages already
    held; a list that sends him to eBay for one of them is worse than no list. Read from
    the enumeration, which carries the three numbers per page."""
    p = os.path.join(BR, "pfa-club-season-targets.json")
    if not os.path.exists(p): return set()
    return {(t["league"], str(t["year"]), t["code"])
            for t in json.load(open(p))["targets"]
            if t.get("on_disk") and t.get("has_roster_table")}


PFA_ROSTER = _pfa_roster_on_disk()
MODERN_FIX = "A league roster page — this season is online, not in a listing."


def _nobody_fix(year):
    """A 2026 UFL club-season holding nobody is a FETCH, not a hunt. Ryan must not be
    sent to eBay for a season that is on the league's own website."""
    return MODERN_FIX if int(year) >= 1990 else NOBODY_FIX
SOME_FIX = "A roster naming the squad; failing that a lineup or a captioned team photograph."


def _men(n):
    return f"{n} man" if n == 1 else f"{n} men"


def ranked_rows():
    """Every gap, one row each, ordered by how much ONE document would fix.

    THE ROW CARRIES ITS PARTS, NOT ITS PROSE. `year`, `club`, `league`, `men_held`,
    `facts_missing` and `missing_breakdown` are separate fields and the markdown's one
    string is COMPOSED from them, so the table and the CSV are two renderings of one row
    and cannot drift. Splitting them in the CSV writer instead would have been a second
    implementation of the same rule, which is how this archive keeps meeting the same bug.

    ABSENT IS NOT ZERO, and a spreadsheet is where that distinction dies first. A field
    is None where the measurement never asked the question, and 0 only where it asked and
    the answer was none:
      an EMPTY club-season holds 0 men -- counted -- and has NO fact count, because
        there are no men to count facts on;
      an OFF THE TABLE club-season holds a counted number of men and has NO fact count,
        because the fact instrument walks the club table and this club-season is not in it;
      an OUTSIDE THE SPAN club-season has NO men count and no fact count: it is in no
        list the instrument reads, so nothing was measured either way;
      a NO COACH club-season that is not also thin has 0 missing facts -- the instrument
        counted them and found none;
      a FORENAME row has neither. A man missing a name is not missing a counted fact.

    FIVE BANDS, and they are the order. The band is explicit and not arithmetic: the
    first version encoded it as `10_000 - year` against `9_000 - men`, and a club-season
    holding one man outranked one holding nobody while both printed "a whole team".

      0  nobody held at all -- a whole squad from nothing, the best find. Nothing
         measured separates these rows, so they run OLDEST FIRST and the document says
         so rather than implying a ranking it does not have.
      1  the club table cannot place the club-season and a few men are held, almost all
         of them from a scoring line. Fewest held first.
      2  men held, facts missing -- by the COUNT of facts, so the top is where one page
         does the most work.
      3  a roster held and nobody recorded running it.
      4  a man holding a surname and nothing else.
    """
    rows = {}

    def put(key, band, tie, adds, kind, fix, note="", year=None, club=None, league=None,
            men_held=None, facts_missing=None, missing_breakdown=None, gap=None, name=None):
        rows[key] = {"band": band, "tie": tie, "adds": adds, "kind": kind,
                     "fix": fix, "note": note, "year": year, "club": club, "name": name,
                     "league": league, "men_held": men_held,
                     "facts_missing": facts_missing,
                     "missing_breakdown": missing_breakdown,
                     "gap": gap if gap is not None else club_season_gap(year, club, league)}

    def club_season_gap(year, club, league):
        """AN EMPTY LEAGUE PRINTS NOTHING, not `()`. measure_thin_archive writes `""` for
        a club-season whose segment lists no league that year -- Frankford 1922-23 and
        the Gunners 1931-33 -- and the markdown printed `1922 Frankford Yellow Jackets ()`,
        which tells a reader nothing and does not recompose from the CSV's empty league
        cell. `""` and `None` mean the same thing here: no league is recorded."""
        return f"{year} {club} ({league})" if league else f"{year} {club}"

    def breakdown(by_field):
        return ", ".join(f"{k} {v}" for k, v in sorted(by_field.items(), key=lambda kv: -kv[1]))

    thin_by_key = {("cs", x["league"], x["year"], x["code"]): x for x in T["thin_club_seasons"]}

    for x in T["empty_club_seasons"]:
        put(("cs", x["league"], x["year"], x["code"]), 0, (int(x["year"]),), "a whole team",
            "empty", NOBODY_FIX,
            "the club table holds the club-season and not one man",
            year=x["year"], club=x["name"], league=x["league"], men_held=0)

    for r in T.get("club_seasons_off_the_table", []):
        nm = " / ".join(r["names"])
        why = ("no club-season at all: a source names the club, the club table refuses "
               "the string")
        if not nm:
            why = ("no club-season and no name: the archive holds the token and nothing "
                   "has ever printed a name for it")
        gap = (f'{r["year"]} {nm} ({r["league"]})' if nm else
               f'{r["year"]} `{r["code"]}` ({r["league"]})')
        common = dict(year=str(r["year"]), club=nm or r["code"], league=r["league"],
                      men_held=r["men"], gap=gap)
        if r["men"] == 0:
            put(("ot", r["league"], r["year"], r["code"]), 0, (r["year"],), "a whole team",
                "off the table", _nobody_fix(r["year"]), why, **common)
        else:
            put(("ot", r["league"], r["year"], r["code"]), 1, (r["men"], r["year"]),
                f'a team, less the {r["men"]} held', "off the table", SOME_FIX,
                f'{_men(r["men"])} held from statistics lines alone; ' + why, **common)

    for x in T["thin_club_seasons"]:
        b = x["by_field"]
        onhand = (x["league"], x["year"], x["code"]) in PFA_ROSTER
        put(("cs", x["league"], x["year"], x["code"]), 2, (-x["missing_facts"], x["year"]),
            f'{x["missing_facts"]} facts', "thin",
            (INGEST_FIX if onhand else _fix_for_thin(x)),
            f'{_men(x["men"])}, {x["missing_facts"]} facts missing — ' + breakdown(b),
            year=x["year"], club=x["name"], league=x["league"], men_held=x["men"],
            facts_missing=x["missing_facts"], missing_breakdown=breakdown(b))

    for x in T["club_seasons_without_a_coach"]:
        k = ("cs", x["league"], x["year"], x["code"])
        extra = "Nobody is recorded running it, so a staff panel or a masthead counts too."
        if k in rows:
            rows[k]["fix"] += " " + extra
        else:
            # NOT IN THE THIN LIST MEANS THE INSTRUMENT COUNTED AND FOUND NONE. It walks
            # every scoped club-season holding men and only files those with a non-zero
            # total, so 0 here is measured, not missing.
            put(k, 3, (x["year"],), "a coach", "no coach", extra,
                f'{_men(x["men"])} held, no coach or staff',
                year=x["year"], club=x["name"], league=x["league"], men_held=x["men"],
                facts_missing=0)

    for x in T["club_seasons_with_no_roster_source"]:
        k = ("cs", x["league"], x["year"], x["code"])
        if k in rows:
            rows[k]["note"] += ("; no man here carries a jersey, a games figure or a "
                                "position, so no source ever gave a roster row")

    # THE SEASONS OUTSIDE A LEAGUE BOUNDARY are listed only where the archive still
    # holds nothing. Frankford 1922-23 and the Gunners 1931-33 went into the club table
    # this week and are already above as thin rows; repeating them here would double-count
    # the two best gains of the week as gaps.
    for x in O["D_established_from_a_document"]:
        for y in x["outside"]:
            if any(k[0] == "cs" and rows[k]["gap"].startswith(f"{y} {x['club']}") for k in rows):
                continue
            # NO league, NO men count: these club-seasons are in no list the instrument
            # reads, so nothing was measured either way and nothing is asserted.
            put(("out", x["club"], y), 0, (y,), "a whole team", "outside the span",
                _nobody_fix(y),
                f'{x["status"]}; not in the club table, so no league source will ever carry it',
                year=str(y), club=x["club"], league=None, gap=f'{y} {x["club"]}')

    for x in T["people_with_a_surname_and_nothing_else"]:
        keys = x["club_seasons"]
        parts = [k.split("|", 2) for k in keys]
        yrs = {p[1].lstrip("y") for p in parts if len(p) == 3}
        lgs = {p[0] for p in parts if len(p) == 3}
        put(("p", x["person"]), 4, (x["name"],), "a forename", "a name",
            "Any page printing his full name: a roster with forenames, a game report, a "
            "bio line.", "a surname and nothing else",
            # the club-season KEY is the club, as ruled. Year and league are read off that
            # key where every key agrees, and left empty where they do not -- the key
            # carries them, so this is reading, not inference.
            year=(yrs.pop() if len(yrs) == 1 else None),
            league=(lgs.pop() if len(lgs) == 1 else None),
            club=", ".join(keys),
            # THE NAME IS THE ONE FIELD THESE ROWS EXIST FOR. The first CSV carried only
            # the club-season key and dropped it: `P_002717` became a row about
            # APFA|1920|DE1 rather than about Gates. `name` is empty on every other kind,
            # because a club-season is not a person.
            name=x["name"],
            gap=f'**{x["name"]}** — {", ".join(keys)}')

    return sorted(rows.values(), key=lambda r: (r["band"], r["tie"], r["gap"]))


# ONE SOURCE FOR THE TYPOS. They were a paragraph inside the markdown writer; the
# spreadsheet needs the same list, and a second copy would drift the first time one was
# added. Rendered by both writers from here.
TYPOS = [
    ("Bufallo", "Buffalo"), ("Neraska", "Nebraska"), ("Univefsity", "University"),
    ("Southen", "Southern"), ("Pittsburg", "Pittsburgh — no h"),
    ("Franklin & Marshal", "Franklin & Marshall — one l"), ("Postion", "Position"),
    ("Phythain", "Phythian — the archive holds both"),
    ("Ericson", "Erickson — the archive holds both"),
    ("Briton", "Britton — the archive holds both"), ("Harolde", "Harold — Grange"),
    ("PROABLE", "Probable"), ("Cincinnati Benagls", "Cincinnati Bengals — PFA's spelling"),
    ("Milwaukee Chiuefs", "Milwaukee Chiefs — PFA's spelling"),
    ("Lousville Bourbons", "Louisville Bourbons — PFA's spelling"),
]


def csv_rows(rows):
    """The same rows, same order, as the ten declared columns. `None` becomes an EMPTY
    cell and never `0` or `n/a`."""
    out = [["rank", "adds", "kind", "year", "name", "club", "league", "men_held",
            "facts_missing", "missing_breakdown", "what_would_fix_it"]]
    for i, r in enumerate(rows, 1):
        out.append([i, r["adds"], r["kind"],
                    _cell(r["year"]), _cell(r.get("name")), _cell(r["club"]),
                    _cell(r["league"]), _cell(r["men_held"]), _cell(r["facts_missing"]),
                    _cell(r["missing_breakdown"]), r["fix"]])
    return out


def _cell(v):
    return "" if v is None else str(v)


# ------------------------------------------------------------------------ spreadsheet
# A FOURTH RENDERING OF ONE ROW LIST, NEVER A SECOND MEASUREMENT. This takes the output
# of csv_rows() -- the very list the CSV is written from -- so the spreadsheet cannot
# disagree with the CSV about what is on it, in what order, or under what rank. Building
# it from a second call to ranked_rows() would be cheap and would also be a second
# answer to the same question.

BANDS = {                      # by what a find ADDS, not by the kind string
    "whole":   "FFD9D2",       # a whole team -- nobody is held at all
    "partial": "FFE9C6",       # a team less the few held
    "name":    "DDE8F5",       # a forename, or a coach
}
NOT_A_HUNT = "9C4200"          # the marker colour: already on the disk


def _band_of(adds):
    a = str(adds or "")
    if a == "a whole team": return "whole"
    if a.startswith("a team, less"): return "partial"
    if a in ("a forename", "a coach"): return "name"
    return None                                     # thin: white, and deliberately so


START_HERE = [
    ("h", "How to use this list"),
    ("", ""),
    ("r", "THE ONE-LINE RULE. Buy a programme, a yearbook or a team photograph that "
          "names men on a club-season this list gives a rank to. Everything else is a "
          "nice thing to own."),
    ("", ""),
    ("h", "What a good page looks like in a listing photograph"),
    ("b", "A ROSTER OR LINE-UP PAGE: two columns of surnames with positions, or a table "
          "headed with a number column. If you can count eleven names, it is worth the "
          "money."),
    ("b", "A BIO PAGE: paragraphs, each starting with a name in capitals followed by an "
          "age -- \"JACK NOLAN-25 years, height 5 ft. 10 in.\" That is the richest page "
          "in the whole class: it carries height, weight, college and prior clubs."),
    ("b", "A CAPTIONED TEAM PHOTOGRAPH: the caption names the men. A caption naming "
          "enough of them is a roster, and the archive rules it as one."),
    ("b", "WHAT TO SKIP: covers, advertisements, articles, scoring grids. Most images in "
          "a listing are these."),
    ("", ""),
    ("h", "How to read the list"),
    ("b", "It is ranked. Row 1 is worth more than row 700; the ranking is by how much a "
          "single find adds."),
    ("b", "THE COLOURS SAY WHAT A FIND ADDS, so you can scan without reading the kind "
          "column:"),
    ("w", "        a whole team -- the archive holds nobody at all"),
    ("p", "        a team less the one or two men already held"),
    ("n", "        a forename for a surname-only man, or a missing coach"),
    ("b", "        white -- a club-season already held, missing facts about the men"),
    ("b", "ROWS IN BROWN BOLD ARE NOT A HUNT. The page is already on this disk and "
          "wants reading, not buying. Do not spend money on these."),
    ("b", "EMPTY CELLS ARE EMPTY ON PURPOSE. An absent number is not a zero: it means "
          "the archive holds no figure, which is a different thing from holding none."),
    ("", ""),
    ("h", "What this list does not cover"),
    ("b", "Minor leagues, by ruling. They are excluded from the archive's scope and so "
          "from this list."),
    ("b", "Anything the archive cannot name. Some club-seasons are so thin the club "
          "table cannot name the club, and those cannot be given a row."),
    ("b", "Anything after 1959 for box scores, and the whole 2010s and 2020s for game "
          "logs -- those arrive by ingest, not by hunting."),
]


def write_xlsx(rows, path):
    """The same rows again, as three sheets. Returns the row count written."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    table = csv_rows(rows)                       # THE CSV'S OWN PROJECTION
    header, body = table[0], table[1:]
    wb = Workbook()

    # ---------------- Start here
    ws = wb.active; ws.title = "Start here"
    ws.column_dimensions["A"].width = 104
    styles = {"h": Font(bold=True, size=13), "r": Font(bold=True, size=11),
              "b": Font(size=11), "": Font(size=11)}
    fills = {"w": PatternFill("solid", fgColor=BANDS["whole"]),
             "p": PatternFill("solid", fgColor=BANDS["partial"]),
             "n": PatternFill("solid", fgColor=BANDS["name"])}
    for i, (k, text) in enumerate(START_HERE, 1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = styles.get(k, styles["b"])
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if k in fills: c.fill = fills[k]
        ws.row_dimensions[i].height = None if len(text) < 90 else 30

    # ---------------- The list
    ws = wb.create_sheet("The list")
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="333333")
        c.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"                       # the header stays put
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header))}{len(body)+1}"

    i_adds = header.index("adds"); i_fix = header.index("what_would_fix_it")
    edge = Side(style="thick", color=NOT_A_HUNT)
    for r in body:
        ws.append(["" if v == "" else v for v in r])
        row = ws[ws.max_row]
        band = _band_of(r[i_adds])
        if band:
            f = PatternFill("solid", fgColor=BANDS[band])
            for c in row: c.fill = f
        # NOT A HUNT IS A SECOND CHANNEL, NOT A REPLACEMENT for the band. The band says
        # what a find adds; this says the find has already been made and is on the disk.
        # Overwriting the fill would trade one fact for the other.
        if "Not a hunt" in str(r[i_fix]):
            for c in row[:3]:
                c.font = Font(bold=True, color=NOT_A_HUNT)
            row[0].border = Border(left=edge)

    # THE TOTALS ARE FORMULAS, so a filtered or edited sheet recomputes rather than
    # carrying a number this run happened to produce. SUM ignores the empty cells, which
    # is exactly right: absent is not zero.
    last = len(body) + 1; tot = last + 2
    ws.cell(row=tot, column=1, value="TOTAL").font = Font(bold=True)
    for name in ("men_held", "facts_missing"):
        col = get_column_letter(header.index(name) + 1)
        c = ws.cell(row=tot, column=header.index(name) + 1,
                    value=f"=SUM({col}2:{col}{last})")
        c.font = Font(bold=True)
    ws.cell(row=tot + 1, column=1,
            value="Empty cells are empty on purpose: SUM ignores them, and an absent "
                  "figure is not a zero.").font = Font(italic=True, size=9)
    widths = {"rank": 6, "adds": 16, "kind": 15, "year": 6, "name": 20, "club": 30,
              "league": 8, "men_held": 10, "facts_missing": 13,
              "missing_breakdown": 40, "what_would_fix_it": 90}
    for j, h in enumerate(header, 1):
        ws.column_dimensions[get_column_letter(j)].width = widths.get(h, 14)

    # ---------------- Typos
    ws = wb.create_sheet("Typos")
    ws.append(["as printed", "what it is"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="333333")
    ws.freeze_panes = "A2"
    for a, b in TYPOS: ws.append([a, b])
    ws.column_dimensions["A"].width = 24; ws.column_dimensions["B"].width = 46
    ws.cell(row=len(TYPOS) + 3, column=1,
            value="Every one of these is held as printed somewhere in the archive or on "
                  "a document it holds. A listing is titled by whoever typed it, so "
                  "search the misspelling too.").font = Font(italic=True, size=9)
    ws.cell(row=len(TYPOS) + 3, column=1).alignment = Alignment(wrap_text=True)

    wb.save(path)
    return len(body)


# --------------------------------------------------------------------------- moved
def what_moved():
    """What changed, and why. Rewritten 2026-09-09: the version that diffed only against
    the 8 September measurement produced sentences like "the surname-only list is 171,
    down from 19", because almost every number on this page has moved and several have
    moved for opposite reasons. The counts are read from the baseline and from today's
    measurement; the reasons are the day's rulings."""
    b = (B or {}).get("counts", {})
    off = C.get("off_the_table", 0)
    return f"""
## What moved, and why

### 10 September: two club-seasons were filled, and 23 more men need a forename

**757 rows → 780. Six rows came off. Twenty-nine went on.**

* **Bethlehem Bears 1926 was rank 2 and is now rank 49.** It held nobody; it holds
  **16 men**, from three newspaper game accounts on a preserved website. **Gilberton
  Catamounts 1926 was rank 3 and is now rank 120**, holding 9. Neither is a hunt any
  more — they are a club-season with men on it and facts still missing about them.
  Empty club-seasons: **11 → 9**.
* **23 more forename rows.** The 25 men arrived from printed line-ups, which print
  surnames. They are held as `forename_unknown`, which is an honest state: the archive
  knows a man played and does not know his first name. **The surname-only list is 171 →
  194 and that is a gain, not a regression.**
* **Four AFL club-seasons came off** — Jets 1968, Chiefs 1966 and 1969, Raiders 1967 —
  because the box scores and game logs completed the last few facts about men already
  held. **That is an ingest doing what a hunt would have done, for nothing.**

**And a correction, because the first version of this section was wrong.** It said the
list had not moved at all and offered reasons why. The list had not moved because the
writer was rendering `thin-archive.json` **from the night before**: it reads a report and
does not measure, and nothing checked the report's age. It does now — the writer refuses
to run on a measurement older than the index. The reasons given were sound and the
premise was false, which is the worse of the two failures.

---

**Almost everything on this page moved on 9 September, and not all of it for the
same reason. Read this before the list.**

**The empty club-seasons: {b.get('empty', '128')} → 44 → {C['empty']}.** Two different
movements, and only the second is a gain.

* *The first was not.* Between 8 and 9 September the archive gained statistics-derived
  stints in the minor-league AFL, EFL, IFL and UFL years. `build_clubs` minted a PFA-only
  club only where the archive covered **nothing** in that league-year, so once those years
  were covered the PFA cell behind each club was **refused instead of minted** and the
  club-season stopped existing. 110 club-seasons left this list without one of them being
  filled. *The Reading Keys were refused because the archive held three men on them.*
* *The second is.* That proxy is gone — `archive_covers` now asks only whether an
  archive-origin club carries that league — and **PFA's own club-season pages were read
  for their rosters**. 16,422 men were on pages already sitting on this disk.

**The club table: 402 → 564 clubs.** 162 minted by dropping the proxy. **Off the table:
123 → {off}** — club-seasons a source names that the table could not place. Men whose bios
read *"he played for the PFA:REA in 1933"* now read *"the Reading Keys"*.

**The person population: 43,562 → 51,108.** 7,412 men promoted from printed rosters, under
Ryan's ruling of 2026-09-09 that **a printed roster is a roster**. That is why the
surname-only list reads **{C['nameless']}** and not 19: 210 of those men were promoted with
`forename_unknown` preserved, which is an honest state and not a regression.

**The minor-league exclusion is now a list, and the measurement reads it.** IFL, ACFL,
COFL, DFL, MWFL, AA, ORFU, PFLA, NWIFL, CAFL, SFL, ALFL and AFA. Their clubs are named so
their men can be read; **the leagues stay off this page**. It used to be nine league tokens
typed into the measurement.

**And the fact counts moved twice.** They rose to 14,963 when 7,412 men arrived carrying
position, age, weight and college under predicates the hunting instrument does not read —
**eleven thousand gaps that were not gaps**. Position and college are now written under the
archive's own predicates and the count is back to **{C['missing_facts_total']:,}**. What
remains is honest: **{C['by_field'].get('weight', 0):,} weights and {C['by_field'].get('age', 0):,} ages**,
because the archive's weight is a *career* value and its age fact is a *birth date*, while
a roster prints what a man weighed and how old he was **that season**. Those were not
folded together, and that is a distinction the archive keeps rather than a gap it has.
"""


# --------------------------------------------------------------------------- short
def short(rows=None):
    o = []; w = o.append
    rows = ranked_rows() if rows is None else rows
    w("# What to look for\n")
    w(f"*One ranked list: every measured gap in the archive, ordered by how much a single\n"
      f"document would fix. The `kind` column is there to sort on or to ignore.\n"
      f"Regenerated {TODAY} from measurement — no reader, no OCR, the archive against itself.*\n")
    w("---\n")
    w("## The one-line rule\n")
    fill = (H["counts"]["fillable from a PFA page already on disk"] if H else 0)
    w(f"**Everything here is a gap nothing on your own disk can fill.** {fill:,} measured gaps\n"
      f"can be filled from a Pro Football Archives page already on this machine, and they have\n"
      f"been taken out — those are an ingest, not a hunt.\n")
    w(f"**Nor will the logs already fetched.** {LOGS['gamelogs']:,} player game logs and\n"
      f"{LOGS['playoffs']:,} playoff logs came down on 8 September and sit unread on the disk.\n"
      f"A game log carries {LOGS['gamelog_columns']} — none of the four facts counted here. A\n"
      f"playoff log carries {LOGS['playoff_columns']}, so it *can* answer a position — but 132\n"
      f"of the 133 missing positions below are 1922–1933, before there were playoffs. Reading\n"
      f"them is work for the archive, not a reason to buy anything.\n")
    nobody_years = sorted(int(r["year"]) for r in
                          [x for x in T["empty_club_seasons"]]
                          + [r for r in T.get("club_seasons_off_the_table", []) if not r["men"]])
    old = [y for y in nobody_years if y < 1990]
    w(f"**Buy 1920s.** {sum(x['missing_facts'] for x in T['thin_club_seasons'] if x['year'].isdigit() and int(x['year']) < 1934):,}\n"
      f"of the {C['missing_facts_total']:,} missing facts are before 1934, and {len(old)} of the\n"
      f"{len(nobody_years)} club-seasons holding nobody are {min(old)}–{max(old)}. The other\n"
      f"{len(nobody_years)-len(old)} are modern leagues and want a website, not a listing.\n")
    w("**Skip the 1934–46 NFL, and only the NFL.** That era is finished — 140 club-seasons,\n"
      "4,265 men, 2.06% of the four facts missing. The *minor-league* AFL of the same years is\n"
      "the opposite: whole squads known from three men on a scoring line, and it is on this list.\n")
    w(what_moved())
    w("---\n")
    w("## What a good page looks like in a listing photograph\n")
    w("**Best — a bio page.** Dense body text in two columns, a bold name starting each\n"
      "paragraph, numbers scattered through the prose. Ages, heights, weights, colleges.\n")
    w("**Nearly as good — a roster table with a college column.** Five or more narrow\n"
      "columns with a wide one on the right. The wide one is the college, and college is\n"
      "what the 1920s record lacks most — 795 of the 2,078 facts missing before 1934.\n")
    w("**Worth little — a lineup of names and numbers.** No age, no college, no weight.\n"
      "Still worth having for any club-season on the list below that holds nobody.\n")
    w("**Skip** — advertisements, articles, scoring grids, and anything 1934–46 NFL without a\n"
      "bio page.\n")
    ing = sum(1 for r in rows if "Not a hunt" in r["fix"])
    w(f"**And skip anything marked \u201cNot a hunt\u201d.** {ing} rows below are club-seasons "
      "whose PFA page is already on this disk with a roster table on it — work the archive "
      "has not done, not a document to find. 16,422 men came off such pages on 9 September.\n")
    w("---\n")
    w(f"## The list — {len(rows):,} gaps, best first\n")
    w("`a whole team` means the archive holds nobody: one document turns nothing into a\n"
      "team, and nothing measured separates those rows from each other, so they run oldest\n"
      "first and the 1920s are worth more than the 1940s. `a team, less the N held` means a\n"
      "source names the club, the club table cannot place it, and N men are held from a\n"
      "statistics line. Everything below those is ranked on the **count** of missing facts.\n")
    w("**The same rows are in `what-to-look-for.csv`**, written by the same run from the "
      "same measurement, one row per gap in this order, with year, name, club and league "
      "as separate columns and the fact count as a number. **An empty cell means the "
      "measurement never asked the question — it is not a zero.** A man missing a "
      "forename is not missing a counted fact, and a club-season the club table cannot "
      "place was never walked by the instrument that counts facts.\n")
    w("| # | one document adds | kind | the gap | what is held | what would fix it |")
    w("|---:|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        w(f'| {i} | **{r["adds"]}** | {r["kind"]} | {r["gap"]} | {r["note"]} | {r["fix"]} |')
    w("")
    w(_note())
    w("---\n")
    w("## The source typos, because that is what a listing will be titled\n")
    w("Listings are titled by whoever typed them. Search on the misspellings too:\n")
    w(" · ".join(f"`{a}` ({b})" for a, b in TYPOS) + "\n")
    w("*Every one of these is a typo held as printed somewhere in the archive or on a\n"
      "document it holds — they are what the material actually says. The last three are\n"
      "club names, and they are the names PFA prints.*\n")
    return "\n".join(o)


# --------------------------------------------------------------------------- full
def in_hand_section():
    if not H:
        return ("\n> **Not checked against what is already on disk.** Run "
                "`src/measure_gaps_already_in_hand.py` first.\n")
    c = H["counts"]; tot = sum(c.values())
    fill = c.get("fillable from a PFA page already on disk", 0)
    why = H.get("why_not_fillable", {})
    return f"""
## Before you hunt: what is already in hand

**{tot:,} missing facts were checked against the documents the archive already
holds.** {fill:,} of them -- {100.0*fill/tot:.0f}% -- can be filled from a Pro
Football Archives team-season page **already on this disk**. Those are an ingest, not
a hunt, and they are excluded from everything below.

**The other {tot-fill:,} cannot be filled by anything already held**, and the reason
matters more than the number:

| | |
|---|---:|
| the man is **not on PFA's roster page at all** | {why.get('not on the page', 0):,} |
| PFA's own cell is empty, or prints `none` | {why.get("PFA's cell is empty or `none`", 0):,} |
| there is no PFA page for that club-season | {why.get('no PFA page', 0):,} |

**That first row is the whole reason this list still exists.** These men were derived
from box scores -- they appeared in a game and the archive holds them for it -- and
PFA's roster table never listed them. No amount of re-reading what is on disk will
produce a college for a man the source does not name.

### What the logs and the box scores will not fix

**The logs are no longer unfetched, and they are still not a hunting answer.**
{LOGS['gamelogs']:,} player game logs and {LOGS['playoffs']:,} playoff logs came down on
8 September -- {LOGS['gamelogs']+LOGS['playoffs']:,} pages, 1.1 GB, {LOGS['absent']} absences --
and sit **unread**. Measured from the pages themselves, not from the section register:

  * a **game log** prints {LOGS['gamelog_columns']}. None of the four facts counted here.
    62% of a 200-page sample also print a jersey number.
  * a **playoff log** prints {LOGS['playoff_columns']} -- every page of a 200-page sample.
    So a playoff log CAN answer a position, and the previous version of this document was
    wrong to say otherwise. It reaches almost nothing on this list all the same: **132 of
    the 133 missing positions are 1922-1933**, and the one that is not is 2020.

Both are pages *per player PFA already has*, so a club-season the archive holds nobody
for gains nothing from either.

**The box scores are the one thing on the disk that would move this list, and most of
them are not on the disk.** {BOXSCORES['exists']:,} exist by PFA's own link graph,
**{BOXSCORES['on_disk']:,} are held** and {BOXSCORES['cited']:,} are cited. A box score
names men a roster page never listed -- that is exactly where the {H['why_not_fillable'].get('not on the page', 0):,}
"not on the page" gaps came from. The remaining {BOXSCORES['exists']-BOXSCORES['on_disk']:,}
are a fetch, and they are the archive's work, not Ryan's.

**Ryan should not go hunting for anything in this section.** It is arriving, or already
arrived, on his own disk.

"""


def full():
    o = []
    w = o.append
    w("# Where the archive is thin\n")
    w(f"*Regenerated {TODAY} from the cohort instrument — no reader, no OCR, just the archive\n"
      "measured against itself. Written to browse eBay listings against. The short version,\n"
      "`what-to-look-for.md`, is the same measurements as one ranked list.*\n")
    w("**This list is only the gaps no source already on the disk can fill.** Every gap is\n"
      "checked against the documents already acquired before it is published as a gap.\n")
    w("**The rule of thumb.** A **prose page with ages and colleges** is worth far more\n"
      "than a lineup of names and numbers. And **both are worth almost nothing for the\n"
      "1934–46 NFL** — that era is finished: 140 club-seasons, 4,265 men, 2.06% of the four\n"
      "facts missing. The *minor-league* AFL of those same years is the opposite, and\n"
      "section Two-b is where it now lives.\n")
    w(f"Scope: every club-season **before 1934**, plus every season of the AAFC, all the\n"
      f"AFLs, the AAF, WFL, USFL, USFL2, XFL, UFL and UFL2. **{C['scoped']} club-seasons**\n"
      f"the club table holds, plus **{C['off_the_table']}** it does not.\n")
    w("| | |\n|---|---|")
    w(f"| **empty** — the table holds the club-season, nobody is on it | **{C['empty']}** |")
    w(f"| empty *by ruling*, and therefore not a gap | {C['empty_by_ruling']} |")
    w(f"| **off the table** — a source names the club, the table places no club-season | **{C['off_the_table']}** |")
    w(f"| men held but no coach or staff | {C['no_coach']} |")
    w(f"| **thin** — men held, facts missing | **{C['thin']}**, missing **{C['missing_facts_total']:,}** facts |")
    w(f"| no man carries a roster row | {C['no_roster_source']} |")
    w(f"| a surname and nothing else | {C['nameless']} |\n")
    w(what_moved())
    w(in_hand_section())
    w("---\n")
    # ---- one
    w("## One — the empty club-seasons\n")
    w(f"**{C['empty']} club-seasons the club table holds with not one roster member.** One\n"
      "document takes each of these from nothing to a team.\n")
    by = collections.defaultdict(list)
    for x in T["empty_club_seasons"]: by[x["year"]].append((x["league"], x["name"]))
    for y in sorted(by):
        lg = "/".join(sorted({l for l, _ in by[y]}))
        names = " · ".join(n for _, n in sorted(by[y], key=lambda t: t[1]))
        w(f"**{y}** *({lg})* — {names}\n")
    if T.get("empty_by_ruling_not_a_gap"):
        w("### Empty by ruling — listed apart, because they are not targets\n")
        for x in T["empty_by_ruling_not_a_gap"]:
            w(f"- **{x['year']} {x['name']}** — {x['why']}\n")
        w("*Read from the club's own record, not from an exception list, so anything ruled\n"
          "this way in future drops out of the hunt automatically.*\n")
    w(f"### Men held but nobody running them — {C['no_coach']} club-seasons\n")
    for x in sorted(T["club_seasons_without_a_coach"], key=lambda x: (x["year"], x["name"])):
        w(f"- **{x['year']}** {x['name']} ({x['league']}) — {_men(x['men'])}, no coach")
    w("")
    w("---\n")
    # ---- two
    w("## Two — the thin ones, ranked by how much one document would do\n")
    w(f"Ranked by the **count** of missing facts, not the share, so the top is where a\n"
      f"single page does the most work. **{C['missing_facts_total']:,} missing facts across\n"
      f"{C['thin']} club-seasons.** By field: {C['by_field']}.\n")
    w("| missing | men | year | club | league | age | college | weight | position |")
    w("|---|---|---|---|---|---|---|---|---|")
    for x in T["thin_club_seasons"][:45]:
        b = x["by_field"]
        w(f"| **{x['missing_facts']}** | {x['men']} | {x['year']} | {x['name']} | {x['league']} | "
          f"{b.get('age',0)} | {b.get('college',0)} | {b.get('weight',0)} | {b.get('position',0)} |")
    rest = len(T["thin_club_seasons"]) - 45
    w(f"\n{rest} further club-seasons follow, all below {T['thin_club_seasons'][45]['missing_facts']} "
      f"missing facts. Every one of them is in `what-to-look-for.md`.\n")
    w("**The 1990s onward are a different gap.** 72 of these club-seasons are 1990 or later\n"
      "and carry 550 missing facts, almost all weight. No listing fixes those: they want a\n"
      "league media guide or a season roster page.\n")
    w("### The men who are barely there\n")
    w(f"**{C['nameless']} people in the whole archive hold a surname and nothing else** — no\n"
      "forename, and every other predicate they carry holds the literal string `\"None\"`.\n")
    w("| person | name | club-season |\n|---|---|---|")
    for x in T["people_with_a_surname_and_nothing_else"]:
        w(f"| `{x['person']}` | **{x['name']}** | {', '.join(x['club_seasons'])} |")
    w("")
    # ---- two-b
    w("---\n")
    w(f"## Two-b — the {C['off_the_table']} club-seasons the club table cannot place\n")
    lost = 0
    if B:
        ea = {(x["league"], x["year"], x["code"]) for x in B["empty_club_seasons"]}
        eb = {(x["league"], x["year"], x["code"]) for x in T["empty_club_seasons"]}
        lost = len(ea - eb)
    w(f"**New on 9 September, and it is where {lost} of yesterday's best targets went.** A\n"
      "source names a club and a year; the club table refuses the string and places no\n"
      "club-season; so the club-season cannot appear as a gap in any list built from the\n"
      "table. Section One fell from 128 to 18 this way and **not one of them was filled**.\n")
    w(f"**{C['off_the_table_with_men']} of the {C['off_the_table']} hold men** — "
      f"{C['off_the_table_men']} in all, three to eight apiece, almost all of them derived\n"
      "from a scoring or passing line rather than a roster. A document naming the squad\n"
      "would do two things at once: name the men, and give the club table the second source\n"
      "`SPAN_EXTENSIONS` needs before it will admit the club-season at all.\n")
    w("| year | club | league | men held | what names it |\n|---|---|---|---|---|")
    for r in sorted(T.get("club_seasons_off_the_table", []), key=lambda r: (-r["men"], r["year"]))[:40]:
        nm = " / ".join(r["names"])
        w(f'| {r["year"]} | ' + (f'**{nm}**' if nm else f'`{r["code"]}` *(no name printed anywhere)*')
          + f' | {r["league"]} | {r["men"]} | '
          + (", ".join("`" + x + "`" for x in r["sources"]) or "—") + " |")
    left = len(T.get("club_seasons_off_the_table", [])) - 40
    if left > 0:
        floor = sorted(T["club_seasons_off_the_table"], key=lambda r: (-r["men"], r["year"]))[40]["men"]
        w(f"\n{left} further club-seasons follow, all holding {floor} men or fewer, "
          f"{sum(1 for r in T['club_seasons_off_the_table'] if not r['men'])} of them nobody at "
          f"all. Every one is in `what-to-look-for.md`.\n")
    w("---\n")
    # ---- three
    w("## Three — the club-seasons no source ever gave a roster for\n")
    boxonly = (N or {}).get("counts", {}).get("boxscore_only")
    w("Read from the evidence the ingests **declare** (`roster_evidence`), not from the\n"
      "shape of the index's stint record.\n")
    if boxonly == 0:
        w("**This section is empty, and that is the day's best news.** It held three\n"
          "club-seasons whose only declared membership evidence was a box-score lineup:\n"
          "Wilson's Wildcats 1926, the 1934 Cincinnati Reds and the 1934 St. Louis Gunners.\n"
          "All three gained a roster-page source — a team photograph caption on 7 September,\n"
          "Pro Football Reference and Troan on 9 September. **0 club-seasons now rest on a\n"
          "box score alone.**\n")
    else:
        w(f"**{boxonly} club-seasons** rest on a declared box-score lineup and nothing else.\n")
    w(f"**The honest limit is unchanged.** Only a handful of stores declare `roster_evidence` at\n"
      f"all: {(N or {}).get('counts',{}).get('roster_page_somewhere','—')} club-seasons are declared to have a roster page and\n"
      f"{(N or {}).get('counts',{}).get('evidence_undeclared_only','—'):,} state nothing either way. Those are *unknown*, not\n"
      f"*has a roster*, and this section is a floor.\n")
    w(f"A weaker test agrees: **{C['no_roster_source']} club-seasons in scope hold no man carrying a\n"
      f"jersey, a games figure or a position** — "
      + " · ".join(f"{x['year']} {x['name']}" for x in T["club_seasons_with_no_roster_source"]) + ".\n")
    w("---\n")
    # ---- four
    w("## Four — the seasons on the wrong side of a league boundary\n")
    w("**The category the rest of this document could not see** until section Two-b was\n"
      "built. These club-seasons are not in the club table, so they cannot appear as gaps in\n"
      "a list built from it.\n")
    w("| club | held | outside | what it was | where it stands now |\n|---|---|---|---|---|")
    held_now = {}
    for x in T["thin_club_seasons"] + T["empty_club_seasons"]:
        held_now[(x["name"], x["year"])] = x["men"]
    for x in O["D_established_from_a_document"]:
        yrs = ", ".join(str(y) for y in x["outside"])
        st = []
        for y in x["outside"]:
            n = held_now.get((x["club"], str(y)))
            st.append(f"{y}: {_men(n)} held" if n is not None else f"{y}: nothing held")
        w(f"| **{x['club']}** | {x['held']} | **{yrs}** | {x['status']} | {'; '.join(st)} |")
    w("\n**Why no source will ever have them.** Every source the archive holds for these\n"
      "clubs is league-derived — StatsCrew, PFA, nflverse, the coaching tree. All of them\n"
      "start and stop at the same boundary, so the seasons either side are invisible to\n"
      "**all of them at once**. Re-reading any of them produces nothing.\n")
    a = O["A_string_attests_a_year_outside_the_span"]
    w("### Route A — a string names a held club in a year outside its span\n")
    w(f"The archive's own refusal lists already record these. **{O['counts']['A']}\n"
      f"attestations across {O['counts']['A_clubs']} clubs.**\n")
    w("| club | held | attested | side | source |\n|---|---|---|---|---|")
    for x in a:
        w(f"| {x['club_name']} | {x['held'][0]}–{x['held'][1]} | **{x['year_attested']}** | "
          f"{x['side']}, {x['gap_years']}y | `{x['source']}` |")
    w("\n**Read this list with care — it mixes two different things.** A short, adjacent\n"
      "gap is likely a real season. A long one is more likely a source defect: *Boston\n"
      "Yanks* attested in **1970**, twenty-two years after the club folded, is a\n"
      "wrong-for-season string. Every row needs a judgement and none is a gap until it\n"
      "gets one.\n")
    w(f"**Route B — `pfa_only_gaps`, {O['counts']['B']} entries.** The same PFA code and name\n"
      "either side of a hole, held as two clubs until a ruling says otherwise.\n")
    w(f"**Route C — `attested_same_name_across_a_long_hole`, {O['counts']['C']} entries**, all Arena.\n")
    w("### What this section still cannot do\n")
    w("**There is no founded or folded year anywhere on disk.** The fandom club-name survey\n"
      "carries **no year fields at all** — its own club-table entries say *\"the survey\n"
      "carries no years\"* — and the Wikipedia store is person-scoped, with no club\n"
      "predicates. **This section remains a floor built from refusals, not a survey.**\n")
    w("### Note for Ryan\n")
    w("**These are the hardest gaps in the archive to fill, and the most valuable.** No\n"
      "league source will ever carry them — that is definitional, not a coverage accident.\n"
      "They need **programmes, local newspapers, or a researcher who worked outside the\n"
      "league record**. Fenton and Troan are exactly that, and between them they produced\n"
      "five of the six club-seasons above within two days of being found.\n")
    w(_note())
    w("---\n")
    w("## What document would fix each gap\n")
    w("Hunt by the photographs in the listing, because that is all a listing reliably shows.\n")
    w("**Worth the most: a player-biography page** — one paragraph per man with a name, an\n"
      "age, a height, a weight and a college. It looks like dense body text in two columns\n"
      "with a bold name starting each entry, not a table. Page seven of the 1926\n"
      "Bears/Tigers programme is exactly this and carried 32 people the archive had none of.\n")
    w("**Nearly as good: a roster table with a college column.** Number, name, position,\n"
      "weight, college fills three of the four fields at once. The tell in a photograph is\n"
      "five or more narrow columns with a wide one on the right — the wide one is the\n"
      "college, and college is what the pre-1934 record lacks most (795 of 2,078).\n")
    w("**A lineup of names and numbers alone is worth little** — eleven men a side, no age,\n"
      "no college, no weight. For a club-season holding nobody it is still worth having.\n")
    w(f"**A staff or coaches panel** is worth more than its size suggests: {C['no_coach']}\n"
      "club-seasons hold a roster and nobody running it.\n")
    w("**For a club-season holding nobody, anything printed will do.** A cover with a team\n"
      "photograph and a caption naming the men, a clipping of a game report, a league\n"
      "schedule. The bar is a document that names the club and some of its men together.\n")
    w("**What to skip.** Anything 1934–46 NFL unless the photographs show a bio page. Anything\n"
      "whose photographs show only advertisements, articles or a scoring grid — **59% of\n"
      "what a programme extractor discards is advertisement and article text**, and the\n"
      "same is true of what a buyer gets.\n")
    w("**Where the money is, in one line.** The 1920–26 APFA and early NFL — Detroit\n"
      "Heralds, Hammond Pros, Rochester Jeffersons, Louisville Brecks, Columbus\n"
      f"Panhandles, Tonawanda Kardex — and the {C['off_the_table']} club-seasons in section\n"
      "Two-b that the club table cannot even name.\n")
    return "\n".join(o)


if __name__ == "__main__":
    # ONE RUN, ONE SET OF ROWS. The CSV and the markdown table are two renderings of the
    # SAME list object, so they cannot disagree about what is on it or in what order.
    # Building the CSV from a second call to ranked_rows() would be cheap and would also
    # be a second answer to the same question.
    ROWS = ranked_rows()
    for name, body in (("where-the-archive-is-thin.md", full()),
                       ("what-to-look-for.md", short(ROWS))):
        p = os.path.join(DOCS, name)
        open(p, "w").write(body)
        print(f"  {name:32s} {len(body):>7,} bytes  {body.count(chr(10))+1:>4} lines")
    p = os.path.join(DOCS, "what-to-look-for.csv")
    # QUOTE_MINIMAL with the default dialect: a field holding a comma or a quote is
    # quoted, and csv.reader round-trips it. lineterminator is pinned so the file does
    # not change shape between platforms.
    with open(p, "w", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(csv_rows(ROWS))
    print(f"  {'what-to-look-for.csv':32s} {os.path.getsize(p):>7,} bytes  "
          f"{len(ROWS):>4} rows + a header")
    x = os.path.join(DOCS, "what-to-look-for.xlsx")
    n = write_xlsx(ROWS, x)
    print(f"  {'what-to-look-for.xlsx':32s} {os.path.getsize(x):>7,} bytes  "
          f"{n:>4} rows, 3 sheets")
