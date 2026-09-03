#!/usr/bin/env python3
"""
build_1979_faces — appearance for every person in the 1979 file: the 1,408
spine, 184 on the four franchises, 124 in the free-agent pool, 1,147 across
four draft classes, 252 staff. Output wip/faces_1979.csv, one row per person,
with the SOURCE of every skin and hair decision beside it.

  python3 tools/build_1979_faces.py
  python3 tools/build_1979_faces.py --selftest

SKIN, in precedence order — ruled 2026-09-02 from the anchor table:
  1. registry family, faces_1986 / staff_faces blocks. A man in 1979 and 1986
     must share a head family (apply_registry_all applies FAMILY DIGIT only,
     archive-wide). 302 spine men, 37 staff. Fixed, not derived.
  2. 2K5 archive, season saves, majority over ERA-WINDOW votes (saves touching
     1976-1983) first — the archive README: "DISAMBIGUATE ON ERA"; 506 spine
     names carry more than one archive record and 372 cannot be split by
     first/last_seen — then all season saves, then all-time rosters as the
     tiebreak. The archive self-validates at 92-100% leave-one-out.
  3. NFL79.ros PSKI 0 -> light, 2/3 -> dark (the build_2000 mapping, measured
     on 629 matched men). 73% on the anchor: real, weaker than the archive,
     never outranks it. Flagged.
  4. PSKI 1 (bimodal, abstain) or nothing -> the league prior. Logged apart.

WITHIN a band the head family is drawn from the published union — LIGHT 54/25/21
across families 1-3, DARK 38/62 across 4-5 — seeded on the NAME so a rebuild
never reshuffles a face. That seeding is the documented convention and is not
the random draw the 2026 ruling removed: those sat on rating-bearing fields and
moved with every run; this sits on fields with no source at all and is fixed
per person. Reported and counted, never mistaken for data.

HAIR: PHCL from NFL79.ros where the man is in it (58.8% on 0, the expected
61-75% band — a dead skin field does not mean dead hair), else from the 1976 mod,
else generated. Style, eyes, beard, eyebrows, clothes: no source exists anywhere
but the 78 hand-verified 1986 men, none of them 1979 — generated, seeded.

STAFF: registry array whole ("a coach has one look and does not age"). A man in
both blocks takes staff_faces if he appears in a 2004+ staff file, else
staff_faces_1986 — the build_2000 rule, derived not hardcoded. Rest generated
from the staff vocabulary; staff may wear glasses.

GATES, asserted before writing: family rules (0/5/6 share a digit, 2/3/4 share
a digit, players Glasses1e); every token in the schema vocabulary; the head
family shares inside the published per-file range and dark share 64-73%; and
THE CONDITIONAL — split the output by its source and confirm the groups differ
by more than 40 points of light share. The negative test is the 2007 bug: a
generator that never read its source must FAIL that check.
"""
import csv, sys, os, re, json, glob, random, unicodedata, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl2k5
from pgm3_paths import sources, repo

HAIR_FAM = {0: '1', 1: '5', 2: '3', 3: '4', 4: '2'}
# EVERY generated token is drawn from the on-disk PLAYER vocabulary, per slot and
# per family, never from a typed list. The first version copied build_2000's
# HAIR_STYLES constant and emitted Hair4k — a token that exists for staff and not
# for players, the exact defect that build's roster_hair_vocab() docstring warns
# about; that build overrides the constant at runtime and the override was not
# copied. Drawing from the vocabulary makes an off-vocabulary generated token
# impossible; the vocabulary check stays as the gate for registry-supplied arrays.
def by_family(voc, slot, prefix):
    out = collections.defaultdict(list)
    for t in sorted(voc[slot]):
        if t.startswith(prefix) and len(t) > len(prefix):
            out[t[len(prefix)]].append(t)
    return out
LIGHT_BAND = [('1', 0.540), ('2', 0.246), ('3', 0.214)]
DARK_BAND = [('4', 0.378), ('5', 0.622)]
ABSTAIN_BAND = [('1', 0.20), ('2', 0.09), ('3', 0.02), ('4', 0.16), ('5', 0.53)]
ERA = (1976, 1983)
POSMAP = {'DB': 'S', 'LB': 'OLB', 'FB': 'RB', 'HB': 'RB', 'T': 'OT', 'G': 'OG', 'ILB': 'MLB', 'NT': 'DT'}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', s.lower())
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s)).strip()

