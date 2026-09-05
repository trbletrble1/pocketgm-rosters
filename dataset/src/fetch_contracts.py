"""Fetch auction-listing contract images so Ryan's readings become TRANSCRIPTIONS.

The refusal was correct: a figure relayed through conversation may never enter
the store. But a transcription of a HELD document may, and the only thing making
these relays rather than transcriptions is that the images are not on disk.

So: fetch the image, hash-pin it, and the 35 figures in
extract/_relayed_pending.json become readings of documents this project holds.

RIGHTS. An auction image belongs to the auction house. It is held for private
reference and citation only. The dataset cites the FIGURE and the LOT; it never
republishes the scan, and pgm3-sources is already outside the repo.

Same transport disciplines as every fetcher here: fetch first, write .part,
rename atomically, never re-fetch, one request per second or slower.

  python3 src/fetch_contracts.py            # fetch the known list
  python3 src/fetch_contracts.py --list     # show it without fetching
"""
import os, sys, json, time, hashlib, struct, urllib.request

UA = "Mozilla/5.0 (research; contact ryannecci@gmail.com)"
DEST = os.path.expanduser("~/Documents/pgm3-sources/contracts")
MANIFEST = os.path.join(DEST, "manifest.json")
DELAY = 1.2

# Known direct image URLs. eBay first: these are LIVE listings that vanish on sale.
KNOWN = [
 {"player": "Ed Franco",     "season": 1938, "house": "ebay",
  "url": "https://i.ebayimg.com/images/g/XmoAAOSwMNxigoyG/s-l1600.jpg"},
 {"player": "Leo Sugar",     "season": 1961, "house": "ebay",
  "url": "https://i.ebayimg.com/images/g/ZVYAAOSw41BkqEfa/s-l1600.jpg"},
 {"player": "Leo Sugar",     "season": 1963, "house": "ebay",
  "url": "https://i.ebayimg.com/images/g/vMIAAOSwyQtV7ZPx/s-l1600.jpg"},
 {"player": "Gail Cogdill",  "season": 1969, "house": "ebay",
  "url": "https://i.ebayimg.com/images/g/ePcAAOSwbW9kgKwG/s-l1600.jpg"},
 {"player": "Doug Atkins",   "season": 1954, "house": "heritage",
  "url": "https://dyn1.heritagestatic.com/ha?p=1-5-9-4-1-15941707&it=product",
  "lot": "heritage 15941707"},
 {"player": "Lou Groza",     "season": 1951, "house": "heritage",
  "url": "https://dyn1.heritagestatic.com/ha?p=1-5-9-4-1-15941705&it=product",
  "lot": "heritage 15941705"},
]


def dims(b):
    if b[:2] == b"\xff\xd8":
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF: i += 1; continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2, 0xC3):
                h, w = struct.unpack(">HH", b[i + 5:i + 9]); return [w, h]
            if m in (0xD8, 0xD9): i += 2; continue
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP" and b[12:16] == b"VP8X":
        return [int.from_bytes(b[24:27], "little") + 1,
                int.from_bytes(b[27:30], "little") + 1]
    return None


def name_for(e):
    p = e["player"].replace(" ", "_")
    return f"{e['season']}_{p}.jpg"


def main():
    if "--list" in sys.argv:
        for e in KNOWN: print(f"  {e['season']} {e['player']:<16} {e['house']:<9} {e['url']}")
        print(f"\n{len(KNOWN)} known direct image URLs")
        return 0
    os.makedirs(DEST, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    got = held = fail = 0
    for e in KNOWN:
        fn = name_for(e); p = os.path.join(DEST, fn)
        if os.path.exists(p) and os.path.getsize(p) == 0: os.remove(p)
        if os.path.exists(p):
            held += 1; continue
        try:
            r = urllib.request.urlopen(
                urllib.request.Request(e["url"], headers={"User-Agent": UA}), timeout=60)
            b = r.read()
        except Exception as ex:
            fail += 1; print(f"  {fn}: {type(ex).__name__} {str(ex)[:60]}"); continue
        if not b:
            fail += 1; print(f"  {fn}: empty - not cached"); continue
        tmp = p + ".part"
        open(tmp, "wb").write(b); os.replace(tmp, p)
        man[fn] = {"player": e["player"], "season": e["season"], "house": e["house"],
                   "lot": e.get("lot"), "url": e["url"],
                   "sha256": hashlib.sha256(b).hexdigest(),
                   "bytes": len(b), "dimensions": dims(b),
                   "fetched": time.strftime("%Y-%m-%d"),
                   "rights": "auction house's image; held for private reference and "
                             "citation. Never republished."}
        got += 1
        print(f"  {fn}: {len(b):,}b {dims(b)}  sha256 {man[fn]['sha256'][:16]}")
        time.sleep(DELAY)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print(f"\nfetched {got}  already held {held}  failed {fail}   -> {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
