"""Run the prose extractor over the WHOLE guide corpus.

Same rules as the twenty-guide build, unchanged: generic header detection, the
Perko check, split headers collapsed, character-for-character round-trip, prose
verbatim, the guide's own label kept and never merged, per-season vitals held as a
second fact, and every unprovable boundary dropped and counted.

Writes build/guide-prose-corpus.json (claims) and build/guide-prose-corpus-leads.json.

  python3 src/ingest_guide_prose_corpus.py [--write] [--limit N]
"""
import os, re, sys, json, csv, time, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import guide_entries as G

BOOKS = os.path.join(BASE, "..", "..", "pgm3-sources", "nfl-books", "text_all")
DECL = json.load(open(os.path.join(BASE, "declarations", "media-guide-prose.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
CENSUS = os.path.join(BASE, "build-reports", "media-guide-prose-census.json")
# was a session scratchpad path (ccc7c2b9/.../census/classified4.json). The id
# belonged to the laptop, so the read died when the archive moved machines.
# The file is a RESULT -- 1,880 classified documents -- so it moved into
# build-reports/ rather than being repointed at the carried-over scratchpad.


def strict_pattern(name):
    p = G.norm(name).split()
    if len(p) < 2: return None
    return re.compile(r"\b" + re.escape(p[0]) + r"[ .'\-]+" + re.escape(p[-1]) + r"\b")


def main():
    write = "--write" in sys.argv
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    CL = IDX.pop("_clubs")
    # rosters, once for the whole corpus
    by_cs = collections.defaultdict(dict); stint_of = {}
    for pid, p in IDX.items():
        if p.get("merged_into") or not p.get("name"): continue
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2)
            # A man who COACHED the club that year is on that club-season by the
            # archive's own record, and the guide gives coaches entries too. Excluding
            # COACHES keys left 67 of them as leads. The league on the claim says
            # COACHES so the stint is never mistaken for a playing one.
            yy = y[1:5] if y.startswith("y") else y
            by_cs[(yy, club)].setdefault(pid, p["name"]); stint_of.setdefault((pid, yy, club), lg)
    C = json.load(open(CENSUS))
    idxcsv = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(BASE, "..", "..",
              "pgm3-sources", "nfl-books", "index.csv")))}
    league_wide = {c["file"] for c in C if idxcsv.get(c["file"][:-4], {}).get("league_wide") == "True"}
    todo = [c for c in C if c["file"] not in league_wide]
    if limit: todo = todo[:limit]
    print(f"corpus: {len(C)} texts; {len(league_wide)} league Record & Fact Books excluded; "
          f"302 zero-byte .notext files are not in this list at all; running {len(todo)}", flush=True)

    claims, leads, per_guide = [], [], []
    drops = collections.Counter(); labels = collections.Counter()
    strict_hits = loose_hits = 0
    t0 = time.time()
    for i, c in enumerate(todo, 1):
        fn, nick, year = c["file"], c["club"], c["year"]
        try:
            t = open(os.path.join(BOOKS, fn), errors="ignore").read()
        except Exception as e:
            per_guide.append({"file": fn, "club": nick, "year": year, "unreadable": str(e)}); continue
        codes, club_why = G.resolve_club(nick, year, CL, fn)
        men = {}
        for code in codes: men.update(by_cs.get((str(year), code), {}))
        kept, dropped = G.entries(t, men)
        sr = f"{SRC_ID}#{fn}"
        gb = gv = gl = 0
        for e in kept:
            bl = G.blocks(e)
            if not bl: continue
            vit = G.vitals(e)
            if e["person"]:
                pid = e["person"]
                club = next((cd for cd in codes if pid in by_cs.get((str(year), cd), {})), None)
                lg = stint_of.get((pid, str(year), club), "NFL")
                ok = []
                for b in bl:
                    if t[b["start"]:b["end"]] == b["text"]: ok.append(b)
                for b in ok:
                    claims.append({"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
                                   "attribution": [DECL["name"]], "subject": ["person", pid],
                                   "predicate": "guide.prose_block", "kind": "observed",
                                   "observed_at": f"guide-{year}",
                                   "value": {"club": club, "league": lg, "year": year,
                                             "label_as_printed": b["label_as_printed"], "text": b["text"],
                                             "chars": len(b["text"]), "source_offsets": [b["start"], b["end"]],
                                             "header_as_printed": e["header"]},
                                   "_verbatim_not_normalised": True, "_boundary_proved": True})
                    labels[str(b["label_as_printed"])] += 1; gb += 1
                if len(ok) != len(bl): drops["a block that did not round-trip, not written"] += len(bl) - len(ok)
                if vit and ok:
                    claims.append({"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
                                   "attribution": [DECL["name"]], "subject": ["person", pid],
                                   "predicate": "guide.vitals_as_printed", "kind": "observed",
                                   "observed_at": f"guide-{year}",
                                   "value": {"club": club, "league": lg, "year": year, **vit,
                                             "header_as_printed": e["header"]},
                                   "_this_is_a_per_season_fact_not_a_correction":
                                       "the archive's height and weight are career-level, from PFA. Both are held."})
                    gv += 1
            else:
                leads.append({"lead_id": f"lead-guide-prose-{len(leads)+1:06d}",
                              "category": "unmatched_no_candidate",
                              "name_as_printed": e["header_name"], "header_as_printed": e["header"],
                              "places_on": [None, year, codes[0] if codes else None],
                              "source_id": SRC_ID, "source_record": sr, "IS_NOT_A_PERSON": True,
                              "why_matching_failed": ("no man on the archive's roster for this club-season "
                                                      "matches the printed name" if men else
                                                      "the archive holds no roster for this club-season"),
                              "prose": [{"label_as_printed": b["label_as_printed"], "text": b["text"],
                                         "source_offsets": [b["start"], b["end"]]} for b in bl],
                              "vitals_as_printed": vit})
                gl += 1
        for e in kept:
            head = e["header"].lower()
            strict_hits += any((sp := strict_pattern(nm)) and sp.search(head) for nm in men.values())
            loose_hits += any((lp := G.name_pattern(nm)) and lp.search(head) for nm in men.values())
        for k, v in dropped.items(): drops[k] += v
        per_guide.append({"file": fn, "club": nick, "year": year, "chars": len(t),
                          "club_codes": codes, "club_resolution": club_why, "roster": len(men), "entries_proved": len(kept),
                          "entries_resolved": sum(1 for e in kept if e["person"]),
                          "prose_blocks": gb, "vitals": gv, "leads": gl, "dropped": dict(dropped)})
        if i % 100 == 0 or i == len(todo):
            el = time.time() - t0
            print(f"  {i}/{len(todo)} guides  {el/60:.1f} min  blocks {len(claims)}  leads {len(leads)}",
                  flush=True)
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"], "stated_by": DECL["stated_by"],
                      "acquisition": DECL["acquisition"],
                      "declaration": "declarations/media-guide-prose.json"},
           "claims": claims, "per_guide": per_guide,
           "counts": {"texts_in_census": len(C), "league_wide_excluded": len(league_wide),
                      "zero_byte_notext_excluded": 302, "guides_run": len(todo),
                      "prose_blocks": sum(1 for c in claims if c["predicate"] == "guide.prose_block"),
                      "vitals_claims": sum(1 for c in claims if c["predicate"] == "guide.vitals_as_printed"),
                      "leads": len(leads), "claims": len(claims),
                      "labels_as_printed": dict(labels.most_common()),
                      "dropped": dict(drops),
                      "matcher": {"headers_matched_by_the_old_adjacent_name_rule": strict_hits,
                                  "headers_matched_by_the_improved_rule": loose_hits}}}
    if write:
        fp = os.path.join(BASE, "build", "guide-prose-corpus.json")
        json.dump(out, open(fp, "w"), indent=1, ensure_ascii=False); print("wrote", fp, flush=True)
        lp = os.path.join(BASE, "build", "guide-prose-corpus-leads.json")
        json.dump({"source": out["source"], "leads": leads, "n": len(leads)},
                  open(lp, "w"), indent=1, ensure_ascii=False); print("wrote", lp, flush=True)
    print(json.dumps(out["counts"], indent=1, default=str)[:1800], flush=True)


if __name__ == "__main__":
    main()
