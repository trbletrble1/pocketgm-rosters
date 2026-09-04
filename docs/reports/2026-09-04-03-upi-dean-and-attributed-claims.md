# The Fred Dean cell, and what it forced in the model

**2026-09-04. Report 03.** Follows reports 01 (the 1982 antitrust hearing) and 02
(the 2002 NFLPA primer). Durable changes are in `DATASET_DESIGN.md` §3.6, §4.3,
§8.4 and §9b.

---

## First: I fetched it rather than logging the relay

The figures reached this session by relay before the URL did. **They are not in
`pgm3-sources`** — the newest file there is the primer, 10:14 today — so at that
point they were unverified, and I said so rather than logging them.

With the URL in hand:

    upi.com/Archives/1981/09/30/Chargers-six-year-defensive-end-Fred-Dean-complaining-his-salary/8038370670400/
    plain curl, browser UA, HTTP 200, 265,563 bytes

**UPI's archive is free and fetchable**, which is what makes the reconstruction
method below viable.

## What the article actually says

> *Perrine … said that the recent NFL salary schedule showed that top defensive
> linemen with six years experience earned $185,000 a year, with the lowest paid
> receiving $62,000. He said the average of all defensive linemen was $70,000, and
> Dean — even with incentive clauses in his current contract, which runs through
> 1984 — is below that.*

> *According to published reports, Dean received $65,000 last year.*

**This is the CBA-required table being read aloud** — highest, lowest and average,
by position and years of service. The 1982 hearing proved the document existed
(report 01); this is an agent quoting from it.

## Two corrections the article forces on the relay

**1. Only Dean's figure is dated.** The relay assigned the whole block to 1980.
The article dates *only* Dean's $65,000, via "last year". Perrine says "the
**recent** NFL salary schedule", which spans 1980 and 1981 and cannot be narrowed
from the text.

| figure | value | cohort | dated |
|---|---|---|---|
| highest | $185,000 | DL, **six years** experience | no |
| lowest | $62,000 | DL, **six years** experience | no |
| average | $70,000 | **all** DL — not the six-year cohort | no |
| Fred Dean | $65,000 | himself | **1980** |

Logged `observed_at: 1981-09-30`, **season unresolved**. That is what the source
supports, and inventing a season to make the cell tidier is the thing this whole
design exists to prevent.

**2. The average is for ALL defensive linemen**, not for the six-year cohort. The
relay had this right; it is flagged here because conflating them puts Dean's
$65,000 against the wrong benchmark, and the two numbers sit adjacent in one
sentence.

## The article contradicts itself, and that is kept

Dean: *"Last year I was the lowest paid sixth-year defensive lineman in the NFL."*
The schedule: the six-year floor is **$62,000**. Published reports: Dean received
**$65,000**.

**All three cannot hold.** Either Dean's claim is negotiating rhetoric, or the
$65,000 is wrong, or the schedule's year differs from Dean's.

Three claims, one contradiction, **no forced resolution** — a `contested` set. The
disagreement is itself evidence about how loosely a figure quoted inside a dispute
should be read, and a model that silently picked one would destroy that.

## What it forced in the model: §3.6, attributed claims

The closing question of report 02 — whether the League's figures can be held as a
second party's claim at all — was ruled: **they cannot.** They reach us only as
quoted by the NFLPA, in both documents. So a claim about a claim needs to be
modelled as one.

**Two fields on every claim, and the second is a chain, not a scalar:**

    stated_by     whose voice this is, inside the document we hold
    attribution   [ordered, from that voice outward toward the origin]

Empty means first-hand. Its length is the number of **removes**.

**This one short article carries three different chains**, which is why a scalar
`attributed_to` would not have been enough:

    cohort figures   UPI -> Perrine (agent, interested party) -> NFL salary schedule
                     2 removes
    Dean's $65,000   UPI -> "published reports"
                     1 remove, origin UNNAMED and unchaseable
    "lowest paid"    UPI -> Dean, about himself
                     1 remove, and an assertion made in a negotiation

**The rule:**

> An attributed claim never counts as an independent source for the party at the
> end of its chain.

A claim with a non-empty `attribution` votes only in `stated_by`'s lineage group.
The League cannot be outvoted by its opponent quoting it — and cannot be
corroborated by its opponent quoting it either.

**Attribution and lineage are different axes and both cap independence.** Lineage
is documents descending from documents (four JINX files are one vote). Attribution
is a document reporting another party. The 2002 primer is lineage-entangled with
the hearing *and* hearsay on the League's number — two separate defects in one
source.

**An unnamed origin is weaker than a named one.** `["published reports"]` cannot
be chased, corroborated or dated, and is recorded verbatim rather than cleaned up,
because paraphrasing it as a source would overstate it.

## §8.4 corrected

The worked example said "two interested parties, on the record, disagreeing". It
is **one party and one hearsay**. Corrected in place rather than deleted, with the
reason, because the first version is the mistake the mechanism now prevents.

It does not change the resolution — `contested` either way — but it changes what a
reader should conclude, and it turns a League-original source from a nicety into a
recorded debt.

## OWED: a League-original source

Every League figure this project holds arrives quoted by the NFLPA or by an agent.
**No document in which the NFL states its own number is in hand.** What would
satisfy it:

- NFL Management Council material — the schedule itself, or a circular reproducing it
- League financial disclosure in any proceeding
- **A court filing in which the League states its own figure** — *Mackey*, the
  1982 antitrust litigation, or a contract-dispute arbitration

## The method this opens, with two cautions

Every holdout of 1980–83 had an agent quoting the same survey. Search UPI 1980–83
for `NFL salary`, `salary schedule`, `holdout`, plus position words. **Not the
document — a reconstruction of it**, one dispute at a time. Ryan is running that
search; cells get logged in §9b as they arrive.

**Caution 1 — the sample is selected for grievance.** These cells are quoted by
agents in active disputes, so the figures chosen for reading aloud are the ones
that support a holdout. A reconstruction assembled from them is not a random
sample of the table.

**Caution 2 — read each cohort definition exactly.** This article gives a
six-year high and low against an all-players average, in one sentence. "The recent
schedule" will recur and each cell will carry its own dating problem.

## Disposition

| item | status |
|---|---|
| DL six-year high/low, DL all-player average | **held**, `source_derived`, 2 removes, season unresolved |
| Dean $65,000 (1980) | **held**, 1 remove, unnamed origin |
| Dean "lowest paid sixth-year DL" | **held**, contested against the two above |
| the salary schedule itself | not in hand — see OWED |
| further UPI cells | Ryan searching |

**Nothing extracted into claims yet.** The design now has somewhere to put these
correctly, which it did not this morning.
