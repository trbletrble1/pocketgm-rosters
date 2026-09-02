#!/usr/bin/env python3
"""
PGM3 roster/staff validation suite.

Usage:
    python3 pgm3_validate.py roster NEW.json REF1.json [REF2.json ...]
    python3 pgm3_validate.py staff  NEW.json REF1.json [REF2.json ...]
    python3 pgm3_validate.py faces  FILE.json [FILE.json ...]        # cross-season face checks
    python3 pgm3_validate.py faces --staff FILE.json [FILE.json ...]
    python3 pgm3_validate.py conditional NEW.json SRC.csv OUT_FIELD SRC_FIELD

The `conditional` pass is the one that catches a field derived from nothing —
split the output by the source value and confirm the groups differ. It is
mandatory before a file is called finished; see the handoff. It was implemented
but missing from this usage text, which is how you end up with a documented
mandatory check that nobody can find.

Contract ceilings and the team cap are parameters, not laws — see LIMITS.
Override per build:

    python3 pgm3_validate.py roster NEW.json REF1.json --team_cap=301.2M
    python3 pgm3_validate.py roster NEW.json REF1.json --salary=60M

REF files are known-good published files. Ranges and zero-patterns are
measured against the UNION of them, never a single one — a value that is
legitimate in 2010 will look out of range against 2017 alone.

Every check here exists because it caught a real bug. See the handoff.
"""
import sys, json, re, collections, statistics

# ------------------------------------------------------------------ limits
# Sanity guards, NOT limits the game enforces.
#
# TESTED 2026-08-28: a league imported with salaries of $45M, $60M and $75M
# accepted all three, displayed them correctly, and used them in its own
# arithmetic ($45M salary -> $50.7M cap hit, $31.3M dead cap). Nothing was
# clamped or rejected. The old "hard caps" of 27.6/34.1/40.9M were the donor
# file's highest-paid player at each field — one record each, inherited
# through five builds. There is no ceiling.
#
# These defaults are therefore set well above anything real, so a genuinely
# absurd value still trips a check while real modern contracts pass freely.
# Override per build with --salary=, --eSalary=, --eGuarantee=, --team_cap=.
#
# team_cap is the real NFL cap for the season being built and moves every
# year — 2026 is $301.2M. Always pass it explicitly for a historical build.
LIMITS = {
    'salary':    150_000_000,   # sanity guard; $75M verified accepted in play
    'eSalary':   150_000_000,   # sanity guard
    'eGuarantee':200_000_000,   # sanity guard
    'team_cap':  301_200_000,   # 2026 NFL cap
}

def load(p):
    with open(p) as f: return json.load(f)

def cohort(p):
    t = p.get('teamID')
    return 'Rookie' if t == 'Rookie' else ('FA' if t == 'Free Agent' else 'T')

def split_tok(t):
    m = re.match(r'([A-Za-z]+)(\d+)(.*)$', str(t))
    return (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)

