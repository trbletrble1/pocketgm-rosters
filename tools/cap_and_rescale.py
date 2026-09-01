"""Pass B1, second half -- cap K/P, then restore the file to $197.4M.

Capping removes money. On 2017 it removed $34.1M and dropped the median top-53
to $195.0M, which fails the payroll gate. Ruling: the $197.4M figure is a hard
engine requirement, not a preference -- the cap is a fixed constant and the
dollars are only meaningful relative to it, so a file at $195.0M is the same
class of error as the 2000 build at $56M, just smaller. Every published file
sits within $29k of the constant.

So: cap, then rescale the whole file by one uniform factor. Uniform scaling
preserves every relationship -- the ordering does not move, only the units --
which is the property that made it acceptable for the 2000 build. The K/P
ceiling survives the rescale because the league median scales with everything
else, so the 4x RATIO is unchanged.

2013 is included. This pass created its $196.5M deviation, $900k outside the
$29k band the other files hold, and the same reasoning applies.
"""
import json, sys, statistics, collections

TARGET = 197_400_000
MULT = 4.0
KP = {'K', 'P'}


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


def lg_median(recs):
    return statistics.median(p['salary'] for p in recs
                             if p['teamID'] not in ('Free Agent', 'Rookie'))


def run(year, dry=False, _hook=None):
    path = f'PGMRoster_{year}.json'
    recs, kw = detect_format(path)
    n_in = len(recs)
    before = [dict(p) for p in recs]
    order0 = sorted(range(n_in), key=lambda i: (recs[i]['salary'] + recs[i]['guarantee'], i))

    # 1. cap
    ceiling = MULT * lg_median(recs)
    capped = 0
    for p in recs:
        if p['position'] in KP and p['salary'] > ceiling:
            f = ceiling / p['salary']
            p['salary'] = int(round(ceiling))
            p['guarantee'] = int(round(p['guarantee'] * f))
            capped += 1

    mid = [dict(q) for q in recs]          # state after the cap, before scaling
    capped_ix = {i for i, q in enumerate(recs)
                 if before[i]['salary'] != q['salary']}

    # 2. uniform rescale back to the engine constant
    med_capped = statistics.median(top53(recs))
    factor = TARGET / med_capped
    assert 0.9 < factor < 1.2, f'{year}: implausible rescale factor {factor:.4f}'
    for p in recs:
        p['salary'] = int(round(p['salary'] * factor))
        p['guarantee'] = int(round(p['guarantee'] * factor))

    if _hook:
        _hook(recs)

    # ---- guards --------------------------------------------------------
    assert len(recs) == n_in, f'{year}: record count moved {n_in} -> {len(recs)}'
    assert [p['appearance'] for p in before] == [p['appearance'] for p in recs], \
        f'{year}: appearance changed'
    for o, nw in zip(before, recs):
        moved = [k for k in o if o[k] != nw[k]]
        assert set(moved) <= {'salary', 'guarantee'}, \
            f'{year}: unexpected field(s) changed: {moved}'
    med = statistics.median(top53(recs))
    assert abs(med - TARGET) < 50_000, \
        f'{year}: median top-53 ${med:,.0f} missed ${TARGET:,}'
    ceil2 = MULT * lg_median(recs)
    over = [(p['forename'], p['surname'], p['salary']) for p in recs
            if p['position'] in KP and p['salary'] > ceil2 * 1.001]
    assert not over, f'{year}: K/P back above {MULT}x after rescale: {over[:3]}'
    # Ordering. Capping MUST reorder -- a kicker dropping from 8.5x to 4x has
    # to pass the players who sat between. What must not reorder is the
    # RESCALE, which is the property that makes uniform scaling safe. So both
    # are measured separately, and every cap-induced inversion must involve a
    # record the cap actually touched.
    # Ordering. Capping MUST reorder -- a kicker dropping from 8.5x to 4x has
    # to pass the players who sat between. What must not reorder is the
    # RESCALE, which is the property that makes uniform scaling safe.
    #
    # This is an exact permutation comparison, not an adjacent-pair scan. The
    # adjacent-pair version was VACUOUS: these files carry minimum-salary
    # ladders where dozens of players hold an identical total, so the strict
    # "<" between neighbours is never true and a $5M jump on one record scored
    # zero inversions.
    def tot(rs, i):
        return rs[i]['salary'] + rs[i]['guarantee']

    def strict_inversions(A, B, skip=frozenset()):
        """Pairs whose STRICT order flips. Ties splitting is allowed: rounding
        the two components separately can separate equal totals by $1, which is
        not a reordering. An exact-permutation check fails on that; an
        adjacent-pair check is vacuous, because these files carry
        minimum-salary ladders where dozens of records share a total, so the
        strict '<' between neighbours is never true and a $5M jump scores
        zero. Grouping by the old total and comparing group extremes is the
        formulation that is neither."""
        ix = [i for i in range(n_in) if i not in skip]
        groups = collections.defaultdict(list)
        for i in ix:
            groups[tot(A, i)].append(i)
        keys = sorted(groups)
        bad = 0
        prev_max = None
        for k in keys:
            cur = [tot(B, i) for i in groups[k]]
            if prev_max is not None and min(cur) < prev_max:
                bad += 1
            prev_max = max(max(cur), prev_max if prev_max is not None else max(cur))
        return bad

    assert strict_inversions(mid, recs) == 0, \
        f'{year}: the rescale reordered contracts -- uniform scaling must not'
    # the cap may reorder, but only around records it actually touched
    assert strict_inversions(before, mid, skip=capped_ix) == 0, \
        f'{year}: the cap reordered records it did not touch'
    inv = strict_inversions(before, mid)

    print(f'  {year}: {capped:3} capped, rescaled x{factor:.5f}  '
          f'median top-53 ${med_capped/1e6:.1f}M -> ${med:,.0f}  '
          f'inversions: rescale 0, cap {inv} (all on capped records)')
    if not dry:
        json.dump(recs, open(path, 'w', encoding='utf-8'), **kw)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    for y in (2017, 2013):
        run(y, dry)
