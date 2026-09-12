"""Neft, Cohen & Deutsch, *Pro Football: The Early Years* (1978) -- PASS 1, the 1920s. Ryan's rulings of 2026-09-12.

WHAT IS TAKEN, AND ONLY THIS:
  * the heights and weights the 1920-29 yearly rosters print (season figures, on the stint);
  * the colleges the 1920-32 register prints, for men this pass joins on a 1920s club-season;
  * the men those rosters name whom the archive does not place on that club-season -- above all the
    mid-season moves, which Neft prints inline ("Oscar Knop (from & to ChiT)") and the archive holds
    almost nothing of.
  Ages are not taken (not in the ruling, and in the six-page sample they added nothing).

READ TWICE, CLAIMED WHERE THE READINGS AGREE. Every line was read from the page image by two readers
working apart (build/neft-readings-1920s/A and /B). A fact is claimed only where both read the same value
for it; where they differ the line is listed, never resolved. A reading error in an ingest becomes a claim.

THE JOIN is ruling One of 2026-09-11, taken from ingest_football_hunting.join -- one implementation, not
a copy: an exact name held once on the club-season, or a surname unique on it. A man it does not find
there is placed only by one of two stated routes, each written on the claim:
  * NAMED IN THE PRINTED MOVE: his line prints a move naming another club (to KEN, from HAM), and his
    exact full name is held once on THAT club's same season. The club comes from the book's own words.
  * THE CLUB'S ADJACENT SEASON: ruling One extended (Ryan, 2026-09-11) -- the surname unique on the same
    club's season before or after, a second man of it on either roster refusing both.
  Anyone else is a LEAD, not a person. Nothing is promoted here.

HELD OUT, by ruling: the men whose records are merge questions (the Lyons, LeJeune and Jean, the Spagnas,
and the same shape the Neft report listed). No claim of this pass lands on them; they are listed.

THE MOVE PREDICATE IS PROPOSED, NOT NAMED. Ryan names it. Until then the move rides verbatim inside
neft.roster_as_printed, so nothing the page says is lost and no name is presumed.

A reference work, consulted and cited under the reference-works ruling: every claim names the printed page.
The scan's text layer is read by nothing here.

  python3 src/ingest_neft_1920s.py [--write]
"""
import os, re, sys, json, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import index_io as IO
import ingest_football_hunting as H          # the join, ruling One -- one implementation
from clubs import Clubs, norm as club_norm
from readings import READERS

STORE = "neft-early-years-1978-1920s"
OUT = os.path.join(BASE, "build", STORE + ".json")
REPORT = os.path.join(BASE, "build-reports", STORE + ".json")
READINGS = os.path.join(BASE, "build", "neft-readings-1920s")
SOURCE_ID = "neft-early-years-1978"
BOOK = {"source_id": SOURCE_ID,
        "title": "Pro Football: The Early Years (An Encyclopedic History, 1895-1959)",
        "stated_by": "David S. Neft, Richard M. Cohen, Jordan A. Deutsch",
        "publisher": "Sports Products Inc., Ridgefield, Connecticut, 1978. ISBN 0-932070-01-9",
        "acquisition": "held: the Internet Archive scan in Football Archive/docs",
        "rights": "(c) 1978. A reference work, consulted and cited under the reference-works ruling: facts cited "
                  "to the printed page, never parsed wholesale. The text layer is not read.",
        "transcription": "two readers per page, working apart, from the page image; claimed only where they agree"}

# PDF pages read. PDF page = printed page + 2. 46 and 53 are standings pages, read to confirm they hold no roster.
ROSTER_PAGES = [18, 19, 20, 22, 23, 24, 26, 27, 28, 30, 31, 32, 34, 35, 36, 38, 39, 40, 41,
                43, 44, 45, 46, 48, 49, 51, 52, 53, 55, 56]
REGISTER_PAGES = list(range(67, 77))
REGISTER_DIRS = {}             # pdf -> reading folder, for a register page read in ANOTHER pass (pass 2 borrows 67-76)
YEARS = range(1920, 1930)
# The season of each roster page, from the section it sits in: each season's essay opens it (PDF 17, 21, 25, 29,
# 33, 37, 42, 47, 50/54). Taken from the layout, not from a running head -- PDF 26 prints none.
SEASON_OF_PAGE = {**{p: 1920 for p in (18, 19, 20)}, **{p: 1921 for p in (22, 23, 24)},
                  **{p: 1922 for p in (26, 27, 28)}, **{p: 1923 for p in (30, 31, 32)},
                  **{p: 1924 for p in (34, 35, 36)}, **{p: 1925 for p in (38, 39, 40, 41)},
                  **{p: 1926 for p in (43, 44, 45, 46)}, **{p: 1927 for p in (48, 49)},
                  **{p: 1928 for p in (51, 52, 53)}, **{p: 1929 for p in (55, 56)}}
def LEAGUE(y): return "APFA" if y <= 1921 else "NFL"


def configure(**kw):
    """Point this ingest at another pass (src/ingest_neft_1930s.py). ONE IMPLEMENTATION: only the pages, the reading
    folders, the seasons and the store change; the reading, the join and the refusals are the same code."""
    g = globals()
    for k, v in kw.items():
        if k not in g: raise SystemExit(f"configure: no setting called {k}")
        g[k] = v
    g["OUT"] = os.path.join(BASE, "build", g["STORE"] + ".json")
    g["REPORT"] = os.path.join(BASE, "build-reports", g["STORE"] + ".json")


# THE BASE STATE LEAVES OUT EVERY NEFT PASS, not only this one: pass 2's adjacent-season route looks at 1929, and pass
# 1's 1929 claims must not place pass 2's 1930 men -- a decider that reads its own output.
NEFT_STORES = "neft-early-years-1978%"

