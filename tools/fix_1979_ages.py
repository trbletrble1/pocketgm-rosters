#!/usr/bin/env python3
"""
fix_1979_ages — real ages for 1979's real staff. Ruled by Ryan 2026-09-04.

    python3 tools/fix_1979_ages.py --dry-run
    python3 tools/fix_1979_ages.py

THE SOURCES, scored against each other before anything was written, and the
answer changed twice as the sample grew.

At n=29 they agreed 20 of 20, to the day. **At n=55 they disagree four times, and
every disagreement is StatsCrew matching a DIFFERENT MAN**: George Allen 1944
against 1918, John McKay 1953 against 1923 — the head coach's son, a receiver —
and Bill Walsh 1927 against 1931, which is Atlanta's offensive line coach against
San Francisco's head coach. Gino Cappelletti differs by a single year and may be
an ordinary discrepancy rather than a collision.

**So the small clean sample was luck, not proof.** 51 of 55 still agree and the
sources are both good; what fails is matching a name against a database holding
every professional footballer since 1920, where a son, a brother and an unrelated
namesake are all waiting.

**THE COACHING TREE IS PRIMARY HERE, because it is a database OF COACHES.** Asked
for a 1979 coach it returns that coach; StatsCrew asked for the same name returns
whoever played under it. StatsCrew fills only the men the Coaching Tree lacks,
and only when the date is possible for a man coaching in 1979.

COVERAGE: the Coaching Tree dates 114 of 1979's 124 real employed staff and
StatsCrew adds 4, for 118. The 164 generated scouts and physios are not counted —
a generated man has no birth date to find, and including them would flatter the
figure. **The men neither source dates are left exactly as they are and flagged,
not estimated.**

AGE = 1979 - birth year, which matches every case the archive already had right
(Gillman 68, Christiansen 51, Ringo 48).

STARTSEASON MOVES WITH AGE, because it is computed from it: r(age, startSeason)
is -0.942 in this file. Leaving it would produce a 63-year-old with a
27-year-old's experience, a worse artifact than the one being fixed. It is
expressed on the GAME clock, 1989-2026, the same convention as draftSeason.

**Each man keeps his own residual.** Rather than flattening everyone onto a
fitted line -- which would erase the spread the file legitimately has, ten years
of it at some ages -- the pass moves a man's tenure by the archive's own slope:

    new_tenure = old_tenure + slope * (new_age - old_age)

so a man who was unusually experienced for his age stays unusually experienced.
The slope is least-squares fitted on this file's employed staff and comes out
near 0.8 years of tenure per year of age.

1986 IS NOT TOUCHED and neither is any other file. 1986's startSeason correlates
with nothing measurable -- best absolute r 0.23 across every numeric field, age
at 0.175 -- so it is independent data, and only 1979's ages are in question here.

GROWTH CURVES ARE NOT REBUILT. They are not age-conditioned in any file:
r(age, curve) runs +0.03 to -0.13, and they are conditioned on potential minus
rating, with 288 of 288 records obeying the 50x rule in every file. Rebuilding
them would be a change with no cause.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 1979
GAME_MIN, GAME_MAX = 1989, 2026
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
SC = 'wip/statscrew_dates_1979.csv'
CT = 'wip/coachtree_dates_1979.csv'
# the Coaching Tree dates gathered during the fill passes, before the bulk pull
CT_EARLY = {'John North': 1921, 'Sid Gillman': 1911, 'Jack Christiansen': 1928, 'Whitey Dovell': 1927,
            'Lew Carpenter': 1932, 'Charlie Sumner': 1930, 'Ollie Spencer': 1931, 'Howard Mudd': 1942,
            'Bobb McKittrick': 1935, 'Harry Gilmer': 1926, 'Dick Bielski': 1932, 'Mike McCormack': 1930,
            'Jim Shofner': 1935, 'Marty Schottenheimer': 1943, 'Bob Schnelker': 1928, 'King Hill': 1936,
            'Joe Spencer': 1923, 'Bill Arnsparger': 1926, 'John Sandusky': 1925, 'Bob Hollway': 1926,
            'Ernie Adams': 1953, 'Rollie Dotsch': 1933, 'Bill Nelsen': 1941, 'Tom Keane': 1926,
            'Chuck Weber': 1930, 'Frank Gansz': 1938, 'Ken Meyer': 1926, 'Jim Ringo': 1931,
            'Tom Bettis': 1933}


def serialiser(path):
    head = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True, text=True, cwd=repo('')).stdout
    for f in (lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, separators=(', ', ': ')),
              lambda d: json.dumps(d, separators=(',', ':'))):
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head:
                return (lambda ff, nn: (lambda x: ff(x) + nn))(f, nl)
    raise AssertionError(f'{path}: stored formatting not reproduced')


def birth_years():
    """StatsCrew first so the Coaching Tree overwrites it: the coaching database
    wins every collision, because a name is not an identity."""
    out = {}
    for r in csv.DictReader(open(repo(SC))):
        if r['born']:
            out[r['name']] = (int(r['born'].split(', ')[1]), 'StatsCrew')
    for name, y in CT_EARLY.items():
        out[name] = (y, 'Coaching Tree')
    for r in csv.DictReader(open(repo(CT))):
        if r['birth_date']:
            out[r['name']] = (int(r['birth_date'][:4]), 'Coaching Tree')
    return out


def main():
    dry = '--dry-run' in sys.argv
    path = f'PGMStaff_{Y}.json'
    ser = serialiser(path)
    d = json.load(open(repo(path)))
    prov = {(r['file'], r['iden']): r for r in csv.DictReader(open(repo(SIDECAR)))}
    emp = [p for p in d if p['teamID'] != 'Free Agent']
    real = [p for p in emp
            if prov.get((str(Y), p['iden']), {}).get('provenance', '').startswith(('real', 'sourced', 'named'))]
    born = birth_years()

    # slope of tenure on age, least squares over the employed staff
    xs = [p['age'] for p in emp]; ys = [2026 - p['startSeason'] for p in emp]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)

    before_ages = [p['age'] for p in emp]
    changed = []; undated = []; implausible = []
    for p in real:
        name = f"{p['forename']} {p['surname']}"
        if name not in born:
            undated.append(name); continue
        by, src = born[name]
        new_age = Y - by
        # A LAST PLAUSIBILITY GUARD AT THE WRITE. The first run of this pass
        # produced Joe Gibbs born 1988 and a head coach aged -16, because the
        # StatsCrew matcher took a modern namesake off a century-wide database.
        # That is fixed at the source now, and the guard stays here anyway: no
        # age reaches a published file without being possible.
        if not (23 <= new_age <= 80):
            implausible.append((name, new_age, by, src)); continue
        if new_age == p['age']:
            continue
        old_ss = p['startSeason']
        new_ss = int(round(2026 - ((2026 - old_ss) + slope * (new_age - p['age']))))
        new_ss = max(GAME_MIN, min(GAME_MAX, new_ss))
        changed.append((name, p['teamID'], p['role'], p['age'], new_age, old_ss, new_ss, src, by))
        p['age'] = new_age
        p['startSeason'] = new_ss

    after_ages = [p['age'] for p in emp]
    q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
    print(f'{Y}: {len(emp)} employed, {len(real)} of them real men')
    print(f'  dated by a source: {len(real) - len(undated)} of {len(real)}'
          f'   ({sum(1 for c in changed if c[7] == "StatsCrew")} of the changes from StatsCrew, '
          f'{sum(1 for c in changed if c[7] == "Coaching Tree")} from the Coaching Tree)')
    print(f'  UNDATED, left exactly as they are: {len(undated)} — {", ".join(sorted(undated))}')
    print(f'  ages corrected: {len(changed)}')
    if implausible:
        print(f'  REFUSED as implausible, left as they are: {len(implausible)} — '
              + '; '.join(f'{n} would be {a} (born {b}, {s})' for n, a, b, s in implausible))
    print(f'  tenure slope fitted on this file: {slope:.3f} years per year of age')
    print(f'\n  age distribution, employed staff        min  p25  median  p75  max   mean')
    print(f'    before   {min(before_ages):>3} {q(before_ages,.25):>4} {q(before_ages,.5):>6} '
          f'{q(before_ages,.75):>5} {max(before_ages):>5}  {sum(before_ages)/len(before_ages):>6.1f}')
    print(f'    after    {min(after_ages):>3} {q(after_ages,.25):>4} {q(after_ages,.5):>6} '
          f'{q(after_ages,.75):>5} {max(after_ages):>5}  {sum(after_ages)/len(after_ages):>6.1f}')
    worst = sorted(changed, key=lambda c: -abs(c[4] - c[3]))[:10]
    print('\n  the ten furthest out:')
    for nm, t, role, oa, na, os_, ns, src, by in worst:
        print(f'    {nm:<22} {t:<4} {role:<14} age {oa:>2} -> {na:>2}  (born {by}, {src})'
              f'   startSeason {os_} -> {ns}')
    assert sum(1 for p in d if p['teamID'] != 'Free Agent') == 288, 'employed staff must stay 288'

    if dry:
        print('\n  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo('wip/age_fix_1979.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['name', 'team', 'role', 'age_before', 'age_after', 'startSeason_before',
                    'startSeason_after', 'source', 'birth_year'])
        w.writerows(changed)
    print(f'\n  wrote {path} and wip/age_fix_1979.csv')


if __name__ == '__main__':
    main()
