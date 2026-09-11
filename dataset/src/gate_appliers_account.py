"""Gate: an applier that does less than a decision recorded must say why -- a legitimate why -- or fail.

Ryan's ruling, 2026-09-11. After the 9 September shape change moved coaching keys from `seasons`
into `coaching_seasons`, two appliers kept reading `seasons` and did almost nothing, silently:

  - apply_club_keys: 677 decided rewrites, 19 applied, 658 skipped (`if from not in ss: continue`);
  - apply_person_merges: 93 merges "applied", moving nothing of what they recorded -- and the
    1,929 club-key rewrites a merge carries went nowhere with them.

"Decided 677, applied 19, skipped 658" would have been loud on day one. This is the loss list
(src/gate_reingest_losses.py) pointed at decisions instead of claims.

  A1  EVERY APPLIER IN THE CHAIN WRITES AN ACCOUNT of every decision it was given
      (build-reports/applier-accounts/<applier>.json, via index_io.write_account), and the
      account covers every decision -- none unaccounted.
  A2  NO DECISION DOES LESS THAN IT RECORDED WITHOUT A LEGITIMATE REASON. The reasons that are
      legitimate are named below, per applier. Anything else -- including "the key is held in a
      dict this applier does not read", which is a symptom and not a reason -- FAILS, loudly, with
      the count and the reason.

    python3 src/gate_appliers_account.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
ACCOUNTS = os.path.join(BASE, "build-reports", "applier-accounts")

# THE LEGITIMATE REASONS, per applier. Anything not here fails. Each is a reason the DECISION no
# longer has work to do -- never a reason the applier could not find its work.
LEGITIMATE = {
    "apply_club_keys": {
        "the person holds neither key: the season this rewrite named is no longer in the index",
        "the person is not in the index",
    },
    "apply_person_merges": {
        "every recorded club-season is already held by the canonical person",
        "a constituent is not in the index",
    },
    # The other five chain appliers account too (Ryan, 2026-09-11: two of the chain's appliers were
    # skipping in silence, which makes accounting the rule rather than the exception). Their named
    # skips are states of the DATA -- a record already gone, a slug the index never held -- stated
    # and counted. A promoted player whose claims did not land is NOT among them: it fails.
    "apply_promotions": set(),
    "apply_player_promotions": set(),
    "demote_stintless": {"the promoted record is already absent from the index"},
    "restore_cfl1945_seasons": {"no club is readable in the man's roster record",
                                "the man's slug is not in the index", "the season is already held"},
    "apply_officials": set(),
}
# EVERY applier in the chain (declarations/person-index-rebuild.json), in chain order.
ACCOUNTING = ("apply_club_keys", "apply_person_merges", "apply_promotions", "apply_player_promotions",
              "demote_stintless", "restore_cfl1945_seasons", "apply_officials")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def judge(name, acc):
    legit = LEGITIMATE.get(name, set())
    outs = acc.get("outcomes") or []
    check(acc.get("decided") == len(outs) and outs is not None,
          f"A1 {name}: the account covers every decision ({acc.get('decided')} decided, {len(outs)} accounted)")
    bad = collections.Counter()
    for o in outs:
        if o["outcome"] == "applied" and o.get("moved", 0) >= o.get("expected", 0): continue
        r = o.get("reason")
        if not r or r not in legit: bad[r or "NO REASON GIVEN"] += 1
    t = acc.get("tally", {})
    check(not bad, f"A2 {name}: every decision that did less than it recorded has a legitimate reason "
                   f"-- {t}, moved {acc.get('moved', 0):,} of {acc.get('expected', 0):,} recorded"
                   + ("" if not bad else f" -- {sum(bad.values()):,} do NOT: {dict(bad)}"))


def selftest():
    global FAILS
    ok = True
    def o(out, exp, mv, r=None): return {"decision": "d", "outcome": out, "expected": exp, "moved": mv, "reason": r}
    cases = (
        ("club keys skipped because the key sits in coaching_seasons (9 September's state)", "apply_club_keys",
         [o("applied", 1, 1), o("skipped", 1, 0, "the from-key is held in coaching_seasons, a dict this applier does not read")], True),
        ("a skip with no reason at all", "apply_club_keys", [o("skipped", 1, 0)], True),
        ("a merge 'applied' that moved nothing, legitimately (all already held)", "apply_person_merges",
         [o("partly_applied", 3, 0, "every recorded club-season is already held by the canonical person")], False),
        ("a merge 'applied' that moved nothing, and does not say why", "apply_person_merges", [o("applied", 3, 0)], True),
        ("everything applied", "apply_club_keys", [o("applied", 1, 1), o("applied", 2, 2)], False))
    for label, name, outs, want_fail in cases:
        FAILS = []; judge(name, {"decided": len(outs), "outcomes": outs, "tally": {}}); got = bool(FAILS)
        g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    for name in ACCOUNTING:
        p = os.path.join(ACCOUNTS, f"{name}.json")
        if not os.path.exists(p):
            check(False, f"A1 {name}: NO ACCOUNT -- the applier has not run, or does not account"); continue
        judge(name, json.load(open(p)))
    if FAILS:
        print(f"\nAPPLIER ACCOUNT GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nAPPLIER ACCOUNT GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
