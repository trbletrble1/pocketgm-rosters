"""Readings: a printed label mapped to a field, a printed value read into a
canonical form. Ruled by Ryan on 2026-09-07.

A READING IS NOT A CORRECTION. The store keeps exactly what the source printed.
The reading sits beside it, marked derived, and can be recomputed or withdrawn
without touching a claim. `birth_date_as_printed` is the precedent.

Why it was ruled. The bio panel was manufacturing disagreements between sources
that agree:

  Jay Rhodemyre   PFA 6-1   guide '61"'      -- listed as a height disagreement
  Derek Carr      PFR OAK   nflverse LV      -- listed as a draft disagreement

51 of 73 unparsable guide heights agree with PFA once read as digits, and 182 of
275 sampled draft disagreements are one selection under two club vocabularies
(GNB/GB, SFO/SF, NWE/NE, TAM/TB). A fabricated disagreement is worse than a hole:
a hole you can see, while this looks like scholarship -- two sources, both cited,
honestly held apart -- and it survives every gate, because the gates check that
disagreements are HELD, and they are being held faithfully, having been invented.

What this module will NOT do, by ruling:

  * It maps only labels that are unambiguously a field. `guide.Aye`,
    `guide.Cracral Information` and `guide.GIANTS vs. PORTSMOUTH` stay as printed
    -- OCR damage and section headings, not field names. Mapping them would be
    inventing structure the source does not have.
  * It refuses any value it cannot read without guessing. `6/114"`, `5'10!2,"`
    and `& feet 3` are left alone. Refusals are COUNTED, never silent, and
    gate_readings prints the count.

An unread value can neither corroborate nor contradict, so it takes no part in
the disagreement test. It stays on the panel verbatim and is counted. That is a
stated limit: two unreadable strings that genuinely differ will not be flagged.
"""
import os, re, sys, json, unicodedata

# THE date reading. Loaded by path because src/ and service/ are not one package;
# there is one implementation and this is it.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "service"))
import dates as _model_dates


BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DECL = os.path.join(BASE, "declarations", "readings.json")
_D = json.load(open(DECL, encoding="utf-8"))

# label -> field, derived from the declaration so widening it is a diff there
LABELS = {}
for _field, _labs in _D["LABELS"].items():
    for _l in _labs:
        LABELS[_l] = _field

_FRACTION = re.compile(r"[%!VvxX]")           # mangled halves: 6'V2", 5'11!4"
_SEP = r"(?:feet|ft\.?|['’°:./′-])"      # '-' is the archive's own form: PFA writes 5-10


def height(v):
    """A printed height -> F-I. Refuses anything carrying a fraction mark or more
    digits than a height has: '6/114\"' and '6:142' are not 6-11 and 6-14."""
    t = unicodedata.normalize("NFKC", str(v)).strip()
    t = t.replace("”", '"').replace("“", '"').replace("″", '"')
    if _FRACTION.search(t) or len(re.sub(r"\D", "", t)) > 3:
        return None
    m = re.match(r"^(\d)\s*" + _SEP + r"?\s*(\d{1,2})\s*(?:in\.?|\")?\s*[,.]?$", t)
    if m and int(m.group(2)) < 12:
        return "%s-%d" % (m.group(1), int(m.group(2)))
    m = re.match(r"^(\d)\s*" + _SEP + r"?\s*[,.]?$", t)
    return "%s-0" % m.group(1) if m else None


def weight(v):
    """A printed weight -> pounds as a bare integer string."""
    m = re.match(r"^(\d{2,3})\s*(?:lbs?\.?)?$", unicodedata.normalize("NFKC", str(v)).strip())
    return m.group(1) if m else None


_MONTH = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


_APOSTROPHE = re.compile(r"['\u2019]")


