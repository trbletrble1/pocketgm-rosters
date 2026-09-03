#!/usr/bin/env python3
"""
rename_generated_staff — generated staff names must not resemble real people.
Ruled 2026-09-03.

  python3 tools/rename_generated_staff.py --dry-run
  python3 tools/rename_generated_staff.py

THE DEFECT. The generator drew invented forenames onto real football surnames —
Rich Dungy, Garo Whitehurst, Elvin Thurman — which reads as a real person
misremembered, worse than an obviously fake name. Under a literal rule (no
surname in the archive) 1,979 of 2,888 generated staff collide, but that rule
catches Dennis Wilson and cannot tell him from Rich Dungy. What makes a name
read as a specific person is DISTINCTIVENESS, not presence.

THE RARITY RULE, both fields. Against 23,056 distinct football people held
(ten files plus the PFR listings 1960-2025): a surname or forename borne by
1-14 of them is dropped from the pool; 15+ (essentially the Census top-100)
stays; 0 — not football — stays, and the surnames there skew Cadwallader-Belvoir,
which is the acceptable failure. A NOTABLE BLOCK — Hall of Fame coaches and
players, and a short celebrity list — is a hard block regardless of count.
Junk stripped ('Assistant' was a forename; 'No' and 'Oh' were surnames).

THE RENAME SCOPE, because an inference that flags George Allen and Hal Hunter
as generated (George, Allen, Hal, Hunter are all in the invented lists) would
rename real men: 1979 renames from the exact provenance CSV; the other nine
rename scouts and physios (the standing exception, always invented) plus
coordinators who fail every real source AND carry a distinctive-class name.
Common-named coordinators stay. New names are deterministic by iden, unique
within the file, and never a real name.

THE SIDECAR. reference/PGM3_STAFF_PROVENANCE.csv — one row per staff record
per file: exact for 1979, inferred elsewhere and marked as such. The 72-key
schema is vanilla's exactly and is not touched.
"""
import json, csv, os, sys, re, glob, random, unicodedata, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources
YEARS = ['1979', '1986', '2000', '2004', '2007', '2010', '2013', '2017', '2021', '2026']
GEN_ROLES = {'Head Scout', 'Off Scout', 'Def Scout', 'Head Physio', 'Assistant Physio'}
COORD = {'Off Co-ord', 'Def Co-ord', 'Special Teams'}
NOTABLE = set(map(str.lower, """Halas Lombardi Landry Shula Noll Walsh Belichick Parcells Gibbs Madden Brown Allen Ditka Levy Reeves Holmgren Dungy
Cowher Coughlin Johnson Seifert Stram Grant Knox Flores Ewbank Lambeau Neale Owen Bell Marchibroda Vermeil Schottenheimer
Unitas Starr Namath Staubach Bradshaw Montana Marino Elway Favre Manning Brady Rodgers Brees Payton Sanders Sayers Simpson
Campbell Dorsett Dickerson Tomlinson Rice Moss Owens Largent Lofton Winslow Gonzalez Munoz Ogden Jones Hannah Webster
Butkus Singletary Lambert Ham Taylor Lewis Urlacher Nitschke Greene Page Olsen White Smith Strahan Tatum Lott Blount
Haynes Woodson Deion Yepremian Stenerud Groza Guy Lechler Hutson Grange Nagurski Thorpe Baugh Layne Tittle Jurgensen Kelly
Aikman Young Warner Kurt Manning Peyton Eli Watt Donald Garrett Mahomes Allen Josh Burrow Hurts
Presley Sinatra Jagger Lennon McCartney Dylan Springsteen Bowie Hendrix Cobain Jackson Madonna Beyonce Swift Eminem
Clinton Reagan Nixon Carter Bush Obama Trump Biden Kennedy Lincoln Roosevelt Eisenhower Truman Jefferson Washington
Spielberg Hitchcock Kubrick Tarantino Scorsese Eastwood Brando DeNiro Pacino Nicholson Streep Hepburn Monroe Bogart
Jordan Ali Ruth Gretzky Woods Federer Serena Bolt Pele Maradona Messi Ronaldo LeBron Kobe Shaq Mantle DiMaggio
Einstein Newton Darwin Hawking Curie Tesla Edison Gates Jobs Musk Bezos Zuckerberg Buffett Rockefeller Carnegie Ford
Oprah Kardashian Hilton Cosby Seinfeld Letterman Carson Leno Colbert Stewart Fallon Kimmel""".split()))
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower(); return ' '.join(re.sub(r'[^a-z ]', '', s).split())

