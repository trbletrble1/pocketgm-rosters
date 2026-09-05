"""Mint ONE person id across all 220 per-season stores.

Today p_000190 is Joe Kapp in cfl-1966, Chick Maggioli in nfl-1950 and Greg
Dortch in nfl-2024. Person ids are store-local and collide. A player who spans
his own career is not a feature; it is correctness.

WHAT MAY JOIN TWO LOCAL PERSONS
  - the same source-native id (StatsCrew slug). This follows the SOURCE'S OWN
    identity assertion - tier A in design 2.4 - not a string we matched.
  - a recorded bidirectional p-/c- cross-reference, which is the evidence design
    2.4 trap 1 demands. A matching slug BODY is never evidence.

WHAT MAY NOT
  - a name. Ever. 1,559 names in this corpus denote more than one person.
    Local persons carrying no source-native id (court figures, keyed name+club+
    case) each keep their own identity and are never merged into a slug.
    This is also what makes CFL 1945-49 safe without a special case: birth date
    is 32.9% and college 56.7% there, so nothing but the slug is available, and
    nothing but the slug is used.

  python3 src/unify_identity.py [--write]
"""
import os, sys, json, glob, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
SLUG = re.compile(r"(statscrew:)?([pc]-[a-z0-9\-]+)")


class DSU:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb


def main():
    write = "--write" in sys.argv
    dsu = DSU()
    local_slugs = collections.defaultdict(set)     # (store, local_id) -> slugs
    slug_births = collections.defaultdict(set)     # slug -> birth dates seen
    no_id = []                                     # locals with no source-native id
    stores = sorted(glob.glob(os.path.join(BASE, "build", "*.json")))
    n_stores = 0
    for f in stores:
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or "denotations" not in d: continue
        n_stores += 1
        name = os.path.basename(f)[:-5]
        for x in d.get("denotations") or []:
            if not isinstance(x, dict): continue
            key = (name, x.get("person"))
            ma = str(x.get("matched_against", ""))
            m = SLUG.search(ma)
            if not m:
                no_id.append(key + (tuple(x.get("discriminator") or []),))
                dsu.find(key)                       # its own island
                continue
            slug = m.group(2)
            local_slugs[key].add(slug)
            dsu.union(key, ("slug", slug))
            b = re.search(r"born=([^,]+, \d{4})", ma)
            if b: slug_births[slug].add(b.group(1).strip())

    # p-/c- cross-references: a coach store denotation naming a p- slug is the
    # SAME man as that player slug, on the source's own bidirectional link.
    xref = 0
    for f in stores:
        if "coach" not in os.path.basename(f): continue
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or "denotations" not in d: continue
        name = os.path.basename(f)[:-5]
        # The cross-reference is a CLAIM, not a denotation: predicate
        # `also_played`, value = the p- slug, source_record = the c- page it was
        # read from. That bidirectional link is the evidence 2.4 trap 1 requires.
        for c_ in d.get("claims") or []:
            if not isinstance(c_, dict) or c_.get("predicate") != "also_played":
                continue
            pm = re.search(r"\b(p-[a-z0-9\-]+)", str(c_.get("value", "")))
            cm = re.search(r"\b(c-[a-z0-9\-]+)", str(c_.get("source_record", "")))
            if pm and cm:
                dsu.union(("slug", pm.group(1)), ("slug", cm.group(1))); xref += 1

    groups = collections.defaultdict(list)
    for key in list(dsu.p):
        groups[dsu.find(key)].append(key)
    people = [g for g in groups.values()]
    with_slug = [g for g in people if any(k[0] == "slug" for k in g)]
    print(f"stores read: {n_stores}")
    print(f"local person records: {sum(len(v) for v in groups.values())}")
    print(f"GLOBAL persons: {len(people)}")
    print(f"  identified by a source-native id: {len(with_slug)}")
    print(f"  no source-native id, kept separate (never merged by name): "
          f"{len(people)-len(with_slug)}")
    print(f"p-/c- cross-references applied: {xref}")

    # careers that span leagues
    span = []
    for g in with_slug:
        leagues = {k[0].split("-")[0] for k in g if k[0] != "slug"}
        if len(leagues) > 1: span.append((sorted(leagues), g))
    print(f"\npersons appearing in MORE THAN ONE league: {len(span)}")
    cnt = collections.Counter(tuple(l) for l, _ in span)
    for k, v in cnt.most_common(8): print(f"   {v:5}  {' + '.join(k)}")

    # a check on the SOURCE's own identity: one slug, two birth dates
    conflict = {s: b for s, b in slug_births.items() if len(b) > 1}
    print(f"\nslugs carrying MORE THAN ONE birth date (the source may have "
          f"conflated two men): {len(conflict)}")
    for s, b in list(conflict.items())[:5]: print(f"   {s}: {sorted(b)}")

    if write:
        out = {}
        for i, g in enumerate(sorted(people, key=lambda g: sorted(map(str, g))), 1):
            gid = f"P_{i:06d}"
            slugs = sorted(k[1] for k in g if k[0] == "slug")
            locals_ = sorted((k[0], k[1]) for k in g if k[0] != "slug")
            out[gid] = {"slugs": slugs, "local": locals_,
                        "evidence": "source_native_id" if slugs else "none - kept separate"}
        json.dump(out, open(os.path.join(BASE, "build-reports", "identity.json"), "w"))
        print(f"\nwrote build-reports/identity.json  ({len(out)} global persons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
