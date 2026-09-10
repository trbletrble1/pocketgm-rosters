"""The seventeen Ghosts game line-ups, plus the officials, the honours and the limit.

RYAN'S RULING, 2026-09-10. The first sweep of these 243 pages asked "which pages are
rosters" and answered correctly. What it never asked is whether a page can place men on
a club-season WITHOUT being a roster. A game account has no squad, no numbers and no
college column, and it still names eleven men a club with their positions.

  started_a_game, NOT a probable line-up. The 1926 Bears-Tigers programme printed its
    line-up BEFORE kickoff, which is why programme.probable_lineup exists: a man named
    there was expected to start and might not have. These are GAME ACCOUNTS, printed
    after the final whistle in the Bethlehem Globe-Times and the Philadelphia Public
    Ledger. A man named in one STARTED. The claim says which it is and why.

  A SUBSTITUTION IS A DIFFERENT ASSERTION and is not folded into the elevens: a man who
    came on did NOT start. `ghosts.substitution` carries who replaced whom.

  OFFICIALS ARE PEOPLE, under the standing rule of 2026-09-08 -- the line is on-field
    game participants. The affiliation is taken AS PRINTED (`Wheeler, Haverford`),
    because it is the source's own words and this ingest does not know what Haverford
    is to Wheeler.

  THE EASTERN LEAGUE STAYS EXCLUDED. Bethlehem Bears and Gilberton Catamounts are in
    the club table already, under EFL, holding nobody. Naming men on a club the table
    holds is not admitting the league, and no club is created here.

  CLUBS NOT IN THE TABLE STAY OUT AND ARE REPORTED, not minted: All-Lancaster,
    Shenandoah, Holmesburg A.C., Conshohocken A.C., Parkside A.C., Bridesburg,
    New York Shipyard, Hog Island, USS Michigan, Washington Pros. Some are athletic
    clubs and some are service teams and those are different questions.

  THE PHOTOGRAPH IS NOT TAKEN. Bethlehem_Gooch.htm is credited "Image courtesy, Beth
    Campanella" -- a named private lender is not a licence. Recorded as a refusal so a
    later reader can see it was seen and declined.

CITATION. The newspaper where the page names one, Fenton as the FINDING AID rather than
the source of the fact, and the Wayback snapshot address with its sha256.

  python3 src/ingest_ghosts_lineups.py            read and report
  python3 src/ingest_ghosts_lineups.py --write    write build/ghosts-lineups.json
"""
import os, re, sys, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import index_io as IO
import clubs as ac

M = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron")
MAN = json.load(open(os.path.join(M, "manifest.json")))
MEASURE = os.path.join(BASE, "build-reports", "ghosts-lineups.json")
DECL = json.load(open(os.path.join(BASE, "declarations", "ghosts-lineups.json")))
SRC_ID = DECL["source_id"]

# THE TWO CLUBS THE TABLE ALREADY HOLDS. Resolved through Clubs(), never typed as an id:
# an ingest that invents a club code resolves to nothing and no gate catches it.
TABLE_CLUBS = {"Bethlehem": ("Bethlehem Bears", 1926),
               "Gilberton": ("Gilberton Catamounts", 1926)}
NEWSPAPER = re.compile(r"(Bethlehem\s+Globe-Times|Public\s+Ledger|Evening\s+Bulletin|"
                       r"Philadelphia\s+Inquirer|Morning\s+Call|Reading\s+Eagle)", re.I)


def snap(page):
    for v in MAN["files"].values():
        if not v.get("absent") and v.get("path", "").endswith("/" + page):
            return v
    raise SystemExit(f"{page}: not in the preservation manifest")


def text_of(page):
    v = snap(page)
    t = open(os.path.join(M, v["path"]), errors="replace").read()
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"</t[dhr]>", " | ", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return v, re.sub(r"\s+", " ", t)


_PROM = {}


def promoted():
    """(name, year, club code) -> person id, for the men promoted from THIS ingest's own
    leads.

    THE ROUTE'S OWN CAUTION, AGAIN. A promoted man's seasons come from the INGEST'S
    claims, so on the first run apply_player_promotions reported
    `promoted_but_holding_none: 25` -- twenty-five people admitted holding no season at
    all. An ingest that raises a lead must run again once the lead is promoted. This is
    the third store to learn it, which is why it is written down here rather than
    remembered."""
    if _PROM: return _PROM["m"]
    m = {}
    fp = os.path.join(BASE, "build", "player-promotions.json")
    if os.path.exists(fp):
        for pr in json.load(open(fp)).get("promotions", []):
            if not str(pr.get("source", "")).startswith("ghosts-lineups"): continue
            nm = (pr.get("identified_by") or {}).get("name_as_printed") or pr.get("name")
            for ps in pr.get("playing_seasons") or []:
                m[(str(nm).strip().lower(), int(ps["year"]), ps["club"])] = pr["person_id"]
    _PROM["m"] = m
    return m


