"""Pro Football Archives' award pages: honour-team selections and named awards.

TWO PREDICATES, BECAUSE THEY ARE TWO ASSERTIONS. Ryan's ruling of 2026-09-08.

  honour_team_selection  named to an honour team at a POSITION -- one of eleven or
                         twenty-two. Renamed from `ghosts.honour_selection`, which
                         was defined for exactly this and should stop naming one
                         source now that two write it.
  award_won              won a singular named thing. No position, no seat. Widening
                         one predicate over both would leave a position field
                         meaningless on 939 claims and every consumer testing which
                         kind it holds.

THE SELECTOR IS PART OF THE CLAIM, NOT METADATA. 130 of 778 (year, award) pairs on
these pages have more than one winner, because several bodies gave several awards.
1957 NFL Player of the Year is Jim Brown AND Johnny Unitas AND Y. A. Tittle. Drop the
selector and one year in six becomes a false disagreement.

SELECTORS ARE HELD AS PRINTED. `AP` stays `AP`; the page's own legend travels beside
it. Expanding it in the value would be the archive rewriting a source's shorthand.

THE CLUB IS NOT MEMBERSHIP on either predicate. `club_as_printed` says who he was
with when he was honoured. The subject is the PERSON, never a stint, so nothing here
can be read as a season.

  python3 src/ingest_pfa_awards.py [--write]
"""
import os, re, sys, json, collections, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from readings import person_name as _person_name

AWARDS = os.path.expanduser("~/Documents/pgm3-sources/pfa-awards")
OUT = os.path.join(BASE, "build", "pfa-awards.json")
NAV = ("privacy policy", "nfl boxscores", "nfl game officials", "nfl training camps",
       "nfl roster limits", "pro football hall of fame", "super bowl", "in memoriam",
       "previous season", "last updated")

PREDICATE_DEFINITIONS = {
    "honour_team_selection": {
        "definition": "named to an honour team for a season by a named selector -- an "
                      "all-pro or all-league selection.",
        "is_not_membership": "it does NOT assert that the man played for the club named "
                             "beside him, or for any club. Two selectors may name him "
                             "and a third may not; the honour is the selector's act, not "
                             "the club's.",
        "carries": "year, the honour as printed (All-NFL, All-CFL), position as printed, "
                   "the club he was with as printed, and the SELECTORS as printed.",
        "renamed_from": "ghosts.honour_selection, 2026-09-08 -- RENAMED, not twinned. A "
                        "source prefix belongs on a predicate where sources MEAN "
                        "different things; Fenton and PFA mean the same thing here, and "
                        "source_id already records which said it.",
    },
    "award_won": {
        "definition": "won a singular named award for a season, as stated by a named "
                      "selector -- Player of the Year, Coach of the Year, Rookie of the "
                      "Year.",
        "is_not_membership": "it does NOT assert that the man played for the club named "
                             "beside him. The club is who he was with when he was given "
                             "the award.",
        "is_not_an_honour_team": "there is no position and no seat. A man is not one of "
                                 "eleven; he won a thing. Filing it under "
                                 "honour_team_selection would make `position` meaningless "
                                 "on every one of these claims.",
        "carries": "year, the award as printed, the league where the page or the award "
                   "name states one, the club as printed, and the SELECTORS as printed.",
        "several_winners_is_normal": "130 of 778 (year, award) pairs have more than one "
                                     "winner because several bodies gave several awards. "
                                     "That is not a contested fact and must not be read "
                                     "as one.",
        "ruled_by": "Ryan, 2026-09-08.",
    },
}


def text(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).replace("\xa0", " ").strip()


def norm(s):
    """THE one name reading -- readings.person_name. This file used to carry
    its own copy, and the copies disagreed on apostrophes, initials, hyphens
    and suffixes across about 1,200 names."""
    return _person_name(s)


def people_by_name(conn):
    by = collections.defaultdict(set)
    for p, n in conn.execute("select person, name from person_name"):
        by[norm(n)].add(p)
    return by


def rosters(conn):
    """(club_id, year) -> {person}. THE CLUB AND THE SEASON ARE ON THE CLAIM AND MUST
    BE USED. Two men are called Jim Brown; only one of them was a Cleveland Brown in
    1957, and the row says Cleveland Browns 1957. Matching on the name alone threw that
    away and filed the most famous award on the page as ambiguous."""
    out = collections.defaultdict(set)
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim where scope='stint' "
            "and club_id is not null and person is not null and league not in "
            "('COACHES','ASSISTANTS','SALARIES','COACH') group by club_id, year, person"):
        out[(cid, y)].add(p)
    return out


