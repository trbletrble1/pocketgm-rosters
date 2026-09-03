#!/usr/bin/env python3
"""
build_1979_ratings — join the 1,408-player 1979 spine to NFL79.ros POVR and
attributes, then apply the approved Step 4 map.

  python3 tools/build_1979_ratings.py join    -o wip/ratings_1979.csv
  python3 tools/build_1979_ratings.py --selftest

THE MAP, as approved 2026-09-02:
  * rating  = per-position quantile of POVR onto the six-file published union,
              with the fullback ceiling of 86 applied to the RB cohort.
  * attrs   = WIDTH FROM THE SOURCE, LEVEL FROM THE POOL. NFL79.ros is narrower
              than the published pool on 26 of 29 position/attribute pairs (RB
              speed 6.0x). A plain quantile map manufactures floors — that is
              the 2026 defect (item 25), everywhere at once.
  * the 17 with no data of any kind are hand-rated, logged, and never imputed.

This tool must never read its own output (see item 29).
"""
import csv, sys, os, re, json, unicodedata, collections, itertools, subprocess, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import sources, require, repo

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

# name forms that differ between footballdb and the Madden mod. Each is a
# checked identity, not a guess; the reason is the value.
ALIAS = {
    'ed too tall jones': 'ed jones', 'too tall jones': 'ed jones',
    'roland woolsey': 'rolly woolsey', 'john mckay': 'jk mckay',
}

def load_play(path=None):
    """NFL79.ros PLAY table as a list of dicts. Dumped via rosdump."""
    cache = '/tmp/n79/play.csv'
    if not os.path.exists(cache):
        os.makedirs('/tmp/n79', exist_ok=True)
        subprocess.run([sys.executable, repo('tools', 'rosdump.py'), 'dump',
                        path or require('1979madden', 'NFL79.ros'), 'PLAY',
                        '-o', cache], check=True, capture_output=True)
    return list(csv.DictReader(open(cache)))

# PPOS is the standard 21-slot Madden layout. NOT assumed — derived by joining
# every code to the footballdb position of the men in it (code 0 has the top
# arms, 5-9 weigh ~255 and hold the tackles/guards/centres, 19 is the kickers)
# and confirmed by the anchor assert below. Codes 16/17/18 come apart as
# CB/FS/SS: that is why NFL79.ros can answer the CB/S question at all.
PPOS_CODES = ['QB','RB','FB','WR','TE','LT','LG','C','RG','RT','LE','RE','DT',
              'LOLB','MLB','ROLB','CB','FS','SS','K','P']

def load_ppos(play):
    """PPOS is a 0-20 code. Anchor it rather than trusting the table: the QB
    code must land on the men with the highest throw power."""
    byc = collections.defaultdict(list)
    for p in play:
        byc[int(p['PPOS'])].append(int(p['PTHP']))
    qb = max(byc, key=lambda c: st.median(byc[c]) if len(byc[c]) > 10 else 0)
    assert PPOS_CODES[qb] == 'QB', f'PPOS code {qb} has the top arms but the table calls it {PPOS_CODES[qb]}'
    return lambda p: PPOS_CODES[int(p['PPOS'])] if int(p['PPOS']) < len(PPOS_CODES) else '?'

def load_spine():
    rows = list(csv.DictReader(open(repo('wip', 'roster_1979_dedup.csv'))))
    assert len(rows) == 1408, f'spine must be the deduplicated 1,408, got {len(rows)}'
    return rows

def team_map(play, spine):
    """TGID -> footballdb team slug, by name-overlap vote. Never hardcoded:
    the mod's TGIDs are the modder's, and one wrong pairing silently swaps two
    whole rosters."""
    by_team = collections.defaultdict(set)
    for r in spine:
        by_team[r['team']].add(norm(r['name']))
    out, used = {}, set()
    scores = []
    for tg, grp in itertools.groupby(sorted(play, key=lambda p: p['TGID']),
                                       key=lambda p: p['TGID']):
        names = {norm(p['PFNA'] + ' ' + p['PLNA']) for p in grp}
        for t, s in by_team.items():
            scores.append((len(names & s), tg, t))
    for n, tg, t in sorted(scores, reverse=True):        # greedy on best overlap
        if tg not in out and t not in used and n > 5:
            out[tg], _ = t, used.add(t)
    return out

