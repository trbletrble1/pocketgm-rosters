"""Ingest Pro Football Archives COACH pages. Writes dataset/build/pfa-coaches.json.

The point is the role vocabulary. PFA prints coaching roles as the period
printed them -- 'Defensive Front Seven', 'Offensive Backs', 'Line', 'Chief
Offense' -- where every other store on disk has normalised them to modern
titles. So the one rule that matters: the `Position` cell is stored EXACTLY as
printed, whole, unsplit. See declarations/pfa-coaches.json.

Identity is the PFA code on the PFA side (4,553 listings, 3,903 codes) and one
of three routes to an archive person, never the name alone. An unresolved coach
is a LEAD with every field, in the player-lead structure.
"""
import os, re, sys, json, collections, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_pfa import claim, kin_claim, disagreement, date_key, SRC_ID, DECL as SRC_DECL, PFAError
from pfa_coach_pages import parse_coach, load, CACHE, CoachPageError

DECL = json.load(open(os.path.join(BASE, "declarations", "pfa-coaches.json"), encoding="utf-8"))
LISTS = ("nfl-head-coaches", "nfl-assistant-coaches", "cfl-head-coaches", "cfl-assistant-coaches")
BIO_FIELDS = {"birth_date": "pfa.birth_date", "birth_place": "pfa.birth_place",
              "death_date": "pfa.death_date", "death_place": "pfa.death_place",
              "high_school": "pfa.high_school", "military_service": "pfa.military_service",
              "height": "pfa.height", "weight": "pfa.weight"}


class PFACoachError(Exception):
    pass


def norm(n):
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode()
    n = re.sub(r"\(.*?\)", "", n)
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


def nclub(n):
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def club_printed(row):
    return re.sub(r"^\d{4} ", "", re.sub(r"\s*\(.*?\)$", "", row.get("printed_long") or ""))


# ------------------------------------------------------------------ the source
def listings():
    rows = []
    for lst in LISTS:
        t = open(os.path.join(CACHE, lst + ".html"), encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'<a href="/coaches/([a-z0-9]+)\.html"[^>]*>(.*?)</a>', t):
            rows.append({"code": m.group(1), "name_in_list": re.sub("<[^>]+>", "", m.group(2)).strip(), "list": lst})
    return rows


def official_codes():
    t = open(os.path.join(CACHE, "officials.html"), encoding="utf-8", errors="ignore").read()
    return set(re.findall(r'href="/officials/([a-z0-9]+)\.html"', t))


