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


def load_index():
    return json.load(open(INDEX_PATH))


def save_index(idx):
    dump_atomic(idx, INDEX_PATH)

