"""Ingest English Wikipedia as a claim layer. WRITES to dataset/build/wikipedia.json.

Everything here is attributed and ranked below media guides and contemporary
newspapers. Disagreements with StatsCrew are HELD, never resolved: both values
stay, both attributed.

The five hard rules are enforced HERE, at the write, not checked afterwards:
  - no claim without a source attribution   -> add() is the only door
  - no photograph overwrites one held       -> HELD_PHOTOS consulted per person
  - a fair-use image cannot be EXPRESSED    -> photo_claim raises on the licence
  - an unmatched person produces no claims  -> claims are built inside the match
  - a prose claim records whether it is cited -> `cited` is a required field
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
SRC = "/Users/ryannecci/Documents/pgm3-sources"
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
CLUBS = IDX["_clubs"]
PHOTOS = json.load(open(os.path.join(BASE, "build", "photos.json")))
HELD_PHOTOS = {c["subject"][1] for c in PHOTOS["claims"] if c["predicate"] == "has_photograph"}

# READ FROM THE DECLARATION, never duplicated here. A rule that lives in both
# a declaration and a Python literal drifts -- model.py already proved that with
# the salary conventions, where the two copies disagreed by four predicates.
OK_LICENCE = re.compile(DECL["PHOTOGRAPHS"]["licence_allow_pattern"], re.I)
FAIR_USE = re.compile(DECL["PHOTOGRAPHS"]["licence_refuse_pattern"], re.I)
ERA_CUT = DECL["IDENTITY"]["era_cut"]
GRID = re.compile(r"Infobox (gridiron football|NFL|College football|CFL)|"
                  r"American football (player|coach)|Canadian football", re.I)
FOOT = re.compile(r"football", re.I)


class IngestError(Exception):
    pass


# ---------------------------------------------------------------- identity
def club_names(p):
    """KEY IS {club_code}|{year}. Looking it up as {league}|{year}|{code} returns
    None for every club and silently disables this branch -- which is what
    happened in four earlier probes."""
    out = set()
    for c in p["clubs"]:
        for y in range(p["first"], p["last"] + 1):
            n = CLUBS.get(f"{c}|{y}")
            if n:
                out.add(n)
    return out


def confirm(p, text):
    if not GRID.search(text):
        return False, "not a gridiron biography"
    if any(n and n in text for n in club_names(p)):
        return True, "club named"
    if p["first"] < ERA_CUT:
        return False, "pre-%d and no club named" % ERA_CUT
    if any(str(y) in text for y in range(p["first"], p["last"] + 1)) and FOOT.search(text):
        return True, "year + football context"
    return False, "no club, no year"


# ---------------------------------------------------------------- wikitext
def infobox(t):
    i = t.lower().find("{{infobox")
    if i < 0:
        return ""
    d = 0
    for j in range(i, min(len(t), i + 40000)):
        if t.startswith("{{", j): d += 1
        elif t.startswith("}}", j):
            d -= 1
            if d == 0: return t[i:j + 2]
    return t[i:i + 40000]


def params(ib):
    body = ib[2:-2] if ib.endswith("}}") else ib[2:]
    out, cur, parts, d, b, i = {}, "", [], 0, 0, 0
    while i < len(body):
        if body.startswith("{{", i): d += 1; cur += "{{"; i += 2; continue
        if body.startswith("}}", i): d -= 1; cur += "}}"; i += 2; continue
        if body.startswith("[[", i): b += 1; cur += "[["; i += 2; continue
        if body.startswith("]]", i): b -= 1; cur += "]]"; i += 2; continue
        c = body[i]
        if c == "|" and d == 0 and b == 0: parts.append(cur); cur = ""
        else: cur += c
        i += 1
    parts.append(cur)
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out


def plain(v):
    v = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", v, flags=re.S)
    v = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", v)
    v = re.sub(r"\{\{[Bb]irth date(?: and age)?\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}",
               r"\1-\2-\3", v)
    v = re.sub(r"\{\{[Dd]eath date(?: and age)?\|(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}",
               r"\1-\2-\3", v)
    v = re.sub(r"\{\{[^}]*\}\}", " ", v)
    v = re.sub(r"'''|''|<[^>]+>", "", v)
    return re.sub(r"\s+", " ", v).strip(" ,.")


FIELDS = {
    "death_date": "wikipedia.death_date", "death_place": "wikipedia.death_place",
    "birth_place": "wikipedia.birth_place", "birth_date": "wikipedia.birth_date",
    "high_school": "wikipedia.high_school", "draftyear": "wikipedia.draft_year",
    "draftround": "wikipedia.draft_round", "draftpick": "wikipedia.draft_pick",
    "pastteams": "wikipedia.club_career", "teams": "wikipedia.club_career",
    "pastcoaching": "wikipedia.post_playing_career",
    "coaching": "wikipedia.post_playing_career",
}
SECTIONS = ("Early life", "Personal life", "Early years", "Later life")


class WikiStore:
    def __init__(self):
        self.claims = []
        self.source_records = {}
        self.matched = set()
        self.photo_added = set()

    def record(self, title):
        sr = f"wikipedia-en#{title}"
        self.source_records[sr] = {"source_id": "wikipedia-en", "locator": title}
        return sr

    def add(self, sr, person, predicate, value, **extra):
        """The only door. A claim without an attributed source cannot be made."""
        if not sr or sr not in self.source_records:
            raise IngestError("claim without a resolvable source record")
        if person not in self.matched:
            raise IngestError(f"{person} is UNMATCHED; it may produce no claims")
        c = {"source_record": sr, "source_id": "wikipedia-en",
             "stated_by": "English Wikipedia", "attribution": ["English Wikipedia"],
             "subject": ["person", person], "predicate": predicate,
             "value": value, "kind": "observed", "observed_at": "fetched-2026-09"}
        c.update(extra)
        self.claims.append(c)
        return c

    def photo(self, sr, person, filename, licence):
        """Gap-fill only, and a fair-use image is INEXPRESSIBLE -- there is no
        path through this function that yields a claim for one."""
        if FAIR_USE.search(licence or ""):
            raise IngestError(f"fair-use image refused: {filename} ({licence})")
        if not OK_LICENCE.search(licence or ""):
            raise IngestError(f"licence not public domain or open CC: {filename} ({licence})")
        if person in HELD_PHOTOS:
            raise IngestError(f"{person} already holds a photograph; gap-fill only")
        self.photo_added.add(person)
        return self.add(sr, person, "wikipedia.photograph", filename,
                        note=f"licence: {licence}")


def extract(ws, sr, pid, title, text):
    n = collections.Counter()
    ib = infobox(text)
    P = params(ib)
    for k, pred in FIELDS.items():
        v = P.get(k, "")
        if not v.strip():
            continue
        val = plain(v)
        if not val:
            continue
        ws.add(sr, pid, pred, val[:400], cited=bool(re.search(r"<ref", v, re.I)))
        n[pred] += 1
    # ---- prose, with its citation ----
    for sec in SECTIONS:
        m = re.search(r"==\s*" + sec + r"\s*==(.*?)(?=\n==|\Z)", text, re.S | re.I)
        if not m:
            continue
        body = re.sub(r"\n+", " ", m.group(1))
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", body):
            raw = s
            txt = plain(s)
            if len(txt) < 40:
                continue
            refs = re.findall(r"<ref[^>]*>(.*?)</ref>", raw, re.S)
            cite = plain(refs[0])[:300] if refs else None
            ws.add(sr, pid, "wikipedia.prose", txt[:600],
                   section=sec, cited=bool(refs), citation=cite)
            n["wikipedia.prose"] += 1
    # ---- the reference list itself, held independently of the claims ----
    for r in re.findall(r"<ref[^>]*>(.*?)</ref>", text, re.S):
        low = r.lower()
        kind = ("newspaper" if re.search(r"\{\{\s*cite news|newspapers\.com", low)
                else "book" if re.search(r"\{\{\s*cite book", low)
                else "pfr" if "pro-football-reference" in low
                else "web" if re.search(r"\{\{\s*cite web", low)
                else "other")
        named = bool(re.search(r"\|\s*(newspaper|work|publisher|title)\s*=", low))
        dated = bool(re.search(r"\|\s*date\s*=\s*\S", low))
        ws.add(sr, pid, "wikipedia.reference", plain(r)[:400],
               ref_kind=kind, locatable=bool(named and dated), cited=True)
        n["wikipedia.reference"] += 1
    return n
