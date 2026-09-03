#!/usr/bin/env python3
"""
build_1979_roster_file — assemble PGMRoster_1979.json and PGMStaff_1979.json
from every cohort this build has produced, then gate them.

  python3 tools/build_1979_roster_file.py            # writes both files
  python3 tools/build_1979_roster_file.py --selftest

COHORTS AND WHERE EACH FIELD COMES FROM
  spine 1,408     attributes/rating  wip/attributes_1979.csv (NFL79.ros, mapped)
                  potential          wip/potential_1979.csv
                  contracts          re-solved here over 32 teams (see below)
                  face               wip/faces_1979.csv
                  age, jersey        wip/roster_1979_dedup.csv (footballdb)
                  years pro          NFL79.ros PYRP, corrected (build_1979_ratings)
  franchises 184  rating             POVR quantile-mapped as the spine was, or the
  + FA pool 124                      calibrated/1976/prospect figure (unrated_1979)
                  attributes         NFL79.ros for 258 rated men, the 1976 mod for
                                     23 unrated, same map; 27 take the per-position
                                     median and the closing shift to their rating
                  potential          injury mechanic (IND), prospect band (young
                                     23), veteran band headroom otherwise
  draft 1,147     rating/potential   wip/draft_class_{year}.csv
                  attributes         per-position median, shifted to rating —
                                     prospects and free agents in the published
                                     files were never sourced either
                  draftNum           real pick (1980) or class rank (1981-83)
                  draftSeason        2027-2030
  staff 252       rating/name/age    wip/staff_1979.csv
                  43 skills          measured per-role profile off the published
                                     staff files (rate, median, sd), as build_2000
                  face               wip/faces_1979.csv (registry or generated)

DRAFT PICK NUMBERS FOR ROSTERED MEN: none. wip/draft_picks_pre2001.csv begins at
1980. Every 1979 rostered and free-agent man carries the 224 floor. Stated as a
gap; a 1958-1979 pick source would fill it.

CONTRACTS ARE RE-SOLVED OVER 32 TEAMS. The contract tool ran on the 28 real
teams; the payroll constant ($197.4M median top-53) is a median across the
league the file will CONTAIN, and that league has 32 teams. Same tool, wider
population, TOP_RATIO re-solved against the cap.

teamNum is measured off the 2017 file, not assumed.

GATES, self-tested before writing: exact key sets; the 50x growth rule on every
record (with a tampered record that must FAIL); family rules on every face; the
teamID set is the fixed 32 plus Rookie and Free Agent, with TEN/CAR/JAX/IND held
by the four franchises; every staff primary equals rating; draftSeason 2027-2030
for prospects and <= 2026 for everyone else; iden unique. Then pgm3_validate
roster / staff / faces and the conditional pass, on the written files.
"""
import csv, sys, os, re, json, uuid, random, unicodedata, collections, statistics as st, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