# Neft's team codes, as printed on his Codes page (printed p. 9, PDF 11), read by eye. Codes name a CITY
# ("Det -- Detroit"), so a code resolves to the one archive club of that city in the league that season,
# or to nothing.
CODES = {"akr": ["Akron"], "bkn": ["Brooklyn"], "bos": ["Boston"], "buf": ["Buffalo"], "can": ["Canton"],
         "chib": ["Chicago Bears", "Chicago Staleys"], "chic": ["Chicago Cardinals"], "chicc": ["Chicago Cardinals"],
         "chit": ["Chicago Tigers"], "cin": ["Cincinnati"], "cle": ["Cleveland"], "col": ["Columbus"],
         "day": ["Dayton"], "dec": ["Decatur"], "det": ["Detroit"], "dul": ["Duluth"], "eva": ["Evansville"],
         "fra": ["Frankford"], "gb": ["Green Bay"], "ham": ["Hammond"], "har": ["Hartford"], "kc": ["Kansas City"],
         "ken": ["Kenosha"], "la": ["Los Angeles"], "lou": ["Louisville"], "mil": ["Milwaukee"],
         "min": ["Minneapolis", "Minnesota"], "mun": ["Muncie"], "nwk": ["Newark"], "nyg": ["New York Giants"],
         "nyy": ["New York Yankees"], "oor": ["Oorang"], "ora": ["Orange"], "port": ["Portsmouth"],
         "pott": ["Pottsville"], "prov": ["Providence"], "rac": ["Racine"], "ri": ["Rock Island"],
         "roch": ["Rochester"], "si": ["Staten Island"], "stl": ["St. Louis"], "tol": ["Toledo"],
         "was": ["Washington"], "phi": ["Philadelphia"], "pit": ["Pittsburgh"]}
# Pit and Phi are on the same Codes page and enter the book in 1933.
# `Tol` is not on the Codes page but the 1922-23 rosters print "Toledo Maroons" and the register "22-23Tol".

# HELD OUT: merge questions, left for their own look (Ryan, 2026-09-12). The first six are the ruling's own
# examples; the rest are the same shape, listed in reports/2026-09-12-neft-against-the-hunting-list.md.
HOLD_OUT = {"P_045336": "Walt LeJeune -- beside Walt Jean", "P_014834": "Walt Jean -- beside Walt LeJeune",
            "P_002555": "Butch Spagna -- beside Joe Spagna", "P_045330": "Joe Spagna -- beside Butch Spagna",
            "P_015972": "Babe Lyon -- beside George Lyon (1934 St. Louis)", "P_047098": "George Lyon -- beside Babe Lyon",
            "P_002623": "Dick Egan -- two records, 1924 Kenosha and Dayton", "P_015218": "Dick Egan -- the second record",
            "P_002620": "Bill Clark -- two 1920 records", "P_002685": "Bill Clark -- the second 1920 record",
            "P_002834": "Babe Clark -- the register gives Hal Clark the nickname Babe",
            "P_045352": "Walter Mahanq -- a record with no facts beside Walter Mahan", "P_015589": "Walter Mahan -- beside Walter Mahanq"}

LINEAGE = ("Ryan, 2026-09-12: 'Two compilers differing by a few pounds, and Neft is the ancestor of one of them.' "
           "The archive's other pre-1933 roster figures come in part from compilations that descend from this "
           "book, so where this claim agrees with another source that is partly the same compilation and not "
           "corroboration; where it differs, both are held and neither is chased. Which of the archive's sources "
           "descends from it is not established claim by claim.")
READ_BY = {"readers": ["A", "B"], "method": "two readers, working apart, each from the page image a line at a time; "
                                             "the fact is claimed because both read the same value"}

PREDICATE_DEFINITIONS = {
    "neft.roster_as_printed": {
        "definition": "named on this club-season's roster in Neft's yearly section, with the position and any move "
                      "or note exactly as printed. It places the man on the club-season.",
        "the_move_inside_it": "move_as_printed is the source's words, e.g. 'from & to ChiT'. The ORDER of a man's "
                              "stints is not inferred from it, and a move printed differently on two clubs is "
                              "held twice, as printed."},
    "neft.roster.height": {
        "definition": "the height Neft's yearly roster prints for this man in this season.",
        "not_folded": "a season figure, like pfa.roster.height; not the career pfa.height. In no family, so a "
                      "difference from another source shows on the claim and in the report but not in the "
                      "contested table -- family membership is Ryan's call."},
    "neft.roster.weight": {
        "definition": "the weight Neft's yearly roster prints for this man in this season.",
        "not_the_register": "the register's weight is a career average by Neft's own definition and is NOT "
                            "taken. In no family, as neft.roster.height."},
    "neft.college_as_printed": {
        "definition": "the college the 1920-32 register prints, exactly as printed; each college in a list is its own claim.",
        "why_not_in_the_college_family": "Filed first as `college`, and the model then recorded 392 new college "
            "contests, many of them ONE SCHOOL IN TWO NOTATIONS: 'Washington & Jeff.' against 'Washington & Jefferson' "
            "(16), 'Miami-Ohio' against 'Miami (OH)' (13), 'Georgetown' against 'Georgetown (DC)' (13), 'N.Y.U.' against "
            "'NYU' (8). The declared college reading does not fold Neft's abbreviations, so in the family they are "
            "fabricated disagreements -- the same fabrication as 61\" against 6-1. Held as printed, outside the family, "
            "until Ryan rules a reading for Neft's forms (2026-09-12).",
        "none_is_not_claimed": "a printed 'none' is counted, not claimed: 'none' is not a school."},
}
PREDICATE_DEFINITIONS["neft.move_as_printed"] = {
    "definition": "the move this book prints beside a man on this club-season -- 'from HAM', 'to KEN', 'from & to "
                  "ChiT' -- held exactly as printed.",
    "asserts_nothing_about": "the order or date of the moves, or the other club: the club the words name has its own "
                             "roster line, which is its own claim. 'As printed' is the whole promise.",
    "refuses": ["an order or date", "a stint on the other club", "a transaction (no date, no mechanism is printed)",
                "reconciling a move printed differently on two clubs -- each is held as printed"],
    "ruled_by": "Ryan, 2026-09-12: 'the predicate is neft.move_as_printed'."}
