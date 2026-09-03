#!/usr/bin/env python3
"""
fix_1979_staff — batch 4, staff side. Ruled 2026-09-03.

  python3 tools/fix_1979_staff.py --dry-run
  python3 tools/fix_1979_staff.py

1. COACH HAIR. The staff builder drew hair without conditioning on anything.
   The game's rule, measured on its own 432 staff, is AGE FIRST, THEN FAMILY:
   at 45 and over, grey (Hair6) in 340 of 348 regardless of head family; under
   45, Head3/4/5 are black (Hair1) in 54 of 54 and Head1/2 mix Hair2-5. Every
   1979 staff member redraws hair from that (family x age band) table, seeded on
   his identity, with beard and eyebrows following the hair family as the
   player builder does. Men who also sit in a later file take THAT file's hair instead (the
   registry makes the later file canonical), so the faces gate's 'hair constant
   across seasons' does not get worse.

2. HEAD-COACH POOL, real. 1979 shipped with no free-agent staff at all (288 =
   32 x 9). wip/coach_pool_1979.csv holds 99 real head coaches with careers;
   8 are already sitting; the other 91 join as free agents — ALL of them, by
   the batch-3 rule that a named man is never dropped (1986 keeps 20 for the
   same reason). Faces: 4 already carry one in 1986 (Bill Johnson, Modzelewski,
   Ringo, Sandusky) and take it; the rest have NO SOURCED SKIN and draw a head
   family from the game's staff distribution — written to
   wip/staff_pool_1979_faces_unsourced.csv so a later pass can verify them.
   Six have no age in the source and take 1979 - first year coached + 30.

3. THE OTHER EIGHT ROLES have no source and are generated, 16 each, on the
   game's own pool profile per role (ratings 57-69, ages 34-71, no contract),
   with invented names checked against every real coach name in the archive.

Every pool man's potential draws from the game's staff headroom (batch 3),
growthType on the 50x rule, teamID 'Free Agent', salary and length 0 as the
game's pool carries. Attributes clone the nearest-rated sitting man of the role
and then take the man's own rating as the primary.
"""
import json, csv, os, sys, re, random, unicodedata, collections, statistics as st, subprocess, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

VS = os.path.join(sources(), 'vanilla', 'PGMStaff_vanilla_2026-09-03.json')
ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams', 'Head Scout', 'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio']
PRIM = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach', 'Def Co-ord': 'DCcoach', 'Special Teams': 'STcoach',
        'Head Scout': 'Hscout', 'Off Scout': 'Oscout', 'Def Scout': 'Dscout', 'Head Physio': 'Hphysio', 'Assistant Physio': 'Aphysio'}
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z ]', '', s).split())
fam = lambda a: re.match(r'Head(\d+)', a[0]).group(1)
def ageband(a): return '<45' if a < 45 else '45-59' if a < 60 else '60+'

def build_growth(potential, rating, rng, n_slots=51):
    gt = [0] * n_slots; need = (potential - rating) * 50
    if need > 0:
        slots = rng.sample(range(0, 20), min(8, max(1, need // 100 or 1))); per = need // len(slots)
        for i, s in enumerate(slots): gt[s] = per if i else need - per * (len(slots) - 1)
    for s in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))): gt[s] = -100 * rng.randint(1, 3)
    return gt

CANDS = [lambda d: json.dumps(d, separators=(', ', ': ')), lambda d: json.dumps(d, separators=(',', ':')),
         lambda d: json.dumps(d, separators=(',', ':'), ensure_ascii=False), lambda d: json.dumps(d),
         lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, indent=2)]
def serialiser(head):
    for f in CANDS:
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head: return (lambda f, nl: lambda d: f(d) + nl)(f, nl)
    raise AssertionError('stored formatting not reproduced')