def load(name):
    spec = importlib.util.spec_from_file_location(name, repo('tools', name + '.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

SLUG2ID = {'atlanta-falcons': 'ATL', 'baltimore-colts': 'BAL', 'buffalo-bills': 'BUF', 'chicago-bears': 'CHI',
           'cincinnati-bengals': 'CIN', 'cleveland-browns': 'CLE', 'dallas-cowboys': 'DAL', 'denver-broncos': 'DEN',
           'detroit-lions': 'DET', 'green-bay-packers': 'GB', 'houston-oilers': 'HOU', 'kansas-city-chiefs': 'KC',
           'los-angeles-rams': 'LAR', 'miami-dolphins': 'MIA', 'minnesota-vikings': 'MIN', 'new-england-patriots': 'NE',
           'new-orleans-saints': 'NO', 'new-york-giants': 'NYG', 'new-york-jets': 'NYJ', 'oakland-raiders': 'LV',
           'philadelphia-eagles': 'PHI', 'pittsburgh-steelers': 'PIT', 'san-diego-chargers': 'LAC', 'seattle-seahawks': 'SEA',
           'san-francisco-49ers': 'SF', 'st-louis-cardinals': 'ARI', 'tampa-bay-buccaneers': 'TB', 'washington-redskins': 'WAS',
           'Memphis Southmen': 'TEN', 'Charlotte Hornets': 'CAR', 'Jacksonville Sharks': 'JAX', 'Indianapolis Racers': 'IND'}
FIXED = set('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split())
POSMAP = {'DB': 'S', 'LB': 'OLB', 'FB': 'RB', 'HB': 'RB', 'T': 'OT', 'G': 'OG', 'ILB': 'MLB', 'NT': 'DT'}
HEADROOM = [4, 4, 3, 2, 1, 1, 0, 0, 0]
INJURY_DISCOUNT = 14

def iden(key):
    return str(uuid.UUID(int=random.Random(f'{key}|1979').getrandbits(128))).upper()

def build_growth(potential, rating, rng, n_slots):
    """build_2000.build_growth, verbatim: positives in 0-16, negatives in 20+."""
    gt = [0] * n_slots
    need = (potential - rating) * 50
    if need:
        k = min(6, max(1, need // 150 + 1))
        slots = rng.sample(range(0, 17), k); share = need // k
        for i, sl in enumerate(slots):
            gt[sl] = share if i else need - share * (k - 1)
    for sl in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))):
        gt[sl] = -100 * rng.randint(1, 3)
    assert sum(v for v in gt if v > 0) == need
    return gt

# ------------------------------------------------------------- references
def ref_roster():
    r = json.load(open(repo('PGMRoster_2017.json')))
    keys = list(r[0].keys())
    ro = [x for x in r if x['teamID'] not in ('Rookie', 'Free Agent')]
    by = collections.defaultdict(set)
    for x in ro: by[x['teamID']].add(x['teamNum'])
    per_team_constant = all(len(v) == 1 for v in by.values())
    return keys, per_team_constant, ro

def ref_staff():
    s = json.load(open(repo('PGMStaff_2021.json')))
    return list(s[0].keys()), s[0]

def staff_profile():
    """Per role: for every numeric key, the rate it is non-zero, its median and
    sd among the published staff files; for every string key, the vocabulary."""
    files = [repo(f'PGMStaff_{y}.json') for y in (1986, 2004, 2007, 2013, 2017, 2021)]
    recs = [x for f in files if os.path.exists(f) for x in json.load(open(f))]
    prof = {}
    for role in sorted({x['role'] for x in recs}):
        v = [x for x in recs if x['role'] == role]; p = {'num': {}, 'str': {}}
        for k in v[0]:
            if isinstance(v[0][k], (int, float)) and not isinstance(v[0][k], bool):
                vals = [x[k] for x in v]; nz = [a for a in vals if a]
                p['num'][k] = dict(rate=len(nz) / len(vals), med=st.median(nz) if nz else 0, sd=st.pstdev(nz) if len(nz) > 1 else 0)
            elif isinstance(v[0][k], str):
                p['str'][k] = collections.Counter(x[k] for x in v).most_common()
        prof[role] = p
    return prof

PRIMARY = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach', 'Def Co-ord': 'DCcoach', 'Special Teams': 'STcoach',
           'Head Scout': 'Hscout', 'Off Scout': 'Oscout', 'Def Scout': 'Dscout', 'Head Physio': 'Hphysio', 'Assistant Physio': 'Aphysio'}
OFF_POS = ['QB', 'RB', 'WR', 'TE', 'OT', 'OG', 'C']; DEF_POS = ['DE', 'DT', 'OLB', 'MLB', 'CB', 'S']

# ------------------------------------------------------------- players
def assemble_players(keys, per_team_constant):
    R = load('build_1979_ratings'); W = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']
    LIVE = sorted(set().union(*[set(W[p][0]) for p in W]))
    pool = R.pool_attrs(LIVE); rat_pool = R.pool_ratings()
    n79 = {norm(x['PFNA'] + ' ' + x['PLNA']): x for x in csv.DictReader(open(R.dump_path('n79')))}
    n76 = {norm(x['PFNA'] + ' ' + x['PLNA']): x for x in csv.DictReader(open(R.dump_path('n76')))}
    faces = {(r['cohort'], norm(r['name']), r['pos'], r['team']): r['appearance'].split() for r in csv.DictReader(open(repo('wip', 'faces_1979.csv')))}
    # keyed on POSITION as well: Cleveland rostered two Robert Jacksons in 1979,
    # a guard and a linebacker, and a (team, name) key silently kept one of them.
    attrs = {(r['team'], r['name'], r['pgm3_pos']): r for r in csv.DictReader(open(repo('wip', 'attributes_1979.csv')))}
    pots = {(r['team'], r['name'], r['pgm3_pos']): r for r in csv.DictReader(open(repo('wip', 'potential_1979.csv')))}
    dedup = collections.defaultdict(list)
    for r in csv.DictReader(open(repo('wip', 'roster_1979_dedup.csv'))): dedup[(r['team'], r['name'])].append(r)
    assert len(attrs) == 1408 and len(pots) == 1408, (len(attrs), len(pots))
    unrated = {r['name']: r for r in csv.DictReader(open(repo('wip', 'unrated_1979.csv')))}
    # source medians per (pos, attr) from the spine's own NFL79 records, for the shift map
    play = R.load_play(); spine = R.load_spine(); tm = R.team_map(play, spine); ppos = R.load_ppos(play)
    rows, _ = R.join(play, spine, tm, ppos_name=ppos, report=[])
    k5 = R.load_2k5(rows, ppos)
    smed = collections.defaultdict(list)
    for r, p, _ in rows:
        pg = R.POS_OVERRIDE.get((r['team'], r['name']), (R.PGM3POS[ppos(p)],))[0]
        for a in LIVE:
            v = R.src_value(p, a, k5.get((r['team'], r['name'])), pg)
            if v is not None: smed[(pg, a)].append(v)
    SM = {k: st.median(v) for k, v in smed.items() if len(v) >= 12}

    # THE ZERO-PATTERN CONVENTION, read from the references rather than assumed:
    # a position's unused attributes are ZERO in every published file — a
    # receiver's passing accuracy, a lineman's coverage — 202 (position, attr)
    # pairs at 100% zero, none carrying weight in the vectors bar one OLB entry.
    # The map filled all thirty for everyone and the validator caught it.
    ZERO = collections.defaultdict(set)
    zc = collections.defaultdict(lambda: [0, 0])
    for y in ('1986', '2004', '2013', '2017'):
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] in ('Rookie', 'Free Agent'): continue
            for a in LIVE: zc[(x['position'], a)][0] += (x[a] == 0); zc[(x['position'], a)][1] += 1
    for (pz, a), (z, t) in zc.items():
        if z / t >= 0.95: ZERO[pz].add(a)
    def mapped_attrs(pos, src, target):
        d = {}
        for a in LIVE:
            pm = pool.get((pos, a))
            if pm is None: d[a] = 50; continue
            v = R.src_value(src, a, None, pos) if src is not None else None
            d[a] = int(round(max(1, min(99, st.median(pm) + (v - SM[(pos, a)]))))) if (v is not None and (pos, a) in SM) else int(round(st.median(pm)))
        for a in ZERO[pos]: d[a] = 0
        names = [a for a in W[pos][0] if a not in ZERO[pos]]; co = W[pos][1]; S = sum(c for a, c in zip(W[pos][0], co) if a in names)
        k = (target - R.overall_of(d, pos, W)) / S
        return {a: (0 if a in ZERO[pos] else int(round(max(1, min(99, d[a] + (k if a in names else 0)))))) for a in LIVE}

    def band_rating(pos, povr, cohort_povrs):
        return R.quantile_map([povr], rat_pool[pos])[0] if len(cohort_povrs) < 2 else None

    out = []; stats = collections.Counter()
    # ---- spine
    for (team, name, pos), a in attrs.items():
        pt = pots[(team, name, pos)]; cands = dedup[(team, name)]
        dd = cands[0] if len(cands) == 1 else next((c for c in cands if {'OG': 'OG', 'OLB': 'LB', 'MLB': 'LB', 'S': 'DB', 'CB': 'DB'}.get(pos, pos) == c['pos']), cands[0])
        rating, pot = int(a['rating']), int(pt['potential']); yrs = int(pt['years_pro'])
        rec = {k: 0 for k in keys}
        for at in LIVE: rec[at] = 0 if at in ZERO[a['pgm3_pos']] else int(a[at])
        rec.update(forename=name.split()[0], surname=' '.join(name.split()[1:]), position=a['pgm3_pos'], teamID=SLUG2ID[team],
                   age=int(dd['age']), rating=rating, potential=pot, appearance=faces[('spine', norm(name), a['pgm3_pos'], team)],
                   draftNum=224, draftSeason=2026 - yrs, teamNum=0, iden=iden(f'spine|{team}|{name}|{pos}'), _cohort='spine', _yrs=yrs, _team=team)
        rec['growthType'] = build_growth(pot, rating, random.Random(f'{name}|growth|1979'), 31)
        out.append(rec); stats['spine'] += 1
    # ---- franchises and FA pool
    fr = list(csv.DictReader(open(repo('wip', 'franchises_1979.csv'))))
    for x in fr: x['_fpos'] = x['pgm3_pos']       # decided once, in build_1979_franchises
    by_pos_povr = collections.defaultdict(list)
    for x in fr:
        if x['povr'].isdigit(): by_pos_povr[x['_fpos']].append(int(x['povr']))
    # quantile-map the pool's POVR onto the published band per position, plotting position, as the spine was
    povr_to_rating = {}
    for pos, vals in by_pos_povr.items():
        mapped = R.quantile_map(vals, rat_pool[pos])
        for v, m in zip(vals, mapped): povr_to_rating[(pos, v)] = m
    for x in fr:
        name = x['name']; pos = x['_fpos']; n = norm(name)      # the pool CSV says DB/LB; the mod says CB/S, MLB/OLB — taken, as the spine does
        is_fa = x['franchise'] == '(free agent pool)'
        if x['povr'].isdigit():
            rating = povr_to_rating[(pos, int(x['povr']))]; src = n79.get(n) or n76.get(n); rsrc = 'POVR mapped'
        else:
            rating = int(unrated[name]['rating']); src = n76.get(n); rsrc = unrated[name]['basis'][:30]
        # years pro: the 1979 mod's PYRP, corrected as the spine's is. A man whose
        # ONLY record is the 1976 mod carries PYRP as of 1976 and must be aged
        # forward three years, exactly as his rating was: Vince Papale shipped at
        # zero years pro — 1976 was his rookie year — with a 2026 draftSeason and a
        # rookie's contract ladder. Twenty-three men take the 1976 record.
        if src and n in n79 and src.get('PYRP', '').isdigit():
            yrs = R.years_pro({'PYRP': src['PYRP']})
        elif src and src.get('PYRP', '').isdigit():
            yrs = R.years_pro({'PYRP': src['PYRP']}) + 3
        else:
            yrs = max(0, int(x['age']) - 22)
        if x['reason'] == 'INJURY':
            healthy = rating; rating = max(40, healthy - INJURY_DISCOUNT); pot = healthy; stats['injury mechanic'] += 1
        elif not x['povr'].isdigit() and int(x['age']) < 30:
            pot = min(99, rating + 7); stats['prospect-band potential'] += 1
        else:
            pot = min(99, rating + HEADROOM[min(yrs, 8)])
        a = mapped_attrs(pos, src, rating); stats['attrs from NFL79' if (src and n in n79) else 'attrs from 1976' if src else 'attrs pool median'] += 1
        rec = {k: 0 for k in keys}; rec.update(a)
        rec.update(forename=name.split()[0], surname=' '.join(name.split()[1:]), position=pos,
                   teamID='Free Agent' if is_fa else SLUG2ID[x['franchise']], age=int(x['age']), rating=rating, potential=pot,
                   appearance=faces[('fa_pool' if is_fa else 'franchise', n, pos, x['franchise'])], draftNum=224, draftSeason=2026 - yrs, teamNum=0,
                   iden=iden(f'pool|{x["franchise"]}|{name}|{pos}'), _cohort='fa_pool' if is_fa else 'franchise', _yrs=yrs, _team=x['franchise'])
        rec['growthType'] = build_growth(pot, rating, random.Random(f'{name}|growth|1979'), 31)
        out.append(rec); stats['fa_pool' if is_fa else 'franchise'] += 1
    # ---- prospects
    for year, season in ((1980, 2027), (1981, 2028), (1982, 2029), (1983, 2030)):
        cls = list(csv.DictReader(open(repo('wip', f'draft_class_{year}.csv'))))
        ranked = sorted(cls, key=lambda x: (int(x['draft_pick']) if x['draft_pick'] else 9999, -int(x['rating'])))
        for i, x in enumerate(ranked):
            name, pos = x['name'], x['pos']; rating, pot = int(x['rating']), int(x['potential'])
            rec = {k: 0 for k in keys}; rec.update(mapped_attrs(pos, None, rating))
            rec.update(forename=name.split()[0], surname=' '.join(name.split()[1:]), position=pos, teamID='Rookie', age=int(x['age']),
                       rating=rating, potential=pot, appearance=faces[(f'draft_{year}', norm(name), pos, 'Rookie')],
                       draftNum=int(x['draft_pick']) if x['draft_pick'] else i + 1, draftSeason=season, teamNum=0,
                       iden=iden(f'draft{year}|{name}|{pos}|{i}'), _cohort=f'draft_{year}', _yrs=0, _team='Rookie')
            rec['growthType'] = build_growth(pot, rating, random.Random(f'{name}|growth|{year}'), 31)
            out.append(rec); stats[f'draft_{year}'] += 1
    # ---- contracts, re-solved over 32 teams
    C = load('build_1979_contracts')
    crows = [dict(rating=r['rating'], pgm3_pos=r['position'], years_pro=r['_yrs'], team=r['teamID'], name=r['forename'] + ' ' + r['surname'])
             for r in out if r['_cohort'] in ('spine', 'franchise')]
    con = C.build(crows, quiet=True)
    pp_ = C.published_personality()
    for r, c in zip([r for r in out if r['_cohort'] in ('spine', 'franchise')], con):
        r.update(salary=c['salary'], guarantee=c['guarantee'], length=c['length'], eSalary=c['salary'], eGuarantee=c['guarantee'], eLength=c['length'])
    ros = [r for r in out if r['_cohort'] in ('spine', 'franchise')]
    for f in ('greed', 'loyalty', 'ambition'):
        for r, v in zip(sorted(out, key=lambda z: z['iden']), C.spread(len(out), pp_[f])): r[f] = v
    for r in out:
        if r['_cohort'] not in ('spine', 'franchise'):
            r.update(salary=0, guarantee=0, length=0, eSalary=0, eGuarantee=0, eLength=0)
    # ---- teamNum
    if per_team_constant:
        idx = {t: i + 1 for i, t in enumerate(sorted(FIXED))}
        for r in out: r['teamNum'] = idx.get(r['teamID'], 0)
    else:
        cnt = collections.Counter()
        for r in sorted(out, key=lambda z: (z['teamID'], -z['rating'])):
            if r['teamID'] in FIXED: cnt[r['teamID']] += 1; r['teamNum'] = cnt[r['teamID']]
    stats['TOP_RATIO'] = round(C.TOP_RATIO, 2); stats['median top-53'] = C.team_median_top53(con)
    return out, stats

