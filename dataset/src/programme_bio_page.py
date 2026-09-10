"""Read a programme BIO page -- a roster where each man is a paragraph, not a row.

TWO FAULTS, BOTH MEASURED BEFORE THEY WERE FIXED, both in census_programs_yield.py.

  THE BANDING READ ACROSS THE WHOLE PAGE. Most of these pages are set in two or three
  columns. A horizontal band therefore holds one man from the left column and one from
  the right, the band is discarded as `band_multi_number`, and BOTH men are lost. The
  fix is not a better band: it is to put the page into reading order FIRST, using the
  bounding boxes, which census_programs_reconstruct.py already established
  geometrically. Column membership is a geometric fact.

  THE NAME PATTERNS WERE ANCHORED. `^\\s*NAME\\s*$` matches only a line that is nothing
  but a name. Page Seven of the 1926 Bears-Tigers programme reads
  `JACK NOLAN-25 years, height 5 ft. 10 in.` on ONE line, so no name on that page could
  ever have matched, whatever the banding did. An anchored pattern is a decision that
  the page is a list; these pages are prose.

THE TRANSCRIPTION IS THE CHECK, NOT THE TARGET. `Football Archive/docs/
1926-bears-tigers-programme-transcription.md` holds all 28 players and 4 staff, read by
eye. The rule here is written from what a bio entry IS -- a name, then an age in years,
then the rest of the sentence -- and the transcription then says whether it holds. It is
not tuned until the two agree.

  python3 src/programme_bio_page.py --check    read Page Seven and score it
"""
import os, re, sys, json, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
OCR = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")

# THE TRANSFORM, from census_programs_reconstruct.py. Vision returns boxes in the
# ORIGINAL image frame, so a page read sideways has text running vertically in box
# coordinates. `down` is the axis along a column; `column` is the axis across the page.
DOWN = {"up":    lambda b: b["y"],  "down":  lambda b: -b["y"],
        "right": lambda b: -b["x"], "left":  lambda b: b["x"]}
ACROSS = {"up":    lambda b: b["x"], "down":  lambda b: -b["x"],
          "right": lambda b: b["y"], "left":  lambda b: -b["y"]}

# A BIO ENTRY IS A NAME THEN AN AGE. Unanchored at the end -- the rest of the sentence
# follows on the same line and that is the whole point. The dash is whatever the printer
# used and whatever OCR made of it.
# A PRINTED NAME MAY START WITH A QUOTED NICKNAME AND MAY CARRY LOWER CASE.
# `"HONEY" EARLE`, `"COWBOY" WELLS` and `FELTON McCONNELL` are all names as the page
# prints them, and a pattern demanding an initial capital followed by capitals refuses
# every one. It is the `- NN years` that identifies an entry, not the shape of the name,
# so the name may be anything up to it.
ENTRY = re.compile(r"^\s*[\"“”']?\s*([A-Z][A-Za-z’'\"“”.\- ]{2,34}?)\s*[-–—]\s*(\d{1,2})\s*years", re.U)
HEIGHT = re.compile(r"height\s*([5-7])\s*ft\.?\s*(\d{1,2})?", re.I)
WEIGHT = re.compile(r"weight\s*(\d{2,3})\s*lbs", re.I)


def columns(lines, orientation, n_cols=None):
    """Lines grouped into columns by the across-axis, each sorted down the page.

    THE COLUMN BOUNDARY IS FOUND FROM THE GAPS, not assumed to be two. A page set in
    three narrow columns and a page set in two are the same problem and the widest gaps
    say which it is."""
    if not lines: return []
    a = ACROSS[orientation]; d = DOWN[orientation]
    xs = sorted(a(l) for l in lines)
    gaps = sorted(((xs[i+1] - xs[i], i) for i in range(len(xs)-1)), reverse=True)
    # a column break is a gap wider than 6% of the page across
    cuts = sorted(xs[i] + g/2 for g, i in gaps if g > 0.06)
    if n_cols: cuts = cuts[:n_cols-1]
    def which(l):
        v = a(l)
        return sum(1 for c in cuts if v > c)
    out = {}
    for l in lines: out.setdefault(which(l), []).append(l)
    return [sorted(v, key=d) for _, v in sorted(out.items())]


def entries_of(lines, orientation):
    """-> one record per man. A continuation line belongs to the entry above it IN ITS
    OWN COLUMN, which is the thing reading order buys."""
    men = []
    for col in columns(lines, orientation):
        cur = None
        for l in col:
            t = (l.get("text") or "").strip()
            if not t: continue
            m = ENTRY.match(t)
            if m:
                cur = {"name_as_printed": m.group(1).strip(" .-"),
                       "age_as_printed": f"{m.group(2)} years", "text": t}
                men.append(cur)
            elif cur is not None and not re.fullmatch(r"\d{1,2}", t):
                cur["text"] += " " + t
    for m in men:
        h = HEIGHT.search(m["text"]); w = WEIGHT.search(m["text"])
        if h: m["height_as_printed"] = f"{h.group(1)} ft. {h.group(2)} in." if h.group(2) else f"{h.group(1)} ft."
        if w: m["weight_as_printed"] = f"{w.group(1)} lbs."
        tail = m["text"]
        cut = WEIGHT.search(tail)
        if cut: m["college_or_prior_as_printed"] = tail[cut.end():].strip(" .,")
    return men


def read_page(listing_json, image):
    d = json.load(open(listing_json))
    im = next((x for x in d["images"] if x["image"] == image), None)
    if im is None: raise SystemExit(f"{image}: not in {listing_json}")
    return entries_of(im.get("lines") or [], im.get("orientation") or "up")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def check():
    f = os.path.join(OCR, "1926-RED-GRANGE-S-record-game-CHICAGO-BEARS-v-L-A-TIGERS-"
                          "Football-Program.json")
    men = read_page(f, "s-l1600 (9).webp")
    doc = os.path.expanduser("~/Dropbox/Football Archive/docs/"
                             "1926-bears-tigers-programme-transcription.md")
    want = []
    for line in open(doc, encoding="utf-8"):
        c = [x.strip() for x in line.split("|")]
        if len(c) > 3 and re.fullmatch(r"\d{1,2}", c[1] or "") and "years" in line:
            want.append(c[2])
    got = {norm(m["name_as_printed"]) for m in men}
    hit = [w for w in want if norm(w) in got]
    miss = [w for w in want if norm(w) not in got]
    extra = sorted(got - {norm(w) for w in want})
    print(f"the transcription holds {len(want)} players")
    print(f"the reader found        {len(men)} entries")
    print(f"  recovered             {len(hit)}")
    print(f"  missed                {len(miss)}  {miss}")
    print(f"  found and not in it   {len(extra)}  {extra[:6]}")
    full = [m for m in men if m.get("height_as_printed") and m.get("weight_as_printed")]
    print(f"  with height AND weight {len(full)}")
    for m in men[:3]:
        print("   e.g.", {k: v for k, v in m.items() if k != "text"})
    return 0 if len(hit) >= len(want) else 1


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else check())
