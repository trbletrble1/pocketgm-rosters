"""Which club-seasons did NO SOURCE ever give a roster for?

THIS REPLACES A TEST THAT MEASURED THE WRONG THING. The first version asked whether
any man on a club-season carried `jersey`, `games_played`, `games_started` or
`position` at the TOP LEVEL of the index's stint record. Two store shapes write that
record: StatsCrew-shaped stores write the fields flat, and PFA-shaped stores write
them nested under the predicate that stated them --

    flat        {"jersey": 65, "games_played": 8, "position": {...}}
    predicate   {"pfa.roster_membership": {"jersey": "11", "height": "5-8", ...}}

so the old test scored every predicate-keyed stint as having no roster detail, whatever
it held. 4,123 stints in the index are predicate-keyed. It reported the 1926 AFL New
York Yankees as having no roster, and PFA's roster page gives all 16 of them a jersey,
a height and a weight. What it actually listed was: club-seasons where no man ALSO
appears in a flat-shape store.

THE EVIDENCE IS DECLARED, AND WAS ALL ALONG. ingest_afl1926.py writes
`roster_evidence: roster_page | boxscore_lineup` on every claim, for exactly this
question, and its docstring says so: "A roster-page roster and a boxscore-derived
roster are not the same object." The right test reads that, and for stores that do not
declare it, asks whether the only thing placing a man there is a boxscore.

  python3 src/measure_no_roster_source.py
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
OUT = os.path.join(BASE, "build-reports", "no-roster-source.json")

# stores whose membership is DERIVED from who appeared in a game, not from a roster
BOXSCORE_STORES = {"pfa-boxscore-membership", "pfa-boxscores", "boxscore-membership"}


def main():
    ev = collections.defaultdict(lambda: collections.Counter())   # club-season -> evidence
    stores = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or not isinstance(d.get("claims"), list): continue
        for c in d["claims"]:
            v = c.get("value"); s = c.get("subject")
            key = None
            if isinstance(v, dict) and {"league", "year", "club_code"} <= set(v):
                key = f"{v['league']}|{v['year']}|{v['club_code']}"
            elif isinstance(v, str) and v.count("|") == 2:
                key = v
            elif isinstance(s, list) and len(s) == 4 and s[0] == "stint":
                continue                       # no league in the subject; skipped, not guessed
            if not key: continue
            stores[key].add(st)
            if isinstance(v, dict) and v.get("roster_evidence"):
                ev[key][v["roster_evidence"]] += 1          # the store DECLARED it
            elif st in BOXSCORE_STORES:
                ev[key]["boxscore_lineup"] += 1
            else:
                ev[key]["undeclared"] += 1

    rows = []
    for key, e in ev.items():
        if e.get("roster_page"): continue                   # a source gave a roster: not here
        if e.get("boxscore_lineup") and not e.get("undeclared"):
            rows.append({"club_season": key, "evidence": dict(e),
                         "stores": sorted(stores[key]),
                         "basis": "boxscore_lineup, declared by the store"})
    rows.sort(key=lambda r: r["club_season"])
    und = sum(1 for e in ev.values() if e.get("undeclared") and not e.get("roster_page")
              and not e.get("boxscore_lineup"))
    res = {"_note": "club-seasons no source gave a roster for, read from the evidence the "
                    "ingests declare, not from the shape of the index's stint record.",
           "club_seasons_with_any_membership_evidence": len(ev),
           "no_roster_source": rows,
           "counts": {"boxscore_only": len(rows),
                      "roster_page_somewhere": sum(1 for e in ev.values() if e.get("roster_page")),
                      "evidence_undeclared_only": und}}
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"club-seasons with membership evidence : {len(ev):,}")
    print(f"  a source gave a roster page          : {res['counts']['roster_page_somewhere']:,}")
    print(f"  BOXSCORE-DERIVED ONLY (declared)     : {len(rows)}")
    for r in rows: print(f"      {r['club_season']:22s} {r['evidence']}  {r['stores']}")
    print(f"  evidence undeclared either way       : {und:,}  <- these are NOT a finding, "
          f"only stores that state no roster_evidence")
    print("\n->", OUT)
    return res


if __name__ == "__main__":
    main()
