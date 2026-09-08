"""Apply build/assistants-identity.json to build-reports/identity.json.

WHY AN APPLIER AND NOT unify_identity.py. unify_identity assigns global ids by
ENUMERATION ORDER (P_000001, P_000002, ... over its groups), so re-running it
against a changed store set renumbers every person in the archive -- and every
P_ id in every build store, the person index, the merges and the promotions points
at the old numbering. identity.json on disk is the authority and is edited in
place, exactly as the person merges are.

Idempotent both ways: undo removes every local this file has recorded before
applying the current set, so deleting a decision genuinely un-joins it.

NOTHING IS OVERWRITTEN. A join adds one (store, local) pair to a person who already
has a source-native id, and records the evidence per local under `local_evidence`.
The person's slugs, its other locals and its `evidence` field are untouched.

  python3 src/apply_assistants_identity.py [--write]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO

IDP = os.path.join(BASE, "build-reports", "identity.json")
DP = os.path.join(BASE, "build", "assistants-identity.json")
MARK = "local_evidence"


def undo(idm):
    n = 0
    for gid, v in idm.items():
        ev = v.get(MARK) or {}
        drop = {tuple(k.split("|", 1)) for k, e in ev.items() if e.get("applied_by") == "apply_assistants_identity"}
        if not drop: continue
        v["local"] = [l for l in v["local"] if tuple(l) not in drop]
        for k in [k for k, e in ev.items() if e.get("applied_by") == "apply_assistants_identity"]: ev.pop(k); n += 1
        if not ev: v.pop(MARK, None)
    return n


def apply(idm, D):
    applied, missing, already = 0, [], 0
    for j in D["joins"]:
        v = idm.get(j["person"])
        if not v: missing.append(j["person"]); continue
        pair = [j["store"], j["local"]]
        if pair in v["local"]: already += 1; continue
        v["local"] = sorted(v["local"] + [pair])
        v.setdefault(MARK, {})[f"{j['store']}|{j['local']}"] = {
            "evidence": j["evidence"], "why": j["why"], "club_years_matched": j["club_years_matched"],
            "source_record": j["source_record"], "decided_at": j["decided_at"], "applied_by": "apply_assistants_identity"}
        applied += 1
    return applied, missing, already


def main():
    idm = json.load(open(IDP)); D = json.load(open(DP))
    before = sum(len(v["local"]) for v in idm.values())
    rev = undo(idm)
    applied, missing, already = apply(idm, D)
    after = sum(len(v["local"]) for v in idm.values())
    slugless = [j["person"] for j in D["joins"] if not idm.get(j["person"], {}).get("slugs")]
    rep = {"joins_decided": len(D["joins"]), "removed_first": rev, "applied": applied, "already_present": already,
           "people_missing": missing, "local_records": {"before": before, "after": after},
           "targets_without_a_source_native_id": slugless,
           "_why_that_matters": "gate_identity: a group holding more than one local must be held together by a slug. "
                                "Every target here already has one; a join is recorded beside it with its own evidence, never as a slug."}
    print(json.dumps(rep, indent=1))
    if missing or slugless: print("REFUSING TO WRITE: a target is missing or has no source-native id", file=sys.stderr); return 1
    if "--write" in sys.argv:
        IO.dump_atomic(idm, IDP); print("wrote", IDP)
    else: print("(dry run: pass --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
