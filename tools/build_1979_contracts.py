#!/usr/bin/env python3
"""
build_1979_contracts — salary, guarantee, length and the three personality
fields for the 1,408-man 1979 spine.

  python3 tools/build_1979_contracts.py            # writes wip/contracts_1979.csv
  python3 tools/build_1979_contracts.py --selftest

THE RULE (handoff, "On era scaling"): era accuracy governs everything EXCEPT the
dollar scale. Ratios, orderings and who is paid more than whom are 1979's; the
scale alone comes from the engine, because the engine has no cap field and cannot
know what year it is. So this builds era-real RELATIVITIES and then applies one
uniform factor to land the median top-53 on the $197.4M published constant.

MEASURED, not invented:
  * length by years pro — the published six's own median: 4 for a first-year man
    counting down to 1, then short veteran deals. A rookie deal running out.
  * guarantee / salary by REMAINING length — the published six's median at each
    length. `guarantee` is money still owed, so it collapses as a deal runs down.
  * the personality fields — greed, loyalty and ambition correlate with NOTHING
    in the published files (|r| < 0.02 against rating, age and salary). They are
    reproduced as a distribution, deterministically, and carry no per-player
    meaning here because they carry none there.

SOURCED:
  * the floor. The 1977 collective bargaining agreement — the one in force in
    1979 — set minimum salaries of $12,500 for rookies and $13,000 for veterans.

TOP_RATIO, how far the best-paid man sits above the median, is CONSTRAINED
rather than chosen. It started as a judgement at 10x — more compressed than the
published six (17.8x to 36.9x), this project's 1986 build (26.9x) or its 2000
build (12.8x), which is the era claim: 1979 had no free agency and the Rozelle
Rule held the top of the market down. But 10x put Pittsburgh at $293.3M and
Dallas at $285.5M, over the $280M engine cap, because payroll tracks team quality
and those were the two best teams in the league. Two constraints then fix it:

    no team may exceed the $280M engine cap
    team payroll spread must sit in the published max/median band, 1.23 to 1.38

    10x -> max team $293.3M, spread 1.49   TWO TEAMS OVER
     8x -> max team $272.6M, spread 1.38   clear, at the band's top edge
     6x -> max team $254.2M, spread 1.29

Hand-setting it broke twice — 10x, then 8x again the moment the running-back
multiplier was raised to fix the pay table — so it is now SOLVED against a
$275M ceiling every run. The median top-53 holds at $197.4M at every value, so
the payroll constant does not choose between them: the engine cap does.

ALSO NOTED: the 1986 build pays kickers 1.40x the file median and punters 1.22x,
against the published six's 1.36x and 1.16x — it inherited the modern market's
specialist premium wholesale. In 1979 kickers and punters were paid at or below
the average. That is the one place this build deliberately departs from the
published shape.
"""
import csv, sys, os, collections, statistics as st, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

TARGET_MEDIAN_TOP53 = 197_400_000
ENGINE_CAP = 280_000_000             # hardcoded in the engine; no cap field exists
CAP_HEADROOM = 275_000_000           # the ceiling this build actually targets
TOP_RATIO = None                     # SOLVED against CAP_HEADROOM, never set by hand
FLOOR_RATIO = 0.24                   # $13,000 CBA veteran minimum over a low-$60,000s average

# measured from the published six
LENGTH_BY_YEARS = [4, 3, 2, 1, 1, 1, 1, 2, 1, 1]
GUARANTEE_BY_LENGTH = {1: 0.06, 2: 0.09, 3: 0.08, 4: 0.21, 5: 1.25, 6: 0.44, 7: 0.32}

# era-real relativities. QB is the premium position in any era, but 1979's
# marquee earners were quarterbacks AND running backs — a first pass at QB 2.00
# put NINE quarterbacks ahead of Walter Payton, which is a modern league's
# pay table, not this one. The wide receiver was worth less than now; the kicker
# and the punter were near the bottom, which is where the published files do NOT
# put them.
POS_MULT = {'QB': 1.75, 'RB': 1.35, 'DE': 1.05, 'OT': 1.05, 'DT': 1.00, 'MLB': 1.00,
            'OLB': 0.98, 'C': 0.95, 'OG': 0.95, 'CB': 0.95, 'TE': 0.92, 'WR': 0.92,
            'S': 0.90, 'K': 0.65, 'P': 0.60}
ROOKIE_SLOT = {0: 0.55, 1: 0.75}     # 1979 rookies signed slotted deals, not market ones

def rel_salary(rating, pos, yrs, median_rating, k):
    import math
    v = math.exp(k * (rating - median_rating))
    return max(FLOOR_RATIO, v) * POS_MULT.get(pos, 1.0) * ROOKIE_SLOT.get(yrs, 1.0)

def solve_top_ratio(rows):
    """The largest compression ratio that still keeps every team under the engine
    cap. Solved, not chosen — hand-setting it broke twice: 10x put Pittsburgh at
    $293M, and 8x broke again the moment the running-back multiplier was raised
    to fix the pay table. The constraint is what matters, so the constraint is
    what the code holds."""
    global TOP_RATIO
    lo, hi = 2.0, 14.0
    for _ in range(40):
        TOP_RATIO = (lo + hi) / 2
        out = build(rows, quiet=True, solve_ratio=False)
        by = collections.defaultdict(list)
        for x in out:
            by[x['team']].append(x['salary'] + x['guarantee'])
        if max(sum(v) for v in by.values()) > CAP_HEADROOM:
            hi = TOP_RATIO
        else:
            lo = TOP_RATIO
    TOP_RATIO = lo
    return lo

