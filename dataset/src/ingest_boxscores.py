"""Ingest PFA boxscores, 1920-1959. 2,888 games.

A GAME IS A NEW SUBJECT: ["game", league, year, number] -- the same structured
shape as ["league_season", league, year] and ["club_season", club, year] already
in the store. The three parts come from PFA's own identifier (1926nfl001), so the
subject is the source's key rather than one invented here, and it sorts and filters
without parsing a string.

TABLES ARE FOUND BY HEADER, NEVER BY INDEX. Pages carry 13, 14 or 16 tables:
PUNTING is present on about half, and one game has no scoring plays at all. An
index-based parse would read a different table on different pages, and would read
IN MEMORIAM -- site furniture on every page -- as game data.

LINEUPS ARE PARSED BY CELL SEQUENCE, NOT BY <tr>. PFA emits rows without closing
tags, so a <tr>...</tr> regex merges two players into one row. The death lists had
the identical defect.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
# THE WHOLE CORPUS NOW LIVES IN ONE TREE, fetched 9-10 September: 17,935 pages under
# nflboxscores1/ and nflboxscores2/ with a manifest. pfa2 holds only the 2,888 older
# flattened copies, which is what this ingest used to read and why it could only ever
# see 1920-59.
CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa-boxscores")
DECL = json.load(open(os.path.join(BASE, "declarations", "pfa.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
STORE = "pfa-boxscores"                       # this ingest's own store, excluded below
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

# THE TRAILING DIGITS ARE OPTIONAL, and that is not a cosmetic change. The old pattern
# required them, so 1966aflnfl.html .. 1969aflnfl.html -- SUPER BOWLS I TO IV -- did not
# match and were skipped IN SILENCE. Measured over all 17,935 pages: those four are the
# ONLY names that do not carry a number, so the fix is complete rather than partial.
GAMEID = re.compile(r"^(\d{4})([a-z]+)(\d*)\.html$")
TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
TABLE = re.compile(r"<table.*?</table>", re.S)
PLAYER = re.compile(r'href="(/players/[^"]+)"')
CODE = re.compile(r"([a-z]{2,6}\d{4,6})")
# a club cell runs name and code together: "Columbus TigersCOL"
CLUBCELL = re.compile(r"^(.*?)([A-Z]{2,4})$")

# IN MEMORIAM is site furniture on every page. Naming it here is what keeps it out.
FURNITURE = ("In Memoriam", "Data Coverage", "NFL Boxscores", "NFL Game Logs",
             "Roster Key", "Stat Key", "NFL Game Officials", "NFL Training Camps")
# SACKS WAS MISSING AND NOBODY NOTICED, because it is on 1.4% of 1920-59 pages and this
# ingest never read a page after 1959. It is on 100% of pages from 1970 on.
STAT_TABLES = ("RUSHING", "PASSING", "RECEIVING", "INTERCEPTIONS",
               "PUNT RETURNS", "KICKOFF RETURNS", "PUNTING", "SACKS")


class BoxError(Exception):
    pass


def text(x):
    t = re.sub("<[^>]+>", " ", x)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&bull;", "•")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def verbatim(frag):
    """Tags removed WITHOUT inserting a space. The scoring play is stored as the
    source printed it, and '(<a>Red Dunn</a> kick)' must not become '( Red Dunn
    kick)' -- a claim marked verbatim has to actually be verbatim."""
    t = re.sub("<[^>]+>", "", frag)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&bull;", "\u2022")):
        t = t.replace(a, b)
    return re.sub(r"[ \t]+", " ", t).strip()


def cells(frag):
    return [text(c) for c in TD.findall(frag)]


def split_club(s):
    """'Columbus TigersCOL' -> ('Columbus Tigers', 'COL'). The same run-together
    shape as the transaction and coach club cells."""
    m = CLUBCELL.match(s or "")
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2)
    return (s or "").strip(), None


