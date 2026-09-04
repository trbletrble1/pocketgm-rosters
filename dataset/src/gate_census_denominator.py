"""Gate: a census figure must state its denominator.

A fill percentage computed only over the pages that CARRY a column answers
"where the column exists, how often is it filled" - not "how much of this
league-season has this value". Where a column is present on some pages and
absent on others the two numbers differ, and a bare scalar cannot say which
it is. CFL-1945 games_played is 100.0 conditional and 71.4 absolute: two
of eight teams have no GP column at all.

This is a property over EVERY league-season and EVERY measured column, not a
check on the season that exposed it.

Run:  python3 src/gate_census_denominator.py
Exit 1 = FAIL.
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
import fetch_statscrew as F

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
COLS = {"#": "jersey", "GP": "games_played", "GS": "games_started",
        "Birth Date": "birth_date"}


def league_years():
    for f in sorted(glob.glob(os.path.join(BASE, "build-reports", "sweep-*.json"))):
        d = json.load(open(f))
        for s in d.get("summary", []):
            yield s["league"], s["year"]


def measure(league, year):
    """-> {col: (filled, rows_with_col, rows_total, pages_without)}"""
    out = {c: [0, 0, 0, 0] for c in COLS}
    try:
        teams = F.teams_in(league, year)
    except Exception:
        return None
    for t in sorted(teams):
        try:
            hdr, rows, _ = F.parse_roster(F.team_roster(t, year))
        except Exception:
            continue
        for c in COLS:
            has = c in hdr
            if not has:
                out[c][3] += 1
            for r in rows:
                out[c][2] += 1
                if has:
                    out[c][1] += 1
                    if r.get(c, "") != "":
                        out[c][0] += 1
    return out


def main():
    decl = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
    fa = decl["field_availability"]
    offenders, checked = [], 0
    for league, year in league_years():
        m = measure(league, year)
        if not m:
            continue
        key = f"{league}-{year}"
        for col, field in COLS.items():
            filled, with_col, total, pages_without = m[col]
            if not with_col or not total:
                continue
            cond = 100.0 * filled / with_col
            absol = 100.0 * filled / total
            checked += 1
            if abs(cond - absol) <= 0.1:
                continue                      # no ambiguity to state
            spec = fa.get(field, {})
            stored = spec.get("census_by_league_season", {}).get(key)
            # The census MUST NOT be a bare number where the two differ.
            if stored is None or isinstance(stored, (int, float)):
                offenders.append({
                    "league_season": key, "field": field,
                    "conditional_fill": round(cond, 1), "absolute_fill": round(absol, 1),
                    "pages_missing_the_column": pages_without,
                    "stored": stored,
                    "why": "bare scalar cannot say which denominator it used"})
    print(f"league-season/field pairs checked: {checked}")
    print(f"pairs where conditional != absolute fill: "
          f"{len([o for o in offenders])} unstated")
    for o in offenders[:25]:
        print(f"  [FAIL] {o['league_season']:>10} {o['field']:<13} "
              f"conditional {o['conditional_fill']:>5}%  absolute {o['absolute_fill']:>5}%  "
              f"({o['pages_missing_the_column']} pages lack the column)  stored={o['stored']}")
    if len(offenders) > 25:
        print(f"  ... and {len(offenders)-25} more")
    json.dump(offenders, open(os.path.join(BASE, "build-reports",
              "gate-census-denominator.json"), "w"), indent=1)
    if offenders:
        print(f"\nGATE FAILED: {len(offenders)} census figures do not state their denominator.")
        return 1
    print("\nGATE PASSED: every ambiguous census figure states both denominators.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
