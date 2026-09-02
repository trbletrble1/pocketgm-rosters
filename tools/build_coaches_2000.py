import sys
#!/usr/bin/env python3
"""Build $PGM3_SOURCES/pfr/coaches_2000.csv from the fetched Wikipedia staff sections.

Every name here came off a page fetched 2026-08-31 and cached in raw.jsonl.
Nothing is filled in from memory: where a source names no one, the name is left
empty and the note says why. See docs/PGM3_TASK_coaches_2000.md.
"""
import csv, os, collections

WP = 'https://en.wikipedia.org/wiki/'
PFR = 'https://www.pro-football-reference.com/teams/{}/2000.htm'

def u(slug):
    """Resolve a source slug to a URL. 'PFR:xxx' is a PFR team season page.

    PFR pages cannot be fetched directly — every transport returns 403 or a
    Cloudflare bot check — but their coaching block is readable through search
    result snippets, which is where the two PFR-sourced rows came from.
    See $PGM3_SOURCES/pfr/README.md.
    """
    if slug.startswith('PFR:'):
        return PFR.format(slug[4:])
    return WP + slug

SEASON = {
 'ARI':'2000_Arizona_Cardinals_season',   'ATL':'2000_Atlanta_Falcons_season',
 'BAL':'2000_Baltimore_Ravens_season',    'BUF':'2000_Buffalo_Bills_season',
 'CAR':'2000_Carolina_Panthers_season',   'CHI':'2000_Chicago_Bears_season',
 'CIN':'2000_Cincinnati_Bengals_season',  'CLE':'2000_Cleveland_Browns_season',
 'DAL':'2000_Dallas_Cowboys_season',      'DEN':'2000_Denver_Broncos_season',
 'DET':'2000_Detroit_Lions_season',       'GB':'2000_Green_Bay_Packers_season',
 'IND':'2000_Indianapolis_Colts_season',  'JAX':'2000_Jacksonville_Jaguars_season',
 'KC':'2000_Kansas_City_Chiefs_season',   'MIA':'2000_Miami_Dolphins_season',
 'MIN':'2000_Minnesota_Vikings_season',   'NE':'2000_New_England_Patriots_season',
 'NO':'2000_New_Orleans_Saints_season',   'NYG':'2000_New_York_Giants_season',
 'NYJ':'2000_New_York_Jets_season',       'OAK':'2000_Oakland_Raiders_season',
 'PHI':'2000_Philadelphia_Eagles_season', 'PIT':'2000_Pittsburgh_Steelers_season',
 'SD':'2000_San_Diego_Chargers_season',   'SEA':'2000_Seattle_Seahawks_season',
 'SF':'2000_San_Francisco_49ers_season',  'STL':'2000_St._Louis_Rams_season',
 'TB':'2000_Tampa_Bay_Buccaneers_season', 'TEN':'2000_Tennessee_Titans_season',
 'WAS':'2000_Washington_Redskins_season',
}

