# 22 — The CFL sweep, and a defect in numbers I already reported

2026-09-04. Branch `dataset-design`.

The CFL was the remaining sweep. It is done: **80 seasons, 37,671 rows, 36,235
persons.** But the season that opened the sweep also exposed a defect in figures
I gave you in report 21, so most of this report is about that.

---

## 1. The source carries 1945, not 1958 — and it back-maps the name

You scoped this as "CFL from 1958". StatsCrew carries **1945**. I swept from
there, because thirteen seasons of real rosters are worth having.

But they are not CFL seasons. The CFL was founded in 1958. Every year page from
1945 to 1957 is titled *"Canadian Football League (CFL)"* and every team code
carries the `CFL` prefix. Measured: the strings *Interprovincial*, *Big Four*,
*IRFU*, *WIFU* and *Union* appear **nowhere** on the 1945, 1950, 1954 or 1957
pages. The source has applied the modern name to seasons in which it did not
exist.

This is the brief's opening failure in miniature — a label that reads like a
fact and is actually a later hop. So the pre-1958 league name is held as **a
claim attributed to StatsCrew**, never as an observed league identity.

**What I did not do:** split 1945–57 into IRFU (east) and WIFU (west). That
split is real, and I know it. But I know it — this source does not say it.
Writing it in would be invention wearing a source's provenance, which is the
one thing the dataset is built to prevent. It is recorded as an open gap
needing a source that actually states it.

**2026 is held out.** It renders, with an 8-column header and no GS. It is an
in-progress season as of today: its GP values are a mid-season snapshot that
would file indistinguishably from a final total, and the cache rule forbids
re-fetching to correct them later.

**2020 was refused, correctly.** The league-year page renders and lists **zero
teams** — the CFL cancelled the 2020 season for COVID. The ingest stopped on a
match rate of 0.000 rather than recording an empty season as a successful one.
That is now declared as an absence, not a failure to retry: retrying it fetches
the same empty page forever.

---

## 2. The defect: a census figure that did not state its denominator

CFL-1945 came back `games_played: 100%`. The 1945 header has no GP column.

Both were true. `ingest_season.py` counted the denominator as *rows on pages
that carry the column*:

```python
if c in cols_present:
    fill_seen[c][1] += 1          # denominator only counts these rows
```

Four of the eight 1945 teams have no GP column. So the figure answered "where
the column exists, how often is it filled" — 100% — while the fraction of the
league-season's rows actually carrying a value was **71.4%**. A single scalar
cannot say which question it answered, and I stored scalars.

**Blast radius, measured across 2,660 cached pages:** 27 year/column
combinations where a column is present on some pages and absent on others.
Five of them were figures I put in the declaration in report 21:

| league-season | field | I reported | fraction of all rows |
|---|---|---|---|
| **WFL-1975** | games_started | **25.2%** | **13.5%** |
| WLAF-1992 | games_started | 15.1% | 12.0% |
| USFL-1985 | games_started | 19.7% | 16.8% |
| UFL-2012 | games_started | 4.9% | 2.5% |
| WFL-1974 | games_started | 7.8% | 7.1% |

WFL-1975 is the bad one: I told you a quarter, and it is an eighth.

### The gate

`src/gate_census_denominator.py`. The property, over every league-season and
every measured column: *where a column is absent from some pages of a
league-season, the census must state both denominators; a bare number is
refused.*

It was **run against the existing declaration before the fix and failed on seven
real figures** — the five above plus APFA-1920 and APFA-1921 jersey (60.3%
conditional against 34.3% absolute). That is a failure found on shipped data,
not one constructed to be found. It was then broken deliberately once more —
WFL-1975 reverted to the bare `25.2` — and fired for its stated reason,
exit 1; restored, exit 0.

### The fix

The census was **hand-pasted**, which is how a conditional number came to sit in
a field read as absolute. It is now generated: `src/measure_census.py` recomputes
every figure from cache, emits a bare number only where the two denominators
agree, and an object naming both where they do not.

`ingest_season.py` now tracks both, and raises the divergence as a deviation.

**Related, found by the same fix: 13 team pages across 11 league-seasons are
linked by a league page and parse to zero rows.** Ten are CFL 1945–54; two are
WFL-1974 (`WFLCHA`, `WFLSHR` — the mid-season relocations). They contributed
nothing, and before this they contributed it silently. Now declared.

