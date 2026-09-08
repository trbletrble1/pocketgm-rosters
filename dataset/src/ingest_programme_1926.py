"""The 1926 Chicago Bears v Los Angeles Tigers programme: one document, two pages.

FILED UNDER THE GAME, NOT A SEASON. Ryan's ruling of 2026-09-07: a non-league
professional club enters the archive when a club in scope played it in a documented
game, and it enters FOR THAT GAME ONLY. So the Los Angeles Tigers get a game
subject and no club-season, and the year problem never arises.

THE YEAR PROBLEM, RECORDED BECAUSE IT NEARLY HAPPENED. The document is dated
16 January 1926, which is a calendar date inside the 1925 NFL season. Measured
against the person index: the 22 printed Bears names resolve on NFL|1925|CHI at
22 of 22 with Grange and BOTH Sternamans held, and on NFL|1926|CHI at 13 of 23
with neither. The programme prints `3 E. Sternaman` and `4 J. Sternaman`; the held
1926 Bears carry only Dutch, so filing this under 1926 would have given Joey's
claims to his brother -- undetectable and permanent. The Bears corroboration
therefore joins NFL|1925|CHI, which is where the football belongs.

A PROBABLE LINE-UP IS NOT A BOXSCORE LINEUP. Printed before kickoff, by a
publisher, asserting who was expected to start. `roster_membership.started_a_game`
means "named in a starting lineup, from a boxscore" -- an after-the-fact record of
what happened. They are different assertions and are NOT filed together. This
document proves the gap in its own pages: it lists `22 McMillen` at right guard in
the probable line-up and does not carry McMillen in the roster at all.

NOBODY ON THE TIGERS IS A PERSON. The archive holds no Los Angeles Tigers
club-season and not one of the 28 resolves to a held man. Under the afl-1926
precedent they are LEADS, parked and not promoted, carrying the full field set so
that promoting one later is a ruling rather than a re-read.

VALUES ARE HELD AS PRINTED. `Univefsity`, `Southen California`, `Pittsburg`,
Cory's `5 ft. 8 1/2 in.`, both spellings of Phythain/Phythian. Nothing is corrected.
Starke's age is ABSENT -- the entry gives height and weight and omits age -- which
is a different fact from unmeasured, and is written as kind="absent".

  python3 src/ingest_programme_1926.py [--dry]
"""
import os, re, sys, json, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO

SOURCE = {
    "source_id": "programme-1926-chi-lat",
    "name": "OFFICIAL GRID PROGRAM -- Chicago Bears vs Los Angeles Tigers, "
            "Los Angeles Coliseum, January 16, 1926",
    "acquisition": "photographed",
    "stated_by": "The Frank Meline Co., Sun Building, 706 So. Hill St. (publisher's imprint)",
    "attribution": ["OFFICIAL GRID PROGRAM, The Frank Meline Co., Los Angeles, 1926"],
    "rights": "published in the United States in 1926 -- public domain outright",
    "acquired_from": "two photographs supplied by Ryan, 2026-09-07",
    "transcription": "docs/1926-bears-tigers-programme-transcription.md (Dropbox), "
                     "read from the images by one reader; NOT checked by a second, "
                     "and NOT the census_programs_* extraction, which yielded zero",
    "pages_held": ["front spread (probable line-ups, both rosters, scoring grid)",
                   "page seven (TIGERS ON THE FIELD)"],
    "pages_not_seen": "every other page of the programme",
}
SR_FRONT = f"{SOURCE['source_id']}#front-spread"
SR_PAGE7 = f"{SOURCE['source_id']}#page-seven"

# THE GAME IS THE SUBJECT. ["game", league, year, number] is the boxscore shape;
# this game belongs to no league, so the league slot says so rather than borrowing
# one, and the number slot carries the date because that is what identifies it.
GAME = ["game", "EXHIBITION", "1926", "1926-01-16-chi-lat"]

