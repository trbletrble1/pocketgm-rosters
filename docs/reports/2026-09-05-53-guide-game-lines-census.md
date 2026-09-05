# 53 — The guide parse: a census, a defect in my own scoping, and what home/away actually costs

2026-09-05. **Measurement only. Nothing written to the store.**

The word was given to parse the guides' result lines into `("game", …)` subjects.
The census came first, and it changed the plan twice.

---

## 1. The first census was wrong, and wrong in a way I have been wrong before

My first pass matched any line opening with a date token and containing a score.

> **1,273,139 "game-shaped lines"** — against report 52's estimate of ~340,000.

The excess was not discovery. It was `11/16/33` (a birthdate), `6-0, 190` (a
height and a weight), and `Montana, Joe 60-33` (completions and attempts).

**This is the lesson `gate_statistics_name_their_table` already taught, for the
third time: a column is named by the header above it, not guessed from its
shape.** I wrote that gate for `Yds` and then, in a new file, went straight back
to inferring meaning from a line's silhouette.

Header-anchored — a line counts only inside the run beneath a header row that
names the columns:

> **150,716 rows under 19,045 headers, 43 distinct header signatures.**

**An 88% reduction.** The examples are now overwhelmingly real games.

## 2. The section context is not trustworthy, and it was about to poison the record

| context | rows |
|---|---|
| regular | 84,207 |
| preseason | 16,417 |
| **postseason** | **50,092** |

**50,092 postseason rows is impossible** — the league plays about eleven
postseason games a year. The tracker is sticky: once a short line matches
`Playoff`, every subsequent row inherits it until the next heading. Fill-forward,
again.

**It matters because the 49ers 1998 guide prints its four-game August block in
exactly the shape of the regular-season block directly beneath it.** A parser
that trusted this would have mixed exhibition games into the record silently.

**Section context is not usable yet and no claim may depend on it.**

## 3. The checksum I was counting on covers 2% of blocks

Report 52's plan was to let the guides' redundancy outvote the OCR. The strongest
form of that was the season block that declares its own record — `1960 (Won 5,
Lost 8, Tied 1)` — which validates the lines beneath it rather than trusting them.

> **384 of 19,045 headers have a declared W-L-T within twelve lines. 2.0%.**

The checksum is real and it is nearly absent. It can verify a sample; it cannot
police the corpus.

## 4. Nearly half the blocks cannot be dated from local context

> **10,502 of 19,045 headers (55%) have a year within twelve lines.**

The guides print the month and day on the line and the year in a heading that is
often further away than twelve lines, or lost. **The year is the expensive field,
exactly as feared, and 45% of blocks will need a wider or a different rule.**

## 5. The guides are a 1960s-onward backbone, not a 1920s one

Rows whose year was recoverable, by decade:

| | | | | |
|---|---|---|---|---|
| 1920s | **81** | 1970s | 9,452 |
| 1930s | **606** | 1980s | 8,927 |
| 1940s | 1,276 | 1990s | 12,224 |
| 1950s | 1,171 | 2000s | 16,884 |
| 1960s | 6,892 | 2010s | 14,065 |
| | | 2020s | 7,659 |

**1920–1959 yields 3,134 dated rows in total.** Report 52 called the guides "the
pre-1999 backbone". Measured, that is true from about 1960 and false before it:
the earliest decades are thinner than PFA, which has 524 boxscore pages for the
1920s against the guides' 81 dated rows. **A correction to my own report of four
hours ago.**

## 6. Home and away is encoded as an absence, and that is the real cost

A guide marks an away game with `at` and a home game with nothing:

```
08/09 W 21-17 Seattle 50,153          <- home
08/23 LL 17-31 at Denver 69,874        <- away
```

Across the biggest family, **37.7% of rows carry `at`**. A full season log should
be near 50%. **The gap is OCR dropping the word — and a dropped `at` silently
converts an away game into a home one.** Within a single line there is no way to
tell a lost marker from a home game, because both look like nothing.

And in the 1960s Bills format the site column survives as
`PYRPIPYrpriicririyipy` — a column of single characters with the alignment gone.
**Home/away is not merely damaged there, it is destroyed.**

**The recovery is the pair, not the line.** Every game appears in both clubs'
guides with opposite polarity, so a game is confirmed when two guides disagree
about who was away in the right direction. That is a resolution rule, not a
parsing rule, and it is what the claims store is for.

## 7. Two columns printed side by side become one line

```
Fri., Aug. 10* 17-33 L Houston Oilers Atlanta, Ga. 11,50 Sat., Aug. 7* 24-30 L Kansas City Chiefs Univ.
```

Two seasons printed in parallel, OCR'd into one row. **A left-to-right parser
takes the first game and drops the second without erroring** — 821 headers and
5,246 rows in this family alone. Note also `11,50`: the attendance is truncated
at the column boundary, so attendance in these families is not readable either.

## 8. `Date+attendance+starter`: 209 headers, 0 rows

**That is not an absence of data. It is a parser that failed and reported
nothing** — the empty-versus-failed distinction, now for the sixth time. 209
headers were found and nothing was read beneath them.

## 9. One thing is better than report 52 said

`Date Opponent P/S …` — the per-player game log — carries `P` (played), `S`
(started) and `INACTIVE—KNEE` per man per game.

> **1,750 headers, 27,481 player-game rows, and 94.3% carry `at`/`vs.`** — the
> cleanest home/away in the entire corpus.

**Report 52 said Pro Football Archives was "the only source of starting lineups".
That is wrong.** The guides carry started-versus-played per player per game, for
free, already on disk, with the home/away marker intact. PFA remains the only
source for the *pre-modern* era, which is a much narrower claim than the one I
made.

---

## What this changes

| report 52 said | measured |
|---|---|
| guides are the pre-1999 backbone | true from ~1960; **3,134 dated rows before 1960** |
| redundancy outvotes the OCR | the declared-record checksum covers **2%** of blocks |
| PFA is the only lineup source | **wrong** — 27,481 player-game rows in the guides |
| ~340,000 result lines corpus-wide | **150,716 header-anchored rows** in 1,803 files |

**Nothing has been written to the store.** Four things must be settled before a
line becomes a claim: the year rule for the 45%, the section context, the
two-column split, and the away-marker pairing. The first three are parsing; the
fourth is resolution, and it is the one the store was built for.

`dataset/build-reports/game-lines-census.json` carries all 43 signatures.