def person_name(v):
    """A printed name reduced for comparison. THE one implementation.

    There were 29 of these across src/ and service/, in 8 distinct behaviours, and
    four pairs of them decided the same question differently -- the awards ingest
    against the measurement of its own leads, the player promotion route against the
    coach one, duplicate detection against promotion, two ingests joining on the same
    index. About 1,200 names carry the punctuation they disagreed on.

    THE THREE CHOICES, made deliberately and measured first:

    An APOSTROPHE IS INSIDE A WORD and is deleted: `O'Brien` and `OBrien` both give
    `obrien`, and a source that prints one is matched by a source that prints the
    other. Turning it into a space would have made them disagree.

    EVERY OTHER PUNCTUATION MARK SEPARATES and becomes a space: `Jean-Paul` and
    `Jean Paul` both give `jean paul`, `Y.A.` and `Y. A.` both give `y a`. The two
    rules pull opposite ways on the same input, which is why one blanket rule was
    wrong in both directions before.

    A SUFFIX IS KEPT. `Tony Adamle Jr.` stays `tony adamle jr`. Stripping it would
    unify one more man in the whole archive and would silently merge a father with a
    son -- a name is not a person, and the cheap direction is the one that never
    conflates. A source that omits the suffix is still reached by the surname-and-
    initial rule held to a club-season, which is where that job belongs.

    ACCENTS FOLD, they are not deleted. `Jose` and `Jose` are one man; eleven of the
    old implementations turned `Jose` into `Jos` by stripping the letter with its mark.

    Measured over the archive's 40,255 distinct printed names: this unifies 11 of the
    1,760 people held under more than one name -- the rest are genuinely different
    names, like Johnny Blood and Johnny McNally -- and puts 2,137 people in a key they
    share with someone else, which is the base rate of men with the same name and is
    within 8 of every alternative tested. THE CHOICE IS NEARLY FREE; what was costly
    was having eight of them.
    """
    t = unicodedata.normalize("NFKD", str(v or ""))
    t = "".join(ch for ch in t if not unicodedata.combining(ch)).lower()
    t = _APOSTROPHE.sub("", t)
    t = re.sub(r"[^a-z0-9]", " ", t)
    return " ".join(t.split())


def birth_date(v, source_id=None):
    """A printed date -> `YYYY-MM-DD`, or None where the string carries no calendar day.

    ONE IMPLEMENTATION, IMPORTED. This used to be a second, poorer date reader living
    beside `service/dates.py`: it read `2005-08-14` and not `2005-8-14`, knew nothing
    of `c. 1948`, `(aged 72)` or `17 July 1982`, and the difference showed up as a
    dozen manufactured disagreements in Crippen's register. The archive's own standing
    rule is that a gate or a reader which reimplements what it checks can pass while
    the thing it checks has changed -- and this was the third pair of duplicate
    implementations found on 2026-09-08, after the grouping rule in bio_select and
    gate_readings. `service/dates.py` is the reading; this is a thin adapter to the
    key shape the family comparison wants.

    A BARE NUMERIC DATE IS STILL NOT REORDERED unless its source has DECLARED its
    order with the measurement behind it -- see
    service/declarations/date-formats-by-source.json. `2001-12-10` and `2001-10-12`
    remain two different dates for a source that has not been measured.

    Only a day-precision reading returns a value, as before: a year or a year-month
    is not a day, and folding one into a day would be the coarsening this family has
    always refused.
    """
    r = _model_dates.read(v, source_id) if source_id else _model_dates.read(v)
    if not r or r.get("precision") != "day":
        return None
    return "%04d-%02d-%02d" % (r["year"], r["month"], r["day"])


# The ordinal suffix on the OVERALL PICK is optional: Pro Football Archives prints both
# "(80th overall)" and "(86 overall)". Requiring it left five of its own selections
# unreadable, and a reader that cannot read the archive hides real disagreements while
# claiming to remove false ones (gate_readings R3).
_DRAFT_STR = re.compile(r"(\d+)(?:st|nd|rd|th)\s+round\s*\((\d+)(?:st|nd|rd|th)?\s+overall\)\s*(\d{4})", re.I)


