"""Build the read model: every claim in dataset/build/, indexed by global person,
club-season, predicate family and source record, in one SQLite file.

READ-ONLY over the archive. Writes one file, outside the repo (paths.READ_MODEL),
and writes it the way index_io.py writes the index: to a sibling temp file, then
os.replace. A reader sees the old model or the new one, never a partial.

Nothing is dropped in silence. A claim whose person does not resolve is kept with
person NULL and counted by store (gate G2); a claim whose source record is not in
its store's table is kept and counted (gate G3); a date string that cannot be read
is kept and counted (gate G1); the people here are reconciled against the index
(gate G4). A failing gate REFUSES to publish -- the previous model keeps serving.

    python3 build_read_model.py            # build, gate, publish
    python3 build_read_model.py --force    # publish even if a gate fails (development only; the snapshot says so loudly)
"""
import os, sys, json, glob, sqlite3, time, collections, re, datetime, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, families, identity, snapshot, dates, gates


def archive_clubs():
    """The archive's own club-table accessor, imported WHEN A BUILD RUNS, not at import time.

    It used to be a module-level import, which meant gates.py and gate_selftest.py -- which
    only want the SCHEMA constant from this file -- could not run on a machine that did not
    have the whole archive checked out. A self-test that needs the archive present is a worse
    self-test, so the dependency is now where it is actually used."""
    sys.path.insert(0, os.path.join(paths.DATASET, "src"))
    import clubs
    return clubs

PERSON_SCOPES = ("person", "person_season", "stint", "contract", "transfer")
REAL_LEAGUES = None   # filled from the club table: leagues that appear in any segment

SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE input(path TEXT PRIMARY KEY, mtime_ns INTEGER, size INTEGER);
CREATE TABLE store(name TEXT PRIMARY KEY, shape TEXT, claims INTEGER, has_table INTEGER, inline_source TEXT, league TEXT);
CREATE TABLE source(source_id TEXT PRIMARY KEY, declared_in TEXT, declaration TEXT);
CREATE TABLE source_record(store TEXT, sr TEXT, source_id TEXT, locator TEXT, PRIMARY KEY(store, sr));
CREATE TABLE claim(
  id INTEGER PRIMARY KEY, store TEXT, cid TEXT, scope TEXT, subject TEXT, s1 TEXT, person TEXT,
  league TEXT, year INTEGER, club_str TEXT, club_id TEXT, club_via TEXT,
  predicate TEXT, family TEXT, value TEXT, value_text TEXT,
  source_id TEXT, source_record TEXT, sr_in_table INTEGER, stated_by TEXT, attribution TEXT,
  kind TEXT, observed_at TEXT, observed_year INTEGER, note TEXT, extra TEXT);
CREATE TABLE date_reading(claim INTEGER PRIMARY KEY, family TEXT, literal TEXT, y INTEGER, m INTEGER, d INTEGER,
  precision TEXT, approximate INTEGER, trailing TEXT, readable INTEGER);
CREATE TABLE person(id TEXT PRIMARY KEY, in_identity INTEGER, slugs TEXT, locals TEXT, evidence TEXT,
  merged_into TEXT, merge_id TEXT, merged_from TEXT, in_index INTEGER, index_name TEXT,
  n_claims INTEGER, first_year INTEGER, last_year INTEGER, roles TEXT);
CREATE TABLE person_name(person TEXT, name TEXT, norm TEXT, predicate TEXT, store TEXT, claim INTEGER, year INTEGER);
CREATE VIRTUAL TABLE person_name_fts USING fts5(norm, person UNINDEXED, name UNINDEXED, tokenize='unicode61');
CREATE TABLE denotation(store TEXT, did TEXT, source_record TEXT, person TEXT, local TEXT, discriminator TEXT,
  method TEXT, matched_against TEXT, status TEXT, note TEXT);
