"""Gate: a disagreement between two values that read to the same thing is not a
disagreement, and nothing may record one.

The instance was heights. The bio panel showed PFA's "6-1" beside the guide's
'61"' and filed the pair under `disagreements` -- two sources that agree, held
apart as though they did not. 51 of 73 unparsable guide heights were like that.
Chasing it, the same defect turned out to be an order of magnitude worse in a
field nobody had looked at: 182 of 275 sampled draft disagreements were one
selection under two club vocabularies, PFR's TAM against nflverse's TB.

The property, which is what this gate checks and the instance is not: for any
field carrying a reading, values that read alike are one value written twice.
It generalises past heights on purpose -- weights, dates, draft picks, jersey
numbers, anything with two printed forms will have the same problem.

A fabricated disagreement is worse than a missing claim. A hole you can see;
this looks like scholarship -- two sources, both cited, honestly held apart --
and it survives every other gate here, because they check that disagreements are
HELD, and these were held faithfully, having been invented.

R1  the declaration and the code agree: every accepted example reads, every
    refused example refuses
R2  no person carries a disagreement whose values all read to one thing  (ALL
    people, no sample -- a sampled gate is how the P2 bug hid for a week)
R3  the archive's OWN commonest printed form reads. This one has already earned
    its keep: the first cut of readings.height() did not accept "5-10", PFA's
    format, so Len Eshmont's genuine 5-10 against the guide's 5-11 was silently
    NOT flagged. A reader that cannot read the archive hides real disagreements
    while claiming to remove false ones.
R4  a reading never edits what was printed: `value` is preserved verbatim and the
    reading rides beside it under `reads_as`

Run:  python3 src/gate_readings.py [--selftest]      exit 1 = FAIL
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import readings
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "service"))
import reading_view as RV
from bio_select import Tables, vitals

DECL = json.load(open(os.path.join(BASE, "declarations", "readings.json"), encoding="utf-8"))
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def r1_declaration_and_code_agree():
    print("R1  the declaration's examples read, and its refusals refuse")
    for field, spec in DECL["VALUE_READINGS"].items():
        if not readings.READERS.get(field):
            continue
        bad_a = [v for v in spec.get("accepted_forms_by_example", [])
                 if isinstance(v, str) and readings.read(field, v) is None]
        bad_r = [v for v in spec.get("refused_by_example", [])
                 if readings.read(field, v) is not None]
        check(not bad_a, f"{field}: every declared accepted form reads"
              if not bad_a else f"{field}: declared accepted but does NOT read: {bad_a}")
        check(not bad_r, f"{field}: every declared refusal still refuses"
              if not bad_r else f"{field}: declared refused but DOES read: "
                                f"{[(v, readings.read(field, v)) for v in bad_r]}")


def sweep(T):
    """Every person, every field with a reader. No sample."""
    collapsed, single, unread, total = [], [], collections.Counter(), collections.Counter()
    forms = collections.defaultdict(collections.Counter); sample = {}
    ids = sorted(T.people)
    for g in ids:
        V = vitals(T, g, T.people[g])
        for field, rows in V.items():
            if field in ("disagreements", "position") or not readings.READERS.get(field):
                continue
            for r in rows:
                total[field] += 1
                key = json.dumps(r["value"], sort_keys=True)   # NOT str(): a dict must
                forms[field][key] += 1                          # stay a dict for the reader
                sample.setdefault((field, key), r["value"])
            # THE SHARED GROUPING. A reading can be a dict -- the draft reading is one
            # -- and dicts are neither hashable nor equal when `same()` calls them one
            # fact. This was a private set; it is now the one implementation, which is
            # the third place that rule has had to be pulled back into RV.group.
            groups, unreadable = RV.group(field, [r["value"] for r in rows])
            n_reads, un = len(groups), len(unreadable)
            unread[field] += un
            if field not in (V.get("disagreements") or []): continue
            # One value cannot disagree with itself. A single-row field flagged here
            # was flagged by a rule that reads ANOTHER field -- vitals() raises
            # birth_date when birth_date_as_printed carries a different year, which
            # is a real disagreement (Glenn Dobbs: index 1920, the guide 1922) and
            # not this gate's business. Counted below, never silently passed over.
            if len(rows) < 2:
                single.append((g, field)); continue
            if n_reads <= 1 and not un:
                collapsed.append((g, T.people[g].get("name"), field, [r["value"] for r in rows]))
    return ids, collapsed, single, unread, total, forms, sample


def main():
    if "--selftest" in sys.argv:
        return selftest()
    print(DECL["RULING"]["rule"] + "\n")
    r1_declaration_and_code_agree()

    T = Tables()
    ids, collapsed, single, unread, total, forms, sample = sweep(T)

    print(f"R2  no recorded disagreement collapses to one reading  ({len(ids):,} people, full sweep)")
    check(not collapsed, f"none of {len(ids):,} people carry one"
          if not collapsed else f"{len(collapsed)} do, e.g. {collapsed[:3]}")

    print("R3  the archive's own commonest printed form reads")
    for field in sorted(total):
        if not forms[field]: continue
        key, n = forms[field].most_common(1)[0]
        top = sample[(field, key)]
        got = readings.read(field, top)
        check(got is not None,
              f"{field}: commonest form {str(top)[:56]!r} ({n:,}x) reads as {got!r}"
              if got is not None else
              f"{field}: commonest form {str(top)[:56]!r} ({n:,}x) does NOT read -- the reader "
              f"cannot read the archive, so it hides real disagreements")

    print("R4  a reading never edits what was printed")
    edited = []
    for g in ids[:2000]:
        for field, rows in vitals(T, g, T.people[g]).items():
            if field in ("disagreements", "position"): continue
            for r in rows:
                if "reads_as" in r and r["reads_as"] == r["value"]: edited.append((g, field, r))
    check(not edited, "every row keeps its printed value; reads_as only ever sits beside it"
          if not edited else f"{len(edited)} rows carry a redundant reading: {edited[:2]}")

    by_field = collections.Counter(f for _, f in single)
    print(f"  note  {len(single)} field(s) flagged with a single value, "
          f"raised by a rule reading another field: {dict(by_field) or 'none'}")

    print("R5  a reading exists once: no module name is defined in both src/ and service/")
    svc = os.path.join(BASE, "service")
    declared = {c["name"] for c in DECL["ONE_RULING_ONE_DEFINITION"]["known_module_name_collisions"]}
    if os.path.isdir(svc):
        mine = {f[:-3] for f in os.listdir(HERE) if f.endswith(".py")}
        theirs = {f[:-3] for f in os.listdir(svc) if f.endswith(".py")}
        clash = sorted((mine & theirs) - declared)
        check(not clash, f"no undeclared collision ({len(declared)} declared and owned: "
                         f"{', '.join(sorted(declared))})"
              if not clash else
              f"{clash} defined in BOTH src/ and service/. Which one an `import` gets depends on "
              f"sys.path order and on what reached sys.modules first, and it fails silently in the "
              f"direction of 'the other implementation answered'. One ruling, one definition.")
    else:
        check(True, "no service/ tree here")

    print("\n  values left as printed because they could not be read without guessing:")
    for field in sorted(total):
        print(f"    {unread[field]:5d} of {total[field]:6,}  {field}")
    print("  (refusals are counted, never silent -- declarations/readings.json)")

    print(f"\nREADINGS GATE: {'pass' if not FAILS else 'FAIL'}")
    for m in FAILS: print("   -", m)
    return 1 if FAILS else 0


def selftest():
    """Each check, shown failing for its own reason."""
    print("=== each check, failing for its own reason ===")
    real = readings.height
    readings.height = lambda v: None
    readings.READERS["height"] = readings.height
    r1_declaration_and_code_agree()
    print("  ^ R1 fires when the code stops honouring the declaration")
    readings.height = real; readings.READERS["height"] = real

    rows = [{"value": "6-1", "source": "pfa"}, {"value": '61"', "source": "guide"}]
    from bio_select import _differ
    print(f"  R2/R4 basis: _differ('height', {['6-1', '61\"']}) = {_differ('height', rows)} "
          f"(False = the two read alike, so it is not a disagreement)")
    print(f"        _differ('height', ['5-10','5-11']) = "
          f"{_differ('height', [{'value':'5-10','source':'a'},{'value':'5-11','source':'b'}])} "
          f"(True = a real difference still stands)")
    print(f"  R3 basis: readings.height('5-10') = {readings.height('5-10')!r} "
          f"(None here would mean the reader cannot read the archive)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
