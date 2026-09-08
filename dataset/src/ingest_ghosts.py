"""Ghosts of the Gridiron: John J. Fenton's rosters, cited two ways. Facts only.

RYAN'S RULING, 2026-09-07. Recording that Frankford's 1922 roster contained these
men -- cited to Fenton, and to the newspaper he names where he names one -- is
ordinary scholarly use, the same position the archive already takes on Crippen's
book. It is not republication. **Facts are not his to withhold; his prose, his
selection and his photography are.** So: rosters ingested, 1,752 scans preserved
and held pending permission, none published, and none of his sentences copied
into a claim.

CITED TWO WAYS. Where he names a paper attached to a fact, the paper is the
source and Fenton is the finding aid. **No roster page names one** -- checked,
page by page -- so every roster claim here records `underlying_source: unstated`
as a STATED ABSENCE. It does NOT reach for the twenty-one newspapers on his
sources page: that list describes the site and describes no page in it, and
attributing a roster to it would manufacture a citation he never made.

EVERY CLAIM CITES THE SNAPSHOT. The live site is dead. A source record names
`web.archive.org/web/<timestamp>id_/<url>`, which is a thing that can be fetched,
rather than a URL that 404s.

  python3 src/ingest_ghosts.py [--dry]
"""
import os, re, sys, json, html, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
from readings import READERS

# PROMOTED PLAYERS, by name. A man promoted from a lead has an id and no claims; the
# claims are written here, which is what builds his seasons. Read from the decision
# store so the id is the decision's, never minted twice.
def _promoted():
    p = os.path.join(BASE, "build", "player-promotions.json")
    if not os.path.exists(p): return {}
    import unicodedata as _u, re as _re
    def _n(x):
        x = _u.normalize("NFKD", str(x)); x = "".join(c for c in x if not _u.combining(c))
        return " ".join(_re.sub(r"[^a-z ]", " ", x.lower()).split())
    return {_n(q["name"]): q["person_id"] for q in json.load(open(p))["promotions"]}


PROMOTED = _promoted()
READ = READERS["college"]

MIRROR = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron")
MANIFEST = json.load(open(os.path.join(MIRROR, "manifest.json")))

SOURCE = {
    "source_id": "ghostsofthegridiron",
    "name": "Ghosts of the Gridiron (John J. Fenton), preserved from the Wayback Machine",
    "acquisition": "preserved",
    "stated_by": "John J. Fenton",
    "attribution": ["Ghosts of the Gridiron, John J. Fenton, 2004-2008"],
    "rights": "copyrighted personal website by a named living author. FACTS INGESTED AND "
              "CITED; prose not reproduced; 1,752 images preserved and HELD PENDING "
              "PERMISSION, none published.",
    "acquired_from": "web.archive.org, 2026-09-07/08; 2,172 files, 150 MB, every one "
                     "verified by sha256. Original host home.comcast.net/~ghostsofthegridiron, dead.",
    "ranking": "NOT downstream of Neft. Fenton worked from twenty-one newspapers on "
               "microfilm at the Free Library of Philadelphia, the Historical Society of "
               "Frankford's collection of Yellow Jackets game programmes, and private "
               "manuscript scrapbooks. Total Football (Carroll/Gershman/Neft/Thorn) is "
               "one of fourteen books he lists, not his spine. A disagreement between "
               "this source and StatsCrew or PFA is therefore a REAL disagreement, and "
               "the first the 1920s record has had.",
    "known_traps": {
        "rosters_cite_nothing": "his prose names papers against facts; his roster pages "
                                "name no source at all. Recorded as unstated, never "
                                "attributed to his global list.",
        "printed_errors_are_held": "`West Viginia`, `BillColeman` with no space, `?` for "
                                   "an unknown college. Held as printed.",
    },
}

