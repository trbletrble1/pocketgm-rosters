#!/usr/bin/env python3
"""
fill_coordinators — coordinators from the Coaching Tree, 1979 and 2010.
Ruled by Ryan 2026-09-04.

    python3 tools/fill_coordinators.py --dry-run
    python3 tools/fill_coordinators.py

A CORRECTION TO MY OWN REPORT FIRST, because the ruling rested on it. I told
Ryan 2010 carried "36 invented coordinator records". It does not. My classifier
treated every provenance value that did not begin real/sourced/named as
invented, and 2010's 36 are all `unknown (no real source, not from the invented
lists)` -- a different thing. Against the source, **29 of the 36 are the right
man already**, 22 of them stored with an initial (`D. Toub` for Dave Toub).
2010 was never a hole; it was a set of unverified abbreviations. 1979's 65 are
genuinely `invented` and the report was right about those.

WHAT THIS PASS DOES.

  1979, 24 fills where the source names a man for the slot:
    * 14 TITLED   -- the source gives that exact title that year (George Perles,
      Buddy Ryan, Joe Gibbs, Ernie Stautner).
    * 10 INFERRED -- no 1979 team had a titled special teams coach, so the slot
      takes the man carrying "Special Teams Assistant" as a second role (Ditka
      at Dallas, Gansz at Cincinnati). Marked per record, not as a general note.

  1979, 12 records on franchises that did not exist -- Carolina, Jacksonville,
  and IND and TEN, which are the modern ids of two franchises the file already
  carries historically at BAL and HOU -- get their OWN provenance value.
  "Carolina had no 1979 staff because Carolina had no 1979" is a different fact
  from "we could not find one", and the sidecar now says which.

  1979, 3 slots NOT filled because the real man is already in the file, parked
  as a free-agent head coach: Ken Meyer (Chicago), Jim Ringo (New England) and
  Tom Bettis (the Cardinals). Filling would put one man in two places, which is
  precisely the LeBeau defect closed yesterday. Reported, not written.

  2010, all 36: 7 confirmed as already correct, 23 expanded from an initial to
  the man's full name, 3 corrected to a different man, 2 marked as the seniority
  fallback, 1 (Houston) left alone and marked absent from the source.

  Mark Duffner's 2010 Jacksonville record moves from Off Scout to Def Scout: the
  source has him as their LINEBACKERS coach, a defensive job, and our file had
  him on the offensive side. The two scout records swap identity so both slots
  stay filled and no one is invented.

WHAT THIS PASS DELIBERATELY DOES NOT DO: the 23 remaining 1979 fallbacks, where
no titled coordinator existed and the slot must take the senior assistant on
that side. The rule is approved but it misfires on at least one team -- applied
mechanically it makes Ken Iman Philadelphia's offensive coordinator while SID
GILLMAN is sitting on the same staff under "Quality Control" -- so the picks go
to Ryan as a list rather than into the file. Three more (Atlanta, Minnesota and
Pittsburgh's special teams) have no candidate at all: those staffs carry nobody
in a special teams role, so there is nothing to infer and they stay generated.

AGES ARE NOT TOUCHED. Ruled a separate pass, to be scored against a known
reference first. A real man therefore sits on the slot's existing age until then,
and the sidecar says the age is not sourced.
"""
import json, os, re, sys, csv, io, subprocess, unicodedata, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

PULL = 'wip/coaching_tree_1979_2010.csv'
SIDECAR = 'reference/PGM3_STAFF_PROVENANCE.csv'
REG = 'reference/PGM3_FACE_REGISTRY.json'
YEARS = (1979, 2010)
PROV = {}

# 2010 records where our man is simply wrong, from the pull
CORRECT_2010 = {('PIT', 'Special Teams'): 'Al Everest',
                ('SF', 'Special Teams'): 'Kurt Schottenheimer',
                ('TB', 'Special Teams'): 'Rich Bisaccia'}
# 2010 slots the source shows had no titled coordinator; our man is already the
# senior assistant on that side, so only the provenance changes
FALLBACK_2010 = {('DAL', 'Def Co-ord'): 'Wade Phillips called the defence himself; our record already '
                                        'holds Paul Pasqualoni, his defensive line coach and senior '
                                        'defensive assistant',
                 ('NE', 'Def Co-ord'): "Belichick ran 2010 without a titled defensive coordinator; our "
                                       "record holds Chad O'Shea, who coached the WIDE RECEIVERS -- the "
                                       "wrong side of the ball, left for the fallback pass"}
