#!/usr/bin/env python3
"""
build_2026.py — PGMRoster_2026.json / PGMStaff_2026.json

Stdlib only. No absolute paths (precedent: every tool must run from a clean
clone). Run stages individually or `all`:

    python3 tools/build_2026.py join
    python3 tools/build_2026.py selftest

INPUTS
  sources/nflverse/roster_2026.csv   who is on a roster   (authority: cohort)
  sources/madden/madden_27_launch.csv  how good they are  (authority: ratings)
  wip/PGM3_2026_build_data.json      staff, schemes, weights, draft boards

RULINGS APPLIED (Ryan, 2026-09-01)
  Free agents: Madden record AND years_exp >= 2.  Pool 472, 28% derived.
  Named attribute columns used only where within-position Spearman vs
  OverallRating >= 0.50; percentile fill below that.  Threshold is a CHOSEN
  cut, not a fitted one -- sensitivity at 0.4/0.6 reported in the build log.
"""
import csv, json, os, sys, collections, unicodedata, re, statistics, datetime, random, hashlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*a): return os.path.join(REPO, *a)

CUR_SEASON = 2026

# ---------------------------------------------------------------- vocabulary
# ONE position vocabulary. Madden's labels are a source encoding and are
# translated once, here, at the point of entry (precedent: three translation
# bugs in one build came from carrying two vocabularies around).

TEAM_FROM_MADDEN = {
    '49ers':'SF','Bears':'CHI','Bengals':'CIN','Bills':'BUF','Broncos':'DEN',
    'Browns':'CLE','Buccaneers':'TB','Cardinals':'ARI','Chargers':'LAC',
    'Chiefs':'KC','Colts':'IND','Commanders':'WAS','Cowboys':'DAL',
    'Dolphins':'MIA','Eagles':'PHI','Falcons':'ATL','Giants':'NYG',
    'Jaguars':'JAX','Jets':'NYJ','Lions':'DET','Packers':'GB','Panthers':'CAR',
    'Patriots':'NE','Raiders':'LV','Rams':'LAR','Ravens':'BAL','Saints':'NO',
    'Seahawks':'SEA','Steelers':'PIT','Texans':'HOU','Titans':'TEN',
    'Vikings':'MIN',
}
# nflverse -> PGM3 modern team IDs. nflverse says LA for the Rams.
TEAM_FROM_NFLVERSE = {'LA':'LAR'}

# Madden position -> PGM3's fifteen. LEDG/REDG resolve by team front.
POS_FROM_MADDEN = {
    'QB':'QB','HB':'RB','FB':'RB','WR':'WR','TE':'TE',
    'LT':'OT','RT':'OT','LG':'OG','RG':'OG','C':'C',
    'DT':'DT','MIKE':'MLB','WILL':'OLB','SAM':'OLB',
    'FS':'S','SS':'S','CB':'CB','K':'K','P':'P',
    'LS':None,                      # long snappers are cut (locked decision)
    'LEDG':'EDGE','REDG':'EDGE',    # resolved per team front below
}
PGM3_POSITIONS = ['QB','RB','WR','TE','OT','OG','C','DE','DT','OLB','MLB','S','CB','K','P']

# Coarse family, used only as a join guard. nflverse already ships this
# vocabulary, so the guard compares like with like.
FAMILY_FROM_MADDEN = {
    'WR':{'WR'},'TE':{'TE'},'QB':{'QB'},'K':{'K'},'P':{'P'},'LS':{'LS'},
    'HB':{'RB'},'FB':{'RB'},
    'CB':{'DB'},'FS':{'DB'},'SS':{'DB'},
    'DT':{'DL'},'LEDG':{'DL','LB'},'REDG':{'DL','LB'},
    'MIKE':{'LB'},'WILL':{'LB'},'SAM':{'LB'},
    'LT':{'OL'},'RT':{'OL'},'LG':{'OL'},'RG':{'OL'},'C':{'OL'},
}

# ---------------------------------------------------------------- normaliser
_SUFFIX = re.compile(r'\b(jr|sr|ii|iii|iv|v)\b')

def norm(s):
    """Fold accents to ASCII (never strip -- recurring-bug list), lowercase,
    GLUE periods and apostrophes, SPACE hyphens, drop suffix tokens anywhere.

    The two punctuation rules genuinely differ; this reproduces the face
    registry's own behaviour, measured against its keys rather than against
    its description.  A.J. Brown -> 'aj brown'; Gbaja-Biamila -> two words."""
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace('-', ' ')
    s = re.sub(r"[.'`’]", '', s)
    s = _SUFFIX.sub(' ', s)
    return ' '.join(s.split())

def name_parts(s):
    p = norm(s).split()
    return (p[0], p[-1]) if len(p) >= 2 else (norm(s), norm(s))

# ---------------------------------------------------------------- loaders
def load_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))

def load_madden(path):
    rows = load_csv(path)
    for i, r in enumerate(rows):
        r['_idx']   = i          # stable row identity; normalised NAME is not
                                 # unique -- 7 pairs of real namesakes share one
        r['_team']  = TEAM_FROM_MADDEN[r['Team']]
        r['_norm']  = norm(r['Name'])
        r['_fam']   = FAMILY_FROM_MADDEN[r['Position']]
    return rows

def load_nflverse(path):
    rows = load_csv(path)
    for r in rows:
        r['_team'] = TEAM_FROM_NFLVERSE.get(r['team'], r['team'])
        r['_norm'] = norm(r['full_name'])
        r['_exp']  = int(r['years_exp']) if r['years_exp'] not in ('', 'NA') else 0
    return rows

def madden_pgm3_position(mrow, front_by_team):
    """Madden label -> PGM3 position, resolving edge by the team's real front."""
    p = POS_FROM_MADDEN[mrow['Position']]
    if p == 'EDGE':
        return 'OLB' if front_by_team[mrow['_team']] == '3-4' else 'DE'
    return p

# ---------------------------------------------------------------- the join
class JoinResult:
    def __init__(self):
        self.pairs = []          # (nflverse row, madden row, tier)
        self.unmatched = []
        self.ambiguous = []
        self.tier_counts = collections.Counter()

def build_madden_index(mad):
    idx = collections.defaultdict(list)
    for r in mad:
        idx[r['_norm']].append(r)
    return idx

def madden_birthdate(mrow):
    """Madden ships an Excel serial. Epoch 1899-12-30 absorbs the 1900 leap-year
    bug and reproduces nflverse's ISO birth_date EXACTLY -- verified to the day
    on every one of the seven in-file namesakes, including two men born in the
    same year. Year-level matching is NOT sufficient: Michael Carter and
    Michael Carter II are both 1999."""
    try:
        serial = int(float(mrow['PLYR_BIRTHDATE']))
    except (ValueError, KeyError, TypeError):
        return None
    if serial <= 0: return None
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=serial)

def nflverse_birthdate(nrow):
    bd = (nrow.get('birth_date') or '').strip()
    try:
        return datetime.date(*(int(x) for x in bd.split('-')))
    except (ValueError, TypeError):
        return None

def resolve_namesakes(cands, nrow):
    """Several Madden rows share a normalised name. Separate them on EXACT
    birth date -- the disambiguator a name collision cannot share (precedent:
    a looser position rule is the wrong fix; birth date needs no ruling).
    Returns a single row, or None if birth date cannot separate them."""
    want = nflverse_birthdate(nrow)
    if want is None:
        return None
    keep = [c for c in cands if madden_birthdate(c) == want]
    return keep[0] if len(keep) == 1 else None

