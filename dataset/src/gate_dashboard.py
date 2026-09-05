"""Gate: the dashboard must not render "never counted" as 0%.

An empty result and a failed one are the same bytes. A coverage dashboard that
draws an unmeasured field as 0% is that error at its worst, because the reader
sees a hole where there is only ignorance and goes looking for data that was
never absent.

So this gate builds a grid containing BOTH cases and proves they come out as
different cell types, and that the population row reconciles to the archive.

  python3 src/gate_dashboard.py     exit 1 = FAIL
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_dashboard as B

OUT = os.path.join(HERE, "..", "export", "coverage-dashboard.html")


def main():
    checks, fails = [], []

    # --- a grid holding a genuinely-zero field and a never-counted one --------
    per = {"P_1": {"first": 1926, "leagues": {"NFL"}, "person": {}, "seasons": {}, "name": "A"},
           "P_2": {"first": 1975, "leagues": {"WFL"}, "person": {}, "seasons": {}, "name": "B"}}
    sets = {"counted and empty": set(),          # measured, found nothing
            "never counted": B.UNMEASURED,       # not measured at all
            "counted and full": {"P_1", "P_2"}}
    g = B.grid(per, sets, "decade")
    row = {r["field"]: r for r in g["rows"]}

    z = row["counted and empty"]
    u = row["never counted"]
    f = row["counted and full"]

    if z["total_n"] == 0 and all(c["n"] == 0 for c in z["cells"]):
        checks.append("a field counted and found empty renders n=0 with its denominator")
    else:
        fails.append(f"[FAIL] the empty field did not render as 0: {z}")

    if u["total_n"] is None and all(c["n"] is None for c in u["cells"]):
        checks.append("a field never counted renders n=None -- a different TYPE, not a value")
    else:
        fails.append(f"[FAIL] the unmeasured field did not render as None: {u}")

    if z["cells"][0]["n"] is not u["cells"][0]["n"]:
        checks.append("zero and unmeasured are distinguishable in the data, not only in CSS")
    else:
        fails.append("[FAIL] zero and unmeasured collapse to the same value")

    if all(c["d"] > 0 for c in f["cells"]):
        checks.append("every cell carries its denominator alongside the numerator")
    else:
        fails.append("[FAIL] a cell lost its denominator")

    # --- the rendered page must draw them differently ------------------------
    if not os.path.exists(OUT):
        fails.append("[FAIL] no dashboard has been generated")
    else:
        page = open(OUT, encoding="utf-8").read()
        if 'class="un"' in page and "not measured" in page:
            checks.append("the page defines a distinct 'not measured' cell class")
        else:
            fails.append("[FAIL] the page has no distinct unmeasured cell")
        if "c.n===null" in page:
            checks.append("the renderer branches on null BEFORE computing a percentage")
        else:
            fails.append("[FAIL] the renderer does not special-case null")
        d = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',
                                 page, re.S).group(1))
        checks.append(f"figures live in the page as DATA, not baked into markup "
                      f"({len(d['decade']['rows'])} decade rows, {len(d['league']['rows'])} league rows)")
        popcheck = next((c for c in d["checks"] if "population row" in c["text"]), None)
        if popcheck and popcheck["ok"]:
            checks.append("population reconciles to the archive index: "
                          + re.sub("<[^>]+>|&mdash;", "", popcheck["text"]))
        else:
            fails.append("[FAIL] the population row does not reconcile to the archive")

    # --- the publish step must FAIL LOUDLY, never skip -----------------------
    import tempfile, json as J
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "coverage-dashboard.html")
        open(src, "w").write("<html>x</html>")

        missing = os.path.join(td, "no-such-folder")
        cfgm = os.path.join(td, "m.json")
        J.dump({"targets": [{"name": "gone", "dir": missing, "required": True}]}, open(cfgm, "w"))
        os.environ["PGM3_DASHBOARD_TARGETS"] = cfgm
        res, ok = B.publish(src)
        if not ok and res and not res[0][2] and "does not exist" in res[0][1]:
            checks.append("a missing or unsynced target FAILS and is reported, never skipped")
        else:
            fails.append(f"[FAIL] a missing target did not fail loudly: {res} ok={ok}")

        good = os.path.join(td, "dest"); os.makedirs(good)
        cfgg = os.path.join(td, "g.json")
        J.dump({"targets": [{"name": "ok", "dir": good, "required": True}]}, open(cfgg, "w"))
        os.environ["PGM3_DASHBOARD_TARGETS"] = cfgg
        res, ok = B.publish(src)
        if ok and "md5 verified" in res[0][1] and "new file" in res[0][1]:
            checks.append("a good target copies and VERIFIES the md5 after writing")
        else:
            fails.append(f"[FAIL] a good target did not verify: {res}")

        open(os.path.join(good, "coverage-dashboard.html"), "w").write("<html>DIFFERENT</html>")
        res, ok = B.publish(src)
        if ok and "OVERWROTE a DIFFERENT existing file" in res[0][1]:
            checks.append("overwriting a DIFFERENT existing file is announced, not silent")
        else:
            fails.append(f"[FAIL] a silent overwrite went unannounced: {res}")
        # --- a folder with NO LIVE SYNC CLIENT must fail like a missing one ---
        # This is the failure that actually happened: a leftover GoogleDrive
        # folder whose client was uninstalled. The bytes copied and the md5
        # verified while nothing synced. Bytes alone are not evidence of a sync.
        cfgd = os.path.join(td, "dead.json")
        J.dump({"targets": [{"name": "dead client", "dir": good,
                             "provider_process": "NoSuchSyncClient.app",
                             "provider_name": "Nothing", "required": True}]}, open(cfgd, "w"))
        os.environ["PGM3_DASHBOARD_TARGETS"] = cfgd
        res, ok = B.publish(src)
        if not ok and "NO SYNC CLIENT IS RUNNING" in res[0][1]:
            checks.append("a folder that exists but has NO LIVE SYNC CLIENT fails, "
                          "exactly like a missing folder")
        else:
            fails.append(f"[FAIL] a dead sync target was accepted: {res}")

        live, detail = B.provider_running("NoSuchSyncClient.app")
        if live is False:
            checks.append("provider_running() returns False for a client that is not running")
        else:
            fails.append(f"[FAIL] provider_running gave {live} for a missing client")
        live, _ = B.provider_running("launchd")
        if live is True:
            checks.append("provider_running() returns True for a process that IS running")
        else:
            fails.append("[FAIL] provider_running could not see a known-running process")
        os.environ.pop("PGM3_DASHBOARD_TARGETS", None)

    for c in checks: print("  " + c)
    for f_ in fails: print("  " + f_)
    if fails:
        print(f"\nGATE FAILED: {len(fails)} checks did not hold.")
        return 1
    print(f"\nGATE PASSED: {len(checks)} checks. Unmeasured is not zero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
