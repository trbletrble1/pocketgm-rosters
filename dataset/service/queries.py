"""The read side. Every function takes an open read-only connection and returns
plain dicts. Nothing here chooses: a fact is every value held, each with the
claims that hold it; `contested` is a flag; a display name is a derived value
under the §9.3 recipe and says so.
"""
import os, sys, json, re, sqlite3, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, dates, families, classification

# WHAT A THING IS -- from declarations/classification.json, never from a name.
# See service/classification.py for why, and for the two files that keep their own
# `stats-` test because they ask a different question.
STAFF_PREDICATES = classification.staff_predicates()
NAME_PREDICATES = classification.name_predicates()
STATISTIC_STORES = classification.statistic_stores()


def _is_statistic(row):
    return row["store"] in STATISTIC_STORES


def _in_sql(col, values, negate=False):
    """(sql fragment, args) for `col IN (...)`. The values are DECLARED, so the
    list is long on purpose: a prefix is what broke this."""
    v = sorted(values)
    return f"{col} {'NOT ' if negate else ''}IN ({','.join('?' * len(v))})", v


DISPLAY_NAME_RECIPE = "display-name/design-9.3@v1"
DATE_RECIPE = dates.RECIPE
REAL_LEAGUE_CACHE = {}


class NotFound(Exception):
    def __init__(self, msg, **extra): super().__init__(msg); self.extra = extra


def connect():
    if not os.path.exists(paths.READ_MODEL): raise NotFound("no read model has been built yet", hint="python3 build_read_model.py")
    c = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())).strip()


def meta(conn):
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}


def snapshot_block(conn, changed=None, rebuild=None):
    m = meta(conn)
    gates = [{"name": r["name"], "status": r["status"], "counts": json.loads(r["counts"])} for r in conn.execute("SELECT * FROM gate ORDER BY name")]
    out = {"id": m.get("snapshot_id"), "built_at": m.get("built_at"), "claims": int(m.get("claims", 0)), "people": int(m.get("people", 0)),
           "stores": int(m.get("stores", 0)), "gates": m.get("gates_status"),
           "inputs_changed_since": changed if changed is not None else []}
    if m.get("forced") == "1":
        out["WARNING"] = "this read model was published with FAILED gates (--force); see /snapshot for which"
    if rebuild: out["rebuild"] = rebuild
    out["gate_detail"] = gates
    return out


# ---------------------------------------------------------------- claims -> facts
def claim_view(r):
    return {"claim": f"{r['store']}/{r['cid']}", "store": r["store"], "source_id": r["source_id"], "source_record": r["source_record"],
            "stated_by": r["stated_by"], "attribution": json.loads(r["attribution"] or "[]"), "kind": r["kind"],
            "observed_at": json.loads(r["observed_at"]) if r["observed_at"] else None, "note": r["note"],
            **({"extra": json.loads(r["extra"])} if r["extra"] else {})}


def facts_from_rows(rows, readings=None):
    """rows: claim rows of one subject. -> {family: fact}. A fact holds every value with its
    claims; date families add a derived same-day grouping; `contested` is a flag."""
    by_fam = collections.OrderedDict()
    for r in rows:
        by_fam.setdefault(r["family"], []).append(r)
    out = {}
    for fam, rs in by_fam.items():
        kind = families.kind_of(fam)
        positive = [r for r in rs if r["kind"] != "absent"]
        absent = [r for r in rs if r["kind"] == "absent"]
        groups = collections.OrderedDict()
        for r in positive:
            groups.setdefault((r["value"], r["predicate"]), []).append(r)
        values = [{"value": json.loads(v), "predicate": p, "claims": [claim_view(r) for r in g]} for (v, p), g in groups.items()]
        fact = {"family": fam, "predicates": sorted({r["predicate"] for r in rs}), "values": values, "literals": len({v for v, p in groups})}
        if kind == "date" and positive:
            items = []; seen = set()
            for (v, p), g in groups.items():
                # THE SOURCE DECIDES HOW A NUMERIC DATE READS. Ruled 2026-09-08:
                # a source that declared its numeric order, with the evidence, is read
                # in that order. build_read_model passes the source and this did not,
                # so 610 Crippen death dates read as a calendar day in the model and
                # came back through the service as unreadable -- the archive
                # disagreeing with itself about its own value, in the path a reader
                # actually sees. The plain reading is tried first, so a value that
                # already read is never reinterpreted; a declared format can only
                # RESCUE one the shared reading refuses.
                lit = json.loads(v)
                rd = dates.read(lit)
                if rd is None:
                    for _sid in {x["source_id"] for x in g if x["source_id"]}:
                        rd = dates.read(lit, _sid)
                        if rd is not None:
                            break
                if v not in seen: seen.add(v); items.append((None if lit is None else str(lit), rd))
                if rd: 
                    for val in values:
                        if val["value"] == lit and val["predicate"] == p: val["reading"] = dict(rd, derived=True, recipe=DATE_RECIPE)
            grp = dates.same_day_groups(items)
            unread = sorted({lit for lit, rd in items if rd is None and lit is not None})
            fact["same_day"] = {"groups": grp, "unreadable": unread, "derived": True, "recipe": DATE_RECIPE}
            fact["contested"] = (len(grp) + len(unread)) > 1
        else:
            fact["contested"] = len({v for v, p in groups}) > 1
        if absent: fact["absent_in"] = [claim_view(r) for r in absent]
        if not positive: fact["basis"] = "absent" if absent else "unknown"
        out[fam] = fact
    return out