def draft(v):
    """A draft selection -> a DICT: {year, league, kind, numbering} with either
    {round, overall} or {order}.

    A SELECTION IS NOT IDENTIFIED BY YEAR AND PICK. This reading used to be the string
    `YYYY r{round} p{overall}`, on the stated ground that "an overall pick number is
    unique within a draft year". **It is not.** Measured 2026-09-08 across the whole
    range: 72 of 90 years hold more than one draft numbering its picks from 1, and one
    year holds five. 1950 has an NFL draft and an AAFC allocation draft -- overall pick
    1 is Leon Hart in one and Chet Mutryn in the other. 1965 has NFL, AFL and CFL.

    LEAGUE AND KIND ARE IN THE READING, where a consumer has to see them, rather than
    inside a value where they can be ignored. They were always present as
    `league_from_filename` and `draft_kind`; nothing downstream was obliged to look, and
    a naive join on (year, pick) put one man's selection under another's name.

    A FIELD ONLY ONE SIDE CARRIES IS SILENCE, NOT A DIFFERENCE. reading_view.same()
    compares dict readings on the fields BOTH carry, so a record that states no league
    still matches one that does -- which is right, because 135 contested rows are a
    source declining to name the league and not a second draft. `league` and `kind` are
    therefore OMITTED when unknown rather than filled with a placeholder, which would
    turn silence into a claim.

    A SELECTION WITH AN ORDER AND NO ROUND IS READ AS ONE. Ruled by Ryan, 2026-09-08.
    An expansion, allocation or dispersal draft is not run in rounds: PFA prints those
    pages with the columns `Team | Player | Pos | College | Notes` and NO Round and NO
    Overall at all. The 1960 AFL draft is printed as two sittings, team by team. Such a
    selection reads to {year, order, league, kind} -- `round` and `overall` are ABSENT,
    not zero and not null, because absent is the only one of the three that means the
    document does not say. Zero would sort; null would compare. 602 held claims and
    roughly 1,631 selections still on disk are behind this.

    AND THAT IS NOT ENOUGH ON ITS OWN, which is why `numbering` is here. Omitting
    `round` and `overall` would leave an ordered selection and a numbered one sharing
    only year and league -- and `same()` compares the fields BOTH carry, so it would
    call them one selection. The rule that protects an unstated league would join a
    1960 AFL allocation pick to a 1960 AFL draft pick. So the reading states HOW it is
    numbered, in a field both forms carry and neither can be silent about: `order` or
    `round_and_pick`. A field only one side carries is silence; a field both sides
    carry is a comparison, and this difference must be compared.
    """
    if isinstance(v, dict):
        y, r, p = v.get("year"), v.get("round"), v.get("overall_pick")
        if y is not None and None in (r, p):
            o = v.get("printed_order", v.get("order"))
            if o is None: return None
            out = {"year": int(y), "order": int(o), "numbering": "order"}
            lg = (v.get("league_from_filename") or v.get("league_from_link")
                  or v.get("league"))
            if lg and str(lg) != "?": out["league"] = str(lg).upper()
            k = v.get("draft_kind")
            if k: out["kind"] = str(k)
            return out
        if None in (y, r, p): return None
        out = {"year": int(y), "round": int(r), "overall": int(p),
               "numbering": "round_and_pick"}
        lg = (v.get("league_from_filename") or v.get("league_from_link")
              or v.get("league"))
        if lg and str(lg) != "?": out["league"] = str(lg).upper()
        k = v.get("draft_kind")
        if k: out["kind"] = str(k)
        return out
    m = _DRAFT_STR.search(str(v))
    if not m: return None
    # a printed string states no league and no kind: silence, not a placeholder
    return {"year": int(m.group(3)), "round": int(m.group(1)), "overall": int(m.group(2)),
            "numbering": "round_and_pick"}


