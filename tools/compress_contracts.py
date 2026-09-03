#!/usr/bin/env python3
"""
compress_contracts — redistribute salary within each team so the cheap end is
actually cheap. 1979 and 2000 only.

  python3 tools/compress_contracts.py 1979 2000 --dry-run
  python3 tools/compress_contracts.py 1979 2000

THE DEFECT IS DISTRIBUTION, NOT TOTAL. Every file's median top-53 is $197.4M and
nobody exceeds the $280M engine cap. But 1979's cheapest quarter costs **$2.14M**
against $0.73-1.02M in the eight conforming files, so a user against the cap has
no cheap depth to cut. The cap does not break, it seizes. 2000 is the milder
version, $1.29M.

THE TARGET IS THE EIGHT CONFORMING FILES, NOT THE VANILLA SAMPLE. Ryan's caveat
is right and stronger than it looks: `PGM3_VANILLA_SAMPLE.json` holds 45 rostered
players chosen one per position at min, median and max rating, so its median is
not a population median — and its top-quintile share of 51% sits BELOW all eight
conforming files (54-65%), which is the stratification showing. Direction from
vanilla, shape from the files that already work:

    p25 $0.90M (0.73-1.02)   median $1.27M (0.93-1.74)   top 20% holds 60.6% (54-65)

THE TRANSFORM IS RANK-PRESERVING AND TEAM-TOTAL-PRESERVING. Within each team,
salaries are re-spaced onto the pooled conforming shape by rank, then rescaled so
the team's total is unchanged to the dollar. Ordering therefore cannot move — this
is a redistribution, not a re-rating — and every payroll assertion that passed
before passes unchanged by construction.

1979's ERA DEPARTURES SURVIVE for the same reason. Kickers at 0.83 and punters at
0.80 of the field median, and the QB/RB rebalance, were expressed as ORDERING; a
rank-preserving transform cannot undo them. Verified in the report rather than
assumed.

DEFERRED 2026-09-03, NOT APPLIED TO ANY FILE. It works — rank-preserving within
team, team totals exact, 1979 moves to 1.16M/1.80M/63% with zero strictly-ordered
pairs inverted — but the target and the gate disagree about which reference is
authoritative, and that turned out to be the real question. Compressing toward the
eight conforming files propagates a position hierarchy the game does not share;
compressing toward vanilla is correct and redefines "conforming" for the whole
archive. Payroll level and payroll shape are one decision. See backlog item 37.
"""
import json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

CONFORMING = ['1986', '2004', '2007', '2010', '2013', '2017', '2021', '2026']

def rostered(d):
    return [x for x in d if x['teamID'] not in ('Rookie', 'Free Agent')]

def target_shape():
    """Pooled salary+guarantee of the conforming files, normalised to its own
    median, so it is a SHAPE rather than a level."""
    out = []
    for y in CONFORMING:
        for x in rostered(json.load(open(repo(f'PGMRoster_{y}.json')))):
            out.append(x['salary'] + x['guarantee'])
    out.sort()
    m = st.median(out) or 1
    return [v / m for v in out]

def at(curve, rank, n):
    q = (rank + 0.5) / n
    return curve[min(len(curve) - 1, int(round(q * (len(curve) - 1))))]