# The ten top-level table headings, measured across all 2,882 well-formed pages:
# every one of them carries these (PUNTING only when someone punted). A <th> row
# is the start of a NEW TABLE only if it is one of these. That distinction is the
# whole fix -- LINEUPS contains its own <th> sub-headings for each club and for
# Offense and Defense, so "split at every <th>" shreds a 9,133-byte lineup table
# into a 61-byte stub and took pfa.game_lineup to zero.
TOP_LEVEL = ("Score By Quarters", "Qtr", "LINEUPS", "RUSHING", "PASSING", "RECEIVING",
             "INTERCEPTIONS", "PUNTING", "PUNT RETURNS", "KICKOFF RETURNS")


def split_at_headers(t):
    """One <table> element -> the tables it actually contains, AS RAW SUBSTRINGS.

    TWO PAGES OMIT A CLOSING </table>, so one table swallows the next whole. On
    1942nfl006 the SCORING table was absorbed into 'Score By Quarters', which then
    yielded rows whose club was 'Qtr', '1', '2', '3' and '4' -- the scoring table's
    own header and quarter numbers read as clubs -- while parse_scoring found no
    'Qtr' table and the game lost all seven scoring plays. The club table
    downstream refused those five strings, which is how it surfaced.

    Repaired STRUCTURALLY, at the seam, not by recognising junk: filtering rows
    whose club is not a club would hide the same defect on a page where the
    swallowed values looked plausible, and would never give the plays back.

    IT SLICES THE ORIGINAL STRING AND NEVER REBUILDS IT. The first attempt matched
    rows with `<tr...>(.*?)</tr>` and re-serialised them, which quietly required a
    CLOSING </tr> -- and PFA omits those, the very defect parse_lineups exists to
    survive. Every LINEUPS table came back empty and a full re-run took
    pfa.game_lineup from 83,471 to 0 while reporting success.
    """
    starts = [m.start() for m in re.finditer(r"<tr", t)]
    heads = []
    for i, st in enumerate(starts):
        row = t[st:(starts[i + 1] if i + 1 < len(starts) else len(t))]
        if "<th" not in row:
            continue
        c = cells(row)
        if c and any(c[0].startswith(k) for k in TOP_LEVEL):
            heads.append(st)
    if len(heads) <= 1:
        return [t]                       # the normal case: unchanged, byte for byte
    return [t[h:(heads[i + 1] if i + 1 < len(heads) else len(t))]
            for i, h in enumerate(heads)]


def find_tables(html):
    """Every table, keyed by its first-row signature. Furniture is dropped HERE,
    once, by name -- not by position and not by being last."""
    out = collections.defaultdict(list)
    # Only a page that is MISSING a </table> can have swallowed one. Splitting is
    # skipped entirely otherwise, so 2,882 of 2,888 pages take the identical path
    # they always did.
    swallowed = len(re.findall(r"<table", html)) > html.count("</table>")
    for raw in TABLE.findall(html):
        for t in (split_at_headers(raw) if swallowed else [raw]):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
            head = cells(rows[0])[0] if rows and cells(rows[0]) else ""
            if any(head.startswith(f) for f in FURNITURE):
                continue
            out[head].append(t)
    return out


META = re.compile(r"Date:\s*(?P<date>.*?)"
                  r"Location:\s*(?P<loc>.*?)"
                  r"Venue:\s*(?P<venue>.*?)"
                  r"Attendance:\s*(?P<att>.*)$", re.S)


def parse_meta(html):
    """Date, location, venue and attendance sit in ONE cell, run together with no
    separator but their own labels. The labels are the separators.

    ATTENDANCE IS A NUMBER OR ABSENT. 'Attendance:' with nothing after it means
    the figure is not recorded -- writing 0 would assert an empty stadium."""
    for t in TABLE.findall(html):
        for c in cells(t):
            if c.startswith("Date:"):
                m = META.match(c)
                if not m:
                    return {"_unparsed_meta_cell": c}
                att = m.group("att").strip().replace(",", "")
                return {"date": m.group("date").strip(),
                        "location": m.group("loc").strip(),
                        "venue": m.group("venue").strip(),
                        "attendance": int(att) if att.isdigit() else None,
                        "attendance_state": "stated" if att.isdigit() else "not_recorded"}
    return None


