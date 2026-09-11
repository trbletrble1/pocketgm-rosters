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

A REBUILD RE-READS ONLY WHAT MOVED. 74 of 147 seconds used to be spent parsing 957
store files, and roughly three quarters of that re-read files that had not changed.
The previous published model is opened READ ONLY and the rows of unchanged stores are
lifted out of it; only stores whose file has moved are parsed again. Measured: 154s
becomes 93s.

  --full   parse every store, whatever its mtime says
  --fast   the default; kept as a flag so a script can be explicit

WHAT INVALIDATES A CACHED STORE BESIDES ITS OWN mtime -- nearly everything, so the
test is one fingerprint over everything EXCEPT the store files: the declarations that
decide how a claim is read, and the code that reads it. See READ_STAGE_INPUTS. If any
of it moved, every store is re-read. This is the case that would go wrong quietly: a
declaration changes how a claim is read without the store file moving by a byte.

This is a cache of READING, not of deriving. `person`, `person_name`, `contested`,
`person_family`, `stint_person`, `source_summary` and `club_refusal` are still built
over the whole corpus every time.
"""
import os, sys, json, glob, sqlite3, time, collections, re, datetime, unicodedata, hashlib
import shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, families, identity, snapshot, dates, gates
import classification

NAME_PREDICATES = classification.name_predicates()
import league_tokens as LT


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
CREATE TABLE contested(person TEXT, family TEXT, year TEXT, n_groups INTEGER, groups TEXT, literals TEXT, PRIMARY KEY(person, family, year));
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
    (store_league_tokens: assistants -> COACHES, ruled 2026-09-07). Read, not mirrored.

    Returns None where the declaration says the store has NO league of its own; the
    caller then takes it from the season key on the subject. The rule that reads the
    declaration lives in service/league_tokens.py and has exactly one implementation --
    it used to have two, and both took the first word of an English sentence, so the
    twelve stores declared "NOT A LEAGUE -- ..." got a league called NOT."""
    global _LEAGUE_TOKENS
    if _LEAGUE_TOKENS is None:
        _LEAGUE_TOKENS = LT.tokens(paths.INDEX_REBUILD_DECL)
    return LT.store_league(st, _LEAGUE_TOKENS)


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


# ---------------------------------------------------------------- the read-stage cache
#
# WHAT INVALIDATES A CACHED STORE BESIDES ITS OWN mtime. This is the question that
# makes or breaks the fast path, and the answer is: nearly everything, so the test is
# a single fingerprint of EVERYTHING EXCEPT the store files.
#
# A row in `claim` is not a copy of the store. It is the store read THROUGH:
#
#   identity.json          -> the `person` column
#   build/clubs.json       -> `club_id`, `club_via`, REAL_LEAGUES, and the roles
#   person-index-rebuild   -> `store_league_tokens`, hence the `league` column
#   predicate-families     -> the `family` column, and which claims get a date reading
#   dates-as-printed,      -> every row of `date_reading`
#     date-formats-by-source
#   coaching-seasons       -> NAME_PREDICATES, hence which claims become `person_name`
#   every declarations/*.json with a source_id -> the `source` table
#   AND THE CODE ITSELF    -> build_read_model.py and the modules its loop calls
#
# A declaration can therefore change how a claim is read without the store file moving
# by a byte -- which is exactly the case that would go wrong quietly. So the cache is
# all-or-nothing on that fingerprint: if any of it moved, every store is re-read. Only
# when it is identical does an unchanged store's mtime and size mean its rows are still
# right.
READ_STAGE_INPUTS = ["build-reports/identity.json", "build/clubs.json",
                     "declarations/person-index-rebuild.json", "declarations/coaching-seasons.json",
                     "service/declarations/predicate-families.json",
                     "service/declarations/dates-as-printed.json",
                     "service/declarations/date-formats-by-source.json",
                     "service/declarations/classification.json",
                     "service/build_read_model.py", "service/league_tokens.py", "service/identity.py",
                     "service/dates.py", "service/families.py", "service/classification.py",
                     "src/clubs.py"]


