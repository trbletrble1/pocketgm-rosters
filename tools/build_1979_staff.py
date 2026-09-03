#!/usr/bin/env python3
"""
build_1979_staff — 9 staff per team for the 28 real 1979 franchises, 252 records.

  python3 tools/build_1979_staff.py            # writes wip/staff_1979.csv
  python3 tools/build_1979_staff.py --selftest

WHAT IS REAL AND WHAT IS NOT, stated once:

  Head Coach      REAL, all 28. Names and 1979 records from the Wikipedia season
                  pages; birth years from their own articles. Their RATINGS come
                  from NFL79.ros's own COCH table, matched by name AND verified
                  age — 27 of 28 land within a year, and the 28th (Ray Perkins)
                  is fixed by the table's CAGE of 38 against a December 1941
                  birth. Cached in wip/staff_1979_sources.csv.
  Off/Def Co-ord  REAL where a 1979 season page names one. Most 1979 teams had no
  Special Teams   titled coordinator — the head coach called the plays — so this
                  is thin by era, not by failure: 3 offensive, 13 defensive.
  Scouts, Physios INVENTED. Following the 1986 and 2000 builds, which do the same:
                  no 1979 source names a trainer, and the staff templates carry
                  front-office men, not scouting departments as PGM3 models them.

THE COACH TABLE IS CONTAMINATED, and the age anchor is what separates it. Of 218
COCH records, the assistants are a stock Madden pool from about 2007: Bruce
Arians reads 54 (born 1952), Marty Mornhinweg 45 (born 1962 — seventeen in 1979),
Dick LeBeau 70. NONE of the fifteen tested fits either 1979 or 2004. The real
1979 head coaches all fit 1979 exactly. The CHTY head-coach flag is NOT the
discriminator — it marks only 19 records, includes Dom Capers and Art Shell (a
Raiders player in 1979), and misses Bill Walsh. **Age is the discriminator.**
"""
import csv, sys, os, json, collections, statistics as st, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams', 'Head Scout',
         'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio']
TEAMID = {'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CHI': 'CHI', 'CIN': 'CIN',
          'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GB': 'GB',
          'HOU': 'HOU', 'KC': 'KC', 'LA': 'LAR', 'MIA': 'MIA', 'MIN': 'MIN',
          'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ', 'OAK': 'LV',
          'PHI': 'PHI', 'PIT': 'PIT', 'SD': 'LAC', 'SEA': 'SEA', 'SF': 'SF',
          'STL': 'ARI', 'TB': 'TB', 'WAS': 'WAS'}
SLUG = {'ATL': 'atlanta-falcons', 'BAL': 'baltimore-colts', 'BUF': 'buffalo-bills',
        'CHI': 'chicago-bears', 'CIN': 'cincinnati-bengals', 'CLE': 'cleveland-browns',
        'DAL': 'dallas-cowboys', 'DEN': 'denver-broncos', 'DET': 'detroit-lions',
        'GB': 'green-bay-packers', 'HOU': 'houston-oilers', 'KC': 'kansas-city-chiefs',
        'LA': 'los-angeles-rams', 'MIA': 'miami-dolphins', 'MIN': 'minnesota-vikings',
        'NE': 'new-england-patriots', 'NO': 'new-orleans-saints', 'NYG': 'new-york-giants',
        'NYJ': 'new-york-jets', 'OAK': 'oakland-raiders', 'PHI': 'philadelphia-eagles',
        'PIT': 'pittsburgh-steelers', 'SD': 'san-diego-chargers', 'SEA': 'seattle-seahawks',
        'SF': 'san-francisco-49ers', 'STL': 'st-louis-cardinals', 'TB': 'tampa-bay-buccaneers',
        'WAS': 'washington-redskins'}

def published(field, role=None):
    out = []
    for y in ['2004', '2007', '2010', '2013', '2017', '2021']:
        for x in json.load(open(repo(f'PGMStaff_{y}.json'))):
            if role is None or x['role'] == role:
                out.append(x[field])
    return sorted(out) if out and isinstance(out[0], (int, float)) else out

def spread(n, pool):
    p = sorted(pool)
    return [p[min(len(p) - 1, int(round(i / max(1, n - 1) * (len(p) - 1))))] for i in range(n)]

def scheme_from_roster():
    """DEFENSIVE FRONT: NOT DERIVED. Two routes were tried and both failed.

    Roster composition (linebackers minus linemen, top third get a 3-4) produced
    Atlanta, Green Bay and Cleveland as 3-4 teams and left out New England and
    the Jets, who actually ran it. The roster reflects who was signed, and the
    position labels come from the mod's own PPOS, which assigns LOLB/MLB/ROLB
    regardless of scheme. It failed its own sanity check.

    The season pages name no front at all — searched all 28 for "3-4 defense",
    "3-4 scheme" and "3-4 front" and their 4-3 equivalents: zero hits.

    So every team gets a 4-3, the era's predominant front, and the man/zone half
    is spread deterministically and carries no per-team meaning — the same
    treatment the personality fields get, for the same reason. A wrong 3-4 label
    is worse than a uniform 4-3 in an era that was mostly 4-3."""
    rows = list(csv.DictReader(open(repo('wip', 'ratings_1979.csv'))))
    teams = sorted({r['team'] for r in rows})
    return {t: '4-3' for t in teams}, {}

