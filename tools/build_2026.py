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
import csv, json, os, sys, collections, unicodedata, re, statistics, datetime, random, hashlib, math

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

# ============================ position vocabulary at the LOOKUP boundary
# FOURTH boundary-translation bug, found by Ryan in play: three faces wrong,
# 891 lookups silently lost.
#
# The two face sources speak DIFFERENT vocabularies and neither is PGM3's
# build vocabulary at the point of query:
#
#   PGM3_PLAYER_ARCHIVE  2K5's 17 labels — T, G, SS, FS, ILB, FB where PGM3
#                        has OT, OG, S, MLB, RB. A genuine vocabulary gap.
#   PGM3_FACE_REGISTRY   PGM3's exact 15. Its misses are POSITION DRIFT for
#                        the same man (Cameron Jordan DE->OLB), not vocabulary.
#
# Measured before the fix, on 1,888 rostered:
#     archive  832 hit / 583 position-differs / 473 absent
#     registry 1033 hit / 308 position-differs / 547 absent
# Every one of those 891 fell through to a GENERATED face while real data sat
# in the file. Nothing objected, because the build produced a face for every
# record — the identity-mismatch shape a third time, and the reason the guard
# below asserts on the MATCH RATE rather than on output completeness.
POS_FROM_ARCHIVE = {'T': 'OT', 'G': 'OG', 'SS': 'S', 'FS': 'S',
                    'ILB': 'MLB', 'FB': 'RB'}

def index_by_name(index):
    by = collections.defaultdict(set)
    for k in index:
        nm, _, pos = k.rpartition('|')
        by[nm].add(pos)
    return by

def fit_published_appearances(paths):
    """name|position -> the seasons it is attested in a published file, used
    as the ERA TEST. A prospect record is a FUTURE player, so it is dated by
    draftSeason on the game clock, not by the file's nominal year."""
    seen = collections.defaultdict(set)
    for path in paths:
        yr = int(re.search(r'(\d{4})', os.path.basename(path)).group(1))
        for r in json.load(open(path)):
            k = f"{norm(r['forename'] + ' ' + r['surname'])}|{r['position']}"
            seen[k].add(r['draftSeason'] if cohort_of(r) == 'Rookie' else yr)
    return seen

def lookup_by_position(index, by_name, nm, pos, exp, seen):
    """Exact key, then vocabulary translation, then position drift verified by
    ERA. Returns (value, how).

    Position ADJACENCY on its own is refused: applied blindly it merges
    fathers and sons — Antoine Winfield, Jon Runyan, Kris Jenkins, Jeremiah
    Trotter and Michael Pittman are all adjacent-position pairs. The era test
    is a discriminator the collision cannot share, and where several positions
    survive it the answer is REFUSED, not the arbiter's best guess."""
    k = f'{nm}|{pos}'
    if k in index: return index[k], 'exact'
    stored = by_name.get(nm)
    if not stored: return None, 'absent'
    for q in stored:
        if POS_FROM_ARCHIVE.get(q, q) == pos:
            return index[f'{nm}|{q}'], 'translated'
    debut = CUR_SEASON - (exp or 0)
    good = [q for q in stored
            if any(debut - 2 <= s <= CUR_SEASON + 1 for s in seen.get(f'{nm}|{q}', ()))]
    if len(good) == 1: return index[f'{nm}|{good[0]}'], 'era-verified'
    return None, 'ambiguous' if len(good) > 1 else 'unverifiable'

def assert_face_lookup_rate(stats, floor=0.80):
    """Assert on the MATCH RATE, never on output completeness. The build emits
    a face for every record whether the lookup landed or not, so a count check
    is dead by construction here -- that is exactly how 891 losses shipped.

    The denominator is records whose NAME IS PRESENT in the source. A name the
    source has never heard of is not a lookup failure and including it would
    measure the source's coverage instead of the lookup's correctness -- the
    two answer different questions, and mixing them is what let the original
    defect hide.

    Measured: exact-key-only resolves 0.640 of names the sources hold; with
    translation and the era test it resolves 0.864. The floor is 0.80 -- above
    the pre-fix rate by a wide margin and below the achieved rate, so a
    vocabulary regression fires it. The residual 13.6% are DELIBERATE
    refusals: position drift with no published appearance to verify against,
    plus one genuinely ambiguous name."""
    resolvable = sum(v for k, v in stats.items() if k != 'absent')
    if not resolvable:
        raise AssertionFailed('face lookup ran over ZERO resolvable records')
    hit = stats['exact'] + stats['translated'] + stats['era-verified']
    rate = hit / resolvable
    if rate < floor:
        raise AssertionFailed(f'face lookup resolved {rate:.3f} of names the sources '
                              f'hold, below {floor:.3f} ({hit}/{resolvable}) '
                              f'— position vocabulary mismatch?')
    return rate, hit, resolvable

# The documented rule is "light calls reliable at any source count, dark calls
# need 3+ sources". It omits AGREEMENT, and agreement is a real quality signal
# the archive already carries. Scored against the registry as an independent
# check:
#
#   band   agreement      n     matches registry
#   dark   0.50-0.74    176        54.5%   <- a coin flip
#   dark   0.75-0.99     77        75.3%
#   dark   1.00        7800        89.3%
#   light  0.50-0.74    164        64.0%
#   light  1.00         2410       87.6%
#
# Aidan Hutchinson is the case that exposed it: archive `dark`, 4 sources, but
# unanimous False and agreement 0.50. He is exactly the profile the source
# quality doc names -- a recent, prominent player, where a fan setting values
# by eye makes visible errors while getting obscure players right by default.
# Myles Garrett by contrast reads 10 sources, unanimous, agreement 1.00.
ARCHIVE_MIN_AGREEMENT = 0.75

def archive_band(key, archive):
    """Light at any source count; dark at 3+ sources; and EITHER band only
    above the agreement floor. A call the archive itself records as a coin
    flip is not a call."""
    a = archive.get(key)
    if not a: return None
    if a.get('agreement', 1.0) < ARCHIVE_MIN_AGREEMENT: return None
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

def stage_appearances(verbose=True, precomputed=None):
    bundle, front, mad, nfl = load_all()
    refs   = [P(f) for f in MODERN_REFS]
    lib    = fit_appearance_library(refs)
    vocab  = published_vocabulary(refs)
    prior  = band_prior(refs)
    arc    = json.load(open(P('reference','PGM3_PLAYER_ARCHIVE.json')))['players']
    reg    = json.load(open(P('reference','PGM3_FACE_REGISTRY.json')))['faces']
    arc_by, reg_by = index_by_name(arc), index_by_name(reg)
    seen   = fit_published_appearances([P(f) for f in ALL_PUBLISHED])
    how    = collections.Counter(); how_reg = collections.Counter()

    if precomputed is not None:
        # REUSE the caller's rows. Re-deriving them here creates new objects,
        # so every id()-keyed lookup in the assembly missed and 2,107 records
        # fell through to a placeholder face -- five distinct appearances in
        # the whole file. Second instance of this identity bug in one
        # assembly; the first was contracts shipping salary 0.
        cohort = []
        for n, m, pos in precomputed:
            try: wt = float(m['Weight'])
            except (KeyError, ValueError, TypeError): wt = _weight(n)
            try: ag = int(m['Age'])
            except (KeyError, ValueError, TypeError): ag = None
            cohort.append((n, pos, wt, ag))
    else:
        res  = join([r for r in nfl if r['status'] == 'ACT'], mad)
        pmap = fit_position_map([(n, m) for n, m, _ in res.pairs], front)
        cohort = []
        for n, m, _ in res.pairs:
            pos = madden_pgm3_position(m, front)
            if pos is None: continue                  # long snappers, cut
            cohort.append((n, pos, float(m['Weight']), int(m['Age'])))
        for n in res.unmatched:
            pos = apply_position_map(n, front, pmap)
            cohort.append((n, pos, _weight(n), None))

    src = collections.Counter(); built = []
    for n, pos, w, age in cohort:
        key  = f"{n['_norm']}|{pos}"
        # precedence: the registry knows this man's actual family; the archive
        # knows his band; position is the last resort.
        rv, hr = lookup_by_position(reg, reg_by, n['_norm'], pos, n['_exp'], seen)
        how_reg[hr] += 1
        rf = tok_family(rv[0]) if rv else None
        av, ha = lookup_by_position(arc, arc_by, n['_norm'], pos, n['_exp'], seen)
        how[ha] += 1
        band = None
        if rf: band = 'light' if rf <= 3 else 'dark'
        elif av:
            if av.get('agreement', 1.0) >= ARCHIVE_MIN_AGREEMENT and not (
                    av['band'] == 'dark' and av.get('n_sources', 0) < 3):
                band = av['band']
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
        print(f'   archive  lookup: ' + '  '.join(f'{k} {v}' for k, v in how.most_common()))
        print(f'   registry lookup: ' + '  '.join(f'{k} {v}' for k, v in how_reg.most_common()))
        r_, h_, t_ = assert_face_lookup_rate(how_reg + how)
        print(f'   match-rate assertion: {100*r_:.1f}% ({h_}/{t_}) of face lookups landed')
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
    fa_raw = [r for r in nfl if r['status'] in ('CUT', 'W04')]
    res  = join(act, mad)
    rres = join(resv, mad)
    rfa  = join(fa_raw, mad, use_team_pass=False)
    pmap = fit_position_map([(n, m) for n, m, _ in res.pairs], front)

    # RULING D: free agents are those with a Madden record OR >= 2 years of
    # experience. 471 kept of 855, 132 derived = 28.0% of the pool.
    fa_matched = {id(n) for n, _, _ in rfa.pairs}
    fa_keep = [n for n in fa_raw if id(n) in fa_matched or n['_exp'] >= 2]
    fa_keep_ids = {id(n) for n in fa_keep}
    cohort_of_id = {}
    for n in fa_keep: cohort_of_id[id(n)] = 'FA'

    # ---- tier 1: a real Madden 27 row -----------------------------------
    rows, tier_of = [], {}
    for n, m, _ in list(res.pairs) + list(rres.pairs) + list(rfa.pairs):
        if id(n) in cohort_of_id or id(n) not in fa_keep_ids:
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
    for n in list(res.unmatched) + list(rres.unmatched) + [x for x in rfa.unmatched if id(x) in fa_keep_ids]:
        j = jinx.get(n['_norm'])
        if not j: continue
        pos = apply_position_map(n, front, pmap)
        conv = jinx_to_m27_row(j, pos, scale)
        if not conv: continue
        rows.append((n, conv, pos)); tier_of[id(n)] = 2; t2 += 1

    # ---- tier 3: no source at all --------------------------------------
    fine, coarse = fit_tier3_reference(refs)
    t3 = 0
    for n in list(res.unmatched) + list(rres.unmatched) + [x for x in rfa.unmatched if id(x) in fa_keep_ids]:
        if n['_norm'] in jinx: continue
        pos = apply_position_map(n, front, pmap)
        rng = random.Random(name_seed(n, pos))
        rt = tier3_rating(n, pos, fine, coarse, rng)
        if rt is None: continue
        rows.append((n, {'OverallRating': rt}, pos)); tier_of[id(n)] = 3; t3 += 1

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

    # ---- percentile fill for every live cell still empty ----------------
    # tier 2 lacks the attributes .ros has no column for; tier 3 lacks
    # everything. Fill at the player's rating percentile WITHIN his position.
    fillt, ratpool = fit_percentile_fill(refs)
    filled = collections.Counter(); filled_keys = set()
    for n, m, pos in rows:
        live = set(weights[pos][0])
        try: rt = float(m['OverallRating'])
        except (KeyError, ValueError): continue
        rp = percentile_of(ratpool[pos], rt) if ratpool.get(pos) else 0.5
        for a in ATTR_MAP:
            if a not in live or (pos, a) in GATE_OFF: continue
            if a in built.get(id(n), {}): continue
            pool = fillt.get((pos, a))
            if not pool: continue
            built.setdefault(id(n), {})[a] = int(round(_target_at(pool, rp)))
            filled[a] += 1; filled_keys.add((id(n), a))

    if verbose:
        n1 = sum(1 for v in tier_of.values() if v == 1)
        print(f'ATTRIBUTES')
        print(f'   tier 1  Madden 27 row            {n1:5d} players')
        print(f'   tier 2  2025 JINX -> M27 scale   {t2:5d} players')
        print(f'   (position, attribute) cells mapped : {mapped}')
        print(f'   cells gated off by ruling          : {gated}')
        print(f'   cells refused as degenerate        : {len(degen)}')
        for d in degen: print(f'      {d}')
        tot_cells = sum(len(v) for v in built.values())
        nf = sum(filled.values())
        print(f'   tier 3  no source, percentile fill {t3:5d} players')
        print(f'   attribute cells total              : {tot_cells}')
        print(f'   of which SOURCED                   : {tot_cells-nf} '
              f'({100*(tot_cells-nf)/max(1,tot_cells):.1f}%)')
        print(f'   of which percentile-filled         : {nf} '
              f'({100*nf/max(1,tot_cells):.1f}%)')
        top = sorted(filled.items(), key=lambda x: -x[1])[:6]
        print(f'   most-filled attributes: ' + ', '.join(f'{a} {c}' for a, c in top))
    return rows, built, targets, weights, tier_of, filled_keys, cohort_of_id

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
            # only players who actually carry the source column: a tier-2 row
            # lacks the columns .ros has no field for, and tier-3 rows carry
            # no source at all. Measuring a percentile fill against a source it
            # never saw would report a real map as broken.
            pairs = [(float(m[col]), built[id(n)][a])
                     for n, m in group
                     if col in m and a in built.get(id(n), {})]
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

