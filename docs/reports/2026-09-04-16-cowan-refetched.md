# Cowan re-fetched — the opinion is there, wrapped in a machine summary

**2026-09-04. Report 16.** Scan only. Replaces the dead file in report 15.

    pgm3-sources/DocDump/30484e16-8631-44cd-a908-294a4900ca7b.pdf
    5 pages, 109,245 bytes, 11,302 characters, bytes/char 9.7   -> healthy band
    sha256 5b61eed5ae5c1b51ceb9f288cf47ca76b5bc54287aaeffa150194fb5f00ca89a

**Same case as the failed HTML** — *The Miami Dolphins, Ltd. v. Paul Cowan, as
administrator ad litem of the estate of David Arthur Overstreet*, Fla. 3d DCA,
11 Aug 1992, No. 91-2420, 601 So.2d 301. Docket number matches.

## It is usable — with a trap the ratio check would not have caught

**Pages 4–5 are the opinion**, opening *"COPE, Judge. The Miami Dolphins, Ltd.,
appeal an adverse summary final judgment."*

**Pages 1–3 are a machine-generated summary.** The headings give it away —
`SUMMARY`, `Legal Issues Presented`, `Arguments of the Parties`, `Table of
Precedents Cited`, `Court's Reasoning and Analysis`. That is CaseMine's own
AI layer, not the court.

**So the file mixes a primary source with a derived one, and a naive extraction
would quote the summariser as the court.** Under §3.3 the summary is
`source_derived` at best; only pages 4–5 are `observed`.

**The difference is visible in the text.** The summary says the second payment was
*"contingent on Overstreet's adherence to the contract provisions"*. The opinion
says the bonus was *"additional consideration for Overstreet's signing of the NFL
Player Contracts and 'the Player's adherence to all provisions of said
contracts. . . .'"* — which is a quotation of the rider itself, and materially
different: **consideration for signing AND adherence**, not a payment contingent
on adherence. The paraphrase drops the signing half.

**Recorded as a caution the ratio screen cannot reach.** Report 15's
bytes-per-character check identifies a page with no body text. It says nothing
about a page whose body text is partly generated. **A healthy ratio is not
evidence that what you are reading is the source.**

## What it holds

**David Overstreet, Miami Dolphins, 1983:**

    three consecutive ONE-YEAR NFL Player Contracts   1983-84, 1984-85, 1985-86
    "Signing Bonus Rider", executed simultaneously
      $150,000   upon execution
      $100,000   due 1 May 1986

The rider is quoted as *"additional consideration for Overstreet's signing of the
NFL Player Contracts and 'the Player's adherence to all provisions of said
contracts'"*.

Overstreet died in a car accident in 1984. The Dolphins did not pay the 1986
instalment. **The case was decided on arbitration, not on the merits** — the court
reversed and sent it to arbitration, so **it never ruled whether the bonus was
earned.** What the document establishes is what the contract *said*, not what was
owed.

**No annual salary figures.** The rider is all the money in it.

## Two structural facts worth their own predicates

**1. A signing bonus paid in instalments, the second deferred three years.**
Every other bonus in the collection is paid at signing (Smith $23,000, Heidel
$50,000) or across a short schedule (Greenwood's three $25,000 instalments over
19 months). This one defers 40% of the bonus to **thirty months after the last
season it covers**. That is a different instrument.

**2. A "three-year deal" papered as three consecutive one-year contracts, bound
together by a rider.** The rider *"was expressly made part of each of the three
NFL Player Contracts"* — which is how the multi-year commitment was actually
constructed under a reserve system that contracted year by year.

Both are facts about **how contracts were written**, the same family as
`roster_bonus_is_conditional` — and neither carries a per-year salary. They belong
with the system rules, not in a money average.

## Disposition

| item | status |
|---|---|
| Cowan opinion, pages 4–5 | **usable**, `observed`, zero removes |
| Cowan summary, pages 1–3 | **`source_derived`** — a machine summary, do not quote as the court |
| Overstreet bonus rider, $150,000 + $100,000 | held, person-scoped |
| bonus-instalment and three-one-year-contracts structures | candidates for the system-rule family |
| whether the $100,000 was owed | **never decided** — sent to arbitration |

Report 15's dead file is now closed. **The extraction order stands.**