CREATE TABLE club(id TEXT PRIMARY KEY, json TEXT, first INTEGER, last INTEGER, origin TEXT, lineage_kind TEXT);
CREATE TABLE club_code(code TEXT, first INTEGER, last INTEGER, club_id TEXT);
CREATE TABLE club_name(norm TEXT, name TEXT, first INTEGER, last INTEGER, club_id TEXT, kind TEXT);
CREATE TABLE club_unresolved(section TEXT, json TEXT, mentions TEXT);
CREATE TABLE club_refusal(string TEXT, year INTEGER, league TEXT, why TEXT, n INTEGER);
CREATE TABLE contested(person TEXT, family TEXT, n_groups INTEGER, groups TEXT, literals TEXT, PRIMARY KEY(person, family));
CREATE TABLE gate(name TEXT PRIMARY KEY, status TEXT, counts TEXT, report TEXT);
CREATE TABLE source_summary(source_id TEXT, store TEXT, predicate TEXT, n INTEGER, records INTEGER);
CREATE TABLE person_family(person TEXT, family TEXT, pos INTEGER, ab INTEGER, PRIMARY KEY(person, family));
CREATE TABLE stint_person(person TEXT, league TEXT, year INTEGER, PRIMARY KEY(league, year, person));
"""

INDEXES = """
CREATE INDEX claim_person ON claim(person);
CREATE INDEX claim_club_year ON claim(club_id, year) WHERE scope='stint';
CREATE INDEX claim_league_year ON claim(league, year) WHERE scope='stint';
CREATE INDEX claim_year ON claim(year) WHERE scope='stint';
CREATE INDEX source_summary_sid ON source_summary(source_id);
CREATE INDEX person_family_family ON person_family(family);
CREATE INDEX claim_family ON claim(family);
CREATE INDEX claim_predicate ON claim(predicate);
CREATE INDEX claim_sr ON claim(source_record);
CREATE INDEX claim_source ON claim(source_id);
CREATE INDEX claim_store_cid ON claim(store, cid);
CREATE INDEX claim_subject ON claim(subject) WHERE scope NOT IN ('person','person_season','stint');
CREATE INDEX person_name_norm ON person_name(norm);
CREATE INDEX person_name_person ON person_name(person);
CREATE INDEX denotation_person ON denotation(person);
CREATE INDEX denotation_sr ON denotation(source_record);
CREATE INDEX date_reading_family ON date_reading(family, readable);
CREATE INDEX club_code_code ON club_code(code);
CREATE INDEX club_name_norm ON club_name(norm);
CREATE INDEX contested_family ON contested(family);
"""


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def norm_name(s):
    """Accent-folded, lower, alphanumeric words. The same fold queries.norm applies; CLAUDE.md: fold, never strip."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ",
        unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower())).strip()


_LEAGUE_TOKENS = None
def is_claim_store(d):
    """THE reader's test for whether a build file is a claim store: a JSON object with a
    top-level `claims` list. Nothing else is read, and until 2026-09-07 nothing else was
    counted either.

    It lives here, alone, because gates.py's RS-G5 needs the same test and a second copy
    would drift -- silently on both sides, which is the whole defect that gate exists for.
    RS-G5 imports this function AND probes it with specimens on every run, so a predicate
    that quietly widens or narrows fails a gate instead of changing what the archive holds
    without anyone saying so."""
    return isinstance(d, dict) and isinstance(d.get("claims"), list)


def store_league(st):
    """A stint's league comes from the store filename (stats-nfl-1987 -> NFL) unless the
    archive's rebuild declaration says the store's name is not its league
    (store_league_tokens: assistants -> COACHES, ruled 2026-09-07). Read, not mirrored."""
    global _LEAGUE_TOKENS
    if _LEAGUE_TOKENS is None:
        d = json.load(open(paths.INDEX_REBUILD_DECL)) if os.path.exists(paths.INDEX_REBUILD_DECL) else {}
        _LEAGUE_TOKENS = {k: v.split(" ")[0] for k, v in (d.get("store_league_tokens") or {}).items() if not k.startswith("_")}
    base = st[6:] if st.startswith("stats-") else st
    return _LEAGUE_TOKENS.get(base) or base.split("-")[0].upper()


