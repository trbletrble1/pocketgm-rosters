#!/usr/bin/env python3
"""
build_1979_draft — the four draft classes a 1979 file needs, 1980 to 1983.
Writes wip/draft_class_{year}.csv. Record assembly (52 keys) happens in the
final roster build, with every cohort together.

  python3 tools/build_1979_draft.py
  python3 tools/build_1979_draft.py --selftest

TWO KINDS OF CLASS, and they are not the same thing:

  1980  FULLY SOURCED. The PFR draft listing is on disk (fetched with the 1979
        pages): 335 picks with round, pick, team, position, age, college, last
        season played, career AV and Pro Bowls. Membership, ordering and career
        outcome are all real. This class meets the historical-build convention
        in the handoff — potential is a rating-band baseline RAISED by what the
        man became — in full.

  1981  MEMBERSHIP FROM THE 2K5 ARCHIVE, and it leaks. A draftee is a years_pro
  1982  ==1 man in his rookie-season save (2K5 reads rookies as 1, measured),
  1983  so 1981 is 1981-82 yp==1, 1983 is 1983-84 yp==1, and 1982 — no 1982-83
        save exists — is 1983-84 yp==2. Anchored: Rogers, Taylor, Lott, Easley
        all read 1 in 1981-82; Elway, Marino, Dickerson, Matthews read 1 in
        1983-84; Marcus Allen, McMahon, Munchak read 2. Jim Kelly is ABSENT from
        1983-84, which is the source knowing he went to the USFL.
        The leak, measured on the 1980 class against its listing: of 209
        draftees who played, 167 are in the next save and only 124 carry the
        expected years_pro — 27 read one low, 16 read stock junk (Earl Cooper,
        a first-round pick, reads 11). So the filter reaches ~74% of the men
        present and none of the 42 cut before the next season. These three
        classes therefore carry NO career raise (no outcome is on disk), NO
        real pick order (ordered on the archive's attributes through the
        calibrated per-position model instead), and ages from the 1980
        listing's distribution as a prior. Ryan's pending PFR fetch for
        1981-83 closes all three gaps; until then they are board-rank classes
        in the sense the 2026 build's future classes are — no hidden gems.

RATING: level from the published prospect band (3,353 prospects across four
files: p5 53, median 61, p95 75), ordering from the source. Plotting position,
never rank/(n-1).

POTENTIAL, from build_2000.draft_potential with the random draw REMOVED (Ryan's
2026 ruling: one rule, median only): headroom = GAP_BY_BAND[rating band]
(18/8/4/4/5/1 from the 40s up, measured on 6,124 published prospects — driven
by rating, not round), plus the career raise 0.9*min(6,probowls) +
1.6*min(4,allpro) + 0.09*min(120,car_av) + 0.30*min(12,seasons_started),
gap capped at 40. RAISE-ONLY: a bust keeps his ceiling.

AGE: age AT DRAFT for every class. A first version made each class a year
younger per year out — seniors, juniors — and the published files contradict
it: every historical file carries all four future classes (draftSeason 2027 to
2030) at the same median age, 22 to 23. The convention is that a class is rated
as of its own draft. So 1980 -> 2027, 1981 -> 2028, 1982 -> 2029, 1983 -> 2030,
all at age-at-draft; the 1980 listing's distribution (21-26, median 22) is the
prior for the three archive classes, which carry no age.

ORDERING WITHIN AN ARCHIVE CLASS is by percentile WITHIN POSITION, then merged.
The first version sorted every position together on raw predicted overall, and
the top of all three classes was a punter or a kicker — Stachowicz, Karlis,
Scribner — because the K/P models emit on their own scale. Same rule as
everywhere else in this build: level from the pool, per position.
"""
import csv, sys, os, re, unicodedata, collections, statistics as st, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

GAP_BY_BAND = {4: 18, 5: 8, 6: 4, 7: 4, 8: 5, 9: 1}
GAP_CAP = 40
F = ['Speed', 'Agility', 'PassArmStrength', 'Stamina', 'KickPower', 'Durability',
     'Strength', 'Jumping', 'Coverage', 'RunRoute', 'Tackle']
