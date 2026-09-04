"""Recompute every field census from the cache, stating BOTH denominators.

The census in declarations/statscrew.json was hand-computed from a metric that
silently conditioned on column presence (ingest_season's fill_seen only counted
rows on pages that CARRIED the column). Where a column is absent from some of a
league-season's pages the two denominators diverge - WFL-1975 games_started was
recorded as 25.2% when the fraction of all rows carrying a value is 13.5%.

Reads the cache only; makes no network requests.

  python3 src/measure_census.py           # report
  python3 src/measure_census.py --write   # report and update the declaration
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
import fetch_statscrew as F

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
COLS = {"#": "jersey", "GP": "games_played", "GS": "games_started",
        "Birth Date": "birth_date", "Hometown": "hometown", "College": "college"}


def league_years():
    seen = set()
    for f in sorted(glob.glob(os.path.join(BASE, "build-reports", "sweep-*.json"))):
        for s in json.load(open(f)).get("summary", []):
            k = (s["league"], s["year"])
            if k not in seen:
                seen.add(k); yield k


def measure(league, year):
    acc = {c: [0, 0, 0, 0] for c in COLS}     # filled, rows_with_col, rows_total, pages_without
    empty_pages = []
    try:
        teams = F.teams_in(league, year)
    except Exception:
        return None, None
    for t in sorted(teams):
        try:
            hdr, rows, _ = F.parse_roster(F.team_roster(t, year))
        except Exception:
            continue
        if not rows:
            empty_pages.append(t)
            continue
        for c in COLS:
            has = c in hdr
            if not has:
                acc[c][3] += 1
            for r in rows:
                acc[c][2] += 1
                if has:
                    acc[c][1] += 1
                    if r.get(c, "") != "":
                        acc[c][0] += 1
    return acc, empty_pages


def entry(filled, with_col, total, pages_without):
    """A bare number where the denominators agree; both where they do not."""
    if not total:
        return None
    if not with_col:
        return {"column_absent_from_every_page": True, "fill_of_all_rows": 0.0,
                "pages_missing_the_column": pages_without}
    cond = round(100.0 * filled / with_col, 1)
    absol = round(100.0 * filled / total, 1)
    if abs(cond - absol) <= 0.1:
        return cond                            # unambiguous: one number says it all
    return {"fill_where_column_present": cond,
            "fill_of_all_rows": absol,
            "pages_missing_the_column": pages_without,
            "_why_two_numbers": "the column is absent from some pages of this "
                                "league-season, so a single figure cannot say "
                                "which denominator it used"}


def main():
    write = "--write" in sys.argv
    decl_p = os.path.join(BASE, "declarations", "statscrew.json")
    decl = json.load(open(decl_p))
    fa = decl["field_availability"]
    census = {f: {} for f in COLS.values()}
    empties, changed = {}, []
    for league, year in league_years():
        acc, empty = measure(league, year)
        if acc is None:
            continue
        key = f"{league}-{year}"
        if empty:
            empties[key] = empty
        for col, field in COLS.items():
            e = entry(*acc[col])
            if e is None:
                continue
            census[field][key] = e
            old = fa.get(field, {}).get("census_by_league_season", {}).get(key)
            if isinstance(e, dict) and isinstance(old, (int, float)):
                changed.append((key, field, old, e.get("fill_of_all_rows")))
    print(f"league-seasons measured: {len(set(k for f in census.values() for k in f))}")
    print(f"\ncensus figures that were a CONDITIONAL fill stored as if absolute: {len(changed)}")
    for k, f, old, new in changed:
        print(f"   {k:>10} {f:<14} stored {old:>5}%  ->  fill_of_all_rows {new:>5}%")
    print(f"\nteam pages listed by a league page but parsing to ZERO rows: "
          f"{sum(len(v) for v in empties.values())} across {len(empties)} league-seasons")
    for k, v in sorted(empties.items())[:15]:
        print(f"   {k}: {v}")
    if write:
        for field, c in census.items():
            fa.setdefault(field, {})["census_by_league_season"] = c
            fa[field]["kind"] = "per_league_season"
            fa[field]["_denominator_rule"] = (
                "a bare number means the column is on every page of that "
                "league-season and the two denominators agree; an object means "
                "they do not, and names both")
        decl["empty_roster_pages"] = {
            "_what": "teams a league-year page links but whose roster page parses "
                     "to zero rows. They contribute nothing and, before this was "
                     "measured, contributed it silently.",
            "_measured": "2026-09-04, from cache",
            "by_league_season": empties}
        json.dump(decl, open(decl_p, "w"), indent=1)
        print("\ndeclaration updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