_SAINT = re.compile(r"^s(?:t|aint)\.?$", re.I)
_COUNTRY = re.compile(r"[\s,.]*(?:u\.?\s?s\.?\s?a\.?|u\.?\s?s\.?|united\s+states(?:\s+of\s+america)?)[\s,.]*$", re.I)
# THE FIFTY STATES AND DC, by their USPS abbreviation. Ruled by Ryan, 2026-09-07:
# `Los Angeles, CA` and `Los Angeles, California` are one place.
_STATES = {
 "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas", "ca": "california",
 "co": "colorado", "ct": "connecticut", "de": "delaware", "fl": "florida", "ga": "georgia",
 "hi": "hawaii", "ia": "iowa", "id": "idaho", "il": "illinois", "in": "indiana",
 "ks": "kansas", "ky": "kentucky", "la": "louisiana", "ma": "massachusetts",
 "md": "maryland", "me": "maine", "mi": "michigan", "mn": "minnesota", "mo": "missouri",
 "ms": "mississippi", "mt": "montana", "nc": "north carolina", "nd": "north dakota",
 "ne": "nebraska", "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico",
 "nv": "nevada", "ny": "new york", "oh": "ohio", "ok": "oklahoma", "or": "oregon",
 "pa": "pennsylvania", "ri": "rhode island", "sc": "south carolina", "sd": "south dakota",
 "tn": "tennessee", "tx": "texas", "ut": "utah", "va": "virginia", "vt": "vermont",
 "wa": "washington", "wi": "wisconsin", "wv": "west virginia", "wy": "wyoming",
 "dc": "district of columbia",
}
# A COLLEGE ABBREVIATION FOLDS ONLY WHERE IT HAS EXACTLY ONE POSSIBLE SCHOOL.
# Ruled by Ryan 2026-09-07 and DECLARED in declarations/readings.json under
# VALUE_READINGS.college.COLLEGE_SYNONYMS, with a reason on every entry and on every
# refusal. Read from the declaration, never typed here, so the rule and the code
# cannot drift. Six fold; `georgetown`, `cornell`, `nebraska` and `lebanon` are
# refused because a second real school competes for the same short form, and a
# refused pair stays a disagreement.
_POSDECL = None


def _positions():
    global _POSDECL
    if _POSDECL is None:
        _POSDECL = json.load(open(os.path.join(BASE, "declarations", "positions.json"),
                                  encoding="utf-8"))
    return _POSDECL


_MULTI = re.compile(r"[-/,;]|\s+or\s+", re.I)


def position(v):
    """A printed position -> {role, spot?, alignment?}, or None.

    RULED BY RYAN, 2026-09-09, in three parts, and the third is the one that matters.

      EXPAND THE ABBREVIATION. `LH`, `Left Halfback` and `Left halfback` are one fact.
        Notation, and safe.
      A SIDE IS PART OF THE POSITION. Left Halfback and Right Halfback are a real
        disagreement; 1920s formations distinguished them and the sources are recording
        something. Sides are NOT folded away.
      AN UNSTATED SIDE IS SILENCE. `Halfback` does not contest `Left Halfback`. A source
        printing `HB` is not asserting he was not a left halfback -- it is not saying.

    THE SILENCE IS reading_view.same()'s, NOT A SECOND IMPLEMENTATION. It compares two
    dict readings on the fields BOTH carry, so a reading that omits `spot` matches one
    that states it. `spot` and `alignment` are omitted when unknown rather than filled
    with a placeholder, exactly as `league` and `kind` are in the draft reading, because a
    placeholder turns silence into a claim.

    WHY THIS EXISTS AT ALL. `position`, `statscrew.position` and `pfa.position_career`
    were three families and build_contested walks only DECLARED ones, so the archive could
    not record a disagreement about a position at all -- 348 real ones were invisible.

    A MULTI-POSITION STRING IS REFUSED, not split. `HB-QB` and `RDT-RDE-LDE-LDT` state a
    LIST, and whether a list of two contests a list of one is a rule Ryan has not made.
    Refusals are counted and take no part in the disagreement test.
    """
    if isinstance(v, dict):
        v = v.get("code") or v.get("position") or v.get("value")
    if v is None: return None
    t = str(v).strip()
    if not t or _MULTI.search(t): return None
    d = _positions()
    hit = d["codes"].get(t.upper()) or d["names"].get(re.sub(r"[^a-z]", "", t.lower()))
    return dict(hit) if hit else None


def _load_college_synonyms():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     "declarations", "readings.json")
    try:
        v = json.load(open(d))["VALUE_READINGS"]["college"]["COLLEGE_SYNONYMS"]["folds"]
    except Exception:
        return {}
    return {k: x["to"] for k, x in v.items()}


