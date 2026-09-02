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

Against the registry's hand-verified players it agrees **10 of 11** reachable.
The miss is **Aaron Donald, whom RFM has as light** — plainly wrong, and a
reminder that it is a source and not an oracle. Against Ryan's photo
confirmations, 8 of 9.

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

### Recommended precedence — NOT YET APPLIED, needs a ruling

1. registry `_verified_keys` above everything (Donald shows RFM errs)
2. archive where it has **5+ sources** (98.5% agreement makes this near-moot)
3. **RFM for the 424 players the archive cannot reach at all** — the clear win
4. RFM as the tie-break in the thin 1-2 source band, where the two agree only
   77.4% and one of them is wrong a fifth of the time. Photo confirmation is
   still the only thing that settles those.

