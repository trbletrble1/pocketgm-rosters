#!/usr/bin/env python3
"""
build_1979_coach_pool — the free-agent coaching pool for 1979, in Ryan's tiers,
with every man's record and why he was available. Writes wip/coach_pool_1979.csv.
REPORTS ONLY: it allocates nobody to a franchise.

  python3 tools/build_1979_coach_pool.py

WHY. Every published file carries ~165 free-agent staff, 21-33 of them head
coaches. 1979 currently ships with none, which is the defect fixed in 2026 this
session — a user who fires a coordinator must have somebody to hire. And 2021's
pool is entirely invented (Jocelyn Lyndhurst, Quill Kestrel), which is on the
audit list and is not reproduced here. Every man below is real.

TIERS:
  1  Recently out — last head-coaching season 1975-1978. The core.
  2  Long out — last season 1974 or earlier, ALIVE in 1979. Retired names an
     expansion team could plausibly tempt back; the same reasoning that put Jim
     Otis and Otis Sistrunk in the player pool.
  3  College — not here. They have no NFL record and need their own source and a
     stated rating method.

DEATH IS A HARD GATE, checked rather than assumed: Vince Lombardi died in 1970.
Each man's article is read for a death year and anyone dead before 1979 is
dropped by name. A man with no birth year whose last season predates 1960 is held
out as unverifiable rather than guessed at.

RATING METHOD, stated because it is a choice and a weak one:
  career winning percentage, quantile-mapped onto the published Head Coach band
  with the plotting position, exactly as 1979's sitting coaches were mapped from
  the mod's own view of them. Winning percentage is the only measure every man in
  both tiers has, and it rewards men who coached good teams — Bill Arnsparger
  built Miami's No-Name Defense and comes out near the floor on a 7-28 head
  coaching record. The basis is printed beside every name so Ryan can overrule
  any of it. Men with fewer than 16 games are held OUT of the mapping entirely
  and take the band's lower third: a 9-game record is noise, not a rating.
"""
import csv, sys, os, re, json, urllib.request, urllib.parse, time, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo

UA = {'User-Agent': 'pocketgm-rosters/1.0 (historical roster research; ryannecci@gmail.com)'}
DEATHS = '/tmp/coach_deaths.json'
MIN_GAMES = 16
MAX_AGE = 75

def plausible(rec, first, last):
    """A man's own coaching record is the anchor for his biography.

    The Wikipedia lookup collides on namesakes — the fifth time in this build.
    George Allen returned 1952, which is his SON the senator, making the coach 27
    in 1979; John Ralston returned a birth year making him 33; and 'George Wilson'
    returned a man who died in 1912, thirty years before the Lions coach started.

    No fetch fixes this reliably, but the record does: nobody is a head coach at
    24, and nobody coaches after he dies. Both gates come free from data already
    parsed, and a bio failing either is discarded rather than trusted."""
    b, d = rec.get('born'), rec.get('died')
    # A man who has already FINISHED an NFL head-coaching career is not in his
    # twenties. 'at least 25 at his first season' was too loose — it passed a
    # birth year of 1951 for the Bengals' Bill Johnson, making him 28 in 1979
    # with a completed career. Thirty-five in 1979 is the floor, and a bio that
    # fails it is discarded rather than corrected, because we do not know which
    # namesake it belongs to.
    if b is not None and (first - b < 25 or 1979 - b < 35):
        rec['born'] = None
    if d is not None and d < last:
        rec['died'] = None
    return rec

def bios(men):
    """Birth and death years, from each man's own article.

    THE ARTICLE MUST BE ABOUT THE RIGHT MAN, and that is verified rather than
    hoped for. The lookup collides on namesakes — the fifth time in this build:
    George Allen returned 1952, which is his SON the senator; 'George Wilson'
    returned a man who died in 1912, thirty years before the Lions coach began.
    An age gate alone was too loose to catch it — a birth year of 1948 for the
    Bengals' Bill Johnson still cleared 'at least 25 at his first season'.

    So the article has to NAME ONE OF HIS TEAMS. That is what identifies him, and
    a page that does not is discarded rather than mined for a year."""
    cache = json.load(open(DEATHS)) if os.path.exists(DEATHS) else {}
    todo = [m for m in men if m['name'] not in cache]
    for i, m in enumerate(todo):
        n = m['name']
        nick = {t.strip().split()[-1] for t in m['teams'].split(';') if t.strip()}
        w = ''
        for title in (n, f'{n} (American football)', f'{n} (American football coach)'):
            u = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
                {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
                 'format': 'json', 'titles': title, 'redirects': 1})
            try:
                p = list(json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))['query']['pages'].values())[0]
                w = p['revisions'][0]['slots']['main']['*'] if 'revisions' in p else ''
            except Exception:
                w = ''
            if any(k in w for k in nick):
                break
            w = ''                       # wrong man, or the wrong article — do not mine it
        d = re.search(r'\{\{ *[Dd]eath[ _]date(?: and age)? *\|(?: *mf *= *\w+ *\|)? *(\d{4})', w)
        b = re.search(r'\{\{ *[Bb]irth[ _]date(?: and age)? *\|(?: *mf *= *\w+ *\|)? *(\d{4})', w)
        if not b:
            b = re.search(r'born[^)\n]{0,60}?\b(18\d\d|19[0-5]\d)\b', w[:3000])
        if not d:
            d = re.search(r'died[^)\n]{0,60}?\b(19\d\d|20[0-2]\d)\b', w[:3000])
        cache[n] = {'died': int(d.group(1)) if d else None,
                    'born': int(b.group(1)) if b else None,
                    'matched': bool(w)}
        time.sleep(0.2)
        if (i + 1) % 30 == 0:
            json.dump(cache, open(DEATHS, 'w')); print(f'    ...{i + 1}/{len(todo)}')
    json.dump(cache, open(DEATHS, 'w'))
    return cache

