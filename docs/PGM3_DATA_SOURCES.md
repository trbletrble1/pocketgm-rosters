# PGM3 — External data sources

What can be fetched, from where, and what it is good for. Established
2026-08-31, the session that first went looking properly.

The short version: **most of what the handoff describes as hand research is a
bulk download.** Draft classes, player biographies, birth dates, physicals and
combine measurements all come from nflverse in one command each. Coaching staffs
come from Pro-Football-Reference, but only through search — see below.

---

## nflverse — bulk, machine-readable, no scraping

All fetchable with plain `curl` from a build container; `github.com` is
reachable where most of the web is not.

| file | URL | rows | covers |
|---|---|---|---|
| `players` | `.../releases/download/players/players.csv.gz` | 25,064 | rookie season 1974 on |
| `draft_picks` | `.../releases/download/draft_picks/draft_picks.csv.gz` | 12,927 | 1980–2026 |
| `combine` | `.../releases/download/combine/combine.csv.gz` | 8,968 | 2000 on |
| `historical_contracts` | `.../releases/download/contracts/historical_contracts.csv.gz` | 31,893 | patchy before ~2005 |

Base: `https://github.com/nflverse/nflverse-data`

Also `https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv`
— 7,548 games, 1999 on, carrying `home_coach` and `away_coach`.

### `players` — the most useful file in the project

Coverage measured, not assumed: **birth date, height, weight, college and
position are all 100% populated**; jersey number 97%; headshot URL 99%. It
carries `pfr_id`, `otc_id` and `espn_id` as cross-reference keys.

Active-player counts by era: 1,742 in 1986, 2,041 in 2000, 2,208 in 2004,
2,820 in 2021. **Every era this project builds is covered.**

**This solves the namesake problem outright.** Every case that cost a full
session on 2026-08-31 separates cleanly on birth date:

| name | | |
|---|---|---|
| Antoine Winfield | 1977, CB | 1998, SAF |
| Jon Runyan | 1973, OT | 1997, G |
| Kris Jenkins | 1979, NT | 2001, DT |
| Jeremiah Trotter | 1977, MLB | 2002, LB |
| Joe Thomas | 1963 WR, 1984 OT, 1991 OLB | |

Use it before writing any name-keyed lookup.

### `draft_picks`

Round, pick, team, position, college, age, Hall of Fame flag, All-Pro and Pro
Bowl counts, career AV, games, and the headline career stats. The four classes a
2000 file carries — 2001 through 2004 — are 1,024 picks in one download.

### `combine` — strong signal, narrow coverage

Correlations against Madden attributes, measured on 1,880 matched players in the
2021 file:

| combine | Madden | corr |
|---|---|---|
| forty | speed | **−0.946** |
| weight | `PWGT` | +0.967 |
| height | `PHGT` | +0.955 |
| vertical | jumping | +0.883 |
| cone | agility | −0.873 |
| forty | acceleration | −0.869 |
| shuttle | agility | −0.820 |
| broad jump | jumping | +0.777 |
| bench | strength | +0.764 |

Every sign in the expected direction. Madden's speed rating is close to a
restatement of the forty time.

**But coverage is era-dependent and it cuts against the older builds:**

| season | players with combine data |
|---|---|
| 1986 | 3% |
| 2000 | **13%** |
| 2003 | 39% |
| 2007 | 55% |
| 2013 | 57% |
| 2021 | 64% |

The dataset starts in 2000, so a 2000 roster is mostly veterans drafted before
it. **Do not build attributes on this for a historical season** — it is a
cross-check on rookies, not a foundation. It is most useful for 2026.

**And it is not an independent check on the modern files.** Vertical-to-jumping
runs 0.55–0.69 in files up to 2017 and then jumps to 0.88–0.90 in the 2021, 2023
and 2025 JINX files. Either those modders derive jumping from combine numbers or
Madden started doing so. Treating combine as independent corroboration of a
modern file would be circular.

### `historical_contracts`

Contracts covering each season: 944 for 2010, 212 for 2004, **80 for 2000, 6 for
1986**. Historical builds still derive contracts, exactly as the handoff says.

---

## Pro-Football-Reference — search it, never fetch it

**Direct access is blocked in every form tested on 2026-08-31**: plain `curl`
403, `curl` with a browser user-agent 403, WebFetch 403, and the in-app browser
served a Cloudflare bot-detection interstitial.

**But PFR content comes through search results.** Both open coach rulings on
2000 were resolved from search snippets carrying PFR's own coordinator blocks,
including role labels that appear on no other site.

This was validated with a negative control rather than assumed: a PFR-restricted
search for New England's 2000 defensive coordinator — a post that did not exist —
correctly reported the absence and named the position coaches with PFR's labels,
where a summariser inventing an answer would have produced a name.

**Rule: search PFR, do not fetch it. Snippets are fragments, not pages, so
corroborate anything load-bearing against a second source.**

Team season pages carry head coach, both coordinators, and special teams inside
`Other Notable Asst.` — more complete than Wikipedia, which omits special teams
on some pages.

---

## Coaching staffs

**Head coaches** are in `nfldata/games.csv` for 1999 on. Reliable for teams with
no mid-season change; **not reliable for teams that changed**. In 2000 it had
Washington's two coaches transposed across the season and Arizona's split wrong.

It does correctly flag *which* teams changed, which is the useful part. Verify
the split against contemporary sources every time.

Ruling (Ryan, 2026-08-31): where two men coached a season, the file takes
whoever coached the most games; the other goes in the build log.

**Coordinators and special teams** come from Wikipedia `{year} {Team} season`
staff sections, corroborated against PFR via search. All 31 of the 2000 staffs
were built this way — see `sources/pfr/coaches_2000.csv`.

Nothing published anywhere carries NFL coordinators in bulk. GitHub was searched;
the only relevant repository is a script that scrapes PFR team-by-team.

---

## What is not available

- **Coaching staffs in bulk.** Per-team lookup is the only route.
- **Scouts and physios.** Not documented anywhere. The published files carry
  ~160 generated names per season with 0–7% recurrence across seasons. Whether
  that continues is an open ruling.
- **Contracts before ~2005** in any usable density.
- **Combine data before 2000.**

## Realistic Franchise Mod (RFM) — appearance source, Madden 27

