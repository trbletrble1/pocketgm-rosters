"""Which programme pages are set in two columns, and which fuse names to other text.

These are the two faults that account for the 1926 Bears/Tigers page entirely, and
this MEASURES them. It changes nothing and fixes nothing.

TWO COLUMNS is measured from the numbers themselves, not from a guess about layout:
take every bare jersey number on the page, split them at the midpoint of the across
axis, and ask whether both halves are populated AND whether the bands that carry two
numbers carry one from each half. A table with a merged row has two numbers on the
SAME side; a two-column page has one on each.

NAMES FUSED TO OTHER TEXT is measured against the extractor's own patterns: a band
holding a capitalised word of three letters or more that NO anchored name pattern
matches. `JACK NOLAN-25 years, height 5 ft. 10 in.` is the case -- legible to a
reader, invisible to `^...$`.

  python3 src/census_programs_shape.py
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from census_programs_lineup_probe import bands, RE_NUM
from census_programs_yield import RE_MAN, RE_SUR, RE_READABLE, men_of

SRC = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
OUT = os.path.join(BASE, "build-reports", "corpus-census-programs-shape.json")


def shape_of(image):
    bs = bands(image)
    if not bs:
        return None
    xs = sorted(x for b in bs for _, x, t in b if RE_NUM.match(t))
    # THE SPLIT IS THE PAGE'S OWN BIGGEST GAP, not a midpoint. A midpoint split is
    # wrong whenever the two columns are unequally wide or the photograph is angled,
    # and it mis-read the one page whose layout is known by hand.
    two_col = False; split = None; sep = 0.0; left = right = 0
    pairs = straddling = 0
    if len(xs) >= 6:
        gaps = [(b - a, (a + b) / 2.0) for a, b in zip(xs, xs[1:])]
        sep, split = max(gaps)
        inner = sorted(g for g, _ in gaps)
        typical = inner[len(inner) // 2]
        # THE MEDIAN GAP IS OFTEN EXACTLY ZERO, because a column's numbers share an
        # across coordinate. `sep >= 4 * 0` is true of every page, so that test alone
        # is a vacuous pass. The span test below cannot degenerate and is the one that
        # actually carries the claim.
        span = xs[-1] - xs[0]
        left = sum(1 for x in xs if x < split); right = len(xs) - left
        for b in bs:
            n = [x for _, x, t in b if RE_NUM.match(t)]
            if len(n) >= 2:
                pairs += 1
                if (min(n) < split) != (max(n) < split): straddling += 1
        # two populated clusters, separated by a gap that is BOTH several times the
        # typical spacing and a real fraction of the page's width
        two_col = (left >= 3 and right >= 3 and span > 0
                   and sep >= 4.0 * typical and sep >= 0.15 * span)

    fused = fusible = 0
    for b in bs:
        toks = [t.strip() for _, _, t in b]
        if not any(RE_NUM.match(t) for t in toks): continue
        anchored = any(RE_MAN.match(t) or RE_SUR.match(t) for t in toks)
        readable = any(RE_READABLE.search(t) for t in toks)
        if readable: fusible += 1
        if readable and not anchored: fused += 1
    return {"image": image.get("image"), "orientation": image.get("orientation"),
            "lines": len(image.get("lines") or []), "bands": len(bs),
            "numbers": len(xs), "two_number_bands": pairs, "straddling_the_split": straddling,
            "column_split_at": split, "gap_as_fraction_of_page_width": (round(sep / span, 3) if len(xs) >= 6 and span else None),
            "numbers_left": left, "numbers_right": right,
            "two_column": two_col,
            "numbered_bands_with_a_readable_name": fusible,
            "numbered_bands_where_no_anchored_pattern_matches": fused,
            "names_fused": fused >= 3 and fused >= 0.6 * max(fusible, 1)}


def main():
    per_listing, images = [], []
    for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        d = json.load(open(f))
        rows = [r for r in (shape_of(im) for im in d["images"]) if r]
        drops = []
        men = sum(len(men_of(im, drops)) for im in d["images"])
        lost = sum(x.get("men_at_least", 0) for x in drops)
        per_listing.append({
            "listing": d["listing"], "file": os.path.basename(f),
            "images": len(d["images"]), "images_banded": len(rows),
            "two_column_images": sum(1 for r in rows if r["two_column"]),
            "fused_name_images": sum(1 for r in rows if r["names_fused"]),
            "men_reported": men, "men_lost_at_least": lost,
            "image_rows": rows})
        images.extend({**r, "listing": d["listing"]} for r in rows)

    tc = sum(1 for r in images if r["two_column"])
    fn = sum(1 for r in images if r["names_fused"])
    both = sum(1 for r in images if r["two_column"] and r["names_fused"])
    total_images = sum(x["images"] for x in per_listing)
    res = {"_note": "measurement only. Nothing is fixed and the extractor is unchanged.",
           "images_total": total_images, "images_banded": len(images),
           "two_column_images": tc, "fused_name_images": fn, "both_faults": both,
           "listings_with_a_two_column_image": sum(1 for x in per_listing if x["two_column_images"]),
           "listings_with_a_fused_name_image": sum(1 for x in per_listing if x["fused_name_images"]),
           "listings": per_listing}
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"images {total_images}, of which {len(images)} produced bands at all")
    print(f"  set in TWO COLUMNS                      {tc:>4}")
    print(f"  names FUSED to other text               {fn:>4}")
    print(f"  both faults on the same image           {both:>4}")
    print(f"  listings with at least one two-column image: {res['listings_with_a_two_column_image']} of {len(per_listing)}")
    print(f"  listings with at least one fused-name image: {res['listings_with_a_fused_name_image']} of {len(per_listing)}")
    print("->", OUT)
    return res


if __name__ == "__main__":
    main()
