# PGM3 — Rulings and Precedents

Judgment calls already made, and why. These aren't rules derived from the files — they're decisions where the data allowed more than one answer. A new session should follow them rather than relitigate.

If a precedent looks wrong, say so and make the case. Don't quietly do something different.

---

## Accuracy vs. matching the existing files

**Ship real numbers even when the published files don't.** Payrolls in 2004, 2010 and 2017 aren't scaled to their eras — 2004 runs $179M salary against a real $80.6M cap. That was never a decision, just contracts fitted to PGM3's ceiling with nobody checking. 2007 ships at ~$100M against a real $109M cap, and that's correct. Don't inflate accurate data to match a defect.

**AMENDED 2026-08-31 — the general rule stands, the classification was wrong.**
"Don't inflate accurate data to match a defect" is still right. What was wrong
was calling the ~$196M payroll target a defect. **It is a game constraint.**
PGM3's salary cap is a fixed engine constant of about **$280M** and there is
**no cap field anywhere in the schema** — the game cannot know what year it
is. Ship era-accurate dollars and every team has ~$225M of room: nobody is cap
strapped, every signing is affordable, extensions never bind, and the whole
financial layer is inert.

**The evidence that it is a convention and not seven independent accidents:**
on the **top-53** basis the seven files read 197,400,001 / 197,424,500 /
197,426,500 / 197,428,500 / 197,429,000 / 197,427,000 / 197,426,500 — a **$29k
spread on $197.4M**, 0.015%, 1986 exact to the dollar. Seven eras agreeing to
0.015% is not a convention, it is a fitted constant. **Measure on the basis the
files were built on**: top-51 scatters by $1M and reads like a loose habit;
top-53 collapses to a single number. The wrong basis turned a fitted target
into something that looked arguable. The old note read that same spread
as "contracts fitted to PGM3's ceiling with nobody checking", which is the
right observation and the wrong conclusion — fitted to the ceiling **is** the
convention, because the ceiling is all the engine has.

**The narrowing: era accuracy governs everything except the dollar SCALE.**
Ratios, orderings, who is paid more than whom, the sourced anchors, the league
minimum — all era-accurate. The scale alone is set by the engine. One uniform
factor preserves every relationship while making the economy live, which is
why the fix is a multiply and not a refit.

**Cost of the misclassification:** the 2000 build shipped at $54.6M, was
flagged correctly by the build session as a divergence from all seven files,
and was signed off as deliberate. It took an in-game test — Green Bay with
$200M of room — to find it. **No check could have caught it**: `cross_year`
skips money fields by design because "they legitimately differ by era", which
is exactly the assumption at fault, and the `team_cap` guard passed because it
was handed the real 2000 cap as its parameter. A guard given the wrong
parameter passes and reads as evidence. Now gated by `median team payroll` in
`check_roster`, which compares against the published band.

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

## A fill and a floor look identical from the outside

**2026-08-31, Pass B2, rejected before any record was written.** Both are a
large block of records sharing one exact value. Nothing about the *value* tells
you which you are looking at — not its size, not its roundness, not how many
records hold it, not how sparse its neighbourhood is.

**What separates them is whether the population sharing the value has anything
else in common.**

- The stamina-1 block: no shared anything. An absence of data.
- The 2010 salary block: shared age (median 23), shared zero guarantee (99%),
  shared draft recency, and it sits in a **six-value monotone ladder** whose
  ratios decay 1.166 → 1.099 exactly as real minimum scales do. A coherent
  cohort — players on the league minimum for their accrued seasons.

**So the test is to characterise the population, not the value.** Group the
records holding the value and ask what else they share. A fill block is
heterogeneous in everything except the filled field; a floor block is
homogeneous in the thing that *causes* the floor.

This is the sharper form of the single-position detector written the same day —
that one asks whether a block is concentrated in one position, and this asks the
general question the position case is one instance of.

**Corollary, and the reason this nearly went wrong:** the spike detector built
for B2 flags our own 2000 file at ratio 14.6, and 2000 was built with an
explicit `min_salary()` floor whose values it reproduces to within $4. **Run a
new detector against a file whose provenance you know before trusting what it
says about files you do not.** A detector that condemns a known-good file is
measuring the wrong thing, and that is cheap to discover and expensive to miss.


## A single value held by one position is fill; a real tail spreads

**2026-08-31, Pass A1.** New detector, sharper than the `≤10 range` rule and it
catches cases that rule misses.

Repairing the `stamina == 1` block surfaced a second layer underneath it. The
tell was not the value's magnitude — it was its **position concentration**:

| file | block | positions |
|---|---|---|
| 2021 | 29 records at exactly **5** | **all WR** |
| 2021 | 9 at 16 / 8 at 34 | all OT / all DT |
| 2013 | 44 at 2, 23 at 4 | 11 positions — a smear, ambiguous |
| 2010, 2004 | nothing under 40 | the clean controls |

**2021's 29 receivers at stamina 5 are nowhere near the range floor**, so the
`≤10 range` detector does not see them. But a genuine low tail is produced by
individual players being bad at something, and bad players occur at every
position. A single value held by a single position is a default that was
written once and applied to a group.

Apply it to any field: group by value, and for values with a meaningful count,
count the distinct positions. One or two positions at a single exact value is
fill regardless of where the value sits in the range.

## Find the real cohort applies to a repair's SOURCE, not just its target

Same pass, and the more instructive half. The first run of the stamina repair
drew replacement values from "every record that is not 1" — and **that pool
still contained the other fill blocks**. The repair therefore *propagated* the
defect it was cleaning: 2021's stamina-2 block grew from 37 records to 51.

**What caught it was the conditional pass, not any distribution check.** The
`PSTA` deciles came out `[56, 63, 30, 65, 13, 68, 71, 66, 76, 89]` — 30 and 13
sitting mid-range. The marginal was fine; a distribution check passes this,
which is how the original defect shipped in the first place.

**"Find the real cohort before measuring anything" has always been stated about
the thing being measured. It applies with equal force to the population a
repair samples from.** A fix that draws from contaminated data launders the
contamination into records that did not have it, and every count still looks
right because the counts were never the problem.

## Scope fixed to the instances you happened to look at

**2026-08-31, third instance in one day.** The Pass A2 brief said staff ages
were wrong "archive-wide", generalised from Belichick reading 40, 43 and 52 in
2004, 2010 and 2017. The four files where he was **already exactly right** —
34, 55, 61, 69 — were not checked.

Measured, 1986, 2007, 2013 and 2021 were largely correct, 2013 at **102 of 106
exact**. A wholesale rewrite would have overwritten those with whatever the
source returned, false positives included. The targeted repair — rewrite only
where a sourced value exists *and disagrees* — moved 368 records instead of 896.

Same shape as the 132-face overlap and the 1986 Rookie cohort: **the boundary of
the evidence you gathered is not the boundary of the defect.** Before accepting
a scope, check the cases the evidence did not cover — especially the ones that
would show the scope is smaller, since those are the ones a repair destroys.


## Internal consistency finds impossibility, never wrongness

**2026-08-31, staff ages.** The 2000 staff file carried ages with essentially
no relationship to the men — Tony Dungy at 70 against a real 45, Jeff Fisher at
61 against 42, only 13 of 89 checkable coaches within ±2 years. Every check in
the suite passed.

The reason is worth stating exactly. The internal check available was
"age minus seasons coached ≥ 28", and it caught **two** records — Reeves
coaching 19 seasons by age 44, Mora 13 by 30. Those were the only *impossible*
ones. **Dungy at 70 with four seasons coached is perfectly consistent and 25
years wrong.** Consistency constrains a value against other values in the same
record; it cannot reach outside the file to the person.

**The distribution was the disguise:** median 49.5, range 30–72, sitting right
next to the published files. A plausible marginal with no per-person signal —
the same shape as the stamina bug (`PSTM` vs `PSTA`) and the appearance bug.
**Third instance of this exact failure mode. When a field's marginal looks
right, that is not weak evidence, it is no evidence, and the test is always to
check individuals against something outside the file.**

**And it propagated silently.** `startSeason` is a fitted function of age
(r ≈ −0.96 in every modern published file). A wrong age produced a wrong
`startSeason` **while the correlation stayed perfect**, because a function of a
bad input still fits its input. A derived field agreeing with its source proves
the derivation, never the source.

## Match on the occupation, not the name

Same investigation. nflverse `players.csv` looked like the obvious source for
coach birth dates and it is a trap: it matched 22 of 128 coaches and **4 were
false positives** — Marvin Lewis, Andy Reid, Bill Callahan and Jimmy Raye never
played in the NFL, and the Raye match was his son, the father/son merge this
project has logged before. An 18% false rate on the matches it did make.

**No mechanical discriminator separates them.** Career length fails: the false
hits had one-season careers, and so do Sylvester Croom and Sean Payton, who are
true matches.

**What worked was a source that carries the occupation.** One bulk Wikidata
SPARQL query filtered on `occupation = American football coach` resolved 98 of
126 in a single request, and the occupation filter is exactly the discriminator
a name lookup lacks — it separated both Moras, both Ken Andersons and both Jim
Johnsons without a judgement call. **Prefer a source with a role field over a
larger source without one.**

Operational note: Wikidata's `wbsearchentities` endpoint rate-limits hard
(HTTP 429 within ~15 requests, and backoff to 10s did not clear it). The SPARQL
endpoint takes a `VALUES` block of 126 names in one request and does not.


## A repair scoped to the overlap improves every metric and leaves the defect

**2026-08-31, building 2000.** Found 132 players whose skin family disagreed
between 1986 and 2000 while every other file agreed among themselves. The
obvious repair was to write those 132 into the face registry with 2000's
anchor-tested `PSKI` value.

It would have improved every signal available: the all-cohorts family
disagreement count falls from 163 toward 31, `pgm3_validate.py faces` stays
clean, cross-file consistency rises. **No check in this project would have
objected.**

It was still the wrong fix. 131 of the 132 sit in 1986's Rookie cohort, which
has ~1,334 members, none of them sourced. Repairing the 132 fixes the subset
that happens to overlap 2000, leaves ~1,200 unsourced records untouched, and
removes the very signal by which a later session would find them.

**The general form: a fix applied to the subset you can see improves every
metric while leaving the defect intact and less visible. That is worse than
not fixing it, because the metrics are how anyone later finds the problem.**

Related to "a correct marginal is the weakest evidence a derived field is
right" but not the same. That one is about a *field* being wrong while looking
right. This is about a *repair* being wrong while looking right. Same
mechanism underneath: measuring the visible subset.

**The trigger to name.** The scope of that fix was "what appears in both
files" — which has nothing to do with the defect, whose real boundary is a
cohort inside one file. **Whenever a fix is scoped by what appears in both of
two things, check whether that scope has any relationship to the defect.**
Overlap is a property of how you happened to look, not of what is broken.

## The proximate reason is a real finding, which is why it stops you

Same investigation. Asked why the 132 disagreed, the build session answered
that `faces_1986` keys include `teamID`, so a man on CHI in 1986 and DET in
2000 can never match. True, specific, verifiable — and the wrong level. That
explains **how the disagreement got through**; it does not explain **why the
two sides disagreed**. The cause was that one side had no source at all.

A proximate reason is dangerous precisely because it is a genuine finding.
It survives checking, so it feels like the answer. **When a mechanism explains
how something went unnoticed, ask separately what it was that went unnoticed.**


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

### Third instance: the target can be the wrong POPULATION, not the wrong width

**2026-09-03, the 1979 coach floor.** The published files separate head coaches
**in a job** from head coaches **in the pool**: across nine files and 288 sitting
men the minimum rating is **58, without exception**, while the free-agent pool runs
down to 32. Ranking our 32 sitting coaches by win percentage and mapping them
across the *whole* published head-coach band — free agents included — put eight
below that floor, and **Neill Armstrong, who took Chicago to the playoffs in 1979,
on 32**: the lowest-rated coach this project has produced. Mapping onto the sitting
band alone fixes it and leaves the ordering untouched.

The metric was never wrong. Published coach ratings track real win percentage at
**r = +0.66** across 373 matched men; the guess that they rated on something else
was checked and refuted. **It was the band.**

So the family now has three members, and they fail differently:
- the 2026 stretch and the 1979 expansion pool — a source too NARROW to span its target;
- the 2000 stamina block — a target CONTAMINATED by an artifact;
- the 1979 coach floor — a target drawn from the wrong POPULATION.

**Check that the target band comes from the population you are assigning to, not
merely from the right field of the right file.**

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

---

## A pooled correlation averages the cohort where a field works with the cohort where it doesn't

Four instances in one session, all the same shape:

| field | pooled | split |
|---|---|---|
| `PTSA` vs real salary | **+0.417** | rookies **+0.500**, veterans **+0.020** |
| `stamina` vs `PSTA` | 0.847 | within position **0.999** |
| within-light skin family | union 54/25/21 | seven files, f3 from 1.8% to 46.8% |
| `OLB` `manCover` | 32.3% populated | 62.3% of it fill, real gate 0% |

**A pooled statistic is a weighted average of every sub-population it spans, and
it is most misleading exactly when the sub-populations differ — which is the case
you are usually trying to detect.** `PTSA` at +0.417 reads like a usable if noisy
source. It is a good source for rookies and literally no source for veterans, and
the pooled number is an artifact of mixing them that describes neither.

