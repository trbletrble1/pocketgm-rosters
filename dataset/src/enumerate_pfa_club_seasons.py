"""Every PFA club-season page the archive wants, enumerated BEFORE anything is fetched.

The denominator is built from the club table and the empty-club-season measurement, not
from what came back. Three numbers, kept apart, as declarations/source-coverage.json's
`enumerable_parts` rule requires:

  EXISTS    PFA's own link graph, over every page already cached, names the page
  ON DISK   the page is in one of the four PFA caches
  CITED     a claim in the read model names that locator

THE FOUR CACHES. `pfa2` (50,829), `pfa-team-seasons` (1,446), `pfa` (418) and
`pfa-awards` (231). A first count of what was on disk said 0 of 44 because it looked in
one of them.

  python3 src/enumerate_pfa_club_seasons.py            report
  python3 src/enumerate_pfa_club_seasons.py --write    write build-reports/pfa-club-season-targets.json
"""
import os, re, sys, json, html, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

SRC = os.path.expanduser("~/Documents/pgm3-sources")
TREES = ("pfa-team-seasons", "pfa2", "pfa", "pfa-awards")
OUT = os.path.join(BASE, "build-reports", "pfa-club-season-targets.json")
LINK = re.compile(r'href=["\']?/?([0-9]{4}[a-z][a-z0-9\-]*\.html)', re.I)
# A PAGE WITH A ROSTER SAYS SO IN ITS OWN TITLE. Found 2026-09-09: PFA titles a page that
# carries a roster "<year> <club> (<league>) Scores, Roster, Stats, Coaches" and one that
# does not "<year> <club> (<league>) - Pro Football Archives". The five EFL 1926-27 pages
# are the second kind and they carry SCORES and Schedule Notes only. It is a property of
# the title, so it can be applied to all 1,446 cached pages without reading one of them.
ROSTER_IN_TITLE = "Roster"


def disk():
    out = {}
    for d in TREES:
        p = os.path.join(SRC, d)
        if os.path.isdir(p):
            for f in os.listdir(p): out.setdefault(f.lower(), os.path.join(p, f))
    return out


def linked(have):
    s = set()
    for p in have.values():
        if not p.endswith(".html"): continue
        try: t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception: continue
        s |= {m.lower() for m in LINK.findall(t)}
    return s


def variants(code, league, year):
    """PFA's own locator for a club-season, from the club table's code. PFA writes `-`
    where the archive's code carries `/` (S/K -> s-k) and sometimes drops the separator
    (W-B -> wb), so each form is tried and the one PFA links is taken. Nothing is invented:
    a code that matches no linked page is reported, not guessed at."""
    b = code.replace("PFA:", "").lower()
    b = re.sub(r"^(afl|ufl|wfl|efl|pcfl|tsfl|ifl|acfl|cofl|dfl|mwfl|afa|arfl|nfle|wlaf)[:\-]?", "", b)
    forms = [b, b.replace("/", "-"), b.replace("/", ""), b.replace("-", "")]
    return [f"{year}{league.lower()}{v}.html" for v in dict.fromkeys(forms) if v]


def title_of(path):
    try: s = open(path, encoding="utf-8", errors="replace").read(4000)
    except Exception: return None
    m = re.search(r"(?is)<title>(.*?)</title>", s)
    return html.unescape(m.group(1)).strip() if m else None


