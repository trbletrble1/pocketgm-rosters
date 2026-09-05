# 35 — What the Madden files contain (characterisation 2 of 4)

2026-09-04. Characterisation only. Nothing extracted.

We tested `PSKI`, `PHCL`, `PFMK` and `PHED` because appearance was the question.

> **18 roster files · 63,378 player rows · 110 field codes · every one of the 110
> present in all 18 files.**

We had looked at four.

## Two fields decode to biography, and both were validated against held data

**`PHGT` is height in inches.** Range 60–90, 25 distinct values. Checked against
StatsCrew's 2013 rosters on 1,730 name matches:

> **`PHGT` equals StatsCrew's height in inches for 1,191 of 1,728 — 68% exact.**

The residual is genuine source disagreement plus namesake noise from matching on
name; 68% exact agreement on a 25-value scale is not a coincidence.

**`PWGT` is pounds minus 160.** The modal difference between StatsCrew's weight
and `PWGT` is **exactly 160, in 690 of 1,730 matches** — with 161 and 158 as the
next most common, which is disagreement about the same quantity rather than a
different one.

Neither was decoded from what the four-letter codes are assumed to mean. Both
were read out of the data and checked against a source already held.

## What the 110 fields are

| kind | n | examples |
|---|---|---|
| text | 2 | `PFNA` forename (3,917 distinct), `PLNA` surname (7,251) |
| identifier / large int | 9 | `PGID` (14,075 distinct), `POID` (14,347), `TGID` (71 — teams) |
| rating-like 0–99 | ~40 | `POVR`, `PTAK`, `PPBK`, `PRBK`, `PCAR`, `PINJ`, `PEGO`, `PIMP` |
| numeric | ~20 | `PSPD`, `PACC`, `PSTR`, `PAWR`, `PJMP`, **`PHGT`**, **`PWGT`**, **`PCOL`** |
| small enum | ~38 | `PSKI` (4), `PHED` (16), `PFMK` (14), `PTAL` (17), `PHCL` (6) |
| flag | 7 | `PEYE`, `PHAN`, `PICN`, `PFHO` |

**`PCOL` has 365 distinct values in 0–451 — that is college**, and 365 is about
the right order for the colleges appearing in an NFL roster file. **`PAGE`** runs
2–61 with 36 distinct values.

## The caveat that governs all of it

**The enums are indices, and we do not hold the lookup tables.** `PCOL = 214` is
a college, but which one is answered by a table inside the game, not in these
files. The same is true of `PHED`, `PFMK`, `PTAL` and the other ~38 enums —
including the appearance fields already in use, where the *distinction* between
values was usable without the labels because we only needed to tell men apart.

For college that is not enough: an index is only a college if you can name it.

**But it is recoverable without the game.** `PCOL` can be resolved against
StatsCrew's college claims by the same method that decoded `PHGT` — match players
by name in one season, read across, and check the mapping holds in a second
season. That is a measurement, not a guess, and it is the obvious next step if
this source is wanted.

## What this changes

- **Height and weight are available for 63,378 player-rows** from an independent
  source, decoded and validated. The dataset currently holds neither as a claim.
- **College is available** once the index is resolved — and resolvable by
  measurement.
- **~40 rating fields** exist and are untouched. They are *opinions*, not
  observations, and would enter as attributed claims from a named product, never
  as `observed` — the same treatment the 2K5 era votes already get.
- The four appearance fields we used are **4 of 110**.
