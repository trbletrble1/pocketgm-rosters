"""The 1926 American Football League: nine clubs, one season, never enumerated.

WHY IT WAS MISSING. Stage one walked PFA by asking it for the club-seasons THE
ARCHIVE ALREADY HELD. The archive held no AFL 1926, so PFA was never asked, and a
league it has full rosters for stayed invisible. Every one of the 200 player pages
was already in the cache -- this was never an acquisition gap, only an enumeration
one. A loop driven by what you have cannot find what you lack.

CLUB CODES ARE PFA'S OWN URL TOKEN, UPPERCASED: 1926aflchi.html -> AFLCHI.
Not CHI. build_person_index keys the club map on (club, year) and IGNORES the
league, so an AFL 'CHI' in 1926 would collide with the NFL's Chicago Bears and one
of the two names would be silently overwritten by glob order. That is the same
defect gate_merged_clubs.M4 catches at PIT|1943, and there was no reason to create
a second instance of it while fixing a gap.

ALL NINE CLUBS HAVE A PFA ROSTER PAGE (corrected 2026-09-13). This said Wilson's
Wildcats had none -- "1926aflpc.html is a hard 404" -- and took its men from the
box scores. That URL was built from the archive's club code, AFLPC; PFA names the
page 1926aflwil.html, and it has been on disk since 4 September with a ROSTER table
of the same 20 men the box scores gave. Every club is now read from its own page.

NO SCRATCHPAD (2026-09-13). The club list, the PFA-code map and the page fetcher
were read from a session scratchpad that died with the session, so this store could
not be reproduced. The club pages are declared in declarations/club-names.json; the
code map is pfa_codes.holders() read from the published model with this store
excluded, plus PFA's own code on the officials record; pages are read from the PFA
caches on disk, never fetched.

THE UNHELD MEN STAY LEADS. Ryan's ruling on player leads is unchanged. They carry
the full field set so that promoting one is a ruling, not a re-fetch.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, sqlite3
from ingest_pfa import parse_player, cells, text
import pfa_codes

SRC = os.path.expanduser("~/Documents/pgm3-sources")
# The folders pfa2fetch.py read its cache from, in its order. Read-only: nothing is fetched.
PFA_CACHES = ("pfa", "pfa_probe", "pfa2")
DOUBLED = re.compile(r'^players/[a-z]/([a-z])/(.+)$')
PFA_TITLE = re.compile(r"<title>\s*(\d{4})\s+(.*?)\s+\(([A-Z0-9]+)\)", re.S | re.I)
CANONICAL = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']https?://[^/]+/([^"\']+)["\']', re.I)
STORE = "afl-1926"


def canonical(path):
    """pfa2fetch.canonical: PFA links some men twice, once with a doubled letter
    directory (/players/s/b/beso00200.html); the second form 404s."""
    path = path.lstrip('/')
    m = DOUBLED.match(path)
    return f'players/{m.group(1)}/{m.group(2)}' if m else path


def get(path):
    """-> (body, status, ok), from the caches on disk only."""
    key = canonical(path).replace('/', '_')
    for d in PFA_CACHES:
        p = os.path.join(SRC, d, key)
        if os.path.exists(p):
            return open(p, encoding='utf-8', errors='replace').read(), 'cache', True
    return None, 'not cached', False


def code_map():
    """PFA code -> archive person, from the published model, never from this store.

    pfa_codes.holders() is the one implementation. It does not read `pfa.role`, where
    the officials ingest keeps PFA's own code for a man who was both player and
    official -- Louie Kolls (koll00400, P_043033) is reached only that way, and the
    scratchpad map this replaces had him. A code reaching two people is refused."""
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    hold = pfa_codes.holders(conn, exclude_stores=(STORE,))
    held = {k: set(v) for k, v in hold.items()}
    for person, value in conn.execute("SELECT person, value FROM claim WHERE predicate='pfa.role' "
                                      "AND person IS NOT NULL AND store != ?", (STORE,)):
        code = (json.loads(value) or {}).get("pfa_code")
        if code: held.setdefault(code, set()).add(person)
    return {k: next(iter(v)) for k, v in held.items() if len(v) == 1}

SOURCE = {
    "source_id": "pro-football-archives",
    "name": "Pro Football Archives, 1926 American Football League",
    "acquisition": "fetched",
    "stated_by": "Pro Football Archives",
    "attribution": ["Pro Football Archives (profootballarchives.com)"],
    "_club_code": "PFA's own URL token, uppercased, because the club map ignores league",
    "_roster_kind": "roster_page for all nine clubs. Until 2026-09-13 Wilson's Wildcats was "
                    "read from the box scores as a 'hard 404'; the page is 1926aflwil.html, on "
                    "disk since 4 September, and names the same 20 men.",
}
SEASON = "1926"
LEAGUE = "AFL"


class AFL26Error(Exception):
    pass


def club_code(url):
    """1926aflchi.html -> AFLCHI. The SOURCE'S identifier, never the name."""
    m = re.match(r"^1926(afl[a-z]+)\.html$", url)
    if not m:
        raise AFL26Error(f"not a 1926 AFL club url: {url!r}")
    return m.group(1).upper()


