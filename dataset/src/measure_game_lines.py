"""Census the game-result lines in the media-guide text -- HEADER-ANCHORED.

The first version of this file matched any line that opened with a date token
and contained a score. It reported 1,273,139 lines against report 52's estimate
of ~340,000, and the excess was noise: birthdates (11/16/33), heights and
weights (6-0, 190), and completion splits (Montana, Joe 60-33).

The fix is the lesson gate_statistics_name_their_table already taught for stat
columns and this file had to learn again for game lines: A COLUMN IS NAMED BY
THE HEADER ABOVE IT, NOT GUESSED FROM ITS SHAPE. So a line is only a game line
if it sits in the run beneath a header row that names the columns.

Measurement only. Writes a report, never a claim.
"""
import re, os, json, collections

TEXT = "/Users/ryannecci/Documents/pgm3-sources/nfl-books/text_all"
OUT = "dataset/build-reports/game-lines-census.json"

# A header row must name a date-ish column, an opponent column, and at least one
# of result/score/attendance/venue. Anything looser drifts back into noise.
HDR_DATE = re.compile(r"\b(Date|Day/Date)\b")
HDR_OPP  = re.compile(r"\bOpponent\b")
HDR_BITS = {
    "result":     re.compile(r"\b(W-L-T|W-L_|W-L|W/L|Result)\b"),
    "score":      re.compile(r"\bScore\b"),
    "attendance": re.compile(r"\b(Attendance|Attend\.?|Att\.)"),
    "venue":      re.compile(r"\b(Location|Site|Stadium)\b"),
    "starter":    re.compile(r"\b(Starter|QB|OB)\b"),
    "player_ps":  re.compile(r"\bP/S\b"),
}
# lines that could be a game row inside a run
ROW = re.compile(
    r"^\s*(?:(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\.?,\s*)?"
    r"(?:\d{1,2}/\d{1,2}(?!/\d)|[A-Z][a-z]{2}[a-z]*\.?\s?\d{1,2}|[A-Z$0-9][.,]\s?\d{1,2})\b")
SCORE = re.compile(r"\b\d{1,3}\s*-\s*\d{1,3}\b")
WLT   = re.compile(r"(?:^|\s)([WLT])(?:[\s_.]|$)")
FUSED = re.compile(r"(?:^|\s)([WLT])(\d{1,3})\s*-\s*(\d{1,3})\b")
ATT   = re.compile(r"\b\d{2,3},\d{3}\b")
SIDE  = re.compile(r"(?:^|\s)(at|vs\.?)\s+[A-Z]")
PS    = re.compile(r"(?:^|\s)(INACTIVE|DNP|[PS])(?:\s|$)")
YEAR  = re.compile(r"\b(19[2-9]\d|20[0-2]\d)\b")
RECORD = re.compile(r"\((?:Won|W)[a-z]*\.?\s*(\d{1,2})[,\s]+(?:Lost|L)[a-z]*\.?\s*(\d{1,2})"
                    r"(?:[,\s]+(?:Tied|T)[a-z]*\.?\s*(\d{1,2}))?\)", re.I)
PRE  = re.compile(r"\b(PRE-?SEASON|Pre-?season|EXHIBITION|Exhibition)\b")
POST = re.compile(r"\b(POST-?SEASON|Post-?season|PLAYOFF|Playoff|SUPER BOWL|Super Bowl)\b")

GAP = 3   # consecutive non-rows that end a run

def signature(h):
    bits = [k for k, rx in HDR_BITS.items() if rx.search(h)]
    return ("Day/Date" if "Day/Date" in h else "Date") + "+" + "+".join(sorted(bits))

