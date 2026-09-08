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
READERS = {"height": height, "weight": weight, "birth_date": birth_date, "draft": draft,
           "college": college, "birth_place": place, "death_place": place}


def read(field, value):
    """The reading, or None when the value cannot be read without guessing."""
    fn = READERS.get(field)
    return fn(value) if fn else None