PROPOSED_MOVE_PREDICATE = {
    "status": "RULED 2026-09-12 as neft.move_as_printed (see predicate_definitions); the proposal is kept as written.",
    "asserts": "this book prints this man on this club-season with this move text -- 'from HAM', 'to KEN', "
               "'from & to ChiT' -- in the source's words, and the clubs those words name.",
    "refuses": ["an ORDER or DATE of the moves: 'from & to ChiT' says he came from and went back to the Tigers, "
                "not when, and nothing is inferred beyond the words",
                "a stint on the OTHER club: the club the move names has its own roster line, which is its own claim",
                "a transaction: no date, no mechanism (trade, release, loan) is printed",
                "reconciling a move printed differently on two clubs: Frank Rydzewski's 1920 move reads three "
                "ways on three rosters and is held three times, as printed"],
    "until_named": "the move rides verbatim inside neft.roster_as_printed.move_as_printed, so nothing is lost",
}


# ---------------------------------------------------------------- the two readings
def required(path):
    if not os.path.exists(path):
        raise SystemExit(f"MISSING INPUT: {path}. The two readings live in {READINGS}/A and /B, one JSON per page; "
                         "they are moved there from the readers' working folders, never read from a scratchpad.")
    return json.load(open(path))


def t(s):
    """A reading's typography, not its content: quote marks, '&amp;', spacing."""
    if s is None: return None
    s = str(s).replace("&amp;", "&").replace("’", "'").replace("‘", "'").replace("”", '"') \
              .replace("“", '"').replace("''", '"')
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def tmove(s):
    s = t(s)
    if s and s.startswith("(") and s.endswith(")"): s = s[1:-1].strip()
    return s or None


def club_key(s): return re.sub(r"[^a-z ]", "", (t(s) or "").lower()).strip()


FIELDS = ("pos", "hgt", "wgt", "move_as_printed", "note_as_printed", "mark_as_printed", "surname_only")


def unsure(m):
    return {u.get("field") for u in (m.get("uncertain") or []) if isinstance(u, dict)} | \
           {u for u in (m.get("uncertain") or []) if isinstance(u, str)}


def fieldval(m, f):
    v = m.get(f)
    # A move or note is printed in parentheses; one reader keeping them and the other not is typography, not a
    # disagreement (found on the first dry run: John Thomas's "(played as John Webster)").
    if f in ("move_as_printed", "note_as_printed"): return tmove(v)
    if f == "surname_only": return bool(v)
    return t(v)


def agree_roster(pdf):
    """-> (agreed lines, disagreements). A line is a man both readers put on the same club block under the same
    printed name; each of its fields is agreed or not on its own."""
    a, b = required(os.path.join(READINGS, "A", f"p{pdf}.json")), required(os.path.join(READINGS, "B", f"p{pdf}.json"))
    dis, lines = [], []
    if bool(a.get("has_rosters")) != bool(b.get("has_rosters")):
        dis.append({"pdf": pdf, "what": "whether the page holds rosters", "A": a.get("has_rosters"), "B": b.get("has_rosters")})
        return lines, dis
    ca = {club_key(c["club_as_printed"]): c for c in a.get("clubs", [])}
    cb = {club_key(c["club_as_printed"]): c for c in b.get("clubs", [])}
    for k in sorted(set(ca) ^ set(cb)):
        c = ca.get(k) or cb.get(k)
        dis.append({"pdf": pdf, "what": "a club block one reader has and the other does not (or names differently)",
                    "club_as_printed": c["club_as_printed"], "reader": "A" if k in ca else "B", "men": len(c["men"])})
    for k in sorted(set(ca) & set(cb)):
        A, B = ca[k], cb[k]
        def keyed(c):
            seen = collections.Counter(); out = {}
            for m in c["men"]:
                nk = (t(m["name_as_printed"]) or "").lower(); seen[nk] += 1
                out[(nk, seen[nk])] = m
            return out
        ma, mb = keyed(A), keyed(B)
        for key in sorted(set(ma) ^ set(mb)):
            m = ma.get(key) or mb.get(key)
            dis.append({"pdf": pdf, "club_as_printed": A["club_as_printed"], "what": "a name one reader read and the other did not",
                        "reader": "A" if key in ma else "B", "name_as_printed": m["name_as_printed"],
                        "column": m.get("column"), "n": m.get("n")})
        for key in sorted(set(ma) & set(mb)):
            x, y = ma[key], mb[key]
            if "name" in unsure(x) | unsure(y) or "name_as_printed" in unsure(x) | unsure(y):
                dis.append({"pdf": pdf, "club_as_printed": A["club_as_printed"], "what": "a name a reader marked uncertain",
                            "name_as_printed": x["name_as_printed"]}); continue
            agreed = {}
            for f in FIELDS:
                if f in unsure(x) | unsure(y):
                    dis.append({"pdf": pdf, "club_as_printed": A["club_as_printed"], "name_as_printed": x["name_as_printed"],
                                "what": f"{f} marked uncertain", "A": x.get(f), "B": y.get(f)}); continue
                if fieldval(x, f) == fieldval(y, f): agreed[f] = fieldval(x, f)
                else:
                    dis.append({"pdf": pdf, "club_as_printed": A["club_as_printed"], "name_as_printed": x["name_as_printed"],
                                "what": f"{f} read differently", "A": x.get(f), "B": y.get(f)})
            lines.append({"pdf": pdf, "club_as_printed": t(A["club_as_printed"]), "name_as_printed": t(x["name_as_printed"]),
                          "fields": agreed, "disagreed": sorted(set(FIELDS) - set(agreed))})
    return lines, dis