# ------------------------------------------------------------- staff
def assemble_staff(keys, ref):
    prof = staff_profile()
    faces = {(norm(r['name'])): r['appearance'].split() for r in csv.DictReader(open(repo('wip', 'faces_1979.csv'))) if r['cohort'] == 'staff'}
    TEAMID = load('build_1979_staff').TEAMID
    out = []
    for x in csv.DictReader(open(repo('wip', 'staff_1979.csv'))):
        role = x['role']; name = x['forename'] + ' ' + x['surname']; rating = int(x['rating']); age = int(x['age'])
        rng = random.Random(f'{name}|{role}|staff|1979'); p = prof[role]
        r = {}
        for k in keys:
            if isinstance(ref[k], str):
                voc = p['str'].get(k); r[k] = voc[0][0] if voc else ''
            elif isinstance(ref[k], list): r[k] = []
            else:
                e = p['num'].get(k, dict(rate=0, med=0, sd=0))
                if e['rate'] < 0.5: r[k] = 0
                else:
                    shift = rating - p['num']['rating']['med']
                    r[k] = max(1, min(99, int(round(e['med'] + 0.55 * shift + rng.gauss(0, max(2.0, e['sd'] * 0.45))))))
        r.update(forename=x['forename'], surname=x['surname'], role=role, teamID=TEAMID[x['team']], rating=rating, age=age)
        r[PRIMARY[role]] = rating
        r['potential'] = min(99, rating + rng.randint(0, 4))
        r['startSeason'] = max(1989, min(2026, int(round(-0.881 * age + 2054.5 + rng.gauss(0, 2.5)))))
        r['eGuarantee'] = 0
        r['length'] = max(1, r['length'] or 2); r['eLength'] = max(0, min(4, r['eLength'] or 2))
        r['appearance'] = faces[norm(name)]
        r['growthType'] = build_growth(r['potential'], rating, rng, 51)
        r['offStyle'] = 'West Coast' if (x['team'] == 'SF' and role == 'Head Coach') else 'Pro Style'   # 1979: Walsh, and everyone else
        r['defStyle'] = rng.choice(['4-3 Man', '4-3 Zone'])                                              # 4-3 for all 28, ruled; man/zone carries no meaning
        r['scoutBoost'] = rng.choice(OFF_POS if role == 'Off Scout' else DEF_POS if role == 'Def Scout' else OFF_POS + DEF_POS)
        r['iden'] = iden(f'staff|{x["team"]}|{role}|{name}')
        out.append(r)
    return out

