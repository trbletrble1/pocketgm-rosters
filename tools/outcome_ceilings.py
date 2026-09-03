#!/usr/bin/env python3
"""
outcome_ceilings — item 40. Make a prospect's ceiling reflect what he became,
not where he started.

  python3 tools/outcome_ceilings.py 2013 --dry-run
  python3 tools/outcome_ceilings.py 1979 2000 2004 2010 2013 2017

THE DEFECT. The old formula was rating + min(40, GAP_BY_BAND[rating//10] + noise
+ raise). Three anchors on the starting rating: the baseline is picked by rating
band, the whole sum is added to rating, and the 40-point cap is measured from
rating. So Aaron Rodgers (63, the largest raise in 2004's class) stopped at 95
while Jahri Evans (73) reached 99, and Dak Prescott (58, more career value than
Myles Garrett) topped out at 79.

THE MECHANISM. Within each draft class, rank men by outcome and map that rank
onto the class's EXISTING potential distribution. The marginal distribution is
preserved by construction, so star supply (90+ share, 1.8-4.5% against vanilla's
2.0-3.1%) and the ceiling counts do not move; what changes is WHICH men hold the
ceilings. Rating is a floor: where the mapped potential would sit at or below a
man's rating he gets rating + 3, vanilla's median headroom among its unlocked
prospects. A bare rating floor was measured first and locked 13-15% of every
class — men locked for being rated above their outcome rank, which is not
vanilla's locked share and not a bust. Ruled 2026-09-03.

PER CLASS, NOT PER FILE. 2017's 2021-class men have truncated careers; a
whole-file rank would push them down for playing fewer seasons, not worse ones.

THE OUTCOME SCORE IS UNCHANGED: 0.9*min(6, pro_bowls) + 1.6*min(4, all_pro)
+ 0.09*min(120, wAV) + 0.30*min(12, seasons_started). Pro Bowls capped at six
because every alternative measured worse (item 35).

MEASURED, per file, correlation of potential with outcome 0.64-0.69 -> 0.88-0.95.
Rodgers 95 -> 99, Prescott 79 -> 91, Hurts 77 -> 89. Herbert and Murray settle at
88, which is where their outcomes put them against Allen and Jackson.

ACCEPTED DIVERGENCE: headroom p90 widens from 14-15 to 17-20 against vanilla's
unlocked 10-11. Prescott at 33 points of headroom IS the fix working.

SOURCES.
  1979 (1980-83), 2004 (2005-08), 2010 (2011-14), 2013 (2014-17), 2017 (2018-21):
        PFR draft listings carrying wAV directly. 0 misses on every file.
  2000 (2001-04): PFR picks with car_av FILLED FROM NFLVERSE CAREER SPAN, the
        +0.76 substitute for wAV's +0.94. Same mechanism, weaker signal, and the
        file says so. 5 of 1,024 miss the listing and are left as they are.
NOT HERE, by ruling:
  2007  two of its four classes (2009, 2010) have no listing. Held for the pages.
  1986, 2021  no listings; nflverse span exists but 1986 is the archive's best
        file at +0.70 and is not touched on a weaker signal than the others get.
  2026  its classes are 2027 and 2028. No outcome can exist and none is invented.
        Its ceilings are consensus scouting, which is the honest thing for a
        future class.

RATINGS ARE NOT TOUCHED. Only potential and growthType move.
"""
import json, csv, sys, os, re, random, unicodedata, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
CLASSES = {'1979': [1980, 1981, 1982, 1983], '2000': [2001, 2002, 2003, 2004],
           '2004': [2005, 2006, 2007, 2008], '2010': [2011, 2012, 2013, 2014],
           '2013': [2014, 2015, 2016, 2017], '2017': [2018, 2019, 2020, 2021],
           # the ten pages Ryan saved 2026-09-03 unblock these three
           '1986': [1987, 1988, 1989, 1990], '2007': [2008, 2009, 2010, 2011], '2021': [2022, 2023, 2024, 2025]}
FLOOR_GAP = 3          # vanilla's median headroom among unlocked prospects
NAMED = ['aaron rodgers', 'jahri evans', 'adrian peterson', 'dak prescott', 'myles garrett',
         'jalen hurts', 'justin herbert', 'kyler murray', 'josh allen', 'lamar jackson',
         'tom brady', 'drew brees', 'ladainian tomlinson', 'anthony munoz', 'ronnie lott',
         'dan marino', 'john elway', 'mike singletary', 'jj watt', 'russell wilson']

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

def num(r, k):
    v = (r.get(k) or '').strip()
    return float(v) if v.replace('.', '', 1).isdigit() else 0.0

def outcome(r):
    return (0.9 * min(6, num(r, 'pro_bowls')) + 1.6 * min(4, num(r, 'all_pro'))
            + 0.09 * min(120, num(r, 'career_av')) + 0.30 * min(12, num(r, 'seasons_started')))

