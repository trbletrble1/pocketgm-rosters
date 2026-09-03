#!/usr/bin/env python3
"""
fetch_nfl_standings — points for and against, by team and season, 1960-1978.
Writes wip/nfl_standings_1960_1978.csv. Cached under /tmp/standings.

  python3 tools/fetch_nfl_standings.py

WHY. A head coach's winning percentage cannot see what his UNITS did, which is
exactly the signal the 1979 coaching pool needs: Bill Arnsparger went 7-28 as a
head coach and built Miami's No-Name Defense. Points allowed is that signal.

Season pages do NOT carry it — they transclude {{1973 AFC East standings}} and
the like — so this reads the templates, whose names are taken FROM each season
page rather than guessed, because the division structure changes across the
period (AFL and NFL to 1969, then AFC and NFC, with divisions renamed).
"""
import urllib.request, urllib.parse, json, re, csv, sys, os, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

UA = {'User-Agent': 'pocketgm-rosters/1.0 (historical roster research; ryannecci@gmail.com)'}
CACHE = '/tmp/standings'
YEARS = range(1960, 1979)

def wt(title):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9]', '_', title) + '.wiki')
    if os.path.exists(f):
        return open(f).read()
    u = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
         'format': 'json', 'titles': title, 'redirects': 1})
    try:
        p = list(json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))['query']['pages'].values())[0]
        s = p['revisions'][0]['slots']['main']['*'] if 'revisions' in p else ''
    except Exception:
        s = ''
    open(f, 'w').write(s); time.sleep(0.2)
    return s

def rows_from(tpl):
    """One standings table -> [(team, w, l, t, pf, pa)]. The columns are found by
    reading the header rather than assumed: PF and PA sit in different positions
    across eras, and DIV/CONF columns appear only in some."""
    hdr = [h for h in re.findall(r'\{\{ *Abbr *\| *([A-Z]+) *\|', tpl)]
    try:
        i_pf, i_pa = hdr.index('PF'), hdr.index('PA')
    except ValueError:
        return []
    out = []
    for blk in tpl.split('\n|-')[1:]:
        # TWO CELL CONVENTIONS. Later templates put one cell per line; the 1960
        # ones run them inline as |10||4||0||.714||379||285. Normalise the inline
        # form to the line form before splitting, or the whole season parses to
        # zero rows with no error — which is what happened.
        blk = blk.replace('||', '\n|')
        cells = [re.sub(r'\[\[[^|\]]*\|', '', c).replace(']]', '').replace('[[', '').strip()
                 for c in re.split(r'\n\s*\|(?!\|)', blk) if c.strip()]
        cells = [re.sub(r'\{\{[^}]*\}\}|<[^>]+>|style *= *"[^"]*"', '', c).strip(' |') for c in cells]
        cells = [c for c in cells if c]
        if len(cells) < i_pa + 2:
            continue
        team = re.sub(r'^\d{4} ', '', cells[0])
        if not re.match(r'^[A-Z]', team) or re.fullmatch(r'[\d.\-–]+', team):
            continue
        nums = cells[1:]
        if len(nums) <= i_pa:
            continue
        try:
            w, l, t = int(nums[0]), int(nums[1]), int(nums[2])
            pf, pa = int(nums[i_pf]), int(nums[i_pa])
        except (ValueError, IndexError):
            continue
        out.append((team, w, l, t, pf, pa))
    return out

def main():
    recs = []
    for y in YEARS:
        page = wt(f'{y} NFL season') + wt(f'{y} AFL season')
        # the name may carry parameters: {{1960 NFL Western standings|hidenote=y}}.
        # Requiring '}}' straight after the name found the Eastern division and
        # missed the Western one, halving the season without raising anything.
        names = sorted(set(re.findall(r'\{\{ *(' + str(y) + r' [A-Z][^}|]*standings)\s*(?:\|[^}]*)?\}\}', page)))
        got = 0
        for n in names:
            for team, w, l, t, pf, pa in rows_from(wt('Template:' + n)):
                recs.append(dict(season=y, team=team, w=w, l=l, t=t, pf=pf, pa=pa)); got += 1
        print(f'  {y}: {len(names)} standings tables, {got} team-seasons')
        assert got >= 12, f'{y}: only {got} team-seasons — the template names changed'
    # league rank within season: 1 = fewest points allowed / most scored
    by = collections.defaultdict(list)
    for r in recs:
        by[r['season']].append(r)
    for y, v in by.items():
        for r in v:
            r['pa_rank'] = sorted(v, key=lambda z: z['pa']).index(r) + 1
            r['pf_rank'] = sorted(v, key=lambda z: -z['pf']).index(r) + 1
            r['n_teams'] = len(v)
    f = open(repo('wip', 'nfl_standings_1960_1978.csv'), 'w', newline='')
    wr = csv.DictWriter(f, fieldnames=['season', 'team', 'w', 'l', 't', 'pf', 'pa', 'pf_rank', 'pa_rank', 'n_teams'])
    wr.writeheader(); wr.writerows(recs); f.close()
    print(f'\nwrote wip/nfl_standings_1960_1978.csv: {len(recs)} team-seasons')
    # anchor: the 1973 Dolphins allowed 150 points and led the league
    d = [r for r in recs if r['season'] == 1973 and 'Miami' in r['team']]
    assert d and d[0]['pa'] == 150 and d[0]['pa_rank'] == 1, f'1973 Dolphins anchor failed: {d}'
    print('  anchor: the 1973 Dolphins allowed 150 points, first in the league')

if __name__ == '__main__':
    main()
