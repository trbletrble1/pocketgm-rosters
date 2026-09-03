#!/usr/bin/env python3
"""
contracts_to_vanilla — level AND shape in one write, the game as the reference.
1979 and 2000. Ruled 2026-09-03 (item 37).

  python3 tools/contracts_to_vanilla.py 1979 2000 --dry-run
  python3 tools/contracts_to_vanilla.py 1979 2000

WHY NOT THE PAYROLL TOOL. raise_payroll scales each team uniformly, which leaves
the within-team shape alone — and these two files' shape is the defect: 1979's
player p90:p10 is 4.6x against the game's 10.7x, its tenth-percentile man earns
$1.40M against $0.70M, and a user against the cap has no cheap depth to cut.
Both files fail raise_payroll's position-ratio guard for exactly that reason,
so level and shape land together, in one write and one gate pass.

WHY NOT compress_contracts. That transform is rank-preserving within team, and
measured against the game it is the 5.9x failure again: every 1979 team's #1
earner is its quarterback (our POS_MULT put him there), so the game's top-of-
team share lands on 32 quarterbacks and the QB ratio goes 1.84 -> 6.38 against
vanilla's 2.25. Mean position distance 0.323 -> 0.679.

THE TRANSFORM. League-wide, per position, rank-map salary+guarantee onto the
game's distribution for that position (plotting position (i+0.5)/n). Then scale
each team uniformly onto the rank-mapped vanilla team total, as raise_payroll
does. Position ratios land on the game's by construction; team medians exact.
Measured: 1979 mean distance 0.323 -> 0.124, 2000 0.351 -> 0.142, p10/p25 on
the game's ($0.75M/$1.09M against $0.70M/$1.03M).

THE COST, ACCEPTED BY RULING: within a team, one cross-position pair in six
reorders (1979 16.8%, 2000 12.9%). Within a position essentially nothing moves
(24 of 2,385 pairs, all ties). Those inversions are our POS_MULT hierarchy
(QB 1.75, RB 1.35 ...) being replaced by the game's, and that hierarchy was
established as ours, not the engine's.

THE DATA IS SOUND. Item 45 measured the near-zero-contract defect on every
file: 1979 and 2000 carry ZERO placeholders on the real signature. Their
compression is formula-built. This is not fitting to broken data.

Extension terms scale with the man (eSalary/eGuarantee by the same factor his
salary took), so the asking ratio drawn in batch 4 survives.
"""
import json, os, sys, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
import importlib.util
_s = importlib.util.spec_from_file_location('rp', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raise_payroll.py'))
rp = importlib.util.module_from_spec(_s); _s.loader.exec_module(rp)

def q(arr, p):
    i = p * (len(arr) - 1); lo = int(i); hi = min(lo + 1, len(arr) - 1)
    return arr[lo] + (arr[hi] - arr[lo]) * (i - lo)

def run(y, dry, van, vpay, vr, vpos):
    head = subprocess.run(['git', 'show', f'HEAD:PGMRoster_{y}.json'], capture_output=True, text=True, cwd=repo('')).stdout
    ser = (lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')) if head.count('\n') > 1 else (lambda d: json.dumps(d, separators=(', ', ': ')))
    assert ser(json.loads(head)) == head, f'{y}: stored formatting not reproduced'
    d = json.load(open(repo(f'PGMRoster_{y}.json')))
    ros = rp.rostered(d); by = rp.team_pay(ros); rb = rp.pos_ratios(ros)
    pay = lambda x: x['salary'] + x['guarantee']
    before = {x['iden']: pay(x) for x in ros}
    bt = {t: rp.top53(ps) for t, ps in by.items()}
    # 1. per position, onto the game's distribution for that position
    bypos = collections.defaultdict(list)
    for x in ros: bypos[x['position']].append(x)
    for pos, xs in bypos.items():
        ref = vpos.get(pos) or sorted(v for k in vpos for v in vpos[k])
        xs.sort(key=lambda x: (pay(x), x['rating'], x['iden']))
        for i, x in enumerate(xs):
            new = q(ref, (i + .5) / len(xs)); g = x['guarantee'] / pay(x) if pay(x) else 0
            x['_g'] = int(round(new * g)); x['_s'] = int(round(new)) - x['_g']
    # 2. per team, uniformly onto the rank-mapped vanilla total
    order = sorted(by, key=lambda t: sum(before[z['iden']] for z in by[t]))
    for rank, t in enumerate(order):
        tgt = vpay[min(len(vpay) - 1, int(round((rank + 0.5) / len(order) * (len(vpay) - 1))))]
        cur = sum(sorted((z['_s'] + z['_g'] for z in by[t]), reverse=True)[:53]); k = tgt / cur
        for z in by[t]:
            tot = int(round((z['_s'] + z['_g']) * k)); g = int(round(z['_g'] * k))
            f = tot / before[z['iden']] if before[z['iden']] else 1.0
            z['salary'], z['guarantee'] = tot - g, g
            z['eSalary'] = int(round(z['eSalary'] * f)); z['eGuarantee'] = int(round(z['eGuarantee'] * f))
            z.pop('_s'); z.pop('_g')
    ra = rp.pos_ratios(ros); at = {t: rp.top53(ps) for t, ps in by.items()}
    md_b = st.mean(abs(rb[p] - vr[p]) for p in rb if p in vr); md_a = st.mean(abs(ra[p] - vr[p]) for p in ra if p in vr)
    inv = tot = inv_same = tot_same = 0
    for t, ps in by.items():
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = ps[i], ps[j]
                if before[a['iden']] == before[b['iden']]: continue
                flip = (before[a['iden']] < before[b['iden']]) != (pay(a) < pay(b))
                tot += 1; inv += flip
                if a['position'] == b['position']: tot_same += 1; inv_same += flip
    s = sorted(x['salary'] for x in ros); n = len(s); vs = sorted(x['salary'] for x in van)
    ap = sorted(at.values())
    print(f'=== {y} ===')
    print(f"  team top-53   before med ${st.median(bt.values())/1e6:.1f}M -> after min/p25/med/max ${ap[0]/1e6:.1f}M/${ap[len(ap)//4]/1e6:.1f}M/${st.median(ap)/1e6:.1f}M/${ap[-1]/1e6:.1f}M   (vanilla ${vpay[0]/1e6:.1f}M/${vpay[len(vpay)//4]/1e6:.1f}M/${st.median(vpay)/1e6:.1f}M/${vpay[-1]/1e6:.1f}M)")
    print(f"  player salary p10/p25/med/p90  ${s[n//10]/1e6:.2f}M/${s[n//4]/1e6:.2f}M/${s[n//2]/1e6:.2f}M/${s[n*9//10]/1e6:.2f}M  p90:p10 {s[n*9//10]/s[n//10]:.1f}x   (vanilla ${vs[len(vs)//10]/1e6:.2f}M/${vs[len(vs)//4]/1e6:.2f}M/${vs[len(vs)//2]/1e6:.2f}M/${vs[len(vs)*9//10]/1e6:.2f}M {vs[len(vs)*9//10]/vs[len(vs)//10]:.1f}x)")
    print(f"  mean position distance to vanilla {md_b:.3f} -> {md_a:.3f};  QB {rb['QB']:.2f} -> {ra['QB']:.2f} (vanilla {vr['QB']:.2f}); K {rb.get('K',0):.2f} -> {ra.get('K',0):.2f} (vanilla {vr.get('K',0):.2f})")
    print(f"  within-team pairs reordered: {inv:,} of {tot:,} ({inv/tot:.1%}) — same-position {inv_same} of {tot_same:,}   ACCEPTED BY RULING")
    assert max(ap) <= vpay[-1] + 1000 and md_a < md_b and inv_same / max(1, tot_same) < 0.02
    v = [x['eSalary'] / x['salary'] for x in ros if x['salary'] > 0]
    print(f"  extension ratio survives: median {st.median(v):.2f}, want a raise {sum(1 for r_ in v if r_ > 1.05)/len(v):.0%}")
    if dry: print('  --dry-run: nothing written\n'); return
    open(repo(f'PGMRoster_{y}.json'), 'w').write(ser(d)); print(f'  wrote PGMRoster_{y}.json\n')

def main():
    years = [a for a in sys.argv[1:] if a in ('1979', '2000')]; dry = '--dry-run' in sys.argv; assert years
    van = rp.rostered(json.load(open(rp.VAN))); vby = rp.team_pay(van)
    vpay = sorted(rp.top53(ps) for ps in vby.values()); vr = rp.pos_ratios(van)
    vpos = collections.defaultdict(list)
    for x in van: vpos[x['position']].append(x['salary'] + x['guarantee'])
    for k in vpos: vpos[k].sort()
    for y in years: run(y, dry, van, vpay, vr, vpos)

if __name__ == '__main__':
    main()
