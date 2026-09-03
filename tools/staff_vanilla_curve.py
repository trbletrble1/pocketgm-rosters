#!/usr/bin/env python3
"""
staff_vanilla_curve — batch 3. Three changes to every staff file, from one
game-generated reference, ruled 2026-09-03.

  python3 tools/staff_vanilla_curve.py 2007 --dry-run
  python3 tools/staff_vanilla_curve.py 1979 1986 2000 2004 2007 2010 2013 2017 2021 2026

THE REFERENCE is the game's own staff export (three exports of one league; the
game ships a fixed staff, so n = 1 is all there is). Measured:

  headroom     median 7, p90 14, max 27, NOBODY locked — and UNCONDITIONAL:
               r(headroom, age) +0.02, r(headroom, rating) +0.02, flat across
               every age band and rating band. Ours: median 2, 12-68% locked.
  potential    runs 63-114. 24 of 432 sit ABOVE 99; the 98-rated head coaches
               carry 100-114. If the engine generates it, it reads it. Ours
               capped at 95-97 by a convention mistaken for the engine's.
  HC floor     every sitting head coach is 64+, with a ramp above it
               (64, 65, 65, 66, 66, 66, 66, 66, 67 ...). Ours: 58-61, 26 men
               across ten files.
  pool         16 per role, every one rated below the employed floor
               (HC 57-64, others 59-69). Ours: 16-33 per role, rated 32-95.

1. POTENTIAL. Every staff member draws his headroom from the reference's 432
   observed values, seeded on his identity. potential = rating + headroom, and it
   may exceed 99 exactly as the game's does. growthType rebuilt on the 50x rule,
   which is OURS — vanilla holds it exactly on 43 of 432, median ratio 0.95,
   range 0.24-1.98 — but sits inside the game's range and stays.

2. FLOOR. Sitting head coaches below 64 are rank-mapped onto the bottom of the
   reference's employed-HC ramp, not piled onto 64. rating == HCcoach on 100% of
   records in both vanilla and ours, so the lift sets both. Pat Dye (63, JAX,
   Ryan's own settlement) moves with the rest: the placement carries the story,
   not the number. Ruled.

3. POOL. SIZE AND FLOOR FROM VANILLA, COMPOSITION REAL. 16 per role. Generated
   filler below 57 is dropped first, then generated filler at 57+, weakest first.
   A named man is never dropped, and ratings are untouched — so 2007 keeps
   Cowher 90, Parcells 90 and Jimmy Johnson 86, who were genuinely available, and
   the pool reads 57-90 rather than the game's 57-64. ACCEPTED DIVERGENCE, same
   reasoning as the prospects: vanilla invents its pool, we have real men.
   Dropping the legends to hit a band would trade the best thing about these
   files for conformance with a generator.

   Real vs generated: a man is REAL if any real-coach source names him (the three
   coach CSVs in sources, or a sitting job on any team in any of the ten files),
   GENERATED if his forename and surname both come from the invented name lists
   and no source knows him, AMBIGUOUS otherwise — and ambiguous men are kept.

1979 HAS NO POOL: 288 records, 32 x 9. Potential and floor apply; the pool is
created in batch 4, which opens that file anyway.
"""
import json, os, sys, re, csv, glob, random, unicodedata, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

VAN = os.path.join(sources(), 'vanilla', 'PGMStaff_vanilla_2026-09-03.json')
ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams', 'Head Scout',
         'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio']
PRIM = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach', 'Def Co-ord': 'DCcoach',
        'Special Teams': 'STcoach', 'Head Scout': 'Hscout', 'Off Scout': 'Oscout',
        'Def Scout': 'Dscout', 'Head Physio': 'Hphysio', 'Assistant Physio': 'Aphysio'}
YEARS = ['1979', '1986', '2000', '2004', '2007', '2010', '2013', '2017', '2021', '2026']
POOL_SIZE = 16
FLOOR = 64

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z ]', '', s).split())

def build_growth(potential, rating, rng, n_slots=51):
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

