#!/usr/bin/env python3
"""
fix_1979_beards — 1979's beards are a flat uniform draw; redraw them from the
archive's own distribution. Ruled 2026-09-03 (item 59), independent of Mike.

  python3 tools/fix_1979_beards.py --dry-run
  python3 tools/fix_1979_beards.py

1979's beard style letters sit at 194-249 each — a uniform draw across the
eight tokens — where every other file has clean shaven (`g`) dominant at
28-32% and a consistent shape. There is no beard source (Madden bakes facial
hair into the head model, item 58), so the honest target is the archive's own
shape: the pooled distribution of the nine other files' rostered men,
conditioned on skin class (it differs: dark-skinned men wear the fuller
styles more), drawn seeded on name|position so a man agrees with himself
across files. Hand-verified faces untouched. Colour digit untouched (it is
shared with hair and eyebrows, item 58).
"""
import json, os, sys, random, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
import build_2000 as b
cls = lambda a: 'dark' if a[0][4] in '45' else 'light'
def main():
    dry = '--dry-run' in sys.argv
    reg = json.load(open(repo('reference', 'PGM3_FACE_REGISTRY.json'))); ver = set(reg['_verified_keys']['players'])
    pool = collections.defaultdict(collections.Counter)
    for y in (1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026):
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))):
            if x['teamID'] != 'Rookie': pool[cls(x['appearance'])][x['appearance'][3][6:]] += 1
    dist = {c: sorted(v.items()) for c, v in pool.items()}
    for c, v in dist.items(): print(f"  archive beard shape, {c}: " + ', '.join(f"{t} {n / sum(n2 for _, n2 in v):.0%}" for t, n in v))
    def draw(rng, c):
        v = dist[c]; tot = sum(n for _, n in v); r = rng.random() * tot; acc = 0
        for t, n in v:
            acc += n
            if r <= acc: return t
        return v[-1][0]
    head = subprocess.run(['git', 'show', 'HEAD:PGMRoster_1979.json'], capture_output=True, text=True, cwd=repo('')).stdout
    d = json.load(open(repo('PGMRoster_1979.json'))); before = collections.Counter(x['appearance'][3][6:] for x in d); moved = 0
    for x in d:
        n = b.norm_registry(x['forename'] + ' ' + x['surname']); k = n + '|' + x['position']
        if k in ver or k + '|' + x['teamID'] in ver: continue
        t = draw(random.Random(f"{k}|beard"), cls(x['appearance']))
        a = list(x['appearance']); new = a[3][:6] + t
        if new != a[3]: a[3] = new; x['appearance'] = a; moved += 1
    after = collections.Counter(x['appearance'][3][6:] for x in d)
    print(f"  1979 before: " + ', '.join(f"{t} {n}" for t, n in sorted(before.items())))
    print(f"  1979 after:  " + ', '.join(f"{t} {n}" for t, n in sorted(after.items())) + f"   ({moved} moved)")
    if dry: print('  --dry-run'); return
    open(repo('PGMRoster_1979.json'), 'w').write(json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')); print('  wrote PGMRoster_1979.json')
if __name__ == '__main__': main()
