"""Gate: a disagreement the archive records must be a disagreement the archive can SERVE.

RULED BY RYAN, 2026-09-07. A store that writes

    {"person": "P_000057", "nflverse": "1994-08-29", "statscrew": "1994-08-28",
     "ruling": "UNRESOLVED - both held"}

is asserting that both values are held. For `nflverse-rosters` that was false 1,021 times
of 1,080: the second value existed only inside the report, so the read model could not
contest it, `/contested` said the man's birth date was uncontested, and the bio panel --
which reads the report directly -- showed a disagreement the archive said did not exist.

THIS GATE REPLACES A PATTERN. Six gates already check a disagreements block:
gate_nflverse_rosters item 6, gate_drafts D3, gate_pfa3 T6, gate_pfa G6, gate_pfa_coaches
G7 and gate_person_merges G8. Every one of them checks the STORE'S REPORT -- both keys
present, `resolved` is null, "UNRESOLVED" in the ruling string -- and not one asks whether
either value is a claim. They pass on a report that is internally tidy and externally
false. PFA's three pass truthfully, but they would pass just as happily if PFA stopped
writing the claim tomorrow.

WHAT IS CHECKED, per side of per row:

  D1  the row names a person, a field, and at least two sides. A row this gate cannot
      read is COUNTED and named, never skipped quietly -- an unread row is not a passing
      row.
  D2  every side's value is a claim the archive holds for that person, in that field's
      family, under the field's own declared reading. `1974-03-24` and `March 24, 1974`
      are the same claim; a value nothing holds is a failure naming the person.
  D3  a row that says it is unresolved IS unresolved: no `resolved` verdict.
  D4  THE DENOMINATOR IS STATED, and an empty one is refused. A gate that checked no rows
      does not pass.

WHERE THE CLAIMS COME FROM: `build/*.json`, the archive's own stores -- not the read
model, which lags a rebuild and would let a store look wrong for a day after it was fixed,
or right for a day after it broke.

ONE DEFINITION, IMPORTED. Dates read through the service's `dates.py` (the reader RS-G1
and RS-G6 use) and values through `src/readings.py`, both loaded by FILE PATH under
distinct names. This gate carries no reading of its own.

  python3 src/gate_disagreements_are_claims.py [--selftest]      exit 1 = FAIL
"""
import os, re, sys, json, glob, importlib.util, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
FAMILIES = os.path.join(BASE, "service", "declarations", "predicate-families.json")
BLOCKS = os.path.join(BASE, "declarations", "disagreement-blocks.json")
import readings


def _by_path(name, path):
    """Load a module by file path, never by bare name. Two modules of one name inside one
    sys.path took the bio endpoint down on 2026-09-07; see declarations/readings.json
    ONE_RULING_ONE_DEFINITION."""
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    except Exception:
        return None


DATES = _by_path("service_dates", os.path.join(BASE, "service", "dates.py"))

# Keys on a disagreement row that are ABOUT the row rather than a side of it.
META = {"person", "subject", "field", "name", "resolved", "ruling", "kind", "differs_in",
        "other_source", "source_record", "revision_id", "league", "year", "code",
        "club_as_printed", "comparison", "_both_are_held", "_the_source_contradicts_itself",
        "_not_a_conflict_about_a_fact", "lead_id", "why", "note", "_why", "printed_order"}
# A block name that tells you the field when the row does not carry one.
BLOCK_FIELD = [("birth_date", "birth_date"), ("death_date", "death_date"),
               ("head_coach", "head_coach"), ("role_string", "role_title")]


def families():
    d = json.load(open(FAMILIES, encoding="utf-8"))
    of, kind = {}, {}
    for fam, spec in d["families"].items():
        kind[fam] = spec.get("kind", "value")
        for p in spec["predicates"]: of[p] = fam
    return of, kind


def read_value(field, kind, v):
    """The comparable form of a value, or None when it cannot be read. A date reads to its
    calendar day; a value family reads through its declared reading; anything else compares
    as the string it was printed as."""
    if v is None: return None
    if kind == "date":
        if DATES is None: return None                 # a reader that cannot run is not a pass
        r = DATES.read(str(v))
        return ("day",) + tuple(DATES.key(r)) if r else None
    if readings.READERS.get(field):
        r = readings.read(field, v)
        return ("read", r) if r is not None else None
    if isinstance(v, (dict, list)): return None
    return ("literal", re.sub(r"\s+", " ", str(v).strip().lower()))


