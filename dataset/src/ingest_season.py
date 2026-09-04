"""Ingest NFL 1950 end to end.

Identity is resolved through StatsCrew slugs and the player/coach cross-reference
link. A matching slug BODY across the p-/c- namespaces is never treated as
evidence (design 2.4, trap 1).
"""
import os, sys, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import Store
import fetch_statscrew as F

LEAGUE = os.environ.get("LEAGUE", "NFL")
YEAR = int(os.environ.get("YEAR", "1950"))
SEASON = f"{LEAGUE}-{YEAR}"
DECL = json.load(open(os.path.join(HERE, "..", "declarations", "statscrew.json")))

# per-era / per-league availability, read from the declaration rather than assumed
JERSEY_USABLE = YEAR >= DECL["field_availability"]["jersey"]["usable_from"]
GP_LEAGUE_RATE = DECL["field_availability"]["games_played"]["measured"].get(LEAGUE)

PERSON_PREDS = {"Birth Date": "birth_date", "College": "college", "Hometown": "hometown"}
STINT_PREDS  = {"#": "jersey", "GP": "games_played", "GS": "games_started"}


def run(store, log):
    store.add_source(DECL)
    teams = F.teams_in(LEAGUE, YEAR)
    log(f"teams: {len(teams)}  {teams}")

    by_slug = {}          # slug -> person id
    rows_seen = denot = absences = 0
    stints = []
    name_only_collisions = 0

    for team in teams:
        page = F.team_roster(team, YEAR)
        hdr, rows, slugs = F.parse_roster(page)
        cols_present = set(hdr)
        # a column absent from the page is a DECLARATION fact, not N absence claims
        missing_cols = [c for c in ("#", "GP", "GS", "Birth Date") if c not in cols_present]
        if missing_cols:
            log(f"  {team}: columns absent for this era/league: {missing_cols}")
        names = {}
        for r in rows:
            rows_seen += 1
            nm = r.get("Player", "")
            names.setdefault(nm, 0); names[nm] += 1
            slug = slugs.get(nm)
            sr = store.add_source_record("statscrew", f"roster/{team}-{YEAR}#{nm}")
            if not slug:
                store.add_denotation(sr, None, ["name"], "attribute-match",
                                     status="ambiguous", note="no slug on the row")
                continue
            if slug not in by_slug:
                by_slug[slug] = store.mint_person()
            p = by_slug[slug]
            store.add_denotation(sr, p, ["source_native_id"], "exact-id",
                                 matched_against="statscrew:" + slug)
            denot += 1
            subj_person = ("person", p)
            subj_stint  = ("stint", p, team, SEASON)
            store.declare_subject(subj_person)
            store.declare_subject(subj_stint)
            store.declare_subject(("person_season", p, SEASON))
            stints.append((p, team, slug, nm))

            for col, pred in PERSON_PREDS.items():
                if col not in cols_present:
                    continue
                v = r.get(col, "")
                if v == "":
                    store.add_absence(sr, subj_person, pred, YEAR,
                                      note=f"column present, cell blank ({team})")
                    absences += 1
                else:
                    store.add_claim(sr, subj_person, pred, v, YEAR)

            pos = r.get("Pos.", "")
            if pos:
                store.add_claim(sr, ("person_season", p, SEASON), "position",
                                {"vocab": "statscrew", "code": pos}, YEAR)

            for col, pred in STINT_PREDS.items():
                if col not in cols_present:
                    continue          # era/league does not have the field at all
                v = r.get(col, "")
                if v == "":
                    store.add_absence(sr, subj_stint, pred, YEAR,
                                      note=f"column present, cell blank ({team})")
                    absences += 1
                else:
                    try: v = int(v)
                    except ValueError: pass
                    store.add_claim(sr, subj_stint, pred, v, YEAR)

        dupes = {n: c for n, c in names.items() if c > 1}
        if dupes:
            name_only_collisions += sum(dupes.values())
            log(f"  {team}: repeated names on one roster: {dupes}")

    log(f"rows {rows_seen}  denotations {denot}  distinct persons {len(by_slug)}  absences {absences}")
    return by_slug, stints, rows_seen, denot


def resolve_coaches(store, by_slug, log):
    """Follow the p-/c- cross-reference. Never match on the slug body."""
    both, checked = [], 0
    for slug, p in by_slug.items():
        page = F.person(slug)
        info = F.parse_person(page)
        checked += 1
        if not info["is_real"]:
            log(f"  PHANTOM: {slug} returned a page with no name/birth date - skipped")
            continue
        cx = [x for x in info["xref"] if x.startswith("c-")]
        if cx:
            both.append((slug, cx[0], info["name"]))
            sr = store.add_source_record("statscrew", f"person/{slug}#xref")
            store.add_denotation(sr, p, ["source_native_id", "cross_reference"],
                                 "exact-id",
                                 matched_against=f"statscrew:{slug}<->{cx[0]}",
                                 note="bidirectional player/coach link followed; slug body NOT string-matched")
            store.add_claim(sr, ("person", p), "also_coached", cx[0], YEAR,
                            note="the man played AND coached - one person id, two careers")
    log(f"person pages checked {checked}; player+coach cross-references followed {len(both)}")
    for s, c, n in both[:12]:
        log(f"    {n}: {s} <-> {c}")
    return both


def main():
    out = []
    def log(m):
        print(m, flush=True); out.append(m)
    store = Store()
    by_slug, stints, rows, denot = run(store, log)
    # MATCH RATE, not count - a fallback makes the count check dead by construction
    rate = denot / rows if rows else 0
    log(f"denotation match rate {rate:.4f} ({denot}/{rows})")
    floor = float(os.environ.get("MATCH_FLOOR","0.99"))
    assert rate >= floor, f"match rate {rate:.3f} below floor {floor}"
    if os.environ.get("SKIP_XREF") == "1":
        log("SKIP_XREF=1 - person-page cross-reference pass skipped for this league")
        both = []
    else:
        both = resolve_coaches(store, by_slug, log)
    store.save(os.path.join(HERE, "..", "build", f"{LEAGUE.lower()}-{YEAR}.json"))
    log(f"claims {len(store.claims)}  denotations {len(store.denotations)}  persons {len(store.persons)}")
    open(os.path.join(HERE, "..", "build", f"ingest-{LEAGUE.lower()}-{YEAR}.log"), "w").write("\n".join(out))

if __name__ == "__main__":
    main()
