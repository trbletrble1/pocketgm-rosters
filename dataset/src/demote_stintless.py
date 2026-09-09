"""Demote the 201 promoted coaches who carry no coaching stint.

Ryan's ruling, following Gus Kitchens: a man documented in a staff listing with no
record of working a season is a LEAD, not a person. The archive's line is a career,
not a listing.

The promotions recorded their evidence and an undo, so this reverses from what is
stored -- nothing is re-derived. Every field the promotion held is carried into the
lead, so a later promotion stays a ruling rather than a re-fetch.
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
IDX_PATH = os.path.join(BASE, "build-reports", "person-index.json")
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import index_io as IO  # atomic index write
PROM = os.path.join(BASE, "build", "coach-promotions.json")


class DemoteError(Exception):
    pass


def main(write=True):
    prom = json.load(open(PROM))
    idx = json.load(open(IDX_PATH))
    before = sum(1 for k in idx if k != "_clubs")
    stintless = [p for p in prom["promotions"] if not p["coaching_seasons"]]
    leads, removed, kept = [], 0, 0
    for p in stintless:
        pid = p["person_id"]
        rec = idx.get(pid)
        if rec is None:
            kept += 1
            continue
        # every field the promotion held, so a later promotion is a ruling
        leads.append({
            "lead_id": f"lead-stintless-{len(leads)+1:04d}",
            "category": "promoted_then_demoted_no_stint",
            "name": p["name"], "source": p["source"],
            "pfa_code": p.get("pfa_code"),
            "IS_NOT_A_PERSON": True,
            "_ruling": "a man documented in a listing with no record of working a "
                       "season is a lead; the archive's line is a career, not a listing",
            "was_person_id": pid,
            "identified_by": p["identified_by"],
            "no_archive_match_evidence": p["no_archive_match_evidence"],
            "original_lead_ref": p["reversible"]["lead_ref"],
            "source_record": p["reversible"].get("source_record"),
            "fields": p.get("fields") or {},
            "coaching_seasons": p["coaching_seasons"],
            "reversible": {"undo": "re-create this person_id from was_person_id and "
                                   "restore the index entry",
                           "index_entry_at_demotion": rec},
        })
        del idx[pid]
        removed += 1
    after = sum(1 for k in idx if k != "_clubs")
    out = {"decided_at": "2026-09-06",
           "leads": leads,
           "counts": {"stintless_promotions": len(stintless),
                      "demoted": removed, "already_absent": kept,
                      "people_before": before, "people_after": after,
                      "by_source": dict(collections.Counter(p["source"] for p in stintless))}}
    if write:
        IO.save_index(idx)
        IO.dump_atomic(out, os.path.join(BASE, "build", "coach-demotions.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv); c = o["counts"]
    for k, v in c.items():
        print(f"  {k:24s} {v}")
