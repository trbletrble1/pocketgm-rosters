# 30 — Assistant coaches: the method (4 of 4, part 1)

2026-09-04. Branch `dataset-design`.

StatsCrew cannot supply assistants at all. The guides can. **900 men, 1,782
stints from 1,059 guides so far** — but the value of this report is the four
things that were wrong first, because each would have produced a plausible number.

---

## 1. `re.I` on the whole pattern, which is a correctness bug wearing a
## performance bug's clothes

The extractor hung. The cause: `re.compile(name_pattern + title_pattern, re.I)`.

Case-insensitivity makes `[A-Z]` match lowercase, so the name half matched at
nearly every position in a multi-megabyte file — catastrophic backtracking. But
the slowness was the symptom. **The real damage is that `re.I` silently discarded
the "a name is capitalised" constraint that was doing all the work.**

Scoped to the title only, where era genuinely varies the casing: 29 seconds, and
the constraint is back.

## 2. A league-wide book is not a club

First run: *"mike shanahan: 1993 — NFL Record & Fact Book 1993, San Francisco
49ers"*, refused as a man at two clubs in one season. He was not. That is **one
appointment recorded in two documents** — the precedent already on the books as
*two documents from one office are one vote*.

`index.csv` has a `league_wide` column flagging exactly these. **I was not reading
it.** Same shape as every declaration failure this week: the field existed, and
nothing consulted it. False refusals fell from 78 to 24.

## 3. A name beside a title is not that club's staff

Still wrong after that: **`tom landry: 1979 — Cincinnati Bengals, Dallas
Cowboys`.** Landry coached Dallas. The Bengals guide *mentions* him.

Guides discuss opponents, history and former staff throughout. Matching the whole
document conflates *named in this guide* with *employed by this club*. Anchoring
to a staff section — `COACHING STAFF`, `ASSISTANT COACHES`, `THE HEAD COACH`,
present in **109 of 120** sampled guides — removes it. Landry is now Dallas only.

126 guides have no findable staff section and are skipped rather than guessed at.

## 4. The title vocabulary was era-biased, and would have produced a false trend

The 1999 Colts staff list reads:

> Jim Mora, Head Coach · **Bruce Arians, Quarterbacks** · **Gene Huey, Running
> Backs** · **Howard Mudd, Offensive Line** · Tom Moore, Offensive Coordinator

**Modern guides omit the word "Coach".** My vocabulary required it, so every
unit-only title was invisible — and because older guides *do* write "Backfield
Coach", the loss falls entirely on recent decades. That is not a gap; it is a
**manufactured era trend**, the shape this project keeps finding.

Era-native vocabulary added. Verified on the men it was missing:

| | |
|---|---|
| Bruce Arians | Chiefs 1989/1991 Running Backs; Colts 1999 Quarterbacks |
| Gene Huey | Colts 1999, 2000, 2001 Running Backs |
| Howard Mudd | Colts 1998–2000 Offensive Line |
| **Tom Moore** | **Lions 1994 Quarterbacks → 1995, 1996 Offensive Coordinator** |

Tom Moore's chain is stint continuity doing exactly what §2.4 asks of it: a
promotion inside one club, visible as a chain rather than a contradiction.

---

## Where it stands

| decade | stints |
|---|---|
| 1940s | 4 |
| 1950s | 68 |
| 1960s | 104 |
| 1970s | 259 |
| 1980s | 376 |
| 1990s | 670 |
| 2000s | 301 |

900 distinct men · 1,782 stints · **100 with stints at more than one club**, which
is the population stint continuity exists to track.

Top titles: Head Coach 215, Offensive Line 214, Defensive Line 199, Defensive
Coordinator 142, Linebackers 132, Special Teams 116.

**Refused: 2.** `hank bullough` (Lions and Colts, 1993) and `jack reilly`
(Cowboys and Patriots, 2001) each appear at two clubs in one season with no
discriminator — birth date is 3.7% and absent for both. Per §2.4 they are
refused, not resolved. They may be one man who moved mid-season or two men; this
source cannot say, and neither will we.

---

## Not yet done

**The store write.** This is the method, verified, not the ingest. The pull is at
1,059 of ~1,773 text-bearing guides and still running; 2010s and 2020s are absent
entirely, which is why the decade table falls off after the 2000s. Running the
ingest now would bake a coverage artefact into the claims.

When the pull completes: re-run, write the store with `stint_continuity`
denotations, re-run the birth-date measurement across all decades, and gate it.