PREDICATE_DEFINITIONS = {
    "programme.probable_lineup": {
        "definition": "named in a PROBABLE line-up printed in a game programme before "
                      "kickoff. An expectation stated in advance by a publisher, not a "
                      "record of who took the field.",
        "is_not": "roster_membership.started_a_game, which means 'named in a starting "
                  "lineup, from a boxscore' -- an after-the-fact record of what happened",
        "ruled_by": "Ryan, 2026-09-07, on this document",
        "evidence_that_they_differ": "this programme lists 22 McMillen at right guard in "
                                     "the probable line-up and does not carry McMillen in "
                                     "the roster list at all",
    },
    "programme.roster_as_printed": {
        "definition": "named in a club's roster list as printed in a game programme. "
                      "Corroborating for a club the archive already holds; it is the "
                      "publisher's list, not the club's.",
    },
    "programme.annotation": {
        "definition": "a mark made on the document by a reader, not by the publisher. "
                      "Held as an annotation on the document and never as a source for "
                      "the fact it appears to state.",
    },
}

# ---------------------------------------------------------------- page seven
# no, name as printed, age, height, weight, college/prior as printed, position.
# None = the page prints nothing there. "" is never used; absence is absence.
TIGERS = [
 (1,  'JACK NOLAN',            '25 years', '5 ft. 10 in.',    '185 lbs.', 'Santa Clara U., Guard 1922-24', 'Guard'),
 (2,  'BILL COLE',             '24 years', '6 ft. 2 in.',     '210 lbs.', 'U. Southern California 1923', 'Tackle'),
 (4,  'STUART "STEW" BEAM',    '25 years', '6 ft. 2 in.',     '195 lbs.', 'All coast tackle 1923 University of California', 'Tackle'),
 (5,  'DEL HUFFORD',           '25 years', '5 ft. 11 in.',    '175 lbs.', 'University of California End 1923', 'End'),
 (6,  'HOGEY EVANS',           '24 years', '5 ft. 9 in.',     '175 lbs.', 'University of California Quarterback 1923', 'Quarterback'),
 (7,  'HARRY SHIPKEY',         '23 years', '6 ft. 2 in.',     '205 lbs.', 'Stanford Tackle 1924', 'Tackle'),
 (8,  'GEO. BAKER',            '22 years', '6 ft. 2 in.',     '190 lbs.', 'Stanford 1924', 'Center'),
 (9,  'ROY BAKER',             '25 years', '5 ft. 10 in.',    '175 lbs.', 'University of Southern California 1922', 'Halfback'),
 (10, 'PAUL MINNICK',          '26 years', '5 ft. 11 in.',    '195 lbs.', 'University of Iowa guard 1922', 'Guard'),
 (11, 'FELTON McCONNELL',      '24 years', '6 ft. 2 in.',     '195 lbs.', 'Georgia Tech. Tackle 1923', 'Tackle'),
 (12, 'KARL RENIUS',           '28 years', '6 ft.',           '180 lbs.', 'Occidental 1925. Center', 'Center'),
 (14, 'GENE CORY',             '27 years', '5 ft. 8½ in.', '210 lbs.', 'Occidental 1920-22. Captain and Tackle 1922', 'Guard'),
 (15, '"HONEY" EARLE',         '22 years', '5 ft. 10',        '180 lbs.', 'University of Southern California halfback', 'Halfback'),
 (16, 'DEWEY LYLE',            '29 years', '6 ft.',           '185 lbs.', 'Minnesota 1916 end', 'End'),
 (17, 'OAK SMITH',             '30 years', '6 ft.',           '180 lbs.', 'Drake University 1916 Captain and end', 'End'),
 (18, '"COWBOY" WELLS',        '23 years', '6 ft.',           '175 lbs.', 'Sewanee University', None),
 (19, 'HAYDEN PHYTHAIN',       '23 years', '5 ft. 10½ in.', '170 lbs.', 'U. Southen California. End 1924', 'End'),
 (21, 'LEE DEMPSEY',           '25 years', '6 ft.',           '175 lbs.', 'Dubuque, Iowa 1921 End', 'End'),
 (22, 'DAN HAY',               '24 years', '6 ft.',           '170 lbs.', 'New York Univefsity 1922 half-back', 'Halfback'),
 (24, 'WILLIAM BLEWETT',       '22 years', '5 ft. 10 in.',    '190 lbs.', 'University of California halfback 1922', 'Halfback'),
 (26, "WALT O'BRIEN",          '26 years', '5 ft. 10 in.',    '166 lbs.', 'University of California end 1923', 'End'),
 (27, '"HOBO" KINCAID',        '27 years', '5 ft. 11 in.',    '180 lbs.', 'University of Southern California halfback 1922', 'Halfback'),
 (28, '"TIGER" RATTERMAN',     '25 years', '6 ft. 2 in.',     '210 lbs.', 'Georgia Tech. Captain Bull Dogs 1920', 'Center and end'),
 (29, 'CHUCK WINTERBURN',      '25 years', '5 ft. 8 in.',     '210 lbs.', 'Coach at Santa Ana. From Pittsburg in 1923', 'Plays quarterback'),
 (33, 'GEORGE WILSON',         '24 years', '5 ft. 11 in.',    '185 lbs.', 'Univ. of Washington 1924', 'All American Halfback'),
 (40, 'NEWTON STARKE',         None,       '5 ft. 10 in.',    '155 lbs.', 'Played end for three years at University of Southern California, finishing this season', 'End'),
 (41, 'JOHNNY HAWKINS',        '23 years', '6 ft.',           '175 lbs.', 'All-Pacific Coast guard at U. S. C. in 1923. Would have been All-American in 1924 when he captained Trojans but played quarter instead', None),
 (None,'"TIGER" KATTERMAN',    '25 years', '6 ft. 2 in.',     '210 lbs.', 'Played end and center at Georgia Tech prior to 1919', None),
]

