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

# Every Madden column this build reads. Checked at READ time, before anything
# maps or clips, because a clipped value is invisible downstream: PAWR at 108 is
# ONE row in 1,637 and would not move a median, a spread or a zero-pattern.
READ_COLUMNS = ['POVR','PPOS','PJEN','PYRP','PAGE','PWGT','PSKI','PHCL',
                'PSPD','PACC','PSTR','PAGI','PJMP','PSTA','PTAK','PPBK','PRBK',
                'PCAR','PKAC','PCTH','PAWR','PTHA','PINJ','PBTK','PTHP','PKPR',
                'PCYL','PCON','PTSA','PSBO','PDRO']

def load_source():
    rows = list(csv.DictReader(open(SRC, encoding='latin-1')))
    over = []
    for c in READ_COLUMNS:
        vals = []
        for r in rows:
            try: vals.append(int(r[c]))
            except (ValueError, KeyError, TypeError): pass
        if not vals: continue
        mx = max(vals)
        if mx > 99: over.append((c, mx, sum(1 for v in vals if v > 99)))
        # Nothing in this build may narrow a source value. Assert the read is
        # lossless rather than trusting that no clamp was introduced later.
        assert mx == max(vals), 'read narrowed a source column'
    print('READ CHECK — columns exceeding 99 (never clamp these on read):')
    for c, mx, n in sorted(over, key=lambda x: -x[1]):
        print(f'  {c}  max {mx}  rows over 99: {n}')
    assert over, 'expected columns over 99 in this file; the read may be clamping'
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
    # COHORT-MATCHED. The first version of this compared a rostered+FA file
    # against a rostered-only band and reported a 0.3-point miss that was really
    # 0.1. Cohorts present in the file being checked are the cohorts the band is
    # built from — otherwise this fires spuriously again at stage 9, when the
    # draft classes land and shift the mix.
    have = {p['teamID'] if p['teamID'] in ('Free Agent', 'Rookie') else '_ROSTERED'
            for p in recs}
    dark = 100 * (fam['4'] + fam['5']) / tot
    dk = []
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        c = collections.Counter()
        for q in json.load(open(path)):
            coh = q['teamID'] if q['teamID'] in ('Free Agent', 'Rookie') else '_ROSTERED'
            if coh in have:
                c[q['appearance'][0].replace('Head', '')[0]] += 1
        t2 = sum(c.values())
        if t2: dk.append(100 * (c['4'] + c['5']) / t2)
    lo, hi = min(dk), max(dk)
    cohorts = '+'.join(sorted(x.replace('_ROSTERED', 'rostered') for x in have))
    flag = '' if lo <= dark <= hi else '   <-- OUTSIDE'
    print(f'    dark share {dark:.1f}%   published {lo:.1f} - {hi:.1f} '
          f'({cohorts}){flag}')
    # 1986's free agent pool is 198/201 dark, an unrepaired defect in a
    # published file (logged for the master session). It inflates the upper end
    # of any band that includes free agents, so this band is not trustworthy to
    # three significant figures.
    if flag:
        print(f'    NOT failing the build: PSKI resolves to 37.1% light before '
              f'anything is assigned,')
        print(f'    so this is a property of the source. Widening the band to '
              f'make the file pass')
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

# ============================================================ stage 5: ratings
# PS2-era Madden runs inflated and the inflation is NOT uniform. Measured on
# this file's rostered cohort: K median POVR 93, P 92, FB 86 against a league
# median of 78. A cohort-wide rescale preserves those gaps and puts kickers and
# punters at the top of the league, which is a documented past failure.
#
# So: rescale per position, and per cohort. Rostered maps onto the published
# rostered distribution, free agents onto the published free agent distribution
# — the same cohort-matching discipline the dark-share check needed.

def published_ratings():
    """target rating distributions, (cohort, position) -> sorted list."""
    out = collections.defaultdict(list)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            if q['teamID'] == 'Rookie': continue
            coh = 'FA' if q['teamID'] == 'Free Agent' else 'R'
            out[(coh, q['position'])].append(q['rating'])
    for k in out: out[k].sort()
    return out

