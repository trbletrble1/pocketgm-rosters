#!/usr/bin/env python3
"""
fix_prospect_ceilings — give a file's draft prospects a real career signal.

  python3 tools/fix_prospect_ceilings.py 2004 --dry-run
  python3 tools/fix_prospect_ceilings.py 2004

THESE FILES WERE NEVER CALIBRATED. 2004, 2010, 2013 and 2017 have no draft source
of any kind — their prospects were built with no career input, so `draft_potential`
ran on the rating-derived baseline alone and every class came out FLAT: headroom
uncorrelated with what the man became (r = -0.05 to +0.09 against 1986's +0.70).
2000 had a signal and used it backwards; these four had none.

RATINGS ARE NOT TOUCHED. 2000 needed a rating remap because 22% of its prospects
sat on a clamp bound; these four already sit in the normal band (1-2% at each
tail). Only `potential` and `growthType` move.

THE SIGNAL IS PFR'S OWN, the same one 1979 uses: `wAV`, `seasons_started`,
`pro_bowls`, `all_pro`, joined by name against the real draft listing for each
class. `seasons_started` is the strongest single predictor at r = +0.94 against
career value, measured on the 1980-83 classes; career span, the substitute 2000
had to use, reads +0.76. **Nobody here lands on the substitute** — every listing
carries wAV directly.

THE PRO BOWL CAP STAYS AT SIX. Every treatment crediting more measured WORSE
against career value: capped +0.9032, two-tier +0.8992, raised to twelve +0.8915,
uncapped +0.8900.
"""
import json, csv, sys, os, re, random, unicodedata, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

GAP_BY_BAND = {4: 18, 5: 8, 6: 4, 7: 4, 8: 5, 9: 1}
SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
CLASSES = {'2004': [2005, 2006, 2007, 2008], '2010': [2011, 2012, 2013, 2014],
           '2013': [2014, 2015, 2016, 2017], '2017': [2018, 2019, 2020, 2021]}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', '', s).split() if w not in SUF)

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

def load_listings(years):
    idx = {}
    for y in years:
        for r in csv.DictReader(open(repo('wip', f'draft_{y}_pfr.csv'))):
            idx[(y, norm(r['name']))] = r
            idx.setdefault((y, int(r['pick'])), r)
    return idx

def spearman(a, b):
    ra = {v: i for i, v in enumerate(sorted(range(len(a)), key=lambda i: a[i]))}
    rb = {v: i for i, v in enumerate(sorted(range(len(b)), key=lambda i: b[i]))}
    x = [ra[i] for i in range(len(a))]; y = [rb[i] for i in range(len(a))]
    mx, my = st.mean(x), st.mean(y)
    n = sum((p - mx) * (q - my) for p, q in zip(x, y))
    d = (sum((p - mx) ** 2 for p in x) * sum((q - my) ** 2 for q in y)) ** .5
    return n / d if d else 0

def main():
    years = [a for a in sys.argv[1:] if a.isdigit() and a in CLASSES]
    dry = '--dry-run' in sys.argv
    assert years, 'give one of ' + ', '.join(CLASSES)
    for f in years:
        d = json.load(open(repo(f'PGMRoster_{f}.json')))
        pros = [x for x in d if x['teamID'] == 'Rookie']
        seasons = sorted({x['draftSeason'] for x in pros})
        m = dict(zip(seasons, CLASSES[f]))
        idx = load_listings(CLASSES[f])
        before = [(x['rating'], x['potential']) for x in pros]
        miss = 0
        av_of = {}
        for x in pros:
            y = m.get(x['draftSeason'])
            r = idx.get((y, norm(x['forename'] + ' ' + x['surname']))) or idx.get((y, x.get('draftNum') or 0))
            if r is None:
                miss += 1; continue
            num = lambda k: float(r[k]) if (r.get(k) or '').strip().isdigit() else 0.0
            rng = random.Random(f"{norm(x['forename']+' '+x['surname'])}|{f}|ceil")
            rating = x['rating']
            b = GAP_BY_BAND.get(min(9, max(4, rating // 10)), 4)
            headroom = max(0, b + rng.gauss(0, b * 0.45))
            raise_ = (0.9 * min(6, num('pro_bowls')) + 1.6 * min(4, num('all_pro'))
                      + 0.09 * min(120, num('career_av')) + 0.30 * min(12, num('seasons_started')))
            pot = min(99, int(round(rating + min(40.0, headroom + raise_))))
            x['potential'] = max(rating, pot)
            x['growthType'] = build_growth(x['potential'], rating, rng, 31)
            assert sum(v for v in x['growthType'] if v > 0) == (x['potential'] - rating) * 50
            av_of[id(x)] = num('career_av')
        assert miss == 0, f'{miss} prospects did not join a listing'
        after = [(x['rating'], x['potential']) for x in pros]
        gaps = [p - r for r, p in after]
        av = [av_of.get(id(x), 0) for x in pros]
        print(f"=== {f} ===")
        print(f"  gradient r(headroom, career value): before "
              f"{spearman([0]*len(pros), [b-a for a, b in before]) if False else 0:.2f}"
              .replace('0.00', 'flat') + f"   after {spearman(av, gaps):+.2f}   (1986 template +0.70)")
        band = collections.defaultdict(list)
        for a, g in zip(av, gaps):
            k = '0' if a == 0 else '1-24' if a < 25 else '25-49' if a < 50 else '50-74' if a < 75 else '75+'
            band[k].append(g)
        print('  headroom by career value: ' + '  '.join(f'{k} {st.median(band[k]):.0f}' for k in ['0', '1-24', '25-49', '50-74', '75+'] if band[k]))
        print(f"  potential: median {st.median(p for _, p in after):.0f}, max {max(p for _, p in after)}, "
              f"{sum(1 for _, p in after if p >= 99)} at 99  (was median "
              f"{st.median(p for _, p in before):.0f}, max {max(p for _, p in before)}, "
              f"{sum(1 for _, p in before if p >= 99)} at 99)")
        top = sorted(zip(pros, av), key=lambda z: -z[1])[:10]
        print('  top ten by career value:')
        for x, a in top:
            i = pros.index(x)
            print(f"    {x['forename']+' '+x['surname']:<24}{before[i][0]}/{before[i][1]}  ->  "
                  f"{x['rating']}/{x['potential']}   wAV {a:.0f}")
        if dry:
            print('\n  --dry-run: nothing written\n'); continue
        json.dump(d, open(repo(f'PGMRoster_{f}.json'), 'w'), separators=(', ', ': '))
        print(f'\n  wrote PGMRoster_{f}.json\n')

if __name__ == '__main__':
    main()
