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


def men_of(image):
    bs = bands(image)
    if not bs: return []
    numbered = [b for b in bs if sum(1 for _, _, t in b if RE_NUM.match(t)) >= 1]
    if len(numbered) < 6: return []
    out = []
    for b in numbered:
        toks = [t.strip() for _, _, t in b]
        nums = [t for t in toks if RE_NUM.match(t)]
        if len(nums) != 1: continue                  # pairs are not forced -- see docstring
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
        if not names: continue
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
    listings = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SRC, f)))
        men, pages = [], 0
        for im in d["images"]:
            m = men_of(im)
            if m: pages += 1; men.extend(m)
        # one listing photographs the same page more than once; dedupe on number+name
        seen, uniq = set(), []
        for m in men:
            k = (m["number"], norm(m["name"]))
            if k in seen: continue
            seen.add(k); uniq.append(m)
        if uniq:
            listings.append({"listing": d["listing"], "pages": pages, "men": uniq})

    tot = sum(len(x["men"]) for x in listings)
    fc = collections.Counter()
    for x in listings:
        for m in x["men"]:
            for k in ("position", "college", "height", "weight"): fc[k] += k in m
            fc["full_name"] += m["full_name"]
    print(f"listings yielding men: {len(listings)}   men on forced rows: {tot}")
    print("\nfields carried, of those men:")
    for k in ("full_name", "position", "college", "height", "weight"):
        print(f"   {k:<10} {fc[k]:>4}  {fc[k]/tot:>5.0%}")
    print("\nmen per listing, biggest first:")
    for x in sorted(listings, key=lambda x: -len(x["men"]))[:14]:
        wc = sum(1 for m in x["men"] if "college" in m)
        print(f"   {len(x['men']):>3} men ({wc:>2} with college)   {x['listing'][:58]}")

    res = {"_note": "men on rows forced by geometry; two-number rows excluded as unforced",
           "men_total": tot, "fields": dict(fc), "listings": listings}
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
