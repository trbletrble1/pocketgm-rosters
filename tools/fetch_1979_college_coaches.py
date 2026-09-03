#!/usr/bin/env python3
"""
fetch_1979_college_coaches — head coaches of the Southern-conference college
programmes in 1979, for tier 3 of the coaching pool. Writes
wip/college_coaches_1979.csv.

  python3 tools/fetch_1979_college_coaches.py

SCOPED TO THE SOUTH ON PURPOSE. Jacksonville's doctrine is a Southern hire, and
Indianapolis's is a first-time NFL head coach — which the 99-man NFL pool cannot
supply by construction, since every man in it has already been one. A college
coach who never coached professionally is a first-timer by definition. Fetching
all of Division I-A would be ~140 pages for two hires.

Team names come from the season page's transcluded standings templates rather
than a hand list, and each team's own 1979 page carries the coach in its infobox.
"""
import urllib.request, urllib.parse, json, re, csv, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

UA = {'User-Agent': 'pocketgm-rosters/1.0 (historical roster research; ryannecci@gmail.com)'}
CACHE = '/tmp/college79'
CONFS = ['Atlantic Coast Conference', 'Southeastern Conference', 'Southwest Conference',
         'Southern Conference', 'Southland Conference', 'NCAA Division I-A independents']

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

def main():
    teams = []
    for c in CONFS:
        t = ('1979 ' + c + (' football standings' if 'independents' not in c else ' football records'))
        w = wt('Template:' + t)
        found = re.findall(r'\[\[(1979 [^|\]]+ football team)(?:\|[^\]]*)?\]\]', w)
        teams += found
        print(f'  {c:<42}{len(found):>4} teams')
    teams = sorted(set(teams))
    print(f'\n{len(teams)} distinct 1979 Southern-region programmes')
    rows = []
    for t in teams:
        w = wt(t)
        m = re.search(r'\|\s*head_coach\s*=\s*([^\n|]+)', w)
        if not m:
            m = re.search(r'\|\s*coach\s*=\s*([^\n|]+)', w)
        name = re.sub(r'\[\[[^|\]]*\|', '', m.group(1)).replace(']]', '').replace('[[', '').strip() if m else ''
        name = re.sub(r'\{\{[^}]*\}\}', '', name).strip()
        # 'Ralph Staub (American football)' is a page title, not a name
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
        yr = re.search(r'\|\s*head_coach_year\s*=\s*(\d+)', w)
        rec = re.search(r'\|\s*record\s*=\s*(\d+)[–-](\d+)(?:[–-](\d+))?', w)
        rows.append(dict(team=re.sub(r'^1979 | football team$', '', t), coach=name,
                         season_of_tenure=yr.group(1) if yr else '',
                         record_1979='%s-%s-%s' % (rec.group(1), rec.group(2), rec.group(3) or 0) if rec else ''))
    named = [r for r in rows if r['coach']]
    assert len(named) >= len(rows) * 0.8, f'only {len(named)}/{len(rows)} coaches parsed'
    f = open(repo('wip', 'college_coaches_1979.csv'), 'w', newline='')
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows); f.close()
    print(f'wrote wip/college_coaches_1979.csv: {len(named)} of {len(rows)} with a named coach')

if __name__ == '__main__':
    main()