def parse_quarters(tabs):
    out = []
    for t in tabs.get("Score By Quarters", []):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        hdr = cells(rows[0]) if rows else []
        for r in rows[1:]:
            c = cells(r)
            if len(c) < 2:
                continue
            club, code = split_club(c[0])
            out.append({"club": club, "club_code": code,
                        "by_quarter": dict(zip(hdr[1:], c[1:]))})
    return out


def parse_scoring(tabs):
    """The play is stored VERBATIM. 'Hal Erickson 20 pass from Red Dunn (Red Dunn
    kick)' is one string and it stays one string: the structure is not regular
    enough to split safely, and a wrong split is worse than none."""
    out = []
    for t in tabs.get("Qtr", []):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        hdr = [h.lower() for h in cells(rows[0])] if rows else []
        for r in rows[1:]:
            raw = TD.findall(r)
            c = cells(r)
            if len(c) < 3:
                continue
            club, code = split_club(c[1])
            # the men in the play are LINKED, so they resolve structurally without
            # splitting the prose into scorer / passer / kicker
            linked = [CODE.search(u).group(1) for u in PLAYER.findall(raw[2])
                      if CODE.search(u)]
            rec = {"quarter": c[0], "club": club, "club_code": code,
                   "play_as_printed": verbatim(raw[2]), "_verbatim": True,
                   "players_linked": linked,
                   "_prose_not_split": "scorer/distance/passer are not parsed out; "
                                       "the linked codes identify the men instead"}
            if len(c) > 3:
                rec["running_score"] = dict(zip(hdr[3:], c[3:]))
            out.append(rec)
    return out


TRIPLE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)


def parse_lineups(tabs):
    """Rows split on the OPENING <tr>, which survives PFA's unclosed tags, so a row
    keeps its cell count and an EMPTY CELL IS NOT LOST.

    THREE STATES, kept separable, the same distinction roster limits make between
    '-' and '' and the salary table makes for Baltimore 1952:
      stated              the source printed a value and it was read
      present_but_empty   the cell was there and the source said nothing
      cell_absent         there was no cell at all
    An empty cell must never become a placeholder word: a query for positions has
    to be unable to return one as if it were a position code.

    THE POSITION STRING IS STORED EXACTLY AS PRINTED. 'C/MG' is centre / middle
    guard; splitting or mapping it is a ruling that has not been made."""
    # A CLUB HEADING IS A CLUB THE SCORE TABLE ALSO NAMES.
    #
    # From 1946 the lineup table is sectioned Offense / Defense under each club,
    # and those section headings are single-cell rows exactly like the club
    # heading above them. `club = cs[0]` on any single-cell row therefore
    # overwrote 'Cleveland Browns' with 'Offense' and then 'Defense', and 50,675
    # of 83,471 lineup rows -- SIX IN TEN, across 1,198 games from 1946 to 1959 --
    # recorded a section where the club belongs. The archive did not know which
    # club six in ten lineup men played for.
    #
    # gate_merged_clubs M5 never saw it because all three merger years are
    # pre-1946 old-format pages, where the bug cannot fire.
    #
    # The score table names both clubs and only those two, so it is the authority
    # on what a club heading can be. A single-cell row that is not one of them is a
    # SECTION, kept as section_as_printed rather than thrown away -- offence and
    # defence is real information the page is giving us.
    out = []
    # PREFIX, not equality. The score table sometimes appends the club's code with a
    # space -- 'Philadelphia Eagles-Pittsburgh Steelers P-P' -- which split_club's
    # run-together pattern does not strip. Requiring equality made the three merged
    # club-seasons fail their own check and dropped 99 rows in 1943-44 to no club at
    # all: a fix for 1946-59 that broke exactly the years gate_merged_clubs covers.
    valid = {r["club"] for r in parse_quarters(tabs) if r.get("club")}

    def is_club(v):
        return any(sc == v or sc.startswith(v + " ") for sc in valid)

    # The ONLY true section words, measured across all 2,888 pages: 'Offense' and
    # 'Defense', 2,396 games each. Every other heading the score table does not
    # name is a STRAY CLUB from a page that leaked another game's lineups -- four
    # pages, eight rows, and three of the four are the unbalanced-<table> pages.
    # Carrying the previous club through one of those would label Pottsville's men
    # 'Chicago Bears', which is worse than admitting we do not know.
    SECTIONS = ("Offense", "Defense")
    for t in tabs.get("LINEUPS", []):
        club, section = None, None
        for frag in re.split(r"<tr\b", t)[1:]:
            cs = [text(c) for c in TD.findall(frag)]
            raws = TD.findall(frag)
            if not cs:
                continue
            if len(cs) == 1:
                v = cs[0]
                if v and v != "LINEUPS":
                    # no score table (2 games of 2,888) -> no authority to check
                    # against, so fall back to the old behaviour rather than
                    # dropping the club entirely
                    if not valid or is_club(v):
                        club, section = v, None
                    elif v in SECTIONS:
                        section = v
                    else:
                        # a club this game's score table does not name: we do not
                        # know whose lineup follows, and saying so beats guessing
                        club, section = None, v
                continue
            # a row may pack more than one man; walk it in threes from each link
            for i, raw in enumerate(raws):
                link = PLAYER.search(raw)
                if not link:
                    continue
                code = CODE.search(link.group(1))
                jer = cs[i - 2] if i >= 2 else None
                pos = cs[i - 1] if i >= 1 else None
                state = lambda v: ("cell_absent" if v is None else
                                   "present_but_empty" if not v.strip() else "stated")
                out.append({
                    "club_as_printed": club,
                    "section_as_printed": section,
                    "jersey": jer if (jer and jer.strip()) else None,
                    "jersey_state": state(jer),
                    "position_as_printed": pos if (pos and pos.strip()) else None,
                    "position_state": state(pos),
                    "name_as_printed": cs[i],
                    "pfa_code": code.group(1) if code else None,
                    "_position_is_verbatim": True,
                    "_absence_is_absence": "an empty cell is recorded as an absence "
                                           "with its state, never as a placeholder"})
    return out


