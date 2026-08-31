# PGM3 — Rulings and Precedents

Judgment calls already made, and why. These aren't rules derived from the files — they're decisions where the data allowed more than one answer. A new session should follow them rather than relitigate.

If a precedent looks wrong, say so and make the case. Don't quietly do something different.

---

## Accuracy vs. matching the existing files

**Ship real numbers even when the published files don't.** Payrolls in 2004, 2010 and 2017 aren't scaled to their eras — 2004 runs $179M salary against a real $80.6M cap. That was never a decision, just contracts fitted to PGM3's ceiling with nobody checking. 2007 ships at ~$100M against a real $109M cap, and that's correct. Don't inflate accurate data to match a defect.

**But first check whether it *is* a defect.** Draft potential looked like the same situation — the handoff said busts should be busts, no file did it. Checking showed the files were right and the handoff was wrong. Verify before overriding.

**Observed range is not accepted range.** Min/max derived from three files describes those files, not what the game accepts. Keep real values that fall outside it:
- Lane Kiffin was genuinely 32 in 2007, below the observed staff floor of 36
- Josh McDaniels was 31 — the only value in that file outside the observed vocabulary entirely
- Dick LeBeau 70, Mike Stock 68
- Morten Andersen played at 47; Vinny Testaverde at 44
- Amobi Okoye was 20, the youngest first-round pick ever
- Matt Stover was pick 329 and Keenan McCardell 326, from 12-round drafts

If the game rejects a value, import says so immediately. That's cheap to find out.

---

## Contract ceilings — TESTED, none exists

**The game accepts contracts far larger than anything we have ever shipped.** Tested 2026-08-28 in a throwaway league built from the 2004 roster: salaries of $45M, $60M and $75M imported, displayed correctly, and were used in the game's own arithmetic — a $45M salary produced a $50.7M cap hit and $31.3M dead cap. Nothing was clamped or rejected.

The figures previously treated as hard caps — $27.6M salary, $34.1M eSalary, $40.9M eGuarantee — were **the donor file's highest-paid player at each field**, one record each, inherited through five builds and then written into the handoff as a limit. Vanilla's $30M was the same artifact from a different league.

**Ruling: there is no contract ceiling. Ship real contracts.** 2026 uses real modern salaries with no compression, and the phantom-cap-room problem that clamping would have caused does not arise.

`pgm3_validate.py` keeps the ceilings as parameters so an implausible value still gets flagged, but they are sanity guards set well above anything real, not limits.

**Round trip confirmed: salary, guarantee and length are preserved exactly** — all 3,023 matched players identical, including the $45M/$60M/$75M test contracts.

**`eSalary`, `eGuarantee` and `eLength` are game-computed outputs. Don't fit them.** The same export rewrote them league-wide (35%, 51% and 51% survival), including 565 players authored at eGuarantee 0 who came back nonzero. They track rating, so the game derives them from player value, which is why no screen shows them. Ship sane values for first-load validity and spend no build time fitting them. `rating` behaves the same way at 41% survival, independently confirming that the game recomputes overall from attributes.

**The wider lesson is already recorded above** under "observed range is not accepted range": five files agreeing to the dollar meant a shared ancestor, not a wall. This is the second time that rule has been vindicated and the first time it was tested rather than argued.

---

## Ratings and potential

**Potential is raise-only.** Draft position sets the baseline; career outcomes pull it up for players who exceeded their slot and never pull it down. Potential is a *ceiling*, not an outcome — a bust had the ceiling and didn't reach it. Lowering it conflates the two and bakes hindsight into innate ability. It also keeps late-round hits findable while not punishing a pick a real GM couldn't have called.

**Changing a field means rebuilding every field derived from it. Run `pgm3_validate.py` before shipping — always.**

2026-08-28, in the same session that rebuilt prospect potential: `potential` was changed for ~4,700 prospects across all five files and `growthType` was not rebuilt with it. The 50× rule ties them together — positive growth must equal `(potential − rating) × 50` — so all five files shipped broken. They had been clean before.

Every check that was run passed. Range checks passed, because both fields were individually plausible. The conditional checks passed, because the new potential values genuinely tracked career outcomes. **The defect lived in the relationship between two fields, and no single-field check can see it.** The validator has caught exactly this class since it was written, and it was not run before pushing.

Two rules follow:

1. **Before any push, run the validator with the file checked against the other four.** It takes seconds. This is not optional and there is no cohort or field small enough to skip it.
2. **When changing a field, list what derives from it before changing anything.** `potential` drives `growthType`. `rating` drives `potential`'s floor. `PCON` drives salary and guarantee proration. A field is rarely alone.

The reviewing session is not exempt from this. It made the error.

---

**Every player must be able to decline. `growthType` needs a negative portion.**

The published 2013 file shipped with no decline curve for any of its 2,531 veterans or 1,018 prospects — not one negative entry in the file. The visible symptom was a 52-year-old Tony Gonzalez still rated 97 after twenty simulated seasons. The other four files carry decline for every player, totalling a median of about −22,900.

The curve is 31 slots: growth in the early indices, decline from roughly index 8 onward. Onset and total are close to constant regardless of age — the game appears to apply the curve relative to age internally rather than the array being age-indexed. There is a dominant pattern but real variation around it (roughly 2,300 distinct decline patterns across the four healthy files), so decline should be drawn from the donor distribution rather than stamped from one template.

Repaired 2026-08-28 by sampling donor curves from the healthy files, matched on cohort and on `potential − rating` so the 50× rule holds by construction, seeded on name+pick for reproducibility. Where no donor existed for a large gap, the donor's decline was kept and its positive slots rescaled to the required sum.

---

**An arbiter that resolves one collision can create another if it shares the collision's blind spot.**

Deduping 2021 by name+position falsely split Von Miller, traded mid-season and listed DE on one team page and OLB on the other — one man, two rows. Replacing the key with a Madden-identity arbiter (one distinct Madden record means one person) fixed that and immediately falsely merged Lamar Jackson the cornerback into Lamar Jackson the quarterback, because Madden 22 carries only one of them. Andre Smith and Spencer Brown failed the same way.

The arbiter was blind in exactly the place the collision lived: a player missing from Madden is indistinguishable from a player who doesn't exist. The fix is a second constraint the collision cannot share — here, position family, since a traded player changes position only within a family. DE/OLB is one edge rusher; QB/CB is two people regardless of what any single source says. Family gates the merge; the arbiter runs only inside a family.

**General form: when replacing a key to fix a false split, check whether the new key can produce a false merge before trusting it. Ask what the new arbiter cannot see, and whether that blind spot overlaps the collision being resolved.**

---

**Measure the cause before explaining it.**

Twice in the 2021 build a coherent theory was offered for an anomalous number, and both times a single count disproved it in seconds. The cap check was declared the known salary+guarantee property without comparing magnitude against the reference files — it was off by nearly double, and the real cause was `guarantee` shipping as total contract money rather than an annual figure. The appearance shortfall was attributed to pool size — the pool held 5,767 distinct faces against 3,287 players, nearly 2:1 surplus, and the real cause was a rejection loop written into one code path and not the other.

**An explanation that arrives before a measurement is a hypothesis wearing a conclusion's clothes.** Related: when a check fails, compare the magnitude against the reference files before concluding it's a known property. A failure that is expected in kind can still be wrong in size.

---

**Map the derived relationship, not the two endpoints independently.**

Quantile-mapping rating and potential separately let rating overtake potential wherever a player's rank differed between the two distributions, producing first overall picks at 80/80. Clamping afterwards hides it: the clamp holds, so it looks fixed, while the signal is silently gone wherever the ranks cross. Mapping the *gap* instead makes `potential < rating` structurally impossible rather than corrected after the fact. Applies anywhere two correlated fields are quantile-mapped.

**Strengthened 1986: matching a distribution is not evidence the structure
inside it is right.** This failure mode has now occurred three times, and in the
two 1986 cases every distribution check passed on the broken version.

Contract `length` was fitted to the published files' distribution conditioned on
years pro. Per-bucket means and one-year shares matched to two decimal places.
But length was assigned at random *within* each bucket, and the published files
have a consistent within-bucket relationship the random version destroyed —
better players get longer deals at the same experience level, correlation 0.22
to 0.39 in all thirteen buckets, mean rating 71 on one-year deals against 79 on
three-plus. The marginal distribution cannot see this.

`salary` then matched all fifteen position medians and the overall shape while
correlating with rating at 0.706 against the published 0.520. Because salary is
exponential in rating, that over-tight link amplified a normal spread in team
talent (1986 sd 1.62 against published 1.64) into a 72M–338M payroll range with
four teams over the cap. The distributions were right; the joint structure was
not.

**When fitting a field against reference files, measure the correlations the
reference has and reproduce them explicitly** — including deliberately adding
noise when the naive construction is too tight. Matching a marginal is the
weakest evidence available that a derived field is correct.

---

**A bug found in one field should prompt asking what else uses that code path.**

2021's `norm()` stripped non-a-z characters before folding accents, so `Piñeiro` became `pieiro` — a key matching nothing. It surfaced as one wrong skin tone. But `norm()` is the shared key for every lookup in the build, and the same two players were also missing their draft position and contract: Julién Davenport had been silently carrying a fallback contract and an undrafted pick number instead of pick 130.

Two players in 3,287 is 0.06% — invisible to every distribution check, unable to move a median, and it would have recurred in every future build. **Fix the shared function, not the record, and then check every consumer of that function.**

---

**Prospect potential = per-position slot baseline + a career raise. Rebuilt across all five files 2026-08-28.**

The original 2013 method was `min(99, rating + max(random 2..9, career ladder))`. 70% of prospects took the random draw, the AV ladder's lower rungs sat below the average dice roll, and first-team All-Pro was read as a threshold rather than a count — so Donald's eight and Linsley's one scored identically. Aaron Donald shipped at 90 against Khalil Mack's 99.

The replacement:

- **Slot baseline** `a_pos + b_pos·ln(pick)`, fitted per position from the 2004/2007/2010 rookie cohorts. Per-position matters: real draft position embeds positional value, so a pooled fit flatters running backs and punishes quarterbacks, and that confound misled an earlier analysis of this very bug.
- **Achievement score** from MVP 12, DPOY/OPOY 10, first-team All-Pro 6 **each**, Pro Bowl 1.5, plus career AV and years-as-starter as **percentiles within position and draft class**. Raw AV is not comparable across positions.
- **Normalised against a fixed elite-career reference (95), not the position cohort maximum.** Cohort-max normalisation makes the best player at a weak position score like the best at a strong one — it sent Corey Linsley to 96 on one All-Pro selection.
- **raise = 26 · score^2.0**, then `potential = min(99, max(rating, slot, slot + raise))`.

Raise-only is preserved: the score never subtracts. There is **no cap on potential minus rating** — the old ceiling of 14 was an artifact of the ladder's maximum, not a bound.

Results: Donald 90→99, Mack 99→96, Linsley 81→67, McCarron 74→67. Both conditional checks pass on all five files — raise rises across career-AV deciles and rises sharply with All-Pro count (0.0 at none, up to 12.8 at four or more).

**Known consequence, accepted:** most prospects sit exactly at their slot baseline with no raise. Only genuinely exceptional careers exceed what the draft position implied. **Second-team All-Pro is not in the formula** — PFR draft pages don't carry it.

**Files still disagree on shared draft classes, legitimately.** Of 89 disagreements between 2007 and 2010, 60 are players carrying a different `rating` in each file (each rates from its own era's Madden source, and potential can't fall below rating) and 29 are players listed at different positions. None unexplained. Before the rebuild, 226 of 256 disagreed for no reason at all.

**Prefer the source's own opinion, formed at the right time.** Joe Thomas: the 2007 post-season CSV says 85, a Madden 09-derived correction said 96. Take 85 — 96 is a year later, after he'd made All-Pro. Same logic softened Shaun Alexander from a Madden 09-derived 77 to 82, and later to the CSV's own 80.

**Don't cap a player against a cluster that came from a different source.** Randy Moss was capped at 93 to sit inside the receiver group as the Madden 08 launch file spaced it. In the post-season file he's 99 with three receivers at 97–98 — a tight group, not an outlier. Cap dropped. He led the league with 23 touchdowns.

**Don't manufacture separation.** Six running backs tied at 87 is what the source says. Inventing distinctions to match another file's spread adds information nobody has.

