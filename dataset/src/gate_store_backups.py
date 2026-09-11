"""Gate: a store backup is not committed, and nothing depends on one.

Ryan, 2026-09-11. A copy of a build/ file taken before a run overwrites it is a rollback aid
for that session, not a backup and not a record. docs/DATASET_PRECEDENTS.md, "A store backup
is a rollback aid, not a backup", says where one is safe and for how long.

  B1  NO STORE BACKUP IS TRACKED BY GIT. A 56.5 MB one was pushed on 2026-09-11 and stays in
      history by ruling -- rewriting a published branch is worse than a large blob.
  B2  EVERY STORE BACKUP ON DISK IS IGNORED. A backup named off the convention would be
      committed by the next `git add`, which is how the first one got in.
  B3  NOTHING IN src/ OR service/ READS A STORE BACKUP. A file a gate or the service reads is
      a RECORD -- a baseline, a reversal list -- and a record must be tracked, because it
      outlives the session. If code comes to depend on a backup, it has stopped being one.

The convention: build-reports/<store>-store.before-<YYYY-MM-DD>.json

    python3 src/gate_store_backups.py [--selftest]
"""
import os, re, sys, glob, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, ".."))
PATTERN = re.compile(r"-store\.before-\d{4}-\d{2}-\d{2}\.json$")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def b1(tracked):
    hit = sorted(f for f in tracked if PATTERN.search(f))
    check(not hit, f"B1 no store backup is tracked by git" + ("" if not hit else f" -- {hit}"))


def b2(on_disk, ignored):
    loose = sorted(f for f in on_disk if PATTERN.search(f) and f not in ignored)
    check(not loose, f"B2 all {sum(1 for f in on_disk if PATTERN.search(f))} store backups on disk "
                     f"are ignored" + ("" if not loose else f" -- not ignored: {loose}"))


def b3(backups, sources):
    """sources: {path: text}. A backup's file NAME appearing in code means code reads it."""
    read = sorted({(os.path.basename(b), p) for b in backups for p, t in sources.items()
                   if os.path.basename(b) in t})
    check(not read, "B3 nothing in src/ or service/ reads a store backup"
          + ("" if not read else f" -- {read[:3]}"))


def main(argv):
    if "--selftest" in argv: return selftest()
    tracked = subprocess.run(["git", "ls-files", "build-reports"], cwd=BASE,
                             capture_output=True, text=True, check=True).stdout.split()
    on_disk = [os.path.relpath(f, BASE) for f in glob.glob(os.path.join(BASE, "build-reports", "*"))]
    cand = [f for f in on_disk if PATTERN.search(f)]
    r = subprocess.run(["git", "check-ignore", "--no-index", *cand], cwd=BASE,
                       capture_output=True, text=True) if cand else None
    ignored = set(r.stdout.split()) if r else set()
    sources = {}
    for d in ("src", "service"):
        for f in glob.glob(os.path.join(BASE, d, "*.py")):
            if os.path.basename(f) == os.path.basename(__file__): continue
            sources[os.path.relpath(f, BASE)] = open(f, errors="replace").read()
    b1(tracked); b2(on_disk, ignored); b3(cand, sources)
    if FAILS:
        print(f"\nSTORE BACKUP GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nSTORE BACKUP GATE: pass"); return 0


def selftest():
    global FAILS
    ok = True

    def expect(label, fn, want_fail):
        global FAILS
        nonlocal ok
        FAILS = []; fn(); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if got else 'pass'}")

    bk = "build-reports/pfa-club-rosters-store.before-2026-09-11.json"
    expect("B1 a store backup is tracked", lambda: b1([bk, "build-reports/x.json"]), True)
    expect("B1 none tracked", lambda: b1(["build-reports/index-orphans-2026-09-11.json"]), False)
    expect("B2 a store backup on disk is not ignored", lambda: b2([bk], set()), True)
    expect("B2 it is ignored", lambda: b2([bk], {bk}), False)
    expect("B3 a gate reads a store backup",
           lambda: b3([bk], {"src/gate_x.py": "open('pfa-club-rosters-store.before-2026-09-11.json')"}), True)
    expect("B3 nothing reads it", lambda: b3([bk], {"src/gate_x.py": "open('index-orphans.json')"}), False)
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
