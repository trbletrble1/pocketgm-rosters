#!/usr/bin/env python3
"""Birth dates from the Coaching Tree, over its HTTP MCP endpoint, cached.

The server speaks plain JSON-RPC over POST, so a whole cohort can be gathered in
one pass instead of one tool call per man. Slugs are `first-last` lowercased;
where that misses, `search_coaches` finds the real slug.
"""
import os, re, sys, csv, json, time, hashlib, unicodedata, urllib.request

URL = 'https://coaching-tree.app/mcp'
CACHE = os.path.join(os.environ.get('PGM3_SOURCES', os.path.expanduser('~/Documents/pgm3-sources')),
                     'coachingtree')
_id = [10]


def call(tool, args):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, tool + '_' + hashlib.sha1(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16] + '.json')
    if os.path.exists(f):
        return json.load(open(f))
    time.sleep(0.4)
    _id[0] += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id[0], 'method': 'tools/call',
                       'params': {'name': tool, 'arguments': args}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
    raw = urllib.request.urlopen(req, timeout=40).read().decode()
    try:
        txt = json.loads(raw)['result']['content'][0]['text']
        out = json.loads(txt)
    except Exception:
        out = {'error': raw[:200]}
    json.dump(out, open(f, 'w'))
    return out


def slugify(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def birth(name):
    o = call('get_coach', {'slug': slugify(name)})
    if isinstance(o, dict) and o.get('birth_date'):
        return o['birth_date'], slugify(name)
    hits = call('search_coaches', {'query': name.split(' ', 1)[1]})
    cands = hits if isinstance(hits, list) else hits.get('results', hits.get('coaches', []))
    for c in cands or []:
        if not isinstance(c, dict):
            continue
        if slugify(c.get('name', '')) == slugify(name):
            o = call('get_coach', {'slug': c['slug']})
            if o.get('birth_date'):
                return o['birth_date'], c['slug']
    return None, None


if __name__ == '__main__':
    names = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    w = csv.writer(open(sys.argv[2], 'w', newline=''))
    w.writerow(['name', 'slug', 'birth_date'])
    hit = 0
    for n in names:
        try:
            b, s = birth(n)
        except Exception as e:
            b, s = None, None
        if b:
            hit += 1
        w.writerow([n, s or '', b or ''])
    print(f'  {hit} of {len(names)} dated by the Coaching Tree')