def season_key(C, club_id, year):
    """`EFL|1926|PFA:BET` -- the shape promote_players reads, built from the CLUB TABLE's
    own code and league rather than typed. A code typed here would resolve to nothing and
    no gate would catch it."""
    for c in C.T["clubs"]:
        if c["id"] != club_id: continue
        for s in c["segments"]:
            for lg in s["leagues"]:
                if (lg.get("first") or 0) <= year <= (lg.get("last") or 9999):
                    return f"{lg.get('league')}|{year}|{s.get('code')}"
    return None


def club_of(page, side, C):
    """-> (club_id, printed) for a club the TABLE holds, else (None, printed).

    THE MAP IS DECLARED, NOT DERIVED, and declarations/ghosts-lineups.json says why: a
    reader that took the two capitalised strings before the first position picked up the
    first PLAYER as the second club on sixteen of seventeen pages. The club id is still
    resolved through Clubs() rather than typed, so a club that leaves the table takes
    this ingest with it."""
    spec = (DECL.get("side_to_club") or {}).get(page)
    if not spec: return None, page
    full = spec.get(side)
    if not full:
        return None, spec.get(f"{side}_as_printed") or page
    for c in C.T["clubs"]:
        for nm in c.get("names", []):
            if (nm.get("name") or "").lower() == full.lower():
                return c["id"], full
    raise SystemExit(f"{full}: declared for {page} but the club table does not hold it")


