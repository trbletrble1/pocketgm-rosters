"""The archive as MCP tools, so Claude can read it directly. Ruled 2026-09-07.

Runs over stdio and calls queries.py in-process against the published read model --
the same functions the HTTP routes call, so the contract is identical: every value
with its claims, `contested` as a flag, nothing chosen, `snapshot` on every result.

Register with Claude Code:
    claude mcp add football-archive -- ~/.venvs/football-archive-service/bin/python /Users/ryannecci/Documents/pocketgm-rosters-clone/dataset/service/mcp_server.py
Claude Desktop (claude_desktop_config.json):
    {"mcpServers": {"football-archive": {"command": "/Users/ryannecci/.venvs/football-archive-service/bin/python",
                                          "args": ["/Users/ryannecci/Documents/pocketgm-rosters-clone/dataset/service/mcp_server.py"]}}}
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mcp.server.mcpserver import MCPServer
import queries as Q, status as S, bios

INSTRUCTIONS = """A read-only archive of professional football: ~5 million claims from documents, indexed by person, club-season, predicate family and source record.
Every value comes with the claims that hold it and each claim names its source record. Where sources disagree, `contested` is true and EVERY value is returned: the archive holds both and does not choose. Do not present one of them as the answer; say that the sources disagree and cite them.
A name is a claim: search returns candidates, never one person. `display_name` is a derived value (design 9.3) and says so. Dates are compared on the calendar day as a derived reading; the printed strings are never rewritten.
Every result carries `snapshot`: what the read model was built from, whether inputs have changed since, and the gate status. If `snapshot.gates` is FAIL, say so when it matters."""

server = MCPServer("football-archive", instructions=INSTRUCTIONS, version="0.1")


def _run(fn, *a, **kw):
    try:
        conn = Q.connect()
    except Q.NotFound as e:
        return {"error": str(e), **e.extra}
    try:
        try:
            res = fn(conn, *a, **kw)
        except Q.NotFound as e:
            return {"error": str(e), **e.extra, "snapshot": Q.snapshot_block(conn)}
        status, body = res if isinstance(res, tuple) else (200, res)
        body["snapshot"] = Q.snapshot_block(conn)
        if status != 200: body["status"] = status
        return body
    finally:
        conn.close()


@server.tool()
def get_person(person_id: str, one: bool = False) -> dict:
    """Everything held about a person by id (P_000001): names with their eras, facts by predicate family (each value with its claims and source records; `contested` where sources disagree), stints by club-season with the four-state games reading, statistics, denotations, merges. `one=True` asks for one value per fact and returns status 409 with the candidates if any fact is contested."""
    return _run(Q.person, person_id, one=one)


@server.tool()
def get_bio(person_id: str, facts: bool = True) -> dict:
    """A man's biography and vitals panel, assembled from claims at read time. `bio` is the prose and `panel` is identity as structured data -- birth, birthplace, hometown, college, high school, height, weight, draft, position -- each value naming its source, with any field the sources disagree on listed under `panel.disagreements` and NOT resolved. BOTH ARE DERIVED and say so; neither is a claim. The prose is one man's worth of English and cannot hold two birth dates, so where a fact is contested the prose says whatever the generator says -- `facts` and `contested` carry every value with its claims, so what the prose left out is still here. Say the sources disagree; do not repeat the sentence as if it settled it."""
    def fn(conn):
        p = Q.person(conn, person_id)
        if isinstance(p, tuple): p = p[1]
        try:
            b = bios.bio(person_id)
        except bios.Unavailable as e:
            return 503, {"person": person_id, "error": str(e), **e.extra}
        out = {"person": person_id, "display_name": p["display_name"]}
        if b is None:
            out["bio"] = {"value": None, "basis": "absent", "why": bios.why_no_bio(person_id)}
            out["panel"] = None
        else:
            out["bio"] = b["prose"]; out["panel"] = b["panel"]
        out["generator"] = bios.status()
        if facts:
            out["facts"] = p["facts"]; out["contested"] = p["contested"]
        if b is not None:
            out["panel_quieter_than_the_claims"] = bios.panel_quieter_than_the_claims(
                b["panel"]["fields"], p["contested"])
            out["panel_noisier_than_the_claims"] = bios.panel_noisier_than_the_claims(
                b["panel"]["fields"], b["panel"]["disagreements"], p["facts"], p["contested"])
        return out
    return _run(fn)


@server.tool()
def search_people(name: str, year: int | None = None, mode: str = "tokens", limit: int = 50) -> dict:
    """Candidates for a name -- never one person. Accent-folded match over every name claim; `year` narrows to careers spanning it; mode tokens|exact|prefix. Each candidate carries what separates him: birth dates as held, colleges, first/last season, club-seasons, roles."""
    return _run(Q.search, name, year=year, mode=mode, limit=limit)


@server.tool()
def get_club_season(league: str, year: int, club: str) -> dict:
    """The roster of a club-season (league NFL, year 1950, club BA1 or 'Baltimore Colts'): each man with the stint claims that place him there and a four-state games reading; staff from the coaching stores. 404-style error if the club table holds no such club that year; an empty roster on a held club-season is a result with basis 'unknown'."""
    return _run(Q.club_season, league, year, club)


@server.tool()
def get_club(club_id: str) -> dict:
    """A club as the club table holds it: code segments, names by year, leagues, every source string, lineage links WITH their evidence, and every unresolved lineage candidate or split touching it (listed, not joined)."""
    return _run(Q.club, club_id)


@server.tool()
def search_clubs(name: str, year: int | None = None) -> dict:
    """Club names matching a string, with the years each name applied and the club id."""
    return _run(Q.clubs_search, name, year=year)


@server.tool()
def census(family: str, population: str = "people") -> dict:
    """How many people have a value for a predicate family (birth_date, death_date, college, ...), as a basis distribution over a stated population: observed / contested / absent / unknown, summing to n. population: people | people:league=NFL | people:year=1926 | people:league=NFL,year=1950."""
    return _run(Q.census, family, population=population)


@server.tool()
def census_club_seasons(year: int) -> dict:
    """How many club-seasons a year has -- several honest answers (roster club strings, distinct clubs after the table, coaching keys, clubs the table holds), not added."""
    return _run(Q.census_club_seasons, year)


@server.tool()
def list_sources() -> dict:
    """Every source in the archive with claim counts and whether it has a declaration."""
    return _run(Q.sources)


@server.tool()
def get_source(source_id: str) -> dict:
    """A source's declaration (acquisition, stated_by, lineage, URL patterns, known traps), the stores it feeds and the predicates it carries."""
    return _run(Q.source, source_id)


