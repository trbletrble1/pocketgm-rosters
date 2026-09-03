#!/usr/bin/env python3
"""
fix_2000_prospects — 2000's prospect ratings and ceilings. Three parts, two of
them DATA rather than formula.

  python3 tools/fix_2000_prospects.py --dry-run
  python3 tools/fix_2000_prospects.py

THE DIAGNOSIS, and it took three passes to reach because each one was incomplete
rather than wrong.

  1. The gradient is INVERTED. Prospect headroom against career length reads
     r = -0.16, and men who NEVER PLAYED take the largest gaps: median 14 against
     9 for twenty-year careers. 1986 reads +0.70 on the same measure and 1979,
     after its PFR fix, is monotone 8/5/10/14/22 by career value.

  2. 222 OF 1,024 PROSPECTS SIT AT EXACTLY RATING 40 — a pile-up on a clamp
     bound, not a distribution. Ratings came from two incompatible sources: a man
     who matched a Madden roster took his real POVR (PS2-era, so 80s and 90s),
     and a man who did not took `74 - 9.5*log(pick)` clamped to 40-93. At pick 195
     that formula yields 24, so every unmatched late pick lands on the floor. Hence
     22% of the class in the 40s and 13% at 80+, against 1-2% at both ends in every
     other file. Fourth instance of a quantile/scale problem being a POPULATION
     problem.

  3. `car_av` IS EMPTY FOR ALL 1,024 ROWS of wip/draft_picks_2001_2004.csv. It
     carries the largest weight in `draft_potential`'s raise, so the raise ran on
     partial data and the rating-derived baseline dominated — and that baseline is
     LARGEST for the lowest-rated men, who are the 222 on the clamp. That is the
     inversion, exactly.

     THE FORMULA WAS NEVER WRONG IN EITHER FILE. 1979 works because PFR gave it
     real wAV; 2000 failed because the column was blank. A field the formula
     weights heavily, present in the schema and empty in the data, errors nothing
     and inverts the output.

WHAT THIS DOES
  * fills `car_av` from nflverse career span, using the span-to-wAV medians
    MEASURED on the 1980-83 PFR classes where both signals exist;
  * maps both rating sources onto the pooled prospect band from the other nine
    files, order preserved, so the two scales align and nobody sits on a bound;
  * recomputes potential with `draft_potential`'s arithmetic UNCHANGED, and
    rebuilds growthType so the 50x invariant holds.

STATED WEAKNESS: career span correlates with wAV at +0.80, against 0.94 for the
seasons-started signal PFR gives directly. 2000's classes are therefore less
well-founded than 1979's and should not be read as equivalent.
"""
import json, csv, sys, os, re, math, unicodedata, collections, statistics as st, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

GAP_BY_BAND = {4: 18, 5: 8, 6: 4, 7: 4, 8: 5, 9: 1}
SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', '', s).split() if w not in SUF)

def span_to_av():
    """Median wAV per career-span band, measured on the 1980-83 PFR classes."""
    b = collections.defaultdict(list)
    for y in (1980, 1981, 1982, 1983):
        for r in csv.DictReader(open(repo('wip', f'draft_{y}_pfr.csv'))):
            av = int(r['career_av']) if r['career_av'].isdigit() else 0
            ls = int(r['last_season']) if r['last_season'].isdigit() else 0
            sp = (ls - y + 1) if ls else 0
            b[min(sp, 20)].append(av)
    out = {}
    for k in range(0, 21):
        v = [x for kk, vv in b.items() if abs(kk - k) <= 1 for x in vv] or [0]
        out[k] = st.median(v)
    return out

def nflverse_span(draft_rows):
    """Career span per drafted man, joined in FOUR TIERS.

    A name-only join is not enough twice over. nflverse holds 878 normalized
    names with more than one record, so `setdefault` silently keeps whichever
    came first — a father, a namesake, the wrong man. And it writes MIKE Vick,
    not Michael: the fifth forename variant this project has hit, after Billy
    Thompson, Timothy Stokes, Art Whittington and Deac Sanders, and this one
    would have given the FIRST OVERALL PICK of the class a zero-year career.
    That is precisely the error that looks fine in aggregate.

    Tiers: exact name (874); name plus draft year, which separates the
    duplicates (84); surname plus exact draft slot, which recovers Vick (9);
    surname plus year plus initial (2). 55 unresolved, and they look genuinely
    never-played — Bill Baber, Onomo Ojo, Rick Crowell."""
    by, bysur = collections.defaultdict(list), collections.defaultdict(list)
    p = os.path.join(sources(), 'nflverse', 'players.csv')
    for x in csv.DictReader(open(p, encoding='utf-8', errors='ignore')):
        k = norm(x['display_name'])
        by[k].append(x)
        if k:
            bysur[k.split()[-1]].append(x)
    def sp(x):
        a, b = x.get('rookie_season', ''), x.get('last_season', '')
        return (int(b) - int(a) + 1) if a.isdigit() and b.isdigit() else None
    out, tiers = {}, collections.Counter()
    for r in draft_rows:
        k = norm(r['pfr_player_name']); c = by.get(k, [])
        pick = None
        if len(c) == 1:
            pick, t = c[0], 'name'
        elif len(c) > 1:
            m = [q for q in c if q.get('draft_year') == r['season'] or (q.get('draft_pick') and q['draft_pick'] == r['pick'])]
            if len(m) == 1:
                pick, t = m[0], 'name + draft year'
        if pick is None:
            sur = k.split()[-1] if k else ''
            m = [q for q in bysur.get(sur, []) if q.get('draft_year') == r['season'] and q.get('draft_pick') == r['pick']]
            if len(m) == 1:
                pick, t = m[0], 'surname + draft slot'
            else:
                m = [q for q in bysur.get(sur, []) if q.get('draft_year') == r['season'] and norm(q['display_name'])[:1] == k[:1]]
                if len(m) == 1:
                    pick, t = m[0], 'surname + year + initial'
        if pick is None:
            tiers['unresolved'] += 1; continue
        tiers[t] += 1
        v = sp(pick)
        if v is not None:
            out[k] = v
    print('  nflverse join: ' + ', '.join(f'{k} {v}' for k, v in tiers.most_common()))
    return out