def solve_k(rows, med_rating):
    """TOP_RATIO is a claim about the FINISHED distribution, so the rating
    exponent is solved against the final max/median — position multipliers and
    rookie slotting included. Setting it on the rating curve alone let QB's 2.00
    stack on top and shipped 20.5x while the docstring said 10x."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        k = (lo + hi) / 2
        v = [rel_salary(int(r['rating']), r['pgm3_pos'], int(r['years_pro']), med_rating, k)
             for r in rows]
        if max(v) / st.median(v) < TOP_RATIO:
            lo = k
        else:
            hi = k
    return k

def spread(n, pool_sorted):
    """Reproduce a marginal distribution deterministically across n players."""
    return [pool_sorted[min(len(pool_sorted) - 1, int(round(i / max(1, n - 1) * (len(pool_sorted) - 1))))]
            for i in range(n)]

def published_personality():
    out = collections.defaultdict(list)
    for y in ['2004', '2007', '2010', '2013', '2017', '2021']:
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] not in ('Rookie', 'Free Agent'):
                for f in ('greed', 'loyalty', 'ambition'):
                    out[f].append(x[f])
    for f in out:
        out[f].sort()
    return out

def selftest():
    ok = 0
    try:                     # the scale factor must actually be solved for, not assumed
        rows = [{'rating': 70, 'pgm3_pos': 'QB', 'years_pro': 3, 'team': 't%d' % (i // 50)}
                for i in range(1400)]
        s = build(rows, quiet=True)
        med = team_median_top53(s)
        assert abs(med - TARGET_MEDIAN_TOP53) / TARGET_MEDIAN_TOP53 < 0.02, med
        ok += 1; print(f'  ok: a flat roster still lands on the $197.4M constant ({med:,.0f})')
    except AssertionError as e:
        print(f'  FAIL: scale not solved ({e})')
    try:                     # a kicker must NOT come out above the median, the 1986 defect
        rows = ([{'rating': 75, 'pgm3_pos': 'K', 'years_pro': 5, 'team': 'a'}] +
                [{'rating': 75, 'pgm3_pos': 'WR', 'years_pro': 5, 'team': 'a'} for _ in range(50)])
        s = build(rows, quiet=True)
        assert s[0]['salary'] < st.median([x['salary'] for x in s[1:]]), 'kicker priced above the field'
        ok += 1; print('  ok: an equally rated kicker is paid BELOW the field, not above it')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok

def team_median_top53(sal):
    by = collections.defaultdict(list)
    for x in sal:
        by[x['team']].append(x['salary'] + x['guarantee'])
    return st.median([sum(sorted(v, reverse=True)[:53]) for v in by.values()])

def build(rows, quiet=False, solve_ratio=True):
    if solve_ratio:
        solve_top_ratio(rows)
    med_rating = st.median([int(r['rating']) for r in rows])
    k = solve_k(rows, med_rating)
    out = []
    for r in rows:
        y = int(r['years_pro']); rat = int(r['rating']); pos = r['pgm3_pos']
        L = LENGTH_BY_YEARS[min(y, len(LENGTH_BY_YEARS) - 1)]
        out.append({'team': r['team'], 'name': r.get('name', ''), 'pos': pos, 'rating': rat,
                    'length': L, 'rel': rel_salary(rat, pos, y, med_rating, k),
                    'gr': GUARANTEE_BY_LENGTH[L]})
    # solve the single uniform factor
    lo, hi = 1.0, 1e9
    for _ in range(80):
        mid = (lo + hi) / 2
        for x in out:
            x['salary'] = int(round(x['rel'] * mid)); x['guarantee'] = int(round(x['salary'] * x['gr']))
        if team_median_top53(out) < TARGET_MEDIAN_TOP53:
            lo = mid
        else:
            hi = mid
    if not quiet:
        print(f'TOP_RATIO solved against the ${CAP_HEADROOM/1e6:.0f}M ceiling: {TOP_RATIO:.2f}x')
        print(f'uniform scale factor solved: {mid:,.0f}  ->  median top-53 {team_median_top53(out):,.0f}')
    return out

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 2 else 1)
    rows = list(csv.DictReader(open(repo('wip', 'potential_1979.csv'))))
    assert len(rows) == 1408
    out = build(rows)
    pp = published_personality()
    for f in ('greed', 'loyalty', 'ambition'):
        for x, v in zip(out, spread(len(out), pp[f])):
            x[f] = v
    w = csv.writer(open(repo('wip', 'contracts_1979.csv'), 'w', newline=''))
    w.writerow(['team', 'name', 'pos', 'rating', 'salary', 'guarantee', 'length',
                'eSalary', 'eGuarantee', 'eLength', 'greed', 'loyalty', 'ambition'])
    for x, r in zip(out, rows):
        w.writerow([x['team'], r['name'], x['pos'], x['rating'], x['salary'], x['guarantee'],
                    x['length'], x['salary'], x['guarantee'], x['length'],
                    x['greed'], x['loyalty'], x['ambition']])
    v = sorted(x['salary'] for x in out)
    print(f"salary: min {v[0]:,}  p25 {v[len(v)//4]:,}  median {st.median(v):,.0f}  "
          f"p90 {v[len(v)*9//10]:,}  max {v[-1]:,}   max/med {v[-1]/st.median(v):.1f}")
    print(f'wrote wip/contracts_1979.csv: {len(out)} contracts')
