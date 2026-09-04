"""Ingest the transcribed salary figures.

Every figure carries its convention (the predicate name IS the convention),
its regime, its attribution chain and its acquisition state. The six decoys are
checked ON THE WRITE rather than trusted to the declaration.
"""
import os, sys, json, collections, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model import Store, StoreError, SALARY_CONVENTIONS, SYSTEM_PREDICATES

BASE = os.path.join(HERE, "..")
SRC = os.environ.get("PGM3_SOURCES", os.path.expanduser("~/Documents/pgm3-sources"))
LOG = []
def log(m): print(m, flush=True); LOG.append(m)


def load_decoys():
    d = json.load(open(os.path.join(BASE, "declarations", "salary_conventions.json")))
    return {int(x["value"]): x for x in d["non_salary_figures_that_look_like_salaries"]}, d


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    decoys, decl = load_decoys()
    tbl = json.load(open(os.path.join(BASE, "extract", "courts.json")))
    store = Store()

    counts = collections.Counter()
    by_conv = collections.Counter()
    by_regime = collections.Counter()
    by_league = collections.Counter()
    by_decade = collections.Counter()
    decoy_hits = []
    refusals = []
    people = {}

    for case_id, case in sorted(tbl["cases"].items()):
        path = os.path.join(SRC, "DocDump", case["file"])
        if not os.path.exists(path):
            refusals.append((case_id, "source file not on disk")); continue
        src_id = f"court/{case_id}"
        store.add_source({
            "source_id": src_id, "name": case["citation"],
            "acquisition": "held",           # a file on disk, hash-pinned
            "stated_by": "the court",
            "attribution": [],               # findings of fact - ZERO removes
            "derived_from": None,
            "sha256": sha(path),
            "transcriber": tbl["_transcriber"],
        })
        for i, f in enumerate(case["figures"]):
            counts["figures seen"] += 1
            pred, val = f["predicate"], f["value"]

            # --- DECOY CHECK, ON THE WRITE ---------------------------------
            if val in decoys and pred in SALARY_CONVENTIONS:
                dk = decoys[val]
                same_case = dk["scoped_to_source_key"] in case_id.lower()
                if same_case and dk["decoy_kind"] == "not_compensation":
                    decoy_hits.append((case_id, f.get("person"), pred, val, "BLOCKED: " + dk["what"]))
                    counts["DECOY BLOCKED"] += 1
                    continue
                if same_case and dk["decoy_kind"] == "requires_pairing":
                    need = dk["must_be_paired_with"]
                    present = any(g["predicate"] == need for g in case["figures"])
                    if not present:
                        decoy_hits.append((case_id, f.get("person"), pred, val,
                                           f"BLOCKED: needs a companion {need} figure in the same case"))
                        counts["DECOY BLOCKED"] += 1
                        continue
                    decoy_hits.append((case_id, f.get("person"), pred, val,
                                       f"admitted, paired with {need}"))
                    counts["decoy paired"] += 1

            key = (f.get("person") or "?", case_id)
            if key not in people:
                people[key] = store.mint_person()
            p = people[key]
            store.declare_subject(("person", p))

            sr = store.add_source_record(src_id, f"figure{i+1}")
            store.add_denotation(sr, p, ["name", "club", "case"], "hand",
                                 matched_against=f"{case['citation']} :: {f.get('person')}",
                                 note="named party or witness in a federal/state opinion")

            season = f.get("season")
            club = f.get("club")
            # A season-less contract figure belongs to the CONTRACT, not the man.
            # Filing two of a player's contracts on ("person", p) collapses them
            # into a false contest - Kapp's $300,000 Minnesota deal against his
            # $600,000 New England deal are two instruments, not a disagreement.
            # A club-to-club release fee is neither a stint nor a contract: the
            # payee is the other CLUB. Ruled 2026-09-04 - it takes its own
            # subject naming both clubs, or it states a rule where there is an
            # instance. The store refuses every other shape.
            if f.get("subject_scope") == "transfer":
                subj = ("transfer", p, f["from_club"], f["to_club"], f["season"])
                # The FEE is observed. A club in the subject may not be. Kapp's
                # opinion says "Kapp's Canadian team" and never names it, so
                # CFLBC is source_derived - and a reader seeing it in the subject
                # would otherwise assume the court said it. Provenance records
                # ORIGIN, not last hop.
                _d = f.get("from_club_is_DERIVED")
                if _d:
                    store.declare_subject(subj)
                    store.add_claim(sr, subj, "from_club_identification",
                                    f["from_club"], f["season"], kind=_d["kind"],
                                    stated_by=None, attribution=[],
                                    note=_d["basis"][:200])
            elif season:
                subj = ("stint", p, club or "?", f"y{season}")
            elif club:
                subj = ("contract", p, club)
            else:
                subj = ("person", p)
            store.declare_subject(subj)
            try:
                store.add_claim(sr, subj, pred, val, season or f"case:{case_id}",
                                kind="observed", stated_by="the court", attribution=[],
                                note=f["quote"][:200])
            except StoreError as e:
                refusals.append((case_id, f"{pred} {val}: {e}")); counts["refused"] += 1
                continue

            counts["claims written"] += 1
            by_conv[pred] += 1
            by_regime[f.get("regime") or "unresolved"] += 1
            by_league[f.get("league") or "?"] += 1
            if season: by_decade[f"{(season//10)*10}s"] += 1
            else: by_decade["season unresolved"] += 1

            # regime travels with the figure, as its own claim on the stint
            if season and f.get("regime") not in (None, "n/a", "unresolved"):
                store.add_claim(sr, subj, "governing_regime", f["regime"], season,
                                kind="observed", stated_by="the court",
                                note="Rozelle Rule through 1976; Article XV from 1977")


    # ---------------- newspapers ----------------------------------------
    news = json.load(open(os.path.join(BASE, "extract", "newspapers.json")))
    for sid, src in sorted(news.items()):
        if sid.startswith("_"): continue          # _RELAYED_NOT_INGESTED etc.
        acq = src.get("acquisition", "held")
        f_ = src.get("file")
        path = os.path.join(SRC, "DocDump", f_) if f_ else None
        store.add_source({"source_id": f"news/{sid}", "name": src["citation"],
                          "acquisition": acq, "stated_by": src["stated_by"],
                          "attribution": src.get("attribution", []), "derived_from": None,
                          "sha256": sha(path) if path and os.path.exists(path) else None})
        conv = src.get("convention")
        for i, f in enumerate(src.get("figures", [])):
            counts["figures seen"] += 1
            pred = f.get("convention") or conv
            season = f.get("season", src.get("season"))
            val = f["value"]
            dk = decoys.get(val)
            if (dk and dk["decoy_kind"] == "not_compensation"
                    and dk["scoped_to_source_key"] in sid.lower()):
                decoy_hits.append((sid, f.get("player"), pred, val, "BLOCKED: " + dk["what"]))
                counts["DECOY BLOCKED"] += 1; continue
            key = (f["player"], sid)
            if key not in people: people[key] = store.mint_person()
            p_ = people[key]; store.declare_subject(("person", p_))
            sr = store.add_source_record(f"news/{sid}", f"fig{i+1}")
            store.add_denotation(sr, p_, ["name", "club", "season"], "hand",
                                 matched_against=f"{src['citation']} :: {f['player']}")
            subj = ("stint", p_, f.get("club", "?"), f"y{season}") if season else ("person", p_)
            store.declare_subject(subj)
            store.add_claim(sr, subj, pred, val, season or f"src:{sid}",
                            kind="observed", stated_by=src["stated_by"],
                            attribution=f.get("attribution_override", src.get("attribution", [])),
                            note=(f.get("quote") or "")[:200])
            counts["claims written"] += 1; by_conv[pred] += 1
            by_regime[src.get("regime", "unresolved")] += 1
            by_league[src.get("league", "?")] += 1
            by_decade[f"{(season//10)*10}s" if season else "season unresolved"] += 1
            if f.get("block_assignment") == "INFERRED": counts["position INFERRED"] += 1
            if f.get("tier") == "HEDGED": counts["author-HEDGED"] += 1
        for i, f in enumerate(src.get("figures_on_a_different_convention", [])):
            counts["figures seen"] += 1
            key = (f["player"], sid)
            if key not in people: people[key] = store.mint_person()
            p_ = people[key]
            sr = store.add_source_record(f"news/{sid}", f"altconv{i+1}")
            subj = ("stint", p_, f.get("club", "?"), f"y{f['season']}")
            store.declare_subject(subj)
            store.add_claim(sr, subj, f["predicate"], f["value"], f["season"],
                            kind="observed", stated_by=src["stated_by"],
                            attribution=src.get("attribution", []), note=(f.get("quote") or "")[:200])
            counts["claims written"] += 1; by_conv[f["predicate"]] += 1
            by_regime[src.get("regime", "unresolved")] += 1
            by_league[src.get("league", "?")] += 1
            by_decade[f"{(f['season']//10)*10}s"] += 1
        for i, tm in enumerate(src.get("teams", [])):
            for col, pred in (("base", src.get("conventions", {}).get("base")),
                              ("nflpa_total", src.get("conventions", {}).get("total"))):
                if not pred: continue
                counts["figures seen"] += 1
                subj = ("cohort", src.get("league", "NFL"), src["season"], tm["club"])
                store.declare_subject(subj)
                sr = store.add_source_record(f"news/{sid}", f"team{i+1}-{col}")
                store.add_claim(sr, subj, "cohort_salary_average", tm[col], src["season"],
                                kind="observed", stated_by=src["stated_by"],
                                attribution=src.get("attribution", []),
                                note=f"convention={pred}; population={src.get('population','')}"[:200])
                counts["claims written"] += 1; counts["cohort aggregates"] += 1
                by_conv[f"cohort/{pred}"] += 1
                by_regime[src.get("regime", "unresolved")] += 1
                by_league[src.get("league", "?")] += 1
                by_decade[f"{(src['season']//10)*10}s"] += 1
        for i, f in enumerate(src.get("cohort_figures", [])):
            counts["figures seen"] += 1
            subj = tuple("?" if x is None else x for x in f["scope"])
            store.declare_subject(subj)
            sr = store.add_source_record(f"news/{sid}", f"cohort{i+1}")
            store.add_claim(sr, subj, f["predicate"], f["value"],
                            f["scope"][2] or f"src:{sid}", kind="observed",
                            stated_by=src["stated_by"], attribution=src.get("attribution", []),
                            note=(f.get("quote") or "")[:200])
            counts["claims written"] += 1; counts["cohort aggregates"] += 1
            by_conv[f["predicate"]] += 1
            by_regime[src.get("regime", "unresolved")] += 1
            by_league[src.get("league", "?")] += 1
            by_decade[f"{(f['scope'][2]//10)*10}s" if f["scope"][2] else "season unresolved"] += 1

    store.save(os.path.join(BASE, "build", "salaries.json"))

    log("=" * 62)
    log(f"figures seen      {counts['figures seen']}")
    log(f"claims written    {counts['claims written']}")
    log(f"DECOYS BLOCKED    {counts['DECOY BLOCKED']}")
    log(f"refused           {counts['refused']}")
    log(f"persons           {len(store.persons)}   total claims {len(store.claims)}")
    log("")
    log("by convention:")
    for k, v in by_conv.most_common(): log(f"   {k:26s} {v}")
    log("by regime:")
    for k, v in by_regime.most_common(): log(f"   {k:26s} {v}")
    log("by league:")
    for k, v in by_league.most_common(): log(f"   {k:26s} {v}")
    log("by decade:")
    for k, v in sorted(by_decade.items()): log(f"   {k:26s} {v}")
    if decoy_hits:
        log("")
        log("DECOYS BLOCKED ON THE WRITE:")
        for c, who, pred, val, what in decoy_hits:
            log(f"   {c}: ${val:,} as {pred} -> {what[:60]}")
    if refusals:
        log("")
        log("REFUSED:")
        for c, why in refusals: log(f"   {c}: {why[:100]}")
    open(os.path.join(BASE, "build", "ingest-salaries.log"), "w").write("\n".join(LOG))

if __name__ == "__main__":
    main()
