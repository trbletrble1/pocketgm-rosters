"""Apply build/person-merges.json to build-reports/person-index.json.

REVERSIBLE BY CONSTRUCTION. Each merged person carries, in the index itself, the
exact contribution it took from the record it absorbed: the season keys it
gained, the stint fields it took on seasons both held, and the person values it
added. So this script begins by UNDOING every contribution already recorded,
and then applies whatever decisions build/person-merges.json currently holds.

That makes it idempotent, and it makes un-merging real: delete a decision, run
this again, and the two records stand apart exactly as they did.

NOTHING IS DELETED. The absorbed record stays whole in the index and gains
`merged_into`; the canonical gains `merged_from`.

  python3 src/apply_person_merges.py [--write] [--report PATH]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
IDXP = os.path.join(BASE, "build-reports", "person-index.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import index_io as IO  # atomic index write
MP = os.path.join(BASE, "build", "person-merges.json")


def undo(index):
    """Reverse every contribution the index records. Returns how many it reversed."""
    n = 0
    for pid, v in index.items():
        if pid == "_clubs" or not isinstance(v, dict): continue
        for c in v.pop("merged_from", []) or []:
            for k in c.get("seasons_added", []): (v.get("seasons") or {}).pop(k, None)
            for k, fields in (c.get("stint_fields_taken") or {}).items():
                sd = (v.get("seasons") or {}).get(k)
                if not sd: continue
                for scope, f in fields: (sd.get(scope) or {}).pop(f, None)
            for f, vals in (c.get("person_values_added") or {}).items():
                cur = (v.get("person") or {}).get(f)
                if not cur: continue
                v["person"][f] = [x for x in cur if x not in vals]
                if not v["person"][f]: v["person"].pop(f)
            n += 1
    for pid, v in index.items():
        if pid != "_clubs" and isinstance(v, dict): v.pop("merged_into", None)
    return n


def apply(index, merges):
    applied, missing = [], []
    for d in merges["merges"]:
        c, a = d["canonical_person"], d["absorbed_person"]
        if c not in index or a not in index:
            missing.append(d["merge_id"]); continue
        C, A = index[c], index[a]
        rw = dict(d["contribution"]["season_key_rewrites"])
        gained = set(d["contribution"]["seasons_gained_from_absorbed"])
        took = d["contribution"]["stint_fields_taken_from_absorbed"]
        seasons_added = []
        for k, sd in (A.get("seasons") or {}).items():
            ck = rw.get(k, k)
            if ck in gained and ck not in (C.get("seasons") or {}):
                C.setdefault("seasons", {})[ck] = json.loads(json.dumps(sd)); seasons_added.append(ck)
        for k, fields in took.items():
            cs = (C.get("seasons") or {}).get(k)
            src = next((sd for kk, sd in (A.get("seasons") or {}).items() if rw.get(kk, kk) == k), None)
            if not cs or not src: continue
            for scope, f in fields:
                if f not in (cs.get(scope) or {}): cs.setdefault(scope, {})[f] = (src.get(scope) or {}).get(f)
        added = {}
        for f, vals in d["contribution"]["person_values_added_from_absorbed"].items():
            cur = (C.get("person") or {}).setdefault(f, [])
            new = [x for x in vals if x not in cur]
            if new: cur.extend(new); added[f] = new
        C["seasons"] = {k: C["seasons"][k] for k in sorted(C.get("seasons") or {})}
        C.setdefault("merged_from", []).append({
            "person": a, "merge_id": d["merge_id"], "decided_at": d["decided_at"],
            "evidence": d["why"], "seasons_added": sorted(seasons_added),
            "stint_fields_taken": took, "person_values_added": added,
            "_the_absorbed_record_is_kept_whole_under_its_own_id": True})
        A["merged_into"] = {"person": c, "merge_id": d["merge_id"],
                            "_this_record_is_kept_whole_and_is_not_deleted": True}
        applied.append(d["merge_id"])
    return applied, missing


def main():
    index = json.load(open(IDXP))
    merges = json.load(open(MP))
    before = summary(index)
    reversed_ = undo(index)
    clean = summary(index)
    applied, missing = apply(index, merges)
    after = summary(index)
    rep = {"contributions_reversed_first": reversed_, "merges_applied": len(applied),
           "merges_whose_people_are_missing": missing,
           "people": {"before": before["people"], "after": after["people"]},
           "club_seasons": {"before_this_run": before["seasons"], "unmerged_base": clean["seasons"],
                            "after": after["seasons"]},
           "person_values": {"unmerged_base": clean["values"], "after": after["values"]},
           "people_carrying_merged_from": sum(1 for k, v in index.items()
                                              if k != "_clubs" and isinstance(v, dict) and v.get("merged_from")),
           "people_carrying_merged_into": sum(1 for k, v in index.items()
                                              if k != "_clubs" and isinstance(v, dict) and v.get("merged_into"))}
    print(json.dumps(rep, indent=1))
    if "--report" in sys.argv:
        json.dump(rep, open(sys.argv[sys.argv.index("--report") + 1], "w"), indent=1)
    if "--write" in sys.argv:
        IO.save_index(index)
        print("wrote", IDXP)
    else:
        print("(dry run: pass --write to change the index)")


def summary(index):
    ppl = [v for k, v in index.items() if k != "_clubs" and isinstance(v, dict)]
    return {"people": len(ppl), "seasons": sum(len(v.get("seasons") or {}) for v in ppl),
            "values": sum(len(x) for v in ppl for x in (v.get("person") or {}).values())}


if __name__ == "__main__":
    main()