def display_name(name_rows, hints=None):
    """§9.3: the name claim covering the largest span of the person's own attested career,
    tie-broken earliest. Undated name claims (a modern reference's 'fetch-2026') do not
    count toward a span; if no name claim is dated, the most-attested string. DERIVED."""
    # A FORENAME-FIRST FORM WINS WHERE THE PERSON HOLDS ONE. Ruled 2026-09-09 by Ryan:
    # `Fritz Pollard`, not `Pollard, Frederick Douglass`. A display name is READ, and
    # surname-first is a filing convention, not a name. This filters the CANDIDATES and
    # changes nothing else: the §9.3 span rule below runs exactly as before on what is
    # left, both forms stay in the store as printed, and both stay searchable. A man who
    # holds ONLY a surname-first form keeps it -- 12 people in the archive.
    rows = list(name_rows)
    filed = [r for r in rows if classification.is_surname_first(r["name"])]
    read_as_written = [r for r in rows if not classification.is_surname_first(r["name"])]
    dropped_filing_forms = sorted({r["name"] for r in filed}) if (filed and read_as_written) else []
    if dropped_filing_forms: rows = read_as_written
    spans = collections.defaultdict(set); count = collections.Counter(); claims = collections.defaultdict(list)
    for r in rows:
        count[r["name"]] += 1; claims[r["name"]].append(r["claim"])
        if r["year"]: spans[r["name"]].add(r["year"])
    if not count:
        return {"value": None, "basis": "unknown", "derived": True, "recipe": DISPLAY_NAME_RECIPE,
                "why": "no source holds a name claim for this person; a person has no name except as a claim",
                **({"source_records_that_denote_him": hints} if hints else {})}
    if spans:
        best = max(spans, key=lambda n: (max(spans[n]) - min(spans[n]) + 1, -min(spans[n]), count[n]))
        why = f"largest career span ({min(spans[best])}-{max(spans[best])}), ties to the earliest"
    else:
        best = count.most_common(1)[0][0]; why = "no dated name claim; the most-attested string"
    out = {"value": best, "basis": "derived", "derived": True, "recipe": DISPLAY_NAME_RECIPE, "why": why,
           "inputs": [f"{c}" for c in claims[best]][:20]}
    if dropped_filing_forms:
        out["surname_first_forms_not_chosen"] = dropped_filing_forms
        out["why"] += "; surname-first forms were set aside as a filing convention (they remain claims and remain searchable)"
    return out


