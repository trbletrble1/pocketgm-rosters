# PGM3 Roster Project — Working Reference

> **Read alongside this file (added 2026-08-31):**
> - `PGM3_SOURCE_QUALITY.md` — which Madden CSVs can be trusted for skin, and how
>   to test a new one. Supersedes any source guidance below.
> - `PGM3_HAIR_VOCABULARY.md` — the observed hair style tokens. Supersedes the
>   list in the vocabulary section below.
> - `PGM3_VERIFIED_FACES.md` — the two registry blocks, and the rule that hand
>   edits are locked.
> - **`PGM3_DATA_SOURCES.md` — read this before hand-researching anything.**
>   Draft classes, player biographies, birth dates, physicals and combine
>   measurements are all bulk downloads from nflverse. Birth dates solve the
>   namesake problem outright. **PFR access depends on which client you are** —
>   see the transport table under "Draft prospects — potential" below. From a
>   build session it is blocked; route PFR pulls through the master session, or
>   use Wikipedia and nflverse.
> - **`.ros` files no longer need Windows.** `tools/rosgui.py` decodes them
>   directly, verified exact against Xtreme on three files. Its "Screen" button
>   gives a usable / unusable verdict in a second — see `PGM3_SOURCE_QUALITY.md`.
> - **REGISTRY: re-pull before applying it.** `PGM3_FACE_REGISTRY.json` gained
>   the first entries ever in `_verified_keys.staff` on 2026-08-31 — 18 coaches
>   Ryan hand-edited in 1986, six of which propagate into `staff_faces` and
>   changed `PGMStaff_2004/2007/2010/2013`, 35 records across five files.
>   **Check `_verified_keys.staff` reads 18, not 0, before any registry pass.**
>   Note also that **the staff key is name alone and has a namesake hole**: Jim
>   Mora Sr. (1986 New Orleans) and Jim Mora Jr. (2004 Atlanta) are two men and
>   only the 2007 file spells the suffix. The merge blocks propagation for any
>   name wearing a generational suffix anywhere in the archive; assume that rule
>   applies to staff generally.
> - **Open finding (2026-08-31):** head family 4 ranges 14–39% across the
>   published files, worst in 2010. Not a regression — it predates the skin
>   repair and has never been investigated. `pgm3_validate.py faces` flags it.
> - `madden_skin_groups.json` has been **removed from the project** — it scored 78%
>   against anchors and its `agree` field measures consistency, not correctness.
>   If a copy resurfaces, do not use it.

This is the accumulated knowledge from building PocketGM 3 roster files. Read this before starting work. It exists because handoffs to fresh sessions have failed before, and every item here was learned by getting something wrong first.

---

## What this project is

Building historical and current NFL roster files for **PocketGM 3** (PGM3), a mobile football management sim. Each season needs two files:

- `PGMRoster_YYYY.json` — players (rostered, free agents, draft prospects)
- `PGMStaff_YYYY.json` — coaches, scouts, physios

Files are hosted on GitHub and imported into the game by URL.

**Repo:** `https://github.com/trbletrble1/pocketgm-rosters`
**Import URL pattern:** `https://raw.githubusercontent.com/trbletrble1/pocketgm-rosters/main/PGMRoster_2004.json`

**Published:** 2004, 2007, 2010, 2013, 2017, 2021 — roster + staff each, all validated. Six seasons.
**Remaining:** 2026 (scoped, staff research done, waiting on post-cut rosters).

Anywhere below this line that says "three files" or "four files" is a measurement taken before later seasons shipped — treat it as a subset and re-check before relying on it.

---

## Non-negotiable principles

These came from the person running the project. Violating them wastes everyone's time.

1. **Never invent data when real data exists.** Search for it, ask for it, or say it doesn't exist. Don't estimate and present it as fact.
2. **Never attach invented ratings to real people's names.** Especially in coaching pools. If depth is needed, use clearly fictional names.
3. **All roster years follow the same methodology.** If one file does something differently, that's a bug, not a variation — unless there's a stated reason.
4. **Finish the whole job.** Fixing 16 of 32 teams and calling it done is not acceptable. If the data only supports partial work, say so explicitly rather than quietly stopping.
5. **"It hasn't broken yet" is not evidence something is correct.** Several bugs sat in published files for months without being noticed.
6. **When the person reports something odd in play, take it seriously and check the data.** Every single report has turned out to be a real bug — a fullback rated 90, a coach with empty star ratings, a blocked contract extension. Look at the actual record and compare the field against the working files before explaining it away.
7. **Bulk operations run before hand edits, never after.** The person's hand-edited avatars have been put at risk twice — once by a duplicate-appearance rule that would have overwritten a face they set, once by a library pass that overwrote four hand-edited prospects. There is no safe cohort. Merge their latest export last.
8. **Partial compliance is evidence of a rule, not evidence against one.** A field that follows a pattern in 90% of records is a rule with noise. Reading that as "no rule applies" produced a wrong line in this document that stood for a whole session and propagated into two files. If most records obey something, treat it as the rule and the exceptions as errors.

---

## Before comparing files, check you have the current ones

**Four separate stale-artifact incidents happened in one session.** Every one produced a confident, wrong conclusion — a bug asserted in a file that had already been fixed, a rule argued against on the basis of flattened values that had since been restored, two cohort comparisons that disagreed because one side was old.

The mechanism is `raw.githubusercontent.com/.../main/...` serving a cached copy. The push was fine; the CDN wasn't current. **And the obvious check fails**: ETag is a content hash, so identical ETags across two pulls normally proves the content is unchanged — but it's the hash of the *cached* object, so the check is served from the same cache it's meant to detect.

**The pattern is not about who holds the file — it's about having two copies at all.** The fourth incident was entirely local: a pipeline wrote appearances into `step2_roster.json` while the next stage read `step3_roster.json`, so a verified fix never reached the output. Same shape, no network involved. **Rebuild in place on the artifact that actually feeds the next step**, rather than producing a parallel file that can drift.

**Fix for the network case: clone the repo. Don't fetch individual files from `raw.githubusercontent.com` at all.**

    git clone --depth 1 https://github.com/trbletrble1/pocketgm-rosters.git repo
    cd repo && git rev-parse --short HEAD    # the version you are holding — report this

One command gets all ten published files and tells you exactly which commit you have. It goes over the git protocol rather than the raw CDN, so the stale-copy failure mode does not exist on this path, and **Ryan never has to supply a SHA.** Pinning a raw URL to a SHA also works, but it needs a human to fetch the SHA by hand every time, which is a chore that will eventually be skipped.

Verified 2026-08-28: a clone at `30e3369` produced a `PGMRoster_2004.json` byte-identical to the same file fetched pinned to commit `cd95042`. Two independent routes, same bytes.

Record counts at `30e3369`, as a smoke test for any future clone — rosters 2004/2007/2010/2013/2017 at 3023/3165/3219/3549/3525 records, 52 keys each; staff at 453/453/443/453/453 records, 72 keys each.

**Two routes that do not work, so nobody re-tries them:**

- **The GitHub API** (`api.github.com/repos/.../commits?path=...`) resolves the current SHA correctly, but is rate-limited by IP on shared infrastructure and returned HTTP 403 within minutes of first use. Not dependable.
- **Cache-busting the raw URL** with a random query string appeared to return current content, but there is no way to tell "defeated the cache" from "the cache happened to be warm and correct". Unproven — don't rely on it.

A clone is current as of the moment it runs; if Ryan pushes mid-session, re-clone. When a cross-file comparison produces a surprising result, **suspect a stale copy before suspecting a bug** — and say which commit you're holding when you report a finding.

**Related discipline, learned the hard way on 2026-08-28: run `pgm3_validate.py` before every push, with the file checked against the other four.** A rebuild of `potential` shipped without rebuilding the `growthType` that depends on it, breaking all five files that had been clean. Every check that was run passed, because both fields were individually plausible — the defect lived in the rule connecting them. The validator catches exactly this and takes seconds. It was not run.

---

## Critical: what counts as authoritative

**There is now a real game export.** `PGM3_SCHEMA_REFERENCE.json` has a `VANILLA_authoritative` section built from a fresh PGM3 league the game generated itself — no custom rosters, no games played. **Where it disagrees with the donor or with our built files, it wins on questions of what the game does.** For value *ranges*, still prefer the union of built files; the vanilla export is a single league and a narrower sample.

It has already overturned two rules that came from the donor:
- **The 50× `growthType` rule applies to draft prospects only in a game-generated league.** Vanilla rookies obey it 69%; rostered players and free agents obey it 0%. **All four published files enforce it at 100% in every cohort**, which is tighter than the game requires — inherited from the donor. New builds should match the published files for consistency, not chase the vanilla behaviour, because the veteran career-arc mechanic (positive sums around 400) isn't understood well enough to reproduce per player. If that ever changes, it should change all files at once. For veterans the curve is a full career arc whose positive portion has already been partly consumed. Our built files enforce it on everyone — inherited from the donor, which did the same. Not corrected in the shipped files (they play fine and the mechanic isn't understood), but **build new files the vanilla way**.
- **Staff `startSeason` has a real spread tracking age** — 1988–2024, correlation −0.972, `startSeason ≈ −0.963 × age + 2059.6`. Flat 2026 is wrong. 2010 and 2017 were flattened by mistake and have been restored.

That's the cost of treating a user's file as a reference: their conventions get inherited as though they were the game's.

---

## Older note: the donor files

There is a donor file in uploads (`PGMRoster2025-06-12_3.json` / `PGMStaff2025-06-12.json`). **It is another user's roster, not a developer file.** It is evidence about what the game *accepts* — schema, field names, value ranges, vocabulary — not about what is *correct*.

Do not say "the game requires X" based on the donor. Say "this matches the working files." The only real authority is:
- Does it load without crashing
- What the person observes in play

The 2010 and 2017 files are known-good because they've been played extensively. Use them as the reference range for anything new.

**The game can also export the roster currently loaded** (option in settings). That export is the closest thing to ground truth available — it's the file after the game has read, validated, and played with it. Useful for capturing avatar edits, and for seeing what the game does to a file on import (it regenerates all `iden` values, for instance).

