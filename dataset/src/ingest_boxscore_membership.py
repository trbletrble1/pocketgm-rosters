"""Stage 1 of roster-membership-as-a-claim: the PFA boxscore lineups.

RYAN'S RULING. Roster membership becomes a claim held from every source, with the
DEFINITION RECORDED ON THE CLAIM. The five sources on disk answer different
questions -- on a season roster, on any roster at any point, ever signed, started
a game, in the guide at press time -- and the archive has been showing only
StatsCrew's answer. The definition belongs on the claim, not in the resolution.

WHY THE BOXSCORES FIRST. Strictest definition (started a game), 4% disagreement
with the spine, and genuinely independent -- a lineup is who took the field, not
another reading of the same roster list. Proven: it built Card-Pitt, the 1926 AFL
and the 1934 Cincinnati Reds when nothing else could. If the shape is wrong we
find out on the cheapest source.

THE SHAPE, and why each part is where it is:

  predicate  roster_membership.started_a_game
             The definition rides in the PREDICATE. build_person_index folds
             person-scoped claims into person[predicate] as strings, so a
             definition kept only in the value would be flattened out of the
             derived view. Stage 3's nflverse claims will be
             roster_membership.on_a_roster_at_any_point; two men, two predicates,
             never one predicate with two meanings.
  value      "LEAGUE|YEAR|CODE" -- the season-key shape, so it is directly
             comparable with the spine's keys without a join.
  subject    ["person", pid] -- NOT a stint. A stint subject is what the builder
             turns into a season key, and that would merge this into StatsCrew's
             membership, which is exactly what this stage must not do.
  games      every game the man started for that club, with its date, so the
             evidence is retrievable from the claim and never has to be re-derived.

ONE CLAIM PER SOURCE PER MAN PER CLUB-SEASON. A man who started eight games holds
one membership claim with eight games on it, not eight claims. A man StatsCrew
also places on that club holds two claims with two predicates. That is the point.

THE LIMITATION, STATED ON EVERY CLAIM. A boxscore lineup is ~11 starters a side.
A squad man who never started is not here, and his absence from this source is
not evidence he was absent from the club.

CLUB STRINGS RESOLVE THROUGH build/clubs.json, never a derived map. A string the
table cannot place is counted and reported, never skipped.

  python3 src/ingest_boxscore_membership.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
from clubs import Clubs

SRC_ID = "pfa-boxscores"
PRED = "roster_membership.started_a_game"
OUT = os.path.join(BASE, "build", "pfa-boxscore-membership.json")


class MembershipError(Exception):
    pass


def main(write=True):
    B = json.load(open(os.path.join(BASE, "build", "pfa-boxscores.json")))
    C = Clubs()
    games = {tuple(c["subject"]): c["value"] for c in B["claims"] if c["predicate"] == "pfa.game"}

    # (pid, league, year, club_id) -> evidence
    per = {}
    n = collections.Counter()
    for c in B["claims"]:
        if c["predicate"] != "pfa.game_lineup":
            continue
        v = c["value"]; g = tuple(v["game"]); league, year = g[1], g[2]
        n["lineup_rows"] += 1
        s = v.get("club_as_printed")
        if not s:
            n["rows_with_no_club"] += 1          # the 19 stray-heading rows; already reported
            continue
        r = C.resolve(s, year, league, source="boxscore")
        if not r:
            n["rows_unresolved_club"] += 1
            continue
        cid, how = r
        code = C.code_for(cid, year)
        if not code:
            # the table knows the club but says it fielded no team that year
            n["rows_club_without_season"] += 1
            C._refuse(s, year, league, "boxscore", "club known, no code-segment covers that year")
            continue
        key = (c["subject"][1], league, year, cid)
        e = per.setdefault(key, {"code": code, "club_as_printed": s, "resolved_as": how,
                                 "games": [], "positions": collections.Counter()})
        e["games"].append({"game": list(g), "pfa_game_id": games.get(g, {}).get("pfa_game_id"),
                           "date": games.get(g, {}).get("date"),
                           "position_as_printed": v.get("position_as_printed"),
                           "jersey": v.get("jersey")})
        if v.get("position_as_printed"):
            e["positions"][v["position_as_printed"]] += 1

    claims = []
    for (pid, league, year, cid), e in sorted(per.items()):
        claims.append({
            "source_record": f"{SRC_ID}#lineups/{league}-{year}-{e['code']}",
            "source_id": SRC_ID, "stated_by": "Pro Football Archives",
            "attribution": ["Pro Football Archives (profootballarchives.com), game boxscores"],
            "subject": ["person", pid],
            "predicate": PRED,
            "value": f"{league}|{year}|{e['code']}",
            "kind": "observed", "observed_at": "fetched-2026-09",
            "definition": "started a game: the man is named in this club's starting lineup "
                          "in at least one boxscore that season",
            "definition_limitation": "a lineup is ~11 starters a side. A squad man who never "
                                     "started is NOT here, and his absence from this source is "
                                     "not evidence he was absent from the club",
            "club_id": cid, "club_code": e["code"], "club_as_printed": e["club_as_printed"],
            "club_resolved_as": e["resolved_as"],
            "league": league, "year": year,
            "appearances": len(e["games"]),
            "games": sorted(e["games"], key=lambda x: x["game"]),
            "positions_as_printed": dict(e["positions"]),
        })
    # ONE CLAIM PER MAN PER CLUB-SEASON. Assert it; do not trust the grouping.
    seen = collections.Counter((c["subject"][1], c["value"]) for c in claims)
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        raise MembershipError(f"{len(dup)} (man, club-season) pairs hold more than one claim: {dup[:3]}")

    refusals = C.census()
    club_seasons = collections.Counter(c["value"] for c in claims)
    out = {
        "source": {"source_id": SRC_ID, "name": "Pro Football Archives game boxscores, lineups",
                   "stated_by": "Pro Football Archives", "acquisition": "fetched",
                   "definition": "started a game", "predicate": PRED,
                   "_stage": "1 of 4 -- roster membership as a claim, per source, definition on the claim",
                   "_not_collapsed": "these claims sit BESIDE the StatsCrew spine. Subjects are "
                                     "persons, not stints, so build_person_index cannot fold them "
                                     "into `seasons`. A man both sources place on a club holds two "
                                     "claims under two predicates."},
        "claims": claims,
        "unresolved_club_strings": [{"league": lg, "year": y, "string": s, "why": why, "rows": n_}
                                    for lg, y, s, why, n_, _ in refusals],
        "counts": {**dict(n), "membership_claims": len(claims),
                   "club_seasons_attested": len(club_seasons),
                   "people": len({c["subject"][1] for c in claims}),
                   "unresolved_club_strings": len(refusals),
                   "unresolved_rows": sum(r[4] for r in refusals)},
    }
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, OUT, indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--dry" not in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:28s} {v:,}")
    if o["unresolved_club_strings"]:
        print("  UNRESOLVED club strings (counted, not skipped):")
        for u in o["unresolved_club_strings"]:
            print(f"     {u['rows']:6,}  {u['league']}|{u['year']}|{u['string']}   [{u['why']}]")
