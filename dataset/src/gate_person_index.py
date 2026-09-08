"""Gate: the person index can be rebuilt without losing anyone's work.

THREE PROPERTIES, checked over ALL of src/, not over a list of known files.

P1  EVERY WRITER IS DECLARED. Any script in src/ that writes the index must be
    named in declarations/person-index-rebuild.json -- either in `chain` (it is a
    post-processing patch the rebuild must re-run, in order) or in `exempt` with a
    reason. A writer that is in neither FAILS THE GATE BY NAME. This is the exact
    failure of 2026-09-06: a patcher was written, a rebuild ran, the patch vanished.

P2  NO WRITER IS IN-PLACE. `json.dump(x, open(<index>, "w"))` on a 347 MB gitignored
    file is destroyed by an interrupt. Every write must go through
    index_io.save_index / dump_atomic (temp file, fsync, os.replace).

P4  NO STINT SUBJECT IS SKIPPED IN SILENCE. gate_stint_subjects.py resolves every stint
    subject in every store exactly as the builder does (one shared function). A store
    with an unresolvable subject refuses the rebuild UNLESS it is declared in
    known_unresolvable_stores or held_stores with its reason -- declared, counted and
    printed on every build, never silent. This is the check P3 cannot be: a store
    that never enters is 0 -> 0 on both sides of P3.

P3  A REBUILD LOSES NOTHING. Called by build_person_index.py around the rebuild:
    every season key every person held BEFORE must still be held AFTER, and no
    counted field (coaching seasons, officiating seasons, club-key rewrites, CFL
    1945 restores, merges) may fall. If it does the rebuild is ROLLED BACK and the
    build exits non-zero. This is the check that a careful session happened to do
    by hand on 2026-09-06; it is now the check, not the session.

  python3 src/gate_person_index.py            # P1 + P2, static, exit 1 on failure
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
DECL = os.path.join(BASE, "declarations", "person-index-rebuild.json")
INDEX_BASENAME = "person-index.json"

# names that, anywhere in src/, denote the index path
KNOWN_IDENTS = {"IDXP", "IDX_PATH", "INDEX_PATH", "AP.IDXP", "IO.INDEX_PATH"}


def _index_idents(src):
    """Identifiers in this file that hold the index path: the known names plus any
    local assignment whose right-hand side mentions person-index.json."""
    idents = set(KNOWN_IDENTS)
    for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=.*" + re.escape(INDEX_BASENAME), src, re.M):
        idents.add(m.group(1))
    return idents


def _alt(idents):
    return "(?:" + "|".join(re.escape(i) for i in sorted(idents, key=len, reverse=True)) + ")"


def writers():
    """{filename: [evidence lines]} for every src script that writes the index."""
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        src = open(f, encoding="utf-8", errors="ignore").read()
        idents = _index_idents(src)
        A = _alt(idents)
        ev = []
        for i, line in enumerate(src.split("\n"), 1):
            if re.search(r"\bopen\(\s*" + A + r"\s*,\s*['\"]w", line): ev.append((i, line.strip()))
            elif re.search(r"(?<!def )\bsave_index\s*\(", line):         ev.append((i, line.strip()))
            elif re.search(r"\bdump_atomic\s*\([^,]+,\s*" + A + r"\b", line): ev.append((i, line.strip()))
        if ev and os.path.basename(f) != "gate_person_index.py":
            out[os.path.basename(f)] = ev
    return out


def in_place_writes():
    """[(file, line_no, text)] for every in-place index write anywhere in src/."""
    bad = []
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        src = open(f, encoding="utf-8", errors="ignore").read()
        A = _alt(_index_idents(src))
        for i, line in enumerate(src.split("\n"), 1):
            if re.search(r"json\.dump\([^)]*open\(\s*" + A + r"\s*,\s*['\"]w", line) or \
               re.search(r"\bopen\(\s*" + A + r"\s*,\s*['\"]w['\"]\s*\)\s*\.write", line):
                bad.append((os.path.basename(f), i, line.strip()))
    return bad


def static_checks():
    fails = []
    if not os.path.exists(DECL):
        fails.append(f"P1  no declaration at {os.path.relpath(DECL, BASE)} -- nothing records "
                     f"which patch scripts a rebuild must re-run")
        decl = {"builder": None, "chain": [], "exempt": {}}
    else:
        decl = json.load(open(DECL))
    declared = {decl.get("builder")} | {c["script"] for c in decl.get("chain", [])} | set(decl.get("exempt", {}))
    W = writers()
    for f, ev in W.items():
        if f not in declared:
            fails.append(f"P1  {f} writes the index but is not declared in {os.path.basename(DECL)} "
                         f"(chain or exempt) -- a rebuild would silently discard its work. "
                         f"evidence: line {ev[0][0]}: {ev[0][1]}")
    for c in decl.get("chain", []):
        if not os.path.exists(os.path.join(HERE, c["script"])):
            fails.append(f"P1  declared chain step {c['script']} does not exist")
        elif c["script"] not in W:
            fails.append(f"P1  declared chain step {c['script']} does not write the index -- stale declaration")
    # DERIVED TABLES: the INVERSE property. These read the finished index and write a
    # different artifact, so P1's rule for `chain` is exactly wrong for them -- and
    # weakening that rule to fit them in would have cost the property it holds. Checked
    # rather than assumed: one that DID write the index would be a patcher wearing the
    # wrong label, and P3 would read its work as an unexplained gain.
    for c in (decl.get("derived_tables_after_the_chain", {}) or {}).get("steps", []):
        if not os.path.exists(os.path.join(HERE, c["script"])):
            fails.append(f"P1  declared derived table {c['script']} does not exist")
        elif c["script"] in W:
            fails.append(f"P1  declared derived table {c['script']} WRITES THE INDEX -- it is "
                         f"an index patcher and belongs in `chain`, where P3 can see it")
    for f, i, t in in_place_writes():
        fails.append(f"P2  {f}:{i} writes the index in place: {t}")
    # P4
    try:
        import gate_stint_subjects as GS
        res, sfails = GS.check(GS.load_loc2g())
        allowed = set(decl.get("known_unresolvable_stores", {})) | set(decl.get("held_stores", {}))
        for line in sfails:
            st = line.split(":")[0]
            if st not in allowed:
                fails.append(f"P4  {line} -- not declared in known_unresolvable_stores or held_stores; the rebuild would drop these men in silence")
    except FileNotFoundError as e:
        fails.append(f"P4  cannot run gate_stint_subjects: {e}")
    return fails, W


def selftest():
    """P4 shown failing for its own reason: a store with the league in s[1] refuses the
    rebuild BY NAME, and the builder's reader COUNTS it rather than dropping it."""
    import gate_stint_subjects as GS, build_person_index as B
    tmp = os.path.join(BASE, "build", "zz-selftest-p4.json")
    json.dump({"claims": [{"subject": ["stint", "NFL", "CHI", "1950"], "predicate": "x", "value": 1, "person": "P_000001"}]}, open(tmp, "w"))
    try:
        fails, _ = static_checks()
        a = any("P4" in f and "zz-selftest-p4" in f for f in fails)
        print(f"  {'OK  ' if a else 'BAD '} P4 refuses the rebuild by filename for a stint with the league in s[1]")
        P, rep = B.read_claims([tmp], GS.load_loc2g())
        b = any(r["store"] == "zz-selftest-p4" and r["stints"] == 1 for r in rep["skipped"])
        print(f"  {'OK  ' if b else 'BAD '} the builder COUNTS the skipped stint by store: {rep['skipped']}")
        json.dump({"claims": [{"subject": ["stint", "P_000001", "CHI", "1950"], "predicate": "x", "value": 1}]}, open(tmp, "w"))
        fails2, _ = static_checks(); P2, rep2 = B.read_claims([tmp], GS.load_loc2g())
        c = not any("zz-selftest-p4" in f for f in fails2) and not rep2["skipped"] and "P_000001" in P2
        print(f"  {'OK  ' if c else 'BAD '} the same stint with the person in s[1] passes and is indexed")
    finally:
        os.remove(tmp)
    ok = a and b and c
    print(f"selftest {'PASSED' if ok else 'FAILED'}"); return ok


