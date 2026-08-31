# Task — 2000 season build, steps 3–10

Build `PGMRoster_2000.json` and `PGMStaff_2000.json`.

Written by the master session 2026-08-31 against repo commit `db0bc3c`.

**Read first:** `CLAUDE.md`, `docs/PGM3_PROJECT_HANDOFF.md`, and the 2000 sections
of `docs/PGM3_PRECEDENTS.md` (seven new sections, lines ~1348 onward). Everything
below assumes those. Where this brief and the handoff disagree, say so rather
than picking one.

---

## What is already settled — do not re-derive

| item | state |
|---|---|
| Source audit | Done. All findings in `PGM3_PRECEDENTS.md` |
| Coaching staffs, 31 teams | Done. `sources/coaches_2000.csv`, 124 rows, HC/OC/DC/ST |
| Cohort | `TGID` 1–31 = 1,637 rostered. Drop 0, 32, 33, 34 |
| Free agents | `TGID` 1009 + 1014 = 694. **Keep all** |
| Scouts and physios | Generated. Deliberate exception, ruled |
| `draftNum` source | nflverse `draft_picks`. `PDRO` is a cross-check only |

**Two deliberate blanks in the coach file** — `JAX/OC` and `NE/DC`. Coughlin ran
the Jacksonville offense, Belichick the New England defense. Both are absences in
the season, not gaps in the research. Do not fill them with an invented name;
assign the slot per whatever convention the published files use for a vacant
coordinator, and log it.

---

## BLOCKING — needs a ruling before step 6

**2000 had 31 teams. PGM3 expects 32 modern team IDs. The vacant one is `HOU`.**

The Titans are `TEN` by 2000, so Houston has no franchise until 2002. But every
published file, **including 1986, carries all 32 team IDs with `HOU` populated** —
55 players in 1986, 55 in 2004, 69 in 2021, and 9 staff in 1986.

1986 solved the same shortfall by inventing four expansion franchises. That is a
precedent, but it was a substantial creative build with its own lore, not a
default.

Three options, all needing Ryan:

1. **Ship 31 teams and leave `HOU` empty.** Cheapest. **Untested** — no file has
   ever done it and nobody knows whether the game accepts a missing team. Would
   need an import test before the build commits to it.
2. **Invent an expansion franchise for the `HOU` slot**, per the 1986 precedent.
   Consistent with every published file. Costs a research and lore pass, and puts
   ~53 invented players in the file.
3. **Something else** — e.g. stock `HOU` from the free agent pool as a
   developmental squad.

**Do not guess this.** Stop and ask. It changes the roster count, the staff count
and the payroll checks.

---

## Step 3 — Cohort and positions

Drop `TGID` 0, 32, 33 and 34. Assert the survivor count is **1,637 rostered +
694 free agents**.

`teamID` uses **modern IDs for every season** — 2000 St. Louis is `LAR`, Oakland
is `LV`, San Diego is `LAC`, Tennessee is `TEN`. Getting this wrong breaks those
teams on import.

Resolve positions from Madden's `PPOS`, which is specific. Check the **CB/S ratio
against the published files (1.06–1.30)** before moving on.

**`PJEN` carries real jersey numbers — do not generate `teamNum`.** De-duplicate
within team-season, resolving in favour of the more experienced player. Free
agents and prospects get 0.

---

## Step 4 — Appearances (early, not last)

`PSKI` in this file is **four-level**: 0 light (32.4%), **1 abstain** (11.1%,
bimodal ~54% dark), 2 dark (30.0%), 3 dark (26.5%). Anchor-tested 19/20 light and
17/17 dark. **Value 1 must abstain, not vote** — forcing it is a documented past
error with its own precedent.

Hair from `PHCL`: `0`→family 1 black, `1`→5 blond, `2`→3 brown, `3`→4 red,
`4`→2 light brown. Reliable for black vs non-black (98%); shade is muddle and
cannot be resolved.

