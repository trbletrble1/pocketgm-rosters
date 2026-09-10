"""Gate: every declared family has a reading, or is declared deliberately unread.

RYAN'S RULING, 2026-09-09, and it is the property the position family exposed.

WHAT HAPPENED. `position` was declared a family with no reading and the build published
**32,372 fabricated disagreements** -- `HB` against `LH`, `LB` against `MLB`, `CB` against
`LCB`, each one a source being less specific rather than contradicting. RS-G6 REPORTED
PASS. It re-groups every contested row with the shared grouper and compares the count to
what the builder recorded, but the builder uses THAT SAME GROUPER, so the test can only
catch a drift between two copies of one rule. A family with no reading is not in its
population at all (`if fam not in fams: continue`), so all 32,372 rows were skipped rather
than examined.

Green meaning "nothing to check" and green meaning "everything checked" have now been the
same answer three times: RS-G6 when only two families were declared, RS-G8 when its check
was derived from the declaration it was checking, and this.

AND DECLARING A FAMILY IS TWO EDITS IN TWO FILES with nothing between them.
`service/declarations/predicate-families.json` says which predicates are one field.
`declarations/readings.json` `VALUE_READINGS` is what `reading_view.families()` actually
reads. I declared the family in the first, rebuilt, and the reading was silently absent --
`families_with_a_reading` stayed at 7 and the contested count did not move. It took a
second build to notice. That check belongs HERE, in this gate, and not in RS-G6: RS-G6's
job is that a recorded disagreement is real, and this gate's job is that the machinery
which decides that exists at all. One property, one gate.

  A1  every declared family has a reading, or a declared exemption naming a reason
  A2  every reading names a declared family -- the two files agree BOTH ways
  A3  a declared reading can actually be run: the shared reader returns something for the
      declaration's own worked example, so a reading declared and never implemented fails

  python3 src/gate_family_readings.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
FAMS = os.path.join(BASE, "service", "declarations", "predicate-families.json")
READS = os.path.join(BASE, "declarations", "readings.json")
EXEMPT_KEY = "_families_deliberately_unread"
FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def load():
    f = json.load(open(FAMS, encoding="utf-8"))
    r = json.load(open(READS, encoding="utf-8"))
    declared = {k: v for k, v in (f.get("families") or {}).items() if not k.startswith("_")}
    readings = {k: v for k, v in (r.get("VALUE_READINGS") or {}).items() if not k.startswith("_")}
    exempt = {k: v for k, v in (r.get(EXEMPT_KEY) or {}).items() if not k.startswith("_")}
    return declared, readings, exempt


def main(argv):
    if "--selftest" in argv: return selftest()
    declared, readings, exempt = load()
    date_fams = {k for k, v in declared.items() if (v or {}).get("kind") == "date"}
    print(f"{len(declared)} declared families, {len(readings)} readings, {len(exempt)} exemptions")

    # A1 -- a family with no reading manufactures disagreements, and nothing else says so
    missing = sorted(k for k in declared if k not in readings and k not in exempt and k not in date_fams)
    check(not missing,
          f"A1 all {len(declared) - len(date_fams)} non-date families have a reading or an exemption"
          + ("" if not missing else
             f" -- {len(missing)} have NEITHER: {missing}. A family with no reading groups by the "
             f"LITERAL, so every notational difference becomes a disagreement and RS-G6 cannot see "
             f"it, because a family with no reading is not in RS-G6's population."))

    # A2 -- both ways, because the two files are edited separately
    orphan = sorted(k for k in readings if k not in declared)
    check(not orphan, f"A2 all {len(readings)} readings name a declared family"
          + ("" if not orphan else
             f" -- {len(orphan)} name none: {orphan}. Two files, one fact, and nothing else "
             f"compares them."))

    # A3 -- a reading declared and never implemented is not a reading
    import reading_view as RV
    dead = []
    for f, spec in sorted(readings.items()):
        ex = (spec or {}).get("accepted_forms_by_example") or []
        if not ex: dead.append((f, "declares no worked example to try")); continue
        if not any(RV.read(f, v) is not None for v in ex):
            dead.append((f, f"the shared reader returns nothing for any of {ex[:3]}"))
    check(not dead, f"A3 all {len(readings)} declared readings can be run"
          + ("" if not dead else f" -- {len(dead)} cannot: {dead[:3]}"))

    for f in sorted(exempt):
        print(f"  note {f} is declared deliberately unread: "
              f"{str(exempt[f])[:90]}")
    if FAILS:
        print(f"\nFAMILY READING GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nFAMILY READING GATE: pass"); return 0


def selftest():
    """Both answers, on the state that was actually published."""
    ok = True
    cases = [
        ("A1 the state published at 21:43 -- position declared, reading absent",
         {"declared": ["height", "weight", "birth_date", "draft", "college", "birth_place",
                       "death_place", "position"],
          "readings": ["height", "weight", "birth_date", "draft", "college", "birth_place",
                       "death_place"], "exempt": []}, True),
        ("A1 the same family with a reading",
         {"declared": ["position"], "readings": ["position"], "exempt": []}, False),
        ("A1 a family declared deliberately unread, with a reason",
         {"declared": ["position"], "readings": [], "exempt": ["position"]}, False),
        ("A2 a reading naming no family",
         {"declared": [], "readings": ["position"], "exempt": []}, True),
    ]
    for label, c, want_fail in cases:
        miss = [k for k in c["declared"] if k not in c["readings"] and k not in c["exempt"]]
        orph = [k for k in c["readings"] if k not in c["declared"]]
        failed = bool(miss or orph)
        good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}"
              + (f"  ({len(miss)} without a reading)" if miss else ""))
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
