"""The Fourth PFRA Annual (1983), pages 10-14: five St. Louis club-seasons.

A PUBLISHED REFERENCE WORK, USED AS ONE. Not public domain. Every claim carries the
publication and the PAGE. The pages themselves are not reproduced, and nothing here
copies prose.

LINEAGE, AND THE DISTINCTION THAT MATTERS. The PFRA is the same body whose Linescore
Committee produced the AAFC linescores in Crippen's book, so its SCHEDULES may descend
from that committee's work and are not automatically an independent voice. THE ROSTER
COLUMNS DO NOT: no committee reading box scores produces a man's age or the college he
attended. The distinction is recorded on the claims, not in a note somewhere else.

WHAT THIS INGEST DOES NOT DECIDE:
  * the 1934 asterisks. Eight starred non-league games sit beside three NFL ones in one
    season, and Pittsburgh appears TWICE, once starred and once not. The asterisk is held
    exactly as printed and this file does not say what it means.
  * St. Louis Veterans 1932. The club is not in the table and no in-scope club appears on
    its five-game schedule, so the non-league ruling's trigger is not met. Its 28 men and
    5 games are written as LEADS and refusals, never as claims.
  * a league. The 1931-33 seasons are pre-NFL independent football; no league is asserted.

  python3 src/ingest_pfra_annual_1983.py [--write]
"""
import os, re, sys, json, collections, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import clubs as ac
from readings import person_name

SRC = os.path.expanduser("~/Documents/pgm3-sources/pfra")
OUT = os.path.join(BASE, "build", "pfra-annual-4-1983.json")
REPORT = os.path.join(BASE, "build-reports", "pfra-annual-4-1983.json")
DECL = os.path.join(BASE, "declarations", "pfra-annual.json")

SOURCE = {
    "source_id": "pfra-annual-4-1983",
    "name": "Fourth PFRA Annual (1983)",
    "acquisition": "preserved",
    "stated_by": "Professional Football Researchers Association",
    "attribution": ["Fourth PFRA Annual, Professional Football Researchers Association, 1983"],
    "rights": "A PFRA publication. NOT public domain. Facts are held with the page cited "
              "under the reference-works ruling; the pages are not reproduced and no prose "
              "is copied.",
    "acquired_from": "web.archive.org snapshot 20120226105518 of "
                     "profootballresearchers.org/Coffin_Corner/05-An-167.pdf, fetched "
                     "2026-09-08; 97,654 bytes, 14 pages, "
                     "sha256 038e1e521e487205b32fede494c894dafb0bbc9598d69cf2a0d0d1443081f86d",
}

SCHEDULE_LINEAGE = (
    "The PFRA's Linescore Committee, chaired by Gary Selby, produced the AAFC linescores "
    "in Crippen's book, and Selby is one of three men Crippen names as the AAFC "
    "reconstruction team. A PFRA schedule may therefore descend from the same work and is "
    "NOT automatically an independent voice on a game record.")
ROSTER_LINEAGE = (
    "This does NOT descend from a linescore reconstruction. A committee working from box "
    "scores does not produce a man's age or the college he attended, so whatever the "
    "schedules descend from, these columns came from somewhere else.")

PREDICATES = {
    "pfra.roster_listing": {
        "definition": "named in the club's printed roster table for that season. It is not "
                      "a box-score appearance and does not say the man played; it says the "
                      "Annual's roster for this club-season lists him.",
        "is_not": "roster_membership.started_a_game, which is what the archive's own 1934 "
                  "Gunners men were derived from."},
    "pfra.position_as_printed": {"definition": "the position abbreviation as the roster prints it."},
    "pfra.age_in_season": {
        "definition": "the age the roster prints against the man for that season.",
        "is_not": "a birth date. It is an age in one season and cannot be turned into one "
                  "without knowing the date the Annual computed it from."},
    "pfra.coach_as_printed": {"definition": "the coach the page names for that club-season, verbatim."},
    "pfra.game_result": {
        "definition": "one game on the club's printed schedule: date, home or away, the two "
                      "scores, the result letter, and the opponent as printed."},
    "pfra.attendance": {"definition": "the attendance printed against one game."},
    "pfra.game_cancelled": {
        "definition": "a game printed on the schedule that was NOT played. A cancelled game "
                      "is a fact about a schedule, not a game, and carries no score."},
    "pfra.season_line": {"definition": "the season summary line as printed."},
}

PAGES = {"1931 St. Louis Gunners": 10, "1932 St. Louis Veterans": 11,
         "1932 St. Louis Gunners": 12, "1933 St. Louis Gunners": 13,
         "1934 St. Louis Gunners": 14}
