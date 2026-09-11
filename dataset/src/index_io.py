"""The one way to write build-reports/person-index.json.

WHY THIS FILE EXISTS. The index is a 347 MB gitignored file with no version history.
Six scripts used to write it with `json.dump(idx, open(path, "w"))`, which opens the
real file and streams into it: an interrupt mid-stream leaves it truncated, and
there is nothing to restore from. `dump_atomic` writes a sibling temp file, fsyncs
it, then `os.replace`s it over the target. A reader sees either the old complete
file or the new one, never a partial.

Every writer of the index goes through `save_index`. That is not only for safety --
it is what lets src/gate_person_index.py FIND the writers, so a patch script added
later is either declared in declarations/person-index-rebuild.json or fails the gate
by name. The failure this guards against happened on 2026-09-06: patch scripts
wrote the index directly, a rebuild silently discarded their work, and nobody knew.
"""
import os, json

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INDEX_PATH = os.path.join(BASE, "build-reports", "person-index.json")


def dump_atomic(obj, path, **kw):
    """json.dump to `path` such that the file is never observably partial."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    tmp = os.path.join(d, "." + os.path.basename(path) + ".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(obj, f, **kw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)           # atomic on the same filesystem
    except BaseException:
        try: os.remove(tmp)             # a failed write leaves nothing behind
        except OSError: pass
        raise
    try:                                # make the rename itself durable
        dfd = os.open(d, os.O_RDONLY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    except OSError:
        pass


def _fact(c):
    return (json.dumps(c.get("subject")), c.get("predicate"),
            json.dumps(c.get("value"), sort_keys=True), c.get("source_record"))


def write_store(out, path, reasons=None, **kw):
    """Write a claim store atomically AND SAY WHAT IT LOST against the store it replaces.

    Ryan's ruling, 2026-09-11: every ingest reports what it drops. Re-running the coach
    ingest lost 18 coaches (592 claims) and nothing said so; the defect lived two days and
    surfaced only because a store happened to be diffed by hand. So the writer -- the one
    place every store passes through -- loads the predecessor, compares FACT BY FACT
    (subject, predicate, value, source record; never totals), and records every loss in the
    store itself as `lost_since_predecessor`: one entry per source record, with the count and
    the reason the ingest gives. A loss the ingest gives no reason for is written with
    `reason: null`, printed, and fails src/gate_reingest_losses.py R1. A right loss recorded is
    the point, not an exception to it.

    `reasons(claim) -> (reason, extra_dict) or None` is the ingest's account of a lost claim.
    """
    lost = []
    if os.path.exists(path) and isinstance(out, dict) and "claims" in out:
        with open(path) as f:
            old = json.load(f)
        now = {}
        for c in out["claims"]:
            k = _fact(c); now[k] = now.get(k, 0) + 1
        by_rec = {}
        for c in old.get("claims", []):
            k = _fact(c)
            if now.get(k, 0) > 0:
                now[k] -= 1; continue
            r = reasons(c) if reasons else None
            reason, extra = (r if r else (None, {}))
            e = by_rec.setdefault(c.get("source_record"), {"source_record": c.get("source_record"), "claims": 0,
                                                         "reasons": {}, **(extra or {})})
            e["claims"] += 1
            e["reasons"][reason or "UNSTATED"] = e["reasons"].get(reason or "UNSTATED", 0) + 1
        for e in by_rec.values():
            stated = [r for r in e["reasons"] if r != "UNSTATED"]
            e["reason"] = None if "UNSTATED" in e["reasons"] else "; ".join(sorted(stated))
            lost.append(e)
        del old
    if isinstance(out, dict) and "claims" in out:
        out["lost_since_predecessor"] = sorted(lost, key=lambda e: str(e["source_record"]))
        n = sum(e["claims"] for e in lost)
        tally = {}
        for e in lost:
            for r, k in e["reasons"].items(): tally[r] = tally.get(r, 0) + k
        print(f"LOST SINCE THE PREDECESSOR: {n:,} claims on {len(lost):,} records -- by reason: {tally}")
    dump_atomic(out, path, **kw)
    return lost


def load_index():
    return json.load(open(INDEX_PATH))


def save_index(idx):
    dump_atomic(idx, INDEX_PATH)

