# The Cowboys story read from the files, and what a second scan is worth

**2026-09-04. Report 05.** Follows 04, which logged this source as blocked.
It is now unblocked. Durable changes in `DATASET_DESIGN.md` §9b and a new
precedent.

---

## Two scans landed, not one

    Midland_Reporter_Telegram_1982_02_24.pdf   50pp  64,974,642 B  story p.29
      sha256 69c5ae755eb2d9555aa517cd15fb46631706cda2ec7b243a26f7efcaa08ec9e7
    Big_Spring_Herald_1982_02_24.pdf           30pp  48,956,755 B  story p.15
      sha256 8c745bc8541ac2b56c3899117b3d8c3a7bfb8887fe8b3e2c6b90cda731a27637

Both carry OCR text layers and read directly with `pypdf`. `acquisition: held`.
The Herald was not mentioned in the brief and turns out to be the more useful of
the two — not for its content, which is worse, but for what having two of them
makes possible.

## The chain, read off the page

The byline is **`DALLAS (AP)`**. The body: *"according to the Dallas Morning News.
In a story published Tuesday…"*

    the paper we hold  <-  AP wire  <-  Dallas Morning News  <-  UNNAMED

    stated_by     Midland Reporter-Telegram
    attribution   ["AP", "Dallas Morning News", <unnamed origin>]

**Three removes, as Ryan said**, and report 04's two-remove description was wrong.
The Morning News still does not say where its figures came from, so the chain ends
unnamed at the fourth position rather than resolving.

