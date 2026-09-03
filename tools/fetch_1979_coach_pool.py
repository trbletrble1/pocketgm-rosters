#!/usr/bin/env python3
"""
fetch_1979_coach_pool — every man who had been an NFL head coach before 1979,
from the Wikipedia per-franchise coach lists. Writes wip/coach_pool_1979_raw.csv.
Pages are cached under /tmp/coachlists; a second run re-reads the cache.

  python3 tools/fetch_1979_coach_pool.py

Tiers 1 and 2 of the free-agent coaching pool come from here. Tier 3 (college)
does not — a college coach has no NFL record and needs a different source and a
stated rating method.

THE PARSER IS LAYOUT-FREE, and that is the whole lesson of writing it. Four
layouts were coded and each new franchise page broke the next:

    Pittsburgh   Name | Term            | GC W L T
    Atlanta      Name | Yrs | First | Last | GC W L T
    Denver       Name | First | Last  | GC W L T
    Minnesota    Name | Yrs | Year    | GC W L T      (a one-season second spell)
    San Diego    Name | '1961-1969, 1971' | ...        (a compound term)

and the ordering between them mattered too — the Term regex matches a bare year,
so trying it first swallowed Denver's First column and read Red Miller, a sitting
1979 head coach, as 1977-1977. So there is no layout list. The record is found by
its OWN ARITHMETIC — the first run of four integers where games = wins + losses +
ties — and every 4-digit year before that run is the term. Self-checking: a run
that does not balance is not the record.

Four separate one-line defects each silently emptied a page or truncated a career:
  * {{sortname|Norb|Hecker}} is the NAME on half the pages; a blanket template
    strip deleted it and seventeen of twenty-eight lists parsed to zero.
  * {{nfly|1927}} is the YEAR on others; stripping it left an empty term.
  * Green Bay puts the name in a !scope="row" header cell, so a split on '|'
    alone never saw it.
  * bgcolor="#FFE6BD"|Don Coryell — an unlisted attribute prefix — cost Coryell
    his San Diego tenure, and a non-breaking space in 'Sid Gillman\\xa0' cost
    Gillman his Rams years and left his career reading 18-19 instead of 122-99.

TWO ANCHORS, because a parse that is merely non-empty is not a parse that is
complete. Membership: all 28 of 1979's sitting head coaches must appear with a
last season of 1979 or later — that caught Miller and Coryell. Careers: six men
whose totals are known independently must match to the game — that caught
Gillman, whom the membership check could never see.
"""
import urllib.request, urllib.parse, json, re, csv, sys, os, time, html, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

UA = {'User-Agent': 'pocketgm-rosters/1.0 (historical roster research; ryannecci@gmail.com)'}
CACHE = '/tmp/coachlists'
LISTS = ['Atlanta Falcons', 'Baltimore Colts', 'Buffalo Bills', 'Chicago Bears',
         'Cincinnati Bengals', 'Cleveland Browns', 'Dallas Cowboys', 'Denver Broncos',
         'Detroit Lions', 'Green Bay Packers', 'Houston Oilers', 'Kansas City Chiefs',
         'Los Angeles Rams', 'Miami Dolphins', 'Minnesota Vikings', 'New England Patriots',
         'New Orleans Saints', 'New York Giants', 'New York Jets', 'Oakland Raiders',
         'Philadelphia Eagles', 'Pittsburgh Steelers', 'San Diego Chargers',
         'Seattle Seahawks', 'San Francisco 49ers', 'St. Louis Cardinals',
         'Tampa Bay Buccaneers', 'Washington Redskins']
# careers known independently — the check a membership test cannot make
CAREER = {'Sid Gillman': (122, 99, 7), 'Weeb Ewbank': (130, 129, 7),
          'Paul Brown': (213, 104, 9), 'Hank Stram': (131, 97, 10),
          'George Allen': (116, 47, 5), 'Bud Grant': (158, 96, 5)}

def wt(title):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9]', '_', title) + '.wiki')
    if os.path.exists(f):
        return open(f).read()
    u = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
         'format': 'json', 'titles': title, 'redirects': 1})
    p = list(json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))['query']['pages'].values())[0]
    s = p['revisions'][0]['slots']['main']['*'] if 'revisions' in p else ''
    open(f, 'w').write(s); time.sleep(0.25)
    return s