WEATHER = re.compile(r"Weather:\s*(?P<w>.*?)(?:Temp:\s*(?P<t>.*?))?"
                     r"(?:Humidty:\s*(?P<h>.*?))?(?:Wind:\s*(?P<wind>.*))?$")


def parse_weather(html):
    """The weather cell, which NOTHING has ever read -- in either era.

    It is not a modern field: 1,326 of the 2,888 pages already ingested carry one,
    45.9% of 1920-59, 100% from the 1950s. `Humidty` is PFA's own spelling and is
    read as printed rather than corrected, because the label is the source's."""
    for tb in TABLE.findall(html):
        for c in cells(tb):
            if c.startswith("Weather:"):
                m = WEATHER.match(c)
                if not m:
                    return {"_unparsed_weather_cell": c}
                g = {k: (v or "").strip() or None for k, v in m.groupdict().items()}
                return {"weather_as_printed": g["w"], "temperature_as_printed": g["t"],
                        "humidity_as_printed": g["h"], "wind_as_printed": g["wind"],
                        "_label_as_printed": "Humidty", "_cell": c}
    return None


def parse_stats(tabs):
    """An EMPTY statistic table and an ABSENT one are different facts. Pre-1950
    pages print the table with no rows, which is the era; PUNTING is simply not
    present on about half the pages, which is a different thing."""
    out = {}
    for name in STAT_TABLES:
        ts = tabs.get(name)
        if ts is None:
            out[name] = {"state": "table_not_present"}
            continue
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", ts[0], re.S)
        hdr = cells(rows[0]) if rows else []
        body = [cells(r) for r in rows[1:] if any(cells(r))]
        # A CLUB HEADING IS NOT A STATISTIC LINE. Pre-1950 pages print the table
        # and the two club names with every value cell empty -- that is the era,
        # and counting the club rows as content would report statistics the source
        # does not have. A stat line carries a value in some column after the first.
        stat_lines = [r for r in body if any(x.strip() for x in r[1:])]
        state = ("table_not_present" if not ts else
                 "present_with_statistics" if stat_lines else
                 "present_but_no_statistics_recorded")
        out[name] = {"state": state, "columns": hdr,
                     "rows": stat_lines,
                     "club_rows_only": len(body) if not stat_lines else 0,
                     "_empty_is_the_era_not_a_parse_failure": not stat_lines}
    return out


