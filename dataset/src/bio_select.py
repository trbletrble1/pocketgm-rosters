"""SELECTION LAYER. Decides WHAT a biography says and in what order. No English here.

Output is a Facts object: an ordered list of typed fact records, each tagged with a
slot (lead / body / close), a score, and raw values. bio_write.py turns it into
prose. Moving a fact out of the prose and into a panel is a change HERE only.

THREE SLOTS, RULED.
  LEAD   whichever of three scores is highest FOR THIS MAN:
           career shape  -- distance from the typical career
           distinction   -- his best season's percentile among function-mates
           salience      -- the floor: the statistic his position records
  BODY   clubs, seasons, and at most one or two numbers that matter
  CLOSE  a human fact where one exists; where none exists the bio ENDS
  PANEL  identity, as structured data beside the prose and never inside it:
         birth date, birth place, hometown, college, high school, height,
         weight, draft, position. Ryan's ruling 2026-09-06: the prose carries
         only what says something; the panel carries who he is. Every panel
         value names its source, and a field two sources disagree on lists
         both values. Nothing is picked.

ONE SCALE. Every score is a distance-from-typical in [0, 1]:
  shape        = max over detected shapes of (2 * |percentile - 0.5|) for career
                 length, or a fixed distance for a categorical shape (one club,
                 one game, crossed leagues, war gap, played-then-coached,
                 defunct club).
  distinction  = the best season percentile among men of the same function in
                 the same league and year (>= 10 comparators), used as a lead
                 only at >= 0.90.
  salience     = capped at 0.45, so it never outranks a real shape or a real
                 distinction. It is the floor, by ruling.

SALIENCE IS DERIVED, NOT INVENTED. For each position code and decade, the column
the men who held it most often record (share >= 0.40 of their seasons), by the
project's own co-occurrence method in derive_position_function.py. The held file
carries an empty `codes` map because its column names predate the table.column
keys, so the derivation runs here. Codes with no column at any share are "no
salient stat" and lead from shape.

DISAGREEMENTS ARE NOT SILENTLY RESOLVED. A birth date disputed by PFA or
nflverse is listed in the panel with every value and its source.

A 1940s GUIDE'S OWN PROSE WINS THE CLOSE OUTRIGHT when it exists (Ryan's ruling
2026-09-06). notes_excerpt() is therefore determined: it walks the block for
the first run of sentences that are prose and not OCR wreckage, instead of
giving up when the first sentence is a table row or a torn word.
"""
import os, re, sys, json, collections, statistics
import readings

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def required(*parts):
    """Resolve a load-bearing input under BASE, and refuse to run without it.

    The bio prints are held to a byte-exact baseline by gate_coach_runs R4, so an
    input that goes missing does not degrade the prose -- it silently rewrites it.
    Missing is therefore fatal here, never skipped.

    This replaced a read from a session scratchpad: the path carried a session id,
    the read was guarded by os.path.exists, and when the archive moved machines the
    file was simply not there. Every PFA fact -- 2,249 military-service, 4,232 death
    dates, 4,166 death places -- left the bios without a word of complaint. The same
    claims were in build/pfa-pre1950.json, byte-identical, the whole time.
    """
    fp = os.path.join(BASE, *parts)
    if not os.path.exists(fp):
        raise SystemExit("bio_select: required input missing: %s" % os.path.normpath(fp))
    return fp


IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
CLUBS = IDX.pop("_clubs", {})

DEFUNCT_LEAGUES = {"AAFC", "APFA", "WFL", "USFL", "USFL2", "XFL", "WLAF", "UFL", "UFL2", "AAF", "AFL"}
# a league that changed its name is the same league: APFA became the NFL in 1922
LEAGUE_FAMILY = {"APFA": "NFL", "USFL2": "USFL", "UFL2": "UFL"}


def families(leagues):
    return list(dict.fromkeys(LEAGUE_FAMILY.get(l, l) for l in leagues if l != "COACHES"))
LEAGUE_NAME = {"NFL": "the NFL", "APFA": "the APFA", "AAFC": "the AAFC", "AFL": "the AFL",
               "CFL": "the CFL", "WFL": "the WFL", "USFL": "the USFL", "USFL2": "the USFL",
               "XFL": "the XFL", "WLAF": "the World League", "UFL": "the UFL", "UFL2": "the UFL",
               "AAF": "the AAF"}

# candidate salient columns, in the project's precedence order, keyed table.column
SALIENT_CANDIDATES = ["defense_and_fumbles.Tackle", "receiving.No.", "passing.Comp",
                      "kicking.FGM", "punting.No.", "rushing.Yds", "interceptions.No.",
                      "total_scoring.Points"]
# the verb-bearing measure a column stands for (English lives in bio_write; this is a key)
MEASURE = {"defense_and_fumbles.Tackle": "tackles", "receiving.No.": "receptions",
           "passing.Comp": "completions", "kicking.FGM": "field_goals",
           "punting.No.": "punts", "rushing.Yds": "rushing_yards",
           "interceptions.No.": "interceptions", "total_scoring.Points": "points"}
# below these a total is noise, not a fact worth a sentence (Ryan: better nothing)
FLOOR = {"defense_and_fumbles.Tackle": 20, "receiving.No.": 10, "passing.Comp": 25,
         "kicking.FGM": 5, "punting.No.": 20, "rushing.Yds": 150, "interceptions.No.": 5,
         "total_scoring.Points": 20}
# a companion number that belongs with the measure (yards with receptions etc.)
COMPANION = {"receiving.No.": "receiving.Yds", "passing.Comp": "passing.Yds",
             "rushing.Yds": "rushing.TDs", "interceptions.No.": "interceptions.Yds"}


def num(v):
    try:
        return float(str(v).replace(",", "").replace("&nbsp;", "").strip())
    except Exception:
        return None


def clean(v):
    if v is None: return None
    t = str(v).strip().strip(",")
    if t.lower() in ("none", "null", "", "n/a", "-"): return None
    t = re.sub(r"\bNone\b", "", t).strip().strip(",").strip()
    return t or None


