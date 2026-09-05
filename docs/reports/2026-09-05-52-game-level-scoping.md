# 52 — Game-level scoping: three routes, and a hybrid

2026-09-05. **Scoping only. 2.2 MB fetched — nothing at scale.**

The subject is settled (`("game", league, date, away_club, home_club)`,
appearances as `listed_in_lineup`), NFL only to begin. The question was which
source pays for which era.

---

## 1. nflverse — a quarter of the span in one file

**`schedules/games.csv`, 2.2 MB, fetched.**

> **7,548 games, 1999–2026, 46 columns.**

And the columns are the ruled subject exactly: `gameday`, `away_team`,
`home_team` — plus scores, `stadium`, `roof`, `surface`, `temp`, `wind`,
`referee`.

**It also carries cross-reference ids** — `pfr`, `espn`, `pff`, `ftn`, `gsis`,
`old_game_id`. Those are join keys to every other source, which is the thing the
photo set and the position codes both lacked.

Beyond the schedule, the release holds:

| release | span | size |
|---|---|---|
| `pbp` play-by-play | 1999–2025 | **4.3 GB** |
| `weekly_rosters` | 2002–2026 | 306 MB |
| `depth_charts` | 2001– | 247 MB |
| `snap_counts`, `injuries`, `officials` | | 47 / 17 / 2 MB |

**`weekly_rosters` and `snap_counts` are the participation data** — who was
actually available and who played — which is the honest version of the
`listed_in_lineup` question rather than a guess from a boxscore column.

**Verdict: take the schedule now. It is one file and it settles 1999–2026.**
Play-by-play at 4.3 GB is a separate decision and not needed for game-level
identity.

## 2. The media guides — free, and better than report 38 predicted

Already on disk. Report 34 characterised the sections and never looked inside.

> **42,251 date-and-result lines across 220 guides.** Extrapolating, ~340,000
> across the corpus.

A complete game record in one line:

```
11/24 at Detroit Lions Tiger Stadium T 20-20 46,152
9/17  LOS ANGELES RAMS TULANE STADIUM L 13-27 80,879
```

**Date, opponent, venue, result, score, and attendance** — attendance being
something `games.csv` does *not* carry.

**And the OCR is far better here than in the statistical tables.** Report 38
measured 66% of stat tables misaligned. Here:

| | |
|---|---|
| month out of range 1–12 | **1%** |
| day out of range | 0.2% |

*A one-line record survives OCR where a multi-column table does not, because
there is no alignment to lose.*

**The redundancy is the feature.** Every guide reprints its club's full history,
so the same game appears in many guides across many years. That is exactly what a
claims store with resolution is built for: **OCR errors can be outvoted rather
than trusted.** The 1% bad dates are recoverable, not lost.

**Verdict: this is the pre-1999 backbone, and it costs nothing.**

## 3. Pro Football Archives — sparse, but it has what the others don't

**4,929 boxscore pages, 1920–2024.**

| decade | pages | | decade | pages |
|---|---|---|---|---|
| 1920s | 524 | | 1970s | 418 |
| 1930s | 391 | | 1980s | 406 |
| 1940s | 379 | | 1990s | 834 |
| 1950s | **204** | | 2000s | 631 |
| 1960s | 550 | | 2010s | 507 |

**That is ~47 pages a year against seasons of 60–240 games. It is a partial
archive, not a comprehensive one** — the 1950s have 204 pages for a decade of
roughly 700 games.

**So PFA cannot be the backbone.** But it is the only source of the thing the
others lack: **starting lineups**, 57–67 named players per boxscore.

**Verdict: targeted, not swept.** Fetch boxscores where lineups are wanted, not
to build the game list.

---

## The hybrid

| what | source | cost |
|---|---|---|
| game list + results, **1999–2026** | nflverse `games.csv` | **done, 2.2 MB** |
| game list + results + **attendance**, pre-1999 | media guides | **£0, on disk** |
| **lineups**, any era | PFA boxscores | ~4,929 pages, targeted |
| participation, 2002+ | nflverse `weekly_rosters` | 306 MB, later |

**Nothing needs a 20,000-page sweep.** The expensive route was the wrong one:
the modern era is one file, the historic era is already on disk, and PFA is a
supplement rather than a spine.

**What I would do next, on your word:** parse the guides' result lines into
`("game", …)` subjects and let the redundancy resolve the OCR. That is
measurement against data already held, and it would say how much of 1920–1998 the
guides actually reach before a single page is fetched.

**13 gate suites pass.**
