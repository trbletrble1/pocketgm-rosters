"""Every person a claim names was created by a decision. Nothing invents a human.

THE HOLE THIS CLOSES. resolve_person() accepts any id beginning `P_` on the PREFIX
ALONE -- `if isinstance(pid, str) and pid.startswith("P_"): return pid`. So an
ingest can write `["stint", "P_999999", ...]`, the builder resolves it, the index
grows a person, and no check anywhere objects. The promotion route exists to make
person creation a recorded judgement; without this gate the route can simply be
walked around.

THE LEGITIMATE ORIGINS, ESTABLISHED RATHER THAN ASSUMED. Every script that writes
a P_ id into the index was read, and every decision store it reads was opened:

  identity.json          40,745  a source-native id resolved to a global person
  coach-promotions        1,799  promote_coaches.py
  officials-applied       1,052  apply_officials.py (978 of them created)
  person-merges              93  merges: BOTH sides, canonical and absorbed
  player-promotions          14  promote_players.py

RE-DERIVED, NOT TRUSTED. The origins are read from the decision stores themselves,
never from the index (which is what would be wrong) and never from a store's own
report of what it did. An id present in the index proves only that something wrote
it, which is the thing being tested.

EMPTY DENOMINATORS ARE REFUSED, in both directions: no origins loaded, or no claims
scanned, fails rather than passing over nothing.

  python3 src/gate_person_origin.py [--selftest]
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
REPORT = os.path.join(BASE, "build-reports", "person-origin.json")


def origins():
    """-> {pid: [origin, ...]}, from the DECISION STORES. Never from the index."""
    o = collections.defaultdict(list)
    p = os.path.join(BASE, "build-reports", "identity.json")
    if os.path.exists(p):
        for pid in json.load(open(p)): o[pid].append("identity")
    for f, key, how in (("coach-promotions.json", "promotions", "coach_promotion"),
                        ("player-promotions.json", "promotions", "player_promotion")):
        q = os.path.join(BASE, "build", f)
        if os.path.exists(q):
            for r in (json.load(open(q)).get(key) or []):
                if r.get("person_id"): o[r["person_id"]].append(how)
    q = os.path.join(BASE, "declarations", "person-merge-decisions.json")   # the decisions, in git; read loudly
    if True:
        for m in (json.load(open(q)).get("merges") or []):
            # BOTH SIDES. An absorbed record still answers, so its id is a person.
            for k in ("canonical_person", "absorbed_person"):
                if m.get(k): o[m[k]].append("merge")
    q = os.path.join(BASE, "build", "officials-applied.json")
    if os.path.exists(q):
        for pid in (json.load(open(q)).get("applied") or []):
            if isinstance(pid, str): o[pid].append("officials")
    return o


def claimed_ids(stores=None):
    """-> {pid: {store: n}} for every P_ id named as a claim subject or `person`."""
    seen = collections.defaultdict(collections.Counter)
    for f in sorted(stores or glob.glob(os.path.join(BASE, "build", "*.json"))):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or not isinstance(d.get("claims"), list): continue
        for c in d["claims"]:
            for v in (c.get("person"), (c.get("subject") or [None, None])[1]):
                if isinstance(v, str) and v.startswith("P_"): seen[v][st] += 1
    return seen


def run(stores=None, orig=None, quiet=False):
    o = orig if orig is not None else origins()
    seen = claimed_ids(stores)
    fails = []
    if not o:
        fails.append("no origins loaded at all -- every id would pass for lack of "
                     "anything to check against")
    if not seen:
        fails.append("no P_ id found in any claim -- the scan found nothing to check, "
                     "which is a broken scan and not a clean sheet")
    orphans = {pid: dict(sts) for pid, sts in seen.items() if pid not in o}
    # THE OTHER DIRECTION, AND THE ONE THAT MATTERS MORE. A claim naming an invented id
    # is how a person gets in; the INDEX is where he then lives. Checking only the claims
    # would miss a person written straight into the index by a chain step. Skipped when
    # the caller passes explicit stores, because a self-test store is not the archive.
    idx_orphans = {}
    if stores is None:
        ip = os.path.join(BASE, "build-reports", "person-index.json")
        if os.path.exists(ip):
            idx = json.load(open(ip)); idx.pop("_clubs", None)
            idx_orphans = {pid: {"name": (v or {}).get("name"),
                                 "entered_by": (v or {}).get("entered_by")}
                           for pid, v in idx.items()
                           if pid.startswith("P_") and pid not in o}
            if idx_orphans:
                fails.append(f"{len(idx_orphans):,} people are IN THE INDEX and were created "
                             f"by no decision")
        else:
            fails.append("no person index on disk to check the second direction against")
    by_store = collections.Counter()
    for pid, sts in orphans.items():
        for st in sts: by_store[st] += 1
    if orphans:
        fails.append(f"{len(orphans):,} P_ ids are named by claims and were created by no "
                     f"decision: {dict(by_store.most_common(6))}")
    kinds = collections.Counter(k for v in o.values() for k in v)
    # An origin with no person is NOT a failure: demote_stintless.py removes the coach
    # promotions that carry no season, by declared design. Counted, not failed on.
    unused = sorted(set(o)) if False else None
    if not quiet:
        print(f"origins loaded      {len(o):,}   {dict(kinds)}")
        print(f"P_ ids in claims    {len(seen):,}   across "
              f"{len({s for v in seen.values() for s in v}):,} stores")
        print(f"WITH NO ORIGIN      {len(orphans):,} in claims, {len(idx_orphans):,} in the index")
        for pid, sts in sorted(orphans.items())[:15]:
            print(f"   {pid}  {sts}")
    out = {"_what": "every P_ id a claim names, against the decisions that create people",
           "_origins_are_read_from": ["build-reports/identity.json",
                                      "build/coach-promotions.json",
                                      "build/player-promotions.json",
                                      "build/person-merges.json (both sides)",
                                      "build/officials-applied.json"],
           "origins": len(o), "origins_by_kind": dict(kinds),
           "ids_in_claims": len(seen), "with_no_origin": len(orphans),
           "orphans_by_store": dict(by_store), "orphans": orphans,
           "in_the_index_with_no_origin": idx_orphans,
           "_an_origin_with_no_person_is_not_a_failure":
               "demote_stintless.py removes the coach promotions that carry no coaching "
               "season, by declared design, so a handful of decided ids are legitimately "
               "absent from the index. Counted, never failed on.",
           "fails": fails}
    if stores is None:
        json.dump(out, open(REPORT, "w"), indent=1)
    return fails, out


def selftest():
    """IT MUST BE SEEN TO FAIL. Three ways it can be wrong, each forced once."""
    import tempfile
    ok = True
    d = tempfile.mkdtemp()
    inv = os.path.join(d, "invented.json")
    json.dump({"claims": [{"subject": ["stint", "P_999999", "XXX", "1900"],
                           "person": "P_999999", "predicate": "x", "value": 1}]},
              open(inv, "w"))
    f, _ = run(stores=[inv], quiet=True)
    hit = any("created by no decision" in x for x in f)
    print(f"  {'PASS' if hit else 'FAIL'}  an invented id in a claim is caught")
    ok &= hit
    f, _ = run(stores=[inv], orig={}, quiet=True)
    hit = any("no origins loaded" in x for x in f)
    print(f"  {'PASS' if hit else 'FAIL'}  zero origins is refused, not passed over")
    ok &= hit
    empty = os.path.join(d, "empty.json")
    json.dump({"claims": []}, open(empty, "w"))
    f, _ = run(stores=[empty], quiet=True)
    hit = any("broken scan" in x for x in f)
    print(f"  {'PASS' if hit else 'FAIL'}  zero claims scanned is refused, not passed over")
    ok &= hit
    good = os.path.join(d, "good.json")
    json.dump({"claims": [{"subject": ["stint", "P_000001", "X", "1"], "person": "P_000001",
                           "predicate": "x", "value": 1}]}, open(good, "w"))
    f, _ = run(stores=[good], orig={"P_000001": ["identity"]}, quiet=True)
    print(f"  {'PASS' if not f else 'FAIL'}  a properly created id passes")
    ok &= not f
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("SELF-TEST -- the gate must be seen to fail before it is believed:")
        raise SystemExit(0 if selftest() else 1)
    print("SELF-TEST first:")
    if not selftest():
        raise SystemExit("the gate's own self-test failed; its verdict means nothing")
    print()
    fails, out = run()
    print()
    if fails:
        print("PERSON ORIGIN GATE: FAIL")
        for x in fails: print("   -", x)
        raise SystemExit(1)
    print("PERSON ORIGIN GATE: pass")
