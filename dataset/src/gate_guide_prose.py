"""Gate for build/guide-prose.json. Properties over the whole build. exit 1 = FAIL.

  G1  no prose block attaches to a man whose boundary was not proved: every claim
      carries the proof flag and names the header it was bounded by.
  G2  EVERY BLOCK ROUND-TRIPS. The stored text is compared character-for-character
      against the source file at its recorded offsets. This is what proves the
      prose was not summarised, rewritten, normalised or OCR-corrected.
  G3  a per-season vital cannot overwrite a career-level one: it is a different
      predicate on a person subject, never a stint, and the archive's own PFA
      height and weight are untouched.
  G4  no claim attaches to an unresolved man; no lead carries a claim.
  G5  the boundary rule still holds on re-derivation: re-running the finder over
      each guide reproduces the same proved spans.
  G6  drops are counted, not silent: every guide reports its own reasons.

  python3 src/gate_guide_prose.py
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import guide_entries as G
BOOKS = os.path.join(BASE, "..", "..", "pgm3-sources", "nfl-books", "text_all")

FAILS = []
def check(ok, m):
    if not ok: FAILS.append(m)


def main():
    B = json.load(open(os.path.join(BASE, "build", "guide-prose.json")))
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); IDX.pop("_clubs")
    files = {}
    def src(rec):
        fn = rec.split("#", 1)[1]
        if fn not in files: files[fn] = open(os.path.join(BOOKS, fn), errors="ignore").read()
        return files[fn]

    prose = [c for c in B["claims"] if c["predicate"] == "guide.prose_block"]
    vit = [c for c in B["claims"] if c["predicate"] == "guide.vitals_as_printed"]
    print(f"prose blocks: {len(prose)}   per-season vitals: {len(vit)}   leads: {len(B['leads'])}")

    rt = 0
    for c in prose:
        v = c["value"]
        check(c.get("_boundary_proved") is True, "G1 a block without the boundary proof")
        check(v.get("header_as_printed"), "G1 a block that does not name its header")
        a, b = v["source_offsets"]
        if src(c["source_record"])[a:b] == v["text"]: rt += 1
        else: FAILS.append(f"G2 a block does not round-trip: {c['source_record']} {a}:{b}")
        check(len(v["text"]) == v["chars"], "G2 a block's length does not match its text")
    print(f"  round-tripped against the source file: {rt} of {len(prose)}")

    for c in vit:
        check(c["subject"][0] == "person", "G3 a vital is not on a person subject")
        check(c["predicate"] != "pfa.height" and c["predicate"] != "pfa.weight", "G3 a vital took a PFA predicate")
        check("_this_is_a_per_season_fact_not_a_correction" in c, "G3 a vital without the per-season note")
        check(c["value"].get("year") and c["value"].get("club"), "G3 a vital without its club-season")
    held = {c["subject"][1] for c in vit}
    print(f"  per-season vitals on {len(held)} men, all under guide.vitals_as_printed on a person subject")

    for c in B["claims"]:
        check(c["subject"][0] == "person" and c["subject"][1] in IDX,
              f"G4 a claim on {c['subject']} which is not a person the index holds")
    for l in B["leads"]:
        check(l.get("IS_NOT_A_PERSON") is True, "G4 a lead not marked IS_NOT_A_PERSON")
        check("prose" in l, "G4 a lead without its prose attached")
        check(not any(k in l for k in ("subject", "predicate")), "G4 a lead carrying a claim")

    # G5 re-derive
    same = 0
    for g in B["per_guide"]:
        t = src(f"x#{g['file']}")
        codes = []
        CL = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))["_clubs"]
        for k, v in CL.items():
            if k.endswith("|" + str(g["year"])) and G.norm(g["club"]).rstrip("s") in G.norm(v):
                codes.append(k.split("|")[0])
        men = {}
        for pid, p in IDX.items():
            if p.get("merged_into") or not p.get("name"): continue
            for k in p.get("seasons") or {}:
                lg, y, club = k.split("|", 2)
                if lg != "COACHES" and y == str(g["year"]) and club in codes: men[pid] = p["name"]
        kept, dropped = G.entries(t, men)
        check(len(kept) == g["entries_proved"],
              f"G5 {g['club']} {g['year']} re-derives {len(kept)} proved spans, build says {g['entries_proved']}")
        check(dict(dropped) == g["dropped"], f"G5 {g['club']} {g['year']} drop reasons differ on re-derivation")
        same += 1
    print(f"  re-derived the boundary on {same} guides")

    for g in B["per_guide"]:
        check("dropped" in g, f"G6 {g['club']} {g['year']} reports no drops")
    print(f"  dropped in total: {sum(B['counts']['dropped'].values())} "
          f"({', '.join(f'{v} {k}' for k, v in B['counts']['dropped'].items())})")

    if FAILS:
        print(f"\nGATE FAILED ({len(FAILS)})")
        for m in FAILS[:15]: print("  FAIL", m)
        return 1
    print("\ngate_guide_prose: every property holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
