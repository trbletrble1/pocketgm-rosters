"""Ingest Pro Football Archives, pre-1950. Writes dataset/build/pfa-pre1950.json.

Three shapes here, and the third is new.

FIELDS on a person -- high school, birth place, death date and place, draft round
and pick, military service, height, weight -- attributed to PFA and ranked as a
SECOND VOICE beside StatsCrew. Where they differ, BOTH are held.

COLLEGE is a table, not a string: year, college, participation level ("Played",
"Lettered", "Roster"). Kept as rows with the raw participation word.

THE TRANSACTION LOG is a sequence of events and only 44.9% carry a date. Each
entry is its own claim carrying `dated` and `printed_row`. printed_row is the
row's position ON THE PAGE -- what the source shows -- and is NOT a chronology.
There is no code path that gives an undated entry a date, because a log that
silently orders undated events asserts a sequence the source does not give.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
DECL = json.load(open(os.path.join(BASE, "declarations", "pfa.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")


class PFAError(Exception):
    pass


LABEL = re.compile(r"<b>\s*([A-Za-z][A-Za-z ]{1,28}?)\s*:\s*</b>")
# A value ENDS at the next label or at the end of its cell. It does not run on.
STOP = re.compile(r"<b\b|</td>|</tr>|</table>")
ENT = {"&nbsp;": " ", "&amp;": "&", "&bull;": "\u2022", "&quot;": '"', "&#39;": "'"}


def text(fragment):
    t = re.sub("<[^>]+>", " ", fragment)
    for k, v in ENT.items():
        t = t.replace(k, v)
    return re.sub(r"\s+", " ", t).strip()


def cells(row):
    return [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def labelled(html):
    """Every <b>Label:</b> on the page, with its value bounded by the NEXT LABEL
    OR THE END OF ITS CELL.

    The bound is the whole point. PFA prints the label whether or not it has a
    value -- 'High School:' appears on 100% of pages -- so a reader that takes
    'whatever text follows' will, on an empty field, walk past the cell and
    return the next thing it finds. That is how 'High School: Year' happens:
    'Year' is the header of the college table further down the page. An empty
    field and a missing one are the same bytes here, and both must yield "".

    Values are tag-STRIPPED, not tag-bounded: Draft's value lives inside an <a>,
    so stopping at the first '<' would empty every draft on the site."""
    out = {}
    for m in LABEL.finditer(html):
        rest = html[m.end():]
        stop = STOP.search(rest)
        out.setdefault(m.group(1).strip(), text(rest[:stop.start()] if stop else rest[:200]))
    return out


KIN_CELL = re.compile(r"<b>\s*Relatives\s*:\s*</b>(.*?)</td>", re.S)
KIN_LINK = re.compile(r'<a href="/(players|coaches|officials)/(?:[a-z]/)?([a-z0-9]+)\.html"[^>]*>(.*?)</a>')


def parse_relatives(html):
    """Kinship edges, exactly as printed.

    THE SEPARATOR IS ';' AND ONLY ';'. A comma inside one of these cells is part
    of a name -- "Chuck Drulis, Jr." -- never a boundary. Measured: 0 of 258 cells
    use a comma outside a link, 48 use a semicolon.

    NO INVERSE IS EVER SYNTHESISED. PFA prints both directions itself: Al Akins'
    page says "Brother of Frank Akins" and Frank's says "Brother of Al Akins";
    all six Nesser brothers each list the other five. Manufacturing the reciprocal
    would turn one source statement into two and make a derived claim wear the
    clothes of an observed one. Every edge here was printed on the page it came
    from, and if a direction is missing that is a fact about PFA, not a gap to fill.

    THE FAR END MAY LEAVE THE PLAYER POPULATION. Six edges point at /coaches/ and
    two at /officials/ -- Steve Belichick's son Bill among them. Those will never
    resolve against an archive built on who played, so the edge holds the section
    and code and stays unresolved rather than being dropped.

    The relation word is kept RAW. 'Brother' and 'brother' and 'Twin brother' are
    three different strings and PFA meant each of them; folding them is a ruling."""
    m = KIN_CELL.search(html)
    if not m:
        return []
    out = []
    for part in m.group(1).split(";"):
        link = KIN_LINK.search(part)
        if not link:
            continue
        before = part[:link.start()]
        rel = re.sub(r"\s+of\s*$", "", text(before)).strip()
        if not rel:
            continue
        out.append({"relation_as_printed": rel,
                    "of_name": text(link.group(3)),
                    "of_pfa_section": link.group(1),
                    "of_pfa_code": link.group(2),
                    "of_person": None,
                    "printed_order": len(out) + 1})
    return out


def parse_player(html):
    L = labelled(html)

    def split_dp(s):
        m = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s*(.*)$", s)
        return (m.group(1), m.group(2).strip()) if m else ("", s.strip())

    bd, bp = split_dp(L.get("Born", ""))
    dd, dp = split_dp(L.get("Died", ""))
    out = {"birth_date": bd, "birth_place": bp, "death_date": dd, "death_place": dp,
           "high_school": L.get("High School", ""), "height": L.get("Height", ""),
           "weight": L.get("Weight", ""), "draft": L.get("Draft", ""),
           "military_service": L.get("Military Service", ""),
           "position": L.get("Position", ""), "relatives": parse_relatives(html),
           "college_rows": [], "college_stated_none": False, "transactions": []}
    for tbl in re.findall(r"<table.*?</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S)
        if not rows:
            continue
        hdr = [c.lower() for c in cells(rows[0])]
        if "year" in hdr and "college" in hdr:
            for r in rows[1:]:
                c = cells(r)
                if len(c) < 2:
                    continue
                # PFA prints a row reading college 'none' with no year. That is the
                # SOURCE SAYING THERE WAS NO COLLEGE -- an absence it asserts, not a
                # row we failed to read. Dropping it would lose the statement.
                if not c[0] and c[1].strip().lower() == "none":
                    out["college_stated_none"] = True
                    continue
                if c[0]:
                    out["college_rows"].append(
                        {"year": c[0], "college": c[1],
                         "participation": (c[2] if len(c) > 2 else "")})
        if "transaction" in hdr:
            n = 0
            for r in rows[1:]:
                c = cells(r)
                if len(c) < 2:
                    continue
                # the first cell holds "<season> <Club> (<LEAGUE>)<Club>" -- the
                # season context and the club name run together because they are
                # separate elements in one cell. Split rather than store the join.
                raw = c[0]
                m = re.match(r"^(.*\))\s*(.*)$", raw)
                season_context, team = (m.group(1).strip(), m.group(2).strip()) if m else ("", raw)
                if not team:
                    team = season_context
                date = c[1] if len(c) > 1 else ""
                typ = c[2] if len(c) > 2 else ""
                if not DATE.match(date):            # the date cell is empty or not a date
                    typ = typ or date
                    date = ""
                if not (team or typ):
                    continue
                n += 1
                out["transactions"].append(
                    {"team": team, "season_context": season_context,
                     "date": date or None, "type": typ,
                     "dated": bool(date), "printed_row": n})
    return out


def transaction_claim(sr, pid, e):
    """An undated transaction CANNOT acquire a date. There is no argument that
    would let it: the value carries date=None and dated=False, and printed_row is
    the page's row position, not a time."""
    if not e["dated"] and e["date"]:
        raise PFAError("an undated transaction was given a date")
    if e["dated"] and not DATE.match(e["date"] or ""):
        raise PFAError("dated=True but the date is not a date")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": ["person", pid],
            "predicate": "pfa.transaction", "value": e, "kind": "observed",
            "observed_at": "fetched-2026-09",
            "_printed_row_is_not_a_chronology": True}


