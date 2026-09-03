#!/usr/bin/env python3
"""
cap_rating_98 — the six 2026 men computed above 98. Ruled 2026-09-03.

  python3 tools/cap_rating_98.py --dry-run
  python3 tools/cap_rating_98.py

Not a data defect: attributes clamp at 99 but the rating computed from them
never did, and these six are elite in the attributes their position weights
hardest (Folk: accuracy 99 at 1.04 and power 92 at 0.59). No file has ever
exceeded 98 and the game does not either (vanilla max 98; potential max 99).

Stored rating capped at 98, and enough LOW-WEIGHT attribute moved so the formula
computes 98 too — lowest |weight| first, moved in whichever direction LOWERS the
rating (a negative weight is raised, not shaved). BOUNDED: no attribute moves
more than 10 points, and injuryProne and discipline are never touched — they
carry almost no rating weight but they are gameplay, and the first draft drove
Garrett's injuryProne 13 -> 99 and Parsons' discipline 99 -> 1 to buy two
points. If the bounded low-weight fields cannot reach 98 the tool escalates to
the next-lowest weight, still bounded, and prints every move. Potential capped
at the game's 99; growthType rebuilt on the 50x rule.
"""
import json, os, sys, random, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo
KW = json.load(open(repo('wip', 'PGM3_2026_build_data.json')))['weights']
CAP, TARGET = 98, 98.49
def formula(x):
    names, w = KW[x['position']]; return sum(x[a] * c for a, c in zip(names, w[:-1])) + w[-1]
def build_growth(potential, rating, rng, n_slots=31):
    gt = [0] * n_slots; need = (potential - rating) * 50
    if need > 0:
        slots = rng.sample(range(0, 20), min(8, max(1, need // 100 or 1))); per = need // len(slots)
        for i, s in enumerate(slots): gt[s] = per if i else need - per * (len(slots) - 1)
    for s in rng.sample(range(20, n_slots), rng.randint(3, min(8, n_slots - 21))): gt[s] = -100 * rng.randint(1, 3)
    return gt

def main():
    dry = '--dry-run' in sys.argv
    head = subprocess.run(['git', 'show', 'HEAD:PGMRoster_2026.json'], capture_output=True, text=True, cwd=repo('')).stdout
    assert json.dumps(json.loads(head), separators=(', ', ': ')) == head
    d = json.load(open(repo('PGMRoster_2026.json')))
    for x in [z for z in d if z['rating'] > CAP or formula(z) > TARGET]:
        names, w = KW[x['position']]; moves = []
        for a, c in sorted(zip(names, w[:-1]), key=lambda t: abs(t[1])):
            if c == 0 or a in ('injuryProne', 'discipline') or formula(x) <= TARGET: continue
            step = -1 if c > 0 else 1                      # lower a positive weight, raise a negative one
            start = x[a]
            while formula(x) > TARGET and 1 <= x[a] + step <= 99 and abs(x[a] + step - start) <= 10: x[a] += step
            if x[a] != start: moves.append(f"{a} {start}->{x[a]} (w {c:+.3f})")
        assert formula(x) <= TARGET, x['surname']
        was = x['rating']; x['rating'] = CAP; x['potential'] = min(99, max(x['potential'], CAP)) if x['potential'] > 99 else max(x['potential'], CAP)
        x['growthType'] = build_growth(x['potential'], x['rating'], random.Random(f"{x['iden']}|cap98"), 31)
        print(f"  {x['forename']} {x['surname']:<14} {x['position']:>3} {was} -> {x['rating']} (formula {formula(x):.2f}), potential {x['potential']};  moved: " + '; '.join(moves))
    assert not any(z['rating'] > CAP for z in d) and not any(z['potential'] > 99 for z in d)
    if dry: print('  --dry-run: nothing written'); return
    open(repo('PGMRoster_2026.json'), 'w').write(json.dumps(d, separators=(', ', ': '))); print('  wrote PGMRoster_2026.json')

if __name__ == '__main__':
    main()
