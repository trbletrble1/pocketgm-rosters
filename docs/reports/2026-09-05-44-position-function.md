# 44 — What a position code does, and what nothing will tell us

2026-09-05. **224 position codes characterised from data. Zero invented.**

The position map was the last of the five gaps, and it split in two on contact.

---

## No held source states what a position code means

Checked before deriving anything:

- **StatsCrew prints the code bare.** No `title`, no `abbr`, no legend. The `Pos.`
  header carries nothing.
- **The guides have no legend that survives OCR.** A pattern for `QB – Quarterback`
  lines returned `NON = Kicker`, `TWO = Tight End`, `AFC = Safety` — prose matched
  as a legend. *That is report 34's error exactly: matching a shape and inferring
  a meaning.* Abandoned rather than extracted.

**So the English name of a position code is not available as a claim from
anything we hold.** Writing `ROE-RDE-LO = right offensive end / right defensive
end` would be my knowledge in a source's clothing.

## But the FUNCTION is derivable, and it is what the bio needed

For every code, measure which statistical columns the men who held it actually
recorded. Reproducible from the cache by anyone; `source_derived` with a stated
basis.

| code | seasons | salient | profile |
|---|---|---|---|
| WR | 13,111 | **receptions** | No. 0.98 · Yds 0.96 · Rec 0.61 |
| RB | 9,745 | **yards** | No. 0.99 · Yds 0.96 · Rec 0.30 |
| DB | 8,689 | **tackles** | Tackle 0.72 · Solo 0.36 |
| LB | 8,411 | **tackles** | Tackle 0.72 · Solo 0.43 |
| QB | 7,393 | **completions** | Att 0.96 · Comp 0.94 · Yds 0.84 |
| K | 3,314 | **field goals made** | FGA 0.94 · FGM 0.93 |
| **C** | 1,902 | **none** | No. 0.21 · Tackle 0.19 |

**224 codes have enough seasons to characterise; 87% of all people are covered.**

And the answer to the Seau case:

> Junior Seau … The rosters list him at RILB, RLB, LLB. **In all, the surviving
> statistics credit him with 1,686 tackles.**

Not 238 yards. The bio now asks the position what matters before reading the
numbers.

## The finding I did not expect

**17 codes have no salient statistic at all, and every one is an offensive
lineman:** `C`, `G`, `T`, `LG`, `LT`, `LOG`, `LOT-ROT`, `MG`, `C/G`, `G/T`.

A centre records `No.` in 21% of his seasons and essentially nothing else. **This
is not a coverage gap — it is what football statistics are.** The men who played
the position that touches the ball on every snap have almost no recorded
individual acts, in any era, from any source in this archive.

**A bio for a guard will always be a bio about presence rather than performance**,
and the honest sentence is the one already written: *"No statistics are recorded
for him — only that he was there."*

---

## The ruling I need

The **English names** are a separate question and they are yours, because they
cannot come from data.

§5 already frames it: era-native positions are held, **translation happens at
export, per era, and the mapping is itself data.** That means an English mapping
is legitimately a **build artefact, not a dataset claim** — invention belongs at
export, recorded in the build's provenance, never in the dataset's.

So the options are:

1. **Declare an export-level map from general knowledge**, marked as the build's
   own with no source — which §5 explicitly permits, and which would make
   `ROE-RDE-LO` readable to anyone.
2. **Find a source that states them** — a rulebook, a league guide's glossary, a
   reference work. None is in hand.
3. **Leave codes raw** and let the derived function carry the meaning, which is
   what the bios do today.

I would take (1), scoped to the ~224 characterised codes rather than all 2,042,
and marked so that no consumer can mistake it for something a source said. **But
it is the first time in this project I would be writing football knowledge into a
file, and that is your call rather than mine.**

**10 gate suites pass.**
