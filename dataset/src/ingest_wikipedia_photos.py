"""Backfill photographs from English Wikipedia for people who hold none.

WHY A SECOND WIKIPEDIA INGEST. ingest_wikipedia.py read 2,183 of the 8,137 confirmed
articles. The other 5,954 were confirmed to exist and never fetched, so their images
were never looked at. This reads the whole cache -- which, since 2026-09-06, includes
the sweep fetch of 9,658 further articles and 1,838 image licences.

THE FOUR RULES, each enforced at the write and not checked afterwards:

  GAP-FILL ONLY. HELD is every person holding a photograph in ANY build file other
  than the one this run writes. A person in HELD cannot reach photo() -- it raises.
  The before/after count is written into the build so the claim "nothing was
  overwritten" is arithmetic rather than assertion. (The first version built HELD
  from two named files and so double-counted the 432 already landed in
  wikipedia-photos-backfill.json; a photograph is held wherever it is held.)

  LICENCE IS RECORDED, NOT JUST TESTED. Open CC carries attribution conditions public
  domain does not. A photograph whose licence is not stored cannot be used safely
  later, so the licence string is a first-class field, kept RAW as the source wrote it.
  'No restrictions' stays 'No restrictions'.

  FAIR USE IS INEXPRESSIBLE. photo() raises on it. There is no path to a claim.

  AN UNRECOGNISED LICENCE IS NOT A REFUSED ONE. Anything the declaration's allow
  pattern does not name, and that is not fair use, is held in `unrecognised_licence`
  for a ruling and NOT ingested. On 2026-09-06 Ryan ruled 'No restrictions' and 'GFDL'
  in; the declaration's pattern now names them, family `free-other`.

THE EVIDENCE IS THE SOURCE'S OWN, AND SAYS WHICH. A PSF photo rests on a filename
matching a name. This rests on the image sitting inside that man's own article and
-- before era_cut -- on that article naming his club. Two tiers, `club-named` and
`name-unique`, written on the claim AND the denotation as `evidence_tier`, so a
reader tells them apart without re-deriving anything. RULED 2026-09-06: name-unique
is ingested, separately, never before era_cut.

  python3 src/ingest_wikipedia_photos.py [--write]     writes build/wikipedia-photos-sweep.json
"""
import os, re, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
CACHE = os.path.expanduser("~/Documents/pgm3-sources/wiki_cache")
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
CLUBS = IDX.pop("_clubs", {})
OUT_NAME = "wikipedia-photos-sweep.json"
OUT = os.path.join(BASE, "build", OUT_NAME)
PHOTO_PREDS = ("has_photograph", "wikipedia.photograph")

# read from the declaration, never duplicated here
OK_LICENCE = re.compile(DECL["PHOTOGRAPHS"]["licence_allow_pattern"], re.I)
FAIR_USE = re.compile(DECL["PHOTOGRAPHS"]["licence_refuse_pattern"], re.I)
GRID = re.compile(DECL["PHOTOGRAPHS"]["infobox_allow_pattern"], re.I)
BASE_GRID = re.compile(DECL["PHOTOGRAPHS"]["infobox_base_pattern"], re.I)   # pre-extension: what "admitted only by the extension" is measured against
ERA_CUT = DECL["IDENTITY"]["era_cut"]
PD = re.compile(r"public domain|^pd\b|^pd-", re.I)
FREE_OTHER = re.compile(r"^no restrictions$|^gfdl$", re.I)
NO_ATTRIBUTION = re.compile(r"public domain|^pd\b|^pd-|cc0|^no restrictions$", re.I)
COLLEGE_COACH = re.compile(r"Infobox college coach", re.I)

from wiki_api import infobox_image      # ONE reader, imported; see wiki_api for the four forms it reads


class IngestError(Exception):
    pass


def nk(s):
    s = re.sub(r"\(.*?\)", " ", str(s or ""))
    return re.sub(r"[^a-z]", "", s.lower())


def norm_img(fn):
    fn = re.sub(r"^\s*(File|Image):", "", fn or "", flags=re.I).strip().replace("_", " ")
    return fn.lower()


def era(y):
    return ("1920s (pre-1931)" if y < 1931 else "1930s" if y < 1941 else "1940s" if y < 1951 else
            "1950s" if y < 1961 else "1960s" if y < 1971 else "1970s" if y < 1981 else
            "1980s" if y < 1991 else "1990s" if y < 2001 else "2000s" if y < 2011 else "2010s+")


def held_photographs():
    """Every person who already holds a photograph, in ANY build file but this run's."""
    held = set()
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        if os.path.basename(f) == OUT_NAME: continue
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if c.get("predicate") in PHOTO_PREDS: held.add(c["subject"][1])
    return held