# ---------------------------------------------------------------- P3 -----------
def population(idx):
    """What a rebuild must not lose. Per-person season keys plus counted fields.

    A season key is recorded under BOTH its current name and, when apply_club_keys
    has normalised it, the name the source printed (`_club_as_printed`). Club-key
    normalisation RENAMES keys -- 'COACHES|y1957|Los Angeles Rams' becomes the
    normalised code -- and the first protected rebuild read those 476 renames across
    50 people as losses. They are not: the season and its printed name survive."""
    empty = set()          # entries that record NOTHING: no name, no seasons, no claims, no counted field
    seasons, n = {}, {"entries": 0, "with_season": 0, "coaching_seasons": 0,
                      "officiating_seasons": 0, "club_as_printed": 0, "restored_cfl1945": 0,
                      "merged_into": 0, "guide_prose": 0}
    for pid, v in idx.items():
        if pid == "_clubs" or not isinstance(v, dict): continue
        n["entries"] += 1
        sd = v.get("seasons") or {}
        ks = set(sd.keys())
        for k, s in sd.items():
            if isinstance(s, dict) and s.get("_club_as_printed"):
                parts = k.split("|")
                if len(parts) == 3:
                    ks.add(f"{parts[0]}|{parts[1]}|{s['_club_as_printed']}")   # the pre-normalisation name
        # A rewrite that JOINED an existing season leaves no _club_as_printed on the target:
        # apply_club_keys keeps the printed name and the whole original record in the person's
        # own rewrite note instead. The key is renamed and folded, not lost, and the note is the
        # proof -- only keys the applier itself recorded are forgiven here.
        for r in (v.get("_club_key_normalisations") or []):
            if r.get("from") and r.get("to") in ks: ks.add(r["from"])
        if sd: n["with_season"] += 1
        seasons[pid] = ks
        if not (ks or v.get("name") or v.get("person") or v.get("coaching_seasons")
                or v.get("officiating_seasons") or v.get("person_season")): empty.add(pid)
        if v.get("coaching_seasons"): n["coaching_seasons"] += 1
        if v.get("officiating_seasons"): n["officiating_seasons"] += 1
        if v.get("merged_into"): n["merged_into"] += 1
        if any(k.startswith("guide.") for k in (v.get("person") or {})): n["guide_prose"] += 1
        for s in (v.get("seasons") or {}).values():
            if isinstance(s, dict):
                if "_club_as_printed" in s: n["club_as_printed"] += 1
                if "_restored_from" in s: n["restored_cfl1945"] += 1
    return {"counts": n, "seasons": seasons, "empty": empty}