def med(v):
    v = sorted(v); return v[len(v)//2] if v else None

# ---------------------------------------------------------------- roster


def _extra_vocab():
    """The full appearance vocabulary, independent of which reference files
    were passed.

    This must NOT depend on the references. Running with three references
    instead of four once produced 229 phantom failures, because the missing
    file was the only one using certain tokens. Union everything available:
    the donor files if present, AND the schema reference, which carries the
    complete vocabulary and lives in project context."""
    import os
    out = set()
    for cand in ('PGMRoster2025-06-12_3.json','/mnt/user-data/uploads/PGMRoster2025-06-12_3.json',
                 'PGMStaff2025-06-12.json','/mnt/user-data/uploads/PGMStaff2025-06-12.json'):
        try:
            if os.path.exists(cand):
                out |= set(v for p in load(cand) for v in p['appearance'] if v != '#N/A')
        except Exception:
            pass
    for cand in ('reference/PGM3_SCHEMA_REFERENCE.json','../reference/PGM3_SCHEMA_REFERENCE.json',
                 'PGM3_SCHEMA_REFERENCE.json','/mnt/user-data/uploads/PGM3_SCHEMA_REFERENCE.json',
                 '/mnt/project/PGM3_SCHEMA_REFERENCE.json'):
        try:
            if os.path.exists(cand):
                ref = load(cand)
                for slot, toks in ref.get('appearance_vocab_by_slot', {}).items():
                    out |= {t for t in toks if t != '#N/A'}
                break
        except Exception:
            pass
    return out

def check_roster(new, refs):
    out = []
    pool = [p for r in refs for p in r]
    keys = set(pool[0].keys())
    types = {k: type(pool[0][k]) for k in keys}
    NUM = [k for k, v in pool[0].items() if isinstance(v, int)]
    LO = {k: min(p[k] for p in pool) for k in NUM}
    HI = {k: max(p[k] for p in pool) for k in NUM}
    MONEY = {'salary','guarantee','eSalary','eGuarantee','length','eLength',
             'draftSeason','draftNum','age','teamNum','rating','potential'}
    VOCAB = set(v for p in pool for v in p['appearance'] if v != '#N/A')
    VOCAB |= _extra_vocab()
    TEAMS = {'ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU',
             'IND','JAX','KC','LAC','LAR','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI',
             'PIT','SEA','SF','TB','TEN','WAS'}
    on = [p for p in new if cohort(p) == 'T']
    tcount = collections.Counter(p['teamID'] for p in on)

    # --- structure
    out.append(('schema keys', sum(1 for p in new if set(p.keys()) != keys)))
    out.append(('field types', sum(1 for p in new for k in keys if not isinstance(p[k], types[k]))))
    out.append(('duplicate iden', len(new) - len({p['iden'] for p in new})))
    out.append(('empty names', sum(1 for p in new if not str(p['forename']).strip() or not str(p['surname']).strip())))

    # --- team ids: MODERN for every season (2004 SD is LAC, etc)
    out.append(('non-modern teamID', len({p['teamID'] for p in on} - TEAMS)))

    # --- ranges, measured against the union of refs
    oor = sum(1 for p in new for k in NUM if not LO[k] <= p[k] <= HI[k])
    if oor: print(f'  WARN  {oor} values outside the reference range '
                  f'(observed range != accepted range — check they are real, do not auto-clamp)')
    out.append(('attribute outside 0-99',
                sum(1 for p in new for k in NUM if k not in MONEY and not 0 <= p[k] <= 99)))

    # --- growth
    out.append(('growthType length != 31', sum(1 for p in new if len(p['growthType']) != 31)))
    # 50x applies in EVERY cohort. A fresh game export shows veterans obeying
    # it 0% of the time — their curve is a career arc whose positive portion
    # is partly spent, summing around 400. That mechanic is not understood
    # well enough to reproduce per player, so all five published files enforce
    # 50x on everyone and new builds match them. Ruled: five consistent files
    # beat a game behaviour nobody has worked out. Hard fail in both cohorts.
    out.append(('growthType 50x rule (all cohorts)',
                sum(1 for p in new
                    if sum(x for x in p['growthType'] if x > 0) != (p['potential']-p['rating'])*50)))
    out.append(('potential < rating', sum(1 for p in new if p['potential'] < p['rating'])))

    # --- appearance
    out.append(('appearance length != 9', sum(1 for p in new if len(p['appearance']) != 9)))
    out.append(('appearance token not in vocab',
                sum(1 for p in new for v in p['appearance'] if v not in VOCAB)))
    out.append(('skin family mismatch (slots 0/5/6)',
                sum(1 for p in new if len({split_tok(p['appearance'][j])[1] for j in (0,5,6)}) > 1)))
    out.append(('hair family mismatch (slots 2/3/4)',
                sum(1 for p in new if len({split_tok(p['appearance'][j])[1] for j in (2,3,4)}) > 1)))
    out.append(('player wearing glasses',
                sum(1 for p in new if p['appearance'][7] != 'Glasses1e')))
    # NOTE: duplicate appearances are FINE. Do not check for them.

    # --- roster shape
    out.append(('team count != 32', abs(len(tcount) - 32)))
    out.append(('roster over 69', sum(1 for v in tcount.values() if v > 69)))
    out.append(('roster under 45', sum(1 for v in tcount.values() if v < 45)))
    out.append(('duplicate jersey within team',
                sum(1 for t in tcount
                    for k, n in collections.Counter(x['teamNum'] for x in on if x['teamID']==t).items()
                    if n > 1)))
    out.append(('same person twice on rosters',
                sum(1 for k, v in collections.Counter(
                    (p['forename'], p['surname'], p['position'], p['teamID']) for p in on).items() if v > 1)))
    # a man cannot be rostered and a free agent at the same time. suffixes are
    # stripped because the two sources often disagree ("Marion Barber" on one,
    # "Marion Barber Jr." on the other) — that asymmetry is how a duplicate
    # survives an exact-name exclusion.
    def _sfx(n):
        return re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '',
                      n.lower().replace('.', '')).strip()
    _ros = {(_sfx(p['forename']), _sfx(p['surname']), p['position']) for p in on}
    _fa  = {(_sfx(p['forename']), _sfx(p['surname']), p['position'])
            for p in new if p.get('teamID') == 'Free Agent'}
    out.append(('same person rostered and free agent', len(_ros & _fa)))

    # --- position minimums per team
    # derive minimums from what the reference files actually ship, not an
    # ideal — 2010 and 2017 both carry a team with only 1 DE and play fine
    MIN = {}
    for r in refs:
        ro = [p for p in r if cohort(p) == 'T']
        for t in {p['teamID'] for p in ro}:
            cc = collections.Counter(p['position'] for p in ro if p['teamID'] == t)
            for pos in set(list(cc)+list(MIN)):
                MIN[pos] = min(MIN.get(pos, 99), cc[pos])
    short = 0
    for t in tcount:
        c = collections.Counter(p['position'] for p in on if p['teamID'] == t)
        short += sum(1 for pos, mn in MIN.items() if c[pos] < mn)
    if short: print(f'  WARN  {short} team/position shortfalls '
                    f'(published files ship with these too — check they are plausible)')

    # --- CB/S ratio catches the generic-DB-label bug
    c = collections.Counter(p['position'] for p in on)
    ratio = c['CB']/max(1, c['S'])
    refr = [collections.Counter(p['position'] for p in r if cohort(p)=='T') for r in refs]
    lo = min(x['CB']/max(1,x['S']) for x in refr); hi = max(x['CB']/max(1,x['S']) for x in refr)
    out.append((f'CB/S ratio {ratio:.2f} outside ref {lo:.2f}-{hi:.2f}',
                0 if lo-0.15 <= ratio <= hi+0.15 else 1))

    # --- contracts
    out.append(('rostered length < 1', sum(1 for p in on if p['length'] < 1)))
    out.append(('free agent length != 0',
                sum(1 for p in new if cohort(p)=='FA' and p['length'] != 0)))
    pay = collections.Counter()
    for p in on: pay[p['teamID']] += p['salary'] + p['guarantee']
    cap = LIMITS['team_cap']
    out.append((f'team over {cap/1e6:.1f}M cap', sum(1 for v in pay.values() if v > cap)))
    CEIL = {k: LIMITS[k] for k in ('salary','eSalary','eGuarantee')}
    for k, v in CEIL.items():
        out.append((f'{k} over ceiling {v:,}', sum(1 for p in new if p[k] > v)))

    # --- contract ladder AND overall shape (both required)
    CUR = 2026
    lad = []
    for yp in range(0, 4):
        g = [p['length'] for p in on if CUR - p['draftSeason'] == yp]
        if g: lad.append(med(g))
    out.append((f'rookie contract ladder {lad} not descending',
                0 if lad == sorted(lad, reverse=True) else 1))
    one = sum(1 for p in on if p['length'] == 1) / max(1, len(on))
    out.append((f'1-year deals {100*one:.0f}% outside 25-45%',
                0 if 0.25 <= one <= 0.45 else 1))

    # --- paired check: guarantee tracks REMAINING length, not signing bonus
    def gratio(pool_):
        o = [p for p in pool_ if cohort(p)=='T' and p['salary'] > 0]
        r1 = [p['guarantee']/p['salary'] for p in o if p['length']==1]
        r5 = [p['guarantee']/p['salary'] for p in o if p['length']>=5]
        return (med(r1) or 0), (med(r5) or 0)
    n1, n5 = gratio(new)
    out.append((f'guarantee/salary 1yr={n1:.2f} 5yr={n5:.2f} — should rise with length',
                0 if n5 > n1 else 1))

    # --- draft pool
    rk = [p for p in new if cohort(p)=='Rookie']
    if rk:
        byS = collections.defaultdict(list)
        for p in rk: byS[p['draftSeason']].append(p['draftNum'])
        out.append(('duplicate pick within a class',
                    sum(1 for s, v in byS.items() if len(set(v)) != len(v))))
        out.append(('prospect eSalary/eLength != 0',
                    sum(1 for p in rk if p['eSalary'] != 0 or p['eLength'] != 0)))
        rc = collections.Counter(p['position'] for p in rk)
        out.append(('draft pool has no safeties', 1 if rc['S'] == 0 else 0))
        out.append(('draft pool missing a LB type',
                    1 if (rc['MLB'] == 0 or rc['OLB'] == 0) else 0))

    # ---- ROSTER COMPOSITION: no team empty at a position the references
    # always fill. `zero_pattern` is about attribute VALUES, not roster
    # composition, so nothing in this suite looked at depth charts. 2026
    # shipped with 16 of 32 teams carrying no defensive end at all, every
    # other check green, and it was found by a person opening a depth chart.
    ref_never_empty = None
    for r in refs:
        bt = collections.defaultdict(collections.Counter)
        for q in r:
            if cohort(q) == 'T': bt[q['teamID']][q['position']] += 1
        filled = {p for p in {x['position'] for x in r if cohort(x) == 'T'}
                  if all(c[p] for c in bt.values())}
        ref_never_empty = filled if ref_never_empty is None else (ref_never_empty & filled)
    if ref_never_empty:
        bt = collections.defaultdict(collections.Counter)
        for q in on: bt[q['teamID']][q['position']] += 1
        gaps = [f'{t} has no {p}' for t in sorted(bt) for p in sorted(ref_never_empty)
                if bt[t][p] == 0]
        out.append((f'team empty at a position every reference fills '
                    f'({len(ref_never_empty)} positions checked)'
                    + (': ' + '; '.join(gaps[:5]) if gaps else ''), len(gaps)))
        # Per-team position RATE, on a TOP-53 slice, against the range every
        # reference spans. Two calibration points, both learned the hard way:
        #
        # 1. UNANIMITY, not a percentage band. The published files disagree
        #    with each other by 26-77% on these rates, so a +/-15% rule fails
        #    most of them against one another. The range they SPAN passes every
        #    published file by construction and still catches a real defect --
        #    DE at 3.1/team against a spanned 3.8-5.0 fires immediately.
        #
        # 2. TOP-53, because the references are not 53-man rosters. They carry
        #    53-67 per team, built from everyone who played that season, and on
        #    an all-rostered basis RB reads 5.2-6.5 against a modern roster's
        #    4. On a top-53 slice the same files read 4.2-5.4 and the apparent
        #    1.5/team shortfall is 0.3. Comparing a point-in-time roster to a
        #    season-long cohort manufactures a defect that is not there.
        def _rate53(recs):
            by = collections.defaultdict(list)
            for q in recs:
                if cohort(q) == 'T': by[q['teamID']].append(q)
            n = len(by) or 1
            c = collections.Counter()
            for t, ps in by.items():
                for q in sorted(ps, key=lambda x: -x['rating'])[:53]: c[q['position']] += 1
            return {p: c[p] / n for p in set(c) | set(ref_never_empty)}
        mine = _rate53(new)
        refr = [_rate53(r) for r in refs]
        odd = []
        for p in sorted(ref_never_empty):
            vals = [r.get(p, 0) for r in refr]
            lo, hi = min(vals), max(vals)
            if not (lo <= mine.get(p, 0) <= hi):
                odd.append(f'{p} {mine.get(p,0):.1f}/team vs the range every reference spans, {lo:.1f}-{hi:.1f}')
        # WARNING, not a gate, and the reason is measured rather than assumed.
        # Leave-one-out, EVERY published file falls outside the span of the
        # other seven -- 1986 on 5 positions, 2000 on 4, 2010 on 5, 2013 on 5,
        # 2021 on 5, and 2004/2007/2017 on 1 each. So "the span of every
        # reference" cannot pass the references by construction; the archive is
        # too heterogeneous with itself. A gate calibrated to it would fail the
        # files it is calibrated on.
        # The TEAM-EMPTY check above IS a gate: 0 of 256 published team-seasons
        # leave a position empty, which is unanimous, and it catches the real
        # defect (16 teams with no DE) on its own.
        if odd:
            print(f'  WARN  {len(odd)} position rates outside the span of every '
                  f'reference, top-53 basis (the references do not span each '
                  f'other either — leave-one-out, all 8 fail 1-5 positions)')
            for o in odd[:6]: print(f'          {o}')

    # ---- team payroll must sit on the published convention --------------
    # PGM3's cap is a fixed engine constant of ~$280M with no field in the
    # schema, so era-accurate dollars are NOT playable: a 2000-dollar file
    # leaves ~$225M of room on every team and the financial layer goes inert.
    # On a TOP-53 basis all seven published files read $197.4M with a spread
    # of $29k -- 0.015%, 1986 landing on the round number to the dollar. Top-51
    # scatters by $1M, so top-53 is the real basis and top-51 the derived view. cross_year deliberately skips money fields ("they differ by era"),
    # which is exactly the assumption that hides this, so it is checked here.
    # Found by in-game test only, after a build shipped at $54.6M.
    def _top53(recs):
        by = collections.defaultdict(list)
        for q in recs:
            if cohort(q) == 'T':
                by[q['teamID']].append(q['salary'] + q['guarantee'])
        return [sum(sorted(v, reverse=True)[:53]) for v in by.values()]
    # NB true median, not med(): med() returns the upper-middle element, which
    # on 32 teams reads ~$1.2M high and would compare two different conventions.
    ref_meds = [statistics.median(_top53(r)) for r in refs if _top53(r)]
    mine = _top53(on)
    if ref_meds and mine:
        lo, hi = min(ref_meds) - 1e6, max(ref_meds) + 1e6
        m = statistics.median(mine)
        out.append((f'median team payroll ${m/1e6:.1f}M vs published '
                    f'${lo/1e6:.1f}-{hi/1e6:.1f}M',
                    0 if lo <= m <= hi else 1))
        out.append(('teams over the ~$280M engine cap',
                    sum(1 for x in mine if x > 280_000_000)))
    return out