def scan_cache():
    """Every cached article with text, plus every cached image licence."""
    arts, lic = {}, {}
    for f in glob.glob(CACHE + "/*.json"):
        try: d = json.load(open(f))
        except Exception: continue
        for _, pg in ((d.get("query") or {}).get("pages") or {}).items():
            for e in (pg.get("imageinfo") or []):
                em = e.get("extmetadata") or {}
                L = (em.get("LicenseShortName") or {}).get("value") or ""
                if L:
                    lic[norm_img(re.sub(r"^File:", "", pg.get("title") or ""))] = L
            if "missing" in pg or "invalid" in pg: continue
            revs = pg.get("revisions") or []
            txt = ""
            if revs:
                r0 = revs[0]
                txt = r0.get("*") or (r0.get("slots", {}).get("main", {}) or {}).get("*") or ""
            if not txt: continue
            m = infobox_image(txt)
            arts[pg.get("title")] = {"grid": bool(GRID.search(txt)),
                                     "college_coach_only": bool(COLLEGE_COACH.search(txt)),
                                     "img": m, "txt": txt}
    return arts, lic


def people():
    A, byname = {}, collections.defaultdict(list)
    for pid, p in IDX.items():
        if not isinstance(p, dict): continue
        yrs, clubs = set(), set()
        se = p.get("seasons") or {}
        for key in (se.keys() if isinstance(se, dict) else []):
            pp = str(key).split("|")
            if len(pp) == 3 and pp[1].lstrip("yY").isdigit():
                y = int(pp[1].lstrip("yY")); yrs.add(y)
                cn = CLUBS.get(f"{pp[2]}|{y}")
                if cn: clubs.add(cn)
        if not yrs: continue
        A[pid] = {"name": p.get("name"), "first": min(yrs), "clubs": clubs}
        byname[nk(p.get("name"))].append(pid)
    return A, byname


def licence_family(L):
    if PD.search(L): return "public-domain"
    if FREE_OTHER.search(L): return "free-other"
    return "open-cc"


class Out:
    def __init__(self, held):
        self.held = held; self.claims = []; self.denotations = []
        self.refused = {"fair_use": [], "unrecognised_licence": [], "already_held": []}
        self.n = collections.Counter()

    def photo(self, title, pid, filename, licence, method, discriminator, tier):
        if pid in self.held:
            raise IngestError(f"{pid} already holds a photograph; gap-fill only")
        if FAIR_USE.search(licence or ""):
            raise IngestError(f"fair-use image refused: {filename} ({licence})")
        if not OK_LICENCE.search(licence or ""):
            raise IngestError(f"licence not recognised as free: {filename} ({licence})")
        sr = f"wikipedia-en#{title}"
        self.claims.append({
            "source_record": sr, "source_id": "wikipedia-en", "stated_by": "English Wikipedia",
            "attribution": ["English Wikipedia"], "subject": ["person", pid],
            "predicate": "wikipedia.photograph", "value": filename,
            "licence": licence,                      # RAW, as the source wrote it
            "licence_family": licence_family(licence),
            "attribution_required": not bool(NO_ATTRIBUTION.search(licence)),
            "evidence_tier": tier,
            "kind": "observed", "observed_at": "fetched-2026-09",
            "note": f"licence: {licence}; evidence: {method}"})
        self.denotations.append({
            "person": pid, "source_record": sr, "method": method, "evidence_tier": tier,
            "discriminator": discriminator, "matched_against": f"wikipedia-en:{title}",
            "status": "asserted",
            "note": "the image sits inside this man's own article; this is the SOURCE'S "
                    "association, not a filename match. Stronger than psf-photos tier 3, "
                    "and still not a verified face."})
        self.held.add(pid)
        self.n["written"] += 1


