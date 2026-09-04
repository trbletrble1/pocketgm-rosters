#!/usr/bin/env python3
"""
apply_mike_pre1990 — Mike's period layers are AUTHORITATIVE for skin before 1990;
the archive is the fallback where Mike is silent; the voting system is unchanged
from 2000 on. Ruled 2026-09-03 (items 53-56).

  python3 tools/apply_mike_pre1990.py --dry-run
  python3 tools/apply_mike_pre1990.py

WHY. Ryan verified 100 disagreements by photograph: Mike 95 of 99, the archive 4,
not directional. De-biased over the era population Mike reads ~95-98% and the
archive ~77-81% (NOT 4% — that was a chosen subset). The archive's pre-1990
labels rest on one weak decoded field plus distribution draws that were
propagated as if sourced. The 2000s archive agrees with Mike at 98-99% and is
left alone.

WHAT MOVES. For every rostered or free-agent man in 1979 and 1986 whom Mike's
period layers (not the shared 2003 base) label with a clear class, the skin
family (Head/Nose/Mouth digit) is set into that class: light -> family drawn
from LIGHT_BAND, dark -> DARK_BAND, seeded on identity, variant letter kept.
Hair colour follows the player builder's rule (dark -> Hair1; light -> Hair3),
with beard and eyebrows following hair, style letters kept. A man already in
the right class does not move.

WHAT DOES NOT. The 142 hand-verified faces — asserted untouched. PSKI 7 and
split votes abstain to the archive. Men Mike does not cover keep their archive
label; for 1986 that is 630 men on a label that runs ~77%, and the provenance
sidecar says so per man.

The registry's canonical entries for moved men are updated so the registry does
not later revert them (item 54 makes apply_registry_all unsafe regardless).
"""
import json, csv, glob, os, sys, random, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
import build_2000 as b
SP = os.environ.get('MIKE_DUMPS', '/private/tmp/claude-501/-Users-ryannecci-Documents/7d657473-7b09-4504-a233-e0c752ba771f/scratchpad/mike')
MAP = {'0': 'light', '1': 'light', '2': 'light', '3': 'dark', '4': 'dark', '5': 'dark', '6': 'dark', '7': None}
LIGHT_BAND = [('1', 0.540), ('2', 0.246), ('3', 0.214)]; DARK_BAND = [('4', 0.378), ('5', 0.622)]
cls = lambda a: 'dark' if a[0][4] in '45' else 'light'
def draw(rng, band):
    r = rng.random(); acc = 0
    for f, w in band:
        acc += w
        if r <= acc: return f
    return band[-1][0]

