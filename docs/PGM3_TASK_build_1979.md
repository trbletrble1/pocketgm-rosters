# Task — 1979 season build

Build `PGMRoster_1979.json` and `PGMStaff_1979.json`.

Opened by the build session 2026-09-02 against repo commit `3e6f9a2`.
Rulings by Ryan (master session) as marked.

**Read first:** `CLAUDE.md`, `docs/PGM3_PROJECT_HANDOFF.md`,
`docs/PGM3_BUILD_FRICTION.md`, `docs/PGM3_PRECEDENTS.md`, and
`docs/PGM3_TASK_build_2000.md` + `docs/PGM3_TASK_2000_HOU.md` as the closest
analogue. Where this brief and the handoff disagree, **say so rather than
picking one** — that is an escalation, not a judgement call.

---

## What 1979 is

Last season of the 1970s. 28 teams. Pittsburgh win their fourth Super Bowl in
six years, beating the Rams 31-19. Staubach's final season. Montana is a rookie
third on San Francisco's depth chart. Earl Campbell runs for 1,697 yards.

PGM3 needs 32 team IDs, so **four franchises are invented.**

---

## Settled — do not re-derive

| item | state |
|---|---|
| Team ID mapping | Ruled. See below and the handoff's roster-record rules |
| Vacant slots | `CAR`, `IND`, `JAX`, `TEN` |
| Archive era gate | Ruled. Vote-presence, not `era_certain` — see below |
| Payroll basis | Median top-53 salary+guarantee = **$197.4M**, engine cap ~$280M |
| Contracts | Invented. No salary data exists before 2000 |
| Coordinator vacancies | Promote the senior real assistant, record in `note` |
| Scouts and physios | Generated. The standing exception to no-invented-humans |
| Head coaches | Always real, including in the free agent pool |

### Team IDs — city where a slot exists, lineage where it does not

    Houston Oilers   -> HOU    Earl Campbell displays as Houston
    Baltimore Colts  -> BAL    Bert Jones displays as Baltimore
    vacant: CAR, IND, JAX, TEN

Recorded in full in the handoff on 2026-09-02; three published files depended on
it and it had never been written down. **The Colts invert between 1979 and
1986** — real in `BAL` here, real in `IND` there, with the other slot invented
in each. Same rule, different answers, because the franchise moved.

### The archive era gate — ruled 2026-09-02

`reference/PGM3_PLAYER_ARCHIVE.json` is the appearance source. The
**`1979-1980` file is the archive's strongest single source**: 1,999 players,
1,999 edited, the only file of 42 at 100%. 1,921 entries carry a vote from it,
against a 1979 league of roughly 1,260 rostered players; 93.4% unanimous.

**Take era membership from the presence of a `1979-1980` season vote. Do NOT use
`era_certain` or `first_seen`/`last_seen`.**

```python
in_era = any(v['src'] == '1979-1980' for v in entry['votes'])
```

The window is a derived field with a known defect on exactly this cohort — the
`stock` flag is keyed on name alone, so genuine 1979 men with modern namesakes
get a window built from files that do not contain them, and `era_certain` reads
`True` anyway. D.D. Lewis reads 2004-2009. Full mechanism and measurements in
`PGM3_AUDIT_BACKLOG.md` item 18.

**Owed:** the position-aware re-test against the full ultimate70s rosters. The
archive-side half is done (name+position frees 59 of 338; recovers 29 of the 33
PFR-confirmed genuine players). The 33 is a floor — PFR stat tables cover only
the 1,144 men who recorded a stat.

---

## Sources

**Ryan fetches. The build session does not** — PFR is 403 from this transport and
`ultimate70s.com` has not been tested from it. Ask; do not try.

### Already in the repo at `3e6f9a2`

`sources/1979PFR/` — all 28 team pages, the 1979 coaches index, the 1980 draft
listing. Saved HTML, so no CDN-stale failure mode. Measured coverage of the 28
team pages:

| field | coverage |
|---|---|
| head coach + season record | 28/28 |
| defensive alignment (11× 3-4, 17× 4-3) | 28/28 |
| defensive coordinator | 26/28 — Cleveland and Detroit blank |
| **offensive coordinator** | **11/28** |
| named assistants with unit responsibility | 28/28 |
| points for/against + league rank, SRS/SOS, playoffs | 28/28 |

**There is no roster or starters table on a PFR team page.** The 17 missing OCs
are a real feature of 1979, not a research gap; every one has a real offensive
assistant on the same page to promote.

### Needed from Ryan

1. **`https://www.ultimate70s.com/nfl_roster/{CODE}/1979/N`**, one per team —
   the only source giving the full 45-man roster. Anchor-check before trusting
   it wholesale; it is a fan site.
2. **PFR coach pages** for career records through 1978. The season coaches index
   is **confirmed unusable** for career records — do not re-try it.
3. **1981, 1982, 1983 draft pages** (1980 is already in the repo).

---

## Namesake landmines specific to this file

Four documented traps land in 1979 at once. Handle deliberately; do not discover
them at gate time.

| person | 1979 role | the trap |
|---|---|---|
| **Frank Gansz** | Cincinnati (ST/TE) | Sr./Jr. — malformed three different ways across 1986/2004/2007. Sr. is the 1986 KC and 2000 JAX coach |
| **Jim Mora** | Seattle (DL) | Sr./Jr. — registry holds Sr. in `staff_faces_1986`, Jr. in `staff_faces`; the name-alone key cannot express it |
| **Dick LeBeau** | Green Bay (DB) | Documented validator false positive on duplicate names |
| **Bill Belichick** | NY Giants (def. asst/ST) | Earliest appearance in the archive by seven years |

On the player side, the residual same-position namesakes from the archive
re-test are **D.D. Lewis (OLB)**, **Stanley Morgan (WR)** and **Kellen Winslow
(TE)** — Winslow being the canonical father/son case the handoff already names.

---

## Build order

Follows the handoff's order. Steps 1 and 4 are the ones with open questions.

**0. Docs.** Done 2026-09-02 — this file, the team-ID rule, backlog item 18, the
archive-cohort amendment, and the stale era-scale line deleted from the 2000
brief.

**1. Anchor-check ultimate70s.** Pittsburgh, Houston, San Francisco, Tampa Bay
first. Check roster against the PFR stat tables, and jersey/position/games
agreement. **Report the number before going further.**

**2. Cohort and positions.** 28 real teams → modern IDs. Check the CB/S ratio
against the published band (1.06-1.30) before moving on.

**3. Appearances — early, not last.** From the `1979-1980` archive file under the
vote-presence rule. Run the conditional pass the moment they are built.

**4. Ratings and attributes — SOURCE FOUND 2026-09-02.** An earlier version of
this brief said no attribute data exists for 1979 and named ratings the build's
biggest unknown. **That was wrong** — it read the archive's schema (skin band
only) instead of the source file. `1979-1980SAVEGAME.DAT` carries **height,
weight, jersey, years pro and eleven attributes**: Speed, Strength, Agility,
Jumping, Stamina, Tackle, Coverage, RunRoute, KickPower, PassArmStrength,
Durability. See the precedent "a file checked for one field and found wanting
has not been checked."

