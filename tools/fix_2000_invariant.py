#!/usr/bin/env python3
"""fix_2000_invariant.py — close 2000's computed-rating gap through FILLED
cells only, keeping the authored rating.

The INVERSE of the 2026 fix, and available only because 2000 is a mix. Its
ratings match the published distribution (40/59/70/85/98) and were authored
against it; nine of its attributes are percentile fills. So instead of
recomputing the rating from the attributes -- which is right for 2026 and
wrong here -- the filled cells are moved until they SUPPORT the rating.

Nothing sourced is touched. The rating is never written. Records whose filled
cells cannot close the gap are LEFT BROKEN AND REPORTED, the same rule as
2026's tier-1 refusals: a record that cannot be fixed without touching sourced
data stays broken and documented.

    python3 fix_2000_invariant.py --dry-run
    python3 fix_2000_invariant.py --apply
"""
import sys, json, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_2026 as B

FILE = 'PGMRoster_2000.json'
FILL_RHO = 0.99      # a percentile fill is monotone in rating: rho ~ 1.0

def detect_filled(recs):
    """Tier the file FROM ITS OUTPUT -- 2000 has no build script either."""
    bypos = collections.defaultdict(list)
    for r in recs:
        if B.cohort_of(r) == 'T': bypos[r['position']].append(r)
    out = {}
    for a in sorted(B.ATTR_MAP):
        rhos = []
        for pos, g in bypos.items():
            pr = [(x['rating'], x[a]) for x in g if x.get(a)]
            if len(pr) < 25: continue
            rho = B.spearman([p[0] for p in pr], [p[1] for p in pr])
            if rho is not None: rhos.append(abs(rho))
        if rhos: out[a] = st.median(rhos)
    return {a for a, m in out.items() if m > FILL_RHO}, out

def main(apply_it):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, FILE)
    recs = json.load(open(path))
    W = json.load(open(B.BUNDLE))['weights']
    filled, rhos = detect_filled(recs)
    print(f'filled attributes (rho > {FILL_RHO}): {len(filled)}')
    for a in sorted(filled, key=lambda x: -rhos[x]): print(f'   {a:16s} {rhos[a]:.3f}')
    # per-(position, attribute) bounds from the file's own values
    lo, hi = {}, {}
    for r in recs:
        for a in filled:
            v = r.get(a)
            if not v: continue
            k = (r['position'], a)
            lo[k] = min(lo.get(k, v), v); hi[k] = max(hi.get(k, v), v)
    before_ratings = [r['rating'] for r in recs]
    before_sourced = {(i, a): r[a] for i, r in enumerate(recs)
                      for a in B.ATTR_MAP if a in r and a not in filled}
    fixed = refused = already = 0; ref = []
    for r in recs:
        pos = r['position']
        if pos not in W: continue
        gap = r['rating'] - B.computed_rating(r, pos, W)
        if abs(gap) <= 0.5: already += 1; continue
        names, coef = W[pos]
        mov = [(a, c) for a, c in zip(names, coef) if a in filled and a in r and r[a]]
        base = sum(c * r[a] for a, c in mov)
        if abs(base) < 1e-9: refused += 1; ref.append((r, gap, 'no filled cells')); continue
        f = 1.0 + gap / base
        trial = dict(r)
        for a, _c in mov:
            v = r[a] * f
            b = (lo.get((pos, a)), hi.get((pos, a)))
            if b[0] is not None: v = max(b[0], min(b[1], v))
            trial[a] = int(round(max(1, min(99, v))))
        if abs(B.computed_rating(trial, pos, W) - r['rating']) <= 0.5:
            for a, _c in mov: r[a] = trial[a]
            fixed += 1
        else:
            refused += 1; ref.append((r, gap, 'filled cells cannot reach'))
    print(f'\nalready within 0.5: {already}   closed: {fixed}   REFUSED: {refused}')
    # ---- the two properties that make this the better trade ----
    assert [r['rating'] for r in recs] == before_ratings, 'a rating moved'
    moved = [k for k, v in before_sourced.items() if recs[k[0]][k[1]] != v]
    assert not moved, f'{len(moved)} SOURCED attributes moved: {moved[:4]}'
    print('   ASSERTED: no rating changed; no sourced attribute changed')
    g = [abs(max(1, min(99, B.computed_rating(r, r['position'], W))) - r['rating'])
         for r in recs if r['position'] in W]
    print(f'   invariant now: median {st.median(g):.2f}  max {max(g):.2f}  '
          f'over 5: {sum(1 for x in g if x > 5)}  (was 476)')
    if ref:
        print(f'\n   refused, left broken and documented ({len(ref)}):')
        for r, gp, why in sorted(ref, key=lambda x: -abs(x[1]))[:6]:
            print(f'      {r["forename"]} {r["surname"]:20s} {r["position"]:4s} gap {gp:+6.1f}  {why}')
    if apply_it:
        with open(path, 'w') as f: json.dump(recs, f, separators=(',', ':'))
        print(f'\nWRITTEN: {path}')
    else:
        print('\ndry run — nothing written')

if __name__ == '__main__':
    main('--apply' in sys.argv)