**Credit: Realistic Franchise Mod (RFM), a community Madden 27 mod.** Extracted
with `tools/rfm.py` from `sources/madden/CAREER-RFM`, committed so the
extraction is reproducible from a clean clone.

    sha256      cda3782991cbceeac8803c197137eb576cf4de82b5bcb30037fd3eeb80d3a7ae
    bytes       5662392
    extracted   2026-09-02
    players     2955

Same class of source as the 2K5 community rosters: a work in progress whose
accuracy varies with how much attention a given player got. **Pinned and dated
above; re-extract only against a recorded hash.**

### What it is worth, measured

Against the registry's hand-verified players it agrees **10 of 11** reachable,
and **10 of 10 excluding one contested record**. Against the photo
confirmations, 8 of 9.

**The contested record — resolved three ways.** The single anchor miss was
`aaron donald`, RFM light against a verified dark. A case-sensitive search for
`DonaldAaron` finds nothing, which suggested a false join. It is not: the
composite is stored lowercase as `donaldAaron_10852`, and the record reads
forename `Aaron`, surname `Donald`, head `gen_2_H_B_005`.

Whether it is THE Aaron Donald cannot be settled from the file. He retired in
2024, the id (10852) sits well below the current-player range, and the
ethnicity code reads H. A generated or placeholder player is the likelier
reading. **The anchor is unreliable either way and should not carry the weight
of "RFM is not an oracle"** -- excluding it, the source is 10 of 10.

**Anchor against the cohort the source is for.** `rfm.py anchor` takes an
optional roster file and skips anchors not on it. Aaron Donald retired in 2024
and sits in the asset database with an untouched placeholder head; he is in the
registry only because it carries him from an older season, and he can never
reach a build because lookups fire on 2026 rosters. Scoring him made a
10-of-10 source read 10 of 11:

    unscoped                 agree 10  disagree 1  90.9%   (74 absent, 20 abstain)
    scoped to 2026 cohort    agree  7  disagree 0   100%   (0 absent, 97 out of scope)

A stale record scoring as a miss is the phantom-match problem one layer up.

**The lowercase composite is NOT a staleness filter — hypothesis tested and
refuted.** Exactly 9 of 3,068 null-delimited composites start lowercase, and
they are two unrelated things:

- **seven are truncated** by a leading character (`rownKyron` for Brown,
  `acksonTrishton` for Jackson, `anielsJalon` for Daniels). Only two of the
  nine reach the output at all.
- **two are genuine**: `donaldAaron` (retired) and `vandenBergJordan` — Jordan
  van den Berg, a real lowercase Dutch surname particle, **who is on a 2026
  roster**. One current, one stale, on a population of two.

The signal is a file artifact, not a currency marker.

**Extraction verified sound.** Every one of the 2,955 emitted composites is
present in the file, and every emitted surname appears as its own
null-delimited field. Nine composites are stored truncated by a leading
character (`rownKyron` for Brown, `acksonTrishton` for Jackson); one reaches
the output and is flagged by a lowercase surname.

### Count reconciliation

    raw "gen_" occurrences          3070
    matching the head-code pattern  3067
    duplicate player ids collapsed   112
    emitted                         2955
    abstain (skin 3)                  94

The gap against a 3,044 count is **de-duplication**: 112 head codes repeat an
id already seen. Nothing is lost; the same player is written more than once.

Against the player archive, 2,055 players in common, **86.9% agreement**. The
discriminating axis is NOT era -- every RFM player is current, so there is no
historical overlap to test -- but the **archive's own confidence**:

| archive sources | n | agreement |
|---|---|---|
| 1-2 (thin) | 911 | **77.4%** |
| 3-4 | 465 | 88.6% |
| 5+ | 679 | **98.5%** |

Monotone. Where the archive is well-corroborated the two agree almost
perfectly, so **the disagreements concentrate where the archive is admittedly
weak** -- which is the cohort that has defeated every other approach.

### Coverage of the 2026 rostered file (1,885 players)

    RFM        1,662   88%
    archive    1,366   72%
    RFM only     424
    neither       95

### Precedence — APPLIED to 2026 (Ryan, 2026-09-02)

1. registry `_verified_keys` above everything (Donald shows RFM errs)
2. archive where it has **5+ sources** (98.5% agreement makes this near-moot)
3. **RFM for the 424 players the archive cannot reach at all** — the clear win
4. RFM as the tie-break in the thin 1-2 source band, where the two agree only
   77.4% and one of them is wrong a fifth of the time. Photo confirmation is
   still the only thing that settles those.

### Applied — the change set

| rule | records |
|---|---|
| 1 `_verified_keys`, untouched | 7 |
| 2 archive at 5+ sources, untouched | 355 |
| 3-4 RFM applied | 1705 |
| no RFM entry | 566 |

**384 bands changed** (207 dark->light, 177 light->dark). The bulk is players
the archive cannot reach at all (208); the rest sit in the thin band (n=1: 97,
n=2: 38, n=3: 29, n=4: 12). **Zero overturned at 5+ archive sources.**

Lukas Van Ness resolves dark -> light. Nothing else could reach him: 1-2
archive sources, below every floor.

**Nineteen people now have a 2026 face that differs from every earlier season**
— an unavoidable consequence of applying a better source to one file only.
Spot-reading them, 2026 is the one that is right: AJ Epenesa, Alex Highsmith,
Byron Murphy, Josh Palmer and Poona Ford move to dark; Michael Hoecht, Brock
Wright and Michael Bandy move to light. Applying RFM to the published files is
a separate ruling and has not been made.

**2026 ONLY.** No published file is touched — verified.

**Correction.** This section first claimed `appearance` was the only field that
differed. It was not: `greed` and `ambition` differed on ~2,500 records, and
the cause was not RFM at all. **The build was non-deterministic.**
`DERIVED_ATTRS` is a set, two of its members are drawn with `rng.random()`, and
iterating in set order made which draw each one received depend on Python's
hash seed. Two consecutive builds of identical input differed on 2,500 and
2,570 records. Now sorted, and two consecutive builds are byte-identical.

A file that cannot be rebuilt the same way twice is not reproducible from a
clean clone, which is the property the pinned RFM provenance exists to give.
The claim that surfaced it was mine and it was wrong.

### Band split after RFM — measured, and NOT a divergence

    1986 32.1%   2000 35.6%   2004 34.7%   2007 30.6%
    2010 30.8%   2013 30.5%   2017 29.8%   2021 27.2%
    2026 28.7%   (27.0% before RFM)