TIGERS_STAFF = [
 ('SID NICHOLS',   'Quarterback Illinois 1915-17. Now head coach Occidental University.'),
 ('SID FOSTER',    'Director of Athletics at Manuel Arts High School, Occidental Halfback 1914-15-16.'),
 ('SID COLLINS',   'All time Center Nebraska University 1907-8-10.'),
 ('BILL ANDERSON', 'University Illinois 1914-15-16. Trainer Occidental College.'),
]

NO_TRAILING_POSITION = {'"COWBOY" WELLS', 'JOHNNY HAWKINS', '"TIGER" KATTERMAN'}

# ------------------------------------------------------- front spread, Tigers
TIGERS_FRONT = [(1,'Nolan'),(2,'Cole'),(4,'Beam'),(5,'Hufford'),(6,'Evans'),(7,'Shipkey'),
 (8,'G. Baker'),(9,'R. Baker'),(10,'Minnick'),(11,'McConnell'),(12,'Renius'),(14,'Cory'),
 (15,'Earle'),(16,'Lyle'),(17,'Smith'),(18,'Wells'),(19,'Phythian'),(21,'Dempsey'),
 (22,'Hay'),(24,'Blewett'),(26,"O'Brien"),(27,'Kincaid'),(28,'Ratterman'),(29,'Winterburn'),
 (33,'Wilson'),(40,'Starke'),(41,'Hawkins'),(None,'Katterman')]

# -------------------------------------------------------- front spread, Bears
BEARS_FRONT = [(3,'E. Sternaman'),(4,'J. Sternaman'),(7,'Halas'),(9,'White'),(10,'Romney'),
 (11,'Knop'),(12,'Blacklock'),(13,'Trafton (Capt.)'),(15,'Fleckenstein'),(16,'Healy'),
 (17,'Scott'),(18,'Murry'),(19,'Hanny'),(21,'Mullen'),(24,'Anderson'),(25,'Walquist'),
 (26,'Mohardt'),(27,'Crawford'),(28,'Smith'),(29,'Bryan'),(77,'Grange'),(80,'Britton')]

