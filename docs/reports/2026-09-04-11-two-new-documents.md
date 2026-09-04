# Two new documents: pre-1936 assistant coaches, and the article that explains §8.4

**2026-09-04. Report 11.** Both in `pgm3-sources/DocDump/`.

---

## 1. `pre1936_nfl_assistant_coaches.csv` — small, and the best-provenanced thing held

    21 rows, 14 columns, 7,476 bytes
    sha256 794e009b791a849cb20d6e5e55f42f5fad97502ad0b47eefb8c5a208ca3faeac
    years 1921, 1923-26, 1931, 1933-35   ·   11 clubs

**It addresses a recorded gap directly** — "coaching staffs before 1934" was one of
the four known gaps in the original brief. This is not a full answer (21 rows
across 9 scattered years is not a staff list) but it is the first material of any
kind for that era.

**Fill rates:** full name, title, club, year and `primary_source` at **100%**;
birth date, birthplace, death date and college at **80%**; high school 71%;
`lineage_source` 66%.

**Every row cites its own source.** Sixteen to `profootballarchives.com`, five to
`pro-football-history.com`. That is **per-row attribution**, which nothing else in
this project has — Shapiro is one remove for a whole document; this is one remove
*per claim*.

    stated_by     <the compiler - UNKNOWN, see below>
    attribution   ["profootballarchives.com" | "pro-football-history.com"]   per row

**A fourth source-native id scheme.** The profootballarchives URLs carry coach ids
— `higg00400`, `ster00400`, `walq00200`, `berr01600`, `chri00600`, `flah01000`,
`pott00200`, `wilh00400`. Pattern looks like `{surname4}{5 digits}` on a spaced
sequence rather than a dense counter. **Not yet tested** for the namesake
behaviour StatsCrew's was tested for, and it should be before it is trusted as an
identifier.

### Three things to handle carefully

**The compiler is unnamed.** The CSV has no header row identifying who assembled
it or when. Under §3.7 that makes its `stated_by` unknown — the rows are
`source_derived` from two named sites via an unnamed compilation step. **Worth
asking Ryan who built it**, because a compilation is a claim.

**The `title` field conflates a stint fact with a career fact.** Two rows read
`Assistant Coach / later Head Coach` — Ernie Nevers 1931, Mike Palm 1933. "Later
head coach" is true of the man and false of the stint. Those are **two claims
about two seasons** and must not be stored as one title, or a 1931 export will
list Nevers as a head coach.

**Four rows have no birth date** — Cad Reese and J.P. Rooney, both Pittsburgh,
1934 and 1935. Per the media-guide declaration those fall to `stint_continuity`,
and both have a `known_coaching_lineage` string, which is exactly the evidence
that mechanism uses.

**Useful shape in the data:** Ed Sternaman alternates head coach and assistant
across 1922–25; Red Grange appears three years running and his title changes to
`Backfield Coach` in 1935. Both are stint-scoped facts the model already holds.

---

## 2. `A Players View of the NFL Reserve System.pdf` — and it revises §8.4

    Edward Newman, 4 U. Miami Ent. & Sports L. Rev. 129 (1987)
    62 pages, 3,531,689 bytes
    sha256 66f2219e593ec215c7c8715c081a205ffd90049318e56a10f177835c6738d7af

A law review article by a **four-time All-Pro Dolphins guard and NFLPA player
representative**, written as a law student. Another interested party — and one who
says so on page 2: *"many of the author's comments are based on personal
observations and experiences during his career."*

### Appendix B — 1985 average salary by entry round

A **per-draft-round** axis, which is new. Counts per cell, split all players and
starters, base and total:

| round | n | avg base | avg salary | starters n | starters base | starters salary |
|---|---|---|---|---|---|---|
| 1 | 234 | $258,630 | $326,281 | 157 | $277,965 | $331,865 |
| 2 | 192 | 203,230 | 248,220 | 96 | 232,980 | 256,570 |
| 3 | 162 | 184,005 | 204,000 | 82 | 216,090 | 209,875 |
| … | | | | | | |
| 12+ | 3 | 250,000 | 250,000 | 2 | 262,500 | 262,500 |
| Free agents | 356 | 115,510 | 143,500 | 110 | 153,130 | 177,370 |

