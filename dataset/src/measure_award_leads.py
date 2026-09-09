"""Why 2,113 award rows did not become claims.

THREE DIFFERENT ANSWERS, and they need different work:
  matched more than one   the archive holds that exact name twice; a join would be a
                          coin toss
  failed on name form     nobody holds the printed name, but exactly one person shares
                          the surname AND the forename initial -- `Johnny Blood` for
                          `Johnny McNally`. A looser matcher would have joined it; the
                          ingest refused because a looser matcher is the surname trap
  matched nobody          no plausible person at all

The last group is the one that means something. An all-league selection is a man good
enough that somebody named him the best in the league at his position. If the archive
does not hold him, either the roster he belongs to was never read (COVERAGE) or it was
read and he is in it under a form nothing matched (a JOIN defect). Those are different
jobs, and the club-season tells them apart.

  python3 src/measure_award_leads.py
"""
import os, re, sys, json, sqlite3, collections

_SP = {}
def STAFF_PREDICATE_SQL():
    # STAFF IS A PREDICATE, NOT A LEAGUE. `league not in ('COACHES',...)` let 41,662
    # of 54,908 staff claims through as players once the coaching subjects carried real
    # leagues, so this pool held 30,364 STAFF-ONLY (club, year, person) pairs -- coaches
    # offered as candidates for a player's award, statistic line or roster gap.
    # declarations/coaching-seasons.json is the list.
    if not _SP:
        import os as _o, json as _j
        _d = _j.load(open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "..",
                                       "declarations", "coaching-seasons.json")))
        _p = sorted(_d["staff_predicates"]["predicates"])
        _SP["sql"] = "predicate not in (" + ",".join("'" + x + "'" for x in _p) + ")"
    return _SP["sql"]


HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import clubs as ac
from readings import person_name as _person_name

STORE = os.path.join(BASE, "build", "pfa-awards.json")
OUT = os.path.join(BASE, "build-reports", "award-leads.json")


def norm(s):
    """THE one name reading -- readings.person_name. This file used to carry
    its own copy, and the copies disagreed on apostrophes, initials, hyphens
    and suffixes across about 1,200 names."""
    return _person_name(s)


def main():
    d = json.load(open(STORE))
    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()

    exact = collections.defaultdict(set)
    by_sur_ini = collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        k = norm(nm)
        if not k:
            continue
        exact[k].add(p)
        w = k.split()
        if len(w) >= 2:
            by_sur_ini[(w[-1], w[0][0])].add(p)

    # who the archive holds on each club-season, for the coverage test AND for the
    # join test: `Johnny Blood` is held as `Johnny McNally`, which no surname rule can
    # find. A man on the very club-season sharing a forename or a surname is a
    # CANDIDATE -- reported, never joined.
    roster = collections.defaultdict(set)
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim where scope='stint' "
            "and club_id is not null and person is not null and " + STAFF_PREDICATE_SQL() +
            " group by club_id, year, person"):
        roster[(cid, y)].add(p)
    names_of = collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        if norm(nm): names_of[p].add(norm(nm))
    held = {k: len(v) for k, v in roster.items()}

    buckets = collections.Counter()
    nobody = []
    for L in d["leads"]:
        name = L["name_as_printed"]; v = L["value"]
        k = norm(name)
        hits = exact.get(k, set())
        if len(hits) > 1:
            buckets["matched more than one"] += 1
            continue
        w = k.split()
        variant = by_sur_ini.get((w[-1], w[0][0]), set()) if len(w) >= 2 else set()
        if len(variant) == 1:
            buckets["failed on name form"] += 1
            continue
        if len(variant) > 1:
            buckets["failed on name form, and ambiguous even then"] += 1
            continue
        buckets["matched nobody"] += 1
        year = v.get("year"); club = v.get("club_as_printed")
        lg = v.get("league")
        cid = None
        if club and year:
            r = C.resolve(club, year, lg if lg and lg.isalpha() else None, source="pfa-awards")
            cid = r[0] if r else None
        cands = []
        if cid and year:
            want = set(k.split())
            for p in roster.get((cid, year), ()):
                for nm in names_of.get(p, ()):
                    if set(nm.split()) & want:
                        cands.append(nm); break
        nobody.append({"name": name, "year": year, "league": lg, "club": club,
                       "predicate": L["predicate_it_would_be"],
                       "club_id": cid,
                       "men_the_archive_holds_on_that_club_season":
                           (held.get((cid, year), 0) if cid else None),
                       "candidates_on_that_club_season": sorted(cands)[:3]})

    print(f"{len(d['leads']):,} leads\n")
    for k, n in buckets.most_common():
        print(f"   {n:>6,}  {k}")

    with_cs = [x for x in nobody if x["club_id"]]
    empty = [x for x in with_cs if not x["men_the_archive_holds_on_that_club_season"]]
    peopled = [x for x in with_cs if x["men_the_archive_holds_on_that_club_season"]]
    unres = [x for x in nobody if not x["club_id"]]
    print(f"\nOF THE {len(nobody):,} THAT MATCHED NOBODY -- coverage gap, or join defect?")
    print(f"   {len(empty):>6,}  the archive holds NOBODY on that club-season -- COVERAGE")
    withcand = [x for x in peopled if x["candidates_on_that_club_season"]]
    print(f"   {len(peopled):>6,}  the archive holds men on it and not him -- a JOIN "
          "defect or a thin roster")
    print(f"   {len(withcand):>6,}     ...of those, a man on that very club-season shares "
          "a name part -- a CANDIDATE, reported not joined")
    print(f"   {len(unres):>6,}  the club table cannot place the club at all -- COVERAGE, "
          "one level up")

    print(f"\nTWENTY THAT MATCHED NOBODY")
    print(f"   {'year':>5} {'league':7} {'name':24} {'club as printed':28} held there")
    for x in sorted(nobody, key=lambda z: (z["year"] or 0))[:20]:
        h = x["men_the_archive_holds_on_that_club_season"]
        print(f"   {x['year']:>5} {str(x['league'])[:7]:7} {x['name'][:24]:24} "
              f"{str(x['club'])[:28]:28} "
              + ("club not in the table" if x["club_id"] is None else f"{h} men"))
    by_dec = collections.Counter((x["year"] or 0) // 10 * 10 for x in nobody)
    print("\n   matched nobody, by decade:")
    for k in sorted(by_dec):
        print(f"      {k}s {by_dec[k]:>5,}")
    by_lg = collections.Counter(str(x["league"]) for x in nobody)
    print("   by league:", ", ".join(f"{k} {v:,}" for k, v in by_lg.most_common(8)))

    json.dump({"buckets": dict(buckets), "matched_nobody": nobody}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