**Dating disagreement between the printings.** Both papers are dated Wednesday 24
February 1982 (the Herald's masthead: `WEDNESDAY, FEB. 24, 1982`). Midland says the
Morning News story was *"published Tuesday"* — 23 February. The Herald says
*"published today"*. Logged `contested`, leaning 23 Feb: Midland's is the specific
claim and the Herald's reads like an editorial substitution.

## What a second copy is actually worth

**For attribution and lineage, the two papers are one source.** Same AP wire.
Their agreeing tells you nothing about whether the Morning News was right, and
counting the Herald as corroboration would inflate a single source — the same
error as counting the 2002 primer against the 1982 hearing.

**For acquisition, they are two independent witnesses** — two physical papers, two
scans, two OCR passes over identical words. A free transcription check, and it
fired at once:

| figure | Midland | Big Spring | resolution |
|---|---|---|---|
| Dallas average | **$89,170** | `$80,170` | Midland |
| Washington | **$89,162** | `180,162` | Midland |
| Newhouse | **$145,000** | `$146,000` | Midland |
| Ron Springs | **$65,000** | `$66,000` | Midland |
| RB league average | **$94,948** | `$M,M8` | Midland |
| NY Giants | **$75,000** | `$^,000` | Midland |

**Neither cell was settled by preferring a scan.** Two independent things settled
them:

1. **The article's own logic.** It says Dallas *"was higher than any NFC East
   team"* and names Washington at $89,162 in the same paragraph. $80,170 puts
   Dallas below Washington and contradicts the sentence; $89,170 satisfies it.
   Same instrument as the percentage column that arbitrated the hearing's
   twice-printed table in report 01.
2. **The Herald's errors are a character-confusion class**, not noise — 5→6 twice,
   89→80/180 twice. A systematic fault identifies the bad instrument. **Averaging
   the two transcriptions would have been wrong**; identifying the worse one was
   right.

Written up as a precedent: *a syndicated story in two papers is one vote and two
witnesses*. It generalises past newspapers — wire copy, syndicated columns, a
table reprinted twice in one hearing, a press release carried by several outlets.
**One vote for what happened, N witnesses for what the page says.**

## Report 04's flags, resolved against the page

**1. The $8 gap is REAL.** Midland prints *"The average Cowboy salary of $89,170 …
The Redskins, for example, paid players an average $89,162"* — both in one
paragraph, in the source. Two team averages $8 apart is a genuine coincidence in
the underlying data, not a transcription slip. My flag was reasonable and wrong.

**2. The 35.5% basis is still unreadable**, and only the original Morning News
piece can settle it. The wire says the club *"spent 35.5 percent of its $15.42
million gross revenue in 1981 on player salaries"* and, separately, that the
reported figures *"did not include performance bonuses or the players' shares of
playoff money."* Whether the percentage is on the same basis is **not stated**.
The gap stands — 35.5% = $5.474M against $4.726M for 53 × $89,170 — and is about
the right size for the excluded items. **Unresolved.**

**3. Richards's basis mismatch is REAL, and the source discloses it.** The article
reports **base pay** explicitly: Danny White *"made $235,000 base salary"*, Pearson
*"got less in base pay"*. Richards is flagged as the exception — *"made $165,000 …
but $105,000 of it was a signing bonus"*, implying a $60,000 base. **The
inconsistency is the source's own and stated**, which is the good case. He remains
the only component breakdown in any 1981 source held.

**4. NEW — the article benchmarks against a league average it never states.**
*"31 of its 53 players less than the National Football League average"* and *"four
times the league average"* both rest on a number absent from the wire story.
Taking White's $375,000 literally as 4× implies ~$93,750 against the primer's
$82,400 for 1981, a 14% gap — though "four times" is plainly loose. **The Morning
News's own league average is not in this story**, which limits what the "31 of 53"
claim can be used for.

## Confirmed figures

Positional averages QB **$160,037**, RB **$94,948**, WR **$85,873**. Teams: Denver
**$106,000** highest, Dallas **$89,170**, Washington **$89,162**, Philadelphia
**$83,000**, NY Giants **$75,000**, Kansas City **$64,000** lowest. Named: Manning
**$600,000**, Payton **$800,000**, Randy White **$375,000**, Dorsett **$325,000**,
Danny White **$235,000** base, Richards **$165,000** incl. $105,000 bonus,
Newhouse **$145,000**, Hill and Johnson **$135,000** each, Pearson **$125,000**,
Springs **$65,000**. Club: 35.5% of $15.42M gross, 31 of 53 below league average,
margin of error under $4,000.

**Exclusions confirmed on the page and travelling with every figure: no
performance bonuses, no playoff shares.**

**Manning at $600,000 still settles nothing** — round number, attractor,
uninformative in both directions whatever it matches.

## The Shapiro article — logged as `relayed`, and its structure logged separately

Not on disk, so per §3.7 **nothing in it may become a claim yet**. Logged now
because its *structural* content is evidence about the owed document.

**It states the owed table's dimensions, from a witness holding it:**

> *The Management Council also broke down salaries from first-year players to
> 20-year players, by position, listing the highest salary paid, the lowest salary
> paid, the average and the median salary.*

Position × service year, 1st through 20th, **four statistics per cell — high, low,
average, median.** The hearing proved it existed; Dean's agent read one cell aloud;
this names the axes.

**It also splits the document into two halves with different survival odds**, which
sharpens the debt:

| half | released? | where to look |
|---|---|---|
| averages and medians by position | **public** | contemporary press, 1978–82 |
| the service-year breakdown | **withheld** | Management Council papers, agent files, arbitration and litigation discovery |

**The public half is what the UPI method reconstructs. The withheld half is the
actual debt** — and Dean's agent quoting six-year figures at a press conference
proves copies reached agents, so agent papers and contract-dispute discovery are
the live routes.

**Two more things worth having, when the scan lands:**

- **The author declares his own derivation** — *"Using those figures (which were
  not made public), previously published salary estimates and interviews with
  several highly placed NFL sources, it is possible to deduce…"* That is
  `source_derived` **announced by the source**, better than the 2002 primer's
  silence and better than most of what this project holds. Three provenance tiers
  inside one article, marked by the author, with Blount and Talbert explicitly
  hedged (*"is believed to have earned"*) — per §3.6 each tier gets its own
  attribution and the hedged pair must not be flattened into the rest.
- **Garvey on the Management Council's figures:** *"on the whole are accurate. I
  have no reason to doubt them."* **The opposing party declining to dispute them.**
  It is not a League-original source and does not discharge the debt — but it is
  the same two organisations a year before the hearing, and a concession is
  evidence of a different and stronger kind than either party's own assertion.

## Disposition

| item | status |
|---|---|
| Cowboys story, all figures | **held**, `source_derived`, 3 removes, unnamed origin |
| Dallas/Washington $8 gap | **resolved** — real, in the source |
| Richards basis | **resolved** — source discloses it |
| 35.5% basis | **unresolved** — needs the original DMN piece |
| DMN's own league average | **absent from the wire story** |
| Shapiro article | `relayed` — scan owed before any figure is used |
| owed table's dimensions | **known**, and the debt now splits in two |