# ========================================= tier 3: no source, percentile fill
# 72 players reach the file this way. The task brief expects rookies to take
# DRAFT POSITION -- that is not available, and the reason is worth stating:
# EA ships 100% of the drafted class (215 of 215 drafted 2026 first-year
# players are in Madden 27). The rookies that are missing are the UNDRAFTED
# ones who made rosters after the file locked, and they have no pick number
# to tier on. draft_number is empty for every one of them.
#
# So the conditioning variables are draft status and experience, both of which
# are real and monotone in the published archive:
#
#              0-1 yr    2-3 yr    4-6 yr     7+ yr
#   undrafted      62        66        70        75
#   drafted        69        74        77        80
#
# Percentile fill is load-bearing by design here, not a failure -- roughly a
# fifth of every draft class reaches every build this way and no amount of
# source work changes it. It is reported as a standing share.
EXP_BANDS = [(1, '0-1 yr'), (3, '2-3 yr'), (6, '4-6 yr'), (99, '7+ yr')]

def exp_band(yrs):
    for hi, _ in EXP_BANDS:
        if yrs <= hi: return hi
    return 99

def fit_tier3_reference(paths):
    """(position, undrafted, band) -> sorted published ratings, with a
    position-pooled fallback for thin cells. A rank drawn against a cohort
    this small would carry no information about level, so the reference has to
    be a real population."""
    fine = collections.defaultdict(list); coarse = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T' or not r.get('draftSeason'): continue
            yrs = CUR_SEASON - r['draftSeason']
            if yrs < 0 or yrs > 20: continue
            key = (r['draftNum'] >= 224, exp_band(yrs))
            fine[(r['position'],) + key].append(r['rating'])
            coarse[key].append(r['rating'])
    return ({k: sorted(v) for k, v in fine.items() if len(v) >= 20},
            {k: sorted(v) for k, v in coarse.items()})

def tier3_rating(nrow, pos, fine, coarse, rng):
    ud = nrow['draft_number'] in ('', 'NA')
    key = (pos, ud, exp_band(nrow['_exp']))
    pool = fine.get(key) or coarse.get((ud, exp_band(nrow['_exp'])))
    if not pool: return None
    return pool[min(len(pool) - 1, int(rng.random() * len(pool)))]

def fit_percentile_fill(paths):
    """(position, attribute) -> sorted values, used to fill at the player's
    rating percentile within his position. The documented fallback when no
    source covers the player at all."""
    t = collections.defaultdict(list); rat = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T': continue
            rat[r['position']].append(r['rating'])
            for a in ATTR_MAP:
                if r.get(a): t[(r['position'], a)].append(r[a])
    return ({k: sorted(v) for k, v in t.items()},
            {k: sorted(v) for k, v in rat.items()})

def percentile_of(sorted_vals, v):
    below = sum(1 for x in sorted_vals if x < v)
    eq    = sum(1 for x in sorted_vals if x == v)
    return (below + (eq - 1) / 2.0) / max(1, len(sorted_vals) - 1)

# ------------------------------------------------- the derived attribute block
# Five attributes have no source column and are derived. Measured on 7,978
# published rostered records:
#
#   the four personality fields are MUTUALLY independent -- every pairwise
#   correlation |r| < 0.04, reproducing the precedent exactly, so they are
#   fitted independently rather than resampled as whole rows.
#
#   BUT they are not alike with respect to RATING. greed, loyalty and ambition
#   are independent of it (-0.012, -0.007, -0.013); discipline is NOT, at
#   +0.543. The precedent tested the four against each other and against
#   injuryProne, not against rating. So discipline is filled at the player's
#   rating percentile and the other three are drawn from the position marginal.
#
#   ballStrip likewise tracks rating at +0.673 and has no source column of its
#   own -- its best correlate in Madden 27 is OverallRating (0.666), which wins
#   only through general player quality and is not a source.
DERIVED_BY_RATING   = {'ballStrip', 'discipline'}
DERIVED_INDEPENDENT = {'greed', 'loyalty', 'ambition'}

def fit_derived_pools(paths):
    t = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T': continue
            for a in DERIVED_ATTRS:
                if r.get(a): t[(r['position'], a)].append(r[a])
    return {k: sorted(v) for k, v in t.items()}

def build_derived(rows, built, weights, pools, ratpool, verbose=False):
    """Fill the derived block. Must run BEFORE the refit: leaving ballStrip at
    zero costs 5-6 rating points at DE/OLB/DT/MLB, which the solver then tries
    to recover by pushing real attributes, and that is exactly the distortion
    the bound assertion exists to catch."""
    made = collections.Counter()
    for n, m, pos in rows:
        attrs = built.get(id(n))
        if attrs is None: continue
        live = set(weights[pos][0])
        try: rt = float(m['OverallRating'])
        except (KeyError, ValueError): continue
        rp = percentile_of(ratpool[pos], rt) if ratpool.get(pos) else 0.5
        rng = random.Random(name_seed(n, pos) ^ 0x9E3779B9)
        for a in DERIVED_ATTRS:
            # greed, loyalty and ambition are NOT in weights.json -- they do
            # not feed the rating -- but they ARE schema fields and every
            # published record populates them. Gating on `live` left all three
            # at 100% zero across every position.
            if a in attrs: continue
            if a not in live and a not in DERIVED_INDEPENDENT: continue
            pool = pools.get((pos, a))
            if not pool: continue
            if a in DERIVED_BY_RATING:
                v = int(round(_target_at(pool, rp)))
            else:
                v = pool[min(len(pool) - 1, int(rng.random() * len(pool)))]
            attrs[a] = max(0, min(99, v))
            made[a] += 1
    return made

# ================================================================= contracts
# The spreadsheet carries _TotalSalary and _SigningBonus and NOTHING ELSE --
# no contract length, no total length, so `length` and `guarantee` are both
# derived. 1,760 players have Madden money; 128 do not and must be drawn.
#
# LENGTH has two constraints and BOTH are required (the handoff is explicit):
#   1. consistent with draftSeason -- the ladder runs 4/3/2/1 by years pro, and
#      the game refuses extensions when length contradicts it;
#   2. the overall marginal is heavily short -- 36% one-year deals, nothing
#      above 7.
# And a third the 1986 build had to learn: within a years-pro bucket the
# published files put BETTER players on LONGER deals, correlation 0.11-0.38.
# Assigning length at random inside each bucket reproduces both marginals to
# two decimal places and destroys that. So the rank is rating blended with
# per-player noise, and the blend weight is FITTED against the reference's own
# within-bucket correlation rather than guessed -- guessed weights came out at
# 0.585 against a 0.353 target in 1986; fitted ones hit 0.357.

def fit_length_reference(paths):
    """(years-pro bucket) -> (length distribution, target corr with rating)."""
    dist = collections.defaultdict(collections.Counter)
    pairs = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T' or not r.get('draftSeason'): continue
            yp = CUR_SEASON - r['draftSeason']
            if not (0 <= yp <= 20): continue
            b = min(yp, 10)
            dist[b][r['length']] += 1
            pairs[b].append((r['length'], r['rating']))
    corr = {}
    for b, v in pairs.items():
        n = len(v)
        mL = sum(x for x, _ in v) / n; mR = sum(y for _, y in v) / n
        num = sum((x - mL) * (y - mR) for x, y in v)
        d1 = sum((x - mL) ** 2 for x, _ in v) ** .5
        d2 = sum((y - mR) ** 2 for _, y in v) ** .5
        corr[b] = num / (d1 * d2) if d1 and d2 else 0.0
    return dist, corr

def _pearson(a, b):
    n = len(a)
    if n < 3: return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = sum((x - ma) ** 2 for x in a) ** .5
    db = sum((x - mb) ** 2 for x in b) ** .5
    return num / (da * db) if da and db else 0.0