The published range across all eight files is **27.2% to 35.6%**, and 2026 at
**28.7% sits inside it**, between 2021 and 2017. RFM moved the file from 27.0%
to 28.7% — **toward the middle of the range, not away from it**.

A narrower reading of the range as 30.5-35.6% excludes 2017 (29.8%) and 2021
(27.2%) and makes 28.7% look like an undershoot. It is not. Which files count
as "the published range" is the same pooling question that has produced a wrong
claim four times in this build; the answer here is all eight.

### Precedence revised — RFM outranks the archive at any source count

Ryan photo-checked all six contested cases: RFM correct on 5 of 5 decided,
with Fairbairn genuinely mid-tone.

**The sample was only the disagreements**, so it establishes that RFM wins when
the two differ — not that the archive is unreliable. Measured, they agree
**316 of 322 (98.1%)** at 5+ sources.

**The proposed mechanism is refuted.** "Five 2K5 rosters carrying the same
default for a modern player" predicts the archive is weak on modern players.
Split by era, agreement at 5+ sources is:

    career starts after 2005    98.1%   (n=697)
    career overlaps the 2K5 era 77.8%   (n=27)

The archive is **strongest** exactly where the mechanism said it would be
weakest. The revised rule is right; the reason is that RFM wins the 1.9% of
cases where they disagree, not that the gradient fails to transfer.

**Four records changed, not the one predicted.** The dry run counted only
RFM/archive disagreements and missed a hole in the old rule 2: "archive wins"
conferred AUTHORITY without ever writing the archive's ANSWER. Michael Burton
(archive light, n=9) and Ben Skowronek (archive light, n=6) were shipping
**dark against both sources**. Gunner Olszewski moves dark -> light as ruled,
and Ka'imi Fairbairn goes to family 3, the boundary, rather than being forced
to a side.

### RFM applied to 2021 — with a boundary band

Ryan photo-checked twelve of the 78 disagreements. RFM correct on 5 of 5
decisive cases, but **seven of the twelve are genuinely mid-tone**. The finding
is not that RFM is right about 2021; it is that a binary split disagrees most
about people who are actually in between.

**RFM's own scale identifies them — but not at the values expected.** The
proposed cut (2 and 4, adjacent to the abstain band) does not separate: 3 of 6
mid-tone against 3 of 5 decisive. The cut that does is **4-5**, the light end
of RFM's dark range:

    mid-tone in skin 4-5     5 of 5
    decisive in skin 4-5     0 of 5

(Mahomes is absent from RFM; Aaron Donald is excluded — his RFM record is the
untouched placeholder established earlier, and applying it would have shipped
him light.)

So mid-tone is **machine-readable after all**, at 4-5 rather than 2-4, and no
longer needs a photo per player.

**The boundary family holds.** Family 3 runs 0.7% to 12.5% across the archive,
and 2021's 0.7% is the lowest of any file. Routing 22 players there takes it to
**1.7%** — inside the range, and toward the middle rather than away.

    disagreements handled          74
    boundary (skin 4-5) -> family 3  22
    decisive flips                   52   (35 light, 17 dark)
    light share            27.2% -> 28.1%   (published 27.2-35.6%)

Only `appearance` changed, asserted. The faces gate went **27 -> 26**
cross-season disagreements — one fewer, because 2021 and 2026 now share a
source. NOT extended to the other published files: twelve players from one file
is not evidence about seven others.

### The skin 4-5 boundary rule — independently confirmed, with one false positive

Tested against 2026's photo-checked cases, which were decided before the rule
existed:

    mid-tone identified      1 of 1   (Fairbairn, skin 4)
    decisive misclassified   1 of 13  (Tristan Wirfs, skin 4)

Combined with 2021: **6 of 6 mid-tone identified, 1 of 18 decisive misread.**
Wirfs is decisively dark and the rule calls him boundary; he escaped only
because routing fires on disagreements and RFM already agreed with the file.

**A working rule, not a settled one.** It identifies mid-tone reliably and
carries a small false-positive rate on decisive dark players at skin 4. Use it
to route disagreements, not to reclassify agreements.

### Placeholder records excluded at source

`EXCLUDE_IDS` in `tools/rfm.py` drops `10852` — Aaron Donald, retired 2024,
carried with an untouched placeholder head (`gen_2_H_B_005`, ethnicity H). That
record attempted to enter **two** different files and would have shipped him
light in both. Excluded once at extraction rather than remembered in every
consumer.


---

## footballdb.com — 1979 roster spine (added 2026-09-02)

    https://www.footballdb.com/teams/nfl/{period-team-slug}/roster/1979

**Slugs are the PERIOD team name**, not the modern franchise: `houston-oilers`,
`baltimore-colts`, `st-louis-cardinals`, `oakland-raiders`, `san-diego-chargers`,
`washington-redskins`. All 28 resolve.

**Transport matters — the site is behind Cloudflare.** Tested 2026-09-02:

| transport | result |
|---|---|
| `curl`, browser User-Agent | **403** — Cloudflare "Attention Required!" |
| Claude Code `WebFetch` | **403** |
| **in-app browser (`mcp__Claude_Browser__navigate`)** | **works** |
| in-page `fetch()` from footballdb's own origin | **403** — XHR is blocked even same-origin |

So it is navigate-and-extract, one page at a time. **The pages are cached in
`sources/1979footballdb/`** (28 files, 1,438 players, pipe-delimited
`jersey|name|pos|games|age|college`) so no rebuild depends on the site still
admitting us — same reason the PFR pages are in the repo.

**What it gives:** jersey, name, position, games played, age, college.
**What it does not:** height, weight, games started (all blank). Height and
weight come from the 2K5 save instead.

**Do not source anything but the roster table.** The page header carries MODERN
metadata pasted onto a historical page — the 1979 Houston Oilers page reads
"AFC South, 3-14, Head Coach: Robert Saleh" and Pittsburgh reads "Mike
McCarthy". The table itself is clean and anchor-checked: 42 of Pittsburgh's 46
appear on the PFR 1979 Pittsburgh page with **zero contradictions**, and the 11
Houston players absent from PFR are the entire interior offensive line plus
low-snap backups — men who cannot record a stat.

**A batch's tab title lags one navigation behind the extracted content.** Verify
by extracting `document.title` in the same call as the table, not from the tab
context line.

## Wikipedia 1979 season pages — roster templates (NOT depth charts)

