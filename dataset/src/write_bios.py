"""Generate a human-readable paragraph for a person, FROM CLAIMS ONLY.

Rules, and they are the point:
  - every sentence traces to a claim. Nothing plausible-but-unsourced.
  - a gap is stated, not smoothed. "appears on a roster in 1941, then not again
    until 1946" is a fact, and the reader knows what it means.
  - shape varies by career. A one-game man in 1926 does not get the sentences a
    fifteen-year career gets.
  - a statistic is only rendered where the declaration says the measure applies.

  python3 src/write_bios.py --sample 50
"""
import os, re, sys, json, random, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
CLUBS = IDX.pop("_clubs", {})


def club(code, year):
    """The club's name IN THAT SEASON. 26 team codes carry more than one name -
    BU1 is the Buffalo All-Americans, then the Bisons, then the Rangers - so a
    per-code name would be wrong for part of their history."""
    return CLUBS.get(f"{code}|{year}") or code
DECL = json.load(open(os.path.join(BASE, "declarations", "statscrew.json")))
APPLIC = DECL["stat_columns"]["applicability"]
_pf = os.path.join(BASE, "declarations", "position_function.json")
POSFN = json.load(open(_pf))["codes"] if os.path.exists(_pf) else {}
UNRESOLVED = set(APPLIC.get("_unresolved", {}).get("columns", []))

LEAGUE_NAME = {"NFL": "the NFL", "APFA": "the APFA", "AAFC": "the AAFC",
               "AFL": "the AFL", "CFL": "the CFL", "WFL": "the WFL",
               "USFL": "the USFL", "USFL2": "the USFL", "XFL": "the XFL",
               "WLAF": "the World League", "UFL": "the UFL", "UFL2": "the UFL",
               "AAF": "the AAF"}


def seasons(p):
    out = []
    for k, d in p["seasons"].items():
        lg, yr, club = k.split("|")
        m = re.search(r"(\d{4})", yr)          # salary stints use "y1952"
        if not m: continue
        out.append({"league": lg, "year": int(m.group(1)), "club": club,
                    "stint": d.get("stint", {}), "stats": d.get("stats", {})})
    return sorted(out, key=lambda s: (s["year"], s["club"]))


def clean(v):
    """A source that writes the literal 'None' or 'none' has told us nothing."""
    if v is None: return None
    t = str(v).strip().strip(",")
    if t.lower() in ("none", "null", "", "n/a", "-"): return None
    t = re.sub(r"\bNone\b", "", t).strip().strip(",").strip()
    return t or None


def num(v):
    try: return float(str(v).replace(",", ""))
    except Exception: return None


def career_totals(ss):
    t = collections.Counter()
    for s in ss:
        for k, v in s["stats"].items():
            if k in UNRESOLVED: continue
            n = num(v)
            if n is not None and k in ("Yds", "TDs", "No.", "Att", "Comp", "Ints"):
                t[k] += n
    return t


def gaps(years):
    out = []
    for a, b in zip(years, years[1:]):
        if b - a > 1: out.append((a, b))
    return out


