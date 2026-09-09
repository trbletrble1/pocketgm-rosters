"""Fetch the PFRA Coffin Corner run from the Wayback Machine. Same discipline as Ghosts.

POLITE. One request at a time, one second apart, no concurrency. Back-off gets SLOWER
on 429 and 5xx (x3 each try) rather than retrying harder. A 404 is an ABSENCE with a
reason, not an error, and is recorded as one.

WORKS THROUGH A LIST IT DOES NOT DISCOVER. targets.json is built from the CDX index
before any fetch. This file never crawls and never follows a link.

RESUMES FROM THE MANIFEST, AND THE MANIFEST IS NEVER HALF-WRITTEN. Every file is
written to disk, then hashed, then recorded, then the manifest is rewritten through a
temp file and os.replace -- so a kill at any point leaves either the old manifest or
the new one, and a file on disk with no manifest entry is re-fetched rather than
silently trusted. Re-running skips what the manifest already holds AND whose bytes
still hash to what it recorded.

  python3 src/fetch_coffin_corner.py            fetch, resuming
  python3 src/fetch_coffin_corner.py --verify   re-hash every file against the manifest
  python3 src/fetch_coffin_corner.py --status   what is done, what is left
"""
import os, sys, ssl, json, time, hashlib, urllib.request, urllib.error, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite_fetch as PF          # ONE implementation of the polite-fetch rule

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

DEST = os.path.expanduser("~/Documents/pgm3-sources/pfra/coffin_corner")
TARGETS = os.path.expanduser("~/Documents/pgm3-sources/pfra/targets.json")
MANIFEST = os.path.join(DEST, "manifest.json")
UA = ("pgm3-archive/1.0 (personal football research archive; one request per second; "
      "contact ryannecci@gmail.com)")
DELAY = 1.0


def load():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {"_what": "One row per article of the PFRA Coffin Corner, fetched from the "
                     "Wayback Machine. Absences are rows too.",
            "_rights": "A PFRA publication. NOT public domain. Held for consultation; facts "
                       "are cited to the page under the reference-works ruling. Not republished.",
            "_politeness": "one request at a time, 1s apart, back-off x3 on 429/5xx",
            "files": {}, "absences": {}, "started": None, "runs": []}


def save(man):
    os.makedirs(DEST, exist_ok=True)
    PF.save(man, MANIFEST)                     # delegated: one implementation


def fetch(url, delay, tries=4):
    """Delegated to polite_fetch. This file used to carry its own copy of the rule;
    the copy and the one in src/polite_fetch.py were identical the day they were
    written, which is exactly how the league-token rule drifted into two."""
    return PF.fetch(url, delay, UA, tries=tries, timeout=120)


def sha(b):
    return PF.sha(b)                      # delegated: one implementation


def verify(man):
    """FULL, never sampled. Every manifest entry re-hashed off the disk, and every file
    on the disk counted against the manifest."""
    ok = bad = missing = 0; problems = []
    for name, rec in man["files"].items():
        p = os.path.join(DEST, name)
        if not os.path.exists(p):
            missing += 1; problems.append(f"{name}: in the manifest, not on disk"); continue
        b = open(p, "rb").read()
        if sha(b) != rec["sha256"]:
            bad += 1; problems.append(f"{name}: sha256 differs from the manifest"); continue
        if len(b) != rec["bytes"]:
            bad += 1; problems.append(f"{name}: byte count differs from the manifest"); continue
        ok += 1
    on_disk = {f for f in os.listdir(DEST) if f.lower().endswith(".pdf")}
    orphan = sorted(on_disk - set(man["files"]))
    for f in orphan:
        problems.append(f"{f}: on disk, in NO manifest entry")
    print(f"manifest entries        {len(man['files']):>6,}")
    print(f"  re-hashed and equal   {ok:>6,}")
    print(f"  hash or size differs  {bad:>6,}")
    print(f"  missing from disk     {missing:>6,}")
    print(f"pdf files on disk       {len(on_disk):>6,}")
    print(f"  with no manifest entry{len(orphan):>6,}")
    print(f"absences recorded       {len(man['absences']):>6,}")
    for p in problems[:20]: print("   !", p)
    return not problems


def main():
    argv = sys.argv[1:]
    os.makedirs(DEST, exist_ok=True)
    man = load()
    T = json.load(open(TARGETS))
    targets = T["targets"]

    if "--verify" in argv:
        sys.exit(0 if verify(man) else 1)

    # Absences are recorded ONCE, from the CDX, with their reason. They are a fact about
    # the run, not a gap in this fetch.
    for a in T["absences"]:
        k = a.get("file") or f"article-{a['article']}"
        man["absences"].setdefault(k, a)

    todo = []
    for t in targets:
        rec = man["files"].get(t["file"])
        p = os.path.join(DEST, t["file"])
        if rec and os.path.exists(p):
            # TRUST NOTHING THAT DOES NOT HASH. A manifest row whose file has changed or
            # been truncated is not done; it is re-fetched.
            if sha(open(p, "rb").read()) == rec["sha256"]:
                continue
        todo.append(t)

    if "--status" in argv:
        print(f"targets {len(targets):,}   done {len(targets)-len(todo):,}   to fetch {len(todo):,}   "
              f"absences {len(man['absences'])}")
        return

    man["started"] = man["started"] or datetime.datetime.now().isoformat(timespec="seconds")
    run = {"began": datetime.datetime.now().isoformat(timespec="seconds"), "fetched": 0,
           "absent": 0, "failed": 0}
    man["runs"].append(run); save(man)
    print(f"to fetch {len(todo):,} of {len(targets):,}")

    for i, t in enumerate(todo, 1):
        body, status, err = fetch(t["url"], DELAY)
        if body is not None:
            p = os.path.join(DEST, t["file"])
            tmp = p + ".part"
            with open(tmp, "wb") as f:
                f.write(body); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, p)                 # a PDF is never half-written either
            man["files"][t["file"]] = {
                "sha256": sha(body), "bytes": len(body),
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "capture_timestamp": t["timestamp"],
                "snapshot_url": t["url"], "original_url": t["original"],
                "volume": t["vol"], "issue": t["issue"], "article": t["article"],
                "http_status": status}
            run["fetched"] += 1
        elif status == 404:
            man["absences"][t["file"]] = {
                "file": t["file"], "snapshot_url": t["url"], "http_status": 404,
                "why": "the Wayback Machine answered 404 for a capture its index lists; "
                       "the record exists and the document does not",
                "when": datetime.datetime.now().isoformat(timespec="seconds")}
            run["absent"] += 1
        else:
            man["absences"][t["file"]] = {
                "file": t["file"], "snapshot_url": t["url"], "http_status": status,
                "error": err, "why": "the fetch did not succeed after four tries with "
                                     "widening back-off; recorded rather than retried harder",
                "when": datetime.datetime.now().isoformat(timespec="seconds")}
            run["failed"] += 1
        save(man)                              # AFTER EVERY FILE, so a kill loses at most one
        if i % 50 == 0 or i == len(todo):
            print(f"  {i:>5,}/{len(todo):,}  fetched {run['fetched']:,}  "
                  f"absent {run['absent']}  failed {run['failed']}", flush=True)
        time.sleep(DELAY)
    run["ended"] = datetime.datetime.now().isoformat(timespec="seconds")
    save(man)
    print("done.")
    verify(man)


if __name__ == "__main__":
    main()
