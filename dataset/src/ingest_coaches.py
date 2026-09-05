"""Ingest coaching data from three sources into one season-agnostic store.

Assistant identity rests on stint_continuity, not birth date (media-guide
declaration). Where a birth date exists it is used AND the denotation records
WHICH source's value it matched against, because a contested discriminator is
inherited by the denotation resting on it.
"""
import os, sys, re, json, glob, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from model import Store
import fetch_statscrew as F

BASE = os.path.join(HERE, "..")
SRC = os.environ.get("PGM3_SOURCES", os.path.expanduser("~/Documents/pgm3-sources"))
LOG = []
def log(m): print(m, flush=True); LOG.append(m)


def norm(n):
    return re.sub(r"[^a-z ]", "", (n or "").lower()).strip()


def ingest_coachingtree(store, index):
    d = json.load(open(os.path.join(BASE, "declarations", "coaching-tree.json")))
    store.add_source(d)
    n_c = n_s = 0
    for f in sorted(glob.glob(os.path.join(SRC, "coachingtree", "*.json"))):
        j = json.load(open(f))
        if not isinstance(j, dict) or not j.get("name"):
            continue
        slug = j["slug"]
        sr = store.add_source_record("coaching-tree", f"coach/{slug}")
        key = (norm(j["name"]), j.get("birth_date"))
        p = index.get(key)
        if p is None:
            p = store.mint_person(); index[key] = p
        store.declare_subject(("person", p))
        store.add_denotation(sr, p, ["name", "birth_date"], "attribute-match",
                             matched_against=f"coaching-tree:{slug} birth_date={j.get('birth_date')}",
                             note="slug is name-derived and carries no counter; it is a "
                                  "within-source key, not cross-source evidence")
        n_c += 1
        for pred, val in (("birth_date", j.get("birth_date")), ("birthplace", j.get("birthplace")),
                          ("college", j.get("college"))):
            if val: store.add_claim(sr, ("person", p), pred, val, "fetch-2026")
        for st in (j.get("stints") or []):
            yr, team = st.get("year"), st.get("team")
            if not yr or not team: continue
            subj = ("stint", p, team, f"y{yr}")
            store.declare_subject(subj)
            for role in (st.get("roles") or []):
                store.add_claim(sr, subj, "role_title", role, "fetch-2026")
                n_s += 1
            store.add_claim(sr, subj, "is_head_coach", bool(st.get("is_head_coach")), "fetch-2026")
    log(f"coaching-tree: {n_c} coaches, {n_s} role claims")


