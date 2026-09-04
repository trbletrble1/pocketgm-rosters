#!/usr/bin/env python3
"""
fix_prospect_floor — the +3 prospect floor made archive-wide. Ruled by Ryan
2026-09-03.

    python3 tools/fix_prospect_floor.py --dry-run
    python3 tools/fix_prospect_floor.py 1979 1986 ...        # default: all ten

THE RULING AND WHY IT EXISTS. outcome_ceilings applied a rating+3 floor to a
prospect's potential inside each draft class it processed, so it was a property
of a transform rather than of the archive: seven files kept 68-133 prospects
under it, 2007 kept 496 and 2026 kept 75, and the retrofit could not write a
gate for it because the archive did not hold the property. Ryan ruled it
archive-wide, which is what makes it checkable.

THE PROPERTY: a prospect's potential is at least his rating plus three. A
prospect whose ceiling is his current rating is not a prospect; the draft board
reads him as a man with nothing to come.

GROWTH CURVES ARE REBUILT for every man whose potential moves, because the
archive enforces the 50x rule in every cohort — the positive slots of
growthType sum to (potential - rating) * 50 — and raising potential without
rebuilding the curve fails the roster gate at once. The curve is rebuilt with
outcome_ceilings' own build_growth, seeded per man on iden so a re-run is
identical, and the negative decline slots are drawn the same way they are
everywhere else in the archive.

THE 99 CEILING is respected: potential is capped there. Measured before
writing, no prospect in any of the ten files is rated above 86, so the cap
binds on nobody and no man is silently held under the floor. If a future file
carries a prospect above 96 the cap wins and the gate exempts exactly those men.
"""
import json, os, sys, random, subprocess, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
import importlib.util
_s = importlib.util.spec_from_file_location(
    'oc', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outcome_ceilings.py'))
oc = importlib.util.module_from_spec(_s); _s.loader.exec_module(oc)

YEARS = [1979, 1986, 2000, 2004, 2007, 2010, 2013, 2017, 2021, 2026]
FLOOR = 3
CEILING = 99


def run(y, dry):
    path = f'PGMRoster_{y}.json'
    head = subprocess.run(['git', 'show', f'HEAD:{path}'],
                          capture_output=True, text=True, cwd=repo('')).stdout
    ser = ((lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else ''))
           if head.count('\n') > 1 else (lambda d: json.dumps(d, separators=(', ', ': '))))
    assert ser(json.loads(head)) == head, f'{y}: stored formatting not reproduced'

    d = json.load(open(repo(path)))
    rk = [p for p in d if p.get('teamID') == 'Rookie']
    need = [p for p in rk if p['potential'] < min(p['rating'] + FLOOR, CEILING)]
    held = [p for p in rk if p['rating'] + FLOOR > CEILING]
    moved = 0
    for p in need:
        tgt = min(p['rating'] + FLOOR, CEILING)
        p['potential'] = tgt
        rng = random.Random(f"{p['iden']}|prospect_floor")
        p['growthType'] = oc.build_growth(p['potential'], p['rating'], rng, n_slots=len(p['growthType']))
        assert sum(x for x in p['growthType'] if x > 0) == (p['potential'] - p['rating']) * 50
        assert len(p['growthType']) == 31
        moved += 1
    gaps = [p['potential'] - p['rating'] for p in rk]
    print(f'  {y}: prospects {len(rk):>4}  raised {moved:>4}  '
          f'min gap now {min(gaps)}  median {sorted(gaps)[len(gaps)//2]}  '
          f'max rating among raised {max([p["rating"] for p in need], default=0)}'
          + (f'  [{len(held)} held at the 99 ceiling]' if held else ''))
    if not dry and moved:
        open(repo(path), 'w').write(ser(d))
    return moved


def main():
    dry = '--dry-run' in sys.argv
    years = [int(a) for a in sys.argv[1:] if a.isdigit()] or YEARS
    print(f'prospect potential floor: rating + {FLOOR}, capped at {CEILING}'
          + ('   DRY RUN' if dry else ''))
    tot = sum(run(y, dry) for y in years)
    print(f'  {tot} prospects raised across {len(years)} file(s)'
          + ('' if dry else ' — written'))


if __name__ == '__main__':
    main()
