"""ONE reader for a Pro Football Archives game log or playoff log page.

The pages are one table of stacked blocks. A block is:

    SECTION            one cell, upper case          RUSHING
    PHASE              one cell, upper case          REGULAR SEASON / POSTSEASON
    HEADER             DATE, YEAR TEAM, AHN, OPP, SCORE, RES, then the section's columns
    ROW ...            one per game the man recorded something in that section

A page carries several blocks and a man can appear under RUSHING, RECEIVING and
KICKOFF RETURNS for the same game, so a row is NOT a game and the count of rows is
not the count of appearances. Rows are keyed on (code, date, section) and games on
(code, date).

THE ROW LENGTH IS CHECKED AGAINST THE HEADER, never zipped blindly. PFA has printed
a fuller layout than its own header before (see docs/DATASET_PRECEDENTS.md), and a
silent zip would file one column's value under another's name. A row whose length
does not match its header is COUNTED and returned as a mismatch, not guessed at.

Playoff logs are a different page: a season-total table per year, with NO, POS, GP
and GS -- so they carry a POSITION, which a game log does not.
"""
import re, html, os

_TABLE = re.compile(r'(?is)<table.*?</table>')
_TR = re.compile(r'(?is)<tr.*?</tr>')
_TD = re.compile(r'(?is)<t[hd][^>]*>(.*?)</t[hd]>')
_SCRIPT = re.compile(r'(?is)<script.*?</script>')
_HREF = re.compile(r'(?is)href="([^"]+)"')
# "1967 New Orleans Saints (NFL) 1967 NO NFL" -- the long form then the short form
_TEAM = re.compile(r'^(\d{4})\s+(.+?)\s+\((\w+)\)\s+\d{4}\s+(\S+)\s+(\w+)$')
_DATE = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')

FIXED = ["DATE", "YEAR TEAM", "AHN", "OPP", "SCORE", "RES"]


def _text(cell):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()


def _cells(tr):
    return [_text(c) for c in _TD.findall(tr)]


def _raw_cells(tr):
    return _TD.findall(tr)


def code_of(path):
    """gamelogs/a/abra00500.html -> ('a', 'abra00500'), the SAME code the player page
    uses, which is how a log joins to a person: players/a/abra00500.html."""
    parts = path.replace("\\", "/").split("/")
    return parts[-2], os.path.splitext(parts[-1])[0]


def read(path):
    """-> dict(kind, code, letter, blocks=[...], mismatches=int, rows=int)

    EVERY table is walked, not the longest one. A playoff log is several tables --
    the per-year table, then SNAP COUNTS, then PENALTIES -- and taking `max(tables,
    key=len)` returned the biggest and silently dropped the rest, including the one
    carrying POSITION. A game log with several sections splits the same way.

    A block is {"section", "phase", "columns", "rows"} and a row is a dict of column
    name -> printed string, with `_boxscore` holding the href on the date cell."""
    s = open(path, encoding="utf-8", errors="replace").read()
    body = _SCRIPT.sub(" ", s)
    letter, code = code_of(path)
    kind = "playoff" if "/playoffs/" in path.replace("\\", "/") else "gamelog"
    blocks, mism = [], 0
    section, phase, cols, cur = None, None, None, None
    for tab in _TABLE.findall(body):
        for tr in _TR.findall(tab):
            raw = _raw_cells(tr)
            cs = [_text(c) for c in raw]
            if not cs: continue
            if len(cs) == 1:
                t = cs[0]
                if not t: continue
                if t in ("REGULAR SEASON", "POSTSEASON", "PRESEASON", "PLAYOFFS"):
                    phase = t
                elif t.upper() == t and len(t) < 40:
                    section, phase, cols, cur = t, None, None, None
                continue
            # A HEADER ROW IS RECOGNISED BY SHAPE, not by which directory the file
            # came from. The first version required kind == "playoff" before it would
            # accept `PENALTIES, Called, Yards ...` as a header, so the same table
            # parsed differently depending on its path -- and a fixture could not
            # reproduce the bug it was written to catch.
            label = cs[0]
            is_header = label in ("DATE", "YEAR TEAM") or (
                len(cs) > 2 and label and label == label.upper()
                and not any(ch.isdigit() for ch in label)
                and date_of(label) is None and team_of(label) is None)
            if is_header:
                if label not in ("DATE", "YEAR TEAM"):
                    section = label
                    cols = ["YEAR TEAM"] + cs[1:]
                else:
                    cols = cs
                cur = {"section": section, "phase": phase, "columns": cols, "rows": []}
                blocks.append(cur)
                continue
            if cur is None or cols is None:
                continue
            if len(cs) != len(cols):
                mism += 1
                continue
            row = dict(zip(cols, cs))
            m = _HREF.search(raw[0])
            row["_boxscore"] = m.group(1) if m else None
            # THE TEAM CELL'S LINKS, kept as the date cell's is. The cell prints the club
            # three ways -- a link, a full name, a short label for phones -- and the short
            # label is the one that is wrong: on ~22% of PLAYOFF rows it prints the opponent
            # (`2013 CAR NFL` on a 49er's row whose link and full name both say San
            # Francisco). team_of_row() reads the club from the link. Ryan, 2026-09-11.
            # BY POSITION, as the team cell always was read: the second cell on a game log,
            # the first on a playoff log. Looking it up by the label "YEAR TEAM" lost every
            # PUNTING row, whose block header shifts the labels by one.
            ti = 0 if kind == "playoff" else 1
            if len(raw) > ti:
                row["_team_cell"] = cs[ti]
                row["_team_links"] = _HREF.findall(raw[ti])
            cur["rows"].append(row)
    return {"kind": kind, "code": code, "letter": letter, "blocks": blocks,
            "mismatches": mism, "rows": sum(len(b["rows"]) for b in blocks),
            "empty": not blocks}


