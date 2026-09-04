# The salary extraction — 123 figures, and five defects in my own instruments

**2026-09-04. Report 18.** The extraction, in the ordered queue. Coverage at
`dataset/build-reports/salary-coverage.json`; store at `dataset/build/salaries.json`
(not committed — extracted third-party content, same ruling as `sources/`).

---

## Headline

    figures transcribed   123
    claims written        123        (148 including regime claims)
    refused                 0
    decoys blocked          0        (1 admitted paired, 1 false positive fixed - below)
    persons                91
    seasons          1965-1986        15 distinct
    contests                1        genuine, retained

**Everything was hand-transcribed**, courts and newspapers alike. Regex-scraping
money out of a legal opinion is how a decoy gets in, and an automated parse of the
newspaper table misassigned players to the wrong position (below). Every row in
`dataset/extract/` carries the source's own words.

## By convention — and the shape is the finding

| predicate | n |
|---|---|
| `salary_base_plus_prorated_bonus` | **73** |
| `base_salary_year` | 21 |
| `signing_bonus` | 10 |
| `contract_total_stated` | 5 |
| `cohort_salary_average` / `_high` / `_low` | 5 |
| `reporting_bonus` | 2 |
| `salary_base` | 2 |
| `roster_bonus`, `option_year_pay`, `additional_compensation`, `amount_actually_paid`, `total_earnings_year` | 1 each |

**Three-fifths of everything held is on one convention**, and it is the one that
pro-rates signing bonuses — because the Dallas Morning News table is the single
largest source. **A naive average over "salaries" would be 59% one newspaper's
method.** That is precisely what §3.6b exists to prevent, and the counts make the
case better than the argument did.

## By regime, league and era

    rozelle       24 figures      article-xv    85      n/a (rival league)  12
    NFL          108              WFL           12      AFL                  2
    1960s         11              1970s         41      1980s               59

**Fifteen seasons between 1965 and 1986.** Densest at 1984 (55, the DMN table) and
1978 (21, Shapiro). Thinnest 1967–1971, where every figure comes from a court.

**The regime travels as its own claim** — 20 Rozelle-era, 5 Article XV stints
carry `governing_regime`. Rival-league contracts are marked `n/a`: the NFL regime
did not govern them.

## Five defects in my own instruments, all caught before shipping

**1. An undeclared money predicate sailed through.** `amount_actually_paid` was
not in `SALARY_CONVENTIONS`, and the bare-name check only refuses `salary`,
`pay`, `compensation`, `wage`. It would have entered unclassified. **Fixed by
requiring any money-shaped predicate to be declared** — and the new guard
immediately refused `weekly_pay_packet` in a test.

**2. I mis-filed two figures myself.** Heidel's *"$5,000 as additional
compensation"* and Gardin's *"$43,326 as a professional football player during
1971"* were both written as `contract_total_stated`. Neither is a contract total.
Now `additional_compensation` and `total_earnings_year`, both declared.

**3. The decoy check was too blunt on Kapp.** It blocked the $600,000 contracted
total outright. But **$600,000 and $154,000 are both real and describe different
things**, exactly as the master session said — the declaration was conflating
*false* with *easily misread*. Split into `not_compensation` (block) and
`requires_pairing` (**admit, but require the companion figure in the same case**).
Kapp's $600,000 is now admitted *because* `amount_actually_paid` $154,000 sits
beside it; remove the companion and it is blocked again, which was tested.

**4. A decoy fired on a real salary.** Ray Guy's **$150,000** punter salary in the
1984 table was blocked because a 1968 *agent's deposition estimate* in *Smith*
happened to be the same number. **A decoy is a figure in a document, never a
number in the abstract** — and $150,000 is a round number, an attractor, which is
the same precedent that rejected Manning's $600,000 as corroboration. Each decoy
is now scoped to its source and fires only there.

**5. Two contracts collapsed into a false contest.** Kapp's Minnesota deal
($300,000) and his New England deal ($600,000) were both filed on
`("person", p)` because neither carries a single season. Two instruments read as a
disagreement. **A season-less contract figure now takes a `("contract", person,
club)` subject.** The false contest disappeared; the real one remains.

## The one contest, and it is genuine

    base_salary_year  (stint, Hayes, Los Angeles Rams, y1974)
        $22,000   stated_by the court
        $26,000   stated_by the court

**Two alternative contracts signed the same day**, which is what the case is
about. Neither value chosen, both retained.

## The newspaper table: an automated parse abandoned

A coordinate-based parse of the UD page reconstructed **4 of 52 rows and
misassigned 2 of those** — Eric Dickerson to LINEBACKERS, Uwe von Schamann to
DEFENSIVE BACKS. The page is three interleaved columns and layout extraction puts
a heading from one column on the same line as a player from another. **A silently
wrong position is the failure this project keeps catching, so the table was read
instead.**

All ten position blocks are held: quarterbacks, running backs, wide receivers,
tight ends, offensive line, defensive line, linebackers, defensive backs, place
kickers, punters — **52 players, five or six per block.**

**Two rows carry `block_assignment: INFERRED`.** Dickerson and Wilder sit adjacent
to a neighbouring column's heading. They are assigned to RUNNING BACKS on three
grounds — they continue the block's descending sequence exactly (580,000 → 550,000
→ 500,000), both men were running backs, and the block is otherwise four entries
where every other is five or six. **That is an inference and it is labelled as
one.**

**And a correction to report 14:** the UD page is bylined *"By The Associated
Press"*, so the chain is **UD ← AP ← Dallas Morning News ← unnamed** — three
removes, not the two I reported. The same chain as the Pampa story.

## A new subject scope the extraction forced

A positional average is **neither a person's pay nor a league rule**, and it had
nowhere to live: person-money predicates refuse a league subject, correctly.

Added a **`cohort` scope** with `cohort_salary_average`, `_median`, `_high`,
`_low`, `cohort_size`. Person-money predicates refuse a cohort subject and cohort
predicates refuse a person, both enforced.

**This is the shape of the owed Management Council table** — position × service
year, high/low/average/median per cell. Building the scope now means that document
drops straight in if the Mackey records request is ever made. It currently holds
five figures: Shapiro's 1977 and 1978 league averages, and Dean's three
defensive-line cells.

## Redundancy earning its keep

The `bare salary refused` selftest reported "did not fire" — because **two
independent guards** now refuse a bare `salary`, and disabling one left the other
holding. That is the redundancy working, not a broken gate. The selftest now
disables both to prove the gate can fail. Same shape as the summary-layer audit
surviving my regex bug because the heading check was independent.

**10/10 gates pass. 10/10 fire when broken.**

## What the salary layer now covers

**Years:** 1965–1986, fifteen seasons. **Leagues:** NFL (108), WFL (12), AFL (2).
**Positions:** all ten of the newspaper's blocks for 1984; the court cases are
position-agnostic and name whoever was a party.

**What it does not cover:** no season before 1965; nothing between 1971 and 1974;
nothing after 1986; and **no rank-and-file players except the ones who sued.** The
newspaper tables are top-five-per-position lists, so the 1984 coverage is the
league's best paid and says nothing about a median.

**Not yet ingested:** the three survey-lineage articles (Cayman Compass 1986, LA
Times 1988, and the 2002 primer's series), which are the weakest provenance and
partly duplicate each other. Shapiro's positional *deltas* were deliberately left
out — they are year-on-year changes, not levels, and inventing a predicate to hold
them would invite them being read as salaries.
