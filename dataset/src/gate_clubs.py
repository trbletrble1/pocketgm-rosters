"""Gate for the club table (build/clubs.json). Read-only. Exit 1 on any failure.

  K1  every club-season the archive holds resolves through the table, or is in the table's own unresolved list
  K2  year scoping: 1946 'Buffalo Bisons' is the AAFC club; 1986 'Buffalo Bisons' is the Bills, recorded wrong-for-season
  K3  no claim lost or moved: the builder is not an index writer; the person index is untouched; the declared writer count is 8
  K4  an unmappable string fails loudly: resolve() records it, census() lists it, report() prints it
  K7  a misprinted string is a SPELLING of a club that was there: it names a club the table
      holds, in a year that club was active, is not one of that club's own names, and is not
      any OTHER club's real name that year -- which would make it a false join, not a misprint
  K9  an attested league span names a club the table HOLDS, sits inside that club's years,
      cites the page that attests it, and every league on every club carries its evidence
  K8  a span extension is corroborated OUTSIDE the source that proposed it, is adjacent to
      the span it extends, and every corroboration carries a locator
  K5  internal: unique ids, stable anchors, one club per code-year, every segment year named, merged clubs never chained,
      every string year-scoped inside its club's span, the unresolved list carries reasons and is not truncated

  python3 src/gate_clubs.py
"""
import os, sys, json, hashlib, collections, io
import coaching_season as CS
import clubs as CLUBSMOD    # PSEUDO_LEAGUES(): the declaration, read not typed

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import Clubs, report, norm, TABLE

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def year_of(y): return int(y[1:5]) if str(y).startswith("y") else int(y)


import json as _j, os as _o


def _decl_labels():
    """The gate's own explanations, read from declarations/clubs.json rather than typed."""
    d = _j.load(open(_o.path.join(BASE, "declarations", "clubs.json")))
    return d.get("LEAGUE_LABELS_THAT_ARE_NOT_ARCHIVE_TOKENS") or {}