def club_name(code, year):
    """The archive's name for the club a season-key token names that year.

    FROM THE CLUB TABLE, ruled by Ryan 2026-09-09 after Les Dodson's bio read "two
    games with the PFA:WIL in 1941" -- a club the table names perfectly well.

    WHY THE TABLE AND NOT THE MAP. `CLUBS` is the index's `_clubs`, and it is built
    from ONE STORE: build/club-names.json, StatsCrew's roster-page titles. 3,666
    claims, 321 tokens, and NOT ONE PFA code. It is short because its population is
    narrow, not because anything went wrong. It also answers a different question --
    its own note says "from the roster page title; a name for THIS season, not a
    franchise identity" -- where a bio wants the archive's name for the club that
    year. Measured 2026-09-09: the club table names all 3,666 of the map's entries
    and agrees with every one, and names 11,002 more season keys the map cannot.

    WHY NOT WIDEN THE MAP. build_person_index writes `_clubs`, and build_clubs is a
    step in the chain that build_person_index triggers -- so a map widened from the
    club table would be built from the table of the PREVIOUS run, one generation
    stale, which is the failure this archive has already had twice this week. And
    bio_select ALREADY loads the club table: `club_id()` resolves tokens through it.
    A second, staler answer to one question is the duplicate-implementation defect.

    WHAT MAKES THIS STABLE, given that a derived club id moved twice this week: this
    DERIVES NOTHING. It looks a token up in the table and reads the name the table
    holds for that year. No id is minted, no name is composed. If the table changes,
    the name changes with it, which is correct -- the table is the record.

    A TOKEN THE TABLE CANNOT NAME KEEPS ITS OWN TEXT, and that is deliberate. 2,018
    season keys are on club-seasons the table does not cover: 660 where it holds the
    club but no name for that year (almost all 2025, past the table's last held
    season), 809 where the token places at another year but not this one (PFA:AMS in
    1996, before its 1998 code span), 549 it never places. Naming those would assert
    a name the archive does not hold. gate_bio_club_names.py counts them.

    `_clubs` STILL EXISTS and is still written: normalise_club_keys.py reads it to
    ask whether a token is already a code that year, which is a different question
    from what a club was called."""
    return club_name_or_none(code, year) or code


def club_name_or_none(code, year):
    """As `club_name`, but None where the archive holds NO name for that club-season.

    The difference matters to the Namer, which decides a club was RENAMED by finding
    two different names across a man's years. With the token as a fallback, a year the
    table cannot name looked like a new name: "the Carolina Panthers, later the CAR",
    because the table's names stop at 2024 and he coached into 2025. Unknown is not a
    different name, and only this function can say so."""
    r = _club_table().resolve(code, year, None, source="season_key")
    if r:
        nm = _club_table().name_for(r[0], year)
        if nm: return nm
    return CLUBS.get(f"{code}|{year}")


def pfield(p, k):
    v = (p.get("person") or {}).get(k)
    if isinstance(v, list): v = v[0] if v else None
    return clean(v)


def seasons(p):
    """Every season a man holds, playing and coaching, each saying which it is.

    WHICH DICT IT CAME FROM IS THE ANSWER. Ruled 2026-09-09: a coaching season lives
    in `coaching_seasons` and a playing one in `seasons`, decided by the claim's
    PREDICATE when the index is built. This used to read `seasons` alone and guess
    with `bool(st.get("role_title")) and not codes` -- which saw only the stores that
    write `role_title`, missed every PFA coaching season, and so told Jack Pardee's
    bio that he played thirty-two seasons for seven clubs. Four of the seven he only
    coached; he played fifteen, for two."""
    out = []
    for coaching, src in ((False, p.get("seasons") or {}), (True, p.get("coaching_seasons") or {})):
        for k, d in src.items():
            lg, yr, club = k.split("|")
            m = re.search(r"(\d{4})", yr)
            if not m: continue
            st = (d.get("stint") or {}) if isinstance(d, dict) else {}
            pos = st.get("position")
            codes = []
            for one in (pos if isinstance(pos, list) else [pos]):
                if isinstance(one, dict): one = one.get("code")
                if one: codes.append(str(one))
            out.append({"league": lg, "year": int(m.group(1)), "club": club, "stint": st,
                        "stats": (d.get("stats") or {}) if isinstance(d, dict) else {},
                        "codes": codes, "coaching": coaching})
    return sorted(out, key=lambda s: (s["year"], s["club"]))