def main():
    write = "--write" in sys.argv
    conn = sqlite3.connect(paths.READ_MODEL)
    byname = people_by_name(conn)
    roster = rosters(conn)
    names_of = collections.defaultdict(set)
    for p_, nm_ in conn.execute("select person, name from person_name"):
        if norm(nm_): names_of[p_].add(norm(nm_))
    import clubs as ac
    C = ac.Clubs()

    files = sorted(f for f in os.listdir(AWARDS) if f.endswith(".html"))
    claims, leads, srs, persons = [], [], {}, []
    loosened, loose_ambiguous = [], []
    n = collections.Counter()
    legends = {}
    cid = 0

    for f in files:
        m = re.match(r"^(\d{4})([a-z]*)awards\.html$", f)
        if not m:
            n["file not of the award shape, skipped"] += 1
            continue
        year, league_token = int(m.group(1)), m.group(2).upper()
        t = open(os.path.join(AWARDS, f), errors="replace").read()
        sr = f"pro-football-archives#{f}"
        srs[sr] = {"source_id": "pro-football-archives", "locator": f}
        section, legend = None, None
        rows_here = []
        for tb in re.findall(r"(?is)<table.*?</table>", t):
            for tr in re.findall(r"(?is)<tr.*?</tr>", tb):
                c = [text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
                if not any(c):
                    continue
                if len(c) == 1:
                    low = c[0].lower()
                    if any(k in low for k in NAV) or low.startswith("&copy"):
                        section = None; continue
                    if re.match(r"^All[\s-]", c[0]):
                        section = c[0]
                    elif c[0].count("=") >= 2:
                        legend = dict(re.findall(r"([A-Za-z][A-Za-z-]*)=([^=]+?)(?=\s+[A-Za-z][A-Za-z-]*=|$)", c[0]))
                        legend = {k: v.strip() for k, v in legend.items()}
                        legends[f] = legend
                    continue
                # THE BANNER AND THE COLUMN HEADERS SHARE A ROW on many pages:
                # `All-AFL | Position | Team | Selectors`. Read as data that is an
                # award called `All-AFL` won by `Position`, and it left 26 header rows
                # as leads and every selection on those pages carrying a placeholder
                # instead of its honour.
                if len(c) > 1 and c[1] in ("Position", "Team", "Selectors"):
                    if re.match(r"^All[\s-]", c[0]):
                        section = c[0]
                    continue
                if len(c) < 3 or c[0] in ("Offense", "Defense", "Player", "Position", "Name"):
                    continue
                rows_here.append((section, c))
        for section, c in rows_here:
            sel = c[3] if len(c) > 3 else ""
            looks_position = bool(re.match(r"^[A-Z]{1,3}(-[A-Z]{1,3})?$", c[1]))
            if (section and re.match(r"^All[\s-]", section)) or looks_position:
                pred = "honour_team_selection"
                name, val = c[0], {
                    "year": year, "honour_as_printed": section or "(the page's honour "
                                                                 "team; no banner in this table)",
                    "position_as_printed": c[1] or None,
                    "club_as_printed": c[2] or None,
                    "selectors_as_printed": sel.split() or None,
                }
                lgt = re.match(r"^All-([A-Za-z]+)$", section or "")
                if lgt: val["league"] = lgt.group(1).upper()
                elif league_token: val["league"] = league_token
            else:
                pred = "award_won"
                name, val = c[1], {
                    "year": year, "award_as_printed": c[0],
                    "club_as_printed": c[2] or None,
                    "selectors_as_printed": sel.split() or None,
                }
                lgm = re.match(r"^([A-Z]{2,5})\s", c[0])
                if lgm: val["league"] = lgm.group(1)
                elif league_token: val["league"] = league_token
            if legends.get(f):
                val["selector_legend"] = legends[f]
            if not name:
                n["row with no name, refused"] += 1
                continue
            n[pred] += 1
            rec = f"{sr}#{pred}#{name}#{val.get('award_as_printed') or val.get('honour_as_printed')}"
            srs[rec] = {"source_id": "pro-football-archives",
                        "locator": f"{f}#{name}"}
            hits = sorted(byname.get(norm(name), ()))
            how = "exact full name, unique in the archive"
            # the club and the season, resolved once and used by both rules below
            _club, _yr = val.get("club_as_printed"), val.get("year")
            _lg = val.get("league")
            _r = (C.resolve(_club, _yr, _lg if _lg and _lg.isalpha() else None,
                            source="pfa-awards") if _club and _yr else None)
            if not hits and _r:
                # LOOSER, AND ONLY BECAUSE THE CLUB-SEASON HOLDS IT. Ryan's ruling of
                # 2026-09-08: a surname and a forename initial join ONLY where the
                # candidate holds a season on that exact club-season. Without that
                # condition this rule is the surname trap -- `G. Wilson` and `Abe
                # Wilson` share a surname and are not the same man.
                w = norm(name).split()
                if len(w) >= 2:
                    on_it = [p_ for p_ in roster.get((_r[0], _yr), ())
                             if any(x.split() and x.split()[-1] == w[-1]
                                    and x.split()[0][:1] == w[0][:1]
                                    for x in names_of.get(p_, ()))]
                    if len(on_it) == 1:
                        hits = on_it
                        how = ("surname and forename initial, and he is the only such "
                               f"man holding a season on {_r[0]} in {_yr}")
                        n["joined on surname and initial, held to the club-season"] += 1
                        loosened.append(
                            {"name_as_printed": name, "year": _yr, "club": _club,
                             "league": _lg, "person": on_it[0],
                             "archive_names": sorted(names_of.get(on_it[0], ())),
                             "predicate": pred, "club_id": _r[0]})
                    elif len(on_it) > 1:
                        n["surname and initial, but SEVERAL such men on that "
                          "club-season -- refused"] += 1
                        loose_ambiguous.append(
                            {"name_as_printed": name, "year": _yr, "club": _club,
                             "club_id": _r[0], "candidates":
                                 [sorted(names_of.get(p_, ()))[:2] for p_ in on_it]})
            if len(hits) > 1:
                # SEVERAL MEN OF THAT NAME: the club and the season decide, and they
                # are on the row. A coach's award has no club-season to stand on, so
                # it stays ambiguous rather than being guessed.
                yr = val.get("year"); r = _r
                if r:
                    on_it = [p for p in hits if p in roster.get((r[0], yr), ())]
                    if len(on_it) == 1:
                        hits = on_it
                        how = ("the exact name, and only one man of it holds a season "
                               f"on {r[0]} in {yr}")
                        n["ambiguous name settled by the club and season"] += 1
                    elif len(on_it) > 1:
                        n["several men of that name on that very club-season"] += 1
            cid += 1
            base = {"id": "c_%06d" % cid, "predicate": pred, "value": val,
                    "kind": "observed", "source_id": "pro-football-archives",
                    "source_record": rec, "stated_by": "Pro Football Archives",
                    "attribution": [], "observed_at": year,
                    "_definition": PREDICATE_DEFINITIONS[pred]["definition"],
                    "_is_not_membership": PREDICATE_DEFINITIONS[pred]["is_not_membership"]}
            if len(hits) == 1:
                base["subject"] = ["person", hits[0]]
                base["_join_evidence"] = how
                claims.append(base); n[pred + " joined"] += 1
            else:
                # A NAME IS NOT A PERSON. Nought or several matches is a lead, not a
                # join, and not a new person either -- the surname trap has been walked
                # into here often enough.
                cid -= 1
                leads.append({"lead_id": f"lead-pfa-award-{len(leads)+1:05d}",
                              "IS_NOT_A_PERSON": True, "name_as_printed": name,
                              "predicate_it_would_be": pred, "value": val,
                              "source_record": rec,
                              "why": ("no person of that name in the archive" if not hits
                                      else f"{len(hits)} people hold that exact name")})
                n[pred + " left as a lead"] += 1

    out = {"source": {"source_id": "pro-football-archives",
                      "acquisition": "fetched 2026-09-08, one request at a time",
                      "stated_by": "Pro Football Archives"},
           "_what": f"{len(files)} award pages, 1920-2026",
           "predicate_definitions": PREDICATE_DEFINITIONS,
           "_selectors_as_printed": "the selector tokens are held exactly as the page "
                                    "prints them, with that page's own legend beside "
                                    "them in `selector_legend`. Expanding `AP` to "
                                    "`Associated Press` in the value would be the archive "
                                    "rewriting a source's shorthand.",
           "_the_looser_name_rule": "Ryan's ruling, 2026-09-08: a surname and a forename "
                                    "initial join ONLY where the candidate holds a season "
                                    "on that exact club-season. The club-season is what "
                                    "makes it safe; without it the rule is the surname "
                                    "trap.",
           "joined_on_surname_and_initial": loosened,
           "refused_several_such_men_on_the_club_season": loose_ambiguous,
           "source_records": srs, "claims": claims, "leads": leads,
           "counts": dict(n) | {"claims": len(claims), "leads": len(leads),
                                "pages": len(files)}}
    for k, v in sorted(n.items(), key=lambda kv: -kv[1]):
        print(f"   {k:44s} {v:>7,}")
    print(f"   {'claims':44s} {len(claims):>7,}")
    print(f"   {'leads':44s} {len(leads):>7,}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        print("wrote", OUT)
    else:
        print("   (dry run; --write to store)")


if __name__ == "__main__":
    main()