def main():
    dry = '--dry-run' in sys.argv
    no_pool = '--no-pool' in sys.argv   # hair only; the pool is HELD until its 87 unsourced faces are ruled on
    van = json.load(open(VS)); vhd = [x['potential'] - x['rating'] for x in van]
    vocab = json.load(open(repo('reference', 'PGM3_SCHEMA_REFERENCE.json')))['appearance_vocab_by_slot']
    hair_tab = collections.defaultdict(list)
    for x in van: hair_tab[(fam(x['appearance']), ageband(x['age']))].append([q for q in x['appearance'] if q.startswith('Hair')][0][4])
    vfam = [fam(x['appearance']) for x in van]
    def redraw_hair(x, seed):
        rng = random.Random(seed); f = fam(x['appearance'])
        h = rng.choice(hair_tab[(f, ageband(x['age']))])
        pick = lambda slot, pre: rng.choice([t for t in vocab[slot] if t.startswith(pre + h)] or vocab[slot])
        a = list(x['appearance']); a[2] = pick('2', 'Hair'); a[3] = pick('3', 'Beard'); a[4] = pick('4', 'Eyebrows')
        x['appearance'] = a; return h

    files = {}
    for y in ('1979',):
        head = subprocess.run(['git', 'show', f'HEAD:PGMStaff_{y}.json'], capture_output=True, text=True, cwd=repo('')).stdout
        files[y] = (json.load(open(repo(f'PGMStaff_{y}.json'))), serialiser(head))
    s79 = files['1979'][0]
    s79[:] = [x for x in s79 if x['teamID'] != 'Free Agent']   # rebuild the pool from the sitting 288; the generated men are seeded and come back identical

    # 1. hair
    before = collections.Counter(); after = collections.Counter()
    for x in s79:
        before[[q for q in x['appearance'] if q.startswith('Hair')][0][4]] += 1
        h = redraw_hair(x, f"{x['iden']}|1979|hair"); after[h] += 1
    grey45 = sum(1 for x in s79 if x['age'] >= 45 and x['appearance'][2].startswith('Hair6')); n45 = sum(1 for x in s79 if x['age'] >= 45)
    print(f"1. hair: family counts {dict(sorted(before.items()))} -> {dict(sorted(after.items()))}; staff 45+ now grey {grey45}/{n45} (vanilla 340/348)")
    # MULTI-SEASON MEN TAKE THE LATER FILE'S HAIR, not the other way round. The
    # registry's rule is one canonical face per person with the later published
    # files as the priority, and the faces gate holds hair constant across
    # seasons (only the age variant may move). Pushing 1979's age-conditioned
    # grey OUT onto 1986 and 2000 made the gate worse — 38 -> 42 differing —
    # because a 1979 coach can sit in any of the nine later files. So: for every
    # 1979 man found elsewhere, 1979 copies that face's hair, beard and eyebrows.
    canon = {}
    for y in ('1986', '2000', '2004', '2007', '2010', '2013', '2017', '2021', '2026'):
        for x in json.load(open(repo(f'PGMStaff_{y}.json'))):
            canon.setdefault(norm(x['forename'] + ' ' + x['surname']), (y, x['appearance']))
    took = collections.Counter()
    for x in s79:
        c = canon.get(norm(x['forename'] + ' ' + x['surname']))
        if c is None: continue
        y, app = c
        if fam(app) == fam(x['appearance']):
            a = list(x['appearance']); a[2], a[3], a[4] = app[2], app[3], app[4]; x['appearance'] = a; took[y] += 1
        else:
            took['skipped: head family differs'] += 1
    print(f"   multi-season men: 1979 took the later file's hair for {sum(v for k, v in took.items() if not k.startswith('skipped'))} — {dict(took)}")
    if no_pool:
        print('  --no-pool: the head-coach pool and the eight generated roles are HELD (87 of 91 real men have no sourced skin)')
        if dry: print('  --dry-run: nothing written'); return
        for y, (d, ser) in files.items(): open(repo(f'PGMStaff_{y}.json'), 'w').write(ser(d))
        print('  wrote PGMStaff_1979.json (hair only)'); return
    # 2. real head-coach pool
    sitting = {norm(x['forename'] + ' ' + x['surname']) for x in s79}
    pool_rows = [r for r in csv.DictReader(open(repo('wip', 'coach_pool_1979.csv'))) if norm(r['name']) not in sitting]
    later = {k: v[1] for k, v in canon.items()}
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json')))
    regf = {}
    for k in ('staff_faces', 'staff_faces_1986'):
        for nk, v in (reg.get(k) or {}).items(): regf.setdefault(norm(nk.split('|')[0]), v.get('appearance', v) if isinstance(v, dict) else v)
    # ERA COCH TABLES reach four of the 87 (Fairbanks and Lemm in 1979-SB-XIV, Bettis
    # and Hollway in 1983-SB-XVIII); the mods renamed only head coaches and a few
    # coordinators over stock Madden 08, so the rest of the pool is unreachable.
    # CSKI is the same 0-4 skin scale the player builder reads from PSKI.
    # CSKI reads as the player builder reads PSKI: 0 -> the light band, 2/3 -> the
    # dark band, 1 -> bimodal, abstain. Wally Lemm is CSKI 1 and so is NOT sourced.
    COCH_SKIN = {'chuck fairbanks': '0', 'tom bettis': '0', 'bob hollway': '0'}
    LIGHT_BAND = [('1', 0.540), ('2', 0.246), ('3', 0.214)]; DARK_BAND = [('4', 0.378), ('5', 0.622)]
    ABSTAIN_BAND = [('1', 0.20), ('2', 0.09), ('3', 0.02), ('4', 0.16), ('5', 0.53)]   # build_1979_faces' league prior
    def skin_fam(rng, k):
        band = LIGHT_BAND if k == '0' else DARK_BAND; r = rng.random(); acc = 0
        for f, w in band:
            acc += w
            if r <= acc: return f
        return band[-1][0]
    hc_templates = sorted([x for x in s79 if x['role'] == 'Head Coach'], key=lambda x: x['rating'])
    def clone(role, rating):
        ts = sorted([x for x in s79 if x['role'] == role], key=lambda x: abs(x['rating'] - rating))
        return json.loads(json.dumps(ts[0]))
    new, unsourced, aged = [], [], 0
    for r in pool_rows:
        rating = int(r['rating']); first = int(r['first'])
        age = int(r['age_1979']) if r['age_1979'].strip().isdigit() else 1979 - first + 30
        if not r['age_1979'].strip().isdigit(): aged += 1
        x = clone('Head Coach', rating)
        x['forename'], x['surname'] = r['name'].split()[0], ' '.join(r['name'].split()[1:])
        x['rating'] = x['HCcoach'] = rating; x['age'] = age; x['teamID'] = 'Free Agent'
        for k in ('salary', 'guarantee', 'eSalary', 'eGuarantee', 'length', 'eLength'): x[k] = 0
        x['startSeason'] = max(1989, 2026 - (1979 - first)); x['iden'] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'1979|pool|{r["name"]}')).upper()
        nk = norm(r['name'])
        if nk in regf and isinstance(regf[nk], list): x['appearance'] = list(regf[nk]); src = 'registry'
        elif nk in later: x['appearance'] = list(later[nk]); src = 'later file'
        elif nk in COCH_SKIN:
            rng = random.Random(f'{nk}|1979|face'); f = skin_fam(rng, COCH_SKIN[nk])
            a = list(x['appearance']); a[0] = rng.choice([t for t in vocab['0'] if t.startswith('Head' + f)])
            a[5] = rng.choice([t for t in vocab['5'] if t.startswith('Nose' + f)] or vocab['5']); a[6] = rng.choice([t for t in vocab['6'] if t.startswith('Mouth' + f)] or vocab['6'])
            x['appearance'] = a; src = 'COCH skin'
        else:
            # NO SOURCED SKIN -> ASSIGNED, the same machinery every other coach and
            # player gets. The hold on these men (twice) rested on a principle the
            # project does not have: the rule is NO INVENTED HUMANS, never "no
            # assigned appearance for a real person" — the registry votes across
            # sources and assigns where coverage is thin, which is most of every
            # historical file. Reversed 2026-09-03. Head family from the league
            # prior the player builder uses when no source speaks (ABSTAIN_BAND),
            # hair by the game's age-then-family rule; listed for later sourcing.
            rng = random.Random(f'{nk}|1979|face'); r_ = rng.random(); acc = 0; f = '5'
            for fam_, w_ in ABSTAIN_BAND:
                acc += w_
                if r_ <= acc: f = fam_; break
            a = list(x['appearance']); a[0] = rng.choice([t for t in vocab['0'] if t.startswith('Head' + f)])
            a[5] = rng.choice([t for t in vocab['5'] if t.startswith('Nose' + f)] or vocab['5']); a[6] = rng.choice([t for t in vocab['6'] if t.startswith('Mouth' + f)] or vocab['6'])
            x['appearance'] = a; src = 'ASSIGNED (league prior)'; unsourced.append((r['name'], age, rating, f))
        if src not in ('later file', 'registry'): redraw_hair(x, f"{x['iden']}|1979|hair")   # a sourced face is canonical, hair included
        h = min(random.Random(f"{x['iden']}|1979|staffpot").choice(vhd), 114 - rating)
        x['potential'] = rating + h; x['growthType'] = build_growth(x['potential'], rating, random.Random(f"{x['iden']}|1979|gt"))
        new.append(x)
    hr = sorted(x['rating'] for x in new)
    print(f"2. head-coach pool: {len(new)} real men — faces from a later file {sum(1 for x in new if norm(x['forename']+' '+x['surname']) in later)}, era COCH skin {sum(1 for x in new if norm(x['forename']+' '+x['surname']) in COCH_SKIN)}, ASSIGNED from the league prior {len(unsourced)} (listed in wip/staff_pool_1979_faces_unsourced.csv for later sourcing); ratings {hr[0]}-{st.median(hr):.0f}-{hr[-1]}")
    csv.writer(open(repo('wip', 'staff_pool_1979_faces_unsourced.csv'), 'w', newline='')).writerows([['name', 'age', 'rating', 'left_out']] + [list(u[:3]) + [f'assigned from the league prior (Head{u[3]}); not in registry, no later file, no era COCH skin'] for u in unsourced])

    # 3. eight generated roles
    names = json.load(open(repo('wip', 'staff_name_pool.json'))); real = {norm(n) for n in names['real_coach_names']} | sitting | {norm(x['forename'] + ' ' + x['surname']) for x in new} | set(canon)   # canon: every staff name in every later file — a generated man must not collide with one (Rakim Barrett did, with a 2000 physio)
    vpool = collections.defaultdict(list)
    for x in van:
        if x['teamID'] == 'Free Agent': vpool[x['role']].append((x['rating'], x['age'], x['startSeason']))
    used = set()
    for role in ROLES[1:]:
        for i in range(16):
            rng = random.Random(f'1979|gen|{role}|{i}')
            for _ in range(1000):
                nm = f"{rng.choice(names['forenames'])} {rng.choice(names['surnames'])}"
                if norm(nm) not in real and norm(nm) not in used: break
            used.add(norm(nm))
            rating, age, ss = rng.choice(vpool[role])
            x = clone(role, rating)
            x['forename'], x['surname'] = nm.split()[0], ' '.join(nm.split()[1:])
            x['rating'] = x[PRIM[role]] = rating; x['age'] = age; x['teamID'] = 'Free Agent'; x['startSeason'] = ss
            for k in ('salary', 'guarantee', 'eSalary', 'eGuarantee', 'length', 'eLength'): x[k] = 0
            x['iden'] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'1979|gen|{role}|{i}')).upper()
            f = rng.choice(vfam); a = list(x['appearance']); a[0] = rng.choice([t for t in vocab['0'] if t.startswith('Head' + f)])
            a[5] = rng.choice([t for t in vocab['5'] if t.startswith('Nose' + f)] or vocab['5']); a[6] = rng.choice([t for t in vocab['6'] if t.startswith('Mouth' + f)] or vocab['6']); x['appearance'] = a
            redraw_hair(x, f"{x['iden']}|1979|hair")
            h = min(rng.choice(vhd), 114 - rating); x['potential'] = rating + h; x['growthType'] = build_growth(x['potential'], rating, random.Random(f"{x['iden']}|1979|gt"))
            new.append(x)
    print(f"3. generated pool: {len(new) - sum(1 for x in new if x['role'] == 'Head Coach')} men across eight roles, on the game's per-role pool profile")
    s79.extend(new)
    for x in s79:
        assert x['rating'] == x[PRIM[x['role']]] and len(x['growthType']) == 51 and sum(v for v in x['growthType'] if v > 0) == (x['potential'] - x['rating']) * 50, x['surname']
    c = collections.Counter(x['role'] for x in s79 if x['teamID'] == 'Free Agent')
    print(f"   file: {len(s79)} records; pool by role {dict(c)}")
    if dry:
        print('  --dry-run: nothing written'); return
    for y, (d, ser) in files.items():
        open(repo(f'PGMStaff_{y}.json'), 'w').write(ser(d))
    print('  wrote PGMStaff_1979.json')

if __name__ == '__main__':
    main()
