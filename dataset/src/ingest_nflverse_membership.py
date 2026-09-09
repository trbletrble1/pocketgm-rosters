"""Stage 3 of roster-membership-as-a-claim: the nflverse per-season rosters.

THE DEFINITION, and it is the whole reason this is a separate claim. nflverse
counts ANYONE WHO WAS ON A ROSTER AT ANY POINT IN THE SEASON. StatsCrew counts men
on the season roster. Different questions, different answers -- 10,854 person-club-
seasons nflverse attests that the spine lacks, 7,723 the spine has that nflverse
lacks, 115,747 agreed. The Raiders' 2020 club-season already came from nflverse
for exactly this reason, and carried the difference on every claim; this is the
same fact generalised to 1920-2026.

IDENTITY: THE ID BRIDGE, WHICH STAGES 1 AND 2 DID NOT HAVE.
nflverse's rows carry gsis_id, pfr_id and esb_id. The archive holds none of them
on a person -- except build/nflverse-draft.json, whose 11,412 claims carry BOTH a
gsis_id and an archive person id. That is a structural handle: a man resolved
through it is resolved on an identifier both sides printed, not on his name.
89,529 of 142,631 roster rows carry a gsis_id and 56,606 resolve through the
bridge.

THE NAME ROUTE IS INHERITED, NOT REDONE. build/nflverse-rosters.json already
matched 130,661 memberships on name+birth_date, with its own refusals, leads and
disagreement records. Re-deriving that here would either reproduce it or diverge
from it, and a second opinion on identity that nobody asked for is worse than
none. Those decisions are taken as given and TAGGED `name+birth_date`; the bridge
only ADDS, and every claim says which route resolved it.

WHERE THE TWO ROUTES DISAGREE ABOUT A MAN'S NAME, that is recorded and NOT
resolved: the bridge is an id match, the archive's name is the archive's, and a
name that does not look like the roster's is evidence about the bridge worth
keeping, not a reason to drop the row.

  python3 src/ingest_nflverse_membership.py [--dry]
"""
import os, re, csv, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
from clubs import Clubs

SRC_ID = "nflverse-rosters"
PRED = "roster_membership.on_a_roster_at_any_point"
DEFN = ("on a roster at any point in the season: nflverse's per-season roster file "
        "lists the man against this club for this season")
LIMIT = ("nflverse counts anyone who appeared on a roster at ANY point in the year, "
         "including men signed and released without playing. It is a WIDER definition "
         "than StatsCrew's season roster -- the 2020 Raiders are 86 men here against a "
         "StatsCrew peer median of 70 -- so a man here is not necessarily a man who "
         "played, and the two must not be summed")
ROSTERS = os.path.expanduser("~/Documents/pgm3-sources/nflverse/rosters/roster_*.csv")
OUT = os.path.join(BASE, "build", "nflverse-membership.json")


