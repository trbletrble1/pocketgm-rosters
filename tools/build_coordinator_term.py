#!/usr/bin/env python3
"""
build_coordinator_term — what a man's UNITS did, for the 1979 coaching pool.
Writes wip/coordinator_term_1979.csv and prints the men where the coordinator
record and the head-coaching record disagree most.

  python3 tools/build_coordinator_term.py

THE PROBLEM IT SOLVES. The pool rates men on career winning percentage, which is
measured and right for most of the 99 — but it rewards men who coached good teams
and cannot see a man whose units were good while his teams were bad. Bill
Arnsparger went 7-28 as a head coach and built Miami's No-Name Defense. That is
Charlotte's doctrine exactly, and the head-coaching number is blind to it.

THE MEASURE. Each man's coaching career is read from the structured infobox on
his own article — `coach_years1`/`coach_team1` pairs, which carry the role in
brackets: 'Miami Dolphins (Defensive coordinator)', 'Pittsburgh Steelers (DC)'.
For every NFL coordinator season between 1960 and 1978, his team's league rank is
taken from wip/nfl_standings_1960_1978.csv — points ALLOWED for a defensive
coordinator, points SCORED for an offensive one — and converted to a percentile
so eras with 13 teams and 28 teams compare.

STATED LIMITS:
  * It credits the unit, not the man. A coordinator on a great roster looks great.
  * Role tags are inconsistent; 'AHC/DC' and 'Assistant head coach' both appear,
    and a man tagged only with a team and no role is skipped rather than guessed.
  * It reaches 1960-1978 only, so a career that ended before 1960 has no term.
  * A man with no article infobox — Joe Collier and Chuck Knox both return
    nothing — has no term. Absence here is missing data, never a low score.
"""
import urllib.request, urllib.parse, json, re, csv, sys, os, time, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

UA = {'User-Agent': 'pocketgm-rosters/1.0 (historical roster research; ryannecci@gmail.com)'}
CACHE = '/tmp/coacharticles'
DEF = re.compile(r'\b(DC|DB|DL|LB|defensive coordinator|defensive backfield|defense)\b', re.I)
OFF = re.compile(r'\b(OC|QB|RB|WR|OL|TE|offensive coordinator|backfield|offense)\b', re.I)

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

def career(w):
    """A man's coaching stints, from EITHER infobox.

    {{Infobox college coach}} uses numbered coach_years/coach_team pairs and tags
    the role in brackets — 'Pittsburgh Steelers (DC)'. Only 15 of the 99 pool men
    use it; the rest carry {{Infobox NFL biography}}, whose `pastcoaching` is a
    bullet list with the role in parentheses or after a <br>. Parsing only the
    first form found no career at all for Weeb Ewbank, Blanton Collier, Nick
    Skorich or Joe Schmidt.

    The second form's roles are mostly GENERIC — 'assistant', 'Assistant coach' —
    with no side, so it adds men without adding a usable term. That is a real
    limit of the source and it is reported rather than papered over."""
    out = _career_college(w) + _career_nfl(w)
    return out

def _career_nfl(w):
    m = re.search(r'\|\s*pastcoaching\s*=(.*?)(?=\n\s*\|\s*\w+\s*=)', w, re.S)
    if not m:
        return []
    out = []
    for ln in m.group(1).split('\n*'):
        ln = re.sub(r'\{\{ *nfly *\| *(\d{4})(?: *\| *(\d{4}))? *\}\}',
                    lambda z: z.group(1) + ('–' + z.group(2) if z.group(2) else ''), ln, flags=re.I)
        ln = re.sub(r'\[\[[^|\]]*\|', '', ln).replace(']]', '').replace('[[', '')
        ln = re.sub(r'<br\s*/?>', ' ', ln)
        y = re.search(r'\((\d{4})(?:\s*[–-]\s*(\d{4}))?\)', ln)
        if not y:
            continue
        a = int(y.group(1)); b = int(y.group(2)) if y.group(2) else a
        team = ln[:y.start()].strip(' *|')
        role = ln[y.end():].strip(' *|()')
        out.append((a, b, team, role))
    return out

