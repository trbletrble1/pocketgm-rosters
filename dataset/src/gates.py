"""Gates. Each must be shown to FAIL before it is trusted.

Run `python3 src/gates.py --selftest` to construct each failure and watch it fire.
"""
import sys, json
sys.path.insert(0, __file__.rsplit('/',1)[0])
from model import Store, StoreError

FAILURES = []

# Each declared hard rule must name the gate that enforces it. A rule with no
# gate is prose; a gate with no rule is undocumented behaviour. Keeping the
# mapping here means adding a rule to the declaration without enforcing it
# FAILS, rather than sitting there reading like policy.
import os as _os
_SAL = json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                    "..", "declarations", "salary_conventions.json")))
RULE_ENFORCED_BY = {
    0: "gate_bare_salary_refused",
    1: "gate_conventions_do_not_pool",
    2: "gate_bare_salary_refused",        # an undeclared money name is refused
    3: "export manifest - src/export_pgm3.py states the convention",
    4: "gate_income_floor_is_not_pay",
}
SYSTEM_RULE_ENFORCED_BY = {
    0: "gate_system_rules_cannot_be_averaged",
    1: "gate_system_rules_cannot_be_averaged",
    2: "gate_system_rules_cannot_be_averaged",
}
TRANSFER_RULE_ENFORCED_BY = {
    0: "gate_transfer_is_not_a_rule_or_a_salary",
    1: "gate_transfer_is_not_a_rule_or_a_salary",
    2: "gate_transfer_is_not_a_rule_or_a_salary",
}


def gate_income_floor_is_not_pay(store_factory):
    """A guaranteed income floor may not sit where pay sits.

    It is owed only if the player's OUTSIDE earnings fall short, so a scheduled
    figure is a ceiling on the club's exposure, not a sum anybody received.
    Filed on a stint it would read as what he was paid that season.
    """
    s = store_factory()
    s.add_source({"source_id": "inst", "acquisition": "held", "stated_by": "inst"})
    sr = s.add_source_record("inst", "r1")
    p = s.mint_person()
    for subj, why in ((("stint", p, "CLE", "NFL-1964"), "a stint"),
                      (("person", p), "a person")):
        try:
            s.add_claim(sr, subj, "guaranteed_income_floor_year", 5000, 1964)
            return False, f"a guaranteed income floor was ACCEPTED on {why}"
        except StoreError as e:
            if "not pay" not in str(e):
                return False, f"refused on {why}, but for the wrong reason: {str(e)[:80]}"
    s.declare_subject(("contract", p, "CLE"))
    s.add_claim(sr, ("contract", p, "CLE"), "guaranteed_income_floor_year", 5000, 1964)
    return True, ("refused on stint and person; accepted only on a contract subject")


def gate_every_hard_rule_has_a_gate():
    """The declaration's hard_rules must each name an enforcer."""
    missing = [i for i in range(len(_SAL["hard_rules"])) if i not in RULE_ENFORCED_BY]
    missing += [f"system:{i}" for i in range(len(_SAL["system_rules"]["hard_rules"]))
                if i not in SYSTEM_RULE_ENFORCED_BY]
    missing += [f"transfer:{i}"
                for i in range(len(_SAL["transfer_payments"]["hard_rules"]))
                if i not in TRANSFER_RULE_ENFORCED_BY]
    if missing:
        return False, f"declared hard rules with NO enforcing gate: {missing}"
    return True, (f"{len(RULE_ENFORCED_BY)} salary + {len(SYSTEM_RULE_ENFORCED_BY)} "
                  f"system + {len(TRANSFER_RULE_ENFORCED_BY)} transfer hard rules "
                  f"each name a gate")

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
    # NFLPA quoting the League, twice. NOTE the predicate names its convention -
    # a bare `salary` here is what made the §8.4 error possible, and the store now
    # refuses it. This fixture originally pooled 93,333 against 68,900 as one
    # predicate, which is that error embedded in a test.
    s.add_claim(r1, ("person",p), "club_cost_per_player", 93333, 1981,
                stated_by="NFLPA", attribution=["NFL Management Council"])
    s.add_claim(r2, ("person",p), "club_cost_per_player", 93333, 2002,
                stated_by="NFLPA", attribution=["NFL Management Council"])
    # the League itself, first-hand, saying something else ON THE SAME CONVENTION
    s.add_claim(r3, ("person",p), "club_cost_per_player", 68900, 1981,
                stated_by="NFLMC", attribution=[])
    r = s.resolve(("person",p), "club_cost_per_player", policy)
    # two NFLPA-stated claims must NOT outweigh one first-hand claim by count
    if r["basis"] != "contested":
        return False, f"two hearsay claims beat one first-hand claim: {r['basis']} {r['value']}"
    return True, "hearsay pair did not outvote the first-hand claim"


# ---------------------------------------------------------------- gate 8
def gate_bare_salary_refused(store_factory):
    """A money figure must name its convention. Pooling must be inexpressible."""
    s = store_factory()
    s.add_source({"source_id": "t", "acquisition": "held", "stated_by": "t"})
    sr = s.add_source_record("t", "r1")
    try:
        s.add_claim(sr, ("person", "p_1"), "salary", 68900, 1979)
        return False, "a bare `salary` claim was ACCEPTED"
    except StoreError as e:
        return ("convention" in str(e)), str(e)[:70]


