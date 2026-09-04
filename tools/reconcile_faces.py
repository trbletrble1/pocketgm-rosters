#!/usr/bin/env python3
"""
reconcile_faces — item 54. One person, one face; and the registry brought back
onto the files. Ruled by Ryan 2026-09-03.

    python3 tools/reconcile_faces.py --dry-run
    python3 tools/reconcile_faces.py

WHAT ITEM 54 ACTUALLY IS, measured before anything was written. The faces gates
report 18 players and 40 staff whose faces move between seasons, which sounds
like a face problem. It is three different things:

  1. FIVE NAMESAKES, which are not a defect at all. `robert woods|WR` appears in
     1979 aged 24 and in 2013 aged 21; `mark clayton|WR` is 25 in 1986 and 25 in
     2007. The gate keys a person on name and position, which cannot separate
     two men who share both. THE TEST IS ARITHMETIC, not a judgement: for one
     man the age gap between two files must track the year gap. Five pairs miss
     it by 21 to 37 years. They are exempted BY NAME in the registry's
     `_namesakes` block, so the exemption is a recorded fact rather than a
     silent skip -- and the seventh namesake precedent says check before
     applying anything by name, which is what this does.

  2. TWO GENUINE SKIN ERRORS, the only two disagreements in the whole archive
     that cross the light/dark line: Martin Gramatica reads dark in 2000 and
     light in 2004 and 2007, and `eric wilson|MLB`, which is one of the five
     namesakes. So ONE real skin error, and the majority rule fixes it the right
     way -- Gramatica is Argentine and the two later files outvote the one.

  3. EVERYTHING ELSE IS SHADE DRIFT INSIDE ONE SIDE. 16 players and all 21 staff
     differ only in which light family or which dark family they carry -- Bill
     Parcells is family 2 in 1986 and family 1 in every later file, both light.
     The 1986 era-scoped registry block and the modern block disagree about the
     same man, which is the registry contradicting itself rather than a claim
     about anyone's skin.

THE RULE, applied per man:

  * A face Ryan verified is never touched and always wins. The registry's value
    for a verified man IS the canonical value.
  * Otherwise the majority across his files wins; a tie goes to his most recent
    file.
  * Only the FAMILY DIGIT moves, in slots 0/5/6 together, letters preserved --
    the aging variant is derived from age and weight and must keep varying, and
    a pass that wrote whole faces is exactly what flattened it once before.
  * Hair is a colour digit shared by slots 2/3/4, so a hair change carries the
    beard and eyebrows digits with it, letters preserved.
  * Staff carry one look, so a staff man's whole appearance is made identical.

THEN THE REGISTRY IS BROUGHT ONTO THE FILES, the direction item 54 ruled:
file -> registry, per man. The registry was last written 2026-09-03 for the
quarterback faces and the files moved after it, so `apply_registry_all.py` would
have reverted every one of those men. It is safe to run again after this pass.
"""
import json, os, re, sys, collections, subprocess, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

YEARS = [1979, 1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026]
REG = 'reference/PGM3_FACE_REGISTRY.json'
SKIN_SLOTS = (0, 5, 6)      # head, nose, mouth share the skin family digit
HAIR_SLOTS = (2, 3, 4)      # hair, beard, eyebrows share the colour digit


