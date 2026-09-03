#!/usr/bin/env python3
"""
update_2026_opener — the two real changes in Ryan's September 1 change set.

  python3 tools/update_2026_opener.py --dry-run     # report, write nothing
  python3 tools/update_2026_opener.py

THE CHANGE SET WAS FIVE AND IS TWO. Checked against the file rather than applied:
Broderick Jones is already DAL, Kaleb Johnson already GB, and Odell Beckham Jr. is
already in the file at NYG on 73. Only two changes are real.

  1. ADD Aaron Donald, LAR, DE, rating 92.
  2. MOVE Gervon Dexter Sr. ATL -> CHI. teamID only.

DONALD'S RATING: 92, and the hand-set and the fit AGREE. Ryan set 92 by judgement —
he is 35, hasn't played since 2023, and the fitted decay was expected to diverge.
It does not. He is 98 in our 2017 file at 26 and 97 in 2021 at 30; among DE/DT
aged 29-31 across the published six (n=310) that is the 98.7th percentile, and
that percentile among DE/DT aged 34-36 (n=47) reads exactly 92. Scale check:
2026 already carries Khalil Mack at 35 on 94 and DeMarcus Lawrence at 34 on 92.

  STATED LIMIT: the age curve is built from men who KEPT PLAYING, so it cannot
  see a two-year layoff, and no file we hold measures one. 92 is an UPPER BOUND.
  Same survivorship trap as the 1979 age curve.

HIS ATTRIBUTES are his own 2021 record's, shifted by a single uniform k across the
live attributes so the recomputed overall lands on 92 — the stage-8 pattern. Not
invented, and not drawn from a position median.

HIS APPEARANCE is the registry's `aaron donald|DE`, which is in `_verified_keys`
— Ryan's own hand edit from an earlier season, and per the registry's README a
hand edit outranks everything. There are TWO entries, `|DT` and `|DE`, with
different faces; only the DE one is verified, and DE is also the position that
puts him on Garrett's line. The archive agrees with it independently: 10
appearances, unanimously dark, skin 3 in nine of them.

  THE RFM PLACEHOLDER STAYS OUT. `donaldAaron_10852` carries an untouched head
  reading skin 2 / ethnicity H and has tried to enter two files already. Verified
  again here: the export excludes it and he is absent from all 2,954 registry
  rows. Note the guard is in `cmd_dump`, NOT in `records()` — the raw generator
  still yields him — so the comment above EXCLUDE_IDS is wrong about its own
  location. Fixed in the same commit.
"""
import json, sys, os, copy, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

TARGET = 92
# ONE DEPARTURE FROM 'teamID ONLY', and it is forced by the move rather than a
# second change. Dexter carried number 9 from Atlanta; Chicago already has Jahdae
# Walker on 9, and the roster gate fails on a duplicate within a team. 99 is free
# on Chicago and is the number he actually wears there. Reported rather than
# folded in: the instruction was teamID only, and this is teamID plus the jersey
# the move makes impossible to keep.
MOVES = {('Gervon', 'Dexter Sr.'): ('ATL', 'CHI', 99)}
DONALD_FACE = ["Head4b", "Eyes1b", "Hair1p", "Beard1d", "Eyebrows1b",
               "Nose4b", "Mouth4b", "Glasses1e", "Clothes2"]
IDEN = 'A2D0C1E4-5B36-47AF-9C10-DA1979E00092'      # not present in the file; asserted below

def overall(rec, pos, W):
    names, co = W[pos][0], W[pos][1]
    return sum(rec[a] * c for a, c in zip(names, co)) + (co[-1] if len(co) == len(names) + 1 else 0)

