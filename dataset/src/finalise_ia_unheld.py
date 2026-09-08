"""Finalise the unheld-archive.org fetch: re-score the sport verdict from the stored
texts, reconcile the index, and produce the byte census.

WHY RE-SCORE. The fetch flags a text as another sport when other-sport vocabulary
outnumbers football vocabulary. That is right for the trap it guards -- an item whose
title collides with an MLB club -- and wrong for a general sports magazine whose NFL
preview is bound with baseball and basketball coverage ('Inside Sports 1985-08 NFL
Preview': football 34, other 65). Raw counts cannot tell those apart; the shape of the
evidence can:

    KEEP as football when the football vocabulary is SUBSTANTIAL IN ITSELF (>= 25
    hits) or at least matches the other sport. Otherwise reject.

    A ratio, not an absolute floor -- the floor was tried first at 10 and was wrong:
    it rescued 'San Francisco Giants 2016 Media Guide' (football 10, other 1,477) and
    '2023' (14 vs 860), which are plainly baseball, and it split the New Orleans
    Buccaneers (ABA) series across two verdicts on 11-vs-32 and 7-vs-25. A document
    ABOUT pro football uses football words in the hundreds; a baseball guide that
    mentions a football stadium ten times does not become a football document.

Every reject is listed by name with both counts so the call can be checked. Texts are
never deleted -- a rejected item stays on disk and simply does not enter index.csv.

Also reports, because a non-empty check is not a content check:
  - every stored text's byte count, and every text under 2,000 bytes BY NAME
  - per-player content markers per item (recorded, never parsed)

  python3 src/finalise_ia_unheld.py [--write]
"""
import os, re, sys, csv, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
LOG = os.path.join(BASE, "build-reports", "ia-unheld-fetch.json")
OUT = os.path.join(BASE, "build-reports", "ia-unheld-final.json")
ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
TEXT, INDEX = os.path.join(ROOT, "text_all"), os.path.join(ROOT, "index.csv")
FOOT = re.compile(r"\b(quarterback|touchdown|linebacker|fumble|yardage|gridiron|halfback|fullback|punt|field goal|end zone)\b", re.I)
OTHER = re.compile(r"\b(pitcher|infield|batting average|shortstop|home runs?|innings?|goaltender|power play|slap ?shot|"
                   r"free throw|rebounds?|three-point|jump shot)\b", re.I)
PLAYER = re.compile(r"^\s*(PERSONAL|COLLEGE|PRO|CAREER|HONORS)\s*[:—–-]|\bBorn\b|\bHt\.|\bWt\.|^[A-Z][A-Z'\-]+,\s+[A-Z][a-z]", re.M)


def verdict(f, o):
    """football when the football vocabulary stands on its own, or is not outweighed."""
    if f >= 25: return "football"
    if f >= 3 and o <= f: return "football"
    return "other" if o > f else "unclear"


def main():
    write = "--write" in sys.argv
    log = json.load(open(LOG))
    res = {"_date": "2026-09-07", "rescored": [], "still_rejected": [], "small_texts": [], "per_class": {},
           "counts": {}, "byte_census": {}, "excluded_no_football_evidence": []}
    # THE INDEX IS REBUILT FROM ITS PRE-FETCH BACKUP, not appended to. The fetch appended
    # every item whose verdict was not 'other' -- and 'unclear' (no football vocabulary at
    # all) is not evidence of football. That let in a 7-byte hockey guide and eight volumes
    # of 'Black Eagles', a Vietnam War novel series matched by \bEagles\b. An item enters
    # the corpus only on POSITIVE football evidence.
    keep, drop = [], []
    for rec in log["fetched"] + log["sport_mismatch"]:
        p = os.path.join(TEXT, rec["identifier"] + ".txt")
        if not os.path.exists(p): continue
        t = open(p, errors="ignore").read()
        f, o = len(FOOT.findall(t)), len(OTHER.findall(t))
        v = verdict(f, o)
        row = {**rec, "football_terms": f, "other_sport_terms": o, "verdict": v}
        was_flagged = rec in log["sport_mismatch"]
        if v == "football":
            keep.append(row)
            if was_flagged: res["rescored"].append(row)
        else:
            drop.append(row)
            (res["still_rejected"] if o > f else res["excluded_no_football_evidence"]).append(row)
    base = INDEX + ".before-ia-unheld-20260907"
    if write and os.path.exists(base):
        rows = list(csv.DictReader(open(base)))
        have = {r["identifier"] for r in rows}
        for rec in keep:
            if rec["identifier"] in have: continue
            rows.append({"year": rec.get("year") or "", "identifier": rec["identifier"],
                         "league_wide": str(rec.get("query") == "pro-football-preview" or rec.get("class") == "preview annual"),
                         "restricted": "", "title": rec.get("title", "")})
        tmp = INDEX + ".rebuild"
        with open(tmp, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["year", "identifier", "league_wide", "restricted", "title"])
            w.writeheader(); w.writerows(rows)
        os.replace(tmp, INDEX)
    rows_to_add = keep
    sizes, per_class, per_decade, pp = [], collections.Counter(), collections.Counter(), 0
    for rec in log["fetched"]:
        p = os.path.join(TEXT, rec["identifier"] + ".txt")
        n = os.path.getsize(p) if os.path.exists(p) else 0
        sizes.append(n); per_class[rec["class"]] += 1
        per_decade[(rec["year"] // 10 * 10) if rec.get("year") else "?"] += 1
        if rec.get("per_player_likely"): pp += 1
        if n < 2000: res["small_texts"].append({"identifier": rec["identifier"], "bytes": n, "title": rec["title"]})
    sizes.sort()
    res["byte_census"] = {"files": len(sizes), "total_bytes": sum(sizes),
                          "min": sizes[0] if sizes else 0, "p10": sizes[len(sizes) // 10] if sizes else 0,
                          "median": sizes[len(sizes) // 2] if sizes else 0, "max": sizes[-1] if sizes else 0,
                          "under_2000_bytes": len(res["small_texts"])}
    res["per_class"] = dict(per_class)
    res["per_decade"] = {str(k): v for k, v in sorted(per_decade.items(), key=lambda x: str(x[0]))}
    res["counts"] = {"fetched": len(log["fetched"]), "notext": len(log["notext"]), "containers": len(log["containers"]),
                     "sport_rescored_to_football": len(res["rescored"]), "still_rejected": len(res["still_rejected"]),
                     "excluded_no_football_evidence": len(res["excluded_no_football_evidence"]),
                     "failed": len(log["failed"]), "per_player_likely": pp,
                     "in_corpus": len(rows_to_add)}
    IO.dump_atomic(res, OUT, indent=1)
    print(json.dumps(res["counts"], indent=1))
    print("byte census:", json.dumps(res["byte_census"], indent=1))
    if res["still_rejected"]:
        print("still rejected as another sport:")
        for x in res["still_rejected"]: print(f"   {x['identifier']}  football={x['football_terms']} other={x['other_sport_terms']}  {x['title'][:60]}")
    if res["small_texts"]:
        print("texts under 2,000 bytes:")
        for x in res["small_texts"]: print(f"   {x['bytes']:6}  {x['identifier'][:48]}  {x['title'][:50]}")
    print(f"wrote {os.path.relpath(OUT, BASE)}" + ("" if write else "   (dry run; --write appends the rescored rows to index.csv)"))


if __name__ == "__main__":
    main()
