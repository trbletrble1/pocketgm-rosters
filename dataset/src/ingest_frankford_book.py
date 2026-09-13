"""frankfordyellowjacketsbook.com -- the companion site to the Frankford Yellow Jackets book.

Ryan's ruling, 2026-09-09, after the assessment in
reports/2026-09-09-frankfordyellowjacketsbook-assessment.md: IT GOES IN. A contemporary
club collection worked from the Historical Society of Frankford, not the Neft lineage,
and it behaves like an independent source -- corroborating almost exactly for 1924-31 and
adding twelve men for 1922-23 that Fenton never gave.

TWO STORES, because one store cannot be two leagues:
  frankford-book.json      the NFL seasons 1924-31, and every person-scoped name claim
  frankford-book-ind.json  1899-1923, played in no league the archive holds, plus the games

THE JOIN IS EXACT NAME ONLY FOR A CLUB-SEASON PLACEMENT. Ryan's ruling, and the third
time this archive has met it: Andy King, Jim Talbot, the 1934 Cincinnati Reds. 65 rows
match exactly and 179 on surname alone; the 179 place NOBODY and are listed as
candidates. Reporting the surname matches as fills would have claimed 27 positions
filled where the defensible figure is 7.

A PERSON-SCOPED NAME CLAIM IS NOT A PLACEMENT and may use tier 3 -- a surname unique
among the men the archive already holds on that club-season -- because it adds a string
to a man rather than adding a man to a club-season. Every claim records which tier
placed it, so the two can never be counted together by accident.

NOBODY IS PROMOTED AND NO CLUB IS CREATED HERE. A man the archive does not hold is a
LEAD with its evidence; an opponent string is a CANDIDATE. The four pre-1922 club-seasons
are declared in declarations/clubs.json under the boundary ruling, not minted here.

  python3 src/ingest_frankford_book.py            read and report
  python3 src/ingest_frankford_book.py --write    write both stores
"""
import os, re, sys, json, html, glob, unicodedata, collections, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

SITE = os.path.expanduser("~/Documents/pgm3-sources/frankford-book")
SRC_ID = "frankford-yellow-jackets-book"
STATED = "Brian Michael and Andrew Weicker"
ATTRIB = ["Brian Michael and Andrew Weicker, frankfordyellowjacketsbook.com, 2026"]
OBSERVED = "fetched-2026-09-09"

# The club-season key each roster page lands on. NFL years use the archive's own code;
# the independent years use the DOC codes declared in declarations/clubs.json. A year
# with no entry here has NO club-season and its men can only be leads.
KEY = {y: ("FYJ", f"NFL-{y}", "frankford-book") for y in range(1924, 1932)}
KEY.update({1922: ("DOC:FYJ-IND", "1922", "frankford-book-ind"),
            1923: ("DOC:FYJ-IND", "1923", "frankford-book-ind")})
KEY.update({y: ("DOC:FYJ-EARLY", str(y), "frankford-book-ind") for y in (1899, 1900, 1903, 1906)})
NO_CLUB_SEASON = (1912, 1913, 1914, 1915, 1919, 1921)
# The key the PERSON INDEX writes for these stints: the store's declared league, the
# year, the code. promote_players matches a lead's `places_on.club_season` against it.
INDEX_KEY = {y: f"NFL|{y}|FYJ" for y in range(1924, 1932)}
INDEX_KEY.update({y: f"IND|{y}|DOC:FYJ-IND" for y in (1922, 1923)})
INDEX_KEY.update({y: f"IND|{y}|DOC:FYJ-EARLY" for y in (1899, 1900, 1903, 1906)})
ONLY_SOURCE = ("THE ONLY SOURCE IN EXISTENCE FOR THIS CLUB-SEASON. No other source in the "
               "archive or its caches names the Frankford Yellow Jackets before 1922, so "
               "nothing can corroborate this man and nothing ever refuses him. He is here "
               "because one page of one site prints him on this roster, and that is the "
               "whole of it.")

RECON = ("the authors' own compilation. Their rosters index states it: 'This is our attempt to "
         "piece together the players who appeared in at least one game for each of the Frankford "
         "Yellow Jackets seasons 1899-1931.' Not a transcription of one club document.")