def agree_register(pdf):
    d = REGISTER_DIRS.get(pdf, READINGS)
    a, b = required(os.path.join(d, "A", f"r{pdf}.json")), required(os.path.join(d, "B", f"r{pdf}.json"))
    def keyed(d):
        # The key drops what the two readers FILED differently, not what they read differently: a remark like
        # "(played as John Webster)" one reader kept in the name and the other moved to the note, and a trailing
        # comma ("Besta,"). A nickname in parentheses -- "(Hawk)" -- is part of the name and stays.
        def name_key(s):
            s = re.sub(r"\((?:[^)]*\b(?:played|born|also|know|known)\b[^)]*)\)", "", t(s) or "", flags=re.I)
            return re.sub(r"[,\s]+$", "", re.sub(r"\s+", " ", s)).strip().lower()
        seen = collections.Counter(); out = {}
        for e in d.get("entries", []):
            k = (name_key(e.get("name_as_printed")), (t(e.get("teams_as_printed")) or "").replace(" ", "").lower())
            seen[k] += 1; out[k + (seen[k],)] = e
        return out
    ea, eb = keyed(a), keyed(b); dis, out = [], []
    for k in sorted(set(ea) ^ set(eb)):
        e = ea.get(k) or eb.get(k)
        dis.append({"pdf": pdf, "what": "a register entry one reader has and the other does not (name or team-by-year read differently)",
                    "reader": "A" if k in ea else "B", "name_as_printed": e.get("name_as_printed"), "teams_as_printed": e.get("teams_as_printed")})
    for k in sorted(set(ea) & set(eb)):
        x, y = ea[k], eb[k]
        u = unsure(x) | unsure(y)
        same = (t(x.get("college_as_printed")) == t(y.get("college_as_printed")) and x.get("college_cell") == y.get("college_cell"))
        if u & {"college_as_printed", "college_cell", "college"} or not same:
            dis.append({"pdf": pdf, "what": "college read differently or marked uncertain", "name_as_printed": x.get("name_as_printed"),
                        "A": x.get("college_as_printed"), "B": y.get("college_as_printed")}); continue
        out.append({"pdf": pdf, "name_as_printed": t(x["name_as_printed"]), "teams_as_printed": t(x["teams_as_printed"]),
                    "college_as_printed": t(x.get("college_as_printed")), "college_cell": x.get("college_cell")})
    return out, dis


# ---------------------------------------------------------------- the archive
class RM(H.RM):
    """Ruling One's read model, BASE STATE for THIS route: every stint claim except this store's own."""
    def roster(self, club_id, year):
        ph = ",".join("?" * len(H.STAFF))
        q = ("select distinct person from claim where scope='stint' and club_id=? and year=? and store not like ? "
             f"and person is not null and predicate not in ({ph})")
        return {p for (p,) in self.c.execute(q, (club_id, year, NEFT_STORES, *sorted(H.STAFF)))}


def city_club(C, cities, year, league):
    """The one archive club of these city names in the league that season, or None."""
    hits = set()
    for cid, c in C.by_id.items():
        nm = C.name_for(cid, year)
        if nm and C.plays(cid, year, league) and any(club_norm(nm).startswith(club_norm(x)) for x in cities):
            hits.add(cid)
    return next(iter(hits)) if len(hits) == 1 else None


def header_club(C, printed, year, league):
    """A roster header -> (club id, how). The table's resolver first; then the city the header begins with."""
    s = re.sub(r"\(.*?\)", "", printed).strip()
    # A HEADER NAMING TWO CLUBS IS NEFT'S COMBINED CLUB, AND IT IS HELD, NOT PLACED. "CINCINNATI REDS 0-8-0 Algy Clark --
    # ST. LOUIS GUNNERS 1-2-0 Mike Palm" is one roster in the book and two clubs in the archive; Ryan, 2026-09-11: two
    # sources disagreeing about how a season is organised, held and not resolved. Found before pass 2 wrote a claim: the
    # city fallback below resolved the header as Cincinnati, which would have put all of C-S on the Reds.
    parts = [p for p in re.split(r"\s+[—–-]+\s+", s) if p.strip()]
    if len(parts) > 1:
        names = [re.sub(r"\s+\d+-\d+-\d+.*$", "", p).strip() for p in parts]
        return None, (f"refused: the header names {len(parts)} clubs in one roster ({' / '.join(names)}) -- Neft's "
                      "combined club, held and not placed on either (Ryan, 2026-09-11)")
    r = C.resolve(s.title(), year, league, source=SOURCE_ID)
    if r: return r[0], f"club table: {r[1]}"
    hits = {cid for cid in C.by_id if C.name_for(cid, year) and C.plays(cid, year, league)
            and club_norm(s).startswith(club_norm(" ".join(C.name_for(cid, year).split()[:-1])) or "\0")}
    if len(hits) == 1: return next(iter(hits)), "the city the header begins with"
    return None, "refused: " + ("no club" if not hits else f"{len(hits)} clubs") + " of that city that season"


def move_codes(move):
    # From 1933 a Chicago club is printed with a space: "to & from CHI B", "from CHI C". Read as ChiB and ChiC.
    move = re.sub(r"\bCHI\.?\s+([BCT])\b", lambda m: "Chi" + m.group(1), move or "", flags=re.I)
    return [w.lower().rstrip(".") for w in re.findall(r"[A-Za-z]+\.?", move)
            if w.lower().rstrip(".") in CODES]


TEAM = re.compile(r"(PC|HC)?((?:\d{2}(?:-\d{2})?,?)+)([A-Z][A-Za-z]*(?:-[A-Z][A-Za-z]*)?)")
def register_seasons(teams):
    """'20ChiT 20Ham 20-21Det PC22Ham 26AFL' -> [(1920,'chit'), (1920,'ham'), (1920,'det'), (1921,'det'), (1922,'ham')].
    HC (a non-playing coach) and league codes are not playing seasons."""
    out = []
    for pc, yrs, code in TEAM.findall((teams or "").replace(" and ", " ")):
        if pc == "HC" or code.lower() not in CODES: continue
        for part in yrs.strip(",").split(","):
            a, _, b = part.partition("-")
            for yy in range(int(a), int(b or a) + 1): out.append((1900 + yy, code.lower()))
    return out


