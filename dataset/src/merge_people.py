"""Decide which person records are one man, and record each decision.

A PROPOSER since 2026-09-11: the decisions are declarations/person-merge-decisions.json, in git,
and this writes only build/person-merge-proposals.json (what the rule would add or withdraw).
It used to write dataset/build/person-merges.json. Decides only; applying the decisions to
the index is apply_person_merges.py, and un-merging is deleting a decision and
running that again. See declarations/person-merges.json.

  python3 src/merge_people.py [--write]
"""
import os, sys, json, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from person_duplicates import Population, nclub, dparts

DECL = json.load(open(os.path.join(BASE, "declarations", "person-merges.json"), encoding="utf-8"))
DECIDED_AT = "2026-09-06"


class MergeError(Exception):
    pass


def canonical_season_key(key, name_to_code, mapped=None):
    """COACHES|y1969|Pittsburgh Steelers -> COACHES|y1969|PIT. A club-season written
    as a NAME by one source and a CODE by another is ONE club-season and must not be
    counted twice.

    The season-aware map in club_keys.py is asked first, because it also carries the
    SOURCE DEFECTS: Coaching Tree calls Buffalo's 1986 club the Bisons, which no
    name-to-code lookup can resolve, and without this the absorbed record's Bisons
    seasons arrive at the canonical as a second Buffalo club. The absorbed record
    itself is never rewritten -- it keeps what the source printed."""
    if mapped: return mapped
    lg, y, club = key.split("|", 2)
    yr = y[1:5] if y.startswith("y") else y
    if not yr.isdigit(): return key
    codes = name_to_code.get((nclub(club), yr), set())
    if len(codes) == 1 and club not in codes:
        return f"{lg}|{y}|{next(iter(codes))}"
    return key


def orphan_half(pop, pid):
    """An orphaned Coaching Tree person: no name in the index, and the Coaching Tree
    store is the only place he came from."""
    return (not pop.P[pid]["index_name"]) and pop.P[pid]["srcs"] == ["coaches"]