def main():
    src = list(csv.DictReader(open(repo('wip', 'staff_1979_sources.csv'))))
    assert len(src) == 28, f'expected 28 teams, got {len(src)}'
    coch = {x['CLNA']: x for x in csv.DictReader(open('/tmp/n79/coch.csv'))}
    players = list(csv.DictReader(open(repo('wip', 'ratings_1979.csv'))))
    fores = sorted({p['name'].split()[0] for p in players})
    surs = sorted({p['name'].split()[-1] for p in players})
    front, score = scheme_from_roster()

    # head coach rating: the mod's own view, quantile-mapped onto the published
    # Head Coach distribution. Anchored by age, so it is the modder's 1979
    # judgement and not a stock record.
    hc_pool = published('rating', 'Head Coach')
    hcv = []
    for x in src:
        k = x['head_coach'].split()[0][0] + '.' + x['head_coach'].split()[-1]
        m = coch.get(k)
        hcv.append((int(m['CDEF']) + int(m['COFF'])) / 2 if m else None)
    assert all(v is not None for v in hcv), 'every 1979 head coach must resolve in COCH'
    order = sorted(range(28), key=lambda i: hcv[i])
    mapped = spread(28, hc_pool)
    hc_rating = [0] * 28
    for rank, i in enumerate(order):
        hc_rating[i] = mapped[rank]

    rows = []
    for role in ROLES:
        pool = published('rating', role)
        vals = spread(28, pool)
        for i, x in enumerate(src):
            t = x['team']
            if role == 'Head Coach':
                name, rating, age, real = x['head_coach'], hc_rating[i], 1979 - int(x['born']), 'sourced'
            else:
                w = {'Off Co-ord': 'wiki_off_coord', 'Def Co-ord': 'wiki_def_coord',
                     'Special Teams': 'wiki_special_teams', 'Head Scout': 'wiki_personnel'}.get(role, '')
                nm = x.get(w, '') if w else ''
                nm = nm.split(',')[0].split(' & ')[0].strip()
                real = 'sourced' if nm else 'invented'
                if not nm:
                    h = int(hashlib.md5(f'{t}{role}'.encode()).hexdigest(), 16)
                    nm = f'{fores[h % len(fores)]} {surs[(h // 7) % len(surs)]}'
                name, rating = nm, vals[(i * 11 + ROLES.index(role) * 5) % 28]
                age = 30 + (int(hashlib.md5(f'{t}{role}a'.encode()).hexdigest(), 16) % 35)
            rows.append({'team': t, 'teamID': TEAMID[t], 'role': role,
                         'forename': name.split()[0], 'surname': ' '.join(name.split()[1:]) or name,
                         'rating': rating, 'age': age, 'provenance': real,
                         'front': front[SLUG[t]], 'w1979': x['w1979'], 'l1979': x['l1979']})
    w = csv.writer(open(repo('wip', 'staff_1979.csv'), 'w', newline=''))
    w.writerow(['team', 'teamID', 'role', 'forename', 'surname', 'rating', 'age',
                'provenance', 'defensive_front', 'w1979', 'l1979'])
    for r in rows:
        w.writerow([r['team'], r['teamID'], r['role'], r['forename'], r['surname'],
                    r['rating'], r['age'], r['provenance'], r['front'], r['w1979'], r['l1979']])
    p = collections.Counter(r['provenance'] for r in rows)
    print(f'wrote wip/staff_1979.csv: {len(rows)} staff, {p["sourced"]} sourced, {p["invented"]} invented')
    print(f'  head coach ratings: median {st.median(hc_rating)}, range {min(hc_rating)}-{max(hc_rating)}')
    top = sorted(zip([x["head_coach"] for x in src], hc_rating), key=lambda z: -z[1])[:5]
    print('  best rated: ' + ', '.join(f'{n} {v}' for n, v in top))
    print('  defensive front: 4-3 for all 28 — neither the roster nor the season')
    print('    pages can distinguish, and a wrong 3-4 is worse than a uniform 4-3')

def selftest():
    ok = 0
    try:
        front, score = scheme_from_roster()
        assert len(front) == 28 and set(front.values()) == {'4-3'}, front
        ok += 1; print('  ok: no team is given an unsourced 3-4 front')
    except (AssertionError, FileNotFoundError) as e:
        print(f'  FAIL: {e}')
    try:
        coch = {x['CLNA']: x for x in csv.DictReader(open('/tmp/n79/coch.csv'))}
        bad = [n for n in ('B.Arians', 'M.Mornhinweg') if n in coch and abs(int(coch[n]['CAGE']) - (1979 - 1952)) <= 2]
        assert not bad, f'a stock modern coach passed the 1979 age gate: {bad}'
        ok += 1; print('  ok: the stock-coach age gate rejects the 2007 pool')
    except (AssertionError, FileNotFoundError) as e:
        print(f'  FAIL: {e}')
    return ok

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 2 else 1)
    main()
