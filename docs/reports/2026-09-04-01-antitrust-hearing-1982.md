# Antitrust Policy and Professional Sports — what is actually in it

**Reported before extracting, per Ryan's instruction. 2026-09-04.**

    Google Books id   XQ8oAAAAMAAJ
    sha256            8ed1a97cc9a6b965a61ab5197b2fa1ad7439fb1bf959e1149f8d141678738551
    bytes             18,570,665
    pages             685 PDF pages (678 with text)
    cached            ~/Documents/pgm3-sources/hearings/hearing_XQ8o.{pdf,txt}

**Transport.** The PDF download works with plain `curl -L`; **the 302 is
load-bearing** — without `-L` you get 562 bytes of HTML that reads exactly like a
book with no text. Same trap the handoff records for archive.org `_djvu.txt`.
The **EPUB is gated** behind a captcha `continue=` page; the PDF is not.

**Text layer.** JBIG2 scans with a CID-encoded OCR layer. No `pdftotext`,
`mutool` or PyMuPDF on this machine; `pypdf` (pip, local `--target`) extracts it
cleanly. 1,801,544 characters, 423 `$` signs, 188 dollar amounts of $1,000+.

**Printed page = PDF page − 11**, confirmed on 521 pages.

---

## The headline: Attachment B, "NFL FINANCIAL SUMMARY: 1966–1980"

Printed **twice** in the record, at printed pages **233 and 239** (PDF 244, 250).
Per **average club**, in **thousands of dollars**, with a percentage-of-revenue
column beside every figure. Footnote: 9 AFL + 15 NFL clubs (1966), 26 clubs
(1970, 1975), 27 clubs (1977, 1979, 1980).

| | 1966 AFL | 1966 NFL | 1970 | 1975 | 1977 | 1979 | 1980 est |
|---|---|---|---|---|---|---|---|
| Ticket sales | 1,174 | 2,019 | 2,839 | 4,202 | 4,753 | 5,345 | 6,225 |
| TV & radio | 745 | 1,321 | 1,541 | 2,442 | 2,328 | 5,556 | 6,000 |
| **Total income** | **2,164** | **3,741** | **4,825** | **7,399** | **7,909** | **12,090** | **13,300** |
| **Salaries, incl. pre/post-season** | **1,193** | **1,321** | **1,661** | **2,887** | **3,435** | **4,524** | **5,065** |
| Retirement & medical | 69 | 150 | 202 | 250 | 546 | 666 | 745 |
| Total player cost | 1,262 | 1,471 | 1,863 | 3,137 | 3,981 | 5,190 | 5,810 |
| Other expense | 1,119 ✗ | 1,443 | 2,017 | 3,406 | 3,955 | 5,150 | 6,090 |
| Total expenses | 2,271 | 2,914 | 3,880 | 6,543 | 7,936 | 10,340 | 11,900 |
| Operating profit (loss) | (107) | 827 | 945 | 856 | (27) | 1,750 | 1,400 |

**This is a league-aggregate series covering exactly the years the brief
predicted — 1966, 1970, 1975, 1977, 1979, 1980 — and it is per club, not per
player.** As expected: Congress cared about the aggregate.

### OCR quality — measured, not assumed

Three independent checks, all cheap, all run:

1. **The table is printed twice.** Diffed cell by cell: 136 numeric tokens each,
   **one substantive disagreement** — 1975 Total player cost reads **1,063** on
   printed p.233 and **1,863** on p.239.
2. **Every cell against the table's own percentage column** (49 cells): 45 pass
   within rounding, 4 fail.
3. **Additivity**: `Total player + Other expense = Total expenses`, and
   `Total income − Total expenses = Operating profit`, per column.

**What the checks resolve:**

- *1975 Total player cost* — `4,825 × 38.6% = 1,862`, and
  `Salaries 1,661 + Retirement 202 = 1,863`. **1,863 is correct; 1,063 is OCR.**
- *1966 AFL Other expense* — reads **1,119**; the percentage column implies 1,008
  and `2,271 − 1,262 = 1,009`. Two independent checks agree. **OCR error,
  correctable to 1,009.** It is the only column that fails additivity.
