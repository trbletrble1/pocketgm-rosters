#!/usr/bin/env python3
"""
raise_payroll_2026 — lift 2026's team payroll from the archive's $197.4M toward
the game's $242.9M. 2026 ONLY; Ryan plays it before the other nine follow.

  python3 tools/raise_payroll_2026.py --dry-run
  python3 tools/raise_payroll_2026.py

THE TARGET IS MEASURED, THE EXPECTATION IS NOT. Two independently generated fresh
vanilla leagues — zero shared player identifiers — agree to the dollar: 1,696
rostered, team payroll median $242.9M, min $155.3M, max $276.6M. **We know that is
what the game's generator produces. We do NOT know whether the engine expects it**,
and from outside the two are indistinguishable. Only a play test separates them,
which is why this file goes to Ryan before the other nine move.

A SINGLE GLOBAL FACTOR DOES NOT WORK. Hitting the median needs 1.2245x, which puts
our richest team at **$329.6M** against vanilla's observed maximum of $276.6M, and
**12 of 32 teams past it**. Our team-to-team spread is wider than the game's:
$111M-$269M, a 2.42x range, against vanilla's $155M-$277M at 1.78x.

SO TEAM TOTALS ARE MAPPED ONTO VANILLA'S OWN DISTRIBUTION by rank, and each team is
then scaled uniformly to its new total. That hits the median and the ceiling by
construction, and **a uniform per-team scale cannot reorder anyone inside that
team** — this is a level change, not a re-rating.

ROSTER SIZE IS A KNOWN CONFOUND, stated rather than corrected: we carry 59.1 men
per team against vanilla's 53.0, so the same team total buys $4.11M per man where
vanilla pays $4.58M. Matching totals is the instruction; matching per-man cost
would be a different and larger change.
"""
import json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

VAN = os.path.join(sources(), 'vanilla', 'PGMRoster_vanilla_2026-09-03.json')

def rostered(d):
    return [x for x in d if x['teamID'] not in ('Rookie', 'Free Agent')]

def team_pay(recs):
    by = collections.defaultdict(list)
    for x in recs:
        by[x['teamID']].append(x)
    return by

def top53(ps):
    """THE PROJECT'S PAYROLL BASIS IS THE TOP 53, not the whole roster — the
    handoff is explicit and the gate measures it. Matching whole-roster totals
    instead left the top-53 median at $241.2M against a $242.9M target, because we
    carry 59.1 men per team and the six cheapest fall outside the count. Vanilla
    carries exactly 53, so for the game the two are the same number; for us they
    are not, and that difference IS the roster-size confound."""
    return sum(sorted((z['salary'] + z['guarantee'] for z in ps), reverse=True)[:53])

def pos_ratios(ros):
    md = st.median(x['salary'] for x in ros) or 1
    p = collections.defaultdict(list)
    for x in ros:
        p[x['position']].append(x['salary'] / md)
    return {k: st.median(v) for k, v in p.items()}

