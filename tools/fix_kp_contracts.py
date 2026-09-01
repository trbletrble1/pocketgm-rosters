"""Pass B1 -- cap kicker and punter contracts at 4x each file's league median.

Same defect as the K/P ratings trap, one field over: Madden grades kickers on
leg strength and punters on power, which saturates them near the top of the
rating scale, and contracts were derived partly from rating.

Measured as a multiple of each file's OWN league median salary, so era scaling
does not confound it. The medians are fine -- 0.87 to 1.92, which is realistic.
The problem is entirely in the tail: a punter at 8x a league median salary is
not a thing that happened. Real top-of-market specialists run about 3-4x.

47 records across four files. 2004, 2007 and 2021 are untouched entirely.

4x rather than tighter: the 2000 build landed K/P at 2.68x after engine
scaling, inside the published 1.08-2.85x band, with its p95 at 5.00x against a
published median p95 of 6.43x. A 4x ceiling brings the archive into line with
2000 without flattening genuine variation.

guarantee scales with salary so the pair stays proportional.
"""
import json, sys, os, statistics, collections

FILES = [1986, 2004, 2007, 2010, 2013, 2017, 2021]
KP = {'K', 'P'}
MULT = 4.0


def detect_format(path):
    raw = open(path, encoding='utf-8').read()
    d = json.loads(raw)
    for sep in ((',', ':'), (', ', ': ')):
        for asc in (False, True):
            kw = dict(ensure_ascii=asc, separators=sep)
            if json.dumps(d, **kw) == raw:
                return d, kw
    raise SystemExit(f'{path}: no dumps setting reproduces the file')


def top53(recs):
    by = collections.defaultdict(list)
    for p in recs:
        if p['teamID'] not in ('Free Agent', 'Rookie'):
            by[p['teamID']].append(p['salary'] + p['guarantee'])
    return [sum(sorted(v, reverse=True)[:53]) for v in by.values()]


def fix(year, dry=False, _hook=None):
    path = f'PGMRoster_{year}.json'
    recs, kw = detect_format(path)
    n_in = len(recs)
    before = [dict(p) for p in recs]
    ros = [p for p in recs if p['teamID'] not in ('Free Agent', 'Rookie')]
    lg = statistics.median(p['salary'] for p in ros)
    assert lg > 0, f'{year}: zero league median salary'
    ceiling = MULT * lg
    med_before = statistics.median(top53(recs))

    kp_med_before = {q: statistics.median(
        [p['salary'] for p in ros if p['position'] == q]) for q in KP}

    changed = 0
    for p in recs:
        if p['position'] not in KP or p['salary'] <= ceiling:
            continue
        f = ceiling / p['salary']
        p['salary'] = int(round(ceiling))
        p['guarantee'] = int(round(p['guarantee'] * f))   # stays proportional
        changed += 1

    if _hook:
        _hook(recs)

    # ---- guards --------------------------------------------------------
    assert len(recs) == n_in, f'{year}: record count moved {n_in} -> {len(recs)}'
    assert [p['appearance'] for p in before] == [p['appearance'] for p in recs], \
        f'{year}: appearance changed'
    for o, nw in zip(before, recs):
        moved = [k for k in o if o[k] != nw[k]]
        if not moved:
            continue
        assert set(moved) <= {'salary', 'guarantee'}, \
            f'{year}: unexpected field(s) changed: {moved}'
        assert nw['position'] in KP, f'{year}: a non-specialist moved ({nw["position"]})'
        assert o['salary'] > ceiling, \
            f'{year}: a record at or under the ceiling moved ({o["salary"]} <= {ceiling:.0f})'
        assert nw['salary'] <= o['salary'], f'{year}: a capped salary went UP'
    ros2 = [p for p in recs if p['teamID'] not in ('Free Agent', 'Rookie')]
    for q in KP:
        v = [p['salary'] for p in ros2 if p['position'] == q]
        assert statistics.median(v) == kp_med_before[q], \
            f'{year}: the {q} median moved -- only the tail should change'
    med_after = statistics.median(top53(recs))
    drift = abs(med_after - med_before) / med_before
    assert drift < 0.01, f'{year}: team payroll median moved {100*drift:.2f}%'

    if changed:
        print(f'  {year}: {changed:3} capped at {MULT:.0f}x (${ceiling/1e6:.2f}M)   '
              f'top-53 median ${med_before/1e6:.1f}M -> ${med_after/1e6:.1f}M')
    else:
        print(f'  {year}:   0 over {MULT:.0f}x, untouched')
    if not dry and changed:
        json.dump(recs, open(path, 'w', encoding='utf-8'), **kw)
    return changed


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    print(f'  TOTAL {sum(fix(y, dry) for y in FILES)} records capped')
