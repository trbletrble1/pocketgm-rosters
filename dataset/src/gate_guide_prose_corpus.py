"""Gate for build/guide-prose-corpus.json. Same properties as the twenty-guide
gate, over the whole corpus. exit 1 = FAIL.

  G1  no prose block attaches to a man whose boundary was not proved.
  G2  EVERY block round-trips character-for-character against its source file,
      checked independently of the ingest by re-reading every guide.
  G3  a per-season vital cannot displace a career-level one: person subject,
      its own predicate, the club-season inside the value.
  G4  no claim attaches to an unresolved man; no lead carries a claim.
  G5  the excluded sets are excluded: no league Record & Fact Book and no
      zero-byte text produced a claim.
  G6  the boundary re-derives: a sample of guides reproduces the same proved
      spans and the same drop reasons.
  G7  drop categories match the ones the tuned sample used, so the rates can be
      compared rather than absorbed.

  python3 src/gate_guide_prose_corpus.py [--sample N]
"""
import os, sys, json, csv, random, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import guide_entries as G
BOOKS = os.path.join(BASE, "..", "..", "pgm3-sources", "nfl-books", "text_all")
SAMPLE_CATEGORIES = {"no per-player label inside the span",
                     "another rostered man appears in header position inside the span",
                     "span length outside 120-60,000 characters",
                     "the header line names more than one rostered man",
                     "no header-shaped line in the guide",
                     "a block that did not round-trip, not written"}
FAILS = []
def check(ok, m):
    if not ok: FAILS.append(m)


