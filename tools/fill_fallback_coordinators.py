#!/usr/bin/env python3
"""
fill_fallback_coordinators — 1979's seniority fallbacks, on career standing.
Ruled by Ryan 2026-09-04.

    python3 tools/fill_fallback_coordinators.py --dry-run
    python3 tools/fill_fallback_coordinators.py

THE RULE, as amended. Where no titled coordinator existed, the slot takes the
senior assistant on that side of the ball, and **seniority means career standing,
not title rank** — the man with the longer career on that side by 1979, from the
Coaching Tree's career span. Title order survives only as the tiebreak when
career standing is silent.

The amendment exists because title rank failed in three distinct ways, which is
a better argument for it than any single case:

  * THE MAN HAD JUST ARRIVED. Five of the nine. Sam Wyche's entire career begins
    on the 1979 San Francisco staff; Ken Iman had three years. Titles go to
    newcomers and standing does not.
  * THE MAN HAD BEEN A HEAD COACH OR COORDINATOR AND WAS NOW A POSITION COACH.
    Five of the nine — John North, Lew Carpenter, Charlie Sumner, Sid Gillman,
    Jack Christiansen. Not "just arrived" but moved or demoted; different cause,
    same fix.
  * NEITHER. Ollie Spencer, seventeen unbroken years on the Raiders' offensive
    line, passed over because a five-year man shared his title.

NO MINIMUM MARGIN, ruled explicitly. Seattle's offence is the narrowest call in
the table — Howard Mudd's five years against Jerry Rhome's three — and it is
marked as such in the sidecar so a reviewer knows where the rule is weakest. A
threshold would be a second arbitrary rule protecting the first, and title order
is not a good enough default to deserve that protection.

WHERE THE RULE REACHES THE SAME MAN AS TITLE ORDER it is left alone: twelve of
the twenty-one, including Bill Arnsparger at Miami, the case Ryan named as the
test. A rule that moved him would have been suspect.

AGES ARE NOT TOUCHED, ruled a separate pass. Each man keeps his slot's existing
age and the sidecar says the age is not sourced — the Coaching Tree carries a
birth date for every one of these nine, and that pass gets scored against a known
reference before any of it is written.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 1979
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
REG = 'reference/PGM3_FACE_REGISTRY.json'
COMPARISON = 'wip/fallback_rule_comparison.csv'

# --agreed writes the FOURTEEN slots where career standing and title order reach
# the SAME man. They were held with the rest of the fallbacks while the rule was
# in question and then missed, because "write the nine" meant the nine that
# CHANGED — so Pittsburgh read an invented man while both rules said Rollie
# Dotsch. The easy cases sat behind a ruling they did not need.
AGREED = [
    ('ARI', 'Off Co-ord', 'Harry Gilmer',        22, 'Leon McLaughlin',  13),
    ('BAL', 'Off Co-ord', 'Dick Bielski',        15, 'Ernie Zwahlen',    12),
    ('CIN', 'Off Co-ord', 'Mike McCormack',      13, 'Boyd Dowler',       0),
    ('CLE', 'Off Co-ord', 'Jim Shofner',         12, 'Jim Garrett',      11),
    ('DET', 'Def Co-ord', 'Marty Schottenheimer', 5, 'Floyd Peters',      5),
    ('DET', 'Off Co-ord', 'Bob Schnelker',       16, 'Fred Hoaglin',      0),
    ('HOU', 'Off Co-ord', 'King Hill',            7, 'Joe Bugel',         4),
    ('KC',  'Off Co-ord', 'Joe Spencer',         18, 'Tom Pagna',         1),
    ('MIA', 'Def Co-ord', 'Bill Arnsparger',     15, 'Mike Scarry',       0),
    ('MIA', 'Off Co-ord', 'John Sandusky',       20, 'Dan Henning',       0),
    ('MIN', 'Def Co-ord', 'Bob Hollway',         12, 'Murray Warmath',    1),
    ('NYG', 'Off Co-ord', 'Ernie Adams',          0, 'Dick Scesniak',     0),
    ('PIT', 'Off Co-ord', 'Rollie Dotsch',        8, 'Dick Hoak',         7),
    ('TB',  'Off Co-ord', 'Bill Nelsen',          6, 'George Chaump',     0),
]
# team, slot, man, his years by 1979, the title-order pick he displaces and his years
FILLS = [
    ('ATL', 'Off Co-ord', 'John North',        14, 'Ted Plumb',         5),
    ('DEN', 'Off Co-ord', 'Whitey Dovell',     12, 'Babe Parilli',      8),
    ('GB',  'Off Co-ord', 'Lew Carpenter',     15, 'Zeke Bratkowski',  10),
    ('LV',  'Def Co-ord', 'Charlie Sumner',    16, 'Myrel Moore',       7),
    ('LV',  'Off Co-ord', 'Ollie Spencer',     17, 'Sam Boghosian',     5),
    ('PHI', 'Off Co-ord', 'Sid Gillman',       24, 'Ken Iman',          3),
    ('SEA', 'Def Co-ord', 'Jack Christiansen', 20, 'Larry Peccatiello', 7),
    ('SEA', 'Off Co-ord', 'Howard Mudd',        5, 'Jerry Rhome',       3),
    ('SF',  'Off Co-ord', 'Bobb McKittrick',    8, 'Sam Wyche',         0),
]
CLOSEST = ('SEA', 'Off Co-ord')
# THREE OF THE NINE ARE ALREADY IN THE FILE, parked in the free-agent head-coach
# pool: North, Gillman and Christiansen, all former head coaches, which is why
# the 1979 build's coach pool picked them up. Same defect as Ken Meyer, Jim Ringo
# and Tom Bettis, same ruling — a man in his actual job beats a man in a pool
# plus an invented one in the slot — so they MOVE and their pool record is
# deleted rather than being filled around.
BIRTH = {'John North': 1921, 'Sid Gillman': 1911, 'Jack Christiansen': 1928,
         'Whitey Dovell': 1927, 'Lew Carpenter': 1932, 'Charlie Sumner': 1930,
         'Ollie Spencer': 1931, 'Howard Mudd': 1942, 'Bobb McKittrick': 1935,
         'Harry Gilmer': 1926, 'Dick Bielski': 1932, 'Mike McCormack': 1930,
         'Jim Shofner': 1935, 'Marty Schottenheimer': 1943, 'Bob Schnelker': 1928,
         'King Hill': 1936, 'Joe Spencer': 1923, 'Bill Arnsparger': 1926,
         'John Sandusky': 1925, 'Bob Hollway': 1926, 'Ernie Adams': 1953,
         'Rollie Dotsch': 1933, 'Bill Nelsen': 1941}


def norm(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    x = re.sub(r'[^a-z ]', '', x)
    return ' '.join(w for w in x.split() if w not in {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}).strip()


def serialiser(path):
    head = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True, text=True, cwd=repo('')).stdout
    for f in (lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, separators=(', ', ': ')),
              lambda d: json.dumps(d, separators=(',', ':'))):
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head:
                return (lambda ff, nn: (lambda x: ff(x) + nn))(f, nl)
    raise AssertionError(f'{path}: stored formatting not reproduced')


def main():
    dry = '--dry-run' in sys.argv
    path = f'PGMStaff_{Y}.json'
    ser = serialiser(path)
    d = json.load(open(repo(path)))
    reg = json.load(open(repo(REG)))
    staff_faces = reg.get('staff_faces', {})
    prov = {(r['file'], r['iden']): r for r in csv.DictReader(open(repo(SIDECAR)))}
    present = {}
    for p in d:
        present.setdefault(norm(p['forename'] + ' ' + p['surname']), []).append(f"{p['teamID']}/{p['role']}")

    agreed = '--agreed' in sys.argv
    work = AGREED if agreed else FILLS
    edits = {}; drop = set(); age_gaps = []; held = []
    print(f'{Y}: {len(work)} fallback slots — '
          + ('career standing and title order AGREE' if agreed else 'career standing overturns title order'))
    for team, slot, man, yrs, displaced, dyrs in work:
        rec = [p for p in d if p['teamID'] == team and p['role'] == slot]
        assert len(rec) == 1, f'{team} {slot}: expected one record, found {len(rec)}'
        rec = rec[0]
        # NAMESAKE / DUPLICATE CHECK before applying anything by name -- the
        # LeBeau defect is one file-write away every single time.
        pool = [p for p in d if p['teamID'] == 'Free Agent'
                and norm(p['forename'] + ' ' + p['surname']) == norm(man)]
        elsewhere = [p for p in d if p['teamID'] != 'Free Agent'
                     and norm(p['forename'] + ' ' + p['surname']) == norm(man)]
        if elsewhere:
            # HELD, NOT FORCED. Two of the fourteen collide with a man who already
            # holds a job in this file, and each collision is a contradiction
            # between our source and the Coaching Tree rather than a duplicate to
            # resolve mechanically:
            #   Marty Schottenheimer is Cleveland's Def Co-ord, marked `sourced`.
            #     The Coaching Tree puts him on DETROIT's linebackers in 1979 and
            #     has him reaching Cleveland in 1980. Our file may be a year early.
            #   Bill Arnsparger is CAROLINA's head coach, `named by Ryan` — on a
            #     franchise that did not exist in 1979. His real 1979 job is at
            #     Miami, which is the slot this pass wants to fill.
            held.append((team, slot, man, [f"{p['teamID']}/{p['role']}" for p in elsewhere]))
            continue
        assert len(pool) <= 1, f'{man} appears {len(pool)} times in the free-agent pool'
        pv = prov.get((str(Y), rec['iden']), {}).get('provenance', '')
        assert pv.startswith('invented'), f'{team} {slot} is {pv!r}, not an invented slot — refusing'

        was = f"{rec['forename']} {rec['surname']}"
        fn, ln = man.split(' ', 1)
        rec['forename'], rec['surname'] = fn, ln
        moved = bool(pool)
        if moved:
            src = pool[0]
            rec['age'] = src['age']
            rec['appearance'] = list(src['appearance'])
            drop.add(src['iden'])
        else:
            face = staff_faces.get(norm(man))
            if isinstance(face, list) and len(face) == 9:
                rec['appearance'] = list(face)
        if BIRTH.get(man) and abs((Y - BIRTH[man]) - rec['age']) > 2:
            age_gaps.append((team, slot, man, rec['age'], Y - BIRTH[man]))
        how = (f'Coaching Tree: the {Y} {team} staff had no titled '
               f'{"offensive" if slot == "Off Co-ord" else "defensive"} coordinator, so the slot takes '
               f'the senior assistant on that side by CAREER STANDING — {man} had {yrs} years by {Y}'
               + (f', and title order reaches the same man' if agreed else
                  f' against {displaced}\'s {dyrs}, whom title order would have chosen')
               + '. INFERRED, not a titled coordinator; age not sourced')
        if moved:
            how += ('. Moved out of the free-agent head-coach pool, where the 1979 build had parked '
                    'him while an invented man held the job he actually had; his free-agent record is gone')
        if (team, slot) == CLOSEST and not agreed:
            how += ('. THE CLOSEST CALL IN THE TABLE: five years against three, the narrowest margin on '
                    'which this rule overturns title order anywhere in 1979')
        edits[(str(Y), rec['iden'])] = (man, 'real (name in a real source)', how)
        print(f'  {team} {slot:<12} {was:<20} -> {man:<18} ({yrs} yrs vs {displaced} {dyrs})'
              + ('  [moved from the free-agent pool]' if moved else '')
              + ('   <- closest call' if (team, slot) == CLOSEST else ''))

    if held:
        print('  HELD — the man already holds a job in this file, and the clash is a source '
              'contradiction rather than a duplicate:')
        for t, sl, m, where in held:
            print(f'     {t} {sl:<12} wanted {m:<22} but he is already at {", ".join(where)}')
    before_employed = sum(1 for p in d if p['teamID'] != 'Free Agent')
    d = [p for p in d if p['iden'] not in drop]
    assert before_employed == sum(1 for p in d if p['teamID'] != 'Free Agent') == 288
    print(f'  {len(drop)} free-agent records deleted; employed staff stays 288')
    if age_gaps:
        print('  ages the separate pass must correct (file vs the source\'s birth date):')
        for t, sl, m, has, should in age_gaps:
            print(f'     {t} {sl:<12} {m:<18} file says {has}, born {BIRTH[m]} so {should} in {Y}')
        with open(repo('wip/staff_age_gaps_1979_coordinators%s.csv' % ('_agreed' if agreed else '')), 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['team', 'slot', 'name', 'file_age', 'age_from_birth_date', 'birth_year'])
            for t, sl, m, has, should in age_gaps: w.writerow([t, sl, m, has, should, BIRTH[m]])

    raw = open(repo(SIDECAR), newline='').read()
    term = '\r\n' if '\r\n' in raw else '\n'
    trailing = term if raw.endswith(term) else ''
    rows = raw.split(term)
    if trailing:
        rows = rows[:-1]
    out = [rows[0]]; hit = 0
    for line in rows[1:]:
        parts = next(csv.reader([line]))
        k = (parts[0], parts[1])
        if parts[0] == str(Y) and parts[1] in drop:
            continue
        if k in edits:
            name, provv, how = edits[k]
            parts[5], parts[6], parts[7] = name, provv, how
            b = io.StringIO(); csv.writer(b, lineterminator='').writerow(parts)
            out.append(b.getvalue()); hit += 1
        else:
            out.append(line)
    assert hit == len(edits), f'sidecar matched {hit} of {len(edits)} records'
    print(f'  {hit} sidecar rows rewritten')

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join(out) + trailing)
    print(f'  wrote {path} and the sidecar — now run tools/reconcile_faces.py --staff')


if __name__ == '__main__':
    main()
