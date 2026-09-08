"""Re-OCR every eBay game-programme photograph with Apple Vision, and MEASURE THE LIFT
against the tesseract pass already recorded in build-reports/corpus-census-programs.json.

WHY DO IT TWICE. The census reported OCR on this class as a FLOOR, not a count: the 1925
Giants/Providence listing scored 0 of 8 photographs above 60 tesseract words, and its
lineup page -- both elevens by number, name, college and position -- reads by eye. Two
causes were guessed at and neither had been separated: the engine, and the photograph.
This pass fixes the engine and leaves the photograph, so whatever remains is the image.

WHAT IS DIFFERENT
  - Apple Vision (VNRecognizeTextRequest, accurate, revision 3) instead of tesseract,
    which is not installed on this machine at all -- the earlier pass ran on the laptop.
  - Four orientations tried per image, best kept. Dealer photographs are often sideways
    or upside down, and tesseract was given no chance to notice.
  - Language correction OFF. These pages are surnames and colleges, not prose, and
    correction turns `Milstead` into `Milstead`-shaped English.
  - Per-line BOUNDING BOXES kept. A lineup page is a table; column position is what
    separates a jersey number from a weight, and the tesseract pass threw it away.

STILL NOT A PARSE. Nothing is written to the store, no OCR is corrected, and the output
says `vision_words` beside `tesseract_words` rather than replacing it.

  python3 src/census_programs_vision.py [--limit N] [--listing SUBSTR]
"""
import os, re, sys, json, zipfile, shutil, subprocess, tempfile, time

SRC = os.path.expanduser("~/Documents/pgm3-sources/programs")
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
SCRATCH = os.environ.get("YB_SCRATCH", tempfile.gettempdir())
OUTDIR = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
SUMMARY = os.path.join(BASE, "build-reports", "corpus-census-programs-vision.json")
BASELINE = os.path.join(BASE, "build-reports", "corpus-census-programs.json")
IMG = (".jpg", ".jpeg", ".png", ".webp")
BIN = os.path.join(SCRATCH, "visocr")


