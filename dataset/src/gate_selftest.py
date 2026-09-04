"""Prove every gate FAILS when its invariant is broken.

'An assertion that cannot fail reports success.' Each entry below deliberately
breaks one invariant, runs the gate, and requires it to report failure.
"""
import sys, os, json, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model, gates
from model import Store

POLICY = json.load(open(os.path.join(HERE, "..", "policy", "resolution.json")))


def broken_store_factory(**breaks):
    """A Store subclass with one invariant deliberately removed."""
    class Broken(Store):
        pass
    if breaks.get("allow_relayed"):
        def add_source(self, decl):
            self.sources[decl["source_id"]] = decl; return decl["source_id"]
        Broken.add_source = add_source
    if breaks.get("allow_dangling_sr"):
        orig = Store.add_claim
        def add_claim(self, sr, *a, **k):
            if sr not in self.source_records:
                self.source_records[sr] = {"source_id": "?", "locator": "?"}
                self.sources.setdefault("?", {"source_id": "?", "stated_by": "?"})
            return orig(self, sr, *a, **k)
        Broken.add_claim = add_claim
    if breaks.get("allow_invented"):
        model.FORBIDDEN_KINDS.discard("invented"); model.KINDS.add("invented")
    if breaks.get("allow_empty_discriminator"):
        def add_denotation(self, sr, person, discriminator, method, **k):
            d = {"id": self._mint("d"), "source_record": sr, "person": person,
                 "discriminator": list(discriminator), "method": method,
                 "status": k.get("status", "asserted")}
            self.denotations.append(d); return d["id"]
        Broken.add_denotation = add_denotation
    if breaks.get("coalesce_absent_to_zero"):
        orig = Store.resolve
        def resolve(self, subject, predicate, policy):
            r = orig(self, subject, predicate, policy)
            if r["basis"] in ("absent", "unknown"):   # the classic null->0
                r["basis"], r["value"] = "observed", 0
            return r
        Broken.resolve = resolve
    if breaks.get("force_resolve_contests"):
        orig = Store.resolve
        def resolve(self, subject, predicate, policy):
            r = orig(self, subject, predicate, policy)
            if r["basis"] == "contested":            # pick the first, quietly
                r["basis"] = "observed"; r["value"] = r["candidates"][0]["value"]
            return r
        Broken.resolve = resolve
    if breaks.get("count_sources_not_lineage"):
        Broken._lineage_group = lambda self, c: (c["source_id"], c["stated_by"])
    if breaks.get("allow_bare_salary"):
        model.BARE_MONEY_PREDICATES.clear()
    if breaks.get("pool_conventions"):
        # an ingest that strips the convention off the predicate name - which is
        # exactly how the §8.4 error happens in the wild
        orig = Store.add_claim
        def add_claim(self, sr, subject, predicate, *a, **k):
            if predicate.startswith(("salary_", "club_cost")):
                predicate = "money"
            return orig(self, sr, subject, predicate, *a, **k)
        Broken.add_claim = add_claim
        orig_r = Store.resolve
        def resolve(self, subject, predicate, policy):
            if predicate.startswith(("salary_", "club_cost")):
                predicate = "money"
            return orig_r(self, subject, predicate, policy)
        Broken.resolve = resolve
    return Broken


CASES = [
    ("relayed refused", "allow_relayed",
     lambda sf, pol: gates.gate_relayed_refused(sf)),
    ("claim needs a resolvable source_record", "allow_dangling_sr",
     lambda sf, pol: gates.gate_claim_needs_source_record(sf)),
    ("invented has no field to occupy", "allow_invented",
     lambda sf, pol: gates.gate_invented_refused(sf)),
    ("denotation records its discriminator", "allow_empty_discriminator",
     lambda sf, pol: gates.gate_denotation_records_discriminator(sf)),
    ("four bases reachable and distinct", "coalesce_absent_to_zero",
     lambda sf, pol: gates.gate_four_bases_reachable(sf, pol)),
    ("contested survives resolution", "force_resolve_contests",
     lambda sf, pol: gates.gate_contested_survives(sf, pol)),
    ("attributed claim cannot vote as the attributed party", "count_sources_not_lineage",
     lambda sf, pol: gates.gate_attributed_cannot_vote_as_attributed_party(sf, pol)),
    ("bare `salary` predicate refused", "allow_bare_salary",
     lambda sf, pol: gates.gate_bare_salary_refused(sf)),
    ("salary conventions do not pool", "pool_conventions",
     lambda sf, pol: gates.gate_conventions_do_not_pool(sf, pol)),
]

def main():
    print("gate self-test: each gate must FAIL when its invariant is broken\n")
    bad = []
    for name, brk, run in CASES:
        saved_forbidden = set(model.FORBIDDEN_KINDS); saved_kinds = set(model.KINDS)
        saved_bare = set(model.BARE_MONEY_PREDICATES)
        sf = broken_store_factory(**{brk: True})
        try:
            ok, detail = run(sf, POLICY)
        finally:
            model.FORBIDDEN_KINDS.clear(); model.FORBIDDEN_KINDS.update(saved_forbidden)
            model.KINDS.clear(); model.KINDS.update(saved_kinds)
            model.BARE_MONEY_PREDICATES.clear(); model.BARE_MONEY_PREDICATES.update(saved_bare)
        fired = not ok
        print(f"  [{'FIRED' if fired else 'SILENT'}] {name}")
        print(f"           break: {brk}")
        print(f"           gate said: {detail}")
        if not fired:
            bad.append(name)
    print()
    if bad:
        print(f"{len(bad)} gate(s) did NOT fire when broken — they cannot fail and report success:")
        for n in bad: print("   ", n)
        return 1
    print(f"all {len(CASES)} gates fired when their invariant was broken")
    return 0

if __name__ == "__main__":
    sys.exit(main())
