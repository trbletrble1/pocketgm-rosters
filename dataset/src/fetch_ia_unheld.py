"""Fetch the unheld professional archive.org texts into the guide corpus.

Reads build-reports/ia-unheld-pro-items.json (enumerate_ia_unheld.py). For each
candidate: the metadata call (REQUIRED -- the OCR file is not named after the
identifier), then the `_djvu.txt`, stored EXACTLY as fetch_guides.py stores media
guides -- nfl-books/meta/<id>.json, nfl-books/text_all/<id>.txt, `.notext` marker when
the item has no text -- and a row appended to nfl-books/index.csv with the same fields
(year, identifier, league_wide, restricted, title). Text only, never the PDFs.

THE TRAPS, applied at fetch time where they can actually be seen:
  - cover-only: no `_djvu.txt` in `files` -> `.notext` marker, listed, never a failure
  - CONTAINER: more than one `_djvu.txt` (or more than one document PDF) in `files`
    -> the item is a collection of documents; recorded in `containers`, NOT fetched
    as if it were one book. Its year is usually an institution's founding.
  - sport collision: the fetched text is scored on football vs baseball/hockey/
    basketball vocabulary; a text that reads as another sport is kept on disk (it was
    fetched) but flagged `sport_mismatch` and NOT added to the index.
  - byte counts: every stored text's size is logged; anything under 2,000 bytes is
    listed by name -- a 341-byte text has passed every non-empty check before.
  - per-player content: a cheap heuristic (PERSONAL/COLLEGE/Born/Ht./Wt. markers,
    'SURNAME, First' lines) is scored and recorded, NOT parsed.

Transport as fetch_guides.py: follow redirects, fetch-then-rename, one request per
second or slower, HTTP status read on every call, retry with backoff on network
errors. Resumable: anything already on disk is skipped.

  python3 src/fetch_ia_unheld.py [limit]
"""
import os, re, sys, csv, json, time, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
CAND = os.path.join(BASE, "build-reports", "ia-unheld-pro-items.json")
LOG = os.path.join(BASE, "build-reports", "ia-unheld-fetch.json")
ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
META, TEXT, INDEX = os.path.join(ROOT, "meta"), os.path.join(ROOT, "text_all"), os.path.join(ROOT, "index.csv")
UA = "pgm3-archive-research/1.0 (NFL historical roster research; contact: ryannecci@gmail.com)"
DELAY = 1.0
FOOT = re.compile(r"\b(quarterback|touchdown|linebacker|fumble|yardage|gridiron|halfback|fullback|punt|field goal|end zone)\b", re.I)
OTHER = re.compile(r"\b(pitcher|infield|batting average|shortstop|home runs?|innings?|goaltender|power play|slap ?shot|"
                   r"free throw|rebounds?|three-point|jump shot)\b", re.I)
PLAYER = re.compile(r"^\s*(PERSONAL|COLLEGE|PRO|CAREER|HONORS)\s*[:—–-]|\bBorn\b|\bHt\.|\bWt\.|^[A-Z][A-Z'\-]+,\s+[A-Z][a-z]", re.M)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(7):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read(); code = r.status
            time.sleep(DELAY)
            return code, data
        except urllib.error.HTTPError as e:
            time.sleep(DELAY)
            if e.code in (404, 403): return e.code, None
            if e.code == 429 or e.code >= 500: pass
            else: return e.code, None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass
        wait = [15, 30, 60, 120, 300, 600, 900][attempt]
        print(f"  [ia] retrying in {wait}s", flush=True); time.sleep(wait)
    return 0, None


def cache(path, url):
    """Fetch FIRST, write .part, rename. A failure leaves no file behind."""
    if os.path.exists(path) and os.path.getsize(path) == 0: os.remove(path)
    if os.path.exists(path): return open(path, "rb").read(), True, 200
    code, data = fetch(url)
    if not data: return None, False, code
    tmp = path + ".part"
    with open(tmp, "wb") as fh: fh.write(data)
    os.replace(tmp, path)
    return data, False, code


def sport(text):
    f, o = len(FOOT.findall(text)), len(OTHER.findall(text))
    return f, o, ("football" if f >= 3 and f >= 2 * o else "other" if o > f else "unclear")


