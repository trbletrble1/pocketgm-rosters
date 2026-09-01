# Task — 2026 season build

Build `PGMRoster_2026.json` and `PGMStaff_2026.json`.

Written by the master session 2026-09-01, the first settled day after cuts.

**Read first:** `CLAUDE.md`, `docs/PGM3_PROJECT_HANDOFF.md` (especially the
"2026 build" section and "How attributes get derived"), `docs/PGM3_PRECEDENTS.md`,
and `docs/PGM3_BUILD_FRICTION.md`. Where this brief and the handoff disagree, say
so rather than picking one — a contradiction between documents is an escalation,
not a judgement call. That exact situation shipped a broken 2000 file.

---

## What is already done

`wip/PGM3_2026_build_data.json`, built 2026-08-25. Do not re-derive any of it:

- All 32 head coaches rated from career records
- All 64 coordinators rated from real 2025 units, play-caller aware
- All 32 special teams from 2025 rankings
- Schemes, fronts, coverages for all 32
- 2025 team performance, points and opponent-adjusted SRS
- 2027 draft board, 289 prospects; 2028 board, 32 prospects, low confidence
- The position weights reconstruction — R² 0.9922–0.9994, use this one

Decisions already locked are in the handoff's "2026 build" section: long snappers
cut, edge/LB mapped per team scheme, FB→RB re-ranked within the RB pool, FS/SS→S,
all post-cut players kept as free agents, appearances seeded on name hash.

---

## The two inputs, both now in hand

**1. nflverse `roster_2026`** — post-cut and settled, verified 2026-09-01:

    https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv.gz

    1,695 ACT     31 of 32 teams at exactly 53 (LA at 52, one open spot)
      855 CUT/W04  the free agent pool
      223 RES      reserve/IR

This is the authority on **who is on a roster**. It carries position, jersey
number, birth date, height, weight, college, years of experience, `draft_club`
and `draft_number`.

**2. The Madden 27 launch spreadsheet** — 2,362 players, 72 columns, on the
modern scale, no rescaling needed. This is the authority on **how good they are**.

Same architecture as the 2000 build: an external source says who existed, the
Madden file says what they are. The spreadsheet being pre-cut (74 per team, EA's
slice of the 90-man rosters) is fine and expected.

---

## Step 1 — the join, and the thing that will bite you

Match nflverse to Madden on normalised name. **Run a nickname pass before you
report any match rate.**

Exact-name matching gives 95 misses. Twelve of those are name-form mismatches and
the real number is **83**:

    Cameron Heyward -> Cam Heyward          Pat Surtain II  -> Patrick Surtain II
    Foye Oluokun    -> Foyesade Oluokun     Daxton Hill     -> Dax Hill
    Olu Oluwatimi   -> Olusegun Oluwatimi   Chig Okonkwo    -> Chigoziem Okonkwo
    Josh Palmer     -> Joshua Palmer        Matthew Orzech  -> Matt Orzech
    Olumuyiwa Fashanu -> Olu Fashanu        Francisco Mauigoa -> Francis Mauigoa
    Christian Roland-Wallace -> Chris Roland-Wallace
    Ben Yurosek     -> Benjamin Yurosek

**It goes both directions** — nflverse has the short form sometimes and the long
form other times — so a one-way rule misses half of them.

The rule that worked: same surname, same first initial, and one first name a
prefix of the other. That recovered 12 with **zero ambiguous**. Assert the
recovery is one-to-one and refuse anything ambiguous rather than guessing; 12 for
12 is partly luck and a bigger cohort will collide.

**Report the match rate after the nickname pass, not before.** Reporting 94% when
the real figure is 95.1% is the same class of error as the punctuation bug that
nearly cost a thousand registry matches.

### The 83 genuine misses split into two tiers

    32 rookies    never in any Madden file
    51 veterans   late signings — Von Miller (DAL), Keenan Allen (IND),
                  Stefon Diggs (WAS), Darren Waller (CAR), Za'Darius Smith (ATL),
                  D.J. Humphries (WAS)

EA locked the roster before those men signed. **Veterans take the adjacent-year
tier** — real attributes from a prior Madden file, which measures 2.35 MAE
against 8.52 for percentile fill. **Rookies take draft position**, and
`draft_number` is in the nflverse file.

Assert on the match rate, not the output count. Every tier here has a fallback
that keeps the count right by construction.

---

## Step 2 — attributes

**The handoff's attribute map now has two columns**, `.ros` code and spreadsheet
name. Use the spreadsheet column. Do not translate the codes yourself.

**Five attributes the handoff previously called unsourceable now have named
columns** — `vision`, `decisions`, `releaseLine`, `manCover`, `zoneCover`, plus
`routeRun`. All 100% populated with correct positional structure
(`ManCoverageRating` medians 71 for CB, 12 for QB). The handoff section is
updated with the table. **Use the columns and anchor-test each one anyway.**

