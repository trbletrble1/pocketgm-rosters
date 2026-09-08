"""The club strings on PFA's team-season pages that the club table refuses.

NOTHING IS ADDED. This is a scope report: how many of the refused strings sit in
leagues the minor-league exclusion already rules out, how many sit in leagues the
archive holds, and what admitting or refusing each league would cost in pages and in
men.

A LEAGUE THE ARCHIVE HOLDS is one the club table already places a club in that year.
That is the archive's own answer, not mine -- checked per (league, year), because a
league can be in scope in one season and not another.

CANDIDATES ARE NAMED, NEVER JOINED. Where a refused string looks like a club the
table already holds under another name -- the Newark Bears and Demons were one club
with two names -- it is listed as a candidate with its evidence. Deciding it is a
club-table ruling and is not made here.

  python3 src/measure_refused_clubs.py
"""
import os, re, sys, json, sqlite3, collections, difflib

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import measure_pfa_team_seasons as M
import clubs as ac

OUT = os.path.join(BASE, "build-reports", "refused-clubs.json")


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).split())


def main():
    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()
    pb = M.cache_files()

    # leagues the archive holds, per year and overall, from its own claims
    held_league_year = set()
    held_league = collections.Counter()
    for lg, y, n in conn.execute(
            "select league, year, count(distinct person) from claim where scope='stint' "
            "and league is not null group by league, year"):
        held_league_year.add((str(lg).upper(), y)); held_league[str(lg).upper()] += n

    # every club name the table holds, for the look-alike search
    names = collections.defaultdict(set)
    for name, cid, first, last in conn.execute(
            "select name, club_id, first, last from club_name"):
        names[norm(name)].add((cid, first, last))
    all_names = sorted(names)

    refused = []
    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        year, club, league, rows, _ = got
        if C.resolve(club, year, league, source="pfa-team-season"):
            continue
        n = norm(club)
        # a club the table may already hold under another name -- CANDIDATES only
        # THREE STRENGTHS, kept apart. `Michigan Arrows` against `Michigan Panthers`
        # is a shared city and nothing else; reporting it beside `San Antonio
        # Brahamas` against `San Antonio Brahmas` would bury the one real finding in
        # forty guesses.
        cand = []
        if n in names:                       # the SAME name, held for other years
            for cid, first, last in names[n]:
                cand.append({"strength": "same name, different years",
                             "name": n, "club_id": cid, "first": first, "last": last,
                             "active_that_year": bool(first <= year <= last)})
        if not cand:
            for m in difflib.get_close_matches(n, all_names, n=3, cutoff=0.86):
                # a near-identical string: one or two characters, i.e. a misprint
                if m.split()[:-1] != n.split()[:-1]:
                    continue                 # differ before the last word: not a misprint
                for cid, first, last in names[m]:
                    cand.append({"strength": "near-identical, a misprint away",
                                 "name": m, "club_id": cid, "first": first, "last": last,
                                 "active_that_year": bool(first <= year <= last)})
        if not cand:
            # AN ALTERNATIVE NAME IS NOT A MISPRINT. `Birmingham Bolts` and
            # `Birmingham Thunderbolts` are one club under two printed names -- the
            # Newark Bears and Demons shape -- and no edit-distance threshold finds
            # it, because the strings genuinely differ. The test that does: same city
            # word, and one nickname CONTAINS the other.
            city, nick = " ".join(n.split()[:-1]), n.split()[-1]
            for m in all_names:
                mw = m.split()
                if len(mw) < 2 or " ".join(mw[:-1]) != city:
                    continue
                a, b = mw[-1], nick
                if a == b or not (a.endswith(b) or b.endswith(a)):
                    continue
                for cid, first, last in names[m]:
                    cand.append({"strength": "same city, one nickname inside the other",
                                 "name": m, "club_id": cid, "first": first, "last": last,
                                 "active_that_year": bool(first <= year <= last)})
        weak = [] if cand else [
            m for m in difflib.get_close_matches(n, all_names, n=3, cutoff=0.72)]
        refused.append({"page": f, "year": year, "league": league, "club": club,
                        "men_on_the_page": len(rows),
                        "archive_holds_this_league_that_year":
                            (league, year) in held_league_year,
                        "archive_holds_this_league_at_all": league in held_league,
                        "look_alikes": cand, "weak_resemblances": weak})

    by = collections.defaultdict(lambda: {"pages": 0, "men": 0, "years": set(),
                                          "held_that_year": 0, "held_ever": False})
    for r in refused:
        b = by[r["league"]]
        b["pages"] += 1; b["men"] += r["men_on_the_page"]; b["years"].add(r["year"])
        b["held_that_year"] += 1 if r["archive_holds_this_league_that_year"] else 0
        b["held_ever"] = b["held_ever"] or r["archive_holds_this_league_at_all"]

    rows_out = sorted(by.items(), key=lambda kv: -kv[1]["men"])
    print(f"{len(refused)} club strings the table refuses, in {len(by)} leagues\n")
    hdr = f"{'league':8s}{'pages':>7s}{'men':>8s}{'years':>16s}  archive holds this league?"
    print(hdr); print("-" * (len(hdr) + 8))
    tot_in = tot_out = 0
    for lg, b in rows_out:
        ys = sorted(b["years"])
        span = f"{ys[0]}-{ys[-1]}" if len(ys) > 1 else str(ys[0])
        if b["held_ever"]:
            verdict = (f"YES -- {held_league[lg]:,} men held"
                       + (f", {b['held_that_year']}/{b['pages']} of these years"
                          if b["held_that_year"] else ", but NOT in these years"))
            tot_in += b["men"]
        else:
            verdict = "no -- the archive holds no club-season in it"
            tot_out += b["men"]
        print(f"{lg:8s}{b['pages']:>7,}{b['men']:>8,}{span:>16s}  {verdict}")
    print("-" * (len(hdr) + 8))
    print(f"{'':8s}{len(refused):>7,}{tot_in + tot_out:>8,}")
    print(f"\nmen behind strings in leagues the archive DOES hold : {tot_in:,}")
    print(f"men behind strings in leagues it holds nothing for  : {tot_out:,}")

    look = [r for r in refused if r["look_alikes"]]
    weakn = sum(1 for r in refused if r.get("weak_resemblances"))
    print(f"\nSTRINGS THAT LOOK LIKE A CLUB THE TABLE ALREADY HOLDS ({len(look)})"
          " -- candidates, not joins")
    for r in sorted(look, key=lambda r: -r["men_on_the_page"]):
        print(f"   {r['year']} {r['league']:6s} {r['club'][:34]:34s} "
              f"{r['men_on_the_page']:>3} men")
        for c in r["look_alikes"][:2]:
            when = "ACTIVE that year" if c["active_that_year"] else \
                   f"held {c['first']}-{c['last']}, not that year"
            print(f"        {c['strength']:32s} {c['club_id'][:38]:38s} {when}")
    print(f"\n   a further {weakn} share a city or a word with a club the table holds "
          "and nothing more. Not listed as candidates: `Michigan Arrows` against "
          "`Michigan Panthers` is a city, not a name.")
    json.dump({"refused": refused,
               "by_league": {k: {**v, "years": sorted(v["years"])} for k, v in by.items()},
               "men_in_leagues_held": tot_in, "men_in_leagues_not_held": tot_out},
              open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
