"""What does a programme lineup page actually yield, and can a ROW be proved?

THE STANDARD is the one that dropped Lions 1942 and that guide_entries.py enforces:
an entry whose boundary cannot be proved is dropped and counted, because a fact
attached to the wrong man is undetectable and permanent.

A LINEUP PAGE IS A TABLE, so the entry is a row and the geometry is different from
prose. Two things were established by looking before this was written:

  1. Reconstructing COLUMNS fails on this material. The photographs are angled, so
     perspective makes a column drift down the page; clustering on the column
     coordinate merged four columns of the 1936 Redskins/Giants lineup into one
     blob of 311 lines. An earlier version of this probe did exactly that and
     reported 96% of pairings "ambiguous" -- an artefact of the clustering, not a
     property of the page. Rows are the stable structure; band on the DOWN
     coordinate and sort within the band by the across coordinate.

  2. Banded that way the same page reads properly:
         40 | Millner   | Left End       | ...
         24 | Bausch    | Center         | Phillips | 19
         35 | R. Smith  | Quarterback    | Goodwin  | 14
     and below it a fuller roster carrying number, full name, position, college
     and height.

TWO FAILURE MODES, both seen on that one page, both fatal if unchecked:
  ROW MERGE    two adjacent rows fall inside one band --
               `21 | 17 | Olsson | Edwards | Left Guard | Left Tackle | ...`
               This is the Perko failure in table form.
  COLUMN SLIP  a cell the OCR missed shifts every later field left, so
               `13 | Edw. Justice | H.b. | 6.2` puts a HEIGHT where the college goes.

Both are detectable from the band itself, which is what makes a proof possible:
a band carrying exactly one bare number and at least one name is forced; a band
carrying two numbers is a merge and must be dropped. This counts both.

  python3 src/census_programs_lineup_probe.py [--listing SUBSTR] [--dump]
"""
import os, re, sys, json, statistics, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from census_programs_reconstruct import AXES

SRC = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
OUT = os.path.join(BASE, "build-reports", "corpus-census-programs-lineup-probe.json")

RE_NUM   = re.compile(r"^\s*(\d{1,2})\s*$")
RE_NAME  = re.compile(r"^\s*((?:[A-Z]\.?\s+)?[A-Z][A-Za-z'’\-]{2,}(?:\s+[A-Z][A-Za-z'’\-]{2,})?)\s*$")
RE_POS   = re.compile(r"^\s*(Left|Right|L\.|R\.)?\s*(End|Tackle|Guard|Center|Centre|Quarterback|"
                      r"Halfback|Fullback|Back|H\.?b\.?|F\.?b\.?|Q\.?b\.?|C\.?|E\.?|T\.?|G\.?)\s*$", re.I)
RE_HT    = re.compile(r"^\s*[5-6][\.\-'’ ]\s?\d{1,2}\s*$")
RE_WT    = re.compile(r"^\s*(1[5-9]\d|2[0-6]\d)\s*$")
RE_COLL  = re.compile(r"[A-Z][a-z]+.*\b(University|College|State|Tech|Institute)\b|"
                      r"^\s*(Yale|Harvard|Navy|Army|Brown|Colgate|Fordham|Syracuse|Michigan|"
                      r"Purdue|Nebraska|Stanford|Alabama|Georgetown|Villanova|Marquette|Duquesne)\s*$")
RE_HEAD  = re.compile(r"\bNo\.?\b", re.I)


