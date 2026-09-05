"""Gate: the five hard rules of the Wikipedia layer, each shown to refuse.

Wikipedia is ranked below media guides and contemporary newspapers, and its
infobox fields are effectively uncited -- 0% for birth date, college and draft,
and only 6.7% of infoboxes carry a reference anywhere. Uncited does not mean
unused: for most of these men it is the only source for death date, high school
and draft. So the protection is not exclusion, it is that every claim says who
said it and a fair-use image cannot be expressed at all.

  python3 src/gate_wikipedia.py      exit 1 = FAIL
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import ingest_wikipedia as W

BUILD = os.path.join(BASE, "build", "wikipedia.json")


def main():
    checks, fails = [], []
    D = json.load(open(BUILD))
    claims = D["claims"]; srs = set(D["source_records"]); matched = set(D["matched"])
    print(f"claims: {len(claims):,}   source records: {len(srs):,}   matched people: {len(matched):,}")

    # 1 -- no claim without a source attribution
    bad = [c for c in claims if c.get("source_record") not in srs
           or not c.get("attribution") or not c.get("stated_by")]
    (checks if not bad else fails).append(
        "every claim carries a resolvable source record and an attribution"
        if not bad else f"[FAIL] {len(bad)} claims lack a source record or attribution")

    # 2 -- an unmatched person produces no claims at all
    orphan = {c["subject"][1] for c in claims if c["subject"][1] not in matched}
    (checks if not orphan else fails).append(
        "no claim attaches to an unmatched person"
        if not orphan else f"[FAIL] {len(orphan)} unmatched people carry claims")

    # 3 -- no photograph overwrites one already held
    over = [c for c in claims if c["predicate"] == "wikipedia.photograph"
            and c["subject"][1] in W.HELD_PHOTOS]
    (checks if not over else fails).append(
        f"{sum(1 for c in claims if c['predicate']=='wikipedia.photograph')} photographs added, "
        f"none over a person who already held one"
        if not over else f"[FAIL] {len(over)} photographs overwrite a held image")

    # 4 -- a fair-use image is INEXPRESSIBLE, not merely forbidden
    ws = W.WikiStore(); ws.matched = {"P_TEST"}
    sr = ws.record("Test")
    for lic, needle in (("Fair use", "fair-use"), ("Non-free fair use", "fair-use"),
                        ("All rights reserved", "not public domain")):
        try:
            ws.photo(sr, "P_TEST", "x.jpg", lic)
            fails.append(f"[FAIL] a '{lic}' image was accepted")
        except W.IngestError as e:
            if needle not in str(e): fails.append(f"[FAIL] '{lic}' refused for the wrong reason: {e}")
            else: checks.append(f"refuses a '{lic}' image: {str(e)[:60]}")
    for lic in ("Public domain", "PD-US", "CC BY-SA 4.0", "CC0"):
        try:
            ws.photo(sr, "P_TEST", "y.jpg", lic); checks.append(f"admits '{lic}'")
            ws.photo_added.discard("P_TEST")
        except W.IngestError as e:
            fails.append(f"[FAIL] '{lic}' was refused: {e}")
    # and gap-fill: a person who already holds one is refused
    held = next(iter(W.HELD_PHOTOS))
    ws.matched.add(held)
    try:
        ws.photo(sr, held, "z.jpg", "Public domain")
        fails.append("[FAIL] a photograph was added over a held one")
    except W.IngestError as e:
        assert "gap-fill" in str(e), e
        checks.append("refuses a photograph for a person who already holds one")
    # and a claim for an unmatched person is refused at the door
    try:
        ws.add(sr, "P_NOT_MATCHED", "wikipedia.death_date", "x")
        fails.append("[FAIL] an unmatched person was given a claim")
    except W.IngestError as e:
        assert "UNMATCHED" in str(e), e
        checks.append("refuses a claim for an unmatched person")

    # 5 -- prose carries whether it is cited, queryably
    prose = [c for c in claims if c["predicate"] == "wikipedia.prose"]
    nocite = [c for c in prose if "cited" not in c]
    cited = sum(1 for c in prose if c.get("cited"))
    (checks if not nocite else fails).append(
        f"all {len(prose):,} prose claims record `cited`: {cited:,} cited, "
        f"{len(prose)-cited:,} uncited, and the field is queryable"
        if not nocite else f"[FAIL] {len(nocite)} prose claims do not record `cited`")

    # 6 -- disagreements are held, not resolved
    dis = [c for c in claims if c.get("statscrew_differs")]
    both = [c for c in dis if c.get("statscrew_value")]
    (checks if len(dis) == len(both) else fails).append(
        f"{len(dis)} StatsCrew disagreements hold BOTH values, none resolved"
        if len(dis) == len(both) else "[FAIL] a disagreement dropped one side")

    for c in checks: print("  " + c)
    for f in fails: print("  " + f)
    if fails:
        print(f"\nGATE FAILED: {len(fails)} checks did not hold.")
        return 1
    print(f"\nGATE PASSED: {len(checks)} checks, and the four refusals fire for their own reasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