# The per-man join, stated. Each is a JUDGEMENT with its evidence, never a sweep.
# key = name as printed on the front spread -> (P_ id, the evidence for this man)
BEARS_JOIN = {
 'E. Sternaman':   ('P_002760', 'printed initial E. + surname; Dutch Sternaman is Edward. '
                                'Two Sternamans are held on NFL|1925|CHI and the printed '
                                'initials are what separate them'),
 'J. Sternaman':   ('P_014762', 'printed initial J. + surname; Joey Sternaman. See above -- '
                                'without the initials this pair is unjoinable'),
 'Halas':          ('P_002747', 'surname unique on the held NFL|1925|CHI roster'),
 'White':          ('P_015343', 'surname unique on the held NFL|1925|CHI roster'),
 'Romney':         ('P_015134', 'surname unique on the held NFL|1925|CHI roster'),
 'Knop':           ('P_002606', 'surname unique on the held NFL|1925|CHI roster'),
 'Blacklock':      ('P_002741', 'surname unique on the held NFL|1925|CHI roster'),
 'Trafton (Capt.)':('P_002761', 'surname unique on the held NFL|1925|CHI roster; the '
                                'captaincy is printed and is held as printed'),
 'Fleckenstein':   ('P_015341', 'surname unique on the held NFL|1925|CHI roster'),
 'Healy':          ('P_002804', 'SPELLING VARIANT: the programme prints Healy, the archive '
                                'holds Ed Healey. One letter, unique on the club-season, no '
                                'competing Heal- surname. Stated as a judgement, not a match'),
 'Scott':          ('P_002901', 'surname unique on the held NFL|1925|CHI roster'),
 'Murry':          ('P_014976', 'surname unique on the held NFL|1925|CHI roster'),
 'Hanny':          ('P_015045', 'surname unique on the held NFL|1925|CHI roster'),
 'Mullen':         ('P_015036', 'surname unique on the held NFL|1925|CHI roster'),
 'Anderson':       ('P_014305', 'surname unique on the held NFL|1925|CHI roster'),
 'Walquist':       ('P_014862', 'surname unique on the held NFL|1925|CHI roster'),
 'Mohardt':        ('P_014857', 'surname unique on the held NFL|1925|CHI roster'),
 'Crawford':       ('P_015340', 'surname unique on the held NFL|1925|CHI roster'),
 'Smith':          ('P_002902', 'surname unique on the held NFL|1925|CHI roster'),
 'Bryan':          ('P_014356', 'surname unique on the held NFL|1925|CHI roster'),
 'Grange':         ('P_015342', 'surname unique on the held NFL|1925|CHI roster'),
 'Britton':        ('P_015339', 'surname unique on the held NFL|1925|CHI roster; the '
                                'line-up prints Briton, one t, and both spellings are held'),
 'McMillen':       ('P_015201', 'in the PROBABLE LINE-UP only, not in the printed roster. '
                                'surname unique on the held NFL|1925|CHI roster'),
}
BEARS_CLUB, BEARS_SEASON = 'CHI', '1925'

PROBABLE_LINEUP = [
 ('18 Hanny','LE / RE','Lyle 16'), ('16 Healy','LT / RT','Shipkey 7'),
 ('24 Anderson','LG / RG','McConnell 11'), ('13 Trafton (Capt.)','C','Baker 8'),
 ('22 McMillen','RG / LG','Hawkins 41'), ('18 Murry','RT / LT','Beam 4'),
 ('21 Mullen','RE / LE','Starke 40'), ('4 J. Sternaman','Q','Winterburn 29'),
 ('77 Grange','LH / RH','Wilson (Capt.) 33'), ('25 Walquist','RH / LH','Kincaid 27'),
 ('80 Briton','F','Baker 9'),
]

CONTRADICTIONS = [
 {"where": "page seven vs front spread", "club": "Los Angeles Tigers",
  "what": "PHYTHAIN on page seven, Phythian on the front spread",
  "held": "both, as printed", "resolved": False},
 {"where": "front spread, roster vs probable line-up", "club": "Chicago Bears",
  "what": "the roster gives 18 Murry and 19 Hanny; the line-up gives 18 Hanny at left end "
          "and 18 Murry at right tackle -- 18 twice and 19 nowhere",
  "held": "both, as printed", "resolved": False},
 {"where": "front spread, roster vs probable line-up", "club": "Chicago Bears",
  "what": "the roster prints 80 Britton, the line-up prints 80 Briton",
  "held": "both, as printed", "resolved": False},
 {"where": "front spread, probable line-up vs roster", "club": "Chicago Bears",
  "what": "McMillen is in the probable line-up at right guard and is not in the roster list",
  "held": "as printed; he is joined on the probable_lineup predicate only", "resolved": False},
]