Anchor test passes — Dorsett 98 speed against Payton 89, Stallworth/Carmichael/
Swann/Largent top the route runners, Blount top corner coverage, Lambert 92 and
Ham 90 top the tacklers, Bradshaw 90 and Staubach 86 top the arms, Stenerud and
Moseley top the kickers, kickers 39 speed against receivers 87. Real per-player
signal, not positional defaults.

Maps to roughly half of PGM3's live attributes, including the physical half.
The remainder still needs percentile fill. Ratings are now a **filtering and
merging problem**, not a derivation problem.

Still owed in the proposal: how players with **no 2K5 record** are handled
(~18%), and whether that cohort correlates with obscurity or is random.

**4a. THE MEASURED PROPOSAL — 2026-09-02, brought before building, per the ruling.**

*The source.* `NFL79.ros` `POVR` covers **97% of the 1,408 spine** (1,114 with the
2K5 save too, 256 alone). **17 players have no data of any kind** — named below —
and **69 of the 256 rest on one modder's opinion alone** (in NFL79.ros, not in the
2K5 save, no 1979 stat line). Prospects: none carry a rating; draft classes are a
separate step.

*The anchor, formal.* 1979 All-Pro team from Wikipedia, 53 matched to NFL79.ros:
**median 94th percentile within position, 3 below the 75th** — Rick Upchurch
(69%), Tony Nathan (65%), Ira Matthews (41%), all return men whose All-Pro
selection was for returns. The source knows 1979. (Bradshaw 99th, Payton 99th,
Campbell 96th, Blount 98th, Ham 98th, Greene 97th.)

*The scale.* PS2-era inflation: median 79, 8.5% at 90+. Per-position quantile map
onto the six-file union, shifts −3 (QB, K) to −12 (FB, DE). The documented traps
behave: Ray Guy 99 → published-P 92, Moseley 99 → 93, Payton 99 → 95, Campbell
88 → 88. **The FB cohort, located by the handoff's named fullbacks** (Leach, Kuhn,
Neal, Alstott, Richardson, Strong, Reece, Juszczyk, Ricard — 22 appearances at
position RB across the six refs): **rating median 71, ceiling 86**, with Leach and
Kuhn at 45 in 2010 confirming the documented floor. So **Riggins 95 and Harris 93
map against ~86, not the RB pool's 94.** Median percentile within RB is 59% at
n=22 against the handoff's 28% on a fuller cohort — the named list is biased
toward the famous ones, so the ceiling is confirmed and the percentile is not.

*Attributes — THE SPREAD RULE IS THE BUILD, NOT AN OPTION.* Measured: `NFL79.ros`
is a **narrower source than Madden 27 at nearly every position and attribute.**
Source p5–p95 width against the six-file published union:

    RB speed   5 vs 30   6.00x        TE speed    9 vs 34   3.78x
    CB power  13 vs 38   2.92x        QB power   15 vs 39   2.60x
    DE speed  14 vs 36   2.57x        QB speed   19 vs 40   2.11x

The 2026 defect (item 25) was a 2.4x stretch at ONE position. 1979 is at or above
1.4x on **26 of 29** position/attribute pairs measured. A plain per-position
quantile map would manufacture floors across the entire file — the 2026 bug,
everywhere at once. **Width from the source, level from the pool**, at every
position, is the only map that can be run here. The 2K5 save cross-checks
physicals (speed r=+0.84, tackle +0.89, weight +0.97 on 1,132 shared).

*The 69 single-source, no-stat players are real ratings, not filler.* 26 distinct
`POVR` values, the mode held by 6; attribute distinct-value counts (31–38 of 69)
match a random 69 from the rest of the spine (29–40). They sit lower (median 73
against 80) because they are backups — 12 OG, 8 DT, 8 OT. **Accept `POVR`, flag
as single-source.**

*Ordering — INCONCLUSIVE, and stated as such.* PGM3 position weights applied to
the 2K5 attributes, Spearman against `POVR`: S 0.51, WR 0.54, CB 0.49, MLB 0.48
where the 2K5 fields cover 53–75% of the weight mass; QB 0.12 at 21%, K/P ~0 at
~31%. **Agreement tracks coverage, so this measures the 2K5 file's reach, not the
source's order.** It supports the order where it can see it and says nothing
where it cannot. (A probe printed "source ORDER is fine" over these numbers —
retracted; second instance today of a verdict written into a print.)

*Production data, per position.* Stat lines exist for 92–100% of every skill
position, 83–87% of the front seven and secondary, **37% of the offensive line**
— Ryan's prediction exactly. 282 players (20%) have no stat line, 157 of them
linemen. A stat-based rating is a cross-check for skill positions and nothing
for the line; `POVR` is the rating source at every position.

*The 17 with no data of any kind:* Ronnie McCartney (ATL LB, 16g), Joseph Shipp
(BUF TE, 16), Billy Thompson (DEN DB, 16), Timothy Stokes (GB OT, 16), Donald
Westbrook (NE WR, 16), Thomas Seabron (SF LB, 16), Howie Kurnick (CIN LB, 15),
Philip Tabor (NYG DE, 15), Johnnie McDaniel (WAS WR, 15), Donald Schwartz (NO
DB, 14), Sidney Justin (LAR DB, 13), Walt Landers (GB RB, 9), Art Whittington
(OAK RB, 9), Steve Stewart (GB LB, 3), Phillip Wise (MIN DB, 1), Richie Szaro
(NYJ K, 1), Deac Sanders (PHI DB, 1). **Hand-rate from position and games, and
log each.** Billy Thompson was a Pro Bowl safety; do not let him fall out.

*The step-2 gate, run early — CB/S is OUT OF BAND.* `NFL79.ros` rostered: CB 120,
S 118, **ratio 1.02** against the published 1.06–1.30 (1986, the nearest era
file, 1.11). The position-mix table says it is a **corner shortfall** (−2.1 per
team against the published mean) rather than a safety surplus. The source's
positions are specific, so the handoff's fix — resolve generic `DB` through
Madden — does not apply; the labels are already Madden's. The 2K5 save, which
labels CB/FS/SS independently, arbitrates: **its 28 verified team blocks give
CB/S = 1.28, inside the band.** Two independent 1979 sources disagreeing means
**labelling, not the era** — the NFL79 modder calls more men safeties than the
2K5 modder does, and all **53 individual disagreements** on the shared 192 DBs are in
`wip/cbs_disagreements_1979.csv` (33 NFL79=S/2K5=CB, 20 the other way). **A recommendation was made here and is RETRACTED.** "Take the 2K5 label where
the two differ" was written before the 20 names in that direction were read.
They include **Roger Wehrli, Raymond Clayborn, Lemar Parrish, Neal Colzie** —
corners, three of them Pro Bowl or Hall of Fame corners — whom the 2K5 modder
labels FS. The rule would have moved Wehrli to safety. **A third signal settles most of it.** Wikipedia's career position for the 53,
via the API: **supports the NFL79 label 24 times, the 2K5 label twice, neither
never**; 27 give no call (blank, or just "Defensive back"). Wehrli, Clayborn,
Parrish and Colzie all read "Cornerback" — NFL79 had them right, the 2K5 save
wrong. So the sources are NOT symmetrically wrong: **where checkable, NFL79.ros
is right 24:2**, and the 2K5 modder's DB labels are the unreliable ones — behind
an aggregate ratio that sat comfortably in band. A ratio in band is not evidence
the labels under it are right.

