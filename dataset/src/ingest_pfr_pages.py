"""Pro-Football-Reference pages Ryan saved, read for what they state.

TWO DOCUMENTS, TWO DIFFERENT KINDS OF EVIDENCE, and they are not filed alike.

  1920 Detroit Heralds -- eleven PLAYER pages. PFR's own compilation of vitals for
    men the archive already holds by name. Full name, position, height, weight,
    birth and death date and place, college, high school.

  1934 Cincinnati Reds -- a CLUB-SEASON page. The archive holds 12 men on this
    club-season and every one of them came from a box score; it is one of only
    three club-seasons no source ever gave a roster for. PFR's page is PFR's own
    compilation FROM THE SAME BOX SCORES. It is corroboration OF THE SAME KIND,
    not a second kind, and every claim says so in `_same_evidence_as`. A reader
    counting independent sources would otherwise count one twice.

WHAT IS NOT DONE HERE. No person is promoted. Men PFR names whom the archive does
not hold are written as LEADS, because admitting a person is its own act with its
own route. The 1934 page's roster table is not in the saved copy, so the men read
are those appearing in its passing, rushing-and-receiving or scoring tables.

THE JOIN IS THE RULED ONE, tier by tier, and each claim records which tier placed
it: exact name on the club-season, then exact and unique in the archive, then
surname on the club-season, then nothing.

  python3 src/ingest_pfr_pages.py            read and report
  python3 src/ingest_pfr_pages.py --write    write build/pfr-pages.json
"""
import os, re, sys, json, html, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import sqlite3

SRC_ID = "pro-football-reference"
DOCS = os.path.expanduser("~/Dropbox/Football Archive/docs/hunting")
HERALDS = os.path.join(DOCS, "1920 Heralds Players from PFR")
CIN = os.path.join(DOCS, "1934 Cincinnati Reds Rosters, Stats, Schedule _ Pro-Football-Reference.com.html")
OUT = os.path.join(BASE, "build", "pfr-pages.json")


