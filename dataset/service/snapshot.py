"""What the read model was built from, and whether that has changed since.

An input is any file the build reads. Its fingerprint is (path, mtime_ns, size);
the snapshot id is a hash over all of them, so two builds from identical inputs
carry the same id and any change to any input is visible by comparison.
"""
import os, glob, hashlib, json
import paths


def inputs():
    files = sorted(glob.glob(os.path.join(paths.BUILD, "*.json")))
    files += [paths.IDENTITY, paths.PERSON_INDEX, paths.INDEX_REBUILD_DECL]
    files += sorted(glob.glob(os.path.join(paths.DECLARATIONS, "*.json")))
    files += sorted(glob.glob(os.path.join(paths.SERVICE_DECLARATIONS, "*.json")))
    out = []; seen = set()
    for f in files:
        if f in seen: continue
        seen.add(f)
        try:
            st = os.stat(f)
            out.append((os.path.relpath(f, paths.DATASET), st.st_mtime_ns, st.st_size))
        except FileNotFoundError:
            out.append((os.path.relpath(f, paths.DATASET), None, None))
    return out


def fingerprint(inp=None):
    inp = inp if inp is not None else inputs()
    h = hashlib.sha1()
    for row in inp: h.update(json.dumps(row).encode())
    return h.hexdigest()[:16]


def changed_since(recorded):
    """recorded: [(path, mtime_ns, size)] from the read model. -> list of {path, what}."""
    now = {p: (m, s) for p, m, s in inputs()}
    then = {p: (m, s) for p, m, s in recorded}
    out = []
    for p in sorted(set(now) | set(then)):
        if p not in then: out.append({"path": p, "what": "new"})
        elif p not in now: out.append({"path": p, "what": "gone"})
        elif now[p] != then[p]: out.append({"path": p, "what": "modified"})
    return out
