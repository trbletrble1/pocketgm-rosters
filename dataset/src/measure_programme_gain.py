"""What would the shortlist actually GAIN? Three numbers, kept apart.

MEASUREMENT ONLY. Nothing is written to any store. The extractor
(census_programs_yield.py) is NOT touched and still accepts exactly what it accepted
before -- the two-column work-around lives here, in the measurement, because whether
it belongs in the extractor is Ryan's decision after he has seen these numbers.

THE THREE NUMBERS ARE NOT ADDED TOGETHER. They answer different questions:

  A  CANDIDATES THE ARCHIVE MAY NOT HOLD -- reported as candidates with what
     separates them, never as a count of new people. A surname present among 43,000
     is not the same man, and the club-season is what makes the join worth anything.
  B  MEN HELD WHO ARE MISSING WHAT THE PAGE CARRIES -- of age, weight, college and
     position, how many does the archive lack for that man? This is the gap.
  C  PURE DUPLICATION -- held, all four already there. Worth something under the
     archive's source ranking (a contemporary document outranks a 1970s
     reconstruction) but it is NOT a gap being filled.

THE READER IS VALIDATED BEFORE IT IS BELIEVED. --selftest runs it against page seven
of the 1926 Bears/Tigers programme, whose 28 men were read by hand. A reader that
cannot find 28 there is not trusted to count anything here.

  python3 src/measure_programme_gain.py [--selftest]
"""
import os, re, sys, json, glob, statistics, collections, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from census_programs_reconstruct import AXES
from census_programs_lineup_probe import RE_NUM

SRC = os.path.join(BASE, "build-reports", "corpus-census-programs-ocr-vision")
OUT = os.path.join(BASE, "build-reports", "programme-gain.json")

# The five Ryan named: top three by volume, plus rank 15 and rank 7.
TARGETS = [
 ("1938 N.Y. GIANTS v WASHINGTON REDSKINS", [("NFL","1938","NYG"),("NFL","1938","WAS")]),
 ("1941 Brooklyn Dodgers v New York Giants", [("NFL","1941","BRO"),("NFL","1941","NYG")]),
 ("1942 NFL World Championship",             [("NFL","1942","CHI"),("NFL","1942","WAS")]),
 ("1935 NFL CHICAGO BEARS v PACIFIC",        [("NFL","1935","CHI")]),
 ("1946”RARE”MIAMI SEAHAWKS v L.A. DONS",    [("AAFC","1946","MIS"),("AAFC","1946","LAD")]),
]

# ---------------------------------------------------------------- the readers
RE_AGE  = re.compile(r"\b(\d{2})\s*years?\b", re.I)
RE_WT   = re.compile(r"\b(1[3-9]\d|2[0-9]\d)\s*(?:lbs?\.?|pounds)\b", re.I)
RE_WT_B = re.compile(r"(?<!\d)(1[4-9]\d|2[0-5]\d)(?!\d)")          # a bare weight
RE_HT   = re.compile(r"\b([5-6])\s*(?:ft\.?|feet|['’])\s*(\d{1,2})\s*(½|1/2)?\s*(?:in\.?|\")?", re.I)
RE_POSW = re.compile(r"\b(Left|Right|L\.|R\.)?\s*(End|Tackle|Guard|Center|Centre|Quarterback|"
                     r"Half\s?back|Full\s?back|Back|Halves|H\.?B\.?|F\.?B\.?|Q\.?B\.?|"
                     r"L\.?E\.?|R\.?E\.?|L\.?T\.?|R\.?T\.?|L\.?G\.?|R\.?G\.?)\b", re.I)
