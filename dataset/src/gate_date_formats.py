"""A declared date format must beat the alternative, on the archive's own evidence.

THE RULE IT GUARDS. Ryan, 2026-09-08: a source that writes dates in a consistent
order may declare that order, and the reading uses it for that source's values. A
source with no measurement behind it does NOT get a declared format -- it stays
unreadable and declared as printed, which is the honest state.

THE PROPERTY. For every declared numeric order, read that source's bare numeric dates
BOTH WAYS and compare each against the dates other sources hold for the same man and
family. The declared order must agree MORE OFTEN than the opposite one. A format that
agrees less is not a reading of that source, it is a corruption of it, and saying so
in a declaration does not make it true.

WHY IT IS NOT ENOUGH TO CHECK THE DECLARATION HAS EVIDENCE. A number in a JSON file
is a claim about a measurement, not the measurement. This re-derives it from the
claims every time it runs.

EMPTY DENOMINATORS ARE REFUSED. A declared source whose dates can be compared against
nothing has not been shown to be right; it fails rather than passing over nothing.

  python3 src/gate_date_formats.py [--selftest]
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import dates as model_dates

DECL = os.path.join(paths.SERVICE_DECLARATIONS, "date-formats-by-source.json")
SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
DATE_FAMILIES = ("birth_date", "death_date")


def evidence(conn, formats):
    """-> {source: {order: agreements}} plus the compared count, from the claims."""
    held = collections.defaultdict(set)          # (person, family) -> {(y,m,d)}
    numeric = collections.defaultdict(list)      # source -> [(person, family, a,b,y)]
    q = ("select source_id, person, family, value_text from claim "
         "where family in (%s) and person is not null and value_text is not null"
         % ",".join("?" * len(DATE_FAMILIES)))
    for sid, person, fam, val in conn.execute(q, DATE_FAMILIES):
        m = SLASH.match(str(val).strip())
        if m and sid in formats:
            numeric[sid].append((person, fam, int(m.group(1)), int(m.group(2)),
                                 int(m.group(3))))
            continue
        r = model_dates.read(val)               # NO source: the plain reading
        if r and r["precision"] == "day":
            held[(person, fam)].add((r["year"], r["month"], r["day"]))
    out = {}
    for sid, rows in numeric.items():
        score = {"MDY": 0, "DMY": 0}
        compared = 0
        for person, fam, a, b, y in rows:
            other = held.get((person, fam))
            if not other:
                continue
            compared += 1
            if (y, a, b) in other: score["MDY"] += 1
            if (y, b, a) in other: score["DMY"] += 1
        out[sid] = {"score": score, "compared": compared, "rows": len(rows)}
    return out


def run(formats=None, conn=None, quiet=False):
    fails = []
    if formats is None:
        d = json.load(open(DECL))["sources"]
        formats = {k: v["numeric_order"] for k, v in d.items() if v.get("numeric_order")}
    if conn is None:
        conn = sqlite3.connect(paths.READ_MODEL)
    if not formats:
        if not quiet: print("   no source declares a date format")
        return [], {}
    ev = evidence(conn, formats)
    for sid, order in sorted(formats.items()):
        e = ev.get(sid)
        if not e or not e["compared"]:
            fails.append(f"{sid}: declares {order} and NOT ONE of its numeric dates can "
                         "be compared against another source. An untested format is a "
                         "guess with a declaration around it")
            continue
        mine = e["score"][order]
        other = e["score"]["DMY" if order == "MDY" else "MDY"]
        if not quiet:
            print(f"   {sid}: declared {order} agrees {mine:,}   "
                  f"the other order agrees {other:,}   of {e['compared']:,} compared")
        if mine <= other:
            fails.append(f"{sid}: declares {order}, which agrees {mine:,} times against "
                         f"{other:,} for the opposite order. A format that agrees less "
                         "is not a reading of the source")
    return fails, ev


def selftest():
    """IT MUST BE SEEN TO FAIL. The only way to make it fail on real data is to declare
    the WRONG order, so that is what the self-test declares."""
    ok = True
    conn = sqlite3.connect(paths.READ_MODEL)
    cases = [
        ({"crippen-aafc-register": "DMY"}, True,
         "the WRONG order for a source the archive can check"),
        ({"crippen-aafc-register": "MDY"}, False, "the measured order"),
        ({"a-source-with-no-claims": "MDY"}, True,
         "a format nothing can be compared against"),
    ]
    for f, want, why in cases:
        fl, _ = run(formats=f, conn=conn, quiet=True)
        got = bool(fl)
        print(f"  {'PASS' if got == want else 'FAIL'}  "
              f"{'refuses' if got else 'accepts':8s} {why}")
        if got: print(f"        -> {fl[0][:120]}")
        ok &= got == want
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv: raise SystemExit(0 if selftest() else 1)
    print("SELF-TEST first -- the gate must be seen to fail:")
    if not selftest(): raise SystemExit("self-test failed; the gate's verdict means nothing")
    print()
    fails, _ = run()
    print()
    if fails:
        print("DATE FORMAT GATE: FAIL")
        for f in fails: print("   -", f)
        raise SystemExit(1)
    print("DATE FORMAT GATE: pass")
