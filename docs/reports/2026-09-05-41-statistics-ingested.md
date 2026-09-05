# 41 — Statistics ingested

2026-09-05. **217 league-seasons. 0 failed.**

> **1,933,217 statistics claims. The archive goes from 1,405,895 to 3,339,112 —
> 2.4×, and 1,424 MB on disk.**

| | |
|---|---|
| observed | 1,864,936 |
| **`source_derived`** | **68,281** |
| denotations | 307,995 |
| stores written | 217 |

**I predicted ~1.37 million and it is 1.93 million.** The estimate was made before
the two-row-header fix, which recovered about 40% more rows. So the archive
*more than* doubles rather than doubling — the direction of my error was toward
under-counting, because I measured a corpus I was still parsing wrongly.

| league | claims | | league | claims |
|---|---|---|---|---|
| **NFL** | 1,337,991 | | XFL | 12,740 |
| **CFL** | 446,049 | | UFL | 10,276 |
| AFL | 43,835 | | USFL2 | 8,934 |
| USFL | 24,818 | | WLAF | 7,404 |
| AAFC | 17,334 | | AAF | 4,597 |
| WFL | 13,278 | | UFL2 / APFA | 4,349 / 1,612 |

---

## Verified against the record, not against plausibility

The parser fix was confirmed on Billy Grimes. The ingest is confirmed on someone
harder to be accidentally right about:

> **Jim Brown, Cleveland 1963 — `No. 291`, `Yds 1863`, `Avg. 6.4`, `TDs 12`.**

That is the season exactly as recorded. A shifted or misaligned table cannot
produce four correct values in a row.

And the anachronism, still correctly marked at scale:

> **Tobin Rote, Green Bay 1950 — `Att 224`, `Comp 83`, `Yds 1231` all `observed`;
> `Rating 26.7` `source_derived`.**

## The gate's real test, at full scale

> **12,150 `Rating` claims across the corpus. Zero filed as `observed`.**

`gate_anachronism` had 68,281 chances to fire — every calculated cell — and fired
on none, because the ingest never offered it one. A gate that passes because the
violation was made unreachable is the outcome the design asks for; a gate that
passes because it was never tested is not, and this one was constructed against
the real case before any statistics existed.

**All 9 gate suites pass.**

## Deviations

**291 across 217 league-seasons — 1.3 per season.**

| | |
|---|---|
| CFL | 176 |
| NFL | 86 |
| UFL | 16 |
| everything else | 13 |

Concentrated in `FRec`, `FYds`, `FF` (fumbles) and `2Pt`, `Saf` (scoring), and
they are season-to-season variation inside a decade rather than defects — the
declaration predicts a league-decade figure and individual seasons move around
it. `CFL-2013 FRec: declared 63.2, actual 22.0` is one season differing from its
decade, not a parse failure.

**They are recorded, not suppressed.** The threshold is 20 points; loosening it
would make them vanish without making them untrue.

---

## What the archive now holds

| | |
|---|---|
| people (unified) | 40,745 |
| roster stores | 217 league-seasons |
| **statistics stores** | **217 league-seasons** |
| coach stints | 2,363 head + 1,086 assistant |
| photos denoted | 20,779 |
| salary figures | 182 |
| **total claims** | **3,339,112** |
| disk | 1,424 MB |

**A player page now has something to say.** Jim Brown resolves to one person
across his career, with per-season statistics attached to `(person, season,
club)`, a photograph where the name is unambiguous, and the era-native position
the source recorded.

## Owed

- **The game-level ruling**, now that volume is known: 1.4 GB for season level, so
  scale is not the objection. Boxscore lineups and gamelogs remain a different
  axis needing a subject shape.
- **`Single` is 100% filled in every league**, including those with no such
  scoring play, because the source writes `0` rather than leaving cells empty.
  Fill is not applicability. Nothing in the current checks can tell the
  difference, and any consumer reading `Single` outside the CFL will read zeros
  as measurements.
