#!/usr/bin/env python3
"""
extract_pfr_draft — a PFR draft listing saved as HTML into wip/draft_YYYY_pfr.csv.

  python3 tools/extract_pfr_draft.py 1981 1982 1983
  python3 tools/extract_pfr_draft.py --verify 1980      # reproduce the existing CSV

PFR CANNOT BE FETCHED FROM THIS SESSION, and the in-app browser does not change
that: it reaches the Cloudflare interstitial and the challenge does not clear
(two navigations, 26 seconds). That is bot detection, so it is not worked around.
The transport that DOES work costs Ryan one 'Save Page As' per year — the 1980
listing already in sources/1979PFR/ arrived exactly that way, and passing a saved
file to disk avoids the context limit that truncated the 1981 fetch at pick 185.

Save from:  https://www.pro-football-reference.com/years/YYYY/draft.htm
Save to:    $PGM3_SOURCES/1979PFR/   (any filename containing the year and 'Draft')

WHAT THE LISTING CARRIES, and why it closes three classes at once: Rnd, Pick, Tm,
Player, Pos, Age, To, AP1, PB, St, wAV, DrAV and College. The hindsight signal is
wAV and DrAV directly — no derivation — and a man who never played reads blank,
which is itself the signal. In the 1980 class wAV is present on 208 of 349.
"""
import re, html, csv, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import repo, sources

# `last_season`, not `last_year` — build_1979_draft.py reads that name, and the
# 1980 CSV it was written against uses it. All four classes must carry the SAME
# columns or they are rated on different bases: the original 1980 CSV lacked
# all_pro and seasons_started entirely, so raise_for() silently scored those two
# as zero for that class alone.
FIELDS = ['round', 'pick', 'team', 'name', 'pos', 'age', 'last_season', 'all_pro',
          'pro_bowls', 'seasons_started', 'career_av', 'draft_av', 'college']
STAT = {'round': 'draft_round', 'pick': 'draft_pick', 'team': 'team', 'name': 'player',
        'pos': 'pos', 'age': 'age', 'last_season': 'year_max', 'all_pro': 'all_pros_first_team',
        'pro_bowls': 'pro_bowls', 'seasons_started': 'years_as_primary_starter',
        'career_av': 'career_av', 'draft_av': 'draft_av', 'college': 'college_id'}

def find(year):
    # 'Draft Listing' first: a saved TEAM page ('... Team Draftees ...') also
    # matches '*{year}*Draft*' and parses to zero picks, which is how 1979 failed.
    pats = [f'*{year} NFL Draft Listing*.htm*', f'*{year}*Draft Listing*.htm*',
            f'*{year}*Draft*.html', f'*{year}*draft*.html', f'*{year}*Draft*.htm']
    for p in pats:
        hits = glob.glob(os.path.join(sources('1979PFR'), p))
        if hits:
            return hits[0]
    return None

def parse(path):
    w = open(path, encoding='utf-8', errors='ignore').read()
    out = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', w, re.S):
        c = {}
        for m in re.finditer(r'<t[hd][^>]*data-stat="([^"]+)"[^>]*>(.*?)</t[hd]>', tr, re.S):
            c[m.group(1)] = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
        if not c.get('player') or not c.get('draft_round', '').isdigit():
            continue                                   # header and separator rows
        # 'Anthony Munoz HOF' — the Hall of Fame marker is appended to the name
        name = re.sub(r'\s+HOF$', '', c['player']).strip()
        out.append({k: (name if k == 'name' else c.get(STAT[k], '')) for k in FIELDS})
    return out

def main():
    years = [a for a in sys.argv[1:] if a.isdigit()]
    verify = '--verify' in sys.argv
    assert years, 'give one or more years'
    for y in years:
        p = find(y)
        if p is None:
            print(f'{y}: NOT ON DISK. Save the listing from '
                  f'https://www.pro-football-reference.com/years/{y}/draft.htm into '
                  f'{sources("1979PFR")}/')
            continue
        rows = parse(p)
        assert rows, f'{y}: parsed zero picks from {os.path.basename(p)}'
        av = sum(1 for r in rows if r['career_av'].isdigit())
        out = repo('wip', f'draft_{y}_pfr.csv')
        if verify and os.path.exists(out):
            old = list(csv.DictReader(open(out)))
            same = sum(1 for a, b in zip(old, rows) if a.get('name') == b['name'])
            print(f'{y}: {len(rows)} picks parsed; existing CSV has {len(old)}; '
                  f'names agree on {same}')
            continue
        w = csv.DictWriter(open(out, 'w', newline=''), fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
        print(f'{y}: {len(rows)} picks -> wip/draft_{y}_pfr.csv   '
              f'(wAV present on {av}, blank means he never played)')

if __name__ == '__main__':
    main()