def real_names():
    real = set()
    for fn in ('coach_birth_years.csv', 'coach_birth_years_2026.csv', 'coaches_2000.csv'):
        for r in csv.DictReader(open(os.path.join(sources(), fn))):
            real.add(norm(r['name']))
    for p in glob.glob(repo('wip', '*coach*.csv')):
        for r in csv.DictReader(open(p)):
            for k in ('name', 'coach'):
                if r.get(k): real.add(norm(r[k]))
    for y in YEARS:
        for x in json.load(open(repo(f'PGMStaff_{y}.json'))):
            if x['teamID'] != 'Free Agent':
                real.add(norm(x['forename'] + ' ' + x['surname']))
    return real

def classify(x, real, fore, sur):
    n = norm(x['forename'] + ' ' + x['surname'])
    if n in real: return 'real'
    if x['forename'] in fore and x['surname'] in sur: return 'generated'
    return 'ambiguous'

CANDIDATES = [
    ('compact ", ": "', lambda d: json.dumps(d, separators=(', ', ': '))),
    ('compact "," ":"', lambda d: json.dumps(d, separators=(',', ':'))),
    ('compact default', lambda d: json.dumps(d)),
    ('compact ", ": " raw-unicode', lambda d: json.dumps(d, separators=(', ', ': '), ensure_ascii=False)),
    ('compact "," ":" raw-unicode', lambda d: json.dumps(d, separators=(',', ':'), ensure_ascii=False)),
    ('compact default raw-unicode', lambda d: json.dumps(d, ensure_ascii=False)),
] + [(f'indent={i}', (lambda i: lambda d: json.dumps(d, indent=i))(i)) for i in (1, 2, 4)] \
  + [(f'indent={i} raw-unicode', (lambda i: lambda d: json.dumps(d, indent=i, ensure_ascii=False))(i)) for i in (1, 2, 4)]

def fmt_of(head):
    """Return (name, serialiser) for the ONE candidate that reproduces HEAD
    byte-for-byte, trailing newline included. Anything else is a format drift
    and the diff stops being a check."""
    for name, f in CANDIDATES:
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head:
                return name + (' +nl' if nl else ''), (lambda f, nl: lambda d: f(d) + nl)(f, nl)
    raise AssertionError('stored formatting not reproduced by any candidate: ' + repr(head[:80]))

def dump(d, head):
    return fmt_of(head)[1](d)