REFUSALS = [{
  "refusal_id": "refuse-programme-1926-ratterman-katterman",
  "kind": "unclassifiable",
  "subject": "two printed entries in one document that may be one man or two",
  "entries": ['"TIGER" RATTERMAN, no. 28', '"TIGER" KATTERMAN, no number'],
  "identical_on": ["age 25 years", "height 6 ft. 2 in.", "weight 210 lbs.",
                   "college Georgia Tech", 'nickname "TIGER"'],
  "differing_on": ["jersey number: 28 vs none printed",
                   "position: 'Center and end' vs 'end and center'",
                   "college detail: 'Captain Bull Dogs 1920' vs 'played end and center "
                   "prior to 1919'"],
  "why_not_a_merge_decision": "neither is a held person, so there is nothing to merge. "
      "This is a question about what the document says, not about the archive.",
  "why_unresolvable_here": "both lists carry both men in two separately typeset places, "
      "but the second list is NOT independent evidence -- one compositor can repeat one "
      "error across a single programme. Either one man was typeset twice under two "
      "spellings and numbered once, or two Georgia Tech men of the same age and build "
      "played for this club and one had no jersey number.",
  "ruling": "hold both as printed. Do not merge and do not split on this document alone.",
  "what_would_settle_it": "a second, independently produced source for this club -- a "
      "newspaper line-up or a box score for the game of 16 January 1926",
}]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s.lower()).split()