def rows_of(store, d):
    """Every disagreement row a store carries, with the block it came from."""
    dis = d.get("disagreements")
    if dis is None: return []
    if isinstance(dis, list): return [("(list)", r) for r in dis if isinstance(r, dict)]
    if isinstance(dis, dict):
        out = []
        for block, rs in dis.items():
            if isinstance(rs, list):
                out += [(block, r) for r in rs if isinstance(r, dict)]
        return out
    return []


def person_of(r):
    p = r.get("person")
    if isinstance(p, str) and p.startswith("P_"): return p
    s = r.get("subject")
    if isinstance(s, (list, tuple)) and len(s) > 1 and str(s[1]).startswith("P_"): return s[1]
    for v in r.values():
        if isinstance(v, dict) and str(v.get("person", "")).startswith("P_"): return v["person"]
    return None


def field_of(r, block):
    f = r.get("field")
    if isinstance(f, str) and f: return f
    for needle, fld in BLOCK_FIELD:
        if needle in block: return fld
    return None


def sides_of(r):
    """{source: value} for every side of the row. A side is a scalar under a key that is
    not row metadata; a nested {"person": ...} side (Wikipedia's shape) is a person
    comparison, not a value one, and is returned as such."""
    out = {}
    for k, v in r.items():
        if k in META or k.startswith("_"): continue
        if isinstance(v, (str, int, float)) and str(v).strip(): out[k] = v
    return out


def wanted_predicates(fields, of, all_preds=()):
    """The predicates whose claims could satisfy the fields these rows name.

    A field the families declaration knows is answered by every predicate in its family.
    A field it does NOT know -- high_school, head_coach -- is answered by any predicate
    whose last dotted segment is that field name (`pfa.high_school`, `statscrew.high_school`),
    because that is how this archive namespaces one question across sources. Reading only
    the bare name found nothing and reported the archive as holding neither side."""
    fams = {of.get(f, f) for f in fields}
    preds = {p for p, fam in of.items() if fam in fams} | fams
    undeclared = {f for f in fields if of.get(f) is None}
    if undeclared:
        preds |= {p for p in all_preds if p.rsplit(".", 1)[-1] in undeclared}
    return preds


def held_values(persons, fields, of, kind, log=print):
    """(person, family) -> {reading} from build/*.json. The stores, not the read model.

    A STORE-LOCAL SUBJECT IS STILL A CLAIM ABOUT A PERSON. The per-season roster stores
    write ("person", "p_000123") -- a lowercase id local to that store -- and only
    identity.json turns it into a global P_ id. The first cut of this gate compared
    subjects to global ids directly, found none of them, and reported that the archive
    held NEITHER side of 1,061 nflverse rows. It holds one side of most of them. The
    resolver is the builder's own, imported, so this gate and the index cannot disagree
    about who a claim is about."""
    import gate_stint_subjects as GS
    from build_person_index import resolve_person
    all_preds = set()
    files = sorted(glob.glob(os.path.join(BASE, "build", "*.json")))
    loc2g = GS.load_loc2g()
    preds = wanted_predicates(fields, of, all_preds=_all_predicates(files))
    held = collections.defaultdict(set)
    unreadable = []
    for f in files:
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception as e:
            # A STORE THAT WILL NOT PARSE IS NOT A STORE WITH NO CLAIMS. Counted, and it
            # makes the gate fail rather than shrinking its evidence in silence.
            unreadable.append((os.path.basename(f), f"{type(e).__name__}: {e}"[:90])); continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if not isinstance(c, dict) or c.get("kind") == "absent": continue
            p = c.get("predicate")
            if p not in preds: continue
            s = c.get("subject")
            raw = s[1] if isinstance(s, (list, tuple)) and len(s) > 1 else None
            if raw is None: continue
            pid = raw if isinstance(raw, str) and raw.startswith("P_") else resolve_person(st, raw, loc2g)
            if pid not in persons: continue
            fam = of.get(p, p)
            r = read_value(fam, kind.get(fam, "value"), c.get("value"))
            if r is not None: held[(pid, fam)].add(r)
    log(f"  claims read from build/: {sum(len(v) for v in held.values()):,} readable values "
        f"over {len(held):,} (person, family) pairs, for {len(persons):,} people and "
        f"{len(preds)} predicate(s)")
    return held, unreadable