def main():
    sigs = collections.Counter()
    rows_by_sig = collections.Counter()
    side_by_sig = collections.Counter()
    att_by_sig = collections.Counter()
    wlt_by_sig = collections.Counter()
    fused_by_sig = collections.Counter()
    ps_by_sig = collections.Counter()
    ex = collections.defaultdict(list)
    ctx_counts = collections.Counter()
    years = collections.Counter()
    headed_with_year = 0
    headed_with_record = 0
    files = 0

    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith(".txt"): continue
        files += 1
        lines = open(os.path.join(TEXT, fn), encoding="utf-8", errors="replace").read().splitlines()
        i = 0
        ctx = "unknown"; ctx_year = None
        while i < len(lines):
            s = lines[i].strip()
            if PRE.search(s) and len(s) < 70: ctx = "preseason"
            elif POST.search(s) and len(s) < 70: ctx = "postseason"
            elif re.match(r"^\s*(19|20)\d\d\b", s) and len(s) < 70:
                ctx = "regular"; ctx_year = int(s[:4])
            if not (HDR_DATE.search(s) and HDR_OPP.search(s) and len(s) < 130
                    and any(rx.search(s) for rx in HDR_BITS.values())):
                i += 1; continue
            sig = signature(re.sub(r"\s+", " ", s))
            sigs[sig] += 1
            # look back up to 12 lines for the year and the declared record
            back = "\n".join(lines[max(0, i-12):i])
            ym = YEAR.findall(back); rm = RECORD.search(back)
            if ym: headed_with_year += 1
            if rm: headed_with_record += 1
            # walk the run
            j = i + 1; miss = 0; n = 0
            while j < len(lines) and miss < GAP:
                t = lines[j].strip()
                if t and ROW.match(t) and (SCORE.search(t) or WLT.search(t) or PS.search(t)):
                    n += 1; miss = 0
                    rows_by_sig[sig] += 1
                    if SIDE.search(t): side_by_sig[sig] += 1
                    if ATT.search(t): att_by_sig[sig] += 1
                    if WLT.search(t): wlt_by_sig[sig] += 1
                    if FUSED.search(t): fused_by_sig[sig] += 1
                    if PS.search(t): ps_by_sig[sig] += 1
                    ctx_counts[ctx] += 1
                    if ym: years[int(ym[-1])] += 1
                    if len(ex[sig]) < 4: ex[sig].append(t[:105])
                else:
                    if t: miss += 1
                j += 1
            i = j

    fam = {}
    for sig, hcount in sigs.most_common(24):
        r = rows_by_sig[sig]
        fam[sig] = {
            "header_occurrences": hcount, "rows_in_runs": r,
            "rows_per_header": round(r / hcount, 1) if hcount else 0,
            "with_at_or_vs": side_by_sig[sig],
            "home_away_recoverable_pct": round(100.0 * side_by_sig[sig] / r, 1) if r else 0.0,
            "with_attendance": att_by_sig[sig],
            "with_wlt": wlt_by_sig[sig], "wlt_fused_to_score": fused_by_sig[sig],
            "with_played_started_flag": ps_by_sig[sig],
            "examples": ex[sig],
        }
    rep = {
        "files": files,
        "header_rows_found": sum(sigs.values()),
        "distinct_header_signatures": len(sigs),
        "rows_under_a_header": sum(rows_by_sig.values()),
        "headers_with_a_year_within_12_lines": headed_with_year,
        "headers_with_a_declared_W_L_T_record": headed_with_record,
        "rows_by_section_context": dict(ctx_counts),
        "rows_by_year_decade": dict(sorted(collections.Counter(
            {} if not years else {(y // 10) * 10: 0 for y in years}).items())),
        "families": fam,
    }
    for y, c in years.items():
        rep["rows_by_year_decade"][(y // 10) * 10] = rep["rows_by_year_decade"].get((y // 10) * 10, 0) + c
    rep["rows_by_year_decade"] = dict(sorted(rep["rows_by_year_decade"].items()))
    json.dump(rep, open(OUT, "w"), indent=2)
    print(json.dumps({k: v for k, v in rep.items() if k != "families"}, indent=2))
    for k, v in fam.items():
        print(f"\n--- {k}\n    headers {v['header_occurrences']:,} | rows {v['rows_in_runs']:,}"
              f" ({v['rows_per_header']}/header) | at/vs {v['home_away_recoverable_pct']}%"
              f" | att {v['with_attendance']:,} | fused {v['wlt_fused_to_score']:,}")
        for e in v["examples"]: print("      ", e)

if __name__ == "__main__":
    main()
