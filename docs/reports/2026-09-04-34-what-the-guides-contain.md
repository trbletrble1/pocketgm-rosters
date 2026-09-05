# 34 — What the media guides contain (characterisation 1 of 4)

2026-09-04. Characterisation only. Nothing extracted.

Report 11 surveyed **28 files, all 1979**. This is **1,803 files across ten
decades**, reported per decade rather than pooled — because a 1939 guide and a
2019 guide are different objects, and pooling hides exactly that.

## Section presence, share of guides in each decade

| section | 1930s | 1940s | 1950s | 1960s | 1970s | 1980s | 1990s | 2000s | 2010s | 2020s |
|---|---|---|---|---|---|---|---|---|---|---|
| *(files)* | 4 | 42 | 85 | 139 | 207 | 248 | 265 | 274 | 324 | 215 |
| coaching staff | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 96 | 99 |
| roster | 100 | 83 | 78 | 94 | 100 | 99 | 100 | 99 | 96 | 99 |
| records | 50 | 92 | 100 | 95 | 100 | 100 | 100 | 100 | 97 | 100 |
| schedule / results | 50 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 97 | 100 |
| history | 100 | 90 | 100 | 97 | 100 | 100 | 100 | 100 | 96 | 100 |
| stadium | 75 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 97 | 100 |
| media info | 50 | 92 | 100 | 100 | 100 | 100 | 100 | 100 | 96 | 99 |
| medical staff | 100 | 76 | 91 | 91 | 96 | 97 | 99 | 98 | 95 | 99 |
| opponents | 100 | 78 | 98 | 92 | 100 | 99 | 100 | 99 | 96 | 99 |
| **career statistics** | **0** | 69 | 97 | 94 | 100 | 100 | 100 | 100 | 96 | 100 |
| **draft history** | **0** | 66 | 89 | 97 | 100 | 100 | 100 | 99 | 96 | 99 |
| front office | 50 | 50 | 78 | 98 | 99 | 100 | 100 | 99 | 96 | 100 |
| **transactions** | **0** | **0** | 2 | 3 | 23 | 27 | 58 | 89 | 92 | **95** |
| all-time roster | 0 | 0 | 2 | 32 | 48 | 56 | **73** | 71 | 66 | 59 |
| **player bios** | 0 | 9 | 29 | 38 | 53 | 72 | **81** | 63 | 50 | **39** |
| pronunciation | 0 | 7 | 3 | 21 | 35 | 47 | **51** | 44 | 39 | 32 |
| community | 25 | 38 | 45 | 62 | 90 | 99 | 100 | 99 | 96 | 100 |
| cheerleaders | 0 | 2 | 1 | 9 | 7 | 23 | 35 | **65** | 64 | 61 |

## What the 1979 sample could not have told us

**Three sections did not exist in the early era at all.** Career statistics and
draft history are **0% in the 1930s**; transactions is **0% through the 1940s and
2% in the 1950s**, reaching 95% only in the 2020s. A survey of 1979 guides
reports these as present and gives no hint that they are a *later invention*. For
a 1935 guide, their absence is a fact about the era, not a gap in the file.

**Two sections peak and then decline** — the opposite of what a single-era sample
suggests. **Player biographies** peak at **81% in the 1990s** and fall to **39% in
the 2020s**. Pronunciation guides peak at 51% and fall to 32%. Whatever the cause,
a consumer assuming "modern guide, therefore richer" is wrong on both.

**The only section that is universal across ninety years is the coaching staff**
(96–100% in every decade), which is fortunate, because that is what item 4 rests
on.

## The vocabulary problem, quantified

The census counted **348,988 distinct unmatched headings** — capitalised lines our
eighteen-section vocabulary has no word for. The most frequent are not obscure:

```
1558 SCORING    1537 PASSING     1536 RUSHING    1499 INTERCEPTIONS
1498 PUNT RETURNS  1487 KICKOFF RETURNS  1449 PUNTING  1432 RECEIVING
1136 FIRST DOWNS  1074 FUMBLES  1073 PENALTIES  1066 DEFENSE
```

**These are statistical category headings, appearing in ~1,500 of 1,803 guides.**
Report 11 recorded "per-player career statistics" as one section. The census says
the guides carry a **structured statistical vocabulary of their own** — scoring,
passing, rushing, interceptions, both return categories, punting, receiving,
first downs, fumbles, penalties — in more than four guides in five, across every
era.

That is the same shape as the StatsCrew statistics now being fetched, from an
independent source, and it is the single largest thing in these files that
nothing has looked at.

Also unmatched and frequent: **club names as headings** (`NEW YORK GIANTS` 699,
`GREEN BAY PACKERS` 636), which is the opponents/history sections naming their
subjects, and `REGULAR SEASON` / `PRESEASON` / `POSTSEASON` — a **season-phase
distinction** the dataset does not currently model at all.

## What this changes

- The guides are a **statistics source**, not only a staff-and-bio source. ~1,500
  carry structured statistical headings.
- **Season phase** (regular / pre / post) appears as a first-class division in the
  guides and has no representation in the dataset.
- Section presence is **era-dependent and non-monotonic**, so any future guide
  work must be declared per era, like positions and stat columns.
- The eighteen-word vocabulary is nowhere near enough; the unmatched list is the
  raw material for extending it, and it is now saved in
  `build-reports/guide-sections.json`.
