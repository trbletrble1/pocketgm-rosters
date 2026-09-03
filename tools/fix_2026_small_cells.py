#!/usr/bin/env python3
"""
fix_2026_small_cells — item 45, source (1). Ruled 2026-09-03.

  python3 tools/fix_2026_small_cells.py --dry-run
  python3 tools/fix_2026_small_cells.py

build_2026's assign_money ranks each man inside his (position, length) cell and
maps rank to a quantile as q = i / max(1, n-1). A cell of ONE gives q = 0 and the
man lands on the pool's minimum: Josh Allen is the only six-year quarterback in
the file and earned $0.12M while Madden carried $37.1M. A cell of two puts one
man at q = 0 and the other at q = 1 — the same defect one step milder.

MEASURED ACROSS ALL TEN FILES: only 2026 was built with that builder and only
2026 shows it. 41 rostered men sit in 22 cells of fewer than five; 22 of them
are under $500K (10 of 10 singletons, 7 of 14 in cells of two, 3 of 9 in three,
2 of 8 in four). The other 93 sub-$500K men are the pool-floor placeholders,
item 45 source (2), and are NOT touched here.

THE FIX. A cell with no rank to preserve is not mapped to a quantile. A man in a
cell of fewer than five whose pay sits BELOW the game's median for his position
and rating band (+-5, vanilla's own rostered men) is lifted to it. LIFT ONLY:
the defect is q = 0 landing on the floor; the man at q = 1 in a cell of two is
at worst generous, and cutting Maxx Crosby from $37.5M to a band median was the
first draft's mistake. The reference is VANILLA's median, not the file's — the
file's 85+ median is the compressed top (item 45 source 3) and would have put
Josh Allen at $10.5M against the game's $20.8M for his band. Madden's value is
printed beside each man for the record but is not used: measured earlier today
it is a stale proxy (Zack Baun at $2.4M after signing for $17M a year).

The re-pricing lifts team totals, so tools/raise_payroll.py 2026 runs after it
to put the level back on the game's exactly (uniform per-team scale, ordering
exact). Extension terms scale with the man.
"""
import json, csv, os, sys, re, unicodedata, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' '.join(w for w in re.sub(r'[^a-z ]', '', s).split() if w not in {'jr', 'sr', 'ii', 'iii', 'iv', 'v'})
pay = lambda x: x['salary'] + x['guarantee']
SMALL = 5

def main():
    dry = '--dry-run' in sys.argv
    head = subprocess.run(['git', 'show', 'HEAD:PGMRoster_2026.json'], capture_output=True, text=True, cwd=repo('')).stdout
    assert json.dumps(json.loads(head), separators=(', ', ': ')) == head
    d = json.load(open(repo('PGMRoster_2026.json'))); r = [x for x in d if x['teamID'] not in ('Rookie', 'Free Agent')]
    cells = collections.Counter((x['position'], x['length']) for x in r)
    van = [x for x in json.load(open(os.path.join(sources(), 'vanilla', 'PGMRoster_vanilla_2026-09-03.json'))) if x['teamID'] not in ('Rookie', 'Free Agent')]
    mad = {}
    for row in csv.DictReader(open(os.path.join(sources(), 'madden', '2025JINXROSTER V21 - PLAY.csv'), encoding='utf-8', errors='replace')):
        mad.setdefault(norm(row['PFNA'] + ' ' + row['PLNA']), float(row['PTSA'] or 0) * 1000)
    def ref(x):
        # widen the band until eight peers exist; a 96-rated man reaches past
        # vanilla's maximum rating of 89, so +-5 alone can be empty
        for w in (5, 8, 12, 20, 40):
            peers = [pay(z) for z in van if z['position'] == x['position'] and abs(z['rating'] - x['rating']) <= w]
            if len(peers) >= 8: return st.median(peers)
        for w in (5, 8, 12, 20, 40):
            peers = [pay(z) for z in van if abs(z['rating'] - x['rating']) <= w]
            if len(peers) >= 8: return st.median(peers)
        return st.median(pay(z) for z in van)
    fixed = []
    for x in sorted(r, key=lambda x: -x['rating']):
        n = cells[(x['position'], x['length'])]
        if n >= SMALL: continue
        was = pay(x); new = int(round(ref(x))); g = x['guarantee'] / was if was else 0.05
        if was >= new: continue                                  # lift only
        f = new / was if was else 1.0
        x['guarantee'] = int(round(new * g)); x['salary'] = new - x['guarantee']
        x['eSalary'] = int(round(x['eSalary'] * f)); x['eGuarantee'] = int(round(x['eGuarantee'] * f))
        fixed.append((x, n, was, new, mad.get(norm(x['forename'] + ' ' + x['surname']))))
    print(f"  {sum(1 for x in r if cells[(x['position'], x['length'])] < SMALL)} men in cells under {SMALL}; {len(fixed)} sat below the game's position-and-band median and are lifted to it")
    for x, n, was, new, m in fixed[:12]:
        print(f"    {x['forename']+' '+x['surname']:<20} {x['position']:>3} {x['rating']:>3} age {x['age']:>2}  cell n={n}  ${was/1e6:>5.2f}M -> ${new/1e6:>5.2f}M   (Madden {'$%.1fM' % (m/1e6) if m else '—'})")
    u5 = sum(1 for x in r if pay(x) < 5e5); stars = sum(1 for x in r if x['rating'] >= 85 and x['age'] >= 26 and pay(x) < 2e6)
    print(f"  under $500K now {u5} (was 115; the remaining are pool-floor placeholders, source 2); 85+/26+/<$2M now {stars} (was 21)")
    if dry: print('  --dry-run: nothing written'); return
    open(repo('PGMRoster_2026.json'), 'w').write(json.dumps(d, separators=(', ', ': '))); print('  wrote PGMRoster_2026.json — now run tools/raise_payroll.py 2026 to restore the level')

if __name__ == '__main__':
    main()
