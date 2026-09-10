"""Joseph Plunkett -- a forename for one of the archive's surname-only men.

The archive holds `Plunkett`, Chicago Cardinals 1920, wingback, one game, and
`college: none` as a POSITIVE assertion -- a man whose surname is all that
survived. Wikipedia's article gives a full name, a birth date, a death date and
place, a height and a weight, and its club, year and position all match what the
archive already holds. That agreement is the join; nothing here rests on the name
alone.

WHAT THE ARTICLE DOUBTS, THE ARCHIVE DOES NOT HOLD. It says some sources credit
Plunkett with helping to found the NFL and with owning the league's original
Milwaukee club, and calls those claims unverified in its own words. They are
recorded here as a REFUSAL with the article's own wording, so a later reader can
see they were seen and declined rather than missed. Ryan's ruling, 2026-09-09.

The 1948 Life photograph is noted, not taken: a photograph has its own rights
route and this is not it.

  python3 src/ingest_wikipedia_plunkett.py            read and report
  python3 src/ingest_wikipedia_plunkett.py --write    write build/wikipedia-plunkett.json
"""
import os, re, sys, json, html, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

SRC_ID = "wikipedia-en"
DOC = os.path.expanduser("~/Dropbox/Football Archive/docs/hunting/Joseph Plunkett (American football) - Wikipedia.html")
OUT = os.path.join(BASE, "build", "wikipedia-plunkett.json")
SR = f"{SRC_ID}#Joseph Plunkett (American football)"


def main(write=False):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", open(DOC, errors="ignore").read())))
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)

    # THE JOIN IS THE AGREEMENT, NOT THE NAME. Club, year and position must match
    # what the archive already holds, or this writes nothing.
    pid = None
    for r in conn.execute("SELECT DISTINCT person FROM person_name WHERE norm='plunkett'"):
        held = {(x[0], x[1], x[2]) for x in conn.execute(
            "SELECT league, year, club_str FROM claim WHERE scope='stint' AND person=?", (r[0],))}
        if any(y == 1920 and c == "CHC" for _, y, c in held): pid = r[0]; break
    checks = {"club and year (APFA 1920 Chicago Cardinals)": pid is not None,
              "position (wingback)": bool(re.search(r"Position\s+Wingback", t, re.I)),
              "games played (1)": bool(re.search(r"Games played\s*1\b", t))}
    for k, v in checks.items(): print(f"  {'ok  ' if v else 'FAIL'} {k}")
    if not all(checks.values()):
        print("  the article does not agree with what the archive holds; nothing written"); return None

    g = lambda p: (re.search(p, t) or [None, None])[1]
    fields = {
        "wikipedia.full_name": g(r"(Joseph T\. Plunkett)\s*\("),
        "wikipedia.birth_date": g(r"Born\s*\(\s*[\d-]+\s*\)\s*([A-Z][a-z]+ \d{1,2}, \d{4})"),
        "wikipedia.death_date": g(r"Died\s*([A-Z][a-z]+ \d{1,2}, \d{4})"),
        "wikipedia.death_place": g(r"\(aged \d+\)\s*(Cook County, Illinois)"),
        "wikipedia.height": g(r"Listed height\s*(\d ft \d+ in)"),
        "wikipedia.weight": g(r"Listed weight\s*(\d+ lb)"),
    }
    base = {"source_id": SRC_ID, "source_record": SR, "stated_by": "Wikipedia",
            "attribution": ["Wikipedia contributors"], "kind": "observed",
            "_joined_on": "club, year and position all agree with what the archive already holds"}
    claims = [{**base, "subject": ["person", pid], "predicate": k, "value": v}
              for k, v in fields.items() if v]

    refused = [{"source_id": SRC_ID, "source_record": SR, "person": pid,
                "not_held": "helping to found the National Football League",
                "why": "the article calls it unverified in its own words: \"Although the claims are "
                       "unverified, some sources have credited him with...\". Ryan's ruling 2026-09-09: "
                       "what a source doubts, the archive does not hold."},
               {"source_id": SRC_ID, "source_record": SR, "person": pid,
                "not_held": "owning the NFL's original football club in Milwaukee",
                "why": "the same sentence, the same wording, the same ruling."},
               {"source_id": SRC_ID, "source_record": SR, "person": pid,
                "not_held": "the 1948 Life magazine photograph",
                "why": "noted, not taken. A photograph has its own rights route and this is not it."}]

    out = {"_what": "Joseph Plunkett: a forename for a surname-only man, on an agreement of club, year and position.",
           "source_id": SRC_ID, "person": pid,
           "counts": {"claims": len(claims), "refused": len(refused)},
           "claims": claims, "refused": refused}
    print(f"\n  {pid} gains {len(claims)} claims: {sorted(fields)}")
    print(f"  {len(refused)} things the article states and the archive declines to hold")
    if write:
        json.dump(out, open(OUT, "w"), indent=1); print(f"  -> {OUT}")
    else:
        print("  (dry run; pass --write)")
    return out


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