---

## Run the validation suite first

`pgm3_validate.py` is in the project files. It encodes every check below plus everything else this project has learned.

    python3 pgm3_validate.py roster NEW.json REF1.json REF2.json
    python3 pgm3_validate.py staff  NEW.json REF1.json REF2.json

Plus a cross-season face pass, which takes a whole set of files rather than one:

    python3 pgm3_validate.py faces PGMRoster_2004.json PGMRoster_2007.json ...
    python3 pgm3_validate.py faces --staff PGMStaff_2004.json PGMStaff_2007.json ...

Seven checks, each of which exists because the bug happened on 2026-08-31:
head/nose/mouth share a family digit; players wear `Glasses1e`; head family
constant per person across seasons; hair style constant; **the aging variant
still varies** (a collapse means a pass wrote whole registry faces instead of
rewriting only the family digit); **verified faces intact** (catches a hand edit
being overwritten); and head-family distribution comparable across files — the
check that would have caught 1986.

Run it after step 8 and before any push. On the files published that morning it
found 14 overwritten hand edits in seconds; they had been found by accident days
of work later.

Pass **all** known-good files as references — ranges are measured against their union, never a single file. Exit code 0 means clean.

Two things it handles that a naive check gets wrong: position-specific attributes are compared only among the positions that use them, and money fields are skipped because they legitimately differ by era.

`PGM3_PRECEDENTS.md` holds the judgment calls already made. Follow them or make the case for changing one; don't quietly diverge.

---

## The validation method that actually finds bugs

Structural validation (types, ranges, required fields) passes on broken files. Two techniques have found nearly every real bug:

### 1. Zero-pattern comparison
For every field, compare the *proportion of zero values* in the new file against the working files. A field that is never zero in 2010/2017 but all-zero in the new file is a bug — even though zero is technically in range.

**This found:** all 31 staff specialty attributes missing (caused a crash), `management`/`motivation` at zero for all 453 staff, `guarantee`/`eGuarantee` missing.

### 2. Cross-year field comparison by cohort
For every numeric field, compare min/median/max across all three years, split by cohort (rostered / free agent / draft prospect). Flag anything where one year is a clear outlier.

**This found:** 2004 stamina median 25 vs 81–86 (source scale mismatch — 87% of players would have gassed out), 2010 rookie stamina all zero, 2004 jumping ~20 points low.

### 3. Conditional distribution — check against the SOURCE value
The single most productive check in this project. For any field derived from a source, **split the output by the source value and compare the groups.** A field that is pure noise still produces a perfectly reasonable overall distribution; it only fails when you condition on what it was supposed to be derived from.

Three separate bugs shipped past every distribution check and were caught only this way:
- **Stamina** in 2004 — correct median 83, correlation 0.116 with the real source. The wrong Madden field was read, then rescaled to look right
- **Attributes from percentiles** — a plausible spread per position, MAE 8.52 against 2.35 for using real adjacent-year values
- **Appearances** in 2007 — a name-seeded face generator gives a sensible mix of skin tones. Split by Madden `PSKI` and all three source groups looked identical

The test: group output by source value, compare the groups. If they look the same, the field is noise no matter how good the overall shape is.

### 3. Condition on the source value, not the overall distribution
**This is the check that catches the hardest class of bug**, and it has now caught three:

- **stamina** — read from `PSTM` instead of `PSTA`. Correct median after rescaling, correlation 0.116 with the real field.
- **percentile-filled attributes** — a sensible spread per position, MAE 8.52 against real adjacent-year data.
- **appearances** — a face generator seeded on a name hash. Perfectly reasonable spread of skin tones.

None of these failed a distribution check, because none of them had a wrong distribution. They had *no relationship to the source*. The test is to split the output by the source value and see whether the groups differ:

    for each value of the source field (e.g. Madden PSKI 0/1/2):
        what does the output distribution look like?
    if all groups look the same, the source was never used

A correct mapping shows clean separation — PSKI 0 landing in skin families 1–3, PSKI 2 in 4–5. A dead field shows every group looking identical.

This can't be automated in `pgm3_validate.py` because it needs the source file, so run it by hand whenever a field is supposed to derive from something.

**Always compare cohort to cohort and position to position.** Measuring across a whole file produces false signals: the working files' `Rookie` bucket is a future draft pool rated as low as 40, and including it made 2010 and 2017 look like they disagreed wildly (sd 13.8 vs 8.4) when excluding it showed them nearly identical (both median 70, mean 70.7).

Important refinement: position-specific attributes (QB accuracy, kick accuracy, coverage) look all-zero when measured across the whole pool because most players legitimately have zero. **Check them only among the positions that use them** before declaring a bug.

---

## Bugs found, and what to check for in future builds

| Bug | How it happened | Check for it |
|---|---|---|
| **Staff specialty attributes all zero** | Built records with `{k:0 for k in schema}` then only filled fields I was thinking about | Zero-pattern comparison against working files. Every role carries ~31 specialty fields |
| **Coaches missing 3 of 4 coaching attrs** | Only set each coach's primary (`DCcoach` for a DC) | In working files every coach has `HCcoach`, `OCcoach`, `DCcoach`, `STcoach` — all non-zero. Same for scouts (`Hscout`/`Oscout`/`Dscout`) and physios |
| **Staff salaries compressed** | Invented formula (`rating² × 80`) instead of fitting from working files | Fit per role from 2010/2017. Range should be ~$150K–$5.7M, exponential in rating |
| **draftSeason compression** | Clamped floor at 2022, piling 872 players onto one year | Veterans should span ~2007–2026. Brett Favre should read ~13 years experience, not 4 |
| **Fullbacks rated as elite RBs** | Madden grades FB on blocking, then position collapses into RB | Any position collapse where the source grades on different criteria. Run implied ratings through the *target* position's formula, don't trust source overall |
| **Player renamed between eras** | PFR uses current names; period Madden uses the name he had that season | Silent match failure, no error — the player just falls through to a fallback. Nickell Robey-Coleman was Nickell Robey in 2013; Will Compton is William Compton on PFR; Trenton Robinson is Trent Robinson. A hyphenated-surname retry catches some, first-name variants need a manual pass. **Scan the unmatched list for names that look almost right** before assuming a player is absent |
| **Name collisions — state this as a principle, not a list** | Every build has found new instances in new places | **A disambiguator has to be a field the collision does not share.** Position works when two players have different roles and fails when they don't — two linebackers named C.J. Mosley need something else, and for a draft prospect the drafting team is unique by construction. Pick the field that actually separates the specific collision rather than reaching for position by habit.

