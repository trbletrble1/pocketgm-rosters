#!/usr/bin/env python3
"""
build_1979_franchises — the four invented 1979 franchises, from the 308-man pool
of men genuinely out of football that year. No real 1979 roster is touched: none
of the 308 appears in the 1,408-man spine, and that is asserted, not assumed.

  python3 tools/build_1979_franchises.py            # writes wip/franchises_1979.csv
  python3 tools/build_1979_franchises.py --selftest

  TEN  Memphis Southmen      blocked in court, impatient. Signed Csonka, Kiick and
                             Warfield away from Miami in 1974, applied to join the
                             NFL, was refused, sued under antitrust, lost. Four
                             years of doing everything right and being told no.
                             So: four men bought outright and everything else
                             young and cheap, because the expensive slots are gone.
  CAR  Charlotte Hornets     inheritance as strategy. The New York Stars ran out of
                             money mid-1974 and moved to Charlotte in-season. The
                             city got somebody else's failure and made the best of
                             it. So: men other teams let go — released, career
                             ended, fell out with a coach. NOT the injured.
  JAX  Jacksonville Sharks   folded mid-1974 owing money to players and vendors.
                             An ownership group that will not overspend again.
                             So: cheap, and leaning Southern. A tendency, not a rule.
  IND  Indianapolis Racers   no WFL team, no grievance, a domed stadium going up on
                             speculation. Nothing to prove, so they can be patient.
                             So: the injured, whom their own teams still wanted.
                             Bad on purpose, with real talent arriving.

THE INJURY MECHANIC. An injured man's rating source is his 1978 form, which is
what he can do healthy. So potential holds that level and the 1979 rating sits 14
below it. Precedented: 69 veterans in the published files carry 10 or more points
of headroom, across four of the six, up to 46.

SCARCE POSITIONS ARE RESERVED BEFORE ANY DOCTRINE RUNS. The pool is whoever fell
out of football, and that population is 47 running backs and 46 linebackers
against 14 quarterbacks, 10 centres and 6 kickers. Doctrine-first left Charlotte
with no quarterback and Indianapolis with no centre. A weak team is a shape; a
team with no quarterback is broken. The cost is stated: Jacksonville's Southern
share falls from 63% to 41%, against a 27% pool baseline, so it stays a lean.
"""
import csv, sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

TEAMS = ['MEM', 'CAR', 'JAX', 'IND']
TEAMID = {'MEM': 'TEN', 'CAR': 'CAR', 'JAX': 'JAX', 'IND': 'IND'}
NAME = {'MEM': 'Memphis Southmen', 'CAR': 'Charlotte Hornets',
        'JAX': 'Jacksonville Sharks', 'IND': 'Indianapolis Racers'}
ROSTER = 46
INJURY_DISCOUNT = 14
SCARCE = [('QB', 2), ('C', 2), ('K', 1), ('P', 1), ('OG', 3), ('DE', 3), ('TE', 2)]
STARS = ['Too Tall Jones', 'Fran Tarkenton', 'Otis Sistrunk', 'Jim Otis']
# the nine the pool could not resolve, whom no doctrine claims. Placed on fit and
# labelled as such, rather than left to fall wherever the fill order put them.
UNCLAIMED = {'Mo Spencer': 'JAX', 'Ken Payne': 'JAX', 'David Lee': 'JAX',
             'Willie Hall': 'MEM', 'Jim Bailey': 'MEM', 'Sidney Brown': 'IND',
             'John Woodcock': 'IND', 'Bo Rather': 'CAR', 'Reggie Haynes': 'CAR'}
SOUTH = {'Alabama', 'Auburn', 'Tennessee', 'Georgia', 'Florida', 'Florida State',
         'Clemson', 'LSU', 'Mississippi', 'Southern Mississippi', 'Grambling',
         'Jackson State', 'Southern', 'Prairie View A&M', 'North Carolina',
         'North Carolina Central', 'Duke', 'Wake Forest', 'Tulane', 'Tennessee State',
         'Bethune-Cookman', 'Florida A&M', 'Louisiana Tech', 'Arkansas', 'Baylor',
         'Texas', 'Houston', 'Memphis State', 'Georgia Tech', 'Kentucky',
         'South Carolina', 'Vanderbilt', 'Alcorn State', 'Miami (FL)'}

def povr(x):
    """0 means NO MADDEN RECORD, not a rating of zero. 47 of the 308 have none —
    22 men aged 22-25 with no NFL career yet, and 21 aged 33-39 who retired before
    the source's coverage. Sorting 'cheapest first' on this swept ALL of them to
    Jacksonville: 30 of its 46, including Jackie Smith, Mick Tingelhoff, Emmitt
    Thomas, Chris Hanburger, Willie Brown and Jake Scott. The cheap team got the
    Hall of Fame. Use rated_key() for any ordering, never povr() directly."""
    v = x.get('povr', '')
    return int(v) if str(v).isdigit() else 0

