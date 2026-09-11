"""What the ambiguous player leads carry BESIDES a name and a year. Measurement only.

    python3 src/measure_ambiguous_leads.py            # print the table
    python3 src/measure_ambiguous_leads.py --write    # also build-reports/ambiguous-leads-evidence.json

WHY. promote_players refuses a lead whose printed name more than one held person carries.
747 are refused that way. Split by era alone (2026-09-11): 395 have exactly one candidate
playing within three years, 116 several, 236 none. Ryan's question before ruling on the
395: is era really the only evidence, or do the leads carry more? Four kinds, strongest
first:

  CLUB-SEASON    a candidate already on the lead's club-season. Measured 0.
  SOURCE ID      PFA's own player code. The team pages link each name to
                 /players/<x>/<code>.html; the lead never recorded it, the page on disk
                 still has it. Settles without judgement, as it did for the gamelogs.
  COLLEGE/BIRTH  two independent facts agreeing. College through readings.college (the
                 declared fold), birth year against the printed age.
  ADJACENT       a candidate on the SAME CLUB within three years -- Ryan's open question;
                 the club does the work rather than the calendar.

THE JOIN IS ON lead_ref. The 9 September split joined on (store, name) and pooled every
same-named lead's club-seasons for 527 of 747 cases; that is why it said 362/225/158.

Nothing is placed and no store is written.
"""
import os, re, sys, json, html, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, readings
import index_io as IO

PROM = os.path.join(BASE, "build", "player-promotions.json")
PAGES = os.path.expanduser("~/Documents/pgm3-sources/pfa-team-seasons")
OUT = os.path.join(BASE, "build-reports", "ambiguous-leads-evidence.json")
ROW = re.compile(r"<tr.*?</tr>", re.S | re.I)
LINK = re.compile(r'<a href="/?players/[a-z]/([a-z0-9]+)\.html"[^>]*>(.*?)</a>', re.S | re.I)


def _txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def families(conn):
    f = json.loads(dict(conn.execute("SELECT key, value FROM meta"))["predicate_families"])
    return f["birth_date"]["predicates"], f["college"]["predicates"]