def join(nfl_pool, mad, use_team_pass=True):
    """Three tiers, each asserted on MATCH RATE not on output count.
    A fallback exists downstream for every miss, so a count check here is
    dead by construction (precedent: the count assertion could not fail)."""
    idx = build_madden_index(mad)
    res = JoinResult()
    consumed = set()

    # --- tier 1: exact normalised name, resolved TWO-SIDEDLY -------------
    # A normalised name is not a unique key on EITHER side. Madden holds 7
    # pairs of real namesakes; the nflverse pools hold 4 (active) and 2 (free
    # agent). One rule handles both directions: where a name is not 1-to-1,
    # pair on EXACT birth date and refuse whatever does not resolve.
    by_name = collections.defaultdict(list)
    for n in nfl_pool:
        by_name[n['_norm']].append(n)
    still = []
    for key, nlist in by_name.items():
        mlist = idx.get(key, [])
        if not mlist:
            still.extend(nlist); continue
        if len(nlist) == 1 and len(mlist) == 1:
            res.pairs.append((nlist[0], mlist[0], 'exact'))
            res.tier_counts['exact'] += 1
            consumed.add(mlist[0]['_idx'])
            continue
        # collision on one or both sides -- birth date is the only field the
        # collision does not share.
        taken = set()
        for n in nlist:
            want = nflverse_birthdate(n)
            hits = [m for m in mlist
                    if m['_idx'] not in taken and madden_birthdate(m) == want] if want else []
            if len(hits) == 1:
                res.pairs.append((n, hits[0], 'exact+birthdate'))
                res.tier_counts['exact+birthdate'] += 1
                consumed.add(hits[0]['_idx']); taken.add(hits[0]['_idx'])
            else:
                # unresolved: let the later tiers try, then fall through to
                # unmatched. Never guess between two real people.
                still.append(n)

    # --- tier 2: nickname by first-name prefix ------------------------------
    # Same surname, same first initial, one forename a prefix of the other.
    # Only Madden rows nothing has claimed are eligible.
    free = collections.defaultdict(list)
    for k, v in idx.items():
        p = k.split()
        if len(p) < 2: continue
        for r in v:
            if r['_idx'] in consumed: continue
            free[(p[-1], p[0][0])].append(r)
    left = []
    for n in still:
        fn, sn = name_parts(n['full_name'])
        cands = []
        for c in free.get((sn, fn[0]), []):
            cfn, csn = name_parts(c['Name'])
            if csn == sn and cfn[0] == fn[0] and (cfn.startswith(fn) or fn.startswith(cfn)):
                cands.append(c)
        uniq = {c['_norm'] for c in cands}
        if len(uniq) == 1:
            res.pairs.append((n, cands[0], 'nickname-prefix'))
            res.tier_counts['nickname-prefix'] += 1
            consumed.add(cands[0]['_idx'])
        elif len(uniq) > 1:
            res.ambiguous.append((n, cands)); left.append(n)
        else:
            left.append(n)

    # --- tier 3: same team + surname + compatible position family -----------
    # Catches diminutives no prefix rule can reach (Francisco -> Kiko).
    # Requires team AND family agreement, so it cannot merge two men the way
    # a bare prefix rule can.
    final = []
    if use_team_pass:
        pool = [r for v in idx.values() for r in v if r['_idx'] not in consumed]
        for n in left:
            sn = name_parts(n['full_name'])[1]
            cands = [m for m in pool
                     if name_parts(m['Name'])[1] == sn
                     and m['_team'] == n['_team']
                     and n['position'] in m['_fam']]
            uniq = {c['_norm'] for c in cands}
            if len(uniq) == 1:
                res.pairs.append((n, cands[0], 'nickname-team'))
                res.tier_counts['nickname-team'] += 1
                consumed.add(cands[0]['_idx'])
            elif len(uniq) > 1:
                res.ambiguous.append((n, cands)); final.append(n)
            else:
                final.append(n)
    else:
        final = left
    res.unmatched = final
    return res

# ---------------------------------------------------------------- assertions
class AssertionFailed(Exception): pass

def assert_one_to_one(res):
    """No Madden record may be claimed by two nflverse players. This is the
    guard that stopped Francis Mauigoa's ratings landing on Francisco."""
    tgt = [m['_idx'] for _, m, _ in res.pairs]
    dup = [i for i, v in collections.Counter(tgt).items() if v > 1]
    if dup:
        names = sorted({res.pairs[0][1].__class__ and
                        next(m['Name'] for _, m, _ in res.pairs if m['_idx'] == i)
                        for i in dup})
        raise AssertionFailed(f'join not one-to-one; Madden rows claimed twice: {names}')
    return len(tgt)

def assert_match_rate(res, pool, floor):
    """Assert on the RATE, never the count -- every tier below has a fallback
    that keeps the count right by construction."""
    rate = len(res.pairs) / max(1, len(pool))
    if rate < floor:
        raise AssertionFailed(f'match rate {rate:.4f} below floor {floor:.4f} '
                              f'({len(res.pairs)}/{len(pool)})')
    return rate

def assert_no_ambiguous(res):
    if res.ambiguous:
        raise AssertionFailed(f'{len(res.ambiguous)} ambiguous joins refused: '
                              + ', '.join(n["full_name"] for n, _ in res.ambiguous[:5]))
    return 0

# Measured 2026-09-01 on the 1,695-man active cohort: 1,550 of 1,621 matched
# pairs agree on birth date exactly, 95.62%. The 71 that disagree are NOT bad
# joins -- 70 of 71 are the same name on the SAME team at a compatible
# position, and the gaps cluster on 1 day (13) and 365/366 days (13) in BOTH
# directions (40 earlier, 31 later, mean +19.7d, median -1d). That is EA
# data-entry noise, not a systematic offset and not a merge.
#
# So this floor is a gross-failure smoke alarm, NOT a correctness proof. It is
# set at 0.90 because rejecting every disagreement would discard 71 real
# players. Birth date IS authoritative where it is used to SEPARATE namesakes:
# there the candidate set is tiny, and a wrong EA date yields an ambiguous
# refusal (safe) rather than a wrong merge (unsafe).
def assert_birthdates_agree(res, floor=0.90):
    """Independent check that a matched pair is the same man. See the note
    above for why the floor is loose -- the residual is source noise."""
    checked = disagree = 0
    bad = []
    for n, m, tier in res.pairs:
        a, b = nflverse_birthdate(n), madden_birthdate(m)
        if a is None or b is None: continue
        checked += 1
        if a != b:
            disagree += 1
            bad.append((n['full_name'], m['Name'], tier, str(a), str(b)))
    if checked == 0:
        raise AssertionFailed('birth-date check ran over ZERO comparable pairs')
    rate = 1 - disagree / checked
    if rate < floor:
        raise AssertionFailed(f'birth-date agreement {rate:.4f} below {floor:.4f} '
                              f'({disagree}/{checked} disagree)')
    return rate, checked, bad

def assert_positions_translated(mad, front_by_team):
    """Every Madden label must land in PGM3's fifteen or be an explicit cut."""
    bad = set()
    for r in mad:
        if r['Position'] not in POS_FROM_MADDEN:
            bad.add(r['Position']); continue
        p = madden_pgm3_position(r, front_by_team)
        if p is not None and p not in PGM3_POSITIONS:
            bad.add(r['Position'])
    if bad:
        raise AssertionFailed(f'positions with no PGM3 translation: {sorted(bad)}')
    return 0

