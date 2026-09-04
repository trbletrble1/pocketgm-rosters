"""Measure how often Coaching Tree and StatsCrew disagree about a coach's birth date.

§9.2 established birth date is nearly always PRESENT. Presence is not agreement,
and the discriminator the identity model leans on hardest must be measured for
agreement, not only for fill.
"""
import os, sys, re, json, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fetch_statscrew as F
SRC = os.environ.get("PGM3_SOURCES", os.path.expanduser("~/Documents/pgm3-sources"))
MON = {m: i+1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}

def to_iso(s):
    m = re.match(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", (s or "").strip())
    return f"{m.group(3)}-{MON[m.group(1)]:02d}-{int(m.group(2)):02d}" if m and m.group(1) in MON else None

def slug_for(name):
    parts = name.replace(".", "").split()
    if len(parts) < 2: return None
    return f"c-{parts[-1][:5].lower()}{parts[0][:3].lower()}"

def main():
    coaches = {}
    for f in glob.glob(os.path.join(SRC, "coachingtree", "*.json")):
        j = json.load(open(f))
        if isinstance(j, dict) and j.get("name") and j.get("birth_date"):
            coaches[j["name"]] = j
    res = collections.Counter(); rows = []
    for name, c in sorted(coaches.items()):
        base = slug_for(name)
        if not base: res["no slug form"] += 1; continue
        hit = None
        for n in range(1, 4):
            slug = f"{base}{n:03d}"
            try: info = F.parse_person(F.person(slug))
            except Exception: break
            if not info["is_real"]: continue
            if re.sub(r"[^a-z]", "", info["name"].lower()) == re.sub(r"[^a-z]", "", name.lower()):
                hit = (slug, info); break
        if not hit: res["not found on statscrew"] += 1; continue
        slug, info = hit
        sc = to_iso(info.get("born"))
        ct = c["birth_date"]
        if not sc: res["statscrew has no parseable date"] += 1; continue
        if sc == ct: res["AGREE"] += 1
        else:
            res["DISAGREE"] += 1
            rows.append((name, slug, ct, sc, "year only" if ct[5:] == sc[5:] else "day/month too"))
    print("birth-date agreement, Coaching Tree vs StatsCrew")
    for k, v in res.most_common(): print(f"  {k:32s} {v}")
    tot = res["AGREE"] + res["DISAGREE"]
    if tot: print(f"\n  agreement rate: {res['AGREE']}/{tot} = {100*res['AGREE']/tot:.1f}%")
    print(f"\ndisagreements ({len(rows)}):")
    for n, s, ct, sc, kind in rows:
        print(f"  {n:24s} {s:16s} coaching-tree {ct}   statscrew {sc}   ({kind})")
    json.dump(rows, open(os.path.join(HERE, "..", "build-reports", "birthdate-conflicts.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
