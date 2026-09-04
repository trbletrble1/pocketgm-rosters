#!/usr/bin/env python3
"""
statscrew — a cached, rate-limited fetcher for statscrew.com, and a roster parser.

    python3 tools/statscrew.py drift          # column drift across five eras
    python3 tools/statscrew.py roster CLE 1950
    python3 tools/statscrew.py index NFL 1950

THE SITE IS ONE PERSON'S WORK. Every page is cached on first fetch and never
requested twice; a run that hits only cached pages makes no network calls at all.
Requests are spaced by at least a second and carry a contact address.

THE CACHE LIVES OUTSIDE THE SCRATCHPAD, under `$PGM3_SOURCES/statscrew/raw/`,
because /tmp was wiped mid-session on 2026-09-04 and took every uncommitted dump
with it. Anything expensive to re-obtain belongs on durable disk.

URL patterns, confirmed reachable 2026-09-04 (HTTP 200, raw HTML, no Cloudflare):
    /football/roster/t-{TEAM}/y-{YEAR}
    /football/l-{LEAGUE}/y-{YEAR}
"""
import os, re, sys, time, hashlib, urllib.request, html as htmllib

BASE = 'https://www.statscrew.com'
UA = 'pocketgm-rosters archival research (contact ryannecci@gmail.com)'
CACHE = os.path.join(os.environ.get('PGM3_SOURCES', os.path.expanduser('~/Documents/pgm3-sources')),
                     'statscrew', 'raw')
_last = [0.0]


def fetch(path):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(path.encode()).hexdigest()[:16] + '_' + re.sub(r'[^A-Za-z0-9]+', '_', path).strip('_')[-60:]
    f = os.path.join(CACHE, key + '.html')
    if os.path.exists(f):
        return open(f, encoding='utf-8', errors='replace').read(), True
    wait = 1.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(BASE + path, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode('utf-8', errors='replace')
    _last[0] = time.time()
    open(f, 'w', encoding='utf-8').write(body)
    return body, False


def tables(doc):
    """Every <table> as (headers, rows-of-cells), tags stripped."""
    out = []
    for t in re.findall(r'<table[^>]*>(.*?)</table>', doc, re.S | re.I):
        rows = []
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S | re.I):
            cells = [htmllib.unescape(re.sub(r'<[^>]+>', '', c)).strip()
                     for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S | re.I)]
            if cells:
                rows.append(cells)
        if rows:
            out.append((rows[0], rows[1:]))
    return out


def roster_table(doc):
    """The widest table that looks like a roster (has a Player-ish column)."""
    best = None
    for head, rows in tables(doc):
        joined = ' '.join(head).lower()
        if 'player' in joined or 'name' in joined:
            if best is None or len(head) > len(best[0]):
                best = (head, rows)
    return best


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'drift'
    if cmd == 'roster':
        team, year = sys.argv[2], sys.argv[3]
        doc, cached = fetch(f'/football/roster/t-{team}/y-{year}')
        head, rows = roster_table(doc) or ([], [])
        print(f'{team} {year}  {"cached" if cached else "fetched"}  {len(rows)} rows')
        print('  columns:', head)
        for r in rows[:5]:
            print('   ', r)
        return
    if cmd == 'index':
        league, year = sys.argv[2], sys.argv[3]
        doc, cached = fetch(f'/football/l-{league}/y-{year}')
        teams = sorted(set(re.findall(r'/football/roster/t-([A-Za-z0-9]+)/y-%s' % year, doc)))
        print(f'{league} {year}  {"cached" if cached else "fetched"}  teams: {teams}')
        return

    # ---- drift: the same question asked of five eras ---------------------
    ERAS = [('NFL', 1920), ('NFL', 1950), ('NFL', 1979), ('NFL', 2000), ('NFL', 2020)]
    print('column drift across a century — one team per era\n')
    seen = {}
    for league, year in ERAS:
        doc, cached = fetch(f'/football/l-{league}/y-{year}')
        teams = sorted(set(re.findall(r'/football/roster/t-([A-Za-z0-9]+)/y-%d' % year, doc)))
        if not teams:
            print(f'{year}: no team links found on the season index'); continue
        team = teams[0]
        rdoc, rcached = fetch(f'/football/roster/t-{team}/y-{year}')
        got = roster_table(rdoc)
        if not got:
            print(f'{year} {team}: no roster table found'); continue
        head, rows = got
        seen[year] = head
        print(f'{year}  {team:<5} {len(teams):>2} teams in the league, {len(rows):>3} men'
              f'   [{"cached" if cached and rcached else "fetched"}]')
        print(f'   columns ({len(head)}): {head}')
        if rows:
            print(f'   first row: {rows[0]}')
        print()
    if len(seen) > 1:
        base = None
        print('drift:')
        for y in sorted(seen):
            cols = seen[y]
            if base is None:
                base = cols; print(f'   {y}: baseline, {len(cols)} columns'); continue
            added = [c for c in cols if c not in base]
            gone = [c for c in base if c not in cols]
            print(f'   {y}: {len(cols)} columns'
                  + (f'   gained {added}' if added else '')
                  + (f'   lost {gone}' if gone else '')
                  + ('   identical to the previous era' if not added and not gone else ''))
            base = cols


if __name__ == '__main__':
    main()
