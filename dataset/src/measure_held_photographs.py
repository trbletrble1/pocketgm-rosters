"""Measure what each candidate ALREADY holds, so 'never shrink' can be tested.

The replacement rule (declarations/wikipedia.json PHOTOGRAPHS.REPLACEMENT) compares
on the shorter side. That needs a size for the HELD photograph, and the store records
photographs by filename with no dimensions at all. So measure the files.

Three populations, and they are not equally knowable:

  photos.json          the PSF set -- files on disk under $PGM3_SOURCES/photos. Measurable.
  wikipedia-photos-*   the 432 downloaded 2026-09-07, now in build/photographs/wikipedia.
                       Measurable. The claim carries the Commons file title; the download
                       named files {ordinal}_{sanitised title}, so the title maps back.
  wikipedia.json       the older ingest -- filename only, never downloaded, no licence
                       either. NOT measurable. Reported as unknown, and the replacement
                       rule REFUSES on unknown rather than assuming a thumbnail.

  python3 src/measure_held_photographs.py [--write]   -> build-reports/held-photographs.json
"""
import os, re, sys, json, glob, struct, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO

DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
OK_LICENCE = re.compile(DECL["PHOTOGRAPHS"]["licence_allow_pattern"], re.I)

PSF = os.path.expanduser("~/Documents/pgm3-sources/photos/PSFplayers")
WIKI_FILES = os.path.join(BASE, "build", "photographs", "wikipedia")
OUT = os.path.join(BASE, "build-reports", "held-photographs.json")
PHOTO_PREDS = ("has_photograph", "wikipedia.photograph")


def dims(p):
    """Dimensions from the file's own header. Same reader used for the 432 on
    2026-09-07, so the numbers are comparable rather than merely similar.

    WebP and TIFF were added 2026-09-07 after they were found landing in the
    replacement run's download_failures and being dropped without an error --
    the archive's recurring defect, an input that reads as nothing. The formats
    are read now, AND an unreadable file is fatal rather than skipped; see
    gate_photographs_measurable.py for the property.
    """
    try:
        with open(p, "rb") as f: head = f.read(64)
    except OSError:
        return None
    if head[:2] == b"\xff\xd8":
        with open(p, "rb") as f:
            f.read(2)
            while True:
                b = f.read(1)
                while b and b != b"\xff": b = f.read(1)
                while b == b"\xff": b = f.read(1)
                if not b: return None
                m = b[0]
                if m in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                    f.read(3); h, w = struct.unpack(">HH", f.read(4)); return w, h, "jpeg"
                ln = struct.unpack(">H", f.read(2))[0]; f.seek(ln - 2, 1)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", head[16:24]); return w, h, "png"
    if head[:3] == b"GIF":
        w, h = struct.unpack("<HH", head[6:10]); return w, h, "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        c = head[12:16]
        if c == b"VP8 ":                       # lossy: 3-byte start code then 14-bit w/h
            w, h = struct.unpack("<HH", head[26:30]); return w & 0x3FFF, h & 0x3FFF, "webp"
        if c == b"VP8L":                       # lossless: 14 bits each, packed, minus one
            b = struct.unpack("<I", head[21:25])[0]
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1, "webp"
        if c == b"VP8X":                       # extended: 24-bit canvas size minus one
            w = int.from_bytes(head[24:27], "little") + 1
            h = int.from_bytes(head[27:30], "little") + 1
            return w, h, "webp"
        return None
    if head[:4] in (b"II\x2a\x00", b"MM\x00\x2a"):
        end = "<" if head[:2] == b"II" else ">"
        try:
            with open(p, "rb") as f: buf = f.read(65536)
            off = struct.unpack(end + "I", buf[4:8])[0]
            n = struct.unpack(end + "H", buf[off:off + 2])[0]
            w = h = None
            for i in range(n):
                e = off + 2 + i * 12
                tag, typ = struct.unpack(end + "HH", buf[e:e + 4])
                if tag not in (256, 257): continue
                v = (struct.unpack(end + "H", buf[e + 8:e + 10])[0] if typ == 3
                     else struct.unpack(end + "I", buf[e + 8:e + 12])[0])
                if tag == 256: w = v
                else: h = v
            if w and h: return w, h, "tiff"
        except Exception:
            return None
        return None
    return None


