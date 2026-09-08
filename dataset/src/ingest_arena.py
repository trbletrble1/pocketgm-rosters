"""The Arena Football League, 1987-2019: a scope hole, fetched and filled.

WHAT WAS MISSING. Arena is in the archive's declared scope and the archive held
essentially none of it: no build store carried an Arena claim, identity.json had
no Arena entry, and the StatsCrew sweep's 228 club tokens contained no Arena.
Parsing built 91 clubs across 352 club-seasons from Wikipedia standings and PFA
transaction rows, but those clubs carried NO ROSTERS. This is the rosters.

THE SOURCE, AND WHY THIS ONE. Enumerated before pulling:

  StatsCrew `ARENA`   1987-2019, 32 years with teams, 404 club-seasons, 84 codes.
                      Full roster tables: #, Player, Pos., Birth Date, Height,
                      Weight, College, Hometown, GP. 404 of 404 parsed, 0 failed.
  PFA `{year}arfl*`   1987-2008 ONLY, 291 club pages, nothing from 2009 on.

StatsCrew wins on span (1987-2019 against 1987-2008) and on structure. 2009 is
empty AND CORRECT -- the league cancelled that season -- and 2020-2025 are empty
because this league folded in 2019; the 2024 revival is a different body.

THE CODE TRAP DOES NOT ARISE FROM THIS SOURCE, and that is worth stating because
it does from the other. PFA writes Arena clubs under CITY codes that collide with
the NFL's -- CLE, PIT, DAL, ARI. StatsCrew's are ALREADY NAMESPACED: ARENAALB,
ARENAARI, ARENABUF. They cannot be confused with the NFL's ARI/BUF/CLE, so this
ingest carries them through unchanged, the way ingest_afl1926 wrote AFLCHI rather
than CHI and for the same reason.

`ARENA` WAS NOT A DECLARED LEAGUE CODE. declarations/statscrew.json refuses any
code not in VERIFIED_with_rosters and its own instruction is "verify what it
actually resolves to and declare it before ingesting it". Verified by enumerating
all 39 years, then declared with that evidence. AFL3 -- which also serves arena
football but is a 33,869-byte stub, byte-identical for 1987, 2000 and 2019 with
zero roster links -- STAYS REFUSED, because a build reaching for the third AFL
(1940-41) must still not get arena football.

IDENTITY: name + birth date, and RYAN'S LEAD RULING STANDS. StatsCrew prints a
birth date on most Arena rows. A man who matches an archive person on both is
that person; a man who does not is a LEAD, never a new person minted on a name.

  python3 src/ingest_arena.py [--dry]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write

SRC_ID = "statscrew"
LEAGUE = "ARENA"
ROSTERS = "/tmp/arena_rosters.json"
OUT = os.path.join(BASE, "build", "arena-1987-2019.json")


class ArenaError(Exception):
    pass


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def iso(d):
    """'September 29, 1973' -> '1973-09-29'. Anything else -> None, never a guess."""
    m = re.match(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})$", (d or "").strip())
    if not m:
        return None
    M = ["January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"]
    if m.group(1) not in M:
        return None
    return f"{m.group(3)}-{M.index(m.group(1))+1:02d}-{int(m.group(2)):02d}"


def main(write=True):
    R = json.load(open(ROSTERS))["rosters"]
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    idx.pop("_clubs", None)

    # the archive's people by (name, birth date) and by name alone
    bybd, byname = {}, collections.defaultdict(list)
    for pid, p in idx.items():
        if not isinstance(p, dict) or not p.get("name"):
            continue
        n = norm(p["name"]); byname[n].append(pid)
        # THE INDEX STORES THE PRINTED STRING -- 'September 29, 1973' -- not ISO.
        # Comparing it to an ISO date sliced to [:10] gives 'September', which
        # matches nothing: the first run reported 0 of 13,599 matched. Both sides
        # go through iso() so the comparison is between two dates.
        for b in (p.get("person") or {}).get("birth_date", []) or []:
            k = iso(b) or str(b).strip()
            bybd.setdefault((n, k), []).append(pid)

    n = collections.Counter()
    claims, leads = [], []
    per = collections.defaultdict(dict)          # (year, code) -> {slug: row}
    for key, v in R.items():
        year, code = key.split("|"); year = int(year)
        for row in v["rows"]:
            name = (row.get("Player") or "").strip()
            if not name:
                n["rows_no_name"] += 1; continue
            slug = v["slugs"].get(name)
            per[(year, code)][slug or f"__noslug__{norm(name)}"] = row

    for (year, code), men in sorted(per.items()):
        for slug, row in sorted(men.items()):
            n["roster_rows"] += 1
            name = (row.get("Player") or "").strip(); nn = norm(name)
            bd = iso(row.get("Birth Date"))
            pid = None; route = None
            if bd and (nn, bd) in bybd and len(set(bybd[(nn, bd)])) == 1:
                pid, route = bybd[(nn, bd)][0], "name+birth_date"
            value = {"league": LEAGUE, "year": year, "club_code": code,
                     "name_as_printed": name, "statscrew_slug": slug,
                     "position_as_printed": (row.get("Pos.") or "").strip() or None,
                     "jersey": (row.get("#") or "").strip() or None,
                     "birth_date_as_printed": (row.get("Birth Date") or "").strip() or None,
                     "height": (row.get("Height") or "").strip() or None,
                     "weight": (row.get("Weight") or "").strip() or None,
                     "college": (row.get("College") or "").strip() or None,
                     "hometown": (row.get("Hometown") or "").strip() or None,
                     "games_played": (row.get("GP") or "").strip() or None,
                     "_club_code_is_the_sources_own": "StatsCrew namespaces its Arena codes "
                         "(ARENAALB); they cannot collide with the NFL's ARI/BUF/CLE the way "
                         "PFA's Arena city codes do",
                     "_resolved_on": "name + birth date, never a name alone"}
            sr = f"{SRC_ID}#roster/{code}-{year}#{name}"
            if pid:
                n["matched"] += 1
                claims.append({"source_record": sr, "source_id": SRC_ID, "stated_by": "StatsCrew",
                               "attribution": ["StatsCrew.com Arena Football League rosters"],
                               "subject": ["stint", pid, code, str(year)],
                               "predicate": "statscrew.arena_roster", "value": value,
                               "kind": "observed", "observed_at": year})
                claims.append({"source_record": sr, "source_id": SRC_ID, "stated_by": "StatsCrew",
                               "attribution": ["StatsCrew.com Arena Football League rosters"],
                               "subject": ["person", pid], "predicate": "statscrew.arena_club",
                               "value": value, "kind": "observed", "observed_at": year})
            else:
                n["lead"] += 1
                same = byname.get(nn, [])
                leads.append({"lead_id": f"lead-arena-{len(leads)+1:05d}",
                              "category": "player_lead_unpromoted",
                              "name_as_printed": name, "statscrew_slug": slug,
                              "places_on": {"league": LEAGUE, "year": year, "club": code},
                              "source_id": SRC_ID, "source_record": sr,
                              "IS_NOT_A_PERSON": True,
                              "why": ("no archive person matches on name AND birth date. "
                                      + (f"{len(same)} archive person(s) share this name; a name "
                                         "alone is not identity" if same else
                                         "no archive person of this name at all")),
                              "same_name_in_archive": same[:5],
                              "birth_date_printed": bool(bd),
                              "roster_line": value})

    cs = collections.Counter(f"{LEAGUE}|{c['subject'][3]}|{c['subject'][2]}"
                             for c in claims if c["subject"][0] == "stint")
    out = {"source": {"source_id": SRC_ID, "name": "StatsCrew.com, Arena Football League",
                      "stated_by": "StatsCrew", "acquisition": "fetched",
                      "league_code": "ARENA", "span": "1987-2019",
                      "_declared": "declarations/statscrew.json league_codes.VERIFIED_with_rosters",
                      "_2009_empty_and_correct": "the league cancelled its 2009 season",
                      "_codes_namespaced_by_the_source": True},
           "claims": claims, "leads": leads,
           "club_seasons": dict(sorted(cs.items())),
           "counts": {**dict(n), "claims": len(claims), "leads": len(leads),
                      "club_seasons_filled": len(cs),
                      "people_matched": len({c["subject"][1] for c in claims
                                             if c["subject"][0] == "person"}),
                      "distinct_leads": len({l["statscrew_slug"] or l["name_as_printed"]
                                             for l in leads})}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, OUT, indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--dry" not in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:24s} {v:,}")