# ---------------------------------------------------------------- person
def person(conn, pid, one=False):
    p = conn.execute("SELECT * FROM person WHERE id=?", (pid,)).fetchone()
    if not p: raise NotFound(f"no such person {pid}")
    rows = conn.execute("SELECT * FROM claim INDEXED BY claim_person WHERE person=? ORDER BY scope, league, year, club_str, family, predicate, store, id", (pid,)).fetchall()
    names = conn.execute("SELECT n.*, c.store||'/'||c.cid AS claim FROM person_name n JOIN claim c ON c.id=n.claim WHERE n.person=? ORDER BY n.year, n.name", (pid,)).fetchall()
    hints = [r[0] for r in conn.execute("SELECT DISTINCT source_record FROM denotation WHERE person=? LIMIT 8", (pid,))]
    out = {"person": pid, "display_name": display_name(names, hints), "index_name": p["index_name"],
           "identity": {"in_identity": bool(p["in_identity"]), "slugs": json.loads(p["slugs"]), "locals": json.loads(p["locals"]), "evidence": p["evidence"], "in_index": bool(p["in_index"])},
           "roles_from_claims": json.loads(p["roles"]), "first_year": p["first_year"], "last_year": p["last_year"], "n_claims": p["n_claims"]}
    if p["merged_into"]: out["merged_into"] = {"person": p["merged_into"], "merge_id": p["merge_id"], "note": "nothing deleted; this record stands and the survivor carries merged_from"}
    if p["merged_from"]: out["merged_from"] = json.loads(p["merged_from"])
    nm = collections.OrderedDict()
    for n in names: nm.setdefault(n["name"], {"value": n["name"], "predicate": n["predicate"], "years": set(), "claims": []})
    for n in names:
        nm[n["name"]]["claims"].append(n["claim"]); 
        if n["year"]: nm[n["name"]]["years"].add(n["year"])
    out["names"] = [dict(v, years=sorted(v["years"])) for v in nm.values()]
    by_scope = collections.defaultdict(list)
    for r in rows: by_scope[r["scope"]].append(r)
    out["facts"] = facts_from_rows([r for r in by_scope["person"] if r["predicate"] not in NAME_PREDICATES])
    ps = collections.OrderedDict()
    for r in by_scope["person_season"]: ps.setdefault((r["league"], r["year"]), []).append(r)
    out["seasons"] = [{"league": lg, "year": y, "facts": facts_from_rows(rs)} for (lg, y), rs in ps.items()]
    st = collections.OrderedDict()
    for r in by_scope["stint"]: st.setdefault((r["year"], r["league"], r["club_str"]), []).append(r)
    stints = []
    for (y, lg, club), rs in st.items():
        stats = [r for r in rs if _is_statistic(r)]
        other = [r for r in rs if not _is_statistic(r)]
        cid = next((r["club_id"] for r in rs if r["club_id"]), None); via = next((r["club_via"] for r in rs if r["club_via"]), None)
        s = {"year": y, "league": lg, "club": {"as_written": club, "club_id": cid, "resolved_via": via, "name_that_year": club_name_for(conn, cid, y) if cid else None},
             "facts": facts_from_rows(other), "games": four_state(other)}
        if stats: s["statistics"] = facts_from_rows(stats)
        stints.append(s)
    out["stints"] = stints
    others = [r for r in rows if r["scope"] not in ("person", "person_season", "stint")]
    if others: out["other_subjects"] = [{"subject": json.loads(r["subject"]), "family": r["family"], "value": json.loads(r["value"]), **claim_view(r)} for r in others]
    out["denotations"] = [dict(r) for r in conn.execute("SELECT store, did, source_record, local, discriminator, method, matched_against, status, note FROM denotation WHERE person=? ORDER BY store, did", (pid,))]
    for d in out["denotations"]: d["discriminator"] = json.loads(d["discriminator"] or "null")
    out["contested"] = [{"family": r["family"], "groups": json.loads(r["groups"])} for r in conn.execute("SELECT family, groups FROM contested WHERE person=?", (pid,))]
    if one:
        if out["contested"]:
            return 409, {"error": "one value was asked for and this person holds more than one on " + ", ".join(c["family"] for c in out["contested"]),
                         "person": pid, "candidates": {c["family"]: out["facts"].get(c["family"], {}).get("values") for c in out["contested"]},
                         "note": "the archive holds both; it does not choose"}
        out["facts"] = {f: (v["values"][0] if v["values"] else v) for f, v in out["facts"].items()}
    return 200, out


def four_state(rows):
    """§9.6: the four states of a games count on a stint, all reachable."""
    g = [r for r in rows if r["predicate"] == "games_played"]
    obs = [r for r in g if r["kind"] != "absent"]; ab = [r for r in g if r["kind"] == "absent"]
    if obs:
        vals = {r["value"] for r in obs}
        if len(vals) > 1: return {"basis": "contested", "values": [{"value": json.loads(v), "claims": [claim_view(r) for r in obs if r["value"] == v]} for v in vals]}
        return {"basis": "observed", "value": json.loads(obs[0]["value"]), "claims": [claim_view(r) for r in obs]}
    if ab: return {"basis": "absent", "why": "a source with a games column lists him and the cell is blank", "claims": [claim_view(r) for r in ab]}
    return {"basis": "unknown", "why": "no source that counts games has been read against this stint"}


def club_name_for(conn, cid, year):
    r = conn.execute("SELECT name FROM club_name WHERE club_id=? AND kind='official' AND first<=? AND last>=? LIMIT 1", (cid, year, year)).fetchone()
    return r["name"] if r else None