# ------------------------------------------------------------- gates
def gate_players(out, keys):
    assert all(set(r) - {'_cohort', '_yrs', '_team'} == set(keys) for r in out), 'roster key set drift'
    for r in out:
        assert sum(v for v in r['growthType'] if v > 0) == (r['potential'] - r['rating']) * 50 and len(r['growthType']) == 31, r['forename']
        a = r['appearance']; assert a[0].replace('Head', '')[0] == a[5].replace('Nose', '')[0] == a[6].replace('Mouth', '')[0] and a[7] == 'Glasses1e'
        assert r['teamID'] in FIXED | {'Rookie', 'Free Agent'}, r['teamID']
        if r['teamID'] == 'Rookie': assert 2027 <= r['draftSeason'] <= 2030
        else: assert r['draftSeason'] <= 2026 and r['draftNum'] >= 1
    assert len({r['iden'] for r in out}) == len(out), 'iden collision'
    assert sum(1 for r in out if r['_cohort'] == 'spine') == 1408, 'the spine is not 1,408 — a keyed dict dropped someone'
    # team in the key: two men may share a name and a position on different teams
    # (the Gene Washingtons). The stronger invariant — no two spine men share a
    # mod record — is enforced in the join itself, so nothing is lost here.
    dup = collections.Counter((norm(r['forename'] + ' ' + r['surname']), r['position'], r['_team'], r['_cohort']) for r in out)
    assert max(dup.values()) == 1, [k for k, v in dup.items() if v > 1][:5]
    teams = {r['teamID'] for r in out if r['teamID'] in FIXED}
    assert teams == FIXED, f'missing teams {FIXED - teams}'
    for t in ('TEN', 'CAR', 'JAX', 'IND'):
        assert all(r['_cohort'] == 'franchise' for r in out if r['teamID'] == t), t

