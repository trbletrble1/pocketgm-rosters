# The summary-layer audit, a tested boundary rule, and Reynolds

**2026-09-04. Report 17.** Still scan-only. Three things: an audit of the earlier
extractions, a boundary detector that was tested rather than assumed, and
*Reynolds v. NFL*.

---

## 1. The audit: no earlier extraction is compromised

**Only the Cowan PDF carries a machine-summary layer.** Checked all 16 documents
for CaseMine's generated headings — `Legal Issues Presented`, `Arguments of the
Parties`, `Table of Precedents Cited`, `Court's Reasoning and Analysis`,
`Factual and Procedural Background`.

    Cowan PDF        all five headings present   -> summary layer
    everything else  none                        -> opinion only

Three CaseMine cases (Bergey, Heidel, Rudolph) carry the string `AMICUS`, but that
is the site's chat-widget branding in the page chrome, not a summary. **Every
figure reported in reports 14 and 15 came from opinion text.**

## 2. The boundary rule — proposed, tested, and failed three times before it held

The proposal was: *the opinion starts where a judge's name appears.* **Tested
against all 16 documents, that fails three ways**, and each failure is worth
recording because each would have cost something different.

| failure | case | what went wrong | cost if unfixed |
|---|---|---|---|
| **metadata field** | Cowan | `COPE, Judge` appears FIRST at offset 270 as CaseMine's `JUDGES` field, and again at 6099 as the real opening | you take the summary as the opinion |
| **citation inside the text** | Kapp | the LAST judge marker is *"Marshall, J. in Flood, supra"* — a citation, 41,000 chars into the opinion | you lose 98% of the case |
| **mid-document heading** | Gardin, Heidel | Tax Court puts an `OPINION` heading AFTER the findings of fact | **you cut off exactly where the money is** — Heidel's $50,000 bonus sits before it |

Two more, from my own instruments:

- The audit's first regex required a word boundary after `J.`, which never matches
  (`.` then a space are both non-word). **It silently dropped every California
  opinion** — Partee reported "no judge marker" while the text plainly reads
  `BROUSSARD, J.` The audit's *conclusion* survived because the summary-heading
  check was independent, but the column was wrong.
- The prose test required `[A-Z][a-z]` after the marker. Kapp continues
  `SWEIGERT, District Judge. THE RECORD` — all caps — so it failed.

**The rule that holds**, in `dataset/src/opinion_boundary.py`:

1. If a summary layer is present, take the text after the last `JUDGMENT` marker.
2. Otherwise take the **earliest** of: the first `OPINION` heading *that has a
   judge's name within 400 characters*, and the first judge marker **not** preceded
   by `JUDGES` and followed by a lowercase run.

**Result: 15 of 16 land on the judge's name; the 16th (Brown) lands on the
`OPINION` heading with a subtitle before the judge, which is also correct.** Two
documents correctly refuse — the Cowan captcha HTML, and the Super Bowl article,
which is not a case at all.

**The design principle, and it is the important half: err toward including chrome,
never toward excluding court text.** Including site furniture costs noise.
Excluding findings of fact costs the evidence. The Tax Court failure is the proof —
the "tidier" boundary was the one that would have thrown away Heidel's contract.

## 3. Reynolds v. NFL, 584 F.2d 280 (8th Cir. 1978)

    CASEMINE - REYNOLDS v. NATIONAL FOOTBALL LEAGUE.pdf
    11 pages, 216,192 bytes, 33,725 chars, bytes/char 6.4
    NO summary layer.  Opinion opens "GIBSON, Chief Judge."
    sha256 343f132c334807582c8f3b852f4a9c411d69e37b17701c8fb9d0f9197f9897a0

**No contracts, as expected — and a complete free-agency price schedule.**

### The qualifying-offer floor, by years of credited service

    < 4th year completed    $30,000
    < 5th year completed    $40,000
    each subsequent year    +$5,000

### The draft-compensation ladder, keyed on the size of that offer

    $50,000 - $65,000       one third-round choice
    ...
    $200,000 or more        FIRST-round choices in the two NEXT college drafts

A $50,000 offer is also the **threshold** below which no compensation is owed, for
a player who has not completed his seventh season — and that threshold rises with
service. The old club has **seven days** from an offer sheet to serve a
first-refusal notice, and all contracts expire **1 February**.

### And a fourth salary convention, defined by the CBA itself

> *The qualifying offer essentially refers only to monetary salary payments to be
> made for the player's services or as a bonus for reporting; **it does not include
> non-cash compensation or outside income possibilities.***

**A qualifying offer is a floor a club had to clear, never evidence of what anyone
was paid.** Filed beside real salaries it would read as sixteen players earning
exactly $30,000. Recorded as its own convention with that warning attached.

### The regime change, and why every contract must be read against it

Reynolds dates it precisely. The **Rozelle Rule** — the signing club compensates
the old club, with the Commissioner awarding compensation if they cannot agree —
was struck in *Mackey* (8th Cir. 1976, cert. dismissed 1977). **Article XV, "First
Refusal/Compensation", replaced it.**

And the court supplies its own measurement of the difference: **176 players played
out their options in eleven years under the Rozelle Rule**, against a far smaller
number under the new rule.

**So every contract in the case files needs reading against the regime operating in
its season** — Smith (1968), Heidel (1965), Kapp (1967–70) and Partee (1974–76) are
Rozelle-era; Overstreet (1983–86) and Brown (1989) are Article XV. Recorded as
`player_movement_regime`, a system predicate, so the dating travels with the
contracts rather than being remembered.

## Recorded

`dataset/declarations/salary_conventions.json` now holds **five conventions** and
**eight system predicates**. New in this pass: `qualifying_offer`,
`qualifying_offer_floor`, `draft_compensation_ladder`, `player_movement_regime`.

**Extraction order unchanged.** Courts first — now with the boundary detector in
front of them.