# page -> club-season. None means the archive holds no club-season for it.
PAGES = {
 # Created 2026-09-08 under the non-league ruling: a professional club a document
 # establishes, entering AS ITSELF. No league is asserted -- the club table carries it
 # with an empty league, as it already does for six PFA independents -- and its lineage
 # to the NFL club from 1924 is UNKNOWN and recorded as an unresolved candidate.
 "Yellowjackets_1922_roster.htm": (("IND","1922","DOC:FYJ-IND"), "Frankford Yellow Jackets", 1922,
                                   "independent, pre-NFL: Frankford joined the NFL in 1924"),
 "Yellowjackets_1923_roster.htm": (("IND","1923","DOC:FYJ-IND"), "Frankford Yellow Jackets", 1923,
                                   "independent, pre-NFL: Frankford joined the NFL in 1924"),
 "Yellowjackets_1924_roster.htm": (("NFL","1924","FYJ"), "Frankford Yellow Jackets", 1924, None),
 "Yellowjackets_1925_roster.htm": (("NFL","1925","FYJ"), "Frankford Yellow Jackets", 1925, None),
 "Yellowjackets_1926_roster.htm": (("NFL","1926","FYJ"), "Frankford Yellow Jackets", 1926, None),
 "Yellowjackets_1927_roster.htm": (("NFL","1927","FYJ"), "Frankford Yellow Jackets", 1927, None),
 "Yellowjackets_1928_roster.htm": (("NFL","1928","FYJ"), "Frankford Yellow Jackets", 1928, None),
 "Yellowjackets_1929_roster.htm": (("NFL","1929","FYJ"), "Frankford Yellow Jackets", 1929, None),
 "Yellowjackets_1930_roster.htm": (("NFL","1930","FYJ"), "Frankford Yellow Jackets", 1930, None),
 "Yellowjackets_1931_roster.htm": (("NFL","1931","FYJ"), "Frankford Yellow Jackets", 1931, None),
 "Maroons_1925_roster.htm": (("NFL","1925","POT"), "Pottsville Maroons", 1925, None),
 "Maroons_1926_roster.htm": (("NFL","1926","POT"), "Pottsville Maroons", 1926, None),
 "Maroons_1927_roster.htm": (("NFL","1927","POT"), "Pottsville Maroons", 1927, None),
 "Maroons_1928_roster.htm": (("NFL","1928","POT"), "Pottsville Maroons", 1928, None),
 # NOT Pottsville. The page's own title is `Boston Bulldogs 1929 NFL Team Roster` --
 # the franchise moved for 1929, and the archive holds NFL|1929|BO2 with 22 men. This
 # file was twice reported as a Pottsville club-season the archive held nothing for,
 # on the strength of its FILENAME. It is corroboration, not a gap.
 "Maroons_1929_roster.htm": (("NFL","1929","BO2"), "Boston Bulldogs", 1929, None),
 "Quakers_1926_roster.htm": (("AFL","1926","AFLPHI"), "Philadelphia Quakers", 1926, None),
}


def text_cells(tr):
    out = []
    for c in re.findall(r"(?is)<t[dh].*?</t[dh]>", tr):
        v = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
        if v: out.append(v)
    return out


