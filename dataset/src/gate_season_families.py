"""Gate: a season figure contests only a season figure, of the same season. Ryan, 2026-09-12.

The ruling: a family for season weights, and not the career one -- folding Neft's season weight into PFA's career
weight would manufacture disagreements that are not disagreements, the same fabrication as 61" against 6-1.

  F1  THE SEASON WEIGHT FAMILY HOLDS NO CAREER PREDICATE: none of pfa.weight, weight, guide.WEIGHT, and none of
      pfa.roster.weight, which is the career value printed on each roster page (measured: 2.0% season-to-season
      change against Neft's 43.2%).
  F2  EVERY CLAIM IN IT IS SEASON-SCOPED IN THE MODEL, so the year key keeps it apart from anything career-scoped.
  F3  NO CONTESTED ROW IN A SEASON-BEARING FAMILY MIXES SCOPES OR SEASONS: for every contested row in weight_season
      and height with a year, every contributing claim is season-scoped and of that year; for every row without one,
      every contributing claim is person-scoped.
  F4  NO CONTESTED ROW IN THEM COLLAPSES UNDER ITS READING: two values that read alike are one value (gate_readings
      R2's property, checked here on these families in the model this gate is pointed at).

    python3 src/gate_season_families.py [--model PATH]    exit 1 = FAIL
"""
import os, sys, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from readings import READERS

FAM = os.path.join(BASE, "service", "declarations", "predicate-families.json")
CAREER = {"pfa.weight", "weight", "guide.WEIGHT", "pfa.roster.weight"}
SEASON_SCOPES = ("person_season", "stint", "club_season", "league_season")
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def main():
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else paths.READ_MODEL
    if not os.path.exists(model): raise SystemExit(f"MISSING INPUT: {model}")
    fam = json.load(open(FAM))["families"]
    ws = fam.get("weight_season")
    check(bool(ws), "F0 the weight_season family is declared")
    if not ws: print("\nGATE FAILED"); return 1
    check(not (set(ws["predicates"]) & CAREER), f"F1 no career predicate in weight_season ({sorted(set(ws['predicates']) & CAREER)})")
    c = sqlite3.connect(f"file:{model}?mode=ro", uri=True)
    q = ",".join("?" * len(ws["predicates"]))
    bad2 = c.execute(f"select scope, count(*) from claim where predicate in ({q}) and scope not in {SEASON_SCOPES} group by scope",
                     ws["predicates"]).fetchall()
    check(not bad2, f"F2 every weight_season claim is season-scoped in the model ({bad2})")
    bad3, bad4, n = [], [], 0
    for family, reader in (("weight_season", "weight_season"), ("height", "height")):
        for person, year in c.execute("select person, year from contested where family=?", (family,)):
            n += 1
            rows = c.execute("select scope, year, value from claim where person=? and family=? and value is not null",
                             (person, family)).fetchall()
            if year:
                mine = [r for r in rows if str(r[1]) == str(year) and r[0] in SEASON_SCOPES]
                if not mine: bad3.append((family, person, year, "no season claim of that year"))
            else:
                mine = [r for r in rows if r[0] not in SEASON_SCOPES]
            vals = set()
            for _, _, v in mine:
                try: v = json.loads(v)
                except Exception: pass
                vals.add(READERS[reader](str(v)))
            if len(vals - {None}) < 2 and None not in vals: bad4.append((family, person, year, sorted(map(str, vals))))
    check(not bad3, f"F3 no contested row mixes scopes or seasons ({n} rows checked; {len(bad3)} do: {bad3[:3]})")
    check(not bad4, f"F4 no contested row collapses under its reading ({len(bad4)} do: {bad4[:3]})")
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
