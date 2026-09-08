"""The HTTP surface. FastAPI; JSON; read-only.

    ~/.venvs/football-archive-service/bin/uvicorn app:app --port 8765

Every response carries `snapshot`: what the read model was built from, whether
any input has changed since, and the gate status. When an input changes the
service starts a rebuild in the background (at most one at a time, and not more
often than REBUILD_COOLDOWN) and keeps serving the old model until the new one
is published -- or refuses to publish, if a gate fails, in which case
`snapshot.rebuild.last_result` says so.
"""
import os, sys, time, json, subprocess, threading, contextlib
from urllib.parse import urlsplit, urlunsplit
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
import paths, snapshot, queries as Q, access, bios

REBUILD_COOLDOWN = int(os.environ.get("FOOTBALL_ARCHIVE_REBUILD_COOLDOWN", "600"))
AUTO_REBUILD = os.environ.get("FOOTBALL_ARCHIVE_AUTOREBUILD", "0") == "1"   # OFF by default, ruled 2026-09-07: POST /rebuild on demand
DESCRIPTION = ("A read-only service over the football archive. Every value traces to the document it came from; "
               "where sources disagree, every value is returned and `contested` is set. Nothing here chooses.")

# The MCP server, mounted at /mcp over streamable HTTP so a client that is not on this
# machine can use the same tools as the stdio server. Same functions, same contract.
import mcp_server as MCPS
from mcp.server.transport_security import TransportSecuritySettings


def _allowed_hosts():
    """The MCP transport refuses a Host header it does not know (DNS-rebinding protection,
    and it is right to). Declare the addresses this service is legitimately reached on --
    loopback, the tailnet IP and MagicDNS name, plus anything in FOOTBALL_ARCHIVE_HOSTS --
    rather than turning the protection off."""
    names = ["127.0.0.1", "localhost", "[::1]"]
    try:
        import subprocess
        ts = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        r = subprocess.run([ts, "status", "--json"], capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            self_ = json.loads(r.stdout).get("Self") or {}
            names += [ip for ip in (self_.get("TailscaleIPs") or []) if ":" not in ip]
            dns = (self_.get("DNSName") or "").rstrip(".")
            if dns: names.append(dns)
    except Exception:
        pass
    names += [h for h in os.environ.get("FOOTBALL_ARCHIVE_HOSTS", "").split(",") if h.strip()]
    port = os.environ.get("FOOTBALL_ARCHIVE_PORT", "8765")
    return sorted({h for n in names for h in (n, f"{n}:{port}", f"{n}:443")})


ALLOWED_HOSTS = _allowed_hosts()
_mcp_asgi = MCPS.server.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        allowed_hosts=ALLOWED_HOSTS,
        allowed_origins=[f"http://{h}" for h in ALLOWED_HOSTS] + [f"https://{h}" for h in ALLOWED_HOSTS]))


@contextlib.asynccontextmanager
async def _lifespan(_app):
    """A mounted Starlette sub-app's lifespan is not run by the parent; run it here or
    the MCP session manager is never started and every /mcp call fails."""
    async with _mcp_asgi.router.lifespan_context(_mcp_asgi):
        yield


app = FastAPI(title="Football Archive", description=DESCRIPTION, version="0.1", lifespan=_lifespan)
app.mount("/mcp", _mcp_asgi)


# Discovery paths an MCP client probes BEFORE it has any credentials, looking for an
# OAuth authorization server (RFC 9728 and the MCP auth spec). This service has no
# OAuth -- its credential is in the URL path -- so the honest answer is "nothing here",
# and the honest answer is 404. Answering 401 instead told Claude's connector that the
# server wanted OAuth and would not say where, which is a dead end it cannot leave.
# Nothing is served under this prefix to anyone, authenticated or not, so replying
# without a token leaks nothing that the 401 body does not already say.
DISCOVERY_PREFIX = "/.well-known/"