# ---------------------------------------------------------------- search
def search(conn, q, year=None, mode="tokens", limit=50):
    qn = norm(q)
    if not qn: raise NotFound("empty query")
    limit = max(1, min(int(limit or 50), 500))
    if mode == "exact":
        hits = conn.execute("SELECT DISTINCT person FROM person_name WHERE norm=?", (qn,)).fetchall()
    elif mode == "prefix":
        hits = conn.execute("SELECT DISTINCT person FROM person_name WHERE norm LIKE ? LIMIT 5000", (qn + "%",)).fetchall()
    else:
        toks = [t for t in qn.split() if t]
        match = " ".join(f'"{t}"' for t in toks)
        hits = conn.execute("SELECT DISTINCT person FROM person_name_fts WHERE person_name_fts MATCH ? LIMIT 5000", (match,)).fetchall()
    ids = [h["person"] for h in hits]
    exact = {h["person"] for h in conn.execute("SELECT DISTINCT person FROM person_name WHERE norm=?", (qn,))} if ids else set()
    cands = []
    for pid in ids:
        p = conn.execute("SELECT * FROM person WHERE id=?", (pid,)).fetchone()
        if not p: continue
        if year is not None:
            y = int(year)
            if p["first_year"] is None or not (p["first_year"] <= y <= p["last_year"]): continue
        cands.append(candidate(conn, p, exact=pid in exact))
    cands.sort(key=lambda c: (not c["exact_match"], c["first_year"] or 9999, c["person"]))
    return {"query": q, "query_norm": qn, "mode": mode, "year": year, "n": len(cands), "truncated": len(cands) > limit,
            "note": "candidates, not an answer: a name is a claim and a single result is an outcome, not a promise",
            "candidates": cands[:limit]}


def candidate(conn, p, exact=False):
    pid = p["id"]
    names = [r["name"] for r in conn.execute("SELECT DISTINCT name FROM person_name WHERE person=? ORDER BY name", (pid,))]
    bd = [{"value": json.loads(r["value"]), "predicate": r["predicate"], "source_id": r["source_id"]} for r in conn.execute(
        "SELECT DISTINCT value, predicate, source_id FROM claim INDEXED BY claim_person WHERE person=? AND family='birth_date' AND kind!='absent'", (pid,))]
    col = sorted({json.loads(r["value"]) for r in conn.execute("SELECT DISTINCT value FROM claim INDEXED BY claim_person WHERE person=? AND predicate IN ('college','pfa.college') AND kind!='absent'", (pid,)) if isinstance(json.loads(r["value"]), str)})
    nostat, nsargs = _in_sql("store", STATISTIC_STORES, negate=True)
    clubs = [f"{r['league']}|{r['year']}|{r['club_str']}" for r in conn.execute(
        f"SELECT DISTINCT league, year, club_str FROM claim INDEXED BY claim_person WHERE person=? AND scope='stint' AND {nostat} ORDER BY year LIMIT 40", [pid] + nsargs)]
    contested = [r["family"] for r in conn.execute("SELECT family FROM contested WHERE person=?", (pid,))]
    return {"person": pid, "exact_match": exact, "index_name": p["index_name"], "names_held": names, "birth_dates_held": bd, "colleges_held": col,
            "first_year": p["first_year"], "last_year": p["last_year"], "roles_from_claims": json.loads(p["roles"]), "club_seasons": clubs,
            "contested": contested, **({"merged_into": p["merged_into"]} if p["merged_into"] else {})}


# ---------------------------------------------------------------- clubs
_CLUBS = {}
def archive_clubs():
    """The archive's own resolver, loaded once per file version."""
    st = os.stat(paths.CLUBS); k = (st.st_mtime_ns, st.st_size)
    if _CLUBS.get("k") != k:
        sys.path.insert(0, os.path.join(paths.DATASET, "src")); import clubs as ac
        _CLUBS["k"] = k; _CLUBS["C"] = ac.Clubs()
    return _CLUBS["C"]


def resolve_club(conn, club, year, league=None):
    y = int(year)
    r = conn.execute("SELECT id FROM club WHERE id=?", (club,)).fetchone()
    if r: return club, "club_id"
    r = conn.execute("SELECT club_id FROM club_code WHERE code=? AND first<=? AND last>=?", (club, y, y)).fetchone()
    if r: return r["club_id"], "code"
    res = archive_clubs().resolve(club, y, league if league and league != "COACHES" else None, source="service")
    if res: return res
    return None, None


