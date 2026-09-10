"""Every gate must FAIL when its invariant is broken. A gate that has only ever
passed has not been tested (dataset/README.md). Builds a tiny read model in a
temp directory from fixture stores, breaks one invariant per gate, and asserts
the gate fails BY NAME.

    python3 gate_selftest.py
"""
import os, sys, json, sqlite3, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gates, dates


def mini_model(claims, date_rows=(), stores=(), sources=()):
    conn = sqlite3.connect(":memory:")
    conn.executescript(__import__("build_read_model").SCHEMA)
    for i, c in enumerate(claims, 1):
        row = {"id": i, "store": "fix", "cid": f"c_{i}", "scope": "person", "subject": json.dumps(["person", "p_1"]), "s1": "p_1", "person": "P_1",
               "league": None, "year": None, "club_str": None, "club_id": None, "club_via": None, "predicate": "birth_date", "family": "birth_date",
               "value": json.dumps("May 12, 1925"), "value_text": "May 12, 1925", "source_id": "fix", "source_record": "fix#r1", "sr_in_table": 1,
               "stated_by": "fixture", "attribution": "[]", "kind": "observed", "observed_at": "1925", "observed_year": 1925, "note": None, "extra": None}
        row.update(c)
        conn.execute("INSERT INTO claim VALUES(" + ",".join("?" * 26) + ")", list(row.values()))
    for r in date_rows: conn.execute("INSERT INTO date_reading VALUES(?,?,?,?,?,?,?,?,?,?)", r)
    for s in stores: conn.execute("INSERT INTO store VALUES(?,?,?,?,?,?)", s)
    for s in sources: conn.execute("INSERT INTO source VALUES(?,?,?)", s)
    return conn


SKIPPED = []


def expect(name, result, status):
    ok = result["status"] == status
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: expected {status}, got {result['status']}  {result['counts']}")
    return ok


def skip(name, why):
    """A check that could not run says so BY NAME. It never counts as a pass: a self-test
    that quietly shrinks on a machine missing its inputs is the vacuous pass this project
    keeps finding, one level up."""
    SKIPPED.append((name, why))
    print(f"  SKIP {name}: {why}")
    return True


def with_dates_decl(entries):
    """Point G1 at a temp declaration so the self-test does not depend on what is declared today."""
    d = tempfile.mkdtemp(); p = os.path.join(d, "dates-as-printed.json")
    json.dump({"accepted_as_printed": [{"string": e} for e in entries]}, open(p, "w"))
    gates.DATES_DECL = p


