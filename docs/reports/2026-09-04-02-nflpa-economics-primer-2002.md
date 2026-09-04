# NFL Economics Primer 2002 — what it holds, and how far it can be trusted

**2026-09-04. Report 02.** Companion to `2026-09-04-01-antitrust-hearing-1982.md`,
which this source turns out to be entangled with. Durable conclusions are in
`DATASET_DESIGN.md` §9b and `DATASET_PRECEDENTS.md`; this is the working record.

    title      NFL Economics Primer 2002
    author     M. J. Duberstein, NFLPA Research Department, April 2002
    pages      164
    file       pgm3-sources/385388545-NFL-Economics-Primer-April-2002.pdf
    sha256     911489526cc300a1f512c79215efe763d3d1f0f5eae7c1da4cc56f5653a4ce81
    bytes      5,630,227

**Extraction.** Use the PDF with `pypdf` and
`extract_text(extraction_mode="layout")`. Ryan's instruction to prefer the PDF
over the shipped `.txt` was correct and load-bearing: the flat extraction loses
the table geometry, so year-to-value association becomes guesswork. Layout mode
recovers the columns intact.

**Page offset: printed page = PDF page − 1**, confirmed on 162 of 164 pages.

---

## The two questions, established before extracting anything

### 1. Is the 1933–2001 series annual or spot years?

**Spot years before 1970, annual after.** The table is on **printed p.20**
(PDF 21) — not printed p.18, which is a chart.

Years present: **39 of 69.**

    1933  1940  1946  1950  1955  1960  1963      <- seven spot years
    1970 ... 2001                                  <- annual, unbroken

**Thirty years are absent**, including every year of the 1940s except 1940 and
1946, and all of 1964–1969.

**The chart on printed pp.18–19 plots all 69 years on its axis.** For 30 of them
there is no underlying figure in the document. Anyone reading the chart instead of
the table takes an interpolation for an observation.

> **The chart is not a source. The table is.** Cite printed p.20, never p.18.

There is also a discrepancy between them worth recording: the p.18/19 chart
carries a callout at **1943 of $10,000**, and **1943 is not in the table**. The
chart's subtitle reads "In Actual & 1977 $000s" while the table and the chart's
own footnote read 1997. Two small internal inconsistencies in the presentation
layer; the table itself is clean (below).

### 2. Does it cite where its pre-1970 figures came from?

**No. Zero `Source:` lines in 164 pages.**

There is exactly one provenance statement, on the cover:

> *All salary data in this report comes from the NFLPA Salary Cap Information
> System*

**That cannot be true of the historical series.** The salary cap began in **1994**.
A cap information system is not the origin of a 1933 average salary. And the
primer itself calls that figure an estimate, in its own words:

> *…instead of an estimated 1933 actual average NFL salary of $8,000, its
> adjusted value in 1997 dollars becomes $98,765.*

**Verdict, by the test Ryan set** — *a 2002 primer citing sources is usable; one
that doesn't is `source_derived`* — **the entire series is `source_derived`**, and
the seven pre-1970 points are estimates by the document's own admission.

**This is `registry-1986` in an external source**: one provenance line covering a
whole document, naming the system the author read from rather than where each
value came from. Written up as a precedent — *a document-level provenance
statement does not cover the claims beneath it*. The check that exposed it was a
single question: **did the salary cap exist in 1933?**

---

## The series is internally consistent, which is worth stating separately

Poor provenance and bad arithmetic are different failures, and this document has
the first without the second. Two checks, both pass:

- **Base year.** 1997 actual = 1997 constant = $736,700. Exact.
- **Implied deflator is monotonically decreasing across all 39 rows**, from
  **12.35×** in 1933 to **0.907×** in 2001, with no reversal.

So the constant-dollar column is a single consistent deflator applied throughout —
the numbers are internally sound. **What is unknown is where the actual-dollar
figures came from before 1970, not whether they were handled consistently after.**

## NFL average salary, printed p.20 — the full table

Actual dollars and constant 1997 dollars, as printed.

| season | actual $ | 1997 $ |
|---|---|---|
| 1933 | 8,000 | 98,800 |
| 1940 | 8,500 | 97,700 |
| 1946 | 12,000 | 99,200 |
| 1950 | 15,000 | 100,000 |
| 1955 | 16,000 | 95,800 |
| 1960 | 17,000 | 92,400 |
| 1963 | 20,000 | 104,700 |
| 1970 | 23,000 | 95,000 |
| 1971 | 24,600 | 97,600 |
| 1972 | 26,100 | 100,400 |
| 1973 | 27,500 | 99,300 |
| 1974 | 33,000 | 107,500 |
| 1975 | 39,600 | 118,200 |
| 1976 | 47,500 | 133,800 |
| 1977 | 55,300 | 146,300 |
| 1978 | 62,600 | 154,200 |
| 1979 | 68,900 | 152,400 |
| 1980 | 78,700 | 153,400 |
| 1981 | 82,400 | 145,600 |
| 1982 | 120,400 | 200,700 |
| 1983 | 152,800 | 246,500 |
| 1984 | 225,600 | 347,100 |
| 1985 | 244,800 | 365,400 |
| 1986 | 244,700 | 359,900 |
| 1987 | 243,900 | 343,500 |
| 1988 | 273,700 | 369,900 |
| 1989 | 343,500 | 446,100 |
| 1990 | 395,400 | 488,100 |
| 1991 | 462,700 | 544,400 |
| 1992 | 483,900 | 556,200 |
| 1993 | 666,400 | 740,400 |
| 1994 | 628,300 | 682,900 |
| 1995 | 716,600 | 754,300 |
| 1996 | 787,500 | 803,600 |
| 1997 | 736,700 | 736,700 |
| 1998 | 992,700 | 977,100 |
| 1999 | 1,056,300 | 1,019,600 |
| 2000 | 1,116,100 | 1,075,241 |
| 2001 | 1,100,500 | 997,733 |
---