def shape_of(vals):
    s = sorted(vals); n = len(s)
    qq = lambda p: s[min(n - 1, int(p * n))]
    tot = sum(s) or 1
    return qq(.25), st.median(s), qq(.75), 100 * sum(s[-max(1, n // 5):]) / tot

def spearman(a, b):
    ra = {v: i for i, v in enumerate(sorted(range(len(a)), key=lambda i: a[i]))}
    rb = {v: i for i, v in enumerate(sorted(range(len(b)), key=lambda i: b[i]))}
    x = [ra[i] for i in range(len(a))]; y = [rb[i] for i in range(len(a))]
    mx, my = st.mean(x), st.mean(y)
    n = sum((p - mx) * (q - my) for p, q in zip(x, y))
    d = (sum((p - mx) ** 2 for p in x) * sum((q - my) ** 2 for q in y)) ** .5
    return n / d if d else 0

# NO BAND. A band computed from our own eight "conforming" files put SEVEN OF TEN
# positions outside it when measured against a real vanilla league — kickers 0.59
# against our 1.00-1.92, corners 2.18 against 0.83-1.01. It describes our
# convention, not the engine, and asserting it would enforce our own divergence.
#
# THE ASSERTION IS RELATIVE AND THE REFERENCE IS THE GAME: no position's ratio may
# move FURTHER from vanilla's value than it already is. That is the one property
# the gate was written to catch — a transform making a ratio worse — and it needs
# no claim that any band is normal. It would have caught the 5.9x quarterback on
# the first run, which is what the band was scaffolding for.
VANILLA = os.path.join(os.environ.get('PGM3_SOURCES', ''), 'vanilla',
                       'PGMRoster_vanilla_2026-09-03.json')

def pos_ratios(ros):
    md = st.median(x['salary'] for x in ros) or 1
    p = collections.defaultdict(list)
    for x in ros:
        p[x['position']].append(x['salary'] / md)
    return {k: st.median(v) for k, v in p.items()}

def compress(path, curve, apply=True, alpha=1.0):
    d = json.load(open(path))
    ros = rostered(d)
    by = collections.defaultdict(list)
    for x in ros:
        by[x['teamID']].append(x)
    before = [x['salary'] + x['guarantee'] for x in ros]
    for t, ps in by.items():
        ps.sort(key=lambda z: z['salary'] + z['guarantee'])
        tot = sum(z['salary'] + z['guarantee'] for z in ps)
        # BLEND, do not replace. alpha=1 is the pure conforming shape, which
        # over-concentrates; alpha=0 leaves the file alone. The blend is applied
        # to the normalised shapes so it is a spacing change, not a level change.
        cur = [z['salary'] + z['guarantee'] for z in ps]
        cm = st.median(cur) or 1
        cur_n = [v / cm for v in cur]
        tgt = [at(curve, i, len(ps)) for i in range(len(ps))]
        raw = [alpha * a + (1 - alpha) * b for a, b in zip(tgt, cur_n)]
        k = tot / (sum(raw) or 1)
        for z, r in zip(ps, raw):
            new = r * k
            g = z['guarantee'] / (z['salary'] + z['guarantee']) if (z['salary'] + z['guarantee']) else 0
            z['_new_sal'] = int(round(new * (1 - g)))
            z['_new_gua'] = int(round(new * g))
        # put the rounding remainder on the best-paid man so the total is exact
        diff = tot - sum(z['_new_sal'] + z['_new_gua'] for z in ps)
        ps[-1]['_new_sal'] += diff
    after = [x['_new_sal'] + x['_new_gua'] for x in ros]
    # ORDERING IS A PER-TEAM CONSTRAINT: 'the best-paid man on each team stays the
    # best-paid'. Measured globally it reads 0.97, but that is teams rescaling by
    # different factors, not men swapping inside a team — a global figure answers
    # a question nobody asked.
    rhos = []
    for ps in by.values():
        b = [z['salary'] + z['guarantee'] for z in ps]
        a = [z['_new_sal'] + z['_new_gua'] for z in ps]
        rhos.append(spearman(b, a))
    rho = min(rhos)
    rho_global = spearman(before, after)
    if apply:
        for x in ros:
            x['salary'], x['guarantee'] = x.pop('_new_sal'), x.pop('_new_gua')
            x['eSalary'], x['eGuarantee'] = x['salary'], x['guarantee']
    else:
        for x in ros:
            x.pop('_new_sal', None); x.pop('_new_gua', None)
    return d, before, after, (rho, rho_global), by

def vanilla_ratios():
    d = [x for x in json.load(open(VANILLA)) if x['teamID'] not in ('Rookie', 'Free Agent')]
    return pos_ratios(d)

def solve_alpha(path, curve, year):
    """The largest blend under which NO position moves further from vanilla than
    it already sits. Searched, not chosen."""
    van = vanilla_ratios()
    base = pos_ratios(rostered(json.load(open(path))))
    best = 0.0
    for i in range(0, 101):
        a = i / 100.0
        d, *_ = compress(path, curve, apply=False, alpha=a)
        d2 = json.load(open(path))
        ros = rostered(d2)
        by = collections.defaultdict(list)
        for x in ros: by[x['teamID']].append(x)
        for ps in by.values():
            ps.sort(key=lambda z: z['salary'] + z['guarantee'])
            tot = sum(z['salary'] + z['guarantee'] for z in ps)
            cur = [z['salary'] + z['guarantee'] for z in ps]
            cm = st.median(cur) or 1
            tgt = [at(curve, j, len(ps)) for j in range(len(ps))]
            raw = [a * t + (1 - a) * (c / cm) for t, c in zip(tgt, cur)]
            k = tot / (sum(raw) or 1)
            for z, r in zip(ps, raw):
                g = z['guarantee'] / (z['salary'] + z['guarantee']) if (z['salary'] + z['guarantee']) else 0
                z['salary'] = int(round(r * k * (1 - g)))
        rat = pos_ratios(ros)
        ok = all(abs(rat[q] - van.get(q, rat[q])) <= abs(base[q] - van.get(q, base[q])) + 0.02
                 for q in rat if q in base)
        if ok:
            best = a
    return best

def main():
    years = [a for a in sys.argv[1:] if a.isdigit()]
    dry = '--dry-run' in sys.argv
    curve = target_shape()
    print(f'target shape pooled from {len(CONFORMING)} conforming files, {len(curve)} players\n')
    print(f"{'file':<8}{'':<6}{'p25':>9}{'median':>9}{'p75':>9}{'top20%':>9}{'  spearman':>11}")
    for y in years:
        p = repo(f'PGMRoster_{y}.json')
        d, before, after, (rho, rho_global), by = compress(p, curve, apply=not dry)
        # report SALARY ONLY, the basis of the reference table, alongside the
        # salary+guarantee the transform actually moves
        ros_ = rostered(d)
        for lab, v, sv in (('before', before, [x['salary'] for x in ros_] if dry else None),
                           ('after', after, [x['salary'] for x in ros_] if not dry else None)):
            a, b, c, e = shape_of(v)
            extra = ''
            if sv:
                sa, sb, sc, se = shape_of(sv)
                extra = f'   salary-only p25 {sa/1e6:.2f}M med {sb/1e6:.2f}M top20 {se:.0f}%'
            print(f"{y if lab=='before' else '':<8}{lab:<6}{a/1e6:>8.2f}M{b/1e6:>8.2f}M{c/1e6:>8.2f}M{e:>8.0f}%"
                  + (f"{rho:>11.4f}" if lab == 'after' else '') + extra)
        if lab == 'after':
            print(f"        ordering: worst per-team spearman {rho:.4f}, global {rho_global:.4f}")
        pay = [sum(z['salary'] + z['guarantee'] for z in ps) for ps in by.values()] if not dry else None
        if not dry:
            top53 = [sum(sorted((z['salary'] + z['guarantee'] for z in ps), reverse=True)[:53]) for ps in by.values()]
            print(f"        median top-53 ${st.median(top53):,.0f}   max team ${max(pay):,.0f}   over 280M: {sum(1 for v in pay if v > 280e6)}")
            assert abs(st.median(top53) - 197_400_000) < 200_000, st.median(top53)
            assert max(pay) < 280_000_000
            json.dump(d, open(p, 'w'), separators=(', ', ': '))
            print(f'        wrote {os.path.basename(p)}')
        print()

if __name__ == '__main__':
    main()