def read_stage_fingerprint():
    """One hash over every input that changes how a claim is READ, the code included,
    and over the declarations that name a source. The store files are NOT in it: they
    are what the fingerprint licenses us to skip."""
    h = hashlib.sha256()
    paths_ = list(READ_STAGE_INPUTS) + sorted(
        os.path.relpath(f, paths.DATASET) for f in glob.glob(os.path.join(paths.DECLARATIONS, "*.json")))
    for rel in paths_:
        f = os.path.join(paths.DATASET, rel)
        h.update(rel.encode())
        try:
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""): h.update(chunk)
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest()[:16]


def cacheable_stores(prev_path, fp_now):
    """-> ({store: (mtime_ns, size)} we may keep from `prev_path`, why not).

    A store is cacheable when the read-stage fingerprint is unchanged AND the previous
    model recorded that store with the mtime and size the file has today."""
    if not prev_path or not os.path.exists(prev_path): return {}, "no previous model"
    try:
        c = sqlite3.connect(f"file:{prev_path}?mode=ro", uri=True)
        m = dict(c.execute("SELECT key, value FROM meta WHERE key IN ('read_stage_fingerprint','snapshot_id')"))
        if m.get("read_stage_fingerprint") != fp_now:
            c.close(); return {}, "the read-stage fingerprint changed: a declaration or the code moved"
        recorded = {p: (mt, sz) for p, mt, sz in c.execute("SELECT path, mtime_ns, size FROM input")}
        have = {r[0] for r in c.execute("SELECT name FROM store")}   # the column is `name`
        c.close()
    except sqlite3.Error as e:
        return {}, f"the previous model could not be read: {e}"
    keep = {}
    for f in sorted(glob.glob(os.path.join(paths.BUILD, "*.json"))):
        st = os.blocks if False else os.path.basename(f)[:-5]
        rel = os.path.relpath(f, paths.DATASET)
        try: stt = os.stat(f)
        except OSError: continue
        if st in have and recorded.get(rel) == (stt.st_mtime_ns, stt.st_size):
            keep[st] = (stt.st_mtime_ns, stt.st_size)
    return keep, None


