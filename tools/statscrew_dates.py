#!/usr/bin/env python3
"""Gather birth dates from StatsCrew for a list of names. Cached, 1.1s apart.

THE SEARCH FIELD MATTERS: filling `searchnamefirst` returns nothing at all, so
every query is last-name-only and the man is matched out of the candidate list.
The strict form scored 5 of 29 where this scores 20 of 29 — a fact about the
query that read exactly like a fact about the source.
"""
import os, re, sys, csv, html, time, hashlib, urllib.request, urllib.parse, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statscrew import fetch, CACHE, UA, BASE


def norm(x):
    x = unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', x)


def search_last(last):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, 'searchL_' + hashlib.sha1(last.encode()).hexdigest()[:16] + '.html')
    if os.path.exists(f):
        return open(f, encoding='utf-8', errors='replace').read()
    time.sleep(1.1)
    data = urllib.parse.urlencode({'searchnamelast': last, 'searchnamefirst': '', 'searchteam': ''}).encode()
    req = urllib.request.Request(BASE + '/football/search', data=data, headers={'User-Agent': UA})
    b = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', errors='replace')
    open(f, 'w', encoding='utf-8').write(b)
    return b


def candidates(last):
    d = search_last(last)
    ids = re.findall(r'/football/stats/p-([a-z0-9]+)', d)
    t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', d)))
    seg = t.split('Results:', 1)[1] if 'Results:' in t else t
    names = re.findall(r"([A-Z][A-Za-z'\-\.]+),\s+([A-Z][A-Za-z'\-\.\s]{1,20}?)(?=\s+[A-Z][A-Za-z'\-\.]+,|\s+Football)", seg)
    return list(zip(ids, [f'{f.strip()} {l}' for l, f in names])) if len(names) == len(ids) else [(i, '') for i in ids]


def born(pid):
    doc, _ = fetch(f'/football/stats/p-{pid}')
    t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', doc)))
    m = re.search(r'Born:\s*([A-Z][a-z]+ \d{1,2}, \d{4})', t)
    if not m:
        return None
    c = re.search(r'Career:\s*(\d{4})-(\d{4})', t)
    return (m.group(1), int(c.group(1)) if c else None, int(c.group(2)) if c else None)


# PLAUSIBILITY, and the pass that lacked it produced Joe Gibbs born 1988 and a
# head coach aged -16. A name match on a century-wide database is not an identity
# match: StatsCrew holds every professional footballer since 1920, so "Joe Gibbs"
# and "Leeman Bennett" each return a modern player as readily as the man wanted.
# A 1979 staff member must have been born early enough to be an adult that year
# and not so early as to be implausible, and if his playing career is known it
# must have started before he was coaching.
def plausible(birth_year, career_start, season=1979, lo=25, hi=80):
    age = season - birth_year
    if not (lo <= age <= hi):
        return False
    if career_start and career_start > season:
        return False
    return True


def lookup(name):
    parts = name.split(' ', 1)
    if len(parts) < 2:
        return None, None
    first, last = parts
    cands = candidates(last)
    for exact in (True, False):
        for pid, label in cands:
            if not label:
                continue
            ok = norm(label) == norm(name) if exact else (
                norm(label.split()[-1]) == norm(last) and norm(label.split()[0])[:3] == norm(first)[:3])
            if not ok:
                continue
            got = born(pid)
            if not got:
                continue
            b, cs, ce = got
            if plausible(int(b.split(', ')[1]), cs):
                return pid, b
    return None, None


if __name__ == '__main__':
    names = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    w = csv.writer(open(sys.argv[2], 'w', newline=''))
    w.writerow(['name', 'statscrew_id', 'born'])
    hit = 0
    for n in names:
        pid, b = lookup(n)
        if b:
            hit += 1
        w.writerow([n, pid or '', b or ''])
    print(f'  {hit} of {len(names)} dated by StatsCrew')
