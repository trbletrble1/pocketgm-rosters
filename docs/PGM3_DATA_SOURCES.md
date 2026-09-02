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

