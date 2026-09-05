# 46 — A statistic must name its table

2026-09-05. I went looking for superlatives in the media guides and found a
defect in 1.9 million claims I had already written.

---

## What I set out to do

The bios reach for *"led the league in rushing"* and cannot get there. Records
sections are 29% of the guides' statistical headings, so I characterised them.

**Section-anchored extraction works and yields almost nothing.** Anchoring on a
heading — `MOST FIELD GOALS MADE` — and reading the rows beneath gives clean,
meaningful records:

```
MOST FIELD GOALS MADE      38  Stephen Gostkowski, 2013
MOST ATTEMPTS             336  Bobby Layne, 1950
```

But **only 466 of 11,005 record headings (4%) have parseable rows beneath.** The
rest is report 38's OCR damage. And even a clean-looking block carries errors —
one Lions list of *attempt* totals around 330 contains `3829 BILL MUNSON, 1968`,
a yardage figure bled into the wrong column.

**A line without its heading is meaningless.** "18 Dalton Hilliard, 1989" — 18
what? The measure lives in the heading; line-level matching discards it.

**And these are CLUB records, not league.** Gostkowski's 38 is a Patriots record.
The bios want *the league*.

## Which is why I checked whether league leaders were computable — and they were not

They should have been. 1.9 million statistics are loaded. So:

```
NFL 1963, top by "Yds":
   3,678  Danny Villanueva      <- a punter
   3,481  Johnny Unitas
   3,311  Tommy Davis           <- a punter
```

**`Yds` means a different thing in every table** — passing, rushing, receiving,
punting, returns — and my ingest stored the column name without the table.
Johnny Unitas and a punter both hold `Yds = 3481`, and nothing distinguishes them.

**This is the exact error I had just diagnosed in the guides**, committed in my
own ingest, at a scale of 1.9 million claims. *A line without its heading is
meaningless* — and I had written every statistic that way.

**It is also the salary lesson in another field.** There is no predicate called
`salary` because the convention belongs in the name. There must be no predicate
called `Yds` either.

### And the source was telling me all along

Every table is preceded by an `<h2>`:

> Passing · Rushing · Receiving · Kicking · Punting · Punt Returns · Kick Returns
> · Interceptions · Defense and Fumbles · Total Scoring

**Not a modelling choice — a fact the source states that I was discarding.**

## The fix

Predicates are now `table.column`: `passing.Yds`, `rushing.Yds`,
`defense_and_fumbles.Tackle`. A table with no heading is **refused**, not stored
ambiguously. All 217 league-seasons re-ingested: **1,900,503 claims, all
qualified.**

`gate_statistics_name_their_table` refuses any bare ambiguous column
(`Yds`, `No.`, `Avg.`, `Long`, `TDs`, `Att`, `Int`, `Fum`). It fires on a
constructed claim of bare `Yds = 3481`.

### League leaders, now

| | computed | record |
|---|---|---|
| NFL 1963 `rushing.Yds` | **Jim Brown 1,863** | Jim Brown 1,863 |
| NFL 1963 `passing.Yds` | **Johnny Unitas 3,481** | Unitas 3,481 |
| NFL 1972 `rushing.Yds` | **O.J. Simpson 1,251**, Larry Brown 1,216 | — |

*On that last one: I wrote "Larry Brown led 1972" in my own check note. Brown was
MVP that season; Simpson led the league. The data was right and my note was
wrong — recorded because the whole point of checking against the record is that
it catches me, not only the pipeline.*

**Superlatives are now computable** — a max over `(league, season, predicate)` —
without the guides at all.

## What that means for the records sections

**They are worth much less than they looked, and only for what cannot be
computed.**

- **League leaders: computable.** Don't need the guides.
- **Club records: 4% extractable**, OCR-damaged, and duplicative of what a max
  over club-seasons already gives.
- **Genuinely absent and only in the guides:** single-game records
  (`Passing Yards: 510, vs. Cincinnati, Nov. 19, 2006`) — the archive holds no
  game-level data at all, which is the deferred subject-shape question.
  **2,288 such lines matched, and they are the cleanest shape in the corpus.**

So the records sections are not the route to superlatives. **Computation is.**
Their unique contribution is single-game marks, which land squarely in the
game-level design question rather than in front of it.

---

**12 gate suites pass. 1,900,503 statistics claims, every one naming its table.**
