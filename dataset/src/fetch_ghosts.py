"""Preserve Ghosts of the Gridiron from the Wayback Machine. Politely.

THE INTERNET ARCHIVE IS A CHARITY AND THIS IS A FAVOUR. One request at a time, a
full second between them, a User-Agent that says who is asking and why, and an
exponential back-off that gets SLOWER on 429 and 5xx rather than retrying harder.
No concurrency. If this takes an hour, it takes an hour.

EVERY FILE KEEPS ITS CAPTURE TIMESTAMP. A claim must be able to name the exact
snapshot it came from -- `web.archive.org/web/20091214052450id_/<url>` -- because the
live URL is dead and naming it would be a citation to nothing. The mirror on disk is
for reading; manifest.json is the record, and it carries the timestamp, the Wayback
URL, the sha256 and the byte count for every file.

A PAGE WAYBACK NEVER CAPTURED IS A REAL ABSENCE. It is counted, with its CDX status,
and never silently skipped. The CDX index already flags 35 rows as 301/302/504 -- a
504 in CDX means the crawler recorded a gateway error, not a page.

  python3 src/fetch_ghosts.py [--limit N] [--delay S]
"""
import os, sys, json, time, hashlib, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
DEST = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron")
CDX = os.path.join(DEST, "cdx.json")
MANIFEST = os.path.join(DEST, "manifest.json")
UA = ("pgm3-archive-preservation/1.0 (personal football history archive; "
      "one-off preservation of a dead site; contact via github.com/ryannecci)")
DELAY = 1.0


def fetch(url, tries=4):
    delay = DELAY
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read(), r.status, None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                delay *= 3                      # SLOWER, not harder
                time.sleep(delay); continue
            return None, e.code, str(e)
        except Exception as e:
            if i < tries - 1: delay *= 3; time.sleep(delay); continue
            return None, None, repr(e)
    return None, None, "gave up"


def main():
    argv = sys.argv[1:]
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    delay = float(argv[argv.index("--delay") + 1]) if "--delay" in argv else DELAY
    rows = json.load(open(CDX)); cols, rows = rows[0], rows[1:]
    rows = [dict(zip(cols, r)) for r in rows]
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"files": {}, "absent": []}
    done = man["files"]
    todo = [r for r in rows if r["original"] not in done]
    if limit: todo = todo[:limit]
    print(f"{len(rows)} CDX rows, {len(done)} already held, {len(todo)} to fetch, "
          f"{delay}s between requests", flush=True)
    n_ok = n_absent = 0
    for i, r in enumerate(todo, 1):
        orig, ts = r["original"], r["timestamp"]
        wb = f"http://web.archive.org/web/{ts}id_/{orig}"
        if r["statuscode"] != "200":
            man["absent"].append({"url": orig, "timestamp": ts,
                                  "cdx_status": r["statuscode"], "mimetype": r["mimetype"],
                                  "why": "the CDX index records this capture as "
                                         f"{r['statuscode']}, so Wayback holds no page here"})
            done[orig] = {"absent": True, "cdx_status": r["statuscode"]}
            n_absent += 1; continue
        body, status, err = fetch(wb)
        time.sleep(delay)
        if body is None:
            man["absent"].append({"url": orig, "timestamp": ts, "wayback_url": wb,
                                  "http_status": status, "error": err,
                                  "why": "Wayback returned no body for a capture its own "
                                         "index records as 200"})
            done[orig] = {"absent": True, "http_status": status}
            n_absent += 1
        else:
            p = urllib.parse.urlparse(orig).path
            p = urllib.parse.unquote(p).replace("/~ghostsofthegridiron", "").lstrip("/") or "index.htm"
            p = p.replace("..", "_")
            out = os.path.join(DEST, "mirror", p)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.isdir(out): out = out + ".file"
            with open(out, "wb") as f: f.write(body)
            done[orig] = {"path": os.path.relpath(out, DEST), "timestamp": ts,
                          "wayback_url": wb, "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest(),
                          "mimetype": r["mimetype"], "cdx_length": r["length"]}
            n_ok += 1
        if i % 25 == 0:
            json.dump(man, open(MANIFEST, "w"), indent=1)
            print(f"  {i}/{len(todo)}  ok={n_ok} absent={n_absent}", flush=True)
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print(f"DONE  fetched={n_ok}  absent={n_absent}  held total={len(done)}", flush=True)


if __name__ == "__main__":
    main()