# ---------------------------------------------------------------- paths
MADDEN_CSV   = P('sources', 'madden',   'madden_27_launch.csv')
NFLVERSE_CSV = P('sources', 'nflverse', 'roster_2026.csv')
BUNDLE       = P('wip', 'PGM3_2026_build_data.json')

def load_all():
    bundle = json.load(open(BUNDLE))
    front  = {t: v['front'] for t, v in bundle['staff_schemes'].items()}
    mad    = load_madden(MADDEN_CSV)
    nfl    = load_nflverse(NFLVERSE_CSV)
    return bundle, front, mad, nfl

# ---------------------------------------------------------------- selftest
def selftest():
    """Prove every assertion FAILS before relying on it passing.
    An assertion that cannot fail reports success, in the same words."""
    bundle, front, mad, nfl = load_all()
    act = [r for r in nfl if r['status'] == 'ACT']
    ok  = []

    def expect_fire(label, fn):
        try:
            fn(); print(f'   FAIL  {label}: did not fire on a broken input'); return False
        except AssertionFailed as e:
            print(f'   ok    {label}: fired -> {str(e)[:72]}'); ok.append(label); return True

    def expect_pass(label, fn):
        try:
            fn(); print(f'   ok    {label}: passes on clean input'); ok.append(label); return True
        except AssertionFailed as e:
            print(f'   FAIL  {label}: fired on CLEAN input -> {e}'); return False

    print('assertion self-test (corrupt an input, watch it fire, restore):')

    good = join(act, mad)

    # 1. one-to-one -- forge a duplicate claim
    broken = JoinResult()
    broken.pairs = list(good.pairs) + [(good.pairs[0][0], good.pairs[1][1], 'forged')]
    expect_fire('one_to_one', lambda: assert_one_to_one(broken))
    expect_pass('one_to_one', lambda: assert_one_to_one(good))

    # 2. match rate -- floor above what is achievable
    expect_fire('match_rate', lambda: assert_match_rate(good, act, 0.999))
    expect_pass('match_rate', lambda: assert_match_rate(good, act, 0.90))

    # 3. non-empty guard -- a rate check over ZERO pairs must not pass silently
    empty = JoinResult()
    expect_fire('match_rate(empty)', lambda: assert_match_rate(empty, act, 0.90))

    # 4. ambiguous refusal -- forge one
    amb = JoinResult(); amb.ambiguous = [(act[0], mad[:2])]
    expect_fire('no_ambiguous', lambda: assert_no_ambiguous(amb))
    expect_pass('no_ambiguous', lambda: assert_no_ambiguous(good))

    # 5. birth-date agreement -- forge a mismatched pair
    bd = JoinResult()
    fake = dict(good.pairs[0][1]); fake['PLYR_BIRTHDATE'] = '11111'
    bd.pairs = [(good.pairs[0][0], fake, 'forged')]
    expect_fire('birthdates', lambda: assert_birthdates_agree(bd))
    expect_fire('birthdates(empty)', lambda: assert_birthdates_agree(JoinResult()))
    expect_pass('birthdates', lambda: assert_birthdates_agree(good))

    # 6. position translation -- forge an untranslatable label
    bad = [dict(mad[0])]; bad[0]['Position'] = 'NICKEL'
    expect_fire('positions', lambda: assert_positions_translated(bad, front))
    expect_pass('positions', lambda: assert_positions_translated(mad, front))

    # 7. appearance invariants -- corrupt one slot at a time
    good_app = ['Head5a','Eyes1a','Hair1d','Beard1b','Eyebrows1a','Nose5d','Mouth5a','Glasses1e','Clothes2']
    expect_pass('appearance', lambda: assert_appearance_valid(good_app))
    expect_fire('appearance(head group)',
                lambda: assert_appearance_valid([*good_app[:5],'Nose4d',*good_app[6:]]))
    expect_fire('appearance(hair group)',
                lambda: assert_appearance_valid([*good_app[:3],'Beard2b',*good_app[4:]]))
    expect_fire('appearance(family 6)',
                lambda: assert_appearance_valid(['Head6a','Eyes1a','Hair1d','Beard1b','Eyebrows1a',
                                                 'Nose6d','Mouth6a','Glasses1e','Clothes2']))
    expect_fire('appearance(glasses)',
                lambda: assert_appearance_valid([*good_app[:7],'Glasses2a',good_app[8]]))
    expect_fire('appearance(vocabulary)',
                lambda: assert_appearance_valid(good_app, vocab={'Head5a'}))
    expect_fire('appearance(slot count)', lambda: assert_appearance_valid(good_app[:8]))

    print(f'\n   {len(ok)} assertion checks passed '
          f'(each fires on a broken record and passes on a clean one)')
    return True

# ---------------------------------------------------------------- stage: join
def stage_join(verbose=True):
    bundle, front, mad, nfl = load_all()
    assert_positions_translated(mad, front)

    act = [r for r in nfl if r['status'] == 'ACT']
    fa_raw = [r for r in nfl if r['status'] in ('CUT', 'W04')]

    res = join(act, mad)
    assert_one_to_one(res)
    assert_no_ambiguous(res)
    rate = assert_match_rate(res, act, 0.95)
    bdrate, bdn, bdbad = assert_birthdates_agree(res)

    if verbose:
        print(f'ROSTERED  {len(act)} active')
        for t in ('exact', 'exact+birthdate', 'nickname-prefix', 'nickname-team'):
            if res.tier_counts[t]:
                print(f'   {t:18s} {res.tier_counts[t]:5d}')
        print(f'   {"TOTAL":18s} {len(res.pairs):5d}  = {100*rate:.2f}%')
        print(f'   {"unmatched":18s} {len(res.unmatched):5d}')
        rk = [r for r in res.unmatched if r['_exp'] == 0]
        print(f'      rookies (exp 0)  {len(rk):5d}   veterans {len(res.unmatched)-len(rk):5d}')
        print(f'   birth-date agreement {100*bdrate:.2f}% over {bdn} pairs '
              f'({len(bdbad)} disagree -- EA data-entry noise, see note in '
              f'assert_birthdates_agree; 70/71 are same name, same team)')

    # free agents: RULING D -- Madden record AND years_exp >= 2
    fres = join(fa_raw, mad, use_team_pass=False)
    assert_one_to_one(fres)
    matched_fa = {n['gsis_id'] for n, _, _ in fres.pairs}
    fa_keep = [r for r in fa_raw if r['gsis_id'] in matched_fa or r['_exp'] >= 2]
    fa_derived = [r for r in fa_keep if r['gsis_id'] not in matched_fa]
    if verbose:
        print(f'\nFREE AGENTS  {len(fa_raw)} post-cut, ruling D (Madden record OR exp>=2)')
        print(f'   with Madden record {len(matched_fa):5d}')
        print(f'   kept               {len(fa_keep):5d}')
        print(f'   of which derived   {len(fa_derived):5d}  = '
              f'{100*len(fa_derived)/max(1,len(fa_keep)):.1f}% of the pool')
        print(f'   dropped            {len(fa_raw)-len(fa_keep):5d}  '
              f'(no Madden record and under 2 years experience)')
    return res, fres, fa_keep, fa_derived

# ---------------------------------------------------------------- main

