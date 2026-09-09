"""Gate: a script must not write unless it is asked to.

29 of the 66 scripts in src/ that can write do so by DEFAULT, and 14 of those take no
flags at all -- there is no way to ask them what they would do first. That property cost
two incidents in one afternoon on 2026-09-09:

  * `ingest_officials.py` was run with `--write`, which it does not accept and silently
    ignored. It wrote anyway and the store fell from 10,316 claims to 734.
  * `promote_coaches.py` was run three times in the belief that it was a dry run, because
    every other script reached for that day took `--write`. Each run wrote, and one
    re-minted 1,799 person ids, orphaning 1,596 index entries.

Neither was a bug in the script. Both were the same property: the safe action was the one
you had to know to ask for.

THE RULE. Every `__main__` that can write must take an explicit opt-in -- a `--write`
flag, or an argparse action that requires one. `--dry` is NOT an opt-in: it makes writing
the default and puts the burden on the caller to remember.

  python3 src/gate_writes_are_opt_in.py            exit 1 = FAIL
  python3 src/gate_writes_are_opt_in.py --list     just the work list
"""
import os, re, sys, ast, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE

OPT_IN = re.compile(r'["\']--write["\']\s+in\s+(?:sys\.)?argv')
OPT_OUT = re.compile(r'["\']--dry["\']\s+not\s+in\s+(?:sys\.)?argv')
WRITE_DEFAULT = re.compile(r"def\s+main\s*\([^)]*\bwrite\s*=\s*True")
WRITE_PARAM = re.compile(r"def\s+main\s*\([^)]*\bwrite\s*=")
BARE_CALL = re.compile(r"^\s*(?:\w+\s*(?:,\s*\w+\s*)*=\s*)?main\(\s*\)", re.M)


def classify(path):
    """-> (verdict, why) or (None, None) if the file cannot write from __main__."""
    s = open(path, encoding="utf-8", errors="replace").read()
    if "__main__" not in s or not WRITE_PARAM.search(s):
        return None, None
    tail = s[s.index("if __name__"):]
    if OPT_IN.search(s):
        return "ok", "writes only when --write is given"
    if OPT_OUT.search(s):
        return "writes-unless-dry", ("writes by default; --dry is the escape. The safe "
                                     "action is the one the caller must remember to ask for")
    if WRITE_DEFAULT.search(s) and BARE_CALL.search(tail):
        has_argv = "sys.argv" in s
        return "writes-bare", ("main(write=True) called as main()"
                               + ("" if has_argv else "; the file reads no argv at all, so "
                                  "there is NO flag that would stop it"))
    if WRITE_DEFAULT.search(s):
        return "writes-default", "main(write=True); no opt-in found at the call site"
    return None, None


def main():
    rows = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".py") or f.startswith("gate_writes_are_opt_in"):
            continue
        v, why = classify(os.path.join(SRC, f))
        if v: rows.append((f, v, why))
    g = collections.defaultdict(list)
    for f, v, why in rows: g[v].append((f, why))
    ok = len(g.get("ok", []))
    bad = [r for r in rows if r[1] != "ok"]
    print(f"scripts in src/ whose __main__ can write: {len(rows)}")
    print(f"  opt-in (--write)                     : {ok}")
    print(f"  WRITE BY DEFAULT                     : {len(bad)}")
    for v in ("writes-bare", "writes-unless-dry", "writes-default"):
        if not g.get(v): continue
        print(f"\n  {v}  ({len(g[v])})")
        for f, why in g[v]:
            print(f"      {f:38s} {why}")
    if "--list" in sys.argv:
        print("\nwork list:")
        for f, v, _ in bad: print(f"  {f}")
        return 0
    print("\nPASS" if not bad else f"\nFAIL: {len(bad)} scripts write unless told not to")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
