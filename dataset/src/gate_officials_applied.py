"""The officials survive a rebuild, and stay ONE person each.

This gate exists because the failure it guards was invisible to the gate that
should have caught it. gate_person_index P3 compares the index before a rebuild
with the index after, so it can only see work that a rebuild DESTROYS. The
officials were not destroyed by a rebuild -- they were never applied by one. P3
read 0 officiating_seasons before and 0 after and passed. A check that measures a
regression cannot see a gap that is already open, so these checks measure the
STORE against the INDEX rather than the index against itself.

  python3 src/gate_officials_applied.py [--selftest]
"""
import os, re, sys, json, copy, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
import apply_officials as A

DECL = os.path.join(BASE, "declarations", "person-index-rebuild.json")
STORE = os.path.join(BASE, "build", "pfa-officials.json")


def light_copy(idx, pids):
    """Shallow index copy with only the named records duplicated.

    copy.deepcopy on a 106 MB index takes minutes and five probes made the
    selftest time out. Nothing here mutates a record this gate does not name, so
    copying those records and aliasing the rest is both correct and instant."""
    out = dict(idx)
    for p in pids:
        if p in out and isinstance(out[p], dict):
            out[p] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in out[p].items()}
    return out


def expected(store):
    """Who the STORE says must be in the index, and how many season keys each has."""
    return {pid: len(e["officiating_seasons"]) for pid, e in A.collect(store).items()}


def checks(idx, store, decl):
    out = []

    # F1  every man the store applies is in the index WITH his seasons.
    want = expected(store)
    bad = []
    for pid, k in want.items():
        rec = idx.get(pid)
        if rec is None:
            bad.append(f"{pid} absent from the index entirely"); continue
        got = len(rec.get("officiating_seasons") or {})
        if got != k:
            bad.append(f"{pid} holds {got} officiating season keys, the store says {k}")
    out.append(("F1", f"all {len(want)} officials are in the index with their seasons", bad[:8]))

    # F2  ONE PERSON PER CODE. Ryan's ruling: a man reachable at the player, coach
    # and official paths is one person with three roles, never three people.
    bycode = collections.defaultdict(list)
    for pid, v in idx.items():
        if pid == "_clubs" or not isinstance(v, dict): continue
        c = (v.get("identified_by") or {}).get("officials_pfa_code")
        if c: bycode[c].append(pid)
    bad = [f"PFA code {c} maps to {len(p)} people: {p}" for c, p in bycode.items() if len(p) > 1]
    out.append(("F2", "no PFA officials code maps to more than one person", bad[:8]))

    # F3  IDEMPOTENT. Applied to an index that already holds the officials, the
    # applier must change nothing -- and applied to one stripped of them, it must
    # put back exactly what is there now. Both directions, because
    # apply_promotions.py is only safe in one.
    # It must not depend on whether the LIVE index happens to be correct. Comparing
    # a fresh apply against the live index made F1's probe trip F3 too: corrupt one
    # record and both fire, which proves the checks overlap, not that either works.
    # So F3 starts from a stripped index, applies twice, and asks two questions the
    # live index cannot influence -- does the second apply change anything, and does
    # the first produce what the store says.
    bad = []
    created = {c["person_id"] for c in store["created"]}
    fresh = light_copy(idx, want)
    for pid in want:
        if pid not in fresh: continue
        fresh[pid].pop("officiating_seasons", None)
        fresh[pid].pop("roles", None)
        # NAME IS STRIPPED ONLY FOR THE 978 THE STORE CREATED. The 74 who already
        # existed get their name from the CLAIMS FLOW, not from pfa-officials.json,
        # so a rebuild hands them to this script already named and it never sets
        # one. Blanking them would simulate a rebuild that does not happen.
        if pid in created:
            fresh[pid]["name"] = None
    _, a1, _ = A.main(write=False, idx=fresh)
    snap = {p: {f: a1[p].get(f) for f in ("officiating_seasons", "roles", "name")}
            for p in want if p in a1}
    _, a2, _ = A.main(write=False, idx=light_copy(a1, want))
    for pid in want:
        if pid not in a2: bad.append(f"{pid} lost on the second apply"); continue
        for f in ("officiating_seasons", "roles", "name"):
            if a2[pid].get(f) != snap.get(pid, {}).get(f):
                bad.append(f"{pid}.{f} changed on the second apply -- not idempotent")
        if len(a1[pid].get("officiating_seasons") or {}) != want[pid]:
            bad.append(f"{pid} a fresh apply gave "
                       f"{len(a1[pid].get('officiating_seasons') or {})} season keys, "
                       f"the store says {want[pid]}")
    out.append(("F3", "a second apply changes nothing and a fresh apply matches the store", bad[:8]))

    # F4  DECLARED, so a rebuild runs it without anyone remembering to.
    names = [c["script"] for c in decl.get("chain", [])]
    bad = ([] if "apply_officials.py" in names else
           ["apply_officials.py is not in the rebuild chain -- a rebuild would drop "
            "the officials again and P3 would not notice"])
    if decl.get("known_missing_steps"):
        bad.append(f"{len(decl['known_missing_steps'])} step(s) still recorded as missing")
    out.append(("F4", "the applier is declared in the rebuild chain", bad))

    # F5  RECONCILES. Index holders == store men; refusals stay out.
    holders = {p for p, v in idx.items()
               if p != "_clubs" and isinstance(v, dict) and v.get("officiating_seasons")}
    refused = {r["pfa_code"] for r in store["refusals"]}
    leaked = [p for p in holders
              if (idx[p].get("identified_by") or {}).get("officials_pfa_code") in refused]
    bad = []
    if len(holders) != len(want):
        bad.append(f"{len(holders)} people hold officiating_seasons, the store applies {len(want)}")
    if leaked:
        bad.append(f"{len(leaked)} refused official(s) reached the index: {leaked[:4]}")
    out.append(("F5", "population reconciles and no refused official reached the index", bad))
    return out


