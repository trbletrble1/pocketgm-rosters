"""Build the club table from held material. Writes build/clubs.json only.

Reads: the person index (its _clubs map is StatsCrew's code|year -> name, plus
PFA's nine 1926 AFL clubs; player season keys give the league by year and the
men who corroborate every cross-source claim), build/club-names.json,
build/pfa-coaches.json, build/pfa-pre1950.json transactions,
build/nflverse-rosters.json, build/coaches.json, build/assistants.json,
build/pfa-boxscores.json, the person merges (for corroboration: a name and a code one man
holds for one season are one club) and the merger rulings in declarations/clubs.json (by
name; the builder finds the codes). It reads NO decisions file: the club-key decisions are
made FROM this table by normalise_club_keys.py.

  python3 src/build_clubs.py [--write]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import norm, nickname, city, TABLE
DECL = json.load(open(os.path.join(BASE, "declarations", "clubs.json")))

PSEUDO = {"SALARIES": "court store", "COACHES": "Coaching Tree stints"}   # season-key tokens that are not leagues
FAMILY = {"WIFU": "CFL", "IRFU": "CFL", "ORFU": "CFL", "NFLE": "WLAF", "ARENA": "ARFL"}    # PFA's pre-1958 Canadian leagues live under the archive's CFL codes; NFL Europe is the WLAF renamed


def fam(league, year):
    """The archive's league for a source's league name in a given year. PFA reuses 'UFL' and 'USFL' for the revivals."""
    if league == "UFL" and year >= 2024: return "UFL2"
    if league == "USFL" and year >= 2022: return "USFL2"
    return FAMILY.get(league, league)
CARRY_MIN, CARRY_SHARE = 4, 0.25                                            # men carried across a code change before it is a relocation


def slug(s): return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")


def lev(a, b):
    if abs(len(a) - len(b)) > 2: return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def initials(s): return "".join(w[0] for w in (s or "").lower().split() if w[0].isalpha())


def year_of(y): return int(y[1:5]) if str(y).startswith("y") else int(y)


def clean_printed(s):
    """'1954 British Columbia Lions (WIFU)' -> 'British Columbia Lions'. The full form is kept beside it."""
    return re.sub(r"^\d{4} ", "", re.sub(r"\s*\(.*?\)$", "", s or "")).strip()


def main():
    write = "--write" in sys.argv
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    CL = IDX.pop("_clubs")
    prev = json.load(open(TABLE)) if os.path.exists(TABLE) else {}
    anchor = dict(prev.get("id_anchor", {}))
    unresolved = collections.defaultdict(list)

    # ---------------------------------------------------------------- 1. what the index holds per code and year
    lg_of = collections.defaultdict(lambda: collections.defaultdict(set))
    men_at = collections.defaultdict(set)                     # (year, code) -> pids
    for pid, p in IDX.items():
        for k in p.get("seasons") or {}:
            lg, y, c = k.split("|", 2); yr = year_of(y)
            if lg in PSEUDO: continue
            lg_of[c][lg].add(yr); men_at[(yr, c)].add(pid)
    league_years = collections.defaultdict(set)
    for d in lg_of.values():
        for lg, ys in d.items(): league_years[lg] |= ys
    # a DARK year is a league-wide season not played (2020 CFL, 2021-22 XFL): a hole of at most two years inside a
    # league's span. Longer holes are not dark -- the 1926 AFL and the 1960 AFL share a name, not a league.
    dark = {}
    for lg, ys in league_years.items():
        holes = sorted(y for y in range(min(ys), max(ys) + 1) if y not in ys); runs, run = [], []
        for y in holes:
            if run and y == run[-1] + 1: run.append(y)
            else:
                if run: runs.append(run)
                run = [y]
        if run: runs.append(run)
        dark[lg] = {y for r in runs if len(r) <= 2 for y in r}
    # the merger rulings, by name: the merged club is the code-year carrying the merged name that HOLDS THE MEN;
    # any other code-year carrying that name is a phantom and is silenced with its reason
    MERGED = {}                                                          # (league, year, code) -> {name, of: [parent names], kind}
    for r in DECL["MERGERS"]["rulings"]:
        y = int(r["year"]); carriers = [k.split("|")[0] for k, v in CL.items() if k.endswith(f"|{y}") and v == r["merged"]]
        with_men = [c for c in carriers if men_at.get((y, c))]
        if len(with_men) != 1: raise SystemExit(f"build_clubs: merger {r['merged']} {y}: code-years carrying the name {carriers}, with men {with_men}; need exactly one")
        MERGED[(r["league"], str(y), with_men[0])] = {"name": r["merged"], "of": r["of"], "kind": r["kind"], "phantoms": [c for c in carriers if c != with_men[0]]}
    silent = {(c, int(y)) for (_, y, _), m in MERGED.items() for c in m["phantoms"]}
    hist = collections.defaultdict(dict)
    for k, v in CL.items():
        c, y = k.split("|")
        if (c, int(y)) in silent:
            unresolved["silenced_code_years"].append({"code": c, "year": int(y), "name": v, "why": "carries a merged club's name in the merger year but holds no men; the season belongs to the code that does (declarations/clubs.json MERGERS)"}); continue
        hist[c][int(y)] = v
    pfa_league = {}
    for c in json.load(open(os.path.join(BASE, "build", "club-names.json")))["claims"]:
        if c["subject"][1] not in ("?", None): pfa_league[c["subject"][3]] = c["subject"][1]
        k = f"{c['subject'][3]}|{c['subject'][2]}"
        if k not in CL: unresolved["club_names_not_yet_in_the_index"].append({"code_year": k, "name": c["value"], "league": c["subject"][1], "why": "build/club-names.json holds it; the person index's _clubs will after the next rebuild"})

    def league_at(code, yr):
        for lg, ys in lg_of.get(code, {}).items():
            if yr in ys: return lg, "player season key"
        if code in pfa_league: return pfa_league[code], "PFA club-season claim"
        for pre, lg in (("CFL", "CFL"), ("USFL", "USFL"), ("US2", "USFL2"), ("XFL", "XFL"), ("AFL", "AFL"), ("WFL", "WFL"), ("UFL", "UFL"), ("AAF", "AAF")):
            if code.startswith(pre) and len(code) > len(pre): return lg, "code prefix; no player season held"
        return None, "unknown"

    # ---------------------------------------------------------------- 2. segments: one code, one contiguous run of years
    runs = []
    for code, ys in hist.items():
        years = sorted(ys); run = [years[0]]; dk = []
        for a, b in zip(years, years[1:]):
            lg, _ = league_at(code, a); gap = set(range(a + 1, b))
            if not gap or (lg and gap <= dark.get(lg, set())): run.append(b); dk.extend(sorted(gap))
            else: runs.append((code, run, dk)); run = [b]; dk = []
        runs.append((code, run, dk))
    segs = []
    for code, run, dk in runs:
        leagues, names = [], []
        for y in run:                                                    # a name and a league persist across a league-wide dark year
            lg, ev = league_at(code, y)
            if leagues and leagues[-1]["league"] == lg: leagues[-1]["last"] = y
            else:
                if leagues: leagues[-1]["last"] = y - 1
                leagues.append({"league": lg, "first": y, "last": y, "evidence": ev})
            nm = hist[code][y]
            if names and names[-1]["name"] == nm: names[-1]["last"] = y
            else:
                if names: names[-1]["last"] = y - 1
                names.append({"name": nm, "first": y, "last": y, "kind": "official", "source": "pro-football-archives" if code in pfa_league else "statscrew"})
        segs.append({"code": code, "first": run[0], "last": run[-1], "leagues": leagues, "names": names, "origin": "archive",
                     "dark_years": dk, "_dark_note": "league-wide seasons not played; the club is carried across them under its last name" if dk else ""})
    segs.sort(key=lambda s: (s["first"], s["code"]))
    merged_codes = {code for (_, _, code), m in MERGED.items() if m["kind"] == "merger"}

    # ---------------------------------------------------------------- 3. lineage, mechanical only
    def nick_last(s): return nickname(s["names"][-1]["name"])
    def nick_first(s): return nickname(s["names"][0]["name"])
    def lg_at(s, y):
        for l in s["leagues"]:
            if l["first"] <= y <= l["last"]: return l["league"]
    def carry(a, b):
        A, B = men_at.get((a["last"], a["code"]), set()), men_at.get((b["first"], b["code"]), set())
        return len(A & B), min(len(A), len(B))
    succ, pred = {}, {}
    for i, a in enumerate(segs):
        if a["code"] in merged_codes: continue
        best = None
        for j, b in enumerate(segs):
            if j == i or j in pred or b["code"] in merged_codes or b["first"] <= a["last"]: continue
            gap = set(range(a["last"] + 1, b["first"]))
            lg = lg_at(a, a["last"])
            adjacent = not gap or (lg and gap <= dark.get(lg, set()))
            n, m = carry(a, b)
            same_nick = nick_first(b) == nick_last(a)
            if b["code"] != a["code"]:
                if not adjacent or not same_nick: 
                    if adjacent and n >= 8 and m and n / m >= 0.5:
                        unresolved["lineage_candidates"].append({"kind": "code change, nickname NOT carried, men carried", "from": [a["code"], a["last"], a["names"][-1]["name"]],
                                                                 "to": [b["code"], b["first"], b["names"][0]["name"]], "men_carried": [n, m], "why": "a relocation that also renamed is a ruling, not a mechanical link"})
                    continue
                if n >= CARRY_MIN and m and n / m >= CARRY_SHARE:
                    cand = (0, -n, j, f"relocation or recode: nickname carried into the next year under a new code; {n} of {m} men carried")
                else:
                    unresolved["lineage_candidates"].append({"kind": "code change, nickname carried, men NOT carried", "from": [a["code"], a["last"], a["names"][-1]["name"]],
                                                             "to": [b["code"], b["first"], b["names"][0]["name"]], "men_carried": [n, m], "why": "a shared nickname across a code change is not a relocation until the men carry over"})
                    continue
            else:
                if adjacent: continue                                   # cannot happen: same code adjacent is one segment
                if not same_nick:
                    unresolved["lineage_splits"].append({"code": a["code"], "earlier": [a["first"], a["last"], a["names"][-1]["name"]], "later": [b["first"], b["last"], b["names"][0]["name"]],
                                                         "men_carried": [n, m], "why": "same code, different nickname across a gap: two clubs until a ruling says otherwise"})
                    continue
                cand = (1, -n, j, f"resumed: same code and nickname after a {len(gap)}-year absence; {n} of {m} men carried" + ("" if n >= CARRY_MIN else " (NOT corroborated by the men)"))
            if best is None or cand < best: best = cand
        if best:
            _, _, j, why = best; succ[i] = (j, why); pred[j] = (i, why)

    # ---------------------------------------------------------------- 4. chains -> clubs
    def anchor_id(key, name, first):
        cid = anchor.get(key) or f"club-{slug(name)}-{first}"
        n = 2
        while cid in by_id and anchor.get(key) != cid: cid = f"{slug(name)}-{first}-{n}"; n += 1
        anchor[key] = cid; return cid
    clubs = []; seen = set()
    def new_id(first_seg, name):
        key = f"{first_seg['code']}|{first_seg['first']}"
        cid = anchor.get(key) or f"club-{slug(name)}-{first_seg['first']}"
        anchor[key] = cid; return cid
    for i in sorted(range(len(segs)), key=lambda i: (segs[i]["first"], segs[i]["code"])):
        if i in seen or i in pred: continue
        chain, k = [], i
        while True:
            chain.append(k); seen.add(k)
            if k in succ: k = succ[k][0]
            else: break
        first = segs[chain[0]]; cid = new_id(first, first["names"][0]["name"])
        names, leagues = [], []
        for k in chain:
            for n in segs[k]["names"]:
                if names and names[-1]["name"] == n["name"] and names[-1]["last"] + 1 >= n["first"]: names[-1]["last"] = n["last"]
                else: names.append(dict(n))
            for lg in segs[k]["leagues"]:
                if leagues and leagues[-1]["league"] == lg["league"] and leagues[-1]["last"] + 1 >= lg["first"]: leagues[-1]["last"] = lg["last"]
                else: leagues.append(dict(lg))
        lineage = {"kind": "merger" if first["code"] in merged_codes else ("single segment" if len(chain) == 1 else "chain"),
                   "links": [{"from": segs[a]["code"], "to": segs[b]["code"], "year": segs[b]["first"], "why": succ[a][1]} for a, b in zip(chain, chain[1:])],
                   "merger_of": [], "merger_seasons": {}, "merged_into": {}}
        clubs.append({"id": cid, "origin": "archive", "first": first["first"], "last": segs[chain[-1]]["last"],
                      "segments": [{k2: v for k2, v in segs[k].items() if k2 not in ("names", "origin")} for k in chain],
                      "names": names, "leagues": leagues, "lineage": lineage, "strings": []})
    by_id = {c["id"]: c for c in clubs}
    by_code_year = {}
    for c in clubs:
        for s in c["segments"]:
            for y in range(s["first"], s["last"] + 1): by_code_year[(s["code"], y)] = c["id"]

    # ---------------------------------------------------------------- 5. mergers, from the rulings: parents are found by NAME the year before
    parent_name_in_merger_year = {}                                     # (norm(parent name), year) -> merged club id
    name_in_year = collections.defaultdict(set)
    for c in clubs:
        for n in c["names"]:
            for y in range(n["first"], n["last"] + 1): name_in_year[(norm(n["name"]), y)].add(c["id"])
    for (lg, y, code), m in MERGED.items():
        y = int(y); cid = by_code_year.get((code, y))
        if not cid: unresolved["merged_clubs"].append({"code": code, "year": y, "why": "merged code not in _clubs"}); continue
        c = by_id[cid]; parents = []
        for pn in m["of"]:
            ids = {i for yy in range(y - 1, y - 4, -1) for i in name_in_year.get((norm(pn), yy), set())}
            if len(ids) != 1: unresolved["merged_clubs"].append({"parent": pn, "year": y, "why": f"parent name resolves to {sorted(ids)} in the three years before the merger; need exactly one"}); continue
            pid_ = next(iter(ids)); parents.append(pid_)
            by_id[pid_]["lineage"]["merged_into"][str(y)] = cid
            parent_name_in_merger_year[(norm(pn), y)] = cid
        if m["kind"] == "merger": c["lineage"]["kind"] = "merger"; c["lineage"]["merger_of"] = parents
        else: c["lineage"]["merger_seasons"][str(y)] = {"absorbed": parents, "name": m["name"]}
        c["strings"].append({"string": m["name"], "source": "merger_ruling", "kind": "alias", "league": lg, "first": y, "last": y})
    for c in clubs:                                                   # each half of a 'Boston Yanks/Brooklyn Tigers' is a parent name in the merger year
        for n in c["names"]:
            if "/" in n["name"] and n["name"].count("/") == 1 and all(len(h.split()) > 1 for h in n["name"].split("/")):
                for h in n["name"].split("/"):
                    for y in range(n["first"], n["last"] + 1): parent_name_in_merger_year.setdefault((norm(h.strip()), y), c["id"])

    # ---------------------------------------------------------------- 6. the name cascade every source goes through
    name_year = collections.defaultdict(set); nick_year = collections.defaultdict(set)
    def index_names():
        name_year.clear(); nick_year.clear()
        for c in clubs:
            for n in c["names"]:
                for y in range(n["first"], n["last"] + 1):
                    name_year[(norm(n["name"]), y)].add(c["id"]); nick_year[(nickname(n["name"]), y)].add(c["id"])
            for s in c["strings"]:
                if s["kind"] == "beyond_archive" and s["source"] == "pfa_cell":
                    for y in range(s["first"], s["last"] + 1): name_year[(norm(s["string"]), y)].add(c["id"])
    index_names()
    def club_league(cid, y):
        for l in by_id[cid]["leagues"]:
            if l["first"] <= y <= l["last"]: return l["league"]
    def in_league(ids, y, league):
        if not league: return ids
        keep = {i for i in ids if fam(club_league(i, y), y) == fam(league, y)}
        return keep or ids
    def official_name(cid, y):
        return next((n["name"] for n in by_id[cid]["names"] if n["first"] <= y <= n["last"]), None)
    def archive_covers(league, y):
        f = fam(league, y)
        return any(fam(l, y) == f and y in ys for l, ys in league_years.items()) or any(
            c["origin"] == "archive" and fam(l["league"], y) == f and l["first"] <= y <= l["last"] for c in clubs for l in c["leagues"])
    # CORROBORATION: a name and a code one man holds for one league-year are one club. Read from the
    # plain base (rewrites and merges undone in memory) plus the merge pairing, exactly as
    # normalise_club_keys.py read it: after the rewrite nobody holds the printed name, and after the
    # merge the absorbed record is folded in under its rewritten key -- either shortcut empties the map.
    import apply_person_merges as AP, apply_club_keys as CKA
    base = json.load(open(AP.IDXP)); base.pop("_clubs", None)
    CKA.undo(base); AP.undo(base)                                       # undo reads the notes on the records, not the decisions file
    view = {}
    if os.path.exists(AP.MP):
        for d in json.load(open(AP.MP))["merges"]:
            c_, a_ = d["canonical_person"], d["absorbed_person"]
            ss = dict((base.get(c_) or {}).get("seasons") or {}); ss.update((base.get(a_) or {}).get("seasons") or {})
            view[c_] = {"seasons": ss}
    for pid, p in base.items():
        if pid not in view and isinstance(p, dict): view[pid] = p
    corroborated = collections.Counter()                                 # (norm(name), code) -> person-seasons holding both, any year
    for pid, p in view.items():
        by = collections.defaultdict(set)
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2); by[(lg, year_of(y))].add(club)
        for (lg, yr), cs in by.items():
            names = [x for x in cs if (x, yr) not in by_code_year]; codes = [x for x in cs if (x, yr) in by_code_year]
            for nm in names:
                for code in codes: corroborated[(norm(nm), code)] += 1
    def defect(nm, y):
        """The corroborated code for a printed name in a year the club existed under that code with the
        same city -- Ryan's ruling: a source defect is accepted only on corroboration, and the pair once
        corroborated is the source's habit (Coaching Tree calls Buffalo the Bisons in every year)."""
        cands = [(code, n) for (nm2, code), n in corroborated.items() if nm2 == norm(nm) and (code, y) in by_code_year
                 and city(official_name(by_code_year[(code, y)], y)) == city(nm)]
        if len({c for c, _ in cands}) == 1: return cands[0]
        if len(cands) > 1: unresolved["corroboration_conflicts"].append({"name": nm, "year": y, "codes": cands, "why": "the name is corroborated against two clubs of that city in one year"})
        return None

    def variant(a, b):
        """Two city strings that are one printed form of the same place: equal, initials, a prefix, or a slip of the pen."""
        if a == b: return True
        if not a or not b: return False
        return a.startswith(b) or b.startswith(a) or lev(a, b) <= 2
    def match(nm, y, league=None):
        """-> (club id, kind, extra) or (None, why, {}). Every path is year-scoped. A nickname alone never resolves a
        different city: 'Hollywood Bears' is not the Chicago Bears, and the table says so rather than guessing."""
        ids = in_league(name_year.get((norm(nm), y), set()), y, league)
        if len(ids) == 1: return next(iter(ids)), "official", {}
        if len(ids) > 1: return None, "ambiguous: more than one club under that name that year", {}
        if "/" in nm and not any(s["string"] == nm for c in clubs for s in c["strings"]):
            return None, "compound string: needs a ruling", {}
        if (norm(nm), y) in parent_name_in_merger_year:
            cid = parent_name_in_merger_year[(norm(nm), y)]
            return cid, "wrong_for_season", {"correct_name_then": official_name(cid, y), "note": "a parent's name in the year it played merged"}
        if "-" in nm:                                     # 'Brooklyn-New York Yankees', 'Chicago Cardinals-Pittsburgh Steelers'
            halves = [h.strip() for h in nm.split("-") if len(h.split()) > 1]
            found = {}
            for h in halves:
                cid, kind, extra = match(h, y, league)
                if cid: found[cid] = h
            if len(found) == 1:
                cid = next(iter(found)); return cid, "compound_printed_name", {"official_name_then": official_name(cid, y), "matched_on": f"the half '{found[cid]}' resolves; the other half does not name a second club that year"}
            if len(found) > 1: return None, f"compound string names two clubs that year ({', '.join(official_name(i, y) for i in found)}): needs a ruling", {}
        words = nm.split(); a = city(nm)
        ids = in_league(nick_year.get((nickname(nm), y), set()), y, league)
        if not ids and len(words) > 1:                                      # a slip in the nickname: 'Memphis Expess'
            ids = {i for (nk, yy), ss in nick_year.items() if yy == y and lev(nk, nickname(nm)) <= 1 for i in ss if city(official_name(i, y)) == a}
            ids = in_league(ids, y, league)
        if len(ids) == 1:
            cid = next(iter(ids)); off = official_name(cid, y); b = city(off)
            if variant(a, b) or (a and b and (initials(" ".join(words[:-1])) == b or initials(" ".join(off.split()[:-1])) == a)):
                return cid, "printed_name", {"official_name_then": off, "matched_on": "nickname; city is a variant spelling or abbreviation"}
            if any(norm(n["name"]) == norm(nm) for n in by_id[cid]["names"]):
                return cid, "wrong_for_season", {"correct_name_then": off, "matched_on": "the club's own name in another year"}
            d = defect(nm, y)                                                # corroboration outranks a nickname that happens to match elsewhere
            if d:
                cid2 = by_code_year[(d[0], y)]; off2 = official_name(cid2, y)
                return cid2, ("alias" if norm(off2) == norm(nm) else "wrong_for_season"), {"correct_name_then": off2, "matched_on": f"corroboration: {d[1]} person-seasons hold both this name and {d[0]}", "person_seasons": d[1]}
            return None, f"nickname matches {off} but the city differs: not resolved on a nickname alone", {}
        if len(ids) > 1:                                                     # 'New York Giants' 1921: Brickley Giants and Evansville Crimson Giants share the nickname; the city settles it
            by_city = [i for i in ids if variant(a, city(official_name(i, y)))]
            if len(by_city) == 1:
                cid = by_city[0]; off = official_name(cid, y)
                return cid, "printed_name", {"official_name_then": off, "matched_on": "nickname shared by two clubs that year; the city is a variant of one of them"}
            return None, "ambiguous: nickname shared by more than one club that year", {}
        cityonly = in_league({i for (n2, yy), ss in name_year.items() if yy == y for i in ss if norm(nm) and n2.startswith(norm(nm)) and n2 != norm(nm)}, y, league)
        cityonly = {i for i in cityonly if norm(nm) == norm(" ".join(official_name(i, y).split()[:-1]))}
        if len(cityonly) == 1 and len(words) <= 2:
            cid = next(iter(cityonly))
            if norm(nm) == norm(" ".join(official_name(cid, y).split()[:-1])):
                return cid, "printed_name", {"official_name_then": official_name(cid, y), "matched_on": "the source gave the city and left the nickname off"}
        d = defect(nm, y)
        if d:
            cid = by_code_year[(d[0], y)]; off = official_name(cid, y)
            return cid, ("alias" if norm(off) == norm(nm) else "wrong_for_season"), {"correct_name_then": off, "matched_on": f"corroboration: {d[1]} person-seasons hold both this name and {d[0]}", "person_seasons": d[1]}
        return None, "no club under that name that year", {}

    def add(cid, string, source, kind, league, y, y1=None, **extra):
        """Record a string on a club for the years [y, y1]. A range grows only where the
        new years TOUCH it: a string seen in 1942 and 1944 is two strings, not one that
        silently covers 1943 -- the year the Eagles' name belonged to the merged club."""
        c = by_id[cid]; y1 = y1 or y
        if kind not in ("beyond_archive", "club_without_a_season_that_year") and not (c["first"] <= y and y1 <= c["last"]):
            extra = {"role": kind, **extra}; kind = "beyond_archive"
        for s in c["strings"]:
            if s["string"] == string and s["source"] == source and s["kind"] == kind and s.get("league") == league \
                    and y <= s["last"] + 1 and y1 >= s["first"] - 1:
                s["first"] = min(s["first"], y); s["last"] = max(s["last"], y1); return
        c["strings"].append({"string": string, "source": source, "kind": kind, "league": league, "first": y, "last": y1, **extra})
    def refuse(source, string, league, y, why, **extra):
        unresolved["strings"].append({"source": source, "string": string, "league": league, "year": y, "why": why, **extra})

    # ---------------------------------------------------------------- 7. PFA: coach cells (and the promoted coaching_seasons keys, which are the same cells) and pre-1950 transactions
    pc = json.load(open(os.path.join(BASE, "build", "pfa-coaches.json")))
    cells = collections.defaultdict(set)                                # (league, code, printed) -> years
    for cl in pc["claims"]:
        if cl["predicate"] != "pfa.coaching_season": continue
        v = cl["value"]; cells[(v["league"], v["club"], clean_printed(v["club_as_printed"]))].add(int(v["year"]))
    for pid, p in IDX.items():
        for k, rows in (p.get("coaching_seasons") or {}).items():
            lg, y, c = k.split("|", 2)
            for r in rows: cells[(lg, c, clean_printed(r.get("printed_long") or ""))].add(year_of(y))
    pf = json.load(open(os.path.join(BASE, "build", "pfa-pre1950.json")))
    txs = collections.defaultdict(set)
    for cl in pf["claims"]:
        if cl["predicate"] != "pfa.transaction": continue
        m = re.match(r"^(\d{4}) (\S+) (\S+)$", cl["value"].get("team", ""))
        if m: txs[(m.group(3), m.group(2), clean_printed(cl["value"].get("season_context", "")))].add(int(m.group(1)))
    bx = json.load(open(os.path.join(BASE, "build", "pfa-boxscores.json")))
    bxs = collections.defaultdict(set)
    for cl in bx["claims"]:
        if cl["predicate"] == "pfa.game_score_by_quarter":
            for side in cl["value"]: bxs[(cl["subject"][1], side.get("club_code") or "", side["club"])].add(int(cl["subject"][2]))
        elif cl["predicate"] == "pfa.game_lineup":                     # the lineup tables print the club too, without a code
            g = cl["value"].get("game") or []
            if len(g) < 3: continue
            if cl["value"].get("club_as_printed") is None:            # the page's heading was not a club its score table names: unknown, counted
                unresolved["lineups_with_no_club"].append({"game": g[1:], "section_as_printed": cl["value"].get("section_as_printed"), "person": cl["subject"][1]}); continue
            bxs[(g[1], "", cl["value"]["club_as_printed"])].add(int(g[2]))
    last_held = {lg: max(ys) for lg, ys in league_years.items()}
    def beyond_archive(lg, y):
        f = fam(lg, y); return f in last_held and y > last_held[f]
    pfa_only = collections.defaultdict(set)                             # (code, printed) -> {(league, year)} with no archive club
    resolved_years = {}                                                 # (family, code, year) -> club ids, across the three PFA tables
    cell_resolved = {}                                                  # (league, code, printed, year) -> club id
    pending = []
    for label, table in (("pfa_cell", cells), ("pfa_transaction", txs), ("boxscore", bxs)):
        for (lg, code, pn), ys in table.items():
            for y in sorted(ys):
                cid, kind, extra = match(pn, y, lg)
                if cid:
                    if code: add(cid, code, label, "code", lg, y)
                    add(cid, pn, label, kind if kind != "official" else "printed_name", lg, y, **extra)
                    resolved_years.setdefault((fam(lg, y), code, y), set()).add(cid); cell_resolved[(lg, code, pn, y)] = cid
                else: pending.append((label, lg, code, pn, y, kind))
    for label, lg, code, pn, y, why in pending:                         # the source's own code continuity: the same code resolves to one club within three years
        near = {cid for (f2, c2, y2), cids in resolved_years.items() if code and (f2, c2) == (fam(lg, y), code) and abs(y2 - y) <= 3 for cid in cids}
        if len(near) == 1:
            cid = next(iter(near)); c = by_id[cid]
            has_segment = any(s["first"] <= y <= s["last"] for s in c["segments"])
            off = official_name(cid, y) if has_segment else None
            agrees = has_segment and (nickname(pn) == nickname(off) or city(pn) == city(off))
            own_name = any(norm(n["name"]) == norm(pn) for n in c["names"])
            if agrees or own_name or (beyond_archive(lg, y) and own_name):
                if has_segment: kind, extra = ("printed_name" if norm(off) == norm(pn) else "wrong_for_season"), {"correct_name_then": off}
                elif beyond_archive(lg, y): kind, extra = "beyond_archive", {"note": f"the archive's last held {fam(lg, y)} season is {last_held[fam(lg, y)]}; this string is recorded, no season is held"}
                elif c["first"] <= y <= c["last"]: kind, extra = "club_without_a_season_that_year", {"note": "the club is identified; it fielded no team that year"}
                else: kind = None
                if kind:
                    add(cid, code, label, "code", lg, y); add(cid, pn, label, kind, lg, y, matched_on="PFA code continuity: the same code resolves to this club within three years, and the name agrees", **extra)
                    cell_resolved[(lg, code, pn, y)] = cid; continue
        if beyond_archive(lg, y):
            hit = {c["id"] for c in clubs if c["origin"] == "archive" and any(norm(n["name"]) == norm(pn) and n["last"] == last_held[fam(lg, y)] for n in c["names"])}
            if len(hit) == 1:
                cid = next(iter(hit)); add(cid, code, label, "code", lg, y)
                add(cid, pn, label, "beyond_archive", lg, y, note=f"the archive's last held {fam(lg, y)} season is {last_held[fam(lg, y)]}; this string is recorded, no season is held", matched_on="the club's name in the archive's last held season")
                cell_resolved[(lg, code, pn, y)] = cid; continue
            if label != "boxscore": pfa_only[(code, pn)].add((lg, y)); continue
        if label != "boxscore" and not archive_covers(lg, y): pfa_only[(code, pn)].add((lg, y))
        else: refuse(label, f"{pn} [{code}]" if code else pn, lg, y, why, printed=pn, pfa_code=code)
    # PFA-only clubs: leagues and years the archive holds no club in at all. One club = one PFA code with one printed name over
    # consecutive years. A hole is a hole: the same code and name either side of one is reported, not bridged.
    for (code, pn), lys in sorted(pfa_only.items()):
        years = sorted({y for _, y in lys}); lg_by_year = collections.defaultdict(set)
        for lg, y in lys: lg_by_year[y].add(lg)
        run = [years[0]]
        for a, b in zip(years, years[1:]):
            if b == a + 1: run.append(b)
            else:
                unresolved["pfa_only_gaps"].append({"code": code, "name": pn, "earlier": [run[0], run[-1]], "later_from": b, "why": "same PFA code and name either side of a hole: two clubs until a ruling says otherwise"})
                _emit_pfa_only(clubs, by_id, by_code_year, anchor, code, pn, run, lg_by_year, beyond_archive); run = [b]
        _emit_pfa_only(clubs, by_id, by_code_year, anchor, code, pn, run, lg_by_year, beyond_archive)
        for lg, y in lys: cell_resolved[(lg, code, pn, y)] = next(cid for (sc, yy), cid in by_code_year.items() if yy == y and sc.startswith("PFA:") and sc.endswith(":" + code) and by_id[cid]["names"][0]["name"] == pn)
    index_names()

    # ---------------------------------------------------------------- 7a. leagues with no club map: clubs from club-season ATTESTATION
    # A league nobody swept has no codes in _clubs, so it had no clubs, so every string naming one refused --
    # 559 Arena strings and not one Arena club. The attestation (a printed name, a league, a year) is the club-season;
    # the men come from the transaction store and decide lineage exactly as everywhere else.
    ATT = DECL["LEAGUES_THE_ARCHIVE_HOLDS_NO_CLUB_MAP_FOR"]["attested_only_leagues"]
    mem = collections.defaultdict(set)                                   # (league, year, source code) -> pids
    mp = os.path.join(BASE, "build", "pfa-transaction-membership.json")
    if os.path.exists(mp):
        for cl in json.load(open(mp))["claims"]:
            v = cl.get("value")
            if not isinstance(v, str) or v.count("|") != 2 or cl["subject"][0] != "person": continue
            lg, y, code = v.split("|")
            if lg in ATT and y.isdigit(): mem[(lg, int(y), code)].add(cl["subject"][1])
    for lg, spec in sorted(ATT.items()):
        wf = os.path.join(BASE, "build", os.path.basename(spec["club_season_source"].split()[0]))
        if not os.path.exists(wf): unresolved["attested_leagues"].append({"league": lg, "why": f"club-season source {wf} not on disk"}); continue
        att = collections.defaultdict(set)                                # norm(name) -> years
        printed = collections.defaultdict(collections.Counter)            # norm(name) -> printed forms as the source wrote them
        for r in json.load(open(wf))["club_seasons"]:
            if r.get("league") != spec.get("club_season_league_token", lg) or not r.get("club_as_printed"): continue
            raw = r["club_as_printed"]
            key_form = re.sub(r"\s*\([^)]*\)\s*$", "", re.sub(r"^\((?:\d+|#)\)[-\s]*", "", raw).strip()).strip() or raw
            att[norm(key_form)].add(int(r["year"])); printed[norm(key_form)][raw] += 1
        runs_att = collections.defaultdict(list)                          # key -> [contiguous runs]
        for key, ys in sorted(att.items()):
            years = sorted(ys); run = [years[0]]
            for x, y2 in zip(years, years[1:]):
                if y2 == x + 1: run.append(y2)
                else: runs_att[key].append(run); run = [y2]
            runs_att[key].append(run)
        # the club's NAME is the printed form without the bracket seed and without Wikipedia's article
        # disambiguator -- but the disambiguator stays in the KEY, because it is what tells the two
        # Milwaukee Mustangs apart, and merging them would invent one club out of two.
        # The bracket seed ('(1) Arizona Rattlers', 'Chicago Rush(1)') and Wikipedia's article
        # disambiguator ('(arena football)', '(1994-2001)') are both stripped, for the key as well as the
        # name: measured on this store, every disambiguated form's years are a SUBSET of the bare name's,
        # so the disambiguator is an article title, not a second club. Where a name really does cover two
        # clubs the long hole between them is reported below, with the disambiguator as the evidence.
        def display(p):
            p = re.sub(r"^\((?:\d+|#)\)[-\s]*", "", p).strip()
            return re.sub(r"\s*\([^)]*\)\s*$", "", p).strip() or p
        name_of = {k: display(max(printed[k], key=lambda p: (printed[k][p], -len(p)))) for k in printed}
        # the men, by (year, city): PFA writes this league under CITY codes, so a club-season takes its
        # transactions only where exactly one attested club of that city played that year
        men_att = collections.defaultdict(set); code_of = {}
        for (l2, y, code), pids in sorted(mem.items()):
            if l2 != lg: continue
            hits = [k for k, rs in runs_att.items() for run in rs if y in run
                    and (initials(" ".join(name_of[k].split()[:-1])) == norm(code) or norm(" ".join(name_of[k].split()[:-1])).startswith(norm(code)))]
            hits = sorted(set(hits))
            if len(hits) == 1: men_att[(hits[0], y)] |= pids; code_of[(hits[0], y)] = code
            else: refuse("pfa_transaction", code, lg, y, ("ambiguous: " + str(len(hits)) + " attested clubs of that city that year" if hits else "no attested club of that city that year"), men=len(pids))
        # ONE CLUB PER NAME, its runs chained: a hole in the standings articles is a gap in the SOURCE, and the
        # same club under the same name either side of it is linked as resumed, with the men stated -- the archive
        # rule, applied here. A different name is a different club until the nickname AND the men carry.
        # THE ARCHIVE WINS WHERE IT HOLDS THE CLUB. Once a league's codes carry names in _clubs,
        # its clubs are ordinary archive clubs and the attestation is a STRING on them, not a
        # second club. Only years the archive holds no club of that name for are emitted here.
        emitted = {}
        for key, rs in sorted(runs_att.items(), key=lambda kv: kv[1][0][0]):
            nm = name_of[key]
            held_years = {y: next(iter(ids)) for y in sorted(att[key])
                          for ids in [in_league(name_year.get((norm(nm), y), set()), y, lg)] if len(ids) == 1}
            for y, cid_ in sorted(held_years.items()):
                for p2 in printed[key]:
                    add(cid_, p2, "wikipedia", "printed_name", lg, y,
                        note="league-season standings" + (" (a playoff seed, not part of the name)" if p2.startswith("(") else ""))
                if (key, y) in code_of: add(cid_, code_of[(key, y)], "pfa_transaction", "code", lg, y, men=len(men_att[(key, y)]))
            left = sorted(set(att[key]) - set(held_years))
            if not left:
                unresolved["attested_matched_to_an_archive_club"].append({"league": lg, "name": nm, "years": sorted(att[key]),
                    "club": sorted({c for c in held_years.values()})[0], "why": "the archive holds this club under its own code; the attestation is recorded as strings on it"})
                continue
            rs = []; run = [left[0]]
            for a_, b_ in zip(left, left[1:]):
                if b_ == a_ + 1: run.append(b_)
                else: rs.append(run); run = [b_]
            rs.append(run)
            first, last = rs[0][0], rs[-1][-1]
            cid = anchor_id(f"ARENA:{key}|{first}", nm, first)
            segs = [{"code": f"ARENA:{key}", "first": r[0], "last": r[-1],
                     "leagues": [{"league": lg, "first": r[0], "last": r[-1], "evidence": spec["club_season_source"].split(" (")[0]}]} for r in rs]
            for a_, b_ in zip(rs, rs[1:]):
                hole = b_[0] - a_[-1] - 1
                if hole >= 3:
                    dis = sorted({p for p in printed[key] if re.search(r"\([^)]*\)$", p)})
                    unresolved["attested_same_name_across_a_long_hole"].append(
                        {"league": lg, "name": nm, "earlier": [rs[0][0], a_[-1]], "later": [b_[0], rs[-1][-1]], "hole_years": hole,
                         "men_carried": len(men_att.get((key, a_[-1]), set()) & men_att.get((key, b_[0]), set())),
                         "wikipedia_disambiguator": dis,
                         "why": "held as ONE club: this source's standings are demonstrably incomplete (1997-2005 carry 0-2 clubs of a 14-19 club league), so a hole is not evidence the club did not play. "
                                "A ruling could split it -- Wikipedia's own disambiguator is the evidence where there is one."})
            links = [{"from": f"ARENA:{key}", "to": f"ARENA:{key}", "year": b_[0],
                      "why": f"the same club across a {b_[0] - a_[-1] - 1}-year hole in the standings articles (this source is incomplete: a hole is not an absence); "
                             + (f"{len(men_att.get((key, a_[-1]), set()) & men_att.get((key, b_[0]), set()))} men carried"
                                if men_att.get((key, a_[-1])) and men_att.get((key, b_[0])) else "no transactions either side to corroborate it")}
                     for a_, b_ in zip(rs, rs[1:])]
            c = {"id": cid, "origin": "attested_only", "first": first, "last": last, "segments": segs,
                 "names": [{"name": nm, "first": first, "last": last, "kind": "official", "source": "wikipedia-en"}],
                 "leagues": [{"league": lg, "first": first, "last": last, "evidence": "league-season standings"}],
                 "lineage": {"kind": "attested_only", "links": links, "merger_of": [], "merger_seasons": {}, "merged_into": {}},
                 "seasons_attested": left, "men_from_transactions": sum(len(men_att.get((key, y), ())) for y in left),
                 "strings": [{"string": nm, "source": "wikipedia", "kind": "printed_name", "league": lg, "first": first, "last": last}]}
            for p2, n2 in printed[key].items():
                if p2 != nm: c["strings"].append({"string": p2, "source": "wikipedia", "kind": "printed_name", "league": lg, "first": first, "last": last,
                                                  "note": "as the standings printed it" + (" (a playoff seed, not part of the name)" if p2.startswith("(") else " (a second spelling)")})
            for y in sorted(set(att[key]) - set(held_years)):
                if (key, y) in code_of:
                    c["strings"].append({"string": code_of[(key, y)], "source": "pfa_transaction", "kind": "code", "league": lg, "first": y, "last": y,
                                         "note": "PFA writes this league's clubs under city codes that collide with NFL codes; scoped to this league and year, never a segment code",
                                         "men": len(men_att[(key, y)])})
            clubs.append(c); by_id[cid] = c; emitted[key] = c
            for r in rs:
                for y in range(r[0], r[-1] + 1): by_code_year[(f"ARENA:{key}", y)] = cid
        # a move or a rename: the nickname carried into the next year AND the men carried
        for k1, c1 in sorted(emitted.items()):
            for k2, c2 in sorted(emitted.items()):
                if k1 == k2 or c2["first"] != c1["last"] + 1: continue
                n1, n2 = c1["names"][0]["name"], c2["names"][0]["name"]
                if nickname(n1) != nickname(n2): continue
                A_, B_ = men_att.get((k1, c1["last"]), set()), men_att.get((k2, c2["first"]), set())
                n, m = len(A_ & B_), min(len(A_), len(B_))
                if n >= CARRY_MIN and m and n / m >= CARRY_SHARE:
                    c1["lineage"]["links"].append({"from": f"ARENA:{k1}", "to": f"ARENA:{k2}", "year": c2["first"],
                                                   "why": f"relocation or rename: nickname carried into the next year and {n} of {m} men carried"})
                else:
                    unresolved["lineage_candidates"].append({"kind": "attested league: nickname carried, men NOT carried", "from": [n1, c1["last"]], "to": [n2, c2["first"]],
                                                             "men_carried": [n, m], "league": lg,
                                                             "why": "a nickname carrying into a new city is not a relocation until the men carry; this league moves every other season"})
        index_names()

    # ---------------------------------------------------------------- 7b. the fandom redirect survey (Fetching's, read from Dropbox; Ryan's ruling: a string source)
    FANDOM = os.path.expanduser("~/Library/CloudStorage/Dropbox/Football Archive/reports/2026-09-06-fandom-club-name-variants.json")
    if not os.path.exists(FANDOM): raise SystemExit(f"build_clubs: the fandom survey is missing at {FANDOM}")
    FD = json.load(open(FANDOM))
    club_names_all = collections.defaultdict(set)                       # norm(name) -> club ids bearing it in any year
    for c in clubs:
        for n in c["names"]: club_names_all[norm(n["name"])].add(c["id"])
    fd_counts = collections.Counter()
    for e in FD["variants"] + FD.get("prose_variants", []):
        canon, route, lg = e["canonical"], e.get("route", "redirect"), e.get("league")
        bare = re.sub(r"\s*\([^)]*\)\s*$", "", canon)                    # fandom's disambiguator: 'Cleveland (NFL)', 'Philadelphia Stars (football)'
        ids = club_names_all.get(norm(bare), set())
        if not ids:                                                      # a variant spelling of a name the archive holds: 'British Columbia Lions' / 'BC Lions'
            cand = {i for c2 in clubs for n in c2["names"] for i in [c2["id"]] if nickname(n["name"]) == nickname(bare) and variant(city(bare), city(n["name"]))}
            cand |= {i for c2 in clubs for n in c2["names"] for i in [c2["id"]] if nickname(n["name"]) == nickname(bare) and initials(" ".join(bare.split()[:-1])) == city(n["name"])}
            ids = cand
        matched_on = "the canonical name"
        if e.get("year"):                                                # the survey dates the entry: the year is binding, never a fallback
            ids = {i for i in ids if by_id[i]["first"] <= e["year"] <= by_id[i]["last"]}
            if not ids:                                                  # 'Los Angeles Wildcats' 1926 -> the one 1926 club nicknamed Wildcats; the survey itself says four names, one club
                ids = set(nick_year.get((nickname(bare), e["year"]), set())); matched_on = "the nickname, unique in the survey's year; the survey states the identity"
        if not ids:                                                      # the canonical is fandom's page title; try its variants as archive names
            via = {i for v in e["variants"] for i in club_names_all.get(norm(re.sub(r"\s*\([^)]*\)\s*$", "", v)), set())}
            if len(via) == 1: ids = via; matched_on = "a variant that is an archive name"
        if len(ids) > 1 and lg:                                          # the survey's league, mapped to the archive's
            fam_lg = {"Ohio": "APFA", "AFL-1926": "AFL", "AFL-1940": "AFL", "USFL": "USFL", "WFL": "WFL", "CFL": "CFL", "NFL": "NFL", "AAFC": "AAFC"}.get(lg, lg)
            ids = {i for i in ids if any(fam(l["league"], l["first"]) == fam_lg for l in by_id[i]["leagues"])} or ids
        if len(ids) != 1:
            fd_counts["canonical " + ("ambiguous" if ids else "not in the archive")] += 1
            refuse("fandom_redirect", canon, lg, e.get("year"), ("ambiguous: the canonical name belongs to more than one club" if ids else "the canonical name is no club the archive holds") + f"; {len(e['variants'])} variant(s) not attached: " + ", ".join(e["variants"]), route=route)
            continue
        cid = next(iter(ids)); c = by_id[cid]
        for v in e["variants"]:
            own = [n for n in c["names"] if norm(n["name"]) == norm(v)]
            if own:                                                      # the variant is a name the club bore: scoped to those years
                for n in own: add(cid, v, "fandom_redirect", "alias", None, n["first"], n["last"], route=route, years_from="the club's own name")
                fd_counts["variant = an official name"] += 1
            else:                                                        # the survey carries no year: scoped to the club's whole span, and says so
                for sg in c["segments"]:                                  # the years the club actually played, never a merger year it sat out
                    add(cid, v, "fandom_redirect", "alias", None, sg["first"], sg["last"], route=route, years_from="the club's seasons; the survey carries no years")
                fd_counts["variant scoped to the club span"] += 1
        own = [n for n in c["names"] if norm(n["name"]) == norm(bare)]
        if own:
            for n in own: add(cid, canon, "fandom_redirect", "printed_name", None, n["first"], n["last"], route="canonical", matched_on=matched_on, years_from="the club's own name")
        else:
            for sg in c["segments"]: add(cid, canon, "fandom_redirect", "printed_name", None, sg["first"], sg["last"], route="canonical", matched_on=matched_on)
    for e in FD.get("unverified_leads", []):
        unresolved["leads"].append({**e, "source": "fandom_redirect"})
    unresolved["fandom_survey"] = {"file": FANDOM, "entries": len(FD["variants"]) + len(FD.get("prose_variants", [])), **fd_counts}
    index_names()

    # ---------------------------------------------------------------- 8. nflverse abbreviations, by the men who hold both that year
    nv = json.load(open(os.path.join(BASE, "build", "nflverse-rosters.json")))
    men_codes = collections.defaultdict(set)
    for (y, code), pids in men_at.items():
        if league_at(code, y)[0] not in ("NFL", "APFA", "AAFC", "AFL"): continue
        for pid in pids: men_codes[(pid, y)].add(code)
    co = collections.defaultdict(collections.Counter)
    for cl in nv["claims"]:
        if not cl["predicate"].endswith("roster_membership") or not isinstance(cl["value"], str) or "|" not in cl["value"]: continue
        y, ab = cl["value"].split("|", 1); y = int(y)
        for code in men_codes.get((cl["subject"][1], y), ()): co[(ab, y)][code] += 1
    for (ab, y), cnt in co.items():
        (code, n), second = cnt.most_common(1)[0], (cnt.most_common(2)[1][1] if len(cnt) > 1 else 0)
        if (n >= 3 and n >= 2 * second or n >= 10 and n >= 1.5 * second) and (code, y) in by_code_year:
            add(by_code_year[(code, y)], ab, "nflverse", "code", None, y, corroborated_by=f"{n} of {sum(cnt.values())} men that year")
        else: refuse("nflverse", ab, None, y, f"not corroborated: {n} of {sum(cnt.values())} NFL men point at {code}, {second} at the runner-up")
    nv_years = collections.defaultdict(set)
    for cl in nv["claims"]:
        if cl["predicate"].endswith("roster_membership") and isinstance(cl["value"], str) and "|" in cl["value"]:
            y, ab = cl["value"].split("|", 1); nv_years[ab].add(int(y))
    for ab, ys in nv_years.items():
        for y in sorted(ys):
            if (ab, y) not in co: refuse("nflverse", ab, None, y, f"beyond the archive's last held NFL season ({last_held['NFL']})" if y > last_held["NFL"] else "no man on that nflverse roster holds an NFL, AAFC or AFL season key that year")

    # ---------------------------------------------------------------- 9. Coaching Tree and media-guide stint clubs
    for label, fn in (("coaching_tree", "coaches.json"), ("media_guide", "assistants.json")):
        st = json.load(open(os.path.join(BASE, "build", fn)))
        pairs = collections.defaultdict(set)
        for cl in st["claims"]:
            if cl["subject"][0] == "stint": pairs[cl["subject"][2]].add(year_of(cl["subject"][3]))
        for nm, ys in pairs.items():
            for y in sorted(ys):
                if (nm, y) in by_code_year: add(by_code_year[(nm, y)], nm, label, "code", None, y); continue
                cid, kind, extra = match(nm, y)
                if cid: add(cid, nm, label, kind if kind != "official" else "alias", None, y, **extra)
                else: refuse(label, nm, None, y, kind)

    # ---------------------------------------------------------------- 11. every season-key token that is not a code, and every coaching-season key
    # Season keys are read from the plain base (rewrites undone, merges undone, then the merge pairing): the
    # index on disk holds the NORMALISED keys, and the table must record what the sources printed.
    for pid, p in list(view.items()) + [(pid, p) for pid, p in IDX.items()]:
        for k in p.get("seasons") or {}:
            lg, y, c = k.split("|", 2); yr = year_of(y)
            if (c, yr) in by_code_year: continue
            src = "season_key:" + lg if lg in PSEUDO else "season_key"
            cid, kind, extra = match(c, yr, None if lg in PSEUDO else lg)
            if cid: add(cid, c, src, kind if kind != "official" else "alias", None if lg in PSEUDO else lg, yr, **extra)
            else: refuse(src, c, lg, yr, kind)
        for k, rows in (p.get("coaching_seasons") or {}).items():
            lg, y, c = k.split("|", 2); yr = year_of(y)
            for r in rows:
                pn = clean_printed(r.get("printed_long") or "")
                if (lg, c, pn, yr) not in cell_resolved: refuse("coaching_season_key", f"{pn} [{c}]", lg, yr, "the PFA cell behind this coaching season did not resolve", printed=pn, pfa_code=c)

    # ---------------------------------------------------------------- 12. conflicts and archive gaps the table makes visible
    owners = collections.defaultdict(set)
    for c in clubs:
        for s in c["strings"]:
            if s["kind"] == "code" or s.get("role") == "code":
                for y in range(s["first"], s["last"] + 1): owners[(s["source"], s.get("league"), s["string"], y)].add(c["id"])
    for (source, lg, code, y), ids in sorted(owners.items()):
        if len(ids) < 2: continue
        carry = {}
        for cid in ids:
            carry[cid] = sum(1 for s_ in by_id[cid]["strings"] if s_["source"] == source and s_["string"] == code and (s_["kind"] == "code" or s_.get("role") == "code")
                             for yy in range(s_["first"], s_["last"] + 1) if yy != y)
        keep = [cid for cid, n in carry.items() if n == max(carry.values())]
        if len(keep) == 1 and max(carry.values()) > 0:                      # the code belongs to the club that carries it in other years; the other cell misprinted it
            for cid in ids:
                if cid == keep[0]: continue
                for s_ in by_id[cid]["strings"]:
                    if s_["source"] == source and s_["string"] == code and s_.get("league") == lg and s_["first"] <= y <= s_["last"] and (s_["kind"] == "code" or s_.get("role") == "code"):
                        s_["kind"] = "code_misprinted"; s_.pop("role", None)
                        s_["note"] = f"the source prints this club under code {code} in {y}, but {code} is {by_id[keep[0]]['id']} in every other year; kept as printed, not a code"
            unresolved["code_conflicts"].append({"source": source, "league": lg, "code": code, "year": y, "clubs": sorted(ids), "settled": keep[0],
                                                 "why": f"one source code named two clubs in one year; settled by continuity ({carry[keep[0]]} other years on {keep[0]}), the other entry recorded as code_misprinted"})
        else:
            unresolved["code_conflicts"].append({"source": source, "league": lg, "code": code, "year": y, "clubs": sorted(ids), "why": "one source code names two clubs in one year; no continuity settles it"})
    same = collections.defaultdict(set)
    for c in clubs:
        for n in c["names"]:
            for y in range(n["first"], n["last"] + 1): same[(norm(n["name"]), y)].add(c["id"])
    seen_pairs = set()
    for (nm, y), ids in sorted(same.items()):
        if len(ids) > 1 and (nm, tuple(sorted(ids))) not in seen_pairs:
            seen_pairs.add((nm, tuple(sorted(ids)))); unresolved["same_name_same_year"].append({"name": nm, "year": y, "clubs": sorted(ids), "why": "two clubs bear one name in one year; a lookup on the name alone is ambiguous there"})
    pending = collections.Counter(); pending_why = {}                   # code-years whose men sit in a build file the index did not take in
    for fn in ("afl-1926.json", "nfl-1934-cincinnati.json"):
        fp = os.path.join(BASE, "build", fn)
        if not os.path.exists(fp): continue
        for cl in json.load(open(fp))["claims"]:
            sub = cl["subject"]
            if sub[0] != "stint" or len(sub) != 4 or "roster_membership" not in cl["predicate"]: continue
            builder_shape = isinstance(sub[1], str) and sub[1].startswith("P_")     # build_person_index reads ['stint', person, club, season]
            key = (sub[1], int(sub[3])) if builder_shape else (sub[2], int(sub[3]))
            pending[key] += 1
            pending_why[key] = (f"{fn}: stint subjects are [stint, person, club, season]; the index will hold them after a rebuild" if builder_shape
                                else f"{fn}: stint subjects are [stint, league, code, year] with the person in the value; build_person_index reads [stint, person, club, season] and skips them -- the file's shape, not a rebuild, is what stands between these men and the index")
    this_year = 2026
    for c in clubs:
        if c["origin"] != "archive": continue
        for s in c["segments"]:
            for y in range(s["first"], s["last"] + 1):
                if men_at.get((y, s["code"])): continue
                lg = league_at(s["code"], y)[0]
                if (s["code"], y) in pending: why = f"{pending[(s['code'], y)]} person-seasons held in build/{pending_why[(s['code'], y)]}"
                elif y in s.get("dark_years", []) or (lg and y in dark.get(lg, set())): why = "league did not play that season; StatsCrew page only"
                elif y >= this_year: why = "future season"
                elif f"{s['code']}|{y}" in DECL.get("KNOWN_EMPTY_CODE_YEARS", {}): why = DECL["KNOWN_EMPTY_CODE_YEARS"][f"{s['code']}|{y}"]
                elif lg in ("NFL", "APFA") and y > 1945: why = "a modern NFL season with no men held: not yet explained"
                else: why = "no roster held for this club-season"
                unresolved["archive_code_years_without_players"].append({"club": c["id"], "code": s["code"], "year": y, "name": official_name(c["id"], y), "why": why})
    # ---------------------------------------------------------------- 13. collapse refusals to one row per string, sort, count, write
    coll = {}
    for r in unresolved["strings"]:
        k = (r["source"], r["string"], r.get("league"), r["why"])
        e = coll.setdefault(k, {kk: v for kk, v in r.items() if kk != "year"} | {"years": []})
        if r.get("year") is not None: e["years"].append(r["year"])
    unresolved["strings"] = sorted(({**{kk: v for kk, v in e.items() if kk != "years"}, "first": min(e["years"]) if e["years"] else None,
                                     "last": max(e["years"]) if e["years"] else None, "n_years": len(e["years"])} for e in coll.values()),
                                   key=lambda r: (r["source"], -(r["n_years"] or 0), r["string"]))
    for c in clubs: c["strings"].sort(key=lambda s: (s["source"], s["first"], s["string"]))
    clubs.sort(key=lambda c: (c["first"], c["id"]))
    ids = collections.Counter(c["id"] for c in clubs)
    if any(n > 1 for n in ids.values()): raise SystemExit(f"duplicate club ids: {[i for i, n in ids.items() if n > 1]}")
    codeless = collections.Counter()
    for pid, p in view.items():
        for k in p.get("seasons") or {}:
            lg, y, c = k.split("|", 2); yr = year_of(y)
            if lg in PSEUDO or (c, yr) in by_code_year: continue
            if not any(norm(c) == norm(n["name"]) for cl in clubs for n in cl["names"]): codeless[(lg, c)] += 1
    for (lg, c), n in sorted(codeless.items(), key=lambda x: -x[1])[:400]:
        unresolved["index_code_seasons_with_no_name"].append({"league": lg, "code": c, "person_seasons": n,
            "why": "the index holds this club-season but nothing names the club: no _clubs entry and no club_name claim. A club needs a name before the table can hold it."})

    # ---------------------------------------------------------------- per-league census: clubs held vs strings refused
    # Arena had 559 strings refusing and not one club, and it took a league-by-league look to see it. This is
    # that look, computed on every build: a league with sources naming it and NO club in the table is the shape.
    per_league = {}
    seen_lg = collections.Counter()
    mem_lg = collections.Counter()
    if os.path.exists(mp):
        for cl in json.load(open(mp))["claims"]:
            v = cl.get("value")
            if isinstance(v, str) and v.count("|") == 2: mem_lg[v.split("|")[0]] += 1
    for c in clubs:
        for l in c["leagues"]:
            if l["league"]: seen_lg[l["league"]] += 0
    for lg in set(seen_lg) | set(mem_lg) | {r.get("league") for r in unresolved["strings"] if r.get("league")} | set(league_years):
        if not lg or lg in PSEUDO or (lg in FAMILY and FAMILY[lg] in set(seen_lg) | set(mem_lg) | set(league_years)): continue
        kin = {lg} | {k for k, v in FAMILY.items() if v == lg}
        held = [c for c in clubs if any(l["league"] in kin for l in c["leagues"])]
        ref = [r for r in unresolved["strings"] if r.get("league") in kin]
        per_league[lg] = {"clubs": len(held), "club_seasons": sum(len(range(s["first"], s["last"] + 1)) for c in held for s in c["segments"] if any(l["league"] == lg for l in s["leagues"])),
                          "family": sorted(kin - {lg}) or None,
                          "strings": sum(1 for c in clubs for s in c["strings"] if s.get("league") in kin),
                          "strings_refused": len(ref), "lookups_refused": sum(r.get("n_years") or 1 for r in ref),
                          "refused_why": dict(collections.Counter(r["why"].split(":")[0][:60] for r in ref)),
                          "membership_rows_in_transactions": sum(mem_lg.get(k, 0) for k in kin),
                          "index_seasons": sum(len(league_years.get(k, ())) for k in kin),
                          "ZERO_CLUBS": len(held) == 0}
    counts = {"mergers_declared": len(DECL["MERGERS"]["rulings"]), "clubs": len(clubs), "archive_clubs": sum(1 for c in clubs if c["origin"] == "archive"), "pfa_only_clubs": sum(1 for c in clubs if c["origin"] == "pfa_only"), "pfa_only_beyond_frontier": sum(1 for c in clubs if c.get("beyond_the_archive_frontier")),
              "segments": sum(len(c["segments"]) for c in clubs), "chains": sum(1 for c in clubs if len(c["segments"]) > 1),
              "links": sum(len(c["lineage"]["links"]) for c in clubs), "mergers": sum(1 for c in clubs if c["lineage"]["merger_of"]),
              "names": sum(len(c["names"]) for c in clubs), "strings": sum(len(c["strings"]) for c in clubs),
              "strings_by_source": dict(collections.Counter(s["source"] for c in clubs for s in c["strings"])),
              "strings_by_kind": dict(collections.Counter(s["kind"] for c in clubs for s in c["strings"])),
              "wrong_for_season": sum(1 for c in clubs for s in c["strings"] if s["kind"] == "wrong_for_season"),
              "unresolved_strings": len(unresolved["strings"]), "unresolved_lookups": sum(r["n_years"] or 1 for r in unresolved["strings"]),
              "unresolved_by_source": dict(collections.Counter(r["source"] for r in unresolved["strings"])),
              "lineage_splits": len(unresolved["lineage_splits"]), "lineage_candidates": len(unresolved["lineage_candidates"]),
              "code_conflicts": len(unresolved["code_conflicts"]), "archive_code_years_without_players": len(unresolved["archive_code_years_without_players"]),
              "same_name_same_year": len(unresolved["same_name_same_year"]), "attested_matched_to_an_archive_club": len(unresolved["attested_matched_to_an_archive_club"]), "index_code_seasons_with_no_name": len(unresolved["index_code_seasons_with_no_name"]), "attested_clubs": sum(1 for c in clubs if c["origin"] == "attested_only"),
              "attested_same_name_across_a_long_hole": len(unresolved["attested_same_name_across_a_long_hole"]), "lineups_with_no_club": len(unresolved["lineups_with_no_club"]), "club_names_not_yet_in_the_index": len(unresolved["club_names_not_yet_in_the_index"]), "fandom_survey": dict(unresolved.get("fandom_survey", {})), "pfa_only_gaps": len(unresolved["pfa_only_gaps"]), "silenced_code_years": len(unresolved["silenced_code_years"]),
              "leagues": sorted({l["league"] for c in clubs for l in c["leagues"] if l["league"]}), "code_years": len(by_code_year),
              "leagues_with_zero_clubs": sorted(lg for lg, v in per_league.items() if v["ZERO_CLUBS"])}
    out = {"declaration": "declarations/clubs.json", "sources": sorted({s["source"] for c in clubs for s in c["strings"]}),
           "clubs": clubs, "per_league": dict(sorted(per_league.items(), key=lambda kv: -kv[1]["membership_rows_in_transactions"])), "unresolved": dict(unresolved), "id_anchor": dict(sorted(anchor.items())), "counts": counts}
    if write:
        json.dump(out, open(TABLE, "w"), indent=1, ensure_ascii=False); print("wrote", TABLE)
    print(json.dumps(counts, indent=1))
    return out


