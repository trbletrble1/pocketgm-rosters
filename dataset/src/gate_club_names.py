"""Gate: build/club-names.json is written by code, and every claim in it can be produced.

RS-G3 stood red at 414 from 7 September: claims appended to club-names.json BY HAND on 6
and 7 September, citing source records the store never registered. Nothing wrote them, so
re-running src/ingest_club_names.py would have dropped all 414 in silence (Ryan, 2026-09-13:
register what is there, and move the writing into code).

  K1  EVERY CLAIM'S RECORD IS REGISTERED in the store's own source_records table.
  K2  EVERY CLAIM IS ONE THE INGEST WRITES. The gate runs ingest_club_names.build() without
      writing and compares, claim for claim: a claim in the store the ingest would not write
      is a hand edit, and fails. So does a claim the ingest writes that the store lacks.
  K3  EVERY CITED PAGE IS ON DISK. Each record's locator resolves to a cached page.

  python3 src/gate_club_names.py        exit 1 = FAIL
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)


def key(c):
    return (json.dumps(c["subject"]), c["predicate"], json.dumps(c["value"]), c["source_record"])


def main():
    d = json.load(open(os.path.join(BASE, "build", "club-names.json")))
    table = d.get("source_records") or {}
    claims = d["claims"]
    print(f"club-names: {len(claims):,} claims, {len(table):,} registered records")
    if not claims:
        print("REFUSED: an empty store is not a pass."); return 2
    unreg = [c["source_record"] for c in claims if c["source_record"] not in table]
    check(not unreg, f"K1 every claim's record is registered ({len(unreg)} are not: {unreg[:3]})")

    import ingest_club_names as ICN
    store, pages = ICN.build()
    want = {key(c) for c in store.claims}
    have = {key(c) for c in claims}
    hand, missing = sorted(have - want), sorted(want - have)
    check(not hand and not missing,
          f"K2 every claim is one the ingest writes ({len(hand)} in the store the ingest would not write: "
          f"{[h[3] for h in hand[:3]]}; {len(missing)} the ingest writes that the store lacks)")

    gone = [sr for sr, p in pages.items() if not os.path.exists(p)]
    check(pages and not gone, f"K3 every cited page is on disk ({len(pages):,} pages; {len(gone)} missing: {gone[:3]})")

    print("\nCLUB NAMES GATE:", "pass" if not FAILS else f"{len(FAILS)} FAILURE(S)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
