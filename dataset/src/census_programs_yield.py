"""What a programme lineup page YIELDS: men, fields, and how many the archive holds.

Reading, not parsing. Nothing here is written to the store and no claim is made.
Every count is of what a page can be SEEN to carry, and a man is only counted where
the row he sits on is forced by the geometry.

WHAT COUNTS AS A MAN. A row band carrying exactly one bare jersey number and one
name-shaped token. Bands carrying two numbers are the two-club starting-lineup
format -- legitimately two men -- but they are NOT counted here, because the field
order across the pair is not forced: on the 1936 Redskins/Giants roster

    20 | 21 | Lester Olsson | Clifford Battles | H.b. | Guard | Mercer | W. Va Wesleyan

Olsson was the guard and Battles the halfback, and reading the tokens in order gives
both men the other's position. Counting them would inflate the yield with pairs whose
fields are a coin toss.

  python3 src/census_programs_yield.py [--match]      --match joins the person index
"""
import os, re, sys, json, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from census_programs_lineup_probe import bands, RE_NUM, RE_POS

SRC = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
OUT = os.path.join(BASE, "build-reports", "corpus-census-programs-yield.json")

# a name with an optional initial, allowing the full-name form the rosters use
RE_MAN = re.compile(r"^\s*((?:[A-Z][a-z]+|[A-Z]\.)(?:\s+(?:[A-Z][a-z]+|[A-Z]\.|\"[A-Z][a-z]+\"))*"
                    r"\s+[A-Z][A-Za-z'’\-]{2,})\s*$")
RE_SUR = re.compile(r"^\s*((?:[A-Z]\.\s*)?[A-Z][A-Za-z'’\-]{2,})\s*$")
RE_HT  = re.compile(r"^\s*([5-6])[\.\-'’ ]\s?(\d{1,2})\s*$")
RE_WT  = re.compile(r"^\s*(1[5-9]\d|2[0-6]\d)\s*$")
RE_COL = re.compile(r"\b(University|College|State|Tech|Institute|Normal)\b|"
                    r"^(Yale|Harvard|Navy|Army|Brown|Colgate|Fordham|Syracuse|Michigan|Purdue|"
                    r"Nebraska|Stanford|Alabama|Georgetown|Villanova|Marquette|Duquesne|"
                    r"Notre Dame|Minnesota|Iowa|Pittsburgh|Holy Cross|Gonzaga|Tufts)$")


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


# A CAPITALISED WORD OF THREE LETTERS OR MORE. Not a name pattern -- deliberately
# weaker than RE_MAN/RE_SUR, because the point of the drop log is to show what the
# strict patterns could not see. `JACK NOLAN-25 years` matches here and nowhere else.
RE_READABLE = re.compile(r"\b[A-Z][A-Za-z'’\-]{2,}\b")


def readable_names(toks):
    """Text in a band that a human would read as a name, whether or not the anchored
    patterns match it. Reported, never used to accept a man."""
    out = []
    for t in toks:
        w = RE_READABLE.findall(t)
        if w: out.append({"token": t[:120], "capitalised_words": w[:8]})
    return out[:12]


