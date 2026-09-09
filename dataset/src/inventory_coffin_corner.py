"""An INVENTORY of the Coffin Corner run. Not an ingest. Nothing is claimed.

For each article: volume, issue, year, title, author, what kind of thing it is, how
much of it is tabular, and which of the archive's EMPTY club-seasons it names.

WHAT IS READ AND WHAT IS DERIVED. Volume, issue, year, title and author are READ off
the page -- every article opens `THE COFFIN CORNER: Vol. N, No. M (YEAR)` followed by
a centred title and a `By ...` line. The KIND is DERIVED, by the rules below, and is
a label on a guess: it is there to sort 1,079 articles into piles worth looking at,
not to be quoted as a fact about any one of them.

  python3 src/inventory_coffin_corner.py
"""
import os, re, sys, json, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
SRC = os.path.expanduser("~/Documents/pgm3-sources/pfra")
DEST = os.path.join(SRC, "coffin_corner")
OUT = os.path.join(BASE, "build-reports", "coffin-corner-inventory.json")

# `Vol. 2, No. 6 (1980)` and `Vol. 2, Annual (1980)` are both headers; the Annual
# issues print no "No.". Some articles print no header line at all, and for those the
# FILENAME carries the same three facts -- <vol>-<issue>-<article>.pdf.
HEAD = re.compile(r"THE COFFIN CORNER:\s*Vol\.\s*([0-9IVXL]+),?\s*(?:No\.\s*)?([A-Za-z0-9]+)\s*(?:\((\d{4})\))?", re.I)
FROM_NAME = re.compile(r"^(\d{2})-([A-Za-z0-9]{2})-(\d+)[a-z]?\.pdf$", re.I)
# A BYLINE, not a source note: "Reprinted from The Packer Report" and "(Ed. note: ...)"
# sit BEFORE the title on some articles, and treating them as bylines swallowed it.
BY = re.compile(r"^\s*(?:By|Compiled by|Edited by|Submitted by|Researched by|As told to)\s+(.{2,70})$", re.I)
SOURCE_NOTE = re.compile(r"^\s*(?:\(|\[|Reprinted|From the|Ed\.? note|---)", re.I)

KIND_RULES = [
    ("league register / all-time record",
     r"\b(ALL-TIME|ALL TIME|REGISTER|ROSTERS?|RECORDS?|STANDINGS?|DIRECTORY|ENCYCLOPEDIA|WHO'S WHO|CHECKLIST)\b"),
    ("statistical study",
     r"\b(STATISTIC|LEADERS?|RATING|RANKING|NUMBERS|ANALYSIS|BY THE NUMBERS|SCORING|YARDAGE|AVERAGES?)\b"),
    ("draft / transactions", r"\b(DRAFT|TRADES?|TRANSACTIONS?|SIGNING)\b"),
    ("game account", r"\b(GAME|BOWL|CHAMPIONSHIP|PLAYOFF|VS\.?|DEFEAT|UPSET|CLASSIC)\b"),
    ("league history", r"\b(LEAGUE|A\.?F\.?L\.?|A\.?A\.?F\.?C\.?|N\.?F\.?L\.?|CONFERENCE|ASSOCIATION|W\.?F\.?L\.?|CIRCUIT)\b"),
    ("club history", r"\b(TEAM|CLUB|ELEVEN|GRIDDERS|FRANCHISE)\b"),
]
PERSONISH = re.compile(r"^[A-Z][A-Za-z'.\-]+(?: [A-Z][A-Za-z'.\-]+){1,2}$")
# Ordinary English words that are ALSO surnames the archive holds. Without this, "A
# CLOSER LOOK" is a biography of a man named Look and "THE STORY OF..." one of a man
# named Story. The archive holds 43,562 people; a surname vocabulary that large will
# match ordinary prose unless the ordinary words are taken out of it first.
COMMON = {"LOOK","STORY","DAY","CASE","LAST","FIRST","BIG","LONG","GAME","YEAR","YEARS",
          "TIME","TIMES","BEST","WORST","GREAT","LITTLE","OLD","NEW","MAN","MEN","BOY",
          "KING","PRICE","YOUNG","BROWN","WHITE","BLACK","GREEN","HILL","FIELD","PARK",
          "WOOD","STONE","POST","MARCH","MAY","BALL","BOWL","PASS","RUSH","LINE","BACK",
          "END","GUARD","CENTER","COACH","CHAMPION","CHAMPIONS","RECORD","RECORDS",
          "MYTH","WAY","WAR","HOME","ROAD","LIFE","DEATH","FALL","RISE","WIN","LOSS",
          "TITLE","CROWN","DYNASTY","LEGEND","LEGENDS","STAR","STARS","IRON","STEEL"}