**Recommendation, needing a ruling:** take NFL79.ros's DB label everywhere. The
residual hand list is the 27 no-calls in `wip/cbs_disagreements_1979.csv` —
and given the 24:2 prior, only the **16 where NFL79 says S and the 2K5 save says
CB** carry real risk (the direction that would lose corners). One namesake leaked
into the Wikipedia join — the Jets' Bobby Jackson resolved to a coach of the
same name — and produced a no-call, so it did no harm; flagged. The out-of-band
1.02 then stands as **the era as this modder saw it**, with 16 men to check.

*Six teams carry two or more kickers* (NYJ four: Leahy, Jacobs, Linhart, Szaro
— footballdb confirms all four played) and New Orleans two punters. Real
mid-season churn, not filler; the mover rule (games, then block, then hand)
already covers it.

**APPROVED as proposed (Ryan, 2026-09-02):** hand-rate the 17 with no data; accept the 69 single-source, flagged; take NFL79.ros's DB labels with the 16 hand checks; width from the source, level from the pool, at every position. Bring the 16.

**5. Contracts.** Invented, scaled to the $197.4M top-53 constant. Era-accurate
ratios and orderings; the dollar scale alone comes from the engine. K/P ceilings
from the era's real market, not from the published files — they carry a
documented inflation defect.

**6. Staff.** 9 per team × 32. Real coaches; promotions logged in `note`.

**7. The four invented franchises** — `CAR`, `IND`, `JAX`, `TEN`. See below.

**8. Draft classes 1980-1983**, then the face registry **last**, then all gates.

---

## The 2K5 source file — structure, and the filter that falls out of it

**File position encodes team.** VERIFIED 2026-09-02 against all 28 full
footballdb rosters (1,438 players) — not against PFR stat-line players, which was
the earlier and weaker check. **Zero overlapping blocks.** Widths 50-53.

    team                   lo    hi   w  cover      team                   lo    hi   w  cover
    st-louis-cardinals      0    52  53   74%       new-york-giants       954  1003  50   67%
    atlanta-falcons        54   105  52   80%       new-york-jets        1007  1059  53   74%
    [STOCK]               106   158  53    -        oakland-raiders      1060  1111  52   73%
    buffalo-bills         159   211  53   75%       philadelphia-eagles  1113  1165  53   82%
    [STOCK]               212   264  53    -        pittsburgh-steelers  1167  1216  50   83%
    chicago-bears         265   317  53   77%       los-angeles-rams     1219  1271  53   73%
    cincinnati-bengals    318   369  52   83%       san-diego-chargers   1274  1324  51   78%
    dallas-cowboys        371   423  53   77%       san-francisco-49ers  1325  1376  52   72%
    denver-broncos        424   476  53   80%       seattle-seahawks     1378  1429  52   82%
    detroit-lions         477   529  53   78%       tampa-bay-buccaneers 1431  1483  53   85%
    green-bay-packers     530   582  53   64%       houston-oilers       1484  1535  52   68%
    baltimore-colts       584   635  52   80%       washington-redskins  1537  1589  53   78%
    [STOCK]               636   688  53    -        cleveland-browns     1590  1640  51   81%
    kansas-city-chiefs    689   740  52   85%
    miami-dolphins        742   793  52   74%       [1641-1673] tail
    minnesota-vikings     796   847  52   82%       [1674-1943] STOCK 2004, five blocks
    new-england-patriots  849   900  52   82%       [1944-1997] SECOND PITTSBURGH, novelty
    new-orleans-saints    901   953  53   80%

**Three interior STOCK blocks** sit inside the sequence at 106-158, 212-264 and
636-688 — 53 slots each, zero 1979 players. The 2K5 base carries more team slots
than 1979 had teams; the modder left three unedited.

**`nfl2k5.py` decodes no team pointers**, so this index structure is the only
team signal the file carries. It is what makes the source usable per team, and
it resolves namesakes: scoping a match to the team's own block removed a
Pittsburgh name that name-only matching had placed in Miami's block.

**An earlier version of this table was measured with a sliding window anchored
at multiples of 54.** That window reports 54-wide blocks whether or not they
exist — the measurement contained its own answer. Real starts are not at
multiples of 54; the widths were roughly right and the alignment was an
artifact. **Blocks are internally position-ordered** (CB, DE/DT, FB, FS, G, ILB,
K, OLB, P, QB, RB, SS, T, TE, WR, C), so a team begins where that sequence
resets. That detector is derived from the data rather than imposed on it.

### Coverage, and the cohort with no 2K5 record

**1,107 of 1,438 rostered players, 77%**, appear in their own team's block.
Per team it runs 64% (Green Bay) to 85% (Tampa Bay, Kansas City).

**The missing cohort correlates with obscurity, measured — it is not random:**

    games played    present   absent   absent rate
       1 - 4            59       75        56%
       5 - 9            82       61        43%
      10 - 13          157       34        18%
      14 - 16          809      161        17%

Absent median 13 games against present 16. The 2K5 blocks hold ~52 slots and a
1979 roster with churn runs to 60, so the men who fall out are the ones who
played least. **Filling this cohort from position and games played is therefore
defensible** rather than a guess at a random hole.

**But the correlation is not the whole story: 161 absent players started 14-16
games.** A 17% floor persists across every games band, so obscurity explains the
gradient, not the entire gap.

### `1979-SB-XIV.ros` is the SAME roster as `NFL79.ros`, not a second one

Evaluated 2026-09-02. It looked like independent corroboration and is not.

| | |
|---|---|
| shared names | **2,038 — the entire name set of both files** |
| in one file only | **0 / 0** |
| `PTAK`, `PWGT`, `PAGE`, `PSTR` identical | **100%** |
| `PSPD` identical | 99.8% |
| `POVR` identical | 98.4% |

**Weight by lineage, not file count.** Two files agreeing at 98-100%
value-for-value is one vote, not two, and the cross-file test that gave
r = +0.84 against the 2K5 save gives nothing here.

**The two real differences, both deliberate revisions:**

- **A different invented franchise.** `NFL79.ros` has Charlotte and Memphis;
  SB-XIV renames the slots and carries **Memphis and Honolulu**. Confirms these
  four teams are the modder's own invention, not a fixed historical set.
- **A quarterback rebalancing pass.** 32 ratings changed and they are almost all
  QBs, all upward: Bert Jones 77->89, Stabler 81->89, Landry 76->84, Theismann
  84->91, Dickey 77->83, Manning 81->87, DeBerg 79->85, Grogan 84->89. Jim
  Jensen 86->77 is the only large fall.

**Use `NFL79.ros` as the primary and treat SB-XIV as a variant.** Where they
disagree the difference is a judgement call by the same author, not evidence.
Bert Jones is the case that matters: 77 against 89 for a man who played four
games in 1979.

**CORRECTION to an earlier inference.** Neither file carries Biletnikoff or
Tarkenton, and that was read as two independent modders converging on a
convention. **They are one file, so it is one vote.** The conclusion that both
men need a hand-assigned rating is unchanged; the evidence for a *convention* is
weaker than it looked.

### Contamination: the positional filter clears the tail and NOT the blocks

Three kinds of junk sit in the tail region, index 1674 onward:

