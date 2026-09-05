"""Mirror coverage, carry-forward disagreement, and three cheap detectors.

Measurement only. Writes a report; no claim, no store, no parser.

Two encodings in this corpus fail SILENTLY. The section context is sticky, which
produced 50,092 impossible postseason rows. And home is encoded as the ABSENCE
of "at", so an OCR-dropped marker turns an away game into a home one with
nothing to detect it. Coverage was measured for the year rules; accuracy was not.
Both need an independent witness, and a mirrored game is one witness for both:
the opposing club's guide prints the same fixture with the "at" marker flipped
and its own year heading.

  MATCHING NEVER USES THE YEAR. The year is the unknown; matching on it would be
  circular and would manufacture the agreement being measured. A candidate pair
  is matched on club pair + month/day + the unordered score pair, and only then
  are the two guides' year assignments compared.

  python3 src/measure_guide_mirrors.py
"""
import re, os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
TEXT = "/Users/ryannecci/Documents/pgm3-sources/nfl-books/text_all"
OUT = os.path.join(BASE, "build-reports", "guide-mirrors.json")

CITIES = json.load(open(os.path.join(BASE, "export", "club_cities.json"), encoding="utf-8"))
GAMES = json.load(open(os.path.join(BASE, "export", "season_game_counts.json"),
                       encoding="utf-8"))["nfl_regular_season_games"]

UNAMB = CITIES["unambiguous"]
NICK = CITIES["unambiguous_when_the_nickname_is_present"]
AMBIG = CITIES["AMBIGUOUS_city_only_ALWAYS_DROPPED"]

HDR_DATE = re.compile(r"\b(Date|Day/Date)\b")
HDR_OPP = re.compile(r"\bOpponent\b")
HDR_BITS = re.compile(r"\b(W-L-T|W-L_|W-L|W/L|Result|Score|Attendance|Attend\.?|Att\.)\b")
HDR_VENUE = re.compile(r"\b(Location|Site|Stadium)\b")

DATE_SLASH = re.compile(r"^\s*(\d{1,2})/(\d{1,2})(?!/\d)\b")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DATE_MON = re.compile(r"^\s*(?:(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\.?,\s*)?"
                      r"([A-Z][a-z]{2})[a-z]*\.?\s?(\d{1,2})\b")
SECOND_DATE = re.compile(r"\S\s+(?:\d{1,2}/\d{1,2}(?!/\d)|"
                         r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\.,)")
SCORE = re.compile(r"\b(\d{1,3})\s*-\s*(\d{1,3})\b")
ATT = re.compile(r"\b\d{2,3},\d{3}\b")
# the away marker, INCLUDING the fused forms OCR produces: atCleveland, @HOU
AWAY = re.compile(r"(?:^|\s)(?:at|@)\s*(?=[A-Z])|(?:^|\s)at(?=[A-Z])")
HOMEMARK = re.compile(r"(?:^|\s)vs\.?\s+(?=[A-Z])")
# W/L/T including the OCR variants Ww, WwW, LL, lo
RESULT = re.compile(r"(?:^|\s)(W+w*W*|L+|T|Ww)(?=[\s_.,]|$)", re.I)
BAREYEAR = re.compile(r"^\s*(19[2-9]\d|20[0-2]\d)\b")
RECORD = re.compile(r"\((?:Won|W)[a-z]*\.?\s*(\d{1,2})[,\s]+(?:Lost|L)[a-z]*\.?\s*(\d{1,2})"
                    r"(?:[,\s]+(?:Tied|T)[a-z]*\.?\s*(\d{1,2}))?\)", re.I)
PUBYEAR = re.compile(r"-((?:19|20)\d\d)-")
LEAGUEWIDE = re.compile(r"^(nfl|official|nfl-hall|pro-football|afl-)")


def guide_club(fn):
    stem = re.sub(r"\.txt$", "", fn)
    stem = re.sub(r"-[a-z]$", "", stem)
    m = re.match(r"^(.*?)-((?:19|20)\d\d)-", stem)
    lead = m.group(1) if m else stem.split("-")[0]
    if LEAGUEWIDE.match(lead):
        return None, None
    nick = lead.split("-")[-1]
    py = PUBYEAR.search(fn)
    return nick, (int(py.group(1)) if py else None)


