"""Print fifty biographies, stratified by career band, random within band, seeded.

Prose to stdout. The vitals panel is DATA, one record per man, written with
--vitals PATH as JSON: {"n", "id", "name", "vitals"}. It is not formatted here;
layout is a later decision and the two layers stay separate.

Bands and counts are Ryan's. A man is placed in the FIRST band that fits him in the
order below and is not reused, so the fifty are fifty different men.

  python3 src/print_bios.py [--seed 2026] [--map path]
"""
import os, sys, json, random, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from bio_select import Tables, career, select, DEFUNCT_LEAGUES, CLUBS, pfield, families
from bio_write import write

BANDS = [("one or two games total", 8), ("pre-1930", 6), ("war gap spanning 1942-45", 5),
         ("ten or more seasons", 6), ("crossed leagues", 5), ("played then coached", 4),
         ("merged or defunct club", 4), ("thin record", 4),
         ("holds a 1940s guide notes block", 4), ("holds PFA military service", 4)]


def bands_for(T, g):
    p = T.people[g]; c = career(p)
    if not c["years"]: return set()
    out = set()
    if c["games"] is not None and c["games"] <= 2: out.add("one or two games total")
    if c["years"][0] < 1930: out.add("pre-1930")
    if any(set(range(a + 1, b)) & {1942, 1943, 1944, 1945} for a, b in c["gaps"]):
        out.add("war gap spanning 1942-45")
    if len(c["years"]) >= 10: out.add("ten or more seasons")
    if len(families(c["leagues"])) >= 2: out.add("crossed leagues")
    if c["played"] and c["coached"]:
        cy = sorted({s["year"] for s in c["coached"]})
        if cy[-1] >= c["years"][-1]: out.add("played then coached")
    for code, lg in c["clubs"]:
        if lg in DEFUNCT_LEAGUES or (lg == "NFL" and not CLUBS.get(f"{code}|2024")):
            out.add("merged or defunct club"); break
    col = pfield(p, "college")
    if not pfield(p, "birth_date") or not col or col.lower() == "none": out.add("thin record")
    if g in T.notes: out.add("holds a 1940s guide notes block")
    if T.pfa.get(g, {}).get("military_service"): out.add("holds PFA military service")
    return out


def main():
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 2026
    T = Tables()
    pools = collections.defaultdict(list)
    for g in T.people:
        for b in bands_for(T, g): pools[b].append(g)
    random.seed(seed)
    chosen, seen = [], set()
    for b, n in BANDS:
        pool = sorted(x for x in pools[b] if x not in seen)
        pick = random.sample(pool, min(n, len(pool)))
        for g in pick: seen.add(g); chosen.append((b, g))
    out, mapping, panel = [], [], []
    for i, (b, g) in enumerate(chosen, 1):
        F = select(T, g)
        if not F: continue
        out.append(f"{i}. {write(F)}")
        mapping.append({"n": i, "band": b, "id": g, "name": F["name"],
                        "lead": F["lead_kind"], "close": F["close_kind"]})
        panel.append({"n": i, "id": g, "name": F["name"], "vitals": F["vitals"]})
    print("\n\n".join(out))
    if "--vitals" in sys.argv:
        json.dump(panel, open(sys.argv[sys.argv.index("--vitals") + 1], "w"), indent=1, ensure_ascii=False)
    if "--map" in sys.argv:
        json.dump({"seed": seed, "bands": BANDS, "pool_sizes": {b: len(pools[b]) for b, _ in BANDS},
                   "median_seasons": T.median_seasons,
                   "codes_without_salient": T.codes_without_salient, "chosen": mapping},
                  open(sys.argv[sys.argv.index("--map") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
