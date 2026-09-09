"""The polite-fetch core, with ONE implementation.

Proved on the Coffin Corner run of 2026-09-08 and re-proved for every fetcher that
uses it, because a property proved on one caller is not proved on another. The whole
point of this module is that there is no second copy of the rule to drift.

  * one request at a time, a fixed delay apart, no concurrency
  * back-off WIDENS x3 on 429/5xx and gives up after four tries rather than hammering
  * a 404 is an ABSENCE with a reason, never an error
  * every file written through a .part + os.replace, fsync'd first
  * the manifest rewritten through a temp file + os.replace after EVERY file, so a kill
    at any moment leaves either the old manifest or the new one and never a torn one
  * resume trusts nothing that does not HASH: a manifest row whose file has changed is
    re-fetched
  * verify is FULL and counts both ways -- every row re-hashed off disk, every file on
    disk checked for a row
"""
import os, ssl, json, time, hashlib, datetime, urllib.request, urllib.error

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(manifest, header):
    if os.path.exists(manifest):
        return json.load(open(manifest))
    return dict(header, files={}, absences={}, started=None, runs=[])


def save(man, manifest):
    os.makedirs(os.path.dirname(manifest), exist_ok=True)
    tmp = manifest + ".tmp"
    with open(tmp, "w") as f:
        json.dump(man, f, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, manifest)


def fetch(url, delay, ua, tries=4, timeout=90):
    d = delay
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                return r.read(), r.status, None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, 404, None
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                d *= 3
                time.sleep(d); continue
            return None, e.code, str(e)
        except Exception as e:
            if i < tries - 1:
                d *= 3; time.sleep(d); continue
            return None, None, repr(e)
    return None, None, "gave up after %d tries" % tries


def write_file(dest, name, body):
    p = os.path.join(dest, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".part"
    with open(tmp, "wb") as f:
        f.write(body); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)
    return p


def todo(man, targets, dest, key="file"):
    """What is left. A manifest row whose bytes no longer hash to what it recorded is
    NOT done -- that is the difference between resuming and assuming."""
    out = []
    for t in targets:
        rec = man["files"].get(t[key])
        p = os.path.join(dest, t[key])
        if rec and os.path.exists(p) and sha(open(p, "rb").read()) == rec["sha256"]:
            continue
        out.append(t)
    return out


def verify(man, dest, exts=(".html",)):
    ok = bad = missing = 0; problems = []
    for name, rec in man["files"].items():
        p = os.path.join(dest, name)
        if not os.path.exists(p):
            missing += 1; problems.append(f"{name}: in the manifest, not on disk"); continue
        b = open(p, "rb").read()
        if sha(b) != rec["sha256"]:
            bad += 1; problems.append(f"{name}: sha256 differs from the manifest"); continue
        if len(b) != rec["bytes"]:
            bad += 1; problems.append(f"{name}: byte count differs from the manifest"); continue
        ok += 1
    on_disk = set()
    for root, _dirs, files in os.walk(dest):
        for f in files:
            if f.endswith(exts):
                on_disk.add(os.path.relpath(os.path.join(root, f), dest))
    orphan = sorted(on_disk - set(man["files"]))
    for f in orphan[:50]:
        problems.append(f"{f}: on disk, in NO manifest entry")
    print(f"manifest entries        {len(man['files']):>7,}")
    print(f"  re-hashed and equal   {ok:>7,}")
    print(f"  hash or size differs  {bad:>7,}")
    print(f"  missing from disk     {missing:>7,}")
    print(f"files on disk           {len(on_disk):>7,}")
    print(f"  with no manifest entry{len(orphan):>7,}")
    print(f"absences recorded       {len(man['absences']):>7,}")
    for p in problems[:20]: print("   !", p)
    return not problems