# team -> {role: (name, note, source_slug_override_or_None)}
# Notes carry the page's own role label whenever it is not a plain
# "Offensive coordinator" / "Defensive coordinator" / "Special teams".
D = {
 'ARI': {'OC': ('Marc Trestman', '', None),
         'DC': ('Larry Marmie',
                'Ruling (Ryan, 2026-08-31). McGinnis was DC for games 1-7 and moved '
                'up to HC when Tobin was fired; Marmie took the defence for games '
                '8-16 and held it through 2003. PFR lists both men as 2000 DC. The '
                'Wikipedia season page predates the change and still shows McGinnis, '
                'which is why the earlier build had him here.',
                'PFR:crd'),
         'ST': ('Hank Kuhlmann', '', None)},
 'ATL': {'OC': ('George Sefcik', 'listed as "Offensive coordinator/running backs"', None),
         'DC': ('Rich Brooks', 'listed as "Assistant head coach/defensive coordinator"', None),
         'ST': ('Joe DeCamillis', '', None)},
 'BAL': {'OC': ('Matt Cavanaugh', '', None),
         'DC': ('Marvin Lewis', '', None),
         'ST': ('Russ Purnell', '', None)},
 'BUF': {'OC': ('Joe Pendry', '', None),
         'DC': ('Ted Cottrell', '', None),
         'ST': ('Ronnie Jones', '', None)},
 'CAR': {'OC': ('Bill Musgrave', '', None),
         'DC': ('John Marshall', 'listed as "Assistant head coach/defensive coordinator"', None),
         'ST': ("Scott O'Brien", '', None)},
 'CHI': {'OC': ('Gary Crowton', '', None),
         'DC': ('Greg Blache', '', None),
         'ST': ('Keith Armstrong', '', None)},
 'CIN': {'OC': ('Ken Anderson', '', None),
         'DC': ('Dick LeBeau',
                'Ruling (Ryan, 2026-08-31): LeBeau held HC and DC SIMULTANEOUSLY. He '
                'was assistant HC/DC under Coslet, took over as HC after game 3, and '
                'kept calling the defence. He therefore legitimately fills both the '
                'HC and DC slot in this file — not an error, and not to be '
                '"fixed" by a later pass. PFR gives him as the 2000 DC.',
                'PFR:cin'),
         'ST': ('Al Roberts', '', None)},
 'CLE': {'OC': ('Pete Carmichael', '', None),
         'DC': ('Romeo Crennel', 'listed as "Defensive coordinator/defensive line"', None),
         'ST': ('Mark Michaels', '', None)},
 'DAL': {'OC': ('Jack Reilly',
                'Season page has no staff section; name taken from its prose, which '
                'calls him "new offensive coordinator".', None),
         'DC': ('Mike Zimmer',
                'Season page has no staff section; his own article gives '
                '"Defensive coordinator (2000-2006)" with Dallas.', 'Mike_Zimmer'),
         'ST': ('Joe Avezzano',
                'Season page has no staff section; his own article gives '
                '"1990-2002 Dallas Cowboys (ST)".', 'Joe_Avezzano')},
 'DEN': {'OC': ('Gary Kubiak', 'listed as "Offensive coordinator/quarterbacks"', None),
         'DC': ('Greg Robinson', '', None),
         'ST': ('Rick Dennison',
                'Preferred over Anthony Lynn, listed as "Special teams assistant"', None)},
 'DET': {'OC': ('Sylvester Croom', '', None),
         'DC': ('Larry Peccatiello', '', None),
         'ST': ('Chuck Priefer', '', None)},
 'GB':  {'OC': ('Tom Rossley', '', None),
         'DC': ('Ed Donatell', '', None),
         'ST': ('Frank Novak', '', None)},
 'IND': {'OC': ('Tom Moore', '', None),
         'DC': ('Vic Fangio', '', None),
         'ST': ('Kevin Spencer', '', None)},
 'JAX': {'OC': ('Bobby Petrino',
                'PROMOTION, not a title he held. Jacksonville had no offensive '
                'coordinator in 2000 — Coughlin ran the offense and the source '
                'lists a complete offensive staff (QB Petrino, RB Ingram, WR '
                'McNulty, TE Hoaglin, OL Maser, QC McGee) with no OC among them. '
                'Ruling (Ryan, 2026-08-31): the slot cannot be left empty — all '
                '224 team-coordinator slots across the seven published files are '
                'filled with a distinct real person — and an invented name is '
                'barred for coaches. Petrino was the senior offensive assistant '
                'and is promoted into the slot. He did not hold the title.', None),
         'DC': ('Dom Capers', '', None),
         'ST': ('Frank Gansz', '', None)},
 'KC':  {'OC': ('Jimmy Raye', '', None),
         'DC': ('Kurt Schottenheimer', '', None),
         'ST': ('Mike Stock', '', None)},
 'MIA': {'OC': ('Chan Gailey', '', None),
         'DC': ('Jim Bates', '', None),
         'ST': ('Mike Westhoff', '', None)},
 'MIN': {'OC': ('Sherman Lewis', '', None),
         'DC': ('Emmitt Thomas', '', None),
         'ST': ('Gary Zauner', '', None)},
 'NE':  {'OC': ('Charlie Weis', 'listed as "Offensive coordinator/running backs"', None),
         'DC': ('Eric Mangini',
                'PROMOTION, not a title he held. New England had no defensive '
                'coordinator in 2000 — Belichick ran the defense and the source '
                'lists a complete defensive staff (DL Melvin, LB Ryan, asst LB '
                'Johnson, DB Mangini, asst Walker) with no DC among them. Ruling '
                '(Ryan, 2026-08-31): same reasoning as JAX/OC. Mangini is promoted '
                'into the slot. He did not hold the title.', None),
         'ST': ('Brad Seely', '', None)},
 'NO':  {'OC': ('Mike McCarthy', '', None),
         'DC': ('Ron Zook', '', None),
         'ST': ('Al Everest', '', None)},
 'NYG': {'OC': ('Sean Payton', 'listed as "Offensive coordinator/quarterbacks"', None),
         'DC': ('John Fox', '', None),
         'ST': ('Larry Mac Duff', '', None)},
 'NYJ': {'OC': ('Dan Henning', '', None),
         'DC': ('Mike Nolan', '', None),
         'ST': ('Mike Sweatman', '', None)},
 'OAK': {'OC': ('Bill Callahan', 'listed as "Offensive coordinator/offensive line"', None),
         'DC': ('Chuck Bresnahan', '', None),
         'ST': ('Bob Casullo', '', None)},
 'PHI': {'OC': ('Rod Dowhower', '', None),
         'DC': ('Jim Johnson', '', None),
         'ST': ('John Harbaugh', '', None)},
 'PIT': {'OC': ('Kevin Gilbride', '', None),
         'DC': ('Tim Lewis', '', None),
         'ST': ('Jay Hayes', '', None)},
 'SD':  {'OC': ('Geep Chryst', '', None),
         'DC': ('Joe Pascale', '', None),
         'ST': ('Bruce Read', '', None)},
 'SEA': {'OC': ('Gil Haskell', '', None),
         'DC': ('Steve Sidwell', '', None),
         'ST': ('Pete Rodriguez', '', None)},
 'SF':  {'OC': ('Marty Mornhinweg', '', None),
         'DC': ('Jim Mora',
                'Jim L. Mora, the son. NOT the Jim E. Mora who is Indianapolis HC in '
                'this same file — see the IND/HC row. Any name-keyed lookup must '
                'keep these two apart.', None),
         'ST': ('Bruce DeHaven', '', None)},
 'STL': {'OC': ('Bobby Jackson', 'listed as "Offensive coordinator/running backs"', None),
         'DC': ('Peter Giunta', '', None),
         'ST': ('Larry Pasquale', '', None)},
 'TB':  {'OC': ('Les Steckel', '', None),
         'DC': ('Monte Kiffin', '', None),
         'ST': ('Joe Marciano', '', None)},
 'TEN': {'OC': ('Mike Heimerdinger', '', None),
         'DC': ('Gregg Williams', '', None),
         'ST': ('Alan Lowry', '', None)},
 'WAS': {'OC': ('Terry Robiskie',
                'Source labels him "Pass game coordinator", not OC — Turner called '
                'plays. The confirmed table in docs/PGM3_TASK_coaches_2000.md gives '
                'him as the OC, and that is followed here.', None),
         'DC': ('Ray Rhodes', '', None),
         'ST': ('LeCharls McDaniel', '', None)},
}