def club_season(conn, league, year, club):
    y = int(year); league = league.upper()
    cid, via = resolve_club(conn, club, y, league)
    if not cid:
        near = [dict(r) for r in conn.execute("SELECT DISTINCT name, club_id, first, last FROM club_name WHERE norm LIKE ? ORDER BY first LIMIT 12", ("%" + norm(club).replace(" ", "%") + "%",))]
        raise NotFound(f"the club table holds no club for {club!r} in {y}", nearest_names=near, note="404 means the table does not hold it; an empty roster on a held club-season is a 200")
    exists = conn.execute("SELECT 1 FROM club_code WHERE club_id=? AND first<=? AND last>=?", (cid, y, y)).fetchone() is not None
    rows = conn.execute("SELECT * FROM claim WHERE scope='stint' AND club_id=? AND year=? ORDER BY person, family, store, id", (cid, y)).fetchall()
    by_person = collections.OrderedDict()
    for r in rows: by_person.setdefault(r["person"] or f"unresolved:{r['store']}/{r['s1']}", []).append(r)
    roster, staff, other = [], [], []
    for pid, rs in by_person.items():
        leagues = {r["league"] for r in rs}
        p = conn.execute("SELECT index_name FROM person WHERE id=?", (pid,)).fetchone()
        if pid.startswith("unresolved:"):
            st, local = pid[len("unresolved:"):].split("/", 1)
            own = [{"value": json.loads(r["value"]), **claim_view(r)} for r in conn.execute("SELECT * FROM claim WHERE store=? AND s1=? AND predicate='name'", (st, local))]
            entry = {"person": None, "unresolved": {"store": st, "local_id": local, "why": "identity.json does not hold this local id (gate G2 lists the store)"},
                     "name_as_written": own, "display_name": {"value": own[0]["value"] if own else None, "basis": "unresolved", "derived": True, "why": "the store's own name claim for an id no identity resolves"},
                     "index_name": None, "club_as_written": sorted({r["club_str"] for r in rs}), "leagues_as_written": sorted(leagues)}
        else:
            nm = conn.execute("SELECT n.*, c.store||'/'||c.cid AS claim FROM person_name n JOIN claim c ON c.id=n.claim WHERE n.person=?", (pid,)).fetchall()
            hints = [] if nm else [r[0] for r in conn.execute("SELECT DISTINCT source_record FROM denotation WHERE person=? LIMIT 8", (pid,))]
            entry = {"person": pid, "display_name": display_name(nm, hints), "index_name": p["index_name"] if p else None,
                     "club_as_written": sorted({r["club_str"] for r in rs}), "leagues_as_written": sorted(leagues)}
        # STAFF IS DECIDED BY THE PREDICATE, NOT BY THE LEAGUE. This used to read
        # `leagues & {"COACHES","ASSISTANTS","COACH"}`, which worked only while the
        # coaching claims carried no real league. On 2026-09-09 they were given one --
        # `NFL-1979` -- and every one of them started matching the REQUESTED league, so
        # 26,105 of 31,986 coaching pairs sorted onto the roster: Jack Pardee became a
        # player on the 1979 Redskins and the 2024 Bears returned no staff at all.
        # A pfa.coaching_season claim is a coaching season whatever league it names.
        staff_rows = [r for r in rs if r["predicate"] in STAFF_PREDICATES]
        main = [r for r in rs if r["league"] == league and r["predicate"] not in STAFF_PREDICATES]
        rest = [r for r in rs if r["league"] != league]
        placed = False
        if staff_rows:
            e = dict(entry); e["facts"] = facts_from_rows(staff_rows)
            e["_role"] = "staff: this club-season holds a coaching or staff claim for him"
            staff.append(e); placed = True
        if main:
            e = dict(entry)
            e["facts"] = facts_from_rows([r for r in main if not _is_statistic(r)])
            e["games"] = four_state(main)
            stats = [r for r in main if _is_statistic(r)]
            if stats: e["statistics"] = facts_from_rows(stats)
            # A PLAYER-COACH IS BOTH, AND IS LISTED TWICE ON PURPOSE. 782 (person,
            # club-season) pairs hold a playing claim and a staff claim -- Glenn Dobbs at
            # Saskatchewan, Bill Daddio at Buffalo. Choosing one list for them would
            # delete a fact the archive holds; n_members and n_staff each count him once.
            if placed: e["_also_staff_this_season"] = True
            roster.append(e); placed = True
        if not placed:
            # THE LAST LEAGUE-STRING TEST IN THIS FUNCTION, REMOVED 2026-09-09. It read
            # `staff if leagues & {"COACHES","ASSISTANTS","COACH"} else other`. Reaching
            # here means the man holds NO staff predicate on this club-season, so the
            # branch could only ever have sorted a coaching-keyed claim that carries no
            # coaching predicate. Measured: 0 (person, club-season) pairs in the archive.
            # It was dead, and a dead string test is one that comes back to life quietly.
            entry["facts"] = facts_from_rows(rest or rs)
            other.append(entry)
    names = [{"value": json.loads(r["value"]), **claim_view(r)} for r in conn.execute(
        "SELECT * FROM claim WHERE scope='club_season' AND predicate='club_name' AND subject LIKE ? ", (f'%"{y}"%',)) if json.loads(r["subject"])[-1] in {club} | {r2["code"] for r2 in conn.execute("SELECT code FROM club_code WHERE club_id=?", (cid,))}]
    out = {"league": league, "year": y, "club": {"requested": club, "club_id": cid, "resolved_via": via, "name_that_year": club_name_for(conn, cid, y),
                                                  "code_that_year": (archive_clubs().code_for(cid, y) if cid in archive_clubs().by_id else None)},
           "names_that_season": names, "members": roster, "staff": staff, "n_members": len(roster), "n_staff": len(staff)}
    if other: out["other_leagues_at_this_club_that_year"] = other
    if not roster:
        out["basis"] = "unknown"
        out["why"] = ("the club table holds this club that year; no roster store places anyone on it" if exists
                      else "the club table holds this club, but not for this year; nothing places anyone on it")
    return out