def flat(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


# ---------------------------------------------------------------- the pages
def heralds_players():
    out = []
    for f in sorted(glob.glob(os.path.join(HERALDS, "*Stats, Height*.html"))):
        h = open(f, errors="ignore").read()
        i = h.find('id="meta"')
        if i < 0: continue
        seg = flat(h[i:i + 2600]).split("More bio")[0]
        disp = re.search(r"<h1>\s*(?:<span>)?(.*?)(?:</span>)?\s*</h1>", h, re.S)
        disp = flat(disp.group(1)) if disp else None
        if not disp: continue
        g = lambda p: (re.search(p, seg) or [None, None])[1]
        rec = {"display": disp, "file": os.path.basename(f),
               "full_name": g(re.escape(disp) + r"\s+([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){1,3})\s+Position"),
               "position": g(r"Position\s*:\s*([A-Z/\-]+)"),
               "height": g(r"\b(\d-\d{1,2})\s*,"), "weight": g(r"(\d{2,3})lb"),
               "college": g(r"College\s*:\s*([A-Za-z .'&\-]+?)\s*(?:High School|More|$)"),
               "high_school": g(r"High School\s*:\s*([A-Za-z .'&\-]+?\([A-Z]{2}\))")}
        b = re.search(r"Born:\s*([A-Za-z]+\s*\d{1,2}\s*,\s*\d{4})(?:\s+in\s+(.+?))?\s*(?:Died|College|High School)", seg)
        if b: rec["birth_date"], rec["birth_place"] = re.sub(r"\s+,", ",", b.group(1)), (b.group(2) or None)
        d = re.search(r"Died:\s*([A-Za-z]+\s*\d{1,2}\s*,\s*\d{4})(?:\s+in\s+(.+?))?\s*(?:College|High School)", seg)
        if d: rec["death_date"], rec["death_place"] = re.sub(r"\s+,", ",", d.group(1)), (d.group(2) or None)
        out.append(rec)
    return out


def cincinnati_men():
    h = open(CIN, errors="ignore").read()
    men = {}
    for tid in ("passing", "rushing_and_receiving", "scoring"):
        m = re.search(r'id="%s".*?</table>' % tid, h, re.S)
        if not m: continue
        for r in re.split(r"<tr\b", m.group(0))[1:]:
            r = r.split("</tr>")[0]
            d = {k: flat(v) for k, v in re.findall(r'data-stat="([^"]+)"[^>]*>(.*?)</t[hd]>', r, re.S)}
            n = d.get("name_display")
            if not n or n in ("Player", "Team Totals", "Opp Totals"): continue
            keep = {k: d[k] for k in ("age", "pos", "games", "games_started") if d.get(k)}
            men.setdefault(n, {}).update(keep)
    return men


# ---------------------------------------------------------------- the join
def roster(conn, league, year, club_id):
    out = {}
    for r in conn.execute("SELECT DISTINCT person FROM claim WHERE scope='stint' AND club_id=? AND year=?", (club_id, year)):
        for n in conn.execute("SELECT DISTINCT name FROM person_name WHERE person=?", (r[0],)):
            out.setdefault(norm(n[0]), set()).add(r[0])
    return out


def place(conn, name, on_club, may_use_archive_wide):
    """(person, tier) under the ruled discipline, or (None, why).

    `may_use_archive_wide` IS FALSE FOR A CLUB-SEASON PLACEMENT, and that is the
    whole point of passing it. Tier 2 -- exact and unique ANYWHERE in the archive --
    is sound for a person-scoped fact about a man the page is already about. It is
    NOT sound for a stint: it would put a man on a club-season no source places him
    on, on the strength of his name being unusual. That is the Jim Talbot mistake in
    a different dress, and the first run of this ingest made it: 18 of the 1934 Reds
    joined against a club-season the archive holds 12 men on.
    """
    n = norm(name)
    if n in on_club and len(on_club[n]) == 1:
        return next(iter(on_club[n])), "exact name on the club-season"
    if may_use_archive_wide:
        ids = {r[0] for r in conn.execute("SELECT DISTINCT person FROM person_name WHERE norm=?",
                                          (" ".join(re.findall(r"[a-z]+", name.lower())),))}
        if len(ids) == 1:
            return next(iter(ids)), "exact and unique in the archive"
    sur = norm(name.split()[-1])
    hits = {p for k, v in on_club.items() if k.endswith(sur) for p in v}
    if len(hits) == 1:
        return next(iter(hits)), "surname on the club-season"
    return None, ("ambiguous on the club-season" if hits else "no man of that name on the club-season")


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    claims, leads = [], []
    n = collections.Counter()

    # ---- 1920 Detroit Heralds
    heralds = roster(conn, "APFA", 1920, "club-detroit-heralds-1920")
    for p in heralds_players():
        pid, tier = place(conn, p["display"], heralds, may_use_archive_wide=True)
        sr = f"{SRC_ID}#hunting/1920-detroit-heralds/{p['file']}"
        if not pid:
            leads.append({"source_id": SRC_ID, "source_record": sr, "name_as_printed": p["display"],
                          "club": "APFA|1920|DE1", "why": tier, "fields": p}); n["heralds_lead"] += 1; continue
        n["heralds_joined"] += 1
        base = {"source_id": SRC_ID, "source_record": sr, "stated_by": "Pro-Football-Reference",
                "attribution": ["Pro-Football-Reference.com"], "kind": "observed",
                "_joined_on": tier}
        for pred, val in (("pfr.full_name", p.get("full_name")), ("pfr.position", p.get("position")),
                          ("pfr.height", p.get("height")), ("pfr.weight", p.get("weight")),
                          ("pfr.birth_date", p.get("birth_date")), ("pfr.death_date", p.get("death_date")),
                          ("pfr.birth_place", p.get("birth_place")), ("pfr.death_place", p.get("death_place")),
                          ("pfr.college", p.get("college")), ("pfr.high_school", p.get("high_school"))):
            if val: claims.append({**base, "subject": ["person", pid], "predicate": pred, "value": val}); n["heralds_claims"] += 1

    # ---- 1934 Cincinnati Reds
    cin = roster(conn, "NFL", 1934, "club-cincinnati-reds-1933")
    SAME = ("PFR's own compilation from the SAME box scores the archive already read for this "
            "club-season. Corroboration of the same kind, not an independent roster.")
    for name, d in sorted(cincinnati_men().items()):
        pid, tier = place(conn, name, cin, may_use_archive_wide=False)
        sr = f"{SRC_ID}#hunting/1934-cincinnati-reds"
        if not pid:
            leads.append({"source_id": SRC_ID, "source_record": sr, "name_as_printed": name,
                          "club": "NFL|1934|CIN", "why": tier, "fields": d}); n["cin_lead"] += 1; continue
        n["cin_joined"] += 1
        base = {"source_id": SRC_ID, "source_record": sr, "stated_by": "Pro-Football-Reference",
                "attribution": ["Pro-Football-Reference.com"], "kind": "observed",
                "_joined_on": tier, "_same_evidence_as": SAME}
        subj = ["stint", pid, "CIN", "NFL-1934"]
        for pred, val in (("pfr.age_that_season", d.get("age")), ("pfr.position", d.get("pos")),
                          ("pfr.games_played", d.get("games")), ("pfr.games_started", d.get("games_started"))):
            if val: claims.append({**base, "subject": subj, "predicate": pred, "value": val}); n["cin_claims"] += 1

    out = {"_what": "Pro-Football-Reference pages, read for what they state. Nothing promoted.",
           "source_id": SRC_ID, "counts": dict(n), "claims": claims, "leads": leads}
    print(f"  1920 Heralds : {n['heralds_joined']} men joined, {n['heralds_lead']} leads, {n['heralds_claims']} claims")
    print(f"  1934 Reds    : {n['cin_joined']} men joined, {n['cin_lead']} leads, {n['cin_claims']} claims")
    print(f"  TOTAL        : {len(claims)} claims, {len(leads)} leads")
    if write:
        json.dump(out, open(OUT, "w"), indent=1); print(f"  -> {OUT}")
    else:
        print("  (dry run; pass --write)")
    return out


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