@app.middleware("http")
async def gate(request: Request, call_next):
    """access.py's two rules, applied to every request before it reaches a route."""
    client = request.client.host if request.client else None
    local = access.is_loopback(client)
    path = request.url.path
    # A capability URL: /t/<token>/... is the same request with the token stripped off.
    presented = None
    prefix = ""
    if path.startswith("/t/"):
        parts = path.split("/", 3)
        presented = parts[2] if len(parts) > 2 else None
        rest = "/" + (parts[3] if len(parts) > 3 else "")
        if not access.matches(presented):
            return JSONResponse({"error": "bad token in path"}, status_code=401)
        prefix = "/t/" + presented
        request.scope["path"] = path = rest
        request.scope["raw_path"] = rest.encode()
    if presented is None:
        auth = request.headers.get("authorization", "")
        presented = auth[7:].strip() if auth[:7].lower() == "bearer " else None
    if path.startswith(DISCOVERY_PREFIX):
        return JSONResponse({"error": "not found",
                             "note": "this service has no OAuth authorization server; its credential is the token"},
                            status_code=404)
    if any(path.rstrip("/").endswith(w) for w in access.WRITE_ROUTES) and (access.EXPOSED or not local):
        return JSONResponse({"error": "refused: /rebuild runs work on the machine and is loopback-only"
                                      + (" (this service is running exposed)" if access.EXPOSED else ""),
                             "note": "the archive is never written by this service; this route rebuilds its own cache"},
                            status_code=403)
    if not local and not access.matches(presented):
        return JSONResponse({"error": "a token is required from off this machine",
                             "how": "Authorization: Bearer <token>, or /t/<token>/... in the path for clients with no header field"},
                            status_code=401)
    response = await call_next(request)
    return _keep_the_token_on_redirects(response, prefix)


def _keep_the_token_on_redirects(response, prefix):
    """The token is stripped out of the path before routing, so anything the router
    builds from that path -- above all its trailing-slash redirect -- comes back WITHOUT
    the token. `POST /t/<token>/mcp` was answering 307 to `/mcp/`, and a client that
    followed it arrived with no credential and was refused 401. The redirect handed the
    caller a broken address. Put the prefix back on the way out."""
    if not prefix or not (300 <= response.status_code < 400): return response
    loc = response.headers.get("location")
    if not loc: return response
    u = urlsplit(loc)
    if u.path.startswith(prefix): return response
    response.headers["location"] = urlunsplit((u.scheme, u.netloc, prefix + u.path, u.query, u.fragment))
    return response
_state = {"checked_at": 0, "changed": [], "last_build_started": 0, "proc": None, "last_result": None, "lock": threading.Lock()}


def _rebuild_state():
    p = _state["proc"]
    running = p is not None and p.poll() is None
    if p is not None and not running and _state["last_result"] is None:
        _state["last_result"] = {"exit": p.returncode, "meaning": {0: "published", 1: "REFUSED: a gate failed; previous model kept", 2: "another build was running"}.get(p.returncode, "error"),
                                 "log": paths.BUILD_LOG}
    return {"running": running, "last_started": _state["last_build_started"] or None, "last_result": _state["last_result"], "auto": AUTO_REBUILD, "cooldown_seconds": REBUILD_COOLDOWN}


