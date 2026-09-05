# 33 — Assistant coaches (4 of 4), and what validation cost

2026-09-04. Branch `dataset-design`.

**The guide pull finished: 1,796 texts, 302 no-text, 7 failed, 0 zero-byte, 1.8GB,
every decade 1930s–2020s.**

Two results. The birth-date rate is settled. The extraction turned out to be
**36% precise** on first measurement, and most of this report is how that was
found and what it cost to fix.

---

## 1. Coach birth dates: 3.4%, and the shape is not what the partial corpus showed

| decade | files | coach titles | with a birth date |
|---|---|---|---|
| 1930s | 4 | 14 | **0.0%** |
| 1940s | 42 | 484 | 0.6% |
| 1950s | 85 | 1,918 | 2.8% |
| 1960s | 138 | 3,485 | 2.4% |
| 1970s | 206 | 10,363 | 4.4% |
| **1980s** | 248 | 20,877 | **9.1%** |
| 1990s | 263 | 38,769 | 4.9% |
| 2000s | 273 | 65,803 | 3.7% |
| 2010s | 323 | 91,230 | 2.2% |
| 2020s | 214 | 65,950 | 1.9% |
| **all** | **1,796** | **298,893** | **3.4%** |

**Correction to report 29.** On 513 files I reported a rising trend. It is not
rising — it **peaks at 9.1% in the 1980s and falls to 1.9% in the 2020s**. The
trend was an artefact of where the download had reached. Modern guides are far
larger (65,950 coach titles in the 2020s against 484 in the 1940s) and carry
*proportionally fewer* birth dates.

**The ruling is unaffected and now rests on 1,796 files instead of 28.** Never
above 9.1% in any decade, 0% before 1940. §2.4's stint continuity stands.

---

## 2. The extraction was 36% precise, and StatsCrew is what proved it

The first full-corpus run produced **1,588 names and 5,542 stints**. Two refusals
were obvious nonsense — `south carolina`, `quality control` — which prompted a
check rather than a fix.

**StatsCrew's 2,363 head-coach stints are the one dimension of a guide staff list
that can be independently verified.** Assistants cannot be checked against
anything; that is precisely why the guides are being read. So the head coach is
the yardstick.

> **Of guide-derived head-coach claims, 36% matched StatsCrew.**

The failures named their own causes:

```
new york city / ohio phone / d.c. phone / texas phone   <- a league DIRECTORY page
balas tom landry / biographies monte clark              <- the previous line, bleeding in
coaches don coryell / ticke bill parcells
```

### Fix 1 — anchor the name boundary → 65%

The regex took the two or three capitalised words before a title. In OCR'd
multi-column text those are often the end of the previous line. Requiring the
name to *start* at a boundary took precision to 65%.

*And the measurement itself was wrong at that point:* `george s. halas` @ 1951–58
was counted as an error. That **is** George Halas; StatsCrew writes "George
Halas". Comparing exact strings understates precision, so it is now reported as a
range — 65% strict, 69% allowing name-form differences. Same normalisation
question as the photo set, but used to *estimate* rather than to *assign*, which
is a different thing and is stated as such.

### Fix 2 — certify the block by its head coach → 93%

The deepest error was not a bad name. The 2007 Jets guide yielded Romeo Crennel,
Charlie Weis, Bill Belichick and Eric Mangini as **Jets 2007** staff. They were
Jets assistants — **in the late 1990s.** The guide carries a historical staff
list and my extractor stamped the guide's year onto it.

**The guide's year is not the stint's year.**

So the verifiable dimension certifies the unverifiable ones:

> If a staff list names the head coach StatsCrew records for that season, the list
> is that season's real staff and its assistants stand with it. If it names a
> different man, the block is a retrospective or a directory and **every name in
> it is dropped.**

| | |
|---|---|
| 36% → | unanchored |
| 65% → | name boundary anchored |
| **93%** | head-coach block certification |

**198** names dropped as mismatched blocks; **5,154** more as unverifiable —
their block named no head coach at all.

### What it cost

| | before | after |
|---|---|---|
| names | 1,003 | **447** |
| stints | 3,600 | **1,086** |
| two-club conflicts needing refusal | 25 | **0** |

**Recall more than halved, and that is the correct trade.** An unverifiable stint
has no discriminator that could clean it later — the whole reason assistants rest
on stint continuity. A gap is recoverable; 3,600 stints at 70% is not.

Residual error is **~7%**, measured and declared rather than implied. The
remaining failures are still bleeds: `ry jim mora`, `by tom landry`,
`sam mike mccarthy`.

---

## 3. What is now in the store

`build/assistants.json` — **447 persons, 1,086 stint claims.** Each carries the
certification basis in its note, so a consumer can see *why* it was trusted.

| decade | stints | | title | n |
|---|---|---|---|---|
| 1940s–1960s | 98 | | Head Coach | 152 |
| 1970s–1980s | 119 | | Offensive Line | 84 |
| 1990s | 211 | | Defensive Coordinator | 74 |
| 2000s | 245 | | Defensive Line | 73 |
| 2010s | 280 | | Special Teams | 66 |
| 2020s | 133 | | Tight Ends | 64 |

Identity is `["name", "stint_continuity"]` — the chain of club-seasons a man
occupies — with the measured 3.4% birth-date rate recorded as the reason it
cannot be anything else.

---

## Also settled: the subject shape for statistics

Measured on data already held, ahead of the statistics work:

> **5,007 person-seasons are at more than one club — 3.02%**, in every league
> (NFL 3,017 · CFL 1,392 · USFL 211 · WFL 101 · AFL 79 · APFA 54 · AAFC 49).

So a season's statistics belong to **(person, season, club)**. A `(person,
season)` shape would collapse two clubs' numbers into one and manufacture false
contests — the 1950-positions failure, one level up. The `stint` shape already
handles it; this quantifies why it must.

**Items 1–4 are done. Statistics is next.**
