"""Record every prose block that moved from a lead onto a person when the
club-season key was fixed, so the move is visible and reversible.

Reads the BEFORE build (a snapshot passed on the command line) and the AFTER
build in build/, writes build/guide-prose-corpus-moves.json. Each move carries
the whole original lead record, so reversing a move needs nothing re-derived:
drop the claim, restore the lead.

  python3 src/record_guide_prose_moves.py BEFORE_CORPUS.json BEFORE_LEADS.json [--write]
"""
import os, sys, json, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def key(sr, off): return (sr, off[0], off[1])


def main():
    bc, bl = sys.argv[1], sys.argv[2]
    B0 = json.load(open(bc)); L0 = json.load(open(bl))
    B1 = json.load(open(os.path.join(BASE, "build", "guide-prose-corpus.json")))
    L1 = json.load(open(os.path.join(BASE, "build", "guide-prose-corpus-leads.json")))
    before_lead = {}
    for l in L0["leads"]:
        for b in l["prose"]: before_lead[key(l["source_record"], b["source_offsets"])] = l
    before_person = {key(c["source_record"], c["value"]["source_offsets"]): c["subject"][1]
                     for c in B0["claims"] if c["predicate"] == "guide.prose_block"}
    after_person = {key(c["source_record"], c["value"]["source_offsets"]): c
                    for c in B1["claims"] if c["predicate"] == "guide.prose_block"}
    after_lead = {key(l["source_record"], b["source_offsets"]) for l in L1["leads"] for b in l["prose"]}
    moves, why = [], collections.Counter()
    for k, c in after_person.items():
        if k in before_lead and k not in before_person:
            l = before_lead[k]
            w = ("the club-season now resolves" if l["why_matching_failed"].startswith("the archive holds no roster")
                 else "the man coached that club that year")
            why[w] += 1
            moves.append({"source_record": k[0], "source_offsets": [k[1], k[2]], "from_lead": l["lead_id"],
                          "to_person": c["subject"][1], "why": w, "club_season": [c["value"]["league"], c["value"]["year"], c["value"]["club"]],
                          "original_lead_record": l, "reverse": "delete the claim at these offsets and restore original_lead_record"})
    lost = [k for k in before_person if k not in after_person] + [k for k in before_lead if k not in after_person and k not in after_lead]
    dup = [k for k in after_person if k in after_lead]
    out = {"moved": moves, "counts": {
        "blocks_on_people": {"before": len(before_person), "after": len(after_person)},
        "blocks_on_leads": {"before": len(before_lead), "after": len(after_lead)},
        "blocks_total": {"before": len(before_person) + len(before_lead), "after": len(after_person) + len(after_lead)},
        "moved_lead_to_person": len(moves), "moved_by_reason": dict(why),
        "blocks_lost": len(lost), "blocks_on_both_a_person_and_a_lead": len(dup),
        "men_with_prose": {"before": len(set(before_person.values())),
                           "after": len({c["subject"][1] for c in after_person.values()})},
        "lead_records": {"before": len(L0["leads"]), "after": len(L1["leads"])}}}
    dec = collections.defaultdict(lambda: {"before": [0, 0], "after": [0, 0]})
    for tag, B in (("before", B0), ("after", B1)):
        for g in B["per_guide"]:
            if g.get("unreadable"): continue
            d = (g["year"] // 10) * 10; dec[d][tag][0] += g["entries_proved"]; dec[d][tag][1] += g["entries_resolved"]
    out["counts"]["resolution_by_decade"] = {str(d): {t: {"proved": v[t][0], "resolved": v[t][1]} for t in v} for d, v in sorted(dec.items())}
    print(json.dumps(out["counts"], indent=1))
    if "--write" in sys.argv:
        fp = os.path.join(BASE, "build", "guide-prose-corpus-moves.json")
        json.dump(out, open(fp, "w"), indent=1, ensure_ascii=False); print("wrote", fp)


if __name__ == "__main__":
    main()
