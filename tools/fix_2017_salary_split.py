#!/usr/bin/env python3
"""
fix_2017_salary_split — backlog 62. Ruled by Ryan 2026-09-03.

    python3 tools/fix_2017_salary_split.py --dry-run
    python3 tools/fix_2017_salary_split.py

THE DEFECT. At a95c793 the contract work put a floor on salary and 2017 came
out with nobody under $500K. At 7b40c9a, four commits later, the guarantee
split moved money out of salary into guarantee for 1,016 of 2017's players —
total compensation preserved on every one of them, cap arithmetic untouched,
and the salary floor silently undone underneath it. Elijah Wilkinson ended on
$101,178 of salary against $494,049 of guarantee. Nothing in the split's code
mentioned the floor.

Found by the retrofitted salary-wall gate on its first run, in a file that was
green under every check that existed the day before.

THE FIX, as ruled: the floor binds on SALARY ALONE, the Christen Miller ruling
of 2026-09-03 — a man must not read as unpaid on a contract screen that shows
salary. So this re-splits the same money:

    salary    = min(total, max(salary, vanilla floor for his position and band))
    guarantee = total - salary

TOTAL COMPENSATION IS UNCHANGED FOR EVERY MAN, asserted per record. No new
money, no payroll re-true, no raise_payroll pass afterwards: team payroll is
identical to the dollar, so the published median stays where it is.

WHERE A MAN'S WHOLE PAY IS UNDER THE FLOOR he takes all of it as salary and his
guarantee goes to zero. 280 men are in that position and they were there before
the split too — 2017's per-team rescale left its cheapest men at $583,062
against a $600,000 floor. That is the second-floor-pass drift, not this defect,
and this tool does not invent money to cover it.
"""
import json, os, sys, collections, subprocess, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
import importlib.util
_s = importlib.util.spec_from_file_location(
    'rp', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raise_payroll.py'))
rp = importlib.util.module_from_spec(_s); _s.loader.exec_module(rp)

Y = 2017
pay = lambda x: x['salary'] + x['guarantee']
def band(r): return '<60' if r < 60 else '60s' if r < 70 else '70s' if r < 80 else '80+'


def main():
    dry = '--dry-run' in sys.argv
    path = f'PGMRoster_{Y}.json'
    head = subprocess.run(['git', 'show', f'HEAD:{path}'],
                          capture_output=True, text=True, cwd=repo('')).stdout
    ser = ((lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else ''))
           if head.count('\n') > 1 else (lambda d: json.dumps(d, separators=(', ', ': '))))
    assert ser(json.loads(head)) == head, f'{Y}: stored formatting not reproduced'

    van = rp.rostered(json.load(open(rp.VAN)))
    floor = collections.defaultdict(list); fband = collections.defaultdict(list)
    for x in van:
        floor[(x['position'], band(x['rating']))].append(x['salary'])
        fband[band(x['rating'])].append(x['salary'])
    def vfloor(x):
        v = floor.get((x['position'], band(x['rating'])))
        return min(v) if v and len(v) >= 5 else min(fband[band(x['rating'])])

    d = json.load(open(repo(path)))
    on = [p for p in d if p.get('teamID') not in ('Rookie', 'Free Agent')]
    before_pay = {id(p): pay(p) for p in on}
    before_team = collections.Counter()
    for p in on: before_team[p['teamID']] += pay(p)

    s0 = sorted(p['salary'] for p in on)
    moved = lifted_to_floor = all_salary = 0; dollars = 0
    for p in on:
        tot = pay(p); f = vfloor(p)
        if p['salary'] >= f: continue
        new_s = min(tot, f)
        dollars += new_s - p['salary']; moved += 1
        p['salary'], p['guarantee'] = new_s, tot - new_s
        if new_s == f: lifted_to_floor += 1
        else: all_salary += 1
        assert pay(p) == tot, 'total compensation changed'

    for p in on: assert pay(p) == before_pay[id(p)], 'total compensation changed'
    after_team = collections.Counter()
    for p in on: after_team[p['teamID']] += pay(p)
    assert before_team == after_team, 'team payroll changed'

    s1 = sorted(p['salary'] for p in on)
    w = lambda s: s[0] / s[len(s) // 100] if s[len(s) // 100] else 0
    print(f'{Y}: {len(on)} rostered')
    print(f'  below the vanilla floor on salary: {moved}')
    print(f'    {lifted_to_floor} reach the floor from their own guarantee')
    print(f'    {all_salary} take their whole pay as salary (it is under the floor)')
    print(f'  ${dollars/1e6:.2f}M moved guarantee -> salary; total pay unchanged on all {len(on)}')
    print(f'  salary min ${s0[0]:,} -> ${s1[0]:,};  1st pct ${s0[len(s0)//100]:,} -> ${s1[len(s1)//100]:,}')
    print(f'  salary wall min/p01 {w(s0):.2f} -> {w(s1):.2f}   (gate needs >= 0.90)')
    print(f'  under $500K {sum(1 for x in s0 if x < 5e5)} -> {sum(1 for x in s1 if x < 5e5)}')
    print(f'  guarantee > 0 on {sum(1 for p in on if p["guarantee"] > 0)} of {len(on)}')
    print(f'  median team payroll ${st.median([sum(sorted([pay(q) for q in on if q["teamID"] == t], reverse=True)[:53]) for t in after_team])/1e6:.1f}M (unchanged by construction)')

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    print(f'  wrote {path}')


if __name__ == '__main__':
    main()
