#!/usr/bin/env python3
"""
fix_1979_roster — batch 4, roster side. Ruled 2026-09-03.

  python3 tools/fix_1979_roster.py --dry-run
  python3 tools/fix_1979_roster.py

1. WILLIE BROWN is a Hall of Fame cornerback and was labelled S. Relabelled CB;
   attributes untouched (he is 37 and his coverage numbers are his own).
2. THIN POSITIONS came from the franchise builder's SCARCE list, which reserves
   no OT or S and one MLB. Four signings from the free-agent pool: the best OT
   to JAX and TEN, the best S to JAX, the best MLB to IND. Four original teams at
   one centre are source data with a different signature and are left alone.
3. KICKERS. Not inflation — 1979's K/P scale matches vanilla's — but placement:
   the scarce pass handed each franchise the BEST available kicker and the four
   absorbed every kicker in the pool. Jim Bakken (37, retired after 1978) takes
   the age-forward decline the 47 unrated men took, 33-45: -8, so 90 -> 82.
   Tom Jurich (22, 1978 tenth-rounder, wAV -1) was one of 22 young unrated men
   ranked BY AGE ALONE onto the prospect band and came out second of 22 at 74;
   he is re-estimated from his outcome, the worst of the 22, at the band's low
   end. The other 21 carry the same age-only ranking and are flagged, not moved.
4. DRAFT NUMBERS from the twenty PFR listings 1960-1979: a unique name match, or
   an ambiguous one resolved by draft year (1979 - years pro, +-1). Undrafted men
   stay at 224. Pre-1977 drafts ran to pick 487; the real number is written and
   FLAGGED UNVERIFIED against the engine — 1986 and 2000 already carry 420 and
   336 with no known harm.
5. EXTENSION TERMS (item 41's 1979 half). Every man had eSalary == salary, so
   every extension was free. Drawn from vanilla's joint distribution by
   (length, rating band): the ratio eSalary/salary at a seeded quantile, eLength
   from the cell's own distribution, eGuarantee/eSalary likewise. Vanilla's
   shape: median 1.00, 3-year men ask 1.72x, the 50s-rated ask 0.65x.

Formatting: 1979's roster is stored at indent 1 and is written back the same way.
"""
import json, csv, os, sys, re, random, unicodedata, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

VAN = os.path.join(sources(), 'vanilla', 'PGMRoster_vanilla_2026-09-03.json')
SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
KW = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', '', s).split() if w not in SUF)

def rating_of(x):
    names, w = KW[x['position']]
    return int(round(sum(x[a] * c for a, c in zip(names, w[:-1])) + w[-1]))

def band(r): return '<60' if r < 60 else '60s' if r < 70 else '70s' if r < 80 else '80+'

def build_growth(potential, rating, rng, n_slots=31):
    gt = [0] * n_slots
    need = (potential - rating) * 50
    if need > 0:
        slots = rng.sample(range(0, 20), min(8, max(1, need // 100 or 1)))
        per = need // len(slots)
        for i, s in enumerate(slots):
            gt[s] = per if i else need - per * (len(slots) - 1)
    for s in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))):
        gt[s] = -100 * rng.randint(1, 3)
    return gt

