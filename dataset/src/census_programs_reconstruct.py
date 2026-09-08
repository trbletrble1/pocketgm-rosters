"""Put the programme OCR back into READING ORDER, using the bounding boxes.

WHY THIS IS NEEDED BEFORE ANYONE ASKS WHAT A LINEUP PAGE YIELDS. The Vision pass
records one text line at a time. Sorting those lines by raw coordinate produces a
page that LOOKS readable and is not: on the 1926 Bears v L.A. Tigers roster page a
man's own continuation line lands several lines away from his name, because the page
is three narrow columns photographed sideways. Every field is present and no entry
is contiguous. Counting men off that text would be counting an artefact.

THE TRANSFORM, and how it was established rather than assumed. Vision returns boxes
in the ORIGINAL image frame, not the frame of the orientation it read the text in.
So for a page read at orientation `right`, text runs vertically in box coordinates:
`TIGERS-BEARS` is w=0.016, h=0.177. Checked against four lines of two known entries:

    x=0.587 y=0.585  DEL HUFFORD-25 years, height 5 ft. 11
    x=0.575 y=0.583  in., weight 175 lbs. University of California
    x=0.517 y=0.583  HARRY SHIPKEY-23 years, height 6 ft.
    x=0.507 y=0.583  2 in., weight 205 lbs. Stanford. Tackle 1924.

Same y to three decimals -- that is the COLUMN. Descending x -- that is DOWN THE PAGE.
So for `right`: down = -x, column = y. The other orientations follow by rotation.

WHAT IS PROVED AND WHAT IS NOT. Column membership and the order of lines within a
column are geometric facts and are proved. The left-to-right order OF the columns is
inferred from the sign convention and is not load-bearing here: an entry never spans
two columns, so entry integrity does not depend on it. Stated rather than hidden.

Writes reconstructed text beside the raw. Reading, not parsing; no claims, no store.

  python3 src/census_programs_reconstruct.py [--listing SUBSTR] [--min-words N]
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
SRC = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
OUT = os.path.join(BASE, "build-reports", "corpus-census-programs-reading-order")

# (down_value, column_value) as functions of the raw box. Vision's y is bottom-up.
AXES = {
    "up":    lambda b: (-(b["y"]),  b["x"]),
    "down":  lambda b: (  b["y"],  -b["x"]),
    "right": lambda b: (-(b["x"]), -b["y"]),
    "left":  lambda b: (  b["x"],   b["y"]),
}


def columns(lines, orient, tol=0.035):
    """Group lines into columns by their column coordinate, then order each column
    down the page. `tol` is a fraction of the page; columns in these programmes are
    far wider apart than the jitter of an angled photograph."""
    f = AXES.get(orient, AXES["up"])
    pts = [(f(l), l) for l in lines]
    pts.sort(key=lambda p: p[0][1])                      # by column coordinate
    cols, cur, last = [], [], None
    for (down, col), l in pts:
        if last is not None and col - last > tol:
            cols.append(cur); cur = []
        cur.append((down, l)); last = col
    if cur: cols.append(cur)
    for c in cols: c.sort(key=lambda p: p[0])            # down the page
    return [[l for _, l in c] for c in cols]


def page_text(image):
    lines = image.get("lines") or []
    if not lines: return ""
    out = []
    for col in columns(lines, image.get("orientation", "up")):
        out.append("\n".join(l["text"] for l in col))
    return "\n\n[column]\n".join(out)


def main():
    only = sys.argv[sys.argv.index("--listing") + 1] if "--listing" in sys.argv else None
    minw = int(sys.argv[sys.argv.index("--min-words") + 1]) if "--min-words" in sys.argv else 0
    os.makedirs(OUT, exist_ok=True)
    n = pages = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SRC, f)))
        if only and only.lower() not in d["listing"].lower(): continue
        chunks = [f"### LISTING: {d['listing']}",
                  "### reading order reconstructed from bounding boxes; columns marked"]
        for im in d["images"]:
            if im.get("words", 0) < minw: continue
            chunks.append(f"\n--- IMAGE: {im['image']}  ({im.get('words')} words, "
                          f"read at orientation {im.get('orientation')})\n" + page_text(im))
            pages += 1
        with open(os.path.join(OUT, f[:-5] + ".txt"), "w") as fh:
            fh.write("\n".join(chunks) + "\n")
        n += 1
    print(f"{n} listings, {pages} pages reconstructed -> {OUT}")


if __name__ == "__main__":
    main()