# ----------------------------------------------------------------- staff

def check_staff(new, refs):
    out = []
    pool = [p for r in refs for p in r]
    keys = set(pool[0].keys())
    types = {k: type(pool[0][k]) for k in keys}
    NUM = [k for k, v in pool[0].items() if isinstance(v, int)]
    LO = {k: min(p[k] for p in pool) for k in NUM}
    HI = {k: max(p[k] for p in pool) for k in NUM}
    STR = [k for k, v in pool[0].items() if isinstance(v, str) and k not in ('forename','surname','iden')]
    SVOC = {k: set(p[k] for p in pool) for k in STR}
    VOCAB = set(v for p in pool for v in p['appearance'] if v != '#N/A')
    VOCAB |= _extra_vocab()
    PRIM = {'Head Coach':'HCcoach','Off Co-ord':'OCcoach','Def Co-ord':'DCcoach',
            'Special Teams':'STcoach','Head Scout':'Hscout','Off Scout':'Oscout',
            'Def Scout':'Dscout','Head Physio':'Hphysio','Assistant Physio':'Aphysio'}
    OFFPOS = {'QB','RB','WR','TE','OT','OG','C'}
    emp = [p for p in new if p['teamID'] != 'Free Agent']
    tcount = collections.Counter(p['teamID'] for p in emp)

    out.append(('schema keys', sum(1 for p in new if set(p.keys()) != keys)))
    out.append(('field types', sum(1 for p in new for k in keys if not isinstance(p[k], types[k]))))
    out.append(('duplicate iden', len(new) - len({p['iden'] for p in new})))
    out.append(('duplicate names',
                sum(1 for k, v in collections.Counter(
                    (p['forename'], p['surname']) for p in new).items() if v > 1)))
    oor = sum(1 for p in new for k in NUM if not LO[k] <= p[k] <= HI[k])
    if oor: print(f'  WARN  {oor} values outside the reference range '
                  f'(observed range != accepted range — check they are real, do not auto-clamp)')
    out.append(('string not in vocab',
                sum(1 for p in new for k in STR if p[k] not in SVOC[k])))
    out.append(('primary attribute != rating',
                sum(1 for p in new if p[PRIM[p['role']]] != p['rating'])))
    out.append(('potential < rating', sum(1 for p in new if p['potential'] < p['rating'])))

    # every specialty field must be populated — this crashed the game once.
    # management/motivation apply to everyone; playcalling only to coaches.
    COACH_ROLES = {'Head Coach','Off Co-ord','Def Co-ord','Special Teams'}
    for f in ('management','motivation','discipline'):
        if f in keys:
            out.append((f'{f} == 0', sum(1 for p in new if p[f] == 0)))
    if 'playcalling' in keys:
        out.append(('playcalling == 0 (coaches only)',
                    sum(1 for p in new if p['role'] in COACH_ROLES and p['playcalling'] == 0)))
    # every coach carries all four coaching attrs, not just his own
    COACH = {'Head Coach','Off Co-ord','Def Co-ord','Special Teams'}
    out.append(('coach missing a coaching attribute',
                sum(1 for p in new if p['role'] in COACH
                    for f in ('HCcoach','OCcoach','DCcoach','STcoach') if p[f] == 0)))
    out.append(('scout missing a scout attribute',
                sum(1 for p in new if 'Scout' in p['role']
                    for f in ('Hscout','Oscout','Dscout') if p[f] == 0)))

    out.append(('growthType length != 51', sum(1 for p in new if len(p['growthType']) != 51)))
    out.append(('growthType 50x rule (DOES apply to staff)',
                sum(1 for p in new
                    if sum(x for x in p['growthType'] if x > 0) != (p['potential']-p['rating'])*50)))

    out.append(('scout wrong-side specialty',
                sum(1 for p in new
                    if (p['role']=='Off Scout' and p['scoutBoost'] not in OFFPOS)
                    or (p['role']=='Def Scout' and p['scoutBoost'] in OFFPOS))))

    out.append(('appearance length != 9', sum(1 for p in new if len(p['appearance']) != 9)))
    out.append(('appearance token not in vocab',
                sum(1 for p in new for v in p['appearance'] if v not in VOCAB)))
    out.append(('skin family mismatch',
                sum(1 for p in new if len({split_tok(p['appearance'][j])[1] for j in (0,5,6)}) > 1)))
    out.append(('hair family mismatch',
                sum(1 for p in new if len({split_tok(p['appearance'][j])[1] for j in (2,3,4)}) > 1)))

    out.append(('team count != 32', abs(len(tcount) - 32)))
    out.append(('not exactly 9 staff per team', sum(1 for v in tcount.values() if v != 9)))
    out.append(('employed salary <= 0', sum(1 for p in emp if p['salary'] <= 0)))
    out.append(('free agent salary != 0',
                sum(1 for p in new if p['teamID']=='Free Agent' and p['salary'] != 0)))
    # bound comes from a real game export (vanilla league), not from our files
    out.append(('startSeason outside 1988-2026',
                sum(1 for p in new if not 1988 <= p['startSeason'] <= 2026)))
    # the game gives startSeason a real spread that tracks age (corr -0.97).
    # a file with one distinct value has lost that.
    out.append(('startSeason flat (should spread with age)',
                1 if len({p['startSeason'] for p in new}) < 5 else 0))
    return out

