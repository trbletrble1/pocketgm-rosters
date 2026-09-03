#!/usr/bin/env python3
"""
build_1979_unrated — ratings for the 47 men on the four invented franchises whom
no Madden file covers. Output: wip/unrated_1979.csv.

  python3 tools/build_1979_unrated.py
  python3 tools/build_1979_unrated.py --selftest

They split cleanly and need different treatment:

  24 aged 30-39, who retired before the source's coverage. 21 are in the 2K5
     archive after all — the 1958-1980 save carries 17 and the GOATs save 13,
     overlapping on 9, and the two are independent rather than copies (they agree
     on only ~21% of values). The archive gives ELEVEN ATTRIBUTES BUT NO OVERALL,
     so the overall is CALIBRATED: a per-position least-squares fit from those
     eleven onto Madden's POVR, trained on the 1,133 men who carry both.

     Prefer the era file. The GOATs save runs about five points hot on speed
     (median 80 against 75), which is what an all-time roster does.

  23 aged 22-29, with no NFL career yet. The archive holds exactly ONE of them,
     which is the confirmation rather than a gap: they have no career to have been
     recorded. They go through the prospect machinery — low current rating against
     real headroom.

   3 in neither, hand-rated: Vince Papale, Pat Curran, MacArthur Lane. Careers
     fetched, not remembered.

THE FIT VARIES A LOT BY POSITION and is reported beside every rating: QB 0.78 and
P 0.77 at the top, RB 0.44 at the bottom. Mean absolute error 3-5 points. A
measured estimate with a stated error beats a judgement, but a 0.44 estimate
should be visible as one.
"""
import csv, sys, os, re, unicodedata, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl2k5
from pgm3_paths import repo, require

F = ['Speed', 'Agility', 'PassArmStrength', 'Stamina', 'KickPower', 'Durability',
     'Strength', 'Jumping', 'Coverage', 'RunRoute', 'Tackle']
SEASON_FILE = '1979-1980SAVEGAME.DAT'   # first preference: the right season AND the
                                        # scale the model was trained on. It holds
                                        # only 1 of the 24, which is why the
                                        # historical archives are needed at all.
ERA_FILE = '1958-1980SAVEGAME.DAT'      # second: the right era, wrong season
GOATS = 'GOATSSAVEGAME.DAT'             # fallback: runs ~5 hot on speed

# Hand-rated, with the basis stated. Careers fetched from their own articles.
# Rate the man, not the story: Papale is a three-season special-teams player and
# comes out near the floor, which is honest and still a good detail for anyone
# who spots him on Charlotte's roster.
HAND = {
    'Vince Papale':   (55, 'three NFL seasons, Eagles 1976-78, primarily special teams'),
    'Pat Curran':     (72, 'ten seasons at tight end, Rams and Chargers 1969-78, a starter'),
    'MacArthur Lane': (78, 'eleven seasons 1968-78; at 36 the oldest back to rush for 100 yards in a game'),
}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

def solve(A, b):
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-9:
            continue
        M[c], M[piv] = M[piv], M[c]
        d = M[c][c]
        M[c] = [v / d for v in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [a - f * bb for a, bb in zip(M[r], M[c])]
    return [M[i][n] for i in range(n)]

def fit(rows):
    """Least squares with an intercept and a whisper of ridge, so a position with
    40 men and eleven predictors cannot produce a singular matrix."""
    X = [x for x, _ in rows]; y = [v for _, v in rows]; n = len(F)
    A = [[sum(X[k][i] * X[k][j] for k in range(len(X))) + (1e-6 if i == j else 0)
          for j in range(n)] + [sum(X[k][i] for k in range(len(X)))] for i in range(n)]
    A.append([sum(X[k][j] for k in range(len(X))) for j in range(n)] + [float(len(X))])
    b = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(n)] + [sum(y)]
    return solve(A, b)

def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    n = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    d = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** .5
    return n / d if d else 0.0