def roster_rows(html):
    """The ROSTER table, found by its heading, and read by COLUMN NAME.

    Three states per cell, kept separable: a value, a cell that is present and
    empty, and a column the page does not have at all. A jersey number nobody
    printed is not a jersey number of zero."""
    for tbl in re.findall(r"<table.*?</table>", html, re.S):
        if "players/" not in tbl or "ROSTER" not in tbl:
            continue
        rows = [r for r in re.split(r"<tr", tbl)[1:]]
        hdr = None
        for r in rows:
            c = [x.strip() for x in cells(r)]
            if "Player" in c:
                hdr = c
                break
        if not hdr:
            raise AFL26Error("roster table with no Player column")
        out = []
        for r in rows:
            c = [x.strip() for x in cells(r)]
            if c == hdr or "Player" in c or len(c) < 2:
                continue
            href = re.search(r'href=["\']([^"\']*players/[^"\']+)["\']', r)
            if not href:
                continue
            path = canonical(href.group(1))
            rec = {"pfa_code": path.rsplit("/", 1)[-1][:-5], "path": path,
                   "name_as_printed": c[hdr.index("Player")] if "Player" in hdr else ""}
            for col, field in (("No", "jersey"), ("Pos", "position"),
                               ("Ht", "height"), ("Wt", "weight")):
                if col not in hdr:
                    rec[field], rec[field + "_state"] = None, "column_absent"
                    continue
                i = hdr.index(col)
                v = c[i] if i < len(c) else ""
                rec[field] = v or None
                rec[field + "_state"] = "stated" if v else "present_but_empty"
            out.append(rec)
        return out
    raise AFL26Error("no ROSTER table on the page")