def club(conn, cid):
    r = conn.execute("SELECT json FROM club WHERE id=?", (cid,)).fetchone()
    if not r: raise NotFound(f"no such club {cid}")
    c = json.loads(r["json"])
    unresolved = [{"section": u["section"], "item": json.loads(u["json"])} for u in conn.execute("SELECT section, json, mentions FROM club_unresolved") if cid in json.loads(u["mentions"])
                  or any(f"code:{s['code']}" in json.loads(u["mentions"]) for s in c["segments"])]
    # MEMBERS ARE DECIDED BY THE PREDICATE, NOT BY THE LEAGUE -- the same fix
    # club_season() took on 2026-09-09, which did not reach this line. It read
    # `league NOT IN ('COACHES','ASSISTANTS','SALARIES','COACH')`, and once the
    # coaching claims carried real leagues it counted 22 coaches among the 2024
    # Bears' 83 "members". Staff are counted separately and the two are not added.
    nostaff, sargs = _in_sql("predicate", STAFF_PREDICATES, negate=True)
    isstaff, sargs2 = _in_sql("predicate", STAFF_PREDICATES)
    mem = dict(conn.execute(f"SELECT year, COUNT(DISTINCT person) FROM claim WHERE scope='stint' AND club_id=? AND {nostaff} GROUP BY year", [cid] + sargs))
    stf = dict(conn.execute(f"SELECT year, COUNT(DISTINCT person) FROM claim WHERE scope='stint' AND club_id=? AND {isstaff} GROUP BY year", [cid] + sargs2))
    seasons = [{"year": y, "n": mem.get(y, 0), "n_staff": stf.get(y, 0)} for y in sorted(set(mem) | set(stf))]
    return {"club": c, "seasons_held_with_members": seasons, "unresolved_touching_this_club": unresolved,
            "note": "lineage links are the table's, with their evidence; candidates and splits are listed, not joined"}


def clubs_search(conn, name, year=None):
    q = "%" + norm(name).replace(" ", "%") + "%"
    rows = conn.execute("SELECT DISTINCT club_id, name, first, last, kind FROM club_name WHERE norm LIKE ? ORDER BY first, name", (q,)).fetchall()
    if year is not None:
        y = int(year); rows = [r for r in rows if r["first"] <= y <= r["last"]]
    return {"query": name, "year": year, "n": len(rows), "candidates": [dict(r) for r in rows[:200]]}


# ---------------------------------------------------------------- census
def parse_population(spec):
    spec = (spec or "people").strip()
    if not spec.startswith("people"): raise NotFound(f"unknown population {spec!r}; use people[:league=NFL][,year=1950]")
    filt = {}
    if ":" in spec:
        for part in spec.split(":", 1)[1].split(","):
            if "=" not in part: raise NotFound(f"bad population filter {part!r}")
            k, v = part.split("=", 1); filt[k.strip()] = v.strip()
    return filt