def flip(printed):
    sur, _, fore = printed.partition(",")
    fore = fore.strip(); out = []
    nick = re.search(r"\(([^)]+)\)", fore); plain = re.sub(r"\(.*?\)", "", fore).strip()
    if nick: out.append(f"{nick.group(1).strip()} {sur.strip()}")
    if plain: out.append(f"{plain} {sur.strip()}")
    if not fore: out.append(sur.strip())
    return out


def main(write=False):
    C = Clubs(); rm = RM()
    claims, leads, candidates, refusals, held_back, rdis, unresolved = [], [], [], [], [], [], []
    srecs = {}; n = collections.Counter(); season = collections.defaultdict(collections.Counter)
    placed = {}                       # (club_id, year, name_as_printed) -> pid, for the register join
    held = collections.defaultdict(lambda: collections.defaultdict(set))
    for p, pred, v in rm.c.execute("select person, predicate, value from claim where person is not null and store not like ? and "
                                   "(predicate like '%height' or predicate like '%HEIGHT' or predicate like '%weight' or "
                                   "predicate like '%WEIGHT' or (predicate like '%college%' and predicate != 'pfa.college_season'))",
                                   (NEFT_STORES,)):
        fam = "height" if pred.lower().endswith("height") else "weight" if pred.lower().endswith("weight") else "college"
        try: v = json.loads(v)
        except Exception: pass
        if isinstance(v, (str, int, float)): held[p][fam].add(str(v))

    def reading(fam, v):
        try: r = READERS[fam](v)
        except Exception: r = None
        return r

    def compare(pid, fam, v, y):
        prior = held[pid][fam]
        # A COLLEGE OF "none" IS NOT A SCHOOL. StatsCrew writes `none` for both Neft's printed none and his blank
        # (measured on 1920 Hammond, 2026-09-11), so a Neft school beside it fills a gap; it is not a disagreement.
        # Counted on the first full dry run as 416 disagreements and 0 gaps, which was the wrong way round.
        if fam == "college": prior = {x for x in prior if x.strip().lower() not in ("none", "unknown", "")}
        if not prior: season[y][f"{fam}: the archive lacks"] += 1; return "the archive lacks"
        mine = reading(fam, v); theirs = {reading(fam, x) for x in prior} - {None}
        if mine is not None and mine in theirs: season[y][f"{fam}: agrees"] += 1; return "agrees"
        season[y][f"{fam}: DISAGREES, both held"] += 1; return "disagrees; both held"

    def claim(pid, subj, pred, val, pdf, **extra):
        pp = pdf - 2; sr = f"{SOURCE_ID}#p{pp}"
        srecs[sr] = {"source_id": SOURCE_ID, "locator": f"printed page {pp} (PDF {pdf})",
                     "rights": BOOK["rights"]}
        c = {"source_record": sr, "source_id": SOURCE_ID, "stated_by": BOOK["stated_by"],
             "attribution": [f"{BOOK['title']}, p. {pp}"], "subject": subj, "predicate": pred, "value": val,
             "kind": "observed", "observed_at": 1978, "person": pid, "_cited": f"{BOOK['title']}, p. {pp}",
             "_lineage": LINEAGE, "_read_by": READ_BY}
        c.update(extra); claims.append(c); n[pred] += 1
        return c

    # ------------------------------------------------ the yearly rosters
    # TWO PHASES. Phase 1 joins every line ruling One finds on its own club-season. Phase 2 places the rest by the
    # printed move or the club's adjacent season -- and REFUSES an adjacent-season placement on a man this book prints
    # on another club that same season. Found on the first dry run: Neft's surname-only 1920 Cleveland "O'Connor"
    # joined Dan O'Connor through the 1921 Cleveland roster, though the same page prints Dan O'Connor on 1920 Canton
    # with no move. A printed move is different: there the book itself names the other club.
    items = []; joined_elsewhere = collections.defaultdict(lambda: collections.defaultdict(set))  # year -> pid -> clubs
    # ONE CLUB, ONE BLOCK, ACROSS PAGES. From 1933 a club's linemen sit on one page and its backs and ends on the facing
    # page, so the block is (season, club), not (page, club) -- otherwise a surname or a full name printed twice on one
    # club, once among the linemen and once among the backs, would never be counted twice. Each line keeps its own page.
    blocks = collections.OrderedDict()
    for pdf in ROSTER_PAGES:
        lines, dis = agree_roster(pdf); rdis += dis
        y = SEASON_OF_PAGE[pdf]
        season[y]["lines both readers agree on"] += len(lines); season[y]["reader disagreements"] += len(dis)
        for L in lines: blocks.setdefault((y, club_key(L["club_as_printed"])), []).append(L)
    for (y, _), block in blocks.items():
        lg = LEAGUE(y); printed = block[0]["club_as_printed"]
        cid, how = header_club(C, printed, y, lg)
        if not cid:
            unresolved.append({"pdf": sorted({L["pdf"] for L in block}), "club_as_printed": printed, "season": y,
                               "why": how, "men": len(block)})
            season[y]["lines on a club the table cannot name"] += len(block); continue
        roster = rm.roster(cid, y)
        sn = collections.Counter(H.surname(L["name_as_printed"]) for L in block)
        # A FULL NAME PRINTED TWICE ON ONE CLUB IS NOT ONE MAN. Ruling One refuses a surname the document prints
        # twice; its exact-name tier did not, so both of Neft's 1926 Brooklyn Lions named Earl Britton -- FB 6'3"
        # 200 age 24, starred, and FB-TB-WB 5'10" 185 age 29 -- joined the one Earl Britton held, and two men's
        # figures landed on one person. Caught by gate_neft_ingest N1 on the first write; both lines refuse now.
        full = collections.Counter((L["name_as_printed"] or "").lower() for L in block)
        for L in block:
            pdf = L["pdf"]
            if full[(L["name_as_printed"] or "").lower()] > 1:
                items.append({"pdf": pdf, "y": y, "lg": lg, "cid": cid, "how": how, "printed": L["club_as_printed"],
                              "roster": roster, "sn": sn, "L": L, "tier": None, "pid": None, "via": None,
                              "ev": f"REFUSED: the book prints the name '{L['name_as_printed']}' "
                                    f"{full[(L['name_as_printed'] or '').lower()]} times on this club-season; "
                                    "one held man cannot be both"})
                continue
            tier, pid, ev = H.join(L["name_as_printed"], roster, rm, sn)
            if pid: joined_elsewhere[y][pid].add(cid)
            items.append({"pdf": pdf, "y": y, "lg": lg, "cid": cid, "how": how, "printed": L["club_as_printed"],
                          "roster": roster, "sn": sn, "L": L, "tier": tier, "pid": pid, "ev": ev, "via": None})
    # A SURNAME JOIN THE BOOK CONTRADICTS. Neft prints "Hunk Anderson" on the 1923 Bears by his full name and a separate
    # "Will Anderson" on the 1923 Cleveland Indians; the archive holds Hunk on Cleveland too, so ruling One's surname tier
    # joined Will to him and the new season-weight family set two men's weights against each other (185 vs 175). The
    # O'Connor shape, found in phase 1: a surname join is refused when the same season's pages join that man BY HIS FULL
    # NAME on another club and neither line prints a move. A printed move links the two lines (Whitey Woodin, 1922:
    # "from RAC" on Green Bay, "to GB" on Racine) and the join stands.
    exact_on = collections.defaultdict(lambda: collections.defaultdict(list))   # year -> pid -> [(club, move)]
    for it in items:
        if it["pid"] and it["tier"] == "exact_full_name_on_the_club_season":
            exact_on[it["y"]][it["pid"]].append((it["cid"], it["L"]["fields"].get("move_as_printed")))
    for it in items:
        if not it["pid"] or it["tier"] != "surname_unique_on_the_club_season": continue
        mv = it["L"]["fields"].get("move_as_printed")
        other = [(c2, m2) for c2, m2 in exact_on[it["y"]].get(it["pid"], []) if c2 != it["cid"]]
        if other and not mv and not any(m2 for _, m2 in other):
            it.update(tier=None, pid=None, via=None, ev=(
                f"REFUSED: the surname joins {rm.index_name.get(it['pid'])} ({it['pid']}), but this book prints him by his "
                f"full name on {sorted(c for c, _ in other)} that same season, this line prints '{it['L']['name_as_printed']}', "
                "and no move links the two"))
    for it in items:
        if it["pid"] or it["ev"] != "not on the club-season": continue
        tier, pid, ev, via = place_elsewhere(C, rm, it["L"]["name_as_printed"], it["L"]["fields"].get("move_as_printed"),
                                             it["cid"], it["y"], it["lg"], it["sn"])
        if pid and tier == "the_clubs_adjacent_season" and joined_elsewhere[it["y"]].get(pid, set()) - {it["cid"]}:
            tier, pid, ev, via = None, None, (
                f"REFUSED: the club's adjacent season names {rm.index_name.get(pid)} ({pid}), but this book prints him on "
                f"{sorted(joined_elsewhere[it['y']][pid])} that same season with no move to this club"), None
        it.update(tier=tier, pid=pid, ev=ev, via=via)
    for it in items:
        pdf, y, lg, cid, how, printed, roster = it["pdf"], it["y"], it["lg"], it["cid"], it["how"], it["printed"], it["roster"]
        L = it["L"]; nm, f = L["name_as_printed"], L["fields"]
        tier, pid, ev, via = it["tier"], it["pid"], it["ev"], it["via"]
        code = C.code_for(cid, y); key = f"{lg}-{y}"
        if not pid:
            rec = {"IS_NOT_A_PERSON": True, "name_as_printed": nm, "club_as_printed": printed, "club_id": cid,
                   "season": y, "printed_page": pdf - 2, "fields_both_readers_agree_on": f, "why": ev}
            if str(ev).startswith("REFUSED"):
                refusals.append(rec); season[y]["refused"] += 1; continue
            # RULING THREE: a spelling variant of a man already on the roster (Applegran against Appelgran) is a
            # CANDIDATE -- shown with its counterpart, joined to nobody, never counted as a man the archive lacks.
            # Only a name with no visible counterpart is a lead.
            cp = H.counterpart(nm, roster, set(), rm)
            if cp:
                rec["visible_counterpart_on_the_club_season"] = cp; rec["kind"] = "candidate"
                candidates.append(rec); season[y]["CANDIDATES: a spelling beside a held man, joined to nobody"] += 1
            else:
                rec["kind"] = "lead"; leads.append(rec)
                season[y]["LEADS: named by Neft, placed nowhere, no counterpart"] += 1
            continue
        if pid in HOLD_OUT:
            held_back.append({"person": pid, "why": HOLD_OUT[pid], "name_as_printed": nm, "club_id": cid,
                              "season": y, "printed_page": pdf - 2})
            season[y]["held out: a merge question"] += 1; continue
        placed[(cid, y, nm.lower())] = pid
        new = tier in ("named_in_the_printed_move", "the_clubs_adjacent_season")
        season[y]["MEN: placed on a club-season the archive did not hold him on" if new else "joined on the club-season"] += 1
        if new: season[y][f"MEN placed via {tier}"] += 1
        joined_on = {"club_id": cid, "year": y, **({"via": via} if via else {})}
        subj = ["stint", pid, code, key]
        v = {"name_as_printed": nm, "club_as_printed": printed, "club_code": code, "league": lg, "year": y,
             **{k: f[k] for k in ("pos", "move_as_printed", "note_as_printed", "mark_as_printed") if f.get(k)},
             "_fields_the_readers_disagreed_on": L["disagreed"], "_join_tier": tier, "_join_evidence": ev,
             "_joined_on": joined_on, "_club_resolved_by": how,
             "_definition": PREDICATE_DEFINITIONS["neft.roster_as_printed"]["definition"]}
        claim(pid, subj, "neft.roster_as_printed", v, pdf)
        # RULING ONE, 2026-09-12: the move is its own claim, neft.move_as_printed -- the words, and nothing they imply.
        if f.get("move_as_printed"):
            claim(pid, subj, "neft.move_as_printed",
                  {"move_as_printed": f["move_as_printed"], "name_as_printed": nm, "club_as_printed": printed,
                   "_definition": PREDICATE_DEFINITIONS["neft.move_as_printed"]["definition"]},
                  pdf, _joined_on=joined_on, _join_tier=tier)
        for fld, pred, fam in (("hgt", "neft.roster.height", "height"), ("wgt", "neft.roster.weight", "weight")):
            if f.get(fld):
                claim(pid, subj, pred, f[fld], pdf, _joined_on=joined_on, _join_tier=tier,
                      _against_the_archive=compare(pid, fam, f[fld], y))

    # ------------------------------------------------ the register: colleges
    for pdf in REGISTER_PAGES:
        entries, dis = agree_register(pdf); rdis += dis
        n["register entries both readers agree on"] += len(entries)
        for e in entries:
            allseas = register_seasons(e["teams_as_printed"])
            # A register page BORROWED from another pass (pass 2 reading pass 1's 1920-32 register): an entry with a
            # season before this decade was that pass's to join, so its college is not claimed a second time.
            if pdf in REGISTER_DIRS and any(yy < min(YEARS) for yy, _ in allseas):
                n["register: an entry the earlier pass reaches, left to it"] += 1; continue
            seasons = [(yy, code) for yy, code in allseas if yy in YEARS]
            if not seasons: continue
            forms = {" ".join(H.toks(x)) for x in flip(e["name_as_printed"])}
            pids = set(); on = []
            for yy, code in seasons:
                cid = city_club(C, CODES[code], yy, LEAGUE(yy))
                for (c2, y2, nm), pid in placed.items():
                    if c2 == cid and y2 == yy and (" ".join(H.toks(nm)) in forms or
                                                     any(v in H.variants(nm) for x in forms for v in H.variants(x) if len(v) > 1)):
                        pids.add(pid); on.append({"club_id": cid, "year": yy})
            cell = e["college_cell"]
            if len(pids) != 1:
                n["register: not joined to one man this pass placed"] += 1; continue
            pid = next(iter(pids)); yy = on[0]["year"]
            if pid in HOLD_OUT: n["register: held out, a merge question"] += 1; continue
            if cell == "none": season[yy]["college: 'none' printed (counted, not claimed)"] += 1; continue
            if cell != "printed" or not e["college_as_printed"]: continue
            for col in [x.strip() for x in e["college_as_printed"].split(",") if x.strip()]:
                claim(pid, ["person", pid], "neft.college_as_printed", col, pdf,
                      _printed_in="the 1920-32 register", _name_as_printed=e["name_as_printed"],
                      _teams_as_printed=e["teams_as_printed"], _joined_on=on[0], _joined_via=on,
                      _against_the_archive=compare(pid, "college", col, yy))

    # WHERE THE ARCHIVE HOLDS A LEAD'S EXACT NAME THAT SEASON -- information for Ryan, NEVER a join: the book puts him
    # on one club and the archive on another (John Barsha: Neft's 1920 Hammond, the archive's 1920 Rochester).
    for l in leads:
        pv = {v for v in H.variants(l["name_as_printed"]) if len(v) > 1}
        ps = {p for p in rm.by_sur.get(H.surname(l["name_as_printed"]), ())
              if any(pv & H.variants(x) for x in rm.names[p])} if pv else set()
        l["the_archive_holds_this_exact_name_that_season_on"] = sorted({
            f"{rm.index_name.get(p)} ({p}): {cid}" for p in ps
            for (cid,) in rm.c.execute("select distinct club_id from claim where person=? and scope='stint' and year=? "
                                        "and store not like ?", (p, l["season"], NEFT_STORES))})
    counts = {"claims": len(claims), "by_predicate": dict(n), "leads": len(leads), "candidates": len(candidates),
              "refusals": len(refusals),
              "held_back": len(held_back), "reader_disagreements": len(rdis), "clubs_unresolved": len(unresolved),
              "by_season": {y: dict(c) for y, c in sorted(season.items())}}
    out = {"source": BOOK, "source_records": srecs, "predicate_definitions": PREDICATE_DEFINITIONS,
           "proposed_predicate_for_the_move": PROPOSED_MOVE_PREDICATE, "_the_lineage": LINEAGE,
           "claims": claims, "leads": leads, "candidates": candidates, "refusals": refusals, "held_back": held_back,
           "reader_disagreements": rdis, "clubs_the_table_cannot_name": unresolved, "counts": counts}
    if write:
        # THE ACCOUNT OF WHAT A REWRITE DROPS (index_io.write_store). A claim on a line whose full name the book prints
        # twice on its club was a defect of the first write and is withdrawn by name; anything else lost has no reason
        # on purpose, so gate_reingest_losses R1 fails it.
        twice = {(f"{SOURCE_ID}#p{r['printed_page']}", r["club_as_printed"], r["name_as_printed"].lower()) for r in refusals
                 if "times on this club-season" in r["why"]}
        contradicted = {(f"{SOURCE_ID}#p{r['printed_page']}", r["club_as_printed"], r["name_as_printed"].lower()) for r in refusals
                        if "by his full name on" in r["why"]}
        # What rested on those lines in the PREDECESSOR: their stint subjects (the roster line, its height and weight)
        # and their men (a college is joined through the line). Read from the store being replaced, not guessed.
        gone_subj, gone_men, gone_contra, gone_contra_men = set(), set(), set(), set()
        if os.path.exists(OUT):
            for oc in json.load(open(OUT)).get("claims", []):
                ov = oc.get("value") if isinstance(oc.get("value"), dict) else {}
                k = (oc.get("source_record"), ov.get("club_as_printed"), (ov.get("name_as_printed") or "").lower())
                if oc.get("predicate") == "neft.roster_as_printed" and k in twice:
                    gone_subj.add(json.dumps(oc["subject"])); gone_men.add(oc.get("person"))
                if oc.get("predicate") == "neft.roster_as_printed" and k in contradicted:
                    gone_contra.add((json.dumps(oc["subject"]), oc.get("source_record")))
                    gone_contra_men.add(oc.get("person"))
        WHY2 = ("withdrawn: a surname join the book contradicts -- it prints the joined man by his full name on another club "
                "that season, this line prints another forename, and no move links them (Will against Hunk Anderson, 1923; "
                "found through the season-weight family, 2026-09-12)")
        WHY = ("withdrawn: the book prints this name twice on the club-season and one held man cannot be both; the first "
               "write joined both lines to him (gate_neft_ingest N1, 2026-09-12)")
        # A RESTATEMENT IS NOT A LOSS: the same subject, predicate, source record and value with only its `_`-annotations
        # changed -- ruling Two added `basis` to the move route's `_joined_on` (2026-09-12). The same account
        # ingest_football_hunting gives. Anything else lost still gets no reason, so gate_reingest_losses R1 fails it.
        def plain(v): return {k: x for k, x in v.items() if not str(k).startswith("_")} if isinstance(v, dict) else v
        now = {(json.dumps(c["subject"]), c["predicate"], json.dumps(plain(c["value"]), sort_keys=True), c["source_record"])
               for c in claims}
        refiled = {(json.dumps(c["subject"]), json.dumps(c["value"]), c["source_record"]) for c in claims
                   if c["predicate"] == "neft.college_as_printed"}
        def reasons(old):
            if old.get("predicate") == "college" and \
                    (json.dumps(old.get("subject")), json.dumps(old.get("value")), old.get("source_record")) in refiled:
                return ("refiled as neft.college_as_printed, the same value on the same man and page: in the college "
                        "family Neft's abbreviations made fabricated disagreements (2026-09-12)", {})
            if json.dumps(old.get("subject")) in gone_subj: return (WHY, {})
            if (json.dumps(old.get("subject")), old.get("source_record")) in gone_contra: return (WHY2, {})
            # A college reaches a man only through a roster line this pass joined; withdraw the line and the college it
            # carried was on the wrong man too (Drake on Jerry Johnson, from Neft's George Johnson).
            if old.get("predicate") == "neft.college_as_printed" and old.get("person") in gone_contra_men:
                return (WHY2 + " -- this college was joined through that line, so it sat on the wrong man", {})
            if old.get("predicate") == "college" and old.get("person") in gone_men:
                return (WHY + " -- this college was joined through that line", {})
            if (json.dumps(old.get("subject")), old.get("predicate"), json.dumps(plain(old.get("value")), sort_keys=True),
                    old.get("source_record")) in now:
                return ("restated: the same fact with only its _-annotations changed (ruling Two, 2026-09-12, added "
                        "`basis` to the move route's _joined_on). Not a loss of any fact.", {})
            return None
        IO.write_store(out, OUT, reasons=reasons, indent=1)
        IO.dump_atomic({"written": datetime.date.today().isoformat(), "counts": counts, "leads": leads,
                        "refusals": refusals, "held_back": held_back, "reader_disagreements": rdis,
                        "clubs_the_table_cannot_name": unresolved}, REPORT, indent=1)
    return out


