#!/usr/bin/env python3
"""
fix_2021_fa_injuryprone — the last cross-year failure. Ruled 2026-09-03.

    python3 tools/fix_2021_fa_injuryprone.py --dry-run
    python3 tools/fix_2021_fa_injuryprone.py

THE DEFECT, and it is a cohort crossing exactly as Ryan read it. 2021's free
agents carry the ARCHIVE'S ROOKIE DRAW of injuryProne:

    2021 free agents vs the nine other files' free agents   KS 0.263
    2021 free agents vs the nine other files' rookies       KS 0.067

Medians alone would not have settled it -- the cohort reads 34 where the archive
reads 49, and 34 happens to be the archive's rookie median, which is suggestive
and no more. The distributions settle it: 103 men matching a pool of 9,000
rookies at KS 0.067 is the same draw.

A FIRST TEST OF MINE WAS WRONG AND IS WORTH RECORDING. I compared 2021's free
agents against 2021's OWN rookies, found them differently shaped (KS 0.306), and
concluded there was no crossing. 2021's rookies are themselves anomalous -- p10
19 to p90 41 against an archive rookie spread of 6 to 83 -- so the comparison
tested one defect against another. The reference for "what a rookie draw looks
like" is the archive, never the file being questioned.

SCOPE, measured rather than assumed:

  * NO OTHER FIELD crossed. injuryProne separates the two pools by KS 0.196;
    discipline, loyalty, ambition, greed and intelligence separate them by
    0.005-0.052, and the same test on 2017's free agents assigns those fields to
    a different pool each time. They cannot tell the pools apart, so they are
    not evidence of anything.
  * NO OTHER FILE crossed. Eight files show "rostered matches the free-agent
    pool", which is an artifact: rostered and free-agent draws are
    indistinguishable archive-wide, KS 0.02-0.05 in both directions. 1979 and
    2026 match nothing well, which is a different thing from matching the wrong
    cohort.
  * THERE IS NO BUILDER OF OURS TO RE-RUN. 2021's injuryProne is byte-identical
    to the file's first commit, 77da945 "Add files via upload". The crossing
    came in with the donor; no tool in this repository ever assigned the field.
    So the correct assignment is being made for the first time rather than
    repaired.

THE FIX: a rank-preserving remap of the 103 men onto the nine-file free-agent
distribution, plotting position (i+0.5)/n. Every man keeps his place in the
order -- the most fragile free agent stays the most fragile -- and the cohort
lands on the archive's level. Nothing else in the record is touched.

STILL OPEN, deliberately: 2021's ROOKIES are narrower than any other file's
rookie draw (p10 19, p90 41). Their median of 29 sits inside the archive's 28-44
so no gate fires, and widening a distribution is a different decision from
moving one onto its own cohort's level. Measured and left.
"""
import json, os, sys, subprocess, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

YEARS = [1979, 1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026]
Y, FIELD = 2021, 'injuryProne'


def cohort(p):
    return 'Rookie' if p.get('teamID') == 'Rookie' else ('FA' if p.get('teamID') == 'Free Agent' else 'T')


def main():
    dry = '--dry-run' in sys.argv
    path = f'PGMRoster_{Y}.json'
    head = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True, text=True, cwd=repo('')).stdout
    ser = None
    for f in (lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, separators=(', ', ': ')),
              lambda d: json.dumps(d, separators=(',', ':'))):
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head:
                ser = (lambda ff, nn: (lambda x: ff(x) + nn))(f, nl); break
        if ser: break
    assert ser, f'{path}: stored formatting not reproduced'

    ref = sorted(p[FIELD] for y in YEARS if y != Y
                 for p in json.load(open(repo(f'PGMRoster_{y}.json'))) if cohort(p) == 'FA')
    d = json.load(open(repo(path)))
    fa = [p for p in d if cohort(p) == 'FA']
    order = sorted(fa, key=lambda p: (p[FIELD], p['iden']))
    n = len(order)
    before = [p[FIELD] for p in fa]
    moved = 0
    for i, p in enumerate(order):
        q = (i + 0.5) / n
        v = ref[min(len(ref) - 1, int(round(q * (len(ref) - 1))))]
        if p[FIELD] != v: p[FIELD] = v; moved += 1
    after = [p[FIELD] for p in fa]
    qq = lambda v, x: sorted(v)[int(x * (len(v) - 1))]
    print(f'{Y} free agents: {n} men, {moved} values changed')
    print(f'  reference: {len(ref)} free agents from the other nine files, median {st.median(ref):.0f}')
    print(f'  before  p10 {qq(before,.1):>3}  p25 {qq(before,.25):>3}  median {st.median(before):>5.1f}  p75 {qq(before,.75):>3}  p90 {qq(before,.9):>3}')
    print(f'  after   p10 {qq(after,.1):>3}  p25 {qq(after,.25):>3}  median {st.median(after):>5.1f}  p75 {qq(after,.75):>3}  p90 {qq(after,.9):>3}')
    # RANK PRESERVED, tested as monotonicity rather than as a stable sort: the
    # remap creates ties, and re-sorting a tie block by iden reorders men inside
    # it while preserving every rank relation that existed. The property is that
    # nobody overtakes anybody.
    vals = [p[FIELD] for p in order]
    assert all(a <= b for a, b in zip(vals, vals[1:])), 'the remap did not preserve the order'
    assert len(fa) == n and all(cohort(p) == 'FA' for p in order)
    if dry:
        print('  DRY RUN — nothing written'); return
    open(repo(path), 'w').write(ser(d))
    print(f'  wrote {path}')


if __name__ == '__main__':
    main()
