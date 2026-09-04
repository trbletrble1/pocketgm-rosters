# Coaches, and the other leagues — every declared `kind` was too coarse by one level

**2026-09-04. Report 21.** Follows report 20. Census at
`dataset/build-reports/league-census.txt` / `.json`.

---

## Coaches: 103 NFL seasons

    club-seasons with a head coach   2,217
    distinct coaches                   478
    persons                            476        2 phantom c- pages skipped
    stints                           2,363
    claims                           6,701

**No network for the links** — every club-season → coach link came from the
already-cached roster pages. Only the 478 distinct person pages were fetched.

**136 club-seasons have MORE THAN ONE head coach** — mid-season changes, recorded
by the source. 1968 Atlanta has Van Brocklin and Hecker; 2000 Arizona has Tobin
and McGinnis. **The dataset holds both as stints.** The roster project's handoff
records a ruling forced by a single team field — *"where two men coached a season,
the file takes whoever coached the most games; the other goes in the build log"* —
and this is the same shape as the 13 mid-season player movers in 1950: **the coin
flip belongs to the export, not the store.**

**236 of 478 head coaches also have a player record** — nearly half, each carrying
the bidirectional `p-`/`c-` cross-reference, followed rather than string-matched.
Design shape 8 at scale.

**The scope limit stands and must travel with the number:** the `c-` namespace is
head coaches only. 2,363 stints across 103 seasons is **roughly one per
club-season and nothing for assistants.** It is not a staff census.

**Two phantom pages** — `c-kromeaar001`, `c-murphjoh001` — caught by the
name-and-birth-date existence test rather than by HTTP status.

## The other leagues: 34 league-seasons, zero failures

    APFA  1920-21      AAFC  1946-49      AFL   1960-69      WFL   1974-75
    USFL  1983-85      USFL2 2022-23      XFL   2001/20/23   WLAF  1991-92
    UFL   2009-12      UFL2  2024         AAF   2019

    14,000+ additional player-rows

**Three coverage findings before the data:**

- **`AFL3` is the ARENA Football League**, not the 1940 AFL. A code collision, and
  a build reaching for "the third AFL" would silently get arena football.
- **The 1936 AFL and NFL Europe have league pages but no roster links at all** —
  `AFL2 1936` and `NFLE 1997` both render a title and list nothing. The brief's
  "both AFLs" is therefore **one AFL** in this source.
- **Team codes are globally unique across leagues.** Verified on 12 year-sharing
  pairs — NFL/WFL 1974, NFL/USFL 1983-85, NFL/XFL 2020, NFL/AFL 1960-69 and
  others — **no collisions**, so the `{TEAM}_{YEAR}` cache key is safe. That was
  an assumption until it was checked.

## THE FINDING: every declared `kind` is one level too coarse

Report 20 found `jersey` declared `per_era` was really **per-page**. The league
sweep finds the same defect in the other direction:

**`games_played` and `games_started` are declared `per_league`. They swing by
SEASON within a league.**

| league | season | GP | GS |
|---|---|---|---|
| **WLAF** | 1991 | **96.3%** | 96.3% |
| **WLAF** | **1992** | **16.1%** | **15.1%** |
| USFL | 1983 | 86.7% | 77.9% |
| USFL | 1985 | **42.0%** | **19.7%** |
| UFL | 2009 | 90.2% | 90.2% |
| UFL | 2012 | 64.9% | **4.9%** |
| WFL | 1974 | 21.6% | 7.8% |
| WFL | 1975 | 45.8% | 25.2% |

**WLAF is the sharpest: 96.3% to 16.1% in consecutive seasons of the same
league.** No per-league constant can express that.

Both fields are now `kind: per_league_season`, with the full census stored.

**So all three granularity claims made today were wrong by exactly one level:**

    jersey          per_era      ->  per_era AND per_page
    games_played    per_league   ->  per_league_season
    games_started   per_league   ->  per_league_season

Each was declared from report 06's four-teams-per-league-year sample, and each is
**finer than a sample of that shape can resolve.** The pattern is the finding:
**a sample tells you a field's typical value; only a census tells you what the
field's granularity is.**

## What held

**Birth date holds everywhere.** Worst case **APFA 1920 at 88.8%**; every other
league-season is **≥93.8%**. §9.2 was measured on the NFL and eight sampled
league-years; it is now confirmed across every league StatsCrew carries.

**College is 100% in all 34 league-seasons.** Height and weight are ≥98.6%
everywhere.

**Hometown remains the weakest field** and is worst in the *modern* minor leagues
— XFL 2020 at 75.7%, AAF 2019 at 75.9%, USFL2 2022 at 80.2% — against 85.3% in
APFA 1920. That inverts the intuition and confirms report 06's smaller finding at
census scale.

## Where the player layer stands

    NFL          103 seasons   1922-2024   117,300 player-rows
    other leagues 34 seasons               ~14,000 player-rows
    coaches      2,363 head-coach stints, 476 men, 103 NFL seasons

    ~2,600 pages cached, one fetch each, never re-fetched
    zero-byte cache entries: 0

**Not done:** the CFL, which StatsCrew carries from 1958 and which is ~67 more
seasons; and assistant coaches, which this source cannot supply at all.
