#!/usr/bin/env python3
"""
fix_2026_contracts — three contract defects in 2026, one pass, in order.
Ruled 2026-09-03.

  python3 tools/fix_2026_contracts.py --dry-run
  python3 tools/fix_2026_contracts.py

1. THE FLOOR (item 45 source 2). 2026's cheap end is the archive's inherited
   placeholders — 96 rostered men under $500K, a minimum of $2K — where the
   game's rostered minimum is $600K (110 men sit exactly on it) with position
   exceptions in the 60s band: QB $1.08M, WR $1.09M, CB and DT $0.80M, DE
   $0.70M. The floor is measured from vanilla as the minimum pay by (position,
   rating band), falling back to the band minimum. LIFT ONLY.
2. THE COMPRESSED TOP (source 3). The position-aware transform that took 1979
   and 2000 from mean position distance 0.32/0.35 to 0.13/0.14: per position,
   rank-map onto the game's distribution for that position, then scale each
   team uniformly onto the rank-mapped vanilla total. Runs on the corrected
   floor, so the floor is not mapped twice.
3. EXTENSION TERMS, derived from the FINAL salary. Rostered men draw from
   vanilla's joint (length, rating band) table as 1979's 1,597 did — 2026's
   existing terms were one-sided (100% asking for a raise, item 41). Free
   agents are a DIFFERENT distribution, checked before assuming otherwise:
   vanilla's 448 carry salary 0, length 0, eLength 1 and an ABSOLUTE asking
   price in eSalary (median $0.70M), so they draw eSalary by rating band from
   vanilla's free agents, not a ratio. 2026's 465 free agents had eSalary 0 —
   any of them could be re-signed forever at nothing.

2b. A SECOND FLOOR PASS after the transform, ruled. We carry 59 men per team
   to the game's 53, so each team's bottom six map onto vanilla's per-position
   minimum, and the uniform per-team scale then takes some of them under $600K
   — 12 men, a few thousand dollars each, p10 at $0.62M against the game's
   $0.70M. Lift-only again, then raise_payroll re-trues the medians.

Then tools/raise_payroll.py 2026 puts team medians back on $242.9M exactly.
"""
import json, os, sys, random, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
import importlib.util
_s = importlib.util.spec_from_file_location('rp', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raise_payroll.py'))
rp = importlib.util.module_from_spec(_s); _s.loader.exec_module(rp)
pay = lambda x: x['salary'] + x['guarantee']
def band(r): return '<60' if r < 60 else '60s' if r < 70 else '70s' if r < 80 else '80+'
def q(arr, p):
    i = p * (len(arr) - 1); lo = int(i); hi = min(lo + 1, len(arr) - 1); return arr[lo] + (arr[hi] - arr[lo]) * (i - lo)
def shape(r):
    s = sorted(x['salary'] for x in r); n = len(s); return s[n // 10], s[n // 2], s[n * 9 // 10]
def asks(r):
    v = [x['eSalary'] / x['salary'] for x in r if x['salary'] > 0]
    return st.median(v), sum(1 for z in v if z > 1.05) / len(v), sum(1 for z in v if z < 0.95) / len(v)

def main():
    dry = '--dry-run' in sys.argv
    head = subprocess.run(['git', 'show', 'HEAD:PGMRoster_2026.json'], capture_output=True, text=True, cwd=repo('')).stdout
    assert json.dumps(json.loads(head), separators=(', ', ': ')) == head
    van_all = json.load(open(rp.VAN)); van = rp.rostered(van_all); vfa = [x for x in van_all if x['teamID'] == 'Free Agent']
    d = json.load(open(repo('PGMRoster_2026.json'))); ros = rp.rostered(d); fa = [x for x in d if x['teamID'] == 'Free Agent']
    watch = {n: None for n in ('Josh Allen', 'Aidan Hutchinson', 'Trey Smith', 'Maxx Crosby')}
    for x in ros:
        if x['forename'] + ' ' + x['surname'] in watch: watch[x['forename'] + ' ' + x['surname']] = x
    w0 = {n: pay(x) for n, x in watch.items()}
    vp10, vmed, vp90 = shape(van); vmin = min(pay(x) for x in van)
    print(f"{'':<26}{'p10':>8}{'median':>9}{'p90':>8}{'<$500K':>8}{'mean dist':>11}")
    def row(tag):
        p10, med, p90 = shape(ros); md = st.mean(abs(rp.pos_ratios(ros)[k] - vr[k]) for k in rp.pos_ratios(ros) if k in vr)
        print(f"{tag:<26}${p10/1e6:>6.2f}M ${med/1e6:>6.2f}M ${p90/1e6:>6.2f}M{sum(1 for x in ros if pay(x) < 5e5):>8}{md:>11.3f}")
    vr = rp.pos_ratios(van)
    print(f"{'vanilla':<26}${vp10/1e6:>6.2f}M ${vmed/1e6:>6.2f}M ${vp90/1e6:>6.2f}M{0:>8}{'':>11}")
    row('2026 before')

    # ---- 1. floor from vanilla, lift only
    floor = collections.defaultdict(list)
    for x in van: floor[(x['position'], band(x['rating']))].append(pay(x))
    fband = collections.defaultdict(list)
    for x in van: fband[band(x['rating'])].append(pay(x))
    def vfloor(x):
        v = floor.get((x['position'], band(x['rating'])))
        return min(v) if v and len(v) >= 5 else min(fband[band(x['rating'])])
    lifted = 0
    for x in ros:
        f = vfloor(x)
        if pay(x) < f:
            g = x['guarantee'] / pay(x) if pay(x) else 0.05; x['guarantee'] = int(round(f * g)); x['salary'] = int(round(f)) - x['guarantee']; lifted += 1
    row(f'after floor ({lifted} lifted)')

    # ---- 2. position-aware onto the game
    vpos = collections.defaultdict(list)
    for x in van: vpos[x['position']].append(pay(x))
    for k in vpos: vpos[k].sort()
    before = {x['iden']: pay(x) for x in ros}; by = rp.team_pay(ros)
    bypos = collections.defaultdict(list)
    for x in ros: bypos[x['position']].append(x)
    for pos, xs in bypos.items():
        ref = vpos.get(pos) or sorted(v for k in vpos for v in vpos[k])
        xs.sort(key=lambda x: (pay(x), x['rating'], x['iden']))
        for i, x in enumerate(xs):
            new = q(ref, (i + .5) / len(xs)); g = x['guarantee'] / pay(x) if pay(x) else 0
            x['_g'] = int(round(new * g)); x['_s'] = int(round(new)) - x['_g']
    vpay = sorted(rp.top53(ps) for ps in rp.team_pay(van).values())
    order = sorted(by, key=lambda t: sum(before[z['iden']] for z in by[t]))
    for rank, t in enumerate(order):
        tgt = vpay[min(len(vpay) - 1, int(round((rank + 0.5) / len(order) * (len(vpay) - 1))))]
        cur = sum(sorted((z['_s'] + z['_g'] for z in by[t]), reverse=True)[:53]); k = tgt / cur
        for z in by[t]:
            tot = int(round((z['_s'] + z['_g']) * k)); g = int(round(z['_g'] * k)); z['salary'], z['guarantee'] = tot - g, g; z.pop('_s'); z.pop('_g')
    inv = tot = 0
    for t, ps in by.items():
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = ps[i], ps[j]
                if before[a['iden']] == before[b['iden']]: continue
                tot += 1; inv += (before[a['iden']] < before[b['iden']]) != (pay(a) < pay(b))
    row('after position-aware')
    lifted2 = 0
    for x in ros:
        f = vfloor(x)
        if pay(x) < f:
            g = x['guarantee'] / pay(x) if pay(x) else 0.05; x['guarantee'] = int(round(f * g)); x['salary'] = int(round(f)) - x['guarantee']; lifted2 += 1
    row(f'after 2nd floor ({lifted2} lifted)')
    print(f"   within-team cross-position pairs reordered {inv:,} of {tot:,} ({inv/tot:.1%}); QB ratio {rp.pos_ratios(ros)['QB']:.2f} (vanilla {vr['QB']:.2f})")
    print("   the watched men: " + '; '.join(f"{n} ${w0[n]/1e6:.1f}M -> ${pay(x)/1e6:.1f}M" for n, x in watch.items()))

    # ---- 3. extension terms from FINAL salary
    cell = collections.defaultdict(lambda: {'ratio': [], 'elen': [], 'eg': []})
    for x in van:
        if x['salary'] <= 0: continue
        c = cell[(x['length'], band(x['rating']))]; c['ratio'].append(x['eSalary'] / x['salary']); c['elen'].append(x['eLength']); c['eg'].append(x['eGuarantee'] / x['eSalary'] if x['eSalary'] else 0)
    def draw(x):
        k = (x['length'], band(x['rating']))
        if len(cell[k]['ratio']) < 20: k = min((kk for kk in cell if len(cell[kk]['ratio']) >= 20), key=lambda kk: (abs(kk[0] - x['length']), kk[1] != band(x['rating'])))
        c = cell[k]; rng = random.Random(f"{x['iden']}|2026|ext")
        return sorted(c['ratio'])[min(len(c['ratio']) - 1, int(rng.random() * len(c['ratio'])))], rng.choice(c['elen']), rng.choice(c['eg'])
    vmax_s = max(x['eSalary'] for x in van); vmax_g = max(x['eGuarantee'] for x in van)
    for x in ros:
        if x['salary'] <= 0: continue
        r_, el, eg = draw(x); es = min(int(round(x['salary'] * r_)), vmax_s); x['eSalary'], x['eLength'], x['eGuarantee'] = es, el, min(int(round(es * eg)), vmax_g)
    m, up, dn = asks(ros); print(f"   rostered asks: median {m:.2f}, want a raise {up:.0%}, want less {dn:.0%}   (vanilla 1.00 / 27% / 22%)")
    # free agents: absolute asking price by rating band, from vanilla's free agents
    fask = collections.defaultdict(list)
    for x in vfa: fask[band(x['rating'])].append((x['eSalary'], x['eGuarantee'], x['eLength']))
    for x in fa:
        rng = random.Random(f"{x['iden']}|2026|fa"); pool = fask.get(band(x['rating'])) or [v for b in fask for v in fask[b]]
        x['eSalary'], x['eGuarantee'], x['eLength'] = rng.choice(pool)
    print(f"   free agents: {len(fa)} now carry an asking price, median ${st.median(x['eSalary'] for x in fa)/1e6:.2f}M, eLength {dict(collections.Counter(x['eLength'] for x in fa))}   (vanilla FA median ${st.median(x['eSalary'] for x in vfa)/1e6:.2f}M, eLength 1)")
    if dry: print('  --dry-run: nothing written'); return
    open(repo('PGMRoster_2026.json'), 'w').write(json.dumps(d, separators=(', ', ': '))); print('  wrote PGMRoster_2026.json — now run tools/raise_payroll.py 2026')

if __name__ == '__main__':
    main()
