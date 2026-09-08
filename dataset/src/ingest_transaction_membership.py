"""Stage 2 of roster-membership-as-a-claim: the PFA transactions. Dry-run until ruled.

ONE PREDICATE PER DEFINITION, AND TRANSACTIONS NEED SEVERAL. A man signed in July
and released in August was associated with the club and never on its roster in
StatsCrew's sense. A man on injured reserve was on the roster and never played. A
man activated from the practice squad was, for certain, on the active roster.
Those are different facts and do not share a predicate.

THE VOCABULARY IS 433 TYPES and was read in full before this was written. It
carries the source's own typos ('Trdaed', 'Excluisve Rights Free Agent',
'Released (Ijnured)'), its own uncertainty marks ('Signed?', 'Reserve/?'), CFL
abbreviations ('TR-OTT', 'LOAN-JAC', 'S-CFL'), and about fifty rows where the CLUB
STRING has leaked into the type column ('2007 Atlanta Falcons (NFL) 2007 ATL
NFL'). The raw type is kept verbatim on every claim; grouping is by meaning, and
the leaked rows are counted as unparseable, never mapped.

DIRECTION WAS MEASURED, NOT ASSUMED. 'Free Agent' looks like an arrival and is a
DEPARTURE: in 23,906 of 31,807 sequences the row before it is the same club, and
the sequence reads Signed -> Free Agent -> next club. Its 25,686 rows go with
Released. 'Traded' and 'Assigned on Waivers' are checked the same way below.

CLUB STRINGS RESOLVE THROUGH build/clubs.json. Every refusal is counted by league
and reason. Leagues Ryan ruled OUT -- ACFL, COFL, PCFL, AFA, ORFU, DFL, MWFL --
are measured and nothing from them is written.

  python3 src/ingest_transaction_membership.py [--dry]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
from clubs import Clubs

SRC_ID = "pfa-transactions"
OUT = os.path.join(BASE, "build", "pfa-transaction-membership.json")
TEAM = re.compile(r"^(\d{4})\s+([A-Z0-9\-]+)\s+([A-Z0-9]+)$")          # '2014 TB NFL'
CTX = re.compile(r"^(\d{4})\s+(.+?)\s+\(([A-Z0-9]+)\)$")                   # '1946 Chicago Cardinals (NFL)'
RUN = re.compile(r"^(\d{4})\s+(.+?)\s+\1\s+([A-Z0-9\-]+)$")                # '1938 Cincinnati Bengals 1938 CINB'
LEAKED = re.compile(r"^\d{4} .+ \d{4} [A-Z0-9\-]+( [A-Z0-9]+)?$")
TYPEWORDS = {"signed", "released", "draft", "traded", "free agent", "activated", "retired"}


def club_of(v):
    """-> (year, club_string, league_or_None, shape) or (None, None, None, why).

    THE TEAM FIELD HAS THREE SHAPES, and the first version read one of them and
    threw 62,926 rows away -- 15.6% of the source -- as 'unparseable'. They were
    not. 'Chicago Cardinals' with season_context '1946 Chicago Cardinals (NFL)'
    is the commonest shape in the whole store (~59,000 rows); the year and league
    live one field over. A parser that reads one shape and reports the rest as a
    source defect is reporting its own gap.

    About 310 rows have the TEAM and TYPE columns swapped ('Signed' in team,
    '1917 Toledo Maroons 1917 TOLM' in type). Those are recognised and swapped
    back, and counted, rather than mapped as a club called 'Signed'."""
    team = (v.get("team") or "").strip(); typ = (v.get("type") or "").strip(); ctx = (v.get("season_context") or "").strip()
    if team.lower() in TYPEWORDS and (RUN.match(typ) or LEAKED.match(typ)):
        team, typ = typ, team                                   # swapped columns
        v = dict(v, type=typ, _columns_swapped=True)
    m = TEAM.match(team)
    if m: return int(m.group(1)), m.group(2), m.group(3), "code", v
    m = RUN.match(team)
    if m: return int(m.group(1)), m.group(2), None, "name_and_code_run_together", v
    m = CTX.match(ctx)
    if m and team:
        return int(m.group(1)), team, m.group(3), "name_with_context", v
    if m and not team:
        return int(m.group(1)), m.group(2), m.group(3), "context_only", v
    return None, None, None, f"no year in team {team!r} or context {ctx!r}", v

IN_SCOPE = {"NFL", "APFA", "AAFC", "AFL", "AFL1", "AFL2", "AFL3", "AFL4", "CFL", "IRFU", "WIFU",
            "WFL", "USFL", "USFL2", "XFL", "XFL2", "XFL3", "UFL", "UFL2", "AAF", "ARFL", "NFLE", "WLAF"}
RULED_OUT = {"ACFL", "COFL", "PCFL", "AFA", "ORFU", "DFL", "MWFL"}

# ---- the proposed predicate set -------------------------------------------
# predicate -> (definition, limitation). Grouping is by what the transaction
# ATTESTS about the man and the club, never by the label.
PREDICATES = {
    "roster_membership.drafted_by": (
        "the club acquired the man's rights in a draft",
        "a draft pick is a right, not a roster spot; a drafted man who never signed was never on the club"),
    "roster_membership.signed": (
        "the club signed the man to a contract",
        "signed is not rostered: a man signed in July and released in August never made the roster"),
    "roster_membership.acquired": (
        "the club acquired the man by trade, waiver claim, purchase, loan or recall",
        "acquired is not rostered; the man may have been cut before playing"),
    "roster_membership.on_active_roster": (
        "the man was activated to, or elevated to, the club's active roster",
        "attests one point in time; says nothing about how long he stayed"),
    "roster_membership.on_reserve": (
        "the man was on one of the club's reserve lists: injured, physically unable, suspended, military, "
        "did not report, retired, COVID, non-football injury or illness",
        "on a reserve list is a roster status, and most of these men did not play that season"),
    "roster_membership.practice_squad": (
        "the man was on the club's practice, taxi or developmental squad",
        "a practice squad is not the roster; an elevation is recorded under on_active_roster"),
    "roster_membership.departed": (
        "the man left the club: released, waived, became a free agent, retired, rights released, deceased, "
        "or the contract or trade was voided",
        "a departure implies prior association but is negative evidence about the season roster"),
    "roster_membership.rights_retained": (
        "the club retained the man's rights by designating him a franchise or transition player",
        "a tag is the OPPOSITE of a departure -- it keeps him. 173 rows; a claim that says the "
        "opposite of what happened is exactly what one-predicate-per-definition exists to prevent"),
    "roster_membership.transaction_unstated": (
        "PFA lists a transaction row for this club-season with no type printed",
        "the association exists; its kind is unknown -- 30,454 rows, almost all pre-1950 and undated"),
}


def norm_type(t):
    t = (t or "").strip().lower().rstrip("?").strip()
    t = re.sub(r"\s+", " ", t)
    # the source's own typos, folded ONLY for grouping -- the raw string stays on the claim
    for a, b in (("trdaed", "traded"), ("excluisve", "exclusive"), ("exlcusive", "exclusive"),
                 ("agnet", "agent"), ("ijnured", "injured"), ("settement", "settlement"),
                 ("phyiscal", "physical"), ("assgned", "assigned"), ("negotation", "negotiation"),
                 ("rleleased", "released"), ("didnot", "did not"), ("release (", "released ("),
                 ("traded voided", "trade voided")):
        t = t.replace(a, b)
    return t


def classify(raw):
    """-> predicate or 'unparseable' or 'unclassified'."""
    if LEAKED.match((raw or "").strip()):
        return "unparseable"
    t = norm_type(raw)
    if not t:
        return "roster_membership.transaction_unstated"
    if "draft" in t and "declared ineligible" not in t:
        return "roster_membership.drafted_by"
    if t.startswith("activated") or t == "practice squad elevation" or t.startswith("exemption") \
            or t in ("s-ex", "restored"):
        return "roster_membership.on_active_roster"
    if t.startswith("practice") or t.startswith("taxi") or "developmental squad" in t \
            or t == "restored to practice squad" or "practice squad" in t:
        return "roster_membership.practice_squad"
    if t.startswith("reserve") or t.startswith("injured") or t in ("disabled", "disabled list", "il", "res",
            "inj", "injured", "ia", "exempt/left squad", "exempt") or t.startswith("reserve ("):
        return "roster_membership.on_reserve"
    # RYAN'S RULING: the tags get their own predicate. Checked BEFORE the free-agent
    # test below, or 'Free Agent (Franchise Tag)' would fall through to departed.
    if "(franchise tag)" in t or "(transition tag)" in t:
        return "roster_membership.rights_retained"
    if t.startswith("released") or t.startswith("free agent") or "free agent" in t or t.startswith("retired") \
            or t in ("deceased", "contract voided", "trade voided", "rights released", "selection declared ineligible",
                     "waived", "cut", "fa", "ret", "franchise free agent", "r fa", "rfa") \
            or t.startswith("trade voided") or t.startswith("released"):
        return "roster_membership.departed"
    if t.startswith("signed") or t in ("purchased", "allocated", "allocated (national)", "s-cfl") \
            or t.startswith("allocated"):
        return "roster_membership.signed"
    if t.startswith("traded") or t.startswith("assigned on waivers") or t in ("acquired", "obtained", "loaned",
            "recalled from farm team", "returned", "return", "waivers recalled", "rights traded",
            "negotiation rights traded", "t", "ga") or t.startswith("tr-") or t.startswith("loan"):
        return "roster_membership.acquired"
    return "unclassified"


def main(write=False):
    C = Clubs()
    rows = []
    for f in ("pfa-pre1950.json", "pfa-1950on.json"):
        for x in json.load(open(os.path.join(BASE, "build", f)))["claims"]:
            if x["predicate"] == "pfa.transaction":
                rows.append((x["subject"][1], x["value"], x["source_record"]))

    # direction check for the two remaining ambiguous arrivals
    by = collections.defaultdict(list)
    for pid, v, sr in rows: by[pid].append(v)
    direction = {}
    for typ in ("Traded", "Assigned on Waivers"):
        same = diff = 0
        for pid, rs in by.items():
            rs = sorted(rs, key=lambda r: r.get("printed_row", 0))
            for i, r in enumerate(rs):
                if (r.get("type") or "").strip() == typ and i:
                    if rs[i - 1].get("team") == r.get("team"): same += 1
                    else: diff += 1
        direction[typ] = {"prev_same_club": same, "prev_other_club": diff}

    n = collections.Counter(); bypred = collections.Counter(); rawtypes = collections.defaultdict(collections.Counter)
    league_seen = collections.Counter(); scope = collections.Counter()
    unparseable, unclassified = collections.Counter(), collections.Counter()
    per = {}
    shapes = collections.Counter(); nofield = collections.Counter()
    for pid, v, sr in rows:
        n["transactions"] += 1
        year, pfa_code, league, shape, v = club_of(v)
        if year is None:
            n["team_field_unparseable"] += 1; nofield[shape] += 1; continue
        shapes[shape] += 1
        if v.get("_columns_swapped"): n["columns_swapped_and_restored"] += 1
        if league is None:
            # no league printed anywhere: the club table decides, or refuses
            r0 = C.resolve(pfa_code, year, None, source="pfa_transaction")
            league = C.league_for(r0[0], year) if r0 else None
            if league is None:
                n["rows_no_league_and_unresolvable"] += 1
                C._refuse(pfa_code, year, "?", "pfa_transaction", "no league printed and the table cannot place the string"); continue
        league_seen[league] += 1
        if league in RULED_OUT:
            scope["ruled_out_rows"] += 1; scope[("ruled_out", league)] += 1; continue
        if league not in IN_SCOPE:
            scope["league_not_ruled_on_rows"] += 1; scope[("not_ruled_on", league)] += 1; continue
        pred = classify(v.get("type"))
        rawtypes[pred][(v.get("type") or "")] += 1
        if pred == "unparseable":
            unparseable[(v.get("type") or "")] += 1; continue
        if pred == "unclassified":
            unclassified[(v.get("type") or "")] += 1; continue
        r = C.resolve(pfa_code, year, league, source="pfa_transaction")
        if not r:
            n["rows_unresolved_club"] += 1; continue
        cid, how = r
        code = C.code_for(cid, year)
        if not code:
            C._refuse(pfa_code, year, league, "pfa_transaction", "club known, no code-segment covers that year")
            n["rows_club_without_season"] += 1; continue
        key = (pid, league, year, cid, pred)
        e = per.setdefault(key, {"code": code, "pfa_code": pfa_code, "resolved_as": how, "transactions": []})
        e["transactions"].append({"type_as_printed": v.get("type") or "", "date": v.get("date"),
                                  "dated": bool(v.get("dated")), "printed_row": v.get("printed_row"),
                                  "season_context": v.get("season_context"), "source_record": sr})

    claims = []
    for (pid, league, year, cid, pred), e in sorted(per.items()):
        d, lim = PREDICATES[pred]
        claims.append({"source_record": e["transactions"][0]["source_record"], "source_id": SRC_ID,
                       "stated_by": "Pro Football Archives",
                       "attribution": ["Pro Football Archives (profootballarchives.com), player transactions"],
                       "subject": ["person", pid], "predicate": pred,
                       "value": f"{league}|{year}|{e['code']}",
                       "kind": "observed", "observed_at": "fetched-2026-09",
                       "definition": d, "definition_limitation": lim,
                       "club_id": cid, "club_code": e["code"], "club_as_printed": e["pfa_code"],
                       "club_resolved_as": e["resolved_as"], "league": league, "year": year,
                       "transactions": e["transactions"],
                       "types_as_printed": sorted({t["type_as_printed"] for t in e["transactions"]})})
        bypred[pred] += 1
    dup = collections.Counter((c["subject"][1], c["value"], c["predicate"]) for c in claims)
    assert not [k for k, v in dup.items() if v > 1], "one claim per (man, club-season, predicate) violated"

    refusals = C.census()
    out = {"source": {"source_id": SRC_ID, "stated_by": "Pro Football Archives", "acquisition": "fetched",
                      "predicates": PREDICATES, "_stage": "2 of 4",
                      "_direction_measured": {"Free Agent": "departure -- 23,906 of 31,807 preceded by the same club",
                                              **direction}},
           "claims": claims,
           "unresolved_club_strings": [{"league": lg, "year": y, "string": s, "why": why, "rows": k}
                                       for lg, y, s, why, k, _ in refusals],
           "unparseable_types": dict(unparseable), "unclassified_types": dict(unclassified),
           "raw_types_by_predicate": {p: dict(c.most_common()) for p, c in rawtypes.items()},
           "out_of_scope": {str(k): v for k, v in scope.items()},
           "leagues_seen": dict(league_seen.most_common()),
           "team_field_shapes": dict(shapes), "team_field_failures": dict(nofield.most_common(10)),
           "counts": {**dict(n), "claims": len(claims), "claims_by_predicate": dict(bypred),
                      "club_seasons_attested": len({c["value"] for c in claims}),
                      "people": len({c["subject"][1] for c in claims}),
                      "unresolved_club_strings": len(refusals), "unresolved_rows": sum(r[4] for r in refusals),
                      "unparseable_rows": sum(unparseable.values()),
                      "unclassified_rows": sum(unclassified.values())}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, OUT, indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    for k, v in c.items():
        if k != "claims_by_predicate": print(f"  {k:28s} {v:,}" if isinstance(v, int) else f"  {k}: {v}")
    print("  claims by predicate:")
    for p, v in sorted(c["claims_by_predicate"].items(), key=lambda x: -x[1]): print(f"     {v:8,}  {p}")
    print("  direction:", json.dumps(o["source"]["_direction_measured"]))
    print(f"  unclassified types ({len(o['unclassified_types'])}):", dict(sorted(o["unclassified_types"].items(), key=lambda x: -x[1])[:25]))
    print(f"  unparseable (club string in type column): {c['unparseable_rows']} rows, {len(o['unparseable_types'])} strings")
    print("  team field shapes:", o["team_field_shapes"])
    print("  team field failures:", o["team_field_failures"])
    print("  out of scope:", o["out_of_scope"])
    json.dump(o, open("/tmp/stage2_dry.json", "w"))
