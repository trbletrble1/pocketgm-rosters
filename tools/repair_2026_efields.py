#!/usr/bin/env python3
"""repair_2026_efields — restore the extension terms a6fb417 destroyed.

WHAT WENT WRONG. tools/raise_payroll.py assigned

    x['eSalary'], x['eGuarantee'] = x['salary'], x['guarantee']

and those are not mirrors. Vanilla pairs them with eLength, and they are the
terms the player wants to RE-SIGN for:

    Derrick Tunsil     salary 3.1M  length 1  |  eSalary 7.7M  eLength 4
    Reginald Emanuel   salary 9.5M  length 4  |  eSalary 9.4M  eLength 3
    Jayden Agholor     salary 10.3M length 3  |  eSalary 10.5M eLength 4

Tunsil is on a cheap one-year deal and wants 7.7M over four. Flattening the
fields makes every player's asking price equal his current salary, so every
extension is free and nobody ever asks for a raise. A gameplay defect, live in
2026 since a6fb417.

WHY IT IS REPAIRABLE. a6fb417 touched nothing but the four money fields, and its
per-team scale was uniform to 2.2e-04 (pure rounding). So the factor each team
received is recoverable from the salary change, and the pre-write e-fields at
a6fb417^ can be carried forward through the same scale.

Rostered men get their pre-write e-fields rescaled by their team's factor. Men
the payroll tool never touched get theirs back verbatim.

    python3 tools/repair_2026_efields.py --dry-run
    python3 tools/repair_2026_efields.py
"""
import json, os, subprocess, sys, statistics as st, collections

BROKE = 'a6fb417'

def repo(n):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), n)

def main():
    dry = '--dry-run' in sys.argv
    pre = json.loads(subprocess.run(['git', 'show', f'{BROKE}^:PGMRoster_2026.json'],
                                    capture_output=True, text=True, cwd=repo('')).stdout)
    now = json.load(open(repo('PGMRoster_2026.json')))
    assert len(pre) == len(now), (len(pre), len(now))

    # Recover each team's factor from the salary+guarantee change.
    ks = collections.defaultdict(list)
    for a, b in zip(pre, now):
        tb, ta = a['salary'] + a['guarantee'], b['salary'] + b['guarantee']
        if tb > 0 and ta != tb:
            ks[a.get('teamID')].append(ta / tb)
    k_by = {t: st.median(v) for t, v in ks.items() if t is not None}
    spread = max(max(v) - min(v) for v in ks.values() if len(v) > 1)
    assert spread < 1e-3, f'per-team factor is not uniform: {spread:.2e}'
    print(f"recovered {len(k_by)} team factors, "
          f"{min(k_by.values()):.4f}-{max(k_by.values()):.4f}, uniform to {spread:.1e}")

    touched = restored = 0
    for a, b in zip(pre, now):
        assert a['iden'] == b['iden'] and a['surname'] == b['surname']
        moved = (a['salary'] + a['guarantee']) != (b['salary'] + b['guarantee'])
        k = k_by.get(a.get('teamID'), 1.0) if moved else 1.0
        if moved:
            # Same round-the-total-then-split as the payroll tool, so the
            # extension keeps its shape rather than drifting a dollar.
            tot = int(round((a['eSalary'] + a['eGuarantee']) * k))
            eg = int(round(a['eGuarantee'] * k))
            b['eSalary'], b['eGuarantee'] = tot - eg, eg
            touched += 1
        else:
            b['eSalary'], b['eGuarantee'] = a['eSalary'], a['eGuarantee']
            restored += 1

    ds = sum(1 for x in now if x['salary'] != x['eSalary'])
    dg = sum(1 for x in now if x['guarantee'] != x['eGuarantee'])
    pds = sum(1 for x in pre if x['salary'] != x['eSalary'])
    pdg = sum(1 for x in pre if x['guarantee'] != x['eGuarantee'])
    print(f"  rescaled {touched}, restored verbatim {restored}")
    print(f"  salary != eSalary:       {pds} before the break -> 0 broken -> {ds} now")
    print(f"  guarantee != eGuarantee: {pdg} before the break -> 0 broken -> {dg} now")
    assert ds == pds and dg == pdg, 'the distinction did not come back intact'

    if dry:
        print('  --dry-run: nothing written'); return
    json.dump(now, open(repo('PGMRoster_2026.json'), 'w'), separators=(', ', ': '))
    print('  wrote PGMRoster_2026.json')

if __name__ == '__main__':
    main()
