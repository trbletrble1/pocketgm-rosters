#!/usr/bin/env python3
"""
apply_mike_extend — three extensions to the pre-1990 ruling, and Ryan's verdicts
as truth. Ruled 2026-09-03.

  python3 tools/apply_mike_extend.py --dry-run
  python3 tools/apply_mike_extend.py

1. PROSPECTS. The first apply excluded them and a prospect record is a real man:
   Reggie Roby sat light on a 1979 prospect record after being verified dark.
   Mike's period layer now reaches prospects in 1979 and 1986.
2. THE 1990 BOUNDARY (item 57). Where Mike's period layer speaks, its base is
   silent, and the 2000 record disagrees, 2000 follows Mike — 89 men. The 12
   where period and base disagree with each other are not "base silent" and
   stay with the 2000s voting.
3. RYAN'S VERDICTS ARE TRUTH EVERYWHERE. 100 by photograph: 73 light, 26 dark,
   1 middle. Every record of a verified man in every file and cohort takes the
   verdict; light/dark enter _verified_keys beside the existing 142. The four
   where Mike was wrong — Danielson, Jury, Steve Moore, Lusk, all light — are
   corrected. `middle` (Tatupu) is recorded as Ryan's answer in _verified_middle
   and no family is forced; his face stays as it is.

Family digit seeded on name|position, never on the per-file iden (35 false
cross-season disagreements last time). Hair follows skin by the builder's rule.
"""
import json, csv, glob, os, sys, random, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
import build_2000 as b
SP = os.environ.get('MIKE_DUMPS', '/private/tmp/claude-501/-Users-ryannecci-Documents/7d657473-7b09-4504-a233-e0c752ba771f/scratchpad/mike')
MAP = {'0': 'light', '1': 'light', '2': 'light', '3': 'dark', '4': 'dark', '5': 'dark', '6': 'dark', '7': None}
LIGHT_BAND = [('1', 0.540), ('2', 0.246), ('3', 0.214)]; DARK_BAND = [('4', 0.378), ('5', 0.622)]
cls = lambda a: 'dark' if a[0][4] in '45' else 'light'
YE = (1979, 1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026)
def draw(rng, band):
    r = rng.random(); acc = 0
    for f, w in band:
        acc += w
        if r <= acc: return f
    return band[-1][0]
def set_class(x, m, n):
    rng = random.Random(f"{n}|{x['position']}|mike"); fam = draw(rng, DARK_BAND if m == 'dark' else LIGHT_BAND)
    a = list(x['appearance'])
    for i, pre in ((0, 'Head'), (5, 'Nose'), (6, 'Mouth')): a[i] = f"{pre}{fam}{a[i].replace(pre, '')[1:]}"
    hf = '1' if m == 'dark' else '3'
    for i, pre in ((2, 'Hair'), (3, 'Beard'), (4, 'Eyebrows')): a[i] = f"{pre}{hf}{a[i].replace(pre, '')[1:]}"
    x['appearance'] = a

