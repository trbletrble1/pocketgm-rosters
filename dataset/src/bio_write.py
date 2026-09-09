"""WORDING LAYER. Turns a Facts object from bio_select into sentences. No selection here.

Rules, all of them from Ryan's reading of the old bios:
  - no hedging verbs. He scored, he ran for, he caught. The honesty lives in the
    store; the sentence does not apologise.
  - the club comes early.
  - a number is written only once and the whole bio carries at most three.
  - plurals are real words: one pass, two passes. Never "1 receptions".
  - when there is no close, the bio ends. No filler.
  - sentence shapes vary by man, deterministically (hash of the id), so the
    fourth bio does not read like the first.
  - ONE NAME PER CLUB PER BIO (2026-09-06, Perko). A franchise that was renamed
    during the man's time with it is named ONCE, by its name in the year of the
    first mention, with the other name in a parenthetical on that first mention
    only. Every later mention reuses the same name.
  - a club is not named twice in one breath (2026-09-06, Kerasiotis). When the
    war-gap lead's before-club and after-club are the same club, the second
    mention is a pronoun, and the body does not list the club again.

Identity (birth, college, hometown, high school, height, weight, draft,
position) is NOT written here. It is data in F["vitals"], for a panel.
"""
import re, hashlib
from bio_select import club_name, club_name_or_none, LEAGUE_NAME, DEFUNCT_LEAGUES, LEAGUE_FAMILY, _club_table, is_head_position

VERB = {  # measure -> (singular, plural) past-tense phrase with {n}
    "tackles": ("made one tackle", "made {n} tackles"),
    "receptions": ("caught one pass", "caught {n} passes"),
    "completions": ("completed one pass", "completed {n} passes"),
    "field_goals": ("kicked one field goal", "kicked {n} field goals"),
    "punts": ("punted once", "punted {n} times"),
    "rushing_yards": ("ran for one yard", "ran for {n} yards"),
    "interceptions": ("intercepted one pass", "intercepted {n} passes"),
    "points": ("scored one point", "scored {n} points"),
}
MORE = {  # for "only k men ... more"
    "tackles": "made more", "receptions": "caught more", "completions": "completed more",
    "field_goals": "kicked more", "punts": "punted more often", "rushing_yards": "ran for more",
    "interceptions": "intercepted more", "points": "scored more",
}
COMPANION_PHRASE = {"receptions": "for {n} yards", "completions": "for {n} yards",
                    "rushing_yards": "and {n} touchdowns", "interceptions": "for {n} return yards"}


def _h(seed, k):
    return int(hashlib.md5(seed.encode()).hexdigest(), 16) >> (k * 4)


def pick(seed, k, options):
    return options[_h(seed, k) % len(options)]


def n_(x):
    x = int(round(x))
    return f"{x:,}"


