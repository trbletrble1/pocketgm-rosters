#!/usr/bin/env python3
"""
fix_1979_young — item 46. The 22 young unrated men, ranked by OUTCOME.

  python3 tools/fix_1979_young.py --dry-run
  python3 tools/fix_1979_young.py

build_1979_unrated mapped the 22 young men with no NFL career onto the
published prospect band ORDERED BY AGE — 22 ahead of 25 — "because age is the
only signal these men carry". It is not: all 22 join a 1976-79 PFR listing and
carry wAV, and it is -1 to 4 for every one of them. Tom Jurich (wAV -1) was
ruled down to the band's low end in batch 4; Willie Taylor (wAV 0) still read 77
as Jacksonville's best player on the age-only ranking. Same signature, 21 men.

Now: rank the 22 by outcome (wAV, then seasons, then age as the last tiebreak)
and map that rank onto the same prospect band with the same plotting position
the rest of the build uses, (i+0.5)/n. Attributes move with the rating: every
live attribute is scaled by the same factor so the man's SHAPE is kept and his
LEVEL lands on the band, then the primary is nudged until the linear rating
formula reads the band value exactly. Potential keeps each man's headroom.
"""
import json, csv, os, sys, re, random, unicodedata, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
KW = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']
SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', '', s).split() if w not in SUF)
def rating_of(x):
    names, w = KW[x['position']]
    return int(round(sum(x[a] * c for a, c in zip(names, w[:-1])) + w[-1]))
def build_growth(potential, rating, rng, n_slots=31):
    gt = [0] * n_slots; need = (potential - rating) * 50
    if need > 0:
        slots = rng.sample(range(0, 20), min(8, max(1, need // 100 or 1))); per = need // len(slots)
        for i, s in enumerate(slots): gt[s] = per if i else need - per * (len(slots) - 1)
    for s in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))): gt[s] = -100 * rng.randint(1, 3)
    return gt

def main():
    dry = '--dry-run' in sys.argv
    d = json.load(open(repo('PGMRoster_1979.json'))); by = {norm(x['forename'] + ' ' + x['surname']): x for x in d}
    young = [r for r in csv.DictReader(open(repo('wip', 'unrated_1979.csv'))) if r['age'].isdigit() and int(r['age']) <= 25]
    idx = {}
    for y in (1976, 1977, 1978, 1979):
        for r in csv.DictReader(open(repo('wip', f'draft_{y}_pfr.csv'))): idx.setdefault(norm(r['name']), r)
    def num(r, k):
        v = (r.get(k) or '').strip(); return float(v) if re.fullmatch(r'-?\d+(\.\d+)?', v) else None
    men = []
    for r in young:
        x = by[norm(r['name'])]; L = idx.get(norm(r['name']), {})
        wav = num(L, 'career_av') or 0.0     # blank wAV is 0, as the project's outcome score reads it; Jurich's -1 stays the worst
        men.append((x, wav, num(L, 'seasons_started') or 0, int(r['age'])))
    assert len(men) == 22
    prat = sorted(x['rating'] for y in ('2013', '2017', '2021', '2026') for x in json.load(open(repo(f'PGMRoster_{y}.json'))) if x['teamID'] == 'Rookie')
    order = sorted(men, key=lambda t: (t[1], t[2], -t[3]))              # worst outcome first
    print(f"  {'name':<20}{'pos':>4}{'age':>4}{'wAV':>6}{'was':>5}{'now':>5}")
    for i, (x, wav, ss, age) in enumerate(order):
        q = (i + 0.5) / len(order); target = prat[min(len(prat) - 1, int(round(q * (len(prat) - 1))))]
        was, hd = x['rating'], x['potential'] - x['rating']
        names, w = KW[x['position']]; live = [a for a, c in zip(names, w[:-1]) if c > 0]
        # scale the positively-weighted attributes toward the target, keep the shape
        for _ in range(60):
            cur = rating_of(x)
            if cur == target: break
            f = (target - w[-1]) / max(1e-9, (cur - w[-1]))
            for a in live: x[a] = max(1, min(99, int(round(x[a] * f))))
        for _ in range(200):                                              # then nudge the heaviest attribute
            cur = rating_of(x)
            if cur == target: break
            a = max(live, key=lambda a: dict(zip(names, w))[a]); x[a] += 1 if cur < target else -1
        x['rating'] = rating_of(x); x['potential'] = x['rating'] + hd
        x['growthType'] = build_growth(x['potential'], x['rating'], random.Random(f"{x['iden']}|1979|young"), 31)
        print(f"  {x['forename']+' '+x['surname']:<20}{x['position']:>4}{age:>4}{wav:>6.0f}{was:>5}{x['rating']:>5}")
    for x in d: assert sum(v for v in x['growthType'] if v > 0) == (x['potential'] - x['rating']) * 50
    for t in ('JAX', 'TEN', 'CAR', 'IND'):
        top = sorted([z for z in d if z['teamID'] == t], key=lambda z: -z['rating'])[:3]
        print(f"  {t} top three: " + ', '.join(f"{z['surname']} {z['position']} {z['rating']}" for z in top))
    if dry: print('  --dry-run: nothing written'); return
    open(repo('PGMRoster_1979.json'), 'w').write(json.dumps(d, indent=1) + '\n'); print('  wrote PGMRoster_1979.json')

if __name__ == '__main__':
    main()
