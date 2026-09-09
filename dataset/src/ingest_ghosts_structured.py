"""The four structured Ghosts pages that are NOT rosters.

RYAN'S RULING, 2026-09-08: an honour is not club membership and needs its own
predicate. An all-pro selection asserts that a man was named to an honour team for a
season -- by a named selector -- not that he played for the club the table is filed
under. Same reasoning as programme.team_photograph.

THE GILBERTON PAGE IS ESTABLISHED FROM THE PAGE, NOT ASSUMED. Its two tables are
headed `GILBERTON LINEUP TODAY` and `YELLOW JACKETS' LINEUP FOR TODAY` -- printed
BEFORE the game, in a clipping reproduced on the page. That is the probable-line-up
assertion exactly, so it goes there and not to started_a_game.

  python3 src/ingest_ghosts_structured.py [--dry]
"""
import os, re, sys, json, html, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
M = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron")
MAN = json.load(open(os.path.join(M, "manifest.json")))

SOURCE = {
    "source_id": "ghostsofthegridiron",
    "name": "Ghosts of the Gridiron (John J. Fenton) -- structured non-roster tables",
    "acquisition": "preserved",
    "stated_by": "John J. Fenton",
    "attribution": ["Ghosts of the Gridiron, John J. Fenton, 2004-2008"],
    "rights": "copyrighted personal website by a named living author. FACTS ingested and "
              "cited; prose not reproduced; images held pending permission.",
}

PREDICATE_DEFINITIONS = {
    "honour_team_selection": {
        "definition": "named to an honour team for a season by a named selector -- an "
                      "all-pro or all-league selection.",
        "is_not_membership": "it does NOT assert that the man played for the club the "
                             "table is filed under, or for any club. Two selectors may "
                             "name him and a third may not; the honour is the selector's "
                             "act, not the club's.",
        "why_not_roster_membership": "roster_membership.* means a club or a source stated "
                                     "a man's standing on a squad. Filing an award there "
                                     "would make an honour indistinguishable from a "
                                     "season, and no later reader could separate them.",
        "carries": "year, position as printed, the honour (1st/2nd/3rd team), and the "
                   "SELECTOR -- which is the source of the honour and is not the archive's "
                   "to drop.",
        "ruled_by": "Ryan, 2026-09-08. Archive proposes the definition.",
    },
}

PAGES = {
 "Yellowjackets_all-pros.htm": ("honour", "Frankford Yellow Jackets"),
 "Maroons_all-pros.htm":       ("honour", "Pottsville Maroons"),
 "Quakers.htm":                ("honour", "Philadelphia Quakers"),
 "Yellowjackets_Gilberton_1923.htm": ("lineup", None),
}


def snap(page):
    for v in MAN["files"].values():
        if not v.get("absent") and v.get("path", "").endswith("/" + page): return v
    raise SystemExit(f"{page}: not in the preservation manifest")


