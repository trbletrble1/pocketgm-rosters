"""Fetch the standings TEMPLATES the cached season articles transclude.

The census of the 1,207 fetched season articles (2026-09-07 08:05) found that most
league-season standings are not in the article at all: they are transcluded --
{{1975 CFL West Division standings}}, {{1987 Arena Football League Standings}},
{{2024 UFL standings}} ... ~650 of them across CFL, Arena, UFL, XFL and USFL --
and template pages are not category members, so the enumerator never saw them.
This scans the cached article wikitext for those transclusions, turns each into a
Template: title, and fetches the ones not already cached, raw, with revision ids,
into wiki_cache/ in the cache's own shape.

  python3 src/fetch_wiki_standings_templates.py
"""
import os, re, sys, json, glob, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
from wiki_api import api
CACHE = os.path.expanduser("~/Documents/pgm3-sources/wiki_cache")
LOG = os.path.join(BASE, "build-reports", "wikipedia-standings-templates-fetch.json")
MARK = "wikipedia league/team season"
TRANS = re.compile(r"\{\{\s*((?:19|20)\d{2}(?:[–-]\d{2,4})? [^{}|\n]*?(?:[Ss]tandings|[Tt]able))\s*(?:\||\}\})")


def main():
    have, arts = set(), {}
    for f in glob.glob(CACHE + "/*.json"):
        try: d = json.load(open(f))
        except Exception: continue
        mine = MARK in str(d.get("_source", ""))
        for pg in (d.get("query") or {}).get("pages", {}).values():
            if pg.get("title") and "missing" not in pg: have.add(pg["title"])
            if mine and "revisions" in pg:
                arts[pg["title"]] = ((pg["revisions"][0].get("slots") or {}).get("main") or {}).get("*") or ""
    want = set()
    for t, txt in arts.items():
        for m in TRANS.findall(txt):
            name = re.sub(r"\s+", " ", m).strip()
            want.add("Template:" + name)
    todo = sorted(x for x in want if x not in have)
    print(f"articles scanned {len(arts)}; distinct standings transclusions {len(want)}; to fetch {len(todo)}", flush=True)
    log = {"_date": "2026-09-07", "transclusions": sorted(want), "fetched": [], "missing": [], "http_errors": []}
    for i in range(0, len(todo), 20):
        chunk = todo[i:i + 20]
        params = {"action": "query", "titles": "|".join(chunk), "redirects": 1,
                  "prop": "revisions", "rvprop": "ids|timestamp|content", "rvslots": "main"}
        code, d = api(params)
        if code != 200 or d is None:
            log["http_errors"].append({"batch": i // 20, "http": code, "titles": chunk}); continue
        d["_source"] = "wikipedia standings templates transcluded by the season articles, fetched 2026-09-07 (yearbooks session)"
        IO.dump_atomic(d, os.path.join(CACHE, hashlib.sha1("|".join(chunk).encode()).hexdigest()[:26] + ".json"))
        for pg in d.get("query", {}).get("pages", {}).values():
            if "missing" in pg: log["missing"].append(pg.get("title")); continue
            rev = (pg.get("revisions") or [{}])[0]
            log["fetched"].append({"title": pg.get("title"), "revid": rev.get("revid"), "timestamp": rev.get("timestamp"),
                                   "bytes": len(((rev.get("slots") or {}).get("main") or {}).get("*") or "")})
        if (i // 20 + 1) % 10 == 0: print(f"  batch {i // 20 + 1}/{(len(todo) + 19) // 20}", flush=True)
    IO.dump_atomic(log, LOG, indent=1)
    print(f"fetched {len(log['fetched'])} templates; missing {len(log['missing'])}; http errors {len(log['http_errors'])}; "
          f"wrote {os.path.relpath(LOG, BASE)}", flush=True)


if __name__ == "__main__":
    main()