Face shape from real weight (`PWGT` + 160) and age, thresholds 260 lb and age 30.
Variants `a` thin young, `b` thick young, `c` thin old, `d` thick old.

**Run the conditional check the moment appearances are built:**

    python3 tools/pgm3_validate.py conditional PGMRoster_2000.json \
        "sources/madden/2000_-_PLAY.csv" appearance PSKI

Groups must separate. If every `PSKI` value produces the same family mix, the
source was never used.

**Do not source skin from the 2003 or 2004 PLAY files.** Both are scored unusable
(0.647, ~0.59–0.65). They are fine for hair and for ratings.

---

## Step 5 — Ratings, rescaled per position

**Both inflation traps are live in this file.** Measured on the rostered cohort:
kicker/punter at **median `POVR` 93** and fullbacks at **86.5**, against a league
median of 78.

- Rescale **per position**, never cohort-wide. A cohort-wide rescale puts kickers
  and punters at the top of the league — documented past failure.
- **Fullbacks → RB**, but map against the **real FB cohort** in the published
  files (median 65, ceiling ~83), not the RB pool. Madden grades FBs on blocking.
- **Six columns exceed 99** among the attribute-shaped fields — `PCHS` 109,
  `PLSS` 109, `PAWR` 108, `PSBS` 107, `PTGH` 104, `PTHP` 104. Do not clamp to
  0–99 on read; a single clipped row is invisible to every distribution check.

---

## Step 6 — Attributes