def seeded(key, salt):
    return random.Random(f'{key}|{salt}|1979')

def draw(rng, band):
    x = rng.random(); acc = 0.0
    for fam, w in band:
        acc += w
        if x <= acc: return fam
    return band[-1][0]

# ------------------------------------------------------------------ sources
def load_archive():
    """name -> (era votes, season votes, all-time votes)."""
    era, season, alltime = (collections.defaultdict(list) for _ in range(3))
    for f in sorted(glob.glob(sources('NFL2k25 Year Saves', '*.DAT'))):
        yrs = [int(y) for y in re.findall(r'\d{4}', os.path.basename(f))]
        lo, hi = (yrs[0], yrs[-1]) if yrs else (0, 0)
        at = (hi - lo) > 3 or 'GOATS' in f
        try:
            pl = nfl2k5.Save(f).players
        except Exception:
            continue
        for q in pl:
            n = norm(q['fname'] + ' ' + q['lname'])
            if at:
                alltime[n].append(q['skin_band'])
            else:
                season[n].append(q['skin_band'])
                if lo <= ERA[1] and hi >= ERA[0]:
                    era[n].append(q['skin_band'])
    return era, season, alltime

def majority(v):
    if not v: return None, 0.0
    (b, k), = collections.Counter(v).most_common(1)
    return (b, k / len(v)) if k / len(v) > 0.5 else (None, k / len(v))

def archive_band(n, era, season, alltime):
    for votes, tag in ((era[n], 'archive era-majority'), (season[n], 'archive season-majority')):
        b, m = majority(votes)
        if b: return b, m, tag
    b, m = majority(alltime[n])
    if b: return b, m, 'archive all-time tiebreak'
    return None, 0.0, ''

def load_ros(path):
    if not os.path.exists(path): return {}
    return {norm(x['PFNA'] + ' ' + x['PLNA']): x for x in csv.DictReader(open(path))}

def load_registry():
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json')))
    p86 = {(norm(k.split('|')[0]), k.split('|')[1]): v for k, v in reg['faces_1986'].items() if k.count('|') >= 1}
    # FILE FIRST. The validator compares file to file, and the shipped 1986 file
    # disagrees with the registry block for two men — Mickey Shuler (block family
    # 1, file family 3) and Gary Anderson (block 4, file 1) — out of 530 checked.
    # What shipped is the authority and the registry is its index, so a man in
    # the 1986 file takes the file's appearance; the block covers the 137 the
    # file does not hold. The two disagreements are registry drift: backlog 32.
    f86 = repo('PGMRoster_1986.json')
    if os.path.exists(f86):
        seen = {}
        for x in json.load(open(f86)):
            if x['teamID'] not in ('Rookie', 'Free Agent'):
                seen.setdefault((norm(x['forename'] + ' ' + x['surname']), x['position']), x['appearance'])
        for k, v in seen.items():
            if k in p86: p86[k] = v
    s86 = {norm(k.split('|')[0]): v for k, v in reg['staff_faces_1986'].items()}
    sm = {norm(k.split('|')[0]): v for k, v in reg['staff_faces'].items()}
    later = set()
    for y in (2004, 2007, 2010, 2013, 2017, 2021):
        p = repo(f'PGMStaff_{y}.json')
        if os.path.exists(p):
            later |= {norm(q['forename'] + ' ' + q['surname']) for q in json.load(open(p))}
    return p86, s86, sm, later

def vocab():
    s = json.load(open(repo('reference', 'PGM3_SCHEMA_REFERENCE.json')))['appearance_vocab_by_slot']
    return {int(k): set(v) for k, v in s.items()}

def staff_vocab():
    v = collections.defaultdict(set)
    for y in (1986, 2004, 2007, 2010, 2013, 2017, 2021):
        p = repo(f'PGMStaff_{y}.json')
        if os.path.exists(p):
            for q in json.load(open(p)):
                for i, tok in enumerate(q['appearance']): v[i].add(tok)
    return {i: sorted(v[i]) for i in v}

def published_family_ranges():
    rng = collections.defaultdict(list); dark = []
    for y in (1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021):
        p = repo(f'PGMRoster_{y}.json')
        if not os.path.exists(p): continue
        r = [x for x in json.load(open(p)) if x['teamID'] not in ('Rookie', 'Free Agent')]
        c = collections.Counter(x['appearance'][0].replace('Head', '')[0] for x in r)
        for f in '12345': rng[f].append(100 * c[f] / len(r))
        dark.append(100 * (c['4'] + c['5']) / len(r))
    return {f: (min(v), max(v)) for f, v in rng.items()}, (min(dark), max(dark))