# ------------------------------------------------------------------ derived tables
class Tables:
    """Everything that needs the whole population: salience per (code, decade),
    career-length percentiles, per-season comparators for distinction, and the
    auxiliary sources (PFA, nflverse, guides)."""

    def __init__(self):
        # A COACHING-ONLY MAN IS A MAN. Since 2026-09-09 his seasons are in
        # `coaching_seasons`, so `p.get("seasons")` alone dropped every one of them out
        # of the corpus -- the comparator pools, the salience map, and the coaching-only
        # bios, which printed nothing at all. The gate that caught it was a baseline
        # going from 37 lines to 0.
        self.people = {g: p for g, p in IDX.items()
                       if (p.get("seasons") or p.get("coaching_seasons")) and p.get("name")}
        self._salience()
        self._club_leagues()
        self._length_percentiles()
        self._comparators()
        self._aux()

    # salience: position code x decade -> column, by co-occurrence share
    def _salience(self):
        n = collections.Counter(); hit = collections.defaultdict(collections.Counter)
        for g, p in self.people.items():
            for s in seasons(p):
                if s["coaching"] or not s["stats"]: continue
                dec = (s["year"] // 10) * 10
                for c in s["codes"]:
                    for key in (c, f"{c}|{dec}"):
                        n[key] += 1
                        for col in SALIENT_CANDIDATES:
                            v = num(s["stats"].get(col))
                            if v and v > 0: hit[key][col] += 1
        self.salient = {}; self.qualifying = {}
        for key, cnt in n.items():
            if cnt < 15: continue
            shares = {col: hit[key][col] / cnt for col in SALIENT_CANDIDATES}
            q = [c for c in SALIENT_CANDIDATES if shares[c] >= 0.40]
            self.qualifying[key] = q
            # the column these men record MOST OFTEN, not the first in a list
            self.salient[key] = max(q, key=lambda c: shares[c]) if q else None
        codes_seen = {k for k in n if "|" not in k and n[k] >= 15}
        self.codes_without_salient = sorted(c for c in codes_seen
                                            if not any(self.salient.get(k) for k in self.salient
                                                       if k == c or k.startswith(c + "|")))

    def salient_for(self, code, year):
        dec = (year // 10) * 10
        if f"{code}|{dec}" in self.salient: return self.salient[f"{code}|{dec}"]
        return self.salient.get(code)

    def qualifying_for(self, code, year):
        dec = (year // 10) * 10
        if f"{code}|{dec}" in self.qualifying: return self.qualifying[f"{code}|{dec}"]
        return self.qualifying.get(code, [])

    def _club_leagues(self):
        """(club, year) -> league, from the CLUB TABLE. A coaching season is keyed
        COACHES|yYYYY|CLUB and carries no league, so a coaching career cannot be said
        to cross leagues without this. Until patch 3 of the club job this was read
        from the archive's own playing keys, which left 29 coaching club-seasons
        without a league; the table answers 12 of those (NFL Europe, the COFL and
        ACFL, two CFL years) and agrees with the playing keys on every one of the
        4,725 it answered before. The rest are tokens the table refuses and counts."""
        self._table = _club_table(); self._league_cache = {}

    def league_of(self, club, year):
        k = (club, int(year))
        if k not in self._league_cache:
            r = self._table.resolve(club, int(year), None, source="season_key")
            self._league_cache[k] = self._table.league_for(r[0], int(year)) if r else None
        return self._league_cache[k]

    def _length_percentiles(self):
        lengths = []
        for p in self.people.values():
            ys = {s["year"] for s in seasons(p) if not s["coaching"]}
            if ys: lengths.append(len(ys))
        lengths.sort()
        self.median_seasons = statistics.median(lengths)
        self._len_sorted = lengths
        cl = []
        for p in self.people.values():
            # the coaching dict, not a league token. Before 2026-09-09 this counted only
            # the COACHES-keyed stores, so the median coaching career was measured over
            # a third of the coaching seasons the archive holds.
            ys = {k.split("|")[1] for k in (p.get("coaching_seasons") or {})}
            if ys: cl.append(len(ys))
        cl.sort()
        self._coach_len_sorted = cl
        self.median_coaching_seasons = statistics.median(cl) if cl else 0

    def coach_length_percentile(self, n):
        """Distance from the typical COACHING career, which is not the typical
        playing one: the median coaching career is three seasons and the longest
        is forty-six."""
        import bisect
        L = self._coach_len_sorted
        if not L: return 0.5
        lo = bisect.bisect_left(L, n); hi = bisect.bisect_right(L, n)
        return (lo + hi) / 2 / len(L)

    def length_percentile(self, n):
        import bisect
        L = self._len_sorted
        lo = bisect.bisect_left(L, n); hi = bisect.bisect_right(L, n)
        return (lo + hi) / 2 / len(L)

    # comparators: (league, year, column) -> sorted values among function-mates
    def _comparators(self):
        pools = collections.defaultdict(list)
        for g, p in self.people.items():
            for s in seasons(p):
                if s["coaching"] or not s["stats"]: continue
                cols = set()
                for c in s["codes"]: cols.update(self.qualifying_for(c, s["year"]))
                for col in cols:
                    v = num(s["stats"].get(col))
                    if v and v > 0: pools[(s["league"], s["year"], col)].append(v)
        self.pools = {k: sorted(v) for k, v in pools.items()}

    def percentile(self, league, year, col, value):
        import bisect
        L = self.pools.get((league, year, col))
        if not L or len(L) < 10: return None, 0
        below = bisect.bisect_left(L, value)
        return below / len(L), len(L)

    def _aux(self):
        self.pfa = collections.defaultdict(dict); self.disputed = {}
        d = json.load(open(required("build", "pfa-pre1950.json")))
        for c in d.get("claims") or []:
            s = c.get("subject"); pid = s[1] if isinstance(s, list) and len(s) > 1 else None
            if not pid: continue
            pred = (c.get("predicate") or "").replace("pfa.", "")
            if pred in ("military_service", "death_date", "death_place", "birth_place",
                        "high_school", "height", "weight", "college", "draft_selection", "draft"):
                self.pfa[pid].setdefault(pred, c.get("value"))
        for x in d.get("disagreements") or []:
            if x.get("field") == "birth_date":
                s = x.get("subject"); pid = s[1] if isinstance(s, list) else None
                if pid: self.disputed.setdefault(pid, []).append(("pfa", x.get("pfa"), x.get("statscrew")))
        d = json.load(open(required("build", "nflverse-rosters.json")))
        for x in d["disagreements"]["birth_date_vs_statscrew"]:
            self.disputed.setdefault(x["person"], []).append(("nflverse", x["nflverse"], x["statscrew"]))
        # draft: PFR listings and nflverse players.csv, both already resolved to persons
        self.draft = collections.defaultdict(list)
        for fn, src in (("pfr-drafts.json", "Pro-Football-Reference"), ("nflverse-draft.json", "nflverse")):
            for c in json.load(open(required("build", fn))).get("claims") or []:
                s_ = c.get("subject"); pid = s_[1] if isinstance(s_, list) and len(s_) > 1 else None
                if pid: self.draft[pid].append((src, c.get("value")))
        self.guide = collections.defaultdict(dict); self.notes = {}
        d = json.load(open(required("build", "guide-pre1950-delimited.json")))
        for r in d["runs"].values():
            for gd in r["guides"].values():
                title = gd["source"]["name"]; year = gd["source"]["places_on"]["year"]
                for c in gd["claims"]:
                    pid = c["subject"][1]; pred = c["predicate"]
                    if pred.startswith("guide.NOTES"):
                        self.notes.setdefault(pid, {"text": c["value"], "guide": title, "year": year})
                    else:
                        self.guide[pid].setdefault(pred.replace("guide.", ""), c["value"])


# ------------------------------------------------------------------ per-person facts
def fact(kind, slot, score=0.0, **v):
    return {"kind": kind, "slot": slot, "score": round(score, 3), **v}


def career(p):
    ss = seasons(p)
    played = [s for s in ss if not s["coaching"]]
    coached = [s for s in ss if s["coaching"]]
    yrs = sorted({s["year"] for s in played})
    c = {"played": played, "coached": coached, "years": yrs,
         "leagues": [l for l in dict.fromkeys(s["league"] for s in played)],
         "clubs": [], "games": None, "gaps": []}
    seen = []
    for s in played:
        key = (s["club"], s["league"])
        if not seen or seen[-1] != key: seen.append(key)
    c["clubs"] = seen
    gs = [s["stint"].get("games_played") for s in played]
    if any(g not in (None, "") for g in gs):
        c["games"] = int(sum(num(g) or 0 for g in gs))
    for a, b in zip(yrs, yrs[1:]):
        if b - a > 1: c["gaps"].append((a, b))
    return c


def coach_career(T, c):
    """The coaching career as its own career: years, clubs in order, the leagues it
    ran through, and its gaps. Nothing here is a lesser version of a playing
    career; it is the career."""
    ss = sorted(c["coached"], key=lambda s: s["year"])
    if not ss: return None
    yrs = sorted({s["year"] for s in ss})
    clubs = []
    for s in ss:
        if not clubs or clubs[-1][0] != s["club"]: clubs.append((s["club"], s["year"]))
    lgs = [l for l in (T.league_of(s["club"], s["year"]) for s in ss) if l]
    return {"years": yrs, "clubs": clubs, "leagues": list(dict.fromkeys(lgs)),
            "unplaced_clubs": sorted({s["club"] for s in ss if not T.league_of(s["club"], s["year"])}),
            "gaps": [(a, b) for a, b in zip(yrs, yrs[1:]) if b - a > 1],
            "seasons": ss}


def coaching_shapes(T, cc, co):
    """The career shapes, run over a COACHING career. Measured 2026-09-06 on the 347
    coaching-only men the archive holds:

      long_career, one_club, single_season and war_gap fire exactly as they do for
        a playing career, on the coaching years -- 61 men coached ten seasons or
        more, 26 spent five or more at a single club, 86 coached one season, 3 have
        a gap over the war.
      crossed_leagues needs the club-to-league map above, because a coaching season
        key carries no league. With it, 60 of the 347 cross a league family, which
        is the shape that catches a man moving from the CFL to the NFL.
      played_then_coached cannot apply, and is not forced.
      single_game, distinction and salience cannot apply: a coaching stint records
        no games and no statistics, so there is nothing to be distinguished on.
    """
    out = []
    n = len(cc["years"])
    dist = 2 * abs(T.coach_length_percentile(n) - 0.5)
    if n == 1:
        out.append(fact("coached_one_season", "lead", max(dist, 0.70), year=cc["years"][0],
                        club=cc["clubs"][0][0]))
    if n >= 10:
        out.append(fact("coached_long", "lead", max(dist, 0.85), seasons=n,
                        first=cc["years"][0], last=cc["years"][-1]))
    if n >= 5 and len({k[0] for k in cc["clubs"]}) == 1:
        out.append(fact("coached_one_club", "lead", max(dist, 0.80) + 0.01, seasons=n,
                        club=cc["clubs"][0][0], first=cc["years"][0], last=cc["years"][-1]))
    if len(families(cc["leagues"])) >= 2:
        out.append(fact("coached_across_leagues", "lead", 0.78, leagues=families(cc["leagues"])))
    for a, b in cc["gaps"]:
        missing = set(range(a + 1, b))
        # a gap must BE the war, not merely contain it. Joe Bach was away from 1937
        # to 1951 and calling that a war gap is a story the archive did not tell.
        if missing & {1942, 1943, 1944, 1945} and missing <= {1941, 1942, 1943, 1944, 1945, 1946}:
            out.append(fact("coached_war_gap", "lead", 0.88, before=a, after=b))
    for code, yr in cc["clubs"]:
        lg = T.league_of(code, yr)
        # for a coaching career only a DEFUNCT LEAGUE is a shape. The player-side
        # test also counts an NFL club absent from the 2024 map, but that catches
        # relocations: it would call Dennis Allen's Oakland Raiders defunct and then
        # lead with "he coached in the NFL", which says nothing.
        if lg in DEFUNCT_LEAGUES:
            out.append(fact("coached_defunct_club", "lead", 0.62, club=code, league=lg, year=yr))
            break
    return out


def shapes(T, c, p):
    """Categorical shapes, each with a distance-from-typical."""
    out = []
    n = len(c["years"])
    if not n: return out
    pct = T.length_percentile(n)
    dist = 2 * abs(pct - 0.5)
    if n == 1 and (c["games"] is not None and c["games"] <= 2):
        out.append(fact("single_game", "lead", 0.97, games=c["games"], season=c["played"][0]))
    elif n == 1:
        out.append(fact("single_season", "lead", max(dist, 0.75), season=c["played"][0]))
    if n >= 10:
        out.append(fact("long_career", "lead", max(dist, 0.85), seasons=n,
                        first=c["years"][0], last=c["years"][-1]))
    if n >= 5 and len({k[0] for k in c["clubs"]}) == 1:
        out.append(fact("one_club", "lead", max(dist, 0.80) + 0.01, seasons=n,
                        club=c["clubs"][0][0], first=c["years"][0], last=c["years"][-1]))
    if len(families(c["leagues"])) >= 2:
        out.append(fact("crossed_leagues", "lead", 0.78, leagues=families(c["leagues"])))
    for a, b in c["gaps"]:
        missing = set(range(a + 1, b))
        if missing & {1942, 1943, 1944, 1945}:
            out.append(fact("war_gap", "lead", 0.88, before=a, after=b))
    if c["played"] and c["coached"]:
        cy = sorted({s["year"] for s in c["coached"]})
        if cy and cy[-1] >= c["years"][-1]:
            out.append(fact("played_then_coached", "lead", 0.82, first_coach=cy[0],
                            last_coach=cy[-1], coach_seasons=len(cy),
                            coaching=coaching(c), clubs=coach_clubs(c)))
    for code, lg in c["clubs"]:
        if lg in DEFUNCT_LEAGUES or (lg == "NFL" and not CLUBS.get(f"{code}|2024")):
            yr = next(s["year"] for s in c["played"] if s["club"] == code)
            out.append(fact("defunct_club", "lead", 0.62, club=code, league=lg, year=yr))
            break
    return out


def _is_code(tok, year):
    return f"{tok}|{year}" in CLUBS


def _club_table():
    """The club table (build/clubs.json) is REQUIRED here: coaching runs group on
    its club id. Missing table = loud failure, not a fallback to the old code test."""
    global _CLUB_TABLE
    try: return _CLUB_TABLE
    except NameError: pass
    from clubs import Clubs, TABLE
    if not os.path.exists(TABLE): raise SystemExit("bio_select: build/clubs.json is missing; run src/build_clubs.py --write")
    _CLUB_TABLE = Clubs(); return _CLUB_TABLE


def club_id(tok, year):
    """The club a coaching-season token names that year, from the table. A token the
    table cannot place keeps its own text as its key and is counted by the table's
    census, which gate_coach_runs prints."""
    r = _club_table().resolve(tok, year, None, source="season_key")
    return r[0] if r else f"?{tok}"


_CD = {}
def coaching_decl():
    """declarations/coaching-seasons.json -- where a role is read from, and which
    printed positions mean HEAD COACH. Read, never typed here."""
    if not _CD:
        _CD["d"] = json.load(open(os.path.join(BASE, "declarations", "coaching-seasons.json")))
    return _CD["d"]


def roles_on(stint):
    """Every role this stint states, EXACTLY as printed, in declaration order.

    `role_title` carries it directly; PFA's coaching predicates carry a dict whose
    `position_as_printed` is the role. Reading only the first left PFA's 1,046
    distinct printed positions -- 'Defensive Coordinator', 'Assistant Strength and
    Conditioning', 'HEAD COACH' -- entirely unread, on 3,356 men."""
    out = []
    for pred in coaching_decl()["roles"]["role_predicates"]:
        v = stint.get(pred)
        if isinstance(v, dict): v = v.get("position_as_printed")
        if isinstance(v, str) and v.strip(): out.append(v.strip())
    return out


def is_head_position(role):
    """Does this printed position say he WAS THE HEAD COACH? The first slash-separated
    segment, upper-cased, against the declared list and nothing else -- so
    'HEAD COACH/Offensive Coordinator' is one and 'Assistant Head Coach' is not."""
    if not isinstance(role, str): return False
    return role.split("/")[0].strip().upper() in set(
        coaching_decl()["roles"]["head_coach_positions"]["first_segments"])


def head_standing(stint):
    """Was he THE HEAD COACH that season? The ONE implementation, shared with
    src/gate_coach_runs.py, which used to carry its own copy and reported 727 men
    losing a year the moment this one changed. `is_head_coach` is the Coaching Tree's
    predicate; PFA says it in `position_as_printed`."""
    return bool(stint.get("is_head_coach")) or any(is_head_position(r) for r in roles_on(stint))


def coach_runs(c):
    """Coaching seasons as RUNS: contiguous years at one CLUB with the same
    standing, head or assistant. The club is the table's club id, not the token.

    ONE YEAR IS ONE JOB even where the archive holds it twice. The merge of
    2026-09-06 gave these men both halves of a career, and the two halves spell a
    club differently: Marv Levy's 1986 is held as both COACHES|y1986|BUF and
    COACHES|y1986|Buffalo Bisons, because Coaching Tree calls Buffalo's 1986 club
    the Bisons and the archive calls it the Bills. Until the club table both
    spellings were kept apart by preferring a code to a name; now both resolve to
    club-buffalo-bills-1960 and are one job because they are one club. Two
    distinct clubs in one year is a real split season and both are kept.

    The run's `club` is still a token for the writer: the code where the year
    offers one, else the printed token of the run's first year."""
    by_year = collections.defaultdict(lambda: collections.defaultdict(list))
    for s in c["coached"]:
        # HEAD STANDING IS READ FROM WHAT THE SOURCE PRINTS, not from one predicate.
        # `is_head_coach` is the Coaching Tree's; PFA says it in `position_as_printed`,
        # and 706 men PFA prints as HEAD COACH were read as assistants with no role.
        by_year[(s["year"], head_standing(s["stint"]))][club_id(s["club"], s["year"])].append(s)
    rows = []
    for (year, head), clubs in sorted(by_year.items()):
        for cid, ss in sorted(clubs.items()):
            toks = sorted({x["club"] for x in ss}, key=lambda t: (not _is_code(t, year), t))
            roles = [r for x in ss for r in roles_on(x["stint"])]
            rows.append({"year": year, "club_id": cid, "club": toks[0], "head": head, "roles": roles})
    out = []
    for r in sorted(rows, key=lambda r: (r["year"], r["club_id"])):
        prev = next((x for x in out if x["club_id"] == r["club_id"] and x["head"] == r["head"]
                     and r["year"] - x["last"] <= 1), None)
        if prev:
            prev["last"] = max(prev["last"], r["year"]); prev["years"].add(r["year"])
            prev["roles"].extend(r["roles"])
            if not _is_code(prev["club"], prev["first"]) and _is_code(r["club"], r["year"]): prev["club"] = r["club"]
        else:
            out.append({"club_id": r["club_id"], "club": r["club"], "head": r["head"], "first": r["year"], "last": r["year"],
                        "years": {r["year"]}, "roles": list(r["roles"])})
    return sorted(out, key=lambda x: (x["first"], x["last"]))


def coaching(c):
    """What his coaching career WAS, for the lead. Ryan's ruling of 2026-09-06:

      head coaching outranks assistant work -- if he ever held a head job, that is
        what the bio leads with;
      the LONGEST head job outranks the rest, the later one where two are equal.
        Measured over the 92 merged men: 40 held more than one head job and 27 of
        those have a different answer for last and longest. Longest gives the job
        the man is remembered for every time they differ -- Ditka's eleven years at
        Chicago over three at New Orleans, Flores's six with the Raiders over three
        at Seattle, Schottenheimer's ten at Kansas City over a single UFL season.
      assistant work is one clause, never the lead.

    Role strings are carried EXACTLY as printed and are never rewritten here."""
    runs = coach_runs(c)
    if not runs: return None
    heads = [r for r in runs if r["head"]]
    principal = max(heads, key=lambda r: (len(r["years"]), r["last"])) if heads else None
    if principal is None:
        # a career assistant: the role he held over the most seasons, as printed
        tally = collections.Counter(x for r in runs for x in r["roles"])
        principal = max(runs, key=lambda r: (len(r["years"]), r["last"]))
        role = tally.most_common(1)[0][0] if tally else None
    else:
        role = collections.Counter(principal["roles"]).most_common(1)[0][0] if principal["roles"] else None
    roles_varied = len({x for x in principal["roles"]}) > 1
    assistant_years = {y for r in runs if not r["head"] for y in r["years"]}
    head_years = {y for r in heads for y in r["years"]}
    assistant_years -= head_years
    # for a man who was never a head coach the principal job IS assistant work, so
    # counting it again as "assistant years before that" contradicts the sentence
    # that just named it. What is left to say is how long he coached in all.
    if not heads: assistant_years -= principal["years"]
    return {"runs": runs, "head_jobs": len(heads), "was_head_coach": bool(heads),
            "roles_varied": roles_varied,
            "club": principal["club"], "club_id": principal["club_id"], "run_years": sorted(principal["years"]),
            "first": principal["first"], "last": principal["last"],
            "seasons": len(principal["years"]), "role_as_printed": role,
            "assistant_seasons": len(assistant_years),
            "assistant_before": bool(assistant_years) and (not head_years or max(assistant_years) < min(head_years)),
            "other_head_jobs": [{"club": r["club"], "club_id": r["club_id"], "first": r["first"], "last": r["last"],
                                 "seasons": len(r["years"])} for r in heads if r is not principal],
            "first_year": min(r["first"] for r in runs), "last_year": max(r["last"] for r in runs)}


def coach_clubs(c):
    """Ordered distinct (club, first_year) over the coaching seasons."""
    out = []
    for s in sorted(c["coached"], key=lambda s: s["year"]):
        if not out or out[-1][0] != s["club"]: out.append((s["club"], s["year"]))
    return out


def numbers(T, c, p):
    """The one statistic that matters for this man, and his best season on it."""
    votes = collections.Counter()
    for s in c["played"]:
        for code in s["codes"]:
            col = T.salient_for(code, s["year"])
            if col: votes[col] += 1
    if not votes: return None, None, None
    col = votes.most_common(1)[0][0]
    total = sum((num(s["stats"].get(col)) or 0) for s in c["played"] if (num(s["stats"].get(col)) or 0) > 0)
    best = None; best_pct = None; best_n = 0; best_col = None
    for s in c["played"]:
        qcols = set()
        for code in s["codes"]: qcols.update(T.qualifying_for(code, s["year"]))
        for qc in qcols:
            v = num(s["stats"].get(qc))
            if not v or v <= 0: continue
            if v < FLOOR[qc]: continue
            pct, n = T.percentile(s["league"], s["year"], qc, v)
            if pct is not None and (best_pct is None or pct > best_pct):
                best, best_pct, best_n, best_col = s, pct, n, qc
    comp = None
    if best and COMPANION.get(best_col):
        comp = num(best["stats"].get(COMPANION[best_col]))
    return col, {"total": total, "seasons_with": sum(1 for s in c["played"] if (num(s["stats"].get(col)) or 0) > 0)}, \
           ({"season": best, "column": best_col, "measure": MEASURE[best_col],
             "value": num(best["stats"].get(best_col)), "percentile": best_pct,
             "n": best_n, "companion": comp} if best else None)


def birth(T, g, p):
    bd = pfield(p, "birth_date")
    if not bd: return None
    dis = T.disputed.get(g)
    if not dis: return fact("birth_date", "lead", 0, date=bd, disputed=False)
    years = {re.search(r"\d{4}", str(x)).group(0) for _, a, b in dis for x in (a, b, bd)
             if x and re.search(r"\d{4}", str(x))}
    if len(years) == 1:
        return fact("birth_date", "lead", 0, date=None, year=years.pop(), disputed=True)
    return fact("birth_date", "lead", 0, date=None, years=sorted(years), disputed=True)


_WORDS = None


def _dictionary():
    global _WORDS
    if _WORDS is None:
        _WORDS = set()
        for fp in ("/usr/share/dict/words",):
            if os.path.exists(fp):
                _WORDS = {w.strip().lower() for w in open(fp, errors="ignore")}
    return _WORDS


def _ocr_torn(sent):
    """True when the sentence carries OCR wreckage: a pipe, a run of spaces, or
    lowercase words of four letters and more that no dictionary knows. A proper
    noun is capitalised and never counted. Two unknown words, or one in ten, is
    the threshold; measured on the Perko 1946 block (‘xcusons’, ‘liaving’)."""
    if "|" in sent or re.search(r" {3,}", sent): return True
    if re.search(r"[A-Za-z][\[\]{}]|[\[\]{}][A-Za-z]", sent): return True   # Bow] -- a torn glyph
    D = _dictionary()
    if not D: return False
    ws = re.findall(r"\b[a-z]{4,}\b", sent)
    if not ws: return False
    def known(w):
        if w in D: return True
        for stem in (w.rstrip("s"), w.rstrip("d"), re.sub(r"(ing|ed|es|ly|er)$", "", w),
                     re.sub(r"([a-z])\1(ed|ing)$", r"\1", w)):     # signalled -> signal
            if stem in D: return True
        return False
    bad = [w for w in ws if not known(w)]
    return len(bad) >= 2 or len(bad) / len(ws) > 0.10


def notes_excerpt(text):
    """The first run of a guide's prose that IS prose. Walks the block sentence by
    sentence; skips a label line, a table row, a torn sentence; then gathers
    consecutive clean sentences until the excerpt says enough (>= 60 chars) and
    stops before it runs long (<= 240). A telegraphic ellipsis block is quoted as
    the guide wrote it, up to a natural break. None only when nothing in the
    block survives, which is then not the guide's prose but its wreckage."""
    t = re.sub(r"-\n\s*", "", text)                 # base-\nball -> baseball
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    if t.count("...") + t.count(". . .") >= 2:
        t = re.sub(r"\.\s?\.\s?\.", "...", t)
        t = t.lstrip(". ")
        cut = t[:240]
        end = cut.rfind("...")
        first = (cut[:end + 3] if end > 60 else cut).strip()
        return first if len(re.findall(r"\b[a-z]{3,}\b", first)) >= 8 and not _ocr_torn(first) else None
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z\u201c\"])", t)
    out = []
    for x in sents:
        x = x.strip()
        # a label or a heading is a HARD stop: the next man's entry may begin here
        # (the 1946 Steelers block for Perko runs on into Compagno's), so nothing
        # past it is quoted as this man's.
        if (":" in x[:60] and not x.startswith("\u201c")) or \
           re.search(r"\b(Height|Weight|Born|Residence|Married)\b", x[:40]) or \
           re.search(r"\b(High School|University|College)\s*$", x):
            break
        junk = (not re.match(r"^[A-Z\u201c\"]", x)) or len(x) > 240 or _ocr_torn(x) \
            or len(re.findall(r"\b[a-z]{2,}\b", x)) < 2
        if junk:
            if out: break
            continue
        if out and len(" ".join(out)) + 1 + len(x) > 240: break
        out.append(x)
        if len(" ".join(out)) >= 60 and (len(out) >= 4 or len(" ".join(out)) >= 150): break
    first = " ".join(out)
    if len(first) < 40 or len(re.findall(r"\b[a-z]{3,}\b", first)) < 8: return None
    return first


def close_facts(T, g, p):
    """Candidates for the close, in a rough order. First one that exists wins."""
    out = []
    pf = T.pfa.get(g, {}); gd = T.guide.get(g, {})
    ntx = T.notes.get(g)
    if ntx:
        first = notes_excerpt(ntx["text"])
        if first:
            out.append(fact("notes", "close", 0, text=first, guide=ntx["guide"], year=ntx["year"]))
    ms = pf.get("military_service") or gd.get("SERVICE RECORD")
    if ms: out.append(fact("military", "close", 0, text=ms,
                           source="pfa" if pf.get("military_service") else "guide"))
    dd = pfield(p, "death_date") or pf.get("death_date")
    if dd: out.append(fact("death", "close", 0, date=dd, place=pf.get("death_place")))
    mar = gd.get("MARITAL STATUS")
    if mar: out.append(fact("family", "close", 0, text=mar))
    # hometown and high school were closes until 2026-09-06; they are identity and
    # live in the panel now. Nothing is backfilled in their place: the bio ends.
    return out


# ------------------------------------------------------------------ the panel
def _add(V, field, value, source, **extra):
    """The printed value is what is stored. A reading, where one can be made
    without guessing, sits beside it under `reads_as` and is marked derived --
    it can be recomputed or withdrawn without touching a claim (declarations/
    readings.json). Only the reading is compared; see disagreements() below."""
    if value is None: return
    if isinstance(value, str):
        value = clean(value)
        if not value: return
    row = {"value": value, "source": source, **extra}
    r = readings.read(field, value)
    if r is not None and r != value: row["reads_as"] = r
    if row not in V.setdefault(field, []): V[field].append(row)


def _differ(field, rows):
    """A field disagrees when its values carry more than one distinct READING.

    Two values that read to the same thing are one value written twice: PFA's
    "6-1" and the guide's '61"', PFR's TAM and nflverse's TB. A value that cannot
    be read takes no part -- it can neither corroborate nor contradict -- so it is
    excluded here, kept on the panel verbatim, and counted by gate_readings.
    """
    if readings.READERS.get(field):
        # THE SHARED GROUPING, not a set of readings. A reading can be a DICT -- the
        # draft reading is {year, league, kind, numbering, ...} -- and two dicts that
        # `same()` calls one fact are not equal and are not hashable. A set here
        # therefore both crashed and, before the reading became a dict, silently
        # counted `{year, round, overall}` against `{year, round, overall, league}` as
        # a disagreement. RV.group is the one implementation of this rule.
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                          "..", "service"))
        import reading_view as RV
        groups, unreadable = RV.group(field, [r["value"] for r in rows])
        return len(groups) > 1
    seen = {json.dumps(r["value"], sort_keys=True) for r in rows}   # no reader: as written
    return len(seen) > 1


