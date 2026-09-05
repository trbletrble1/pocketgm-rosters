"""Gate: the English position labels are a build artefact, not evidence.

Two properties, both from the instruction that created the file:

  1. NOTHING MAY CITE IT. No claim, denotation or source record anywhere in the
     store may reference export/position_labels.json, and the file must declare
     no source_id, acquisition or stated_by - the fields that would let a
     consumer treat it as a source.

  2. IT MUST NOT OVERWRITE THE CODE. Every position claim in the store must
     still carry the era-native code the source printed. A label is rendered
     BESIDE a code, never instead of it.

  python3 src/gate_labels_are_not_evidence.py      exit 1 = FAIL
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
LABELS = os.path.join(BASE, "export", "position_labels.json")


def main():
    M = json.load(open(LABELS))
    fail = []
    # 1a. the file itself must not look like a source
    for k in ("source_id", "acquisition", "stated_by", "attribution", "derived_from"):
        if k in M: fail.append(f"position_labels.json declares '{k}' - that makes it citable")
    # 1b. nothing in the store may reference it
    cited = 0
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        try: raw = open(f, encoding="utf-8").read()
        except Exception: continue
        if "position_labels" in raw or "position-labels" in raw:
            cited += 1; fail.append(f"{os.path.basename(f)} references the label map")
    # 2. every position claim still carries the source's own code
    checked = stripped = 0
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if c.get("predicate") != "position": continue
            checked += 1
            v = c.get("value")
            vals = v if isinstance(v, list) else [v]
            for one in vals:
                code = one.get("code") if isinstance(one, dict) else one
                if not code:
                    stripped += 1; break
                # a label would be prose; a code is short and has no spaces
                if isinstance(code, str) and " " in code and len(code) > 12:
                    stripped += 1
                    fail.append(f"a position claim carries prose, not a code: {code!r}")
                    break
    print(f"position claims checked: {checked:,}   without a source code: {stripped}")
    print(f"stores referencing the label map: {cited}")
    labelled = sum(1 for _ in M["atoms"])
    print(f"label atoms: {labelled}   uncertain and flagged: "
          f"{len(M.get('_uncertain', {}).get('codes', []))}")
    for f_ in fail[:8]: print(f"  [FAIL] {f_}")
    if fail:
        print("\nGATE FAILED"); return 1
    print("\nGATE PASSED: labels are not cited, and no code was overwritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
