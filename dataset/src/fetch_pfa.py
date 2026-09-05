"""Targeted fetch from profootballarchives.com, driven by the CDX page list.

NOT a crawl. The CDX API gave us every archived URL for the domain; we fetch the
ones we want from the LIVE site, which is current and fast. Ryan's own crawler
managed 5,800 junk pages in 3.5 hours; this is a different job.

Same transport disciplines as every other fetcher here:
  - fetch FIRST, write to .part, rename atomically. A cache must never be able
    to store a failure.
  - a zero-byte file already on disk is deleted, not served.
  - one request per second or slower. Never re-fetch a page we hold.

  python3 src/fetch_pfa.py <group>       groups: priority | list
"""
import os, sys, re, json, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (research; contact ryannecci@gmail.com)"
CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa")
PAGES = "/tmp/pfa_pages.json"
DELAY = 1.0

# The leagues StatsCrew cannot supply, plus the CFL predecessor unions it
# back-maps. This is the whole reason for the source.
PRIORITY = re.compile(r"^/?(\d{4})(irfu|wifu|orfu|afl)([a-z0-9\-]*)\.html$")


def fetch(path):
    key = path.strip("/").replace("/", "_")
    p = os.path.join(CACHE, key)
    if os.path.exists(p) and os.path.getsize(p) == 0:
        os.remove(p)
    if os.path.exists(p):
        return "cached"
    url = "https://www.profootballarchives.com/" + path.strip("/")
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return f"http{e.code}"
    if not data:
        return "empty - not cached"
    tmp = p + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, p)
    time.sleep(DELAY)
    return "fetched"


def main():
    group = sys.argv[1] if len(sys.argv) > 1 else "priority"
    os.makedirs(CACHE, exist_ok=True)
    pages = json.load(open(PAGES))
    want = sorted({p for p in pages if PRIORITY.match(p)})
    if group == "list":
        import collections
        c = collections.Counter(PRIORITY.match(p).group(2) for p in want)
        print(f"priority pages: {len(want)}")
        for k, v in c.most_common(): print(f"   {k}: {v}")
        return 0
    print(f"priority pages to fetch: {len(want)}", flush=True)
    n = {"fetched": 0, "cached": 0}
    bad = []
    for i, p in enumerate(want):
        r = fetch(p)
        if r in n: n[r] += 1
        else: bad.append((p, r))
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(want)}] fetched={n['fetched']} cached={n['cached']} "
                  f"failed={len(bad)}", flush=True)
    print(f"\nfetched {n['fetched']}  already held {n['cached']}  failed {len(bad)}")
    for p, r in bad[:10]: print(f"   {p}: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
