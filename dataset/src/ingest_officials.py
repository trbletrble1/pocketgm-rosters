"""Ingest PFA officials. Ryan's ruling: officials are people.

THE LINE IS ON-FIELD GAME PARTICIPANTS. Officials are on the field. This is not a
precedent for trainers, equipment managers, owners or broadcasters, and no later
ingest should cite it as one.

ROLE IS QUERYABLE. An official is not a player. A query for players must not
return referees, and a bio must know that an official's career is games WORKED.
Players, coaches and officials are separable by `roles` on the person and by the
predicate on the claim.

ONE MAN, TWO ROLES. 22 officials share a PFA code with a coach -- Fay Abbott's
page is one record reachable at two paths. A man who officiated and coached is one
person with two roles, never two people, and the code is what proves it.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
CACHE = "/Users/ryannecci/Documents/pgm3-sources/pfa2"
# THE INPUTS WERE IN A SESSION SCRATCHPAD UNDER /tmp AND THE SESSION IS GONE. The
# archive's own rule -- results never live in a literal /tmp path -- was broken here, and
# it bit: this ingest could not run at all. The two match files were preserved by hand in
# session-scratch-from-laptop-2026-09-07, and that copy is what is read now. Recorded
# rather than quietly repointed: an input that lives outside build/ is still a hazard.
_PRESERVED = os.path.expanduser("~/Documents/session-scratch-from-laptop-2026-09-07/"
                                "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")
SP = _PRESERVED
DECL = json.load(open(os.path.join(BASE, "declarations", "pfa.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]

from ingest_pfa import parse_player, text, canonical_url

TITLE = re.compile(r"<title>(.*?)\s+(?:NFL|AFL|AAFC|APFA)?\s*Officiating Record", re.S)
H1 = re.compile(r"<h1>(.*?)</h1>", re.S)


def official_name(html):
    """PFA's officials template appends an 's' to the name in the <h1> -- a
    possessive with the apostrophe lost. 'Fay Abbott' is rendered 'Fay Abbotts' on
    1,326 of 1,328 pages, and taking the h1 would have created 1,102 people under
    names that do not exist. The <title> carries the clean form.

    Two pages need the fallback: one has a mojibake apostrophe in the title, one
    has an empty h1."""
    t = TITLE.search(html)
    name = text(t.group(1)) if t else ""
    if name and "\ufffd" not in name and "?" not in name:
        return name, "title"
    h = H1.search(html)
    hn = text(h.group(1)) if h else ""
    if hn.endswith("s"):
        return hn[:-1], "h1_minus_template_s"
    return name or hn, "fallback"
from promote_coaches import build_index, screen, new_person_id

CODE = re.compile(r"([a-z]{2,6}\d{4,6})")
YEAR = re.compile(r"^\d{4}$")


class OfficialError(Exception):
    pass


def parse_officiating(html):
    """Year | League | Assignment. The last row of each table is a CAREER TOTAL --
    '2 Years' with empty league and assignment -- and is not a season. 1,328 of
    them exist, one per page, and counting them as seasons would inflate every
    official's career by one."""
    out, total = [], None
    for t in re.findall(r"<table.*?</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
        if not rows:
            continue
        hd = [text(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S)]
        if hd[:3] != ["Year", "League", "Assignment"]:
            continue
        for r in rows[1:]:
            c = [text(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(c) < 3:
                continue
            if not YEAR.match(c[0]):
                total = c[0]          # "2 Years" -- the career summary
                continue
            out.append({"year": int(c[0]), "league_as_printed": c[1],
                        # KEPT EXACTLY AS PRINTED. The crew vocabulary has changed
                        # over a century: 'Head Linesman' became 'Down Judge', and
                        # 'Umpire; Head Linesman' is one season in two roles.
                        "assignment_as_printed": c[2],
                        "_assignment_is_verbatim": True})
    return out, total


def other_role_links(html):
    """A page linking /players/ or /coaches/ is the SOURCE saying this man had
    another career. That is evidence of one man with two roles, not two men."""
    out = {}
    for kind in ("players", "coaches"):
        m = re.search(rf'href="/{kind}/([a-z0-9/]*?)\.html"', html)
        if m:
            c = CODE.search(m.group(1))
            if c:
                out[kind] = c.group(1)
    return out


def prior_ids_from_the_model():
    """The person id THIS INGEST ALREADY MINTED for each PFA code, recovered from the
    published read model.

    WHY THIS IS NOT A DECIDER READING ITS OWN OUTPUT. It very nearly is, and the
    distinction is the whole of it. `screen()` is the decider: it asks "is this man
    already in the archive under another name?" and it must never see this ingest's own
    people, or it refuses to create George Young on the grounds that George Young exists
    -- the George Young it created last time. That is what happened: 1,254 refusals, 0
    created, every candidate the ingest's own prior self.

    Recovering an id for a code is not that question. It is the same question
    promote_players.py answers when it says a man already promoted must get HIS id back
    and not a fresh one: the PFA code is a SOURCE-NATIVE key, and the same key is the same
    man. Without it the ingest is not idempotent, and an id that moves is worse than an id
    recovered.

    Keyed on the code, never on the name."""
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    except Exception:
        return {}
    out = {}
    for pid, sr in conn.execute("select person, source_record from claim "
                                "where store='pfa-officials' and person is not null"):
        m = CODE.search(str(sr))
        if m:
            out.setdefault(m.group(1), pid)
    return out


def person_map():
    cmap = {}
    for pid, v in json.load(open(SP + "pfa_match.json"))["matched"].items():
        m = CODE.search(v[0])
        if m:
            cmap[m.group(1)] = pid
    for u, pid in json.load(open(SP + "pfa2_match.json"))["matched"].items():
        m = CODE.search(u)
        if m:
            cmap.setdefault(m.group(1), pid)
    p = os.path.join(BASE, "build", "coach-promotions.json")
    if os.path.exists(p):
        for x in json.load(open(p))["promotions"]:
            if x.get("pfa_code"):
                cmap.setdefault(x["pfa_code"], x["person_id"])
    # LAST, so it never overrides a structural match: the ids this ingest minted before.
    for code, pid in prior_ids_from_the_model().items():
        cmap.setdefault(code, pid)
    return cmap


_PRIOR = {}


def main(write=True):
    import write_bios as W
    IDX = W.IDX
    by_name, by_surname = build_index(IDX)
    global _PRIOR
    _PRIOR = prior_ids_from_the_model()
    cmap = person_map()
    coach_codes = set()
    p = os.path.join(BASE, "build", "pfa-coaches.json")
    if os.path.exists(p):
        C = json.load(open(p))
        for c in C["claims"]:
            m = CODE.search(c["source_record"])
            if m:
                coach_codes.add(m.group(1))
        for l in C["leads"]:
            coach_codes.add(l["pfa_code"])

    claims, created, refusals, dual = [], [], [], []
    n = collections.Counter(); vocab = collections.Counter()
    resolved = 0
    for fn in sorted(os.listdir(CACHE)):
        if not fn.startswith("officials_"):
            continue
        code = fn[len("officials_"):-len(".html")]
        h = open(os.path.join(CACHE, fn), encoding="utf-8", errors="replace").read()
        r = parse_player(h)
        seasons, total = parse_officiating(h)
        others = other_role_links(h)
        name, name_route = official_name(h)
        sr = f"{SRC_ID}#officials/{code}.html"

        roles = ["official"]
        if others.get("coaches") == code or code in coach_codes:
            roles.append("coach")
        if others.get("players") == code:
            roles.append("player")
        if len(roles) > 1:
            dual.append({"pfa_code": code, "name": name, "roles": roles,
                         "_one_man_two_roles": "the SAME PFA code is reachable at more "
                                               "than one path; it is one record",
                         "linked": others})

        pid = cmap.get(code)
        how = None
        if pid:
            resolved += 1
            how = {"route": "pfa_code", "code": code,
                   "_never_by_name": "identity resolved structurally"}
            if code in _PRIOR:
                how["_recovered"] = ("this ingest minted this id for this code on an earlier "
                                     "run; recovering it keeps the man's id stable and is "
                                     "why the ingest is idempotent")
        else:
            ok, ev = screen(name or "", IDX, by_name, by_surname)
            if not ok:
                refusals.append({"pfa_code": code, "name_as_printed": name,
                                 "refused_because": ev.get("refused_because"),
                                 "evidence": ev})
                n["refused"] += 1
                continue
            pid = new_person_id(IDX)
            created.append({"person_id": pid, "name": name, "name_route": name_route,
                            "pfa_code": code,
                            "entered_by": "officials_ingest",
                            "roles": roles,
                            "_ruled": "officials are people; the line is ON-FIELD GAME "
                                      "PARTICIPANTS and this is not precedent for "
                                      "trainers, owners or broadcasters",
                            "identified_by": {"pfa_code": code, "source_record": sr},
                            "no_archive_match_evidence": ev,
                            "officiating_seasons": seasons,
                            "reversible": {"undo": "delete this person_id; the officials "
                                                   "page is the only source",
                                           "source_record": sr}})
            how = {"route": "created", "code": code}
        for s in seasons:
            vocab[s["assignment_as_printed"]] += 1
            claims.append({"source_record": sr, "source_id": SRC_ID,
                           "stated_by": DECL["stated_by"], "attribution": [DECL["name"]],
                           # A PERSON_SEASON, NOT A PERSON. Ruled 2026-09-09 alongside the
                           # coaching subjects -- but NOT a stint, because an official has
                           # no club. PFA assigns him to a LEAGUE and a season ("1939 NFL,
                           # Field Judge") and never to a team, so a stint subject would
                           # have to invent a club. person_season gives the model a year
                           # and a league, which is exactly what the source states.
                           "subject": ["person_season", pid,
                                       f"{s.get('league_as_printed') or 'NFL'}-{s['year']}"],
                           "predicate": "pfa.officiating_season",
                           "value": s, "kind": "observed", "observed_at": "fetched-2026-09",
                           "_role": "official"})
            n["officiating_season"] += 1
        if total:
            claims.append({"source_record": sr, "source_id": SRC_ID,
                           "stated_by": DECL["stated_by"], "attribution": [DECL["name"]],
                           "subject": ["person", pid], "predicate": "pfa.officiating_career",
                           "value": {"as_printed": total,
                                     "_a_summary_not_a_season": True},
                           "kind": "observed", "observed_at": "fetched-2026-09"})
            n["officiating_career"] += 1
        claims.append({"source_record": sr, "source_id": SRC_ID,
                       "stated_by": DECL["stated_by"], "attribution": [DECL["name"]],
                       "subject": ["person", pid], "predicate": "pfa.role",
                       "value": {"roles": roles, "pfa_code": code},
                       "kind": "observed", "observed_at": "fetched-2026-09"})
        n["role"] += 1
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           # THE SOURCE RECORD TABLE. The ingest never emitted one, so every claim named a
           # record its own store did not hold and RS-G3 counted the store among those with
           # no table at all. The locator is the page each claim was read from -- already
           # computed above as `sr` -- so this states what was always true.
           "source_records": {c["source_record"]: {
                "source_id": SRC_ID,
                "locator": c["source_record"].split("#", 1)[1]}
                for c in claims},
           "claims": claims, "created": created, "refusals": refusals,
           "dual_role": dual,
           "counts": {"pages": 1328, "resolved_to_existing": resolved,
                      "created": len(created), "refused": len(refusals),
                      "dual_role_men": len(dual),
                      "by_predicate": dict(n),
                      "assignment_vocabulary": dict(vocab.most_common())}}
    if write:
        # ATOMIC. A build store written with json.dump(open(path,"w")) streams into the
        # REAL file, so a rebuild reading it mid-write gets a truncated file. That is not
        # hypothetical: it cost Parsing a rebuild whose P3 reported "person P_040746
        # vanished" and 300+ others, because build_person_index caught the parse error
        # with `except Exception: continue` and skipped the whole store in silence.
        # dump_atomic writes a temp file, fsyncs and os.replaces, so a reader sees either
        # the old file or the new one, never half of one.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-officials.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv); c = o["counts"]
    for k in ("pages", "resolved_to_existing", "created", "refused", "dual_role_men"):
        print(f"  {k:24s} {c[k]:,}")
    print("  claims:", {k: f"{v:,}" for k, v in c["by_predicate"].items()})
    print(f"  assignment vocabulary: {len(c['assignment_vocabulary'])} distinct")