def _one_time_transition():
    """An EXACT list of ids a declared, enabled, one-time transition may drop -- and only
    while the declaration says enabled. Empty otherwise, which is the normal state."""
    if not os.path.exists(DECL): return set()
    t = json.load(open(DECL)).get("p3_one_time_transition") or {}
    return set(t.get("ids") or ()) if t.get("_enabled") else set()


def compare(before, after):
    """Violations of P3. Empty list == the rebuild lost nothing."""
    v = []; dropped_empty = []
    for pid, ks in before["seasons"].items():
        aks = after["seasons"].get(pid)
        if aks is None:
            # AN ENTRY THAT RECORDED NOTHING IS NOT WORK. P3 protects what a person holds;
            # an entry with no name, no season, no claim and no counted field holds nothing,
            # and 1,598 of them existed only because the builder read a chain step's own
            # report back as a source (2026-09-07). Anything carrying ANY content still fails.
            forgiven = pid in before.get("empty", ()) or pid in _one_time_transition()
            (dropped_empty if forgiven else v).append(pid if forgiven else f"person {pid} vanished from the index")
        elif not ks <= aks:
            v.append(f"person {pid} lost season keys: {sorted(ks - aks)}")
    for k, b in before["counts"].items():
        a = after["counts"].get(k, 0)
        if k == "entries": b -= len(dropped_empty)
        if a < b:
            v.append(f"count {k} fell {b} -> {a}" + (f" (after allowing {len(dropped_empty)} empty entries dropped)" if k == "entries" and dropped_empty else ""))
    if dropped_empty:
        print(f"\nP3: {len(dropped_empty):,} EMPTY entries dropped -- no name, no season, no claim, no counted field. "
              f"Not a loss; listed so it is never silent. e.g. {sorted(dropped_empty)[:5]}")
    return v


if __name__ == "__main__":
    if "--selftest" in sys.argv: sys.exit(0 if selftest() else 1)
    fails, W = static_checks()
    print(f"index writers found in src/: {len(W)}")
    for f, ev in W.items():
        print(f"   {f:34} line {ev[0][0]}")
    if fails:
        print("\nGATE FAILED")
        for x in fails: print("  ", x)
        sys.exit(1)
    print("\nGATE PASSED (P1 every writer declared; P2 no in-place writes; P4 every unresolvable stint store declared)")