def assign_lengths(group, dist, target_corr, seed):
    """group: [(key, rating)]. Returns {key: length} reproducing the bucket's
    published length distribution while hitting its rating correlation."""
    n = len(group)
    if n == 0: return {}
    lens = []
    tot = sum(dist.values())
    for L in sorted(dist):
        lens += [L] * int(round(n * dist[L] / tot))
    while len(lens) < n: lens.append(sorted(dist)[0])
    lens = sorted(lens[:n])
    rng = random.Random(seed)
    noise = {k: rng.random() for k, _ in group}
    by_rating = sorted(range(n), key=lambda i: group[i][1])
    rrank = {}
    for pos_, i in enumerate(by_rating): rrank[i] = pos_ / max(1, n - 1)
    best, best_err = None, 9e9
    for w in [x / 40.0 for x in range(0, 41)]:
        score = [w * rrank[i] + (1 - w) * noise[group[i][0]] for i in range(n)]
        order = sorted(range(n), key=lambda i: score[i])
        out = {}
        for slot, i in enumerate(order): out[group[i][0]] = lens[slot]
        got = _pearson([out[group[i][0]] for i in range(n)],
                       [group[i][1] for i in range(n)])
        err = abs(got - target_corr)
        if err < best_err: best, best_err = out, err
    return best

# --------------------------------------------------------------- money
# PAYROLL BASIS, pinned by measurement and reproducible on a clean clone:
# rank by salary+guarantee, take the top 53, sum salary+guarantee, take the
# median across the 32 teams. That reproduces all eight published files TO THE
# DOLLAR (1986 197,400,001 ... 2021 197,426,500, a $29k spread on $197.4M).
# Ranking by salary instead reads 2017 $20.4M low, so the basis matters.
#
# The engine cap is a fixed ~$280M with no cap field anywhere in the schema,
# so era-accurate dollars leave every team ~$225M of room and the financial
# layer goes inert. That shipped once and was found only by starting a season.
PAYROLL_TARGET = 197_400_000
ENGINE_CAP     = 280_000_000

# Provenance. Every money value carries a tag and every guard checks it before
# firing: a floor written for a drawn value will silently overwrite a sourced
# one and the output still looks reasonable, because looking reasonable is the
# guard's entire job. Jason Elam's real $1,071,167 was pushed to $2,200,000 by
# exactly that, and nothing but the real figure sitting in the next column
# would have caught it.
SRC_MADDEN = 'madden'      # _TotalSalary / _SigningBonus present
SRC_DRAWN  = 'drawn'       # no Madden money -- drawn from the published pool

def fit_money_reference(paths):
    """(position, length) -> sorted published salary and guarantee, in dollars,
    with (position,) and () fallbacks for thin cells. Contracts carry more
    joint structure than any other field group -- salary x rating x position x
    length x guarantee -- so a single-axis fit always loses something. Fitted
    on two axes here, with the third (position) checked afterwards."""
    sal = collections.defaultdict(list); gte = collections.defaultdict(list)
    dropped = 0
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T': continue
            # CLEAN THE TARGET. 37 rostered records carry salary 0 and all of
            # them are in 2017 -- 1.9% of that file, 0.0% of 2010/2013/2021.
            # A quantile map inherits its target's defects, and these also
            # crush any log-scale correlation measured against the reference
            # (log(1)=0 outliers took corr(log salary, rating) from +0.42 to
            # +0.15 and made the published band look far wider than it is).
            if r['salary'] == 0:
                dropped += 1; continue
            for key in ((r['position'], r['length']), (r['position'],), ()):
                sal[key].append(r['salary']); gte[key].append(r['guarantee'])
    return ({k: sorted(v) for k, v in sal.items()},
            {k: sorted(v) for k, v in gte.items()})

def _pool(ref, pos, length):
    for key in ((pos, length), (pos,), ()):
        v = ref.get(key)
        if v and len(v) >= 25: return v
    return ref.get((), [0])

def assign_money(players, ref_sal, ref_gte, rng):
    """players: [(key, pos, length, order_value, provenance)] where
    order_value ranks the player within his (position,length) cell.

    The reference supplies the LEVEL in dollars; the Madden contract supplies
    the ORDER. Ranking on rating instead would apply the published
    rating-salary relationship twice -- the published pool already encodes it,
    which is how 1986 came out at correlation 0.706 against a published 0.520
    and produced four teams over the cap."""
    cells = collections.defaultdict(list)
    for k, pos, ln, ov, prov in players: cells[(pos, ln)].append((k, ov, prov))
    salary, guarantee, prov_of = {}, {}, {}
    for (pos, ln), g in cells.items():
        ps = _pool(ref_sal, pos, ln); pg = _pool(ref_gte, pos, ln)
        g = sorted(g, key=lambda x: (x[1], rng.random()))
        n = len(g)
        for i, (k, ov, prov) in enumerate(g):
            q = i / max(1, n - 1)
            salary[k]   = int(round(_target_at(ps, q)))
            guarantee[k] = int(round(_target_at(pg, q)))
            prov_of[k]  = prov
    return salary, guarantee, prov_of

# RULING (Ryan, 2026-09-01): compress the top of the distribution so no team
# exceeds the engine cap, holding the median at $197.4M exactly.
#
# The constraint is absolute in the archive: 0 of 256 team-seasons across
# eight files exceed $280M, and the highest ever shipped is 2017 at $277.6M.
# Ranking on real _TotalSalary makes 2026 more faithful than any published
# file -- team payroll tracks genuine roster cost at +0.67, where 2013 reads
# -0.57 and 2021 +0.08 because those builds ranked on rating -- and real money
# concentration exceeds what the engine allows. Measured across 12 seeds the
# top team sat at $279.1-281.1M and breached in 7, so it is structural.
#
# p=0.90 lands the maximum at $272.3M, the same ceiling 2013 ships, with the
# median held to the dollar. A global rescale (option C) cleared the cap but
# dropped the median to $193.6M, outside the validator's published band.
PAYROLL_COMPRESS_P = 0.90

def compress_top(salary, guarantee, p=PAYROLL_COMPRESS_P):
    """Power compression about the median. Monotone, so it preserves every
    ordering; it only pulls in the extremes."""
    live = [v for v in salary.values() if v > 0]
    if not live: return
    med = statistics.median(live)
    for k in salary:
        if salary[k] > 0:
            salary[k] = int(round(med * (salary[k] / med) ** p))
        if guarantee[k] > med:
            guarantee[k] = int(round(med * (guarantee[k] / med) ** p))

def scale_to_payroll(salary, guarantee, team_of, target=PAYROLL_TARGET):
    """One uniform multiplier. It preserves every ratio, ordering and anchor
    while making the economy live, which is why the fix is a multiply and not
    a refit."""
    def med_top53():
        by = collections.defaultdict(list)
        for k, t in team_of.items():
            if t: by[t].append(salary[k] + guarantee[k])
        tot = [sum(sorted(v, reverse=True)[:53]) for v in by.values() if v]
        return statistics.median(tot) if tot else 0
    cur = med_top53()
    if cur <= 0: return 1.0
    f = target / cur
    for k in salary:
        salary[k] = int(round(salary[k] * f)); guarantee[k] = int(round(guarantee[k] * f))
    return f

def assert_guards_spared_sourced(before, after, prov_of, tag=SRC_MADDEN):
    """After every guard has run, re-read the sourced records against their
    original values and fail if any moved. Tested against a deliberately
    corrupted record before being trusted -- an assertion that cannot fail
    reports success in the same words as a real pass."""
    sourced = [k for k, p in prov_of.items() if p == tag]
    if not sourced:
        raise AssertionFailed('guard check ran over ZERO sourced records')
    moved = [k for k in sourced if before.get(k) != after.get(k)]
    if moved:
        raise AssertionFailed(f'{len(moved)} sourced contracts moved by a guard, '
                              f'e.g. {moved[:3]}')
    return len(sourced)

# ==================================================================== refit
# Solve attributes toward the target rating through the bundle's position
# weights, bounded by the min/max observed in the published files. This is the
# step that makes the file internally consistent regardless of which tier any
# individual value came from.
#
# The reconstruction is sound: it reproduces published ratings at median |err|
# 0.18-0.46 with a max of 3.5 across 2010/2013/2017/2021.
#
# THE RISK THIS GUARDS. Tier-2 and tier-3 players arrive with a mixture of
# real and percentile-filled cells. A solver closing a rating gap will happily
# push a REAL value a long way to compensate for a filled one, and the result
# stays inside bounds and looks entirely reasonable. So displacement is
# reported split by tier AND by sourced-versus-filled: a generic out-of-range
# count cannot tell "the solver distorted a real value" from "a fill landed at
# an edge", and those need different responses.

def fit_attr_bounds(paths):
    """(position, attribute) -> (min, max) observed in the published files."""
    lo, hi = {}, {}
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'T': continue
            for a in ATTR_MAP:
                v = r.get(a)
                if not v: continue
                k = (r['position'], a)
                lo[k] = min(lo.get(k, v), v); hi[k] = max(hi.get(k, v), v)
    return {k: (lo[k], hi[k]) for k in lo}

def computed_rating(attrs, pos, weights):
    names, coef = weights[pos]
    icept = coef[len(names)] if len(coef) > len(names) else 0.0
    return sum(c * attrs.get(a, 0) for a, c in zip(names, coef)) + icept

# RULING (Ryan, 2026-09-01): cap the per-attribute displacement rather than
# chase rating exactness, with the governing constraint that the refit may not
# drop any attribute's conditional pass below rho 0.95.
#
# An UNCAPPED solve routes almost the whole correction into each position's
# largest coefficient -- kickAccuracy is 1.040 for K and 1.078 for P, 1.8x the
# next attribute -- and takes kickAccuracy from rho 0.995 to 0.441. Every
# structural check still passes: rating exact, values in bounds, distributions
# right. The stored rating is display only and the game recomputes it from
# attributes, so trading a cosmetic field for the field the engine actually
# ranks kickers by is the wrong way round.
#
# CAP = 1 is what the >=0.95 constraint requires. The headline "cap at 3" does
# NOT satisfy it -- measured, 3 attributes fall below (kickAccuracy 0.86,
# mPassAcc 0.93, sPassAcc 0.94). Sensitivity, calibration on:
#
#   cap   rating|err| med / p90    attrs < 0.95   min rho
#     1          1.67 / 7.35             0          0.960
#     2          0.40 / 5.52             1          0.905
#     3          0.25 / 3.65             3          0.860
#     5          0.18 / 0.56             7          0.812
#
# A coefficient-scaled cap was tried and is dominated: at C=2 it reads 1.32
# median error with 4 attributes below 0.95, worse on the protected quantity
# than uniform cap 1 at 1.67 with none.
#
# The p90 rating error of 7.35 is the price and is reported, not buried.
REFIT_CAP = 1