def text_of(path, pages=2):
    try:
        return subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", str(pages), path, "-"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def full_text(path):
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""


def head_from_name(name):
    m = FROM_NAME.match(name)
    if not m: return None, None, None
    v = m.group(1)
    return v, m.group(2), (1978 + int(v) if v.isdigit() else None)


def parse_head(t):
    m = HEAD.search(t)
    if not m: return None, None, None
    # Not every issue prints the year in its running head; volume 1 is 1979 and the run
    # is annual, so the year is derived from the volume where the page does not print it.
    y = int(m.group(3)) if m.group(3) else (1978 + int(m.group(1)) if m.group(1).isdigit() else None)
    return m.group(1), m.group(2), y


def parse_title_author(t):
    """Choose the title by SHAPE, not by position. Several articles print an epigraph or
    an editor's note above the title, so `the first line after the header` is wrong for
    them; a title is short and predominantly upper-case, and that holds throughout."""
    lines = [l.rstrip() for l in t.split("\n")]
    i = next((k for k, l in enumerate(lines) if HEAD.search(l)), None)
    if i is None:
        i = -1
    window = [l.strip() for l in lines[i + 1:i + 12] if l.strip()]
    author = None
    for l in window:
        m = BY.match(l)
        if m:
            author = m.group(1).strip().rstrip("."); break

    def upper_share(x):
        a = [c for c in x if c.isalpha()]
        return sum(c.isupper() for c in a) / len(a) if a else 0.0

    title = []
    for l in window:
        if BY.match(l) or SOURCE_NOTE.match(l):
            if title: break
            continue
        if not (3 <= len(l) <= 95):
            if title: break
            continue
        # A multi-line editor's note only has its FIRST line matched by SOURCE_NOTE; its
        # continuation lines look like titles. A title does not end in a full stop or a
        # closing bracket, and that separates them.
        if l.endswith((".", ")", "]", ",")) and upper_share(l) < 0.6:
            if title: break
            continue
        if upper_share(l) > 0.6 or not title:
            title.append(l)
            if len(title) >= 2 and upper_share(l) <= 0.6: break
        else:
            break
        if len(title) >= 3: break
    return (" -- ".join(title).strip() or None), author


def tabular_share(txt):
    """How much of the article reads as a table: lines with >=3 runs of 2+ spaces, or
    a high density of short numeric tokens. A rough measure, and labelled as one."""
    lines = [l for l in txt.split("\n") if l.strip()]
    if not lines: return 0.0
    n = 0
    for l in lines:
        if len(re.findall(r"\s{2,}", l)) >= 3: n += 1
        elif len(re.findall(r"\b\d{1,4}\b", l)) >= 5: n += 1
    return round(n / len(lines), 3)


CLUB_VOCAB = None
PERSON_VOCAB = None


def _vocabs():
    """Club names and person surnames the ARCHIVE holds. Classifying a 1,079-article run
    from a keyword list is guesswork; using the archive's own vocabulary at least makes
    the guess answer to something."""
    global CLUB_VOCAB, PERSON_VOCAB
    if CLUB_VOCAB is not None: return CLUB_VOCAB, PERSON_VOCAB
    import sqlite3
    sys.path.insert(0, os.path.join(BASE, "service")); sys.path.insert(0, os.path.join(BASE, "src"))
    import paths, clubs as ac
    C = ac.Clubs()
    CLUB_VOCAB = set()
    for c in C.T["clubs"]:
        for n in c.get("names", []):
            for tok in n["name"].replace("/", " ").split():
                if len(tok) > 4: CLUB_VOCAB.add(tok.upper())
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    PERSON_VOCAB = {r[0].split()[-1].upper() for r in
                    conn.execute("select name from person_name where name is not null")
                    if r[0] and len(r[0].split()[-1]) > 3}
    return CLUB_VOCAB, PERSON_VOCAB


def kind_of(title, txt, tab):
    T = (title or "").upper()
    clubs_v, people_v = _vocabs()
    head = re.split(r"[:,\-]", T)[0].strip()
    head = re.sub(r"^(THE|A|AN)\s+", "", head)
    # str.strip(chars) strips from BOTH ends: "STRONG".strip(".'S") is "TRONG", and Ken
    # Strong stopped being a biography. Trim only trailing punctuation and a possessive.
    def _t(w): return re.sub(r"(?:['\u2019]S|[.,;:!?'\u2019\"])+$", "", w)
    toks = [_t(w) for w in head.split() if _t(w) and _t(w) not in COMMON]
    for name, pat in KIND_RULES:
        if re.search(pat, T):
            if name == "league register / all-time record":
                return name if tab > 0.15 else name + " (prose)"
            return name
    # a title whose FIRST clause names a club the archive holds is a club history
    if any(t in clubs_v for t in toks):
        return "club history"
    # a title whose first clause is a person's name -- surname the archive holds, or a
    # two-word capitalised phrase -- is a biography
    if 1 <= len(toks) <= 3 and toks and toks[-1] in people_v:
        return "biography"
    if tab > 0.40: return "statistical study"
    if tab > 0.20: return "part-tabular study"
    return "narrative -- unclassified"


