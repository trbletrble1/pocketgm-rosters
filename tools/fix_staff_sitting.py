#!/usr/bin/env python3
"""
fix_staff_sitting — sitting staff earn nothing in 1979, and contract length runs
to 19 years in 1979 and 18 in 2000 where the game's maximum is 5. Ruled
2026-09-03. Checked on all ten files first: the salary defect is 1979's alone
(built this week by a tool that got the free-agent structure right and the
sitting one wrong); the length defect is 1979's and 2000's.

  python3 tools/fix_staff_sitting.py --dry-run
  python3 tools/fix_staff_sitting.py

LENGTH IS NOT TENURE. In 1979 it correlates with nothing — r -0.01 against
2026-startSeason, +0.02 against age; Shula 19 at 49, Madden 17 at 43 — and the
game keeps tenure in startSeason (2026-startSeason runs to 38 years in
vanilla), so nothing is lost by overwriting it. Men over the game's range take
a length drawn from vanilla's employed distribution FOR THEIR RATING BAND
(60s: all 1-year; 70s: 1-2; 80+: 1-5), seeded on identity. Men inside the
range are left alone.

SALARY, 1979 sitting men: rank-mapped within (role, rating band) onto vanilla's
employed salary distribution for that cell (plotting position (i+.5)/n), band
fallback for thin cells. Guarantee then split from the total by vanilla's rule
(every multi-year man; one-year men by band share) at vanilla's ratios. The
extension ask, which had been a ratio of a zero salary and so was ~zero too,
is re-derived from the new salary through vanilla's (length, band) joint table
with eGuarantee split as vanilla splits it.
"""
import json, os, sys, random, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
V = os.path.join(sources(), 'vanilla', 'PGMStaff_vanilla_2026-09-03.json')
def band(r): return '<60' if r < 60 else '60s' if r < 70 else '70s' if r < 80 else '80+'
ORDER = ['<60', '60s', '70s', '80+']
def q(arr, p):
    i = p * (len(arr) - 1); lo = int(i); hi = min(lo + 1, len(arr) - 1); return arr[lo] + (arr[hi] - arr[lo]) * (i - lo)
def pick(rng, arr): return arr[min(len(arr) - 1, int(rng.random() * len(arr)))]
CANDS = [lambda d: json.dumps(d, separators=(', ', ': ')), lambda d: json.dumps(d, separators=(',', ':')),
         lambda d: json.dumps(d, separators=(',', ':'), ensure_ascii=False), lambda d: json.dumps(d), lambda d: json.dumps(d, indent=1)]
def serialiser(head):
    for f in CANDS:
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head: return (lambda f, nl: lambda d: f(d) + nl)(f, nl)
    raise AssertionError('stored formatting not reproduced')

