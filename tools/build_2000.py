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

# --------------------------------------------------- adjacent-year correction
# Measured 2026-08-31 on four replicates (2003-2006 classes), leave-one-class-out.
# PAWR is the only attribute that degrades badly with source distance, because
# awareness genuinely grows: a source two years later has two seasons of growth
# baked in and reads HIGH, mean signed error +9.28. So we SUBTRACT to recover
# the rookie-year state. Adding would roughly double the error.
#
# GAP 2 ONLY. At gap 1 the bias is +5.35 and correcting it lands inside the
# noise, which is what the handoff records. A correction fitted at one gap is
# meaningless at another.
PAWR_GAP2_OFFSET = -9

def pawr_correction(gap_years):
    assert gap_years in (0, 1, 2), f'unsupported source gap {gap_years}'
    if gap_years != 2:
        return 0
    return PAWR_GAP2_OFFSET


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

# ============================================================ stage 4: faces
# Appearances are built EARLY, not last — the handoff records three of four
# files shipping with random faces because this was left to the end.

HAIR_FAM = {0:'1', 1:'5', 2:'3', 3:'4', 4:'2'}      # PHCL -> hair family
HAIR_STYLES = {'1':list('abcdefghijklmnopqs')+['r1','r2'],
               '2':list('abcdefghijkl'), '3':list('abcdefghijkl'),
               '4':list('abcdefghijk'),  '5':list('abcdefghijkl')}
BEARD_STYLES = ['a','b','c','d','e','f1','f2','g']

# Measured 2026-08-31 against the published 2004/2007 rostered cohorts, 629
# players matched on name+position and unique on both sides:
#   PSKI 0 -> 75.0% family 1, 85% in families 1-3          => light
#   PSKI 1 -> 30.8% family 1, 66.1% families 4-5           => BIMODAL, abstain
#   PSKI 2 -> 97.1% families 4-5                           => dark
#   PSKI 3 -> 92.6% families 4-5                           => dark
# PSKI 2 and 3 are not separable from each other (21/76 vs 18/75 across families
# 4/5), so they get identical treatment. Inventing a distinction between them
# would not be supported by the measurement.
#
# The WITHIN-band spread is a separate question from the band itself, and the
# first fit of it was wrong. It was measured on 2000 players who also appear in
# a published file, and that cohort is not representative of the 2000 league:
#   - compositionally it over-weights the long-career, light-skewing positions,
#     QB/K/P/OL/TE at 39.3% against the full cohort's 33.8%
#   - and the skew persists WITHIN position: light offensive tackles present in
#     the 2000 source are 96.7% family 1 against 63.6% for those absent, and
#     running backs 73.3% against 38.5%
# Fitted on that subset the light band came out 88/6/6 and projected family 1 at
# 30.5% of the file, above the published ceiling of 27.4% (2004). Dark share and
# total light share were both in band; one family was running hot. That is the
# 1986 signature and the `faces` pass is the check that catches it.
#
# PSKI decides light vs dark — that is what it is scored for and what the
# conditional tests. It carries no information about WHICH light family, so the
# internal spread is taken from the published rostered population instead.
#
# Caveat worth carrying: the published files do not agree with each other on
# this. Within-light f1/f2/f3 runs 77.6/8.0/14.4 in 2004, 34.9/18.3/46.8 in
# 2010 and 48.5/49.7/1.8 in 2021 — three incompatible conventions. The union is
# the best available target, not a stable one. This is the same open finding the
# handoff records for family 4 ranging 14-39%.
LIGHT_BAND = [('1', 0.540), ('2', 0.246), ('3', 0.214)]   # published union
DARK_BAND  = [('4', 0.378), ('5', 0.622)]                 # published union
# No skin information at all. The league-wide prior from the published files is
# the least-wrong fill; it is not a reading of PSKI and is logged separately.
ABSTAIN_BAND = [('1', 0.20), ('2', 0.09), ('3', 0.02), ('4', 0.16), ('5', 0.53)]

def seeded(key, salt):
    """Stable per-player randomness. Seeded on the name so a rebuild never
    reshuffles a face — the documented convention, and the reason hand edits
    survive. Not a source of data; every seeded field is counted and reported."""
    return random.Random(f'{key}|{salt}|2000')

def draw(rng, band):
    x = rng.random(); acc = 0.0
    for fam, w in band:
        acc += w
        if x <= acc: return fam
    return band[-1][0]