RE_COLW = re.compile(r"\b(Universit\w+|Univ\.?|College|State|Tech\.?|Institute|Normal|U\.)\b", re.I)
# A NAME IS NOT ANCHORED HERE. That anchoring is the extractor's second fault and the
# whole point of this measurement is to read past it.
# The delimiter is a name followed by a VITAL, not specifically by an age. Newton
# Starke's entry reads `NEWTON STARKE-Height 5 ft.` -- he is the one man on the page
# with no age printed, and keying on "NN years" loses exactly the man whose absence
# is the interesting fact. The nickname may sit anywhere in the name, not only first:
# `STUART "STEW" BEAM-25 years`.
_NAMEWORD = r"(?:[\"“'‘][A-Z][A-Za-z]+[\"”'’]|(?:Mc|Mac|O')?[A-Z][A-Za-z'’\-]+\.?)"
RE_NAME_FUSED = re.compile(
    r"(?:^|[|~]\s*)((?:" + _NAMEWORD + r"\s+){0,3}" + _NAMEWORD + r")"
    r"\s*[-—–]\s*(?:\d{2}\s*years|Height\b|[5-6]\s*ft)", re.I)
RE_NAME_PLAIN = re.compile(r"^\s*((?:[A-Z]\.\s*){0,2}(?:Mc|Mac|O')?[A-Z][A-Za-z'’\-]{2,}"
                           r"(?:\s+(?:Mc|Mac|O')?[A-Z][A-Za-z'’\-]{2,}){0,2})\s*$")
def COLLEGE_WORDS_ONLY(t):
    """Is this token a college NAME the archive already holds as one? Built from the
    archive's own college claims, so it needs no hand-typed list to go stale."""
    return norm(t) in _COLLEGES


_COLLEGES = set()


STOP = {"college","name","position","height","weight","total","score","program","official",
        "coach","coaches","tackle","guard","center","end","halfback","fullback","quarterback",
        "back","left","right","captain","team","club","the","and","field","goal","touchdown",
        "points","point","page","lineup","line","ups","probable","university","state"}


def columns_of(image):
    """Split the page into columns at its own largest gap in the ACROSS axis, then band
    each column separately. This is the two-column work-around, and it lives here."""
    lines = image.get("lines") or []
    if len(lines) < 12: return []
    f = AXES.get(image.get("orientation", "up"), AXES["up"])
    pts = [(f(l)[0], f(l)[1], l["text"]) for l in lines]
    xs = sorted(p[1] for p in pts)
    span = xs[-1] - xs[0]
    cuts = []
    if span > 0 and len(xs) >= 12:
        gaps = sorted(((b - a, (a + b) / 2.0) for a, b in zip(xs, xs[1:])), reverse=True)
        for g, mid in gaps[:3]:
            # a real column boundary: a wide empty strip with text well on both sides
            if g >= 0.10 * span and 0.15 * span < mid - xs[0] < 0.85 * span:
                if all(abs(mid - c) > 0.15 * span for c in cuts): cuts.append(mid)
    cuts.sort()
    groups = [[] for _ in range(len(cuts) + 1)]
    for p in pts:
        i = sum(1 for c in cuts if p[1] > c); groups[i].append(p)
    groups = [g for g in groups if len(g) >= 6]
    # A TWO-COLUMN PAGE IS NOT A TABLE, and confusing them is how this script first
    # reported Fordham, Arkansas and Cork-Tipped as men. A page set in two columns has
    # two independent entry lists, so EACH side carries its own jersey numbers. A table
    # has one number column and the rest are fields of the same row -- splitting it
    # turns the college column into a list of "names". Split only when both sides are
    # numbered; otherwise band the full width, exactly as the extractor does.
    if len(groups) > 1:
        numbered = sum(1 for g in groups
                       if sum(1 for _, _, t in g if RE_NUM.match(t.strip())) >= 3)
        if numbered < len(groups): return [pts]
    return groups or [pts]


def band(group):
    """Rows within one column, on the down axis. Same rule as the extractor's."""
    pts = sorted(group)
    ds = [p[0] for p in pts]
    gaps = [b - a for a, b in zip(ds, ds[1:]) if b - a > 1e-9]
    if not gaps: return [pts]
    th = 3.0 * statistics.median(gaps)
    out, cur = [], [pts[0]]
    for p in pts[1:]:
        if p[0] - cur[-1][0] > th: out.append(cur); cur = []
        cur.append(p)
    out.append(cur)
    return [sorted(b, key=lambda x: x[1]) for b in out]