def clean(x):
    x = re.sub(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', '', x, flags=re.S)
    x = re.sub(r'\{\{ *sortname *\| *([^|}]+) *\| *([^|}]+)[^}]*\}\}', r'\1 \2', x, flags=re.I)
    x = re.sub(r'\{\{ *(?:nowrap|nobold|sortname) *\| *([^|}]+) *\}\}', r'\1', x, flags=re.I)
    x = re.sub(r'\{\{ *nfly *\| *(\d{4})[^}]*\}\}', r'\1', x, flags=re.I)
    for _ in range(3):
        x = re.sub(r'\{\{[^{}]*\}\}', '', x)
    x = re.sub(r'\[\[[^|\]]*\|', '', x).replace(']]', '').replace('[[', '')
    x = re.sub(r'<[^>]+>', '', x)
    x = re.sub(r'[a-zA-Z-]+\s*=\s*"[^"]*"\s*\|?', '', x)
    x = re.sub(r'^[a-zA-Z-]+\s*=\s*[^|"\s]+\s*\|', '', x)
    x = html.unescape(x)
    x = re.sub(r'[   \s]+', ' ', x)   # &nbsp; survives html.unescape as \xa0
    return x.strip(" |*†‡^+")

def parse(team, w):
    out = []
    for h in ('==Coaches==', '==Head coaches=='):
        if h in w:
            w = w[w.index(h):]; break
    for blk in w.split('\n|-'):
        cells = [c for c in (clean(c) for c in re.split(r'\n\s*[|!](?![|!])', blk)) if c]
        if len(cells) < 6:
            continue
        ni = next((i for i, c in enumerate(cells)
                   if re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){1,3}", c)), None)
        if ni is None:
            continue
        name, rest = cells[ni], cells[ni + 1:]
        k = next((q for q in range(len(rest) - 3)
                  if all(re.fullmatch(r'\d+', c) for c in rest[q:q + 4])
                  and int(rest[q]) == sum(int(c) for c in rest[q + 1:q + 4])
                  and int(rest[q]) > 0), None)
        if k is None:
            continue
        years = [int(y) for c in rest[:k] for y in re.findall(r'\b(19\d{2}|20[0-2]\d)\b', c)]
        if not years:
            continue
        first, last = min(years), max(years)
        if 'present' in ' '.join(rest[:k]):
            last = 2026
        if not (1920 <= first <= 2026):
            continue
        gc, wn, ls, ti = (int(c) for c in rest[k:k + 4])
        out.append(dict(team=team, name=name, first=first, last=last, gc=gc, w=wn, l=ls, t=ti))
    return out

def main():
    rows = []
    for t in LISTS:
        r = parse(t, wt(f'List of {t} head coaches'))
        print(f'  {t:<24}{len(r):>4} coaches parsed')
        assert len(r) >= 6, f'{t}: {len(r)} rows — the layout changed; do not build a pool on a partial fetch'
        rows += r
    by = collections.defaultdict(list)
    for r in rows:
        by[r['name']].append(r)
    out = [dict(name=n, first=min(s['first'] for s in v), last=max(s['last'] for s in v),
                teams='; '.join(sorted({s['team'] for s in v})),
                gc=sum(s['gc'] for s in v), w=sum(s['w'] for s in v),
                l=sum(s['l'] for s in v), t=sum(s['t'] for s in v), spells=len(v))
           for n, v in by.items()]
    out.sort(key=lambda r: (-r['last'], -r['w']))
    idx = {r['name']: r for r in out}

    hc = [x['head_coach'] for x in csv.DictReader(open(repo('wip', 'staff_1979_sources.csv')))]
    missing = [n for n in hc if n not in idx]
    early = [(n, idx[n]['last']) for n in hc if n in idx and idx[n]['last'] < 1979]
    assert not missing and not early, f'1979 head coaches missing {missing}, or reading pre-1979 {early}'
    print(f"  anchor: all {len(hc)} of 1979's head coaches present, last season >= 1979")
    bad = [(n, (idx[n]['w'], idx[n]['l'], idx[n]['t']), v) for n, v in CAREER.items()
           if n in idx and (idx[n]['w'], idx[n]['l'], idx[n]['t']) != v]
    assert not bad, 'careers truncated: ' + '; '.join(f'{n} parsed {g} want {v}' for n, g, v in bad)
    print(f'  anchor: {len(CAREER)} independently known careers match to the game')

    f = open(repo('wip', 'coach_pool_1979_raw.csv'), 'w', newline='')
    wr = csv.DictWriter(f, fieldnames=list(out[0].keys())); wr.writeheader(); wr.writerows(f_ := out); f.close()
    print(f'\n{len(rows)} spells -> {len(out)} distinct men; wrote wip/coach_pool_1979_raw.csv')
    print(f"  last coached before 1979: {sum(1 for r in out if r['last'] < 1979)}")

if __name__ == '__main__':
    main()