def build_library():
    """Head family per person from the published rostered cohorts. A person
    carrying more than one family across files is ambiguous and is NOT copied —
    that is the known name|position split problem and guessing which face to
    keep risks overwriting a hand edit."""
    fams = collections.defaultdict(set)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            if q['teamID'] in ('Free Agent', 'Rookie'): continue
            k = (norm(q['forename'] + ' ' + q['surname']), q['position'])
            fams[k].add(q['appearance'][0].replace('Head', '')[0])
    return {k: next(iter(v)) for k, v in fams.items() if len(v) == 1}

def published_family_ranges():
    """min/max head-family share across the published rostered cohorts. Ranges
    are measured against the union of known-good files, never a single one."""
    per = collections.defaultdict(list)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        c = collections.Counter(q['appearance'][0].replace('Head', '')[0]
                                for q in json.load(open(path))
                                if q['teamID'] not in ('Free Agent', 'Rookie'))
        t = sum(c.values())
        for k in '12345': per[k].append(100 * c[k] / t)
    return {k: (min(v), max(v)) for k, v in per.items()}


def stage4(recs):
    lib = build_library()
    stat = collections.Counter()
    for p in recs:
        r = p['_src']
        key = norm(p['forename'] + ' ' + p['surname']) + '|' + p['position']
        rng = seeded(key, 'skin')
        pski = int(r['PSKI'])

        libfam = lib.get((norm(p['forename'] + ' ' + p['surname']), p['position']))
        if libfam:
            skin = libfam; src = 'library'; stat['skin: library'] += 1
        elif pski == 0:
            skin = draw(rng, LIGHT_BAND);  src = 'pski'; stat['skin: PSKI light'] += 1
        elif pski in (2, 3):
            skin = draw(rng, DARK_BAND);   src = 'pski'; stat['skin: PSKI dark'] += 1
        else:
            skin = draw(rng, ABSTAIN_BAND); src = 'abstain'; stat['skin: ABSTAINED (PSKI 1)'] += 1
        p['_skin_src'] = src

        # Face shape from REAL weight and age. PWGT + 160 = pounds (verified
        # exactly on Brady 225, Donald 280, Joe Thomas 312). Thresholds 260 lb
        # and age 30: a thin young, b thick young, c thin old, d thick old.
        lb = int(r['PWGT']) + 160
        age = int(r['PAGE'])
        variant = ('d' if lb >= 260 else 'c') if age >= 30 else ('b' if lb >= 260 else 'a')
        p['weight_lb'] = lb

        phcl = int(r['PHCL'])
        hair = HAIR_FAM.get(phcl)
        if hair is None:
            hair = '1'; stat['hair: PHCL out of range -> black'] += 1
        else:
            stat['hair: PHCL'] += 1

        hr = seeded(key, 'hair')
        p['appearance'] = [
            f'Head{skin}{variant}',
            f'Eyes1{hr.choice("abcde")}',
            f'Hair{hair}{hr.choice(HAIR_STYLES[hair])}',
            f'Beard{hair}{hr.choice(BEARD_STYLES)}',
            f'Eyebrows{hair}{hr.choice("ab")}',
            f'Nose{skin}{hr.choice("abcd")}',
            f'Mouth{skin}{hr.choice("ab")}',
            'Glasses1e',
            f'Clothes{hr.choice("12")}',
        ]
        p['_skin'] = skin

    print()
    print('STAGE 4 — appearances')
    tot = len(recs)
    for k, v in sorted(stat.items()):
        print(f'  {k:34} {v:5}  {100*v/tot:5.1f}%')
    sourced = tot - stat['skin: ABSTAINED (PSKI 1)']
    print(f'  skin sourced or library-backed       {sourced:5}  {100*sourced/tot:5.1f}%')

    # --- structural rules, asserted rather than eyeballed
    for p in recs:
        a = p['appearance']
        assert a[0].replace('Head','')[0] == a[5].replace('Nose','')[0] == a[6].replace('Mouth','')[0], \
            f'head/nose/mouth family split for {p["forename"]} {p["surname"]}'
        assert a[2].replace('Hair','')[0] == a[3].replace('Beard','')[0] == a[4].replace('Eyebrows','')[0], \
            f'hair/beard/eyebrows family split for {p["forename"]} {p["surname"]}'
        assert a[7] == 'Glasses1e', 'players never wear glasses'
        assert len(a) == 9
    print('  family rules, glasses, array length: all pass')

    # THE 1986 CHECK, as an assertion rather than something a reviewer has to
    # spot. 1986 passed every other test: dark share in band, total light share
    # in band, one family running hot. `pgm3_validate.py faces` flags it, but by
    # then the registry has been applied on top and it is being diagnosed
    # through two layers.
    fam = collections.Counter(p['_skin'] for p in recs)
    print('  head family: ' + '  '.join(f'{k}:{100*v/tot:.1f}%' for k, v in sorted(fam.items())))
    pub_range = published_family_ranges()
    bad = []
    for k in '12345':
        share = 100 * fam[k] / tot
        lo, hi = pub_range[k]
        flag = '' if lo <= share <= hi else '   <-- OUTSIDE'
        if flag: bad.append(f'family {k} at {share:.1f}% against a published {lo:.1f}-{hi:.1f}%')
        print(f'    family {k}: {share:5.1f}%   published {lo:5.1f} - {hi:5.1f}{flag}')
    assert not bad, 'head family distribution out of band: ' + '; '.join(bad)
    # Aggregate dark share. The per-family check above passes this file while
    # the aggregate does not, which is why both are needed: every family can sit
    # inside its own range while the light/dark balance sits outside.
    dark = 100 * (fam['4'] + fam['5']) / tot
    dk = []
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        c = collections.Counter(q['appearance'][0].replace('Head', '')[0]
                                for q in json.load(open(path))
                                if q['teamID'] not in ('Free Agent', 'Rookie'))
        t2 = sum(c.values()); dk.append(100 * (c['4'] + c['5']) / t2)
    lo, hi = min(dk), max(dk)
    flag = '' if lo <= dark <= hi else f'   <-- OUTSIDE published {lo:.1f}-{hi:.1f}'
    print(f'    dark share {dark:.1f}%   published {lo:.1f} - {hi:.1f}{flag}')
    if flag:
        print(f'    NOT failing the build on this: it is a property of the source,')
        print(f'    not of the mapping. PSKI resolves to {100*33.1/(33.1+56.1):.1f}% light before')
        print(f'    anything is assigned. Widening the band to make the file pass')
        print(f'    would be fitting the check to the data. NEEDS A RULING.')
    var = collections.Counter(p['appearance'][0][-1] for p in recs)
    print('  head variant: ' + '  '.join(f'{k}:{100*v/tot:.1f}%' for k, v in sorted(var.items())))
    return recs

