"""Enumerate the unheld professional archive.org texts: the document-class sweep's
"1,730 professional items, 1950-onward, with text, none held" and the
`pro-football-preview` collection (406 items, 1954-2025).

The sweep's own list was never written down, so this re-derives it from
archive.org's search API and WRITES IT DOWN:
    build-reports/ia-unheld-pro-items.json

THE TRAPS, ALL APPLIED HERE, NONE BY SIZE:
  - cover-only items: the reliable test is a `DjVuTXT` entry in `format`; item size
    means nothing (a 16.5 MB item was one PNG). Items without DjVuTXT are listed
    separately as `no_text`, never queued.
  - sport collisions: 14 items in the account share names with MLB clubs. Titles
    naming an MLB/NHL/NBA/MLS/college programme are excluded by token and the
    exclusion is listed so it can be checked; the fetch step also sport-checks the
    text (football vs baseball vocabulary), because the title is not enough.
  - containers: items whose `files` hold more than one document are detected at
    fetch time (the metadata call is required anyway); the enumeration flags
    identifiers whose title smells of an archive/collection.
  - the local index is the truth for "held": identifiers in nfl-books/index.csv
    are skipped, whatever archive.org says.

archive.org advancedsearch, descriptive User-Agent with contact, serial, HTTP status
read on every call; paging by `page`, 500 rows a page.

  python3 src/enumerate_ia_unheld.py
"""
import os, re, sys, csv, json, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
OUT = os.path.join(BASE, "build-reports", "ia-unheld-pro-items.json")
INDEX = os.path.expanduser("~/Documents/pgm3-sources/nfl-books/index.csv")
UA = "pgm3-archive-research/1.0 (NFL historical roster research; contact: ryannecci@gmail.com)"
UPLOADER = "wwittler@hotmail.com"
FIELDS = ["identifier", "title", "year", "format", "collection", "item_size", "mediatype"]

PRO = re.compile(r"\b(NFL|AFL|CFL|USFL|XFL|WFL|UFL|AAFC|WLAF|NFL Europe|Arena|pro football|professional football|"
                 r"49ers|Bears|Bengals|Bills|Broncos|Browns|Buccaneers|Cardinals|Chargers|Chiefs|Colts|Commanders|Cowboys|"
                 r"Dolphins|Eagles|Falcons|Giants|Jaguars|Jets|Lions|Oilers|Packers|Panthers|Patriots|Raiders|Rams|Ravens|"
                 r"Redskins|Saints|Seahawks|Steelers|Texans|Titans|Vikings|Argonauts|Stampeders|Alouettes|Roughriders|"
                 r"Rough Riders|Blue Bombers|Eskimos|Elks|Tiger-Cats|BC Lions|Renegades|Redblacks|Super Bowl|Grey Cup)\b", re.I)
NOT_PRO = re.compile(r"\b(MLB|NHL|NBA|MLS|baseball|hockey|basketball|soccer|lacrosse|Yankees|Dodgers|Red Sox|Mets|Cubs|"
                     r"Braves|Phillies|Pirates|Reds|Indians|Guardians|Tigers|Twins|Orioles|Nationals|Astros|Angels|Mariners|"
                     r"Padres|Expos|Brewers|Royals|Athletics|Rockies|Marlins|Diamondbacks|Blue Jays|Rangers|White Sox|"
                     r"university|college|football program|high school|NCAA|bowl game)\b", re.I)
CLASS = [("media guide", r"media guide|press guide|press book|record book|record manual"),
         ("yearbook", r"yearbook|year book"), ("program", r"\bprogram\b|programme|gameday|game day"),
         ("preview annual", r"preview|annual|handbook|digest|almanac|magazine|register|prospectus"),
         ("other", r".")]


def search(q, page):
    params = {"q": q, "rows": 500, "page": page, "output": "json"}
    for f in FIELDS: params.setdefault("fl[]", []);
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({"q": q, "rows": 500, "page": page, "output": "json"}) + \
          "".join(f"&fl[]={f}" for f in FIELDS)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                code = r.status; d = json.loads(r.read())
            time.sleep(1.0)
            return code, d
        except Exception as e:
            wait = [15, 30, 60, 120, 300, 600][attempt]
            print(f"  [ia] {type(e).__name__}: {e} -- waiting {wait}s", flush=True); time.sleep(wait)
    raise RuntimeError("archive.org search unavailable")


def all_docs(q):
    docs, page = [], 1
    while True:
        code, d = search(q, page)
        r = d.get("response", {}); got = r.get("docs", [])
        docs += got
        print(f"   page {page}: HTTP {code}, {len(got)} docs, numFound {r.get('numFound')}", flush=True)
        if len(docs) >= r.get("numFound", 0) or not got: break
        page += 1
    return docs


def classify(title):
    for name, pat in CLASS:
        if re.search(pat, title, re.I): return name
    return "other"


def main():
    held = {r["identifier"] for r in csv.DictReader(open(INDEX))}
    print(f"held identifiers in index.csv: {len(held)}", flush=True)
    result = {"_what": "unheld professional archive.org texts, 1950-onward, re-derived from the search API; "
                       "with_text requires DjVuTXT in format; excluded lists are written so the exclusion can be checked",
              "_date": "2026-09-07", "held_in_index": len(held), "queries": {}, "candidates": [], "no_text": [],
              "excluded_not_pro": [], "excluded_pre1950": [], "container_suspects": []}
    queries = {
        "pro-football-preview": f'collection:pro-football-preview AND mediatype:texts',
        "account-pro-1950on": f'uploader:"{UPLOADER}" AND mediatype:texts AND year:[1950 TO 2026]',
    }
    seen = set()
    for name, q in queries.items():
        print(f"== {name}: {q}", flush=True)
        docs = all_docs(q)
        result["queries"][name] = {"q": q, "numFound": len(docs)}
        for x in docs:
            ident = x.get("identifier"); title = str(x.get("title") or "")
            if not ident or ident in seen: continue
            seen.add(ident)
            if ident in held: continue
            fmt = x.get("format") or []; fmt = [fmt] if isinstance(fmt, str) else fmt
            yr = x.get("year"); yr = int(str(yr)[:4]) if yr and str(yr)[:4].isdigit() else None
            rec = {"identifier": ident, "title": title, "year": yr, "query": name, "class": classify(title),
                   "item_size": x.get("item_size"), "collection": x.get("collection")}
            if name != "pro-football-preview" and (not PRO.search(title) or NOT_PRO.search(title)):
                result["excluded_not_pro"].append(rec); continue
            if name != "pro-football-preview" and yr is not None and yr < 1950:
                result["excluded_pre1950"].append(rec); continue
            if "DjVuTXT" not in fmt:
                result["no_text"].append(rec); continue
            if re.search(r"archive|collection|complete set|volumes?\b|\bset\b", title, re.I):
                rec["container_suspect"] = True; result["container_suspects"].append(ident)
            result["candidates"].append(rec)
    by = {}
    for r in result["candidates"]:
        k = f"{r['query']}/{r['class']}"; by[k] = by.get(k, 0) + 1
    result["counts"] = {"candidates_with_text": len(result["candidates"]), "no_text": len(result["no_text"]),
                        "excluded_not_pro": len(result["excluded_not_pro"]), "excluded_pre1950": len(result["excluded_pre1950"]),
                        "container_suspects": len(result["container_suspects"]), "by_query_and_class": by}
    IO.dump_atomic(result, OUT, indent=1)
    print(json.dumps(result["counts"], indent=1), flush=True)
    print(f"wrote {os.path.relpath(OUT, BASE)}", flush=True)


if __name__ == "__main__":
    main()
