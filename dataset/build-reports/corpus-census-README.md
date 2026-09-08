# corpus-census — one row per document, for querying

Built 2026-09-07 by the `yearbooks` session. **Nothing here was parsed into the store.**

    corpus-census.sqlite    table `documents`, 3,110 rows, indexed on
                            stratum / klass / per_player / year_as_filed / dup_relation
    corpus-census.csv       the same rows, for anything without sqlite

Built by `src/census_frame.py` -> `src/census_duplicates.py`, `src/census_programs_ocr.py`
-> `src/census_table.py`. Alongside: `corpus-census-readings.json` (what was read, by whom,
by what method) and `corpus-census-programs-ocr/` (the OCR of all 667 programme photographs). Full findings: Dropbox `Football Archive/reports/2026-09-07-corpus-census.md`.

## The one thing to know before you use it

**`klass`, `per_player` and `read_method` are filled only where a document was OPENED AND
READ. Everywhere else they say `unread`.** 543 of 3,110 are read. `read_method` names the
sample and its size when a sample was used, so a row never implies more than it is.

**The `ev_*` columns are counted evidence for deciding what to read next — not verdicts.**
This census measured how far they mislead: the automated biography test finds 51 of the 59
pre-1950 guides that reading finds 59 of, and OCR found 0 text-bearing photographs in the
1925 programme listing whose lineup page reads perfectly by eye. Do not promote an `ev_`
column into a claim.

## Queries

```sql
-- pre-1950 documents carrying per-man biography  (62)
SELECT doc_id FROM documents WHERE year_as_filed < 1950 AND per_player LIKE '%biography%';

-- what has NOT been read yet, biggest first
SELECT doc_id, stratum, bytes FROM documents WHERE read_method='unread' ORDER BY bytes DESC;

-- redundant copies: a document with a near-identical partner
SELECT doc_id, dup_with, dup_containment FROM documents WHERE dup_relation='near-identical';

-- the class with no text layer at all
SELECT doc_id, note FROM documents WHERE stratum='programs';
```

## Two things another session may want to act on

1. **`jets-2020-media-guide-new-york` is the 2019 guide.** SETTLED 2026-09-07 by reading it.
   The two texts are byte-identical (555,111 bytes, SHA `a9fce71dd6da93e78c57caa95e82e28b773ddabb`),
   and the content is unambiguously 2019: a `2019 DRAFT PICKS` contents entry, a `2018 SEASON
   REVIEW`, rookie bios reading "Selected by the Jets ... in the 2019 NFL Draft", Joe Douglas
   (general manager from June 2019) present and Mike Maccagnan absent, and **not one member of
   the 2020 draft class** — no Becton, Mims, Perine, Zuniga or Cager, when Becton was the 11th
   overall pick. "2020" appears 3 times in 95,900 words; "2019" appears 281.

   **The error is upstream, not ours.** `meta/` shows two separate Internet Archive items with
   different identifiers and ARKs whose ORIGINAL PDFs are the same file — md5
   `f873805e80e10ba5626019272c025d48`, 26,705,325 bytes — uploaded by the same uploader 35
   seconds apart on 2022-04-29 and described as different years. `index.csv` copied that
   faithfully. Sweeping the source-PDF md5 of all **2,844** `meta/*.json`, this is the **only**
   pair in the whole guide corpus held under two items with **different years** (the one other
   shared-PDF group is five same-year Sports Illustrated 2015 regional covers, which have no
   text and are not in `index.csv`). That sweep catches what a text checksum cannot: items
   whose source is identical but whose IA-derived text differs by OCR run.

   **So the New York Jets 2020 media guide is not held at all** — it is a gap, not a duplicate.
   Costless today (guide ingestion so far is only the LA Dons 1948 sketches, and nothing in
   `src/` or `declarations/` names `jets-2020`), but it would silently file 2019 facts under
   2020 the moment the guide corpus is parsed at scale. Still not fixed here — `index.csv`
   is not this session's to write.
2. **`pgm3-sources/programs/` (55 listings, 667 photographs, 1925-1946) has no text layer and
   is in no index.** It carries lineup pages with college and position, match officials by name,
   league standings, and captioned headshots from 1939. It is invisible to everything downstream.
   STILL TRUE — but the class is now much more readable than the census said. See below.

## The programme OCR was re-run, and the floor moved

2026-09-07. `src/census_programs_vision.py` + `src/visocr.m` re-read all 667 photographs with
Apple Vision, trying four orientations each. Output in `corpus-census-programs-ocr-vision/`
(text and per-line JSON **with bounding boxes** — a lineup page is a table, and column position
is what separates a jersey number from a weight). Summary in `corpus-census-programs-vision.json`.
The tesseract pass in `corpus-census-programs-ocr/` is **kept unchanged**; the record of how far
the first pass misled is the most useful thing the census measured.

Six `ev_vision_*` columns were ADDED to the `documents` table for the 55 programme rows. No
existing column was edited. They remain evidence, not verdicts.

**Scored with the same detector against both passes, same 55 listings, same images:**

| listings of 55 carrying...     | tesseract | vision |
|--------------------------------|----------:|-------:|
| a lineup / officials heading   |        28 |     48 |
| 3+ position words on a page    |        32 |     46 |
| 4+ biography words on a page   |        33 |     39 |

Raw word count barely moved (161,649 -> 177,471, x1.10) and Vision actually reports **fewer**
photographs over 60 words (529 -> 481) because it emits less noise. **Word count was the wrong
measure.** What changed is how many listings can be seen to carry a lineup or a biography page.

**The cause is orientation, not the engine's cleverness.** 377 of the 667 photographs (57%) read
best rotated — 150 upside down, 126 right, 101 left — and they carry **64% of all words read**.
The tesseract pass was never given a rotation to try.

**A resolution claim made mid-session was wrong and is corrected here.** Nine listings hold loose
files named `s-l1600`, and it looked as though the other 46 held only a small variant. Measuring
pixels says otherwise: **52 of 55 listings hold images of 1599-1600 px**, the zipped ones included.
Only **three** are small (~1000x666) — `1925 New York Giants vs Providence Steam Rollers`,
`1926 New York Giants v Kansas City Cowboys`, `1926 New York Yankees Pacific Coast Wildcats`.
That stratum reads 74 words per photograph against 271 for the rest, and 38% of its photographs
clear 60 words against 73%. **Re-fetching bigger images is worth doing for three listings, not 46.**

**Resolution is still the binding limit on those three.** The 1925 lineup spread is legible by eye
and Vision reads its headings — `Line-Up and Numbers of Both Teams`, both clubs' linesmen,
`Official Schedule, 1925`, the league standing — but the player ROWS garble (`BENKERT (Rutee`,
`KHORD ECISTEIS`). Upscaling 3x lifts that page 189 -> 312 words and still recovers only 6 of 34
name/college tokens. At 1200x1600 the same kind of page reads cleanly: `COLLEGE ALL-STARS LINE-UP
/ Name / College / No.`, then Beattie Feathers/Tennessee, Sidney Gillman/Ohio State,
George Sauer/Nebraska.

3. **`programs/Grange Article.webp` sits loose at the top of `programs/`, inside no listing
   directory, so BOTH OCR passes walked straight past it.** 1115x1600, photographed upside down,
   **918 words** of 1925 reporting on Grange turning professional. Now read, in
   `corpus-census-programs-ocr-vision/LOOSE-Grange-Article.txt`. Anything that enumerates this
   class by iterating listing directories will miss it too.