def main():
    os.makedirs(META, exist_ok=True); os.makedirs(TEXT, exist_ok=True)
    cand = json.load(open(CAND))["candidates"]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(cand)
    held = {r["identifier"] for r in csv.DictReader(open(INDEX))}
    log = {"_date": "2026-09-07", "fetched": [], "notext": [], "containers": [], "sport_mismatch": [], "failed": [],
           "small_texts": [], "already": 0}
    if os.path.exists(LOG):
        try: log = json.load(open(LOG))
        except Exception: pass
    done = {x["identifier"] for k in ("fetched", "notext", "containers", "sport_mismatch") for x in log[k]}
    rows_to_add = []
    for i, c in enumerate(cand[:limit]):
        ident, title, year = c["identifier"], c["title"], c["year"]
        if ident in done or ident in held: log["already"] += 1; continue
        mp, tp = os.path.join(META, ident + ".json"), os.path.join(TEXT, ident + ".txt")
        raw, was_cached, code = cache(mp, f"https://archive.org/metadata/{ident}")
        if raw is None:
            log["failed"].append({"identifier": ident, "stage": "metadata", "http": code}); continue
        try: meta = json.loads(raw)
        except Exception:
            log["failed"].append({"identifier": ident, "stage": "metadata-parse"}); os.remove(mp); continue
        files = meta.get("files", [])
        djvu = [f["name"] for f in files if f["name"].endswith("_djvu.txt")]
        pdfs = [f["name"] for f in files if f["name"].lower().endswith(".pdf") and not f["name"].endswith("_text.pdf")]
        if len(djvu) > 1 or len(pdfs) > 1:
            log["containers"].append({"identifier": ident, "title": title, "year": year, "djvu_texts": len(djvu), "pdfs": len(pdfs)})
            continue
        if not djvu:
            open(tp + ".notext", "w").write("")
            log["notext"].append({"identifier": ident, "title": title, "year": year, "reason": "no _djvu.txt in item"})
            continue
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(djvu[0])}"
        data, was_cached, code = cache(tp, url)
        if data is None:
            log["failed"].append({"identifier": ident, "stage": "text", "http": code}); continue
        text = data.decode("utf-8", errors="ignore")
        f, o, verdict = sport(text)
        players = len(PLAYER.findall(text))
        rec = {"identifier": ident, "title": title, "year": year, "class": c["class"], "query": c["query"],
               "bytes": len(data), "words": len(text.split()), "http": code, "ocr_file": djvu[0],
               "sport": verdict, "football_terms": f, "other_sport_terms": o,
               "per_player_markers": players, "per_player_likely": players >= 40}
        if verdict == "other":
            log["sport_mismatch"].append(rec); continue          # on disk, not in the index
        if len(data) < 2000: log["small_texts"].append({"identifier": ident, "bytes": len(data), "title": title})
        log["fetched"].append(rec)
        rows_to_add.append({"year": year or "", "identifier": ident,
                            "league_wide": str(c["query"] == "pro-football-preview" or c["class"] == "preview annual"),
                            "restricted": "", "title": title})
        if len(rows_to_add) >= 25:
            with open(INDEX, "a", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["year", "identifier", "league_wide", "restricted", "title"]); w.writerows(rows_to_add)
            rows_to_add = []
            IO.dump_atomic(log, LOG, indent=1)
            print(f"  [{i + 1}/{limit}] fetched={len(log['fetched'])} notext={len(log['notext'])} containers={len(log['containers'])} "
                  f"sport-mismatch={len(log['sport_mismatch'])} failed={len(log['failed'])} small={len(log['small_texts'])}", flush=True)
    if rows_to_add:
        with open(INDEX, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["year", "identifier", "league_wide", "restricted", "title"]); w.writerows(rows_to_add)
    IO.dump_atomic(log, LOG, indent=1)
    print(f"\nfetched {len(log['fetched'])}  no text {len(log['notext'])}  containers {len(log['containers'])}  "
          f"sport mismatch {len(log['sport_mismatch'])}  failed {len(log['failed'])}  small (<2 KB) {len(log['small_texts'])}  "
          f"already held/done {log['already']}", flush=True)


if __name__ == "__main__":
    main()