def san(t):
    """The download's own naming: 'File:' stripped, then non-[alnum._-] to '_', cut at 80."""
    t = re.sub(r"^File:", "", t or "")
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in t)[:80]


def wiki_file_index():
    idx = collections.defaultdict(list)
    if not os.path.isdir(WIKI_FILES): return idx
    for f in sorted(os.listdir(WIKI_FILES)):
        _, _, rest = f.partition("_")
        idx[rest].append(f)
    return idx


def main():
    write = "--write" in sys.argv
    wf = wiki_file_index()
    held, n = {}, collections.Counter()
    for path in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        src = os.path.basename(path)
        try: d = json.load(open(path))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if c.get("predicate") not in PHOTO_PREDS: continue
            pid, val = c["subject"][1], c.get("value")
            # rights status of what is HELD decides WHICH rule applies to it:
            # a licence the declaration recognises -> rights-clear -> NEVER SHRINK;
            # no licence at all -> rights-unknown -> RIGHTS_SUPERSEDES_RIGHTS_UNKNOWN.
            lic = c.get("licence")
            rec = {"held_in": src, "value": val, "w": None, "h": None, "fmt": None,
                   "bytes": None, "measurable": False, "why": None,
                   "licence": lic,
                   "rights": "clear" if lic and OK_LICENCE.search(lic) else "unknown"}
            if src == "photos.json":
                p = os.path.join(PSF, val or "")
                dd = dims(p)
                if dd:
                    rec.update(w=dd[0], h=dd[1], fmt=dd[2], bytes=os.path.getsize(p), measurable=True)
                    n["psf_measured"] += 1
                else:
                    rec["why"] = "PSF file not on disk or unreadable"; n["psf_unmeasurable"] += 1
            elif src.startswith("wikipedia-photos-"):
                cands = wf.get(san(val)) or []
                if len(cands) == 1:
                    p = os.path.join(WIKI_FILES, cands[0]); dd = dims(p)
                    if dd:
                        rec.update(w=dd[0], h=dd[1], fmt=dd[2], bytes=os.path.getsize(p),
                                   measurable=True, file=cands[0])
                        n["wiki_measured"] += 1
                    else:
                        rec["why"] = "downloaded file unreadable"; n["wiki_unmeasurable"] += 1
                else:
                    rec["why"] = ("image never downloaded" if not cands
                                  else f"{len(cands)} files share that name")
                    n["wiki_not_downloaded"] += 1
            else:
                rec["why"] = f"{src} records a filename only; the image was never downloaded"
                n["unmeasurable_other"] += 1
            # a person may hold more than one; keep the LARGEST, which is what
            # 'never shrink' must beat
            prev = held.get(pid)
            if prev is None or (rec["w"] or 0) * 0 + min(rec["w"] or 0, rec["h"] or 0) > \
                               min(prev["w"] or 0, prev["h"] or 0):
                held[pid] = rec
    for r in held.values():
        r["shorter_side"] = min(r["w"], r["h"]) if r["measurable"] else None
    meas = [r for r in held.values() if r["measurable"]]
    doc = {"_what": "the photograph each person already holds, measured from the file, so the "
                    "replacement rule can require a strictly larger shorter side",
           "_unknown_is_refused": "a person whose held size is None cannot be shown to gain; "
                                  "PHOTOGRAPHS.REPLACEMENT.held_size_unknown refuses rather than guesses",
           "measured_at": "2026-09-07", "counts": dict(n),
           "people": len(held), "measurable": len(meas),
           "held": held}
    for k, v in sorted(n.items()): print(f"  {k:24s} {v}")
    print(f"\n  people holding a photograph {len(held)}   measurable {len(meas)}   "
          f"unknown {len(held) - len(meas)}")
    if meas:
        ss = sorted(r["shorter_side"] for r in meas)
        print(f"  held shorter side: min {ss[0]}  median {ss[len(ss)//2]}  max {ss[-1]}")
    if write:
        IO.dump_atomic(doc, OUT, indent=1); print(f"\nwrote build-reports/{os.path.basename(OUT)}")
    return doc


if __name__ == "__main__":
    main()