**Quantile maps must collapse ties, or they manufacture it for you.** Ranking tied source values consecutively hands them different targets. In the 2013 build this hit 76% of players — Manning and Brady both at Madden 97 came out 94 and 97, three tight ends tied at 65 spread to 45/61/62. **The overall distribution looks perfect throughout**, because the shape is right; only checking within a tied block catches it. Give every player sharing a source value the target at the block's midpoint quantile.

**A position-specific honour doesn't license a correction on a general scale.** Pro Bowl fullbacks are selected on blocking and short yardage, against other fullbacks, for a dedicated roster spot. Being the best fullback in football doesn't make you a better running back than LeSean McCoy. Cap fullback corrections at the FB cohort ceiling. The same applies to any honour awarded in a category the rating scale doesn't measure — long snappers, returners.

**An up-correction short on headroom awards what headroom exists, rather than being skipped.** A player already near the ceiling can't clear a +9 trigger, so the mechanism silently drops the best seasons. Peyton Manning's 2013 — 55 touchdowns, unanimous MVP, first-team All-Pro — produced no correction because he started at 97. Award the available room instead.

**Let historical outliers be outliers.** The 2007 Patriots should look absurd. If a rescale flattens the 16-0 team into an ordinary good one, the rescale is wrong.

**`injuryProne` is scaled to the vanilla game export, not to `100 − PINJ`.** The naive inversion produces a median around 20 where a game-generated league sits at 52 — our players were roughly half as injury-prone as the game intends, which quietly makes a core mechanic easier. Targets: rostered 52, free agents 49, rookies 34. Veterans should be MORE fragile than rookies; three of four files originally had that inverted.

**Generated appearances stay inside the families the source can produce.** Madden's `PHCL` maps to hair families 1–5 only, so any player with a real face is in that range. A generator drawing across all six leaves family 6 exclusively on unsourced players — a visible tell for which records had data. Constrain it.

---

**An "uncertain" scheme takes the modal value for that season, recorded in a note field.** There is no neutral option in the scheme or coverage vocabulary, so "leave it generic" isn't available — something has to be written. Take the most common value across the other 31 teams and say in a note that it was defaulted. Washington 2026 was flagged uncertain and got West Coast, which was modal at 24 of 32. Picking a vaguer-sounding label instead is still a specific claim, just a less likely one.

---

## Real people vs. invented ones

**Real coaches form a clean top block in free agent pools; invented names sit strictly below all of them.** Not interspersed. 2017 originally had invented names above real ones and had to be fixed.

**Invented names must not collide with real people.** Check generated names against every real coach name across all files. 2010 had 28 scout and physio slots carrying real coach names — Sean McVay, Adam Gase, Chuck Pagano.

**The free agent coach pool holds coaches a team might plausibly hire, not everyone technically unemployed.** Marv Levy was excluded at 82 — real, available, never a realistic signing.

**Never attach invented ratings to real people.** This is why 2029 and 2030 draft classes are generated rather than filled with real recruiting-ranking names: real names with meaningless numbers are worse than obviously fictional ones.

---

## Structural decisions

**Long snappers are cut.** None are viable elsewhere — their overalls are graded purely on snapping while their blocking sits in the 45–69 range. An 81-rated long snapper would be an 81-rated center who can't block.

**Fullbacks map to RB, but rebuild attributes from source first and map against the real FB cohort.** Madden rates them above halfbacks on blocking criteria. The actual FB cohort in the working files sits at the 28th percentile of the RB pool.

**FS/SS both map to S. Both edge codes map by team scheme (3-4 vs 4-3), not blindly.**

**When a coordinator slot doesn't exist, use the senior assistant on that side and record why.** Miami 2007 had no OC (Cam Cameron called plays) — Terry Shea, QB coach and former Bears OC, fills it. Tampa Bay 2026 has no DC (Todd Bowles calls it) — George Edwards, pass game coordinator. Both carry a note field so they read as decisions rather than errors.

**Duplicate appearances are fine.** The game's own export has 12 and the donor has 183. Never alter a face to break a tie.

**Prospect `eSalary` and `eLength` are both 0.** Matches the donor, where 1,326 of 1,434 prospects have both at zero.

---

## Process

**A person gets one face across every season.** The face registry is applied as the last step of every build, and hand edits are its top-priority source. Ryan should never have to make Aaron Rodgers five times. Before the registry, Belichick and Brady each had five different faces across five files.

**Bulk operations run before hand edits, never after.** The person's avatar work has been overwritten once and nearly a second time. There is no safe cohort — they edit rostered players, prospects, free agents and coaches.

**When they report something odd in play, check the data.** Every report has been a real bug.

**Don't switch primary rating source mid-build.** Rebuild everything against the new source rather than patching. Two rating scales in one file is invisible to structural checks.

**Values fitted to one scale must be re-derived, never carried across.** A bias correction fitted for ratings is meaningless on attributes, and a correction derived under one rescale is meaningless under another.

**Test rather than assume when the answer is checkable.** The age-adjustment curve looked completely reasonable and nearly doubled the error — only a holdout caught it. Percentile-derived attributes looked fine until measured against adjacent-year real data (MAE 8.52 vs 2.35).

**Ask for a document rather than guessing.** Coaching staffs, schemes, career records and draft boards have all come from a targeted prompt to another AI, with an instruction to say "uncertain" rather than estimate. That workflow has produced good, verifiable data every time. Verify a sample before building on it.

---

---

---

## Stale mental model of a file you already corrected

The stale-artifact rule covers reading an out-of-date file. The 1986 session
found a second form: **working from an out-of-date understanding of a file that
had already been corrected in the same session.**

The four expansion teams were established early as already stocked with real
out-of-league veterans, and written into the build log. Two hundred messages
later, presented with "25 USFL players against 212 slots", the assistant
accepted the framing and began ranking sources to fill 187 non-existent gaps —
contradicting its own documented finding without noticing.

**Before scoping work against a number someone supplies, check it against what
the build log already says.** A number offered in conversation does not override
a measurement already recorded; if they disagree, that disagreement is itself
the finding.

---

## The bit-shift is not uniform across fields in the 1986 `.ros`

Reading the binary directly, `POVR` yields correct values at declared bit offset
**+3** and `TGID`/`PAGE`/`PPOS` do not; at **−4** the team and age fields look
plausible and `POVR` does not. No single shift works for the whole record, and
the cause was never established because the CSV export made it moot.

**Consequence:** anyone reading the `.ros` rather than an Xtreme DB CSV export
will hit this on every numeric field, and plausible-looking output is not
evidence the shift is right — `PAGE` at the wrong shift produced ages of 46 for
24-year-olds while still falling inside a believable range. Use the CSV export.
This is "observed range is not accepted range" with a concrete instance.

---

## Find the real cohort before measuring anything

**Twice in the 1986 session, a measurement taken across a whole file produced a
confident wrong conclusion, and both times the fix was to identify the real
population first.**

The contract fields were tested for signal across all 2,470 rows of the 1986
`PLAY` export. `PCON`, `PSBO`, `PVCO` and `PSXP` correlated with rating at
between −0.16 and +0.22, which reads as noise, and the conclusion was that
nothing in the file held real contract data. But 724 of those rows are filler —
joke all-star teams, two Hall of Fame legends squads, generated free agents and
169 empty `New Player` placeholders — all carrying defaults by construction. On
the 1,746 real players the same fields read `PCON` +0.59, `PSBO` +0.65 and
`PTSA` +0.66. Three genuine relationships had been diluted into apparent noise
by rows that were never players.

The same session's handoff described the `COCH` table as "28 real 1986 coaches
and ~184 modern ones, filter them out by name", from a name-match test run
across all 215 records. `TGID` sorts it exactly: 128 coaches sit on teams 1–32,
four per team, and they are the real 1986 staffs; the other 87 sit on the same
filler team IDs as the players. No name filtering is needed at all.

**The filler is usually separable by a field that hasn't been checked yet** — a
team ID, a status flag, a record-index boundary. Look for it before measuring,
not after a result looks strange.

**The tell in both cases was visible in the output that was already produced.**
`PVCO` sat on a single value for 1,584 of 1,746 records. A field that degenerate
should prompt the question of what population is being measured, rather than
being read as confirmation that the field is dead.

Related to the stale-artifact rule: that one says check you have the current
file, this one says check you are measuring the right rows of it.

---

---

---

---

---

## A published reference is an output, not a specification

**Three times in the 1986 session, a relationship was fitted on top of a
reference that already contained it — applying it twice.** The instances look
unrelated; the cause is identical.

1. **Guarantee as a ratio to salary.** The project handoff describes guarantee as
   a ratio of salary, which is a correct *observation about the output*. Used as
   an *input specification* it exploded: published players with near-zero salary
   and a real guarantee produce ratios approaching 100, and quantile-mapping onto
   that tail applied them to normal salaries. First attempt produced a $566M cap
   hit for Carlos Carson.
2. **Salary against rating.** A per-position quantile map of rating rank onto the
   published salary distribution already reproduces the published rating-salary
   relationship. Because the map was built on rating rank *and* the reference was
   ordered by rating, the result correlated at 0.706 against a published 0.520 —
   too tight, which amplified normal team-talent spread into a 72M–338M payroll
   range with 4/32 teams over the cap.
3. **Prospect potential gap.** The published prospect gap curve was used as a
   draft-slot baseline, then a career-achievement raise was added on top. But
   those published files were built by the same raise-only method, so the curve
   *already embeds* achievement. Top-decile gap came out 14.3 against a published
   9.3.

**The general form: a published file is the product of a method, so it already
encodes every relationship that method produced. Anything you add on top of it
is applied twice.**

**The shape that works — used successfully twice:**

> **Let the reference supply the level; let your own derivation supply the order
> within it.**

Guarantee: rank 1986 players by salary, map onto published guarantee *in dollars*
within a length bucket. Prospect gap: rank players by career achievement, map onto
the published gap distribution within a draft-slot band. In both cases the derived
quantity decides *who gets more*, and the reference decides *how much more*.

**Fourth instance, and it recurred AFTER being written down twice.** The 1986
head-family mapping was hand-assigned — skin 0 to families 1–2, skin 2 to family
3, skin 1 to families 4–5. Result: 61.7% in family 4 against a published 36.2%,
and 1.4% in family 3 against 43.0%. Fitting it instead (published per-position
family distribution supplies the level, the skin field supplies the order) landed
11.5/7.2/43.1/35.3/2.9 against 11.1/6.7/43.0/36.2/3.1.

**Why it recurs despite being documented: hand-assigning a mapping does not feel
like fitting a relationship.** It feels like a definition — "dark skin means a
dark family, obviously" — and definitions do not trigger the instinct to check
against a reference. The tell is the same every time: a category share that is
wildly off while the ordering looks sensible.

**Diagnostic:** before adding a term, ask whether the reference distribution was
itself produced by a method that included that term. If yes, the term belongs in
the ranking, not in the value.

**The tell is a correlation that BEATS the reference, not one that misses it.**
Under-correlation looks like a bad fit and gets investigated. Over-correlation
looks like a good fit and ships. Fourth instance, 1986 attribute block: two
derived fields driven from one shared source score came out at 0.828 against a
published 0.353 — a shared source cannot carry the independent variation the
reference has, so members of a derived group are always *too* alike. Fix is
per-member noise blended into the rank, with the weight **fitted against the
reference's own within-group correlation, not guessed**. Guessed weights got
0.585; fitted weights got 0.357 against a target of 0.353.

Closely related to "matching a marginal distribution is the weakest available
evidence" — that entry is about checks that pass when structure is broken; this
one is about how the structure gets broken in the first place.

---

---

---

## A safe default is still a claim about the data

Every correlation finding in the 1986 session pushed one way: preserve joint
structure, prefer whole-row resampling, beware independently-fitted fields. The
project owner proposed whole-row resampling as a **safe default** for the
personality block — `discipline`, `loyalty`, `greed`, `ambition` — on exactly
that reasoning, since a method that copies complete records cannot produce
over-tight correlation.

**The measurement refuted it.** In the published files those four are mutually
independent: every pairwise correlation under 0.05, and under 0.05 against
`injuryProne` too. Whole-row resampling would have been *safe* but would have
risked importing correlation the reference does not have. Independent fitting is
correct here precisely because independence is the reference's real structure.
Built output reproduces it — all pairs under 0.05, all four marginals matching
the published median and mean exactly.

**The general form: "safe default" is a hypothesis about the data, not an escape
from checking it.** A default chosen because it fails gracefully in the common
case still asserts that this case is the common one. The refuting measurement —
here, one correlation matrix — is almost always cheaper than the rework.