# ---------------------------------------------------------------- gate 9
def gate_conventions_do_not_pool(store_factory, policy):
    """Two figures under different conventions must NOT read as a contest."""
    s = store_factory()
    for sid in ("nflpa", "dmn"):
        s.add_source({"source_id": sid, "acquisition": "held", "stated_by": sid})
    p = s.mint_person()
    s.declare_subject(("person", p))
    a = s.add_source_record("nflpa", "1")
    b = s.add_source_record("dmn", "1")
    s.add_claim(a, ("person", p), "salary_base", 450000, 1984)
    s.add_claim(b, ("person", p), "salary_base_plus_prorated_bonus", 570000, 1984)
    r1 = s.resolve(("person", p), "salary_base", policy)
    r2 = s.resolve(("person", p), "salary_base_plus_prorated_bonus", policy)
    if r1["basis"] != "observed" or r1["value"] != 450000:
        return False, f"salary_base resolved {r1['basis']}/{r1['value']}"
    if r2["basis"] != "observed" or r2["value"] != 570000:
        return False, f"prorated resolved {r2['basis']}/{r2['value']}"
    return True, "Randy White 1984: base 450,000 and base+prorated 570,000 both stand, no contest"


# ---------------------------------------------------------------- gate 10
def gate_system_rules_cannot_be_averaged(store_factory, policy):
    """A system rule and a player's salary must not share a subject scope.
    If they cannot meet, no average can pool them."""
    s = store_factory()
    s.add_source({"source_id": "ct", "acquisition": "held", "stated_by": "court"})
    sr = s.add_source_record("ct", "1")
    p = s.mint_person()
    # a system rule on a person must be refused
    try:
        s.add_claim(sr, ("person", p), "option_year_rate", 0.90, 1968)
        return False, "a system rule was accepted on a PERSON subject"
    except StoreError:
        pass
    # player money on a league must be refused
    try:
        s.add_claim(sr, ("league_season", "NFL", "1968"), "salary_base", 50000, 1968)
        return False, "player money was accepted on a LEAGUE subject"
    except StoreError:
        pass
    # and each is accepted in its own scope
    s.add_claim(sr, ("league_era", "NFL", "1968"), "option_year_rate", 0.90, 1968)
    s.add_claim(sr, ("person", p), "salary_base", 22000, 1968)
    return True, "0.90 lives on the league, $22,000 on the man; the scopes never meet"


# ---------------------------------------------------------------- gate 12
def gate_transfer_is_not_a_rule_or_a_salary(store_factory):
    """A club-to-club release fee has its own subject and refuses every other.

    Ruled 2026-09-04: on a league subject it states a RULE where there is an
    INSTANCE; on a person it says the player received money he did not receive.
    """
    s = store_factory()
    s.add_source({"source_id": "ct", "acquisition": "held", "stated_by": "ct"})
    sr = s.add_source_record("ct", "kapp")
    p = "p_kapp"
    # Each case names the marker of the rule that MUST do the refusing. Catching
    # a bare StoreError is not enough: widening the scope rule still left the
    # arity rule refusing the league subject, and the gate read that as correct.
    # A gate that fires must fire for its STATED reason.
    cases = [
        (("league_season", "NFL", "1967"), "inter_club_transfer_fee",
         "requires a transfer-scoped subject", "a league subject"),
        (("person", p), "inter_club_transfer_fee",
         "requires a transfer-scoped subject", "a person subject"),
        (("cohort", "QB", "1967"), "inter_club_transfer_fee",
         "requires a transfer-scoped subject", "a cohort subject"),
        (("transfer", p, "BC"), "inter_club_transfer_fee",
         "names BOTH clubs", "a transfer subject naming ONE club"),
        (("transfer", p, "BC", "MIN", 1967), "salary_base",
         "payee of a transfer fee is a club", "a person salary on a transfer subject"),
    ]
    for subj, pred, marker, why in cases:
        try:
            s.add_claim(sr, subj, pred, 50000, 1967)
            return False, f"{pred} was ACCEPTED on {why}"
        except StoreError as e:
            if marker not in str(e):
                return False, (f"{why} was refused, but by the WRONG rule - "
                               f"expected {marker!r}, got: {str(e)[:110]}")
    # the real shape is accepted
    s.add_claim(sr, ("transfer", p, "BC", "MIN", 1967),
                "inter_club_transfer_fee", 50000, 1967)
    return True, ("refused on league, person, cohort and a one-club transfer; "
                  "accepted only as (transfer, person, from_club, to_club, year)")


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
    ok, d = gate_bare_salary_refused(sf);                   check("bare `salary` predicate refused", ok, d)
    ok, d = gate_conventions_do_not_pool(sf, policy);        check("salary conventions do not pool", ok, d)
    ok, d = gate_system_rules_cannot_be_averaged(sf, policy)
    check("system rules cannot be averaged with player money", ok, d)
    ok, d = gate_transfer_is_not_a_rule_or_a_salary(sf)
    check("transfer fee is neither a rule nor a salary", ok, d)
    ok, d = gate_income_floor_is_not_pay(sf)
    check("a guaranteed income floor is not pay", ok, d)
    ok, d = gate_every_hard_rule_has_a_gate()
    check("every declared hard rule names an enforcing gate", ok, d)
    bad = [n for n,o,_ in FAILURES if not o]
    print(f"\n{len(FAILURES)-len(bad)}/{len(FAILURES)} gates pass")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