def bands(image):
    """Rows, as bands on the down coordinate. The threshold is derived from the page's
    own median line spacing, never tuned per page."""
    lines = image.get("lines") or []
    if len(lines) < 12: return None
    f = AXES.get(image.get("orientation", "up"), AXES["up"])
    # BAND WITHIN EACH COLUMN, NEVER ACROSS THE PAGE. This banded the whole page on the
    # down coordinate, so on a two-column page a single band held one man from the LEFT
    # column and one from the RIGHT. The band then carried two numbers, was discarded as
    # `band_multi_number`, and BOTH men were lost -- 866 drops across the class. A column
    # is a geometric fact and is found from the page's own widest gaps, not assumed to be
    # two. ONE IMPLEMENTATION: the split is programme_bio_page.columns().
    # AND THE SPLIT IS TRIGGERED BY THE SYMPTOM, NOT APPLIED BLINDLY. Splitting every
    # page into columns first made the class WORSE -- 255 men to 219 -- because on a
    # single-column line-up page the row is `NUM NAME POSITION` and the gaps BETWEEN
    # FIELDS look exactly like a column break, so every row shattered. The thing that
    # distinguishes a two-column PAGE from a multi-field ROW is that a two-column page
    # puts TWO NUMBERS at the same height. So: band the page whole, and only re-band by
    # column when that banding actually shows the symptom.
    def _band(pts_in):
        pts = sorted(pts_in)
        if len(pts) < 2: return []
        ds = [q[0] for q in pts]
        gaps = sorted(b - a for a, b in zip(ds, ds[1:]) if b - a > 1e-6)
        if not gaps: return []
        th = 3.0 * statistics.median(gaps)
        res, cur = [], [pts[0]]
        for q in pts[1:]:
            if q[0] - cur[-1][0] > th: res.append(cur); cur = []
            cur.append(q)
        res.append(cur)
        return res

    whole = _band([(f(l)[0], f(l)[1], l["text"]) for l in lines])
    numbered = [b for b in whole if any(RE_NUM.match(x[2].strip()) for x in b)]
    multi = sum(1 for b in numbered
                if sum(1 for x in b if RE_NUM.match(x[2].strip())) > 1)
    if not numbered or multi / len(numbered) < 0.30:
        return [sorted(b, key=lambda x: x[1]) for b in whole]

    import programme_bio_page as _B
    cols = _B.columns(lines, image.get("orientation", "up")) or [lines]
    out = []
    for col in cols:
        out += _band([(f(l)[0], f(l)[1], l["text"]) for l in col])
    if not out: return None
    return [sorted(b, key=lambda x: x[1]) for b in out]


def probe_page(image):
    bs = bands(image)
    if not bs: return None
    # a lineup/roster page is one with a run of bands each carrying a bare number
    numbered = [b for b in bs if sum(1 for _, _, t in b if RE_NUM.match(t)) >= 1]
    if len(numbered) < 6: return None
    r = collections.Counter(); fields = collections.Counter()
    for b in numbered:
        toks = [t.strip() for _, _, t in b]
        nnum = sum(1 for t in toks if RE_NUM.match(t))
        nname = sum(1 for t in toks if RE_NAME.match(t) and not RE_NUM.match(t)
                    and not RE_POS.match(t))
        if nnum >= 2: r["merged"] += 1
        elif nname == 0: r["no_name"] += 1
        else: r["proved"] += 1
        if nnum == 1 and nname: fields["number"] += 1; fields["name"] += 1
        if any(RE_POS.match(t) for t in toks): fields["position"] += 1
        if any(RE_COLL.search(t) for t in toks): fields["college"] += 1
        if any(RE_HT.match(t) for t in toks): fields["height"] += 1
        if any(RE_WT.match(t) for t in toks): fields["weight"] += 1
    return {"rows": dict(r), "fields": dict(fields), "bands": len(bs)}


def main():
    only = sys.argv[sys.argv.index("--listing") + 1] if "--listing" in sys.argv else None
    dump = "--dump" in sys.argv
    tot = collections.Counter(); ftot = collections.Counter(); per = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SRC, f)))
        if only and only.lower() not in d["listing"].lower(): continue
        rr = collections.Counter(); ff = collections.Counter(); pages = 0
        for im in d["images"]:
            p = probe_page(im)
            if not p: continue
            pages += 1; rr.update(p["rows"]); ff.update(p["fields"])
        if pages:
            per.append({"listing": d["listing"], "pages": pages, **dict(rr),
                        "fields": dict(ff)})
            tot.update(rr); ftot.update(ff)
    per.sort(key=lambda x: -x.get("proved", 0))
    n = sum(tot.values())
    print(f"listings with a numbered roster/lineup page: {len(per)}")
    print(f"numbered rows found: {n}")
    for k in ("proved", "merged", "no_name"):
        print(f"   {k:<9} {tot[k]:>5}  {tot[k]/n:>5.0%}" if n else "")
    print(f"\nfields present, counted over rows (a row may carry several):")
    for k in ("number", "name", "position", "college", "height", "weight"):
        print(f"   {k:<9} {ftot[k]:>5}")
    if dump:
        print("\nby listing (proved / merged / no-name):")
        for x in per[:24]:
            print(f"   {x.get('proved',0):>4} /{x.get('merged',0):>3} /{x.get('no_name',0):>3}"
                  f"   {x['listing'][:60]}")
    json.dump({"_note": "row-band probe; proved = exactly one bare number and at least one name",
               "totals": dict(tot), "fields": dict(ftot), "listings": per},
              open(OUT, "w"), indent=1)
    print("\n->", OUT)


if __name__ == "__main__":
    main()
