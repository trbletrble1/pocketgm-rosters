"""Fetch the SIZE of every candidate replacement photograph.

WHY THIS EXISTS. Dropping the gap-fill rule (declarations/wikipedia.json PHOTOGRAPHS,
RULING 2026-09-07) means a photograph may now replace one already held -- but only if
it is LARGER. That comparison needs a size for the candidate, and the wiki cache does
not have one: the 2026-09-06 sweeps asked imageinfo for `extmetadata` only, so every
cached image carries a licence and no dimensions.

Everything else the ingest needs is already cached -- all 2,329 candidate articles,
all 2,329 infobox images, all their licences. This fetches the missing column and
nothing else: url, size, and the full extmetadata block, batched 50 titles a request.

  python3 src/fetch_wiki_photo_sizes.py [--write]

Writes build-reports/wikipedia-photo-sizes.json: image title -> url, width, height,
bytes, mime, and the Artist / Credit / DateTimeOriginal / LicenseUrl that step 2 found
populated and worth storing with the claim rather than reducing to a licence string.

NOTE ON WHAT THIS SIZE IS. It is the API's report, not the file. Two of the 432
downloaded on 2026-09-07 had on-disk dimensions that disagreed with it. It is good
enough to CHOOSE candidates with; the size written on a claim is measured from the
downloaded file itself, per PHOTOGRAPHS.MEASURED_NOT_PROMISED.measured_from.
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from wiki_api import api
import index_io as IO

CACHE = os.path.expanduser("~/Documents/pgm3-sources/wiki_cache")
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
from wiki_api import infobox_image      # ONE reader, imported; see wiki_api for the four forms it reads
OUT = os.path.join(BASE, "build-reports", "wikipedia-photo-sizes.json")
BATCH = 50


def candidates():
    """The people every sweep skipped because they already held a photograph, and the
    infobox image of the article it skipped them on."""
    seen = {}
    for f in sorted(glob.glob(os.path.join(BASE, "build", "wikipedia-photos-*.json"))):
        d = json.load(open(f))
        for x in (d.get("refused") or {}).get("already_held", []):
            seen[x["person"]] = x["title"]
    arts = {}
    for f in glob.glob(CACHE + "/*.json"):
        try: d = json.load(open(f))
        except Exception: continue
        for _, pg in ((d.get("query") or {}).get("pages") or {}).items():
            if "missing" in pg or "invalid" in pg: continue
            revs = pg.get("revisions") or []
            if not revs: continue
            r0 = revs[0]
            txt = r0.get("*") or (r0.get("slots", {}).get("main", {}) or {}).get("*") or ""
            if txt: arts[pg.get("title")] = txt
    out, missing = {}, []
    for pid, title in seen.items():
        txt = arts.get(title)
        if not txt: missing.append((pid, title)); continue
        img = infobox_image(txt)
        if not img: missing.append((pid, title)); continue
        out[pid] = {"title": title, "image": img}
    return out, missing


def fetch(images, log=print):
    got, absent = {}, []
    titles = sorted(images)
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        code, data = api({"action": "query", "prop": "imageinfo",
                          "iiprop": "url|size|mime|extmetadata",
                          "titles": "|".join("File:" + t for t in chunk)})
        if code != 200 or not data:
            log(f"  batch {i // BATCH + 1}: HTTP {code}"); continue
        pages = (data.get("query") or {}).get("pages") or {}
        for _, pg in pages.items():
            t = re.sub(r"^File:", "", pg.get("title") or "")
            # A file hosted on COMMONS is reported by en.wikipedia as "missing" -- it is
            # missing LOCALLY -- while still carrying full imageinfo (imagerepository
            # "shared"). Treating "missing" as absent discarded 2,076 of 2,329 real files
            # on the first run. The imageinfo block is the only thing that decides.
            if not pg.get("imageinfo"):
                absent.append(t); continue
            e = pg["imageinfo"][0]; em = e.get("extmetadata") or {}
            def v(k): return (em.get(k) or {}).get("value")
            got[t] = {"url": e.get("url"), "w": e.get("width"), "h": e.get("height"),
                      "bytes": e.get("size"), "mime": e.get("mime"),
                      "licence": v("LicenseShortName"), "licence_url": v("LicenseUrl"),
                      "artist": v("Artist"), "credit": v("Credit"),
                      "date_original": v("DateTimeOriginal")}
        if (i // BATCH) % 10 == 0:
            log(f"  {min(i + BATCH, len(titles))}/{len(titles)} images", flush=True)
    return got, absent


def main():
    write = "--write" in sys.argv
    cand, missing = candidates()
    images = {v["image"] for v in cand.values()}
    print(f"candidates {len(cand)}  distinct images {len(images)}  "
          f"no cached article or no infobox image {len(missing)}")
    got, absent = fetch(images)
    sized = sum(1 for v in got.values() if v.get("w"))
    print(f"\nfetched {len(got)}  with dimensions {sized}  absent from Commons {len(absent)}")
    doc = {"_what": "candidate replacement photographs: url, size and attribution, "
                    "fetched because the cache carries licences without dimensions",
           "_size_is_the_apis": "chosen with, not written with -- the claim's size is measured "
                                "from the downloaded file (PHOTOGRAPHS.MEASURED_NOT_PROMISED)",
           "fetched_at": "2026-09-07", "candidates": cand, "images": got,
           "absent": sorted(absent), "no_article_or_image": missing}
    if write:
        IO.dump_atomic(doc, OUT, indent=1); print(f"wrote build-reports/{os.path.basename(OUT)}")
    return doc


if __name__ == "__main__":
    main()