def hc_band():
    out = []
    for y in ('1986', '2004', '2007', '2010', '2013', '2017', '2021'):
        p = repo(f'PGMStaff_{y}.json')
        if os.path.exists(p):
            out += [x['rating'] for x in json.load(open(p)) if x['role'] == 'Head Coach']
    return sorted(out)

def main():
    raw = list(csv.DictReader(open(repo('wip', 'coach_pool_1979_raw.csv'))))
    for x in raw:
        for k in ('first', 'last', 'gc', 'w', 'l', 't', 'spells'):
            x[k] = int(x[k])
    sitting = {x['head_coach'] for x in csv.DictReader(open(repo('wip', 'staff_1979_sources.csv')))}
    pool = [x for x in raw if x['last'] < 1979 and x['name'] not in sitting]
    print(f'{len(pool)} men last coached before 1979 and are not sitting 1979 head coaches')
    print('fetching birth and death years...')
    bio = bios(pool)

    for x in pool:
        bio[x['name']] = plausible(bio.get(x['name'], {}), x['first'], x['last'])
    dead = [x for x in pool if (bio.get(x['name'], {}).get('died') or 9999) < 1979]
    alive = [x for x in pool if x not in dead]
    print(f'  dead by 1979, dropped: {len(dead)}')
    print('    ' + ', '.join(f"{x['name']} (d.{bio[x['name']]['died']})"
                             for x in sorted(dead, key=lambda z: bio[z['name']]['died'])[:8]) + ' ...')
    keep = []
    unverif = 0
    for x in alive:
        b = bio.get(x['name'], {}).get('born')
        x['born'], x['age79'] = b, (1979 - b if b else None)
        if b is None and x['last'] < 1960:
            unverif += 1; continue                       # almost certainly dead; not guessed at
        if x['age79'] and x['age79'] > MAX_AGE:
            continue
        x['tier'] = 1 if x['last'] >= 1975 else 2
        x['winpct'] = x['w'] / max(1, x['gc'])
        x['why'] = f"last coached {x['last']}, {x['teams'].split(';')[0].strip()}"
        keep.append(x)
    print(f'  held out as unverifiable (no birth year, last coached before 1960): {unverif}')
    nomatch = sum(1 for x in pool if not bio.get(x['name'], {}).get('matched'))
    print(f'  articles that never named one of his teams (identity unconfirmed): {nomatch}')
    print(f'  alive, aged {MAX_AGE} or under: {len(keep)}')

    band = hc_band()
    rated = sorted([x for x in keep if x['gc'] >= MIN_GAMES], key=lambda x: x['winpct'])
    for i, x in enumerate(rated):
        q = (i + 0.5) / len(rated)                        # plotting position, as everywhere else
        x['rating'] = band[min(len(band) - 1, int(round(q * (len(band) - 1))))]
        x['basis'] = f"career {x['w']}-{x['l']}-{x['t']} ({x['winpct']:.3f}) on the published band"
    for x in keep:
        if x['gc'] < MIN_GAMES:
            x['rating'] = band[len(band) // 6]
            x['basis'] = f"only {x['gc']} games — band's lower third, record too short to rank"

    keep.sort(key=lambda x: (x['tier'], -x['rating']))
    f = open(repo('wip', 'coach_pool_1979.csv'), 'w', newline='')
    wr = csv.writer(f)
    wr.writerow(['tier', 'name', 'age_1979', 'first', 'last', 'record', 'win_pct',
                 'teams', 'rating', 'rating_basis', 'why_available'])
    for x in keep:
        wr.writerow([x['tier'], x['name'], x['age79'] or '', x['first'], x['last'],
                     f"{x['w']}-{x['l']}-{x['t']}", f"{x['winpct']:.3f}", x['teams'],
                     x['rating'], x['basis'], x['why']])
    f.close()
    n1 = sum(1 for x in keep if x['tier'] == 1)
    print(f'\nwrote wip/coach_pool_1979.csv: {n1} tier 1, {len(keep) - n1} tier 2')
    for tier, label in ((1, 'TIER 1 — recently out of the NFL, last season 1975-78'),
                        (2, 'TIER 2 — long out of it, alive in 1979')):
        v = [x for x in keep if x['tier'] == tier]
        print(f'\n=== {label} ({len(v)}) ===')
        print(f"  {'name':<22}{'age':>4}{'record':>13}{'pct':>7}{'rtg':>5}  last, and where")
        for x in v:
            rec = f"{x['w']}-{x['l']}-{x['t']}"
            print(f"  {x['name']:<22}{str(x['age79'] or '?'):>4}{rec:>13}{x['winpct']:>7.3f}"
                  f"{x['rating']:>5}  {x['last']}  {x['teams'][:44]}")

if __name__ == '__main__':
    main()
