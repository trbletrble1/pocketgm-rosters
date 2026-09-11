"""Apply build/club-key-normalisation.json to the person index.

Reverses every rewrite it has already recorded before applying the current set, so
it is idempotent AND deleting a decision genuinely un-normalises that key.

The index is left UNMERGED. Run order, from the declaration:
    src/apply_club_keys.py --write
    src/merge_people.py --write
    src/apply_person_merges.py --write

NOTHING IS LOST. Each normalised season carries `_club_as_printed`, so a reader can
still see that the source said Bisons, and the person carries the list of rewrites.

  python3 src/apply_club_keys.py [--write]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import apply_person_merges as AP
import index_io as IO                  # atomic index write

NP = os.path.join(BASE, "build", "club-key-normalisation.json")


def undo(index):
    n = 0
    for pid, p in index.items():
        if pid == "_clubs" or not isinstance(p, dict): continue
        for r in reversed(p.pop("_club_key_normalisations", []) or []):
            # the note says which dict the rewrite was applied in; notes written before
            # 2026-09-11 carry none and were all applied in `seasons`
            ss = p.get(r.get("dict", "seasons")) or {}
            if r.get("joined_an_existing_season"):
                tgt = ss.get(r["to"])
                if tgt:
                    for scope, f in r.get("fields_taken", []): (tgt.get(scope) or {}).pop(f, None)
                ss[r["from"]] = r["original_record"]
            elif r["to"] in ss:
                rec = ss.pop(r["to"]); rec.pop("_club_as_printed", None); ss[r["from"]] = rec
            n += 1
        for dn in ("seasons", "coaching_seasons"):
            if isinstance(p.get(dn), dict):
                p[dn] = {k: p[dn][k] for k in sorted(p[dn])}
    return n


def _bare(k):
    """`COACHES|y1969|X` -> `COACHES|1969|X`: the year form coaching_seasons uses since 2026-09-09."""
    lg, y, c = k.split("|", 2)
    return f"{lg}|{y[1:5] if y.startswith('y') and y[1:5].isdigit() else y}|{c}"


def apply(index, decisions, account=None):
    """`account`, if a list, receives one outcome per decided rewrite (index_io.write_account)."""
    applied, missing = 0, []
    by_person = collections.defaultdict(list)
    for r in decisions["rewrites"]: by_person[r["person"]].append(r)
    for pid, rs in by_person.items():
        p = index.get(pid)
        if not p:
            missing.append(pid)
            if account is not None:
                account += [{"decision": f"{r['person']}:{r['from']}", "outcome": "skipped", "expected": 1, "moved": 0,
                             "reason": "the person is not in the index", "legitimate": True} for r in rs]
            continue
        for r in rs:
            # BOTH DICTS (Ryan, 2026-09-11). The 9 September shape change moved coaching keys into
            # `coaching_seasons`, written with a bare year; this read `seasons` only and skipped
            # 658 of its 677 rewrites without a word. A rewrite is applied in whichever dict holds
            # its from-key -- in `coaching_seasons` under the bare-year form -- and the note says
            # which, so undo() reverses it exactly.
            if r["from"] in (p.get("seasons") or {}):
                dn, fk, tk = "seasons", r["from"], r["to"]
            elif _bare(r["from"]) in (p.get("coaching_seasons") or {}):
                dn, fk, tk = "coaching_seasons", _bare(r["from"]), _bare(r["to"])
            else:
                if account is not None:
                    held = r["to"] in (p.get("seasons") or {}) or _bare(r["to"]) in (p.get("coaching_seasons") or {})
                    why, ok = (("already applied", False) if held else
                               ("the person holds neither key: the season this rewrite named is no longer in the index", True))
                    account.append({"decision": f"{pid}:{r['from']}", "outcome": "skipped", "expected": 1, "moved": 0,
                                    "reason": why, "legitimate": ok})
                continue
            ss = p[dn]
            if account is not None:
                account.append({"decision": f"{pid}:{r['from']}", "outcome": "applied", "expected": 1, "moved": 1,
                                "reason": None, "legitimate": True, "dict": dn})
            rec = ss.pop(fk)
            note = {"from": fk, "to": tk, "dict": dn, "decided_from": r["from"], "decided_to": r["to"],
                    "kind": r["kind"], "club_as_printed": r["club_as_printed"], "evidence": r["evidence"]}
            r = {**r, "from": fk, "to": tk}
            if r["to"] in ss:
                tgt = ss[r["to"]]; taken = []
                for scope in ("stint", "stats"):
                    for f, v in (rec.get(scope) or {}).items():
                        if f not in (tgt.get(scope) or {}):
                            tgt.setdefault(scope, {})[f] = v; taken.append([scope, f])
                note.update(joined_an_existing_season=True, fields_taken=taken,
                            original_record=json.loads(json.dumps(rec)))
            else:
                rec["_club_as_printed"] = r["club_as_printed"]
                ss[r["to"]] = rec
            p.setdefault("_club_key_normalisations", []).append(note)
            applied += 1
        for dn in ("seasons", "coaching_seasons"):
            if isinstance(p.get(dn), dict):
                p[dn] = {k: p[dn][k] for k in sorted(p[dn])}
    return applied, missing


def summary(index):
    ppl = [v for k, v in index.items() if k != "_clubs" and isinstance(v, dict)]
    return {"people": len(ppl), "seasons": sum(len(v.get("seasons") or {}) for v in ppl)}


def main():
    index = json.load(open(AP.IDXP))
    merges = json.load(open(AP.MP))
    D = json.load(open(NP))
    AP.undo(index)                          # merges OFF; this layer sits under them
    before = summary(index)
    rev = undo(index)
    base = summary(index)
    acct = []
    applied, missing = apply(index, D, account=acct)
    IO.write_account("apply_club_keys", acct, run="write" if "--write" in sys.argv else "dry")
    after = summary(index)
    absorbed = {d["absorbed_person"] for d in merges["merges"]}
    touched = {r["person"] for r in D["rewrites"]}
    rep = {"rewrites_reversed_first": rev, "rewrites_applied": applied,
           "people_touched": len(touched), "absorbed_people_touched": len(touched & absorbed),
           "people_missing": missing,
           "club_seasons": {"unmerged_before": before["seasons"], "unnormalised_base": base["seasons"],
                            "after": after["seasons"]},
           "index_left": "unmerged - run merge_people.py then apply_person_merges.py"}
    print(json.dumps(rep, indent=1))
    if "--write" in sys.argv:
        IO.save_index(index); print("wrote", AP.IDXP)
    else:
        print("(dry run: pass --write)")


if __name__ == "__main__":
    main()
