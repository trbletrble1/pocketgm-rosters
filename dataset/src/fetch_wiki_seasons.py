"""Fetch the enumerated league-season and team-season articles into wiki_cache/.

Reads build-reports/wikipedia-season-articles.json (enumerate_wiki_seasons.py).
Fetches ONLY titles that resolved on-target and exist. Writes the RAW MediaWiki
response, 20 titles per file, into ~/Documents/pgm3-sources/wiki_cache/ in the
cache's own shape, so ingest_wikipedia_photos.scan_cache() and everything else
that globs the cache read these exactly as they read the originals.

  rvprop=ids|timestamp|content  -- the REVISION ID is part of the attribution.
  redirects=1                   -- and the resolved target is recorded per page.

Never re-pulls a title already present in the cache. Serial, ~1/s, User-Agent
with contact, HTTP status read on every call; a non-200 is logged and the batch
is retried once after a pause, then skipped and reported.

  python3 src/fetch_wiki_seasons.py
"""
import os, sys, json, glob, time, hashlib, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
CACHE = os.path.expanduser("~/Documents/pgm3-sources/wiki_cache")
ENUM = os.path.join(BASE, "build-reports", "wikipedia-season-articles.json")
LOG = os.path.join(BASE, "build-reports", "wikipedia-season-fetch.json")
UA = "pgm3-archive-research/1.0 (NFL historical roster research; contact: ryannecci@gmail.com)"
DELAY = 1.0; BATCH = 20


from wiki_api import api     # hardened: backs off through outages, 5xx and 429 instead of raising


def cached_titles():
    have = set()
    for f in glob.glob(CACHE + "/*.json"):
        try: d = json.load(open(f))
        except Exception: continue
        for pg in ((d.get("query") or {}).get("pages") or {}).values():
            if pg.get("title") and "missing" not in pg: have.add(pg["title"])
    return have


def main():
    enum = json.load(open(ENUM))
    want, skipped = [], {"off_target": 0, "missing": 0, "already_cached": 0}
    have = cached_titles()
    for lg, v in enum["leagues"].items():
        for t, r in v.get("titles", {}).items():
            if r["off_target"]: skipped["off_target"] += 1; continue
            if not r["exists"]: skipped["missing"] += 1; continue
            tgt = r["target"]
            if tgt in have: skipped["already_cached"] += 1; continue
            want.append((lg, tgt))
        # standings TEMPLATES: the season articles transclude them, so the article wikitext
        # does not carry the standings -- the template text does. Fetched like any page.
        for t in v.get("standings_templates", {}):
            if t in have: skipped["already_cached"] += 1; continue
            want.append((lg, t))
    want = sorted(set(want))
    print(f"to fetch: {len(want)}   skipped {skipped}", flush=True)
    log = {"_date": "2026-09-07", "fetched": [], "http_errors": [], "skipped": skipped}
    for i in range(0, len(want), BATCH):
        chunk = [t for _, t in want[i:i + BATCH]]
        params = {"action": "query", "titles": "|".join(chunk), "redirects": 1,
                  "prop": "revisions", "rvprop": "ids|timestamp|content", "rvslots": "main"}
        code, d = api(params)
        if code != 200 or d is None:
            print(f"  HTTP {code} on batch {i // BATCH}; pausing 30s and retrying once", flush=True)
            time.sleep(30); code, d = api(params)
            if code != 200 or d is None:
                log["http_errors"].append({"batch": i // BATCH, "http": code, "titles": chunk}); continue
        d["_source"] = ("wikipedia league/team season articles, fetched 2026-09-07 (yearbooks session); "
                        "raw API response, revision ids included")
        key = hashlib.sha1("|".join(chunk).encode()).hexdigest()[:26]
        IO.dump_atomic(d, os.path.join(CACHE, f"{key}.json"))
        for pg in d.get("query", {}).get("pages", {}).values():
            rev = (pg.get("revisions") or [{}])[0]
            log["fetched"].append({"title": pg.get("title"), "revid": rev.get("revid"),
                                   "timestamp": rev.get("timestamp"), "missing": "missing" in pg,
                                   "bytes": len(((rev.get("slots") or {}).get("main") or {}).get("*") or "")})
        if (i // BATCH + 1) % 10 == 0:
            print(f"  batch {i // BATCH + 1}/{(len(want) + BATCH - 1) // BATCH}  fetched {len(log['fetched'])}", flush=True)
            IO.dump_atomic(log, LOG, indent=1)
    IO.dump_atomic(log, LOG, indent=1)
    zero = sum(1 for x in log["fetched"] if x["bytes"] == 0 and not x["missing"])
    print(f"\nfetched {len(log['fetched'])} pages; http errors {len(log['http_errors'])}; "
          f"zero-byte content {zero}; wrote {os.path.relpath(LOG, BASE)}", flush=True)


if __name__ == "__main__":
    main()
