"""Pro Football Archives player game logs and playoff logs, ROW-SHAPED.

Ryan's ruling, 2026-09-09, after one decade was measured (see
reports/2026-09-09-one-decade-of-gamelogs.md):

  row-shaped, not per-cell -- per-cell is 8,294,120 claims against an archive of
    7,897,823 and doubles it to restate what it already holds;
  postseason first -- the archive holds NO player postseason statistic at all, and
    7.7 of the 8 points of new material is that;
  then the regular season, for the SCHEDULE -- 2,154 distinct 1970s games with a
    date, an opponent, a score and a result, in an era where every one of the
    archive's 2,888 pfa.game claims is 1920-1959;
  hold the 102 self-disagreements, resolve none, and keep them apart from the 436
    short sums, which are PFA's partial pre-1982 sack logs and not a disagreement;
  one decade, then stop and report.

TWO PARTS, TWO STORES, run and reported separately:

  --part postseason   build/pfa-postseason-1970s.json
                      the POSTSEASON blocks of the game logs (per-game statistics),
                      and the playoff-log pages (per-YEAR playoff totals, jersey
                      number, position, games played, games started). Both are "the
                      postseason"; they are different pages and different grains and
                      the predicates say which is which.
  --part regular      build/pfa-gamelogs-1970s.json
                      the REGULAR SEASON blocks, the games derived from them, and
                      the disagreements against PFA's own season pages.

THE JOIN IS THE PFA CODE, not a name. A log at gamelogs/a/abra00500.html is the same
man as players/a/abra00500.html, which the archive already cites on 1.16M claims.
2,532 of 2,636 men on the 1970s pages join to exactly one person and none to more
than one. A name join was never attempted and is not a fallback here.

THE CLUB CODE COMES FROM THE TABLE. Every subject's code is resolved through the
archive's own Clubs() before the claim is written; a row whose code the table cannot
place for that year is REFUSED and counted, never invented.

  python3 src/ingest_pfa_logs.py --part postseason            read and report
  python3 src/ingest_pfa_logs.py --part postseason --write    write the store
"""
import os, re, sys, json, glob, sqlite3, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import pfa_gamelog as G
import measure_pfa_gamelogs as M

LOGS = os.path.expanduser("~/Documents/pgm3-sources/pfa-logs")
SRC_ID = "pfa-gamelogs"
STATED = "Pro Football Archives"
ATTRIB = [STATED]
OBSERVED = "fetched-2026-09-08"
DECADE = 1970                                 # overridden by --decade; see main()

# WHY THE DECADE IS AN ARGUMENT AND NOT A CONSTANT ANY MORE. Ryan's standing
# instruction is one decade, measured, then stop -- never ten decades on one decade's
# evidence. Measured 2026-09-10 across all 33,747 pages, and THE 1970s DO NOT HOLD:
#
#   KICKOFF RETURNS.FC is blank on all 8,080 rows of the 1970s and carries a value on
#     7,297 of 8,403 in the 1980s. A rule that read the 1970s as "this column is the
#     era" would silently drop a real 1980s statistic.
#   SCORING.X2 is blank on all but 4 rows of the 1970s -- and carries 4,173 values in
#     the 1960s, because the AFL had the two-point conversion and the NFL did not. The
#     era facts are NOT monotonic: blank, then data, then blank again, then data.
#   SCORING.X2A is blank on every 1980s row and not on every 1970s one.
#   RECEIVING.TAR is blank in every decade to 1989 and starts in the 1990s.
#
# Which is the whole argument for the empty-column rule: a blank is never a zero and
# the blank columns are RECORDED PER ROW rather than inferred from the decade.

SCHEDULE_NOTE = (
    "ASSEMBLED FROM COVERAGE, NOT A SCHEDULE PFA PUBLISHED. This game record is derived "
    "by collapsing the two sides of player game-log rows. A row exists only where a man "
    "recorded something in some section, so a game in which nobody figured in any section "
    "is absent from this set entirely, and the number of games here is not the number of "
    "games played.")
DISAGREE_NOTE = (
    "PFA's own season statistic page and PFA's own game logs differ. The archive holds "
    "both and resolves neither.")


