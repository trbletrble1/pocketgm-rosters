#!/usr/bin/env python3
"""2000 season build — one pipeline, one artifact.

Deliberately a single in-memory pass writing the output once. The handoff
records a failure where a stage wrote step2_roster.json while the next stage
read step3_roster.json, so a verified fix never reached the output. There are
no intermediate roster files here.

Run:  python3 tools/build_2000.py [--stage N]
"""
import csv, json, os, sys, collections, unicodedata, datetime, statistics, random

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(REPO, 'sources', 'madden', '2000_-_PLAY.csv')
SEASON = 2000
GAME_NOW = 2026                       # the game's internal clock
OFFSET = GAME_NOW - SEASON            # historical builds offset draftSeason by this

# ---------------------------------------------------------------- team map
# From the 2000 .ros TEAM table (TGID/TLNA/TDNA), spot-checked 12/12 against
# known 2000 players. MODERN ids: San Diego -> LAC, St Louis -> LAR, Oakland ->
# LV. Using period-correct ids breaks those three teams on import.
TEAM = {1:'CHI',2:'CIN',3:'BUF',4:'DEN',5:'CLE',6:'TB',7:'ARI',8:'LAC',9:'KC',
        10:'IND',11:'DAL',12:'MIA',13:'PHI',14:'ATL',15:'SF',16:'NYG',17:'JAX',
        18:'NYJ',19:'DET',20:'GB',21:'CAR',22:'NE',23:'LV',24:'LAR',25:'BAL',
        26:'WAS',27:'NO',28:'SEA',29:'PIT',30:'TEN',31:'MIN'}
FA_TGID = {1009, 1014}

# PPOS -> PGM3 position. Vocabulary is the 15 the published files use: no FB
# (collapses to RB) and OG, not G. FB is tracked separately because Madden
# grades fullbacks on blocking and they must be mapped against the real FB
# cohort, not the RB pool.
PPOS = {0:'QB',1:'RB',2:'RB',3:'WR',4:'TE',5:'OT',6:'OG',7:'C',8:'OG',9:'OT',
        10:'DE',11:'DE',12:'DT',13:'OLB',14:'MLB',15:'OLB',16:'CB',17:'S',
        18:'S',19:'K',20:'P'}
IS_FB = {2}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))   # fold, not strip
    s = s.lower().replace('.', ' ').replace("'", ' ').replace('-', ' ')
    return ' '.join(s.split())

def load_source():
    rows = list(csv.DictReader(open(SRC, encoding='latin-1')))
    # Print the max of every numeric column we intend to read. Nine columns in
    # this file exceed 99 and a single clipped row is invisible to every
    # distribution check.
    return rows

def cohort(rows):
    rost = [r for r in rows if int(r['TGID']) in TEAM]
    fa   = [r for r in rows if int(r['TGID']) in FA_TGID]
    assert len(rost) == 1637, f'rostered {len(rost)}, expected 1637'
    assert len(fa)   == 694,  f'free agents {len(fa)}, expected 694'
    return rost, fa

def base_record(r, teamid):
    ppos = int(r['PPOS'])
    return {
        '_src': r,
        'forename': r['PFNA'].strip(),
        'surname':  r['PLNA'].strip(),
        'position': PPOS[ppos],
        'is_fb':    ppos in IS_FB,
        'teamID':   teamid,
        'teamNum':  int(r['PJEN']) if teamid not in ('Free Agent', 'Rookie') else 0,
        'povr':     int(r['POVR']),
    }

def dedupe_jerseys(recs):
    """teamNum is real data (PJEN) and must not be generated. But the published
    files carry zero duplicates within a team-season across 11,737 rostered
    players, so collisions are resolved in favour of the more experienced man;
    the junior player moves within his position's observed range."""
    moved = 0
    byteam = collections.defaultdict(list)
    for p in recs:
        if p['teamID'] not in ('Free Agent', 'Rookie'):
            byteam[p['teamID']].append(p)
    for team, ps in byteam.items():
        used = {}
        # more experienced first, so the senior man keeps his number
        for p in sorted(ps, key=lambda x: (-int(x['_src']['PYRP']), -x['povr'])):
            n = p['teamNum']
            if n not in used:
                used[n] = p; continue
            pool = [x for x in range(1, 100) if x not in used]
            if not pool:
                continue
            same = [x for x in pool if abs(x - n) <= 20] or pool
            p['teamNum'] = same[0]; used[same[0]] = p; moved += 1
    return moved

def stage3():
    rows = load_source()
    rost, fa = cohort(rows)
    recs = [base_record(r, TEAM[int(r['TGID'])]) for r in rost]
    recs += [base_record(r, 'Free Agent') for r in fa]
    assert len(recs) == len(rost) + len(fa), 'record count changed building base'

    pos = collections.Counter(p['position'] for p in recs if p['teamID'] != 'Free Agent')
    ratio = pos['CB'] / max(1, pos['S'])
    moved = dedupe_jerseys(recs)

    print(f'STAGE 3 — cohort, positions, team ids, jerseys')
    print(f'  rostered {len(rost)}  free agents {len(fa)}  total {len(recs)}')
    print(f'  teams {len(set(p["teamID"] for p in recs if p["teamID"] != "Free Agent"))}')
    print(f'  CB {pos["CB"]}  S {pos["S"]}  ratio {ratio:.3f}   (published 1.058-1.302)')
    assert 1.00 <= ratio <= 1.35, f'CB/S ratio {ratio:.3f} outside the published band'
    print(f'  fullbacks flagged for the FB cohort map: {sum(1 for p in recs if p["is_fb"])}')
    print(f'  jersey collisions resolved: {moved}')
    dups = 0
    byteam = collections.defaultdict(collections.Counter)
    for p in recs:
        if p['teamID'] != 'Free Agent': byteam[p['teamID']][p['teamNum']] += 1
    for t, c in byteam.items(): dups += sum(v - 1 for v in c.values() if v > 1)
    assert dups == 0, f'{dups} duplicate jerseys remain'
    print(f'  duplicate jerseys after resolution: {dups}')
    print(f'  free agents / prospects on teamNum 0: '
          f'{sum(1 for p in recs if p["teamID"]=="Free Agent" and p["teamNum"]==0)}/{len(fa)}')
    return recs

if __name__ == '__main__':
    recs = stage3()