DECL = json.load(open(os.path.join(BASE, "declarations", "frankford-book.json")))
# A ROSTER LINE PRINTED AS STAFF IS STAFF (Ryan, 2026-09-12). The declaration said so from
# 2026-09-09 and this file never read it: Swope and Gilmore went in as playing stints.
STAFF_PRINTED = frozenset(DECL["staff_printed_among_players"]["roles"])
FO = DECL["front_office_page"]
PROMOTED_TIER = ("this ingest's own lead, promoted by promote_players.py -- the exact printed "
                 "name on the exact club-season")
from ingest_football_hunting import PREDICATE_DEFINITIONS as _HUNT_PREDS
import staff_people as SP
STAFF_DEF = _HUNT_PREDS["club_staff_role"]["definition"]
NOT_A_PERSON = ("names no person and joins no one; the archive may hold a namesake and that is "
                "not this man")
CAPTAIN_OR_COACH_DEF = ("printed under the front-office page's heading 'Captains/Coaches of the "
                        "Football Team of Frankford A.A.', which does not say which of the two a "
                        "man was. Held as captain-or-coach, never as a coaching season (Ryan, "
                        "2026-09-12).")


def cs_subject(y):
    code = KEY[y][0]
    return ["club_season", "NFL" if code == "FYJ" else "IND", str(y), code]


def years_in(s):
    out = []
    for a, b in re.findall(r"\b(1[89]\d\d)(?:\s*-\s*(1[89]\d\d))?\b", s):
        out += list(range(int(a), int(b or a) + 1))
    return sorted(set(out))


def front_office():
    """-> [(heading, line_as_printed, name_part, years_part, [years])] from the cached page.
    Each list is one <p> under an <h4>, one line per <br>. A heading the declaration does
    not name stops the run."""
    s = open(os.path.join(SITE, "the-yellow-jackets_front-office.html"), encoding="utf-8",
             errors="replace").read()
    m = re.search(r"(?is)<main.*?</main>", s) or re.search(r"(?is)<article.*?</article>", s)
    s = m.group(0) if m else s
    parts = re.split(r"(?is)<h4[^>]*>(.*?)</h4>", s)
    out = []
    for heading, body in zip(parts[1::2], parts[2::2]):
        h = flat(heading)
        if h in FO["prose_headings"]: continue
        if h not in FO["headings"]:
            raise SystemExit(f"REFUSING: the front-office page has a heading the declaration does "
                             f"not name: {h!r}")
        p = re.search(r"(?is)<p[^>]*>(.*?)</p>", body)
        for raw in re.split(r"(?i)<br\s*/?>", p.group(1) if p else ""):
            line = flat(raw)
            if not line: continue
            mm = re.match(r"^(.*?)\s+[–-]\s+(.*)$", line)
            if not mm or not years_in(mm.group(2)):
                raise SystemExit(f"REFUSING: a front-office line with no name-dash-years shape: {line!r}")
            out.append((h, line, mm.group(1).strip(), mm.group(2).strip(), years_in(mm.group(2))))
    return out


HSF = ("Historical Society of Frankford -- Howard Barnes's 1985 scrapbook of newspaper articles "
       "and game results, and Frankford Athletic Association documents and photographs. Named by "
       "the authors on the site, not by this ingest.")