def main(write=True):
    c2p = code_map()
    clubs, claims, leads = {}, [], []
    # THE CLUB PAGES ARE DECLARED (declarations/club-names.json), with the archive's club code
    # beside PFA's page: 1926aflwil.html is AFLPC. The locator is PFA's own -- the canonical URL
    # the page records for itself -- not a name built from a code.
    for e in json.load(open(os.path.join(BASE, "declarations", "club-names.json")))["pfa_club_pages"]:
        s = e["club_season"]
        if s[1] != LEAGUE or s[2] != SEASON: continue
        f = os.path.join(SRC, e["cached"])
        if not os.path.exists(f):
            raise AFL26Error(f"{e['cached']} is declared and not on disk")
        h = open(f, encoding="utf-8", errors="replace").read()
        t, c = PFA_TITLE.search(h), CANONICAL.search(h)
        if not t or not c or t.group(1) != SEASON:
            raise AFL26Error(f"{e['cached']}: no title, no canonical URL, or another season")
        clubs[s[3]] = {"club_as_printed": " ".join(t.group(2).split()), "url": c.group(1),
                       "cached": e["cached"], "roster_evidence": "roster_page", "men": roster_rows(h)}
    if len(clubs) != 9:
        raise AFL26Error(f"the 1926 AFL had nine clubs; {len(clubs)} pages are declared")

    seen = collections.Counter()
    for code, cl in sorted(clubs.items()):
        sr = f"{SOURCE['source_id']}#{cl['url']}"
        for m in cl["men"]:
            seen[m["pfa_code"]] += 1
            pid = c2p.get(m["pfa_code"])
            val = {k: m.get(k) for k in
                   ("name_as_printed", "pfa_code", "jersey", "jersey_state",
                    "position", "position_state", "height", "height_state",
                    "weight", "weight_state")}
            val.update({"club_as_printed": cl["club_as_printed"],
                        "club_code": code, "league": LEAGUE, "year": 1926,
                        "roster_evidence": cl["roster_evidence"],
                        "_resolved_on": "pfa_code, never the name"})
            if pid:
                claims.append({
                    "source_record": sr, "source_id": SOURCE["source_id"],
                    "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
                    # ["stint", PERSON, club, season] -- the person in s[1]. The first
                    # version put the LEAGUE there and carried the person as a sidecar
                    # field the builder never reads, so every one of these 102 claims
                    # was skipped silently and the rebuild produced 0 AFL|1926 seasons.
                    # The league comes from the FILENAME (afl-1926 -> AFL), which is
                    # why it has no place in the subject. Caught by Parsing, not by me:
                    # my own simulation replicated the key derivation and never the
                    # person-resolution step that precedes it.
                    "subject": ["stint", pid, code, SEASON],
                    "predicate": "pfa.roster_membership", "value": val,
                    "kind": "observed", "observed_at": "fetched-2026-09",
                    "person": pid})
                claims.append({
                    "source_record": sr, "source_id": SOURCE["source_id"],
                    "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
                    "subject": ["person", pid], "predicate": "pfa.afl1926_club",
                    "value": val, "kind": "observed", "observed_at": "fetched-2026-09"})
            else:
                p, pst, pok = get(m["path"])
                fields = parse_player(p) if pok else {}
                leads.append({
                    "lead_id": f"lead-afl1926-{len(leads)+1:03d}",
                    "category": "player_lead_unpromoted",
                    "pfa_code": m["pfa_code"], "name_as_printed": m["name_as_printed"],
                    "places_on": {"league": LEAGUE, "year": 1926, "club": code,
                                  "club_as_printed": cl["club_as_printed"]},
                    "roster_evidence": cl["roster_evidence"],
                    "source_id": SOURCE["source_id"], "source_record": sr,
                    "player_page": m["path"], "player_page_status": pst,
                    "IS_NOT_A_PERSON": True,
                    "why": "no archive person resolves to this PFA code. Ryan's ruling "
                           "on player leads stands: parked, not promoted.",
                    "roster_line": val, "fields": fields})
    out = {"source": SOURCE, "clubs": {k: {kk: vv for kk, vv in v.items() if kk != "men"}
                                       for k, v in clubs.items()},
           "claims": claims, "leads": leads,
           "counts": {"clubs": len(clubs),
                      "men_attested": len(seen),
                      "men_on_more_than_one_club": sum(1 for v in seen.values() if v > 1),
                      "held_people": len({c["person"] for c in claims if "person" in c}),
                      "leads": len(leads),
                      "roster_page_clubs": sum(1 for v in clubs.values()
                                               if v["roster_evidence"] == "roster_page"),
                      "boxscore_only_clubs": sum(1 for v in clubs.values()
                                                 if v["roster_evidence"] == "boxscore_lineup")}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, os.path.join(BASE, "build", "afl-1926.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"clubs {c['clubs']} ({c['roster_page_clubs']} roster-page, "
          f"{c['boxscore_only_clubs']} boxscore-only)")
    print(f"men attested {c['men_attested']}  on >1 club {c['men_on_more_than_one_club']}")
    print(f"held people given an AFL|1926 season: {c['held_people']}")
    print(f"leads written (parked, not promoted) : {c['leads']}")
    print(f"claims {len(o['claims'])}")