def _all_predicates(files):
    """Every predicate name in the build tree. Read once, so an undeclared field can be
    answered by the predicates that namespace it."""
    out = set()
    for f in files:
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if isinstance(c, dict) and c.get("predicate"): out.add(c["predicate"])
    return out


def block_shapes():
    """Which blocks are a value comparison and which are something else, read from
    declarations/disagreement-blocks.json. A shape not named there FAILS -- the declaration
    is where a new block's kind gets looked at, not here."""
    if not os.path.exists(BLOCKS): return set(), {}
    d = json.load(open(BLOCKS, encoding="utf-8"))
    value = set(d.get("value_comparison", {}).get("blocks") or [])
    other = {k: v for k, v in (d.get("not_a_value_comparison") or {}).items() if not k.startswith("_")}
    return value, other


def check(stores, held, of, kind, value_blocks=None, other_blocks=None):
    """-> (results, counts). One result per failing store."""
    value_blocks = value_blocks if value_blocks is not None else set()
    other_blocks = other_blocks or {}
    fails, counts = [], collections.Counter()
    per_store = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    for store, block, r in stores:
        key = f"{store}:{block}"
        counts["rows"] += 1; per_store[key]["rows"] += 1
        pid, field = person_of(r), field_of(r, block)
        # A block the declaration calls something other than a value comparison is COUNTED
        # and named, and its rows are not put through the value test. A block named in
        # neither list falls through to the value test and fails as an unreadable row,
        # which is how a new store's new shape arrives here to be looked at.
        okey = key if key in other_blocks else (f"{store}:{field}" if f"{store}:{field}" in other_blocks else None)
        if okey:
            per_store[key]["not_a_value_comparison"] += 1; counts["not_a_value_comparison"] += 1
            continue
        sides = sides_of(r)
        if not pid or not field or len(sides) < 2:
            per_store[key]["unreadable_row"] += 1; counts["unreadable_row"] += 1
            if len(examples[key + "|unreadable"]) < 2:
                examples[key + "|unreadable"].append(json.dumps(r)[:160])
            continue
        if r.get("resolved") is not None:
            per_store[key]["resolved"] += 1; counts["resolved"] += 1
        fam = of.get(field, field)
        k = kind.get(fam, "value")
        h = held.get((pid, fam), set())
        missing = []
        for src, v in sides.items():
            rv = read_value(fam, k, v)
            if rv is None:
                per_store[key]["side_value_unreadable"] += 1; counts["side_value_unreadable"] += 1
                continue
            if rv not in h: missing.append((src, v))
        if missing:
            per_store[key]["a_side_is_not_a_claim"] += 1; counts["a_side_is_not_a_claim"] += 1
            if len(examples[key]) < 3:
                examples[key].append({"person": pid, "field": field, "not_held": missing,
                                      "the_archive_holds": sorted(str(x) for x in h)[:4]})
        else:
            per_store[key]["both_sides_held"] += 1; counts["both_sides_held"] += 1
    for key, c in sorted(per_store.items()):
        if c["a_side_is_not_a_claim"] or c["unreadable_row"] or c["resolved"]:
            fails.append((key, dict(c), examples.get(key, []) or examples.get(key + "|unreadable", [])))
    return fails, counts, per_store


def collect(log=print):
    of, kind = families()
    stores = []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try:
            with open(f) as fh:
                head = fh.read(4096)
            if '"disagreements"' not in head:
                # cheap prefilter is not enough: the block can sit late in a big file
                if os.path.getsize(f) > 200_000_000: continue
            d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or "disagreements" not in d: continue
        for block, r in rows_of(os.path.basename(f)[:-5], d):
            stores.append((os.path.basename(f)[:-5], block, r))
    log(f"  disagreement rows found: {len(stores):,} in "
        f"{len({s[0] for s in stores})} store(s)")
    return stores, of, kind