def person_map():
    """PFA code -> archive person, READ FROM THE PUBLISHED MODEL.

    WHY THIS EXISTS. The old map was two JSON files in a session scratchpad under
    /tmp, and the session is gone. This ingest could not run at all, which means the
    106,744 claims it had already written could not be reproduced -- the archive's own
    rule about literal /tmp paths, broken inside a committed file, exactly as it was in
    ingest_officials.py.

    WHY THIS IS NOT A DECIDER READING ITS OWN OUTPUT. The question here is "which
    archive person is this PFA page?", answered on a SOURCE-NATIVE key -- the same
    question promote_players.py answers when it gives a promoted man his own id back.
    It is not "is this man already in the archive?", which is the question that must
    never see this ingest's own people. The guard is structural and it is asserted
    below: this ingest's store is excluded, and it carries no player-page source record
    to contribute in any case.

    AN AMBIGUOUS CODE IS REFUSED, NEVER PICKED. Two codes -- stan03000 and cham00800 --
    reach two archive persons apiece, each pair sharing a name and almost certainly an
    unmerged duplicate. Choosing one silently is the tier-2 guess this archive has
    already been bitten by. They are refused and counted."""
    import sqlite3
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    seen = collections.defaultdict(set)
    for pid, sr in conn.execute(
            "select person, source_record from claim where person is not null "
            "and store != ? and source_record like '%players/%.html%'", (STORE,)):
        m = CODE.search(str(sr))
        if m:
            seen[m.group(1)].add(pid)
    # the guard, checked rather than asserted in a comment
    self_ref = conn.execute("select count(*) from claim where store = ? "
                            "and source_record like '%players/%.html%'", (STORE,)).fetchone()[0]
    if self_ref:
        raise BoxError(f"{self_ref} claims in this ingest's own store carry a player-page "
                       f"source record; the map would be reading its own output")
    cmap = {c: next(iter(v)) for c, v in seen.items() if len(v) == 1}
    global _AMBIGUOUS
    _AMBIGUOUS = {c: sorted(v) for c, v in seen.items() if len(v) > 1}
    return cmap


_AMBIGUOUS = {}


def claim(sr, subject, pred, value, **extra):
    if subject is None or value in (None, "", [], {}):
        raise BoxError("a claim needs a subject and a non-empty value")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": subject, "predicate": pred,
            "value": value, "kind": "observed", "observed_at": "fetched-2026-09", **extra}


