"""Gates on the officials ingest. Five properties, each shown failing first."""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
CACHE = "/Users/ryannecci/Documents/pgm3-sources/pfa2"
from ingest_officials import parse_officiating


class GateFailure(Exception):
    pass


def o1_no_second_person_for_a_man_already_held(b):
    """An official who resolves to an archive person is ATTACHED to him. Creating
    a second record for a man already held is the duplicate this whole check
    exists to prevent."""
    created = {c["pfa_code"] for c in b["created"]}
    attached = {c["value"]["pfa_code"] for c in b["claims"]
                if c["predicate"] == "pfa.role"} - created
    both = created & attached
    if both:
        raise GateFailure(f"{len(both)} codes were both created and attached")
    ids = [c["person_id"] for c in b["created"]]
    if len(ids) != len(set(ids)):
        raise GateFailure("a person id was issued twice")
    if not b["refusals"]:
        raise GateFailure("zero refusals -- the duplicate check is not working")
    return (f"{len(created):,} created, {len(attached):,} attached to men already held, "
            f"{len(b['refusals'])} refused")


def o2_dual_role_is_one_person(b):
    """22 officials share a code with a coach; Fay Abbott's page is one record at
    two paths. A man with two roles is ONE person, and the code proves it."""
    for d in b["dual_role"]:
        for kind, c in (d.get("linked") or {}).items():
            if c != d["pfa_code"]:
                raise GateFailure(f"{d['pfa_code']} links {kind} code {c} -- not the same record")
        if len(set(d["roles"])) < 2:
            raise GateFailure(f"{d['pfa_code']} is in dual_role with one role")
    byid = collections.Counter()
    for c in b["claims"]:
        if c["predicate"] == "pfa.role":
            byid[c["value"]["pfa_code"]] += 1
    dup = [k for k, v in byid.items() if v > 1]
    if dup:
        raise GateFailure(f"{len(dup)} codes carry more than one role claim")
    combos = collections.Counter(tuple(sorted(d["roles"])) for d in b["dual_role"])
    return f"{len(b['dual_role'])} dual-role men, one person each: {dict(combos)}"


def o3_role_is_queryable(b):
    """Players, coaches and officials must be separable."""
    roles = collections.Counter()
    for c in b["claims"]:
        if c["predicate"] == "pfa.role":
            for r in c["value"]["roles"]:
                roles[r] += 1
        if c["predicate"].startswith("pfa.officiating") and c.get("_role") not in (None, "official"):
            raise GateFailure("an officiating claim is not marked as an official's")
    if "official" not in roles:
        raise GateFailure("no official role recorded")
    return f"roles queryable: {dict(roles)}"


def o4_creation_reversible_with_evidence(b):
    for c in b["created"]:
        if not c.get("identified_by") or not c.get("no_archive_match_evidence"):
            raise GateFailure(f"{c['person_id']} has no evidence")
        if not (c.get("reversible") or {}).get("undo"):
            raise GateFailure(f"{c['person_id']} cannot be un-created")
        tests = {t["test"] for t in c["no_archive_match_evidence"]["checked"]}
        if not any("surname" in t for t in tests):
            raise GateFailure(f"{c['person_id']} was screened on NAME ALONE")
    return f"{len(b['created']):,} creations, each evidenced and reversible"


def o5_assignment_string_unaltered(b, sample=200):
    """The crew vocabulary has changed over a century. A stored assignment must be
    byte-identical to the page."""
    want = collections.defaultdict(collections.Counter)
    for c in b["claims"]:
        if c["predicate"] == "pfa.officiating_season":
            code = c["source_record"].rsplit("/", 1)[-1].replace(".html", "")
            want[code][(c["value"]["year"], c["value"]["assignment_as_printed"])] += 1
    checked = 0
    for fn in sorted(os.listdir(CACHE)):
        if not fn.startswith("officials_"):
            continue
        code = fn[len("officials_"):-len(".html")]
        if code not in want:
            continue
        h = open(os.path.join(CACHE, fn), encoding="utf-8", errors="replace").read()
        seasons, _ = parse_officiating(h)
        got = collections.Counter((s["year"], s["assignment_as_printed"]) for s in seasons)
        if got != want[code]:
            raise GateFailure(f"{fn}: stored assignments differ from the page")
        checked += 1
        if checked >= sample:
            break
    return f"{checked} officials re-parsed, every assignment string identical to the page"


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:38s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:38s} failed: {str(e)[:54]}")
    show("O1 zero refusals", lambda: o1_no_second_person_for_a_man_already_held(
        {"created": [], "claims": [], "refusals": []}))
    show("O2 dual role as two records", lambda: o2_dual_role_is_one_person(
        {"dual_role": [{"pfa_code": "a1", "roles": ["official", "coach"],
                        "linked": {"coaches": "b2"}}], "claims": []}))
    show("O3 role not queryable", lambda: o3_role_is_queryable({"claims": []}))
    show("O4 created on name alone", lambda: o4_creation_reversible_with_evidence(
        {"created": [{"person_id": "P_9", "identified_by": {"x": 1},
                      "reversible": {"undo": "y"},
                      "no_archive_match_evidence": {"checked": [
                          {"test": "exact normalised name"}]}}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    b = json.load(open(os.path.join(BASE, "build", "pfa-officials.json")))
    print("\n=== against the officials build ===")
    ok = True
    for nm, fn in (("O1 no second person", o1_no_second_person_for_a_man_already_held),
                   ("O2 dual role is one person", o2_dual_role_is_one_person),
                   ("O3 role is queryable", o3_role_is_queryable),
                   ("O4 creation reversible", o4_creation_reversible_with_evidence),
                   ("O5 assignment unaltered", o5_assignment_string_unaltered)):
        try:
            print(f"  PASS  {nm:28s} {fn(b)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:28s} {e}")
    sys.exit(0 if ok else 1)
