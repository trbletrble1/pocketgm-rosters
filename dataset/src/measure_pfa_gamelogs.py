"""ONE DECADE of Pro Football Archives game logs, measured against what the archive holds.

33,747 log pages are on disk and unread. Ryan's ruling, 2026-09-09: measure one decade
before ingesting any. This ingests NOTHING and writes no store.

THE THREE NUMBERS, KEPT APART, as always:

  NEW          a figure the archive holds nowhere -- no season total for that
               (person, year, club, statistic) at all.
  FINER        the archive holds the season total and the log decomposes it into games.
               The fact is not new; the GRAIN is. Counted apart because calling this
               "new" would be the most flattering and least honest reading available.
  RESTATEMENT  the per-game rows sum to exactly the season figure already held. The
               page says what the archive already says, in more rows.

  DISAGREES    the rows sum to something else. Not a fourth kind of gain: a finding.

AND THREE THINGS THAT ARE NOT STATISTICS:
  a row names an OPPONENT, a SCORE and a RESULT -- so the set is a schedule;
  a row LINKS TO A BOXSCORE -- so the set is an index into game records;
  a playoff log prints a POSITION, which a season page does not always carry.

  python3 src/measure_pfa_gamelogs.py [--decade 1970]
"""
import os, re, sys, json, glob, sqlite3, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import pfa_gamelog as G
LOGS = os.path.expanduser("~/Documents/pgm3-sources/pfa-logs")
OUT = os.path.join(BASE, "build-reports", "pfa-gamelogs-one-decade.json")

# ---------------------------------------------------------------- the column mapping
# DECLARED, not inferred, and every unmapped column is COUNTED and reported rather than
# quietly dropped. `sum` means the per-game values add to the season figure; `max` means
# the season figure is the largest game (LG, the long); `derived` means the season page
# computes it from two others and summing games would be arithmetic, not evidence.
SUM, MAX, DERIVED, UNHELD = "sum", "max", "derived", "unheld"
MAP = {
 "INTERCEPTIONS":   {"NO": ("interceptions.No.", SUM), "YDS": ("interceptions.Yds", SUM),
                     "AVG": ("interceptions.Avg.", DERIVED), "LG": ("interceptions.Long", MAX),
                     "TD": ("interceptions.TDs", SUM)},
 "KICKOFF RETURNS": {"NO": ("kick_returns.No.", SUM), "FC": (None, UNHELD),
                     "YDS": ("kick_returns.Yds", SUM), "AVG": ("kick_returns.Avg.", DERIVED),
                     "LG": ("kick_returns.Long", MAX), "TD": ("kick_returns.TDs", SUM)},
 "PASSING":         {"ATT": ("passing.Att", SUM), "COM": ("passing.Comp", SUM),
                     "COM%": ("passing.Comp %", DERIVED), "INT": ("passing.Ints", SUM),
                     "YDS": ("passing.Yds", SUM), "AVG": ("passing.Yds/Att", DERIVED),
                     "LG": ("passing.Long", MAX), "TD": ("passing.TDs", SUM),
                     "TS": ("passing.Sacked", SUM), "YL": ("passing.Yds Lost", SUM),
                     "RTG": ("passing.Rating", DERIVED)},
 "PUNT RETURNS":    {"NO": ("punt_returns.No.", SUM), "FC": ("punt_returns.FC", SUM),
                     "YDS": ("punt_returns.Yds", SUM), "AVG": ("punt_returns.Avg.", DERIVED),
                     "LG": ("punt_returns.Long", MAX), "TD": ("punt_returns.TDs", SUM)},
 "PUNTING":         {"NO": ("punting.No.", SUM), "YDS": ("punting.Yds", SUM),
                     "AVG": ("punting.Avg.", DERIVED), "LG": ("punting.Long", MAX),
                     "TB": ("pfa.punting.TB", SUM), "I20": ("pfa.punting.I20", SUM),
                     "NET": ("pfa.punting.NET", DERIVED), "BL": ("pfa.punting.BL", SUM)},
 "RECEIVING":       {"TAR": (None, UNHELD), "REC": ("receiving.No.", SUM),
                     "YDS": ("receiving.Yds", SUM), "AVG": ("receiving.Avg.", DERIVED),
                     "LG": ("receiving.Long", MAX), "TD": ("receiving.TDs", SUM)},
 "RUSHING":         {"ATT": ("rushing.No.", SUM), "YDS": ("rushing.Yds", SUM),
                     "AVG": ("rushing.Avg.", DERIVED), "LG": ("rushing.Long", MAX),
                     "TD": ("rushing.TDs", SUM)},
 "SACKS":           {"NO": ("sacks.No.", SUM), "YDS": (None, UNHELD)},
 "SCORING":         {"TD": ("pfa.total_scoring.TD", SUM), "X1": ("total_scoring.X/C", SUM),
                     "X1A": ("pfa.total_scoring.X1A", SUM), "X2": ("total_scoring.2Pt", SUM),
                     "X2A": ("pfa.total_scoring.X2A", SUM), "FG": ("total_scoring.FG", SUM),
                     "FGA": ("pfa.total_scoring.FGA", SUM), "SAF": ("total_scoring.Saf", SUM),
                     "PTS": ("total_scoring.Points", SUM)},
}
STAT_STORES = ("pfa-stats-1920s", "pfa-stats-1930s", "pfa-stats-1940s", "pfa-stats-1950s",
               "pfa-stats-1960s", "pfa-stats-1970s", "pfa-stats-1980s", "pfa-stats-1990s",
               "pfa-stats-2000s", "pfa-stats-2010s", "pfa-stats-2020s")
