"""What PFA's per-player statistics on the team-season pages would add.

MEASUREMENT ONLY. Nothing ingested, nothing written to a store, nothing fetched.

THE QUESTION IS THE OVERLAP, and it is not established until it is measured. This
morning cost 2,930 pages of effort for 937 men on the assumption that a
different-looking page must hold different facts. It did not: PFA's team-season
roster tables and PFA's player pages were the same author restated.

BUT THE LINEAGE IS DIFFERENT HERE. Every one of the archive's 1,900,503 `stats-*`
claims carries source_id `statscrew`. PFA is therefore a SECOND source for these
statistics, not the same one twice -- with the standing caution that StatsCrew and PFA
both descend from Neft's 1970s reconstruction for the pre-1933 record, so agreement
there is an echo rather than corroboration.

THREE NUMBERS, KEPT APART, per category and per era:
  not held at all      the man cannot be matched to a person holding that club-season
  man held, stat not   he is held on that club-season and the archive has no claim in
                       that statistic category for him that year
  restates             the archive already holds that category for him that year

THE JOIN IS THE ONE RULED ON. Exact name; an ambiguous name settled by the
club-season; surname and forename initial ONLY where he holds that club-season.

  python3 src/measure_stats_overlap.py
"""
import os, re, sys, json, sqlite3, collections

_SP = {}
def STAFF_PREDICATE_SQL():
    # STAFF IS A PREDICATE, NOT A LEAGUE. `league not in ('COACHES',...)` let 41,662
    # of 54,908 staff claims through as players once the coaching subjects carried real
    # leagues, so this pool held 30,364 STAFF-ONLY (club, year, person) pairs -- coaches
    # offered as candidates for a player's award, statistic line or roster gap.
    # declarations/coaching-seasons.json is the list.
    if not _SP:
        import os as _o, json as _j
        _d = _j.load(open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "..",
                                       "declarations", "coaching-seasons.json")))
        _p = sorted(_d["staff_predicates"]["predicates"])
        _SP["sql"] = "predicate not in (" + ",".join("'" + x + "'" for x in _p) + ")"
    return _SP["sql"]


HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import measure_pfa_team_seasons as M
import clubs as ac

OUT = os.path.join(BASE, "build-reports", "stats-overlap.json")

# PFA's section banner -> the archive's statistic family prefix
CATEGORY = {
    "SCORING": "total_scoring", "FIELD GOALS": "kicking",
    "RUSHING": "rushing", "PASSING": "passing", "RECEIVING": "receiving",
    "INTERCEPTIONS": "interceptions", "PUNTING": "punting",
    "PUNT RETURNS": "punt_returns", "KICKOFF RETURNS": "kick_returns",
    "FUMBLES": "defense_and_fumbles", "DEFENSE": "defense_and_fumbles",
    "SACKS": "sacks",
}
TOTALS = ("Team Totals", "Opponents Totals", "Totals")