def entries_from_text(text):
    """BIO SHAPE: entries delimited by `NAME-NN years`. Everything up to the next
    delimiter belongs to that man."""
    hits = list(RE_NAME_FUSED.finditer(text))
    out = []
    for i, m in enumerate(hits):
        seg = text[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(text)]
        whole = text[m.start(): hits[i + 1].start() if i + 1 < len(hits) else len(text)]
        name = re.sub(r"\s+", " ", m.group(1)).strip(" .,-")
        if not name or name.split()[-1].lower() in STOP: continue
        ht = RE_HT.search(seg); wt = RE_WT.search(seg) or RE_WT_B.search(seg)
        age = RE_AGE.search(whole)
        out.append({"name": name, "shape": "bio",
                    "age": age.group(1) if age else None,
                    "height": ht.group(0).strip() if ht else None,
                    "weight": wt.group(1) if wt else None,
                    "college": (RE_COLW.search(seg).group(0) if RE_COLW.search(seg) else None),
                    "college_text": (seg[RE_COLW.search(seg).start(): RE_COLW.search(seg).start()+60].strip()
                                     if RE_COLW.search(seg) else None),
                    "position": (RE_POSW.search(seg).group(0).strip() if RE_POSW.search(seg) else None)})
    return out


def entries_from_band(toks):
    """TABLE SHAPE: one band, one man -- a number and a name-shaped token, with the
    other fields taken from whatever else is on the row."""
    nums = [t for t in toks if RE_NUM.match(t)]
    # EACH TOKEN TO AT MOST ONE FIELD, in priority order. Without this, "Washington
    # State" is a college AND a name and every row yields a second, fictional man.
    claimed, fields = set(), {}
    def take(key, pred):
        got = []
        for i, t in enumerate(toks):
            if i in claimed or not pred(t.strip()): continue
            claimed.add(i); got.append(t.strip())
        fields[key] = got
        return got
    take("num", lambda t: RE_NUM.match(t))
    take("pos", lambda t: RE_POSW.fullmatch(t))
    take("col", lambda t: RE_COLW.search(t) or COLLEGE_WORDS_ONLY(t))
    take("ht", lambda t: RE_HT.fullmatch(t))
    take("wt", lambda t: RE_WT.fullmatch(t) or RE_WT_B.fullmatch(t))
    names = [m.group(1) for t in toks
             for m in [RE_NAME_PLAIN.match(t.strip())]
             if m and toks.index(t) not in claimed
             and m.group(1).split()[-1].lower() not in STOP
             and not RE_COLW.search(m.group(1)) and not COLLEGE_WORDS_ONLY(m.group(1))]
    if not names: return []
    row = " | ".join(toks)
    ht = RE_HT.search(row); wt = RE_WT.search(row) or RE_WT_B.search(row); age = RE_AGE.search(row)
    col = RE_COLW.search(row); pos = RE_POSW.search(row)
    return [{"name": names[0], "shape": "table",
             "number": int(nums[0]) if len(nums) == 1 else None,
             "age": age.group(1) if age else None,
             "height": ht.group(0).strip() if ht else None,
             "weight": wt.group(1) if wt else None,
             "college": col.group(0) if col else None,
             "college_text": row[col.start(): col.start()+60].strip() if col else None,
             "position": pos.group(0).strip() if pos else None}]


def read_image(image):
    out = []
    for g in columns_of(image):
        bs = band(g)
        text = " ~ ".join(t for b in bs for _, _, t in b)
        bio = entries_from_text(text)
        if bio:
            out.extend(bio); continue
        for b in bs:
            out.extend(entries_from_band([t.strip() for _, _, t in b]))
    return out


