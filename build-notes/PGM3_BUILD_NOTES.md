# PGM3 Historical Roster — Build Notes

Written for Claude, to rebuild this for a different NFL season. Attach this plus `pgm3_toolkit.zip` at the start of a new chat.

Reference build: 2010 season, completed Aug 2026. Repo: `github.com/trbletrble1/pocketgm-rosters`

---

## 0. Read this first

**The reference file (`PGMRoster2025-06-12_3.json`) is USER-GENERATED, not an official PGM3 export.** Its *structure* is trustworthy — field names, types, array shapes, the position-weighted OVR formula. Its *content distributions* are not reliable evidence of how the game behaves. Do not conclude "the game works this way" from that file's value distributions. I did, twice, and was wrong both times.

**Verify game behavior by asking Ryan to look, not by inferring.** He can start a default-roster save and read the screen. Several hours were lost to me theorizing about PGM3 internals from data alone.

---

## 1. PGM3 file format

Two JSON files, flat arrays of objects.

**Roster: 52 fields per player.** Key ones:
- `teamID` — one of 32 fixed modern IDs (ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS), plus `Rookie` and `Free Agent`
- `rating`, `potential`, `age`, `position`, `teamNum`
- `salary`, `guarantee`, `length` — current contract
- `eSalary`, `eGuarantee`, `eLength` — what the player is *asking for*
- `draftSeason`, `draftNum`
- `appearance` — 9-token array
- `growthType` — 31-element array
- `iden` — uppercase UUID, must be unique
- ~30 skill attributes

**Staff: 71 fields.** `role` is one of: Head Coach, Off Co-ord, Def Co-ord, Special Teams, Head Scout, Off Scout, Def Scout, Head Physio, Assistant Physio. Exactly **9 per team**. Plus a Free Agent pool.

---

## 2. Critical mechanics — these are verified

**The game ignores `rating` and recomputes OVR from position-weighted attributes.** This is the single most important fact. Setting `rating: 94` on Rodgers displayed him as 65 until the attributes were refitted. `weights.json` in the toolkit has fitted linear coefficients per position (R² 0.96–0.998). Method: compute predicted OVR, then apply offset `d = (target - predicted) / sum(weights)` iteratively, clamped 1–99. All players land within 1 point.

**`draftSeason` runs on the game's internal clock, not calendar years.** Current season = 2026. For a 2010 build the offset was **+16** (2010 → 2026, 2011 draft class → 2027). Recompute this offset for a different year.

**A rookie/draft pool MUST exist or the game crashes on import.** Prospects need `draftSeason` ≥ currentYear+1. Four classes worked well.

**`draftNum` above 224 clamps to 224, which the game reads as undrafted.** Costs ~30 real late-round picks per class. Unavoidable.

**Cap is $280M and counts `salary + guarantee`, not salary alone.**

**Staff `length` must be ≥ 1 for employed staff** or they display as a vacancy/offer.

**`appearance` is 9 tokens:** `[Head{n}{a}, Eyes, Hair, Beard, Eyebrows, Nose, Mouth, Glasses, Clothes]`. The family digit `{n}` of Head, Nose and Mouth must match. Hair token family digit = hair colour.

**Expiring contracts are the game's business, not the file's.** PGM3 filters to players with **4+ accrued seasons** (computed from `draftSeason`) and then picks among them itself, differently each load. `length` controls the displayed contract and cap accounting, not who hits free agency. This is verified: a test file with all of one team at `length=1` and another at `length=7` displayed correctly, but the expiring list still varied.

---

## 3. Data sources

| What | Where |
|---|---|
| Rosters, ages, jersey numbers, coaching staffs, drafts, career AV, SRS | Pro-Football-Reference — Ryan saves pages manually as "Webpage, HTML Only", commits to repo |
| Player ratings | `maddenratings.weebly.com` — team spreadsheets and full-league files |
| Real skin tone / hair colour | Madden PS2 game disc, `DATA/DB_TEAMS.DAT` (PS2 releases only, through Madden 13) |
| Skin/hair for post-PS2 years | Community Madden 08 PC roster `.ros` exported to CSV via a Windows roster editor — has a labelled `PSKI` column |
| Contracts, real cap numbers | `github.com/nflverse/nflverse-data/releases/download/contracts/historical_contracts.parquet` |

**Use the parquet, not the CSV.** The parquet has 51,931 rows vs the CSV's 31,893, and includes a `season_history` field with per-year `base_salary`, `prorated_bonus`, `cap_number`. That's the good data. Needs `pip install pyarrow --break-system-packages`.

**PFR pages must be saved by Ryan** — the site blocks automated fetching. Ask him to save and commit; then fetch from `raw.githubusercontent.com`.

---

## 4. Build pipeline

1. **Rosters** from PFR team pages. Positions resolve from PFR codes first, Madden second, weight-based fallback last. Adjust 3-4 defensive ends → DT.
2. **Ratings** from Madden spreadsheets, joined by normalised name. **Join on name alone, not team+name** — players change teams between the summer Madden roster and the season, and 52 were badly mis-rated because of this.
3. **Refit attributes** so computed OVR matches the Madden overall.
4. **Draft classes** from PFR draft pages. Current rating from that year's Madden if available; **potential from real career outcomes** (career AV, All-Pro selections, years started). This is what makes drafting feel right.
5. **Contracts** — real per-season cap numbers from the OTC parquet where available; model the rest, floored at the real CBA minimum by accrued seasons (derive the schedule empirically from the 10th percentile of real base salaries by years in league).
6. **Contract length** — rookie deals from real draft slot + years in league; veterans rank-mapped by rating within age band.
7. **growthType** — index by `(age, potential gap)` against the reference. Correlation between potential headroom and early growth should be ~+0.9. If it's low, high-potential players never develop.
8. **Appearance** — see section 5.
9. **Staff** — see section 6.
10. **Validate** — see section 7.