def run(y, dry, van, van_hc, real, fore, sur):
    import subprocess
    head = subprocess.run(['git', 'show', f'HEAD:PGMStaff_{y}.json'], capture_output=True, text=True, cwd=repo('')).stdout
    fmt_name, _ = fmt_of(head)   # raises if no candidate reproduces HEAD
    d = json.load(open(repo(f'PGMStaff_{y}.json')))
    hd = [x['potential'] - x['rating'] for x in van]
    print(f'=== {y} ===  {len(d)} records')

    # ---- 2. FLOOR first, so potential draws on the lifted rating
    low = sorted([x for x in d if x['role'] == 'Head Coach' and x['teamID'] != 'Free Agent' and x['rating'] < FLOOR],
                 key=lambda x: (x['rating'], x['surname']))
    ramp = van_hc[:len(low)]
    for x, r in zip(low, ramp):
        print(f"  floor  {x['surname']:<14} {x['teamID']:<4} {x['rating']} -> {r}")
        x['rating'] = x[PRIM['Head Coach']] = r
    assert all(x['rating'] == x[PRIM[x['role']]] for x in d), 'rating != primary attribute'

    # ---- 1. POTENTIAL from the game's curve
    hb = [x['potential'] - x['rating'] for x in d]
    for x in d:
        rng = random.Random(f"{x['iden']}|{y}|staffpot")
        h = rng.choice(hd)
        # the game's observed ceiling is 114 (rating 99 + a wide draw); the gate
        # checks 63-114, so a draw that would pass it is trimmed to it
        h = min(h, 114 - x['rating'])
        x['potential'] = x['rating'] + h
        x['growthType'] = build_growth(x['potential'], x['rating'], random.Random(f"{x['iden']}|{y}|staffgt"), 51)
        assert len(x['growthType']) == 51 and sum(v for v in x['growthType'] if v > 0) == h * 50
    ha = [x['potential'] - x['rating'] for x in d]
    print(f"  headroom  med {st.median(hb):.0f} -> {st.median(ha):.0f}   p90 {sorted(hb)[int(len(hb)*.9)]} -> {sorted(ha)[int(len(ha)*.9)]}   "
          f"max {max(hb)} -> {max(ha)}   locked {sum(1 for v in hb if v == 0)/len(hb):.0%} -> {sum(1 for v in ha if v == 0)/len(ha):.0%}   (vanilla 7 / 14 / 27 / 0%)")
    print(f"  potential max {max(x['potential'] for x in d)}, above 99: {sum(1 for x in d if x['potential'] > 99)}   (vanilla 114, 24)")

    # ---- 3. POOL
    fa = [x for x in d if x['teamID'] == 'Free Agent']
    if not fa:
        print('  pool   NONE — 1979 carries no free-agent staff; created in batch 4')
    dropped = []
    cls_all = {id(x): classify(x, real, fore, sur) for x in fa}
    for role in ROLES:
        men = [x for x in fa if x['role'] == role]
        if not men: continue
        cls = {id(x): classify(x, real, fore, sur) for x in men}
        # AMBIGUITY RESOLVES AT THE LEVEL OF THE SET, NOT THE NAME. Ruled
        # 2026-09-03. 2017's head-coach pool held five Hoffmans, three Vances,
        # two Osbornes, two Sullivans and two Lockharts, none of whom had ever
        # held any role on any team in any of the ten files. Individually each
        # was ambiguous; collectively they were a name generator drawing on a
        # small surname pool, and no researched list of real coaches looks like
        # that. Jim Mora Sr. (2007) and Douglas Henderson (2004) are ambiguous
        # individually — one name each, no pattern — and stay kept. So: an
        # ambiguous man whose surname is shared with another non-real man in the
        # same file's pool is generated.
        surn = collections.Counter(x['surname'] for x in fa if cls_all[id(x)] != 'real')
        for x in men:
            if cls[id(x)] == 'ambiguous' and surn[x['surname']] >= 2:
                cls[id(x)] = 'generated'
        gen_low = sorted([x for x in men if cls[id(x)] == 'generated' and x['rating'] < 57], key=lambda x: x['rating'])
        gen_hi = sorted([x for x in men if cls[id(x)] == 'generated' and x['rating'] >= 57], key=lambda x: x['rating'])
        keep = list(men)
        for pile in (gen_low, gen_hi):
            for x in pile:
                if len(keep) <= POOL_SIZE: break
                keep.remove(x); dropped.append(x)
        kept_r = sorted(x['rating'] for x in keep)
        c = collections.Counter(cls[id(x)] for x in keep)
        tag = '' if len(keep) <= POOL_SIZE else f'   OVER by {len(keep)-POOL_SIZE}: no generated man left to drop'
        amb = [x['forename'] + ' ' + x['surname'] + f" {x['rating']}" for x in keep if cls[id(x)] == 'ambiguous' and x['rating'] < 57]
        print(f"  pool   {role:<17} {len(men):>2} -> {len(keep):>2}   {kept_r[0]}-{kept_r[-1]}   real {c['real']:>2} gen {c['generated']:>2} amb {c['ambiguous']:>2}{tag}"
              + (f"   ambiguous<57 kept: {', '.join(amb)}" if amb else ''))
    d = [x for x in d if x not in dropped]
    if dropped:
        print(f"  dropped {len(dropped)} generated men, ratings {min(x['rating'] for x in dropped)}-{max(x['rating'] for x in dropped)}")

    if dry:
        print('  --dry-run: nothing written\n'); return
    open(repo(f'PGMStaff_{y}.json'), 'w').write(dump(d, head))
    print(f'  wrote PGMStaff_{y}.json  ({fmt_name})\n')

def main():
    years = [a for a in sys.argv[1:] if a in YEARS]
    dry = '--dry-run' in sys.argv
    assert years
    van = json.load(open(VAN))
    van_hc = sorted(x['rating'] for x in van if x['role'] == 'Head Coach' and x['teamID'] != 'Free Agent')
    assert van_hc[0] == FLOOR
    pool = json.load(open(repo('wip', 'staff_name_pool.json')))
    fore, sur = set(pool['forenames']), set(pool['surnames'])
    real = real_names()
    print(f'reference: {len(van)} staff, headroom median {st.median(x["potential"]-x["rating"] for x in van):.0f}, HC ramp {van_hc[:9]}; real-name union {len(real)}\n')
    for y in years:
        run(y, dry, van, van_hc, real, fore, sur)

if __name__ == '__main__':
    main()
