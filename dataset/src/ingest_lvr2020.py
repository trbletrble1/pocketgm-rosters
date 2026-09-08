"""LVR|2020 from nflverse, because StatsCrew's page is blank.

RYAN'S RULING. The archive is multi-source by design; leaving a whole club-season
empty because ONE source has a hole is the wrong trade. StatsCrew serves the Las
Vegas Raiders' 2020 roster page -- 34,580 bytes, correct headers -- with an EMPTY
<tbody> and a note inviting anyone with the information to send it in. Every other
Raiders season parses (2018 OAK 77 rows, 2019 OAK 71, 2021 LVR 69, 2022 67,
2023 64). That is a hole, not a fact, and the archive mirrored it faithfully.

WHY NOT PFR, WHICH THE BRIEF PREFERRED. It is not on disk. The 78 saved
Pro-Football-Reference pages are 30 club rosters from 1979 plus one DRAFT LISTING
per year 2017-2025; there is no 2020 roster page for any club. The brief's own
fallback therefore applies: nflverse, and say so.

THE DEFINITION DIFFERS AND THE STORE SAYS SO. nflverse counts everyone who
appeared on a roster at any point in the year; StatsCrew's 2020 clubs average
about 69 men and nflverse gives the Raiders 86. A reader comparing club sizes for
2020 will see one club that is a fifth larger than its neighbours, and the reason
has to be legible from the data rather than from a commit message. Every claim
here carries source_id "nflverse-rosters" and a _roster_definition note, and the
store records that this is the only 2020 club-season not built from StatsCrew.

BETTER SOURCE AVAILABLE, NOT USED HERE. The club's own 2020 media guide is on
disk (nfl-books/text_all/raiders-2020-media-guide-las-vegas.txt, 1.9 MB from the
Internet Archive) and media guides outrank both PFR and nflverse in this archive.
Its alphabetical roster is OCR'd with the jersey-number column split away from the
names and hometown lines interleaved, so extracting it cleanly is a parsing job
with a real risk of a wrong name, not a lookup. Recorded as the upgrade path.

  python3 src/ingest_lvr2020.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write

NV = os.path.join(BASE, "build", "nflverse-rosters.json")
LEAGUE, YEAR, CLUB, NV_TEAM = "NFL", 2020, "LVR", "2020|LV"


class LvrError(Exception):
    pass


def main(write=True):
    nv = json.load(open(NV))
    men = [c for c in nv["claims"]
           if c["predicate"] == "nflverse.roster_membership" and c["value"] == NV_TEAM]
    if not men:
        raise LvrError(f"nflverse has no {NV_TEAM} membership -- refusing to write an "
                       f"empty club-season over an empty club-season")
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    clubs = idx.pop("_clubs", {})
    if clubs.get(f"{CLUB}|{YEAR}") is None:
        raise LvrError(f"{CLUB}|{YEAR} is not in the club map; this ingest fills an "
                       f"existing empty club-season, it does not invent one")
    held = sum(1 for pid, p in idx.items()
               if isinstance(p, dict) and f"{LEAGUE}|{YEAR}|{CLUB}" in (p.get("seasons") or {}))
    if held:
        raise LvrError(f"{LEAGUE}|{YEAR}|{CLUB} already holds {held} men -- refusing to "
                       f"write over a club-season somebody has already filled")

    # what the OTHER 31 clubs that year were built from, measured not assumed
    sc = collections.Counter()
    for pid, p in idx.items():
        if not isinstance(p, dict):
            continue
        for k in (p.get("seasons") or {}):
            if k.startswith(f"{LEAGUE}|{YEAR}|"):
                sc[k.split("|")[2]] += 1
    peer = sorted(sc.values())
    median = peer[len(peer) // 2] if peer else None

    claims = []
    for c in men:
        pid = c["subject"][1]
        if pid not in idx:
            raise LvrError(f"{pid} is on nflverse's roster but not in the index")
        val = {"club_as_printed": clubs[f"{CLUB}|{YEAR}"], "club_code": CLUB,
               "league": LEAGUE, "year": YEAR,
               "nflverse_team": "LV", "match_route": c.get("match_route"),
               "roster_evidence": "nflverse_roster_csv",
               "_source_differs_from_the_other_31_clubs":
                   f"every other {LEAGUE} {YEAR} club-season in this archive comes from "
                   f"StatsCrew, whose roster page for this club is blank. This one is "
                   f"nflverse.",
               "_roster_definition":
                   f"nflverse counts everyone who appeared on a roster at any point in "
                   f"the season. The other 31 clubs that year hold a median of {median} "
                   f"men; this club holds {len(men)}. The difference is the definition, "
                   f"not the club."}
        claims.append({"source_record": c["source_record"], "source_id": "nflverse-rosters",
                       "stated_by": "nflverse", "attribution": nv["source"]["name"],
                       # ["stint", PERSON, club, season]. Third store I wrote with the
                       # league in s[1] and the person as a sidecar the builder never
                       # reads -- caught by gate_stint_subjects, not by me, and only
                       # after Parsing found the first two. 86 of 86 skipped silently.
                       "subject": ["stint", pid, CLUB, str(YEAR)],
                       "predicate": "nflverse.roster_membership_stint",
                       "value": val, "kind": "observed", "observed_at": "roster-2020",
                       "person": pid})
    out = {"source": {"source_id": "nflverse-rosters", "name": nv["source"]["name"],
                      "stated_by": "nflverse", "acquisition": "fetched",
                      "_why_not_statscrew": "StatsCrew's LVR/2020 roster page has an empty "
                                            "<tbody> and asks for contributions",
                      "_why_not_pfr": "no 2020 roster page on disk; the saved PFR pages are "
                                      "1979 rosters and per-year draft listings",
                      "_better_source_available": "nfl-books/text_all/"
                                                  "raiders-2020-media-guide-las-vegas.txt -- "
                                                  "the club's own guide, outranks this, OCR "
                                                  "needs work"},
           "claims": claims,
           "counts": {"men": len(claims), "peer_clubs_that_year": len(sc),
                      "peer_median_men": median,
                      "peer_range": [min(peer), max(peer)] if peer else None}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, os.path.join(BASE, "build", "nfl-2020-lvr.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--dry" not in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:24s} {v}")
