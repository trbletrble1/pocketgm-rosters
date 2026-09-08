"""Club-seasons on the WRONG SIDE of a league boundary: the gaps no list can see.

Three times in two days a club turned out to have seasons the archive holds nothing for
that are not in the club table either, so they cannot appear as gaps in any list built
from it:

  Frankford Yellow Jackets 1922-23   independent, before joining the NFL in 1924
  Pottsville Maroons 1924 and 1929   Anthracite League before, and after the NFL run
  St. Louis Gunners 1931-33          independent, before buying the Reds' place in 1934

Every source the archive holds for those clubs is league-derived, so **all of them start
and stop at the same boundary** and the seasons either side are invisible to the lot at
once. This finds the rest, from evidence already on disk.

FOUR ROUTES, KEPT APART, BECAUSE THEY ARE NOT EQUALLY GOOD:
  A  a string names a held club in a year OUTSIDE its span -- the archive's own refusals
  B  pfa_only_gaps: the same PFA code and name either side of a hole
  C  attested_same_name_across_a_long_hole
  D  established from a document this session, not from the archive at all

WHAT THIS CANNOT DO. There is no founded/folded year on disk. The fandom survey carries
NO year fields (its own club-table entries say "the survey carries no years"), and the
wikipedia store is person-scoped -- no club predicates at all. A real founded/folded
sweep needs a fetch, and the network belongs to the preservation run.

  python3 src/measure_outside_span.py
"""
import os, sys, json, re, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
OUT = os.path.join(BASE, "build-reports", "outside-span.json")

# Route D: established from documents this session. Held apart because the evidence is
# not in the archive and cannot be re-derived from it.
FROM_DOCUMENTS = [
 {"club": "Frankford Yellow Jackets", "code": "FYJ", "held": "NFL 1924-1931",
  "outside": [1922, 1923], "status": "independent, pre-NFL",
  "evidence": "Yellowjackets_1922_roster.htm (27 men, head coach Heinie Miller) and "
              "_1923_roster.htm (20 men, head coach Lou Little) -- ROSTER PAGES. Both "
              "INGESTED 2026-09-08 as leads: 47 men held as leads on a club-season the "
              "club table does not carry, waiting for a ruling that creates it.",
  "source_kind": "hobbyist site working from Philadelphia newspaper microfilm (not Neft)"},
 {"club": "Pottsville Maroons", "code": "POT", "held": "NFL 1925-1928",
  "outside": [1924], "status": "Anthracite League before",
  "evidence": "Maroons_1924_stats.htm is a season SCHEDULE -- games, opponents, dates "
              "and scores, NOT men. It does not take the club-season from nothing to a "
              "team.",
  "source_kind": "as above",
  "_1929_was_wrong_twice": "Maroons_1929_roster.htm was reported here as a Pottsville "
      "club-season the archive holds nothing for. It is not. The page's OWN TITLE is "
      "`Boston Bulldogs 1929 NFL Team Roster` -- the franchise moved for 1929 -- and the "
      "archive holds NFL|1929|BO2 with 22 men, all 22 of whom the page names. It is "
      "corroboration, not a gap. The error was reading the FILENAME and not the page, "
      "and it survived two reports."},
 {"club": "St. Louis Gunners", "code": "SLG", "held": "NFL 1934 only",
  "outside": [1931, 1932, 1933], "status": "independent, before buying the 1934 "
              "Cincinnati Reds' place",
  "evidence": "the fandom club page names four head coaches -- Conzelman 1931, Baker "
              "1932, Henry 1933, Walsh 1934. Only 1934 is held. NOT INGESTED: the fandom "
              "survey was scoped strings-only and read no staff.",
  "source_kind": "wiki, unranked and Neft-seeded -- a LEAD, not a source"},
]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    T = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    byname = collections.defaultdict(list)
    for c in T["clubs"]:
        for n in c["names"]: byname[norm(n["name"])].append(c)
        for s in c["strings"]:
            if s["kind"] in ("printed_name", "alias"): byname[norm(s["string"])].append(c)

    U = T["unresolved"]
    seen, routeA = set(), []
    for r in U["strings"]:
        if r.get("first") is None: continue
        for yr in range(r["first"], (r.get("last") or r["first"]) + 1):
            for c in byname.get(norm(r["string"]), []):
                if c["first"] <= yr <= c["last"]: continue
                k = (c["id"], yr, r["string"])
                if k in seen: continue
                seen.add(k)
                side = "before" if yr < c["first"] else "after"
                routeA.append({"club": c["id"],
                               "club_name": c["names"][0]["name"],
                               "held": [c["first"], c["last"]],
                               "year_attested": yr, "side": side,
                               "gap_years": (c["first"] - yr if side == "before"
                                             else yr - c["last"]),
                               "string": r["string"], "source": r.get("source"),
                               "why_it_refused": r.get("why")})
    routeA.sort(key=lambda x: (-x["gap_years"], x["club"]))

    res = {"_note": "MEASUREMENT ONLY. No club-season is created. Four routes kept apart "
                    "because they are not equally good evidence.",
           "_cannot_do": "No founded/folded year exists on disk. The fandom survey carries "
                         "no year fields at all and the wikipedia store is person-scoped. "
                         "A real founded/folded sweep needs a fetch.",
           "A_string_attests_a_year_outside_the_span": routeA,
           "B_pfa_only_gaps": U.get("pfa_only_gaps", []),
           "C_same_name_across_a_long_hole": U.get("attested_same_name_across_a_long_hole", []),
           "D_established_from_a_document": FROM_DOCUMENTS,
           "counts": {"A": len(routeA), "A_clubs": len({x["club"] for x in routeA}),
                      "B": len(U.get("pfa_only_gaps", [])),
                      "C": len(U.get("attested_same_name_across_a_long_hole", [])),
                      "D": len(FROM_DOCUMENTS),
                      "D_club_seasons": sum(len(x["outside"]) for x in FROM_DOCUMENTS)}}
    json.dump(res, open(OUT, "w"), indent=1)
    c = res["counts"]
    print(f"A  a string names a held club outside its span : {c['A']} attestations, {c['A_clubs']} clubs")
    for x in routeA[:12]:
        print(f"     {x['club_name']:28s} held {x['held'][0]}-{x['held'][1]}  attested {x['year_attested']} "
              f"({x['side']}, {x['gap_years']}y)  <- {x['source']}")
    print(f"B  pfa_only_gaps                               : {c['B']}")
    print(f"C  same name across a long hole                : {c['C']}")
    print(f"D  established from a document this session    : {c['D']} clubs, "
          f"{c['D_club_seasons']} club-seasons")
    print("\n->", OUT)
    return res


if __name__ == "__main__":
    main()