---

## 5. Appearance extraction (PS2 discs)

Ask Ryan for `DB_TEAMS.DAT` from the disc's DATA folder (~900KB). `PLADATA.DAT` is the playbook, not players. `PLYRFACE.DAT`/`COACHES.DAT` are mesh and texture data.

**Format:** `TERF` container. Field definition table gives 4-char tags with bit widths and offsets. Player records are **104 bytes**, first name at byte 0, last name at byte 11.

**Bit order is LSB-first.** Field offsets in the table are NOT the actual positions — every 7-bit attribute sits **55 bits below its stated offset**. Verified for Madden 11 and 12 PS2:

- `speed` bit 308, `agility` 349, `jumping` 535, `acceleration` 270, `stamina` 241, `toughness` 324, `kick accuracy` 263, `kick power` 581
- **skin tone: bit 356, 2 bits** — values 0=light, 1=medium, 2=dark
- **hair colour: bit 424, 3 bits**

**Always validate before applying:** brute-force `speed` against the Madden spreadsheet for that year. Madden 11 hit 94.4%, Madden 12 96.9%. If it's below ~85% the layout is wrong or the roster has been edited.

**Do not trust field names.** `PSKI` is labelled "Player Stats Kicking" in the community definitions file and "SKIN_COLOR" in another. It is skin tone. Find fields by validating values, never by name.

**Coach records** are 68 bytes in the same file, 4 per team, with names like `D.Toub`. Useful for special teams coordinators, which PFR does not list.

---

## 6. Staff build

**Real names** for head coaches, coordinators and special teams from PFR team pages plus the disc. Scouts and physios have no public source — names are invented, and say so.

**Coach ratings are derived, not invented:** 60% career win percentage, 20% the team's season SRS relative to its preseason Madden talent level, 20% career playoff record, all scaled by experience `(0.55 + 0.45 * min(1, games/160))`. Then normalise to 58–95. This produced Belichick 95, Childress 67, Cable 70 — a defensible hierarchy.

**Free agent coach pool:** pull PFR's all-time coaches index (`pro-football-reference.com/coaches/`, fetchable). Anyone whose last head-coaching year is before the target season was available. **Cross-check full names against the employed staff** to exclude coordinators — surname-only matching wrongly excluded Marty Schottenheimer because Brian Schottenheimer was employed.

**Other free agent pools have no data source.** Spread was constructed to make hiring interesting: a couple of prizes at 84–90, solid at 75–83, average 64–74, duds 55–63. Asking price on a convex curve, `floor + (top*1.05 - floor) * q^2.6`, so only elite hires hurt. **Vary both `rating` and the underlying attributes together** since it's unclear which the game reads.

---

## 7. Validation — run before every handoff

Structural: key mismatch, type mismatch, duplicate `iden`, empty names, `potential < rating`, `appearance` length ≠ 9, `growthType` length ≠ 31, negative money, out-of-range numerics.

Game rules: no team over $280M, roster sizes ≤ 69, no duplicate jersey numbers within a team, exactly 9 staff per team, employed staff `length` ≥ 1.

Accuracy: ages vs PFR (should be 99%+), ratings vs Madden (89%+ exact), team assignment vs PFR, draft picks at correct slots.

Distributions vs reference: `corr(cap hit, rating)` ~+0.6, `corr(length, age)` ~−0.4, `corr(potential gap, early growth)` ~+0.9.

---

## 8. Mistakes I made — do not repeat

- **Searched only part of a file and declared data absent.** Told Ryan a `.ros` had no 2014 players; it had three record blocks and I searched one. Beckham, Manziel, Bortles were all in it.
- **Sent him hunting for a Madden 15 PC release that never existed.** Madden's last PC release before 2019 was Madden 08.
- **Assumed field names meant what they said.** Cost hours on `PSKI`.
- **Joined ratings on team+name** instead of name, mis-rating 52 players who changed teams.
- **Changed ratings without updating growth curves**, and salaries without updating contracts. Any time one side of a linked pair moves, check the other.
- **Loose fuzzy name matching created false positives** — paired Hamza Abdullah with his brother Husain. Require surname exact plus first-name match; a similarity threshold alone is not enough.
- **Reported a coverage number that counted players I had deliberately skipped.** Count what was actually applied.
- **Called the project finished repeatedly when it wasn't.** Ryan found the next step every time. Do not propose stopping.

---

## 9. Which years are viable

**Hard floor: 2002.** The NFL reached 32 teams that year. PGM3 has 32 fixed slots and every one must be filled. Before 2002 there are 1–6 empty slots, untested and likely fatal.

- **2004–2012** — best case. PS2 discs exist for real appearance data.
- **2013–2020** — contracts are *better* (OTC coverage ~100% by 2017 vs 37% for 2010), and no uncapped-year distortion. Appearance needs a community roster CSV.
- **2017 specifically** — 2,431 players with real cap numbers, and only the Raiders mismatched on branding.
- **Pre-2002** — blocked on team count.

Cosmetic branding mismatches to expect: Rams/Chargers/Raiders city moves, Oilers→Titans before 1997, no Ravens before 1996.