def refit_player(attrs, pos, target, weights, bounds, tol=0.4, iters=60,
                 cap=REFIT_CAP):
    """Least-norm step along the coefficient vector, clipped to the observed
    bounds AND to +/- cap from the incoming value. Returns (attrs, error)."""
    names, coef = weights[pos]
    c = list(coef[:len(names)])
    out, orig = dict(attrs), dict(attrs)
    for _ in range(iters):
        err = target - computed_rating(out, pos, weights)
        if abs(err) < tol: break
        live = []
        for a, ci in zip(names, c):
            if a not in out or ci == 0: continue
            b = bounds.get((pos, a))
            if not b: continue
            lo = max(b[0], orig[a] - cap); hi = min(b[1], orig[a] + cap)
            want_up = (err > 0) == (ci > 0)
            if want_up and out[a] >= hi: continue
            if not want_up and out[a] <= lo: continue
            live.append((a, ci, lo, hi))
        denom = sum(ci * ci for _, ci, _, _ in live)
        if denom == 0: break
        for a, ci, lo, hi in live:
            out[a] = int(round(min(hi, max(lo, out[a] + err * ci / denom))))
    return out, target - computed_rating(out, pos, weights)

def calibrate_positions(rows, built, weights, bounds):
    """Per-position CONSTANT shift so each position's median computed rating
    meets its median target. A constant shift preserves rank order exactly, so
    it costs the conditional pass nothing, and it removes the systematic part
    of the gap so the capped refit only has to absorb per-player residual."""
    bypos = collections.defaultdict(list)
    for n, m, pos in rows:
        if built.get(id(n)) and 'OverallRating' in m: bypos[pos].append((n, m))
    shifts = {}
    for pos, group in bypos.items():
        names, coef = weights[pos]
        sc = sum(coef[:len(names)])
        if not sc: continue
        gaps = [computed_rating(built[id(n)], pos, weights) - float(m['OverallRating'])
                for n, m in group]
        sh = -statistics.median(gaps) / sc
        shifts[pos] = sh
        for n, m in group:
            a = built[id(n)]
            for k in names:
                if k not in a: continue
                b = bounds.get((pos, k)); v = a[k] + sh
                v = min(b[1], max(b[0], v)) if b else v
                a[k] = max(0, min(99, int(round(v))))
    return shifts

def assert_conditional_after_refit(rows, after, floor=0.95):
    """THE GOVERNING CONSTRAINT. The refit may not drop any attribute's
    conditional pass below rho 0.95. Measured within position, against the
    source column, on players who actually carry that column."""
    bypos = collections.defaultdict(list)
    for n, m, pos in rows: bypos[pos].append((n, m))
    bad, rhos = [], {}
    for a, col in ATTR_MAP.items():
        post = []
        for pos, group in bypos.items():
            pr = [(float(m[col]), after[id(n)][a]) for n, m in group
                  if col in m and a in after.get(id(n), {})]
            if len(pr) < 8: continue
            sv = [-x for x, _ in pr] if a in INVERTS else [x for x, _ in pr]
            r = spearman(sv, [y for _, y in pr])
            if r is not None: post.append(r)
        if not post: continue
        rhos[a] = statistics.median(post)
        if rhos[a] < floor: bad.append(f'{a} {rhos[a]:.3f}')
    if not rhos:
        raise AssertionFailed('post-refit conditional check ran over ZERO attributes')
    if bad:
        raise AssertionFailed('refit degraded the conditional pass below '
                              f'{floor}: {", ".join(bad)}')
    return rhos

def assert_refit_bounds(before, after, rows, tier_of, filled_keys, bounds,
                        max_sourced_shift=12.0):
    """Split displacement by tier and by sourced-vs-filled, and refuse a build
    where the solver has moved SOURCED cells materially further than it moves
    tier-1 sourced cells. That is the signature of compensating for a fill by
    distorting real data."""
    disp = collections.defaultdict(list)
    oob = []
    for n, m, pos in rows:
        t = tier_of.get(id(n), 1)
        a0, a1 = before.get(id(n), {}), after.get(id(n), {})
        for a, v in a1.items():
            b = bounds.get((pos, a))
            if b and not (b[0] <= v <= b[1]):
                oob.append(f'{pos}.{a}={v} outside {b}')
            if a in a0:
                kind = 'filled' if (id(n), a) in filled_keys else 'sourced'
                disp[(t, kind)].append(abs(v - a0[a]))
    if oob:
        raise AssertionFailed(f'{len(oob)} attributes outside observed bounds: {oob[:4]}')
    if not disp:
        raise AssertionFailed('refit bound check ran over ZERO cells')
    for (t, kind), v in sorted(disp.items()):
        if kind == 'sourced' and len(v) >= 20:
            med = statistics.median(v)
            if med > max_sourced_shift:
                raise AssertionFailed(
                    f'tier {t} sourced cells displaced by a median of {med:.1f} '
                    f'(limit {max_sourced_shift}) — the solver is compensating '
                    f'for fills by moving real values')
    return {k: (len(v), statistics.median(v)) for k, v in sorted(disp.items())}

def stage_refit(verbose=True):
    rows, built, targets, weights, tier_of, filled_keys, coh = stage_attributes(verbose=False)
    refs   = [P(f) for f in MODERN_REFS]
    bounds = fit_attr_bounds(refs)
    _, ratpool = fit_percentile_fill(refs)
    made = build_derived(rows, built, weights, fit_derived_pools(refs), ratpool)
    shifts = calibrate_positions(rows, built, weights, bounds)
    for a in made: filled_keys.update()      # derived cells count as filled
    for n, m, pos in rows:
        for a in DERIVED_ATTRS:
            if a in built.get(id(n), {}): filled_keys.add((id(n), a))
    if verbose:
        print(f'DERIVED BLOCK built before the refit: '
              + ', '.join(f'{a} {c}' for a, c in sorted(made.items())))
    before = {k: dict(v) for k, v in built.items()}
    after, errs = {}, []
    for n, m, pos in rows:
        attrs = built.get(id(n))
        if not attrs: continue
        try: target = float(m['OverallRating'])
        except (KeyError, ValueError): continue
        new, err = refit_player(attrs, pos, target, weights, bounds)
        after[id(n)] = new; errs.append(abs(err))
    rep = assert_refit_bounds(before, after, rows, tier_of, filled_keys, bounds)
    rhos = assert_conditional_after_refit(rows, after)
    if verbose:
        errs.sort()
        print(f'REFIT — {len(after)} players solved against the bundle weights')
        print(f'   |rating error| after refit: median {statistics.median(errs):.2f}  '
              f'p90 {errs[int(.9*len(errs))]:.2f}  max {max(errs):.2f}')
        print(f'   within tolerance (<0.4): '
              f'{100*sum(1 for e in errs if e < 0.4)/len(errs):.1f}%')
        print(f'   attributes outside observed bounds: 0 (asserted)')
        print(f'   post-refit conditional pass: min rho '
              f'{min(rhos.values()):.3f} ({min(rhos, key=rhos.get)}), '
              f'median {statistics.median(list(rhos.values())):.3f} '
              f'— all 28 above the 0.95 floor (asserted)')
        print()
        print(f'   DISPLACEMENT, split by tier and provenance:')
        print(f'   {"tier":>4s} {"provenance":>11s} {"cells":>7s} {"median |shift|":>15s}')
        for (t, kind), (nn, med) in rep.items():
            print(f'   {t:4d} {kind:>11s} {nn:7d} {med:15.1f}')
    return rows, after, tier_of

def stage_contracts(verbose=True, precomputed=None):
    """length -> salary/guarantee -> scale to $197.4M -> compress under the cap.
    Every money value carries a provenance tag and the guard assertion runs
    after all guards, against the pre-guard snapshot."""
    bundle, front, mad, nfl = load_all()
    refs = [P(f) for f in MODERN_REFS]
    dist, corr = fit_length_reference(refs)
    ref_sal, ref_gte = fit_money_reference(refs)
    # REUSE the caller's rows when given. Re-running stage_attributes here
    # creates new objects, so every id()-keyed lookup in the assembly missed
    # and the whole file shipped with salary 0 -- correct record count, no
    # money. Identity is not a value; do not key across independent builds.
    if precomputed is not None:
        rows, built, _, weights, tier_of, _fk, coh = precomputed
    else:
        rows, built, _, weights, tier_of, _fk, coh = stage_attributes(verbose=False)

    players = []
    for n, m, pos in rows:
        if id(n) in coh: continue          # free agents: salary/length/teamNum 0
        try: rt = float(m['OverallRating'])
        except (KeyError, ValueError): continue
        players.append((n, m, pos, rt))

    # --- length ---------------------------------------------------------
    buckets = collections.defaultdict(list)
    for n, m, pos, rt in players: buckets[min(n['_exp'], 10)].append((id(n), rt))
    lengths = {}
    for b, g in buckets.items():
        b2 = b if b in dist else min(dist, key=lambda x: abs(x - b))
        lengths.update(assign_lengths(g, dist[b2], corr[b2], seed=1000 + b))

    # --- money ----------------------------------------------------------
    src = [float(m['_TotalSalary']) for n, m, pos, rt in players
           if m.get('_TotalSalary') not in (None, '')]
    lo, hi = min(src), max(src)
    rng = random.Random(2026)
    plist, team_of = [], {}
    for n, m, pos, rt in players:
        k = id(n); ts = m.get('_TotalSalary')
        if ts not in (None, ''):
            ov = (math.log(float(ts) + 1) - math.log(lo + 1)) / (math.log(hi + 1) - math.log(lo + 1))
            prov = SRC_MADDEN
        else:
            ov = rt / 100.0; prov = SRC_DRAWN
        plist.append((k, pos, lengths[k], ov, prov)); team_of[k] = n['_team']
    salary, guarantee, prov_of = assign_money(plist, ref_sal, ref_gte, rng)
    # NO SALARY FLOOR GUARD, deliberately. Measured: the built distribution
    # runs min $2,171 / p1 $23,608, inside what the archive already contains
    # (2017 ships min $1,012 / p1 $37,456). A floor written for drawn values
    # would fire on sourced ones and the output would still look reasonable --
    # that is how Jason Elam's real $1,071,167 became $2,200,000. Confirm the
    # defect is present before fixing it; here it is not. prov_of is carried
    # so that any guard added later can check provenance before firing, and
    # assert_guards_spared_sourced exists for that moment.
    f = scale_to_payroll(salary, guarantee, team_of)
    snapshot = {k: (salary[k], guarantee[k]) for k in salary}
    compress_top(salary, guarantee)
    scale_to_payroll(salary, guarantee, team_of)

    by = collections.defaultdict(list)
    for k, t in team_of.items(): by[t].append(salary[k] + guarantee[k])
    tot = sorted(sum(sorted(v, reverse=True)[:53]) for v in by.values())
    med = statistics.median(tot)
    over = sum(1 for x in tot if x > ENGINE_CAP)
    if over:
        raise AssertionFailed(f'{over} team(s) over the ${ENGINE_CAP/1e6:.0f}M engine cap '
                              f'(max ${tot[-1]/1e6:.1f}M) — 0 of 256 published team-seasons breach it')
    if abs(med - PAYROLL_TARGET) > 1_000_000:
        raise AssertionFailed(f'median team payroll ${med/1e6:.1f}M off the '
                              f'${PAYROLL_TARGET/1e6:.1f}M convention')
    # guarantee must rise with remaining length
    ratios = {}
    for L in range(1, 8):
        g = [guarantee[k] / salary[k] for k, _, ln, _, _ in plist if ln == L and salary[k] > 0]
        if len(g) >= 10: ratios[L] = statistics.median(g)
    # Match the validator exactly: median ratio at length 1 vs length >= 5.
    # A strictly-monotone-by-bucket test would be WRONG -- the published files
    # are not monotone either (2013 reads 6yr 0.44 against 5yr 1.67, 2021 reads
    # 3yr 0.10 against 2yr 0.22), and the long buckets are thin.
    r1 = [guarantee[k] / salary[k] for k, _, ln, _, _ in plist if ln == 1 and salary[k] > 0]
    r5 = [guarantee[k] / salary[k] for k, _, ln, _, _ in plist if ln >= 5 and salary[k] > 0]
    n1 = statistics.median(r1) if r1 else 0.0
    n5 = statistics.median(r5) if r5 else 0.0
    if not (n5 > n1):
        raise AssertionFailed(f'guarantee/salary 1yr={n1:.2f} 5yr={n5:.2f} — must rise with length')
    ks = sorted(ratios)

    if verbose:
        print(f'CONTRACTS for {len(salary)} rostered players')
        print(f'   sourced (Madden money) {sum(1 for v in prov_of.values() if v==SRC_MADDEN):5d}'
              f'   drawn {sum(1 for v in prov_of.values() if v==SRC_DRAWN):4d}')
        print(f'   length: 1-yr {100*sum(1 for v in lengths.values() if v==1)/len(lengths):.1f}%'
              f'   max {max(lengths.values())}')
        print(f'   median team payroll ${med/1e6:.1f}M (top-53, salary+guarantee)  target $197.4M')
        print(f'   team range ${tot[0]/1e6:.1f}M - ${tot[-1]/1e6:.1f}M   over the $280M engine cap: {over}')
        print(f'   guarantee/salary by length: ' + '  '.join(f'{L}yr {ratios[L]:.2f}' for L in ks))
    return plist, salary, guarantee, prov_of, lengths, team_of, snapshot

