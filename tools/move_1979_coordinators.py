#!/usr/bin/env python3
"""
move_1979_coordinators — three men out of the free-agent pool and into the jobs
they actually held. Ruled by Ryan 2026-09-04.

    python3 tools/move_1979_coordinators.py --dry-run
    python3 tools/move_1979_coordinators.py

Ken Meyer, Jim Ringo and Tom Bettis were 1979 offensive coordinators — Chicago,
New England and the Cardinals — and the 1979 build put all three in the
free-agent head-coach pool while inventing men for the slots they held. The fill
pass could not touch them: writing the name into the slot while the man sat in
the pool would have put one man in two places, which is the LeBeau defect.

A MAN IN HIS ACTUAL JOB BEATS A MAN IN A POOL PLUS AN INVENTED ONE IN THE SLOT.
So each man moves into his slot and his free-agent record is deleted. The pool
loses three men it should never have held; 1979's free-agent staff goes 219 to
216 and its head-coach pool 91 to 88. Nothing pins those counts — the archive
runs from 144 to 219 free agents across the ten files — while EMPLOYED staff is
exactly 288 in every file, 32 teams by 9 roles, and stays exactly 288 here.

WHAT MOVES AND WHAT STAYS, following the Duffner precedent. Name, age and face
come from the man's own record: his ages are already sourced from the coach pool
and correct (Ringo 48, Bettis 46 in 1979). Rating, potential, the growth curve
and startSeason stay with the SLOT — this changes who holds the job, not how
good the team's offence is, and inventing a coordinator rating for a man the
archive rates as a head coach would be a claim nothing supports.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 1979
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
MOVES = [('Ken Meyer', 'CHI'), ('Jim Ringo', 'NE'), ('Tom Bettis', 'ARI')]
SLOT = 'Off Co-ord'
HOW = ('Coaching Tree: titled Offensive Coordinator, 1979 {team}. Moved out of the '
       'free-agent head-coach pool, where the 1979 build had parked him while an '
       'invented man held the job he actually had; his free-agent record is gone')


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
    before_employed = sum(1 for p in d if p['teamID'] != 'Free Agent')

    drop = set(); edits = {}
    for full, team in MOVES:
        fn, ln = full.split(' ', 1)
        pool = [p for p in d if p['teamID'] == 'Free Agent' and p['forename'] == fn and p['surname'] == ln]
        slot = [p for p in d if p['teamID'] == team and p['role'] == SLOT]
        assert len(pool) == 1 and len(slot) == 1, f'{full}: expected one pool record and one slot, got {len(pool)}/{len(slot)}'
        src, dst = pool[0], slot[0]
        was = f"{dst['forename']} {dst['surname']}"
        dst['forename'], dst['surname'] = src['forename'], src['surname']
        dst['age'] = src['age']
        dst['appearance'] = list(src['appearance'])
        drop.add(src['iden'])
        edits[(str(Y), dst['iden'])] = (full, 'real (name in a real source)', HOW.format(team=team))
        print(f'  {team} {SLOT}: {was} -> {full} (age {src["age"]}); '
              f'rating {dst["rating"]} and potential {dst["potential"]} unchanged; free-agent record deleted')

    d = [p for p in d if p['iden'] not in drop]
    after_employed = sum(1 for p in d if p['teamID'] != 'Free Agent')
    assert before_employed == after_employed == 288, 'employed staff must stay at 288'
    names = [(p['forename'], p['surname']) for p in d]
    for full, _ in MOVES:
        fn, ln = full.split(' ', 1)
        assert names.count((fn, ln)) == 1, f'{full} appears {names.count((fn, ln))} times — one man, one record'
    print(f'  free agents {len([p for p in json.load(open(repo(path))) if p["teamID"] == "Free Agent"])} -> '
          f'{len([p for p in d if p["teamID"] == "Free Agent"])}; employed stays {after_employed}')

    raw = open(repo(SIDECAR), newline='').read()
    term = '\r\n' if '\r\n' in raw else '\n'
    trailing = term if raw.endswith(term) else ''
    rows = raw.split(term)
    if trailing:
        rows = rows[:-1]
    out = [rows[0]]; hit = 0; removed = 0
    for line in rows[1:]:
        parts = next(csv.reader([line]))
        if parts[0] == str(Y) and parts[1] in drop:
            removed += 1; continue
        if (parts[0], parts[1]) in edits:
            name, provv, how = edits[(parts[0], parts[1])]
            parts[5], parts[6], parts[7] = name, provv, how
            b = io.StringIO(); csv.writer(b, lineterminator='').writerow(parts)
            out.append(b.getvalue()); hit += 1
        else:
            out.append(line)
    print(f'  sidecar: {hit} rows rewritten, {removed} rows removed for the deleted free agents')
    assert hit == len(edits) and removed == len(drop), 'sidecar did not match the records'

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join(out) + trailing)
    print(f'  wrote {path} and the sidecar')


if __name__ == '__main__':
    main()