# ------------------------------------------------------------ zero pattern

# roster fields that legitimately differ between files and would fire on every
# build if compared: money moves with the era, identity fields are per-season.
# Same purpose as STAFF_SKIP below.
ROSTER_SKIP = {'salary','guarantee','eSalary','eGuarantee','length','eLength',
               'draftSeason','draftNum','teamNum','iden'}

# staff fields that legitimately differ between files — see precedents
STAFF_SKIP = {'guarantee','eGuarantee','salary','eSalary','length','eLength','startSeason','age',
              'greed','loyalty','ambition'}

def zero_pattern(new, refs, kind):
    """A field never zero in the refs but zero in the new file is a bug,
    even though zero is technically in range. This found the crash.

    Staff must be compared WITHIN ROLE — a scout legitimately has zero
    playcalling, and pooling roles hides that."""
    pool = [p for r in refs for p in r]
    NUM = [k for k, v in pool[0].items() if isinstance(v, int)]
    bad = []
    if kind == 'staff':
        for role in sorted({p['role'] for p in pool}):
            n = [p for p in new if p['role'] == role]
            r = [p for p in pool if p['role'] == role]
            if len(n) < 15 or len(r) < 15: continue
            for k in NUM:
                if k in STAFF_SKIP: continue
                rz = sum(1 for p in r if p[k] == 0)/len(r)
                nz = sum(1 for p in n if p[k] == 0)/len(n)
                if abs(nz - rz) > 0.30:
                    bad.append(f'[{role}] {k}: new {100*nz:.0f}% zero vs ref {100*rz:.0f}%')
        return bad
    # Rosters are compared WITHIN POSITION, for exactly the reason staff are
    # compared within role: a linebacker legitimately has zero kickAccuracy,
    # and pooling positions hides it. Pooled, this check missed OLB coverage
    # being gated off in 2000 because MLB/CB/S at 100% diluted OLB at 0%.
    # Added 2026-09-01 after that gap was found by hand.
    for pos in sorted({p['position'] for p in pool}):
        n = [p for p in new if p['position'] == pos]
        r = [p for p in pool if p['position'] == pos]
        if len(n) < 15 or len(r) < 15:
            continue                      # too few to say anything
        for k in NUM:
            if k in ROSTER_SKIP:
                continue
            rz = sum(1 for p in r if p[k] == 0) / len(r)
            nz = sum(1 for p in n if p[k] == 0) / len(n)
            if abs(nz - rz) > 0.30:
                bad.append(f'[{pos}] {k}: new {100*nz:.0f}% zero vs ref {100*rz:.0f}%')
    return bad