# The Veterans are OUT: no in-scope club on their schedule, so the non-league ruling's
# trigger is not met and Ryan has not ruled. Leads only.
OUT_OF_SCOPE = "1932 St. Louis Veterans"
# The league position of a season key needs a TOKEN and there is no way to write an
# empty one, so the three independent seasons use IND -- the archive's declared token
# meaning "independent, no league asserted", already carrying Frankford 1922-23. It is
# not a competition and must never be read as one. The club table holds these seasons
# with an EMPTY league, which is the same fact written where an empty string is allowed.
CLUB_OF = {"1931 St. Louis Gunners": ("DOC:SLG-IND", "IND", 1931),
           "1932 St. Louis Gunners": ("DOC:SLG-IND", "IND", 1932),
           "1933 St. Louis Gunners": ("DOC:SLG-IND", "IND", 1933),
           "1934 St. Louis Gunners": ("SLG", "NFL", 1934)}

STAR = re.compile(r"\*")
DAY1 = re.compile(r"^(?P<day>\S+)\s+(?P<date>[OND]-\s?\d{1,2})\s+(?P<ha>[HA])\s+(?P<rest>.*)$")
DAY2 = re.compile(r"^(?P<mon>Sep|Oct|Nov|Dec)\s+(?P<dd>\d{1,2})\s+(?P<day>\S+)\s+(?P<ha>[HA])\s+(?P<rest>.*)$")


def parse_game(line, club):
    """Two printed layouts, one reading. Everything is also kept verbatim."""
    g = {"as_printed": line, "asterisk": bool(STAR.search(line))}
    m = DAY1.match(line)
    if m:
        g.update(day=m.group("day"), date_as_printed=m.group("date").replace(" ", ""),
                 home_away=m.group("ha"))
        rest = m.group("rest")
        mm = re.match(r"^(?P<opp>.*?)\s+(?P<a>--|\d+)-\s?(?P<b>--|\d+)\s+(?P<res>[WLT])\s*(?P<att>[\d,]*)$", rest)
        if mm:
            g.update(opponent_as_printed=mm.group("opp").strip(), score_for=mm.group("a"),
                     score_against=mm.group("b"), result=mm.group("res"),
                     attendance_as_printed=mm.group("att") or None)
        else:
            mc = re.match(r"^(?P<opp>.*?)\s+--\s*-\s*--\s+Canc\.$", rest)
            if mc:
                g.update(opponent_as_printed=mc.group("opp").strip(), cancelled=True)
        return g
    m = DAY2.match(line)
    if not m:
        return None
    g.update(day=m.group("day"), date_as_printed=f"{m.group('mon')} {m.group('dd')}",
             home_away=m.group("ha"))
    rest = m.group("rest")
    if "(can.)" in rest:
        g.update(opponent_as_printed=rest.split("(can.)")[0].strip().lstrip("-").strip(),
                 cancelled=True)
        g["opponent_as_printed"] = re.sub(r"^--\s*", "", g["opponent_as_printed"]).strip()
        return g
    mm = re.match(r"^(?P<a>_*\d+_*)\s+(?P<opp>.*?)\s+(?P<b>_*\d+_*)\s+(?P<res>[WLT])\s*(?P<att>[<_\d,]*)$", rest)
    if mm:
        g.update(score_for=mm.group("a"), opponent_as_printed=mm.group("opp").strip(),
                 score_against=mm.group("b"), result=mm.group("res"),
                 attendance_as_printed=mm.group("att") or None)
    return g



_PROM = {}


def _promoted():
    """(normalised printed name, year, club code) -> the id promote_players minted for a
    lead THIS ingest raised. Read once."""
    if _PROM: return _PROM["m"]
    m = {}
    fp = os.path.join(BASE, "build", "player-promotions.json")
    if os.path.exists(fp):
        for pr in json.load(open(fp)).get("promotions", []):
            if not str(pr.get("source", "")).startswith("pfra-annual"): continue
            nm = person_name((pr.get("identified_by") or {}).get("name_as_printed") or pr.get("name") or "")
            for ps in pr.get("playing_seasons") or []:
                m[(nm, int(ps["year"]), ps["club"])] = pr["person_id"]
    _PROM["m"] = m
    return m


