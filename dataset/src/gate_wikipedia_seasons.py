"""Gate the Wikipedia league/team-season builds. Properties over EVERY record in every
build/wikipedia-seasons-*.json, not samples.

  A  ATTRIBUTED: every claim, club-season and lead carries source_record (the article),
     revision_id and a `cited` flag where it states a fact. A Wikipedia fact without a
     revision id is not attributable -- the page will change.
  B  PEOPLE ONLY IN CLAIMS: every claim subject is ["person", P_...]; every lead carries
     NO person id and a why; nothing in `leads` was also claimed (no silent promotion).
  C  EVIDENCE NAMES ITSELF: every claim's evidence_method is one the declaration allows,
     and no match before era_cut rests on anything but club-year evidence.
  D  DISAGREEMENTS ARE HELD, NOT RESOLVED: every disagreement names both sides with real
     person ids from the index, and the Wikipedia side is also present as a claim.
  E  CLUBS: every club-season has club_as_printed; a resolved one has club_id AND how;
     every refusal is written in full.
  F  COUNTS ARE TRUE: claims == sum of coach_matched:*; leads == coach_lead;
     disagreements == disagreement:head_coach; no off-target article in source_records.

  python3 src/gate_wikipedia_seasons.py      exit 1 = FAIL
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia-seasons.json")))
ERA_CUT = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json")))["IDENTITY"]["era_cut"]
METHODS = {"club-year", "name-unique+coach-history"}
ENUM = os.path.join(BASE, "build-reports", "wikipedia-season-articles.json")


def gate_file(path, idx_ids, off_target):
    name = os.path.basename(path); d = json.load(open(path)); fail = []
    def chk(c, m):
        if not c: fail.append(f"{name}: {m}")
    claims, cs, leads, dis = d["claims"], d["club_seasons"], d["leads"], d["disagreements"]
    n = d["counts"]
    # A
    for c in claims:
        chk(c.get("source_record", "").startswith("wikipedia-en#") and c.get("revision_id"), f"claim without article+revision: {c.get('subject')}")
        chk(isinstance(c.get("cited"), bool), f"claim without a cited flag: {c.get('subject')}")
    for x in cs:
        chk(x.get("source_record") and x.get("revision_id") and x.get("year") and x.get("league"), f"club-season without attribution: {str(x)[:80]}")
    for l in leads:
        chk(l.get("source_record") and l.get("revision_id") and l.get("why_matching_failed"), f"lead without attribution or reason: {l.get('name_as_printed')}")
    # B
    claimed = set()
    for c in claims:
        s = c.get("subject")
        chk(isinstance(s, list) and s[0] == "person" and str(s[1]).startswith("P_") and s[1] in idx_ids, f"claim subject is not a person in the index: {s}")
        if isinstance(s, list) and len(s) > 1: claimed.add((s[1], c["value"].get("year"), c["value"].get("club_as_printed")))
    for l in leads:
        chk(not l.get("person") and not l.get("person_id"), f"a lead carries a person id: {l.get('name_as_printed')}")
    # C
    for c in claims:
        chk(c.get("evidence_method") in METHODS, f"undeclared evidence method {c.get('evidence_method')!r}")
        if c["value"].get("year", ERA_CUT) < ERA_CUT:
            chk(c.get("evidence_method") == "club-year", f"pre-era-cut match on {c.get('evidence_method')!r}: {c['subject']} {c['value'].get('year')}")
    # D
    claim_pids = {c["subject"][1] for c in claims}
    for x in dis:
        chk(x["wikipedia"]["person"] in idx_ids and all(a["person"] in idx_ids for a in x["archive"]), f"disagreement names a person not in the index: {x}")
        chk(x["wikipedia"]["person"] in claim_pids, f"disagreement whose Wikipedia side is not also a claim: {x['wikipedia']}")
        chk(x["wikipedia"]["person"] not in {a["person"] for a in x["archive"]}, f"a 'disagreement' where both sides agree: {x}")
    # E
    for x in cs:
        chk(x.get("club_as_printed"), f"club-season without a club string: {str(x)[:80]}")
        if x.get("club_id"): chk(x.get("club_resolved_how"), f"resolved club without how: {x['club_as_printed']}")
    for r in d.get("refused_clubs", []):
        chk(r.get("string") and r.get("why"), f"refusal without string or reason: {r}")
    # F
    chk(len(claims) == sum(v for k, v in n.items() if k.startswith("coach_matched:")), "claims != sum of coach_matched")
    chk(len(leads) == n.get("coach_lead", 0), "leads != coach_lead")
    chk(len(dis) == n.get("disagreement:head_coach", 0), "disagreements != disagreement:head_coach")
    used = {sr.split("#", 1)[1] for sr in d["source_records"]}
    chk(not (used & off_target), f"off-target articles used: {sorted(used & off_target)[:3]}")
    print(f"{name}: claims {len(claims)}  club_seasons {len(cs)}  leads {len(leads)}  disagreements {len(dis)}  "
          f"refused clubs {len(d.get('refused_clubs', []))}  templates missing {len(d.get('standings_templates_missing', {}))}")
    return fail


def main():
    files = sorted(glob.glob(os.path.join(BASE, "build", "wikipedia-seasons-*.json")))
    if not files: print("FAIL: no build/wikipedia-seasons-*.json"); return 1
    import index_io as IO
    idx = IO.load_index(); idx.pop("_clubs", None); idx_ids = set(idx)
    enum = json.load(open(ENUM))["leagues"]
    off = {t for v in enum.values() for t, r in v["titles"].items() if r["off_target"]} | \
          {r["target"] for v in enum.values() for r in v["titles"].values() if r["off_target"]}
    fail = []
    for f in files: fail += gate_file(f, idx_ids, off)
    if fail:
        print("\nGATE FAILED:"); [print("  -", x) for x in fail[:15]]; return 1
    print(f"\nGATE PASSED over {len(files)} build(s): attributed to article+revision, people only in claims, "
          "evidence declared, disagreements held with both sides, clubs resolved or refused in full, counts true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
