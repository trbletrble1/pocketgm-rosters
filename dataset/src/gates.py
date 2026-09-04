"""Gates. Each must be shown to FAIL before it is trusted.

Run `python3 src/gates.py --selftest` to construct each failure and watch it fire.
"""
import sys, json
sys.path.insert(0, __file__.rsplit('/',1)[0])
from model import Store, StoreError

FAILURES = []

def check(name, ok, detail=""):
    FAILURES.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok

# ---------------------------------------------------------------- gate 1
def gate_relayed_refused(store_factory):
    """`relayed` may never enter the store."""
    s = store_factory()
    try:
        s.add_source({"source_id": "x", "acquisition": "relayed"})
        return False, "a relayed source was ACCEPTED"
    except StoreError:
        return True, "refused"

# ---------------------------------------------------------------- gate 2
def gate_claim_needs_source_record(store_factory):
    s = store_factory()
    try:
        s.add_claim("nonexistent#1", ("person","p_1"), "x", 1, 1950)
        return False, "a claim with a dangling source_record was ACCEPTED"
    except StoreError:
        return True, "refused"

# ---------------------------------------------------------------- gate 3
def gate_invented_refused(store_factory):
    s = store_factory()
    s.add_source({"source_id": "t", "acquisition": "held", "stated_by": "t"})
    sr = s.add_source_record("t", "r1")
    try:
        s.add_claim(sr, ("person","p_1"), "hair", "brown", 1950, kind="invented")
        return False, "an invented claim was ACCEPTED"
    except StoreError:
        return True, "refused"

# ---------------------------------------------------------------- gate 4
def gate_denotation_records_discriminator(store_factory):
    s = store_factory()
    p = s.mint_person()
    s.add_source({"source_id": "t", "acquisition": "held", "stated_by": "t"})
    sr = s.add_source_record("t", "r1")
    try:
        s.add_denotation(sr, p, [], "attribute-match")
        return False, "a denotation with no discriminator was ACCEPTED"
    except StoreError:
        return True, "refused"

# ---------------------------------------------------------------- gate 5
def gate_four_bases_reachable(store_factory, policy):
    """§9.6: all four states constructible AND coming back distinct.
    A counter that can only read zero is the vacuous pass."""
    s = store_factory()
    s.add_source({"source_id": "sc", "acquisition": "fetched", "stated_by": "sc"})
    people = {k: s.mint_person() for k in ("unknown","absent","zero","n")}
    sr = s.add_source_record("sc", "roster")
    # state 1: no claim at all
    # state 2: absence claim (column exists, cell blank)
    s.add_absence(sr, ("person_season", people["absent"], "NFL-1950"), "games_played", 1950)
    # state 3: observed zero
    s.add_claim(sr, ("person_season", people["zero"], "NFL-1950"), "games_played", 0, 1950)
    # state 4: observed n
    s.add_claim(sr, ("person_season", people["n"], "NFL-1950"), "games_played", 12, 1950)
    got = {}
    for k, p in people.items():
        r = s.resolve(("person_season", p, "NFL-1950"), "games_played", policy)
        got[k] = (r["basis"], r["value"])
    want = {"unknown": ("unknown", None), "absent": ("absent", None),
            "zero": ("observed", 0), "n": ("observed", 12)}
    if got != want:
        return False, f"got {got}"
    if len({v for v in got.values()}) != 4:
        return False, "four states did not come back distinct"
    return True, "4/4 distinct: " + ", ".join(f"{k}={v[0]}({v[1]})" for k,v in got.items())

# ---------------------------------------------------------------- gate 6
def gate_contested_survives(store_factory, policy):
    """A contest with no separating rule must NOT resolve."""
    s = store_factory()
    for sid in ("a","b"):
        s.add_source({"source_id": sid, "acquisition": "held", "stated_by": sid})
    p = s.mint_person()
    ra = s.add_source_record("a","1"); rb = s.add_source_record("b","1")
    s.add_claim(ra, ("person", p), "birth_date", "1918-04-29", 2026)
    s.add_claim(rb, ("person", p), "birth_date", "1922-04-29", 2026)
    r = s.resolve(("person", p), "birth_date", policy)
    if r["basis"] != "contested":
        return False, f"resolved to {r['basis']} / {r['value']} instead of contested"
    return True, f"{len(r['candidates'])} candidates retained, no value chosen"

# ---------------------------------------------------------------- gate 7
def gate_attributed_cannot_vote_as_attributed_party(store_factory, policy):
    """The League cannot be corroborated by its opponent quoting it twice."""
    s = store_factory()
    s.add_source({"source_id":"hearing","acquisition":"held","stated_by":"NFLPA"})
    s.add_source({"source_id":"primer","acquisition":"held","stated_by":"NFLPA",
                  "derived_from":"hearing"})
    s.add_source({"source_id":"league","acquisition":"held","stated_by":"NFLMC"})
    p = s.mint_person()
    r1 = s.add_source_record("hearing","p61")
    r2 = s.add_source_record("primer","p20")
    r3 = s.add_source_record("league","x")
    # NFLPA quoting the League, twice
    s.add_claim(r1, ("person",p), "salary", 93333, 1981,
                stated_by="NFLPA", attribution=["NFL Management Council"])
    s.add_claim(r2, ("person",p), "salary", 93333, 2002,
                stated_by="NFLPA", attribution=["NFL Management Council"])
    # the League itself, first-hand, saying something else
    s.add_claim(r3, ("person",p), "salary", 68900, 1981, stated_by="NFLMC", attribution=[])
    r = s.resolve(("person",p), "salary", policy)
    # two NFLPA-stated claims must NOT outweigh one first-hand claim by count
    if r["basis"] != "contested":
        return False, f"two hearsay claims beat one first-hand claim: {r['basis']} {r['value']}"
    return True, "hearsay pair did not outvote the first-hand claim"


def main():
    policy = json.load(open(__file__.rsplit('/',2)[0] + "/policy/resolution.json"))
    sf = Store
    print("gates:")
    ok, d = gate_relayed_refused(sf);                       check("relayed refused", ok, d)
    ok, d = gate_claim_needs_source_record(sf);             check("claim needs a resolvable source_record", ok, d)
    ok, d = gate_invented_refused(sf);                      check("invented has no field to occupy", ok, d)
    ok, d = gate_denotation_records_discriminator(sf);      check("denotation records its discriminator", ok, d)
    ok, d = gate_four_bases_reachable(sf, policy);          check("four bases reachable and distinct", ok, d)
    ok, d = gate_contested_survives(sf, policy);            check("contested survives resolution", ok, d)
    ok, d = gate_attributed_cannot_vote_as_attributed_party(sf, policy)
    check("attributed claim cannot vote as the attributed party", ok, d)
    bad = [n for n,o,_ in FAILURES if not o]
    print(f"\n{len(FAILURES)-len(bad)}/{len(FAILURES)} gates pass")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