def copy_cached(conn, prev_path, keep):
    """Copy the read-stage rows of the cached stores out of the previous model.

    -> (max claim id used, {store: n_claims}, [person_name tuples], {person: aggregate}).
    Only the tables the READ STAGE writes are copied. Everything downstream --
    person, person_family, stint_person, contested, source_summary -- is still built
    over the whole corpus, exactly as before. This is a cache of reading, not of
    deriving."""
    if not keep: return 0, {}, [], {}
    # ATTACHED READ ONLY. The previous model is the one being SERVED; a fast build must
    # never take a write lock on it, and the file: URI is the only way to say so.
    conn.execute("ATTACH DATABASE ? AS prev", (f"file:{prev_path}?mode=ro",))
    q = ",".join("?" * len(keep)); ks = sorted(keep)
    conn.execute(f"INSERT INTO claim SELECT * FROM prev.claim WHERE store IN ({q})", ks)
    conn.execute(f"INSERT INTO date_reading SELECT d.* FROM prev.date_reading d JOIN prev.claim c ON c.id=d.claim WHERE c.store IN ({q})", ks)
    conn.execute(f"INSERT INTO denotation SELECT * FROM prev.denotation WHERE store IN ({q})", ks)
    conn.execute(f"INSERT INTO source_record SELECT * FROM prev.source_record WHERE store IN ({q})", ks)
    conn.execute(f"INSERT INTO store SELECT * FROM prev.store WHERE name IN ({q})", ks)   # the column is `name`
    names = [tuple(r) for r in conn.execute(f"SELECT * FROM prev.person_name WHERE store IN ({q})", ks).fetchall()]
    # THE STORE'S OWN RECORDED COUNT, not COUNT(*) over its claims: four stores hold
    # zero claims and a GROUP BY drops them, which made `meta.stores` read 500 against
    # a full build's 504. The equality gate caught it.
    per = {r[0]: r[1] for r in list(conn.execute(f"SELECT name, claims FROM prev.store WHERE name IN ({q})", ks))}
    # AN INLINE SOURCE IS REGISTERED WHILE THE STORE IS READ, so a cached store's
    # source row has to come with it. 11 were missing until the gate said so.
    inline = [tuple(r) for r in conn.execute(
        f"SELECT * FROM prev.source WHERE declared_in LIKE 'build/%#source' AND "
        f"REPLACE(REPLACE(declared_in,'build/',''),'.json#source','') IN ({q})", ks).fetchall()]
    # TWO DIFFERENT NUMBERS, and conflating them was a real bug. `top` is the highest
    # claim id copied, and new rows must be numbered above it. `n` is HOW MANY rows
    # were copied. They are equal only when every store is cached -- which is exactly
    # the case the equality gate happened to exercise, so it did not catch this: with
    # two stores re-read, `n_claims` started at the max id and the build reported
    # 7,907,595 claims where it held 7,897,823.
    top = conn.execute("SELECT COALESCE(MAX(id), 0) FROM claim").fetchone()[0]
    n_copied = conn.execute("SELECT COUNT(*) FROM claim").fetchone()[0]
    # the `people` aggregate the read loop would have accumulated for these stores,
    # re-derived from the very rows just copied. Same arithmetic, read off the claims.
    people = {}
    for pid, n in list(conn.execute(f"SELECT person, COUNT(*) FROM prev.claim WHERE store IN ({q}) AND person IS NOT NULL GROUP BY person", ks)):
        people[pid] = {"n": n, "first": None, "last": None, "roles": set()}
    for pid, mn, mx in list(conn.execute(f"SELECT person, MIN(year), MAX(year) FROM prev.claim WHERE store IN ({q}) AND person IS NOT NULL AND scope='stint' AND year IS NOT NULL GROUP BY person", ks)):
        people[pid]["first"], people[pid]["last"] = mn, mx
    for pid, lg in list(conn.execute(f"SELECT DISTINCT person, league FROM prev.claim WHERE store IN ({q}) AND person IS NOT NULL AND scope='stint' AND year IS NOT NULL", ks)):
        if lg in REAL_LEAGUES: people[pid]["roles"].add("player")
        elif lg: people[pid]["roles"].add(lg.lower())
    for pid, pred in list(conn.execute(f"SELECT DISTINCT person, predicate FROM prev.claim WHERE store IN ({q}) AND person IS NOT NULL AND predicate IN ('pfa.coaching_season','pfa.coaching_playoffs','pfa.officiating_season')", ks)):
        people[pid]["roles"].add("official" if pred == "pfa.officiating_season" else "coaches")
    # EVERY STATEMENT MUST BE FINISHED BEFORE THE DETACH. An undrained cursor holds the
    # attached database open and SQLite reports it as locked -- which is a confusing
    # error for what is really "you are still reading it".
    conn.commit()
    conn.execute("DETACH DATABASE prev")
    conn.executemany("INSERT OR IGNORE INTO source VALUES(?,?,?)", inline)
    return top, n_copied, per, names, people, {r[0] for r in inline}