def bio(g, p):
    name = p["name"] or "This man"
    ss = seasons(p)
    if not ss: return None
    yrs = sorted({s["year"] for s in ss})
    clubs = list(dict.fromkeys(s["club"] for s in ss))
    lgs = [l for l in dict.fromkeys(s["league"] for s in ss) if l != "COACHES"]
    span = (yrs[0], yrs[-1])
    n_seasons = len(yrs)
    per = p["person"]
    # position is era-native and stored as {"code": "LDH", "vocab": "statscrew"}
    pos = []
    for s in ss:
        v = s["stint"].get("position")
        for one in (v if isinstance(v, list) else [v]):
            if isinstance(one, dict): one = one.get("code")
            if one and one not in pos: pos.append(str(one))
    born = clean(per.get("birth_date", [None])[0])
    college = clean(per.get("college", [None])[0])
    where = clean(per.get("hometown", [None])[0])

    # A COACHING season is not a playing season. Both are `stint` subjects and
    # only a role_title claim tells them apart - so "Mike McCarthy played 18
    # seasons" came out of the same sentence that describes a player.
    def is_coaching(s):
        return bool(s["stint"].get("role_title")) and not s["stint"].get("position")
    played = [s for s in ss if not is_coaching(s)]
    coached = [s for s in ss if is_coaching(s)]
    if not played and coached:
        cy = sorted({s["year"] for s in coached})
        cl = list(dict.fromkeys(s["club"] for s in coached))
        lead = name
        if born: lead += f", born {born}"
        out = [f"{lead}, appears in the record as a coach, not a player."]
        out.append(f"He coached {len(cy)} seasons between {cy[0]} and {cy[-1]}"
                   + (f", with the {club(cl[0], str(cy[0]))}." if len(cl) == 1
                      else ", for the " + ", the ".join(
                          club(c, str(next(s['year'] for s in coached if s['club'] == c)))
                          for c in cl[:3]) + "."))
        if college: out.append(f"He came from {college}.")
        for a, b in gaps(cy):
            out.append(f"He appears on a staff in {a}, then not again until {b}.")
        return " ".join(out)
    ss_all = ss
    ss = played or ss
    yrs = sorted({s["year"] for s in ss})
    clubs = list(dict.fromkeys(s["club"] for s in ss))
    n_seasons = len(yrs)
    span = (yrs[0], yrs[-1])

    S = []

    # --- opening, varied by career length -------------------------------------
    lead = name
    if born: lead += f", born {born}"
    if where: lead += f" in {where}"
    if n_seasons == 1:
        s0 = ss[0]
        S.append(f"{lead}, appears in the record for a single season: "
                 f"{s0['year']} with the {club(s0['club'], str(s0['year']))} in "
                 f"{LEAGUE_NAME.get(s0['league'], s0['league'])}.")
    elif n_seasons <= 3:
        S.append(f"{lead}, played {n_seasons} seasons between {span[0]} and {span[1]}.")
    elif len(clubs) >= 4:
        S.append(f"{lead}, spent {n_seasons} seasons across {len(clubs)} clubs "
                 f"between {span[0]} and {span[1]}.")
    else:
        S.append(f"{lead}, played {n_seasons} seasons from {span[0]} to {span[1]}"
                 + (f", all of them with the {club(clubs[0], str(yrs[0]))}."
                    if len(clubs) == 1 else ", for the "
                    + ", the ".join(club(c, str(next(s['year'] for s in ss if s['club'] == c)))
                                    for c in clubs[:3]) + "."))
    if college:
        S.append(f"He came from {college}." if not college.endswith(".")
                 else f"He came from {college}")
    if pos:
        if len(pos) == 1:
            S.append(f"The rosters list him at {pos[0]}.")
        else:
            S.append("The rosters list him at " + ", ".join(pos[:3])
                     + (", and other positions." if len(pos) > 3 else "."))

    # --- more than one league --------------------------------------------------
    if len(lgs) > 1:
        bits = []
        for lg in lgs:
            if lg == "COACHES": continue
            ys = sorted({s["year"] for s in ss if s["league"] == lg})
            bits.append(f"{LEAGUE_NAME.get(lg, lg)} ({ys[0]}"
                        + (f"–{ys[-1]}" if ys[-1] != ys[0] else "") + ")")
        S.append("His career crosses leagues: " + "; ".join(bits) + ".")

    # --- gaps, stated not smoothed --------------------------------------------
    for a, b in gaps(yrs):
        S.append(f"He appears on a roster in {a}, then not again until {b}.")

    # --- what he did, only where a measure applies -----------------------------
    # WHICH statistic matters depends on the position, and nothing in the archive
    # says so - 2,298 position codes and no mapping. So take the largest counting
    # total the man actually has and NAME the column, rather than pretending to
    # know which number defines him. Junior Seau's tackles ARE in the archive;
    # hardcoding "yards" reported a 20-year linebacker as having 238 of them.
    # keyed on TABLE.COLUMN now: a statistic that does not name its table is
    # ambiguous, and "yards" alone was reporting punters as leading passers.
    LABEL = {"rushing.Yds": "rushing yards", "receiving.Yds": "receiving yards",
             "passing.Yds": "passing yards", "punting.Yds": "punting yards",
             "punt_returns.Yds": "punt return yards",
             "kick_returns.Yds": "kick return yards",
             "interceptions.Yds": "interception return yards",
             "defense_and_fumbles.Tackle": "tackles",
             "defense_and_fumbles.Solo": "solo tackles",
             "defense_and_fumbles.FF": "forced fumbles",
             "receiving.No.": "receptions", "rushing.No.": "carries",
             "interceptions.No.": "interceptions", "punting.No.": "punts",
             "passing.Comp": "completions", "passing.TDs": "touchdown passes",
             "total_scoring.Points": "points", "kicking.FGM": "field goals"}
    tot = collections.Counter()
    for s in ss:
        for k, v in s["stats"].items():
            if k in UNRESOLVED or k not in LABEL: continue
            n = num(v)
            if n: tot[k] += n
    if tot:
        # WHICH statistic matters is decided by the position's derived function,
        # not by which number happens to be biggest. Junior Seau's 238 interception
        # return yards outranked his 1,686 tackles until this existed.
        want = None
        for pcode in pos:
            f = POSFN.get(pcode, {}).get("salient_column")
            if not f: continue
            for cand in LABEL:
                if cand.endswith("." + f) and tot.get(cand): want = cand; break
            if want: break
        k = want or max(tot, key=lambda x: tot[x] * (2 if x in ("Tackle", "Yds", "Rec") else 1))
        best = max(ss, key=lambda s: num(s["stats"].get(k)) or 0)
        bv = num(best["stats"].get(k)) or 0
        if bv and len(ss) > 1 and bv >= 0.2 * tot[k]:
            S.append(f"His biggest recorded season was {best['year']} with "
                     f"the {club(best['club'], str(best['year']))}: "
                     f"{int(bv):,} {LABEL[k]}.")
        S.append(f"In all, the surviving statistics credit him with "
                 f"{int(tot[k]):,} {LABEL[k]}"
                 + (f" and {int(tot['TDs']):,} touchdowns."
                    if tot.get("TDs") and k != "TDs" else ".")
                 .replace("1 touchdowns", "1 touchdown"))
    elif not any(s["stats"] for s in ss):
        S.append("No statistics are recorded for him — only that he was there.")

    # --- coaching --------------------------------------------------------------
    roles = sorted({v for s in ss_all for k, v in s["stint"].items()
                    if k == "role_title" for v in ([v] if isinstance(v, str) else v)})
    if roles:
        cy = sorted({s["year"] for s in ss_all if s["stint"].get("role_title")})
        S.append(f"He also appears as {roles[0].lower()}"
                 + (f" ({cy[0]}–{cy[-1]})." if len(cy) > 1 else f" in {cy[0]}."))
    return " ".join(S)