**Any lookup keyed on a player name is a bug until it is disambiguated.** Not just the roster join — the ratings backfill, the corrections delta, the appearance library, the fullback cohort. Cascade: name+team+position, then name+position, then name-only *only when the name is unique in that file*. And position is a **tiebreaker, not a filter** — an over-strict guard drops real players who changed position between years (Julius Peppers DE→OLB, Dan Klecko DT→FB, Lorenzo Alexander LB→DT). The 2013 build hit three of these in places the rule as previously written didn't cover |
| **Namesake collisions (instances)** | Matched on name only | Steve Smith (2007 NYG rookie vs Carolina star), Alex Smith (2005 QB #1 and TE #71), Derrick Johnson (LB #15, CB #205), Adrian Peterson (two real players). Match on name + team + position |
| **"HOF" in surnames** | PFR appends "HOF" to Hall of Famers in draft tables | Strip before splitting names. **This recurred:** the published 2010 file shipped "Luke Kuechly HOF" as a surname, caught 2026-08-28 during the potential rebuild. It also silently broke his face-registry lookup, since the key is built from the name. New Hall of Fame inductions add new names every year, so re-check this on any rebuild rather than assuming a past pass caught them all |
| **Same player on two teams** | PFR lists mid-season movers on both teams' pages | 70 duplicates in 2010. Dedupe on name+position, keep the team with more games/better rating |
| **Coach schemes generic** | Drew from donor distribution instead of real identities | Every coach on a team should share that team's real scheme |
| **Real names as invented filler** | Name generator collided with real coaches | 28 scout/physio slots in 2010 had real coach names (Sean McVay, Adam Gase, Chuck Pagano). Check invented names against all real coach names across all files |
| **Madden rating scale drift** | PS2-era Madden (03–09) runs inflated: median 77–80, 12–23% at 90+. Madden 10+ is modern scale: median 71 | Rescale to match working files, **position by position** — a cohort-wide rescale put punters and kickers at the top of the league |
| **PFR generic position labels** | PFR labels many players `DB`, `LB`, `OL`, `DL` rather than the specific position. Mapping all `DB` to CB starved safeties on 29 of 32 teams | Resolve generic labels through Madden's position, which is specific. Check the CB/S ratio against the working files — they run 1.06–1.30. Also handle `PR`/`KR` (map to WR) and hyphenated labels like `RB-TE` |
| **Contract lengths too short for young players** | Took Madden's contract-length field at face value; it doesn't mean remaining years | Working files show a rookie ladder: drafted this year = 4 years left, then 3, 2, 1. Almost no young player should have an expiring deal. 2004 had 26% of actual rookies expiring. **Symptom in play: the game blocks contract extensions**, saying you can't negotiate until the final year of a rookie deal. Check median `length` bucketed by (2026 − draftSeason) against the working files |

---

## PGM3 file format rules

### Roster records
- **`teamID` uses MODERN team IDs for every season, regardless of where the franchise played that year.** The fixed set is: ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS, plus `Rookie` and `Free Agent`. So the 2004 San Diego Chargers are `LAC`, the 2004 St. Louis Rams are `LAR`, and the 2004 Oakland Raiders are `LV`. Using period-correct IDs (SD, STL, OAK) breaks those three teams on import. All three published files follow this; verify it early in any new build
- Schema must exactly match the working files (52 keys). Copy key set from `PGMRoster_2017.json`
- `iden` — uppercase UUID, unique within file
- `growthType` — **31 elements** for players. Sum of positive values must equal `(potential - rating) × 50` exactly. Correlation checks are not sufficient
- `draftNum` — **real pick number for everyone**. Prospects carry their actual slot; rostered and free agent players carry their real pick, with **224 as the undrafted floor**. No file uses 0 or −1 anywhere. Verified across all four
- `draftSeason` — game's internal clock has current season = **2026**. Historical builds offset by (2026 − season year). Prospects land 2027–2030
- Rosters run 53–69 per team. The game flags anything over 53 but all three files ship this way — built from everyone who played that season
- Cap ceiling ~$280M; no team should exceed it
- `length` — remaining contract years. **Two constraints, both required.** (1) It must be consistent with `draftSeason`: a recently drafted player is still on a rookie deal and the game will refuse extensions if `length` says otherwise — the ladder runs 4, 3, 2, 1 by years pro. (2) The overall distribution is heavily weighted short: ~34–39% of rostered players are on 1-year deals, and nothing exceeds 7. Fit both, not just the ladder. Rostered players need `length ≥ 1`; free agents need `length = 0`. Distributions for both are in `PGM3_SCHEMA_REFERENCE.json`
- `eLength` — years on the expected/next contract. Working-file range is 0–4

### Staff records
- Staff contract fields are **role-specific, not pooled**. But **amended 2026-08-31: the pooled figure is also the wrong target for `eGuarantee`, and the "head-coach-only, 33%/0%" reading appears to have been measured on 2010 alone.** Per file, `eGuarantee` non-zero rates are four incompatible behaviours: 2004, 2017 and 2021 are flat zero across all nine roles; 2010 is 100% for head coaches and 0% for the other eight; 2013 runs 31–62% throughout; 1986 and 2007 are low and scattered. **2010 is also HC-only for `guarantee`, which no other file is** — so the documented shape is 2010's, not the archive's. **Ruling: ship staff `eGuarantee` at ZERO.** It matches the plurality, it is internally consistent rather than an average of incompatible files, and `eGuarantee` is game-computed and overwritten on import anyway. **`guarantee` is different and should be fitted per role** — it is non-zero in 28–100% of every role in six of seven files, with only 2010 zeroing the non-HC roles. Fitting a pooled rate across all roles still produces a field that looks plausible and is wrong
- **Observed range is not accepted range.** The min/max derived from three files describes what those files happen to contain, not what the game accepts. Lane Kiffin was genuinely 32 in 2007 and Josh McDaniels 31, both below the observed staff floor. Keep real values rather than clamping to a range you derived yourself — if the game rejects it, import will say so immediately
- `growthType` — **51 elements** for staff (not 31). **The 50× rule applies to draft prospects only** (see the authoritative section above — vanilla veterans obey it 0% of the time). Our built files enforce it everywhere and pass validation on that basis: positive values must sum to exactly `(potential − rating) × 50`, same as roster players. An earlier version of this document said the rule didn't apply to staff — that was wrong, derived from misreading the donor's 90% compliance as evidence of no rule. All three staff files now obey it at 100%. Curve shape: positives in slots 0–16, negatives in slots 20–50 (always multiples of 100), slots 17–19 always zero
- `startSeason` — must be 1989–2026
- Primary attribute must equal `rating` (`HCcoach` for a head coach, `Hscout` for head scout, etc.)
- Every coach carries all four coaching attrs; scouts carry all three scout attrs; physios carry both physio attrs
- 9 staff per team: HC, OC, DC, ST, Head Scout, Off Scout, Def Scout, Head Physio, Assistant Physio
- `scoutBoost` — Off Scout gets offensive positions only, Def Scout defensive only, Head Scout either
- **Special teams coaches:** `offStyle`/`defStyle` are unused placeholders for this role. The meaningful field is `fourthStyle` (Cautious/Balanced/Aggressive). Don't assign them team schemes
- Scouts and physios also carry scheme-style fields, but they appear to be placeholders

### Appearance (9-element array)
- Slots 0, 5, 6 (Head, Nose, Mouth) — must share the same family digit
- Slots 2, 3, 4 (Hair, Beard, Eyebrows) — must share the same family digit (separate group)
- Slot 7 (Glasses) — players always `Glasses1e` (none); staff can wear glasses
- All tokens must exist in the appearance vocabulary in `PGM3_SCHEMA_REFERENCE.json`. **Note: the raw donor contains one corrupted record** (surname "4", `#N/A` in slots 0/5/6). `#N/A` is never valid. The schema reference has it filtered out; if you ever re-derive the vocabulary from the raw donor, filter it again
- **Duplicate appearances are FINE.** The game's own export has 12 duplicates in 3,313 records and the donor has 183 in 4,036. Uniqueness was a self-imposed rule, stricter than the game requires. Never alter a player's face just to break a tie — especially not one the person hand-edited
- Beard letters: a=mustache, d=goatee, e=full beard, g=clean shaven

---

## Rating mechanics

**The game recomputes overall from attributes.** The stored `rating` field is display only. Changing a rating without refitting attributes does nothing in-game.

`weights.json` holds per-position linear coefficients fitted from the donor file. **It was lost once in a container reset and had to be refit** — the current version reproduces all three files with median error under 1 point, but it's a reconstruction, not the original. It's included in the build data bundle; preserve it.

Refit procedure: solve attributes toward a target rating, bounded by the min/max observed in working files, iterating until error < 0.4.

---

## Build order

Follow this sequence. It exists because deviating from it has cost real time.

1. **Parse sources and resolve positions.** Generic PFR labels (`DB`/`LB`/`OL`/`DL`) through Madden's position. Handle `PR`/`KR` and hyphenated labels. Check the CB/S ratio against the reference files before moving on.
2. **Appearances.** Do these *early*, not last. They are a direct field copy from `PSKI`/`PHCL` plus the appearance library — the cheapest thing in the build to get right, and the easiest to forget. Three of four files shipped with random faces and had to be fixed afterwards. **Run the conditional check the moment they're built** (see below).
3. **Ratings** — rescale per position and per cohort.
4. **Attributes** — direct map, then percentile fill, then bounded refit.
5. **Contracts, growth curves, identity fields.**
6. **Staff.**
7. **Draft classes.**
8. **Apply the face registry** — `PGM3_FACE_REGISTRY.json` over the top of everything. This is where Ryan's hand edits live and it must run after any bulk appearance work, never before.
   - **Apply the family digit, never the whole face.** Slots 0, 5 and 6 carry a family digit and a variant letter; the variant is derived from age and weight and **legitimately differs between seasons**. Writing the registry array wholesale flattens the aging. Rewrite the digit and keep the season's own letter. Staff are the exception — coaches have one look and no aging, so the whole array is correct for them.
   - **Rebuild every season the registry touches**, not just the ones you're working on, or players end up inconsistent either side of the boundary.
   - **`_verified_keys` is locked.** Anything Ryan set by hand, player or coach, is never overwritten by any pass regardless of how the source scores. A pass that disagrees skips and logs. See `PGM3_VERIFIED_FACES.md`.
9. **Validation** — `pgm3_validate.py roster`, then `faces`, then the conditional pass.

### The conditional pass — mandatory before a file is called finished

For **every field that derives from a source**, split the output by the source value and confirm the groups differ. Not the overall distribution — the distribution *conditioned on the source*.

    for each distinct value of the source field:
        summarise the output for that group
    if every group looks alike, the source was never used

Fields to check, at minimum:
- `stamina` against `PSTA` (not `PSTM`)
- `appearance` skin family against `PSKI`, hair against `PHCL`
- every direct-mapped attribute against its Madden column
- `rating` against source overall
- `guarantee` against remaining `length`
- staff ratings against the unit performance they came from

This has caught three bugs that passed every other check: stamina reading a dead field, percentile-filled attributes, and a name-hash face generator. All three had *correct-looking distributions*. That is exactly why a distribution check misses them.

The suite has a command for it:

    python3 pgm3_validate.py conditional NEW.json SRC.csv OUT_FIELD SRC_FIELD

    python3 pgm3_validate.py conditional PGMRoster_2007.json 2007_-_PLAY.csv stamina PSTA
    python3 pgm3_validate.py conditional PGMRoster_2007.json 2007_-_PLAY.csv appearance PSKI

It buckets continuous sources into deciles, handles the appearance array by reading the skin family digit, and matches on normalized name. A healthy result shows clear separation — stamina rising from 1 to 92 across `PSTA` deciles, or `PSKI` 0 landing 47/24/26 across skin families 1–3 while `PSKI` 2 lands 30/66 in families 4–5. A dead field shows every group looking alike.

Report the output alongside the validator result.

---

## Starting a new season — the shopping list

Give the person this list up front. Everything else in the build follows from it.

**1. PFR pages — two per team plus four draft pages.** Team codes:

    crd atl rav buf car chi cin cle dal den det gnb htx clt
    jax kan mia min nwe nor nyg nyj rai phi pit sdg sfo sea
    ram tam oti was

    https://www.pro-football-reference.com/teams/{code}/{YEAR}.htm         (coordinators, draft info)
    https://www.pro-football-reference.com/teams/{code}/{YEAR}_roster.htm  (the player list)
    https://www.pro-football-reference.com/years/{YEAR+1..YEAR+4}/draft.htm

Save as "Webpage, HTML Only". Give them the `open -a "Google Chrome" <urls>` command in batches of 16 — 68 pages is a lot of clicking otherwise. PFR wraps tables in HTML comments; strip `<!--` and `-->` before parsing.

**2. Madden ratings.** `https://www.maddenratings.net/madden-nfl-{NN}.html` where NN is the season year + 1 (Madden 14 = 2013 season, Madden 22 = 2021). Per-team `.xlsx`, sometimes one combined file for recent years. **Also grab the next three years' files** — they supply rookie ratings for the draft classes.

**3. Contracts.** Best is a disc `PLAY` table CSV for that season, exported with Xtreme DB Editor. If none exists, Over The Cap or Spotrac historical cap numbers. The maddenratings spreadsheets carry no contract fields at all.

**4. A schemes document** for all 32 teams — head coach, both coordinators, special teams, offensive scheme, base defense, coverage lean. Ask another AI with an instruction to say "uncertain" rather than guess. This has worked every time.

**5. Career records** for all 32 head coaches through the *prior* season, plus coordinator birth years. Same approach.

**6. Special teams rankings.** Gosselin published through 2023 — `rickgosselin.com`, searchable by year. 2024+ is Bill Huber's Packers On SI rankings, published as a chart image the person has to read out.

**Known status for the likely next builds:**
- **2013** — Madden 14 covers it. Gosselin published. A `2013_-_miner69_-_PLAY.csv` exists in uploads but it is a **community roster with a broken skin field** — usable for ratings, not for appearances.
- **2021** — Madden 22 covers it. Gosselin published. Contracts should be on Over The Cap.

**Appearances:** build from disc CSV `PSKI`/`PHCL` where available, and fill the rest from the appearance library built out of the finished rosters. Every completed season makes that library better.

---

## Data sources by type

| Need | Source |
|---|---|
| Historical rosters | Pro Football Reference season roster pages |
| Player ratings/attributes | maddenratings.net — per-team `.xlsx` per year, or one combined file for recent years |
| Historical contracts | Madden disc `PLAY` table CSV (`PTSA` field is **total contract value** — divide by `PCON` for annual) |
| Coach records | PFR individual coach pages (`coaching_ranks` + `coaching_results` tables). **The season coaches index gives lifetime totals — inflated for historical builds. Use individual pages.** See the worked instance below; do not re-try the index |
| Coordinator performance | PFR season pages, unit rank in points and yards |
| Special teams | Gosselin's rankings **through 2023 only — he stopped**. 2024+ successor: Bill Huber's Packers On SI annual rankings (published as a chart image; ask the person to read it) |
| Career records, coordinator units, special teams — what is and is not computable | see the two notes immediately below |
| Draft classes | PFR draft listing pages — includes career AV, Pro Bowls, All-Pros, years started |

**The PFR season coaches index is CONFIRMED UNUSABLE for career records. Do not
re-try it.** Verified on the 1999 index, 2026-08-31. It carries three columns and
none of them is "career through this season":

| column | Andy Reid on the 1999 page | what it actually is |
|---|---|---|
| season | 16 G, 5–11 | correct — his rookie year |
| w/ Team | 224 G, 130–93 | his **entire** 1999–2012 Philadelphia run |
| Career | 437 G, 279–157 | his record **through 2025** |

Reid had coached exactly 16 games when the 2000 season began; the page says 437.
Cowher's "w/ Team" 240 games is all of 1992–2006 the same way. The only usable
column is the single season — **which is precisely the figure the rating rule
forbids**, and the one that rated Reid 71 off a bad year.

Routes that do work: individual PFR coach pages, or summing seasons of the index
across the years before the build year (~19 fetches for a 2000 build, and it
yields a reusable career-record table since coordinator ratings and the
free-agent coach pool need the same data).

**Team unit ranks for coordinators ARE computable without PFR.** nflverse
`games.csv` carries every game result back to 1922 — points for and against per
team-season, which gives offensive and defensive ranks directly. Verified for
2000: St. Louis 540 points scored, Baltimore 165 allowed, 31 teams at 16 games
each. **Its `home_coach`/`away_coach` fields only begin in 1999**, so it cannot
supply career records, only current-season units.

**`norm()` must PRESERVE generational suffixes on any build reaching back more
than ~20 years.** The documented rule — strip `Jr/Sr/II/III/IV/V` and collapse
initials — is correct *within* an era, where it matches a player to himself
across files that spell him differently. It is actively harmful *across* eras,
because it collapses fathers and sons into one key.

**Measured, 1986 session.** The face registry was matched against the 1986 cohort
on `name + position`, the registry's own key. 16 matches. **Only 3 were the same
person** — Doug Flutie, Jerry Rice and Ray Brown, all of whom played into the
published seasons. **Nine were cross-era namesakes at the same position**, which
position cannot separate: Clay Matthews (father OLB 1978–96 / Matthews III OLB
2009–19), Kellen Winslow (father TE / Winslow II TE), Mickey Shuler (father TE /
Shuler Jr TE), Mark Clayton, Eric Wright, Mike Richardson, Mark Brown. Four
unverified. Reading the registry would have put the son's face on the father in
at least nine cases.

Winslow and Shuler collide because `norm()` strips the suffix — but note the
asymmetry: **the 1986 file spells them "Kellen Winslow" and "Mickey Shuler" with
no suffix, because in 1986 they were the only ones.** The suffix is not being
stripped from the older data; it was never there. It is the *later* file that
carries "II"/"Jr", and `norm()` removes it. So "preserve generational suffixes"
only helps when both sides have them, and across a generational gap only one side
does. **The real fix is era (and team) in the key**, not suffix handling.

**The namesake false-match rate scales with the gap between seasons.** Name-only
gave 4% apparent overlap; name+position gave 0.9%; genuinely-same-person is
**0.17%**. So 71% of the apparent overlap was false on position alone, and ~81%
of what survived position was still false. Any build reaching further back should
expect worse, and should not treat a name+position match as sufficient evidence
of identity across a generational gap.

**Era is the missing discriminator and the registry has no field for it.** Hence
`faces_1986` as a separate top-level block rather than additions to `faces` — see
below.

**UNCONDITIONAL: any operation that writes keyed records asserts the count.**

```python
assert len(output) == len(input), f'{len(input)} in, {len(output)} out — key collision'
```

Silent overwrite is invisible to every other check. No distribution check, no
constraint check, no zero-pattern comparison and no amount of eyeballing detects
it, because the output is internally consistent — just short. The 1986 face
registry write produced **1,745 entries from 1,746 players** and raised nothing;
the cause was two different James Joneses, both RB, both in 1986. The same one
line would have caught the `PYRP` repair that edited two Doug Smiths and the
earlier registry rebuild.

Corollary for keys: **a key needs enough fields to be unique in the widest
population it will ever be queried against.** A registry is queried across every
season that exists, so `name|position` was never sufficient — it simply had not
yet met a population where it fails. Use `name|position|teamID`, plus era scoping
for cross-era blocks.

**`teamNum` (jersey) is IN the Madden source — do not generate it.** `PJEN`
carries real jersey numbers and follows era conventions exactly: QB/K/P 1–19,
RB/CB/S 20–49, C/OG/OT 50–79, TE/WR 80s, DE/DT 60–99. Verified on the 1986 file
by position medians. Published `teamNum` is 0 for free agents and prospects and
non-zero for every rostered player, with **zero duplicates within a team-season
across all 11,737 rostered players** — that is a hard convention, so de-duplicate
after import (resolve in favour of the more experienced player, moving the junior
one within his position's number range). Note that a per-position number range
table derived from convention is *stricter* than the game requires: the published
files sit outside such a table 14.2% of the time, so do not treat range
violations as defects.

**Madden PLAY CSVs are named by SEASON, not by game year.** `2007_-_PLAY.csv` is the 2007 season. Verify by checking whether that year's rookies are present with `PYRP` 0.

**A post-season Madden update is a better source than the launch roster.** It rates players on what they actually did that year. But it only pushes breakouts *up* — publishers never demote established veterans mid-season. So "up" corrections are usually already baked in and "down" corrections are still needed. Check both directions rather than assuming.

**Contract fields:** `PTSA` is total contract value, `PCON` is length, `PSBO` is signing bonus. `PSBO` is a *component of* `PTSA`, not an addition — adding them double-counts. `PSBO` does **not** map straight to `guarantee` — see the contracts section for the length-decay formula. Verify annualization against two or three published contracts before scaling anything.

**Madden disc `DB_TEAMS.DAT` contains one database block per team**, each with its own PLAY table of ~53 players. Xtreme DB Editor opens only the first block, which looks like a one-team file. There is no filter to find. The full-league PLAY CSVs came from a different `.DAT`.

**Madden spreadsheet layouts vary and some are traps.** Madden 12's per-team sheets are **per-position blocks**, each with its own header row and column set — a flat read applies the QB columns to everyone and gives every lineman a Throw Accuracy Deep rating. Madden 11's Minnesota file is effectively **empty**: 52 of 54 players have an overall and nothing else. Madden 10 carries only 9 columns. Always inspect a sheet's structure before parsing it.

**Madden year → season mapping:** Madden NFL 06 covers the 2005 season. So the 2005 draft class gets rookie ratings from Madden 06. Madden 27 covers 2026.

Column names differ every year (`First_Name` vs `FIRSTNAME` vs `First`). Always inspect before parsing. One Madden 11 file has a line break inside a header.

---

## How ratings get built

**Players:** Madden overall → rescaled per position to match working-file distribution → attributes refit to hit the new rating.

**Draft prospects — rating:** rookie-year Madden ratings where available; otherwise derived from draft position.

**Draft prospects — potential:** per-position slot baseline from log(pick), plus a career-achievement raise. Rebuilt across all five files 2026-08-28; the full method and its coefficients are in `PGM3_PRECEDENTS.md`. The career inputs come from PFR draft pages (`all_pros_first_team` as a **count**, `pro_bowls`, `years_as_primary_starter`, `career_av`) plus an MVP/DPOY/OPOY list. **PFR access is per-transport, not per-site. Retested across four clients on 2026-08-31 — do not test it a fifth time.**

| transport | result |
|---|---|
| master session `web_fetch` | **works** — `/years/1986/index.htm` returns full standings, W-L-T, PF, PA, OSRS/DSRS |
| Claude Code `WebFetch` (build session) | **403** |
| `curl`, plain or with a browser User-Agent | **403** |
| in-app browser | **Cloudflare "Performing security verification"** interstitial |

Six URLs across those four transports were tested on 2026-08-31: `/years/1986/index.htm`, three `teams/{code}/2000.htm` pages and two others. Only the master session's `web_fetch` succeeded.

**Consequence for a build session: PFR is blocked.** Route PFR pulls through the master session, or use Wikipedia season pages and nflverse, which is how the 31 coaching staffs in `sources/coaches_2000.csv` were actually researched — 122 of its 124 rows carry Wikipedia URLs. The Cloudflare interstitial is bot detection and is not something to work around.

Two earlier versions of this note each stated half of the table as the whole truth, and each was then cited to contradict the other. The 1986 amendment was right that the original finding "was about one client, not the site" — it just drew the boundary in the wrong place, and a build session inherited "PFR works" and lost time to 403s.

Caveat that still applies wherever a fetch does succeed: PFR wraps most tables in HTML comments, so a fetch returns the section headings with no rows under them — strip `<!--` and `-->` before parsing. Standings tables are not comment-wrapped and come through directly.

**Potential is raise-only.** Draft position sets the baseline; career outcomes — career AV, Pro Bowls, All-Pros, years started — pull it *up* for players who exceeded their slot, and never pull it down. Verified across all three published files: no first-round pick in any of them has potential below 70, and pick dominates the fit (corr −0.68 to −0.79 against log pick).

An earlier version of this document said "busts are busts." That was wrong — no file has ever done it, and the raise-only behaviour is correct on its own terms. **Potential is a ceiling, not an outcome.** A bust is a player who had the ceiling and didn't reach it; lowering his potential conflates ceiling with achievement and bakes hindsight into innate ability. It also preserves the interesting half of the draft — late-round hits stay findable (Jamaal Charles at pick 73, Carl Nicks at 164) while you aren't punished for a pick a real GM couldn't have called. For future classes this is impossible; potential has to come from scouting projection instead.

**Head coaches:** career record through the prior season, regressed toward .500 for small samples, plus bonuses for Super Bowls, playoff wins, Coach of the Year. **Do not use single-season records** — that rated Andy Reid 71 off one bad year.

**Coach of the Year bonuses count AP awards ONLY** (ruling, 2026-08-31). A clean
comparable standard, and the 2000 build records what it costs: **Bobby Ross**
(1992 PFWA/UPI/Greasy Neale), **Tom Coughlin** (1996 UPI), **Dave Wannstedt**
(1994 UPI) and **Dennis Green** (1992 UPI, 1998 Greasy Neale) all carry zero
despite winning a Coach of the Year award in this era. Those four are the line a
later session "fixes" by adding the other voting bodies. The convention is
deliberate — do not widen it without a ruling, and if it ever is widened, every
season has to be rebuilt together or the files stop being comparable.

**Coordinators and special teams: rate them on the season being built, not the prior one.** 2004 used its own 2004 unit ranks and Gosselin's 2004 rankings; 2007 used 2007. **The prior season is only correct for a current-season build** where the season hasn't been played — that's why 2026 used 2025. Applying the 2026 rule to a historical build is an error and it happened once.

Distinguish play-callers from title-holders — a coordinator who didn't call plays gets partial credit.

**Head coaches are the exception:** their career record runs *through* the prior season, since the season being built hasn't happened from their perspective at hiring time.

**Special teams:** published all-32 rankings.

**Scouts and physios:** no public data exists for any year. Invented, but fitted to working-file distributions.

---

## Contracts: guarantee, ceilings, and payroll basis

**Quote payroll on a stated basis.** Salary-only and salary+guarantee are very different numbers and mixing them produces false comparisons:

| | salary only | salary + guarantee | real NFL cap |
|---|---|---|---|
| 2004 | $179M | $220M | $80.6M |
| 2010 | $161M | $226M | uncapped year |
| 2017 | $153M | $248M | $167M |

**`guarantee` tracks REMAINING length, not the original signing bonus.** It's money still owed, decreasing as a deal runs down. Ratio to salary runs 0.00–0.08 for a player in his final year and 0.47–1.67 at five years remaining. Mapping Madden's `PSBO` straight across is wrong — that's the full original bonus, so a player four years into a five-year deal carries it as though none had been paid. Use `guarantee = PSBO × (length ÷ PCON)`.

**There is no contract ceiling. Tested, not assumed.** On 2026-08-28 a throwaway league was imported with salaries of $45M, $60M and $75M. All three loaded, displayed correctly, and fed the game's own arithmetic — a $45M salary produced a $50.7M cap hit and $31.3M dead cap. Nothing clamped, nothing rejected.

The figures long treated as hard caps — $27,600,000 salary, $34,100,000 eSalary, $40,900,000 eGuarantee — were **the donor file's highest-paid player at each field**, one record each, inherited through five builds and then written into this document as a limit. Five files agreeing to the dollar meant a shared ancestor, not a wall. Vanilla's $30M was the same artifact from a different league.

**Consequence: 2026 ships real modern contracts with no compression.** The `LIMITS` values in `pgm3_validate.py` are now sanity guards set far above anything real, not caps, and remain overridable per build with `--salary=`, `--eSalary=`, `--eGuarantee=`.

**Round-trip confirmed 2026-08-28.** An export taken after importing the test league returned **salary, guarantee and length identical for all 3,023 matched players**, including the $45M/$60M/$75M contracts. The game stores authored salaries and hands them back unchanged.

**`eSalary` and `eGuarantee` are game-computed OUTPUTS, not inputs — do not fit them.** The same export rewrote them for everyone: only 35% of `eSalary` and 51% of `eGuarantee` values survived, and **565 players authored at eGuarantee 0 came back with nonzero figures**. Warren's test value of $50M returning as $7M was not clamping — it was the same regeneration every player got. In the export these fields track rating cleanly (median `eSalary` $600K at ratings 40–60, $3.3M at 70–80, $7.7M at 80–90), so the game derives them from player value. That is also why no screen displays them: they are internal working values driving extension demands. `eLength` behaves the same way (51% survival), and `rating` likewise at 41%, independently confirming that the game recomputes overall from attributes.

**Build consequence: ship sane values so the file is valid on first load, then stop.** Time spent fitting `eSalary`, `eGuarantee` or `eLength` for players is discarded by the game. (This is about the *player* file — the staff role-specific `eGuarantee` finding is separate and untested.)

Caveat on the test: one player's age changed between import and export, so a small amount of game time passed. Not enough to explain a 65% rewrite of `eSalary`, but it is not a perfectly clean round trip. The salary result is unaffected — 100% identical is 100% identical.

**Team payroll cap is a parameter, not a constant.** It is the real NFL cap for the season being built and moves every year — 2026 is $301.2M. The old hardcoded $280M was stale. Pass `--team_cap=` explicitly for any build. Note the check measures salary+guarantee, which the published files already exceed by design, so it is a sanity guard rather than a true cap check.

**On era scaling:** the published files are not scaled to their seasons — 2004 runs $179M salary against a real $80.6M cap. That's a defect nobody noticed rather than a convention. New builds should ship real numbers; don't inflate accurate data to match.

---

## Free agent coaching pools

Rule: **real coaches form a clean top block; invented names sit strictly below all of them.** Invented names must not be interspersed among or above real ones.

Also: invented names must not accidentally be real people. Check generated names against every real coach name across all files.

2010's pool is entirely real (27 coaches). 2004 has 15 real + 6 invented. 2017 has 10 real + 23 invented.

---

## 2026 build — status and decisions

### Already built (in the data bundle)
- All 32 head coaches rated from career records
- All 64 coordinators rated from real 2025 units, play-caller aware
- All 32 special teams rated from 2025 rankings
- Schemes, fronts, coverage for all 32, verified against multiple sources
- 2025 team performance data (points, opponent-adjusted SRS)

### Decisions locked in
- **Long snappers:** cut all of them. None are viable elsewhere — their overalls are graded purely on snapping while their blocking sits in the 45–69 range
- **Edge/LB:** Madden 27 uses `LEDG`/`REDG` and `MIKE`/`WILL`/`SAM`. Map by each team's real scheme (3-4 vs 4-3), which is in the bundle
- **Fullbacks → RB**, but rebuild attributes from source and re-rank within the RB pool. Do not trust Madden's FB overall
- **FS/SS → S**
- **Free agents:** keep all post-cut players (~1,100 league-wide before practice squads)
- **Draft classes:** real names for 2027 and 2028, generated for 2029 and 2030. Real names exist for 2029 via recruiting rankings but carry no NFL signal; 2030 would be current high schoolers
- **Appearances:** seed from a hash of the player's name so rebuilds don't reshuffle faces. This file will be refreshed; the historical ones won't
- **Tampa Bay has no defensive coordinator** — Todd Bowles calls the defense. George Edwards (pass game coordinator) fills the slot

### Still needed
1. **Post-cut rosters.** Cuts are Sunday Aug 30 (6pm ET), waivers clear Monday Aug 31 (1pm ET), practice squads that evening. Tuesday Sep 1 is the first settled day
2. **Madden 27 spreadsheet** — the person has it; single file, all 32 teams, 2,362 players. Contains ratings, contracts, ages, attributes. Already on the modern scale, no rescaling needed

That's it. Everything else is in the data bundle.

### Draft classes
**2027: 289 prospects, production-ready.** Ranks 1–100 from the NFL Mock Draft Database consensus board (31 analyst boards aggregated); 101–300 from Drafttek's preseason Top 450. Two boards stitched, so the seam near rank 100 is approximate — fine for a draft pool.

**2028: 32 prospects, low confidence.** No genuine overall 2028 big board existed as of late August 2026. The source is a first-round mock draft projection whose team order was explicitly randomized, so treat rank as rough ordering only. Schools may be stale. Use these 32 as the top of the class and generate the rest, or re-check for a real board later in the season.

**2029 and 2030 are generated**, per the decision above.

**Important conceptual note:** in the historical builds, prospect *potential* comes from a draft-slot baseline raised by what the player actually became (first-team All-Pro count, MVP/DPOY/OPOY, career AV and years started, per position). That's impossible for future classes — potential has to come from board rank instead. This means no hidden gems and no busts; the draft reflects consensus opinion. Arguably more realistic for a GM sim (you draft on scouting, not hindsight) but it's a real difference worth mentioning in the Reddit post.

### Known characteristics of the Madden 27 file
- 74 players per team (EA's cut of the 90-man rosters — not real 53s)
- Median overall 71, 4.0% at 90+ — matches 2010/2017 exactly
- Contracts included (`_TotalSalary`, `_SigningBonus`)
- No free agent pool — every player has a team

---

## How attributes get derived

This was never written down and cost a session to reconstruct. Three tiers, then a refit.

**1. Direct map** where a Madden column corresponds to a PGM3 attribute:
`PSPD`→speed, `PACC`→burst, `PSTR`→power, `PAGI`→agility, `PJMP`→jumping, **`PSTA`→stamina (NOT `PSTM` — see below)**, `PTAK`→tackle, `PPBK`→passBlock, `PRBK`→rushBlock, `PCAR`→ballSecurity, `PKAC`→kickAccuracy, `PCTH`→catching, `PAWR`→intelligence, `PTHA`→all three pass accuracy fields and throwOnRun. `PINJ` **inverts** to injuryProne (confirmed: correlation −0.52, and PGM3's higher value means more fragile).

**`PSTM` is not stamina.** `PSTA` is. An earlier version of this document had `PSTM`, which is ~54% zeros with a median of 0 in the 2007 file and correlates 0.16 against a known stamina column. `PSTA` runs median 80–85 and correlates 0.86. Following the wrong one ships most of a file with stamina 0, or — if you then rescale to fix the distribution — with a plausible-looking distribution and no real per-player signal. The 2004 file had exactly that: correct median, correlation 0.116 with the true source. Verify any field code against a named column in another year before trusting it.

**Direct-mapped attributes still need quantile-mapping per position.** Madden's scales don't match PGM3's at the low end — raw Madden gives offensive tackles jumping ~30 against a working-file 68, kickers power ~34 against 74, QB rushBlock 20 against 40. Copying values across ships several attributes 20+ points low. Let Madden supply the ordering and the working files supply the scale, exactly as with the rating rescale.

**2. No usable Madden source.** Several attributes have no equivalent — vision, decisions, releaseLine, manCover/zoneCover all correlate below ~0.5 against anything in Madden. Fill these from the donor's per-position distribution at the player's rating percentile. That's what `per_position_attr_percentiles_from_2010_2017` in the schema reference is for.

**Source tiers, best first.** Post-season CSV for the target season → the same season's launch spreadsheet for anyone the CSV misses → an adjacent year's file with a damped age adjustment → derived from draft position and experience. Real data from the right season always beats derivation, even when it means adding a tier. Any value carried between tiers must be re-derived through the current map, never copied — a bias correction fitted to one scale is meaningless on another.

**When a year's attribute set is missing, use a neighbouring year's real attributes — not percentiles.** Tested on the 2010 draft class with a one-year gap, 176 players and 1,356 comparisons: adjacent-year real attributes score MAE 2.35 against 8.52 for percentile-from-overall. It wins on every single attribute, and by an order of magnitude on physical ones (speed 0.73 vs 7.50, trucking 1.57 vs 19.61). Madden essentially doesn't re-rate physical attributes year to year, so percentiles throw away real per-player signal and substitute a generic spread.

**Do not apply an age adjustment to attributes.** The bias correction fitted for *ratings* makes attributes worse (injury 4.30 → 6.53, strength 1.35 → 1.59). Awareness genuinely grows — rookies sit ~7.9 points below their second-year selves — but correcting for it lands inside the noise. Ratings and attributes need different treatment.

Percentiles remain the fallback only when no neighbouring year covers the player at all.

**3. Refit against the position weights** so the computed overall equals the target rating, bounded by the observed min/max per attribute. This is the step that makes the file consistent regardless of how any individual value was sourced. Without bounds, the solver drives jumping, vision, decisions and intelligence below anything in the working files.

**Position collapse: map against the real target cohort, not the whole pool.** Madden rates fullbacks *above* halfbacks (median 82 vs 79) because it grades them on blocking. But the actual FB cohort in the working files sits at the 28th percentile of the RB pool — median 65, with elite blockers like Vonta Leach and John Kuhn at 45. Mapped as ordinary RBs, Lorenzo Neal at 98 becomes a top-five back. Mapped against the real FB cohort he lands at 83, the cohort ceiling. **Find the target cohort by name in the working files and map against it.** This generalizes to any position collapse where the source grades on different criteria.

**Don't switch primary rating source mid-build.** If a better source appears, rebuild every record against it rather than patching. Two rating scales in one file is invisible to every structural check and shows up months later as odd gameplay. The same applies to any value fitted to the old scale — corrections, backfills, derived fallbacks all need re-deriving from raw source, not carrying over.

**Only populate a position's live attributes** — `weights.json` lists them per position; everything else stays zero. Live counts: 20 for QB/RB/WR/TE, 18 for MLB/CB/S, 16 for DE/DT/OLB, 14 for the offensive line, 12 for K/P. Position gating is real and must be preserved: manCover/zoneCover only for MLB/CB/S, pass accuracy QB-only, kickAccuracy K/P only.

**The standard reconstruction is the one in `PGM3_2026_build_data.json`** — refit from the 2010 and 2017 published rosters, rostered cohort only (including the Rookie pool corrupts the fit), R² 0.9922–0.9994. Use it. It supersedes an earlier donor-fitted version.

**How much does a wrong reconstruction actually cost?** Almost nothing in play. The game recomputes overall from attributes using its own weights, which nobody has; the stored `rating` is display only. A reconstruction that's off by half a point means the game shows a number half a point from what was intended. **What it does break is validation** — a file refit under one reconstruction shows 4–5 point "errors" under another, which looks like a defect and isn't. That's a reporting problem, not a data problem, and it isn't worth refitting finished files to resolve.

**Two divergent reconstructions exist.** One was refit from the donor file, one from 2010+2017. Both hit R² above 0.99, but coefficients differ by up to 3.2 (offensive tackles). **Consequence: refit error is only meaningful against the weights a file was fitted with.** A file refit under one reconstruction will show 4–5 point errors under the other, which looks like a defect and isn't. Before comparing refit error across sessions or files, confirm both used the same weights. Ship the weight file alongside any build that used it.

**On weights.json:** it has been lost to container resets twice and reconstructed both times — once by regressing on the donor, once on 2010+2017. Both recoveries hit R² above 0.99 with median error under half a rating point, which is good evidence the model is genuinely linear. But it is a **fitted artifact, not an authoritative file.** Keep a copy in the build data bundle. If a real one ever surfaces, diff against it.

---

## The face registry — apply it last, every time

`PGM3_FACE_REGISTRY.json` gives every recurring person one face across every season he appears in. It holds 6,008 players keyed on `"normalized name|position"` and 538 staff keyed on **name alone** (a coach changes role between years, so position can't be part of the key).

**It is the last step of any build.** After appearances are sourced or generated, apply the registry over the top. Nothing runs after it.

**It is also where Ryan's hand edits live.** He edits faces in-game so players look like themselves; those edits are the highest-priority entries. Applying the registry means he never rebuilds a face he has already made. Before it existed, Bill Belichick had five different faces across five files and so did Tom Brady — 3,655 players who appear in more than one roster looked different depending which you loaded.

**Adding new hand edits:** Ryan exports from the game and sends the file. Diff it against the source, and write every changed record into the registry at top priority — **including draft prospects and free agents.** Skipping those cohorts has lost his work twice; there is no safe cohort.

**Priority when a player appears in several files:** Ryan's export first, then 2004, 2007, 2013, 2010, 2017.

**Known open issue (still open after the 2026-08-28 application): 262 names are split across two positions with two different faces**, because the key is `name|position` and players change position between seasons — Dansby OLB/MLB, Dockett DT/DE, Brooking OLB/MLB. That is the thing the registry exists to prevent. It can't be fixed by keying on name alone, because roughly 47 of the 262 are real namesakes (Alex Smith QB and TE) who must stay split. Each needs the same-file test: two entries in one published file means two people; entries in different files only means one player who moved. Written up in `PGM3_TASK_registry_position_splits.md` with the worklist in `PGM3_FACE_REGISTRY_SPLITS.json`. Not urgent — it's how the published files already look. Fold it into the next full regeneration.

The registry is ~700KB, too big to sit comfortably in project context alongside everything else. Ryan uploads it to whichever session needs it, like the Madden spreadsheets.

**Applied to all five published files 2026-08-28.** Result: 3,118 players and all 207 staff inconsistencies resolved. Players carrying more than one face across the five files dropped from 4,063 to 945. Belichick and Brady are down from five faces each to one. Validation clean — record counts, schemas and every non-`appearance` field unchanged; family rules hold; no player wearing glasses; all tokens in vocabulary.

**The 945 that remain are the `name|position` split problem** documented above and in `PGM3_TASK_registry_position_splits.md`. They were deliberately left alone: resolving them means choosing which of two faces to keep, and some of those faces are hand edits, so guessing risks overwriting the person's work.

**Formatting note:** the rewrite normalised JSON whitespace, which varied between the published files. `PGMRoster_2007.json` was pretty-printed and is now compact (4.41MB → 3.66MB); the staff files were written without separator spaces and are now slightly larger. Functionally identical, but expect a whole-file diff rather than a clean one.

---

## Appearances: the library, and protecting hand edits

### Hand edits always win
The person edits avatars in-game, exports, and sends the file to be merged. **Any bulk operation must run FIRST, then hand edits merge on top.** Doing it the other way silently overwrites their work — this has happened, and it took several of their hand-edited draft prospects (Rodgers, Cutler, Flacco, Vince Young).

They can edit **anyone**: rostered players, draft prospects, free agents, coaches. There is no protected category. Never assume a cohort is safe to bulk-modify.

Also never modify a face to break a duplicate — duplicates are fine (see Appearance rules).

### The appearance library
Appearances in the published files were sourced from Madden's `PSKI` (skin) and `PHCL` (hair) fields, which exist **only in the disc PLAY CSVs** — the maddenratings.net spreadsheets have no appearance columns at all.

Mapping:
- `PSKI` 0 = light → skin families 1–3, 1 = medium → 3–4, 2 = dark → 4–5
- `PHCL` 0 = Hair1 (black), 1 = Hair5, 2 = Hair3 (brown), 3 = Hair4, 4 = Hair2

**`PSKI` is four-level in several files, not three.** Where a fourth value
exists, 0 is light and 2 and 3 are both dark. Value 1 is not a middle tone — in
the 2000 file it is bimodal, roughly 54% dark, and should abstain rather than
vote.

**Never source skin from a file that has not been scored.** Seven of seventeen
Madden CSVs carry no usable skin signal, including `2003`, `2004` and `2013`,
which were previously treated as good. See `PGM3_SOURCE_QUALITY.md` for the
scored table and the ten-second spread test that identifies a bad file.

**Appearance is stable across years** — 98% identical for players present in both the 2005 and 2007 discs. So a player's face can be sourced from *any* file he appears in, not just his own season.

**That makes the published rosters a growing library.** A 2008 draftee is a veteran in the 2010 file with a real face already assigned, in PGM3 format, already rule-valid. Build the lookup keyed on normalized name + position from the **rostered cohort only** (prospects and free agents were never sourced), then copy the 9-element array across directly.

Applied so far: 519 faces to 2004's draft pool, 402 to 2010's, 23 to 2017's. 2017 gains little because its prospects are the 2018–2021 classes and nothing in the project is newer — **that will fix itself once 2026 is built.**

A degenerate skin field — one value holding 29–92% of the league — makes a file
useless for skin. **This is not a community-versus-official split.** The JINX
community files score 0.92–0.98 and are usable; the year-named `2003`, `2004` and
`2013` files score 0.59–0.65 and are not. Score every file individually before
use — `PGM3_SOURCE_QUALITY.md`.

---

## Merging avatar edits from the person

The game can export the roster it's currently using (there's a download option in settings). The person edits avatars in-game to make players look more like themselves, then sends the export. **This is the best way to capture avatar work — much better than describing faces in words — and the edits should be merged back into the source file so they survive rebuilds.**

How to merge:

1. Diff the export's `appearance` arrays against the source file
2. **Match on forename + surname + position + teamID, not `iden`.** The game regenerates every `iden` on import, so IDs never survive a round trip. Including teamID resolves nearly all duplicate-name cases (e.g. a veteran on a team and a prospect of the same name in the draft pool)
3. **Skip anyone still ambiguous after that** rather than guessing. Matching on name alone once reported 22 edits when the person had made 16
4. Confirm the list with the person before applying — they'll know what they actually changed
5. **Do not "fix" duplicate appearances afterward.** Duplicates are normal (see Appearance rules above). Never modify a face the person set

An export taken mid-season will have aged a year and will contain game-generated prospects that don't exist in the source. That's fine, it just means fewer records match.

**Merged so far in 2004:** 68 players and 24 coaches, plus a handful of draft prospects. Four prospect edits (Rodgers, Cutler, Flacco, Vince Young) were lost to a library pass and need re-merging from a fresh export. Players include most of the era's stars (Ray Lewis, Strahan, Peppers, Walter Jones, Ogden, Pace, Moss, Holt, Harrison, Owens, Gonzalez, Witten, Gates, Tomlinson, Alexander, Dawkins) plus 15+ quarterbacks. Coaches include Belichick, Parcells, Gibbs, Cowher, Dungy, Holmgren, Shanahan, Gruden, and four free agents.

**No college field exists.** The schema is 52 keys with no college. The person edited a player's college in-game, exported, and it did not persist — PGM3 generates colleges at runtime. Real college data can't be authored into the file. This is a standing feature request to the developer.

---

## Appearance data — solved sources

Appearance is now sourced from real Madden data for 96–99% of players in every
published file. There are three separate sources; use them in this order.

### 1. Xtreme DB `PLAY` table CSV exports — the authoritative source

Ryan can open any `.ros` file in Xtreme DB Editor and export the `PLAY` table to
CSV. This gives **named columns** — no bit offsets, no inference. Sixteen exports
now exist, covering 2003–2025.

- **`PHCL` is hair colour and is completely reliable.** Every dark-haired player
  reads 0 in all sixteen files. Map: `0`→family 1 black, `1`→5 blond, `2`→3 brown,
  `3`→4 red, `4`→2 light brown. **Verified: Andy Dalton reads `PHCL` 3, which maps
  to family 4, independently identified as red from in-game screenshots.**
  14,246 players. Resulting spread: 74% black, 23% brown, 2.1% blond, 0.7% red.
- **`PSKI` is skin tone but is NOT consistently scaled across community rosters.**
  The 2011–2015 exports put light and dark players both on value 1; the 2025 export
  spreads light players across 0, 1 and 2. **Anchor it per file against known
  players before using it**, or use the photo measurement instead.
- **`PWGT` + 160 = real weight in pounds.** Verified exactly: Brady 225,
  Donald 280, Joe Thomas 312, Vita Vea 347. This is what drives face shape.
- **`PHED` exists (15 values) but is not used.** It correlates with weight but is
  independent of skin and age. Face shape is derived from real weight and age
  instead, which is more accurate.
- **There is no facial hair or hairstyle column.** Every field in `PLAY` and `COCH`
  was tested against known bearded and clean-shaven players; nothing separates
  them. Madden of this era does not store them. Settled — do not retest.

### 2. The `.ros` binaries directly

Sixteen files decode. Skin sits at **bit 402** in the 2003–2008 and 2016–2025
files, and **bit 464** in the 2011–2015 files. `PSKI` is a **three- or four-level
scale** depending on the file (see `PGM3_SOURCE_QUALITY.md`), not binary —
collapsing it to two breaks calibration.
This route is superseded by the CSV exports but is still how the coach data was
found.

**Coach appearance is in the `COCH` table.** Note the table directory starts at
**offset 0x18**, not 0x40 — reading from the wrong offset hides five of the ten
tables. 229 real coaches per file, 66 named fields. Skin is at **bit 392**,
91–98% accurate on 2,685 labelled observations. The named `CSKI` column in a
`COCH` CSV export agrees with it exactly.

### 3. Photo measurement from NFL headshots

nflverse publishes headshot URLs. Skin tone, hair colour, hair height and facial
hair can all be measured from the pixels. **For skin tone this is more reliable
than `PSKI`** — it caught Travis Kelce and David Bakhtiari being wrongly dark.

Practical notes if this is picked up again:

- The images are **RGBA with transparent backgrounds**. Converting straight to RGB
  produces garbage; composite onto white first
- Roughly **half of all players return a helmet silhouette placeholder**, not a
  face. Detect by skin-pixel fraction: real faces are 7–17%, placeholders 0%
- Find the face by **skin colour** (`R > G >= B`), not by geometry — head-based
  geometry fails on players with long hair
- Chin sits about **2.05 face-widths** below the forehead
- Hair extent must be measured as **"not background"**, not as "dark", or a dark
  jersey reads as hair
- Anything measuring beside or below the head hits the jersey and is unreliable;
  only the zone directly above the crown works

---

## Hair and beard style vocabulary — mapped

Both were mapped from in-game screenshots of the editor cycling through options,
anchored against players whose tokens were known.

**Hair, 20 styles** (black has all 20; other colours have 12, missing the
textured ones). **The list that was here was inferred from cycle position and was
wrong on fourteen of twenty entries. It has been replaced by observation — see
`PGM3_HAIR_VOCABULARY.md`, which is now authoritative.**

Summary of the observed list:

`a` short tapered crop · `b` medium wavy messy · `c` short spiky quiff ·
`d` short flat crop · `e` medium swept back · `f` long shaggy · `g` short spiky
textured · `h` short buzz · `i` very short, receding temples · `j` fully bald ·
`k` horseshoe (bald crown, hair at sides) · `l` shaved with stubble ·
`m` short dreads/twists · `n` very short textured crop · `o` cornrows with
braids behind · `p` short afro / high-top fade · `q` tall curly afro ·
`r1` long dreadlocks · `r2` long dreadlocks · `s` cornrows with visible parts

Only `b`, `h`, `i`, `j` and `m` survived from the inferred list — the three that
had ever been anchored against a real player, plus two lucky hits. Everything
else moved.

`r1` and `r2` could not be separated; both render as long dreadlocks.

Consequence: `k` is a fourth balding style alongside `f`, `g` and `i`. Hair style
is assigned at random with no age relation, so roughly 2,600 players across the
published files wear a balding style unconnected to their age.

**Beard, 7 styles in a cycle of 8 tokens** (`f1` and `f2` render identically):

`g` clean shaven · `a` subtle stubble · `b` moustache with soul patch ·
`c` chin strap, no moustache · `d` moustache with goatee · `e` full beard
moderate / fu manchu · `f1`/`f2` full beard thick

Both are currently assigned at random. The intended fix is to measure a category
from the photo and **draw a specific style within that category, seeded on the
player's name** — so the same player always gets the same style, but a hundred
short-haired players spread across the short styles rather than sharing one.

**Head variants are solved and applied:** `a` thin young, `b` thick young,
`c` thin old, `d` thick old. Assigned from real weight (`PWGT` + 160) and age,
thresholds 260 lb and age 30. Result: thin faces average 217 lb, thick 301 lb;
young faces average 24, old 32. Face shape is deliberately **not** merged across
files — a player ages between seasons, so Brady is `Head1a` in 2004 and `Head1c`
from 2007 on.

---

## Current state of the published files

**All twelve files rebuilt 2026-08-29.** Contracts corrected and era-scaled;
appearance rebuilt from real Madden data.

- **Skin and hair colour are 96–99% sourced in every roster.** Agreement with
  source: 99.7% skin, 99.8% hair
- **Contracts**: the double-count is fixed (cap hit = `salary` + `guarantee`), and
  each era is scaled so the median top-53 cap hit is 197.4M against a 280M cap.
  All six sit at 200–207M median team payroll, 0/32 teams over cap
- **Coaches**: skin from the `COCH` table plus 402 hand-researched coaches which
  take priority. Tomlin, Carroll, Arians, Harbaugh and Caldwell were all wrong
  before this and are now right
- **Staff faces unified** — 81 people had different faces in different files
- **Jersey numbers verified** 16/16 against reality; **contract lengths verified**
  10/11, the miss being Mahomes at 7 because his 10-year deal exceeds the game's
  length cap

**Known open items, none blocking:**

0f. **THE 2000 FILE DIVERGES FROM THE PUBLISHED FILES IN THREE PLACES, ON
   PURPOSE. None of the three is visible to `pgm3_validate.py`.** Recorded here
   rather than only in a build log, because the validator will never surface
   them and a future session would otherwise find a 2000 file that disagrees
   with its neighbours, find no explanation, and "fix" the correct one.

   | deviation | matches | diverges from | measured reason |
   |---|---|---|---|
   | `OLB` `manCover`/`zoneCover` gated OFF | 2004, 2007, 2017 | 2013, 2021 | where present the entire range is **1–3** against `MLB`'s 38–92, and 62–100% of the non-zero values are the fill value 1 |
   | team payroll ~**$54M** | — | all seven ($150–250M) | the real 2000 cap was **$62.17M**; the published files are not era-scaled, which the precedents record as a defect nobody caught rather than a convention |
   | K/P salaries capped ~**$1.2M** | — | all seven (K p95 **$7.61M**, P max **$10.56M**) | the real 2000 top-of-market for a kicker was **$1,071,167** (Jason Elam) |

   **Two more, on the STAFF side, both validator limitations rather than file
   defects:**

   | check | reports | why it is correct |
   |---|---|---|
   | `duplicate names` [2] | Dick LeBeau twice, Jim Mora twice | LeBeau held **Cincinnati HC and DC simultaneously** — a ruling, not an error. The two Moras are **different men**, father at Indianapolis and son at San Francisco. The check keys on name alone and cannot express either |
   | `verified faces intact` [2] | `jim mora` @ 1986 and @ 2000 | Same hole. The registry holds Mora Sr. in `staff_faces_1986` and Mora Jr. in `staff_faces`; a name-alone check must call one of them an overwrite. The 1986 instance predates this build |

   **The 2000 staff file adds ZERO new face inconsistencies to the archive.**
   Measured by running `faces --staff` over the published files alone and then
   with 2000 added: head-family, hair-style and full-face disagreement counts
   are **21 / 38 / 40** either way.

   **Why the validator cannot see any of them.** `zero_pattern` pools all
   positions for rosters, so `OLB` at 0% is diluted by `MLB`/`CB`/`S` at 100%;
   and `cross_year` skips money fields by design, since they legitimately differ
   by era. All three are correct divergences from defective references.

0e. **BACKLOG — make `zero_pattern` per-position for rosters.** It currently
   splits **staff by role** ("a scout legitimately has zero playcalling, and
   pooling roles hides that") but **pools roster records across positions**. The
   same reasoning applies: a linebacker legitimately has zero `kickAccuracy`.
   It is an inconsistency, not a design choice.

   **What it actually is: a defect detector for the cleanup passes.** Three of
   the five published-file defects queued below are fill artifacts hiding in
   specific positions — `OLB` coverage, and the position-specific parts of the
   stamina and salary spikes. A per-position zero-pattern check is the
   instrument that would have found them without anyone looking.

   **Do not build it mid-roster-build**: it moves the standard a file is being
   measured against while it is being measured, and it will almost certainly
   fire across all seven published files at once. **Run it report-only against
   all seven first, then decide about gating.**

0d. **PLAYABILITY DEFECT — kicker and punter CONTRACTS are inflated, not just
   their ratings.** Measured 2026-08-31 while building 2000's contracts;
   confirmed independently by Ryan. Pooled across the published files, **kickers
   reach a p95 of $7.61M and a max of $10.4M, punters $10.56M**, against a real
   2000 top-of-market of about **$1.07M** (Jason Elam, the highest-paid kicker
   in the league that year). Their median sits at 1.0–1.9x the league median
   depending on the file — second only to quarterbacks in several.

   This is the K/P inflation trap showing up in a **second field**. The ratings
   version is documented and guarded against; the contract version was not.
   **Probably the most visible of the five backlog defects in play** — a $10M
   punter is something a user notices immediately, where a stamina-1 block or an
   unused head family is not.

   The 2000 build does not inherit it: position ceilings come from the real 2000
   market, not from the published files. **Fifth member of the "a safe default
   is still a claim" family.**

0c. **The 2000 Madden file is a PRESEASON PROJECTION, not a performance
   rating.** Robert Brooks is rated **91 overall** in it. He retired in August
   1999, came back with Denver in 2000, played four games and caught three
   passes for 51 yards, then retired for good. Madden is rating his 1995 peak,
   not his 2000 season. Implications well beyond contracts: any check that
   assumes the source reflects what a player did that year is measuring the
   wrong thing, and a player's rating carries no information about whether he
   actually played.

0b. **Salary fill artifact — the published files spike at round mid-range
   numbers.** Found 2026-08-31 checking whether they clamp or smear at the
   bottom. They **smear** (2004's bottom decile holds 83 distinct values of 188),
   so there is no minimum-salary convention to inherit — but each file carries a
   spike somewhere in the middle instead: **2007 has 384 rostered players (20.5%)
   on exactly $1,019,000**, 2010 has 188 on $779,000, 2004 has 112 on $730,000.
   A fifth of a roster on one salary to the dollar is a fill, not a negotiation.
   **Fourth member of the "a safe default is still a claim" family**, after the
   1986 free-agent skin, the stamina-1 block, and the OLB coverage 1-3 values.

0a. **PLAYABILITY DEFECT — 1,622 players across the published files have
   `stamina` 1 and will gas out in game.** Found 2026-08-31 during the 2000
   build; confirmed independently by Ryan. **Backlog for the master session.
   This is a playability item, not data hygiene** — it is the same failure the
   handoff already records for 2004's stamina scale mismatch, where 87% of
   players would have gassed out and it was treated as a serious bug.

   | file | at stamina 1 | share of non-zero |
   |---|---|---|
   | 2007 | 9 | 0.3% |
   | 2010 | 0 | 0.0% |
   | 1986 | 200 | 6.1% |
   | 2021 | 226 | 6.9% |
   | 2013 | 285 | 8.0% |
   | 2004 | 267 | 8.8% |
   | **2017** | **635** | **18.0%** |

   (Counting every non-zero record. Rostered-only the total is 1,267 and 2017
   reads 24.9% — state the cohort when quoting these.)

   2017 has 635 players who gas out. The block is spread across every position
   and concentrated in low-rated fringe players: a cohort that never got a real
   source and took a default instead. **Same shape as item 0 below** — third
   sighting of "a safe default is still a claim". `zoneCover`, `manCover` and
   `greed` carry smaller blocks of the same kind.

0. **1986's free agent pool never got a skin source — 198 of 201 are dark
   (98.5%).** Found 2026-08-31 while cohort-matching a distribution check for
   the 2000 build; confirmed independently by Ryan. **Backlog for the master
   session — do not chase it mid-build.**

   | family | n |
   |---|---|
   | 1 | 3 |
   | 2 | 0 |
   | 3 | 0 |
   | 4 | 95 |
   | 5 | 103 |

   Families 2 and 3 are entirely unused, which is the signature of a cohort that
   was never sourced rather than one sourced badly. The rostered 1986 cohort next
   to it reads 67.9% dark and 16.1% family 1, so the defect is confined to the
   free agents. Named cases: **Ralph Giacomarro** (P) is `Head4c`, **James Britt**
   (CB) `Head4a`, **Cliff Benson** (TE) `Head4c`. The only three light players in
   the whole pool are Joe DeLamielleure, Jan Stenerud and John Hannah.

   This is the 1986 skin defect again, in the cohort the original repair pass did
   not cover — the free agents were built in a separate session from the rostered
   file. It is also the exact thing the handoff warns about under "there is no
   safe cohort".

   **Consequence for anyone using a distribution band:** it inflates the top of
   any range that includes free agents. The published rostered+FA dark band reads
   63.8–71.1%, and the 71.1% ceiling is this bug. Do not trust that band to three
   significant figures.

1. **508 players have no skin data** — scattered fringe players in no Madden
   roster. The photo route would cover them
2. **230 players carry more than one face.** 222 are genuinely different people
   sharing a name (different position *and* birth year). Only ~8 are worth
   reconciling
3. **Facial hair and hairstyle are unsourced for everyone.** Not in any Madden
   file of this era. The photo measurement is the live attempt
4. **2007 Adrian Peterson** is a validator false positive — Bears RB and Vikings
   RB, two real people
5. **`eSalary`/`eGuarantee`/`eLength` are game-computed** and overwritten on
   import. Don't fit them

**Saved games do not pick up any of this.** Republished files only affect newly
started leagues.

---

## Reading modern Madden files

`madden-file-tools` (npm, by bep713) reads the `FBCHUNKS` roster format directly
and gives **208 named fields** instead of the 92 numeric IDs a hand-written parser
finds. Install with `npm install madden-file-tools --ignore-scripts`, then
`require('madden-file-tools/helpers/MaddenRosterHelper')`.

The six `ROSTER-MADDEN*PRIME` files decode cleanly this way — but **their
appearance fields are empty**. `PLHS` (hairstyle) is zero for all 3,133 players in
all six. They contain nothing useful for faces.

The remaining lead for hairstyle and facial hair is a **real Madden 24 or 25
franchise save**, where appearance lives in a `CharacterVisuals` table as JSON
with named assets. Roster files do not have it; franchise files do.

---

## Reddit posts

Posts are published for 2010 and 2017; a 2004 post is drafted. They promise real draft slots, real coaching staffs, and real contracts — **check that claims in the posts are actually true of the files.** The pick-number issue was caught this way.

Tone: written for people who already play the game and use custom rosters. No methodology explanations. Short, direct, links first.

---

## Working style

The person is direct and concise — single-word approvals are normal. They push back immediately when something stops short or makes an unwarranted assumption. That pushback has been right every time it's happened, including:

- Catching that a fullback shouldn't be a 90-rated RB
- Asking why only 16 of 32 coaches got real schemes
- Noticing staff salaries were too compressed to matter
- Pointing out that deleting 2010's pick numbers destroyed real data
- Asking "is there anything else you decided was okay?" — which surfaced three more real bugs

When they ask for a document from another AI, give them a precise prompt including an instruction to say "uncertain" rather than guess. That workflow has produced excellent, verifiable data three times. **Verify a sample of what comes back before building on it.**