def men_of(image, drops=None):
    """UNCHANGED in what it accepts. Every drop is now recorded in `drops`.

    Before this, each of the four exits below was a bare `return []` or `continue`.
    A page the parser could not read and a page with nothing on it produced the same
    output -- no men, no note, nothing to count. That is the archive's standing
    defect class and this is the instrument for it, not the fix for it."""
    def drop(why, **kw):
        if drops is not None:
            drops.append({"image": image.get("image"), "why": why,
                          "orientation": image.get("orientation"),
                          "lines": len(image.get("lines") or []), **kw})
    bs = bands(image)
    if not bs:
        n = len(image.get("lines") or [])
        drop("no_bands", detail=("fewer than 12 lines" if n < 12 else
             "no positive gaps between lines"), bands=0)
        return []
    numbered = [b for b in bs if sum(1 for _, _, t in b if RE_NUM.match(t)) >= 1]
    if len(numbered) < 6:
        drop("image_under_6_numbered_bands", bands=len(bs), numbered_bands=len(numbered),
             numbers_seen=sum(sum(1 for _, _, t in b if RE_NUM.match(t)) for b in numbered),
             readable=readable_names([t.strip() for b in numbered for _, _, t in b]))
        return []
    out = []
    for bi, b in enumerate(numbered):
        toks = [t.strip() for _, _, t in b]
        nums = [t for t in toks if RE_NUM.match(t)]
        if len(nums) != 1:
            # Pairs are not forced -- see docstring. But a two-column PAGE also lands
            # here, and there the two numbers are two columns, not two merged rows.
            drop("band_multi_number", band=bi, numbers=nums, tokens=len(toks),
                 men_at_least=len(nums), readable=readable_names(toks))
            continue
        # EACH TOKEN IS ASSIGNED TO AT MOST ONE FIELD, in priority order. Without
        # this, "Washington State" matches the name pattern as well as the college
        # pattern and every roster row looks like it carries two men. An earlier
        # version reported 39% of rows as merges on exactly that artefact.
        claimed = set()
        def take(pred):
            got = []
            for i, t in enumerate(toks):
                if i in claimed or not pred(t): continue
                claimed.add(i); got.append(t)
            return got
        take(lambda t: RE_NUM.match(t))                     # the number, already counted
        pos = take(lambda t: RE_POS.match(t))
        col = take(lambda t: RE_COL.search(t) and t.strip().lower() != "college")
        ht  = take(lambda t: RE_HT.match(t))
        wt  = take(lambda t: RE_WT.match(t))
        full = take(lambda t: RE_MAN.match(t))
        sur = take(lambda t: RE_SUR.match(t))
        names = full + sur
        names = [n for n in names if n.strip().lower() not in
                 ("college", "name", "position", "height", "weight", "no", "total")]
        if not names:
            # A number, and not one token that is NOTHING BUT a name. On a bio page
            # every entry reads `JACK NOLAN-25 years, height 5 ft. 10 in.` and the
            # anchored patterns cannot match any of them.
            drop("band_no_name_matched", band=bi, numbers=nums, tokens=len(toks),
                 men_at_least=1, readable=readable_names(toks))
            continue
        # SURPLUS IS THE PROOF CONDITION. Two colleges, or two heights, on one row
        # means two men's rows merged and one man's number was lost -- the case that
        # gave Charlie Malone another man's college and height, and the only kind of
        # merge that does not announce itself in the number count.
        surplus = [k for k, v in (("name", names), ("position", pos), ("college", col),
                                  ("height", ht), ("weight", wt)) if len(v) > 1]
        rec = {"number": int(nums[0]), "name": names[0], "full_name": bool(full)}
        if pos: rec["position"] = pos[0]
        if col: rec["college"] = col[0]
        if ht: rec["height"] = ht[0]
        if wt: rec["weight"] = int(wt[0])
        if surplus: rec["surplus"] = surplus
        out.append(rec)
    return out