Same shape as checking whether age was an input to the head coach formula, and
whether OC ratings tracked DC ratings. Sharper than both, because the default
came from the person with the most context and was still wrong for this field.

**Practical rule:** before applying a structure-preserving method, look at the
structure. If the reference shows independence, preserve *that*.

---

---

---

## The by-position gradient test has a blind spot: partial defaults

The position-gradient test (a field is real if its by-position profile matches
known demographics) correctly identified `PHED` as informative — a 73-point
spread from CB to K, monotonic, ordered exactly like the published files.

**It still missed that `PHED` was partly defaulted.** `PHED` puts 49.6% of the
1986 cohort in the dark bucket. The real 1986 NFL was roughly 60–65% Black, and
a genuine skin field found later in an Xbox 360 roster gives 68.2% with a
98.3-point gradient. So `PHED`'s single-value spike at 7 was a **catch-all that
absorbed part of the dark cohort** while the players it *did* distinguish were
distributed correctly.

**The limitation, stated generally: a gradient can be correctly shaped and still
under-detect one category.** The players a field does classify can be classified
well while a large default bucket quietly swallows the rest. The gradient test
sees shape, not coverage.

**Second check to run alongside it: compare the field's overall base rate against
the known real-world rate.** A gradient that matches while the base rate is 15
points off is a partially-defaulted field, not a working one.

---

---

---

## When a correction turns out smaller than the argument used to make it, record the size

The 1986 coach appearance research came from 2004–2010 rows. The correction —
hair colour is era-dependent, so 79% grey describes men aged 61 at observation,
not the same men at 43 in 1986 — was **right in principle**. The argument used to
make it was that adopting the rate would produce "a league of white-haired
forty-somethings".

**Checked afterwards: the published staff files run about 60% grey at every age
band, including 25–40.** PGM3's staff art is mostly grey regardless of age. So
conditioning hair on age moved the result from 79% to 57%, against a published
60%. Real, worth doing, and far smaller than the rhetoric implied.

**An overstated correction that goes unchecked becomes what the next session
believes.** The direction survives into the record easily; the magnitude does
not, unless it is written down. Record both — and when the magnitude turns out
smaller than the case made for it, say so in the same place the case was made.

---

## Donor copying is safe for role fields and unsafe for person fields

Whole-record donor copying preserves joint structure by construction and has been
the right method repeatedly (scouts and physios, `growthType` arrays, appearance
token triples). It has a hard boundary.

**Safe — fields that describe a ROLE.** Scheme and style (`offStyle`,
`defStyle`, `blitzStyle`), growth curves, coaching-attribute spreads, contract
shapes. Any coach of that rating could plausibly have these.

**Unsafe — fields that describe a PERSON.** Appearance above all. Skin tone,
hair, facial hair are facts about an individual, and a donor is a different
individual.

**1986 instance.** The staff file was assembled by donor copy from published
staff, appearance included, and nobody questioned it because every structural
check passed. **Chuck Noll was shipping as a dark-skinned coach**, along with
roughly twenty others — 17% of the coaching staff dark against a real 1986 figure
near 7%, in a league whose first modern Black head coach was still three years
away.

Rebuilt from research (7), plus `CSKI` non-zero as *positive evidence only* (2
more; the field is ~78% precise — its false positives are Belichick and Ernie
Stautner, both white), light otherwise.

**Rule: before donor-copying a field, ask whether it is a fact about the job or a
fact about the man.** Structural checks cannot tell the difference; every one of
them passed.

---

## Research data is dated by the moment of observation — decide transfer field by field

A research pass returns what was true **when the source was observed**, not when
the build is set. Whether that matters depends on the field, and the decision has
to be made per field rather than accepting or rejecting the pass wholesale.

**1986 session.** 41 coach-appearance rows already existed in the project,
researched for the **2004–2010** published seasons. 38 joined cleanly to the 1986
staff — the same men, eighteen years earlier.

| field | survives an 18-year shift? |
|---|---|
| skin tone | **yes** — stable for life |
| facial hair | **mostly** — moustaches persist; usable |
| hair colour | **no** — it is a function of age at observation |

**79% of the rows read "grey or white".** That describes men whose mean age *at
observation* was 61. The same men had a mean age of **43 in 1986**, and
twenty-one of the grey-haired ones were between 26 and 45: Ditka 47, Parcells 45,
Belichick 34, Dungy 30, Cowher 29. Adopting that rate as the 1986 fill would have
produced a league of white-haired forty-somethings.

**This is the photo-pass problem inverted, and worse.** When 1980s cards showed
helmeted players, the field was *unavailable* and obviously so. Here the field is
*available and wrong*, which passes every distribution check — the 79% grey rate
is a perfectly plausible marginal for a set of coaches. Only asking *when* it was
observed exposes it.

**Also a generational trap in the same file.** "Jim Mora" joined on name, but the
1986 record gives age 51 (born 1935 — Mora **Sr**, Saints) while the research row
is 2004 Atlanta (Mora **Jr**, born 1961). The older file omits the suffix because
in 1986 there was only one. Excluded. See the `norm()` entry in the handoff.

**Rules:**
1. Before joining a research pass, establish **when** it was observed.
2. Classify each field as era-stable, era-decaying or era-dependent, and transfer
   only the first two.
3. **When commissioning a pass for a historical build, state the target year
   explicitly and say why** — otherwise it returns present-day answers for anyone
   whose career continued, and those are the recognisable names.

---

## A plausible distribution is not evidence of signal — anchor the field

**Twice in the 1986 session a source column looked entirely healthy on every
distribution check and carried no usable information.** Marginals cannot detect
this; only anchoring against known-truth cases can.

**`PSTM` (stamina).** Range 0–87, 86 distinct values, smooth spread — passes any
range or shape check. But its **position leaders are punter (54) and kicker
(51)**, which is absurd for stamina. `PSTA`, which leads at CB (96) and S (96),
is the real field.

**`PSKI` (skin tone).** Three values with 82.4% of the cohort in one bucket —
already suspicious, but not conclusive, since a 1986 league could plausibly
concentrate. The anchor test is conclusive: **all 12 documented Black players and
13 of 14 documented white players read the same value, 1.** The field does not
separate the anchor groups at all. The modder never set it.

Mapping `PSKI` directly would have produced a complete appearance block that
passed every check while assigning skin tone essentially at random across 1,746
players — an error invisible to every automated test and obvious to anyone who
opened the game.

**The two anchor tests, both cheap:**

1. **Position leaders.** Group by position, rank medians. Real football
   attributes have predictable leaders. A nonsense leader board means the label
   is wrong. Works without a schema.
2. **Known-truth cohorts.** Assemble two lists of players whose true value is
   documented, and check the field separates them. If both cohorts return the
   same value, the field is dead regardless of its distribution.

**Rule: before using any source column, anchor it. A field earns trust by
separating cases you already know the answer to, not by having a believable
histogram.** This is the operational form of "observed range is not accepted
range" — that entry warns that a plausible *value* proves nothing; this one
warns that a plausible *distribution* proves nothing either.

**Corollary — when a field is dead, condition the replacement on what you do
know.** Published skin-tone families vary enormously by position: 52.9% of
kickers and 41.1% of punters in the lightest family against 1.5% of cornerbacks
and 4.1% of receivers. A flat league-wide fill is wrong in both directions
simultaneously; a position-conditioned fill is right roughly 90% of the time
before any research is done.

---

## A field whose position leaders are physically absurd is mislabelled

The 1986 source carries both `PSTM` and `PSTA`, and the handoff records a
recurring confusion between them: the wrong one produces "a plausible
distribution with zero per-player signal."

**`PSTM` looks fine on every distribution check** — range 0–87, 86 distinct
values, sensible-looking spread. Nothing about the marginal identifies it.

**The discriminator is which positions lead it.** `PSTA` leads at CB (96) and
S (96), which is what stamina should look like. `PSTM` leads at **punter (54)
and kicker (51)** — physically absurd for a stamina field. `PSTA` is stamina;
`PSTM` is something else.

**Generalise the method, not the case:** for any column whose meaning is
uncertain, group by position and rank the medians. Real football attributes have
predictable leaders — corners lead speed and coverage, tackles lead pass block,
guards lead run block, middle linebackers lead tackling, quarterbacks lead
passing. A column whose leader board is nonsense is mislabelled regardless of
how plausible its distribution is. This works on any file, without a schema.

The same check, run forward, validates a whole attribute block: build the
expected leader per attribute from the published files, then confirm the built
file reproduces it. 1986 passed 28 of 28.

**Report ties rather than resolving them.** `idxmax` on tied medians picks
arbitrarily. The published files have WR and RB tied at exactly 83 on
`elusiveness`; a naive check flagged a mismatch that did not exist. A real
inversion inside a tie would look identical to that false alarm, so the check
must list all tied leaders and pass if the expected position is among them.

---

---

---

## The axis a mapping is fitted on is the axis it preserves

A quantile map reproduces the reference's structure **along the axis it is
bucketed by**, and discards it along every other. So when the output deviates,
looking for the cause on the axis you fitted is looking where it cannot be.

**1986 `guarantee`.** Mapped in dollars within **length** buckets, ranked on
salary. The zero-pattern check flagged it at 12.3 points. The hypothesis was that
the published files hold a real population of zero-guarantee minimum-salary
contracts spread across length buckets. Measured: **the length buckets matched
almost exactly** (44.1% vs 44.9% at length 1, 42.1% vs 37.3% at length 2). The
deviation was entirely on **position** — published QBs are 27.5% zero-guarantee
and kickers 42.9%, because guarantee tracks player value and value is
position-shaped. The single-axis fit had flattened it.

Remapping on `(position, length)` with a length-only fallback for thin buckets
took the worst position deviation from 12.3 points to 5.5, with payroll,
correlation, position medians and the 50x rule all unchanged.

**This is the third instance in the contract work specifically** — after
length-vs-rating and salary-vs-team-spread. That makes it a property of
contracts rather than a recurring mistake: **contract fields carry more joint
structure than any other field group in the file** (salary x rating x position x
length x guarantee), so any single-axis fit loses something. Fit contracts on at
least two axes and check the third.

**Diagnostic:** when a mapped field deviates, list the axes the reference varies
on, then check which of them the mapping bucketed by. The deviation is on one of
the others.

---

## Confirm the defect is present before fixing it

A variant of "measure the cause before explaining it", and a nastier one: the
failure is not a wrong explanation of a real problem, it is a **plausible
explanation of a problem that does not exist**. A fix applied to healthy data is
a defect introduced.

**1986 session.** A published rostered record showed a linebacker with eleven
attributes at zero — `catching`, `passBlock`, `trucking` and so on. Correct
inference: the published files null out attributes that do not apply to a
position. **Incorrect inference: that the 1986 build had filled them.** A
per-position zero mask was written and applied.

It was redundant. The attribute block is built by **per-position quantile
mapping**, and if 100% of published centres have `catching` at zero then every
value drawn from that distribution is zero. The unmasked build already matched
the published zero pattern to within **0.2 percentage points across all 420
position-attribute cells**. The mask double-applied it, zeroing 92.3% of OLB
coverage against a target of 67.7%.

**The check was one line and available before the fix:** compare the built
file's zero rate against the reference's. It was run afterwards, as diagnosis,
when it should have been run first, as confirmation.

**Rule: before writing a fix, measure that the thing you are fixing is actually
wrong in the built output.** Seeing the mechanism that *could* cause a defect is
not the same as observing the defect.

---

## Quantile mapping transports structure, not just shape — and that makes the zero-pattern check a METHOD detector

A per-position quantile map draws values from the reference's own distribution
for that position. Anything structurally true of that distribution comes across
for free:

- **Zero patterns.** 100% of published C have `catching` = 0, so every mapped
  value is 0. Measured across 15 positions x 28 attributes: max deviation 0.2
  points, including the partial case (OLB coverage live 32% of the time — built
  67.8% zero against a published 67.7%).
- **Value vocabulary.** Only values present in the reference can be produced.
- **Bounds and granularity.** Min, max and the set of attainable values follow.

**Consequence for validation: the zero-pattern comparison passes by construction
on any quantile-mapped field.** A failure there is therefore *not* evidence of a
data problem — it is evidence the field was built some other way (hand-assigned,
parametrically fitted, defaulted). **It is a method detector, not a data
detector**, and should be read that way: it tells you which fields skipped the
mapping, and those are the ones to inspect.

---

## Vocabulary checks beat hand-written constraint checks

Two kinds of check on built output, and they are not equally trustworthy.

