#!/usr/bin/env python3
"""
skin_anchor — the accuracy of every skin source this project holds, measured
against one ground truth, and reported beside the screen's verdict so the two
can be compared.

  python3 tools/skin_anchor.py                 # every .ros and every 2K5 save
  python3 tools/skin_anchor.py --selftest

GROUND TRUTH: the men the 2K5 archive labels unanimously across three or more
saves. For a .ros file that is the whole archive. For a 2K5 save under test it
is the archive WITHOUT that save — leave-one-out — otherwise a save is scored
against a consensus it helped form and every save looks better than it is.

The `PSKI` middle-value screen (>28% on value 1 = "collapsed") measures whether
a field has degenerated. It does NOT measure whether the values are right. On
the first five files tested it rejected three at 67-74% accuracy and passed one
at 90%, and the file that actually fails (57%, near a coin flip) sits at a lower
middle share than three it rejects. This tool exists so that the accuracy figure
sits next to every source and the screen is never read as a usability gate.
"""
import sys, os, re, csv, glob, subprocess, unicodedata, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl2k5
from pgm3_paths import sources, repo

MIN_VOTES = 3

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

def load_saves():
    out = {}
    for f in sorted(glob.glob(sources('NFL2k25 Year Saves', '*.DAT'))):
        try:
            out[os.path.basename(f)] = {norm(q['fname'] + ' ' + q['lname']): q['skin_band']
                                        for q in nfl2k5.Save(f).players}
        except Exception as e:
            print(f'  skip {os.path.basename(f)}: {e}', file=sys.stderr)
    return out

def consensus(saves, exclude=None):
    votes = collections.defaultdict(list)
    for name, d in saves.items():
        if name == exclude:
            continue
        for n, b in d.items():
            votes[n].append(b)
    return {n: v[0] for n, v in votes.items() if len(v) >= MIN_VOTES and len(set(v)) == 1}

def score_ros(path, truth):
    out = '/tmp/skin_anchor_' + re.sub(r'[^A-Za-z0-9]', '_', os.path.basename(path)) + '.csv'
    if not os.path.exists(out):
        r = subprocess.run([sys.executable, repo('tools', 'rosdump.py'), 'dump', path, 'PLAY', '-o', out],
                           capture_output=True, text=True)
        if r.returncode:
            return None
    rows = list(csv.DictReader(open(out)))
    if not rows or 'PSKI' not in rows[0]:
        return None
    k = [int(x['PSKI']) for x in rows if x['PSKI'].isdigit()]
    mid = sum(1 for v in k if v == 1) / max(1, len(k))
    m = [(truth[norm(x['PFNA'] + ' ' + x['PLNA'])], int(x['PSKI'])) for x in rows
         if x['PSKI'].isdigit() and norm(x['PFNA'] + ' ' + x['PLNA']) in truth]
    if len(m) < 30:
        return dict(n=len(m), acc=None, mid=mid, rule='')
    best = max(((sum(1 for b, v in m if ('dark' if v >= t else 'light') == b) / len(m), t) for t in (1, 2)))
    return dict(n=len(m), acc=best[0], mid=mid, rule=f'dark>={best[1]}')

def score_save(name, saves):
    truth = consensus(saves, exclude=name)
    d = saves[name]
    m = [(truth[n], b) for n, b in d.items() if n in truth]
    if len(m) < 30:
        return dict(n=len(m), acc=None)
    return dict(n=len(m), acc=sum(1 for t, b in m if t == b) / len(m))

def selftest():
    ok = 0
    saves = {'a': {'x': 'dark', 'y': 'light'}, 'b': {'x': 'dark', 'y': 'light'},
             'c': {'x': 'dark', 'y': 'light'}, 'd': {'x': 'dark', 'y': 'dark'}}
    try:
        full = consensus(saves)
        loo = consensus(saves, exclude='d')
        assert 'y' not in full and loo.get('y') == 'light', 'leave-one-out must change the truth'
        ok += 1; print("  ok: leave-one-out removes the save under test from its own ground truth")
    except AssertionError as e:
        print(f'  FAIL: {e}')
    try:
        assert consensus({'a': {'x': 'dark'}, 'b': {'x': 'dark'}}) == {}, 'two votes is not unanimity'
        ok += 1; print('  ok: fewer than three votes is not a ground truth')
    except AssertionError as e:
        print(f'  FAIL: {e}')
    return ok

def main():
    saves = load_saves()
    truth = consensus(saves)
    print(f'ground truth: {len(truth)} men unanimous across {MIN_VOTES}+ of {len(saves)} saves\n')
    rows = []
    for f in sorted(glob.glob(sources('**', '*.ros'), recursive=True)):
        s = score_ros(f, truth)
        if s:
            rows.append((os.path.relpath(f, sources()), 'ros', s))
    for name in sorted(saves):
        rows.append((name, '2k5', score_save(name, saves)))
    w = csv.writer(open(repo('docs', 'skin_anchor_table.csv'), 'w', newline=''))
    w.writerow(['source', 'kind', 'matched', 'accuracy', 'pski_middle_share', 'screen_verdict', 'rule'])
    print(f"{'source':<40}{'kind':<5}{'matched':>8}{'accuracy':>10}{'middle':>8}   screen")
    for src, kind, s in rows:
        acc = f"{s['acc']*100:.0f}%" if s['acc'] is not None else '  (thin)'
        mid = f"{s['mid']*100:.0f}%" if 'mid' in s else '     -'
        verdict = ('REJECT' if s['mid'] > 0.28 else 'pass') if 'mid' in s else '-'
        print(f'{src:<40}{kind:<5}{s["n"]:>8}{acc:>10}{mid:>8}   {verdict}')
        w.writerow([src, kind, s['n'], f"{s['acc']:.3f}" if s['acc'] is not None else '',
                    f"{s['mid']:.3f}" if 'mid' in s else '', verdict, s.get('rule', '')])
    print(f'\nwrote docs/skin_anchor_table.csv ({len(rows)} sources)')

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('self-test:'); sys.exit(0 if selftest() == 2 else 1)
    main()