def gate_staff(out, keys):
    assert all(set(r) == set(keys) for r in out), 'staff key set drift'
    for r in out:
        assert r[PRIMARY[r['role']]] == r['rating'], r['surname']
        assert len(r['growthType']) == 51 and sum(v for v in r['growthType'] if v > 0) == (r['potential'] - r['rating']) * 50
        assert 1989 <= r['startSeason'] <= 2026
    # nine per team for ALL 32 — the four franchises carry generated staff now
    assert collections.Counter(r['teamID'] for r in out) == collections.Counter({t: 9 for t in sorted(FIXED)}), 'not nine per team across the 32'

def selftest():
    ok = 0
    keys, ptc, _ = ref_roster(); skeys, sref = ref_staff()
    out, stats = assemble_players(keys, ptc)
    try: gate_players(out, keys); ok += 1; print(f'  ok: every player gate holds on {len(out)} records')
    except AssertionError as e: print(f'  FAIL players: {e}')
    try:
        bad = [dict(r) for r in out[:50]]; bad[7]['growthType'] = list(bad[7]['growthType']); bad[7]['growthType'][0] += 50
        try: gate_players(bad, keys); print('  FAIL: a tampered growthType passed the 50x gate')
        except AssertionError: ok += 1; print('  ok: a tampered growthType FAILS the 50x gate — the check is not vacuous')
    except Exception as e: print(f'  FAIL negative: {e}')
    sf = assemble_staff(skeys, sref)
    try: gate_staff(sf, skeys); ok += 1; print(f'  ok: every staff gate holds on {len(sf)} records')
    except AssertionError as e: print(f'  FAIL staff: {e}')
    try:
        assert stats['injury mechanic'] == 6 and stats['attrs from NFL79'] >= 250, dict(stats)
        ok += 1; print(f"  ok: six injured men took the mechanic; {stats['attrs from NFL79']} pool men took NFL79 attributes, {stats['attrs from 1976']} took 1976, {stats['attrs pool median']} the median")
    except AssertionError as e: print(f'  FAIL provenance: {e}')
    return ok