Reachable from the container with a User-Agent header, same as the career
articles. **There is no depth chart and no starter marking on any 1979 season
page** — searched all 15 tested for `Starters` / `Depth chart` / `Lineup`
headers (0 of 15) and for the word "start" anywhere (only prose and PFR
citations). What the pages carry is a **flat roster**: jersey number, name,
and a position label, grouped by unit. Two formats:

- `{{NFLplayer|NUM|Name|d=disambiguator|POS|STATUS}}` — most teams. `POS` is
  the last unnamed parameter, but **`IR` / `PUP` / `rookie=y` also sit there**;
  a parser that takes the last token reads `IR` as a position. Skip status tokens.
- A hand-built wikitable with `'''Group'''` headings and `* NUM Name POS` lines
  — Cleveland, and others. Italics mark rookies.

**Value:** jersey numbers, and DB labels at CB/FS/SS granularity where
footballdb gives only `DB`. **Not** a rating signal — nothing marks starters.

**Lineage caveat:** the Cincinnati, Washington and Pittsburgh pages cite PFR's
1979 roster page as their source; Denver does not. Treat as PFR-derived unless
checked. It is independent of NFL79.ros and of the 2K5 save.


## `NFL79.ros` COCH — a real 1979 head-coach source inside a 2007 stock pool

218 records, 68 fields. **All 28 of 1979's head coaches are in it with ages that
verify against their birth years**, carrying the modder's per-unit ratings. The
assistants are stock, from roughly a 2007 Madden: their ages fit neither 1979 nor
2004, and they include men who were children in 1979.

**Use `CAGE` against a fetched birth year as the gate. Do not use `CHTY`.** The
head-coach flag marks 19 records, includes Dom Capers and Art Shell, and misses
Bill Walsh.

The same test should be run before trusting the 1983, 1986 or 1990 mods' coach
tables — see backlog item 20.

## `1976_raidermike.ros` — an adjacent-year mod, three years before the build

In `sources/1976madden/`. 2,299 players, 110 fields, and it **screens FAIL for
faces**: `PSKI` is collapsed at 29% on the middle value, over the 28% threshold.
`COCH` is the same ~2007 Madden stock pool as `NFL79.ros` — D. LeBeau and
G. Williams are both in it — so its coach table is worthless for 1976 the same
way, and by the same age test.

**It is INDEPENDENT of `NFL79.ros`, not a copy.** Of the 964 men in both, `POVR`
agrees on 11% and the live attributes on 30-51%. Height agrees on 97%, which is
not lineage — height does not change.

**Its value is ratings for men gone before 1979.** It closed the last three of the
1979 expansion pool that no other source reached — MacArthur Lane 96, Pat Curran
78, Vince Papale 63 — and being three years back it reaches men active in 1976 and
retired by 1979, which is deeper than the 1977-78 difference goes. **Worth
revisiting before anyone concludes the expansion pool is exhausted.**

**Age-forward, measured on those 964 rather than assumed:**

| age in 1976 | median POVR change by 1979 | n |
|---|---|---|
| 22-25 | +2.0 | 551 |
| 26-29 | 0.0 | 325 |
| 30-33 | −1.5 | 70 |
| 34-40 | −8.0 | 7 |

**Caveat that no statistic shows:** those 964 are men who were *still playing* in
1979. A man being aged forward *because he is in the expansion pool* is by
definition one who did not survive. The curve therefore understates his decline
and the result is an **upper bound**. Same selection trap as the league's rising
age curve.

## PFR: the in-app browser does NOT get through, and the fix is a saved file

Tested 2026-09-03 on `https://www.pro-football-reference.com/years/1981/draft.htm`.
The browser reaches Cloudflare's "Performing security verification" interstitial
and **the challenge does not clear** — two navigations and 26 seconds of waiting,
title still "Just a moment...". That is bot detection, so it is not worked around.

This is **not** the footballdb case. There, `curl` and `WebFetch` returned 403 and a
real browser engine was simply admitted. PFR issues an active challenge that the
in-app browser does not satisfy, so the transport table now reads:

| source | curl / WebFetch | in-app browser | works |
|---|---|---|---|
| Wikipedia API | yes, with a User-Agent | yes | **API** |
| footballdb | 403 | **yes** | in-app browser |
| PFR | 403 | **challenge never clears** | **a file saved by Ryan** |

**The working transport costs one "Save Page As" per year.** The 1980 listing in
`sources/1979PFR/` arrived exactly that way — 738KB of saved HTML — and a file on
disk sidesteps the context limit that truncated a pasted 1981 fetch at pick 185.
Fetching in halves by round is unnecessary.

`tools/extract_pfr_draft.py` parses that format. Verified against the 1980 listing:
335 picks, names agreeing with the existing `wip/draft_1980_pfr.csv` on all 335. It
finds the file by year and reports what is missing, so the moment 1981-83 land it is
one command.

The listing carries `Rnd, Pick, Tm, Player, Pos, Age, To, AP1, PB, St, wAV, DrAV,
College`. **The hindsight signal is `wAV` and `DrAV` directly**, no derivation, and
a man who never played reads blank — which is itself the signal. In the 1980 class
`wAV` is present on 208 of 349 rows.

## The Mike `.ros` family — ten files, one source (added 2026-09-03)

`$PGM3_SOURCES/mike/`: 1966Roster, 1976Roster, 1978Roster, 1996Roster,
Mike-NFL1941-1969, Mike-NFL1970-1974, Mike-NFL1975-1979, Mike-NFL1980-1989,
Mike-USFL_WFL, MuscleMike-LM67. 112 PLAY fields, an eight-value `PSKI`.

**Lineage: not ten voters.** Every file carries the same 2,032-record block —
identical on name, skin, age, overall, height, weight, college — a **2003-season
base** (Van Pelt 33, Wuerffel 29, Mirer 33) covering 54–63% of our 2000 and 2004
files. Each file is that base plus a period layer; pairwise identical period
records run 54–67% between the single-year files and everything, 42–50% between
the era files. Weighted in the registry as ONE source: one vote on the base,
separate votes on the layers (files listed per man in `mike_skin`).

**PSKI (eight values), from the pooled crosstab against 1,396 anchors:** 0, 1, 2
→ light (99 / 96 / 92% pure); 3, 4, 5, 6 → dark (100%); **7 abstains** (58%,
bimodal). Note Mike's 1 is light, unlike the three-value sources where 1 abstains.