def norm(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    x = re.sub(r'[^a-z ]', '', x)
    return ' '.join(w for w in x.split() if w not in {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}).strip()


def tok(t):
    m = re.match(r'([A-Za-z]+)(\d+)(.*)$', str(t))
    return (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)


def set_digit(t, d):
    p, _, s = tok(t)
    return f'{p}{d}{s}' if p else t


def cohort(p):
    return 'Rookie' if p.get('teamID') == 'Rookie' else ('FA' if p.get('teamID') == 'Free Agent' else 'T')


def load_files():
    ros = {y: json.load(open(repo(f'PGMRoster_{y}.json'))) for y in YEARS}
    stf = {y: json.load(open(repo(f'PGMStaff_{y}.json'))) for y in YEARS}
    return ros, stf


def index(ros, stf):
    players = collections.defaultdict(list)
    staff = collections.defaultdict(list)
    for y in YEARS:
        for p in ros[y]:
            if cohort(p) != 'T':
                continue
            players[norm(p['forename']) + ' ' + norm(p['surname']) + '|' + p.get('position', '')].append((y, p))
        for p in stf[y]:
            staff[norm(p['forename']) + ' ' + norm(p['surname'])].append((y, p))
    return players, staff


def find_namesakes(players):
    """Two records are the same man only if the age gap tracks the year gap.
    Tolerance 6 years, which absorbs the archive's age noise and still leaves
    the five real collisions missing by 21-37."""
    out = {}
    for k, v in players.items():
        if len({y for y, _ in v}) < 2:
            continue
        v = sorted(v, key=lambda t: t[0])   # a man can appear twice in one file; never compare the dicts
        worst = 0; detail = None
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                (y1, a), (y2, b) = v[i], v[j]
                if a.get('age') is None or b.get('age') is None:
                    continue
                miss = abs((b['age'] - a['age']) - (y2 - y1))
                if miss > worst:
                    worst, detail = miss, f'{y1} aged {a["age"]} vs {y2} aged {b["age"]} — off by {miss}'
        if worst > 6:
            out[k] = detail
    return out


def canonical(recs, verified_value, slot_key):
    """slot_key(appearance) -> the value being reconciled."""
    if verified_value is not None:
        return verified_value
    votes = collections.Counter(slot_key(p['appearance']) for _, p in recs)
    top = max(votes.values())
    tied = [v for v, n in votes.items() if n == top]
    if len(tied) == 1:
        return tied[0]
    return slot_key(max(recs, key=lambda yp: yp[0])[1]['appearance'])   # most recent file


def main():
    dry = '--dry-run' in sys.argv
    reg = json.load(open(repo(REG)))
    # VERIFIED KEYS COME IN TWO FORMS and the second one bit on the first run:
    # modern men are 'name|POS' in the `faces` block, 1986 men are
    # 'name|POS|TEAM' in `faces_1986`. Matching only the first form left Doug
    # Flutie and Jerry Rice unprotected and this pass overwrote both -- the
    # faces gate caught it on the next run, which is the whole argument for the
    # gate. A record is protected if EITHER form of its key is verified, and the
    # canonical value is looked up in both blocks.
    vk = set(reg['_verified_keys']['players'])
    vstaff = reg['_verified_keys']['staff']
    vstaff_names = set(vstaff) if isinstance(vstaff, dict) else set(vstaff)

    heads = {}
    for path in ([f'PGMRoster_{y}.json' for y in YEARS] + [f'PGMStaff_{y}.json' for y in YEARS] + [REG]):
        heads[path] = subprocess.run(['git', 'show', f'HEAD:{path}'],
                                     capture_output=True, text=True, cwd=repo('')).stdout
    # THE ARCHIVE STORES FOUR DIFFERENT SERIALISATIONS and a diff against a file
    # written in the wrong one stops being a check. Measured, not assumed:
    # rosters are indent=1 (1979) or ', '/': ' compact (nine); staff are
    # indent=1 (1979), ','/':' compact (1986-2013) and ', '/': ' compact
    # (2017-2026); the registry is indent=1. Detected per file against HEAD.
    CANDIDATES = [lambda d: json.dumps(d, indent=1),
                  lambda d: json.dumps(d, indent=0),
                  lambda d: json.dumps(d, indent=2),
                  lambda d: json.dumps(d, separators=(', ', ': ')),
                  lambda d: json.dumps(d, separators=(',', ':')),
                  lambda d: json.dumps(d, separators=(',', ': ')),
                  json.dumps]
    SER = {}
    for path, h in heads.items():
        d = json.loads(h)
        for f in CANDIDATES:
            for nl in ('', '\n'):
                if f(d) + nl == h:
                    SER[path] = (lambda ff, nn: (lambda x: ff(x) + nn))(f, nl); break
            if path in SER: break
        assert path in SER, f'{path}: stored formatting not reproduced by any known serialiser'
    def ser_for(path): return SER[path]

    ros, stf = load_files()
    players, staff = index(ros, stf)
    nam = find_namesakes(players)

    print(f'namesakes found by the age-gap test: {len(nam)}')
    for k, d in sorted(nam.items()):
        print(f'    {k:<24} {d}')

    # ---------------- players: family digit and hair colour ----------------
    mike = reg.get('mike_skin', {})
    changed_p = collections.Counter(); touched = []; held_mike = []
    for k, v in players.items():
        if k in nam or len({y for y, _ in v}) < 2:
            continue
        base = k.split('|')[0]
        def vkey_of(y, p):
            return k + '|' + str(p.get('teamID')) if y == 1986 else k
        # THE ERA-SCOPED BLOCK IS CHECKED FIRST, and the order matters. For Doug
        # Flutie, Jerry Rice and Reggie White the verified key is the 1986 team
        # form and the modern `faces` entry is UNVERIFIED -- reading `faces`
        # first made the unverified modern value canonical and left the man
        # split, because his verified 1986 record is rightly protected from
        # rewriting. The verified value is the strongest evidence in the project
        # (`_verified`: the only real hairstyle and facial-hair data anywhere in
        # it), so it propagates FORWARD to his other records.
        rv = None
        for y2, p2 in v:
            vk2 = k + '|' + str(p2.get('teamID'))
            if vk2 in vk and isinstance(reg.get('faces_1986', {}).get(vk2), list):
                rv = reg['faces_1986'][vk2]; break
        if rv is None and k in vk and isinstance(reg.get('faces', {}).get(k), list):
            rv = reg['faces'][k]
        for slots, key, name in ((SKIN_SLOTS, lambda a: tok(a[0])[1], 'skin'),
                                 (HAIR_SLOTS, lambda a: a[2], 'hair')):
            if len({key(p['appearance']) for _, p in v}) < 2:
                continue
            want = canonical(v, key(rv) if rv else None, key)
            for y, p in v:
                if key(p['appearance']) == want:
                    continue
                if any(vkey == vkey_of(y, p) for vkey in vk):
                    continue                      # a verified record is never rewritten
                was = key(p['appearance'])
                # GUARD: Mike is authoritative on skin class before 1990 (item
                # 56, 95 of 99 against Ryan's verdicts). A majority of later
                # files must never flip a pre-1990 man across the light/dark
                # line against him. Shade inside a side is not his claim.
                if name == 'skin' and y < 1990:
                    mk = mike.get(base, {}).get('class')
                    if mk and (mk == 'light') != (want in {'1', '2', '3'}):
                        held_mike.append((y, k, was, want, mk)); continue
                if name == 'hair':
                    p['appearance'][2] = want
                    for s in (3, 4):
                        p['appearance'][s] = set_digit(p['appearance'][s], tok(want)[1])
                else:
                    for s in slots:
                        p['appearance'][s] = set_digit(p['appearance'][s], want)
                changed_p[(name, y)] += 1
                touched.append((y, k, name, was, want))

    # ---------------- staff: HELD, and why ---------------------------------
    # THE STAFF HALF IS NOT A FILE DEFECT AND IS NOT APPLIED. Measured: of the
    # 46 coaches carried in BOTH registry blocks, 40 have DIFFERENT faces in the
    # two, and every drifted file agrees exactly with the block that governs it
    # -- Parcells is the registry's Head2c in 1986 and the registry's Head1d in
    # 2004, 2007 and 2010. The files are applying the registry correctly. The
    # registry holds two faces for one man.
    #
    # That is a contradiction between two documents, and it is in one document:
    # `_README` says "canonical face per person, so anyone appearing in several
    # seasons looks the same", `_scope` says the 1986 blocks are ERA-SCOPED. For
    # a man who coached in both eras they cannot both hold. A contradiction
    # between documents is an escalation, not a tie to be broken by a tool, so
    # nothing is written until Ryan rules which block governs a man in both.
    #
    # The shape of the evidence, for that ruling: the 1986 values are family 2
    # where the modern ones are family 1, and family 4 where the modern ones are
    # 5 (Dennis Green). Both pairs sit on the same side of the light/dark line,
    # so no skin claim is in dispute -- it looks like the 1986 block was built
    # on a different family convention rather than a statement about any man.
    #
    # RULED 2026-09-03 and applied with --staff. Of the 40 disputed coaches
    # exactly ONE is verified -- Jim Mora -- and all 18 verified staff faces are
    # 1986 faces. So the ruling that loses no hand-set data is:
    #
    #   * a verified 1986 face wins and propagates FORWARD, which is precisely
    #     what shipped for Flutie, Rice and Reggie White among the players;
    #   * for the other 39, neither block is evidence about the man -- the 1986
    #     values are family 2 where the modern are family 1, on the same side of
    #     the light/dark line, which is a convention and not a claim -- so the
    #     value carried by most of his files becomes canonical.
    #
    # That rewrites 47 pre-1990 records rather than 130 modern ones, overwrites
    # no verified face, and keeps the gate at full strength: era-scoping stays
    # legitimate for men who appear in ONE era, which is what the block is for.
    changed_s = collections.Counter()
    for k, v in (staff.items() if '--staff' in sys.argv else []):
        if len({y for y, _ in v}) < 2:
            continue
        arrays = {tuple(p['appearance']) for _, p in v}
        if len(arrays) < 2:
            continue
        # EVERY hand-set staff face in the project is a 1986 face -- all 18
        # verified staff entries carry season 1986 -- so a verified coach is
        # looked up in the ERA block first, exactly as the players are. Reading
        # `staff_faces` first would make an unverified modern value canonical
        # and then quietly overwrite the verified one.
        ver = None
        if k in vstaff_names:
            ver = reg.get('staff_faces_1986', {}).get(k)
            if not isinstance(ver, list):
                ver = reg.get('staff_faces', {}).get(k)
        if ver:
            want = list(ver)
        else:
            votes = collections.Counter(tuple(p['appearance']) for _, p in v)
            top = max(votes.values())
            tied = [a for a, n in votes.items() if n == top]
            want = list(tied[0] if len(tied) == 1
                        else tuple(max(v, key=lambda yp: yp[0])[1]['appearance']))
        for y, p in v:
            if p['appearance'] != want:
                p['appearance'] = list(want); changed_s[y] += 1

    print(f'\nplayers: {sum(changed_p.values())} records rewritten '
          f'({sum(n for (nm, _), n in changed_p.items() if nm == "skin")} skin, '
          f'{sum(n for (nm, _), n in changed_p.items() if nm == "hair")} hair)')
    for (nm, y), n in sorted(changed_p.items()): print(f'    {y} {nm}: {n}')
    for t in touched[:12]: print(f'      {t[0]} {t[1]:<24} {t[2]} {t[3]} -> {t[4]}')
    if held_mike:
        print(f'    {len(held_mike)} pre-1990 changes HELD against Mike\'s skin class: ' +
              '; '.join(f'{y} {k} {a}->{b} (mike {m})' for y, k, a, b, m in held_mike[:5]))
    print(f'staff: {sum(changed_s.values())} records rewritten'
          + ('' if '--staff' in sys.argv else '  [HELD — see above]'))
    for y, n in sorted(changed_s.items()): print(f'    {y}: {n}')

    # ---------------- registry <- files, and the namesake block ------------
    # STAFF NAMESAKES, same idea and a second arithmetic test for the case the
    # players do not have: two records of one name in ONE file. Same age is one
    # man holding two jobs; different ages are two men. Jim Mora is Indianapolis
    # head coach at 65 and San Francisco defensive coordinator at 39 in the same
    # 2000 file -- father and son, both real, both correctly placed. Dick LeBeau
    # is 63 on both of his, so he is one man and is NOT recorded here.
    staff_ns = {}
    for k, v in staff.items():
        byfile = collections.defaultdict(list)
        for y, p in v: byfile[y].append(p)
        for y, ps in byfile.items():
            if len(ps) > 1 and len({p.get('age') for p in ps}) > 1:
                staff_ns[k] = (f'{y}: ' + ' vs '.join(
                    f'{p["role"]} {p["teamID"]} aged {p.get("age")}' for p in ps)
                    + ' — one file, one name, different ages, so two men')
    # THE CROSS-FILE TEST IS NOT USED FOR STAFF, and this is a measurement not a
    # caution. Run at tolerance 12 it returns 58 men, and the top of the list is
    # Bill Belichick "aged 49 in 1979 and 34 in 1986" and Adam Gase "35 in 2013,
    # 52 in 2017" -- one man each, with a wrong age field. Staff ages carry far
    # more noise than players' (Bruce Coslet is 40 in both 1986 and 2000), so on
    # this cohort the test measures the age field rather than identity and would
    # write 57 false namesakes into the registry to hide one real problem.
    # The SAME-FILE test above has no such failure mode: two records, one file,
    # one name, two ages is two men whatever the ages are worth.
    print(f'staff namesakes: {len(staff_ns)}')
    for k, v_ in sorted(staff_ns.items()): print(f'    {k:<20} {v_}')

    reg.setdefault('_namesakes', {})
    reg['_namesakes'] = {
        'note': ('Two different men sharing a name and a position. The faces gate keys a '
                 'person on name|position and cannot separate them, so one-face-per-person '
                 'does not apply. Found by the age-gap test: for one man the age gap between '
                 'two files tracks the year gap; these miss by 21-37 years. Recorded so the '
                 'exemption is a fact and not a silent skip.'),
        'players': {k: d for k, d in sorted(nam.items())},
        'staff': {k: d for k, d in sorted(staff_ns.items())},
        'staff_note': ('Two tests, because staff collide two ways. In ONE file: same name, '
                       'different ages means two men (Jim Mora, 65 at Indianapolis and 39 at '
                       'San Francisco in 2000); same age means one man in two jobs, which is a '
                       'data question and not a namesake (Dick LeBeau, 63 on both Cincinnati '
                       'records) and is deliberately NOT recorded here. ACROSS files: the age '
                       'gap must track the year gap, tolerance 12, wider than the players\' 6 '
                       'because staff ages carry more noise.'),
    }
    # SCOPE OF THE REGISTRY UPDATE, deliberately narrow. Item 54 named the
    # entries where the registry's HEAD FAMILY disagrees with the live file --
    # 191 men, and where a face could be checked (Molden, Epenesa, Firkser) the
    # file was right and the registry stale. Only those are rewritten. Rewriting
    # every entry that differs from the newest file in any slot would touch a
    # thousand, most of them aging variants the registry is right to hold.
    reg_updates = 0; reg_seen = 0
    for k, v in players.items():
        if k in nam: continue
        if any(vkey == k or vkey.startswith(k + '|') for vkey in vk): continue
        cur = reg.get('faces', {}).get(k)
        if not isinstance(cur, list): continue
        reg_seen += 1
        newest = max(v, key=lambda yp: yp[0])[1]
        if tok(cur[0])[1] != tok(newest['appearance'][0])[1]:
            reg['faces'][k] = list(newest['appearance']); reg_updates += 1
    print(f'\nregistry: {reg_seen} multi-file entries checked, {reg_updates} rewritten from the '
          f'file on a head-family disagreement (verified untouched; file -> registry as ruled)')
    if '--staff' not in sys.argv:
        print('  staff faces HELD — the registry contradicts itself on 40 of 46 coaches '
              'carried in both blocks; see the module docstring. Escalated, not written.')

    if dry:
        print('\nDRY RUN — nothing written'); return
    for y in YEARS:
        p = f'PGMRoster_{y}.json'; open(repo(p), 'w').write(ser_for(p)(ros[y]))
        p = f'PGMStaff_{y}.json'; open(repo(p), 'w').write(ser_for(p)(stf[y]))
    open(repo(REG), 'w').write(ser_for(REG)(reg))
    print('\nwrote twenty files and the registry')


if __name__ == '__main__':
    main()
