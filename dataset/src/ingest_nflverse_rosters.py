"""Ingest nflverse historical rosters: birth dates and roster membership. Nothing else.

A THIRD VOICE. Before 1950 the archive heard StatsCrew and PFA and nobody else. This is
a third, and its birth-date coverage before 1950 is 96.7% / 99.5% / 100.0% by decade.

WHAT THIS REFUSES TO WRITE, and the refusals are enforced, not documented:
  headshot_url  a url is not an image. 15 of 20 sampled urls -- fifteen DIFFERENT urls --
                return one byte-identical generic silhouette. Ingesting it would record
                11,701 pre-1950 photographs that do not exist.
  position      the archive holds 324 distinct pre-1950 codes against this source's 19,
                and is more specific on 796 season-pairs against 42.
  college       0.0% populated before 1980.
REFUSED is a set checked inside claim(); there is no path that writes one.

IDENTITY. Name alone is not a route. 2,470 nflverse people match an archive name uniquely
and would be a guess; 286 match a shared name and would be a bug. The routes are
name+birth_date and birth_date-alone, both requiring uniqueness in the archive.

DISAGREEMENTS ARE HELD. And they are found on a join that is NOT the field being
compared -- unique archive name plus a shared season -- because matching on birth date
and then comparing birth dates proves nothing.

  python3 src/ingest_nflverse_rosters.py [--write]
"""
import os, re, csv, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
DECL = json.load(open(os.path.join(BASE, "declarations", "nflverse-rosters.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
ROSTERS = os.path.expanduser("~/Documents/pgm3-sources/nflverse/rosters")
REFUSED = set(DECL["WHAT_IS_REFUSED_AND_WHY"])          # read, never duplicated here
IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
CLUBS = IDX.pop("_clubs", {})
MONTHS = {m: i + 1 for i, m in enumerate(
    "january february march april may june july august september october "
    "november december".split())}


class NflverseError(Exception):
    pass


def iso(s):
    if not s: return None
    s = str(s).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m: return m.group(0)
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$", s)
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return None


def pfield(p, n):
    pr = p.get("person"); v = pr.get(n) if isinstance(pr, dict) else None
    return (v[0] if isinstance(v, list) else v) if v else None


def nk(s):
    s = re.sub(r"\(.*?\)", " ", str(s or ""))
    return re.sub(r"[^a-z]", "", s.lower())


def archive():
    A, byname, bybd, bybdname = {}, collections.defaultdict(list), \
        collections.defaultdict(list), collections.defaultdict(list)
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        yrs = set()
        se = p.get("seasons") or {}
        for key in (se.keys() if isinstance(se, dict) else []):
            pp = str(key).split("|")
            if len(pp) == 3 and pp[1].lstrip("yY").isdigit(): yrs.add(int(pp[1].lstrip("yY")))
        if not yrs: continue
        bd = iso(pfield(p, "birth_date"))
        A[pid] = {"name": p.get("name"), "k": nk(p.get("name")), "bd": bd, "yrs": yrs}
        byname[A[pid]["k"]].append(pid)
        if bd:
            bybd[bd].append(pid); bybdname[(A[pid]["k"], bd)].append(pid)
    return A, byname, bybd, bybdname


def load_rows():
    people, rows = {}, 0
    for f in sorted(glob.glob(ROSTERS + "/roster_*.csv")):
        for x in csv.DictReader(open(f)):
            rows += 1
            k = (nk(x.get("full_name")), iso(x.get("birth_date")))
            r = people.setdefault(k, {"name": x.get("full_name"), "bd": k[1], "seasons": []})
            r["seasons"].append((int(x["season"]), (x.get("team") or "").strip()))
    return people, rows


class Out:
    def __init__(self):
        self.claims = []; self.leads = []; self.unmatchable = []
        self.n = collections.Counter()
        self.disagreements = {"birth_date_vs_statscrew": [], "birth_date_vs_pfa": []}

    def claim(self, pid, predicate, value, year, **extra):
        if not pid:
            raise NflverseError("a claim requires a person; a lead is not a person")
        field = predicate.split(".", 1)[1]
        if field in REFUSED:
            raise NflverseError(f"{field} is refused by the declaration and cannot be written")
        c = {"source_record": f"{SRC_ID}#roster_{year}.csv", "source_id": SRC_ID,
             "stated_by": DECL["stated_by"], "attribution": [DECL["name"]],
             "subject": ["person", pid], "predicate": predicate, "value": value,
             "kind": "observed", "observed_at": f"roster-{year}"}
        c.update(extra)
        self.claims.append(c); self.n[predicate] += 1
        return c


def main():
    write = "--write" in sys.argv
    A, byname, bybd, bybdname = archive()
    people, rowcount = load_rows()
    out = Out(); n = collections.Counter()
    n["rows_read"] = rowcount; n["distinct_people"] = len(people)
    matched = {}
    for k, v in people.items():
        nmk, bd = k
        if bd and len(bybdname.get((nmk, bd), ())) == 1:
            matched[k] = (bybdname[(nmk, bd)][0], "name+birth_date"); n["route_name_and_birth_date"] += 1
        elif bd and len(bybd.get(bd, ())) == 1:
            matched[k] = (bybd[bd][0], "birth_date_alone"); n["route_birth_date_alone"] += 1
        else:
            n["unmatched"] += 1
    # ---- claims
    for k, (pid, route) in matched.items():
        v = people[k]
        if v["bd"]:
            first = min(s for s, _ in v["seasons"])
            out.claim(pid, "nflverse.birth_date", v["bd"], first, match_route=route)
            if not A[pid]["bd"]: n["birth_date_the_archive_lacks"] += 1
        for season, team in sorted(set(v["seasons"])):
            out.claim(pid, "nflverse.roster_membership", f"{season}|{team}", season,
                      season=season, team=team, match_route=route)
    claimed = {c["subject"][1] for c in out.claims}
    # ---- the unmatched split in two, because they are NOT the same thing.
    # A man the archive has never heard of is a LEAD. A man the archive HOLDS but whose
    # birth date it lacks is not a lead -- calling him one would invent a person who is
    # already on the books. The permitted routes cannot reach him, and that is a fact
    # about our key, not about him.
    for k, v in people.items():
        if k in matched: continue
        first = min(s for s, _ in v["seasons"])
        cands = byname.get(k[0]) or []
        shared = [p for p in cands if A[p]["yrs"] & {s for s, _ in v["seasons"]}]
        if len(shared) == 1:
            p0 = shared[0]
            out.unmatchable.append({
                "name_as_printed": v["name"], "nflverse_birth_date": v["bd"],
                "archive_person": p0, "archive_name": A[p0]["name"],
                "archive_birth_date": A[p0]["bd"],
                "shared_seasons": sorted(A[p0]["yrs"] & {s for s, _ in v["seasons"]})[:6],
                "first_season": first,
                "why": ("the archive holds a person of this name sharing a season, but the "
                        "archive has NO birth date for him, so neither permitted route can "
                        "confirm it. Name plus a shared season is NOT a route."
                        if not A[p0]["bd"] else
                        "the archive holds a person of this name sharing a season but the "
                        "birth dates differ; neither permitted route matches."),
                "IS_NOT_A_PERSON": False,
                "IS_NOT_RESOLVED": True,
                # if that archive person ALREADY received claims from a different nflverse
                # identity, this one cannot simply be folded into him: the source is holding
                # two people under one name and only one of them is joined.
                "archive_person_already_has_claims": p0 in claimed,
                "ruling_needed": "promote, reject, or widen the identity routes"})
            n["unmatchable_archive_may_already_hold"] += 1
            if p0 in claimed: n["_unmatchable_whose_archive_person_already_has_claims"] += 1
            if v["bd"] and not A[p0]["bd"]:
                n["nflverse_has_a_birth_date_the_archive_lacks"] += 1
                if first < 1950: n["_of_those_pre_1950"] += 1
            continue
        why = ("no archive person carries this name and birth date, and the birth date is "
               "not unique in the archive" if v["bd"] else "this source gives no birth date, "
               "and name alone is not a route")
        out.leads.append({
            "lead_id": f"lead-nvr-{len(out.leads)+1:05d}",
            "category": "unmatched_no_candidate",
            "name_as_printed": v["name"], "birth_date": v["bd"],
            "source_id": SRC_ID, "source_record": f"{SRC_ID}#roster_{first}.csv",
            "first_season": first,
            "places_on": [{"year": s, "team": t} for s, t in sorted(set(v["seasons"]))][:12],
            "why_matching_failed": why,
            "same_name_in_archive": len(cands),
            "candidate_person": None, "IS_NOT_A_PERSON": True})
        n["leads"] += 1
        if first < 1950: n["leads_first_season_pre_1950"] += 1
    # ---- disagreements, on a join that is not the field compared
    pfa_bd = {}
    pf = os.path.join(BASE, "build", "pfa-pre1950.json")
    if os.path.exists(pf):
        for c in json.load(open(pf)).get("claims") or []:
            if c.get("predicate") == "pfa.birth_date":
                s = c.get("subject")
                if isinstance(s, list) and len(s) > 1: pfa_bd[s[1]] = iso(c.get("value")) or c.get("value")
    for k, v in people.items():
        cands = byname.get(k[0]) or []
        if len(cands) != 1 or not v["bd"]: continue
        pid = cands[0]
        if not (A[pid]["yrs"] & {s for s, _ in v["seasons"]}): continue
        if A[pid]["bd"] and A[pid]["bd"] != v["bd"]:
            out.disagreements["birth_date_vs_statscrew"].append(
                {"person": pid, "name": v["name"], "nflverse": v["bd"],
                 "statscrew": A[pid]["bd"], "ruling": "UNRESOLVED - both held"})
        if pfa_bd.get(pid) and pfa_bd[pid] != v["bd"]:
            out.disagreements["birth_date_vs_pfa"].append(
                {"person": pid, "name": v["name"], "nflverse": v["bd"],
                 "pfa": pfa_bd[pid], "ruling": "UNRESOLVED - both held"})
    n["disagree_birth_date_vs_statscrew"] = len(out.disagreements["birth_date_vs_statscrew"])
    n["disagree_birth_date_vs_pfa"] = len(out.disagreements["birth_date_vs_pfa"])
    doc = {"source": {k: DECL[k] for k in ("source_id", "name", "stated_by", "acquisition")},
           "REFUSED_FIELDS": sorted(REFUSED),
           "claims": out.claims, "leads": out.leads,
           "unmatchable_not_leads": out.unmatchable,
           "disagreements": out.disagreements, "counts": dict(n) | dict(out.n)}
    if write:
        import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import index_io as IO
        IO.dump_atomic(doc, os.path.join(BASE, "build", "nflverse-rosters.json"), indent=1)  # 77 MB, gitignored: never in place
    for kk in sorted(doc["counts"]): print(f"  {kk:36s} {doc['counts'][kk]}")
    if write: print("\nwrote build/nflverse-rosters.json")
    return doc


if __name__ == "__main__":
    main()