# =============================================================== draft classes
# RULING (Ryan, 2026-09-01): ship 2027 and 2028 ONLY. 2029 and 2030 are
# dropped -- they would have been ~600 fully invented people with no real
# names behind them. This DIVERGES from every published file, which all carry
# four classes, and belongs in the Reddit post's "what's not real" section
# because anyone used to the historical files will expect four.
#
# POTENTIAL: level from board rank, plus a rank-scaled PROBABILITY of a large
# gap. Not rank-scaled variance -- that was the original proposal and the
# archive refutes it.
#
# MEASURED, on rostered players by the slot they were drafted at (what they
# actually became, NOT the published `potential` field, which was itself built
# by slot-baseline-plus-career-raise and would only measure the method):
#
#   band        n     median  IQR   max   share >=85
#   1-10      382         83   11    98      40.3%
#   11-32     753         81   12    98      33.2%
#   33-64     901         77   12    98      22.2%
#   65-105    991         73   12    98      12.3%
#   106-150   907         71   11    98       8.4%
#   151-200   852         68   10    98       4.7%
#   201-223   313         67    9    96       5.4%
#   224 UDFA 2879         65   12    98       3.8%
#
# The IQR is FLAT at 9-12 across every band and the ceiling is 98 everywhere,
# including undrafted. What falls with draft position is the MEDIAN (83->65)
# and the HIT RATE (40.3%->3.8%). So uncertainty is roughly constant and
# widening variance at the bottom would fit an assumption rather than the data
# -- and would quietly fill round six with decent players.
#
# CAVEAT, and it must travel with the finding: this measures ROSTERED players,
# so busts are not in the archive to be measured. The flat IQR is CONDITIONAL
# ON MAKING A ROSTER; unconditionally the spread at low picks is wider. It is
# still the right read for a CEILING -- the game simulates the bust when
# potential is not reached -- but "spread is flat by draft position" is false
# without that conditioning.
#
# THE HOLE THIS FIXES: published prospects have 0.0-0.1% with potential >= 85
# below pick 64, against a real rostered outcome of 4.9% at pick 106+. The
# published files contain no late steals at all.
#
# Late-round hits also CLUSTER by position (pick 106+, rating >= 85):
#   C 8.7%  OG 7.6%  QB 6.7%  OT/CB 5.3%  WR 4.4%  DE 4.2%  MLB 3.9%
#   TE 3.7%  DT/S 3.6%  RB 2.2%  OLB 1.7%
# K and P read 15.0% and 13.1% and are EXCLUDED as an artifact -- kickers are
# almost never drafted early, so every good one counts as a late hit. The 2027
# board carries no K/P prospects in any case.
#
# GAP CONSTRAINT: the archive runs median 6, p90 12, max 23-28 (2000 is the
# documented divergence at 40). No cap tighter than that. The 2013 build
# capped the gap at 14 -- EXACTLY the reference p90 -- which is why it
# compressed the top and put Louis Nix above Aaron Donald. A cap set at the
# 90th percentile of the reference is not a safety margin, it is a guarantee
# of clipping the tail. That generalises well past 2013.
DRAFT_CLASSES = [2027, 2028]
LATE_HIT_RATE = 0.049          # pick 106+, measured
HIT_POTENTIAL = (85, 95)
# The archive's own maximum prospect gap is 23-28 (2000 diverges at 40). A hit
# must therefore be a good player who SLID, not a bad one leaping 42 points --
# the first cut of this produced a rating-52 tackle with a 94 ceiling, a gap of
# 42, wider than anything the archive contains. Bounding the gap at the
# reference maximum is not the 2013 mistake: 28 is the archive MAX, where 2013
# capped at 14, its p90.
MAX_PROSPECT_GAP = 28

POSITION_HIT_RATE = {           # pick 106+, rating >=85; K/P excluded
    'C': 8.7, 'OG': 7.6, 'QB': 6.7, 'OT': 5.3, 'CB': 5.3, 'WR': 4.4,
    'DE': 4.2, 'MLB': 3.9, 'TE': 3.7, 'DT': 3.6, 'S': 3.6, 'RB': 2.2,
    'OLB': 1.7,
}

# The bundle maps the boards' coarse labels wholesale -- every `LB` becomes
# MLB and every `EDGE` becomes DE -- which leaves the draft pool with ZERO
# OLBs and fails the validator's "draft pool missing a LB type" check. PGM3's
# OLB carries both 3-4 edge rushers and weak-side backers, so both source
# labels feed it. Published prospect pools run MLB 24.3% / OLB 32.2% /
# DE 43.5% across 2013+2017+2021, and the split below reproduces that while
# respecting the semantics: MLB can only come from `LB`, DE only from `EDGE`,
# OLB from either. Allocation is seeded on the player's name so it is
# reproducible and NOT correlated with board rank.
PROSPECT_LB_SPLIT = {'LB': (('MLB', 0.54), ('OLB', 0.46)),
                     'EDGE': (('DE', 0.81), ('OLB', 0.19))}

def prospect_positions(records):
    """Assign by SORTED HASH so the counts are exact. Drawing each prospect
    independently against a probability leaves small-sample variance -- 26
    linebackers split 65/35 instead of 54/46 on the first attempt, which put
    OLB at 17.5% of the LB+EDGE group against a published 32.2%."""
    out = {}
    groups = collections.defaultdict(list)
    for i, rec in enumerate(records):
        raw = rec.get('pos_raw')
        if raw in PROSPECT_LB_SPLIT: groups[raw].append(i)
        else: out[i] = rec['position']
    for raw, idxs in groups.items():
        idxs = sorted(idxs, key=lambda i: hashlib.sha256(
            norm(records[i]['name']).encode()).hexdigest())
        n = len(idxs); start = 0
        rule = PROSPECT_LB_SPLIT[raw]
        for j, (pos, share) in enumerate(rule):
            take = n - start if j == len(rule) - 1 else int(round(share * n))
            for i in idxs[start:start + take]: out[i] = pos
            start += take
    return [out[i] for i in range(len(records))]

def fit_prospect_curve(paths):
    """slot -> sorted published prospect ratings and gaps, for the LEVEL."""
    rt = collections.defaultdict(list); gp = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            if cohort_of(r) != 'Rookie' or not r.get('draftNum'): continue
            b = _slot_band(r['draftNum'])
            rt[b].append(r['rating']); gp[b].append(r['potential'] - r['rating'])
    return ({k: sorted(v) for k, v in rt.items()},
            {k: sorted(v) for k, v in gp.items()})

def _slot_band(pick):
    for hi in (10, 32, 64, 105, 150, 200, 223, 300):
        if pick <= hi: return hi
    return 300

def hit_probability(pick, position):
    """Rank-scaled probability of a large gap, weighted by the position's
    measured late-hit rate. Calibrated to the pick-106+ figure specifically --
    round seven and undrafted behave differently from round four."""
    # Calibrated against the ELIGIBLE population, not everyone: with the gap
    # bounded at 28, only ~60% of pick-106+ prospects are rated high enough to
    # reach 85 at all, so the raw probability has to be scaled up by ~1.67x to
    # land the observed rate. Result: 106+ hits at 5.4% against a measured
    # 4.9%, with 5.6% of the whole class carrying a hit.
    if pick <= 32:   base = 0.0        # the top is already high by level
    elif pick <= 64: base = 0.024
    elif pick <= 105: base = 0.048
    elif pick <= 150: base = 0.096
    elif pick <= 200: base = 0.056
    else:            base = 0.048
    mean_rate = sum(POSITION_HIT_RATE.values()) / len(POSITION_HIT_RATE)
    w = POSITION_HIT_RATE.get(position, mean_rate) / mean_rate
    return min(0.35, base * w)

def build_prospect(rank, position, season, rt_curve, gp_curve, rng):
    """rating from the slot curve; potential = rating + gap, raise-only."""
    b = _slot_band(rank)
    rts = rt_curve.get(b) or rt_curve[max(rt_curve)]
    gps = gp_curve.get(b) or gp_curve[max(gp_curve)]
    q = rng.random()
    rating = int(round(_target_at(rts, q)))
    gap = int(round(_target_at(gps, rng.random())))
    if rng.random() < hit_probability(rank, position):
        target = rng.randint(*HIT_POTENTIAL)
        gap = max(gap, target - rating)
    gap = min(gap, MAX_PROSPECT_GAP)
    potential = min(99, max(rating, rating + gap))   # raise-only
    return rating, potential

# ===================================================================== staff
# 32 teams x 9 roles in every published file, no exceptions: Head Coach, Off
# Co-ord, Def Co-ord, Special Teams, Head Scout, Off Scout, Def Scout, Head
# Physio, Assistant Physio. A vacant real-world coordinator still needs a body.
STAFF_ROLES = ['Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams',
               'Head Scout', 'Off Scout', 'Def Scout',
               'Head Physio', 'Assistant Physio']