**Accuracy.** On the shared base all ten read 98.1–98.6% on the same ~560
anchors — that is the base measured ten times, and it is what the earlier 97.7%
was. On the period layers: LM67 96.2% (208 anchors), 1996Roster 98.3% (118),
USFL/WFL 96.1% (76), 1980-89 93.3% (30), 1970-74 90.9% (44), 1975-79 90.6% (32),
1978 90.5% (21), 1976 89.5% (19), 1966 88.0% (25). **NFL1941-1969: 13 anchors,
no evidence either way.** Against hand-verified truth (archive consensus
computed without 1986): archive 95/95, Mike 79/81.

**Coverage of our rostered men (union):** 1979 89%, 1986 70%, 2000 86%, 2004
69%, 2007 40%, then falling.

**LM67 is the file to build on, and it is narrower than the forum thread
implies:** 159 year-labelled teams across 44 seasons, 1957–2002 (`'82 Packers'`,
`'99TEN'`), 7,678 players, one to seven teams a year — Raiders 15 seasons,
Cowboys 14, 49ers 10. **A notable-teams database, not a league-year database.**
Plus 32 unlabelled current teams (3,560 men) and 5,501 records unique to it.

## `Mike-USFL_WFL.ros` — decoded, 2026-09-03

**93 team rows, 91 with players, 4,904 men. Fully labelled in the TEAM table**, so
this is a decode, not an inference. Four blocks by `TTYP`:

| `TTYP` | what | teams | men | in the shared 2003 base |
|---|---|---|---|---|
| 0 | the modern NFL | 32 | 1,743 | **100%** |
| 2 | all-time franchise teams (`ALLCHI`, `All Bills`…) | 31 | 1,567 | 3% |
| **5** | **alternate leagues** | **27** | **1,347** | **0%** |
| 1 | free agents | 1 | 247 | 100% |

**The `POVR` 99s are in the all-time block, not the USFL one.** Jim Kelly is 99 on
the *Buffalo All Bills* and **93** on the Houston Gamblers; Steve Young 99 on the
*All 49ers* and 91 on Los Angeles; Herschel Walker 99 on the *All Vikings* and 90
on New Jersey; Reggie White 99 on both the *All Eagles* and *All Packers* and 96
at Memphis. The all-time block reads median 93 with 140 men at 99 — that is the
career-peak block. **The alternate-league block reads median 76, p90 85, max 96,
one man at 99** (Csonka), against our 1979 at median 70 / p90 85 / max 98 and
1986 at 71 / 86 / 98. Era-shaped, a little compressed at the bottom.

**The 27 alternate-league teams are four things:**

- **The 1984 USFL, complete — all 18 teams, 926 men.** Not 1983 (12 teams) or
  1985 (14): the eighteen are exactly the 1984 field. **Twelve named men checked
  against their real 1984 club: 12 of 12 correct** — Kelly at Houston, Young at
  Los Angeles, Walker at New Jersey, White at Memphis, Carter at Michigan,
  Williams at Oklahoma, Cribbs at Birmingham, Landeta and Oates at Philadelphia,
  Zimmerman at Los Angeles.
- **The 1975 WFL, partial — 4 of 11 teams, 201 men**: Honolulu Hawaiians,
  Memphis Southmen, Southern California Sun, Birmingham Vulcans. **1975, not
  1974**: Birmingham were the Americans in 1974 and the Vulcans in 1975. Csonka
  and Warfield are at Memphis, correctly.
- **The Longest Yard (1974), 2 teams, 84 men** — The Mean Machine and the Citrus
  State Guards. Paul Crewe, Captain Knauer, Granny Granville, Connie Shokner,
  Charlie Blue Eyes, Bogdanski; Joe Kapp, who was in the film, plays for the
  guards. Fiction, and flagged as such.
- **Three Hawaii service teams, 136 men** — Schofield Knights, Barbers Point
  Warriors, Black Rock Scorpions (Schofield Barracks and Barbers Point are Oahu
  installations). Not identifiable as any league; ratings 69 median. Likely the
  modder's own.

**The alternate-league block is entirely original work**: 0 of 1,347 records
match the shared 2003 base, and **0 match an all-time record even by name plus
attributes** — 36 USFL men share a name with someone in the all-time block and
not one shares a record. Csonka's 99 at Memphis is his own row, not a copy.

**Anchor test, alternate-league rows only** (our verified faces plus Ryan's
photograph verdicts as truth): **USFL 12 of 13 = 92.3%**, WFL 2 of 2, no
abstentions. Thin — the archive barely reaches these men — but consistent with
the family's 96% on period layers elsewhere.

**Condition of the data.** 51 men per USFL team, age median 24 (range 19–38),
a full positional spread. **39 names appear twice or more inside the block and
68 records are padding-shaped** (`Tino Gomez.`, `Darren Anduha.`, `P #40`), all
in the film and Hawaii teams. **621 of the 926 USFL men appear nowhere in our
1979, 1986 or 2000 files** — median `POVR` 74, p90 83 — which is the pool a
build would draw on.

## The Mike family — full season inventory (2026-09-03, restated)

**Nine of the ten files carry year-labelled teams** (`'66 Vikings`, `66MIN`), so
this is a decode. `wip/mike_season_inventory.csv` carries the table: **one row
per season PER SOURCE FILE**, never aggregated across files, with team count,
player count, the real league size that year, and what the block is.

**537 season blocks, 25,916 men, 54 distinct seasons 1941-2002 — and that
sentence answers the wrong question.** A block labelled `'58 Colts` makes 1958
"a season present in the family"; it is two teams. **Aggregating across files
hides where the teams come from**: 1966 reads as 30 teams only if the
standalone `1966Roster.ros` (24 teams, a complete league) is pooled with three
notable teams from each of two compilations. Those are different objects and
the table now keeps them apart.

### What is actually buildable

**Five season-league combinations are a complete league, and each comes from one
file** — no pooling, no invented teams:

| season | league | teams | men | source |
|---|---|---|---|---|
| **1966** | NFL+AFL | **24 of 24** | 1,087 | `1966Roster.ros` |
| **1976** | NFL | **28 of 28** | 1,334 | `1976Roster.ros` |
| **1978** | NFL | **28 of 28** | 1,370 | `1978Roster.ros` |
| **1984** | USFL | **18 of 18** | 926 | `Mike-USFL_WFL.ros` |
| **1996** | NFL | **30 of 30** | 1,508 | `1996Roster.ros` |