def read_roster(path):
    """Name, position(s), college -- exactly as printed. Never normalised."""
    t = open(path, errors="replace").read()
    head, men, cols = None, [], None
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        rows = [text_cells(tr) for tr in re.findall(r"(?is)<tr.*?</tr>", tb)]
        rows = [r for r in rows if r]
        if len(rows) < 4: continue
        for r in rows:
            low = r[0].lower()
            if len(r) == 1 and low.startswith("head coach"):
                head = r[0][len("head coach"):].strip() or None
            elif r[0].lower() in ("player",):
                cols = r
            elif len(r) >= 2 and "roster" not in low and not low.startswith("head coach"):
                men.append(r)
        if men: break
    return head, cols, men


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def main(write=True):
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    IDX.pop("_clubs", None)
    claims, leads, srecs, disagree, unjoined = [], [], {}, [], []
    n = collections.Counter()

    def snapshot(page):
        for url, v in MANIFEST["files"].items():
            if v.get("absent"): continue
            if v["path"].endswith("/" + page) or v["path"] == "mirror/" + page:
                return v
        raise SystemExit(f"{page}: not in the preservation manifest")

    for page, (key, club_printed, year, why_no_season) in sorted(PAGES.items()):
        snap = snapshot(page)
        sr = f"{SOURCE['source_id']}#{page}@{snap['timestamp']}"
        srecs[sr] = {"source_id": SOURCE["source_id"], "locator": snap["wayback_url"],
                     "description": f"{club_printed} {year} roster, as Fenton prints it",
                     "sha256": snap["sha256"], "captured": snap["timestamp"]}
        head, cols, men = read_roster(os.path.join(MIRROR, snap["path"]))
        n["pages"] += 1; n["men_read"] += len(men)

        # A BRAND-NEW CLUB-SEASON HAS NO COHORT TO JOIN AGAINST. Frankford 1922 and 1923
        # were created from this document, so nobody is on them yet and the usual
        # club-season-scoped join returns nothing. For those two only, the join is against
        # the WHOLE archive on an exact full name -- which is weaker, and every claim says
        # so. A surname alone is never enough and an ambiguous name is refused.
        archive_wide = key and key[0] == "IND"
        cohort = {}
        if archive_wide:
            for pid, p_ in IDX.items():
                if not isinstance(p_, dict) or not p_.get("name"): continue
                cohort.setdefault(norm(p_["name"]), []).append((pid, p_))
        elif key:
            for pid, p in IDX.items():
                if not isinstance(p, dict) or not p.get("name"): continue
                if any(k.startswith("|".join(key)) for k in (p.get("seasons") or {})):
                    cohort.setdefault(norm(p["name"]).split()[-1], []).append((pid, p))

        for row in men:
            name = row[0]
            pos = row[1] if len(row) > 1 else None
            col = row[2] if len(row) > 2 else None
            val = {"name_as_printed": name,
                   "position_as_printed": pos,
                   "college_as_printed": col,
                   "club_as_printed": club_printed, "year": year,
                   "head_coach_as_printed": head,
                   # THE CITATION, BOTH WAYS. No roster page names a paper, so the
                   # underlying source is recorded as ABSENT, not guessed.
                   "underlying_source": "unstated",
                   "_underlying_source_note":
                       "Fenton names no newspaper on this page. His sources page lists "
                       "twenty-one, but that list describes the site and describes no "
                       "page in it; attributing this roster to it would manufacture a "
                       "citation he never made.",
                   "finding_aid": {"who": "John J. Fenton, Ghosts of the Gridiron",
                                   "snapshot": snap["wayback_url"],
                                   "captured": snap["timestamp"]},
                   "_values_as_printed": "position and college exactly as the page sets "
                                         "them, including typos and `?` for unknown"}
            promoted_id = PROMOTED.get(norm(name)) if key else None
            cand = (cohort.get(norm(name), []) if archive_wide
                    else (cohort.get(norm(name).split()[-1], []) if cohort else []))
            exact = [c for c in cand if norm(c[1]["name"]) == norm(name)]
            pick = exact[0] if len(exact) == 1 else (cand[0] if len(cand) == 1 else None)
            if pick:
                pid, p = pick
                if archive_wide:
                    fyj = [k for k in (p.get("seasons") or {}) if "|FYJ" in k]
                    val["_join_evidence"] = (
                        "exact full name, unique in the whole archive, AND this man holds a "
                        f"Frankford NFL season ({', '.join(sorted(fyj))}) -- the strongest "
                        "form available for a club-season with no cohort" if fyj else
                        "exact full name, unique in the whole archive. WEAKER than a "
                        "club-season-scoped join: no held season places this man at "
                        "Frankford, and the club-season is new, so there was no cohort to "
                        "check him against.")
                    val["_join_is_archive_wide"] = True
                else:
                    val["_join_evidence"] = ("exact name on the club-season" if exact
                                             else "surname unique on the club-season")
                claims.append({"source_record": sr, "source_id": SOURCE["source_id"],
                               "stated_by": SOURCE["stated_by"],
                               "attribution": SOURCE["attribution"],
                               "subject": ["stint", pid, key[2], key[1]],
                               "predicate": "ghosts.roster_as_printed", "value": val,
                               "kind": "observed", "observed_at": "preserved-2026-09",
                               "person": pid})
                n["joined"] += 1
                # THE COLLEGE IS ITS OWN CLAIM. Inside a value dict it is invisible to the
                # college family, so a disagreement with PFA could never be recorded as one.
                if col and col != "?":
                    claims.append({"source_record": sr, "source_id": SOURCE["source_id"],
                        "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
                        "subject": ["person", pid], "predicate": "ghosts.college",
                        "value": col, "kind": "observed",
                        "observed_at": "preserved-2026-09", "person": pid,
                        "underlying_source": "unstated",
                        "finding_aid": {"who": "John J. Fenton, Ghosts of the Gridiron",
                                        "snapshot": snap["wayback_url"]}})
                    n["college_claims"] += 1
                # ---- THE DISAGREEMENT REPORT: the point of a non-Neft source
                per = p.get("person") or {}
                heldc = [x for x in (per.get("college") or []) if str(x).strip().lower() not in ("none","")]
                if col and heldc and col != "?":
                    # COMPARE ON THE DECLARED READING, NOT THE LITERAL. `Penn State` and
                    # `Penn St.` are one school and the archive says so in
                    # service/declarations/predicate-families.json. A first version of
                    # this compared lowercased strings and reported 109 disagreements,
                    # 42 of which were the reading's job.
                    fr = READ(col); hr = {READ(x) for x in heldc}
                    if fr is not None and fr not in hr:
                        multi = bool(re.search(r"[;,/]| and ", col))
                        one, others = fr.split(), [h for h in hr if h]
                        prefixy = any(h and (h.startswith(one[0]) or one[0].startswith(h.split()[0]))
                                      for h in others)
                        shape = ("Fenton names MORE THAN ONE college -- an addition, not a conflict"
                                 if multi else
                                 "one string abbreviates the other and the declared reading does "
                                 "not cover it -- a READING GAP, not a disagreement about the man"
                                 if prefixy else
                                 "two different schools -- a REAL disagreement")
                        disagree.append({"person": pid, "held_as": p["name"], "field": "college",
                                         "club_season": "|".join(key),
                                         "fenton": col, "archive": heldc,
                                         "fenton_reads_as": fr, "archive_reads_as": sorted(hr),
                                         "shape": shape, "source_record": sr})
            elif promoted_id:
                val["_join_evidence"] = ("promoted from a lead: no held person carried this "
                                         "name, and a roster places him on a club-season "
                                         "the archive holds. See build/player-promotions.json")
                val["_entered_by"] = "promotion_from_lead"
                claims.append({"source_record": sr, "source_id": SOURCE["source_id"],
                               "stated_by": SOURCE["stated_by"],
                               "attribution": SOURCE["attribution"],
                               "subject": ["stint", promoted_id, key[2], key[1]],
                               "predicate": "ghosts.roster_as_printed", "value": val,
                               "kind": "observed", "observed_at": "preserved-2026-09",
                               "person": promoted_id})
                n["promoted_joined"] += 1
            else:
                leads.append({"lead_id": f"lead-ghosts-{len(leads)+1:04d}",
                              "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                              "name_as_printed": name, "roster_line": val,
                              "places_on": {"club_as_printed": club_printed, "year": year,
                                            "club_season": "|".join(key) if key else None,
                                            "_why_no_club_season": why_no_season},
                              "source_id": SOURCE["source_id"], "source_record": sr,
                              "why": ("the archive holds no club-season for this club and "
                                      "year at all" if not key else
                                      ("ambiguous: more than one held man shares this surname"
                                       if len(cand) > 1 else
                                       "not held on this club-season"))})
                n["leads"] += 1
                if key: unjoined.append({"club_season": "|".join(key), "name": name,
                                         "candidates": [c[1]["name"] for c in cand]})

    # ---- THE 1926 EASTERN LEAGUE: a HELD SOURCE DOCUMENT, and nothing else.
    # Ryan's ruling 2026-09-07: a record of clubs, seasons or results may be registered
    # as a source document -- searchable and citable -- without creating club-seasons.
    # NOTHING DERIVES FROM IT. Its subject is the DOCUMENT, never a club and never a
    # person, so no join can reach it and no count can pick it up. If a Gilberton roster
    # ever turns up the club is created then, on the roster, and this is waiting.
    bsnap = snapshot("Bethlehem.htm")
    bsr = f"{SOURCE['source_id']}#Bethlehem.htm@{bsnap['timestamp']}"
    srecs[bsr] = {"source_id": SOURCE["source_id"], "locator": bsnap["wayback_url"],
                  "description": "Bethlehem Bears 1926 -- the Eastern League of "
                                 "Professional Football, held as a document",
                  "sha256": bsnap["sha256"], "captured": bsnap["timestamp"]}
    held_doc = {
      "document": bsr,
      "about": "the Eastern League of Professional Football, 1926",
      "IS_NOT_A_CLUB_TABLE": "This is a document the archive holds. It creates no club, "
          "no club-season and no person, and nothing derives from it. A held document "
          "that starts answering 'which clubs existed in 1926' is a club table by "
          "another name, reached by a route with none of the club table's gates on it. "
          "IT MUST STAY INERT.",
      "why_held_and_not_admitted": "Fenton calls the ELF 'a regional minor league' in his "
          "own words, so the minor-league exclusion governs its season. The evidence is "
          "real and the scope decision is unchanged; holding the document keeps both.",
      "standings_as_printed": [
        {"club":"Bethlehem Bears","W":6,"L":2,"T":2,"Pct":".750","PF":72,"PA":45},
        {"club":"Gilberton Catamounts","W":5,"L":2,"T":2,"Pct":".714","PF":51,"PA":22},
        {"club":"All-Lancaster Red Roses","W":5,"L":2,"T":3,"Pct":".714","PF":49,"PA":49,
         "note":"Awarded league championship"},
        {"club":"Mount Carmel Wolverines","W":5,"L":3,"T":1,"Pct":".625","PF":91,"PA":43},
        {"club":"Coaldale Big Green","W":4,"L":4,"T":3,"Pct":".500","PF":63,"PA":43},
        {"club":"Atlantic City Roses","W":2,"L":4,"T":2,"Pct":".333","PF":22,"PA":65},
        {"club":"Shenandoah Red Jackets","W":2,"L":5,"T":1,"Pct":".286","PF":55,"PA":41},
        {"club":"Mount Airy AA","W":1,"L":3,"T":1,"Pct":".250","PF":13,"PA":67},
        {"club":"Newark Blues","W":1,"L":6,"T":0,"Pct":".142","PF":7,"PA":58},
        {"club":"Clifton Heights Black & Orange","W":1,"L":1,"T":1,"Pct":".500","PF":3,
         "PA":10,"note":"Withdrew from league on October 13"}],
      "_standings_are_labelled_unofficial_by_the_author": True,
      "all_eastern_league_team_as_printed": [
        ["Bill Evans, Coaldale","left end","Mike Gaffney, Bethlehem"],
        ["Stan Sieracki, Atlantic City","left tackle","Butch Boslego, Gilberton"],
        ["Stemmy, Shenandoah","left guard","Charlie Eastman, Bethlehem"],
        ["Honeyboy Evans, Coaldale","center","Duke, Shenandoah"],
        ["Jake Kaufman, Atlantic City","right guard","Gold, Mount Airy"],
        ["Kaufman*, Newark","right tackle","Joe Garland, Coaldale"],
        ["Vic Emmanuel, Lancaster","right end","George Poole, Newark"],
        ["Tomcavage, Shenandoah","quarterback","Rae McGraw, Lancaster"],
        ["Fritz Pollard, Gilberton","left halfback","Johnny Chapman, Gilberton"],
        ["Carl Beck, Bethlehem","right halfback","Joe Zaleha, Coaldale"],
        ["Briggs Kingsley, Lancaster","fullback","Marv Wood, Mount Carmel"]],
      "_asterisk_is_the_authors": "Fenton notes no Newark player named Kaufman appears to "
                                  "have existed and suggests John Hoffman. His note, held "
                                  "as his.",
      "bethlehem_scoring_as_printed": [
        ["Michael \"Gyp\" Downey",2,5,8,"-",41], ["Carroll \"Ginny\" Gooch",3,"-","-","-",18],
        ["Carl Beck","1 [1]","-","-","-","6 [12]"], ["Mike Gaffney",1,"-","-","-",6],
        ["Leo Douglas","[1]","-","-","-","[6]"], ["John \"Beets\" Berger","-","[1]","-","-","[1]"],
        ["Un-credited","-",1,"-","-",1]],
      "_bracketed_figures": "non-league play, per the author's own note",
      "clubs_named_that_the_club_table_does_not_hold": [
        "All-Lancaster Red Roses","Mount Carmel Wolverines","Coaldale Big Green",
        "Atlantic City Roses","Shenandoah Red Jackets","Mount Airy AA",
        "Clifton Heights Black & Orange"],
      "clubs_named_that_are_on_the_empty_list": ["Bethlehem Bears","Gilberton Catamounts",
                                                 "Newark Blues"],
    }

    # ---- ATLANTIC CITY enters for ONE GAME, under the non-league ruling.
    ac_game = ["game", "EXHIBITION", "1926", "1926-frankford-v-atlantic-city"]
    claims.append({"source_record": bsr, "source_id": SOURCE["source_id"],
        "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
        "subject": ac_game, "predicate": "ghosts.club_in_game",
        "value": {"club_as_printed": "Atlantic City Roses",
                  "role": "non-league professional club",
                  "opponent_in_scope": "Frankford Yellow Jackets (NFL)",
                  "enters_on": "Ryan's ruling of 2026-09-07 -- a non-league professional "
                               "club enters when a club in scope played it in a documented "
                               "game, FOR THAT GAME ONLY",
                  "scope": "THIS GAME ONLY. No club-season, no league, no season of this "
                           "club is held, and its Eastern League record is NOT admitted.",
                  "as_the_document_states_it": "Atlantic City started the season with a "
                      "string of losses to Frankford, Mount Carmel, Gilberton and Lancaster",
                  "_the_date_is_not_printed": "the page gives no date for this game; the "
                      "game key is therefore the season, not a day, and is marked as such"},
        "kind": "observed", "observed_at": "preserved-2026-09"})
    n["atlantic_city_game"] = 1

    out = {"source": SOURCE, "source_records": srecs,
           "held_documents": [held_doc],
           "claims": claims, "leads": leads,
           "disagreements_with_the_archive": disagree,
           "named_but_not_joined": unjoined,
           "counts": {"pages": n["pages"], "men_read": n["men_read"],
                      "claims": len(claims), "joined": n["joined"], "leads": n["leads"],
                      "disagreements": len(disagree),
                      "held_people_touched": len({c["person"] for c in claims if "person" in c}),
                      "held_documents": 1, "clubs_created": 0, "club_seasons_created": 0}}
    # ONE LEAGUE PER STORE. build_person_index derives a stint's league from the STORE
    # FILENAME -- k = (league, year, club) -- and there is no per-claim override. This
    # source covers NFL and AFL club-seasons, so it is written as two stores and both
    # are declared in store_league_tokens. Splitting follows the archive's own
    # convention (stats-usfl-1984 -> USFL); patching the builder to read a league off a
    # claim would change every store's behaviour to serve one ingest.
    def league_of(c):
        s_ = c.get("subject")
        if isinstance(s_, list) and s_ and s_[0] == "stint":
            for page, (key, *_r) in PAGES.items():
                if key and s_[2] == key[2] and str(s_[3]) == key[1]: return key[0]
        return None
    nfl = [c for c in claims if league_of(c) not in ("AFL","IND")]
    afl = [c for c in claims if league_of(c) == "AFL"]
    ind = [c for c in claims if league_of(c) == "IND"]
    out["claims"] = nfl
    out["counts"]["claims"] = len(nfl)
    aflout = {"source": {**SOURCE, "_split": "AFL club-seasons of the same source; see "
                         "ghostsofthegridiron.json for the NFL ones and for the held "
                         "documents. Split because a store carries one league."},
              "source_records": {c["source_record"]: srecs[c["source_record"]] for c in afl},
              "claims": afl, "leads": [],
              "counts": {"claims": len(afl),
                         "held_people_touched": len({c["person"] for c in afl if "person" in c})}}
    indout = {"source": {**SOURCE, "_split": "the INDEPENDENT club-seasons -- Frankford "
                         "1922 and 1923, before the club joined the NFL. Held apart "
                         "because a store carries one league token and these assert NO "
                         "league at all."},
              "source_records": {c["source_record"]: srecs[c["source_record"]] for c in ind},
              "claims": ind, "leads": [],
              "counts": {"claims": len(ind),
                         "held_people_touched": len({c["person"] for c in ind if "person" in c})}}
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "ghostsofthegridiron.json"), indent=1)
        IO.dump_atomic(aflout, os.path.join(BASE, "build", "ghostsofthegridiron-afl.json"), indent=1)
        IO.dump_atomic(indout, os.path.join(BASE, "build", "ghostsofthegridiron-ind.json"), indent=1)
    return out, aflout, indout


if __name__ == "__main__":
    o, a, i = main(write="--dry" not in sys.argv)
    c = o["counts"]
    print(f"AFL store: {a['counts']['claims']} claims, {a['counts']['held_people_touched']} people")
    print(f"IND store: {i['counts']['claims']} claims, {i['counts']['held_people_touched']} people "
          f"(Frankford 1922-23, no league asserted)")
    print(f"pages {c['pages']}  men read {c['men_read']}  joined {c['joined']}  leads {c['leads']}")
    print(f"held people touched: {c['held_people_touched']}")
    print(f"DISAGREEMENTS with the archive: {c['disagreements']}")
