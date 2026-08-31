#!/usr/bin/env python3
"""Apply the face registry to EVERY published season, not only the one in hand.

A player who appears either side of a boundary must look the same in both, so
the registry pass is archive-wide by definition. Players take the FAMILY DIGIT
only — the aging variant legitimately differs between seasons and writing the
array wholesale flattens it. Staff take the whole array; a coach has one look
and does not age.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_2000 as b

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEARS = (1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021)

def main(apply=False):
    reg = json.load(open(os.path.join(REPO, 'reference', 'PGM3_FACE_REGISTRY.json')))
    before = {g: set(v) for g, v in reg['_verified_keys'].items()}
    assert len(before['players']) == 84 and len(before['staff']) == 18, \
        f'_verified_keys is {len(before["players"])}/{len(before["staff"])}, expected 84/18'
    total = 0
    for y in YEARS:
        path = os.path.join(REPO, f'PGMRoster_{y}.json')
        if not os.path.exists(path): continue
        d = json.load(open(path))
        blk = reg['faces_1986'] if y == 1986 else reg['faces']
        changed = []
        for p in d:
            k = b.norm_registry(p['forename'] + ' ' + p['surname'])
            key = f'{k}|{p["position"]}' + (f'|{p["teamID"]}' if y == 1986 else '')
            ent = blk.get(key)
            if not ent: continue
            keep = [p['appearance'][i].replace(pre, '')[1:] for i, pre in
                    ((0, 'Head'), (5, 'Nose'), (6, 'Mouth'))]
            cand = list(ent)
            for (i, pre), var in zip(((0, 'Head'), (5, 'Nose'), (6, 'Mouth')), keep):
                cand[i] = f'{pre}{ent[i].replace(pre, "")[0]}{var}'
            if cand == p['appearance']: continue
            old = p['appearance'][0]
            p['appearance'] = cand
            changed.append((f"{p['forename']} {p['surname']}", p['position'],
                            p['teamID'], old, p['appearance'][0]))
        total += len(changed)
        print(f'  {y}: {len(changed)} record(s)')
        for nm, pos, t, o, n in changed[:5]:
            print(f'      {nm} ({pos}, {t}) {o} -> {n}')
        if apply and changed:
            # the aging variant must SURVIVE — only the family digit moves
            for nm, pos, t, o, n in changed:
                assert o[-1] == n[-1], f'{nm}: variant changed {o} -> {n}'
            json.dump(d, open(path, 'w'), separators=(',', ':'))
    after = {g: set(v) for g, v in json.load(open(
        os.path.join(REPO, 'reference', 'PGM3_FACE_REGISTRY.json')))['_verified_keys'].items()}
    assert after == before, '_verified_keys changed'
    print(f'  total {total}   _verified_keys untouched: '
          f'{len(before["players"])} players / {len(before["staff"])} staff')
    if not apply: print('\ndry run — nothing written. pass --apply.')
    return 0

if __name__ == '__main__':
    sys.exit(main('--apply' in sys.argv))
