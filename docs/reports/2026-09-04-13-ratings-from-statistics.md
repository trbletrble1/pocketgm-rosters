# Should ratings be derived from statistics? Measured, with a recommendation

**2026-09-04. Report 13.** Task 3 of three. This is a **decision for Ryan**; what
follows is the measurement and my recommendation, not a build.

Coverage data at `dataset/build-reports/stats-coverage-1950.json`.

---

## First: a parser bug that would have killed this on a false measurement

The first run of this measurement reported **0% of players have any 1950
statistic — including quarterbacks.** That is not credible, and it was the
instrument.

**StatsCrew emits `<tbody><td class="dt-left">1953</td>…` with no opening `<tr>`.**
Every stat table's rows are malformed that way, so a `<tr>…</tr>` regex silently
drops all of them. Fixed by splitting on `</tr>` instead of requiring `<tr>`.

**Two things worth recording.** The roster tables are *well-formed* — 41 `<tr>`
opens and 41 closes on Baltimore — so **the 1950 ingest is unaffected** and was
checked rather than assumed. And this is the **third instrument bug today**, all
found the same way: an implausible number treated as a question about the method.
Had it not been, this report would have concluded "1950 has no per-player
statistics" and closed the question wrongly.

## The measurement: 1950 statistical coverage by position, n=446

| position | n | any 1950 stat | % | what the row actually contains |
|---|---|---|---|---|
| QB | 22 | 22 | **100%** | Passing 22, Rushing 18 |
| P | 9 | 9 | **100%** | Punting 9 |
| TE | 33 | 33 | **100%** | Receiving 33, Scoring 26 |
| K | 13 | 13 | **100%** | Kicking 13, Scoring 13 |
| S | 12 | 12 | **100%** | Interceptions 9, Returns 8 |
| WR | 15 | 15 | **100%** | Rushing 15, Returns 15 |
| RB | 71 | 69 | 97% | Rushing 67, Receiving 61 |
| CB | 35 | 33 | 94% | Interceptions 29 |
| DE | 43 | 38 | 88% | *Defense and Fumbles 30* |
| MLB | 12 | 10 | 83% | *Interceptions 8, Fumbles 6* |
| OLB | 34 | 25 | 74% | *Interceptions 20, Fumbles 20* |
| DT | 58 | 40 | 69% | *Fumbles 34* |
| OG | 43 | 29 | 67% | *Fumbles 18, Kick Returns 10* |
| C | 20 | 13 | 65% | *Fumbles 12* |
| OT | 26 | 12 | **46%** | *Fumbles 12, Kick Returns 4* |

**Coverage is not the number that matters. Informativeness is.**

Ernie Blandin was a starting left tackle for Baltimore in 1950. His **entire**
1950 statistical record:

    Receiving             1 catch, 16 yards
    Kick Returns          3 for 31 yards
    Defense and Fumbles   2 fumbles, Tackle 0, Brup 0

**Nothing about blocking, which is what he was paid to do.** The table has a
`Tackle` column and it reads 0 — for him and for Otto Graham. Across the 165
players with a 1950 Defense-and-Fumbles row, the non-zero values concentrate in
the fumble columns.

*(Whether the NFL recorded tackles at all in 1950 is stated from general knowledge
and not measured here. What is measured: the column exists and reads 0 on the
players inspected, and no position's row carries a blocking or tackling volume.)*

**So the split is not 94%/46%. It is roughly this:**

    real per-player signal        QB P TE K S WR RB CB       ~200 of 446   (45%)
    a row, but nothing about
    the man's actual job          DE MLB OLB DT OG C OT      ~246 of 446   (55%)

That is the gap the original brief already recorded — *"statistics reach the
ball-touching positions; linemen and most defenders barely appear in a box
score"* — now measured on a real season rather than assumed.

## Recommendation: yes, and scoped — with the scope visible in the data

**1. Derive ratings only where statistics bear on the job.** For the eight
ball-touching positions the inputs are real and per-player: attempts, completions,
yards, touchdowns, interceptions, punts, field goals, returns.

**2. Store them as `derived` (§3.3), never `observed`** — recipe id, version, and
the input claim ids, so the value is reproducible and its staleness detectable.

**3. For the other 55%, the honest output is `unknown`.** Do not derive a lineman's
rating from a fumble recovery and a kick return; that is a number with the *form*
of a derivation and none of its substance, and it would be the worst kind of
value in this dataset — invention wearing a recipe.

**4. A rating for a lineman therefore belongs to the export**, alongside the 12,910
values it already invents and declares. That is not a failure. **A rating that
exists for quarterbacks and not for tackles is the dataset being honest about a
real asymmetry in the historical record**, and the manifest already has the shape
to say so.

**5. The recipe must take LEVEL from the consumer and ORDER from the statistics.**
This project's own precedent — *a published reference is an output, not a
specification* — has four recorded instances of a term being applied twice. Rank
players by production within position, map that rank onto the consumer's rating
distribution. Never fit a formula on the published files and then add a
statistical term on top.

**6. Gate it the way this project gates everything: the conditional check.** Split
the derived rating by the source statistic and confirm the groups differ. A rating
with a plausible distribution and no relationship to its input is the exact failure
the roster project caught three times, and it passes every other check.

## The limit I would not cross

**Ordering within a position is defensible. Ordering across positions is not.**

A 1950 quarterback and a 1950 guard cannot be ranked against one another from
statistics, because only one of them has any. A league-wide derived rating
distribution would be fiction dressed as derivation — and it would look
*more* authoritative than the export's honest invention, which is what makes it
dangerous.

So: derive within position, and let the export place positions relative to each
other under a rule it declares.

## What this would actually buy

The brief's framing was that this is what makes a season *playable* rather than
*plausible*, and that nobody else could do it. Both are right, with one
qualification:

**it makes 45% of a 1950 roster playable on real evidence, and the rest stays
invented.** That is still a change of kind — no existing historical roster file
has any player rated from what he actually did. But a claim that "1950 is derived
from statistics" would be true of the skill positions and false of the trenches,
and the difference has to travel with the number.

## Recommended next, if this is approved

1. Write the recipe as an export-side artifact with a version, and the
   position scope as **data** — the same shape as `position_map.json`.
2. Derive for one position first — **quarterback**, where 22 of 22 have passing
   volume — and run the conditional check before extending.
3. Report the conditional result before deriving a second position.