def base_claim(sr, note=None, kind="observed"):
    c = {"source_id": SRC_ID, "source_record": sr, "stated_by": STATED,
         "attribution": list(ATTRIB), "kind": kind, "observed_at": OBSERVED}
    if note: c["note"] = note
    return c


def split_stats(row, cols):
    """-> (printed, blank). A BLANK IS NOT A ZERO: a column PFA prints empty is named
    in `columns_printed_blank` and never given a value."""
    printed, blank = {}, []
    for c in cols:
        v = (row.get(c) or "").strip()
        (blank.append(c) if v == "" else printed.__setitem__(c, v))
    return printed, blank


def load_rows(kind):
    return M.rows_for(DECADE, kind)


def joiner(conn):
    return M.person_of_code(conn)


def run(part, write):
    import paths
    from clubs import Clubs
    C = Clubs()
    conn = sqlite3.connect("file:" + paths.READ_MODEL + "?mode=ro", uri=True)
    code2p = joiner(conn)
    n = collections.Counter()
    claims, refused, srs = [], [], {}

    _res = {}

    def res(s, y, lg):
        # Cached: one answer per (string, year, league). The refusal census the resolver
        # keeps is never read by this ingest, so caching changes no output.
        if not s: return None
        k = (s, y, lg)
        if k not in _res: _res[k] = C.resolve(s, y, lg, source="season_key")
        return _res[k]

    def club_of(r):
        """-> (club hit, None) or (None, why). THE FULL NAME AND ITS LINK, HELD AGAINST EACH
        OTHER AT THE CLUB (Ryan, 2026-09-11). Codes are not compared: PFA links the 2020
        Raiders as `oak` beside the name "Las Vegas Raiders", and both are the one Raiders
        club. Both resolve to one club -> that club. Only one resolves -> that one. They
        name DIFFERENT clubs -> refused, counted.
        THE LEAGUE IS ON THE ROW AND MUST BE USED. This passed None and refused 682 1980s
        rows saying the table "cannot place HOU in 1984" -- it can: the Houston Oilers are
        NFL 1970-1996. A join must use every field on the row; this is the third time."""
        by_link = res(r["club_code"], r["year"], r.get("league"))
        by_name = res(r.get("club_printed"), r["year"], r.get("league"))
        if by_link and by_name and by_link[0] != by_name[0]:
            return None, (f"the full name `{r['club_printed']}` and its link `{r['club_code']}` name two "
                          f"different clubs in {r['year']}")
        hit = by_link or by_name
        if not hit:
            return None, (f"the club table cannot place `{r['club_printed']}` [{r['club_code']}] in "
                          f"{r['year']} for league `{r.get('league')}`")
        return hit, None

    # THE STRING PFA PRINTS FOR A CLUB, learned from the rows where its short label is RIGHT.
    # A row whose label named the opponent needs its own club's string, and the table's code
    # is the wrong one to reach for: PFA labels the Bears CHIB and the table holds CHI, so a
    # Bear's right-labelled rows sat on CHIB and his wrong-labelled rows on CHI -- one man,
    # one club-season, two season keys. Measured on the first pass: 652 of them, 388 men,
    # where the stores before the fix held 12. (club, year, league) -> Counter(label).
    labels = collections.defaultdict(collections.Counter)

    def learn(rows):
        for r in rows:
            short = r.get("club_short_label")
            if not short: continue
            hit, _ = club_of(r)
            if hit and (res(short, r["year"], r.get("league")) or (None,))[0] == hit[0]:
                labels[(hit[0], r["year"], r.get("league"))][short] += 1

    def place(r):
        """(person, club string) or (None, why)."""
        pids = code2p.get(r["code"]) or []
        if len(pids) != 1:
            return None, ("no person holds this PFA player page" if not pids
                          else "the PFA code joins to more than one person")
        hit, why = club_of(r)
        if not hit: return None, why
        # THE SUBJECT'S CLUB STRING MOVES ONLY WHERE IT WAS WRONG. Where the short label names
        # the same club, it stays the token it always was, so no correct season key is
        # renamed; where it named another club, the string PFA prints for the right club
        # that year takes its place.
        short = r.get("club_short_label")
        by_short = res(short, r["year"], r.get("league"))
        if by_short and by_short[0] == hit[0]:
            return pids[0], short
        seen = labels.get((hit[0], r["year"], r.get("league")))
        if seen:
            n["club_string_from_the_label_pfa_prints_for_it"] += 1
            return pids[0], sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        # NEVER THE LINK'S CODE. PFA's link code is not a club's code (`oak` for the 2020
        # Raiders, `stl` for the 1934 Gunners, who hold SLG); written as a key it names
        # nothing. Only where PFA never prints the club's label rightly that decade is the
        # table's code used, counted; a club with no code that year is refused, counted.
        code = C.code_for(hit[0], r["year"])
        if not code:
            return None, f"the club table holds `{hit[0]}` with no code in {r['year']}"
        n["club_string_from_the_table_code"] += 1
        return pids[0], code

    def record(locator):
        """EVERY source_record this ingest writes goes through here, so the store's own
        table can never fall behind its claims. (Named `record`, not `reg`: `reg` is
        the regular-season row list four lines below and shadowed the function.) It did: the first published run named
        `gamelogs/derived/<game id>` on 1,932 game claims and `gamelogs/against-the-
        season-page` on 102 disagreements, and registered NEITHER -- RS-G3's standing red
        rose from 414 to 2,448 and I published it. Gate L6 now holds the property on the
        store, so it fails before a build rather than after one."""
        sr = f"{SRC_ID}#{locator}"
        srs[sr] = {"source_id": SRC_ID, "locator": locator}
        return sr

    def sr_for(kind, code):
        return record(f"{kind}/{code[0]}/{code}.html")

    # THE PHASE VOCABULARY IS CLOSED, and a row outside it is COUNTED, not filed as
    # whichever side of a `!=` it happens to fall on. `phase != "REGULAR SEASON"` would
    # have swept a preseason row -- or the 5 rows in the whole corpus that carry no phase
    # at all -- into the postseason store without a word.
    PHASES = ("REGULAR SEASON", "PLAYOFFS")

    def of_phase(rows, want):
        keep, other = [], collections.Counter()
        for r in rows:
            if r["phase"] == want: keep.append(r)
            elif r["phase"] not in PHASES: other[str(r["phase"])] += 1
        return keep, other

    if part == "postseason":
        gl, glmeta = load_rows("gamelogs")
        pl, plmeta = load_rows("playoffs")
        learn(gl); learn(pl)                 # every row, both page kinds, before any is placed
        # A ROW REFUSED BY THE READER IS COUNTED IN THE STORE, not only in the reader's
        # metadata, which nothing kept: that is how 2,570 rows nearly vanished in silence.
        n["rows_team_link_unusable_club_from_the_full_name"] += glmeta.get("rows_team_link_unusable_club_from_the_full_name", 0)
        post, off_vocab = of_phase(gl, "PLAYOFFS")
        n["rows_with_a_phase_outside_the_vocabulary"] = sum(off_vocab.values())
        for r in post:
            pid, club = place(r)
            if pid is None:
                refused.append({"page": r["code"], "year": r["year"], "why": club}); n["refused_game"] += 1; continue
            printed, blank = split_stats(r["stats"], list(r["stats"]))
            v = {"date_as_printed": r["date"], "section": r["section"], "phase": r["phase"],
                 "home_away_neutral": r["ha"], "opponent_as_printed": r["opp"],
                 "score_as_printed": r["score"], "result_as_printed": r["result"],
                 "club_as_printed": r["club_printed"], "statistics": printed,
                 "columns_printed_blank": blank,
                 # WHAT PFA'S SHORT LABEL PRINTED, held as printed. On ~22% of playoff
                 # rows it names the opponent; the club above comes from the row's link.
                 "club_short_label_as_printed": r.get("club_short_label"),
                 "boxscore": (r["boxscore"] or "").lstrip("/") or None}
            claims.append({**base_claim(sr_for("gamelogs", r["code"])),
                           "id": f"post:{r['code']}:{r['date']}:{r['section']}",
                           "subject": ["stint", pid, club, f"{r['league']}-{r['year']}"],
                           "predicate": "pfa.postseason_game", "value": v})
            n["postseason_game"] += 1

        n["rows_team_link_unusable_club_from_the_full_name"] += plmeta.get("rows_team_link_unusable_club_from_the_full_name", 0)
        for r in pl:
            pid, club = place(r)
            if pid is None:
                refused.append({"page": r["code"], "year": r["year"], "why": club}); n["refused_playoff"] += 1; continue
            printed, blank = split_stats(r["stats"], list(r["stats"]))
            if r["section"] == "SNAP COUNTS":
                # HOW MUCH A MAN ACTUALLY PLAYED, as against whether he started. Ryan's
                # ruling, 2026-09-10: its own predicate, because this is PARTICIPATION and
                # not performance -- nothing was gained, attempted or conceded -- and under
                # an existing statistic predicate a consumer summing "defensive statistics"
                # would be adding plays to tackles. ONE CLAIM, not four: the four figures
                # describe one thing and splitting them makes a reader reassemble what the
                # source printed together.
                def _i(x):
                    try: return int(str(x).strip())
                    except (TypeError, ValueError): return None
                o, d_, s_ = (_i(printed.get(k)) for k in ("OFF", "DEF", "ST"))
                tot = _i(printed.get("TOTAL"))
                v = {"offense": o, "defense": d_, "special_teams": s_,
                     "club_as_printed": r["club_printed"],
                     "columns_printed_blank": blank,
                     "club_page": (r["boxscore"] or "").lstrip("/") or None,
                     "_the_printed_total_is_NOT_stored":
                         "PFA prints TOTAL and it equals OFF+DEF+ST, so it is arithmetic "
                         "and not evidence. It was seen and deliberately not kept -- the "
                         "source did not lack it. Same reasoning as the age-to-birth-year "
                         "refusal.",
                     "_postseason_only":
                         "PFA publishes snap counts for the POSTSEASON and not for the "
                         "regular season: the section appears on playoff-log pages and on "
                         "no gamelog page, checked across 3,000 of them. This is not a "
                         "season total and there is no regular-season figure to compare.",
                     "_the_grain_is_a_PLAYOFF_YEAR_not_a_game":
                         "one row per man per club per postseason, unlike the per-game "
                         "rows everywhere else in this store."}
                if None in (o, d_, s_) or tot is None or o + d_ + s_ != tot:
                    # THE ARITHMETIC IS CHECKED, NOT ASSUMED. Where it does not hold the
                    # printed total is EVIDENCE again and is kept, because dropping it
                    # would be discarding the very case that makes it worth having.
                    v["total_as_printed"] = printed.get("TOTAL")
                    v["_kept_because_it_does_not_add_up"] = True
                    n["snap_total_does_not_add_up"] += 1
                claims.append({**base_claim(sr_for("playoffs", r["code"])),
                               "id": f"snaps:{r['code']}:{r['year']}",
                               "subject": ["stint", pid, club, f"{r['league']}-{r['year']}"],
                               "predicate": "pfa.playoff_snap_counts", "value": v})
                n["playoff_snap_counts"] += 1
                continue
            v = {"table": r["section"] or "PLAYOFF SEASONS", "club_as_printed": r["club_printed"],
                 "columns": printed, "columns_printed_blank": blank,
                 "club_page": (r["boxscore"] or "").lstrip("/") or None}
            claims.append({**base_claim(sr_for("playoffs", r["code"])),
                           "id": f"play:{r['code']}:{r['year']}:{r['section'] or 'SEASONS'}",
                           "subject": ["stint", pid, club, f"{r['league']}-{r['year']}"],
                           "predicate": "pfa.playoff_season", "value": v})
            n["playoff_season"] += 1
        meta = {"gamelogs": glmeta, "playoffs": plmeta,
                "postseason_rows_in_the_decade": len(post), "playoff_rows_in_the_decade": len(pl),
                "phase_vocabulary": list(PHASES), "rows_outside_it": dict(off_vocab)}
        out_name = f"pfa-postseason-{DECADE}s"
        what = (f"The {DECADE}s POSTSEASON: the POSTSEASON blocks of PFA's player game logs, one "
                "claim per row, and PFA's playoff-log pages, one claim per playoff year. The "
                "archive holds no other player postseason statistic of any kind.")

    else:
        gl, glmeta = load_rows("gamelogs")
        learn(gl)                            # every row, before any is placed
        n["rows_team_link_unusable_club_from_the_full_name"] += glmeta.get("rows_team_link_unusable_club_from_the_full_name", 0)
        reg, off_vocab = of_phase(gl, "REGULAR SEASON")
        n["rows_with_a_phase_outside_the_vocabulary"] = sum(off_vocab.values())
        games = {}
        for r in reg:
            pid, club = place(r)
            if pid is None:
                refused.append({"page": r["code"], "year": r["year"], "why": club}); n["refused"] += 1; continue
            # THE PLACED CLUB IS WHAT EVERYTHING DOWNSTREAM KEYS ON -- the game's sides and the
            # season sums below -- never `club_code`, which is now PFA's link code. Keying
            # the sides on it labelled 51 Raiders games `OAK` and dropped 4 held conflicts.
            r["_club"] = club
            printed, blank = split_stats(r["stats"], list(r["stats"]))
            box = (r["boxscore"] or "").lstrip("/") or None
            v = {"date_as_printed": r["date"], "section": r["section"],
                 "home_away_neutral": r["ha"], "opponent_as_printed": r["opp"],
                 "score_as_printed": r["score"], "result_as_printed": r["result"],
                 "club_as_printed": r["club_printed"], "statistics": printed,
                 "columns_printed_blank": blank, "boxscore": box,
                 "club_short_label_as_printed": r.get("club_short_label")}
            claims.append({**base_claim(sr_for("gamelogs", r["code"])),
                           "id": f"gl:{r['code']}:{r['date']}:{r['section']}",
                           "subject": ["stint", pid, club, f"{r['league']}-{r['year']}"],
                           "predicate": "pfa.game_log", "value": v})
            n["game_log"] += 1
            if box and r["date"]:
                m = re.search(r"/(\d{4})([a-z]+)(\d+)\.html$", "/" + box)
                if not m:
                    n["boxscore_locator_unparsed"] += 1; continue
                gid = f"{m.group(1)}{m.group(2)}{m.group(3)}"
                g = games.setdefault(gid, {"pfa_game_id": gid, "league": r["league"],
                                           "year": int(m.group(1)), "number": int(m.group(3)),
                                           "date_as_printed": r["date"], "clubs": {},
                                           "boxscore": box, "pages": set()})
                g["clubs"].setdefault(club, {"home_away_neutral": r["ha"],
                                                       "opponent_as_printed": r["opp"],
                                                       "score_as_printed": r["score"],
                                                       "result_as_printed": r["result"]})
                g["pages"].add(r["code"])
        for gid, g in sorted(games.items()):
            pages = sorted(g.pop("pages"))
            g["_sides_held"] = len(g["clubs"])
            g["_men_whose_rows_attest_it"] = len(pages)
            claims.append({**base_claim(record(f"gamelogs/derived/{gid}"), note=SCHEDULE_NOTE,
                                        kind="source_derived"),
                           "id": f"game:{gid}",
                           "subject": ["game", g["league"], g["year"], g["number"]],
                           "predicate": "pfa.game_as_logged", "value": g})
            n["game_as_logged"] += 1
            n["game_with_one_side_only"] += int(g["_sides_held"] == 1)

        # ---- the disagreements, held and not resolved; the short sums kept apart
        agg = collections.defaultdict(lambda: {"n": 0, "sum": 0.0, "max": None, "blank": 0})
        for r in reg:
            pids = code2p.get(r["code"]) or []
            if len(pids) != 1: continue
            if not r.get("_club"):
                # A row the ingest refused to place is not summed under a code it could not
                # place; before this it was summed under whatever the cell printed.
                n["season_sum_rows_skipped_unplaced"] += 1; continue
            mp = M.MAP.get(r["section"]) or {}
            for col, raw in r["stats"].items():
                if col not in mp: continue
                v = M.number(raw)
                s = agg[(pids[0], r["year"], r["_club"], r["league"], r["section"], col)]
                s["n"] += 1
                if v is None: s["blank"] += 1; continue
                s["sum"] += v
                s["max"] = v if s["max"] is None else max(s["max"], v)
        held = M.held_season(conn, DECADE)
        short = []
        for (pid, y, code, league, sec, col), s in agg.items():
            pred, how = M.MAP[sec][col]
            if pred is None or how == M.DERIVED or s["blank"]: continue
            # THE LEAGUE, AGAIN, AND THIS WAS THE THIRD COPY IN THIS FILE. place() had it,
            # the gate's codes() had it, and so did this.
            hit = C.resolve(code, y, league, source="season_key")
            got = held.get((pid, y, hit[0] if hit else code, pred))
            if got is None: continue
            hv = M.number(got)
            want = s["max"] if how == M.MAX else s["sum"]
            if hv is None or want is None or abs(hv - want) < 1e-6: continue
            if want < hv:
                short.append({"person": pid, "year": y, "club_as_printed": code,
                              "statistic": pred, "the_season_page_prints": got,
                              "the_game_logs_sum_to": want, "games_logged": s["n"]})
                n["short_sum_not_written_as_a_claim"] += 1
                continue
            claims.append({**base_claim(record("gamelogs/against-the-season-page"),
                                        note=DISAGREE_NOTE),
                           "id": f"conflict:{pid}:{y}:{code}:{pred}",
                           # THE LEAGUE WAS HARDCODED `NFL` ON EVERY DISAGREEMENT CLAIM.
                           # Every AAFC, AFL, WFL and USFL disagreement was filed under a
                           # competition it was not played in -- 1,654 claims across every
                           # decade asserted NFL whatever the row said. The gate caught only
                           # the ones where the code does not ALSO name an NFL club that
                           # year; the rest would have passed and still been wrong.
                           "subject": ["stint", pid, code, f"{league}-{y}"],
                           "predicate": "pfa.game_logs_exceed_the_season_page",
                           "value": {"statistic": pred, "the_season_page_prints": got,
                                     "the_game_logs_sum_to": want, "games_logged": s["n"],
                                     "the_season_page_is_held_under": "pro-football-archives"}})
            n["disagreement"] += 1
        meta = {"gamelogs": glmeta, "regular_season_rows_in_the_decade": len(reg),
                "phase_vocabulary": list(PHASES), "rows_outside_it": dict(off_vocab),
                "short_sums": short[:40], "short_sums_total": len(short)}
        out_name = f"pfa-gamelogs-{DECADE}s"
        what = (f"The {DECADE}s REGULAR SEASON game logs, one claim per row; the games derived "
                "from them, each carrying the coverage limit on the claim; and the places "
                "where PFA's game logs exceed PFA's own season page.")

    out = {"_what": what,
           "_the_schedule_is_assembled_from_coverage": SCHEDULE_NOTE,
           "source": {"source_id": SRC_ID, "name": "Pro Football Archives — player game logs",
                      "stated_by": STATED, "attribution": list(ATTRIB), "acquisition": "fetched"},
           "source_records": srs, "claims": claims,
           "counts": dict(n), "refused": refused[:60], "refused_total": len(refused),
           "meta": meta}
    print(f"PFA LOGS -> {out_name}   ({'WRITE' if write else 'dry run'})")
    for k, v in sorted(n.items()): print(f"  {k:38s} {v:>9,}")
    print(f"  {'claims':38s} {len(claims):>9,}")
    print(f"  {'refused (counted, never invented)':38s} {len(refused):>9,}")
    if refused:
        why = collections.Counter(x["why"] for x in refused)
        for w, c in why.most_common(5): print(f"      {c:>6,}  {w}")
    if write:
        p = os.path.join(BASE, "build", out_name + ".json")
        json.dump(out, open(p, "w"), indent=1)
        print(f"  -> {p}  ({os.path.getsize(p):,} bytes)")
    else:
        print("  (dry run; pass --write)")
    return out


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=("postseason", "regular"))
    ap.add_argument("--decade", type=int, default=1970,
                    help="the decade to read; one at a time, by ruling")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.decade % 10 or not (1920 <= a.decade <= 2020):
        ap.error("--decade is a decade: 1920, 1930 ... 2020")
    DECADE = a.decade
    run(a.part, a.write)
