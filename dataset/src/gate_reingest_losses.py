"""Gate: a re-ingest that loses claims must say so itself, with a reason, or it fails.

Ryan's ruling, 2026-09-11. Re-running the PFA coach ingest dropped 18 coaches -- 597 claims --
and gained nothing. Its own counts moved (1,759 resolved -> 1,741), but nothing compared the new
store with the one it replaced, the writer overwrote it, and no gate noticed. It was found only
because the store had been backed up and diffed by hand. The archive has found that shape before;
this one was live.

  R1  EVERY CLAIM THE CANDIDATE LOSES AGAINST ITS PREDECESSOR IS ACCOUNTED FOR BY THE CANDIDATE
      ITSELF: the store must carry `lost_since_predecessor`, one entry per source record it lost
      claims from, with the count and a reason. A loss the store does not state -- or states with
      the wrong count, or with no reason -- FAILS. A silent loss is the defect, whether or not the
      loss is right.
  R2  NOTHING IS LOST TO A PERSON WHO IS ONLY A MERGE SHELL. A reason that names a conflict between
      a person and the shell merged into him is not a reason (the 18 of 2026-09-11 were exactly that).

Claims are compared at the fact's own level -- (subject, predicate, value, source record) -- never
by totals (docs/DATASET_PRECEDENTS.md: a rewritten store is compared with its predecessor).

    python3 src/gate_reingest_losses.py --candidate NEW.json --predecessor OLD.json
    python3 src/gate_reingest_losses.py --selftest
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def losses(old, new):
    """-> {source_record: n claims lost}, compared fact by fact."""
    def keyed(d):
        c = collections.Counter()
        for x in d.get("claims", []):
            c[(json.dumps(x.get("subject")), x.get("predicate"), json.dumps(x.get("value"), sort_keys=True),
               x.get("source_record"))] += 1
        return c
    lost = keyed(old) - keyed(new)
    by = collections.Counter()
    for k, n in lost.items(): by[k[3]] += n
    return by


def r12(old, new, shells=frozenset()):
    lost = losses(old, new)
    stated = {e.get("source_record"): e for e in (new.get("lost_since_predecessor") or [])}
    unstated = {r: n for r, n in lost.items() if r not in stated}
    wrong = {r: (n, stated[r].get("claims")) for r, n in lost.items() if r in stated and stated[r].get("claims") != n}
    no_reason = [r for r in lost if r in stated and not stated[r].get("reason")]
    total = sum(lost.values())
    check(not unstated and not wrong and not no_reason,
          f"R1 every one of the {total:,} claims lost against the predecessor is stated by the store itself, "
          f"with its count and a reason"
          + ("" if not unstated else f" -- {sum(unstated.values()):,} claims on {len(unstated)} records are NOT "
                                     f"stated, e.g. {sorted(unstated.items())[:3]}")
          + ("" if not wrong else f" -- {len(wrong)} stated with the wrong count, e.g. {sorted(wrong.items())[:2]}")
          + ("" if not no_reason else f" -- {len(no_reason)} stated with no reason, e.g. {no_reason[:2]}"))
    shell_reasons = [r for r, e in stated.items() if r in lost and set(e.get("candidates") or []) & shells
                     and len(set(e.get("candidates") or [])) > 1]
    check(not shell_reasons, "R2 no loss is explained by a conflict with a merge shell"
          + ("" if not shell_reasons else f" -- {len(shell_reasons)} are, e.g. {shell_reasons[:3]}"))
    if total:
        why = collections.Counter(stated[r]["reason"] for r in lost if r in stated and stated[r].get("reason"))
        print(f"         losses by stated reason: {dict(why)}")


def selftest():
    global FAILS
    ok = True
    def c(subj, pred, val, sr): return {"subject": subj, "predicate": pred, "value": val, "source_record": sr}
    old = {"claims": [c(["stint", "P_1", "BAL", "NFL-1975"], "pfa.coaching_season", {"r": 1}, "pfa#coaches/baug00600.html"),
                      c(["person", "P_2"], "pfa.name_as_printed", "X", "pfa#coaches/x.html")]}
    silent = {"claims": [old["claims"][1]]}
    stated = {"claims": [old["claims"][1]], "lost_since_predecessor": [
        {"source_record": "pfa#coaches/baug00600.html", "claims": 1, "reason": "route_conflict", "candidates": ["P_1", "P_9"]}]}
    wrong_n = {"claims": [old["claims"][1]], "lost_since_predecessor": [
        {"source_record": "pfa#coaches/baug00600.html", "claims": 5, "reason": "route_conflict"}]}
    for label, new, shells, want_fail in (
            ("a coach lost silently (the 18 of 2026-09-11)", silent, frozenset(), True),
            ("the same loss, stated with its count and reason", stated, frozenset(), False),
            ("stated, but the reason is a conflict with a merge shell", stated, frozenset({"P_9"}), True),
            ("stated with the wrong count", wrong_n, frozenset(), True),
            ("nothing lost", old, frozenset(), False)):
        FAILS = []; r12(old, new, shells); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    new = json.load(open(argv[argv.index("--candidate") + 1]))
    old = json.load(open(argv[argv.index("--predecessor") + 1]))
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    shells = frozenset(p for p, v in idx.items() if isinstance(v, dict) and v.get("merged_into"))
    r12(old, new, shells)
    if FAILS:
        print(f"\nRE-INGEST LOSS GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nRE-INGEST LOSS GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