def has_roster_table(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    for tab in re.findall(r"(?is)<table.*?</table>", s):
        for tr in re.findall(r"(?is)<tr.*?</tr>", tab)[:1]:
            cs = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
                  for x in re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", tr)]
            if cs and cs[0].strip().upper() == "ROSTER": return True
    return False


def targets():
    T = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    out = {}
    for c in T["clubs"]:
        if c["origin"] not in ("pfa_only", "archive"): continue
        for seg in c["segments"]:
            for y in range(seg["first"], seg["last"] + 1):
                if y in (seg.get("dark_years") or []): continue
                for l in seg["leagues"]:
                    if not (l["first"] <= y <= l["last"]) or not l["league"]: continue
                    key = (c["id"], seg["code"], l["league"], y)
                    if key not in out:
                        nm = next((n["name"] for n in c["names"] if n["first"] <= y <= n["last"]),
                                  c["names"][0]["name"])
                        out[key] = {"club_id": c["id"], "code": seg["code"], "league": l["league"],
                                    "year": y, "name": nm, "origin": c["origin"]}
    return list(out.values())


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    cited = {sr.split("#", 1)[1].split("#")[0].lower().rsplit("/", 1)[-1]
             for (sr,) in conn.execute("select distinct source_record from claim "
                                       "where source_record like 'pro-football-archives#%'")}
    have = disk(); lnk = linked(have)
    rows = []
    n = collections.Counter()
    for t in targets():
        vs = variants(t["code"], t["league"], t["year"])
        ex = next((v for v in vs if v in lnk), None)
        od = next((v for v in vs if v in have), None)
        loc = od or ex
        r = dict(t, locator=loc, exists=bool(ex), on_disk=bool(od),
                 cited=bool(loc and loc in cited),
                 title=title_of(have[od]) if od else None)
        r["title_promises_a_roster"] = bool(r["title"] and ROSTER_IN_TITLE in r["title"])
        r["has_roster_table"] = has_roster_table(have[od]) if od else None
        rows.append(r)
        n["targets"] += 1; n["exists"] += r["exists"]; n["on_disk"] += r["on_disk"]
        n["cited"] += r["cited"]
        if r["on_disk"]:
            n["title_promises"] += r["title_promises_a_roster"]
            n["has_table"] += bool(r["has_roster_table"])
    pfa_only = [r for r in rows if r["origin"] == "pfa_only"]
    print(f"CLUB-SEASON PAGES, enumerated from the club table")
    print(f"  targets                {n['targets']:>6,}   (pfa_only {len(pfa_only):,})")
    print(f"  PFA links a page       {n['exists']:>6,}")
    print(f"  on disk                {n['on_disk']:>6,}")
    print(f"  cited by a claim       {n['cited']:>6,}")
    print(f"  title promises a roster{n['title_promises']:>6,}  (of those on disk)")
    print(f"  has a ROSTER table     {n['has_table']:>6,}")
    liars = [r for r in rows if r["on_disk"] and r["title_promises_a_roster"] and not r["has_roster_table"]]
    quiet = [r for r in rows if r["on_disk"] and not r["title_promises_a_roster"] and r["has_roster_table"]]
    print(f"\n  TITLE TEST: {len(liars)} pages promise a roster and have none; "
          f"{len(quiet)} have one and do not promise it")
    for r in liars[:12]: print(f"     promises, has none: {r['locator']}  {r['title']}")
    for r in quiet[:12]: print(f"     has one, silent   : {r['locator']}  {r['title']}")
    missing = [r for r in rows if r["exists"] and not r["on_disk"]]
    noloc = [r for r in rows if not r["exists"] and not r["on_disk"]]
    print(f"\n  TO FETCH: {len(missing)}   |   no locator found at all: {len(noloc)}")
    for r in sorted(missing, key=lambda x: (x["league"], x["year"]))[:40]:
        print(f"     {r['league']:5s} {r['year']} {r['name'][:28]:28s} {r['locator']}")
    if noloc:
        print("  no linked page for these codes (reported, not guessed):")
        for r in noloc[:20]: print(f"     {r['league']:5s} {r['year']} {r['name'][:28]:28s} code {r['code']}")
    if write:
        json.dump({"_what": "every PFA club-season page the club table implies, with the three "
                            "numbers apart. Built BEFORE any fetch.",
                   "counts": dict(n), "targets": rows}, open(OUT, "w"), indent=1)
        print(f"\n-> {OUT}")
    return rows


if __name__ == "__main__":
    main(write="--write" in sys.argv)