# --------------------------------------------------------- cross-year meds

# attributes that only apply to some positions. Measuring these across the
# whole pool shows a median of 0 and looks like a bug when it isn't.
POS_SPECIFIC = {
    'sPassAcc': {'QB'}, 'mPassAcc': {'QB'}, 'dPassAcc': {'QB'}, 'throwOnRun': {'QB'},
    'kickAccuracy': {'K','P'},
    'tackle': {'MLB','OLB','DE','DT','CB','S'},
    'blockShedding': {'DE','DT','MLB','OLB'},
    'ballStrip': {'MLB','OLB','DE','DT','CB','S'},
    'manCover': {'MLB','CB','S'}, 'zoneCover': {'MLB','CB','S'},
    'releaseLine': {'WR','TE'}, 'routeRun': {'WR','TE','RB'},
    'vision': {'RB','WR'}, 'skillMove': {'RB','WR'},
    'trucking': {'RB','TE'}, 'elusiveness': {'RB','WR'},
    'rushBlock': {'OT','OG','C','TE'}, 'passBlock': {'OT','OG','C','RB'},
    'catching': {'WR','TE','RB'}, 'ballSecurity': {'RB','WR','TE','QB'},
}
# money and identity fields legitimately differ between eras — don't compare
SKIP_CROSS_YEAR = {'salary','guarantee','eSalary','eGuarantee','length','eLength',
                   'draftSeason','draftNum','teamNum','startSeason','age'}

