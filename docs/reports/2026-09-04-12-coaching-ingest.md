# The coaching ingest — 1921 to 2023, and two bugs in my own model

**2026-09-04. Report 12.** Task 2 of three. Summary at
`dataset/build-reports/coaches-summary.json`, conflicts at
`dataset/build-reports/birthdate-conflicts.json`.

---

## What went in

Three sources, one **season-agnostic** store — coaching is not organised by the
season being built.

    coaching-tree         116 coaches   2,757 role claims   stints 1951-2023
    pre1936-assistants     21 rows          2 titles split  stints 1921-1935
    statscrew (c-)         13 head coaches, 1950, all resolved through c- slugs

    TOTAL  144 persons · 5,720 claims · 2,433 stints · span 1921-2023

**Coaching Tree's cache holds nothing before 1951** — 45 stints in the 1950s, 373
in the 1960s, **846 in the 1970s**, 703 in the 1980s, thinning to 6 in the 2020s.
So the pre-1936 CSV is not merely first for its era, it is *only*: the two sources
do not overlap at all.

**All 13 of the 1950 head coaches resolved**, each through StatsCrew's `c-` slug
with the person page confirming a real record.

**Two conflated titles split**, as report 11 required. `Assistant Coach / later
Head Coach` became a `role_title` on the 1931 stint and a `later_became` claim on
the person. Without the split a 1931 export lists Ernie Nevers as a head coach.

## Two bugs in my own model, both found by an implausible number

### 1. 344 false contests — a set-valued predicate resolved as single-valued

The first resolution reported **344 contested role titles** out of 2,433 stints, a
14% contest rate on the predicate the media guides are supposed to be *good* at.

**All 344 came from one source.** Coaching Tree returns `roles` as a list:

    Buffalo 1990   ['Pass Game Coordinator', 'Quarterbacks']   sources=['coaching-tree']

A coach holding two jobs is one source stating a **set**, not two sources
disagreeing. The ingest emitted one claim per element and the resolver, which
assumed one value per predicate, read them as competing.

Fixed by declaring set-valued predicates in the policy; they **union within a
lineage group** and contest only when two independent groups assert different
sets. **344 → 0**, and the contest that survived is real: the CSV's compiler states
Red Grange's coaching lineage two different ways on two rows.

**The tell was the rate.** Fourteen percent of a predicate contested, from a single
source, with no second voice present — a contest needs two voices and there was
one. **Check the source count before believing a contest.**

### 2. And the same shape is in the 1950 positions, which I reported as a result

Report 09 presented 11 contested positions as the design working. **Read again,
they are the same class of error.** They are mid-season movers listed differently
by their two clubs, and I wrote position to `person_season` scope. **On the
stint** they are two single values and there is no contest at all.

Whether position belongs on the stint, the person-season, or both is a scope
question that has never been ruled. **Until it is, those 11 should be read as a
scope artifact, not as evidence.** They are left in place deliberately rather than
quietly re-scoped, because re-scoping changes the export and is a ruling.

## Birth-date agreement, measured — and the shape matters more than the rate

§9.2 established that birth date is nearly always *present*. **Presence is not
agreement**, and the discriminator the identity model leans on hardest had never
been measured for it.

Coaching Tree's 116 coaches against StatsCrew's `c-` namespace:

    AGREE                    68
    DISAGREE                  5        agreement 68/73 = 93.2%
    not found on StatsCrew   43        (naive slug construction, not a source gap)

| coach | Coaching Tree | StatsCrew | differs on |
|---|---|---|---|
| Bobby Ross | 1936-12-23 | 1935-12-23 | **year only** |
| Bud Carson | 1930-04-28 | 1931-04-28 | **year only** |
| George Allen | 1918-04-29 | 1922-04-29 | **year only** |
| Ron Erhardt | 1931-02-27 | 1932-02-27 | **year only** |
| Buddy Ryan | 1934-02-17 | 1934-02-16 | day |

**Four of five preserve day and month exactly and differ only in the year**, three
of them by exactly one. That is a signature, not noise, and it is consistent with
age misreporting — well documented in football.

**The refinement this forces: a discriminator's reliability depends on what it is
asked.**

| question | is a contested birth date usable? |
|---|---|
| *is this the same man?* | **yes, strongly** — two different men would differ on day and month too |
| *when was he born?* | **no** — record `contested` |

A birth-date conflict degrades the **value** and barely touches the **identity**
use. §2.4's Tier B may keep leaning on it; §3's value layer must carry the contest.
Written into §9.1.

## What the store now supports, and what it does not

**Supports:** 35 distinct role titles, exact and contemporaneous where they come
from a club's own publication; stint chains per person across 1921–2023; the
head-coach flag; and the graph fields Coaching Tree carries (proteges, mentors)
which are ingested as claims but not yet used.

**Does not:** assistant staffs for any season in bulk. The store has 2,433 stints
for **144 men**. A single 1979 club had nine or ten assistants; thirteen 1950 clubs
had perhaps 40 between them. **This is a sample of notable coaches, not a staff
census**, and it must not be presented as one — which is exactly what the
declaration says and what the media-guide route exists to fix.

**The route to a real staff census remains the guides**, per report 06's
measurement: they carry the exact title but no birth date, so assistant identity
rests on stint continuity and two same-named assistants with overlapping chains
have no discriminator at all.

## Next

Task 3 — whether to derive ratings from statistics. That decision is its own
report.
