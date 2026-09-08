"""Per-player statistics from PFA's team-season pages.

MEASURED FIRST, 2026-09-08: 373,877 rows -- 320,228 restating what the archive holds,
36,868 a statistic it lacks for a man it holds, 16,781 held by nobody. Ryan ruled the
ingest worth doing on the middle number, of which defence and sacks are half.

PFA IS A SECOND SOURCE HERE. Every one of the archive's 1,900,503 `stats-*` claims
carries source_id `statscrew`; none came from PFA. So the restating rows are
CORROBORATION, and the predicate is unprefixed where the two sources mean the same
thing, so their figures land in one family and can agree or disagree.

WHERE THE MEANING IS NOT CERTAIN, THE PREDICATE IS NOT SHARED. A column that has no
unambiguous StatsCrew equivalent keeps its own `pfa.<category>.<COLUMN>` predicate.
Putting PFA's completions into StatsCrew's attempts would be a silent, serious defect,
and the mapping is declared below rather than guessed row by row.

THE LINEAGE CAUTION TRAVELS ON THE CLAIM. StatsCrew and PFA both descend from Neft's
1970s reconstruction of the pre-1933 record, so their agreement before 1933 is an ECHO
and not independent corroboration. Every claim before 1933 carries that in a field a
reader sees, not only in a declaration.

WHAT STAYS OUT: rows whose man cannot be joined (16,781 -- coverage, not statistics; a
statistic needs a man), and pages whose club string the club table refuses (222).
Both are counted and reported.

  python3 src/ingest_pfa_stats.py [--write]
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import measure_pfa_team_seasons as M
import measure_stats_overlap as S
import clubs as ac

OUTDIR = os.path.join(BASE, "build")
REPORT = os.path.join(BASE, "build-reports", "pfa-stats-ingest.json")

# PFA's column -> StatsCrew's, per category. ONLY where the two plainly mean the same
# thing. Everything absent from this map keeps a `pfa.` predicate of its own.
SHARED = {
 "RUSHING": {"ATT": "rushing.No.", "YDS": "rushing.Yds", "AVG": "rushing.Avg.",
             "LG": "rushing.Long", "TD": "rushing.TDs"},
 "RECEIVING": {"REC": "receiving.No.", "YDS": "receiving.Yds", "AVG": "receiving.Avg.",
               "LG": "receiving.Long", "TD": "receiving.TDs"},
 "INTERCEPTIONS": {"INT": "interceptions.No.", "YDS": "interceptions.Yds",
                   "AVG": "interceptions.Avg.", "LG": "interceptions.Long",
                   "TD": "interceptions.TDs"},
 "KICKOFF RETURNS": {"NO": "kick_returns.No.", "YDS": "kick_returns.Yds",
                     "AVG": "kick_returns.Avg.", "LG": "kick_returns.Long",
                     "TD": "kick_returns.TDs"},
 "PUNT RETURNS": {"NO": "punt_returns.No.", "FC": "punt_returns.FC",
                  "YDS": "punt_returns.Yds", "AVG": "punt_returns.Avg.",
                  "LG": "punt_returns.Long", "TD": "punt_returns.TDs"},
 "PUNTING": {"NO": "punting.No.", "YDS": "punting.Yds", "AVG": "punting.Avg.",
             "LG": "punting.Long"},
 "PASSING": {"ATT": "passing.Att", "COM": "passing.Comp", "PCT": "passing.Comp %",
             "YDS": "passing.Yds", "LG": "passing.Long", "TD": "passing.TDs",
             "TD%": "passing.TD %", "INT": "passing.Ints", "INT%": "passing.Int %",
             "TS": "passing.Sacked", "YL": "passing.Yds Lost",
             "Y/ATT": "passing.Yds/Att", "RTG": "passing.Rating"},
 "SACKS": {"NO": "sacks.No.", "YDS": "sacks.Yds"},
 "SCORING": {"PTS": "total_scoring.Points", "FG": "total_scoring.FG",
             "SAF": "total_scoring.Saf", "X1": "total_scoring.X/C",
             "X2": "total_scoring.2Pt"},
 "FIELD GOALS": {"MADE": "kicking.FGM", "ATT": "kicking.FGA", "PCT": "kicking.FG %",
                 "LG": "kicking.Long"},
 # TKL IS NOT StatsCrew's `Tackle` AND WAS DEMOTED, 2026-09-08. StatsCrew's Tackle is
 # its own Def + ST; PFA's TKL is its own DT + STT. Where both are present the
 # SPECIAL-TEAMS halves match exactly (13 = 13) and the defensive halves do not
 # (4 against 43), so the two aggregates count different things. Mapped, it produced
 # 25,986 "differences of fact" -- four fifths of all of them -- from a definition, not
 # from football. It now keeps its own `pfa.` predicate.
 "DEFENSE": {"PD": "defense_and_fumbles.PD",
             "TFL": "defense_and_fumbles.TFL", "TFLY": "defense_and_fumbles.TFLY",
             "FF": "defense_and_fumbles.FF", "QH": "defense_and_fumbles.QBH",
             "BL": "defense_and_fumbles.K Blk"},
 "FUMBLES": {"NO": "defense_and_fumbles.Fum", "REC": "defense_and_fumbles.FRec",
             "YDS": "defense_and_fumbles.FYds", "TD": "defense_and_fumbles.FTD"},
}
ECHO = ("PFA and StatsCrew both descend from David Neft's 1970s reconstruction of the "
        "pre-1933 record from newspapers. Where they agree on a figure before 1933 that "
        "is an ECHO, not independent corroboration.")


def same_figure(a, b):
    """Compare two printed figures WITHOUT rewriting either.

    The archive's own StatsCrew values carry a literal `&nbsp;` -- `'10&nbsp;'` --
    which made every `Long` column disagree 100% of the time. PFA marks a longest play
    that scored with a trailing `t`: `68t` is 68 yards. Neither is a difference about
    football, and both would have been published as one."""
    def clean(x):
        x = str(x).replace("&nbsp;", " ").replace("\xa0", " ").strip()
        return re.sub(r"t$", "", x)
    return clean(a) == clean(b)


def norm(s):
    s = re.sub(r"[^a-z ]", " ", str(s or "").lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(s.split())


def learn_layouts(pb):
    """Per category, the header of each LENGTH, learned from tables whose rows already
    match their header.

    WHAT THE PAGES ACTUALLY DO. PFA renders a data row under a FULLER layout than the
    header it prints: a 1920 SCORING table prints nine column labels over rows of
    twelve values, because the era had no two- or three-point conversions to label. The
    cells are not spacers and dropping them is not the rule -- THE ROW'S LENGTH SAYS
    WHICH LAYOUT IT IS. A 13-cell scoring row is the 13-cell scoring header:
    TD X1 X1A PCT X2 X2A DX FG FGA PCT SAF PTS, and Sid Nichols's PTS is 9 -- which is
    what PFA's own page says, and what the short header made read as 1. StatsCrew holds
    6 for him, so he is now a real disagreement, held: PFA's 9 is its own TD and X1
    columns added up (one touchdown and three conversions) and StatsCrew's 6 is not.
    That is a difference about football and the archive keeps both.

    Tested the way the rejected repair was tested: re-reading the misaligned rows this
    way agrees with StatsCrew on 98.4% of 42,179 shared figures, against 62.8% for
    dropping empty cells and ~99% for rows that never needed it."""
    seen = collections.defaultdict(collections.Counter)
    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        t = open(pb[f], errors="replace").read()
        if "<h1" not in t:
            continue
        for tb in re.findall(r"(?is)<table.*?</table>", t):
            cc = [[M.text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
                  for tr in re.findall(r"(?is)<tr.*?</tr>", tb)]
            if not cc or not cc[0]:
                continue
            cat = cc[0][0].strip().upper()
            if cat not in S.CATEGORY:
                continue
            body = [r for r in cc[1:] if r and r[0] and r[0] not in S.TOTALS]
            if body and all(len(r) == len(cc[0]) for r in body):
                seen[cat][tuple(cc[0])] += len(body)
    out = {}
    for cat, c in seen.items():
        for hdr, k in c.items():
            L = len(hdr)
            if L not in out.get(cat, {}) or k > out[cat][L][1]:
                out.setdefault(cat, {})[L] = (list(hdr), k)
    return {cat: {L: v[0] for L, v in d.items()} for cat, d in out.items()}


def main():
    write = "--write" in sys.argv
    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()

    byname, names_of = collections.defaultdict(set), collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        k = norm(nm)
        if k: byname[k].add(p); names_of[p].add(k)
    roster = collections.defaultdict(set)
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim where scope='stint' and "
            "club_id is not null and person is not null and league not in "
            "('COACHES','ASSISTANTS','SALARIES','COACH') group by club_id, year, person"):
        roster[(cid, y)].add(p)
    # THE COMPARISON KEYS ON THE CLUB-SEASON. Keying on person+year alone compared a
    # two-club man's figures as a set and manufactured disagreements; 5% of a sample
    # were that artefact.
    held = {}
    for p, y, cid, fam, v in conn.execute(
            "select person, year, club_id, family, value_text from claim "
            "where store like 'stats-%' and person is not null"):
        held.setdefault((p, y, cid, str(fam)), set()).add(str(v).strip())

    n = collections.Counter()
    per_decade = collections.defaultdict(list)
    srs_by_decade = collections.defaultdict(dict)
    disagreements = []
    pb = M.cache_files()
    LAYOUT = learn_layouts(pb)
    cid_counter = 0

    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        year, club, league, _r, _ = got
        res = C.resolve(club, year, league, source="pfa-stats")
        if not res:
            n["pages whose club the table refuses -- NO CLAIMS WRITTEN"] += 1
            continue
        club_id = res[0]
        # THE SUBJECT IS A STINT, NOT A PERSON. StatsCrew's statistic claims are
        # `["stint", person, code, "LEAGUE-YEAR"]`, and that is how the model derives a
        # claim's year, league and club_id. Writing them person-scoped left every one
        # with year None and club_id None -- present in the model and attached to no
        # season, so unable to sit beside the figures they corroborate. The code comes
        # from the club table and is never constructed here.
        code = C.code_for(club_id, year)
        if not code:
            n["pages whose club the table gives no code that year -- NO CLAIMS"] += 1
            continue
        here = roster.get((club_id, year), set())
        dec = year // 10 * 10
        text = open(pb[f], errors="replace").read()
        sr = f"pro-football-archives#{f}"
        srs_by_decade[dec][sr] = {"source_id": "pro-football-archives", "locator": f}
        for tb in re.findall(r"(?is)<table.*?</table>", text):
            cells = [[M.text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
                     for tr in re.findall(r"(?is)<tr.*?</tr>", tb)]
            if not cells or not cells[0]:
                continue
            cat = cells[0][0].strip().upper()
            if cat not in S.CATEGORY:
                continue
            hdr = cells[0]
            for row in cells[1:]:
                if not row or not row[0] or row[0] in S.TOTALS:
                    continue
                n["statistic rows"] += 1
                # COLUMNS ARE MAPPED BY POSITION, SO THE ROW MUST BE THE HEADER'S
                # LENGTH. PFA's SCORING and DEFENSE tables insert spacer cells the
                # header does not declare -- Sid Nichols's 9 points read as 1, and
                # every total_scoring figure on those rows was wrong. Dropping the
                # empty cells to force a fit was TESTED against StatsCrew and gave 63%
                # agreement where the aligned rows give 99%, so it is not the rule and
                # is not used. These rows are counted and NOT read.
                use = hdr
                if len(row) != len(hdr):
                    use = LAYOUT.get(cat, {}).get(len(row))
                    if not use:
                        n["ROWS WHOSE LENGTH MATCHES NO LEARNED LAYOUT -- not read"] += 1
                        n[f"  no layout: {cat}"] += 1
                        continue
                    n["rows re-read under the layout their LENGTH names"] += 1
                name = norm(row[0])
                hits = byname.get(name, set())
                on_it = hits & here
                if len(on_it) == 1:
                    pid, how = next(iter(on_it)), "exact name, on that club-season"
                elif len(hits) == 1 and not on_it:
                    pid, how = next(iter(hits)), "exact name, unique in the archive"
                elif len(on_it) > 1:
                    pid = None
                else:
                    w = name.split()
                    loose = [p for p in here
                             if any(x.split() and x.split()[-1] == w[-1]
                                    and x.split()[0][:1] == w[0][:1]
                                    for x in names_of.get(p, ()))] if len(w) >= 2 else []
                    pid = loose[0] if len(loose) == 1 else None
                    how = "surname and forename initial, on that club-season"
                if not pid:
                    n["ROWS HELD BY NOBODY -- left out, a coverage finding"] += 1
                    continue
                n["rows joined"] += 1
                rec = f"{sr}#{cat}#{row[0]}"
                srs_by_decade[dec][rec] = {"source_id": "pro-football-archives",
                                           "locator": f"{f}#{cat}#{row[0]}"}
                for i, col in enumerate(use[1:], 1):
                    if i >= len(row):
                        break
                    v = row[i].strip()
                    if not v:
                        continue
                    col = col.strip().upper()
                    shared = SHARED.get(cat, {}).get(col)
                    pred = shared or f"pfa.{S.CATEGORY[cat]}.{col}"
                    n["cells written"] += 1
                    n["cells on a predicate shared with StatsCrew" if shared
                      else "cells on a pfa-only predicate"] += 1
                    if shared:
                        theirs = held.get((pid, year, club_id, shared))
                        if theirs:
                            if any(same_figure(v, t) for t in theirs):
                                n["  agrees with StatsCrew"] += 1
                            else:
                                n["  DISAGREES with StatsCrew -- both stand"] += 1
                                if len(disagreements) < 100000:
                                    disagreements.append(
                                        {"person": pid, "year": year, "club_id": club_id,
                                         "predicate": shared, "pfa": v,
                                         "statscrew": sorted(theirs),
                                         "shared_lineage_before_1933": year < 1933})
                        else:
                            n["  a figure StatsCrew does not hold"] += 1
                    cid_counter += 1
                    cl = {"id": "c_%07d" % cid_counter, "predicate": pred, "value": v,
                          "subject": ["stint", pid, code, f"{league}-{year}"],
                          "kind": "observed",
                          "source_id": "pro-football-archives", "source_record": rec,
                          "stated_by": "Pro Football Archives", "attribution": [],
                          "observed_at": year, "_join": how,
                          "_club_season": {"club_id": club_id, "year": year,
                                           "league": league}}
                    if year < 1933:
                        cl["_agreement_with_statscrew_is_an_echo"] = ECHO
                    per_decade[dec].append(cl)

    print(f"   {'statistic rows':52s} {n['statistic rows']:>9,}")
    for k in ("rows joined", "ROWS HELD BY NOBODY -- left out, a coverage finding",
              "pages whose club the table refuses -- NO CLAIMS WRITTEN",
              "rows re-read under the layout their LENGTH names",
              "ROWS WHOSE LENGTH MATCHES NO LEARNED LAYOUT -- not read",
              "cells written", "cells on a predicate shared with StatsCrew",
              "cells on a pfa-only predicate", "  agrees with StatsCrew",
              "  DISAGREES with StatsCrew -- both stand",
              "  a figure StatsCrew does not hold"):
        print(f"   {k:52s} {n[k]:>9,}")
    pre = sum(1 for d in disagreements if d["shared_lineage_before_1933"])
    print(f"   {'  of the disagreements, before 1933 (shared lineage)':52s} {pre:>9,}")

    if write:
        for dec, claims in sorted(per_decade.items()):
            store = os.path.join(OUTDIR, f"pfa-stats-{dec}s.json")
            json.dump({"source": {"source_id": "pro-football-archives",
                                  "acquisition": "in the original PFA sweep and the "
                                                 "2026-09-08 team-season fetch",
                                  "stated_by": "Pro Football Archives"},
                       "_what": f"per-player statistics from PFA team-season pages, {dec}s",
                       "_second_source": "every stats-* claim in the archive is StatsCrew's; "
                                         "these are a second compilation, not the same one",
                       "_shared_lineage_before_1933": ECHO,
                       "_unmapped_columns": "a column with no unambiguous StatsCrew "
                                            "equivalent keeps a pfa.<category>.<COLUMN> "
                                            "predicate rather than being merged into one "
                                            "that means something else",
                       "source_records": srs_by_decade[dec], "claims": claims,
                       "counts": {"claims": len(claims)}}, open(store, "w"))
            print(f"   wrote {os.path.basename(store):24s} {len(claims):>9,} claims")
        json.dump({"counts": dict(n), "disagreements": disagreements,
                   "disagreements_total": len(disagreements)}, open(REPORT, "w"), indent=1)
        print(f"   report {REPORT}")
    else:
        print("   (dry run; --write to store)")


if __name__ == "__main__":
    main()