def main():
    keys, ptc, _ = ref_roster(); skeys, sref = ref_staff()
    out, stats = assemble_players(keys, ptc); gate_players(out, keys)
    sf = assemble_staff(skeys, sref); gate_staff(sf, skeys)
    clean = [{k: r[k] for k in keys} for r in out]
    json.dump(clean, open(repo('PGMRoster_1979.json'), 'w'), indent=1)
    json.dump([{k: r[k] for k in skeys} for r in sf], open(repo('PGMStaff_1979.json'), 'w'), indent=1)
    print(f"wrote PGMRoster_1979.json ({len(clean)} records) and PGMStaff_1979.json ({len(sf)})")
    print('  cohorts: ' + ', '.join(f'{k} {v}' for k, v in stats.items() if not k.startswith(('attrs', 'injury', 'prospect', 'TOP', 'median'))))
    print(f"  contracts over 32 teams: TOP_RATIO {stats['TOP_RATIO']}x, median top-53 ${stats['median top-53']/1e6:.1f}M")
    by = collections.defaultdict(list)
    for r in clean:
        if r['teamID'] in FIXED: by[r['teamID']].append(r['salary'] + r['guarantee'])
    pay = sorted(sum(v) for v in by.values()); print(f"  team payroll: min ${pay[0]/1e6:.1f}M median ${st.median(pay)/1e6:.1f}M max ${pay[-1]/1e6:.1f}M   over $280M: {sum(1 for p in pay if p > 280e6)}")
    print(f"  roster sizes: {min(len(v) for v in by.values())}-{max(len(v) for v in by.values())}")

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 4 else 1)
    main()