# ------------------------------------------------------------------ people
def cohorts():
    out = []
    for x in csv.DictReader(open(repo('wip', 'ratings_1979.csv'))):
        out.append(dict(cohort='spine', name=x['name'], pos=x['pgm3_pos'], team=x['team'], age=None))
    for x in csv.DictReader(open(repo('wip', 'franchises_1979.csv'))):
        out.append(dict(cohort='franchise' if x['franchise'] != '(free agent pool)' else 'fa_pool',
                        name=x['name'], pos=x['pgm3_pos'], team=x['franchise'], age=int(x['age']) if x['age'].isdigit() else None))
    for y in (1980, 1981, 1982, 1983):
        for x in csv.DictReader(open(repo('wip', f'draft_class_{y}.csv'))):
            out.append(dict(cohort=f'draft_{y}', name=x['name'], pos=x['pos'], team='Rookie', age=int(x['age'])))
    for x in csv.DictReader(open(repo('wip', 'staff_1979.csv'))):
        out.append(dict(cohort='staff', name=x['forename'] + ' ' + x['surname'], pos=x['role'], team=x['team'], age=int(x['age'])))
    return out

def player_face(p, ctx, disable_source=False):
    n = norm(p['name']); key = f"{n}|{p['pos']}|{p['team']}"
    era, season, alltime = ctx['archive']; n79 = ctx['n79']; n76 = ctx['n76']; p86 = ctx['p86']
    fr = seeded(key, 'face'); hr = seeded(key, 'hair')
    # --- skin band and family
    skin_src, agree, fam = '', 0.0, None
    reg_arr = None
    if (n, p['pos']) in p86:
        # THE VALIDATOR'S RULE, read from its code: head/nose/mouth match on
        # FAMILY DIGIT (the age variant is free — players age) and eyes, hair,
        # beard, eyebrows, glasses, clothes are compared WHOLE. 'Family digit
        # only' in apply_registry_all means slots 0/5/6, not all nine. A first
        # version took only the digit and regenerated the rest, and 248 registry
        # men failed 'hair style constant across seasons'.
        reg_arr = p86[(n, p['pos'])]
        fam, skin_src, agree = reg_arr[0].replace('Head', '')[0], 'registry-1986 family', 1.0
    else:
        b, m, tag = archive_band(n, era, season, alltime) if not disable_source else (None, 0, '')
        if b:
            skin_src, agree = tag, m
            fam = draw(fr, LIGHT_BAND if b == 'light' else DARK_BAND)
        elif n in n79 and int(n79[n]['PSKI']) in (0, 2, 3) and not disable_source:
            k = int(n79[n]['PSKI']); skin_src, agree = f'NFL79 PSKI {k} (73%)', 0.73
            fam = draw(fr, LIGHT_BAND if k == 0 else DARK_BAND)
        elif n in n79:
            skin_src = 'PSKI 1 bimodal -> abstain, league prior'; fam = draw(fr, ABSTAIN_BAND)
        else:
            skin_src = 'no source -> league prior'; fam = draw(fr, ABSTAIN_BAND)
    # --- hair family
    src_row = n79.get(n) or n76.get(n)
    if src_row and src_row.get('PHCL', '').isdigit() and int(src_row['PHCL']) in HAIR_FAM:
        hair, hair_src = HAIR_FAM[int(src_row['PHCL'])], 'PHCL ' + ('NFL79' if n in n79 else '1976 mod')
    else:
        hair, hair_src = hr.choice(list(HAIR_FAM.values())), 'generated'
    # --- variant: age and weight, as build_2000
    age = p['age'] if p['age'] is not None else (int(src_row['PAGE']) if src_row and src_row.get('PAGE', '').isdigit() else 26)
    lb = int(src_row['PWGT']) + 160 if src_row and src_row.get('PWGT', '').isdigit() else 180 + fr.randint(0, 100)
    variant = ('d' if lb >= 260 else 'c') if age >= 30 else ('b' if lb >= 260 else 'a')
    V = ctx['pv']
    head = f'Head{fam}{variant}' if f'Head{fam}{variant}' in ctx['vocab'][0] else hr.choice(V['head'][fam])
    app = [head, hr.choice(V['eyes']['1']), hr.choice(V['hair'][hair]), hr.choice(V['beard'][hair]),
           hr.choice(V['eyebrows'][hair]), hr.choice(V['nose'][fam]), hr.choice(V['mouth'][fam]),
           'Glasses1e', hr.choice(sorted(ctx['vocab'][8]))]
    if reg_arr is not None:
        for i in (1, 2, 3, 4, 7, 8): app[i] = reg_arr[i]                       # whole
        app[5] = f"Nose{fam}{reg_arr[5].replace('Nose', '')[1:]}"            # family from registry, variant theirs too
        app[6] = f"Mouth{fam}{reg_arr[6].replace('Mouth', '')[1:]}"
        hair_src = 'registry-1986 (whole)'
    band = 'light' if fam in '123' else 'dark'
    return app, skin_src, agree, hair_src, band

