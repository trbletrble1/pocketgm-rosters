"""The 1934 Cincinnati Reds are their own club-season, built FROM THE BOXSCORES.

RYAN'S RULING, and it is the Card-Pitt shape. The Reds existed, played eight
games, went 0-8 and folded. The St. Louis Gunners bought the franchise and played
the last three. Two clubs, one season -- and the archive shows one, because
StatsCrew collapsed both into SLG, which carries 55 men for a three-game club.

WHY NOT nflverse. nflverse names 27 men on 1934|CIN and that is ONE SOURCE'S WORD
about which club a man belonged to. Splitting 55 men on it would be guessing which
man played which three games, and a wrong split is undetectable and permanent.

WHY THE BOXSCORES. A man who APPEARED IN A REDS GAME played for the Reds. That is
structural, not inferred: the boxscore names him in that club's lineup and links
him by his own PFA code. The archive holds 61 games for 1934, and the Reds' eight
and the Gunners' three are among them with their own lineups. This is exactly how
the merged-club rosters were built when no source held one.

WHAT IT DOES NOT DO. It does not remove anybody from SLG. StatsCrew says all 55
are Gunners; nflverse says 27 are Reds; the boxscores say 20 appeared for the Reds
and 20 for the Gunners with four in both. ALL THREE STAND, counted, resolved by
nobody. The four who appear in both clubs' lineups get both club-seasons, because
that is what the source shows: the franchise changed hands mid-season and they
kept playing.

A MAN IN NEITHER CLUB'S BOXSCORES STAYS UNASSIGNED. 35 of the 55 are attested by
no lineup either way. They keep their SLG season and gain nothing here. Splitting
them by guess is the thing this ingest exists to avoid.

  python3 src/ingest_cin1934.py [--dry]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
import ingest_boxscores as IB

SRC_ID = "pro-football-archives"
YEAR, LEAGUE = 1934, "NFL"
# CIN is the Bengals from 1968, never before. The club map is keyed (code, year),
# so CIN|1934 is free -- checked, not assumed, because that map IGNORES LEAGUE and
# a careless code here would collide the way an AFL 'CHI' in 1926 would have with
# the Bears.
CLUBS = {"Cincinnati Reds": "CIN", "St. Louis Gunners": "SLG"}
NEW_CLUB = "CIN"


class Cin1934Error(Exception):
    pass


def from_boxscores():
    """-> {club_as_printed: {pfa_code: {name, games:[...]}}} , re-parsed from the pages.

    RE-PARSED, not read out of build/pfa-boxscores.json. That store writes a
    game_lineup claim only for a man it could RESOLVE and sends the rest to its
    leads, whose records do not carry a club -- so reading claims alone returns 12
    men a side where the pages name 20, and the eight it drops are exactly the
    unheld men this ingest has to see. The same narrower-source mistake cost the
    1926 AFL half of Wilson's Wildcats."""
    out = collections.defaultdict(dict)
    for fn in sorted(os.listdir(IB.CACHE)):
        m = IB.GAMEID.match(fn)
        if not m or int(m.group(1)) != YEAR:
            continue
        h = open(os.path.join(IB.CACHE, fn), encoding="utf-8", errors="replace").read()
        tabs = IB.find_tables(h)
        meta = IB.parse_meta(h) or {}
        gid = fn.split("_", 1)[1].replace(".html", "")
        for row in IB.parse_lineups(tabs):
            club = row["club_as_printed"]
            if club not in CLUBS:
                continue
            e = out[club].setdefault(row["pfa_code"],
                                     {"name_as_printed": row["name_as_printed"],
                                      "games": [], "rows": []})
            e["games"].append({"pfa_game_id": gid, "date": meta.get("date")})
            e["rows"].append({"position_as_printed": row["position_as_printed"],
                              "position_state": row["position_state"],
                              "jersey": row["jersey"], "jersey_state": row["jersey_state"]})
    return out