**Nothing sits between.** There is no partial league at 40-89% anywhere in the
family: the other **51 of 56 season-league combinations are notable teams only**,
3-39% of their league, typically four to ten famous sides. The 1975 WFL is 4 of
11 (36%) and belongs in that group.

**Pooling files does not help.** Across all 56 combinations, only two seasons
gain a single franchise from the union of files (1984 NFL and 1995, 4 → 5); every
other season repeats the same famous teams in every file that carries it. The
39 multi-file seasons are **cross-checks on the same teams**, which is useful for
verification and useless for coverage.

**So the era claim, corrected: the forties and fifties are not available.** 1941
is two teams, 1945 through 1958 is one or two teams a year, 1960 is five, and the
first buildable season is 1966. Of our ten published seasons, 1979 (6 teams, 21%),
1986 (3, 11%) and 2000 (1, 3%) appear, all as notable teams.

**Excluded from the season list, being real data but not seasons:** 320 modern
NFL blocks (the shared 2003 base), 62 all-time franchise teams (`All Bills`,
median `POVR` 93 — where the career-peak 99s live), 67 stadium and uniform test
teams with placeholder names (`LA Coliseum`, `QB 32W`), 10 free-agent pools, 4
Pro Bowl squads, the 2 fiction teams from *The Longest Yard*, the 3 Hawaii
service teams.

**A classifier trap worth recording:** matching a team by nickname alone put the
modern **Carolina Panthers** into the 1984 USFL in all ten files, because the
USFL's Michigan **Panthers** share the nickname. City and nickname together are
the key. Caught because Julius Peppers appeared in a 1984 roster.

**`Mike-NFL1941-1969` is 5,322 players across 104 blocks and is the only source
for every season before 1957.** Its 76.9% anchor reading is **13 men** against an
archive that barely reaches the era — no evidence either way, not a quality
verdict, and it should not be read as one.

## The PS2 2K5 "every season 1940–2022" mod — five archives, decoded (2026-09-03)

**Container.** 121 `.max` files, 253–306 KB each: `Ps2PowerSave` (Action Replay
MAX) wrapping an ESPN NFL 2K5 PS2 save, game code `BASLUS-20919`. The header
parses exactly (compressed length, five inner files, decompressed length); the
payload is **LZARI** — LZSS with arithmetic coding, which is why it reads as
8.00 bits/byte and byte-wise LZSS fails. `mymcplus` decodes it. Inside:
`icon.sys`, `VIEW.ICO`, `TYPE`, the save data, `EXTRA`. Ten files carry a 20-byte
`EXTRA` instead of 4 and decode by reading to end-of-file. **All 121 decode.**

**What the archives hold.** 70 roster saves (`Ros*`, 593,984 bytes, tag `ROST`)
and 51 franchise saves (`Fra*`, 720,044 bytes, tag `04 00 00 00`), 70 distinct
seasons 1940–2022: 50 with both, 18 roster-only, 2 franchise-only (1942, 1951).
**Gaps: 1945, 1947–49, 1957–59, 1975, 1996, 1999–2000, 2005, 2014.** Three labels
lie: `Ros43.max` holds `Ros1941` inside (content is 1943 — Luckman, Baugh, Hutson,
no Van Buren), `ros1989.max` holds a slot named `2K7` (content is 1989), and
`Ros1967.max` holds a **franchise** blob, so 1967 has no roster. `Ros1978` and
`Ros1979` share an inner name; content separates them (1979 has Simms, Winslow,
Montana; 1978 does not).

**The roster save is readable end to end** by the project's existing 2K5 backend
(`rosdump` → `nfl2k5.py`): 1,944 player slots, names, position, skin, face,
jersey, weight, height, years pro, and eleven ratings. Layout is the 2K5 shape
exactly — **32 blocks of 53 in fixed team order, then 248 free agents.** No
draft table: the roster carries 0 rookies in 1979 and 190 in 2022 as ordinary
records; **the draft classes the modder describes live in the franchise save,
which our decoder does not read.** The franchise files are league state.

**The claim of full leagues from 1940 does not survive the content.** Every
season fills all 32 blocks and every slot differs between files — the modder
touched everything — but what he filled the early blocks with is **generated
men with anachronistic names**: Jaxton Russo, Zayden James, Kyrie Small, Huxley
Barker on a 1943 roster, 135–242 modern given names per pre-1960 file. Real men
are sprinkled in (Luckman, Isbell, Cherundolo in 1943; Lujack, Layne, Tittle,
Graham, Baugh in 1950 — on modern team slots). Joined to the 26,067 real
football names the project holds:

| era | real-name share | note |
|---|---|---|
| 1940–1946 | **2–9%** | filler with modern names |
| 1950–1956 | 13–22% | the pool is thin here, so a floor |
| 1960–1965 | 36–59% | |
| 1966–1998 | 62–85% | |
| 2001–2022 | 84–96% | |

**Same-year cross-check** against our PFR-sourced files, where the pool is
strong: **PS2 1979 rostered 1,696 → 70% in our 1979 file; our 1,586 rostered →
76% in PS2. 1986: 68% and 64%.** So a 1979 PS2 roster is roughly 500 men we do
not hold and roughly 400 of ours it does not — the same men in the middle and
generated men at the edges, consistent with a real 1979 core of ~1,200 and
filler to 1,696. This is the same shape as our 1979 build's 59-man rosters and
the four invented franchises, done by a different hand.

**Skin, against our truth** (the 241 verified faces plus Ryan's verdicts, 202
anchors on 1979 and 1986): raw values **1 and 2 are light (140 of 150), 3–6 and
above are dark (46 of 49)** — **94% with that mapping.** The decoder's "mixed"
band mixes raw 2 (light) with raw 3 (dark) and should not be used. The 1943
roster reading 42% dark is the filler's random skin, not the 1943 NFL.

**Ratings are the modder's design, as Ryan said**: 1979 speed median 63 against
our 82, tackle median 31 against a distribution that starts at 0 for non-
tacklers — different scale and different zero convention. Not importable
directly; rescale to the archive's shape if used at all.

**What it is, plainly:** for 1966–2022 a real core of 60–95% of each roster with
verified 2K5-format skin at 94%, sitting inside generated filler; for 1940–1965
mostly filler around a few dozen to a few hundred real men. Readable throughout.
`wip/ps2_2k5_season_inventory.csv`.

## Pro Strategy Football 2026 mod (`psf2026`) — decoded 2026-09-03