def staff_face(p, ctx):
    n = norm(p['name']); s86, sm, later, sv = ctx['s86'], ctx['sm'], ctx['later'], ctx['staff_vocab']
    if n in s86 and n in sm:
        return (sm[n], 'registry staff_faces (appears 2004+)') if n in later else (s86[n], 'registry staff_faces_1986')
    if n in s86: return s86[n], 'registry staff_faces_1986'
    if n in sm: return sm[n], 'registry staff_faces'
    fr = seeded(f'{n}|staff', 'face')
    fam = draw(fr, ABSTAIN_BAND); hair = fr.choice(['1', '2', '3', '4', '5'])
    def pick(slot, prefix, fam_digit):
        c = [t for t in sv[slot] if t.startswith(prefix + fam_digit)]
        return fr.choice(c) if c else fr.choice(sv[slot])
    app = [pick(0, 'Head', fam), fr.choice(sv[1]), pick(2, 'Hair', hair), pick(3, 'Beard', hair), pick(4, 'Eyebrows', hair),
           pick(5, 'Nose', fam), pick(6, 'Mouth', fam), fr.choice(sv[7]), fr.choice(sv[8])]
    return app, 'generated (staff vocabulary, league prior)'

# ------------------------------------------------------------------ gates
def check_family_rules(rows, voc):
    for r in rows:
        a = r['appearance']
        assert a[0].replace('Head', '')[0] == a[5].replace('Nose', '')[0] == a[6].replace('Mouth', '')[0], r['name']
        assert a[2].replace('Hair', '')[0] == a[3].replace('Beard', '')[0] == a[4].replace('Eyebrows', '')[0], r['name']
        if r['cohort'] != 'staff': assert a[7] == 'Glasses1e', r['name']
        for i, tok in enumerate(a):
            assert tok in voc[i] or r['cohort'] == 'staff', f'{r["name"]}: {tok} not in vocabulary slot {i}'

def era_dark_share(names):
    """The era's OWN measurement: the 1979-80 save's dark share over the file's
    own names. This is what the gate tests against, because the published
    64-73% range is a 1986-2021 population and 1979 is not in it."""
    idx = {}
    for q in nfl2k5.Save(sources('NFL2k25 Year Saves', '1979-1980SAVEGAME.DAT')).players:
        idx.setdefault(norm(q['fname'] + ' ' + q['lname']), q['skin_band'])
    hit = [idx[norm(n)] for n in names if norm(n) in idx]
    return len(hit), 100 * sum(1 for b in hit if b == 'dark') / max(1, len(hit))