def team_of(cell):
    """'1967 New Orleans Saints (NFL) 1967 NO NFL' -> (1967, 'New Orleans Saints',
    'NFL', 'NO'). Returns None rather than guessing when the cell is not that shape."""
    m = _TEAM.match(cell.strip())
    if not m: return None
    return int(m.group(1)), m.group(2), m.group(3), m.group(4)


_STEM = re.compile(r'(?:^|/)(\d{4})([a-z0-9/-]+)\.html$')


def _link_code(link, y, league):
    m = _STEM.search(link or "")
    if not m: return None
    yy, rest = m.groups(); lg = league.lower()
    if int(yy) != y or not rest.startswith(lg) or len(rest) == len(lg): return None
    return rest[len(lg):].upper()


def team_of_row(row):
    """-> (year, full name, league, the FULL NAME'S LINK code or None, short label as
    printed, the other link's code) -- None only when the team cell does not parse.

    THE CLUB IS READ FROM THE FULL NAME AND ITS LINK, never from the short label. Ryan's
    ruling, 2026-09-11: PFA's short label names the OPPONENT on about 22% of playoff rows.
    The cell carries two links: the first sits with the full name, the second with the
    short label -- and the second can point wherever the label does (a 1934 Gunners row
    links `1934nflstl` with its name and `1934nflcin` with its label). So the FIRST link is
    read and the other is returned as printed. The first link's code need not be the
    code a club holds (PFA files the 2020 Raiders under `oak`), which is why the caller
    resolves it to a CLUB and holds it against the full name there. The short label is
    returned so it can be kept: it is what PFA published."""
    t = team_of(row.get("_team_cell", ""))
    if not t: return None
    y, full, league, short = t
    links = row.get("_team_links") or []
    # A LINK THAT CANNOT BE READ FOR THE ROW'S YEAR IS RETURNED AS None, NOT A REFUSAL: the
    # full name still names the club. The one such row in the archive reads "1933 New York
    # Giants ... NYG" beside a link to the 1934 Giants page; refusing it lost a right claim.
    first = _link_code(links[0], y, league) if links else None
    other = _link_code(links[1], y, league) if len(links) > 1 else None
    return y, full, league, first, short, other


def date_of(cell):
    m = _DATE.match(cell.strip())
    if not m: return None
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"


def stat_columns(block):
    return [c for c in block["columns"] if c not in FIXED]


def _selftest():
    """Both answers, on fixtures, for the two properties that have already gone wrong
    once each while this reader was being written."""
    import tempfile
    ok = True

    def write(html_text):
        f = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                        dir=os.environ.get("TMPDIR") or ".")
        f.write(html_text); f.close()
        return f.name

    # 1. A ROW SHORTER THAN ITS HEADER IS COUNTED, NEVER ZIPPED. Zipping would file the
    #    TD column's value under LG for every career-totals row on every playoff page.
    p = write("<table><tr><td>RUSHING</td></tr><tr><td>REGULAR SEASON</td></tr>"
              "<tr><th>DATE</th><th>YEAR TEAM</th><th>AHN</th><th>OPP</th><th>SCORE</th>"
              "<th>RES</th><th>ATT</th><th>YDS</th></tr>"
              "<tr><td>9/1/1974</td><td>1974 X Y (NFL) 1974 XY NFL</td><td>H</td><td>Z</td>"
              "<td>7-3</td><td>W</td><td>2</td><td>9</td></tr>"
              "<tr><td>Career Totals</td><td>2</td><td>9</td></tr></table>")
    d = read(p); os.unlink(p)
    good = d["rows"] == 1 and d["mismatches"] == 1
    ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} a short row is counted, not zipped "
          f"(rows {d['rows']}, mismatches {d['mismatches']})")

    # 2. EVERY TABLE IS WALKED. A playoff log is several tables and the biggest is not
    #    the one carrying POSITION; taking max(tables, key=len) returned 0 blocks here.
    p = write("<table><tr><th>YEAR TEAM</th><th>NO</th><th>POS</th></tr>"
              "<tr><td>2011 X Y (NFL) 2011 XY NFL</td><td>54</td><td>ILB</td></tr></table>"
              "<table><tr><th>PENALTIES</th><th>Called</th><th>Yards</th><th>A</th><th>B</th>"
              "<th>C</th></tr>"
              "<tr><td>2011 X Y (NFL) 2011 XY NFL</td><td>1</td><td>10</td><td>0</td>"
              "<td>0</td><td>0</td></tr></table>")
    d = read(p); os.unlink(p)
    secs = [b["section"] for b in d["blocks"]]
    good = len(d["blocks"]) == 2 and "PENALTIES" in secs and d["rows"] == 2
    ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} every table is walked (blocks {len(d['blocks'])}, "
          f"sections {secs})")

    # 3. A summary row does not parse as a team, so it cannot be counted as a season.
    good = team_of("2 Years (NFL) 2 Years NFL") is None and \
        team_of("1974 San Francisco 49ers (NFL) 1974 SF NFL") == (1974, "San Francisco 49ers", "NFL", "SF")
    ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} a totals row does not parse as a year and club")

    # 4. A blank cell is not a zero.
    good = date_of("12/15/1974") == "1974-12-15" and date_of("") is None
    ok &= good
    print(f"  {'ok  ' if good else 'FAIL'} a date parses, a blank does not")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