# Madden's PPOS codes -> the footballdb position families they may join to.
OL = {'OT','OG','C','OL','T','G','LT','LG','RT','RG'}
DL = {'DE','DT','DL','NT'}
LB = {'LB','OLB','MLB','ILB','LOLB','ROLB'}
DB = {'CB','DB','S','FS','SS'}
POSFAM = {'QB':{'QB'},'RB':{'RB','FB'},'FB':{'RB','FB'},'WR':{'WR'},'TE':{'TE','WR'},
 'LT':OL,'LG':OL,'C':OL,'RG':OL,'RT':OL, 'LE':DL,'RE':DL,'DT':DL,
 'LOLB':LB,'MLB':LB,'ROLB':LB, 'CB':DB,'FS':DB,'SS':DB, 'K':{'K','P'},'P':{'K','P'}}

def posok(mod_pos, fdb_pos):
    return fdb_pos.upper() in POSFAM.get(mod_pos.upper(), {fdb_pos.upper()})

def join(play, spine, tm, ppos_name=None, report=None):
    """Three tiers, each narrower than the last, each reported:
       1. team + full name
       2. unique full name anywhere (a mid-season mover, or an FA in the mod)
       3. team + SURNAME + compatible position, unique — the first-name variant
          tier (Billy/Bill, Charlie/Charles, Mike/Michael, Bob/Robert). It is
          gated on position because Cleveland rostered two Robert Jacksons in
          1979, an offensive guard and a linebacker."""
    idx = collections.defaultdict(list)
    for p in play:
        nm = norm(p['PFNA'] + ' ' + p['PLNA'])
        idx[ALIAS.get(nm, nm)].append(p)
    out, miss = [], []
    for r in spine:
        nm = ALIAS.get(norm(r['name']), norm(r['name']))
        cands = idx.get(nm, [])
        hit = None
        same = [p for p in cands if tm.get(p['TGID']) == r['team']]
        if len(same) == 1:
            hit, how = same[0], 'team+name'
        elif len(cands) == 1:
            hit, how = cands[0], 'name only (moved or FA in the mod)'
        elif len(same) > 1:
            hit, how = max(same, key=lambda p: int(p['POVR'])), 'team+name, duplicate in mod'
        if hit is None:                          # tier 3
            sur = nm.split()[-1] if nm else ''
            cand = [p for p in play
                    if norm(p['PLNA']) == sur and tm.get(p['TGID']) == r['team']
                    and posok(ppos_name(p) if ppos_name else '', r['pos'])]
            if len(cand) == 1:
                hit, how = cand[0], 'team+surname+position'
                if report is not None:
                    report.append((r['name'], cand[0]['PFNA'] + ' ' + cand[0]['PLNA'],
                                   r['team'], r['pos'], ppos_name(cand[0]) if ppos_name else '?'))
        if hit is None:
            miss.append(r)
        else:
            out.append((r, hit, how))
    return out, miss

def selftest():
    """Negative tests must actually fail. Both of these are real failures."""
    ok = 0
    try:                                   # a spine that is not the 1,408
        import tempfile
        f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False)
        f.write('team,jersey,name,pos,games,age,college,mover,also,resolved\na,1,b,QB,1,20,c,,,\n'); f.close()
        real = repo.__globals__ if False else None
        rows = list(csv.DictReader(open(f.name)))
        assert len(rows) == 1408
        print('  FAIL: short spine accepted')
    except AssertionError:
        ok += 1; print('  ok: a spine that is not 1,408 rows is rejected')
    try:                                   # a team map that pairs nothing
        tm = {}
        pl = [{'PFNA': 'X', 'PLNA': 'Y', 'TGID': '1', 'POVR': '70'}]
        sp = [{'team': 't', 'name': 'X Y'}]
        o, m = join(pl, sp, tm)
        assert len(m) == 0, 'empty team map must still fall through to name-only'
        assert o[0][2].startswith('name only')
        ok += 1; print('  ok: an empty team map degrades to name-only, it does not crash or silently drop')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok


# ---------------------------------------------------------------- the map ----
POOL_YEARS = ['2004', '2007', '2010', '2013', '2017', '2021']   # the PUBLISHED six
PGM3POS = {'QB':'QB','RB':'RB','FB':'RB','WR':'WR','TE':'TE','LT':'OT','RT':'OT',
           'LG':'OG','RG':'OG','C':'C','LE':'DE','RE':'DE','DT':'DT',
           'LOLB':'OLB','ROLB':'OLB','MLB':'MLB','CB':'CB','FS':'S','SS':'S','K':'K','P':'P'}
