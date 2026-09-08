"""Ingest Wikipedia league-season and team-season articles: standings, head coaches,
club-season records, results, and every man the archive does not hold.

Rules are read from declarations/wikipedia-seasons.json, never duplicated here.

  - every fact carries source_record (article), revision_id and timestamp, and `cited`
  - club strings resolve through build/clubs.json; unresolved strings are kept as printed
  - head coaches match on club-year evidence, or unique name + coaching history;
    anything else is a LEAD and produces no claims. Nothing is promoted.
  - disagreements with the archive's head coaches are HELD, both sides, counted by league
  - standings and results have no archive counterpart; recorded as new facts

WHAT THE FIRST DRY RUN TAUGHT (08:08): a wikitable cell's attributes were split from
its value at the LAST '|', which sits inside {{Abbr|W|Wins}} and [[..|Name]]; the split
is now at the first '|' outside braces and brackets. Templates are looked up by a
normalised title because articles transclude '...Standings' and the cache holds the
redirect target '...standings'. Headers nest {{nowrap|{{Abbr|W|Wins}}}}; the AAF table
carries one 'W–L' column.

  python3 src/ingest_wikipedia_seasons.py [--write] [--league ARENA,CFL] [--out DIR]
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
from clubs import Clubs
CACHE = os.path.expanduser("~/Documents/pgm3-sources/wiki_cache")
ENUM = os.path.join(BASE, "build-reports", "wikipedia-season-articles.json")
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia-seasons.json"), encoding="utf-8"))
ERA_CUT = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json")))["IDENTITY"]["era_cut"]
MARKS = ("wikipedia league/team season", "wikipedia standings templates")

REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
LINK = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")
TPL_KEEP = re.compile(r"\{\{\s*(?:Abbr|abbr|Tooltip|tooltip|nowrap|Nowrap|Nobold|nobold)\s*\|\s*([^|{}]*)(?:\|[^{}]*)?\}\}")
TPL_ANY = re.compile(r"\{\{[^{}]*\}\}")
REC = re.compile(r"(\d{1,2})\s*[–\-—]\s*(\d{1,2})(?:\s*[–\-—]\s*(\d{1,2}))?")
SCORE = re.compile(r"'*\s*([WLT])\s*'*\s*,?\s*(\d{1,3})\s*[–\-—]\s*(\d{1,3})")
YEAR = re.compile(r"\b(19[0-9]{2}|20[0-9]{2})\b")


def nk(s):
    s = re.sub(r"\(.*?\)", " ", str(s or ""))
    return re.sub(r"[^a-z]", "", s.lower())


def ntitle(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().lower()


def plain(v):
    """Wikitext value -> plain text. Keeps a `cited` flag separately (see cited())."""
    v = REF.sub("", v or "")
    v = LINK.sub(lambda m: (m.group(2) if m.group(2) is not None else m.group(1)), v)
    for _ in range(4):                                  # innermost first: {{nowrap|{{Abbr|W|Wins}}}}
        v2 = TPL_KEEP.sub(r"\1", v)
        if v2 == v: break
        v = v2
    v = re.sub(r"<br\s*/?>", " ; ", v, flags=re.I)
    for _ in range(3):
        v2 = TPL_ANY.sub("", v)
        if v2 == v: break
        v = v2
    v = re.sub(r"<[^>]+>", "", v)
    v = v.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", v).strip(" ;")


def cited(raw):
    return bool(re.search(r"<ref", raw or "", re.I))


def _strip_attrs(c):
    """'style="..."| value' -> 'value', splitting at the FIRST '|' outside {{ }} and [[ ]]."""
    depth_b = depth_l = 0
    for i, ch in enumerate(c):
        if c.startswith("{{", i): depth_b += 1
        elif c.startswith("}}", i): depth_b = max(0, depth_b - 1)
        elif c.startswith("[[", i): depth_l += 1
        elif c.startswith("]]", i): depth_l = max(0, depth_l - 1)
        elif ch == "|" and depth_b == 0 and depth_l == 0:
            head = c[:i]
            if re.search(r"=|^\s*(align|style|colspan|rowspan|scope|width|class|bgcolor)\b", head, re.I):
                return c[i + 1:].strip()
            return c
    return c


def infobox(text):
    m = re.search(r"\{\{\s*Infobox[^\n]*\n(.*?)\n\}\}", text, re.S)
    if not m: return {}, None
    kind = re.search(r"\{\{\s*Infobox\s*([^\n|]*)", text).group(1).strip().lower()
    params, cur, buf = {}, None, []
    for line in m.group(1).split("\n"):
        pm = re.match(r"^\s*\|\s*([A-Za-z_][A-Za-z0-9_ \-]*?)\s*=(.*)$", line)
        if pm:
            if cur: params[cur] = "\n".join(buf)
            cur, buf = pm.group(1).strip().lower(), [pm.group(2)]
        elif cur: buf.append(line)
    if cur: params[cur] = "\n".join(buf)
    return params, kind


def tables(text):
    """Every wikitable as a list of rows, each row a list of raw cells (attributes stripped)."""
    out = []
    for m in re.finditer(r"\{\|(.*?)\n\|\}", text, re.S):
        rows, cur = [], []
        for line in m.group(1).split("\n"):
            s = line.strip()
            if s.startswith("|-"):
                if cur: rows.append(cur); cur = []
            elif s.startswith("|+"):
                continue
            elif s.startswith("!") or s.startswith("|"):
                body = s[1:]
                cells = re.split(r"!!|\|\|", body) if s.startswith("!") else re.split(r"\|\|", body)
                for c in cells: cur.append(_strip_attrs(c.strip()))
        if cur: rows.append(cur)
        out.append(rows)
    return out


def coach_names(raw):
    v = REF.sub("", raw or "")
    v = re.sub(r"<br\s*/?>", ";", v, flags=re.I)
    v = LINK.sub(lambda m: (m.group(2) if m.group(2) is not None else m.group(1)), v)
    v = TPL_ANY.sub("", v); v = re.sub(r"<[^>]+>", "", v).replace("'''", "")
    v = re.sub(r"\(.*?\)", "", v)
    names = []
    for part in re.split(r";|,|&| and |/|\n", v):
        p = part.strip(" *")
        if 3 <= len(p) <= 40 and re.search(r"[A-Za-z]", p) and not re.search(r"interim|vacant|none|unknown|tbd", p, re.I):
            names.append(re.sub(r"\s+", " ", p))
    return names


# ------------------------------------------------------------------ standings ---
def _int(x):
    try: return int(re.sub(r"[^\d\-]", "", str(x))) if x not in (None, "") else None
    except Exception: return None


def standings_from_sports_table(block):
    """{{#invoke:sports table|main|...}} -> rows. Parameters sit several to a line
    ('| team1 = EDM | name_EDM = [[..|Edmonton Eskimos]]| status_EDM = CQ'); names carry
    digits (team1) and values carry '|' inside [[links]]."""
    P = {}
    for m in re.finditer(r"\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*((?:\[\[[^\]]*\]\]|\{\{[^{}]*\}\}|[^|\n])*)", block):
        P[m.group(1).strip()] = m.group(2).strip()
    title = plain(P.get("title", ""))
    rows = []
    for k, v in P.items():
        if re.match(r"team\d+$", k):
            code = v.strip()
            if not code: continue
            name = plain(P.get(f"name_{code}", code))
            g = lambda f: P.get(f"{f}_{code}")
            rows.append({"club_as_printed": name, "division": title or None,
                         "w": _int(g("win")), "l": _int(g("loss")), "t": _int(g("draw")),
                         "pf": _int(g("pf")), "pa": _int(g("pa")), "cited": cited(block)})
    return rows


HEAD_SYN = {"WINS": "W", "W": "W", "LOSSES": "L", "L": "L", "TIES": "T", "T": "T", "PF": "PF", "PA": "PA",
            "POINTS FOR": "PF", "POINTS AGAINST": "PA", "W–L": "W–L", "W–L–T": "W–L–T", "RECORD": "W–L"}


def standings_from_table(rows, division=None):
    """A wikitable whose header has W and L (or Wins/Losses, or one W–L column) -> rows.
    The FIRST Wins/Losses pair is the overall record (a second pair is the division
    record). A full-width row inside the table ('Eastern Division') becomes the
    division; a leading numeric cell is a rank, not a team."""
    if not rows: return []
    hdr = None
    for i, r in enumerate(rows[:5]):
        cells = [HEAD_SYN.get(plain(c).upper().replace("—", "–").replace("-", "–"), None) for c in r]
        if ("W" in cells and "L" in cells) or ("W–L" in cells) or ("W–L–T" in cells): hdr = (i, cells); break
    if not hdr: return []
    hi, cells = hdr
    col = {}
    for j, c in enumerate(cells):
        if c and c not in col: col[c] = j                                 # first occurrence = overall
    wl = col.get("W–L", col.get("W–L–T"))
    out, div = [], division
    for r in rows[hi + 1:]:
        if len(r) == 1 and plain(r[0]) and not re.search(r"\d", plain(r[0])):
            div = plain(r[0]); continue
        if len(r) < 2: continue
        cells_p = [plain(c) for c in r]
        off = 1 if re.fullmatch(r"\d{1,2}\.?", cells_p[0] or "") else 0     # rank column
        team = cells_p[off] if off < len(cells_p) else ""
        team = re.sub(r"^\(?[a-z*]{1,3}\)?[-–]\s*|^\([a-z]\)\s*", "", team).strip()   # y-, x-, (e), (x) clinch markers
        if not team or team.upper() in ("TEAM", "CLUB") or re.fullmatch(r"[\d.–\-]+", team): continue
        def at(k):
            j = col.get(k); j = (j + off) if j is not None else None
            return _int(r[j]) if j is not None and j < len(r) else None
        if wl is not None and (wl + off) < len(r):
            m = REC.search(cells_p[wl + off])
            w, l, t = (int(m.group(1)), int(m.group(2)), (int(m.group(3)) if m.group(3) else None)) if m else (None, None, None)
        else:
            w, l, t = at("W"), at("L"), at("T")
        if w is None or l is None: continue
        out.append({"club_as_printed": team, "division": div, "w": w, "l": l, "t": t,
                    "pf": at("PF"), "pa": at("PA"), "cited": any(cited(c) for c in r)})
    return out


def results_from_tables(tbls):
    games = []
    for rows in tbls:
        if not rows: continue
        hcells = [plain(c).lower() for c in rows[0]]
        if not any("opponent" in c for c in hcells): continue
        if not any(re.search(r"result|score|final", c) for c in hcells): continue
        for r in rows[1:]:
            txt = " || ".join(r)
            sm = SCORE.search(plain(txt)) or SCORE.search(txt)
            opp = None
            for c in r:
                pc = plain(c)
                if re.search(r"\bat\b|\bvs\.?\b|[A-Z][a-z]+ [A-Z]", pc) and not SCORE.search(pc) and not re.match(r"^\d", pc) and len(pc) > 3:
                    opp = pc; break
            if not sm or not opp: continue
            games.append({"week": plain(r[0]) if r else None,
                          "opponent_as_printed": re.sub(r"^(at|vs\.?)\s+", "", opp).strip(),
                          "home": not re.match(r"^at\b", opp), "result": sm.group(1),
                          "score_for": int(sm.group(2)), "score_against": int(sm.group(3)), "cited": cited(txt)})
    return games


# ------------------------------------------------------------------ main -----------
def load_cache():
    pages, bynorm = {}, {}
    for f in glob.glob(CACHE + "/*.json"):
        try: d = json.load(open(f))
        except Exception: continue
        if not any(m in str(d.get("_source", "")) for m in MARKS): continue
        for pg in (d.get("query") or {}).get("pages", {}).values():
            if "missing" in pg or "revisions" not in pg: continue
            rev = pg["revisions"][0]
            txt = ((rev.get("slots") or {}).get("main") or {}).get("*") or rev.get("*") or ""
            pages[pg["title"]] = {"text": txt, "revid": rev.get("revid"), "timestamp": rev.get("timestamp")}
            bynorm[ntitle(pg["title"])] = pg["title"]
    return pages, bynorm


def people(idx):
    byname = collections.defaultdict(list); keys = {}
    for pid, v in idx.items():
        if not isinstance(v, dict) or not v.get("name"): continue
        byname[nk(v["name"])].append(pid)
        keys[pid] = set((v.get("seasons") or {}).keys())
    return byname, keys


def match_coach(name, year, code, byname, keys):
    """-> (pid, method) or (None, why)."""
    cands = byname.get(nk(name), [])
    if not cands: return None, "no man of that name in the archive"
    yr = f"y{year}"
    if code:
        hit = [p for p in cands if any(k.split("|")[1:3] == [yr, code] for k in keys[p])]
        if len(hit) == 1: return hit[0], "club-year"
        if len(hit) > 1: return None, "more than one man of that name at that club-year"
    if int(year) < ERA_CUT: return None, "pre-era-cut: no club-year evidence"
    if len(cands) == 1 and any(k.startswith("COACHES|") for k in keys[cands[0]]): return cands[0], "name-unique+coach-history"
    if len(cands) == 1: return None, "name unique but no coaching history: not identity"
    return None, "ambiguous: several men of that name, none at that club-year"


class ClubResolver:
    """Clubs.resolve with the lookup string normalised and the PRINTED string untouched:
    a trailing ' (2022)' league disambiguator and '(e) '/'(x) ' clinch markers are
    Wikipedia typography, not club names. Refusals still land in the wrapped census."""
    def __init__(self, C): self.C = C
    def resolve(self, s, year, league=None, source=None):
        r = self.C.resolve(s, year, league, source)
        if r: return r
        s2 = re.sub(r"\s*\((19|20)\d{2}\)\s*$", "", s); s2 = re.sub(r"^\([a-z]\)\s*", "", s2).strip()
        if s2 and s2 != s:
            r = self.C.resolve(s2, year, league, source)
            if r:
                k = (source or "?", league or "?", str(year), s, "no club under that string that year")
                self.C.refused.pop(k, None)                 # the raw string is not a refusal after all
                return r[0], r[1] + "+normalised"
        return None
    def __getattr__(self, name): return getattr(self.C, name)


def main():
    write = "--write" in sys.argv
    only = set(sys.argv[sys.argv.index("--league") + 1].split(",")) if "--league" in sys.argv else None
    outdir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(BASE, "build")
    enum = json.load(open(ENUM))["leagues"]
    pages, bynorm = load_cache()
    idx = IO.load_index(); idx.pop("_clubs", None)
    byname, keys = people(idx)
    arch_hc = collections.defaultdict(set)
    for pid, ks in keys.items():
        for k in ks:
            p = k.split("|")
            if p[0] == "COACHES" and len(p) == 3:
                st = (idx[pid]["seasons"][k].get("stint") or {})
                if st.get("is_head_coach"): arch_hc[(p[1].lstrip("y"), p[2])].add(pid)
    C = ClubResolver(Clubs())
    summary = {}
    # AN ARTICLE BELONGS TO ONE LEAGUE BUILD. The 2024-present UFL category tree includes
    # its predecessor leagues' seasons, so '2023 USFL season' and '2023 XFL season' were
    # parsed under UFL too. Leagues are processed in this order and the first to claim
    # an article keeps it; a league-season title that names another league is skipped.
    ORDER = ["USFL2", "XFL", "UFL", "ARENA", "CFL", "WFL", "AAF"]
    NAMES_LEAGUE = {"USFL2": r"\bUSFL\b", "XFL": r"\bXFL\b", "UFL": r"\bUFL\b|United Football League",
                    "ARENA": r"Arena Football League", "CFL": r"\bCFL\b", "WFL": r"World Football League", "AAF": r"\bAAF\b"}
    claimed = set()
    for lg in [x for x in ORDER if x in enum] + [x for x in enum if x not in ORDER]:
        v = enum[lg]
        if only and lg not in only: continue
        lgname = lg
        club_seasons, claims, leads, disagreements, refs = [], [], [], [], {}
        n = collections.Counter(); srecs = {}; missing_tpl = collections.Counter(); lead_why = collections.Counter()
        for title, r in v["titles"].items():
            if r["off_target"] or not r["exists"]: n["skipped_off_target_or_missing"] += 1; continue
            t = r["target"]; pg = pages.get(t)
            if not pg: n["not_in_cache"] += 1; continue
            if t in claimed: n["skipped_claimed_by_another_league"] += 1; continue
            other = [o for o, pat in NAMES_LEAGUE.items() if o != lg and re.search(pat, t)]
            if other and re.search(r"^\d{4} .+ season$", t) and not re.search(NAMES_LEAGUE[lg], t):
                n["skipped_names_another_league"] += 1; continue
            claimed.add(t)
            text, revid, ts = pg["text"], pg["revid"], pg["timestamp"]
            sr = f"wikipedia-en#{t}"; srecs[sr] = {"source_id": "wikipedia-en", "locator": t, "revision_id": revid, "timestamp": ts}
            ym = YEAR.search(t); year = int(ym.group(1)) if ym else None
            if not year: n["no_year_in_title"] += 1; continue
            refs[t] = len(REF.findall(text))
            ib, kind = infobox(text)
            is_league_season = kind == "sports season" or bool(re.match(r"^\d{4} (CFL|XFL|UFL|USFL|AAF|WFL|Arena Football League|United Football League) season$", t))
            base = {"league": lgname, "year": year, "source_record": sr, "revision_id": revid, "timestamp": ts}
            if is_league_season:
                n["league_season_articles"] += 1
                rows = []
                for m in re.finditer(r"\{\{#invoke:sports table\|main(.*?)\n\}\}", text, re.S):
                    rows += [{**x, "from": "sports_table"} for x in standings_from_sports_table(m.group(1))]
                for m in re.finditer(r"\{\{\s*((?:19|20)\d{2}(?:[–-]\d{2,4})? [^{}|\n]*?(?:[Ss]tandings|[Tt]able))\s*(?:\||\}\})", text):
                    want = "Template:" + re.sub(r"\s+", " ", m.group(1)).strip()
                    tn = want if want in pages else bynorm.get(ntitle(want))
                    tp = pages.get(tn) if tn else None
                    if not tp: missing_tpl[want] += 1; continue
                    div = re.sub(r"^(19|20)\d{2}(–\d{2,4})?\s*|\s*[Ss]tandings$|\s*[Tt]able$", "", m.group(1)).strip()
                    div = re.sub(r"\b(CFL|XFL|UFL|USFL|AAF|WFL|Arena Football League|AFL)\b", "", div).strip() or None
                    for blk in re.finditer(r"\{\{#invoke:sports table\|main(.*?)\n\}\}", tp["text"], re.S):
                        rows += [{**x, "from": tn, "template_revision_id": tp["revid"]} for x in standings_from_sports_table(blk.group(1))]
                    for tb in tables(tp["text"]):
                        rows += [{**x, "from": tn, "template_revision_id": tp["revid"]} for x in standings_from_table(tb, div)]
                for tb in tables(text):
                    rows += [{**x, "from": "inline_table"} for x in standings_from_table(tb)]
                seen = set()
                for x in rows:
                    key = (x["club_as_printed"], x["w"], x["l"], x["t"])
                    if key in seen: continue
                    seen.add(key)
                    res = C.resolve(x["club_as_printed"], year, lgname, source="wikipedia")
                    club_seasons.append({**base, "kind": "standings", **x,
                                         "club_id": res[0] if res else None, "club_resolved_how": res[1] if res else None})
                    n["standings_rows"] += 1
                for k in ("finals_champ", "season_champs", "conf1_champ", "conf2_champ"):
                    if ib.get(k) and plain(ib[k]):            # a champion field that reduces to nothing is no fact
                        club_seasons.append({**base, "kind": k, "club_as_printed": plain(ib[k]), "cited": cited(ib[k])})
            else:
                n["team_season_articles"] += 1
                team = plain(ib.get("team", "")) or re.sub(r"^\d{4} |\s+season$", "", t)
                res = C.resolve(team, year, lgname, source="wikipedia")
                cid, how = (res[0], res[1]) if res else (None, None)
                code = C.code_for(cid, year) if cid else None
                rec = {**base, "kind": "team_season", "club_as_printed": team, "club_id": cid, "club_resolved_how": how, "code": code}
                rm = REC.search(plain(ib.get("record", "")))
                if rm: rec.update({"w": int(rm.group(1)), "l": int(rm.group(2)), "t": int(rm.group(3)) if rm.group(3) else None, "record_cited": cited(ib.get("record", ""))})
                for k in ("division_place", "league_place", "conference_place", "playoffs", "general_manager", "stadium"):
                    if ib.get(k): rec[k] = plain(ib[k]); rec[k + "_cited"] = cited(ib[k])
                games = results_from_tables(tables(text))
                if games: rec["results"] = games; n["games"] += len(games)
                club_seasons.append(rec); n["team_season_records"] += 1
                for cname in coach_names(ib.get("coach", "") or ib.get("head_coach", "")):
                    n["coach_mentions"] += 1
                    pid, how_m = match_coach(cname, year, code, byname, keys)
                    if pid:
                        claims.append({"source_record": sr, "source_id": "wikipedia-en", "stated_by": "English Wikipedia",
                                       "attribution": ["English Wikipedia"], "subject": ["person", pid],
                                       "predicate": "wikipedia.head_coach",
                                       "value": {"league": lgname, "year": year, "club_as_printed": team, "club_id": cid, "code": code},
                                       "revision_id": revid, "timestamp": ts, "cited": cited(ib.get("coach", "")),
                                       "evidence_method": how_m, "kind": "observed", "observed_at": "fetched-2026-09"})
                        n[f"coach_matched:{how_m}"] += 1
                        if code and arch_hc.get((str(year), code)) and pid not in arch_hc[(str(year), code)]:
                            disagreements.append({"league": lgname, "year": year, "club_as_printed": team, "code": code, "field": "head_coach",
                                                  "wikipedia": {"name": cname, "person": pid, "name_in_index": idx[pid].get("name")},
                                                  "archive": [{"person": a, "name": idx[a].get("name")} for a in sorted(arch_hc[(str(year), code)])],
                                                  "source_record": sr, "revision_id": revid})
                            n["disagreement:head_coach"] += 1
                        elif code and arch_hc.get((str(year), code)): n["agreement:head_coach"] += 1
                        else: n["no_counterpart:head_coach"] += 1
                    else:
                        lead_why[how_m] += 1
                        leads.append({"lead_id": f"lead-wikiseason-{lg}-{len(leads) + 1:05d}", "category": "wikipedia_head_coach_unmatched",
                                      "name_as_printed": cname, "league": lgname, "year": year, "club_as_printed": team, "club_id": cid, "code": code,
                                      "source_record": sr, "revision_id": revid, "why_matching_failed": how_m,
                                      "promotion": "requires a ruling; not promoted here"})
                        n["coach_lead"] += 1
        doc = {"source": {"source_id": "wikipedia-en", "name": DECL["name"], "stated_by": "English Wikipedia",
                          "acquisition": DECL["acquisition"], "attribution": ["English Wikipedia"],
                          "rank": DECL["RANK"]["position"], "declaration": "declarations/wikipedia-seasons.json", "league": lgname},
               "source_records": srecs, "claims": claims, "club_seasons": club_seasons, "leads": leads,
               "disagreements": disagreements,
               "refused_clubs": [{"league": a, "year": b, "string": c, "why": d, "n": e} for a, b, c, d, e, _ in C.census() if a == lgname],
               "standings_templates_missing": dict(missing_tpl),
               "lead_reasons": dict(lead_why),
               "references_per_article": refs,
               "counts": dict(n)}
        C.refused.clear()
        out = os.path.join(outdir, f"wikipedia-seasons-{lgname.lower()}.json")
        if write: IO.dump_atomic(doc, out, indent=1)
        summary[lgname] = dict(n, claims=len(claims), club_seasons=len(club_seasons), leads=len(leads),
                               disagreements=len(disagreements), refused_clubs=len(doc["refused_clubs"]),
                               templates_missing=len(missing_tpl))
        print(f"== {lgname}: " + ", ".join(f"{k}={v}" for k, v in sorted(summary[lgname].items())), flush=True)
    return summary


if __name__ == "__main__":
    main()