def _emit_pfa_only(clubs, by_id, by_code_year, anchor, code, pn, run, lg_by_year, beyond_archive):
    segcode = f"PFA:{code}"
    if any((segcode, y) in by_code_year for y in run): segcode = f"PFA:{sorted(lg_by_year[run[0]])[0]}:{code}"
    key = f"{segcode}|{run[0]}"
    cid = anchor.get(key) or f"club-{slug(pn)}-{run[0]}"
    for suffix in ("", f"-{slug(code)}", f"-{slug(code)}-" + "-".join(sorted(l for ls in lg_by_year.values() for l in ls)).lower()):
        if cid + suffix not in by_id: cid = cid + suffix; break
    else: raise SystemExit(f"cannot give {pn} {run[0]} a unique id")
    anchor[key] = cid
    leagues = []
    for y in run:
        lgs = sorted(lg_by_year.get(y, set())) or [leagues[-1]["league"] if leagues else None]
        for lg in lgs:
            if leagues and leagues[-1]["league"] == lg and leagues[-1]["last"] >= y - 1: leagues[-1]["last"] = y
            else: leagues.append({"league": lg, "first": y, "last": y, "evidence": "PFA prints no league: an independent" if lg == "" else "PFA coaching cell or transaction; the archive holds no club in this league that year"})
    seg = {"code": segcode, "first": run[0], "last": run[-1], "leagues": leagues, "pfa_code": code}
    c = {"id": cid, "origin": "pfa_only", "first": run[0], "last": run[-1], "segments": [seg],
         "names": [{"name": pn, "first": run[0], "last": run[-1], "kind": "official", "source": "pro-football-archives"}],
         "leagues": [dict(l) for l in leagues],
         "beyond_the_archive_frontier": all(beyond_archive(l, y) for y in run for l in lg_by_year.get(y, ())),
         "lineage": {"kind": "pfa_only", "links": [], "merger_of": [], "merger_seasons": {}, "merged_into": {}},
         "strings": []}
    for l in leagues:
        c["strings"].append({"string": code, "source": "pfa_cell", "kind": "code", "league": l["league"], "first": l["first"], "last": l["last"]})
        c["strings"].append({"string": pn, "source": "pfa_cell", "kind": "printed_name", "league": l["league"], "first": l["first"], "last": l["last"]})
    clubs.append(c); by_id[cid] = c
    for y in run: by_code_year[(segcode, y)] = cid


if __name__ == "__main__":
    main()