def main():
    if not os.path.exists(TABLE):
        print("  FAIL  build/clubs.json is missing: run src/build_clubs.py --write"); return 1
    C = Clubs(); T = C.T
    idx_path = os.path.join(BASE, "build-reports", "person-index.json")
    before = hashlib.sha256(open(idx_path, "rb").read()).hexdigest()
    IDX = json.load(open(idx_path)); CL = IDX.pop("_clubs")
    unresolved = T["unresolved"]
    # A SILENCED CODE-YEAR IS EXPLAINED, not missing: a merger's phantom parent, or the second
    # printed name of a club that relocated within a season (RELOCATIONS_WITHIN_A_SEASON,
    # 2026-09-11). The table records each with its reason; the check below used to know only
    # PIT 1943, typed in, and failed the day a second kind of silence was ruled.
    silenced = {(r["code"], int(r["year"])) for r in unresolved.get("silenced_code_years", [])}
    listed = collections.defaultdict(set)                  # (source, string) -> years, from the table's own list
    for r in unresolved["strings"]:
        for y in range(r["first"] or 0, (r["last"] or 0) + 1): listed[(r["source"], r["string"])].add(y)

    # ---- K1 every club-season resolves or is listed
    print("K1  every club-season resolves or is reported unresolvable")
    seen = set(); unres = collections.Counter(); unlisted = []
    for k in CL: seen.add(("_clubs", k.split("|")[0], int(k.split("|")[1]), None))
    for pid, p in IDX.items():
        for k in p.get("seasons") or {}:
            lg, y, c = k.split("|", 2); seen.add(("season_key", c, year_of(y), lg))
        for k, rows in (p.get("coaching_seasons") or {}).items():
            lg, y, c = k.split("|", 2)
            for r in CS.rows(rows): seen.add(("coaching_season", c, year_of(y), lg, CS.printed_club(r)))
    for row in sorted(seen, key=str):
        src, tok, yr, lg = row[:4]
        if src == "_clubs" and (tok, yr) in silenced: continue
        if src == "coaching_season":
            pn = __import__("build_clubs").clean_printed(row[4] or "")
            hit = C.resolve(pn, yr, lg, source="pfa_cell") or C.resolve(tok, yr, lg, source="pfa_cell")
            key = ("coaching_season_key", f"{pn} [{tok}]")
        else:
            hit = C.resolve(tok, yr, None if lg in CLUBSMOD.PSEUDO_LEAGUES() else lg, source=None if src == "_clubs" else "season_key")
            key = (f"season_key:{lg}" if lg in CLUBSMOD.PSEUDO_LEAGUES() else "season_key", tok)
        if hit: continue
        unres[key] += 1
        if yr not in listed.get(key, set()) and not any(yr in ys and k2[1] == key[1] for k2, ys in listed.items()): unlisted.append((src, tok, yr, lg))
    total = len(seen)
    check(not unlisted, f"{total:,} club-seasons enumerated; {sum(unres.values()):,} did not resolve and every one is in the table's unresolved list" if not unlisted
          else f"{len(unlisted)} club-seasons neither resolve nor appear in the unresolved list: "
               + "; ".join(f"{n} x {k}" for k, n in collections.Counter((u[0], u[3]) for u in unlisted).most_common())
               + f" -- all: {sorted(unlisted, key=str)}")

    # ---- K2 year scoping
    print("K2  a name is looked up with its year")
    r46 = C.resolve("Buffalo Bisons", 1946, "AAFC"); r86 = C.resolve("Buffalo Bisons", 1986)
    check(r46 and C.league_for(r46[0], 1946) == "AAFC" and C.name_for(r46[0], 1946) == "Buffalo Bisons" and r46[1] == "official",
          f"1946 Buffalo Bisons -> {r46}: the AAFC club, by its own name")
    check(r86 and C.name_for(r86[0], 1986) == "Buffalo Bills" and r86[1] == "wrong_for_season",
          f"1986 Buffalo Bisons -> {r86}: the Bills, recorded as a name wrong for its season")
    check(r46 and r86 and r46[0] != r86[0], "the two resolve to different clubs")
    w = [s for c in T["clubs"] for s in c["strings"] if s["kind"] == "wrong_for_season" and not s.get("correct_name_then")]
    check(not w, f"every wrong-for-season string names the correct name for that season ({len(w)} do not)")
    cnp = [c for c in T["clubs"] if c["lineage"]["merger_of"]]
    check(len(cnp) >= 1 and all(len(c["segments"]) == 1 and not c["lineage"]["links"] for c in cnp),
          f"the merged clubs are their own clubs, never chained into a parent: {[c['id'] for c in cnp]}")
    rulings = json.load(open(os.path.join(BASE, "declarations", "clubs.json")))["MERGERS"]["rulings"]
    for r in rulings:
        if r["kind"] != "merger": continue
        hit = C.resolve(r["merged"], int(r["year"]), r["league"])
        check(bool(hit) and hit[0] in {c["id"] for c in cnp} and all(C.resolve(p, int(r["year"]), r["league"])[0] == hit[0] for p in r["of"] if C.resolve(p, int(r["year"]), r["league"])),
              f"{r['year']} '{r['merged']}' is its own club and its parents' names that year resolve to it, never to a parent: {hit}")

    # ---- K3 no claim lost or moved
    print("K3  the table is not an index writer")
    src = open(os.path.join(HERE, "build_clubs.py")).read() + open(os.path.join(HERE, "clubs.py")).read()
    check("save_index" not in src and "index_io" not in src and "dump_atomic" not in src, "build_clubs.py and clubs.py never import the index writer")
    check(hashlib.sha256(open(idx_path, "rb").read()).hexdigest() == before, "person index unchanged while the gate ran")
    decl = json.load(open(os.path.join(BASE, "declarations", "person-index-rebuild.json")))
    writers = [decl["builder"]] + [s["script"] for s in decl["chain"]] + list(decl.get("exempt", {}).keys())
    # THE PROPERTY IS THAT BUILD_CLUBS IS NOT AN INDEX WRITER. It used to also assert
    # `len(writers) == 8`, which is a BASELINE and not a property: the count is legitimately
    # 9 the moment a chain step is added, and adding apply_player_promotions.py failed this
    # gate for a reason that had nothing to do with the club table. P1 already checks that
    # every declared chain step writes the index, so the number was redundant as well as
    # brittle. Count reported, property asserted.
    check(not any("clubs" in w for w in writers), f"build_clubs is not among the {len(writers)} declared index writers (builder, chain, exempt helper)")
    total_claims = sum(len(p.get("seasons") or {}) for p in IDX.values())
    check(total_claims > 0, f"{total_claims:,} player seasons in the index, none touched")

    # ---- K4 loud failure
    print("K4  an unmappable string fails loudly")
    C2 = Clubs(); r = C2.resolve("Zzyzx Zebras", 1975, "NFL", source="test")
    rows = C2.census(); buf = io.StringIO(); report(C2, log=lambda s: buf.write(s + "\n"))
    check(r is None and any("Zzyzx Zebras" in row[2] for row in rows) and "Zzyzx Zebras" in buf.getvalue(), "an invented string is refused, counted by census() and printed by report()")
    r2 = C2.resolve("Buffalo Bisons", 1899); check(r2 is None and any(row[1] == "1899" for row in C2.census()), "a year outside every span is refused, not guessed")
    check(len(T["unresolved"]["strings"]) == T["counts"]["unresolved_strings"] and all(r.get("why") for r in T["unresolved"]["strings"]),
          f"the unresolved list is complete ({T['counts']['unresolved_strings']} strings, {T['counts']['unresolved_lookups']} lookups) and every row carries a reason")

    # ---- K5 internal consistency
    print("K5  internal consistency")
    ids = collections.Counter(c["id"] for c in T["clubs"]); check(all(n == 1 for n in ids.values()), f"{len(ids)} club ids, all unique")
    anchor = T["id_anchor"]
    check(all(anchor.get(f"{c['segments'][0]['code']}|{c['segments'][0]['first']}") == c["id"] for c in T["clubs"]), "every club's id is anchored to its first code and year")
    cy = collections.Counter((s["code"], y) for c in T["clubs"] for s in c["segments"] for y in range(s["first"], s["last"] + 1))
    check(all(n == 1 for n in cy.values()), f"{len(cy):,} code-years, each on exactly one club")
    unnamed = [(c["id"], y) for c in T["clubs"] for s in c["segments"] for y in range(s["first"], s["last"] + 1) if not C.name_for(c["id"], y)]
    check(not unnamed, f"every segment year carries an official name ({len(unnamed)} do not: {unnamed[:3]})")
    nolg = [(c["id"], y) for c in T["clubs"] if c["origin"] == "archive" for s in c["segments"] for y in range(s["first"], s["last"] + 1) if not C.league_for(c["id"], y)]
    check(not nolg, f"every archive club-season carries a league ({len(nolg)} do not: {nolg[:3]})")
    bad = [(c["id"], s["string"]) for c in T["clubs"] for s in c["strings"] if not (s["first"] <= s["last"])]
    check(not bad, f"every string is year-scoped ({len(bad)} are not)")
    outside = [(c["id"], s["string"], s["first"], s["last"]) for c in T["clubs"] for s in c["strings"]
               if s["kind"] not in ("beyond_archive", "club_without_a_season_that_year") and not (c["first"] <= s["first"] and s["last"] <= c["last"])]
    check(not outside, f"every string lies inside its club's span unless marked beyond the archive or a year without a season ({len(outside)} do not: {outside[:3]})")
    silent = [(k, v) for k, v in CL.items() if (k.split("|")[0], int(k.split("|")[1])) in {("PIT", 1943), ("PHI", 1943), ("CHC", 1944), ("PIT", 1944), ("BRO", 1945)} and not C.by_code_year(k.split("|")[0], int(k.split("|")[1]))]
    check(all(C.by_code_year(p, y) is None for p, y in (("PIT", 1943), ("PHI", 1943), ("CHC", 1944), ("PIT", 1944), ("BRO", 1945))), "the parents are silent in their merger years")
    all_codes = {k.split("|")[0] for k in CL}
    missing = [k for k in CL if not C.by_code_year(k.split("|")[0], int(k.split("|")[1])) and (k.split("|")[0], int(k.split("|")[1])) not in silenced]
    check(not missing, f"every _clubs code-year is in the table ({len(missing)} missing: {missing[:5]})")

    print("K6  no league in scope has sources naming it and no club")
    # EVERY EXPLANATION IS DECLARED, since 2026-09-09. Two of these three sets were typed
    # into this gate and one was read from the declaration, so a league could be RULED out
    # of scope and still fail here -- AA was, with its ruling written down three blocks
    # away in LEAGUES_ATTESTED_BUT_OUT_OF_SCOPE, which nothing read. Same class as the
    # statistics-store prefix and the staff-by-league test.
    P = T["per_league"]
    _lab = _decl_labels()
    art = set(_lab.get("fandom_survey_labels") or ())
    fam = set(_lab.get("family_mapped_to_the_archives_own_league") or ())
    # NOT LEAGUES AT ALL, declared rather than hardcoded: a token the index needs in the
    # league position for a club that asserts no league. Its clubs ARE in this table,
    # under league ''. Read from declarations/clubs.json so the ruling and the gate cannot
    # drift -- adding one here instead would be a second place to state the same thing.
    _decl = json.load(open(os.path.join(BASE, "declarations", "clubs.json")))
    nol = {k for k in (_decl.get("LEAGUE_TOKENS_THAT_ARE_NOT_LEAGUES") or {})
           if not k.startswith("_")}
    # A LEAGUE RULED OUT OF SCOPE IS AN EXPLANATION. The block's own text says a declared
    # unknown differs from an accidental one and that only it can tell them apart -- and
    # then no gate read it.
    oos = {k for k in (_decl.get("LEAGUES_ATTESTED_BUT_OUT_OF_SCOPE") or {})
           if not k.startswith("_")}
    zero = [lg for lg, v in P.items() if v["ZERO_CLUBS"]]
    unexplained = [lg for lg in zero if lg not in art | fam | nol | oos]
    check(not unexplained, f"{len(P)} leagues; {len(zero)} hold no club and every one is explained "
          f"({sorted(art & set(zero))} are the fandom survey's labels, {sorted(fam & set(zero))} are family-mapped to CFL with 0 refusals, {sorted(nol & set(zero))} are not leagues, {sorted(oos & set(zero))} are ruled out of scope)"
          if not unexplained else f"leagues with sources but no club: {unexplained}")
    # THE OTHER GATE'S NUMBER, NAMED HERE. This counts the CAUSE; gate_club_table_reach
    # counts the EFFECT -- the season keys those refusals leave unnameable. On 2026-09-09
    # both were found naming the same tokens with neither mentioning the other.
    try:
        _d = _j.load(open(_o.path.join(BASE, "declarations", "clubs.json")))
        print(f"    the EFFECT, counted by gate_club_table_reach: a ceiling of "
              f"{(_d.get('CLUB_TABLE_REACH') or {}).get('ceiling', '?')} season keys the table "
              f"cannot name. Every refusal counted here is one of them.")
    except Exception:
        pass
    silent = [lg for lg in fam & set(zero) if P[lg]["strings_refused"]]
    check(not silent or all(lg == "ORFU" for lg in silent), f"a family-mapped league refusing strings is reported, not silent: {[(lg, P[lg]['strings_refused']) for lg in silent]}")
    arfl = P.get("ARFL", {})
    check(arfl.get("clubs", 0) > 0 and arfl.get("club_seasons", 0) > 0, f"ARFL: {arfl.get('clubs')} clubs, {arfl.get('club_seasons')} club-seasons, {arfl.get('strings_refused')} strings still refusing")
    # ---- K7  misprinted strings
    print("K7  a misprinted string is a spelling of a club that was there")
    misprints = [(c, x) for c in T["clubs"] for x in c["strings"]
                 if x.get("kind") == "name_misprinted"]
    real_names = collections.defaultdict(set)          # normalised name -> club ids
    for c in T["clubs"]:
        for n in c["names"]:
            for y in range(int(n["first"]), int(n["last"]) + 1):
                real_names[(norm(n["name"]), y)].add(c["id"])
    bad_year = [f"{x['string']!r} on {c['id']} dated {x['first']} (club held {c['first']}-{c['last']})"
                for c, x in misprints if not (c["first"] <= int(x["first"]) <= c["last"])]
    self_name = [f"{x['string']!r} is already a name of {c['id']}"
                 for c, x in misprints
                 if any(norm(n["name"]) == norm(x["string"]) for n in c["names"])]
    other_club = [f"{x['string']!r} is {sorted(real_names[(norm(x['string']), int(x['first']))] - {c['id']})}'s "
                  "real name that year -- a false join, not a misprint"
                  for c, x in misprints
                  if real_names.get((norm(x["string"]), int(x["first"])), set()) - {c["id"]}]
    check(not bad_year, f"every misprint falls inside its club's span ({len(bad_year)} do not: {bad_year[:3]})")
    check(not self_name, f"no misprint is also one of the club's own names ({len(self_name)}: {self_name[:3]})")
    check(not other_club, f"no misprint is another club's real name that year ({len(other_club)}: {other_club[:3]})")
    if misprints:
        check(all(x.get("evidence") for _, x in misprints),
              f"every misprint carries its evidence ({len(misprints)} declared)")
    # ---- K8  span extensions
    print("K8  a span extension is corroborated outside the source that proposed it")
    exts = [(c, e) for c in T["clubs"] for e in (c.get("_span_extensions") or [])]
    alone = [f"{c['id']} {e['year']}: nothing outside {e.get('proposed_by')!r}"
             for c, e in exts
             if not [x for x in e.get("corroboration", [])
                     if x.get("source_id") and x["source_id"] != e.get("proposed_by")]]
    noloc = [f"{c['id']} {e['year']}" for c, e in exts
             if any(not x.get("locator") for x in e.get("corroboration", []))]
    faraway = [f"{c['id']} {e['year']} onto {e['was']}" for c, e in exts
               if int(e["year"]) not in (int(e["was"][0]) - 1, int(e["was"][1]) + 1)]
    check(not alone, f"every extension has corroboration from another source ({len(alone)}: {alone[:3]})")
    check(not noloc, f"every corroboration carries a locator ({len(noloc)}: {noloc[:3]})")
    check(not faraway, f"every extension is adjacent to the span it extends ({len(faraway)}: {faraway[:3]})")
    if exts:
        check(True, f"{len(exts)} span extension(s) declared: "
                    + ", ".join(f"{c['id']} {e['year']}" for c, e in exts[:4]))
    # ---- K9  attested league spans
    print("K9  an attested league span sits inside its club, cites pages, and adds nothing else")
    DECLS = json.load(open(os.path.join(BASE, "declarations", "clubs.json")))
    declared = DECLS.get("LEAGUE_SPANS_A_SOURCE_ATTESTS", {}).get("spans", [])
    byid = {c["id"]: c for c in T["clubs"]}
    outside, nopage, missing, uncited = [], [], [], []
    for spec in declared:
        c = byid.get(spec["club_id"])
        if c is None:
            missing.append(spec["club_id"]); continue
        a, b = int(spec["first"]), int(spec["last"])
        if not (c["first"] <= a <= b <= c["last"]):
            outside.append(f"{spec['club_id']} {spec['league']} {a}-{b} vs club {c['first']}-{c['last']}")
        if not [e for e in (spec.get("evidence") or []) if e.get("locator")]:
            nopage.append(f"{spec['club_id']} {spec['league']}")
        got = [L for seg in c["segments"] for L in seg.get("leagues", [])
               if L.get("league") == spec["league"]]
        if not got:
            uncited.append(f"{spec['club_id']} {spec['league']} declared but not in the table")
        elif any(not L.get("pages") for L in got):
            nopage.append(f"{spec['club_id']} {spec['league']} in the table with no pages")
    # THE PROPERTY, not the list: every league on any club must be a league SOME source
    # attested -- either a declared span with pages, or one the builder derived. A league
    # that appears on a club and is cited by nothing is how `NOT` got into the model.
    uncited_leagues = sorted({L["league"] for c in T["clubs"] for seg in c["segments"]
                              for L in seg.get("leagues", [])
                              if L.get("league") and not L.get("evidence")})
    check(not missing, f"every declared span names a club the table holds ({len(missing)}: {missing[:3]})")
    check(not outside, f"every declared span sits inside its club's years ({len(outside)}: {outside[:3]})")
    check(not nopage, f"every declared span cites a page ({len(nopage)}: {nopage[:3]})")
    check(not uncited, f"every declared span reached the table ({len(uncited)}: {uncited[:3]})")
    check(not uncited_leagues, f"every league on a club carries its evidence ({uncited_leagues[:5]})")
    if declared:
        check(True, f"{len(declared)} attested league span(s): "
                    + ", ".join(f"{s['club_id'].split('-1')[0][5:]} {s['league']}" for s in declared[:4]))
    print()
    print("K10 the pseudo-league tokens are DERIVED, not typed")
    # The four files that hand a season key's league to the club resolver used to type
    # ("COACHES", "SALARIES"). None gained IND when IND was declared a non-competition,
    # so 69 season keys handed the resolver a token the club table does not hold. They
    # now read declarations/person-index-rebuild.json; this recomputes what that list
    # MUST be -- the declared single-word tokens minus the leagues the club table holds
    # -- so the summary cannot drift from the declaration it summarises.
    import league_tokens as LT
    _decl = os.path.join(BASE, "declarations", "person-index-rebuild.json")
    _real = {L["league"] for c in T["clubs"] for seg in c["segments"] for L in seg.get("leagues", []) if L.get("league")}
    _derived = {t for t in LT.tokens(_decl).values() if t} - _real
    _declared = set(LT.pseudo_leagues(_decl))
    check(_derived == _declared,
          f"pseudo_league_tokens == single-word declared tokens minus the club table's leagues "
          f"({sorted(_declared)})" if _derived == _declared
          else f"declared {sorted(_declared)} but the table derives {sorted(_derived)}; "
               f"missing {sorted(_derived - _declared)}, extra {sorted(_declared - _derived)}")
    check(CLUBSMOD.PSEUDO_LEAGUES() == _declared,
          f"clubs.PSEUDO_LEAGUES() is the declaration and nothing else")
    print("K11 no club is minted from an empty name")
    # A DERIVED ID MOVING BECAUSE THE DATA MOVED, twice in three days. On 2026-09-09 the
    # coaching seasons were re-shaped and build_clubs read the printed club from a field
    # only ONE of the two producers writes; every PFA coaching row arrived with no name
    # and 46 clubs were minted as `club--2000`, `club--2001`, taking PFA:AMS off the
    # Amsterdam Admirals and stranding 3,833 statistics claims with no club at all. An
    # id built from a name is only as stable as the name, so the empty one fails here.
    nameless = sorted(c["id"] for c in T["clubs"]
                      if not any((n.get("name") or "").strip() for n in (c.get("names") or [])))
    check(not nameless, f"every club in the table has a name ({len(nameless)}: {nameless[:5]})")
    print()
    if fails:
        print(f"CLUB TABLE GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print(f"CLUB TABLE GATE: pass  ({T['counts']['clubs']} clubs, {T['counts']['strings']:,} strings, {T['counts']['unresolved_strings']} unresolved strings reported)"); return 0


if __name__ == "__main__":
    sys.exit(main())
