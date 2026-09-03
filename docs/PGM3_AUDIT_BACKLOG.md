# Audit backlog

**Ruling (Ryan): 2026 ships first. Then 2021 and the rest are audited properly,
rather than patched as things surface.**

Nothing on this list is fixed. Each entry is here because patching it mid-build
would mean changing a shipped file on the strength of a finding that has had no
review pass of its own — which is how the defects below got in.

---

## 1. 1986 is the rebuild candidate, not 2021

Where the day started, 2021 looked like the badly-built file. Measured side by
side, **1986 is worse on every invariant**:

| | 1986 | 2000 | 2021 |
|---|---|---|---|
| rostered rating invariant, >5 | **629** | 476 | **0** |
| prospect invariant, >5 | **627** | 366 | 105 |
| verified faces drifted | **6** | 0 | 0 |
| unsourced prospect + FA cohorts | **yes** | — | — |

2021 holds the rostered invariant that 1986 and 2000 break badly. A rebuild
decision, if one is made, points at 1986.

---

## 1b. 2021 was built to a different standard

**MEASURED AGAINST ITS SIBLINGS — the case is weaker than this section claimed.**
Two of the four defects do not survive the comparison:

| claim | 2021 | siblings | verdict |
|---|---|---|---|
| free agent salary non-zero | **103** | 0 in all seven | **holds, unique** |
| prospects break the rating invariant | **105** | 0 in 2004/07/10/13/17 | **holds** (1986 627, 2000 366) |
| `eGuarantee` populated | 1425 | 2013 **1500**, 2010 1364, 2007 1213 | **does not hold** — 2021 is mid-pack |