def main():
    dry = '--dry-run' in sys.argv
    head = subprocess.run(['git', 'show', 'HEAD:PGMRoster_1979.json'], capture_output=True, text=True, cwd=repo('')).stdout
    assert json.dumps(json.loads(head), indent=1) + ('\n' if head.endswith('\n') else '') == head, 'stored formatting not reproduced'
    d = json.load(open(repo('PGMRoster_1979.json')))
    by_name = {norm(x['forename'] + ' ' + x['surname']): x for x in d}
    rostered = lambda: [x for x in d if x['teamID'] not in ('Rookie', 'Free Agent')]
    pool = lambda: [x for x in d if x['teamID'] == 'Free Agent']
    log = []

    # 1. Willie Brown
    wb = by_name['willie brown']; assert wb['position'] == 'S' and wb['teamID'] == 'IND'
    wb['position'] = 'CB'; log.append(f"Willie Brown S -> CB (IND, {wb['rating']}, age {wb['age']})")

    # 2. four signings from the pool
    def sign(team, pos, exclude=()):
        c = sorted([x for x in pool() if x['position'] == pos and x['iden'] not in exclude], key=lambda x: (-x['rating'], x['age']))[0]
        team_pos = [z for z in rostered() if z['teamID'] == team and z['position'] == pos]
        ref = sorted(rostered(), key=lambda z: z['salary'])
        # a pool signing takes the team's median contract at his position, one year
        med = st.median(z['salary'] for z in rostered() if z['position'] == pos)
        c['teamID'] = team; c['salary'] = int(med); c['guarantee'] = int(med * 0.06); c['length'] = 1
        used = {z['teamNum'] for z in rostered() if z['teamID'] == team}
        c['teamNum'] = next(n for n in range(1, 100) if n not in used)   # a pool man carries 0; the gate refuses duplicates
        log.append(f"signed {c['forename']} {c['surname']} {pos} {c['rating']} age {c['age']} -> {team} (had {len(team_pos)}) at ${med/1e6:.2f}M/1y")
        return c['iden']
    a = sign('JAX', 'OT'); sign('TEN', 'OT', exclude=(a,)); sign('JAX', 'S'); sign('IND', 'MLB')

    # 3. kickers
    bk = by_name['jim bakken']; assert bk['rating'] == 90 and bk['position'] == 'K'
    target = 82; before = bk['rating']
    names, w = KW['K']; fixed = sum(bk[a] * c for a, c in zip(names, w[:-1]) if a not in ('kickAccuracy', 'power')) + w[-1]
    ka, pw = bk['kickAccuracy'], bk['power']
    # take the eight points off accuracy and power in proportion to their weight
    for _ in range(200):
        if rating_of(bk) <= target: break
        bk['kickAccuracy'] -= 1
        if rating_of(bk) > target: bk['power'] -= 1
    bk['potential'] = max(bk['potential'] - (before - bk['rating']) if False else bk['rating'], bk['rating'])
    bk['rating'] = rating_of(bk); bk['potential'] = bk['rating']
    bk['growthType'] = build_growth(bk['potential'], bk['rating'], random.Random('bakken|1979|gt'), 31)
    log.append(f"Bakken {before} -> {bk['rating']} (kickAccuracy {ka} -> {bk['kickAccuracy']}, power {pw} -> {bk['power']}); age-forward 33-45: -8")

    tj = by_name['tom jurich']; assert tj['rating'] == 74
    # the prospect band the 22 young men were mapped onto, and his place on it by OUTCOME
    prat = sorted(x['rating'] for y in ('2013', '2017', '2021', '2026') for x in json.load(open(repo(f'PGMRoster_{y}.json'))) if x['teamID'] == 'Rookie')
    q = (0 + 0.5) / 22                                    # worst outcome of 22 -> lowest plotting position
    new = prat[min(len(prat) - 1, int(round(q * (len(prat) - 1))))]
    hd = tj['potential'] - tj['rating']; before = tj['rating']
    # move the K attributes so the linear rating lands on the band value
    for _ in range(400):
        if rating_of(tj) <= new: break
        tj['kickAccuracy'] -= 1
        if rating_of(tj) > new: tj['power'] -= 1
    tj['rating'] = rating_of(tj); tj['potential'] = tj['rating'] + hd
    tj['growthType'] = build_growth(tj['potential'], tj['rating'], random.Random('jurich|1979|gt'), 31)
    log.append(f"Jurich {before} -> {tj['rating']} (potential {tj['potential']}), the prospect band at the worst outcome of 22 (wAV -1)")

    # 4. draft numbers
    idx = collections.defaultdict(list)
    for y in range(1960, 1980):
        for r in csv.DictReader(open(repo('wip', f'draft_{y}_pfr.csv'))):
            idx[norm(r['name'])].append((y, int(r['pick'])))
    set_, over224, amb_unres, undrafted = 0, 0, 0, 0
    for x in rostered():
        c = idx.get(norm(x['forename'] + ' ' + x['surname']), [])
        expect = 1979 - (2026 - x['draftSeason'])
        near = [t for t in c if abs(t[0] - expect) <= 1]
        pick = c[0][1] if len(c) == 1 else near[0][1] if len(near) == 1 else None
        if pick is None:
            (undrafted if not c else amb_unres.__class__) and None
            if c: amb_unres += 1
            else: undrafted += 1
            continue
        x['draftNum'] = pick; set_ += 1; over224 += pick > 224
    log.append(f"draftNum set on {set_} rostered men ({over224} above 224, UNVERIFIED against the engine); {undrafted} not in any 1960-79 listing stay 224; {amb_unres} ambiguous and unresolved stay 224")

    # 5. extension terms from vanilla's joint table
    van = [x for x in json.load(open(VAN)) if x['teamID'] not in ('Rookie', 'Free Agent') and x['salary'] > 0]
    cell = collections.defaultdict(lambda: {'ratio': [], 'elen': [], 'eg': []})
    for x in van:
        k = (x['length'], band(x['rating'])); c = cell[k]
        c['ratio'].append(x['eSalary'] / x['salary']); c['elen'].append(x['eLength']); c['eg'].append(x['eGuarantee'] / x['eSalary'] if x['eSalary'] else 0)
    def draw(x):
        k = (x['length'], band(x['rating']))
        if len(cell[k]['ratio']) < 20:
            k = min((kk for kk in cell if len(cell[kk]['ratio']) >= 20), key=lambda kk: (abs(kk[0] - x['length']), kk[1] != band(x['rating'])))
        c = cell[k]; rng = random.Random(f"{x['iden']}|1979|ext")
        ratio = sorted(c['ratio'])[min(len(c['ratio']) - 1, int(rng.random() * len(c['ratio'])))]
        return ratio, rng.choice(c['elen']), rng.choice(c['eg'])
    n = 0; vmax_s = max(x['eSalary'] for x in van); vmax_g = max(x['eGuarantee'] for x in van); clamped = 0
    for x in rostered():
        if x['salary'] <= 0: continue
        ratio, el, eg = draw(x)
        es = int(round(x['salary'] * ratio)); egv = int(round(es * eg))
        if es > vmax_s or egv > vmax_g: clamped += 1
        x['eSalary'] = min(es, vmax_s); x['eLength'] = el; x['eGuarantee'] = min(egv, vmax_g); n += 1
    log.append(f"extension money clamped to vanilla's maxima (eSalary ${vmax_s/1e6:.1f}M, eGuarantee ${vmax_g/1e6:.1f}M) on {clamped} men")
    r = rostered(); v = [x['eSalary'] / x['salary'] for x in r if x['salary'] > 0]
    log.append(f"extension terms drawn on {n}: eSalary/salary median {st.median(v):.2f}, want a raise {sum(1 for q in v if q > 1.05)/len(v):.0%}, want less {sum(1 for q in v if q < 0.95)/len(v):.0%} (vanilla 1.00 / 27% / 22%); eLength differs from length on {sum(1 for x in r if x['eLength'] != x['length'])/len(r):.0%} (vanilla 72%)")

    for line in log: print('  ' + line)
    # thin-position check after
    cnt = collections.defaultdict(collections.Counter)
    for x in rostered(): cnt[x['teamID']][x['position']] += 1
    print('  after: JAX OT', cnt['JAX']['OT'], 'TEN OT', cnt['TEN']['OT'], 'JAX S', cnt['JAX']['S'], 'IND MLB', cnt['IND']['MLB'])
    for t in ('IND', 'JAX'):
        top = sorted([x for x in rostered() if x['teamID'] == t], key=lambda x: -x['rating'])[:4]
        print(f"  {t} top four now: " + ', '.join(f"{x['surname']} {x['position']} {x['rating']}" for x in top))
    for x in d:
        assert sum(v for v in x['growthType'] if v > 0) == (x['potential'] - x['rating']) * 50, x['surname']
    if dry:
        print('  --dry-run: nothing written'); return
    open(repo('PGMRoster_1979.json'), 'w').write(json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else ''))
    print('  wrote PGMRoster_1979.json (indent 1)')

if __name__ == '__main__':
    main()