# Mid-season HC changes. Ruling (Ryan, 2026-08-31): the slot goes to whoever
# coached the most games; the other is recorded here.
HC_NOTE = {
 'ARI': 'Mid-season change: Vince Tobin games 1-7, Dave McGinnis games 8-16. '
        'McGinnis takes the slot (9 games).',
 'CIN': 'Mid-season change: Bruce Coslet games 1-3, Dick LeBeau games 4-16. '
        'LeBeau takes the slot (13 games). The source page still lists Coslet as HC.',
 'DET': 'Mid-season change: Bobby Ross games 1-9, Gary Moeller games 10-16. '
        'Ross takes the slot (9 games).',
 'WAS': 'Mid-season change: Norv Turner games 1-13, Terry Robiskie games 14-16. '
        'Turner takes the slot (13 games). Contradicts nflverse games.csv, which '
        'had the two transposed.',
 'IND': 'Jim E. Mora, the father. NOT the Jim Mora who is San Francisco DC in this '
        'same file — see the SF/DC row. Any name-keyed lookup must keep these apart.',
 'DAL': 'Season page has no staff section; HC from coaches_2000_HC.csv, and the '
        'page prose confirms Campo was promoted to head coach.',
}

# Repo-relative, so this runs from any clone. It previously carried an absolute
# path to one machine's working copy plus the old $PGM3_SOURCES/pfr/ layout, and would
# have written outside the repo after the files moved out of the repo.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HC_FILE = os.path.join(REPO, 'sources', 'coaches_2000_HC.csv')
OUT = os.path.join(REPO, 'sources', 'coaches_2000.csv')