def norm(s):
    s = re.sub(r"[^a-z ]", " ", str(s or "").lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(s.split())


def main():
    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()

    byname = collections.defaultdict(set)
    names_of = collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        k = norm(nm)
        if k:
            byname[k].add(p); names_of[p].add(k)
    roster = collections.defaultdict(set)
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim where scope='stint' and "
            "club_id is not null and person is not null and " + STAFF_PREDICATE_SQL() +
            " group by club_id, year, person"):
        roster[(cid, y)].add(p)
    # (person, year, category) the archive already holds a statistic for
    holds = set()
    for p, y, fam in conn.execute(
            "select person, year, family from claim where store like 'stats-%' "
            "and person is not null and family is not null group by person, year, family"):
        holds.add((p, y, str(fam).split(".")[0]))
    # AND THE VALUES, for the three columns that map without a judgement:
    # yards rushing, receiving and passing. `restates` above says the archive holds
    # THAT CATEGORY for that man and year -- not that it holds the same numbers, which
    # is a different question and the one that decides whether PFA is worth more as a
    # corroborator than as an adder.
    YARDS = {"rushing": "rushing.Yds", "receiving": "receiving.Yds",
             "passing": "passing.Yds"}
    yards = {}
    for p, y, fam, v in conn.execute(
            "select person, year, family, value_text from claim where store like 'stats-%' "
            "and family in ('rushing.Yds','receiving.Yds','passing.Yds') "
            "and person is not null"):
        yards.setdefault((p, y, str(fam).split(".")[0]), set()).add(str(v).strip())

    pb = M.cache_files()
    n = collections.Counter()
    by_cat = collections.defaultdict(collections.Counter)
    by_era = collections.defaultdict(collections.Counter)
    unmatched_reason = collections.Counter()
    notheld_league = collections.Counter()
    notheld_empty = collections.Counter()
    disagreements = []

    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        year, club, league, _rows, _ = got
        res = C.resolve(club, year, league, source="pfa-stats")
        if not res:
            n["pages whose club the table refuses -- SKIPPED"] += 1
            continue
        cid = res[0]
        here = roster.get((cid, year), set())
        text = open(pb[f], errors="replace").read()
        for tb in re.findall(r"(?is)<table.*?</table>", text):
            cells = [[M.text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
                     for tr in re.findall(r"(?is)<tr.*?</tr>", tb)]
            if not cells or not cells[0]:
                continue
            cat = CATEGORY.get(cells[0][0].strip().upper())
            if not cat:
                continue
            for c in cells[1:]:
                if not c or not c[0] or c[0] in TOTALS:
                    continue
                n["statistic rows"] += 1
                by_cat[cells[0][0].strip().upper()]["rows"] += 1
                era = year // 10 * 10
                by_era[era]["rows"] += 1
                name = norm(c[0])
                hits = byname.get(name, set())
                on_it = hits & here
                how = None
                if len(on_it) == 1:
                    pid, how = next(iter(on_it)), "exact name, on that club-season"
                elif len(hits) == 1 and not on_it:
                    pid, how = next(iter(hits)), "exact name, unique, but no season held there"
                elif len(on_it) > 1:
                    pid, how = None, "several of that exact name on that club-season"
                else:
                    w = name.split()
                    loose = [p for p in here
                             if any(x.split() and x.split()[-1] == w[-1]
                                    and x.split()[0][:1] == w[0][:1]
                                    for x in names_of.get(p, ()))] if len(w) >= 2 else []
                    if len(loose) == 1:
                        pid, how = loose[0], "surname and initial, on that club-season"
                    else:
                        pid = None
                        how = ("several by surname and initial on that club-season"
                               if len(loose) > 1 else "no person of that name")
                if not pid:
                    n["NOT HELD AT ALL"] += 1
                    by_cat[cells[0][0].strip().upper()]["not held"] += 1
                    by_era[era]["not held"] += 1
                    unmatched_reason[how] += 1
                    notheld_league[league] += 1
                    notheld_empty["the archive holds NOBODY on that club-season"
                                  if not here else
                                  "the archive holds men on it and not him"] += 1
                    continue
                n[f"joined by {how}"] += 1
                if cat in YARDS:
                    # the banner row IS the header row: ['RUSHING','ATT','YDS',...]
                    hdr = [x.lower() for x in cells[0]]
                    yi = hdr.index("yds") if "yds" in hdr else None
                    mine = c[yi].strip() if yi is not None and yi < len(c) else None
                    theirs = yards.get((pid, year, cat))
                    if mine and mine.isdigit() and theirs:
                        if mine in theirs:
                            n[f"  {cat} yards AGREE"] += 1
                        else:
                            n[f"  {cat} yards DISAGREE"] += 1
                            if len(disagreements) < 400:
                                disagreements.append(
                                    {"person": pid, "year": year, "category": cat,
                                     "pfa": mine, "archive": sorted(theirs),
                                     "club": club})
                if (pid, year, cat) in holds:
                    n["RESTATES what is already held"] += 1
                    by_cat[cells[0][0].strip().upper()]["restates"] += 1
                    by_era[era]["restates"] += 1
                else:
                    n["MAN AND SEASON HELD, THIS STATISTIC NOT"] += 1
                    by_cat[cells[0][0].strip().upper()]["stat missing"] += 1
                    by_era[era]["stat missing"] += 1

    print("THE THREE NUMBERS, KEPT APART")
    for k in ("NOT HELD AT ALL", "MAN AND SEASON HELD, THIS STATISTIC NOT",
              "RESTATES what is already held"):
        print(f"   {k:46s} {n[k]:>8,}")
    print(f"   {'statistic rows in all':46s} {n['statistic rows']:>8,}")

    print("\nBY CATEGORY")
    print(f"   {'':22s}{'rows':>9s}{'not held':>10s}{'stat missing':>14s}{'restates':>10s}")
    for cat, v in sorted(by_cat.items(), key=lambda kv: -kv[1]["rows"]):
        print(f"   {cat:22s}{v['rows']:>9,}{v['not held']:>10,}"
              f"{v['stat missing']:>14,}{v['restates']:>10,}")

    print("\nBY ERA")
    print(f"   {'':8s}{'rows':>9s}{'not held':>10s}{'stat missing':>14s}{'restates':>10s}"
          f"{'restates %':>12s}")
    for era in sorted(by_era):
        v = by_era[era]
        pc = 100.0 * v["restates"] / v["rows"] if v["rows"] else 0
        print(f"   {era}s{v['rows']:>8,}{v['not held']:>10,}{v['stat missing']:>14,}"
              f"{v['restates']:>10,}{pc:>11.1f}%")

    print("\nWHERE BOTH HOLD A YARDS FIGURE, DO THEY AGREE?")
    for cat in ("rushing", "receiving", "passing"):
        a, dsg = n[f"  {cat} yards AGREE"], n[f"  {cat} yards DISAGREE"]
        tot = a + dsg
        print(f"   {cat:12s} agree {a:>7,}   DISAGREE {dsg:>6,}"
              + (f"   ({100.0*dsg/tot:.1f}% of {tot:,} compared)" if tot else ""))
    print("   a category counted as `restates` above means the archive holds THAT "
          "CATEGORY\n   for that man and year -- not that it holds the same numbers.")

    print("\nTHE ROWS HELD BY NOBODY, BY LEAGUE")
    for lg, cnt in notheld_league.most_common(10):
        print(f"   {lg:8s} {cnt:>8,}")
    print("   and by whether the archive has that club-season at all:")
    for k, cnt in notheld_empty.most_common():
        print(f"      {cnt:>8,}  {k}")

    print("\nWHY A ROW COULD NOT BE JOINED")
    for w, cnt in unmatched_reason.most_common():
        print(f"   {cnt:>8,}  {w}")

    json.dump({"totals": dict(n), "by_category": {k: dict(v) for k, v in by_cat.items()},
               "by_era": {k: dict(v) for k, v in by_era.items()},
               "unmatched": dict(unmatched_reason),
               "not_held_by_league": dict(notheld_league),
               "not_held_club_season_state": dict(notheld_empty),
               "yards_disagreements": disagreements}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
