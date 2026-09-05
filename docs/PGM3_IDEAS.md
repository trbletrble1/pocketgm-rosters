# Running list — things to dig into

Kept by the master session. Not the backlog (that's `PGM3_BACKLOG.md` in the repo,
which tracks defects). This is threads, ideas and unexplored ground.

---

## Immediate

**Coaching Tree MCP** — https://coaching-tree.app/mcp
Free, no auth, `get_team_staff` returns a full staff for any team any year.
This is the gap every source has. Add with:
`claude mcp add coaching-tree --transport streamable-http https://coaching-tree.app/mcp`
Test first: how far back does it go, and does it give coordinators or only head coaches.
Bonus: the coaching-tree genealogy itself is real lore for franchise stories.

**Do PSF and 2K5 carry staff?**
Every source found so far is players only. PSF is a different lineage entirely so
it may differ. The 2K5 franchise saves hold the draft classes we can't read — staff
may be in there too.

---

## The photograph library

26,145 headshots at `pgm3-sources/photos/PSFplayers/`, keyed by player name.

The `measured.csv` beside it does **not** work — cheek luminance 65.6% against a
55.7% base rate, and the one good-looking column is measuring the skin detector's
bias. Aaron Donald reads near-white; Tony Gonzalez reads near-black. The images are
fine; the analysis isn't.

A working pass needs: face detection placing the sample region, a key of name plus
position (there are two Josh Allens on disk), and scoring against Ryan's 61 verified
men before anything touches a file.

If it works it answers skin, hair colour, facial hair and the balding axis together.

---

## Buildable seasons

Five complete leagues, each from a single file:

| season | league | teams | source |
|---|---|---|---|
| 1966 | NFL + AFL | 24 of 24 | `1966Roster.ros` |
| 1976 | NFL | 28 of 28 | `1976Roster.ros` |
| 1978 | NFL | 28 of 28 | `1978Roster.ros` |
| 1984 | USFL | 18 of 18 | `Mike-USFL_WFL.ros` |
| 1996 | NFL | 30 of 30 | `1996Roster.ros` |

Plus PSF covers every year 1940–2025 at 43 real men per team, and the AAFC
1946–49 which nothing else reaches.

**1984 USFL as an expansion pool**: 621 men absent from every published file.

---

## Process changes discussed, not started

1. **One builder parameterised by season** rather than a script per build.
2. **Vanilla consulted at build time**, not after a reader complains.
3. **Provenance per field per player** — origin, not last hop.
4. **A source index** — for any year, what exists, what it covers, tested accuracy
   per field. Cheapest of the four and it unblocks the next build.
5. **A franchise-story template** — eight expansion teams done across two files and
   there's a pattern: real city history, a reason they're available, a doctrine that
   shapes the roster, a coach who embodies it.

Standing rule already applied: **every fix ships with a check.**

---

## The dataset / game question

Three shapes, increasing in size, each useful if you stop there:

- **Publish the archive as a dataset.** Every season 1940–2026, real players,
  ratings, faces, draft outcomes. Nobody has this.
- **A viewer.** Load any season, compare players across eras, look up any draft
  class. A weekend over a clean dataset.
- **A game.** `fbsim-core` (Rust, play-by-play, statistical basis) is the closest
  existing engine. `open-football` keeps its data in a separate repo from its
  simulator — that's the architecture this would want.

Consensus: **build the usable dataset first.** It's the only step that's useful
whether or not anything follows, and it needs a schema that isn't PGM3's import
format.

---

## Still worth hunting

- A **historical coaching database** — the Coaching Tree MCP may already answer this.
- A **later 2K5 mod release**. What we have is the 2021 alpha; he promised a full
  release plus weekly updates.
- Whether the **PSF mod's maker** built anything else. Best-decoded source of the
  three.
- More **standalone `.ros` seasons** from whoever made 1966/1976/1978/1996.

---

## Deferred with reasons

- **Third floor pass** on 2013, 2017, 2021 — $0.65M against vanilla's $0.70M.
  Declined; inside the roster-size confound's noise.
- **2021's rookie draw** is narrower than any other file's. Median inside range so
  no gate fires. Widening a distribution is its own decision.
- **Staff age errors** — Belichick 49 in 1979, Gase 35 in 2013. 58 surfaced
  incidentally by the namesake test. That list is the starting point for an audit.
- **Compound forenames split wrong** — Lee Roy Selmon stored as forename "Lee".
  Nine each in 1979 and 1986. Touches verified face keys.
- **Era-appropriate generated names** — Giuseppe Brewer in 1979. Needs a
  first-name-by-decade frequency source we don't have.

---

## Source leads found, not yet chased

