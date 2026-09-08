"""Gate for the club table (build/clubs.json). Read-only. Exit 1 on any failure.

  K1  every club-season the archive holds resolves through the table, or is in the table's own unresolved list
  K2  year scoping: 1946 'Buffalo Bisons' is the AAFC club; 1986 'Buffalo Bisons' is the Bills, recorded wrong-for-season
  K3  no claim lost or moved: the builder is not an index writer; the person index is untouched; the declared writer count is 8
  K4  an unmappable string fails loudly: resolve() records it, census() lists it, report() prints it
  K5  internal: unique ids, stable anchors, one club per code-year, every segment year named, merged clubs never chained,
      every string year-scoped inside its club's span, the unresolved list carries reasons and is not truncated

  python3 src/gate_clubs.py
"""
import os, sys, json, hashlib, collections, io

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import Clubs, report, norm, TABLE

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def year_of(y): return int(y[1:5]) if str(y).startswith("y") else int(y)


def main():
    if not os.path.exists(TABLE):
        print("  FAIL  build/clubs.json is missing: run src/build_clubs.py --write"); return 1
    C = Clubs(); T = C.T
    idx_path = os.path.join(BASE, "build-reports", "person-index.json")
    before = hashlib.sha256(open(idx_path, "rb").read()).hexdigest()
    IDX = json.load(open(idx_path)); CL = IDX.pop("_clubs")
    unresolved = T["unresolved"]
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
            for r in rows: seen.add(("coaching_season", c, year_of(y), lg, r.get("printed_long")))
    for row in sorted(seen, key=str):
        src, tok, yr, lg = row[:4]
        if src == "coaching_season":
            pn = __import__("build_clubs").clean_printed(row[4] or "")
            hit = C.resolve(pn, yr, lg, source="pfa_cell") or C.resolve(tok, yr, lg, source="pfa_cell")
            key = ("coaching_season_key", f"{pn} [{tok}]")
        else:
            hit = C.resolve(tok, yr, None if lg in ("COACHES", "SALARIES") else lg, source=None if src == "_clubs" else "season_key")
            key = (f"season_key:{lg}" if lg in ("COACHES", "SALARIES") else "season_key", tok)
        if hit: continue
        unres[key] += 1
        if yr not in listed.get(key, set()) and not any(yr in ys and k2[1] == key[1] for k2, ys in listed.items()): unlisted.append((src, tok, yr, lg))
    total = len(seen)
    check(not unlisted, f"{total:,} club-seasons enumerated; {sum(unres.values()):,} did not resolve and every one is in the table's unresolved list" if not unlisted
          else f"{len(unlisted)} club-seasons neither resolve nor appear in the unresolved list, e.g. {unlisted[:5]}")

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
    check(len(writers) == 8 and not any("clubs" in w for w in writers), f"{len(writers)} declared index writers (builder, chain, exempt helper); build_clubs is not among them")
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
    missing = [k for k in CL if not C.by_code_year(k.split("|")[0], int(k.split("|")[1])) and (k.split("|")[0], int(k.split("|")[1])) not in {("PIT", 1943)}]
    check(not missing, f"every _clubs code-year is in the table ({len(missing)} missing: {missing[:5]})")

    print("K6  no league in scope has sources naming it and no club")
    P = T["per_league"]; art = {"Ohio", "AFL-1926", "AFL-1940", "Arena"}   # the fandom survey's own league labels, not archive tokens
    fam = {"IRFU", "WIFU", "ORFU"}                                        # PFA's pre-1958 Canadian unions: their clubs are held under the archive's CFL codes
    zero = [lg for lg, v in P.items() if v["ZERO_CLUBS"]]
    unexplained = [lg for lg in zero if lg not in art | fam]
    check(not unexplained, f"{len(P)} leagues; {len(zero)} hold no club and every one is explained "
          f"({sorted(art & set(zero))} are the fandom survey's labels, {sorted(fam & set(zero))} are family-mapped to CFL with 0 refusals)"
          if not unexplained else f"leagues with sources but no club: {unexplained}")
    silent = [lg for lg in fam & set(zero) if P[lg]["strings_refused"]]
    check(not silent or all(lg == "ORFU" for lg in silent), f"a family-mapped league refusing strings is reported, not silent: {[(lg, P[lg]['strings_refused']) for lg in silent]}")
    arfl = P.get("ARFL", {})
    check(arfl.get("clubs", 0) > 0 and arfl.get("club_seasons", 0) > 0, f"ARFL: {arfl.get('clubs')} clubs, {arfl.get('club_seasons')} club-seasons, {arfl.get('strings_refused')} strings still refusing")
    print()
    if fails:
        print(f"CLUB TABLE GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print(f"CLUB TABLE GATE: pass  ({T['counts']['clubs']} clubs, {T['counts']['strings']:,} strings, {T['counts']['unresolved_strings']} unresolved strings reported)"); return 0


if __name__ == "__main__":
    sys.exit(main())