class NvError(Exception):
    pass


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def main(write=True):
    C = Clubs()
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    idx.pop("_clubs", None)

    # the bridge: gsis_id -> archive person, from the draft store's own claims
    D = json.load(open(os.path.join(BASE, "build", "nflverse-draft.json")))
    g2p = {c["gsis_id"]: c["subject"][1] for c in D["claims"] if c.get("gsis_id")}
    p2p = {c["pfr_id"]: c["subject"][1] for c in D["claims"] if c.get("pfr_id")}
    # the gsis the bridge believes goes with each pfr_id, so a pfr match can be
    # CONTRADICTED by the row's own gsis
    p2g = {c["pfr_id"]: c.get("gsis_id") for c in D["claims"] if c.get("pfr_id")}

    # the inherited name+birth_date decisions, as (person, season, team)
    R = json.load(open(os.path.join(BASE, "build", "nflverse-rosters.json")))
    byname = collections.defaultdict(set)          # (season, team) -> {person}
    for c in R["claims"]:
        if c["predicate"] == "nflverse.roster_membership":
            byname[(c["season"], c["team"])].add(c["subject"][1])

    n = collections.Counter()
    per = {}                                        # (person, season, cid) -> evidence
    namecheck = []
    for f in sorted(glob.glob(ROSTERS)):
        for r in csv.DictReader(open(f)):
            n["rows"] += 1
            season = int(r["season"]); team = (r.get("team") or "").strip()
            gid = (r.get("gsis_id") or "").strip(); pid_x = (r.get("pfr_id") or "").strip()
            full = (r.get("full_name") or "").strip()
            person, route = None, None
            if gid and gid in g2p:
                person, route = g2p[gid], "gsis_id"
            elif pid_x and pid_x in p2p and not (gid and p2g.get(pid_x) and p2g[pid_x] != gid):
                person, route = p2p[pid_x], "pfr_id"
            elif pid_x and pid_x in p2p:
                # THE ROW'S OWN gsis CONTRADICTS THE BRIDGE ENTRY'S. Every one of the
                # seven claims this route produced was the same bad match: nflverse
                # prints pfr_id 'JohnDe22' on Damaris Johnson's rows, the bridge has
                # that id against Dennis Johnson (a 2002 third-round pick, gsis
                # 00-0021086) while the rows carry gsis 00-0029435, and the archive
                # already holds Damaris separately as P_032907 on those very
                # club-seasons. A pfr id that disagrees with the row's gsis is not
                # evidence of identity; refused and counted, never guessed between.
                n["pfr_id_contradicted_by_row_gsis"] += 1
            if person is None:
                # inherited name+birth_date. The store matched per ROW and recorded only
                # (person, season, team), so a row can only be re-credited by name --
                # and the archive's name is often not the roster's ('Peli Anau'). An
                # exact-name re-check dropped 7,159 of the store's own decisions, which
                # is the second opinion on identity this ingest exists NOT to give. So
                # the row is credited to the club-season's inherited set when its name
                # matches, and every inherited tuple is added below whether or not any
                # row matched it.
                for cand in byname.get((season, team), ()):
                    if norm((idx.get(cand) or {}).get("name")) == norm(full):
                        person, route = cand, "name+birth_date"; break
            if person is None:
                n["rows_no_row_level_identity"] += 1; continue
            if person not in idx:
                n["rows_person_not_in_index"] += 1; continue
            # the bridge is an ID match; if the archive's name does not look like the
            # roster's, KEEP the row and record the mismatch
            if route in ("gsis_id", "pfr_id"):
                an = norm((idx.get(person) or {}).get("name"))
                if an and norm(full) and an != norm(full):
                    n["id_bridge_name_mismatch"] += 1
                    if len(namecheck) < 400:
                        namecheck.append({"person": person, "archive_name": idx[person].get("name"),
                                          "nflverse_name": full, "gsis_id": gid,
                                          "season": season, "team": team})
            res = C.resolve(team, season, None, source="nflverse")
            if not res:
                n["rows_unresolved_club"] += 1; continue
            cid, how = res
            code = C.code_for(cid, season)
            if not code:
                C._refuse(team, season, "?", "nflverse", "club known, no code-segment covers that year")
                n["rows_club_without_season"] += 1; continue
            k = (person, season, cid)
            e = per.setdefault(k, {"code": code, "team": team, "resolved_as": how,
                                   "routes": set(), "rows": []})
            e["routes"].add(route)
            e["rows"].append({"season": season, "nflverse_team": team,
                              "status": (r.get("status") or "").strip() or None,
                              "jersey_number": (r.get("jersey_number") or "").strip() or None,
                              "gsis_id": gid or None, "pfr_id": pid_x or None,
                              "esb_id": (r.get("esb_id") or "").strip() or None,
                              "name_as_printed": full,
                              "source_record": f"{SRC_ID}#{os.path.basename(f)}"})

    # EVERY INHERITED TUPLE LANDS, row-level evidence or not. The store's identity
    # decisions are taken as given; this ingest adds the id bridge, it does not
    # re-adjudicate who the man is.
    for (season, team), people in byname.items():
        res = C.resolve(team, season, None, source="nflverse")
        if not res:
            n["inherited_unresolved_club"] += len(people); continue
        cid, how = res
        code = C.code_for(cid, season)
        if not code:
            n["inherited_club_without_season"] += len(people); continue
        for person in people:
            if person not in idx:
                n["inherited_person_not_in_index"] += 1; continue
            k = (person, season, cid)
            if k in per:
                continue                                  # a row already carried it
            n["inherited_without_row_evidence"] += 1
            per[k] = {"code": code, "team": team, "resolved_as": how,
                      "routes": {"name+birth_date"},
                      "rows": [{"season": season, "nflverse_team": team, "status": None,
                                "jersey_number": None, "gsis_id": None, "pfr_id": None,
                                "esb_id": None, "name_as_printed": None,
                                "source_record": f"{SRC_ID}#roster_{season}.csv",
                                "_evidence": "inherited from build/nflverse-rosters.json; the "
                                             "row is in that store, not re-matched here"}]}

    claims = []
    for (person, season, cid), e in sorted(per.items(), key=lambda x: (x[0][1], x[0][2], x[0][0])):
        league = C.league_for(cid, season) or "NFL"
        route = ("gsis_id" if "gsis_id" in e["routes"] else
                 "pfr_id" if "pfr_id" in e["routes"] else "name+birth_date")
        claims.append({
            "source_record": e["rows"][0]["source_record"], "source_id": SRC_ID,
            "stated_by": "nflverse", "attribution": ["nflverse historical rosters, roster_{year}.csv"],
            "subject": ["person", person], "predicate": PRED,
            "value": f"{league}|{season}|{e['code']}",
            "kind": "observed", "observed_at": f"roster-{season}",
            "definition": DEFN, "definition_limitation": LIMIT,
            "identity_route": route,
            "_identity_note": ("resolved on gsis_id, an identifier both nflverse and the "
                               "archive's draft store print -- stronger than a name"
                               if route in ("gsis_id", "pfr_id") else
                               "inherited from build/nflverse-rosters.json's name+birth_date "
                               "match; not re-derived here"),
            "club_id": cid, "club_code": e["code"], "club_as_printed": e["team"],
            "club_resolved_as": e["resolved_as"], "league": league, "year": season,
            "rows": e["rows"], "row_count": len(e["rows"]),
        })
    dup = collections.Counter((c["subject"][1], c["value"]) for c in claims)
    bad = [k for k, v in dup.items() if v > 1]
    if bad:
        raise NvError(f"{len(bad)} (man, club-season) pairs hold more than one claim: {bad[:3]}")

    refusals = C.census()
    horizon = [r for r in refusals if str(r[1]).isdigit() and int(r[1]) >= 2025]
    out = {"source": {"source_id": SRC_ID, "stated_by": "nflverse", "acquisition": "held",
                      "definition": DEFN, "definition_limitation": LIMIT, "predicate": PRED,
                      "_stage": "3 of 4",
                      "_identity": {"bridge": "gsis_id/pfr_id via build/nflverse-draft.json",
                                    "bridge_size": len(g2p),
                                    "name_route": "inherited from build/nflverse-rosters.json, not re-derived"},
                      "_not_collapsed": "person subjects, never stints: the builder makes season "
                                        "keys only from stints, so this cannot merge into the spine"},
           "claims": claims,
           "id_bridge_name_mismatches": namecheck,
           "unresolved_club_strings": [{"league": lg, "year": y, "string": s, "why": why, "rows": k}
                                       for lg, y, s, why, k, _ in refusals],
           "counts": {**dict(n), "claims": len(claims),
                      "by_identity_route": dict(collections.Counter(c["identity_route"] for c in claims)),
                      "club_seasons_attested": len({c["value"] for c in claims}),
                      "people": len({c["subject"][1] for c in claims}),
                      "unresolved_club_strings": len(refusals),
                      "unresolved_rows": sum(r[4] for r in refusals),
                      "horizon_strings_2025_plus": len(horizon),
                      "horizon_rows_2025_plus": sum(r[4] for r in horizon)}}
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



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:28s} {v:,}" if isinstance(v, int) else f"  {k}: {v}")
