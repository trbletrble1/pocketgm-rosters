#!/usr/bin/env python3
"""
build_1979_roster - deduplicate the 28 footballdb 1979 rosters into one table.

    python3 tools/build_1979_roster.py

Reads  sources/1979footballdb/*.txt   (jersey|name|pos|games|age|college)
Writes wip/roster_1979_dedup.csv

THE THREE RULES, all ruled by Ryan 2026-09-02:

1. MOVERS vs NAMESAKES - split on COLLEGE, not position. Two men shared a name
   AND a position in this season (Larry Brown OT, Gene Washington WR); position
   would have merged them. College + age separates every case.
2. A mover is assigned to the team he played the most games for. Exact ties go
   to the team whose 2K5 block holds him. What no rule reaches is a hand call,
   logged with its reason.
3. Low-stakes note, recorded deliberately: 13 of 30 movers are decided by a
   margin of one or two games. That is a coin flip dressed as a rule. Each moves
   one player between teams carrying 46-60, so it is not worth buying a source
   for - but it should not read as more principled than it is.
"""
import sys, os, glob, csv, collections, unicodedata, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl2k5
from nfl2k5 import norm as knorm

BLOCKS = {'st-louis-cardinals':(0,52),'atlanta-falcons':(54,105),'buffalo-bills':(159,211),
'chicago-bears':(265,317),'cincinnati-bengals':(318,369),'dallas-cowboys':(371,423),
'denver-broncos':(424,476),'detroit-lions':(477,529),'green-bay-packers':(530,582),
'baltimore-colts':(584,635),'kansas-city-chiefs':(689,740),'miami-dolphins':(742,793),
'minnesota-vikings':(796,847),'new-england-patriots':(849,900),'new-orleans-saints':(901,953),
'new-york-giants':(954,1003),'new-york-jets':(1007,1059),'oakland-raiders':(1060,1111),
'philadelphia-eagles':(1113,1165),'pittsburgh-steelers':(1167,1216),'los-angeles-rams':(1219,1271),
'san-diego-chargers':(1274,1324),'san-francisco-49ers':(1325,1376),'seattle-seahawks':(1378,1429),
'tampa-bay-buccaneers':(1431,1483),'houston-oilers':(1484,1535),'washington-redskins':(1537,1589),
'cleveland-browns':(1590,1640)}

# The one record no rule reaches. 1 game each for Baltimore and Detroit, no 2K5
# record. Baltimore is where he started the season.
HAND = {'jerry golsteyn': ('baltimore-colts', 'started the season in Baltimore; '
                           '1 game each, no 2K5 record, no rule reaches it')}

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()

def load():
    rows = []
    for f in sorted(glob.glob('sources/1979footballdb/*.txt')):
        team = os.path.basename(f)[:-4]
        for line in open(f):
            c = line.rstrip('\n').split('|')
            if len(c) < 6:
                continue
            rows.append(dict(team=team, jersey=c[0], name=c[1], pos=c[2],
                             games=int(c[3]), age=int(c[4]), college=c[5]))
    return rows

def main():
    rows = load()
    assert len(rows) == 1438, f'expected 1438 source rows, got {len(rows)}'
    save = nfl2k5.Save('sources/NFL2k25 Year Saves/1979-1980SAVEGAME.DAT')
    k5 = collections.defaultdict(list)
    for i, p in enumerate(save.players):
        k5[knorm(p['fname'] + ' ' + p['lname'])].append(i)

    by = collections.defaultdict(list)
    for r in rows:
        by[norm(r['name'])].append(r)

    out, log = [], []
    for key, group in by.items():
        if len(group) == 1:
            out.append(dict(group[0], mover='', also='', resolved=''))
            continue
        # two men on the SAME team share a name -> two people, keep both
        if len({r['team'] for r in group}) < len(group):
            for r in group:
                out.append(dict(r, mover='', also='same-team namesake', resolved=''))
            log.append(('same-team namesake', key, [r['team'] for r in group]))
            continue
        colleges = {norm(r['college']) for r in group}
        ages = [r['age'] for r in group]
        same_man = (len(colleges) == 1 and colleges != {''}
                    and max(ages) - min(ages) <= 1)
        if not same_man:
            for r in group:                      # different men sharing a name
                out.append(dict(r, mover='', also='namesake', resolved=''))
            log.append(('namesake', key, [f"{r['team']}/{r['pos']}/{r['college']}" for r in group]))
            continue
        # a genuine mover: one record, most games wins
        ranked = sorted(group, key=lambda r: -r['games'])
        how = 'games'
        if len(ranked) > 1 and ranked[0]['games'] == ranked[1]['games']:
            teams = {r['team'] for r in group}
            blk = [t for i in k5.get(key, [])
                   for t, (lo, hi) in BLOCKS.items() if lo <= i <= hi and t in teams]
            if blk:
                ranked = sorted(group, key=lambda r: (r['team'] != blk[0], -r['games']))
                how = '2K5 block (games tied)'
            elif key in HAND:
                team, why = HAND[key]
                ranked = sorted(group, key=lambda r: (r['team'] != team, -r['games']))
                how = 'HAND: ' + why
            else:
                how = 'UNRESOLVED TIE'
        win = ranked[0]
        rec = dict(win, games=sum(r['games'] for r in group), mover='yes',
                   also=';'.join(f"{r['team']}:{r['games']}" for r in ranked[1:]),
                   resolved=how)
        out.append(rec)
        log.append(('mover', key, [win['team'], how,
                                   ranked[0]['games'] - ranked[1]['games']]))

    dupes = sum(len(g) - 1 for g in by.values()
                if len(g) > 1 and len({r['team'] for r in g}) == len(g)
                and len({norm(r['college']) for r in g}) == 1
                and {norm(r['college']) for r in g} != {''}
                and max(r['age'] for r in g) - min(r['age'] for r in g) <= 1)
    assert len(out) == len(rows) - dupes, \
        f'{len(rows)} in, {len(out)} out, expected {len(rows)-dupes}'
    unresolved = [l for l in log if l[0] == 'mover' and l[2][1] == 'UNRESOLVED TIE']
    assert not unresolved, f'unresolved mover ties: {unresolved}'

    os.makedirs('wip', exist_ok=True)
    with open('wip/roster_1979_dedup.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['team','jersey','name','pos','games',
                                           'age','college','mover','also','resolved'])
        w.writeheader()
        for r in sorted(out, key=lambda r: (r['team'], r['name'])):
            w.writerow(r)

    movers = [l for l in log if l[0] == 'mover']
    print(f'source rows          {len(rows)}')
    print(f'movers collapsed     {len(movers)}')
    print(f'namesakes kept apart {len([l for l in log if l[0]=="namesake"])}')
    print(f'same-team namesakes  {len([l for l in log if l[0]=="same-team namesake"])}')
    print(f'DEDUPLICATED TOTAL   {len(out)}')
    print()
    print('resolution of the 30 movers:')
    for how, n in collections.Counter(l[2][1] for l in movers).most_common():
        print(f'   {n:>2}  {how}')
    thin = [l for l in movers if isinstance(l[2][2], int) and l[2][2] <= 2]
    print(f'\ndecided by a margin of <=2 games: {len(thin)} of {len(movers)}'
          '  <- coin flip dressed as a rule')
    per = collections.Counter(r['team'] for r in out)
    print(f'\nper-team: min {min(per.values())}  max {max(per.values())}  '
          f'mean {sum(per.values())/len(per):.1f}  teams {len(per)}')

if __name__ == '__main__':
    main()