def opponent_club(residue):
    """Conservative. Returns (club, reason). Ambiguous city -> (None, 'ambiguous')."""
    t = residue.lower().strip()
    t = re.sub(r"^(at|@|vs\.?)\s*", "", t)
    t = re.sub(r"[^a-z0-9 .']+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return None, "empty"
    for k, v in NICK.items():            # nickname present -> unambiguous
        if t.startswith(k):
            return v, "nickname"
    for k in AMBIG:                      # ambiguous city, city only
        if t == k or t.startswith(k + " "):
            return None, "ambiguous"
    for k, v in UNAMB.items():
        if t == k or t.startswith(k + " "):
            return v, "city"
    return None, "unmapped"


def rows_of_file(fn):
    """Header-anchored rows, with the carry-forward year recorded but NOT used."""
    club, pub = guide_club(fn)
    if not club:
        return [], {}
    L = open(os.path.join(TEXT, fn), encoding="utf-8", errors="replace").read().splitlines()
    out = []
    stats = collections.Counter()
    year_headings = []          # detector 1: monotonicity
    per_year_rows = collections.Counter()   # detector 2: overrun
    blocks = []                 # detector 3: declared record vs counted
    i = 0
    carry = None
    pending_record = None
    while i < len(L):
        s = L[i].strip()
        if BAREYEAR.match(s) and len(s) < 70:
            carry = int(s[:4]); year_headings.append(carry)
            rm = RECORD.search(s)
            pending_record = (carry, rm.groups()) if rm else None
        if not (HDR_DATE.search(s) and HDR_OPP.search(s) and len(s) < 130
                and HDR_BITS.search(s) and not HDR_VENUE.search(s)):
            i += 1
            continue
        j = i + 1
        miss = 0
        blk = {"year": carry, "declared": pending_record, "W": 0, "L": 0, "T": 0, "n": 0}
        pending_record = None
        while j < len(L) and miss < 3:
            t = L[j].strip()
            if not t:
                j += 1
                continue
            sm = SCORE.search(t)
            dm = DATE_SLASH.match(t) or DATE_MON.match(t)
            if not (dm and sm):
                miss += 1
                j += 1
                continue
            miss = 0
            stats["rows_seen"] += 1
            if SECOND_DATE.search(t[dm.end():]):
                stats["dropped_two_column"] += 1
                j += 1
                continue
            if DATE_SLASH.match(t):
                mo, da = int(dm.group(1)), int(dm.group(2))
            else:
                mo = MONTHS.get(dm.group(1).lower()[:3])
                da = int(dm.group(2))
            if not mo or not (1 <= mo <= 12 and 1 <= da <= 31):
                stats["dropped_bad_date"] += 1
                j += 1
                continue
            a, b = int(sm.group(1)), int(sm.group(2))
            if a > 100 or b > 100:
                stats["dropped_impossible_score"] += 1
                j += 1
                continue
            resid = t[dm.end():]
            resid = ATT.sub(" ", resid)
            resid = SCORE.sub(" ", resid)
            away = bool(AWAY.search(resid))
            home_marked = bool(HOMEMARK.search(resid))
            resid = RESULT.sub(" ", resid)
            resid = re.sub(r"[.—–_*+#|()\[\]]+", " ", resid)
            resid = re.sub(r"\s+", " ", resid).strip()
            opp, why = opponent_club(resid)
            stats["opp_" + why] += 1
            rl = RESULT.search(t[dm.end():])
            wlt = None
            if rl:
                g = rl.group(1).upper()
                wlt = "W" if g.startswith("W") else ("L" if g.startswith("L") else "T")
                blk[wlt] += 1
            blk["n"] += 1
            if carry:
                per_year_rows[carry] += 1
            if opp:
                out.append({"guide": fn, "club": club, "pub": pub, "carry": carry,
                            "mo": mo, "da": da, "opp": opp,
                            "sc": tuple(sorted((a, b))), "away": away,
                            "home_marked": home_marked, "wlt": wlt})
            j += 1
        if blk["n"]:
            blocks.append(blk)
        i = j
    return out, {"stats": stats, "years": year_headings,
                 "per_year_rows": per_year_rows, "blocks": blocks}


def decade(y):
    return (y // 10) * 10 if y else None


def main():
    allrows = []
    stats = collections.Counter()
    mono_viol = 0
    mono_checked = 0
    overrun = collections.Counter()
    overrun_checked = 0
    unchecked_pre1933 = 0
    ck_blocks = 0
    ck_pass = 0
    ck_fail = 0
    files = 0
    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith(".txt"):
            continue
        files += 1
        rows, meta = rows_of_file(fn)
        if not meta:
            continue
        allrows.extend(rows)
        stats.update(meta["stats"])
        ys = meta["years"]
        for a, b in zip(ys, ys[1:]):
            mono_checked += 1
            if b < a:
                mono_viol += 1
        for y, n in meta["per_year_rows"].items():
            if y < 1933:
                unchecked_pre1933 += 1
                continue
            cap = GAMES.get(str(y))
            if cap is None:
                unchecked_pre1933 += 1
                continue
            overrun_checked += 1
            if n > cap + 10:
                overrun[decade(y)] += 1
        for blk in meta["blocks"]:
            if not blk["declared"]:
                continue
            ck_blocks += 1
            w, l, t = blk["declared"][1]
            dw, dl = int(w), int(l)
            dt = int(t) if t else 0
            if (blk["W"], blk["L"], blk["T"]) == (dw, dl, dt):
                ck_pass += 1
            else:
                ck_fail += 1

    # ---- MEASURE 1: mirror coverage. Key excludes the year, deliberately. ----
    key = collections.defaultdict(list)
    for r in allrows:
        key[(frozenset((r["club"], r["opp"])), r["mo"], r["da"], r["sc"])].append(r)

    mirrored = collections.Counter()
    total = collections.Counter()
    ha_agree = collections.Counter()
    ha_total = collections.Counter()
    yr_agree = collections.Counter()
    yr_dis = collections.Counter()
    yr_total = collections.Counter()
    pairs_examined = 0

    for r in allrows:
        total[decade(r["carry"])] += 1

    mirrored_rows = collections.Counter()
    # SECOND AXIS, independent of carry-forward: the guide's publication decade,
    # taken from the filename. The carry-forward decade axis is contaminated --
    # it bins rows by the very value under test -- so a row wrongly carried into
    # 1925 is REPORTED as a 1920s row. Publication decade cannot be contaminated
    # that way. It answers a different question (which guides supply mirrors,
    # not which seasons are covered) and is an upper bound on the season year.
    pub_total = collections.Counter()
    pub_mirrored = collections.Counter()
    pub_ha_total = collections.Counter()
    pub_ha_agree = collections.Counter()
    pub_yr_total = collections.Counter()
    pub_yr_dis = collections.Counter()
    for r in allrows:
        pub_total[decade(r["pub"])] += 1
    for k, group in key.items():
        by_club = collections.defaultdict(list)
        for r in group:
            by_club[r["club"]].append(r)
        # an independent witness means two DIFFERENT clubs' guides. Two guides of
        # the same club reprint the same history and witness nothing.
        if len(by_club) < 2:
            continue
        ca, cb = sorted(by_club)[:2]
        ra, rb = by_club[ca][0], by_club[cb][0]
        pairs_examined += 1
        d = decade(ra["carry"]) or decade(rb["carry"])
        # coverage is counted in ROWS, not pairs: every row in a mirrored group
        # is a row whose game has an independent witness.
        for r in group:
            mirrored_rows[decade(r["carry"])] += 1
            pub_mirrored[decade(r["pub"])] += 1
        pd = decade(ra["pub"]) or decade(rb["pub"])
        pub_ha_total[pd] += 1
        if ra["away"] != rb["away"]:
            pub_ha_agree[pd] += 1
        if ra["carry"] and rb["carry"]:
            pub_yr_total[pd] += 1
            if ra["carry"] != rb["carry"]:
                pub_yr_dis[pd] += 1
        mirrored[d] += 1
        ha_total[d] += 1
        if ra["away"] != rb["away"]:
            ha_agree[d] += 1
        if ra["carry"] and rb["carry"]:
            yr_total[d] += 1
            if ra["carry"] == rb["carry"]:
                yr_agree[d] += 1
            else:
                yr_dis[d] += 1

    decades = sorted({d for d in list(total) + list(mirrored_rows) if d})
    per_decade = {}
    for d in decades:
        m, t = mirrored_rows[d], total[d]
        yt = yr_total[d]
        per_decade[str(d)] = {
            "rows_with_a_mapped_opponent": t,
            "rows_in_a_mirrored_group": m,
            "mirror_coverage_pct": round(100.0 * m / t, 1) if t else 0.0,
            "home_away_pairs_checked": ha_total[d],
            "home_away_agree": ha_agree[d],
            "home_away_agreement_pct": round(100.0 * ha_agree[d] / ha_total[d], 1) if ha_total[d] else None,
            "carry_forward_pairs_with_both_years": yt,
            "carry_forward_disagreements": yr_dis[d],
            "carry_forward_DISAGREEMENT_pct": round(100.0 * yr_dis[d] / yt, 1) if yt else None,
        }

    by_pub = {}
    for d in sorted({x for x in pub_total if x}):
        t, m = pub_total[d], pub_mirrored[d]
        yt = pub_yr_total[d]
        by_pub[str(d)] = {
            "rows": t, "rows_in_a_mirrored_group": m,
            "mirror_coverage_pct": round(100.0 * m / t, 1) if t else 0.0,
            "home_away_pairs": pub_ha_total[d],
            "home_away_agreement_pct": round(100.0 * pub_ha_agree[d] / pub_ha_total[d], 1) if pub_ha_total[d] else None,
            "carry_forward_pairs": yt,
            "carry_forward_DISAGREEMENT_pct": round(100.0 * pub_yr_dis[d] / yt, 1) if yt else None,
        }

    rep = {
        "_what_this_is": "measurement only; no parser, no claim, no store",
        "_THE_CARRY_FORWARD_DECADE_AXIS_IS_CONTAMINATED": (
            "BY_DECADE bins each row by its carry-forward year -- the value under "
            "test. A row wrongly carried into 1925 is reported as a 1920s row. "
            "BY_PUBLICATION_DECADE is the independent axis and shows a different "
            "question: which guides supply mirrors, not which seasons are covered."),
        "rows_with_NO_carry_forward_year": total[None],
        "_matching_never_used_the_year": True,
        "files": files,
        "rows_seen_under_a_header": stats["rows_seen"],
        "rows_kept_with_a_mapped_opponent": len(allrows),
        "dropped": {
            "two_column_row": stats["dropped_two_column"],
            "bad_date": stats["dropped_bad_date"],
            "impossible_score": stats["dropped_impossible_score"],
            "opponent_AMBIGUOUS_city": stats["opp_ambiguous"],
            "opponent_unmapped": stats["opp_unmapped"],
            "opponent_empty": stats["opp_empty"],
        },
        "opponent_resolved_by": {
            "nickname_present": stats["opp_nickname"],
            "unambiguous_city": stats["opp_city"],
        },
        "mirrored_groups": pairs_examined,
        "BY_DECADE": per_decade,
        "BY_PUBLICATION_DECADE": by_pub,
        "detectors": {
            "1_year_headings_non_decreasing": {
                "adjacent_pairs_checked": mono_checked,
                "backwards_jumps": mono_viol,
                "pct": round(100.0 * mono_viol / mono_checked, 2) if mono_checked else None,
            },
            "2_rows_carried_past_a_season_length": {
                "year_blocks_checked": overrun_checked,
                "unchecked_no_bound_available": unchecked_pre1933,
                "overruns_by_decade": {str(k): v for k, v in sorted(overrun.items()) if k},
                "_bound": "regular_season + 10, deliberately generous",
            },
            "3_declared_W_L_T_checksum": {
                "blocks_with_a_declared_record": ck_blocks,
                "matched_the_counted_rows": ck_pass,
                "did_not_match": ck_fail,
                "pct_matching": round(100.0 * ck_pass / ck_blocks, 1) if ck_blocks else None,
            },
        },
    }
    json.dump(rep, open(OUT, "w"), indent=2)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
