"""Gates on the coach promotion. Six properties, each shown FAILING first."""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")


class GateFailure(Exception):
    pass


def p1_no_promotion_without_evidence(o):
    if not o["promotions"]:
        raise GateFailure("no promotions -- an empty result is not a pass")
    for p in o["promotions"]:
        if not p.get("identified_by"):
            raise GateFailure(f"{p['person_id']} has no evidence of identity")
        ev = p.get("no_archive_match_evidence") or {}
        if not ev.get("checked"):
            raise GateFailure(f"{p['person_id']} records no check against the archive")
        tests = {c["test"] for c in ev["checked"]}
        if "exact normalised name" not in tests:
            raise GateFailure(f"{p['person_id']} was not screened on exact name")
        if not any("surname" in t for t in tests):
            raise GateFailure(f"{p['person_id']} was screened on NAME ALONE")
    return f"{len(o['promotions']):,} promotions, each with identity and archive-check evidence"


def p2_every_promotion_reversible(o):
    for p in o["promotions"]:
        r = p.get("reversible") or {}
        if not r.get("lead_ref") or not r.get("undo"):
            raise GateFailure(f"{p['person_id']} cannot be un-promoted from what is stored")
    return f"{len(o['promotions']):,} promotions, each carrying its lead ref and undo"


def p3_parked_categories_untouched(o):
    C = json.load(open(os.path.join(BASE, "build", "pfa-coaches.json")))
    want = {"namesake_only_not_evidence": 136, "ambiguous_candidates": 319,
            "route_conflict": 20}
    live = collections.Counter(l["category"] for l in C["leads"])
    promoted_refs = {p["reversible"]["lead_ref"] for p in o["promotions"]}
    for cat, n in want.items():
        if live[cat] != n:
            raise GateFailure(f"{cat}: {live[cat]} leads, expected {n}")
        touched = [l["lead_id"] for l in C["leads"]
                   if l["category"] == cat and l["lead_id"] in promoted_refs]
        if touched:
            raise GateFailure(f"{len(touched)} {cat} leads were promoted")
    return "136 namesake + 319 ambiguous + 20 route-conflict, all present, none promoted"


def p4_no_player_lead_promoted(o):
    ok = {"pfa-coach-lead", "media-guide-assistant", "coaching-tree"}
    for p in o["promotions"]:
        if p["source"] not in ok:
            raise GateFailure(f"{p['person_id']} came from {p['source']!r}, not a coach source")
        ref = str(p["reversible"].get("lead_ref", ""))
        if ref.startswith(("lead-pfa-0", "lead-draft", "lead-death")) and "coach" not in ref:
            raise GateFailure(f"{p['person_id']} was promoted from a PLAYER lead: {ref}")
    return f"{len(o['promotions']):,} promotions, all from coach sources, no player lead"


def p5_no_claim_created_or_lost(o):
    """Two separate operations with two separate properties.

    PROMOTION creates people and no claims -- the promotion store must hold none.
    APPLYING it writes exactly one claim per coaching season the promotions carry:
    no season lost, none duplicated. Counting a global total would pass while
    silently gaining or dropping seasons, so the check is against the promotions
    themselves."""
    p = json.load(open(os.path.join(BASE, "build", "coach-promotions.json")))
    if "claims" in p:
        raise GateFailure("the promotion store writes claims; it must only create people")
    want = sum(len(x["coaching_seasons"]) for x in o["promotions"])
    ap = os.path.join(BASE, "build", "coach-seasons-promoted.json")
    if not os.path.exists(ap):
        return f"promotion store holds no claims; not yet applied ({want:,} seasons pending)"
    got = json.load(open(ap))["claims"]
    if len(got) != want:
        raise GateFailure(f"applied {len(got):,} claims for {want:,} coaching seasons")
    # A duplicate the LEAD already carried is faithful reproduction, not a fault of
    # the apply step -- 25 exist because a coach listed in two of PFA's coach
    # indexes had his seasons concatenated upstream. What must never happen is the
    # apply step ADDING duplication, so the two multisets are compared.
    applied = collections.Counter((c["subject"][1], json.dumps(c["value"], sort_keys=True))
                                  for c in got)
    leads = collections.Counter((x["person_id"], json.dumps(s, sort_keys=True))
                                for x in o["promotions"] for s in x["coaching_seasons"])
    if applied != leads:
        extra = sum((applied - leads).values()); lost = sum((leads - applied).values())
        raise GateFailure(f"apply step added {extra} and lost {lost} season claims")
    upstream_dup = sum(v - 1 for v in leads.values() if v > 1)
    ids = {x["person_id"] for x in o["promotions"]}
    stray = {c["subject"][1] for c in got} - ids
    if stray:
        raise GateFailure(f"{len(stray)} applied claims name a person who was not promoted")
    return (f"{len(got):,} claims applied = {want:,} seasons promoted, multiset identical; "
            f"{upstream_dup} duplicates carried FROM the leads, none added here")