# ------------------------------------------------- position for unmatched men
# The 74 unmatched active players and the derived free agents have no Madden
# row, so no Madden position. nflverse's `position` is coarse (DB/OL/LB/DL) but
# `depth_chart_position` is fine and 100% populated.
#
# The map from depth_chart_position -> PGM3 position is FITTED on the matched
# pairs, not hand-written (precedent: a hand-written list of what to populate
# is a list of what its author remembered). It is conditioned on the team's
# front, because the same depth-chart label means different things in a 3-4
# and a 4-3.
#
# Where the modal answer is weak, a WEIGHT split is tried as a second axis and
# kept only if it beats the mode under leave-one-out. It helps in exactly the
# cells where the ambiguity is physical -- a 4-3 "OLB" over ~241lb is an edge
# rusher (PGM3 DE), under it an off-ball linebacker -- and not at all for ILB,
# where both roles weigh the same.

def _weight(nrow):
    try: return float(nrow['weight'])
    except (ValueError, KeyError, TypeError): return None

def fit_position_map(pairs, front):
    """Returns {(dcp, front): ('mode', pos) | ('weight', thresh, heavy, light)}"""
    cells = collections.defaultdict(list)
    for n, m in pairs:
        d = (n.get('depth_chart_position') or '').strip()
        p = madden_pgm3_position(m, front)
        if d and p: cells[(d, front[n['_team']])].append((p, _weight(n)))
    rule = {}
    for key, obs in cells.items():
        cnt = collections.Counter(p for p, _ in obs)
        modal = cnt.most_common(1)[0][0]
        mode_acc = cnt[modal] / len(obs)
        best = ('mode', modal); best_acc = mode_acc
        if len(cnt) >= 2:
            (pa, _), (pb, _) = cnt.most_common(2)
            wa = [w for p, w in obs if p == pa and w]
            wb = [w for p, w in obs if p == pb and w]
            if len(wa) >= 5 and len(wb) >= 5:
                heavy, light = (pa, pb) if statistics.median(wa) > statistics.median(wb) else (pb, pa)
                hv = wa if heavy == pa else wb
                lv = wb if heavy == pa else wa
                # leave-one-out over candidate thresholds
                cands = sorted({int(w) for w in hv + lv})
                bt, ba = None, 0.0
                for t in cands:
                    acc = (sum(1 for x in hv if x >= t) + sum(1 for x in lv if x < t)) / (len(hv) + len(lv))
                    if acc > ba: ba, bt = acc, t
                # honest check: refit the threshold without each point
                hits = 0; tot = 0
                for pool, truth in ((hv, heavy), (lv, light)):
                    for i, x in enumerate(pool):
                        h2 = [y for j, y in enumerate(hv) if not (pool is hv and j == i)]
                        l2 = [y for j, y in enumerate(lv) if not (pool is lv and j == i)]
                        if not h2 or not l2: continue
                        t2, a2 = None, 0.0
                        for t in sorted({int(y) for y in h2 + l2}):
                            a = (sum(1 for y in h2 if y >= t) + sum(1 for y in l2 if y < t)) / (len(h2) + len(l2))
                            if a > a2: a2, t2 = a, t
                        pred = heavy if x >= t2 else light
                        hits += (pred == truth); tot += 1
                loo = hits / tot if tot else 0.0
                if loo > mode_acc + 0.02:      # keep only a real improvement
                    best = ('weight', bt, heavy, light); best_acc = loo
        rule[key] = best
    return rule

def apply_position_map(nrow, front, rule, fallback='WR'):
    d = (nrow.get('depth_chart_position') or '').strip()
    key = (d, front.get(nrow['_team'], '4-3'))
    r = rule.get(key)
    if r is None:
        # unseen cell -- fall back to the label ignoring front, then to coarse
        for (dd, ff), rr in rule.items():
            if dd == d: r = rr; break
    if r is None: return fallback
    if r[0] == 'mode': return r[1]
    w = _weight(nrow)
    if w is None: return r[3]      # no weight -> the lighter/off-ball reading
    return r[2] if w >= r[1] else r[3]

# ================================================================ appearances
# Measured on 11,737 modern rostered records (2004/2007/2010/2013/2017/2021):
#
#   slots 0/5/6 (Head/Nose/Mouth) share a family digit   100.00%
#   slots 2/3/4 (Hair/Beard/Eyebrows) share a family     100.00%
#   slot 7 Glasses is 'Glasses1e' for every player       100.00%
#   families run 1-5. FAMILY 6 DOES NOT EXIST in any of the eight published
#   files, so a generator must never emit it.
#
# The HEAD VARIANT LETTER is not drawn -- it is derived, and it is exact:
#       age >= 30            -> the "old" pair    (c/d)   100.0% over 11,737
#       weight >= 253 lb     -> the "heavy" pair  (b/d)
#   giving a:light+young  b:heavy+young  c:light+old  d:heavy+old.
#   Validated jointly at 92.9% against real weights, with essentially all
#   error on the weight axis and none on age -- and that error is an artifact
#   of applying 2026 weights to 2017/2021 records, which is real weight gain.
#   This is why the face registry must write the family digit ONLY: the letter
#   is a function of the player's age and weight IN THAT SEASON.
#
# NOSE and MOUTH variants are INDEPENDENT of the head variant (uniform 25%
# per nose letter, 50/50 mouth) -- only the family is shared. Do not tie them.
#
# HAIR family is strongly conditioned on HEAD family: head 4/5 take hair
# family 1 at 93-96% (black hair), head 1 spreads 18.6/16.7/55.3. Drawing
# hair independently would destroy that joint structure.

APPEARANCE_SLOTS = ['Head','Eyes','Hair','Beard','Eyebrows','Nose','Mouth','Glasses','Clothes']
HEAD_GROUP  = (0, 5, 6)
HAIR_GROUP  = (2, 3, 4)
VALID_FAMILIES = (1, 2, 3, 4, 5)
AGE_OLD_CUT    = 30
WEIGHT_HEAVY_CUT = 253

_FAM = re.compile(r'^([A-Za-z]+)(\d+)(.*)$')
def tok_parts(t):
    m = _FAM.match(t)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (t, None, '')
def tok_family(t):  return tok_parts(t)[1]
def tok_variant(t): return tok_parts(t)[2]

def head_variant(age, weight):
    """Exact, not drawn. See the note above."""
    old   = age is not None and age >= AGE_OLD_CUT
    heavy = weight is not None and weight >= WEIGHT_HEAVY_CUT
    return {(False,False):'a', (False,True):'b',
            (True,False):'c',  (True,True):'d'}[(old, heavy)]

def fit_appearance_library(paths):
    """Everything drawn is drawn from the published files, conditioned on the
    variable that actually governs it. Nothing here is hand-assigned."""
    lib = {
        'head_family': collections.defaultdict(collections.Counter),  # (pos,band)->fam
        'hair_family': collections.defaultdict(collections.Counter),  # headfam->hairfam
        'variants':    collections.defaultdict(collections.Counter),  # (slot,fam)->variant
        'eyes':        collections.Counter(),
        'clothes':     collections.Counter(),
    }
    n = 0
    for p in paths:
        for r in json.load(open(p)):
            if r['teamID'] in ('Rookie', 'Free Agent'): continue
            a = r['appearance']; n += 1
            hf = tok_family(a[0])
            band = 'light' if hf <= 3 else 'dark'
            lib['head_family'][(r['position'], band)][hf] += 1
            lib['hair_family'][hf][tok_family(a[2])] += 1
            for i in (0, 2, 3, 4, 5, 6):
                lib['variants'][(i, tok_family(a[i]))][tok_variant(a[i])] += 1
            lib['eyes'][a[1]] += 1
            lib['clothes'][a[8]] += 1
    lib['_n'] = n
    return lib

def _draw(rng, counter):
    tot = sum(counter.values())
    x = rng.random() * tot
    for k, v in sorted(counter.items()):
        x -= v
        if x <= 0: return k
    return sorted(counter)[-1]

