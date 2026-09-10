"""WHAT A THING IS. One implementation of the four classifications the read
service applies to every response, read from declarations/classification.json.

Nothing here is a literal and nothing here reads a name. Until 2026-09-09 all
three were string tests inside queries.py:

    r["store"].startswith("stats-")            a statistic
    league NOT IN ('COACHES','ASSISTANTS',..)  a coach
    r["predicate"] not in ("name",)            a name

Each was correct when it was written and wrong the day something was named
differently -- PFA's statistics arrived as `pfa-stats-1920s`, the coaching
subjects were given real leagues, and two stores wrote a name under a predicate
that is not spelt "name". The declaration is the record; RS-G8 re-derives all
three from the model and fails on any difference, in both directions.

WHAT DOES *NOT* BELONG HERE. `build_person_index.py` and `league_tokens.py` also
test `store.startswith("stats-")`, and they must keep it. They are not asking
what a claim MEANS; they are asking which ROSTER store a local id belongs to,
under StatsCrew's one-to-one `stats-nfl-1987` / `nfl-1987` pairing. PFA's
`pfa-stats-*` stores have no paired roster store, contribute 0 of 527,348
denotations, and would be broken, not fixed, by stripping a prefix. Two
different questions that happened to share a prefix; conflating them here would
be the same mistake in the other direction.
"""
import json, os, re
import paths

_PATH = os.path.join(paths.SERVICE_DECLARATIONS, "classification.json")
_D = None


def raw():
    global _D
    if _D is None: _D = json.load(open(_PATH))
    return _D


def statistic_stores():
    """The stores whose stint claims are per-season statistics."""
    return frozenset(raw()["statistic_stores"]["stores"])


def is_statistic(store):
    return store in statistic_stores()


# THE STAFF PREDICATES ARE THE ARCHIVE'S RULING, NOT THE SERVICE'S. They live in
# dataset/declarations/coaching-seasons.json, because src/build_person_index.py sorts
# the person index by the same list and the two must be one implementation. Before
# 2026-09-09 they were typed here and the index decided by league token instead; the
# result was 17,067 coaching seasons in the dict every consumer reads as playing.
_ARCHIVE_PATH = os.path.join(paths.DECLARATIONS, "coaching-seasons.json")
_A = None


def archive_raw():
    global _A
    if _A is None: _A = json.load(open(_ARCHIVE_PATH))
    return _A


def staff_predicates():
    """The predicates that make a man staff rather than a player on a club-season."""
    return frozenset(archive_raw()["staff_predicates"]["predicates"])


def staff_stores():
    return frozenset(archive_raw()["staff_predicates"]["stores_that_carry_them"])


def considered_and_not_staff():
    return frozenset(archive_raw()["staff_predicates"]["not_staff_though_it_appears_in_those_stores"])


def name_predicates():
    """Person-scoped predicates whose value is a man's name."""
    return frozenset(raw()["name_predicates"]["predicates"])


# ---------------------------------------------------------------- name form
def generational_suffixes():
    return {t.lower() for t in raw()["name_forms"]["generational_suffixes"]}


_PAREN = re.compile(r"\([^)]*\)")


def is_surname_first(name):
    """Is this string filed surname-first? A READING, applied at read time; the store
    is never rewritten and both forms stay searchable.

    Split on the FIRST comma; set aside parentheticals and generational suffixes in
    the tail; if anything remains, the head stood alone as a surname. A bare comma
    test gets 280 of the index's 2,472 comma names wrong -- `Robert D. Bean, Jr.` is
    forename-first and `ALFORD, Herbert Bruce, Sr. (Bruce)` is not.
    """
    if not isinstance(name, str) or "," not in name:
        return False
    tail = _PAREN.sub(" ", name.split(",", 1)[1])
    suff = generational_suffixes()
    rest = [t for t in (x.strip(" .") for x in re.split(r"[,\s]+", tail)) if t and t.lower() not in suff
            and (t.lower() + ".") not in suff]
    return bool(rest)


def is_bare_surname(name, others):
    """Is `name` a one-word name that another of `others` merely lengthens?

    Ruled by Ryan, 2026-09-09: a display name exists to be read, and a bare surname is
    what survives when nothing else does -- not a name to prefer over a fuller one for
    the same man. The archive knew Plunkett's forename and showed a surname, because
    9.3 prefers a DATED claim and the fuller name was undated.

    THE TEST IS DELIBERATELY NARROW and its reach was measured before it was written:
    2 people in the archive hold both shapes and 1 display name changes. It does not
    decide between two multi-word names, and the containment rule that would -- every
    word of A appearing in a longer B -- reaches 1,616 people, prefers middle names
    nobody uses, and fights the surname-first ruling. See the declaration."""
    if not isinstance(name, str): return False
    w = name.split()
    if len(w) != 1: return False
    bare = w[0].lower().strip(".,")
    for o in others:
        ow = (o or "").split()
        if len(ow) > 1 and ow[-1].lower().strip(".,") == bare: return True
    return False
