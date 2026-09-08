"""Ingest the per-player PROSE from twenty club press guides, and the per-season
vitals as printed. Writes dataset/build/guide-prose.json.

No field parser. See declarations/media-guide-prose.json.

  python3 src/ingest_guide_prose.py [--write]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import guide_entries as G

BOOKS = os.path.join(BASE, "..", "..", "pgm3-sources", "nfl-books", "text_all")
DECL = json.load(open(os.path.join(BASE, "declarations", "media-guide-prose.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
GUIDES = [("redskins",1957),("redskins",1959),("giants",1959),("giants",1962),("giants",1968),
          ("cowboys",1965),("cowboys",1969),("colts",1974),("colts",1978),("eagles",1975),
          ("dolphins",1984),("dolphins",1988),("bears",1985),("packers",1995),("packers",1998),
          ("broncos",1997),("ravens",2003),("ravens",2008),("jaguars",2005),("jaguars",2009)]
CENSUS = os.path.join(BASE, "build-reports", "media-guide-prose-census.json")
# was a session scratchpad path (ccc7c2b9/.../census/classified4.json). The id
# belonged to the laptop, so the read died when the archive moved machines.
# The file is a RESULT -- 1,880 classified documents -- so it moved into
# build-reports/ rather than being repointed at the carried-over scratchpad.
FILES = {(c["club"], c["year"]): c["file"] for c in json.load(open(CENSUS))}


class ProseError(Exception):
    pass


def strict_pattern(name):
    """the OLD matcher: forename and surname adjacent. Kept only to report the rate
    the improved one lifted."""
    p = G.norm(name).split()
    if len(p) < 2: return None
    return re.compile(r"\b" + re.escape(p[0]) + r"[ .'\-]+" + re.escape(p[-1]) + r"\b")


def main():
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    CL = IDX.pop("_clubs")
    claims, leads, per_guide = [], [], []
    n = collections.Counter(); drops = collections.Counter(); labels = collections.Counter()
    strict_hits = loose_hits = 0
    for nick, year in GUIDES:
        fn = FILES[(nick, year)]
        t = open(os.path.join(BOOKS, fn), errors="ignore").read()
        codes = [k.split("|")[0] for k, v in CL.items()
                 if k.endswith("|" + str(year)) and G.norm(nick).rstrip("s") in G.norm(v)]
        men, stints = {}, {}
        for pid, p in IDX.items():
            if p.get("merged_into") or not p.get("name"): continue
            for k in p.get("seasons") or {}:
                lg, y, club = k.split("|", 2)
                if lg != "COACHES" and y == str(year) and club in codes:
                    men[pid] = p["name"]; stints[pid] = (lg, club)
        kept, dropped = G.entries(t, men)
        sr = f"{SRC_ID}#{fn}"
        gb = gl = gv = 0
        for e in kept:
            bl = G.blocks(e); vit = G.vitals(e)
            if not bl: continue
            if e["person"]:
                pid = e["person"]; lg, club = stints[pid]
                for b in bl:
                    if t[b["start"]:b["end"]] != b["text"]:
                        raise ProseError("a block does not round-trip against its source")
                    claims.append({
                        "source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
                        "attribution": [DECL["name"]], "subject": ["person", pid],
                        "predicate": "guide.prose_block", "kind": "observed",
                        "observed_at": f"guide-{year}",
                        "value": {"club": club, "league": lg, "year": year,
                                  "label_as_printed": b["label_as_printed"], "text": b["text"],
                                  "chars": len(b["text"]), "source_offsets": [b["start"], b["end"]],
                                  "header_as_printed": e["header"]},
                        "_verbatim_not_normalised": True, "_boundary_proved": True})
                    labels[str(b["label_as_printed"])] += 1; gb += 1
                if vit:
                    claims.append({
                        "source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
                        "attribution": [DECL["name"]], "subject": ["person", pid],
                        "predicate": "guide.vitals_as_printed", "kind": "observed",
                        "observed_at": f"guide-{year}",
                        "value": {"club": club, "league": lg, "year": year, **vit,
                                  "header_as_printed": e["header"]},
                        "_this_is_a_per_season_fact_not_a_correction":
                            "the archive's height and weight are career-level, from PFA. Both are held."})
                    gv += 1
            else:
                leads.append({"lead_id": f"lead-guide-prose-{len(leads)+1:05d}",
                              "category": "unmatched_no_candidate",
                              "name_as_printed": e["header_name"], "header_as_printed": e["header"],
                              "places_on": [None, year, codes[0] if codes else None],
                              "source_id": SRC_ID, "source_record": sr,
                              "IS_NOT_A_PERSON": True,
                              "why_matching_failed": "no man on the archive's roster for this club-season "
                                                     "matches the printed name",
                              "prose": [{"label_as_printed": b["label_as_printed"], "text": b["text"],
                                         "source_offsets": [b["start"], b["end"]]} for b in bl],
                              "vitals_as_printed": vit})
                gl += 1
        # matcher rate, old against new, on the same proved headers
        for e in kept:
            head = e["header"].lower()
            s_ = any((sp := strict_pattern(nm)) and sp.search(head) for nm in men.values())
            l_ = any((lp := G.name_pattern(nm)) and lp.search(head) for nm in men.values())
            strict_hits += bool(s_); loose_hits += bool(l_)
        for k, v in dropped.items(): drops[k] += v
        per_guide.append({"club": nick, "year": year, "file": fn, "roster": len(men),
                          "entries_proved": len(kept),
                          "entries_resolved": sum(1 for e in kept if e["person"]),
                          "prose_blocks": gb, "vitals": gv, "leads": gl,
                          "dropped": dict(dropped)})
        n["blocks"] += gb; n["vitals"] += gv; n["leads"] += gl
        print(f"{nick:9s} {year}  roster {len(men):3d}  proved {len(kept):3d}  "
              f"blocks {gb:3d}  vitals {gv:3d}  leads {gl:3d}  dropped {sum(dropped.values()):3d}")
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"], "stated_by": DECL["stated_by"],
                      "acquisition": DECL["acquisition"], "declaration": "declarations/media-guide-prose.json"},
           "claims": claims, "leads": leads, "per_guide": per_guide,
           "counts": {"guides": len(GUIDES), "prose_blocks": n["blocks"],
                      "vitals_claims": n["vitals"], "leads": n["leads"],
                      "claims": len(claims),
                      "labels_as_printed": dict(labels.most_common()),
                      "dropped": dict(drops),
                      "matcher": {"headers_matched_by_the_old_adjacent_name_rule": strict_hits,
                                  "headers_matched_by_the_improved_rule": loose_hits}}}
    if "--write" in sys.argv:
        fp = os.path.join(BASE, "build", "guide-prose.json")
        json.dump(out, open(fp, "w"), indent=1, ensure_ascii=False); print("wrote", fp)
    print(json.dumps(out["counts"], indent=1, default=str)[:1400])
    return out


if __name__ == "__main__":
    main()
