"""Decide which season keys carry a club NAME that denotes a club CODE.

Writes dataset/build/club-key-normalisation.json. Decides only; applying is
src/apply_club_keys.py. See declarations/club-key-normalisation.json.

  python3 src/normalise_club_keys.py [--write]
"""
import os, sys, json, collections
import clubs as CL

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import norm
import apply_person_merges as AP
import apply_club_keys as CKA

DECIDED_AT = "2026-09-06"


def build():
    """Decide through the CLUB TABLE. Since patch 4 of the club job (2026-09-06) the
    corroboration a source defect needs -- one man holding the name and the code for
    one season -- is computed inside build_clubs.py from the same base-plus-merge
    view this file used to build, and every decision here is a table lookup: the
    printed name, the year, the league. The output shape is unchanged, so
    apply_club_keys.py, merge_people.py and gate_club_keys.py read it as before."""
    from clubs import Clubs
    C = Clubs()
    index = json.load(open(AP.IDXP)); clubs = index.pop("_clubs", {})
    merges = json.load(open(AP.MP))
    absorbed = {d["absorbed_person"] for d in merges["merges"]}
    if os.path.exists(CKA.NP): CKA.undo(index)
    AP.undo(index)                                  # the plain base: no merges, no rewrites
    def is_code(tok, yr): return f"{tok}|{yr}" in clubs
    def decide(club, yr, lg):
        """-> (code, kind, archive name, evidence) or (None, why, None, None), through the table."""
        C.refused.clear()
        r = C.resolve(club, int(yr), None if lg in CL.PSEUDO_LEAGUES() else lg, source="season_key")
        if not r:
            why = next((k[4] for k in C.refused), "no club under that name that year")
            return None, why, None, None
        cid, kind = r; code = C.code_for(cid, int(yr)); arch = C.name_for(cid, int(yr))
        if not code: return None, "the club fielded no team that year", arch, None
        if not is_code(code, yr): return None, "no archive code for this club that year (held only by PFA)", arch, None
        st = next((s for s in C.by_id[cid]["strings"] if norm(s["string"]) == norm(club) and s["first"] <= int(yr) <= s["last"]), {})
        if kind == "official": return code, "mapping_gap", arch, "the club carried this exact name that season"
        if kind == "wrong_for_season":
            n = st.get("person_seasons")
            if not n: return None, "source_defect_uncorroborated", arch, None
            return code, "source_defect", arch, f"{n} person-seasons hold both this name and {code}"
        if kind in ("printed_name", "alias", "compound_printed_name"):
            return code, "mapping_gap", arch, st.get("matched_on") or "the club carried this name that season"
        return None, f"table kind {kind} is not a decision", arch, None
    rewrites, refused = [], collections.Counter()
    refused_ex = collections.defaultdict(collections.Counter)
    at_merge = []
    for pid, p in sorted(index.items()):
        if not isinstance(p, dict): continue
        # BOTH DICTS (Ryan, 2026-09-11). Since the 9 September shape change the coaching keys this
        # decider exists for live in `coaching_seasons`, written with a bare year; reading `seasons`
        # only, a regeneration dropped 658 rewrites and all 1,929 merge-time records -- the decider
        # undoing its own decisions. Coaching keys are decided in the form the index now writes;
        # gate_club_key_decisions compares decisions in the bare-year form.
        for key in sorted(p.get("seasons") or {}) + sorted(p.get("coaching_seasons") or {}):
            dn = "seasons" if key in (p.get("seasons") or {}) else "coaching_seasons"
            lg, y, club = key.split("|", 2)
            yr = y[1:5] if y.startswith("y") else y
            if not yr.isdigit() or is_code(club, yr): continue
            code, kind, arch, ev = decide(club, yr, lg)
            if not code:
                refused[kind] += 1; refused_ex[kind][club] += 1
                continue
            new = f"{lg}|{y}|{code}"
            rec = {"person": pid, "from": key, "to": new, "kind": kind,
                   "club_as_printed": club, "club_in_the_archive": arch,
                   "evidence": ev, "decided_at": DECIDED_AT}
            if pid in absorbed:
                rec["absorbed_record_not_altered"] = True
                rec["applied_by"] = "the merge, when this record is folded into its canonical"
                at_merge.append(rec)
            else:
                rec["collides"] = new in (p.get(dn) or {})
                rewrites.append(rec)
    by_kind = collections.Counter(r["kind"] for r in rewrites)
    at_kind = collections.Counter(r["kind"] for r in at_merge)
    pairs = collections.Counter((r["club_as_printed"], r["to"].split("|")[2], r["kind"])
                                for r in rewrites + at_merge)
    out = {"declaration": "declarations/club-key-normalisation.json", "decided_at": DECIDED_AT,
           "decided_through": "build/clubs.json (the club table)",
           "rewrites": rewrites, "applied_when_merging": at_merge,
           "REFUSED": {"_why": "left exactly as printed", "counts": dict(refused),
                       "examples": {k: dict(v.most_common(10)) for k, v in refused_ex.items()}},
           "counts": {"rewrites": len(rewrites), "by_kind": dict(by_kind),
                      "people": len({r["person"] for r in rewrites}),
                      "collisions": sum(1 for r in rewrites if r["collides"]),
                      "on_absorbed_records_applied_only_when_merging": len(at_merge),
                      "by_kind_when_merging": dict(at_kind),
                      "refused": sum(refused.values()),
                      "source_defects": [{"printed": a, "code": b, "seasons": n}
                                         for (a, b, k), n in pairs.most_common() if k == "source_defect"]}}
    return out


def main():
    o = build()
    if "--write" in sys.argv:
        fp = os.path.join(BASE, "build", "club-key-normalisation.json")
        json.dump(o, open(fp, "w"), indent=1, ensure_ascii=False); print("wrote", fp)
    print(json.dumps(o["counts"], indent=1))
    print("refused:", json.dumps(o["REFUSED"]["counts"], indent=1))


if __name__ == "__main__":
    main()
