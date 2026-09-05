"""Expand an era-native position code into an English label. BUILD ONLY.

The label never replaces the code and is never a claim. See
export/position_labels.json for why this is not a source.

  python3 src/expand_position_labels.py [--check]
"""
import os, re, sys, json

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
M = json.load(open(os.path.join(BASE, "export", "position_labels.json")))
ATOMS, PRE, JOIN = M["atoms"], M["prefixes"], M["joiners"]


def one(tok):
    tok = tok.strip()
    if not tok: return None
    if tok in ATOMS: return ATOMS[tok]
    # longest atom suffix, with side/phase prefixes in front
    for i in range(1, len(tok)):
        head, tail = tok[:i], tok[i:]
        if tail in ATOMS and all(c in PRE for c in head):
            words = [PRE[c] for c in head]
            return " ".join(words + [ATOMS[tail]])
    return None


def label(code):
    """-> English, or None. None is an honest answer and must stay one."""
    parts = re.split(r"([-/,])", str(code))
    out, ok = [], False
    for p in parts:
        if p in JOIN: out.append(JOIN[p]); continue
        e = one(p)
        if e is None: return None
        out.append(e); ok = True
    return "".join(out) if ok else None


def main():
    fn = os.path.join(BASE, "declarations", "position_function.json")
    codes = json.load(open(fn))["codes"]
    hit = {c: label(c) for c in codes}
    named = {c: v for c, v in hit.items() if v}
    print(f"characterised codes: {len(codes)}   labelled: {len(named)} "
          f"({100*len(named)//len(codes)}%)")
    print("\nsample:")
    for c in list(codes)[:6]:
        print(f"   {c:<12} {hit[c] or '(no label - left as the code)'}")
    print("\nunlabelled:")
    for c, v in hit.items():
        if not v: print(f"   {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
