#!/usr/bin/env python3
"""
fix_staff_money — four fields the game populates and ours left empty. Ruled
2026-09-03, one pass, from the coverage sweep.

  python3 tools/fix_staff_money.py --dry-run
  python3 tools/fix_staff_money.py

1. FREE-AGENT STAFF ASKING PRICE, 1979 only (219 of 219 at eSalary 0; the other
   nine populate it). THE GOING RATE BY (ROLE, RATING BAND) from vanilla's
   employed salaries — NOT vanilla's flat $0.20M. In the game's own file the
   flat ask and the going rate are the same number, because its pool is 57-69
   rated men and $0.20M is the going rate for that band. Copying the literal
   value into a pool holding Paul Brown at 88 imports a number that was never
   meant to price him — the same trap as the position band and the payroll
   constant: correct in the source population, wrong in ours. eLength 1,
   eGuarantee 0, as vanilla's free agents carry.
2. EMPLOYED STAFF eGuarantee, nine files (85-100% empty against vanilla's 50%).
   A SPLIT of the extension ask, total held: eGuarantee = (eSalary+eGuarantee)
   x a ratio drawn from vanilla's (median 0.33), eSalary the remainder. Who
   gets one follows vanilla: every man on an extension of four years or more,
   otherwise by rating band at vanilla's share.
3. EMPLOYED STAFF guarantee, 1979 and 2010 (100% / 89% empty against 50%).
   Same split of salary+guarantee, total held; vanilla gives it to every
   multi-year man and to one-year men by rating band (60s 11%, 70s 65%,
   80+ 100%).
4. ROSTERED PLAYER guarantee, 2017 (72% empty against 40%). Same split of
   salary+guarantee, total held; presence by contract length at vanilla's
   share (1-year 38%, 2-year 85%, 3+ 100%), ratio from vanilla's by length.

TOTAL COMPENSATION DOES NOT MOVE: salary+guarantee and eSalary+eGuarantee are
asserted unchanged on every record touched, so payroll, ordering and every
guard are untouched by construction. Nobody who already had a guarantee loses
it or has it changed.
"""
import json, os, sys, random, collections, statistics as st, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
V = os.path.join(sources(), 'vanilla')
YEARS = ['1979', '1986', '2000', '2004', '2007', '2010', '2013', '2017', '2021', '2026']
def band(r): return '<60' if r < 60 else '60s' if r < 70 else '70s' if r < 80 else '80+'
CANDS = [lambda d: json.dumps(d, separators=(', ', ': ')), lambda d: json.dumps(d, separators=(',', ':')),
         lambda d: json.dumps(d, separators=(',', ':'), ensure_ascii=False), lambda d: json.dumps(d),
         lambda d: json.dumps(d, indent=1), lambda d: json.dumps(d, indent=2)]
def serialiser(head):
    for f in CANDS:
        for nl in ('', '\n'):
            if f(json.loads(head)) + nl == head: return (lambda f, nl: lambda d: f(d) + nl)(f, nl)
    raise AssertionError('stored formatting not reproduced')
def pick(rng, arr): return arr[min(len(arr) - 1, int(rng.random() * len(arr)))]

