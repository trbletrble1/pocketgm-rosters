# 36 — What the court cases contain (characterisation 3 of 4)

2026-09-04. Characterisation only. **Nothing extracted** — this one needs reading
rather than parsing, and the counts below are a map of where to read.

Every opinion was transcribed for salary figures and nothing else. **26 documents
— 16 HTML, 10 PDF.**

## Where the non-money content is

| document | contract | roster | career | finance | comp. award | movement | injury |
|---|---|---|---|---|---|---|---|
| **Kapp v. NFL** | **32** | 3 | 2 | 1 | – | **11** | – |
| Hayes v. NFL | **20** | – | – | 1 | – | – | 2 |
| Cincinnati Bengals v. Bergey | **14** | 3 | 7 | – | 1 | 3 | – |
| Partee v. San Diego | 9 | – | 1 | – | **7** | 2 | – |
| Beathard v. Chicago | 8 | – | – | – | – | – | – |
| Rudolph v. Miami Dolphins | 7 | **15** | 3 | – | – | – | 3 |
| Rivers v. NY Jets | 6 | – | – | – | 1 | 1 | – |
| Gardin v. Commissioner | – | 4 | 7 | **7** | – | 1 | – |
| Heidel v. Commissioner | – | – | 1 | **7** | – | – | – |
| **Alabama Football v. Greenwood** | 1 | 5 | – | **4** | – | – | 1 |
| Smith v. Pro-Football | 3 | – | 3 | 1 | 3 | – | – |

**PDFs** (page counts, same categories):

| document | pp | comp. award | contract | roster | movement |
|---|---|---|---|---|---|
| **Mackey v. NFL** (two versions) | 14 / 21 | **73 / 86** | 18 / 16 | – | – |
| **A Players View of the NFL Reserve System** | **62** | **46** | 7 | **29** | – |
| Reynolds v. NFL | 11 | 13 | 3 | – | 1 |
| Robertson v. NBA | 42 | 4 | 2 | – | **26** |

## The three that change what the archive could hold

**1. Mackey names the compensation awards, with clubs and picks.** Verified by
reading, not counting:

> "Commissioner Rozelle awarded as compensation from the New Orleans Saints to
> the San Francisco 49ers … the New Orleans Saints' first round …"
>
> "Commissioner Rozelle awarded to the New England Patriots the Los Angeles Rams'
> first round draft choice in the 1972 draft, and stated that additional
> compensation would be awarded to the Patriots from the Rams at the conclusion
> of the 1971 season."

That is **(player, from_club, to_club, year, compensation in draft picks)** —
adjacent to the `transfer` subject built for Kapp's $50,000, and needing the same
kind of shape. It is the operation of the Rozelle Rule recorded case by case, and
the dataset currently holds `player_movement_regime` as a declared predicate with
nothing in it.

**2. *A Players View of the NFL Reserve System* — 62 pages, 46 compensation
mentions, 29 roster mentions — has never been characterised at all.** It is not a
court opinion; it reads as a law-review or advocacy piece walking through the
reserve system's mechanics, First Refusal/Compensation included. Its provenance
needs establishing before anything is taken from it — it is a *party's view* by
its own title.

**3. Club finances exist in the tax cases, not the antitrust ones.** `Gardin` and
`Heidel` (both Tax Court) each carry 7 finance mentions, and **Greenwood carries a
WFL franchise's figures**. These are club-scoped economics — a subject the
dataset has never held.

## Reading notes before anything is extracted

- **Kapp's 32 contract-structure mentions** are the richest single seam. We took
  five money figures from it and left the instrument's shape.
- **Rudolph's 15 roster mentions** are the only concentration of roster facts, and
  it is a Florida appellate case, not federal — a different acquisition class.
- Robertson is **basketball**, and its 26 movement mentions are reserve-clause
  reasoning, not football facts. It stays a legal precedent, not a data source.
- Two documents scored zero on every category (`Usfl Players Ass'n`, the Super
  Bowl XXII piece) — real absences, worth recording so nobody re-reads them.

**Recommended order if extraction is wanted:** Mackey's compensation awards
first — they are enumerable, verifiable against draft records, and they populate
a declared predicate that is currently empty.