**A vocabulary check** asks: does the built file use any token the reference files
never use? The game's value vocabulary is **closed**, so any novel token is wrong
by definition. This needs no domain knowledge, no format model, and catches
format errors, invented values and mis-parsed fields in one pass.

**A hand-written constraint check** asks: does the output satisfy a rule I
believe holds? It compares the data against *my model of the format*, so it fails
whenever the model is wrong — which is exactly when it is least likely to be
suspected.

**When the two disagree, the model is the more likely thing to be wrong.**

**Evidence — the same trap twice in one hour, 1986 session.** `Hair` and `Beard`
tokens can carry a trailing style digit (`Hair1r2`, `Beard1a2`). First it hit the
*builder*: appearance was assembled as a pipe-delimited string with a simplified
hair token. Then it hit the *validator*: a constraint check read family digits at
fixed character positions, so on tokens with a trailing digit it read the wrong
characters and reported the family-digit rule at **0%** immediately after a set of
correct overrides. The regex version reported 100%.

**The validator instance is the more dangerous of the two.** A silent pass loses
a check; a false alarm sends you unpicking data that was fine, consuming both
effort and confidence in a correct result. Here the vocabulary check settled it —
zero novel tokens, which cannot be true if the tokens were malformed.

**Two standard opening moves before building against any new format:**
1. **Read one real published row.** A fixed value produces no distribution
   violation because there is no distribution to violate — `Eyes` and `Clothes`
   hard-coded to one value each would have made every 1986 player subtly
   identical and passed every aggregate check.
2. **Run the vocabulary check first, not last.**

---

---

## Keep failed attempts in the log — a matcher becomes trustworthy only through its failures

The 1986 name-variant matcher took **three iterations**, and each fix came from a
specific documented failure rather than from tuning.

1. **v1** — surname ratio ≥0.88, forename ≥0.72, prefilter cutoff 0.80.
   Reported 168 "absent" players. **Jim Ritcher** failed at surname ratio 0.857
   (a transposed pair of letters); **Dave/David Waymer** and **Mike/Michael Cofer**
   never reached the guard because the 0.80 prefilter never surfaced the candidate.
2. **v2** — the count was refused rather than reported, precisely because the
   matcher had just been shown failing on four names in the same message.
3. **v3** — prefilter **0.72**, surname **≥0.84**, forename **≥0.60**, plus
   side-of-ball agreement. Recovered 32 variants including Ritcher, Wagoner,
   Fryar, Rohn Stark, Issiac Holt.

**A guard that is never reached looks identical to a guard that passed.** That is
the nastiest of the three failure modes and it is invisible unless a known-true
case is checked by hand.

**The general point: the thresholds were only tunable because the earlier failures
were found and written down.** Had v1's 168 been reported and accepted, tuning
would have been blind — there would have been no signal that anything was wrong,
because the output was internally consistent and plausible.

**Log the attempts that failed, not only the method that worked.** The failures
are what make the final parameters defensible rather than arbitrary.

**Related: exact-name matching of "missing" records is a systematic OVERESTIMATE,
not a noisy one.** Three instances in the 1986 session — the draft pass, the face
registry overlap, the 1985 fallout — every correction in the same direction, fewer
real absences than the raw count. A noisy estimate is still usable; a biased one
is not.

**The fix that removes the matcher beats the fix that improves it.** The final
1985→1986 fallout used complete rosters against a complete file: set arithmetic,
no matcher in the exclusion itself. 179 same-man-different-position rows were
caught for free — a fifth of the pool, which any name-based method would have
turned into false free agents.

---

## Doug Smith — the project's canonical namesake case

Two different men in the 1986 cohort: a **centre on the Rams (TGID 24)** and a
**defensive tackle on the Oilers (TGID 30)**. He collided **three times in one
session**, in three different kinds of operation:

1. **A repair** — `PYRP` corrections keyed on name alone edited both records,
   only one of which was broken.
2. **A source-file duplicate resolution** — the Xbox 360 roster disagrees with
   itself on his skin tone; taking the modal value would have picked arbitrarily
   between two real people.
3. **A research join** — the photo pass returned "Doug Smith, RAM, C". Name-only
   matching would have put the Rams centre's face on the Oilers tackle.

He is a better canonical example than the C.J. Mosley case because both men are
**in the same file, in the same season**, and position is the *only* field that
separates them — so every arbiter that ignores position fails, and every one that
uses it succeeds.

**Fourth instance, and it removed the last discriminator.** The 1986 cohort
contains **two different James Joneses, both RB, both in 1986**. Name+position —
the face registry's own key — is not unique *within a single season*, let alone
across eras. Writing the registry block on `name|position` silently produced
1,745 entries from 1,746 players: one man overwrote the other, with no error.

**The key must include team**: `name|position|teamID` gives 1,746 unique keys.
The general rule is that a key needs enough fields to be unique *in the widest
population it will ever be queried against* — and a registry is queried across
every season that exists, so its key needs era and team as well as position.

**Silent count loss is the tell.** 1,746 in, 1,745 out, no error raised. Any
build step that writes a keyed structure should assert output count equals input
count, the same way a repair asserts its key matches exactly one row.

**Standing rule for research prompts: always ask for team and position, not just
the name.** In the 1986 photo pass those columns were present only because they
had been requested to help the researcher *confirm identity* — the safe join was
luck, not design. One extra column at prompt-writing time against a join that
silently puts one man's face on another.

---

## A repair operation is a lookup

