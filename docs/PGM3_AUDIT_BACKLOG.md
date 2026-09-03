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
