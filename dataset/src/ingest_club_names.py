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


def main():
    write = "--write" in sys.argv
    t2l = team_league()
    store = Store()
    store.add_source(json.load(open(os.path.join(BASE, "declarations", "statscrew.json"))))
    seen = {}
    miss = 0
    for f in sorted(glob.glob(os.path.join(F.CACHE, "R_*.html"))):
        m0 = re.match(r"R_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
        if not m0: continue
        team, year = m0.group(1), m0.group(2)
        h = open(f, encoding="utf-8", errors="replace").read()
        m = TITLE.search(h)
        if not m:
            miss += 1; continue
        if m.group(1) != year:
            miss += 1; continue                  # title year must match the key
        name = " ".join(m.group(2).split())
        lg = t2l.get((team, year), "?")
        seen[(lg, year, team)] = name
    print(f"club-seasons named: {len(seen):,}   pages with no usable title: {miss}")
    names = collections.Counter(seen.values())
    print(f"distinct club names: {len(names):,}")
    # a club whose NAME changes across seasons - the reason this is per-season
    byteam = collections.defaultdict(set)
    for (lg, y, t), n in seen.items(): byteam[t].add(n)
    changed = {t: sorted(v) for t, v in byteam.items() if len(v) > 1}
    print(f"team codes carrying MORE THAN ONE name across seasons: {len(changed)}")
    for t, v in list(changed.items())[:6]: print(f"   {t}: {v}")
    if write:
        for (lg, year, team), name in sorted(seen.items()):
            subj = ("club_season", lg, year, team)
            store.declare_subject(subj)
            sr = store.add_source_record("statscrew", f"roster/{team}-{year}#title")
            store.add_claim(sr, subj, "club_name", name, int(year),
                            kind="observed", stated_by="StatsCrew",
                            note="from the roster page title; a name for THIS "
                                 "season, not a franchise identity")
        store.save(os.path.join(BASE, "build", "club-names.json"))
        print(f"\nwrote build/club-names.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