def check_family_gate(rows):
    """THE GATE IS RE-BASED ON THE ERA, and the published range is printed beside
    it so the divergence is visible rather than hidden.

    The first version asserted the 1979 file against the published files' range
    (dark 64.4-72.9%) and failed at 55.9%. Measured: the era's own archive says
    1979 sat at 53.6% over this file's names and 57.3% over all 1,999 men in the
    1979-80 save; 1981-82 reads 48.2%, 1983-84 53.6%. The archive and the
    published files agree within a point for 1999-2013 (64.3 vs 64.4, 65.7 vs
    65.3, 68.1 vs 69.5) and diverge by ~7 at both ends: the published 1986 file
    reads 67.8% against its own era's save at 58.6-60.7%, and 2021 reads 72.9
    against 65.6. So the published range is a later population, and the 1986
    build — one of this project's own — runs seven points darker than its era's
    source (backlog item 31). A gate built from later eras applied to an earlier
    one: the population precedent Ryan ruled, in a new form.

    What the gate CAN test: (1) the file's dark share against the era's own
    measurement, +/-3; (2) the within-band family split against the published
    union, which is the only spread data there is, +/-3 of what that split
    implies at this dark share. Family 2 at ~11% is the union's 24.6% of light
    applied to a 44%-light league — a consequence, not a second defect."""
    fam_rng, dark_rng = published_family_ranges()
    rostered = [r for r in rows if r['cohort'] in ('spine', 'franchise')]
    c = collections.Counter(r['appearance'][0].replace('Head', '')[0] for r in rostered); t = len(rostered)
    dark = 100 * (c['4'] + c['5']) / t
    n_era, era = era_dark_share([r['name'] for r in rostered])
    bad = []
    if abs(dark - era) > 3.0: bad.append(f'dark {dark:.1f}% vs the era\'s own {era:.1f}% (1979-80 save, {n_era} of these men)')
    light = 100 - dark
    implied = {'1': light * 0.540, '2': light * 0.246, '3': light * 0.214, '4': dark * 0.378, '5': dark * 0.622}
    for f in '12345':
        share = 100 * c[f] / t
        if abs(share - implied[f]) > 3.0: bad.append(f'family {f} {share:.1f}% vs {implied[f]:.1f}% implied by the published within-band split at this dark share')
    return c, t, dark, fam_rng, dark_rng, bad, (n_era, era), implied

def conditional(rows, by, label):
    """Split the output by its SOURCE value; the groups must differ."""
    g = collections.defaultdict(list)
    for r in rows:
        k = by(r)
        if k is not None: g[k].append(r['band'])
    light = {k: 100 * sum(1 for b in v if b == 'light') / len(v) for k, v in g.items() if len(v) >= 20}
    return light

def selftest(ctx):
    ok = 0
    people = [p for p in cohorts() if p['cohort'] == 'spine']
    rows = []
    for p in people:
        app, src, ag, hs, band = player_face(p, ctx)
        rows.append(dict(p, appearance=app, skin_source=src, band=band))
    try:
        check_family_rules(rows, ctx['vocab']); ok += 1; print('  ok: family rules and vocabulary hold on the spine')
    except AssertionError as e:
        print(f'  FAIL family rules: {e}')
    try:
        light = conditional(rows, lambda r: {'light': 'archive light', 'dark': 'archive dark'}.get(archive_band(norm(r['name']), *ctx['archive'])[0]), 'archive')
        sep = light.get('archive light', 0) - light.get('archive dark', 100)
        assert sep > 40, light
        ok += 1; print(f'  ok: the conditional separates by archive band, {sep:+.0f} points')
    except AssertionError as e:
        print(f'  FAIL conditional: {e}')
    try:                                   # the 2007 bug: a generator that never read its source
        bad = []
        for p in people:
            app, src, ag, hs, band = player_face(p, ctx, disable_source=True)
            bad.append(dict(p, appearance=app, skin_source=src, band=band))
        light = conditional(bad, lambda r: {'light': 'archive light', 'dark': 'archive dark'}.get(archive_band(norm(r['name']), *ctx['archive'])[0]), 'archive')
        sep = light.get('archive light', 0) - light.get('archive dark', 100)
        assert sep <= 40, f'a source-blind generator passed the conditional at {sep:+.0f} — the test is vacuous'
        ok += 1; print(f'  ok: with the source disconnected the conditional FAILS ({sep:+.0f} points) — the check is not vacuous')
    except AssertionError as e:
        print(f'  FAIL negative: {e}')
    try:
        reg_rows = [r for r in rows if r['skin_source'] == 'registry-1986 family']
        assert all(r['appearance'][0].replace('Head', '')[0] == ctx['p86'][(norm(r['name']), r['pos'])][0].replace('Head', '')[0] for r in reg_rows)
        assert len(reg_rows) > 250, len(reg_rows)
        ok += 1; print(f'  ok: all {len(reg_rows)} registry-1986 men carry exactly the registry family')
    except AssertionError as e:
        print(f'  FAIL registry: {e}')
    return ok

