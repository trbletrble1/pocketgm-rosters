#!/usr/bin/env python3
"""2000 season build — one pipeline, one artifact.

Deliberately a single in-memory pass writing the output once. The handoff
records a failure where a stage wrote step2_roster.json while the next stage
read step3_roster.json, so a verified fix never reached the output. There are
no intermediate roster files here.

Run:  python3 tools/build_2000.py [--stage N]
"""
import csv, json, os, sys, collections, unicodedata, datetime, statistics, random, math

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


def norm_registry(s):
    """The registry's key form. MEASURED against 11,069 `faces` keys and 2,231
    `staff_faces` keys, not taken from the stated description.

    The registry's stated rule is "lowercase, strip punctuation and
    Jr/Sr/II/III/IV/V, collapse initials". Strip is right for periods and
    apostrophes and WRONG for hyphens, which the registry turns into a space:

        A.J. Brown            -> aj brown            (period GLUED)
        Scott O'Brien         -> scott obrien        (apostrophe GLUED)
        Kabeer Gbaja-Biamila  -> kabeer gbaja biamila (hyphen SPACED)

    Getting that wrong in either direction costs about a thousand roster
    records. Spacing everything (the general norm() below) missed the 758
    period cases; gluing everything missed the 212 hyphen cases.

    Suffix tokens are stripped ANYWHERE, not only trailing — measured: making
    it trailing-only dropped the hit rate from 97.7% to 96.9%, because the
    registry itself drops a middle "V." the same way.

    Hit rate on punctuated names across the seven published rosters: 97.7%.
    The residual 23 are genuinely absent from the registry, not mis-keyed —
    every sampled one has no near-match under any spelling.
    """
    SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
    t = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace('-', ' ').replace('/', ' ')          # hyphen and slash -> SPACE
    t = ''.join(c for c in t if c.isalnum() or c.isspace())   # period/apostrophe -> GLUE
    return ' '.join(w for w in t.split() if w not in SUF)


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

def drop_unshippable(recs):
    """Three source records cannot ship. Each is dropped on evidence, logged by
    name, and never replaced with an invention."""
    dropped = []
    # (a) no forename in the source, and no offensive lineman named Bailey on
    #     ANY 2000 roster in nflverse. Not a real 2000 player.
    for p in list(recs):
        if not p['forename'].strip() or not p['surname'].strip():
            dropped.append((p, 'no forename in the source; no OL of that surname '
                               'on any 2000 roster'))
            recs.remove(p)
    # (b) the source lists two men twice, once on a team and once in the free
    #     agent pool, same position, same age, same PYRP, different POVR. Keep
    #     the rostered copy per the handoff's dedupe rule.
    ros = {(p['forename'], p['surname'], p['position'])
           for p in recs if p['teamID'] != 'Free Agent'}
    for p in list(recs):
        if p['teamID'] == 'Free Agent' and (p['forename'], p['surname'], p['position']) in ros:
            dropped.append((p, 'duplicated in the source; the rostered copy is kept'))
            recs.remove(p)
    for p, why in dropped:
        print(f'  DROPPED  {p["forename"]!r} {p["surname"]!r} '
              f'({p["position"]}, {p["teamID"]}) — {why}')
    return recs, len(dropped)


def stage3():
    rows = load_source()
    rost, fa = cohort(rows)
    recs = [base_record(r, TEAM[int(r['TGID'])]) for r in rost]
    recs += [base_record(r, 'Free Agent') for r in fa]
    assert len(recs) == len(rost) + len(fa), 'record count changed building base'
    recs, n_dropped = drop_unshippable(recs)
    assert len(recs) == len(rost) + len(fa) - n_dropped, 'drop count mismatch'

    pos = collections.Counter(p['position'] for p in recs if p['teamID'] != 'Free Agent')
    ratio = pos['CB'] / max(1, pos['S'])
    moved = dedupe_jerseys(recs)

    print(f'STAGE 3 — cohort, positions, team ids, jerseys')
    print(f'  rostered {len(rost)}  free agents {len(fa)}  dropped {n_dropped}  '
          f'total {len(recs)}')
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

# ======================================================== stage 2b: Houston
# Ruling (Ryan, 2026-08-31): fill the vacant HOU slot with the Houston Texans
# arriving two years early. Nothing is invented but the start date -- the
# franchise was awarded 29-0 on 6 October 1999 and Charley Casserly was hired as
# GM on 19 January 2000.
#
# The construction rule is a CONSEQUENCE, not a filter: a GM with no scouting
# department signs what he can already evaluate, which is men the Oilers drafted
# and men playing within a day's drive. The lopsided roster follows from that.
# Trim the surplus, never the shortage -- the positions Casserly could evaluate
# are fine and the ones he could not are dire, and that is the point.
HOU_MIN = {'QB':2,'RB':2,'WR':4,'TE':2,'OT':2,'OG':2,'C':1,'DE':3,'DT':3,
           'OLB':3,'MLB':1,'CB':4,'S':2,'K':1,'P':1}
HOU_TARGET = 53
# Steve Young (99) and Dan Marino (91) are in the pool and are LEFT THERE.
# Either would make Houston's quarterback the best or second-best in the league
# in year one and destroy the premise, and neither had any reason to un-retire
# for an expansion team.
HOU_FORBIDDEN = {'Steve Young', 'Dan Marino'}
# Erik Kramer is an explicit exception to the construction rule -- N.C. State,
# never an Oiler. The stated why is the Detroit connection: he is one of the two
# men Detroit played ahead of Andre Ware, and signing both re-runs that
# competition ten years later in Ware's home town.
HOU_EXCEPTION = {'Erik Kramer': 'exception to the construction rule — N.C. State, '
                                'never an Oiler. Signed for the Detroit connection '
                                'with Andre Ware.'}

def stage2b(recs):
    core_path = os.path.join(REPO, 'wip', 'hou_core_2000.json')
    core = json.load(open(core_path))['unique']
    # The selection script and the build use different position vocabularies:
    # the selection kept FB/FS/SS, the build collapses FB->RB and FS/SS->S to
    # match PGM3's 15. Translate or four core players silently fail to match.
    XLATE = {'FS': 'S', 'SS': 'S', 'FB': 'RB', 'G': 'OG'}
    want = {(c['first'], c['last'], XLATE.get(c['mpos'], c['mpos'])) for c in core}
    fa = [p for p in recs if p['teamID'] == 'Free Agent']
    byname = {(p['forename'], p['surname'], p['position']): p for p in fa}

    picked, missing = [], []
    for k in sorted(want):
        p = byname.get(k)
        if p is None: missing.append(k)
        else: picked.append(p)
    print()
    print('STAGE 2b — Houston')
    print(f'  core selected position-aware, birth-date disambiguated: {len(core)}')
    # A core player failing to match is a translation bug, not an absence, and
    # it silently shrinks the premise -- Jason Layman is a 1996 Oilers second
    # round pick, exactly the cohort this roster is built from. Assert on it.
    assert len(missing) <= 3, (f'{len(missing)} core players did not match the pool: '
                               + ', '.join(f'{a} {b} ({c})' for a, b, c in missing))
    if missing:
        print(f'  {len(missing)} core players are no longer in the pool '
              f'(dropped as unshippable in stage 3): '
              + ', '.join(f'{a} {b}' for a, b, _ in missing))

    for nm, why in HOU_EXCEPTION.items():
        f, l = nm.split(' ', 1)
        for p in fa:
            if (p['forename'], p['surname']) == (f, l) and p not in picked:
                picked.append(p); print(f'  + {nm} — {why}')
    for p in picked:
        assert f"{p['forename']} {p['surname']}" not in HOU_FORBIDDEN, \
            f"{p['forename']} {p['surname']} must be left in the pool"

    have = collections.Counter(p['position'] for p in picked)
    # fill shortages with the WORST available, per the spec: the positions
    # Casserly could not evaluate are dire and should be the worst on the roster
    added = []
    for pos, need in sorted(HOU_MIN.items()):
        short = need - have.get(pos, 0)
        if short <= 0: continue
        pool = sorted((p for p in fa if p['position'] == pos and p not in picked),
                      key=lambda x: x['povr'])
        for p in pool[:short]:
            picked.append(p); added.append((pos, p)); have[pos] += 1
    if added:
        print(f'  filled {len(added)} shortage slots from the general pool, '
              f'worst-first: ' + ', '.join(f'{pos}' for pos, _ in
                                           sorted(collections.Counter(a[0] for a in added).items())))

    # trim surplus, best-kept, never below the minimum
    trimmed = 0
    while len(picked) > HOU_TARGET:
        have = collections.Counter(p['position'] for p in picked)
        cands = [p for p in picked
                 if have[p['position']] > HOU_MIN.get(p['position'], 0)
                 and f"{p['forename']} {p['surname']}" not in HOU_EXCEPTION]
        if not cands: break
        worst = min(cands, key=lambda x: x['povr'])
        picked.remove(worst); trimmed += 1
    print(f'  trimmed {trimmed} surplus players, lowest-rated first, '
          f'never below the positional minimum')

    # Jerseys. These men arrive from the free agent pool carrying teamNum 0, so
    # Houston needs numbers assigned. PJEN is real data and is preferred where
    # it is valid and free; the rest come from the era's positional ranges,
    # which the handoff verified on the 1986 file by position medians.
    RANGES = {'QB': range(1, 20), 'K': range(1, 20), 'P': range(1, 20),
              'RB': range(20, 50), 'CB': range(20, 50), 'S': range(20, 50),
              'C': range(50, 80), 'OG': range(50, 80), 'OT': range(50, 80),
              'MLB': range(50, 60), 'OLB': range(50, 60),
              'TE': range(80, 90), 'WR': range(80, 90),
              'DE': range(60, 100), 'DT': range(60, 100)}
    used, kept = set(), 0
    for p in sorted(picked, key=lambda x: -int(x['_src']['PYRP'])):
        n = int(p['_src']['PJEN'])
        if 1 <= n <= 99 and n not in used:
            p['teamNum'] = n; used.add(n); kept += 1
        else:
            p['teamNum'] = 0
    for p in picked:
        if p['teamNum']: continue
        for n in list(RANGES.get(p['position'], range(1, 100))) + list(range(1, 100)):
            if n not in used:
                p['teamNum'] = n; used.add(n); break
    print(f'  jerseys: {kept} kept from PJEN, {len(picked)-kept} assigned '
          f'from the positional ranges')
    assert len({p['teamNum'] for p in picked}) == len(picked), 'duplicate HOU jersey'
    assert all(1 <= p['teamNum'] <= 99 for p in picked), 'HOU jersey out of range'

    for p in picked:
        p['teamID'] = 'HOU'
        p['_hou'] = True
    assert len({id(p) for p in picked}) == len(picked), 'a player was picked twice'
    print(f'  HOU roster: {len(picked)}')
    shape = collections.Counter(p['position'] for p in picked)
    print('  shape: ' + '  '.join(f'{k}{v}' for k, v in sorted(shape.items())))
    for pos, mn in HOU_MIN.items():
        assert shape.get(pos, 0) >= mn, f'HOU is below minimum at {pos}: {shape.get(pos,0)}/{mn}'
    ware = [p for p in picked if (p['forename'], p['surname']) == ('Andre', 'Ware')]
    assert ware, 'Andre Ware is not on the roster — the premise depends on him'
    print(f"  Andre Ware: POVR {ware[0]['povr']}, age corrected to "
          f"{[c for c in core if c['last']=='Ware'][0]['nfl_age']} from the stale Madden "
          f"{[c for c in core if c['last']=='Ware'][0]['madden_age']}")
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
    pure_fill = []
    for k in list(vals):
        v = vals[k]
        if not v: continue
        ones = sum(1 for x in v if x == 1)
        if not ones or ones / len(v) <= 0.02:
            continue
        rest = [x for x in v if x > 1]
        # A "rating" whose entire observed range sits at or below 10 is not a
        # rating. OLB manCover takes ONLY the values 1, 2 and 3 across every
        # published file, against MLB manCover's 38-92 — and it is absent
        # entirely from 2004, 2007 and 2017 while 2013 and 2021 carry it for
        # 100% of their OLBs. Whatever it is, it is not coverage skill, and
        # shipping Derrick Brooks a manCover of 3 would be shipping a number
        # with no meaning.
        if rest and max(v) <= 10:
            rest = []
        if not rest:
            # EVERY non-zero value is 1. The field is not partly filled, it is
            # entirely fill and the position does not use it at all. OLB
            # zoneCover is exactly this: 31.6% "non-zero" in the published
            # rostered cohort, 100% of which is the value 1.
            vals[k] = []
            pure_fill.append(k)
            dropped[k[2]] += ones
        elif statistics.median(rest) > 20:
            vals[k] = rest
            dropped[k[2]] += ones
    if dropped:
        print('  target cleaned — value-1 fill blocks dropped from the published '
              'distributions:')
        for a, n in sorted(dropped.items(), key=lambda x: -x[1]):
            print(f'    {a:14} {n:5} values')
    for k in sorted(pure_fill):
        print(f'    {k[0]}/{k[1]} {k[2]}: ENTIRELY fill, gated off')
    for k in vals: vals[k].sort()
    # THE GATE IS DERIVED FROM THE CLEANED POPULATION.
    #
    # Cleaning the target is not enough: every statistic taken off that
    # population has to be recomputed too, and the gating rate is one. Read off
    # the raw data, OLB manCover looked 32.3% populated; 62.3% of those values
    # are the fill, so the real gate is 12.2%. OLB zoneCover looked 31.6% and is
    # actually 0%. Same defect as the target contamination, one step later in
    # the pipeline.
    # THE GATE AND THE DISTRIBUTION ANSWER DIFFERENT QUESTIONS.
    #
    # The gate asks "does this position use this field at all". The
    # distribution asks "what values does it take". Cleaning fill out of the
    # second must not change the first: stamina is 100% populated and ~9% fill,
    # and computing the rate from the cleaned values dropped it to 0.91, below
    # the partial-field threshold. Stamina was then gated OFF for the bottom 9%
    # of several positions -- 37 players shipped with stamina 0, which the
    # conditional pass caught and no structural check would have.
    #
    # So: the rate is the ORIGINAL non-zero share, EXCEPT where cleaning
    # emptied the field entirely, which is the OLB coverage case and means the
    # position genuinely does not use it.
    rate = {}
    for k in seen:
        if not seen[k]: continue
        rate[k] = 0.0 if (k in vals and not vals[k]) else nz[k] / seen[k]
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