- *1980 estimated column* — three cells fail the percentage check but **both
  additivity identities hold**. Footnote 3 says the 1980 column is an estimate
  "based on results of large majority of clubs and projections". **The
  inconsistency is in the source document, not the OCR.** Do not "correct" it.

So: **~2 OCR errors in 136 numeric tokens (~1.5%), both caught and both
correctable from the document's own arithmetic.** The table carries its own gate.

---

## The dispute — two interested parties, on the record, disagreeing

Printed pp. **59–61** (PDF 70–72) carry the NFLPA's analysis, and the League's
figures beside it. They do not agree about 1979:

| | NFLPA | NFL |
|---|---|---|
| average player pay | **$68,900** (1981 NFLPA salary survey, excl. performance bonuses) | **$93,333** (~$140M ÷ 1,500 players) |
| after each side's own adjustments | "still under **$75,000**" | "still stays over **$85,000**" |
| average team player expenditure, 1979 | **$4,300,000** | **$5,200,000** |

Elsewhere in the same testimony: average team revenue 1980 **$14,310,191**, player
salaries **$4.3M** = 30% of gross, **average salary $78,500**, 1,532 players, and
an assumption of 51 paid players per team against a **squad size of 45**.

**This is a textbook case for the design.** Both sources have a stake in the
number, both are named, both are dated, and neither is a mistake to be resolved
away — the disagreement is the historical fact. Under §4 this resolves to
`basis: contested` with both claims retained, and it is exactly the precedent
*"when a source has a stake in its own entry, check that entry first — and say so
before you look."*

## Coaching salaries — an unexpected find

Same page (printed 60), NFLPA estimate for an average club, 1980:

- **head coach ~$100,000**
- **nine assistant coaches at ~$45,000 each** (~$505,000 total)
- other coaching costs ~$195,000

The project's staff files have never had a sourced salary figure for any era.
This is an estimate by an interested party, not a league return — but it is
dated, attributed and reproducible, which is more than "derived" gave us.

---

## What is NOT here

**No positional or years-of-service salary data.** Searched: `by team position`,
`years of service`, quarterback-adjacent dollar figures, rookie minimum. One hit
each, and they are all the *same* passage — the **CBA text describing a
compilation that is not reproduced in the record**:

> …a compilation of salary information which shall set forth the average salary
> for all players then under contract to the Member Clubs, including current and
> deferred compensation and any signing or reporting bonus, **compiled by team
> positions and years of service** of the players. This information shall also
> include the highest and lowest salary for each team position…

**That is a lead, not a gap.** An annual NFLMC→NFLPA compilation with per-position
highs, lows and averages by service year existed contractually from this era. It
is the single most useful salary document this project could obtain, and the
hearing proves it exists without containing it.

**Also absent:** Ed Garvey's prepared statement is not at printed p.597 in this
volume — p.597 is testimony attacking Rozelle with no figures, and Garvey appears
around printed 593–594. The p.597 reference is presumably to one of the other
three volumes.

---

## Recommended next, not done

1. **Get the other three volume IDs from Ryan** and run the same pull. The
   Garvey statement and any Rozelle exhibits with a finer breakdown are likely
   there.
2. **Chase the NFLMC/NFLPA annual salary compilation** — named in the CBA above.
   Candidate holders: NFLPA publications, the *Mackey* and later antitrust
   filings, subsequent oversight hearings.
3. **Confirm the four flagged cells against the page images** before any figure
   is used. The arithmetic says what they should be; an eyeball on the scan
   closes it.
4. **Do not commit the PDF to the repo.** Same ruling as `sources/` — it is a
   third-party scan, cached on disk and hash-pinned above.

## What this is worth to a build, stated plainly

A **measured 1979 league average** lets an export scale invented salaries to a
real number instead of a guessed one — which was the stated hope, and it is met,
with a caveat: there are **two** measured 1979 averages, $4.3M and $5.2M per club,
and choosing between them is a ruling. The honest export records which it used and
why, in the build's own provenance.

It does **not** give per-player or per-position figures, so it cannot make a
salary a *fact* about any individual. It sets the level; the ordering still has to
come from somewhere else — which is the shape §4.5 of the design already
prescribes for exactly this case.
