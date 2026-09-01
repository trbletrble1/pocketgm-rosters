# 2000 season — final build log

Merged to `main` 2026-08-31 as `66d6e78`. All figures measured from the
shipped files, not from the build conversation.

    PGMRoster_2000.json   3,352 players
    PGMStaff_2000.json      453 staff
    PGMRoster_2004.json   3,023 players (republished, one record changed)

## Composition

| cohort | n |
|---|---|
| rostered | 1,690 |
| free agents | 638 |
| draft prospects | 1,024 |

32 teams (31 real + Houston), roster sizes **46–55**, median 52. Every team
fields a complete set of position groups; none is missing a QB, K, P, C or TE.

Staff: 53 head coaches, 50 each of offensive/defensive coordinators and
special teams, 150 scouts, 100 physios.

## What is sourced

**Rosters** decoded from Madden `.ros` binaries by `tools/rosdump.py`, written
for this build — table directory at `0x18`, field definitions at `+0x28`,
values as bit offsets into each record. This removed the Windows/Xtreme DB
Editor dependency. Verified field-exact against the matching CSV export.

**Attributes** quantile-mapped per position rather than copied; Madden's scales
do not match PGM3's at the low end. Direct-mapped fields verified at rho
0.997–1.000 within (cohort, position).

**Appearance** from `PSKI`/`PHCL`, anchor-tested at 19/20 light and 17/17 dark
before use. Skin and hair 96–99% sourced.

**Ages** prefer nflverse birth dates over Madden's stale values.

**Staff**: 31 real head-coach staffs with coordinators and special teams
sourced from contemporary team records. HC ratings fitted to career record
through 1999, weighted by games. **Birth years sourced for 124 of 128** real
coaches via a bulk Wikidata query filtered on occupation; 4 special teams
coaches with no birth year in any source take the role median and are tagged.

**Contracts**: 66 players carry true Over The Cap 2000 numbers.

## What is not sourced

| | scale |
|---|---|
| veteran contracts drawn from a model | ~95% (66 of ~1,300 anchored) |
| draft classes percentile-filled | ~22% of each class |
| scouts and physios invented | ~160 |
| Houston | entire 53-man roster, counterfactual |
| staff birth years derived | 4 of 128 |

## Dollar scale

The game has **no cap field** and does not know what year it is; the cap is a
fixed engine constant of ~$280M. Era-accurate 2000 dollars leave ~$225M of room
on every team and make the financial layer inert. All seven published files sit
on a **top-53 median of $197.4M within a $29k spread**.

This file: uniform **×3.5879** over `salary` and `guarantee`, landing on
**$197,399,997**. Zero contract inversions; the 66 sourced anchors keep their
proportions to 4.2e-07.

    payroll top-53   median $197.4M   range $189.3M–$213.3M   0 teams over cap

## Gate state at merge

- **roster** — ALL CLEAR against all seven published files
- **staff** — 1 deliberate failure: `duplicate names` reports Dick LeBeau twice
  (he held Cincinnati HC and DC simultaneously) and Jim Mora twice (two
  different men, father at IND aged 65, son at SF aged 39)
- **faces** — 8 head-family and 16 hair-style cross-season disagreements, on
  the **rostered** cohort, against 8 and 15 for the published files alone

## Deliberate deviations from the published files

| deviation | reason |
|---|---|
| OLB `manCover`/`zoneCover` gated off | where present the entire range is 1–3 against MLB's 38–92, and 62–100% of non-zero values are the fill value 1 |
| K/P contracts not inflated | median $2.68M sits inside the published $1.08–2.85M range; the correction shows in the tail, p95 $5.00M against a published median p95 of $6.43M |
| payroll spread 0.96–1.08 vs published 0.63–1.40 | real 2000 teams sat $0.2M–$2.1M under a $62.17M cap, every team within ~3% of the ceiling |

---

# Things a player will notice and may report as a bug

Ordered by how likely someone is to post about it. Each is a deliberate
decision with a measurement behind it, not an oversight.

**1. Mike Alstott is rated 70. Lorenzo Neal is 86.**
The fullback ruling is blocking-led: FB rating leans on lead blocking rather
than carrying. Alstott was a six-time Pro Bowler and the most famous fullback
of the era, and he is the single most likely bug report in this file. Neal
above Alstott is an ordering **no published file uses**. It is correct for how
the position actually functioned; it will still look wrong to anyone who
remembers Alstott running people over.

**2. Rosters are thin — 46 to 55, against 53 to 69 in the published files.**
Seattle carries 46. Every team is complete and fieldable (no missing position
group) but depth charts have gaps the published files do not, and a player used
to 2004 or 2017 will see empty slots.

**3. Houston exists and did not.**
Real men and real records, invented start date. The roster is unbalanced in a
way real teams are not: **4 receivers and 9 running backs**. This is the
clearest single piece of fiction in the file and should be named plainly.

**4. No team is ever cap-strapped, and none is unusually flush.**
Payrolls run 0.96–1.08 of the league median against a published 0.63–1.40. This
is closer to how a hard cap actually worked in 2000 — real teams sat within ~3%
of the ceiling — but it removes texture: there is no bargain-hunting team and
no team in cap trouble. This one is a genuine trade-off, accuracy against
gameplay feel, and worth flagging as such rather than defending.

**5. Kickers and punters are not millionaires.**
Median $2.68M against a real 2000 top-of-market of $1,071,167 for a kicker
(Jason Elam). Inside the published range at the median, deliberately short in
the tail: p95 $5.00M against a published median p95 of $6.43M, and 2010's
$12.59M. Anyone comparing files will see K/P cheaper here.

**6. Contract extensions behave differently.**
`PCYL` is years *remaining*, not total length, and this build is the first to
use that path. Extension negotiations may not match what a player expects from
the other files.

**7. Coach ages are right here and wrong everywhere else.**
2000's staff birth years are sourced. The published files' are not — 2010 ships
Sean Payton at 71 against a real 47, and Tom Coughlin at 43 against 64. A
player moving between files will see the same man at very different ages, and
**2000 is the correct one**. Logged as backlog item 0i.

**8. One 2004 player's face changed.**
Ted Ginn Jr., `Head2a` to `Head4a`, from applying the face registry across the
archive. Republished with 2000 so the two files agree.

**Two smaller things**, unlikely to be noticed but real: roughly 22% of each
draft class is percentile-filled because those players appear in no Madden
export, and ~160 scouts and physios are invented, as they are in every file.