@server.tool()
def get_source_record(source_id: str, locator: str) -> dict:
    """The document: every claim one source record produced, and its denotations. E.g. source_id 'statscrew', locator 'roster/BA1-1950#Sisto Averno'."""
    return _run(Q.source_record, source_id, locator)


@server.tool()
def list_contested(family: str | None = None, league: str | None = None, year: int | None = None, limit: int = 100, offset: int = 0) -> dict:
    """The disagreement worklist: people whose sources give different values for a family, with every value and its claims."""
    return _run(Q.contested, family=family, league=league, year=year, limit=limit, offset=offset)


@server.tool()
def snapshot() -> dict:
    """What the read model is serving: snapshot id, build time, counts, the four gates with their full reports, stores, and which inputs have changed since the build."""
    def fn(conn):
        return {"gates": [{"name": r["name"], "status": r["status"], "counts": json.loads(r["counts"]), "report": json.loads(r["report"])} for r in conn.execute("SELECT * FROM gate ORDER BY name")],
                "stores": conn.execute("SELECT COUNT(*) FROM store").fetchone()[0]}
    return _run(fn)


@server.tool()
def sessions_status() -> dict:
    """The four Claude sessions' status file from Dropbox: who is working on what, done or not, the report path, and whether that report has synced to this machine yet."""
    return S.read()


if __name__ == "__main__":
    server.run("stdio")