POSMAP = {'DB': 'S', 'CB': 'CB', 'S': 'S', 'FS': 'S', 'SS': 'S', 'LB': 'OLB', 'OLB': 'OLB', 'ILB': 'MLB',
          'MLB': 'MLB', 'RB': 'RB', 'FB': 'RB', 'HB': 'RB', 'WR': 'WR', 'TE': 'TE', 'QB': 'QB',
          'T': 'OT', 'OT': 'OT', 'G': 'OG', 'OG': 'OG', 'C': 'C', 'DE': 'DE', 'DT': 'DT', 'NT': 'DT',
          'K': 'K', 'P': 'P', 'DL': 'DE', 'OL': 'OG'}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

def at(band, rank, n):
    return band[min(len(band) - 1, int(round((rank + 0.5) / n * (len(band) - 1))))]

def prospect_band():
    import json
    out = []
    for y in ('2013', '2017', '2021', '2026'):
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] == 'Rookie':
                out.append(x['rating'])
    return sorted(out)

def raise_for(row):
    def num(k):
        try: return float(row.get(k) or 0)
        except (ValueError, TypeError): return 0.0
    return (0.9 * min(6, num('pro_bowls')) + 1.6 * min(4, num('all_pro'))
            + 0.09 * min(120, num('career_av')) + 0.30 * min(12, num('seasons_started')))

