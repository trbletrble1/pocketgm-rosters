#!/usr/bin/env python3
"""fix_olb_coverage.py — zero OLB manCover/zoneCover in the four files that
carry fill there.

Five of nine published files gate these two fields off entirely for OLB:
2000, 2004, 2007, 2017 and 2026 hold them at zero for every OLB. That is the
convention. The other four carry values of 1 to 3 against an MLB range of
38 to 92 at the same positions -- not low ratings, FILL.

Identical vocabulary in all four (manCover in {1,2,3}, zoneCover in {1}),
which is what identifies 1986's 46-of-143 and 2010's 6-of-153 as the same
defect partially applied rather than something else.

NOT populated with real values. No source has OLB coverage for these eras, and
replacing fill with better-looking fill is what this project refuses.

CUT ON THE FILL VOCABULARY, NOT ON THE POSITION. A first version zeroed every
OLB record and destroyed real data: the PROSPECT cohort carries genuine
coverage values (45-76, the plausible range) mixed in with the fill, and 2010's
prospect zoneCover is entirely real -- 58 to 70, not a single 1. Only values in
{1,2,3} are fill; anything at 38 or above is a rating and is left alone.

    python3 fix_olb_coverage.py --dry-run | --apply
"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_2026 as B

FILES = ['PGMRoster_1986.json', 'PGMRoster_2010.json',
         'PGMRoster_2013.json', 'PGMRoster_2021.json']
FIELDS = ('manCover', 'zoneCover')
FILL_MAX = 3          # the fill vocabulary; MLB at the same positions runs 38-92

def main(apply_it):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fn in FILES:
        path = os.path.join(root, fn)
        recs = json.load(open(path))
        before = json.loads(json.dumps(recs))
        n = 0
        for r in recs:
            if r['position'] != 'OLB': continue
            for a in FIELDS:
                v = r.get(a, 0)
                if 0 < v <= FILL_MAX:
                    r[a] = 0; n += 1
        # nothing but those two fields, on OLB records, may move
        assert len(recs) == len(before)
        for x, y in zip(before, recs):
            d = [k for k in x if x[k] != y[k]]
            if not d: continue
            assert x['position'] == 'OLB', f'{fn}: non-OLB record changed'
            assert set(d) <= set(FIELDS), f'{fn}: unexpected field moved: {d}'
        left = sum(1 for r in recs if r['position'] == 'OLB'
                   and any(0 < r.get(a, 0) <= FILL_MAX for a in FIELDS))
        assert left == 0, f'{fn}: {left} OLB records still carry fill'
        kept = sum(1 for r in recs if r['position'] == 'OLB'
                   and any(r.get(a, 0) > FILL_MAX for a in FIELDS))
        print(f'   {fn[10:14]}  {n:4d} fill values zeroed   real values preserved: {kept}')
        if apply_it:
            with open(path, 'w') as f: json.dump(recs, f, separators=(',', ':'))
    print('   ASSERTED: only manCover/zoneCover, only on OLB records, counts unchanged')
    print('WRITTEN' if apply_it else 'dry run — nothing written')

if __name__ == '__main__':
    main('--apply' in sys.argv)