# ------------------------------------------------------------------ the archive side
class Archive:
    def __init__(self):
        IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
        self.CL = IDX.pop("_clubs", {})
        self.people = IDX
        self.by_name = collections.defaultdict(list)
        self.by_name_bd = collections.defaultdict(list)
        self.coach_stints = collections.defaultdict(set)
        for pid, p in IDX.items():
            nm = norm(p.get("name")); self.by_name[nm].append(pid)
            bd = (p.get("person") or {}).get("birth_date"); bd = bd[0] if isinstance(bd, list) and bd else bd
            if date_key(bd): self.by_name_bd[(nm, date_key(bd))].append(pid)
            for k in p.get("seasons") or {}:
                if k.startswith("COACHES|"):
                    _, y, club = k.split("|", 2); y = int(y[1:5])
                    self.coach_stints[(nm, y, nclub(self.club_name(club, y)))].add(pid)
                    self.coach_stints[(nm, y, nclub(club))].add(pid)
        # PFA player codes -> person, and every (person, predicate, value) PFA already states
        self.player_code = {}; self.held = set(); self.held_vals = collections.defaultdict(list)
        for fn in ("pfa-pre1950.json", "pfa-1950on.json"):
            fp = os.path.join(BASE, "build", fn)
            if not os.path.exists(fp): continue
            for c in json.load(open(fp))["claims"]:
                code = c["source_record"].split("#", 1)[1]
                self.player_code.setdefault(code, set()).add(c["subject"][1])
                self.held.add((c["subject"][1], c["predicate"], json.dumps(c["value"], sort_keys=True)))
                if c["predicate"] in BIO_FIELDS.values():
                    self.held_vals[(c["subject"][1], c["predicate"])].append(c["value"])
        # the three coaching stores, as (pid or name, year, club) -> [role, is_head_coach]
        ident = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
        local = {}
        for pid, v in ident.items():
            for src, lid in v.get("local", []): local[(src, lid)] = pid
        self.stores = {}
        for fn, src, key in (("coaches.json", "coaching-tree", "coaches"), ("coaches-nfl.json", "statscrew", "coaches-nfl")):
            d = json.load(open(os.path.join(BASE, "build", fn)))
            hc = {tuple(c["subject"]): c["value"] for c in d["claims"] if c["predicate"] == "is_head_coach"}
            # the Coaching Tree person carries NO name in the person index (its name
            # is the store's own slug, coach/george-allen). The slug is the only name
            # there is, so it is read back for the join and for the coaching
            # club-season identity route. It is a within-source key: it is never
            # evidence on its own, only with a shared club-season.
            slug_name = {}
            for c in d["claims"]:
                if src == "coaching-tree":
                    slug = c["source_record"].split("#coach/")[-1]
                    slug_name.setdefault(c["subject"][1], slug.replace("-", " "))
            st = collections.defaultdict(list); unmapped = 0
            for c in d["claims"]:
                if c["predicate"] != "role_title": continue
                _, lp, club, y = c["subject"]; pid = local.get((key, lp))
                if not pid: unmapped += 1; continue
                y = int(y[1:5])
                row = {"club": nclub(self.club_name(club, y)), "club_as_held": club,
                       "role": c["value"], "is_head_coach": hc.get(tuple(c["subject"])), "pid": pid}
                st[(pid, y)].append(row)
                nm = slug_name.get(lp) or norm(self.people.get(pid, {}).get("name"))
                if nm:
                    st[(norm(nm), y)].append(row)
                    self.coach_stints[(norm(nm), y, row["club"])].add(pid)
                    self.coach_stints[(norm(nm), y, nclub(club))].add(pid)
            self.stores[src] = {"by_pid_year": st, "stints": sum(len(v) for v in st.values() if isinstance(v, list)) // 2 if src == "coaching-tree" else sum(len(v) for k, v in st.items() if isinstance(k[0], str) and k[0].startswith("P_")),
                                "unmapped_local_ids": unmapped, "slug_named": len(slug_name)}
        d = json.load(open(os.path.join(BASE, "build", "assistants.json")))
        names = {c["subject"][1]: c["value"] for c in d["claims"] if c["predicate"] == "name"}
        st = collections.defaultdict(list)
        for c in d["claims"]:
            if c["predicate"] != "role_title": continue
            _, lp, club, y = c["subject"]; y = int(y[1:5])
            st[(norm(names.get(lp, "")), y)].append({"club": nclub(club), "club_as_held": club, "role": c["value"], "is_head_coach": None})
        self.stores["media-guides"] = {"by_name_year": st, "stints": sum(len(v) for v in st.values()), "unmapped_local_ids": 0}

    def club_name(self, club, y):
        return self.CL.get(f"{club}|{y}") or club


# ------------------------------------------------------------------ identity
def resolve(A, d):
    """Three routes, every one of them structural or exact. Returns (pid, routes, why)."""
    nm = norm(d["name"]); cands = {}; notes = []; amb = {}
    if d["links"]["players"]:
        pc = d["links"]["players"][0]; url = f"players/{pc[0]}/{pc}.html"
        pids = A.player_code.get(url, set())
        if len(pids) == 1: cands["playing_record"] = next(iter(pids))
        elif len(pids) > 1: notes.append(f"playing record {url} resolves to {len(pids)} people")
        else: notes.append(f"playing record {url} is not resolved by stages one or two")
    hits = set()
    for s in d["seasons"]:
        if s["section"] != "REGULAR SEASON": continue
        for key in ((nm, s["year"], nclub(club_printed(s))), (nm, s["year"], nclub(s["club"]))):
            hits |= A.coach_stints.get(key, set())
    if len(hits) == 1: cands["name+coaching_club_season"] = next(iter(hits))
    elif len(hits) > 1:
        notes.append(f"{len(hits)} archive people of this name share his coaching club-seasons")
        amb["name+coaching_club_season"] = sorted(hits)
    bd = date_key(d["bio"].get("birth_date"))
    if bd:
        pids = A.by_name_bd.get((nm, bd), [])
        if len(pids) == 1: cands["name+birth_date"] = pids[0]
        elif len(pids) > 1:
            notes.append(f"{len(pids)} archive people share this name and birth date")
            amb["name+birth_date"] = sorted(pids)
    if len(set(cands.values())) > 1:
        return None, cands, "route_conflict"
    if cands:
        return next(iter(cands.values())), sorted(cands), None
    if notes: return None, amb, "ambiguous_candidates: " + "; ".join(notes)
    if A.by_name.get(nm): return None, {}, "namesake_only_not_evidence"
    return None, {}, "unmatched_no_candidate"