def main():
    match = "--match" in sys.argv
    listings, all_drops = [], []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SRC, f)))
        men, pages, drops = [], 0, []
        for im in d["images"]:
            m = men_of(im, drops)
            if m: pages += 1; men.extend(m)
        # one listing photographs the same page more than once; dedupe on number+name
        seen, uniq, deduped = set(), [], 0
        for m in men:
            k = (m["number"], norm(m["name"]))
            if k in seen: deduped += 1; continue
            seen.add(k); uniq.append(m)
        # LOST is the floor, not the estimate: every dropped band demonstrably held at
        # least `men_at_least` men, and a multi-number band holds at least as many men
        # as it holds numbers. The true figure is higher wherever a man's number was
        # never read at all.
        lost = sum(x.get("men_at_least", 0) for x in drops)
        rec = {"listing": d["listing"], "file": f, "pages": pages, "men": uniq,
               "reported": len(uniq), "deduped": deduped,
               "dropped_bands": sum(1 for x in drops if x["why"].startswith("band_")),
               "dropped_images": sum(1 for x in drops if not x["why"].startswith("band_")),
               "men_lost_at_least": lost,
               "images": len(d["images"]), "drops": drops}
        listings.append(rec)
        all_drops.extend({**x, "listing": d["listing"]} for x in drops)

    tot = sum(len(x["men"]) for x in listings)
    lost = sum(x["men_lost_at_least"] for x in listings)
    if not tot:
        raise SystemExit("REFUSING TO REPORT: no listing yielded a man, so every "
                         "percentage below would divide by zero and the report would "
                         "describe nothing.")
    fc = collections.Counter()
    for x in listings:
        for m in x["men"]:
            for k in ("position", "college", "height", "weight"): fc[k] += k in m
            fc["full_name"] += m["full_name"]
    yielding = sum(1 for x in listings if x["men"])
    print(f"listings: {len(listings)}   yielding men: {yielding}   "
          f"men on forced rows: {tot}")
    print(f"DROPPED, uncounted until now: {sum(x['dropped_bands'] for x in listings)} bands "
          f"and {sum(x['dropped_images'] for x in listings)} images, "
          f"holding AT LEAST {lost:,} men -- {lost/max(tot,1):.1f}x what was reported")
    print("\nfields carried, of those men:")
    for k in ("full_name", "position", "college", "height", "weight"):
        print(f"   {k:<10} {fc[k]:>4}  {fc[k]/tot:>5.0%}")
    print("\nmen per listing, biggest first:")
    for x in sorted(listings, key=lambda x: -len(x["men"]))[:14]:
        wc = sum(1 for m in x["men"] if "college" in m)
        print(f"   {len(x['men']):>3} men ({wc:>2} with college)   {x['listing'][:58]}")

    import collections as _c
    by_why = _c.Counter(x["why"] for x in all_drops)
    res = {"_note": "men on rows forced by geometry; two-number rows excluded as unforced",
           "_drops_note": "every exit that discards a band or an image now records what it "
                          "threw away. men_lost_at_least is a FLOOR: a band holding two "
                          "numbers held at least two men. Nothing here is a fix -- the "
                          "extractor accepts exactly what it accepted before.",
           "men_total": tot, "men_lost_at_least": lost,
           "drops_by_reason": dict(by_why),
           "fields": dict(fc), "listings": listings}
    json.dump({"_note": res["_drops_note"], "men_total": tot, "men_lost_at_least": lost,
               "drops_by_reason": dict(by_why), "drops": all_drops},
              open(os.path.join(BASE, "build-reports",
                                "corpus-census-programs-drops.json"), "w"), indent=1)
    if match:
        import index_io as IO
        IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
        IDX.pop("_clubs", None)
        held = collections.Counter()
        names = collections.defaultdict(set)
        for pid, p in IDX.items():
            if not isinstance(p, dict) or not p.get("name"): continue
            n = norm(p["name"])
            if n: names[n.split()[-1]].add(n)
        for x in listings:
            for m in x["men"]:
                n = norm(m["name"]); sur = n.split()[-1] if n else ""
                cand = names.get(sur, ())
                if not cand: held["surname_absent"] += 1
                elif n in cand: held["exact_name_held"] += 1
                else: held["surname_held_only"] += 1
        print(f"\nagainst the archive's {sum(len(v) for v in names.values()):,} people:")
        for k in ("exact_name_held", "surname_held_only", "surname_absent"):
            print(f"   {k:<20} {held[k]:>4}  {held[k]/tot:>5.0%}")
        res["archive_match"] = dict(held)
    json.dump(res, open(OUT, "w"), indent=1)
    print("\n->", OUT)


if __name__ == "__main__":
    main()
