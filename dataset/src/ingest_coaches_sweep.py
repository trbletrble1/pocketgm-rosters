"""Head coaches for every swept NFL season.

Club-season -> coach links come from the CACHED roster pages: no network.
Only the distinct c- person pages are fetched, once each.

NOTE the scope limit, per report 12: StatsCrew's c- namespace holds HEAD COACHES
ONLY. This produces roughly one coach per club-season and NOTHING for assistants.
It is not a staff census and must not be read as one.
"""
import os, re, sys, json, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model import Store
import fetch_statscrew as F

BASE = os.path.join(HERE, "..")
CACHE = os.environ.get("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
COACH = re.compile(r'Coach:\s*(?:<[^>]+>\s*)*<a[^>]*href="[^"]*/football/stats/(c-[a-z0-9\-]+)"[^>]*>([^<]+)</a>')
LOG = []
def log(m): print(m, flush=True); LOG.append(m)

def main():
    store = Store()
    store.add_source(json.load(open(os.path.join(BASE, "declarations", "statscrew.json"))))
    club_seasons = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(CACHE, "R_*.html"))):
        m = re.search(r"R_([A-Z0-9]+)_(\d{4})\.html$", os.path.basename(f))
        if not m: continue
        team, year = m.group(1), int(m.group(2))
        for slug, name in COACH.findall(open(f, encoding="utf-8", errors="replace").read()):
            club_seasons[(team, year)].append((slug, name.strip()))

    # slug -> the name the source printed. Previously this was read, used for
    # logging, and DISCARDED: the coach store held no name at all, in any field.
    slug_name = {}
    for lst in club_seasons.values():
        for slug, name in lst:
            if name: slug_name.setdefault(slug, name)

    multi = {k: v for k, v in club_seasons.items() if len(v) > 1}
    log(f"club-seasons with a head coach: {len(club_seasons)}")
    log(f"club-seasons with MORE THAN ONE: {len(multi)}  (mid-season changes)")
    for k in sorted(multi)[:6]:
        log(f"   {k[1]} {k[0]}: {[n for _, n in multi[k]]}")

    slugs = sorted({s for v in club_seasons.values() for s, _ in v})
    log(f"distinct coaches: {len(slugs)}")

    people, phantom, xref = {}, [], 0
    for i, slug in enumerate(slugs):
        try:
            info = F.parse_person(F.person(slug))
        except Exception as e:
            log(f"   fetch failed {slug}: {e}"); continue
        if not info["is_real"]:
            phantom.append(slug); continue
        p = store.mint_person(); people[slug] = p
        store.declare_subject(("person", p))
        sr = store.add_source_record("statscrew", f"person/{slug}")
        store.add_denotation(sr, p, ["source_native_id"], "exact-id",
                             matched_against=f"statscrew:{slug} born={info.get('born')}")
        for pred, key in (("birth_date", "born"), ("college", "college"),
                          ("death_date", "deceased"), ("high_school", "high_school")):
            v = info.get(key)
            if v: store.add_claim(sr, ("person", p), pred, v, "fetch-2026")
        if slug_name.get(slug):
            store.add_claim(sr, ("person", p), "name", slug_name[slug],
                            "fetch-2026", kind="observed", stated_by="StatsCrew")
        px = [x for x in info["xref"] if x.startswith("p-")]
        if px:
            xref += 1
            store.add_claim(sr, ("person", p), "also_played", px[0], "fetch-2026",
                            note="bidirectional player/coach cross-reference followed")

    stints = 0
    for (team, year), lst in sorted(club_seasons.items()):
        for slug, name in lst:
            p = people.get(slug)
            if p is None: continue
            subj = ("stint", p, team, f"y{year}")
            store.declare_subject(subj)
            sr = store.add_source_record("statscrew", f"roster/{team}-{year}#coach:{slug}")
            store.add_claim(sr, subj, "role_title", "Head Coach", year)
            store.add_claim(sr, subj, "is_head_coach", True, year)
            if len(lst) > 1:
                store.add_claim(sr, subj, "shared_or_split_season", True, year,
                                note=f"{len(lst)} head coaches recorded for this club-season")
            stints += 1

    store.save(os.path.join(BASE, "build", "coaches-nfl.json"))
    log(f"phantom c- pages skipped: {len(phantom)}  {phantom[:6]}")
    log(f"player/coach cross-references followed: {xref}")
    log(f"persons {len(store.persons)}  stints {stints}  claims {len(store.claims)}")
    open(os.path.join(BASE, "build", "ingest-coaches-nfl.log"), "w").write("\n".join(LOG))

if __name__ == "__main__":
    main()