def main(write=True):
    box = from_boxscores()
    if set(box) != set(CLUBS):
        raise Cin1934Error(f"expected both clubs in the 1934 boxscores, found {sorted(box)}")
    c2p = json.load(open(os.path.join(
        "/private/tmp/claude-501/-Users-ryannecci-Documents/"
        "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad", "pfa_code2pid.json")))
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    clubs_map = idx.pop("_clubs", {})
    # REFUSE IF THE CLUB-SEASON ALREADY HOLDS MEN, not if the name exists. The first
    # guard refused on the club-map entry, which THIS ingest's own club_name claim
    # creates on the next rebuild -- so the second run refused against the first
    # run's work and the store could never be regenerated. What is worth protecting
    # is a club-season somebody has already populated; a name with no men is the
    # expected state between this ingest and its rebuild.
    already = {p for p, v in idx.items()
               if isinstance(v, dict) and f"{LEAGUE}|{YEAR}|{NEW_CLUB}" in (v.get("seasons") or {})}
    if already:
        raise Cin1934Error(f"{LEAGUE}|{YEAR}|{NEW_CLUB} already holds {len(already)} men in the "
                           f"index -- refusing to write over a populated club-season")

    slg = {pid for pid, p in idx.items()
           if isinstance(p, dict) and f"{LEAGUE}|{YEAR}|SLG" in (p.get("seasons") or {})}
    claims, leads = [], []
    per = {}
    for club, code in CLUBS.items():
        held, lead = [], []
        for pfa, e in sorted(box[club].items()):
            pid = c2p.get(pfa)
            val = {"club_as_printed": club, "club_code": code,
                   "league": LEAGUE, "year": YEAR,
                   "name_as_printed": e["name_as_printed"], "pfa_code": pfa,
                   "appearances": len(e["games"]), "games": e["games"],
                   "lineup_rows": e["rows"],
                   "roster_evidence": "boxscore_lineup",
                   "_why": "a man who appeared in this club's lineup played for this "
                           "club. Structural: the boxscore names him and links his own "
                           "PFA code. Weaker than a roster page -- a man who was on the "
                           "club and never started is NOT here.",
                   "_resolved_on": "pfa_code, never the name"}
            sr = f"{SRC_ID}#nflboxscores1/{YEAR}-{code}"
            if pid:
                held.append(pid)
                # only the NEW club-season is written; SLG already exists and this
                # ingest does not touch it
                if code == NEW_CLUB:
                    claims.append({"source_record": sr, "source_id": SRC_ID,
                                   "stated_by": "Pro Football Archives",
                                   "attribution": ["Pro Football Archives"],
                                   # ["stint", PERSON, club, season] -- the person in s[1],
                                   # not the league. Same defect as afl-1926: the builder
                                   # resolves s[1] to a person and skipped all 12 of these
                                   # silently. League comes from the filename (nfl-1934-...).
                                   "subject": ["stint", pid, code, str(YEAR)],
                                   "predicate": "pfa.boxscore_roster_membership",
                                   "value": val, "kind": "observed",
                                   "observed_at": "fetched-2026-09", "person": pid})
                claims.append({"source_record": sr, "source_id": SRC_ID,
                               "stated_by": "Pro Football Archives",
                               "attribution": ["Pro Football Archives"],
                               "subject": ["person", pid],
                               "predicate": "pfa.club_1934_boxscore_attested",
                               "value": val, "kind": "observed",
                               "observed_at": "fetched-2026-09"})
            else:
                lead.append(pfa)
                leads.append({"lead_id": f"lead-cin1934-{len(leads)+1:03d}",
                              "category": "player_lead_unpromoted",
                              "pfa_code": pfa, "name_as_printed": e["name_as_printed"],
                              "places_on": {"league": LEAGUE, "year": YEAR, "club": code,
                                            "club_as_printed": club},
                              "roster_evidence": "boxscore_lineup",
                              "source_id": SRC_ID, "source_record": sr,
                              "IS_NOT_A_PERSON": True,
                              "why": "no archive person resolves to this PFA code. Ryan's "
                                     "ruling on player leads stands: parked, not promoted.",
                              "roster_line": val})
        per[code] = {"club_as_printed": club, "held": held, "leads": lead,
                     "men_attested": len(box[club])}

    cin, gun = set(per["CIN"]["held"]), set(per["SLG"]["held"])
    unassigned = sorted(slg - cin - gun)
    out = {
        "source": {"source_id": SRC_ID, "name": "Pro Football Archives boxscores, 1934",
                   "stated_by": "Pro Football Archives", "acquisition": "fetched",
                   "_roster_evidence": "boxscore_lineup -- NOT a roster page"},
        "clubs": {c: {k: v for k, v in d.items() if k != "held"} for c, d in per.items()},
        "claims": claims, "leads": leads,
        "disagreement": {
            "_held_not_resolved": "three sources, three answers, none overruled",
            "statscrew": {"says": f"all {len(slg)} men are St. Louis Gunners "
                                  f"({LEAGUE}|{YEAR}|SLG)", "men": len(slg)},
            "nflverse": {"says": "27 men are Cincinnati Reds (1934|CIN)", "men": 27},
            "pfa_boxscores": {"says": f"{len(cin)} men appeared for Cincinnati and "
                                      f"{len(gun)} for the Gunners; "
                                      f"{len(cin & gun)} appeared for BOTH",
                              "cincinnati": len(cin), "gunners": len(gun),
                              "both": len(cin & gun)}},
        "unassigned": {
            "_ruling": "a man in neither club's boxscores is NOT split by guess. He keeps "
                       "his SLG season and gains nothing here.",
            "count": len(unassigned), "person_ids": unassigned},
        "counts": {"cincinnati_men_attested": per["CIN"]["men_attested"],
                   "cincinnati_held": len(cin), "cincinnati_leads": len(per["CIN"]["leads"]),
                   "gunners_men_attested": per["SLG"]["men_attested"],
                   "gunners_held": len(gun), "gunners_leads": len(per["SLG"]["leads"]),
                   "played_for_both": len(cin & gun),
                   "slg_men_before": len(slg), "unassigned": len(unassigned),
                   "claims": len(claims), "leads": len(leads)}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, os.path.join(BASE, "build", "nfl-1934-cincinnati.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--dry" not in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:28s} {v:,}")