def train():
    """Per-position models, trained on the men who carry both an archive record
    and a Madden overall. Returns {pos: (weights, r, mean_abs_error, n)}."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('b', repo('tools', 'build_1979_ratings.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    play = m.load_play(); spine = m.load_spine()
    tm = m.team_map(play, spine); ppos = m.load_ppos(play)
    rows, _ = m.join(play, spine, tm, ppos_name=ppos, report=[])
    k5 = m.load_2k5(rows, ppos)
    data = collections.defaultdict(list)
    for r, p, _ in rows:
        q = k5.get((r['team'], r['name']))
        if q:
            data[m.PGM3POS[ppos(p)]].append(([q[f] for f in F], int(p['POVR'])))
    out = {}
    for pos, v in data.items():
        if len(v) < 25:
            continue
        w = fit(v)
        pred = [sum(a * b for a, b in zip(x, w[:-1])) + w[-1] for x, _ in v]
        act = [y for _, y in v]
        out[pos] = (w, pearson(pred, act), st.mean(abs(a - b) for a, b in zip(pred, act)), len(v))
    return out, m

def archives():
    """Both archives, with GOATs QUANTILE-ALIGNED onto the era file per attribute.

    Without this the two are simply different scales — GOATs runs 90 against 67 on
    stamina and 95 against 79 on durability — and a man read from one is not
    comparable to a man read from the other. It showed: Billy Kilmer, from the era
    file, came out above Fran Tarkenton, from GOATs, because they were never on the
    same axis. Preferring the era file per man is not enough when some men appear
    only in the other one."""
    raw = {}
    for f in (SEASON_FILE, ERA_FILE, GOATS):
        raw[f] = list(nfl2k5.Save(require('NFL2k25 Year Saves', f)).players)
    ref = {a: sorted(q[a] for q in raw[SEASON_FILE]) for a in F}
    src = {a: sorted(q[a] for q in raw[GOATS]) for a in F}
    def align(v, a):
        s_, r_ = src[a], ref[a]
        i = max(0, min(len(s_) - 1, __import__('bisect').bisect_left(s_, v)))
        return r_[min(len(r_) - 1, int(round(i / max(1, len(s_) - 1) * (len(r_) - 1))))]
    out = {}
    for f in (SEASON_FILE, ERA_FILE, GOATS):
        d = collections.defaultdict(list)
        for q in raw[f]:
            rec = dict(q)
            if f != SEASON_FILE:
                for a in F:
                    rec[a] = align(q[a], a)
            d[norm(q['fname'] + ' ' + q['lname'])].append(rec)
        out[f] = d
    return out

POSMAP = {'DB': 'S', 'LB': 'OLB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'QB': 'QB',
          'OT': 'OT', 'OG': 'OG', 'C': 'C', 'DE': 'DE', 'DT': 'DT', 'K': 'K', 'P': 'P'}

def at(band, rank, n):
    """Plotting position, (i+0.5)/n, NOT rank/(n-1). The naive form hands the top
    man of a small group the band's MAXIMUM: 23 young men stretched across the
    published prospect distribution gave David Posey, a 22-year-old kicker, a 93
    — the band's ceiling — because he happened to sort first among six men who are
    all 22. Same defect as the rating map, same fix."""
    q = (rank + 0.5) / n
    return band[min(len(band) - 1, int(round(q * (len(band) - 1))))]

def prospect_band():
    """The 23 young men have no NFL career, and the archive holds exactly one of
    them — which is the confirmation, not a gap. They are prospects in everything
    but label, so they take the published prospect distribution: rating p5 53,
    median 61, p95 75, and headroom median 7 against a p90 of 13. Measured over
    3,353 prospects in four published files.

    Ordered within the group by AGE — 22 ahead of 25 — because a man still
    unsigned at 25 is a worse prospect than one at 22, and age is the only signal
    these men carry."""
    import json
    rat, hd = [], []
    for y in ('2013', '2017', '2021', '2026'):
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] == 'Rookie':
                rat.append(x['rating']); hd.append(x['potential'] - x['rating'])
    return sorted(rat), sorted(hd)

def veteran_band():
    """The level the calibrated ORDERING is placed onto. The model is trained on
    men who were playing in 1979; the archive rates its men at career level; and
    our 24 were out of football. Applied raw it produced Billy Kilmer at 96 aged
    39 and Jim Mandich, a backup tight end, at 90.

    The right population is the pool's OWN rated men of the same age — 39 men aged
    30-39 who were also out of football in 1979. They sit at a median of 77 with a
    p90 of 85. So the fit supplies the ordering and this supplies the level, which
    is the same rule the whole build uses.

    The age curve inside the league runs the other way — median POVR rises from 74
    at 22 to 87 at 33 — but that is survivorship, and these men are the opposite
    selection. Conditioning on the league would have been the wrong population."""
    out = []
    for f in ('expansion_pool_1979_top40.csv', 'expansion_pool_1979_rest.csv'):
        for x in csv.DictReader(open(repo('wip', f))):
            if str(x.get('povr', '')).isdigit() and str(x['age']).isdigit() and int(x['age']) >= 30:
                out.append(int(x['povr']))
    assert len(out) >= 25, f'the veteran band is too thin to map onto: {len(out)}'
    return sorted(out)

def main():
    models, m = train()
    band = veteran_band()
    arc = archives()
    rows = [x for x in csv.DictReader(open(repo('wip', 'franchises_1979.csv')))
            if x['franchise'] != '(free agent pool)' and not x['povr'].isdigit()]
    fh = open(repo('wip', 'unrated_1979.csv'), 'w', newline='')
    w = csv.writer(fh)
    w.writerow(['name', 'pos', 'age', 'franchise', 'group', 'rating', 'basis',
                'archive_file', 'fit_r', 'fit_mean_abs_error'])
    done, raw, pending, youngsters = collections.Counter(), [], [], []
    prat, phd = prospect_band()
    for x in sorted(rows, key=lambda z: (int(z['age']) < 30, -int(z['age']))):
        nm, pos = x['name'], POSMAP.get(x['pos'], x['pos'])
        young = int(x['age']) < 30
        rec, src = None, ''
        for f in (SEASON_FILE, ERA_FILE, GOATS):       # right season, then right era
            if norm(nm) in arc[f]:
                rec, src = arc[f][norm(nm)][0], f
                break
        if nm in HAND:
            rating, basis, r_, e_ = HAND[nm][0], f'hand: {HAND[nm][1]}', '', ''
            done['hand'] += 1
        elif rec is not None and pos in models and not young:
            ww, r_, e_, _ = models[pos]
            v = sum(a * b for a, b in zip([rec[f] for f in F], ww[:-1])) + ww[-1]
            raw.append((nm, v, pos, r_, e_, x, src))
            rating, basis = None, 'calibrated from the 2K5 archive'
            done['calibrated'] += 1
        else:
            youngsters.append(nm)
            rating, basis, r_, e_ = None, 'prospect band — no career to have been recorded', '', ''
            done['prospect'] += 1
        pending.append([nm, x['pos'], x['age'], x['franchise'],
                        'young' if young else 'old', rating, basis, src,
                        f'{r_:.2f}' if r_ != '' else '', f'{e_:.1f}' if e_ != '' else ''])
    # place the calibrated ordering onto the veteran band
    order = sorted(range(len(raw)), key=lambda i: raw[i][1])
    placed = {}
    for rank, i in enumerate(order):
        placed[raw[i][0]] = at(band, rank, len(order))
    # the young: placed on the prospect band, ordered by age
    ages = {r[0]: int(r[2]) for r in pending}
    yorder = sorted(youngsters, key=lambda nm: (-ages[nm], nm))   # oldest worst; name breaks ties
    for rank, nm in enumerate(yorder):
        placed[nm] = at(prat, rank, len(yorder))
    for row in pending:
        if row[5] is None and row[0] in placed:
            row[5] = placed[row[0]]
            if row[0] in youngsters:
                row[6] = 'prospect band, ordered by age (the only signal they carry)'
        w.writerow([c if c is not None else '' for c in row])
    fh.close()   # the reader below opened an unflushed handle and printed nothing
    print(f'wrote wip/unrated_1979.csv: {dict(done)}')
    print(f"\n{'pos':<5}{'n':>5}{'r':>7}{'mean |err|':>12}   the per-position fit, worst first")
    for pos, (_, r_, e_, n) in sorted(models.items(), key=lambda kv: kv[1][1]):
        print(f'{pos:<5}{n:>5}{r_:>7.2f}{e_:>12.1f}')
    out = list(csv.DictReader(open(repo('wip', 'unrated_1979.csv'))))
    print(f"\n{'name':<20}{'pos':<4}{'age':>4}{'rating':>7}{'fit r':>7}{'+/-':>6}   basis")
    for x in out:
        if x['rating']:
            print(f"{x['name']:<20}{x['pos']:<4}{x['age']:>4}{x['rating']:>7}{x['fit_r'] or '  —':>7}"
                  f"{x['fit_mean_abs_error'] or ' —':>6}   {x['basis'][:44]}")

def selftest():
    ok = 0
    models, _ = train()
    try:
        assert all(0.3 < r < 0.95 for _, r, _, _ in models.values()), \
            {p: round(r, 2) for p, (_, r, _, _) in models.items()}
        ok += 1; print('  ok: every position model fits in a believable band, none perfect and none useless')
    except AssertionError as e:
        print(f'  FAIL: a model is degenerate: {e}')
    try:
        arc = archives()
        n_era = sum(1 for k in arc[ERA_FILE])
        shared = set(arc[ERA_FILE]) & set(arc[GOATS])
        same = sum(1 for k in shared if arc[ERA_FILE][k][0]['Speed'] == arc[GOATS][k][0]['Speed'])
        assert same / max(1, len(shared)) < 0.5, 'the two archive saves are the same file'
        ok += 1; print(f'  ok: the two archive saves are independent ({same}/{len(shared)} identical on speed)')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 2 else 1)
    main()