def read_listing(path):
    d = json.load(open(path))
    men = []
    for im in d["images"]: men.extend(read_image(im))
    seen, uniq = set(), []
    for m in men:
        k = norm(m["name"])
        if not k or k in seen: continue
        seen.add(k); uniq.append(m)
    return d["listing"], uniq


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def selftest():
    """The reader must find page seven's 28 men. Read by hand; the answer is known."""
    p = os.path.join(SRC, "1926-RED-GRANGE-S-record-game-CHICAGO-BEARS-v-L-A-TIGERS-"
                          "Football-Program.json")
    _, men = read_listing(p)
    KNOWN = ("nolan cole beam hufford evans shipkey baker minnick mcconnell renius cory "
             "earle lyle smith wells phythain dempsey hay blewett brien kincaid ratterman "
             "winterburn wilson starke hawkins katterman").split()
    got = {norm(m["name"]).split()[-1] for m in men}
    found = [k for k in KNOWN if k in got]
    print(f"SELFTEST 1926 page seven: reader returned {len(men)} entries; "
          f"{len(found)} of 27 known surnames present")
    print(f"   missing: {[k for k in KNOWN if k not in got]}")
    withf = collections.Counter()
    for m in men:
        for f in ("age", "height", "weight", "college", "position"): withf[f] += bool(m.get(f))
    print(f"   fields read: {dict(withf)}")
    return len(found)




# --------------------------------------------------------------- the archive side
BIRTH = ("birth_date", "pfa.birth_date", "nflverse.birth_date", "wikipedia.birth_date")


def _real(v):
    """A VALUE, not merely a key. build_person_index stringifies an absence claim to
    the literal "None", so `birth_date: ["None"]` is a man with no birth date wearing
    a birth-date predicate. Counting the key as held is how a first version of this
    measurement reported the pre-1934 record as complete. (The builder was fixed under
    ruling 8 but nothing has been rebuilt, so the index still carries them.)"""
    for x in (v if isinstance(v, list) else [v]):
        if str(x).strip().lower() not in ("none", "", "null", "unknown", "n/a"):
            return True
    return False


def holds(p, year):
    """Of the four facts a programme prints, which does the archive already hold for
    this man? `pfa.weight` and `pfa.height` are CAREER values, not season values -- a
    programme's weight is contemporary and season-specific, so 'held' here means the
    archive has something to compare, not that it has the same fact."""
    per = p.get("person") or {}
    h = {}
    h["age"] = any(k in per and _real(per[k]) for k in BIRTH)
    h["weight"] = any(k.endswith("weight") and _real(v) for k, v in per.items())
    h["college"] = any((k == "college" or k.endswith(".college") or k == "pfa.college_season")
                       and _real(v) for k, v in per.items())
    pos = False
    for k, v in (p.get("seasons") or {}).items():
        if k.split("|")[1] == year and ((v.get("stint") or {}).get("position")): pos = True
    for row in (p.get("person_season") or []):
        if len(row) >= 3 and str(row[0]) == year and row[1] == "position": pos = True
    if "pfa.position_career" in per: pos = True
    h["position"] = pos
    return h


def build_cohort(IDX, keys):
    """Everyone the archive holds on any of this game's club-seasons."""
    want = {f"{lg}|{yr}|{cl}" for lg, yr, cl in keys}
    coh = {}
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        for k in (p.get("seasons") or {}):
            if any(k.startswith(w) for w in want):
                coh[pid] = p; break
    return coh


