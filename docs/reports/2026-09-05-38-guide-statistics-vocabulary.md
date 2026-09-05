# 38 — The guides' statistical vocabulary, and a correction

2026-09-04. Characterisation only. Nothing extracted.

You asked whether the guides' statistics are worth having, on the grounds that
they are season-level, already on disk, and cover eras StatsCrew is thin on.

**Two of those three hold. The third has a measured problem.**

---

## First, a correction to report 34

Report 34 said *"the guides are a statistics source"* on the strength of heading
frequency — `SCORING` 1,558, `PASSING` 1,537, `RUSHING` 1,536, in ~1,500 of 1,803
files.

**I counted headings and inferred tables without reading what sits under them.**

Measured on **15,076 statistical headings across 220 guides**:

| what follows the heading | share |
|---|---|
| prose / other | **41%** |
| records and leaders (`MOST`, `FEWEST`, career highs by game) | **29%** |
| numeric block, unclassified | 14% |
| **per-player table** | **9%** |
| game-dated highs | 4% |

A `PASSING` heading in the 1999 Colts guide opens *"COLTS (SEASON) / MOST FEWEST
/ 190 1998 66 1953"* — a team records table. In the 2007 Colts guide it opens
*"Attempts: 31 at Seattle 12/24/05"* — one player's career highs.

Both are statistics. **Neither is the per-player season table I implied.** The
claim was an inference from a word count — the same error report 34 was written to
correct in report 11, one level up.

---

## The vocabulary, where the tables are real

The per-player tables do exist, and their column vocabulary is consistent and
legible across eras:

```
No. Yds. Avg. LG TD                        164     (receiving / returns)
NO YDS AVG FC LG TD                        146     (punt returns - FC = fair catch)
No. Yds Avg Long TD                         93
No. and Yards Kickoff Returns               93
No. and Yards Interception Returns          92
Att. Cmp. Yds. Pct. TD Int LG Rating        74     (passing)
CMP% YDS/ATT 1D 1D% INT                     72
```

**`FC` — fair catches — is a column StatsCrew's return tables do not carry.** So
the guides are not purely a subset.

## The problem, measured

**12,644 candidate statistical header rows in 300 guides** — extrapolating to
roughly 76,000 across the corpus. But:

> **Only 33% have data rows that align to their header. 66% are OCR-damaged.**

Alignment here is generous: a row counts as clean if its numeric fields match the
header width. Two thirds fail even that.

The damage is visible in the vocabulary itself — **`1D` appears for `TD`** in 72
header rows, and `LG` / `Long` / `LC` vary for the same column. A worked example
of a *header that parsed cleanly* with rows that did not:

```
Att. Cmp. Yds. Pct. TD INT LG Rating
KOON. 2 icee cree aewe  147 1983 536 9 16 64 638
```

The column names survived. The player's name did not, and neither did the
alignment of his numbers.

## What this means for the ruling

**The guides are a corroboration source for statistics, not a primary one.**

- **Season-level: yes.** Same shape as StatsCrew, no new subject needed.
- **Covers thin eras: yes** — and `FC` shows they carry columns StatsCrew lacks.
- **Reliable at the value level: no.** Two thirds of tables are unusable as they
  stand, and the failure is silent: an OCR-mangled row still parses into numbers,
  it just parses into the *wrong* numbers.

That last point is why this should not be ingested alongside StatsCrew as though
it were equivalent. A wrong statistic that looks right is the photo-set problem
in another field — and here there is a clean source to check against, which is
exactly how it should be used: **ingest the guides' statistics only where
StatsCrew has nothing, and mark every value with its OCR-alignment status.**

**I would not do that until the StatsCrew statistics are in and their coverage
gaps are known**, because "eras StatsCrew is thin on" is currently an assumption.
The fetch running now will say which eras those actually are.

---

**Statistics fetch: 1,341 pages, through 1996, zero failures.**