def build_appearance(rng, position, band, age, weight, lib, head_family=None):
    """band supplies the ORDER (which side of light/dark), the published files
    supply the LEVEL (which family within that side, per position).

    head_family, when given, is the face registry's own family for this man and
    OVERRIDES the draw. It must be applied HERE, not as a later overwrite:
    hair family is conditioned on head family, so rewriting the head afterwards
    leaves the hair conditioned on the wrong one. Measured: doing it the late
    way put 79 dark-skinned players in light hair -- Mike Evans at Head4a with
    Hair3a -- and every structural assertion passed on all 79, because both
    family groups were internally consistent and every token was in vocabulary.
    Same shape as "changing a field means rebuilding every field derived from
    it", applied to a field the registry changes at the very end."""
    if head_family is not None:
        hf = head_family
    else:
        hfc = lib['head_family'].get((position, band))
        if not hfc:                   # unseen (position, band) -- pool the position
            hfc = collections.Counter()
            for (p, b), c in lib['head_family'].items():
                if b == band: hfc.update(c)
        hf = _draw(rng, hfc)
    assert hf in VALID_FAMILIES, f'head family {hf} outside 1-5'
    hv = head_variant(age, weight)                 # derived, not drawn
    hair_f = _draw(rng, lib['hair_family'][hf])
    assert hair_f in VALID_FAMILIES, f'hair family {hair_f} outside 1-5'
    out = [None] * 9
    out[0] = f'Head{hf}{hv}'
    out[5] = f'Nose{hf}{_draw(rng, lib["variants"][(5, hf)])}'
    out[6] = f'Mouth{hf}{_draw(rng, lib["variants"][(6, hf)])}'
    out[2] = f'Hair{hair_f}{_draw(rng, lib["variants"][(2, hair_f)])}'
    out[3] = f'Beard{hair_f}{_draw(rng, lib["variants"][(3, hair_f)])}'
    out[4] = f'Eyebrows{hair_f}{_draw(rng, lib["variants"][(4, hair_f)])}'
    out[1] = _draw(rng, lib['eyes'])
    out[7] = 'Glasses1e'                            # 100% of players
    out[8] = _draw(rng, lib['clothes'])
    return out

def archive_band(key, archive):
    """Light calls are reliable at any source count; dark calls need 3+.
    Measured: applying this tightens dark into families 4/5 from 96.3% to
    99.0%, dropping 955 low-confidence calls."""
    a = archive.get(key)
    if not a: return None
    if a['band'] == 'dark' and a.get('n_sources', 0) < 3: return None
    return a['band']

def assert_appearance_valid(app, vocab=None):
    """Structural invariants, each measured at 100% in the published files."""
    if len(app) != 9:
        raise AssertionFailed(f'appearance has {len(app)} slots, expected 9')
    hf = {tok_family(app[i]) for i in HEAD_GROUP}
    if len(hf) != 1:
        raise AssertionFailed(f'slots 0/5/6 families disagree: {[app[i] for i in HEAD_GROUP]}')
    gf = {tok_family(app[i]) for i in HAIR_GROUP}
    if len(gf) != 1:
        raise AssertionFailed(f'slots 2/3/4 families disagree: {[app[i] for i in HAIR_GROUP]}')
    bad = [f for f in (hf | gf) if f not in VALID_FAMILIES]
    if bad:
        raise AssertionFailed(f'family {bad} outside 1-5 (family 6 exists in no published file)')
    if app[7] != 'Glasses1e':
        raise AssertionFailed(f'player glasses {app[7]!r}, expected Glasses1e')
    if vocab is not None:
        novel = [t for t in app if t not in vocab]
        if novel:
            raise AssertionFailed(f'tokens absent from the published vocabulary: {novel}')
    return True

MODERN_REFS = ['PGMRoster_2004.json','PGMRoster_2007.json','PGMRoster_2010.json',
               'PGMRoster_2013.json','PGMRoster_2017.json','PGMRoster_2021.json']

def published_vocabulary(paths):
    v = set()
    for p in paths:
        for r in json.load(open(p)):
            v.update(r['appearance'])
    return v

def band_prior(paths):
    """P(dark | position) from the published files, for players the archive
    has no usable opinion on. A flat league-wide fill is wrong in both
    directions at once; kickers and corners are nothing alike."""
    c = collections.defaultdict(collections.Counter)
    for p in paths:
        for r in json.load(open(p)):
            if r['teamID'] in ('Rookie','Free Agent'): continue
            c[r['position']]['dark' if tok_family(r['appearance'][0]) > 3 else 'light'] += 1
    return c

def name_seed(nrow, position):
    """Seed on the player's name so a rebuild does not reshuffle faces."""
    return int(hashlib.sha256(f"{nrow['_norm']}|{position}".encode()).hexdigest()[:16], 16)

def stage_appearances(verbose=True):
    bundle, front, mad, nfl = load_all()
    refs   = [P(f) for f in MODERN_REFS]
    lib    = fit_appearance_library(refs)
    vocab  = published_vocabulary(refs)
    prior  = band_prior(refs)
    arc    = json.load(open(P('reference','PGM3_PLAYER_ARCHIVE.json')))['players']
    reg    = json.load(open(P('reference','PGM3_FACE_REGISTRY.json')))['faces']

    res  = join([r for r in nfl if r['status'] == 'ACT'], mad)
    pmap = fit_position_map([(n, m) for n, m, _ in res.pairs], front)

    cohort = []
    for n, m, _ in res.pairs:
        pos = madden_pgm3_position(m, front)
        if pos is None: continue                      # long snappers, cut
        cohort.append((n, pos, float(m['Weight']), int(m['Age'])))
    for n in res.unmatched:
        pos = apply_position_map(n, front, pmap)
        w = _weight(n)
        cohort.append((n, pos, w, None))

    src = collections.Counter(); built = []
    for n, pos, w, age in cohort:
        key  = f"{n['_norm']}|{pos}"
        # precedence: the registry knows this man's actual family; the archive
        # knows his band; position is the last resort.
        rf   = tok_family(reg[key][0]) if key in reg else None
        band = ('light' if rf <= 3 else 'dark') if rf else archive_band(key, arc)
        src['registry' if rf else ('archive' if band else 'position-prior')] += 1
        rng  = random.Random(name_seed(n, pos))
        if band is None:
            band = _draw(rng, prior[pos]) if prior.get(pos) else 'dark'
        if age is None:                               # no Madden row -> nflverse
            try:    age = CUR_SEASON - int((n.get('birth_date') or '0000')[:4])
            except ValueError: age = 26
        app = build_appearance(rng, pos, band, age, w, lib, head_family=rf)
        assert_appearance_valid(app, vocab)
        built.append((n, pos, band, app))

    if verbose:
        print(f'APPEARANCES built for {len(built)} rostered players '
              f'(long snappers excluded)')
        for k in ('registry', 'archive', 'position-prior'):
            print(f'   family from {k:16s} {src[k]:5d}  ({100*src[k]/len(built):5.1f}%)')
        print(f'   SOURCED total            {src["registry"]+src["archive"]:5d}  '
              f'({100*(src["registry"]+src["archive"])/len(built):5.1f}%)')
        print(f'   all {len(built)} pass the structural + vocabulary assertions')
    return built, lib, vocab, arc