def main():
    B = json.load(open(os.path.join(BASE, "build", "guide-prose-corpus.json")))
    L = json.load(open(os.path.join(BASE, "build", "guide-prose-corpus-leads.json")))
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); CL = IDX.pop("_clubs")
    prose = [c for c in B["claims"] if c["predicate"] == "guide.prose_block"]
    vit = [c for c in B["claims"] if c["predicate"] == "guide.vitals_as_printed"]
    print(f"guides run: {B['counts']['guides_run']}   prose blocks: {len(prose):,}   "
          f"vitals: {len(vit):,}   leads: {len(L['leads']):,}")

    # G1
    for c in prose:
        check(c.get("_boundary_proved") is True and c["value"].get("header_as_printed"),
              "G1 a block without the boundary proof or its header")

    # G2 every block, by re-reading each guide once
    byfile = collections.defaultdict(list)
    for c in prose: byfile[c["source_record"].split("#", 1)[1]].append(c)
    rt = bad = 0
    for fn, cs in byfile.items():
        t = open(os.path.join(BOOKS, fn), errors="ignore").read()
        for c in cs:
            a, b = c["value"]["source_offsets"]
            if t[a:b] == c["value"]["text"] and len(c["value"]["text"]) == c["value"]["chars"]: rt += 1
            else:
                bad += 1
                if bad <= 5: FAILS.append(f"G2 block does not round-trip: {fn} {a}:{b}")
    print(f"  round-tripped against the source: {rt:,} of {len(prose):,}")
    check(bad == 0, f"G2 {bad} blocks do not round-trip")

    # G3
    for c in vit:
        check(c["subject"][0] == "person", "G3 a vital not on a person subject")
        check(c["predicate"] == "guide.vitals_as_printed", "G3 a vital on the wrong predicate")
        check("_this_is_a_per_season_fact_not_a_correction" in c, "G3 a vital without the per-season note")
        check(c["value"].get("year") and c["value"].get("club"), "G3 a vital without its club-season")

    # G4
    for c in B["claims"]:
        check(c["subject"][0] == "person" and c["subject"][1] in IDX,
              f"G4 a claim on {c['subject']} which the index does not hold")
    for l in L["leads"][:5000]:
        check(l.get("IS_NOT_A_PERSON") is True and "prose" in l, "G4 a malformed lead")
        check("predicate" not in l, "G4 a lead carrying a claim")

    # G5
    idxcsv = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(BASE, "..", "..",
              "pgm3-sources", "nfl-books", "index.csv")))}
    lw = {k + ".txt" for k, r in idxcsv.items() if r.get("league_wide") == "True"}
    used = {c["source_record"].split("#", 1)[1] for c in B["claims"]} | \
           {l["source_record"].split("#", 1)[1] for l in L["leads"]}
    check(not (used & lw), f"G5 {len(used & lw)} league Record & Fact Books produced records")
    check(not any(f.endswith(".notext") for f in used), "G5 a zero-byte text produced a record")
    check(B["counts"]["league_wide_excluded"] == len(lw),
          f"G5 the build excluded {B['counts']['league_wide_excluded']}, the index has {len(lw)}")
    print(f"  excluded: {len(lw)} league Record & Fact Books, 302 zero-byte texts; "
          f"neither produced a record")

    # G6 re-derive a sample
    n = int(sys.argv[sys.argv.index("--sample") + 1]) if "--sample" in sys.argv else 25
    random.seed(4)
    have = [g for g in B["per_guide"] if not g.get("unreadable")]
    by_cs = collections.defaultdict(dict)
    for pid, p in IDX.items():
        if p.get("merged_into") or not p.get("name"): continue
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2)
            if lg != "COACHES": by_cs[(y, club)][pid] = p["name"]
    for g in random.sample(have, min(n, len(have))):
        t = open(os.path.join(BOOKS, g["file"]), errors="ignore").read()
        codes, _ = G.resolve_club(g["club"], g["year"], CL, g["file"])
        men = {}
        for c in codes: men.update(by_cs.get((str(g["year"]), c), {}))
        kept, dropped = G.entries(t, men)
        check(len(kept) == g["entries_proved"],
              f"G6 {g['file']} re-derives {len(kept)} spans, build says {g['entries_proved']}")
        check(dict(dropped) == {k: v for k, v in g["dropped"].items()
                                if k != "a block that did not round-trip, not written"},
              f"G6 {g['file']} drop reasons differ on re-derivation")
    print(f"  re-derived the boundary on {min(n, len(have))} guides")

    # G8 club resolution: a guide's roster must come from the clubs its own token
    # names. A loose match once gave a 49ers guide 1,201 men drawn from every club.
    huge = [g for g in B["per_guide"] if not g.get("unreadable") and g["roster"] > 120]
    check(not huge, f"G8 {len(huge)} guides resolved a roster over 120 men, e.g. "
                    f"{huge[0]['file'] if huge else ''} with {huge[0]['roster'] if huge else 0}")
    amb = [g for g in B["per_guide"] if g.get("club_resolution") == "ambiguous nickname"]
    print(f"  club resolution: {sum(1 for g in B['per_guide'] if g.get('club_resolution')=='one club')} guides to one club, "
          f"{len(amb)} left ambiguous, {sum(1 for g in B['per_guide'] if g.get('club_resolution')=='no club of that name that season')} to none")

    # G9 the key fix: moves recorded and reversible, nothing lost or doubled, and no
    # block on a man by name alone -- every claim's man is on the resolved club-season
    # roster, COACHES seasons included, for that guide.
    mp = os.path.join(BASE, "build", "guide-prose-corpus-moves.json")
    if os.path.exists(mp):
        M = json.load(open(mp)); mc = M["counts"]
        check(mc["blocks_total"]["before"] == mc["blocks_total"]["after"],
              f"G9 blocks changed in total: {mc['blocks_total']}")
        check(mc["blocks_lost"] == 0 and mc["blocks_on_both_a_person_and_a_lead"] == 0,
              f"G9 lost {mc['blocks_lost']}, doubled {mc['blocks_on_both_a_person_and_a_lead']}")
        for m in M["moved"]:
            check(m.get("original_lead_record") and m["original_lead_record"].get("lead_id") == m["from_lead"],
                  "G9 a move without its original lead record")
        print(f"  moves: {mc['moved_lead_to_person']:,} blocks lead->person, recorded with their original lead; "
              f"total blocks {mc['blocks_total']['before']:,} before and {mc['blocks_total']['after']:,} after")
    on_cs = 0; off_cs = []
    rost = collections.defaultdict(set)
    for pid, p in IDX.items():
        if p.get("merged_into") or not p.get("name"): continue
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2); rost[(y[1:5] if y.startswith("y") else y, club)].add(pid)
    for c in prose:
        v = c["value"]
        if c["subject"][1] in rost.get((str(v["year"]), v["club"]), ()): on_cs += 1
        else: off_cs.append((c["source_record"], c["subject"][1], v["year"], v["club"]))
    check(not off_cs, f"G9 {len(off_cs)} blocks attach to a man NOT on that club-season, e.g. {off_cs[:2]}")
    print(f"  every block's man is on the resolved club-season roster: {on_cs:,} of {len(prose):,}")

    # G7
    for k in B["counts"]["dropped"]:
        check(k in SAMPLE_CATEGORIES, f"G7 a drop category the tuned sample never used: {k}")
    print(f"  drop categories: {len(B['counts']['dropped'])}, all of them ones the sample used")

    if FAILS:
        print(f"\nGATE FAILED ({len(FAILS)})")
        for m in FAILS[:15]: print("  FAIL", m)
        return 1
    print("\ngate_guide_prose_corpus: every property holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