def cross_year(new, refs, kind):
    """Compare medians per field per cohort. Catches scale bugs like the
    stamina problem (median 25 vs 83, from reading PSTM instead of PSTA).

    Two refinements that matter:
      - position-specific attributes are compared ONLY among the positions
        that use them, or every one looks broken
      - money fields are skipped; they differ by era by design
    """
    bad = []
    pool = [p for r in refs for p in r]
    NUM = [k for k, v in pool[0].items() if isinstance(v, int)]
    if kind == 'staff':
        # compare within role; pooling roles produces false alarms
        for role in sorted({p['role'] for p in pool}):
            n = [p for p in new if p['role'] == role]
            r = [p for p in pool if p['role'] == role]
            if len(n) < 15 or len(r) < 15: continue
            for k in NUM:
                if k in STAFF_SKIP: continue
                a, b = med([p[k] for p in n]), med([p[k] for p in r])
                if a is None or b is None: continue
                if abs(a-b) > 15 and abs(a-b) > 0.25*max(1, min(a, b)):
                    bad.append(f'[{role}] {k}: new {a} vs ref {b}')
        return bad
    cohorts = ('T','FA','Rookie')
    for coh in cohorts:
        def sel(src):
            return [p for p in src
                    if (cohort(p) if kind=='roster'
                        else ('FA' if p['teamID']=='Free Agent' else 'T')) == coh]
        n, r = sel(new), sel(pool)
        if len(n) < 20 or len(r) < 20: continue
        for k in NUM:
            if k in SKIP_CROSS_YEAR: continue
            pos = POS_SPECIFIC.get(k)
            nn = [p[k] for p in n if pos is None or p.get('position') in pos]
            rr = [p[k] for p in r if pos is None or p.get('position') in pos]
            if len(nn) < 20 or len(rr) < 20: continue
            a, b = med(nn), med(rr)
            if a is None or b is None: continue
            if abs(a-b) > 15 and abs(a-b) > 0.25*max(1, min(a, b)):
                bad.append(f'[{coh}] {k}: new {a} vs ref {b}')
    return bad

# ----------------------------------------------------------------- driver