def claim(sr, pid, pred, value):
    if not pid:
        raise PFAError("a claim requires a matched person; a lead is not a person")
    # PFA prints the label whether or not it has a value. An empty value is the
    # source saying NOTHING, and nothing is not a fact. It is also indistinguishable
    # from a read that failed -- same bytes -- so neither may become a claim.
    if isinstance(value, str) and not value.strip():
        raise PFAError("an empty value is not a claim: the label was printed, the fact was not")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": ["person", pid],
            "predicate": pred, "value": value, "kind": "observed",
            "observed_at": "fetched-2026-09"}


FIELD_PREDICATE = {
    "high_school": "pfa.high_school", "birth_place": "pfa.birth_place",
    "birth_date": "pfa.birth_date", "death_date": "pfa.death_date",
    "death_place": "pfa.death_place", "draft": "pfa.draft",
    "military_service": "pfa.military_service", "height": "pfa.height",
    "weight": "pfa.weight", "position": "pfa.position",
}


def kin_claim(sr, pid, e):
    """A kinship edge. The SUBJECT must be a matched person; the OBJECT need not be.

    That asymmetry is deliberate. PFA states "Brother of Frank Akins, /players/a/
    akin00300" -- a fact about the man whose page this is, made in terms of another
    man it names and codes. If akin00300 doesn't resolve, the statement about the
    subject is undamaged: what is unknown is who the object is, not whether the
    claim was made. Holding the section and code means a later resolution sharpens
    the edge with no re-parse, which is the same bargain the leads take.

    Six of these point at /coaches/ and two at /officials/. Those will never resolve
    against an archive built on who played, and they are still real edges."""
    if not e.get("relation_as_printed") or not e.get("of_pfa_code"):
        raise PFAError("a kinship edge needs a printed relation and a coded object")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": ["person", pid],
            "predicate": "pfa.kin", "value": e, "kind": "observed",
            "observed_at": "fetched-2026-09",
            "_object_may_be_unresolved": True,
            "_inverse_is_never_synthesised": True}


