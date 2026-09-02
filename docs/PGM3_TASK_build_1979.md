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