# ================================================================= attributes
# THE MAP. Two entries differ from the handoff as written on 2026-09-01 and
# both changes were measured, not inferred:
#
#   trucking -> TruckingRating, NOT BreakTackleRating.  Within position against
#   published trucking: RB 0.863/0.417, WR 0.969/0.619, TE 0.927/0.594,
#   QB 0.643/0.383. Anchor: Derrick Henry (247lb) reads Trucking 91 /
#   BreakTackle 92; Christian McCaffrey (205lb) reads 67 / 93. Trucking is
#   running THROUGH people; break-tackle includes evasion.
#   The position MEDIANS point the other way (published WR trucking 74,
#   BreakTackle WR 75, Trucking WR 50) and cannot settle it: a per-position
#   quantile map forces output medians onto the target whichever column feeds
#   it, so only within-position ORDERING distinguishes them.
#
#   skillMove/elusiveness/blockShedding gain named columns the handoff lacks,
#   at within-position 0.885 / 0.827 / 0.608.
#
# ballStrip and discipline stay DERIVED: their best correlate is OverallRating
# (0.666 / 0.652), which wins only because good players score high on
# everything. A column that correlates through overall quality is not a source.
ATTR_MAP = {
    'speed':'SpeedRating', 'burst':'AccelerationRating', 'power':'StrengthRating',
    'agility':'AgilityRating', 'jumping':'JumpingRating', 'stamina':'StaminaRating',
    'tackle':'TackleRating', 'passBlock':'PassBlockRating', 'rushBlock':'RunBlockRating',
    'ballSecurity':'CarryingRating', 'kickAccuracy':'KickAccuracyRating',
    'catching':'CatchingRating', 'intelligence':'AwarenessRating',
    'trucking':'TruckingRating',
    'injuryProne':'InjuryRating',
    'sPassAcc':'ThrowAccuracyShortRating', 'mPassAcc':'ThrowAccuracyMidRating',
    'dPassAcc':'ThrowAccuracyDeepRating', 'throwOnRun':'ThrowOnTheRunRating',
    'routeRun':'ShortRouteRunningRating',
    'vision':'BCVisionRating', 'decisions':'PlayRecognitionRating',
    'releaseLine':'ReleaseRating', 'manCover':'ManCoverageRating',
    'zoneCover':'ZoneCoverageRating',
    'skillMove':'SpinMoveRating', 'elusiveness':'JukeMoveRating',
    'blockShedding':'BlockSheddingRating',
}
INVERTS = {'injuryProne'}          # PGM3 higher = more fragile; Madden the reverse
DERIVED_ATTRS = {'ballStrip', 'discipline', 'greed', 'loyalty', 'ambition'}

# Gated off despite weights.json listing them live. OLB manCover/zoneCover in
# the published files spans 1-3 and 1-1 against MLB's 38-92 and 44-97, and
# every value-1 record in the whole archive for these two fields is an OLB
# (184 and 290 of them, 100%). That is fill, not a rating. Matches 2004, 2007
# and 2017, which gate it off; diverges from 2013 and 2021, which populate it
# with junk. Gating it here also leaves the CB/MLB/S quantile targets clean
# with no separate target-cleaning step.
GATE_OFF = {('OLB', 'manCover'), ('OLB', 'zoneCover')}

def assert_not_degenerate(values, label):
    """A column is fill, not a rating, when its values sit on the floor.

    The precedent is precise and easy to misread: "a rating whose ENTIRE
    OBSERVED RANGE SITS AT OR BELOW 10 is fill". That is max <= 10, not
    max - min <= 10. Published OLB manCover runs 1-3 and zoneCover 1-1 -- floor
    values. Madden CB speed runs 84-96 and WR burst 84-98 -- real values in a
    homogeneous population, because every corner is fast.

    A narrow-spread test rejects the second along with the first. It is the
    same mistake as scoring a column by its correlation with OverallRating:
    both confuse "this population is uniform on this attribute" with "this
    column is not real". Written out because the first implementation here
    made exactly that error and refused CB speed, WR burst and 12 other
    genuine cells."""
    v = sorted(values)
    if len(v) < 8:
        return None
    hi, nd = v[-1], len(set(v))
    if hi <= 10 or nd <= 4:
        raise AssertionFailed(
            f'{label}: degenerate source (max {hi:.0f}, {nd} distinct) — floor values, not a rating')
    return (v[0], hi, nd)

def _target_at(sorted_target, q):
    n = len(sorted_target)
    if n == 1: return sorted_target[0]
    i = q * (n - 1)
    lo = int(i); hi = min(lo + 1, n - 1)
    return sorted_target[lo] + (sorted_target[hi] - sorted_target[lo]) * (i - lo)

def quantile_map(src, target_sorted):
    """Rank-map src onto the target distribution, COLLAPSING TIES.

    Every player sharing a source value gets the target at the block's midpoint
    quantile. Ranking tied values consecutively hands them different targets and
    manufactures separation the source does not contain -- it hit 76% of players
    in the 2013 build, and the overall distribution looks perfect throughout
    because the shape is right. Only checking inside a tied block catches it."""
    n = len(src)
    if n == 0: return []
    blocks = collections.defaultdict(list)
    for i, v in enumerate(src): blocks[v].append(i)
    out = [0] * n
    pos = 0
    for v in sorted(blocks):
        k = len(blocks[v])
        mid = pos + (k - 1) / 2.0
        q = mid / (n - 1) if n > 1 else 0.5
        tv = int(round(_target_at(target_sorted, q)))
        for i in blocks[v]: out[i] = tv
        pos += k
    return out

def fit_quantile_targets(paths, cohort='T'):
    """(position, attribute) -> sorted published values. The LEVEL comes from
    here; the ORDER comes from the Madden column."""
    t = collections.defaultdict(list)
    for p in paths:
        for r in json.load(open(p)):
            if cohort_of(r) != cohort: continue
            for a in ATTR_MAP:
                v = r.get(a)
                if v: t[(r['position'], a)].append(v)
    return {k: sorted(v) for k, v in t.items()}

def cohort_of(r):
    tid = r.get('teamID')
    return 'Rookie' if tid == 'Rookie' else ('FA' if tid == 'Free Agent' else 'T')

def spearman(a, b):
    def rk(x):
        o = sorted(range(len(x)), key=lambda i: x[i]); r = [0]*len(x); i = 0
        while i < len(o):
            j = i
            while j+1 < len(o) and x[o[j+1]] == x[o[i]]: j += 1
            for k in range(i, j+1): r[o[k]] = (i+j)/2.0 + 1
            i = j+1
        return r
    n = len(a)
    if n < 3: return None
    ra, rb = rk(a), rk(b); ma, mb = sum(ra)/n, sum(rb)/n
    num = sum((ra[i]-ma)*(rb[i]-mb) for i in range(n))
    da = sum((x-ma)**2 for x in ra)**.5; db = sum((x-mb)**2 for x in rb)**.5
    return num/(da*db) if da and db else None