def place_elsewhere(C, rm, nm, move, cid, y, lg, sn):
    """The two stated routes for a man ruling One does not find on the club-season. -> (tier, pid, evidence, via)."""
    # RULING TWO, 2026-09-12: on the club a printed move names, ruling One applies in full -- an exact name OR a
    # surname unique on that roster. "The book is telling you he moved to Kenosha, so the club is not a guess." The
    # refusal carries over: two men of the surname on that roster refuse both (H.join's own refusal), and so does the
    # surname printed twice on this club's block. (He is not on this club's roster, or phase 1 would have joined him.)
    found, refused = {}, []
    for code in move_codes(move):
        other = city_club(C, CODES[code], y, lg)
        if not other or other == cid: continue
        tier, pid, ev = H.join(nm, rm.roster(other, y), rm, sn)
        if str(ev).startswith("REFUSED"): refused.append(f"{other}: {ev}")
        elif pid: found[pid] = (other, tier, ev)
    if refused:
        return None, None, "REFUSED on the club the printed move names -- " + "; ".join(refused), None
    if len(found) == 1:
        pid, (other, inner, iev) = next(iter(found.items()))
        return ("named_in_the_printed_move", pid,
                f"not on the club-season; his line prints '{move}', and on {other} {y}, the club those words name: {iev}",
                {"club_id": other, "year": y, "move_as_printed": move, "basis": inner})
    if len(found) > 1:
        return None, None, f"REFUSED: the printed move names {len(found)} clubs, each holding a man this name joins", None
    found, refused = set(), []
    for yy in (y - 1, y + 1):
        if not C.code_for(cid, yy): continue
        tier, pid, ev = H.join(nm, rm.roster(cid, yy), rm, sn)
        if str(ev).startswith("REFUSED"): refused.append(f"{yy}: {ev}")
        elif pid: found.add((pid, yy))
    if refused:
        return None, None, "REFUSED on the club's adjacent season -- " + "; ".join(refused), None
    if len({p for p, _ in found}) == 1:
        pid = next(iter(found))[0]; yrs = sorted(yy for _, yy in found)
        return ("the_clubs_adjacent_season", pid,
                f"not on the club-season; the name joins one man on the same club's {', '.join(map(str, yrs))} "
                "season (ruling One extended, 2026-09-11)", {"club_id": cid, "adjacent_years": yrs})
    if len({p for p, _ in found}) > 1:
        return None, None, "REFUSED: the adjacent seasons join two different men", None
    return None, None, "not on the club-season, not named by a printed move, not on the club's adjacent season", None


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"claims {c['claims']:,}  leads {c['leads']}  refusals {c['refusals']}  held out {c['held_back']}  "
          f"reader disagreements {c['reader_disagreements']}  clubs unresolved {c['clubs_unresolved']}")
    print("  by predicate:", c["by_predicate"])
    for y, s in c["by_season"].items():
        print(f"  {y}: " + "; ".join(f"{k} {v}" for k, v in sorted(s.items())))
    if "--write" not in sys.argv: print("DRY RUN -- nothing written. --write to write.")