def main(write=True):
    cmap = person_map()
    claims, leads, unparsed = [], [], []
    n = collections.Counter()
    resolved_by_decade = collections.Counter()
    links_by_decade = collections.Counter()
    posvocab = collections.Counter()
    games = 0
    pages = []
    for dn in ("nflboxscores1", "nflboxscores2"):
        d = os.path.join(CACHE, dn)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            m = GAMEID.match(fn)
            if m:
                pages.append((dn, fn, m))
    for dn, fn, m in sorted(pages, key=lambda x: (x[2].group(1), x[2].group(2),
                                                  int(x[2].group(3) or 0))):
        year, league, num = int(m.group(1)), m.group(2).upper(), m.group(3)
        sr = f"{SRC_ID}#{dn}/{fn}"
        if not num:
            # THE FOUR INTER-LEAGUE CHAMPIONSHIPS -- Super Bowls I to IV. PFA gives
            # them no game number, and the old pattern therefore dropped all four IN
            # SILENCE. Ryan ruled 2026-09-10 that they go in under a DECLARED token:
            # AFLNFL is a competition between two leagues and not a league, declared in
            # clubs.json LEAGUE_TOKENS_THAT_ARE_NOT_LEAGUES with what it asserts and
            # what it refuses. THE NUMBER IS 1 BECAUSE THERE WAS ONE SUCH GAME A SEASON
            # -- it is the source's own arithmetic, not an invented ordinal.
            num = 1
            n["inter_league_championship"] += 1
        num = int(num)
        h = open(os.path.join(CACHE, dn, fn), encoding="utf-8", errors="replace").read()
        tabs = find_tables(h)
        subj = ["game", league, year, num]
        games += 1
        meta = parse_meta(h)
        if not meta or "_unparsed_meta_cell" in (meta or {}):
            unparsed.append({"game": fn, "what": "meta cell", "raw": (meta or {}).get(
                "_unparsed_meta_cell", "no Date: cell found")})
        else:
            claims.append(claim(sr, subj, "pfa.game", {
                "pfa_game_id": fn.replace(".html", ""),
                "league": league, "year": year, "number": num, **meta}))
            n["game"] += 1
        w = parse_weather(h)
        if w:
            claims.append(claim(sr, subj, "pfa.game_weather", w)); n["weather"] += 1
        q = parse_quarters(tabs)
        if q:
            claims.append(claim(sr, subj, "pfa.game_score_by_quarter", q)); n["score"] += 1
        for p in parse_scoring(tabs):
            claims.append(claim(sr, subj, "pfa.scoring_play", p)); n["scoring_play"] += 1
        dec = (year // 10) * 10
        lus = parse_lineups(tabs)
        if not lus:
            # THE THIRD STATE at game level: no LINEUPS table, or one with no men.
            # Distinct from a game whose men merely failed to resolve.
            claims.append(claim(sr, subj, "pfa.game_lineup_absent",
                                {"state": "no_lineups_table" if "LINEUPS" not in tabs
                                          else "table_present_no_players",
                                 "_not_a_parse_failure": True}))
            n["lineup_absent"] += 1
        for L in lus:
            posvocab[L["position_as_printed"]] += 1
            links_by_decade[dec] += 1
            pid = cmap.get(L["pfa_code"])
            if pid:
                resolved_by_decade[dec] += 1
                claims.append(claim(sr, ["person", pid], "pfa.game_lineup",
                                    {**L, "game": subj})); n["lineup"] += 1
            else:
                leads.append({"lead_id": f"lead-box-{len(leads)+1:06d}",
                              "category": "lineup_code_unresolved",
                              "pfa_code": L["pfa_code"],
                              "name_as_printed": L["name_as_printed"],
                              "game": subj, "source_record": sr,
                              "IS_NOT_A_PERSON": True,
                              "why": "no archive person resolves to this PFA code"})
        st = parse_stats(tabs)
        claims.append(claim(sr, subj, "pfa.game_statistics", st)); n["statistics"] += 1
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           "subject_shape": {"game": ["game", "<league>", "<year>", "<number>"],
                             "_why": "PFA's own identifier (1926nfl001) split into its "
                                     "three parts, so the subject is the source's key and "
                                     "sorts without string parsing"},
           "claims": claims, "leads": leads, "unparsed": unparsed,
           "counts": {"games": games, "claims": len(claims), "leads": len(leads),
                      "by_predicate": dict(n),
                      "lineup_links_by_decade": dict(sorted(links_by_decade.items())),
                      "lineup_resolved_by_decade": dict(sorted(resolved_by_decade.items())),
                      "position_vocabulary": dict(posvocab.most_common()),
                      "unparsed": len(unparsed)}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-boxscores.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv); c = o["counts"]
    print(f"  games {c['games']:,}   claims {c['claims']:,}   leads {c['leads']:,}   "
          f"unparsed {c['unparsed']}")
    for k, v in sorted(c["by_predicate"].items(), key=lambda x: -x[1]):
        print(f"     {k:16s} {v:,}")
    print("  lineup links resolved by decade:")
    for d in sorted(c["lineup_links_by_decade"]):
        t = c["lineup_links_by_decade"][d]; r = c["lineup_resolved_by_decade"].get(d, 0)
        print(f"     {d}s  {r:6,} of {t:6,}  {r*100.0/t:5.1f}%")
    print(f"  distinct two-way position strings: {len(c['position_vocabulary'])}")
