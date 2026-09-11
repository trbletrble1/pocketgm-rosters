"""Gates on PFA stage two. The stage-one properties still hold, plus three that
only stage two can violate.

S1 leads were ENUMERATED, NOT FETCHED -- and must carry no claims at all.
S2 a lead's PFA code is never also a matched person's code (the stage-one bug,
   re-armed for a population 8x larger).
S3 coverage is reported per band and a band with no people is UNMEASURED, not 0%.
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_pfa import canonical_url


class GateFailure(Exception):
    pass


def s1_leads_carry_no_claims(build):
    """A lead is not a person and was not fetched. If a lead ever acquired a claim
    it would mean either that the fetch boundary leaked or that a lead was quietly
    promoted -- and promotion requires a ruling that does not exist."""
    leads = build.get("leads") or []
    if not leads:
        raise GateFailure("no leads enumerated -- an empty list is not a pass")
    subjects = {c["subject"][1] for c in build["claims"]}
    for l in leads:
        if not l.get("NOT_FETCHED_THIS_PASS"):
            raise GateFailure(f"lead {l['pfa_code']} is not flagged NOT_FETCHED_THIS_PASS")
        if l.get("pfa_code") in subjects:
            raise GateFailure(f"lead {l['pfa_code']} appears as a claim subject")
    return f"{len(leads):,} leads, none fetched, none carrying a claim"


def s2_no_code_is_both(build, match):
    matched = {canonical_url(c) for c in match.get("matched", {})}
    leadc = {canonical_url(l["pfa_code"]) for l in (build.get("leads") or [])}
    both = matched & leadc
    if both:
        raise GateFailure(f"{len(both)} codes are both matched and a lead, e.g. {sorted(both)[:2]}")
    return f"{len(matched):,} matched codes and {len(leadc):,} lead codes, disjoint"


def s3_unmeasured_is_not_zero(build):
    """A band with no people is UNMEASURED. Rendering it as 0% would assert that PFA
    holds nothing for that band, which is a different claim from having asked nobody."""
    cov = build.get("counts", {}).get("coverage_by_band") or {}
    if not cov:
        raise GateFailure("no coverage by band was computed")
    for b, d in cov.items():
        if not d.get("people"):
            raise GateFailure(f"band {b} has no people but reports fields {sorted(d)}")
        for f, v in d.items():
            if f != "people" and v > d["people"]:
                raise GateFailure(f"band {b}: {f}={v} exceeds its denominator {d['people']}")
    return f"{len(cov)} bands, each with a denominator, no rate above 100%"


def demonstrate():
    outs = []

    def show(nm, fn):
        try:
            fn(); outs.append(f"  {nm:34s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            outs.append(f"  {nm:34s} failed: {str(e)[:62]}")
    show("S1 a lead carrying a claim", lambda: s1_leads_carry_no_claims(
        {"leads": [{"pfa_code": "players/a/a00100.html", "NOT_FETCHED_THIS_PASS": True}],
         "claims": [{"subject": ["person", "players/a/a00100.html"]}]}))
    show("S2 code both matched and lead", lambda: s2_no_code_is_both(
        {"leads": [{"pfa_code": "players/u/umon00200.html"}]},
        {"matched": {"players/u/umon00200.html": "P_1"}}))
    show("S3 band reported with no people", lambda: s3_unmeasured_is_not_zero(
        {"counts": {"coverage_by_band": {"1950s": {"people": 0, "high_school": 3}}}}))
    return outs


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    bp = os.path.join(BASE, "build", "pfa-1950on.json")
    # The preserved copy, as ingest_pfa2.py reads it; the /tmp session is gone (2026-09-11).
    SP = os.path.expanduser("~/Documents/session-scratch-from-laptop-2026-09-07/"
                            "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/pfa2_match.json")
    if not os.path.exists(bp):
        print("\n(build not written yet -- gates run after the ingest)"); sys.exit(0)
    build = json.load(open(bp)); match = json.load(open(SP))
    print("\n=== against the stage-two build ===")
    ok = True
    for nm, fn in (("S1 leads carry no claims", lambda: s1_leads_carry_no_claims(build)),
                   ("S2 no code is both", lambda: s2_no_code_is_both(build, match)),
                   ("S3 unmeasured is not zero", lambda: s3_unmeasured_is_not_zero(build))):
        try:
            print(f"  PASS  {nm:28s} {fn()}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:28s} {e}")
    sys.exit(0 if ok else 1)
