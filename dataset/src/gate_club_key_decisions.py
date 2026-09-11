"""Gate for patch 4 of the club job: the club-key decisions are made through the club table.

  D1  the table-driven decider reproduces build/club-key-normalisation.json: the same (person, from, to,
      kind) set for rewrites and for merge-time records -- every difference listed
  D2  the refused set is the same or every difference is listed with the table's reason
  D3  build_clubs.py reads no decisions file; the table's source_defect strings carry their corroboration
      count; the four known defects (Bisons->BUF, Bulldogs->CLE, Hornets->OAK, Alouettes 1982->CFLMTL) are
      wrong_for_season strings on the right clubs
  D4  applying the regenerated decisions to a COPY of the index reproduces the index byte-for-byte
      (nothing is written)
  D5  gate_club_keys and gate_coach_runs pass

  python3 src/gate_club_key_decisions.py
"""
import os, sys, json, subprocess, collections, hashlib

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import normalise_club_keys as N, apply_club_keys as CKA, apply_person_merges as AP
from clubs import Clubs, norm

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def main():
    D = json.load(open(CKA.NP)); E = N.build()
    # Compared in the BARE-YEAR form (2026-09-11): the decisions were recorded as `COACHES|y1969|X`,
    # and since the 9 September shape change the index writes `COACHES|1969|X`. One key, two spellings.
    key = lambda r: (r["person"], CKA._bare(r["from"]), CKA._bare(r["to"]), r["kind"])
    print(f"  population: {sum(len(v.get('seasons') or {}) for v in json.load(open(AP.IDXP)).values() if isinstance(v, dict)):,} "
          "keys in seasons and the coaching_seasons below are what the regenerated decisions were derived from")
    print("D1  the decisions reproduce")
    for name in ("rewrites", "applied_when_merging"):
        a = {key(r): r for r in D[name]}; b = {key(r): r for r in E[name]}
        gone, new = sorted(set(a) - set(b)), sorted(set(b) - set(a))
        check(not gone and not new, f"{name}: {len(a)} decided before, {len(b)} now, identical" if not gone and not new
              else f"{name}: {len(gone)} no longer decided {gone[:4]}; {len(new)} newly decided {new[:4]}")
        ev = [(k, a[k]["evidence"], b[k]["evidence"]) for k in set(a) & set(b) if a[k]["kind"] == "source_defect" and a[k]["evidence"] != b[k]["evidence"]]
        check(not ev, f"{name}: every source defect carries the same corroboration count" if not ev else f"{name}: {len(ev)} corroboration counts differ, e.g. {ev[:2]}")
    print("D2  the refused set, against the old decider computed here")
    from club_keys import ClubKeys
    idx0 = json.load(open(AP.IDXP)); cl0 = idx0.pop("_clubs", {}); CKA.undo(idx0); AP.undo(idx0)
    view = {}
    for d in json.load(open(AP.MP))["merges"]:
        view[d["canonical_person"]] = {dn: {**((idx0.get(d["canonical_person"]) or {}).get(dn) or {}),
                                            **((idx0.get(d["absorbed_person"]) or {}).get(dn) or {})}
                                       for dn in ("seasons", "coaching_seasons")}
    for pid, p in idx0.items():
        if pid not in view and isinstance(p, dict): view[pid] = p
    old_ref = {(r[2], r[1]) for r in ClubKeys(view, cl0).census(idx0)}
    new_ref = set(); walked = collections.Counter()
    decided = {(r["person"], CKA._bare(r["from"])) for r in E["rewrites"] + E["applied_when_merging"]}
    for pid, p in idx0.items():
        if not isinstance(p, dict): continue
        # both dicts (2026-09-11): walking `seasons` only, both sides of D2 lost every coaching refusal
        # together and agreed on what was left
        for dn in ("seasons", "coaching_seasons"):
            for k in p.get(dn) or {}:
                walked[dn] += 1
                lg, y, club = k.split("|", 2); yr = y[1:5] if y.startswith("y") else y
                if yr.isdigit() and f"{club}|{yr}" not in cl0 and (pid, CKA._bare(k)) not in decided: new_ref.add((club, yr))
    print(f"  D2 walked {sum(walked.values()):,} keys ({walked['seasons']:,} seasons, {walked['coaching_seasons']:,} coaching_seasons)")
    only_old, only_new = sorted(old_ref - new_ref), sorted(new_ref - old_ref)
    named = json.load(open(os.path.join(BASE, "declarations", "club-key-normalisation.json"))).get("WHERE_THE_TABLE_AND_THE_OLD_DECIDER_DIVERGE", {})
    def declared(club, yr): return any(club in k and (yr in k or " " + yr not in k and yr in k.split()) for k in named if not k.startswith("_")) or any(club in k and yr in k for k in named)
    undeclared = [x for x in only_old + only_new if not declared(x[0], x[1])]
    check(not undeclared,
          (f"{len(old_ref)} refused by the old decider, {len(new_ref)} by the table; {len(only_old) + len(only_new)} divergence(s), every one declared with its reason: "
           + "; ".join(f"{c} {y}" for c, y in only_old + only_new)) if not undeclared
          else f"undeclared divergence(s): {undeclared[:6]} -- name each in declarations/club-key-normalisation.json WHERE_THE_TABLE_AND_THE_OLD_DECIDER_DIVERGE with its reason")
    print("D3  the table stands on its own")
    src = open(os.path.join(HERE, "build_clubs.py")).read()
    check("club-key-normalisation.json" not in src, "build_clubs.py does not read the decisions file")
    C = Clubs()
    want = {("Buffalo Bisons", "BUF", 1986), ("Cleveland Bulldogs", "CLE", 1990), ("Oakland Hornets", "OAK", 1965), ("Montreal Alouettes", "CFLMTL", 1982)}
    for nm, code, y in sorted(want):
        r = C.resolve(nm, y)
        st = next((s for s in C.by_id[r[0]]["strings"] if norm(s["string"]) == norm(nm) and s["first"] <= y <= s["last"] and s["kind"] == "wrong_for_season"), None) if r else None
        check(bool(r) and C.code_for(r[0], y) == code and st is not None and st.get("person_seasons"),
              f"{nm} {y} -> {code} as wrong_for_season, corroborated by {st.get('person_seasons') if st else None} person-seasons")
    check(not C.T["counts"]["strings_by_source"].get("normalisation"), "no string is sourced from the decisions file")
    print("D4  the regenerated decisions reproduce the index on a copy")
    idx = json.load(open(AP.IDXP)); before = hashlib.sha256(json.dumps(idx, sort_keys=True).encode()).hexdigest()
    M = json.load(open(AP.MP)); AP.undo(idx); CKA.undo(idx)
    acct = []; CKA.apply(idx, E, account=acct); AP.apply(idx, M)
    by_dict = collections.Counter(o.get("dict") for o in acct if o["outcome"] == "applied")
    print(f"  D4 regenerated rewrites applied to the copy: {sum(by_dict.values()):,} of {len(acct):,} "
          f"({by_dict.get('seasons', 0):,} in seasons, {by_dict.get('coaching_seasons', 0):,} in coaching_seasons)")
    for p in idx.values():
        for dn in ("seasons", "coaching_seasons"):
            if isinstance(p, dict) and isinstance(p.get(dn), dict): p[dn] = {k: p[dn][k] for k in sorted(p[dn])}
    after = hashlib.sha256(json.dumps(idx, sort_keys=True).encode()).hexdigest()
    live = hashlib.sha256(open(AP.IDXP, "rb").read()).hexdigest()
    check(before == after, "undo + apply(regenerated) + merges reproduces the index exactly, in memory" if before == after else "the index would change under the regenerated decisions")
    check(hashlib.sha256(open(AP.IDXP, "rb").read()).hexdigest() == live, "the index file was not written")
    print("D5  the other gates")
    for g in ("gate_club_keys.py", "gate_coach_runs.py"):
        out = subprocess.run([sys.executable, os.path.join(HERE, g)], capture_output=True, text=True).stdout
        ok = "every property holds" in out or "GATE: pass" in out
        check(ok, f"{g} passes" if ok else out[-600:])
    print()
    if fails: print(f"CLUB KEY DECISIONS GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print("CLUB KEY DECISIONS GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main())
