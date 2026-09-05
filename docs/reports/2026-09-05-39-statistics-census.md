# 39 — The statistics column census, and what it does to the store

2026-09-05. NFL fetch complete. **Nothing ingested.**

> **2,229 pages fetched, 0 failed. 2,233 team-seasons, 1922–2024, 22,461 tables,
> 208,061 player rows.**

Median page 74KB, smallest 33KB (LOU 1926), largest 99KB, and **zero pages under a
quarter of median** — the size check added after the media-guide finding came back
clean, which is the answer it was built to give.

---

## The volume

| | |
|---|---|
| populated value cells | **1,366,929** |
| of which calculated (`Rating`, all the percentages) | **45,209** |
| observed counts | **1,321,720** |
| **current store, all 222 stores** | **1,405,895 claims / 616 MB** |

> **Statistics roughly DOUBLES the archive. Not an order of magnitude — a factor
> of about two.**

*I had estimated ~430,000 for the current store and quoted it before checking. It
is 1,405,895 — wrong by more than three times, and it flipped the answer from
"×3.3" to "doubles". Measured now, not remembered.*

At ~440 bytes per claim on disk, the NFL statistics take `build/` from 616 MB to
roughly **1.2 GB**. Other leagues, on the roster-row ratio, add perhaps another
30%. **This is comfortably inside a laptop and not the scaling problem it looked
like from the outside** — which is the useful half of the answer for the
game-level ruling you deferred.

---

## Two defects in my own parser, both found by implausible numbers

**1. A malformed `<th>` became a column.** An unclosed tag made the regex swallow
the next one, so `<th class="dt-center"` arrived as a column name. Fixing it took
player rows from **185,269 to 193,484** — the bad header was breaking row
chunking on the tables it appeared in.

**2. Commented-out headers were read as live columns.** The pages carry a
disabled grouping row:

```html
<!-- <tr> <th colspan=7>Tackles</th> <th colspan=5>Fumbles</th> <th>Kicks</th> </tr> -->
```

I stripped `<script>` and not comments. That invented a **`Tackles` column filled
84% in the 1920s** — half a century before tackles were recorded. The live column
is `Tackle`, singular. Stripping comments took rows from **193,484 to 208,061**.

Both were caught the same way: a number that could not be true. *Implausibility is
a signal about your method before it is a signal about the data* — twice in one
census, and the second one only surfaced because I chased the first.

---

## The era-native finding, and it is not what I declared

**Column presence is nearly constant. Column FILL is what is era-native.**

| column | 20s | 30s | 40s | 50s | 60s | 70s | 80s | 90s | 00s | 10s | 20s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Tackle** | 0 | 0 | 0 | 0 | 0 | 0 | **10** | **59** | 73 | 82 | **88** |
| Ints | 0 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| Yds | 0 | 90 | 99 | 99 | 99 | 99 | 83 | 79 | 79 | 78 | 91 |
| **Rating** | **100** | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |

`Tackle` appears in the header of every era and is **empty until the 1980s**,
reaching 88% only in the 2020s — which tracks tackles becoming an official NFL
statistic in 1994. The header is not the era signal; the fill is.

**Only two columns are era-native by presence:** `Sacked` and `Yds Lost`,
**1969–2024, 56 years, no gaps**. Everything else in the 56-column vocabulary is
present throughout and varies by fill.

So the declaration must key on **fill by era**, not presence. The `era_native_columns`
entry as written would have declared `Tackle` universal and been wrong in every
season before 1980.

---

## And the anachronism at full scale

> **`Rating` is 100% populated in every decade, including the 1920s. 94 seasons of
> passer ratings computed from a 1973 formula.**

That is **45,209 calculated cells**, alongside `Comp %`, `Yds/Att`, `TD %`,
`Int %`, `X/CP %` and `FG %` — arithmetic on counted columns, derived in every era
including the ones that printed them.

`gate_anachronism.py` exists for exactly this and will refuse them as `observed`.
It has never had real data to run against. **When statistics are ingested it will
have 45,209 chances to fire, and it must fire on none of them** — because the
ingest must file them as `source_derived` in the first place.

---

## What remains before ingest

- Other leagues (AAFC, both AFLs, WFL, USFL, XFL, WLAF, UFL, AAF, CFL) — same
  fetcher, ~700 team-seasons.
- The `era_native_columns` declaration rewritten to key on fill, not presence.
- The subject shape is settled: `(person, season, club)`, since **5,007
  person-seasons are at more than one club**.
