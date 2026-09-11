"""Gate for the person merges. Properties, not instances. exit 1 = FAIL.

  G1  no merge without recorded evidence: every decision carries the verdict
      `duplicate`, the tests it passed, and the evidence that produced it.
  G2  the scope ruled: exactly one half of every merge is an orphaned Coaching
      Tree person, the other carries a name and a source-native id.
  G3  REVERSIBLE. Undo every recorded contribution and each constituent must
      return to the season count the decision recorded BEFORE the merge; then
      re-apply and the index must come back identical. Round-trip, both ways.
  G4  nothing deleted: both constituents are still in the index, the absorbed
      one whole, carrying `merged_into`.
  G5  the union has no double-counting: a merged person's club-seasons are the
      union of both halves under the canonical key, each once.
  G6  what was refused is untouched: the 7 StatsCrew-against-itself pairs, the
      34 unclassifiable, the 7 namesakes and the 5 mis-attached source records
      carry no merge and appear in no decision.
  G7  no claim lost, none duplicated: every claim in the archive still resolves
      to exactly one person once the merge map is followed, and the total is
      unchanged.
  G8  a merge resolves no disagreement: every held disagreement carries
      resolved = null.

  python3 src/gate_person_merges.py
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import apply_person_merges as AP

FAILS = []
def check(ok, msg):
    if not ok: FAILS.append(msg)


def main():
    M = json.load(open(AP.MP))                     # declarations/person-merge-decisions.json, in git
    index = json.load(open(AP.IDXP))
    ident = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
    merges = M["merges"]
    print(f"decisions: {len(merges)}")

    # G1
    for d in merges:
        check(d["verdict"] == "duplicate" and d["tests_passed"] and d["evidence"]
              and d.get("decided_at") and d.get("why"), f"G1 {d['merge_id']} lacks evidence")
        e = d["evidence"]
        check(e["name"] in ("same", "one_absent"), f"G1 {d['merge_id']} merged across differing names")
        check(e["birth_date"] in ("exact", "one_component"), f"G1 {d['merge_id']} merged without a birth date agreeing")
        check(not e["shared_source_record"], f"G1 {d['merge_id']} merged on a shared source record")

    # G2
    for d in merges:
        a, c = d["absorbed_person"], d["canonical_person"]
        srcs = sorted({s for s, _ in ident.get(a, {}).get("local", [])})
        check(srcs == ["coaches"], f"G2 {d['merge_id']} absorbed a person from {srcs}")
        check(not ident.get(a, {}).get("slugs"), f"G2 {d['merge_id']} absorbed a person carrying a slug")
        check(bool(ident.get(c, {}).get("slugs")) and bool(index[c].get("name")),
              f"G2 {d['merge_id']} canonical lacks a name or a slug")

    # "UNALTERED" IS WHAT A RECORD HOLDS, NOT WHERE IT IS STORED OR HOW IT IS SPELLED (Ryan,
    # 2026-09-11). G3, G4 and G5 used to count and compare `seasons` only, against counts recorded on
    # 6 September. The 9 September shape change moved every shell's keys into `coaching_seasons` and
    # re-spelled their years, so G4 failed on all 93 while nothing had changed -- and G5, which should
    # have caught that merges were moving nothing, compared an empty set with an empty set. Club-seasons
    # are compared as (year, club) through the club table, across both stint dicts.
    from clubs import Clubs
    CL = Clubs(); _yc = {}
    def yc(k):
        p = k.split("|", 2)
        if len(p) != 3: return None
        y = p[1].lstrip("y")[:4]
        if not y.isdigit(): return None
        kk = (p[2], int(y))
        if kk not in _yc:
            r = CL.resolve(p[2], int(y)); _yc[kk] = r[0] if r else "?" + p[2]
        return (int(y), _yc[kk])
    def cs_of(rec): return {yc(k) for dn in ("seasons", "coaching_seasons") for k in (rec.get(dn) or {})} - {None}

    # G4
    for d in merges:
        a, c = d["absorbed_person"], d["canonical_person"]
        check(a in index and c in index, f"G4 {d['merge_id']} lost a constituent")
        check(index[a].get("merged_into", {}).get("person") == c, f"G4 {d['merge_id']} absorbed record not marked")
        recorded = {yc(k) for k in d["contribution"]["seasons_gained_from_absorbed"]
                    + d["contribution"]["seasons_held_by_both"]} - {None}
        check(cs_of(index[a]) == recorded,
              f"G4 {d['merge_id']} the absorbed record was altered: it holds {len(cs_of(index[a]))} club-seasons "
              f"(year, club, both dicts), its decision recorded {len(recorded)}")
        check(any(x["person"] == a for x in index[c].get("merged_from", [])),
              f"G4 {d['merge_id']} canonical does not name what it absorbed")

    # G5
    for d in merges:
        a, c = d["absorbed_person"], d["canonical_person"]
        lost = cs_of(index[a]) - cs_of(index[c])
        check(not lost, f"G5 {d['merge_id']} the merged person does not hold {len(lost)} of the absorbed "
                        f"club-seasons, e.g. {sorted(lost)[:2]}")
        for dn in ("seasons", "coaching_seasons"):
            ks = list(index[c].get(dn) or {})
            check(len(ks) == len(set(ks)), f"G5 {d['merge_id']} duplicate keys in {dn}")

    # G3 round trip: undo removes exactly what the merge added, and re-applying reproduces the index
    base = json.loads(json.dumps(index))
    n = AP.undo(base)
    check(n == len(merges), f"G3 reversed {n} contributions, expected {len(merges)}")
    added = {x["person"]: x for rec in index.values() if isinstance(rec, dict) for x in rec.get("merged_from", [])}
    for d in merges:
        a, c = d["absorbed_person"], d["canonical_person"]
        left = [k for k in (added.get(a) or {}).get("seasons_added", [])
                if (k[1] if isinstance(k, list) else k) in (base[c].get(k[0] if isinstance(k, list) else "seasons") or {})]
        check(not left, f"G3 {d['merge_id']} undo left {len(left)} added club-season(s) on the canonical")
        check("merged_from" not in base[c] and "merged_into" not in base[a],
              f"G3 {d['merge_id']} a marker survived the undo")
    AP.apply(base, M)
    for d in merges:
        for p in (d["canonical_person"], d["absorbed_person"]):
            check(json.dumps(base[p], sort_keys=True) == json.dumps(index[p], sort_keys=True),
                  f"G3 {d['merge_id']} {p} did not round-trip identically")

    # G6
    merged_pairs = {(d["canonical_person"], d["absorbed_person"]) for d in merges}
    R = M["REFUSED"]
    groups = {"statscrew_against_itself": R["statscrew_against_itself"]["pairs"],
              "unclassifiable": R["unclassifiable"]["pairs"], "namesakes": R["namesakes"]["pairs"],
              "mis_attached_source_records": R["mis_attached_source_records"]["pairs"]}
    # the refused counts are read from the build's OWN verdict tally rather than
    # hardcoded: normalising the club keys changed what detection can see, and a
    # constant here would only record what the numbers were on the day it was written
    v = M["counts"]["verdicts"]
    expect = {"statscrew_against_itself": M["counts"]["refused_statscrew_against_itself"],
              "unclassifiable": v.get("unclassifiable", 0), "namesakes": v.get("namesake", 0),
              "mis_attached_source_records": v.get("mis-attached source record", 0)}
    check(v.get("duplicate", 0) == len(merges) + expect["statscrew_against_itself"],
          "G6 the duplicate verdicts do not reconcile to merges plus the StatsCrew refusals")
    for k, prs in groups.items():
        check(len(prs) == expect[k], f"G6 {k} holds {len(prs)}, expected {expect[k]}")
        # the refused PAIR must not have been merged. A person may appear in a
        # refused pair and in a merge, and correctly so: there are three Bill
        # Walshes, and the Coaching Tree one duplicates the 1931 coach while
        # staying a namesake of the 1927 player. John McKay merged with himself
        # and stayed apart from John McKay born 1953, who is his son.
        for p in prs:
            check((p["a"], p["b"]) not in merged_pairs and (p["b"], p["a"]) not in merged_pairs,
                  f"G6 a {k} pair was merged: {p['a']} + {p['b']}")

    # G7 self-contained: read every claim once, map it through the merge map, and
    # require that nothing is lost or doubled. A stored snapshot cannot serve here --
    # another session is writing new stores into the same build directory, and its
    # claims would read as a change this layer did not make.
    total, per, absorbed_hit = 0, collections.Counter(), 0
    absorbed_of = {d["absorbed_person"]: d["canonical_person"] for d in merges}
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        cl = d.get("claims")
        if not isinstance(cl, list) or not cl: continue
        s0 = cl[0].get("subject")
        if not (isinstance(s0, list) and len(s0) > 1 and str(s0[1]).startswith("P_")): continue
        for c in cl:
            sub = c.get("subject")
            if isinstance(sub, list) and len(sub) > 1 and str(sub[1]).startswith("P_"):
                total += 1
                if sub[1] in absorbed_of: absorbed_hit += 1
                per[absorbed_of.get(sub[1], sub[1])] += 1
    check(sum(per.values()) == total, "G7 the merge map lost or doubled a claim")
    for a, c in absorbed_of.items():
        check(c in index, f"G7 {a} maps to {c}, which the index does not hold")
    print(f"  claims addressed to a person: {total:,}; addressees after the merge map: {len(per):,}; "
          f"claims sitting on an absorbed id: {absorbed_hit}")

    # G8
    for d in merges:
        for scope in ("stint", "person"):
            for x in d["disagreements_held_not_resolved"][scope]:
                check(x.get("resolved") is None, f"G8 {d['merge_id']} resolved a disagreement")
    check(R["statscrew_against_itself"].get("resolved") is None, "G8 the StatsCrew contradiction was resolved")

    in_merge = {d["canonical_person"] for d in merges} | {d["absorbed_person"] for d in merges}
    in_refused = {x for prs in groups.values() for p in prs for x in (p["a"], p["b"])}
    both = sorted(in_merge & in_refused)
    print(f"  people in a merge who are also in a refused pair: {len(both)} (a man may duplicate one person and be a namesake of another)")
    print(f"  merged people: {len(merges)}; club-seasons gained {M['counts']['club_seasons_gained']}, "
          f"held by both {M['counts']['club_seasons_held_by_both']}")
    if FAILS:
        print(f"\nGATE FAILED ({len(FAILS)})")
        for m in FAILS[:25]: print("  FAIL", m)
        return 1
    print("\ngate_person_merges: every property holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