def main(write=False):
    rosters = json.load(open(os.path.join(SRC, "rosters.json")))
    scheds = json.load(open(os.path.join(SRC, "schedules.json")))
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    C = ac.Clubs()
    SPAN = json.load(open(os.path.join(BASE, "declarations", "pfa-stats-join.json"))
                     )["tier_2_span_guard"]["years"]

    byname = collections.defaultdict(set); names_of = collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        k = person_name(nm)
        if k: byname[k].add(p); names_of[p].add(k)
    roster_of = collections.defaultdict(set)
    for cid, y, p in conn.execute("select club_id, year, person from claim where scope='stint' "
                                  "and club_id is not null and person is not null group by club_id, year, person"):
        roster_of[(cid, y)].add(p)
    span = {}
    for p, a, b in conn.execute("select person, min(year), max(year) from claim where scope='stint' "
                                "and person is not null and year is not null group by person"):
        span[p] = (a, b)

    claims, leads, refusals = [], [], []
    n = collections.Counter()
    srs = {}

    def sr(page, what):
        k = f"{SOURCE['source_id']}#page {page}#{what}"
        srs[k] = {"source_id": SOURCE["source_id"], "locator": f"page {page}, {what}"}
        return k

    def claim(rec, subj, pred, val, **kw):
        c = {"id": "c_%05d" % (len(claims) + 1), "source_record": rec,
             "source_id": SOURCE["source_id"], "stated_by": SOURCE["stated_by"],
             "attribution": SOURCE["attribution"], "subject": subj, "predicate": pred,
             "value": val, "kind": "observed"}
        c.update(kw); claims.append(c); n[pred] += 1; return c

    for club, page in PAGES.items():
        year = int(club[:4])
        men = rosters[club]; sch = scheds[club]
        out_of_scope = club == OUT_OF_SCOPE
        code, league, _ = CLUB_OF.get(club, (None, None, None))
        season_key = f"{league}-{year}" if not out_of_scope else None
        cid = None
        if not out_of_scope:
            r = C.resolve(code, year, None, source="pfra-annual")   # IND is not a league; resolve on the code
            cid = r[0] if r else None
        here = roster_of.get((cid, year), set()) if cid else set()

        # ---- the roster
        for m in men:
            nm = m["name"]; k = person_name(nm)
            rec = sr(page, f"roster {nm}")
            if out_of_scope:
                leads.append({"lead_id": f"lead-pfra-{year}-vet-{len(leads)+1:03d}",
                              "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                              "name_as_printed": nm, "evidence_kind": "printed_roster",
                              "places_on": {"club_as_printed": "St. Louis Veterans",
                                            "year": year, "league": None,
                                            "club_season": None},
                              "source_id": SOURCE["source_id"], "source_record": rec,
                              "why": "the club is NOT in the archive's club table and no "
                                     "in-scope club appears on its five-game schedule, so "
                                     "the non-league ruling's trigger is not met. Ryan's call."})
                n["veterans leads"] += 1
                continue
            hits = byname.get(k, set()); on_it = hits & here
            pid = how = None
            if len(on_it) == 1:
                pid, how = next(iter(on_it)), "exact name, on that club-season"
            elif len(on_it) > 1:
                n["ROWS WHOSE NAME IS ON THE CLUB-SEASON TWICE -- ambiguous"] += 1
            elif len(hits) == 1:
                cand = next(iter(hits)); sp = span.get(cand)
                if sp and sp[0] - SPAN <= year <= sp[1] + SPAN:
                    pid, how = cand, "exact name, unique in the archive"
                else:
                    n["TIER 2 REFUSED -- the one namesake is not held in this era"] += 1
            else:
                w = k.split()
                loose = [p for p in here
                         if any(x.split() and x.split()[-1] == w[-1] and x.split()[0][:1] == w[0][:1]
                                for x in names_of.get(p, ()))] if len(w) >= 2 else []
                if len(loose) == 1:
                    pid, how = loose[0], "surname and forename initial, on that club-season"
            if not pid:
                # A MAN THIS INGEST RAISED AND promote_players PROMOTED. A promoted
                # player's seasons come from the ingest's CLAIMS, so without this the
                # Annual's 58 promoted men became people holding NO SEASON -- counted by
                # apply_player_promotions as `promoted_but_holding_none`, and visible
                # rather than silent, but still a person the archive cannot place. The
                # match is the lead's own identity: the exact printed name on the exact
                # club-season, not a name join against the archive.
                pid = _promoted().get((k, year, code))
                if pid:
                    how = ("this ingest's own lead, promoted by promote_players.py under the "
                           "printed-roster ruling of 2026-09-09")
                    n["  tier: promoted from this ingest's own lead"] += 1
            if not pid:
                leads.append({"lead_id": f"lead-pfra-{year}-{len(leads)+1:03d}",
                              "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                              "name_as_printed": nm, "evidence_kind": "printed_roster",
                              "places_on": {"club_as_printed": club[5:], "club_code": code,
                                            "league": league, "year": year,
                                            "club_season": f"{league}|{year}|{code}"},
                              "source_id": SOURCE["source_id"], "source_record": rec,
                              "why": "named in the Annual's printed roster and matched nobody "
                                     "the archive holds under the ruled join discipline"})
                n["men who matched nobody -- leads"] += 1
                continue
            n[f"  tier: {how}"] += 1
            subj = ["stint", pid, code, season_key]
            claim(rec, subj, "pfra.roster_listing",
                  {"name_as_printed": nm, "club_as_printed": club[5:], "page": page,
                   "_definition": PREDICATES["pfra.roster_listing"]["definition"],
                   "_is_not": PREDICATES["pfra.roster_listing"]["is_not"],
                   "_lineage": ROSTER_LINEAGE, "_join": how})
            for fld, pred in (("pos", "pfra.position_as_printed"), ("age", "pfra.age_in_season")):
                if m.get(fld):
                    claim(rec, subj, pred, m[fld], _lineage=ROSTER_LINEAGE)
            for fld, pred in (("hgt", "height"), ("wgt", "weight"), ("college", "college")):
                v = m.get(fld)
                if v and v.lower() != "none":
                    claim(rec, ["person", pid], pred, v, _lineage=ROSTER_LINEAGE, _page=page)
                elif v and v.lower() == "none":
                    claim(rec, ["person", pid], "college", "none", kind="absent",
                          _lineage=ROSTER_LINEAGE, _page=page,
                          _note="the Annual prints `none` -- an asserted absence, not a blank")

        # ---- the coach
        for cl in sch["coach_lines"]:
            if out_of_scope:
                refusals.append({"what": cl, "why": "St. Louis Veterans 1932 is not a club the "
                                                    "table holds; no claim written"})
                continue
            claim(sr(page, "coach"), ["club_season", league, str(year), code],
                  "pfra.coach_as_printed", cl,
                  _definition=PREDICATES["pfra.coach_as_printed"]["definition"])

        # ---- the schedule
        for line in sch["games_as_printed"]:
            g = parse_game(line, club)
            if not g:
                refusals.append({"what": line, "why": "schedule line did not parse; NOT written"})
                n["schedule lines that did not parse"] += 1
                continue
            opp = g.get("opponent_as_printed")
            res = C.resolve(opp, year, None, source="pfra-annual") if opp else None
            g["opponent_club_id"] = res[0] if res else None
            g["opponent_in_the_archive"] = bool(res)
            if out_of_scope:
                refusals.append({"what": line, "why": "St. Louis Veterans 1932: no claim written"})
                continue
            rec = sr(page, f"schedule {g.get('date_as_printed')} {opp}")
            gsubj = ["game", league or "IND", str(year), f"{year}-{code}-{re.sub(r'[^a-z0-9]+','-',(opp or '').lower()).strip('-')}"]
            if g.get("cancelled"):
                claim(rec, gsubj, "pfra.game_cancelled",
                      {**g, "_definition": PREDICATES["pfra.game_cancelled"]["definition"],
                       "_lineage": SCHEDULE_LINEAGE})
                n["cancelled games"] += 1
                continue
            claim(rec, gsubj, "pfra.game_result",
                  {**g, "_definition": PREDICATES["pfra.game_result"]["definition"],
                   "_lineage": SCHEDULE_LINEAGE,
                   "_asterisk_as_printed": g["asterisk"],
                   "_the_asterisk_is_not_interpreted":
                       "held exactly as printed. Eight starred games sit beside three NFL "
                       "ones in 1934 and Pittsburgh appears twice, once starred and once "
                       "not. What it means is open and is Ryan's."})
            if g.get("attendance_as_printed"):
                claim(rec, gsubj, "pfra.attendance", g["attendance_as_printed"],
                      _lineage=SCHEDULE_LINEAGE,
                      _definition=PREDICATES["pfra.attendance"]["definition"])
                n["attendance figures"] += 1
        if sch.get("season_line") and not out_of_scope:
            claim(sr(page, "season line"), ["club_season", league, str(year), code],
                  "pfra.season_line", sch["season_line"], _lineage=SCHEDULE_LINEAGE)

    out = {"source": SOURCE, "source_records": srs, "predicate_definitions": PREDICATES,
           "claims": claims, "leads": leads, "refusals": refusals,
           "counts": dict(n) | {"claims": len(claims), "leads": len(leads),
                                "refusals": len(refusals)}}
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        json.dump({"counts": out["counts"], "leads": leads, "refusals": refusals},
                  open(REPORT, "w"), indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for k, v in sorted(o["counts"].items(), key=lambda x: -x[1] if isinstance(x[1], int) else 0):
        print(f"   {str(v):>7} {k}")
