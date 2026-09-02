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

## 14. This session created 21 cross-season head-family changes

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
better source to two files of nine necessarily breaks it. The options are to
apply RFM everywhere (declined on a twelve-player sample), accept the
inconsistency as the cost of per-player accuracy, or revert. **That is a
ruling, and it has not been made.**

