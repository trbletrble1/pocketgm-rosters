"""John Troan's site, read for the one thing nothing else in the archive carries.

ASSESSED 2026-09-08 AS AN ECHO. 30 of 34 birth dates agree exactly with StatsCrew,
PFA and nflverse together, and it fills no gaps. His rosters and his dates are NOT
ingested and this file does not read them.

TWO THINGS ONLY, on Ryan's ruling of 2026-09-09:

  1. THE `Exp` COLUMN -- years of professional experience going into that season.
     Nothing else in the archive carries it.
  2. THE SURNAME-ONLY CORROBORATION. Troan holds Mathewson and Warren of the 1920
     Hammond Pros as bare surnames too. A second compiler reaching the same
     dead end is evidence that the surname really is all that survives -- which is
     a different and more useful thing than a gap.

AND ONE MEASURED REFUSAL. Troan's Hammond 1920 page gives `Exp` = 1 for EVERY man
on it, all 28. In the league's first season that is not a fact about a player, it
is a fact about the year, and writing 28 identical claims would put a number in the
archive that distinguishes nobody. Only Pottsville 1926 is read, where Exp runs 1
to 7 and does distinguish.

RIGHTS. One man's copyrighted compilation, used as a reference and cited. Not
parsed wholesale, not republished. Every claim names the page.

  python3 src/ingest_troan_experience.py            read and report
  python3 src/ingest_troan_experience.py --write    write build/troan-experience.json
"""
import os, re, sys, json, html, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

SRC_ID = "jt-sw"
DOCS = os.path.expanduser("~/Dropbox/Football Archive/docs/hunting")
OUT = os.path.join(BASE, "build", "troan-experience.json")


def rows(path):
    h = open(path, errors="ignore").read()
    out = []
    for r in re.split(r"<tr\b", h, flags=re.I)[1:]:
        r = r.split("</tr>")[0]
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
        if any(cells): out.append(cells)
    hdr = next((r for r in out if "Player" in r and "Exp" in r), None)
    if not hdr: return []
    # THE HEADER IS NOT A PLAYER. Including it put the string "Exp" among the values,
    # which made a column of 28 identical 1s look like it had two distinct values and
    # defeated the refusal below. A row is a player only if its Player cell is not the
    # header's own word.
    return [d for d in (dict(zip(hdr, r)) for r in out if len(r) >= len(hdr))
            if d.get("Player") and d["Player"] != "Player"]


def norm(s): return re.sub(r"[^a-z]", "", (s or "").lower())


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    claims, notes = [], []
    n = collections.Counter()

    # ---- 1. the corroboration, which writes no claim
    ham = rows(os.path.join(DOCS, "1920 Hammond Pros.html"))
    troan_surnames = {p["Player"] for p in ham if " " not in p["Player"]}
    held = {}
    for r in conn.execute("SELECT DISTINCT person FROM claim WHERE scope='stint' AND club_id=? AND year=1920",
                          ("club-hammond-pros-1920",)):
        for x in conn.execute("SELECT DISTINCT name FROM person_name WHERE person=?", (r[0],)):
            held.setdefault(norm(x[0]), r[0])
    both = sorted(s for s in troan_surnames if norm(s) in held)
    for s in both:
        notes.append({"source_id": SRC_ID, "source_record": f"{SRC_ID}#1920-hammond-pros",
                      "person": held[norm(s)], "name_as_printed": s,
                      "what": "a second compiler holds this man as a bare surname too",
                      "why": "corroborates that the surname is all that survives, which is a "
                             "different thing from the archive not having looked. No claim is "
                             "written: agreeing that nothing is known is not a fact about the man."})
    n["surname_corroborations"] = len(notes)

    # ---- 2. the Exp column, where it distinguishes
    for label, fn, club_id, code, league, year in (
            ("1920 Hammond Pros", "1920 Hammond Pros.html", "club-hammond-pros-1920", "HAM", "APFA", 1920),
            ("1926 Pottsville Maroons", "1926 Pottsville Maroons.html", "club-pottsville-maroons-1925", "POT", "NFL", 1926)):
        rs = rows(os.path.join(DOCS, fn))
        exp = {p["Player"]: p.get("Exp") for p in rs if p.get("Exp")}
        distinct = sorted(set(exp.values()))
        if len(distinct) < 2:
            n[f"refused_{year}"] = len(exp)
            notes.append({"source_id": SRC_ID, "source_record": f"{SRC_ID}#{club_id}-{year}",
                          "what": f"Exp not taken from {label}",
                          "why": f"every one of the {len(exp)} men carries Exp = {distinct[0]!r}. In the "
                                 f"league's first season that is a fact about the YEAR, not about a player, "
                                 f"and it would distinguish nobody."})
            print(f"  {label}: Exp is {distinct[0]!r} for all {len(exp)} -- REFUSED, it distinguishes nobody")
            continue
        on_club = {}
        for r in conn.execute("SELECT DISTINCT person FROM claim WHERE scope='stint' AND club_id=? AND year=?", (club_id, year)):
            for x in conn.execute("SELECT DISTINCT name FROM person_name WHERE person=?", (r[0],)):
                on_club.setdefault(norm(x[0]), set()).add(r[0])
        joined = miss = 0
        for name, e in sorted(exp.items()):
            ids = on_club.get(norm(name)) or set()
            if len(ids) != 1:
                miss += 1
                notes.append({"source_id": SRC_ID, "name_as_printed": name, "club": f"{year}|{club_id}",
                              "what": "Exp not written", "why": "no single man of that name on the club-season"})
                continue
            joined += 1
            claims.append({"source_id": SRC_ID, "source_record": f"{SRC_ID}#{club_id}-{year}",
                           "stated_by": "John Troan, jt-sw.com/football", "attribution": ["John Troan"],
                           "kind": "observed", "subject": ["stint", next(iter(ids)), code, f"{league}-{year}"],
                           "predicate": "jtsw.professional_experience_years", "value": e,
                           "_what_it_is": "years of professional experience going into that season, as Troan "
                                          "states them. Nothing else in the archive carries this.",
                           "_joined_on": "exact name on the club-season"})
        n[f"exp_{year}_joined"] = joined; n[f"exp_{year}_unplaced"] = miss
        print(f"  {label}: Exp runs {distinct[0]}-{distinct[-1]}; {joined} written, {miss} unplaced")

    out = {"_what": "John Troan's site, read for the Exp column and for the surname-only corroboration. "
                    "His rosters and his dates are NOT ingested: assessed 2026-09-08 as an echo.",
           "source_id": SRC_ID, "counts": dict(n), "claims": claims, "notes": notes}
    print(f"\n  surname-only men Troan holds as surnames too: {both}")
    print(f"  claims {len(claims)}, notes {len(notes)}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1); print(f"  -> {OUT}")
    else:
        print("  (dry run; pass --write)")
    return out


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
