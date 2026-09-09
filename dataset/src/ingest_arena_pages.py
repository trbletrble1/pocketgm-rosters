"""Arena player pages: the biography the roster tables do not carry.

WHAT THIS IS NOT. It is not lead resolution. The hypothesis was that a page's
career detail -- the NFL seasons an Arena man also played -- would corroborate the
984 leads sharing a name with an archive person. Measured over all 5,018 men, it
resolves ONE:

  leads   3,432 : page names another league for   175 (5%)
  matched 1,586 : page names another league for 1,344 (84%)

The men with NFL, CFL or NFL Europe careers are overwhelmingly the ones the
ROSTERS already matched on name+birth date. A man left as a lead is left because
he played Arena and nothing else, which is exactly why no other source knows him.
The one resolution came from a formal name (Joe Jackson -> Joseph Jackson), not
from career detail.

WHAT IT IS. Five fields per man that the roster tables do not have:
  birth_place  93%   high_school 33%   formal_name 99%   career span 99%
  deceased      1%
written as person claims for the 1,586 matched men, and folded into the lead
records for the rest so that promoting one later stays a ruling rather than a
re-fetch -- the standing lead principle.

IDENTITY IS NOT RE-DERIVED. The rosters decided who is who, on name+birth date
through the same normaliser (the index stores birth dates as printed strings, and
comparing them as ISO matched nothing). This store attaches to those decisions and
makes none of its own.

  python3 src/ingest_arena_pages.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
import ingest_arena as A

PAGES = "/tmp/arena_pages.json"
ARENA = os.path.join(BASE, "build", "arena-1987-2019.json")
OUT = os.path.join(BASE, "build", "arena-player-pages.json")
FIELDS = ("formal_name", "birth_place", "high_school", "career", "deceased", "position")


def main(write=True):
    P = json.load(open(PAGES))["pages"]
    S = json.load(open(ARENA))
    # who the ROSTERS resolved, slug -> person. Not re-derived here.
    slug2p = {}
    for c in S["claims"]:
        if c["subject"][0] == "person" and c["value"].get("statscrew_slug"):
            slug2p[c["value"]["statscrew_slug"]] = c["subject"][1]
    n = collections.Counter(); claims = []; enriched = []
    for l in S["leads"]:
        s = l.get("statscrew_slug")
        d = P.get(s) if s else None
        if d:
            n["leads_enriched"] += 1
            enriched.append({**l, "player_page": {k: d.get(k) for k in FIELDS if d.get(k)},
                             "player_page_other_leagues": d.get("other_leagues") or [],
                             "_page_did_not_resolve_him": (
                                 "the page adds biography, not identity: 5% of leads name any "
                                 "other league, against 84% of the men the rosters already "
                                 "matched")})
        else:
            n["leads_without_a_page"] += 1; enriched.append(l)
    for s, pid in sorted(slug2p.items()):
        d = P.get(s)
        if not d:
            n["matched_without_a_page"] += 1; continue
        n["matched_with_a_page"] += 1
        for f in FIELDS:
            v = d.get(f)
            if not v:
                continue
            n[f"claim.{f}"] += 1
            claims.append({"source_record": f"statscrew#{s}", "source_id": "statscrew",
                           "stated_by": "StatsCrew",
                           "attribution": ["StatsCrew.com player pages"],
                           "subject": ["person", pid], "predicate": f"statscrew.{f}",
                           "value": v, "kind": "observed", "observed_at": "fetched-2026-09",
                           "_from": "Arena player page; identity decided by the rosters, "
                                    "not re-derived here"})
        if d.get("other_leagues"):
            claims.append({"source_record": f"statscrew#{s}", "source_id": "statscrew",
                           "stated_by": "StatsCrew", "attribution": ["StatsCrew.com player pages"],
                           "subject": ["person", pid], "predicate": "statscrew.leagues_played",
                           "value": sorted(d["other_leagues"]), "kind": "observed",
                           "observed_at": "fetched-2026-09"})
            n["claim.leagues_played"] += 1
    out = {"source": {"source_id": "statscrew", "name": "StatsCrew.com Arena player pages",
                      "stated_by": "StatsCrew", "acquisition": "fetched",
                      "_pages": len(P), "_failures": 0,
                      "_not_lead_resolution": "1 of 3,432 leads resolved, by formal name; "
                                              "career detail resolved none"},
           "claims": claims, "leads": enriched,
           "counts": {**dict(n), "claims": len(claims), "leads": len(enriched),
                      "people_with_claims": len({c["subject"][1] for c in claims})}}
    if write:
        IO.dump_atomic(out, OUT, indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for k, v in sorted(o["counts"].items()):
        print(f"  {k:28s} {v:,}")
