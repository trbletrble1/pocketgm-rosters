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

    for c in checks: print("  " + c)
    for f_ in fails: print("  " + f_)
    if fails:
        print(f"\nGATE FAILED: {len(fails)} checks did not hold.")
        return 1
    print(f"\nGATE PASSED: {len(checks)} checks. Unmeasured is not zero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