**nflverse `draft_picks.csv`** — CONFIRMED GOOD, not yet used.
`https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv`
Carries season, round, pick, team, player, college, age, hof, allpro, probowls,
`seasons_started`, `w_av`, `car_av`, `dr_av` plus career stats. **Starts 1980.**
That is exactly the hindsight signal we have been extracting from hand-saved PFR
pages, in one download, covering every published file's draft classes except the
pre-1980 `draftNum` work.

**nflverse `players.csv`** — same release path, `players/players.csv`. Birth
dates, colleges, headshot URLs, rookie and last season for everyone. Bears on the
staff age audit and the photo work.

**Wikidata** — UNCHECKED. `query.wikidata.org` is blocked from the master
session's sandbox; needs adding to the build session allowlist. Question: are NFL
assistant coaching stints modelled there at all?

**Wikipedia coaching-career infoboxes** — every coach article carries the full
career as structured text (team, years, exact role, every stop). The 1979 build
already used Wikipedia manually. Bulk parsing is a different route to the same
coordinator data and it definitely exists.

**PFRA membership, $40** — `profootballresearchers.com/join.html`. Members-only
archive includes **a register of former assistant coaches** and **NFL/AFL
gamebooks back to 1950**, which are items 1 and 2 on the hunt list. Also AAFC
encyclopedia, WFL material, draft lists to 1936, all-pro lists to 1920. Held
pending other free options. Caveat: scans and documents rather than a dataset,
and a research association's archive has terms.

**Pro Football Archives** — `profootballarchives.com`. Fetchable, no Cloudflare.
Every head coach back to the 1920s, plus seasons, teams, players, drafts, awards,
boxscores and roster limits by year. Distinguishes Jim Mora from Jim Mora Jr with
separate IDs. Small site run by one person since 2006 — be polite about request
rates. Not on the build session's allowlist yet.

**spatto12/NFLCoaches** — GitHub, PFR-scraped, head coaches 1966-2023. Four CSVs:
history, every regular season game, every season, awards. Good for rating coaches;
no coordinators.

---

## Housekeeping

**Source file inventory needed before cleaning Downloads.** Some sources may exist
only in Downloads rather than in `pgm3-sources/`. Ask the build session for a full
inventory: where each file lives, whether it is in the sources tree, and whether
anything is referenced by a tool but missing.

**Back up `pgm3-sources/`.** 110MB+ of files gathered from forums that may not
exist in a year, and it currently exists in exactly one place.

**Scratch space is not durable.** `/tmp` was wiped mid-session twice. Commit before
reporting covers most of it; uncommitted scratch is at risk within a single day.

---

## TO DO — contract coverage gap, 1987–2010

The nflverse OTC bulk file (`historical_contracts.csv.gz`) is complete only for
**2017–2021** and stops at 2022. Coverage by year signed:

```
  1994-2003     9-40 per year       notable deals only
  2004-2010    92-322               a fraction
  2011-2016    616-2,074            filling in
  2017-2021    3,700-4,700          essentially complete
  2022         2,020                file cutoff, not OTC's
```

**The 1987–2010 gap is a different problem from the pre-1990 one:** that data
exists on overthecap.com, it just isn't in the free bulk download. Same for
2022 onward.

**Targeted fetch from OTC rather than a hunt.** Worth doing — if the claim is
that everything available was gathered, this is available.

Full picture across the archive:

```
  1965-1986   205 claims, 92 people   courts and newspapers
  1987-2010   scattered, notable only
  2011-2016   partial
  2017-2021   complete
  2022+       not held
```

---

## Feature direction — "stats with heart"

The archive's differentiator is **a generated, human-sounding bio for every one
of ~40,000 people** — most of whom have never had a paragraph written about them.

Possible because every sentence can be built from claims: birth date (96%+
everywhere), hometown, college (100%), and the full stint history including
cross-league careers. Nothing invented, nothing plausible-but-unsourced.

**What makes it read as written rather than generated** is noticing patterns the
data already holds: one-club men, journeymen, league-crossers, war-year gaps,
players who became coaches, fathers and sons, shortest and longest careers. And
bio structure should vary by career shape — a one-game man in 1926 shouldn't get
the same sentences as a fifteen-year Hall of Famer.

**Where a media guide carries real prose, quote it with attribution** rather than
paraphrasing.

Anyone else building this would have a model write the bios and produce 40,000
confident fictions. This design can't, structurally. That's the differentiator.

---

## Two features, specced (full spec: TWO_FEATURES_SPEC.md)

**A. Reader corrections.** A small control on every surface showing data — submit a
correction with a mandatory explanation, plus a separate "something looks broken."

The correction is a *claim*, not a support ticket: `source: reader_correction`,
lowest tier in the ranking, never silently changes a value, and doesn't require the
reader to be right. The snapshot must capture the **resolution policy version**, or
a correction filed six months ago can't be judged against a policy that's changed.

**B. The eBay pipeline.** eBay is the deepest contract vein found — the tier below
the auction houses. Contracts, offer letters, paycheques. New ones appear
continuously and sold listings expire after ~90 days, so this is a **periodic
sweep**, not a one-time pull.

