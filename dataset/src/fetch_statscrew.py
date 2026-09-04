"""Fetch and cache StatsCrew pages. Cache is a source tree, not a claim store."""
import os, re, time, urllib.request, html
UA = "Mozilla/5.0 (research; contact ryannecci@gmail.com)"
CACHE = os.environ.get("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/build1950"))

def _get(url, key):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key + ".html")
    if not os.path.exists(p):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(0.7)
    return open(p, encoding="utf-8", errors="replace").read()

def league_year(league, year):
    return _get(f"https://www.statscrew.com/football/l-{league}/y-{year}", f"L_{league}_{year}")

def team_roster(team, year):
    return _get(f"https://www.statscrew.com/football/roster/t-{team}/y-{year}", f"R_{team}_{year}")

def person(slug):
    return _get(f"https://www.statscrew.com/football/stats/{slug}", f"P_{slug}")

def teams_in(league, year):
    t = league_year(league, year)
    return sorted(set(re.findall(r'/football/roster/t-([A-Z0-9]+)/y-%d' % year, t)))

def _strip(x):
    return html.unescape(re.sub(r"<[^>]+>", "", x)).strip()

def parse_roster(page):
    """-> (headers, [ {col: cell} ], {name: slug}). Blank cells are preserved as ''. """
    t = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    hdr = [_strip(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)]
    rows, slugs = [], {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) != len(hdr) or not hdr:
            continue
        cells = [_strip(c) for c in tds]
        rec = dict(zip(hdr, cells))
        m = re.search(r"/football/stats/(p-[a-z0-9]+)", tr)
        if m and rec.get("Player"):
            slugs[rec["Player"]] = m.group(1)
        rows.append(rec)
    return hdr, rows, slugs

PERSON_FIELDS = ("Born", "Deceased", "Position", "Height", "Weight", "College", "High School", "Career")

def parse_person(page):
    t = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    i = t.find("<h1")
    seg = t[i:i + 2500]
    xref = sorted(set(x for x in re.findall(r"/football/stats/([pc]-[a-z0-9]+)", seg)))
    flat = re.sub(r"<[^>]+>", "|", seg)
    flat = re.sub(r"\|+", "|", html.unescape(flat))
    flat = re.sub(r"[ \t]+", " ", flat)
    name = (re.search(r"^\|?\s*([^|]{2,60}?)\s*\|", flat) or [None, ""])[1].strip()
    out = {"name": name, "xref": xref}
    for f in PERSON_FIELDS:
        m = re.search(re.escape(f) + r":\s*\|?\s*([^|]*)", flat)
        out[f.lower().replace(" ", "_")] = m.group(1).strip() if m else ""
    # a page is REAL only if it carries a name and a full birth date
    out["is_real"] = bool(name) and bool(re.match(r"[A-Z][a-z]+ \d{1,2}, \d{4}", out.get("born","")))
    return out