def main():
    dry = '--dry-run' in sys.argv
    ve = [x for x in json.load(open(V)) if x['teamID'] != 'Free Agent']
    sal = collections.defaultdict(list); sal_b = collections.defaultdict(list); ln = collections.defaultdict(list)
    for x in ve: sal[(x['role'], band(x['rating']))].append(x['salary']); sal_b[band(x['rating'])].append(x['salary']); ln[band(x['rating'])].append(x['length'])
    for k in sal: sal[k].sort()
    for k in sal_b: sal_b[k].sort()
    def near(b): return b if sal_b[b] else min((z for z in ORDER if sal_b[z]), key=lambda z: abs(ORDER.index(z) - ORDER.index(b)))
    g_share = {b: sum(1 for x in ve if band(x['rating']) == b and x['length'] == 1 and x['guarantee'] > 0) / max(1, sum(1 for x in ve if band(x['rating']) == b and x['length'] == 1)) for b in ORDER}
    g_ratio = sorted(x['guarantee'] / (x['salary'] + x['guarantee']) for x in ve if x['guarantee'] > 0)
    cell = collections.defaultdict(lambda: {'ratio': [], 'elen': []})
    for x in ve:
        if x['salary'] > 0: c = cell[(x['length'], band(x['rating']))]; c['ratio'].append(x['eSalary'] / x['salary']); c['elen'].append(x['eLength'])
    eg_share = {b: sum(1 for x in ve if band(x['rating']) == b and x['eLength'] < 4 and x['eGuarantee'] > 0) / max(1, sum(1 for x in ve if band(x['rating']) == b and x['eLength'] < 4)) for b in ORDER}
    eg_ratio = sorted(x['eGuarantee'] / (x['eSalary'] + x['eGuarantee']) for x in ve if x['eGuarantee'] > 0)
    for y in ('1979', '2000'):
        fn = f'PGMStaff_{y}.json'; head = subprocess.run(['git', 'show', f'HEAD:{fn}'], capture_output=True, text=True, cwd=repo('')).stdout
        ser = serialiser(head); d = json.load(open(repo(fn))); e = [x for x in d if x['teamID'] != 'Free Agent']; log = []
        # LENGTH: only men over the game's range
        over = [x for x in e if x['length'] > 5]
        for x in over:
            b = near(band(x['rating'])) if not ln[band(x['rating'])] else band(x['rating'])
            x['length'] = pick(random.Random(f"{x['iden']}|{y}|len"), sorted(ln[b]))
        L = [x['length'] for x in e]; log.append(f"length: {len(over)} men over 5 redrawn from vanilla's band distribution; now min-med-max {min(L)}-{st.median(L):.0f}-{max(L)} (vanilla 1-1-5)")
        # SALARY: 1979 only (the sitting men earn nothing)
        if st.median(x['salary'] for x in e) < 50_000:
            cells = collections.defaultdict(list)
            for x in e: cells[(x['role'], band(x['rating']))].append(x)
            for (role, b), xs in cells.items():
                ref = sal[(role, b)] if len(sal[(role, b)]) >= 5 else sal_b[near(b)]
                xs.sort(key=lambda x: (x['rating'], x['iden']))
                for i, x in enumerate(xs):
                    tot = int(round(q(ref, (i + .5) / len(xs)))); rng = random.Random(f"{x['iden']}|{y}|g")
                    if x['length'] >= 2 or rng.random() < g_share[b]:
                        x['guarantee'] = int(round(tot * pick(rng, g_ratio))); x['salary'] = tot - x['guarantee']
                    else: x['salary'], x['guarantee'] = tot, 0
                    # extension ask from the new salary
                    k = (x['length'], b)
                    if len(cell[k]['ratio']) < 10: k = min((kk for kk in cell if len(cell[kk]['ratio']) >= 10), key=lambda kk: (abs(kk[0] - x['length']), kk[1] != b))
                    rng2 = random.Random(f"{x['iden']}|{y}|ext"); c = cell[k]
                    es = int(round(x['salary'] * pick(rng2, sorted(c['ratio'])))); x['eLength'] = rng2.choice(c['elen'])
                    if x['eLength'] >= 4 or rng2.random() < eg_share[b]: x['eGuarantee'] = int(round(es * pick(rng2, eg_ratio))); x['eSalary'] = es - x['eGuarantee']
                    else: x['eSalary'], x['eGuarantee'] = es, 0
            hc = [x for x in e if x['role'] == 'Head Coach']
            log.append(f"salary: 288 sitting men mapped onto vanilla's (role, band) distributions; median ${st.median(x['salary'] for x in e)/1e6:.2f}M (vanilla $0.20M); HC 80+ med ${st.median(x['salary']+x['guarantee'] for x in hc if x['rating']>=80)/1e6:.2f}M (vanilla $6.05M); guarantee present {sum(1 for x in e if x['guarantee']>0)/len(e):.0%} (vanilla 50%); eSalary/salary med {st.median(x['eSalary']/x['salary'] for x in e if x['salary']):.2f} (vanilla 1.00); eGuarantee present {sum(1 for x in e if x['eGuarantee']>0)/len(e):.0%} (vanilla 50%)")
            log.append("  " + '; '.join(f"{x['surname']} {x['rating']} ${(x['salary']+x['guarantee'])/1e6:.2f}M/{x['length']}y ask ${(x['eSalary']+x['eGuarantee'])/1e6:.2f}M/{x['eLength']}y" for x in sorted(hc, key=lambda x: -x['rating'])[:4]))
        print(f"=== {fn} ===\n   " + '\n   '.join(log))
        if not dry: open(repo(fn), 'w').write(ser(d)); print(f"   wrote {fn}")
    if dry: print('--dry-run: nothing written')

if __name__ == '__main__':
    main()
