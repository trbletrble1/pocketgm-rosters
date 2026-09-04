# Five more salary sources — and Mackey arrived

**2026-09-04. Report 19.** Follows report 18. Five files landed, not one; three
relayed sources did not.

---

## First: more arrived than the brief described

    1987-02-09.pdf                          the Buffalo survey — INGESTED
    1987_raiders_rams_salary_numbers.txt    the transcription — read, not yet ingested
    CASEMINE - MACKEY v. NFL (D.Minn. 1975) NEW
    CASEMINE - KAPP v. NFL (N.D.Cal. 1974)  duplicate of the HTML already held
    CASEMINE - Robertson v. NBA             confirms Ryan's finding

## Mackey is here, and it settles the owed question — negatively

**The published opinion contains two dollar figures and neither is a salary:**

- **$35,000** — Rozelle directing *"the Rams to pay to the Patriots the sum of
  $35,000 constituting Olsen's initial signing bonus and other expenses."* An
  **inter-club transfer payment**, the second instance after Kapp's $50,000.
- **$200,000** — *"The union was approximately $200,000 in debt during the 1974
  negotiations."* Union finance, not compensation.

**So the financial exhibits are not in the published opinion.** That is what the
OWED entry predicted and it is now confirmed rather than assumed: the ~400 trial
exhibits live in the case file at the National Archives, and the Archives request
remains the only route. **A negative result that closes a question.**

**One structural nuance worth keeping.** The Rams' payment is described as
constituting *Olsen's signing bonus* — so an inter-club transfer price could be
**calculated from a player's bonus and equal it exactly**. That makes the transfer-fee
decoy sharper, not weaker: the number can legitimately be both.

**Robertson confirms empty** — one dollar figure across 42 pages, as Ryan found.

## The Buffalo survey — 28 teams, and it is a FOURTH bonus treatment

    The Register (NJ), 9 February 1987, p.17, dateline BUFFALO
    "Jets top NFL salary list; Giants No. 11"

**Correction to the brief:** the document held is *The Register* carrying it, so
the chain is **Register ← Buffalo News ← NFLPA survey** — one remove further than
described.

**All 28 clubs captured, both columns.** Every headline figure in the relay checks
out: Jets highest base **$233,700**, Steelers lowest **$146,331**, 49ers highest
total **$259,709**, Broncos lowest **$145,097**.

### The inversions prove it is not the DMN convention

Two clubs have a *total* **below** their base — Cleveland by $2,404 and **Denver
by $51,233**.

**Addition cannot produce an inversion.** So the two columns are not (base) and
(base + bonus) over the same money, and treating this "total" as the Dallas
Morning News's `salary_base_plus_prorated_bonus` would have been wrong.

The source explains it: *"the discrepancy is attributable to bonus payments that
have long deferments."* And Newman's Appendix C corroborates the mechanism —
*"the Management Council pro-rates signing bonuses…; the NFLPA defers money to the
year it is received."*

**So there is now a fourth convention: `salary_base_plus_bonuses_nflpa`** — bonuses
included, attributed to the year received rather than pro-rated. Declared, with
the caution that **the exact arithmetic producing an inversion is not determinable
from the page** and should not be reconstructed.

**Population stated on the page**, and it matters: *"the average pay for all of a
team's players, even if the player spent the year on injured reserve and didn't
play."*

## Three sources did NOT enter, and that is the rule working

**The Elway/Williams comparison and Staudohar are `relayed`** — conversation text
with no document behind them. Under §3.7 they **cannot become claims**. Recorded
in `newspapers.json` under `_RELAYED_NOT_INGESTED` so the leads survive.

**The Elway lead is worth chasing for a structural reason, not its numbers**: the
**1987 strike deduction — 25% of base salary over 24 days for players who did not
cross**, Elway losing $250,000. If that holds, **every 1987 figure in every source
needs flagging as pre- or post-deduction**, which is a convention question, not a
figure question.

*(Also noted: Steve Watson's $700,000 was described as derived from "$300,000 more
than" Elway's $1 million. That is arithmetic on a relayed figure — two steps from
any document.)*

## The lineage ruling, recorded

**The Buffalo survey, the 1988 LA Times piece, the 1986 Cayman Compass piece, the
2002 primer and the NFLPA half of the 1982 hearing are all the NFLPA's own
survey.** One lineage group. Agreement between any two is **not** corroboration —
§4.3 counts lineage groups, and this was already proven when the primer and Newman
matched identically for 1971–1980, ten years running.

**The only non-NFLPA salary sources held are the fourteen court opinions and the
Dallas Morning News tables.** Written into `newspapers.json` as
`_lineage_ruling` so it is not re-derived.

## The Raiders/Rams transcription — read, deliberately not yet ingested

`acquisition: transcribed`, Ryan as transcriber, LA Times 23 August 1987. Forty-odd
players with **forward schedules**, which nothing else has.

**Not ingested yet, for a reason worth stating.** The file mixes **1985 team
aggregates with 1987 player figures** and says so; it flags **its own OCR
uncertainty** on Harrah's 1988 figure, Irvin's 1988 line and three "approx."
values. Ingesting it needs a per-row confidence field the extraction tables do not
yet carry, and forward-year schedules need a subject shape for *a future season's
contracted salary* — which is a different thing from a salary paid.

**Both are modelling decisions, not transcription work.** Doing them badly would
put a 1985 team average and a 1990 contracted figure in the same predicate as a
1987 salary paid.

## Where the salary layer stands

    claims        205        persons 92
    seasons       1965-1986, 15 distinct
    conventions   5 declared, THREE distinct bonus treatments
    gates         10/10 pass, 10/10 fire

    cohort/salary_base                     28    the Buffalo base column
    cohort/salary_base_plus_bonuses_nflpa  28    the Buffalo total column
    salary_base_plus_prorated_bonus        73    the DMN tables
    base_salary_year                       21    court contracts
    signing_bonus                          10
    ...

**The three bonus treatments, side by side, are the day's real gain:** pro-rated
(Management Council / DMN), as-received (NFLPA / Buffalo), and excluded entirely
(base only). **The Buffalo survey is the first source to give two of them over the
same population** — which is what would make calibration between them possible,
and is exactly why they must not be pooled first.

**Owed:** the Elway document, Staudohar, and a per-row confidence field before the
Raiders/Rams file can land.