# ------------------------------------------------------------------ claims
def season_claim(sr, pid, row):
    v = {"year": row["year"], "league": row["league"], "club": row["club"],
         "club_as_printed": row["printed_long"], "position_as_printed": row["position_as_printed"],
         "conference": row["conference"], "division": row["division"], "seq": row["seq"],
         "finish": row["finish"], "club_record_as_printed": row["club_record"], "club_page": row["href"]}
    for fl in ("href_disagrees_with_printed_cell", "no_club_page", "row_width_differs_from_header"):
        if row.get(fl): v[fl] = row[fl]
    c = claim(sr, pid, "pfa.coaching_season" if row["section"] == "REGULAR SEASON" else "pfa.coaching_playoffs", v)
    c["_position_as_printed_is_verbatim_and_unsplit"] = True
    # THE SUBJECT IS A STINT, NOT A PERSON. Ruled 2026-09-09, and it is the repair the
    # statistics ingest already had. A person subject leaves club_id and year NULL in the
    # read model -- the club and the year sit inside the value, where the model never
    # looks -- so 41,316 of 48,582 coaching claims could not be found by any "who coached
    # this club-season" question. The 2024 Chicago Bears showed one man. The club code and
    # the league are already in every row; nothing is inferred here.
    if row.get("club") and row.get("league") and row.get("year"):
        c["subject"] = ["stint", pid, str(row["club"]), f"{row['league']}-{row['year']}"]
    else:
        # A row PFA prints with no club stays person-scoped and is counted, never guessed.
        c["_no_club_on_the_row_so_the_subject_stays_person_scoped"] = True
    return c


def lead_record(n, d, code, why, cands, lists, also_official):
    first = next((s for s in d["seasons"] if s["section"] == "REGULAR SEASON"), None) or (d["seasons"][0] if d["seasons"] else None)
    b = d["bio"]
    return {"lead_id": f"lead-pfa-coach-{n:05d}", "category": why.split(":")[0],
            "name_as_printed": d["name"], "printed_full_name": d["printed_full_name"],
            "places_on": [first["league"], first["year"], first["club"]] if first else None,
            "source_id": SRC_ID, "source_record": f"{SRC_ID}#coaches/{code}.html",
            "pfa_url": f"coaches/{code}.html", "pfa_code": code, "lists": sorted(lists),
            "also_in_officials_list": also_official,
            "candidate_person": ({r: p for r, p in cands.items()} if cands else None),
            "IS_NOT_A_PERSON": True, "why_matching_failed": why,
            "fields": {k: b.get(k, "") for k in ("high_school", "height", "weight", "birth_place", "death_place",
                                                  "birth_date", "death_date", "draft", "military_service", "position")},
            "college_rows": b["college_rows"], "relatives": b["relatives"], "transactions": [],
            "coaching_seasons": d["seasons"], "rows_without_club": d["rows_without_club"]}


