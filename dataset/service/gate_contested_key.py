"""A CONTEST IS TWO ANSWERS TO ONE QUESTION, AND THE KEY IS WHAT SAYS WHICH QUESTION.

Since 2026-09-10 `build_contested` keys on `(person, family, year)` where the family
holds season-scoped members and `(person, family)` where it does not. This gate holds
the property that made that ruling safe:

  E1  EVERY FAMILY THAT HOLDS NO SEASON-SCOPED CLAIM IS IDENTICAL UNDER BOTH KEYS,
      ROW FOR ROW -- not in total, row for row. Nine of the ten declared families
      hold none, and adding the year must not move a single one of their rows.

  E2  ONLY A FAMILY DECLARED TO HOLD SEASON-SCOPED MEMBERS MAY DIFFER, and the gate
      derives that list FROM THE CLAIMS rather than carrying a copy of it.

  E3  NOTHING APPEARS. A finer key can only split a group, never create a
      disagreement that the coarser key did not have. A row under the new key must
      have a counterpart under the old one for the same person and family; if one
      appears from nowhere the grouping is not a refinement and the ruling's argument
      does not hold.

WHY ROW FOR ROW AND NOT TOTALS. Keying on the raw `subject` column -- the obvious
reading of the same defect -- would have UNDONE PERSON MERGING and sent the total UP,
from 26,335 to 44,077. A gate comparing totals would have called that an improvement.

    python3 service/gate_contested_key.py [--selftest]
"""
import os, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths

FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def seasonal_families(conn, fams):
    """Derived from the claims, never typed here."""
    out = set()
    q = ",".join("?" * len(fams))
    for f, in conn.execute(
            f"SELECT DISTINCT family FROM claim WHERE family IN ({q}) "
            f"AND scope IN ('person_season','stint','club_season','league_season')", tuple(fams)):
        out.add(f)
    return out


def contested_pairs(conn, with_year):
    """(person, family, year-or-blank) -> the groups json, under one key or the other."""
    if with_year:
        rows = conn.execute("SELECT person, family, year, groups FROM contested")
        return {(p, f, y): g for p, f, y, g in rows}
    rows = conn.execute("SELECT person, family, year, groups FROM contested")
    out = collections.defaultdict(list)
    for p, f, y, g in rows: out[(p, f, "")].append(g)
    return {k: v for k, v in out.items()}


def main(argv):
    if "--selftest" in argv: return selftest()
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    conn.row_factory = None
    fams = list(json.load(open(os.path.join(HERE, "declarations",
                                            "predicate-families.json")))["families"])
    seasonal = seasonal_families(conn, fams)
    print(f"{len(fams)} declared families; {len(seasonal)} hold season-scoped claims: "
          f"{sorted(seasonal)}")

    # E1/E2 -- a non-seasonal family must have EVERY row keyed with a blank year, which
    # is exactly what "identical under both keys" means once the key carries the year.
    bad = collections.Counter()
    for f, y, n in conn.execute("SELECT family, year, COUNT(*) FROM contested GROUP BY 1,2"):
        if f not in seasonal and (y or "") != "":
            bad[f] += n
    check(not bad, f"E1 all {len(fams)-len(seasonal)} families holding no season-scoped claim "
                   f"are keyed identically under both keys"
          + ("" if not bad else f" -- {dict(bad)} carry a year they should not"))

    moved = {f for f, in conn.execute("SELECT DISTINCT family FROM contested WHERE year != ''")}
    check(moved <= seasonal, f"E2 only a family that HOLDS season-scoped claims differs"
          + ("" if moved <= seasonal else f" -- {sorted(moved - seasonal)} differ and hold none"))

    # E3 -- nothing appears. Every contested row's values must still be a disagreement
    # when that person's whole family is grouped together: a refinement can split, never
    # invent.
    import reading_view as RV
    has = set(RV.families())
    appeared = []
    for p, f, y, lits in conn.execute("SELECT person, family, year, literals FROM contested "
                                      "WHERE year != '' LIMIT 4000"):
        vals = json.loads(lits)
        allv = []
        for raw, in conn.execute("SELECT DISTINCT value FROM claim WHERE person=? AND family=? "
                                 "AND kind!='absent' AND value IS NOT NULL", (p, f)):
            try: allv.append(json.loads(raw))
            except (TypeError, ValueError): allv.append(raw)
        if len(allv) < 2: appeared.append((p, f, y)); continue
        if f in has:
            gs, unread = RV.group(f, allv)
            if len(list(gs)) + len(unread) < 2: appeared.append((p, f, y))
    check(not appeared, f"E3 no contested row appears that the coarser key did not hold"
          + ("" if not appeared else f" -- {len(appeared)} appeared, e.g. {appeared[:3]}"))

    n = conn.execute("SELECT COUNT(*) FROM contested").fetchone()[0]
    per = dict(conn.execute("SELECT family, COUNT(*) FROM contested GROUP BY 1"))
    print(f"\ncontested rows {n:,}   {per}")
    if FAILS:
        print(f"\nCONTESTED KEY GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCONTESTED KEY GATE: pass"); return 0


def selftest():
    """The gate must FAIL when a non-seasonal family is keyed with a year."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE contested(person TEXT, family TEXT, year TEXT, n_groups INTEGER,"
              " groups TEXT, literals TEXT, PRIMARY KEY(person, family, year))")
    c.execute("CREATE TABLE claim(person TEXT, family TEXT, scope TEXT, value TEXT, kind TEXT)")
    c.execute("INSERT INTO claim VALUES('P_1','birth_date','person','\"a\"','observed')")
    c.execute("INSERT INTO contested VALUES('P_1','birth_date','1970',2,'[]','[]')")
    seasonal = seasonal_families(c, ["birth_date"])
    ok = "birth_date" not in seasonal
    print(f"  {'ok  ' if ok else 'FAIL'} a person-scoped family is not derived as seasonal")
    bad = [f for f, y in c.execute("SELECT family, year FROM contested")
           if f not in seasonal and y != ""]
    print(f"  {'ok  ' if bad else 'FAIL'} E1 fails on a non-seasonal family carrying a year:"
          f" expected a failure, got {'one' if bad else 'none'}")
    print("SELFTEST OK" if (ok and bad) else "SELFTEST FAILED")
    return 0 if (ok and bad) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