STAFF_FILES = ['PGMStaff_2010.json', 'PGMStaff_2013.json',
               'PGMStaff_2017.json', 'PGMStaff_2021.json']
PRIMARY_ATTR = {'Head Coach': 'HCcoach', 'Off Co-ord': 'OCcoach',
                'Def Co-ord': 'DCcoach', 'Special Teams': 'STcoach',
                'Head Scout': 'Hscout', 'Off Scout': 'Oscout',
                'Def Scout': 'Dscout', 'Head Physio': 'Hphysio',
                'Assistant Physio': 'Aphysio'}

def fit_staff_profile(paths, live_threshold=0.5):
    """role -> {field: sorted published values} for every field the role
    actually populates, plus the donor pool of whole growthType arrays.

    MEASURED, never hand-listed. The first 2000 staff builder hand-listed which
    attributes each role carries and left ~30 specialty fields at zero --
    management, motivation, playcalling, passRush, playDesign, injPrevent,
    reInjuryRisk. That is the bug the handoff records as having CRASHED THE
    GAME, and its assertions passed because they checked the fields their
    author was thinking of."""
    recs = []
    for path in paths:
        for r in json.load(open(path)):
            if r.get('teamID') not in ('Free Agent', ''): recs.append(r)
    skip = {'age', 'rating', 'potential', 'startSeason', 'salary', 'guarantee',
            'length', 'eSalary', 'eGuarantee', 'eLength'}
    numeric = [k for k, v in recs[0].items() if isinstance(v, int) and k not in skip]
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    cnt = collections.Counter()
    donors = collections.defaultdict(list)
    for r in recs:
        role = r['role']; cnt[role] += 1
        for k in numeric:
            if r.get(k): by[role][k].append(r[k])
        donors[(role, r['potential'] - r['rating'])].append(r['growthType'])
    live = {}
    for role in cnt:
        live[role] = {k: sorted(v) for k, v in by[role].items()
                      if len(v) / cnt[role] > live_threshold}
    return live, donors, recs