def main():
    n = 50
    if "--sample" in sys.argv: n = int(sys.argv[sys.argv.index("--sample") + 1])
    people = {g: p for g, p in IDX.items() if p["seasons"] and p["name"]}
    buckets = collections.defaultdict(list)
    for g, p in people.items():
        ss = seasons(p); yrs = sorted({s["year"] for s in ss})
        clubs = {s["club"] for s in ss}; lgs = {s["league"] for s in ss}
        dec = (yrs[0] // 10) * 10
        has_stats = any(s["stats"] for s in ss)
        roles = any(k == "role_title" for s in ss for k in s["stint"])
        if roles: buckets["player-coach"].append(g)
        if len(yrs) == 1: buckets[f"one season {dec}s"].append(g)
        elif len(yrs) >= 12: buckets["long career"].append(g)
        elif len(clubs) >= 4: buckets["journeyman"].append(g)
        if len(lgs) > 1: buckets["multi-league"].append(g)
        if gaps(yrs) and any(1941 <= a <= 1945 or 1941 <= b <= 1945
                             for a, b in gaps(yrs)): buckets["war gap"].append(g)
        if not has_stats: buckets["no statistics"].append(g)
        buckets[f"{dec}s"].append(g)
    random.seed(17)
    chosen, seen = [], set()
    order = ["one season 1920s", "war gap", "player-coach", "multi-league",
             "journeyman", "long career", "no statistics", "1920s", "1930s",
             "1940s", "1950s", "1960s", "1970s", "1980s", "1990s", "2000s",
             "2010s", "2020s"]
    per = max(1, n // len(order))
    for b in order:
        pool = [g for g in buckets.get(b, []) if g not in seen]
        for g in random.sample(pool, min(per, len(pool))):
            seen.add(g); chosen.append((b, g))
    while len(chosen) < n:
        g = random.choice(list(people))
        if g not in seen: seen.add(g); chosen.append(("random", g))
    for b, g in chosen[:n]:
        t = bio(g, people[g])
        if t: print(f"\n[{b}]  {g}\n{t}")


if __name__ == "__main__":
    main()
