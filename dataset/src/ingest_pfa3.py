"""PFA stage three: deaths, drafts, roster limits, training camps.

Four bodies, four shapes, and two of them are not about a person at all.

DEATHS are parsed by PERSON LINK, never by <tr>. PFA emits <tr> without closing
tags, so a <tr>...</tr> regex swallows several logical rows into one match -- one
CFL row appears to hold five men. The cells are read in document order and a date
is paired with the link that follows it.

DRAFTS reuse the player-page predicate exactly, so a query sees one kind of draft
claim and not two.

ROSTER LIMITS are a fact about a LEAGUE-SEASON and TRAINING CAMPS about a CLUB.
Neither is a person, and forcing them onto a person subject would be a lie about
what the source says.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
CACHE = "/Users/ryannecci/Documents/pgm3-sources/pfa2"
SP = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
      "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")
DECL = json.load(open(os.path.join(BASE, "declarations", "pfa.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]

CODE = re.compile(r"([a-z]{2,6}\d{4,6})")
TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
DATE = re.compile(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$")
LINK = re.compile(r'href="(/(?:players|coaches|officials)/[^"]*)"')


class PFA3Error(Exception):
    pass


def text(x):
    t = re.sub("<[^>]+>", " ", x)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&bull;", "•"), ("&#39;", "'")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def code_of(href):
    """PFA writes a person link four ways: /players/l/lee00120.html,
    /coaches/hoag00400.html (no letter directory at all), /players/lee001200.html
    (letter directory missing) and /players/brig00100/.html (the code sitting in
    the directory slot with an empty filename). The CODE is the stable part of all
    four, so it is what identity rests on -- as it has since stage one."""
    m = CODE.search(href or "")
    return m.group(1) if m else None


def name_link_agrees(name, code):
    """Does the code's stem appear in the printed surname?

    14 of 11,036 death records fail this. Eleven are benign -- PFA renders 'St.'
    as 'sain' (St. Clair -> sain00400) and the rest are surname spellings. Three
    are not: the coaches list prints 'Sherman Lewis' over a link to watt02530,
    which is MORRIS WATTS. Identity rests on the code, correctly, but that is
    exactly why a code contradicting its own label must be flagged and not
    written silently -- it is how a death gets filed under the wrong man."""
    stem = re.match(r"^([a-z]+)", code or "")
    if not stem:
        return None
    return stem.group(1) in re.sub(r"[^a-z]", "", (name or "").lower())


def person_map():
    cmap = {}
    for pid, v in json.load(open(SP + "pfa_match.json"))["matched"].items():
        c = code_of(v[0])
        if c:
            cmap[c] = pid
    for u, pid in json.load(open(SP + "pfa2_match.json"))["matched"].items():
        c = code_of(u)
        if c:
            cmap.setdefault(c, pid)
    return cmap


def claim(sr, subject, pred, value, kind="observed", **extra):
    if value in (None, "") or subject is None:
        raise PFA3Error("a claim needs a subject and a non-empty value")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": subject, "predicate": pred,
            "value": value, "kind": kind, "observed_at": "fetched-2026-09", **extra}


# ---------------------------------------------------------------- 1. deaths
DEATH_PAGES = {"player-deaths-nfl.html": ("NFL", "player"),
               "player-deaths-cfl.html": ("CFL", "player"),
               "coaches-deaths-nfl.html": ("NFL", "coach"),
               "coaches-deaths-cfl.html": ("CFL", "coach")}


def parse_deaths(html):
    """Cells in document order; a date followed by a person link is one record.
    Never <tr> -- see the module docstring."""
    out = []
    pending = None
    for raw in TD.finditer(html):
        inner = raw.group(1)
        t = text(inner)
        if DATE.match(t):
            pending = t; continue
        m = LINK.search(inner)
        if m and pending:
            out.append({"death_date": pending, "name_as_printed": t,
                        "href": m.group(1), "pfa_code": code_of(m.group(1))})
            pending = None
    return out


# ---------------------------------------------------------------- 2. drafts
DRAFT_TYPE = re.compile(r"^drafts_(\d{4})([a-z]+?)(draft|expansiondraft|allocationdraft|"
                        r"dispersaldraft|redshirtdraft|equalizationdraft)\.html$")


def cells(row):
    return [text(c) for c in TD.findall(row)]


def parse_draft_page(html, fname):
    """Columns are read BY HEADER NAME. 12 of 203 pages carry no Round or Overall
    at all -- expansion, allocation and dispersal drafts -- and 5 use a `From`
    column (the club a man came from) where others use `College`. Reading either
    by position would silently file a previous club as a college, and would give
    an expansion pick a round it never had."""
    tabs = re.findall(r"<table.*?</table>", html, re.S)
    if not tabs:
        return None, []
    best = max(tabs, key=len)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", best, re.S)
    if not rows:
        return None, []
    hdr = cells(rows[0])
    body = [cells(r) for r in rows[1:] if cells(r)]
    if not body:
        return None, []
    # 7 of 203 pages have data rows WIDER than the header: two unlabelled leading
    # cells sit where Round and Overall would be. The header labels the RIGHTMOST
    # columns, so it is aligned from the right -- and only when those leading cells
    # are actually empty, which is checked rather than assumed.
    common = collections.Counter(len(b) for b in body).most_common(1)[0][0]
    off = common - len(hdr)
    if off > 0 and all(not any(b[:off]) for b in body[:20] if len(b) > off):
        idx = {h: i + off for i, h in enumerate(hdr)}
    else:
        off = 0
        idx = {h: i for i, h in enumerate(hdr)}
    m = DRAFT_TYPE.match(fname)
    year = int(m.group(1)) if m else None
    league = (m.group(2) or "").upper() if m else ""
    kind = m.group(3) if m else "draft"
    complete = "Round" in idx and "Overall" in idx
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < len(hdr) + off - 1 or not c:
            continue
        get = lambda k: c[idx[k]] if k in idx and idx[k] < len(c) else ""
        if not get("Player"):
            continue
        rec = {"year": year, "league_from_filename": league, "draft_kind": kind,
               "team": get("Team"), "name_as_printed": get("Player"),
               "position_as_printed": get("Pos"),
               "notes": get("Notes") or get("Note"),
               "printed_order": len(out) + 1}
        # `From` is the club a man was taken FROM. It is not a college and is
        # never written as one.
        if "From" in idx:
            rec["from_club_as_printed"] = get("From")
        if "College" in idx:
            rec["college_as_printed"] = get("College")
        if complete:
            rd, pk = get("Round"), get("Overall")
            rec["round"] = int(rd) if rd.isdigit() else None
            rec["overall_pick"] = int(pk) if pk.isdigit() else None
        mm = LINK.search(r)
        rec["pfa_code"] = code_of(mm.group(1)) if mm else None
        out.append(rec)
    return ("selection" if complete else "allocation"), out


# ------------------------------------------------------- 3. roster limits
LIMIT_COLS = ("Active", "Inactive", "Practice Squad", "Contract", "Cutdown Dates",
              "Trade Deadline", "Free Agency", "Injured Reserve", "Notes")


def parse_roster_limits(html):
    """A LEAGUE-SEASON fact, not a person fact.

    The source's own empty-versus-absent distinction is preserved exactly: '-'
    means the thing did not exist that year (there were no practice squads in
    1920), '' means it existed and the value is not recorded. Collapsing them
    would assert PFA knows a 1920 practice-squad limit was zero."""
    best = max(re.findall(r"<table.*?</table>", html, re.S), key=len)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", best, re.S)
    hdr = cells(rows[0]); idx = {h: i for i, h in enumerate(hdr)}
    out = []
    for r in rows[1:]:
        c = cells(r)
        if len(c) < 2 or not c[idx.get("Year", 0)].isdigit():
            continue
        rec = {"year": int(c[idx["Year"]]), "league": c[idx["Lge"]]}
        for k in LIMIT_COLS:
            if k in idx and idx[k] < len(c):
                v = c[idx[k]]
                rec[k] = {"value": v,
                          "state": "did_not_exist" if v == "-" else
                                   ("not_recorded" if v == "" else "stated")}
        out.append(rec)
    return out


# ------------------------------------------------------- 4. training camps
def parse_training_camps(html):
    """The club is a SECTION HEADER, not a column: rows inherit it from above.
    `Years` is a RANGE STRING and is stored exactly as printed. Expanding
    '1920-1921' into two season facts is a different shape from what the source
    prints, and an expansion cannot be undone -- a stored range always can."""
    best = max(re.findall(r"<table.*?</table>", html, re.S), key=len)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", best, re.S)
    club = None; out = []
    for r in rows:
        c = cells(r)
        if len(c) == 1 and c[0]:
            club = c[0]; continue
        if len(c) >= 2 and club and c[0]:
            fac = c[1]
            mm = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", fac)
            out.append({"club_as_printed": club,
                        "years_as_printed": c[0],
                        "_years_is_a_range_not_a_year": True,
                        "facility": mm.group(1).strip() if mm else fac,
                        "location": mm.group(2).strip() if mm else ""})
    return out


# ------------------------------------------------------------------ assembly
def main(write=True):
    import write_bios as W
    cmap = person_map()
    claims, leads, disagreements = [], [], []
    n = collections.Counter(); deaths_by = collections.Counter()
    unresolved = collections.Counter()

    # existing death dates, to compare against
    have = collections.defaultdict(dict)
    for f, tag in (("pfa-pre1950.json", "pfa_player_page"), ("pfa-1950on.json", "pfa_player_page"),
                   ("wikipedia.json", "wikipedia")):
        p = os.path.join(BASE, "build", f)
        if not os.path.exists(p):
            continue
        for c in json.load(open(p))["claims"]:
            if c["predicate"].endswith("death_date"):
                have[c["subject"][1]].setdefault(tag, c["value"])

    # --- 1. deaths
    for fname, (lg, role) in DEATH_PAGES.items():
        h = open(os.path.join(CACHE, fname), encoding="utf-8", errors="replace").read()
        sr = f"{SRC_ID}#{fname}"
        for rec in parse_deaths(h):
            pid = cmap.get(rec["pfa_code"])
            deaths_by[(lg, role, "resolved" if pid else "unresolved")] += 1
            if not pid:
                unresolved["death"] += 1
                leads.append({"lead_id": f"lead-death-{len(leads)+1:05d}",
                              "category": "death_record_unresolved",
                              "name_as_printed": rec["name_as_printed"],
                              "pfa_code": rec["pfa_code"], "league": lg, "role": role,
                              "death_date": rec["death_date"], "source_record": sr,
                              "IS_NOT_A_PERSON": True,
                              "why": "no archive person resolves to this PFA code"})
                continue
            agrees = name_link_agrees(rec["name_as_printed"], rec["pfa_code"])
            extra = {} if agrees is not False else {
                "_name_link_mismatch": True,
                "_printed_name": rec["name_as_printed"],
                "_review": "the printed name does not match the linked code's stem"}
            if agrees is False:
                n["name_link_mismatch"] += 1
            claims.append(claim(sr, ["person", pid], "pfa.death_date", rec["death_date"],
                                _from="death_list", league=lg, role=role, **extra))
            n["death_date"] += 1
            for tag, other in have.get(pid, {}).items():
                if other and other != rec["death_date"]:
                    disagreements.append(
                        {"subject": ["person", pid], "field": "death_date",
                         "pfa_death_list": rec["death_date"], tag: other,
                         "other_source": tag, "resolved": None, "kind": "derived",
                         "_both_are_held": "neither value is preferred or removed"})

    # a man listed twice with different dates is the SOURCE contradicting itself
    seen = collections.defaultdict(set)
    for c in claims:
        if c["predicate"] == "pfa.death_date":
            seen[c["subject"][1]].add(c["value"])
    self_conflict = {p: sorted(v) for p, v in seen.items() if len(v) > 1}
    for p, v in self_conflict.items():
        disagreements.append({"subject": ["person", p], "field": "death_date",
                              "pfa_death_list": v[0], "pfa_death_list_also": v[1],
                              "other_source": "pfa_death_list", "resolved": None,
                              "kind": "derived",
                              "_the_source_contradicts_itself": True})

    # --- 2. drafts
    for fn in sorted(os.listdir(CACHE)):
        if not fn.startswith("drafts_"):
            continue
        h = open(os.path.join(CACHE, fn), encoding="utf-8", errors="replace").read()
        kind, rows = parse_draft_page(h, fn)
        if not kind:
            continue
        sr = f"{SRC_ID}#{fn}"
        for rec in rows:
            pid = cmap.get(rec["pfa_code"]) if rec["pfa_code"] else None
            pred = "pfa.draft_selection" if kind == "selection" else "pfa.draft_allocation"
            if pid:
                claims.append(claim(sr, ["person", pid], pred, rec))
                n[pred.split(".")[1]] += 1
            else:
                # TWO DIFFERENT FACTS, and folding them together overstates the
                # first eightfold:
                #   no_pfa_page  -- the row carries no player link at all. PFA
                #                   holds no page for this man.
                #   not_matched  -- PFA has a page; no ARCHIVE person resolves to
                #                   it. He is already among the deferred leads.
                # Neither says he never played. That needs roster cross-referencing
                # and this ingest does not settle it.
                cat = "no_pfa_page" if not rec["pfa_code"] else "pfa_page_not_matched"
                unresolved["draft_" + cat] += 1
                leads.append({"lead_id": f"lead-draft-{len(leads)+1:05d}",
                              "category": cat,
                              "name_as_printed": rec["name_as_printed"],
                              "pfa_code": rec["pfa_code"], "source_record": sr,
                              "IS_NOT_A_PERSON": True, "fields": rec,
                              "why": ("PFA holds no player page for this man"
                                      if cat == "no_pfa_page" else
                                      "PFA has a page but no archive person resolves to it"),
                              "_never_played_is_NOT_asserted": True})

    # --- 3. roster limits: a LEAGUE-SEASON subject
    h = open(os.path.join(CACHE, "nflrosterlimits.html"), encoding="utf-8",
             errors="replace").read()
    sr = f"{SRC_ID}#nflrosterlimits.html"
    for rec in parse_roster_limits(h):
        subj = ["league_season", rec["league"], rec["year"]]
        for k in LIMIT_COLS:
            if k in rec and rec[k]["state"] != "not_recorded":
                claims.append(claim(sr, subj, "pfa.roster_limit." + k.lower().replace(" ", "_"),
                                    rec[k], kind="observed" if rec[k]["state"] == "stated" else "absent"))
                n["roster_limit"] += 1

    # --- 4. training camps: a CLUB subject, range kept as printed
    h = open(os.path.join(CACHE, "trainingcamps.html"), encoding="utf-8",
             errors="replace").read()
    sr = f"{SRC_ID}#trainingcamps.html"
    for rec in parse_training_camps(h):
        claims.append(claim(sr, ["club", rec["club_as_printed"]], "pfa.training_camp", rec))
        n["training_camp"] += 1

    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           "claims": claims, "leads": leads, "disagreements": disagreements,
           "confirmed_absences": [
               {"what": "1946 AAFC draft", "url": "drafts/1946aafcdraft.html",
                "status": "HTTP 404", "_read_at_request_time": True},
               {"what": "1930 AFL equalization draft",
                "url": "drafts/1930aflequalizationdraft.html", "status": "HTTP 404",
                "_read_at_request_time": True}],
           "counts": {"claims": len(claims), "leads": len(leads),
                      "disagreements": len(disagreements),
                      "source_self_contradictions": len(self_conflict),
                      "by_predicate": dict(n),
                      "deaths": {f"{a} {b} {c}": v for (a, b, c), v in deaths_by.items()},
                      "unresolved": dict(unresolved)}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-stage3.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    for k in ("claims", "leads", "disagreements", "source_self_contradictions"):
        print(f"  {k:28s} {c[k]:,}")
    print("  by predicate:")
    for k, v in sorted(c["by_predicate"].items(), key=lambda x: -x[1]):
        print(f"     {k:22s} {v:,}")
    print("  deaths:")
    for k, v in sorted(c["deaths"].items()):
        print(f"     {k:24s} {v:,}")
