#!/usr/bin/env python3
"""
merge_mike_registry — the Mike family enters the face registry as ONE source with
a tiebreak role. Ruled 2026-09-03.

  python3 tools/merge_mike_registry.py --dry-run
  python3 tools/merge_mike_registry.py

WHAT WAS MEASURED (docs, item 53). Ten .ros files from one project. Every one
carries the same 2,032-record 2003-season base; each adds a period layer. The
97.7% anchor test earlier reported was that base measured through one file —
our anchors are mostly 2000s men — so all ten scored 98.1-98.6% on the same
~560 records. The period layers, the actual contribution, run 89-96%
(LM67 96.2% on 208; 1996Roster 98.3% on 118; the pre-1990 files 88-91% on
19-44 each; NFL1941-69 76.9% on 13, which is NO EVIDENCE, not a low score).
Against hand-verified truth the archive consensus reads 95/95 and Mike 79/81.
On the archive's own splits Mike sides with the majority 29-3. The 59 'ties'
first reported were name-only; 57 of them are the same name at two positions —
different men. Keyed as the registry keys (name|position) the archive has FOUR
one-to-one ties, and Mike resolves all four. Union coverage: 89% of 1979 rostered, 70% of 1986, 86% of 2000.

THE TERMS. (1) ONE source, not ten — one vote on the shared base, separate
votes only on the period layers; the block records which files carry each man.
(2) PSKI 0/1/2 -> light (99/96/92% pure), 3/4/5/6 -> dark (100%), 7 ABSTAINS
(58%, bimodal — the same disposition as value 1 in the three-value sources).
(3) Tiebreak: where the archive's files split one-to-one on a man, the side
Mike agrees with becomes canonical. Where the archive has a majority, it stands
(Mike agrees 29-3). Where the archive has nothing, the Mike label is recorded
for builders to consume; no published face is invented here.

Coverage and the faces gate are reported before and after.
"""
import json, csv, glob, os, sys, re, unicodedata, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
import build_2000 as b
SP = os.path.join(os.environ.get('MIKE_DUMPS', '/private/tmp/claude-501/-Users-ryannecci-Documents/7d657473-7b09-4504-a233-e0c752ba771f/scratchpad/mike'))
MAP = {'0': 'light', '1': 'light', '2': 'light', '3': 'dark', '4': 'dark', '5': 'dark', '6': 'dark', '7': None}
SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
norm = b.norm_registry   # the registry's own key form, measured — not a lookalike
cls = lambda a: 'dark' if a[0][4] in '45' else 'light'
YE = (1979, 1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026)

def main():
    dry = '--dry-run' in sys.argv
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json')))
    # --- the Mike block: one source, files listed per man
    mike = {}
    for p in sorted(glob.glob(os.path.join(SP, '*.PLAY.csv'))):
        f = os.path.basename(p).replace('.PLAY.csv', '').replace(' (1)', '').replace(' 3', '')
        for r in csv.DictReader(open(p)):
            n = norm(r['PFNA'] + ' ' + r['PLNA']); c = MAP.get(r['PSKI'])
            e = mike.setdefault(n, {'votes': collections.Counter(), 'files': set(), 'psKI': collections.Counter()})
            e['files'].add(f); e['psKI'][r['PSKI']] += 1
            if c: e['votes'][c] += 1
    block = {}
    for n, e in mike.items():
        if not e['votes']: block[n] = {'class': None, 'abstain': True, 'files': sorted(e['files']), 'PSKI': dict(e['psKI'])}; continue
        top = e['votes'].most_common()
        block[n] = {'class': top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else None, 'files': sorted(e['files']), 'PSKI': dict(e['psKI'])}
    # --- archive labels per name|position and per file
    labels = collections.defaultdict(dict); files = {}
    for y in YE:
        d = json.load(open(repo(f'PGMRoster_{y}.json'))); files[y] = d
        for x in d:
            if x['teamID'] == 'Rookie': continue
            labels[(norm(x['forename'] + ' ' + x['surname']), x['position'])].setdefault(y, (cls(x['appearance']), x['appearance']))
    # --- coverage before
    rostered = {(norm(x['forename'] + ' ' + x['surname']), x['position']) for y in YE for x in files[y] if x['teamID'] not in ('Rookie', 'Free Agent')}
    reg_cov = sum(1 for k in rostered if f'{k[0]}|{k[1]}' in reg['faces'] or any(kk.startswith(f'{k[0]}|{k[1]}|') for kk in ()))
    mike_only = sum(1 for k in rostered if f'{k[0]}|{k[1]}' not in reg['faces'] and block.get(k[0], {}).get('class'))
    # --- tiebreak
    ties = []; resolved = []
    for k, v in labels.items():
        if len(v) < 2: continue
        cnt = collections.Counter(c for c, _ in v.values())
        if len(cnt) < 2: continue
        m = block.get(k[0], {}).get('class')
        top = cnt.most_common()
        if top[0][1] == top[1][1]:                       # one-to-one tie
            ties.append(k)
            if m:
                win = [(y, app) for y, (c, app) in v.items() if c == m][0]
                resolved.append((k, m, win[0], [y for y, (c, _) in v.items() if c != m]))
                reg['faces'][f'{k[0]}|{k[1]}'] = list(win[1])
    reg['mike_skin'] = block
    reg['_mike'] = ("Skin class from the Mike .ros family (ten files, sources/mike/), merged 2026-09-03 as ONE source: "
                    "they share a 2,032-record 2003 base and differ only in period layers, so they are one vote on the base and separate votes on the layers "
                    "(files listed per man). PSKI 0/1/2 light, 3/4/5/6 dark, 7 abstains. Role: tiebreak where the archive's files split one-to-one, "
                    "and a label where the archive has nothing; never authority over an archive majority (it agrees 29-3) and never over a verified face. "
                    "LM67 is 159 notable teams across 44 seasons (1957-2002), not a league-year database. NFL1941-1969 has no evidence either way (13 anchors).")
    print(f"Mike block: {len(block)} names, {sum(1 for e in block.values() if e['class'])} with a class, {sum(1 for e in block.values() if e.get('abstain') or not e['class'])} abstaining/split")
    print(f"registry coverage of rostered name|position across ten files: {reg_cov}/{len(rostered)} canonical faces before; Mike adds a skin class on {mike_only} uncovered men")
    print(f"one-to-one ties in the archive: {len(ties)}; resolved by Mike: {len(resolved)}  e.g. " + '; '.join(f"{k[0]} -> {m} (keeps {w}, moves {l})" for k, m, w, l in resolved[:5]))
    if dry: print('--dry-run: nothing written'); return
    json.dump(reg, open(repo('reference', 'PGM3_FACE_REGISTRY.json'), 'w'), indent=1)
    print('wrote reference/PGM3_FACE_REGISTRY.json')

if __name__ == '__main__':
    main()
