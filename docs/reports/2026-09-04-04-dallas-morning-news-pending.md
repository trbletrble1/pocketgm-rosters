# The Dallas Morning News piece — held, not fetchable, and blocked on one file

**2026-09-04. Report 04.** Follows 01 (1982 hearing), 02 (2002 primer), 03 (UPI
Dean). Durable changes in `DATASET_DESIGN.md` §3.7 and §9b, and a sharpened
precedent.

---

## The ask, first

**Put the scanned PDF in `pgm3-sources/`.** Nothing in this report can become a
claim until it is there.

The article reached this session as text in conversation. Under §3.7 that is
`acquisition: relayed` — **a lead, not a source.** Once the PDF is on disk it
becomes `held`, hash-pinnable, and the Acrobat text copy becomes a `transcribed`
reading of it with Ryan named as transcriber. Then the figures can be claims that
cite a file rather than a paste.

## What it forced in the model: §3.7, acquisition as a third axis

Ryan's framing was right — this is a third class. Not a verifiable URL, not an
unverified relay, but a document he holds, OCR-transcribed, with him as the
transcriber. The model had no name for it.

Three orthogonal axes now, and a source can be weak on any one independently:

| axis | question |
|---|---|
| **attribution** (§3.6) | who *asserted* it |
| **lineage** (§4.3) | which documents descend from which |
| **acquisition** (§3.7) | how faithfully the text reached *us* |

    fetched      URL, hash-pinned, reproducible          -> may enter
    held         a file in the source tree, hash-pinned  -> may enter
    transcribed  a reading of a held document            -> may enter, naming
                                                            transcriber + tool
    relayed      conversation text, no document behind it -> NEVER enters

**`relayed` earns its place by itself.** Four times today a figure or a repo fact
arrived as conversational memory and was treated as established, and each time it
was wrong or incomplete — the doc filenames, the two namesake cases, the Dean
dating, and this. Naming the state and giving it a rule turns a recurring
discipline failure into something the model refuses structurally rather than
something a session has to remember.

**And one guard I want on the record.** Ryan transcribing a document is **not** a
human verdict under §4.2. A verdict is a person adjudicating evidence; a
transcription is a person operating a lossy instrument. Conflating them would let
an OCR slip inherit rank 1 and outrank every source in the dataset.

> Transcription is an acquisition channel, never an adjudication.

## Plausibility pass on the relayed figures

Run now so the arithmetic is ready when the scan arrives. Benchmark is the
primer's 1981 league average, **$82,400** (report 02).

| figure | value | × league | reading |
|---|---|---|---|
| QB average | $160,037 | 1.94 | plausible |
| RB average | $94,948 | 1.15 | plausible |
| WR average | $85,873 | 1.04 | plausible |
| Denver, highest | $106,000 | 1.29 | plausible |
| Dallas | $89,170 | 1.08 | see flag 1 |
| Washington | $89,162 | 1.08 | see flag 1 |
| Philadelphia | $83,000 | 1.01 | plausible |
| NY Giants | $75,000 | 0.91 | plausible |
| Kansas City, lowest | $64,000 | 0.78 | spread 1.66×, plausible |
| Payton | $800,000 | 9.71 | high; he was at the top of the market |
| Manning | $600,000 | 7.28 | plausible — but see below |
| Ron Springs | $65,000 | 0.79 | plausible |

**The shape holds.** Positional ordering QB > RB > WR, team spread 1.66×, star
salaries an order of magnitude above the mean. Nothing here contradicts the
primer, which is a real if weak corroboration of the whole block.

### Three flags for the re-read

**1. Dallas $89,170 and Washington $89,162 differ by $8.** Possible. But adjacent
numbers in a column are exactly where a transcription slips, and an $8 gap between
two team averages is the kind of coincidence worth two seconds of checking.

**2. The 35.5% may not be on the same basis as the averages.**

    35.5% of $15.42M gross      = $5,474,100
    team average $89,170 x 53   = $4,726,010
    gap                         =   $748,090

Not necessarily a defect. The article's salaries **exclude performance bonuses and
playoff shares**; "spent on players" probably does not, and the gap is about the
right size for benefits and bonuses. **But the basis must be read off the page,
not assumed** — this is report 01's 1980-column lesson, where three cells failed a
check and the document was right.

**3. Howard Richards is quoted on a different basis from everyone else.**
$165,000 of which $105,000 signing bonus implies a **$60,000 base** — 0.73× league
on base, 2.00× on total. If the other named players are base-only, he is not
comparable to them.

He is also **the only component breakdown in any 1981 source this project holds**,
which makes establishing his basis worth more than the figure itself. A single
salary decomposed into base and bonus is the thing that would let a build
distinguish `salary` from `guarantee` for the era, and no aggregate can supply it.

## Manning at $600,000 — the match settles nothing

It matches the January UPI story exactly, which looks like the shared-ancestry
tell from report 02. **It is much weaker, and the difference is worth stating.**

That precedent turned on $68,900 — a figure no two independent surveys land on by
chance. **$600,000 is a round number and an attractor.** Contracts are negotiated
to round numbers and reporters round to them, so two genuinely independent sources
can arrive at $600,000 with no shared ancestry at all.

So the check has two parts, and the first was implicit until now:

1. **Is the figure improbable on its own?** $68,900 and $94,948 are. $600,000,
   $135,000 and $65,000 are not.
2. Only then does an exact match across a gap indicate shared ancestry.

**A round-number agreement is uninformative in both directions** — not
corroboration, not evidence of a common source. Recorded as such. The precedent in
`DATASET_PRECEDENTS.md` is sharpened accordingly.

## Provenance

    stated_by     Dallas Morning News (via AP)
    attribution   UNKNOWN — the paper does not say
    acquisition   transcribed (pending: currently relayed)

**Better than Dean's two removes**: a paper's own reporting, with a **stated
margin of error under $4,000** — which implies a survey the paper or AP conducted
rather than a document it was handed. But the origin is unnamed, so it **cannot be
tested for lineage** against the Management Council survey, and that is exactly the
test that mattered for the primer.

**The non-denial is weak evidence, not none.** Club spokesman Greg Aiello: *"I
don't even know if it's accurate."* A spokesman declining to contest specific
figures about his own club is worth recording and worth little alone.

**Definitional note that must travel with every figure from this source:** it
excludes **performance bonuses and playoff shares**. The primer and the hearing do
not use that basis. Comparing across the three without stating it manufactures a
disagreement out of a definition — the same failure as comparing salary-only
payroll against salary-plus-guarantee in the roster project.

## Disposition

| item | status |
|---|---|
| the scan itself | **NOT ON DISK — blocking** |
| positional averages, team averages, named players | `relayed`; become claims once the file lands |
| Richards base/bonus split | highest-value single figure here; establish its basis |
| Manning $600,000 corroboration | **rejected as uninformative** — round number |
| Dallas/Washington $8 gap | re-read |
| 35.5% basis | read off the page |

**Nothing extracted into claims.** One file unblocks all of it.