# ------------------------------------------------------------------ the coaching stores
def compare(A, pid, name, rows, out, pairs):
    by_year = collections.defaultdict(list)
    for r in rows:
        if r["section"] == "REGULAR SEASON": by_year[r["year"]].append(r)
    for src, store in A.stores.items():
        table = store.get("by_pid_year") or store.get("by_name_year")
        keys = [pid, norm(name)] if "by_pid_year" in store else [norm(name)]
        years = set(by_year) | {y for (k, y) in table if k in keys}
        for y in sorted(years):
            pf = list(by_year.get(y, []))
            st = list(table.get((keys[0], y), [])) or (list(table.get((keys[1], y), [])) if len(keys) > 1 else [])
            for r in pf:
                pc = {nclub(club_printed(r)), nclub(r["club"])}
                m = next((s for s in st if s["club"] in pc), None)
                rec = {"subject": ["person", pid], "year": y, "pfa_club": r["club"], "pfa_club_as_printed": r["printed_long"],
                       "pfa_position_as_printed": r["position_as_printed"], "store": src, "resolved": None, "kind": "derived"}
                if m is None:
                    rec.update(comparison="season_in_pfa_not_in_store"); out.append(rec); continue
                st.remove(m)
                rec.update(store_club_as_held=m["club_as_held"], store_role_title=m["role"], store_is_head_coach=m["is_head_coach"])
                if m.get("pid") and m["pid"] != pid:
                    rec["store_person"] = m["pid"]
                    rec["_archive_holds_this_man_twice"] = "the store's person and the PFA-resolved person differ; joined by name and club-season"
                a, b = r["position_as_printed"], m["role"]
                if a == b: rec["comparison"] = "role_string_identical"
                elif a.casefold() == b.casefold(): rec["comparison"] = "role_string_differs_in_case_only"
                else:
                    rec["comparison"] = "role_string_differs"
                    rec["_not_a_conflict_about_a_fact"] = "one source may preserve what the other normalised; both strings are held and the mapping is a ruling not yet made"
                    pairs[(a, b, src)] += 1
                out.append(rec)
            for m in st:
                out.append({"subject": ["person", pid], "year": y, "store": src, "store_club_as_held": m["club_as_held"],
                            "store_role_title": m["role"], "comparison": "season_in_store_not_in_pfa", "resolved": None, "kind": "derived"})


