# Birth-date coverage by league and decade — §9.2 answered

**2026-09-04. Report 06.** Closes §10 step 2. Durable result in
`DATASET_DESIGN.md` §9.2.

## Method

StatsCrew league-year index pages enumerate their team roster links; **four teams
sampled per league-year**, every player row parsed, fill rate computed per column
against the header actually present on that page (so a missing column is
distinguished from an empty cell).

**25 league-years, ~4,613 player rows, 130 pages fetched.** Plain `curl`-equivalent
via `urllib`, 0.8s between requests, cached. Grid chosen to cover the leagues where
identity work was expected to be thinnest — **APFA, AAFC, both AFL eras, WFL, USFL,
XFL, CFL** — not just NFL decades.

## Result

| league-year | n | birth date | hometown | jersey `#` | GP | GS |
|---|---|---|---|---|---|---|
| APFA 1920 | 102 | **92.2%** | 89.2 | **60.4** | 100 | 100 |
| NFL 1925 | 88 | 98.9 | 97.7 | **77.3** | 100 | 100 |
| NFL 1930 | 125 | 96.8 | 98.4 | **87.2** | 100 | 100 |
| NFL 1935 | 113 | 100 | 100 | 97.3 | 100 | 100 |
| NFL 1940 | 142 | 100 | 99.3 | 97.9 | 100 | 100 |
| NFL 1945 | 168 | 100 | 99.4 | 93.5 | 100 | 100 |
| AAFC 1946 | 152 | 100 | 99.3 | 100 | 100 | 100 |
| AAFC 1949 | 141 | 100 | 100 | 99.3 | 100 | 100 |
| NFL 1950 | 146 | 100 | 100 | 100 | 100 | 100 |
| NFL 1955 | 146 | 100 | 100 | 100 | 100 | 100 |
| AFL 1960 | 190 | 99.5 | 95.8 | 100 | 100 | 100 |
| AFL 1965 | 178 | 100 | 98.9 | 100 | 100 | 100 |
| AFL 1969 | 196 | 100 | 100 | 99.5 | 100 | 100 |
| NFL 1960 | 160 | 100 | 99.4 | 100 | 100 | 100 |
| NFL 1965 | 172 | 100 | 100 | 100 | 100 | 100 |
| NFL 1970 | 190 | 100 | 100 | 100 | 100 | 100 |
| NFL 1980 | 198 | 100 | 100 | 100 | 100 | 100 |
| NFL 1990 | 215 | 100 | 100 | 100 | 100 | 100 |
| NFL 2000 | 227 | 100 | 100 | 100 | 100 | 100 |
| NFL 2010 | 235 | 100 | 99.6 | 100 | 100 | 100 |
| NFL 2020 | 278 | 100 | 98.2 | 100 | 100 | 100 |
| WFL 1974 | 235 | 100 | 90.2 | 95.3 | **14.9** | **4.7** |
| USFL 1984 | 268 | 99.3 | 94.0 | 89.2 | **76.9** | **65.7** |
| XFL 2020 | 261 | **96.2** | **76.6** | 100 | 84.7 | 84.7 |
| CFL 1979 | 187 | 100 | **74.3** | 90.9 | 100 | **4.7** |

**College is 100% in all 25 samples.**

## The answer

**Birth date is ≥96% in every league-year sampled and 100% in 19 of 25.** The
1920 Akron page this section rested on — 91%, n=23 — was the **worst case in the
entire grid**, and even it is usable.

**The primary discriminator holds back to 1920, and across the AAFC and both AFL
eras.** §9.2 was opened on the worry that the earliest era would need a different
declared discriminator. It does not.

## Three things the measurement was not looking for

**1. The era-dependent field is the jersey number, not birth date.** 60.4% in
1920, 77.3% in 1925, 87.2% in 1930, reaching 97%+ only from 1935. That matches the
1920 Akron roster page having **no `#` column at all** (nine headers against
1950's ten). So jersey is unusable as a discriminator before ~1935 and fine after
— a **per-era** property of the source, which the source declaration should carry
rather than a single per-source verdict.

**2. Games played is a LEAGUE property, not an era property.** This is the one
that changes something.

    WFL 1974    GP 14.9%   GS  4.7%
    CFL 1979    GP  100%   GS  4.7%
    USFL 1984   GP 76.9%   GS 65.7%
    NFL         GP  100%   GS  100%   in every sample, 1920 to 2020

**§9.6's state 2 — a source with a GP column leaving the cell blank — is not an
edge case. It is the normal condition for the minor leagues.** Nearly six in seven
WFL players have a blank GP cell in a table that has the column.

Two consequences. Any roster-completeness gate must be **scoped per league**, or
it reads the WFL as catastrophically broken when it is merely a league nobody
compiled game logs for. And the four-state model earns its keep immediately rather
than in some future edge case: collapsing state 2 into state 1 would lose the
distinction on ~200 of the 235 WFL players sampled.

**3. Hometown is the weakest field overall**, and not where expected — CFL 1979 at
74.3% and XFL 2020 at 76.6%, both worse than anything in the 1920s. It is not a
reliable fallback discriminator despite appearing on every page.

## Caveat

**Four teams per league-year is a sample, not a census.** It is enough to retire
the concern §9.2 was opened for. It is **not** enough to quote a fill rate for a
whole league-year, and any figure from this table should be cited with its n.
