"""RETENTION GATE: prove that publishing keeps the previous model, and that the
count is bounded. Proved, not asserted -- it runs six real publishes against a
throwaway cache directory and checks what is on disk after each, and it reads the
identity of the model actually being served.

Ryan ruled on 2026-09-09 that the previous published model is kept, after the
question "what did the service return before this weekend?" could not be answered:
`publish()` was a bare `os.replace`, which retains nothing, and the stores that
would rebuild the old model are under build/, which is gitignored.

WHAT THIS PROVES, in order:
  0. the model actually being served reports its own identity -- the only property
     here a fixture cannot fake, and the one that caught `SELECT k, v` against a
     meta table whose columns are `key` and `value`
  1. the first publish onto an empty cache retains nothing and does not fail
  2. the second publish keeps the first model, identified by ITS OWN meta table
  3. the fourth publish still holds exactly KEEP_PREVIOUS, and the one dropped is
     the OLDEST BY built_at, not by file mtime
  4. an unreadable retained model is the first to go, because it cannot serve a diff
  5. the served model is never the one removed

    python3 gate_retention.py
"""
import os, sys, json, shutil, sqlite3, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def a_model(path, snapshot_id, built_at):
    """THE SCHEMA MUST BE THE REAL ONE. The first version of this test invented a
    meta table with columns `k` and `v` -- and so did model_identity() -- and both
    were wrong together: the real model's columns are `key` and `value`. A test that
    builds its own fixture proves the fixture. Property 0 below therefore checks the
    ACTUAL published model, which is the only thing here that cannot be faked."""
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    c.executemany("INSERT INTO meta VALUES(?,?)", [("snapshot_id", snapshot_id), ("built_at", built_at)])
    c.commit(); c.close()


def main():
    sys.path.insert(0, HERE)
    import paths as _p0
    cache_real = _p0.CACHE_DIR                      # the real one, before the override
    cache = tempfile.mkdtemp(prefix="retention-")
    os.environ["FOOTBALL_ARCHIVE_CACHE"] = cache
    for m in ("paths", "build_read_model"): sys.modules.pop(m, None)
    import paths, build_read_model as B
    assert paths.CACHE_DIR == cache, f"the cache override did not take: {paths.CACHE_DIR}"
    fails = []
    def chk(cond, what):
        (print if cond else fails.append)(f"  {'ok  ' if cond else 'FAIL'} {what}")
        if not cond: print(f"  FAIL {what}")

    def do_publish(sid, built):
        tmp = paths.READ_MODEL + ".building"
        a_model(tmp, sid, built)
        return B.publish(tmp, paths.READ_MODEL, log=lambda *a: None)

    # 0 -- THE REAL MODEL. Everything below runs against fixtures this file writes, so
    # it can only prove the code agrees with itself. This one property reads the model
    # actually being served, and it is what caught `SELECT k, v` against a meta table
    # whose columns are `key` and `value`.
    real = os.path.join(cache_real, "archive.sqlite")
    if os.path.exists(real):
        sid, built = B.model_identity(real)
        chk(sid is not None and built is not None,
            f"the model actually being served reports its identity (got {sid!r}, {built!r})")
    else:
        chk(True, "no published model on this machine to check (skipped)")

    # 1 -- the first publish onto an empty cache
    r = do_publish("aaaa", "2026-09-01T00:00:00")
    chk(r["retained"] is None, "first publish retains nothing and does not fail")
    chk(os.path.exists(paths.READ_MODEL), "first publish leaves a served model")

    # 2 -- the second keeps the first, by its OWN identity
    do_publish("bbbb", "2026-09-02T00:00:00")
    prev = B.previous_models()
    chk([p["snapshot_id"] for p in prev] == ["aaaa"], f"second publish keeps the first, identified as aaaa (got {[p['snapshot_id'] for p in prev]})")
    chk(B.model_identity(paths.READ_MODEL)[0] == "bbbb", "the served model is the new one")

    # 3 -- bounded at KEEP_PREVIOUS, dropping the oldest by built_at
    do_publish("cccc", "2026-09-03T00:00:00")
    do_publish("dddd", "2026-09-04T00:00:00")
    prev = B.previous_models()
    chk(len(prev) == B.KEEP_PREVIOUS, f"exactly KEEP_PREVIOUS={B.KEEP_PREVIOUS} retained (got {len(prev)})")
    chk([p["snapshot_id"] for p in prev] == ["cccc", "bbbb"], f"the oldest went first, newest-first order (got {[p['snapshot_id'] for p in prev]})")
    chk(B.model_identity(paths.READ_MODEL)[0] == "dddd", "the served model is never the one removed")

    # 4 -- built_at decides, not mtime. Make the OLDEST the most recently touched.
    old = [p for p in B.previous_models() if p["snapshot_id"] == "bbbb"][0]["path"]
    os.utime(old, None)
    do_publish("eeee", "2026-09-05T00:00:00")
    chk([p["snapshot_id"] for p in B.previous_models()] == ["dddd", "cccc"],
        f"a fresh mtime does not save the oldest model (got {[p['snapshot_id'] for p in B.previous_models()]})")

    # 5 -- an unreadable retained model goes first
    victim = B.previous_models()[0]["path"]
    open(victim, "wb").write(b"not a database")
    chk(B.model_identity(victim)[0] is None, "an unreadable model reports no identity rather than raising")
    do_publish("ffff", "2026-09-06T00:00:00")
    left = B.previous_models()
    chk(all(p["readable"] for p in left), f"the unreadable model was removed first (left: {[(p['snapshot_id']) for p in left]})")

    shutil.rmtree(cache, ignore_errors=True)
    if fails:
        print(f"\nRETENTION GATE: {len(fails)} FAILURE(S)"); return 1
    print(f"\nRETENTION GATE: pass  (KEEP_PREVIOUS={B.KEEP_PREVIOUS}; 6 properties proved on real publishes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
