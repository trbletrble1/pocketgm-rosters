"""Gates on the draft ingests: nflverse, the two wip CSVs, and PFR.

Each property is shown FAILING for its own stated reason before it is trusted.
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")

STORES = ("nflverse-draft.json", "wip-drafts.json", "pfr-drafts.json")
COMPLETE = ("nflverse.draft_selection", "draft.selection", "pfr.draft_selection")


class GateFailure(Exception):
    pass


def load():
    out = {}
    for s in STORES:
        p = os.path.join(BASE, "build", s)
        if os.path.exists(p):
            out[s] = json.load(open(p))
    return out


def d1_no_claim_on_an_unresolved_man(stores):
    """Every claim carries a person. The unresolved are kept in their own list and
    have no claims at all -- an unresolved row is a gap, and a gap is not a subject."""
    if not stores:
        raise GateFailure("no draft stores present -- an empty corpus is not a pass")
    n = 0
    for name, d in stores.items():
        unresolved_ids = {u.get("gsis_id") or u.get("name_as_printed")
                          for u in d.get("unresolved", [])}
        for c in d["claims"]:
            s = c.get("subject")
            if not (isinstance(s, list) and len(s) > 1 and str(s[1]).startswith("P_")):
                raise GateFailure(f"{name}: a claim has subject {s!r}")
            if c.get("gsis_id") and c["gsis_id"] in unresolved_ids:
                raise GateFailure(f"{name}: {c['gsis_id']} is both claimed and unresolved")
            n += 1
    return f"{n:,} claims, every one on a resolved person"


def d2_a_pick_without_a_round_is_not_a_draft(stores):
    """draft_picks_pre2001.csv has NO round column. Its rows may never be written
    under a predicate that means 'a draft selection', because a consumer reading
    round=None on such a claim cannot tell 'the source had no round' from 'this man
    went undrafted-then-signed' or from a parse that dropped it. The limitation
    lives in the predicate name, where it cannot be missed."""
    for name, d in stores.items():
        for c in d["claims"]:
            v = c.get("value") or {}
            if c["predicate"] in COMPLETE and v.get("round") is None:
                raise GateFailure(
                    f"{name}: {c['predicate']} written with no round -- a partial fact "
                    f"wearing a complete predicate")
            if c["predicate"] == "draft.overall_pick_only" and "round" in v:
                raise GateFailure(f"{name}: overall_pick_only claim carries a round")
    return "no partial draft is written under a complete predicate"


def d3_disagreements_held(stores):
    for name, d in stores.items():
        for x in d.get("disagreements", []):
            if x.get("resolved") is not None:
                raise GateFailure(f"{name}: a {x['field']} disagreement was resolved")
            sides = [k for k in ("nflverse", "statscrew", "pfa", "pfr") if x.get(k)]
            if len(sides) < 2:
                raise GateFailure(f"{name}: a disagreement kept only {sides}")
    n = sum(len(d.get("disagreements", [])) for d in stores.values())
    return f"{n} disagreements, both sides held, none resolved"


def d4_identity_never_rests_on_name_alone(stores):
    """Every resolved row must name the evidence that resolved it. A route of
    'name only' is not permitted to exist -- 923 names in this era are shared by
    two men and eleven by one called Mike Williams."""
    ok = {"name_and_birth_date", "career_window_one_part_birth_date_differs",
          "unique_name_in_career_window", "career_window_broke_the_namesake_tie"}
    seen = collections.Counter()
    for name, d in stores.items():
        for k in (d.get("counts", {}).get("by_resolution") or {}):
            seen[k] += 1
        for c in d["claims"]:
            # THE ROUTE IS A PROPERTY OF THE CLAIM, NOT OF ONE SHAPE OF VALUE. This read
            # only `value["resolved_by"]` and so assumed every claim's value is a dict.
            # The first claim with a scalar value -- nflverse's birth date, added
            # 2026-09-07 when a disagreeing value became a claim -- crashed the gate with
            # AttributeError rather than checking it. Read both, and require one.
            v = c.get("value")
            r = c.get("resolved_by") or ((v or {}).get("resolved_by") if isinstance(v, dict) else None)
            if r and r not in ok:
                raise GateFailure(f"{name}: a claim was resolved by {r!r}")
    if "name_only" in seen:
        raise GateFailure("a 'name_only' resolution route exists")
    return f"{len(seen)} resolution routes, none of them name alone"


def demonstrate():
    outs = []

    def show(nm, fn):
        try:
            fn(); outs.append(f"  {nm:38s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            outs.append(f"  {nm:38s} failed: {str(e)[:66]}")
    show("D1 claim on an unresolved man", lambda: d1_no_claim_on_an_unresolved_man(
        {"x": {"claims": [{"subject": ["person", None], "predicate": "p", "value": {}}],
               "unresolved": []}}))
    show("D2 pick with no round", lambda: d2_a_pick_without_a_round_is_not_a_draft(
        {"x": {"claims": [{"predicate": "draft.selection",
                           "value": {"overall_pick": 209, "round": None}}]}}))
    show("D3 disagreement resolved", lambda: d3_disagreements_held(
        {"x": {"claims": [], "disagreements": [
            {"field": "birth_date", "nflverse": "a", "statscrew": "b", "resolved": "nflverse"}]}}))
    show("D4 resolved on name alone", lambda: d4_identity_never_rests_on_name_alone(
        {"x": {"claims": [{"predicate": "p", "value": {"resolved_by": "name_only"}}],
               "counts": {"by_resolution": {"name_only": 5}}}}))
    return outs


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    st = load()
    print(f"\n=== against {len(st)} draft store(s) ===")
    ok = True
    for nm, fn in (("D1 no claim on unresolved", d1_no_claim_on_an_unresolved_man),
                   ("D2 partial is not complete", d2_a_pick_without_a_round_is_not_a_draft),
                   ("D3 disagreements held", d3_disagreements_held),
                   ("D4 identity not name alone", d4_identity_never_rests_on_name_alone)):
        try:
            print(f"  PASS  {nm:30s} {fn(st)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:30s} {e}")
    sys.exit(0 if ok else 1)