def flat(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[“”\"'’]", "", s)
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def page_table(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"(?is)<main.*?</main>", s) or re.search(r"(?is)<article.*?</article>", s)
    s = m.group(0) if m else s
    out = []
    for t in re.findall(r"(?is)<table.*?</table>", s):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", t):
            cs = [flat(x) for x in re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", tr)]
            if any(cs): rows.append(cs)
        if rows: out.append(rows)
    return out


def rosters():
    """-> {year: (header, [row, ...])}, from the pages on disk."""
    out = {}
    for f in sorted(glob.glob(os.path.join(SITE, "*-roster.html"))):
        y = int(os.path.basename(f)[:4])
        tabs = page_table(f)
        if not tabs: continue
        rows = tabs[0]
        out[y] = (rows[0], rows[1:])
    return out


def schedules():
    """-> {year: [(date, opponent_as_printed, result, is_league)]}. THE ASTERISK IS THE
    SITE'S OWN convention for a league game; its absence marks a non-league one. Read,
    not inferred."""
    out = {}
    for f in sorted(glob.glob(os.path.join(SITE, "*-schedule-results.html"))):
        y = int(os.path.basename(f)[:4])
        tabs = page_table(f)
        if not tabs: continue
        games = []
        for r in tabs[0][1:]:
            if len(r) < 3 or r[0] == "Date": continue
            opp = r[1]
            games.append((r[0], opp, r[2], "*" in opp))
        out[y] = games
    return out


def held(conn, own=frozenset()):
    """What the archive holds on Frankford, per year: exact names and surnames.

    `own` is the men promote_players minted from THIS ingest's leads. Their names reach
    person_name through promotion-names, the name each decision recorded -- which is this
    ingest's own printed line coming back. Measured 2026-09-12: a re-run relabelled 202
    placements from "this ingest's own lead" to "exact name on the club-season", as if the
    archive had held the man before this source. So their promotion names are not read."""
    ex = collections.defaultdict(dict); sur = collections.defaultdict(lambda: collections.defaultdict(set))
    for pid, y in conn.execute("""select distinct person, year from claim
            where club_str in ('FYJ','DOC:FYJ-IND','DOC:FYJ-EARLY') and person is not null"""):
        if pid in own:
            # nothing but this site and its own promotion names him: the base state holds no
            # name for him, so there is nothing to join on. promoted() places him.
            others = conn.execute("select 1 from person_name where person=? and store not like "
                                  "'frankford-book%' and store != 'promotion-names' limit 1", (pid,)).fetchone()
            if not others: continue
        # THE NAME A PROMOTION DECISION RECORDED, read from the decision and not from
        # promotion-names. Measured 2026-09-12: promotion-names writes a decision's name only
        # for a man no other store names -- and this ingest's own fuller names ARE another
        # store. So "Mellow" (P_045327, promoted from Fenton's 1922 page) left promotion-names
        # because this file had named him "David Mellow"; the next run could no longer find
        # him, dropped the fuller name, and would have found him again the run after. Nine
        # men flipped between candidate and lead, seven names came and went. The decision
        # store does not read this ingest, so the loop is cut here.
        if pid in DECIDED and pid not in own:
            n_ = norm(DECIDED[pid])
            if n_:
                ex[y].setdefault(n_, pid); sur[y][n_.split()[-1]].add(pid)
        # A DECIDER MUST NOT READ ITS OWN OUTPUT. The published model now holds this
        # ingest's own 142 fyjbook.name_as_printed claims, so on a second run every man
        # it had given a fuller name to matched EXACTLY -- surname candidates fell from
        # 179 to 37 and the claim count doubled, because the archive was agreeing with
        # yesterday's version of this file. The join reads what the archive held BEFORE
        # this source.
        for (nm,) in conn.execute("select distinct name from person_name where person=? "
                                  "and store not like 'frankford-book%'", (pid,)):
            n = norm(nm)
            if not n: continue
            ex[y].setdefault(n, pid)
            sur[y][n.split()[-1]].add(pid)
    longest = {}
    for pid, in conn.execute("select distinct person from person_name"):
        pass
    return ex, sur


def _decided_names():
    """person_id -> the name its promotion decision recorded, players and coaches."""
    out = {}
    for f in ("player-promotions.json", "coach-promotions.json"):
        p = os.path.join(BASE, "build", f)
        if not os.path.exists(p):
            raise SystemExit(f"REFUSING: build/{f} is absent; the join reads decision names from it")
        for d in json.load(open(p)).get("promotions") or []:
            if d.get("person_id") and d.get("name"): out[d["person_id"]] = d["name"]
    return out


DECIDED = _decided_names()


def longest_held(conn, pid):
    best = ""
    for (nm,) in conn.execute("select distinct name from person_name where person=? "
                              "and store not like 'frankford-book%'", (pid,)):
        if len(norm(nm)) > len(norm(best)): best = nm
    return best


def base(sr, tier=None, extra=None):
    c = {"source_id": SRC_ID, "source_record": sr, "stated_by": STATED,
         "attribution": list(ATTRIB), "kind": "observed", "observed_at": OBSERVED,
         "_the_page_is_a_reconstruction": RECON, "_collection_worked_from": HSF}
    if tier: c["_joined_on"] = tier
    if extra: c.update(extra)
    return c


def promoted():
    """name-as-printed + club-season -> the id promote_players minted for OUR OWN lead.

    A promoted player's seasons come from the ingest's CLAIMS, so this ingest has to run
    again after the promotion or the men it raised become people with no seasons. The
    match is the lead's own identity -- the exact printed name on the exact club-season --
    and not a name join against the archive."""
    p = os.path.join(BASE, "build", "player-promotions.json")
    if not os.path.exists(p): return {}
    out = {}
    for pr in json.load(open(p)).get("promotions", []):
        if not str(pr.get("source", "")).startswith("frankford-book"): continue
        idb = pr.get("identified_by") or {}
        nm = norm(idb.get("name_as_printed") or pr.get("name") or "")
        for ps in pr.get("playing_seasons") or []:
            out[(nm, int(ps["year"]), ps["club"])] = pr["person_id"]
    return out


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    PROM = promoted()
    ex, sur = held(conn, frozenset(PROM.values()))
    STAFF_PROM = SP.promoted_staff("frankford-book")
    # THE CLUB-SEASON'S ROSTER for the staff join, read from the person index: who the
    # archive holds on it. A staff man holds no season, so a staff claim never changes it.
    _idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    _ros = collections.defaultdict(list)
    for _p, _r in _idx.items():
        if _p == "_clubs" or not isinstance(_r, dict): continue
        for _k in (_r.get("seasons") or {}):
            _ros[_k].append((_p, [_r.get("name")]))
    ROSTER_OF = lambda key: _ros.get(key, [])
    R, S = rosters(), schedules()
    n = collections.Counter()
    out = {"frankford-book": [], "frankford-book-ind": []}
    srs = {"frankford-book": {}, "frankford-book-ind": {}}
    leads, candidates, opponents, refused = [], [], collections.Counter(), []
    staff_not_placed, staff_kept = [], []

    def rec(store, locator):
        sr = f"{SRC_ID}#{locator}"
        srs[store][sr] = {"source_id": SRC_ID, "locator": locator}
        return sr

    # ------------------------------------------------------------------ rosters
    for y in sorted(R):
        hdr, rows = R[y]
        gi = {c: i for i, c in enumerate(hdr)}
        loc = f"{y}-roster"
        store = KEY.get(y, (None, None, "frankford-book-ind"))[2]
        sr = rec(store, loc)
        for r in rows:
            def cell(c):
                i = gi.get(c)
                return r[i].strip() if i is not None and len(r) > i and r[i].strip() else None
            printed = cell("Name")
            if not printed: continue
            n["rows"] += 1
            pos, col, jer = cell("Position"), cell("College"), cell("Jersey Number")
            row = {"name_as_printed": printed, "position_as_printed": pos,
                   "college_as_printed": col, "jersey_as_printed": jer,
                   "club_as_printed": "Frankford Yellow Jackets", "year": y,
                   "page": f"https://frankfordyellowjacketsbook.com/{y}-roster/"}
            nm = norm(printed)
            if pos in STAFF_PRINTED:
                # CLUB_STAFF_ROLE ON THE CLUB-SEASON, naming no person (ruling Four). The man
                # this line promoted keeps his record through a person-scoped claim from the
                # same line (Ryan, 2026-09-12) -- joined on this ingest's own promotion, which
                # is the exact printed name on the exact club-season, not a new join.
                n["staff_printed_among_players"] += 1
                if y not in KEY:
                    staff_not_placed.append({**row, "why": "the archive holds no club-season for this year"})
                    continue
                code, key, store = KEY[y]
                only = {"_the_only_source_in_existence": ONLY_SOURCE} if code == "DOC:FYJ-EARLY" else None
                out[store].append({**base(sr, None, only), "subject": cs_subject(y),
                                   "predicate": "club_staff_role",
                                   "value": {"name_as_printed": printed, "role_as_printed": pos,
                                             "club_as_printed": "Frankford Yellow Jackets",
                                             "page": row["page"], "_definition": STAFF_DEF,
                                             "_not_a_person": NOT_A_PERSON},
                                   "_ruled": "Ryan, 2026-09-12: printed as Manager, so staff, not a player."})
                pid = PROM.get((nm, y, code)) or ex.get(y, {}).get(nm)
                if pid:
                    nsr = rec("frankford-book", loc)
                    out["frankford-book"].append({
                        **base(nsr, PROMOTED_TIER if PROM.get((nm, y, code)) else "exact name on the club-season", only),
                        "subject": ["person", pid], "predicate": "fyjbook.staff_role_as_printed",
                        "value": {"name_as_printed": printed, "role_as_printed": pos, "year": y, "club_code": code,
                                  "club_as_printed": "Frankford Yellow Jackets", "page": row["page"]},
                        "_why_a_person_claim": DECL["staff_printed_among_players"]["_the_man_is_kept"]})
                    staff_kept.append({"person": pid, "name_as_printed": printed, "year": y, "role_as_printed": pos})
                    n["staff_person_kept"] += 1
                continue
            pid = ex.get(y, {}).get(nm)
            tier = "exact name on the club-season"
            if not pid and y in KEY:
                pid = PROM.get((nm, y, KEY[y][0]))
                if pid:
                    tier = ("this ingest's own lead, promoted by promote_players.py -- the "
                            "exact printed name on the exact club-season")
            cand = sur.get(y, {}).get(nm.split()[-1], set()) if nm else set()

            if pid:                                   # TIER 1 -- and only tier 1 places a man
                n["placed_exact" if tier.startswith("exact") else "placed_own_promotion"] += 1
                code, key, store = KEY[y]
                subj = ["stint", pid, code, key]
                # THE EVIDENCE RIDES ON THE CLAIM, not in a declaration, wherever this is
                # the only source there is. Ryan's ruling: a reader must be able to see
                # that a man rests on one source without going and looking for one.
                only = {"_the_only_source_in_existence": ONLY_SOURCE} if code == "DOC:FYJ-EARLY" else None
                out[store].append({**base(sr, tier, only),
                                   "subject": subj, "predicate": "fyjbook.roster_as_printed",
                                   "value": row})
                for pred, v in (("fyjbook.position", pos), ("fyjbook.college", col),
                                ("fyjbook.jersey", jer)):
                    if v:
                        out[store].append({**base(sr, tier, only),
                                           "subject": subj, "predicate": pred, "value": v})
                        n[pred] += 1
            else:
                why = ("no man of that name on this club-season"
                       if y not in NO_CLUB_SEASON else
                       "the archive holds no club-season for this year at all")
                if len(cand) == 1:
                    # TIER 3. Admissible for a NAME, never for a placement.
                    tpid = next(iter(cand))
                    hn = longest_held(conn, tpid)
                    n["surname_candidate"] += 1
                    candidates.append({"year": y, "name_as_printed": printed,
                                       "person": tpid, "archive_holds": hn,
                                       "why_not_placed": "surname matches and the full name does "
                                                         "not; tier 3 is inadmissible for a "
                                                         "club-season placement"})
                    if norm(printed) != norm(hn) and (
                            len(norm(printed).split()) > len(norm(hn).split())
                            or len(norm(printed)) > len(norm(hn)) + 2):
                        # THE RECORD IS REGISTERED IN THE STORE THE CLAIM LANDS IN. A name
                        # claim for an independent year is written to frankford-book while its
                        # page was registered in frankford-book-ind, and 17 claims named a
                        # record their own store's table did not hold -- the same defect that
                        # raised RS-G3 from 414 to 2,448 earlier the same afternoon.
                        nsr = rec("frankford-book", loc)
                        out["frankford-book"].append({
                            **base(nsr, "surname unique among the men the archive holds on this "
                                       "club-season (tier 3) -- a name, not a placement"),
                            "subject": ["person", tpid],
                            "predicate": "fyjbook.name_as_printed", "value": printed,
                            "_beside_not_instead_of": f"the archive holds {hn!r}; both stand",
                            "_year_the_name_was_printed_for": y})
                        n["fuller_name"] += 1
                else:
                    n["lead"] += 1
                    cs = INDEX_KEY.get(y)
                    leads.append({
                        "lead_id": f"lead-fyjbook-{n['lead']:04d}",
                        "category": "player_lead_unpromoted",
                        "IS_NOT_A_PERSON": True,
                        # DECLARED, and the route refuses a kind it does not know. Ryan's
                        # ruling of 2026-09-09: a printed roster is a roster.
                        "evidence_kind": "printed_roster",
                        "name_as_printed": printed, "roster_line": row, "year": y,
                        "places_on": {"club_as_printed": "Frankford Yellow Jackets", "year": y,
                                      "club_season": cs,
                                      "_why_no_club_season": (None if cs else
                                          "the site prints a roster for this year and the club "
                                          "table holds no club-season for it: one to three names "
                                          "is not a season")},
                        # NO-MATCH EVIDENCE, PER MAN. What was looked for and what was found.
                        "no_archive_match_evidence": {
                            "searched": f"every man the archive holds on {cs or 'this year'}",
                            "exact_name_matches": 0,
                            "surname_matches": sorted(cand),
                            "why": ("no man of that name on this club-season"
                                    if not cand else
                                    "more than one held man shares the surname, so it is "
                                    "ambiguous and this route refuses it"),
                            "_nothing_can_corroborate": (ONLY_SOURCE if cs and "EARLY" in cs else None)},
                        "why": why, "source_id": SRC_ID, "source_record": sr,
                        "candidates": sorted(cand)})

    # ------------------------------------------------------------------ the games
    for y in sorted(S):
        loc = f"{y}-schedule-results"
        sr = rec("frankford-book-ind", loc)
        for i, (date, opp, result, league) in enumerate(S[y], 1):
            if league: continue                        # a league game; the archive holds those
            name = re.sub(r"^at\s+", "", opp).strip()
            venue = None
            m = re.search(r"\(([^)]*)\)\s*$", name)
            if m and m.group(1).lower().startswith("at "):
                venue = m.group(1); name = name[:m.start()].strip()
            opponents[name] += 1
            n["non_league_game"] += 1
            out["frankford-book-ind"].append({
                **base(sr),
                "subject": ["game", "IND", str(y), f"{y}-{i:02d}-frankford"],
                "predicate": "fyjbook.game_as_printed",
                "value": {"date_as_printed": date, "opponent_as_printed": opp,
                          "opponent_name_as_printed": name, "venue_note": venue,
                          "result_as_printed": result, "at_home": not opp.startswith("at "),
                          "club_as_printed": "Frankford Yellow Jackets", "year": y,
                          "league_game": False,
                          "_how_league_is_known": "the site marks a league game with an asterisk "
                                                  "on the opponent. This cell carries none."},
                "_no_club_is_created": "Ryan's ruling, 2026-09-09: report the opponent, create "
                                       "nothing. The string is held as printed."})

    # ------------------------------------------------------------------ the front office
    # Ryan, 2026-09-12 (Three). Each line on each year it prints, on that club-season, naming
    # no person. A year with no club-season is listed, never opened.
    fo_placed, fo_not_placed, fo_pairs = 0, [], 0
    for heading, line, who, yrs_printed, yrs in front_office():
        pred = FO["headings"][heading]
        body = re.search(r"\bof (?:the )?(.*)$", heading)
        for y in yrs:
            fo_pairs += 1
            if y not in KEY:
                fo_not_placed.append({"heading_as_printed": heading, "line_as_printed": line, "year": y,
                                      "why": ("the year is dark in the club table: no document names the club that year"
                                              if y in (1901, 1902, 1904, 1905) else
                                              "the club table holds no club-season for this year")})
                continue
            store = KEY[y][2]
            fsr = rec(store, "front-office")
            only = {"_the_only_source_in_existence": ONLY_SOURCE} if KEY[y][0] == "DOC:FYJ-EARLY" else None
            v = {"name_as_printed": who, "role_as_printed": heading, "line_as_printed": line,
                 "years_as_printed": yrs_printed, "club_as_printed": body.group(1) if body else None,
                 "page": "https://frankfordyellowjacketsbook.com/the-yellow-jackets/front-office/"}
            if pred == "club_staff_role":
                v.update({"_definition": STAFF_DEF, "_not_a_person": NOT_A_PERSON})
            else:
                v.update({"_definition": CAPTAIN_OR_COACH_DEF, "_not_a_person": NOT_A_PERSON})
            out[store].append({**base(fsr, None, only), "subject": cs_subject(y),
                               "predicate": pred, "value": v})
            fo_placed += 1; n[f"front office: {pred}"] += 1
            if pred != "club_staff_role": continue
            # THE MAN, UNDER THE PERSON RULE (Ryan, 2026-09-13). The club-season claim above names
            # nobody; this finds him, in order: his own promotion on this exact club-season, the one
            # staff join (staff_people.join) against the club-season's roster, a staff promotion of
            # an earlier run -- or a staff lead for promote_players to decide.
            code = KEY[y][0]; nm = norm(who)
            pid, tier = PROM.get((nm, y, code)), PROMOTED_TIER
            ev = "this site's own promotion of the same printed name on the same club-season"
            if not pid:
                tier, pid, ev = SP.join(who, ROSTER_OF(INDEX_KEY[y]))
            if not pid and STAFF_PROM.get((SP._pn(who), y, code)):
                pid, tier, ev = STAFF_PROM[(SP._pn(who), y, code)], SP.PROMOTED_TIER, "promoted from this line's staff lead"
            if pid:
                psr = rec("frankford-book", "front-office")
                out["frankford-book"].append({
                    **base(psr, tier, only), "subject": ["person", pid], "predicate": "fyjbook.staff_role_as_printed",
                    "value": {"name_as_printed": who, "role_as_printed": heading, "year": y, "club_code": code,
                              "club_as_printed": v["club_as_printed"], "line_as_printed": line, "page": v["page"]},
                    "_join_evidence": ev, "_ruled": SP.DECL["_ruled"]})
                n["front office: staff line on a person"] += 1
            else:
                leads.append(SP.lead(f"lead-fyjbook-staff-{y}-{re.sub(r'[^a-z]+', '-', nm).strip('-')}", who, heading,
                                     v["club_as_printed"], INDEX_KEY[y], y, SRC_ID, fsr, ev))
                n["front office: staff lead"] += 1
    n["front office: (line, year) placed"] = fo_placed
    n["front office: (line, year) not placed"] = len(fo_not_placed)

    # TWO PAGES, HELD NOT RESOLVED. A man printed on a roster page and on the front-office
    # page -- by forename and surname, a middle initial ignored. A LIST FOR THE REPORT, NOT A
    # JOIN: nothing here places anyone or links a person to a role.
    two_pages = []
    fo_lines = front_office()
    for y in sorted(R):
        hdr, rows = R[y]; gi = {c: i for i, c in enumerate(hdr)}
        for r in rows:
            printed = r[gi["Name"]].strip() if "Name" in gi and len(r) > gi["Name"] else ""
            t = [w for w in norm(printed).split() if w not in ("jr", "sr")]
            if len(t) < 2 or len(t[0]) < 2: continue
            pat = re.compile(rf"\b{t[0]}\b(?: [a-z]\b)? {t[-1]}\b")
            for heading, line, who, _, yrs in fo_lines:
                if pat.search(norm(who)):
                    two_pages.append({"roster_page": f"{y}-roster", "name_on_roster": printed,
                                      "position_on_roster": (r[gi["Position"]] if "Position" in gi and len(r) > gi["Position"] else None) or None,
                                      "front_office_heading": heading, "front_office_line": line,
                                      "front_office_years": yrs, "same_year": y in yrs})

    # ------------------------------------------------------------------ the stores
    reports = {}
    for store in ("frankford-book", "frankford-book-ind"):
        d = {"_what": ("frankfordyellowjacketsbook.com. " +
                       ("The NFL seasons 1924-31 and every person-scoped name claim."
                        if store == "frankford-book" else
                        "The independent seasons 1899-1923 and the non-league games.")),
             "source": {"source_id": SRC_ID, "name": "frankfordyellowjacketsbook.com",
                        "stated_by": STATED, "attribution": list(ATTRIB),
                        "acquisition": "fetched"},
             "source_records": srs[store], "claims": out[store]}
        if store == "frankford-book-ind":
            d["leads"] = leads
            d["surname_candidates_NOT_PLACED"] = candidates
            d["non_league_opponents_NOT_CREATED"] = [
                {"name_as_printed": k, "games": v} for k, v in opponents.most_common()]
            d["staff_printed_among_players"] = {"kept_as_people": staff_kept, "NOT_PLACED": staff_not_placed}
            d["front_office_lines_by_year"] = fo_pairs
            d["front_office_NOT_PLACED"] = fo_not_placed
            d["two_pages_held_not_resolved"] = two_pages
        reports[store] = d

    print("FRANKFORD BOOK   (%s)" % ("WRITE" if write else "dry run"))
    for k in sorted(n): print(f"  {k:34s} {n[k]:>7,}")
    print(f"  {'claims: frankford-book':34s} {len(out['frankford-book']):>7,}")
    print(f"  {'claims: frankford-book-ind':34s} {len(out['frankford-book-ind']):>7,}")
    print(f"  {'leads (nobody promoted)':34s} {len(leads):>7,}")
    print(f"  {'surname candidates (not placed)':34s} {len(candidates):>7,}")
    print(f"  {'non-league opponents (not created)':34s} {len(opponents):>7,}")
    if write:
        for store, d in reports.items():
            p = os.path.join(BASE, "build", store + ".json")
            json.dump(d, open(p, "w"), indent=1)
            print(f"  -> {p}  ({os.path.getsize(p):,} bytes)")
    else:
        print("  (dry run; pass --write)")
    return reports, n


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
