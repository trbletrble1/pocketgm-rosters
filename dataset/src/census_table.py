"""Assemble the corpus census: ONE ROW PER DOCUMENT, queryable, for the other sessions.

    build-reports/corpus-census.sqlite   -- table `documents`, query it
    build-reports/corpus-census.csv      -- the same rows, for anything without sqlite

The point of the shape is the separation the earlier three passes did not keep:

  * `klass`, `per_player`, `read_method` are filled ONLY from readings -- a person or an
    agent opened the document. Where nothing was read the columns say `unread`, never a
    guess. `read_method` names the sample and its size where a sample was used.
  * `ev_*` columns are COUNTED EVIDENCE -- vocabulary hits, line shapes, the years the
    text mentions. They are there to triage what to read next. They are not verdicts, and
    the census measured how badly they mislead: the biography window finds 51 of the 59
    pre-1950 texts that reading finds 59 of, and OCR of the eBay programme photographs
    finds 0 text-bearing images in the 1925 listing whose lineup page reads perfectly
    by eye.
  * `dup_*` columns come from containment measurement, not from titles.

  python3 src/census_table.py
"""
import os, sys, csv, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
BR = os.path.join(BASE, "build-reports")
FRAME = os.path.join(BR, "corpus-census-frame.json")
DUPS = os.path.join(BR, "corpus-census-duplicates.json")
PROGS = os.path.join(BR, "corpus-census-programs.json")
READINGS = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
            "775492f6-85e4-45dc-8452-79a3131ced7a/scratchpad/readings.json")
DB = os.path.join(BR, "corpus-census.sqlite")
CSV = os.path.join(BR, "corpus-census.csv")

COLS = [("doc_id", "TEXT"), ("stratum", "TEXT"), ("path", "TEXT"), ("title_as_filed", "TEXT"),
        ("year_as_filed", "INTEGER"), ("has_text", "INTEGER"), ("format", "TEXT"),
        ("klass", "TEXT"), ("per_player", "TEXT"), ("read_method", "TEXT"), ("note", "TEXT"),
        ("bytes", "INTEGER"), ("words", "INTEGER"),
        ("ev_year_min", "INTEGER"), ("ev_year_max", "INTEGER"), ("ev_year_modal", "INTEGER"),
        ("ev_football", "INTEGER"), ("ev_baseball", "INTEGER"), ("ev_hockey", "INTEGER"),
        ("ev_basketball", "INTEGER"), ("ev_college", "INTEGER"),
        ("ev_bio_labels", "INTEGER"), ("ev_bio_prose", "INTEGER"), ("ev_htwt", "INTEGER"),
        ("ev_roster_rows", "INTEGER"), ("ev_name_pos", "INTEGER"),
        ("ev_stat_heads", "INTEGER"), ("ev_stat_rows", "INTEGER"),
        ("dup_relation", "TEXT"), ("dup_with", "TEXT"), ("dup_containment", "REAL"),
        ("dup_n_partners", "INTEGER")]