def vitals(T, g, p):
    """Identity as data. Every value names its source; a field with two distinct
    values is listed under `disagreements` and NOT resolved. Layout is not here."""
    V = {}
    pf = T.pfa.get(g, {}); gd = T.guide.get(g, {})
    _add(V, "birth_date", pfield(p, "birth_date"), "person-index")
    for src, a, b in T.disputed.get(g, []):
        _add(V, "birth_date", a, src); _add(V, "birth_date", b, "statscrew")
    for lab in ("BORN", "Born", "Born in"):
        _add(V, "birth_date_as_printed", gd.get(lab), "guide")
    _add(V, "birth_place", pf.get("birth_place"), "pfa")
    _add(V, "birth_place", pfield(p, "birthplace"), "person-index")
    _add(V, "hometown", pfield(p, "hometown"), "person-index")
    for lab in ("HOME TOWN", "HOMETOWN"): _add(V, "hometown", gd.get(lab), "guide")
    col = pfield(p, "college")
    if col and col.lower() != "none": _add(V, "college", col, "person-index")
    _add(V, "college", pf.get("college"), "pfa")
    for lab in ("COLLEGE FOOTBALL", "College", "COLLEGE (HEADER)"): _add(V, "college", gd.get(lab), "guide")
    _add(V, "high_school", pfield(p, "high_school"), "person-index")
    _add(V, "high_school", pf.get("high_school"), "pfa")
    for lab in ("HIGH SCHOOL FOOTBALL", "HIGH SCHOOL"): _add(V, "high_school", gd.get(lab), "guide")
    _add(V, "height", pf.get("height"), "pfa")
    for lab in ("Height", "HEIGHT", "Ht.", "HT"): _add(V, "height", gd.get(lab), "guide")
    _add(V, "weight", pf.get("weight"), "pfa")
    for lab in ("Weight", "WEIGHT", "Wt.", "WT"): _add(V, "weight", gd.get(lab), "guide")
    for src, val in T.draft.get(g, []):
        if isinstance(val, dict):
            _add(V, "draft", {k: val[k] for k in ("year", "round", "overall_pick", "team") if k in val}, src)
    for k in ("draft_selection", "draft"):
        if pf.get(k): _add(V, "draft", pf[k], "pfa")
    codes = collections.Counter(); vocab = {}
    for s in seasons(p):
        if s["coaching"]: continue
        pos = s["stint"].get("position")
        for one in (pos if isinstance(pos, list) else [pos]):
            if isinstance(one, dict) and one.get("code"):
                codes[one["code"]] += 1; vocab.setdefault(one["code"], one.get("vocab"))
    for code, n in codes.most_common():
        _add(V, "position", code, vocab.get(code) or "stint", seasons=n)
    dis = [f for f, rows in V.items() if f != "position" and _differ(f, rows)]
    years = {m.group(0) for f in ("birth_date", "birth_date_as_printed") for r in V.get(f, [])
             for m in [re.search(r"\b(18|19|20)\d{2}\b", str(r["value"]))] if m}
    if len(years) > 1 and "birth_date" not in dis: dis.append("birth_date")
    if dis: V["disagreements"] = sorted(dis)
    return V