def _career_college(w):
    yrs = dict(re.findall(r'\|\s*coach_years(\d+)\s*=\s*([^\n|]+)', w))
    tms = dict(re.findall(r'\|\s*coach_team(\d+)\s*=\s*([^\n|]+)', w))
    out = []
    for k in sorted(yrs, key=int):
        raw = tms.get(k, '')
        t = re.sub(r'\[\[[^|\]]*\|', '', raw).replace(']]', '').replace('[[', '').strip()
        m = re.match(r'^(.*?)\s*\(([^)]*)\)?\s*$', t)
        team, role = (m.group(1).strip(), m.group(2)) if m else (t, '')
        span = yrs[k].strip()
        y = re.match(r'(\d{4})(?:\s*[–-]\s*(\d{4}))?', span)
        if not y:
            continue
        a = int(y.group(1)); b = int(y.group(2)) if y.group(2) else a
        out.append((a, b, team, role))
    return out

def main():
    pool = list(csv.DictReader(open(repo('wip', 'coach_pool_1979.csv'))))
    stand = list(csv.DictReader(open(repo('wip', 'nfl_standings_1960_1978.csv'))))
    idx = {}
    for r in stand:
        idx[(int(r['season']), r['team'])] = r
    teams_by_season = collections.defaultdict(list)
    for r in stand:
        teams_by_season[int(r['season'])].append(r['team'])

    def find_team(season, name):
        cands = [t for t in teams_by_season.get(season, []) if name and (name in t or t in name)]
        if not cands and name:
            nick = name.split()[-1]
            cands = [t for t in teams_by_season.get(season, []) if t.endswith(nick)]
        return cands[0] if len(cands) == 1 else (cands[0] if cands else None)

    rows, done = [], 0
    for x in pool:
        w = wt(x['name'])
        if not any(k in w for k in {t.strip().split()[-1] for t in x['teams'].split(';') if t.strip()}):
            w = wt(x['name'] + ' (American football)')
        pct, seasons, detail = [], 0, []
        for a, b, team, role in career(w):
            side = 'D' if DEF.search(role) else ('O' if OFF.search(role) else None)
            if side is None or not role:
                continue
            for y in range(max(a, 1960), min(b, 1978) + 1):
                t = find_team(y, team)
                if not t:
                    continue
                r = idx[(y, t)]
                rank = int(r['pa_rank'] if side == 'D' else r['pf_rank'])
                n = int(r['n_teams'])
                pct.append(1 - (rank - 1) / max(1, n - 1))
                seasons += 1
                detail.append(f'{y} {t} {side} {rank}/{n}')
        done += 1
        if done % 25 == 0:
            print(f'  ...{done}/{len(pool)}')
        rows.append(dict(name=x['name'], tier=x['tier'], hc_record=x['record'],
                         hc_winpct=float(x['win_pct']), rating=int(x['rating']),
                         coord_seasons=seasons,
                         unit_pct=round(st.mean(pct), 3) if pct else '',
                         detail='; '.join(detail[:8])))
    f = open(repo('wip', 'coordinator_term_1979.csv'), 'w', newline='')
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows); f.close()
    have = [r for r in rows if r['unit_pct'] != '']
    print(f"\nwrote wip/coordinator_term_1979.csv: {len(have)} of {len(rows)} men have a coordinator record")
    print(f"  covering {sum(r['coord_seasons'] for r in have)} coordinator seasons\n")
    # the disagreement: unit percentile against head-coaching percentile
    hc_sorted = sorted(r['hc_winpct'] for r in rows)
    for r in have:
        r['hc_pct'] = hc_sorted.index(r['hc_winpct']) / max(1, len(hc_sorted) - 1)
        r['gap'] = r['unit_pct'] - r['hc_pct']
    have.sort(key=lambda r: -r['gap'])
    print('=== WHERE THE TWO DISAGREE MOST — units better than the record ===')
    print(f"  {'name':<20}{'HC record':>11}{'HC pct':>8}{'unit pct':>10}{'gap':>7}{'sns':>5}  where")
    for r in have[:12]:
        print(f"  {r['name']:<20}{r['hc_record']:>11}{r['hc_pct']:>8.2f}{r['unit_pct']:>10.2f}"
              f"{r['gap']:>+7.2f}{r['coord_seasons']:>5}  {r['detail'][:46]}")
    print('\n=== and the reverse — record better than the units ===')
    for r in have[-6:]:
        print(f"  {r['name']:<20}{r['hc_record']:>11}{r['hc_pct']:>8.2f}{r['unit_pct']:>10.2f}"
              f"{r['gap']:>+7.2f}{r['coord_seasons']:>5}  {r['detail'][:46]}")

if __name__ == '__main__':
    main()