*(Ryan's independent read gave 2021 at 0 and 2013 at 144 — a different field or cohort from mine. The conclusion is the same either way: 2021 is not uniquely bad on it. The disagreement is unresolved and the claim rests on it not holding under EITHER measurement.)*

| family-2 skin share | 9.2% | 1986 8.2%, 2017 8.0%, 2013 7.2% | **weak** — a continuum, not an outlier |

And 2021 **holds** the rostered rating invariant (0 players over 5), where 1986
(629) and 2000 (476) break it badly. On that measure 2021 is with the good
files, not the bad ones.

The invented free-agent coach pool (0 of 27 head coaches real) still stands.
So the honest count is **two or three defects, not four to six**, and 1986 and
2000 are the worse files on every invariant measured. Any decision to rebuild
2021 should start from this table rather than from the earlier count.


Four independent defects now, in one file, each found by a different route and
none by any existing check. That is no longer a run of bad luck; it is evidence
about how the file was produced, and it should be audited as a whole rather
than defect by defect.

| # | defect | evidence |
|---|---|---|
| 1 | free agent salary | non-zero where every other file zeroes it |
| 2 | family-2 skin | band distribution unlike any other file |
| 3 | `eGuarantee` | populated against the archive's own pattern |
| 4 | **free agent pool fully invented** | 27 free agent head coaches matching **nothing** in any direction — no earlier team job, no later one, and nothing on the 2026 team side. Six of eight files carry real coaches; 2004 is 12-past-vs-1-future, 2010 is 24-vs-3. 2021 is 0. |

The fourth was found while building the 2026 pool and is the clearest of the
four, because the comparison is against seven sibling files doing the opposite.

**Audit question, not yet answered:** are these four the whole of it, or is 2021
systematically different in ways nobody has probed? Every check that has been
pointed at it has found something.

---

## 2. Coverage of the checks themselves

**The `faces` gate reaches ~26% of what it protects.** 78 of 105 verified
players (74%) are unreachable because their lock is keyed in a format the
checker cannot read. The gate reports clean over the quarter it can see. This
is the largest single instance of the vacuous-pass family and it is still live.
See *Vacuous pass is this project's dominant failure mode* in the precedents.

**The 78 are audited. Almost nothing has drifted.**

    head family changed    1 person   Jerry Rice, WR SF, in 2000 (family 5 -> 4)
    hair/beard/brow        0
    variant only          24 people, 55 records   expected, not drift

They are the marquee players -- Montana, Taylor, Reggie White, Marino, Munoz,
Payton, Elway, Lott, Rice at 94-98 -- and their hand-set faces have held.

**CORRECTION.** An earlier pass reported six drifts, all in 1986, four of them
described as newly discovered. **All six were false**, and the cause was the
gate I had just widened: `faces` (2-part keys) and `faces_1986` (3-part) hold
**23 keys in common, every one with a different value**, and six of those are
verified. The gate preferred the 2-part block, so it compared an 1986-era
verified face against the wrong entry. Precedence fixed -- a 3-part verified
key reads `faces_1986` first -- and the six resolve to zero.

**The real finding is about the registry, not the file.** Two blocks carry
conflicting values for 23 players with no precedence ever defined between them.
That is a history artifact and it is where a future error will come from.

---

## 3. Cross-file data defects

| defect | measured | notes |
|---|---|---|
| **team payroll vs roster QUALITY** | measured, all nine files, eight definitions — see the precedent *Payroll and quality: measured, and what survives the definition* | **Closed, not an audit item.** 2026 is at the low end (rank 1-3 of 9) but 2000 occupies the same territory under every definition, so 2026 is not outside the archive's range in any robust sense. |
| ~~team payroll vs roster COST~~ | **STRUCK** | Not measurable as specified. On the files' own fields it is a tautology (payroll = salary+guarantee vs cost = salary, r>=0.86 in all nine). The original +0.67/-0.57/+0.08 used real SOURCE contract money, which exists for 2026 only; historical files have no equivalent. A measurement that cannot be defined is not a task -- if it matters later, the definition comes first. |
| **`trucking` means different things in different files** | not yet quantified | the handoff mapped it to `BreakTackleRating`; 2026 uses `TruckingRating`. Whether earlier files agree is unchecked. |
| **K/P contract inflation** | not yet quantified | a `fix_kp_contracts.py` exists, which implies a known past instance |
| ~~OLB coverage junk~~ | **FIXED** — four files, not two | 1986 (173), 2010 (43), 2013 (552), 2021 (403) fill values zeroed. Five of nine files already gated these off; that is the convention. Identical fill vocabulary in all four (`manCover` in {1,2,3}, `zoneCover` in {1}) against an MLB range of 38-92, which is what identified 1986's 46-of-143 and 2010's 6-of-153 as the same defect partially applied. **2026 is now ALL CLEAR** — this was the last gate failure firing on every run, and it was contaminating the reference union 2026 is measured against. |
| **2017 zero-salary records** | 37 rostered at `salary` 0 = **1.9%**, vs 0.0% in 2010/2013/2021 | already excluded from the 2026 quantile target |
| **1986 prospect and free agent cohorts are unsourced** | not yet quantified | 1986 is also the file with the 1,745-of-1,746 registry write |
| **170 thin drift cases** | 170 | unsolvable from the archive alone; needs an external source |

---

## 4. Found while building the 2026 free agent pool

**The head-coach ranking selects for the recently fired and excludes every
legend.** Candidates are ranked by recency of last team job, then cut at 27.
The archive does the opposite: it keeps highly rated coaches in its pools for
decades — Cowher appears as a free agent in 2007, 2010 **and** 2013 without
ever returning to a team, and Parcells, Gibbs, Seifert and Dungy behave the
same way. **35 coaches** the archive keeps are outside a top-27-by-recency cut,
and they are the highest rated of the whole population (Gibbs 91, Seifert 90,
Cowher 90, Parcells 90, Dungy 86).

Bill Cowher was added by name for 2026 on Ryan's ruling, displacing the
lowest-rated of the recency picks (Hue Jackson, 59). **The general bias was
deliberately not fixed** — widening the ranking rebuilds 16 of the 27, which is
a different pool, not one addition, and it belongs in a reviewed pass.

**Do not fix it by sourcing from published free agent records.** That was tried:
those pools are mostly the archive's own invented coaches, and the widened
candidate list came back full of Jocelyn Lyndhurst, Quill Kestrel and Caspian
Thornbury. **A team-side record is what makes a name real.** The age-72 ceiling
independently excludes most of the legends anyway (Gibbs would be 87, Seifert
79, Belichick 74).

---

## 5. Still open from earlier passes

- **Teach the `faces` gate both `_verified_keys` formats** — prerequisite for §2.
- **The 170 thin drift cases** — see §3.

---

## 6. Found at the `main` merge

**The faces gate cannot tell namesakes apart, and reports them as drift.**
Adding 2026 to the cross-season faces run took head-family disagreements 7 -> 8
and hair 16 -> 17. Both extras are one person: `chris brazzell|WR`.

    2000   Chris Brazzell      age 22  DAL  rating 58   Head4a / Hair1o
    2026   Chris Brazzell II   age 22  CAR  rating 72   Head5a / Hair1n

Two different people. `norm()` strips suffixes anywhere — correct and necessary
for the join layer — so father and son collapse to the same `name|position`
key in the checker. Both faces sit in the dark band (4 and 5), so nothing is
visibly wrong; the gate is reporting a false positive, not a defect.

This is the same namesake problem the join layer already solved with birth
dates (Michael Carter vs Michael Carter II). The faces gate never got that
treatment. **Fix belongs with the "teach the gate both key formats" work in
§2** — the key is the shared weakness.

**Staff faces failures (21 head family / 38 hair / 40 face / 2 verified-key
overwrites, Jim Mora in `PGMStaff_1986` and `PGMStaff_2000`) are ALL
pre-existing.** No staff file except 2026 was modified by this build, and the
gate returns byte-identical output on the old `main`. They belong to the
archive, not to this work.

---

## 7. Files that break the computed-rating invariant

**1986 — RECLASSIFIED as an ATTRIBUTE defect, and a documented EXCEPTION.**
Not fixable, and the fix that worked for 2026 would make it worse. Tiered from
the output (no build script exists): **zero** of its 28 attributes are
percentile-filled, so they are authored throughout and there are no filled
cells to rescale. Its ratings already match the published distribution at every
quantile (40/59/71/86/98). Storing the computed value would give 31/55/72/88/99,
put 134 prospects below 40 with the worst at 6, and move 506 ratings by more
than 10 points. **Excluded from the invariant gate for this reason** — a
known-unfixable file failing a gate forever teaches nothing. It needs an era
source with machine-readable attribute data, and none exists.

**2000 — FIXED, through filled cells only (Ryan, 2026-09-02).**

    invariant        median 3.10 -> 0.08      over 5: 1026 -> 298
    rating dist      40/59/70/85/98  ->  40/59/70/85/98   (identical)
    fields changed   the 9 filled attributes, nothing else
    records changed  2,727

Both properties that make this the better trade were **asserted, not assumed**:
no rating moved, and no sourced attribute moved. The faces gate and the full
roster gate are byte-identical before and after — 2000's pre-existing warnings
and its `zero-pattern` failure are untouched.

**336 records refused and left broken**, the same rule as 2026's tier-1
refusals: a record that cannot be fixed without touching sourced data stays
broken and documented. They are dominated by long snappers carried at position
C with a structural +37 gap, and by DT/DE/CB/OLB. `tools/fix_2000_invariant.py`
is reproducible and re-derives the filled set from the output each run.

**Original assessment, retained.** Nine of its 28
attributes are percentile-filled, six at exactly rho 1.000 (`decisions`,
`routeRun`, `vision`, `skillMove`, `zoneCover`, `elusiveness`). That allows the
**inverse** of the 2026 fix: keep the authored rating, which matches the
published distribution (40/59/70/85/98), and adjust only the FILLED cells so
the attributes support it. Measured, **3,192 of 3,351 records (95.3%) can have
their gap closed by filled cells alone**; 159 cannot, the worst short by 21
points. This touches no sourced data and does not move the rating distribution
at all. NOT APPLIED — 2000 is published.



The archive's rule is that a player's stored rating is whatever his attributes
compute to. Four published files hold it across **11,737 records** — median
0.26, max 3.45, **zero** players more than 5 off. Three files break it:

| file | median | max | >5 points | >10 |
|---|---|---|---|---|
| 1986 | 3.60 | 22.9 | **632** | 122 |
| 2000 | 2.95 | 24.2 | **481** | 81 |
| 2026 (pre-ruling) | 1.75 | 30.2 | 359 | 81 |

2026 is fixed by storing the computed value. **1986 and 2000 are deliberately
not fixed** — this is the fourth and fifth piece of evidence that both were
built to a different standard, alongside 2000's known defects and 1986's
1,745-of-1,746 registry write. `assert_rating_matches_attributes` now gates
this, so no future build can reintroduce it.

---

## 8. `build_derived` — the FIFTH dependency-order instance

**Not moot, and not closed.** Re-measured after the rating became a function of
the attributes: median +0.66, p90 +6.44, max +8.25 on tier 1. Most of that is
legitimate -- it populates derived cells that were zero, and a zero cell
contributes nothing to the computed rating.

The defect is ORDER, not magnitude. It runs **after** the fill's rescale, so
zero-information rookies drift up to **+6.2** past the draw that was
deliberately truncated to keep them low. Median drift is +0.19, small enough to
leave.

Dependency-order bugs in this build, in sequence: registry before hair,
degeneracy before inversion, derived block before refit, rating before the
derived block, and now the fill's rescale before the derived block. **The rule
that keeps emerging: whatever a value is computed FROM must be final before it
is computed.**

### Original decomposition, retained

Decomposed by stage, the tier-3 gap between the stored rating and the DRAWN
rating comes almost entirely from one step:

| stage | tier-3 residual (median / p90) |
|---|---|
| after the donor fill | **-0.1 / +0.3** |
| after `build_derived` | +0.9 / **+5.6** |
| after `calibrate_positions` | +1.2 / +6.1 |

The fill is exact. `build_derived` contributes **+5.6 of the +6.1** p90.
`calibrate_positions` has since been removed and accounted for only 0.5 of it.

Not opened. Logged with the decomposition so the next pass starts from the
measurement rather than the symptom.

**Correction recorded:** this residual was first attributed to
`calibrate_positions`. It causes 0.5 of 6.1. Decomposing by stage rather than
defending the first claim is what located the real step.

---

## 9. Integer rounding at the attribute boundary — one cause, three bugs

**RESOLVED.** One rounding convention now applies at the boundary where attributes become integers (`int(round(v))`, not `int(v)`). The three defensive margins added downstream were patches for it; the rescale margin is back to half a point. Invariant unchanged at 0.60 across every cohort.


Attributes are written as integers while the rating is computed from floats,
and the boundary between them has now produced three separate defects:

1. **Will Anderson Jr. 5.7 points adrift of his own attributes** — the rating
   was computed from the float dict, the file stored `int()`-truncated values.
2. **Nine rescaled players landing on 39 against a target of 40** — the solve
   hit 40.0 exactly and truncation took it below.
3. **DJ Herman gaining nearly four rating points from a +/-0.5 shift** —
   `calibrate_positions` added a fraction to twenty cells and re-rounded, and
   enough rounded up to move the rating four points.

Each was patched where it appeared. **The boundary itself has not been fixed** —
one rounding convention applied once, at the point attributes become integers,
rather than three defensive margins. Own item.

---

## 10. Draft prospects break the computed-rating invariant

**RESOLVED.** Prospects now take one real donor vector rescaled onto the slot-derived rating, and the rating is computed from the attributes -- decided LAST, after the derived block, which is what the first attempt got wrong (53 players still adrift because derived cells carry rating weight). Rookie cohort: max gap 41.46 -> 0.50, 185 over 5 -> 0.


Rostered players and free agents both hold it at **max 0.50**. The Rookie
cohort does not:

| cohort | n | median | p90 | max | >5 |
|---|---|---|---|---|---|
| rostered | 1890 | 0.25 | 0.44 | **0.50** | 0 |
| free agents | 465 | 0.24 | 0.44 | **0.50** | 0 |
| **prospects** | 278 | **8.12** | **20.85** | **41.46** | **185** |

This is not an archive convention. Three of four published files hold the
invariant for prospects as tightly as for anyone:

    2010  max 3.82  >5: 0        2017  max 4.42  >5: 0
    2013  max 1.46  >5: 0        2021  max 23.95 >5: 105

Only 2021 breaks it — a sixth piece of evidence for §1. A.J. Harris is stored
at 49 and computes to **7.5**, so the game will display a number bearing no
relation to the file's.

Prospects have their own build path (`fit_prospect_curve`) which the
stored-equals-computed ruling never reached. Not fixed: it needs the same
decision the rostered cohort got, and the draft class is a distinct deliverable.

---

## 11. The undrafted hit rate runs above its target — re-measure, do not tune

The zero-information cohort draws an 80+ ceiling at a measured archive rate of
**8.3%**. The realised rate on the 2026 build:

| | n | reached 80+ potential | rate |
|---|---|---|---|
| target (archive) | 5683 | 469 | **8.3%** |
| 2026 cohort | 54 | 8 | **14.8%** |

Inside noise — at n=54 the expected count is 4.5 with sd 2.0, so 8 is about
1.7 sd high. But the bias is also **real by construction**: the hit draw raises
potential, while a non-hit can still reach 80 through the ordinary gap draw, so
the two paths add rather than partition.

**Deliberately not tuned.** Adjusting a rate to fit a 54-player sample is
fitting to noise, which is the worse error. Re-measure on a larger cohort — a
future season with more sourceless players, or the cohort pooled across
several builds — and separate the two paths before changing the constant.

*(Ryan's independent check of the live file read n=154 for undrafted age <=24
at 8.4%, against n=54 for the strict zero-information cohort at 14.8%. The two
populations differ: his includes undrafted players WITH experience, who do not
go through the hit-rate mechanism at all. The strict cohort is the one the
mechanism acts on and the one to re-measure.)*

---

## 12. The 1986/1990 retro mods — parsed, not usable

`ROSTER-1986V1` and `ROSTER-1990` (Madden 25 retro mods) both decode: FBCHUNKS,
zlib at offset 74, key-value records anchored on `c25c33`, **identical 170-key
schema**. 1986 holds **1,679 real players**, 1990 holds 1,945 — a season this
project does not cover at all.

**Record classes** (3,111 anchors in 1986): 1,679 real, 616 blank `"0 0"`,
556 named `"."`, 235 generic `"POS #NN"`. Any share computed on 3,111 is wrong.

**163 is an unset default, not a ceiling** — it appears on 61 keys, one holds
it on every record, and Montana alone has 17 fields at it.

**Confirmed fields:** height = `c289f4 - 64` (r=0.954 against real heights, and
the thing that validates the parse). `c2bcb4` is speed-shaped — zero zeros on
the real roster, and its top values are Braziel, Hill, Cade, Minnifield, Fryar,
all CB/WR. `c2fdb2` is a **QB** field, not overall rating: its top values are
Kenney, Krieg, Esiason, Lomax. My earlier reading of it as a rating was wrong.

**Blocked on the value scale.** Dividing by 1.606 (159/99) puts the maximum at
99 but the median at 36-39, far too low for an attribute distribution. Fields
are identifiable by signature; none has been decoded into a usable 0-99 scale.

**Skin (`c2cced`) rejected** — see the precedent on thresholds fitted to famous
players. Not usable, and the 1986 faces item stays closed.

---

## 13. The registry's two blocks conflict, with no precedence defined

    faces        11,068 keys      faces_1986        2,115
    staff_faces   2,231           staff_faces_1986    438

    roster keys in both blocks: 23   ALL 23 hold different values
    staff  keys in both blocks: 46   40 hold different values

**Consumer audit — every reader of these blocks:**

| consumer | behaviour | verdict |
|---|---|---|
| `apply_registry_all.py` | selects by file year | **correct** |
| `build_2000.py` | explicit per-(team, role) map, documents the Mora father/son | **correct** |
| `build_2026.py` | reads `faces` / `staff_faces` only | **safe** — no 1986-era key can reach a 2026 build |
| `pgm3_validate.py` | preferred the 2-part block | **was wrong; fixed** — 3-part key reads the 3-part block, and keys ambiguous across blocks are refused rather than scored |

**Precedence, now recorded:** an 1986-era key reads `faces_1986` first. Where a
bare name cannot distinguish two men, the consumer refuses rather than choosing.

**NARROWED: 17 of the 23 are namesakes, 3 are aging, 3 need a ruling.**

Sorted by whether age advances with the seasons (tolerance 3 years, since these
files carry known age noise):

    NAMESAKES, no ruling needed   17   Clay Matthews, Kellen Winslow, Marion
                                       Barber, Mark Clayton, Stanley Morgan,
                                       Joe Montana, Mike Richardson, James
                                       Wilder, Eric Wright, Mickey Shuler,
                                       Ricky Williams, Aaron Brown, Eric
                                       Wilson, Mark Brown, Jan Stenerud, John
                                       Hannah, John Stallworth
    AGING, same head family        3   Reggie White 5b->5d, Ray Brown 5b->5d,
                                       Morten Andersen 1a->1c
    HEAD FAMILY CHANGED            3   Doug Flutie 1->3, Gary Anderson 4->1,
                                       Jerry Rice 5->4

**The blocks are era-specific by design, not in conflict.** All six same-man
cases carry `faces_1986` in the 1986 file and `faces` in 2004+, which is a
young face and an old face for one man. Only the three where the HEAD FAMILY
changes are questionable, since the project's rule is family constant and
variant free to age.

**Only those three need Ryan**, and Gary Anderson (4 -> 1, dark to light) is
the one that matters most.

**Jerry Rice was NOT overwritten, and the guard did not fail.** Every file
carries the era-correct face: 1986 `Head5a` at age 23, 2004 `Head4c` at 41.
The verified key `jerry rice|WR|SF` is 1986-scoped, but he was still on SF in
2000 at 37, so the gate applied a 23-year-old's face to a 37-year-old and
called it an overwrite. Gate now scopes 1986 keys to the 1986 file. **Both
verified-face checks pass; there is no drift anywhere in the 105.**

**The 40 staff conflicts are NOT reconciled.** Two values for one player is a
question about which edit was later and which was intended, and that is Ryan's
to answer. Some are certainly legitimate — the Moras are two people — and
others are probably stale. Nothing should be merged by inference.

---

## 14. This session created 21 cross-season head-family changes — CLOSED

The faces gate's `head FAMILY constant across seasons` check was right all
along, and I closed the thread around it as a tooling artifact. It is not.

Filtering that check for **same man** (age advancing with the seasons, +/-3):

    same-man family changes BEFORE this session:   3
                            NOW:                  24
    created by this session:                      21
    resolved:                                      0

**The three pre-existing are Doug Flutie, Gary Anderson and Jerry Rice** —
exactly the three identified by inspection, all 1986 -> 2000+, with Gary
Anderson cross-band at 4 -> 1.

**The 21 are mine**, from applying RFM to 2026 and to 2021 and to no other
file: Epenesa, Highsmith, Byron Murphy, Poona Ford, Elijah Wilkinson, Isaac
Seumalo, Jonah Jackson, Josh Oliver, Josh Palmer, Michael Burton, Michael
Hoecht, Michael Bandy, Morgan Fox, Nick Martin, Younghoe Koo, Kyle Peko, Corey
Levin, Austen Pleasants, Storm Norton, Gunner Olszewski, Ka'imi Fairbairn.
Fourteen are cross-band.

**I reported 19 of these at the time as "expected, and 2026 is the one that is
right."** That framing was a rationalisation: it treated a violation of the
project's own rule as an acceptable side effect, without measuring the total or
calling it a regression. The per-player accuracy gain is real; so is the
cross-season breakage, and only one of the two got reported.

**The rule assumes one source of truth per person across files.** Applying a
better source to two files of nine necessarily breaks it.

**RESOLVED. Trajectory: 3 pre-existing -> 24 after the RFM work -> 0.**

    back-applied the boundary rule to 2026        6 closed
    corrected the boundary target, family 3 -> 4  the band-flip cause
    three photo verdicts (Anderson, Williams, Cox)
    Morgan Cox 2013, a position-change case
    extended RFM to free agents                   the last 2

Fifteen within-band variant differences remain, which is the aging rule working
as intended.

**How it was caught matters more than how it was fixed.** The 19 were reported
at the time as "expected, and 2026 is the one that is right" -- a framing that
sounded like analysis and was a rationalisation. It was accepted. What exposed
it was a measurement run after a pushback on an unrelated claim, not a gate and
not a review. **A plausible explanation offered alongside a real improvement is
the hardest kind of error to catch, because both halves are true and only one
gets counted.**

---

## 15. The boundary rule, back-applied — and why it cannot be widened

The mid-tone rule (RFM skin 4-5 -> family 3) was introduced for 2021 and never
back-applied to 2026, which had been done first. Six players were therefore
routed one way in 2021 and another in 2026 from the identical source value:
Epenesa, Highsmith, Byron Murphy, Seumalo, Jonah Jackson, Josh Oliver.

Back-applied. **Cross-band same-man changes 12 -> 6; same-man total 23 -> 17.**
Light share 28.9% -> 29.3%, inside the published 27.2-35.6%.

**The wider version — route every skin-4/5 player, not only disagreements —
was MEASURED AND REFUSED.** Family 3 sits in the LIGHT band (<=3), while RFM
skin 4-5 is the light end of its DARK range. Routing every such player to
family 3 converts them from dark to light:

    file   skin 4-5   would move   light now -> after
    2017        37           34      29.8% -> 31.5%
    2021       147          125      28.1% -> 33.9%
    2026       341          340      28.9% -> 46.9%   <- against a published max of 35.6%

RFM covers 91.6% of 2026 against 44% of 2021, so the same rule has a wildly
different blast radius per file. **Applied broadly it would make nearly half
the 2026 league light.** The disagreement-scoped version is the correct one.

**This also means the boundary family is arguably wrong.** If skin 4-5 denotes
the lighter end of dark, family 4 (the lightest DARK family) is the faithful
target, not family 3. Family 3 was chosen for Fairbairn, whom Ryan called
genuinely mid-tone, and it works for a handful of hand-checked cases -- but it
flips the band, and that is why it cannot scale. Worth revisiting before the
rule is used again.

**Six cross-band cases remain, small enough for one photo pass:** Gary Anderson
(pre-existing), Kyle Williams, Morgan Cox, Corey Levin, Austen Pleasants,
Ka'imi Fairbairn.

---

## 16. The constancy check is blind to men who change position — RECORDED, NOT FIXED

`head FAMILY constant across seasons` keys on `name|position`, so a player who
moves from guard to centre is **never compared to himself**. Re-keyed on name
alone and split by whether age advances with the seasons:

    cross-band cases hidden by the position key   128
       SAME MAN, changed position                  61   <- genuine
       different men (namesakes)                   65   <- the key doing its job
       two records in one season                    2   <- ambiguous

**61 genuine cross-band flips that nothing has ever flagged.** They are
long-standing, not from this session:

    brad meester      2000:OG/fam5(dark) -> 2004-2013:C/fam1(light)
    aeneas williams   2000:CB/fam1(light) -> 2004:S/fam5(dark)
    david harris      2007-2013:MLB/fam5(dark) -> 2017:OLB/fam3(light)
    bj raji           2010:DT/fam3(light) -> 2013:DE/fam5(dark)

The 65 namesakes are why the key includes position in the first place -- Gary
Anderson's 1986 running back and kicker land in that group. **The position key
is not wrong; it is doing two jobs and only succeeding at one.** A correct
check needs identity resolution (age progression, team continuity) rather than
a composite key.

Measured, NOT fixed. 61 records across six published files is a ruling.

---

## 17. RFM was applied to the ROSTERED cohort only — CLOSED

The last two cross-band cases -- Austen Pleasants and Corey Levin -- are both
**free agents** in the file that was not corrected, and rostered in the file
that was. Both read RFM skin 2, decisively light, and their FA records still
carry family 4.

The RFM application scoped to `cohort_of(r) == 'T'` throughout. Free agents and
prospects were never touched in any file, so a man who is a free agent in one
season and rostered in another can disagree with himself. **Extended on Ryan's ruling: 4 records (2017 one, 2021 three, 2026 none).**
2026's free agents already agreed with RFM on all 364 covered. Same precedence,
same boundary handling. **Cross-band same-man changes across every cohort: 0.**


---

## 18. The archive's `stock` flag is keyed on NAME ALONE, and it poisons the era metadata

Found 2026-09-02 during the 1979 build, while following the handoff's own
instruction to "check `era_certain`". **Affects every historical build, not just
1979.** Measured, not fixed.

### The mechanism

`tools/build_archive.py:107` decides whether a pre-2000 vote is a modern "stock"
leftover:

```python
is_stock = (kind in ('season', 'span') and year and year < 2000
            and norm(p['fname'] + ' ' + p['lname']) in stock)
```

`stock` comes from `nfl2k5.stock_names()`, which is a **set of names** — no
position, no team. This is the project's most-documented recurring bug ("any
lookup keyed on name alone is a bug until it is position-aware"), applied to a
1958-2026 population where the handoff already measures an 81% cross-era
false-match rate.

Line 115 then compounds it:

```python
if year and not is_stock:
    e['years'].append(year)
```

A flagged vote never contributes to `first_seen`/`last_seen`. So a genuine
1970s player whose name recurs in the modern era gets his era window built
**only from files that do not contain him** — and `era_certain` is computed from
that window, so it reads `True`.

The comment above line 107 is correct about the intent ("a stock leftover still
describes the right man, so its SKIN vote counts. It says nothing about when he
played"). The defect is that the *test* for stock-ness cannot tell a leftover
from a namesake.

### The failure mode is a confident wrong answer, not a gap

| | |
|---|---|
| archive entries carrying at least one `stock` vote | **1,952** |
| of those, era window is empty (`first_seen` None) | 499 |
| of those, window exists and excludes the flagged year | **1,453** |
| …and `era_certain` reads **True** anyway | **1,453** |

**The 1,453 is definitional, not itself the defect** — a flagged vote cannot
feed the window by construction, so of course the window excludes it. Do not
quote it as a defect count. What makes it dangerous is that `era_certain` is
`True` on all of them: an empty window abstains, a window built from the wrong
man asserts.

Worked instances, all confirmed on their own 1979 PFR team pages:

    dd lewis|OLB        Cowboys LB       window reads 2004-2009  era_certain True
    stanley morgan|WR   Patriots WR      window reads 2021-2023  era_certain True
    ted washington|OLB  Oilers LB        window empty
    steve foley|FS      Broncos S        window empty
    william gay|DE      Lions DE         window empty

### What a position-aware key actually buys — measured

Re-derived the flag from the source `.DAT` files on `name|position`:

| | 1979-1980 file |
|---|---|
| edited players | 1,999 |
| flagged by name only (current) | 338 |
| flagged by name+position (proposed) | 279 |
| **freed** | **59** |

Against the 33 flagged men independently confirmed in the 1979 PFR stat tables:

- **29 of 33 recovered** by name+position (88%)
- **4 not recovered** — same-position cross-era namesakes: D.D. Lewis (OLB),
  Stanley Morgan (WR), Kellen Winslow (TE), plus one false match on the PFR side

**Kellen Winslow is the canonical case the handoff already names** (father TE /
Winslow II TE) and it is the proof that position cannot finish the job. Per
precedent — "a composite key cannot both exclude namesakes and follow a man who
moves" — the residual needs identity resolution (birth year, team continuity),
not a wider key.

The 33 is a **floor**: PFR stat tables list only the 1,144 players who recorded
a stat in 1979, so linemen and backups are invisible to that test. The
position-aware re-test against the full ultimate70s rosters is owed, per Ryan's
ruling.

### Ruling (Ryan, 2026-09-02) and what a build should do meanwhile

**Do not repair the archive mid-build.** For a historical build, take era
membership from **the presence of a season vote from that year's file**, not
from `first_seen`/`last_seen`/`era_certain`. The vote is a direct observation;
the window is a derived field with a known defect on exactly this cohort.

    # correct for a 1979 build
    in_era = any(v['src'] == '1979-1980' for v in entry['votes'])
    # NOT: entry['era_certain'] and entry['first_seen'] <= 1979 <= entry['last_seen']

When this is picked up: fix `stock_names()` to key on `name|position`, rebuild,
and re-measure the residual. **Rebuilding changes era metadata for every
pre-2000 file**, so it is a whole-archive pass with its own review, not a patch.

*Provenance: `stock_names()` was written 2026-09-01 to strip 2004 leftovers out
of retro files, which it does correctly. Nobody checked what it did to era
metadata. Recorded per the standing rule that a deliberate divergence carries
its reason beside it.*

### Two further copies of the defective instruction

`era_certain` is computed as `bool(e['years'])` (`build_archive.py:129`) — it
means "at least one non-stock vote exists", **not** "the era is known". Three
documents told a build session to trust it. Corrected 2026-09-02 in
`PGM3_PROJECT_HANDOFF.md` and `PGM3_TASK_build_2026.md`.

**The third copy cannot be corrected without the rebuild.** The same instruction
is baked into `_README` *inside* `reference/PGM3_PLAYER_ARCHIVE.json`
(`build_archive.py:153-154`): *"Check first_seen/last_seen against the season
being built - but only where era_certain is true."* A session reading the
archive directly gets the wrong instruction from the artifact itself, with no
way to know a doc supersedes it. **Fix it in the same pass that fixes
`stock_names()`.**

---

## 19. The 1986 mod is the ANCESTOR of our 1986 file, not an era source for it

Evaluated 2026-09-02 against audit item 7, which says 1986's broken
computed-rating invariant "needs an era source with machine-readable attribute
data, and none exists." `1986_Roster_Mod_v1.0.ros` was offered as that source.

**It is not one. It is where our 1986 file came from.**

| | |
|---|---|
| mod rostered | **1,746** |
| `PGMRoster_1986.json` rostered | **1,746** |
| shared names | **1,734** |
| in published only / mod only | 1 / 1 |

`1986v1.0 - raidermike.ros` is **byte-identical** to it — md5
`f7038e9711f1d237a3a1b56fc8feade5` for both. One mod under two names; the second
copy is not kept.

**So agreement with it is lineage, not corroboration** — the standing rule that
files descending from each other share their errors. It cannot say what 1986
quality truly was.

### What it CAN settle, and does

Our rating and our attributes both descend from this file **through different
transformations**: the rating through a per-position rescale (median 77 -> 71),
the attributes through quantile mapping plus a bounded refit (speed 75 -> 83,
passBlock 57 -> 75). Both halves had equal opportunity to preserve the source's
ordering. **One did and one did not.**

Correlation of the mod's `POVR` against each half:

| cohort | vs our STORED rating | vs our COMPUTED-from-attributes |
|---|---|---|
| all 1,745 shared | **+0.9329** | +0.8598 |
| the 630 invariant-breakers | **+0.9216** | +0.8156 |

Unanimous per position on the breaking subset, every one with n>=15:

    RB  +0.977 / +0.698     OLB +0.982 / +0.931     CB  +0.994 / +0.902
    DE  +0.993 / +0.941     OT  +0.984 / +0.959     S   +0.976 / +0.891
    WR  +0.988 / +0.912     MLB +0.993 / +0.910     DT  +0.990 / +0.930

**The stored rating is the faithful half; the attributes are the drifted half.**
Item 7 ruled that on other grounds — that the ratings already match the
published distribution at every quantile and storing the computed value would
move 506 ratings by more than 10. This is independent support for the same
conclusion from the pipeline's own ancestry.

**It is NOT a licence to repair 1986.** The claim is only "our rating stayed
closer to what we built from", not "our rating is right". A true repair still
needs a source outside our own lineage, and this is not one. **Item 7's
exception stands.**

### What the file IS good for

**Its `COCH` table is genuinely 1986** — and unlike `NFL79.ros`, which wrapped 28
real head coaches around ~190 records from 2007-08, all four coaches per team
are period-correct:

    CHI  Ditka, Kazor, Hughes, Tobin        NYG  Belichick, Crennel, Erhardt, Parcells
    PIT  Dungy, Moore, Hoak, Noll           SF   Holmgren, vonAppen, Seifert, Walsh
    DAL  Hackett, Lowry, Landry, Stautner   GB   Jauron, Coughlin, Gregg, Modzelewski

128 real 1986 coaches, four per team. (The 53-man pool at TGID 1023 is modern —
Heimerdinger, Donatell, Chris Palmer, Zauner — and is junk.) Note the file
spells Belichick "B.Beilicheck".

**Contamination is essentially nil**: exactly one player on its real teams is
absent from our published file (Ed "Too Tall" Jones, 35, who did play in 1986).

**`PSKI` is dead at 63% on the middle value**, so it does not reopen the 1986
appearance problem. That stays closed.

---

## 20. The 1986 mod's COCH table — 128 period-correct coaches, and the first independent check on `PGMStaff_1986.json`

Separate from item 19, which rejected the same file as a *player* source.
**This is a different question and the answer is different.**

`1986_Roster_Mod_v1.0.ros` carries **four coaches per team across all 32 slots,
all period-correct**, unlike `NFL79.ros` which wrapped 28 real head coaches
around ~190 records from 2007-08:

    CHI  Ditka, Kazor, Hughes, Tobin          NYG  Belichick, Crennel, Erhardt, Parcells
    PIT  Dungy, Moore, Hoak, Noll             SF   Holmgren, vonAppen, Seifert, Walsh
    DAL  Hackett, Lowry, Landry, Stautner     GB   Jauron, Coughlin, Gregg, Modzelewski
    MIA  Westhoff, Shula, Studley, Sandusky

**`PGMStaff_1986.json` has never had an independent check.** This is one. The
file spells Belichick **"B.Beilicheck"**, so any join must be on surname +
initial, not exact match.

The 53-record pool at `TGID 1023` is modern (Heimerdinger, Donatell, Chris
Palmer, Zauner) and is junk. `CSKI` reads 14% dark against a real coaching
population of ~21% and a registry figure of 24.1% — **do not use it for coach
skin.**

**Not applied. 1986 is published.** Recorded so the check is available when 1986
is next opened.

---

## 21. Two more historical `.ros` files — one real find, one closed door

Both screened, lineage-checked first, and neither is a copy of anything held.
Cross-file identical-value rates against every other file we hold run 4-28% on
`POVR`, against 98.4% for the two 1979 files that ARE one roster.

### `1983-SB-XVIII.ros` — the FIRST usable historical `.ros` skin source

1,974 players, 1,641 rostered. **`PSKI` passes the screen** at 14.3% on the
middle value (rostered cohort) against a 28% threshold. Anchor-tested against
1,202 players carrying an unanimous multi-source label in the 2K5 archive:

    PSKI 0   n=488    9.6% dark
    PSKI 1   n=150   56.7% dark      <- the documented abstain value
    PSKI 2   n=564   96.8% dark

Clean monotone separation. **Rule: 0 = light, 2 = dark, 1 abstains** — that
covers 1,052 of 1,202 at ~93.5% accuracy. A two-way split at `PSKI >= 1` gives
89.2%.

For comparison on the same anchor method: **`NFL79.ros` reaches only 83.9%** with
the same abstain rule (its ordering is real but weaker — 0/1/2/3 at
17.5/46.2/83.8/93.5% dark), and **the 1986 mod is dead** at 65.3% with 82.4% of
the file on the middle value. The 2K5 archive's 93.4% remains the better source
for 1979, so this changes nothing there.

**Incremental value is modest and should not be oversold.** Of its 1,630
rostered names, 74.2% already carry a strong archive label. It could add a
usable vote for 421, of which 233 are absent from the archive entirely. Against
the 1986 file's open appearance gap (backlog item 0):

    1986 rostered    460 uncovered ->  99 the 1983 file could vote for
    1986 Rookie      749 uncovered ->   0
    1986 Free Agent   48 uncovered ->  13

**112 of 1,257, about 9%.** The Rookie cohort gets nothing, because 1986's
prospect pool is the 1987-1990 draft classes who were not in the league in 1983.

### `1990-SB-XXV.ros` — a real 1990 roster whose skin field is dead

12,075 players across 227 team slots. **It is not a season roster; it is a
Madden all-time collection**: 32 base teams plus **146 historical season-teams
spanning 1957-2002**, including five 1979 teams and three 1986 teams.

**Those historical teams are worthless as data.** They are anonymised for
licensing — forename holds the position and surname holds the jersey number
(`"QB" "#5"`, `"HB" "#30"`), the numbers do not match the real rosters, and the
ratings are inflated (the 1979 Dallas line reads 96-99 straight across). 7,684
of the 12,075 records are nameless in this way. **The five 1979 teams cannot
cross-validate `NFL79.ros`: there are no names to join on.**

**The 32 base teams ARE a genuine 1990 season roster**, 1,730 players, verified
by cohort: Barry Sanders 22 / `PYRP` 1, Deion Sanders 23 / 1, Derrick Thomas
23 / 1, Thurman Thomas 24 / 2, Montana 34, Rice 28, Elway 30, Marino 29, Warren
Moon in the Oilers slot.

**But `PSKI` is 99.6% on a single value — completely dead.**

**This closes the route backlog item 0 was hoping for.** That item measures a
1990 export as covering 514 of the 1,260 unsourced 1986 names and concludes "a
1990 or 1991 build closes roughly 40% of the gap as a side effect." **This 1990
file cannot do that.** It is a usable 1990 *attribute and identity* source and
not a skin source. Item 0's estimate should be read as conditional on finding a
1990 file whose skin field survives, which this one does not.

---

## 22. The `.mdc` draft classes — a second route into item 0, on the RATINGS side

30 files, 1987-2016, "Generated by Nza's Editor. MDC File Version: 1".
Tab-separated, 77 fields, cached in `sources/mdc_draft_classes/`.

### Lineage and shape, checked first

**29 distinct of 30. `2009.mdc` is a byte-identical copy of `2008.mdc`**
(md5 `c4c337a39b49b59cf7343554bf4e6ba4`) — there is no real 2009 class here.
Consecutive-year name overlap is 0-5 everywhere else, so the rest are genuinely
different classes. `2012`/`2013` share 24 names and are worth a look before use.

**Every file is exactly 257 rows (1994 has 254).** That is a container cap, not
a class size — the 1987 draft ran 12 rounds and 335 selections. **These classes
are truncated, not complete.**

### It does NOT carry a rating

No column behaves like an overall. Tested every numeric column against the
attribute block (cols 8-24): the highest mean |r| is 0.473, and that column is
itself an attribute. **The ratings half of the prospect gap is untouched by this
source.**

### It DOES carry real attributes, and ours do not

The decisive measurement, on the 246 of 257 1987 names that match the 1986
Rookie cohort:

| | mean abs r against log(draft pick) |
|---|---|
| **our 1986 prospect attributes** | **0.440** — intelligence −0.843, jumping −0.729, agility −0.701 |
| **the `.mdc` attribute columns** | **0.098**, max 0.312 |

**Our prospect attributes are a function of where the player was picked.** The
`.mdc` attributes are not. Its speed column carries textbook positional
structure — WR 87, CB 88, RB 72, QB 54, DT 52, C 26, K 25.

The same defect shows in the rating directly: **our 1986 prospect `rating`
correlates −0.937 with `draftNum`.** That is the documented "derived from draft
position" fallback, now quantified.

### Coverage of the cohort the 1983 file could not reach at all

    1987.mdc  246 of the 1986 Rookie cohort      cumulative 246
    1988.mdc  244                                cumulative 490
    1989.mdc  243                                cumulative 730
    1990.mdc  206                                cumulative 934

**934 of 1,323 = 70.6%.** Against the 1983 skin file's **0 of 749** on the same
cohort. Different half of the problem, far larger reach.

### Skin: collapsed, as suspected

Column 47 reads `{0: 185, 1: 11, 2: 50, 4: 11}` — **72.0% on the dominant
value**, the same shape that made the 2023 file unusable. Columns 46, 48, 49,
50, 52, 57, 58 all carry dominant defaults too. **No usable skin field.** This
source is attributes and identity only.

### Disposition

**Not applied. 1986 is published.** But this is the first source that addresses
the prospect cohort's *attribute* defect, and item 0's remaining Rookie gap is
the largest single block of unsourced data in the archive. The 30 files also
cover every published season's draft classes, so the same test should be run for
2000, 2004, 2007, 2010, 2013, 2017 and 2021 before any of them is reopened.

---

## 23. The prospect defect, measured across every published season

Generalisation of item 22, run 2026-09-02. **Report only — no published file
touched.** Two numbers per season: how far the prospect cohort's own fields are
a function of draft slot, and how much of that cohort the `.mdc` classes reach.

| file | prospects | `rating` r vs log(pick) | attributes mean abs r | mdc coverage | classes available |
|---|---|---|---|---|---|
| 1986 | 1,334 | **−0.899** | **0.698** | 70.6% | 1987-1990 |
| 2000 | 1,024 | −0.611 | 0.402 | **81.7%** | 2001-2004 |
| 2004 | 1,017 | −0.646 | 0.219 | 80.7% | 2005-2008 |
| 2007 | 1,017 | −0.681 | 0.237 | 53.5% | 2008, 2010, 2011 — **2009 absent** |
| 2010 | 1,017 | −0.857 | 0.199 | 52.4% | 2011-2014 |
| 2013 | 1,018 | −0.785 | 0.412 | 62.4% | 2014-2016 — 2017 not in the set |
| 2017 | 1,024 | −0.724 | 0.206 | **0%** | none |
| 2021 | 1,033 | **−0.899** | 0.452 | **0%** | none |
| 2026 | 278 | −0.778 | 0.182 | **0%** | none |

Class mapping was measured by name-matching, not assumed from the file year.

### Finding 1 — the RATING defect is archive-wide, not historical

**Every one of the nine files** carries a prospect `rating` between **−0.611 and
−0.899** against log draft pick. The newer files are no different: 2017 −0.724,
2021 −0.899, 2026 −0.778. Prospect rating is a function of where the player was
picked in every file this project has ever shipped.

**The `.mdc` set does not fix this** — it carries no overall column (item 22).

### Finding 2 — the ATTRIBUTE defect is NOT archive-wide, and 1986 is the outlier

Mean abs r across 17 attributes: **1986 at 0.698** stands alone. 2021 (0.452),
2013 (0.412) and 2000 (0.402) are moderate; 2004, 2007, 2010, 2017 and 2026 sit
at 0.18-0.24, which is consistent with attributes genuinely sourced from a
Madden export rather than derived from slot.

### Finding 3 — 2021 breaks the "newer files were built better" expectation

2017 (0.206) and 2026 (0.182) behave as expected. **2021 does not**: at 0.452 it
is worse than 2004, 2007 and 2010, with a rating correlation of −0.899 that ties
1986 for the worst in the archive. That is consistent with audit item 1b, which
records 2021 as the least-reviewed file and the only published file whose
prospects break the computed-rating invariant (105 records). **Do not treat
recency as evidence of quality here.**

### The 2009 gap belongs to 2007

`2009.mdc` is a byte-identical copy of `2008.mdc`, so the real 2009 class does
not exist in the set. **2007 is the file that needs it** — its cohort spans
2008-2011. Coverage from the three real classes is 544 of 1,017 = **53.5%**, and
the 473-record gap is dominated by 2009. No amount of matching improves this
without a genuine 2009 class.

### The 257-row container — corrected, and it only bites on 1986

An earlier note said the missing rows were "late-round picks" cut at 257.
**Measured, that is wrong about the mechanism**: matched players span pick 1 to
**335**, so the file is a 257-row *sample* of the class, not a truncation at
pick 257.

| class | real size (from matched picks) | 257 rows cover |
|---|---|---|
| 1987 | ~335 | 77% |
| 1988 | ~329 | 78% |
| 1989 | ~334 | 77% |
| 1990 | ~329 | 78% |
| 2001, 2004, 2008, 2014, 2016 | ~246-256 | **100-104%** |

**The 12-round drafts of the 1980s exceed the container; the 7-round drafts from
2001 on do not.** So the cap costs 1986 about 78 men per class and costs every
other file nothing — their coverage gaps are match failures, not truncation.

**The direction of the original concern still holds for 1986**: its uncovered
prospects have a median draft pick of **243 against 129 for the covered**, p75
at 293. The men the fix would not reach are the late picks — exactly the
population a slot-derived fill serves worst.

### Where a fix would actually pay

Ranked by slot-dependence times coverage:

    1986   attr 0.698  coverage 70.6%   product 0.493
    2000   attr 0.402  coverage 81.7%   product 0.329
    2013   attr 0.412  coverage 62.4%   product 0.257
    2004   attr 0.219  coverage 80.7%   product 0.177   attributes already sourced
    2007   attr 0.237  coverage 53.5%   product 0.127   attributes already sourced
    2010   attr 0.199  coverage 52.4%   product 0.104   attributes already sourced
    2017 / 2021 / 2026                  no mdc coverage at all

**Three candidates: 1986, 2000, 2013.** 2021 has the defect and no source.

---

## 24. 2026 drafted rookies are inflated — the rookie fix reached the undrafted only

Reader report via Ryan: **Fernando Mendoza reads 84 and has never taken an NFL
snap.** Investigated 2026-09-02. **Report only — nothing changed. 2026 is
published.**

Cohort: rostered players with `draftSeason` 2026 (the game clock's current
season), i.e. first-year players on a team rather than in the prospect pool.
**304 records: 215 drafted, 89 undrafted.**

### The undrafted group is fine. The drafted group is not.

    2026 undrafted first-year   median 63   mean 62.8   max 78    >=80  0.0%
    2026 drafted first-year     median 73   mean 73.0   max 88    >=80 15.8%

Against every other published file's first-year rostered cohort:

| file | drafted med | drafted >=80 | undrafted med |
|---|---|---|---|
| 1986 | 66 | 6.8% | 62 |
| 2000 | 65 | 3.8% | 61 |
| 2004 | 69 | 11.8% | 62 |
| 2007 | 66 | 4.4% | 59 |
| 2010 | 67 | 4.8% | 59 |
| 2013 | 67 | 3.4% | 62 |
| 2017 | 71 | 3.2% | 63 |
| 2021 | 68 | 10.2% | 59.5 |
| **2026** | **73** | **15.8%** | 63 |

**A drafted/undrafted gap is normal** — every file has one, 4 to 8 points. 2026's
is 10, the largest but not out of family. **The anomaly is the level of the
drafted group**: highest median in the archive and the highest `>=80` share by a
clear margin.

### The inflation is OURS, not the source's

    Madden 27 source, our drafted cohort   median 71.0   >=80   2.4%
    our file, same players                 median 73.0   >=80  16.0%
    Madden 27 whole file                   median 71.0   >=80  16.3%
    Madden 27 rows with YearsPro = 0       median 68.0   >=80   1.2%

**`>=80` goes from 2.4% in the source to 16.0% in our file — a 6.7x increase —
and lands almost exactly on the whole-file rate of 16.3%.** The source knows
these are rookies and rates them low within its own population; the per-position
quantile rescale mapped them onto the general distribution and erased that.

It is not a pass-through: only 6.6% of drafted rookie ratings are identical to
the source overall, median delta +2. The rescale ran; it ran against the wrong
target population.

**This is the shape Ryan predicted.** The undrafted group sits at median 63 with
0% at `>=80`, squarely inside the archive band — the age-conditioned draw reached
them. The drafted group did not get it.

### A second, independent defect: no growth headroom

**85 of 215 drafted first-year rookies have `rating == potential`** — 39.5%,
spread evenly by round (13/32 in round 1, 13/32 in round 2, 11/32 in round 3).

    Mendoza      pick  1   rating 84  potential 84    no headroom at all
    Peter Woods  pick 29   rating 87  potential 95    correct shape

Against the archive: 2017 0.0%, 2021 0.0%, 2010 1.1%, 2007 3.3%, 2000 5.9%,
2004 8.0%, 1986 11.2%, **2013 50.0%**. So 2026 and 2013 are the two outliers, and
**2013 is worse** — that file should be checked in the same pass.

A rookie who cannot develop is arguably the more visible problem in play than one
rated two points high, and the #1 overall pick having zero headroom is the worst
single instance.

### What a fix would need

Both defects are in the same cohort but are not the same bug: one is a rescale
target, the other a `potential` draw. **Neither should be repaired without
re-running the gates on 2026 and re-checking 2013's 50%**, and this would be the
fifth write to 2026 today.

### 24b. The potential defect: 2013 and 2026 share a symptom, not a cause

Extended 2026-09-02 on Ryan's instruction to measure `rating == potential` across
every file rather than the two that surfaced. **Report only.**

**First correction: the raw rate is not the measurement.** `rating == potential`
runs 9.5-52.5% in the rostered cohort of every published file, including the ones
called clean. That is *correct* — a 33-year-old has no growth left. The defect
only exists conditioned on experience.

**The archive has a designed curve.** Median headroom by years pro
(2026 − `draftSeason`), rostered:

    file      yr0   yr1   yr2   yr3   yr4   yr6   yr8  yr12   max
    1986        4     4     3     2     1     0     0     0    32
    2000        5     5     5     4     3     1     1     0    14
    2004        4     3     3     3     3     2     1     0    43
    2007        5     4     3     2     1     0     0     0    30
    2010        4     4     3     2     1     0     0     0    46
    2017        6     4     2     0     0     0     0     0    28
    2021        6     6     7     7     2     2     2     4    10
    2013        0     0     0     0     0     1     0     0     6
    2026        2     3     2     2     2     2     2     1    32

**Six files decay 4-6 at year zero to 0 by year 6-8. Three do not.**

### The clean files: 2017 by design, 2021 by accident

Both read 0.0% zero-headroom among first-year drafted players, but for opposite
reasons. **2017 has a real curve** — 6 at year 0 falling to 0 by year 3, max 20.
**2021 has a flat one** — ~6 at year 0 and still 4 at year 12, capped at max 10.
It gives twelve-year veterans growth they should not have. **Copy 2017's shape,
not 2021's.**

### 2013 and 2026 are different bugs

| | 2013 | 2026 | 2017 |
|---|---|---|---|
| drafted first-year n | 178 | 215 | 190 |
| rating median | **67 (normal)** | **73 (inflated)** | 71 |
| rating >= 80 | **3.4% (normal)** | **15.8%** | 3.2% |
| headroom median | 0 | 2 | 6 |
| **headroom max, whole file** | **6** | 32 | 28 |
| rating == potential | 50.0% | 39.5% | 0.0% |
| growthType invariant holds | 100% | 100% | 100% |

**2013 is a ceiling.** Not one of its 1,903 rostered players has more than **6
points** of headroom. Its ratings are entirely normal. The potential field was
compressed against the rating, so nobody in the file can develop much and half
the rookies cannot develop at all. One cause, and it is not 2026's.

**2026 is an unconditioned draw plus the rescale inflation.** Its headroom
reaches 32, so nothing is capped — the distribution simply has no age term, and
sits flat at 2 from rookies to twelve-year veterans. On top of that its drafted
rookies are rated 73 against a source median of 71 and an archive band of 65-71.

**Two files, one number in common, two causes. They need separate fixes.**

### The constraint any fix must respect

**`growthType` holds its invariant at 100% in all three files** — positive values
sum to exactly `(potential − rating) × 50`. So potential cannot be moved without
rebuilding `growthType` in the same pass. This is the documented failure that
broke five files once already: a `potential` rebuild shipped without the
`growthType` that depends on it, and every individual check passed because both
fields were separately plausible.

---

## 25. The per-position quantile map discards the source's spread — and it is a defect, not a symptom

Opened 2026-09-02 from a reader question about QB overalls. **Report only. No
published file touched.** Every figure below was reproduced by the master
session or comes from one named artifact.

### The symptom, reproduced to the point

    QB speed        min   p25   median   p75   max   p5-95
    Madden 27        69    78      83     86    95      26
    our 2026 file    36    66      78     84    99      63     stretch 2.42x

    Kirk Cousins  madden 69 ours 36 (-33)    Andy Dalton  73 -> 48 (-25)
    Cooper Rush   73 -> 48 (-25)             Jared Goff   74 -> 52 (-22)

### Q1 — QB-only, or everywhere?  EVERYWHERE

188 position x attribute cells, p5-p95 width ratio file/source, 2026 rostered:

    stretch >= 2.0x : 87 of 188      median 1.93x      compressed (<=0.8x): 1
    worst attributes by median stretch: ballSecurity 3.36x, stamina 2.79x,
    speed 2.41x, burst 2.15x, releaseLine 2.12x, passBlock 2.10x, power 2.00x

Stamina is worse than speed. S and CB stamina floors drop by **-78 and -79
points** (source min 80 / 81 -> file min 2). The low tail is a smear across 19
values and 13 positions — a stretch, not a fill block.

### Q2 — where did the wide target come from?  THE MAP, NOT A REFERENCE FILE

**First answer given was wrong and is retracted.** The initial read blamed 2021,
because 2021 stretches its own source 1.69x and sits in the six-file union
`MODERN_REFS`. Measured, dropping 2021 from the pool changes the pooled target
width by a **median 1.00x** across all 188 cells — QB speed is 53-93 with or
without it. (2021 does own one cell: S stamina narrows 0.63x without it.)

The width is intrinsic to the construction. `fit_quantile_targets` POOLS six
files into one sorted list per (position, attribute); `quantile_map` takes only
the source's RANK and hands rank 0 to the pool's absolute minimum. Level from
the pool, order from Madden — **spread from neither**. Any union of files with
different populations is wider than any one source, so the source is always
stretched to fill it. The docstring's own tie-collapse warning is the other
half: 85 QBs carry only 23 distinct source speeds, so blocks of 4-8 QBs at
source 75/76/77/78 land on 53/59/63/66 — a 3-point source band fanned to 13.

Which files preserve their own source width (all cells, median): 2004 1.00x,
2007 1.05x, 2013 1.14x, 2017 1.17x, **2021 1.69x, 2026 1.93x**. The two newest
files are the defective ones, and 2013 is clean on speed (QB min 63; its only
stretched cells are stamina, which is the already-open fill item 0j).

### Why it reaches the overall — and why that is 2026-specific

`|stored rating - computed from attributes|` median 0.25, within 1 on 99.6% of
2026 rostered. **The stored rating IS the attribute-computed overall** (the
item-7 fix). So stretched speed -> low computed overall -> stored rating.
Cousins 58 is exactly what weights.json produces from speed 36.

Order damage, Spearman of our rating vs Madden overall, position-aware join:
QB 0.842, RB 0.750, DT 0.786, K 0.736, P 0.426; best S 0.926, WR 0.917.
Worst displacements (Madden rank -> ours, 0 = worst): Cousins 53 -> 1 of 85,
Patrick Ricard 86 -> 3 of 112, Tutu Atwell 102 -> 22 of 190. **16.8% of
players shift by >= 20% of their position's rank range, and middle-of-band
players shift MORE than tail players (0.130 vs 0.079)** — the tie-collapse
signature, not just pooled tails.

**2021 has the attribute stretch but NOT the order damage** — Spearman 0.986 at
QB, 0.89-0.98 elsewhere — because its rating was ranked from source POVR and
its attributes were stretched afterwards. It also holds the invariant (median
0.18). Consequence: **a 2021 fix must hold rating fixed and refit attributes to
it**; a 2026 fix rewrites rating.

### Q3 — what does correcting it do?  Two constructions, two artifacts

**Candidate 1 — spread-preserving map** (level = pooled median, width = the
source's own). Written to `/tmp/scratch_2026_spreadfix.json` and gated:

- QB speed floor 36 -> 65, S/CB stamina floor 2 -> 83/81. The absurd values go.
- Cousins 58 -> 70, Dalton 59 -> 69, Rush 62 -> 66, Goff 79 -> 82 (Madden 73/71/65/88).
- **MAE vs Madden improves at 10 of 15 positions; worsens at OT (+2.1), OG, QB, TE.**
  Spearman improves at 13 of 15.
- **Moves 1,277 ratings; forces `potential` up for 520 of them, and 142 of those
  are >= 6-year veterans** — manufacturing the exact headroom shape item 24b
  calls a defect in 2021. Not shippable as written for that reason alone.
- **Gate-neutral**: the published 2026 ALREADY fails `cross-year medians by
  cohort` against 2021/2017/2013 on `[Rookie] injuryProne 47 vs 31`, and the
  scratch file fails on the identical row with identical numbers. The fix
  neither causes nor cures it.
- **Barely touches item 24**: drafted-rookie >= 80 goes 12.3% -> 10.6% on the
  gated artifact. (An earlier simulation said 3.4%; the difference is 7 rookies
  sitting in [79, 80) and rounding — the stored rating is authoritative.)

**Candidate 2 — same map plus a per-position LEVEL anchor to Madden's median**
(simulated, not gated; no potential forcing applied):

    pos   MAE now   spread-only   spread+level     med(ours-madden)
    QB      5.6        5.1            3.2                 0
    OT      4.6        4.2            2.1                 0
    OG      4.5        3.6            2.0                 0
    RB      5.6        5.8            3.4                 0
    S       3.0        1.4            1.4                -1
    TE      3.8        4.1            3.9                 0    <- the one that worsens

**Improves MAE at 14 of 15 positions**, Spearman at 13 of 15, residual median
0 or +-1 everywhere. Cousins 58 -> 65, Dalton 59 -> 65. **Goff 79 -> 78 against
Madden 88** — anchoring the QB level down costs the good QBs. The middle ground
exists; it is not free.

The two constructions are NOT interchangeable and the write-up must not blend
their numbers: candidate 1's figures come from a gated file with potential
forced; candidate 2's from a simulation without it.

### The four defects pending on 2026, and how they interact

| defect | item | mechanism | touched by the spread fix? |
|---|---|---|---|
| drafted rookies rated ~73, >=80 at 15.8% | 24 | rescale ran against the whole-file population | **barely** (12.3 -> 10.6%) — separate target-population fix |
| 39.5% of drafted rookies with zero headroom | 24b | potential draw has no age term | **made worse** if potential is force-clamped (520 forced, 142 veterans) |
| attributes stretched 1.93x, order damage | 25 | rank-only map onto a pooled union | this |
| prospect injuryProne median 47 vs archive 28-34 | NEW | not investigated | no — and it is what the gate is currently failing on |

**Sequencing that follows from the table:** the potential fix (24b, the 2017
curve) must run AFTER the attribute fix and BEFORE any clamp, or the clamp
manufactures veteran headroom. The rookie rescale (24) is a separate target and
runs on its own. One write, in that order. And 2013 needs none of this — its
open item is the stamina fill.

### Three corrections to earlier statements, recorded

- *"The wide target came from 2021."* Wrong — median 1.00x without it.
- *"This fix does not address the rookie inflation"* then *"it does, 10.1 -> 3.4%."*
  Both wrong; the gated artifact says 12.3 -> 10.6%. Threshold rounding.
- *"MAE improves at 12 of 15."* That was the simulation; the gated file is 10 of
  15, with OT worse by 2.1.

Each was caught by re-running against the artifact rather than the simulation.
**Quote the gated file, never the simulation, and say which one you are quoting.**

### 25b. Two more on 2026 before the one write — `decisions` is a source-side inversion, `injuryProne` is promoted to pending

**`decisions` for offensive positions.** A commenter flagged QB; measured, 2026
is the only file where rookie QB `decisions` exceeds veteran (84 vs 71). The
other eight run rookie 5-18 points BELOW veteran. **The inversion is in the
source, not the map**: Madden's `PlayRecognitionRating` for QBs reads rookie 26
/ veteran 18, `r(source, years pro) = -0.362`, and ours tracks it at +0.857.
It is a DEFENSIVE field — DE/DT/MLB/CB/S carry 70-86 with `r = +0.42 to +0.69`
— and for offense it is unpopulated noise (18-40) that happens to run downhill
with age. Five positions are inverted at the source (QB, RB, WR, TE, C; OT/OG
flat), and the pooled-target map stretched that noise into confident curves.

The archive's own QB curve, eight normal files pooled: **66 / 72 / 70 / 76 / 78
/ 80** by years pro 0 / 1 / 2 / 3-5 / 6-9 / 10+. 2026's rookie QB at 84 sits
at the 10+ median. That curve is the only non-Madden target for a draw.
**Needs a ruling**: draw offensive `decisions` from the per-position archive
curve, or leave and log. Overall impact is +2.0 at QB; the harm is in play.

**`injuryProne` for prospects** — promoted from a note to pending, per Ryan.
Published 2026 already fails `cross-year medians` on it (47 vs 31). **Root cause
measured: it is NOT a missed inversion.** Rostered and free agents read
`r = -0.946 / -0.945` against Madden's `InjuryRating` — inverted as documented.
Prospects have **2 of 278** in the source at all; their 47 is a no-source draw
filled at the rostered level (~49) instead of the rookie level the archive holds
(28-34, target ~34). Same family as item 24: a cohort drawn against the wrong
population. Fix is a re-draw of prospect `injuryProne` to ~34. **Needs a
ruling; OFF in the tool.**


### 25c. The one write, built and gated — `tools/fix_2026_spread_potential.py`

Scratch-targeted by default; writes `PGMRoster_2026.json` only when told to.
Two negative tests (empty weights must fail; a tampered `growthType` must be
detectable) both fail on purpose. **Published file untouched throughout — asserted.**

**Stages, in the order the interaction table requires:** attributes (candidate 1,
spread-preserving, no clamp) → rating recomputed → **rookies re-rescaled against a
first-year target WITH an attribute refit** (so the invariant holds) → potential =
rating + 2017's bucket median → growthType rebuilt. Rookies run *before* potential;
the first version ran them after and the two stages fought (rookie headroom 10).

**Four defects in my own build, all caught by measuring the gated file, all fixed:**
a vacuous negative test (`W or load_weights()` reloaded the real table on `{}`);
growthType gated on a running count (432 untouched players rewritten); rookie
rescale without refit (invariant fell to 89.4%); potential drawn at random from
right-tailed buckets (rookie headroom 12, 31 veterans gained >4).

**Two guards tried and REMOVED, with the measurement that removed them.** An
"authored headroom survives" guard kept 117 veterans above 4 and Goff at 88.
Measured: published veteran headroom correlates **+0.044** with (Madden overall −
our rating) and potential **+0.956** with our own rating — it is rating plus
noise, the 24b draw's tail, and Goff's 88 = Madden 88 is one of **3 exact matches
in 117**. A `max()` guard for under-6s preserved the same tail (published p90 7-8
at every age) and re-opened the stage fight. **One rule, no guard.**

**The gated artifact** (`/tmp/scratch_2026_onewrite.json`), every figure from it:
headroom medians **6/4/2/0/0/0/0/0/0 — 2017's exactly**; veterans 6+ over 4:
**0/480** (2017: 2); rookies median **65**, ≥80 **6.0%**, zero-headroom **0.0%**,
headroom **6**; growthType 1890/1890; |stored−computed| within 1 on 99.9%;
QB speed floor 36→54 (p5 52→68), S stamina p5 54→85; Cousins 58→67, Dalton
59→66, **Goff 79→82 with potential 88→82**. Gate: fails the identical pre-existing
`[Rookie] injuryProne 47 vs 31` row and nothing else.

**Costs, stated:** the young p90 is flattened to the median (**6/4/2/0 vs 2017's
12/10/8/4**) because the ruling named the curve and there is no ruling on spread;
**1,157 potentials lowered**, 827 of 1,410 under-6s, median drop 4; Goff 88→82;
MAE vs Madden worsens at a minority of positions (WR/TE/RB) — the "level from the
pool" residual Ryan accepted as legitimate disagreement.

**Rulings needed before the write:**
1. **The young tail** — accept the median-only curve, or restore spread (2017's
   p90) by a rank-preserved draw?
2. **The unjoined 398** (21%, no unique name+position in Madden 27; 28 with
   stamina <40): a p5 floor from the fixed position would touch 314 records /
   909 cells and lift stamina min 2→62. A floor, not a map. OFF until ruled.
3. **Offensive `decisions`** (25b): draw from the archive curve, or leave and log.
4. **Prospect `injuryProne`** (25b): re-draw to ~34, or leave.

### 25d. QB level, the full re-measure, and what the baseline claim actually was

**Ruled:** stretch fix everywhere, quarterback handled separately — close QB overall
to Madden's as far as the attributes allow, nothing outside the source range, a
stated per-attribute cap, spread across fields, residual reported. Sequence:
attributes → potential → rookies → decisions → injuryProne → QB level last.

**One thing the sequence cannot hold literally, and how it is honoured:**
`potential` is a function of `rating`, so it is re-derived after *every* stage
that moves rating (rookies, decisions, QB level), not run once. `growthType`
follows it each time. That is the rule below.

**The cap, measured on scratch builds before anything was applied:**

    cap   QB MAE 5.6 ->   median |gap|   Spearman 0.842 ->   Goff (Madden 88)
     8          1.1            0.5            0.984           79 -> 87 / pot 87
    10          0.8            0.0            0.991           79 -> 87 / pot 87
    15          0.9            0.4            0.995           same
    none        0.9            0.4            0.995           same

Beyond 10 buys nothing. **Recommend 10.** Stage 8 isolated against a stages-1-7
baseline: max per-attribute move at cap 10 is **10, zero over**. At cap 8 one
record reads 10 — **Josh Allen, power 91 → 81** — which is the source *ceiling*
of 81, not the shift: he sat above Madden's own QB range. The range rule, doing
its job. **QB attributes outside the source range on the final artifact: 0.**

**Goff: 79 → 87, potential 87, against Madden's 88.** The residual 1 is five of
his twelve live attributes at the source ceiling (intelligence 99, decisions,
power, ballSecurity, stamina). PGM3 values legs; that is the disagreement Ryan
said to leave.

**The re-measure, on the final artifact, with the published column beside it —
because the "14 of 15 within a point" baseline was never true of the published
file.** Eight positions were already off before tonight:

    pos   madden   published   new     spearman pub -> new    verdict
    QB      70        76       71        0.842 -> 0.991      fixed  (+6 -> +1)
    K       78        74       78        0.736 -> 0.701      fixed
    DT      73        75       74        0.786 -> 0.856      fixed
    S       74        76       73        0.926 -> 0.953      fixed
    TE      69        72       70        0.866 -> 0.834      fixed
    OG      72        75       75        0.894 -> 0.886      already off (+3)
    OT      72        78       76        0.905 -> 0.884      already off (+6 -> +4)
    RB      75        72       70        0.750 -> 0.803      already off (-3 -> -5)
    CB      75        75       72        0.890 -> 0.908      MOVED OUT (-3)
    WR      74        74       72        0.917 -> 0.910      MOVED OUT (-2)
    OLB     71        72       73        0.795 -> 0.825      MOVED OUT (+2)
    P       76        77       79        0.426 -> 0.529      MOVED OUT (+3)
    C, DE, MLB                                                within 1 both

**5 fixed, 3 already off, 4 moved out.** The four are stage 1 — candidate 1
takes level from the six-file pool, and the pool's CB/WR median sits below
Madden's while OLB/P sit above. Ryan accepted that as legitimate disagreement
and asked for drift as a finding: **this is the finding.** RB at −5 is the
worst residual in the file and is not new. Spearman rises at 8 positions and
falls at 7; the two largest falls are DE (0.899 → 0.859) and TE (0.866 → 0.834).

**Stages 6 and 7 verified on the artifact:** offensive `decisions` now rises
rookie → veteran at all five positions (QB 65 → 77, RB 62 → 70, WR 59 → 69,
TE 68 → 75, C 64 → 73) against the archive's 66 → 80; prospect `injuryProne`
median 47 → 32 against the archive's 28-34. The `[Rookie] injuryProne` gate row
that published 2026 fails now **passes**; the gate reads ALL CLEAR.

**Invariants on the final artifact:** growthType 1890/1890; |stored − computed|
within 1 on 99.9%; both negative tests fail on purpose; published file untouched.

### 25e. WRITTEN — cap 10, and two items Ryan must see as costs, not footnotes

`PGMRoster_2026.json` rewritten 2026-09-02 by
`tools/fix_2026_spread_potential.py --qb-cap 10`. The written file is
md5-identical to the scratch artifact every figure in 25c/25d was measured on.
2,633 records in and out, identities and order unchanged.

**The premise of the QB-only ruling was a claim that was wrong.** "14 of 15
positions within a point of Madden" was measured earlier the same day, quoted
in the ruling, and never checked against the published file. **Eight were
already off.** The master session owns that. Ryan agreed to treat quarterback
as the sole exception believing the rest of the file was aligned; it was not.

**Cost 1 — four positions moved OUT of line by stage 1**, the level-from-the-pool
step: **CB −3, WR −2, OLB +2, P +3.** Ryan accepted level drift as legitimate
disagreement, but accepted it on the wrong premise. Stated here as a cost.

**Cost 2 — ordering fell at 7 of 15 positions while level improved.** The two
largest: **DE 0.899 → 0.859, TE 0.866 → 0.834** (Spearman against Madden).
Level and order traded against each other; that is a real trade and it is
visible here rather than netted into "MAE improved."

## 26. RB at −5 is inherited from the reference files, not made by the 2026 write

Running backs sit at a median of **70 against Madden's 75** in the written 2026
file; published 2026 had them at 72. **Measured against each reference file's
OWN Madden source**, RB median minus Madden's, with the all-position offset
beside it to isolate RB from the archive's general level:

    file    RB diff   all-position diff   RB minus all
    2004       −5            −6               +1
    2007      −12            −8               −4
    2013       −5            −4               −1
    2017       −6            −3               −3
    2021      −10            −3               −7
    median RB-minus-all across the refs: −3

**Two findings.** The archive runs BELOW Madden's level at every position in
every reference file — that is "level from the pool," by design, and it means
Madden is not the level yardstick anywhere in the archive. And **RB is the
position where the gap is widest, in every file** — so the pool's RB median is
the archive's convention and 2026 inherited it through stage 1. Not a 2026-side
artifact; not from tonight's work; older than every file that fed the pool.

**2007 (−12) and 2021 (−10) are the worst**, which is the third time today those
two files have surfaced together (item 1b, item 23). Whether RB should sit 3–5
below the archive's own level is a design question about the pool, not a defect
in any one file. Leave it, with the number, until the pool itself is reviewed.

## 27. `PGMStaff_2026.json` — one string outside the reference vocabulary, pre-existing

`pgm3_validate.py staff` fails `string not in vocab [1]` at every commit checked
today, before and after the roster write. Not introduced by this work.

**Named, then over-diagnosed, then corrected.** The record is **Bill Cowher, Free
Agent, `physBoost` = "Foot Sprain"**. An earlier version of this item called it
"an injury name in a physio's field on a coach — two questions." **Both were
wrong.** Measured: `physBoost` is populated on **453 of 453** 2026 staff records,
every role, and the reference files' vocabulary for it IS injury names —
`Torn ACL`, `Concussion`, `Turf Toe`, fifteen tokens. An injury name on a coach
is the archive's convention, not a malformation.

**The defect is one token on one record:** "Foot Sprain" is not one of the
fifteen. Add it to the schema vocabulary, or set Cowher's to a listed token
(`Ankle Sprain` is the nearest). Either is a one-line change to a published
staff file, so it waits for a ruling. The probe that first looked at it assumed
the field's meaning instead of reading the vocabulary — the inference about
the field was the error, not the gate.

## 28. The 2026 write skipped every free agent — by a scope accident, not a decision — CLOSED by write 2

Ryan asked whether stage 8 scoped to rostered on purpose. **It did not, and it is
not only stage 8.** `fix_2026_spread_potential.py` line 69 sets
`ro = [x for x in d if x['teamID'] not in ('Rookie','Free Agent')]`, and every
stage from the attribute map (line 73) to the QB level (line 233) iterates that
one variable. Only stage 7, prospect `injuryProne` (line 183), chooses its own
cohort. The variable was set for the rookie and potential questions, which are
rostered questions, and every later stage inherited it without the scope being
re-decided. **An accident of variable reuse.** Nothing changed here — report only.

**What that left on the shipped file, 465 free agents, changed by the write: 0:**

    S  stamina p5    FA  23   rostered 85       QB speed floor   FA 47   rostered 54
    CB stamina p5    FA  18   rostered 80       FA QB MAE vs Madden 4.8   rostered 0.8
    headroom by years pro, FA:  2 3 2 3 2 8 0 2 0   — the flat-2 curve stage 3 never reached

Prospects are right to skip: no Madden rating to align to. **Free agents are not**
— they are real players with real Madden ratings, 277 of 465 with a unique match,
carrying the same stretch, the same flat potential, and at QB the same level gap.
Their invariants hold (growthType 465/465, rating within 1 on 100%) only because
nothing touched them; they are exactly as published.

**The fix is the scope line, and it is one ruling:** stages 1–6 and 8 over
rostered + free agents; stage 5 (first-year rescale) and stage 7 unchanged. It
would be the second write to 2026 tonight — the whole reason for "one write" —
so it waits.


### 29. Write 2 — the tool read its own output, and the fix that came with it

**Reverted before commit.** The first build of write 2 read `PGMRoster_2026.json`
— write 1's output — and ran every stage again. Double-mapping drifted 1,204
records by +1/+2, and stage 5 re-ranked already-rescaled rookies: **Jager Burton
77 → 67 → 41**, Kadyn Proctor (pick 12) 81 → 73 → 62, Francis Mauigoa (pick 10)
83 → 79 → 69. Caught by the re-verification Ryan asked for; never staged.

**Two fixes.** The tool takes an explicit `--source`, defaulting to
`wip/PGMRoster_2026.source.json` (the pre-write published file, md5 `0878a5d0`),
and asserts source ≠ output — the guard fires. And **stage 5 ranks the rookie
class on the source rating**, not the post-stage-1 one: write 1 had ranked on a
value the stretch had already inflated (Lemon at 86 sat 31 of 32 WRs; by the
source, 28). The widened build then moves 26 rostered ratings by ≥5, **all 26
first-year rookies, zero veterans** — the rank correction, not a defect.

**Write-1 misreport, corrected.** Its commit said Cousins 58 → 67, Dalton 59 → 66;
the shipped file had 73 and 71. Two names quoted from a pre-stage-8 artifact.


### 30. The 1986 build pays kickers like a modern league

Position multipliers, median salary against the file median:

| | K | P | QB | RB |
|---|---|---|---|---|
| published six | 1.36 | 1.16 | 1.87 | 0.94 |
| **1986 build** | **1.40** | **1.22** | 2.07 | 0.88 |
| 2000 build | 0.68 | 1.26 | 1.24 | 1.01 |
| 1979 build | 0.83 | 0.80 | 2.02 | 1.22 |

1986 tracks the published six almost exactly at every position, specialists
included. The modern game pays kickers above the median; 1986 did not, and 1979
certainly did not. The 2000 build set K to 0.68 but left P at 1.26, so it is half
corrected. Low stakes — it moves a few contracts, not a rating — but it is an
era claim the file makes and gets wrong.

### 31. The 1986 build reads seven points darker than its own era's archive

| | dark share |
|---|---|
| published `PGMRoster_1986`, rostered | **67.8%** |
| 1986-87 2K5 save, all 1,954 men | 60.7% |
| 1986-87 save restricted to the published 1986 names, 1,200 men | 58.6% |

The archive and the published files agree within a point for 1999-2013, so the
archive is not the thing that is off. Found while re-basing the 1979 face gate
(precedent above). Alongside item 30 it is a second sign that 1986 inherited more
of the modern files' shape than anyone realised. **Log, do not fix** — it is
published and it is the file we understand least. (2021 shows the same gap the
other way: 72.9% against its save's 65.6%.)

### 32. Two registry entries disagree with the shipped 1986 file

`faces_1986` and `PGMRoster_1986.json` were compared on family for the 530 men
in both. Two differ: **Mickey Shuler TE NYJ** (block family 1, file family 3)
and **Gary Anderson K PIT** (block 4, file 1). The validator's cross-season
check compares file to file, so a build that took the block for either man
failed against 1986 — which is how this was found. The 1979 build takes the
file. Which of the two is right for each man is unmeasured; the registry's
own change log may say. Low stakes, two men, logged.

### 31. 2026 carries six players at 99 or above; every other published file maxes at 98

| player | pos | team | before today | after |
|---|---|---|---|---|
| Nick Folk | **K** | ATL | 99 | **100** |
| Lane Johnson | OT | PHI | 99 | **100** |
| Myles Garrett | DE | LAR | 99 | **100** |
| Vita Vea | DT | TB | 98 | 99 |
| Will Anderson Jr. | DE | HOU | 99 | 99 |
| Micah Parsons | OLB | GB | 99 | 99 |

2013, 2017 and 2021 all max at **98**, with nobody at 99.

**Two causes, and they are not the same.** The 99s **predate today** — the
published file already carried **eleven** men at 99 before this session's writes,
which is the out-of-band condition. Today's writes then pushed three of those to
**100** and lifted Vita Vea from 98 (while the count at 99-plus fell from 11 to 6).

**The mechanism for the 100s is that rating has no ceiling.** In
`fix_2026_spread_potential.py` the attributes are clamped — `max(1, min(99, ...))`
at both the attribute map and the rookie refit — but every `x['rating'] = ...`
is a bare `int(round(overall(...)))`. A man whose attributes all sit near 99
computes an overall above 99 and nothing stops him. None of the three is a
quarterback, so stage 8 is not involved: it is the attribute map feeding the
rating recompute.

**A kicker at 100 is the tell.** Fixing it means deciding whether the ceiling is
98 (what the published files do) or 99 (what potential is clamped to in the 1979
build), and whether the eleven inherited 99s come down with it. **Not folded into
the Donald write — different cause, and mixing them makes both harder to reason
about.**

### 32. Coach potential relates to nothing, and a coach can gain two points in a career

**PGM3's convention, not ours — measured across all nine published files.**

| file | median headroom | max | locked | r with age | r with rating |
|---|---|---|---|---|---|
| 2004 | 2 | 5 | 21% | −0.21 | −0.10 |
| 2010 | 2 | 6 | 27% | −0.27 | −0.14 |
| 2013 | 0 | 2 | **68%** | +0.03 | +0.09 |
| 2017 | 3 | 6 | 12% | +0.01 | −0.01 |
| 2021 | 2 | 5 | 20% | −0.07 | −0.02 |
| 2026 | 2 | 4 | 29% | +0.06 | +0.03 |
| 1979 | 2 | 4 | 19% | +0.06 | +0.04 |

Median headroom is **2 at every age band from 30 to 69** across 2017, 2021 and 2026,
and the locked share moves between 14% and 27% with no pattern. Homer Rice locked at
52 while Walt Michaels has headroom at 50 is the general case, not an oddity.

**The tension, logged rather than resolved.** A coach gains two or three points over
a career and a quarter of them cannot move at all, while a rookie player carries up
to 28 and an injured veteran like Charlie Waters carries 14. **Hiring a young coach
cannot pay off in this engine.** Pat Dye reaches 65 whatever we do. Worth knowing
before anyone builds a doctrine around coach development.

**Not widened.** Departing from all nine published files to model something the
engine itself does not model is not worth it, and it was not asked for.

**And the mechanism, stated honestly:** `build_1979_roster_file.py` sets coach
potential as `rating + randint(0, 4)` — a random draw of exactly the kind removed
from the 2026 player build. It is kept here because it reproduces a published
convention that is itself apparently random: there is no signal to fit, so a draw
matching the marginal distribution is the honest choice. Written down as a decision
so it is not discovered later and mistaken for an oversight.

### 33. Prospect ceilings: 2017 is capped at 96, 2000 puts 99 on men who are already 93

Measured 2026-09-03 across every file we hold. Prospects only (`teamID == Rookie`).

| file | at potential 95+ | their median rating | their median gap | max potential |
|---|---|---|---|---|
| 2004 | 5 | 73 | **26** | 99 |
| 2013 | 5 | 76 | **21** | 99 |
| 2010 | 8 | 75 | 22 | 99 |
| 1986 | 19 | 83 | 16 | 99 |
| **2000** | **41** | **88** | **9** | 99 |
| **2017** | **1** | 82 | 14 | **96** |
| 1979 (after the PFR fix) | 27 | 77 | 20 | 99 |

**They fail in opposite directions, and neither is about the per-round gradient** —
every file gives round one about 9 or 10 and later rounds 4 to 8, 2017 included. The
difference is entirely in the tail.

**2017's ceiling is too low.** Maximum prospect potential in the whole file is **96**,
with **zero at 99** and one man at 95 or above. No prospect in that class can become a
franchise player, so Lamar Jackson at 76/84 is not an outlier — it is the ceiling
doing that to everyone.

**2000 is inflated at both ends**: 41 at 95+, 86 at 90+, and **19 rated 90 or higher
before playing a down**, against 0 or 1 in every other file. Tomlinson, Reed and
Peppers reach 99 on a gap of 6 because they start at 92 or 93. **Putting a 99 ceiling
on a man rated 93 is not a scouting reward.**

**What the good files do:** they put the high ceiling on a LOW-rated man. Rodgers is
63/99, Donald 76/99, Aikman 83/99. That gap *is* the reward — the user finds someone
the ratings undersell.

**RULED 2026-09-03, then CORRECTED the same day — fix all three: 1986, 2000 and 2017.**

The first ruling left 2017 alone on my claim that it was "a published original" whose
ceiling "came with the file". **That claim was false and I invented it.** Every one of
the ten files is this project's own work. The handoff says so in as many words — *"one
command gets all ten published files"* — and `PGM3_PRECEDENTS.md` records that **2017
originally had invented names above real ones and had to be fixed**, which is only
possible for a file we build. I read the project's word *published*, meaning
*published by us to the repo*, as *shipped by the game's developer*, and wrote the
misreading into this backlog as a provenance finding. Ryan's ruling then rested on it.

So 2017 is not a design to preserve. Its prospects capping at 96 with none at 99 is a
defect in our own work, exactly as 2000's is, and **no prospect in that file can
become a franchise player.**

**A 96 hard cap is a different mechanism from a misplaced ceiling** and is measured
separately: 2000 misplaces ceilings it does have, while 2017 appears to be clamped
before they are placed at all.

**Correction to a premise (Ryan's):** Tom Brady is NOT missing from 2000. He is on New England
at **73/78, draftNum 199** — rostered rather than a prospect, which is correct: he was
drafted in 2000, so he belongs on a roster while the pool holds the upcoming classes.

### 34. 2017's raises land on long snappers — and `GAP_BY_BAND`'s low band is why

**The four-file proposal's opening evidence. Not fixed here.**

2017 produces **nine prospect raises of 20 points or more** — the same count as
2013. 2013's go to Myles Garrett and Aaron Donald. 2017's go to **Blake Ferguson
(+25), Thomas Fletcher (+23), Hunter Bradley (+23) and Austin Cutting (+22)** —
long snappers rated 40 — with Daniel Jones at +27 the largest in the file.

**It is not a cap.** A clamp piles up at the ceiling; 2017 thins out — one man at
96, one at 94, two at 93, three at 91, seven at 90. **2000 is the file with the
pile-up**, eighteen men at exactly 99. My clamp hypothesis was wrong.

**The mechanism is `GAP_BY_BAND`**, which hands **18 points** of baseline headroom
to a man rated in the 40s and **1 point** to a man in the 90s. Defensible in
isolation — an unproven low-rated prospect has room — but with no career signal to
counterweight it, the baseline decides everything and the lowest-rated men win.

**THE FOUR FILES WERE NEVER CALIBRATED, which is a better explanation than
miscalibration.** There is no draft source file for 2004, 2010, 2013 or 2017 —
their prospects were built with **no career input of any kind**. Nothing was ever
placing those ceilings, which is why all four are flat rather than inverted: 2000
had a signal and used it backwards, these four had none. All four do carry a real
pick number on 100% of prospects, so a PFR listing joins by name and pick exactly
as 1979's did.

| file | r(gap, career span) | never | 1-3 yr | 4-7 | 8-11 | 12+ |
|---|---|---|---|---|---|---|
| 1986 | **+0.70** | 5 | 5 | 7 | 10 | 14 |
| 2021 | +0.43 | 6 | 4 | 10 | 8 | 6 |
| **2013** | +0.09 | 7 | 7 | 7 | 7 | 9 |
| **2010** | +0.09 | 6 | 7 | 6 | 6 | 7 |
| **2004** | −0.05 | 9 | 8 | 7 | 7 | 8 |
| **2017** | −0.06 | 7 | 7 | 7 | 6 | 6 |

**Rodgers 63/99 and Donald 76/99 are isolated cases, not a working mechanism.**
Donald's +23 sits in a file where twelve-year men and never-played men both get 7.
A handful of correct cases in a file with no signal is the plausible-distribution
trap.

**`GAP_BY_BAND` is shared and deliberately untouched here.** It reaches every file
including 1979, which works and is verified; changing a shared formula to improve
one file is how three break. It belongs in the four-file proposal, measured across
the files it affects.

### 35. The `probowls` cap is NOT a defect — CLOSED, and my claim was wrong

I reported that `0.9 * min(6, probowls)` truncated the best careers, since Brees's
13 Pro Bowls score as six and Witten's 11 likewise. **Tested against PFR `wAV` on
the 1,339 men of the 1980-83 classes, every treatment that credits Pro Bowls above
six makes the whole raise term WORSE:**

| treatment | r vs career value |
|---|---|
| **current, `min(6, pb)`** | **+0.9032** |
| two-tier, extra 0.4 for 7-12 | +0.8992 |
| raised cap, `min(12, pb)` | +0.8915 |
| uncapped | +0.8900 |

**And the tiers were never collapsed.** The twelve men above six already take a
median raise of **12.9** against **9.0** for men at four to six — the separation
comes from `allpro` and `seasons_started`, which move with Pro Bowls. My "two real
tiers collapsed into one" was wrong.

**Brees is also not an anomaly.** His raise decomposes as probowls 5.4, allpro 1.6,
`car_av` 4.6, seasons started 3.6 — total 15.2, against Ed Reed's 20.0 and
Peppers's 20.8. He has **one** first-team All-Pro to Reed's five. At 69/89 he
carries a 20-point discovery, which is a defensible placement for a second-round
pick who became great, not a truncation.

**Left as it is.** Ryan authorised fixing the cap; the measurement says do not.

### 36. `seasons_started` is the strongest signal available, at r = +0.94

Measured on the same 1,339 men, against PFR `wAV`:

| signal | r | coverage |
|---|---|---|
| **seasons started** | **+0.94** | 35% |
| career span (nflverse) | +0.76 | 70% |
| Pro Bowls | +0.74 | 9% |
| All-Pros | +0.54 | 4% |
| all three combined | +0.86 | — |

**1979 works partly because it leans on this hardest**, and it had been treated as
a secondary term. Pro Bowls at 9% coverage was never going to carry one.

Note that `seasons_started` is itself capped at 12 and Brees's real figure is 19 —
but by the evidence above, raising that cap should be measured before it is
assumed to help.

### 37. The $197.4M payroll constant is inherited, not measured — the game runs $242.9M

Ryan exported a **full fresh vanilla league** on 2026-09-03: 3,441 roster records,
432 staff, 32 teams of exactly 53. Now in `sources/vanilla/`. It is the only
complete authoritative reference the project holds — the previous one was a
45-player stratified sample.

**Every one of our ten files reads a median top-53 of exactly $197.4M. The game
reads $242.9M.**

Ten files agreeing to the dollar is not ten measurements; it is one ancestor. The
same pattern as the contract-ceiling finding already in the precedents, where five
files agreeing to the dollar turned out to be the donor file's highest-paid player
rather than an engine limit. **$197.4M appears never to have been checked against a
game-generated file** — it could not have been, because none existed until today.

**Stated plainly: the constant was never measured against a game-generated file,
because none existed. One now does.** Every prior validation compared our files to
each other, which is why they agree to the dollar — the same shape as the K/P
contract ceiling, where five files agreeing exactly turned out to be one donor
record wearing five coats. Ten files at $197.4M is one ancestor wearing ten.

**Measure and log, do not act.** Every file is internally consistent at $197.4M and
nothing is broken. A $45M shift across ten published files is Ryan's call and a
large one, with playtesting behind it.

---

#### The contract-compression defect belongs here, because it is the same question

**The defect is real and unfixed.** A reader reported the files "destroy cap".
Totals are correct everywhere — $197.4M median top-53, nobody over the $280M
ceiling — but **1979's cheapest quarter costs $2.14M against vanilla's $1.03M**, so
a user against the cap has no cheap depth to cut. It does not break, it seizes.
2000 is the milder version at $1.29M. Seven of the ten files are fine.

| | p25 | median | top 20% |
|---|---|---|---|
| vanilla (full export) | 1.03M | 1.27M | 58% |
| conforming eight | 0.73–1.02M | 0.93–1.74M | 54–65% |
| **1979** | **2.14M** | **3.30M** | **38%** |
| **2000** | **1.29M** | **2.39M** | **50%** |
| 2007 | 1.02M | 1.22M | 56% — inside, leave alone |

**A working transform exists** (`tools/compress_contracts.py`) and was measured:
rank-preserving within team, team totals exact to the dollar, and it moves 1979 to
1.16M / 1.80M / 63%. **Zero strictly-ordered pairs invert** — the per-team Spearman
of 0.9997 is entirely tied pairs becoming distinguished.

**It is not applied, and the reason is this item.** Compressing toward the eight
conforming files propagates a position hierarchy the game does not share: at a 50%
blend, six of 1979's positions move closer to vanilla and six move further, mean
distance rising 0.32 → 0.42, with quarterback going from 0.41 away to **1.59**.
Compressing toward *vanilla* instead is the right reference and redefines
"conforming" for the whole archive. **Payroll level and payroll shape are one
decision**, and neither half fits inside a two-file fix: the first is knowingly
wrong, the second is a ten-file decision in a two-file disguise.

**What makes the larger ruling possible now:** a full game-generated league is in
`sources/vanilla/` — the first this project has held — and both the payroll constant
and the position band have turned out to be ours rather than the engine's.

#### Two different flatnesses, and only one of them is this item

**2026-09-03.** 1979 has been called "flat" throughout, without distinguishing
which distribution. They point opposite ways.

| | team-payroll spread (max:min) | player-salary spread (p90:p10) |
|---|---|---|
| vanilla | 1.78x | **10.7x** |
| **1979** | **2.45x — the WIDEST of any file** | **4.6x — the narrowest** |
| 2000 | **1.13x — the narrowest** | 7.4x |

**1979's teams are spread wider than the game's; its players are squashed into a
third of the game's range.** Only the player one is this item. 2000 is the reverse
case and its teams are nearly identical to one another — a $24M gap across all 32.

Conflating them sends you looking for the compression in the wrong distribution.

#### The level change amplifies the compression without causing it

A uniform per-team scale leaves the ratio invariant by construction, so raising
1979 to $242.9M moves it 4.6x -> 4.5x. **What moves is the floor.** 1979's
tenth-percentile player goes from **$1.40M to $1.64M** against vanilla's $0.70M —
the cheap depth a capped user needs to cut gets more expensive, not less.

That is the argument for doing level and shape in one write rather than leaving
1979 raised and uncompressed.

#### BATCH 1 DONE, 2026-09-03 — seven files raised, three held

Six raised to $242.9M (1986, 2004, 2013, 2017, 2021, 2007) plus 2026's extension
repair, in f5cc178. Median top-53 $197.4M -> $242.9M, min/p25/max matching vanilla
exactly, ordering exact inside every team.

**Held, and why:**

| | fails | disposition |
|---|---|---|
| **1979** | mean 0.323 -> 0.328 | compression showing through the level. **Batch 4**, one write. |
| **2000** | mean 0.351 -> **0.379**, the largest move of any file | same defect. **Batch 4.** |
| **2010** | mean 0.514 -> 0.521 (ruled noise) AND centre 1.06 -> 1.16 against vanilla 0.55 | the second failure was masked by a short-circuiting assertion. **Unruled.** |

The mechanism behind all of them: rank-mapping team totals onto vanilla's spread
needs a different factor per team, and those factors jostle cross-team position
ratios. **The flatter a file's team spread, the wider the factor range needed, the
more the ratios move.** 2000 is the extreme — 1.13x mapped onto 1.78x demands
factors from 0.82 to 1.33, some teams cut a fifth and others raised a third.

#### 1979 and 2000 DONE, 2026-09-03 — `tools/contracts_to_vanilla.py`; 2010 SKIPPED

Level and shape in one write, the game as the reference, position-aware: each
position rank-mapped onto vanilla's distribution for that position, then each
team scaled uniformly onto the rank-mapped vanilla total.

| | mean position distance | p10 / p25 | team median | within-team pairs reordered |
|---|---|---|---|---|
| 1979 | 0.325 → **0.133** | $0.76M / $1.08M | **$242.9M** | 16.8% (same-position 21 of 2,390) |
| 2000 | 0.351 → **0.142** | $0.64M / $0.94M | **$242.9M** | 12.9% (same-position 23 of 2,705) |
| vanilla | — | $0.70M / $1.03M | $242.9M | — |

The reordering is our `POS_MULT` hierarchy being replaced by the game's, ruled
ours and not the engine's. **The data was sound** — item 45 measured zero
placeholders in either file. Extension terms scale with the man. Roster gate
ALL CLEAR on both with `--payroll=vanilla`.

**2010 is the one file the payroll rollout did not reach, by ruling.** Raising it
moves centre 1.06 → 1.16 against vanilla's 0.55 while the mean distance worsens
0.514 → 0.521 — the guard doing its job, and not the 2007 trade. It stays at
$197.4M; `--payroll=vanilla` is not the flag for it.

#### ALL TEN DONE, 2026-09-03 — `tools/fix_contracts.py`, and the 2010 hold REVERSED

The three-stage tool built on 2026 (floor from vanilla by position and band,
lift-only; position-aware transform; second floor pass; extension terms from the
final salary, rostered from the joint table and free agents from vanilla's own
free-agent asks), then `raise_payroll` to re-true. **The floor binds on SALARY
alone**, ruled: the payroll basis is salary+guarantee, but the floor exists so a
man does not read as unpaid on his contract screen, and that screen shows salary
(Christen Miller, $0.452M salary on $1.08M total, was the case).

| | p10 | median | p90 | salary <$500K | mean dist. | team median |
|---|---|---|---|---|---|---|
| vanilla | 0.70 | 1.27 | 7.50 | 0 | — | 242.9 |
| 1979 / 2000 / 2026 | 0.70–0.72 | 1.34–1.70 | 7.1–10.6 | 0 | 0.124–0.140 | 242.9 |
| 1986 / 2004 / 2007 / 2010 | 0.68–0.69 | 1.30–1.38 | 6.9–8.1 | 0 | 0.108–0.147 | 242.9 |
| 2013 / 2017 / 2021 | **0.65** | 1.20–1.24 | 5.7–7.3 | 0 | 0.108–0.146 | 242.9 |

**p10 after the re-true lands at $0.65–0.72M** against the game's $0.70M. The
three at $0.65M are the deepest rosters, where the 59-vs-53 confound is largest;
the re-true's per-team scale takes a few floor-lifted men back under $0.70M. A
third floor pass would close it and was offered; not run.

**2010's hold is reversed.** The hold was against `raise_payroll`'s uniform
per-team scale, which moved centre 0.10 further from vanilla while the mean
worsened. This transform is a different mechanism, and it gives 2010 the best
gain of the nine — 0.514 → 0.135. The hold was against a transform, not the file.

**2021 is the poorest landing** — 0.146, and the only file whose p90 falls
(6.57 → 5.67). Its salary ordering was built on rating, so the map has nothing
better to work with. Shipped and logged; 2021 has surfaced as the least-well-
built file repeatedly this week (items 4, 42, and here). Its recognisable drops:
Fred Warner $23.6M → $13.7M, Derrick Henry $15.3M → $9.4M (salary+guarantee).

#### RULED: all ten get tuned, as its own piece of work, after two checks

1. ~~Confirm $242.9M from more than one vanilla export.~~ **CLOSED 2026-09-03.**
   Ryan exported a second league. **Zero shared identifiers**, 63% shared names
   from a common name pool — independently generated — and the economy is
   **identical on every measure**:

   | export | md5 | rostered | payroll median | min | max | p25 | top 20% |
   |---|---|---|---|---|---|---|---|
   | 1 | `1f1cf614` | 1,696 | $242.9M | $155.3M | $276.6M | $1.03M | 58% |
   | 2 | `81c4c07a` | 1,696 | $242.9M | $155.3M | $276.6M | $1.03M | 58% |

   Two independent leagues agreeing to the dollar, including per-team minimum and
   maximum, means the game generates its economy from a fixed template. **$242.9M
   is the engine's number, not one sample's variance** — and the archive's $197.4M
   is definitively ours: two measurements of the game against ten copies of one guess.
2. **STILL OPEN — does the cap rise across seasons?** A fresh league cannot answer
   it; this needs a vanilla league **simmed forward a year or two** and exported.
   If payroll rises, $242.9M is a starting point rather than a constant and
   matching it needs to know which. **That export is the remaining blocker.**

### 39. Coach potential IS a defect after all — item 32's ruling rested on a false premise

**Item 32 concluded that coach headroom of 2 with a quarter locked was "PGM3's
convention, not our defect", and Ryan ruled not to widen it on that basis. The
vanilla staff export refutes it.**

| | median headroom | p90 | max | locked |
|---|---|---|---|---|
| **vanilla (the game)** | **7** | **14** | **27** | **0%** |
| 2017 | 3 | 6 | 6 | 12% |
| 1986, 2000, 2021, 2026, 1979 | 2 | 4–5 | 4–8 | 19–32% |
| 2013 | 0 | 2 | 2 | **68%** |

**The game gives a coach the same room a player gets. Our files give him two
points and lock a quarter of them.** Every one of the ten agrees with the others
and disagrees with the engine — the fourth time in two days that a "convention" has
turned out to be one ancestor wearing ten coats, after the payroll constant, the
position band, and the 2017 provenance claim.

**So the tension logged in item 32 — that hiring a young coach cannot pay off — is
ours and fixable, not the engine's.**

**Two more staff findings from the same export, both against work already shipped:**

**The sitting head-coach floor is 64, not 58.** Commit `7fd6391` remapped 1979's
sitting coaches onto a floor of **58**, derived from our own nine files, and that
fix was correct as far as it went — it lifted Neill Armstrong off 32. But the
target was our convention again, and **the game floors sitting coaches at 64**.
1979 currently reads a minimum of 58 and should read 64 or above. Logged against
that commit rather than left reading as correct.

**Our free-agent coach pools are much larger and much worse than the game's.**
Vanilla carries **16** free-agent head coaches rated **57 to 64** — a narrow band
just below the sitting men, so a user firing a coach hires a plausible replacement.
Ours carry **21 to 33** men rated down to **32**. The 1979 pool built at `b69ed98`
holds 99 men across two tiers on the same assumption. **Worth settling before that
pool is used as a template for anything.**

**THE CAVEAT IS RESOLVED, and the reason is structural: THE GAME SHIPS A FIXED
STAFF POPULATION AND GENERATES PLAYERS.** The three exports share all 432
identifiers because those 432 *are* the engine's coaches, not because one file was
copied. Between two exports, **290 of the 432 records differ** — 284 change
`teamID`, the rest change contract terms — while ratings, potentials and attributes
are identical. The rosters, by contrast, share **zero** identifiers between leagues.

So the shared identity is the population, not a repeated sample, and **item 39 is
CONFIRMED rather than provisional.** It also means our staff builders invent names
for a cast the game keeps fixed, which is worth knowing before rebuilding the pool.

#### FIXED on all ten files, 2026-09-03 — `tools/staff_vanilla_curve.py`

Three changes from the game's own staff export (three exports of one league; the
game ships a fixed staff — 290 of 432 records differ only in team and contract —
so n = 1 is all there is).

**Potential.** Vanilla's headroom is unconditional: r with age +0.02, with rating
+0.02, median 7, p90 14, max 27, nobody locked. Every staff member now draws his
headroom from those 432 values, seeded on his identity. **Potential may exceed
99, as the game's does** — vanilla runs to 114 and its 98-rated head coaches carry
100-114 — trimmed at the observed 114. The 50x growthType rule stays: it is ours
(vanilla holds it exactly on 43 of 432, median ratio 0.95, range 0.24-1.98) but
sits inside the game's range.

| | headroom med | p90 | locked | potential max | above 99 |
|---|---|---|---|---|---|
| vanilla | 7 | 14 | 0% | 114 | 24 |
| ours before | 0-3 | 2-6 | **12-68%** (2013 worst) | 94-97 | 0 |
| ours after | 7-8 | 14-15 | **0%** | 106-114 | 3-26 |

**Floor.** 26 sitting head coaches under 64 across ten files, rank-mapped onto
vanilla's employed ramp (64, 65, 65, 66 ...) rather than piled on 64. **Pat Dye
63 -> 66**, ruled: the placement carries the story, and he is still the
lowest-placed of the four franchise hires.

**Pool.** Size and floor from vanilla, composition real. 16 per role; generated
filler dropped weakest-first; **a named man is never dropped and ratings are
untouched**, so 2007 keeps Cowher 90, Parcells 90 and Jimmy Johnson 86. The pool
reads 57-90 against the game's 57-64 — an accepted divergence with the same
reasoning as the prospects: vanilla invents its pool, we have real men. 1986 (20),
2010 (27) and 2026 (27) stay over 16 at head coach because every man there is
real; that is the ruling working.

**Ambiguity resolves at the level of the set, not the name.** 2017's head-coach
pool carried five Hoffmans, four Whitfields, three Vances and two each of Osborne,
Marsh, Sullivan and Lockhart, none of whom had held any role on any team in any of
the ten files. Individually ambiguous; collectively a name generator. Dropped.
Jim Mora Sr. (2007) and Douglas Henderson (2004) — one name each — stay.

**1979 has no pool** (288 records, 32 x 9). Potential and floor applied; the pool
is created in batch 4.

### 38. The position-multiplier "band" is our convention, not the game's

Built from the eight conforming files to gate the contract-compression work.
Against the vanilla export, **seven of ten positions fall outside it**:

| position | vanilla | our band | |
|---|---|---|---|
| K | **0.59** | 1.00–1.92 | outside |
| P | **0.71** | 0.87–1.40 | outside |
| CB | 2.18 | 0.83–1.01 | outside |
| WR | 1.97 | 0.83–0.95 | outside |
| S | 1.32 | 0.83–1.00 | outside |
| OT | 0.86 | 1.06–1.26 | outside |
| QB | 2.25 | 1.45–2.14 | outside |
| RB | 0.92 | 0.82–1.08 | in |
| TE | 0.88 | 0.75–1.00 | in |
| DE | 1.18 | 0.83–1.19 | in |

**The kicker result vindicates the 1979 era ruling from the other direction.** We
paid 1979's kickers 0.77 of the field median as a deliberate era departure from a
"modern" band of 1.00–1.92. **The game itself pays them 0.59.** 1979 is closer to
the engine than the eight files we called conforming, and the premium we treated as
normal is the divergence.

**Consequence for the compression gate:** a relative band built from our own files
would enforce our own convention. The gate should be rebuilt against vanilla, or
restricted to the one property it was written to catch — a transform making a ratio
*worse* — without claiming the band describes anything.

### 40. Prospect potential is computed relative to draft-time rating, so career outcome cannot fully determine the ceiling

**Supersedes the deferred halves of items 34 and 35's follow-ups. One defect, two
symptoms.**

`draft_potential` computes `rating + baseline + raise`, where `baseline` comes from
`GAP_BY_BAND[rating // 10]` and `raise` from career outcomes. **Both terms are
anchored on where a man started**, so where he started bounds where he can finish.

**Symptom one — the ceiling is bounded by the floor.** In 2004, Jahri Evans
(rating 73, career value 114) reaches **99** while Aaron Rodgers (rating 63, career
value **169**) stops at **95**. Evans was a very good guard; Rodgers was a four-time
MVP. Rodgers has the largest raise in the class at +32 and still cannot reach the
top, because 63 + 40 is where the cap bites and 63 + 32 is where he lands.

**The clearest instance is Dak Prescott, 2013 file: rating 58, career value 104 —
more than Myles Garrett — and he tops out at 79.** Wider gap than Rodgers between
what a man became and where he can finish, and a more recognisable name. Jalen
Hurts, 62/77 on 79 career value, is the same shape in 2017.

**What is NOT this defect, for contrast.** In 2017, Justin Herbert falls 82 → 79 and
Kyler Murray 90 → 84. Those are the flat baseline being *corrected* — their prior
ceilings were generous and unmeasured, and their career values (74, 71) genuinely
sit below Josh Allen's 111 and Lamar Jackson's 110. A man losing an unearned ceiling
is the fix working. Rodgers is the defect because he fell *despite* the largest
raise in his class.

**Symptom two — the never-played band sits too high.** `GAP_BY_BAND` gives 18
points of baseline to a man rated in the 40s and 1 to a man in the 90s, so men who
never played take a median headroom of 7 against 6 for men with a career value of
1-24. Every fixed file shows it: 1979, 2000 and now 2004.

**1986 escapes both** only because its prospect ratings cluster tightly — 1% in the
40s, 38% in the 50s — so the baseline barely varies and the raise does the work.
That is why it reads +0.70 while the others plateau around +0.40.

**NOT FIXED. It reaches every file with a calibrated class** — 1979, 2000, 2004 and
the three to follow — and wants measuring across the whole set rather than bolting
on mid-pass. A fix would likely make potential a function of outcome with rating as
a floor, rather than of rating with outcome as a bonus.

**2017's weaker gradient is class composition, not a defect.** It reads +0.33
against +0.40 to +0.44 for the other three, with identical bands. Its classes are
2018-2021 and **recent men have truncated careers**: `wAV` p90 falls from 49 in
2017 to 43, 35 and 30 across 2019-2021, and the file's career-value standard
deviation is **16.8 against 21.5-23.6** for the other three. A compressed outcome
range flattens a correlation without changing the shape. Nothing to chase.

**Two reasoning errors recorded alongside**, both Ryan's and both the same shape:
Rodgers and Peterson were cited as evidence 2004's mechanism worked, and with a
real signal applied Peterson rises to 99 while Rodgers falls to 95 — they were the
flat baseline landing well twice, not a mechanism. **Individual names are not
evidence about a distribution.**

#### FIXED on six files, 2026-09-03 — `tools/outcome_ceilings.py`

**The mechanism.** Within each draft class, rank men by outcome and map that rank
onto the class's EXISTING potential distribution. The marginal is preserved by
construction, so the numbers that matter — star supply at 1.8-4.5% against
vanilla's 2.0-3.1%, and the count at 99 — do not move. **What moves is which men
hold the ceilings.** Rating is a floor: a man whose mapped potential would sit at
or below his rating gets rating + 3, vanilla's median headroom among its unlocked
prospects.

**Why +3 and not a bare floor.** A bare rating floor was measured first and locked
**13-15% of every class** — men locked for being rated above their outcome rank.
That is not vanilla's locked share, which is random, and it is not a bust. Ryan's
"leave the locked share alone" ruling was about not manufacturing busts, and this
does not. The old ~1% locked was the previous formula's noise clipping at zero;
it goes to 0% and nothing real is lost.

**Per class, not per file**, because 2017's 2021-class men have truncated careers
and a whole-file rank would push them down for playing fewer seasons, not worse
ones.

| file | r(outcome, potential) | 90+ | at 99 | headroom p90 | source |
|---|---|---|---|---|---|
| 1979 | +0.69 → **+0.87** | 3.7% → 3.7% | 17 → 17 | 12 → 17 | PFR wAV |
| 2000 | +0.72 → **+0.95** | 3.3% → 3.3% | 9 → 9 | 14 → 17 | **car_av filled from nflverse span — the +0.76 substitute** |
| 2004 | +0.69 → **+0.94** | 4.5% → 4.6% | 8 → 8 | 15 → 18 | PFR wAV |
| 2010 | +0.68 → **+0.94** | 3.9% → 4.1% | 18 → 18 | 15 → 20 | PFR wAV |
| 2013 | +0.64 → **+0.92** | 2.8% → 2.8% | 7 → 7 | 14 → 18 | PFR wAV |
| 2017 | +0.65 → **+0.93** | 2.2% → 2.3% | 8 → 8 | 14 → 18 | PFR wAV |

**The named cases:** Rodgers 95 → **99**. Prescott 79 → **90**. Hurts 77 → 88.
Brees 89 → 97. Russell Wilson 87 → 99. Herbert 79 → 87 and Murray 84 → 86, which
is where their outcomes put them against Allen (95) and Jackson (99). Garrett,
Evans, Peterson, Munoz, Lott, Singletary, Marino, Elway, Tomlinson, Watt: 99,
unchanged.

**ACCEPTED DIVERGENCE, ruled.** Headroom p90 widens from 14-15 to 17-20 against
vanilla's unlocked 10-11. Prescott at 33 points of headroom IS the fix working;
star supply, the measure that matters, does not move.

**HELD, and why — this is six files, not ten:**

| file | classes | reason |
|---|---|---|
| ~~1986~~ | 1987-90 | **DONE 2026-09-03** on the saved pages, 0 misses: +0.80 → +0.86, 90+ 2.8% → 2.9%, at 99 12 → 12, 20% floored. Stays the archive's best file. |
| ~~2021~~ | 2022-25 | **DONE 2026-09-03**, 0 misses: +0.73 → +0.91, the largest gain available; 90+ 3.5% → 3.7%, at 99 8 → 8. **Caveat in the tool**: the 2025 class carries at most one season, mostly draft slot; per-class ranking stops it being punished but cannot make the signal real. |
| **2007** | 2008-11 | Pages saved, every man joins — and **HELD by ruling with the numbers**: the map places only two thirds of the file (36% land on the +3 floor), reaches +0.78, the weakest of the seven, and 2007 is the file closest to vanilla's shape at 31% locked with one man at 99 — the property treated as a deliberate divergence elsewhere. Changing it costs its best feature to gain the least. |
| **2026** | 2027-28 | **The game's future. No outcome can exist and none is invented.** Its ceilings are consensus scouting, which is the honest thing for a future class. **Not touched, by ruling.** |

This also resolves the contradiction between this item's "+0.70 for 1986" and the
Section 3 line calling 1986's prospect cohort unsourced: the +0.70 is measured
against nflverse **career span**, which is a source, just the weaker one. Both
statements were true; neither said which.

#### 2026 raised to the game's level, 2026-09-03 — the play test decides the rest

**Second prerequisite closed by Ryan's measurement, not mine.** He exported a
league simmed into its second season: **1,259 rostered, payroll median $210.7M,
min $99.9M, max $257.4M**. Rosters shrink by 437 as contracts expire before teams
refill, so **payroll falls rather than rising** — $242.9M is what a full roster of
fresh contracts costs, a level and not a curve. *That export is not on disk in the
build session; the figures are Ryan's.*

**2026 only.** Team payroll raised from $197.4M to $242.9M on the **top-53 basis**,
which is the project's documented convention and what the gate measures.

| | min | p25 | median | max |
|---|---|---|---|---|
| before | 109.9M | 178.7M | **197.4M** | 266.6M |
| after | 155.3M | 208.9M | **242.9M** | 276.6M |
| vanilla | 155.3M | 208.9M | 242.9M | 276.6M |

**A single global factor could not do it.** Hitting the median needs 1.2245x, which
sends **12 of 32 teams past vanilla's observed maximum** and our richest to $329.6M.
Our team spread is wider than the game's — 2.42x against 1.78x — so team totals are
mapped onto vanilla's own distribution by rank and each team scaled uniformly.
**Ordering inside every team is exact, asserted pairwise.**

**THE ROSTER-SIZE CONFOUND, noted and NOT fixed — this is the honest limit of the
write.** We carry **59.1** men per team against vanilla's **53.0**, because the
archive includes injured reserve alongside the active 53. So the same team total
buys **$4.11M per man where vanilla pays $4.58M**, leaving individual salaries about
**10% low**. If the play test says signings still feel cheap, this is the first
place to look. Matching per-man cost is a different and larger decision.

Two consequences of carrying six extra men, both stated rather than smoothed:
- Matching *whole-roster* totals instead left the top-53 median at $241.2M and
  failed the gate. The project's basis is top-53 and that is what was matched.
- On the **full-roster** basis our maximum is now **$283.7M**, above the $280M
  engine constant. The gate checks the top-53 basis, where we read $276.6M — and
  **2017 already ships at $280.2M full-roster** and plays, so this is not new
  territory. Flagged because it is outside anything previously shipped.

**`--payroll=vanilla` added to the validator**, opt-in. Comparing a raised file to
the unraised band is a real failure, so the band moves only when asked, and the
other nine still fail if raised by accident. Verified both ways.

**WHAT IS STILL UNKNOWN.** Two independent leagues agree the generator *produces*
$242.9M. Whether the engine *expects* it is not something any file can answer —
those are indistinguishable from outside. **Ryan imports and plays this before the
other nine follow.**

---

### 41. Extension terms are one-sided in every file, and 1979 has none at all

**Found 2026-09-03**, while repairing the damage `raise_payroll` did to
`eSalary`/`eGuarantee`. Repairing the fields meant learning what they are, and
that exposed a defect the flattening had been hiding.

**What the fields are.** `eSalary`/`eGuarantee`/`eLength` are the terms the player
wants to **re-sign** for, against `salary`/`guarantee`/`length` on his current
deal. Vanilla's Derrick Tunsil earns $3.1M on a one-year contract and wants $7.7M
over four; Reginald Emanuel earns $9.5M over four and would take $9.4M over three.

**The game's asking prices go both ways. Ours go one way.**

| file | median eSalary/salary | want a raise (>5%) | want less (<5%) | median length → eLength |
|---|---|---|---|---|
| **vanilla** | **1.000** | **27%** | **22%** | 1 → 2 |
| 1979 | 1.000 | **0%** | **0%** | 2 → 2 |
| 2000 | **0.293** | 0% | **100%** | 2 → 1 |
| 2004 | 0.524 | 7% | 91% | 2 → 3 |
| 2007 | 0.851 | 28% | 60% | 2 → 3 |
| 1986 | 1.056 | 50% | 42% | 2 → 3 |
| 2010 | 1.097 | 56% | 24% | 2 → 3 |
| 2013 | 1.231 | 66% | 21% | 2 → 3 |
| 2021 | 1.310 | 81% | 11% | 2 → 3 |
| **2026** | 1.200 | **100%** | **0%** | 2 → 1 |
| 2017 | 1.508 | 89% | 3% | 2 → 3 |

**Vanilla sits at 1.000 with a real spread on both sides** — roughly a quarter of
the league wants more, roughly a quarter would settle for less, and the median man
asks for what he already earns. That two-sidedness is the negotiation. A GM finds
bargains and overpays, and both exist.

**Three distinct failures here:**

1. **1979 has no extension terms at all.** `eSalary == salary` and
   `eLength == length` for every one of its 1,593 rostered men — 0% differ against
   vanilla's 72%. Built that way by `build_1979_contracts.py`, not damaged later.
   **Every extension in 1979 is free**, which is the same gameplay defect the
   `raise_payroll` flattening caused, native to the file. **Batch 4.**
2. **2026 and 2000 are degenerate in opposite directions.** 2026: every single
   player wants a raise, nobody would take less. 2000: every single player would
   take less, nobody wants a raise, and the median asks for **29%** of his current
   salary. Both also set `eLength` below `length` where the game sets it above.
3. **The other seven are one-sided by degree**, running from 2004 at 7%/91% to
   2017 at 89%/3%. None resembles vanilla's balance.

**ALL TEN DONE, 2026-09-03**, inside `tools/fix_contracts.py`: rostered men draw
from vanilla's joint (length, rating band) table off the final salary; free
agents — a different structure in the game (salary 0, length 0, eLength 1, an
absolute ask in eSalary, median $0.70M) — draw from vanilla's own free agents by
rating band. Every free agent in every file now carries an ask.

**One divergence in the draw, logged.** At ±5% every file reads 29–35% up and
25–33% down against the game's 27% / 22% — six or seven points hotter on both
sides. Measured on any difference the same gap shows, and the cause is visible:
**the game has 33% of men asking exactly what they earn; ours have 12–19%.** The
joint table reproduces each cell's ratio distribution, but the cell fallback and
our band mix (more 80+ men on long deals, where flat asks are rarer) halve the
mass point at 1.00. Real, mild, and not acted on.

This was a ten-file shape question of exactly the same kind as item 37, and it
was ruled on with the same care rather than folded into a payroll pass. It is also unmeasured in one important respect: **we do
not know whether the engine reads `eSalary` directly or treats it as a starting
point for negotiation**, and the difference matters for how far off these numbers
actually put us.

**1979's half is not optional in the same way.** 0% is not a bad distribution, it
is an absent one, and it is already scheduled — batch 4 opens that file anyway.

---

### 42. 2021's free-agent `injuryProne` misses the cross-year median

`[FA] injuryProne: new 34 vs ref 51` — the only remaining roster-gate failure on
2021 after the payroll write, and it predates that write. Unrelated to money.
Free-agent cohort only; the rostered men pass. Not investigated.

---

### 43. Sitting coordinators, scouts and physios are rated below anything the game fields

**Found 2026-09-03**, when the staff-potential gate's first draft used vanilla's
observed floor of 63 and fired on every file. The floor was a rating fact, not a
potential one.

Vanilla's sitting-staff rating minimum by role: **HC 64, OC 60, DC 61, ST 65,
Head Scout 66, Off Scout 65, Def Scout 64, Head Physio 64, Assistant 66.** Ours:

| | OC | DC | ST | H Scout | O Scout | D Scout | H Physio | Asst |
|---|---|---|---|---|---|---|---|---|
| vanilla | 60 | 61 | 65 | 66 | 65 | 64 | 64 | 66 |
| 1979 | 50 | 50 | 51 | 50 | 52 | 51 | 50 | 51 |
| 2000 | 52 | 52 | 52 | 51 | 50 | **45** | 51 | 54 |

Batch 3 raised the head-coach floor to 64 because that was the ruling. **The
other eight roles were never in scope and sit 10-20 points under the game's
floor.** 1979 has 14 sitting men under potential 63 and 2000 has 27, all in these
roles. Same shape as the head-coach floor before it: a convention mistaken for
the engine's. Measure and log; the fix is the head-coach fix applied per role.

### 44. 2000's staff file carries two duplicate names — pre-existing

`FAIL duplicate names [2]` on the staff gate, identical at HEAD before batch 3.
Not investigated.

---

### 45. Near-zero contracts on rated men — three sources, and filling them does not change the compression picture

**Ryan found it in play, 2026-09-03**: Aidan Hutchinson 96 at $0.08M on 7 years,
Josh Allen 96 at $0.12M on 6, Trey Smith 89 at $0.01M. Measured on every file,
rostered men only. Vanilla itself carries 31 stars under $2M — rookie deals, 6 of
them aged 26+ — and a floor of $600K; the signature is therefore **26+ and under
$2M, or anything under $500K**.

| | 85+ & 26+ & <$2M | under $500K | under $100K | min |
|---|---|---|---|---|
| vanilla | 6 | 0 | 0 | $600K |
| 1979, 2000, 2007, 2010 | 0 / 0 / 4 / 16 | **0** | 0 | $631K–$942K |
| 1986 | 13 | 31 | 4 | $67K |
| 2013 | 20 | 20 | 0 | $120K |
| 2021 | 12 | 69 | 0 | $150K |
| **2017** | 15 | **195** | **40** | **$17K** |
| **2026** | 21 | **115** | **53** | **$2K** |

**Three sources, found in 2026's builder (`build_2026.py`):**

1. **A singleton cell maps to the pool's minimum.** `assign_money` ranks each man
   inside his (position, length) cell and maps rank to a quantile with
   `q = i / max(1, n-1)`; with n = 1 that is q = 0. Josh Allen is the only 6-year
   quarterback and Hutchinson the only 7-year end, and each took the bottom dollar
   of the pool. 6 of the 42 stars under $2M and 10 of the 115 under $500K are
   singleton cells. **The Madden source had the money** — Allen's `PTSA` is 37,107
   (≈ $37.1M), Hutchinson's 16,628 — and the build discarded the level on purpose,
   keeping only the order.
2. **The pool's floor is the archive's placeholders.** The reference pool is the
   eight published files, whose bottom holds 2017's 263 sub-$500K men, 2010's
   136, 2013's 96. Anyone mapped low lands on $17K–$100K instead of a real
   minimum. The 89 of 115 who join Madden have a median `PTSA` of 110 — Madden's
   own near-minimum men — and the pool turned a $110K placeholder into a $17K one.
3. **The top is compressed everywhere**, and it is not the placeholders. 85+
   median salary is $6.6M–$11.6M in our files against **$14.35M** in vanilla, and
   filling every placeholder moves it by $0.1M–$2.2M.

**The fill simulation** (placeholders → vanilla's (position, rating-band) median):
p10 moves $0.01M–$0.39M, p90:p10 barely moves except 2017 (17.0x → 10.2x, 208
filled). **1979 and 2000 have zero placeholders**, so their compression — 4.2x and
7.9x against vanilla's 15.7x on salary+guarantee — is formula-built, not missing
money. **Filling does not change what the contract transform is fitting to.**

**Madden's real dollars are not the fix for 2026 either.** Scaled to the game's
economy they give p90:p10 of 54x, p10 $0.21M, and 39 stars still under $2M —
Madden had Zack Baun at $2.4M when he had signed for $17M a year. It is a proxy,
and a stale one.

**Source (1) FIXED on 2026, 2026-09-03 — `tools/fix_2026_small_cells.py`.**
Measured across all ten files first: only 2026 was built with `assign_money` and
only 2026 shows it. 41 rostered men sit in 22 (position, length) cells of fewer
than five; 22 of them are under $500K — **10 of 10 singletons, 7 of 14 in cells of
two, 3 of 9 in three, 2 of 8 in four** — and the other nine files have zero
sub-$500K men in small cells (theirs are the inherited pool floor). The fix: a
cell with no rank to preserve is not mapped to a quantile; a man in a cell under
five whose pay sits below **the game's** median for his position and rating band
is lifted to it, **lift only** — the man at q = 1 in a cell of two is at worst
generous, and the first draft's mistake was cutting Maxx Crosby from $37.5M to a
band median. Vanilla's median, not the file's, because the file's 85+ median is
the compressed top (source 3) and would have put Josh Allen at $10.5M against
the game's $20.8M for his band. 26 men lifted: **Allen $0.12M → $43.8M,
Hutchinson $0.08M → $18.9M, Trey Smith $0.01M → $11.5M**; Madden's value printed
beside each for the record and not used. `raise_payroll` re-run afterwards puts
the level back on the game's exactly. Under $500K 115 → 94; 85+/26+/under $2M
21 → 13. **Sources (2) and (3) remain**: the 94 are the pool floor, and the
compressed top is item 37's shape question on the eight files not yet
transformed.

**Sources (2) and (3) FIXED on 2026, 2026-09-03 — `tools/fix_2026_contracts.py`**,
in order: floor from vanilla by (position, rating band), lift-only — **282
lifted**, not the 96 under $500K, because the floor sits at $0.60M–$1.09M and
the sub-$500K count was the symptom; position-aware transform (mean position
distance 0.385 → 0.124, 14.5% cross-position pairs reordered); a **second floor
pass** ruled in because 59 men per team against the game's 53 map each team's
bottom six onto vanilla's per-position minimum and the per-team scale takes
some under $600K — **369 lifted**, again the population and not the twelve
under $500K; extension terms from the final salary. Then `raise_payroll`
re-trues the medians, with a pinned exception for a +0.001 mean-distance move.

| | p10 | median | p90 | under $500K | asks up / down |
|---|---|---|---|---|---|
| vanilla | $0.70M | $1.27M | $7.50M | 0 | 27% / 22% |
| 2026 before | $0.78M | $1.48M | $6.92M | 94 | 100% / 0% |
| **2026 after** | **$0.70M** | $1.35M | $7.29M | **0** | **33% / 25%** |

Josh Allen $43.2M, Hutchinson $20.1M (both hold from the singleton fix); Trey
Smith $11.4M → $8.0M by ruling (an 89-rated guard placed among vanilla's guards
by rank, better information than the band median). **Free agents were a
different distribution and were checked first**: vanilla's carry salary 0,
length 0, eLength 1 and an absolute asking price in eSalary (median $0.70M), so
2026's 465 draw from that by rating band — the joint table would have given
them nothing. This closes item 41's 2026 half. Remaining: item 41 on the other
eight files; source (3) on the eight files not yet transformed (item 37).

---

### 46. 21 of 1979's 22 young unrated men are ranked by age alone

Found while re-estimating Tom Jurich (batch 4). The 22 young men with no NFL
career were mapped onto the prospect band **ordered by age — 22 ahead of 25** —
because age was the only signal they carried. It is not: all 22 join a 1976-79
draft listing and carry wAV, and it is 0–4 for every one of them. Jurich (wAV −1,
the worst) was ruled down to the band's low end at 51. **Willie Taylor, wAV 0,
still reads 77 and is Jacksonville's best player** on the same age-only ranking.
Same signature, 21 men.

**FIXED 2026-09-03, `tools/fix_1979_young.py`.** The 22 ranked by outcome (wAV,
seasons started, age last) onto the same prospect band with the same plotting
position; attributes scaled so each man keeps his shape and lands on the band;
headroom kept. Jurich stays 51. **Willie Taylor 77 → 65**; Rusty Rebowe 73 → 66;
Leo Biedermann (wAV 4, the best of a bad lot) 66 → 77 and is now Jacksonville's
best player, which is what ranking by outcome means when nobody had one.

### BATCH 4 (1979), 2026-09-03 — what landed and what is held

Landed in `tools/fix_1979_roster.py` and `tools/fix_1979_staff.py --no-pool`:
Willie Brown S → CB; Donnie Green and Rocky Freitas (OT) to JAX and TEN, Mike
Sensibaugh (S) to JAX, Don Rives (MLB) to IND, from the pool; Bakken 90 → 82
(age-forward), Jurich 74 → 51; draft numbers on 1,323 rostered men from the
1960-79 listings (242 above 224, **unverified against the engine**; 255 undrafted
and 19 unresolved stay 224); extension terms on 1,597 from vanilla's joint
(length, rating band) table, clamped to vanilla's maxima on 40 men — median 1.00,
29% want a raise, 26% want less, against vanilla's 1.00 / 27% / 22%; staff hair
from vanilla's age-then-family table, with the 37 multi-season men taking the
later file's hair (the registry makes it canonical — pushing 1979's outward made
the faces gate worse, 38 → 42, and was reversed). `gate_players`/`gate_staff` now
collect every failure before raising.

**HELD: the staff pool.** 91 real head coaches are ready (all of them, by rule)
plus 16 generated men in each of the eight other roles — but **87 of the 91 have
no sourced skin**: the registry knows none, and only Bill Johnson, Modzelewski,
Ringo and Sandusky carry a face in a later file. The tool draws head families for
the rest and writes them to `wip/staff_pool_1979_faces_unsourced.csv`. Invented
skin on real men is the thing this project does not do without saying so.

**RULED AND SHIPPED, 2026-09-03.** Two routes were measured before conceding: the
face registry (0 of 87) and the six era `.ros` COCH tables, dumped for the first
time. The mods renamed only their head coaches and a few coordinators over stock
Madden 08, so COCH reached **4 of 87** — Fairbanks and Lemm (1979-SB-XIV), Bettis
and Hollway (1983-SB-XVIII) — and Lemm's CSKI is 1, the bimodal value the player
builder abstains on. **The pool ships with 7 real head coaches carrying sourced
faces** (Bill Johnson, Modzelewski, Ringo, Sandusky from 1986; Fairbanks, Bettis,
Hollway from COCH skin) plus 16 generated men in each of the eight other roles.
**84 real coaches are left out for want of skin**, listed in
`wip/staff_pool_1979_faces_unsourced.csv`. A smaller real pool beats a full
invented one. Faces-staff gate unchanged at 21 / 38 / 40.

---

### 47. The 98 ceiling was wrong — REVERTED the same day; the ceiling is 99

**Ruled and reverted 2026-09-03.** Six 2026 men computed above 98 and were capped
at 98 on the premise that no file and not the game had ever exceeded it. **The
premise was the snapshot, not the engine.** Ryan loaded 2026: Lane Johnson (98 in
our file), Jalen Ramsey and Pat Surtain (never in the six) all read **99** in
game, and men reach 99 in normal play. A week-one vanilla league has nobody at 99
because nobody has developed yet. **Fifth instance this session of reading our
data's shape as the engine's rule** — see the precedent.

All six restored byte-for-byte from the pre-cap commit (a95c793). Parsons is the
one that mattered: the shave took speed 97 → 87 on a pass rusher and overshot
anyway — he read 97 in game against the 98 aimed at.

**The gate keeps a ceiling at 99**: reached in game, legitimate. 100 is seen
nowhere and is caught. **Resolved by ruling**: Folk, Lane Johnson and Garrett had a STORED rating and
potential of 100 after the revert, which the 99 gate fails. Stored values
clamped to 99, **no attribute touched** — the game computes what it shows from
attributes, so a stored 100 never reached the player; it was a build artefact,
and the clamp changes nothing in play. Gate ALL CLEAR.

**Carried forward** (precedent): `weights.json` is a fit, not the formula — the
shave aimed at 98 and Parsons read 97. Fine for ordering and distribution; any
work that targets a specific rating is verified in game.

### DOCUMENTED CHARACTERISTIC — 59-man rosters, by ruling

Our files carry **59.1 men per team against the game's 53**: the active 53 plus
injured reserve, a deliberate convention already stated in the post. Dropping to
53 would remove ~190 real players, and the injured are often the good ones.
**The cost, accepted: a user cuts to 53 on import.**

**Cross-reference — this is the roster-size confound.** It is why every file's
bottom six per team map onto vanilla's per-position minimum in the contract
transform, why a second floor pass was needed, and why p10 lands at $0.65M on
the three deepest files against the game's $0.70M (item 37). It is also why
top-53 is the project's payroll basis and full-roster totals run higher. One
characteristic, several symptoms; do not investigate them separately.

---

### 48. The 84-coach hold rested on a principle the project does not have — REVERSED

**2026-09-03.** The 1979 head-coach pool was held twice — first at 87 of 91,
then at 84 after the era COCH tables reached three more — on the stated ground
that assigning skin to a real man is invention, and "a smaller real pool beats a
full invented one." **That principle does not exist in this project.** The rule
is **no invented humans** — no fabricated people on rosters — and the record
already states its one standing exception (generated scouts and physios). It was
never "no assigned appearance for a real person," and it could not be: the face
registry votes across community sources and assigns where coverage is thin,
`build_1979_faces` sends every unsourced player to the league prior
(`ABSTAIN_BAND`), and `build_2000` abstains to the same prior. Appearance has
been assigned to real people since the first build.

What got conflated was **"never invent data when real data exists"** — a rule
about outcomes, ratings and contracts, which is why the 2026 prospect hold (no
outcome can exist for a future class) is sound and this one was not.

**Accepted twice at this end before Ryan caught it.** Both earlier reports state
the hold as following from project principle; it did not, and the two rulings
that accepted it were made on that misstatement.

**Reversed and shipped**: all 91 real head coaches in the pool — four with faces
from 1986, three from era COCH skin, **84 assigned from the league prior** by the
same machinery every other coach and player gets, hair by the game's
age-then-family rule, and listed in `wip/staff_pool_1979_faces_unsourced.csv` for
later sourcing. The 423 existing records are byte-identical; nothing sitting
moved. **Faces-staff gate unchanged at 21 / 38 / 40** — none of the 84 sits in
any later file, so they add no multi-season pairs. Staff gate ALL CLEAR.

**Swept for the same misreading elsewhere: none found.** Every other "invented"
in the record refers to franchises, contracts, names for roles with no public
source, or outcomes — the data rule, correctly applied.
