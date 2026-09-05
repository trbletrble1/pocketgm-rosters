# 32 — The CRS figure, and the leagues StatsCrew cannot supply

2026-09-04. Branch `dataset-design`.

---

## 1. The $12,000 — verified, and its provenance is not what it looks like

You gave me the figure in chat. **A relayed number may never enter**, so I fetched
`RL34439.pdf` (842KB, 146 pages), extracted the text, and read it there:

> "Negotiations resulted in **'a minimum salary of $12,000**, better pay for
> exhibitions, and a doubling of the annual pension-fund contribution to $3
> million.'"

Context: the first CBA, effective **July 15 1968 – February 1 1970**, so it
governs the 1968 and 1969 seasons.

**Then I followed the footnote, and that changes the reading.**

You said a CRS report is better provenance than any newspaper. That is true **of
the report**. It is not true of *this figure*, because the CRS did not observe
it — footnote 69 is:

> **Stephen Fox, *Big Leagues: Professional Baseball, Football, and Basketball in
> National Memory* (Lincoln, NE: University of Nebraska Press, 1994), p. 425.**

The quotation marks in the CRS text are doing real work. **The chain is a 1994
popular history → a 2008 CRS report → us**, and Fox does not show us his own
source. The CRS's federal authority does not transfer to a number it took from a
trade book.

So it enters as **`source_derived`**, not `observed`, on a **league subject**:

```
("league_season", "NFL", "1968")  league_minimum_salary = 12000
kind: source_derived
chain: Fox 1994 p.425  ->  CRS RL34439 fn.69  ->  this dataset
```

`league_minimum_salary` is now a declared system predicate — ninth in the family
with `option_year_rate` and `developmental_squad_weekly_wage` — so the store
refuses it on a person, and it can never be averaged with player money.

**What it unlocks, as you said:** Smith's $22,000 base (*Smith v. Pro-Football*,
1968) is now placed — **1.83× the league minimum**. That is the first time any
figure in this dataset has had a floor to stand on.

## 2. The Kagan lead, closed by its own citation pattern

*The Business of Football 2001* (Carmel, CA: Paul Kagan Associates, Inc., 2001).

**Not held.** Zero archive.org hits for the title; the only "Paul Kagan
Associates" hit in the entire archive is a 1985 Newsweek radio broadcast. Your
expectation about 2001 industry reports holds.

**But the stronger evidence is inside the CRS itself.** The report cites it
**exactly five times — pages 392, 393, 394, 395, 396.** Five consecutive pages,
every one supporting the **labour chronology**.

An author writing a 146-page report on NFL player compensation, who had a
1968–1982 salary series in hand, would have cited it for one. The *shape* of the
firm was promising. **The citation pattern says chronology, not series.** Recorded
in `sources_searched_and_empty` with that reasoning, so nobody spends an afternoon
on it later.

## 3. Pro Football Archives — fetching, and it is what the CDX promised

Targeted from the page list, not a crawl. **461 priority pages** — every `afl`,
`irfu`, `wifu` and `orfu` page the archive holds.

**In progress: 280 fetched, 20 failed, 0 zero-byte** at the time of writing.

*The 20 failures are expected and worth naming:* CDX returns every URL ever
archived, including pages the live site no longer serves. A list built from
history will always contain the dead. They are recorded, not retried.

From the first 182 pages: **167 carry a roster, 3,392 distinct player ids.**

Page titles confirm the whole point of the source:

| | |
|---|---|
| `1936afl.html` | **1936 AFL Season Standings** |
| `1940afl.html` | **1940 AFL Season Standings** |
| `1946irfu.html` | **1946 IRFU Season Standings** |
| `1946wifu.html` | **1946 WIFU Season Standings** |
| `1946orfu.html` | **1946 ORFU Season Standings** |

The second and third AFLs, which StatsCrew cannot supply and where `AFL3` loads
the Arena Football League instead. And the three Canadian unions, stated natively
— **the open gap from report 22 closed by a source rather than by memory**, which
is exactly what the refusal was protecting.

**Two things the club pages carry that StatsCrew does not:**

- **Era-native two-way positions.** 1926 Chicago Bulls: `ROE-RDE`, `RDG`,
  `LOE-LDE` — right offensive end / right defensive end, on one man. This is the
  vocabulary §5 exists for, and it is more granular than anything held so far.
- **`Age`, not birth date.** A different discriminator shape, weaker, and it will
  need its own treatment rather than being read as equivalent.

Ingest comes after the fetch, with the position vocabulary declared per era
first.

---

## State

9 gate suites, all passing. 12 in-store gates, 12 firing when broken.
182 salary figures, 0 refused.

**Running:** the PFA priority fetch, and the media guide pull at 1,695 texts,
0 zero-byte.