**Internally consistent with the body text**, which is a real check: the article
proposes draft-compensation thresholds of $204,000, $248,200 and $326,281 — and
those are the round-3, round-2 and round-1 average total salaries from this table.
(The body's $248,200 against the table's $248,220 is a $20 discrepancy, almost
certainly a typo or OCR in one of the two.)

Attribution: *"Chart reprinted by permission of THE LAUDABLE"* — a further remove,
to a publication not otherwise held.

### Appendix C — salary trends 1970–1985, and the note that matters

| year | avg salary | year | avg salary |
|---|---|---|---|
| 1970 | $23,200 | 1978 | $62,600 |
| 1971 | 24,600 | **1979** | **68,900** |
| 1972 | 26,100 | 1980 | 78,700 |
| 1973 | 27,500 | 1981 | 90,000 |
| 1974 | 33,000 | 1982 | 102,250 |
| 1975 | 39,600 | 1983 | 126,500 |
| 1976 | 47,500 | 1984 | 157,810 |
| 1977 | 55,300 | 1985 | 193,300 |

Plus a median-base column from 1976 and year-on-year percentage increases.

**Against the 2002 primer: identical for 1971–1980, ten years running.** Per the
shared-ancestry precedent that is conclusive — these are not two witnesses, they
are one lineage. **1970 differs by $200 ($23,200 vs $23,000) and 1981 onward
diverges completely** ($90,000 vs $82,400, and the gap widens to $244,800 vs
$193,300 by 1985). Two NFLPA-lineage documents disagreeing about the 1980s is
itself worth recording.

### The finding: §8.4's contest is at least partly DEFINITIONAL

Appendix C's note:

> *…the NFLPA and the Management Council employ different methods to measure
> average salary (**the Management Council pro-rates signing bonuses by the number
> of years a player is under contract; the NFLPA defers money to the year it is
> received**)… all this data should be treated as best estimates.*

And the 1982 hearing gives both definitions on its own page — the NFLPA's $68,900
is salary plus deferred pay plus non-performance bonuses; the League's $93,333
divides a total that **also includes medical, workmen's compensation, payroll
taxes, retirement, insurance and pre/post-season pay**.

**Those are answers to two different questions.** One is money a player receives in
a year; the other is what a club spends per player, benefits included, bonuses
spread across the contract.

**So the design was wrong to call it unresolvable in principle.** It is largely a
modelling error on our side: `average_salary` was doing two jobs. Split into
`average_salary_money_received` and `average_player_cost_prorated`, each has one
uncontested value.

Recorded as a precedent — *a contest can be the symptom of an under-specified
predicate* — with the tell: **a disagreement that is large, stable and signed
across years is definitional; genuine evidential contests scatter.**

**What survives, and it is a real contest.** Newman says the 1977–1981 figures were
*"compiled by the NFL Management Council"*. The hearing attributes the same 1979
figure to *the NFLPA's own review of 1,500 player contracts*. **Two documents
disagree about the provenance of one number** — and that survived precisely
because the definitional layer was peeled off first.

### And a route to the owed document

The article cites ***In the Matter of Arbitration Between NFLPA and NFL Management
Council*, Luskin, Arb., May 14, 1980** — a proceeding in which the League is a
party and files its own material. That is the class of source the OWED entry names
(court filing / arbitration where the League states its own figure), and it is now
a specific citation rather than a category.

---

## Disposition

| item | status |
|---|---|
| pre-1936 CSV, 21 rows | **held**, per-row attribution, ready to ingest |
| its compiler | **UNKNOWN — worth asking** |
| `Assistant Coach / later Head Coach` | must split into two seasons' claims |
| profootballarchives id scheme | **untested** for namesakes |
| Newman Appendix B (draft round) | held, `source_derived`, 2+ removes via THE LAUDABLE |
| Newman Appendix C (1970–85) | held; **one lineage with the 2002 primer**, not corroboration |
| §8.4 | **revised** — largely definitional; provenance contest survives |
| Luskin arbitration 1980 | **new lead**, named, toward the League-original debt |
