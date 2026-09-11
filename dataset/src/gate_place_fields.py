"""Gate: a date must not sit in a place field.

Ryan's ruling, 2026-09-11. PFA's player-page reader knew one date shape and filed every
other one whole into the place: `Born: 1890` became Frank Moran's BIRTHPLACE, so a birth
year sat where no birth-date check, family grouping or `contested` flag looks, and the
archive showed his StatsCrew 1905 as settled. 721 birth places and 45 death places.

  F1  NO VALUE IN A PLACE FIELD BEGINS WITH A DATE -- a bare year (`1890`), a year then a
      place (`1938 Baltimore, MD`), a month and year (`August, 1991 Winnipeg, MB`), or a year
      with its month printed empty (`, 1999`). Every place predicate of every source, read
      from the model. Refuses an empty population.

THE TEST IS DELIBERATELY NOT THE READER'S. ingest_pfa.split_date_place decides what a date
is; if its pattern missed a shape, a gate built on the same pattern would miss it too. This
one asks the looser question -- does the value open with a year, alone or after a month --
so a shape the reader does not know still fails here.

    python3 src/gate_place_fields.py [--selftest]
"""
import os, sys, re, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))

# The day is ANY short token starting with a digit: the first version wanted one or two
# digits and so passed six garbled full dates -- `September 256, 2001` -- sitting as places.
DATE_OPENING = re.compile(r"^\W*(?:[A-Z][a-z]+\.?,?\s+(?:\d[^\s,]{0,3},\s*)?)?[12]\d{3}\b")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def f1(rows):
    """rows: (predicate, source_id, value, n)."""
    tot = sum(n for *_, n in rows)
    if not tot:
        check(False, "F1 a date must not sit in a place field -- NO place value to check"); return
    bad = collections.Counter(); eg = collections.defaultdict(list)
    for pred, sid, v, n in rows:
        if isinstance(v, str) and DATE_OPENING.match(v):
            bad[(pred, sid)] += n
            if len(eg[(pred, sid)]) < 3: eg[(pred, sid)].append(v)
    check(not bad, f"F1 none of {tot:,} place values opens with a date"
          + ("" if not bad else f" -- {sum(bad.values()):,} do: "
             + "; ".join(f"{p} [{s}] {n:,} e.g. {eg[(p, s)]}" for (p, s), n in bad.most_common(6))))


def selftest():
    global FAILS
    ok = True
    for label, rows, want_fail in (
            ("a bare year as a birthplace (Frank Moran)", [("pfa.birth_place", "pfa", "1890", 1)], True),
            ("a year then a place", [("pfa.birth_place", "pfa", "1938 Baltimore, MD", 1)], True),
            ("a month, year and place", [("pfa.death_place", "pfa", "August, 1991 Winnipeg, MB", 1)], True),
            ("a year with its month printed empty", [("pfa.death_place", "pfa", ", 1999", 1)], True),
            ("a month year with no comma, a shape the reader might not know", [("x.birth_place", "x", "June 1984", 1)], True),
            ("a full date with a garbled day, then a place",
             [("pfa.birth_place", "pfa", "January 125, 1994 Dallas County, TX", 1)], True),
            ("ordinary places, a word, and a number that is not a year",
             [("pfa.birth_place", "pfa", "Canton, OH", 1), ("pfa.death_place", "pfa", "deceased", 1),
              ("hometown", "sc", "100 Mile House, BC", 1)], False),
            ("nothing to check", [], True)):
        FAILS = []; f1(rows); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    import paths
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT predicate, source_id, json_extract(value,'$'), count(*) FROM claim "
        "WHERE family IN ('birth_place','death_place','hometown') OR predicate LIKE '%place' "
        "OR predicate LIKE '%hometown' GROUP BY 1,2,3").fetchall()
    f1(rows)
    if FAILS:
        print(f"\nPLACE FIELD GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nPLACE FIELD GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
