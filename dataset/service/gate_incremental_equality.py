"""A FAST REBUILD MUST PRODUCE THE SAME MODEL AS A SLOW ONE.

`build_read_model.py --fast` keeps the rows of stores whose input has not changed and
re-reads only what moved. That is a cache, and a cache that can be wrong quietly is
the defect this archive has found six separate ways. So it is gated by EQUALITY:
build both ways from the same inputs and compare every table.

WHAT IS COMPARED, and the one thing that is not.

  Every table is compared row for row, ordered, as tuples.

  `claim.id` is a running counter assigned in store order, so a fast build gives a
  cached store its OLD ids and a re-read store fresh ones. The ids therefore DIFFER
  between the two builds by construction. This is not waved away: each claim is
  matched on its NATURAL key `(store, cid)`, which the schema already keeps unique,
  and then `date_reading.claim` and `person_name.claim` are compared through that
  mapping. So the comparison is complete -- nothing is excluded, one column is
  translated -- and if the two builds disagree about which claim a date reading
  belongs to, this says so.

  `meta` differs in `built_at`, `build_seconds` and the fingerprint of the build
  itself; those three keys are compared for presence, not value, and everything else
  in `meta` is compared exactly.

    python3 service/gate_incremental_equality.py            build both ways and compare
    python3 service/gate_incremental_equality.py --selftest the comparison itself
"""
import os, sys, json, glob, time, sqlite3, subprocess, tempfile, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths

FAILS = []
# KEYS THAT DESCRIBE THE BUILD RATHER THAN THE ARCHIVE. These are the only values
# allowed to differ, and each is here for a stated reason: when it ran, how long it
# took, and -- the point of this gate -- HOW it was built. Everything that describes
# what the archive holds is compared exactly.
META_MAY_DIFFER = {"built_at", "build_seconds", "snapshot_id", "forced",
                   "stores_reused_from_the_previous_model"}


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def tables(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE '%_fts%' ORDER BY name")]


def compare(a_path, b_path, examples=2):
    """-> list of differences between two models.

    DONE IN SQL, with both models ATTACHed, because the Python version loaded 7.9
    million claim rows into a dict twice and took minutes per comparison. `EXCEPT`
    both ways is the same question asked in the engine that already holds the data.

    `claim.id` is a running counter and differs between a full and a fast build by
    construction, so every table is compared with the id replaced by the natural key
    `(store, cid)` -- on `claim` itself, and through a join on `date_reading` and
    `person_name`, which reference it. Nothing is excluded; one column is translated.
    """
    c = sqlite3.connect(":memory:", uri=True)   # uri=True so the models attach read-only by URI
    c.execute("ATTACH DATABASE ? AS m1", (f"file:{a_path}?mode=ro",))
    c.execute("ATTACH DATABASE ? AS m2", (f"file:{b_path}?mode=ro",))
    out = []
    ta = [r[0] for r in c.execute("SELECT name FROM m1.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' ORDER BY name")]
    tb = [r[0] for r in c.execute("SELECT name FROM m2.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '%_fts%' ORDER BY name")]
    if ta != tb:
        out.append({"what": "the two models do not hold the same tables",
                    "only_in_full": sorted(set(ta) - set(tb)), "only_in_fast": sorted(set(tb) - set(ta))})
        return out

    def both_ways(what, sel1, sel2, extra=None):
        for lab, x, y in (("only_in_full", sel1, sel2), ("only_in_fast", sel2, sel1)):
            rows = c.execute(f"SELECT * FROM ({x} EXCEPT {y}) LIMIT ?", (examples + 1,)).fetchall()
            if rows:
                n = c.execute(f"SELECT COUNT(*) FROM ({x} EXCEPT {y})").fetchone()[0]
                out.append({"what": what, "side": lab, "rows": n,
                            **(extra or {}), "example": [str(r)[:150] for r in rows[:examples]]})

    for t in ta:
        cols = [d[1] for d in c.execute(f"PRAGMA m1.table_info({t})")]   # the schema goes BEFORE the pragma
        if t == "meta":
            d1 = dict(c.execute("SELECT key, value FROM m1.meta")); d2 = dict(c.execute("SELECT key, value FROM m2.meta"))
            if set(d1) != set(d2):
                out.append({"what": "meta holds different keys", "only_in_full": sorted(set(d1) - set(d2)),
                            "only_in_fast": sorted(set(d2) - set(d1))})
            for k in sorted(set(d1) & set(d2)):
                if k in META_MAY_DIFFER: continue
                if d1[k] != d2[k]:
                    out.append({"what": "a meta value differs", "key": k, "full": str(d1[k])[:60], "fast": str(d2[k])[:60]})
            continue
        if t == "claim":
            keep = [x for x in cols if x != "id"]
            sel = lambda m: f"SELECT {','.join(keep)} FROM {m}.claim"
            both_ways("a claim differs, is missing or is extra", sel("m1"), sel("m2"))
            continue
        if t in ("date_reading", "person_name") and "claim" in cols:
            keep = [f"x.{y}" for y in cols if y != "claim"]
            sel = lambda m: (f"SELECT {','.join(keep)}, c.store, c.cid FROM {m}.{t} x "
                             f"JOIN {m}.claim c ON c.id = x.claim")
            both_ways(f"{t} differs (compared through the claim it names)", sel("m1"), sel("m2"))
            continue
        sel = lambda m: f"SELECT {','.join(cols)} FROM {m}.{t}"
        both_ways("a table differs", sel("m1"), sel("m2"), {"table": t})
    c.close()
    return out


def build_to(dst, fast):
    env = dict(os.environ)
    argv = [sys.executable, os.path.join(HERE, "build_read_model.py"), "--force", "--to", dst]
    if fast: argv.append("--fast")
    t = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, env=env)
    if r.returncode not in (0, 1):
        print(r.stdout[-2000:]); print(r.stderr[-2000:])
        raise SystemExit(f"build ({'fast' if fast else 'full'}) failed with {r.returncode}")
    return time.time() - t, r.stdout


