"""Gate: money the player did not receive may not be expressed as salary.

Three documents arrived together and all three fail the same way if waved
through, each in a different direction:

  Howard D. Johnson, Cleveland 1955, $6,000. A signed contract for a man who
  does not appear on the 1955 Cleveland roster. Contracted, not earned.

  Mike Askea, WFL 1974, $11,812.50. "Undisputedly owed to Player" -- money the
  club FAILED to pay. Entered as a salary it records the exact inverse.

  Bobby Hebert, Michigan 1983, six paragraph-23 incentives totalling $105,000.
  Contingent on outcomes, and 23.3 pays ONLY IF 23.2 does not, so the six can
  never all be earned: the true maximum is $95,000, not $105,000.

The shared property is one sentence: a figure that did not reach the player is
not a wage. So the refusal is not three special cases, it is one rule with
three shapes -- and the convention lives in the PREDICATE NAME, which is why
there is no path from any of these to salary_base.

  python3 src/gate_money_that_was_not_paid.py      exit 1 = FAIL
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DECL = os.path.join(HERE, "..", "declarations", "salary_conventions.json")

SALARY_PREDICATES = {"salary_base", "salary_base_plus_prorated_bonus",
                     "salary_base_plus_bonuses_nflpa"}


class NotAWage(Exception):
    pass


def admit(predicate, entry):
    """The only door. Anything that did not reach the player is refused here."""
    if predicate in SALARY_PREDICATES:
        if entry.get("never_appeared"):
            raise NotAWage("%s was contracted but the roster check returned "
                           "ABSENT; it belongs to "
                           "contracted_season_salary_no_appearance"
                           % entry.get("person"))
        if entry.get("owed_not_paid"):
            raise NotAWage("%s is money owed and not paid; it belongs to "
                           "unpaid_wages_settlement" % entry.get("person"))
        if entry.get("contingent"):
            raise NotAWage("%s is contingent on an outcome and is not base pay"
                           % entry.get("person"))
    return True


def roster_absence_must_have_been_run(entry):
    """An unrun check is not an absence. Empty is not the same as failed."""
    if entry.get("never_appeared") and not entry.get("roster_check_run"):
        raise NotAWage("%s is marked never_appeared but no roster check was "
                       "recorded. An unrun check is not an absence."
                       % entry.get("person"))
    return True


def max_earnable(provisions):
    """Mutually exclusive provisions may not both be counted.

    The exclusion is declared on ONE side only -- 23.3 says it excludes 23.2,
    23.2 says nothing -- so the group must be closed over BOTH members. Reading
    only the declaring side picks 23.3's $10,000 over 23.2's $15,000 and
    understates the maximum by $5,000. This gate caught exactly that.
    """
    by_ref = {p["ref"]: p for p in provisions}
    groups = {}
    for p in provisions:
        if p.get("excludes"):
            key = frozenset([p["ref"], p["excludes"]])
            members = [by_ref[r] for r in key if r in by_ref]
            groups[key] = members
    total = 0
    counted = set()
    for key, members in groups.items():
        total += max(m["value"] for m in members)
        counted |= set(key)
    for p in provisions:
        if p["ref"] not in counted:
            total += p["value"]
    return total


def main():
    d = json.load(open(DECL, encoding="utf-8"))
    checks = []
    fails = []

    # --- the declaration must carry the convention these route to -----------
    if "contracted_season_salary_no_appearance" not in d["conventions"]:
        fails.append("the declaration has no contracted_season_salary_no_appearance convention")
    else:
        checks.append("the declaration carries contracted_season_salary_no_appearance")

    # --- each refusal must fire, for ITS OWN stated reason -------------------
    for entry, flag, needle in (
        ({"person": "Howard D. Johnson", "never_appeared": True}, "never_appeared", "ABSENT"),
        ({"person": "Mike Askea", "owed_not_paid": True}, "owed_not_paid", "owed and not paid"),
        ({"person": "Bobby Hebert 23.1", "contingent": True}, "contingent", "contingent"),
    ):
        try:
            admit("salary_base", entry)
            fails.append("[FAIL] %s admitted as salary_base" % entry["person"])
        except NotAWage as e:
            if needle not in str(e):
                fails.append("[FAIL] %s refused for the WRONG reason: %s" % (entry["person"], e))
            else:
                checks.append("refuses %s: %s" % (flag, str(e)[:78]))

    # --- and must NOT refuse a figure that was actually paid -----------------
    try:
        admit("salary_base", {"person": "Galen R. Fiss"})
        admit("salary_base", {"person": "William Willis"})
        checks.append("admits Willis 1952 and Fiss 1957, which were earned")
    except NotAWage as e:
        fails.append("[FAIL] a paid salary was refused: %s" % e)

    # --- an unrun roster check is not an absence ----------------------------
    try:
        roster_absence_must_have_been_run({"person": "X", "never_appeared": True})
        fails.append("[FAIL] never_appeared accepted with no roster check run")
    except NotAWage as e:
        assert "unrun check is not an absence" in str(e), e
        checks.append("refuses never_appeared when no roster check was run")
    try:
        roster_absence_must_have_been_run(
            {"person": "Howard D. Johnson", "never_appeared": True, "roster_check_run": True})
        checks.append("accepts never_appeared once the roster check is recorded")
    except NotAWage as e:
        fails.append("[FAIL] a run roster check was still refused: %s" % e)

    # --- mutual exclusion must reduce the maximum ---------------------------
    prov = [
        {"ref": "23.1", "value": 55000},
        {"ref": "23.2", "value": 15000},
        {"ref": "23.3", "value": 10000, "excludes": "23.2"},
        {"ref": "23.4", "value": 10000},
        {"ref": "23.5", "value": 10000},
        {"ref": "23.6", "value": 5000},
    ]
    naive = sum(p["value"] for p in prov)
    real = max_earnable(prov)
    if naive != 105000:
        fails.append("[FAIL] the naive sum is %d, expected 105000" % naive)
    if real != 95000:
        fails.append("[FAIL] max_earnable is %d, expected 95000" % real)
    else:
        checks.append("23.3 excludes 23.2: naive sum $%s, true maximum $%s"
                      % (f"{naive:,}", f"{real:,}"))

    for c in checks:
        print("  " + c)
    for f in fails:
        print("  " + f)
    if fails:
        print("\nGATE FAILED: %d checks did not hold." % len(fails))
        return 1
    print("\nGATE PASSED: %d refusals fire for their own stated reasons, paid "
          "salaries still pass, and mutually exclusive provisions do not both "
          "count." % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
