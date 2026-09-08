"""OCR every photograph in the eBay game-programme listings so the whole class can be
READ rather than sampled.

WHY. `pgm3-sources/programs/` is 55 listings, 1925-1946, ~660 photographs and NO text
layer of any kind -- a class nobody has opened. Opening four of them by eye showed the
listings are not one thing: some are dealer beauty-shots of the cover from several
angles, others photograph the programme page by page, including the lineup spread (both
clubs' rosters with number, college, weight, position, and the officials by name) and
player-biography pages with captioned headshots. A title cannot tell those apart and a
sample would only estimate the split. 660 images is small enough to do completely.

The OCR is EVIDENCE FOR READING, never a parse. Output goes to the session scratchpad
and a summary to build-reports/. Nothing is written to the store and no OCR is corrected.

  python3 src/census_programs_ocr.py [--out DIR]
"""
import os, re, sys, json, zipfile, shutil, subprocess, tempfile

SRC = os.path.expanduser("~/Documents/pgm3-sources/programs")
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else \
    "/private/tmp/claude-501/-Users-ryannecci-Documents/775492f6-85e4-45dc-8452-79a3131ced7a/scratchpad/prog-ocr"
SUMMARY = os.path.join(BASE, "build-reports", "corpus-census-programs.json")
IMG = (".jpg", ".jpeg", ".png", ".webp")


def images_of(listing_dir, work):
    """Every photograph in a listing, loose or zipped, copied into `work`."""
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
    """Best of --psm 3 (page) and --psm 11 (sparse); pages of a programme are dense,
    beauty-shots of a cover are sparse, and neither mode reads both well."""
    best = ""
    for psm in ("3", "11"):
        try:
            r = subprocess.run(["tesseract", path, "stdout", "-l", "eng", "--oem", "1", "--psm", psm],
                               capture_output=True, text=True, timeout=120)
            if len(r.stdout) > len(best): best = r.stdout
        except Exception:
            pass
    return best


def main():
    os.makedirs(OUT, exist_ok=True)
    listings = sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d)))
    res = {"_date": "2026-09-07", "_note": "OCR of every programme photograph; evidence for reading, not a parse",
           "listings": []}
    for i, name in enumerate(listings, 1):
        work = tempfile.mkdtemp(prefix="prog_")
        try:
            imgs = images_of(os.path.join(SRC, name), work)
            texts = []
            for orig, p in imgs:
                t = ocr(p)
                texts.append({"image": orig, "words": len(t.split()), "text": t})
            safe = re.sub(r"[^A-Za-z0-9]+", "-", name)[:80].strip("-")
            with open(os.path.join(OUT, safe + ".txt"), "w") as fh:
                fh.write(f"### LISTING: {name}\n")
                for t in texts:
                    fh.write(f"\n--- IMAGE {t['image']}  words={t['words']} ---\n{t['text']}\n")
            res["listings"].append({"listing": name, "file": safe + ".txt", "images": len(imgs),
                                    "words_total": sum(t["words"] for t in texts),
                                    "words_max": max([t["words"] for t in texts] or [0]),
                                    "images_over_60_words": sum(1 for t in texts if t["words"] > 60)})
            print(f"[{i}/{len(listings)}] {len(imgs):3} imgs  "
                  f"{sum(t['words'] for t in texts):6} words  {name[:56]}", flush=True)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    IO.dump_atomic(res, SUMMARY, indent=1)
    print("wrote", SUMMARY)


if __name__ == "__main__":
    main()
