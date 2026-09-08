"""Gates on the never-enumerated boxscore men. Four properties, each shown failing."""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")


class GateFailure(Exception):
    pass


def n1_leads_never_became_people(b):
    """Ryan's ruling on player leads stands. No claim, no person, no promotion."""
    if b.get("claims"):
        raise GateFailure(f"{len(b['claims'])} claims written; these men are not people")
    for l in b["leads"]:
        if not l.get("IS_NOT_A_PERSON"):
            raise GateFailure(f"{l['lead_id']} is not flagged IS_NOT_A_PERSON")
        if l.get("person_id") or l.get("promoted"):
            raise GateFailure(f"{l['lead_id']} carries a person id")
    return f"{len(b['leads'])} leads, no claims, nobody promoted"


def n2_hard_404_is_its_own_category(b):
    """A 404 is PFA's own answer, verified at request time -- not a fetch that
    failed and not a man who did not exist."""
    d = b["source_dead_links"]
    if not d:
        raise GateFailure("no dead-link category recorded")
    codes = {l["pfa_code"] for l in b["leads"]}
    for x in d:
        if not x.get("_read_at_request_time"):
            raise GateFailure(f"{x['pfa_code']} status was not read at request time")
        if not x["status"].startswith("HTTP 404"):
            raise GateFailure(f"{x['pfa_code']} is in dead links with status {x['status']}")
        if x["pfa_code"] in codes:
            raise GateFailure(f"{x['pfa_code']} is both a dead link and a lead")
    return f"{len(d)} hard 404 kept apart from {len(codes)} leads, status read at request time"


def n3_no_coach_promoted(b):
    for l in b["leads"]:
        if l.get("page_kind") != "player":
            raise GateFailure(f"{l['lead_id']} is a {l['page_kind']} page and was not flagged")
    return f"all {len(b['leads'])} pages are player pages; the coaches ruling does not reach this set"


def n4_reason_is_recorded(b):
    """Structural blind spot and enumeration defect are DIFFERENT FACTS."""
    c = collections.Counter()
    for l in b["leads"]:
        w = l.get("why_never_enumerated", "")
        if not (w.startswith("structural") or w.startswith("defect")):
            raise GateFailure(f"{l['lead_id']} records no reason")
        c[w.split(":")[0]] += 1
        if l.get("boxscore_side") not in ("visitor_only", "home_only", "both_sides", "unknown"):
            raise GateFailure(f"{l['lead_id']} has no boxscore side")
    if not c["structural"] or not c["defect"]:
        raise GateFailure(f"both reasons must occur: {dict(c)}")
    return f"structural {c['structural']}, defect {c['defect']}, each with its side recorded"


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:36s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:36s} failed: {str(e)[:56]}")
    show("N1 a lead became a person", lambda: n1_leads_never_became_people(
        {"claims": [1], "leads": []}))
    show("N2 404 folded into leads", lambda: n2_hard_404_is_its_own_category(
        {"source_dead_links": [{"pfa_code": "x", "status": "HTTP 404",
                                "_read_at_request_time": True}],
         "leads": [{"pfa_code": "x"}]}))
    show("N3 a coach page unflagged", lambda: n3_no_coach_promoted(
        {"leads": [{"lead_id": "L1", "page_kind": "coach"}]}))
    show("N4 no reason recorded", lambda: n4_reason_is_recorded(
        {"leads": [{"lead_id": "L1", "why_never_enumerated": "", "boxscore_side": "both_sides"}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    b = json.load(open(os.path.join(BASE, "build", "pfa-boxscore-leads.json")))
    print("\n=== against the build ===")
    ok = True
    for nm, fn in (("N1 leads never became people", n1_leads_never_became_people),
                   ("N2 hard 404 its own category", n2_hard_404_is_its_own_category),
                   ("N3 no coach promoted", n3_no_coach_promoted),
                   ("N4 reason recorded", n4_reason_is_recorded)):
        try:
            print(f"  PASS  {nm:30s} {fn(b)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:30s} {e}")
    sys.exit(0 if ok else 1)
