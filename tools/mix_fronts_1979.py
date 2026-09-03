#!/usr/bin/env python3
"""
mix_fronts_1979 — DELIBERATE VARIANCE, NOT SOURCED. Ruled 2026-09-03.

Every 1979 team ran a 4-3 in our file because no source names each team's
front and a uniform wrong answer beat a heuristic one. Ryan wants variance
rather than accuracy: roughly a quarter of teams switch to a 3-4, chosen by a
hash of the head coach's iden so it reproduces. Era-plausible — New England
and the Jets ran it in 1979 and it spread through the early eighties — but NOT
a claim about any team. The Man/Zone suffix is kept; every sitting man on the
team moves together, as vanilla's staff mostly do (HC and DC agree on 26/32).

The earlier ruling was that a wrong 3-4 is worse than a uniform 4-3; this
reverses it on the grounds that the game plays better with variety — a
different criterion, not new evidence.
"""
import json, os, sys, hashlib, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
SHARE = 0.25
def main():
    dry = '--dry-run' in sys.argv
    head = subprocess.run(['git', 'show', 'HEAD:PGMStaff_1979.json'], capture_output=True, text=True, cwd=repo('')).stdout
    assert json.dumps(json.loads(head), indent=1) + ('\n' if head.endswith('\n') else '') == head
    d = json.load(open(repo('PGMStaff_1979.json')))
    hc = {x['teamID']: x for x in d if x['role'] == 'Head Coach' and x['teamID'] != 'Free Agent'}
    teams = sorted(hc); k = max(1, round(len(teams) * SHARE))
    ranked = sorted(teams, key=lambda t: int(hashlib.md5(f"{hc[t]['iden']}|fronts".encode()).hexdigest(), 16))
    pick = set(ranked[:k]); moved = 0
    for x in d:
        if x['teamID'] in pick and x['defStyle'].startswith('4-3'):
            x['defStyle'] = '3-4' + x['defStyle'][3:]; moved += 1
    print(f"  3-4 teams ({k} of {len(teams)}): {', '.join(sorted(pick))}; records moved {moved}; fronts now {dict(collections.Counter(x['defStyle'] for x in d if x['teamID'] != 'Free Agent'))}")
    if dry: print('  --dry-run'); return
    open(repo('PGMStaff_1979.json'), 'w').write(json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')); print('  wrote PGMStaff_1979.json')
if __name__ == '__main__': main()
