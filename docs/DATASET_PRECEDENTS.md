# Dataset project — rulings and precedents

Companion to `DATASET_DESIGN.md`. **Neither file belongs to the PGM3 roster
project**; both are parked here to be read and move to the new repo when it
exists.

Started 2026-09-04. **Ruled the same day: these stay here.** The argument for
keeping all method precedents in one place is real and was outweighed — this is a
different project with a different lifecycle, and `PGM3_PRECEDENTS.md` is about
*building files* where this is about *representing knowledge*. **Cross-reference,
do not merge.**

Where an entry here extends or generalises a roster-project precedent, it names it
inline rather than restating it.

---

## A failing check is not automatically an instrument error

Found 2026-09-04 verifying the OCR of a 1984 scan of a 1982 congressional
hearing, before trusting any figure read out of it.

The table — NFL financial summary, 1966–1980, per average club — carries a
percentage-of-revenue column beside every figure, so every cell can be checked
against its own row total. **49 cells, 45 pass, 4 fail.** The obvious reading is
four OCR errors.

It is not. A second, independent check separates them:

| | % check | additivity (`player + other = total`, `income − total = profit`) | verdict |
|---|---|---|---|
| 1975 total player cost | fails | fails | **OCR** — the same table printed twice reads 1,063 on one page and 1,863 on the other; `4,825 × 38.6% = 1,862` and `1,661 + 202 = 1,863` |
| 1966 AFL other expense | fails | fails — the only column that does not balance | **OCR** — reads 1,119; both checks imply 1,009 |
| three cells in the **1980** column | fail | **both identities hold** | **NOT OCR** |

The 1980 column carries footnote 3: *"Final 1980 figures are in preparation.
Estimate based on results of large majority of clubs and projections."* It is an
estimate assembled from a partial sample, so its parts do not reconcile against
its percentages — **in the original document, in 1982, before any scanner
existed.**

**The rule: when a check fails, establish whether the defect is in your reading
of the source or in the source itself, before repairing anything.** "Correcting"
the 1980 cells to satisfy the percentage column would have manufactured a
precision the document explicitly disclaims, and would have destroyed the only
signal that the column is an estimate.

**The instrument that separates them is a second check with a different
mechanism.** One check tells you a cell is wrong. Two checks that disagree with
each other tell you *where* the wrongness lives. The percentage column and the
additivity identities are independent — the first tests a cell against a row
total, the second tests columns against each other — and it is precisely their
disagreement on the 1980 column that is informative.

Same family as the roster project's *"measure before explaining"* and *"confirm
the defect is present before fixing it"*, with the addition that a source can be
internally inconsistent and correct at the same time, because it said so.

**Corollary for the dataset:** a document's own statement of its uncertainty is
data. Footnote 3 is a claim about the 1980 column's reliability, from the
document, and it should be stored as one rather than discovered again by the next
session that runs an arithmetic check.

---

## A source that states a number it computed is not a source that observed it

Recorded 2026-09-04. This is the same finding arriving from a second direction on
the same afternoon, which is why it is a precedent and not a note.

`DATASET_DESIGN.md` §3.3 originally had four claim kinds and assumed that if a
credible document states a number, the document *observed* it. Two cases refute
it:

1. **The 1980 estimated column above.** The document says it is a projection.
2. **The NFLPA's average coaching salary**, same hearing, printed p.60: an
   average club spends ~$505,000 on coaches — built from an assumption of *"nine
   assistant coaches at approximately $45,000 each"*. The **count** is plausibly
   an observation of 1980 practice. The **flat rate is the NFLPA's estimating
   fill**, and the NFLPA is a party to the dispute the hearing is about.

Taken as `observed`, the second imports an interested party's estimating
convention as measured structure — a nine-way flat distribution that nobody
measured. That is the roster project's *"a safe default is still a claim"*
precedent arriving from **outside** the project: someone else's fill, inherited
because their document looked authoritative.

**The rule: a claim is `observed` only where the source is reporting, not
reckoning.** If the source shows its arithmetic, footnotes an estimate, or states
an average it computed itself, the claim is `source_derived` — quotable, usable,
and never mistaken for a measurement.

**This is the general form of the `era_certain` failure.** There, a field named
for a conclusion was a null check, and three documents told sessions to trust it.
Here, a figure that reads as a fact is a computation. Both are the same mistake:
**taking the confidence a value is presented with, instead of the confidence its
derivation supports.**

---

## Implausibility is a signal about your method before it is a signal about the data

Found 2026-09-04, and it is the fourth instance of this shape in one session.

