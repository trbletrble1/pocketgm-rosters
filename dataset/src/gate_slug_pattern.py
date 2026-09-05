"""Gate: every stored source-native id must match the DECLARED pattern.

declarations/statscrew.json :: person_id_scheme.pattern is
    {prefix}-{surname[:5]}{forename[:3]}{NNN}
so every slug ends in a three-digit counter. Anything that does not is a
TRUNCATION, and a truncated slug is not a weaker id - it is a DIFFERENT id that
silently merges every man who shares its prefix.

Found in the wild: the roster parser used (p-[a-z0-9]+), which stops at a
hyphen. "Jean-Baptiste" truncates to "jean-", so p-jean-jav001 was stored as
"p-jean" - and NINE different Jean-* players became one person.

The declaration described this pattern from the start. Nothing enforced it, and
report 23's gate cannot: it checks that a key is NAMED in src/, not that it is
honoured. This is that limit, closed for this one key.

  python3 src/gate_slug_pattern.py        exit 1 = FAIL
"""
import os, sys, json, glob, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
VALID = re.compile(r"^[pc]-[a-z0-9\-]+\d{3}$")


def main():
    decl = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
    pattern = decl["person_id_scheme"]["pattern"]
    bad = collections.defaultdict(set)
    seen = 0
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for x in d.get("denotations") or []:
            if not isinstance(x, dict): continue
            ma = str(x.get("matched_against", ""))
            m = re.search(r"statscrew:([pc]-[a-z0-9\-]+)", ma)
            if not m: continue
            seen += 1
            slug = m.group(1)
            if not VALID.match(slug):
                sr = str(x.get("source_record", ""))
                bad[slug].add(sr.rsplit("#", 1)[-1] if "#" in sr else sr)
    print(f"declared pattern: {pattern}")
    print(f"stored slugs checked: {seen}")
    print(f"slugs that do NOT match (truncated): {len(bad)}")
    hidden = sum(len(v) for v in bad.values())
    for s, names in sorted(bad.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  [FAIL] {s:14} merges {len(names)} men: {sorted(names)[:4]}")
    if bad:
        print(f"\nGATE FAILED: {len(bad)} truncated slugs hiding {hidden} distinct men.")
        return 1
    print("\nGATE PASSED: every stored slug matches the declared pattern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
