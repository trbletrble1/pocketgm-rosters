"""Gate the college-guide candidate build. Properties over EVERY record.

Four failures this prevents, each silent:
  a candidate consumed as an identification;
  a field taken from a document whose columns cannot be bound to their names;
  an age written from an unlabelled table, where it cannot be told from a jersey;
  a prose block stored altered.

  python3 src/gate_college_guides.py     exit 1 = FAIL
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
SRC = os.path.expanduser("~/Documents/pgm3-sources/college-pre1950")
DECL = json.load(open(os.path.join(BASE, "declarations", "college-guides.json"), encoding="utf-8"))
DROPPED = {"Wisconsin_Football,_1947", "Wisconsin_Football,_1948"}


def main():
    p = os.path.join(BASE, "build", "college-guides-candidates.json")
    if not os.path.exists(p):
        print("FAIL: build/college-guides-candidates.json missing"); return 1
    d = json.load(open(p))
    C = d["candidates"]; fail = []
    def chk(c, m):
        if not c: fail.append(m)

    # 1 NOTHING HERE MAY LOOK LIKE A CLAIM
    chk("claims" not in d, "the build has a claims key; a candidate could be consumed as a fact")
    blob = json.dumps(d)
    chk('"subject"' not in blob, "a record carries a subject; only candidate_person is allowed")
    for c in C:
        chk(c.get("IS_NOT_A_CONFIRMED_IDENTIFICATION") is True,
            f"{c['name_as_matched']}: not marked as unconfirmed")
        chk("ruling" in (c.get("promotion") or ""), "promotion note missing")

    # 2 every candidate passed the STRICT test, verified against the cross-reference
    X = json.load(open(SRC + "/xref_strict.json"))
    strict = set()
    for r in X:
        if r["strict"]: strict.update(r["names"])
    names = {c["name_as_matched"] for c in C}
    chk(names <= strict, f"{len(names - strict)} candidates did not pass the strict test")

    # 3 NO FIELD FROM A DOCUMENT WHOSE COLUMNS CANNOT BE BOUND
    for c in C:
        for o in c["observations"]:
            if o["document"] in DROPPED:
                chk("fields" not in o,
                    f"{c['name_as_matched']}: fields taken from {o['document']}, which is dropped")
    # 4 NO AGE, ANYWHERE
    for c in C:
        for o in c["observations"]:
            for k in (o.get("fields") or {}):
                chk(k.lower().rstrip(".") not in {"age", "yrs", "years"},
                    f"a refused field was written: {k}")
    chk("age" in d["refused_fields"], "the build does not record that age is refused")

    # 5 every field's value is present in the man's own verbatim line (structural binding)
    for c in C:
        for o in c["observations"]:
            for k, v in (o.get("fields") or {}).items():
                bare = re.sub(r"[^A-Za-z0-9]", "", str(v)).lower()
                line = re.sub(r"[^A-Za-z0-9]", "", o["verbatim_line"]).lower()
                chk(bare in line,
                    f"{c['name_as_matched']}: {k}={v!r} is not on his own line - positional read")

    # 6 every prose block round-trips against its source
    cache = {}
    rt = 0
    for c in C:
        for o in c["observations"]:
            if "prose" not in o: continue
            doc = o["document"]
            if doc not in cache:
                for q in (f"{SRC}/text/{doc}.txt", f"{SRC}/text_container/{doc}.txt"):
                    if os.path.exists(q):
                        cache[doc] = [x.strip() for x in open(q, encoding="utf-8", errors="replace")]
                        break
            have = cache.get(doc) or []
            want = [x.strip() for x in o["prose"].split("\n") if x.strip()]
            i = 0; ok = True
            for w in want:
                while i < len(have) and have[i] != w: i += 1
                if i >= len(have): ok = False; break
                i += 1
            chk(ok, f"{c['name_as_matched']}: prose does not round-trip against {doc}")
            rt += 1

    nf = sum(1 for c in C for o in c["observations"] if o.get("fields"))
    npr = sum(1 for c in C for o in c["observations"] if o.get("prose"))
    print(f"candidates {len(C)}  observations-with-fields {nf}  prose blocks {npr} (round-tripped {rt})")
    print(f"documents dropped for field extraction: {sorted(d['documents_dropped_for_field_extraction'])}")
    print(f"refused fields: {d['refused_fields']}")
    if fail:
        print("\nGATE FAILED:"); [print("  -", f) for f in fail[:10]]; return 1
    print("\nGATE PASSED: nothing is an identification, no positional field, no age, prose intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
