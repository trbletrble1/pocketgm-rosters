#!/usr/bin/env python3
"""
apply_2026_qb_faces — Ryan's hand-edited quarterback avatars, from an in-game
export, into 2026 and the face registry.

  python3 tools/apply_2026_qb_faces.py --dry-run
  python3 tools/apply_2026_qb_faces.py EXPORT.json

RYAN'S EDIT IS THE CURRENT DECISION, whatever the registry already holds.
`_verified_keys` protects his edits from automated passes; it does not protect
them from him. Where a man is already verified with a different face the new one
SUPERSEDES it, with no conflict flagged and nothing to confirm — he has said he
cannot reasonably track which players he has already edited, so latest edit wins.
Both such men are named in the report so he can see the set.

MATCHING IS BY NAME AND POSITION, not `iden`: the game regenerates identifiers on
export, so the 3,649-record export shares ZERO ids with our 2,634. It also carries
the game's own generated players, which is why only 1:1 name+position matches are
taken.

PROPAGATION FOLLOWS THE GATE'S OWN RULE, which is what "the way earlier hand
edits were" means in code. `pgm3_validate faces` scores a verified face as intact
when, across seasons:

    Head, Nose, Mouth   the FAMILY matches; the variant may differ (players age)
    Eyes, Hair, Beard, Eyebrows, Glasses, Clothes   match EXACTLY

Propagating the head family alone left the other eight elements as they were and
the gate failed on 32 records. Following its rule is not tuning to the test: the
test is the written form of the convention.
"""
import json, sys, os, re, unicodedata, collections, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

YEARS = (1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021)
REG = repo('reference', 'PGM3_FACE_REGISTRY.json')

SUFFIX = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

def norm(s):
    """The registry's own rule: 'lowercase, strip punctuation and Jr/Sr/II/III/IV/V'.

    Not stripping the suffix cost Gardner Minshew his propagation — he is
    'Gardner Minshew II' in 2017 and 2021 and 'Gardner Minshew' in 2026, so the
    keys never met and the gate then reported his 2021 face as overwritten. The
    same asymmetry the validator's own comment describes for Marion Barber."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'[^a-z ]', '', s)
    return ' '.join(w for w in s.split() if w not in SUFFIX).strip()

def key(x):
    return norm(x['forename'] + ' ' + x['surname']) + '|' + x['position']

def family_tok(tok):
    """'Head4c' -> ('4', 'c'); works for Nose and Mouth too."""
    m = re.match(r'[A-Za-z]+(\d+)([a-z0-9]*)$', tok)
    return (m.group(1), m.group(2)) if m else (None, None)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    exp_path = args[0] if args else max(
        (os.path.join(os.path.expanduser('~/Downloads'), f)
         for f in os.listdir(os.path.expanduser('~/Downloads')) if f.startswith('PGMRoster 2026-')),
        key=os.path.getmtime)
    exp = json.load(open(exp_path))
    ours = json.load(open(repo('PGMRoster_2026.json')))
    E = collections.defaultdict(list)
    O = collections.defaultdict(list)
    for x in exp: E[key(x)].append(x)
    for x in ours: O[key(x)].append(x)
    changed = sorted(k for k in O if k in E and len(E[k]) == 1 and len(O[k]) == 1
                     and E[k][0]['appearance'] != O[k][0]['appearance'])
    assert changed, 'no appearance differences found — wrong export?'
    assert all(k.endswith('|QB') for k in changed), \
        'the export changes a non-quarterback: ' + str([k for k in changed if not k.endswith('|QB')])

    reg = json.load(open(REG))
    vk = reg['_verified_keys']['players']
    superseded = [(k, reg['faces'].get(k), E[k][0]['appearance']) for k in changed if k in set(vk)]

    # 1. the 2026 file
    for k in changed:
        O[k][0]['appearance'] = list(E[k][0]['appearance'])
    # 2. the registry: canonical face, and the verified flag
    for k in changed:
        reg['faces'][k] = list(E[k][0]['appearance'])
    added = [k for k in changed if k not in set(vk)]
    reg['_verified_keys']['players'] = sorted(set(vk) | set(changed))
    # 3. propagate across the other seasons, by the gate's rule
    FAMILY_ONLY = (0, 5, 6)          # Head, Nose, Mouth — variant free to age
    EXACT = (1, 2, 3, 4, 7, 8)       # Eyes, Hair, Beard, Eyebrows, Glasses, Clothes
    prop = collections.Counter()
    prop_detail = []
    chg = set(changed)
    for y in YEARS:
        p = repo(f'PGMRoster_{y}.json')
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        hit = 0
        for x in d:
            k = key(x)
            if k not in chg:
                continue
            want = E[k][0]['appearance']
            was = list(x['appearance'])
            new = list(was)
            for i in FAMILY_ONLY:
                nf, _ = family_tok(want[i])
                of, ov = family_tok(new[i])
                if nf and of:
                    new[i] = re.sub(r'^([A-Za-z]+)\d+', r'\g<1>' + nf, new[i])
            for i in EXACT:
                new[i] = want[i]
            if new != was:
                x['appearance'] = new
                hit += 1
                d0 = [f'{was[i]}->{new[i]}' for i in range(9) if was[i] != new[i]]
                prop_detail.append((y, k, ', '.join(d0[:4])))
        prop[y] = hit
        if hit and not dry:
            json.dump(d, open(p, 'w'), separators=(', ', ': '))
    print(f'export: {os.path.basename(exp_path)}  ({len(exp)} records, ours {len(ours)})')
    print(f'appearances changed: {len(changed)}, all quarterbacks')
    print(f'_verified_keys players: {len(vk)} -> {len(reg["_verified_keys"]["players"])} '
          f'({len(added)} new, {len(superseded)} superseded)')
    if superseded:
        print('\n  ALREADY VERIFIED AND NOW DIFFERENT — the new edit wins:')
        for k, old, new in superseded:
            print(f'    {k:<26}{old[0] if old else "?"} -> {new[0]}   (full face replaced)')
    print(f'\n  head family propagated to other seasons: {dict(prop)}')
    for y, k, d0 in prop_detail:
        print(f'    {y}  {k:<26}{d0}')
    if dry:
        print('\n--dry-run: nothing written'); return
    json.dump(ours, open(repo('PGMRoster_2026.json'), 'w'), separators=(', ', ': '))
    # compact, as stored: indent=1 turned a 39-face change into a 180,072-line diff
    json.dump(reg, open(REG, 'w'), separators=(',', ':'))
    print('\nwrote PGMRoster_2026.json and the face registry')

if __name__ == '__main__':
    main()