def main(write=True):
    meas = json.load(open(MEASURE))
    games, honours = meas["games"], meas["honours"]
    C = ac.Clubs()
    claims, leads, refusals, srecs = [], [], [], {}
    n = collections.Counter()
    outside = collections.Counter()

    def cite(page, v, extra=None):
        sr = f"{SRC_ID}#{page}@{v['timestamp']}"
        srecs[sr] = {"source_id": SRC_ID, "locator": v["wayback_url"],
                     "sha256": v["sha256"], "captured": v["timestamp"], "page": page}
        c = {"source_id": SRC_ID, "source_record": sr, "stated_by": DECL["stated_by"],
             "attribution": list(DECL["attribution"]), "kind": "observed",
             "observed_at": "preserved-2026-09",
             "finding_aid": {"who": "John J. Fenton, Ghosts of the Gridiron",
                             "_is_not_the_source_of_the_fact":
                                 "Fenton reproduces a newspaper account. The fact is the "
                                 "newspaper's; Fenton is how the archive found it."},
             "snapshot": v["wayback_url"]}
        if extra: c.update(extra)
        return c

    for g in games:
        page = g["page"]
        v, t = text_of(page)
        paper = NEWSPAPER.search(t)
        paper = paper.group(1) if paper else None
        year = int(re.search(r"(19\d\d)", page).group(1)) if re.search(r"(19\d\d)", page) else None
        base = dict(printed_in=paper, _the_account_is_after_the_game=True)

        for side, men in (("away", g["away_men"]), ("home", g["home_men"])):
            cid, printed = club_of(page, side, C)
            for pos, man in zip(g["positions"], men):
                if not man: continue
                if cid is None:
                    outside[printed if isinstance(printed, str) else page] += 1
                    continue
                key = season_key(C, cid, year)
                if not key:
                    n["no_season_key"] += 1; continue
                code = key.split("|")[-1]
                pid = promoted().get((man.strip().lower(), year, code))
                if pid:
                    # THE CLAIM THE WHOLE PASS IS FOR. started_a_game, not a probable
                    # line-up, and the value says why in the archive rather than only in
                    # a declaration nobody will be reading at the time.
                    claims.append({**cite(page, v, base),
                                   "subject": ["person", pid],
                                   "predicate": "roster_membership.started_a_game",
                                   "value": f"{key.split('|')[0]}|{year}|{code}",
                                   "extra": {
                                       "name_as_printed": man,
                                       "position_as_printed": pos,
                                       "club_as_printed": printed,
                                       "printed_in": paper,
                                       "_why_started_and_not_probable":
                                           "this is a GAME ACCOUNT printed after the "
                                           "whistle, not a programme printed before it. "
                                           "A man named in the line-up of an account "
                                           "started; a man named in a programme was "
                                           "expected to."}})
                    n["started_a_game"] += 1
                    # AND THE CLAIM THAT ACTUALLY PLACES HIM. The one above says he
                    # STARTED; it does not say he was on the club-season, and nothing
                    # downstream reads it as though it did.
                    #
                    # build_person_index writes a season into a man's record ONLY from a
                    # ["stint", person, club, season_key] subject. A person-subject claim
                    # carrying the season key in its VALUE produces no season at all, so
                    # the 25 men promoted here held `seasons: []` and Bethlehem Bears 1926
                    # stayed at rank 2 of the hunting list marked EMPTY -- after being
                    # filled. apply_player_promotions said `promoted_but_holding_none: 25`
                    # and re-running this ingest was not the fix, because what it re-wrote
                    # placed nobody.
                    #
                    # It matched existing practice and that is why it was easy to miss:
                    # pfa-boxscore-membership writes 11,776 started_a_game claims with no
                    # stint subject either. It works there because those men are ALREADY
                    # placed by other stores. It cannot work for a new person on an empty
                    # club-season, which is the only case this ingest has.
                    claims.append({**cite(page, v, base),
                                   "subject": ["stint", pid, code, f"{key.split('|')[0]}-{year}"],
                                   "predicate": "ghosts.lineup_membership",
                                   "value": {"club_as_printed": printed,
                                             "name_as_printed": man,
                                             "position_as_printed": pos,
                                             "printed_in": paper,
                                             "_what_this_asserts":
                                                 "that this man was on this club-season, "
                                                 "because a newspaper printed him in its "
                                                 "starting eleven. The companion "
                                                 "roster_membership.started_a_game claim "
                                                 "says he STARTED; this one places him."}})
                    n["lineup_membership"] += 1
                    continue
                leads.append({
                    "lead_id": f"lead-ghostslu-{len(leads)+1:05d}",
                    "category": "player_lead_unpromoted",
                    "IS_NOT_A_PERSON": True,
                    "evidence_kind": "printed_lineup",
                    "name_as_printed": man,
                    "position_as_printed": pos,
                    "places_on": {"club_season": key, "club_id": cid, "year": year,
                                  "club_as_printed": printed},
                    "source_record": f"{SRC_ID}#{page}@{v['timestamp']}",
                    "printed_in": paper,
                    "why": "named in a starting line-up printed in a game account",
                })
                n["started_a_game_lead"] += 1

        for s in g["substitutions"]:
            m = re.match(r"(.+?)\s+fo[er]\s+(.+)", s, re.I)
            if not m: n["substitution_unparsed"] += 1; continue
            claims.append({**cite(page, v, base),
                           "subject": ["document", page],
                           "predicate": "ghosts.substitution",
                           "value": {"came_on_as_printed": m.group(1).strip(),
                                     "replaced_as_printed": m.group(2).strip(),
                                     "year": year,
                                     "_a_substitute_did_NOT_start":
                                         "held apart from the eleven deliberately: a man "
                                         "who came on is not a man who started."}})
            n["substitution"] += 1

        for role, who in g["officials"]:
            name, _, aff = who.partition(",")
            claims.append({**cite(page, v, base),
                           "subject": ["document", page],
                           "predicate": "ghosts.game_official",
                           "value": {"name_as_printed": name.strip(),
                                     "affiliation_as_printed": aff.strip() or None,
                                     "role_as_printed": role, "year": year,
                                     "_affiliation_is_as_printed":
                                         "the source's own words; this ingest does not "
                                         "know what the affiliation is to the man."}})
            n["game_official"] += 1

    # ---- the Eastern League roster limit
    v, t = text_of("Bethlehem_Shenandoah_1926.htm")
    m = re.search(r"[^.]*complete Bethlehem squad[^.]*\.", t)
    if m:
        claims.append({**cite("Bethlehem_Shenandoah_1926.htm", v),
                       "subject": ["league_season", "EFL", 1926],
                       "predicate": "ghosts.roster_limit_as_printed",
                       "value": {"limit": 20, "as_printed": m.group(0).strip(),
                                 "league_as_printed": "the league",
                                 "_every_other_roster_limit_here_is_NFL":
                                     "the archive holds pfa.roster_limit.* and every one "
                                     "is the NFL. This is an Eastern League limit stated "
                                     "by a 1926 newspaper.",
                                 "_the_league_is_still_excluded":
                                     "a limit stated for a league is not the league being "
                                     "admitted."}})
        n["roster_limit"] += 1

    # ---- the photograph, refused
    vg = snap("Bethlehem_Gooch.htm")
    refusals.append({"page": "Bethlehem_Gooch.htm", "what": "photograph",
                     "image": "pic_Gooch_2.jpg",
                     "subject_as_printed": 'Carroll "Ginny" Gooch, Bethlehem Bears, 1926',
                     "credit_as_printed": "Image courtesy, Beth Campanella",
                     "why_refused": "a named private lender is not a licence. The caption's "
                                    "FACTS may be read and cited; the image is not "
                                    "reproduced. Same route as every photograph here.",
                     "snapshot": vg["wayback_url"]})
    n["photograph_refused"] += 1

    out = {"_what": DECL["_what"],
           "source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "attribution": list(DECL["attribution"]),
                      "acquisition": "preserved", "rights": DECL["rights"]},
           "source_records": srecs, "claims": claims, "leads": leads,
           "refusals": refusals,
           "clubs_not_in_the_table": dict(outside),
           "counts": dict(n)}
    print(f"GHOSTS LINE-UPS   ({'WRITE' if write else 'dry run'})")
    for k, x in sorted(n.items()): print(f"  {k:<28} {x:>6,}")
    print(f"  {'claims':<28} {len(claims):>6,}")
    print(f"  {'leads':<28} {len(leads):>6,}")
    print(f"  clubs not in the table: {sum(outside.values()):,} men across {len(outside)} pages")
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "ghosts-lineups.json"))
        print("  -> build/ghosts-lineups.json")
    return out


if __name__ == "__main__":
    main(write="--write" in sys.argv)
