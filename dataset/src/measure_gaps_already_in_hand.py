"""For every gap on the hunting list, can a source the archive ALREADY HOLDS fill it?

WHY THIS EXISTS. On 8 September the archive read PFA's team-season pages for the
first time and found they cover almost the whole hunting list. A list that sends Ryan
to eBay for a fact sitting on his own disk is worse than no list. So before a gap is
published as a gap, it is checked against the documents already acquired.

THE CHECK IS PER FACT, NOT PER PAGE. A PFA page existing for a club-season proves
nothing: its own cell may be blank. This opens the page, finds the man, and asks
whether that column carries a value.

  python3 src/measure_gaps_already_in_hand.py
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import measure_pfa_team_seasons as M
from measure_programme_gain import holds
import clubs as ac

THIN = os.path.join(BASE, "build-reports", "thin-archive.json")
OUT = os.path.join(BASE, "build-reports", "gaps-already-in-hand.json")
# the hunting list's fields, and the PFA roster column that would answer each
COLUMN = {"college": "college", "weight": "wt", "age": "age", "position": "pos"}


def norm(s):
    s = re.sub(r"[^a-z ]", " ", str(s or "").lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(s.split())


def main():
    thin = json.load(open(THIN))
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    C = ac.Clubs()
    pb = M.cache_files()

    # every PFA team-season page, keyed by the club-season it resolves to
    page_of = {}
    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        y, club, lg, rows, _ = got
        r = C.resolve(club, y, lg, source="hunt")
        if r:
            page_of[(r[0], y)] = rows

    # THE SAME DEFINITION THE LIST USES. `holds()` reads the PERSON INDEX, not the read
    # model, and the two are different artefacts -- the index is lossy. Checking
    # fillability against the model while the list counts against the index compares
    # two different populations: it reported that not one of the 847 missing colleges
    # could be filled, and that every man on the 1920 Hammond Pros already had one.
    by_cs = collections.defaultdict(list)
    for pid, p in IDX.items():
        if not isinstance(p, dict) or pid == "_clubs":
            continue
        for key in (p.get("seasons") or {}):
            parts = key.split("|", 2)
            if len(parts) == 3:
                by_cs[key].append((pid, p))

    n = collections.Counter()
    by_field = collections.defaultdict(collections.Counter)
    still = collections.Counter()
    for row in thin["thin_club_seasons"]:
        yr = str(row["year"])
        key = f"{row['league']}|{yr}|{row['code']}"
        y = int(yr[-4:])
        r = (C.resolve(row["code"], y, row["league"] or None, source="hunt")
             or C.resolve(row["name"], y, row["league"] or None, source="hunt"))
        rows = page_of.get((r[0], y)) if r else None
        prow = {norm(x.get("player")): x for x in (rows or [])}
        for pid, p in by_cs.get(key, []):
            h = holds(p, yr)
            nm = norm(p.get("name") or "")
            hit = prow.get(nm)
            for field in ("age", "weight", "college", "position"):
                if h.get(field):
                    continue
                col = COLUMN[field]
                v = (hit.get(col) or "").strip() if hit else ""
                fillable = bool(v) and v.lower() != "none"
                n["fillable from a PFA page already on disk" if fillable
                  else "not fillable from anything already held"] += 1
                by_field[field]["fillable" if fillable else "not"] += 1
                if not fillable:
                    still[(key, row["name"], "no PFA page" if not rows else
                           ("not on the page" if not hit else "PFA's cell is empty or `none`"))] += 1

    tot = sum(n.values())
    print(f"THE HUNTING LIST'S {tot:,} MISSING FACTS, checked against what is on disk")
    print("   (counted with the LIST'S OWN definition -- holds(), over the person index)\n")
    for k, v in n.most_common():
        print(f"   {v:>6,}  {100.0*v/tot:>5.1f}%  {k}")
    print("\n   by field:")
    print(f"      {'':10s}{'fillable':>10s}{'not':>8s}")
    for f, c in sorted(by_field.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"      {f:10s}{c['fillable']:>10,}{c['not']:>8,}")
    why = collections.Counter()
    for (cs, nmc, reason), v in still.items():
        why[reason] += v
    print("\n   why a gap is NOT fillable:")
    for w, v in why.most_common():
        print(f"      {v:>6,}  {w}")
    agg = collections.Counter()
    for (cs, nmc, reason), v in still.items():
        agg[(cs, nmc)] += v
    print(f"\n   club-seasons with anything left after PFA: {len(agg):,}")
    for (cs, nmc), v in agg.most_common(10):
        print(f"      {v:>4}  {cs:26s} {nmc}")
    json.dump({"counts": dict(n), "by_field": {k: dict(v) for k, v in by_field.items()},
               "why_not_fillable": dict(why),
               "still_missing_by_club_season":
                   [{"club_season": a, "name": b, "left": v} for (a, b), v in agg.most_common()]},
              open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


def _unused():
    thin = json.load(open(THIN))
    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()
    pb = M.cache_files()

    # every PFA team-season page, keyed by the club-season it resolves to
    page_of = {}
    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        y, club, lg, rows, _ = got
        r = C.resolve(club, y, lg, source="hunt")
        if r:
            page_of[(r[0], y)] = rows

    # what the archive holds per person, for the four fields
    held = collections.defaultdict(set)
    for p, fam in conn.execute(
            "select person, family from claim where person is not null and family in "
            "('college','weight','position') group by person, family"):
        held[p].add(fam)
    for p, in conn.execute("select distinct person from claim where predicate like '%age%' "
                           "and person is not null"):
        held[p].add("age")
    names = collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        if norm(nm): names[p].add(norm(nm))
    roster = collections.defaultdict(set)
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim where scope='stint' and "
            "club_id is not null and person is not null and league not in "
            "('COACHES','ASSISTANTS','SALARIES','COACH') group by club_id, year, person"):
        roster[(cid, y)].add(p)

    n = collections.Counter()
    by_field = collections.defaultdict(collections.Counter)
    still = []
    for row in thin["thin_club_seasons"]:
        y = int(str(row["year"])[-4:])
        r = (C.resolve(row["code"], y, row["league"] or None, source="hunt")
             or C.resolve(row["name"], y, row["league"] or None, source="hunt"))
        key = (r[0], y) if r else None
        rows = page_of.get(key) if key else None
        people = roster.get(key, set()) if key else set()
        # index the page's rows by normalised name
        prow = {}
        for pr in (rows or []):
            prow[norm(pr.get("player"))] = pr
        for field, cnt in (row.get("by_field") or {}).items():
            col = COLUMN.get(field)
            filled = 0
            if rows and col:
                # which men on this club-season lack the field, and does the page carry it?
                lacking = [p for p in people if field not in held.get(p, set())]
                for p in lacking:
                    hit = None
                    for nm in names.get(p, ()):
                        if nm in prow:
                            hit = prow[nm]; break
                    if hit and (hit.get(col) or "").strip() and \
                            (hit.get(col) or "").strip().lower() != "none":
                        filled += 1
            filled = min(filled, cnt)
            n["fillable from a PFA page already on disk"] += filled
            n["not fillable from anything already held"] += cnt - filled
            by_field[field]["fillable"] += filled
            by_field[field]["not"] += cnt - filled
            if cnt - filled:
                still.append({"club_season": f"{row['league']}|{row['year']}|{row['code']}",
                              "name": row["name"], "field": field,
                              "still_missing": cnt - filled,
                              "pfa_page": bool(rows)})
    tot = sum(n.values())
    print(f"THE HUNTING LIST'S {tot:,} MISSING FACTS, checked against what is on disk\n")
    for k, v in n.most_common():
        print(f"   {v:>6,}  {100.0*v/tot:>5.1f}%  {k}")
    print("\n   by field:")
    print(f"      {'':10s}{'fillable':>10s}{'not':>8s}")
    for f, c in sorted(by_field.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"      {f:10s}{c['fillable']:>10,}{c['not']:>8,}")
    agg = collections.Counter()
    for s in still:
        agg[(s["club_season"], s["name"])] += s["still_missing"]
    print(f"\n   club-seasons with anything left after PFA: {len(agg):,}")
    for (cs, nm), v in agg.most_common(12):
        print(f"      {v:>4}  {cs:26s} {nm}")
    json.dump({"counts": dict(n), "by_field": {k: dict(v) for k, v in by_field.items()},
               "still_missing": still}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