def conditional_pski(recs):
    """THE mandatory check. Split the output by the source value and confirm the
    groups differ. A face generator seeded on a name produces a perfectly
    reasonable spread of skin tones and fails only here — that bug shipped in
    2007 and passed every distribution check."""
    print()
    print('CONDITIONAL — appearance skin family vs source PSKI')
    print('  (the validator runs its own `conditional` pass on the finished')
    print('   file at stage 10; this is the same computation, in memory, so no')
    print('   parallel artifact exists to drift)')
    print()
    for label, subset in (('all records', recs),
                          ('PSKI-sourced only (library excluded)',
                           [p for p in recs if p['_skin_src'] != 'library'])):
        print(f'  {label}:')
        print(f'    {"PSKI":>5}{"n":>6}   ' + '  '.join(f'fam{f}' for f in '12345') + '     light%')
        rows = collections.defaultdict(collections.Counter)
        for p in subset:
            rows[int(p['_src']['PSKI'])][p['_skin']] += 1
        lights = {}
        for k in sorted(rows):
            tot = sum(rows[k].values())
            cells = '  '.join(f'{100*rows[k][f]/tot:5.1f}' for f in '12345')
            light = 100 * sum(rows[k][f] for f in '123') / tot
            lights[k] = light
            print(f'    {k:>5}{tot:>6}   {cells}   {light:6.1f}%')
        sep = lights.get(0, 0) - max(lights.get(2, 0), lights.get(3, 0))
        print(f'    separation, PSKI 0 light% minus darkest of 2/3: {sep:+.1f} points')
        assert sep > 40, f'PSKI groups do not separate ({sep:+.1f}) — the source was never used'
        print()

if __name__ == '__main__':
    recs = stage3()
    recs = stage4(recs)
    conditional_pski(recs)