- **Stock 2004 players** — David Carr, Jeff Garcia, Jared DeVries, Lewis Sanders
- **Joke entries** — Chris Berman at 99 arm strength, Mel Kiper at receiver,
  "Arquette Steve-O", "Gay Flex"
- **Placeholders** — "Steelers Center", "Steelers Half Back"

Density of real 1979 players is 28-40 per block through index 1673 and **0 per
block from 1674 to 1943**, so discarding `index >= 1674` removes the tail with no
name lookup.

**It does NOT remove all contamination, and an earlier version of this section
wrongly said it did.** Modern players also sit INSIDE real team blocks. The 1979
Pittsburgh block at 1167-1216 contains **Chad Scott** (Steelers 1997-2006),
**Oliver Ross** (1999-2003), **Chukky Okobi** (2001-2006) and **Mike Schneck**
(1999-2004) — four 2000s Steelers among the 1979 ones.

**So footballdb membership is load-bearing.** The block answers *which team*;
only the roster answers *was he actually there*. Those are different claims, and
collapsing them into one is what produced the wrong version of this paragraph.
Use blocks for team assignment and contamination in the tail; use footballdb for
membership.

### The duplicate rule — measured, and it is NOT "take the higher"

55 duplicate names; 38 same-position. **28 of those 38 are 1979 Pittsburgh
Steelers**, in two contiguous blocks (~1167-1216 and ~1944-1997). This is one
duplicated team, not a modder revising marquee players across the league.

**"Take the higher record" splits 19/17 between the first and second block** —
a coin flip, so there is no later-and-better pass to prefer. And the trailing
block is the novelty roster: the same 54 slots holding "Steelers Center" and
"Arquette Steve-O". Taking the higher would import novelty data for the Super
Bowl champion in 17 of 36 cases.

**Rule: take the record inside the in-sequence team block. Discard everything at
index >= 1674.** Position and build still separate genuine namesakes — Kenny
King is a 285 lb DE and a 203 lb rookie RB, two men, and the RB is the Oiler.

*Kept because it is the worked example of "cut on the defect's signature, not
the category that contains it." The category is "duplicate names"; the signature
is "one team appears twice, and the second copy is a joke roster."*

---

## The cohort — SETTLED 2026-09-02

**1,408 real players across 28 teams.** Built by `tools/build_1979_roster.py`
from the 28 cached footballdb rosters into `wip/roster_1979_dedup.csv`.
Per team: min 45 (Pittsburgh), max 57 (Detroit, Green Bay), mean 50.3.

**This is the number the build is measured against.** Establish it once; do not
let it drift. 1,438 source rows minus 30 collapsed movers = 1,408.

### Movers and namesakes — split on COLLEGE

41 names appear more than once. College + age separates them:

