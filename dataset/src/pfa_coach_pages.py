"""Parse a Pro Football Archives COACH page. Read-only; no claims here.

A coach page shares the player page shape above the fold (name, printed full
name, Born / Died / High School labels, the college table, Military Service),
so that part is read by ingest_pfa.parse_player and not re-implemented.

Below it sit the coaching tables: REGULAR SEASON and PLAYOFFS, one row per
club-season, headed YEAR TEAM / Conference / Division / Position / Seq / Finish /
G / W / L / T / PCT. The ROLE is the `Position` column. It is kept EXACTLY as
printed: no normalising, no mapping, no typo repair, no splitting on '/', ';'
or '-'. Whether a compound role decomposes is Ryan's ruling and unmade.

The club cell runs two renderings of the same club together --
  '1995 Winnipeg Blue Bombers (CFL)' and '1995 WPG CFL'
-- as two <span>s around one link, /1995cflwpg.html. The link is the split:
year, league, club code, read from the href, never from the joined text.
Rows with class="career" are the page's own totals and are not seasons.
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ingest_pfa import parse_player, text, cells, labelled

CACHE = os.environ.get("PGM3_SOURCES", os.path.join(HERE, "..", "..", "..", "pgm3-sources")) + "/pfa2"
CLUB_HREF = re.compile(r'href="/(?:playoffteams/)?(\d{4})([a-z0-9\-]+)\.html"')
CAREER = re.compile(r"^\d+ Y[a-z]+ ", re.I)      # '2 Years (CFL)', and the site's own 'Yaear', 'Yera'
LONG = re.compile(r'<span class="d-none d-md-inline">(?:<a[^>]*>)?(.*?)(?:</a>)?</span>', re.S)
SHORT = re.compile(r'<span class="d-inline d-md-none">(?:<a[^>]*>)?(.*?)(?:</a>)?</span>', re.S)
# the page's OWN record links, by their anchor text. Any other /players/ link on a
# coach page is a relative's (Bill Belichick's page links his father's playing
# record) and is identity evidence for nobody.
LINK = re.compile(r'href="/(players|officials)/(?:[a-z]/)?([a-z0-9]+)\.html"[^>]*>\s*(Playing|Officiating) Record\s*<')
LEAGUE_CODES = {"nfl", "cfl", "afl", "aafc", "apfa", "usfl", "wfl", "xfl", "wlaf", "ufl", "aaf", "afa", "nfla"}


class CoachPageError(Exception):
    pass


def split_club_cell(cell_html):
    """year, league and club code from the SHORT rendering ('1995 WPG CFL'), which
    prints them as three tokens (two when the club had no league: '1940 KEN').
    The href ('/1995cflwpg.html') runs league and code together with no boundary,
    so it is kept whole as the page id and CHECKED against the tokens; where it
    disagrees (the Raiders' 2020 page is still /nfloak/ while the cell prints LV;
    one 1954 BC cell prints CFL over a /wifu/ page) both are kept and flagged."""
    m = CLUB_HREF.search(cell_html)
    lo = LONG.search(cell_html); sh = SHORT.search(cell_html)
    if not sh:
        return None
    short = text(sh.group(1)); long_ = text(lo.group(1)) if lo else None
    if CAREER.match(short) or (long_ and CAREER.match(long_)):
        return {"career_row": True}
    if not short and not long_:
        return {"empty_club_cell": True}      # the source printed a season row with no club
    t = re.match(r"^(\d{4}) (\S+)(?: (\S+))?$", short)
    if not t:
        raise CoachPageError(f"short club rendering unreadable: {short!r}")
    year, code, league = int(t.group(1)), t.group(2), (t.group(3) or "")
    href = m.group(0)[6:-1] if m else None
    if href and href.startswith("/playoffteams/"):
        href_check = href[len("/playoffteams"):]
    else:
        href_check = href
    out = {"year": year, "league": league, "club": code, "printed_long": long_,
           "printed_short": short, "href": href}
    if href is None:
        out["no_club_page"] = True
    elif href_check.lower() != f"/{year}{league}{code}.html".lower():
        out["href_disagrees_with_printed_cell"] = True
    return out


def coaching_tables(html):
    """Every season row under REGULAR SEASON / PLAYOFFS, in page order."""
    out = []; anomalies = []
    for tbl in re.findall(r"<table.*?</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>.*?</tr>", tbl, re.S)
        section = None; header = None
        for r in rows:
            if "colspan" in r and "<th" in r:
                # PLAYOFFS prints no header row of its own; it reuses REGULAR SEASON's
                section = text(r); continue
            if "<th" in r:
                header = [text(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", r, re.S)]; continue
            if header is None or "YEAR TEAM" not in header:
                continue
            if 'class="career"' in r:
                continue
            # PLAYOFFS rows print one cell unclosed -- '<td ...><td ...>2</td>' -- which
            # a td..</td> read would merge with its neighbour and shift the record by
            # one column. An empty cell followed directly by another cell is closed
            # first; the Position cell sits before the fault and is unaffected either way.
            r = re.sub(r"(<td[^>]*>)\s*(?=<td)", r"\1</td>", r)
            tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
            club = split_club_cell(tds[0]) if tds else None
            if not club:
                raise CoachPageError(f"season row without a club cell: {text(r)[:80]}")
            if club.get("career_row"):
                continue
            if club.get("empty_club_cell"):
                anomalies.append({"section": section, "row_as_printed": text(r)}); continue
            if len(tds) != len(header):
                # the site prints one header for the section; a row of another width
                # (a UFL 2024 page carries an extra cell) is aligned by position and flagged
                club["row_width_differs_from_header"] = [len(tds), len(header)]
            row = dict(zip(header, [text(c) for c in tds]))
            out.append({"section": section, **club, "position_as_printed": row.get("Position", ""),
                        "conference": row.get("Conference", ""), "division": row.get("Division", ""),
                        "seq": row.get("Seq", ""), "finish": row.get("Finish", ""),
                        "club_record": {k: row.get(k, "") for k in ("G", "W", "L", "T", "PCT")}})
    return out, anomalies


def parse_coach(html, code):
    h1 = re.search(r"<h1>(.*?)</h1>(.*?)<br>", html, re.S)
    name = text(h1.group(1)) if h1 else ""
    printed_full = text(h1.group(2)) if h1 else ""
    bio = parse_player(html)
    # Born / Died may be a bare year or a month and year. This file used to patch its own
    # copy of the splitter for that; the player readers never got the fix and filed 766
    # dates as places. There is now ONE splitter, ingest_pfa.split_date_place, and
    # parse_player already applied it. The raw cell is still kept beside it.
    L = labelled(html)
    for lab, d in (("Born", "birth_date"), ("Died", "death_date")):
        bio[d + "_as_printed"] = L.get(lab, "")
    links = {"players": [], "officials": []}
    for sec, c, _ in LINK.findall(html):
        if c not in links[sec]: links[sec].append(c)
    seasons, anomalies = coaching_tables(html)
    return {"code": code, "name": name, "printed_full_name": printed_full, "bio": bio,
            "seasons": seasons, "rows_without_club": anomalies, "links": links,
            "sections": sorted({s["section"] for s in seasons})}


def load(code):
    fp = os.path.join(CACHE, f"coaches_{code}.html")
    return open(fp, encoding="utf-8", errors="ignore").read()


if __name__ == "__main__":
    import json
    for code in sys.argv[1:] or ["wigt00200", "abbo00250"]:
        print(json.dumps(parse_coach(load(code), code), indent=1)[:3000])
