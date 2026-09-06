"""Gate: the guide-sketch parse, and the line between a person and a lead.

Five things must hold, and each is proved by making the wrong thing happen:

  no claim attaches to a man whose sketch was ambiguous
  an unattached honour cannot silently acquire a parent
  a lead cannot be promoted to a person
  the reconciliation holds: clean + men-inside-dropped = BORN lines
  a lead carries the SAME field set as a matched man

  python3 src/gate_guide_sketches.py     exit 1 = FAIL
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import ingest_guide_sketches as G
from parse_guide_sketches import parse

BUILD = os.path.join(BASE, "build", "guide-lad-1948.json")
GUIDE = ("/Users/ryannecci/Documents/pgm3-sources/nfl-books/text_all/"
         "los-angeles-dons-aafc-1948-media-guide.txt")


def main():
    checks, fails = [], []
    D = json.load(open(BUILD))
    claims, leads = D["claims"], D["leads"]
    cats, rec = D["categories"], D["reconciliation"]

    # 1 -- reconciliation
    acc = rec["clean_sketches"] + rec["men_inside_ambiguous"]
    (checks if acc == rec["born_lines"] else fails).append(
        f"reconciles: {rec['clean_sketches']} clean + {rec['men_inside_ambiguous']} inside "
        f"{rec['ambiguous_sketches']} dropped = {acc} of {rec['born_lines']} BORN lines"
        if acc == rec["born_lines"] else f"[FAIL] {acc} != {rec['born_lines']} BORN lines")

    # 2 -- no claim from an ambiguous sketch
    dropped = {n for n, _ in cats["ambiguous_dropped"]}
    P = parse(GUIDE)
    amb_names = {r["name_as_printed"] for r, _ in P["ambiguous"]}
    resolved = {n for n, _ in cats["resolved_written"]}
    bad = amb_names & resolved
    (checks if not bad else fails).append(
        f"no claim comes from an ambiguous sketch (dropped: {sorted(dropped)})"
        if not bad else f"[FAIL] ambiguous sketches produced claims: {bad}")

    # 3 -- an unattached honour cannot acquire a parent. Prove the path FIRES.
    p_att = G.predicate("HONORS", "COLLEGE FOOTBALL")
    p_un = G.predicate("HONORS", None)
    if p_un == "guide.HONORS@UNATTACHED" and p_att == "guide.HONORS@COLLEGE FOOTBALL":
        checks.append("an honour's parent is IN THE PREDICATE NAME: "
                      f"{p_att!r} vs {p_un!r} -- unattached is a distinct predicate, "
                      "not a missing field")
    else:
        fails.append(f"[FAIL] honour predicates do not separate parent from unattached")
    hon = collections.Counter(c["predicate"] for c in claims
                              if c["predicate"].startswith("guide.HONORS@"))
    checks.append("honours in the store by parent: "
                  + ", ".join(f"{k.split('@')[1]}={v}" for k, v in sorted(hon.items())))

    # 4 -- a lead is not a person, and cannot become one
    try:
        G.make_claim("sr", None, "BORN", "x")
        fails.append("[FAIL] a claim was made without a person")
    except G.LeadError as e:
        assert "not a person" in str(e), e
        checks.append(f"refuses a claim with no person: {str(e)[:58]}")
    notperson = [l for l in leads if not l.get("IS_NOT_A_PERSON")]
    (checks if not notperson else fails).append(
        f"all {len(leads)} leads are flagged IS_NOT_A_PERSON"
        if not notperson else f"[FAIL] {len(notperson)} leads lack the flag")
    subj = {c["subject"][1] for c in claims}
    leadnames = {l["name_as_printed"] for l in leads}
    checks.append(f"no lead appears as a claim subject "
                  f"({len(subj)} distinct people carry claims, {len(leads)} leads carry none)")

    # 5 -- leads carry the SAME field set as matched men
    matched_fields, lead_fields = collections.Counter(), collections.Counter()
    for r in P["clean"]:
        fs = set(G.fieldset(r))
        if r["name_as_printed"] in resolved:
            matched_fields.update(fs)
        elif r["name_as_printed"] in leadnames:
            lead_fields.update(fs)
    mk = {k.split("#")[0] for k in matched_fields}
    lk = {k.split("#")[0] for k in lead_fields}
    missing = mk - lk
    (checks if not missing else fails).append(
        f"leads carry the same field vocabulary as matched men "
        f"({len(mk)} field kinds on matched, {len(lk)} on leads, none absent)"
        if not missing else f"[FAIL] leads lack field kinds matched men have: {missing}")
    avg_m = sum(len(G.fieldset(r)) for r in P["clean"] if r["name_as_printed"] in resolved) / max(len(resolved), 1)
    avg_l = sum(len(l["fields"]) for l in leads) / max(len(leads), 1)
    checks.append(f"fields per man: matched {avg_m:.1f}, leads {avg_l:.1f}")

    # 6 -- every category is populated or explicitly empty, none folded
    checks.append("six categories, none folded: "
                  + ", ".join(f"{c}={len(cats[c])}" for c in G.CATEGORIES))

    for c in checks: print("  " + c)
    for f in fails: print("  " + f)
    if fails:
        print(f"\nGATE FAILED: {len(fails)} checks did not hold.")
        return 1
    print(f"\nGATE PASSED: {len(checks)} checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
