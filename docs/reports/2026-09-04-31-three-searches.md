# 31 — Full-text search, the archive enumeration, and the stats shape

2026-09-04. Branch `dataset-design`. Nothing fetched from a site needing
allowlisting; nothing ingested.

**The salary table is still not found. The other two turned up more than expected.**

---

## 1. Full-text search — the last method, and it fails on the table

Archive.org's full-text search works on access-restricted items, so it reaches
what no catalogue query can. Results:

| query | full-text hits | what they are |
|---|---|---|
| `"highest salary paid"` | 7,423 | unfiltered noise |
| `"highest salary paid" AND "lowest salary paid" AND football` | 13 | **histories of education in Upper Canada** — "football" matched incidentally |
| `"NFL Management Council" AND salary` | 557 | legal briefs, complaints, one CRS report (`RL34439`) |
| `"average salary by position" AND football` | 8 | **Staudohar**, Lipsyte, an anthology, *American almanac of jobs and salaries* |

**Staudohar surfaced by searching text rather than titles** — the source you said
never uploaded. `sportsindustryco0000stau` (1986) and `..._g2x0` (1989), both
access-restricted, both searchable inside.

**And searching inside it settles the question.** The `"average salary by
position"` hit is on page 30, and it is **Table 2.2 — Average Salaries in
Baseball, by Position**, facing Table 2.3 on baseball team salaries. The phrase
matched; the sport did not.

Its four `"Management Council"` hits are **CBA text and citations, not a table**:

- **p.66** — the Other Compensation clause: *"a signing or reporting bonus,
  additional salary payments, incentive bonuses and such other provisions as may
  be negotiated between his club (with the assistance of the Management Council)
  and the NFLPA…"*
- **p.177** — two footnotes: *203 NLRB 165 (1973)*, and the *1977 Collective
  Bargaining Agreement between the NFL Management Council and the NFLPA*.

*One thing worth keeping:* p.66 is independent corroboration of the
`compensation_component` convention — a contemporary source enumerating exactly
the components as separate things, never summed.

### The ESPN Pro Football Encyclopedia: your expectation, confirmed twice

Across **1,541 pages**: **7 hits for `salary`** (narrative, the USFL's "$1.2
million cap"), **5 for `"assistant coach"`** (prose — *"Halas signed Hunk
Anderson… as an assistant coach"*). **No register, no tables.** Not worth a
borrow.

**Verdict: the Management Council table is not in archive.org's full text.** That
was the last untried search method. It is not a failure of searching; it is a
finding about the document.

---

## 2. Pro Football Archives — enumerated, and it is not what I expected

**122,023 CDX rows → 120,687 unique page paths** after stripping scheme, host,
fragment and query. (`www.` duplicates and encoded `#gsc.tab=0` fragments account
for the difference.)

| section | unique pages |
|---|---|
| players | 59,713 + 21,790 at root |
| boxscores | 4,828 |
| weather | 4,786 |
| coaches | 4,741 + 2,359 at root |
| transactions | 3,945 |
| gamelogs | 3,593 |
| playoffs | 2,941 |
| season pages | 9,830 |
| stats / playoffteams / drafts / officials | 769 / 482 / 209 / 140 |

Two URL layouts exist — `/players/{letter}/{id}.html` and the older
`/{id}.html` — both captured. Deduplicating on the stable id
`{surname[:4]}{5 digits}`:

> **45,680 distinct players · 3,633 distinct coaches**

### It holds the leagues StatsCrew refuses

This is the part that matters.

**AFL league-index pages exist for 1926, 1934, 1936–1941, 1944, 1946–1950 and
1960–1969.** That is **every AFL the brief named** — the first (1926), second
(1936–37) and third (1940–41) — all of which StatsCrew cannot supply and where
`AFL3` traps into the Arena Football League.

**And it closes report 22's open gap.** I refused to split CFL 1945–57 into its
predecessor unions because StatsCrew back-maps them all to "CFL" and I would have
been asserting my own knowledge. This source states them natively:

| union | pages | years |
|---|---|---|
| **IRFU** — Interprovincial ("Big Four", east) | 80 | 1946–1969 |
| **WIFU** — Western Interprovincial | 78 | 1946–1960 |
| **ORFU** — Ontario Rugby Football Union | 65 | 1946–1967 |

Clubs resolve correctly on inspection of the URL codes alone — `irfuham`,
`irfumtl`, `irfuott`, `irfutor` east; `wifucal`, `wifusas`, `wifuwpg`, `wifuedm`,
`wifubc` west. **ORFU is a third union I had not accounted for at all.**

Also present: `arfl*` (Arena, properly separated from the AFLs), `acfl`, `cofl`,
`pcfl`, `orfu`, `efl`, `sfl`, `tfl`, `dfl`, and several hundred pre-NFL town-team
codes across **1910–1923**.

**Nothing fetched.** `profootballarchives.com` is not allowlisted and the CDX API
is on `web.archive.org`, a different host. The page list is now in hand, so when
the domain is allowed the fetch is targeted rather than a crawl.

*On the abandoned downloader gem: noted and avoided — the CDX API was queried
directly. Its failure mode, "silently downloading 0 files", is the same
empty-versus-failed family, and a wrapper that cannot tell an empty answer from a
broken one is exactly what this project keeps refusing.*

---

## 3. StatsCrew statistics — the shape, before any ingest

`stats/t-{TEAM}/y-{YEAR}` exists on the same pattern as the rosters and is
already covered by the source declaration. **10–11 tables per page** (passing,
rushing, receiving, kicking, punting, returns and more).

**Three things to settle before ingesting.**

**a) The parse trap applies here too.** These tables emit `<tbody><td>` with no
`<tr>`, so a naive row regex returns only the *Totals* line — I reproduced it,
getting "1 row" for Green Bay 1950. Cells must be chunked by header length. This
is report 12's finding, and it would have silently produced a season of totals
and no players.

**b) The column vocabulary is era-native.** `Sacked` and `Yds Lost` are absent
from the 1950 passing table and present from the 1970s; 1950 and CFL 1979 carry
`X/CA`, which the modern table does not. Same treatment positions got: declare
per era, translate at export.

**c) A computed number is presented as an observation.**

> **Green Bay 1950 — Tobin Rote, passer Rating 26.7.**

The passer-rating formula was adopted in **1973**. Nobody in 1950 knew Tobin
Rote's rating, and no 1950 document states it. StatsCrew computed it and printed
it in the same table as his 224 attempts, which *are* observed.

`Rating` must be ingested as **`source_derived`**, never `observed` — *a source
that states a number it computed is not a source that observed it*. Every
per-column decision needs that question asked before the ingest, not after.

---

## State

**Media guide pull: 1,437 texts, 0 zero-byte**, still running.

Owed to you: whether to pursue `RL34439` (the CRS report) as the last salary
lead, and allowlisting `profootballarchives.com`.