def disagreement(pid, field, pfa_value, other_value, other_source):
    """PFA is a SECOND VOICE, not a correction. Where it differs from StatsCrew both
    values stand and nothing is resolved -- there is no `winner` key to set.

    This record is DERIVED: it is an index over two observed claims, not a new
    observation, and it is marked so. It adds no information; it only says where
    to look."""
    if not pfa_value or not other_value or pfa_value == other_value:
        raise PFAError("a disagreement needs two different non-empty values")
    return {"subject": ["person", pid], "field": field,
            "pfa": pfa_value, "statscrew": other_value,
            "other_source": other_source, "resolved": None,
            "kind": "derived",
            "_both_are_held": "neither value is preferred, removed or merged"}


# What PFA IS, field by field. Measured, not assumed: StatsCrew already holds
# birth_date for 100% of pre-1950 men in the archive and college for 99.7%
# (checked on the UNMATCHED remainder too, so it is a coverage fact and not an
# artefact of who matched). PFA therefore adds nothing to those two except a
# second opinion -- while high school, death, military service, draft, kinship
# and the transaction log have no StatsCrew counterpart at all.
SECOND_VOICE = {"birth_date": "birth_date", "college": "college"}
GAP_FILL = ("high_school", "death_date", "death_place", "military_service",
            "draft", "birth_place", "height", "weight")
# birth_place is NOT compared to StatsCrew's `hometown`. Where a man was born and
# where he was from are different facts and a disagreement between them would be
# manufactured. PFA's birth_place is new information, not a second voice.
NEVER_COMPARE = {"birth_place": "hometown"}

MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October "
    "November December".split())}


