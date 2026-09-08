"""Fold the Apple Vision OCR pass into the census table, ADDITIVELY.

The table already says, for the 55 programme listings, `read_method='unread -- OCR only'`
and carries evidence from the tesseract pass. That pass is now known to be a bad floor:
it read the 1925 Giants/Providence lineup spread as 0 photographs over 60 words when the
page is a legible lineup table. Silently rewriting those numbers would destroy the record
of how far the first pass misled, which is the most useful thing the census measured.

So this ADDS columns rather than editing any. Nothing that was true stops being true:

  ev_vision_words          words Apple Vision read across the listing's photographs
  ev_vision_over_60        photographs over 60 words (the tesseract column stays put)
  ev_vision_lineup         photographs whose text carries a lineup/officials heading
  ev_vision_bio            photographs carrying biography wording
  ev_vision_max_px         the largest pixel dimension held -- the ceiling on all of it
  ev_vision_rotated        the listing holds at least one photograph not upright

`ev_*` remains evidence for deciding what to read next, never a verdict.

  python3 src/census_table_vision.py
"""
import os, sys, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
DB = os.path.join(BASE, "build-reports", "corpus-census.sqlite")
VIS = os.path.join(BASE, "build-reports", "corpus-census-programs-vision.json")

COLS = [("ev_vision_words", "INTEGER"), ("ev_vision_over_60", "INTEGER"),
        ("ev_vision_lineup", "INTEGER"), ("ev_vision_bio", "INTEGER"),
        ("ev_vision_max_px", "INTEGER"), ("ev_vision_rotated", "INTEGER")]


def main():
    listings = json.load(open(VIS))["listings"]
    db = sqlite3.connect(DB)
    have = {r[1] for r in db.execute("PRAGMA table_info(documents)")}
    for name, typ in COLS:
        if name not in have:
            db.execute(f"ALTER TABLE documents ADD COLUMN {name} {typ}")

    # The census keyed programme rows by doc_id; match on the listing directory name,
    # which is what census_frame.py used as the path. Report any that do not match
    # rather than updating zero rows quietly.
    rows = {r[0]: r[1] for r in db.execute(
        "SELECT doc_id, path FROM documents WHERE stratum='programs'")}
    matched = missed = 0
    for L in listings:
        name = L["listing"]
        hit = [d for d, p in rows.items() if name in (p or "") or name in d]
        if not hit:
            print("NO ROW for listing:", name[:70]); missed += 1; continue
        for d in hit:
            db.execute("""UPDATE documents SET ev_vision_words=?, ev_vision_over_60=?,
                          ev_vision_lineup=?, ev_vision_bio=?, ev_vision_max_px=?,
                          ev_vision_rotated=? WHERE doc_id=?""",
                       (L["vision_words"], L["vision_images_over_60"],
                        L["images_lineup_heading"], L["images_with_bio_words"],
                        L["max_px"], 1 if L["rotated"] else 0, d))
            matched += 1
    db.commit()
    print(f"programme rows in table: {len(rows)}   updated: {matched}   listings with no row: {missed}")
    if missed:
        sys.exit("refusing to report success: some listings did not match a row")
    q = db.execute("""SELECT COUNT(*), SUM(ev_vision_lineup>0), SUM(ev_vision_max_px>=1400)
                      FROM documents WHERE stratum='programs'""").fetchone()
    print(f"of {q[0]} programme rows: {q[1]} carry a lineup heading, {q[2]} hold 1600px images")
    db.close()


if __name__ == "__main__":
    main()