def build(dst, force=False, fast=False, prev=None):
    t0 = time.time()
    inp = snapshot.inputs(); fp = snapshot.fingerprint(inp)
    rs_fp = read_stage_fingerprint()
    keep, why_not = ({}, "not asked for") if not fast else cacheable_stores(prev, rs_fp)
    if os.path.exists(dst): os.remove(dst)
    # uri=True so the previous model can be ATTACHed read-only by URI. A plain path
    # still opens normally; the flag only permits the file: form.
    conn = sqlite3.connect(dst, uri=True)
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
    # THE CACHE. Rows of stores whose file has not moved AND whose reading has not
    # changed are lifted out of the previous model rather than parsed again. New ids
    # start above the highest cached one: `claim.id` is a counter, and a cached store
    # keeps the ids it already had so `date_reading` and `person_name` still point at
    # the right rows. A full build numbers them differently, which is why the equality
    # gate matches claims on (store, cid) and translates.
    if keep:
        rowid, n_copied, cached_per, cached_names, cached_people, cached_inline = copy_cached(conn, prev, keep)
        sources.update({sid: (f"build/?#source", None) for sid in cached_inline if sid not in sources})
        per_store.update(cached_per); names.extend(cached_names)
        for pid, agg in cached_people.items():
            p = people[pid]; p["n"] += agg["n"]; p["roles"] |= agg["roles"]
            for k in ("first", "last"):
                if agg[k] is not None:
                    p[k] = agg[k] if p[k] is None else (min(p[k], agg[k]) if k == "first" else max(p[k], agg[k]))
        n_claims = n_copied
        log(f"read-stage cache: {len(keep)} of {len(files)} stores reused, {n_claims:,} claims not re-read")
    elif fast:
        log(f"read-stage cache: NOT USED -- {why_not}")
    for f in files:
        st = os.path.basename(f)[:-5]
        if st in keep: continue
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
                club_str = str(s[2]); yr = season_year(s[3])
                # A store that declares it has no league carries it on the subject:
                # ["stint", person, code, "APFA-1920"]. Reading it from the filename
                # instead is what put 132,038 stint keys in a league called NOT.
                lg = league if league else LT.from_season_key(s[3], REAL_LEAGUES)
                if yr is not None:
                    k = (club_str, yr, lg)
                    if k not in club_cache:
                        # THE LEAGUE GOES INTO THE LOOKUP, including the code lookup. This
                        # tried by_code_year first -- which knows no league -- so `CHI` in a
                        # 1974 WFL coaching cell became the Decatur Staleys before the
                        # league-aware resolver was ever asked. Ryan, 2026-09-11.
                        res = C.resolve(club_str, yr, lg if lg in REAL_LEAGUES else None, source="service")
                        club_cache[k] = res if res else (None, None)
                    club_id, via = club_cache[k]
            elif scope == "person_season" and isinstance(s, list) and len(s) >= 3:
                yr = season_year(s[2])
                lg = league if league else LT.from_season_key(s[2], REAL_LEAGUES)
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
                    # A store that declares no league establishes no ROLE either. This
                    # line used to read `lg.lower()` for anything not a real league,
                    # which is how 32,791 men acquired the role "not" from a league
                    # called NOT. Where the league is unknown the role is unknown, and
                    # the man's other claims say what he was.
                    if lg in REAL_LEAGUES:
                        p["roles"].add("player")
                    elif lg:
                        p["roles"].add(lg.lower())
                if pred in ("pfa.coaching_season", "pfa.coaching_playoffs"): p["roles"].add("coaches")
                if pred == "pfa.officiating_season": p["roles"].add("official")
                # WHICH PREDICATES ARE NAMES is declared, not spelt here. This was the
                # SECOND implementation of that question -- queries.py excluded the single
                # literal "name" from facts -- and the two did not agree: pfa.name_as_printed
                # was indexed AND served as a fact, statscrew.formal_name and full_name were
                # served as facts and never indexed, so search could not find 1,607 names.
                if pred in NAME_PREDICATES and val is not None:
                    if isinstance(val, dict):   # pfa.name_as_printed carries two forms
                        for v in {val.get("name"), val.get("full")} - {None}:
                            names.append((person, v, norm_name(v), pred, st, rowid, None))
                    else:
                        names.append((person, str(val), norm_name(val), pred, st, rowid, observed_year(c.get("observed_at"))))
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
    if True:                                # read loudly: the decisions are a declaration now (2026-09-11)
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
    # CLUB REFUSALS ARE DERIVED FROM THE CLAIMS, not accumulated while reading them.
    #
    # `C.refused` was filled inside the store loop, so a fast build -- which does not
    # parse a cached store -- lost 437 of them and the equality gate said so. The set
    # is a function of the DISTINCT (club string, year, league) the corpus holds and
    # nothing else: `club_cache` already memoised the resolver to one call per key, so
    # asking once per distinct key here gives the same answers and the same counts.
    # Doing it after the loop makes it identical whether a store was read or reused.
    C.refused.clear()
    for club_str, yr, lg in conn.execute(
            "SELECT DISTINCT club_str, year, league FROM claim WHERE scope='stint' "
            "AND club_str IS NOT NULL AND year IS NOT NULL AND club_id IS NULL").fetchall():
        # NO SHORT-CIRCUIT ON A LEAGUE-BLIND LOOKUP: a claim refused because its code names a
        # club of ANOTHER league would be skipped here, and its refusal never recorded.
        C.resolve(club_str, yr, lg if lg in REAL_LEAGUES else None, source="service")
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
    meta = {"snapshot_id": fp, "read_stage_fingerprint": rs_fp,
            "stores_reused_from_the_previous_model": len(keep),
            "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "claims": n_claims, "people": len(allp), "stores": len(per_store), "index_people": len(idx_keys),
            "gates_status": "FAIL" if failed else "PASS", "forced": int(bool(failed and force)),
            "build_seconds": round(time.time() - t0), "predicate_families": json.dumps(fam["raw"]["families"])}
    conn.executemany("INSERT INTO meta VALUES(?,?)", [(k, str(v)) for k, v in meta.items()])
    log("analyze")   # without statistics the planner prefers a 250K-row family index to the person index
    conn.execute("ANALYZE")
    conn.commit(); conn.execute("VACUUM"); conn.close()
    log(f"built in {time.time()-t0:.0f}s: {n_claims:,} claims, {len(allp):,} people, {len(per_store)} stores")
    return failed