_COLLEGE_SYNONYMS = _load_college_synonyms()
_COLLEGE_DROP = {"university", "of", "the"}
_COLLEGE_ABBR = {"univ": "university", "u": "university"}


def college(v):
    """A printed college -> the school, with the abbreviation expanded and the word
    University dropped. Ruled by Ryan, 2026-09-07: `Ohio St.` and `Ohio State` are one
    school.

    `St.` IS EXPANDED ONLY AS THE LAST WORD. `Ohio St.` is Ohio State; `St. Mary's` is
    Saint Mary's, and reading it as `State Mary's` would be a guess dressed as a reading.
    Position is what separates them and position is all that is used.

    `College` IS NEVER DROPPED. Boston College and Boston University are two schools, and
    dropping both words would make them one -- a false agreement, which is worse than the
    two disagreements it would hide. Only `University` goes, because nothing in the corpus
    is distinguished by it alone.
    """
    t = unicodedata.normalize("NFKC", str(v)).strip()
    if not t or t.lower() in ("none", "null", "n/a", "-"):
        return None
    words = re.sub(r"[^\w\s&'-]", " ", t.lower()).split()
    if not words:
        return None
    words = [(_COLLEGE_ABBR.get(w.rstrip("."), w) if i < len(words) - 1 else w)
             for i, w in enumerate(words)]
    if _SAINT.match(words[-1]) and len(words) > 1:
        words[-1] = "state"                      # trailing St. -> State
    out = [w for w in words if w not in _COLLEGE_DROP]
    k = " ".join(out) or None
    return _COLLEGE_SYNONYMS.get(k, k)


def place(v):
    """A printed place -> the place, with a TRAILING country token removed and case and
    punctuation folded. Ruled by Ryan, 2026-09-07, conditionally on the fold being clean;
    measured clean over all 2,874 birth-place and 723 death-place pairs -- every collapse
    it makes is a trailing `USA`, a trailing space, punctuation or case, and none is
    semantic.

    A TRAILING STATE ABBREVIATION IS EXPANDED. Ruled by Ryan, 2026-09-07: `Los Angeles,
    CA` and `Los Angeles, California` are one place. Three limits keep it a reading
    rather than a rewrite, and all three are what stop it reaching further:

      1. ONLY THE LAST TOKEN, and only when something precedes it. Position is what
         separates a state from a word, exactly as it does for `St.` in college(). `IN`,
         `OR`, `OK`, `ME`, `LA` and `DE` are all English words as well as states, and a
         lone `LA` is a place this reader will not guess at -- it stays as printed.
      2. NOTHING ELSE IS REMOVED. The city and every qualifier stay, in the order
         printed. `near Whitesboro, TX` reads to `near whitesboro texas` and
         `Whitesboro, Texas` to `whitesboro texas`, and those still DISAGREE -- because
         one source says the town and the other says somewhere nearby, and that
         difference was never about the state name.
      3. NO CITY IS EVER DROPPED. Reducing a place to its state would make
         `Springfield, IL` and `Chicago, IL` one place, and a fold that can do that is
         not a reading.

    The trailing country is removed first, so `Chicago, Illinois, U.S` and `Chicago, IL`
    both reach `chicago illinois`.
    """
    t = unicodedata.normalize("NFKC", str(v)).strip()
    if not t or t.lower() in ("none", "null", "n/a", "-"):
        return None
    t = _COUNTRY.sub("", t)
    k = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()
    if not k:
        return None
    w = k.split()
    if len(w) > 1 and w[-1] in _STATES:          # a state, never a lone token
        w[-1:] = _STATES[w[-1]].split()
        k = " ".join(w)
    return k or None


# birth_date_as_printed deliberately has NO reader. Its values are compound
# "born" statements in two house styles -- 'Six Mile, S.C., June 27, 1916.' and
# 'August 28, 1919 (28) in Santa Ana, Calif.' -- so pulling a date out of one is
# a parse, not a reading, and would be a separate ruling. The field keeps what
# was printed and its values compare as written.
_MONTHS = {m.lower(): i for i, m in enumerate(
    "January February March April May June July August September October November "
    "December".split(), 1)}