The namesake rule ("any lookup keyed on a player name is a bug until it is
disambiguated") was already established for joins, for the ratings backfill, and
for reference cohort construction. In the 1986 session it bit inside a
**correction script** — written after the rule had been applied correctly to a
join earlier in the same session.

Fifteen players had impossible `PYRP` values needing repair. The fix was keyed
on `name` alone: `L.loc[L.name==n, 'PYRP'] = new`. The 1986 cohort contains
**11 duplicated names** — Doug Smith, Doug Williams, Gary Anderson, James Jones,
Bob Nelson, Bobby Johnson, Charles Jackson, Eric Williams, Mike Black,
Mike Wilson, Robert Jackson. The correction silently edited two different Doug
Smiths: a centre rated 92 and another player rated 81, only one of whom was
broken.

**Why it slipped through a rule that was being followed:** repairs do not *feel*
like lookups. A join is obviously a lookup; an edit feels like an edit. But
`df.loc[df.name==n]` selects rows by name whether it then reads or writes, and
writing is the more dangerous direction because the damage is silent and lands
in a file that will be trusted later.

**The general form: any operation that selects rows by name is a lookup —
reads, writes, deletes, updates.** Disambiguate all of them.

**Third instance, and it is not always a write.** Resolving a *source file's*
self-disagreement by taking the modal value is also a name-keyed lookup. The 1986
Xbox 360 roster has 45 duplicated names, 13 of which disagree with themselves on
skin tone. Mode "resolved" them — but Doug Williams appears once as a QB (light)
and once as an OG (dark), and Gary Anderson once as a K and once as a RB. Those
are **two different men each**, and mode was arbitrarily picking between two real
people. Position disambiguated 10 of the 13 correctly.

**When the disambiguator cannot separate the collision, the answer is
"unresolved" — not the arbiter's best guess.** The remaining three — Dwight
Stephenson, Mike Webster and Randy White — each appear twice *at their own
position* with conflicting values, so position has nothing to work with. Mode
returned the right answer for all three, but by luck: all three are white, so the
majority value happened to be correct. **Being right by luck is
indistinguishable from being right by method until someone checks.** Those three
went to the research queue rather than being marked resolved.

This extends the existing rule that an arbiter can share the collision's blind
spot: here the arbiter has no purchase at all, and the correct output is a flag,
not a value.

**The fix is an assertion, not care.** Key match count must be *checked*:

```python
m = (df.name == n) & (df.TGID == t)
assert m.sum() == 1, f'{n}/{t} matched {m.sum()}'
```

A repair that matches two rows should crash, not proceed. Care does not scale
across a session; the assertion does.

---

## `PYRP` counts NFL seasons played, not seasons since the draft

Deriving draft year as `1986 - PYRP` disagreed with real draft years for 102 of
1,291 matched players. The instinct was to call the field unreliable. **The sign
of the residual carried the whole answer.**

**87 positive residuals** (`PYRP` implies *fewer* seasons than have passed since
the draft) are not errors — they are the field being right. `PYRP` counts NFL
seasons actually played. A +2 spike of 61 players is the **USFL cohort**
returning after two seasons away: Tom Thayer drafted 1983, USFL 1983–84, Bears
from 1985. Sam Clancy and Jim Fahnhorst the same.

**William Andrews is the clearest single case.** He reads 5: drafted 1979,
played 1979–83, missed 1984 *and* 1985 with the knee injury that ended his
prime. A naive `1986 - draft_year` derivation would give 7 and destroy real
information the file was carrying.

**15 negative residuals are the only true errors** — `PYRP` claiming more NFL
seasons than exist since the player was drafted, which is impossible. Keith
Ferguson at 13 when drafted in 1981; Robbie Bosco and Hugh Millen at 8 when
drafted in 1986 and yet to play a down. 1.2% of the cohort.

**Consequences:**
- `PYRP` is the *correct* input for contract length, better than seasons-since-
  draft would be — a player in his second NFL season after two USFL years
  belongs on a second-year deal. The fit did not need revisiting.
- **`PYRP` was being used as a routing key** to send players to the right draft
  source by implied year. 39 were routed to the wrong decade, failed to match,
  and landed in the undrafted bucket looking exactly like genuine undrafted
  players. Fixed by unioning the sources and dropping year routing entirely.
- Undrafted share fell from an apparent **28% to a measured 20.8%**.

**The general lesson: a field that looks wrong may be measuring something
different from what you assumed.** Neither the count of divergences nor the
match rate could distinguish "wrong value" from "different semantic" — only the
*direction* could, because one direction was possible and the other was not.
Same shape as checking whether age was an input to the head coach formula, and
whether OC ratings tracked DC ratings: find the version of the question whose
answer is a number, and check whether that number has a sign.

---

## A rank-based map needs a population, and four is not one

Quantile mapping onto a reference distribution fails in **both directions** when
the cohort being mapped is small, and the two failures look opposite while
having one cause.

**Too few draws lose the tail.** Scouts and physios were generated by resampling
published rows at random, 32 per role. Every median came out correct, but Def
Scout topped out at 77 where every published *season* — also 32 people — reaches
82–92. Random draws from 192 rarely hit the extremes. Fixed by stratifying: one
draw per rating percentile band.

**Too few ranks invent a spread.** The four expansion coordinators were rated by
ranking them against the full published distribution. With n=4 the percentiles
are forced to 12.5 / 37.5 / 62.5 / 87.5, so the best of four landed at 86 —
fourth best in the league — purely for being first of four. Fixed by ranking
them against the **28 real coordinators on the file's own `COFF`/`CDEF` scale**,
which is a real population, then mapping that percentile.

**The rule:** before quantile-mapping, ask what population the rank is computed
against. If it is the cohort being built and that cohort is small, the ranks
carry no information about level — only order. Find a larger reference
population that both cohorts can be placed on, or stratify so the draws cover
the reference's range.

Both incidents were caught by comparing against the published files
*per season* rather than pooled — 32 against 32 is the like-for-like comparison,
and pooling 192 hides exactly this.

---

## When a caution is raised, find the version of it that produces a number

**Three times in the 1986 session a vague worry was converted into a measurable
question, and all three times the measurement changed what happened next.**

1. **Age in the head coach formula.** The 1986 head coach ratings correlated with
   age at 0.523 against a published 0.186, and the plan was to accept it as a
   real property of the era. The question that made it decidable was *is age an
   input to the formula?* It was — a 0.15-weight tiebreak on five first-timers.
   Stripping those out made the correlation **stronger** (0.628), which inverted
   the concern: the age term had been diluting a real effect, not creating a
   fake one.

2. **Source difference on unit ranks.** The worry was that NFL.com and PFR might
   disagree where the published seasons used PFR. The measurable version:
   *ranks are invariant to small discrepancies, so flag only teams whose rank
   would move under a small perturbation.* This converted a blanket caveat into
   a bounded check. (It became moot when PFR opened up — but the framing was
   right.)

3. **SRS contamination of coordinator ratings.** SRS is margin-based, so an
   elite defense can inflate its own team's OSRS through field position. The
   measurable version: *does a team's OC rating track its own DC rating more
   than in the published seasons?* 1986 came out at +0.213 against a published
   +0.236 — cleaner, not worse — and the spread was tighter (8.0/9.0 vs
   9.1/9.3) rather than wider. The concern was real and the data cleared it.

**The pattern: a caution phrased as a worry can only be agreed with or waved
away. The same caution phrased as a comparison against the published files can
be settled.** Ask what number would distinguish the concern being true from it
being false, then compute that number.

Related: this is the constructive form of "measure the cause before explaining
it." That entry says don't theorise before counting; this one says how to turn
a vague worry into something countable.

---

## When a source has a stake in its own entry, check that entry first — and say so before you look

The 1986 special teams ranking comes from the **1987 Kansas City Chiefs media
guide**, built on a system devised by **Frank Gansz**, the Chiefs' own special
teams coach, and it places **Kansas City second**.

That was flagged as the thing to check *before* the check was run. A
reconstruction from six of the seventeen categories (raw 1986 NFL.com data)
correlated with the published table at Spearman 0.616, p=0.0005 — and the
correlation *rose* from 0.558 as coverage categories were added, which is what
you want to see if a table is sound. Both anchors held: Cleveland 1st published
against 4th reconstructed, Tampa Bay 28th against 23rd.

**Kansas City was the single largest disagreement: 2nd published, 16th
reconstructed.** Their net punting ranked 19th, field goal percentage 15th, and
they allowed 5.8 return yards per punt. Nothing measurable supports 2nd.

The ranking was used anyway and Gansz left at 91 — overriding a period source on
a partial reconstruction would be the ratings generating rather than verifying.
But it is logged as a named open item.

**The methodological point: stating the prediction in advance is what makes the
check meaningful.** A confirmation only counts if the disconfirming result would
have been recorded too. Had Kansas City's second place come out well supported,
that would have been evidence *for* the table and would have been logged just as
prominently.

---

## Named columns beat inferred ones, even when the inference validates

Skin tone was reverse-engineered out of the `.ros` binaries by locating a bit
offset and checking it against players whose appearance was known. It validated
at 19–20 out of 20 on famous names, which felt like enough.

It was not. Travis Kelce and David Bakhtiari both came out dark-skinned. The named
`PSKI` column in the CSV export had them right the whole time — the inference was
simply wrong for players outside the test set, and a test set of twenty stars
cannot find that.

The deeper cause: **`PSKI` is not consistently scaled across community rosters.**
Different roster creators used the field differently, so averaging across sixteen
files produced errors that no single-file check would reveal.

The rule: when a named column exists, use it. An inferred field that validates on
a sample is still an inference, and the sample will not contain the cases that
break it.

---

## Ask what produced the earlier data before trying to recreate it

Hours were spent trying to statistically locate a skin-tone field in six
`FBCHUNKS` Madden files — searching by correlation, by cross-year stability, by
distribution shape. It half-worked and was never trustworthy.

The project documentation already recorded that earlier appearance data came from
disc `PLAY` table CSVs exported with Xtreme DB Editor, with `PSKI` and `PHCL` as
named columns. Asking "what produced the working data last time" would have
skipped the entire reverse-engineering effort.

The same pattern repeated with the table directory: five tables were visible at
offset 0x40, and the coach table was assumed absent. It was at 0x18, along with
five other tables. The user's instinct — "that coach data has to be somewhere in
Madden files, they render the coaches" — was right, and it was right because it
reasoned from what the product obviously does rather than from what the parser
happened to show.

---

## A field that renders identically is not necessarily one value

The beard vocabulary has eight tokens but the in-game editor cycles through seven
options. `f1` and `f2` render the same. Deducing the mapping from the cycle alone
would have shifted every token by one from that point on.

The user caught this by noticing there were "a clean shaven and a very subtle
stubble that you may be confusing for a second clean shaven." Two visually similar
options, one of which the assistant had merged.

The rule: when mapping a menu cycle onto a token list, confirm the counts match
before assuming position N in the cycle is token N.

---

## Photo measurement: what a headshot can and cannot give

Established while building the appearance measurement pipeline:

- **Skin tone from cheek pixels beats Madden's own field.** It caught two errors
  the Madden data contained
- **Hair colour from crown pixels works**: black 14, brown 38, light brown 79,
  blond 110 in median luminance. Cleanly ordered
- **Facial hair works** by comparing moustache, chin and jaw zones against the
  cheek baseline. The pattern of which zones are dark separates moustache from
  chin strap from full beard
- **Hair length mostly does not work.** Only the zone directly above the crown is
  reliable; anything beside or below the head hits the jersey

Roughly **half of all NFL headshot URLs return a helmet silhouette**, not a face.
Any estimate of coverage must account for this — the URL count is roughly double
the usable count.

---

## Score every source file separately — provenance does not predict quality

Seventeen Madden CSVs were held in one session for the first time on 2026-08-31
and scored individually for skin signal. Seven carry none. Two of those seven
had already been used in builds.

The failures do not follow provenance. `2003`, `2004` and `2013` are plain
year-named EA-derived files, the same class as `2005`–`2008`, which scored a
perfect 1.000. The fan-made JINX files scored 0.92–0.98 and beat all three.

What predicts failure is the **distribution**, not the maker. Every failing file
has one `PSKI` value swollen to 29–92% of the league. In `2014-SB-XLIX`, 92% of
players sit on a single value.

**Print the distribution before trusting a file. If one value holds more than
about a third of the league, the field is collapsed.** That screen costs ten
seconds and needs no anchor set. Anchor testing is the confirmation, not the
first move.

Full table in `PGM3_SOURCE_QUALITY.md`.

---

## Agreement across files is not independence — weight by lineage

Files that descend from each other share their errors. The four EA files agree
with each other 99.4–99.8%; the five JINX files agree 96.4–100%. Four JINX files
agreeing is one vote, not four.

Measured: players with any EA coverage scored **100%** on 83 anchors. JINX-only
players scored 88.5% on 52. The JINX errors cluster on Burrow, Mayfield, Crosby
and Wirfs — recent stars, all read dark across all four files.

That clustering is the signature of human judgement, and it points the wrong
way from intuition: a fan setting values by eye gets obscure players right by
default and makes visible errors on the ones they have an opinion about.

**Report coverage by source family, never by file count.** "EA-backed" and
"JINX-only" are the useful labels; "agreed by six files" is misleading.

---

## The registry stores one face, but seasons legitimately differ — apply the family, never the whole face

Caught by Ryan on 2026-08-31, after the roster files had already been handed over.

The face registry holds one appearance array per player. Seasons are supposed to
differ on the **variant letter** in the head, nose and mouth slots, because face
shape is derived from age and weight and players age between builds. Writing the
registry's array wholesale into a season overwrites that.

Measured damage from doing it: head **family** differed across seasons for 146
players where the published baseline was 0, and the aging variant dropped from
1,096 players to 926.

Two separate bugs in one operation:
- writing the whole array flattened the aging
- rebuilding only some seasons left players inconsistent either side of the boundary

**Rewrite only the family digit in slots 0, 5 and 6, keep whatever variant that
season already had, and rebuild every season the registry touches.** After the
fix: family differs 0, aging variant 1,096, hair 0 — all matching baseline.

The check that caught it is worth keeping as a standing test: group by
name+position across seasons, then assert family constant, hair constant,
variant free to vary.

---

## Namesake filtering: position adjacency merges fathers and sons

Keying votes on name + position is correct for avoiding namesakes, but it blocks
legitimate matches when a player changes position between a source file and our
registry — Anthony Spencer is OLB in Madden and DE in our files.

Recovering those matches by **position adjacency** looks reasonable and is not.
Applied to 322 candidates it would have merged Antoine Winfield, Jon Runyan,
Kris Jenkins, Jeremiah Trotter and Michael Pittman — every one a father-and-son
pair playing adjacent positions.

**The same-file test cannot catch generational namesakes**, because father and
son never appear in the same file. It removed 48 of 322 and let all five pairs
through.

What worked, in order:
1. same-file test — both positions inside one file means two people (48 removed)
2. source disagreement — the source itself splits across the two positions (2)
3. **era test** — the source's era must overlap the player's actual seasons (58)
4. **rostered-only seasons** — prospect records are future players, not
   contemporaries (104)

Step 4 matters on its own: Jimmy Smith the Ravens corner passed the era test
because he appears in the 2007 and 2010 files as a draft prospect. Filtering to
rostered seasons dropped him.

322 candidates became 29. Jason Taylor survived correctly — 2010, Jets, age 36,
playing OLB after a career at DE.

---

## A project file replaced mid-session stops being a "before" reference

The updated face registry was added to project context partway through the
2026-08-31 session. A later diff of "project copy versus new output" returned
**zero changes**, because both were now the new version.

The count assertion caught it — zero was implausible and obviously wrong. Had
the operation been one where zero was plausible, it would have shipped.

Related to the stale-artifact rule but the opposite direction: the usual failure
is reading an old copy, this one is losing the old copy. **When a comparison
needs a before state, snapshot it in the session rather than assuming a path
still holds it.**

---

## Selection is not a hit rate

Asked on 2026-08-31 to label skin for the whole registry on the grounds of
having been right every time so far, the honest answer was no.

Every correct call had been on a player chosen precisely because confidence was
high. Players outside that set were skipped — 30 of 182 in one pass. That is
selection, not accuracy, and it does not extend to a population where **over
half the registry is rated under 70**.

Extending it would have meant inferring from name patterns and position, and
producing confident labels for thousands of real people from nothing. Worse than
a noisy automated source, because the errors would be systematic and would look
authoritative.

What the knowledge was actually good for: a **154-player calibration set** that
scored seventeen source files and unlocked 595 measured fixes. Small, high
confidence, used to validate a large source rather than to replace one.

Partial validation arrived later: of 97 hand-labels, 53 fell within EA coverage
and 53 agreed.

---

## A hand edit is locked — provenance follows who decided, not what found it

**Ruling, 2026-08-31: anything Ryan sets by hand in game, player or coach, is
verified and can never be overwritten by an automated pass.** However well a
source scores, a person looking at the rendered face outranks it. A pass that
disagrees with a verified key skips it and logs the disagreement.

This exists because it was broken. Six faces Ryan edited in game were filed as
`_labelled_keys` — the overwritable block — because an automated diff was what
surfaced them. The note on that block said a better source *should* overwrite it.
The EA consensus pass then did exactly that to **Tony Gonzalez**, replacing the
`Head3b` he had set by hand with `Head4c`.

Five of the six survived only because EA agreed with them. Gonzalez did not,
because he is of mixed heritage and a binary light/dark source cannot express a
family-3 call made by eye. The single edit that carried the most human judgement
was the single edit that got destroyed — that is the general shape of this
failure, not bad luck.

**The filing was the error, not the scoring.** The diff *found* the edits; Ryan
*made* them. Ask who made the decision, never which process surfaced it.

---

## Value 1 means "don't know" — forcing it created a bias I then blamed on the files

Every Madden `PSKI` field has a middle value, and it carries no information.
Measured across six community files against 378 anchors:

| PSKI | anchors | % actually dark |
|---|---|---|
| 0 | 148 | 6% |
| 1 | 53 | **49%** |
| 2 | 177 | 97% |

Values 0 and 2 are 94–97% accurate. **Value 1 is a coin flip.** It is an unknown
marker, not a middle tone.

Forcing it to one side produced everything that looked like source bias. Assigning
it dark made JINX call 84.9% of the league dark against a real 65–67%; assigning
it light made ROJO call only 51.7%. Both "biases" were the threshold, not the
file. Three separate methods were built to work around a problem that did not
exist, and two of them were abandoned as failures.

**Abstain on the middle value.** Accuracy went 95.5% → 98.4% and registry coverage
27% → 63% from that one change.

The general form: when several independent sources all appear biased in ways that
do not match their measured ranking accuracy, suspect the reader before the data.

---

## Coach faces were already correct — audit before planning work

Staff appearance had never been checked and was assumed to need the same repair
the players did. It did not.

135 coaches audited against the 2005 and 2008 `COCH` files (coach `CSKI` scores
AUC 0.92–0.93 on 54 anchors, and is correctly calibrated at ~21% dark). **Six
mismatches, and the registry was right in all six** — the file called Belichick
dark, Leslie Frazier light, and put Norm Chow, Stan Kwan and Ron Rivera on the
dark side of a binary that cannot represent them.

Registry staff distribution: 24.1% dark against the file's 21%. Agreed.

Also confirmed: **coach faces are a single look, identical across every season.**
244 staff appear in two or more published files and not one byte of the appearance
array differs. Unlike players, there is no aging variant — writing the whole array
is correct for staff and wrong for players.

An hour of measurement removed four items from a five-item plan.

---

## Hair colour: reliable for black, meaningless for shade

`PHCL` was checked for the first time on 2026-08-31.

- **Black vs non-black is 98% accurate** on 775 observations. Black players read
  `PHCL 0` almost without exception.
- **Shade is not.** Known blond players read blond only 18% of the time and brown
  47%. Brown and light brown are effectively interchangeable.

The registry agrees with the source on black vs non-black for **8,930 of 8,998
unanimous cases — 99.2%**. Hair colour was never broken the way skin was.

Roughly a quarter of the league sits in the blond/brown/light-brown muddle and
**nothing available can resolve it.** Do not build a pass that pretends otherwise.

**Also: hair colour survived in all seven files whose skin field collapsed.**
2003, 2004, 2013, 2011, 2012, 2014 and 2015 are worthless for skin and fine for
hair. Source quality is per field, not per file.

---

## Assertions earn their keep on the operations that look trivial

Two entries were about to be "fixed" in the coach audit on the strength of a
summary that had inverted the direction of its own comparison — the `should_be`
column came from the source file, not from judgement, and was read backwards. The
write would have made the archive worse.

Nothing caught it except an assertion that the set of moved records matched the
set of intended records. It failed because the intended change was already the
current value.

The operation was two rows. It was the smallest write of the session and the only
one that was wrong.

---

## Scouts and physios are generated — a deliberate exception to no-invented-humans

**Ruling (Ryan, 2026-08-31): keep generating them.** Real NFL scouting and medical
staffs are not documented for any season this project covers, and inventing a
plausible name is better than shipping an empty slot or attaching a real coach's
name to a job he never held.

This is the one place the no-invented-humans principle is deliberately set aside,
and it has been the practice since the first build without ever being written
down. The measurement that establishes it was already true: **1,687 distinct
scout and physio names across seven published seasons, 0–7% recurrence between
seasons, and almost no overlap with the real coach pool.** Roughly 160 invented
people per season.

The reason to record it rather than leave it implicit: a future session finding
1,687 undocumented humans in the files will either re-litigate the question or
quietly start researching them. Both waste a session. The exception is narrow —
**scouts and physios only.** Coaches are researched, and the free-agent coaching
pool rule (real names form a clean top block, invented names strictly below)
still stands.

---

## A source file's tables can come from different seasons — date each one independently

The 2000 Madden export ships two tables. `PLAY` is genuinely the 2000 season.
`COCH` is the **stock Madden 08 coach table** — 2007 staffs, sitting in a file
named for 2000, in the same archive, in the same 68-column schema every other
`COCH` export uses.

It was caught by reading the head coaches out and recognising them: Tomlin at
Pittsburgh, McCarthy at Green Bay, Kiffin at Oakland, Petrino at Atlanta, Payton
at New Orleans. Every identifiable name is 2007. Nothing structural was wrong
with the file — the schema validated, the row count was normal, the ratings were
in range. Only the identities gave it away.

**Date every table in a source file against known facts of the season it claims,
before using any of it.** The filename dates the archive, not its contents. A
community modder replacing the player table and leaving the coach table at stock
produces exactly this, and it is invisible to every structural check.

Consequence for 2000: all 31 coaching staffs were researched from PFR team season
pages instead. That work is in `sources/coaches_2000.csv` and cost most of a
session. Finding it after the staff file was built would have cost the build too.

The same shape has now appeared twice. `TGID 0` in the same `PLAY` table is 80
rows of 2007-era players — **90% name-match against the published 2007 file,
against 3.7% for the real free agent pool.** A brief described it as the free
agent pool. It is Madden 08 base-roster contamination. Contamination in one table
is a reason to suspect the others.

---

## Two columns holding the same field are not interchangeable — pick one and record why

The 2000 `PLAY` table carries three such pairs, and they behave differently:

- **`PTSA` vs `PVTS`** — total contract value. They **disagree on 449 rows**,
  median 563 against 498. Not a duplicate; one is stale. **Use `PTSA`.**
- **`PVSB` vs `PSBO`** — signing bonus. Identical on every row of the file.
  Either works; use `PSBO`, which the handoff already names.
- **`PGID` vs `POID`** — identical on **2,469 of 2,575 rows (95.9%)**. Every one
  of the 106 differences sits in `TGID` 33 and 34, the invented filler teams. On
  the real cohort the pair is exact.

That last one is why the check has to be scoped. Measured across the whole file,
`PGID == POID` reads as false and looks like a finding. Measured on the cohort
actually being built, it is true. **Run the comparison on the real cohort, not
the raw file** — the same rule as "find the real cohort before measuring
anything", applied to column identity rather than correlation.

Where two columns disagree, the choice is a ruling and belongs in the build log
with the row count and the direction of the difference. A later session that
finds `PVTS` and doesn't know why it was passed over will try it.

---

## Check the top of every numeric column before assuming 0–99

**Nine columns in the 2000 `PLAY` table exceed 99.** A parser that clamps or
`uint8`s an attribute silently truncates them, and the result is a plausible
value in the right range for the wrong player.

| column | max | rows over 99 |
|---|---|---|
| `PCHS` | 109 | 22 |
| `PLSS` | 109 | 76 |
| `PAWR` | 108 | 1 |
| `PSBS` | 107 | 10 |
| `PTGH` | 104 | 1 |
| `PTHP` | 104 | 1 |
| `PFCS` | 103 | 2 |
| `PLPL` | 100 | 510 |
| `PMOR` | 100 | 915 |

`PLPL` and `PMOR` are personality fields the build derives rather than sources,
so they do not affect 2000 — but they are on a 0–100 scale, not 0–99, and a
future build that does try to source them will clip nearly a thousand rows.

The single-row cases are the dangerous ones. `PAWR` at 108 is one player, and one
clipped value in 1,637 will never show up in a distribution check, a zero-pattern
comparison, or a median. **Print the max of every column you intend to read.**

---

## When the handoff names a recurring bug, check whether the source already solves it

Contract length has bitten this project repeatedly — the handoff documents it as
a shipped defect with an in-game symptom (the game refuses extensions when
`length` contradicts `draftSeason`). The fix has been reconstruction from a
rookie ladder every time.

**`PCYL` is contract years remaining. It was in the source all along.**
`PCYL ≤ PCON` holds on **1,637 of 1,637** rostered rows, and **31.8% sit at one
year remaining against a published target of 34–39%** — close enough that the
field is real and only lightly off the target distribution.

`PCON` is total length and is the field previous builds took at face value. That
is the bug: the remaining-years field existed, was never read, and the value that
was read meant something else.

**Before reconstructing a field, audit the source for a column that already holds
it.** The recurring-bug list in the handoff is a list of fields worth searching
the source for, not just a list of things to check afterwards.

---

## 2000 build — audit findings

Findings from the source audit, recorded because they exist nowhere else. General
lessons are in the sections above; this is the 2000-specific reference.

### Cohort

| `TGID` | rows | what it is |
|---|---|---|
| 1–31 | **1,637** | the real 2000 rosters — 31 teams |
| 32 | 52 | Houston Texans placeholder. Every name reads `Texans CB #20`. The franchise did not exist until 2002 |
| 33, 34 | 53, 53 | **Detroit Silverdome** and **Seattle Kingdome** — stadium entries, not generic filler. Structural slots that will appear in other Madden files of this era too |
| 0 | 80 | **EA's own studio team slot, "Tiburon Sharks"** — occupied by Madden 08 base-roster contamination (see above). Both facts are true and complementary: the slot is a permanent EA placeholder, and what is sitting in it here is 2007-era players at a 90% name match to the published 2007 file. That is why the rows read like real players rather than like obvious filler |
| 1009 | 600 | free agents |
| 1014 | 94 | free agents |
| 403 | 1 | **Joe Montana**, `POVR` 99, age 33, 19 years pro — a Madden legend card. He retired after 1994. The `TEAM` table names `TGID` 403 **"NFC Hall of Fame"**, which confirms the reading independently |
| 1008 | 1 | one row named `No Name` |
| 1023 | 4 | four rows named `New Player`, `POVR` 27 |

**The table now accounts for all 2,575 rows.** It previously summed to 2,569 and
the six-row remainder was not recorded anywhere. All six are engine artifacts and
all six are already excluded by the `1–31` + `1009`/`1014` rule, so nothing about
the build changes — but an unexplained remainder in a cohort table is the exact
shape of the thing this project keeps getting caught by, and a later session
finding six unaccounted rows has no way to tell "verified as junk" from "never
looked at". Verified independently by Ryan, 2026-08-31.

**Ruling (Ryan, 2026-08-31): drop `TGID` 32.** 52 invented players on a franchise
that did not exist that season. Drop 0, 33 and 34 for the same reason.

**Ruling (Ryan, 2026-08-31): keep all 694 free agents** — `TGID` 1009 + 1014.

### Fields

- **`PBTK` → `trucking`**, correlation **0.882**. Not in the handoff's direct-map
  list; add it.
- **`PDRO` is a real draft round — a cross-check, not a source.** Correlation
  **0.796** with published `draftNum`, and `PDRO == 15` is the undrafted sentinel
  (198 rows), of which **96.8% carry the 224 floor**.
  **Ruling (Ryan, 2026-08-31): `draftNum` still comes from nflverse
  `draft_picks`, which carries the actual pick number.** 0.796 is good enough to
  identify undrafted players and to sanity-check a round. It is not good enough
  to source a pick number from. Use `PDRO` to catch disagreements with nflverse,
  not to fill the field.
  Both figures reproduced independently on a fresh clone, 2026-08-31: 629 players
  matched on name and position with any name held at more than one position
  dropped, control `PSPD` → speed at +0.889.
- **`PDPI` is not a pick number. Reject it.** Correlation 0.152, with 562 rows
  parked on sentinel 33. `draftNum` comes from nflverse.
- **Personality fields do not source from this CSV.** `PEGO`, `PMOR`, `PIMP`,
  `PLPL`, `PTEN`, `PVCO`, `PKRT`, `PYWT`, `PFEx` and `PTAL` were tested against
  `loyalty`, `greed`, `ambition`, `discipline` and the five unsourceable
  attributes. **Nothing above 0.34, most under 0.1.** Keep deriving them.

### Skin

`PSKI` is **four-level** in this file, not three:

| value | share | reading |
|---|---|---|
| 0 | 32.4% | light |
| 1 | 11.1% | **bimodal, ~54% dark — abstain** |
| 2 | 30.0% | dark |
| 3 | 26.5% | dark |

Anchor-tested at **19/20 light and 17/17 dark**. Value 1 is not a middle tone;
forcing it to one side is the exact error recorded under "Value 1 means don't
know". Abstain, per `PGM3_SOURCE_QUALITY.md`.

### Ratings — the inflation traps are live

PS2-era inflation is present and concentrated where the handoff says it will be.
Measured on the rostered cohort: the kicker/punter group sits at **median
`POVR` 93** and fullbacks at **86.5**, against a league median of 78.

Rescale **per position**, not cohort-wide. A cohort-wide rescale puts kickers and
punters at the top of the league — that is a documented past failure, and this
file would reproduce it.

---

---

## A sentinel landing on a categorical value is stronger evidence than a correlation

When `PDRO` was checked against published `draftNum`, the headline number was a
correlation of **0.796**. The number that actually settled it was different:
`PDRO == 15` is the undrafted sentinel, and **60 of those 62 players carry the
published 224 undrafted floor — 96.8%.**

The correlation is the weaker evidence. A field that is merely *related* to draft
position — experience, age, rating, anything that drifts with seniority — will
produce 0.7-something against pick number without being a round at all. The
correlation says the two move together. It does not say the field means what the
name suggests.

The categorical match says more. There is no way for an unrelated field to put a
specific value on 60 of 62 players who all share one specific published value
unless the two encode the same fact. **A correlation is consistent with many
explanations; an exact agreement on a sentinel is consistent with very few.**

The general form: **when testing what a source field means, look for the discrete
cases before reading the correlation.** Sentinels, floors, zero-patterns and
saturated values are where a field either agrees with its supposed meaning or
does not, and the answer is close to binary. `PDPI` failed exactly this test from
the other direction — 562 rows parked on sentinel 33, which corresponds to
nothing in `draftNum`, and its 0.152 correlation was never the point.

This is the same principle as "a plausible distribution is not evidence of
signal" and "a correct marginal is the weakest evidence a derived field is
right", applied to source identification rather than to derived output. A
continuous summary statistic is the least discriminating thing available. Reach
for the categorical structure first.

---

## Birth date is the namesake disambiguator — a looser position rule is the wrong fix

Worked instance from the 2000 Houston selection, 2026-08-31.

The 60-man core had been chosen on name-only matching against nflverse. Making
the join position-aware dropped it to 53 and killed the known false positive —
**Chris Miller**, whose Baylor namesake turns out not to be a quarterback at all
but a **safety born 1997**, two years old in the season being built.

Then the audit that matters: **for every player a name-only join would have taken
and the position-aware join rejected, check whether the rejection was right.**
Eleven such players. Four were real and were being lost:

- **Van Malone** — Madden `CB`, nflverse `S`. The same man; defensive backs are
  labelled inconsistently between sources.
- **Brian Waters** — Madden `TE`, nflverse `G`. A real position convert who
  entered the league as a tight end and became a Pro Bowl guard. **The handoff
  already warns about exactly this** (Peppers DE→OLB, Klecko DT→FB) and it still
  caught us, because the guard was written before the warning was consulted.
- **Kevin Smith** and **Aaron Wallace** — both dropped as "ambiguous" against
  namesakes born **1993** and **2004**.

**The tempting fix is to loosen the position rule. That is wrong** — it re-admits
Chris Miller. Position cannot separate these cases because in two of them the
position genuinely differs for the same man, and in the other two it genuinely
matches for different men. Position is carrying two jobs and can only do one.

**The fix is a disambiguator the collision does not share: birth date.** An era
filter (aged 20–45 in the season being built, and within six years of the Madden
`PAGE`) removes every confirmed false positive — the 1997 safety, a 2004 Texas
A&M defensive end, a 2002 Texas A&M tackle — and touches no real player. Position
then goes back to being a family-level tiebreaker, which is all it was ever good
for.

Where birth date still ties, reach for the next unshared field rather than
guessing. Two real Kevin Smiths, both defensive backs, both of the right era,
`draft_year` empty for both — settled on **`PYRP` 8**, because Dallas's 1992
first-round corner played 1992–99, exactly eight seasons. That is the categorical
structure the section below on sentinels argues for, and it is stronger evidence
than any similarity score.

Final count 57, from 60. Two of the seven removed were false positives; the rest
failed to match nflverse at all. Nine players were **gained** by splitting the
college field on `;` — nflverse stores `Houston; Alvin Community College`, and an
exact match had been dropping Andre Ware, the one player the whole Houston
premise rests on.

**General form: when a guard drops records, audit the drops before shipping it.**
A join that removes false positives and real players in the same pass looks
identical from the count alone.

---

## An adjacent-year source's error can be a bias rather than noise — measure the sign before damping

Measured 2026-08-31 for the 2001 draft class, which has no rookie-year Madden
export and must source from `2003 - PLAY.csv` at a two-year gap.

Four independent replicates (the 2003–2006 classes, each measured against its own
rookie-year file at gaps of one and two years), cohort defined by **nflverse draft
year, not `PYRP`**:

| | real attributes | percentile fill |
|---|---|---|
| gap 1 | **2.39** | 6.97 |
| gap 2 | **3.15** | 7.26 |

Gap 1 reproducing the documented 2.35 at 2.39 is the check that the method is
sound; run that kind of control first.

**Ruling (Ryan, 2026-08-31): tier 2 for the 2001 class.** Gap 2 is still 2.3×
better than percentile fill. But the damage is not spread evenly — it sits almost
entirely in one column:

| attr | gap 1 | gap 2 | Δ |
|---|---|---|---|
| `PAWR` | 6.34 | **9.81** | **+3.47** |
| `PINJ` | 2.82 | 4.59 | +1.77 |
| every other | 0.93–3.37 | 1.19–4.17 | +0.26 to +0.90 |

**Two obvious fixes for `PAWR` were both tested and both lost.** Percentile fill
scores **13.41** against the uncorrected 9.95 — worse than the thing it was meant
to replace. Shrinking toward the position median finds an optimum of λ = 0.05 and
buys 0.01 MAE, i.e. nothing.

They lost because the error is a **bias, not noise**: the mean signed error is
**+9.28**, the two-years-later file reading systematically high, exactly as the
handoff's "awareness genuinely grows" predicts. Damping and percentile fill both
attack variance. A bias needs a shift.

**A constant −9 offset takes `PAWR` from 9.95 to 6.82**, and it generalises —
leave-one-class-out, fitting the offset on three classes and testing on the
fourth, improves every fold: 8.77→6.16, 12.62→9.08, 7.78→6.33, 10.07→6.28.

**This does not overturn the handoff's "do not age-adjust attributes."** That
finding was measured at a one-year gap, where the bias is +5.35 and correcting it
buys 0.6–1.5 MAE — genuinely inside the noise, as it says. At two years the bias
doubles and the correction pays. The rule is gap-dependent, and the handoff's
version is the gap-1 case.

**Apply it at gap 2 only — not gap 1, not gap 0.** In this build that means the
2001 class and nothing else; 2002, 2003 and 2004 source from their own or an
adjacent year and take no correction. A correction fitted at one gap is
meaningless at another, exactly as a bias correction fitted to one scale is
meaningless on another. `tools/build_2000.py` asserts this.

**The sign, stated so nobody applies it backwards.** The `2003 - PLAY.csv` source
has **two seasons of awareness growth already baked in** relative to the 2001
rookie year being built. So the source reads high and we **subtract** to recover
the pre-rookie state. The measured mean signed error is **+9.28** (prediction
minus truth), which is what that direction predicts. Adding the offset instead of
subtracting it would roughly double the error.

**General form: before damping a source, take the mean *signed* error.** Damping
and percentile fill treat the error as noise. If it is a bias they make things
worse while looking principled, and the sign is one line of arithmetic.


---

## Every tool must run from a clean clone — no absolute paths

`tools/build_coaches_2000.py` carried `REPO = '/Users/ryannecci/Documents/pocketgm-rosters'`
and wrote to `sources/pfr/`, a directory that no longer exists in the repo. Run
from a fresh clone it would have written its output **outside the repo
entirely**, reported success, and left `sources/coaches_2000.csv` untouched. The
next session would have diffed a file that had never been rewritten.

This is the same defect as a stale artifact and it has the same signature: **it
works on the machine that wrote it, and only there.** The stale-CDN rule exists
because two copies of a file drift; an absolute path is the same failure with the
drift happening between machines instead of between fetches.

**Rule: no tool in `tools/` may contain an absolute path.** Derive the repo root
from `__file__`:

```python
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

**Corollary, and the reason `2000.ros` was committed:** a tool that depends on a
file only present on one machine has the same defect as a hardcoded path. The
2000 `TGID` -> team map was read out of the `TEAM` table of a `2000.ros` that
existed in one local working copy and in no clone. The map is correct — it
spot-checks 12/12 against known players, all three relocations included — but
nobody could have re-derived or checked it. Commit the source, or the derivation
is unreproducible whatever the value turns out to be.

---

## A map fitted on the players who match is fitted on the players who survive

The 2000 appearance build reproduced the 1986 signature and was caught by the
same check: **dark share in band, total light share in band, one family running
hot.** Family 1 projected at 29.7% of the file against a published ceiling of
27.4% (2004) and a union of 17.5%.

The first hypothesis was that the map had been fitted against the two published
files with the highest family-1 shares, 2004 and 2007. **Wrong** — refitting
against all seven files gives 31.6% against 31.5%, indistinguishable. The choice
of comparison files was not the problem.

**The problem was who matches at all.** The map was fitted on 2000 players who
also appear in a published roster, and that cohort is not a league:

- **Compositionally** it over-weights the long-career positions. QB/K/P/OL/TE are
  39.3% of the matched subset against 33.8% of the full 2000 cohort — kickers
  double, punters double, quarterbacks up half again.
- **And the skew survives conditioning on position**, which is what makes it more
  than a mix effect. Light offensive tackles present in the 2000 source are
  **96.7% family 1** against 63.6% for those absent; running backs 73.3% against
  38.5%. The gap holds inside every published file, so it is not an artifact of
  averaging files with different conventions.

Fitted there, the light band came out 88/6/6 across families 1/2/3. The published
population says 54/25/21. Refitting on the population rather than the matched
subset brings family 1 to 24.2%, inside the published range.

**The general form is the cohort rule applied to a fitted map rather than to a
measurement.** "Find the real cohort before measuring anything" is usually read
as a rule about the thing being measured. It applies just as hard to the *join*:
a map calibrated on records that matched is calibrated on whatever made them
match. Here that was career length, and career length correlates with the thing
being mapped.

**Ask what the join selected for before trusting anything fitted through it.**
The tell is available cheaply — compare the position mix of the matched subset
against the full cohort, then check whether the effect survives within position.
Two lines each.

### Two things worth carrying

**`PSKI` decides light versus dark and nothing finer.** That is what it is scored
for and what the conditional pass tests. It carries no information about which
light family, so the within-band spread must come from the published population.
Fitting the internal spread through `PSKI` is fitting noise through a biased
join.

**The published files do not agree with each other on the internal spread — and
it is seven conventions, not three.** Within-light f1/f2/f3:

| file | f1 | f2 | f3 |
|---|---|---|---|
| 1986 | 50.2 | 25.7 | 24.1 |
| 2004 | 77.6 | 8.0 | 14.4 |
| 2007 | 66.8 | 10.1 | 23.1 |
| 2010 | 34.9 | 18.3 | 46.8 |
| 2013 | 34.3 | 23.6 | 42.1 |
| 2017 | 64.6 | 30.2 | 5.2 |
| 2021 | 48.5 | 49.7 | 1.8 |

**Family 3 runs from 1.8% to 46.8% of the light band.** That is not one
convention with noise; every file did something different.

**So 54/25/21 is an ARBITRARY DEFAULT, not a fit, and must not be read as one.**
It is the pooled union of seven incompatible populations, which makes it a
manufactured eighth convention matching none of them — the same
pooling-manufactures-a-rule failure this document records elsewhere, in a new
place. It was chosen because there is no source for within-light family, `PSKI`
does not carry it, and every alternative is equally arbitrary. **The evidence
says the target is undefined.** A later session must not treat the union as
authoritative or build anything on it; if a real source for within-light family
ever appears, it supersedes this outright with no argument needed.

Consequence: the `faces` distribution check can only ever catch gross outliers
like 1986, and the build-time assertion added here inherits that weakness — with
family 3 spanning 0.7–14.6% overall, the band passes almost anything. It is a
floor, not a substitute for looking.

**The check is now an assertion in `tools/build_2000.py`, not a reviewer's job.**
Every head family is compared against the min/max across the published files and
the build fails if one falls outside. `pgm3_validate.py faces` still runs at
stage 10, but by then the registry has been applied over the top and the defect
is being diagnosed through two layers.

---

## Name-only lookups: third sighting, and the ambiguous set is the finding

This project's rule is that any lookup keyed on a player name is a bug until it
is disambiguated. It has now been rediscovered three times, in three different
places, by three different routes:

1. **2013 build — "David Johnson".** Two real players, a running back and a
   tight end/fullback. Caught during that build. **It was never written into the
   repo** and lived only in a session summary, which is why it could be cited in
   2026 as though it were documented and turn out not to be. It is written here
   now.
2. **2000 Houston selection.** Chris Miller's Baylor namesake is a safety born
   1997; Anthony Lucas's Texas A&M namesake a defensive end born 2004. See the
   birth-date precedent above.
3. **2000 fullback cohort.** Building the FB rating target by name against the
   Madden exports, **75 names appear as both `PPOS` 2 (FB) and `PPOS` 1 (HB)**
   across the seventeen files, against 448 that are only ever FB.

**The third one is worth dwelling on because the ambiguous set is not noise, it
is 14% of the population.** A cohort built by taking every name ever labelled FB
would have pulled in 75 records that are sometimes halfbacks — and since the
whole point of that cohort is to establish that fullbacks rate *lower* than
halfbacks, contaminating it with halfbacks biases the target in exactly the
direction that defeats the correction. The error would have been invisible: the
cohort would still have looked like fullbacks, just rated a little high.

**Rule: when a cohort is built by name, count the ambiguous set and report it.**
Excluding 75 of 523 is a decision worth stating; silently including them is not a
decision at all. If the ambiguous set is large relative to the cohort, that is
itself evidence the key is too weak.

**And write the case down when it happens.** The David Johnson case was real,
was correctly diagnosed, and cost nothing at the time — then cost a round trip
in 2026 because it was cited from memory against a repo that did not contain it.
A finding that lives only in a conversation is a finding that will be
rediscovered.

---

## Inflation compresses the top of the source range, so trap positions arrive pre-tied

The handoff describes PS2-era Madden inflation as a scale problem: median 77–80
against a modern 71, fixed by rescaling per position. **There is a second form it
does not describe, and a quantile map discards real information because of it.**

Measured on the 2000 rostered cohort, share of each position sitting on the
`POVR` 99 ceiling:

| position | at 99 | share |
|---|---|---|
| FB | 12 / 50 | **24.0%** |
| K | 5 / 37 | 13.5% |
| P | 4 / 31 | 12.9% |
| TE | 4 / 94 | 4.3% |
| every other position | ≤ 3 | ≤ 3.2% |

League-wide 2.5%; the published files carry 0.7–0.9% at their own maximum.

**The pile-up is concentrated in exactly the three positions the inflation trap
already names.** That is not a coincidence — it is the same cause seen from the
other end. Madden grades kickers on leg strength and fullbacks on blocking, and
those narrow criteria saturate: once a dozen fullbacks are all excellent blockers
there is nowhere above 99 to put them.

**Consequence: a quantile map silently discards the ordering.** A tie block maps
to its midrank, so all twelve fullbacks landed on rating 73 against a cohort
ceiling of 86 — arithmetically correct, and it threw away both the distinction
between Lorenzo Neal and Larry Centers and the entire top of the target range.

**No distribution check surfaces this.** The output median was right, the spread
was right, the per-position medians reproduced the published files within a
point. The defect is entirely inside one tie block.

**Fix: rank-map with a real secondary column rather than value-map.** Sort the
group by (primary, secondary) and assign target values by rank, so the top of the
source lands on the top of the target. The secondary must be a column the
position is actually played for — blocking for fullbacks, the kicking columns for
K and P.

**Check for it directly: print the size of the largest tie block per position,
not just the median.** A block of 12 in a group of 50 is invisible to every
summary statistic that was being computed at the time.

---

## A quantile map inherits its target's defects

Building 2000's attributes, `stamina` failed its conditional at rho 0.810 with a
discontinuous first decile — 32, then 75. The source was fine. **The target was
contaminated.**

The published files carry a block of players parked on value **1**:

| attribute | share of non-zero values | median | median excluding 1 |
|---|---|---|---|
| `stamina` | 9.4% | 83 | 84 |
| `zoneCover` | 9.1% | 81 | 82 |
| `manCover` | 5.8% | 79 | 80 |
| `greed` | 3.3% | 71 | 73 |

Three things identify it as a "no source data, default to 1" artifact rather than
a distribution: the players holding it are spread across every position and
concentrated among low-rated fringe players; **its share swings from 0% to 24.9%
between files** (2010 has none, 2017 has a quarter); and the median barely moves
when it is removed. A real low tail does none of those.

The 2000 source has no such block — `PSTA` runs 15 to 99 with no zeros and 5%
under 60. So its genuinely-low-stamina players were being mapped onto the
artifact.

Counts depend on the cohort, so **state it**: 1,267 rostered players sit at
stamina 1 across the seven files, or 1,622 counting every non-zero record
including prospects; 2017 reads 24.9% rostered or 18.0% overall. Two correct
measurements of different populations look like a disagreement otherwise.

**Rule: clean the target before mapping onto it, not just the source.** "Find the
real cohort before measuring anything" is normally applied to the input. A
quantile map has two populations and the same discipline applies to both — the
target is data too. The guard now drops value 1 from any target where it holds
over 2% of non-zero values and the median is above 20, and reports what it
dropped.

### Cleaning the target is not enough — recompute everything derived from it

The first version of this fix cleaned the quantile targets and then read the
**position-gating rate off the uncleaned data**. Same defect, one step later in
the pipeline.

`OLB` `manCover` looked 32.3% populated in the published rostered cohort. 62.3%
of those values are the fill, so the real rate is 12.2%. `OLB` `zoneCover` looked
31.6% populated and is actually **0%** — every single non-zero value is 1.

Chasing that turned up something worse. **`OLB` `manCover` takes only the values
1, 2 and 3**, across every file that has it at all, against `MLB` `manCover`'s
38–92. And it is absent entirely from 2004, 2007 and 2017 while 2013 and 2021
carry it for 100% of their OLBs. Whatever that field is, it is not coverage
skill, and mapping onto it was about to ship Derrick Brooks a `manCover` of 3.
Both OLB coverage fields are now gated off, which matches three published files
exactly.

**Generalised rule: a "rating" whose entire observed range sits at or below 10 is
fill, not a rating.** Check the range, not just the population share — a field
can be 100% populated and still carry nothing.

**And the general form: changing a population means rebuilding every statistic
taken from it.** This is the same shape as the existing rule that changing a
field means rebuilding every field derived from it. A cleaned distribution and a
stale rate computed from the dirty version is a contradiction that no single
check will catch, because each half is internally consistent.

This is worth stating because the defect is self-propagating. Every file built by
mapping onto the published files inherits their fill artifacts, which then makes
the next target slightly worse. Nothing catches it: the output median was right,
the spread was right, and only conditioning on the source showed the break.

---

## Judge a mapping in the population it was performed in

After the target was cleaned, `stamina` still read rho 0.847 pooled — below the
0.90 bar — and the next move would have been to go on adjusting a mapping that
was already exact.

**Within (cohort, position) the same mapping reads rho 0.999 median, 0.950
worst, across 30 groups.**

The map is fitted and applied per position. Pooling across positions mixes
fifteen separate maps whose scales legitimately differ, and the correlation drops
for a reason that has nothing to do with whether any individual map works. Speed
shows the identical pattern — 0.930 pooled, 0.999 within group — and speed was
never in doubt.

The handoff already says to compare cohort to cohort and position to position.
**The point here is that the rule applies to the check as much as to the data.**
A validation pass measured at the wrong altitude produces false failures, and a
false failure costs more than no check at all, because it sends you to modify
working code.

**Report both numbers and assert on the within-group one.** The pooled figure is
still informative — it measures how much position-to-position scale differences
move a field — but it is not the test.


---

## The reference union is not a specification

Three times in one session the published files were consulted as an authority and
found to disagree with each other:

- **Within-light skin family.** Seven files, seven conventions. Family 3 runs
  from 1.8% to 46.8% of the light band.
- **Fullback ratings.** 2004 has Alstott 76 and Neal 51; 2007 has Neal 83 at the
  cohort ceiling. Opposite orderings of the same two men.
- **`OLB` coverage.** Three files at exactly 0%, two at exactly 100%, one at
  3.9%, one at 32.2% — and where present the entire range is 1–3 against `MLB`'s
  38–92 in every file.

**The union of seven outputs is not a specification. When they disagree it
encodes the disagreement, and pooling manufactures an eighth convention that
matches none of them.**

`pgm3_validate.py` measures ranges against the union deliberately, and that is
right for its purpose — a range wide enough to contain every published file is a
sane guard against gross error. **It is not evidence of correctness.** "Matches
the union" means "is not obviously broken", and on a field where the files
disagree it can mean "reproduces the average of a defect and its absence".

**When the references disagree, say which ones you match and which you diverge
from, by name, with the reason.** For `OLB` coverage: this build matches 2004,
2007 and 2017, which gate the field off, and diverges from 2013 and 2021, which
populate it for 100% of their OLBs with values in a 1–3 range against a
positional norm of 38–92. That is reviewable in ten seconds. "Deviates from the
reference union" is not.

---

## When a fit's inputs turn out to be contaminated, measure the coefficients before assuming

`weights.json` was fitted on the 2010 and 2017 published rosters — the uncleaned
versions, including 2017's stamina-1 block. Having cleaned four fields out of the
quantile targets, the refit was still solving through coefficients derived from
the contaminated data.

**Measured rather than assumed.** Refitting per position on the same cohort with
contaminated records excluded (616 of 3,924, 15.7%):

- **Largest single coefficient move across all fifteen positions: 0.0079** (K
  `burst`). At an attribute range of 0–99 that is worth **0.79 rating points** for
  a player at the extreme, and far less for anyone normal.
- Median move per position: 0.0003–0.0020.
- R² 0.9992–0.9996 before, 0.9993–0.9996 after.

The direction is what theory predicts — a rated-70 player carrying stamina 1
tells the regression that stamina barely matters, so cleaning should raise its
coefficient, and it does in 9 of 14 positions.

**The reason it does not matter is relative, not absolute.** In `weights.json`
itself, `stamina` is at most **7.9% of the largest coefficient** in any position's
model (TE, +0.01654 against `passBlock` 0.20838) and a median of **0.6%** across
the fifteen. Worst case, an 80-point stamina swing moves TE's computed rating by
**1.3 points**.

Closed: no refit of `weights.json` is needed.

**State this as a ratio, never as an absolute bound.** An earlier version of this
entry said the coefficient was "within ±0.009 of zero at every position". That
was wrong twice over: the true maximum is 0.0165, and two positions exceed 0.009
— but more importantly **an absolute threshold is meaningless without the scale
of the model it sits in.** 0.0165 is negligible beside `passBlock` at 0.208 and
would be enormous beside a model whose coefficients were all 0.001. The number
also came from a fresh regression rather than from `weights.json`, which is what
the build actually solves through; check the artifact in use, not a
reconstruction of it.

The general form is that a fit's sensitivity to a contaminated input depends on
that input's coefficient **as a fraction of the model's largest**, and that ratio
is cheap to look at.

This is the third instance in one session of the same mistake — reading the
obvious property instead of the informative one. `OLB` `manCover` was 100%
populated and carried nothing, because the informative property was its range
(1–3) not its share. `stamina` read rho 0.847 pooled and 0.999 within position,
because the informative property was the altitude of the measurement. Here the
informative property is the coefficient's size relative to its own model. **When
a number is used to dismiss a concern, check what it is being compared against.**

---

## Salary is not predictable from rating — split the cohort before fitting

Measured 2026-08-31 against 62 real 2000 cap numbers from Over The Cap, matched
into the rostered cohort.

**Rating explains almost nothing.** Predicting log of the real 2000 cap number:

| cohort | n | rating alone | rating + yrs + log(pick) | log(pick) alone |
|---|---|---|---|---|
| all | 62 | R² 0.294 (adj 0.282) | 0.572 (adj **0.549**) | 0.297 |
| **rookie deals** (≤3 yrs) | 32 | 0.120 | 0.710 (adj **0.679**) | 0.610 |
| **veterans** (>3 yrs) | 30 | 0.032 (adj **−0.003**) | 0.218 (adj **0.127**) | 0.215 |

**For veterans, rating has an adjusted R² of −0.003 — it is worse than useless.**
The single number hides two regimes: rookie contracts are slot-driven and largely
predictable, veteran contracts are not predictable from anything in this project.

**The mechanism, from the residuals:** NFL salary tracks contract timing and draft
pedigree, not current performance. Tim Couch, rating 71, first overall pick, real
2000 cap **$5.25M**; Tom Brady, rating 73, sixth round, **$0.21M**. Marshall Faulk
at rating 98 earned less than Troy Aikman at 93 because one was mid-rookie-deal
and the other was a declining franchise quarterback on an old contract.

Even among veterans, **draft slot orders salary better than rating does** —
Spearman +0.443 against +0.171. Where you were drafted predicts what you earn
better than how good you are, years later.

**And `PTSA` is not a fallback.** Its overall Spearman of +0.417 against real cap
numbers comes entirely from the rookie tier (+0.500). **On veterans it is
+0.020 — zero.** A field can carry real signal in one cohort and none in another,
and a pooled correlation will average the two into something that looks usable.

**Rule: split by contract regime before fitting a salary model, and report each
tier separately.** A pooled adjusted R² of 0.549 reads as a mediocre model. The
truth is one good model (0.679) and one that does not exist (0.127), and only the
split shows which players the file will get right.

### The anchor set is not the league

Over The Cap's 2000 coverage is position leaders only — 62 usable players against
1,637 roster spots, and skewed hard:

| draft band | anchors | full cohort |
|---|---|---|
| round 1 | **54.8%** | 16.2% |
| rounds 5–7 | 8.1% | 21.4% |
| undrafted | 6.5% | 24.8% |
| *median pick* | **24** | **118** |

A model fitted on picks 1–31 and applied to pick 118 and undrafted players is
extrapolating past the edge of its data. This is the same defect as fitting the
skin map on players who appear in a published file: **the join selected for
notability, and notability correlates with the thing being modelled.** Say so
rather than quoting the R² alone.