def main():
    frame = json.load(open(FRAME))
    rows = frame["rows"]
    reads = {r["doc_id"]: r for r in json.load(open(READINGS))} if os.path.exists(READINGS) else {}

    dup_by = collections.defaultdict(list)
    if os.path.exists(DUPS):
        for p in json.load(open(DUPS))["pairs_detail"]:
            dup_by[p["a"]].append((p["relation"], p["b"], p["containment_a_in_b"]))
            dup_by[p["b"]].append((p["relation"], p["a"], p["containment_b_in_a"]))

    progs = {}
    if os.path.exists(PROGS):
        for L in json.load(open(PROGS))["listings"]:
            progs["prog:" + L["listing"][:70]] = L

    out = []
    for r in rows:
        ev = r.get("evidence") or {}
        yrs = ev.get("years_top") or []
        span = ev.get("year_span") or [None, None]
        rd = reads.get(r["doc_id"])
        d = sorted(dup_by.get(r["doc_id"], []), key=lambda x: -x[2])
        note = r.get("note", "")
        pg = progs.get(r["doc_id"])
        if pg:
            note = (note + f" | OCR: {pg['images_over_60_words']} of {pg['images']} photographs "
                            f"carry >60 words ({pg['words_total']} total) -- a FLOOR, these are "
                            f"angled dealer photographs and OCR misses readable pages").strip(" |")
        out.append({
            "doc_id": r["doc_id"], "stratum": r["stratum"], "path": r["path"],
            "title_as_filed": r.get("title_as_filed", ""),
            "year_as_filed": int(r["year_as_filed"]) if str(r.get("year_as_filed") or "").isdigit() else None,
            "has_text": 1 if r["has_text"] else 0, "format": r.get("format", ""),
            "klass": (rd or {}).get("klass") or "unread",
            "per_player": (rd or {}).get("per_player") or "unread",
            "read_method": (rd or {}).get("method") or "unread",
            "note": ((rd or {}).get("note", "") + (" | " if rd and rd.get("note") and note else "") + note)[:900],
            "bytes": ev.get("bytes"), "words": ev.get("words"),
            "ev_year_min": span[0], "ev_year_max": span[1],
            "ev_year_modal": yrs[0][0] if yrs else None,
            "ev_football": ev.get("v_football"), "ev_baseball": ev.get("v_baseball"),
            "ev_hockey": ev.get("v_hockey"), "ev_basketball": ev.get("v_basketball"),
            "ev_college": ev.get("v_college"),
            "ev_bio_labels": ev.get("n_bio_labels"), "ev_bio_prose": ev.get("n_bio_prose"),
            "ev_htwt": ev.get("n_htwt"), "ev_roster_rows": ev.get("n_roster_rows"),
            "ev_name_pos": ev.get("n_name_pos"), "ev_stat_heads": ev.get("n_stat_heads"),
            "ev_stat_rows": ev.get("n_stat_rows"),
            "dup_relation": d[0][0] if d else None, "dup_with": d[0][1] if d else None,
            "dup_containment": d[0][2] if d else None, "dup_n_partners": len(d),
        })

    if os.path.exists(DB): os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE documents (" + ", ".join(f"{c} {t}" for c, t in COLS) + ")")
    con.executemany("INSERT INTO documents VALUES (" + ",".join("?" * len(COLS)) + ")",
                    [[r.get(c) for c, _ in COLS] for r in out])
    for c in ("stratum", "klass", "per_player", "year_as_filed", "dup_relation"):
        con.execute(f"CREATE INDEX ix_{c} ON documents({c})")
    con.commit()
    with open(CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[c for c, _ in COLS]); w.writeheader(); w.writerows(out)
    con.close()

    print(f"{len(out)} documents -> {os.path.relpath(DB, BASE)} and .csv")
    con = sqlite3.connect(DB)
    for q, label in [
        ("SELECT read_method LIKE 'unread', COUNT(*) FROM documents GROUP BY 1", "read vs unread"),
        ("SELECT per_player, COUNT(*) FROM documents GROUP BY 1 ORDER BY 2 DESC LIMIT 8", "per-player content"),
        ("SELECT klass, COUNT(*) FROM documents GROUP BY 1 ORDER BY 2 DESC LIMIT 8", "class"),
        ("SELECT dup_relation, COUNT(*) FROM documents WHERE dup_relation IS NOT NULL GROUP BY 1", "duplication"),
    ]:
        print("\n" + label)
        for row in con.execute(q): print("  ", row)
    print("\nthe question the brief named, as a query:")
    print("  SELECT doc_id FROM documents WHERE year_as_filed < 1950 AND per_player LIKE '%biography%';")
    n = con.execute("SELECT COUNT(*) FROM documents WHERE year_as_filed < 1950 "
                    "AND per_player LIKE '%biography%'").fetchone()[0]
    print(f"  -> {n} rows")


if __name__ == "__main__":
    main()