Find and fetch: automated via eBay's API, querying the document class
(`"standard players contract"`) not player names.

Read: partly automated. Typed amounts yes, handwritten no — which is most pre-1960.

**The screen is the piece that makes it scale.** The archive now holds enough
(league averages from 1933, per-club payrolls, the Kramer and Gregg runs, the
per-game convention of the 1920s–40s) to check a machine reading against its era
before a human sees it. Catches dropped commas, per-game read as per-season, and
out-of-range digits. **Cannot catch $7,200 read as $7,500** — so machine-read and
human-read stay separate acquisition states and never pool.

Ryan reviews the queue only: handwritten, low-confidence, screen failures. The band
tightens as more are read, so the load falls over time.

**Legal note:** eBay's API terms restrict storage; bulk-fetching seller images is
grey. Same for Heritage and Lelands scans. Fine for private research — the dataset
cites the figure and the listing, never republishes the image.

---

## Auction contract hunt — status

**The vein went dry** after two waves across Heritage, Lelands, SCP, REA, Goldin,
Memory Lane and Hunt. Sixty contract-seasons located, about half read.

**Three multi-season runs found**, which are worth more than any number of one-offs:

- **Jerry Kramer 1958–68** — ten consecutive years, ordinary guard. Read: $7,750
  rising to $26,000, with the jump landing 1962–64 as the AFL bidding war bit.
- **Ray Nitschke 1964, 1965, 1968, 1972** — the last explicitly his final contract.
- **Forrest Gregg 1964, 1966–67, 1968 amendment** — and the most revealing, because
  the Packers split his pay four ways: salary, scouting employment, signing money,
  incentives ($500 if the team won 10 games), and later $24,000 deferred.

**Earliest surviving contract: Art Schmaehl, 1921, Acme Packers of Green Bay** —
the APFA, before the league was called the NFL.

**Per-game pay is the norm for the early era, not an oddity:** Trafton $90 (1923),
Pearce $85 (1923), Schammel $150 (1934), Stonebraker $225 (1942). Pearce's contract
even states the timing — 90% right after each game, the rest held to season's end.

**Still open:** the Mackey trial exhibits (National Archives, docket 4-72-Civil 277),
and the unpublished files of House Antitrust Subcommittee No. 5, 85th Congress —
both records requests rather than searches. Ryan's brother, an attorney, is the
right person to ask.

---

## Feature — cross-era comparison with an adjustment factor

**Ryan's brother's idea, and he pushed back on the cautious version of it.** The
percentile-only approach ("Unitas was 97th percentile in 1959") is safe and less
useful. He wanted an actual **conversion** — what Unitas's numbers would look like
in Brady's era — with the argument that *"it wouldn't have to be exact and you can
state that, but if you could figure out how to do it, it would be a real feature."*

**He's right, and it isn't invention.** It's a computation over data now held:
express a season against its own league distribution, map onto the equivalent point
in the target season's. Every input measured, the arithmetic stated, and the result
marked **derived** — the same treatment passer rating already gets.

**Why this one is defensible where other sites' aren't.** Most era adjustment is
somebody's formula with a hand-tuned constant. This would be built from the actual
league distribution in both seasons, and a reader could see which seasons, which
columns, and which method.

### Design decisions to make deliberately

**Which method.** Percentile mapping, ratio to league average, and standard
deviations from the mean are all honest and give **different answers**. Pick one,
name it, show the alternative. Same shape as a contested value.

**Show the raw numbers alongside.** The lopsidedness is interesting — 1959 passing
volume genuinely was a fraction of 2007's, and hiding that would be dishonest.

**Handle the incomparable cases.** Unitas versus Brady works. A 1926 two-way lineman
versus a modern guard has **no shared statistic at all** — the archive already knows
this, since 17 position codes have no salient statistic in any era.

### Career versus career, not just season versus season

**Adjust each season, then sum.** That gives an era-adjusted career line rather than
a single year, and it does two useful things:

**Longevity becomes visible as itself** — a 1950s career was shorter because the
schedule was 12 games and careers ended earlier. Per-season adjustment handles that
rather than penalising the older man.

**Peak and accumulation separate** — best five seasons alongside the full career,
which is where most era arguments actually live.

**The schedule-length wrinkle is a real choice.** 12 → 14 → 16 → 17 games. Per-game
is the fairer athletic comparison; per-season is what actually happened. **Show
both.**

### Also applies to teams and coaches

**Coaches may be the best version** — win rates adjusted for era across careers of
very different lengths, which nothing existing does.

### Salaries too

The same treatment: express a salary as a share of that season's league average.
`apy_cap_pct` does exactly this for the modern era, and the archive now holds league
averages back to 1933 — so it can be computed for the whole span.