def main(write=True):
    claims, leads, notes = [], [], []
    n = collections.Counter()

    def claim(sr, subj, pred, val, kind="observed", **kw):
        c = {"source_record": sr, "source_id": SOURCE["source_id"],
             "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
             "subject": subj, "predicate": pred, "value": val, "kind": kind,
             "observed_at": "photographed-2026-09"}
        c.update(kw); claims.append(c); n[pred] += 1; return c

    # ------------------------------------------------ the document, as printed
    for pred, val in (
        ("programme.title", "OFFICIAL GRID PROGRAM"),
        ("programme.date_as_printed", "JANUARY 16, 1926"),
        ("programme.venue_as_printed", "LOS ANGELES COLISEUM"),
        ("programme.matchup_as_printed", "CHICAGO BEARS -- vs -- LOS ANGELES TIGERS"),
        ("programme.publisher_imprint", "The Frank Meline Co., Sun Building, 706 So. Hill St."),
        ("programme.jersey_colours", {"Chicago Bears": "Orange and Blue Jerseys",
                                      "Los Angeles Tigers": "Blue and Gold Jerseys"}),
        ("programme.printed_note", "The Los Angeles Tigers are playing under Richfield "
            "Colors in today's game. Blue and gold uniforms for the team were furnished "
            "through the courtesy of the RICHFIELD OIL COMPANY."),
    ):
        claim(SR_FRONT, GAME, pred, val)

    # THE HAND-WRITTEN SCORE IS NOT A RESULT. A reader's mark, held as an annotation
    # on the document and attributed to an unknown hand. The quarter columns are blank.
    claim(SR_FRONT, GAME, "programme.annotation",
          {"what": "the score grid's Total column, filled in ink",
           "as_written": {"Tigers": "7", "Bears": "12"},
           "quarter_columns": "blank",
           "hand": "unknown; not the publisher's",
           "IS_NOT_A_RESULT": "this is an annotation on the document, not a source for the "
                              "score of the game. Nothing in the archive takes a result "
                              "from it."})

    # ------------------------------------------------------- the Los Angeles Tigers
    # The club enters FOR THIS GAME ONLY. No club-season, by ruling.
    claim(SR_FRONT, GAME, "programme.club_in_game",
          {"club_as_printed": "LOS ANGELES TIGERS",
           "role": "non-league professional club",
           "enters_on": "Ryan's ruling of 2026-09-07 -- a non-league professional club "
                        "enters when a club in scope played it in a documented game",
           "scope": "THIS GAME ONLY. No club-season is created, no league is asserted, "
                    "and no season of this club is held.",
           "opponent_in_scope": {"club": "Chicago Bears", "held_as": "NFL|1925|CHI"}})

    # ---- page seven: every man, every value as printed. All are LEADS.
    for no, name, age, ht, wt, col, pos in TIGERS:
        lead = {
            "lead_id": f"lead-programme-1926-{len(leads)+1:03d}",
            "category": "player_lead_unpromoted",
            "IS_NOT_A_PERSON": True,
            "name_as_printed": name,
            "jersey": no,
            "jersey_state": "observed" if no is not None else "absent",
            "places_on": {"club_as_printed": "Los Angeles Tigers", "game": GAME,
                          "club_season": None,
                          "_why_no_club_season": "the club enters for this game only"},
            "age_as_printed": age,
            "height_as_printed": ht,
            "weight_as_printed": wt,
            "college_or_prior_as_printed": col,
            "position_as_printed": pos,
            "source_id": SOURCE["source_id"], "source_record": SR_PAGE7,
            "why": "the archive holds no Los Angeles Tigers club-season and this man "
                   "resolves to no held person. Ryan's ruling on player leads stands: "
                   "parked, not promoted. The club-season join is a judgement per man "
                   "and nothing here matched on a surname.",
        }
        if age is None:
            # ABSENT, not unmeasured. The entry gives height and weight and omits age.
            lead["age_state"] = "absent"
            lead["_age_absent"] = ("the only man on the page without an age. The entry "
                                   "carries height and weight, so the page had the man's "
                                   "vitals and printed no age -- an absence, not a gap "
                                   "in what was read.")
            claim(SR_PAGE7, ["lead", lead["lead_id"]], "programme.age", None,
                  kind="absent")
        else:
            lead["age_state"] = "observed"
        if pos is None:
            lead["position_state"] = "absent"
            lead["_position_absent"] = ("this entry ends in prose where the others end "
                                        "in a bare position word. Position for this man "
                                        "must be read from the front-spread line-up and "
                                        "is NOT invented from the prose.")
        else:
            lead["position_state"] = "observed"
        if name == "CHUCK WINTERBURN":
            lead["_two_facts_not_a_contradiction"] = (
                "'Coach at Santa Ana. Plays quarterback.' He is numbered and appears in "
                "the roster list, so he is a player of this club and a coach of another. "
                "Two facts, not a contradiction.")
        if name == "GENE CORY":
            lead["_two_positions"] = ("'Captain and Tackle 1922' in the college clause, "
                                      "'Guard' as his position here. College position and "
                                      "club position differ; both stand.")
        leads.append(lead)
        n["tigers_leads"] += 1

    for name, prose in TIGERS_STAFF:
        leads.append({
            "lead_id": f"lead-programme-1926-{len(leads)+1:03d}",
            "category": "staff_lead_unpromoted", "IS_NOT_A_PERSON": True,
            "name_as_printed": name, "role_as_printed": "COACHES", "prose_as_printed": prose,
            "places_on": {"club_as_printed": "Los Angeles Tigers", "game": GAME},
            "source_id": SOURCE["source_id"], "source_record": SR_PAGE7,
            "why": "staff of a club held for one game only; resolves to no held person",
        })
        n["tigers_staff_leads"] += 1

    # ---- the front spread's Tigers roster, and the internal verification
    p7 = {(no, norm(nm)[-1]) for no, nm, *_ in
          [(t[0], t[1]) for t in TIGERS]}
    fr = {(no, norm(nm)[-1]) for no, nm in TIGERS_FRONT}
    nums7 = sorted([t[0] for t in TIGERS if t[0] is not None])
    numsf = sorted([x for x, _ in TIGERS_FRONT if x is not None])
    verified = (len(TIGERS) == len(TIGERS_FRONT) == 28 and nums7 == numsf)
    claim(SR_FRONT, GAME, "programme.internal_verification",
          {"what": "the front-spread Tigers roster against page seven",
           "page_seven_entries": len(TIGERS), "front_spread_entries": len(TIGERS_FRONT),
           "identical_number_set": nums7 == numsf,
           "unnumbered_on_both": "Katterman",
           "surnames_differing": sorted(x[1] for x in p7 - fr),
           "verified": verified,
           "_why_this_counts": "two separately typeset lists of the same 28 men in one "
               "document, counted rather than eyeballed. This is a genuine internal "
               "verification. It does NOT make the two lists independent sources -- see "
               "the Ratterman/Katterman refusal."})
    if not verified:
        raise SystemExit("front spread and page seven do not reconcile; refusing to write")

    # ---- the Bears roster: a corroborating source for a club already held
    joined = 0
    for no, printed in BEARS_FRONT:
        pid, why = BEARS_JOIN[printed]
        claim(SR_FRONT, ["stint", pid, BEARS_CLUB, BEARS_SEASON],
              "programme.roster_as_printed",
              {"name_as_printed": printed, "jersey": no,
               "club_as_printed": "CHICAGO BEARS", "club_code": BEARS_CLUB,
               "league": "NFL", "year": int(BEARS_SEASON),
               "game": GAME, "game_date_as_printed": "JANUARY 16, 1926",
               "_join_evidence": why,
               "_why_1925": "the game is 16 January 1926, inside the 1925 NFL season. "
                            "The printed roster resolves 22 of 22 on NFL|1925|CHI and 13 "
                            "of 23 on NFL|1926|CHI, where neither Grange nor Joey "
                            "Sternaman is held.",
               "_corroborating": "the Chicago Bears are already held for this season; "
                                 "this document is a second, contemporary witness to the "
                                 "roster, not a new source for the club"},
              person=pid)
        joined += 1

    # ---- the probable line-up: its own predicate, on the game, never on started_a_game
    for bears_cell, pos, tigers_cell in PROBABLE_LINEUP:
        claim(SR_FRONT, GAME, "programme.probable_lineup",
              {"chicago_bears_as_printed": bears_cell,
               "position_as_printed": pos,
               "los_angeles_tigers_as_printed": tigers_cell,
               "_definition": PREDICATE_DEFINITIONS["programme.probable_lineup"]["definition"],
               "_is_not": PREDICATE_DEFINITIONS["programme.probable_lineup"]["is_not"]})

    # McMillen: in the line-up, not in the roster. Joined on the LINE-UP only.
    claim(SR_FRONT, ["stint", BEARS_JOIN["McMillen"][0], BEARS_CLUB, BEARS_SEASON],
          "programme.probable_lineup",
          {"name_as_printed": "McMillen", "jersey": 22, "position_as_printed": "RG / LG",
           "game": GAME,
           "_join_evidence": BEARS_JOIN["McMillen"][1],
           "_not_in_the_roster": "this man is in the probable line-up and NOT in the "
                                 "printed roster list. That is the document's own "
                                 "contradiction and it is held, not resolved.",
           "_is_not": PREDICATE_DEFINITIONS["programme.probable_lineup"]["is_not"]},
          person=BEARS_JOIN["McMillen"][0])

    for c in CONTRADICTIONS:
        claim(SR_FRONT, GAME, "programme.internal_contradiction", c)

    out = {"source": SOURCE,
           # SHAPE MATTERS: the read model reads source_records as {record: {source_id,
           # locator}} and calls .get on the value. A plain description string here
           # crashed the whole read-model build with an AttributeError -- one malformed
           # store blocks every rebuild, so the description goes in its own key.
           "source_records": {
               SR_FRONT: {"source_id": SOURCE["source_id"], "locator": "front-spread",
                          "description": "front spread -- probable line-ups, both "
                                         "rosters, scoring grid, publisher's imprint"},
               SR_PAGE7: {"source_id": SOURCE["source_id"], "locator": "page-seven",
                          "description": "page seven -- TIGERS ON THE FIELD, 28 "
                                         "players and 4 staff"}},
           "game": GAME,
           "predicate_definitions": PREDICATE_DEFINITIONS,
           "claims": claims, "leads": leads, "refusals": REFUSALS,
           "counts": {"claims": len(claims), "leads": len(leads),
                      "tigers_player_leads": n["tigers_leads"],
                      "tigers_staff_leads": n["tigers_staff_leads"],
                      "bears_men_joined": joined,
                      "bears_probable_lineup_only": 1,
                      "held_people_touched": len({c["person"] for c in claims if "person" in c}),
                      "refusals": len(REFUSALS),
                      "internal_contradictions": len(CONTRADICTIONS),
                      "absent_claims": sum(1 for c in claims if c["kind"] == "absent"),
                      "by_predicate": dict(n)}}
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "programme-1926-chi-lat.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--dry" not in sys.argv)
    c = o["counts"]
    print(f"claims {c['claims']}   leads {c['leads']}   refusals {c['refusals']}")
    print(f"  Tigers: {c['tigers_player_leads']} player leads + {c['tigers_staff_leads']} staff leads, 0 people")
    print(f"  Bears : {c['bears_men_joined']} joined on NFL|1925|CHI, "
          f"+{c['bears_probable_lineup_only']} in the line-up only")
    print(f"  held people touched: {c['held_people_touched']}")
    print(f"  absent claims: {c['absent_claims']}   contradictions held: {c['internal_contradictions']}")
