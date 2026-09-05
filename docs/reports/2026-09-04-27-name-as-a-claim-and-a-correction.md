# 27 — Name as a claim (2 of 4), and a correction to report 26

2026-09-04. Branch `dataset-design`.

**Report 26 shipped a false merge. Item 2's first measurement found it.**

That is the order things happened in, and it is the reason to report them
together.

---

## 1. The correction: 36 truncated slugs merged 46 men

Item 2 began by asking whether one person's name varies across his career,
because the wrong scope manufactures contests. Three people came back with more
than one name. They were not name variants. They were **nine different men**:

```
['Edris Jean-Alphonse', 'Garland Jean-Batiste', 'Javontae Jean-Baptiste',
 'Leonard Jean-Pierre', 'Max Jean-Gilles', 'Michael Jean-Louis',
 'Patrick Jean-Mary', 'Ricky Jean-Francois', 'Stanley Jean-Baptiste']
```

**The cause is upstream of the unifier, and older than it.** `parse_roster`
extracted slugs with `(p-[a-z0-9]+)`, which stops at a hyphen. StatsCrew builds a
slug from `surname[:5]`, so *Jean-Baptiste* truncates to `jean-` and the true
slug `p-jean-jav001` was stored as **`p-jean`** — at ingest, in every store, since
the first sweep in report 20.

Corpus-wide: **36 truncated slugs hiding 46 distinct men.**

| stored | actually |
|---|---|
| `p-jean` | 9 men — `p-jean-edr001` … `p-jean-sta001` |
| `p-mike` | Nick and Steve Mike-Mayer, brothers |
| `p-haji` | Ali Haji-Sheikh and Sherko Haji-Rasouli |
| `p-al`, `p-ya`, `p-pola`, `p-boye`, `p-good`, … | 1 each |

### The declaration already knew

`person_id_scheme.pattern` is `{prefix}-{surname[:5]}{forename[:3]}{NNN}`. Every
slug ends in a three-digit counter. These do not. The constraint was written down
from the start and nothing enforced it.

**And I made it worse in report 23.** I listed `person_id_scheme` under
`_documentation_only`, which exempted it from even the naming check. That is
exactly the limit I wrote into that gate — *"it cannot see a key that is read and
then ignored"* — and it has now cost something real. The exemption is removed and
the key is enforced.

**Marking a constraint "documentation" is how a declaration stops being
load-bearing without anyone editing it.**

### The gate

`src/gate_slug_pattern.py`. Every stored source-native id must match the declared
pattern. Run against the shipped corpus it failed with all 36, naming the men each
one merged. After the fix and a full re-ingest: **171,831 slugs checked, 0
truncated.**

### What the re-ingest changed

All 217 stores rebuilt from cache. The coach regex had the same bug, so the sweep
now finds coach pages it previously truncated: **749 `c-` pages, up from 478**,
and **370 player/coach cross-references, up from 236**.

**Corrections to report 26:**

| | reported | actual |
|---|---|---|
| global persons | 40,631 | **40,745** |
| p-/c- cross-references | 236 | **370** |
| multi-league careers | 6,923 | **7,011** |
| CFL + NFL | 1,755 | 1,736 |

The nine Jean-* men are nine people. Both Mike-Mayer brothers stand separately.
Kapp is unaffected — still `P_004829` across twelve stores.

---

## 2. A second silent failure, in my own driver

The re-ingest read its work list from `build-reports/sweep-nfl.json`. That file's
`summary` array is **empty**. So all 103 NFL stores were skipped, and the run
printed:

```
re-ingested 114, failed 0
```

**Zero failures, and a third of the corpus untouched.** Caught only by checking
the per-league counts against what I expected them to be.

This is the empty-result family again — the fifth today, after the zero-byte
cache, the empty season index, the 302, and the cross-reference no-op. A report
file that lost its contents is indistinguishable from a league with no seasons.
The driver now takes its work list from the store filenames, which cannot go
stale the same way.

---

## 3. Item 2: the name is a claim

Both ingests now write one. **171,818 name claims across 40,522 people.**

Before this the name was recoverable only by parsing it back out of the
`source_record` identifier — reading a key as data — and **for coaches it was not
recoverable at all.** The coach store held no name in any field: it was read at
ingest, used for logging, and discarded. That is worse than report 25 stated.

**Scope: `person`, and it is measured rather than assumed.** With the truncation
fixed, the number of people StatsCrew renders more than one way is **0 of
40,522**. So a person-scoped name manufactures no contests — the failure mode
that put eleven false contests on 1950 positions does not arise here. Had that
number been non-zero, the scope would have had to be `person_season`.

*The first measurement of this said 3, and all three were the bug. A measurement
that disagrees with the design is worth chasing before it is worth believing.*

---

## 4. State

7 gate suites, all passing; 12 in-store gates, 12 firing when broken.
Declaration keys unread: **0**, with `person_id_scheme` now enforced rather than
exempt.

**Media guide pull, running:** 151 texts, 28 no-text, **0 zero-byte**. It is
slower than I estimated — roughly 16s per item against OCR files up to 2MB, so
the full 2,105 is several hours, not the ~70 minutes I said. The coach birth-date
re-measurement follows it.

**Next: denote the photo set (3 of 4)** — the one where a wrong answer is served
silently as the face of 2,949 men.
