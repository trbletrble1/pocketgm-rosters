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

TWO KINDS OF ROSTER, AND THEY STAY APART. Eight clubs have a PFA roster page.
Wilson's Wildcats does not -- 1926aflpc.html is a hard 404 -- so its men are the
ones the BOXSCORES attest, and every claim says which kind of evidence it rests
on. A roster-page roster and a boxscore-derived roster are not the same object.

THE UNHELD MEN STAY LEADS. Ryan's ruling on player leads is unchanged. They carry
the full field set so that promoting one is a ruling, not a re-fetch.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
SP = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
      "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")
sys.path.insert(0, SP)
from ingest_pfa import parse_player, cells, text
from pfa2fetch import get, canonical
import ingest_boxscores as IB

SOURCE = {
    "source_id": "pro-football-archives",
    "name": "Pro Football Archives, 1926 American Football League",
    "acquisition": "fetched",
    "stated_by": "Pro Football Archives",
    "attribution": ["Pro Football Archives (profootballarchives.com)"],
    "_club_code": "PFA's own URL token, uppercased, because the club map ignores league",
    "_two_roster_kinds": "roster_page for eight clubs; boxscore_lineup for Wilson's "
                         "Wildcats, whose roster page is a hard 404",
}
SEASON = "1926"
LEAGUE = "AFL"
HARD_404 = {"1926aflpc.html": "Wilson's Wildcats"}


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
    c2p = json.load(open(SP + "pfa_code2pid.json"))
    R = json.load(open(SP + "afl26_rosters.json"))
    BOX = json.load(open(os.path.join(BASE, "build", "pfa-boxscores.json")))

    # Wilson's Wildcats: the boxscores are the ONLY roster evidence there is.
    #
    # RE-PARSED FROM THE PAGES, not read out of the boxscore CLAIMS. That store
    # writes a claim only for a man it could resolve and sends the rest to its
    # leads, and its lead record does not carry a club -- so reading claims alone
    # returns 10 Wildcats when the pages name 20, and the ten missing are exactly
    # the unheld men this ingest exists to capture. The narrower source was the
    # wrong one and it failed silently, in the direction of looking complete.
    box_men = collections.defaultdict(dict)
    for x in BOX["claims"]:
        if x["predicate"] == "pfa.game_lineup" and x["value"]["game"][1] == LEAGUE \
                and x["value"]["game"][2] == 1926:
            c2p.setdefault(x["value"]["pfa_code"], x["subject"][1])
    for fn in sorted(os.listdir(IB.CACHE)):
        m = IB.GAMEID.match(fn)
        if not m or m.group(1) != "1926" or m.group(2) != "afl":
            continue
        h = open(os.path.join(IB.CACHE, fn), encoding="utf-8", errors="replace").read()
        for row in IB.parse_lineups(IB.find_tables(h)):
            box_men[row["club_as_printed"]].setdefault(row["pfa_code"], {
                "pfa_code": row["pfa_code"],
                "path": f"players/{row['pfa_code'][0]}/{row['pfa_code']}.html",
                "name_as_printed": row["name_as_printed"],
                "position": row["position_as_printed"],
                "position_state": row["position_state"],
                "jersey": row["jersey"], "jersey_state": row["jersey_state"],
                "height": None, "height_state": "column_absent",
                "weight": None, "weight_state": "column_absent"})

    clubs, claims, leads = {}, [], []
    for url, r in sorted(R["clubs"].items()):
        code = club_code(url)
        h, st, ok = get(url)
        if not ok:
            raise AFL26Error(f"{url} was fetched before and is not now: {st}")
        clubs[code] = {"club_as_printed": r["club_as_printed"], "url": url,
                       "roster_evidence": "roster_page", "men": roster_rows(h)}
    for url, name in HARD_404.items():
        code = club_code(url)
        men = list(box_men.get(name, {}).values())
        if not men:
            raise AFL26Error(f"{name}: roster page 404 and no boxscore evidence either")
        clubs[code] = {"club_as_printed": name, "url": url,
                       "roster_evidence": "boxscore_lineup",
                       "_why": "1926aflpc.html is a hard 404; these are the men the "
                               "boxscores attest, and that is a weaker roster than a "
                               "roster page -- a man who never started is not here",
                       "men": men}

    seen = collections.Counter()
    for code, cl in sorted(clubs.items()):
        sr = f"{SOURCE['source_id']}#1926afl/{cl['url']}"
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
