"""Pro Football Archives' draft pages, ingested.

203 pages, enumerated from the cache before anything is parsed, fetched in the
original PFA sweep and never read until 2026-09-08. 35,161 picks on them, of which
the archive held 22,245 and did not hold 12,807.

THE WHOLE PAGE IS INGESTED, NOT THE 12,807. A store that held only the picks the
archive lacked would be a partial reading of a document with nothing recording the
part it skipped -- the defect the source-coverage rule exists for. Every pick becomes
a claim naming the page it is on; the three relations to what was already held are
COUNTED and reported, and none of them changes what is written.

DISAGREEMENTS ARE HELD, NOT RESOLVED. Where PFA's page and the archive name different
men for the same selection, both stand. The store records the disagreement with the
person the archive already holds, and joins nothing.

THE KEY IS THE SELECTION. Ryan's ruling of 2026-09-08 put league, kind and numbering
into the draft reading, which is what makes this safe: 72 of 90 years hold more than
one draft numbering its picks from 1, and before that fix a naive (year, pick) join
put one man's selection under another's name.

ROUNDS-FREE PAGES ARE OUT. The 26 pages that print no Round and no Overall need the
family ruling on `pfa.draft_allocation` first. They are counted here and skipped.

  python3 src/ingest_pfa_drafts.py [--write]
"""
import os, re, sys, json, collections, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, reading_view as RV
import measure_pfa_drafts as D

OUT = os.path.join(BASE, "build", "pfa-drafts.json")


def norm(s):
    return " ".join(re.sub(r"[^a-z ]", " ", str(s or "").lower()).split())


def held_selections(conn):
    """(year, overall) -> [{person, name, reading}] from the archive's own claims.

    INDEXED COARSELY AND COMPARED ON THE READING. Keying on the full
    (year, league, kind, overall) tuple looks tighter and is wrong: a held claim that
    states no league reads as {year, round, overall, numbering} and would never equal
    a page's {year, league, kind, ...}. `same()` treats a field only one side carries
    as SILENCE, not a difference, and that is the whole reason it exists. Matching on
    the tuple reported 13,793 additions where the reading reports 12,807 -- 986
    selections the archive already held, filed as new."""
    out = collections.defaultdict(list)
    for pred, val, person in conn.execute(
            "select predicate, value, person from claim where family='draft'"):
        try: v = json.loads(val)
        except Exception: continue
        if not isinstance(v, dict): continue
        r = RV.read("draft", v)
        if not r or r.get("overall") is None: continue
        out[(r["year"], r["overall"])].append(
            {"person": person, "name": v.get("name_as_printed"), "predicate": pred,
             "reading": r})
    return out