def unrated(x):
    return not str(x.get('povr', '')).isdigit()

def rated_key(x, cheap=False):
    """Order on rating, with the unrated held out of the comparison entirely."""
    return (1 if unrated(x) else 0, povr(x) if cheap else -povr(x))

def age(x):
    return int(x['age']) if str(x.get('age', '')).isdigit() else 99

def load_pool():
    top = list(csv.DictReader(open(repo('wip', 'expansion_pool_1979_top40.csv'))))
    rest = list(csv.DictReader(open(repo('wip', 'expansion_pool_1979_rest.csv'))))
    for x in rest:
        x['reason'] = ''; x['where'] = ''; x['team78'] = x.get('team', '')
    pool = top + rest
    spine = {r['name'] for r in csv.DictReader(open(repo('wip', 'ratings_1979.csv')))}
    clash = sorted({x['name'] for x in pool} & spine)
    assert not clash, f'these men are on a real 1979 roster: {clash}'
    return top, pool

def allocate(top, pool):
    taken, R = {}, collections.defaultdict(list)
    def take(x, t, why):
        if x['name'] in taken:
            return False
        taken[x['name']] = (t, why); R[t].append((x, why)); return True

    for pos, each in SCARCE:                       # step 0, before any doctrine
        cands = sorted([x for x in pool if x['pos'] == pos], key=rated_key)
        i = 0
        for _ in range(each):
            for t in TEAMS:
                while i < len(cands) and cands[i]['name'] in taken:
                    i += 1
                if i < len(cands):
                    take(cands[i], t, f'reserved: the pool holds few {pos}s'); i += 1
    for x in top:
        if x['reason'] in ('INJURY', 'GAP YEAR'):
            take(x, 'IND', 'the injury bet — his own team still wanted him')
    for x in top:
        if x['name'] not in STARS and any(k in x['reason'] for k in ('RELEASED', 'CAREER ENDED', 'LEFT THE GAME')):
            take(x, 'CAR', 'let go, not hurt')
    for nm in STARS:
        for x in top:
            if x['name'] == nm:
                take(x, 'MEM', 'bought outright')
    for x in top:
        if x.get('team78') == 'miami-dolphins':
            take(x, 'MEM', 'ex-Dolphin, as in 1974')
    for x in top:
        if x['name'] in UNCLAIMED:
            take(x, UNCLAIMED[x['name']], 'no doctrine claims him; placed on fit')
    # the 47 with no Madden record, split by the doctrines rather than by an
    # artefact of sorting. The old ones were let go or retired — Charlotte's
    # profile. The young ones have no career yet — cheap and unproven, which is
    # Jacksonville's. Tarkenton is already a Memphis purchase.
    # Doctrine first, then a cap. Old and unrated is Charlotte's profile and young
    # and unrated is Jacksonville's, but taking all of each left those two rosters
    # HALF unsourced — 23 and 21 of 46, every one needing a hand rating. So each
    # team takes at most 12, and the overflow goes to the franchise whose doctrine
    # fits second: recognisable finished names to Memphis, young men to
    # Indianapolis, who can wait for them.
    UNRATED_CAP = 12
    # Overflow order matters. Sending old men to Memphis second pushed its median
    # age from 24 to 27 and cost it the one thing its doctrine asks for — young and
    # cheap, because the expensive slots are spent. Memphis takes old men LAST.
    order = {'old': ['CAR', 'IND', 'JAX', 'MEM'], 'young': ['JAX', 'MEM', 'IND', 'CAR']}
    held = collections.Counter()
    for x in sorted([z for z in pool if unrated(z) and z['name'] not in taken],
                    key=lambda z: (age(z) < 30, age(z))):
        band = 'old' if age(x) >= 30 else 'young'
        for t in order[band]:
            if held[t] < UNRATED_CAP:
                why = ('no Madden record; a name that had finished'
                       if band == 'old' else 'no Madden record; young and unproven, which is cheap')
                take(x, t, why); held[t] += 1; break

    left = lambda: [z for z in pool if z['name'] not in taken]
    def fill(t, key, why, cap=ROSTER):
        for x in sorted(left(), key=key):
            if len(R[t]) >= cap:
                break
            take(x, t, why)
    # Southern-first up to 40, not 30. At 30 the unrated allocation had already
    # filled a dozen of Jacksonville's slots and the lean collapsed to 22%, BELOW
    # the pool's own 27% baseline — the doctrine inverted itself.
    fill('JAX', lambda z: (z['college'] not in SOUTH,) + rated_key(z, cheap=True), 'cheap, and Southern', cap=40)
    fill('MEM', lambda z: (age(z) > 24,) + rated_key(z), 'young and cheap; the slots are spent')
    fill('IND', lambda z: (age(z) > 26,) + rated_key(z), 'young, and they can wait')
    fill('JAX', lambda z: rated_key(z, cheap=True), 'cheap, wherever from')
    fill('CAR', lambda z: rated_key(z), 'worth another look')
    for t in TEAMS:
        fill(t, lambda z: rated_key(z), 'roster filler')
    return R, left()