def main():
    dry = '--dry-run' in sys.argv
    vs = json.load(open(os.path.join(V, 'PGMStaff_vanilla_2026-09-03.json'))); ve = [x for x in vs if x['teamID'] != 'Free Agent']
    vr = [x for x in json.load(open(os.path.join(V, 'PGMRoster_vanilla_2026-09-03.json'))) if x['teamID'] not in ('Rookie', 'Free Agent')]
    # vanilla tables
    rate = collections.defaultdict(list); rate_b = collections.defaultdict(list)
    for x in ve: rate[(x['role'], band(x['rating']))].append(x['salary']); rate_b[band(x['rating'])].append(x['salary'])
    ORDER = ['<60', '60s', '70s', '80+']
    def going(x):
        # vanilla employs nobody under 60; a 1979 pool man at 32-59 takes the 60s going rate
        b = band(x['rating']); v = rate[(x['role'], b)]
        if len(v) >= 5: return st.median(v)
        if rate_b[b]: return st.median(rate_b[b])
        return st.median(rate_b[min((q for q in ORDER if rate_b[q]), key=lambda q: abs(ORDER.index(q) - ORDER.index(b)))])
    g_share = {b: sum(1 for x in ve if band(x['rating']) == b and x['length'] == 1 and x['guarantee'] > 0) / max(1, sum(1 for x in ve if band(x['rating']) == b and x['length'] == 1)) for b in ('<60', '60s', '70s', '80+')}
    g_ratio = sorted(x['guarantee'] / (x['salary'] + x['guarantee']) for x in ve if x['guarantee'] > 0)
    eg_share = {b: sum(1 for x in ve if band(x['rating']) == b and x['eLength'] < 4 and x['eGuarantee'] > 0) / max(1, sum(1 for x in ve if band(x['rating']) == b and x['eLength'] < 4)) for b in ('<60', '60s', '70s', '80+')}
    eg_ratio = sorted(x['eGuarantee'] / (x['eSalary'] + x['eGuarantee']) for x in ve if x['eGuarantee'] > 0)
    pg_share = {l: sum(1 for x in vr if x['length'] == l and x['guarantee'] > 0) / max(1, sum(1 for x in vr if x['length'] == l)) for l in range(0, 8)}
    pg_ratio = {l: sorted(x['guarantee'] / (x['salary'] + x['guarantee']) for x in vr if x['length'] == l and x['guarantee'] > 0) for l in range(0, 8)}
    pg_all = sorted(x['guarantee'] / (x['salary'] + x['guarantee']) for x in vr if x['guarantee'] > 0)
    vz = lambda rows, k: sum(1 for x in rows if not x[k]) / len(rows)
    print(f"vanilla empty shares — staff employed: guarantee {vz(ve,'guarantee'):.0%}, eGuarantee {vz(ve,'eGuarantee'):.0%};  rostered players: guarantee {vz(vr,'guarantee'):.0%}\n")
    for y in YEARS:
        for kind in ('Staff', 'Roster'):
            fn = f'PGM{kind}_{y}.json'
            head = subprocess.run(['git', 'show', f'HEAD:{fn}'], capture_output=True, text=True, cwd=repo('')).stdout
            ser = serialiser(head); d = json.load(open(repo(fn))); touched = 0; log = []
            if kind == 'Staff':
                emp = [x for x in d if x['teamID'] != 'Free Agent']; fa = [x for x in d if x['teamID'] == 'Free Agent']
                # 1. free-agent asks (only where empty)
                n = 0
                for x in fa:
                    if x['eSalary'] == 0:
                        x['eSalary'] = int(round(going(x))); x['eLength'] = 1; x['eGuarantee'] = 0; n += 1
                if n: log.append(f"FA asks set on {n}: HC med ${st.median(x['eSalary'] for x in fa if x['role']=='Head Coach')/1e6:.2f}M, max ${max(x['eSalary'] for x in fa)/1e6:.2f}M ({max(fa,key=lambda x:x['eSalary'])['surname']})")
                # 2. eGuarantee split on employed, where the file is emptier than the game
                if vz(emp, 'eGuarantee') - vz(ve, 'eGuarantee') >= 0.15:
                    b0 = vz(emp, 'eGuarantee'); n = 0
                    for x in emp:
                        if x['eGuarantee'] or x['eSalary'] <= 0: continue
                        rng = random.Random(f"{x['iden']}|{y}|eg")
                        if x['eLength'] >= 4 or rng.random() < eg_share[band(x['rating'])]:
                            tot = x['eSalary'] + x['eGuarantee']; x['eGuarantee'] = int(round(tot * pick(rng, eg_ratio))); x['eSalary'] = tot - x['eGuarantee']; n += 1
                    log.append(f"eGuarantee split on {n} employed: empty {b0:.0%} -> {vz(emp,'eGuarantee'):.0%} (vanilla {vz(ve,'eGuarantee'):.0%})")
                # 3. guarantee split on employed
                if vz(emp, 'guarantee') - vz(ve, 'guarantee') >= 0.15:
                    b0 = vz(emp, 'guarantee'); n = 0
                    for x in emp:
                        if x['guarantee'] or x['salary'] <= 0: continue
                        rng = random.Random(f"{x['iden']}|{y}|g")
                        if x['length'] >= 2 or rng.random() < g_share[band(x['rating'])]:
                            tot = x['salary'] + x['guarantee']; x['guarantee'] = int(round(tot * pick(rng, g_ratio))); x['salary'] = tot - x['guarantee']; n += 1
                    log.append(f"guarantee split on {n} employed: empty {b0:.0%} -> {vz(emp,'guarantee'):.0%} (vanilla {vz(ve,'guarantee'):.0%})")
            else:
                ros = [x for x in d if x['teamID'] not in ('Rookie', 'Free Agent')]
                if vz(ros, 'guarantee') - vz(vr, 'guarantee') >= 0.15:
                    b0 = vz(ros, 'guarantee'); n = 0
                    for x in ros:
                        if x['guarantee'] or x['salary'] <= 0: continue
                        rng = random.Random(f"{x['iden']}|{y}|pg"); l = min(7, x['length'])
                        if rng.random() < pg_share.get(l, 1.0):
                            tot = x['salary'] + x['guarantee']; x['guarantee'] = int(round(tot * pick(rng, pg_ratio.get(l) or pg_all))); x['salary'] = tot - x['guarantee']; n += 1
                    log.append(f"guarantee split on {n} rostered: empty {b0:.0%} -> {vz(ros,'guarantee'):.0%} (vanilla {vz(vr,'guarantee'):.0%})")
            if not log: continue
            # TOTAL COMPENSATION HELD — assert against HEAD on every record
            old = {x['iden']: x for x in json.loads(head)}
            for x in d:
                o = old[x['iden']]
                if kind == 'Staff' and x['teamID'] == 'Free Agent' and o['eSalary'] == 0: continue   # the new asks
                assert x['salary'] + x['guarantee'] == o['salary'] + o['guarantee'], (fn, x['surname'])
                assert x['eSalary'] + x['eGuarantee'] == o['eSalary'] + o['eGuarantee'], (fn, x['surname'])
            print(f"=== {fn} ===\n   " + '\n   '.join(log) + "\n   total compensation held on every record (asserted against HEAD)")
            if not dry: open(repo(fn), 'w').write(ser(d)); print(f"   wrote {fn}")
    if dry: print('\n--dry-run: nothing written')

if __name__ == '__main__':
    main()