# THE KEY CARRIES THE YEAR WHERE THE CLAIM IS ABOUT A SEASON. Ruled by Ryan,
# 2026-09-10, after both keys were built and compared.
#
# A contest is two answers to ONE question. `(person, family)` alone asks "what is this
# man's position?", which is not one question -- a guard who later played tackle got
# recorded as a disagreement, 17,372 times. Adding the year asks "what was his position
# THAT SEASON", which is.
#
# IT IS THE RESOLVED `person`, NEVER THE RAW `subject`. Keying on the subject column was
# the obvious reading of the defect and it would have UNDONE PERSON MERGING: subject
# holds the pre-merge id, only 28.2% of birth_date claims have the two agree, and 17,315
# people carry five or more distinct subject strings. A man merged from five records
# would have lost the disagreement BETWEEN them -- the most valuable thing the merge
# produces -- and the total would have gone UP, so it would have looked like a gain.
#
# AND THE PRIMARY KEY MOVED WITH IT. The table was PRIMARY KEY(person, family) written
# with INSERT OR REPLACE, so a finer grouping without a wider key would have kept one
# season per man and dropped the rest IN SILENCE.
SEASON_SCOPES = ("person_season", "stint", "club_season", "league_season")
_YKEY = ("CASE WHEN c.scope IN " + str(SEASON_SCOPES) +
         " THEN COALESCE(CAST(c.year AS TEXT), '') ELSE '' END")


def build_contested(conn, fam):
    out = []
    date_fams = {f for f, s in fam["families"].items() if s.get("kind") == "date"}
    # date families: group by same day
    cur = conn.execute(f"""SELECT c.person, c.family, {_YKEY} yk, d.literal, d.y, d.m, d.d, d.readable FROM claim c JOIN date_reading d ON d.claim=c.id
                          WHERE c.person IS NOT NULL ORDER BY c.person, c.family, yk""")
    last = None; items = []
    def flush():
        if last is None: return
        person, family, yk = last
        seen = {}
        for lit, y, m, dd, r in items: seen.setdefault(lit, (lit, ({"year": y, "month": m, "day": dd} if r else None)))
        groups = dates.same_day_groups(list(seen.values()))
        unread = sorted({lit for lit, y, m, dd, r in items if not r})
        for u in unread: groups.append([u])
        lits = sorted({lit for lit, *_ in items})
        if len(groups) > 1:
            out.append((person, family, yk, len(groups), json.dumps(groups), json.dumps(lits)))
    for person, family, yk, lit, y, m, dd, r in cur:
        if (person, family, yk) != last:
            flush(); last = (person, family, yk); items = []
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
        for person, yk, lits in conn.execute(f"""SELECT person, {_YKEY.replace("c.","")} yk, json_group_array(DISTINCT value) FROM claim c
                                            WHERE family=? AND person IS NOT NULL AND kind!='absent' AND value IS NOT NULL
                                            GROUP BY person, yk HAVING COUNT(DISTINCT value)>1""", (f,)):
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
                out.append((person, f, yk, len(groups), json.dumps(groups), json.dumps(vals)))
    if n_false:
        log(f"  values folded by a declared reading rather than recorded as disagreeing: {n_false:,}")
    conn.executemany("INSERT OR REPLACE INTO contested VALUES(?,?,?,?,?,?)", out)
    return out