def build_donald(d21, W, template):
    src = [x for x in d21 if x['forename'] == 'Aaron' and x['surname'] == 'Donald'][0]
    x = copy.deepcopy(src)
    x['teamID'], x['position'], x['age'] = 'LAR', 'DE', 35
    x['draftSeason'], x['draftNum'] = 2014, 13          # 2014, 13th overall; Mack is the same vintage
    names = W['DE'][0]
    # Search on the INTEGER attributes the record will actually carry. Solving on
    # the continuous shift and rounding afterwards landed him on 91, because the
    # rounding of thirty attributes moves the computed overall by about a point.
    def shifted(k):
        return {a: int(round(max(1, min(99, x[a] + k)))) for a in names if x.get(a, 0)}
    best = None
    for i in range(-4000, 4001):
        k = i / 100.0
        cand = dict(x); cand.update(shifted(k))
        o = int(round(overall(cand, 'DE', W)))
        d = abs(o - TARGET)
        if best is None or d < best[0] or (d == best[0] and abs(k) < abs(best[1])):
            best = (d, k)
        if d == 0 and abs(k) > 0:
            break
    k = best[1]
    x.update(shifted(k))
    # A uniform shift alone cannot land on 92 — thirty attributes round together,
    # so the computed overall steps from 91 to 93 with nothing between. Close the
    # last point with a SINGLE one-step nudge on one attribute, chosen as the
    # smallest-weight one that does the job, so the shape of his 2021 profile is
    # disturbed as little as possible.
    if int(round(overall(x, 'DE', W))) != TARGET:
        co = dict(zip(names, W['DE'][1]))
        for a in sorted((a for a in names if x.get(a, 0)), key=lambda a: abs(co[a])):
            for step in (1, -1, 2, -2):
                v = x[a]
                nv = int(max(1, min(99, v + step)))
                if nv == v:
                    continue
                x[a] = nv
                if int(round(overall(x, 'DE', W))) == TARGET:
                    break
                x[a] = v
            if int(round(overall(x, 'DE', W))) == TARGET:
                break
    assert int(round(overall(x, 'DE', W))) == TARGET, \
        f"could not land on {TARGET}; got {int(round(overall(x, 'DE', W)))}"
    x['rating'] = int(round(overall(x, 'DE', W)))
    x['potential'] = x['rating']                         # 12 years pro: the 2026 curve gives 0 headroom
    x['growthType'] = list(template['growthType'])
    x['appearance'] = list(DONALD_FACE)
    x['iden'] = IDEN
    x['salary'], x['guarantee'], x['length'] = 3_618_133, 1_982_230, 2
    x['eSalary'], x['eGuarantee'], x['eLength'] = 3_618_133, 1_982_230, 2
    return x

def main():
    dry = '--dry-run' in sys.argv
    before = json.load(open(repo('PGMRoster_2026.json')))
    W = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']
    d21 = json.load(open(repo('PGMRoster_2021.json')))
    assert not [x for x in before if x['forename'] == 'Aaron' and x['surname'] == 'Donald'], \
        'Aaron Donald is already in the file'
    assert IDEN not in {x['iden'] for x in before}, 'iden collision'
    zero = next(x for x in before if x['potential'] == x['rating'] and x['teamID'] not in ('Rookie', 'Free Agent'))

    after = copy.deepcopy(before)
    moved = 0
    for x in after:
        key = (x['forename'], x['surname'])
        if key in MOVES:
            frm, to, num = MOVES[key]
            assert x['teamID'] == frm, f'{key} is on {x["teamID"]}, expected {frm}'
            taken = {q['teamNum'] for q in after if q['teamID'] == to and q is not x}
            assert x['teamNum'] in taken, f'{key} number {x["teamNum"]} is free on {to} — do not change it'
            assert num not in taken, f'{num} is taken on {to}'
            x['teamID'] = to; x['teamNum'] = num; moved += 1
    assert moved == len(MOVES), f'{moved} moved, expected {len(MOVES)}'
    donald = build_donald(d21, W, zero)
    after.append(donald)

    # NOTHING ELSE MOVES, asserted field by field
    B = {x['iden']: x for x in before}
    diffs = collections.Counter()
    for x in after:
        b = B.get(x['iden'])
        if b is None:
            continue
        for k in x:
            if x[k] != b[k]:
                diffs[(x['forename'] + ' ' + x['surname'], k)] += 1
    assert set(diffs) == {('Gervon Dexter Sr.', 'teamID'), ('Gervon Dexter Sr.', 'teamNum')}, \
        f'unexpected changes: {dict(diffs)}'
    assert len(after) == len(before) + 1

    print(f'records {len(before)} -> {len(after)}')
    print(f'  moved: Gervon Dexter Sr. ATL -> CHI, and number 9 -> 99 because Chicago')
    print(f'         already has Jahdae Walker on 9. {len(diffs)} fields changed in the whole file.')
    print(f"  added: Aaron Donald  LAR DE  rating {donald['rating']}  potential {donald['potential']}  age 35")
    print(f"         attributes = his 2021 record shifted by one uniform k; face = the verified DE entry")
    lar = [x for x in after if x['teamID'] == 'LAR']
    print(f"  LAR: {len(lar)} players, payroll {sum(x['salary'] + x['guarantee'] for x in lar):,} "
          f"(engine cap 280,000,000)")
    assert sum(x['salary'] + x['guarantee'] for x in lar) < 280_000_000, 'LAR over the engine cap'
    if dry:
        print('\n--dry-run: nothing written'); return
    # MATCH THE STORED FORMATTING. The file is one line of compact JSON; writing
    # it with indent=1 produced a 252,866-line diff for a two-record change and
    # made the review worthless.
    json.dump(after, open(repo('PGMRoster_2026.json'), 'w'), separators=(', ', ': '))
    print('\nwrote PGMRoster_2026.json')

if __name__ == '__main__':
    main()