def build():
    pop = Population()
    # The club-key normalisation decisions, consumed rather than re-derived. They
    # carry the SOURCE DEFECTS -- 'Buffalo Bisons' for Buffalo's 1986 club -- which no
    # name-to-code lookup can resolve, and whose corroboration is only visible in the
    # MERGED index, so re-deriving them here from the unmerged base would find nothing.
    NORM = {}
    fp = os.path.join(BASE, "build", "club-key-normalisation.json")
    if os.path.exists(fp):
        D = json.load(open(fp))
        for r in D.get("rewrites", []) + D.get("applied_when_merging", []):
            NORM[(r["person"], r["from"])] = r["to"]
    verdicts, tests, shared = pop.run()
    IDX, P = pop.IDX, pop.P
    decisions, skipped = [], []
    for d in verdicts.get("duplicate", []):
        a, b = d["a"], d["b"]
        orph = [x for x in (a, b) if orphan_half(pop, x)]
        if len(orph) != 1:
            skipped.append({**{k: d[k] for k in ("a", "b", "why")},
                            "not_merged_because": ("both halves are archive people and the SOURCE asserts two men; "
                                                   "held as a source contradiction" if not orph else
                                                   "both halves are orphans")})
            continue
        absorbed = orph[0]; canonical = b if absorbed == a else a
        if not P[canonical]["index_name"]:
            skipped.append({"a": a, "b": b, "not_merged_because": "no half carries a name in the index"}); continue
        A, C = IDX[absorbed], IDX[canonical]
        rewrites, gained, shared_keys, stint_taken, stint_conflicts = [], [], [], {}, []
        # BOTH DICTS (Ryan, 2026-09-11). The absorbed halves are Coaching Tree records whose keys the
        # 9 September shape change moved into `coaching_seasons`; reading `seasons` only, every
        # proposed contribution came out empty (rewrites 1,929 -> 0, club-seasons gained 1,352 -> 0).
        items = [(dn, k, sd) for dn in ("seasons", "coaching_seasons") for k, sd in (A.get(dn) or {}).items()]
        for dn, k, sd in items:
            ck = canonical_season_key(k, pop.name_to_code, NORM.get((absorbed, k)))
            if ck != k: rewrites.append([k, ck])
            if ck in (C.get(dn) or {}):
                shared_keys.append(ck)
                cs = C[dn][ck]
                took = []
                for scope in ("stint", "stats"):
                    for f, v in (sd.get(scope) or {}).items():
                        cur = (cs.get(scope) or {}).get(f)
                        if cur is None: took.append([scope, f])
                        elif str(cur) != str(v):
                            stint_conflicts.append({"season": ck, "scope": scope, "field": f,
                                                    "canonical": cur, "absorbed": v, "resolved": None})
                if took: stint_taken[ck] = took
            else:
                gained.append(ck)
        # A DATE ALREADY HELD IS NOT A NEW VALUE. Coaching Tree writes 1932-01-05
        # where StatsCrew writes January 5, 1932: the same day in two notations.
        # Adding both would leave the merged Chuck Noll holding two birth dates and
        # looking contaminated. The suppressed form is recorded, not discarded.
        person_added, same_date_other_notation = {}, {}
        for f, vs in (A.get("person") or {}).items():
            have = list((C.get("person") or {}).get(f) or [])
            held_dates = {dparts(x) for x in have if dparts(x)}
            new = []
            for v in vs:
                if v in have: continue
                if f in ("birth_date", "death_date") and dparts(v) and dparts(v) in held_dates:
                    same_date_other_notation.setdefault(f, []).append(v); continue
                new.append(v)
            if new: person_added[f] = new
        # the same date in another notation is not a disagreement
        person_conflicts = []
        for f, vs in (A.get("person") or {}).items():
            have = (C.get("person") or {}).get(f)
            if not have: continue
            held = {dparts(x) for x in have if dparts(x)}
            new = [v for v in vs if v not in have and not (dparts(v) and dparts(v) in held)]
            if new:
                person_conflicts.append({"field": f, "canonical": have, "absorbed": new, "resolved": None})
        rec = pop.recovered.get(absorbed)
        decisions.append({
            "merge_id": f"PM_{len(decisions) + 1:04d}",
            "canonical_person": canonical, "absorbed_person": absorbed,
            "constituents": sorted([canonical, absorbed]),
            "name": P[canonical]["index_name"],
            "recovered_name": ({"value": rec[1], "read_from": rec[0], "source_record": rec[2]} if rec else None),
            "_recovered_name_is_for_matching_only": True,
            "verdict": d["verdict"], "why": d["why"], "evidence": d["evidence"],
            "tests_passed": d["tests_passed"],
            "decided_at": DECIDED_AT,
            "decided_by": "merge_people.py, on Ryan's ruling of 2026-09-06",
            "kind": "decided",
            "contribution": {
                "season_key_rewrites": rewrites,
                "seasons_gained_from_absorbed": sorted(gained),
                "seasons_held_by_both": sorted(shared_keys),
                "stint_fields_taken_from_absorbed": stint_taken,
                "person_values_added_from_absorbed": person_added,
                "absorbed_values_not_added_same_date_other_notation": same_date_other_notation},
            "disagreements_held_not_resolved": {"stint": stint_conflicts, "person": person_conflicts},
            "counts_before": {"canonical_seasons": len(C.get("seasons") or {}),
                              "absorbed_seasons": len(A.get("seasons") or {})},
            "reversal": {"absorbed_record_is_kept_whole": True,
                         "how": "delete this decision from build/person-merges.json and re-run "
                                "src/apply_person_merges.py; the contribution block names exactly what to subtract"}})
    out = {
        "declaration": "declarations/person-merges.json",
        "decided_at": DECIDED_AT,
        "merges": decisions,
        "REFUSED": {
            "statscrew_against_itself": {
                "_why": DECL["WHAT_IS_REFUSED"]["statscrew_against_itself"],
                "kind": "held source contradiction", "resolved": None,
                "pairs": [{"a": s["a"], "b": s["b"],
                           "a_slugs": IDX[s["a"]]["slugs"], "b_slugs": IDX[s["b"]]["slugs"],
                           "name": P[s["a"]]["index_name"], "birth_dates": [P[s["a"]]["bd_raw"], P[s["b"]]["bd_raw"]],
                           "the_contradiction": "StatsCrew's own counter separates namesakes, so two slugs assert "
                                                "two men; the shared exact birth date asserts one. Both records stand.",
                           "why_it_looked_like_one_man": s["why"]} for s in skipped]},
            "unclassifiable": {"_why": DECL["WHAT_IS_REFUSED"]["unclassifiable"],
                               "pairs": verdicts.get("unclassifiable", [])},
            "namesakes": {"_why": DECL["WHAT_IS_REFUSED"]["namesakes"], "pairs": verdicts.get("namesake", [])},
            "mis_attached_source_records": {"_why": DECL["WHAT_IS_REFUSED"]["mis_attached_source_records"],
                                            "kind": "source defect", "resolved": None,
                                            "records": {k: v for k, v in shared.items()},
                                            "pairs": verdicts.get("mis-attached source record", [])}},
        "OPEN_ITEMS": {
            "two_person_records_for_one_name_found_by_the_coach_ingest": {
                "_what": ("Ryan, 2026-09-11: to the merge queue, as questions. The PFA coach ingest's routes "
                          "name two DIFFERENT person records for one coach page, and neither is a merge shell "
                          "(unlike the 18 refused the same day, whose second id was their own shell). Whether "
                          "each pair is one man is a merge decision, not a route conflict, and nothing here "
                          "decides it."),
                "pairs": [
                    {"name": "Gino Cappelletti", "pfa_coach_page": "coaches/capp00600.html",
                     "by_playing_record": "P_001119", "by_name_and_coaching_club_season": "P_014230"},
                    {"name": "Dennis Meyer", "pfa_coach_page": "coaches/meye00200.html",
                     "by_playing_record_and_by_name_and_birth_date": "P_006344",
                     "by_name_and_coaching_club_season": "P_014610"}],
                "seen_since": "the 2026-09-09 coach store, where both were already route conflicts",
                "resolved": None},
            "media_guide_assistants_are_not_in_the_person_index": {
                "store": "build/assistants.json",
                "people": 447, "role_stints": 1086,
                "people_in_the_person_index": 0,
                "_what": "the media-guide assistant coaches never entered the person index at all. Their denotations are matched by name and stint-chain, carry no source-native id, and unify_identity.py therefore gave them no global person. This is ABSENCE, not duplication: there is nothing here to merge, and no claim of theirs is addressable by a person id.",
                "_not_part_of_this_merge": True, "resolved": None},
            "court_salaries_local_ids_do_not_match_the_store": {
                "store": "build/salaries.json",
                "people_in_the_index_from_this_store": 92,
                "whose_local_id_appears_in_the_store_denotations": 17,
                "_what": "75 of the 92 court-salaries people cannot be traced back to the man the court named: the local id the index holds does not appear among that store's own denotations, so no name can be recovered for them. A broken link inside the salaries ingest, separate from duplication.",
                "resolved": None},
            "a_merged_coach_now_holds_several_coaching_roles": {
                "_what": "merging gives a man his whole coaching career, assistant years included. The bio layer picks role_title from his FIRST coaching season, so Chuck Noll now reads 'as defensive line, first with the Los Angeles Chargers in 1960-91' where he was Pittsburgh's head coach from 1969. Every fact is true and the summary is worse. This is the bio layer choosing among roles, not a defect in the merge, and the ruling is Ryan's.",
                "resolved": None}},
        "counts": {"candidate_pairs": sum(len(v) for v in verdicts.values()),
                   "verdicts": {k: len(v) for k, v in verdicts.items()},
                   "tests": tests,
                   "merges": len(decisions),
                   "refused_statscrew_against_itself": len(skipped),
                   "refused_unclassifiable": len(verdicts.get("unclassifiable", [])),
                   "refused_namesakes": len(verdicts.get("namesake", [])),
                   "refused_mis_attached": len(verdicts.get("mis-attached source record", [])),
                   "club_seasons_gained": sum(len(d["contribution"]["seasons_gained_from_absorbed"]) for d in decisions),
                   "club_seasons_held_by_both": sum(len(d["contribution"]["seasons_held_by_both"]) for d in decisions),
                   "season_key_rewrites": sum(len(d["contribution"]["season_key_rewrites"]) for d in decisions),
                   "disagreements_held": sum(len(d["disagreements_held_not_resolved"]["stint"]) +
                                             len(d["disagreements_held_not_resolved"]["person"]) for d in decisions),
                   "dates_not_re_added_in_another_notation":
                       sum(len(v) for d in decisions
                           for v in d["contribution"]["absorbed_values_not_added_same_date_other_notation"].values()),
                   "person_values_added": sum(len(v) for d in decisions
                                              for v in d["contribution"]["person_values_added_from_absorbed"].values())}}
    return out


