"""Ingest StatsCrew team-season statistics.

THREE THINGS THIS MUST GET RIGHT, all established before a line was written:

1. The <tbody><td> parse trap AND commented-out grouping headers. Cells are
   chunked by header length, and HTML comments are stripped first - reading them
   as columns invented a "Tackles" column filled 84% in the 1920s.

2. The subject is (person, season, CLUB). 5,007 person-seasons are at more than
   one club, so a (person, season) shape would collapse two clubs' numbers into
   one and manufacture false contests.

3. A CALCULATED column is not an observation. `Rating` is 100% populated back to
   1923 from a formula adopted in 1973; `Comp %`, `Yds/Att`, `TD %`, `Int %`,
   `X/CP %` and `FG %` are arithmetic on counted columns in every era. These file
   as source_derived. gate_anachronism gets ~45,000 chances to fire and must fire
   on none, because the ingest never offers it one.

Identity: the global person id from build-reports/identity.json where the slug is
known, adopted rather than minted - minting here would recreate the store-local
collision that made p_000190 three different men.

  LEAGUE=NFL YEAR=1950 python3 src/ingest_stats.py
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
os.environ.setdefault("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
from model import Store, StoreError
from measure_stats_census import tables
import fetch_statscrew as F

LEAGUE = os.environ.get("LEAGUE", "NFL")
YEAR = int(os.environ.get("YEAR", "1950"))
SEASON = f"{LEAGUE}-{YEAR}"
DECL = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
SC = DECL["stat_columns"]
CALCULATED = {c for c, v in SC.get("columns", {}).items() if v.get("calculated")}
if not CALCULATED:
    CALCULATED = {"Comp %", "Yds/Att", "TD %", "Int %", "Rating", "X/CP %", "FG %"}

IDENT = {}
_p = os.path.join(BASE, "build-reports", "identity.json")
if os.path.exists(_p):
    for gid, v in json.load(open(_p)).items():
        for s in v["slugs"]: IDENT[s] = gid

# APPLICABILITY, enforced at the write. A source that writes 0 where a measure
# does not apply is indistinguishable by fill from one that measured 0 - so the
# declaration says which, and a column inapplicable in this league is REFUSED
# rather than filed as an observation of zero.
APPLIC = SC.get("applicability", {})
def inapplicable(col):
    a = APPLIC.get(col)
    if not a or not isinstance(a, dict) or "applicable_in" not in a: return False
    ok = a["applicable_in"]
    if ok == ["ALL"] or ok == "ALL": return False
    return LEAGUE not in ok
UNRESOLVED = set(APPLIC.get("_unresolved", {}).get("columns", []))

LOG, DEV = [], []
def log(m): LOG.append(m); print(m, flush=True)


def main():
    store = Store(); store.add_source(DECL)
    teams = F.teams_in(LEAGUE, YEAR)
    rows = cells = obs = derived = 0
    refused_inapplicable = collections.Counter()
    unknown_slug = 0
    fill = collections.defaultdict(lambda: [0, 0])
    for team in sorted(teams):
        key = f"S_{team}_{YEAR}"
        p = os.path.join(F.CACHE, key + ".html")
        if not os.path.exists(p):
            log(f"  {team}: no stats page cached"); continue
        html = open(p, encoding="utf-8", errors="replace").read()
        # slug per player NAME, read from the links on this page
        slugs = dict((n.strip(), s) for s, n in
                     re.findall(r'/football/stats/(p-[a-z0-9\-]+)"[^>]*>([^<]+)</a>', html))
        for hdr, rs in tables(html):
            if "Player" not in hdr: continue
            for r in rs:
                nm = r.get("Player", "").strip()
                if not nm or nm.lower() in ("totals", "total"): continue
                slug = slugs.get(nm)
                if not slug:
                    unknown_slug += 1
                    continue                      # no source-native id: refuse
                gid = IDENT.get(slug)
                pid = store.adopt_person(gid) if gid else store.mint_person()
                subj = ("stint", pid, team, SEASON)
                store.declare_subject(("person", pid)); store.declare_subject(subj)
                sr = store.add_source_record("statscrew", f"stats/{team}-{YEAR}#{nm}")
                if gid:
                    store.add_denotation(sr, pid, ["source_native_id"], "exact-id",
                                         matched_against="statscrew:" + slug)
                rows += 1
                for c in hdr:
                    if c == "Player": continue
                    v = r.get(c, "")
                    fill[c][1] += 1
                    if v == "": continue
                    if inapplicable(c):
                        refused_inapplicable[c] += 1
                        continue          # schema padding, not an observation
                    fill[c][0] += 1; cells += 1
                    calc = c in CALCULATED
                    note = ("computed by the source from counted columns; "
                            "not an observation of this season") if calc else None
                    if c in UNRESOLVED:
                        note = ("APPLICABILITY UNRESOLVED for this league: a zero "
                                "here may be schema padding rather than a measured "
                                "zero. Do not render as a fact about the person.")
                    store.add_claim(sr, subj, c, v, YEAR,
                                    kind="source_derived" if calc else "observed",
                                    stated_by="StatsCrew", note=note)
                    if calc: derived += 1
                    else: obs += 1
    # THE DECLARATION IS LOAD-BEARING: compare fill against the generated census
    # Compare against THIS LEAGUE's figure, not a pooled decade average. The NFL
    # has a continuous statistical tradition; the AAFC, both AFLs, the WFL and the
    # CFL recorded different things. Pooled, the 1950 NFL ingest deviated on nine
    # columns against numbers true of no league.
    for c, (a, b) in fill.items():
        if not b or inapplicable(c): continue   # padding is not a fill deviation
        actual = round(100.0 * a / b, 1)
        col = SC.get("columns", {}).get(c, {})
        dec = (YEAR // 10) * 10
        pred = col.get("fill_by_league_decade", {}).get(f"{LEAGUE}-{dec}")
        if pred is None:
            pred = col.get("fill_by_league", {}).get(LEAGUE)
        if pred is None:
            DEV.append((SEASON, c, None, actual, f"declaration makes no prediction for {LEAGUE}"))
        elif abs(actual - pred) > 20.0:
            DEV.append((SEASON, c, pred, actual,
                        f"fill deviates >20 points from the {LEAGUE} figure"))
    if refused_inapplicable:
        log("  refused as INAPPLICABLE in this league: " +
            ", ".join(f"{k}={v}" for k, v in refused_inapplicable.most_common()))
    log(f"rows {rows}  cells {cells}  observed {obs}  source_derived {derived}  "
        f"rows refused for no slug {unknown_slug}")
    for d in DEV: log(f"  DEV {d[1]}: declared {d[2]} actual {d[3]} -- {d[4]}")
    os.makedirs(os.path.join(BASE, "build"), exist_ok=True)
    store.save(os.path.join(BASE, "build", f"stats-{LEAGUE.lower()}-{YEAR}.json"))
    json.dump([list(d) for d in DEV], open(os.path.join(
        BASE, "build", f"devstats-{LEAGUE.lower()}-{YEAR}.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