def conditional(newp, srcp, out_field, src_field, name_cols=('forename','surname')):
    """Split an output field by its SOURCE value and show whether the groups differ.

    Catches the hardest bug class: a field with a perfectly reasonable
    distribution that has no relationship to the data it came from.
    Three bugs found this way — stamina reading a dead Madden field,
    percentile-filled attributes, and a name-hash face generator.

        python3 pgm3_validate.py conditional NEW.json SRC.csv stamina PSTA

    If every source value shows the same output spread, the source was
    never used, regardless of how sensible the overall distribution looks.
    """
    import csv, unicodedata
    def nrm(x):
        x = unicodedata.normalize('NFKD', str(x)).encode('ascii','ignore').decode().lower()
        x = x.replace('.','').replace("'",'').replace('-',' ')
        x = re.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',x)
        prev = None
        while prev != x:
            prev = x; x = re.sub(r'\b([a-z]) (?=[a-z]\b)', r'\1', x)
        return ' '.join(x.split())
    rows = list(csv.reader(open(srcp, encoding='utf-8', errors='ignore')))
    head = rows[0]; ix = {c: i for i, c in enumerate(head)}
    if src_field not in ix:
        print(f'source field {src_field} not in {srcp}'); return 1
    fn = 'PFNA' if 'PFNA' in ix else head[0]
    ln = 'PLNA' if 'PLNA' in ix else head[1]
    src = {}
    for r in rows[1:]:
        if len(r) >= len(head): src.setdefault(nrm(f'{r[ix[fn]]} {r[ix[ln]]}'), r[ix[src_field]])
    new = load(newp)
    # a source with many distinct values (0-99 ratings) is unreadable one row
    # per value — bucket it into deciles. Few values (PSKI 0/1/2) stay as-is.
    numeric = all(str(v).lstrip('-').isdigit() for v in src.values())
    distinct = len(set(src.values()))
    def bucket(v):
        if numeric and distinct > 12:
            n = int(v); lo = (n//10)*10
            return f'{lo}-{lo+9}'
        return v
    groups = collections.defaultdict(list)
    for p in new:
        k = nrm(' '.join(str(p[c]) for c in name_cols))
        if k in src:
            v = p[out_field]
            if isinstance(v, list):      # appearance array -> skin family digit
                v = split_tok(v[0])[1]
            elif isinstance(v, str):
                v = split_tok(v)[1] or v
            groups[bucket(src[k])].append(v)
    if not groups:
        print('no name matches between the two files'); return 1
    print(f'{out_field} conditioned on {src_field}   ({sum(len(v) for v in groups.values())} matched)')
    print('=' * 60)
    def sk(x):
        try: return (0, int(str(x).split('-')[0]))
        except Exception: return (1, str(x))
    for k in sorted(groups, key=sk):
        g = groups[k]
        if all(isinstance(x, (int, float)) for x in g):
            print(f'  {src_field}={k:>4} (n={len(g):>5}): median {med(g)}')
        else:
            c = collections.Counter(g); t = sum(c.values())
            top = ', '.join(f'{a}:{100*b/t:.0f}%' for a, b in sorted(c.items())[:6])
            print(f'  {src_field}={k:>4} (n={len(g):>5}): {top}')
    print('=' * 60)
    print('Groups should DIFFER. If they look alike, the source was never used.')
    return 0


# ------------------------------------------------------------------ faces

def _norm(x):
    import unicodedata
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii','ignore').decode().lower()
    x = re.sub(r'[^a-z ]','',x)
    return ' '.join(w for w in x.split() if w not in {'jr','sr','ii','iii','iv','v'}).strip()

def _find_registry():
    import os
    for c in ('reference/PGM3_FACE_REGISTRY.json','../reference/PGM3_FACE_REGISTRY.json',
              'PGM3_FACE_REGISTRY.json','/mnt/project/PGM3_FACE_REGISTRY.json',
              '/mnt/user-data/uploads/PGM3_FACE_REGISTRY.json'):
        if os.path.exists(c):
            return load(c)
    return None

def faces(paths, kind='roster'):
    """Cross-season face checks over a whole set of published files.

    Every check here exists because the bug happened on 2026-08-31.

        python3 pgm3_validate.py faces PGMRoster_2004.json PGMRoster_2007.json ...
        python3 pgm3_validate.py faces --staff PGMStaff_2004.json PGMStaff_2007.json ...
    """
    files = {p: load(p) for p in paths}
    res = []

    # ---- 1. structural: head/nose/mouth share a family digit; players wear no glasses
    bad_fam = bad_gl = tot = 0
    for p, recs in files.items():
        for r in recs:
            a = r.get('appearance') or []
            if len(a) < 8: continue
            tot += 1
            if len({split_tok(a[i])[1] for i in (0,5,6)}) != 1: bad_fam += 1
            if kind == 'roster' and a[7] != 'Glasses1e': bad_gl += 1
    res.append(('head/nose/mouth share a family digit',
                f'{bad_fam} of {tot} records violate' if bad_fam else ''))
    if kind == 'roster':
        res.append(('players wear Glasses1e',
                    f'{bad_gl} of {tot} records violate' if bad_gl else ''))

    # ---- 2. one person, one face across seasons
    per = collections.defaultdict(dict)
    for p, recs in files.items():
        for r in recs:
            if kind == 'roster' and cohort(r) != 'T': continue
            k = _norm(r['forename']) + ' ' + _norm(r['surname'])
            if kind == 'roster': k += '|' + r.get('position','')
            per[k][p] = r['appearance']
    multi = {k: v for k, v in per.items() if len(v) > 1}

    famv = [k for k, v in multi.items()
            if len({split_tok(a[0])[1] for a in v.values()}) > 1]
    hairv = [k for k, v in multi.items() if len({a[2] for a in v.values()}) > 1]
    varv  = [k for k, v in multi.items()
             if len({split_tok(a[0])[2] for a in v.values()}) > 1]

    res.append((f'head FAMILY constant across seasons ({len(multi)} multi-season people)',
                f'{len(famv)} differ: ' + ', '.join(famv[:4]) if famv else ''))
    res.append(('hair style constant across seasons',
                f'{len(hairv)} differ: ' + ', '.join(hairv[:4]) if hairv else ''))

    if kind == 'roster':
        # players SHOULD age: the variant letter is derived from age and weight.
        # A collapse here means someone wrote the registry face wholesale
        # instead of rewriting only the family digit.
        pct = 100.0 * len(varv) / len(multi) if multi else 0
        res.append((f'aging variant still varies ({len(varv)}/{len(multi)} = {pct:.0f}%)',
                    'aging looks flattened — did a pass write whole faces?' if pct < 25 else ''))
    else:
        # coaches have exactly one look; nothing about the face may move
        anyd = [k for k, v in multi.items() if len({tuple(a) for a in v.values()}) > 1]
        res.append(('staff face identical across seasons',
                    f'{len(anyd)} differ: ' + ', '.join(anyd[:4]) if anyd else ''))

    # ---- 3. verified (hand-edited) faces must be untouched
    reg = _find_registry()
    if reg is None:
        res.append(('verified faces intact', 'SKIPPED — registry not found'))
    else:
        vk = (reg.get('_verified_keys') or {}).get('players' if kind=='roster' else 'staff', {})
        block = reg['faces'] if kind == 'roster' else reg['staff_faces']
        checked = viol = ambig = 0
        names = []
        # AMBIGUOUS KEYS ARE REFUSED, NOT SCORED. staff_faces and
        # staff_faces_1986 share 46 keys and 40 hold different values, because
        # a bare name cannot separate two men: `jim mora` is Jim E. Mora
        # (1986 NO, 2000 IND, Head2c) in one block and Jim L. Mora (2000 SF,
        # Head1c) in the other. Both files carry the RIGHT face for each; the
        # gate was comparing the father against the son and calling it drift.
        # build_2000.py resolves this per (team, role); the gate cannot, so it
        # declines to score rather than guessing.
        alt = (reg.get('faces_1986') if kind == 'roster'
               else reg.get('staff_faces_1986')) or {}
        for p, recs in files.items():
            for r in recs:
                if kind == 'roster' and cohort(r) != 'T': continue
                nm = _norm(r['forename']) + ' ' + _norm(r['surname'])
                # BOTH KEY FORMATS. _verified_keys.players is keyed
                # name|POS|TEAM while this check built name|POS, so not one
                # verified player ever matched -- the gate was reporting clean
                # over 26% of what it protects. faces is keyed name|POS and
                # faces_1986 name|POS|TEAM, so the lock and the value can live
                # in different formats for the same man.
                k2 = nm + '|' + r.get('position','') if kind == 'roster' else nm
                k3 = k2 + '|' + (r.get('teamID') or '')
                vkey = k3 if k3 in vk else (k2 if k2 in vk else None)
                if vkey is None: continue
                # PRECEDENCE: the 3-part block wins for a 3-part verified key.
                # 23 keys live in BOTH blocks with DIFFERENT values, and six of
                # those are verified. Preferring the 2-part block reported all
                # six as drifted when every one matches faces_1986 exactly --
                # six false positives, four of which were reported as newly
                # discovered drift.
                want = alt.get(k3) if vkey == k3 else None
                if want is None: want = block.get(k2)
                if want is None: want = alt.get(k3)
                other = alt.get(k2) if kind != 'roster' else None
                if other is not None and want is not None and other != want:
                    ambig += 1; continue
                if want is None: continue
                k = vkey
                checked += 1
                got = r['appearance']
                # family must match everywhere; variant may differ (players age)
                same = all(split_tok(want[i])[1] == split_tok(got[i])[1] for i in (0,5,6)) \
                       and all(want[i] == got[i] for i in (1,2,3,4,7,8))
                if not same:
                    viol += 1
                    if len(names) < 4: names.append(f'{k} @ {p}')
        res.append((f'verified faces intact ({checked} checked, {len(vk)} in registry'
                    + (f', {ambig} ambiguous' if ambig else '') + ')',
                    f'{viol} overwritten: ' + ', '.join(names) if viol else ''))

    # ---- 4. head-family distribution per position, against the reference band.
    # This is the check that would have caught 1986: 44% of the league in one
    # family, every anchor and every marginal passing.
    if kind == 'roster' and len(files) > 1:
        share = {}
        for p, recs in files.items():
            c = collections.Counter()
            for r in recs:
                if cohort(r) != 'T': continue
                c[split_tok(r['appearance'][0])[1]] += 1
            t = sum(c.values()) or 1
            share[p] = {f: 100.0*c[f]/t for f in c}
        fams = sorted({f for d in share.values() for f in d})
        odd = []
        for f in fams:
            vals = [share[p].get(f, 0) for p in share]
            lo, hi = min(vals), max(vals)
            if hi - lo > 25:
                worst = max(share, key=lambda p: share[p].get(f,0))
                odd.append(f'family {f}: {lo:.0f}-{hi:.0f}% (worst {worst})')
        res.append(('head-family distribution comparable across files',
                    '; '.join(odd) if odd else ''))
    return res


def main():
    # --salary=, --eSalary=, --eGuarantee=, --team_cap= override the defaults.
    # Accepts plain numbers or shorthand: --team_cap=301.2M
    argv = []
    for a in sys.argv:
        m = re.match(r'--(salary|eSalary|eGuarantee|team_cap)=([\d._]+)([MmKk]?)$', a)
        if m:
            n = float(m.group(2).replace('_',''))
            n *= {'m':1e6, 'k':1e3, '':1}[m.group(3).lower()]
            LIMITS[m.group(1)] = int(n)
        else:
            argv.append(a)
    sys.argv = argv
    if len(sys.argv) >= 2 and sys.argv[1] == 'faces':
        staff = '--staff' in sys.argv
        paths = [a for a in sys.argv[2:] if not a.startswith('--')]
        if not paths:
            print('usage: pgm3_validate.py faces [--staff] FILE.json [FILE.json ...]'); sys.exit(1)
        kind = 'staff' if staff else 'roster'
        print(f'FACES ({kind}): {len(paths)} file(s)')
        print('=' * 72)
        res = faces(paths, kind)
        for n, c in res:
            print(f'  {"FAIL" if c else "ok  "}  {n}' + (f'   [{c}]' if c else ''))
        print('-' * 72)
        bad = [n for n, c in res if c and not c.startswith('SKIPPED')]
        print(f'{len(bad)} failing check(s)' if bad else 'all face checks passed')
        sys.exit(1 if bad else 0)
    if len(sys.argv) >= 2 and sys.argv[1] == 'conditional':
        if len(sys.argv) < 6:
            print('usage: pgm3_validate.py conditional NEW.json SRC.csv OUT_FIELD SRC_FIELD'); sys.exit(1)
        sys.exit(conditional(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    kind, newp, refps = sys.argv[1], sys.argv[2], sys.argv[3:]
    new = load(newp); refs = [load(p) for p in refps]
    print(f'{kind.upper()}: {newp}  ({len(new)} records)')
    print(f'reference union: {", ".join(refps)}')
    if kind == 'roster':
        print(f'limits: salary {LIMITS["salary"]/1e6:.1f}M  eSalary {LIMITS["eSalary"]/1e6:.1f}M  '
              f'eGuarantee {LIMITS["eGuarantee"]/1e6:.1f}M  cap {LIMITS["team_cap"]/1e6:.1f}M'
              '   (provisional — see LIMITS)')
    print('=' * 72)
    res = check_roster(new, refs) if kind == 'roster' else check_staff(new, refs)
    fails = [(n, c) for n, c in res if c]
    for n, c in res:
        print(f'  {"FAIL" if c else "ok  "}  {n}' + (f'   [{c}]' if c else ''))
    print('-' * 72)
    zp = zero_pattern(new, refs, kind)
    print(f'  {"FAIL" if zp else "ok  "}  zero-pattern vs reference')
    for b in zp: print(f'          {b}')
    cy = cross_year(new, refs, kind)
    weak = len(refs) < 2          # one reference is not enough to call a difference a bug
    tag = 'WARN' if (cy and weak) else ('FAIL' if cy else 'ok  ')
    print(f'  {tag}  cross-year medians by cohort')
    for b in cy: print(f'          {b}')
    print('=' * 72)
    total = len(fails) + (1 if zp else 0) + (0 if weak else (1 if cy else 0))
    print('ALL CLEAR' if total == 0 else f'{total} CHECK GROUP(S) FAILED')
    sys.exit(0 if total == 0 else 1)

if __name__ == '__main__':
    main()