def pooled_band():
    """Prospect ratings from every file EXCEPT 2000 — the population 2000's own
    should look like. 1986 is in it deliberately: its gradient is the best we have."""
    out = []
    for y in ('1986', '2004', '2007', '2010', '2013', '2017', '2021', '2026'):
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] == 'Rookie':
                out.append(x['rating'])
    return sorted(out)

def at(band, rank, n):
    q = (rank + 0.5) / n                      # plotting position, as everywhere else
    return band[min(len(band) - 1, int(round(q * (len(band) - 1))))]

def build_growth(potential, rating, rng, n_slots=31):
    gt = [0] * n_slots
    need = (potential - rating) * 50
    if need > 0:
        slots = rng.sample(range(0, 20), min(8, max(1, need // 100 or 1)))
        per = need // len(slots)
        for i, s in enumerate(slots):
            gt[s] = per if i else need - per * (len(slots) - 1)
    for s in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))):
        gt[s] = -100 * rng.randint(1, 3)
    return gt

def main():
    dry = '--dry-run' in sys.argv
    d = json.load(open(repo('PGMRoster_2000.json')))
    pros = [x for x in d if x['teamID'] == 'Rookie']
    assert len(pros) == 1024, len(pros)
    before = {x['iden']: (x['rating'], x['potential']) for x in pros}

    # PART 1 — fill car_av from career span
    s2a = span_to_av()
    draft_rows = list(csv.DictReader(open(repo('wip', 'draft_picks_2001_2004.csv'))))
    spans = nflverse_span(draft_rows)
    draft = {norm(r['pfr_player_name']): r for r in draft_rows}
    assert all(not (r.get('car_av') or '').strip() for r in draft.values()), 'car_av is not empty — has this already run?'
    filled = 0
    for x in pros:
        k = norm(x['forename'] + ' ' + x['surname'])
        sp = spans.get(k)
        r = draft.get(k)
        if r is not None:
            r['car_av'] = str(int(round(s2a[min(sp or 0, 20)]))) if sp is not None else '0'
            filled += 1

    # PART 2 — both rating sources onto the pooled band, order preserved
    band = pooled_band()
    order = sorted(range(len(pros)), key=lambda i: (pros[i]['rating'], -(pros[i]['draftNum'] or 999)))
    newr = [0] * len(pros)
    for rank, i in enumerate(order):
        newr[i] = at(band, rank, len(pros))

    # PART 3 — potential from draft_potential's arithmetic, unchanged
    moved = 0
    for i, x in enumerate(pros):
        rng = random.Random(f"{norm(x['forename'] + ' ' + x['surname'])}|2000|fix")
        rating = newr[i]
        row = draft.get(norm(x['forename'] + ' ' + x['surname']), {})
        def num(k):
            try: return float((row.get(k) or 0) or 0)
            except (ValueError, TypeError): return 0.0
        b = GAP_BY_BAND.get(min(9, max(4, rating // 10)), 4)
        headroom = max(0, b + rng.gauss(0, b * 0.45))
        raise_ = (0.9 * min(6, num('probowls')) + 1.6 * min(4, num('allpro'))
                  + 0.09 * min(120, num('car_av')) + 0.30 * min(12, num('seasons_started')))
        pot = min(99, int(round(rating + min(40.0, headroom + raise_))))
        x['rating'], x['potential'] = rating, max(rating, pot)
        x['growthType'] = build_growth(x['potential'], rating, rng, 31)
        assert sum(v for v in x['growthType'] if v > 0) == (x['potential'] - rating) * 50
        moved += 1

    g = [x['potential'] - x['rating'] for x in pros]
    rt = sorted(x['rating'] for x in pros)
    pile = collections.Counter(rt).most_common(1)[0]
    print(f'car_av filled on {filled} of 1024 draft rows from nflverse career span')
    print(f'prospects rewritten: {moved};  ratings {rt[0]}-{rt[-1]}, '
          f'largest pile-up {pile[1]} men at {pile[0]} (was 222 at 40)')
    print(f'headroom: median {st.median(g):.0f}, p90 {sorted(g)[len(g)*9//10]}, max {max(g)}, '
          f'{sum(1 for x in pros if x["potential"] == 99)} at 99')
    if dry:
        print('\n--dry-run: nothing written'); return
    json.dump(d, open(repo('PGMRoster_2000.json'), 'w'), separators=(', ', ': '))
    w = csv.DictWriter(open(repo('wip', 'draft_picks_2001_2004.csv'), 'w', newline=''),
                       fieldnames=list(next(iter(draft.values())).keys()))
    w.writeheader(); w.writerows(draft.values())
    print('\nwrote PGMRoster_2000.json and wip/draft_picks_2001_2004.csv')

if __name__ == '__main__':
    main()