def rows_of(t, split_br=False):
    out = []
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", tb):
            cells = []
            for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr):
                if split_br:
                    z = re.sub(r"(?i)<br\s*/?>", "\n", z)
                    v = html.unescape(re.sub(r"<[^>]+>", "", z)).replace("\xa0", " ")
                    cells.append([x.strip() for x in v.split("\n") if x.strip()])
                else:
                    v = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", z)))
                    cells.append(v.replace("\xa0", " ").strip())
            if any(cells): rows.append(cells)
        if rows: out.append(rows)
    return out


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def main(write=True):
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    IDX.pop("_clubs", None)
    byname = collections.defaultdict(list)
    for pid, p in IDX.items():
        if isinstance(p, dict) and p.get("name"): byname[norm(p["name"])].append(pid)
    # THE CLUB-SEASON COHORT, which is the strong join. The clipping prints SURNAMES
    # ("Little, Capt.", "Scott", "Spagna"), so an exact full-name match across 43,550
    # people finds almost nobody -- correctly, because a surname alone is worth nothing
    # at that scale. Scoped to the men the archive holds on Frankford's 1923 independent
    # season, a unique surname IS evidence, and it is the join the archive already uses.
    FYJ23 = {}
    for pid, p in IDX.items():
        if not isinstance(p, dict) or not p.get("name"): continue
        if any(k.startswith("IND|1923|DOC:FYJ-IND") for k in (p.get("seasons") or {})):
            FYJ23.setdefault(norm(p["name"]).split()[-1], []).append(pid)

    claims, leads, srecs = [], [], {}
    n = collections.Counter()

    def cite(sr, snapv, extra=None):
        c = {"source_record": sr, "source_id": SOURCE["source_id"],
             "stated_by": SOURCE["stated_by"], "attribution": SOURCE["attribution"],
             "kind": "observed", "observed_at": "preserved-2026-09",
             "underlying_source": "unstated",
             "finding_aid": {"who": "John J. Fenton, Ghosts of the Gridiron",
                             "snapshot": snapv["wayback_url"]}}
        if extra: c.update(extra)
        return c

    # ---------------- the three honour tables
    for page, (kindp, club) in PAGES.items():
        if kindp != "honour": continue
        v = snap(page); sr = f"{SOURCE['source_id']}#{page}@{v['timestamp']}"
        srecs[sr] = {"source_id": SOURCE["source_id"], "locator": v["wayback_url"],
                     "description": f"{club} all-pro / all-league selections",
                     "sha256": v["sha256"], "captured": v["timestamp"]}
        t = open(os.path.join(M, v["path"]), errors="replace").read()
        for rows in rows_of(t):
            hdr = next((i for i, r in enumerate(rows[:4])
                        if len(r) >= 4 and r[0].lower() == "year"), None)
            if hdr is None: continue
            for r in rows[hdr + 1:]:
                if len(r) < 5 or not r[0].strip().isdigit(): continue
                year, name, pos, honour, selector = r[0], r[1], r[2], r[3], r[4]
                val = {"name_as_printed": name, "year": int(year),
                       "position_as_printed": pos, "honour_as_printed": honour,
                       "selector_as_printed": re.sub(r"\s*\d+$", "", selector).strip(),
                       "filed_under_club": club,
                       "_filed_under_is_not_a_claim":
                           "Fenton files this table under the club. The HONOUR is the "
                           "selector's act and this claim does not assert club membership.",
                       "_definition": PREDICATE_DEFINITIONS["honour_team_selection"]["definition"],
                       "_underlying_source_note":
                           "Fenton names the SELECTOR (a newspaper or magazine) but not "
                           "the issue; the selector is recorded as printed and the "
                           "underlying publication reference is unstated."}
                pid = byname.get(norm(name), [])
                if len(pid) == 1:
                    claims.append(cite(sr, v, {"subject": ["person", pid[0]],
                        "predicate": "honour_team_selection", "value": val,
                        "person": pid[0],
                        "_join_evidence": "exact full name, unique in the archive"}))
                    n["honour_claims"] += 1
                else:
                    leads.append({"lead_id": f"lead-ghosts-hon-{len(leads)+1:03d}",
                                  "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                                  "name_as_printed": name, "honour_line": val,
                                  "evidence_kind": "honour_selection",
                                  "places_on": {"club_as_printed": club, "year": int(year),
                                                "club_season": None,
                                                "_why_no_club_season":
                                                  "an honour is not club membership"},
                                  "source_id": SOURCE["source_id"], "source_record": sr,
                                  "why": ("ambiguous: more than one held person carries "
                                          "this name" if len(pid) > 1 else
                                          "no held person carries this name")})
                    n["honour_leads"] += 1

    # ---------------- the printed line-up
    page = "Yellowjackets_Gilberton_1923.htm"
    v = snap(page); sr = f"{SOURCE['source_id']}#{page}@{v['timestamp']}"
    srecs[sr] = {"source_id": SOURCE["source_id"], "locator": v["wayback_url"],
                 "description": "Yellow Jackets v Gilberton, 14 October 1923 -- both "
                                "line-ups as printed before the game",
                 "sha256": v["sha256"], "captured": v["timestamp"]}
    t = open(os.path.join(M, v["path"]), errors="replace").read()
    GAME = ["game", "IND", "1923", "1923-10-14-frankford-v-gilberton"]
    for rows in rows_of(t, split_br=True):
        for r in rows:
            lens = [len(x) for x in r]
            if not lens or max(lens) < 5: continue
            nums, names = r[0], r[1]
            pos = r[2] if len(r) > 2 else []
            cols = r[3] if len(r) > 3 else []
            wts = r[4] if len(r) > 4 else []
            aligned = len(pos) == len(names)
            club = "Frankford Yellow Jackets" if aligned else "Gilberton"
            for i, nm in enumerate(names):
                val = {"name_as_printed": nm,
                       "jersey_as_printed": nums[i] if i < len(nums) else None,
                       "club_as_printed": club, "game": GAME,
                       "printed_before_the_game": True,
                       "_established_from_the_page":
                           "the table is headed 'LINEUP TODAY' / 'LINEUP FOR TODAY' in a "
                           "clipping printed the day of the game -- an expectation stated "
                           "in advance, not a record of who played",
                       "_underlying_source":
                           "Fenton names the intermediate source -- A Documentary "
                           "Scrapbook of Football in Frankford -- and states that the "
                           "ORIGINAL PUBLICATION IS NOT IDENTIFIED. That is the author "
                           "saying he does not know, which is stronger than unstated."}
                if aligned:
                    val["position_as_printed"] = pos[i] if i < len(pos) else None
                    val["college_as_printed"] = cols[i] if i < len(cols) else None
                    val["weight_as_printed"] = wts[i] if i < len(wts) else None
                else:
                    val["position_as_printed"] = None
                    val["_position_not_assignable"] = (
                        f"the table prints {len(names)} names and {len(pos)} positions. "
                        "Assigning them in order would give most of these men another "
                        "man's position -- the column-slip defect. Names and numbers only.")
                key = norm(nm).split()[-1] if norm(nm) else ""
                pid = byname.get(norm(nm), [])
                scoped = FYJ23.get(key, []) if aligned else []
                if not pid and len(scoped) == 1:
                    pid = scoped
                    val["_join_evidence"] = ("surname unique among the men the archive "
                                             "holds on Frankford's 1923 season")
                if len(pid) == 1 and aligned:
                    claims.append(cite(sr, v, {"subject": ["person", pid[0]],
                        "predicate": "programme.probable_lineup", "value": val,
                        "person": pid[0],
                        "_predicate_note":
                            "the same assertion as a programme's probable line-up -- "
                            "printed before kickoff -- from a NEWSPAPER clipping. The "
                            "predicate's name is source-flavoured and its definition is "
                            "not; flagged rather than duplicated under a second name.",
                        "_join_evidence": val.get("_join_evidence",
                                                  "exact full name, unique in the archive")}))
                    n["lineup_claims"] += 1
                else:
                    leads.append({"lead_id": f"lead-ghosts-lu-{len(leads)+1:03d}",
                                  "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                                  "name_as_printed": nm, "lineup_line": val,
                                  "evidence_kind": "printed_lineup_before_kickoff",
                                  "places_on": {"club_as_printed": club, "year": 1923,
                                                "club_season": None},
                                  "source_id": SOURCE["source_id"], "source_record": sr,
                                  "why": "not resolved to a held person by exact name"})
                    n["lineup_leads"] += 1

    out = {"source": SOURCE, "source_records": srecs,
           "predicate_definitions": PREDICATE_DEFINITIONS,
           "claims": claims, "leads": leads,
           "counts": {"claims": len(claims), "leads": len(leads), **dict(n),
                      "held_people_touched": len({c["person"] for c in claims if "person" in c})}}
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "ghosts-structured.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"claims {c['claims']}  leads {c['leads']}  people touched {c['held_people_touched']}")
    for k in ("honour_claims", "honour_leads", "lineup_claims", "lineup_leads"):
        print(f"   {k:16s} {c.get(k,0)}")