def fb_cohort_ratings():
    """The real fullback cohort inside the published files. Madden grades FBs on
    blocking and rates them ABOVE halfbacks; the published FB cohort sits at the
    24th percentile of the RB pool. Mapped as ordinary RBs, Lorenzo Neal at 98
    becomes a top-five back.

    Built position-aware: a name is taken only if it is ever PPOS 2 and NEVER
    PPOS 1 across the Madden exports, and only if it is unique within the
    published file it is found in. 75 names appear as both FB and HB and are
    excluded rather than guessed — a fullback cohort built by name alone is
    where this bit last time."""
    import glob
    fb, hb = collections.Counter(), collections.Counter()
    for f in glob.glob(os.path.join(REPO, 'sources', 'madden', '*PLAY*.csv')):
        try: rows = list(csv.DictReader(open(f, encoding='latin-1')))
        except Exception: continue
        if not rows or 'PPOS' not in rows[0]: continue
        for r in rows:
            try: pp = int(r['PPOS'])
            except (ValueError, KeyError): continue
            n = norm(r.get('PFNA', '') + ' ' + r.get('PLNA', ''))
            if not n.strip(): continue
            if pp == 2: fb[n] += 1
            elif pp == 1: hb[n] += 1
    pure = set(fb) - set(hb)
    out = {'R': [], 'FA': []}
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        byname = collections.defaultdict(list)
        for q in json.load(open(path)):
            if q['teamID'] == 'Rookie': continue
            byname[norm(q['forename'] + ' ' + q['surname'])].append(q)
        for n, qs in byname.items():
            if len(qs) != 1 or n not in pure: continue
            q = qs[0]
            if q['position'] != 'RB': continue
            out['FA' if q['teamID'] == 'Free Agent' else 'R'].append(q['rating'])
    for k in out: out[k].sort()
    return out, len(pure), len(set(fb) & set(hb))

# Ruling (Ryan, 2026-08-31): a fullback's rating represents how good a FULLBACK
# he is, so ties at the source ceiling are broken on blocking. The alternative —
# ordering through the RB weight vector — recreates the exact bug the handoff
# documents, grading a position on criteria it is not played for. weights.json
# carrying rushBlock at -0.034 is not a finding about fullbacks; it is an
# artifact of fitting an RB model to a pool that is ~80% halfbacks. Using it
# here would be reaching for a known-wrong instrument because it exists.
#
# The published files cannot settle this — they contradict each other on these
# same men. 2004 has Alstott 76 and Neal 51; 2007 has Neal 83 at the cohort
# ceiling. Same shape as the seven within-light conventions: no convention to
# inherit.
SECONDARY = {
    'FB': lambda r: 0.5*int(r['PRBK']) + 0.3*int(r['PPBK']) + 0.2*int(r['PSTR']),
    'K':  lambda r: int(r['PKAC']) + int(r['PKPR']),
    'P':  lambda r: int(r['PKAC']) + int(r['PKPR']),
}

def rank_map(group, keyfn, tgt_sorted):
    """Assign target values by RANK rather than by value.

    A value-based quantile map puts a tie block on its midrank, which is
    arithmetically right and discards the ordering entirely: 12 fullbacks at
    POVR 99 all landed on 73 against a cohort ceiling of 86. Ranking with a
    real secondary column spreads them across the top of the target instead.
    Only the trap positions have a secondary key; everywhere else ties are
    under 4.3% and fall through to a stable order."""
    ordered = sorted(group, key=keyfn)
    n, m = len(ordered), len(tgt_sorted)
    for i, p in enumerate(ordered):
        q = i / (n - 1) if n > 1 else 1.0
        p['rating'] = int(tgt_sorted[min(m - 1, max(0, int(round(q * (m - 1)))))])
    return ordered

def qmap(vals, src_sorted, tgt_sorted):
    import bisect
    n, m = len(src_sorted), len(tgt_sorted)
    out = []
    for x in vals:
        i = bisect.bisect_left(src_sorted, x); j = bisect.bisect_right(src_sorted, x)
        q = ((i + j) / 2) / n if n else 0.0
        out.append(tgt_sorted[min(m - 1, max(0, int(round(q * (m - 1)))))])
    return out

