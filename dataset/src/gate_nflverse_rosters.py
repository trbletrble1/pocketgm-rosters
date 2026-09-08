"""Gate the nflverse roster ingest. Properties over EVERY claim and EVERY lead.

Three failures this prevents, each of which would be silent:
  a refused field reaching a claim -- headshot_url would record 11,701 pre-1950
    photographs that do not exist;
  a claim resting on a name alone -- 286 of those would be a demonstrable bug;
  a man the archive already holds being written as a NEW person because our key
    could not reach him.

  python3 src/gate_nflverse_rosters.py     exit 1 = FAIL
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
DECL = json.load(open(os.path.join(BASE, "declarations", "nflverse-rosters.json"), encoding="utf-8"))
ROUTES = {"name+birth_date", "birth_date_alone"}


def main():
    p = os.path.join(BASE, "build", "nflverse-rosters.json")
    if not os.path.exists(p):
        print("FAIL: build/nflverse-rosters.json missing"); return 1
    d = json.load(open(p))
    claims, leads = d["claims"], d["leads"]
    un = d.get("unmatchable_not_leads") or []
    fail = []
    def chk(c, m):
        if not c: fail.append(m)

    # 1 no refused field may appear as a predicate, read from the declaration
    refused = set(DECL["WHAT_IS_REFUSED_AND_WHY"])
    seen = {c["predicate"].split(".", 1)[1] for c in claims}
    chk(not (seen & refused), f"a refused field was written: {sorted(seen & refused)}")
    chk(set(d["REFUSED_FIELDS"]) == refused, "the build's refusal list drifted from the declaration")

    # 2 every claim has a person and an attributed source
    chk(all(c["subject"][0] == "person" and c["subject"][1] for c in claims),
        "a claim without a person")
    chk(all(c.get("source_id") == DECL["source_id"] and c.get("attribution") for c in claims),
        "a claim without its source")

    # 3 NO CLAIM RESTS ON A NAME ALONE
    bad = [c for c in claims if c.get("match_route") not in ROUTES]
    chk(not bad, f"{len(bad)} claims carry no permitted match route")

    # 4 a lead is not a person and carries no claims
    pids = {c["subject"][1] for c in claims}
    chk(all(l.get("IS_NOT_A_PERSON") is True for l in leads), "a lead is not marked IS_NOT_A_PERSON")
    chk(all(l.get("candidate_person") is None for l in leads), "a lead carries a person id")

    # 5 the unmatchable are NOT leads and are NOT resolved -- the distinction is the point
    for u in un:
        chk(u.get("IS_NOT_A_PERSON") is False, "an unmatchable entry is mislabelled a lead")
        chk(u.get("IS_NOT_RESOLVED") is True, "an unmatchable entry claims to be resolved")
        # An unmatchable entry may point at an archive person who ALREADY holds claims
        # from a different nflverse identity -- the source holding two men under one name.
        # That is allowed, but it must SAY SO, or someone will fold the two together.
        chk(u.get("archive_person_already_has_claims") == (u.get("archive_person") in pids),
            "an unmatchable entry misreports whether its archive person already has claims")
    dbl = [u for u in un if u.get("archive_person_already_has_claims")]
    print(f"  unmatchable whose archive person already holds claims: {len(dbl)} "
          f"(flagged, not folded)")

    # 6 disagreements are held, both values present, none resolved
    for kind, rows in d["disagreements"].items():
        other = "statscrew" if "statscrew" in kind else "pfa"
        for r in rows:
            chk(r.get("nflverse") and r.get(other), f"{kind}: a disagreement lost a value")
            chk("UNRESOLVED" in (r.get("ruling") or ""), f"{kind}: a disagreement was resolved")
    cnt = d["counts"]
    chk(cnt.get("disagree_birth_date_vs_statscrew") == len(d["disagreements"]["birth_date_vs_statscrew"]),
        "statscrew disagreement count does not match the rows")
    chk(cnt.get("disagree_birth_date_vs_pfa") == len(d["disagreements"]["birth_date_vs_pfa"]),
        "pfa disagreement count does not match the rows")

    # 7 nobody is both a claim subject and a lead
    lead_names = {l["name_as_printed"] for l in leads}
    chk(cnt["route_name_and_birth_date"] + cnt["route_birth_date_alone"] + cnt["unmatched"]
        == cnt["distinct_people"], "the routes do not reconcile to the population")
    chk(cnt["leads"] + cnt["unmatchable_archive_may_already_hold"] == cnt["unmatched"],
        "leads + unmatchable do not reconcile to unmatched")

    print(f"claims {len(claims)}  leads {len(leads)}  unmatchable-not-leads {len(un)}")
    print(f"refused fields absent: {sorted(refused)}")
    print(f"disagreements held: statscrew {len(d['disagreements']['birth_date_vs_statscrew'])}, "
          f"pfa {len(d['disagreements']['birth_date_vs_pfa'])}")
    if fail:
        print("\nGATE FAILED:"); [print("  -", f) for f in fail[:10] if f]; return 1
    print("\nGATE PASSED: no refused field, no name-only claim, leads and already-held kept apart")
    return 0


if __name__ == "__main__":
    sys.exit(main())