def propose(out, declared):
    """-> what the rule, run on today's base, would ADD and WITHDRAW against the declared decisions."""
    pair = lambda a, b: tuple(sorted((a, b)))
    now = {pair(m["canonical_person"], m["absorbed_person"]): m for m in out["merges"]}
    have = {pair(m["canonical_person"], m["absorbed_person"]): m for m in declared["merges"]}
    verdict_now = {}
    for grp, v in out["REFUSED"].items():
        for p in (v.get("pairs") if isinstance(v, dict) else None) or []:
            if isinstance(p, dict) and p.get("a") and p.get("b"):
                verdict_now[pair(p["a"], p["b"])] = {"refused_as": grp, "verdict": p.get("verdict"),
                                                     "why": p.get("why") or p.get("not_merged_because"),
                                                     "evidence": p.get("evidence")}
    add = [{"canonical_person": m["canonical_person"], "absorbed_person": m["absorbed_person"], "name": m["name"],
            "why": m["why"], "tests_passed": m["tests_passed"]} for k, m in sorted(now.items()) if k not in have]
    withdraw = []
    for k, m in sorted(have.items()):
        if k in now: continue
        vn = verdict_now.get(k) or {"verdict": "no longer a candidate pair", "why": "the rule's tests no longer pair them"}
        withdraw.append({"merge_id": m["merge_id"], "name": m["name"], "canonical_person": m["canonical_person"],
                         "absorbed_person": m["absorbed_person"], "decided": m["why"],
                         "the_rule_now_says": vn.get("verdict"), "because": vn.get("why"),
                         "evidence_then": m.get("evidence"), "evidence_now": vn.get("evidence")})
    return {"_what": ("PROPOSALS, not decisions (Ryan, 2026-09-11). The merge rule re-run on today's base, compared with "
                      "the declared decisions in declarations/person-merge-decisions.json. A proposal to withdraw is a "
                      "FINDING -- the evidence moved since the decision -- and a question for Ryan. Nothing here is applied."),
            "declared": len(have), "the_rule_now_decides": len(now), "unchanged": len(set(now) & set(have)),
            "would_add": add, "would_withdraw": withdraw}