def select(T, g):
    p = T.people[g]
    c = career(p)
    if not c["years"]:
        return coaching_only_bio(T, g, p, c)
    facts = []
    # ---- lead candidates
    sh = shapes(T, c, p)
    col, tot, best = numbers(T, c, p)
    lead_cands = list(sh)
    if best and best["percentile"] is not None and best["percentile"] >= 0.90:
        lead_cands.append(fact("distinction", "lead", best["percentile"], **best))
    if col and tot and tot["total"] >= FLOOR[col]:
        # salience floor: percentile of his career total among men sharing the column,
        # capped so it never outranks a real shape or distinction
        lead_cands.append(fact("salience", "lead", min(0.45, 0.45 * min(1.0, tot["seasons_with"] / 4)),
                               column=col, measure=MEASURE[col], total=tot["total"],
                               best=best))
    lead = max(lead_cands, key=lambda f: f["score"]) if lead_cands else \
        fact("plain", "lead", 0, season=c["played"][0])
    facts.append(lead)
    # ---- body: clubs and seasons, the number that matters. Identity is in the panel.
    facts.append(fact("career_span", "body", 0, years=c["years"], clubs=c["clubs"],
                      leagues=c["leagues"], games=c["games"], gaps=c["gaps"],
                      played=[(s["year"], s["club"], s["league"]) for s in c["played"]]))
    if lead["kind"] != "played_then_coached" and c["played"] and c["coached"]:
        cy = sorted({s["year"] for s in c["coached"]})
        facts.append(fact("coached", "body", 0, first=cy[0], last=cy[-1], n=len(cy),
                          coaching=coaching(c), clubs=coach_clubs(c)))
    if col and tot and tot["total"] >= FLOOR[col] and lead["kind"] not in ("salience",):
        # the career number, only if it is a career and not a single season restated
        if tot["seasons_with"] >= 2 and (lead["kind"] != "distinction" or best["column"] != col
                                         or tot["total"] > 1.5 * best["value"]):
            facts.append(fact("career_total", "body", 0, column=col, measure=MEASURE[col],
                              total=tot["total"], seasons_with=tot["seasons_with"]))
    # ---- close: first that exists. A guide's prose is first in close_facts, by ruling.
    cl = close_facts(T, g, p)
    if cl: facts.append(cl[0])
    return {"id": g, "name": p["name"], "facts": facts, "lead_kind": lead["kind"],
            "close_kind": (cl[0]["kind"] if cl else None), "vitals": vitals(T, g, p)}