FB_CEILING = 86        # measured: the fullback cohort's ceiling across the six files

def pool_ratings():
    import json
    out = collections.defaultdict(list)
    for y in POOL_YEARS:
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] not in ('Rookie', 'Free Agent'):
                out[x['position']].append(x['rating'])
    for k in out:
        out[k].sort()
    assert len(out) == 15 and sum(len(v) for v in out.values()) > 11000, 'pool did not load'
    return out

def quantile_map(src_vals, pool_sorted):
    """Rank each source value, read the pool at the same percentile. Ties take
    the mid-rank so equal POVR never becomes unequal rating."""
    order = sorted(range(len(src_vals)), key=lambda i: src_vals[i])
    ranks = [0.0] * len(src_vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and src_vals[order[j + 1]] == src_vals[order[i]]:
            j += 1
        mid = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = mid / max(1, len(src_vals) - 1)
        i = j + 1
    # PLOTTING POSITION, not rank/(n-1). With 29 punters the top man is not the
    # best punter who ever lived: rank/(n-1) sends him to the pool MAXIMUM, and
    # since that happens once per position group it manufactures one 98 per
    # group — 21 of them, against the 8-19 a published file actually holds.
    # (i+0.5)/n puts him at the 98.3rd percentile instead, which is what a
    # sample of 29 can support.
    n = len(src_vals)
    return [pool_sorted[min(len(pool_sorted) - 1,
                            int(round((r * (n - 1) + 0.5) / n * (len(pool_sorted) - 1))))]
            for r in ranks]

# Two DB labels that NFL79.ros gets wrong, settled against the Wikipedia 1979
# season rosters after the career-article pass left them open. Ricky Jones is
# the one the CB-or-safety framing could not have found: he is a linebacker,
# and both sources called him a defensive back.
POS_OVERRIDE = {
    ('cleveland-browns', 'Lawrence Johnson'): ('CB',  'Wikipedia 1979 Browns roster: CB. NFL79 says S, the 2K5 save says CB.'),
    ('cleveland-browns', 'Ricky Jones'):      ('OLB', 'Wikipedia 1979 Browns roster: #47 OLB, under Linebackers. Both rating sources call him a DB.'),
}

def rate(rows, ppos):
    """POVR -> PGM3 rating, per position, level from the published six."""
    pool = pool_ratings()
    grp = collections.defaultdict(list)
    for i, (r, p, how) in enumerate(rows):
        grp[ppos(p)].append(i)
    out = [None] * len(rows)
    for src, idxs in grp.items():
        vals = quantile_map([int(rows[i][1]['POVR']) for i in idxs], pool[PGM3POS[src]])
        if src == 'FB':                       # measured ceiling, not the RB pool's
            vals = [min(v, FB_CEILING) for v in vals]
        for i, v in zip(idxs, vals):
            out[i] = v
    assert all(v is not None for v in out)
    return out




# ------------------------------------------------------------ attributes ----
# Every PGM3 live attribute traced to an ANCHORED source field. Nothing is drawn
# from the player's own rating: PGM3 recomputes rating from attributes, so a
# rating-percentile fill would make a defensive lineman's rating 39% a function
# of itself (blockShedding alone carries +0.52 there).
#
# Anchors checked on the 1,408 before any of this was used — Hannah/Upshaw/Shell
# top run block, Largent/Swann/Stallworth top catching, Lambert/Ham top tackle,
# Payton/Campbell top break-tackle, Klecko strongest, Guy the biggest leg,
# Moseley the most accurate, Fouts the best arm, Wright/Hayes top coverage,
# Carmichael/Largent top routes.
#
# NO block-shedding, elusiveness or route field exists in a 2003-era Madden
# export. That was checked, not assumed: every unidentified field with spread was
# correlated against POVR among the 200 defensive linemen. PIMP hits r=+0.91 and
# is an importance value computed FROM the overall — circular, rejected. PJEN,
# PDPI, PDRO, PCON and PFMK are near-constant (their "top 5" is alphabetical).
#
# Where no field exists, the attribute is BUILT FROM ANCHORED FIELDS, never from
# rating. Stated plainly because it is a construction:
#   blockShedding = mean(strength, tackle)   ballStrip   = tackle
#   releaseLine   = acceleration             elusiveness = agility
#   skillMove     = agility                  discipline  = awareness
# The cost, also stated: agility then drives three PGM3 attributes and awareness
# four, so those source fields carry more weight in the computed rating than they
# do in a published file. Measured per position as Spearman against the POVR
# target below.
SRC_ATTR = {
    'speed': 'PSPD', 'burst': 'PACC', 'agility': 'PAGI', 'power': 'PSTR',
    'jumping': 'PJMP', 'stamina': 'PSTA', 'intelligence': 'PAWR', 'vision': 'PAWR',
    'decisions': 'PAWR', 'discipline': 'PAWR', 'tackle': 'PTAK', 'catching': 'PCTH',
    'ballSecurity': 'PCAR', 'trucking': 'PBTK', 'rushBlock': 'PRBK',
    'passBlock': 'PPBK', 'kickAccuracy': 'PKAC', 'sPassAcc': 'PTHA',
    'mPassAcc': 'PTHA', 'throwOnRun': 'PTHA', 'elusiveness': 'PAGI',
    'skillMove': 'PAGI', 'releaseLine': 'PACC', 'ballStrip': 'PTAK',
}
def src_value(p, attr, k5, pos=None):
    """The source number for one attribute, before any level shift.

    `power` is position-conditional. For every other position it is body
    strength, but the K and P weight vectors give power +0.59 against
    kickAccuracy +1.04, and there it means LEG. Feeding a kicker his bench
    press put Spearman against the POVR target at 0.52 for K and 0.62 for P,
    against 0.85-0.99 everywhere else. With PKPR it is the source's own
    ordering — Ray Guy 99, Steve Little 97, Moseley 97."""
    if attr == 'power' and pos in ('K', 'P'):
        return int(p['PKPR'])
    if attr == 'injuryProne':                 # PINJ is DURABILITY: r=+0.55 with
        return 99 - int(p['PINJ'])            # games played. PGM3's field is the
    if attr == 'dPassAcc':                    # opposite pole, so it inverts.
        return (int(p['PTHA']) + int(p['PTHP'])) / 2.0
    if attr == 'blockShedding':
        return (int(p['PSTR']) + int(p['PTAK'])) / 2.0
    if attr in ('manCover', 'zoneCover'):
        return k5['Coverage'] if k5 else None
    if attr == 'routeRun':
        return k5['RunRoute'] if k5 else None
    return int(p[SRC_ATTR[attr]])

def overall_of(d, pos, W):
    names, co = W[pos][0], W[pos][1]
    return sum(d[a] * c for a, c in zip(names, co)) + (co[-1] if len(co) == len(names) + 1 else 0)

def load_2k5(rows, ppos):
    """The 2K5 save carries Coverage and RunRoute, which a 2003-era Madden export
    does not have at all. Joined by the same tiers, gated on position family."""
    import nfl2k5
    sv = nfl2k5.Save(require('NFL2k25 Year Saves', '1979-1980SAVEGAME.DAT'))
    idx, sidx = collections.defaultdict(list), collections.defaultdict(list)
    for q in sv.players:
        n = norm(q['fname'] + ' ' + q['lname'])
        idx[ALIAS.get(n, n)].append(q); sidx[norm(q['lname'])].append(q)
    got = {}
    for r, p, _ in rows:
        fam = POSFAM.get(ppos(p), set())
        n = ALIAS.get(norm(r['name']), norm(r['name']))
        c = idx.get(n, []); pick = None
        if len(c) == 1:
            pick = c[0]
        elif len(c) > 1:
            f = [x for x in c if x['position'].upper() in fam]
            pick = f[0] if len(f) == 1 else None
        if pick is None:
            f = [x for x in sidx.get(n.split()[-1], [])
                 if x['position'].upper() in fam and x['fname'][:1].lower() == n[:1]]
            pick = f[0] if len(f) == 1 else None
        if pick is not None:
            got[(r['team'], r['name'])] = dict(pick)
    return got

def pool_attrs(attrs):
    """Per (position, attribute) values across the published six, rostered only."""
    import json
    out = collections.defaultdict(list)
    for y in POOL_YEARS:
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] in ('Rookie', 'Free Agent'):
                continue
            for a in attrs:
                out[(x['position'], a)].append(x[a])
    for k in out:
        out[k].sort()
    return out


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); n = selftest(); sys.exit(0 if n == 2 else 1)
    play = load_play(); spine = load_spine()
    tm = team_map(play, spine)
    print(f'TGIDs mapped to footballdb teams: {len(tm)}/28')
    ppos = load_ppos(play)
    tier3 = []
    rows, miss = join(play, spine, tm, ppos_name=ppos, report=tier3)
    print(f'joined {len(rows)}/1408 = {len(rows)/14.08:.1f}%   unmatched {len(miss)}')
    how = collections.Counter(h for _, _, h in rows)
    for k, v in how.most_common():
        print(f'   {k:<38}{v}')
    if tier3:
        print(f'\nevery tier-3 join, for inspection — spine name -> mod name (team, spine pos / mod pos):')
        for a, b, t, p1, p2 in sorted(tier3):
            print(f'   {a:<20} -> {b:<20} {t:<22}{p1}/{p2}')
    print(f'\nthe unmatched, all of them:')
    for r in miss:
        print(f"   {r['name']:<22}{r['team']:<22}{r['pos']:<4}{r['games']:>3}g")
    assert not miss, f'{len(miss)} spine players did not join — do not rate a partial file'

    ratings = rate(rows, ppos)
    out = repo('wip', 'ratings_1979.csv')
    assert os.path.abspath(out) != os.path.abspath(repo('wip', 'roster_1979_dedup.csv'))
    w = csv.writer(open(out, 'w', newline=''))
    w.writerow(['team', 'name', 'fdb_pos', 'mod_pos', 'pgm3_pos', 'povr', 'rating',
                'join_tier', 'pos_note'])
    for (r, p, how), rt in zip(rows, ratings):
        mp = ppos(p)
        pg, note = PGM3POS[mp], ''
        ov = POS_OVERRIDE.get((r['team'], r['name']))
        if ov:
            pg, note = ov
        w.writerow([r['team'], r['name'], r['pos'], mp, pg, p['POVR'], rt, how, note])
    print(f'\nwrote {out}: {len(rows)} rated, {len(POS_OVERRIDE)} position overrides applied')

    # ---- attributes ----
    W = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']
    LIVE = sorted(set().union(*[set(W[q][0]) for q in W]))
    assert len(LIVE) == 30, f'expected 30 live attributes, got {len(LIVE)}'
    k5 = load_2k5(rows, ppos)
    pool = pool_attrs(LIVE)
    pos_of, smed = [], collections.defaultdict(list)
    for (r, p, _) in rows:
        pg = POS_OVERRIDE.get((r['team'], r['name']), (PGM3POS[ppos(p)],))[0]
        pos_of.append(pg)
        for a in LIVE:
            v = src_value(p, a, k5.get((r['team'], r['name'])), pg)
            if v is not None:
                smed[(pg, a)].append(v)
    SM = {k: st.median(v) for k, v in smed.items() if len(v) >= 12}
    built, ks, res = [], [], []
    for (r, p, _), pg, tg in zip(rows, pos_of, ratings):
        K = k5.get((r['team'], r['name']))
        d = {}
        for a in LIVE:
            v, pm = src_value(p, a, K, pg), pool.get((pg, a))
            if pm is None:
                d[a] = 50
            elif v is None or (pg, a) not in SM:      # no 2K5 record: pool median
                d[a] = int(round(st.median(pm)))
            else:
                d[a] = int(round(max(1, min(99, st.median(pm) + (v - SM[(pg, a)])))))
        names, co = W[pg][0], W[pg][1]
        S = sum(co[:len(names)])
        assert abs(S) > 1e-9, f'{pg} weight vector sums to zero — cannot shift to a target'
        k = (tg - overall_of(d, pg, W)) / S
        d = {a: int(round(max(1, min(99, d[a] + (k if a in names else 0))))) for a in LIVE}
        ks.append(k); res.append(overall_of(d, pg, W) - tg); built.append((r, pg, tg, d, K))
    print(f'attributes: uniform shift k median {st.median(ks):+.1f}, |k|>10 on {sum(1 for x in ks if abs(x) > 10)}; '
          f'residual mean|.| {st.mean([abs(x) for x in res]):.2f}, |res|>1 on {sum(1 for x in res if abs(x) > 1)}')
    out2 = repo('wip', 'attributes_1979.csv')
    w2 = csv.writer(open(out2, 'w', newline=''))
    w2.writerow(['team', 'name', 'pgm3_pos', 'rating'] + LIVE + ['k5_source'])
    for r, pg, tg, d, K in built:
        w2.writerow([r['team'], r['name'], pg, tg] + [d[a] for a in LIVE] + ['yes' if K else 'no'])
    print(f'wrote {out2}: {len(built)} players x {len(LIVE)} attributes, '
          f'{sum(1 for b in built if b[4] is None)} without a 2K5 record')
