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
import os, re, json, unicodedata

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


def birth_date(v):
    """'July 17, 1982' -> '1982-07-17'. An already-ISO date reads as itself.

    Only a spelled-out month is read. A bare numeric date is NOT reordered:
    '2001-12-10' and '2001-10-12' are left as two different dates, because
    deciding which is day and which is month would be a correction, not a reading.
    """
    t = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
    if m:
        return t
    m = re.match(r"^([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})$", t)
    if m and m.group(1).lower() in _MONTH:
        return "%s-%02d-%02d" % (m.group(3), _MONTH[m.group(1).lower()], int(m.group(2)))
    return None


# The ordinal suffix on the OVERALL PICK is optional: Pro Football Archives prints both
# "(80th overall)" and "(86 overall)". Requiring it left five of its own selections
# unreadable, and a reader that cannot read the archive hides real disagreements while
# claiming to remove false ones (gate_readings R3).
_DRAFT_STR = re.compile(r"(\d+)(?:st|nd|rd|th)\s+round\s*\((\d+)(?:st|nd|rd|th)?\s+overall\)\s*(\d{4})", re.I)


def draft(v):
    """A draft selection -> 'YYYY r{round} p{overall}'.

    The club is deliberately NOT part of the reading. An overall pick number is
    unique within a draft year, so year+round+overall IS the selection; the club
    follows from the pick rather than being an independent fact about it. That is
    what makes PFR's 'TAM' and nflverse's 'TB' the same selection rather than two.
    Both strings stay on the panel verbatim -- the reading decides only whether
    the two records are the same selection, never what is displayed.
    """
    if isinstance(v, dict):
        y, r, p = v.get("year"), v.get("round"), v.get("overall_pick")
        return "%s r%s p%s" % (y, r, p) if None not in (y, r, p) else None
    m = _DRAFT_STR.search(str(v))
    return "%s r%s p%s" % (m.group(3), int(m.group(1)), int(m.group(2))) if m else None


_SAINT = re.compile(r"^s(?:t|aint)\.?$", re.I)
_COUNTRY = re.compile(r"[\s,.]*(?:u\.?\s?s\.?\s?a\.?|u\.?\s?s\.?|united\s+states(?:\s+of\s+america)?)[\s,.]*$", re.I)
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
    return " ".join(out) or None


def place(v):
    """A printed place -> the place, with a TRAILING country token removed and case and
    punctuation folded. Ruled by Ryan, 2026-09-07, conditionally on the fold being clean;
    measured clean over all 2,874 birth-place and 723 death-place pairs -- every collapse
    it makes is a trailing `USA`, a trailing space, punctuation or case, and none is
    semantic.

    NOTHING ELSE IS REMOVED. The city and the state stay, in the order printed. Reducing
    a place to its city would make `Springfield, IL` and `Springfield, MA` one place, and
    a fold that can do that is not a reading.
    """
    t = unicodedata.normalize("NFKC", str(v)).strip()
    if not t or t.lower() in ("none", "null", "n/a", "-"):
        return None
    t = _COUNTRY.sub("", t)
    k = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower())).strip()
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