def population_sql(filt):
    """-> (sql producing one column `person`, args). The population is established from the
    stint claims ONCE, never per person, so the planner cannot walk a family index per row."""
    if "league" in filt and "year" in filt:
        return "SELECT DISTINCT person FROM stint_person WHERE league=? AND year=?", [filt["league"].upper(), int(filt["year"])]
    if "league" in filt:
        return "SELECT DISTINCT person FROM stint_person WHERE league=?", [filt["league"].upper()]
    if "year" in filt:
        return "SELECT DISTINCT person FROM stint_person WHERE year=?", [int(filt["year"])]
    return "SELECT id AS person FROM person", []


def census(conn, family, population="people"):
    filt = parse_population(population)
    preds = [r[0] for r in conn.execute("SELECT DISTINCT predicate FROM claim WHERE family=?", (family,))]
    if not preds: raise NotFound(f"no claim carries family {family!r}", families=sorted(families.get()["families"]))
    psql, pargs = population_sql(filt)
    row = conn.execute(f"""WITH pop AS ({psql}),
        f AS (SELECT person, pos, ab FROM person_family WHERE family=?),
        k AS (SELECT person FROM contested WHERE family=?)
        SELECT COUNT(*), SUM(COALESCE(f.pos,0)>0), SUM(COALESCE(f.pos,0)=0 AND COALESCE(f.ab,0)>0), SUM(k.person IS NOT NULL)
        FROM pop LEFT JOIN f ON f.person=pop.person LEFT JOIN k ON k.person=pop.person""", pargs + [family, family]).fetchone()
    n, pos, ab_only, cont = [int(x or 0) for x in row]
    return {"family": family, "predicates": preds, "population": {"spec": population, "definition": "every person in the read model" + (f" with a stint matching {filt}" if filt else ""), "n": n},
            "basis": {"observed": pos - cont, "contested": cont, "absent": ab_only, "unknown": n - pos - ab_only},
            "note": "observed = at least one value and no disagreement; contested = more than one value (same-day grouping for dates); absent = only absence claims; unknown = nothing claimed. They sum to n."}


def census_club_seasons(conn, year):
    """§ Every number here reads a PREDICATE and a DECLARED STORE, never a league
    string or a store-name prefix. Both were wrong on 2026-09-09: the league test
    let 41,662 of 54,908 staff claims through as players (answer 1 too high) while
    answer 3 counted only the claims still carrying a COACHES season key (too low),
    so the two answers overlapped in a census whose note says they are not added."""
    y = int(year)
    nostat, na = _in_sql("store", STATISTIC_STORES, negate=True)
    nostaff, sa = _in_sql("predicate", STAFF_PREDICATES, negate=True)
    isstaff, sb = _in_sql("predicate", STAFF_PREDICATES)
    roster_where = f"scope='stint' AND year=? AND {nostat} AND {nostaff}"
    ra = [y] + na + sa
    real = [r[0] for r in conn.execute(f"SELECT DISTINCT league FROM claim WHERE {roster_where}", ra)]
    roster = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT league, club_str FROM claim WHERE {roster_where})", ra).fetchone()[0]
    roster_ids = conn.execute(f"SELECT COUNT(DISTINCT club_id) FROM claim WHERE {roster_where} AND club_id IS NOT NULL", ra).fetchone()[0]
    coaching = conn.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT club_str FROM claim WHERE scope='stint' AND year=? AND {isstaff})", [y] + sb).fetchone()[0]
    coaching_ids = conn.execute(f"SELECT COUNT(DISTINCT club_id) FROM claim WHERE scope='stint' AND year=? AND club_id IS NOT NULL AND {isstaff}", [y] + sb).fetchone()[0]
    table = conn.execute("SELECT COUNT(DISTINCT club_id) FROM club_code WHERE first<=? AND last>=?", (y, y)).fetchone()[0]
    by_league = [{"league": r[0], "club_seasons": r[1]} for r in conn.execute(f"SELECT league, COUNT(DISTINCT club_str) FROM claim WHERE {roster_where} GROUP BY league", ra)]
    return {"year": y, "answers": [
        {"definition": "club strings that roster stores place at least one player on", "n": roster, "by_league": by_league},
        {"definition": "of those, distinct clubs after resolving through the club table", "n": roster_ids},
        {"definition": "club strings a coaching or staff claim places a man on", "n": coaching,
         "distinct_clubs_after_resolving": coaching_ids,
         "_definition_changed_2026_09_09": "was 'club strings the coaching stores place a coach on (COACHES/ASSISTANTS keys)'. That named the MECHANISM -- the season-key prefix -- and once the coaching subjects carried real leagues it answered a question nobody asks: how many coaching claims still happen to be keyed COACHES. The question is how many club-seasons the archive holds a coaching claim for."},
        {"definition": "clubs the club table holds a code-segment for in that year", "n": table}],
        "note": "three or four honest numbers; they are not added"}