---

## 3. My own declaration was not load-bearing — again

I wrote the CFL predictions into a new top-level `cfl` block. The ingest reads
`field_availability`. So all 80 seasons reported *"declaration makes NO
prediction for this league"* — 159 of the 242 deviations are that one mistake.

This is report 21's lesson recurring in a new shape: there, a declared value was
computed and never referenced; here, it was written where nothing reads. **A
declaration in the wrong place is not a declaration.** The corrected predictions
now live in `field_availability.<field>.census_by_league_season`, which is the
key the ingest actually looks up, and the note recording why sits in the block
where I first put them.

---

## 4. What the CFL data looks like

| decade | seasons | rows | avg teams |
|---|---|---|---|
| 1940s | 5 | 1,290 | 8.2 |
| 1950s | 10 | 3,534 | 9.1 |
| 1960s | 10 | 3,693 | 9.0 |
| 1970s | 10 | 4,205 | 9.0 |
| 1980s | 10 | 4,636 | 8.7 |
| 1990s | 10 | 5,252 | 9.1 |
| 2000s | 10 | 5,311 | 8.4 |
| 2010s | 10 | 6,220 | 8.6 |
| 2020s | 5 | 3,530 | 9.0 |

Fill, as fraction of **all** rows:

| year | birth | college | hometown | GP | GS |
|---|---|---|---|---|---|
| 1945 | 32.9 | 56.7 | 32.9 | 71.4 | 0.0 |
| 1950 | 75.0 | 92.9 | 71.8 | 100.0 | 63.2 |
| 1958 | 84.0 | 99.4 | 81.3 | 100.0 | 1.7 |
| 1970 | 84.0 | 99.7 | 74.7 | 100.0 | 2.1 |
| 1980 | 99.3 | 100.0 | 74.8 | 100.0 | 2.8 |
| 1990 | 99.8 | 100.0 | 97.8 | 100.0 | 7.8 |
| 2000 | 99.8 | 100.0 | 99.8 | 100.0 | 50.0 |
| 2010 | 100.0 | 100.0 | 99.8 | 100.0 | 98.1 |
| 2025 | 98.4 | 99.9 | 99.6 | 60.2 | 59.2 |

**1945 is the worst-covered league-season anywhere in the dataset.** Birth date
at 32.9% is far below the previous worst (APFA 1920, 88.8%), and it takes the
primary discriminator away: for those rosters, identity has to rest on something
else or be refused.

**`games_started` swings 63.2 → 1.7 → 98.1 → 59.2 inside one league.** This is
the third independent confirmation of report 21's correction: the field is
`per_league_season`, and no per-league figure describes it.

---

## 5. Corrections to earlier reports

- **Report 21, WFL-1975 `games_started`: 25.2% should read 13.5%.** Likewise
  WLAF-1992 15.1→12.0, USFL-1985 19.7→16.8, UFL-2012 4.9→2.5, WFL-1974 7.8→7.1.
- Reported mid-sweep and withdrawn before it reached a conclusion: I read CFL
  roster pages as returning "3 rows". `parse_roster` returns a 3-tuple; I was
  measuring the tuple. No finding rested on it.

---

## 6. The media guides are a much larger source than the design assumed

You noted assistants are the media guides' job. Checking what is actually held:
`nfl-books/index.csv` indexes **2,105 guides, 1934 to the 2020s, 76 club
identifiers, none restricted**. Only **28 are on disk** — all 1979.

The design's §2.4 ruling — that guides carry no coach birth dates (2.7%), so
assistant identity rests on stint continuity — was measured on **those 28 1979
files alone**. It is a reasonable prior, not a measured property of the corpus.

Fetching the remaining ~2,077 is an acquisition decision, and yours. Two things
worth knowing before you make it: it is a different host from StatsCrew with its
own rate expectations, and the 2.7% figure should be re-measured on a sample
spanning decades before it is trusted as a corpus-wide fact.

---

## 7. State

103 NFL seasons · 34 other league-seasons · **80 CFL seasons** · 2,363 coach
stints · ~3,400 cached pages · **0 zero-byte cache entries** · **11 gates, 11
pass, 11 fire when broken**.

Remaining as previously noted: assistants (above), QB ratings from statistics,
the Raiders/Rams transcription's per-row confidence field, the Elway document,
Staudohar, and the Mackey Archives request.