# ========================================================= stage 7: contracts
# THE HEADLINE, stated here and in the build log rather than in a footnote:
# roughly 30 veteran contracts in this file are real and roughly 1,100 are
# DRAWN. The contract block of the 2000 Madden file carries rookie signal and
# nothing else, measured three ways against 62 real Over The Cap figures:
#
#   veterans   PTSA +0.020   PSBO -0.040   PSBO/PCON -0.179
#   rookies    PTSA +0.500   PSBO +0.410   PSBO/PCON +0.393
#
# So veteran salaries are not sourced and are not fitted either -- adjusted R2
# on the anchor set is 0.127, fitted on 30 notable players whose median draft
# pick is 24 against the cohort's 118. Extrapolating that outside its support
# would manufacture per-player numbers with no per-player signal.
TEAM_CAP_2000 = 62_170_000
# 2000 minimum salary ladder by credited season.
MIN_2000 = {0: 193_000, 1: 243_000, 2: 288_000, 3: 333_000,
            4: 385_000, 5: 385_000, 6: 385_000,
            7: 440_000, 8: 440_000, 9: 440_000}
def min_salary(yrs): return MIN_2000.get(yrs, 477_000)

# Rating is a FLOOR, not a fit. It explains 3% of veteran salary, so nothing is
# predicted from it -- but the NFL does not pay a 95-rated veteran the minimum,
# and that much weaker claim the evidence does carry.
RATING_FLOOR = [(92, 2_200_000), (87, 1_200_000), (82, 700_000), (77, 450_000)]
def rating_floor(r):
    for lo, v in RATING_FLOOR:
        if r >= lo: return v
    return 0

# The ceiling is the same weak monotone claim as the floor, in the other
# direction: the NFL does not pay a 66-rated player top-ten money. Without it
# the lognormal tail produced Alex Molden (rating 66) at $7.96M and Russell
# Maryland at $17.76M against an era ceiling of $8.54M. Neither is a fit; both
# are guards on a draw.
RATING_CEIL = [(90, 9_000_000), (85, 6_000_000), (80, 4_500_000),
               (75, 3_000_000), (70, 2_000_000)]
ERA_MAX_SALARY = 9_000_000        # highest real 2000 cap number is $8.54M

# Position ceilings, from the real 2000 top of market. The published files
# cannot supply these: they put K at 1.50x the league median with a p95 of
# $7.68M, the K/P inflation defect showing up in contracts as well as ratings.
# The real 2000 kicker market tops out at Jason Elam, $1,071,167.
POS_CEIL = {'QB': 8_600_000, 'OT': 5_000_000, 'DE': 5_000_000, 'WR': 5_000_000,
            'CB': 4_600_000, 'DT': 4_600_000, 'OLB': 4_600_000, 'MLB': 4_600_000,
            'RB': 4_300_000, 'OG': 4_000_000, 'S': 3_500_000, 'TE': 3_200_000,
            'C': 3_200_000, 'K': 1_200_000, 'P': 1_100_000}
def rating_ceiling(r):
    for lo, v in RATING_CEIL:
        if r >= lo: return v
    return 1_200_000

def load_anchors():
    ns = {}
    path = os.path.join(REPO, 'wip', 'otc_anchors_2000.py')
    if not os.path.exists(path): return {}, {}
    g = {}
    exec(open(path).read(), g)
    return g.get('OTC', {}), g.get('EXCLUDED', {})

# A GUARD MUST KNOW THE PROVENANCE OF WHAT IT IS GUARDING.
#
# Floors, ceilings, clamps and defaults are all written for derived values, and
# every one of them will silently overwrite a sourced value if it cannot tell
# the difference. The rating floor pushed Jason Elam's real $1,071,167 up to
# $2.2M and nothing looked wrong, because $2.2M for a top kicker is not absurd.
# It was visible only because the real number was sitting next to it.
#
# Same family as `_verified_keys` being locked against automated passes. That
# rule protects hand edits; this extends it to any real-data tier.
SOURCED_TAGS = {'OTC'}

def assert_guards_spared_sourced(recs, before):
    bad = [f"{p['forename']} {p['surname']}: {before[id(p)]:,} -> {p['salary'] + p['guarantee']:,}"
           for p in recs
           if p.get('_src_tag') in SOURCED_TAGS
           and abs((p['salary'] + p['guarantee']) - before[id(p)]) > 0.01 * before[id(p)]]
    assert not bad, ('a guard modified a SOURCED record: ' + '; '.join(bad[:5]))