| | n |
|---|---|
| genuine movers (same college, age within 1) | **30** |
| namesakes (different colleges) — kept as separate men | **10** |
| same-team namesake pair (Cleveland's two Robert Jacksons) | 1 |

**Position does NOT work as the discriminator here.** Larry Brown (OT/Miami/24
at Kansas City vs OT/Kansas/30 at Pittsburgh) and Gene Washington (WR/Stanford
at Detroit vs WR/Georgia at the Giants) share a name, a position and a season.
See the precedent "the field that resolves identity varies by dataset".

### The mover rule

**Most games played → the 2K5 block on an exact tie → hand call, logged.**
Resolved 28 by games, 1 by block (Henry Monroe, 3-3, to Green Bay), 1 by hand
(**Jerry Golsteyn to Baltimore** — 1 game each, no 2K5 record, started the
season there). A mover's `games` is the SUM across his teams.

**Stated plainly because it is thin: 15 of the 30 are decided by a margin of two
games or fewer.** Median margin 2.5. Neither the 2K5 block (10 agree / 7
disagree / 13 absent) nor footballdb player pages (collapse to "2 TMS", no team
order) give a better tiebreak. Each case moves one player between teams carrying
46-60, so it is not worth buying a source for — but it must not read as more
principled than it is.

### The 161 full-season absentees — a COMPOSITION mismatch, not obscurity

The 2K5 gap is 77% covered overall with a clean obscurity gradient (56% absent
at 1-4 games down to 17% at 14-16). **But the 161 absentees who started 14-16
games are not fringe players and not offensive linemen** — OL are 17% of the 161
against 19% of all full-season players, slightly UNDER-represented.

They are LB (25% of the 161), RB (18%), TE (8%). The cause is the 2K5 template's
slot allocation, not roster size — a block holds 52.2 slots against a 51.4-man
average roster:

    position   2K5 slots/team   real roster/team   surplus
    RB                    5.4                6.7      +1.3
    LB                    6.5                7.5      +1.0
    DT                    4.5                3.2      -1.2
    DB                    8.9                8.2      -0.7

**Build consequence (ruling, Ryan 2026-09-02): rate this cohort from games
played and the team's use of the position, NOT from a position-wide floor.**
They are surplus at positions the template under-allocates. Filling them from
the low end would systematically thin exactly what 1979 teams stocked most.

**OPEN — do not reach for a reason.** TE runs a 25% absent rate with no capacity
pressure against it. That does not fit the mechanism above and is deliberately
left unexplained.

---

## The four invented franchises

**Do not reuse the 1986 stories.** The Baltimore Stars, Jacksonville Bulls,
Tennessee Showboats and Carolina Rattlers are established in a published file
and a published Reddit post. 1979 is a separate counterfactual with no
connection to them. New names, new owners, new coaches, new reasons to exist.

**1979 is not the 1986 premise.** The WFL folded in October 1975 — four years
cold, not four months.

| slot | the real situation |
|---|---|
| `TEN` | **Memphis** sued the NFL for a franchise and lost in court |
| `CAR` | **Birmingham** won the WFL's only completed championship, folded in debt |
| `JAX` | **Charlotte** had a team that arrived already broken, moved mid-season from New York |
| `IND` | **Indianapolis** — no professional football, no WFL history. A different kind of story from the three that lost something |

Four separate stories, not one shared premise. The 1986 post's franchises read
as separate campaigns and that is deliberate.

### The pool — computed, not guessed. 308 men.

**Ruling (Ryan): real rosters stay real. Expansion teams are stocked ONLY from
men genuinely out of football in 1979.** So the pool is a diff, not the Madden
file's 372 free agents — those are one modder's opinion of availability.

**Method:** men on a 1978 footballdb roster and on no 1979 one.
`sources/1978footballdb/` (28 rosters, 1,439) minus the 1,408 spine = **308**.
261 carry a `POVR` from `NFL79.ros`.

**1977 was NOT fetched. Ruled 2026-09-02.** 308 with 261 rated covers four
rosters of ~50, and what 1977 adds is depth at the OLD end specifically —
Biletnikoff, Tarkenton, Kilmer, Hanburger — which is the shape Ryan moved away
from. He wants a handful of real names on ordinary rosters, not four teams of
old men. 28 fetches saved.

**Independent validation:** 117 of the 308 (38%) sit on the modder's four
invented franchises in `NFL79.ros`, and another 106 (34%) in his FA pool. He
computed the same diff from the other direction. Only 35 (11%) are on a real
1979 team in his file — see the accuracy note below.

### `wip/expansion_pool_1979_top40.csv` — the 40 with researched reasons

Researched individually via the Wikipedia API (reachable from the build
container with a User-Agent; `urllib` without one gets 403).

| status | n |
|---|---|
| career ended after 1978 (from career span) | 14 |
| injury — missed 1979 specifically | 6 |
| retired | 5 |
| **source conflict** | 3 |
| gap year, reason not in source | 2 |
| released, then CFL | 2 |
| released / left the game / career ended | 3 |
| unresolved | 7 |

The ones a franchise story can be built on:

    Charlie Waters   DB 30 ovr 94  torn ACL in a 1979 preseason game, back in 1980
    Cappelletti      RB 26 ovr 93  groin injury, whole year, traded to SD for 1980
    Roland Harper    RB 25 ovr 92  knee, whole year, back in 1980 blocking for Payton
    Too Tall Jones   DE 27 ovr 88  quit to box professionally, went 6-0, back in 1980
    Jim Otis         RB 30 ovr 90  retired after 1978
    Otis Sistrunk    DT 32 ovr 87  retired after 1978
    George Kunz      OT 31 ovr 81  back injury cost him 1978 AND 1979
    Ray Pinney       OT 24 ovr 80  injured all of 1979, back in 1980 at guard
    Andrusyshyn      P  31 ovr 81  waived behind Bob Grupp, signed in the CFL
    Tarkenton        QB 38    -    retired as the NFL's career passing leader
    Biletnikoff      WR 35    -    released by Oakland, played 1980 in the CFL

**Tarkenton and Biletnikoff are named exceptions (Ryan).** Both are in the 308.
Neither is in `NFL79.ros`, so neither has a `POVR` and both need rating by hand
or from another source — do not let them fall out for lack of a number.

### `wip/expansion_pool_1979_rest.csv` — the other 266, MEASURED ONLY

No inferred reason. Age band x 1978 games played, which is all the roster data
supports:

    age        fringe 1-7   part 8-13   full 14-16   total
    33+                 1          10           13      24
    30-32               7           6            6      19
    27-29              18          10           20      48
    <=26               72          38           65     175

221 of 266 carry a `POVR`. **Do not proxy a reason from age and games** — the
thing that matters (retired at peak vs released vs injured) is exactly what
those two fields cannot separate. Charlie Waters reads identically to a man
simply cut.

### Two accuracy notes on the sources

**`NFL79.ros` rosters 35 of the 308 on real 1979 teams — men who never played
that season.** 11.4%, so its team assignment is ~89% reliable for this cohort.
The list is heavily offensive line and camp bodies, consistent with the file
being built from a preseason projection (`PYRP` already showed it is a
season-START roster). Charlie Waters is the headline case: rated 94 on Dallas in
a season he missed entirely.

**footballdb's 1979 rosters omit some late-season men.** Three of the 42
researched — **Bo Rather** (Wikipedia: last 3 games for Miami), **John
Woodcock** (a Lion 1976-1980) and **Reggie Haynes** (Washington 1977-1979) —
appear on no cached 1979 roster. The 2K5 cross-check found the same shape
earlier: 88 real period players on real teams that footballdb does not list.
**So 1,408 is a floor, not a census, and a few of the 308 may not be available
at all.** Not repaired; recorded.

### The structural rule, from the 2000 Houston build

**The roster falls out of the franchise's situation rather than being designed.**
Houston 2000 had a GM with no scouting department, so he signed only players he
could already evaluate — which produced nine running backs and four receivers on
its own. Nobody chose the shape.

**Find the equivalent constraint for each of these four and let it shape who
they sign.** A constraint agreed first, a roster second. Bring the four
constraints to Ryan before building any roster.

**Every player is a real person.** Scouts and physios are the documented
exception. Head coaches are always real, including in the free agent pool.
There is no team-name field in the schema — `teamID` is the only team column, so
all naming is Reddit-post copy, not data.

---

## Before any push

    python3 tools/pgm3_validate.py roster PGMRoster_1979.json PGMRoster_1986.json PGMRoster_2000.json PGMRoster_2004.json
    python3 tools/pgm3_validate.py staff  PGMStaff_1979.json  PGMStaff_1986.json  PGMStaff_2000.json
    python3 tools/pgm3_validate.py faces  PGMRoster_*.json

Plus every conditional pass, reported alongside the validator output. **Then
stop** — the last gate is not automated. Ryan imports the file and plays it.

---

## Standing rules for this build

**Measure first, and bring the number to the question.**

**Report before writing.** The outcome changed six times in the last session,
including once where following an instruction would have wrecked 1,330 ratings.

**A contradiction between documents is an escalation, not a judgement call.**
That situation shipped a broken 2000 file.

**Never invent data when real data exists.** Leave the field empty and log it.

**Cut on the defect's signature, not the category that contains it.** A fix
scoped by position destroyed 52 real ratings last session; every assertion
passed and only a git diff caught it.

**Every check runs once against a population where it must fail, and once
against an empty one.** A green gate over an empty set reads identically to a
real pass.

**Assert the count on every keyed write.** `assert len(out) == len(inp)`.

**Say which commit you are holding.**


## DB labels — closed (2026-09-02)

Sequence: NFL79.ros CB/S ratio 1.02 (out of the published 1.06–1.30 band) vs the
2K5 save's 1.28 (in band) → the in-band source was recommended, then retracted
when the names inside it turned out to include Wehrli, Clayborn, Parrish and
Colzie filed at FS → Wikipedia career articles backed NFL79 **24 to 2**, leaving
16 with no call → Ryan settled four by hand (Laird, Jackson, Davis, Thomas: all
safeties) and ruled the remaining twelve source-assigned to NFL79 → a scripted
pass over the Wikipedia 1979 season roster templates, **anchor-tested 4/4 against
Ryan's four**, resolved ten more to safety and found two the framing had hidden.

**Final:** 14 of 16 safety (NFL79 correct), **1 cornerback (Lawrence Johnson,
CLE — NFL79 wrong, 2K5 right)**, **1 outside linebacker (Ricky Jones, CLE —
both sources wrong)**. Recorded in `wip/cbs_disagreements_1979.csv` under
`season_page_pos` and `resolution`. Take NFL79's DB labels for 1979 with those
two overridden.

## The 17 with no rating data — position refined, rating still unsourced

The season pages carry no depth chart and no starter marking, so **they do not
give a rating signal**; the 17 still need hand-rating. They do give jersey
numbers and finer positions for 14 of 17 (three are not named at all): Billy
Thompson DB→**SS**, Deac Sanders DB→**FS**, Don Schwartz DB→**SS**, Sidney
Justin DB→**CB**, McCartney/Seabron/Kurnick LB→**OLB**, Stokes OT→**T**, and
Phil Tabor DE→**DT** (his draft entry says DE — a conflict, low stakes).
Written to `wip/no_data_17_1979.csv` as `jersey` and `season_page_pos`.


## Step 4 — ratings BUILT 2026-09-02. Two things in the approved proposal were wrong.

`tools/build_1979_ratings.py`, output `wip/ratings_1979.csv`, 1,408 rated.

### The 17 with no data of any kind do not exist. The join was.

**Coverage is 100%, not 97%.** All 1,408 spine players carry a `POVR`. The 17
were an artefact of joining on the exact name string: the mod writes **Bill
Thompson, Tim Stokes, Don Westbrook, Joe Shipp, Phil Tabor, Sid Justin, Walter
Landers, Arthur Whittington, Ron McCartney, Howard Kurnick, Tom Seabron, Phil
Wise, Rich Szaro, Don Schwartz, John McDaniel**. The last one is the interesting
one: footballdb's **Deac Sanders** is the mod's **John Sanders**, and Wikipedia
confirms *John Maurice "Deac" Sanders*. Also recovered: Cleveland's **two Robert
Jacksons**, an offensive guard and a linebacker, which the mod disambiguates as
Robert E. and Robert L.

The join now runs three tiers, each reported: team+name (1,353), unique name
anywhere (21), and **team + surname + compatible position** (30). The third tier
is gated on position precisely because of the Robert Jacksons.

**No hand-rating is needed.** The approved instruction to hand-rate the 17 is
moot — there is real source data for every one of them.

### `PPOS` decoded, and it is why the source can answer the CB/S question

Not assumed — derived, by joining every code to the footballdb position of the
men inside it, and anchored on an assert that the code holding the top throwing
arms is the one the table calls QB. It is the standard 21-slot Madden layout,
`QB HB FB WR TE LT LG C RG RT LE RE DT LOLB MLB ROLB CB FS SS K P`. **Codes 16,
17 and 18 come apart as CB, FS and SS** — that is the whole basis for treating
NFL79.ros as a DB-label source.

### The out-of-band CB/S ratio was measured on the wrong population

|                                              | CB  | S   | ratio |
|----------------------------------------------|-----|-----|-------|
| every record in NFL79.ros (2,128)            | 181 | 154 | 1.18  |
| the mod's own 28 rosters (1,452) — *escalated* | 120 | 118 | **1.02** |
| **the 1,408 footballdb spine — what we build**  | 121 | 106 | **1.14** |
| the spine, after the two label corrections   | 122 | 104 | **1.17** |

The 1.02 reproduces exactly, so the escalation was not a mistake — but its cause
is **population, not labelling**. The mod carries **44 men on those 28 teams who
were not on a 1979 roster**, and 13 of them are safeties against 3 corners. The
spine filter removes them and the ratio lands mid-band. The label arbitration was
still worth running: it found two real errors. But the gate that triggered it was
never a labelling defect.

### The scale map

Per-position quantile of `POVR` onto the published six (2004, 2007, 2010, 2013,
2017, 2021, rostered only), fullbacks capped at the measured ceiling of 86. Median
shifts run **−3 (QB, K) to −13 (C)**, matching the proposal.

**Plotting position, not rank/(n−1).** The naive map sends each position group's
top man to the pool *maximum*, which manufactures exactly one 98 per group — 21 of
them, against the 8 to 19 a published file holds. `(i+0.5)/n` puts the best of 29
punters at the 98.3rd percentile instead. Same family as the 2026 stretch defect:
**an order statistic read off the end of a small sample.**

Top-end density, against the published band scaled to 1,408:

| threshold | 1979 | published band | |
|-----|-----|-----|-----|
| ≥90 | 65 | 49–91 | in band |
| ≥95 | 24 | 12–36 | in band |
| ≥98 | 6 | 6–12 | in band |

Median 71 against the published 69–72. The six 98s are Stallworth, Lambert,
Payton, Haynes, Staubach and Bradshaw.

**The traps land near the proposal's figures but not on them**, because the
proposal's numbers were taken with the naive map: Riggins 86 and Harris 86 exactly
as stated, Campbell 90 against ~88, Moseley 95 against ~93, Ray Guy 94 against
~92, Payton 98 against ~95. Stated rather than smoothed. The aggregate band test
is the stronger check and it passes on all three thresholds.

## Step 4 — attributes BUILT 2026-09-02. `wip/attributes_1979.csv`, 1,408 x 30.

**All 30 PGM3 live attributes are covered, and none is drawn from the player's
own rating.** That constraint is not stylistic: PGM3 recomputes rating from
attributes, so a rating-percentile fill would make a defensive lineman's rating
39% a function of itself — `blockShedding` alone carries **+0.52** at DE and DT.

**Every source field anchored before use.** Hannah, Upshaw and Shell top run
block; Largent, Swann and Stallworth top catching; Lambert and Ham top tackle;
Payton and Campbell top break-tackle; Klecko strongest; Ray Guy the biggest leg;
Moseley the most accurate; Fouts the best arm; Wright and Hayes top coverage;
Carmichael and Largent top routes.

**`PINJ` is durability, not proneness** — r = **+0.55** against games played in
1979. PGM3's `injuryProne` is the opposite pole, so it inverts. Measured, not
assumed from the field name.

**A 2003-era Madden export has no block-shedding, elusiveness or route field.**
Checked rather than assumed: every unidentified field with spread was correlated
against `POVR` among the 200 defensive linemen. `PIMP` reaches r = +0.91 and is
an importance value computed *from* the overall — circular, rejected. `PJEN`,
`PDPI`, `PDRO`, `PCON` and `PFMK` are near-constant; their "top five" is
alphabetical. The 2K5 save supplies `Coverage` and `RunRoute` for **1,133 of
1,408 (80.5%)**; the other 275 take the pool median for those three fields.

Where no field exists the attribute is built from anchored fields, never from
rating — `blockShedding` = mean(strength, tackle), `ballStrip` = tackle,
`releaseLine` = acceleration, `elusiveness` and `skillMove` = agility,
`discipline` = awareness. **The cost, stated: agility then drives three PGM3
attributes and awareness four**, so those source fields carry more weight in the
computed rating than they do in a published file.

**`power` is position-conditional.** For K and P the weight vector gives it
+0.59 against `kickAccuracy` +1.04, and there it means *leg*. Feeding a kicker
his bench press put Spearman against the rating target at **0.52 for K and 0.62
for P**; with `PKPR` they are **0.97 and 0.95**. Found by measuring, not by
reading the field name.

**Spearman of computed rating against the POVR target, by position:** 0.85 (RB,
where the fullback ceiling compresses the target) through 0.99 (C). Every other
position is 0.91 or better.

**Level and width behave as designed.** Medians land on the pool within a point;
p5-p95 stays narrower than the pool where the source is narrower — speed 59-94
against the pool's 53-99, intelligence 57-92 against 52-98. Width from the
source, level from the pool.

**Closing to the target.** A per-player uniform shift across that position's
weighted attributes, the 2026 stage-8 pattern: median k **-0.9**, p5-p95 -4.9 to
+3.8, |k|>10 on **2 of 1,408**. Residual after the shift: mean |computed -
target| **0.50**, above 1 on **34**, worst -9.5 where an attribute clamps at 1
or 99.

## Step 4 — potential BUILT 2026-09-02. `wip/potential_1979.csv`.

**`draftSeason` is on the 2026 game clock in every published file, not on the
file's own season.** The 2004 file's rostered players carry draftSeason 2007-2026.
Reading years pro as *(file year − draftSeason)* makes 2004's entire roster
negative and silently drops it, which is what a first pass here did — it produced
a curve built on 243 players instead of 1,990. With *2026 − draftSeason* the
2017 column reproduces the 6/4/2/0/0/0/0/0/0 the 2026 build used, exactly.

**The pooled curve, taken:** median headroom by years pro across the published
six is **4, 4, 3, 2, 1, 1, 0, 0, 0**. 2017 alone is steeper. 1979 takes the pool,
consistent with every other level decision in this build. The interaction with
rating is flat — at year 0 headroom is 4 to 6 across every rating decile, at year
4 and beyond it is 0 to 1 across every decile — so **years pro alone is
adequate** and no second term is warranted.

**`PYRP` is exact where it matters, and one too high where it does not.** Four
men from each draft class: 1976-1979 read exactly right (Montana, Winslow,
Anderson, Hampton 0; Campbell, Lofton, Newsome 1; Dorsett, Morgan, Walker 2;
Haynes, Largent, Muncie 3), and every class from 1975 back reads one too high
(Payton 5 for four seasons, Guy and Hannah 7 for six, Harris 8 for seven). A
clean break between the 1976 and 1975 classes. Corrected rather than carried,
though headroom is 1 or 0 by then so it costs at most a point.

The 2K5 save disagrees in the opposite direction — it has **no zeros at all**,
reading every 1979 rookie as 1 — so NFL79.ros is the source and 2K5 the check.

**Result:** potential median 73, max 99, headroom 0 on 317 and 4 on 480.
`rating == potential` on **23%**, inside the published 10% (2021) to 53% (2017).
The 99 ceiling binds on exactly one man, Mike Haynes at 98 with two years of
headroom. That is the field's observed range in all six files, not a guard of the
kind removed from the 2026 build.

## Step 5 — contracts BUILT 2026-09-02. `wip/contracts_1979.csv`, `tools/build_1979_contracts.py`.

**Measured from the published six, not invented:**

- **Length by years pro** is their own median: **4, 3, 2, 1, 1, 1, 1, 2, 1, 1** —
  a four-year rookie deal counting down, then short veteran deals.
- **`guarantee` / salary by remaining length** is their median at each length:
  0.06, 0.09, 0.08, 0.21, 1.25. Money still owed, collapsing as a deal runs out.
- **greed, loyalty and ambition correlate with nothing** — |r| < 0.02 against
  rating, age and salary in the published six. Reproduced as a distribution,
  deterministically, carrying no per-player meaning here because they carry none
  there. The opposite call to the attributes, and for the opposite reason.

**Sourced:** the floor. The **1977 collective bargaining agreement**, the one in
force in 1979, set minimums of $12,500 for rookies and $13,000 for veterans.

**The era departure, which is the point of the step.** The published six pay
kickers **1.36x** the file median and punters **1.16x** — above the field. This
project's own **1986 build inherited that wholesale: K 1.40, P 1.22.** In 1979
specialists were paid at or below the average. This build ships **K 0.83, P
0.80**. Backlog item 30.

**A first pass put nine quarterbacks ahead of Walter Payton.** That is a modern
league's pay table. 1979's marquee earners were quarterbacks *and* running backs,
so QB came down to 1.75 and RB up to 1.35; Payton now sits fifth, Dorsett eighth.

**The compression ratio is solved, not chosen.** It began as a judgement at 10x —
more compressed than the published six (17.8x to 36.9x), 1986 (26.9x) or 2000
(12.8x), which is the era claim, since 1979 had no free agency and the Rozelle
Rule held the top of the market down. It **broke the engine cap twice**: at 10x
Pittsburgh reached $293.3M and Dallas $285.5M, and 8x broke again the moment the
running-back multiplier was raised. Payroll tracks team quality, and those were
the two best teams in the league. So the tool now **solves for the largest ratio
that keeps every team under $275M** — it lands on **7.15x**. The median top-53
holds at $197.4M at every value, so the payroll constant does not choose the
ratio; the engine cap does.

| | 1979 build | published |
|---|---|---|
| median top-53 | $197,400,000 | $197.4M ± $29k |
| max team payroll | $275.0M | under the $280M engine cap |
| payroll spread, max/median | 1.39 | 1.23–1.38 |
| salary max/median | 7.1 | 17.8–36.9 |

**Stated cost, and it was tested rather than assumed.** Payroll tracks team
quality at **r = +0.82** against the published **+0.28 to +0.47**.

Ryan's instruction was to measure whether **service** explains the published
spread before accepting a divergence: a veteran on an old deal is a real
mechanism, and reproducing a real mechanism is faithful where manufacturing
scatter is not. It was measured, and **it does not.**

Service *is* real and strong in the published six, and it runs the **opposite way
to the guess** — salary relative to what rating alone predicts rises from **0.79**
in a player's first year to **1.50** by his seventh. Veterans are paid *above*
their rating, not below; the modern mechanism is a cheap rookie deal followed by
free agency, not an old contract going stale. But applying that curve at full
strength moves the correlation only **+0.82 → +0.77**.

What actually loosens the published files is **contract history the file does not
record**. Within one file, one service year and a five-point rating band, the p10
to p90 salary spread is **3.5x** (quartiles 2.0x / 3.5x / 5.4x across 170 cells
of 25 or more). Two identical players differ threefold in pay. That residual is
not rating and not service, and it cannot be reproduced without inventing it.

**So the deterministic version stands and the correlation is a stated
divergence.** The service curve was left out on the era argument as well: 1979 had
no free agency, so the modern veteran premium had no mechanism to work through.

## Step 6 — staff BUILT 2026-09-02. `wip/staff_1979.csv`, 252 records, `tools/build_1979_staff.py`.

**`NFL79.ros` carries a coach table nobody had opened.** 218 records, 68 fields:
names, ages, salaries, and per-unit coaching ratings (`CDEF`, `COFF`, `CMOT`,
`CKNW`, `CRQB`, `CRRB`, `CRDB`, `CRDL`, `CROL`, `CRWR`).

**It is contaminated, and the age field is what separates it.** The assistants
are a stock Madden pool from about 2007 — Bruce Arians reads 54 against a 1952
birth, Marty Mornhinweg 45 against 1962 (he was **seventeen** in 1979), Dick
LeBeau 70. **None of the fifteen tested fits 1979 or 2004.** The real head
coaches fit 1979 exactly: ten of ten on the first pass, then **27 of 28** across
the league, with Ray Perkins closed by the table's own `CAGE` of 38 against a
December 1941 birth.

**The `CHTY` head-coach flag is NOT the discriminator.** It marks 19 records,
includes **Dom Capers** and **Art Shell** — a Raiders *player* in 1979 — and
**misses Bill Walsh**, who is in the table at a correct age of 48. Age is the
discriminator. Taking the flag would have shipped two modern coaches and lost
the best coach in the file.

**Head coach ratings are the modder's own view**, quantile-mapped onto the
published Head Coach distribution: Shula 95, Landry 90, Noll 87, Grant 85, Miller
83. Median 69.5 against the published 70, range 32–95 against 32–95. The mod's
ratings correlate **+0.45** with 1979 win percentage, which is right — they
track reputation, not one season. A win-percentage rating would have made **Bill
Walsh the worst coach in the league** on a 2–14 first year.

**Coordinators are thin by era, not by failure.** 1979 teams mostly had no titled
coordinator; the head coach called the plays. Sourced: **3 offensive, 13
defensive, 15 special teams, 11 personnel** — Glanville, Schottenheimer, Collier,
Carson, Marion Campbell, Studley, Baughan, Wiggin, Hanner, Biles, Hawkins, Walton,
Lionel Taylor, Ed Hughes, Brinker, Urich.

**Scouts and physios are invented**, following the 1986 and 2000 builds, which do
the same. No 1979 source names a trainer. 70 of 252 records are sourced; every
row carries a `provenance` column saying which it is.

**The defensive front is NOT derived, and two routes were tried.** Roster
composition (linebackers minus linemen) made Atlanta, Green Bay and Cleveland
into 3–4 teams and left out New England and the Jets, who actually ran it — the
roster reflects who was signed, and the mod's `PPOS` assigns LOLB/MLB/ROLB
regardless of scheme. The season pages name no front at all: zero hits across 28
for "3-4 defense", "3-4 scheme", "3-4 front" and the 4-3 equivalents. **Every
team gets a 4-3**, the era's predominant front, and a wrong 3-4 is worse than a
uniform one.

## Step 7 — the four invented franchises BUILT 2026-09-02. `wip/franchises_1979.csv`.

184 men on four 46-man rosters, 124 to the free agent pool, from the 308 who were
genuinely out of football in 1979. **No real roster is disturbed, and it is
asserted rather than assumed**: the loader fails if any of the 308 appears in the
1,408-man spine. The pool's "real 1979 team" flag on Waters, Kunz and Pinney means
they were under contract, not that they played.

| | n | best | median | age | Southern | from the 40 |
|---|---|---|---|---|---|---|
| Memphis Southmen | 46 | 90 | 77 | 24 | 17 | 12 |
| Charlotte Hornets | 46 | 87 | 79 | 30 | 16 | 18 |
| Jacksonville Sharks | 46 | 82 | 68 | 24 | 19 | 3 |
| Indianapolis Racers | 46 | 94 | 76 | 26 | 11 | 9 |

The pool's own Southern baseline is 25%, so Jacksonville's 41% is a lean and not a
rule, as briefed.

**Ryan's ceiling ruling:** 1986's four invented franchises came out at 75, 79, 82
and 84 — Carolina's best player is a 75, the floor across all nine published
files. These four sit inside that, so a block of weak expansion teams is
precedented in the file that did exactly this.

**THREE DEFECTS, all caught by measuring the result rather than the intent.**

1. **Doctrine-first left Charlotte with no quarterback and Indianapolis with no
   centre.** The pool is whoever fell out of football, and that population is 47
   running backs and 46 linebackers against 14 quarterbacks, 10 centres and 6
   kickers. Scarce positions are now reserved round-robin **before** any doctrine
   runs. A weak team is a shape; a team with no quarterback is broken.
2. **"Cheapest first" silently meant "unrated first."** 47 of the 308 have no
   Madden record, and `povr` read them as zero. Jacksonville took **30 of 46**
   that way, including **Jackie Smith, Mick Tingelhoff, Emmitt Thomas, Chris
   Hanburger, Willie Brown and Jake Scott**. The cheap team got the Hall of Fame.
   Every ordering now goes through `rated_key()`, which holds the unrated out of
   the comparison instead of ranking them at the bottom.
3. **The fix over-corrected twice.** Splitting the unrated by doctrine — old to
   Charlotte, young to Jacksonville — left those two rosters *half* unsourced, 23
   and 21 of 46. Capping each at 12 fixed that but sent the overflow of old men to
   Memphis, pushing its median age from 24 to 27 and costing it the one thing its
   doctrine asks for. Memphis now takes old men **last**. Four self-tests hold the
   result: every team has a quarterback, centre, kicker and punter; every injured
   man is Indianapolis and only Indianapolis; no roster is more than a quarter
   unsourced; and Jacksonville's Southern share must exceed the pool baseline by
   30%.

**Biletnikoff is a Charlotte Hornet because the doctrine claims him** — released
by Oakland after 1978 is exactly Charlotte's profile — not because he reads
better there.

**The injury mechanic**, confirmed before use: potential holds the man's healthy
1978 level and the 1979 rating sits 14 below it. **69 veterans across four of the
six published files carry 10 or more points of headroom, up to 46**, so Charlie
Waters at 73 with an 87 ceiling is unusual but not malformed.

**47 men still need hand ratings** — 11 to 13 per franchise — because no Madden
file covers them. Split between men aged 22 to 25 with no NFL career yet and men
aged 33 to 39 who retired before the source's coverage.

## Step 7b — the 47 with no Madden record, RATED 2026-09-02. `wip/unrated_1979.csv`.

**Ryan's instinct to check the archive first paid.** 21 of the 24 old men are in
it — the 1958-1980 save holds 17, the GOATs save 13, overlapping on 9, and the two
are independent rather than copies. Only **Vince Papale, Pat Curran and MacArthur
Lane** needed hand ratings, their careers fetched rather than remembered.

**The archive gives eleven attributes and no overall**, so the overall is
calibrated: a per-position least-squares fit from those eleven onto Madden's
`POVR`, trained on the 1,133 men who carry both. The fit is reported beside every
rating because it varies a lot — **QB 0.78 and P 0.77 at the top, RB 0.44 and OLB
0.46 at the bottom**, mean absolute error 3 to 5 points.

**Three defects, each caught by reading the result rather than the code.**

1. **Applied raw, the model gave Billy Kilmer a 96 at 39, out of football**, and
   Jim Mandich — a backup tight end — a 90. The archive rates men at *career*
   level; the model was trained on men playing in 1979. **The fit supplies the
   ordering and the pool supplies the level**, which is the same rule the rest of
   this build uses. The right population is the pool's own rated men aged 30-39,
   39 of them, median 77 and p90 85.
   The league's own age curve runs the *other* way — median `POVR` rises from 74 at
   22 to 87 at 33 — but that is **survivorship**, and these men are the opposite
   selection. Conditioning on the league would have been the wrong population.
2. **The two archives are different scales** — GOATs reads 90 against 67 on
   stamina and 95 against 79 on durability — so a man read from one was not
   comparable to a man read from the other. It showed: Kilmer, from the era file,
   outranked Tarkenton, from GOATs. Both are now quantile-aligned per attribute
   onto the **1979-1980 season file**, which is both the right season and the
   scale the model was trained on. It holds only 1 of the 24, which is why the
   historical archives are needed at all. Kilmer fell from 94 to 85.
3. **The plotting-position defect again.** 23 young men stretched across the
   published prospect distribution handed **David Posey, a 22-year-old kicker, a
   93** — the band's ceiling — because he sorted first among six men who are all
   22. `(i+0.5)/n` instead of `rank/(n-1)`, exactly as in the rating map.

**The young 23 go through the prospect band**, measured over 3,353 published
prospects: rating p5 53, median 61, p95 75. The archive holds exactly one of them,
which is the confirmation rather than a gap — they have no career to have been
recorded. Ordered by **age**, oldest worst, because age is the only signal they
carry.

**Result:** old 24 at 55 to 90, median 76. Young 23 at 51 to 77, median 61.

**Papale is rated as what he was**, not as the story: three NFL seasons, primarily
special teams, and a **55** — the lowest of the 24. He is on Charlotte because its
doctrine picked him, and if he sits there as a reclamation that mostly does not
work, that is honest.

### Still to build

Draft classes 1980-1983, then the face registry, then all gates.
