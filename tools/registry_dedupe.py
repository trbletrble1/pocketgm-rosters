#!/usr/bin/env python3
"""Remove duplicate face-registry keys that refer to the same man.

Six keys, each a second spelling of a person who already has an entry. In every
case the key being KEPT is the one whose face matches what the shipped file
actually carries, so no published file changes; the key being deleted can only
ever cause a wrong match.

Ruling (Ryan, 2026-08-31): keep whichever key the shipped file's face matches,
delete the other. Nothing here is in `_verified_keys`, so no hand edit is at
risk — and that is asserted rather than assumed.
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, 'reference', 'PGM3_FACE_REGISTRY.json')

# (block, key to DELETE, key to KEEP, why)
DELETIONS = [
    ('faces_1986', 'maurice  douglass|S|CHI', 'maurice douglass|S|CHI',
     'double space; both entries agree (Head4a), so this changes nothing'),
    ('faces_1986', 'william  roberts|OG|NYG', 'william roberts|OG|NYG',
     'double space; Head3b against the shipped Head5b'),
    ('faces_1986', 'joe  jacoby|OT|WAS', 'joe jacoby|OT|WAS',
     'double space; Head3b against the shipped Head5b'),
    ('faces_1986', 'ali hajisheikh|K|CAR', 'ali haji sheikh|K|CAR',
     'hyphen glued instead of spaced; Head1a against the shipped Head2a'),
    ('faces_1986', 'a j jones|RB|Free Agent', 'aj jones|RB|Free Agent',
     'initials spaced instead of glued; Head5a against the shipped Head4a'),
    ('faces', 'brian st pierre|QB', 'brian stpierre|QB',
     'period spaced instead of glued; Head3c against the shipped Head1a'),
]

def main(apply=False):
    reg = json.load(open(REG))
    locked = {g: set(v) for g, v in reg['_verified_keys'].items()}
    before = {b: len(reg[b]) for b in ('faces', 'faces_1986', 'staff_faces', 'staff_faces_1986')}
    locked_before = {g: set(v) for g, v in reg['_verified_keys'].items()}

    for blk, dead, keep, why in DELETIONS:
        assert dead in reg[blk], f'{dead} is not present — registry already changed?'
        assert keep in reg[blk], f'{keep} is missing — refusing to delete its twin'
        # THE assertion: never remove or alter anything Ryan set by hand.
        for grp, ks in locked.items():
            assert dead not in ks, f'{dead} is in _verified_keys.{grp} — LOCKED'
        print(f'  delete {dead!r}\n     keep {keep!r}   ({why})')
        if apply: del reg[blk][dead]

    if not apply:
        print('\ndry run — nothing written. pass --apply to write.')
        return 0
    after = {b: len(reg[b]) for b in before}
    for b in before:
        exp = before[b] - sum(1 for d in DELETIONS if d[0] == b)
        assert after[b] == exp, f'{b}: expected {exp} keys, got {after[b]}'
    assert {g: set(v) for g, v in reg['_verified_keys'].items()} == locked_before, \
        '_verified_keys changed — refusing to write'
<<<<<<< HEAD
    json.dump(reg, open(REG, 'w'), indent=1)
=======
    # Preserve the file's own compact format. Writing it with indent=1 turned a
    # six-key deletion into a 180,000-line diff, which is unreviewable and is
    # the formatting-churn problem the handoff already records.
    json.dump(reg, open(REG, 'w'), separators=(',', ':'), ensure_ascii=True)
>>>>>>> main
    print(f'\nwrote {REG}')
    for b in before: print(f'  {b}: {before[b]} -> {after[b]}')
    return 0

if __name__ == '__main__':
    sys.exit(main('--apply' in sys.argv))