Ninety league files `YYYY_LEAGUE.lgs2026` (1940–2025 NFL, 1946–1949 AAFC,
1960–1969 AFL-NFL), plaintext, no compression. **File size is base +
teams × 48,792 for all 90**, and the AAFC files size to 8, 8, 8 and 7 teams —
the real league. Team table of 6,604-byte records (city, nickname,
abbreviation at +0/+32/+64); the AAFC tables name the real eight plus two NFL
clubs with no roster behind them. Player records are 856 bytes, **57 per
team**: forename +8, surname +40, jersey +72, college +109, photo filename
+142 (all NUL-terminated in fixed slots, with stale residue after the NUL that
a regex parse misreads), age as u16 at +200 (exact for the eight men checked,
Baugh 1943 to Manning 2010), then a numeric tail not decoded. No face model,
no skin field: **appearance is a headshot reference**, `First_Last.jpg`,
resolving against the 24,256 photographs in the separate `psf2026 - USFL.zip`
(`player_photo_sets/players/`) for 89–96% of referenced names in every era
before 2025; the 2025 file uses a `first_last_college` scheme this set lacks.

**Fourteen fixed slots per team (2, 5, 11, 17, 24–26, 32–34, 40–41, 49–50) are
generated men in every file before 2021** — no photo, a city where the college
goes, 0.7–1.4% pool match (namesake noise). The other 43 are the roster. Against
our 30,379-name pool the 43 are 97–99% real from 1970 on, 92% in the 1960s,
59% in the 1950s and 24% in the 1940s — the last two are the pool's floor, not
the file's: a headshot exists for ~90% of them in every era, and the 1940s
names are the real men (Parker, Manders, Tittle, Dobbs, Sinkwich). From 2021
all 57 slots are real (98% in our 2021). Cross-checks: **98% of PSF's 1979
photo-men are in our 1979, 100% of 2010's**; the remainder are name-form
differences (Herbert/Herb, and our own compound-forename splits, backlog 61).
PSF holds 36–42% of each of our files' men — 43 per team against our ~94.

