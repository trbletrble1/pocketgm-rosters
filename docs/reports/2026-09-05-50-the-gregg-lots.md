# 50 — The Gregg lots: a league payment, an option rate, and two changes I read as one

2026-09-05. **18 images fetched from three Lelands lots. 80 held in total.**
Nothing ingested.

---

## What the 1966–67 lot actually contains

Not one document — a **Player's Copy** of a two-year Standard Players Contract,
signed **by Vincent Lombardi**, plus league correspondence.

> **NATIONAL FOOTBALL LEAGUE STANDARD PLAYERS CONTRACT**
> THE GREEN BAY PACKERS, INCORPORATED — A Corporation in the State of Wisconsin
> **Forrest Gregg**, 705 Melody Lane, Gainsville, Texas
> season commencing in **1966 and 1967** — one instrument, two seasons
> the sum of **$22,500.00**
> Signed **Vincent Lombardi** 6/8/66, Forrest Gregg 6/8/66

## The championship cheque, confirmed and it is a different animal

> **1966 NFL Championship Game.** *"Enclosed is a check from the National Football
> League in the amount of **$9813.63** which constitutes the payment of **your
> share of the player pool** of the championship game played on 1 January 1967 at
> Dallas, Texas… **no deductions have been taken from your share for Federal
> income tax**."*
> — **PETE ROZELLE, Commissioner**

Three things make it a new convention, not a bonus:

- **The payer is the league**, not the club. Every one of the archive's 182 salary
  figures is club-paid.
- **It is a share of a pool**, so the amount depends on the pool and the number of
  shares, neither of which the document states.
- **It is explicitly gross.** Most figures in this collection are not stated to be
  either way.

Declared as `postseason_pool_share`, with the rule that it may not be attributed
to the club nor pooled with club salary. **The archive held no postseason
compensation of any kind.**

## A system fact, finally from an instrument

Paragraph 10:

> *"the Club may fix the rate of compensation… which compensation **shall not be
> less than ninety percent (90%) of the amount paid** by the Club to the Player
> during the preceding season"*

**`option_year_rate = 0.90` is already a declared system predicate here, taken
from secondary description. This is the rule stated in the contract itself** — a
primary source for something we had only at one remove.

And the same paragraph draws the distinction the conventions exist for:

> *"the phrase 'rate of compensation' as above used shall not be understood to
> include bonus payments or payments of any nature whatsoever other than the
> precise sum set forth in Paragraph 3"*

**The 90% applies to base only.** Exactly what `salary_base` is for.

---

## And a second correction to the persistence table

Report 49 corrected the *start* of the 75/25 clause. This corrects its *middle*.

My table read:

| | |
|---|---|
| 1951 / 1954 / 1961 | 75/25 **weekly** |
| 1969 | **blank** percentages, **semi-monthly** |

Gregg 1966 reads **75/25 in equal SEMI-MONTHLY installments.**

**So it is two changes, not one:**

1. **weekly → semi-monthly**, between 1961 and 1966, percentages unchanged
2. **fixed 75/25 → blank percentages**, between 1966 and 1969, interval unchanged

*I read two variables as one because they moved inside the same clause. A payment
schedule has an **interval** and a **split**, and they changed independently and
years apart.* That is the third correction to this one finding in a day, each
from a document that arrived after the conclusion.

---

## Lelands, and what remains

The pattern held for all three lots: 5, 8 and 5 images, up to 1800px, no
blocking. **Lelands is the cleanest of the three hosts** — no 403, no parameter
puzzle, image URLs listed in the lot page.

Still outstanding: **the six Kayfabe storefront item IDs.**

**80 images held. 13 gate suites pass. Nothing from any contract has entered the
store** — the readings are recorded in the manifest and the conventions are
declared, but ingest waits on a decision about how much of this to take.