def ingest_pre1936(store, index):
    d = json.load(open(os.path.join(BASE, "declarations", "pre1936-assistants.json")))
    store.add_source(d)
    path = os.path.join(SRC, "DocDump", "pre1936_nfl_assistant_coaches.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    split = 0
    for i, r in enumerate(rows):
        sr = store.add_source_record("pre1936-assistants", f"row{i+1}")
        bd = (r["birth_date"] or "").strip() or None
        key = (norm(r["full_name"] or r["assistant_name"]), bd)
        p = index.get(key)
        if p is None:
            p = store.mint_person(); index[key] = p
        store.declare_subject(("person", p))
        disc = ["name", "birth_date"] if bd else ["name", "stint_continuity"]
        store.add_denotation(sr, p, disc, "attribute-match",
                             matched_against=f"pre1936:{r['primary_source']} birth_date={bd}",
                             note=None if bd else "no birth date; known_coaching_lineage supplies continuity")
        for col, pred in (("full_name","full_name"),("birth_date","birth_date"),
                          ("birthplace","birthplace"),("death_date","death_date"),
                          ("college","college"),("high_school","high_school")):
            v = (r[col] or "").strip()
            if v: store.add_claim(sr, ("person", p), pred, v, r["year"],
                                  attribution=[r["primary_source"]])
            elif col in ("birth_date","birthplace","death_date","college"):
                store.add_absence(sr, ("person", p), pred, r["year"],
                                  note="column present in the CSV, cell blank")
        subj = ("stint", p, r["team"], f"y{r['year']}")
        store.declare_subject(subj)
        title = (r["title"] or "").strip()
        # DEFECT in the source: 'Assistant Coach / later Head Coach' conflates a
        # stint fact with a career fact. Split; the career half is NOT this season.
        if "/ later" in title:
            this_season, career = [x.strip() for x in title.split("/ later", 1)]
            store.add_claim(sr, subj, "role_title", this_season, r["year"],
                            attribution=[r["primary_source"]])
            store.add_claim(sr, ("person", p), "later_became", career, r["year"],
                            note="split from a title field that conflated a stint fact with a career fact")
            split += 1
        else:
            store.add_claim(sr, subj, "role_title", title, r["year"],
                            attribution=[r["primary_source"]])
        if r["known_coaching_lineage"]:
            store.add_claim(sr, ("person", p), "coaching_lineage",
                            r["known_coaching_lineage"], r["year"],
                            attribution=[r["primary_source"]])
    log(f"pre1936-assistants: {len(rows)} rows, {split} conflated titles split")


def ingest_statscrew_1950_coaches(store, index):
    """Head coaches named on the 1950 team roster pages, resolved through c- slugs."""
    if "statscrew" not in store.sources:
        store.add_source(json.load(open(os.path.join(BASE, "declarations", "statscrew.json"))))
    found = 0
    for team in F.teams_in("NFL", 1950):
        page = F.team_roster(team, 1950)
        m = re.search(r"Coach:\s*(?:<[^>]+>\s*)*<a[^>]*href=\"[^\"]*/football/stats/(c-[a-z0-9\-]+)\"[^>]*>([^<]+)</a>", page)
        if not m:
            m2 = re.search(r"Coach:\s*(?:<[^>]+>\s*)*([A-Z][A-Za-z.' -]{3,30})", page)
            log(f"  {team}: coach named but no c- link" if m2 else f"  {team}: no coach line")
            continue
        slug, name = m.group(1), m.group(2).strip()
        info = F.parse_person(F.person(slug))
        if not info["is_real"]:
            log(f"  {team}: {slug} is a phantom page - skipped"); continue
        bd = info.get("born") or None
        key = (norm(name), None)
        # try to join to an existing person by name+birth-date first
        joined = None
        for (n, b), pid in index.items():
            if n == norm(name) and b and bd and b[:4] and bd.endswith(b[:4]):
                joined = pid; break
        p = joined or store.mint_person()
        index.setdefault((norm(name), bd), p)
        store.declare_subject(("person", p))
        sr = store.add_source_record("statscrew", f"person/{slug}")
        store.add_denotation(sr, p, ["source_native_id"], "exact-id",
                             matched_against=f"statscrew:{slug} born={bd}")
        if bd: store.add_claim(sr, ("person", p), "birth_date", bd, 1950)
        if info.get("college"): store.add_claim(sr, ("person", p), "college", info["college"], 1950)
        subj = ("stint", p, team, "y1950")
        store.declare_subject(subj)
        store.add_claim(sr, subj, "role_title", "Head Coach", 1950)
        store.add_claim(sr, subj, "is_head_coach", True, 1950)
        found += 1
    log(f"statscrew 1950 head coaches: {found}/13")


def main():
    store = Store()
    index = {}
    ingest_coachingtree(store, index)
    ingest_pre1936(store, index)
    ingest_statscrew_1950_coaches(store, index)
    store.save(os.path.join(BASE, "build", "coaches.json"))
    log(f"TOTAL persons {len(store.persons)}  claims {len(store.claims)}  "
        f"denotations {len(store.denotations)}  universe {len(store.universe)}")
    open(os.path.join(BASE, "build", "ingest-coaches.log"), "w").write("\n".join(LOG))

if __name__ == "__main__":
    main()
