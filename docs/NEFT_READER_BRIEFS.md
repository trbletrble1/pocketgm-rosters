# Reading Neft: the reader briefs

The briefs given to the readers of Neft, Cohen & Deutsch, *Pro Football: The Early Years* (1978), for the ingest's passes 1 and 2 (12 September 2026). They are kept here so a later pass reads the book the same way, and so the readings can be judged against what the readers were asked to do.

- **The rights.** The book is consulted and cited under the reference-works ruling, never parsed wholesale. The readers recorded only the fields below.
- **Where the readings live.** They are in `dataset/build/neft-readings-1920s/` and `neft-readings-1930s/`. That folder is git-ignored like every store, and the readings are **not committed**: they are near-complete transcriptions of the book's roster tables, and committing them would republish the book.
- **What is committed.** The ingest (`src/ingest_neft_1920s.py`, `src/ingest_neft_1930s.py`), the gate (`src/gate_neft_ingest.py`), and the reports of each pass in `build-reports/neft-early-years-1978-*.json`. Each report holds the counts, leads, candidates, refusals, held-out men and every reader disagreement.

## Method, for every page

1. **Two readers per page, working apart.** Neither may open the other's folder. A fact is claimed only where both read the same value. Where they differ, the line is listed in the store's `reader_disagreements` and never resolved.
2. **Read from the page image only.** The OCR text layer runs columns together; it put Robeson beside Cole. It may be used only to find which page is which.
3. **Rendering.** `pdftoppm`: 150 dpi to see the layout, then 300 dpi crops read one line at a time, and 600 dpi for blots. PDF page = printed page + 2.
4. **Never guess.** A cell unreadable at 600 dpi is null, with `{"field", "why"}` in the man's `uncertain` list, and an uncertain field is never claimed.
5. **Record only the fields asked for.** No prose, scores, statistics or ages.

## Brief 1: yearly rosters, 1920–32 (PDF 18–66)

**The page:** several club blocks, sometimes below narrative prose.
- Each block opens with a header: the CLUB NAME, W-L-T record and head coach(es).
- Then up to three column groups follow, "Regulars" and two "Substitutes", each row giving Use Name, Pos., Hgt., Wgt., Age and Pts.
- The far-right "Scores of Each Game", the standings, the leaders and any statistics block are not recorded.

**Watch for:**
- **Surname-only men,** usually indented: set `surname_only`.
- **Moves in parentheses after a name,** as in "Oscar Knop (from & to ChiT)": record the words inside the parentheses. A parenthesis that continues on the next line belongs to the man above; it is not a separate man.
- **Other notes** such as "(played as John Webster)": record them in `note_as_printed`.
- **Marks such as "*":** record them in `mark_as_printed`, and the footnote's first sentence in the club's `notes_as_printed`.
- **Lines about absent men,** such as "Red Grange — American Football League" or "Voluntarily Retired": these are club notes, not men.

**Output:** one JSON file per page, holding the clubs, and under each club its men. Each man has `n`, `section`, `name_as_printed`, `surname_only`, `move_as_printed`, `note_as_printed`, `mark_as_printed`, `pos`, `hgt`, `wgt` and `uncertain`.

## Brief 2: club pages, 1933–45 (pass 2 read PDF 80–107, the 1930s): new from 1933

**Each conference-season is a facing pair of pages:**
- **The even page:** the club header, scores, narrative between the clubs, and the club's linemen in labelled columns. The first column is unlabelled, followed by "Tackles" and "Guards".
- **The odd page:** "Backs & Ends", headed only by the club name.
- **No college on either page.**

**What the readers had not seen before:**
1. **Age before height on the backs page.** It comes after height on the linemen page, so readers must read the column headers on every page and never put an age in the height field.
2. **Statistics in parentheses under a name,** such as "(2 receptions for 20 yards)" or "(1 PAT in 1 attempt)", sometimes on the name line itself. They look like a move and are not recorded.
3. **Moves that carry a position,** such as "(from DET T-G)" or "(to PHI,HB-DB,to C-S)". A move can sit on its own line under the name.
4. **One line per man per season.** A traded man is printed once, on the club he played for most, with from/to. An absent man is not a missing man.
5. **Men printed outside their position's column.** Record the section they are printed under. The 1937 West lineman columns carry no Tackles or Guards headings, and one backs page reads "Backs and Ends".
6. **The 1934 combined club,** "CINCINNATI REDS — ST. LOUIS GUNNERS": record it as one block, and do not split its men.

**The ingest treats a club as one block across the pair** (season, club), so a name printed twice on a club, once among the linemen and once among the backs, is counted twice.

## Brief 3: the registers

**1920–32 register (PDF 67–76).** One line per man: name, positions, team-by-year, height, weight, college, trailing number.
- **Record:** `name_as_printed`, `positions_as_printed`, `teams_as_printed`, `note_as_printed`, `college_as_printed`, and `college_cell`.
- **`college_cell`** is one of three values:
  - "printed";
  - "none", when the word *none* is printed. Neft's printed *none* is a positive assertion;
  - "blank".
- **Not recorded:** height, weight (a career average by Neft's definition) or the trailing number.

**1933–45 register (PDF 138–146).** The same fields, plus new things in the line:
- **"See Section" numbers:** not recorded.
- **Codes inside the team-by-year:** MS, HO, VR, injury codes, "26AFL", "34C-S", and PC/HC. They stay inside `teams_as_printed` as printed.
- **Remarks go in the note, not the name:** "(born …)", "(played as …)", killed-in-action and N.B.L. remarks. A nickname in parentheses stays in the name.

**Known limit.** The two pass-2 register readers filed some remarks differently: one inside the team string, one in the note. Those entries do not align, their colleges are not claimed, and they are listed among the register disagreements. A later pass should say explicitly where "killed in action" goes.
