"""Pass A2 -- replace drawn staff ages with sourced birth years, archive-wide.

MEASURED CORRECTION TO THE TASK BRIEF: this is NOT archive-wide in the sense of
all seven files being drawn. Checked against sourced birth years:

    file  checkable  exact  within +/-2  off by >=10
    1986      99       69        77          15
    2004     101        0        20          41
    2007      97       86        87           7
    2010      79        2        11          35
    2013     106      102       104           2
    2017     103        4        16          52
    2021     105       83        86           9

1986, 2007, 2013 and 2021 are largely CORRECT -- 2013 is 102 of 106 exact.
Only 2004, 2010 and 2017 are broadly drawn. Bill Belichick is right in four
files and wrong in three, which is what the drift across 2004/2010/2017 was
showing. (2021's second Belichick at 34 is Steve Belichick, a real coach.)

So this pass is targeted, not wholesale: a record is rewritten only where a
sourced birth year exists AND disagrees with the file. Correct ages are left
alone rather than overwritten with the same value, which keeps the diff honest
and avoids replacing a right answer with a source false positive.

Scout and physio records are invented people under the standing ruling and are
never touched.

startSeason is refitted per file on that file's own age relationship, each
record keeping its own residual, clamped to that file's own observed range.
"""
import json, csv, sys, os, statistics, collections

COACH = {'Head Coach', 'Off Co-ord', 'Def Co-ord', 'Special Teams'}
FILES = [1986, 2004, 2007, 2010, 2013, 2017, 2021]
# 2004 stores forename 'Frank Gansz' / surname 'Jr.'; 2007 has the correct
# split. Fixed opportunistically here since both staff files are being written.
GANSZ = {2004: (('Frank Gansz', 'Jr.'), ('Frank', 'Gansz Jr.'))}


def detect_format(path):
    raw = open(path, encoding='utf-8').read()
    d = json.loads(raw)
    for sep in ((',', ':'), (', ', ': ')):
        for asc in (False, True):
            kw = dict(ensure_ascii=asc, separators=sep)
            if json.dumps(d, **kw) == raw:
                return d, kw
    raise SystemExit(f'{path}: no dumps setting reproduces the file')


def load_births():
    out = {}
    for r in csv.DictReader(open('sources/coach_birth_years.csv', encoding='utf-8')):
        out[r['name']] = int(r['birth_year'])
    return out


def fix(year, births, dry=False, _hook=None):
    path = f'PGMStaff_{year}.json'
    recs, kw = detect_format(path)
    n_in = len(recs)
    before = [dict(p) for p in recs]

    pts = [(p['age'], p['startSeason']) for p in recs]
    ma = statistics.mean(a for a, _ in pts); ms = statistics.mean(s for _, s in pts)
    var = statistics.pvariance([a for a, _ in pts])
    b = (sum((a - ma) * (s - ms) for a, s in pts) / len(pts)) / var
    a0 = ms - b * ma
    lo_ss = min(s for _, s in pts); hi_ss = max(s for _, s in pts)

    changed = gansz = 0
    for p in recs:
        if year in GANSZ:
            bad, good = GANSZ[year]
            if (p['forename'], p['surname']) == bad:
                p['forename'], p['surname'] = good; gansz += 1
        if p['role'] not in COACH or p['teamID'] == 'Free Agent':
            continue
        n = f"{p['forename']} {p['surname']}"
        if n not in births:
            continue
        new_age = year - births[n]
        if new_age == p['age'] or not (20 <= new_age <= 85):
            continue
        resid = p['startSeason'] - (a0 + b * p['age'])
        p['age'] = new_age
        p['startSeason'] = max(lo_ss, min(hi_ss, int(round(a0 + b * new_age + resid))))
        changed += 1

    if _hook:
        _hook(recs)

    # ---- guards --------------------------------------------------------
    assert len(recs) == n_in, f'{year}: record count moved {n_in} -> {len(recs)}'
    assert [p['appearance'] for p in before] == [p['appearance'] for p in recs], \
        f'{year}: appearance changed -- _verified_keys at risk'
    for o, nw in zip(before, recs):
        moved = [k for k in o if o[k] != nw[k]]
        if not moved:
            continue
        assert set(moved) <= {'age', 'startSeason', 'forename', 'surname'}, \
            f'{year}: unexpected field(s) changed: {moved}'
        assert nw['role'] in COACH, \
            f'{year}: an invented staff record moved ({nw["role"]})'
    bad = [(p['forename'], p['surname'], p['age']) for p in recs
           if p['role'] in COACH and not (20 <= p['age'] <= 85)]
    assert not bad, f'{year}: implausible coach age {bad}'
    ss = [p['startSeason'] for p in recs]
    assert lo_ss <= min(ss) and max(ss) <= hi_ss, \
        f'{year}: startSeason left its own range {lo_ss}-{hi_ss}'

    print(f'  {year}: {changed:3} ages corrected'
          + (f', Gansz name split fixed' if gansz else ''))
    if not dry:
        json.dump(recs, open(path, 'w', encoding='utf-8'), **kw)
    return changed


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    births = load_births()
    print(f'  {len(births)} sourced birth years')
    tot = sum(fix(y, births, dry) for y in FILES)
    print(f'  TOTAL {tot} coach ages corrected')
