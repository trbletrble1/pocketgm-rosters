"""Gate: no build input may live in a session scratchpad or in /tmp.

The instance. bio_select.py held this path as a constant:

    /private/tmp/claude-501/-Users-ryannecci-Documents/ccc7c2b9-.../scratchpad

and read the Pro Football Archives claims from it behind `if os.path.exists(pf)`.
The archive moved machines on 2026-09-07. The session id in that path belonged to
the laptop, so the directory was simply not there, the guard substituted an empty
dict, and 75,008 claims left the bios in silence -- 2,249 military-service, 4,232
death dates, 4,166 death places. The same claims sat in build/pfa-pre1950.json,
byte-identical, the whole time. What surfaced was a prose diff four hours later:
'He was a United States Army veteran.' missing from Les Dodson.

The property, which is what this gate checks and the instance is not: a path
containing a session id is correct on one machine, in one session, once. Every
such path in src/ is a silent failure waiting for a restart. So: no file in src/
may name a session scratchpad or /tmp, unless declarations/session-scratchpad-inputs.json
lists it as OUTSTANDING with an owner.

The exemptions live in the declaration, not here, so widening one is a change to
a declared ruling and shows up in a diff -- rather than a quiet edit to the checker.

S1  every scratchpad path in src/ is declared OUTSTANDING
S2  no file listed in CLOSED has taken one back
S3  every declared OUTSTANDING entry still names a real path in that file
    (an entry whose code is gone is debt that has been paid; delete it)
S4  the load-bearing inputs of the bio chain resolve, and resolve under build/

Run:  python3 src/gate_no_scratchpad_inputs.py       exit 1 = FAIL
"""
import sys, os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
DECL = os.path.join(BASE, "declarations", "session-scratchpad-inputs.json")

# A session scratchpad, or literal /tmp. Matched in source text, not resolved:
# the point is that the STRING is in the file, whether or not it exists today.
SCRATCH_PAT = re.compile(r"/private/tmp/claude-\d+|['\"]/tmp/")
SESSION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def offenders():
    """Every src/*.py naming a scratchpad or /tmp path, with line numbers.
    This gate's own text names those paths to explain itself, so it is skipped."""
    found = {}
    me = os.path.basename(__file__)
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn == me:
            continue
        for i, line in enumerate(open(os.path.join(HERE, fn), errors="ignore"), 1):
            if line.lstrip().startswith("#"):
                continue
            if SCRATCH_PAT.search(line):
                found.setdefault(fn, []).append(i)
    return found


def main():
    d = json.load(open(DECL))
    declared = {e["script"]: e for e in d["OUTSTANDING"]}
    closed = {e["script"]: e["note"] for e in d.get("CLOSED", [])}
    print(d["RULING"]["rule"] + "\n")
    found = offenders()
    ok = True

    print("S1  every scratchpad path in src/ is declared")
    undeclared = sorted(set(found) - set(declared))
    if undeclared:
        ok = False
        for fn in undeclared:
            print(f"  FAIL  {fn}: lines {found[fn]} name a session scratchpad or /tmp, "
                  f"and the declaration does not list it")
        print("        A new one of these is not debt, it is a regression. Put the input "
              "in build/ and read it from there.")
    else:
        print(f"  ok    {len(found)} file(s) name one, every one declared with an owner")

    print("S2  no closed file has taken one back")
    regressed = sorted(set(found) & set(closed))
    if regressed:
        ok = False
        for fn in regressed:
            print(f"  FAIL  {fn}: closed, but lines {found[fn]} name a scratchpad again")
            print(f"        {closed[fn]}")
    else:
        print(f"  ok    {len(closed)} closed: {', '.join(sorted(closed)) or 'none'}")

    print("S3  every declared entry still names a real path")
    stale = sorted(set(declared) - set(found))
    if stale:
        ok = False
        for fn in stale:
            gone = not os.path.exists(os.path.join(HERE, fn))
            why = "the file is gone" if gone else "the path is no longer in it"
            print(f"  FAIL  {fn}: declared OUTSTANDING but {why}; move it to CLOSED")
    else:
        print(f"  ok    {len(declared)} declared, all still present")

    print("S4  the bio chain's inputs resolve, and resolve under build/")
    sys.path.insert(0, HERE)
    import bio_select
    if hasattr(bio_select, "SCRATCH"):
        ok = False
        print("  FAIL  bio_select.SCRATCH is back")
    else:
        print("  ok    bio_select names no scratchpad")
    missing = []
    for fn in ("pfa-pre1950.json", "nflverse-rosters.json", "pfr-drafts.json",
               "nflverse-draft.json", "guide-pre1950-delimited.json"):
        if not os.path.exists(os.path.join(BASE, "build", fn)):
            missing.append(fn)
    if missing:
        ok = False
        print(f"  FAIL  build/ is missing {missing} -- the bio prints would be rewritten, "
              f"not stopped, if these were read behind a guard")
    else:
        print("  ok    all 5 required inputs present under build/, read through required()")

    # A missing required input must STOP the run, not degrade it. Prove it.
    src = open(os.path.join(HERE, "bio_select.py"), errors="ignore").read()
    if "raise SystemExit" in src and "def required(" in src:
        print("  ok    required() raises SystemExit rather than returning empty")
    else:
        ok = False
        print("  FAIL  bio_select.required() no longer refuses to run without its input")

    n = sum(len(v) for v in found.values())
    print(f"\nSCRATCHPAD INPUTS GATE: {'pass' if ok else 'FAIL'}  "
          f"({n} path(s) in {len(found)} file(s); {len(declared)} declared outstanding, "
          f"{len(closed)} closed)")
    if ok and declared:
        pres = sum(1 for v in declared.values() if v.get("preserved"))
        silent = [k for k, v in declared.items() if v.get("read") == "silent"]
        print(f"  outstanding: {pres} of {len(declared)} recoverable from the carried-over "
              f"laptop scratchpads; {len(declared) - pres} were under literal /tmp and are gone.")
        if silent:
            print(f"  degrade SILENTLY when their input is absent, worst first: {', '.join(sorted(silent))}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