def words(n):
    W = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
         8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
         14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty"}
    if n in W: return W[n]
    if 20 < n < 40 and n % 10: return W[n // 10 * 10] + "-" + W[n % 10]
    return str(n)


def seasons_word(n):
    return "one season" if n == 1 else f"{words(n)} seasons"


def rng(a, b):
    if a == b: return str(a)
    if a // 100 == b // 100: return f"{a}–{str(b)[2:]}"
    return f"{a}–{b}"


def league(l):
    return LEAGUE_NAME.get(l, l)


def did(measure, n):
    s, p = VERB[measure]
    return s if int(round(n)) == 1 else p.format(n=n_(n))


def runs(played, by_club_only=False):
    """Stints by club: [[club, league, first, last, years]]. The same club across a gap,
    or across a league rename (APFA -> NFL), is ONE club, not two.

    by_club_only merges on the CLUB alone, ignoring the league. A club that changed
    league kept being itself: the Boston Patriots of 1969 are in the AFL and of 1970
    in the NFL, and listing his clubs as 'the Boston Patriots in 1969, the Boston
    Patriots in 1970' names one club twice. The league-aware form is still what the
    crossed-leagues lead needs, since there the league is the point."""
    out = []
    for y, c, l in played:
        fam = LEAGUE_FAMILY.get(l, l)
        prev = next((r for r in out if r[0] == c and
                     (by_club_only or LEAGUE_FAMILY.get(r[1], r[1]) == fam)), None)
        if prev:
            prev[3] = max(prev[3], y); prev[4].add(y)
        else:
            out.append([c, l, y, y, {y}])
    return out


def years_phrase(ys):
    ys = sorted(ys); groups = []
    for y in ys:
        if groups and y - groups[-1][1] == 1: groups[-1][1] = y
        else: groups.append([y, y])
    parts = [str(a) if a == b else rng(a, b) for a, b in groups]
    if len(parts) == 1:
        a, b = groups[0]
        return f"in {a}" if a == b else f"from {a} to {b}"
    return "in " + ", ".join(parts[:-1]) + " and " + parts[-1]


def dot(s):
    """End a sentence without doubling a stop the value already carries."""
    return s if s.endswith(".") else s + "."


_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def date_text(v):
    """Render a date the way the archive prints one. The merge of 2026-09-06 gave
    some men a date in the other source's notation -- Dutch Sternaman's death came
    across as '1973-02-01' -- and both forms are held in the store. This chooses one
    for the sentence; it changes nothing that is stored."""
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", str(v or "").strip())
    if not m: return v
    y, mo, d = (int(x) for x in m.groups())
    return f"{_MONTHS[mo - 1]} {d}, {y}" if 1 <= mo <= 12 else v


def strip_usa(s):
    return re.sub(r",?\s*USA$", "", s or "").strip()


class Namer:
    """One name per club per bio. The name is fixed at the first mention, by the
    year of that mention; if the man's years with the club carry another name,
    the first mention says so once, and every later mention holds the fixed name.

    Names are fixed per CODE, as they always were: a move is a new name (the
    Cleveland Rams, then the Los Angeles Rams), a rename in place is one name with
    a note. A coaching run is named from the club table over the run's own years
    (Namer.run) and fixes every code it crosses; a code's fixed name is reused only
    where that fixing belonged to the same club, so the table's split of a code
    into two clubs (Ottawa Rough Riders / Ottawa Renegades) is honoured."""

    def __init__(self, played):
        self.years = {}
        # (year, code) pairs. A third element used to be accepted and discarded; the
        # only caller passing one passed the literal "COACHES", which is why it looked
        # as though the league mattered here. It never did: a club is named from the
        # club table by year, and the competition is not part of that.
        for y, c, *_ in played: self.years.setdefault(c, set()).add(y)
        self.fixed = {}; self.fixed_cid = {}; self.runs_said = set()

    @staticmethod
    def cid(code, year):
        r = _club_table().resolve(code, year, None, source="season_key")
        return r[0] if r else None

    def _fix(self, code, nm, year):
        self.fixed[code] = nm; self.fixed_cid[code] = self.cid(code, year)

    def _held(self, code, year):
        """The fixed name for this code, if it was fixed for the same club."""
        if code in self.fixed and self.fixed_cid.get(code) == self.cid(code, year): return self.fixed[code]
        return None

    def the(self, code, year, last_year=None):
        held = self._held(code, year)
        if held: return f"the {held}"
        nm = club_name(code, year)
        self._fix(code, nm, year)
        # A YEAR THE ARCHIVE CANNOT NAME IS NOT A RENAME. `club_name` falls back to the
        # token, so a 2025 season -- past the club table's last held names -- read as
        # "the Carolina Panthers, later the CAR". `club_name_or_none` says unknown.
        others = {}
        for y in sorted(self.years.get(code, set())):
            o = club_name_or_none(code, y)
            if o and o != nm: others.setdefault(o, []).append(y)
        if not others and last_year and last_year != year:
            o = club_name_or_none(code, last_year)
            if o and o != nm: others[o] = [last_year]
        if not others: return f"the {nm}"
        o, ys = next(iter(others.items()))
        word = "earlier" if max(ys) < year else "later"
        return f"the {nm} ({word} the {o.split()[-1]})"

    def run(self, co):
        """A coaching RUN, named from the club table over the run's OWN years -- not
        the playing years this Namer was built on, which cannot see a coaching
        tenure cross a move. Where the club was renamed or moved inside the run,
        the first mention says so once: 'the Oakland Raiders, later the Los Angeles
        Raiders'. Later mentions hold the first name. Ryan's ruling of 2026-09-06.
        A merger season's slash name (Boston Yanks/Brooklyn Tigers, 1945) is not a
        rename and is not listed as one."""
        cid = co.get("club_id")
        if not cid or cid.startswith("?"): return self.the(co["club"], co["first"], co.get("last"))
        T = _club_table(); years = co.get("run_years") or list(range(co["first"], co["last"] + 1))
        parts = []                                                   # (code, name) in order across the run
        for y in years:
            code = T.code_for(cid, y) or co["club"]
            # A YEAR THE TABLE CANNOT NAME DOES NOT START A NEW NAME. It used to fall
            # back to the season-key token, so a run reaching into 2025 -- past the
            # club table's last held names -- became "the Carolina Panthers, later the
            # CAR". Where the archive holds no name for a year the run simply continues
            # under the name it already had.
            nm = T.name_for(cid, y) or club_name_or_none(code, y)
            if nm is None:
                if parts: continue
                nm = code                                # nothing known at all: the token stands
            if "/" in nm and any("/" not in p[1] for p in parts): continue
            if not parts or parts[-1][1] != nm: parts.append((code, nm))
        if cid in self.runs_said:
            return f"the {self._held(parts[0][0], years[0]) or parts[0][1]}"
        self.runs_said.add(cid)
        names, note = [], ""; pre_fixed = set(self.fixed)
        for i, (code, nm) in enumerate(parts):
            y = years[0] if i == 0 else years[-1]
            held = self._held(code, y) if code in pre_fixed else None   # a code fixed EARLIER in the bio; not by this run's own first part
            if held is None:
                if code not in self.fixed: self._fix(code, nm, y)
                if i == 0:                                           # the first mention of the club says what else he knew it as -- the same club only
                    others = {}
                    for yy in sorted(self.years.get(code, set())):
                        o = club_name_or_none(code, yy)          # unknown is not a rename
                        if o and o not in {p[1] for p in parts} and self.cid(code, yy) == cid: others.setdefault(o, []).append(yy)
                    if others:
                        o, ys = next(iter(others.items()))
                        note = f" ({'earlier' if max(ys) < co['first'] else 'later'} the {o.split()[-1]})"
                held = nm
            if not names or names[-1] != held: names.append(held)
        if len(names) == 1: return f"the {names[0]}{note}"
        return f"the {names[0]}, later the {names[1]}" + "".join(f", then the {n}" for n in names[2:]) + "," + note


class Writer:
    def __init__(self, F):
        self.F = F; self.id = F["id"]; self.name = F["name"]
        self.nums = 0; self.said_clubs = False; self.said_years = False
        self.named_first = False   # the lead named the first club; the body carries on from it
        self.coach_tail_pending = ""   # the one assistant clause, emitted after the coaching sentence
        self.emitted = ""              # what the bio has actually said so far
        span = next((f for f in F["facts"] if f["kind"] == "career_span"), None)
        if span is None:
            cs = next(f for f in F["facts"] if f["kind"] == "coaching_span")
            # THE DEAD `"COACHES"` WAS REMOVED 2026-09-09. Namer.__init__ is
            # `for y, c, l in played` and never reads `l` again, so the literal decided
            # nothing -- but it read as though a coaching span were a league called
            # COACHES, which is the belief this week was spent removing. Namer now takes
            # pairs; a dead string test is one that comes back to life quietly.
            self.N = Namer(cs["coached"])
        else:
            self.N = Namer(span["played"])

    def v(self, k, opts):
        return pick(self.id, k, opts)

    def the(self, code, year, last_year=None):
        return self.N.the(code, year, last_year)

    def clubs_phrase(self, played, exclude=None):
        R = [r for r in runs(played, by_club_only=True) if not (exclude and r[0] == exclude[0])]
        if not R: return None
        if len(R) <= 3:
            # ONE CLUB IS NAMED ONCE. Two season-key tokens can be one club -- `STL` and
            # `St. Louis All-Stars` are both club-st-louis-all-stars-1923 -- and once the
            # bio started naming clubs from the club table (2026-09-09) both rendered the
            # same, so Ollie Kraehe "went to the St. Louis All-Stars in 1923 and the
            # St. Louis All-Stars in 1923". The runs are kept; the PHRASE is deduplicated
            # on what it actually says, which is the only place the repetition exists.
            parts = list(dict.fromkeys(
                f"{self.the(c, f, l)} {years_phrase(ys)}" for c, lg, f, l, ys in R))
            # NOT ALSO DROPPING A CLUB THE LEAD ALREADY NAMED, and the reason is kept.
            # Ollie Kraehe's lead names the St. Louis All-Stars as his head-coaching club
            # and the next sentence sends him there again -- a real repetition, visible
            # since both his tokens started rendering as one name. Dropping what the lead
            # had said was tried and REVERTED: it also removed Jack Pardee's Rams YEARS
            # ("the Los Angeles Rams in 1957-64 and 1966-70"), which the lead does not
            # give. Losing a fact to save a repetition is the worse trade. The repetition
            # stands, reported rather than papered over.
            if len(parts) == 1: return parts[0]
            return ", ".join(parts[:-1]) + " and " + parts[-1]
        names = list(dict.fromkeys(self.the(c, f, l) for c, lg, f, l, ys in R))
        return f"{words(len(names))} clubs — " + ", ".join(names[:-1]) + " and " + names[-1]

    # ------------------------------------------------------- coaching, Ryan's ruling
    # Head coaching outranks assistant work and leads. The longest head job outranks
    # the rest. Assistant work is ONE CLAUSE. Role strings are rendered EXACTLY as
    # the source printed them -- 'Head Coach', 'Defensive Backs', 'Offensive Backs' --
    # and are never lower-cased, expanded or otherwise rewritten here.
    def head_job(self, co, its_club_already_named=False):
        """(verb, phrase). A job held over years takes 'was'; a single year 'became'.

        Where the sentence has ALREADY named this club -- a player-coach, who took
        over the club he played for -- it becomes 'their', so the Muncie Flyers are
        not named twice in one breath."""
        # PFA PRINTS THE HEAD JOB IN CAPITALS -- 'HEAD COACH', 'HEAD COACH/Offensive
        # Coordinator'. The claim keeps that string exactly; the BIO is derived prose and
        # reads it, the same way the display name reads a surname-first form. Without
        # this the sentence shouted: "blanton collier ... was HEAD COACH of the Cleveland
        # Browns". Only a DECLARED head position is read this way; every other printed
        # role goes through verbatim.
        role = co["role_as_printed"] or "head coach"
        if is_head_position(role): role = "Head Coach"
        club = "their" if its_club_already_named else self.N.run(co)
        if its_club_already_named:
            when = f"from {co['first']} to {co['last']}" if co["first"] != co["last"] else f"in {co['first']}"
            verb = "was" if co["first"] != co["last"] else "became"
            return verb, (f"their {role} {when}" if co["was_head_coach"] else f"their {role}, {when}")
        # where the role changed inside the run, say so rather than let one title
        # stand for twenty years: Carl Taseff's Miami years were not all Running Backs
        # the phrase is complete: callers never add "as" of their own
        if co["was_head_coach"]: lead_in = f"{role} of"
        elif co.get("roles_varied"): lead_in = f"most often as {role}, with"
        else: lead_in = f"as {role} of"
        if co["first"] != co["last"]:
            return "was", f"{lead_in} {club} from {co['first']} to {co['last']}"
        return "became", f"{lead_in} {club} in {co['first']}"

    # --------------------------------------------------- a coaching-only career
    def coach_lead(self, f):
        """A man who only ever coached. The lead is his principal head job, with the
        shape of the career carried in the same sentence where there is one worth
        carrying. No playing sentence is invented, because the archive has none."""
        N = self.name; co = f["coaching"]; shape = f.get("shape")
        verb, job = self.head_job(co)
        n_total = co["last_year"] - co["first_year"] + 1
        sf = f.get("shape_fact") or {}
        if shape == "coached_across_leagues":
            lgs = [league(x) for x in sf.get("leagues", [])]
            where = " and ".join(lgs) if len(lgs) == 2 else ", ".join(lgs[:-1]) + " and " + lgs[-1]
            return self.v(1, [f"{N} coached in {where}, most of it as {job}.",
                              f"{N}'s coaching crossed leagues — {where} — and its longest stretch was as {job}."])
        if shape == "coached_one_club":
            club = self.the(co["club"], co["first"], co["last"])
            k = seasons_word(sf.get("seasons", co["seasons"]))
            a, b = sf.get("first", co["first"]), sf.get("last", co["last"])
            return self.v(1, [f"{N} coached {club} for {k}, {a} to {b}, and no one else.",
                              f"{N} spent his whole coaching career with {club}: {k}, {a} to {b}."])
        if shape == "coached_long":
            return self.v(1, [f"{N} coached {seasons_word(sf.get('seasons', co['seasons']))}, {sf.get('first')} to {sf.get('last')}, and {verb} {job}.",
                              f"Over {seasons_word(sf.get('seasons', co['seasons']))}, {sf.get('first')} to {sf.get('last')}, {N} {verb} {job}."])
        if shape == "coached_war_gap":
            return f"{N} {verb} {job}, with the war years between: he did not coach from {sf['before'] + 1} to {sf['after'] - 1}."
        if shape == "coached_defunct_club":
            L = league(sf.get("league")) if sf.get("league") else None
            club = self.the(sf["club"], sf["year"]) if sf.get("club") else None
            if L and club and sf["club"] != co["club"]:
                return f"{N} {verb} {job}, and had coached {club} of {L} before that."
            return f"{N} {verb} {job}" + (f", of {L}." if L else ".")
        return self.v(1, [f"{N} {verb} {job}.", f"{N} spent {seasons_word(co['seasons'])} as {job}."])

    def role_phrase(self, co, with_club=True):
        """The job as the SOURCE PRINTS IT, with its club and years -- and no verb, so a
        caller can put it where the sentence needs it. `head_job` returns a phrase that
        already carries "as", which reads as "was as Defensive Coordinator" the moment a
        sentence puts a verb in front of it. Head coaches never hit that because their
        phrase is "Head Coach of X"; the 967 men who never held a head job did.

        The role is PFA's or the Coaching Tree's string, verbatim -- 'Offensive Line',
        'Assistant Strength and Conditioning' -- never title-cased and never expanded
        into a sentence the source did not write."""
        role = co.get("role_as_printed")
        club = self.N.run(co) if with_club else None
        when = (f"from {co['first']} to {co['last']}" if co["first"] != co["last"]
                else f"in {co['first']}")
        if role and club: return f"{role} of {club} {when}"
        if role: return f"{role}, {when}"
        if club: return f"{club} {when}"
        return when

    def assistant_lead(self, f):
        """A man who coached and never held a head job. Ryan's ruling, 2026-09-09: the
        bio opens on what he DID -- where he coached, in what roles, across how long.

        It keeps every discipline the playing bios have. It stops rather than pads: a
        one-season assistant gets one sentence, and that is the whole bio where the
        archive holds nothing else. It never states a number the next sentence will
        state again -- the lead names WHERE he mostly was and the span carries the
        totals. It says what it does not know rather than filling: where no source
        names the role, it says so once and does not guess.

        THE ROLE IS "LISTED AS", not "as". PFA lists 1,046 distinct printed positions
        and most are units, not job titles -- 'Safeties', 'Offensive Line', 'Assistant
        Strength and Conditioning'. "was as Safeties" is not English and "was the
        safeties coach" is a sentence the source did not write. "listed as Safeties" is
        exactly what the source does, and it holds the string verbatim."""
        N = self.name; co = f["coaching"]; shape = f.get("shape"); sf = f.get("shape_fact") or {}
        role = co.get("role_as_printed")
        listed = ("most often listed as " if co.get("roles_varied") else "listed as ") + role if role else None
        # Namer.run can end in a clause of its own ("the Vikings, later the MIN"), and a
        # template that appends ", listed as ..." to it produced a double comma.
        def where_club(): return self.N.run(co).rstrip(" ,")

        if shape == "coached_one_season":
            club = self.the(sf.get("club", co["club"]), sf.get("year", co["first"]))
            yr = sf.get("year", co["first"])
            if listed:
                return f"{N} coached one season, {yr}, with {club}, {listed}."
            return (f"{N} coached one season, {yr}, with {club}. "
                    f"No source the archive holds names the job he did there.")

        if shape == "coached_one_club":
            club = self.the(co["club"], co["first"], co["last"])
            k = seasons_word(sf.get("seasons", co["seasons"]))
            a, b = sf.get("first", co["first"]), sf.get("last", co["last"])
            base = f"{N} spent his whole coaching career with {club}: {k}, {a} to {b}"
            return base + (f", {listed}." if listed else ".")

        if shape == "coached_long":
            # NO CLUB COUNT HERE. `coaching_span` says how many clubs, and a lead that
            # says it too both repeats and disagrees -- it counted the runs where the
            # span counts the clubs.
            k = seasons_word(sf.get("seasons", len(co["runs"])))
            a, b = sf.get("first", co["first_year"]), sf.get("last", co["last_year"])
            if listed:
                return f"Over {k}, {a} to {b}, {N} coached, most of it with {where_club()}, {listed}."
            return f"Over {k}, {a} to {b}, {N} coached, most of it with {where_club()}."

        if shape == "coached_across_leagues":
            lgs = [league(x) for x in sf.get("leagues", [])]
            where = " and ".join(lgs) if len(lgs) == 2 else ", ".join(lgs[:-1]) + " and " + lgs[-1]
            tail = (f"most of it with {where_club()}, {listed}" if listed
                    else f"most of it with {where_club()}")
            return f"{N}'s coaching crossed leagues — {where} — {tail}."

        if shape == "coached_war_gap":
            return (f"{N} coached {self.role_phrase(co, with_club=True)}, with the war years "
                    f"between: he did not coach from {sf['before'] + 1} to {sf['after'] - 1}.")

        if shape == "coached_defunct_club":
            L = league(sf.get("league")) if sf.get("league") else None
            when = (f"from {co['first']} to {co['last']}" if co["first"] != co["last"]
                    else f"in {co['first']}")
            head = f"{N} coached {where_club()}" + (f" of {L}" if L else "") + f" {when}"
            return head + (f", {listed}." if listed else ".")

        when = (f"from {co['first']} to {co['last']}" if co["first"] != co["last"]
                else f"in {co['first']}")
        return f"{N} coached {where_club()} {when}" + (f", {listed}." if listed else ".")

    def coaching_career_lead(self, f):
        """A coaching career with no shape to lead on: not long, not one club, not
        across leagues, no war gap. The lead is where he coached and in what role, and
        the span sentence carries the totals.

        IT USED TO SAY THE SPAN AND CALL IT SEASONS. `last_year - first_year + 1` is the
        distance between his first and last years, not how many he coached: Gord Ackerman
        was away in 1964, so the lead said "coached ten seasons" and the very next
        sentence said "in all he coached nine". A bio does not invent a season. The count
        is left to `coaching_span`, which counts them, and this sentence stops instead."""
        N = self.name; co = f["coaching"]
        role = co.get("role_as_printed")
        if role and is_head_position(role): role = "Head Coach"
        listed = (("most often listed as " if co.get("roles_varied") else "listed as ") + role) if role else None
        when = (f"from {co['first']} to {co['last']}" if co["first"] != co["last"]
                else f"in {co['first']}")
        # THE YEARS COME BEFORE THE CLUB. Namer.run can end in a clause of its own --
        # "the Kansas City Chiefs, later the KC" -- and a date phrase appended to that
        # reads as a comma splice. Put the years first and the club's own clause closes
        # the sentence cleanly however long it is.
        club = self.N.run(co).rstrip(" ,")
        return f"{N} coached {when} with {club}" + (f", {listed}." if listed else ".")

    def coaching_span(self, f):
        """The coaching career: how long, across how many clubs, and its gaps."""
        co = f["coaching"]; out = []
        years = f["years"]; n = len(years)
        heads = [r for r in co["runs"] if r["head"]]
        # a second spell at the SAME club is not another club
        others = [h for h in heads if h.get("club_id", h["club"]) != co.get("club_id", co["club"])]
        clubs = list(dict.fromkeys(c for c, _ in f["clubs"]))
        # the lead already gave the total and the range for these shapes; saying it
        # again is repetition, not information
        said_total = f.get("shape") in ("coached_long", "coached_one_club")
        if n > co["seasons"] and not said_total:
            if len(clubs) > 1:
                out.append(self.v(3, [f"He coached {seasons_word(n)} in all, for {words(len(clubs))} clubs, "
                                      f"from {years[0]} to {years[-1]}.",
                                      f"In all he coached {seasons_word(n)} across {words(len(clubs))} clubs, "
                                      f"{years[0]} to {years[-1]}."]))
            else:
                out.append(f"He coached {seasons_word(n)} in all, from {years[0]} to {years[-1]}.")
        elif said_total and len(clubs) > 1 and f.get("shape") == "coached_long":
            out.append(f"He coached for {words(len(clubs))} clubs in all.")
        if others:
            names = [self.N.run(h) for h in others[:3]]
            if len(others) <= 3:
                lst = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
                out.append(f"He held the same job at {lst}.")
            else:
                out.append(f"He was a head coach at {words(len(others))} other clubs, among them "
                           + ", ".join(names[:-1]) + " and " + names[-1] + ".")
        gaps = [(a, b) for a, b in f["gaps"]
                if not (set(range(a + 1, b)) & {1942, 1943, 1944, 1945} and f.get("shape") == "coached_war_gap")]
        if len(gaps) == 1:
            a, b = gaps[0]
            out.append(f"He did not coach in {a + 1}." if b - a == 2
                       else f"He was away from the game from {a + 1} to {b - 1}.")
        elif len(gaps) > 1:
            sp = [str(a + 1) if b - a == 2 else rng(a + 1, b - 1) for a, b in gaps]
            out.append("He was in and out of the game, missing " + ", ".join(sp[:-1]) + " and " + sp[-1] + ".")
        if co["assistant_seasons"] and co["was_head_coach"]:
            out.append(f"He had been an assistant for {seasons_word(co['assistant_seasons'])} before that."
                       if co["assistant_before"] else
                       f"He spent another {seasons_word(co['assistant_seasons'])} as an assistant.")
        return " ".join(out)

    def coach_tail(self, co):
        """One clause for the assistant years, one for any other head job. Never a
        career summary."""
        if self.nums >= 3: return ""
        bits = []
        n = co["assistant_seasons"]
        if n and co["was_head_coach"]:
            bits.append(f"had been an assistant for {seasons_word(n)} before that" if co["assistant_before"]
                        else f"spent another {seasons_word(n)} as an assistant")
        elif n:
            bits.append(f"coached for {seasons_word(n + co['seasons'])} in all")
        k = len(co["other_head_jobs"])
        if k:
            bits.append("was a head coach at one other club too" if k == 1
                        else f"was a head coach at {words(k)} other clubs too")
        if not bits: return ""
        self.nums += 1
        return "He " + (" and ".join(bits) if len(bits) == 2 else bits[0]) + "."

    def coach_where(self, clubs):
        if not clubs: return ""
        if len(clubs) == 1: return f" with {self.the(*clubs[0])}"
        return f", first with {self.the(*clubs[0])} and later {self.the(*clubs[-1])}" if len(clubs) == 2 \
            else f", first with {self.the(*clubs[0])}"

    # ------------------------------------------------------------- lead
    def lead(self, f, span):
        N = self.name; k = f["kind"]; the = self.the
        played = span["played"]
        if k == "single_game":
            s = f["season"]; c = the(s["club"], s["year"]); L = league(s["league"])
            self.said_clubs = self.said_years = True
            if f["games"] == 2:
                return self.v(1, [f"{N} played two professional games, both for {c} in {s['year']}.",
                                  f"{N}'s career was two games with {c} in {s['year']}."])
            return self.v(1, [f"{N} played one professional game, for {c} in {s['year']}.",
                              f"{N}'s professional career was a single game, with {c} in {s['year']}.",
                              f"One game was the whole of {N}'s career: {c}, {s['year']}, in {L}."])
        if k == "single_season":
            s = f["season"]; c = the(s["club"], s["year"]); L = league(s["league"])
            self.said_clubs = self.said_years = True
            return self.v(1, [f"{N} played one season of professional football, {s['year']}, for {c} in {L}.",
                              f"{N}'s career was the {s['year']} season with {c}.",
                              f"{N} spent a single season, {s['year']}, with {c}."])
        if k == "one_club":
            c = the(f["club"], f["first"], f["last"]); self.said_clubs = self.said_years = True
            return self.v(1, [f"{N} spent his whole career with {c}: {words(f['seasons'])} seasons, {f['first']} to {f['last']}.",
                              f"{N} played {words(f['seasons'])} seasons, every one of them for {c}, from {f['first']} to {f['last']}.",
                              f"From {f['first']} to {f['last']}, {words(f['seasons'])} seasons, {N} played for nobody but {c}."])
        if k == "long_career":
            lgs = span["leagues"]; L = league(lgs[0]) if len(lgs) == 1 else "professional football"
            self.said_years = True
            R = runs(played)
            first_club = the(R[0][0], R[0][2], R[0][3])
            if len(R) == 1:
                self.said_clubs = True
                return self.v(1, [f"{N} played {words(f['seasons'])} seasons in {L}, all of them for {first_club}, from {f['first']} to {f['last']}.",
                                  f"{N} spent {words(f['seasons'])} seasons with {first_club}, {f['first']} to {f['last']}."])
            self.named_first = True
            return self.v(1, [f"{N} played {words(f['seasons'])} seasons in {L}, from {f['first']} to {f['last']}, starting with {first_club}.",
                              f"{N}'s career ran {words(f['seasons'])} seasons, {f['first']} to {f['last']}, beginning with {first_club}.",
                              f"Starting with {first_club} in {f['first']}, {N} played {words(f['seasons'])} seasons through {f['last']}."])
        if k == "crossed_leagues":
            R = runs(played)
            self.said_clubs = self.said_years = True
            byl = {}                                   # league family -> its runs, in order
            for c, lg, a, b, ys in R: byl.setdefault(LEAGUE_FAMILY.get(lg, lg), []).append((c, a, b, ys))
            # the same club in two leagues in a row (the AFL clubs of 1970, the AAFC
            # clubs of 1950) is ONE club named once, with both leagues after it
            legs = []
            for fam, rs in byl.items():
                if legs and len(legs[-1]["rs"]) == 1 and legs[-1]["rs"][0][0] == rs[0][0] and len(rs) == 1:
                    legs[-1]["fams"].append((fam, rs[0][1], rs[0][2])); legs[-1]["rs"][0][3].update(rs[0][3])
                else:
                    legs.append({"fams": [(fam, rs[0][1], rs[-1][2])], "rs": rs})
            bits = []; named = {}                      # plain name -> (code, year) first named under it
            def nm_for(c, a, b):
                plain = club_name(c, a)
                if plain in named:
                    c0, a0 = named[plain]
                    # the same club under another code (the Rock Island Independents of the 1925 NFL and the 1926 AFL
                    # are one club in the table) is named already; a different club with the same name is new
                    if c0 == c or (self.N.cid(c0, a0) and self.N.cid(c0, a0) == self.N.cid(c, a)): return f"the {plain.split()[-1]}"
                    return f"a new {plain}"
                named[plain] = (c, a); return the(c, a, b)
            def with_years(nm, ys):
                ys = sorted(ys)
                span = rng(ys[0], ys[-1]) if len(ys) == ys[-1] - ys[0] + 1 else years_phrase(ys)[3:]
                return f"{nm[:-1]}; {span})" if nm.endswith(")") else f"{nm} ({span})"
            for leg in legs:
                if len(leg["fams"]) > 1:
                    c, a, _, _ = leg["rs"][0]
                    bits.append(f"{nm_for(c, a, leg['fams'][-1][2])} in " +
                                " and ".join(f"{league(l)} ({rng(x, y)})" for l, x, y in leg["fams"]))
                    continue
                fam = leg["fams"][0][0]; rs = leg["rs"]
                if len(rs) <= 3:
                    parts = [with_years(nm_for(c, a, b), ys) for c, a, b, ys in rs]
                    lst = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
                else:
                    c, a, b, ys = rs[0]
                    lst = f"{with_years(nm_for(c, a, b), ys)} and {words(len(rs) - 1)} other clubs through {rs[-1][2]}"
                bits.append(f"{league(fam)} with {lst}")
            if len(bits) == 1:
                return self.v(1, [f"{N} played for {bits[0]}.", f"{N} was with {bits[0]}."])
            simple = all(b.startswith("the ") and " with " in b for b in bits)
            return self.v(1, [f"{N} played in {bits[0]} and in {bits[1]}." if len(bits) == 2 and simple else
                              f"{N}'s career crossed leagues: " + "; ".join(bits) + ".",
                              f"{N} moved between leagues: " + "; ".join(bits) + "."])
        if k == "war_gap":
            b, a = f["before"], f["after"]
            code_b = next(c for y, c, l in played if y == b)
            code_a = next(c for y, c, l in played if y == a)
            cb = the(code_b, b)
            self.said_years = False
            if code_a == code_b:
                # the same club both sides of the war: name it once
                if len(runs(played)) == 1: self.said_clubs = self.said_years = True
                return self.v(1, [f"{N} played for {cb} in {b} and did not play again until {a}, when he rejoined them.",
                                  f"{N}'s last game before the war came in {b} with {cb}; his next, in {a}, was with the same club.",
                                  f"{N} was with {cb} in {b}, then out of football until {a}, when he came back to them."])
            ca = the(code_a, a)
            if ca == cb:      # a different club with the same name (the AAFC Dodgers): say which league
                ca = f"the {ca.split()[-1]} of {league(next(l for y, c, l in played if y == a))}"
            return self.v(1, [f"{N} played for {cb} in {b} and did not play again until {a}, when he joined {ca}.",
                              f"{N}'s last game before the war came in {b} with {cb}; his next was in {a}, with {ca}.",
                              f"{N} was with {cb} in {b}, then out of football until {a} and {ca}."])
        if k == "played_then_coached":
            R = runs(played); first = the(R[0][0], R[0][2], R[0][3])
            n = len(span["years"])
            self.said_years = True
            co = f.get("coaching")
            if not co:
                when = rng(f["first_coach"], f["last_coach"])
                return f"{N} played {seasons_word(n)}, beginning with {first} in {span['years'][0]}, and coached afterwards, {when}."
            same_club = co["club"] == R[0][0]
            verb, job = self.head_job(co, its_club_already_named=same_club)
            verb2, job2 = self.head_job(co) if same_club else (verb, job)   # one mention, one naming
            self.coach_tail_pending = self.coach_tail(co)
            head = co["was_head_coach"]
            opts = [(True, f"{N} played {seasons_word(n)}, beginning with {first} in {span['years'][0]}, and "
                           + (f"{verb} {job}." if head else f"then coached, {job}.")),
                    (False, f"{N} was a player first — {seasons_word(n)} from {span['years'][0]} — and "
                            + (f"then {job2}." if head else f"coached after, {job2}."))]
            names_first, sentence = self.v(1, opts)
            # only the variant that NAMES his first club may be followed by "from there"
            self.named_first = names_first
            return sentence
        if k == "defunct_club":
            L = league(f["league"]); R = runs(played)
            if len(R) == 1:
                c, lg, a, b, ys = R[0]; n = len(span["years"])
                self.said_clubs = self.said_years = True
                cn = the(c, a, b)
                if n == 1:
                    return self.v(1, [f"{N} played for {cn} of {L} in {a}.", f"{N} was with {cn}, of {L}, in {a}."])
                return self.v(1, [f"{N} played {words(n)} seasons for {cn} of {L}, {years_phrase(ys)[3:] if years_phrase(ys).startswith('in ') else years_phrase(ys)}.",
                                  f"{N} spent {words(n)} seasons with {cn}, of {L}, {years_phrase(ys)}."])
            n = len(span["years"]); self.said_years = True
            c = the(R[0][0], R[0][2], R[0][3]); self.named_first = True
            return self.v(1, [f"{N} played {words(n)} seasons in {L}, {span['years'][0]} to {span['years'][-1]}, starting with {c}.",
                              f"{N}'s career, {words(n)} seasons in {L} from {span['years'][0]}, began with {c}."])
        if k == "distinction":
            s = f["season"]; c = the(s["club"], s["year"]); L = league(s["league"])
            k_more = int(round((1 - f["percentile"]) * f["n"]))
            self.nums += 1
            phrase = did(f["measure"], f["value"])
            comp = ""
            if f.get("companion") and self.nums < 3 and f["measure"] in COMPANION_PHRASE and f["companion"] > 0:
                comp = " " + COMPANION_PHRASE[f["measure"]].format(n=n_(f["companion"])); self.nums += 1
            if k_more == 0: tail = f"no one in {L} {MORE[f['measure']]} that season"
            elif k_more == 1: tail = f"only one man in {L} {MORE[f['measure']]} that season"
            else: tail = f"only {words(k_more)} men in {L} {MORE[f['measure']]} that season"
            if k_more > 1: self.nums += 1
            return self.v(1, [f"{N} {phrase}{comp} for {c} in {s['year']}; {tail}.",
                              f"In {s['year']}, playing for {c}, {N} {phrase}{comp} — {tail}."])
        if k == "salience":
            R = runs(played); n = len(span["years"]); self.nums += 1
            self.said_years = True
            if len(R) == 1:
                c = the(R[0][0], R[0][2], R[0][3]); self.said_clubs = True
                where = f"for {c}"
            else:
                where = f"across {words(len(R))} clubs"
            when = f"over {words(n)} seasons, {rng(span['years'][0], span['years'][-1])}" if n > 1 else f"in {span['years'][0]}"
            return self.v(1, [f"{N} {did(f['measure'], f['total'])} {where} {when}.",
                              f"Over {words(n)} seasons {N} {did(f['measure'], f['total'])} {where}." if n > 1
                              else f"{N} {did(f['measure'], f['total'])} {where} in {span['years'][0]}."])
        # plain: no shape, no distinction, nothing above the floor. Say the career.
        R = runs(played); n = len(span["years"])
        if len(R) == 1:
            c, lg, a, b, ys = R[0]; self.said_clubs = self.said_years = True
            if n == 1: return f"{N} played for {the(c, a)} in {a}."
            return self.v(1, [f"{N} played {words(n)} seasons for {the(c, a, b)}, {years_phrase(ys)[3:] if years_phrase(ys).startswith('in ') else years_phrase(ys).replace('from ', '')}.",
                              f"{N} spent {words(n)} seasons with {the(c, a, b)}, {years_phrase(ys)}."])
        self.said_years = True; self.named_first = True
        return self.v(1, [f"{N} played {words(n)} seasons, {span['years'][0]} to {span['years'][-1]}, starting with {the(R[0][0], R[0][2], R[0][3])}.",
                          f"{N}'s career ran from {span['years'][0]} to {span['years'][-1]}, {words(n)} seasons, beginning with {the(R[0][0], R[0][2], R[0][3])}."])

    # ------------------------------------------------------------- body
    def span(self, f):
        out = []
        n = len(f["years"])
        if not self.said_clubs:
            R = runs(f["played"], by_club_only=True)
            first = R[0]
            contiguous = len(first[4]) == first[3] - first[2] + 1
            # a player-coach: the lead already named the one club and the years.
            # Saying them again as a second sentence is repetition, not information.
            if len(R) == 1 and club_name(R[0][0], R[0][2]) in self.emitted:
                self.said_clubs = True
                R = []
            elif self.named_first and len(R) > 1 and contiguous:
                # the lead named where he started; say where he went, not where he started again
                rest = self.clubs_phrase(f["played"], exclude=(first[0], first[1]))
                if len(R) <= 4 and rest:
                    out.append(self.v(3, [f"From there he went to {rest}.", f"He moved on to {rest}."]))
                else:
                    names = list(dict.fromkeys(self.the(c, a, b) for c, lg, a, b, ys in R[1:]))
                    out.append(f"He went on to {words(len(names))} more clubs: " + ", ".join(names[:-1]) + " and " + names[-1] + ".")
            elif len(R) <= 3:
                ph = self.clubs_phrase(f["played"])
                if not self.said_years and n > 1:
                    out.append(self.v(3, [f"He played {words(n)} seasons: for {ph}.",
                                          f"His {words(n)} seasons were with {ph}."]))
                elif ph:
                    out.append(self.v(3, [f"He played for {ph}.", f"His clubs were {ph}."]))
            else:
                names = list(dict.fromkeys(self.the(c, a, b) for c, lg, a, b, ys in R))
                lst = ", ".join(names[:-1]) + " and " + names[-1]
                if not self.said_years and n > 1:
                    out.append(f"Over {words(n)} seasons he played for {words(len(names))} clubs: {lst}.")
                else:
                    out.append(f"He played for {words(len(names))} clubs: {lst}.")
            self.said_clubs = True
        gaps = [(a, b) for a, b in f["gaps"]
                if not (set(range(a + 1, b)) & {1942, 1943, 1944, 1945} and self.F["lead_kind"] == "war_gap")]
        if len(gaps) == 1:
            a, b = gaps[0]
            out.append(f"He did not play in {a + 1}." if b - a == 2
                       else f"He was out of the game from {a + 1} to {b - 1}.")
        elif len(gaps) > 1:
            spans = [str(a + 1) if b - a == 2 else rng(a + 1, b - 1) for a, b in gaps]
            out.append("He was in and out of the game, missing " + ", ".join(spans[:-1]) + " and " + spans[-1] + ".")
        return " ".join(out)

    def coached(self, f):
        co = f.get("coaching")
        if not co:
            return f"He coached afterwards, from {f['first']} to {f['last']}." if f["n"] > 1 else f"He coached in {f['first']}."
        self.coach_tail_pending = self.coach_tail(co)
        verb, job = self.head_job(co)
        if co["was_head_coach"]:
            # "came back as" only where he is returning to a club he played for
            played_here = co["club"] in {c for _, c, _ in
                                         next(x for x in self.F["facts"] if x["kind"] == "career_span")["played"]}
            return f"He later became {job}." if verb == "became" else \
                self.v(10, [f"He was later {job}."] + ([f"He came back as {job}."] if played_here else []))
        return f"He later coached, {job}."

    def total(self, f):
        if self.nums >= 3: return ""
        self.nums += 1
        return self.v(4, [f"In all he {did(f['measure'], f['total'])} over {words(f['seasons_with'])} seasons.",
                          f"Over {words(f['seasons_with'])} seasons he {did(f['measure'], f['total'])}."])

    # ------------------------------------------------------------- close
    def close(self, f):
        k = f["kind"]
        if k == "death":
            where = f", in {strip_usa(f['place'])}" if f.get("place") else ""
            return f"He died on {date_text(f['date'])}{where}."
        if k == "military":
            if f["source"] == "pfa":
                return self.v(6, [f"He served in the {f['text']}.", f"He was a {f['text']} veteran."])
            return f"His service record, as the guide printed it: “{f['text']}”"
        if k == "notes":
            g = re.sub(r"\s*\(.*?\)", "", f["guide"])
            g = re.split(r"\s+\d{4}", g)[0].strip().split()[-1]
            q = f["text"].replace("“", "‘").replace("”", "’").replace('"', "’")   # the guide's own quotes nest as singles
            return self.v(9, [f"The {f['year']} {g} guide put it this way: “{q}”",
                              f"“{q}” — the {f['year']} {g} guide."])
        if k == "family":
            return f"The guide listed him as “{f['text']}”"
        return ""

    def render(self):
        F = self.F; facts = F["facts"]
        if F.get("coaching_only"): return self.render_coaching_only()
        span = next(f for f in facts if f["kind"] == "career_span")
        S = [self.lead(facts[0], span)]
        self.emitted = " ".join(S)
        if self.coach_tail_pending: pending_tail, self.coach_tail_pending = self.coach_tail_pending, ""
        else: pending_tail = ""
        for f in facts[1:]:
            k = f["kind"]
            if k == "career_span":
                t = self.span(f)
                if t: S.append(t)
            elif k == "coached":
                S.append(self.coached(f))
                if self.coach_tail_pending: S.append(self.coach_tail_pending); self.coach_tail_pending = ""
            elif k == "career_total":
                t = self.total(f)
                if t: S.append(t)
            elif f["slot"] == "close": S.append(self.close(f))
        if pending_tail: S.insert(1, pending_tail)
        return " ".join(x for x in S if x)


    def render_coaching_only(self):
        facts = self.F["facts"]; lead = facts[0]
        # THREE LEADS, ONE FOR EACH SHAPE A COACHING-ONLY CAREER TAKES: a head coach, a
        # man who never held a head job, and a man whose career has no shape at all
        # beyond its length. The middle one did not exist until 2026-09-09 and its 967
        # men returned 503.
        if lead["kind"] == "coaching_career": S = [self.coaching_career_lead(lead)]
        elif lead["coaching"]["was_head_coach"]: S = [self.coach_lead(lead)]
        else: S = [self.assistant_lead(lead)]
        for f in facts[1:]:
            if f["kind"] == "coaching_span":
                t = self.coaching_span(f)
                if t: S.append(t)
            elif f["slot"] == "close": S.append(self.close(f))
        return " ".join(x for x in S if x)


def write(F):
    return Writer(F).render()
