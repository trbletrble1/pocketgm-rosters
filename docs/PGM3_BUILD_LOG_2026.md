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

## Positions — real depth charts, then a fitted convention shift

**The proportional allocator was scrambling the front seven.** Measured against
nflverse depth charts it put more than half of real MLBs at OLB and split real
ILBs almost evenly. It optimised the aggregate and never checked the individual.

nflverse ships `depth_chart_position` for **2800 of 2800** rows, so it is now
the position source, resolved **through the join** — a name-keyed lookup sent
Pooh Paul Jr. to a different real Chris Paul's depth chart and shipped an
off-ball linebacker at offensive guard.

**The two sources label differently, they do not disagree about who exists.**
Total front seven is in range under both (552 against a published 543-625), so
the gap is a convention difference: nflverse calls men DT and ILB that the
archive calls DE and OLB. Shares are **fitted to the published per-file ranges**,
not reused from the old fixed 0.25:

| shift | count | share | chosen by |
|---|---|---|---|
| OLB -> DE | 45 | 25.9% | heaviest |
| DT -> DE | 24 | 12.8% | lightest |
| MLB -> OLB | 24 | 15.9% | lightest |
| OG -> OT | fitted | — | heaviest |

Weight separates the shifted from the unshifted cleanly in every direction:
DT->DE median 280 lb against DT->DT 305; OLB->DE 270 against OLB->OLB 246;
MLB->OLB 222 against MLB->MLB 234.

Result: **DE 151, DT 146, OLB 144, MLB 110, OT 139, OG 128 — all six inside
their published ranges**, and unshifted rows stay exact (real DE -> DE 115/115,
NT -> DT 22/22, C -> C 92/92).

**Confirmation the shortfall was the cause:** free-agent promotions to fill
empty slots fell from **13 OLBs to zero**. The two remaining promotions are
punters, a genuine nflverse gap (no active punter listed for SF or LAC).

**Ranges are per-file sums.** Summing independent minima and maxima across
files overstates the span: it gave DE+OLB 286-337 where the real per-file span
is 296-331.

**Corrected figure.** The retired 241 lb OLB cut was chosen from a 97.7%
separation that does not reproduce. Against Madden's own edge/off-ball labels
a 241 cut is **90.2%** accurate and the best available cut (237) is 90.8%.

**Two bugs found here, both now asserted:** `stage_build` never wrote the file
(see the precedents), and promoted free agents kept `teamNum` 0, putting two
men on LAC #0 — no published file has a single rostered player wearing 0.

---

## Ratings — store the computed value

**The archive's invariant is that a player's stored rating is whatever his
attributes compute to.** Four published files hold it across **11,737 records**:
median 0.26, max 3.45, **zero** players more than 5 off. Two rulings had been
spent tuning a refit cap to trade stored-rating accuracy against attribute
fidelity. The trade did not exist — storing the computed value costs zero
displacement and zero conditional-pass degradation.

Confirmation the reconstructed weights ARE the formula: Najee Harris was
reported in play at 89. The file stored 80; the weights compute 86.9; storing
computed puts him at **89**.

Result: invariant holds at **max 0.50** (published max 3.45), and the file is
distribution-neutral — median rostered rating and p10 unchanged.

### The fill: one real player's whole vector, not twenty independent draws

Storing the computed value made the file honest about tier-3 inflation; it did
not remove it. DJ Herman, an undrafted rookie with no snaps, read 97 overall in
play on 99 speed, 99 burst and 99 agility.

**The root cause is independent draws.** Twenty attributes each drawn at
percentile p produce a player with NO WEAKNESSES, and a no-weakness player
computes far above p. Measured against 167 published RBs rated 60-66: their
median within-player spread is 53 points with 2 elite and 2 weak cells, and
**not one of the 167 carries ten elite cells.** Herman carried seventeen, with
one trough beside nineteen peaks.

Within-player spread is **flat across the whole rating range** -- 52 to 58 in
every band from 40 to 99 -- so a compressed profile is wrong at any rating, not
just a low one.

**Fix: draw one real player's whole vector** from the same position and rating,
then rescale onto the player's own rating. Structure comes across intact and
scaling is monotone, so the peaks and troughs survive. Same reasoning as
copying growthType whole to guarantee the 50x rule by construction.

**Two things the first attempt got wrong**, both caught by re-measuring rather
than by a gate:

- A +/-12 rating band picked uniformly let a rookie drawn at 83 take a 95-rated
  player's numbers wholesale and become a 98. Narrowed, and the vector is now
  rescaled onto the drawn rating.
- Copying a whole vector cannot produce a no-weakness player **unless the donor
  is one**. Herman then drew a genuinely elite back whose twenty cells ran
  72-99, spread 27 against a published 56, and rescaling preserved that
  flatness. Donors below their own band's 25th-percentile spread are now
  redrawn.

| tier-3 cohort (n=73) | before | after |
|---|---|---|
| computed rating >= 90 | 4 | **0** |
| players with >= 10 elite cells | many | **1** |
| median within-player spread | 24 | **69** (published ~56) |
| computed vs stored, median | -4.56 | **+0.03** |

DJ Herman: **97 -> 87**, spread 50, two weak cells, stdev 17.6 against a
published 14-16. His residual is the draw, not the fill -- `tier3_rating` gave
him 83, the top 1.4% of a 214-player undrafted-rookie pool. Unlikely, faithful,
and the remaining driver.

**The draw is conditioned on AGE as well as draft status and experience.**
Published undrafted rostered players:

| age band | n | median | p90 | >=80 |
|---|---|---|---|---|
| <=24 | 1348 | 62 | 70 | **1%** |
| 25-27 | 1562 | 65 | 76 | 5% |
| 28-30 | 716 | 70 | 83 | 17% |
| 31+ | 448 | 74 | 86 | **29%** |