def main(argv):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    BIRTH, COLLEGE = families(conn)
    IDX = IO.load_index(); IDX.pop("_clubs", None)
    amb = json.load(open(PROM))["ambiguous"]

    leads = {}
    for st in {a["store"] for a in amb}:
        for l in json.load(open(os.path.join(BASE, "build", f"{st}.json"))).get("leads", []):
            leads[(st, l.get("lead_id"))] = l
    missing = [a for a in amb if (a["store"], a["lead_ref"]) not in leads]
    if missing:
        raise SystemExit(f"{len(missing)} ambiguous rows name a lead their store does not hold -- "
                         "an absent lead must not read as a lead with no evidence")

    # WHO HOLDS EACH PFA CODE, archive-wide -- from the claims' own source records and
    # from the stint's pfa_code. Not only the candidates: a code held by a man of another
    # name is itself a finding.
    code_to = collections.defaultdict(set)
    for person, sr in conn.execute(
            "SELECT DISTINCT person, source_record FROM claim WHERE person IS NOT NULL "
            "AND source_record LIKE 'pro-football-archives#players/%'"):
        m = re.search(r"players/[a-z]/([a-z0-9]+)\.html", sr)
        if m: code_to[m.group(1)].add(person)
    for pid, r in IDX.items():
        for s in (r.get("seasons") or {}).values():
            c = ((s or {}).get("stint") or {}).get("pfa.roster_membership", {})
            if isinstance(c, dict) and c.get("pfa_code"): code_to[c["pfa_code"]].add(pid)

    def seasons(pid):
        out = []
        for k in (IDX.get(pid) or {}).get("seasons") or {}:
            p = str(k).split("|")
            if len(p) >= 3 and p[1].isdigit(): out.append((int(p[1]), p[2]))
        return out

    def vals(pid, preds):
        person = (IDX.get(pid) or {}).get("person") or {}
        return [str(v) for p in preds for v in (person.get(p) or [])]

    def birth_years(pid):
        return {int(y) for v in vals(pid, BIRTH) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", v)}

    def colleges(pid):
        return {readings.college(v) for v in vals(pid, COLLEGE) if v and v != "None"} - {None, ""}

    page_cache, page_missing = {}, set()

    def code_on_page(page, name):
        if page not in page_cache:
            fp = os.path.join(PAGES, page)
            if not os.path.exists(fp):
                page_missing.add(page); page_cache[page] = None
            else:
                rows = []
                for r in ROW.findall(open(fp, errors="replace").read()):
                    m = LINK.search(r)
                    if m: rows.append((_txt(m.group(2)), m.group(1)))
                page_cache[page] = rows
        rows = page_cache[page]
        if rows is None: return "page missing", None
        hits = {c for n, c in rows if n.lower() == name.lower()}
        if not hits: return "name not linked on page", None
        if len(hits) > 1: return "two linked rows of that name", None
        return "linked", hits.pop()

    out, T = [], collections.defaultdict(collections.Counter)
    for a in amb:
        L = leads[(a["store"], a["lead_ref"])]
        po = L.get("places_on") or {}
        cs = po.get("club_season") or ""
        y = po.get("year") or int(re.search(r"\|(\d{4})\|", cs).group(1))
        club = cs.split("|")[-1]
        rl = L.get("roster_line") or {}
        cands = a["held_candidates"]
        near = [p for p in cands if any(abs(v - y) <= 3 for v, _ in seasons(p))]
        g = "one" if len(near) == 1 else "several" if near else "none"
        t = T[g]; t["leads"] += 1
        rec = {"store": a["store"], "lead_ref": a["lead_ref"], "name": a["name_as_printed"],
               "year": y, "club_season": cs, "group": g, "candidates": cands, "near": near}

        # SOURCE ID
        if a["store"] == "pfa-club-rosters" and rl.get("page"):
            state, code = code_on_page(rl["page"], a["name_as_printed"])
            rec["pfa_code_state"], rec["pfa_code"] = state, code
            t["pfa: " + state] += 1
            if code:
                holders = code_to.get(code, set())
                on = [p for p in cands if p in holders]
                rec["pfa_code_held_by"] = sorted(holders)
                if len(on) == 1 and g == "one" and on == near: k = "code -> the one candidate in era"
                elif len(on) == 1 and g == "one": k = "code -> a candidate OUTSIDE era"
                elif len(on) == 1: k = "code -> exactly one candidate"
                elif len(on) > 1: k = "code -> several candidates"
                elif holders: k = "code -> a held man of ANOTHER name"
                else: k = "code -> held by nobody"
                rec["pfa_code_says"] = k; t[k] += 1
        else:
            t["no page to read a code from"] += 1

        # COLLEGE, against every candidate and the one in era
        col = rl.get("College") or rl.get("college_as_printed")
        if col:
            lc = readings.college(col)
            agree = [p for p in cands if lc in colleges(p)]
            have = [p for p in cands if colleges(p)]
            rec["college"] = {"printed": col, "agrees_with": agree, "candidates_holding_a_college": have}
            t["has college"] += 1
            if len(agree) == 1: t["college agrees with exactly one candidate"] += 1
            elif agree: t["college agrees with several"] += 1
            elif have: t["college disagrees with every candidate holding one"] += 1
            else: t["no candidate holds a college"] += 1
            if g == "one" and near[0] in agree: t["college agrees with the one in era"] += 1
            if g == "one" and colleges(near[0]) and near[0] not in agree:
                t["college CONTRADICTS the one in era"] += 1

        # BIRTH YEAR from the printed age
        age = str(rl.get("Age") or "").strip()
        if age.isdigit():
            lo, hi = y - int(age) - 1, y - int(age)
            agree = [p for p in cands if any(lo <= b <= hi for b in birth_years(p))]
            have = [p for p in cands if birth_years(p)]
            rec["age"] = {"printed": age, "birth_year_range": [lo, hi], "agrees_with": agree}
            t["has age"] += 1
            if len(agree) == 1: t["age agrees with exactly one candidate"] += 1
            elif agree: t["age agrees with several"] += 1
            elif have: t["age disagrees with every candidate holding a birth date"] += 1
            else: t["no candidate holds a birth date"] += 1
            if g == "one" and near[0] in agree: t["age agrees with the one in era"] += 1
            if g == "one" and birth_years(near[0]) and near[0] not in agree:
                t["age CONTRADICTS the one in era"] += 1

        # ADJACENT SEASON OF THE SAME CLUB
        adj = [p for p in cands if any(c == club and 0 < abs(v - y) <= 3 for v, c in seasons(p))]
        rec["same_club_within_3"] = adj
        if len(adj) == 1: t["same club within 3 years: exactly one candidate"] += 1
        elif adj: t["same club within 3 years: several"] += 1

        if rl.get("Pos") or rl.get("position_as_printed") or L.get("position_as_printed"): t["has position"] += 1
        if rl.get("jersey_as_printed") or rl.get("No") or rl.get("#"): t["has jersey"] += 1

        # NOTHING BUT A NAME AND A YEAR
        rec["only_name_and_year"] = not (rec.get("pfa_code") or col or age.isdigit())
        if rec["only_name_and_year"]: t["carries NOTHING beyond name and year"] += 1
        out.append(rec)

    for g in ("one", "several", "none"):
        print(f"\n== {g.upper()} candidate(s) within three years: {T[g]['leads']} leads")
        for k, v in sorted(T[g].items(), key=lambda kv: (-kv[1], kv[0])):
            if k != "leads": print(f"   {v:>4}  {k}")
    if page_missing: print(f"\nPAGES MISSING: {len(page_missing)} -- {sorted(page_missing)[:5]}")
    if "--write" in argv:
        json.dump({"_what": __doc__.split("\n\n")[0], "measured_on": dict(conn.execute(
            "SELECT key, value FROM meta WHERE key IN ('snapshot_id','built_at')")),
                   "totals": {g: dict(c) for g, c in T.items()}, "leads": out},
                  open(OUT + ".tmp", "w"), indent=1)
        os.replace(OUT + ".tmp", OUT); print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