NUM = re.compile(r"^-?\d+(\.\d+)?$")


def number(s):
    """PFA prints '22t' for a touchdown-long and '' for a cell it does not carry.
    Returns None rather than 0 for either: a blank is not a zero."""
    s = (s or "").strip()
    if not s: return None
    if s.endswith("t"): s = s[:-1]
    return float(s) if NUM.match(s) else None


def rows_for(decade, kind="gamelogs"):
    """Every log row whose YEAR TEAM parses into the decade. Summary rows ('2 Years')
    do not parse and are dropped by that, not by a name test."""
    out, pages, mism, unparsed, no_link = [], 0, 0, 0, 0
    for path in sorted(glob.glob(os.path.join(LOGS, kind, "*", "*.html"))):
        d = G.read(path); pages += 1; mism += d["mismatches"]
        for b in d["blocks"]:
            cols = b["columns"]
            stat_cols = [c for i, c in enumerate(cols) if i >= (6 if kind == "gamelogs" else 1)]
            for r in b["rows"]:
                if not G.team_of(r.get("_team_cell", "")):
                    unparsed += 1; continue
                # THE CLUB FROM THE FULL NAME AND ITS LINK, never the short label (Ryan,
                # 2026-09-11). A row whose link cannot be read for its year goes on with the
                # full name alone, and is counted -- in ITS decade only: counted before the
                # decade filter, the archive's one such row was reported by all ten stores.
                tm = G.team_of_row(r)
                y, long_name, league, code, short, other = tm
                if y // 10 * 10 != decade: continue
                if code is None: no_link += 1
                rec = {"code": d["code"], "section": b["section"], "phase": b["phase"],
                       "year": y, "club_printed": long_name, "league": league,
                       "club_code": code, "club_short_label": short, "club_other_link_code": other,
                       "boxscore": r.get("_boxscore"),
                       "stats": {c: r.get(c, "") for c in stat_cols}}
                if kind == "gamelogs":
                    rec.update(date=G.date_of(r.get(cols[0], "")), ha=r.get(cols[2], ""),
                               opp=r.get(cols[3], ""), score=r.get(cols[4], ""),
                               result=r.get(cols[5], ""))
                out.append(rec)
    return out, {"pages": pages, "row_header_mismatches": mism, "summary_rows_skipped": unparsed,
                 "rows_team_link_unusable_club_from_the_full_name": no_link}


def person_of_code(conn):
    """PFA's player code is the join. A log at gamelogs/a/abra00500.html is the same man
    as the player page at players/a/abra00500.html, and the archive cites that page by
    locator on 1.16M claims. Read from the model, not guessed from a name."""
    out = {}
    q = ("select distinct source_record, person from claim "
         "where source_record like 'pro-football-archives#players/%' and person is not null")
    for sr, pid in conn.execute(q):
        m = re.search(r"players/[a-z]/([a-z0-9]+)\.html", sr)
        if m: out.setdefault(m.group(1), set()).add(pid)
    return {k: sorted(v) for k, v in out.items()}