def main():
    write = "--write" in sys.argv
    conn = sqlite3.connect(paths.READ_MODEL)
    held = held_selections(conn)

    claims, persons, srs, dens = [], [], {}, []
    n = collections.Counter()
    disagreements = []
    cid = 0
    pages = D.pages()
    n["pages enumerated"] = len(pages)
    for path, year, lg, kind in pages:
        page = os.path.basename(path)
        rows = list(D.rows_of(path))
        if not rows:
            n["pages that print no round and no overall -- SKIPPED"] += 1
            continue
        n["pages read"] += 1
        sr = f"pro-football-archives#{page}"
        srs[sr] = {"source_id": "pro-football-archives", "locator": page}
        for r in rows:
            rd, ov = r.get("round"), r.get("overall")
            name = (r.get("player") or "").strip()
            if not name or not str(rd).strip().isdigit() or not str(ov).strip().isdigit():
                n["rows refused: no name, or no round and pick"] += 1
                continue
            n["picks on the pages"] += 1
            pid = "pfadraft_%06d" % (len(persons) + 1)
            persons.append({"id": pid, "name_as_printed": name})
            rec = f"{sr}#{rd}-{ov}"
            srs[rec] = {"source_id": "pro-football-archives",
                        "locator": f"{page}#round {rd} pick {ov}"}
            value = {"year": year, "round": int(rd), "overall_pick": int(ov),
                     "league_from_filename": lg, "draft_kind": kind,
                     "team": (r.get("team") or "").strip() or None,
                     "name_as_printed": name,
                     "position_as_printed": (r.get("pos") or "").strip() or None,
                     "college_as_printed": (r.get("college") or "").strip() or None,
                     "notes": (r.get("notes") or "").strip() or None}
            cid += 1
            claims.append({"id": "c_%06d" % cid, "predicate": "pfa.draft_selection",
                           "value": value, "subject": ["person", pid], "kind": "observed",
                           "source_id": "pro-football-archives", "source_record": rec,
                           "stated_by": "Pro Football Archives", "attribution": [],
                           "observed_at": year, "note": None})
            cid += 1
            claims.append({"id": "c_%06d" % cid, "predicate": "name", "value": name,
                           "subject": ["person", pid], "kind": "observed",
                           "source_id": "pro-football-archives", "source_record": rec,
                           "stated_by": "Pro Football Archives", "attribution": [],
                           "observed_at": year, "note": None})

            mine = RV.read("draft", value)
            already = [h for h in held.get((year, int(ov)), ())
                       if mine and RV.same("draft", mine, h["reading"])]
            if not already:
                n["NOT HELD -- the addition"] += 1
                continue
            named = [h for h in already if norm(h["name"])]
            same = [h for h in named if norm(h["name"]) == norm(name)]
            if not named:
                # THE ARCHIVE HOLDS THE SELECTION AND NOT THE MAN'S NAME. 22,630 of
                # 65,363 held draft readings carry no `name_as_printed` -- PFR's and
                # nflverse's selections identify a pick, not a person. That is not a
                # disagreement about who was taken; there is nothing to disagree with.
                n["already held, but the archive names nobody for it"] += 1
                dens.append({"person": pid, "matched_against": already[0]["person"],
                             "method": "the same selection; the archive holds no name",
                             "discriminator": ["draft_selection"],
                             "source_record": rec, "status": "candidate"})
                continue
            if same:
                n["already held, and the same man"] += 1
                dens.append({"person": pid, "matched_against": same[0]["person"],
                             "method": "the same selection and the same name",
                             "discriminator": ["draft_selection", "name_as_printed"],
                             "source_record": rec, "status": "asserted"})
            else:
                # A DIFFERENT NAME IS NOT YET A DIFFERENT MAN. `Bob Smith` against
                # `Robert Smith` on one selection is a name form; `Jay Berwanger`
                # against `Riley Smith` is two men. The surname decides which question
                # is being asked, and neither is joined here.
                sur = {norm(h["name"]).split()[-1] for h in named
                       if norm(h["name"]).split()}
                same_sur = norm(name).split() and norm(name).split()[-1] in sur
                n["already held, a different NAME FORM (same surname)" if same_sur
                  else "already held, A DIFFERENT MAN -- held, not resolved"] += 1
                disagreements.append(
                    {"selection": {"year": year, "league": lg, "kind": kind,
                                   "round": int(rd), "overall": int(ov)},
                     "pfa_says": name, "the_archive_says": [h["name"] for h in already],
                     "archive_persons": [h["person"] for h in already],
                     "kind": "name form, same surname" if same_sur else "a different man",
                     "source_record": rec})
                dens.append({"person": pid, "matched_against": already[0]["person"],
                             "method": "the same selection, a DIFFERENT name",
                             "discriminator": ["draft_selection"],
                             "source_record": rec, "status": "candidate",
                             "note": "the sources disagree about who this selection was; "
                                     "both stand and nothing is joined"})

    out = {"source": {"source_id": "pro-football-archives",
                      "acquisition": "in the original PFA sweep; unread until 2026-09-08",
                      "stated_by": "Pro Football Archives"},
           "_what": "every pick on PFA's 203 draft pages that prints a round and an "
                    "overall number",
           "_the_whole_page": "the store holds all of them, not only the ones the archive "
                              "lacked. A store holding half a document is a partial "
                              "reading with nothing recording the part it skipped.",
           "_disagreements_are_held": "where PFA and the archive name different men for "
                                      "one selection, both stand and the denotation is a "
                                      "CANDIDATE, never a join.",
           "_rounds_free_pages": "the pages that print no Round and no Overall are skipped "
                                 "and counted; they need the pfa.draft_allocation family "
                                 "ruling first.",
           "source_records": srs, "persons": persons, "claims": claims,
           "denotations": dens, "disagreements": disagreements,
           "counts": dict(n) | {"claims": len(claims), "people": len(persons),
                                "disagreements": len(disagreements)}}
    for k in ("pages enumerated", "pages read",
              "pages that print no round and no overall -- SKIPPED",
              "picks on the pages", "NOT HELD -- the addition",
              "already held, and the same man",
              "already held, but the archive names nobody for it",
              "already held, a different NAME FORM (same surname)",
              "already held, A DIFFERENT MAN -- held, not resolved",
              "rows refused: no name, or no round and pick"):
        print(f"   {k:56s} {n[k]:>7,}")
    print(f"   {'claims written':56s} {len(claims):>7,}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        print("wrote", OUT)
    else:
        print("   (dry run; --write to store)")


if __name__ == "__main__":
    main()
