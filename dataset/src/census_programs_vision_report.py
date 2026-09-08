"""Compare the Apple Vision OCR pass with the tesseract pass, and split the result by
the one thing that is NOT the engine: how many pixels the photograph has.

The census reported programme OCR as a floor. Two causes were possible and had never
been separated -- a weak engine, or a photograph too small to read. This splits them:

  engine     both passes saw the SAME images via the same extraction function, so any
             difference between them is the engine. (tesseract is not installed on this
             machine; its numbers are carried across from the laptop run.)
  photograph 9 of the 55 listings hold eBay's 1200x1600 `s-l1600` images; the other 46
             hold only the ~1000x666 variant, zipped. No listing holds both, so this is
             a comparison of strata, not of the same page twice -- stated as such.

  python3 src/census_programs_vision_report.py
"""
import os, json, statistics

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
VIS = json.load(open(os.path.join(BASE, "build-reports", "corpus-census-programs-vision.json")))
L = VIS["listings"]

def rate(a, b): return f"x{a/b:.2f}" if b else "n/a"

vw = sum(x["vision_words"] for x in L)
tw = sum(x["tesseract_words"] or 0 for x in L)
vo = sum(x["vision_images_over_60"] for x in L)
to = sum(x["tesseract_images_over_60"] or 0 for x in L)
ni = sum(x["n_images"] for x in L)

print(f"{len(L)} listings, {ni} photographs\n")
print(f"{'':<26}{'tesseract':>12}{'vision':>12}{'':>8}")
print(f"{'words read':<26}{tw:>12,}{vw:>12,}{rate(vw,tw):>8}")
print(f"{'photographs over 60 words':<26}{to:>12}{vo:>12}{rate(vo,to):>8}")
print(f"{'listings with a lineup heading':<26}{'10':>12}{sum(1 for x in L if x['images_lineup_heading']):>12}")
print(f"{'listings, positions on a page':<26}{'-':>12}{sum(1 for x in L if x['images_with_positions']):>12}")
print(f"{'listings, biography wording':<26}{'-':>12}{sum(1 for x in L if x['images_with_bio_words']):>12}")
rot = sum(1 for x in L if x["rotated"])
print(f"\nlistings holding at least one photograph NOT upright: {rot}")

# ---- the split that matters: pixels
hi = [x for x in L if (x["max_px"] or 0) >= 1400]
lo = [x for x in L if (x["max_px"] or 0) < 1400]
print(f"\nBY RESOLUTION  (no listing holds both, so these are strata)")
print(f"{'':<22}{'listings':>9}{'images':>8}{'words/image':>13}{'over 60':>9}{'lineup':>8}{'bio':>6}")
for name, S in (("1200x1600 s-l1600", hi), ("~1000x666 zipped", lo)):
    if not S: continue
    im = sum(x["n_images"] for x in S)
    w = sum(x["vision_words"] for x in S)
    print(f"{name:<22}{len(S):>9}{im:>8}{w/im:>13.0f}"
          f"{sum(x['vision_images_over_60'] for x in S)/im:>8.0%}"
          f"{sum(1 for x in S if x['images_lineup_heading']):>8}"
          f"{sum(1 for x in S if x['images_with_bio_words']):>6}")

print("\nTOP LISTINGS BY VISION WORDS")
for x in sorted(L, key=lambda x: -x["vision_words"])[:12]:
    px = "1600" if (x["max_px"] or 0) >= 1400 else " 666"
    print(f"  {x['vision_words']:>6} (tess {str(x['tesseract_words'] or 0):>5})  px{px}  "
          f"lineup={x['images_lineup_heading']} bio={x['images_with_bio_words']}  {x['listing'][:58]}")

print("\nLISTINGS WHERE VISION FOUND A LINEUP HEADING AND TESSERACT'S TOTAL WAS THIN")
for x in sorted(L, key=lambda x: -(x["images_lineup_heading"] or 0)):
    if x["images_lineup_heading"] and (x["tesseract_words"] or 0) < 300:
        print(f"  tess {str(x['tesseract_words'] or 0):>4} -> vision {x['vision_words']:>5}  {x['listing'][:66]}")
