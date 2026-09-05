# 55 — The number pinned, and the all-time-series lines counted

2026-09-05. **Measurement only. Nothing written, nothing rebuilt, nothing demoted.**

---

## 1. The two heading figures — not a refinement, two populations

| population | files | BAREYEAR hits | of which `YYYY (Won x, Lost y)` |
|---|---|---|---|
| **all files** | 1,803 | **2,893,183** | 150,174 — **5.19%** |
| club guides only | 1,755 | 2,323,140 | 148,342 — 6.39% |

`measure_guide_mirrors.py` returns early on league-wide books — the *NFL Record
and Fact Book* and its kin — so **detector 1 never saw the 48 league-wide files.**
Its 2,320,581 figure is *adjacent pairs*, not hits: hits minus files-with-hits
gives 2,321,390 against 2,320,581 reported, a residual of 809 (0.03%).

> **The figure to use is 2,893,183, across all 1,803 files.** The 5.19% and the
> 150,174 are computed on that same population and are consistent.

**One correction to how that arithmetic reads.** 5.2% × 2,893,183 ≈ 150,400 and
"150,174 declared-record headings" are **not two measurements converging — they
are one measurement stated twice.** The 5.2% bucket *is* the declared-record
count as a percentage. The conclusion still holds, but it rests on the
independent plausibility check — **83 headings per guide is about what a club's
full reprinted history should have** — and not on a corroboration that isn't there.

Also worth noting: the club-only rate is **6.39%**, not 5.19%. The league-wide
statistical compendia are *noisier* than the club guides, which is what you would
expect of a book that is mostly tables.

## 2. The all-time-series lines — counted

Tight patterns, so these are **floors**.

| form | lines | positional marker |
|---|---|---|
| **A** — `1954—Colts 17-13 (B)` | **255,058** | **89.5% carry a venue code** |
| **B** — `1967 — PACKERS 33, Raiders 14` | **38,748** | 61.8% carry `at`/`@` |
| **total** | **293,806** | |

**Against 150,716 header-anchored game rows, that is nearly twice as many — and
every one carries its own year on the line.**

By the line's **own** year, which is not carry-forward and not a heading:

| decade | series lines | header-anchored dated rows | ratio |
|---|---|---|---|
| 1920s | **1,900** | 81 | **23×** |
| 1930s | **9,918** | 606 | **16×** |
| 1940s | 12,700 | 1,276 | 10× |
| 1950s | 16,945 | 1,171 | 14× |
| 1960s | 45,175 | 6,892 | 6.6× |
| 1970s | **62,047** | 9,452 | 6.6× |
| 1980s | 55,002 | 8,927 | 6.2× |
| 1990s | 42,002 | 12,224 | 3.4× |
| 2000s | 31,037 | 16,884 | 1.8× |
| 2010s | 14,468 | 14,065 | 1.0× |

**The gain is largest exactly where report 53 said the corpus was thinnest.**

**And they fail loudly, as predicted.** The decade table contains 3 lines dated
to the 1820s, 71 to the 1870s and one to the 2040s — **~280 of 293,806, 0.1%.**
A football game in 1874 is visibly wrong. Compare the game-log format, where a
dropped `at` is *invisible*. Venue is positively encoded here: a missing `(B)`
leaves a line with no venue, not a line that silently reads "home".

### What is NOT measured, and must not be assumed

- **293,806 lines are not 293,806 games.** Every guide reprints the full series,
  so this is heavily duplicated. **The distinct-game count is unmeasured.** The
  duplication is the outvoting substrate, but it is not coverage.
- **Form A names the winner, not the opponent.** The other club comes from the
  section heading — so a proximity dependency remains for the *opponent*, though
  not for the year. Form B names both and needs no section at all.
- **The venue codes are undecoded.** `(A)`, `(B)`, `(W)`, `(GB)`, `(SF)` are
  presumably city or club initials, and `(B)` alone could be Baltimore, Boston or
  Buffalo. Decoding them is its own job with its own ambiguity problem.

## 3. Held open

Both rulings are Ryan's and neither has been acted on. **The mirror set has not
been demoted** — no code or declaration changed. **The heading detector has not
been rebuilt.** Counting first was the cheap order, and the count says the series
lines are dense: about twice the header-anchored rows overall and an order of
magnitude better before 1960.