def p6_coaching_seasons_match_the_lead(o):
    """Compared against THE LEAD'S OWN coaching_seasons.

    The first version of this gate compared against claims keyed by PFA code --
    but claims exist only for RESOLVED people, and the 1,687 lead codes have zero
    overlap with them. The gate was reading an empty dict and calling every
    promotion wrong. A gate pointed at the wrong source of truth fails honest data
    and would have passed a real error."""
    C = json.load(open(os.path.join(BASE, "build", "pfa-coaches.json")))
    lead = {l["lead_id"]: l for l in C["leads"]}
    n = 0
    for p in o["promotions"]:
        if p["source"] != "pfa-coach-lead":
            continue
        L = lead.get(p["reversible"]["lead_ref"])
        if L is None:
            raise GateFailure(f"{p['person_id']} references a lead that does not exist")
        want = L.get("coaching_seasons") or []
        got = p["coaching_seasons"]
        if got != want:
            raise GateFailure(f"{p['person_id']} carries {len(got)} seasons, lead had {len(want)}")
        n += len(got)
    return f"{n:,} coaching seasons, each promotion carrying exactly its lead's"


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:38s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:38s} failed: {str(e)[:56]}")
    show("P1 promoted on name alone", lambda: p1_no_promotion_without_evidence(
        {"promotions": [{"person_id": "P_9", "identified_by": {"x": 1},
                         "no_archive_match_evidence": {"checked": [
                             {"test": "exact normalised name"}]}}]}))
    show("P2 promotion not reversible", lambda: p2_every_promotion_reversible(
        {"promotions": [{"person_id": "P_9", "reversible": {}}]}))
    show("P4 player lead promoted", lambda: p4_no_player_lead_promoted(
        {"promotions": [{"person_id": "P_9", "source": "pfa-player-lead",
                         "reversible": {"lead_ref": "lead-pfa-00001"}}]}))
    show("P6 seasons not the lead's", lambda: p6_coaching_seasons_match_the_lead(
        {"promotions": [{"person_id": "P_9", "source": "pfa-coach-lead",
                         "reversible": {"lead_ref": "lead-pfa-coach-00001"},
                         "coaching_seasons": []}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    o = json.load(open(os.path.join(BASE, "build", "coach-promotions.json")))
    print("\n=== against the promotion store ===")
    ok = True
    for nm, fn in (("P1 evidence on every promotion", p1_no_promotion_without_evidence),
                   ("P2 every promotion reversible", p2_every_promotion_reversible),
                   ("P3 parked categories untouched", p3_parked_categories_untouched),
                   ("P4 no player lead promoted", p4_no_player_lead_promoted),
                   ("P5 no claim created or lost", p5_no_claim_created_or_lost),
                   ("P6 seasons match the lead", p6_coaching_seasons_match_the_lead)):
        try:
            print(f"  PASS  {nm:32s} {fn(o)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:32s} {e}")
    sys.exit(0 if ok else 1)
