"""Ingest NFL 1950 end to end.

Identity is resolved through StatsCrew slugs and the player/coach cross-reference
link. A matching slug BODY across the p-/c- namespaces is never treated as
evidence (design 2.4, trap 1).
"""
import os, sys, re, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import Store
import fetch_statscrew as F

LEAGUE = os.environ.get("LEAGUE", "NFL")
YEAR = int(os.environ.get("YEAR", "1950"))
SEASON = f"{LEAGUE}-{YEAR}"
DEVIATIONS = []
DECL = json.load(open(os.path.join(HERE, "..", "declarations", "statscrew.json")))

# per-era / per-league availability, read from the declaration rather than assumed
FA = DECL["field_availability"]

# --- THE DECLARATION REFUSES, IT DOES NOT MERELY DESCRIBE ---------------------
# The design says "the ingest refuses to run without a discriminator". It said so
# for a while before it was true. These are the refusals that make it true.

_NOT_PLAYED = DECL.get("season_not_played", {})
if SEASON in _NOT_PLAYED:
    _r = _NOT_PLAYED[SEASON]
    sys.exit(f"REFUSED {SEASON}: {_r['why']}\n  {_r['rule']}")

DISCRIMINATORS = DECL["discriminators"]
def discriminator_order(year):
    """The declared order for this era. A source with no discriminator cannot
    resolve identity, so the ingest must not start."""
    for d in DISCRIMINATORS:
        sc = d["scope"]
        if sc.startswith("era:pre-") and year < int(sc.split("-")[-1]):
            return d["order"]
    for d in DISCRIMINATORS:
        if d["scope"] == "default":
            return d["order"]
    return None

DISC_ORDER = discriminator_order(YEAR)
if not DISC_ORDER:
    sys.exit(f"REFUSED {SEASON}: declarations/statscrew.json declares no "
             f"discriminator for this era. Identity cannot be resolved without one.")

# absence_semantics is what separates one declaration fact from N identical claims
ABSENCE = DECL["absence_semantics"]
assert "blank_cell_in_present_column" in ABSENCE and "column_absent_from_page" in ABSENCE, \
    "absence_semantics must state both cases: a blank cell is an absence CLAIM, " \
    "an absent column is a DECLARATION fact"
JERSEY_USABLE = YEAR >= FA["jersey"]["usable_from"]

def expected_fill(field):
    """What the DECLARATION predicts for this field, in this league-year.
    per_era  -> keyed LEAGUE-YEAR, falling back to the nearest sampled year
    per_league -> keyed LEAGUE
    Returns None where the declaration makes no prediction."""
    spec = FA.get(field)
    if not spec: return None
    m = spec.get("measured", {})
    if spec["kind"] == "constant":
        vals = [v for v in m.values() if isinstance(v, (int, float))]
        return vals[0] if vals else None
    if spec["kind"] == "per_league" and LEAGUE in m:
        return m[LEAGUE]
    key = f"{LEAGUE}-{YEAR}"
    if key in m: return m[key]
    same = [(abs(int(k.split("-")[1]) - YEAR), v) for k, v in m.items()
            if k.startswith(LEAGUE + "-") and "-" in k]
    return min(same)[1] if same else None

PERSON_PREDS = {"Birth Date": "birth_date", "College": "college", "Hometown": "hometown"}
STINT_PREDS  = {"#": "jersey", "GP": "games_played", "GS": "games_started"}


def run(store, log):
    store.add_source(DECL)
    teams = F.teams_in(LEAGUE, YEAR)
    log(f"teams: {len(teams)}  {teams}")

    # [filled, rows_on_pages_WITH_the_column, rows_total, pages_without]
    # Two denominators, because they answer different questions and a single
    # scalar cannot say which it used. See src/gate_census_denominator.py.
    fill_seen = collections.defaultdict(lambda: [0, 0, 0, 0])
    empty_pages = []
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
        if not rows:
            # A team the league page LINKS whose roster page parses to nothing.
            # Before this was recorded it contributed nothing, silently.
            empty_pages.append(team)
            log(f"  {team}: roster page parses to ZERO rows")
        for c in ("#", "GP", "GS", "Birth Date", "Hometown", "College"):
            if c not in cols_present: fill_seen[c][3] += 1
        for r in rows:
            for c in ("#", "GP", "GS", "Birth Date", "Hometown", "College"):
                fill_seen[c][2] += 1              # every row, column or not
                if c in cols_present:
                    fill_seen[c][1] += 1
                    if r.get(c, "") != "": fill_seen[c][0] += 1
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

    # --- THE DECLARATION IS LOAD-BEARING ------------------------------------
    # Measure what actually arrived and compare it to what the declaration
    # predicts. A deviation is either a bad declaration or a season the source
    # handles differently, and both are worth stopping for.
    global DEVIATIONS
    for field, col in (("jersey", "#"), ("games_played", "GP"),
                       ("games_started", "GS"), ("birth_date", "Birth Date"),
                       ("hometown", "Hometown"), ("college", "College")):
        seen = fill_seen.get(col)
        if not seen or not seen[1]:
            continue
        actual = 100.0 * seen[0] / seen[1]          # fill WHERE THE COLUMN EXISTS
        absolute = 100.0 * seen[0] / seen[2] if seen[2] else 0.0
        if abs(actual - absolute) > 0.1:
            DEVIATIONS.append((f"{LEAGUE}-{YEAR}", field, round(actual, 1),
                               round(absolute, 1),
                               f"column absent from {seen[3]} page(s): fill where "
                               f"present {actual:.1f}% but {absolute:.1f}% of all rows"))
        exp = expected_fill(field)
        if exp is None:
            DEVIATIONS.append((f"{LEAGUE}-{YEAR}", field, None, round(actual, 1),
                               "declaration makes NO prediction for this league"))
        elif abs(actual - exp) > 10.0:
            DEVIATIONS.append((f"{LEAGUE}-{YEAR}", field, exp, round(actual, 1),
                               "deviation > 10 points"))
    # NOT a deviation: a jersey column existing below usable_from is EXPECTED -
    # usable_from means "usable as a discriminator", and the whole point is that
    # the column is present but too sparse. The first sweep raised this on every
    # season 1922-1934, which was the check being noisy rather than a finding.
    # What IS a deviation is the column being ABSENT above the threshold.
    if empty_pages:
        DEVIATIONS.append((f"{LEAGUE}-{YEAR}", "roster_page", len(teams),
                           len(empty_pages),
                           f"teams linked by the league page with ZERO roster rows: "
                           f"{empty_pages}"))
    if JERSEY_USABLE and not fill_seen.get("#", (0, 0, 0, 0))[1]:
        DEVIATIONS.append((f"{LEAGUE}-{YEAR}", "jersey", FA["jersey"]["usable_from"], 0.0,
                           "jersey column ABSENT at or above usable_from"))
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
    if DEVIATIONS:
        log("DECLARATION DEVIATIONS:")
        for lg, fld, exp, act, why in DEVIATIONS:
            log(f"   {lg} {fld}: declared {exp}  actual {act}  -- {why}")
    json.dump([{"league_year": a, "field": b, "declared": c, "actual": d, "why": e}
               for a, b, c, d, e in DEVIATIONS],
              open(os.path.join(HERE, "..", "build", f"dev-{LEAGUE.lower()}-{YEAR}.json"), "w"))
    open(os.path.join(HERE, "..", "build", f"ingest-{LEAGUE.lower()}-{YEAR}.log"), "w").write("\n".join(out))

if __name__ == "__main__":
    main()
