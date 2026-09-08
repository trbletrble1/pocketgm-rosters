"""Enumerate English Wikipedia league-season and team-season articles per league.

Stage B (Arena), Stage C (CFL) and the five small leagues Stage A never reached:
WFL, AAF, USFL (2022-), XFL, UFL. The Fetching session's enumeration was never
written down, so this re-derives it from the category tree and WRITES IT DOWN:
    build-reports/wikipedia-season-articles.json

WHAT THE FIRST RUN TAUGHT (2026-09-07 07:50), ALL ENFORCED HERE:
  1. Category names are not guessable. Every league starts from SEED ARTICLES; the
     '... seasons' categories are read from each seed's own categories and climbed
     to their parents by LEAGUE TOKEN, and every root found is walked (the first run
     took only the first seed's first candidate, and so stopped at one USFL season).
  2. Some leagues have NO seasons category (WFL, AAF). They get FALLBACK categories
     (the league's own category) walked for season-shaped titles.
  3. Category members come from every namespace. Only MAINSPACE titles are articles.
     Templates are kept SEPARATELY and only when they are standings templates --
     because Arena's standings live in 'Template:1987 Arena Football League
     standings', transcluded into the season article, so the article's own wikitext
     does not carry them. The fetcher pulls those templates too.
  4. THE REDIRECT TRAP. '2022 in Canadian football' -> '2022 in Canadian soccer';
     '2018 Jacksonville Sharks season' -> 'Jacksonville Sharks'. Every title is
     resolved with redirects=1 and the TARGET is checked for the season year, a
     league token, and an off-sport token. Off-target titles are kept, flagged,
     and never fetched as content.
  5. Resumes by league from its own output; `--redo LG,LG` forces leagues.

MediaWiki API via wiki_api (serial ~1/s, backoff through outages, HTTP status read).

  python3 src/enumerate_wiki_seasons.py [--redo ARENA,CFL,...|--redo all]
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
from wiki_api import api
OUT = os.path.join(BASE, "build-reports", "wikipedia-season-articles.json")

LEAGUES = {
    "ARENA": {"seeds": ["1987 Arena Football League season", "2008 Arena Football League season", "2019 Arena Football League season"],
              "tokens": ["Arena Football", "Arena"], "fallback": []},
    "CFL":   {"seeds": ["2022 CFL season", "1958 CFL season", "1975 CFL season"],
              "tokens": ["CFL", "Canadian Football", "Canadian football"], "fallback": []},
    "WFL":   {"seeds": ["1974 World Football League season", "1975 World Football League season"],
              "tokens": ["World Football League", "WFL"], "fallback": ["Category:World Football League"]},
    "AAF":   {"seeds": ["2019 AAF season", "2019 Alliance of American Football season", "Alliance of American Football"],
              "tokens": ["Alliance of American Football", "AAF"], "fallback": ["Category:Alliance of American Football"]},
    "USFL2": {"seeds": ["2022 USFL season", "2023 USFL season"],
              "tokens": ["USFL", "United States Football League"], "fallback": []},
    "XFL":   {"seeds": ["2001 XFL season", "2020 XFL season", "2023 XFL season", "2001 Los Angeles Xtreme season"],
              "tokens": ["XFL"], "fallback": ["Category:XFL (2001)", "Category:XFL (2020)", "Category:XFL (2023)"]},
    "UFL":   {"seeds": ["2009 United Football League season", "2024 UFL season", "2025 UFL season"],
              "tokens": ["United Football League", "UFL"], "fallback": []},
}
# team-name tokens that identify a CFL club season even when 'CFL' is absent from the title
CFL_CLUBS = ["Argonauts", "Stampeders", "Alouettes", "Roughriders", "Rough Riders", "Blue Bombers", "Eskimos", "Elks",
             "Tiger-Cats", "BC Lions", "B.C. Lions", "Renegades", "Redblacks", "Concordes", "Gold Miners", "Posse",
             "Texans", "Pirates", "Barracudas", "Mad Ducks", "Stallions", "Tiger–Cats"]
OFF_SPORT = re.compile(r"soccer|hockey|basketball|baseball|lacrosse|rugby|cricket|curling|in Canadian football", re.I)
YEAR = re.compile(r"\b(19[0-9]{2}|20[0-9]{2})\b")
SEASONISH = re.compile(r"^(19|20)\d{2}(–\d{2})? .+ (season|standings)$|^(19|20)\d{2} (CFL|XFL|UFL|USFL|AAF|WFL|Arena Football League)( season)?$")


def categories_of(title):
    code, d = api({"action": "query", "titles": title, "prop": "categories", "cllimit": "max", "redirects": 1})
    pg = next(iter(d["query"]["pages"].values())) if d else {"missing": ""}
    return code, [c["title"] for c in pg.get("categories", [])], pg.get("title"), "missing" in pg


def members(cat):
    """(mainspace pages, standings templates, subcategories) of a category."""
    pages, tpls, subs, cont = [], [], [], {}
    while True:
        code, d = api({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "max",
                       "cmtype": "page|subcat", **cont})
        if not d: break
        for m in d.get("query", {}).get("categorymembers", []):
            if m["ns"] == 14: subs.append(m["title"])
            elif m["ns"] == 0: pages.append(m["title"])
            elif m["ns"] == 10 and re.search(r"standings|table", m["title"], re.I): tpls.append(m["title"])
        if "continue" not in d: break
        cont = d["continue"]
    return pages, tpls, subs


def walk(roots, depth=3):
    """A root that is not itself a '... seasons' category is a FALLBACK (the league's own
    category): its children are walked unconditionally one level down, because a
    league with no seasons category files its team seasons under plain team categories
    ('Category:Birmingham Americans') whose names carry no 'season'. The season-shaped
    title filter, not the category name, then decides what is kept."""
    loose = {r for r in roots if not re.search(r"seasons?$", r, re.I)}
    seen, titles, tpls = set(), {}, {}
    frontier = [(r, 0) for r in roots]
    while frontier:
        cat, dp = frontier.pop(0)
        if cat in seen or dp > depth: continue
        seen.add(cat)
        pages, t, subs = members(cat)
        print(f"     cat {len(seen):3}  pages={len(pages):3} tpl={len(t):2} subcats={len(subs):3}  {cat}", flush=True)
        for x in pages: titles.setdefault(x, cat)
        for x in t: tpls.setdefault(x, cat)
        for s in subs:
            if cat in loose or re.search(r"season|by team|by year|champion", s, re.I): frontier.append((s, dp + 1))
    return titles, tpls, sorted(seen)


def find_roots(lg, spec):
    """Every '... seasons' category reachable from every seed, climbed to parents by token."""
    roots, log = set(), []
    for seed in spec["seeds"]:
        code, cats, real, missing = categories_of(seed)
        log.append({"seed": seed, "http": code, "resolved_to": real, "missing": missing, "categories": len(cats)})
        print(f"   seed {seed!r} HTTP {code} -> {real!r} missing={missing} cats={len(cats)}", flush=True)
        if missing: continue
        for c in cats:
            if "season" not in c.lower(): continue
            if any(t.lower() in c.lower() for t in spec["tokens"]): roots.add(c)
            # climb one level: a per-season category's parent is usually the '... seasons' root
            _, pcats, _, _ = categories_of(c)
            for p in pcats:
                if re.search(r"seasons$", p, re.I) and any(t.lower() in p.lower() for t in spec["tokens"]): roots.add(p)
    for f in spec["fallback"]: roots.add(f)
    return sorted(roots), log


def resolve(titles, lg, spec):
    out, batch = {}, list(titles)
    toks = list(spec["tokens"]) + (CFL_CLUBS if lg == "CFL" else [])
    for i in range(0, len(batch), 50):
        chunk = batch[i:i + 50]
        code, d = api({"action": "query", "titles": "|".join(chunk), "redirects": 1, "prop": "info"})
        q = (d or {}).get("query", {})
        rd = {r["from"]: r["to"] for r in q.get("redirects", [])}
        norm = {r["from"]: r["to"] for r in q.get("normalized", [])}
        present = {pg.get("title"): ("missing" not in pg) for pg in q.get("pages", {}).values()}
        for t in chunk:
            tgt = rd.get(norm.get(t, t), norm.get(t, t))
            ok_year = bool(YEAR.search(tgt)); ok_tok = any(k.lower() in tgt.lower() for k in toks); off = bool(OFF_SPORT.search(tgt))
            out[t] = {"target": tgt, "redirect": tgt != t, "exists": present.get(tgt, False), "http": code,
                      "off_target": (tgt != t) and (off or not ok_year or not ok_tok),
                      "why": ((("off-sport token" if off else "no year in target" if not ok_year
                               else "no league token in target" if not ok_tok else None)) if tgt != t else None)}
    return out


def main():
    redo = set()
    if "--redo" in sys.argv:
        v = sys.argv[sys.argv.index("--redo") + 1]
        redo = set(LEAGUES) if v == "all" else set(v.split(","))
    result = {"_what": "league-season and team-season ARTICLES per league (mainspace only), from every '... seasons' "
                       "category reachable from the seeds, every title resolved through redirects=1 with the target "
                       "checked; standings TEMPLATES kept separately because the season articles transclude them",
              "_date": "2026-09-07", "leagues": {}}
    if os.path.exists(OUT):
        try: result["leagues"] = json.load(open(OUT)).get("leagues", {})
        except Exception: pass
    for lg, spec in LEAGUES.items():
        done = result["leagues"].get(lg, {})
        if lg not in redo and done.get("roots") and done.get("titles"):
            print(f"== {lg}: already enumerated ({len(done['titles'])} titles), skipping", flush=True); continue
        print(f"== {lg}", flush=True)
        roots, seedlog = find_roots(lg, spec)
        print(f"   roots: {roots}", flush=True)
        if not roots:
            result["leagues"][lg] = {"roots": [], "seeds": seedlog, "error": "no seasons category reachable from any seed", "titles": {}}
            IO.dump_atomic(result, OUT, indent=1); continue
        raw, tpls, walked = walk(roots)
        titles = {t: c for t, c in raw.items() if SEASONISH.search(t)}
        other = {t: c for t, c in raw.items() if t not in titles}
        res = resolve(titles, lg, spec)
        off = sum(1 for v in res.values() if v["off_target"])
        print(f"   {len(raw)} mainspace pages -> {len(titles)} season-shaped ({len(other)} other kept aside), "
              f"{len(tpls)} standings templates; redirects={sum(1 for v in res.values() if v['redirect'])} "
              f"off-target={off} missing={sum(1 for v in res.values() if not v['exists'])}", flush=True)
        result["leagues"][lg] = {"roots": roots, "seeds": seedlog, "categories_walked": walked,
                                 "titles": {t: {"category": titles[t], **res[t]} for t in titles},
                                 "standings_templates": tpls, "non_season_pages": other}
        IO.dump_atomic(result, OUT, indent=1)
    tot = sum(len(v["titles"]) for v in result["leagues"].values())
    tpl = sum(len(v.get("standings_templates", {})) for v in result["leagues"].values())
    print(f"\nwrote {os.path.relpath(OUT, BASE)}: {tot} season articles, {tpl} standings templates", flush=True)


if __name__ == "__main__":
    main()
