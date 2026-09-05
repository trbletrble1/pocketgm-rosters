# 29 — The coach birth-date rate, re-measured on a corpus

2026-09-04. Branch `dataset-design`.

**2.7% came from 28 files, all 1979. Across 513 guides spanning six decades it is
3.7% — and the ruling it supports holds.**

| decade | files | coach titles | with a birth date |
|---|---|---|---|
| 1930s | 4 | 14 | **0.0%** |
| 1940s | 42 | 484 | 0.6% |
| 1950s | 85 | 1,918 | 2.8% |
| 1960s | 138 | 3,485 | 2.4% |
| 1970s | 206 | 10,363 | 4.4% |
| 1980s | 38 | 2,464 | 4.1% |
| **all** | **513** | **18,728** | **3.7%** |

Birth date never exceeds 4.4% in any decade and is **0% before 1940**. It cannot
be the discriminator for assistant coaches. §2.4's move to stint continuity
stands, now on 513 files rather than 28.

---

## Two wrong numbers, caught before they were believed

**The first pass returned 14.3%** — five times the prior, and rising cleanly by
decade, which is exactly the shape a real finding has. Sampling the matches
instead of reporting them:

- Colts 1958 — **a player's** birth date (Raymond Berry)
- Broncos 1968 — **a player's** (George Goeddeke, Offensive Guard)
- Redskins 1966 — **a coach's children's**: *"two sons, Duey, born March 13 … David, born April 15, 1951"*

The cause: I counted the bare word **"Coach"** as a bio marker. It appears
throughout a guide — *coached by*, *coaching staff*, *the coach said* — and each
occurrence dragged in whatever birth date happened to sit within 1,200
characters.

**The second pass returned 4.5%**, restricted to explicit staff titles and a
400-character window, excluding births handed to a son, daughter or wife.
Sampling again: five of seven genuine (Wayne Robinson, Bill Austin, Ted
Marchibroda) — and two still players, a Packers quarterback and a Broncos running
back, both carrying a height-weight and a listed position.

**The third pass rejects those explicitly**, dropping any match with a
height-weight, a listed position, a year-of-service or a draft note between the
title and the birth. **144 rejected.** 3.7%.

*Implausibility is a signal about your method before it is a signal about the
data* — twice in one measurement, and the second time only because I sampled a
number that had already survived one correction.

---

## What this means for item 4

Assistants are extractable. From the 513 guides held so far: **2,610 staff lines,
820 distinct names**, 1,552 of them in the 1970s alone.

The extractor is not finished — it currently matches `denver broncos` as a
person, because a club name sits where a name sits. That, and identity by stint
continuity, is item 4's actual work, and it wants the full corpus rather than the
29% now downloaded.

---

## State

**Guide pull: 513 texts, 0 zero-byte**, running through the index in year order —
1930s to 1980s held, 1990s–2020s pending. This measurement will be re-run when it
completes; the modern decades are where structured bios are likeliest, so 3.7% may
be a floor.

Items 1–3 are done and reported. **Item 4 resumes when the pull finishes.**