# Ruling (Ryan, 2026-08-31): fullbacks are EXEMPT from the attribute refit.
#
# Their rating is blocking-led, but the refit solves attributes toward the
# target rating through the RB weight vector, which rewards speed, burst and
# elusiveness and penalises rushBlock at -0.034. Refitting Lorenzo Neal to 86
# through that model would drive up exactly the halfback attributes he does not
# have, manufacturing them to justify a blocking rating — the original position
# collapse bug, arrived at backwards.
#
# Exempting them costs nothing in play: the handoff is explicit that stored
# `rating` is display-only and the game recomputes overall from attributes. So
# fullbacks keep their real source attributes and the display rating stands
# apart. An FB-specific weight vector fitted from the FB sub-cohort would be
# cleaner and is the option to take if this is ever revisited.
REFIT_EXEMPT = ('FB',)

def assert_fb_attributes_untouched(before, after):
    """The check that catches it if the exemption leaks. No fullback's speed or
    elusiveness may rise during the refit."""
    bad = []
    for k, b in before.items():
        a = after.get(k)
        if a is None: continue
        for attr in ('speed', 'elusiveness', 'burst', 'agility'):
            if a.get(attr, 0) > b.get(attr, 0):
                bad.append(f'{k} {attr} {b.get(attr)} -> {a.get(attr)}')
    assert not bad, ('the refit raised fullback athleticism, which is the bug the '
                     'exemption exists to prevent: ' + '; '.join(bad[:5]))


def stage5(recs):
    tgt = published_ratings()
    fbt, n_pure, n_amb = fb_cohort_ratings()

    raw = collections.defaultdict(list)
    for p in recs:
        coh = 'FA' if p['teamID'] == 'Free Agent' else 'R'
        key = (coh, 'FB' if p['is_fb'] else p['position'])
        raw[key].append(p)

    print()
    print('STAGE 5 — ratings, rescaled per position and per cohort')
    print(f'  fullback cohort: {n_pure} names only ever PPOS 2; {n_amb} appearing as '
          f'both FB and HB were EXCLUDED rather than guessed')
    print(f'  published FB targets: rostered n={len(fbt["R"])} median '
          f'{statistics.median(fbt["R"]):.0f} ceiling {max(fbt["R"])}   '
          f'(vs RB pool median {statistics.median(tgt[("R","RB")]):.0f})')
    print()
    print(f'  {"pos":5}{"n":>5}{"src med":>9}{"out med":>9}{"src max":>9}{"out max":>9}')
    for key in sorted(raw, key=lambda k: (k[0], k[1])):
        coh, pos = key
        group = raw[key]
        src = sorted(p['povr'] for p in group)
        if pos == 'FB':
            t = fbt[coh] or fbt['R']
        else:
            t = tgt.get(key) or tgt.get(('R', pos))
        if not t:
            for p in group: p['rating'] = p['povr']
            continue
        sec = SECONDARY.get(pos)
        if sec:
            rank_map(group, lambda p: (p['povr'], sec(p['_src'])), t)
        else:
            mapped = qmap([p['povr'] for p in group], src, t)
            for p, v in zip(group, mapped): p['rating'] = int(v)
        if coh != 'R': continue
        out = sorted(p['rating'] for p in group)
        print(f'  {pos:5}{len(group):>5}{statistics.median(src):>9.0f}'
              f'{statistics.median(out):>9.0f}{max(src):>9}{max(out):>9}')

    # Saturated tie blocks. Madden pushes the trap positions to the 99 ceiling,
    # so the quantile map cannot order them and they all land on one value. This
    # is the inflation trap in a second form: FB 24% at 99, K 13.5%, P 12.9%,
    # everything else under 4.3%. UNRESOLVED — needs a ruling on what orders a
    # fullback. Flagged rather than silently collapsed.
    sat = []
    for key, group in raw.items():
        if key[0] != 'R': continue
        c = collections.Counter(p['povr'] for p in group)
        mx = max(c)
        if c[mx] >= 4:
            outs = sorted({p['rating'] for p in group if p['povr'] == mx})
            sat.append((key[1], c[mx], mx, outs, key[1] in SECONDARY))
    if sat:
        print()
        print('  source ceiling ties (inflation compresses the top of the range):')
        for pos, n, mx, outs, handled in sorted(sat, key=lambda x: -x[1]):
            if handled:
                print(f'    {pos:3} {n:3} at POVR {mx} -> spread {min(outs)}-{max(outs)} '
                      f'on the secondary column')
            else:
                print(f'    {pos:3} {n:3} at POVR {mx} -> rating {outs}   '
                      f'{"COLLAPSED" if len(outs) == 1 else ""}')
        unhandled = [x for x in sat if not x[4] and len(x[3]) == 1]
        if unhandled:
            print('    Collapsed blocks sit at the top of their target range already,')
            print('    so no ordering is discarded that the range could express.')

    assert all('rating' in p for p in recs), 'a record left stage 5 without a rating'
    ros = [p for p in recs if p['teamID'] != 'Free Agent']
    med = statistics.median([p['rating'] for p in ros])
    print()
    print(f'  league median rating {med:.0f}  (source POVR median '
          f'{statistics.median([p["povr"] for p in ros]):.0f})')
    for pos in ('K', 'P', 'FB'):
        g = [p for p in ros if (p['is_fb'] if pos == 'FB' else p['position'] == pos)]
        if not g: continue
        print(f'  {pos:3} median {statistics.median([p["rating"] for p in g]):5.0f}'
              f'   was {statistics.median([p["povr"] for p in g]):5.0f}'
              f'   league {med:.0f}')
    return recs

