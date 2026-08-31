# PGM3 Historical Roster — Build Notes

Written for Claude, to rebuild this for a different NFL season. Attach this plus `pgm3_toolkit.zip` at the start of a new chat.

Reference build: 2010 season, completed Aug 2026. Repo: `github.com/trbletrble1/pocketgm-rosters`

---

## 0. Read this first

**EVERY PGM3 roster/staff file you will be given is USER-MADE.** There is no official export in this project. That includes `PGMRoster2025-06-12_3.json` and the 2024 files in the repo. Their *structure* is trustworthy — field names, types, array shapes. Their *value distributions* are one person's choices and prove nothing about how the game behaves.

Ryan told me this. I then treated a user-made file as authoritative twice more, describing it as "the real file" and rebuilding staff distributions to match it. Do not do this. When you catch yourself writing "the real file" about anything other than a default-roster export, stop.

**There is still NO vanilla baseline.** Nobody has looked at what PGM3's own DEFAULT rosters produce for staff. Getting one is ten minutes of Ryan's time: new game → DEFAULT (QUICKEST) → look at the hiring screen. Ask for it before making claims about what the game normally does.

**Verify game behavior by asking Ryan to look, not by inferring from data.** He can read the screen; you cannot.

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

**The game recomputes STAFF ratings from attributes too, exactly like players.** A staff record whose `rating` is high but whose underlying skills are low will display correctly in the free-agent list and then COLLAPSE the moment they are hired. Tony Dungy showed 86 available, dropped to 61 on signing, because he was cloned from a template and only `HCcoach` was overwritten — `OCcoach` 53, `DCcoach` 63, `STcoach` 56, technical attributes averaging 59.

The fix: never set a staff rating without rebuilding every attribute to match. Fit each attribute as a linear function of `rating` from a donor file, per role, then apply with modest noise. Verify by checking that the role's primary attribute equals `rating` for every record:

    PRIM={'Head Coach':'HCcoach','Off Co-ord':'OCcoach','Def Co-ord':'DCcoach','Special Teams':'STcoach',
          'Head Scout':'Hscout','Off Scout':'Oscout','Def Scout':'Dscout',
          'Head Physio':'Hphysio','Assistant Physio':'Aphysio'}
    assert all(x[PRIM[x['role']]]==x['rating'] for x in staff)

**Only Head, Nose and Mouth share the appearance family digit** (skin tone). Hair, Beard and Eyebrows have an independent family digit which is COLOUR, not skin. Staff use `Hair6*` almost exclusively — presumably the grey/older set.

**Beard style letters, confirmed visually in-game:** `a` mustache + soul patch, `b` full circle beard, `c` van dyke, `d` goatee, `e` full beard, `f1`/`f2` stubble (barely visible), `g` clean shaven. There is no mustache-only option. Most real NFL coaches should be `g`.

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

Be explicit about which numbers are **derived from real data** and which are **constructed**. Ryan cares about this distinction and will ask.

**Derived — defensible:**

*Real names* for head coaches, coordinators and special teams from PFR team pages plus the game disc's coach records. Scouts and physios have no public source; names are invented, and say so.

*Coach ratings*: 60% career win percentage, 20% the team's season SRS relative to preseason Madden talent, 20% career playoff record, scaled by experience `(0.55 + 0.45 * min(1, games/160))`, normalised to 58–95. Produced Belichick 95, Childress 67 — defensible.

*Free agent coaches*: PFR's all-time coaches index (`pro-football-reference.com/coaches/`, fetchable) gives From/To years. Anyone whose last head-coaching year precedes the target season was available. **Cross-check FULL names against employed staff** — surname-only matching wrongly excluded Marty Schottenheimer because Brian Schottenheimer was employed. 2010 yielded 27 real coaches including Gibbs, Cowher, Dungy, Parcells.

*Team scouting ratings — from real draft performance.* This works well and is reusable:
1. Pull the 5 draft classes preceding the target season (e.g. 2006–2010 for a 2010 build). Use classes that had ALREADY happened — using later drafts is hindsight.
2. Fit expected `career_av` from `log(draft_pick)` across all picks (~R²=0.31).
3. Residual per pick = actual AV − expected. Average per team.
4. Split by side of ball using `pos`: offensive picks → Off Scout, defensive → Def Scout, all → Head Scout.
5. Shrink small samples: `z *= n/(n+8)`. Then `rating = 72 + z*9`, clamped 55–92.

Validation that it's working: for 2006–2010 this put New Orleans top (Colston in round 7), Green Bay second, with the Rams, Oakland and Detroit at the bottom. Cincinnati came out 66 offense / 92 defense, which matches their actual pattern.