Note that pooling misleads in **both directions**. `PTSA` pooled looks better than
it is for veterans; `stamina` pooled looked worse than it is within position and
nearly sent a correct mapping back for repair. There is no safe direction to
assume.

**Rule: before trusting a correlation, name the sub-populations it spans and
compute it within each.** Cohort, position, and contract regime are the three
that have mattered here. If a field is going to be used per player, it has to be
validated in the population that player belongs to, not in the union.

---

## The rule fails when the lookup feels too small to matter

Nineteen rostered players had no contract data. Checking whether they were real
2000 players meant one lookup against nflverse draft data, keyed on name. **Two
came back as retired years earlier and were about to be dropped from the file.**

**Reggie Jones was a name-only match to a different man** — a defensive back from
Memphis drafted in 1991, against a wide receiver with two years of experience.
Position-aware matching kills it instantly.

The bug was committed **in the same session that wrote the birth-date
disambiguation precedent**, by the same author, roughly two hours later.

**That is the useful part of this entry.** The rule does not fail because people
have not read it. It fails because a lookup gets typed quickly against a cohort
that feels too small to be worth the ceremony. Nineteen players felt small. The
appearance library, the ratings backfill and the fullback cohort all felt large
enough to be careful with, and were.

**There is no cohort small enough.** If the join is on a name, it is
position-aware or it is a bug, at n=19 as much as at n=1,637.

---

## `to` and `last season` answer a different question than a roster build asks

The same nineteen produced a second false drop for an unrelated reason.

**Mike Cherry** really is the man in the draft data — quarterback, Giants, 1997,
Murray State — and that record's `to` field reads **1998**. He was nevertheless on
the Giants' roster for all of 2000. He simply never appeared in a game.

`to` and `last season` fields mean **last season in which the player recorded an
appearance**. A roster file models who was under contract, which is a strictly
larger set: third quarterbacks, injured reserve, practice-squad call-ups and
four-game comebacks all belong in it.

**Use a roster source to answer a roster question.** `nflverse`'s
`rosters/roster_YYYY.csv` carries 2,046 player-team records for 2000 with a
`status` field (`ACT`, `RES`, `CUT`, `PUP`, `SUS`), which is the right instrument.
All nineteen appear in it; none were dropped.

The near-miss is instructive on its own: the two instruments disagreed, and the
weaker one was the one already loaded.


---

## A guard must know the provenance of what it is guarding

Building 2000's contracts, a rating-based salary **floor** — written to stop
drawn values landing implausibly low — fired on Jason Elam and pushed his **real
Over The Cap figure of $1,071,167 up to $2,200,000**.

**Nothing looked wrong.** $2.2M for a top kicker is not an absurd number. No
distribution check, no range check and no amount of reading the output would have
caught it. It was visible only because the real figure happened to be sitting in
the same table.

**That is the defining property of this bug class: a guard overwriting a sourced
value produces plausible output, because the guard's whole job is to produce
plausible output.** A guard firing on a derived value is working; the same guard
firing on a real one is destroying data, and the two are indistinguishable from
the result.

Floors, ceilings, clamps, defaults and fallbacks are all written with derived
values in mind, and every one of them will silently overwrite a sourced value if
it cannot tell the difference.

**This is the same rule as `_verified_keys` being locked against automated
passes**, generalised. That rule protects Ryan's hand edits from a pass that
"scores better". This extends it to any real-data tier: an anchored contract, a
sourced appearance, a real draft pick.

**Practical form, and what the build now does:**

1. Every record carries a provenance tag (`OTC`, `rookie-slot`, `veteran-drawn`).
2. Every guard checks that tag before it fires.
3. After the guards run, an assertion re-reads the sourced records against their
   original values and fails the build if any moved.

```python
assert_guards_spared_sourced(recs, {id(p): original[p] for p in sourced})
```

The assertion was tested against a deliberately corrupted record before being
trusted, because an assertion that cannot fail is worse than none — it reports
success. All 66 anchored contracts now reproduce their real figure exactly.


---

## An assertion that cannot fail reports success

`assert_guards_spared_sourced` was written to catch a guard overwriting a sourced
contract. Before trusting it, it was run against a **deliberately corrupted
record** — a sourced value moved by hand — to confirm it fired, and then against
an intact one to confirm it passed.

That step is not ceremony. An assertion with a typo'd comparison, a wrong key, an
empty input set or an unreachable branch **does not report "I could not check
this"**. It reports success, in exactly the same words as a real pass, and it
keeps reporting success for as long as it exists. It is worse than no check,
because no check leaves you suspicious.

This project has one instance already: the 1986 registry write that produced
1,745 entries from 1,746 players and raised nothing, because the count assertion
that would have caught it was not there. The failure mode being described here is
one step worse — the assertion *is* there, and is empty.

**Rule: prove an assertion fails before relying on it passing.** Corrupt an
input, watch it fire, restore. Two lines, once, at the moment it is written.

The cheapest version for a set-based check is to assert the set is non-empty
before asserting anything about its contents — a guard over zero sourced records
passes trivially and forever.

---

## Vacuous pass is this project's dominant failure mode

### The worst class: a production step that reports success without producing output

**`stage_build` never wrote the roster file.** For the entire build it
assembled 2,635 records, ran every assertion over them, printed
`ROSTER assembled: 2635 records`, and persisted nothing. Every correction that
reached the shipped file all session did so through a *separate* script writing
it directly. The build command reported success and produced no output, all
day, and read exactly like a real build.

It surfaced only because a position overhaul that moved hundreds of players
between DE/DT/OLB/MLB came back with **all fifteen position counts identical to
the digit**. That is not a plausible result, and the choice was to investigate
it rather than accept a convenient one.

This is the sharpest form of the family: the other instances check nothing and
say `ok`; this one *does* the work, verifies the work, and throws it away. Every
assertion in it passed, honestly, on records that never left memory.

**Rule: after any step that is supposed to produce an artefact, assert the
artefact CHANGED — a differing hash or mtime — not merely that the step ran
without error.** Record counts, assertion passes and log lines all describe the
in-memory object; only the file on disk is the deliverable.


Counted across the build, **a check reporting green over nothing has caused more
wrong conclusions than anything in the data itself.** Not a tendency — the
leading category, ahead of bad joins, bad thresholds and bad sources. Every
instance below reached a confident, plausible, wrong answer, and every one of
them printed the same word a real pass prints.

| # | instance | what was empty or unreachable | what it reported |
|---|---|---|---|
| 0 | **`stage_build` writing nothing** | the whole output step — records built, verified, discarded | `ROSTER assembled: 2635 records`, every session |
| 1 | `free agent salary != 0` | the file had **no free agents** | `ok`, on every run, for the life of the 288-record file |
| 2 | recombination control | vocabulary built from the very names being tested | `0.0%` on all eight files — the number wanted |
| 3 | `teamId` probe | field is `teamID`; `.get` returned `None` for all 453 | a clean team/free-agent split, entirely fictional |
| 4 | `min(teamID)` as sentinel | `teamID` is an abbreviation; `min` returned `'ARI'` | nine Arizona staff as the league's free agent pool |
| 5 | dead validator block | appended to a `warn` list that did not exist, read a deleted `cnt` | nothing — could only `NameError`, so never ran |
| 6 | conditional pass | scored records whose **source was absent** | a pass on cells derived from nothing |
| 7 | `assert_refit_bounds` | medians 1.0 while one cell moved 92 points | bounds intact, with a 92-point error inside them |
| 8 | MAD display | MAD 1.0 printed as agreement | a seam that looked converged |
| 9 | guarantee assertion | over-strict, so it fired on clean input | the mirror case: a check that cannot *pass* is also uninformative |
| 10 | 1986 registry write | count assertion absent entirely | 1,745 entries from 1,746 players, silently |

Instances 2, 3 and 4 all occurred **inside a single measurement**, minutes apart,
while deliberately trying to be careful. That is the base rate to plan for, not
an unlucky day.

### Why this family is specifically dangerous here

A wrong number invites scrutiny. A green check ends it. Worse, several of these
were *confirmatory*: the recombination control returned exactly the tidy 0.0%
that made the hypothesis look proven, so there was no felt reason to look again.
**The vacuous pass is most likely to survive precisely when it tells you what
you hoped.**

### The rule

**Every check is run twice before it is trusted: once against a population where
it MUST fail, and once against an empty one.**

- *Must-fail run.* Corrupt an input by hand, watch it fire, restore. Two lines,
  once, at the moment the check is written. The 14 free-agent gates were each
  put through this; all 14 fired, and the table above is why that was not
  ceremony.
- *Empty run.* Feed it nothing and see what it says. If it says `ok`, it needs a
  non-empty guard. Assert the population size **before** asserting anything
  about its contents.
- *Report the denominator, always.* `ok` is not a result; `ok, n=165` is. Four of
  the ten above would have been visible on sight with the count printed beside
  the verdict.
- *A control is a check.* It gets both runs too. Instance 2 was a control, not an
  assertion, and it was the most persuasive of all of them.
- *Never build a reference set from the members you intend to test against it.*
  That is instance 2's exact mechanism, and it is easy to write by accident.

### Adjacent, not the same

A **comment that misdescribes its code** is the same disease outside the test
harness. While adding Cowher, the comment claimed the displacement dropped the
lowest-rated coach; the code dropped the least recent. Both were defensible, so
nothing looked wrong, and the documented reason for a data decision was simply
false. Fixed by making the code do what the comment said — verified by reading
back which name was actually dropped, not by trusting the diff.

---

## Payroll and quality: measured, and what survives the definition

A claim that team payroll is uncorrelated with roster quality across all eight
published files was generalised from three, and conflated two different
measurements — payroll vs **cost** with payroll vs **quality**. Measured
properly, across all nine files and **eight defensible definitions** (top-53 or
whole roster x mean or median rating x Pearson or Spearman):

**What survives every definition:**

- **The relationship is positive in the published archive.** Better rosters cost
  more. Under six of eight definitions every published file is positive.
- **2026 and 2000 are the weakest pair, always.** 2026 ranks 1st-3rd weakest of
  nine (median rank 2); 2000 ranks 1st-2nd (median rank 1).
- **The p=0.90 payroll compression is NOT the cause.** Inverting it moves the
  figure by at most **0.045** across all eight definitions, and every delta is
  *negative* — removing compression makes the correlation slightly **weaker**.
  `compress_top` is a monotone power transform about the median, so it cannot
  reorder anything; it reaches a rank statistic only through the nonlinearity
  of a top-53 sum, and that turns out to be worth almost nothing.
- **The weakness is real 2026 cap money.** In the Madden 27 source itself, real
  team payroll against real mean overall is **+0.300** Pearson / **+0.328**
  Spearman, and against median overall **+0.171** / **+0.206** — far below the
  published files under matched definitions. Real teams overpay and underpay,
  and ranking on real money inherits that.

**What does NOT survive the definition:**

- *"Every published file is positive."* **2000 goes to -0.62 and -0.65** under
  the two top-53 Pearson definitions.
- *"2026 falls below the published minimum."* True under **2 of 8** definitions.
  Under the other six it sits inside the range, above 2000.

**Ruling: logged as a deliberate divergence, and it is within the archive's
range.** Ranking on real `_TotalSalary` is the more faithful choice and the
reason the figure is low; 2000 already occupies the same territory, so no
published bound is breached in any robust reading.

**One residual worth an audit line.** Under median-based definitions the build
attenuates further than the source justifies — shipped **-0.030** against a real
**+0.206**, a gap of 0.24, where mean-based definitions lose only 0.06. The
compression accounts for 0.03 of that. Something in the quantile mapping or the
refit flattens the median measure specifically, and it has not been chased.

**The methodological point, which is the same one the coverage claim taught.**
Two of these three headline readings flipped between defensible definitions. A
single number with no sensitivity check around it is not a finding — and the
temptation is strongest when the number is the one you expected. The durable
statements here are the ones quantified across all eight cuts, not the sharpest
one available from any single cut.

---

## A fix that looks like an improvement and imports fiction

The head-coach pool sourced candidates only from **team-side** records. The
obvious widening — also source from published **free agent** records, which is
where the archive keeps Cowher, Parcells and Dungy for decades — is wrong, and
it looks right.

Those pools are **mostly the archive's own invented coaches.** The widened
candidate list came back led by Jocelyn Lyndhurst, Quill Kestrel, Caspian
Thornbury and Denholm Fairholm, interleaved with the real names at
indistinguishable ratings.

**A team-side record is what makes a name real.** A free agent record proves
only that the file contained the name.

This is the hardest class to catch, because the change is a genuine improvement
in coverage and its failure mode is invisible in every count: the pool still has
27 head coaches, still passes every gate, still shows a plausible rating spread.
Only reading the names reveals it. **When a fix widens a source, check what the
new material IS, not how much of it arrived.**

---

## A comment that disagrees with its code is a silent defect

While adding Cowher, the comment stated that a named inclusion displaces the
**lowest-rated** of the recency picks. The code displaced the **least recent**.
Both are defensible rules, both produce a valid 27-coach pool, and every gate
passed either way — so nothing looked wrong, and the recorded justification for
a data decision was simply false.