def main():
    man = json.load(open(os.path.join(DEST, "manifest.json")))
    empty = json.load(open(os.path.join(SRC, "empty-club-seasons.json")))
    # the names to look for, and the leagues Ryan named explicitly
    club_names = {}
    for e in empty:
        for form in {e["name"], e["name"].split("/")[0]}:
            club_names.setdefault(form.strip(), []).append(e)
    FLAGS = {"Bethlehem": "Bethlehem", "Paterson": "Paterson", "Wilkes-Barre": "Wilkes-Barre",
             "Wilkes Barre": "Wilkes-Barre", "1926 AFL": "the 1926 AFL",
             "Eastern League": "the Eastern League", "Eastern Football": "the Eastern League",
             "second AFL": "the second AFL", "third AFL": "the third AFL"}
    rows = []
    for name in sorted(man["files"]):
        p = os.path.join(DEST, name)
        if not os.path.exists(p): continue
        head = text_of(p, 2)
        vol, iss, yr = parse_head(head)
        if not vol:
            vol, iss, yr = head_from_name(name)   # the filename carries the same three facts
        title, author = parse_title_author(head)
        txt = full_text(p)
        tab = tabular_share(txt)
        pages = txt.count("\f") + 1
        # A CLUB NAME SOMEWHERE AND A YEAR SOMEWHERE IS NOT A MATCH. A 3,000-word article
        # will contain "Paterson" in one paragraph and "1932" in another and mean nothing
        # by it. The club name and the year must appear within 200 characters of each
        # other, and the distance is recorded so a reader can judge rather than trust.
        hits = []
        up = txt.upper()
        for cn, es in club_names.items():
            if len(cn) < 6: continue
            at = [m.start() for m in re.finditer(re.escape(cn.upper()), up)]
            if not at: continue
            for e in es:
                # NOT `yr` -- that is the ARTICLE's year, four lines up, and reusing the
                # name here silently rewrote it to whichever club-season matched last.
                ey = str(e["year"])
                ys = [m.start() for m in re.finditer(r"\b" + ey + r"\b", txt)]
                if not ys: continue
                gap = min(abs(a - y) for a in at for y in ys)
                if gap <= 200:
                    hits.append({"club": e["name"], "year": e["year"], "league": e["league"],
                                 "club_id": e["club_id"], "chars_apart": gap,
                                 "in_title": cn.upper() in (title or "").upper()})
        hits.sort(key=lambda h: h["chars_apart"])
        # The names Ryan called out by hand. A hit in the TITLE is worth flagging on its
        # own; a hit in the body is worth knowing and is weaker, so they are kept apart.
        tl = (title or "").lower(); bl = txt.lower()
        flag_title = sorted({v for k, v in FLAGS.items() if k.lower() in tl})
        flag_body = sorted({v for k, v in FLAGS.items() if k.lower() in bl}) 
        flags = flag_title
        rows.append({"file": name, "volume": vol, "issue": iss, "year": yr,
                     "title": title, "author": author,
                     "kind": kind_of(title, txt, tab),
                     "tabular_share": tab, "pages": pages,
                     "words": len(txt.split()),
                     "empty_club_seasons_named": hits[:40],
                     "empty_club_season_in_the_title": sorted({h["club"] for h in hits if h["in_title"]}),
                     "n_empty_club_seasons_named": len({(h["club"], h["year"]) for h in hits}),
                     "flagged_in_title": flag_title,
                     "flagged_in_body": flag_body})
        if len(rows) % 100 == 0: print(f"  read {len(rows)}", flush=True)
    json.dump({"_what": "Inventory of the PFRA Coffin Corner run. NOT an ingest; no claim "
                        "is written from any of it.",
               "_rights": "A PFRA publication, not public domain. Facts would be cited to the "
                          "page under the reference-works ruling.",
               "_kind_is_derived": "volume, issue, year, title and author are read off the "
                                   "page; KIND is a derived label to sort the run into piles "
                                   "and is not a fact about any one article.",
               "articles": rows}, open(OUT, "w"), indent=1)
    print(f"\nwrote {OUT}  ({len(rows)} articles)")
    return rows


if __name__ == "__main__":
    main()