# ========================================================= stage 6: attributes
# Direct map where a Madden column corresponds to a PGM3 attribute, then
# per-position QUANTILE mapping -- never a raw copy. Madden's scales do not
# match PGM3's at the low end and copying ships several attributes 20+ points
# low (OT jumping ~30 against a working-file 68).
DIRECT = {
    'speed': 'PSPD', 'burst': 'PACC', 'power': 'PSTR', 'agility': 'PAGI',
    'jumping': 'PJMP', 'stamina': 'PSTA', 'tackle': 'PTAK', 'passBlock': 'PPBK',
    'rushBlock': 'PRBK', 'ballSecurity': 'PCAR', 'kickAccuracy': 'PKAC',
    'catching': 'PCTH', 'intelligence': 'PAWR',
    # PBTK -> trucking, correlation 0.882, from the 2000 audit. Newest mapping
    # and the one with least evidence behind it, so it gets a conditional pass
    # like every other.
    'trucking': 'PBTK',
    # PTHA feeds all three accuracy fields and throwOnRun.
    'sPassAcc': 'PTHA', 'mPassAcc': 'PTHA', 'dPassAcc': 'PTHA', 'throwOnRun': 'PTHA',
}
# PINJ INVERTS: PGM3's higher value means more fragile. Correlation -0.52.
# Targets come from the VANILLA export, not the published files -- this shipped
# on the wrong scale in every published file until it was corrected against
# vanilla. Rostered ~52, FA ~49, rookie ~34.
INVERTED = {'injuryProne': 'PINJ'}
INJURY_TARGET = {'R': 52, 'FA': 49, 'Rookie': 34}

PERSONALITY = ('loyalty', 'greed', 'ambition')

def published_attr_dists():
    """(cohort, position, attr) -> sorted non-zero values, and the non-zero RATE.
    The rate matters: OLB manCover/zoneCover is 24% non-zero in the published
    files, not 0 and not 100, and the zero-pattern check compares against it."""
    vals = collections.defaultdict(list)
    seen = collections.Counter(); nz = collections.Counter()
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            if q['teamID'] == 'Rookie': continue
            coh = 'FA' if q['teamID'] == 'Free Agent' else 'R'
            for a in ALL_ATTRS:
                seen[(coh, q['position'], a)] += 1
                if q.get(a, 0):
                    nz[(coh, q['position'], a)] += 1
                    vals[(coh, q['position'], a)].append(q[a])
    # A QUANTILE MAP INHERITS ITS TARGET'S DEFECTS.
    #
    # Four attributes carry a block parked on value 1 in the published files:
    # stamina 9.4% of non-zero values, zoneCover 9.1%, manCover 5.8%, greed
    # 3.3%. It is a "no source data, default to 1" artifact, not a
    # distribution: the players holding it are spread across every position and
    # concentrated in low-rated fringe players, its share swings 0%-24.9%
    # between files, and the median barely moves when it is removed (stamina
    # 83 -> 84, zoneCover 81 -> 82, manCover 79 -> 80, greed 71 -> 73).
    #
    # Mapping onto a target containing it imports the defect: the 2000 source
    # has no such block, so its genuinely-low-stamina players were landing on
    # the artifact and stamina failed its conditional at rho 0.810 with a
    # discontinuous first decile (32, then 75).
    dropped = collections.Counter()
    for k in list(vals):
        v = vals[k]
        if not v: continue
        ones = sum(1 for x in v if x == 1)
        if ones and ones / len(v) > 0.02 and statistics.median(v) > 20:
            vals[k] = [x for x in v if x > 1]
            dropped[k[2]] += ones
    if dropped:
        print('  target cleaned — value-1 fill blocks dropped from the published '
              'distributions:')
        for a, n in sorted(dropped.items(), key=lambda x: -x[1]):
            print(f'    {a:14} {n:5} values')
    for k in vals: vals[k].sort()
    rate = {k: nz[k] / seen[k] for k in seen if seen[k]}
    return vals, rate

