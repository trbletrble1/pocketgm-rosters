# 2026 build log

Built 2026-09-01 from nflverse `roster_2026` (who is on a roster) and the
Madden 27 launch spreadsheet (how good they are). Same architecture as 2000.

    PGMRoster_2026.json   2,635 records   1,888 rostered / 469 FA / 278 prospects
    PGMStaff_2026.json      288 records   32 x 9

Input checksums, so a later session can tell whether it holds the same data:

    madden_27_launch.csv  650b9463fee8b0fbb4bbb3a0b64f01e5d5ca9fbc526f2752d969251e0d55d2dd
    roster_2026.csv       44087b928376ef297c702ffed2c6b930185b4556105011baf70673b9a3073a2d

`sources/nflverse/` is gitignored, but the release URL is stable — the file
was re-downloaded mid-build and came back byte-identical.

---

## The join

    exact name              1,589
    exact + birth date         11    the 7 Madden namesakes, resolved on EXACT date
    nickname, prefix rule      11
    nickname, team+surname     10
    ------------------------------
    TOTAL                   1,621 / 1,695 active = 95.63%
    unmatched                  74    31 rookies, 43 veterans

**The brief's twelfth nickname pair was a false merge.** `Francisco Mauigoa ->
Francis Mauigoa` is two men: Francis Mauigoa is a Giants guard who matches
exactly, and Francisco Mauigoa is a Jets linebacker whose Madden row reads
**Kiko Mauigoa**. The prefix rule would have taken it — "Francis" *is* a
prefix of "Francisco" — and only the one-to-one assertion blocked it, by luck
of ordering.

A third tier (same team + surname + compatible position family) recovers ten
diminutives no prefix rule reaches: Michael->Mike, Tedarrell->T.J.,
Andrew->Drew, Julius->JuJu, Andru->Dru, Francisco->Kiko, Andy->Andres,
Jaylahn->JT, Nicholas->Nick. Zero ambiguous.

**The Excel epoch is 1899-12-30** and reproduces every nflverse `birth_date`
to the day. A year-level tolerance is NOT enough: Michael Carter and Michael
Carter II are both 1999.

**A normalised name is not unique on EITHER side.** Madden holds 7 namesake
pairs, the active pool 4, the free-agent pool 2. Tier 1 resolves two-sidedly.

**EA birth dates carry ~4.4% noise.** 71 of 1,621 pairs disagree; 70 of 71 are
the same name on the same team at a compatible position, gaps clustering on
1 day and 365/366 in BOTH directions (40 earlier, 31 later). Data entry, not
merges — and NOT a Jan-1 sentinel: 1 January appears 3 times in 2,362 (0.13%),
*below* chance, with nflverse at 0.14%. So birth date is authoritative for
SEPARATING namesakes and unreliable as a global gate.

---

## Decisions and their numbers

**Free agents — ruling D.** Madden record OR >= 2 years experience. 855
post-cut, 469 kept, 132 derived = 28% of the pool. (471 in the ruling; two
players appear ACT on one team and CUT on another, and the rostered record
wins.) Archive FA pools span 4.8%-37.7% of rostered, so pool size decides
nothing.

**RES included.** ACT+RES gives 55-68 per team, median 60, against a published
53-69. A flat 53 matches nothing in the archive. IR players read as ordinary
depth — PGM3 has no equivalent status and the published files do the same.
57 RES have no Madden record and join the derived tier, counted separately
from the 74 unmatched actives.

**No rating rescale.** Like-for-like on top-53, Madden's matched cohort reads
p10 65 / median 74 against a published 64 / 73. Two points is noise. A
near-identity quantile map would only import the published files' tie
artifacts. **Stated explicitly so a later session does not see a missing step
and add one.**
Name the cohort with every figure: the full Madden file reads median 71, the
matched-to-active subset 74. Same file, three points apart.

**Long snappers cut** (30 on active rosters). FB->RB, FS/SS->S, edge by team
front (16 teams 3-4, 16 4-3).

---

## Attributes — 95.0% of cells sourced

29,647 attribute cells: 28,178 sourced, 1,469 percentile-filled.

    tier 1  Madden 27 row               2,099 players
    tier 2  2025 JINX -> M27 scale        143
    tier 3  no source, percentile fill     117

**Two corrections to the attribute map**, both measured:

`trucking` is `TruckingRating`, NOT `BreakTackleRating`. Within position
against published trucking: RB .863/.417, WR .969/.619, TE .927/.594,
QB .643/.383. Anchor: Derrick Henry (247lb) reads Trucking 91 / BreakTackle
92; Christian McCaffrey (205lb) reads **67 / 93**. Trucking is running THROUGH
people; break-tackle includes evasion.
The position MEDIANS point the other way and cannot settle it — a per-position
quantile map forces output medians onto the target whichever column feeds it,
so only within-position ORDERING distinguishes them.

Three attributes the handoff leaves unmapped have named columns:
`skillMove`->`SpinMoveRating` (.885), `elusiveness`->`JukeMoveRating` (.827),
`blockShedding`->`BlockSheddingRating` (.608). `elusiveness` also scores .686
on `BCVisionRating`, which is already `vision`'s column — `JukeMove` is both
better and distinct, so no column is copied twice.

`ballStrip` and `discipline` stay DERIVED: their best correlate is
`OverallRating` (.666 / .652), which wins only through general player quality.
A column that correlates through overall quality is not a source.

**All 51 contested cells are sourced.** The rho-vs-`OverallRating` threshold
was withdrawn: applied to the direct-mapped attributes it rejects **speed for
cornerbacks at 0.24**. It measures whether an attribute DRIVES a position's
rating, not whether the column is real. Every corner is fast; their speed is
still measured. Replaced by degeneracy plus cross-version stability — and 26
of the 32 cells the threshold would have dropped are already sourced in the
2021 file at rho > 0.90 against the same column.

**Degeneracy is `max <= 10`, not `max - min <= 10`.** The precedent says a
rating whose ENTIRE RANGE SITS AT OR BELOW 10 is fill. The narrow-spread
reading refused CB speed (84-96) and WR burst (84-98) — real values in a
homogeneous population. It also runs on the RAW column, before `injuryProne`
is inverted, or every max reads negative.

**OLB manCover/zoneCover gated off.** Published OLB spans 1-3 and 1-1 against
MLB's 38-92, and 100% of value-1 records archive-wide in both fields are OLB.
Matches 2004, 2007, 2017; diverges from 2013 and 2021 by name and on purpose.
Gating it also leaves the CB/MLB/S quantile targets clean with no separate
cleaning step — the gate and the contamination are one problem.

---

## The refit

**Capped at 1**, with the governing constraint that no attribute's conditional
pass may fall below rho 0.95.

An uncapped solve routes almost the whole correction into each position's
largest coefficient — `kickAccuracy` is 1.040 for K and 1.078 for P, 1.8x the
next attribute — taking it from rho 0.995 to **0.441**. Every structural check
still passed. The stored rating is display only and the game recomputes it
from attributes, so that trades a cosmetic field for the one the engine ranks
kickers by.

    cap   rating |err| med / p90   attrs < 0.95   min rho
      1         1.67 / 7.35             0          0.960
      2         0.40 / 5.52             1          0.905
      3         0.25 / 3.65             3          0.860
      5         0.18 / 0.56             7          0.812

Cap 3 was the headline ruling and does NOT satisfy the constraint the same
ruling added. The p90 rating error of 7.35 is the price and is stated, not
buried. A coefficient-scaled cap was tried and is **dominated**: C=2 gives 1.32
median error with 4 attributes below 0.95, worse on the protected quantity
than uniform cap 1 at 1.67 with none. Negative result, recorded.

**The derived block must be built BEFORE the refit.** `ballStrip` at zero was
worth 5-6 rating points at DE/OLB/DT/MLB and the solver was trying to recover
a value that did not exist yet — pre-refit gap -4.5, max displacement 92.
Building it first took those to -2.2 and 37.

`assert_refit_bounds` could not see that: displacement medians read 1.0 across
every tier and provenance while one cell moved 92 points. **A median cannot
see concentrated damage**, which is why the constraint measures rho.

---

## Contracts

    median team payroll   $197.4M exact    team range $107.5M - $269.9M
    over the $280M engine cap   0          1-year deals 37.8%   max length 7
    guarantee/salary      1yr 0.06 -> 5yr+ 0.29, rising

**Payroll basis, pinned and reproducible:** rank by salary+guarantee, take the
top 53, sum salary+guarantee, median across 32 teams. Reproduces all eight
published files TO THE DOLLAR. Ranking by salary instead reads 2017 $20.4M low.

**Length satisfies three constraints, not the two the handoff names.** Ladder
4/3/2/1; 1-year share 37.8%; and within a years-pro bucket better players get
longer deals. Random assignment inside a bucket reproduces both marginals and
destroys that. Blend weights are FITTED per bucket, landing within 0.02.

**Power compression p=0.90 over the top.** Ranking on real money makes 2026
more faithful than any published file — team payroll tracks genuine roster
cost at **+0.67**, where 2013 reads **-0.57** and 2021 +0.08 — and real
concentration exceeds what the engine allows. Across 12 seeds the top team sat
at $279.1-281.1M and breached in 7. 0 of 256 published team-seasons breach it.

**No salary floor guard, deliberately.** Built min $2,171 / p1 $23,608 sits
inside the archive's own range (2017 ships min $1,012 / p1 $37,456), so a floor
would be a fix applied to healthy data — and a floor written for drawn values
fires on sourced ones.

**Divergence, stated not tuned:** team spread $162M against a published
$93-152M, because the mapping is more faithful, not less.

---

## Draft classes

**2027 and 2028 only.** 2029 and 2030 dropped — ~600 invented people with no
real names behind them. **This diverges from every published file**, which all
carry four, and needs a line in the Reddit post's "what's not real" section.
278 prospects against ~1,020 historically.

**Potential: rank-scaled PROBABILITY of a large gap, not rank-scaled
variance.** Measured on rostered players by the slot they were drafted at —
what they actually BECAME, not the published `potential` field, which was
itself built by slot-baseline-plus-career-raise and would only measure the
method:

    band       n   median  IQR  max   >=85       band        n  median IQR max  >=85
    1-10     382       83   11   98  40.3%       106-150   907      71  11  98  8.4%
    11-32    753       81   12   98  33.2%       151-200   852      68  10  98  4.7%
    33-64    901       77   12   98  22.2%       201-223   313      67   9  96  5.4%
    65-105   991       73   12   98  12.3%       224      2879      65  12  98  3.8%

**IQR is FLAT at 9-12 across every band and the ceiling is 98 everywhere**,
including undrafted. What falls with draft position is the MEDIAN and the HIT
RATE. Widening variance at the bottom would fit an assumption rather than the
data, and would quietly fill round six with decent players.

**CAVEAT, which must travel with the finding:** this measures ROSTERED
players, so busts are not in the archive to be measured. The flat IQR is
CONDITIONAL ON MAKING A ROSTER. It is still the right read for a CEILING — the
game simulates the bust when potential is not reached — but "spread is flat by
draft position" is false without the conditioning.

**The hole this fixes:** published prospects carry 0.0-0.1% with potential
>= 85 below pick 64, against a real rostered outcome of 4.9% at pick 106+.
No late steals at all. Built file lands 106+ at 5.4%.

Position weighting from measured late-hit clustering (C 8.7%, OG 7.6%,
QB 6.7% down to RB 2.2%, OLB 1.7%), K and P excluded as an artifact — kickers
are almost never drafted early, so every good one counts as a late hit.

**Gap bounded at 28, the archive MAXIMUM, not its p90.** The first cut gave a
rating-52 tackle a 94 ceiling — a 42-point gap, wider than anything in the
archive. A steal is a good player who slid. Non-hit gap lands median 7 / p90 13
/ max 23, matching the archive; the widening to p90 17 is entirely the
deliberate 5.6% tail.

Probability calibrated against the ELIGIBLE population: with the gap bounded,
only ~60% of 106+ prospects are rated high enough to reach 85 at all, so the
raw rate needs a ~1.67x scale.

---

## Staff

    ages   sourced 90   role-median 38 (TAGGED)   generated 160
    startSeason 1989-2026, 3% at the ceiling (published 1-5%)
    corr(age, startSeason) -0.961   (published -0.95 to -0.99)

**70.3% of named staff have a sourced birth year**, by role: ST 14 missing,
OC 13, DC 10, **HC 1**. That distribution is itself the finding — head coaches
are documented, special teams coaches are not, and a future build can predict
its own hit rate from it. The committed `coach_birth_years.csv` covers only
45.3% of this cohort because it was built for 2000, where most coaches were
long-established.

**17 refused rather than guessed**, and the refusals are the evidence the
occupation filter works: Tracy Smith reads *news presenter*, Sean Mannion
*boxer*, Brian Mason *politician*. That is the nflverse false-positive pattern
reproduced on a different source, so it is a property of name-matching, not of
nflverse. Also refused: Jim Leonhard, Al Golden, Aden Durde, Anthony Weaver,
typed only as "American football player". Several are certainly the right men,
but nothing separates them from the politician, and an unseparated collision
resolves to unresolved.
Note the soccer QID (Q628099, *association football coach*) is distinct from
Q42331263 and would have silently poisoned the set.

Kellen Moore is ONE entity (Q6385658) carrying two conflicting P569 statements,
1988-07-05 and 1989-07-12 — not two people. Taken as 1988 and tagged
CONFLICTED.

**Per-role field profile is MEASURED, never hand-listed** — 21 live fields for
the coaching roles, 18 for scouts, 14 for physios. A hand-written list is a
list of what its author remembered, and that is the bug that crashed the game.

`growthType` is donor-copied whole, matched on (role, potential - rating), so
the 50x rule holds by construction.

Tampa Bay has no DC (Bowles calls it); George Edwards fills the slot. **`note`
is NOT a staff schema field** in any published file including 2000 — the note
lives in `sources/staff_2026_promotions.csv`.

---

## Gates

Roster: 1 group fails, `[OLB] manCover/zoneCover`, the predicted reference
defect. Staff: ALL CLEAR. Faces: 2 groups fail, and running the gate WITHOUT
this file shows 7 of 8 head-family and 16 of 17 hair disagreements are
pre-existing. This build adds exactly one of each, the same player both times:
`chris brazzell|WR`, two different men collapsed because `norm()` strips "II"
— which the registry requires. Documented `name|position` weakness; fixing it
means adding team and era to the registry key, repo-wide.

    attributes vs source, within position   median rho 1.000 (all 28)
    appearance vs archive band              light->1-3 95.3%, dark->4-5 98.2%
    rating vs source OverallRating          rho 1.000 at all fifteen positions
    guarantee vs remaining length           0.06/0.10/0.12/0.25/0.29 rising

**Not run: the last gate.** Ryan imports the file and plays it.

---

## The last gate

Ryan imported the file and found three wrong faces: Aidan Hutchinson and Drew
Allar built dark and should be light, Myles Garrett built light and should be
dark.

Those three led to **891 lost lookups**, an entire unused `staff_faces` block,
an unread confidence field, **154 registry corrections across eight files**,
and a protection gate covering a quarter of what it claimed. **None of it was
visible to any automated check.**

That has now held for every in-play report on this project — the stamina fill,
the cap bug, Jordy Nelson, and this. Each time the automated suite was green
and each time the thing was real.

**The mechanism is worth stating, because "test it in play" is advice everyone
already agrees with and ignores.** The checks verify that values are
*structurally valid*, and every one of these defects produced structurally
valid values:

- A generated face is a valid face.
- A donor face is a valid face.
- A light-skinned Myles Garrett is a valid record.

Every family digit was consistent, every token was in the vocabulary, every
distribution sat inside the reference band, and the record count was right at
every step. **Only someone who knows what Myles Garrett looks like can see it.**

That is also why the fixes are structural rather than corrective. The three
players were symptoms; hand-correcting them would have left the other 888.
What went in instead was a match-rate assertion on the lookup, a translation at
the boundary, and an agreement floor on the source — so the next instance fails
loudly rather than substituting a default.

### What this build owes to that report

    891   lookups recovered by translating position at the lookup boundary
    2231  staff_faces entries, never read, now applied
    154   registry corrections, seven of eight published files touched
    291   face records rewritten
      2   verified faces found already drifted, unreported for years
     26%  the share of locked faces the protection gate can actually reach