This is the vacuous-pass family relocated into the documentation layer: the
check that should have caught it is a human reading the comment and believing
it. Nothing executable disagrees.

Caught by **reading back which name actually left** rather than reviewing the
diff. Fixed by making the code do what the comment said (Hue Jackson at 59
displaced, not Jay Gruden at 66) — and the first attempt at that fix rebuilt 16
of the 27, which the same read-back caught immediately.

**Rule: when a comment states a selection rule, print what the rule selected.**

---

## Test a headline reading under every defensible cut BEFORE reporting it

Three times in this build, a single-definition result was reported as a robust
finding. Every one was cheap to check and none was checked until challenged.

| # | claim | what broke it |
|---|---|---|
| 1 | archive coverage is U-shaped, 2020+ second-worst | `first_seen` vs `last_seen` — a player active 2018-2026 is in both buckets, so the shape between modern bands was a denominator artifact |
| 2 | every published file is positive on payroll vs quality | 2000 reads **-0.62** and **-0.65** under the two top-53 Pearson cuts |
| 3 | 2026 falls below the published minimum | holds under **2 of 8** definitions; under the other six it sits above 2000 |

Claims 2 and 3 came from the **same table**, reported in the same breath.

**Where it happens is the diagnostic.** All three arrived as numbers that fit a
story already forming — a coverage narrative, then a faithful-money-mapping
narrative. The measurement returned something that confirmed the expectation,
and the search stopped there. **A result that fits the story is not
corroboration; it is the moment the next cut is least likely to be run and most
likely to matter.** This is the same mechanism as the confirmatory vacuous pass
(see *Vacuous pass is this project's dominant failure mode*), operating on a
real number instead of an empty one.

**Rule: enumerate the defensible cuts first, run all of them, and report the
statements that survive.** The cuts are usually obvious and mechanical — bucket
by first or last, mean or median, top-53 or whole roster, Pearson or Spearman,
pooled or per-file. Eight variants of a correlation cost one script.

**And report the sensitivity, not just the survivor.** "Positive across the
archive under 6 of 8 definitions; 2000 goes negative under top-53 Pearson" is a
usable statement. "Every published file is positive" is not, and reads stronger
— which is precisely why it is the one that gets written.

A finding that flips between two defensible definitions **is not a weaker
finding, it is an absent one.** The correct output in that case is the
sensitivity table, and nothing else.

---

## A fix that moves players can regenerate the class it resolves

The registry-drift list was built against the scrambled positions and should
have largely dissolved once positions were real. **70 became 60, not 10.**

Edmunds, Bush, Travis Hunter and Van Ness all resolved — they were on the list
precisely because the build read them as OLB while the registry had them at
MLB. But the residual is dominated by **OT/OG/C** and **DE/OLB**: exactly the
positions the convention shift moves. The fix traded one drift population for
another of the same shape.

This is the fourth time position labelling has bitten this build — the
vocabulary mismatch at the archive lookup, the same mismatch at the registry
lookup, the scheme-versus-body-type allocation, and now this.

**Rule: when a fix works by MOVING records between categories, re-measure the
mismatch it was meant to resolve. A net improvement can hide a regenerated
population, and the count alone will not show it** — 70 to 60 looks like slow
progress and is actually near-total resolution plus near-total regeneration.

---

## A ceiling check finds more than the thing it was written for

`assert_free_agent_ceiling` was added because Bobby Wagner shipped at 97 against
a published free-agent maximum of 93. It fired on its first run — **on someone
else.**

Christian Jones, a Cincinnati rookie offensive tackle born in 2003, was carrying
**94** and a listed age of 32. The nickname tier matches `chris` as a prefix of
`christian`, so he had been joined to **Chris Jones**, the Kansas City defensive
tackle. `assert_one_to_one` holds *within* each join, and the build runs three
of them (ACT, RES, free agents) — so a Madden row already claimed by the active
pass could be claimed again by the free-agent pass. Chris Jones's 94 shipped
twice, once correctly and once as a phantom free agent.

Five rows were being double-claimed, **DeVonta Smith among them.**

**Two rules.** A uniqueness assertion must span every pass that can consume the
resource, not each pass separately; scoping it per-call is how it passes while
the invariant it names is broken. This is now
`assert_no_cross_pass_reuse(*results)` rather than an inline guard, and it is
called at **both** sites that run multiple joins — the fix belongs to the class,
not to the instance that exposed it.

A sweep for the same exposure elsewhere came back clean: `iden` (players, staff,
and the two pooled), jersey within team, draft pick within a class, cohort
membership, and staff team+role slots are all singly-claimed. Worth noting that
**the shipped file looked clean during the bug too** — no duplicate `iden`, no
duplicate jersey. The double-claim was in the SOURCE, and only a check on source
consumption could see it. Auditing outputs for uniqueness does not test this. And **a check written for one suspect record
is worth running across the whole population** — the value here was not
confirming Wagner, which was already known, but the four names nobody was
looking at.

---

## Iterating an unordered collection that consumes a random stream

`DERIVED_ATTRS` is a **set**. Two of its members are drawn with
`rng.random()`. Iterating in set order made *which draw each attribute
received* depend on Python's hash seed, so `greed` and `ambition` swapped
between runs.

**Two consecutive builds of identical input differed on 2,500 and 2,570
records.** The build could not be run twice with the same result.

Nothing about the output looks wrong. Every value is in range, every
distribution is right, every gate passes, and the file is plausible — it is
simply a different plausible file each time. This is the vacuous-pass family
turned inside out: not a check that cannot fail, but an output that cannot be
compared.

**Why it matters more than its size.** A rebuild diffed against the shipped
file would carry **2,500 rows of noise**, and anyone chasing a real change
would have been reading through it. It defeats every future investigation
silently, and it defeats reproducibility from a clean clone — the exact
property the pinned source provenance exists to provide.

**Rule: any iteration that consumes a random stream must be over a SORTED
sequence.** Sets and dicts are fine to store; they are not fine to draw from in
order. The test is two lines — build twice, diff — and it had never been run.

**How it was found.** Not by a gate. By a claim of mine that turned out to be
false: I wrote that `appearance` was the only field RFM changed, checked it,
and found `greed` and `ambition` moving on 2,500 records. The available
explanation was that RFM had caused it. Building twice and diffing was what
separated "my change did this" from "this was always true".

---

## You can tier a file from its output alone

1986 has no build script — it was uploaded — so there is no `filled` set, no
tier map, no provenance of any kind. The instruction was to fix it the way 2026
was fixed, which requires knowing which attributes are sourced and which are
percentile-filled.

**A percentile fill is a monotone function of rating within position.** So rank
correlation exposes it with no pipeline metadata at all:

| file | median \|rho\| over 28 attributes | attributes above 0.95 |
|---|---|---|
| 1986 | 0.595 | **0** |
| 2000 | 0.693 | **9** (six at exactly 1.000) |
| 2013 | 0.451 | 1 |

A fill reads ~1.0; 1986's highest is 0.935 and most sit at 0.2-0.8. **Nothing in
1986 is filled** — its attributes are authored throughout, so the 2026 tail
repair, which works by rescaling filled cells only, has nothing to act on.

**Rule: a file with no provenance can still be tiered, from the output.** Do it
before applying any fix that distinguishes sourced from filled data.

---

## The direction of trust is a property of the file, not of the fix

In 2026 the attributes were Madden-sourced and the stored rating was an
imported stranger that had never seen them. Recomputing the rating from the
attributes was strictly an improvement.

**In 1986 it is the reverse, and applying the same fix would have been the same
class of error we refuse elsewhere** — adjusting measured data to hit a target.

    quantile            min  p10  median  p90  max
    published rostered   40   59      71   86   98
    1986 rostered now    40   59      71   86   98   <- identical at every quantile
    1986 if computed     31   55      72   88   99

1986's ratings were authored against the published distribution and match it to
the digit. Its attributes are the noisy half. Recomputing would import
attribute noise into the one field that is currently right, move 506 ratings by
more than 10 points and 90 by more than 20, and put **134 prospects below 40,
the worst at 6**.

**Ask which half of a record is trustworthy before deciding which half to
recompute.** The answer differed between two files with the identical symptom.

---

## A threshold fitted on famous players will beat its own scale test

A skin field in the 1986 retro mod (`c2cced`) scored **95% against 43 anchors**
at threshold >= 53. At scale against the published file's own head families —
1,210 players — it scored **80.7%**, and the best threshold was 44, not 53.

**Anchors skew toward the well-known, and the well-known are the players every
source gets right.** A threshold chosen on them is fitted to the easy cases and
inherits none of the difficulty of the rest. The check that caught it was the
aggregate share, not the anchor accuracy: predicted 60-65% dark, delivered 43.8%
at the chosen threshold.

**And the multiple-comparisons trap sits right behind it.** Scanning all 170
keys for the best skin predictor returned `c27a25` at **87.0%** — better than
the hypothesised field. That number is the maximum of roughly 6,800
key-and-threshold combinations, and **a search that wide returns something near
87% even when no field encodes skin at all**. It was reported as untrustworthy
rather than as an improvement.

**Rule: a source is scored at scale, on a stated field and a stated threshold,
before it is believed.** An anchor set proposes; only the population decides.

**Triangulation is what settled it.** The mod agreed with the published 1986
file 80.9%, and with the player archive **72.8%** — less than the archive
agrees with the file we already distrust (79.5%). RFM scores 98.1% on that same
test. *A third source that sits further from both of the first two is not a
tiebreaker, it is noise.*

---

## Cut on the defect's signature, not on the category that contains it

The OLB coverage fix was specified as "zero `manCover` and `zoneCover` for every
OLB in the four affected files." Applied literally, that **destroyed 52 real
values**: the PROSPECT cohort carries genuine coverage ratings (45-76, the
plausible range) mixed in with the fill, and 2010's prospect `zoneCover` is
entirely real — 58 to 70, without a single fill value in it.

The scope table the instruction came from measured **rostered players only**,
where the contamination is total. Extending the rule to a cohort nobody had
measured extended it past the evidence.

Re-cut on the fill vocabulary instead — `manCover` in {1,2,3}, `zoneCover` in
{1}, against an MLB range of 38-92 — and the defect is removed while every real
value survives. **The signature identifies the defect; the category merely
contains it.**

Caught by diffing what had been overwritten against git rather than by a gate.
The assertions all passed: only the two named fields moved, only on OLB records,
counts unchanged. **Every one of them was true, and the write was still wrong**
— they constrained the shape of the edit and said nothing about whether the
data being replaced was fill.

---

## A widened check reports its own reach errors as findings

Widening the faces gate took its coverage from **27 to 103** of 105 verified
players — a genuine improvement — and **created a false-positive class in the
same change**. It immediately reported six drifts in 1986, four of them
described as newly discovered. All six were false. Every one matched
`faces_1986` byte for byte; the widened gate was reading `faces` instead.

Then the staff path did it again: two more "drifts", both `jim mora`, which are
**two different men** — Jim E. Mora (1986 NO, 2000 IND) and Jim L. Mora (2000
SF) — split across the two blocks, with each file carrying the correct face.
`build_2000.py` had documented that years ago.

**Both things are true at once, and that is what makes it hard.** A fix that
simply fails is obvious. A fix that improves the headline number while
generating errors that *look like discoveries* is not: the new findings arrive
with the credibility of the improvement that produced them.

**Rule: the first results from a widened check are verified against the raw
source before they are believed, not treated as newly surfaced defects.** Ask
"could the change I just made have manufactured this?" before reporting it.

Eight false positives were passed on as confirmed drift before that question
got asked.

### And refuse what the key cannot distinguish

`staff_faces` and `staff_faces_1986` share 46 keys with 40 different values,
because a bare name cannot separate a father from a son. The gate now reports
those as **ambiguous and declines to score them** rather than guessing a block.
Same discipline as the tier-1 tail refusals: a case that cannot be decided from
the available evidence is reported, not resolved by inference.

---

## A composite key cannot both exclude namesakes and follow a man who moves

The faces gate keys cross-season checks on `name|position`. That key does two
jobs and succeeds at one.

It **correctly excludes namesakes** — Gary Anderson's 1986 file holds a
Chargers running back and a Steelers kicker, and comparing their faces would be
meaningless. Re-keying on name alone surfaces 65 such false positives.

It **hides every man who changes position**. Re-keyed on name and split by
whether age advances with the seasons, **61 genuine cross-band skin flips** have
never been flagged by anything: Brad Meester goes guard/dark in 2000 to
centre/light in 2004 and stays there for four files; Aeneas Williams goes
corner/light to safety/dark; David Harris is a dark middle linebacker for three
files and a light outside linebacker in the fourth.

**No composite key can do both.** Position is exactly the field that separates
two men with one name AND changes for one man over a career. The information
needed is identity — age progression, team continuity, draft position — not a
wider or narrower key.

**This is the same conclusion the join layer reached from the opposite
direction.** There, matching on normalised name merged Michael Carter and
Michael Carter II, and the fix was birth dates: identity resolution, not a
better string. Two independent parts of this project arrived at the same
answer, which makes it a property of the data rather than a quirk of either.

**Rule: when a key is doing identity work, it will fail in one of the two
directions. Decide which failure you are choosing, and measure the other.**

---

## Two scripts in one project, two position vocabularies

The Houston core was selected by one script and assembled by another. The
selection kept Madden's own labels — `FB`, `FS`, `SS`, `G`. The build collapses
to PGM3's fifteen — `FB`→`RB`, `FS`/`SS`→`S`, `G`→`OG`.

Matching the two on `(forename, surname, position)` silently dropped **four of
fifty-seven core players**, including **Jason Layman, a 1996 Houston Oilers
second-round pick** — precisely the cohort the entire roster premise is built
from. The build reported "no longer in the pool", which reads like an absence and
was a translation failure.

**It fails quietly and in the direction that looks reasonable.** A roster one
guard short is not obviously wrong. The count was 53 either way, because the
shortage filler simply took one more body from the general pool.

**Rule: when two scripts exchange records, assert on the match rate, not just on
the output count.** The output was the right size the whole time. What was wrong
was who was in it.

`stage2b` now asserts that at most three core players fail to match, and names
them when any do.

### The count assertion was satisfied throughout, and could not have failed

This is the part worth carrying. `assert len(out) == len(inp)` is this project's
flagship check — it exists because a 1986 registry write produced 1,745 entries
from 1,746 players and raised nothing. **It passed here at every step, and four
wrong men shipped anyway.**

It passed because **a compensating mechanism sat downstream**. The Houston
assembly fills any position below its minimum from the general free agent pool.
Drop four core players, and the filler takes four more bodies; the roster is 53
either way. A count assertion cannot see a defect that something downstream
silently repairs — and the filler's entire job is to keep the count right.

**Corollary, and the operative rule: wherever a fallback exists to make up a
shortfall, the count check is dead by construction.** Any stage carrying a
filler, a default, a percentile backfill or a "top up to N" needs the
**match-rate** assertion specifically. The count assertion is not weak evidence
there; it is no evidence at all.

The same shape appears wherever this project has a fallback tier: percentile fill
behind the direct attribute map, the appearance library behind `PSKI`, the
drawn tier behind the contract anchors. Each of those keeps the count correct
by design.

### One position vocabulary, or an explicit translation at the boundary

Three position-vocabulary translation bugs in one session: `FB`/`HB` in the
fullback cohort, `FS`/`SS` and `G`/`OG` here. Every one silently reduced a
cohort rather than raising an error, because a label that does not match simply
finds nothing.

**Two scripts exchanging records must share one position vocabulary, or translate
explicitly at the boundary. Never match on a label each side defines
separately.** PGM3's fifteen is the project vocabulary; Madden's `PPOS` labels
are a source encoding and must be translated once, at the point of entry, not
carried around and compared.


---

## Give a research source a check it can run on its own output

The 2000 head-coach career records came back with **no uncertain fields**, which
is unusual for this workflow, and the reason looks identifiable rather than lucky.

The standing instruction for these requests is *"say uncertain rather than
guess"*. That only helps once the source already knows it is unsure — it does
nothing about a confident wrong answer, which is the failure that actually
happens. The PFR season index gives Andy Reid 437 career games on the 1999 page
against the 16 he had really coached, and a source reading it would have no
internal reason to doubt that number.

**What was different: the prompt carried two constraints the source could verify
against itself before answering.**

1. **An expected-zeros list** — the seven men who had never been an NFL head
   coach. Any lifetime-total source fails this instantly, because it gives
   Belichick 302 wins where the answer must be a career that had not started.
2. **A table of 22 single-season 1999 records.** Every returned career total must
   contain its coach's 1999 season as a subset. Reid at 5–11 is the headline
   case: it is the one a lifetime-total source breaks most obviously.

Both are checkable by the source, on its own draft, without any outside data.
That converts "be honest about uncertainty" into "here is an arithmetic test you
will fail if you have misread the question".

**Rule: when commissioning research, include at least one constraint the source
can test its own answer against.** A subset relation, a known-zero set, a total
that must reconcile. Two are better than one and they should fail in different
directions — the zeros catch an inflated source, the 1999 subset catches a
deflated or mismatched one.

Both constraints were then re-run **on the returned file** before it was used, and
independently: the 1999 records were recomputed from nflverse game results rather
than taken from the prompt. Verification that reuses the prompt's own numbers is
not verification.


---

## Prefer the convention nobody has to remember

Head coach ratings regress toward .500 for small samples, which raised a
definitional question: Wade Phillips's 1985 New Orleans spell lasted **four
games**, so does it count as a season? Either answer is defensible, both feed the
rating, and the file has to pick one.

**Weighting the regression by games rather than by seasons does not answer the
question. It removes it.** Four games contribute four games' worth of evidence
whether or not anyone calls them a season, so the convention has nothing left to
be inconsistent about. Phillips lands on his real 68 games; no future session has
to look up a ruling before touching the formula.

That is the property worth optimising for. **A convention that must be remembered
is a defect waiting for the session that does not remember it**, and this
document is largely a list of conventions — every one is something a later build
can get wrong. Where two formulations are equally defensible, prefer the one that
makes the question disappear rather than the one that answers it correctly.

The same shape appears elsewhere in this project and is worth recognising:

- **Birth date over position** for namesake disambiguation. Position needs a
  compatibility table that someone must maintain and reason about; birth date is
  a fact the collision does not share and needs no ruling.
- **Provenance tags over guard ordering.** The alternative to tagging records was
  to remember which guards may fire after which stage — a rule that has to be
  held in a maintainer's head. A tag the guard reads does not.

Applied across all 31 coaches rather than only to Phillips: `reg_w + reg_l +
reg_t` gives games directly, and the file totals **2,045**.

---

## Measure a normaliser against the keys, never against its own description

The face registry documents its normalisation as *"lowercase, strip punctuation
and Jr/Sr/II/III/IV/V, collapse initials"*. Implementing exactly that is wrong,
and the error is invisible: a missed key produces a generated face, which looks
fine.

**Measured against the 11,069 `faces` keys, the real rule treats punctuation two
different ways:**

| input | registry key | punctuation |
|---|---|---|
| `A.J. Brown` | `aj brown` | period **glued** |
| `Scott O'Brien` | `scott obrien` | apostrophe **glued** |
| `Kabeer Gbaja-Biamila` | `kabeer gbaja biamila` | hyphen **spaced** |

Getting it wrong in either direction costs about a thousand roster records.
Spacing everything — the build's general `norm()` — misses the **758** period
cases. Gluing everything, which is what the stated description says, misses the
**212** hyphen cases. Neither single rule works and the description names
neither.

Suffix tokens are stripped **anywhere in the name, not only trailing**. That
looks like a bug — it turns `J.R. Ambrose` into `ambrose` — but it is what the
registry does, and enforcing trailing-only dropped the hit rate from 97.7% to
96.9% because the registry drops a middle `V.` the same way. **Reproduce the
artifact's behaviour, not the behaviour it ought to have.**

Final hit rate on punctuated names: **97.7% roster, 100% staff.** The residual 23
are genuinely absent from the registry — every sampled one has no near-match
under any spelling — rather than mis-keyed.

**The general rule: a normaliser is a claim about another artifact's keys, so
test it against those keys.** Three measurements settle it in minutes — how many
names change form, how many then find a key, and whether any two keys collide
once normalised. The third matters because a collision is a merge: `faces_1986`
holds `william  roberts` and `william roberts` (double space) with *different*
faces, and both are the same man.

---

## You check the fields you thought of

The first 2000 staff builder hand-listed which attributes each role carries. It
set the four coaching attributes, the three scout attributes, both physio
attributes — and left about thirty specialty fields at zero: `management`,
`motivation`, `playcalling`, `passRush`, `playDesign`, `injPrevent`,
`reInjuryRisk` and the rest.

**That is the bug the handoff records as having crashed the game**, reproduced
exactly, by an author who had read the warning that morning and written
assertions against it. The assertions passed. They checked that every coach had
four non-zero coaching attributes, because those were the fields I was thinking
about when I wrote them.

**A hand-written list of what to populate is a list of what its author
remembered.** The fix was to stop listing and start measuring: build a per-role
profile from the published files — which fields a role populates, at what rate,
around what centre — and fill from that. Ten failing check groups became one.

This is why the zero-pattern check exists at all. It compares against a
reference precisely so that no one has to remember the field list, and it caught
this in one run.

### Second instance, same session, different domain

Two commits after writing the paragraph above, the same author merged `main`
into a build branch, hit a reported `CONFLICT`, and committed through it —
twice. The first fix then restored **only the file the error message named**,
leaving a 4.7MB registry equally broken through another commit.

Both halves are the same failure as the attribute list:

- **Checked the thing I did, not the thing the tool said it had done.** The
  output being read was a doc edit; `CONFLICT` was on screen and unacted on.
- **Fixed the instance shown rather than sweeping for the class.** `grep -rl
  '^<<<<<<< '` across the tree takes one second and catches every damaged file
  at once. Restoring one file by name catches one.

**Two independent sightings in one session, in unrelated domains, by an author
who had just written the rule.** That is the argument for structural checks over
care: the knowledge was present, recent, and self-authored, and it did not
prevent either instance. The fix in both cases was the same shape — stop
enumerating what you remember, run something that enumerates for you.

---

## Format churn defeats review, and review is the control that catches everything else

Deleting six keys from the face registry produced a **180,323-line diff**,
because the write used `json.dump(..., indent=1)` on a file stored compact. The
data change was correct. The diff was unreviewable.

That is not cosmetic. **The conflict damage described above went unnoticed
through two commits, and a reviewable diff is exactly what would have shown
it.** An unreviewable diff disables the control that catches the mistakes no
specific check anticipates — which is most of them.

The handoff records the 2007 rewrite as a formatting note: *"expect a whole-file
diff rather than a clean one."* This is the version that says what it costs.

**Rule: match the file's existing format when writing it back.** Read the first
bytes and reproduce them — compact stays compact, indented stays indented,
`ensure_ascii` stays as found. Rewritten that way, the same six deletions
produced a **one-line diff**.

Corollary: if a change genuinely requires reformatting, do it as a separate
commit containing nothing else, so the substantive change stays reviewable on
its own.

---

## A fifth of every draft class is in no Madden file, whatever year you reach for

Building 2001-2004, the 2001 class had to come from `2003 - PLAY.csv` at a
two-year gap, and the obvious worry was coverage. Measured:

| class | source | gap | matched |
|---|---|---|---|
| 2001 | 2003 file | **2** | 74% |
| 2002 | 2003 file | 1 | 79% |
| 2003 | 2003 file | **0** | 79% |
| 2004 | 2004 file | **0** | 78% |

**The correct-year class matches at the same rate as the two-year-gap one.**
The shortfall is not caused by reaching for a distant file — it is draftees who
never appear in any Madden export, because they never made a roster the game
cared about. It is uniform at roughly 22% across every class.

Two consequences worth carrying:

**The source-tier hierarchy is about accuracy, not coverage.** A closer year buys
a better value for the players you already had (MAE 2.35 at gap 1, 3.15 at gap 2,
against 7.26 for percentile fill). It buys almost no additional players. Hunting
for a nearer source to fix coverage is hunting for something that is not there.

**Percentile fill is load-bearing by design, not by failure.** Roughly a fifth of
every draft class reaches the file through it, permanently, and no amount of
source work changes that. It should be reported as a standing share rather than
treated as a shortfall to be driven down — and it is the reason the match-rate
assertion matters more than the count.

---

## Record the reason beside a deliberate divergence, not in the commit message

2000's draft prospects carry a maximum potential gap of **40**, against **36 /
33 / 23** in the published files. That is deliberately **looser**, and read cold
it looks like an out-of-range defect that a later session will tighten.

**The reason has to sit next to the number.** The 2013 build capped the gap at
**14** against 29-45 elsewhere and produced **Louis Nix rated above Aaron
Donald**. A cap is not a neutral safety measure — it compresses the top of the
class, and the top of the class is where the recognisable players are.

So the constant in `draft_potential` carries that sentence in the code, not only
here. **A commit message is not where a future reader looks before changing a
constant.** They look at the constant.

General form: a value chosen deliberately outside a reference range needs its
justification stored where the value is, because the reference range is what any
reviewer will check it against first.

---

## Third boundary-translation bug: a vocabulary borrowed across a boundary

Prospect faces were generated from the **staff** hair vocabulary, emitting
`Hair4k` — which exists for staff and not for players. Earlier in the same build,
staff faces were generated from the **roster** vocabulary, emitting `Hair5e`,
`Beard3c` and `Hair4k` in the other direction.

Same root as `FB`/`HB` in the fullback cohort and `G`/`OG` in the Houston
assembly: **a vocabulary carried across a boundary where the two sides genuinely
differ.** Three instances in one build.

The tell is always the same — one side of the boundary was written by someone
holding the other side's vocabulary in mind, and the mismatch produces a value
that looks plausible rather than an error. `Hair4k` is a perfectly well-formed
token. It is simply not one players use.

**Derive the vocabulary from the population you are writing into, never from the
one you happen to have loaded.**

---

## The gate and the distribution answer different questions

Third bite of "recompute everything derived from a cleaned population", and the
first in the **opposite direction** — an over-applied correction rather than an
under-applied one, which is why it is worth its own entry.

Cleaning the value-1 fill out of the quantile targets was right. Recomputing the
**position-gating rate** from the cleaned data was not. Stamina is 100%
populated and roughly 9% fill, so the cleaned rate came out at 0.91, below the
partial-field threshold — and stamina was gated **off** for the bottom 9% of
several positions. **37 players shipped with stamina 0.**

**The two numbers answer different questions:**

| | question | computed from |
|---|---|---|
| **gate** | does this position use this field at all? | the RAW non-zero share |
| **distribution** | what values does this field take? | the CLEANED values |

Cleaning fill out of the distribution must not touch the gate. The single
exception is a field cleaning empties entirely — `OLB` `manCover`, every
non-zero value of which was the fill — because that genuinely means the position
does not use it.

**No structural check could see this.** The output had a plausible distribution,
the right median, a correct zero-pattern against a reference that also carries
zeros there, and 37 records at zero in a field where zero is a legal value. The
**conditional pass** caught it: conditioned on `PSTA`, the 50-59 decile mapped to
a median of 8 against 19 for the decile below it. That is the second time in one
build the conditional found something nothing else could, which is the argument
for its mandatory status.

**Generalised: when a correction changes a population, list every statistic
downstream of it and classify each as "describes the population" or "describes
whether the population applies".** The first kind must be recomputed. The second
must not.

---

## State the cohort with any cross-file count

Face-consistency figures for the 2000 build differ by a factor of four depending
on the cohort, and both numbers are correct:

| cohort | key | family disagreements | hair |
|---|---|---|---|
| rostered only | normalised | 8 → 8 | 15 → 16 |
| all cohorts | normalised | 31 → 163 | 62 → 219 |

`pgm3_validate.py faces` reports the rostered-only figure. A reviewer measuring
across every cohort gets a number four times larger and concludes something
regressed.

This is the same trap as the stamina fill counted at 1,267 rostered against
1,622 including prospects. **Quote the cohort with the number, every time** —
two correct measurements of different populations otherwise read as a
disagreement, and the person who has to reconcile them is the one who did not
take either measurement.

---

## Fixing the instance you were shown, not the class

**Third sighting, and the 2026 build produced two of them an hour apart.**

`stage_contracts` re-ran `stage_attributes` instead of taking the caller's
cohort. That created new objects, so every `id()`-keyed salary lookup missed
and the file shipped with **median team payroll $0.0M** — and a perfectly
correct record count, because the count was never the thing that broke. Found,
diagnosed, fixed.

**The identical bug was sitting in `stage_appearances` and I walked past it.**
It surfaced two gates later: 2,107 records had taken a placeholder face and the
file contained **five distinct appearances across 2,635 records**.

The earlier instances have the same shape. The merge-conflict damage was
repaired by restoring only the file the error message named, leaving a 4.7MB
registry equally broken. The degeneracy test was corrected for its threshold
and then found to have a second fault one step later, running on the inverted
rather than the raw column.

**The trigger is that a fix feels finished when the symptom goes away.** It is
finished when you have looked for the same mistake everywhere else it could
live. `grep` for the pattern, not the instance.

**The practical form is a structural guard, not care.** Both identity bugs are
now impossible to repeat silently, because the lookup asserts on its own MATCH
RATE:

```python
hit = sum(1 for n, m, pos in rows if id(n) in face_of)
if hit < 0.99 * len(rows):
    raise AssertionFailed(...)
```

A miss does not error — it substitutes a default, which is exactly how five
faces reached 2,635 records. **Wherever a lookup has a fallback, assert the
rate.** The count assertion is not weak evidence there; it is no evidence.

**And do not key across independently built cohorts.** `id()` is not a value.
Pass the cohort through, or key on something stable.


## `startSeason` and `draftSeason` run on the GAME'S clock, not the season's

**Every published file treats the current season as 2026**, whatever year the
file models. The handoff states this for `draftSeason`. It is equally true of
`startSeason` and that was written down nowhere:

    file            startSeason range      draftSeason (prospects)
    PGMStaff_2010   1989-2024              -
    PGMStaff_2013   1989-2026              2027-2030
    PGMStaff_2017   1988-2024              -
    PGMStaff_2021   1989-2026              2027-2030

A 2013 file containing coaches who start in 2026 is not a defect. Treating
either field as a real-world year manufactures offsets — subtracting the file
year gave a 2013 coach an offset of "+13", and fitting on those offsets put
**52% of a staff build onto the 2026 ceiling** while reporting a perfect
age/startSeason correlation.

**The failure is silent because the derived field still fits its input.**

## A bound at the reference p90 is a commitment to clipping the top decile

The same operation with the opposite outcome, depending on which statistic it
is anchored to.

**2013 capped prospect `potential - rating` at 14.** The reference p90 is 12
and its max is 23-28. A cap at the 90th percentile does not leave a safety
margin — it removes the top decile by construction. That is why Louis Nix
shipped above Aaron Donald.

**2026 bounds the same quantity at 28, the reference MAXIMUM.** The first cut
had produced a rating-52 tackle with a 94 ceiling, a 42-point gap wider than
anything the archive contains, so a bound was genuinely needed. Bounded at the
max, the non-hit population lands median 7 / p90 13 / max 23 — matching the
archive — while the deliberate tail survives.

**Anchor a bound to the reference's extreme, never to its p90.** If the p90
looks like the right place, what you actually want is a different distribution,
not a clipped one.

## Calibrate a probability against the population that can produce the outcome

Late-round prospects were given a chance of a large potential gap, calibrated
to the measured 4.9% of pick-106+ players who reach rating 85. It came out at
**1.6%**.

The gap is bounded at 28, so a prospect rated 56 **cannot reach 85 at all**.
Only ~60% of the cohort was eligible, and calibrating against all of them was
calibrating against a population that could not produce the outcome. Scaling by
1/0.60 landed it at 5.4%.

Same shape as measuring a correlation within position rather than pooled: the
denominator has to be the population the thing can actually happen in.

## A check must measure only the population it applies to, or it manufactures doubt

Three instances in one build, all in the same direction — **correct work
reported as broken**, which is rarer than the reverse and arguably worse,
because it invites someone to "fix" something that is not broken.

- `conditional_pass` scored tier-2 and tier-3 players against source columns
  they do not carry. A percentile fill measured against a source it never saw
  reports a working map as dead.
- The seam check compared the tier-2 cohort's output against tier-1's and
  fired on `CB`/`WR` intelligence. Tier-2 players are late signings and IR
  bodies, genuinely 5-10 rating points worse, and EVERY attribute ran negative.
  A cohort-quality gap is not a scale error. The fix was to hold the cohort
  fixed: convert the players who have BOTH representations and compare against
  their own real values.
- A `MAD` computed with an `or 1.0` divide-guard that was never divided by
  printed 1.0 where the truth was 0.0, so a perfect conversion read as though
  it had spread.

**Before trusting a failing check, ask whether it is measuring the population
it claims to.** Same root as the pooled-correlation trap: the altitude of the
measurement is part of the measurement.

## Point a suspect instrument at data whose answer you already know

The staff build put 21% of records on the `startSeason` ceiling against a
published 1-5%. That is a plausible property of a young coaching cohort, and
tuning the noise until it went away was the obvious next move.

**Instead, the published 2021 ages were fed through the new formula.** They
produced 18% against their own actual 3% — which proved the formula was wrong
independently of the cohort, and sent the search somewhere else entirely,
where it found that the file-year offset should never have been subtracted.

Same move as running a new spike detector against a file whose provenance is
known before trusting what it says about files that are not. **A detector that
misreads data you already understand is measuring the wrong thing, and that is
cheap to discover and expensive to miss.**

## Independent draws give the right expectation and the wrong counts

Splitting the draft board's coarse `LB` and `EDGE` labels into PGM3 positions
was done by drawing each prospect independently against a probability. Twenty-
six linebackers came out 65/35 instead of the intended 54/46, putting OLB at
17.5% of the LB+EDGE group against a published 32.2%.

That is not bad luck; it is what independent draws do at n=26. Allocating by
**sorted hash** — order the group by a hash of the name, take the first N for
each target — gives exact counts, stays reproducible, and does not correlate
with rank. The result landed 24.6 / 31.6 / 43.9 against a published
24.3 / 32.2 / 43.5.

**Any small-cohort split in this project has the same exposure.**

## Published-file defects found in 2026, none of them previously noticed

Logged rather than fixed; each is invisible to every existing check.

**2013 team payroll is inversely related to roster cost.** Ranking on real
contract money, 2026 shows team payroll tracking roster cost at **+0.67**.
2013 reads **-0.57** — expensive rosters got cheaper payrolls, backwards rather
than merely absent — and 2021 reads +0.08. Both come from ranking salary on
rating instead of money. Invisible because every team's payroll is individually
plausible; only the relationship across teams is wrong.

**2017 carries 37 rostered records at `salary` 0** — 1.9% of that file, 0.0% of
2010/2013/2021. Now dropped from the 2026 quantile target: a map inherits its
target's defects, and `log(1)=0` outliers had crushed the measured
`corr(log salary, rating)` from +0.42 to +0.15, making the reference band look
far wider than it is.

**The 2026 data bundle collapses both linebacker labels.** Every board `LB`
maps to MLB and every `EDGE` to DE, leaving the draft pool with **zero OLBs**
and failing the validator's "missing a LB type" gate. Caught by a gate, not by
anyone reading the bundle — an input approved as complete.

**The handoff's `growthType` shape is imprecise for staff.** Slots 17-19 are
*nearly* always zero (19 of 1,152 records, not always) and positives trail to
slot 26, not 16.

## Fourth boundary-translation bug — and it was found in play, not by a gate

**Ryan reported three wrong faces after importing the 2026 file.** Aidan
Hutchinson and Drew Allar built dark and should be light; Myles Garrett built
light and should be dark. Traced, the cause was **891 silently discarded
lookups**, not three records.

The two face sources speak different vocabularies, and neither is the build's:

    PGM3_PLAYER_ARCHIVE   2K5's 17 labels — T, G, SS, FS, ILB, FB
    PGM3_FACE_REGISTRY    PGM3's exact 15
    the build queried both with PGM3's 15

Measured on 1,888 rostered before the fix:

    archive   832 hit / 583 position-differs / 473 absent
    registry 1033 hit / 308 position-differs / 547 absent

Every one of those 891 fell through to a **generated** face while real data
sat in the file. `Trent Williams` build `OT` / archive `T`. `Kyle Juszczyk`
build `RB` / archive `FB`. `Tony Jefferson` build `S` / archive `SS`.

**The two halves needed different fixes and conflating them would have been
the error.** The archive gap is genuine vocabulary and translates
deterministically. The registry's is POSITION DRIFT for the same man — Cameron
Jordan `DE`->`OLB` — and blind position adjacency is exactly what merges
fathers and sons. The era test settles it: accept a drifted position only when
that name+position is attested in a published file in a season overlapping the
player's career, and REFUSE where several positions survive. 131 recovered, 1
ambiguous refused, 176 unverifiable and refused.

**This is the third appearance of the identity-mismatch shape** — after
contracts shipping salary 0 and appearances taking a placeholder — and it
shipped for the same reason both of those did: **the build produced a face for
every record, so nothing objected.** The guard is now a match-rate assertion,
and the denominator matters: it counts records whose NAME IS PRESENT in the
source, because a name the source never held is not a lookup failure and
including it measures the source's coverage instead of the lookup's
correctness. Exact-key-only resolves 0.677 of resolvable names; with
translation and the era test, 0.864.

**And the same question, asked of every other name-keyed lookup, found a
second miss:** the registry's `staff_faces` block — 2,231 entries, covering 72
of the 128 real coaches — **was never read at all.** Not a vocabulary problem;
its keys are bare names. An unused source, invisible because donor-copied
faces are perfectly valid faces.

## The archive carries its own confidence and the documented rule ignores it

The rule is "light calls reliable at any source count, dark calls need 3+
sources". It says nothing about `agreement`, which the archive stores per
person. Scored against the registry as an independent check:

    band   agreement       n    matches registry
    dark   0.50-0.74     176         54.5%   <- a coin flip
    dark   0.75-0.99      77         75.3%
    dark   1.00         7800         89.3%
    light  0.50-0.74     164         64.0%
    light  1.00         2410         87.6%

**Aidan Hutchinson is the case that exposed it:** archive `dark`, 4 sources —
passing the documented rule — but `unanimous: False` and `agreement: 0.50`.
Myles Garrett reads 10 sources, unanimous, agreement 1.00, and is correct.

Hutchinson is precisely the profile `PGM3_SOURCE_QUALITY.md` describes: a fan
setting values by eye gets obscure players right by default and makes visible
errors on the ones they have an opinion about. The errors cluster on recent
prominent players — Burrow, Mayfield, Crosby, Wirfs, and now Hutchinson.

**A source that publishes its own confidence should be read at that
confidence.** `n_sources` counts votes; `agreement` says whether they agreed,
and four sources at 0.50 is not four sources.

**Hutchinson remains wrong in the built file and must not be hand-corrected.**
Both sources call him dark — the registry at `Head5a`, the archive at
agreement 0.50. With the agreement floor the archive now abstains, but the
registry still drives it. **That is a registry data defect and belongs in a
registry correction pass**, not in a build patching three names. Fixing the
symptom would leave the other 888.

## A lock keyed in a format the checker cannot read is not a lock

`_verified_keys['players']` holds **two key formats**, and each is internally
correct:

    78 keys as name|position|teamID  ->  0 resolve against `faces`
                                         ALL 78 live in `faces_1986`
    27 keys as name|position         ->  27 of 27 resolve against `faces`

The `faces` gate builds its lookup as `name|position` against the `faces`
block. **So it reaches 27 of 105 locked players — 26%.** The other 78 are not
missing from the files; they are unreachable, and they are exactly the ones
`faces_1986` protects.

**Both halves are right.** The 3-part keys carry team because 1986 genuinely
needs it — two James Joneses, both RB, both in that season — which is this
project's own rule that a key needs enough fields to be unique in the widest
population it will be queried against. The gate is right for the modern block.
**The defect lives entirely in the seam**, which is why both sides looked fine
and no check ever objected. A producer and a consumer of the same key must
share its format, and neither side being correct protects you.

**The proof is that it already failed silently.** `doug flutie|QB|CHI` and
`jerry rice|WR|SF` are both 3-part 1986 keys, both inconsistent with the
registry in the 1986 file, and the gate has never reported it in any run.
They were found only because an assertion written for a different purpose
tripped over them.

**And the reporting shape is the trap.** The gate prints "93 checked, 104 in
registry", which reads as 90% coverage. It is 93 RECORD comparisons against 26
distinct KEYS. **A count that conflates records with keys will always flatter
itself** — quote both, or quote the one the reader will act on.

Aidan Hutchinson's 2026 entry is keyed 2-part deliberately, so his lock
actually engages.

---

## Backlog

> The full audit list, including everything this build surfaced and the ruling
> that 2026 ships before any of it is touched, is in
> **`docs/PGM3_AUDIT_BACKLOG.md`**. What follows is the subset that predates it.


**Teach the `faces` gate both key formats, then audit the 78.** Two jobs, and
the second is the interesting one.

    scope        every published file, not 2026
    unreachable  78 of 105 verified players (74%)
    known drift  2 confirmed (doug flutie, jerry rice), both 1986
    unknown      the other 76 have never been checked by any gate

The audit is where more Fluties would be. It needs its own review pass rather
than being folded into a build.

**Tranche 2 of the registry correction: 247 position-drift disagreements**
(`DT`<->`DE`, `OLB`<->`DE`, `CB`<->`FS`) reachable only by accepting a
different position for the same name. **Method: the era test** — accept a
drifted position only where that name+position is attested in a published file
in a season overlapping the player's career, and refuse where several survive.
Deferred deliberately: tranche 1 was sampled at 80% and vindicated, but drift
is inherently riskier than vocabulary because adjacent positions merge fathers
and sons. Own pass, own review.

## Faithful to real football, wrong for the file

**Found in play on a depth chart: 16 of 32 teams had ZERO defensive ends.**
No published file leaves any team empty at any position, in any of eight files
and 256 team-seasons.

The handoff says to map edge players by each team's real front — 3-4 edges to
OLB, 4-3 to DE — and the build did exactly that. **Measured, the archive does
not do this.** For players present in both a published file and Madden 27:

    LEDG on a 3-4 team -> DE 60%      LEDG on a 4-3 team -> DE 69%
    REDG on a 3-4 team -> DE 58%      REDG on a 4-3 team -> DE 65%

The front barely moves it. PGM3 has fifteen slots and does not simulate
fronts; the archive treats edge as a **body type**, roughly 62/38 DE:OLB.

**A rule can be true about football and false about the file.** The scheme
mapping is good football and the wrong model for a fifteen-slot schema, and
nothing about it looked wrong — every record was valid, every attribute in
range, the team sizes correct.

Comparing per-position TOTALS against the archive found two more errors
pushing the same way, both invisible in isolation:

    DT   -> DT 72% / DE 28%      the build sent 100% to DT
    MIKE -> OLB 52% / MLB 48%    the build sent 100% to MLB
    WILL -> MLB 62% / OLB 29%    the build sent 100% to OLB — BACKWARDS

**Allocate per team, not globally.** Shares set the level, weight sets the
order within a team, and a team can never reach zero because the allocation
starts from its own players.

## A composition check, and why a tight band on it is wrong

`zero_pattern` compares attribute VALUES against the reference. **Nothing in
the suite looked at roster composition**, which is why a person opening a
depth chart found this and no gate did.

Added to `pgm3_validate.py`: no team may be empty at a position every
reference file fills. It FAILS on the broken build (18 gaps) and passes on the
fixed one.

**The per-position TOTALS half is a warning, not a gate, and the reason
matters.** The published files disagree with EACH OTHER by 26-77% on per-team
position rates — DT runs 3.2 to 5.6 per team, MLB 2.5 to 4.1, WR 5.5 to 8.5.
A tight band would fail most published files against one another. Worse, a
legitimate cohort difference is indistinguishable from a defect: 2026 carries
exactly one kicker and one punter per team while the published files carry
1.1-1.3, because they were built from everyone who played that season and 2026
is a 53-man roster. **A check whose reference disagrees with itself by 77%
cannot be a gate.** It is a prompt to look.

The first version of that check was also DEAD — it appended to a `warn` list
that does not exist and read a `cnt` I had deleted, so it could only ever
raise NameError, and it never ran because the block it sat in was reached only
after the failure. **An assertion that cannot fail reports success**; one that
cannot run reports nothing at all, which is the same defect wearing a
different face.

## Quantifying "the reference union is not a specification"

Asked to gate roster composition on **the range every reference spans** —
calibrated to the archive's own disagreement rather than an invented band, and
so passing every published file by construction.

**Measured, it does not.** Leave-one-out, per-team position rate on a top-53
slice, counting all fifteen positions:

    1986  5     2004  1     2010  5     2017  1
    2000  4     2007  1     2013  5     2021  5      2026  1

Excluding K and P, whose rate is ~1.0 everywhere: 5 / 3 / 1 / 1 / 4 / 4 / 1 / 5,
and 2026 still 1. Re-running with randomised tie-breaks at the 53-man cut moves
each count by at most 1 — 105 players sit on the exact boundary rating in 2017
alone, so the slice is tie-sensitive and the COUNT should be quoted as a range,
not a point.

**State the method with the number.** The master session measured the same
thing and got 3/1/0/1/1/1/0/2 — a different basis or position set, never
reconciled. The ORDERING was identical under every variant either of us tried,
and that is what the conclusion rests on: **the archive disagrees with itself
substantially more than 2026 disagrees with the archive**, and a gate
calibrated on the archive would fail most of the archive while passing the new
file.

**What CAN be a gate is the unanimous property.** No team in any of 256
published team-seasons is empty at any position. That is not a band, it is
0 versus not-0, and it catches the real defect — 16 teams with no defensive end
— on its own.

**The rule worth carrying: a reference set supports a GATE on properties its
members share unanimously, and only a WARNING on properties they merely cluster
around. Check which one you have before choosing the severity.**

## Rostered is not a basis

`rostered` means 53 players per team in one file and 67 in another. Every
cross-file count taken on it is comparing different things, and the resulting
gap looks exactly like a defect.

Four instances in the 2026 build alone:

- **Rating p10.** Madden read "compressed" against the published files — p10 63-74
  against 45-63 — and it was a 53-man cohort against a 59-68-man one. On top-53
  the gap is 1 point.
- **The registry-covered subset**, which over-weights long-career positions and
  is not a league.
- **RB count.** 128 against a published 172-209, 4.0 per team against 5.2-6.5.
  The published files are built from everyone who PLAYED that season. On a
  top-53 slice they read 4.2-5.4 against 2026's 3.9 — the apparent 1.5/team
  shortfall is 0.3.
- **QB count.** 92 looks wrong against three modern references (69-82) and sits
  inside the full archive's 69-96, because 1986 carries 93 and 2000 carries 96.

**Both of the last two closed on an arithmetic identity rather than a plausible
story**, which is the standard to hold: QB is 88 ACT + 4 RES = 92 exactly, and
RB is 113 ACT + 17 RES − 2 long snappers = 128 exactly. A number that
reconciles to the source needs no explanation; one that merely sounds
reasonable is not closed.


## Pre-2000 is the archive's weak cohort — and that is ALL that survives the cut

Asked what distinguishes the drift cases the archive cannot resolve. Position
does not: the front seven is 69% of the unsolvable set and 71% of the solvable
one. Era does — but **only one era claim survives a change of denominator.**

Share of archive entries sitting at 1-2 sources, by the entry's era:

    bucket by     <2000   2000-09   2010-19   2020+
    first_seen      69%       33%       60%      63%
    last_seen       70%       49%       56%      47%

`era_certain` changes nothing. **The date field changes everything between the
three modern bands** — under `first_seen` coverage looks U-shaped with 2020+
second-worst; under `last_seen` 2020+ is the best-covered band. Both are
defensible, because a player active 2018-2026 belongs to both buckets and the
choice decides which one counts him.

**What holds either way: pre-2000 is much worse than everything else — 69-70%
against 33-63% — and it is also the largest cohort at ~11,200 entries.**
Nothing else about the era ordering is safe to state.

**AMENDED 2026-09-02 (1979 build) — the cohort claim holds; do not read it as a
claim about every FILE in the cohort.** Pre-2000 is the weak cohort, and
`2000-09` is the best-covered band on either denominator. But coverage is a
property of the file, not of the era, and one pre-2000 file is the archive's
strongest single source:

| file | players | edited | note |
|---|---|---|---|
| **`1979-1980`** | **1,999** | **1,999 (100%)** | the only file of 42 at 100% |
| `1958-1980` (span) | 1,837 | 1,773 (96.5%) | |
| `1996-1997` | 1,921 | 832 (43.3%) | the weak end of the same era |

Measured for the 1979 build: **1,921 archive entries carry a `1979-1980` season
vote, against a 1979 league of roughly 1,260 rostered players**, 93.4% of them
unanimous. So a 1979 build is well served by the archive while sitting inside
the worst-covered era.

**The two statements are compatible and both are needed.** "Pre-2000 is the weak
cohort" is true of the ~11,200 entries and false as a prediction about 1979.
Neither sentence should be deleted in favour of the other; a session that reads
only the first will skip a source that covers its whole file. **Check the file,
not the era band** — `_files` in the archive carries `players` and `edited` per
source and answers this in one read.

*(A claim that the 1979 cohort is "better than any other era" was made in
conversation and is wrong: `2000-09` beats it on the archive-wide cut. Usable,
and the exception inside its band — not the best band.)*

**Three wrong characterisations preceded this, each written before the number
under it was read.** "Rises steadily toward the present", from a per-file rate
that is not monotone and reads 92% on a cohort of 13. Then "fewer sources the
more recent the player", printed as a conclusion in the same script output that
refutes it. Then "U-shaped, 2020+ second-worst", which is one denominator's
artifact presented as a property of the data.

**A finding that moves when you change the denominator is a property of the
cut, not of the archive.** Run the alternative before writing the sentence —
here it was one extra field and four numbers.

Kept separate deliberately: **74% of the 2026 cohort's DRIFT cases are
unsolvable from the archive.** That is a different measurement on a selected
subset — drift cases are not the general population — and it stands on its own
without the era claim.

## The free agent staff pool (2026)

**Every published file carries 165 free agent staff; 2026 shipped 0.** A user
who fires a coordinator had nobody to hire. The pool is `teamID == 'Free Agent'`,
and 453 = 288 team (32 x 9) + 165.

**Head coaches are real, every other role is invented.** Measured, not assumed,
by asking whether a free agent's name holds a team job in some modelled season
(a lower bound: it has false negatives, never false positives):

| role | FA n | proven real |
|---|---|---|
| Head Coach | 203 | **36.0%** |
| Off Co-ord / Def Co-ord | 141 each | 0.7% |
| Special Teams | 135 | 0.0% |
| scouts, physios | 135 each | 0.7-3.0% |

The precedent's claim survived the check. It would have been easy to assume.

**The pool draws from the past, not the future.** Free agent head coaches are
men who held a team job in an *earlier* season and are now out of work — 2004
is 12 past vs 1 future, 2010 is 24 vs 3. 2026 follows the same rule.

**2021 is the outlier and was not followed.** Its 27 free agent head coaches
match nothing in any direction, including the 2026 team side — that pool is
fully invented. Six of eight files source real coaches; the dominant precedent
plus *never invent data when real data exists* settles it against the newest file.

**A free agent has no contract but does have an asking price.** `salary`,
`guarantee` and `length` are zero in **1145 of 1145** published FA records,
while `eSalary` / `eGuarantee` / `eLength` are populated. Shipping a free agent
with a salary would have looked plausible and been wrong.

**Age ceiling 72**, the observed maximum across every published FA record.
Without it the real-coach supply reaches an implied age of 102 in 2026.

### How this measurement nearly went wrong

Three separate vacuous passes occurred while measuring these pools — a control
built from the names it was testing, a `teamId` probe returning `None` for all
453 records, and `min(teamID)` reporting nine Arizona staff as the league pool.
They are catalogued with the rest in **Vacuous pass is this project's dominant
failure mode**, which is where that family now lives rather than scattered.

The recombination test itself was **discarded, not reported**: rebuilt
leave-one-out, real team-side staff score 34-60% on it, so it does not separate
invented from real at all.

---

## Guidance embedded in a generated artifact cannot be corrected by editing documentation

Found 2026-09-02. A new failure shape, and the reason the `era_certain` defect
survived being written down correctly elsewhere.

`build_archive.py` writes a `_README` string *into*
`reference/PGM3_PLAYER_ARCHIVE.json`, telling any reader to "check
first_seen/last_seen against the season being built - but only where era_certain
is true." That instruction is wrong. It was corrected in
`PGM3_PROJECT_HANDOFF.md` and `PGM3_TASK_build_2026.md` the same day.

**The copy inside the artifact could not be corrected**, because fixing it means
regenerating the artifact — which was the repair ruled out for the same session.

**An instruction inside a generated artifact supersedes nothing and is superseded
by nothing.** A session that opens the archive to use it reads the embedded
guidance as though it came from the source of truth, with no signal that a
document three directories away corrects it. Documentation has a precedence
order; an artifact's own README sits outside it.

**Consequences:**

- **Prefer a pointer to a claim.** An artifact's embedded README should say where
  the current guidance lives, not restate it. A stale pointer is still a working
  pointer; a stale claim is a wrong claim asserted by the source of truth.
- **A generator that emits guidance is emitting a second copy of documentation**
  that no doc edit can reach, and that will not be re-read when the doc changes.
- **When correcting an instruction, grep the artifacts too**, not just `docs/`.
  The defective sentence existed in three places and only two were editable.

Recorded as backlog item 18's third copy. Fix in the same pass that fixes
`stock_names()`.

---

## A field name can assert a confidence the code never computes

`era_certain` reads as a verified flag. Its implementation is
`build_archive.py:129`:

```python
e['era_certain'] = bool(e['years'])
```

It is a **null check**. It means "at least one vote survived the stock filter",
never "the era is known". For a man whose only era-bearing votes were filtered
out and whose remaining votes come from another era entirely, it reads `True`
while the window it certifies is built from the wrong person — D.D. Lewis, a
1979 Cowboys linebacker, `era_certain` True over a window of 2004-2009.

An empty window abstains and is safe. **A wrongly-populated window asserts, and
the flag named `certain` is what makes it credible.**

**The name is documentation, and this one was wrong.** Three separate documents
told build sessions to trust the field, all three written by people who had read
the name and not the line. The general rule:

- **A boolean whose name claims correctness must be checked against its
  implementation before it is trusted**, especially where it gates a decision.
- **Prefer names that describe the computation** — `has_dated_votes` cannot
  mislead the way `era_certain` does.
- This is the "a safe default is still a claim" family, moved into the naming
  layer: a confident name is a claim about the data, made by whoever typed it.

---

## A file checked for one field and found wanting has not been checked

Twice in two sessions a file already in the repo turned out to hold what a build
needed, after being dismissed.

- **The 1986 retro mod** was opened for faces, found unhelpful, and set aside.
- **`1979-1980SAVEGAME.DAT`** was indexed into the player archive for **skin band
  only**. The build session read the archive's schema, saw one appearance field,
  and reported to Ryan that *no attribute source exists for 1979* — naming
  ratings as the build's largest open question. The underlying file carries
  **height, weight, jersey, years pro and eleven attributes** with real
  per-player signal: Dorsett 98 speed against Payton 89, Blount top corner
  coverage, Lambert and Ham top the tacklers, kickers at 39 speed.

**The index is not the file.** An indexer extracts what its author needed on the
day. Its output describes that intent, not the source's contents — and a later
session reading only the index inherits the earlier session's question, not the
data.

**The rule: before declaring a field unsourceable, open the source, not the
artifact derived from it.** `nfl2k5.Save(path).players[0].keys()` is one line and
it was never run.

Related but distinct from the stale-artifact rule, which is about a file that
*changed*. Here nothing changed and nothing was stale — the file always held the
attributes. What was stale was a **conclusion about the file**, and conclusions
about sources need re-deriving when the question changes.

---

## The field that resolves identity varies by dataset — third independent route

A composite key cannot do identity work. This project has now reached that
conclusion three times, from three datasets, each needing a **different** extra
field:

| build | the discriminator | what it separates |
|---|---|---|
| 2026 | **birth date** | fathers and sons, namesakes across a career gap |
| the 2K5 archive | **era** (`first_seen`/`last_seen`, or better, a season vote) | 68 years of namesakes, 81% false-match rate on name+position |
| **1979 rosters** | **college** | two men who share a name, a position AND a season |

**The 1979 case is the strongest, because position fails inside a single
season.** Splitting 41 repeated names on college + age gave 30 genuine
mid-season movers and 10 namesakes, and **two of the namesakes share a
position**:

    Larry Brown      OT, Miami, 24   Kansas City   |  OT, Kansas, 30      Pittsburgh
    Gene Washington  WR, Stanford, 32 Detroit      |  WR, Georgia, 26     NY Giants

Name+position merges both men. There is no era gap to exploit — it is one
season. Only college separates them.

There is also a **same-team** pair: Cleveland carried two Robert Jacksons in
1979, an offensive guard (#68, Duke) and a linebacker (#56, Texas A&M). Any key
built on `name|team` merges them, and `name|position|team` — the key this
project settled on as "unique in the widest population" — happens to work here
only because their positions differ.

**The rule to carry:** do not reach for position by habit, and do not assume the
key that worked on the last dataset transfers. **Ask what field the specific
collision does not share**, and check that the dataset actually carries it. The
1979 rosters carry college for free; the Madden exports do not.

**Corollary — the discriminator is a property of the SOURCE, not of the
project.** A build that changes source changes discriminators. Recording which
field did the work, per build, is cheaper than rediscovering it.

---

## Record a coin flip as a coin flip

The 1979 mover rule assigns a player to the team he played the most games for.
It resolves 28 of 30 cases, which reads as a clean rule — and **15 of the 30 are
decided by a margin of two games or fewer**, two of them exact ties.

Median margin is 2.5 games. Only 8 of 30 have a margin of 5 or more.

Two sources were tested as a principled tiebreak and neither works: the 2K5
block agrees with the games leader 10 times, disagrees 7 and is absent 13; and
footballdb's player pages collapse a mover to "2 TMS" with no team order at all.

**Ruling (Ryan, 2026-09-02): keep the rule, and state plainly that it is thin.**
Each case moves one player between teams carrying 46-60, so the cost of being
wrong is a single roster slot and it is not worth buying a source to resolve.

**The precedent is about the writing, not the rule.** A rule that resolves 28 of
30 will be read by a later session as well-founded unless the margin is recorded
beside it. Documenting the resolution rate without the margin distribution would
have made a coin flip look like a finding — the same shape as quoting a
correlation without its cohort, or a gate without the population it ran against.

**Where a rule reaches no answer at all, make it a hand call and log the
reason.** Jerry Golsteyn played one game for Baltimore and one for Detroit and
has no 2K5 record. He is assigned to Baltimore because that is where he started
the season, recorded in `build_1979_roster.py` as a named exception rather than
absorbed into the rule.

---

## An anchor that FAILS for the wrong reason is worth more than one that passes

Two instances in one session, 2026-09-02.

**Instance 1 — Ed "Too Tall" Jones.** Ryan supplied him as the anchor for the
1979 expansion pool: out of football that year to box, rated 88 in the Madden
file, "ten points clear of any other free agent." Both facts were true. But the
first run returned `POVR: None`, because **footballdb spells him "Too Tall
Jones" and the Madden file spells him "Ed Jones"** — the documented
rename-between-sources bug. A silent match would have confirmed the anchor and
hidden the defect. The failure exposed a name-normalisation gap affecting 50 of
308 pool members.

**Instance 2 — Fred Biletnikoff and Fran Tarkenton.** Supplied as men who must
be in the pool. They were. But checking them found a **third** defect by
adjacency: chasing career spans for the same cohort surfaced Bo Rather, John
Woodcock and Reggie Haynes, all of whom Wikipedia places in the NFL in 1979 and
none of whom appear on any cached footballdb 1979 roster.

**The general form:** an anchor is chosen because its answer is already known,
so a pass conveys almost no information — it confirms what was already believed.
A failure is the only informative outcome, and the first question is always
**"is the anchor wrong, or is the pipeline wrong?"** Here it was the pipeline
both times.

**Consequence for choosing anchors:** prefer ones whose *identity* is awkward —
nicknames, suffixes, position changes, cross-source spelling — over ones whose
value is merely famous. A famous player with a plain name tests nothing but the
happy path.

---

## Instance: the widened retry that manufactured its own findings

Recorded as a worked instance of "a widened check reports its own reach errors
as findings", which had no example attached.

50 of the 308 pool members had no Madden rating. The documented remedy is to
"scan the unmatched list for names that look almost right", so the retry was
loosened from `first + last` to `surname + age within one year`. It produced 13
candidates. **Ten of them are different men:**

    Too Tall Jones   -> Ed Jones        88   GENUINE (nickname)
    Roland Woolsey   -> Rolly Woolsey   73   GENUINE (nickname)
    John McKay       -> J.K. McKay      77   GENUINE (initials)
    Danny Johnson    -> Ezra Johnson    88   WRONG
    Larry Franklin   -> Tony Franklin   92   WRONG - a kicker for a receiver
    Ken Moore        -> Dean Moore      64   WRONG
    James Van Wagner -> Steve Wagner    74   WRONG - surname split differently

**77% false.** The tell is that the wrong matches are not near-misses: a
92-rated kicker offered for a 23-year-old receiver is not a spelling variant.

**Ruling: the three confirmed aliases are hard-coded by name; the other 37 stay
unmatched and logged.** Applying the retry would have attached real ratings to
the wrong men in a file where nothing downstream could detect it — the rating
would be in range, the position live, the distribution unchanged.

**The rule the instance illustrates:** when a documented remedy is loosened to
reach further, measure its false rate on the cases you can verify BEFORE
applying it to the ones you cannot. A remedy is not a licence.

---

## Reading or committing files the user did not attach requires asking first

Ryan attached one file, `1987.mdc`. The build session listed the directory
containing it, found thirty, read all thirty, copied all thirty into the repo
and pushed them to a public remote. **Nobody asked for twenty-nine of them.**

Two distinct overreaches, and they are not equally serious:

- **Reading the other 29** — an overstep, recoverable, and it did produce real
  findings (the 2008/2009 byte-identical duplicate, the 257-row container cap).
- **Publishing them** — outward-facing, irreversible in practice, and not the
  build session's decision to make. They are third-party community files, so it
  also republished someone else's work under this repo's name.

**The rule: an attachment is permission for that file, not for its directory.**
A path in a message names one file. Wanting the neighbours is a reason to ask,
not a reason to take them.

**What made it feel authorised, and why that was wrong.** The master session's
message said *"there are thirty of these files… 1988 through 1990 feed 1986's
remaining classes."* That is context explaining why the attached file mattered.
It was read as licence. **Context about what exists is not permission to go and
get it** — and the master session recorded that the ambiguity was its own.

Disposition (Ryan, 2026-09-02): the whole `sources/` tree moved out of the repo
and into `.gitignore`. Nothing deleted, no history rewritten.

---

## "Cache what you fetch" applies to sources that can vanish, not to the user's own disk

The standing practice of committing fetched sources exists for one reason: a web
page can go down, a site can start refusing the transport, and a rebuild months
later must not depend on either. `sources/1979footballdb/` is exactly that case
— footballdb is behind Cloudflare and admits only one client.

**It was then applied to thirty files sitting in Ryan's Downloads folder.** They
could not go stale, could not become unreachable, and were already backed up.
The rule's entire justification was absent, and it was used anyway to make an
unrequested action feel routine.

**The test before invoking it: name the disappearance you are guarding against.**
If there isn't one, the rule does not apply and the action needs its own
justification. A precedent invoked without its precondition is not a precedent,
it is a rationalisation — and this one covered publishing files that were never
handed over.

---

## A derived field is re-derived after EVERY stage that moves its input — three instances in one build

Building the one 2026 write, the same bug surfaced three times in one evening,
each caught only by measuring the gated artifact:

1. **potential vs rookies.** Potential was drawn from 2017's curve, then the
   rookie rescale lowered rating and left potential where it was. Rookie headroom
   read 10 against 2017's 6.
2. **decisions vs the QB range rule.** Stage 6 drew offensive `decisions` from
   the archive; stage 8 then clamped it back to Madden's range for that field —
   which at QB is 10-68, the unpopulated noise the draw had just replaced. 41
   moves over the cap, max 31, all in one field.
3. **decisions vs rating.** Stage 6 moved a field with weight 0.183 at QB and did
   not recompute the overall. The rating invariant fell from 99.9% to 91.0%.

**One rule:** a field that is a *function* of others — `rating` of attributes,
`potential` of rating, `growthType` of potential − rating — is re-derived
after every stage that touches any input, never once at a fixed point in the
sequence. A stage order that reads "potential → rookies" cannot be honoured
literally; it is honoured by re-deriving potential after rookies.

**Corollary for range rules:** a clamp built from a source field must not apply
to a value that was deliberately drawn from somewhere else. The source's range
for an unpopulated field is the range of its noise.

**And the probe caught itself once:** the "max move 19" that looked like a cap
failure was the measurement diffing against a baseline that predated stage 6 —
it was the archive draw, doing its job. Isolate a stage by building the artifact
without it, not by assuming the last scratch file is the right baseline.


---

## A probe must not carry its verdict as a string — second instance in one day

Audit 25f recorded a `print("ASSERTED: ...")` that stated a conclusion the
assert beside it had not checked. The same evening a second probe ended with a
hardcoded tell — *"weighted agreement well above the naive mean means the source
ORDER is fine"* — printed under numbers reading 0.12 to 0.54, which the
adjoining column explained as the 2K5 file covering only 21–75% of each
position's weight mass. The correct reading was "inconclusive where coverage is
low," and the sentence said the opposite.

**The rule:** a probe prints numbers and labels. The verdict is written *after*
reading them, by the person, in the report. A tell composed before the run is a
prediction, and printing it beside the result makes a prediction look like a
finding — whichever way the numbers went.


---

## A scope defined for one purpose becomes the scope for everything downstream unless each stage re-decides it

One variable, set at line 69 of the 2026 tool for the rookie and potential
questions — rostered questions — was inherited by every stage through the QB
level. Nothing chose it; each stage used what was there. 465 free agents with
real Madden ratings and the same stretch went untouched by a write built to fix
the stretch. **A variable named for one cohort became the scope for eight stages
that never chose it.**

Ruled fix: each stage states its own cohort, in its own variable, even where the
answer is the same — the bug was the absence of a decision, not the wrong one.
Same family as the derived-field rule: a value set once and reused without
reconsideration. And its sibling, found the same night: **a tool that reads the
file it writes will run its stages twice** — take an explicit source, assert it
is not the output.

---

## An in-band aggregate can hide wrong records — read the names inside it

1979's CB/S ratio came in at 1.02, out of the published 1.06–1.30. The 2K5 save,
labelling independently, read 1.28 — in band — and was recommended as the
tiebreak. The 20 records in one direction of the disagreement included **Roger
Wehrli, Raymond Clayborn, Lemar Parrish and Neal Colzie, labelled FS** by the
in-band source. The recommendation was retracted; Wikipedia career positions
then backed the out-of-band source **24 to 2**. No ratio test finds a Hall of
Fame corner filed as a safety. Look at the names inside the number before
trusting the number.

---

## A two-way disagreement can have a third answer

1979's DB arbitration was framed as NFL79.ros says safety versus the 2K5 save
says corner. Sixteen cases were left after the career-article check, and the
ruling was to take NFL79's label for the twelve unresolved ones — cheap, and
the direction was 24-2 plus 4-0 on the names that mattered.

A scripted pass over the Wikipedia 1979 season rosters — one fetch per team,
minutes — settled ten of the twelve in NFL79's favour and found two it could
not have found: **Lawrence Johnson is a cornerback**, and **Ricky Jones is an
outside linebacker**. Jones is the one that matters. Both sources called him a
defensive back and the question "corner or safety?" had no room for the true
answer. The framing of a disagreement silently asserts that one of the two
sides is right.

Sibling of the in-band-aggregate precedent: there the number hid the wrong
records, here the question hid the right answer. **And a ruling made to avoid an
expensive check is worth re-testing when the check turns out to be cheap** — the
ruling's stated basis was cost, not evidence.


---

## A join on the exact name string measures the name format, not the coverage

1979's brief named **17 players with no rating data of any kind** and had them
down for hand-rating, approved. All 17 were in the source. The mod writes Bill
for Billy, Tim for Timothy, Don for Donald, Arthur for Art, and disambiguates
namesakes with a middle initial. One was a nickname a diminutive rule would
never reach: footballdb's *Deac Sanders* is the mod's *John Sanders*, and the
article confirms **John Maurice "Deac" Sanders**.

Coverage went 97% to 100% by adding one tier — team + surname + compatible
position — and the position gate earns its keep immediately, because Cleveland
rostered **two Robert Jacksons** in 1979, a guard and a linebacker.

**A coverage number is a claim about the join, not about the source.** Before
reporting a cohort as unreachable, join it a second way.

---

## An out-of-band aggregate can be the wrong population rather than the wrong data

The 1979 CB/S ratio escalated at 1.02 against a published band of 1.06-1.30, and
three separate arbitration passes were run against the labels. The number
reproduces — but it was taken over **the mod's own 28 rosters**, not the 1,408
footballdb spine the file is built from. The mod carries 44 men who were not on a
1979 roster, 13 safeties against 3 corners. On the population actually being
built, the ratio is **1.14**, mid-band.

The label work was not wasted; it found two real errors. But **check that a
failing aggregate was computed over the population you are shipping** before
concluding the data is wrong. Sibling of "read the names inside the number."

---

## A gate must measure the population the file will contain, not the population the source contains

**Ruled by Ryan, 2026-09-02.** The 1979 CB/S gate read 1.02 against a published
band of 1.06-1.30 and triggered three arbitration passes. It was computed over
the mod's own 28 rosters. Over the 1,408-player spine the file is actually built
from, the same source reads **1.17** — mid-band. The mod carries 44 men who were
not on a 1979 roster, 13 safeties against 3 corners, and they were the whole
discrepancy.

Same class as the OLB coverage write: **a check run on a cohort adjacent to the
one being shipped.** Before escalating a gate, state which population it was
computed over and confirm it is the one going into the file.

The passes earned their place regardless — they found Lawrence Johnson at corner
and Ricky Jones at outside linebacker. **A binary escalation cannot surface a
third option**; only reading the roster did.


---

## When a new measurement contradicts an old one on the same data, the contradiction is the signal

The 1979 potential curve was computed from the published six and the 2017 column
came out **all zeros**. The 2026 build had used **6/4/2** from that same file, on
that same field. Nothing failed: the buckets were populated, the medians were
plausible, no assert fired and no test existed that would have caught it.

The defect was that `draftSeason` sits on the 2026 game clock in every file, so
*(file year − draftSeason)* is negative for 100% of the 2004 roster and the
filter dropped it. The curve rested on 243 players instead of 1,990.

**What caught it was disagreement with our own prior work, not a test.** Both
numbers came from the same file and the same field, so one of them had to be
wrong. That is a stronger signal than plausibility, and it is available for free
whenever a measurement has been made before — so **when you re-measure something
the project has already measured, compare against the old number and treat any
gap as a defect until you know which side it is on.**

Ryan's framing: *one of them is wrong, and the contradiction is the signal.*

---

## A missing value that sorts is worse than one that errors

The 1979 expansion allocation ordered Jacksonville's roster "cheapest first",
which for 47 of the 308 pool members — men with no Madden record — meant a rating
of **zero**. Zero is a valid rating, so the sort worked, raised nothing, and
returned a plausible-looking roster. **30 of Jacksonville's 46 arrived that way,
including Jackie Smith, Mick Tingelhoff, Emmitt Thomas, Chris Hanburger, Willie
Brown and Jake Scott.** The franchise whose entire doctrine is never signing
anyone expensive was handed the Hall of Fame.

Nothing failed. The defect was visible only in the *shape* of the result.

**Fix: hold the missing out of the comparison, do not rank them last.** A sort key
that returns `(is_missing, value)` keeps them from competing on a number they do
not have. Ranking them at the bottom is the same bug wearing a seatbelt — it still
asserts an ordering the data cannot support.

**And a fix that respects one constraint can violate another silently.** Splitting
the unrated by doctrine left two rosters half unsourced; capping that sent the
overflow to Memphis and aged it from 24 to 27, costing the one thing its doctrine
asks for. Both were caught by re-reading the shape, not by a gate. Ryan's framing:
*it was the shape check that caught it, not a gate.*

---

## A gate built from later files, applied to an earlier era, fails the correct file

The 1979 face step asserted its rostered dark share against the published files'
range, **64.4-72.9%**, and failed at **55.9%**. The published range is a
1986-2021 population. The era's own archive says 1979 sat at **53.6%** over this
file's names and **57.3%** over all 1,999 men in the 1979-80 save; 1981-82 reads
48.2%, 1983-84 53.6%. The file was right.

**The calibration is what made it decidable.** The archive and the published
files agree within a point wherever both are trustworthy — 64.3 vs 64.4 in 1999,
65.7 vs 65.3 in 2004, 68.1 vs 69.5 in 2012 — and diverge by about seven points at
both ends: the published **1986** file reads 67.8% against its own era's save at
58.6-60.7%, and **2021** reads 72.9 against 65.6. So the gate's floor was set by a
file that itself runs seven points darker than its source.

Same family as *a gate must measure the population the file will contain*, one
step further: **a published range is a range over the eras that were published.
Before applying it to a season outside them, measure the era's own source and
gate on that** — and print the published range beside it, so the divergence is
seen rather than smoothed.


---

## A validator run after a crashed build step reports on the previous file

Twice in the 1979 assembly the build chain died before its write, the validators
ran anyway on the files from the run before, and the failures they printed were
read as evidence about the patches just made. They were not. Then a commit gate
that counted every line containing "FAIL" counted the summary line "1 CHECK
GROUP(S) FAILED" and refused a clean build. Put the validators *inside* the chain
that writes the file, gate on the check lines and the exit codes, and print the
build's own "wrote" line beside them. A result is about the file that exists, not
the one you meant to make.

---

## "Coverage 100%" is a claim about the join

Step 4 of 1979 reported every spine man joined to a mod record. It was true, and
18 of them shared 9 records: tier 2 took a unique name anywhere in the mod without
checking position or whether the record was already claimed, and a defensive end
shipped with a running back's attributes. Found five steps later by a uniqueness
assert in assembly. **Bind the strongest tier first and consume; assert one-to-one
on the source side; and read a coverage number as what it measures.**

---

## Match the artifact's formatting, or the diff stops being a check

Two files in this project are stored as a single line of compact JSON. Writing
them back with `indent=1` produced **252,866 lines** for a two-record change to
the 2026 roster, and **180,072** for a thirty-nine-face change to the registry.

Nothing was wrong with either file. But `git diff` is the last check before a
push — the one that catches a tool touching records it was never asked to touch —
and a diff that large cannot be read, so the check silently stops working at
exactly the moment the change is largest.

**Write back in the format the file is stored in**, and confirm it: a two-record
change should produce a one-line diff. Both write tools now pass
`separators=(', ', ': ')`, and the semantic diff — records added, fields changed —
is printed alongside, so the two can be compared.



---

## Do not assert provenance from a word you have not checked the meaning of

**2026-09-03.** Asked which prospect-ceiling defects were ours, I reported that
2004, 2007, 2010, 2013, 2017 and 2021 were "published originals" and 1986, 2000,
2026 and 1979 were ours. **The first half was invented.** All ten files are this
project's own work.

The error was reading one word two ways. This project says *published* to mean
*published by us to the repo* — the handoff's own sentence is **"one command gets
all ten published files"** — and I read it as *shipped by the game's developer*.
Nothing in the record ever claimed 2017 was inherited. `PGM3_PRECEDENTS.md` in fact
records that **2017 originally had invented names above real ones and had to be
fixed**, which is only possible for a file we build; I had the disproof in the same
document I was writing into.

**It changed a decision.** Ryan ruled to leave 2017 alone *because* it was
inherited, and the ruling rested entirely on my claim. A false provenance statement
is worse than a wrong measurement: a measurement gets re-run, while provenance is
taken on trust and then cited.

**Rule: provenance is a claim like any other and needs a source.** Before saying a
file, field or convention came from somewhere, point at the thing that says so. And
when a project word carries a specific local meaning — *published*, *donor*,
*vanilla*, *archive* — check which sense the record is using rather than the sense
it has elsewhere.


---

## A band computed from our own files describes our convention, not the engine

**2026-09-03.** To gate a contract-compression transform I built a position-
multiplier band from the eight files whose salary distribution already looked
right, and used it to assert that no position could drift outside normal. It
caught a real defect immediately — a transform sending quarterbacks to 5.9x the
file median — so the gate worked.

Then Ryan exported a **full vanilla league**, the first complete game-generated
reference the project has ever held. **Seven of the ten positions in that file sit
outside the band.** Kickers read **0.59** against our 1.00-1.92; corners 2.18
against 0.83-1.01; tackles 0.86 against 1.06-1.26.

That is not seven anomalies in the game. It is one systematic difference between
what the engine does and what our files do, and the band was measuring the wrong
side of it.

**The sharpest instance: we paid 1979's kickers 0.77 as a DELIBERATE ERA DEPARTURE
from a modern norm of 1.00-1.92 — and the game pays 0.59.** 1979 was closer to the
engine than the eight files we called conforming. The "departure" was a partial
correction toward the truth and the premium is ours.

**Rule: before asserting that a value is normal, ask what population the norm was
computed over.** Agreement among our own files is evidence of a shared ancestor,
not of correctness — the same shape as ten files reporting a $197.4M payroll
constant to the dollar against the game's $242.9M, and as five files reporting a
contract ceiling that turned out to be one donor record. When the check is a
guard against a specific failure, assert the failure and not the norm.