def main():
    dry = '--dry-run' in sys.argv
    sk = ('PFNA', 'PLNA', 'PSKI', 'PAGE', 'POVR', 'PHGT', 'PWGT', 'PCOL'); key = lambda r: tuple(r.get(c, '') for c in sk)
    files = {os.path.basename(p)[:20]: list(csv.DictReader(open(p))) for p in sorted(glob.glob(os.path.join(SP, '*.PLAY.csv')))}
    cnt = collections.Counter()
    for f, rows in files.items():
        for k in {key(r) for r in rows}: cnt[k] += 1
    shared = {k for k, c in cnt.items() if c >= 8}
    mike = collections.defaultdict(lambda: {'v': collections.Counter(), 'p': collections.Counter(), 'f': set()})
    for f, rows in files.items():
        for r in rows:
            if key(r) in shared: continue
            n = b.norm_registry(r['PFNA'] + ' ' + r['PLNA']); e = mike[n]; e['f'].add(f); e['p'][r['PSKI']] += 1
            c = MAP.get(r['PSKI'])
            if c: e['v'][c] += 1
    def verdict(n):
        e = mike.get(n)
        if not e or not e['v']: return None
        t = e['v'].most_common()
        return t[0][0] if len(t) == 1 or t[0][1] > t[1][1] else None
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json'))); ver = set(reg['_verified_keys']['players'])
    def vkey(x, y):
        k = b.norm_registry(x['forename'] + ' ' + x['surname']) + '|' + x['position']
        return k in ver or (k + '|' + x['teamID']) in ver
    prov79 = {(b.norm_registry(r['name']), r['pos']): r for r in csv.DictReader(open(repo('wip', 'faces_1979.csv')))}
    side = []
    for y in (1979, 1986):
        fn = f'PGMRoster_{y}.json'; head = subprocess.run(['git', 'show', f'HEAD:{fn}'], capture_output=True, text=True, cwd=repo('')).stdout
        ser = (lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')) if head.count('\n') > 1 else (lambda d: json.dumps(d, separators=(', ', ': ')))
        assert ser(json.loads(head)) == head
        d = json.load(open(repo(fn))); c = collections.Counter(); touched_verified = 0
        for x in d:
            if x['teamID'] == 'Rookie': continue
            n = b.norm_registry(x['forename'] + ' ' + x['surname']); m = verdict(n); cur = cls(x['appearance'])
            row = {'file': y, 'iden': x['iden'], 'name': f"{x['forename']} {x['surname']}", 'position': x['position'], 'team': x['teamID'], 'before': cur}
            if vkey(x, y):
                c['verified, untouched'] += 1; row.update(after=cur, source='hand-verified (Ryan), protected'); side.append(row); continue
            if m is None:
                e = mike.get(n)
                why = 'Mike abstains (PSKI 7 / split)' if e and e['p'] else 'not in Mike'
                src = f"archive fallback — {why}" + ("; the 1986 archive label runs ~77% on independent test" if y == 1986 else "")
                c['archive fallback: ' + why] += 1; row.update(after=cur, source=src); side.append(row); continue
            e = mike[n]; src = f"Mike period layer, PSKI {dict(e['p'])}, files {sorted(e['f'])}"
            if m == cur: c['Mike agrees, unchanged'] += 1; row.update(after=cur, source=src); side.append(row); continue
            # seeded on the MAN, not the file: the faces gate compares the family
            # digit across seasons, and a per-file seed let one man draw Head1 in
            # 1979 and Head2 in 1986 — same class, 35 false disagreements
            rng = random.Random(f"{n}|{x['position']}|mike"); fam = draw(rng, DARK_BAND if m == 'dark' else LIGHT_BAND)
            a = list(x['appearance'])
            for i, pre in ((0, 'Head'), (5, 'Nose'), (6, 'Mouth')): a[i] = f"{pre}{fam}{a[i].replace(pre, '')[1:]}"
            hf = '1' if m == 'dark' else '3'
            for i, pre in ((2, 'Hair'), (3, 'Beard'), (4, 'Eyebrows')): a[i] = f"{pre}{hf}{a[i].replace(pre, '')[1:]}"
            x['appearance'] = a; c[f'changed {cur} -> {m}'] += 1; row.update(after=m, source=src); side.append(row)
            rk = n + '|' + x['position'] + (f"|{x['teamID']}" if y == 1986 else '')
            blk = reg['faces_1986'] if y == 1986 else reg['faces']
            if rk in blk: blk[rk] = list(a)
            if y == 1979 and (n, x['position']) in prov79: prov79[(n, x['position'])]['skin_source'] = f"Mike period layer PSKI {'/'.join(sorted(e['p']))} (authoritative pre-1990, 2026-09-03)"
        print(f"=== {fn} ===  " + ', '.join(f"{k}: {v}" for k, v in sorted(c.items())))
        assert c['verified, untouched'] == sum(1 for x in d if x['teamID'] != 'Rookie' and vkey(x, y)), 'a verified face moved'
        if not dry: open(repo(fn), 'w').write(ser(d))
    if not dry:
        reg['_mike'] += (" RULED 2026-09-03 (items 53-56): AUTHORITATIVE for skin on pre-1990 files (1979, 1986), archive the fallback where Mike is silent; "
                         "voting unchanged from 2000 on. Ryan verified 100 disagreements by photograph: Mike 95/99, archive 4/99, not directional. "
                         "De-biased over the era population: Mike ~95-98%, archive ~77-81%. The 630 uncovered 1986 men and 200 uncovered 1979 men keep an archive label that runs ~77% pre-1990.")
        json.dump(reg, open(repo('reference', 'PGM3_FACE_REGISTRY.json'), 'w'), indent=1)
        with open(repo('wip', 'faces_1979.csv'), 'w', newline='') as fh:
            rows = list(prov79.values()); w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        with open(repo('reference', 'PGM3_SKIN_PROVENANCE_PRE1990.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(side[0].keys())); w.writeheader(); w.writerows(side)
        print('wrote PGMRoster_1979.json, PGMRoster_1986.json, the registry, wip/faces_1979.csv, reference/PGM3_SKIN_PROVENANCE_PRE1990.csv')
    else: print('--dry-run: nothing written')

if __name__ == '__main__':
    main()
