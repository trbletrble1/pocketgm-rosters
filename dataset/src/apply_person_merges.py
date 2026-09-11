"""Apply declarations/person-merge-decisions.json to build-reports/person-index.json.

THE DECISIONS ARE A DECLARATION (Ryan, 2026-09-11). They used to live only in the untracked
build/person-merges.json, which merge_people.py regenerated -- and could no longer regenerate
faithfully. A decision is a record, not a derivation: it is in git now, and read from there.

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
MP = os.path.join(BASE, "declarations", "person-merge-decisions.json")


def undo(index):
    """Reverse every contribution the index records. Returns how many it reversed."""
    n = 0
    for pid, v in index.items():
        if pid == "_clubs" or not isinstance(v, dict): continue
        for c in v.pop("merged_from", []) or []:
            # an added key is a bare string (written before 2026-09-11, always in `seasons`) or a
            # [dict, key] pair (since): the applier now writes into either dict
            for k in c.get("seasons_added", []):
                dn, kk = (k if isinstance(k, list) else ("seasons", k))
                (v.get(dn) or {}).pop(kk, None)
            for k, fields in (c.get("stint_fields_taken") or {}).items():
                sd = (v.get("seasons") or {}).get(k) or (v.get("coaching_seasons") or {}).get(k)
                if not sd: continue
                for scope, f in fields: (sd.get(scope) or {}).pop(f, None)
            for f, vals in (c.get("person_values_added") or {}).items():
                cur = (v.get("person") or {}).get(f)
                if not cur: continue
                v["person"][f] = [x for x in cur if x not in vals]
                if not v["person"][f]: v["person"].pop(f)
            for dn in c.get("dicts_created", []):       # only a dict the merge itself created, and only if empty
                if v.get(dn) == {}: v.pop(dn)
            n += 1
    for pid, v in index.items():
        if pid != "_clubs" and isinstance(v, dict): v.pop("merged_into", None)
    return n


def _bare(k):
    lg, y, c = k.split("|", 2)
    return f"{lg}|{y[1:5] if y.startswith('y') and y[1:5].isdigit() else y}|{c}"


def _account_merge(d, A, C, seasons_added):
    """One outcome per decision: what it recorded it would move, what moved, and why not."""
    rw = {_bare(f): _bare(t) for f, t in d["contribution"]["season_key_rewrites"]}
    gained = {_bare(k) for k in d["contribution"]["seasons_gained_from_absorbed"]}
    held_c = {_bare(k) for k in list(C.get("seasons") or {}) + list(C.get("coaching_seasons") or {})}
    moved = len(seasons_added)
    todo = gained - {_bare(k[1] if isinstance(k, list) else k) for k in seasons_added}
    left = todo - held_c
    if not gained or not left and moved == len(gained):
        return {"decision": d["merge_id"], "outcome": "applied", "expected": len(gained), "moved": moved,
                "reason": None, "legitimate": True}
    if not left:
        return {"decision": d["merge_id"], "outcome": "partly_applied", "expected": len(gained), "moved": moved,
                "reason": "every recorded club-season is already held by the canonical person", "legitimate": True}
    in_cs = {rw.get(_bare(k), _bare(k)) for k in (A.get("coaching_seasons") or {})}
    why = ("the recorded club-seasons are held in coaching_seasons, a dict this applier does not read"
           if left & in_cs else "the recorded club-seasons are not in the absorbed record")
    return {"decision": d["merge_id"], "outcome": "partly_applied" if moved else "skipped",
            "expected": len(gained), "moved": moved, "reason": why, "legitimate": False,
            "not_moved": len(left), "rewrites_recorded": len(d["contribution"]["season_key_rewrites"])}


def apply(index, merges, account=None):
    """`account`, if a list, receives one outcome per decision (index_io.write_account)."""
    applied, missing = [], []
    for d in merges["merges"]:
        c, a = d["canonical_person"], d["absorbed_person"]
        if c not in index or a not in index:
            missing.append(d["merge_id"])
            if account is not None:
                account.append({"decision": d["merge_id"], "outcome": "skipped", "expected": 0, "moved": 0,
                                "reason": "a constituent is not in the index", "legitimate": True})
            continue
        C, A = index[c], index[a]
        # BOTH DICTS (Ryan, 2026-09-11). The absorbed halves are Coaching Tree records, and the
        # 9 September shape change moved every one of their keys into `coaching_seasons` with a
        # bare year; this read `seasons` only, so for two days all 93 merges moved nothing. The
        # recorded keys and rewrites are compared in the bare-year form, an absorbed key is found
        # in whichever dict holds it, and it lands in the SAME dict on the canonical.
        rw = {_bare(f): _bare(t) for f, t in d["contribution"]["season_key_rewrites"]}
        gained = {_bare(k) for k in d["contribution"]["seasons_gained_from_absorbed"]}
        took = {_bare(k): v for k, v in d["contribution"]["stint_fields_taken_from_absorbed"].items()}
        seasons_added = []; dicts_created = []
        for dn in ("seasons", "coaching_seasons"):
            for k, sd in (A.get(dn) or {}).items():
                ck = rw.get(_bare(k), _bare(k))
                if ck in gained and ck not in (C.get(dn) or {}):
                    # A DICT THE MERGE CREATES IS RECORDED, so undo() can remove it and the round trip
                    # is exact: the first shape-aware version left one person an empty
                    # `coaching_seasons` he did not have before the merge.
                    if dn not in C: C[dn] = {}; dicts_created.append(dn)
                    C[dn][ck] = json.loads(json.dumps(sd)); seasons_added.append([dn, ck])
        for k, fields in took.items():
            dn = "seasons" if k in (C.get("seasons") or {}) else "coaching_seasons"
            cs = (C.get(dn) or {}).get(k)
            src = next((sd for d2 in ("seasons", "coaching_seasons") for kk, sd in (A.get(d2) or {}).items()
                        if rw.get(_bare(kk), _bare(kk)) == k), None)
            if not cs or not src: continue
            for scope, f in fields:
                if f not in (cs.get(scope) or {}): cs.setdefault(scope, {})[f] = (src.get(scope) or {}).get(f)
        added = {}
        for f, vals in d["contribution"]["person_values_added_from_absorbed"].items():
            cur = (C.get("person") or {}).setdefault(f, [])
            new = [x for x in vals if x not in cur]
            if new: cur.extend(new); added[f] = new
        for dn in ("seasons", "coaching_seasons"):
            if isinstance(C.get(dn), dict): C[dn] = {k: C[dn][k] for k in sorted(C[dn])}
        C.setdefault("merged_from", []).append({
            "person": a, "merge_id": d["merge_id"], "decided_at": d["decided_at"],
            "evidence": d["why"], "seasons_added": sorted(seasons_added),
            "stint_fields_taken": took, "person_values_added": added, "dicts_created": dicts_created,
            "_the_absorbed_record_is_kept_whole_under_its_own_id": True})
        A["merged_into"] = {"person": c, "merge_id": d["merge_id"],
                            "_this_record_is_kept_whole_and_is_not_deleted": True}
        applied.append(d["merge_id"])
        if account is not None:
            account.append(_account_merge(d, A, C, seasons_added))
    return applied, missing


def main():
    index = json.load(open(IDXP))
    merges = json.load(open(MP))
    before = summary(index)
    reversed_ = undo(index)
    clean = summary(index)
    acct = []
    applied, missing = apply(index, merges, account=acct)
    IO.write_account("apply_person_merges", acct, run="write" if "--write" in sys.argv else "dry",
                     rewrites_recorded=sum(len(d["contribution"]["season_key_rewrites"]) for d in merges["merges"]))
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
