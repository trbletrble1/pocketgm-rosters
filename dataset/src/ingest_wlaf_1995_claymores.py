"""The 1995 Scottish Claymores roster, from Pro Football Archives.

WHY THIS ONE CLUB-SEASON. WLAF 1995 is the same league the archive already holds for
1991 and 1992 -- Barcelona Dragons and Frankfurt Galaxy carry WLAF rosters for those
years and COACHES claims from 1995 onwards, so the archive already follows the league
across its hiatus. Ryan ruled on 2026-09-08 that a league in scope is in scope for
its own seasons. The club table's span was extended to 1995 through SPAN_EXTENSIONS,
which required corroboration from a source other than PFA and got it from StatsCrew.

EVERY VALUE IS HELD AS PRINTED. Name, position, height, weight, age and college come
off the roster table verbatim; the declared readings do the comparing, never the
ingest.

LOCAL IDS, NOT PEOPLE. Each man gets a store-local id. Joining him to a person the
archive already holds is the identity question, and answering it on a name would be
the surname trap with a longer runway. The store says who it saw; identity.json says
who they are.

  python3 src/ingest_wlaf_1995_claymores.py [--write]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import measure_pfa_team_seasons as M
import clubs as ac

PAGE = "1995wlafsco.html"
OUT = os.path.join(BASE, "build", "pfa-wlaf-1995.json")
CLUB_ID = "club-scottish-claymores-1996"
# THE CODE COMES FROM THE CLUB TABLE, NEVER FROM ME. An invented code (`WLAFSCO`, by
# analogy with StatsCrew's `WLAFBAR`) is a string nothing resolves: the claims landed
# with club_id None and the club-season stayed empty while every count said it had
# worked.
# the roster columns that carry a fact, and the predicate each becomes
AS_PRINTED = {"pos": "position", "ht": "pfa.height", "wt": "pfa.weight",
              "college": "pfa.college", "no": "jersey", "gp": "games_played",
              "gs": "games_started", "age": "pfa.age"}


def main():
    write = "--write" in sys.argv
    pb = M.cache_files()
    if PAGE not in pb:
        sys.exit(f"{PAGE} is not in any PFA cache")
    got = M.parse(pb[PAGE])
    if not got:
        sys.exit(f"{PAGE} does not parse as a team-season page")
    year, club, league, rows, _ = got
    if (year, league) != (1995, "WLAF"):
        sys.exit(f"{PAGE} is {year} {league}, not 1995 WLAF -- refusing rather than "
                 "trusting the filename")

    C = ac.Clubs()
    code = C.code_for(CLUB_ID, year)
    if not code or not C.by_code_year(code, year):
        sys.exit(f"the club table gives {CLUB_ID} no code that resolves in {year} "
                 f"(got {code!r}). Refusing rather than inventing one.")
    print(f"club code from the table: {code}")
    claims, persons, srs = [], [], {}
    n = collections.Counter()
    sr = f"pro-football-archives#{PAGE}"
    srs[sr] = {"source_id": "pro-football-archives", "locator": PAGE}
    cid = 0
    for r in rows:
        name = (r.get("player") or "").strip()
        if not name:
            n["row with no name, skipped"] += 1
            continue
        pid = "wlaf1995sco_%03d" % (len(persons) + 1)
        persons.append({"id": pid, "name_as_printed": name})
        rec = f"{sr}#{name}"
        srs[rec] = {"source_id": "pro-football-archives",
                    "locator": f"{PAGE}#{name}"}

        def add(pred, val, subject):
            nonlocal cid
            cid += 1
            claims.append({"id": "c_%05d" % cid, "predicate": pred, "value": val,
                           "subject": subject, "kind": "observed",
                           "source_id": "pro-football-archives",
                           "source_record": rec, "stated_by": "Pro Football Archives",
                           "attribution": [], "observed_at": year, "note": None})
            n[pred] += 1

        add("name", name, ["person", pid])
        for col, pred in AS_PRINTED.items():
            v = (r.get(col) or "").strip()
            if not v or v.lower() == "none":
                # `none` in the college cell is PFA asserting the man attended no
                # college. It is recorded as an ABSENCE, not dropped and not stored as
                # the string "none", which would read as a school called None.
                if col == "college" and v.lower() == "none":
                    cid += 1
                    claims.append({"id": "c_%05d" % cid, "predicate": "pfa.college",
                                   "value": None, "subject": ["person", pid],
                                   "kind": "absent",
                                   "source_id": "pro-football-archives",
                                   "source_record": rec,
                                   "stated_by": "Pro Football Archives",
                                   "attribution": [], "observed_at": year,
                                   "note": "the roster table prints `none` for this man"})
                    n["college absent"] += 1
                continue
            add(pred, v, ["person", pid])
        add("roster_membership.on_active_roster", f"{league}|{year}|{code}",
            ["stint", pid, code, f"{league}-{year}"])

    out = {"source": {"source_id": "pro-football-archives",
                      "acquisition": "fetched 2026-09-08 from profootballarchives.com, "
                                     "one request at a time",
                      "stated_by": "Pro Football Archives"},
           "_what": f"the {year} {club} ({league}) roster table, {len(persons)} men",
           "_the_club_season_is_new": "club-scottish-claymores-1996 gained 1995 through "
                                      "SPAN_EXTENSIONS, corroborated by StatsCrew",
           "_identity_is_not_decided_here": "every man carries a store-local id. Joining "
                                            "him to a person the archive holds is the "
                                            "identity question and is not answered on a "
                                            "name.",
           "source_records": srs, "persons": persons, "claims": claims,
           "counts": dict(n) | {"men": len(persons), "claims": len(claims)}}
    print(f"{year} {club} ({league}): {len(persons)} men, {len(claims)} claims")
    for k, v in sorted(n.items(), key=lambda kv: -kv[1]):
        print(f"   {k:38s} {v:>4}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        print("wrote", OUT)
    else:
        print("(dry run; --write to store)")


if __name__ == "__main__":
    main()