**`ToughnessRating` is not stamina. `StaminaRating` is.**

Two rulings already made and recorded in the handoff: pass accuracy maps
one-to-one to Short/Mid/Deep, and `routeRun` takes `ShortRouteRunningRating`.

**Direct-mapped attributes still need per-position quantile mapping.** Madden's
scales do not match PGM3's at the low end.

**Run the conditional pass on every direct-mapped attribute**, not just stamina.
Split by source decile and confirm monotonic separation within position. A pooled
correlation looks broken when it isn't — measured within (cohort, position),
stamina reads 0.999 where pooled reads 0.847.

---

## Step 3 — the free agent pool needs a ruling

The handoff says keep all post-cut players. That is 855 people, and **only 335 of
them are in the Madden file** — EA ships no free agent pool, every player there
has a team.

So 520 free agents would be fully derived. That is a large invented cohort in a
current-season file where everything else is real.

**Bring me the options with numbers, do not choose.** At minimum: keep all 855
and state the derived share plainly, or trim to those with a Madden record plus
recent-experience veterans, or something else you have measured.

Free agent conventions that are already settled: `salary` 0 (six of seven
published files), `length` 0, `teamNum` 0. `eSalary`/`eGuarantee`/`eLength` are
game-computed — ship sane values and spend no time fitting them.

---

## Step 4 — contracts

`_TotalSalary` and `_SigningBonus` are in the spreadsheet.

**Scale to the fitted engine constant, not to the real 2026 cap.** Median team
payroll on a **top-53** basis must land on **$197.4M**. All eight published files
sit within $29k of it. The game's cap is a fixed ~$280M and does not know what
year it is; era-real dollars produce a file with no cap pressure, which is
exactly what shipped in the first 2000 build and was caught only when Ryan
started a season and found Green Bay $224M under.

`guarantee` is the prorated signing bonus, not the whole figure.

---

## Step 5 — staff, draft classes, appearances

**Staff** comes almost entirely from the bundle. Every team carries exactly 9:
head coach, two coordinators, special teams, three scouts, two physios — 32 × 9
in every published file, no exceptions. Tampa Bay has no defensive coordinator
(Bowles calls it); George Edwards fills the slot and it is logged as a promotion,
not a title he held. Scouts and physios are generated per the standing ruling;
check invented names against every real name across all files.

**Staff ages must be sourced, not drawn.** 2004, 2010 and 2017 shipped with ages
wrong by 10–27 years and nobody noticed for years. Use the bulk Wikidata SPARQL
query filtered on `occupation = American football coach` — it resolved 98 of 126
in one request. Do **not** lead with nflverse `players.csv`: 18% false-positive
rate, and career length cannot separate the collisions.

**Draft classes.** 2027 and 2028 from the bundle, 2029 and 2030 generated.
Potential comes from board rank, not from what the player became — that is
impossible for future classes and it means no hidden gems and no busts. Worth a
line in the Reddit post.

**Appearances.** Seed on a hash of the player's name so rebuilds do not reshuffle.
Apply the face registry **last**, over the top, and nothing after it. Family digit
only for players — the aging variant legitimately differs by season. Whole array
for staff. `_verified_keys` is locked: 104 players, 18 staff.

`reference/PGM3_PLAYER_ARCHIVE.json` covers 25,364 people and can supply or check
skin band. Its **light** calls are reliable at any source count; its **dark** calls
need 3+ sources. Check `era_certain` before trusting any era field.

---

## Gates

    python3 tools/pgm3_validate.py roster PGMRoster_2026.json PGMRoster_2021.json PGMRoster_2017.json PGMRoster_2013.json
    python3 tools/pgm3_validate.py staff  PGMStaff_2026.json  PGMStaff_2021.json  PGMStaff_2017.json
    python3 tools/pgm3_validate.py faces  PGMRoster_*.json

Plus every conditional pass, reported alongside the validator output rather than
after it.

`zero_pattern` is now **per position** for rosters. Expect it to report OLB
`manCover`/`zoneCover` against a reference union containing 2013 and 2021, which
populate that field with junk values in the 1–3 range. That is a known reference
defect, not your bug.

**Then stop.** The last gate is not automated: Ryan imports the file and plays it.
Every in-play report he has made on this project turned out to be a real bug, and
two of them were things every automated check had already passed.

---

## Standing rules

**Measure first, and bring the number to the question.** A question with a
measurement attached usually answers itself.

**Never invent data when real data exists.** An honest gap beats a plausible
invention.

**Assert on the match rate, not the output count**, wherever a fallback exists.

**Test every assertion against a deliberately broken record.** An assertion that
cannot fail reports success — three vacuous checks were found during the 2000
build, two of them by the build session auditing its own work.

**A guard must know the provenance of what it guards.** A floor or ceiling meant
for derived values will silently overwrite a sourced one and the output will still
look reasonable, because looking reasonable is its job.

**Say which commit you are holding** when you report a finding.