def main():
    """A PROPOSER. It never writes the decisions (declarations/person-merge-decisions.json, in git since
    2026-09-11) and never overwrites anything they rest on. It runs the rule on today's base and reports
    what the rule would add or withdraw; with --write it records that in build/person-merge-proposals.json.
    It used to write build/person-merges.json -- the decisions themselves -- and a re-run silently
    dropped Joe Spencer's merge."""
    out = build()
    declared = json.load(open(os.path.join(BASE, "declarations", "person-merge-decisions.json")))
    P = propose(out, declared)
    P["counts_of_this_run"] = out["counts"]
    print(f"declared {P['declared']}; the rule now decides {P['the_rule_now_decides']}; unchanged {P['unchanged']}; "
          f"would ADD {len(P['would_add'])}; would WITHDRAW {len(P['would_withdraw'])}")
    for w in P["would_withdraw"]:
        print(f"  withdraw? {w['merge_id']} {w['name']}: the rule now says {w['the_rule_now_says']} -- {w['because']}")
    for a in P["would_add"][:10]:
        print(f"  add? {a['name']}: {a['canonical_person']} + {a['absorbed_person']} -- {a['why']}")
    if "--write" in sys.argv:
        fp = os.path.join(BASE, "build", "person-merge-proposals.json")
        json.dump(P, open(fp, "w"), indent=1, ensure_ascii=False)
        print("wrote", fp, "(proposals only; the decisions are untouched)")


if __name__ == "__main__":
    main()