def stage7(recs, draft_pick):
    otc, excluded = load_anchors()
    ros = [p for p in recs if p['teamID'] != 'Free Agent']
    fa = [p for p in recs if p['teamID'] == 'Free Agent']

    # ---- length. PCYL is contract years REMAINING and holds <= PCON on
    # 1637/1637. Use it directly; do not stretch it to hit the published 34-39%
    # band, which is seven files that disagree.
    ladder_used = fixed = 0
    for p in ros:
        cyl = int(p['_src']['PCYL']); con = int(p['_src']['PCON'])
        assert cyl <= con or con == 0, 'PCYL exceeded PCON'
        if con == 0:
            yrs = int(p['_src']['PYRP'])
            if yrs == 0:
                p['length'] = 4; ladder_used += 1        # rookie ladder
            else:
                p['length'] = 1; fixed += 1              # no data, veteran
        else:
            p['length'] = max(1, cyl)
    for p in fa: p['length'] = 0

    # ---- salary
    #
    # The floor applies to SALARY, not to the cap hit. An earlier version put it
    # on the hit and then divided by (1+g) to get salary, which pushed 735
    # players back under the league minimum -- the floor and the split were each
    # correct and the composition was not.
    anchored = drawn_rk = drawn_vet = 0
    for p in recs:
        key = norm(p['forename'] + ' ' + p['surname']) + '|' + p['position']
        rng = seeded(key, 'salary')      # deterministic: a rebuild must not
                                         # reshuffle a player's contract
        yrs = int(p['_src']['PYRP'])
        pick = draft_pick.get(norm(p['forename'] + ' ' + p['surname']), 224)
        name = p['forename'] + ' ' + p['surname']
        # The rating floor may never exceed the position ceiling, or a
        # 95-rated kicker inherits a quarterback's floor. The league minimum
        # always applies regardless.
        p['_floor'] = max(min_salary(yrs),
                          min(rating_floor(p['rating']),
                              POS_CEIL.get(p['position'], ERA_MAX_SALARY)))
        if name in otc and p['teamID'] != 'Free Agent':
            # REAL. An OTC 2000 cap figure is base + prorated bonus, the same
            # quantity as PGM3's salary + guarantee. Assigning it to `salary`
            # and adding a guarantee on top inflates the player by 5-16% --
            # each field individually sane, the pair wrong.
            p['_hit'] = float(otc[name]); p['_src_tag'] = 'OTC'; anchored += 1
        elif yrs <= 3:
            # Rookie tier. Slot-driven, adjusted R2 0.679 on the anchor set.
            p['_raw'] = math.exp(-0.62 * math.log(max(1, pick))) * rng.uniform(0.80, 1.25)
            p['_src_tag'] = 'rookie-slot'; drawn_rk += 1
        else:
            # Veteran tier. DRAWN, not sourced and not fitted. Right-skewed,
            # tilted by the two things carrying what little signal exists:
            # draft slot (rho +0.443) and years pro.
            p['_raw'] = (math.exp(-0.45 * math.log(max(1, pick)) + 0.05 * min(yrs, 12))
                         * rng.lognormvariate(0, 0.55))
            p['_src_tag'] = 'veteran-drawn'; drawn_vet += 1

    # guarantee ratio, matching the published convention: non-zero on 52-70% of
    # rostered players at a median guarantee/salary of 0.055-0.160
    for p in recs:
        r2 = seeded(norm(p['forename'] + ' ' + p['surname']) + '|' + p['position'], 'guar')
        p['_g'] = 0.0 if r2.random() < 0.38 else r2.uniform(0.04, 0.22)

    # ---- scale each team so the aggregate lands on the real cap. Per-player
    # accuracy is unavailable for veterans, so the aggregate is what can be
    # validated and it is what gets calibrated.
    byteam = collections.defaultdict(list)
    for p in ros: byteam[p['teamID']].append(p)
    for t, ps in byteam.items():
        # Teams do not all spend the same share of the cap. Seeded on the team
        # id so a rebuild reproduces it.
        # Real 2000 accounting was top-51 (Rule of 51) and that is the basis
        # reported, but the validator sums every player, so the band is set to
        # keep the stricter all-player total under the cap too.
        TARGET = seeded(t, 'cap').uniform(0.84, 0.95) * TEAM_CAP_2000
        def total(k):
            hits = []
            for x in ps:
                if '_hit' in x:
                    sal = x['_hit'] / (1 + x['_g'])
                else:
                    sal = min(max(k * x['_raw'], x['_floor']),
                              max(x['_floor'], rating_ceiling(x['rating'])),
                              max(x['_floor'], POS_CEIL.get(x['position'], ERA_MAX_SALARY)),
                              ERA_MAX_SALARY)
                hits.append(sal * (1 + x['_g']))
            return sum(sorted(hits, reverse=True)[:51])
        lo, hi = 1.0, 1e9
        for _ in range(60):
            mid = (lo * hi) ** 0.5
            if total(mid) < TARGET: lo = mid
            else: hi = mid
        k = (lo * hi) ** 0.5
        for x in ps:
            if '_hit' in x:
                # REAL, never floored and never clamped. An earlier version
                # applied the rating floor here and pushed Jason Elam's real
                # $1,071,167 up to $2.2M -- a guard meant for drawn values
                # overwriting sourced ones, which is the worst direction for
                # this kind of bug because the output still looks reasonable.
                x['_sal'] = x['_hit'] / (1 + x['_g'])
            else:
                x['_sal'] = min(max(k * x['_raw'], x['_floor']),
                                max(x['_floor'], rating_ceiling(x['rating'])),
                                max(x['_floor'], POS_CEIL.get(x['position'], ERA_MAX_SALARY)),
                                ERA_MAX_SALARY)
    # free agents: no team to scale against, so use the league median scale
    kfa = statistics.median([max(p['_sal'], 1) / max(p['_raw'], 1e-9)
                             for p in ros if '_raw' in p])
    for p in fa:
        p['_sal'] = min(max(kfa * p.get('_raw', 0.0), p['_floor']),
                        max(p['_floor'], rating_ceiling(p['rating'])),
                        max(p['_floor'], POS_CEIL.get(p['position'], ERA_MAX_SALARY)),
                        ERA_MAX_SALARY)

    for p in recs:
        sal = int(round(p['_sal'] / 1000) * 1000)
        if p['teamID'] == 'Free Agent':
            # A free agent has no current contract. 2004 and 2007 ship FA
            # salary and guarantee at 0 with eSalary carrying the asking price;
            # 2021 does the opposite. Two conventions again — this follows the
            # two that agree, and it is the one consistent with length already
            # being 0.
            p['salary'] = 0; p['guarantee'] = 0; p['_ask'] = sal
        else:
            p['salary'] = sal
            p['guarantee'] = int(round(sal * p['_g'] / 1000) * 1000)
            assert p['salary'] > 0, 'a rostered player has zero salary'

    # eSalary / eGuarantee / eLength are game-computed OUTPUTS and are
    # regenerated on import. Ship sane values for first-load validity, no more.
    for p in recs:
        if p['teamID'] == 'Free Agent':
            p['eSalary'] = int(p['_ask'] / 1000) * 1000
            p['eGuarantee'] = 0
            p['eLength'] = 1
        else:
            p['eSalary'] = int(p['salary'] * 1.05 / 1000) * 1000
            p['eGuarantee'] = int(p['guarantee'] * 1.1 / 1000) * 1000
            p['eLength'] = min(4, max(0, p['length'] - 1))

    # every guard is checked against provenance, not trusted to have behaved
    assert_guards_spared_sourced(recs, {id(p): float(otc[p['forename'] + ' ' + p['surname']])
                                        for p in recs
                                        if p.get('_src_tag') in SOURCED_TAGS})

    print()
    print('STAGE 7 — contracts')
    print(f'  anchored to REAL Over The Cap figures     {anchored:5}')
    print(f'  rookie tier, draft-slot derived           {drawn_rk:5}   (adj R2 0.679)')
    print(f'  veteran tier, DRAWN not sourced           {drawn_vet:5}   (adj R2 0.127 — not fitted)')
    print(f'  -> {100*anchored/max(1,anchored+drawn_vet):.1f}% of veteran-era contracts are real, '
          f'{100*drawn_vet/max(1,anchored+drawn_vet):.1f}% are drawn')
    print(f'  rookie ladder used for length             {ladder_used:5}')
    print(f'  length=1 fallback, no contract data       {fixed:5}')
    lens = collections.Counter(p['length'] for p in ros)
    print(f'  length: ' + '  '.join(f'{k}:{100*v/len(ros):.0f}%' for k, v in sorted(lens.items())))
    print(f'    one-year deals {100*lens[1]/len(ros):.1f}%  (PCYL says 31.8%, published 34-39%)')
    assert all(p['length'] >= 1 for p in ros), 'a rostered player has length 0'
    assert all(p['length'] == 0 for p in fa), 'a free agent has a non-zero length'
    assert not any(p['length'] > 7 for p in recs), 'length above 7'
    return recs

# PGM3's salary cap is a fixed engine constant of ~$280M. There is no cap field
# anywhere in the schema -- the game does not know what year it is. Shipping
# era-accurate 2000 dollars (median top-51 $54.6M) leaves ~$225M of room on
# every team and makes the whole financial layer inert: nobody is ever cap
# strapped, every signing is affordable, extensions never bind.
#
# All seven published files land within $1M of each other:
#   1986 196.4   2004 196.0   2007 195.4   2010 195.8
#   2013 195.7   2017 195.4   2021 195.8
# Seven files across seven eras agreeing to 0.5% is a deliberate convention,
# not the defect the handoff used to call it. Era accuracy governs everything
# except the dollar SCALE, because the cap is fixed and unscaled dollars make
# the economy inert.
#
# One uniform factor over salary and guarantee on every record. Uniform is the
# whole point: it preserves every relationship in the file. The 66 OTC-anchored
# contracts keep their true proportions to each other and to everyone else,
# Brady stays at the bottom of the roster, the K/P correction survives, and the
# league-minimum floor scales with everything else.
#
# eSalary / eGuarantee / eLength are game-computed and are NOT touched.
# The basis is the TOP 53, not the top 51. On top-53 the seven published files
# read 197,400,001 / 197,424,500 / 197,426,500 / 197,428,500 / 197,429,000 /
# 197,427,000 / 197,426,500 -- a spread of $29k on $197.4M, 0.015%, with 1986
# landing on the round number to the dollar. That is a fitted target, and the
# handoff has stated it since the 2026-08-29 rebuild: "each era is scaled so
# the median top-53 cap hit is 197.4M against a 280M cap". On top-51 the same
# files scatter by $1M, so top-51 is the derived view and top-53 the real one.
PGM3_ENGINE_PAYROLL = 197_400_000
PAYROLL_TOP_N = 53

def _topN(recs):
    byteam = collections.defaultdict(list)
    for p in recs:
        if p['teamID'] in ('Free Agent', 'Rookie'): continue
        byteam[p['teamID']].append(p['salary'] + p['guarantee'])
    return [sum(sorted(v, reverse=True)[:PAYROLL_TOP_N]) for v in byteam.values()]

def scale_to_engine(recs):
    """One uniform factor -> median top-51 lands on the published convention."""
    tots = _topN(recs)
    med = statistics.median(tots)
    assert med > 0, 'zero median team payroll before scaling'
    f = PGM3_ENGINE_PAYROLL / med
    assert 2.0 < f < 6.0, f'engine scale factor {f:.3f} outside the sane range'

    n_in  = len(recs)
    frozen = [(p['eSalary'], p['eGuarantee'], p['eLength']) for p in recs]
    before = [(p['salary'], p['guarantee']) for p in recs]

    for p in recs:
        p['salary']    = int(round(p['salary']    * f))
        p['guarantee'] = int(round(p['guarantee'] * f))

    assert len(recs) == n_in, 'scaling changed the record count'
    assert [(p['eSalary'], p['eGuarantee'], p['eLength']) for p in recs] == frozen, \
        'scaling touched a game-computed field'
    # uniform means every non-zero record moved by the same factor, to rounding
    worst = 0.0
    for (s0, g0), p in zip(before, recs):
        for v0, v1 in ((s0, p['salary']), (g0, p['guarantee'])):
            if v0 > 0:
                worst = max(worst, abs((v1 / v0) - f) / f)
    assert worst < 1e-4, f'scaling was not uniform: {worst:.2e} relative drift'

    med2 = statistics.median(_topN(recs))
    assert abs(med2 - PGM3_ENGINE_PAYROLL) < 1_000_000, \
        f'median top-51 ${med2/1e6:.1f}M missed the target'
    over = sum(1 for x in _topN(recs) if x > 280_000_000)
    assert over == 0, f'{over} teams over the ~$280M engine cap after scaling'
    print(f'    engine scale   x{f:.4f}  median top-{PAYROLL_TOP_N} '
          f'${med/1e6:.1f}M -> ${med2/1e6:.1f}M  (max drift {worst:.1e})')
    return recs