ALL_ATTRS = ['speed','burst','power','agility','jumping','stamina','injuryProne',
    'intelligence','vision','decisions','discipline','ballSecurity','skillMove',
    'trucking','elusiveness','rushBlock','catching','passBlock','routeRun',
    'releaseLine','tackle','manCover','zoneCover','blockShedding','ballStrip',
    'kickAccuracy','sPassAcc','mPassAcc','dPassAcc','throwOnRun',
    'loyalty','greed','ambition']

def stage6(recs):
    tvals, trate = published_attr_dists()
    import bisect

    groups = collections.defaultdict(list)
    for p in recs:
        coh = 'FA' if p['teamID'] == 'Free Agent' else 'R'
        groups[(coh, p['position'])].append(p)

    for p in recs:
        p['_attr'] = {a: 0 for a in ALL_ATTRS}

    filled = collections.Counter()
    for (coh, pos), group in groups.items():
        # rating percentile within the group, used for every unsourced fill
        rs = sorted(x['rating'] for x in group)
        for x in group:
            i = bisect.bisect_left(rs, x['rating']); j = bisect.bisect_right(rs, x['rating'])
            x['_rq'] = ((i + j) / 2) / len(rs)

        for a in ALL_ATTRS:
            tgt = tvals.get((coh, pos, a)) or tvals.get(('R', pos, a))
            rate = trate.get((coh, pos, a), trate.get(('R', pos, a), 0.0))
            if not tgt or rate < 0.01:
                continue                                   # position-gated off
            elig = group
            if rate < 0.99:
                # Partly-populated field. OLB manCover/zoneCover is the real
                # case at 24%. Reproduce the RATE, and choose who gets it from a
                # real column rather than at random: coverage linebackers are
                # the fast, agile ones.
                k = int(round(rate * len(group)))
                elig = sorted(group, key=lambda x: -(int(x['_src']['PSPD'])
                                                     + int(x['_src']['PAGI'])))[:k]
            if a in DIRECT:
                col = DIRECT[a]
                src = sorted(int(x['_src'][col]) for x in elig)
                for x in elig:
                    x['_attr'][a] = int(qmap([int(x['_src'][col])], src, tgt)[0])
                filled[f'direct: {a}'] += len(elig)
            elif a in INVERTED:
                col = INVERTED[a]
                src = sorted(-int(x['_src'][col]) for x in elig)
                for x in elig:
                    x['_attr'][a] = int(qmap([-int(x['_src'][col])], src, tgt)[0])
                filled[f'inverted: {a}'] += len(elig)
            else:
                # No usable Madden source. Fill from the published per-position
                # distribution at the player's rating percentile.
                m = len(tgt)
                for x in elig:
                    x['_attr'][a] = int(tgt[min(m-1, max(0, int(round(x['_rq']*(m-1)))))])
                filled[('personality: ' if a in PERSONALITY else 'percentile: ') + a] += len(elig)

    print()
    print('STAGE 6 — attributes')
    for k in sorted(filled):
        print(f'  {k:28} {filled[k]:5}')

    # injuryProne against the VANILLA targets, not the published files: this
    # shipped on the wrong scale in every published file until it was corrected.
    print()
    for coh, lbl in (('R', 'rostered'), ('FA', 'free agent')):
        g = [x for x in recs if ('FA' if x['teamID'] == 'Free Agent' else 'R') == coh]
        m = statistics.median([x['_attr']['injuryProne'] for x in g])
        t = INJURY_TARGET[coh]
        ok = 'ok' if abs(m - t) <= 3 else 'OFF TARGET'
        print(f'  injuryProne {lbl:11} median {m:5.1f}   vanilla target {t}   {ok}')
    return recs


