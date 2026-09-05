# 37 — What Pro Football Archives contains (characterisation 4 of 4)

2026-09-04. Characterisation only. Nothing fetched at scale — a handful of each
page type, which is what decided the finding below.

We took 418 early-league pages because that is what we needed. The CDX
enumeration listed **120,687 pages**.

## The finding that decides the scope

**Four page types no longer exist on the live site.**

| type | pages in the archive | live? |
|---|---|---|
| weather | 4,784 | **404 — 6 of 6 sampled** |
| transactions | 3,945 | **404 — 6 of 6 sampled** |
| stats (league leaders) | 769 | **404 — 6 of 6 sampled** |
| officials | 138 | partial — 2 of 6 resolve |

Confirmed against the site's own navigation: the homepage carries **45 links, and
zero** to transactions, weather, stats or officials. Drafts, boxscores, awards,
gamelogs and coaches are all linked.

**So ~9,500 pages exist only in Wayback.** That matters because the whole reason
for the CDX approach was *enumerate from the archive, fetch from the live site*.
For these four types that route does not exist, and the alternative is the one
ruled out at the start — pulling content from Wayback, where snapshots are patchy
and mix dates.

**This is why a handful of each was worth fetching before deciding what to fetch
at scale.** A crawler would have discovered the same thing by 404-ing 9,500 times.

## What the live types carry

**Boxscores — 4,929 pages.** Per-game, and richer than expected: score by
quarter, scoring plays, **and full lineups**. 57–67 distinct player ids per page.
Sampled 1972, 1991, 2000.

```
Score By Quarters | 1st | 2nd | 3rd | 4th | Final
Qtr | Team | Scoring Plays
LINEUPS | Detroit Lions | Offense | Defense | Chicago Bears
```

**A starting lineup per game is a claim type nothing in this dataset holds** —
StatsCrew gives games-started as a season count, not who started which game.

**Drafts — 392 pages.** `Round · Overall · Team · Player · Pos · College · Notes`.
The 1968 AFL-NFL draft page carries **457 player ids**; 2013 carries 252. Draft
position is a fact the dataset does not hold at all, and the `Notes` column
plausibly carries the trade conditions that Mackey's compensation awards describe
from the other side.

**Gamelogs — 3,593 pages, one per player.** Per-game statistics broken out by
category (`KICKOFF RETURNS`, `INTERCEPTIONS`, `PUNT RETURNS`), with
`DATE · YEAR TEAM · AHN · OPP · SCORE · RES · NO · YDS · AVG · LG · TD`. This is
**game-level statistics**, a granularity below anything currently planned — the
StatsCrew fetch running now is season-level.

**Playoffs — 3,424 pages**, per player, separating postseason statistics from
regular season. The season-phase distinction that also surfaced in the media
guide census, from a second source.

**Awards — 258 pages.** `Offense · Position · Team · Selectors` — and *Selectors*
is the interesting column: it names **who gave the award**, which is an
attribution the dataset's provenance model is built to carry.

## What this changes

- **Boxscore lineups and gamelogs are game-level data.** The dataset's whole
  structure is season-level. This is not more of what we have; it is a level
  below it, and it would want its own subject shape before a single page is
  ingested.
- **Draft position** is absent from the dataset and available here for both
  leagues, back to the 1930s.
- **Award selectors** are a named-attributor claim, which fits the existing model
  exactly.
- **~9,500 pages are Wayback-only** and, under the standing ruling against
  Wayback content, are effectively out of reach — including all 3,945
  transactions pages, which would have been the movement history.

**Nothing here should be fetched until a subject shape for game-level facts is
ruled on.** Boxscores alone are 4,929 pages and would multiply the store by a
different axis than statistics does.
