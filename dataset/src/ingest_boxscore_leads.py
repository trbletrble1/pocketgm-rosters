"""Ingest the 120 men who appear in PFA boxscores and were never enumerated.

THEY STAY LEADS. Ryan's ruling on player leads stands, so nothing here becomes a
person -- but every field is captured so a later promotion is a ruling rather than
a re-fetch. All 119 pages that returned are PLAYER pages; none is a coach, so the
coaches-become-people ruling does not reach this set.

Reuses the stage-one parsers unchanged, including the <a>-anchored draft split
that takes year and league from the href and keeps the raw string as the parent.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
SP = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
      "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")
from ingest_pfa import (parse_player, parse_drafts, CACHE, DECL, SRC_ID, canonical_url)

FIELDS = ("high_school", "birth_place", "birth_date", "death_date", "death_place",
          "draft", "military_service", "height", "weight", "position")


def main(write=True):
    R = json.load(open(SP + "ne_fetch_report.json"))
    sides = json.load(open(SP + "ne_sides.json"))
    split = json.load(open(SP + "ne_split.json"))
    box = json.load(open(os.path.join(BASE, "build", "pfa-boxscores.json")))
    appear = collections.defaultdict(list)
    for l in box["leads"]:
        appear[l["pfa_code"]].append({"game": l["game"], "name_as_printed": l["name_as_printed"]})

    def side_of(c):
        for k in ("only_visitor", "only_home", "both"):
            if c in sides[k]:
                return {"only_visitor": "visitor_only", "only_home": "home_only",
                        "both": "both_sides"}[k]
        return "unknown"

    leads, dead = [], []
    n = collections.Counter()
    for c, u, st in R["dead_404"]:
        dead.append({"pfa_code": c, "url": u, "status": st,
                     "_read_at_request_time": True,
                     "what": "PFA names this man in its own boxscores and has no page "
                             "for him. Not a fetch that failed and not a man who did "
                             "not exist.",
                     "appearances": appear.get(c, [])})
    for c in R["ok"]:
        p = os.path.join(CACHE, f"players_{c[0]}_{c}.html")
        h = open(p, encoding="utf-8", errors="replace").read()
        r = parse_player(h)
        fields = {}
        for f in FIELDS:
            if r.get(f):
                fields[f] = r[f]; n[f] += 1
        drafts = [d for d in parse_drafts(h) if d["parsed"]]
        if drafts:
            n["draft_selection"] += len(drafts)
        if r["college_rows"]:
            n["college_season"] += len(r["college_rows"])
        if r["relatives"]:
            n["kin"] += len(r["relatives"])
        if r["transactions"]:
            n["transaction"] += len(r["transactions"])
        leads.append({
            "lead_id": f"lead-boxne-{len(leads)+1:04d}",
            "category": "boxscore_appearance_never_enumerated",
            "pfa_code": c, "pfa_url": canonical_url(f"players/{c[0]}/{c}.html"),
            "source_id": SRC_ID, "source_record": f"{SRC_ID}#players/{c[0]}/{c}.html",
            "stated_by": DECL["stated_by"],
            "IS_NOT_A_PERSON": True,
            "_ruling": "player leads stay leads; every field is captured so a later "
                       "promotion is a ruling, not a re-fetch",
            "page_kind": "player",
            "why_never_enumerated": ("structural: every league-year he played is one the "
                                     "archive does not hold"
                                     if c in split["structural"] else
                                     "defect: at least one of his league-years WAS "
                                     "enumerated and he was not on the roster page"),
            "boxscore_side": side_of(c),
            "appearances": appear.get(c, []),
            "fields": fields,
            "draft_raw": r.get("draft") or None,
            "draft_selections": drafts,
            "college_rows": r["college_rows"],
            "college_stated_none": r["college_stated_none"],
            "relatives": r["relatives"],
            "transactions": r["transactions"],
        })
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           "claims": [],
           "_no_claims_by_design": "these men are not in the archive; a claim needs a "
                                   "person and a lead is not one",
           "leads": leads, "source_dead_links": dead,
           "counts": {"fetched": len(R["ok"]), "hard_404": len(dead),
                      "leads": len(leads), "by_field": dict(n),
                      "by_side": dict(collections.Counter(l["boxscore_side"] for l in leads)),
                      "structural": sum(1 for l in leads if l["why_never_enumerated"].startswith("structural")),
                      "defect": sum(1 for l in leads if l["why_never_enumerated"].startswith("defect"))}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-boxscore-leads.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    print(f"  fetched {c['fetched']}  hard404 {c['hard_404']}  leads {c['leads']}")
    print(f"  structural {c['structural']}   defect {c['defect']}")
    print(f"  by side: {c['by_side']}")
    print("  fields captured:")
    for k, v in sorted(c["by_field"].items(), key=lambda x: -x[1]):
        print(f"     {k:20s} {v:,}")