def coaching_only_bio(T, g, p, c):
    """A man who only ever coached. Same three slots; the career being described is
    a coaching career. Ryan's ruling of 2026-09-06.

    No playing sentence is invented. 'He never played professionally' is filler
    unless the archive can say what he did instead, and it cannot."""
    if not c["coached"]: return None
    cc = coach_career(T, c)
    co = coaching(c)
    if not cc or not co: return None
    sh = coaching_shapes(T, cc, co)
    best = max(sh, key=lambda f: f["score"]) if sh else None
    # the LEAD is his principal head job, by the longest-run rule. A man who never
    # held one leads on whatever his coaching career was: its length, clubs, shape.
    if co["was_head_coach"]:
        lead = fact("head_coach_career", "lead", 0.95, coaching=co,
                    shape=(best["kind"] if best else None), shape_fact=best)
    elif best:
        # A MAN WHO NEVER HELD A HEAD JOB STILL HAS A CAREER, and it is its own shape.
        # Ruled by Ryan, 2026-09-09. This used to hand `best` -- a bare shape fact
        # carrying `year`/`club`/`seasons` and no `coaching` -- straight to the writer,
        # which has only ever rendered a fact carrying `coaching`. 967 men, every one a
        # career assistant or coordinator, returned 503 from get_bio. The shapes were
        # right; nothing had ever matched them. The fact now carries the career the same
        # way the head-coach lead does, and the writer has a branch for it.
        lead = fact("assistant_career", "lead", best["score"], coaching=co,
                    shape=best["kind"], shape_fact=best)
    else:
        lead = fact("coaching_career", "lead", 0, coaching=co)
    facts = [lead, fact("coaching_span", "body", 0, years=cc["years"], clubs=cc["clubs"],
                        leagues=cc["leagues"], gaps=cc["gaps"], coaching=co,
                        shape=(best["kind"] if best else None),
                        coached=[(s["year"], s["club"]) for s in cc["seasons"]])]
    cl = close_facts(T, g, p)
    if cl: facts.append(cl[0])
    return {"id": g, "name": p["name"], "facts": facts, "lead_kind": lead["kind"],
            "close_kind": (cl[0]["kind"] if cl else None), "vitals": vitals(T, g, p),
            "coaching_only": True}


if __name__ == "__main__":
    T = Tables()
    print("median playing seasons:", T.median_seasons)
    print("position codes with no salient column at any decade:", len(T.codes_without_salient),
          T.codes_without_salient[:20])
    for name in sys.argv[1:] or ["Len Eshmont", "Chris Hinton"]:
        g = next(g for g, p in T.people.items() if p["name"] == name)
        print(json.dumps(select(T, g), indent=1, default=str)[:2500])