def contracts_report(recs):
    ros = [p for p in recs if p['teamID'] != 'Free Agent']
    byteam = collections.defaultdict(list)
    for p in ros: byteam[p['teamID']].append(p)
    tots = []
    for t, ps in byteam.items():
        top = sorted(ps, key=lambda x: -(x['salary'] + x['guarantee']))[:51]
        tots.append(sum(x['salary'] + x['guarantee'] for x in top))
    print()
    print('  AGGREGATE VALIDATION (per-player accuracy is unavailable for veterans)')
    print(f'    basis: top-51 cap hit = salary + guarantee, the Rule of 51 in force in 2000')
    print(f'    real 2000 cap: ${TEAM_CAP_2000/1e6:.2f}M per team')
    print(f'    median team   ${statistics.median(tots)/1e6:6.2f}M  '
          f'({100*statistics.median(tots)/TEAM_CAP_2000:.0f}% of cap)')
    print(f'    range         ${min(tots)/1e6:6.2f}M - ${max(tots)/1e6:.2f}M   '
          f'over cap: {sum(1 for x in tots if x > TEAM_CAP_2000)}/31')
    sal = sorted(p['salary'] for p in ros)
    n = len(sal)
    print(f'    salary p10 ${sal[n//10]/1000:.0f}k  median ${sal[n//2]/1000:.0f}k  '
          f'p90 ${sal[9*n//10]/1e6:.2f}M  max ${sal[-1]/1e6:.2f}M')
    below = [p for p in ros if p['salary'] < min_salary(int(p['_src']['PYRP']))]
    drawn_below = [p for p in below if p.get('_src_tag') != 'OTC']
    print(f'    below the 2000 minimum ladder: {len(below)}/{len(ros)}  '
          f'({len(drawn_below)} drawn, {len(below)-len(drawn_below)} real and correctly not clamped)')
    for p in below:
        if p.get('_src_tag') == 'OTC':
            print(f'      {p["forename"]} {p["surname"]}: real OTC cap ${p["salary"]+p["guarantee"]:,} '
                  f'splits to ${p["salary"]:,} base — the minimum applies to base, the cap number includes bonus')
    assert not drawn_below, 'a DRAWN salary fell below the league minimum'
    return recs

# ============================================================ stage 8: staff
# Coordinators and special teams are rated on THE SEASON BEING BUILT -- 2000's
# own units. Head coaches are the exception: their career record runs through
# the PRIOR season, since 2000 has not happened from their perspective at
# hiring. The prior-season rule for coordinators applies to current-season
# builds only, and applying it to a historical build is an error that has
# happened once.
#
# Unit ranks are COMPUTED from real 2000 game results (nflverse games.csv),
# not researched: points for and against per team over 16 games, 31 teams.
# Special teams come from Gosselin's 2000 rankings, his earliest published year.
GOSSELIN_2000 = ['MIA','CAR','TEN','BAL','SEA','OAK','NE','PHI','DET','DAL','TB',
                 'GB','PIT','ATL','CHI','JAX','ARI','MIN','IND','STL','CLE','DEN',
                 'NYJ','NYG','KC','CIN','NO','SD','WAS','SF','BUF']
# nflverse and Gosselin both use PERIOD team codes; the build uses modern ids.
PERIOD_TO_MODERN = {'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
def modern(t): return PERIOD_TO_MODERN.get(t, t)

# A head coach rating cannot be computed here: career records through 1999 are
# not derivable from anything in the repo. nflverse game data carries coach
# names only from 1999, and the PFR season coaches index gives lifetime totals
# (Andy Reid reads 437 games on the 1999 page against the 16 he had actually
# coached). Both routes are documented as dead in the handoff.
#
# The gap is left as a SENTINEL THAT FAILS THE VALIDATOR LOUDLY, not as a zero.
# A zero rating on 31 head coaches is the exact shape of the staff-attribute bug
# that once crashed the game and passed every check that was run.
# Career records through 1999, supplied 2026-08-31 and verified against
# independently computed 1999 season records before use: every career total
# contains its 1999 season, every first-year coach's career equals his 1999
# season exactly, and the zero set is precisely the seven men who had never
# been an NFL head coach.
#
# RULING (Ryan, 2026-08-31): regress toward .500 by GAMES, not seasons.
# The regression exists to discount small samples and games is the actual
# sample size -- a four-game interim spell and a sixteen-game season are not
# equal evidence. It also dissolves the definitional question rather than
# answering it: Wade Phillips's 1985 four-game New Orleans stint contributes
# four games' worth whether or not anyone calls it a season, so his 68 games
# stand on their own and nobody has to remember a convention.
#
# RULING (Ryan, 2026-08-31): Coach of the Year is AP ONLY. A clean comparable
# standard, and it costs four men who won PFWA, UPI or Greasy Neale awards in
# this era -- BOBBY ROSS, TOM COUGHLIN, DAVE WANNSTEDT and DENNIS GREEN all
# show zero. Recorded by name so nobody later "fixes" it by adding the other
# bodies.
# Calibrated against the published head-coach distribution (224 team head
# coaches across seven files: min 58, p25 67, median 72, p75 79, max 95).
# A first version regressed toward .500 with no experience term and produced a
# floor of 68 against a published 58, with TEN of thirty-one coaches tied on the
# prior — every unproven man landing on the league median. Holding the job is
# itself evidence, and it is what separates a first-time hire from a .500
# veteran, so an experience term carries that and breaks the tie.
HC_PRIOR_GAMES = 24          # regression prior, in games
HC_BASE, HC_SPAN = 34.0, 66.0
HC_EXP_WEIGHT, HC_EXP_FULL = 9.0, 160.0    # ~10 seasons to saturate

def hc_rating(row):
    """Career record through the PRIOR season, regressed toward .500 BY GAMES,
    plus an experience term and Super Bowl, playoff and Coach of the Year
    bonuses."""
    w, l, t = int(row['reg_w']), int(row['reg_l']), int(row['reg_t'])
    g = w + l + t
    pct = (w + 0.5 * t + 0.5 * HC_PRIOR_GAMES) / (g + HC_PRIOR_GAMES)
    r = HC_BASE + HC_SPAN * pct
    r += HC_EXP_WEIGHT * min(1.0, g / HC_EXP_FULL)
    r += 3.0 * int(row['super_bowl_wins'])
    r += 0.55 * int(row['playoff_w'])
    r += 2.0 * int(row['coach_of_year'])
    return max(50, min(95, int(round(r))))


# The sentinel that stood here is gone: hc_rating() now computes from the
# supplied career records. Worth noting honestly that it was never exercised —
# no PGMStaff_2000.json has been written yet, so the validator never saw it.
# It did its job as a design decision, not as a caught failure.

def team_units_2000():
    """Offensive and defensive rank per team from real 2000 results."""
    path = os.path.join(REPO, 'wip', 'games_2000.csv')
    pf, pa = collections.Counter(), collections.Counter()
    for r in csv.DictReader(open(path, encoding='utf-8')):
        h, a = modern(r['home_team']), modern(r['away_team'])
        hs, as_ = int(r['home_score']), int(r['away_score'])
        pf[h] += hs; pa[h] += as_; pf[a] += as_; pa[a] += hs
    assert len(pf) == 31, f'expected 31 teams in 2000, got {len(pf)}'
    off = {t: i + 1 for i, t in enumerate(sorted(pf, key=lambda x: -pf[x]))}
    dfn = {t: i + 1 for i, t in enumerate(sorted(pa, key=lambda x: pa[x]))}
    st = {modern(t): i + 1 for i, t in enumerate(GOSSELIN_2000)}
    assert set(off) == set(st), 'unit ranks and Gosselin disagree on the team set'
    return off, dfn, st, pf, pa

def employed_elsewhere_2000():
    """Every name holding a job on a real 2000 staff. Houston's eight
    non-Glanville slots must not take any of them -- the spec names Dom Capers,
    Chris Palmer and Vic Fangio explicitly, but the rule is mechanical and
    covers all 124 rows, not a list of three."""
    return {c['name'] for c in csv.DictReader(
        open(os.path.join(REPO, 'sources', 'coaches_2000.csv'), encoding='utf-8'))
        if c['name'].strip()}

def assert_hou_staff_free(names):
    """Assert rather than research: anyone already on another team's staff in
    coaches_2000.csv is barred, and that is checkable mechanically."""
    taken = employed_elsewhere_2000()
    clash = sorted(set(names) & taken)
    assert not clash, ('Houston staff take men employed elsewhere in '
                       'coaches_2000.csv: ' + ', '.join(clash))
    return len(taken)


def rank_to_rating(rank, n=31, lo=52, hi=94):
    """Linear rank -> rating. 31 teams, so rank 1 is the best unit in the league."""
    return int(round(lo + (hi - lo) * (n - rank) / (n - 1)))


STAFF_SCHEMA_SRC = 'PGMStaff_2017.json'
STAFF_ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams',
               'Head Scout', 'Off Scout', 'Def Scout', 'Head Physio',
               'Assistant Physio']
COACH_ROLES = {'Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams'}
SCOUT_ROLES = {'Head Scout', 'Off Scout', 'Def Scout'}
PHYSIO_ROLES = {'Head Physio', 'Assistant Physio'}
# Primary attribute per role — must EQUAL rating.
PRIMARY = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach', 'Def Co-ord': 'DCcoach',
           'Special Teams': 'STcoach', 'Head Scout': 'Hscout', 'Off Scout': 'Oscout',
           'Def Scout': 'Dscout', 'Head Physio': 'Hphysio',
           'Assistant Physio': 'Aphysio'}
# Every coach carries all four coaching attrs, every scout all three, every
# physio both. The specialty-attribute bug crashed the game and passed every
# check that was run at the time.
ATTR_GROUP = {**{r: ['HCcoach', 'OCcoach', 'DCcoach', 'STcoach'] for r in COACH_ROLES},
              **{r: ['Hscout', 'Oscout', 'Dscout'] for r in SCOUT_ROLES},
              **{r: ['Hphysio', 'Aphysio'] for r in PHYSIO_ROLES}}
# Contract fields fitted PER ROLE, never pooled -- but the pooled figure was
# also the wrong target, and breaking eGuarantee down per FILE shows why:
#
#   eGuarantee non-zero %   1986  2004  2007  2010  2013  2017  2021
#     Head Coach             38%    0%    6%  100%   62%    0%    0%
#     Off Co-ord             19%    0%    0%    0%   56%    0%    0%
#     Head Scout              3%    0%    3%    0%   31%    0%    0%
#
# Three files are flat zero across all nine roles, 2010 is 100% for head
# coaches and zero for the other eight, 2013 runs 31-62% throughout, 1986 and
# 2007 are low and scattered. Four behaviours, and the pooled 28%/6-11%
# describes none of them. Fifth instance of the union manufacturing a
# convention no file follows.
#
# RULING (Ryan, 2026-08-31): do not fit eGuarantee for staff. Ship it ZERO.
# It matches the plurality -- three of seven files do exactly that, four
# counting 2010's eight non-HC roles -- it is internally consistent rather than
# an average of incompatible files, and the handoff already records eGuarantee
# as game-computed and overwritten on import.
#
# The handoff's "eGuarantee is head-coach-only, 33% HC / 0% elsewhere" appears
# to have been measured on 2010 alone: that is exactly 2010's shape, and 2010
# is HC-only for `guarantee` too, which no other file is.
#
# `guarantee` IS a real field with a real convention -- non-zero in 28-100% of
# every role in six of seven files, with only 2010 zeroing the non-HC roles --
# so it is fitted per role on those six.
STAFF_EGUARANTEE = 0
ROLE_CONTRACT = {
    'Head Coach':       (915_000, 0.76, 0.28, 1_935_000),
    'Off Co-ord':       (800_000, 0.60, 0.09, 1_052_500),
    'Def Co-ord':       (750_000, 0.61, 0.09, 1_085_000),
    'Special Teams':    (607_500, 0.55, 0.09,   817_500),
    'Head Scout':       (490_000, 0.52, 0.06,   647_500),
    'Off Scout':        (350_000, 0.54, 0.09,   475_000),
    'Def Scout':        (350_000, 0.60, 0.09,   470_000),
    'Head Physio':      (540_000, 0.57, 0.08,   650_000),
    'Assistant Physio': (297_500, 0.55, 0.11,   390_000),
}