ABSENT_2010 = {('HOU', 'Special Teams'): 'Houston is absent from the Coaching Tree at every year tried'}
# THE 1979 FILE USES HISTORICAL TEAM IDS, WHICH I HAD BACKWARDS. Its Baltimore
# Colts sit at BAL and its Houston Oilers at HOU -- both already carrying the
# real Maxie Baughan, George Boutselis, Ed Biles and John Paul Young, marked
# `sourced`. So the IDs with no 1979 team behind them are IND and TEN, the
# MODERN ids of those same two franchises, plus Carolina and Jacksonville.
# Relabelling BAL and HOU would have overwritten four real sourced coordinators
# with "this franchise did not exist" -- the exact opposite of the truth.
NO_FRANCHISE = {'CAR', 'JAX', 'IND', 'TEN'}


def norm(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    x = re.sub(r'[^a-z ]', '', x)
    return ' '.join(w for w in x.split() if w not in {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}).strip()


def split_name(full):
    parts = full.strip().split()
    return parts[0], ' '.join(parts[1:])


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
    pull = collections.defaultdict(dict)
    for r in csv.DictReader(open(repo(PULL))):
        pull[int(r['year'])][(r['team'], r['slot'])] = r
    global PROV
    PROV = {(r['file'], r['iden']): r for r in csv.DictReader(open(repo(SIDECAR)))}
    reg = json.load(open(repo(REG)))
    staff_faces = reg.get('staff_faces', {})

    sidecar_edits = {}
    counts = collections.Counter()
    files = {}

    for y in YEARS:
        path = f'PGMStaff_{y}.json'
        ser = serialiser(path)
        d = json.load(open(repo(path)))
        files[y] = (path, ser, d)
        present = collections.Counter(norm(p['forename'] + ' ' + p['surname']) for p in d)

        for p in d:
            if p['teamID'] == 'Free Agent' or p['role'] not in ('Off Co-ord', 'Def Co-ord', 'Special Teams'):
                continue
            key = (p['teamID'], p['role'])
            row = pull[y].get(key)
            ours = f"{p['forename']} {p['surname']}"
            edit = None

            pv = PROV.get((str(y), p['iden']), {}).get('provenance', '')
            if y == 1979 and p['teamID'] in NO_FRANCHISE and pv.startswith('invented'):
                edit = ('generated (franchise did not exist that season)',
                        f'{p["teamID"]} did not field a team in 1979; the slot is a generated man on a '
                        f'franchise the season never had, not a coordinator we failed to find')
                counts['1979 no-franchise'] += 1

            elif y == 1979 and p['teamID'] in NO_FRANCHISE:
                counts['1979 non-existent franchise, already sourced — left alone'] += 1
                continue

            elif y == 1979 and row and row['fill'] in ('titled', 'inferred'):
                fn, ln = split_name(row['name'])
                if present[norm(row['name'])] and norm(row['name']) != norm(ours):
                    # THE REAL MAN IS ALREADY IN THE FILE, parked as a free-agent
                    # head coach: Ken Meyer, Jim Ringo, Tom Bettis. Filling the
                    # slot would put one man in two places, which is the LeBeau
                    # defect. Left alone and reported instead.
                    counts['1979 real man already in the file as a free agent'] += 1
                    continue
                how = (f'Coaching Tree: titled {row["source_title"]}, {y} {p["teamID"]}'
                       if row['fill'] == 'titled' else
                       f'Coaching Tree: NO titled special teams coach on the {y} {p["teamID"]} staff; '
                       f'{row["name"]} carried "{row["source_title"]}" as a second role — INFERRED, '
                       f'not a titled coordinator')
                p['forename'], p['surname'] = fn, ln
                face = staff_faces.get(norm(row['name']))
                if isinstance(face, list) and len(face) == 9:
                    p['appearance'] = list(face)
                edit = ('real (name in a real source)', how + '; age not sourced, slot age retained')
                counts[f'1979 {row["fill"]}'] += 1

            elif y == 2010 and key in ABSENT_2010:
                edit = ('unknown (no real source, not from the invented lists)', ABSENT_2010[key])
                counts['2010 absent from source'] += 1

            elif y == 2010 and key in FALLBACK_2010:
                edit = ('unknown (no real source, not from the invented lists)',
                        'Coaching Tree: ' + FALLBACK_2010[key])
                counts['2010 fallback, marked'] += 1

            elif y == 2010 and key in CORRECT_2010:
                fn, ln = split_name(CORRECT_2010[key])
                if present[norm(CORRECT_2010[key])] and norm(CORRECT_2010[key]) != norm(ours):
                    counts['skipped, name already in file'] += 1
                    continue
                p['forename'], p['surname'] = fn, ln
                face = staff_faces.get(norm(CORRECT_2010[key]))
                if isinstance(face, list) and len(face) == 9:
                    p['appearance'] = list(face)
                edit = ('real (name in a real source)',
                        f'Coaching Tree: {y} {p["teamID"]} {row["source_title"]} was {CORRECT_2010[key]}; '
                        f'our record held {ours}, who held that job in an earlier season')
                counts['2010 corrected to a different man'] += 1

            elif y == 2010 and row and row['name']:
                same_surname = norm(ours).split()[-1:] == norm(row['name']).split()[-1:]
                if not same_surname:
                    counts['2010 unmatched, left alone'] += 1
                    continue
                fn, ln = split_name(row['name'])
                was_initial = ours != row['name']
                p['forename'], p['surname'] = fn, ln
                edit = ('real (name in a real source)',
                        f'Coaching Tree: {"titled " + row["source_title"] if row["fill"] == "titled" else row["source_title"] + " (INFERRED, no titled special teams coach)"}, '
                        f'{y} {p["teamID"]}' + ('; first name expanded from an initial' if was_initial else '; confirmed unchanged'))
                counts['2010 expanded from an initial' if was_initial else '2010 confirmed'] += 1

            if edit:
                sidecar_edits[(str(y), p['iden'])] = (f"{p['forename']} {p['surname']}",) + edit

    # ---- Duffner: a defensive coach on the offensive side ------------------
    path, ser, d = files[2010]
    jax = {p['role']: p for p in d if p['teamID'] == 'JAX' and p['role'] in ('Off Scout', 'Def Scout')}
    if len(jax) == 2 and jax['Off Scout']['surname'] == 'Duffner':
        a, b = jax['Off Scout'], jax['Def Scout']
        for k in ('forename', 'surname', 'age', 'startSeason', 'appearance'):
            a[k], b[k] = b[k], a[k]
        counts['Duffner moved to the defensive side'] += 1
        for rec, who in ((b, 'Mark Duffner'), (a, f"{a['forename']} {a['surname']}")):
            sidecar_edits[('2010', rec['iden'])] = (
                who,
                'real (name in a real source)' if who == 'Mark Duffner' else 'invented (scout/physio, the standing exception)',
                'Coaching Tree: Duffner coached Jacksonville\'s LINEBACKERS in 2010, a defensive job; '
                'our file had him as an offensive scout. The two scout records swap so both stay filled'
                if who == 'Mark Duffner' else
                'displaced to the offensive scout slot when Duffner moved to the defensive side')

    print('what this pass changes:')
    for k, v in sorted(counts.items()):
        print(f'   {v:>3}  {k}')

    # ---- sidecar ----------------------------------------------------------
    raw = open(repo(SIDECAR), newline='').read()
    term = '\r\n' if '\r\n' in raw else '\n'
    trailing = term if raw.endswith(term) else ''
    rows = raw.split(term)
    if trailing:
        rows = rows[:-1]
    out = [rows[0]]
    hit = 0
    for line in rows[1:]:
        parts = next(csv.reader([line]))
        k = (parts[0], parts[1])
        if k in sidecar_edits:
            name, provv, how = sidecar_edits[k]
            parts[5], parts[6], parts[7] = name, provv, how
            b = io.StringIO(); csv.writer(b, lineterminator='').writerow(parts)
            out.append(b.getvalue()); hit += 1
        else:
            out.append(line)
    print(f'   {hit} sidecar rows rewritten of {len(sidecar_edits)} edits')
    assert hit == len(sidecar_edits), 'a record has no sidecar row'

    if dry:
        print('  DRY RUN — nothing written'); return
    for y in YEARS:
        path, ser, d = files[y]
        open(repo(path), 'w').write(ser(d))
    with open(repo(SIDECAR), 'w', newline='') as fh:
        fh.write(term.join(out) + trailing)
    print('  wrote both staff files and the sidecar')


if __name__ == '__main__':
    main()
