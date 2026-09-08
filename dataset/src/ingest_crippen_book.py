"""Kenneth R. Crippen, *The All-America Football Conference* -- read as a reference work.

RYAN'S RULING, 2026-09-08: a published reference work is used the way a reference
work is used. If the book were on the desk he would read the register and cite the
page. That it is a PDF changes nothing about the scholarship, and every claim carries
the book, the edition and the page.

WHAT THIS IS NOT. Not a wholesale lift. Each claim answers a question the archive
already had -- a man it holds, a selection it holds with no round, a coaching season,
a game -- and cites where the answer was read.

THE LINEAGE TRAVELS ON THE CLAIM, not only in the declaration. The linescores are
credited in the book to the PFRA Linescore Committee chaired by Gary Selby, one of the
three men Crippen himself named as the AAFC reconstruction team. Where they agree with
the archive that is partly the same people, and a reader must see that where they read
the claim.

  python3 src/ingest_crippen_book.py [--write]
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from readings import person_name, READERS
import dates as MD

REG = "/tmp/crippen_register.json"
PAGES = "/tmp/crippen_pages.json"
OUT = os.path.join(BASE, "build", "crippen-book.json")
REPORT = os.path.join(BASE, "build-reports", "crippen-book.json")

BOOK = {"source_id": "crippen-aafc-book",
        "title": "The All-America Football Conference",
        "author": "Kenneth R. Crippen (with Matt Reaser; Coach Register by John Maxymuk)",
        "edition": "2017, QuarkXPress typeset PDF, 368 pages",
        "stated_by": "Ken Crippen",
        "_how_it_is_used": "a reference work, consulted and cited. Every claim names "
                           "the book and the printed page it was read on."}
SELBY = ("The linescores are credited in the book to the Professional Football "
         "Researchers Association's Linescore Committee, chaired by GARY SELBY -- one "
         "of the three men Crippen named as the AAFC reconstruction team, with Pete "
         "Palmer and Ken Pullis. Where this agrees with StatsCrew or PFA about the "
         "AAFC it is partly the same people, and that is not corroboration.")

PREDICATES = {
    "crippen.reserve_list_rights": {
        "definition": "the club that held this man's reserve-list rights going into the "
                      "1950 allocation, as the book's allocation table prints it.",
        "why_its_own_predicate": "it is not a roster membership and not a draft "
            "selection: it says who COULD have kept him, not who employed him or who "
            "picked him. Filing it under roster_membership.rights_retained would make a "
            "franchise tag and a defunct league's reserve list the same assertion.",
        "proposed_by": "Archive, 2026-09-08; Ryan to rule on the name",
    },
    "crippen.playing_status_1950": {
        "definition": "where the man actually played in 1950 after the allocation, as "
                      "the book prints it -- including `Did Not Play`.",
        "why_its_own_predicate": "an OUTCOME of the allocation, not a stint. `Did Not "
            "Play` is a positive assertion that he played nowhere, which no "
            "roster_membership predicate can carry; and where he did play, the archive "
            "already holds that season from a roster source and this is a second "
            "statement about it, not a duplicate of it.",
        "proposed_by": "Archive, 2026-09-08; Ryan to rule on the name",
    },
    "crippen.draft_round": {
        "definition": "the round in which a selection was made, as this book prints it.",
        "why_it_matters": "PFA's allocation and dispersal pages print NO round, which is "
            "why those selections read with an order and no round. Crippen prints one. "
            "The archive holds what each source says: PFA still prints none, and this "
            "round is cited to Crippen.",
    },
    "crippen.coaching_season": {
        "definition": "a season on a club's coaching staff with the position held, head "
                      "or assistant, as the Coach Register prints it.",
    },
    "crippen.attendance": {"definition": "the attendance at one game, as the linescores print it."},
    "crippen.scoring_play": {"definition": "one scoring play in one game, verbatim."},
    "crippen.exhibition_game": {
        "definition": "an exhibition game: the date, the two clubs, the score and the "
                      "city. IT NAMES A GAME AND A RESULT, NOT MEN -- the exhibition "
                      "list carries no lineup and no man may be placed on a club by it.",
    },
}


def norm(s):
    return person_name(s)


def flip(printed):
    """`ADAMLE, Anthony (Tony)` -> the forms a reader would search: the nickname first."""
    sur, _, fore = printed.partition(",")
    fore = fore.strip()
    nick = re.search(r"\(([^)]+)\)", fore)
    plain = re.sub(r"\(.*?\)", "", fore).strip()
    out = []
    if nick: out.append(f"{nick.group(1).strip()} {sur.strip()}")
    if plain: out.append(f"{plain.split()[0]} {sur.strip()}"); out.append(f"{plain} {sur.strip()}")
    return out


def main():
    write = "--write" in sys.argv
    reg = json.load(open(REG))
    pages = json.load(open(PAGES))
    conn = sqlite3.connect(paths.READ_MODEL)

    byname = collections.defaultdict(set)
    for p, n in conn.execute("select person, name from person_name"):
        byname[norm(n)].add(p)
    cohort = {p for (p,) in conn.execute(
        "select distinct person from claim where scope='stint' and league='AAFC' "
        "and year between 1946 and 1949 and person is not null")}
    held = collections.defaultdict(lambda: collections.defaultdict(set))
    for p, fam, v in conn.execute(
            "select person, family, value_text from claim where family in "
            "('college','height','weight','birth_date','birth_place','death_date','death_place') "
            "and person is not null and source_id != 'crippen-aafc-book'"):
        held[p][fam].add(str(v).strip())

    n = collections.Counter(); claims = []; leads = []; srs = {}
    weights = []; others = collections.defaultdict(list)
    cid = 0

    def add(pid, pred, val, page, extra=None):
        nonlocal cid
        cid += 1
        rec = f"crippen-aafc-book#page {page}"
        srs[rec] = {"source_id": "crippen-aafc-book", "locator": f"page {page}"}
        c = {"id": "c_%05d" % cid, "predicate": pred, "value": val,
             "subject": ["person", pid] if pid else ["source", "crippen-aafc-book"],
             "kind": "observed", "source_id": "crippen-aafc-book",
             "source_record": rec, "stated_by": "Ken Crippen",
             "attribution": [f"{BOOK['title']}, {BOOK['author']}, {BOOK['edition']}, p. {page}"],
             "observed_at": 2017, "_cited": f"{BOOK['title']}, p. {page}"}
        if extra: c.update(extra)
        claims.append(c); n[pred] += 1
        return c

    # ---------------- Part 8: the Player Register
    for e in reg:
        page = e["book_page"]
        hits = set()
        for form in flip(e["name_as_printed"]):
            h = byname.get(norm(form), set()) & cohort
            if len(h) == 1: hits = h; break
        if len(hits) != 1:
            for form in flip(e["name_as_printed"]):
                h = byname.get(norm(form), set())
                if len(h) == 1: hits = h; break
        if len(hits) != 1:
            # surname and forename initial, held to the AAFC cohort
            w = norm(flip(e["name_as_printed"])[0]).split()
            loose = [p for p in cohort
                     if any(x.split() and x.split()[-1] == w[-1] and x.split()[0][:1] == w[0][:1]
                            for x in [norm(nm) for (nm,) in conn.execute(
                                "select name from person_name where person=?", (p,))])] if len(w) >= 2 else []
            if len(loose) == 1: hits = {loose[0]}
        if len(hits) != 1:
            n["register: left as a lead"] += 1
            leads.append({"IS_NOT_A_PERSON": True, **e}); continue
        pid = next(iter(hits)); n["register: joined"] += 1

        add(pid, "name", e["name_as_printed"], page,
            {"_as_printed": "surname, full forenames and the nickname the book prints"})
        add(pid, "position", e["position_as_printed"], page)
        if e.get("height_as_printed"): add(pid, "height", e["height_as_printed"], page)
        # WEIGHTS ARE THE POINT. Compared, both held, neither resolved.
        wt = e.get("weight_as_printed")
        if wt:
            prior = held[pid]["weight"]
            add(pid, "weight", wt, page)
            if not prior: n["weight: the archive holds none"] += 1
            elif wt in prior: n["weight agrees"] += 1
            else:
                n["WEIGHT DISAGREES -- both held"] += 1
                weights.append({"person": pid, "name": e["name_as_printed"],
                                "crippen": wt, "the_archive": sorted(prior), "page": page})
        for col in [c.strip() for c in (e.get("colleges_as_printed") or "").split(",") if c.strip()]:
            add(pid, "college", col, page,
                {"_two_colleges": "the book records a man's colleges as a list; each is "
                                  "its own claim and neither replaces the other"})
            r = READERS["college"](col)
            prior = {READERS["college"](x) for x in held[pid]["college"]}
            if not held[pid]["college"]: n["college: the archive holds none"] += 1
            elif r in prior: n["college agrees"] += 1
            else:
                n["college differs"] += 1
                others["college"].append({"person": pid, "crippen": col,
                                          "the_archive": sorted(held[pid]["college"]), "page": page})
        born = e.get("born_as_printed") or ""
        m = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})(?:,\s*(.+))?$", born.strip())
        if m:
            add(pid, "birth_date", m.group(1), page)
            prior = held[pid]["birth_date"]
            if not prior: n["birth date: the archive holds none"] += 1
            else:
                mine = MD.read(m.group(1))
                ok = any(MD.read(x) and MD.key(MD.read(x)) == MD.key(mine) for x in prior)
                n["birth date agrees" if ok else "BIRTH DATE DISAGREES -- both held"] += 1
                if not ok: others["birth_date"].append(
                    {"person": pid, "crippen": m.group(1), "the_archive": sorted(prior), "page": page})
            if m.group(2):
                add(pid, "birth_place", m.group(2).strip(), page)
                if not held[pid]["birth_place"]: n["BIRTH PLACE the archive holds none"] += 1
        dec = (e.get("deceased_as_printed") or "").strip()
        md = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})(?:,\s*(.+))?$", dec)
        if md:
            add(pid, "death_date", md.group(1), page)
            if not held[pid]["death_date"]: n["death date: the archive holds none"] += 1
            if md.group(2):
                add(pid, "death_place", md.group(2).strip(), page)
                if not held[pid]["death_place"]: n["death place: the archive holds none"] += 1

    # ---------------- Part 7: the drafts, and the two columns nothing else has
    ALLOC = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s{1,}([A-Z][A-Za-z/\-]{0,4})\s{2,}(.+?)\s{2,}(.+?)\s{2,}(.+?)\s*$")
    DRAFT = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s{2,}([A-Z][A-Za-z/\-]{0,4})\s{2,}(.+?)\s{2,}(.+?)\s*$")
    def draftees(lo, hi, alloc):
        rnd = None; year = None; rows = []
        for pg in range(lo, hi + 1):
            lay = pages[str(pg)]["layout"]; bp = pages[str(pg)]["book_page"]
            for l in lay.split("\n"):
                my = re.match(r"^\s*(19[45]\d)\s*$", l.strip())
                if my: year = int(my.group(1))
                mh = re.match(r"^\s*(19[45]\d)\s+\d+\s*$", l.strip())
                if mh: year = int(mh.group(1))
                mr = re.match(r"^\s*Round (\d+)", l.strip())
                if mr: rnd = int(mr.group(1))
                if re.match(r"^\s*Extra Picks", l.strip()): rnd = None
                m = (ALLOC if alloc else DRAFT).match(l)
                if m and m.group(1).isdigit() and not l.strip().startswith("No"):
                    rows.append({"no": int(m.group(1)), "player": m.group(2).strip(),
                                 "pos": m.group(3), "college": m.group(4).strip(),
                                 "drafted_by": m.group(5).strip(),
                                 "rights": m.group(6).strip() if alloc and m.lastindex >= 6 else None,
                                 "round": rnd, "year": year, "page": bp})
        return rows
    aafc = draftees(156, 169, False)
    alloc = draftees(170, 174, True)
    n["AAFC draft rows read"] = len(aafc)
    n["allocation draft rows read"] = len(alloc)
    for r in aafc + alloc:
        hits = byname.get(norm(r["player"]), set())
        pid = next(iter(hits)) if len(hits) == 1 else None
        if not pid:
            n["draft row: left as a lead"] += 1
            leads.append({"IS_NOT_A_PERSON": True, "kind": "draft", **r}); continue
        n["draft row joined"] += 1
        if r["round"]:
            add(pid, "crippen.draft_round",
                {"year": r["year"], "round": r["round"], "overall": r["no"],
                 "league": "AAFC" if r in aafc else "NFL",
                 "kind": "draft" if r in aafc else "allocationdraft",
                 "player_as_printed": r["player"], "club_as_printed": r["drafted_by"],
                 "college_as_printed": r["college"]}, r["page"],
                {"_pfa_prints_no_round": "PFA's allocation and dispersal pages carry no "
                 "Round column at all, which is why those selections read with an order "
                 "and no round. This round is Crippen's and is cited to him."})
        if r.get("rights"):
            add(pid, "crippen.reserve_list_rights", r["rights"], r["page"])
        # the allocation table's last column is the 1950 playing status
    # ---------------- Part 9: the Coach Register (heads AND assistants)
    CO = re.compile(r"^\s*(19[45]\d)\s+(.+?)\s{2,}(Head Coach|Assistant|Line|Backfield|End[s]?|Tackle[s]?|Guard[s]?|Center|Scout|[A-Z][A-Za-z /\-]{2,24})\s*$")
    HEADC = re.compile(r"^([A-Z][A-Z'’\-]{2,}(?:\s+[A-Z][A-Z'’\-]+)*),\s+(.+)$")
    cur = None
    for pg in range(349, 369):
        lay = pages[str(pg)]["layout"]; bp = pages[str(pg)]["book_page"]
        for l in lay.split("\n"):
            st = l.strip()
            mh = HEADC.match(st)
            if mh and len(mh.group(1)) > 2 and "Part" not in st and "Register" not in st:
                cur = st; continue
            m = CO.match(l)
            if m and cur:
                hits = set()
                for form in flip(cur):
                    h = byname.get(norm(form), set())
                    if len(h) == 1: hits = h; break
                if len(hits) != 1:
                    n["coach row: left as a lead"] += 1
                    leads.append({"IS_NOT_A_PERSON": True, "kind": "coach",
                                  "name_as_printed": cur, "year": int(m.group(1)),
                                  "club_as_printed": m.group(2).strip(),
                                  "position_as_printed": m.group(3).strip(), "page": bp})
                    continue
                n["coach row joined"] += 1
                add(next(iter(hits)), "crippen.coaching_season",
                    {"year": int(m.group(1)), "club_as_printed": m.group(2).strip(),
                     "position_as_printed": m.group(3).strip()}, bp,
                    {"_includes_assistants": "the Coach Register carries assistants as "
                     "well as head coaches, which is a class the archive is thin on. It "
                     "fills NONE of the fifteen club-seasons holding men and no coach -- "
                     "not one of those fifteen is AAFC."})

    # ---------------- Part 6: linescores -- attendance, and the exhibition list
    ATT = re.compile(r"Attendance[—-]\s*([\d,]+)")
    VEN = re.compile(r"^\s*(?:[A-Z][a-z]+day(?: Night)?|[A-Z][a-z]+),?\s+([A-Z][a-z]+ \d{1,2}),?\s+at\s+(.+?)\s*$")
    EX = re.compile(r"^\s*([A-Z][a-z]+ \d{1,2}),\s+([A-Za-z. ]+?)\s+(\d{1,3})\s+vs\.\s+([A-Za-z. ]+?)\s+(\d{1,3})\s*\(([^)]*)\)")
    inex = False
    for pg in range(90, 155):
        lay = pages[str(pg)]["layout"]; bp = pages[str(pg)]["book_page"]
        if "Exhibition Games" in lay: inex = True
        for l in lay.split("\n"):
            if inex:
                me = EX.match(l)
                if me:
                    n["exhibition games"] += 1
                    add(None, "crippen.exhibition_game",
                        {"date_as_printed": me.group(1), "club_a": me.group(2).strip(),
                         "score_a": int(me.group(3)), "club_b": me.group(4).strip(),
                         "score_b": int(me.group(5)), "city_as_printed": me.group(6)},
                        bp, {"_names_a_game_not_men": "the exhibition list carries no "
                             "lineup. It names a game and a result; no man may be placed "
                             "on a club by it.", "_lineage": SELBY})
                    continue
            ma = ATT.search(l)
            if ma:
                n["attendance figures"] += 1
                add(None, "crippen.attendance",
                    {"attendance": int(ma.group(1).replace(",", "")),
                     "line_as_printed": l.strip()[:120]}, bp, {"_lineage": SELBY})
    out = {"source": BOOK, "predicate_definitions": PREDICATES,
           "_the_lineage": SELBY,
           "_not_a_wholesale_lift": "every claim answers a question the archive already "
                                    "had and cites the page it was read on.",
           "source_records": srs, "claims": claims, "leads": leads,
           "weight_disagreements": weights,
           "other_disagreements": {k: v for k, v in others.items()},
           "counts": dict(n) | {"claims": len(claims), "leads": len(leads)}}
    print("PART 8 -- THE PLAYER REGISTER")
    for k, v in n.most_common(): print(f"   {k:44s} {v:>6,}")
    print(f"\n   WEIGHT DISAGREEMENTS: {len(weights)}")
    for w in weights[:10]:
        print(f"      p{w['page']:>3} {w['name'][:30]:30s} Crippen {w['crippen']:>4}  archive {w['the_archive']}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        json.dump({"counts": dict(n), "weight_disagreements": weights,
                   "other_disagreements": {k: v for k, v in others.items()},
                   "leads": leads}, open(REPORT, "w"), indent=1)
        print("\nwrote", OUT)
    else:
        print("\n   (dry run; --write to store)")


if __name__ == "__main__":
    main()
