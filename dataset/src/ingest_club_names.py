"""Club names, per club-season, from the roster page titles already cached.

Every bio said "1924 with MI1". Nobody can know that is the Minneapolis Marines.
0 club-name claims existed in the archive.

PER CLUB-SEASON, not per club. A club's name in a season is a fact about that
season: MI1 is the Minneapolis Marines in 1924, and clubs rename and relocate.
Whether two club-seasons are the same FRANCHISE is a different question the
design deliberately keeps separate (5.2), and this does not answer it.

Reads the cache only. No network.
  python3 src/ingest_club_names.py [--write]
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
os.environ.setdefault("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
from model import Store
import fetch_statscrew as F

TITLE = re.compile(r"<title>\s*(\d{4})\s+(.*?)\s+football\s+Roster\s+on\s+StatsCrew",
                   re.S | re.I)


def team_league():
    out = {}
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        b = os.path.basename(f)[:-5]
        if "-" not in b or b.split("-")[0] in ("stats", "devstats", "coaches",
                                               "salaries", "photos", "assistants"):
            continue
        lg = b.split("-")[0].upper()
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            s = c.get("subject")
            if isinstance(s, list) and len(s) == 4 and s[0] == "stint":
                out[(s[2], str(s[3]).split("-")[-1])] = lg
    return out


SRC = os.path.expanduser("~/Documents/pgm3-sources")
DECL = json.load(open(os.path.join(BASE, "declarations", "club-names.json")))
PFA_TITLE = re.compile(r"<title>\s*(\d{4})\s+(.*?)\s+\(([A-Z0-9]+)\)", re.S | re.I)
CANONICAL = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']https?://[^/]+/([^"\']+)["\']', re.I)


def statscrew_leagues():
    """(team, year) -> the StatsCrew league whose league page links that roster page. The
    source's own statement, read from its own pages -- declarations/club-names.json."""
    out = collections.defaultdict(set)
    for d in DECL["statscrew_caches"]:
        for f in glob.glob(os.path.join(SRC, d, "L_*.html")):
            m = re.match(r"L_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
            if not m: continue
            lg, yr = m.group(1), m.group(2)
            t = open(f, encoding="utf-8", errors="replace").read()
            for team in set(re.findall(r'/football/roster/t-([A-Z0-9]+)/y-%s' % yr, t)):
                out[(team, yr)].add(lg)
    return out


def build(verbose=False):
    """-> (store, {source_record: the cached page it was read from}). Writes nothing.
    src/gate_club_names.py calls this and compares, claim for claim, with the store.

    THE LEAGUE IS STATSCREW'S OWN (Ryan, 2026-09-13). team_league() took the first word of
    whichever build store held the club-season, and by September that read `pfa-`,
    `coaches-` and `neft-` store names as leagues: a re-run would have relabelled 2,339
    club-seasons. A league page that links the roster says which league it is."""
    lgs = statscrew_leagues()
    store = Store()
    store.add_source(json.load(open(os.path.join(BASE, "declarations", "statscrew.json"))))
    seen, where = {}, {}
    miss, several = 0, []
    files = {}
    for d in DECL["statscrew_caches"]:                      # the first folder listed wins
        for f in sorted(glob.glob(os.path.join(SRC, d, "R_*.html"))):
            files.setdefault(os.path.basename(f), f)
    for base_, f in sorted(files.items()):
        m0 = re.match(r"R_([A-Z0-9]+)_(\d{4})\.html$", base_)
        if not m0: continue
        team, year = m0.group(1), m0.group(2)
        h = open(f, encoding="utf-8", errors="replace").read()
        m = TITLE.search(h)
        if not m:
            miss += 1; continue
        if m.group(1) != year:
            miss += 1; continue                  # title year must match the key
        name = " ".join(m.group(2).split())
        got = lgs.get((team, year), set())
        if len(got) > 1:
            several.append((team, year, sorted(got))); continue   # refused, never picked
        lg = next(iter(got)) if got else "?"
        seen[(lg, year, team)] = name; where[(lg, year, team)] = f
    if several:
        raise SystemExit(f"REFUSING: {len(several)} roster pages are linked by two StatsCrew leagues "
                         f"({several[:3]}); the league cannot be read, and is not guessed")
    if verbose:
        print(f"club-seasons named: {len(seen):,}   pages with no usable title: {miss}")
        names = collections.Counter(seen.values())
        print(f"distinct club names: {len(names):,}")
        # a club whose NAME changes across seasons - the reason this is per-season
        byteam = collections.defaultdict(set)
        for (lg, y, t), n in seen.items(): byteam[t].add(n)
        changed = {t: sorted(v) for t, v in byteam.items() if len(v) > 1}
        print(f"team codes carrying MORE THAN ONE name across seasons: {len(changed)}")
        for t, v in list(changed.items())[:6]: print(f"   {t}: {v}")
    pages = {}
    for (lg, year, team), name in sorted(seen.items()):
        subj = ("club_season", lg, year, team)
        store.declare_subject(subj)
        sr = store.add_source_record("statscrew", f"roster/{team}-{year}#title")
        pages[sr] = where[(lg, year, team)]
        store.add_claim(sr, subj, "club_name", name, int(year),
                        kind="observed", stated_by="StatsCrew",
                        note="from the roster page title; a name for THIS "
                             "season, not a franchise identity")
    # PRO FOOTBALL ARCHIVES' CLUB PAGES, for club-seasons StatsCrew does not name (the 1926 AFL,
    # 1934 Cincinnati). Declared page by page; the club code is the archive's, the locator is
    # PFA's own -- the canonical URL the page records for itself.
    store.add_source(json.load(open(os.path.join(BASE, DECL["pfa_source_declaration"]))))
    for e in DECL["pfa_club_pages"]:
        f = os.path.join(SRC, e["cached"])
        h = open(f, encoding="utf-8", errors="replace").read()
        t, c = PFA_TITLE.search(h), CANONICAL.search(h)
        subj = tuple(e["club_season"])
        if not t or not c or t.group(1) != subj[2]:
            raise SystemExit(f"REFUSING: {e['cached']} gives no title, no canonical URL, or another year")
        store.declare_subject(subj)
        sr = store.add_source_record("pro-football-archives", c.group(1))
        pages[sr] = f
        store.add_claim(sr, subj, "club_name", " ".join(t.group(2).split()), int(subj[2]),
                        kind="observed", stated_by="Pro Football Archives",
                        note="from the PFA club page title; a name for THIS season, not a "
                             "franchise identity")
    return store, pages


def main():
    write = "--write" in sys.argv
    store, pages = build(verbose=True)
    print(f"claims {len(store.claims):,}   records {len(store.source_records):,}")
    if write:
        store.save(os.path.join(BASE, "build", "club-names.json"))
        print(f"\nwrote build/club-names.json")
    else:
        print("(dry run; pass --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