def run():
    idx = IO.load_index(); store = json.load(open(STORE)); decl = json.load(open(DECL))
    res = checks(idx, store, decl)
    for cid, desc, bad in res:
        print(f"  {cid} {'FAIL' if bad else 'pass'}  {desc}")
        for b in bad: print(f"        {b}")
    return res


def selftest():
    idx = IO.load_index(); store = json.load(open(STORE)); decl = json.load(open(DECL))
    base = {c for c, _, bad in checks(idx, store, decl) if bad}
    print("SELFTEST -- each check must fail for its own reason and no other")
    print(f"baseline: {sorted(base) or 'all passing'}\n")
    ok = []

    def probe(name, mut):
        i = light_copy(idx, list(expected(store)))
        s, d = copy.deepcopy(store), copy.deepcopy(decl)
        i, s, d = mut(i, s, d)
        fired = {c for c, _, bad in checks(i, s, d) if bad} - base
        good = fired == {name}
        print(f"  {'OK  ' if good else 'BAD '} {name}: added {sorted(fired) or ['nothing']}")
        return good

    def f1(i, s, d):
        # DROP ONE KEY, not the lot. Emptying the dict makes him stop counting as a
        # holder and trips F5 as well, which would prove only that the two checks
        # overlap. One missing season is the smallest thing F1 alone must catch.
        p = sorted(expected(s))[0]
        os_ = dict(i[p]["officiating_seasons"]); os_.pop(sorted(os_)[0])
        i[p]["officiating_seasons"] = os_
        return i, s, d
    def f2(i, s, d):
        p = sorted(expected(s))[0]
        i["P_ZZZ_DUPLICATE"] = {"identified_by": {"officials_pfa_code":
            (i[p].get("identified_by") or {}).get("officials_pfa_code")}}
        return i, s, d
    def probe_f3():
        """F3 no longer reads the live index, so corrupting a record cannot prove
        it works -- the probe has to break the APPLIER. Making collect() drift by
        one marker per call is the smallest true violation: apply twice and the
        second result differs from the first, which is precisely non-idempotence."""
        real = A.collect; state = {"n": 0}
        def drift(store):
            state["n"] += 1
            per = real(store)
            for e in per.values():
                e["roles"] = list(e["roles"]) + [f"run{state['n']}"]
            return per
        A.collect = drift
        try:
            fired = {c for c, _, bad in checks(light_copy(idx, list(expected(store))),
                                               store, decl) if bad} - base
        finally:
            A.collect = real
        good = fired == {"F3"}
        print(f"  {'OK  ' if good else 'BAD '} F3: added {sorted(fired) or ['nothing']}")
        return good
    def f4(i, s, d):
        d["chain"] = [c for c in d["chain"] if c["script"] != "apply_officials.py"]
        return i, s, d
    def f5(i, s, d):
        r = s["refusals"][0]["pfa_code"]
        i["P_ZZZ_REFUSED"] = {"officiating_seasons": {"NFL|1970|Umpire": []},
                              "identified_by": {"officials_pfa_code": r}}
        return i, s, d

    for n, m in (("F1", f1), ("F2", f2)):
        ok.append(probe(n, m))
    ok.append(probe_f3())
    for n, m in (("F4", f4), ("F5", f5)):
        ok.append(probe(n, m))
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    res = run()
    nf = sum(1 for _, _, b in res if b)
    print(f"\n{len(res)-nf} pass, {nf} FAIL")
    sys.exit(1 if nf else 0)