def season_year(s):
    m = re.search(r"(\d{4})", str(s))
    return int(m.group(1)) if m else None


def observed_year(o):
    """An observation year where the observed_at names one: an int, 'NFL-1950', 'guide-1969'.
    'fetch-2026', 'fetched-2026-09', 'held-2026' name when WE got it, not when the source
    observed, and return None."""
    if isinstance(o, int): return o
    if not isinstance(o, str): return None
    if re.match(r"^(fetch|fetched|held|guides|case:)", o): return None
    m = re.search(r"(\d{4})", o)
    return int(m.group(1)) if m else None


def load_sources():
    out = {}
    for f in sorted(glob.glob(os.path.join(paths.DECLARATIONS, "*.json"))):
        d = json.load(open(f))
        if d.get("source_id"):
            out.setdefault(d["source_id"], (os.path.relpath(f, paths.DATASET), d))
    return out


def build(dst, force=False):
    t0 = time.time()
    inp = snapshot.inputs(); fp = snapshot.fingerprint(inp)
    if os.path.exists(dst): os.remove(dst)
    conn = sqlite3.connect(dst)
    conn.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA temp_store=MEMORY; PRAGMA cache_size=-400000;")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO input VALUES(?,?,?)", inp)
    ident = identity.Identity()
    fam = families.get(); date_preds = families.date_predicates()
    sources = load_sources()
    for sid, (where, d) in sources.items():
        conn.execute("INSERT INTO source VALUES(?,?,?)", (sid, where, json.dumps(d)))
    AC = archive_clubs()
    C = AC.Clubs()
    global REAL_LEAGUES
    REAL_LEAGUES = {lg["league"] for c in C.T["clubs"] for s in c["segments"] for lg in s["leagues"]}
    # ---- clubs ----------------------------------------------------------
    for c in C.T["clubs"]:
        conn.execute("INSERT INTO club VALUES(?,?,?,?,?,?)", (c["id"], json.dumps(c), c.get("first"), c.get("last"),
                     c.get("origin"), (c.get("lineage") or {}).get("kind")))
        for s in c["segments"]: conn.execute("INSERT INTO club_code VALUES(?,?,?,?)", (s["code"], s["first"], s["last"], c["id"]))
        for n in c["names"]: conn.execute("INSERT INTO club_name VALUES(?,?,?,?,?,?)", (AC.norm(n["name"]), n["name"], n["first"], n["last"], c["id"], n["kind"]))
    ids = {c["id"] for c in C.T["clubs"]}; codes = {s["code"] for c in C.T["clubs"] for s in c["segments"]}
    for section, items in (C.T.get("unresolved") or {}).items():
        if not isinstance(items, list): continue
        for it in items:
            txt = json.dumps(it)
            mentions = sorted({i for i in ids if i in txt} | {f"code:{k}" for k in codes if re.search(r'"' + re.escape(k) + r'"', txt)})
            conn.execute("INSERT INTO club_unresolved VALUES(?,?,?)", (section, txt, json.dumps(mentions)))
    log(f"clubs: {len(ids)} ids, {len(codes)} codes, leagues {sorted(REAL_LEAGUES)}")
    # ---- stores ---------------------------------------------------------
    files = sorted(glob.glob(os.path.join(paths.BUILD, "*.json")))
    people = collections.defaultdict(lambda: {"n": 0, "first": None, "last": None, "roles": set()})
    names = []
    club_cache = {}
    n_claims = 0; rowid = 0
    per_store = {}
    for f in files:
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception as e:
            log(f"  {st}: NOT JSON ({e})"); continue
        if not is_claim_store(d):
            # Not silent any more. RS-G5 counts and explains every one of these; the log
            # line is so a build that skipped something says so at the time, too.
            log(f"  {st}: not a claim store, skipped ({'array' if isinstance(d, list) else 'object with no top-level claims list'})")
            continue
        table = d.get("source_records") if isinstance(d.get("source_records"), dict) else None
        inline = d["source"].get("source_id") if isinstance(d.get("source"), dict) else None
        if inline and inline not in sources:
            sources[inline] = (f"build/{st}.json#source", d["source"])
            conn.execute("INSERT OR IGNORE INTO source VALUES(?,?,?)", (inline, f"build/{st}.json#source", json.dumps(d["source"])))
        shape = "canonical" if set(d) >= {"claims", "denotations", "persons", "source_records", "universe"} else "ingest-envelope"
        league = store_league(st)
        if table is not None:
            conn.executemany("INSERT OR REPLACE INTO source_record VALUES(?,?,?,?)",
                             ((st, sr, v.get("source_id"), v.get("locator")) for sr, v in table.items()))
        rows = []; drows = []
        for i, c in enumerate(d["claims"]):
            s = c.get("subject"); scope = s[0] if isinstance(s, list) and s else "?"
            s1 = s[1] if isinstance(s, list) and len(s) > 1 else None
            person = ident.resolve(st, s1) if scope in PERSON_SCOPES else None
            yr = club_str = club_id = via = None; lg = None
            if scope == "stint" and isinstance(s, list) and len(s) >= 4:
                club_str = str(s[2]); yr = season_year(s[3]); lg = league
                if yr is not None:
                    k = (club_str, yr, lg)
                    if k not in club_cache:
                        r = C.by_code_year(club_str, yr)
                        if r: club_cache[k] = (r, "code")
                        else:
                            res = C.resolve(club_str, yr, lg if lg in REAL_LEAGUES else None, source="service")
                            club_cache[k] = res if res else (None, None)
                    club_id, via = club_cache[k]
            elif scope == "person_season" and isinstance(s, list) and len(s) >= 3:
                yr = season_year(s[2]); lg = league
            pred = c.get("predicate"); famname = fam["of"].get(pred, pred)
            val = c.get("value"); kind = c.get("kind")
            sr = c.get("source_record")
            sr_in = None if table is None else int(sr in table)
            extra = {k: v for k, v in c.items() if k not in ("id", "subject", "predicate", "value", "kind", "source_id",
                     "source_record", "stated_by", "attribution", "observed_at", "note")}
            rowid += 1
            rows.append((rowid, st, c.get("id") or f"#{i}", scope, json.dumps(s), str(s1) if s1 is not None else None, person,
                         lg, yr, club_str, club_id, via, pred, famname, json.dumps(val), None if isinstance(val, (dict, list)) else (None if val is None else str(val)),
                         c.get("source_id"), sr, sr_in, c.get("stated_by"), json.dumps(c.get("attribution") or []),
                         kind, json.dumps(c.get("observed_at")), observed_year(c.get("observed_at")), c.get("note"),
                         json.dumps(extra) if extra else None))
            if pred in date_preds and kind != "absent":
                # THE SOURCE IS PASSED. A source that has DECLARED its numeric date
                # order, with the measurement behind it, is read in that order; every
                # other source still refuses a bare numeric date. Ruled 2026-09-08.
                r = dates.read(val, c.get("source_id"))
                drows.append((rowid, famname, None if val is None else str(val), r and r["year"], r and r["month"], r and r["day"],
                              r and r["precision"], r and int(r["approximate"]), r and r["trailing"], int(r is not None)))
            if person:
                p = people[person]; p["n"] += 1
                if yr and scope == "stint":
                    p["first"] = yr if p["first"] is None else min(p["first"], yr)
                    p["last"] = yr if p["last"] is None else max(p["last"], yr)
                    p["roles"].add("player" if lg in REAL_LEAGUES else lg.lower())
                if pred in ("pfa.coaching_season", "pfa.coaching_playoffs"): p["roles"].add("coaches")
                if pred == "pfa.officiating_season": p["roles"].add("official")
                if pred == "name" and val: names.append((person, str(val), norm_name(val), pred, st, rowid, observed_year(c.get("observed_at"))))
                if pred == "pfa.name_as_printed" and isinstance(val, dict):
                    for v in {val.get("name"), val.get("full")} - {None}: names.append((person, v, norm_name(v), pred, st, rowid, None))
        conn.executemany("INSERT INTO claim VALUES(" + ",".join("?" * 26) + ")", rows)
        if drows: conn.executemany("INSERT INTO date_reading VALUES(?,?,?,?,?,?,?,?,?,?)", drows)
        for i, dn in enumerate(d.get("denotations") or []):
            conn.execute("INSERT INTO denotation VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (st, dn.get("id") or f"#{i}", dn.get("source_record"), ident.resolve(st, dn.get("person")), dn.get("person"),
                          json.dumps(dn.get("discriminator")), dn.get("method"), dn.get("matched_against"), dn.get("status"), dn.get("note")))
        per_store[st] = len(rows)
        conn.execute("INSERT INTO store VALUES(?,?,?,?,?,?)", (st, shape, len(rows), int(table is not None), inline, league))
        n_claims += len(rows)
        log(f"  {st:36s} {len(rows):9,} claims   total {n_claims:11,}   {time.time()-t0:5.0f}s")
        del d, rows
    # ---- people -----------------------------------------------------------
    log("people: reading the index once, then releasing it")
    idx_names = {}; idx_keys = set()
    st_before = os.stat(paths.PERSON_INDEX)
    idx = json.load(open(paths.PERSON_INDEX))
    st_after = os.stat(paths.PERSON_INDEX)
    if (st_before.st_mtime_ns, st_before.st_size) != (st_after.st_mtime_ns, st_after.st_size):
        log("  index changed during read; reading again"); idx = json.load(open(paths.PERSON_INDEX))
    for k, v in idx.items():
        if k == "_clubs" or not isinstance(v, dict): continue
        idx_keys.add(k); idx_names[k] = (v.get("name"), (v.get("merged_into") or {}).get("person"), v.get("merged_from"))
    del idx
    merges = {}
    if os.path.exists(paths.PERSON_MERGES):
        for m in json.load(open(paths.PERSON_MERGES)).get("merges", []):
            merges[m["absorbed_person"]] = (m["canonical_person"], m["merge_id"])
    ours = set(people) | set(ident.raw)          # what the CLAIMS and the identity map know: the thing G4 compares with the index
    allp = ours | idx_keys                        # the person table also carries index-only ids, so /people/{id} can say "index only, no claim"
    prow = []
    for pid in sorted(allp):
        iv = ident.raw.get(pid); p = people.get(pid)
        nm, mi_idx, mf = idx_names.get(pid, (None, None, None))
        mi, mid = merges.get(pid, (mi_idx, None))
        prow.append((pid, int(iv is not None), json.dumps(iv["slugs"] if iv else []), json.dumps(iv["local"] if iv else []),
                     iv["evidence"] if iv else None, mi, mid, json.dumps(mf) if mf else None, int(pid in idx_keys), nm,
                     p["n"] if p else 0, p["first"] if p else None, p["last"] if p else None, json.dumps(sorted(p["roles"])) if p else "[]"))
    conn.executemany("INSERT INTO person VALUES(" + ",".join("?" * 14) + ")", prow)
    conn.executemany("INSERT INTO person_name VALUES(?,?,?,?,?,?,?)", names)
    conn.executemany("INSERT INTO person_name_fts(norm, person, name) VALUES(?,?,?)",
                     ((n[2], n[0], n[1]) for n in names))
    for (src, lg, y, s, why), n in C.refused.items():
        conn.execute("INSERT INTO club_refusal VALUES(?,?,?,?,?)", (s, int(y) if str(y).isdigit() else None, lg, why, n))
    log(f"people: {len(allp):,} (claims {len(people):,}, identity {len(ident):,}, claims|identity {len(ours):,}, index {len(idx_keys):,}); names {len(names):,}")
    log("indexes")
    conn.executescript(INDEXES)
    log("source summary")   # /sources must never scan 5M claims at request time
    conn.execute("INSERT INTO source_summary SELECT source_id, store, predicate, COUNT(*), COUNT(DISTINCT source_record) FROM claim GROUP BY source_id, store, predicate")
    log("per-person family and stint summaries")   # so a census or a population filter never re-aggregates claims per request
    conn.execute("INSERT INTO person_family SELECT person, family, SUM(kind!='absent'), SUM(kind='absent') FROM claim WHERE person IS NOT NULL GROUP BY person, family")
    conn.execute("INSERT OR IGNORE INTO stint_person SELECT DISTINCT person, league, year FROM claim WHERE scope='stint' AND person IS NOT NULL AND year IS NOT NULL")
    # ---- contested (date families by same-day; other families by literal) ----
    log("contested")
    contested = build_contested(conn, fam)
    log(f"  {len(contested):,} (person, family) pairs contested")
    # ---- gates -------------------------------------------------------------
    log("gates")
    results = gates.run(conn, {"index_keys": idx_keys, "people": ours})   # NOT allp: a set that already contains the index cannot fail G4
    failed = [g for g in results if g["status"] == "FAIL"]
    for g in results:
        conn.execute("INSERT OR REPLACE INTO gate VALUES(?,?,?,?)", (g["name"], g["status"], json.dumps(g["counts"]), json.dumps(g["report"])))
        log(f"  {g['name']}: {g['status']}  {g['counts']}")
    meta = {"snapshot_id": fp, "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "claims": n_claims, "people": len(allp), "stores": len(per_store), "index_people": len(idx_keys),
            "gates_status": "FAIL" if failed else "PASS", "forced": int(bool(failed and force)),
            "build_seconds": round(time.time() - t0), "predicate_families": json.dumps(fam["raw"]["families"])}
    conn.executemany("INSERT INTO meta VALUES(?,?)", [(k, str(v)) for k, v in meta.items()])
    log("analyze")   # without statistics the planner prefers a 250K-row family index to the person index
    conn.execute("ANALYZE")
    conn.commit(); conn.execute("VACUUM"); conn.close()
    log(f"built in {time.time()-t0:.0f}s: {n_claims:,} claims, {len(allp):,} people, {len(per_store)} stores")
    return failed


