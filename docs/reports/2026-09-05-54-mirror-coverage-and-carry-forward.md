# 54 — Two numbers: mirror coverage, and what carry-forward gets wrong

2026-09-05. **Measurement only. No parser, no claim, nothing in the store.**

Matching never used the year. A candidate pair was matched on **club pair +
month/day + the unordered score pair**, and only then were the two guides' year
assignments compared.

**44,744 rows** from 1,803 files, **949 mirrored groups**.

---

## 0. What was dropped, and why the coverage figures are a floor

| dropped | rows |
|---|---|
| opponent was an **unmapped** string | 19,033 |
| opponent was an **ambiguous city** | 14,399 |
| **two-column** row (two games OCR'd onto one line) | 8,546 |
| bad date | 1,423 |
| impossible score | 137 |

Opponents resolved: **40,075 by unambiguous city, 4,669 by nickname.** Guides
print cities, not nicknames, and a city names a franchise only within a period —
Baltimore is the Colts or the Ravens, Chicago is the Bears or the Cardinals
before 1960. **Resolving those by a carried-forward year would be circular**, so
they are dropped. Every coverage number below is therefore **a floor**, and the
14,399 ambiguous rows are the visible headroom.

**A selection effect worth stating.** I excluded headers carrying a venue column,
because venue text pollutes the opponent residue. That is the *older* guide
layout, so the surviving rows come overwhelmingly from guides published 1990 and
later — reprinting all eras, but modern books.

---

## MEASURE 1 — mirror coverage

**The decade axis below is contaminated.** It bins each row by its carry-forward
year, which is the value under test: a row wrongly carried into 1925 is *reported*
as a 1920s row. The 1920s and 1930s figures are almost certainly mislabels, not
coverage.

| decade (carry-forward) | rows | mirrored | coverage |
|---|---|---|---|
| 1920s | 581 | 192 | 33.0% ← distrust |
| 1930s | 769 | 182 | 23.7% ← distrust |
| 1940s | 458 | 1 | **0.2%** |
| 1950s | 1,332 | 184 | 13.8% |
| 1960s | 4,155 | 1,073 | 25.8% |
| 1970s | 4,472 | 1,044 | 23.3% |
| 1980s | 6,835 | 2,059 | 30.1% |
| 1990s | 8,273 | 2,347 | 28.4% |
| 2000s | 7,964 | 2,152 | 27.0% |
| 2010s | 6,566 | 1,907 | 29.0% |
| 2020s | 3,339 | 890 | 26.7% |

On the **independent axis** — publication decade, taken from the filename and so
uncontaminated by carry-forward — coverage is flat at **24.3% to 28.2%** across
the 1980s to 2020s.

> **Mirror coverage is about a quarter to a third of rows, and it is remarkably
> flat.** The predicted shape — useless in the 1920s, strong in the 1960s–70s —
> is half right: it is genuinely near-zero in the 1940s (0.2%) and weak in the
> 1950s (13.8%), but from 1960 on it does **not** climb with era. It sits at
> 23–30% everywhere.

## MEASURE 1b — home/away agreement, and a control

| axis | agreement |
|---|---|
| by carry-forward decade | 90.9% – 100% |
| **by publication decade** | **95.2% – 97.4%** |

Against chance:

| | |
|---|---|
| rows carrying an away marker | 22,047 of 44,744 = **49.3%** |
| **expected by chance** for two independent rows to differ | **50.0%** |
| **control** — same club pair, *different* fixture, different guides, 3,600 pairs | **49.3%** |
| **observed on mirrored pairs** | **~97%** |

**97% against a 49.3% control.** The mirror is not an artefact. And the control
does double duty: if my matcher were pairing coincidentally-similar *different*
games, agreement would have landed near 50%. It did not, **so the matched pairs
are genuine fixtures** — which is what licenses reading Measure 2 at all.

> **A mirrored pair settles home/away.** That is one working mechanism against
> the silent failure where a dropped `at` turns an away game into a home one.

## MEASURE 2 — carry-forward disagreement

| decade | pairs | disagree |
|---|---|---|
| 1960s | 73 | **83.6%** |
| 1970s | 73 | 57.5% |
| 1980s | 147 | 68.7% |
| 1990s | 175 | 64.6% |
| 2000s | 262 | 79.0% |
| 2010s | 114 | 64.0% |
| 2020s | 60 | 80.0% |

On the independent publication axis: **60.0% – 77.1%.**

**This is a disagreement rate, and disagreement is a lower bound on the error
rate.** At least one guide is wrong in every disagreeing pair, so **naive
carry-forward is wrong at least 60% of the time.** The true rate is higher by
however often both guides fail identically.

**How plausible is correlated failure? More than I would like.** These are
independent books by different clubs in different years, which argues against it
— but they share a layout convention. Both put career-statistics tables in the
same kind of place, and that is exactly what breaks carry-forward. **A shared
cause makes correlated failure plausible, so the gap between 60% and the true
error rate should be assumed real rather than assumed away.**

## Why carry-forward fails — measured, not guessed

My year-heading detector fires **2,893,183 times across 1,803 guides: 1,605 per
guide.** No guide has 1,605 seasons.

| what the line actually is | share |
|---|---|
| other — all-time series lines, running heads, bio lines | 64.0% |
| year alone (heading *or* a stat-column cell — unresolvable) | 18.4% |
| **year + numbers — a career STATISTICS row** | 9.8% |
| **`YYYY (Won x, Lost y)` — a real season heading** | **5.2%** |
| year + lowercase — prose | 2.6% |

`1975 55 746 6 13.6` is a receiving line: receptions, yards, touchdowns, average.
**Carry-forward reads it as a season heading and resets the year to 1975.** A
per-player career table resets it once per player. That is also what detector 1
is really seeing.

**So Measure 2 indicts this heading detector, not the carry-forward idea.** The
idea has not been fairly tested; the implementation is 95% noise.

## The three detectors

**1 — year headings non-decreasing.** 590,128 backwards jumps in 2,320,581
adjacent pairs, **25.4%**. Real, but it is mostly detecting the noise above:
career tables restart at every player. It will be worth far more once the
heading detector is honest.

**2 — rows carried past a season's length.** **464 of 4,022 year-blocks exceed
the bound (11.5%)**, spread across every decade; 28 unchecked because pre-1933
has no fixed schedule. The bound is deliberately generous (regular season + 10),
so these are real overruns, not tight-threshold noise.

**3 — the declared W-L-T checksum. 188 blocks near a game table; 9 matched, 179
did not — 4.8%.** That is my row counting, not the guides: I count only rows in
venue-less families, while the declared record covers the whole season.

> **And a correction to report 53.** I wrote that the checksum "covers 2% of
> blocks". **That was an artefact of my twelve-line proximity window.** Corpus-
> wide there are **150,174 `YYYY (Won x, Lost y)` headings — 83 per guide**,
> which is about what a club's full reprinted history should have. **The
> checksums are abundant. They are simply not adjacent to the tables I anchored
> on.** The 2% figure measured my window, not the corpus.

## One lead, noted and not chased

Among the 64% "other" are all-time-series lines that **carry the year on the row
itself**:

```
1933—Packers, 35-9 (GB)
1990— Buffalo 27, at NE 10
```

Year, clubs, score, and an away marker, with no carry-forward required at all.
Not investigated — noting it because it bears directly on the year question.

---

## The two numbers

| | |
|---|---|
| **mirror coverage** | **~25–30% of rows**, flat from 1960; 13.8% in the 1950s; 0.2% in the 1940s |
| **carry-forward disagreement** | **60–80%**, a lower bound on its error rate |

And the third, unasked but decisive: **home/away agreement of ~97% against a
49.3% control.** The mirror works as a witness. Carry-forward, as implemented,
does not — though what has been shown false is this implementation, not the idea.

**Nothing was written to the store. Whether the year becomes a resolution product
rather than a parse product is Ryan's call.**
