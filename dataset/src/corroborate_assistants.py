"""Decide which media-guide staff records denote a person the archive already holds.

RYAN'S RULING, 2026-09-07: a club's own media guide naming a man as its coach
documents that he worked that season. The 249 men this store could not promote were
refused because a person of that exact name already exists -- which is the right
refusal (identity is never a name alone) and the wrong conclusion: the guide is not
a second man, it is the club's own record of the man the archive already has.

THE EVIDENCE IS CLUB AND SEASON, NEVER THE NAME. A guide record joins an archive
person only where EXACTLY ONE person of that name holds a coaching season at a
club-year the guide names him at. The club-year is resolved through the club table,
so 'San Francisco 49ers' and SF are one club. Two candidates, or none, is a refusal.

Decides only; src/apply_assistants_identity.py applies. The role strings are not
touched here and are never rewritten: they are the point.

  python3 src/corroborate_assistants.py [--write]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import Clubs, norm
import index_io as IO

OUT = os.path.join(BASE, "build", "assistants-identity.json")
DECIDED_AT = "2026-09-07"


def build():
    C = Clubs()
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); IDX.pop("_clubs", None)
    A = json.load(open(os.path.join(BASE, "build", "assistants.json")))
    P = json.load(open(os.path.join(BASE, "build", "coach-promotions.json")))
    idm = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
    promoted = {x["lead_ref"] for x in P["promotions"] if x["source"] == "media-guide-assistant"}
    loc_name = {c["subject"][1]: c["value"] for c in A["claims"] if c["predicate"] == "name"}
    src_rec = {c["subject"][1]: c["source_record"] for c in A["claims"] if c["predicate"] == "name"}
    stints = collections.defaultdict(list)
    for c in A["claims"]:
        if c["subject"][0] == "stint":
            stints[c["subject"][1]].append({"club_as_printed": c["subject"][2], "year": int(c["subject"][3][1:5]),
                                            "role_as_printed": c["value"], "source_record": c["source_record"]})
    by_name = collections.defaultdict(list)
    for pid, p in IDX.items():
        if isinstance(p, dict) and p.get("name"): by_name[norm(p["name"])].append(pid)

    def club_id(tok, y):
        r = C.resolve(tok, y, None, source="season_key"); return r[0] if r else None

    def coaching_club_years(p):
        out = set()
        for k in (p.get("coaching_seasons") or {}):
            lg, y, c = k.split("|", 2); yy = int(y[1:5]) if y.startswith("y") else int(y); out.add((club_id(c, yy), yy))
        for k in (p.get("seasons") or {}):
            lg, y, c = k.split("|", 2)
            if lg == "COACHES": yy = int(y[1:5]) if y.startswith("y") else int(y); out.add((club_id(c, yy), yy))
        return {x for x in out if x[0]}

    joins, refused = [], collections.Counter(); refused_ex = collections.defaultdict(list)
    for loc in sorted(loc_name):
        nm = loc_name[loc]
        if loc in promoted:
            refused["promoted as a new person: not an existing man"] += 1; continue
        cands = by_name.get(norm(nm), [])
        if not cands:
            refused["no person of that name in the archive"] += 1; refused_ex["no person of that name in the archive"].append(nm); continue
        hits = []
        for pid in cands:
            cy = coaching_club_years(IDX[pid])
            m = [s for s in stints[loc] if (club_id(s["club_as_printed"], s["year"]), s["year"]) in cy]
            if m: hits.append((pid, m))
        if len(hits) == 1:
            pid, m = hits[0]
            joins.append({"local": loc, "store": "assistants", "person": pid, "name_as_printed": nm,
                          "archive_name": IDX[pid]["name"], "source_record": src_rec.get(loc),
                          "evidence": "club_season_corroboration",
                          "why": f"exactly one person named {IDX[pid]['name']!r} holds a coaching season at a club-year this guide names him at",
                          "club_years_matched": [{"club_as_printed": s["club_as_printed"], "year": s["year"], "club": club_id(s["club_as_printed"], s["year"]),
                                                  "role_as_printed": s["role_as_printed"]} for s in m],
                          "namesakes_considered": len(cands),
                          # HOW MANY NAMESAKES THE CLUB-SEASON EVIDENCE CORROBORATES. It is 1 by
                          # construction here -- len(hits) == 1 is the branch -- and it is RECORDED
                          # so gate_assistants_identity A3 can hold the decision to it without
                          # writing a second copy of this decider. A3 could not fail before
                          # 2026-09-07: it was written `... and ... or True`.
                          "namesakes_corroborated": len(hits),
                          "guide_seasons": len(stints[loc]), "decided_at": DECIDED_AT})
        elif len(hits) > 1: refused["more than one namesake holds a coaching season at a guide club-year"] += 1; refused_ex["more than one namesake holds a coaching season at a guide club-year"].append(nm)
        else: refused["namesake(s) hold no coaching season at any club-year this guide names"] += 1; refused_ex["namesake(s) hold no coaching season at any club-year this guide names"].append(nm)
    return {"declaration": "declarations/media-guides.json", "decided_at": DECIDED_AT,
            "_ruling": "Ryan 2026-09-07: a club's own media guide naming a man as its coach documents that he worked that season.",
            "_evidence_rule": "club and season, never the name: exactly one namesake holding a coaching season at a club-year the guide names him at.",
            "joins": joins,
            "REFUSED": {"_why": "left as leads, exactly as they were", "counts": dict(refused),
                        "examples": {k: sorted(v)[:10] for k, v in refused_ex.items()}},
            "counts": {"joins": len(joins), "people": len({j["person"] for j in joins}),
                       "guide_seasons_joined": sum(j["guide_seasons"] for j in joins),
                       "refused": sum(refused.values())}}


if __name__ == "__main__":
    o = build()
    if "--write" in sys.argv: IO.dump_atomic(o, OUT, indent=1); print("wrote", OUT)
    print(json.dumps(o["counts"], indent=1)); print("refused:", json.dumps(o["REFUSED"]["counts"], indent=1))