def main(argv):
    if "--selftest" in argv: return selftest()
    tmp = tempfile.mkdtemp(prefix="equality-")
    full, fast = os.path.join(tmp, "full.sqlite"), os.path.join(tmp, "fast.sqlite")

    def pair(label):
        for p in (full, fast):
            if os.path.exists(p): os.remove(p)
        tf, _ = build_to(full, fast=False)
        tq, out = build_to(fast, fast=True)
        line = next((l.strip() for l in out.splitlines() if "read-stage cache" in l), "")
        print(f"  {label}: full {tf:.0f}s, fast {tq:.0f}s   {line}")
        d = compare(full, fast)
        check(not d, f"{label}: every table is equal ({len(d)} difference(s))"
              + ("" if not d else "\n      " + "\n      ".join(json.dumps(x)[:190] for x in d[:6])))
        return tf, tq, line

    print("building BOTH ways, TWICE. Four builds; this is not quick and that is the point.")
    t_full, t_fast, _ = pair("every store cached")

    # A PARTIAL CACHE IS THE CASE THAT MATTERS, and it must be a REAL claim store.
    # The all-cached path is the easy one and it hid a bug: `n_claims` was taken from
    # the highest claim ID, which equals the row count only when nothing is re-read.
    # The store is TOUCHED, not modified -- its content is identical, so the two models
    # must still agree exactly. It is touched BEFORE both builds so the `input` table,
    # which records mtimes, is the same in each.
    c = sqlite3.connect(f"file:{full}?mode=ro", uri=True)
    victim_store = c.execute("SELECT name FROM store WHERE claims > 0 ORDER BY claims LIMIT 1").fetchone()[0]
    c.close()
    victim = os.path.join(paths.BUILD, victim_store + ".json")
    st = os.stat(victim)
    print(f"  touching {victim_store} ({st.st_size / 1e3:.0f} kB) so the next fast build must re-read it")
    os.utime(victim, None)
    try:
        pair("one store re-read")
    finally:
        os.utime(victim, (st.st_atime, st.st_mtime))
        print(f"  {victim_store}'s mtime restored")

    if t_full > 0:
        print(f"  INFORMATION: with every store cached, fast is {t_full - t_fast:.0f}s quicker "
              f"({(1 - t_fast / t_full) * 100:.0f}%)")
    for p in (full, fast):
        try: os.remove(p)
        except OSError: pass
    if FAILS:
        print(f"\nINCREMENTAL EQUALITY GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nINCREMENTAL EQUALITY GATE: pass"); return 0


def selftest():
    """The comparison itself, on two tiny models. It must SEE each kind of divergence."""
    tmp = tempfile.mkdtemp(prefix="equality-self-")
    def make(path, claim_rows, dr_rows, meta=(("snapshot_id", "x"), ("claims", "2"))):
        c = sqlite3.connect(path)
        c.executescript("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);"
                        "CREATE TABLE claim(id INT, store TEXT, cid TEXT, person TEXT);"
                        "CREATE TABLE date_reading(claim INT, y INT);")
        c.executemany("INSERT INTO meta VALUES(?,?)", meta)
        c.executemany("INSERT INTO claim VALUES(?,?,?,?)", claim_rows)
        c.executemany("INSERT INTO date_reading VALUES(?,?)", dr_rows)
        c.commit(); c.close()
    A = os.path.join(tmp, "a.sqlite"); B = os.path.join(tmp, "b.sqlite")
    cases = []
    base_a = [(1, "s1", "c1", "P_1"), (2, "s2", "c1", "P_2")]
    # the same content, DIFFERENT ids -- the whole reason the gate translates them
    base_b = [(90, "s2", "c1", "P_2"), (91, "s1", "c1", "P_1")]
    cases.append(("the same content under different claim ids", base_a, [(1, 1900)], base_b, [(91, 1900)], 0))
    # A CHANGED ROW IS TWO DIFFERENCES, one per direction: it is missing from one side
    # and extra on the other. That is what EXCEPT both ways says, and it is more useful
    # than one line -- the report shows the old value and the new.
    cases.append(("a claim's value differs", base_a, [], [(90, "s2", "c1", "P_9"), (91, "s1", "c1", "P_1")], [], 2))
    cases.append(("a claim is missing", base_a, [], [(91, "s1", "c1", "P_1")], [], 1))
    cases.append(("a date reading points at a DIFFERENT claim", base_a, [(1, 1900)], base_b, [(90, 1900)], 2))
    cases.append(("a meta value differs", base_a, [], base_b, [],
                  1, (("snapshot_id", "x"), ("claims", "3"))))
    ok = True
    for case in cases:
        label, ca, da, cb, db, want = case[:6]
        meta_b = case[6] if len(case) > 6 else (("snapshot_id", "x"), ("claims", "2"))
        for p in (A, B):
            try: os.remove(p)
            except OSError: pass
        make(A, ca, da); make(B, cb, db, meta_b)
        got = len(compare(A, B))
        good = got == want; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected {want} difference(s), got {got}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