def date_key(s):
    """A date compared as integers. 'July 7, 1906' and '1906-07-07' are the same
    day and comparing them as strings invents a disagreement -- that cost 231 false
    positives the last time it was measured against Wikipedia."""
    if not s:
        return None
    m = re.match(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})$", s.strip())
    if m and m.group(1) in MONTHS:
        return (int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", s.strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def rescope(match):
    """A PFA player code that resolves to an archive person resolves EVERYWHERE.

    Identity was confirmed per club-season, which made the archive's roster gaps
    look like unknown men: Frank Umont matched on the 1944 Giants and fell through
    as a lead on the 1943. Same man, same code, two verdicts. The code is the
    source's own assertion of identity and it does not vary by season.

    Returns (person_by_code, true_leads, roster_disagreements). Nothing is
    promoted here -- a lead that was ALWAYS a lead stays one."""
    person_by_code = {v[0]: pid for pid, v in match["matched"].items()}
    true_leads, roster = [], []
    for cs, name, url in match["leads"]:
        if url in person_by_code:
            roster.append({"subject": ["person", person_by_code[url]],
                           "field": "club_season_roster",
                           "pfa": {"club_season": cs, "name_as_printed": name},
                           "statscrew": "not on this club-season roster",
                           "other_source": "statscrew", "resolved": None,
                           "kind": "derived",
                           "_both_are_held": "PFA places him here and the archive "
                                             "does not; neither side is removed"})
        else:
            true_leads.append((cs, name, url))
    return person_by_code, true_leads, roster


CACHE = "/Users/ryannecci/Documents/pgm3-sources/pfa2"
LEAD_FIELDS = ("high_school", "height", "weight", "birth_place", "death_place",
               "birth_date", "death_date", "draft", "military_service", "position")


DOUBLED = re.compile(r"^players/[a-z]/([a-z])/(.+)$")


def canonical_url(url):
    """PFA links some men twice on one roster page, once correctly and once with a
    doubled letter directory: the 1949 Baltimore page carries BOTH
    /players/b/beso00200.html and /players/s/b/beso00200.html for Warren Beson.
    The second 404s. It is the source's typo, not a second man, and the player code
    is identical -- which is the same reason the code and not the name is what
    identity rests on."""
    m = DOUBLED.match(url)
    return f"players/{m.group(1)}/{m.group(2)}" if m else url


def page(url):
    for u in {url, canonical_url(url)}:
        p = os.path.join(CACHE, re.sub(r"^/", "", u).replace("/", "_"))
        if os.path.exists(p):
            return open(p, encoding="utf-8", errors="replace").read()
    return None


# Links PFA prints on its own roster pages that resolve to no page on PFA. Verified
# by fetching each one and reading the status: 11 HTTP 404s, not 11 empty reads.
# A dead link is the SOURCE naming a man it has no record of -- neither a man we
# failed to fetch nor a man who does not exist -- and it is kept apart from both.
SOURCE_DEAD_LINKS = {
    "players/a/allm00200.html", "players/b/butc00350.html", "players/c/a.html",
    "players/d/dono00200.html", "players/g/glas00100.html", "players/h/hens00050.html",
    "players/m/mart04300.html", "players/r/roes00400.html", "players/s/sirt00200.html",
    "players/s/stan00700.html", "players/w/wood04480.html",
}


def required(*parts):
    """Resolve a load-bearing input under BASE, and refuse to run without it.

    This replaced a read from a session scratchpad guarded by os.path.exists. The
    path carried a session id; when the archive moved to bghq-mac on 2026-09-07 the
    file was not there, and the guard turned a missing input into an empty dict.
    The same shape cost the bios 30,503 claims about 4,542 men without one word of
    complaint (declarations/session-scratchpad-inputs.json). Missing is fatal here.
    """
    fp = os.path.join(BASE, *parts)
    if not os.path.exists(fp):
        raise SystemExit("%s: required input missing: %s" % (
            os.path.basename(__file__), os.path.normpath(fp)))
    return fp


def main(write=True):
    import write_bios as W
    match = json.load(open(required("build", "pfa-match.json")))
    by_code, true_leads, disagreements = rescope(match)

    claims, leads, missing, dead = [], [], [], []
    n = collections.Counter()
    for pid, v in match["matched"].items():
        url = v[0]
        h = page(url)
        if h is None:
            (dead if canonical_url(url) in SOURCE_DEAD_LINKS else missing).append(url)
            continue
        r = parse_player(h)
        sr = f"{SRC_ID}#{url}"
        sc = (W.IDX.get(pid) or {}).get("person") or {}

        for f in GAP_FILL:
            if not r[f]:
                continue
            if f == "draft":
                dc = draft_claims(sr, pid, h, r[f])
                claims.extend(dc); n["draft"] += 1
                n["draft_selection"] += len(dc) - 1
                unsplit = len(parse_drafts(h)) - (len(dc) - 1)
                if unsplit:
                    n["draft_segments_unparsed"] += unsplit
            else:
                claims.append(claim(sr, pid, FIELD_PREDICATE[f], r[f])); n[f] += 1
        # career-level, and kept apart from StatsCrew's per-season codes: PFA says
        # 'G-T' for a whole career, StatsCrew says a code per season. Comparing
        # them would compare two different measurements, so no disagreement is
        # computed and the predicate says which one this is.
        if r["position"]:
            claims.append(claim(sr, pid, "pfa.position_career", r["position"]))
            n["position_career"] += 1
        if r["birth_date"]:
            claims.append(claim(sr, pid, FIELD_PREDICATE["birth_date"], r["birth_date"]))
            other = (sc.get("birth_date") or [None])[0]
            if other and date_key(r["birth_date"]) and date_key(other) \
                    and date_key(r["birth_date"]) != date_key(other):
                disagreements.append(
                    disagreement(pid, "birth_date", r["birth_date"], other, "statscrew"))
        for row in r["college_rows"]:
            claims.append(claim(sr, pid, "pfa.college_season", row)); n["college_season"] += 1
        if r["college_stated_none"]:
            # the source ASSERTING no college. An absence it states, not one we infer.
            claims.append({**claim(sr, pid, "pfa.college", "none"), "kind": "absent"})
            n["college_stated_none"] += 1
        for e in r["relatives"]:
            e = dict(e, of_person=by_code.get("players/" + e["of_pfa_code"][0] + "/"
                                              + e["of_pfa_code"] + ".html"))
            claims.append(kin_claim(sr, pid, e)); n["kin"] += 1
        for e in r["transactions"]:
            claims.append(transaction_claim(sr, pid, e)); n["transaction"] += 1

    for i, (cs, name, url) in enumerate(true_leads):
        h = page(url)
        r = parse_player(h) if h else None
        leads.append({"lead_id": f"lead-pfa-{i+1:05d}", "category": "unmatched_no_candidate",
                      "name_as_printed": name, "places_on": cs,
                      "source_id": SRC_ID, "source_record": f"{SRC_ID}#{url}",
                      "pfa_url": url, "candidate_person": None, "IS_NOT_A_PERSON": True,
                      "why_matching_failed": "no archive person resolves to this PFA "
                                             "player code on any club-season",
                      "fields": {f: (r[f] if r else "") for f in LEAD_FIELDS},
                      "college_rows": (r["college_rows"] if r else []),
                      "relatives": (r["relatives"] if r else []),
                      "transactions": (r["transactions"] if r else [])})

    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "fetched"},
           "claims": claims, "leads": leads, "disagreements": disagreements,
           "counts": {"matched_people": len(match["matched"]), "claims": len(claims),
                      "lead_entries": len(leads),
                      "lead_pages": len({l["pfa_url"] for l in leads}),
                      "roster_disagreements": sum(1 for d in disagreements
                                                  if d["field"] == "club_season_roster"),
                      "birth_date_disagreements": sum(1 for d in disagreements
                                                      if d["field"] == "birth_date"),
                      "pages_missing_from_cache": len(missing),
                      "source_dead_links": len(dead),
                      "by_predicate": dict(n)}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "pfa-pre1950.json"), indent=1)
    return out




