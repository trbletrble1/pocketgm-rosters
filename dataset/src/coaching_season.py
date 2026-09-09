"""ONE reading of a coaching season's value in the person index.

A COACHING SEASON IS HELD IN ONE SHAPE (Ryan, 2026-09-09): the value is
`{"stats": {...}, "stint": {predicate: value}}` -- the same shape `seasons` uses,
because the ruling is that a claim's place follows its PREDICATE.

Before that the two producers disagreed. `build_person_index.py` wrote nothing to
`coaching_seasons` at all and put staff claims in `seasons`; `apply_promotions.py`
wrote a LIST of raw PFA rows. So `build_clubs.py` and `gate_clubs.py` were written
against the list and would have read the dict as its keys.

This lives in its own module rather than in `index_io.py` because gate_clubs K8
asserts that `build_clubs.py` and `clubs.py` NEVER import the index writer -- they
must not be able to write the index -- and reading a shape is not writing one.
"""


def rows(sd):
    """The PFA source rows on ONE coaching-season entry, whoever wrote it.

    The old list shape is accepted too, so a half-rebuilt tree reads rather than
    crashes, and that is said here rather than in three copies."""
    if isinstance(sd, list): return [r for r in sd if isinstance(r, dict)]     # the pre-2026-09-09 shape
    if not isinstance(sd, dict): return []
    return [v for v in (sd.get("stint") or {}).values() if isinstance(v, dict)]


def printed_club(row):
    """The club exactly as PFA printed it on a coaching row -- "1928 Dayton Triangles (NFL)".

    TWO PRODUCERS, TWO FIELD NAMES, ONE FACT. ingest_pfa_coaches writes it as
    `club_as_printed`; apply_promotions carries PFA's own `printed_long`. build_clubs
    read `printed_long` alone, so the moment build_person_index started routing PFA's
    coaching seasons into `coaching_seasons` (2026-09-09) every one of them arrived
    with no printed name -- and build_clubs minted 46 clubs called `club--2000`,
    `club--2001` and so on from the empty string, taking `PFA:AMS` off the Amsterdam
    Admirals and stranding 3,833 statistics claims with no club. A derived id moving
    because the data moved, for the second time in three days.

    Read here, once, rather than in each caller."""
    if not isinstance(row, dict): return ""
    return str(row.get("printed_long") or row.get("club_as_printed") or "")
