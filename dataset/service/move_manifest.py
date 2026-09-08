"""Prove a copy arrived intact: one line to compare, before anything is deleted.

Run it on the laptop, run it on the mini, compare the FINGERPRINT lines. Same line
means every file is present, the same size, and -- for the parts that exist nowhere
else -- byte-for-byte identical.

    python3 move_manifest.py                      # the standard set
    python3 move_manifest.py --full               # hash the contents of everything (slower)
    python3 move_manifest.py --save before.json   # keep the detail, to find WHICH file differs

What is hashed by content, always: dataset/build and dataset/build-reports. Those are
gitignored, have no history and exist in exactly one place, so a silent truncation there
is unrecoverable. Everything else is checked by path + size, which catches a missing or
half-copied file without reading 10 GB twice.

TWO fingerprints are printed, and they answer different questions. CONTENT covers paths,
sizes and hashes. PERMISSIONS covers the mode bits, and it exists because on 2026-09-07
a copy through an exFAT drive delivered all 102,861 files byte-perfect and rewrote every
one of them as 0700 -- git then reported 263 tracked files as mode-changed when nothing
about their contents had changed, and the content fingerprint matched throughout. A check
that reads every byte and still misses a real difference is worth exactly one more line.
Use fix_modes.py to record and restore the modes themselves.
"""
import os, sys, json, hashlib, argparse

ROOTS = ["Documents/pocketgm-rosters-clone", "Documents/pgm3-sources"]
CONTENT_HASHED = ["Documents/pocketgm-rosters-clone/dataset/build",
                  "Documents/pocketgm-rosters-clone/dataset/build-reports"]
# Only genuinely transient things. NOT .log: dataset/build holds 221 ingest logs that are
# part of the record and gitignored like everything else there, so a missing one must show.
SKIP_SUFFIX = (".pyc", ".tmp", ".prev", ".lock", ".building")
SKIP_DIR = {"__pycache__", ".DS_Store"}


def sha_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(buf)
            if not b: break
            h.update(b)
    return h.hexdigest()


def walk(home, roots, content_roots, full=False):
    rows = []
    for root in roots:
        base = os.path.join(home, root)
        if not os.path.isdir(base):
            print(f"  MISSING ROOT: {base}", file=sys.stderr); continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIR]
            for f in sorted(fn):
                if f in SKIP_DIR or f.endswith(SKIP_SUFFIX): continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, home)
                try:
                    size = os.path.getsize(p)
                except OSError as e:
                    print(f"  UNREADABLE: {rel}: {e}", file=sys.stderr); continue
                digest = None
                if full or any(rel.startswith(c) for c in content_roots):
                    try:
                        digest = sha_file(p)
                    except OSError as e:
                        print(f"  UNREADABLE: {rel}: {e}", file=sys.stderr); continue
                rows.append((rel, size, digest))
    rows.sort()
    return rows


def fingerprint(rows):
    h = hashlib.sha256()
    for rel, size, digest in rows:
        h.update(f"{rel}\0{size}\0{digest or ''}\0".encode())
    return h.hexdigest()[:32]


def mode_fingerprint(home, rows):
    """Paths and their permission bits, separate from content so the two are told apart."""
    import stat
    h = hashlib.sha256()
    for rel, _, _ in rows:
        try: mode = stat.S_IMODE(os.lstat(os.path.join(home, rel)).st_mode)
        except OSError: mode = -1
        h.update(f"{rel}\0{mode}\0".encode())
    return h.hexdigest()[:32]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", default=os.path.expanduser("~"), help="the home folder holding Documents/ (default: yours)")
    ap.add_argument("--full", action="store_true", help="hash the contents of every file, not only the archive")
    ap.add_argument("--save", help="write the per-file detail here, so a mismatch can be located")
    a = ap.parse_args(argv)
    rows = walk(a.home, ROOTS, CONTENT_HASHED, a.full)
    total = sum(r[1] for r in rows)
    hashed = sum(1 for r in rows if r[2])
    print(f"  files       {len(rows):,}")
    print(f"  bytes       {total:,}  ({total/1e9:.2f} GB)")
    print(f"  hashed      {hashed:,} files by content")
    print(f"  FINGERPRINT {fingerprint(rows)}   (paths, sizes, content)")
    print(f"  PERMISSIONS {mode_fingerprint(a.home, rows)}   (mode bits -- an exFAT drive loses these; content cannot see it)")
    if a.save:
        json.dump({"files": len(rows), "bytes": total, "fingerprint": fingerprint(rows),
                   "permissions_fingerprint": mode_fingerprint(a.home, rows),
                   "rows": [{"path": r, "size": s, "sha256": d} for r, s, d in rows]}, open(a.save, "w"), indent=1)
        print(f"  detail      {a.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
