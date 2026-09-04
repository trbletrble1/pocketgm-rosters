"""Gate: every declaration key must be READ by something.

Three times now a declaration has failed to be load-bearing, each in a new shape:

  1. a value computed and never referenced      (JERSEY_USABLE, GP_LEAGUE_RATE)
  2. a value written to the right file, WRONG BLOCK   (declarations.cfl.expected_fill)
  3. a fact recorded as prose that nothing enforces   (league_codes: AFL3)

The first two were caught by reading the code. Neither would have been caught by
a check, because there was no check. This is that check.

The property: for every declaration file, every key that is not explicitly marked
documentation must appear as a string literal somewhere in src/. A key nothing
reads is a note, and a note that looks like a declaration is worse than a note,
because the next person assumes the ingest honours it.

Convention: a key whose name starts with "_" is documentation BY DESIGN - prose
addressed to a reader, never to the code. Everything else must be read, or be
listed in DOCUMENTATION_ONLY below with a reason.

Run:  python3 src/gate_declarations_are_read.py       exit 1 = FAIL
"""
import sys, os, json, glob, re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")

# Keys that are genuinely addressed to a human reader and to no code path.
# Each needs a reason. This list staying short is the point; if it grows, the
# declarations have drifted back into being notes.
# NOT a list in this file. Each declaration names its own documentation-only
# keys under `_documentation_only`, so widening the exemption is a change to the
# declaration and shows up in a diff - rather than a quiet edit to the checker.


def significant_keys(obj, prefix="", depth=0, maxdepth=2):
    """Top-level and second-level keys. Deeper nesting is usually data
    (league-season keys, predicate names), not structure a reader must honour."""
    if not isinstance(obj, dict) or depth > maxdepth:
        return
    for k, v in obj.items():
        if k.startswith("_"):
            continue
        yield prefix + k, k
        if depth < 1:
            yield from significant_keys(v, prefix + k + ".", depth + 1, maxdepth)


def main():
    src = ""
    for f in glob.glob(os.path.join(HERE, "*.py")):
        if os.path.basename(f) == os.path.basename(__file__):
            continue
        src += open(f, encoding="utf-8").read()

    unread, checked = [], 0
    for path in sorted(glob.glob(os.path.join(BASE, "declarations", "*.json"))):
        d = json.load(open(path))
        fname = os.path.basename(path)
        doc_only = set(d.get("_documentation_only", {}))
        for full, leaf in significant_keys(d):
            checked += 1
            # an exemption covers the key AND its subtree: marking `coverage`
            # documentation means its children are documentation too
            if leaf in doc_only or full in doc_only or full.split(".")[0] in doc_only:
                continue
            # a map keyed by DATA (league-seasons, predicate names) is not
            # structure a reader must honour; the parent being read is enough
            if re.fullmatch(r"[A-Z0-9]+-\d{4}", leaf):
                continue
            # READ TEST, and its limit: a string-literal grep over src/. Code
            # that ITERATES a declaration block never names its children, so a
            # child counts as reached when its parent is read. This is a proxy.
            # It cannot see a key that is read and then ignored - only one that
            # nothing so much as names. That is the failure it exists to catch.
            if re.search(r"[\"']" + re.escape(leaf) + r"[\"']", src):
                continue
            parent = full.rsplit(".", 1)[0] if "." in full else None
            if parent and re.search(r"[\"']" + re.escape(parent) + r"[\"']", src):
                continue
            unread.append((fname, full))

    print(f"declaration keys checked: {checked}")
    print(f"keys NOTHING in src/ reads: {len(unread)}")
    for f, k in unread:
        print(f"  [FAIL] {f:<26} {k}")
    json.dump([{"file": f, "key": k} for f, k in unread],
              open(os.path.join(BASE, "build-reports",
                                "gate-declarations-are-read.json"), "w"), indent=1)
    if unread:
        print(f"\nGATE FAILED: {len(unread)} declaration keys are notes wearing a "
              f"declaration's authority.\nEither wire them in, or mark them "
              f"documentation with a reason.")
        return 1
    print("\nGATE PASSED: every declaration key is read by something.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
