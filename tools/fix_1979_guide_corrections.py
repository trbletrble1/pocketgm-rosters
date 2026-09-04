#!/usr/bin/env python3
"""
fix_1979_guide_corrections — the two records the team media guides overturn.
Ruled by Ryan 2026-09-04.

    python3 tools/fix_1979_guide_corrections.py --dry-run
    python3 tools/fix_1979_guide_corrections.py

All 28 of 1979's team guides were pulled and the season's 84 coordinator slots
diffed against them. **Two records are wrong, and only two**, both confirmed by
reading the book rather than by a matcher:

  PITTSBURGH. The Steelers' own guide lists `ROBERT (WOODY) WIDENHOFER Defensive
  Coordinator` and puts George Perles at Assistant Head Coach. We had Perles in
  the coordinator slot on the Coaching Tree's say-so.

  MIAMI. The Dolphins' staff list reads `Offensive Backs, Special Teams: Carl
  Taseff`, and lists **Steve Crosby — the man we had in that slot — as Assistant
  Director of Player Personnel.** He was in the front office, not coaching.

Both replacements' ages come from the same books that identified them: Taseff
`Born Sept. 28, 1928`, and Widenhofer 1943-01-20 from the Coaching Tree, which
the guide corroborates as a coordinator that season.

AGE AND STARTSEASON MOVE TOGETHER, the standing rule: the attributes belong to
the person, and 1979's startSeason is computed from age (r = -0.94), so a man
carried into a slot brings his own age and his tenure is recomputed on the file's
own slope. Rating, potential and the growth curve stay with the slot.

WHAT LEAVES. George Perles was Pittsburgh's assistant head coach and Steve Crosby
was a Miami scout, and **PGM3 has a slot for neither** — the same limitation item
71 recorded when eight position coaches had to leave the file. Crosby is the
narrower case: the format DOES have scout slots, and Miami's are generated men,
so a later pass could put a real personnel man in one. Not done here; this pass
is the two corrections and nothing else.

WHY NOT MORE. The automated diff flagged fourteen disagreements and reading them
dissolved twelve — compound titles (`Def. Coordinator/Linebackers`), dotted
leader lines, OCR'd surnames. Several slots it called silent are confirmations
instead: Cleveland's book names Chuck Weber and Jim Shofner, the two men the
career-standing rule chose by arithmetic alone.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 1979
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
REG = 'reference/PGM3_FACE_REGISTRY.json'
GAME_MIN, GAME_MAX = 1989, 2026

FIXES = [
    ('PIT', 'Def Co-ord', 'Woody Widenhofer', 1943,
     "Pittsburgh Steelers 1979 Media Guide, the team's own staff list: 'ROBERT (WOODY) "
     "WIDENHOFER Defensive Coordinator'. The slot previously held George Perles, whom the same "
     "book lists as Assistant Head Coach -- a role PGM3 does not model. Primary document over "
     "the Coaching Tree, which had the two men's jobs the other way round"),
    ('MIA', 'Special Teams', 'Carl Taseff', 1928,
     "Miami Dolphins 1979 Media Guide, the team's own staff list: 'Offensive Backs, Special "
     "Teams: Carl Taseff', born Sept. 28 1928. The slot previously held Steve Crosby, whom the "
     "SAME book lists as Assistant Director of Player Personnel -- a front-office job, not a "
     "coaching one. The Coaching Tree's 'Special Teams Assistant' label was wrong"),
]


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
    faces = json.load(open(repo(REG))).get('staff_faces', {})
    emp = [p for p in d if p['teamID'] != 'Free Agent']

    xs = [p['age'] for p in emp]; ys = [2026 - p['startSeason'] for p in emp]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)

    edits = {}
    for team, role, man, birth, how in FIXES:
        rec = [p for p in d if p['teamID'] == team and p['role'] == role]
        assert len(rec) == 1, f'{team} {role}: {len(rec)} records'
        rec = rec[0]
        clash = [p for p in d if p is not rec and norm(p['forename'] + ' ' + p['surname']) == norm(man)]
        assert not clash, f'{man} already in the file at ' + ', '.join(f"{p['teamID']}/{p['role']}" for p in clash)
        was, was_age, was_ss = f"{rec['forename']} {rec['surname']}", rec['age'], rec['startSeason']
        new_age = Y - birth
        assert 23 <= new_age <= 80, f'{man}: age {new_age} is not possible'
        rec['forename'], rec['surname'] = man.split(' ', 1)
        rec['age'] = new_age
        rec['startSeason'] = max(GAME_MIN, min(GAME_MAX,
                                 int(round(2026 - ((2026 - was_ss) + slope * (new_age - was_age))))))
        f = faces.get(norm(man))
        if isinstance(f, list) and len(f) == 9:
            rec['appearance'] = list(f)
        edits[(str(Y), rec['iden'])] = (man, 'real (name in a real source)', how)
        print(f'  {team} {role:<14} {was} ({was_age}) -> {man} ({new_age})'
              f'   startSeason {was_ss} -> {rec["startSeason"]}'
              f'   rating {rec["rating"]} and potential {rec["potential"]} unchanged')

    assert sum(1 for p in d if p['teamID'] != 'Free Agent') == 288, 'employed staff must stay 288'
    names = [(p['forename'], p['surname']) for p in d]
    assert not {x for x in names if names.count(x) > 1}, 'one man in two places'

    raw = open(repo(SIDECAR), newline='').read()
    term = '\r\n' if '\r\n' in raw else '\n'
    trailing = term if raw.endswith(term) else ''
    rows = raw.split(term)
    if trailing:
        rows = rows[:-1]
    out = [rows[0]]; hit = 0
    for line in rows[1:]:
        parts = next(csv.reader([line]))
        if (parts[0], parts[1]) in edits:
            name, provv, how = edits[(parts[0], parts[1])]
            parts[5], parts[6], parts[7] = name, provv, how
            b = io.StringIO(); csv.writer(b, lineterminator='').writerow(parts)
            out.append(b.getvalue()); hit += 1
        else:
            out.append(line)
    assert hit == len(edits)
    print(f'  {hit} sidecar rows rewritten')

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join(out) + trailing)
    print(f'  wrote {path} and the sidecar')


if __name__ == '__main__':
    main()