Against 2K5 on the same pool, per season: **2K5 carries more real men from 1944
on** (1979: 1,363 to 1,200; 1989: 1,661 to 1,169) inside far more filler
(~600–1,900 generated men per file against PSF's 14 per team); PSF carries more
in 1940–1943 and holds 19 seasons 2K5 does not (1942, 1945, 1947–49, 1951,
1957–59, 1967, 1975, 1996, 1999–2000, 2005, 2014, 2023–25). PSF's filler is
tagged by slot and photo; 2K5's is not. Neither carries a face model.
`wip/psf_season_inventory.csv`, one row per file.

## The PSF photograph library on disk — 26,145 headshots, and a measurement pass

`pgm3-sources/photos/PSFplayers/` holds **26,145 photographs**, the set the PSF
mod's records reference by filename (`Terry_Bradshaw.jpg`), extracted from the
`psf2026 - USFL.zip` archive. Filenames are `first_last.jpg` with inconsistent
case, keyed on name alone — no position, so a namesake check is required before
anything is applied by name, as always.

Beside it, `pgm3-sources/photos/measured.csv` carries **9,472 rows of
per-photograph measurement** made on 2026-08-31: `skin_frac`, cheek RGB and
luminance, crown RGB and luminance, `mous_delta`, `chin_delta`, `jaw_delta`,
`hair_above`, and a `status` column that marks the photographs where no face was
found. Roughly a third of the library, measured.

**Why this matters and what it is not.** The retrofit of 2026-09-03 recorded
"whether a face matches the man" as one of the things no check can test, because
it needs a person and a photograph. **This is the photograph.** Cheek luminance
bears on skin family, crown luminance on hair colour, the moustache and chin
deltas on facial hair, `hair_above` on the balding axis that item 60 measured
and left. It is plausible that the appearance fields become checkable against a
source rather than only against each other.

**Not acted on, and deliberately.** Every one of those mappings is a hypothesis
until it is scored against Ryan's verdicts the way `PHCL` was — and `PHCL`
scored 86% against a 91% base rate and was refuted. The measurement being on
disk is not the same as the mapping being established. Recorded here so the next
pass starts from what exists rather than re-measuring it.

## The coach-source question: PSF carries head coaches, 2K5 does not

Every source examined so far has been players only. Asked and answered
2026-09-03.

### PSF: yes — 1,945 head coaches across 90 seasons, each with a photograph

**They live in the team record, not a staff table.** Each 6,604-byte team record
carries city, nickname and abbreviation at +0/+32/+64, the stadium at +72, and
then **the head coach's name at +1172 and his photo filename at +1212** —
`Tom Landry` and `Tom_Landry.jpg` in Dallas 1979. One coach per team; no
coordinator, scout or physio anywhere in the format. The file header names a
`coaches` asset path beside `players`, `default_player_names.txt` and
`default_colleges_list.txt`.

| | |
|---|---|
| coaches found | 1,945 across 90 files |
| carrying a photo filename | 1,945, all of them |
| photo resolving in the 26,145-image library | 1,201 |
| already present in our own staff files | 1,724 |

**Coverage by era follows the team detection**: 8 of 27 teams in 1940, 8 of 10
in each AAFC file, then essentially complete from 1960 — 15 of 15, 24 of 24, 26
of 26 in 1979, 29 of 29 in 2000, 30 of 30 in 2010. The team walk finds 26 of
1979's 28 teams, so a couple per file are missed by the anchor rule rather than
absent.

**Cross-check against our own head coaches: 1979 is 26 of 26**, every PSF coach
already in our file. 1986 is 22 of 24, 2000 is 26 of 29, 2010 is 26 of 30 — and
**the men PSF names that we do not are the mid-season changes**: Bruce Coslet at
Cincinnati in 2000 (who started the year LeBeau finished), Gary Moeller and
Terry Robiskie, Jason Garrett and Josh McDaniels in 2010. So PSF and the archive
sometimes pick different ends of the same season, which is a reconciliation
question rather than a disagreement about who existed. `wip/psf_coaches.csv`.

**One caution, unresolved:** 1986 Detroit reads Wayne Fontes, who was Detroit's
coordinator in 1986 and did not become head coach until 1988. Whether that is a
mod error or a mislabelled file is not established, so the set should be scored
against a real source before any of it is applied.

### 2K5: no — the franchise saves carry the game's own 2004 coaches

The franchise saves DO hold a coach table, with a biography line each. It is the
stock NFL 2K5 table: **Belichick, Reid, Dungy, Schottenheimer, Vermeil,
Wannstedt, Coughlin, Del Rio, Mariucci, Martz, Fox, Turner, Sherman, Edwards** —
all fourteen surnames present, plus "Dallas Coach" where Parcells' name was
withheld for licensing.

**It is identical across seasons.** Eleven of the 29 franchise saves share one
byte-identical coach block, six carry none at all, and the files labelled 1940,
1941, 1942, 1961 and 1987 all carry the 2004 coaches. **The modder changed
players and left the coaching staff untouched**, so there is no historical staff
data in the 2K5 archive at any date.

### What this means for the archive

PSF is the first staff source found in any of them, and it is head coaches only.
Coordinators, scouts and physios still have no source anywhere — which is why
the generated-staff exception exists and why 1979's coordinator terms had to be
built rather than sourced.

## The Coaching Tree MCP — the coordinator source, and it carries birth dates

Added by Ryan 2026-09-04 (`coaching-tree.app/mcp`). Five tools: `list_teams`,
`get_team_staff`, `get_coach`, `search_coaches`, `get_coaching_tree`.

**The three questions, answered.**

**How far back.** To at least **1926** — Green Bay 1926 returns Curly Lambeau.
1921 returns an empty staff. The early years are head coach only; assistants
appear by 1933 (Halas plus two) and 1940 (Halas plus three, including Red
Grange). Franchise identity is handled properly: `list_teams` gives every
historical name with its year range, so Oakland 1979 is `LV`, the Houston Oilers
are `TEN`, the St. Louis Cardinals are `ARI`.

**Coordinators, or just head coaches.** **Coordinators, and the entire assistant
staff with real titles** — offensive line, running backs, linebackers, defensive
backs, strength and conditioning, administrative assistant, and second roles
where a man held two.

**1979 Pittsburgh.** Yes: Chuck Noll, **George Perles as defensive
coordinator**, Woody Widenhofer, Dick Hoak, Tom Moore, Rollie Dotsch, Paul Uram,
Dick Walker. Eight men where our file holds Noll and eight invented.

**AND IT CARRIES BIRTH DATES.** `get_coach` returns `birth_date`, birthplace,
college, career span, and a per-year stint list. Frank Gansz: born 1938-11-22,
Cincinnati special teams in 1979. **Our 1979 file has him at 61; he was 40.**
That is backlog 68's staff-age problem with a source attached — and the stint
list also says which team a man was on in a given year, so a man can be placed
as well as aged.

**THE COMPLICATION, and it is the reason nothing has been written yet. 1979
football did not use PGM3's vocabulary.** Of fourteen 1979 teams pulled:

| PGM3 slot | teams with that exact title |
|---|---|
| Defensive coordinator | 8 of 14 |
| Offensive coordinator | 5 of 14 |
| Special teams | **0 of 14** — twelve carry a "Special Teams Assistant" as a *second* role |

Pittsburgh has no offensive coordinator because Noll called the offence himself;
San Francisco has none because Walsh did. Miami's defensive architect is Bill
Arnsparger, titled **Assistant Head Coach / Defensive Assistant**, beside a
"Defensive Run Game Coordinator". Atlanta has no titled coordinator at all.

**So filling PGM3's three fixed slots needs a mapping rule and a seniority
fallback, exactly the shape of the Duffner decision and about 160 times over.**
The candidate rule: take the exact title where it exists; otherwise the senior
assistant on that side of the ball; and state the mapping in the provenance
sidecar every time, so a reader can tell a titled coordinator from an inferred
one. **Not written — that is a ruling.**

**A bonus the archive has needed for a long time: the source disambiguates
namesakes itself.** Atlanta's 1979 offensive line coach is `bill-walsh-7506f6f4-…`
while San Francisco's head coach is `bill-walsh`. Two men, two slugs, no
arithmetic required.

## StatsCrew — reachable, and the schema does not drift across a century

Allowlisted by Ryan 2026-09-04 and tested before anything was built on it.
`tools/statscrew.py`.

**REACHABILITY: yes, directly.** HTTP 200, raw HTML, no Cloudflare, no proxy
problem — `curl` and `urllib` both work from the sandbox. That matters beyond
access: **raw HTML means the pages can be cached**, which a fetch-and-summarise
tool could not do.

**The cache lives at `$PGM3_SOURCES/statscrew/raw/`, NOT in the scratchpad**,
because /tmp was wiped mid-session earlier the same day and took every
uncommitted dump with it. Every page is written on first fetch and never
requested again; requests are spaced a second apart and carry a contact address.
Seventeen pages, 960 KB, so far.

**COLUMN DRIFT: none worth the name.** The same ten columns in 1950, 1979, 2000
and 2020 — `# / Player / Pos. / Birth Date / Height / Weight / College /
Hometown / GP / GS` — byte-identical headers across seventy years. **1920 has
nine: there is no jersey-number column**, which is correct rather than missing,
since numbers were not yet required. That is the only structural difference
found across a century.

**Two things that DO change and matter.**

**The league code.** 1920 is not `l-NFL`; it is **`l-APFA`**, and `l-NFL/y-1920`
returns a page with no team links rather than an error — a silent empty, which is
the failure mode that quietly produces "no data for this season". Any sweep must
assert that a season index yielded teams.

**The position vocabulary is era-correct and therefore era-specific.** 1920 gives
`LE RE LG RG BB WB LDH`; 1950 gives `LDH LDT LLB MG`; 2020 gives `CB FS ILB NT`.
Compound values appear throughout (`FB-LDH-WB-`, `LDE-RDE-NT`, `DT,LDT`) and
carry a trailing hyphen in at least one 1920 case. **Mapping this to PGM3's
position set is a per-era translation table, not a lookup**, and it is the main
work in using the source.

**Birth dates: 100% on every roster from 1950 on, 91% in 1920** (21 of Akron's
23). That is the age audit's reference, and it is independent of the Coaching
Tree.

**Every league Ryan listed resolves**, with codes that are not uniform: NFL and
AAFC and AFL teams use bare codes (`CLE`, `BOS`, `BA1`), while the USFL, WFL, XFL
and CFL prefix the league (`USFLBIR`, `WFLDET`, `XFLDAR`, `CFLBC`). Team codes are
also era-local — 1950's Baltimore is `BA1`.

**Not yet examined**: player IDs, the All-Pro and Coach-of-the-Year tables on the
season index, and the `stats/` and `results/` paths.