**Constructed — say so plainly:**

*Free agent pool spreads.* Every role gets a range roughly 56–91: a couple of prizes, a solid middle, some duds. Rationale: when a head coach is fired his whole staff hits the market, so good coordinators genuinely are available. Ryan asked for this explicitly — "isn't it more lifelike if there aren't just a bunch of bums to hire?"

*All staff pricing.* Convex curve `pmin + (pmax-pmin) * q^2.2` where q is the rating's position in the pool. Keeps the middle cheap so only elite hires hurt. Per-role ranges used for 2010: HC 200k–5.6M (interpolated from a real curve), OC/DC 300k–3.6M, Head Scout 200k–2.4M, Off/Def Scout 150k–1.4M, ST 200k–1.6M, Head Physio 200k–2.0M, Asst Physio 150k–900k. Target team staff payroll ~3M–15M.

*Physio ratings.* No derivation exists. Games lost to injury is the obvious proxy but it's mostly luck. Random spread 56–91.

**Primary attribute must equal `rating`** (they correlate +1.00), and supporting attributes scale by the per-role median ratio with ~±8% noise. Vary both together since it is unclear which the game reads.

*Appearance accuracy for real coaches.* Skin family by known ethnicity (4/5 darker, 1-3 lighter), facial hair by what they actually had, glasses only for the handful who wore them. Cheap, visible, and the thing Ryan noticed most. Check for duplicate `appearance` arrays — a good file has nearly one per record (reference: 431 distinct of 432).

*Name collisions.* Check nobody appears in BOTH the employed staff and the free agent pool, and that no name repeats league-wide. Cloning templates produced 51 duplicates including 19 people who were simultaneously employed and available to hire.

**Ship staff pool changes as a SEPARATE FILE** (e.g. `PGMStaff_YEAR_ExpandedPool.json`) once people are using the original. Changing a file in place breaks saves for existing users.

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
- **Treated user-made roster files as authoritative after being explicitly told they were not — twice.** Rebuilt an entire staff model on one and repeatedly called it "the real 2024 file." This is the single worst pattern in this project.
- **Reported directory contents from a regex over a web page instead of testing the paths.** Told Ryan his `build-notes/` folder contained files it did not. Fetch the actual URL and check the status code.
- **Assumed a screenshot showed a running app** because a product name appeared in the corner. Read what is actually there.
- **Cloned staff records from one template and overwrote only the headline attribute.** Produced 27 coaches with an identical avatar and a rating that collapsed on hire. Whenever you build records by cloning, check that EVERY field was either deliberately set or is genuinely fine to inherit — especially `appearance` and the full attribute block.
- **Modified a file the user had explicitly asked me to leave untouched** (`PGMStaff_2010.json`, which people were already importing) while fixing something else. Restore from the live copy and ask.

## 9. Which years are viable

**Hard floor: 2002.** The NFL reached 32 teams that year. PGM3 has 32 fixed slots and every one must be filled. Before 2002 there are 1–6 empty slots, untested and likely fatal.

- **2004–2012** — best case. PS2 discs exist for real appearance data.
- **2013–2020** — contracts are *better* (OTC coverage ~100% by 2017 vs 37% for 2010), and no uncapped-year distortion. Appearance needs a community roster CSV.
- **2017 specifically** — 2,431 players with real cap numbers, and only the Raiders mismatched on branding.
- **Pre-2002** — blocked on team count.

Cosmetic branding mismatches to expect: Rams/Chargers/Raiders city moves, Oilers→Titans before 1997, no Ravens before 1996.

---

## 10. 2017 build — materials already staged

Everything needed is in the repo under `PGM3 2017 Working Files/`:

- `PFR2017/` — all 32 team pages, coaches page, standings page, and the 2018–2021 draft listings
- `madden_nfl_18/19/20/21/22` ratings — Madden 18 for the 2017 season, and 19–22 give each draft class its REAL rookie ratings (a genuine upgrade on 2010, where only the 2011 class had them)
- `2016/2017/2021 JINXROSTER PLAY.csv` — appearance. The 2017 file covers veterans, the 2021 file covers the draft classes. They agree 92.4% on shared players, so appearance data is intact.
- Two 2024 PGM files — **user-made, see section 0**

Fetch contracts yourself from the nflverse parquet. 2017 has ~2,431 players with real cap numbers, near-total coverage, and 2017 had a real salary cap so no uncapped-year compression is needed.

`PFR2010/2010_DraftFiles/` also holds the 2006–2010 draft listings used for the scouting derivation.