# HOW MANY PUBLISHED MODELS ARE KEPT, and what removes them.
#
# TWO, besides the one being served. Ruled 2026-09-09 by Ryan, after the question
# "what did the service return before this weekend?" could not be answered at all:
# publish() was a bare os.replace, which retains nothing, and the stores that would
# rebuild the old model are under build/, which is gitignored. The model of
# 2026-09-08 18:57:44 did not exist in any form fourteen hours later.
#
# Two and not one, because the useful diff is often not against the last publish
# but against the one before it -- a fix and its rebuild are usually two publishes
# on the same morning. Two and not more, because the model is ~6 GB: three on disk
# is ~18 GB, which is a number a person can hold in their head.
#
# WHAT REMOVES THEM. Nothing else, ever: only this function, only at publish time,
# oldest first by the built_at each one carries in its own meta table (never by the
# file's mtime, which a copy or a backup can rewrite). A model whose meta cannot be
# read is treated as the oldest and goes first -- it cannot be used for a diff.
# There is also a floor: if keeping two would leave less than three models' worth of
# free space, fewer are kept and the publish SAYS SO rather than filling the disk.
KEEP_PREVIOUS = 2


def model_identity(path):
    """(snapshot_id, built_at) from a published model's own meta table, or Nones.

    THE COLUMNS ARE `key` AND `value`. The first version of this function asked for
    `k` and `v`, and its `except Exception` turned the resulting OperationalError
    into "unreadable": the first retained model was filed as
    `archive-unknown-unreadable.sqlite` and the publish said so in one line nobody
    would have read twice. A guard around a required read makes the failure
    invisible, not the code robust -- so a file that IS a database but whose meta
    cannot be queried now RAISES, and only a file that is not a database at all
    returns Nones."""
    try:
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None, None
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'").fetchone():
            return None, None                      # not one of our models
        m = dict(c.execute("SELECT key, value FROM meta WHERE key IN ('snapshot_id','built_at')"))
    except sqlite3.DatabaseError as e:
        if "not a database" in str(e) or "malformed" in str(e):
            return None, None                      # corrupt: it cannot serve a diff
        raise                                      # a schema we do not understand is LOUD
    finally:
        c.close()
    return m.get("snapshot_id"), m.get("built_at")


def previous_models():
    """The retained models, NEWEST FIRST, each with the identity it carries itself."""
    out = []
    for f in glob.glob(os.path.join(paths.PREVIOUS_MODELS, "archive-*.sqlite")):
        sid, built = model_identity(f)
        out.append({"path": f, "snapshot_id": sid, "built_at": built,
                    "bytes": os.path.getsize(f), "readable": sid is not None})
    out.sort(key=lambda r: (r["built_at"] or ""), reverse=True)
    return out