## The finding that changes how this source may be used

**The primer and the 1981 congressional hearing are ONE vote, not two.**

The primer gives **1979 = $68,900**. Report 01 records the hearing giving
**$68,900** for 1979. Verified verbatim in the hearing text:

> *According to our review of over 1,500 player contracts for the 1979 season,
> average salary (salary + deferred compensation earned + all bonuses except
> performance bonuses) was $68,900.*

Same figure. Same organisation — NFLPA Research in 2002, NFLPA Research under
Garvey in 1981. Twenty-one years apart, different authors, arrived from different
places on different days.

**Why it matters.** §8.4 of the design records a contest the dataset declines to
resolve: the NFLPA's $68,900 against the League's $93,333 for the same season.
Treating the primer as independent corroboration would promote **one party's
standing position** to multi-source consensus **inside the dispute itself**.

`derived_from` on the source declaration is what prevents it, and this is §4.3's
lineage rule with a real case attached — generalised from *files that copy each
other* to **institutions that restate themselves**, which is harder to see because
the documents genuinely are different documents.

**The tell:** an exact match on an unusual figure across a long gap. Two
independent surveys of 1,500 contracts do not both land on $68,900. **Suspicious
agreement is evidence of shared ancestry**; the check is to look for the office,
not the file.

**One useful side effect:** it confirms §8.4's season attribution. The hearing's
$68,900 is unambiguously the **1979** figure, not the 1981 survey's own year.

---

## What is genuinely new: salary by years in league

**Printed pp.70–79** (PDF 71–80), and this is the reason to keep the source.

    AVERAGE SALARY BY YEARS IN LEAGUE: THE CURRENT SYSTEM   1993-2001
    AVERAGE SALARY BY YEARS IN LEAGUE: THE OLD SYSTEM       1983-1992

Per **season**, per **service year** (1st through 8th and up), each cell carrying:

- **headcount** (`#`) — how many players
- **share of league** (`%`), with a cumulative column
- **average salary, actual $**
- **average salary, 1997 $**

Sample, 2001, as printed:

| year in league | n | % | actual $ | 1997 $ |
|---|---|---|---|---|
| 1st | 313 | 18% | 824 | 756 |
| 2nd | 283 | 17% | 336 | 308 |
| 3rd | 214 | 13% | 576 | 541 |
| 4th | 186 | 11% | 1,008 | 947 |
| 5th | 167 | 10% | 1,712 | 1,609 |
| 6th | 121 | 7% | 1,686 | 1,585 |
| 7th | 101 | 6% | 1,969 | 1,851 |
| 8th+ | 91 | 5% | 1,790 | 1,682 |

*(thousands; the 1st-year figure reads $824k, which is the cohort average, not a
rookie minimum — the block is a chart-adjacent table and the reading of the
"1st" row should be confirmed against the page image before use.)*

**This is one axis of the table the 1981 hearing proved existed** — per-experience
rather than per-position, from 1983. It carries `n` per cell, which means it can
be weighted rather than merely quoted.

It is still **one interested party's research**, so it enters as `source_derived`
with `stated_by: NFLPA`, and it does not become a fact about any individual.

---

## Correction to the brief

**Printed p.11 is a coaching-CHANGES grid, not salaries.** It gives the head coach
of record for every club at the end of every season **1980–2002** — a 23-year
club-season → head-coach table, which is **stint data** and genuinely useful for
that.

**Searched all 164 pages for coach compensation: none.** Patterns tried:
`coach*…salar*`, `salar*…coach`, `coaching salar*`, `coach*…$`. Zero hits on all
four.

**The NFLPA's 1980 estimate in report 01 — head coach ~$100,000, nine assistants
at ~$45,000 each — remains the only coach salary figure this project has for any
era**, and its flat rate is that party's own estimating fill rather than a
measured spread.

---

## Disposition

| item | printed pp. | status |
|---|---|---|
| NFL average salary 1933–2001 (table) | 20 | usable, `source_derived`, spot years pre-1970 |
| NFL average salary (chart) | 18–19 | **do not cite** — plots years it has no data for |
| Salary by years in league, current system | 71–74 | usable, `source_derived`, carries `n` |
| Salary by years in league, old system | 75–79 | usable, `source_derived`, carries `n` |
| Head coaching changes 1980–2002 | 11 | usable as **stint** data, not compensation |
| Salary components 1970–2001 | 22 | not yet read |
| Leaguewide expenditures 1981–2001 | 31 | not yet read |
| Guaranteed salary / signing bonus / rookie | — | not yet read |

**Not extracted into claims.** Reported first, per the standing rule. The two
pages not yet read are the obvious next pull if this source is accepted.

**Open question for a ruling.** The primer and the hearing being one lineage is
settled. What is not: whether the **League's** figures, which reach us *only as
quoted by the NFLPA in both documents*, can be treated as a second party's claim
at all — or whether we hold them as *the NFLPA's report of what the League
said*. I lean to the latter, which would mean §8.4's contest is currently
**one party and one hearsay**, and a League-original source is still owed.