def load_listings(f):
    idx = {}
    if f == '2000':
        for r in csv.DictReader(open(repo('wip', 'draft_picks_2001_2004.csv'))):
            r2 = {'career_av': r['car_av'], 'pro_bowls': r['probowls'],
                  'all_pro': r['allpro'], 'seasons_started': r['seasons_started']}
            y = int(r['season'])
            idx[(y, norm(r['pfr_player_name']))] = r2
            idx.setdefault((y, int(r['pick'])), r2)
        return idx
    for y in CLASSES[f]:
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

def run(f, dry):
    d = json.load(open(repo(f'PGMRoster_{f}.json')))
    pros = [x for x in d if x['teamID'] == 'Rookie']
    seasons = sorted({x['draftSeason'] for x in pros})
    year_of = dict(zip(seasons, CLASSES[f]))
    idx = load_listings(f)
    joined, missed = [], []
    for x in pros:
        y = year_of[x['draftSeason']]
        key = norm(x['forename'] + ' ' + x['surname'])
        r = idx.get((y, key)) or idx.get((y, x.get('draftNum') or 0))
        (joined if r is not None else missed).append((x, outcome(r) if r is not None else None, y, key))
    if f == '2000':
        assert len(missed) <= 5, f'2000 misses grew: {len(missed)}'
    elif missed:
        print(f'  {len(missed)} prospects did not join a listing (left as they are): ' + ', '.join(f"{x['forename']} {x['surname']} {y}" for x, _, y, _ in missed[:6]))

    before = {id(x): x['potential'] for x, *_ in joined}
    out = {}
    # PER CLASS: rank by outcome, map onto the class's own potential distribution
    for y in CLASSES[f]:
        cls = [(x, o, k) for x, o, yy, k in joined if yy == y]
        pots = sorted(x['potential'] for x, _, _ in cls)
        order = sorted(cls, key=lambda t: (t[1], random.Random(f'{t[2]}|{f}|q').random()))
        for i, (x, o, k) in enumerate(order):
            m = pots[i]
            out[id(x)] = m if m > x['rating'] else min(99, x['rating'] + FLOOR_GAP)

    # apply
    for x, o, y, k in joined:
        p = out[id(x)]
        assert p >= x['rating']
        x['potential'] = p
        x['growthType'] = build_growth(p, x['rating'], random.Random(f'{k}|{f}|ceil2'), 31)
        assert sum(v for v in x['growthType'] if v > 0) == (p - x['rating']) * 50

    # measure
    o = [t[1] for t in joined]
    pb = [before[id(t[0])] for t in joined]; pa = [t[0]['potential'] for t in joined]
    hb = sorted(b - t[0]['rating'] for b, t in zip(pb, joined)); ha = sorted(a - t[0]['rating'] for a, t in zip(pa, joined))
    src = 'PFR wAV (+0.94 signal)' if f != '2000' else 'car_av FILLED FROM NFLVERSE SPAN (+0.76 substitute)'
    print(f'=== {f} ===  {len(joined)} joined, {len(missed)} missed   source: {src}')
    print(f"  r(outcome, potential)  {spearman(o, pb):+.2f} -> {spearman(o, pa):+.2f}")
    print(f"  90+ share              {sum(1 for v in pb if v >= 90) / len(pb):.1%} -> {sum(1 for v in pa if v >= 90) / len(pa):.1%}")
    print(f"  at 99                  {sum(1 for v in pb if v >= 99)} -> {sum(1 for v in pa if v >= 99)}")
    print(f"  locked                 {sum(1 for v in hb if v == 0) / len(hb):.1%} -> {sum(1 for v in ha if v == 0) / len(ha):.1%}")
    print(f"  headroom med / p90     {st.median(hb):.0f} / {hb[int(len(hb) * .9)]} -> {st.median(ha):.0f} / {ha[int(len(ha) * .9)]}")
    floored = sum(1 for t in joined if t[0]['potential'] == min(99, t[0]['rating'] + FLOOR_GAP) and before[id(t[0])] != t[0]['potential'])
    print(f"  floored at rating+{FLOOR_GAP}    {floored} men ({floored / len(joined):.1%})")
    for x, oo, y, k in sorted(joined, key=lambda t: -t[1]):
        if k in NAMED:
            print(f"    {k:<22} rating {x['rating']:>3}   potential {before[id(x)]:>3} -> {x['potential']:>3}   outcome {oo:>5.1f}")
    if dry:
        print('  --dry-run: nothing written\n'); return
    json.dump(d, open(repo(f'PGMRoster_{f}.json'), 'w'), separators=(', ', ': '))
    print(f'  wrote PGMRoster_{f}.json\n')

def main():
    years = [a for a in sys.argv[1:] if a in CLASSES]
    dry = '--dry-run' in sys.argv
    assert years, 'give one or more of ' + ', '.join(CLASSES)
    for f in years:
        run(f, dry)

if __name__ == '__main__':
    main()