Direct map per the handoff, **plus `PBTK` → `trucking`** (correlation 0.882, not
in the handoff's list).

Use **`PSTA` for stamina, not `PSTM`.** Then verify:

    python3 tools/pgm3_validate.py conditional PGMRoster_2000.json \
        "sources/madden/2000_-_PLAY.csv" stamina PSTA

**Direct-mapped attributes still need per-position quantile mapping.** Raw Madden
compresses at the low end; copying values ships several attributes 20+ points
low.

**Personality fields do not source from this CSV.** `PEGO`, `PMOR`, `PIMP`,
`PLPL`, `PTEN`, `PVCO`, `PKRT`, `PYWT`, `PFEx`, `PTAL` all tested below 0.34
against `loyalty`/`greed`/`ambition`/`discipline` and the five unsourceable
attributes, most under 0.1. Keep deriving them from per-position percentiles.

Then refit against `weights.json` bounded by observed min/max, and populate only
each position's live attributes.

---

## Step 7 — Contracts

- **`PCYL` is contract years remaining. Use it.** Holds `≤ PCON` on 1,637 of
  1,637 rows, 31.8% at one year against a published target of 34–39%. This is the
  field previous builds reconstructed by hand.
- **`PTSA` for total value, not `PVTS`** — they differ on 449 rows.
- **`guarantee = PSBO × (length ÷ PCON)`.** `PSBO` is the full original bonus,
  not the remainder.
- Rostered `length ≥ 1`, free agents `length = 0`, nothing above 7.
- **Ship real 2000 numbers. Do not era-scale.** The precedent is explicit:
  published files inflating 2004 to $179M against a real $80.6M cap is a defect
  nobody caught, not a convention. Pass `--team_cap=` for the real 2000 figure.
- **`eSalary`, `eGuarantee`, `eLength` are game-computed.** Ship sane values for
  first-load validity and spend no time fitting them.

---

## Step 8 — Staff

Coaching names are done. What is not done:

- **Ratings.** Head coaches from career record **through 1999** (the season being
  built hasn't happened from their perspective). Coordinators and special teams
  from **2000's own units** — same-season for a historical build. Do not use 1999
  for coordinators; that rule is current-season builds only.
- **Special teams rankings.** Gosselin published through 2023; check he covers
  2000. If not, this needs a source or a ruling.
- **Scouts and physios** — generated, fitted per role. Check invented names
  against every real coach name across all files.
- **Free agent coaching pool** — real coaches form a clean top block, invented
  names strictly below all of them. Needs 2000 employment status verified for
  each candidate.

Per-role rules that have bitten before: `eGuarantee` is head-coach-only among
rostered staff; every coach carries all four coaching attrs; primary attribute
must equal `rating`; scout specialties side-constrained; `growthType` is **51**
elements for staff; `startSeason` needs a real age-correlated spread, not a flat
value.

---

## Step 9 — Draft classes 2001–2004

nflverse `draft_picks` is reachable and covers all four:

    https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv.gz

246 / 261 / 262 / 255 picks for 2001 / 2002 / 2003 / 2004.

**Rookie-rating coverage — better than the file list suggests.** There is no 2001
or 2002 PLAY export, but both classes appear as veterans in files we have:

| class | best source | gap |
|---|---|---|
| 2001 | `2003 - PLAY.csv`, `PYRP` 2 (234 players) | **2 years** |
| 2002 | `2003 - PLAY.csv`, `PYRP` 1 (278) | 1 year |
| 2003 | `2003 - PLAY.csv`, `PYRP` 0 (270) | correct year |
| 2004 | `2004 - PLAY.csv`, `PYRP` 0 (242) | correct year |

Adjacent-year real attributes beat percentile fill by a wide margin (MAE 2.35 vs
8.52), so use them. **`PYRP` counts NFL seasons played, not seasons since the
draft** — a player who missed a year drifts, so join on nflverse draft year, not
on `PYRP` arithmetic.

**Ruling needed:** the 2001 class at a two-year gap is outside "adjacent". Tier 2
with damping, or drop to tier 3? Ask.

**Potential is raise-only** — draft slot baseline plus career-achievement raise,
never lowered. Do not impose a gap cap tighter than the other files without
evidence.

**`draftNum` — keep real pick numbers above 224.** 224 is the undrafted floor and
is also a real pick, so the value is overloaded; the published files already work
this way and carry real picks to 255 (2004), 262 (2021) and 329 (2007). Do not
clamp.

Strip `HOF` from surnames before splitting names. Re-check every rebuild — new
inductions add names.

---

## Step 10 — Face registry, then validate

**Registry runs last. Nothing runs after it.** `reference/PGM3_FACE_REGISTRY.json`.

- **Apply the family digit, never the whole array**, for players — the aging
  variant legitimately differs by season. Staff are the exception.
- **`_verified_keys` is locked.** A pass that disagrees skips and logs.
- **Rebuild every season the registry touches**, not just 2000.
- 2000 sits between 1986 and 2004, so expect namesake collisions across a
  generational gap. Key on `name|position|teamID`; name+position is **not**
  sufficient across eras — measured false-match rate was ~81% on the 1986 cohort.

Then all three gates:

    python3 tools/pgm3_validate.py roster PGMRoster_2000.json PGMRoster_2004.json PGMRoster_2007.json PGMRoster_2021.json
    python3 tools/pgm3_validate.py staff  PGMStaff_2000.json  PGMStaff_2004.json  PGMStaff_2007.json
    python3 tools/pgm3_validate.py faces  PGMRoster_*.json

Plus the conditional passes for `stamina`, `appearance`/`PSKI`, and each
direct-mapped attribute. Report the conditional output alongside the validator
result.

---

## Standing rules for this build

**Assert the count on every keyed write.** `assert len(out) == len(inp)`. Silent
overwrite is invisible to every other check — a 1986 registry write produced
1,745 entries from 1,746 players and raised nothing.

**Never invent data when real data exists.** An honest gap beats a plausible
invention. Leave the field empty and log it.

**Stop and ask rather than guess** where a convention is unclear. Three questions
are already flagged above: the `HOU` slot, the 2001 class tier, and Gosselin's
2000 coverage.

**Pin what you report.** Say which commit you are holding when reporting a
finding.