def retain(dst, log=print):
    """Move the model currently being served into previous/, then prune to
    KEEP_PREVIOUS. Returns what was kept and what was removed, and says why."""
    if not os.path.exists(dst): return {"retained": None, "removed": [], "kept": 0}
    os.makedirs(paths.PREVIOUS_MODELS, exist_ok=True)
    sid, built = model_identity(dst)
    stamp = (built or "unknown").replace(":", "").replace("-", "")
    keep_path = os.path.join(paths.PREVIOUS_MODELS, f"archive-{stamp}-{sid or 'unreadable'}.sqlite")
    os.replace(dst, keep_path)          # same filesystem: atomic, and costs no copy
    size = os.path.getsize(keep_path)
    # the floor: three models' worth of headroom, or keep fewer and say so
    free = shutil.disk_usage(paths.CACHE_DIR).free
    keep = KEEP_PREVIOUS
    if free < 3 * size:
        keep = max(0, min(KEEP_PREVIOUS, int(free // max(size, 1)) - 1))
        log(f"  retention: only {free/1e9:.0f} GB free against a {size/1e9:.0f} GB model -- keeping {keep}, not {KEEP_PREVIOUS}")
    removed = []
    for r in previous_models()[keep:]:
        os.remove(r["path"])
        removed.append({"path": os.path.basename(r["path"]), "snapshot_id": r["snapshot_id"],
                        "built_at": r["built_at"],
                        "why": "oldest beyond KEEP_PREVIOUS" if r["readable"] else "its meta table could not be read, so it cannot serve a diff"})
    return {"retained": {"path": os.path.basename(keep_path), "snapshot_id": sid, "built_at": built},
            "removed": removed, "kept": len(previous_models())}


def publish(tmp, dst, log=print):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = retain(dst, log=log)
    os.replace(tmp, dst)
    if r["retained"]:
        log(f"  kept the outgoing model as previous/{r['retained']['path']} "
            f"({r['retained']['snapshot_id']}, built {r['retained']['built_at']}); {r['kept']} retained")
    for x in r["removed"]:
        log(f"  removed previous/{x['path']}: {x['why']}")
    return r


def main(argv):
    force = "--force" in argv
    # THE FAST PATH IS THE DEFAULT. A rebuild re-reads only the stores whose file has
    # moved; `--full` forces every one to be parsed again. The two are gated equal by
    # service/gate_incremental_equality.py, which builds both ways and compares every
    # table -- and a fast build silently falls back to a full one whenever anything in
    # READ_STAGE_INPUTS has changed, which includes this file.
    fast = "--full" not in argv
    dst_override = None
    if "--to" in argv:
        dst_override = argv[argv.index("--to") + 1]
    os.makedirs(paths.CACHE_DIR, exist_ok=True)
    target = dst_override or paths.READ_MODEL
    tmp = target + ".building"
    lock = paths.READ_MODEL + ".lock"
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip()); os.kill(pid, 0)
            print(f"a build is already running (pid {pid}); refusing to start another", file=sys.stderr); return 2
        except (ValueError, ProcessLookupError, PermissionError):
            os.remove(lock)
    open(lock, "w").write(str(os.getpid()))
    try:
        # THE PREVIOUS MODEL IS THE CACHE. It is the one publish() retained, and it is
        # opened READ ONLY: a fast build reads rows out of it and never writes to it.
        prev = None
        if fast:
            # THE SERVED MODEL IS THE CACHE, because it is the most recent complete
            # build. It is opened READ ONLY and the new model is assembled in `tmp`,
            # so the file being served is never touched. The newest retained model is
            # the fallback for the case where there is no served one yet.
            prevs = previous_models()
            prev = paths.READ_MODEL if os.path.exists(paths.READ_MODEL) else (prevs[0]["path"] if prevs else None)
        failed = build(tmp, force=force, fast=fast, prev=prev)
        if failed and not force:
            print("\nREFUSING TO PUBLISH -- gates failed:", file=sys.stderr)
            for g in failed: print(f"  {g['name']}: {g['counts']}", file=sys.stderr)
            print(f"the previous read model, if any, keeps serving. Unpublished build left at {tmp}", file=sys.stderr)
            return 1
        if failed:
            print("\nWARNING: publishing with FAILED gates because --force was given. Every response will say so.", file=sys.stderr)
        if dst_override:
            os.replace(tmp, target); print(f"wrote {target} (not published: --to)")
        else:
            publish(tmp, paths.READ_MODEL); print(f"published {paths.READ_MODEL}")
        return 0
    finally:
        try: os.remove(lock)
        except OSError: pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
