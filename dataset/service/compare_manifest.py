"""Say WHICH files differ between two move_manifest.py --save files.

    python3 compare_manifest.py before.json after.json
"""
import sys, json


def main(a, b):
    A, B = json.load(open(a)), json.load(open(b))
    ra = {r["path"]: r for r in A["rows"]}; rb = {r["path"]: r for r in B["rows"]}
    missing = sorted(set(ra) - set(rb)); extra = sorted(set(rb) - set(ra))
    sized = sorted(p for p in set(ra) & set(rb) if ra[p]["size"] != rb[p]["size"])
    hashed = sorted(p for p in set(ra) & set(rb)
                    if ra[p]["sha256"] and rb[p]["sha256"] and ra[p]["sha256"] != rb[p]["sha256"])
    print(f"{a}: {A['files']:,} files, {A['bytes']:,} bytes, {A['fingerprint']}")
    print(f"{b}: {B['files']:,} files, {B['bytes']:,} bytes, {B['fingerprint']}")
    if A["fingerprint"] == B["fingerprint"]:
        print("\nIDENTICAL. The copy is complete and, for the archive, byte-for-byte.")
        return 0
    print(f"\nDIFFERENT.  missing on the target: {len(missing)}   extra: {len(extra)}   wrong size: {len(sized)}   wrong content: {len(hashed)}")
    for label, items in (("MISSING", missing), ("WRONG SIZE", sized), ("WRONG CONTENT", hashed), ("EXTRA", extra)):
        for p in items[:20]: print(f"  {label:14s} {p}")
        if len(items) > 20: print(f"  {label:14s} ... and {len(items)-20} more")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