def selftest():
    ok = 0
    top, pool = load_pool()
    try:
        R, _ = allocate(top, pool)
        need = {'QB': 2, 'C': 1, 'K': 1, 'P': 1}
        bad = [(t, p) for t in TEAMS for p, k in need.items()
               if sum(1 for x, _ in R[t] if x['pos'] == p) < k]
        assert not bad, f'a franchise is missing a position it cannot play without: {bad}'
        ok += 1; print('  ok: every franchise has a quarterback, a centre, a kicker and a punter')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        R, _ = allocate(top, pool)
        inj = [x for x, _ in R['IND'] if x.get('reason') == 'INJURY']
        assert len(inj) >= 4, 'Indianapolis is the injury bet and must hold the injured'
        elsewhere = [x['name'] for t in ('MEM', 'CAR', 'JAX') for x, _ in R[t] if x.get('reason') == 'INJURY']
        assert not elsewhere, f'an injured man went somewhere other than Indianapolis: {elsewhere}'
        ok += 1; print('  ok: every injured man is Indianapolis and only Indianapolis')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        R, _ = allocate(top, pool)
        n = {t: sum(1 for x, _ in R[t] if unrated(x)) for t in TEAMS}
        assert max(n.values()) <= 13, f'a roster is more than a quarter unsourced: {n}'
        old = {t: [age(x) for x, _ in R[t] if unrated(x)] for t in TEAMS}
        assert st.median(old['CAR']) > st.median(old['JAX']), 'the age split by doctrine did not hold'
        jx = [x for x, _ in R['JAX']]
        share = sum(1 for x in jx if x['college'] in SOUTH) / len(jx)
        base = sum(1 for x in pool if x['college'] in SOUTH) / len(pool)
        assert share > base * 1.3, f'Jacksonville does not lean Southern: {share:.0%} against a {base:.0%} pool'
        ages = {t: st.median([age(x) for x, _ in R[t] if age(x) < 99]) for t in TEAMS}
        assert ages['MEM'] <= min(ages['CAR'], ages['IND']), f'Memphis is meant to be young: {ages}'
        ok += 1; print(f'  ok: the 47 unrated are spread by doctrine, none over a quarter of a roster ({n})')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok

def main():
    top, pool = load_pool()
    R, spare = allocate(top, pool)
    w = csv.writer(open(repo('wip', 'franchises_1979.csv'), 'w', newline=''))
    w.writerow(['franchise', 'teamID', 'name', 'pos', 'age', 'povr', 'rating_note',
                'college', 'team78', 'reason', 'why_here'])
    for t in TEAMS:
        for x, why in sorted(R[t], key=lambda z: -povr(z[0])):
            note = f'injury: rating {INJURY_DISCOUNT} below potential' if x.get('reason') == 'INJURY' else ''
            w.writerow([NAME[t], TEAMID[t], x['name'], x['pos'], x['age'], x['povr'],
                        note, x['college'], x.get('team78', ''), x.get('reason', ''), why])
    for x in spare:
        w.writerow(['(free agent pool)', 'Free Agent', x['name'], x['pos'], x['age'],
                    x['povr'], '', x['college'], x.get('team78', ''), x.get('reason', ''), ''])
    print(f'wrote wip/franchises_1979.csv: {sum(len(R[t]) for t in TEAMS)} on four rosters, '
          f'{len(spare)} to the free agent pool\n')
    print(f"{'':<22}{'n':>4}{'best':>6}{'med':>5}{'age':>5}{'South':>7}{'from the 40':>13}")
    for t in TEAMS:
        v = [x for x, _ in R[t]]
        p = sorted((povr(x) for x in v if povr(x)), reverse=True)
        a = [age(x) for x in v if age(x) < 99]
        s = sum(1 for x in v if x['college'] in SOUTH)
        print(f'{NAME[t]:<22}{len(v):>4}{p[0]:>6}{st.median(p):>5.0f}{st.median(a):>5.0f}'
              f'{s:>7}{sum(1 for x in v if x.get("where")):>13}')
    for t in TEAMS:
        v = sorted([x for x, _ in R[t]], key=lambda z: -povr(z))[:5]
        print(f'\n  {NAME[t]}: ' + ', '.join(f'{x["name"]} ({x["pos"]} {x["povr"]})' for x in v))

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 3 else 1)
    main()