def main():
    dry = '--dry-run' in sys.argv
    # --- the population that decides distinctiveness
    people = set()
    for y in YEARS:
        for x in json.load(open(repo(f'PGMRoster_{y}.json'))): people.add(norm(x['forename'] + ' ' + x['surname']))
    for p in glob.glob(repo('wip', 'draft_*_pfr.csv')):
        for r in csv.DictReader(open(p)): people.add(norm(r['name']))
    sur_n = collections.Counter(n.split()[-1] for n in people if n); fore_n = collections.Counter(n.split()[0] for n in people if n)
    distinctive = lambda w, cnt: 1 <= cnt[norm(w)] <= 14 or norm(w) in NOTABLE
    # --- rebuild the pool
    pool = json.load(open(repo('wip', 'staff_name_pool.json')))
    junk_f = {'Assistant', 'Oh', 'No'}; junk_s = {'No', 'Oh'}
    clean_f = sorted({f for f in pool['forenames'] if f not in junk_f and re.fullmatch(r"[A-Z][A-Za-z']+", f) and not distinctive(f, fore_n)})
    clean_s = sorted({s.strip() for s in pool['surnames'] if s.strip() not in junk_s and re.fullmatch(r"[A-Z][A-Za-z'\-]+", s.strip()) and not distinctive(s.strip(), sur_n)})
    print(f"pool: forenames {len(pool['forenames'])} -> {len(clean_f)}, surnames {len(pool['surnames'])} -> {len(clean_s)} (dropped 1-14-bearer and notable; junk stripped)")
    # --- real-name sources
    real = set()
    for fn in ('coach_birth_years.csv', 'coach_birth_years_2026.csv', 'coaches_2000.csv'):
        for r in csv.DictReader(open(os.path.join(sources(), fn))): real.add(norm(r['name']))
    for p in glob.glob(repo('wip', '*coach*.csv')):
        for r in csv.DictReader(open(p)):
            for k in ('name', 'coach'):
                if r.get(k): real.add(norm(r[k]))
    real |= {n for n in people}
    prov79 = {}
    for r in csv.DictReader(open(repo('wip', 'staff_1979.csv'))): prov79[norm(r['forename'] + ' ' + r['surname'])] = r['provenance']
    pool79 = {norm(r['name']) for r in csv.DictReader(open(repo('wip', 'coach_pool_1979.csv')))}
    old_f, old_s = set(pool['forenames']), set(pool['surnames'])
    # --- sidecar + rename
    # a new name must not match ANY existing staff name in ANY file — the first
    # run seeded this with real sources and players only, and 25 new names matched
    # kept staff elsewhere, which the faces gate (keyed on name) read as 25 new
    # multi-season people.
    taken_global = set(real)
    for y in YEARS:
        for x in json.load(open(repo(f'PGMStaff_{y}.json'))): taken_global.add(norm(x['forename'] + ' ' + x['surname']))
    side = []
    summary = collections.Counter(); faces_key_changes = 0
    for y in YEARS:
        fn = f'PGMStaff_{y}.json'; head = subprocess.run(['git', 'show', f'HEAD:{fn}'], capture_output=True, text=True, cwd=repo('')).stdout
        ser = (lambda d: json.dumps(d, indent=1) + ('\n' if head.endswith('\n') else '')) if head.count('\n') > 1 else \
              next((lambda f: lambda d: f(d))(f) for f in (lambda d: json.dumps(d, separators=(', ', ': ')), lambda d: json.dumps(d, separators=(',', ':')), lambda d: json.dumps(d, separators=(',', ':'), ensure_ascii=False), lambda d: json.dumps(d)) if f(json.loads(head)) == head)
        d = json.load(open(repo(fn))); used = {norm(x['forename'] + ' ' + x['surname']) for x in d}
        for x in d:
            n = norm(x['forename'] + ' ' + x['surname']); role = x['role']
            if y == '1979':
                if n in prov79: prov, how = ('invented' if prov79[n].startswith('invented') else prov79[n]), 'exact (wip/staff_1979.csv)'
                elif n in pool79: prov, how = 'sourced (coach pool, PFR)', 'exact (wip/coach_pool_1979.csv)'
                else: prov, how = 'invented', 'exact (generated pool, batch 4)'
            else:
                if n in real: prov, how = 'real (name in a real source)', 'inferred'
                elif role in GEN_ROLES: prov, how = 'invented (scout/physio, the standing exception)', 'inferred'
                elif x['forename'] in old_f and x['surname'] in old_s: prov, how = 'invented (both names from the invented lists, no real source)', 'inferred'
                else: prov, how = 'unknown (no real source, not from the invented lists)', 'inferred'
            rename = prov.startswith('invented') and (y == '1979' or role in GEN_ROLES or (role in COORD and (distinctive(x['forename'], fore_n) or distinctive(x['surname'], sur_n))))
            new_name = ''
            if rename and (distinctive(x['forename'], fore_n) or distinctive(x['surname'], sur_n) or x['forename'] in junk_f or x['surname'] in junk_s or y == '1979' and (x['forename'] not in clean_f or x['surname'] not in clean_s)):
                rng = random.Random(f"{x['iden']}|rename")
                for _ in range(500):
                    cand = f"{rng.choice(clean_f)} {rng.choice(clean_s)}"
                    if norm(cand) not in taken_global and norm(cand) not in used: break
                used.add(norm(cand)); taken_global.add(norm(cand)); new_name = cand
                summary[y] += 1
            elif rename: summary[y + ' kept (already clean)'] += 1
            side.append({'file': y, 'iden': x['iden'], 'role': role, 'teamID': x['teamID'], 'name_before': f"{x['forename']} {x['surname']}", 'name_after': new_name or f"{x['forename']} {x['surname']}", 'provenance': prov, 'how': how})
            if new_name: x['forename'], x['surname'] = new_name.split()[0], ' '.join(new_name.split()[1:])
        if not dry: open(repo(fn), 'w').write(ser(d))
    print("renamed per file: " + ', '.join(f"{y}: {summary[y]}" for y in YEARS) + f"   (already clean and kept: {sum(v for k, v in summary.items() if 'kept' in k)})")
    print("provenance rows: " + str(dict(collections.Counter(r['provenance'].split(' (')[0] for r in side))))
    if not dry:
        with open(repo('reference', 'PGM3_STAFF_PROVENANCE.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(side[0].keys())); w.writeheader(); w.writerows(side)
        pool['forenames'], pool['surnames'] = clean_f, clean_s
        json.dump(pool, open(repo('wip', 'staff_name_pool.json'), 'w'), indent=1)
        print("wrote ten staff files, reference/PGM3_STAFF_PROVENANCE.csv, wip/staff_name_pool.json")
    else: print('--dry-run: nothing written')

if __name__ == '__main__':
    main()