def build_contested(conn, fam):
    out = []
    date_fams = {f for f, s in fam["families"].items() if s.get("kind") == "date"}
    # date families: group by same day
    cur = conn.execute("""SELECT c.person, c.family, d.literal, d.y, d.m, d.d, d.readable FROM claim c JOIN date_reading d ON d.claim=c.id
                          WHERE c.person IS NOT NULL ORDER BY c.person, c.family""")
    last = None; items = []
    def flush():
        if last is None: return
        person, family = last
        seen = {}
        for lit, y, m, dd, r in items: seen.setdefault(lit, (lit, ({"year": y, "month": m, "day": dd} if r else None)))
        groups = dates.same_day_groups(list(seen.values()))
        unread = sorted({lit for lit, y, m, dd, r in items if not r})
        for u in unread: groups.append([u])
        lits = sorted({lit for lit, *_ in items})
        if len(groups) > 1:
            out.append((person, family, len(groups), json.dumps(groups), json.dumps(lits)))
    for person, family, lit, y, m, dd, r in cur:
        if (person, family) != last:
            flush(); last = (person, family); items = []
        items.append((lit, y, m, dd, r))
    flush()
    # ---- non-date families: group by the DECLARED READING, not by the literal ----
    # A family is what lets the model record a disagreement; the reading is what stops it
    # recording a false one. Grouping by literal made `Ohio St.` and `Ohio State` two
    # values of one field -- a disagreement between two sources that agree, which is the
    # defect RS-G6 exists to refuse, recorded by the builder RS-G6 checks. So the reading
    # is applied HERE, at the point of recording, and RS-G6 then finds nothing because
    # there is nothing to find rather than because the population is empty.
    #
    # ONE DEFINITION, IMPORTED. reading_view loads dataset/src/readings.py by file path.
    # A value the reader cannot read is its OWN group and is never folded, exactly as an
    # unreadable date is: unreadable is an answer, not a licence to merge.
    import reading_view as RV
    multi = [f for f, s in fam["families"].items() if s.get("kind") != "date"]
    has_reading = set(RV.families())
    n_false = 0
    for f in multi:
        for person, lits in conn.execute("""SELECT person, json_group_array(DISTINCT value) FROM claim
                                            WHERE family=? AND person IS NOT NULL AND kind!='absent' AND value IS NOT NULL
                                            GROUP BY person HAVING COUNT(DISTINCT value)>1""", (f,)):
            vals = []
            for raw in json.loads(lits):
                try: vals.append(json.loads(raw))
                except (TypeError, ValueError): vals.append(raw)
            vals = [v for v in vals if v is not None]
            if len(vals) < 2: continue
            if f in has_reading:
                # USE THE SHARED GROUPER, NOT A COPY OF IT. This block used to carry its
                # own loop, and it was subtly different: RV.group REFINES a group's fact
                # as values join it (`facts[gi] = {**f, **r}`) and this one did not. With
                # a dict reading that difference decides the answer -- a draft value
                # stating no league matched an AFL fact, joined it, and then the NFL value
                # matched the same unrefined fact and joined too, folding two leagues'
                # selections into one. same() is not transitive, and only the refinement
                # makes first-match grouping safe. One ruling, one implementation.
                gs, unread = RV.group(f, vals)
                groups = [[vals[i] for i in g["indices"]] for g in gs] + [[vals[i]] for i in unread]
                if len(groups) < len(vals): n_false += len(vals) - len(groups)
            else:
                groups = [[v] for v in vals]
            if len(groups) > 1:
                out.append((person, f, len(groups), json.dumps(groups), json.dumps(vals)))
    if n_false:
        log(f"  values folded by a declared reading rather than recorded as disagreeing: {n_false:,}")
    conn.executemany("INSERT OR REPLACE INTO contested VALUES(?,?,?,?,?)", out)
    return out


def publish(tmp, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.replace(tmp, dst)


def main(argv):
    force = "--force" in argv
    os.makedirs(paths.CACHE_DIR, exist_ok=True)
    tmp = paths.READ_MODEL + ".building"
    lock = paths.READ_MODEL + ".lock"
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip()); os.kill(pid, 0)
            print(f"a build is already running (pid {pid}); refusing to start another", file=sys.stderr); return 2
        except (ValueError, ProcessLookupError, PermissionError):
            os.remove(lock)
    open(lock, "w").write(str(os.getpid()))
    try:
        failed = build(tmp, force=force)
        if failed and not force:
            print("\nREFUSING TO PUBLISH -- gates failed:", file=sys.stderr)
            for g in failed: print(f"  {g['name']}: {g['counts']}", file=sys.stderr)
            print(f"the previous read model, if any, keeps serving. Unpublished build left at {tmp}", file=sys.stderr)
            return 1
        if failed:
            print("\nWARNING: publishing with FAILED gates because --force was given. Every response will say so.", file=sys.stderr)
        publish(tmp, paths.READ_MODEL)
        print(f"published {paths.READ_MODEL}")
        return 0
    finally:
        try: os.remove(lock)
        except OSError: pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