SCHEMA_SRC = 'PGMRoster_2017.json'

_PICKS = None

def emit(recs, path, prospects=None):
    global _PICKS
    _PICKS = load_draft_picks()
    """Write the 52-key schema. INCOMPLETE at this point: no draft classes, no
    Houston. Written anyway so the validator runs early -- cheap now, expensive
    at stage 10."""
    ref = json.load(open(os.path.join(REPO, SCHEMA_SRC)))[0]
    keys = list(ref.keys())
    import uuid
    out = []
    for i, p in enumerate(recs):
        r = {}
        for k in keys:
            if k in p and k not in ('_src',):
                r[k] = p[k]
            elif k in p.get('_attr', {}):
                r[k] = p['_attr'][k]
            else:
                r[k] = 0 if isinstance(ref[k], int) else ('' if isinstance(ref[k], str) else [])
        r['forename'] = p['forename']; r['surname'] = p['surname']
        r['position'] = p['position']; r['teamID'] = p['teamID']
        r['appearance'] = p['appearance']
        r['age'] = int(p['_src']['PAGE'])
        yrs = int(p['_src']['PYRP'])
        r['draftSeason'] = SEASON + OFFSET - yrs
        r['draftNum'] = resolve_draft_num(f"{p['forename']} {p['surname']}",
                                          p['position'], yrs, _PICKS)
        rng = seeded(f"{p['forename']}|{p['surname']}|{p['position']}", 'grow')
        # potential and growthType built in the SAME pass, invariant asserted
        r['potential'] = vet_potential(r['age'], p['rating'], rng)
        r['growthType'] = build_growth(r['potential'], p['rating'], rng, 31)
        assert sum(v for v in r['growthType'] if v > 0) == (r['potential'] - p['rating']) * 50
        out.append(r)
    if prospects:
        out += prospects
    assert len(out) == len(recs) + len(prospects or []), 'record count changed on emit'
    # iden must be assigned AFTER the prospects are appended, or they all keep
    # the schema default and collide.
    for r in out:
        r['iden'] = str(uuid.UUID(int=random.Random(
            f"{r['forename']}|{r['surname']}|{r['position']}|{r['teamID']}|"
            f"{r['draftNum']}|{r['draftSeason']}|2000roster").getrandbits(128))).upper()
    ids = {r['iden'] for r in out}
    assert len(ids) == len(out), f'{len(out) - len(ids)} duplicate iden'
    for r in out:
        assert set(r.keys()) == set(keys), 'schema key mismatch'
    json.dump(out, open(path, 'w'), separators=(',', ':'))
    print(f'\n  wrote {path}: {len(out)} records x {len(keys)} keys')
    ros = [r for r in out if r['teamID'] not in ('Free Agent', 'Rookie')]
    print(f"  rostered {len(ros)}  free agents "
          f"{sum(1 for r in out if r['teamID'] == 'Free Agent')}  "
          f"prospects {sum(1 for r in out if r['teamID'] == 'Rookie')}")
    nd = sum(1 for r in out if r['draftNum'] == 224)
    print(f'  draftNum: real picks 1-{max(r["draftNum"] for r in out)}, '
          f'{nd} on the 224 undrafted floor ({100*nd/len(out):.0f}%) — never clamped')
    return out

# =========================================================== stage 8: staff
def load_hc_careers():
    path = os.path.join(REPO, 'sources', 'coaches_2000_HC_career_through_1999.csv')
    return {r['coach']: r for r in csv.DictReader(open(path, encoding='utf-8'))}

def load_hou_staff():
    g = {}
    exec(open(os.path.join(REPO, 'wip', 'hou_staff_2000.py')).read(), g)
    return g['HOU_COACHES']

# guarantee fitted on 1986/2004/2007/2013 — the cluster 2000 sits in by era and
# build vintage. 2017 and 2021 run 88-100% across every role, which reads as a
# later build convention rather than an era property, and pooling all six gives
# the midpoint of two clusters rather than the centre of one.
GUARANTEE_FIT_FILES = (1986, 2004, 2007, 2013)