def _calendar_day(s):
    """A printed game date -> (y, m, d), or None. Two formats and no third:
    `November 9, 1975` from a box score, `1970-09-18` from a game log."""
    s = str(s or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return tuple(int(x) for x in m.groups())
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$", s)
    if m and m.group(1).lower() in _MONTHS:
        return (int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    return None


def game(v):
    """A game, as two sources describe it. Ruled by Ryan, 2026-09-10.

    A BOX SCORE AND A GAME LOG DESCRIBE THE SAME GAME. They already share a subject
    built from PFA's own identifier and have avoided collision only because their year
    ranges do not overlap. Two claims on one subject in two families would sit side by
    side with nothing connecting them -- a silent NON-comparison, which is worse than a
    merge because nothing looks wrong.

    THE READING IS A RENAMING AND A DATE, AND NOTHING ELSE. `date` and
    `date_as_printed` are the same field under two names in two formats, so both are
    read to a calendar day -- the same treatment dates already get everywhere, and the
    printed strings are never rewritten.

    EVERYTHING ELSE IS SILENCE AND IS MEANT TO BE. A box score carries venue, location,
    attendance and weather; a game log carries the clubs, their scores and the result.
    Neither carries the other's, so `same()` compares them on the fields BOTH hold and
    ignores the rest. That is the existing mechanism, not a new one. If a later source
    ever carries both, they will compare then without this being touched.

    AN UNREADABLE DATE IS ITS OWN GROUP, as everywhere: unreadable is an answer, not a
    licence to merge."""
    if not isinstance(v, dict):
        return None
    out = {}
    for k in ("pfa_game_id", "league", "year", "number"):
        if v.get(k) is not None:
            out[k] = str(v[k]).lower() if k in ("pfa_game_id", "league") else v[k]
    d = _calendar_day(v.get("date") or v.get("date_as_printed"))
    if d:
        out["calendar_day"] = list(d)
    elif v.get("date") or v.get("date_as_printed"):
        return None
    for k in ("venue", "location", "attendance"):
        if v.get(k) is not None:
            out[k] = v[k]
    if isinstance(v.get("clubs"), dict) and v["clubs"]:
        out["clubs"] = sorted(str(x).upper() for x in v["clubs"])
    return out or None


def snap_counts(v):
    """A postseason snap count -- how much of the game was a man's.

    Ruled by Ryan, 2026-09-10. Three integers, and the printed TOTAL is deliberately
    absent: OFF + DEF + ST equals it on every row measured, so it is arithmetic and
    not evidence. Where a row does NOT add up the ingest keeps the printed total and
    says so, and this reader carries it through rather than pretending it agreed.

    THE READING IS A COERCION, NOT A JUDGEMENT. There is one source today; the family
    exists so a second one can contest rather than sit beside it. A value whose three
    figures are not whole numbers is refused, because a snap is counted and not
    measured."""
    if not isinstance(v, dict):
        return None
    out = {}
    for k in ("offense", "defense", "special_teams"):
        if v.get(k) is None:
            continue
        try:
            out[k] = int(str(v[k]).strip())
        except (TypeError, ValueError):
            return None
    if not out:
        return None
    if v.get("total_as_printed") is not None:
        try: out["total_as_printed"] = int(str(v["total_as_printed"]).strip())
        except (TypeError, ValueError): return None
    return out


# REGISTERED UNDER THE FAMILY NAME, because reading_view looks a reader up BY FAMILY.
# Declaring the family `playoff_snap_counts` and the reader `snap_counts` made A3 fail
# on its own worked example -- the gate catching a two-name mismatch a second time.
READERS = {"game": game, "playoff_snap_counts": snap_counts, "height": height, "weight": weight, "birth_date": birth_date, "draft": draft,
           "college": college, "birth_place": place, "death_place": place,
           "position": position}


def read(field, value):
    """The reading, or None when the value cannot be read without guessing."""
    fn = READERS.get(field)
    return fn(value) if fn else None