Counting dollar amounts in the extracted text of a financial hearing returned
**one `$` in 1.8 million characters**. That is not a plausible property of a
document about player compensation, and it was reported as a likely OCR defect —
"dollar amounts may not survive extraction".

It was a regex bug. `$` is an end-of-string anchor, so `re.findall('$', text)`
matches once, at the end. The real count is **423**.

**The finding was caught before it reached a conclusion**, because the
implausibility was treated as a question rather than an answer, and the next
action was to look at the surrounding text rather than to write up the defect.
The very next check printed the context of five "average salary" hits, every one
of which contained a dollar figure.

**The rule: when a measurement is implausible, suspect the measurement first.**
The instrument is new and unverified; the document has existed for forty years.
Ordering the suspicion that way costs one check and saves a wrong finding that
would have read as authoritative, since "the OCR loses dollar signs" is exactly
the kind of caveat a later session would inherit and never re-test.

Sits between two existing roster-project precedents and sharpens both. *"Point a
suspect instrument at data whose answer you already know"* is the preventive
version. *"An anchor that FAILS for the wrong reason is worth more than one that
passes"* is what happened here — the failure was informative precisely because it
was too extreme to be real.

---

## A negative result about a source is worth as much as a positive one

2026-09-04. The hearing was searched for positional and years-of-service salary
data — the granularity an export actually needs. It has none.

But the search returned something better than a blank: the volume reproduces CBA
language **describing** an annual NFLMC→NFLPA compilation giving average salary
"compiled by team positions and years of service", with the highest and lowest
salary for each position.

**The document proves the existence of a better document without containing it.**

Recorded as an absence claim rather than as a gap, per `DATASET_DESIGN.md` §3.4:
*this source was searched, for this, on this date, with this result.* A later
session that wonders whether anyone checked the 1981–82 hearings gets an answer
instead of repeating the search, and the lead is attached to the answer.

The roster project's canonical instance of the same shape is two mentions of
"salary" in 9.4 million characters of media guide text, both prose — a
measurement that lived in a document as a sentence. Here it lives in the store as
claims.

---

## A document-level provenance statement does not cover the claims beneath it

2026-09-04, found in the *NFL Economics Primer 2002* while establishing whether
it was usable.

Its cover carries one sentence of provenance for 164 pages: *"All salary data in
this report comes from the NFLPA Salary Cap Information System."* That reads as a
complete answer to "where did this come from", and it is why nobody would think
to ask again.

**It cannot be true of most of the document.** The salary cap began in 1994. A
cap information system is not the origin of a 1933 average salary, and the primer
elsewhere calls that figure *"an estimated 1933 actual average NFL salary of
$8,000"*. The sentence describes **the system the author read from**, not where
each value came from — which is the `registry-1986` failure exactly, arriving
from outside the project instead of inside it.

**The rule: provenance attaches to a claim, never to a document.** A source-level
statement is a claim *about the source*, and it is inherited by nothing. Every
value still needs its own origin, and where a source cannot supply one the value
is `source_derived` — not `observed` on the strength of a cover line.

**Practical form:** when a source states its provenance once, globally, test that
statement against the oldest and least likely value in it. One check. Here it
took a single question — *did the salary cap exist in 1933?* — to turn a document
that appeared fully sourced into one that cites nothing.

---

## Two documents from one office are one vote

2026-09-04. The 1981 congressional hearing gives an NFLPA average salary of
**$68,900** for 1979. The *NFL Economics Primer 2002*, pulled from a different
place on a different day, gives 1979 as **$68,900**.

Twenty-one years apart, different authors, same figure — and it would be entirely
natural to read the second as independent corroboration of the first, especially
since it arrived separately and looked like a different kind of document.

**It is the same organisation restating its own position.** NFLPA Research in
2002, NFLPA Research under Garvey in 1981. In the dispute the hearing records —
NFLPA $68,900 against the League's $93,333 — promoting this to two-against-one
would let one party's standing position outvote the other by being written down
twice.

**The rule: `derived_from` is declared on the source, and consensus counts
lineage groups.** This is the roster project's *"agreement across files is not
independence — four JINX files agreeing is one vote"*, generalised from files
that copy each other to **institutions that restate themselves**. The second form
is harder to see, because the documents genuinely are different documents.

**The tell that worked:** an exact match on an unusual figure across a long gap.
Two independent surveys of 1,500 contracts would not both land on $68,900.
**Suspicious agreement is evidence of shared ancestry**, and the check is to look
for the office rather than the file.