def stage_attributes(verbose=True):
    bundle, front, mad, nfl = load_all()
    weights = bundle['weights']
    refs = [P(f) for f in MODERN_REFS]
    targets = fit_quantile_targets(refs, 'T')

    act  = [r for r in nfl if r['status'] == 'ACT']
    resv = [r for r in nfl if r['status'] == 'RES']
    res  = join(act, mad)
    rres = join(resv, mad)
    pmap = fit_position_map([(n, m) for n, m, _ in res.pairs], front)

    # ---- tier 1: a real Madden 27 row -----------------------------------
    rows, tier_of = [], {}
    for n, m, _ in list(res.pairs) + list(rres.pairs):
        pos = madden_pgm3_position(m, front)
        if pos: rows.append((n, m, pos)); tier_of[id(n)] = 1

    # ---- tier 2: 2025 JINX, converted onto the Madden 27 scale -----------
    jinx = load_jinx(P(JINX_2025))
    overlap = []
    for n, m, _ in res.pairs:
        pos = madden_pgm3_position(m, front)
        j = jinx.get(n['_norm'])
        if pos and j: overlap.append((pos, j, m))
    scale = fit_jinx_scale(overlap, front)

    t2 = 0
    for n in list(res.unmatched) + list(rres.unmatched):
        j = jinx.get(n['_norm'])
        if not j: continue
        pos = apply_position_map(n, front, pmap)
        conv = jinx_to_m27_row(j, pos, scale)
        if not conv: continue
        rows.append((n, conv, pos)); tier_of[id(n)] = 2; t2 += 1

    bypos = collections.defaultdict(list)
    for n, m, pos in rows: bypos[pos].append((n, m))

    built = {}
    degen, mapped, gated, partial = [], 0, 0, collections.Counter()
    for pos, group in bypos.items():
        live = set(weights[pos][0])
        for a, col in ATTR_MAP.items():
            if a not in live: continue
            if (pos, a) in GATE_OFF: gated += 1; continue
            tgt = targets.get((pos, a))
            if not tgt: continue
            # a tier-2 row simply lacks the columns .ros does not hold
            have = [(n, m) for n, m in group if col in m]
            partial[a] += len(group) - len(have)
            if len(have) < 8: continue
            raw = [float(m[col]) for _, m in have]
            try:
                assert_not_degenerate(raw, f'{pos}.{a} ({col})')
            except AssertionFailed as e:
                degen.append(str(e)); continue
            src = [-x for x in raw] if a in INVERTS else raw
            out = quantile_map(src, tgt)
            for (n, m), v in zip(have, out):
                built.setdefault(id(n), {})[a] = v
            mapped += 1

    if verbose:
        n1 = sum(1 for v in tier_of.values() if v == 1)
        print(f'ATTRIBUTES')
        print(f'   tier 1  Madden 27 row            {n1:5d} players')
        print(f'   tier 2  2025 JINX -> M27 scale   {t2:5d} players')
        print(f'   (position, attribute) cells mapped : {mapped}')
        print(f'   cells gated off by ruling          : {gated}')
        print(f'   cells refused as degenerate        : {len(degen)}')
        for d in degen: print(f'      {d}')
        miss = {a: c for a, c in partial.items() if c}
        if miss:
            print(f'   tier-2 attributes with NO .ros column (fall through):')
            for a, c in sorted(miss.items(), key=lambda x: -x[1]):
                print(f'      {a:15s} {c:4d} player-cells unfilled')
    return rows, built, targets, weights, tier_of