DRAFT_CELL = re.compile(r"<b>\s*Draft\s*:\s*</b>(.*?)</td>", re.S)
DRAFT_LINK = re.compile(r'<a href="/drafts/(\d{4})([a-z]+)draft\.html"[^>]*>(.*?)</a>')
# Round and overall pick, tolerant of PFA's OWN typography but never inventing a
# value: '3rdd round', 'round(300th', '32nd (325th overall)' and '(38 overall)'
# with no ordinal all appear on their pages. The ordinal suffix is optional; the
# NUMBER is not.
D_ROUND = re.compile(r"^(\d+)(?:st|nd|rd|th|d)*\s*(?:round)?\s*\(", re.I)
D_PICK = re.compile(r"\((\d+)(?:st|nd|rd|th)?\s*overall\)", re.I)
D_TAIL = re.compile(r"(\d{4})\s+(.+?)\s*$")
# Draft events that carry no round by their nature. These are TYPES, not failures:
# the AAFC's territorial 'Special Selection' and the NFL's 'Bonus Pick' lottery.
D_TYPE = re.compile(r"^(Special Selection|Bonus Pick)", re.I)


def parse_drafts(html):
    """One record per draft, anchored on the <a> elements -- not on splitting text.

    Each draft is its own link, and the HREF carries year and league structurally:
    /drafts/1947aafcdraft.html and /drafts/1947nfldraft.html are the two drafts a
    1947 man could be taken in. Reading league from the link beats inferring it
    from a club name, and it gives a cross-check against the year printed in the
    text.

    A segment that cannot be read is returned with parsed=False and its raw text.
    Nothing is guessed: '9-71 1947 Philadelphia Eagles' is not silently read as
    round 9 pick 71."""
    cell = DRAFT_CELL.search(html)
    if not cell:
        return []
    out = []
    for i, m in enumerate(DRAFT_LINK.finditer(cell.group(1)), 1):
        href_year, league, body = int(m.group(1)), m.group(2).upper(), text(m.group(3))
        # PFA sometimes puts the ';' separator INSIDE the anchor text. Removing a
        # delimiter is not the same as guessing at a value.
        body = re.sub(r"^[;,\s]+", "", body)
        rec = {"printed_order": i, "raw_segment": body,
               "draft_year_from_link": href_year, "league_from_link": league,
               "selection_type": None, "round": None, "overall_pick": None,
               "year": None, "club": None, "parsed": False}
        t = D_TYPE.match(body)
        if t:
            rec["selection_type"] = t.group(1)
        else:
            r = D_ROUND.match(body)
            if r:
                rec["round"] = int(r.group(1))
        p = D_PICK.search(body)
        if p:
            rec["overall_pick"] = int(p.group(1))
        tail = D_TAIL.search(body)
        if tail:
            rec["year"], rec["club"] = int(tail.group(1)), tail.group(2)
        # parsed = we have a club, a year, and EITHER a round or a named type.
        rec["parsed"] = bool(rec["club"] and rec["year"]
                             and (rec["round"] is not None or rec["selection_type"]))
        out.append(rec)
    return out


def draft_claims(sr, pid, html, raw_value):
    """The raw string STAYS. The splits are derived from it and say so; if a split
    is ever found wrong, the source's own words are still there to re-derive from.
    A derived claim that replaces its evidence cannot be audited."""
    claims = [claim(sr, pid, "pfa.draft", raw_value)]
    for d in parse_drafts(html):
        if not d["parsed"]:
            continue
        claims.append({**claim(sr, pid, "pfa.draft_selection", d),
                       "kind": "source_derived",
                       "_derived_from": "pfa.draft",
                       "_raw_parent": raw_value})
    return claims


if __name__ == "__main__":
    o = main()
    c = o["counts"]
    for k, v in c.items():
        if k != "by_predicate":
            print(f"  {k:26s} {v:,}")
    print("  claims by predicate:")
    for k, v in sorted(c["by_predicate"].items(), key=lambda x: -x[1]):
        print(f"     {k:22s} {v:,}")
