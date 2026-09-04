#!/usr/bin/env python3
"""
fix_2000_lebeau — backlog 67. Ruled by Ryan 2026-09-03.

    python3 tools/fix_2000_lebeau.py --dry-run
    python3 tools/fix_2000_lebeau.py

THE DEFECT. 2000 carried Dick LeBeau twice on Cincinnati, aged 63 on both, as
head coach and as defensive coordinator. Historically exact — he took over from
Bruce Coslet during the 2000 season and kept calling the defence himself — and
still one man occupying two slots on one team.

THE RULING. LeBeau holds the head-coach slot; the coordinator slot goes to a
real man. The reasoning is asymmetric risk rather than certainty: three
independently generated vanilla staff exports carry ZERO duplicate names across
1,296 records, so one-record-per-person is the engine's own convention, and if a
doubled man breaks a depth chart or a hire it is a gameplay failure a user meets
blind, while splitting him costs a piece of trivia that was never visible in the
interface. No same-man exemption was added to the duplicate check: a check with
two kinds of exemption is one nobody trusts.

THE REAL MAN. Researched rather than invented. The 2000 Bengals defensive staff
was Tim Krumrie (line), MARK DUFFNER (linebackers), Ray Horton (defensive backs)
and Louie Cioffi (defensive staff assistant); no separate coordinator is named
after LeBeau's promotion because there was not one. Duffner is the senior
defensive assistant of the four — a former head coach at Maryland — so the
file's `Def Co-ord` slot goes to him, and the mapping is stated in the
provenance sidecar rather than implied.

He is already in the archive as a 2010 Jacksonville scout and already carries a
registry face, so this pass takes that face rather than inventing one, and he
comes out looking the same in both files.

WHAT IS AND IS NOT CHANGED. Name, age, startSeason and appearance. The rating,
potential, growth curve and every attribute stay exactly as they were: this
changes who occupies the slot, not how good Cincinnati's defence is, and the
archive's staff ratings are assigned by convention rather than sourced per man.
Inventing a rating for Duffner would be a claim nothing supports.
"""
import json, os, re, sys, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 2000
OLD = ('Dick', 'LeBeau')
NEW = ('Mark', 'Duffner')
NEW_AGE = 47          # born 1953
NEW_START = 1997      # joined Cincinnati in 1997
ROLE, TEAM = 'Def Co-ord', 'CIN'
REG = 'reference/PGM3_FACE_REGISTRY.json'
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
HOW = ("Cincinnati's 2000 linebackers coach and the senior defensive assistant; "
       "the real team had no separate defensive coordinator after LeBeau's "
       "promotion, so he is mapped to the Def Co-ord slot")


def norm(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    x = re.sub(r'[^a-z ]', '', x)
    return ' '.join(w for w in x.split() if w not in {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}).strip()


def main():
    dry = '--dry-run' in sys.argv
    path = f'PGMStaff_{Y}.json'
    head = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True, text=True, cwd=repo('')).stdout
    ser = None
    for f in (lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, separators=(', ', ': ')),
              lambda d: json.dumps(d, separators=(',', ':'))):
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head:
                ser = (lambda ff, nn: (lambda x: ff(x) + nn))(f, nl); break
        if ser: break
    assert ser, f'{path}: stored formatting not reproduced'

    reg = json.load(open(repo(REG)))
    face = reg.get('staff_faces', {}).get(norm(' '.join(NEW)))
    assert isinstance(face, list) and len(face) == 9, 'no registry face for the replacement'

    d = json.load(open(repo(path)))
    hits = [p for p in d if (p['forename'], p['surname']) == OLD]
    assert len(hits) == 2, f'expected two {OLD[1]} records, found {len(hits)}'
    tgt = [p for p in hits if p['role'] == ROLE and p['teamID'] == TEAM]
    keep = [p for p in hits if p is not tgt[0]] if tgt else []
    assert len(tgt) == 1 and keep and keep[0]['role'] == 'Head Coach', 'the two records are not the expected pair'
    tgt = tgt[0]

    # nobody else on this team or in this file already carries the new name
    assert not any(norm(p['forename']) + ' ' + norm(p['surname']) == norm(' '.join(NEW)) for p in d), \
        'the replacement name already exists in this file — namesake check before applying by name'

    before = {k: tgt[k] for k in ('forename', 'surname', 'age', 'startSeason', 'rating', 'potential')}
    tgt['forename'], tgt['surname'] = NEW
    tgt['age'], tgt['startSeason'] = NEW_AGE, NEW_START
    tgt['appearance'] = list(face)

    print(f'{Y} {TEAM} {ROLE}: {before["forename"]} {before["surname"]} (age {before["age"]}, '
          f'startSeason {before["startSeason"]}) -> {NEW[0]} {NEW[1]} (age {NEW_AGE}, startSeason {NEW_START})')
    print(f'  rating {before["rating"]} and potential {before["potential"]} unchanged; face taken from the registry')
    print(f'  {OLD[0]} {OLD[1]} keeps the Head Coach slot, age {keep[0]["age"]}')

    # sidecar: the provenance records the ORIGIN, so the row is rewritten in place.
    # THE FILE IS CRLF and its line terminator is detected rather than assumed --
    # rewriting 4,421 rows to LF would be a formatting change dressed as a data
    # change, and the diff would stop being a check.
    raw = open(repo(SIDECAR), newline='').read()
    term = '\r\n' if '\r\n' in raw else '\n'
    trailing = term if raw.endswith(term) else ''
    rows = raw.split(term)
    if trailing: rows = rows[:-1]
    hdr = rows[0]
    out = []
    done = 0
    for line in rows[1:]:
        if line.startswith(f'{Y},{tgt["iden"]},'):
            parts = next(__import__('csv').reader([line]))
            parts[5] = f'{NEW[0]} {NEW[1]}'
            parts[6] = 'real (name in a real source)'
            parts[7] = HOW
            import io, csv as _csv
            b = io.StringIO(); _csv.writer(b, lineterminator='').writerow(parts)
            out.append(b.getvalue()); done += 1
        else:
            out.append(line)
    assert done == 1, f'sidecar row not found for iden {tgt["iden"]}'
    print(f'  sidecar row rewritten: name_after -> {NEW[0]} {NEW[1]}, how -> the real-staff mapping')

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join([hdr] + out) + trailing)
    print(f'  wrote {path} and the sidecar')


if __name__ == '__main__':
    main()