def main():
    write = "--write" in sys.argv
    held_before = held_photographs()
    A, byname = people()
    arts, lic = scan_cache()
    out = Out(set(held_before))
    n = collections.Counter()
    by_era = collections.Counter(); by_family = collections.Counter(); by_tier = collections.Counter()
    era_family = collections.defaultdict(collections.Counter)
    ruled_in = {"free_other_licences": [], "college_coach_infobox": []}
    for title, v in arts.items():
        if not v["grid"] or not v["img"]: continue
        n["article_with_image"] += 1
        cands = byname.get(nk(title)) or []
        if not cands:
            n["no_person_of_that_name"] += 1; continue
        txt = v["txt"]
        if len(cands) > 1:
            hit = [p for p in cands if any(c and c in txt for c in A[p]["clubs"])]
            if len(hit) != 1:
                n["ambiguous_name"] += 1; continue
            cands = hit
        pid = cands[0]
        club_named = any(c and c in txt for c in A[pid]["clubs"])
        if A[pid]["first"] < ERA_CUT and not club_named:
            n["pre_era_cut_club_not_named"] += 1; continue
        # admitted ONLY by the college-coach extension? 'Infobox college coach' is
        # sport-agnostic (measured: it let in basketball coaches on name alone), so it
        # is taken only on club-named evidence, whatever the era.
        ext_only = bool(COLLEGE_COACH.search(txt)) and not BASE_GRID.search(txt)
        if ext_only and not club_named:
            out.refused.setdefault("college_coach_not_club_named", []).append(
                {"person": pid, "name": A[pid]["name"], "first_season": A[pid]["first"],
                 "title": title, "image": v["img"],
                 "_why": "Infobox college coach without the club named; sport unconfirmed"})
            n["college_coach_infobox_not_club_named"] += 1; continue
        n["resolved"] += 1
        L = lic.get(norm_img(v["img"]))
        if not L:
            n["no_licence_data"] += 1; continue
        if pid in out.held:
            out.refused["already_held"].append({"person": pid, "title": title})
            n["skipped_already_held"] += 1; continue
        tier = "club-named" if club_named else "name-unique"
        method = f"article-subject+{tier}"
        disc = (["article_subject", "club_named_in_article"] if club_named
                else ["article_subject", "name_unique_in_person_universe"])
        try:
            out.photo(title, pid, v["img"], L, method, disc, tier)
        except IngestError as e:
            msg = str(e)
            if "fair-use" in msg:
                out.refused["fair_use"].append({"person": pid, "title": title, "image": v["img"], "licence": L})
                n["refused_fair_use"] += 1
            else:
                out.refused["unrecognised_licence"].append({"person": pid, "title": title, "image": v["img"], "licence": L})
                n["refused_unrecognised_licence"] += 1
            continue
        e = era(A[pid]["first"]); fam = licence_family(L)
        by_era[e] += 1; by_family[fam] += 1; by_tier[tier] += 1; era_family[e][fam] += 1
        rec = {"person": pid, "name": A[pid]["name"], "first_season": A[pid]["first"],
               "title": title, "image": v["img"], "licence": L, "evidence_tier": tier}
        if fam == "free-other": ruled_in["free_other_licences"].append(rec)
        if v["college_coach_only"] and not re.search(
                r"Infobox (gridiron football|NFL|College football|CFL)|American football (player|coach)|Canadian football", txt, re.I):
            ruled_in["college_coach_infobox"].append(rec)
    held_after = set(held_before) | {c["subject"][1] for c in out.claims}
    doc = {
        "source": {"source_id": "wikipedia-en", "name": "English Wikipedia",
                   "acquisition": "fetched", "stated_by": "English Wikipedia",
                   "licence": "CC BY-SA; reuse permitted with attribution",
                   "access": "MediaWiki API, User-Agent with contact, batched 50/request, ~1/s",
                   "scope": "photographs only; every cached article -- the original 8,038 plus the "
                            "9,658 fetched in the 2026-09-06 sweep -- for people holding no photograph "
                            "in any build file",
                   "_touches_no_game_file": "writes dataset/build/ only; _verified_keys live in the "
                            "GAME roster files under tools/ and are not read or written here"},
        "run": {"date": "2026-09-06", "session": "yearbooks",
                "rulings_applied": ["unrecognised licences 'No restrictions' and 'GFDL' INCLUDED, raw string kept",
                                    "infobox filter EXTENDED to 'Infobox college coach', NOT to 'sportsperson'",
                                    "name-unique evidence INGESTED on its own tier, never before era_cut"],
                "declaration": "declarations/wikipedia.json PHOTOGRAPHS"},
        "claims": out.claims, "denotations": out.denotations, "refused": out.refused,
        "ruled_in": ruled_in,
        "gap_fill_proof": {
            "people_holding_a_photograph_BEFORE": len(held_before),
            "photographs_written": len(out.claims),
            "people_holding_a_photograph_AFTER": len(held_after),
            "arithmetic": f"{len(held_before)} + {len(out.claims)} = {len(held_after)}",
            "overwritten": len(held_before) - len(held_before & held_after),
            "_meaning": "overwritten must be 0. Every person held before is still held, "
                        "and the count rose by exactly the number of new photographs. BEFORE "
                        "counts every build file, including wikipedia-photos-backfill.json."},
        "counts": dict(n),
        "by_era": {e: {"written": by_era[e], **dict(era_family[e])} for e in sorted(by_era)},
        "by_licence_family": dict(by_family),
        "by_evidence_tier": dict(by_tier)}
    if write:
        IO.dump_atomic(doc, OUT, indent=1)
    for k, v in sorted(n.items()): print(f"  {k:34s} {v}")
    g = doc["gap_fill_proof"]
    print(f"\n  gap-fill: {g['arithmetic']}   overwritten={g['overwritten']}")
    print(f"  by family: {dict(by_family)}   by tier: {dict(by_tier)}")
    print(f"  ruled in: free-other {len(ruled_in['free_other_licences'])}, college-coach infobox {len(ruled_in['college_coach_infobox'])}")
    if write: print(f"\nwrote build/{OUT_NAME}")
    return doc


if __name__ == "__main__":
    main()