def fit_startseason(paths, bin_w=3):
    """age bucket -> sorted published ABSOLUTE startSeason values.

    ABSOLUTE, not offset by the file's season. Every published file runs on
    the GAME'S internal clock where the current season is 2026, whatever year
    the file models -- the handoff states this for draftSeason and startSeason
    behaves identically: 2010, 2013, 2017 and 2021 all top out at 2024-2026.
    Subtracting the file year manufactured offsets up to +14 (a 2013 coach
    reading "season + 13") and put 47% of the build on the clamp.

    startSeason is a function of age (r -0.95 to -0.99 in every modern file),
    which is exactly why a wrong age is dangerous: it produces a wrong
    startSeason WHILE THE CORRELATION STAYS PERFECT. A derived field agreeing
    with its source proves the derivation, never the source.

    NOT a linear fit plus gaussian noise. That was tried and it piles records
    onto the clamp: feeding the PUBLISHED 2021 ages through the fitted line
    produced 18% sitting at the season against their actual 3%, so the
    parametric form was wrong independently of the cohort. Sampling the
    reference's own conditional distribution reproduces the real shape,
    including how it behaves near the ceiling, without my having to guess a
    functional form.

    (The pooled-fit version was worse still -- files' intercepts genuinely
    differ, 47.2 in 2010 against 35.5 in 2021, so a pooled residual reports
    BETWEEN-file spread as within-file noise: sd 4.69 against 2.04 per file,
    and 52% on the clamp.)"""
    by = collections.defaultdict(list)
    for path in paths:
        yr = int(re.search(r'(\d{4})', os.path.basename(path)).group(1))
        for r in json.load(open(path)):
            if r.get('teamID') in ('Free Agent', ''): continue
            by[r['age'] // bin_w].append(r['startSeason'])
    return {k: sorted(v) for k, v in by.items()}, bin_w

def draw_startseason(age, table, bin_w, rng):
    key = age // bin_w
    pool = table.get(key)
    if not pool:
        near = sorted(table, key=lambda k: abs(k - key))
        pool = table[near[0]]
    return pool[min(len(pool) - 1, int(rng.random() * len(pool)))]

def donor_growth(donors, role, gap, rng):
    """Copy a whole published growthType array matched on (role, potential
    minus rating). Donor copying is SAFE here -- a growth curve is a fact about
    the job, not about the man -- and matching on the gap makes the 50x rule
    hold by construction rather than by arithmetic I have to get right.
    It also reproduces slot structure the handoff describes imprecisely:
    slots 17-19 are NEARLY always zero (19 of 1152 records, not always) and
    positives trail to slot 26 rather than stopping at 16."""
    for key in ((role, gap), (None, gap)):
        pool = donors.get(key) if key[0] else [v for (r_, g_), vs in donors.items()
                                               if g_ == gap for v in vs]
        if pool: return list(rng.choice(pool))
    near = sorted(donors, key=lambda k: abs(k[1] - gap))
    for k in near:
        if donors[k]: return list(rng.choice(donors[k]))
    return [0] * 51

def assert_staff_structure(staff, real_names):
    """Every gate the archive enforces, checked here rather than at import."""
    by_team = collections.defaultdict(list)
    for s in staff: by_team[s['teamID']].append(s)
    bad = [t for t, v in by_team.items() if len(v) != 9]
    if bad: raise AssertionFailed(f'teams without exactly 9 staff: {bad[:5]}')
    for t, v in by_team.items():
        got = collections.Counter(x['role'] for x in v)
        missing = [r for r in STAFF_ROLES if got[r] != 1]
        if missing: raise AssertionFailed(f'{t} role slots wrong: {missing}')
    for s in staff:
        pa = PRIMARY_ATTR[s['role']]
        if s.get(pa) != s['rating']:
            raise AssertionFailed(f"{s['forename']} {s['surname']}: primary attr "
                                  f"{pa}={s.get(pa)} != rating {s['rating']}")
        if len(s['growthType']) != 51:
            raise AssertionFailed(f"growthType has {len(s['growthType'])} elements, expected 51")
        pos = sum(x for x in s['growthType'] if x > 0)
        if pos != (s['potential'] - s['rating']) * 50:
            raise AssertionFailed(f"50x rule broken for {s['surname']}: {pos} != "
                                  f"{(s['potential']-s['rating'])*50}")
        if not (1989 <= s['startSeason'] <= 2026):
            raise AssertionFailed(f"startSeason {s['startSeason']} outside 1989-2026")
    invented = {norm(f"{s['forename']} {s['surname']}") for s in staff
                if s['role'] in ('Head Scout', 'Off Scout', 'Def Scout',
                                 'Head Physio', 'Assistant Physio')}
    clash = invented & real_names
    if clash:
        raise AssertionFailed(f'{len(clash)} invented scout/physio names collide with real '
                              f'coaches: {sorted(clash)[:5]}')
    return len(staff)

def _uuid(rng):
    h = '%032X' % rng.getrandbits(128)
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'

def load_staff_ages(path, roles_by_name):
    """Sourced ages, with the unresolved TAGGED rather than silently drawn."""
    got, missing = {}, []
    for r in csv.DictReader(open(path, encoding='utf-8')):
        k = norm(r['name'])
        if r['birth_year']:
            got[k] = (CUR_SEASON - int(r['birth_year']), r['source'])
        else:
            missing.append(r['name'])
    return got, missing

def build_staff(verbose=False):
    bundle, front, mad, nfl = load_all()
    paths = [P(f) for f in STAFF_FILES]
    live, donors, pubrecs = fit_staff_profile(paths)
    ss_table, ss_bin = fit_startseason(paths)
    pool = json.load(open(P('wip', 'staff_name_pool.json')))
    real_names = {norm(n) for n in pool['real_coach_names']}
    prof = json.load(open(P('wip', 'staff_profile.json')))
    gate_vocab = collections.defaultdict(set)
    for f in ('PGMStaff_2021.json', 'PGMStaff_2017.json'):
        for r in json.load(open(P(f))):
            for k, v in r.items():
                if isinstance(v, str): gate_vocab[k].add(v)
    # The full 72-key schema, in the published order. A field a role does not
    # use is present at 0, NOT absent -- the validator reads every key on every
    # record, and this is the same class as the 2000 builder leaving ~30
    # specialty fields unset.
    template = json.load(open(P('PGMStaff_2021.json')))[0]
    SCHEMA = {k: (0 if isinstance(v, int) else ('' if isinstance(v, str) else []))
              for k, v in template.items()}
    gfit = json.load(open(P('wip', 'staff_guarantee_fit.json')))
    schemes = bundle['staff_schemes']

    # named staff from the bundle
    named = {}
    for t, v in bundle['hc_ratings'].items():   named[(t, 'Head Coach')] = v
    for v in bundle['coord_ratings'].values():
        named[(v['team'], 'Off Co-ord' if v['role'] == 'OC' else 'Def Co-ord')] = v
    for t, v in bundle['st_ratings']['ratings'].items(): named[(t, 'Special Teams')] = v

    ages, unresolved = load_staff_ages(P('sources', 'coach_birth_years_2026.csv'), None)
    # role medians for the unresolved, from the published files
    role_age = collections.defaultdict(list)
    for r in pubrecs: role_age[r['role']].append(r['age'])
    role_age = {k: int(statistics.median(v)) for k, v in role_age.items()}

    # published pools for the generated roles, stratified so the draws reach
    # the tails -- 32 random draws from 192 rarely hit the extremes, which
    # once left Def Scout topping out at 77 against a published 82-92.
    by_role_rating = collections.defaultdict(list)
    for r in pubrecs: by_role_rating[r['role']].append(r)

    staff, used_names, tags = [], set(), collections.Counter()
    promotions = []
    face_src = collections.Counter()
    reg_all = json.load(open(P('reference', 'PGM3_FACE_REGISTRY.json')))
    staff_faces = reg_all['staff_faces']
    verified_staff = set(reg_all['_verified_keys'].get('staff', []))
    for team in sorted(schemes):
        sc = schemes[team]
        for slot, role in enumerate(STAFF_ROLES):
            rng = random.Random(int(hashlib.sha256(f'{team}|{role}'.encode()).hexdigest()[:12], 16))
            rec = dict(SCHEMA)
            info = named.get((team, role))
            if info:
                nm = info['name']; rating = int(info['rating'])
                parts = nm.split(); fore, sur = parts[0], ' '.join(parts[1:]) or parts[0]
                k = norm(nm)
                if k in ages: age, tag = ages[k][0], 'sourced'
                else:         age, tag = role_age.get(role, 50), 'role-median'
                tags[tag] += 1
            else:
                # generated: scouts and physios, the one deliberate exception
                donor = rng.choice(by_role_rating[role])
                rating = donor['rating']
                for _ in range(200):
                    fore = rng.choice(pool['forenames']); sur = rng.choice(pool['surnames'])
                    k = norm(f'{fore} {sur}')
                    if k not in real_names and k not in used_names: break
                used_names.add(k)
                age, tag = donor['age'], 'generated'
                tags[tag] += 1
            # attributes: quantile position by rating within the role
            pool_r = sorted(x['rating'] for x in by_role_rating[role])
            q = percentile_of(pool_r, rating)
            for field, vals in live[role].items():
                rec[field] = int(round(_target_at(vals, q)))
            rec[PRIMARY_ATTR[role]] = rating
            gaps = [x['potential'] - x['rating'] for x in by_role_rating[role]]
            gap = sorted(gaps)[int(rng.random() * len(gaps))]
            rec.update({
                'rating': rating, 'potential': min(99, rating + gap),
                'age': age, 'role': role, 'teamID': team,
                'forename': fore, 'surname': sur, 'iden': _uuid(rng),
                'startSeason': max(1989, min(CUR_SEASON,
                                   draw_startseason(age, ss_table, ss_bin, rng))),
                'growthType': donor_growth(donors, role, gap, rng),
            })
            # contracts from the published role distribution
            sal = sorted(x['salary'] for x in by_role_rating[role])
            rec['salary'] = int(round(_target_at(sal, q)))
            grate, gratio = gfit.get(role, [0.5, 0.22])
            rec['guarantee'] = int(round(rec['salary'] * gratio)) if rng.random() < grate else 0
            ln = sorted(x['length'] for x in by_role_rating[role])
            rec['length'] = int(round(_target_at(ln, rng.random())))
            rec['eSalary'] = int(rec['salary'] * 1.15)
            rec['eGuarantee'] = 0        # ruled: ship staff eGuarantee at ZERO
            rec['eLength'] = min(4, max(0, rec['length'] - 1))
            # categorical fields
            for f, counts in prof[role]['str'].items():
                if f in ('role', 'teamID', 'forename', 'surname', 'iden', 'appearance'): continue
                pairs = [(x[0], x[1]) for x in counts
                         if not gate_vocab.get(f) or x[0] in gate_vocab[f]]
                if not pairs: continue
                rec[f] = rng.choices([x[0] for x in pairs], weights=[x[1] for x in pairs])[0]
            if role == 'Head Coach':
                rec['offStyle'] = sc['off']
                rec['defStyle'] = sc.get('cov_style', rec.get('defStyle'))
            if role == 'Off Co-ord':  rec['offStyle'] = sc['off']
            if role == 'Def Co-ord' and sc.get('dc_note'):
                promotions.append((team, role, f"{fore} {sur}",
                                   'PROMOTION, not a title he held. ' + sc['dc_note']))
            # THE REGISTRY'S staff_faces BLOCK, which this build was not using
            # at all -- 2,231 entries, covering 72 of the 128 real coaches, all
            # of whom were taking a donor face instead. Its keys are BARE NAMES,
            # not name|position, so no vocabulary translation applies.
            # The WHOLE ARRAY is written for staff, unlike players: coaches have
            # one look and no aging variant -- 244 staff appear in two or more
            # published files and not one byte of the appearance array differs.
            sk = norm(f'{fore} {sur}')
            if sk in staff_faces:
                rec['appearance'] = list(staff_faces[sk]); face_src['registry'] += 1
            else:
                rec['appearance'] = list(rng.choice(by_role_rating[role])['appearance'])
                face_src['donor'] += 1
            staff.append(rec)
    if verbose:
        vhit = sum(1 for s_ in staff
                   if norm(f"{s_['forename']} {s_['surname']}") in verified_staff)
        print(f'   staff faces: registry {face_src["registry"]}  donor {face_src["donor"]}'
              f'   ({vhit} of the 18 locked _verified_keys present)')
    return staff, tags, unresolved, real_names, promotions

# ================================================================== assembly
ALL_PUBLISHED = ['PGMRoster_1986.json', 'PGMRoster_2000.json', 'PGMRoster_2004.json', 'PGMRoster_2007.json', 'PGMRoster_2010.json', 'PGMRoster_2013.json', 'PGMRoster_2017.json', 'PGMRoster_2021.json']
ROSTER_KEYS = ['speed','vision','jumping','decisions','dPassAcc','ballStrip','burst',
 'rushBlock','releaseLine','discipline','intelligence','zoneCover','catching','throwOnRun',
 'mPassAcc','skillMove','blockShedding','sPassAcc','routeRun','tackle','ballSecurity',
 'passBlock','agility','injuryProne','power','trucking','elusiveness','stamina','manCover',
 'kickAccuracy','forename','surname','position','teamID','age','rating','potential',
 'growthType','appearance','salary','guarantee','length','eSalary','eGuarantee','eLength',
 'greed','loyalty','ambition','draftNum','draftSeason','teamNum','iden']
UNDRAFTED_FLOOR = 224

def fit_player_growth(paths):
    """Whole 31-element donor curves keyed on (cohort, potential - rating), so
    the 50x rule holds by construction. Every player must be able to DECLINE:
    2013 shipped with no negative entry for any of its 2,531 veterans and a
    52-year-old Tony Gonzalez was still rated 97 after twenty simulated
    seasons."""
    d = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            c = cohort_of(r)
            if len(r['growthType']) == 31:
                d[(c, r['potential'] - r['rating'])].append(r['growthType'])
    return d

def fit_potential_gap(paths):
    """(cohort, position) -> sorted published potential-minus-rating."""
    d = collections.defaultdict(list)
    for path in paths:
        for r in json.load(open(path)):
            d[(cohort_of(r), r['position'])].append(r['potential'] - r['rating'])
    return {k: sorted(v) for k, v in d.items()}

def _rescale_positives(curve, target):
    """Keep the donor's DECLINE, rescale its growth slots to the required sum.
    The 2000 build's fix for gaps with no exact donor. Every player must be
    able to decline: 2013 shipped with no negative entry for any of its 2,531
    veterans and a 52-year-old Tony Gonzalez was still rated 97 after twenty
    simulated seasons."""
    out = list(curve)
    idx = [i for i, v in enumerate(out) if v > 0]
    if target <= 0:
        for i in idx: out[i] = 0
        return out
    if not idx:                      # donor has no growth slots -- make one
        out[0] = target
        return out
    cur = sum(out[i] for i in idx)
    for i in idx: out[i] = int(out[i] * target / cur)
    drift = target - sum(out[i] for i in idx)
    out[idx[0]] += drift             # put the rounding remainder in one slot
    return out

def player_growth(pool, cohort, gap, rng):
    """Whole 31-element donor curve keyed on (cohort, potential - rating), so
    the 50x rule holds by construction where an exact donor exists. Where it
    does not, the nearest donor is taken and its positives rescaled."""
    target = gap * 50
    if pool.get((cohort, gap)):
        return list(rng.choice(pool[(cohort, gap)]))
    near = sorted((k for k in pool if k[0] == cohort and pool[k]),
                  key=lambda k: abs(k[1] - gap))
    if not near:
        near = sorted((k for k in pool if pool[k]), key=lambda k: abs(k[1] - gap))
    if not near:
        return [0] * 31
    return _rescale_positives(rng.choice(pool[near[0]]), target)

def assert_roster_record(r, seen_iden):
    if set(r) != set(ROSTER_KEYS):
        raise AssertionFailed(f'schema mismatch: extra {sorted(set(r)-set(ROSTER_KEYS))}, '
                              f'missing {sorted(set(ROSTER_KEYS)-set(r))}')
    if len(r['growthType']) != 31:
        raise AssertionFailed(f"growthType {len(r['growthType'])} elements, expected 31")
    pos = sum(x for x in r['growthType'] if x > 0)
    if pos != (r['potential'] - r['rating']) * 50:
        raise AssertionFailed(f"50x rule: {pos} != {(r['potential']-r['rating'])*50} "
                              f"for {r['forename']} {r['surname']}")
    if r['iden'] in seen_iden:
        raise AssertionFailed(f"duplicate iden {r['iden']}")
    seen_iden.add(r['iden'])
    c = cohort_of(r)
    hi = 256 if c == 'Rookie' else UNDRAFTED_FLOOR
    if r['draftNum'] < 1 or r['draftNum'] > hi:
        raise AssertionFailed(f"draftNum {r['draftNum']} outside 1-{hi} for cohort {c}")
    if c == 'FA' and (r['salary'] or r['length'] or r['teamNum']):
        raise AssertionFailed(f"free agent {r['surname']} must have salary/length/teamNum 0")
    if c == 'T' and r['length'] < 1:
        raise AssertionFailed(f"rostered {r['surname']} has length {r['length']}")
    if c == 'Rookie' and (r['eSalary'] or r['eLength']):
        raise AssertionFailed(f"prospect {r['surname']} must have eSalary/eLength 0")
    return True

def _prospect_face(pr, pos, rng, lib, prior, vocab, archive, med_wt):
    """Prospects get a real generated face, not a placeholder. They are draft
    boards, so the archive rarely covers them and the band comes from the
    position prior -- a flat league-wide fill is wrong in both directions at
    once, since 52.9% of kickers sit in the lightest family against 1.5% of
    cornerbacks. Age 22 and the position's median weight drive the variant."""
    key = f"{norm(pr['name'])}|{pos}"
    band = archive_band(key, archive)
    if band is None:
        band = _draw(rng, prior[pos]) if prior.get(pos) else 'dark'
    app = build_appearance(rng, pos, band, 22, med_wt.get(pos), lib)
    assert_appearance_valid(app, vocab)
    return app

def stage_build(verbose=True):
    """Assemble PGMRoster_2026.json. The face registry is applied LAST, over
    the top, and nothing after it -- family digit only for players, because the
    variant letter is a function of age and weight IN THAT SEASON."""
    bundle, front, mad, nfl = load_all()
    refs   = [P(f) for f in MODERN_REFS]
    rows, built, _, weights, tier_of, filled, coh = stage_attributes(verbose=False)
    bounds = fit_attr_bounds(refs)
    _, ratpool = fit_percentile_fill(refs)
    build_derived(rows, built, weights, fit_derived_pools(refs), ratpool)
    calibrate_positions(rows, built, weights, bounds)
    for n, m, pos in rows:
        a = built.get(id(n))
        if not a or 'OverallRating' not in m: continue
        built[id(n)], _ = refit_player(a, pos, float(m['OverallRating']), weights, bounds)
    assert_conditional_after_refit(rows, {id(n): built[id(n)] for n, _, _ in rows if id(n) in built})

    pre = (rows, built, None, weights, tier_of, filled, coh)
    plist, salary, guarantee, prov_of, lengths, team_of, _ = stage_contracts(
        verbose=False, precomputed=pre)
    faces, _, _, _ = stage_appearances(verbose=False, precomputed=rows)
    face_of = {id(n): app for n, pos, band, app in faces}
    # ASSERT THE LOOKUP LANDS. A miss here does not error -- it silently
    # substitutes a placeholder, which is exactly how five distinct faces
    # reached 2,635 records. Assert on the match RATE, never the output count.
    hit = sum(1 for n, m, pos in rows if id(n) in face_of)
    if hit < 0.99 * len(rows):
        raise AssertionFailed(f'appearance lookup covered {hit}/{len(rows)} rows '
                              f'({100*hit/len(rows):.1f}%) — identity mismatch, '
                              f'records would silently take a placeholder face')

    gpool = fit_player_growth(refs); gapref = fit_potential_gap(refs)
    face_lib = fit_appearance_library([P(f) for f in MODERN_REFS])
    face_prior = band_prior([P(f) for f in MODERN_REFS])
    face_vocab = published_vocabulary([P(f) for f in MODERN_REFS])
    arc_players = json.load(open(P('reference','PGM3_PLAYER_ARCHIVE.json')))['players']
    med_wt = collections.defaultdict(list)
    for n_, m_, p_ in rows:
        w_ = None
        try: w_ = float(m_['Weight'])
        except (KeyError, ValueError, TypeError): w_ = _weight(n_)
        if w_: med_wt[p_].append(w_)
    med_wt = {k: statistics.median(v) for k, v in med_wt.items()}
    pools, rp = fit_percentile_fill(refs)      # hoisted: these load six files
    dpools    = fit_derived_pools(refs)        # each, and the loop runs 321x
    rt_curve, gp_curve = fit_prospect_curve(refs)
    reg = json.load(open(P('reference', 'PGM3_FACE_REGISTRY.json')))
    fk = reg['faces']; verified = set(reg['_verified_keys'].get('players', []))

    out, seen = [], set()
    for n, m, pos in rows:
        a = built.get(id(n))
        if not a: continue
        k = id(n)
        is_fa = k in coh
        rng = random.Random(name_seed(n, pos))
        # `iden` needs its own stream: name+position collides across cohorts
        # (a prospect and a rostered player, or two real namesakes), and the
        # uniqueness assertion caught exactly that.
        irng = random.Random(name_seed(n, pos) ^ (0xFA if is_fa else 0x7) ^ (len(out) << 8))
        rating = int(round(float(m['OverallRating'])))
        gaps = gapref.get(('T', pos)) or [0]
        gap  = gaps[min(len(gaps) - 1, int(rng.random() * len(gaps)))]
        potential = min(99, rating + gap)
        exp = n['_exp']
        rec = {kk: 0 for kk in ROSTER_KEYS}
        for attr, v in a.items():
            if attr in rec: rec[attr] = int(v)
        parts = n['full_name'].split()
        rec.update({
            'forename': parts[0], 'surname': ' '.join(parts[1:]) or parts[0],
            'position': pos, 'teamID': 'Free Agent' if is_fa else n['_team'],
            'age': int(m['Age']) if 'Age' in m else max(21, CUR_SEASON - int((n.get('birth_date') or '2000')[:4])),
            'rating': rating, 'potential': potential,
            'growthType': player_growth(gpool, 'FA' if is_fa else 'T', potential - rating, rng),
            'appearance': face_of.get(k) or ['Head5a','Eyes1a','Hair1d','Beard1b',
                                             'Eyebrows1a','Nose5d','Mouth5a','Glasses1e','Clothes1'],
            # 224 is both the undrafted floor AND the ceiling: no published
            # file uses a value above it, though modern drafts run to ~257
            # picks. Real picks past 224 clamp onto it.
            'draftNum': min(UNDRAFTED_FLOOR, int(n['draft_number']))
                        if n['draft_number'] not in ('', 'NA') else UNDRAFTED_FLOOR,
            'draftSeason': max(1989, CUR_SEASON - exp),
            'iden': _uuid(irng),
        })
        if is_fa:
            rec.update({'salary': 0, 'guarantee': 0, 'length': 0, 'teamNum': 0,
                        'eSalary': 0, 'eGuarantee': 0, 'eLength': 0})
        else:
            rec.update({'salary': salary.get(k, 0), 'guarantee': guarantee.get(k, 0),
                        'length': max(1, lengths.get(k, 1)),
                        'teamNum': int(n['jersey_number']) if str(n.get('jersey_number','')).isdigit() else 0,
                        'eSalary': int(salary.get(k, 0) * 1.2), 'eGuarantee': 0,
                        'eLength': min(4, max(0, lengths.get(k, 1) - 1))})
        out.append(rec)

    # a player can appear ACT on one team and CUT on another; the rostered
    # record wins and the free-agent copy is dropped.
    rostered_keys = {(norm(r['forename'] + ' ' + r['surname']), r['position'])
                     for r in out if cohort_of(r) == 'T'}
    before = len(out)
    out = [r for r in out if not (cohort_of(r) == 'FA' and
           (norm(r['forename'] + ' ' + r['surname']), r['position']) in rostered_keys)]
    dropped_dupe_fa = before - len(out)

    # jersey numbers unique within a team: reserve/IR players share numbers
    # with the active man who inherited them.
    taken = collections.defaultdict(set)
    for r in out:
        if cohort_of(r) != 'T': continue
        t = r['teamID']; j = r['teamNum']
        if j and j not in taken[t]: taken[t].add(j); continue
        for cand in list(range(1, 100)):
            if cand not in taken[t]: r['teamNum'] = cand; taken[t].add(cand); break

    # --- prospects -------------------------------------------------------
    # A draft class is capped at 256, the published convention (2013 ships
    # 256/256/253/253) and roughly a real 257-pick draft. The 2027 board runs
    # to 289, so ranks 257-289 are dropped -- the bottom of the Drafttek
    # 101-450 tail, the least confident part of the board.
    MAX_CLASS = 256
    allrec, seasons = [], []
    for season, key in ((2027, 'draft2027'), (2028, 'draft2028')):
        for pr in bundle[key]:
            if pr['rank'] > MAX_CLASS: continue
            allrec.append(pr); seasons.append(season)
    for pr, season, pos in zip(allrec, seasons, prospect_positions(allrec)):
        rng = random.Random(name_seed({'_norm': norm(pr['name'])}, pos) + season)
        rating, potential = build_prospect(pr['rank'], pos, season, rt_curve, gp_curve, rng)
        parts = pr['name'].split()
        rec = {kk: 0 for kk in ROSTER_KEYS}
        q = percentile_of(rp[pos], rating) if rp.get(pos) else 0.5
        for attr in ATTR_MAP:
            if attr not in set(weights[pos][0]) or (pos, attr) in GATE_OFF: continue
            pl = pools.get((pos, attr))
            if pl: rec[attr] = int(round(_target_at(pl, q)))
        for attr in DERIVED_ATTRS:
            # greed, loyalty and ambition are not in weights.json but every
            # published prospect carries them -- gating on the weights list
            # left the whole Rookie cohort at zero.
            if attr not in set(weights[pos][0]) and attr not in DERIVED_INDEPENDENT:
                continue
            pl = pools.get((pos, attr)) or dpools.get((pos, attr))
            if not pl: continue
            if attr in DERIVED_BY_RATING:
                rec[attr] = max(0, min(99, int(round(_target_at(sorted(pl), q)))))
            else:
                pl = sorted(pl)
                rec[attr] = pl[min(len(pl) - 1, int(rng.random() * len(pl)))]
        rec.update({
            'forename': parts[0], 'surname': ' '.join(parts[1:]) or parts[0],
            'position': pos, 'teamID': 'Rookie', 'age': 22,
            'rating': rating, 'potential': potential,
            'growthType': player_growth(gpool, 'Rookie', potential - rating, rng),
            'appearance': _prospect_face(pr, pos, rng, face_lib, face_prior,
                                         face_vocab, arc_players, med_wt),
            'salary': 0, 'guarantee': 0, 'length': 0, 'teamNum': 0,
            'eSalary': 0, 'eGuarantee': 0, 'eLength': 0,
            'draftNum': pr['rank'], 'draftSeason': season,
            'iden': _uuid(random.Random(name_seed({'_norm': norm(pr['name'])}, pos)
                                        ^ 0xB0 ^ (len(out) << 8))),
        })
        out.append(rec)

    # --- FACE REGISTRY LAST, family digit only for players ---------------
    # A person gets ONE face across every season. The registry supplies it:
    # slots 0/5/6 take its FAMILY DIGIT while keeping this season's variant
    # letter -- that letter is a function of age and weight IN THIS SEASON, so
    # writing the array wholesale flattens the aging. Everything else --
    # eyes, hair, beard, eyebrows, glasses, clothes -- is copied EXACTLY,
    # because hair is a fact about the man and must not drift between files.
    # That is the rule the standing check enforces: family constant, hair
    # constant, variant free to vary.
    fk_by = index_by_name(fk)
    seen_pub = fit_published_appearances([P(f) for f in ALL_PUBLISHED])
    applied = 0; write_how = collections.Counter()
    for rec in out:
        nm = norm(rec['forename'] + ' ' + rec['surname'])
        exp = CUR_SEASON - rec['draftSeason'] if rec['draftSeason'] else 0
        want, hw = lookup_by_position(fk, fk_by, nm, rec['position'], exp, seen_pub)
        write_how[hw] += 1
        if not want: continue
        fam = tok_family(want[0])
        app = list(rec['appearance'])
        for i, tag in ((0, 'Head'), (5, 'Nose'), (6, 'Mouth')):
            app[i] = f'{tag}{fam}{tok_variant(app[i])}'
        for i in (1, 2, 3, 4, 7, 8):
            app[i] = want[i]
        rec['appearance'] = app; applied += 1

    for rec in out: assert_roster_record(rec, seen)
    if verbose:
        c = collections.Counter(cohort_of(r) for r in out)
        print(f'ROSTER assembled: {len(out)} records')
        print(f'   rostered {c["T"]}   free agents {c["FA"]}   prospects {c["Rookie"]}')
        print(f'   face registry applied: {applied}  ' +
              '  '.join(f'{k} {v}' for k, v in write_how.most_common()))
        tm = collections.Counter(r['teamID'] for r in out if cohort_of(r) == 'T')
        print(f'   teams {len(tm)}  sizes {min(tm.values())}-{max(tm.values())}')
        print(f'   all {len(out)} records pass the schema and 50x assertions')
    return out

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
        rows, built, _, weights, tier_of, _fk, _co = stage_attributes()
        assert_no_gated_values(built, rows)
        nlive = assert_attribute_coverage(built, rows, weights)
        print(f'   coverage assertion: every live cell populated for every'
              f' player ({nlive} live slots)')
        rep = seam_report()
        print(f'   tier-seam assertion: JINX->M27 conversion validated on players'
              f' who have both ({len(rep)} columns)')
        worst = sorted(rep, key=lambda r: -abs(r[2]))[:3]
        for mc, n_, med, mad in worst:
            print(f'      {mc:26s} n={n_:5d}  median shift {med:+5.1f}  MAD {mad:.1f}')
        conditional_pass(rows, built)
    elif cmd == 'refit': stage_refit()
    elif cmd == 'contracts': stage_contracts()
    elif cmd == 'assemble': stage_build()
    else: print(__doc__); sys.exit(2)