def main():
    allok = True
    real_decl = gates.DATES_DECL
    bad = "selftest-not-a-date-and-never-declared"     # a real string could be declared as printed; this one cannot be
    readable = [(1, "birth_date", "May 12, 1925", 1925, 5, 12, "day", 0, None, 1)]
    unreadable = [(2, "birth_date", bad, None, None, None, None, None, None, 0)]
    # G1: an unreadable, undeclared string fails; readable passes; declared passes; a declared string NO LONGER SEEN fails (ruled 2026-09-07)
    with_dates_decl([])
    conn = mini_model([{}, {"id": 2, "value": json.dumps(bad), "value_text": bad}], date_rows=readable + unreadable)
    allok &= expect("RS-G1 unreadable undeclared string", gates.g1(conn, {}), "FAIL")
    conn = mini_model([{}], date_rows=readable)
    allok &= expect("RS-G1 readable string", gates.g1(conn, {}), "PASS")
    with_dates_decl([bad])
    conn = mini_model([{}, {"id": 2, "value": json.dumps(bad), "value_text": bad}], date_rows=readable + unreadable)
    allok &= expect("RS-G1 unreadable but declared string", gates.g1(conn, {}), "PASS")
    conn = mini_model([{}], date_rows=readable)
    allok &= expect("RS-G1 declared string no longer in the store", gates.g1(conn, {}), "FAIL")
    gates.DATES_DECL = real_decl
    # G2: an unresolved person in an undeclared store fails; in a declared store passes
    conn = mini_model([{"person": None, "store": "not-declared-anywhere"}])
    allok &= expect("RS-G2 unresolved in undeclared store", gates.g2(conn, {}), "FAIL")
    if os.path.exists(gates.paths.INDEX_REBUILD_DECL):
        decl = json.load(open(gates.paths.INDEX_REBUILD_DECL))
        some = next(k for k in decl["known_unresolvable_stores"] if not k.startswith("_"))
        conn = mini_model([{"person": None, "store": some}])
        allok &= expect(f"RS-G2 unresolved in declared store ({some})", gates.g2(conn, {}), "PASS")
    else:
        allok &= skip("RS-G2 unresolved in a DECLARED store",
                      f"needs the archive's {os.path.relpath(gates.paths.INDEX_REBUILD_DECL, gates.paths.DATASET)}, "
                      f"which is not on this machine")
    # G3: a claim naming a record not in its store's table fails; a claim naming no record fails
    conn = mini_model([{"sr_in_table": 0}]); allok &= expect("RS-G3 record not in table", gates.g3(conn, {}), "FAIL")
    conn = mini_model([{"source_record": None, "sr_in_table": None}]); allok &= expect("RS-G3 no record", gates.g3(conn, {}), "FAIL")
    conn = mini_model([{}]); allok &= expect("RS-G3 record present", gates.g3(conn, {}), "PASS")
    # G4: a person here and not in the index fails; and the reverse; equal passes
    conn = mini_model([])
    allok &= expect("RS-G4 here not in index", gates.g4(conn, {"index_keys": {"P_1"}, "people": {"P_1", "P_2"}}), "FAIL")
    allok &= expect("RS-G4 in index not here", gates.g4(conn, {"index_keys": {"P_1", "P_2"}, "people": {"P_1"}}), "FAIL")
    allok &= expect("RS-G4 equal", gates.g4(conn, {"index_keys": {"P_1"}, "people": {"P_1"}}), "PASS")
    # G5: every build file is a store, or explained. Eight cases against a temp build dir.
    import tempfile, glob as _glob
    real_build, real_bf = gates.paths.BUILD, gates.BUILD_FILES_DECL
    try:
        tmp = tempfile.mkdtemp()
        gates.paths.BUILD = tmp
        # the declaration must live OUTSIDE the build dir, or the gate globs it as a build file
        gates.BUILD_FILES_DECL = tmp + "-decl.json"

        def put(name, obj):
            fp = os.path.join(tmp, name + ".json")
            with open(fp, "w") as fh: json.dump(obj, fh)
            return fp

        def decl(by_name=None, array_rule=True):
            with open(gates.BUILD_FILES_DECL, "w") as fh:
                json.dump({"not_a_claim_store": {
                    "by_name": by_name or {},
                    "by_shape": ([{"when": "top_level_is_an_array", "why": "fixture"}] if array_rule else [])}}, fh)

        def model(inputs=()):
            c = mini_model([])
            for name in inputs:
                fp = os.path.join(tmp, name + ".json"); st = os.stat(fp)
                c.execute("INSERT INTO input VALUES(?,?,?)", (f"build/{name}.json", st.st_mtime_ns, st.st_size))
            return c

        def clear():
            for f in _glob.glob(os.path.join(tmp, "*.json")): os.remove(f)

        # 1. read by the build, has claims, not a store -> the defect this gate exists for
        clear(); put("dropped", {"claims": [{"x": 1}]}); decl()
        allok &= expect("RS-G5 claim store the build read and dropped", gates.g5(model(["dropped"]), {}), "FAIL")
        # 2. same file, never an input -> pending a rebuild, not a failure
        allok &= expect("RS-G5 claim store written since the build", gates.g5(model([]), {}), "PASS")
        # 3. an unreadable file fails, and stays failing even if someone declares it
        clear()
        with open(os.path.join(tmp, "torn.json"), "w") as fh: fh.write("{not json")
        decl(); allok &= expect("RS-G5 unparseable file", gates.g5(model([]), {}), "FAIL")
        decl({"torn": {"why": "trying to declare a broken file away"}})
        allok &= expect("RS-G5 unparseable file, declared anyway", gates.g5(model([]), {}), "FAIL")
        # 4/5. an object with no claims: undeclared fails, declared passes
        clear(); put("notes", {"counts": {}, "decided_at": "x"}); decl()
        allok &= expect("RS-G5 undeclared non-store", gates.g5(model([]), {}), "FAIL")
        decl({"notes": {"why": "a decision record", "read_as": "decision record"}})
        allok &= expect("RS-G5 declared non-store", gates.g5(model([]), {}), "PASS")
        # 6. THE HALF THAT MAKES IT NOTICE: a declared file that has grown a claims list
        clear(); put("notes", {"counts": {}, "claims": [{"x": 1}]})
        decl({"notes": {"why": "a decision record", "read_as": "decision record"}})
        allok &= expect("RS-G5 declared file that grew claims", gates.g5(model([]), {}), "FAIL")
        # 7. a declared file that no longer exists
        clear(); decl({"vanished": {"why": "declared, but gone"}})
        allok &= expect("RS-G5 declared file now missing", gates.g5(model([]), {}), "FAIL")
        # 8. the array rule covers a bare list, and withdrawing the rule uncovers it
        clear(); put("worklist", [1, 2, 3]); decl()
        allok &= expect("RS-G5 array under the shape rule", gates.g5(model([]), {}), "PASS")
        decl(array_rule=False)
        allok &= expect("RS-G5 array with the shape rule withdrawn", gates.g5(model([]), {}), "FAIL")
        # P4 (Fetching's, from gate_photographs_measurable.py): the gate must SHOW the
        # reader something it cannot read and require it to notice. A predicate that
        # quietly widens or narrows must fail RS-G5, not slip past it.
        import build_read_model as _B
        real_pred = _B.is_claim_store
        try:
            clear(); decl()
            allok &= expect("RS-G5 P4 baseline, reader unchanged", gates.g5(model([]), {}), "PASS")
            _B.is_claim_store = lambda d: True          # the reader silently gains a shape
            allok &= expect("RS-G5 P4 reader widened to accept anything", gates.g5(model([]), {}), "FAIL")
            _B.is_claim_store = lambda d: False         # the reader silently loses its own shape
            allok &= expect("RS-G5 P4 reader narrowed to accept nothing", gates.g5(model([]), {}), "FAIL")
        finally:
            _B.is_claim_store = real_pred
    finally:
        gates.paths.BUILD, gates.BUILD_FILES_DECL = real_build, real_bf
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(tmp + "-decl.json"): os.remove(tmp + "-decl.json")
    # RS-G6: a false disagreement must fail; a real one must not; and a reader that
    # cannot run must NOT report a clean sheet it did not check.
    import reading_view as RV
    def contested_model(rows):
        c = mini_model([])
        for pid, fam, groups in rows:
            c.execute("INSERT INTO contested VALUES(?,?,?,?,?,?)",
                      (pid, fam, "", len(groups), json.dumps(groups),
                       json.dumps([v for g in groups for v in g])))
        return c
    cols = [r[1] for r in mini_model([]).execute("PRAGMA table_info(contested)")]
    # THE SHAPE IS ASSERTED, NOT USED AS A CONDITION. This was an `if` on the column
    # list, so widening the table to carry the year would have SKIPPED every check below
    # and reported a clean sheet -- a guard turning a real failure into a confident pass,
    # which is a defect this archive has found four separate ways.
    assert cols == ["person", "family", "year", "n_groups", "groups", "literals"], \
        f"contested schema changed to {cols}; these checks must be updated, not skipped"
    if True:
        same_day = [["May 12, 1925"], ["1925-05-12"]]          # one day, recorded as two groups
        two_days = [["May 12, 1925"], ["May 13, 1925"]]        # genuinely two days
        allok &= expect("RS-G6 two groups that read to one day",
                        gates.g6(contested_model([("P_1", "birth_date", same_day)]), {}), "FAIL")
        allok &= expect("RS-G6 two groups that are genuinely different days",
                        gates.g6(contested_model([("P_1", "birth_date", two_days)]), {}), "PASS")
        real = RV._shared_reader
        try:
            RV._shared_reader = lambda: None
            allok &= expect("RS-G6 with the shared reader unavailable",
                            gates.g6(contested_model([("P_1", "birth_date", two_days)]), {}), "FAIL")
        finally:
            RV._shared_reader = real
    else:
        allok &= skip("RS-G6 false-disagreement cases",
                      f"the contested table is {cols} here, not the shape the fixture writes")
    # ---- G8: what a thing IS, declared. Four injuries, mirroring the four ways the
    # declaration can be wrong. The fixture is two stores: one all-statistics, one all
    # roster, plus one staff store and one name predicate.
    import classification as C
    def g8_model():
        # TWO statistics stores sharing a vocabulary and TWO roster stores sharing
        # one, because that is what the archive looks like -- `stats-nfl-2024` and
        # `stats-nfl-2025` carry the same columns. A fixture of one store each would
        # have nothing to straddle and would let the gate pass on an empty declaration,
        # which is exactly the false pass the first version of this gate gave.
        cl = []
        for j, st in enumerate(["stats-fix-1999", "stats-fix-2000"]):
            for i, pr in enumerate(["passing.Att", "rushing.Yds"], 1):
                cl.append({"store": st, "scope": "stint", "predicate": pr, "family": pr, "cid": f"s{j}{i}"})
        for j, st in enumerate(["fix-1999", "fix-2000"]):
            for i, pr in enumerate(["jersey", "games_played"], 1):
                cl.append({"store": st, "scope": "stint", "predicate": pr, "family": pr, "cid": f"r{j}{i}"})
        for i, pr in enumerate(["is_head_coach", "shared_or_split_season"], 1):
            cl.append({"store": "coaches-fix", "scope": "stint", "predicate": pr, "family": pr, "cid": f"c{i}"})
        cl.append({"store": "fix", "scope": "person", "predicate": "statscrew.formal_name", "family": "name", "cid": "n1"})
        return mini_model(cl)
    base = {"name_forms": {"generational_suffixes": ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"], "worked_examples": {}},
            "statistic_stores": {"stores": ["stats-fix-1999", "stats-fix-2000"]},
            "staff_predicates": {"predicates": ["is_head_coach"], "stores_that_carry_them": ["coaches-fix"],
                                 "not_staff_though_it_appears_in_those_stores": {"shared_or_split_season": "a qualifier"}},
            "name_predicates": {"predicates": ["statscrew.formal_name"]}}
    with tempfile.TemporaryDirectory() as td:
        # BOTH DECLARATIONS. `staff_predicates` moved to dataset/declarations/
        # coaching-seasons.json on 2026-09-09 -- the archive's ruling, shared with
        # build_person_index -- so a fixture that overrode only the service's file left
        # the staff cases reading the REAL list and passing when they should fail. The
        # self-test caught that, which is what it is for.
        real_path, real_d = C._PATH, C._D
        real_apath, real_a = C._ARCHIVE_PATH, C._A
        def decl8(d):
            f = os.path.join(td, "classification.json"); json.dump(d, open(f, "w"))
            a = os.path.join(td, "coaching-seasons.json")
            json.dump({"staff_predicates": d.get("staff_predicates", {"predicates": [], "stores_that_carry_them": [],
                                                                     "not_staff_though_it_appears_in_those_stores": {}})},
                      open(a, "w"))
            C._PATH, C._D = f, None
            C._ARCHIVE_PATH, C._A = a, None
        try:
            decl8(base)
            allok &= expect("RS-G8 declaration matches the model", gates.g8(g8_model(), {}), "PASS")
            d = json.loads(json.dumps(base)); d["statistic_stores"]["stores"].remove("stats-fix-2000")
            decl8(d); allok &= expect("RS-G8 statistics store left undeclared", gates.g8(g8_model(), {}), "FAIL")
            d = json.loads(json.dumps(base)); d["statistic_stores"]["stores"] = []
            decl8(d); allok &= expect("RS-G8 EVERY statistics store undeclared -- the limit, stated: nothing straddles",
                                      gates.g8(g8_model(), {}), "PASS")
            d = json.loads(json.dumps(base)); d["statistic_stores"]["stores"].append("fix-1999")
            decl8(d); allok &= expect("RS-G8 roster store wrongly declared a statistics store", gates.g8(g8_model(), {}), "FAIL")
            d = json.loads(json.dumps(base)); d["staff_predicates"]["predicates"] = []
            decl8(d); allok &= expect("RS-G8 staff predicate dropped", gates.g8(g8_model(), {}), "FAIL")
            d = json.loads(json.dumps(base)); d["staff_predicates"]["not_staff_though_it_appears_in_those_stores"] = {}
            decl8(d); allok &= expect("RS-G8 a staff store's other predicate neither declared nor excluded", gates.g8(g8_model(), {}), "FAIL")
            d = json.loads(json.dumps(base)); d["name_predicates"]["predicates"] = []
            decl8(d); allok &= expect("RS-G8 name predicate dropped", gates.g8(g8_model(), {}), "FAIL")
            # the name-form reading, against its own declared examples
            d = json.loads(json.dumps(base))
            d["name_forms"] = {"generational_suffixes": ["jr", "jr."],
                               "worked_examples": {"surname_first": ["Pollard, Frederick Douglass"],
                                                   "forename_first": ["Robert D. Bean, Jr."]}}
            decl8(d); allok &= expect("RS-G8 name-form reading matches its worked examples", gates.g8(g8_model(), {}), "PASS")
            d2 = json.loads(json.dumps(d)); d2["name_forms"]["generational_suffixes"] = []
            decl8(d2); allok &= expect("RS-G8 suffix list emptied -- 'Robert D. Bean, Jr.' misreads", gates.g8(g8_model(), {}), "FAIL")
            d2 = json.loads(json.dumps(d)); d2["name_forms"]["worked_examples"]["forename_first"] = ["Pollard, Frederick Douglass"]
            decl8(d2); allok &= expect("RS-G8 an example declared the wrong way round", gates.g8(g8_model(), {}), "FAIL")
            # the bare-surname rule, both answers
            d3 = json.loads(json.dumps(d))
            d3["name_forms"]["worked_examples"]["bare_surname_set_aside"] = [["Plunkett", ["Joseph T. Plunkett"]]]
            d3["name_forms"]["worked_examples"]["bare_surname_kept"] = [["Plunkett", ["Plunkett"]], ["Joe Plunkett", ["Joseph T. Plunkett"]]]
            decl8(d3); allok &= expect("RS-G8 the bare-surname rule matches its examples", gates.g8(g8_model(), {}), "PASS")
            d4 = json.loads(json.dumps(d3))
            d4["name_forms"]["worked_examples"]["bare_surname_kept"] = [["Plunkett", ["Joseph T. Plunkett"]]]
            decl8(d4); allok &= expect("RS-G8 a bare surname the ruling KEEPS is being set aside", gates.g8(g8_model(), {}), "FAIL")
            d5 = json.loads(json.dumps(d3))
            d5["name_forms"]["worked_examples"]["bare_surname_set_aside"] = [["Joe Plunkett", ["Joseph T. Plunkett"]]]
            decl8(d5); allok &= expect("RS-G8 a multi-word name declared a bare surname -- the case this ruling does NOT decide",
                                       gates.g8(g8_model(), {}), "FAIL")
        finally:
            C._PATH, C._D = real_path, real_d
            C._ARCHIVE_PATH, C._A = real_apath, real_a

    # the same-day grouping must keep two different days apart and join two spellings of one day
    g = dates.same_day_groups([("May 12, 1925", dates.read("May 12, 1925")), ("1925-05-12", dates.read("1925-05-12")), ("May 13, 1925", dates.read("May 13, 1925"))])
    ok = g == [["May 12, 1925", "1925-05-12"], ["May 13, 1925"]]; allok &= ok
    print(f"  {'ok  ' if ok else 'FAIL'} same-day grouping: {g}")
    if SKIPPED:
        print(f"SELFTEST OK, but {len(SKIPPED)} check(s) COULD NOT RUN here:")
        for n, w in SKIPPED: print(f"  - {n}: {w}")
        print("  These are not passes. Run again where the archive is present.")
    else:
        print("SELFTEST", "OK" if allok else "FAILED")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
