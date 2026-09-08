"""(store, local id) -> global person, through build-reports/identity.json.

The rule is build_person_index.resolve_person's, restated: a P_ id is already
global; otherwise look the (store, local) pair up, and for a stats-<store> file
try the roster store it adopts ids from. tests/test_service.py asserts this
function and theirs agree on a sample, so the two cannot drift apart unnoticed.
"""
import json
import paths


class Identity:
    def __init__(self, path=paths.IDENTITY):
        self.raw = json.load(open(path))
        self.loc2g = {(s, p): g for g, v in self.raw.items() for s, p in v["local"]}

    def resolve(self, store, pid):
        if isinstance(pid, str) and pid.startswith("P_"): return pid
        g = self.loc2g.get((store, pid))
        if g is None and store.startswith("stats-"): g = self.loc2g.get((store[6:], pid))
        return g

    def __len__(self): return len(self.raw)
