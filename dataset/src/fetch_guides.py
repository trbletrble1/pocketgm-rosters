"""Pull media-guide OCR text from archive.org. Text only, never the PDFs.

Two transport rules, both learned the hard way and both declared:

  1. FOLLOW REDIRECTS. archive.org 302s to a node host. Without it you get a
     zero-byte file that reads exactly like a book with no text.
     (declarations/media-guides.json :: retrieval.trap)
  2. FETCH BEFORE OPEN, then rename atomically. Opening the file first turns a
     transient failure into a permanent empty document that the cache serves
     forever as valid. That is the zero-byte cache bug, and this is the same
     shape of source tree.

And one that is specific to this host: the OCR file is NOT named after the
identifier. `rams-1949` holds `Rams, 1949 Media Guide (Los Angeles) V2_djvu.txt`.
Guessing {identifier}_djvu.txt 404s on every item, which would read as "this
archive has no text at all". The metadata call is required, not an optimisation.

  python3 src/fetch_guides.py [limit]
"""
import os, sys, csv, json, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (research; contact ryannecci@gmail.com)"
ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
META = os.path.join(ROOT, "meta")
TEXT = os.path.join(ROOT, "text_all")
DELAY = 1.0                      # one request per second or slower


def _fetch(url):
    """Follow redirects (urllib does by default) and return bytes, or None on 404."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            final = r.geturl()
            data = r.read()
        return data, final
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return None, None
        raise


def _cache(path, fetch_fn):
    """Fetch FIRST, write to .part, rename. A failure leaves no file behind."""
    if os.path.exists(path) and os.path.getsize(path) == 0:
        os.remove(path)                      # a cache must not store a failure
    if os.path.exists(path):
        return open(path, "rb").read(), True
    data = fetch_fn()
    if data is None:
        return None, False
    if not data:
        raise IOError(f"empty response for {path} - refusing to cache")
    tmp = path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    time.sleep(DELAY)
    return data, False


def main():
    os.makedirs(META, exist_ok=True); os.makedirs(TEXT, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(ROOT, "index.csv"))))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(rows)
    got = notext = cached = failed = 0
    absences = []
    for i, r in enumerate(rows[:limit]):
        ident = r["identifier"]
        mp = os.path.join(META, ident + ".json")
        tp = os.path.join(TEXT, ident + ".txt")
        if os.path.exists(tp) and os.path.getsize(tp) > 0:
            cached += 1; continue
        try:
            raw, was_cached = _cache(mp, lambda: _fetch(
                f"https://archive.org/metadata/{ident}")[0])
            if raw is None:
                failed += 1; continue
            meta = json.loads(raw)
            names = [f["name"] for f in meta.get("files", [])
                     if f["name"].endswith("_djvu.txt")]
            if not names:
                # EXPECTED for cover-only items. An absence to record, not a failure.
                notext += 1
                absences.append({"identifier": ident, "year": r["year"],
                                 "title": r["title"], "reason": "no _djvu.txt in item"})
                open(tp + ".notext", "w").write("")
                continue
            fn = urllib.parse.quote(names[0]) if hasattr(urllib, "parse") else names[0]
            url = f"https://archive.org/download/{ident}/{fn}"
            data, was_cached = _cache(tp, lambda: _fetch(url)[0])
            if data is None:
                failed += 1
            else:
                got += 1
        except Exception as e:
            failed += 1
            print(f"  {ident}: {type(e).__name__} {e}", flush=True)
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{limit}] text={got} no-text={notext} "
                  f"cached={cached} failed={failed}", flush=True)
    json.dump(absences, open(os.path.join(ROOT, "no_text_items.json"), "w"), indent=1)
    print(f"\ntext fetched {got}  no _djvu.txt {notext}  already cached {cached}  failed {failed}")


if __name__ == "__main__":
    import urllib.parse
    main()