def build_tool():
    """Compile visocr.m. Kept out of the repo build: it is a local reader, not a product."""
    src = os.path.join(HERE, "visocr.m")
    if os.path.exists(BIN) and os.path.getmtime(BIN) > os.path.getmtime(src):
        return
    cmd = ["clang", "-O2", "-fobjc-arc", "-o", BIN, src,
           "-framework", "Foundation", "-framework", "AppKit",
           "-framework", "Vision", "-framework", "ImageIO", "-framework", "CoreGraphics"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit("cannot build visocr:\n" + r.stderr)


def images_of(listing_dir, work):
    """Every photograph in a listing, loose or zipped, laid out in `work`.
    Same extraction as the tesseract pass, so the two passes see the same images."""
    out = []
    for root, _, fs in os.walk(listing_dir):
        for f in sorted(fs):
            p = os.path.join(root, f)
            if f.lower().endswith(IMG):
                d = os.path.join(work, f"loose_{len(out)}" + os.path.splitext(f)[1].lower())
                shutil.copy(p, d); out.append((f, d))
            elif f.lower().endswith(".zip"):
                try:
                    z = zipfile.ZipFile(p)
                    for n in sorted(z.namelist()):
                        if not n.lower().endswith(IMG) or n.startswith("__MACOSX"): continue
                        d = os.path.join(work, f"zip_{len(out)}" + os.path.splitext(n)[1].lower())
                        with open(d, "wb") as fh: fh.write(z.read(n))
                        out.append((n, d))
                except Exception as e:
                    print("  ZIPERR", f, e, flush=True)
    return out


def ocr(path):
    try:
        r = subprocess.run([BIN, path, "--rotations"], capture_output=True, text=True, timeout=180)
        if r.returncode: return None
        return json.loads(r.stdout)
    except Exception:
        return None


# Headings that say the page is a LINEUP or a BIOGRAPHY page rather than a cover shot.
# Matched loosely because the type is small and the photographs are what they are.
RE_LINEUP = re.compile(r"line.?up|linesmen|starting line|both teams|officials|"
                       r"probable line|referee|umpire|head linesman", re.I)
RE_ROSTER = re.compile(r"\b(halfback|fullback|quarterback|left end|right end|left tackle|"
                       r"right tackle|left guard|right guard|centre|center)\b", re.I)
RE_BIO    = re.compile(r"\b(born|age|height|weight|married|home town|hometown|fraternity|"
                       r"college|high school|years? in (?:the )?league|prep)\b", re.I)


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    only = sys.argv[sys.argv.index("--listing") + 1] if "--listing" in sys.argv else None
    build_tool()
    os.makedirs(OUTDIR, exist_ok=True)

    base = {l["listing"]: l for l in json.load(open(BASELINE))["listings"]} \
        if os.path.exists(BASELINE) else {}

    listings = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    if only: listings = [l for l in listings if only.lower() in l.lower()]
    if limit: listings = listings[:limit]

    res = {"_date": time.strftime("%Y-%m-%d"),
           "_engine": "Apple Vision VNRecognizeTextRequest, accurate, rev3, 4 orientations, no language correction",
           "_note": "OCR is evidence for reading, not a parse. tesseract_* columns are the earlier pass, kept for comparison.",
           "listings": []}
    t0 = time.time()
    for i, name in enumerate(listings, 1):
        work = tempfile.mkdtemp(prefix="pvis_", dir=SCRATCH)
        try:
            imgs = images_of(os.path.join(SRC, name), work)
            rows, best_text = [], []
            for orig, p in imgs:
                d = ocr(p)
                if d is None:
                    rows.append({"image": orig, "words": 0, "error": "vision failed"}); continue
                lines = d["lines"]
                text = "\n".join(l["text"] for l in
                                 sorted(lines, key=lambda l: (-l["y"], l["x"])))
                rows.append({"image": orig, "words": d["words"],
                             "px": [d["px_w"], d["px_h"]], "orientation": d["orientation"],
                             "mean_conf": round(sum(l["conf"] for l in lines) / len(lines), 3) if lines else 0.0,
                             "lineup_heading": bool(RE_LINEUP.search(text)),
                             "position_words": len(RE_ROSTER.findall(text)),
                             "bio_words": len(RE_BIO.findall(text)),
                             "lines": lines})
                best_text.append((orig, text))
            safe = re.sub(r"[^A-Za-z0-9]+", "-", name)[:80].strip("-")
            with open(os.path.join(OUTDIR, safe + ".txt"), "w") as fh:
                fh.write(f"### LISTING: {name}\n### engine: Apple Vision, best of 4 orientations\n")
                for orig, text in best_text:
                    fh.write(f"\n--- IMAGE: {orig}\n{text}\n")
            with open(os.path.join(OUTDIR, safe + ".json"), "w") as fh:
                json.dump({"listing": name, "images": rows}, fh)

            b = base.get(name, {})
            summary = {
                "listing": name, "file": safe + ".txt", "n_images": len(imgs),
                "vision_words": sum(r["words"] for r in rows),
                "vision_words_max": max([r["words"] for r in rows], default=0),
                "vision_images_over_60": sum(1 for r in rows if r["words"] > 60),
                "tesseract_words": b.get("words_total"),
                "tesseract_words_max": b.get("words_max"),
                "tesseract_images_over_60": b.get("images_over_60_words"),
                "images_lineup_heading": sum(1 for r in rows if r.get("lineup_heading")),
                "images_with_positions": sum(1 for r in rows if r.get("position_words", 0) >= 3),
                "images_with_bio_words": sum(1 for r in rows if r.get("bio_words", 0) >= 4),
                "rotated": sorted({r.get("orientation") for r in rows if r.get("orientation") not in (None, "up")}),
                "min_px": min([min(r["px"]) for r in rows if "px" in r], default=None),
                "max_px": max([max(r["px"]) for r in rows if "px" in r], default=None),
            }
            res["listings"].append(summary)
            print(f"[{i:>2}/{len(listings)}] {summary['vision_words']:>6} words "
                  f"(tess {summary['tesseract_words']}) {name[:60]}", flush=True)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    res["_elapsed_s"] = round(time.time() - t0, 1)
    with open(SUMMARY, "w") as fh: json.dump(res, fh, indent=1)
    v = sum(l["vision_words"] for l in res["listings"])
    t = sum(l["tesseract_words"] or 0 for l in res["listings"])
    print(f"\n{len(res['listings'])} listings  vision {v:,} words  tesseract {t:,} words  "
          f"x{v/t:.2f}" if t else "")
    print("summary ->", SUMMARY)


if __name__ == "__main__":
    main()
