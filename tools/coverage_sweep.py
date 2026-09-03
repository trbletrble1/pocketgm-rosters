#!/usr/bin/env python3
"""
coverage_sweep — every field, both files, against the game: the share that is
zero or empty in ours against the share in vanilla, per cohort.

  python3 tools/coverage_sweep.py                 # all ten seasons
  python3 tools/coverage_sweep.py 1979 2026       # some
  python3 tools/coverage_sweep.py --gap 0.10      # flag threshold (default 0.15)

WHY. A field present in the schema and empty in the data does not error and
does not gate. Three instances were found one at a time — free-agent player
extension terms, free-agent staff asking prices, car_av in the 2000 draft file
— before this was written as the general form; its first run found the fourth
(employed staff eGuarantee, nine files). Run it whenever a file is built.
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
V = os.path.join(sources(), 'vanilla')
COHORTS = [('Roster', 'PGMRoster_vanilla_2026-09-03.json', 'rostered', lambda x: x['teamID'] not in ('Rookie', 'Free Agent')),
           ('Roster', 'PGMRoster_vanilla_2026-09-03.json', 'free agents', lambda x: x['teamID'] == 'Free Agent'),
           ('Roster', 'PGMRoster_vanilla_2026-09-03.json', 'prospects', lambda x: x['teamID'] == 'Rookie'),
           ('Staff', 'PGMStaff_vanilla_2026-09-03.json', 'employed', lambda x: x['teamID'] != 'Free Agent'),
           ('Staff', 'PGMStaff_vanilla_2026-09-03.json', 'free agents', lambda x: x['teamID'] == 'Free Agent')]
def empty(v): return v in (0, '', None, []) or (isinstance(v, list) and all(q == 0 for q in v))

def main():
    years = [a for a in sys.argv[1:] if a.isdigit()] or ['1979', '1986', '2000', '2004', '2007', '2010', '2013', '2017', '2021', '2026']
    gap = float(sys.argv[sys.argv.index('--gap') + 1]) if '--gap' in sys.argv else 0.15
    hits = 0
    for kind, vfn, label, coh in COHORTS:
        van = [x for x in json.load(open(os.path.join(V, vfn))) if coh(x)]
        keys = [k for k in van[0] if k != 'iden']
        vz = {k: sum(1 for x in van if empty(x.get(k))) / len(van) for k in keys}
        byk = collections.defaultdict(list)
        for y in years:
            ours = [x for x in json.load(open(repo(f'PGM{kind}_{y}.json'))) if coh(x)]
            if not ours: continue
            for k in keys:
                oz = sum(1 for x in ours if empty(x.get(k))) / len(ours)
                if oz - vz[k] >= gap: byk[k].append((y, oz))
            for k in keys:
                if k not in ours[0]: byk['MISSING KEY ' + k].append((y, 1.0))
        print(f"{kind.upper()} — {label}: " + ('clean' if not byk else ''))
        for k, v in byk.items():
            hits += 1
            print(f"   {k:<14} vanilla empty {vz.get(k, 1.0):>4.0%}   ours: " + ', '.join(f"{y} {oz:.0%}" for y, oz in v))
    print(f"\n{hits} field/cohort pair(s) substantially emptier than the game" if hits else "\nnothing substantially emptier than the game")

if __name__ == '__main__':
    main()
