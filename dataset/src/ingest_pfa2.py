"""PFA stage two: 1950 to present, matched people only.

Reuses every parser stage one settled -- bounded label values, <a>-anchored draft
splitting, printed-but-undated transactions, kinship without synthesised inverses.
What is new here is the population and the expectation about coverage: PFA's fields
are era-dependent (death dates ran 86-100% pre-1930 and 3% for the CFL; military
service 86% for the AAFC and 12% for the 1950s-70s), so coverage is reported BY BAND
and nothing from stage one is assumed to carry forward.

Leads are ENUMERATED, not fetched. Stage one spent about a third of its requests on
men the archive does not hold; deferring them puts the useful claims in far sooner
and loses nothing, because every lead keeps its code, names and club-seasons.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
from ingest_pfa import (parse_player, parse_drafts, draft_claims, kin_claim,
                        transaction_claim, claim, disagreement, date_key,
                        canonical_url, page, GAP_FILL, FIELD_PREDICATE,
                        SRC_ID, DECL, PFAError)

SP = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
      "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")
BANDS = [(1950, 1959), (1960, 1969), (1970, 1979), (1980, 1989),
         (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2025)]


def band(y):
    for a, b in BANDS:
        if a <= y <= b:
            return f"{a}s" if a % 10 == 0 else f"{a}-{b}"
    return "other"


def main(write=True):
    import write_bios as W
    M = json.load(open(SP + "pfa2_match.json"))
    R = json.load(open(SP + "pfa2_rosters.json"))
    # Hard 404s are the SOURCE naming a man it has no page for. That is neither a
    # fetch I failed nor a man who does not exist, and folding it into either would
    # lose the only fact there is. Read from the fetch report, where the status was
    # recorded at request time -- not inferred later from an absent file, which
    # cannot tell a 404 from a page never asked for.
    fr = SP + "pfa2_fetch_report.json"
    DEAD = {canonical_url(u) for u, _ in
            (json.load(open(fr))["dead_404"] if os.path.exists(fr) else [])}
    codes = R["codes"]
    claims, disagreements, dead, missing = [], [], [], []
    n = collections.Counter()
    cover = collections.defaultdict(lambda: collections.Counter())
    seen = set()

    for code, pid in M["matched"].items():
        url = canonical_url(code)
        if url in seen:
            continue
        seen.add(url)
        h = page(url)
        if h is None:
            (dead if url in DEAD else missing).append(url)
            continue
        r = parse_player(h)
        sr = f"{SRC_ID}#{url}"
        sc = (W.IDX.get(pid) or {}).get("person") or {}
        ys = [int(k.split("|")[1]) for k in codes.get(code, []) if k.split("|")[1].isdigit()]
        bd = band(min(ys)) if ys else "other"
        cover[bd]["people"] += 1

        for f in GAP_FILL:
            if not r[f]:
                continue
            if f == "draft":
                dc = draft_claims(sr, pid, h, r[f])
                claims.extend(dc)
                n["draft"] += 1; n["draft_selection"] += len(dc) - 1
                cover[bd]["draft"] += 1
            else:
                claims.append(claim(sr, pid, FIELD_PREDICATE[f], r[f]))
                n[f] += 1; cover[bd][f] += 1
        if r["position"]:
            claims.append(claim(sr, pid, "pfa.position_career", r["position"]))
            n["position_career"] += 1; cover[bd]["position"] += 1
        if r["birth_date"]:
            claims.append(claim(sr, pid, FIELD_PREDICATE["birth_date"], r["birth_date"]))
            n["birth_date"] += 1; cover[bd]["birth_date"] += 1
            other = (sc.get("birth_date") or [None])[0]
            if other and date_key(r["birth_date"]) and date_key(other) \
                    and date_key(r["birth_date"]) != date_key(other):
                disagreements.append(
                    disagreement(pid, "birth_date", r["birth_date"], other, "statscrew"))
        for row in r["college_rows"]:
            claims.append(claim(sr, pid, "pfa.college_season", row)); n["college_season"] += 1
        if r["college_rows"]:
            cover[bd]["college"] += 1
        if r["college_stated_none"]:
            claims.append({**claim(sr, pid, "pfa.college", "none"), "kind": "absent"})
            n["college_stated_none"] += 1
        for e in r["relatives"]:
            claims.append(kin_claim(sr, pid, e)); n["kin"] += 1
        if r["relatives"]:
            cover[bd]["kin"] += 1
        for e in r["transactions"]:
            claims.append(transaction_claim(sr, pid, e)); n["transaction"] += 1
        if r["transactions"]:
            cover[bd]["transactions"] += 1

    rd = [{"subject": ["person", d["person"]], "field": "club_season_roster",
           "pfa": {"club_season": d["club_season"], "pfa_code": d["pfa_code"]},
           "statscrew": "not on this club-season roster", "other_source": "statscrew",
           "resolved": None, "kind": "derived",
           "_both_are_held": "PFA places him here and the archive does not"}
          for d in M["roster_disagreements"]]
    disagreements.extend(rd)

    leads = M["lead_detail"]
    ld = collections.Counter(); ll = collections.Counter()
    for l in leads:
        ys = [k.split("|") for k in l["club_seasons"]]
        if ys:
            ld[(int(ys[0][1]) // 10) * 10] += 1; ll[ys[0][0]] += 1
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           "claims": claims, "disagreements": disagreements, "leads": leads,
           "counts": {"people_with_claims": len({c["subject"][1] for c in claims}),
                      "claims": len(claims), "by_predicate": dict(n),
                      "birth_date_disagreements": sum(1 for d in disagreements
                                                      if d["field"] == "birth_date"),
                      "roster_disagreements": len(rd),
                      "leads_enumerated_not_fetched": len(leads),
                      "leads_by_decade": {str(k): v for k, v in sorted(ld.items())},
                      "leads_by_league": dict(ll),
                      "pages_missing_from_cache": len(missing),
                      "source_dead_links": len(dead),
                      "coverage_by_band": {k: dict(v) for k, v in sorted(cover.items())}}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-1950on.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    for k in ("people_with_claims", "claims", "birth_date_disagreements",
              "roster_disagreements", "leads_enumerated_not_fetched",
              "pages_missing_from_cache", "source_dead_links"):
        print(f"  {k:32s} {c[k]:,}")
    print("  by predicate:")
    for k, v in sorted(c["by_predicate"].items(), key=lambda x: -x[1]):
        print(f"     {k:22s} {v:,}")