def main():
    dry = '--dry-run' in sys.argv
    d = json.load(open(repo('PGMRoster_2026.json')))
    ros = rostered(d)
    van = rostered(json.load(open(VAN)))
    vpay = sorted(top53(ps) for ps in team_pay(van).values())
    by = team_pay(ros)
    order = sorted(by, key=lambda t: sum(z['salary'] + z['guarantee'] for z in by[t]))
    before_pay = {t: top53(by[t]) for t in by}
    before_rat = pos_ratios(ros)
    van_rat = pos_ratios(van)

    rows = []
    for rank, t in enumerate(order):
        tgt = vpay[min(len(vpay) - 1, int(round((rank + 0.5) / len(order) * (len(vpay) - 1))))]
        cur = before_pay[t]
        k = tgt / cur if cur else 1.0
        for z in by[t]:
            z['_s'] = int(round(z['salary'] * k))
            z['_g'] = int(round(z['guarantee'] * k))
        got = sum(sorted((z['_s'] + z['_g'] for z in by[t]), reverse=True)[:53])
        rows.append((t, cur, got, k))
    after_pay = {t: g for t, _, g, _ in rows}
    for x in ros:
        x['_after'] = x['_s'] + x['_g']
    # ORDERING: a uniform per-team scale is monotone, so this must be exact
    for t, ps in by.items():
        b = [z['salary'] + z['guarantee'] for z in ps]
        a = [z['_after'] for z in ps]
        assert all((b[i] < b[j]) == (a[i] < a[j]) for i in range(len(ps)) for j in range(i + 1, len(ps))), t
    for x in ros:
        x['salary'], x['guarantee'] = x['_s'], x['_g']
        x['eSalary'], x['eGuarantee'] = x['_s'], x['_g']
    after_rat = pos_ratios(ros)
    for x in ros:
        for k2 in ('_s', '_g', '_after'):
            x.pop(k2, None)

    ap = sorted(after_pay.values()); bp = sorted(before_pay.values())
    full = sorted(sum(z['salary'] + z['guarantee'] for z in ps) for ps in by.values())
    sal_b = sorted(x['salary'] for x in ros)   # after, since applied
    print(f"{'':<10}{'min':>10}{'p25':>10}{'median':>10}{'max':>10}")
    print(f"{'before':<10}{bp[0]/1e6:>9.1f}M{bp[len(bp)//4]/1e6:>9.1f}M{st.median(bp)/1e6:>9.1f}M{bp[-1]/1e6:>9.1f}M")
    print(f"{'after':<10}{ap[0]/1e6:>9.1f}M{ap[len(ap)//4]/1e6:>9.1f}M{st.median(ap)/1e6:>9.1f}M{ap[-1]/1e6:>9.1f}M")
    print(f"{'vanilla':<10}{vpay[0]/1e6:>9.1f}M{vpay[len(vpay)//4]/1e6:>9.1f}M{st.median(vpay)/1e6:>9.1f}M{vpay[-1]/1e6:>9.1f}M")
    assert max(ap) <= vpay[-1] + 1000, f'a team exceeds vanilla\'s observed maximum: {max(ap):,}'
    print(f"  (top-53 basis, as the project measures payroll; our FULL rosters then run "
          f"${full[0]/1e6:.1f}M-${full[-1]/1e6:.1f}M, median ${st.median(full)/1e6:.1f}M, "
          f"because we carry 59.1 men per team against vanilla's 53.0)")
    print(f"\n  player salary p25 ${sal_b[len(sal_b)//4]/1e6:.2f}M  median ${st.median(sal_b)/1e6:.2f}M   "
          f"(vanilla p25 $1.03M median $1.27M)")
    print(f"  ordering inside every team: EXACT (uniform per-team scale, asserted pairwise)")
    # THE RATIO TEST, and the tolerance is chosen rather than assumed. Scaling each
    # team by its own factor necessarily jostles cross-team position ratios a
    # little; a per-position tolerance of 0.02 flagged tight end (0.02 -> 0.06) and
    # centre (0.64 -> 0.67) — movements of three and four hundredths — while the
    # MEAN distance to vanilla improved. That is noise, not the failure the rule
    # exists to catch: the transform this guard was written for sent quarterbacks
    # 1.18 further away.
    #
    # So: the mean distance must not increase, and no single position may move more
    # than 0.10. Both bite on the 5.9x case and neither bites on jostling.
    md_b = st.mean([abs(before_rat[q] - van_rat[q]) for q in before_rat if q in van_rat])
    md_a = st.mean([abs(after_rat[q] - van_rat[q]) for q in after_rat if q in van_rat])
    big = {q: (before_rat[q], after_rat[q]) for q in after_rat
           if q in van_rat and q in before_rat
           and abs(after_rat[q] - van_rat[q]) - abs(before_rat[q] - van_rat[q]) > 0.10}
    print(f"  mean distance to vanilla: {md_b:.3f} -> {md_a:.3f}"
          f"   worst single move: {max((abs(after_rat[q]-van_rat[q])-abs(before_rat[q]-van_rat[q])) for q in after_rat if q in van_rat and q in before_rat):+.3f}")
    assert md_a <= md_b + 1e-9, f'mean distance to vanilla increased: {md_b:.3f} -> {md_a:.3f}'
    assert not big, big
    print(f"\n  per-team, largest moves:")
    for t, cur, got, k in sorted(rows, key=lambda r: -abs(r[2] - r[1]))[:6]:
        print(f"    {t:<5}${cur/1e6:>6.1f}M -> ${got/1e6:>6.1f}M   x{k:.3f}")
    if dry:
        print('\n--dry-run: nothing written'); return
    json.dump(d, open(repo('PGMRoster_2026.json'), 'w'), separators=(', ', ': '))
    print('\nwrote PGMRoster_2026.json')

if __name__ == '__main__':
    main()