def conditional_pass(rows, built, verbose=True):
    """Mandatory. Split the output by the SOURCE value and confirm the groups
    differ. Reported within (position) -- a pooled figure mixes fifteen maps
    whose scales legitimately differ and reads low for a reason that has
    nothing to do with whether any individual map works."""
    bundle, front, mad, nfl = load_all()
    bypos = collections.defaultdict(list)
    for n, m, pos in rows: bypos[pos].append((n, m))
    out = []
    for a, col in sorted(ATTR_MAP.items()):
        within, pooled_s, pooled_o = [], [], []
        for pos, group in bypos.items():
            pairs = [(float(m[col]), built.get(id(n), {}).get(a))
                     for n, m in group if a in built.get(id(n), {})]
            if len(pairs) < 8: continue
            s = [x for x, _ in pairs]; o = [y for _, y in pairs]
            if a in INVERTS: s = [-x for x in s]
            r = spearman(s, o)
            if r is not None: within.append((pos, r))
            pooled_s += s; pooled_o += o
        if not within: continue
        rs = sorted(r for _, r in within)
        worst = min(within, key=lambda x: x[1])
        pool = spearman(pooled_s, pooled_o)
        out.append((a, len(within), rs[len(rs)//2], worst, pool))
    if verbose:
        print(f'\nCONDITIONAL PASS — output vs SOURCE, within position')
        print(f'{"attribute":15s} {"pos":>4s} {"median rho":>11s} {"worst":>22s} {"pooled":>8s}')
        for a, n, med, worst, pool in out:
            flag = '' if med > 0.95 else '   <-- CHECK'
            print(f'{a:15s} {n:4d} {med:11.3f} {f"{worst[0]} {worst[1]:.3f}":>22s} '
                  f'{pool if pool is not None else 0:8.3f}{flag}')
    return out


def assert_attribute_coverage(built, rows, weights):
    """Every live (position, attribute) must be accounted for: mapped from a
    source, gated off by ruling, or on the derived list. Nothing may be live
    and silently absent.

    This exists because a hand-written list of what to populate is a list of
    what its author remembered -- the 2000 staff builder left ~30 specialty
    fields at zero and its assertions passed, because they checked the fields
    their author was thinking about."""
    bypos = collections.defaultdict(list)
    for n, m, pos in rows: bypos[pos].append(n)
    missing = []
    for pos, players in bypos.items():
        live = set(weights[pos][0])
        for a in live:
            if (pos, a) in GATE_OFF or a in DERIVED_ATTRS: continue
            have = sum(1 for n in players if a in built.get(id(n), {}))
            if have == 0:
                missing.append(f'{pos}.{a} live but never populated')
            elif have < len(players):
                missing.append(f'{pos}.{a} populated for only {have}/{len(players)}')
    if missing:
        raise AssertionFailed('attribute coverage gaps: ' + '; '.join(missing[:8]))
    return sum(len(set(weights[p][0])) for p in bypos)

def assert_no_gated_values(built, rows):
    """A gated-off cell must be absent, not zero-valued-but-present, and no
    player may carry an attribute his position does not use."""
    bad = []
    for n, m, pos in rows:
        for a in built.get(id(n), {}):
            if (pos, a) in GATE_OFF: bad.append(f'{pos}.{a} present despite being gated off')
    if bad:
        raise AssertionFailed('; '.join(sorted(set(bad))[:5]))
    return True


# =========================================== tier 2: adjacent-year (2025 JINX)
# sources/madden/2025JINXROSTER V21 - PLAY.csv. A one-year gap, which the
# handoff measures at MAE 2.35-2.39 against 8.52 for percentile fill.
#
# Dated from its contents, not its filename (the 2000 archive shipped a 2007
# coach table under a 2000 name): top-rated players are Sewell 25, Parsons 26,
# Lane Johnson 35, McCaffrey 29, Ramsey already on Pittsburgh. Genuinely 2025.
#
# Anchor-tested against Madden 27 over 1,322 overlapping players: PSTR/PRBK
# 1.000, PJMP/PCTH 0.999, PAGI/PTAK 0.998, PACC 0.996, PSPD 0.995, PAWR 0.991,
# PINJ 0.980, PSTA 0.938. Real EA data, and a second confirmation of the
# cross-version stability test.
#
# WHAT IT DOES NOT CARRY. Eight PGM3 attributes have no .ros column at all --
# decisions, releaseLine, manCover, zoneCover, routeRun, skillMove,
# elusiveness, blockShedding. PVIS exists but is DEAD (best correlate
# Awareness 0.222), confirming the handoff on .ros vision. And PBTK is
# BreakTackleRating at 0.999, NOT trucking -- the .ros format has no trucking
# column, so trucking falls back too. Report this per ATTRIBUTE, never per
# player: "34 players on the adjacent-year tier" overstates it.
JINX_2025 = 'sources/madden/2025JINXROSTER V21 - PLAY.csv'
JINX_TO_M27 = {
    'PSPD':'SpeedRating', 'PACC':'AccelerationRating', 'PSTR':'StrengthRating',
    'PAGI':'AgilityRating', 'PJMP':'JumpingRating', 'PSTA':'StaminaRating',
    'PTAK':'TackleRating', 'PPBK':'PassBlockRating', 'PRBK':'RunBlockRating',
    'PCAR':'CarryingRating', 'PKAC':'KickAccuracyRating', 'PCTH':'CatchingRating',
    'PAWR':'AwarenessRating', 'PINJ':'InjuryRating', 'POVR':'OverallRating',
}
# One .ros column feeds all four accuracy fields for these players only. The
# standing ruling (three real columns beat one copied three times) applies
# where three columns EXIST; here only PTHA does.
JINX_PTHA_TARGETS = ['ThrowAccuracyShortRating', 'ThrowAccuracyMidRating',
                     'ThrowAccuracyDeepRating', 'ThrowOnTheRunRating']
JINX_DEAD = {'PVIS'}          # present, carries nothing -- measured 0.222

def load_jinx(path):
    with open(path, encoding='latin-1') as f:
        rows = list(csv.DictReader(f))
    idx = collections.defaultdict(list)
    for r in rows:
        idx[norm(f"{r['PFNA']} {r['PLNA']}")].append(r)
    return {k: v[0] for k, v in idx.items() if len(v) == 1}   # refuse namesakes

def fit_jinx_scale(overlap, front):
    """Per (position, column) map from the JINX distribution onto Madden 27's.

    Fitted on the 1,297-player OVERLAP -- a real population -- not on the 34
    players being converted, which would be ~2 per position and is the
    'a rank-based map needs a population, and four is not one' failure.
    JINX runs +2.32 mean above Madden 27 and the offset is position-dependent
    (RB +7, DE +6, but WR/OG/OT -2), so a flat shift is wrong."""
    src = collections.defaultdict(list); tgt = collections.defaultdict(list)
    for pos, jrow, mrow in overlap:
        for jc, mc in JINX_TO_M27.items():
            try:
                src[(pos, jc)].append(float(jrow[jc]))
                tgt[(pos, jc)].append(float(mrow[mc]))
            except (ValueError, KeyError):
                pass
        # PTHA is ONE .ros column feeding FOUR Madden 27 fields, and those
        # four have different levels (QB medians 84/80/76 across Short/Mid/
        # Deep). Fit PTHA against EACH target separately -- calibrating once
        # against Mid and copying leaves Short 2 low and Deep 1 high, which
        # the seam check caught.
        for mc in JINX_PTHA_TARGETS:
            try:
                src[(pos, 'PTHA', mc)].append(float(jrow['PTHA']))
                tgt[(pos, 'PTHA', mc)].append(float(mrow[mc]))
            except (ValueError, KeyError):
                pass
    return {k: (sorted(src[k]), sorted(tgt[k])) for k in src if len(src[k]) >= 12}

def jinx_to_m27_row(jrow, pos, scale):
    """Convert one JINX player onto Madden 27's scale. Returns a dict keyed by
    Madden 27 column names, carrying ONLY the columns .ros actually holds --
    everything else is absent and falls through to the next tier."""
    out = {}
    def conv(jc):
        key = (pos, jc)
        if key not in scale: return None
        s, t = scale[key]
        try: v = float(jrow[jc])
        except (ValueError, KeyError): return None
        below = sum(1 for x in s if x < v); eq = sum(1 for x in s if x == v)
        q = (below + (eq - 1) / 2.0) / max(1, len(s) - 1)
        return int(round(_target_at(t, min(1.0, max(0.0, q)))))
    for jc, mc in JINX_TO_M27.items():
        if jc in JINX_DEAD: continue
        v = conv(jc)
        if v is not None: out[mc] = v
    for mc in JINX_PTHA_TARGETS:
        key = (pos, 'PTHA', mc)
        if key not in scale: continue
        sr, tr = scale[key]
        try: val = float(jrow['PTHA'])
        except (ValueError, KeyError): continue
        below = sum(1 for x in sr if x < val); eq = sum(1 for x in sr if x == val)
        q = (below + (eq - 1) / 2.0) / max(1, len(sr) - 1)
        out[mc] = int(round(_target_at(tr, min(1.0, max(0.0, q)))))
    return out

def assert_tier_seam(overlap, scale, front, tol=0.35):
    """Validate the JINX -> Madden 27 conversion on players who have BOTH.

    The 1,297 overlap players can be sent down either path, so convert their
    JINX row and compare against their real Madden 27 value. If the conversion
    is sound the two agree; if the scale is wrong they diverge, and no
    structural check downstream could see it.

    An EARLIER version of this check compared the tier-2 cohort's output
    against tier-1's and fired on CB/WR intelligence. That was confounded:
    tier-2 players are late signings and IR bodies, genuinely 5-10 rating
    points worse, and every attribute ran negative (intelligence -0.98 IQR,
    stamina -0.76, speed -0.60, agility 0.00). A cohort-quality gap is not a
    scale error, and a seam test has to hold the cohort fixed to tell them
    apart."""
    diffs = collections.defaultdict(list)
    for pos, jrow, mrow in overlap:
        conv = jinx_to_m27_row(jrow, pos, scale)
        for mc, v in conv.items():
            try: actual = float(mrow[mc])
            except (ValueError, KeyError): continue
            diffs[mc].append(v - actual)
    if not diffs:
        raise AssertionFailed('tier seam check ran over ZERO comparable pairs')
    bad, report = [], []
    for mc, d in sorted(diffs.items()):
        med = statistics.median(d)
        # report the TRUE MAD -- an `or 1.0` divide-guard here made a perfect
        # conversion read as though it had spread, which is a misleading number
        # in a report a later session will trust.
        mad = statistics.median([abs(x - med) for x in d])
        report.append((mc, len(d), med, mad))
        if abs(med) > tol * 5:
            bad.append(f'{mc}: median shift {med:+.1f} over {len(d)} players')
    if bad:
        raise AssertionFailed('tier seam: ' + '; '.join(bad[:6]))
    return report

def seam_report():
    bundle, front, mad, nfl = load_all()
    res = join([r for r in nfl if r['status'] == 'ACT'], mad)
    jinx = load_jinx(P(JINX_2025))
    overlap = []
    for n, m, _ in res.pairs:
        pos = madden_pgm3_position(m, front)
        j = jinx.get(n['_norm'])
        if pos and j: overlap.append((pos, j, m))
    scale = fit_jinx_scale(overlap, front)
    return assert_tier_seam(overlap, scale, front)

# ----------------------------------------------------------------- main
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'join'
    if cmd == 'selftest': selftest()
    elif cmd == 'join':   stage_join()
    elif cmd == 'faces':  stage_appearances()
    elif cmd == 'attrs':
        rows, built, _, weights, tier_of = stage_attributes()
        assert_no_gated_values(built, rows)
        rep = seam_report()
        print(f'   tier-seam assertion: JINX->M27 conversion validated on players'
              f' who have both ({len(rep)} columns)')
        worst = sorted(rep, key=lambda r: -abs(r[2]))[:3]
        for mc, n_, med, mad in worst:
            print(f'      {mc:26s} n={n_:5d}  median shift {med:+5.1f}  MAD {mad:.1f}')
        conditional_pass(rows, built)
    else: print(__doc__); sys.exit(2)
