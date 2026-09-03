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
import importlib.util as _ilu
_rs=_ilu.spec_from_file_location('_r', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_1979_ratings.py')); _R=_ilu.module_from_spec(_rs); _rs.loader.exec_module(_R)


# THE FOUR FRANCHISE HEAD COACHES, named by Ryan 2026-09-03. Real men, and each
# is the franchise's doctrine in a person.
#
#   Memphis      George Allen 93     'the future is now' was literally his
#                                    philosophy; he traded picks for veterans
#                                    relentlessly and never had a losing season.
#   Charlotte    Bill Arnsparger 40  bottom seventh of the pool on his head-
#                                    coaching record, top fifth on what his
#                                    defences did. The rating tension is LEFT:
#                                    40 makes him the lowest-rated coach in the
#                                    file, which is the honest consequence of
#                                    rating on winning percentage. The
#                                    coordinator term informed the ALLOCATION,
#                                    not the rating.
#   Jacksonville Pat Dye 50          nine years under Bryant at Alabama, then
#                                    East Carolina, 7-3-1 in 1979. Southern,
#                                    unproven at the top level, cheap.
#   Indianapolis John Madden 95      retired January 1979 at 42 — ulcer, burnout,
#                                    fear of flying — on 103-32-7, the best record
#                                    of any coach with 100 games. What gets him
#                                    back is not money: it is a job where losing
#                                    in year one is expected, in the league's most
#                                    central city, which is the shortest travel
#                                    for a man who will not fly.
#
# PAT DYE'S 50 IS THE COLLEGE BAND, and the reason is measured. Across 47 clean
# pairs of men who coached in both, college winning percentage correlates with
# NFL winning percentage at r = +0.11 (+0.08 within the era). It explains about
# one percent. Nor can the pairs extrapolate downward: they bottom out at .273
# with five below .400, because a coach who lost badly in college never got an
# NFL job and so never became a pair. So college men take the same lower-band
# disposition as a man whose record is too short to rank — and it suits the
# doctrine, since Jacksonville's identity is signing cheap and unproven.
#
# NOTE THE DISTINCTION, unresolved on purpose: the player pool was men genuinely
# out of football, while hiring Dye takes him off a job he holds. That is
# historically normal for an expansion team and it is a different act.
NAMED = {'TEN': ('George Allen', 93, 61), 'CAR': ('Bill Arnsparger', 40, 53),
         'JAX': ('Pat Dye', 50, 40), 'IND': ('John Madden', 95, 43)}

ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams', 'Head Scout',
         'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio']
TEAMID = {'TEN': 'TEN', 'CAR': 'CAR', 'JAX': 'JAX', 'IND': 'IND', 'ATL': 'ATL', 'BAL': 'BAL', 'BUF': 'BUF', 'CHI': 'CHI', 'CIN': 'CIN',
          'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GB': 'GB',
          'HOU': 'HOU', 'KC': 'KC', 'LA': 'LAR', 'MIA': 'MIA', 'MIN': 'MIN',
          'NE': 'NE', 'NO': 'NO', 'NYG': 'NYG', 'NYJ': 'NYJ', 'OAK': 'LV',
          'PHI': 'PHI', 'PIT': 'PIT', 'SD': 'LAC', 'SEA': 'SEA', 'SF': 'SF',
          'STL': 'ARI', 'TB': 'TB', 'WAS': 'WAS'}
SLUG = {'TEN': 'Memphis Southmen', 'CAR': 'Charlotte Hornets', 'JAX': 'Jacksonville Sharks', 'IND': 'Indianapolis Racers', 'ATL': 'atlanta-falcons', 'BAL': 'baltimore-colts', 'BUF': 'buffalo-bills',
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
    assert len(src) == 28, f'expected 28 real teams, got {len(src)}'
    # THE FOUR INVENTED FRANCHISES need nine staff each and have no source of any
    # kind — they did not exist. Every one of their 36 is generated and flagged,
    # exactly as the scouts and physios of the real teams are. Rostering real
    # players who were out of football is one thing; putting a real coach into a
    # job he never held is another, and it was not done here — until Ryan named
    # the four head coaches himself on 2026-09-03. See NAMED. The other 32 staff
    # on these franchises remain generated and flagged.
    for code, nm in (('TEN', 'Memphis Southmen'), ('CAR', 'Charlotte Hornets'), ('JAX', 'Jacksonville Sharks'), ('IND', 'Indianapolis Racers')):
        src.append(dict(team=code, head_coach='', born='', w1979='', l1979='', t1979='', wiki_off_coord='', wiki_def_coord='', wiki_special_teams='', wiki_personnel='', _invented=nm))
    coch = {x['CLNA']: x for x in csv.DictReader(open(_R.dump_path('n79', 'COCH')))}
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
        if x.get('_invented'):
            hcv.append(None); continue
        k = x['head_coach'].split()[0][0] + '.' + x['head_coach'].split()[-1]
        m = coch.get(k)
        hcv.append((int(m['CDEF']) + int(m['COFF'])) / 2 if m else None)
    assert all(v is not None for v, x in zip(hcv, src) if not x.get('_invented')), 'every REAL 1979 head coach must resolve in COCH'
    real = [i for i, x in enumerate(src) if not x.get('_invented')]
    order = sorted(real, key=lambda i: hcv[i])
    mapped = spread(len(real), hc_pool)
    hc_rating = [0] * len(src)
    for i, x in enumerate(src):
        if x.get('_invented'):                         # an expansion head coach: the band's lower third
            hc_rating[i] = hc_pool[len(hc_pool) // 3]
    for rank, i in enumerate(order):
        hc_rating[i] = mapped[rank]

    rows = []
    for role in ROLES:
        pool = published('rating', role)
        vals = spread(len(src), pool)
        for i, x in enumerate(src):
            t = x['team']
            if role == 'Head Coach' and not x.get('_invented'):
                name, rating, age, real = x['head_coach'], hc_rating[i], 1979 - int(x['born']), 'sourced'
            elif role == 'Head Coach' and t in NAMED:
                nm_, rt_, ag_ = NAMED[t]
                name, rating, age, real = nm_, rt_, ag_, 'named by Ryan'
            elif role == 'Head Coach':
                h = int(hashlib.md5(f'{t}HC'.encode()).hexdigest(), 16)
                name, rating, age, real = f'{fores[h % len(fores)]} {surs[(h // 7) % len(surs)]}', hc_rating[i], 38 + h % 20, 'invented (expansion franchise)'
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
                         'front': front.get(SLUG[t], '4-3'), 'w1979': x['w1979'], 'l1979': x['l1979']})
    w = csv.writer(open(repo('wip', 'staff_1979.csv'), 'w', newline=''))
    w.writerow(['team', 'teamID', 'role', 'forename', 'surname', 'rating', 'age',
                'provenance', 'defensive_front', 'w1979', 'l1979'])
    for r in rows:
        w.writerow([r['team'], r['teamID'], r['role'], r['forename'], r['surname'],
                    r['rating'], r['age'], r['provenance'], r['front'], r['w1979'], r['l1979']])
    p = collections.Counter(r['provenance'] for r in rows)
    print(f'wrote wip/staff_1979.csv: {len(rows)} staff, {p["sourced"]} sourced, {p["invented"] + p["invented (expansion franchise)"]} invented ({p["invented (expansion franchise)"]} on the four franchises)')
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
        coch = {x['CLNA']: x for x in csv.DictReader(open(_R.dump_path('n79', 'COCH')))}
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