def start_rebuild(force=False):
    with _state["lock"]:
        if _state["proc"] is not None and _state["proc"].poll() is None: return False
        os.makedirs(paths.CACHE_DIR, exist_ok=True)
        log = open(paths.BUILD_LOG, "a")
        _state["proc"] = subprocess.Popen([sys.executable, os.path.join(HERE, "build_read_model.py")] + (["--force"] if force else []), stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
        _state["last_build_started"] = time.time(); _state["last_result"] = None
        return True


def freshness(conn):
    now = time.time()
    if now - _state["checked_at"] > 5:
        recorded = [(r["path"], r["mtime_ns"], r["size"]) for r in conn.execute("SELECT path, mtime_ns, size FROM input")]
        _state["changed"] = snapshot.changed_since(recorded); _state["checked_at"] = now
    changed = _state["changed"]
    if changed and AUTO_REBUILD and now - _state["last_build_started"] > REBUILD_COOLDOWN:
        start_rebuild()
    return changed


def respond(fn, *a, **kw):
    try:
        conn = Q.connect()
    except Q.NotFound as e:
        return JSONResponse({"error": str(e), **e.extra}, status_code=503)
    try:
        changed = freshness(conn)
        try:
            res = fn(conn, *a, **kw)
        except Q.NotFound as e:
            return JSONResponse({"error": str(e), **e.extra, "snapshot": Q.snapshot_block(conn, changed, _rebuild_state())}, status_code=404)
        status, body = res if isinstance(res, tuple) else (200, res)
        body["snapshot"] = Q.snapshot_block(conn, changed, _rebuild_state())
        return JSONResponse(body, status_code=status)
    finally:
        conn.close()


@app.get("/")
def root():
    return {"service": "Football Archive, read-only", "routes": [r.path for r in app.routes if hasattr(r, "methods") and "GET" in r.methods],
            "premise": DESCRIPTION, "docs": "/docs", "mcp": "/mcp (streamable HTTP)", "access": access.why(),
            "mcp_allowed_hosts": ALLOWED_HOSTS}


@app.get("/snapshot")
def get_snapshot():
    return respond(lambda conn: {"inputs": conn.execute("SELECT COUNT(*) FROM input").fetchone()[0],
                                 "gates": [{"name": r["name"], "status": r["status"], "counts": json.loads(r["counts"]), "report": json.loads(r["report"])} for r in conn.execute("SELECT * FROM gate ORDER BY name")],
                                 "stores": [dict(r) for r in conn.execute("SELECT * FROM store ORDER BY name")],
                                 "club_strings_refused": [dict(r) for r in conn.execute("SELECT * FROM club_refusal ORDER BY n DESC LIMIT 200")],
                                 "predicate_families": json.loads(Q.meta(conn).get("predicate_families", "{}"))})


@app.post("/rebuild")
def rebuild(force: bool = False):
    started = start_rebuild(force=force)
    return {"started": started, "force": force, "state": _rebuild_state(), "note": "force publishes even if a gate fails; every response will then say so" if force else None}


@app.get("/status")
def sessions_status():
    """The four sessions' status file (Dropbox), with whether each finished report is on this disk yet."""
    import status as S
    return S.read()


@app.get("/people/{pid}")
def get_person(pid: str, one: bool = Query(False, description="ask for one value per fact; 409 with the candidates if any fact is contested")):
    return respond(Q.person, pid, one=one)


@app.get("/people/{pid}/bio")
def get_person_bio(pid: str,
                   facts: bool = Query(True, description="carry the underlying facts with their claims beside the prose")):
    """The page the website assembles: prose, panel, and the claims underneath.

    THE BIO IS DERIVED and is labelled so, like the display name and the date reading:
    it is assembled from claims at read time by dataset/src/bio_select.py and
    bio_write.py, and it is not itself a claim. Those two files are Parsing's; nothing
    here alters what a bio says or how it says it.

    THE PROSE IS NOT A WAY ROUND THE CONTESTED RULE. A sentence is one man's worth of
    English and cannot hold two birth dates, so the prose does whatever the generator
    does -- but `facts` carries every value with its claims, `contested` lists the
    disagreements the archive holds, and the panel lists a disputed field under its own
    `disagreements` without choosing. What the prose left out is still on the page."""
    def fn(conn):
        p = Q.person(conn, pid)                      # 404s for an id the archive does not hold
        if isinstance(p, tuple): p = p[1]            # person() may answer (status, body)
        try:
            b = bios.bio(pid)
        except bios.Unavailable as e:
            return 503, {"person": pid, "error": str(e), **e.extra,
                         "note": "the bio is derived at read time and refuses to run on a corpus it cannot fully read; the archive is untouched"}
        out = {"person": pid, "display_name": p["display_name"], "index_name": p["index_name"]}
        if b is None:
            out["bio"] = {"value": None, "basis": "absent", "derived": True,
                          "why": bios.why_no_bio(pid), "recipe": bios.status()["recipe"]}
            out["panel"] = None
        else:
            out["bio"] = b["prose"]; out["panel"] = b["panel"]; out["slots"] = b["slots"]
        out["generator"] = bios.status()
        if facts:
            out["facts"] = p["facts"]
            out["contested"] = p["contested"]
            out["seasons"] = p["seasons"]
        if b is not None:
            out["panel_quieter_than_the_claims"] = bios.panel_quieter_than_the_claims(
                b["panel"]["fields"], p["contested"])
            out["panel_noisier_than_the_claims"] = bios.panel_noisier_than_the_claims(
                b["panel"]["fields"], b["panel"]["disagreements"], p["facts"], p["contested"])
        return out
    return respond(fn)


@app.get("/people")
def search_people(name: str = Query(..., min_length=1), year: int | None = None, mode: str = Query("tokens", pattern="^(tokens|exact|prefix)$"), limit: int = 50):
    return respond(Q.search, name, year=year, mode=mode, limit=limit)


@app.get("/club-seasons/{league}/{year}/{club}")
def get_club_season(league: str, year: int, club: str):
    return respond(Q.club_season, league, year, club)


@app.get("/clubs/{cid}")
def get_club(cid: str):
    return respond(Q.club, cid)


@app.get("/clubs")
def search_clubs(name: str = Query(..., min_length=1), year: int | None = None):
    return respond(Q.clubs_search, name, year=year)


@app.get("/census/club-seasons")
def census_club_seasons(year: int):
    return respond(Q.census_club_seasons, year)


@app.get("/census/{family}")
def census(family: str, population: str = "people"):
    return respond(Q.census, family, population=population)


@app.get("/sources")
def list_sources():
    return respond(Q.sources)


@app.get("/sources/{sid:path}/records/{locator:path}")
def get_source_record(sid: str, locator: str):
    return respond(Q.source_record, sid, locator)


@app.get("/sources/{sid:path}")
def get_source(sid: str):
    return respond(Q.source, sid)


@app.get("/contested")
def list_contested(family: str | None = None, league: str | None = None, year: int | None = None, limit: int = 100, offset: int = 0):
    return respond(Q.contested, family=family, league=league, year=year, limit=limit, offset=offset)