def measure(IDX, listing_file, keys):
    listing, men = read_listing(listing_file)
    year = keys[0][1]
    coh = build_cohort(IDX, keys)
    by_sur = collections.defaultdict(list)
    for pid, p in coh.items():
        n = norm(p.get("name") or "")
        if n: by_sur[n.split()[-1]].append((pid, p.get("name")))

    A, B, C, AMB = [], [], [], []
    for m in men:
        n = norm(m["name"])
        if not n: continue
        sur = n.split()[-1]
        cand = by_sur.get(sur, [])
        page_has = {f: bool(m.get(f)) for f in ("age", "weight", "college", "position")}
        if not any(page_has.values()) and not m.get("height"):
            continue                          # a bare name with nothing on it; not a man's row
        if not cand:
            A.append({"name_as_printed": m["name"], "surname": sur,
                      "page_carries": [f for f, v in page_has.items() if v],
                      "height": m.get("height"),
                      "what_separates_them": "no person on any of this game's club-seasons "
                                             "carries this surname",
                      "IS_A_CANDIDATE_NOT_A_PERSON": True})
            continue
        if len(cand) > 1:
            AMB.append({"name_as_printed": m["name"], "surname": sur,
                        "held_candidates": [c[1] for c in cand],
                        "what_would_separate_them": "the page's jersey number, or a forename "
                            "the archive also holds; surname alone does not"})
            continue
        pid, nm = cand[0]
        h = holds(coh[pid], year)
        missing = [f for f in ("age", "weight", "college", "position") if page_has[f] and not h[f]]
        rec = {"name_as_printed": m["name"], "person": pid, "held_as": nm,
               "page_carries": [f for f, v in page_has.items() if v],
               "archive_holds": [f for f, v in h.items() if v],
               "archive_lacks_that_the_page_carries": missing}
        (B if missing else C).append(rec)
    return {"listing": listing, "club_seasons": [f"{a}|{b}|{c}" for a, b, c in keys],
            "cohort_held": len(coh), "men_read": len(men),
            "A_candidates_not_held": A, "ambiguous_on_surname": AMB,
            "B_held_but_missing": B, "C_pure_duplication": C,
            "counts": {"read": len(men), "A": len(A), "ambiguous": len(AMB),
                       "B": len(B), "C": len(C),
                       "B_field_gaps": dict(collections.Counter(
                           f for r in B for f in r["archive_lacks_that_the_page_carries"]))}}


def main():
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    IDX.pop("_clubs", None)
    for p in IDX.values():
        if not isinstance(p, dict): continue
        for v in ((p.get("person") or {}).get("college") or []):
            n = norm(v)
            if n: _COLLEGES.add(n)
    if len(_COLLEGES) < 200:
        raise SystemExit(f"REFUSING TO MEASURE: only {len(_COLLEGES)} college names were "
                         "read from the archive, so the test that stops a college being "
                         "counted as a man would barely fire.")
    print(f"college names read from the archive: {len(_COLLEGES):,}")
    files = {os.path.basename(f): f for f in glob.glob(os.path.join(SRC, "*.json"))}
    out = []
    for frag, keys in TARGETS:
        hit = None
        for name, path in files.items():
            if norm(frag)[:26] in norm(json.load(open(path))["listing"]): hit = path; break
        if not hit:
            out.append({"listing": frag, "ERROR": "no census file matched"}); continue
        out.append(measure(IDX, hit, keys))
    res = {"_note": "MEASUREMENT ONLY. No store written. The extractor is unchanged; the "
                    "two-column work-around lives in this script.",
           "_the_three_are_not_added": "A is candidates, not new people. B is the gap. "
                    "C is corroboration, not a gap.",
           "listings": out}
    json.dump(res, open(OUT, "w"), indent=1)
    for r in out:
        if "ERROR" in r: print(f"!! {r['listing']}: {r['ERROR']}"); continue
        c = r["counts"]
        print(f"\n{r['listing'][:70]}")
        print(f"   cohort held {r['cohort_held']:>3} | read {c['read']:>3} | "
              f"A(candidates) {c['A']:>3} | ambiguous {c['ambiguous']:>2} | "
              f"B(gap) {c['B']:>3} | C(dup) {c['C']:>3}")
        if c["B_field_gaps"]: print(f"   B gaps by field: {c['B_field_gaps']}")
    print("\n->", OUT)
    return res


if __name__ == "__main__":
    if "--selftest" in sys.argv: selftest(); raise SystemExit
    if selftest() < 25:
        raise SystemExit("REFUSING TO MEASURE: the reader cannot find the page it was "
                         "validated against; its counts would mean nothing.")
    main()