def main():
    ctx = load_ctx()
    rows = []
    for p in cohorts():
        if p['cohort'] == 'staff':
            app, src = staff_face(p, ctx); ag, hs, band = (1.0 if src.startswith('registry') else 0.0), ('registry' if src.startswith('registry') else 'generated'), ('light' if app[0].replace('Head', '')[0] in '123' else 'dark')
        else:
            app, src, ag, hs, band = player_face(p, ctx)
        rows.append(dict(p, appearance=app, skin_source=src, skin_agreement=ag, hair_source=hs, band=band))
    check_family_rules(rows, ctx['vocab'])
    c, t, dark, fam_rng, dark_rng, bad, (n_era, era), implied = check_family_gate(rows)
    assert not bad, 'family gate failed: ' + '; '.join(bad)      # BEFORE the write, not after
    fh = open(repo('wip', 'faces_1979.csv'), 'w', newline='')
    # keyed on TEAM as well as cohort/name/position: Detroit's and New York's Gene
    # Washington are two receivers, and a key without team gave them one row.
    w = csv.writer(fh); w.writerow(['cohort', 'name', 'pos', 'team', 'appearance', 'skin_source', 'skin_agreement', 'hair_source', 'band'])
    for r in rows: w.writerow([r['cohort'], r['name'], r['pos'], r['team'], ' '.join(r['appearance']), r['skin_source'], f"{r['skin_agreement']:.2f}", r['hair_source'], r['band']])
    fh.close()
    print(f'wrote wip/faces_1979.csv: {len(rows)} people\n')
    print(f"{'cohort':<12}{'n':>6}{'registry':>10}{'archive':>9}{'NFL79':>7}{'prior':>7}{'  hair PHCL':>12}")
    for co in ['spine', 'franchise', 'fa_pool', 'draft_1980', 'draft_1981', 'draft_1982', 'draft_1983', 'staff']:
        v = [r for r in rows if r['cohort'] == co]; s = collections.Counter(r['skin_source'].split(' ')[0] for r in v)
        print(f"{co:<12}{len(v):>6}{s['registry-1986']+s['registry']:>10}{s['archive']:>9}{s['NFL79']:>7}{s['PSKI']+s['no']+s['generated']:>7}{sum(1 for r in v if r['hair_source'].startswith('PHCL')):>12}")
    print(f"\nhead family, rostered (spine + franchises, n={t}):")
    print(f"  {'':<10}{'this file':>10}{'era implies':>12}{'published 1986-2021':>22}")
    for f in '12345': print(f"  family {f}: {100*c[f]/t:>9.1f}%{implied[f]:>11.1f}%{fam_rng[f][0]:>13.1f}-{fam_rng[f][1]:.1f}")
    print(f"  dark:     {dark:>9.1f}%{era:>11.1f}%{dark_rng[0]:>13.1f}-{dark_rng[1]:.1f}   (era = 1979-80 save over {n_era} of these men)")
    print('  GATE (era-based): PASS')
    sp = [r for r in rows if r['cohort'] == 'spine']
    light = conditional(sp, lambda r: r['skin_source'].split(' (')[0] if r['skin_source'].startswith(('NFL79', 'archive', 'registry', 'PSKI', 'no')) else None, 'source')
    print('\nCONDITIONAL — light share by skin source (each group must differ from the others as the source says):')
    for k, v in sorted(light.items(), key=lambda kv: -kv[1]): print(f'  {k:<40}{v:5.1f}% light')
    n79 = ctx['n79']
    ps = conditional([r for r in sp if norm(r['name']) in n79], lambda r: f"PSKI {n79[norm(r['name'])]['PSKI']}", 'pski')
    print('  by NFL79 PSKI, all spine men the mod holds (archive decided most of them; the two must still agree in direction):')
    for k in sorted(ps): print(f'    {k:<10}{ps[k]:5.1f}% light')

def load_ctx():
    p86, s86, sm, later = load_registry()
    voc = vocab()
    pv = dict(head=by_family(voc, 0, 'Head'), eyes=by_family(voc, 1, 'Eyes'), hair=by_family(voc, 2, 'Hair'),
              beard=by_family(voc, 3, 'Beard'), eyebrows=by_family(voc, 4, 'Eyebrows'),
              nose=by_family(voc, 5, 'Nose'), mouth=by_family(voc, 6, 'Mouth'))
    for k, fams in (('hair', '12345'), ('beard', '12345'), ('eyebrows', '12345'), ('head', '12345'), ('nose', '12345'), ('mouth', '12345')):
        missing = [f for f in fams if not pv[k].get(f)]
        assert not missing, f'player vocabulary has no {k} tokens for family {missing}'
    return dict(archive=load_archive(), n79=load_ros('/tmp/n79/play.csv'), n76=load_ros('/tmp/n76/play.csv'),
                p86=p86, s86=s86, sm=sm, later=later, vocab=voc, pv=pv, staff_vocab=staff_vocab())

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest(load_ctx()) == 4 else 1)
    main()