# ------------------------------------------------------------------ main
def main(write=True):
    A = Archive()
    L = listings(); by_code = collections.defaultdict(set)
    for r in L: by_code[r["code"]].add(r["list"])
    codes = sorted(f[8:-5] for f in os.listdir(CACHE) if f.startswith("coaches_"))
    if set(codes) != set(by_code):
        raise PFACoachError(f"pages on disk ({len(codes)}) != codes in the four lists ({len(by_code)})")
    officials = official_codes(); shared = sorted(set(codes) & officials)
    claims, leads, cmp, n = [], [], [], collections.Counter()
    bd_dis, intra, pairs = [], [], collections.Counter()
    vocab = collections.Counter(); people = {}; routes = collections.Counter(); flags = collections.Counter()
    for code in codes:
        d = parse_coach(load(code), code)
        pid, cands, why = resolve(A, d)
        for s in d["seasons"]:
            if s["section"] == "REGULAR SEASON": vocab[s["position_as_printed"]] += 1
            for fl in ("href_disagrees_with_printed_cell", "no_club_page", "row_width_differs_from_header"):
                if s.get(fl): flags[fl] += 1
        n["rows_without_club"] += len(d["rows_without_club"])
        if not pid:
            leads.append(lead_record(len(leads) + 1, d, code, why, cands, by_code[code], code in officials))
            n["lead:" + why.split(":")[0]] += 1; continue
        routes["+".join(cands)] += 1
        sr = f"{SRC_ID}#coaches/{code}.html"
        people[code] = {"person": pid, "routes": cands, "lists": sorted(by_code[code]),
                        "also_in_officials_list": code in officials, "canonical_url": f"coaches/{code}.html"}
        for s in d["seasons"]:
            claims.append(season_claim(sr, pid, s)); n["coaching_season" if s["section"] == "REGULAR SEASON" else "coaching_playoffs"] += 1
        b = d["bio"]
        for f, pred in BIO_FIELDS.items():
            v = b.get(f, "")
            if not v: continue
            same = (pid, pred, json.dumps(v, sort_keys=True)) in A.held
            if same: n["bio_already_on_player_page"] += 1; continue
            other = A.held_vals.get((pid, pred), [])
            claims.append(claim(sr, pid, pred, v)); n[f] += 1
            if other:
                intra.append({"subject": ["person", pid], "field": f, "coach_page": v, "player_page": other[0],
                              "resolved": None, "kind": "derived", "_both_are_held": "the same source states two values on two of its own pages"})
        if b["birth_date"]:
            held = (A.people.get(pid) or {}).get("person", {}).get("birth_date")
            held = held[0] if isinstance(held, list) and held else held
            if held and date_key(held) and date_key(b["birth_date"]) and date_key(held) != date_key(b["birth_date"]) \
                    and (pid, "pfa.birth_date", json.dumps(b["birth_date"])) not in A.held:
                bd_dis.append(disagreement(pid, "birth_date", b["birth_date"], held, "statscrew"))
        for row in b["college_rows"]:
            if (pid, "pfa.college_season", json.dumps(row, sort_keys=True)) in A.held: n["bio_already_on_player_page"] += 1; continue
            claims.append(claim(sr, pid, "pfa.college_season", row)); n["college_season"] += 1
        if b["college_stated_none"] and (pid, "pfa.college", '"none"') not in A.held:
            claims.append({**claim(sr, pid, "pfa.college", "none"), "kind": "absent"}); n["college_stated_none"] += 1
        for e in b["relatives"]:
            if (pid, "pfa.kin", json.dumps(e, sort_keys=True)) in A.held: n["bio_already_on_player_page"] += 1; continue
            claims.append(kin_claim(sr, pid, e)); n["kin"] += 1
        if d["printed_full_name"]:
            claims.append(claim(sr, pid, "pfa.name_as_printed", {"name": d["name"], "full": d["printed_full_name"]})); n["name_as_printed"] += 1
        if b.get("draft"): n["draft_present_not_written"] += 1
        compare(A, pid, d["name"], d["seasons"], cmp, pairs)
    by_store = collections.defaultdict(collections.Counter)
    for c in cmp: by_store[c["store"]][c["comparison"]] += 1
    out = {"source": {**{k: SRC_DECL[k] for k in ("source_id", "name", "stated_by", "acquisition")}, "body": "coaches",
                      "declaration": "declarations/pfa-coaches.json"},
           "claims": claims, "leads": leads,
           "people": people,
           "officials_sharing_a_coach_code": {"codes": shared, "rule": "one record, canonical URL under /coaches/",
                                              "n": len(shared)},
           "listings": {"rows": len(L), "distinct_codes": len(by_code),
                        "by_list": collections.Counter(r["list"] for r in L),
                        "codes_in_more_than_one_list": sum(1 for v in by_code.values() if len(v) > 1)},
           "role_vocabulary": {"distinct": len(vocab), "counts": dict(vocab.most_common()),
                               "_as_printed_unsplit": True},
           "disagreements": {"birth_date_vs_statscrew": bd_dis, "coach_page_vs_player_page": intra,
                             "coaching_stores": cmp,
                             "coaching_stores_by_kind": {s: dict(c) for s, c in by_store.items()},
                             "role_string_pairs": [{"pfa": a, "store_role_title": b, "store": s, "n": k}
                                                   for (a, b, s), k in pairs.most_common()],
                             "_held_never_resolved": True},
           "counts": {"pages": len(codes), "resolved": len(people), "leads": len(leads),
                      "routes": dict(routes), **{k: v for k, v in n.items()},
                      "club_cell_flags": dict(flags), "claims": len(claims),
                      "store_stints": {s: {"stints": v["stints"], "unmapped_local_ids": v["unmapped_local_ids"]} for s, v in A.stores.items()}}}
    if write:
        fp = os.path.join(BASE, "build", "pfa-coaches.json")
        json.dump(out, open(fp, "w"), indent=1, ensure_ascii=False)
        print("wrote", fp)
    print(json.dumps({k: out["counts"][k] for k in out["counts"]}, indent=1, default=str))
    print(json.dumps(out["disagreements"]["coaching_stores_by_kind"], indent=1))
    print("listings", out["listings"]); print("officials shared", len(shared))
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