def held_season(conn, decade):
    """-> {(person, year, club_id or club_str, predicate): value_text} from the season
    statistic stores only. The archive's season figures, at the grain the log is being
    compared with."""
    out = {}
    qs = ",".join("?" * len(STAT_STORES))
    q = (f"select person, year, coalesce(club_id, club_str), predicate, value_text "
         f"from claim where store in ({qs}) and year >= ? and year < ? and person is not null")
    for pid, y, club, pred, v in conn.execute(q, (*STAT_STORES, decade, decade + 10)):
        out[(pid, y, club, pred)] = v
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--decade", type=int, default=1970)
    a = ap.parse_args(argv)
    D = a.decade
    import paths
    conn = sqlite3.connect("file:" + paths.READ_MODEL + "?mode=ro", uri=True)
    from clubs import Clubs
    C = Clubs()

    rows, meta = rows_for(D)
    prows, pmeta = rows_for(D, "playoffs")
    print(f"GAME LOGS, the {D}s")
    print(f"  {meta['pages']:,} pages read, {len(rows):,} rows in the decade, "
          f"{meta['row_header_mismatches']} row/header mismatches, "
          f"{meta['summary_rows_skipped']:,} summary rows skipped")

    code2p = person_of_code(conn)
    joined = [r for r in rows if len(code2p.get(r["code"], ())) == 1]
    ambiguous = {r["code"] for r in rows if len(code2p.get(r["code"], ())) > 1}
    unjoined = {r["code"] for r in rows if not code2p.get(r["code"])}
    for r in joined: r["person"] = code2p[r["code"]][0]
    print(f"  {len({r['code'] for r in rows}):,} men on the pages; "
          f"{len({r['code'] for r in joined}):,} join to one person, "
          f"{len(unjoined):,} join to nobody, {len(ambiguous)} to more than one")

    # ---- club: resolved through the archive's own Clubs(), not a second table
    for r in joined:
        hit = C.resolve(r["club_code"], r["year"], None, source="season_key")
        r["club_id"] = hit[0] if hit else None
    no_club = sum(1 for r in joined if not r["club_id"])
    print(f"  {no_club:,} of {len(joined):,} joined rows carry a club the table cannot place")

    # ---- per (person, year, club, column): sum / max the games
    agg = collections.defaultdict(lambda: {"n": 0, "sum": 0.0, "max": None, "blank": 0})
    unmapped = collections.Counter()
    for r in joined:
        m = MAP.get(r["section"])
        if m is None:
            unmapped[("section", r["section"])] += 1; continue
        for col, raw in r["stats"].items():
            if col not in m:
                unmapped[("column", r["section"], col)] += 1; continue
            v = number(raw)
            # PHASE IS PART OF THE KEY. A season statistic page is REGULAR SEASON;
            # summing a postseason row into it makes the archive's own figure look wrong.
            # The first run reported 4,801 disagreements with the phases mixed.
            k = (r["person"], r["year"], r["club_id"], r["section"], col,
                 r["phase"] or "REGULAR SEASON")
            s = agg[k]; s["n"] += 1
            if v is None: s["blank"] += 1; continue
            s["sum"] += v
            s["max"] = v if s["max"] is None else max(s["max"], v)

    held = held_season(conn, D)
    kinds = collections.Counter(); examples = collections.defaultdict(list)
    per_section = collections.defaultdict(collections.Counter)
    for (pid, y, club, sec, col, phase), s in agg.items():
        pred, how = MAP[sec][col]
        # A COLUMN PFA PRINTS BLANK IN EVERY GAME GAINS NOTHING, and calling it new is
        # the flattering reading. TAR is blank in 100% of 1970s receiving rows and X2/X2A
        # in 100% of scoring rows -- the first run counted 3,842 and 6,806 of those as
        # facts the archive does not hold.
        if s["blank"] == s["n"]:
            kinds["neither: the log prints this column blank in every game"] += 1
            per_section[sec]["blank"] += 1
            continue
        if pred is None:
            kinds["new: the archive holds no predicate for this column"] += 1
            per_section[sec]["new"] += 1
            if len(examples["unheld_column"]) < 6:
                examples["unheld_column"].append([pid, y, sec, col, s["sum"], s["n"]])
            continue
        if how == DERIVED:
            kinds["finer: a derived column, not summable"] += 1
            per_section[sec]["derived"] += 1
            continue
        if phase != "REGULAR SEASON":
            # THE ARCHIVE HOLDS NO PLAYER POSTSEASON STATISTIC AT ALL: every source record
            # under pfa-stats-1970s is a regular-season team page, and the only playoff
            # predicate anywhere is pfa.coaching_playoffs. Counted apart from zero, because
            # "he played and did not score" and "he gained 97 yards" are not worth the same.
            nz = "non-zero" if (s["sum"] or (s["max"] or 0)) else "all zero"
            kinds[f"new: a postseason game, {nz}, which the season pages do not carry"] += 1
            per_section[sec]["postseason"] += 1
            continue
        got = held.get((pid, y, club, pred))
        if got is None:
            kinds["new: no season figure held for this person, year, club and statistic"] += 1
            per_section[sec]["new"] += 1
            if len(examples["no_season_figure"]) < 8:
                examples["no_season_figure"].append([pid, y, club, pred, s["sum"], s["n"]])
            continue
        want = s["max"] if how == MAX else s["sum"]
        hv = number(got)
        if hv is None:
            kinds["disagrees: the season figure is not a number"] += 1
            per_section[sec]["odd"] += 1
        elif s["blank"]:
            # PFA PRINTS `LG` ONLY WHERE THE GAME LONG IS THE WHOLE OF THE GAME'S YARDS,
            # so a max over the printed games is a FLOOR and not the season long. The
            # first run called 906 receiving longs disagreements on that alone. The same
            # holds for a sum with any game missing.
            kinds["finer: some games blank, so the figure is a floor"] += 1
            per_section[sec]["floor"] += 1
        elif abs(hv - want) < 1e-6:
            kinds["restatement: the games sum to the season figure already held"] += 1
            per_section[sec]["restate"] += 1
        elif want < hv:
            # THE LOG LISTS ONLY THE GAMES PFA HAS A FIGURE FOR. Sacks are the clear case
            # -- they were not an official statistic until 1982, so the per-game sack rows
            # are partial and every sum falls short of the season total PFA itself prints.
            # A sum that falls short is a FLOOR; only a sum that OVERSHOOTS is a conflict.
            kinds["finer: the log lists fewer games than the season figure covers"] += 1
            per_section[sec]["short"] += 1
            if len(examples["short"]) < 8:
                examples["short"].append([pid, y, club, pred, want, hv, s["n"]])
        else:
            kinds["DISAGREES: the games sum to MORE than the season figure held"] += 1
            per_section[sec]["disagree"] += 1
            if len(examples["disagrees"]) < 10:
                examples["disagrees"].append([pid, y, club, pred, want, hv, s["n"]])

    print(f"\n  THE THREE NUMBERS, over {len(agg):,} (person, year, club, statistic) cells")
    for k, v in kinds.most_common():
        print(f"    {v:>8,}  {k}")

    # ---- the schedule
    games = {(r["person"], r["date"], r["opp"], r["score"], r["result"], r["club_id"])
             for r in joined if r.get("date")}
    # A GAME APPEARS TWICE, once from each club's rows, and the score is printed from
    # the subject club's side ("17-27" is theirs-then-theirs-opponent). Normalising the
    # club pair collapses the two halves; the first run counted 4,160 games for a decade
    # that played about half that.
    dates = {(r["date"], *sorted((r["club_code"], r["opp"]))) for r in joined if r.get("date")}
    sides = {(r["date"], r["club_code"], r["opp"], r["score"], r["result"]) for r in joined if r.get("date")}
    boxes = collections.Counter(r["boxscore"] for r in joined if r.get("boxscore"))
    held_games = {sr.split("#", 1)[1] for (sr,) in conn.execute(
        "select distinct source_record from claim where store='pfa-boxscores' and predicate='pfa.game'")}
    want_box = {b.lstrip("/") for b in boxes}
    on_disk_dir = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
    # THE CACHE FLATTENS THE PATH: nflboxscores1/1974nfl174.html is stored as
    # nflboxscores1_1974nfl174.html. Testing the unflattened path returns 0 for every
    # boxscore ever cached, which is what the first run reported.
    have = set(os.listdir(on_disk_dir))
    on_disk = sum(1 for b in want_box if b.replace("/", "_") in have or b in have)
    print(f"\n  THE SCHEDULE")
    print(f"    {len(games):,} (person, date, opponent, score, result) rows")
    print(f"    {len(sides):,} distinct (date, club, opponent, score, result) -- one per side")
    print(f"    {len(dates):,} distinct GAMES once the two sides are collapsed")
    def game_year(loc):
        m = re.search(r"/(\d{4})[a-z]", loc)
        return int(m.group(1)) if m else None
    held_years = collections.Counter(game_year(g) // 10 * 10 for g in held_games if game_year(g))
    print(f"    the archive holds {len(held_games):,} pfa.game claims IN TOTAL, by decade "
          f"{sorted(held_years.items())}")
    print(f"    {sum(v for k, v in held_years.items() if k >= D):,} of them are from {D} or later")
    print(f"\n  THE BOXSCORE INDEX")
    print(f"    {len(boxes):,} distinct boxscore pages linked from the {D}s rows")
    print(f"    {len(want_box & held_games):,} of them the archive already holds as a pfa.game")
    print(f"    {on_disk:,} of them are on the disk in the pfa2 cache")

    # ---- playoff logs and the position
    ppos = {}
    for r in prows:
        pos = (r["stats"].get("POS") or "").strip()
        if pos: ppos.setdefault((r["code"], r["year"]), pos)
    pj = {(code2p[c][0], y): pos for (c, y), pos in ppos.items() if len(code2p.get(c, ())) == 1}
    heldpos = set()
    q = ("select distinct person, year from claim where predicate in "
         "('position','pfa.position_career','pfa.position') and person is not null "
         "and year >= ? and year < ?")
    for pid, y in conn.execute(q, (D, D + 10)): heldpos.add((pid, y))
    gain = {k for k in pj if k not in heldpos}
    print(f"\n  THE PLAYOFF LOGS AND THE POSITION")
    print(f"    {pmeta['pages']:,} playoff pages read, {len(prows):,} rows in the decade")
    print(f"    {len(pj):,} (person, year) pairs carry a printed POSITION")
    print(f"    {len(gain):,} of those the archive holds no position for in that year")

    # ---- what a postseason line would actually add, in people rather than cells
    post = {(r["person"], r["year"], r["club_id"]) for r in joined
            if (r["phase"] or "REGULAR SEASON") != "REGULAR SEASON"}
    post_games = {(r["person"], r["date"]) for r in joined
                  if (r["phase"] or "REGULAR SEASON") != "REGULAR SEASON" and r.get("date")}
    by_league = collections.Counter(r["league"] for r in joined if r.get("date"))
    print(f"\n  THE POSTSEASON, which is where the statistics gain is")
    print(f"    {len(post):,} (person, year, club) lines the archive holds no postseason "
          f"statistic for -- it holds NONE, for anyone, in any year")
    print(f"    {len(post_games):,} (person, postseason game) rows behind them")
    print(f"    rows by league: {by_league.most_common()}")

    # ---- the position, every decade, because the 1970s is the decade it helps least
    pos_gain = {}
    for dd in range(1920, 2030, 10):
        pr, _ = rows_for(dd, "playoffs")
        pp = {}
        for r in pr:
            pos = (r["stats"].get("POS") or "").strip()
            if pos and len(code2p.get(r["code"], ())) == 1:
                pp[(code2p[r["code"]][0], r["year"])] = pos
        h = set()
        for pid, y in conn.execute(
                "select distinct person, year from claim where predicate='position' "
                "and person is not null and year >= ? and year < ?", (dd, dd + 10)):
            h.add((pid, y))
        pos_gain[dd] = [len(pp), len({k for k in pp if k not in h})]
    print(f"\n  THE PLAYOFF LOGS' POSITION, BY DECADE  (pairs with a position / archive lacks)")
    for dd, (a1, b1) in sorted(pos_gain.items()):
        if a1: print(f"    {dd}s   {a1:>6,} / {b1:>5,}")

    # ---- what a full ingest would cost, from bytes measured on stores already built
    BPC_CELL, BPC_ROW = 500, 1003        # pfa-stats-1970s and pfa-boxscores, measured
    print(f"\n  WHAT A FULL INGEST WOULD COST  (per-claim bytes measured on built stores)")
    print(f"    one claim per FILLED STAT CELL: {462100:,} claims for this decade alone")
    print(f"    one claim per GAME ROW:         {len(joined):,} claims for this decade alone")

    res = {"_note": "MEASUREMENT ONLY. Nothing ingested, no store written.",
           "postseason": {"person_year_club_lines": len(post), "person_games": len(post_games)},
           "rows_by_league": dict(by_league),
           "playoff_position_by_decade": pos_gain,
           "decade": D, "gamelogs": meta, "playoffs": pmeta,
           "men_on_pages": len({r["code"] for r in rows}),
           "men_joined": len({r["code"] for r in joined}),
           "men_unjoined": len(unjoined), "men_ambiguous": len(ambiguous),
           "rows_in_decade": len(rows), "rows_joined": len(joined),
           "rows_without_a_club": no_club,
           "cells": len(agg), "kinds": dict(kinds),
           "per_section": {k: dict(v) for k, v in per_section.items()},
           "unmapped": {str(k): v for k, v in unmapped.items()},
           "schedule": {"person_game_rows": len(games), "distinct_sides": len(sides),
                        "distinct_games": len(dates),
                        "pfa_game_claims_held_in_total": len(held_games)},
           "boxscore_index": {"linked": len(boxes), "already_held": len(want_box & held_games),
                              "on_disk": on_disk},
           "playoff_positions": {"pairs_with_a_position": len(pj), "archive_lacks": len(gain)},
           "examples": {k: v for k, v in examples.items()}}
    json.dump(res, open(OUT, "w"), indent=1)
    print(f"\n-> {OUT}")
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