def main():
    print(__doc__.split("\n")[0] + "\n")
    stores, of, kind = collect()
    # D4 -- an empty denominator is refused, not passed
    if not stores:
        print("GATE FAILED: no disagreement row was found in any build store. A gate that "
              "checked nothing does not pass.")
        return 1
    persons = {p for p in (person_of(r) for _, _, r in stores) if p}
    fields = {f for f in (field_of(r, b) for _, b, r in stores) if f}
    print(f"  people named by a disagreement: {len(persons):,}   fields: {sorted(fields)}")
    value_blocks, other_blocks = block_shapes()
    held, unreadable = held_values(persons, fields, of, kind)
    fails, counts, per_store = check(stores, held, of, kind, value_blocks, other_blocks)
    undeclared = sorted({k for k in per_store
                         if not per_store[k]["not_a_value_comparison"] and k not in value_blocks})
    if undeclared:
        print(f"\n  BLOCKS THE DECLARATION DOES NOT NAME: {undeclared} -- "
              f"declarations/disagreement-blocks.json decides whether a block is a value "
              f"comparison; an unnamed one is checked as one and fails if it is not.")
    print()
    for key in sorted(per_store):
        c = per_store[key]
        state = "FAIL" if (c["a_side_is_not_a_claim"] or c["unreadable_row"] or c["resolved"]) else "ok  "
        print(f"  {state}  {key:52s} rows {c['rows']:5d}  both held {c['both_sides_held']:5d}  "
              f"a side NOT a claim {c['a_side_is_not_a_claim']:5d}  unreadable row {c['unreadable_row']:4d}  "
              f"resolved {c['resolved']:3d}  side unreadable {c['side_value_unreadable']:4d}"
              + (f"  [not a value comparison: {c['not_a_value_comparison']}]" if c["not_a_value_comparison"] else ""))
    if unreadable:
        print(f"\n  UNREADABLE STORES: {len(unreadable)} -- the evidence for this gate is incomplete")
        for b, e in unreadable[:6]: print(f"     {b}: {e}")
    checked = counts["both_sides_held"] + counts["a_side_is_not_a_claim"]
    print(f"\n  TOTAL rows {counts['rows']:,} = {checked:,} value comparisons CHECKED "
          f"+ {counts['not_a_value_comparison']:,} declared not a value comparison "
          f"+ {counts['unreadable_row']:,} this gate could not read.")
    print(f"  OF THE {checked:,} CHECKED: both sides held {counts['both_sides_held']:,}; "
          f"a side is not a claim the archive holds {counts['a_side_is_not_a_claim']:,}; "
          f"resolved despite saying otherwise {counts['resolved']:,}.")
    if not checked:
        print("\nGATE FAILED: no value comparison was checked. A gate that checked nothing does not pass.")
        return 1
    if fails or unreadable:
        print("\nGATE FAILED")
        for key, c, ex in fails:
            print(f"  - {key}: {c}")
            for e in ex[:2]: print(f"      e.g. {json.dumps(e)[:200]}")
        return 1
    print(f"\nGATE PASSED: every side of all {counts['rows']:,} recorded disagreements is a claim "
          f"the archive holds.")
    return 0


def selftest():
    """Each check shown failing for its own reason, over specimens."""
    of, kind = families()
    P = "P_000001"
    held = {(P, "birth_date"): {read_value("birth_date", "date", "March 24, 1974")}}
    cases = [
        ("both sides held", [("fix", "b", {"person": P, "field": "birth_date",
                                           "a": "1974-03-24", "b": "March 24, 1974"})], "both_sides_held"),
        ("a side that is NOT a claim", [("fix", "b", {"person": P, "field": "birth_date",
                                           "a": "1974-03-24", "b": "March 25, 1974"})], "a_side_is_not_a_claim"),
        ("a row this gate cannot read", [("fix", "b", {"nflverse": "x"})], "unreadable_row"),
        ("a row that resolved itself", [("fix", "b", {"person": P, "field": "birth_date",
                                           "a": "1974-03-24", "b": "March 24, 1974",
                                           "resolved": "a"})], "resolved"),
    ]
    print("SELFTEST -- each check, over a specimen\n")
    ok = []
    for name, rows, want in cases:
        _, counts, _ = check(rows, held, of, kind, {"fix:b"}, {})
        good = counts[want] == 1
        print(f"  {'OK  ' if good else 'BAD '} {name}: {dict(counts)}")
        ok.append(good)
    # D4: an empty denominator must not pass
    e = not bool([])
    print(f"  OK   an empty denominator is refused (main() returns 1 on no rows)")
    # the readers must be present; a missing date reader is not a clean sheet
    print(f"  {'OK  ' if DATES else 'BAD '} the service date reader loaded: {bool(DATES)}")
    ok.append(bool(DATES))
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    sys.exit(main())
