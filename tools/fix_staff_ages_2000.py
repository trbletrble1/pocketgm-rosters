"""Replace drawn staff ages with sourced birth years, and recompute startSeason.

The 2000 staff ages had essentially no relationship to the men: only 13 of 89
checkable coaches were within +/-2 years of their real age, 35 were off by 10 or
more, spanning -19 to +26. Tony Dungy shipped at 70 against a real 45. The
distribution was plausible (median 49.5, range 30-72, next to the published
files) with no per-person signal -- the same shape as the stamina and appearance
bugs, and it passed every check in the suite because internal consistency can
only see impossibility, not wrongness.

startSeason is a fitted function of age (r ~ -0.96, residual sd ~2 in every
modern published file), so a wrong age produced a wrong startSeason while the
correlation still looked perfect. Each record's own residual is preserved here
so only the age-driven shift moves.

Sources in sources/coaches_2000_birth_years.csv, one row per record with
provenance. Jim Mora is keyed on (team, role) because the file holds two
different men, father at Indianapolis and son at San Francisco.
"""
import json, csv, sys, statistics, collections

COACH = {'Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams'}
PATH  = 'PGMStaff_2000.json'

def main():
    recs = json.load(open(PATH, encoding='utf-8'))
    n_in = len(recs)
    src = {}
    for r in csv.DictReader(open('sources/coaches_2000_birth_years.csv', encoding='utf-8')):
        src[(r['name'], r['team'], r['role'])] = (int(r['age_2000']), r['source'])
    assert len(src) == 124, f'expected 124 sourced rows, got {len(src)}'

    co = [p for p in recs if p['role'] in COACH and p['teamID'] != 'Free Agent']
    # the four with no birth year anywhere: derive from the sourced cohort's
    # own role median rather than drawing. Tagged, counted and reported.
    st_med = int(statistics.median(
        [a for (n, t, r), (a, s) in src.items() if r == 'Special Teams']))

    # fit startSeason on age from this file's own current relationship
    pts = [(p['age'], p['startSeason']) for p in recs]
    ma = statistics.mean(a for a, _ in pts); ms = statistics.mean(s for _, s in pts)
    b  = (sum((a - ma) * (s - ms) for a, s in pts) / len(pts)) / statistics.pvariance([a for a, _ in pts])
    a0 = ms - b * ma

    before_app = [tuple(p['appearance']) for p in recs]
    changed = derived = 0
    for p in recs:
        if p['role'] not in COACH or p['teamID'] == 'Free Agent':
            continue
        k = (f"{p['forename']} {p['surname']}", p['teamID'], p['role'])
        if k in src:
            new_age, _ = src[k]
        else:
            new_age = st_med; derived += 1
        if new_age == p['age']:
            continue
        resid = p['startSeason'] - (a0 + b * p['age'])   # keep this record's own noise
        p['age'] = new_age
        # the published files hold startSeason in [1988, 2026]; young coaches
        # with a positive residual overshoot the ceiling, so clamp to the
        # observed range rather than inventing a value outside it
        p['startSeason'] = max(1988, min(2026, int(round(a0 + b * new_age + resid))))
        changed += 1

    assert len(recs) == n_in, f'record count moved {n_in} -> {len(recs)}'
    assert [tuple(p['appearance']) for p in recs] == before_app, \
        'staff appearance changed -- it must not depend on age'
    bad = [(p['forename'], p['surname'], p['age']) for p in recs
           if p['role'] in COACH and p['age'] < 28]
    assert not bad, f'coach under 28: {bad}'
    ss = [p['startSeason'] for p in recs]
    assert 1988 <= min(ss) and max(ss) <= 2026, \
        f'startSeason outside the published 1988-2026: {min(ss)}-{max(ss)}'

    print(f'    ages replaced   {changed}/{len(co)} real coaches '
          f'({len(src)} sourced, {derived} derived from the Special Teams median {st_med})')
    a = [p['age'] for p in recs if p['role'] in COACH and p['teamID'] != 'Free Agent']
    print(f'    coach age       {min(a)}-{max(a)}, median {statistics.median(a)}')
    json.dump(recs, open(PATH, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f'    wrote {PATH} ({n_in} records)')

if __name__ == '__main__':
    main()