def main():
    dry = '--dry-run' in sys.argv
    sk = ('PFNA', 'PLNA', 'PSKI', 'PAGE', 'POVR', 'PHGT', 'PWGT', 'PCOL'); key = lambda r: tuple(r.get(c, '') for c in sk)
    files = {os.path.basename(p)[:20]: list(csv.DictReader(open(p))) for p in sorted(glob.glob(os.path.join(SP, '*.PLAY.csv')))}
    cnt = collections.Counter()
    for f, rows in files.items():
        for k in {key(r) for r in rows}: cnt[k] += 1
    shared = {k for k, c in cnt.items() if c >= 8}
    per = collections.defaultdict(collections.Counter); base = collections.defaultdict(collections.Counter); psk = collections.defaultdict(collections.Counter)
    for f, rows in files.items():
        for r in rows:
            n = b.norm_registry(r['PFNA'] + ' ' + r['PLNA']); c = MAP.get(r['PSKI'])
            if key(r) in shared:
                if c: base[n][c] += 1
            else:
                psk[n][r['PSKI']] += 1
                if c: per[n][c] += 1
    top = lambda v: (v.most_common(1)[0][0] if v and (len(v) == 1 or v.most_common(2)[0][1] > v.most_common(2)[1][1]) else None)
    # verdicts keyed on name|POSITION from the sheet Ryan verified — a namesake at
    # another position is a different man and does not take the verdict
    vd_by_name = {b.norm_registry(r['name']): r['verdict'] for r in csv.DictReader(open(repo('wip', 'mike_verdicts_ryan.csv')))}
    sheet = list(csv.reader(open(repo('wip', 'mike_disagreements_for_ryan.csv'))))[5:]
    verd = {b.norm_registry(r[0]) + '|' + r[1]: vd_by_name[b.norm_registry(r[0])] for r in sheet if b.norm_registry(r[0]) in vd_by_name}
    assert len(verd) == 100, len(verd)
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json'))); ver = set(reg['_verified_keys']['players'])
    side = {(r['file'], r['iden']): r for r in csv.DictReader(open(repo('reference', 'PGM3_SKIN_PROVENANCE_PRE1990.csv')))}
    stats = collections.defaultdict(collections.Counter); newver = set(); middle = []
    for y in YE:
        fn = f'PGMRoster_{y}.json'; head = subprocess.run(['git', 'show', f'HEAD:{fn}'], capture_output=True, text=True, cwd=repo('')).stdout
        ser = (lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')) if head.count('\n') > 1 else (lambda d: json.dumps(d, separators=(', ', ': ')))
        assert ser(json.loads(head)) == head
        d = json.load(open(repo(fn))); moved = False
        for x in d:
            n = b.norm_registry(x['forename'] + ' ' + x['surname']); k = n + '|' + x['position']; cur = cls(x['appearance'])
            # 3. verdicts first, everywhere
            if k in verd:
                vd = verd[k]
                if vd == 'middle':
                    middle.append(f"{k}|{y}"); stats[y]['middle recorded, face untouched'] += 1; continue
                newver.add(k)
                if vd != cur: set_class(x, vd, n); stats[y][f'verdict {vd} applied (was {cur})'] += 1; moved = True
                else: stats[y]['verdict agrees'] += 1
                if str(y) in ('1979', '1986'):
                    s = side.get((str(y), x['iden']))
                    if s: s['after'] = vd; s['source'] = 'hand-verified by photograph (Ryan, 2026-09-03), protected'
                    else: side[(str(y), x['iden'])] = {'file': y, 'iden': x['iden'], 'name': f"{x['forename']} {x['surname']}", 'position': x['position'], 'team': x['teamID'], 'before': cur, 'after': vd, 'source': 'hand-verified by photograph (Ryan, 2026-09-03), protected'}
                continue
            if k in ver or (k + '|' + x['teamID']) in ver: continue
            mp = top(per.get(n, collections.Counter())); mb = top(base.get(n, collections.Counter()))
            # 1. prospects in 1979/1986
            if y in (1979, 1986) and x['teamID'] == 'Rookie':
                if mp is None: stats[y]['prospect: archive kept (' + ('abstain' if psk.get(n) else 'not in Mike') + ')'] += 1; src = 'archive fallback (prospect) — ' + ('Mike abstains' if psk.get(n) else 'not in Mike')
                elif mp == cur: stats[y]['prospect: Mike agrees'] += 1; src = f"Mike period layer, PSKI {dict(psk[n])}"
                else: set_class(x, mp, n); stats[y][f'prospect changed {cur} -> {mp}'] += 1; moved = True; src = f"Mike period layer, PSKI {dict(psk[n])} (prospect, extended)"
                side[(str(y), x['iden'])] = {'file': y, 'iden': x['iden'], 'name': f"{x['forename']} {x['surname']}", 'position': x['position'], 'team': x['teamID'], 'before': cur, 'after': cls(x['appearance']), 'source': src}
                continue
            # 2. the 1990 boundary in 2000
            if y == 2000 and x['teamID'] != 'Rookie' and mp and not mb and mp != cur:
                set_class(x, mp, n); stats[y][f'boundary: 2000 follows Mike ({cur} -> {mp})'] += 1; moved = True
                rk = k
                if rk in reg['faces']: reg['faces'][rk] = list(x['appearance'])
        if moved:
            for x in d:
                n = b.norm_registry(x['forename'] + ' ' + x['surname']); rk = n + '|' + x['position'] + (f"|{x['teamID']}" if y == 1986 else '')
                blk = reg['faces_1986'] if y == 1986 else reg['faces']
                if rk in blk and cls(blk[rk]) != cls(x['appearance']): blk[rk] = list(x['appearance'])
        print(f"=== {fn} ===  " + ', '.join(f"{k2}: {v}" for k2, v in sorted(stats[y].items())) if stats[y] else f"=== {fn} ===  nothing")
        if not dry and moved: open(repo(fn), 'w').write(ser(d))
    print(f"\nverified keys: {len(ver)} + {len(newver - ver)} new = {len(ver | newver)};  middle recorded: {middle}")
    if not dry:
        reg['_verified_keys']['players'] = sorted(ver | newver)
        reg['_verified_middle'] = {'note': "Ryan's verdict by photograph was 'middle' — genuinely between the two. A verdict, not an abstention: a source calling him either way is not wrong the way a clear miss is. No family forced; the face stays as it was.", 'players': sorted(set(middle))}
        json.dump(reg, open(repo('reference', 'PGM3_FACE_REGISTRY.json'), 'w'), indent=1)
        rows = list(side.values())
        with open(repo('reference', 'PGM3_SKIN_PROVENANCE_PRE1990.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=['file', 'iden', 'name', 'position', 'team', 'before', 'after', 'source']); w.writeheader(); w.writerows(rows)
        print('wrote roster files, the registry, reference/PGM3_SKIN_PROVENANCE_PRE1990.csv')
    else: print('--dry-run: nothing written')

if __name__ == '__main__':
    main()
