"""Which not-file-shaped declarations claim no denominator for a whole that has
measurable parts.

THE DEFECT. `why_no_denominator` is true of a source whole and can be false of
every part of it. PFA's entry said so for years while 203 draft pages sat on disk
unread, one per year per league, trivially enumerable -- and Phil Flanagan, a 1936
Giants ninth-round pick, is absent from the archive because of it.

THIS SCRIPT DOES NOT RULE. It reports evidence per entry and says `unknown` where
the evidence does not settle it. Rewriting the entries is Ryan's call.

  python3 src/measure_declaration_parts.py
"""
import os, sys, json, re, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

DECL = os.path.join(BASE, "declarations", "source-coverage.json")
SOURCES = os.path.expanduser("~/Documents/pgm3-sources")
# A source id in one of these namespaces names ONE physical document. Its whole is
# its only part, so the rule is satisfied by saying that -- not by silence.
ONE_DOCUMENT = ("court/", "news/", "sys/", "programme-", "media-guide-", "hearing-")


def evidence():
    conn = sqlite3.connect(paths.READ_MODEL)
    claims, locs = collections.Counter(), collections.defaultdict(set)
    for sid, sr, n in conn.execute(
            "select source_id, source_record, count(*) from claim "
            "where source_id is not null group by source_id, source_record"):
        claims[sid] += n
        locs[sid].add(sr.split("#", 1)[1] if "#" in sr else sr)
    return claims, locs


def shape(loc):
    return re.sub(r"\d", "#", re.sub(r"[a-z0-9]{6,}", "X", str(loc)))


def main():
    d = json.load(open(DECL))
    nfs = {k: v for k, v in d["not_file_shaped"].items() if not k.startswith("_")}
    claims, locs = evidence()
    on_disk = set(os.listdir(SOURCES)) if os.path.isdir(SOURCES) else set()

    buckets = collections.defaultdict(list)
    for sid, spec in nfs.items():
        n_loc = len(locs.get(sid, ()))
        shapes = len({shape(l) for l in locs.get(sid, ())})
        one_doc = sid.startswith(ONE_DOCUMENT)
        has = "enumerable_parts" in (spec or {})
        if has:
            b = "DECLARES ITS PARTS"
        elif one_doc:
            b = "ONE DOCUMENT -- whole is the only part, but the entry does not say so"
        elif n_loc > 100 and (shapes <= 20 or shapes / max(n_loc, 1) < 0.05):
            b = ("SAME PROBLEM, REGULAR: many locators in few shapes -- a repeating "
                 "page kind, which is what makes a part enumerable")
        elif n_loc > 100:
            b = ("SAME PROBLEM, IRREGULAR: many locators, no repeating shape. Parts may "
                 "exist but the locators do not show them; the source's own index must "
                 "be read")
        else:
            b = "UNKNOWN -- cannot be established from the read model alone"
        buckets[b].append((sid, claims[sid], n_loc, shapes))

    order = ["DECLARES ITS PARTS",
             ("SAME PROBLEM, REGULAR: many locators in few shapes -- a repeating "
              "page kind, which is what makes a part enumerable"),
             ("SAME PROBLEM, IRREGULAR: many locators, no repeating shape. Parts may "
              "exist but the locators do not show them; the source's own index must "
              "be read"),
             "ONE DOCUMENT -- whole is the only part, but the entry does not say so",
             "UNKNOWN -- cannot be established from the read model alone"]
    print(f"{len(nfs)} not-file-shaped declarations.\n")
    for b in order:
        rows = sorted(buckets.get(b, []), key=lambda r: -r[1])
        if not rows:
            continue
        print(f"{b}  ({len(rows)})")
        print(f"   {'source':44s}{'claims':>11s}{'locators':>10s}{'shapes':>8s}")
        for sid, c, nl, sh in rows:
            print(f"   {sid:44s}{c:>11,}{nl:>10,}{sh:>8,}")
        print()
    print("`shapes` is the count of distinct locator patterns with digits and long "
          "tokens masked.\nFew shapes over many locators means a regular structure "
          "-- which is what makes a part enumerable.\nIt describes what was TAKEN, "
          "not what EXISTS: it is a hint to look, never a denominator.")
    return buckets


if __name__ == "__main__":
    main()