Monotone in every column. The 80-rated undrafted player went undrafted years
ago and earned it since; he is not a rookie. Pooling them put a 24-year-old's
ceiling at 84 when his own cohort stops there only at the 99.4th percentile.

Drawn ratings now match the published distribution WITHIN band, which is the
check the pooled figure could not make -- the same pooling trap that has bitten
this build four times:

| band | published med/p90/>=80 | 2026 drawn |
|---|---|---|
| <=24 | 62 / 70 / 1% | **62 / 67 / 2%** |
| 25-27 | 65 / 76 / 5% | **62 / 76 / 6%** |

Nothing is crushed at the other end: the 28-30 and 31+ pools are untouched and
still reach p90 83 and 86.

### Sourceless rookies: the upside goes in POTENTIAL, not the rating

An undrafted rookie who has never played should not be a good player on day
one, however faithful the draw is to a pooled distribution. DJ Herman drew 84,
the maximum of a 156-player pool -- which will happen to someone in every build.

**Rating is drawn tight and low.** The zero-information pool (undrafted,
<=1 year, age <=24, n=1214) runs min 40 / p25 58 / median 62 / p75 65 /
p90 69 / max 98. The draw is truncated at p75: the long tail belongs to players
who earned it later, and is not available on day one.

**Potential carries the upside**, the same mechanism as the 2027 class and
MEASURED rather than reused from the pick-224 figure. Of 5,683 undrafted
players tracked across the published files:

| ever reach | rate |
|---|---|
| 80+ | **8.3%** |
| 85+ | 4.0% |
| 90+ | 1.3% |

Survivorship travels with it: these are players appearing in at least one
published file, so it is the rate among those who stuck. Ceilings are drawn
from the 393 peaks actually observed at 80+ (median 84, max 98) rather than set
to a constant. Potential is raise-only and the gap is bounded at the published
undrafted maximum of **26**, not its p90, per the Louis Nix precedent.

Result on the 54-player cohort: rating min 49 / median 62 / p90 68 / max 70;
gap median 3 / p90 17 / max 26; 8 of 54 reach an 80+ ceiling. **DJ Herman is
now a 65 with a potential of 91** -- an ordinary rookie who might become very
good, and you have to develop him to find out which.

Two honest notes. The realised hit rate is 14.8% against a target of 8.3%, but
n=54 gives that wide error bars (expected 4.5, sd 2.0), and some non-hits reach
80 through the ordinary gap draw. And the gap distribution is deliberately more
bimodal than the published one -- median 3 against 4, p90 17 against 9 -- which
is what a hit-rate mechanism produces and is the intended shape, not drift.

### The tails were the attributes, not the rating

An attribute set computing to 104 or to 18 is one the archive has never
produced. **Only FILLED cells were rescaled**; a tier-1 player carries real
Madden attributes and is left alone even when he lands outside the range.
Measured, the split is total:

| | filled share of rating weight |
|---|---|
| tier 1 outliers | **0.0%** |
| tier 3 outliers | **96-99.9%** |

Filled cells carry no source column, so the conditional pass does not measure
them and the repair costs it nothing. Scaling is monotone, so ordering within
each player survives, and cells are held inside the published per-attribute
range.

| | before | after |
|---|---|---|
| rostered below 40 | 13 | **1** |
| free agents above 93 | 4 | **0** |
| rostered above 98 | 15 | 15 (all tier 1, refused) |

**22 outliers refused and reported, every one tier 1 with zero filled cells** —
Garrett 102.7, Anderson 104.7, Parsons 102.1, Chase 100.6, and Ryan McCollum at
37.6 on the other end. Rescaling sourced data to hit a target is what this
project refuses; they need individual rulings, not a solver.

**Two traps recorded.** The rating must be computed from the STORED INTEGERS,
not the float attributes — `int()` truncates, and a rating computed from values
that differ from what shipped is not the invariant, it only looks like one
(Will Anderson Jr. was 5.7 adrift of his own attributes). And the rescale had to
aim 1.5 points INSIDE the range rather than at its edge, for the same reason:
nine players landed on 39 against a target of 40 purely from the rounding step
between the solve and the file.

**Nine players' attributes exceed the field ceiling of 99.** That is a schema
limit, not drift, and is reported apart from the invariant check.

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

**Divergence, measured and closed: payroll tracks roster quality weakly.**
Ranking on real `_TotalSalary` decouples payroll from rating the way real cap
situations do, and the file inherits that from the source rather than creating
it. The Madden 27 source itself, before the build touches it:

| real 2026 source, team level, top-53 by real money | Pearson | Spearman |
|---|---|---|
| real payroll vs mean overall | +0.300 | +0.328 |
| real payroll vs median overall | +0.171 | +0.206 |

Well below the published files under matched definitions. Two mechanisms were
ruled out rather than assumed:

- **The p=0.90 compression is not the cause.** Inverting it on the shipped file
  moves the figure by at most **0.045** across eight definitions, and every
  delta is *negative* — removing compression makes the correlation weaker.
  `compress_top` is monotone, so it reaches a rank statistic only through the
  nonlinearity of a top-53 sum.
- **No published bound is breached.** 2026 ranks 1st-3rd weakest of nine, but
  **2000 occupies the same territory under every one of eight definitions**
  (2000 ranks 1st-2nd). "Below the published minimum" holds under only 2 of 8
  cuts and is not a robust reading.

**Open, and not holding the file:** under median-based definitions the build
attenuates to **-0.030** against a source **+0.206** — a 0.24 gap, where
mean-based definitions lose only 0.06 and compression accounts for 0.03.
Something in the quantile map or the refit flattens the median measure
specifically. On the audit list, unexplained.

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
