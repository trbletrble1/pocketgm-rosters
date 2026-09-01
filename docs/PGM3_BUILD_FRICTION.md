# Build friction — what cost round trips on the 2000 build, and why

Written by the master session after 2000 shipped. The goal is fewer stops, not
fewer questions: a build session that asks is working correctly. What this
records is the subset of stops that were **avoidable**, and what made them
avoidable.

Three causes, in order of how much they cost.

---

## Cause 1 — the handoff contradicted itself, and the wrong half won

**This shipped a broken file.** It is the only failure in the 2000 build that
reached Ryan's hands.

Two statements sat in this document at the same time:

- line 864: *"each era is scaled so the median top-53 cap hit is 197.4M against
  a 280M cap"*
- the era-scaling precedent: *"the published files are not scaled to their
  seasons ... a defect nobody noticed. New builds should ship real numbers."*

The master session read the second, ruled real 2000 dollars, and confirmed the
resulting divergence as a *deliberate deviation* when the build session
correctly flagged it. The file went out with every team roughly $224M under the
cap and no financial pressure at all. Ryan found it by starting a season with
Green Bay.

**The measurement was already in the document and neither session ran it.**

### What to do about it

**When a build session finds two statements in conflict, that is an escalation
by itself.** It is not a judgement call to be resolved locally, and it is not
resolved by picking the more recent one. Both may be true about different
things — the PFR access rules turned out to be exactly that, one client blocked
and another not.

**And the resolution goes back into the doc as a measurement, not a preference.**
The payroll entry now reads $197.4M with the seven-file table beside it, because
a figure with its evidence attached cannot be contradicted by a later opinion.

---

## Cause 2 — conventions nobody had measured

Several stops were questions of the form *"what do the published files do
here?"* Every one of them was answerable in under a minute by reading the files,
and every one cost a round trip because the answer was written down nowhere.

The three from this build are now measured and recorded below. The general
rule that follows:

**Before asking about a convention, measure it across the published files.**
Report the measurement with the question. Where the files agree, that is the
answer and no ruling is needed. Where they disagree, the disagreement is the
thing to escalate, and the master session needs the numbers to rule on it.

This is not "guess instead of asking". It is the difference between *"what
should free agent salary be?"* and *"free agent salary is 0 in six of seven
files, 2021 is the outlier — confirm I follow the six?"* The second is answered
in one line.

### Measured conventions

**Free agent contracts.** `salary` is 0 for every free agent in six of seven
files. 2021 is the lone outlier and is the least-reviewed file in the archive.
`length` is 0 to match. `eSalary` is a genuine three-way split and does not
matter — the game recomputes it on import.

    1986 100%   2004 100%   2007 100%   2010 100%
    2013 100%   2017 100%   2021   0%   <- outlier

**Staff count.** Every team in every file carries **exactly 9 staff**: head
coach, two coordinators, special teams, three scouts, two physios. All 32 teams,
all seven files, no exceptions. A vacant real-world coordinator still needs a
body in the slot — promote the senior real assistant and record it as a
promotion in the `note` field. Never invent a name; that exception covers scouts
and physios only.

**Median team payroll, top-53 basis.** Effectively a fitted constant:

    1986 197,400,001   2000 197,399,997   2004 197,424,500   2007 197,426,500
    2010 197,428,500   2013 197,399,995   2017 197,400,004   2021 197,426,500

$29k of spread across the whole archive. Top-51 scatters by $1M and hides this,
which is why the convention read as arguable for so long. **The game's cap is a
fixed constant of about $280M and does not know what year it is**, so era-real
dollars produce a file with no cap pressure. Scale to the constant.

---

## Cause 3 — the good stops, which were not friction

The rest of the escalations were correct and should not be optimised away. They
share a shape: the build session hit something the docs could not have predicted
because nobody had ever looked.

- `PTSA` carries real contract signal for rookies and **none at all** for
  veterans, +0.500 against +0.020, with the pooled figure averaging them into
  something that looks usable
- Ceiling saturation — inflation compresses the top of the source range, so the
  trap positions arrive **pre-tied** and a quantile map silently discards the
  ordering
- The quantile *target* was contaminated: 1,622 published records parked on
  stamina 1

None of these could have been written down in advance. Each became a precedent
afterwards, which is the system working.

**A build session that stops on something genuinely undecided is not costing
time.** Every one of those three stops prevented a defect that no gate would
have caught.

---

## The pattern worth carrying

The avoidable stops all had the same root: **an answer existed in the data or
the docs, and nobody looked before asking.** Both sessions did this. The master
session asserted PFR provenance, a David Johnson citation, and an archive-wide
age defect, all three from recollection, all three wrong, all three caught by a
build session that measured.

So the rule is symmetrical and it is not about who asks:

**Measure first. Bring the number to the question.**

A question with a measurement attached usually answers itself, and when it
doesn't, it is answered in one line instead of four.
