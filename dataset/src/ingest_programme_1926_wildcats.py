"""1926 N.Y. Football Yankees v Pacific Coast Wildcats: cover and team-photograph page.

WHY THIS ONE MATTERS. `AFL|1926|AFLPC` is one of only THREE club-seasons in the whole
archive that no source ever gave a roster for -- `roster_evidence: boxscore_lineup`,
declared by ingest_afl1926.py because PFA's roster page is a hard 404. Its ten held men
were worked out from who appeared in box scores, so a squad man who never played is not
in the archive at all. This caption names TWENTY-TWO, and the ten it confirms are the
ONLY corroboration this club-season has from a source that is not PFA.

A TEAM PHOTOGRAPH IS NOT A ROSTER AND NOT A LINE-UP. It asserts that these men were
photographed together as this club. It does not say any of them played in this game, and
it does not say they were on a roster on any particular day. `roster_membership.*` means
a club stated a man's standing; `programme.probable_lineup` means a publisher expected
him to start. This is weaker than both and is filed under neither.

  python3 src/ingest_programme_1926_wildcats.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
from readings import person_name

SOURCE = {
    "source_id": "programme-1926-nyy-pcw",
    "name": "N. Y. FOOTBALL YANKEES vs PACIFIC COAST WILDCATS -- Yankee Stadium, "
            "Sunday October 24, 1926",
    "acquisition": "photographed",
    "stated_by": "the programme's publisher (not named on the pages held)",
    "attribution": ["N. Y. Football Yankees vs Pacific Coast Wildcats programme, "
                    "Yankee Stadium, 24 October 1926"],
    "rights": "published in the United States in 1926 -- public domain outright",
    "acquired_from": "one photograph supplied by Ryan, 2026-09-07 (cover and team-photo page)",
    "transcription": "docs/1926-yankees-pacific-coast-wildcats-transcription.md (Dropbox); "
                     "one reader, NOT checked by a second",
    "pages_held": ["cover", "team-photograph page, Pacific Coast Wildcats"],
    "pages_not_seen": "every other page, INCLUDING any line-up page",
}
SR_COVER = f"{SOURCE['source_id']}#cover"
SR_PHOTO = f"{SOURCE['source_id']}#team-photograph"
GAME = ["game", "AFL", "1926", "1926-10-24-nyy-pcw"]
CLUB, SEASON, LEAGUE = "AFLPC", "1926", "AFL"

PREDICATE_DEFINITIONS = {
    "programme.team_photograph": {
        "definition": "named in the caption to a team photograph: this man was "
                      "photographed with this club, as this club.",
        "is_not_a_roster": "it does not say the club stated his standing on any day. "
                           "roster_membership.* means a club or a source asserted a man's "
                           "place on a squad; a photograph asserts he was there when it "
                           "was taken.",
        "is_not_a_lineup": "it does not say he played, or was expected to play, in the "
                           "game the programme was printed for. It is weaker than "
                           "programme.probable_lineup, which is already weaker than "
                           "roster_membership.started_a_game.",
        "what_it_is_good_for": "existence and association. For a club-season built "
                               "entirely from box scores, a photograph is the only thing "
                               "that can show a man who never got on the field.",
        "ruled_by": "Archive proposes; Ryan to rule. Raised rather than filed under an "
                    "existing predicate, on the probable-line-up precedent.",
    },
}

# The caption, verbatim, in printed order. (row, name as printed)
CAPTION = [
    (1, "J. Lawson"), (1, "D. Carey"), (1, "H. Shipkey"), (1, "W. Ericson"), (1, "T. Bucklin"),
    (2, "A. Wilson"), (2, "C. Johnston"), (2, "E. Clark"), (2, "L. de Wolf"), (2, "D. Morrison"),
    (2, "T. Illman"),
    (3, "R. Reed"), (3, "R. Stephens"), (3, "R. Flaherty"), (3, "J. Vesser"), (3, "N. Busch"),
    (3, "G. Wilson"),
    (4, "R. Morrison"), (4, "M. Bross"), (4, "E. McRea"), (4, "J. Bradshaw"), (4, "C. Walters"),
]
ROW_LABELS = {1: "Top row, left to right", 2: "2d Row", 3: "3d Row", 4: "Bottom Row"}

# THE JOIN, PER MAN, WITH ITS EVIDENCE. Nine are initial + surname unique on the
# club-season. The tenth is a stated spelling judgement. G. Wilson is NOT joined --
# `Wilson` is held once on this club-season and it is ABE Wilson; joining G. to him
# would be the Sternaman collision exactly.
JOIN = {
 "J. Lawson":   ("P_015811", "Jim Lawson",       "initial J. + surname, unique on AFL|1926|AFLPC"),
 "T. Bucklin":  ("P_015745", "Ted Bucklin",      "initial T. + surname, unique on the club-season"),
 "A. Wilson":   ("P_015831", "Abe Wilson",       "initial A. + surname. NOTE: `Wilson` is held ONCE "
                                                 "here and the caption carries TWO Wilsons; the "
                                                 "initial is what separates them"),
 "T. Illman":   ("P_015839", "Ted Illman",       "initial T. + surname, unique on the club-season"),
 "R. Stephens": ("P_015817", "Ray Stephens",     "initial R. + surname, unique on the club-season"),
 "R. Flaherty": ("P_014463", "Ray Flaherty",     "initial R. + surname, unique on the club-season"),
 "J. Vesser":   ("P_015749", "John Vesser",      "initial J. + surname, unique on the club-season"),
 "M. Bross":    ("P_015794", "Mal Bross",        "initial M. + surname, unique on the club-season"),
 "J. Bradshaw": ("P_015253", "Jim Bradshaw",     "initial J. + surname, unique on the club-season"),
 "W. Ericson":  ("P_015820", "Walden Erickson",  "SPELLING VARIANT, stated as a judgement: the "
                                                 "programme prints Ericson with one k, the archive "
                                                 "holds Erickson. Initial W. agrees, no competing "
                                                 "Eric-/Erick- surname on the club-season. Both "
                                                 "spellings stay as printed"),
}

REFUSALS = [
 {"refusal_id": "refuse-pcw-1926-g-wilson",
  "kind": "unclassifiable",
  "subject": "`G. Wilson` in the team-photograph caption",
  "why": "George 'Wildcat' Wilson is the man this club was named for, and the archive does "
         "NOT hold him on AFL|1926|AFLPC -- because the club-season was derived from box "
         "scores and he does not appear in the ones that were read. `Wilson` resolves once "
         "on this club-season and that man is ABE Wilson, who is separately in this same "
         "caption. Joining G. to him would merge two men named in one photograph.",
  "what_would_settle_it": "a source placing George Wilson on this club-season by a route "
         "other than this caption -- a roster, a box score, or a contract",
  "ruling": "hold as printed; do not join, do not create a person"},
 {"refusal_id": "refuse-pcw-1926-h-shipkey",
  "kind": "unclassifiable",
  "subject": "`H. Shipkey` here against `HARRY SHIPKEY` on the 1926 Bears v L.A. Tigers programme",
  "why": "two documents from the same season, both photographed this year, naming a Shipkey "
         "on two different West Coast clubs. The Tigers programme gives him as 23, 6 ft 2, "
         "205 lbs, Stanford tackle. This caption gives an initial and a surname and nothing "
         "else. A man can play for two clubs in one season and it is not evidence that he did.",
  "what_would_settle_it": "a date-scoped source for either club, or a fuller name here",
  "ruling": "hold both as printed; neither joined to the other nor to a held person"},
 {"refusal_id": "refuse-pcw-1926-morrisons",
  "kind": "unclassifiable",
  "subject": "`D. Morrison` and `R. Morrison`, both in this caption",
  "why": "two Morrisons in one photograph. Contemporary accounts name a Duke Morrison as a "
         "Wildcats runner, which suggests but does not establish that D. is Duke; R. is "
         "unidentified. Neither is held on this club-season.",
  "what_would_settle_it": "a source giving forenames for this club's squad",
  "ruling": "hold both as printed; do not decide which is which"},
]


def _promoted():
    """Men this caption's leads were promoted into people by, from the decision store.
    The id is the DECISION's -- never minted here, never minted twice. Names are read
    through readings.person_name, the archive's one name reading, rather than a local
    copy: there were four copies of that rule and they disagreed."""
    p = os.path.join(BASE, "build", "player-promotions.json")
    if not os.path.exists(p):
        return {}
    out = {}
    for q in json.load(open(p))["promotions"]:
        if q.get("source", "").startswith(SOURCE["source_id"]):
            out[person_name(q["name"])] = q
    return out


def main(write=True):
    claims, leads = [], []
    n = collections.Counter()
    promoted = _promoted()

    def claim(sr, subj, pred, val, **kw):
        c = {"source_record": sr, "source_id": SOURCE["source_id"],
             "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
             "subject": subj, "predicate": pred, "value": val, "kind": "observed",
             "observed_at": "photographed-2026-09"}
        c.update(kw); claims.append(c); n[pred] += 1; return c

    for pred, val in (
        ("programme.title", "N. Y. FOOTBALL YANKEES vs PACIFIC COAST WILDCATS"),
        ("programme.date_as_printed", "Sunday October 24, 1926"),
        ("programme.venue_as_printed", "Yankee Stadium, New York"),
        ("programme.price_as_printed", "PRICE 15 CENTS"),
        ("programme.cover_figure_as_printed", "HAROLDE [Red] GRANGE"),
        ("programme.club_as_printed", "PACIFIC COAST WILDCATS"),
    ):
        claim(SR_COVER if pred != "programme.club_as_printed" else SR_PHOTO, GAME, pred, val)

    # ---- the ten: corroboration for a club-season that otherwise rests on PFA alone
    for row, name in CAPTION:
        if name not in JOIN: continue
        pid, held_as, why = JOIN[name]
        claim(SR_PHOTO, ["stint", pid, CLUB, SEASON], "programme.team_photograph",
              {"name_as_printed": name, "held_as": held_as,
               "caption_row": ROW_LABELS[row],
               "club_as_printed": "PACIFIC COAST WILDCATS",
               "club_code": CLUB, "league": LEAGUE, "year": int(SEASON), "game": GAME,
               "_join_evidence": why,
               "_definition": PREDICATE_DEFINITIONS["programme.team_photograph"]["definition"],
               "_is_not_a_roster": PREDICATE_DEFINITIONS["programme.team_photograph"]["is_not_a_roster"],
               "_corroboration": "AFL|1926|AFLPC is one of three club-seasons in the archive "
                   "that NO source gave a roster for; its men were derived from box scores "
                   "by ingest_afl1926.py. This caption is the ONLY corroboration this "
                   "club-season has from a source that is not Pro Football Archives."},
              person=pid)

    # ---- the twelve. Held as leads until 2026-09-08; a man PROMOTED under the
    # team-photograph ruling now gets a claim instead, and it is the SAME claim the ten
    # held men get. The predicate does not move: he was photographed with this club.
    # Nothing here says he played, and no roster_membership claim is written.
    for row, name in CAPTION:
        if name in JOIN: continue
        q = promoted.get(person_name(name))
        if q:
            claim(SR_PHOTO, ["stint", q["person_id"], CLUB, SEASON], "programme.team_photograph",
                  {"name_as_printed": name, "held_as": None,
                   "caption_row": ROW_LABELS[row],
                   "club_as_printed": "PACIFIC COAST WILDCATS",
                   "club_code": CLUB, "league": LEAGUE, "year": int(SEASON), "game": GAME,
                   "_join_evidence": "NOT a join. This man matched nobody in the archive; he "
                       "was PROMOTED from this caption into a person of his own under Ryan's "
                       "ruling of 2026-09-08, and his id is that decision's. "
                       "See build/player-promotions.json.",
                   "_no_archive_match_evidence": q.get("no_archive_match_evidence"),
                   "_forename_unknown": q.get("forename_unknown"),
                   "_definition": PREDICATE_DEFINITIONS["programme.team_photograph"]["definition"],
                   "_is_not_a_roster": PREDICATE_DEFINITIONS["programme.team_photograph"]["is_not_a_roster"],
                   "_promoted_not_rostered": "He is a person because the caption places him in "
                       "the team picture of a club-season the archive holds. This claim says "
                       "that and only that -- it is not roster membership and does not become "
                       "it. AFL|1926|AFLPC has no roster from any source; its ten other men "
                       "were derived from box scores, which see only who STARTED."},
                  person=q["person_id"])
            n["promoted_into_a_person"] += 1
            continue
        leads.append({
            "lead_id": f"lead-pcw-1926-{len(leads)+1:03d}",
            "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
            "name_as_printed": name, "caption_row": ROW_LABELS[row],
            "places_on": {"club_as_printed": "Pacific Coast Wildcats", "club_code": CLUB,
                          "league": LEAGUE, "year": int(SEASON), "game": GAME,
                          # THE KEY THE ARCHIVE USES. promote_players decides against the
                          # club-seasons the index holds, so the lead has to name one in
                          # that shape rather than leave the route to reconstruct it.
                          "club_season": f"{LEAGUE}|{SEASON}|{CLUB}"},
            "evidence_kind": "team_photograph",
            "source_id": SOURCE["source_id"], "source_record": SR_PHOTO,
            "why": "named in the team-photograph caption and NOT held on AFL|1926|AFLPC. "
                   "Ryan's ruling on player leads stands: parked, not promoted. The join is "
                   "a judgement per man and nothing here matched on a surname.",
            "refusal": next((r["refusal_id"] for r in REFUSALS
                             if name.split(". ")[-1].lower() in r["subject"].lower()), None),
        })
        n["leads"] += 1

    claim(SR_PHOTO, GAME, "programme.caption_verbatim",
          {"club": "PACIFIC COAST WILDCATS",
           "rows": {ROW_LABELS[r]: [nm for rr, nm in CAPTION if rr == r] for r in (1, 2, 3, 4)},
           "men_named": len(CAPTION), "row_counts": [5, 6, 6, 5],
           "_held_as_printed": "initials and surnames exactly as the caption sets them, "
                               "including `W. Ericson` with one k and `de Wolf` lower-case"})

    out = {"source": SOURCE,
           "source_records": {
             SR_COVER: {"source_id": SOURCE["source_id"], "locator": "cover",
                        "description": "cover -- title, date, venue, price, HAROLDE [Red] GRANGE"},
             SR_PHOTO: {"source_id": SOURCE["source_id"], "locator": "team-photograph",
                        "description": "team-photograph page, Pacific Coast Wildcats, "
                                       "22 men named in the caption"}},
           "game": GAME,
           "predicate_definitions": PREDICATE_DEFINITIONS,
           "claims": claims, "leads": leads, "refusals": REFUSALS,
           "counts": {"claims": len(claims), "leads": len(leads),
                      "men_in_caption": len(CAPTION),
                      "corroborated_held_men": len(JOIN),
                      "unheld_leads": len(leads),
                      "refusals": len(REFUSALS),
                      "held_people_touched": len({c["person"] for c in claims if "person" in c}),
                      "by_predicate": dict(n)}}
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "programme-1926-nyy-pcw.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"claims {c['claims']}  leads {c['leads']}  refusals {c['refusals']}")
    print(f"  caption names {c['men_in_caption']}: {c['corroborated_held_men']} corroborate held men, "
          f"{c['unheld_leads']} parked as leads")
    print(f"  held people touched: {c['held_people_touched']}")