# ---------------------------------------------------------------- sources
def sources(conn):
    rows = conn.execute("""SELECT c.source_id, s.declared_in, SUM(n) AS claims, COUNT(DISTINCT c.store) AS stores, SUM(records) AS records_by_store_and_predicate
                           FROM source_summary c LEFT JOIN source s ON s.source_id=c.source_id GROUP BY c.source_id ORDER BY claims DESC""").fetchall()
    return {"n": len(rows), "sources": [dict(r) for r in rows]}


def source(conn, sid):
    s = conn.execute("SELECT * FROM source WHERE source_id=?", (sid,)).fetchone()
    stores = [dict(r) for r in conn.execute("SELECT store, SUM(n) AS claims, SUM(records) AS records_by_predicate FROM source_summary WHERE source_id=? GROUP BY store ORDER BY claims DESC", (sid,))]
    if not s and not stores: raise NotFound(f"no such source {sid}")
    preds = [dict(r) for r in conn.execute("SELECT predicate, SUM(n) AS n FROM source_summary WHERE source_id=? GROUP BY predicate ORDER BY n DESC", (sid,))]
    return {"source_id": sid, "declared_in": s["declared_in"] if s else None, "declaration": json.loads(s["declaration"]) if s else None,
            "stores": stores, "predicates": preds, **({} if s else {"WARNING": "this source_id has no declaration; its acquisition and lineage are not recorded"})}


def source_record(conn, sid, locator):
    sr = f"{sid}#{locator}"
    rows = conn.execute("SELECT * FROM claim WHERE source_record=? ORDER BY store, id", (sr,)).fetchall()
    dens = [dict(r) for r in conn.execute("SELECT store, did, person, local, discriminator, method, matched_against, status, note FROM denotation WHERE source_record=?", (sr,))]
    table = [dict(r) for r in conn.execute("SELECT store, source_id, locator FROM source_record WHERE sr=?", (sr,))]
    if not rows and not dens and not table: raise NotFound(f"no such source record {sr}")
    return {"source_record": sr, "registered_in": table, "claims": [{"subject": json.loads(r["subject"]), "person": r["person"], "predicate": r["predicate"], "family": r["family"], "value": json.loads(r["value"]), **claim_view(r)} for r in rows],
            "denotations": [dict(d, discriminator=json.loads(d["discriminator"] or "null")) for d in dens]}


# ---------------------------------------------------------------- contested
def contested(conn, family=None, league=None, year=None, limit=100, offset=0):
    where = []; args = []
    if family: where.append("k.family=?"); args.append(family)
    if league or year:
        psql, pargs = population_sql({k: v for k, v in (("league", league), ("year", year)) if v})
        where.append(f"k.person IN ({psql})"); args += pargs
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM contested k{wsql}", args).fetchone()[0]
    by_fam = [dict(r) for r in conn.execute(f"SELECT k.family, COUNT(*) AS n FROM contested k{wsql} GROUP BY k.family ORDER BY n DESC", args)]
    limit = max(1, min(int(limit or 100), 1000)); offset = max(0, int(offset or 0))
    rows = conn.execute(f"SELECT k.*, p.index_name FROM contested k JOIN person p ON p.id=k.person{wsql} ORDER BY k.person, k.family LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
    items = []
    for r in rows:
        cl = conn.execute("SELECT * FROM claim INDEXED BY claim_person WHERE person=? AND family=? AND kind!='absent' ORDER BY store, id", (r["person"], r["family"])).fetchall()
        items.append({"person": r["person"], "index_name": r["index_name"], "family": r["family"], "n_groups": r["n_groups"], "groups": json.loads(r["groups"]),
                      "values": [{"value": json.loads(c["value"]), "predicate": c["predicate"], **claim_view(c)} for c in cl]})
    return {"total": total, "by_family": by_fam, "limit": limit, "offset": offset, "items": items,
            "note": "each is a man the sources disagree about; the archive holds every value and this list is the worklist"}