def potential(rating, row):
    band = GAP_BY_BAND.get(min(9, max(4, rating // 10)), 4)
    return int(round(rating + min(GAP_CAP, band + raise_for(row))))

def class_1980(band):
    rows = list(csv.DictReader(open(repo('wip', 'draft_1980_pfr.csv'))))
    rows.sort(key=lambda r: int(r['pick']))
    n = len(rows); out = []
    for rank, r in enumerate(rows):
        rating = at(band[::-1], rank, n)               # pick 1 gets the band's top
        age = int(r['age']) if r['age'].isdigit() else 22
        out.append(dict(year=1980, name=r['name'], pos=POSMAP.get(r['pos'], r['pos']), age=age,
                        rating=rating, potential=potential(rating, r), draft_pick=int(r['pick']),
                        round=r['round'], college=r['college'], career_av=r['career_av'],
                        pro_bowls=r['pro_bowls'], ever_played='yes' if r['last_season'] else 'no',
                        source='PFR 1980 draft listing', ordering='draft pick', raise_basis='career AV, Pro Bowls'))
    return out

def class_archive(year, band, models, age_prior):
    rows = list(csv.DictReader(open(repo('wip', f'draft_{year}_archive.csv'))))
    scored = []
    for r in rows:
        pos = POSMAP.get(r['pos'], r['pos'])
        m = models.get(pos)
        x = [int(r[f]) for f in F]
        if pos == 'QB':
            # THE MODEL FAILS FOR ROOKIE QUARTERBACKS and the data does not. The
            # calibrated QB model (fit 0.78, the best of any position) ranked Elway
            # 62nd in the 1983 class and McMahon 78th in 1982, because its
            # speed/agility/durability terms — fitted on veterans — drown the one
            # QB-specific attribute the archive carries. By PassArmStrength alone
            # Marino is 92 and Elway 90, first and second; Lomax 93, first in 1981.
            # So quarterbacks order on arm. A per-position exception, stated.
            v, fit = float(r['PassArmStrength']), None
        else:
            v = (sum(a * b for a, b in zip(x, m[0][:-1])) + m[0][-1]) if m else st.mean(x)
            fit = m[1] if m else None
        scored.append((v, r, pos, fit))
    # percentile within position, so a kicker competes with kickers
    bypos = collections.defaultdict(list)
    for t in scored:
        bypos[t[2]].append(t[0])
    def pct(v, pos):
        vs = sorted(bypos[pos]); i = sum(1 for x in vs if x < v)
        return (i + 0.5) / len(vs)
    scored.sort(key=lambda t: -pct(t[0], t[2]))
    n = len(scored); out = []
    for rank, (v, r, pos, fit) in enumerate(scored):
        rating = at(band[::-1], rank, n)
        age = at(age_prior, (rank * 7919) % n, n)        # the prior's shape, not its order
        out.append(dict(year=year, name=r['name'], pos=pos, age=max(19, age), rating=rating,
                        potential=potential(rating, {}), draft_pick='', round='', college='',
                        career_av='', pro_bowls='', ever_played='',
                        source=f"2K5 {r['source_save']} years_pro=={r['years_pro_read']}",
                        ordering=('PassArmStrength alone — the model fails for rookie QBs' if pos == 'QB'
                                  else f'calibrated attributes (fit r {fit:.2f})' if fit else 'attribute mean, no model'),
                        raise_basis='NONE — no career outcome on disk; PFR fetch pending'))
    return out

def load_models():
    spec = importlib.util.spec_from_file_location('u', repo('tools', 'build_1979_unrated.py'))
    u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
    models, _ = u.train()
    return models

def selftest():
    ok = 0
    band = prospect_band()
    try:
        c = class_1980(band)
        top = [x['name'] for x in sorted(c, key=lambda x: -x['potential'])[:12]]
        assert 'Anthony Munoz' in top and 'Billy Sims' in top, top
        ok += 1; print('  ok: the hindsight raise surfaces the real stars of 1980 (Munoz, Sims in the top twelve by potential)')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        assert potential(60, {}) == 60 + GAP_BY_BAND[6] and potential(60, {'career_av': '0', 'pro_bowls': '0'}) == 60 + GAP_BY_BAND[6]
        assert potential(60, {'career_av': '120', 'pro_bowls': '6', 'all_pro': '4'}) > potential(60, {})
        ok += 1; print('  ok: no outcome means no raise; an outcome raises and never lowers')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        c = class_1980(band)
        assert max(x['rating'] for x in c) <= band[-1] and min(x['rating'] for x in c) >= band[0]
        assert st.median(x['rating'] for x in c) <= st.median(band) + 3
        ok += 1; print('  ok: the class sits inside the published prospect band, level from the pool')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        models = load_models()
        ages = sorted(int(r['age']) for r in csv.DictReader(open(repo('wip', 'draft_1980_pfr.csv'))) if r['age'].isdigit())
        for year in (1981, 1982, 1983):
            c = class_archive(year, band, models, ages)
            top10 = [x['pos'] for x in sorted(c, key=lambda x: -x['rating'])[:10]]
            assert sum(1 for q in top10 if q in ('K', 'P')) <= 1, f'{year} top ten is specialists again: {top10}'
        ok += 1; print('  ok: no archive class puts more than one kicker or punter in its top ten')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        c83 = class_archive(1983, band, models, ages)
        qbs = [x['name'] for x in sorted(c83, key=lambda x: -x['rating']) if x['pos'] == 'QB']
        assert set(qbs[:2]) == {'John Elway', 'Dan Marino'}, qbs[:4]
        c81 = class_archive(1981, band, models, ages)
        assert [x['name'] for x in sorted(c81, key=lambda x: -x['rating']) if x['pos'] == 'QB'][0] == 'Neil Lomax'
        ok += 1; print('  ok: Elway and Marino lead the 1983 quarterbacks, Lomax the 1981 — arm strength orders rookie QBs')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok

def main():
    band = prospect_band()
    ages = sorted(int(r['age']) for r in csv.DictReader(open(repo('wip', 'draft_1980_pfr.csv'))) if r['age'].isdigit())
    models = load_models()
    keys = ['year', 'name', 'pos', 'age', 'rating', 'potential', 'draft_pick', 'round', 'college',
            'career_av', 'pro_bowls', 'ever_played', 'source', 'ordering', 'raise_basis']
    print(f"published prospect band: p5 {band[len(band)//20]}  median {st.median(band):.0f}  p95 {band[len(band)*19//20]}\n")
    print(f"{'class':<6}{'n':>5}{'rating med':>11}{'pot med':>9}{'headroom':>9}{'raised':>8}{'age med':>8}   top five by potential")
    for year in (1980, 1981, 1982, 1983):
        c = class_1980(band) if year == 1980 else class_archive(year, band, models, ages)
        fh = open(repo('wip', f'draft_class_{year}.csv'), 'w', newline='')
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(c); fh.close()
        hd = [x['potential'] - x['rating'] for x in c]
        raised = sum(1 for x in c if x['potential'] - x['rating'] > GAP_BY_BAND.get(min(9, max(4, x['rating'] // 10)), 4))
        top = ', '.join(f"{x['name'].split()[-1]} {x['potential']}" for x in sorted(c, key=lambda x: -x['potential'])[:5])
        print(f"{year:<6}{len(c):>5}{st.median(x['rating'] for x in c):>11.0f}{st.median(x['potential'] for x in c):>9.0f}{st.median(hd):>9.0f}{raised:>8}{st.median(x['age'] for x in c):>8.0f}   {top}")
    print("\n  published prospects: headroom median 7, p90 13. 1980 is raised by real careers; 1981-83 carry the band baseline only.")

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 5 else 1)
    main()