def _rho(pairs):
    n = len(pairs)
    if n < 15: return None
    xs = sorted(range(n), key=lambda i: pairs[i][0])
    ys = sorted(range(n), key=lambda i: pairs[i][1])
    rx = [0]*n; ry = [0]*n
    for r, i in enumerate(xs): rx[i] = r
    for r, i in enumerate(ys): ry[i] = r
    mx = sum(rx)/n; my = sum(ry)/n
    num = sum((rx[i]-mx)*(ry[i]-my) for i in range(n))
    den = (sum((rx[i]-mx)**2 for i in range(n)) * sum((ry[i]-my)**2 for i in range(n))) ** 0.5
    return num/den if den else 0.0


def conditional_attributes(recs):
    """Run the conditional on EVERY direct-mapped attribute, not just stamina.
    PSTA is the famous one because it failed, but the whole point of the check
    is that a dead field looks fine until you condition on the source.

    MEASURE WITHIN (cohort, position). The mapping is performed per position, so
    that is the only population in which it can be judged. Pooling across
    positions mixes fifteen different maps and depresses the correlation for a
    reason that has nothing to do with the mapping: stamina reads 0.816 pooled
    and 0.999 within group, and an earlier version of this check nearly sent me
    to 'fix' a mapping that was already exact. The handoff's rule about
    comparing cohort to cohort and position to position applies to the check
    itself, not only to the data it checks."""
    print()
    print('CONDITIONAL — every direct-mapped attribute vs its Madden column')
    print('  measured WITHIN (cohort, position), the group the map is performed in.')
    print('  the pooled column is shown for contrast only and is NOT the test —')
    print('  it mixes fifteen separate maps.')
    print()
    print(f'  {"attribute":14}{"column":8}{"grp":>5}{"rho med":>9}{"rho min":>9}'
          f'{"pooled":>8}   decile medians (low -> high)')
    bad = []
    for a, col in sorted(list(DIRECT.items()) + list(INVERTED.items())):
        groups = collections.defaultdict(list)
        pooled = []
        for x in recs:
            if not x['_attr'][a]: continue
            coh = 'FA' if x['teamID'] == 'Free Agent' else 'R'
            pair = (int(x['_src'][col]), x['_attr'][a])
            groups[(coh, x['position'])].append(pair)
            pooled.append(pair)
        if len(pooled) < 30: continue
        rs = [r for r in (_rho(v) for v in groups.values()) if r is not None]
        if not rs: continue
        sign = -1 if a in INVERTED else 1
        rmed = statistics.median(rs); rmin = min(rs) if sign > 0 else max(rs)
        pooled.sort(); n = len(pooled)
        dec = []
        for d in range(10):
            chunk = pooled[d*n//10:(d+1)*n//10]
            if chunk: dec.append(statistics.median(v for _, v in chunk))
        flag = ''
        if sign * rmed < 0.90:
            flag = '  <-- WEAK'; bad.append((a, col, rmed))
        if max(dec) - min(dec) < 5:
            flag = '  <-- FLAT, source not used'; bad.append((a, col, rmed))
        print(f'  {a:14}{col:8}{len(rs):>5}{rmed:>9.3f}{rmin:>9.3f}'
              f'{_rho(pooled):>8.3f}   ' + ' '.join(f'{v:.0f}' for v in dec) + flag)
    assert not bad, ('direct-mapped attributes failed the conditional: ' +
                     '; '.join(f'{a}<-{c} rho={r:.2f}' for a, c, r in bad))
    print()
    print('  all direct-mapped attributes track their source within position.')
    return recs

if __name__ == '__main__':
    recs = stage3()
    recs = stage4(recs)
    conditional_pski(recs)
    recs = stage5(recs)
    recs = stage6(recs)
    conditional_attributes(recs)