def staff_record(schema_keys, ref, role, forename, surname, teamID, rating,
                 rng, guar_fit, scheme, profile):
    """Build a staff record from the MEASURED per-role profile.

    A first version hand-listed which attributes each role carries and left
    about thirty specialty fields at zero — management, motivation,
    playcalling, passRush, injPrevent and the rest. That is precisely the
    specialty-attribute bug the handoff records as having crashed the game, and
    it passed every check I had written because I was checking the fields I had
    thought of. The profile is measured off 1986/2004/2007/2013 instead: which
    fields a role populates, at what rate, and around what centre.
    """
    prof = profile[role]
    r = {}
    for k in schema_keys:
        if isinstance(ref[k], str):
            vocab = prof['str'].get(k)
            r[k] = vocab[0][0] if vocab else ''
        elif isinstance(ref[k], list):
            r[k] = []
        else:
            e = prof['num'][k]
            if e['rate'] < 0.5:
                r[k] = 0                       # this role does not carry it
            else:
                # centre on the role's own median, shifted by how good this
                # person is relative to the role's typical rating
                shift = rating - prof['num']['rating']['med']
                v = e['med'] + 0.55 * shift + rng.gauss(0, max(2.0, e['sd'] * 0.45))
                r[k] = max(1, min(99, int(round(v))))

    r['forename'], r['surname'] = forename, surname
    r['role'], r['teamID'] = role, teamID
    r['rating'] = rating
    r['potential'] = min(99, max(rating, rating + rng.randint(0, 4)))
    for a in ATTR_GROUP[role]:
        r[a] = max(35, min(99, r[a] if r[a] else rating - rng.randint(2, 14)))
    r[PRIMARY[role]] = rating                  # primary MUST equal rating

    r['age'] = max(30, min(72, int(round(rng.gauss(50, 8)))))
    r['startSeason'] = max(1989, min(2026,
        int(round(-0.881 * r['age'] + 2054.5 + rng.gauss(0, 2.5)))))

    base, _, _, esal = ROLE_CONTRACT[role]
    mult = 0.55 + 1.3 * max(0.0, (rating - 55)) / 40.0
    if teamID == 'Free Agent':
        # free agent staff carry no contract, as every published file does
        r['salary'] = 0; r['guarantee'] = 0
        r['eSalary'] = int(round(esal * mult * rng.uniform(0.85, 1.2) / 1000) * 1000)
        r['length'] = 0
    else:
        r['salary'] = int(round(base * mult * rng.uniform(0.85, 1.2) / 1000) * 1000)
        rate, ratio = guar_fit[role]
        r['guarantee'] = (int(round(r['salary'] * ratio * rng.uniform(0.7, 1.4) / 1000) * 1000)
                          if rng.random() < rate else 0)
        r['eSalary'] = int(round(esal * mult * rng.uniform(0.85, 1.2) / 1000) * 1000)
        r['length'] = max(1, r['length'] or 2)
    r['eGuarantee'] = STAFF_EGUARANTEE
    r['eLength'] = max(0, min(4, r['eLength'] or 2))

    gt = [0] * 51
    need = (r['potential'] - r['rating']) * 50
    if need:
        slots = rng.sample(range(0, 17), min(6, max(1, need // 100 + 1)))
        share = need // len(slots)
        for i, sl in enumerate(slots):
            gt[sl] = share if i else need - share * (len(slots) - 1)
    assert sum(v for v in gt if v > 0) == need, 'growthType 50x construction failed'
    for sl in rng.sample(range(20, 51), rng.randint(5, 12)):
        gt[sl] = -100 * rng.randint(1, 4)
    r['growthType'] = gt

    # strings: draw from the role's own observed vocabulary, then let the team
    # scheme override the scheme fields so every coach on a team shares one
    for k, vocab in prof['str'].items():
        if k in ('role', 'teamID', 'forename', 'surname', 'iden'): continue
        r[k] = rng.choices([v for v, _ in vocab], weights=[c for _, c in vocab])[0]
    for k, v in scheme.items():
        if k in r: r[k] = v
    # scoutBoost is side-constrained: Off Scout offensive positions, Def Scout
    # defensive, Head Scout either
    if role in SCOUT_ROLES and 'scoutBoost' in r:
        OFFP = ['QB','RB','WR','TE','OT','OG','C']
        DEFP = ['DE','DT','OLB','MLB','CB','S']
        r['scoutBoost'] = rng.choice(OFFP if role == 'Off Scout' else
                                     DEFP if role == 'Def Scout' else OFFP + DEFP)
    return r


def stage8():
    ref_all = json.load(open(os.path.join(REPO, STAFF_SCHEMA_SRC)))
    ref = ref_all[0]; keys = list(ref.keys())
    coaches = list(csv.DictReader(open(os.path.join(REPO, 'sources', 'coaches_2000.csv'),
                                       encoding='utf-8')))
    careers = load_hc_careers()
    off, dfn, st, _, _ = team_units_2000()
    guar_fit = {k: tuple(v) for k, v in
                json.load(open(os.path.join(REPO, 'wip', 'staff_guarantee_fit.json'))).items()}
    pool = json.load(open(os.path.join(REPO, 'wip', 'staff_name_pool.json')))
    profile = json.load(open(os.path.join(REPO, 'wip', 'staff_profile.json')))
    real_names = set(pool['real_coach_names'])

    # Schemes are assigned PER TEAM and shared by every coach on it. The scheme
    # itself is not researched for 2000 -- but the documented bug was coaches on
    # one team carrying different schemes, and that is what this fixes.
    SCHEME_FIELDS = ('offStyle', 'defStyle', 'blitzStyle', 'fourthStyle', 'rbStyle')
    vocab = {f: sorted({p[f] for p in ref_all if p.get(f)}) for f in SCHEME_FIELDS}
    teams = sorted({modern(c['team']) for c in coaches}) + ['HOU']
    schemes = {t: {f: seeded(t, 'scheme').choice(vocab[f]) for f in SCHEME_FIELDS}
               for t in teams}

    out = []
    RATED = {}
    for c in coaches:
        # coaches_2000.csv carries PERIOD codes (OAK/SD/STL); the roster and the
        # unit ranks use modern ids. Translate at the boundary — two scripts
        # exchanging records must not each define their own vocabulary.
        t, role_key, nm = modern(c['team']), c['role'], c['name']
        role = {'HC': 'Head Coach', 'OC': 'Off Co-ord',
                'DC': 'Def Co-ord', 'ST': 'Special Teams'}[role_key]
        if role_key == 'HC':
            rating = hc_rating(careers[nm])
        elif role_key == 'OC':
            rating = rank_to_rating(off[t])
        elif role_key == 'DC':
            rating = rank_to_rating(dfn[t])
        else:
            rating = rank_to_rating(st[t])
        RATED[(t, role)] = (nm, rating)

    hou = load_hou_staff()
    assert_hou_staff_free([f'{f} {l}' for _, f, l, _ in hou])
    for role, f, l, career in hou:
        rating = hc_rating(career) if career else 68
        RATED[('HOU', role)] = (f'{f} {l}', rating)

    for (t, role), (nm, rating) in sorted(RATED.items()):
        f, _, l = nm.partition(' ')
        rng = seeded(f'{nm}|{t}|{role}', 'staff')
        out.append(staff_record(keys, ref, role, f, l, t, rating, rng, guar_fit, schemes[t], profile))

    # scouts and physios: generated, the one deliberate exception to
    # no-invented-humans. Names recombined from the published files' existing
    # invented pool and checked against every real coach name in the archive.
    used = set()
    for t in teams:
        for role in ('Head Scout', 'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio'):
            rng = seeded(f'{t}|{role}', 'gen')
            for _ in range(400):
                f = rng.choice(pool['forenames']); l = rng.choice(pool['surnames'])
                if f'{f} {l}' not in real_names and (f, l) not in used:
                    used.add((f, l)); break
            else:
                raise AssertionError(f'could not generate a free name for {t}/{role}')
            rating = max(45, min(88, int(round(rng.gauss(66, 8)))))
            out.append(staff_record(keys, ref, role, f, l, t, rating, rng, guar_fit, schemes[t], profile))

    assert len(out) == len(teams) * 9, f'{len(out)} staff for {len(teams)} teams'
    return out, keys, pool, real_names, guar_fit, schemes, vocab, profile


# Real coaches for the free agent pool. The rule is that real names form a
# clean top block and invented names sit strictly below ALL of them.
#
# These three are the men displaced by 2000's mid-season changes, documented in
# the notes of coaches_2000.csv itself: each lost his job during the season and
# is not on any 2000 staff in the file. Verified against the file rather than
# researched separately.
FA_REAL_COACHES = [
    ('Head Coach', 'Vince', 'Tobin',  'Arizona games 1-7; McGinnis took the slot'),
    ('Head Coach', 'Bruce', 'Coslet', 'Cincinnati games 1-3; LeBeau took the slot'),
    ('Head Coach', 'Gary',  'Moeller', 'Detroit games 10-16; Ross took the slot'),
]
FA_POOL_SIZE = 165

def stage8_free_agents(keys, ref, pool, real_names, guar_fit, used_names, profile):
    out = []
    scheme = {}
    for role, f, l, why in FA_REAL_COACHES:
        rng = seeded(f'{f} {l}', 'fa')
        rating = max(58, min(78, int(round(rng.gauss(68, 5)))))
        r = staff_record(keys, ref, role, f, l, 'Free Agent', rating, rng, guar_fit, scheme, profile)
        r['_why'] = why
        out.append(r)
    floor = min(p['rating'] for p in out)
    for i in range(FA_POOL_SIZE - len(out)):
        rng = seeded(f'fa|{i}', 'gen')
        for _ in range(400):
            f = rng.choice(pool['forenames']); l = rng.choice(pool['surnames'])
            if f'{f} {l}' not in real_names and (f, l) not in used_names:
                used_names.add((f, l)); break
        else:
            raise AssertionError('ran out of free generated names for the FA pool')
        role = STAFF_ROLES[i % len(STAFF_ROLES)]
        # strictly BELOW every real coach in the pool
        rating = max(40, min(floor - 1, int(round(rng.gauss(56, 7)))))
        out.append(staff_record(keys, ref, role, f, l, 'Free Agent', rating, rng,
                                guar_fit, scheme, profile))
    reals = [p['rating'] for p in out[:len(FA_REAL_COACHES)]]
    invs = [p['rating'] for p in out[len(FA_REAL_COACHES):]]
    assert min(reals) > max(invs), (
        f'invented FA coach at {max(invs)} is not strictly below the real block '
        f'(lowest real {min(reals)})')
    return out


# Staff are the exception to the family-digit rule: a coach has one look and no
# aging, so the WHOLE registry array is correct for him.
#
# Two cases 2000 has to get right, both crossing the 1986 boundary:
#   Jerry Glanville sits in staff_faces_1986 and NOT in staff_faces. Same man,
#     same city, fourteen years apart — his 1986 Houston face is his 2000 face.
#   `jim mora` exists in BOTH blocks and they are DIFFERENT MEN. staff_faces_1986
#     Head2c is the father, 1986 New Orleans; staff_faces Head1c is the son,
#     2004 Atlanta. 2000 is the first file where both are active, so it is the
#     first that can route them by team and role instead of skipping the key.
# Father/son pairs the registry MERGES, because its normalization strips
# Jr/Sr. Each needs routing by team and role, which is the only thing that
# separates them.
MORA_ROUTE = {
    ('IND', 'Head Coach'):   'staff_faces_1986',  # Jim E. Mora, father
    ('SF',  'Def Co-ord'):   'staff_faces',       # Jim L. Mora, son
    # Frank Gansz Sr. joined Jacksonville in 2000 from the Rams, having been
    # Kansas City's special teams coach and then head coach in the 1980s — the
    # same man as the 1986 file. Frank Gansz Jr. is the one in 2004 and 2007
    # (Raiders 1998-2000, Chiefs 2001-05, Ravens 2006-07), which is why the
    # era rule below cannot see Sr.: the normalized key `frank gansz` appears
    # in later files as the SON.
    ('JAX', 'Special Teams'): 'staff_faces_1986',  # Frank Gansz Sr., father
}
GLANVILLE_BLOCK = 'staff_faces_1986'

def era_1986_only():
    """Staff who appear in the 1986 file and in NO later published file.

    The registry holds some men in BOTH blocks with different faces — Glanville
    and Frank Gansz are both 1986 and 2000 coaches, and their two entries
    disagree. For a man whose only other appearance is 1986, taking the 1986
    face is the choice that leaves him consistent across every file he is in;
    taking staff_faces would create a fresh disagreement. For a man who also
    appears in 2004 or later, staff_faces is the consistent choice instead.
    Derived rather than hardcoded, so it covers whoever else turns up.
    """
    def names(y):
        path = os.path.join(REPO, f'PGMStaff_{y}.json')
        if not os.path.exists(path): return set()
        return {norm_registry(q['forename'] + ' ' + q['surname'])
                for q in json.load(open(path))}
    later = set()
    for y in (2004, 2007, 2010, 2013, 2017, 2021):
        later |= names(y)
    return names(1986) - later

def staff_vocab():
    """Per-slot appearance vocabulary observed in the published STAFF files."""
    v = collections.defaultdict(set)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMStaff_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            for i, tok in enumerate(q['appearance']): v[i].add(tok)
    out = {i: sorted(v[i]) for i in v}
    out['_skin_families'] = sorted({t.replace('Head', '')[0] for t in out[0]})
    # a hair family is usable only if every one of slots 2, 3 and 4 has it
    fam2 = {t.replace('Hair', '')[0] for t in out[2]}
    fam3 = {t.replace('Beard', '')[0] for t in out[3]}
    fam4 = {t.replace('Eyebrows', '')[0] for t in out[4]}
    out['_hair_families'] = sorted(fam2 & fam3 & fam4)
    return out

STAFF_VOCAB = None

def apply_staff_registry(records):
    global STAFF_VOCAB
    STAFF_VOCAB = staff_vocab()
    reg = json.load(open(os.path.join(REPO, 'reference', 'PGM3_FACE_REGISTRY.json')))
    sf, sf86 = reg['staff_faces'], reg['staff_faces_1986']
    locked = set(reg['_verified_keys']['staff'])
    assert len(locked) == 18, (f'_verified_keys.staff reads {len(locked)}, expected 18 — '
                               'the registry copy is stale, re-pull it')
    only86 = era_1986_only()
    stat = collections.Counter(); routed = []
    for p in records:
        key = norm_registry(p['forename'] + ' ' + p['surname'])
        blk = MORA_ROUTE.get((p['teamID'], p['role']))
        if blk is None and key in only86: blk = 'staff_faces_1986'
        if blk:
            face = (sf86 if blk == 'staff_faces_1986' else sf).get(key)
            routed.append((f"{p['forename']} {p['surname']}", p['teamID'], p['role'], blk))
        else:
            face = sf.get(key) or sf86.get(key)
        if face:
            p['appearance'] = list(face)
            stat['registry' + (' (LOCKED)' if key in locked else '')] += 1
        else:
            # Draw from the STAFF appearance vocabulary, which is not the
            # roster one -- staff wear glasses and use hair families the player
            # vocabulary does not contain. Generating plausible-looking
            # combinations produced Hair5e, Hair4k and Beard3c, none of which
            # exist for staff.
            rng = seeded(key, 'staffface')
            fam = rng.choice(sorted(STAFF_VOCAB['_skin_families']))
            hair = rng.choice(sorted(STAFF_VOCAB['_hair_families']))
            def pick(slot, prefix, family):
                opts = [v for v in STAFF_VOCAB[slot]
                        if v.startswith(f'{prefix}{family}')]
                return rng.choice(sorted(opts)) if opts else STAFF_VOCAB[slot][0]
            p['appearance'] = [
                pick(0, 'Head', fam), rng.choice(sorted(STAFF_VOCAB[1])),
                pick(2, 'Hair', hair), pick(3, 'Beard', hair),
                pick(4, 'Eyebrows', hair), pick(5, 'Nose', fam),
                pick(6, 'Mouth', fam), rng.choice(sorted(STAFF_VOCAB[7])),
                rng.choice(sorted(STAFF_VOCAB[8]))]
            stat['generated'] += 1
    print()
    print('  faces:')
    for k, v in sorted(stat.items()):
        print(f'    {k:22} {v:4}  {100*v/len(records):5.1f}%')
    for nm, t, role, blk in routed:
        print(f'    routed: {nm} ({t}/{role}) -> {blk}')
    return records


def emit_staff(records, path):
    ref = json.load(open(os.path.join(REPO, STAFF_SCHEMA_SRC)))[0]
    keys = set(ref.keys())
    import uuid
    for p in records:
        p.pop('_why', None)
        p['iden'] = str(uuid.UUID(int=random.Random(
            f"{p['forename']}|{p['surname']}|{p['role']}|{p['teamID']}|2000staff"
        ).getrandbits(128))).upper()
    assert len({p['iden'] for p in records}) == len(records), 'duplicate staff iden'
    for p in records:
        assert set(p.keys()) == keys, f'schema mismatch on {p["surname"]}'
        assert p[PRIMARY[p['role']]] == p['rating'], f'primary != rating for {p["surname"]}'
        for a in ATTR_GROUP[p['role']]:
            assert p[a] > 0, f'{p["surname"]} has a zero {a} — the crash bug'
        assert len(p['growthType']) == 51, 'growthType must be 51 for staff'
        assert sum(v for v in p['growthType'] if v > 0) == (p['potential'] - p['rating']) * 50
        assert 1989 <= p['startSeason'] <= 2026
    json.dump(records, open(path, 'w'), separators=(',', ':'))
    print(f'\n  wrote {path}: {len(records)} records x {len(keys)} keys')
    return records


# ==================================================== stage 9: draft classes
# Source tiers, best first. The 2001 class has no rookie-year export and comes
# from 2003 at a TWO-YEAR gap; 2002 is one year; 2003 and 2004 are their own.
DRAFT_SRC = {2001: ('2003 - PLAY.csv', 2), 2002: ('2003 - PLAY.csv', 1),
             2003: ('2003 - PLAY.csv', 0), 2004: ('2004 - PLAY.csv', 0)}
DRAFT_POS_OK = {
    'QB': {'QB'}, 'RB': {'RB', 'HB', 'FB'}, 'WR': {'WR'}, 'TE': {'TE'},
    'OT': {'OT', 'T', 'OL', 'G', 'OG', 'C'}, 'OG': {'G', 'OG', 'OL', 'OT', 'T', 'C'},
    'C': {'C', 'OL', 'G', 'OG'},
    'DE': {'DE', 'DL', 'EDGE', 'OLB', 'LB', 'DT'}, 'DT': {'DT', 'NT', 'DL', 'DE'},
    'OLB': {'OLB', 'LB', 'MLB', 'ILB', 'DE'}, 'MLB': {'MLB', 'LB', 'ILB', 'OLB'},
    'CB': {'CB', 'DB'}, 'S': {'S', 'SAF', 'FS', 'SS', 'DB'},
    'K': {'K', 'PK'}, 'P': {'P'},
}

# Measured on 6,124 published prospects: the potential gap is driven by RATING,
# not by draft round. Median gap by rating band runs 18 / 8 / 4 / 4 / 5 / 1 from
# the 40s to the 90s, while by round it is a flat 5-8. A low-rated prospect has
# headroom; a 90-rated one is nearly finished.
#
# A first version derived potential from the draft slot alone and collapsed it
# to rating for every matched player whose Madden rating already exceeded the
# slot baseline — median gap 0 against a published 3-8, i.e. a draft class with
# no growth in it.
GAP_BY_BAND = {4: 18, 5: 8, 6: 4, 7: 4, 8: 5, 9: 1}

def roster_hair_vocab():
    """Hair styles actually observed in the PLAYER files. Not the same set the
    staff files use -- generating from the wrong one emitted Hair4k, which
    exists for staff and not for players."""
    v = collections.defaultdict(set)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            t = q['appearance'][2].replace('Hair', '')
            v[t[0]].add(t[1:])
    return {k: sorted(x) for k, x in v.items()}
ROSTER_HAIR = None

def draft_potential(pick, row, rating, rng):
    """Potential is RAISE-ONLY: a rating-derived headroom sets the baseline and
    career outcomes pull it UP, never down.

    A bust is a player who had the ceiling and did not reach it; lowering his
    potential conflates ceiling with achievement and bakes hindsight into innate
    ability. No gap cap tighter than the published files -- their gaps run to
    36, 33 and 23, and the 2013 build's cap of 14 put Louis Nix above Aaron
    Donald.
    """
    band = GAP_BY_BAND.get(min(9, max(4, rating // 10)), 4)
    headroom = max(0, band + rng.gauss(0, band * 0.45))
    def num(k):
        try: return float(row.get(k) or 0)
        except (ValueError, TypeError): return 0.0
    raise_ = (0.9 * min(6, num('probowls')) + 1.6 * min(4, num('allpro'))
              + 0.09 * min(120, num('car_av')) + 0.30 * min(12, num('seasons_started')))
    # Bound the gap at 40. The published files top out at 36 / 33 / 23, so this
    # is LOOSER than any of them -- it exists to stop headroom and career raise
    # stacking into an outlier, not to compress the class. The 2013 build capped
    # at 14 against 29-45 elsewhere and put Louis Nix above Aaron Donald; that
    # is the failure this must not repeat.
    return int(round(rating + min(40.0, headroom + raise_)))

def build_growth(potential, rating, rng, n_slots=31):
    """growthType and potential are TIED by the 50x rule and must be built in
    the SAME pass. The last time potential was rebuilt without rebuilding growth
    alongside it, all five published files shipped broken and every individual
    check passed, because both fields were independently plausible and the
    defect lived in the rule connecting them.
    """
    gt = [0] * n_slots
    need = (potential - rating) * 50
    if need:
        k = min(6, max(1, need // 150 + 1))
        slots = rng.sample(range(0, 17), k)
        share = need // k
        for i, sl in enumerate(slots):
            gt[sl] = share if i else need - share * (k - 1)
    for sl in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))):
        gt[sl] = -100 * rng.randint(1, 3)
    assert sum(v for v in gt if v > 0) == need, '50x invariant broken at construction'
    return gt


def stage9(schema_keys, ref, tvals, trate):
    NFLD = os.path.join(REPO, 'wip', 'draft_picks_2001_2004.csv')
    draft = collections.defaultdict(list)
    for r in csv.DictReader(open(NFLD, encoding='utf-8')):
        draft[int(r['season'])].append(r)

    global ROSTER_HAIR
    ROSTER_HAIR = roster_hair_vocab()
    out = []
    report = []
    for cls in (2001, 2002, 2003, 2004):
        fname, gap = DRAFT_SRC[cls]
        rows = list(csv.DictReader(open(os.path.join(REPO, 'sources', 'madden', fname),
                                        encoding='latin-1')))
        idx = collections.defaultdict(list)
        for r in rows:
            idx[norm(r['PFNA'] + ' ' + r['PLNA'])].append(r)
        # per-position source distributions, for the quantile map
        srcd = collections.defaultdict(list)
        for r in rows:
            for a, col in list(DIRECT.items()) + list(INVERTED.items()):
                try: srcd[(PPOS[int(r['PPOS'])], a)].append(int(r[col]))
                except (ValueError, KeyError): pass
        for k in srcd: srcd[k].sort()

        matched = filled = posmis = 0
        for d in draft[cls]:
            pick = int(d['pick']); nm = d['pfr_player_name']
            f, _, l = nm.partition(' ')
            dpos = (d['position'] or '').upper()
            pgm = DRAFT_POS_MAP.get(dpos, dpos if dpos in DRAFT_POS_OK else 'WR')
            rng = seeded(f'{nm}|{cls}', 'draft')
            cands = idx.get(norm(nm), [])
            src = None
            if len(cands) == 1:
                mp = PPOS[int(cands[0]['PPOS'])]
                if dpos and dpos in DRAFT_POS_OK.get(mp, set()):
                    src, pgm = cands[0], mp
                else:
                    posmis += 1
            if src is not None:
                matched += 1
                rating = int(src['POVR'])
            else:
                filled += 1
                rating = int(round(74 - 9.5 * math.log(max(1, pick)) + rng.gauss(0, 4)))
            rating = max(40, min(93, rating))

            potential = min(99, draft_potential(pick, d, rating, rng))
            rec = {k: (0 if isinstance(ref[k], int) else ('' if isinstance(ref[k], str) else []))
                   for k in schema_keys}
            rec.update(forename=f, surname=l, position=pgm, teamID='Rookie',
                       rating=rating, potential=potential,
                       draftNum=pick,                      # REAL pick, never clamped
                       draftSeason=SEASON + OFFSET + (cls - SEASON),
                       age=21 + rng.randint(0, 3), salary=0, guarantee=0,
                       length=0, teamNum=0, eSalary=0, eGuarantee=0, eLength=0)
            # potential and growth built together, invariant asserted here
            rec['growthType'] = build_growth(potential, rating, rng, 31)
            assert sum(v for v in rec['growthType'] if v > 0) == (potential - rating) * 50

            for a in ALL_ATTRS:
                tgt = tvals.get(('R', pgm, a)) or tvals.get(('R', 'WR', a))
                if not tgt or trate.get(('R', pgm, a), 0) < 0.5:
                    rec[a] = 0; continue
                if src is not None and a in DIRECT:
                    v = int(src[DIRECT[a]])
                    if a == 'intelligence':
                        v += pawr_correction(gap)      # gap 2 only, asserted
                    s = srcd.get((pgm, a)) or [v]
                    rec[a] = int(qmap([v], s, tgt)[0])
                elif src is not None and a in INVERTED:
                    v = -int(src[INVERTED[a]])
                    s = [-x for x in srcd.get((pgm, a), [-v])][::-1] or [v]
                    rec[a] = int(qmap([v], sorted(s), tgt)[0])
                else:
                    q = max(0.0, min(1.0, (rating - 40) / 53.0))
                    rec[a] = int(tgt[min(len(tgt) - 1, int(round(q * (len(tgt) - 1))))])
            # Prospects have no PSKI source of their own. Seed a valid face here
            # so the record is complete; the registry and the appearance library
            # run over the top at stage 10, which is where a prospect who later
            # appears in a published file picks up his real one.
            fr = seeded(f'{nm}|{cls}', 'face')
            skin = draw(fr, ABSTAIN_BAND)
            hair = fr.choice(list(HAIR_FAM.values()))
            lb = 180 + fr.randint(0, 140)
            variant = 'b' if lb >= 260 else 'a'          # every prospect is young
            rec['appearance'] = [
                f'Head{skin}{variant}', f'Eyes1{fr.choice("abcde")}',
                f'Hair{hair}{fr.choice(ROSTER_HAIR[hair])}',
                f'Beard{hair}{fr.choice(BEARD_STYLES)}',
                f'Eyebrows{hair}{fr.choice("ab")}',
                f'Nose{skin}{fr.choice("abcd")}', f'Mouth{skin}{fr.choice("ab")}',
                'Glasses1e', f'Clothes{fr.choice("12")}']
            out.append(rec)
        report.append((cls, len(draft[cls]), fname, gap, matched, filled, posmis))
    return out, report

DRAFT_POS_MAP = {'HB': 'RB', 'FB': 'RB', 'T': 'OT', 'G': 'OG', 'OL': 'OG',
                 'DL': 'DE', 'NT': 'DT', 'LB': 'OLB', 'ILB': 'MLB', 'EDGE': 'DE',
                 'DB': 'CB', 'SAF': 'S', 'FS': 'S', 'SS': 'S', 'PK': 'K', 'LS': 'C'}
ATTR_LIVE_FIX = ()

# Rostered and free agent potential, measured on 6,356 published records: the
# gap tracks AGE, running 5 / 4 / 1 across the early twenties, mid twenties and
# late twenties, and is never negative. Raise-only applies here too.
VET_GAP_BY_AGE = ((23, 5), (26, 4), (29, 1))
def vet_potential(age, rating, rng):
    g = 0
    for lim, v in VET_GAP_BY_AGE:
        if age <= lim: g = v; break
    if g == 0: g = 0 if age > 32 else 1
    return int(round(min(99, rating + max(0, g + rng.gauss(0, g * 0.6 if g else 0.4)))))

def load_draft_picks():
    """name -> [(pick, position, season)]. Kept as a LIST because 114 names
    carry more than one pick, and collapsing them is the namesake bug."""
    out = collections.defaultdict(list)
    path = os.path.join(REPO, 'wip', 'draft_picks_pre2001.csv')
    for r in csv.DictReader(open(path, encoding='utf-8')):
        out[r['name']].append((int(r['pick']), (r['position'] or '').upper(), int(r['season'])))
    return out

def resolve_draft_num(name, position, yrs_pro, picks):
    """Real pick number, position-aware, with 224 as the undrafted floor.

    224 is both the floor and a real pick, so the value is overloaded and the
    published files carry real picks to 255, 262 and 329. Never clamp.
    """
    cands = picks.get(norm(name), [])
    if not cands: return 224
    ok = [c for c in cands if not c[1] or c[1] in DRAFT_POS_OK.get(position, {c[1]})]
    if len(ok) == 1: return ok[0][0]
    if len(ok) > 1:
        # a man with N years of service entered the league about that long ago
        want = SEASON - yrs_pro
        best = min(ok, key=lambda c: abs(c[2] - want))
        if abs(best[2] - want) <= 2: return best[0]
        return 224
    return 224



# ============================================ stage 10: library, then registry
# ORDER IS THE THING THAT HAS COST THIS PROJECT WORK TWICE.
#   1. the appearance library is a BULK pass -> it runs FIRST
#   2. the face registry runs LAST, over the top, and NOTHING runs after it
# Doing it the other way silently overwrites hand edits, which has happened and
# took several of Ryan's hand-edited draft prospects with it.

def appearance_library():
    """name|position -> appearance, from the published ROSTERED cohorts only.

    Prospects and free agents in the published files were never sourced, so
    they are not evidence about anyone's face. Appearance is 98% stable across
    years, which is what makes a veteran's entry usable for a prospect who
    becomes him later.
    """
    lib = collections.defaultdict(set)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        for q in json.load(open(path)):
            if q['teamID'] in ('Free Agent', 'Rookie'): continue
            lib[(norm_registry(q['forename'] + ' ' + q['surname']), q['position'])].add(
                tuple(q['appearance']))
    # a person carrying more than one face across files is the known
    # name|position split problem; guessing which to copy risks a hand edit
    return {k: list(v)[0] for k, v in lib.items() if len(v) == 1}

def stage10_library(records):
    lib = appearance_library()
    stat = collections.Counter()
    for p in records:
        face = lib.get((norm_registry(p['forename'] + ' ' + p['surname']), p['position']))
        if p['teamID'] not in ('Free Agent', 'Rookie'):
            # A rostered player's SKIN is really sourced, from this file's own
            # PSKI, and the library must not overwrite it. His HAIR is not --
            # hair is seeded here and is constant across seasons for the same
            # man, so taking it from the library is the only way a player
            # absent from the registry looks the same either side of 2000.
            if face:
                p['appearance'][2:5] = list(face[2:5]); stat['library: hair only (skin from PSKI)'] += 1
            else:
                stat['rostered: PSKI skin, seeded hair'] += 1
            continue
        if face:
            p['appearance'] = list(face); stat['library: whole face'] += 1
        else:
            stat['kept seeded'] += 1
    print()
    print('STAGE 10a — appearance library (BULK, runs first)')
    for k, v in sorted(stat.items()): print(f'    {k:36} {v:5}')
    return records

def stage10_registry(records, staff=False):
    """Apply the registry LAST. Nothing runs after this."""
    reg = json.load(open(os.path.join(REPO, 'reference', 'PGM3_FACE_REGISTRY.json')))
    before = {g: set(v) for g, v in reg['_verified_keys'].items()}
    assert len(before['players']) == 84 and len(before['staff']) == 18, \
        f'_verified_keys is {len(before["players"])}/{len(before["staff"])}, expected 84/18'
    faces, faces86 = reg['faces'], reg['faces_1986']
    stat = collections.Counter()
    for p in records:
        key = norm_registry(p['forename'] + ' ' + p['surname'])
        ent = faces.get(f'{key}|{p["position"]}')
        if ent is None:
            stat['no registry entry'] += 1; continue
        # PLAYERS TAKE THE FAMILY DIGIT ONLY. Slots 0, 5 and 6 carry a family
        # digit and an aging variant letter, and the variant legitimately
        # differs between seasons because players age. Writing the array
        # wholesale flattens that, and the collapse is exactly what the `faces`
        # pass detects. Staff are the exception and take the whole array.
        # Take the registry array WHOLESALE, then restore this season's own
        # variant letter in slots 0, 5 and 6. Those three carry a family digit
        # plus an aging variant derived from weight and age, and the variant
        # legitimately differs between seasons -- flattening it is what the
        # `aging variant still varies` check detects.
        #
        # Everything else IS constant across seasons and must be copied: hair,
        # beard and eyebrows above all. Applying only the skin family and
        # leaving hair alone took the archive's hair-style disagreement from 15
        # players to 638.
        cur = p['appearance']
        keep = [cur[i].replace(pre, '')[1:] for i, pre in
                ((0, 'Head'), (5, 'Nose'), (6, 'Mouth'))]
        p['appearance'] = list(ent)
        for (i, pre), var in zip(((0, 'Head'), (5, 'Nose'), (6, 'Mouth')), keep):
            fam = ent[i].replace(pre, '')[0]
            p['appearance'][i] = f'{pre}{fam}{var}'
        stat['registry applied'] += 1
    after = {g: set(v) for g, v in
             json.load(open(os.path.join(REPO, 'reference',
                                         'PGM3_FACE_REGISTRY.json')))['_verified_keys'].items()}
    assert after == before, '_verified_keys changed during the registry pass'
    print()
    print('STAGE 10b — face registry (LAST; nothing runs after it)')
    for k, v in sorted(stat.items()): print(f'    {k:36} {v:5}')
    print(f'    _verified_keys untouched: {len(before["players"])} players, '
          f'{len(before["staff"])} staff')
    return records


# ---------------------------------------------------------------------------
# ENTRY POINT MUST STAY LAST IN THIS FILE. Twice now a new stage was
# appended after it and failed with NameError, because Python binds names
# top to bottom and the main block ran before the stage was defined.
# Append new stages ABOVE this line.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    recs = stage3()
    recs = stage4(recs)
    conditional_pski(recs)
    recs = stage5(recs)
    recs = stage2b(recs)
    recs = stage6(recs)
    conditional_attributes(recs)
    import csv as _csv
    _dp = {}
    _p = os.path.join(REPO, 'wip', 'draft_picks_pre2001.csv')
    if os.path.exists(_p):
        for _r in _csv.DictReader(open(_p, encoding='utf-8')):
            _dp.setdefault(_r['name'], int(_r['pick']))
    recs = stage7(recs, _dp)
    contracts_report(recs)

    # ---- stage 9: draft classes 2001-2004
    _ref = json.load(open(os.path.join(REPO, SCHEMA_SRC)))[0]
    _tv, _tr = published_attr_dists()
    _pros, _rep = stage9(list(_ref.keys()), _ref, _tv, _tr)
    print()
    print('STAGE 9 — draft classes')
    print(f'  {"class":>6}{"picks":>7}{"source":>18}{"gap":>5}{"matched":>9}{"rate":>7}'
          f'{"filled":>8}{"posmis":>8}')
    for cls, n, f, gap, m, fl, pm in _rep:
        print(f'  {cls:>6}{n:>7}{f:>18}{gap:>5}{m:>9}{100*m/n:>6.0f}%{fl:>8}{pm:>8}')
        # ASSERT ON THE MATCH RATE, not the output count. The percentile filler
        # keeps the count right by construction, so a count check here is dead.
        assert m / n >= 0.65, (f'{cls} class matched only {100*m/n:.0f}% of its source — '
                               'the filler is taking over')
    tot = sum(n for _, n, *_ in _rep); mt = sum(r[4] for r in _rep)
    print(f'  overall {mt}/{tot} matched ({100*mt/tot:.0f}%), '
          f'{tot-mt} percentile-filled ({100*(tot-mt)/tot:.0f}%)')
    print(f'  PAWR shift applied at gap 2 only: 2001 -> {pawr_correction(2)}, '
          f'2002 -> {pawr_correction(1)}, 2003/2004 -> {pawr_correction(0)}')
    recs_out = emit(recs, os.path.join(REPO, 'PGMRoster_2000.json'), _pros)
    # stage 10: bulk library FIRST, registry LAST, nothing after it
    recs_out = stage10_library(recs_out)
    recs_out = stage10_registry(recs_out)
    recs_out = scale_to_engine(recs_out)
    _fam = collections.Counter(r['appearance'][0].replace('Head', '')[0] for r in recs_out)
    _var = collections.Counter(r['appearance'][0][-1] for r in recs_out)
    _t = len(recs_out)
    print(f'    head family: ' + '  '.join(f'{k}:{100*v/_t:.1f}%' for k, v in sorted(_fam.items())))
    print(f'    aging variant still varies: ' +
          '  '.join(f'{k}:{100*v/_t:.1f}%' for k, v in sorted(_var.items())))
    for r in recs_out:
        a = r['appearance']
        assert a[0].replace('Head','')[0] == a[5].replace('Nose','')[0] == a[6].replace('Mouth','')[0]
    json.dump(recs_out, open(os.path.join(REPO, 'PGMRoster_2000.json'), 'w'),
              separators=(',', ':'))
    print(f'\n  rewrote PGMRoster_2000.json after the registry pass')