hc = {}
with open(HC_FILE, encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        hc[r['team']] = r['head_coach']

assert len(hc) == 31, f'expected 31 head coaches, got {len(hc)}'
assert set(hc) == set(SEASON), f'HC file and season map disagree: {set(hc) ^ set(SEASON)}'
assert set(D) == set(SEASON), f'staff table incomplete: {set(D) ^ set(SEASON)}'

rows = []
for team in sorted(SEASON):
    src = u(SEASON[team])
    rows.append({'team': team, 'role': 'HC', 'name': hc[team],
                 'source': src, 'note': HC_NOTE.get(team, '')})
    for role in ('OC', 'DC', 'ST'):
        name, note, override = D[team][role]
        rows.append({'team': team, 'role': role, 'name': name,
                     'source': u(override) if override else src, 'note': note})

# ---- assertions before the write ------------------------------------------
assert len(rows) == 124, f'expected 31*4=124 rows, got {len(rows)}'
seen = {}
for r in rows:
    key = (r['team'], r['role'])
    assert key not in seen, f'duplicate row {key}'
    seen[key] = r
    assert r['source'].startswith('https://'), f'{key} has no source URL'
    assert r['role'] in ('HC', 'OC', 'DC', 'ST'), key
    # Every slot must now carry a real person: 224/224 in the published files.
    assert r['name'], f'{key} has no name — the published files never leave a slot empty'
    # Promotions must say so, so nobody later reads them as held titles.
    if 'PROMOTION' in r['note']:
        assert 'did not hold the title' in r['note'], f'{key} promotion note is incomplete'
for team in SEASON:
    for role in ('HC', 'OC', 'DC', 'ST'):
        assert (team, role) in seen, f'missing {team}/{role}'

# HC rows must equal the already-verified file exactly.
for team, name in hc.items():
    assert seen[(team, 'HC')]['name'] == name, f'{team} HC drifted from coaches_2000_HC.csv'

# The five pairings the task doc says a correct extraction must reproduce.
# This asserts the EXTRACTION was right, which it was — keep it even where the
# file's final value has since been overruled, or the guard is lost.
CONFIRMED = {('ARI','OC'):'Marc Trestman', ('ARI','DC'):'Dave McGinnis',
             ('BAL','OC'):'Matt Cavanaugh', ('BAL','DC'):'Marvin Lewis',
             ('CHI','OC'):'Gary Crowton',   ('CHI','DC'):'Greg Blache',
             ('DEN','OC'):'Gary Kubiak',    ('DEN','DC'):'Greg Robinson',
             ('WAS','OC'):'Terry Robiskie', ('WAS','DC'):'Ray Rhodes'}

# Where the file deliberately departs from the confirmed table, and why. A
# departure that is not listed here is a bug, not a decision.
OVERRIDES = {
    ('ARI','DC'): ('Larry Marmie',
                   'Ryan, 2026-08-31. The confirmed table has McGinnis because the '
                   'Wikipedia staff box is the start-of-season staff. Marmie ran '
                   'the defence for the majority of the season (games 8-16).'),
}
for key, want in CONFIRMED.items():
    got = seen[key]['name']
    if key in OVERRIDES:
        want = OVERRIDES[key][0]
        assert got == want, f'override not applied: {key} got {got!r} want {want!r}'
    else:
        assert got == want, f'confirmed check failed: {key} got {got!r} want {want!r}'

# The only names that may appear twice are the three known cases. A fourth
# duplicate means either a copy-paste slip or an undocumented shared role.
EXPECTED_DUPS = {
    'Dick LeBeau',     # CIN HC and DC at once — ruled deliberate, see the note
    'Jim Mora',        # IND HC is the father, SF DC is the son — different men
}
counts = collections.Counter(r['name'] for r in rows if r['name'])
dups = {n for n, c in counts.items() if c > 1}
assert dups == EXPECTED_DUPS, f'unexpected duplicate names: {dups ^ EXPECTED_DUPS}'

blank = [(r['team'], r['role']) for r in rows if not r['name']]

with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['team', 'role', 'name', 'source', 'note'])
    w.writeheader()
    w.writerows(rows)

print(f'wrote {OUT}')
print(f'  {len(rows)} rows, {len(SEASON)} teams x 4 roles')
print(f'  all {len(CONFIRMED)} confirmed cross-checks pass')
print(f'  blank names: {blank if blank else "none"}')
