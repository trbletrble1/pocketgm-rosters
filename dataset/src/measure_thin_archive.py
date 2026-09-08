"""Where the archive is thin: the cohort instrument, pointed at the eras that are not done.

Tonight established that 1934-46 is finished -- 4,553 men, 1.81% of the four programme
facts missing, every one of them weight. This runs the same measurement, with no reader
involved, over the eras nobody has checked: everything before 1934, and every season of
the leagues outside the NFL's main run.

FOUR MEASUREMENTS, KEPT APART:
  EMPTY      club-seasons the club table holds with no roster member at all, and
             separately those with members but no coach or staff.
  THIN       club-seasons where men are held but the facts are not, ranked by the
             COUNT of missing facts, not the share -- the top of that list is where
             one document does the most work.
  NAMELESS   people holding a surname and nothing else, and where they cluster.
  NO ROSTER  club-seasons whose men carry no stint detail at all, so no source ever
             gave a roster row and the members were derived from appearances.

  python3 src/measure_thin_archive.py
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from measure_programme_gain import holds, _real

OUT = os.path.join(BASE, "build-reports", "thin-archive.json")
FIELDS = ("age", "weight", "college", "position")
# every season of these; plus everything before 1934 in any league
WHOLE_LEAGUE = {"AAFC", "AFL", "AAF", "WFL", "USFL", "USFL2", "XFL", "UFL", "UFL2"}
CUTOFF = 1934


def in_scope(league, year):
    if league in WHOLE_LEAGUE: return True
    if not year.isdigit(): return False
    return int(year) < CUTOFF


def main():
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    CLUBS = IDX.pop("_clubs", {}) or {}
    TAB = json.load(open(os.path.join(BASE, "build", "clubs.json")))

    # ---- everyone, by club-season
    cs = collections.defaultdict(lambda: {"men": [], "with_stint": 0})
    coached = set()
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        for k, v in (p.get("seasons") or {}).items():
            pt = k.split("|")
            if len(pt) < 3: continue
            if pt[0] == "COACHES":
                coached.add((pt[2], pt[1].lstrip("y"))); continue
            st = v.get("stint") or {}
            cs[k]["men"].append((pid, p))
            if any(st.get(x) is not None for x in ("jersey", "games_played",
                                                   "games_started", "position")):
                cs[k]["with_stint"] += 1

    # ---- the club table's own club-seasons, so an EMPTY one can be seen at all
    table = {}
    for c in TAB["clubs"]:
        for seg in c["segments"]:
            for y in range(seg["first"], seg["last"] + 1):
                if y in (seg.get("dark_years") or []): continue
                lgs = [l["league"] for l in seg["leagues"]
                       if l["first"] <= y <= l["last"]] or [""]
                nm = next((n["name"] for n in c["names"]
                           if n["first"] <= y <= n["last"]), c["names"][0]["name"])
                for lg in lgs:
                    table[(lg, str(y), seg["code"])] = {"club": c["id"], "name": nm,
                                                        "origin": c["origin"],
                                                        # EMPTY BY RULING IS NOT A GAP. A club
                                                        # whose own record says why it holds no
                                                        # men -- the 1926 Los Angeles Tigers,
                                                        # whose roster is keyed to the GAME and
                                                        # not to a club-season -- is not a
                                                        # hunting target and must not be listed
                                                        # as one. Read from the club, never a
                                                        # hard-coded exception list.
                                                        "declared_empty":
                                                            (c.get("_document") or {}).get("_holds_no_men")}

    scoped = {k: v for k, v in table.items() if in_scope(k[0], k[1])}

    empty, no_coach, thin, no_roster, empty_by_ruling = [], [], [], [], []
    for (lg, yr, code), meta in sorted(scoped.items(), key=lambda x: (x[0][1], x[0][0], x[0][2])):
        key = f"{lg}|{yr}|{code}"
        rec = cs.get(key)
        if rec is None and lg == "":
            # THE CLUB TABLE RECORDS NO LEAGUE; THE INDEX CANNOT. A club-season asserting
            # no league is written `('', year, code)` in the table and `IND|year|code` in
            # the index, because the index key has no way to hold an empty league. The two
            # do not join on their own, and Frankford's 1922-23 seasons were reported as
            # EMPTY while holding 45 men. Match on (year, code) when the league is absent.
            alt = [k for k in cs if k.split("|")[1:] == [yr, code]]
            if alt: rec = cs[alt[0]]
        n = len(rec["men"]) if rec else 0
        has_coach = (code, yr) in coached
        base = {"league": lg, "year": yr, "code": code,
                "name": meta["name"], "men": n, "coach_or_staff": has_coach}
        if n == 0:
            if meta.get("declared_empty"):
                empty_by_ruling.append({**base, "why": meta["declared_empty"]})
            else:
                empty.append(base)
            continue
        if not has_coach:
            no_coach.append(base)
        miss = collections.Counter()
        for pid, p in rec["men"]:
            h = holds(p, yr)
            for f in FIELDS:
                if not h[f]: miss[f] += 1
        tot = sum(miss.values())
        if tot:
            thin.append({**base, "missing_facts": tot, "of_possible": 4 * n,
                         "share": round(tot / (4 * n), 3), "by_field": dict(miss)})
        if rec["with_stint"] == 0:
            no_roster.append({**base, "why": "no man on this club-season carries a jersey, "
                                             "a games figure or a position, so no source "
                                             "ever gave a roster row"})

    # ---- people holding a surname and nothing else
    nameless = []
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        nm = (p.get("name") or "").strip()
        if not nm or " " in nm: continue          # a surname alone has no space in it
        per = p.get("person") or {}
        # A VALUE, not a key. Backnor of the 1921 Tonawanda Kardex carries birth_date,
        # college AND hometown predicates, and all three hold the literal "None".
        facts = [k for k, v in per.items() if not k.startswith("roster_membership")
                 and k not in ("has_photograph", "pfa.transaction") and _real(v)]
        if facts: continue
        keys = [k for k in (p.get("seasons") or {}) if not k.startswith("COACHES")]
        if not keys: continue
        nameless.append({"person": pid, "name": nm, "club_seasons": keys,
                         "predicates_held_but_none_valued":
                             sorted(k for k, v in per.items()
                                    if not k.startswith("roster_membership") and not _real(v))})
    clust = collections.Counter(k for x in nameless for k in x["club_seasons"])

    res = {"_note": "MEASUREMENT ONLY. No store written. Same cohort instrument as the "
                    "1934-46 check, pointed at the eras that are not finished.",
           "_scope": f"every club-season before {CUTOFF}, plus every season of "
                     + ", ".join(sorted(WHOLE_LEAGUE)),
           "club_seasons_in_scope": len(scoped),
           "empty_club_seasons": empty,
           "empty_by_ruling_not_a_gap": empty_by_ruling,
           "club_seasons_without_a_coach": no_coach,
           "thin_club_seasons": sorted(thin, key=lambda x: -x["missing_facts"]),
           "club_seasons_with_no_roster_source": no_roster,
           "people_with_a_surname_and_nothing_else": nameless,
           "nameless_clusters": clust.most_common(40),
           "counts": {"scoped": len(scoped), "empty": len(empty),
                      "empty_by_ruling": len(empty_by_ruling),
                      "no_coach": len(no_coach), "thin": len(thin),
                      "no_roster_source": len(no_roster),
                      "nameless": len(nameless),
                      "missing_facts_total": sum(x["missing_facts"] for x in thin),
                      "by_field": dict(collections.Counter(
                          {f: sum(x["by_field"].get(f, 0) for x in thin) for f in FIELDS}))}}
    json.dump(res, open(OUT, "w"), indent=1)
    c = res["counts"]
    print(f"club-seasons in scope            {c['scoped']:>6}")
    print(f"  EMPTY (no roster member)       {c['empty']:>6}")
    print(f"  with men but NO coach/staff    {c['no_coach']:>6}")
    print(f"  THIN (men held, facts not)     {c['thin']:>6}   missing facts {c['missing_facts_total']:,}")
    print(f"     by field: {c['by_field']}")
    print(f"  NO ROSTER SOURCE               {c['no_roster_source']:>6}")
    print(f"  people with a surname only     {c['nameless']:>6}")
    print("\ntop 12 thin club-seasons by COUNT of missing facts:")
    for x in res["thin_club_seasons"][:12]:
        print(f"   {x['missing_facts']:>4} missing  {x['men']:>3} men  {x['league']}|{x['year']}|{x['code']:<8} "
              f"{x['name'][:30]:30s} {x['by_field']}")
    print("\n->", OUT)
    return res


if __name__ == "__main__":
    main()
