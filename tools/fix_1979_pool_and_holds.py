#!/usr/bin/env python3
"""
fix_1979_pool_and_holds — the three rulings of 2026-09-04.

    python3 tools/fix_1979_pool_and_holds.py --dry-run
    python3 tools/fix_1979_pool_and_holds.py

1. THE EIGHT COME OUT OF THE POOL. Ruled: a pool that misrepresents eight of
   eighty-five men as available is worse than a pool of seventy-seven that is
   true. The point of the free-agent pool is that the user can hire from it, and
   a man who was coaching Tampa Bay's defensive backs that season is not
   available — a sidecar note does not reach the user.

   WHAT IS LOST, and it is a limitation rather than a defect. These eight are
   real men who genuinely coached in 1979 and now appear nowhere in the file:
   Abe Gibron, Bill Johnson, Charley Winner, Dick Modzelewski, Fred O'Connor,
   Jack Faulkner, Norb Hecker and Pete McCulley. Every one was a position coach
   — defensive backs, defensive line, running backs, wide receivers — and
   **PGM3 models nine staff roles, none of which is a position coach.** There is
   nowhere in the format to put them. The nine before them held coordinator jobs
   and so had slots to move into; these do not.

2. MIAMI TAKES THE NEXT CANDIDATE. Bill Arnsparger stays at Carolina by Ryan's
   ruling — placed on a franchise that did not exist in 1979 because Charlotte's
   doctrine needed a man whose record was worse than he was, and that story is
   why the franchise reads as it does. The sidecar now records that his real 1979
   job was Miami and that he sits on an invented franchise BY RULING, so the
   trade is visible rather than looking like an error.

   Miami's defensive slot goes to TOM KEANE on the amended rule: 22 years by
   1979 against Mike Scarry's 13, even though Scarry carried the more senior-
   sounding title of Defensive Run Game Coordinator. The same shape as Gillman
   over Iman.

3. THE SCHOTTENHEIMER YEAR IS SETTLED, and our file was wrong. Checked
   independently of the Coaching Tree: **Marty Schottenheimer coached Detroit's
   linebackers in 1978 and 1979 and became Cleveland's defensive coordinator in
   1980.** Our 1979 file had him as Cleveland's coordinator a year early, marked
   `sourced`. So Detroit's slot takes him, and CLEVELAND'S SLOT — which the file
   had wrong and which the Coaching Tree shows had no titled coordinator at all
   — becomes a fallback and goes to CHUCK WEBER, 15 years by 1979 and already
   Cincinnati's coordinator in 1973-75, over Dick MacPherson's 12.

Ages are still untouched: ruled a separate pass, scored first.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

Y = 1979
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
REG = 'reference/PGM3_FACE_REGISTRY.json'

DROP_FROM_POOL = ['Abe Gibron', 'Bill Johnson', 'Charley Winner', 'Dick Modzelewski',
                  'Fred O\'Connor', 'Jack Faulkner', 'Norb Hecker', 'Pete McCulley']
WHERE_THEY_WERE = {'Abe Gibron': 'Tampa Bay, assistant head coach',
                   'Bill Johnson': 'Tampa Bay, defensive line',
                   'Charley Winner': 'Cincinnati, defensive backs',
                   'Dick Modzelewski': 'Cincinnati, defensive line',
                   "Fred O'Connor": 'Washington, running backs',
                   'Jack Faulkner': 'the Rams, offensive assistant',
                   'Norb Hecker': 'San Francisco, defensive backs',
                   'Pete McCulley': 'the Jets, wide receivers'}

FILLS = [
    ('DET', 'Def Co-ord', 'Marty Schottenheimer',
     'Coaching Tree, confirmed independently: Schottenheimer coached Detroit\'s linebackers in 1978 '
     'and 1979 and did not reach Cleveland until 1980. Our file had him as Cleveland\'s coordinator a '
     'year early. The 1979 Detroit staff carried no titled defensive coordinator, so the slot takes '
     'the senior assistant on that side by career standing. INFERRED; age not sourced'),
    ('CLE', 'Def Co-ord', 'Chuck Weber',
     'Coaching Tree: the 1979 Cleveland staff carried NO titled defensive coordinator — the man this '
     'file had in the slot, Marty Schottenheimer, did not arrive until 1980 — so it takes the senior '
     'assistant on that side by career standing: Weber had 15 years by 1979 and had already been '
     'Cincinnati\'s coordinator in 1973-75, against Dick MacPherson\'s 12. INFERRED; age not sourced'),
    ('MIA', 'Def Co-ord', 'Tom Keane',
     'Coaching Tree: the 1979 Miami staff carried no titled defensive coordinator, and Bill '
     'Arnsparger — who held the job in substance — is placed at Carolina by Ryan\'s ruling. The slot '
     'takes the next man by career standing: Keane had 22 years by 1979 against Mike Scarry\'s 13, '
     'though Scarry carried the more senior-sounding Defensive Run Game Coordinator title. '
     'INFERRED; age not sourced'),
]
ARNSPARGER_NOTE = ('Placed at Carolina BY RYAN\'S RULING on a franchise that did not exist in 1979: '
                   'Charlotte\'s doctrine needed a man whose record was worse than he was, and that '
                   'story is why the franchise reads as it does. His real 1979 job was assistant head '
                   'coach and defensive architect at MIAMI, whose coordinator slot went to Tom Keane. '
                   'The trade is deliberate, not an error')


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
    faces = reg.get('staff_faces', {})
    edits = {}; drop = set()

    # ---- 1. the eight leave the pool ------------------------------------
    print('the eight, out of the free-agent pool:')
    for man in DROP_FROM_POOL:
        recs = [p for p in d if p['teamID'] == 'Free Agent'
                and norm(p['forename'] + ' ' + p['surname']) == norm(man)]
        assert len(recs) == 1, f'{man}: expected one pool record, found {len(recs)}'
        drop.add(recs[0]['iden'])
        print(f'   {man:<18} was {WHERE_THEY_WERE[man]}')

    # ---- 2 & 3. the three slots -----------------------------------------
    print('\nthe three held slots, now filled:')
    for team, slot, man, how in FILLS:
        rec = [p for p in d if p['teamID'] == team and p['role'] == slot]
        assert len(rec) == 1
        rec = rec[0]
        was = f"{rec['forename']} {rec['surname']}"
        fn, ln = man.split(' ', 1)
        rec['forename'], rec['surname'] = fn, ln
        f = faces.get(norm(man))
        if isinstance(f, list) and len(f) == 9:
            rec['appearance'] = list(f)
        edits[(str(Y), rec['iden'])] = (man, 'real (name in a real source)', how)
        print(f'   {team} {slot:<12} {was:<22} -> {man}')

    # Arnsparger's row gains the ruling, his record is untouched
    arn = [p for p in d if norm(p['forename'] + ' ' + p['surname']) == norm('Bill Arnsparger')]
    assert len(arn) == 1 and arn[0]['teamID'] == 'CAR', 'Arnsparger is not where the ruling says'
    edits[(str(Y), arn[0]['iden'])] = ('Bill Arnsparger', 'named by Ryan', ARNSPARGER_NOTE)
    print(f'   CAR Head Coach   Bill Arnsparger — record unchanged, sidecar records the ruling')

    d = [p for p in d if p['iden'] not in drop]
    assert sum(1 for p in d if p['teamID'] != 'Free Agent') == 288, 'employed staff must stay 288'
    names = [(p['forename'], p['surname']) for p in d]
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f'one man in two places: {dupes}'
    pool = sum(1 for p in d if p['teamID'] == 'Free Agent' and p['role'] == 'Head Coach')
    print(f'\n  free-agent head coaches {pool + len(drop)} -> {pool}; employed stays 288')

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
    assert hit == len(edits) and removed == len(drop), f'sidecar {hit}/{len(edits)}, {removed}/{len(drop)}'
    print(f'  sidecar: {hit} rows rewritten, {removed} removed')

    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join(out) + trailing)
    print(f'  wrote {path} and the sidecar — now run tools/reconcile_faces.py --staff')


if __name__ == '__main__':
    main()
