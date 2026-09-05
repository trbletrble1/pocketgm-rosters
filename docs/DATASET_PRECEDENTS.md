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

**SHARPENED 2026-09-04, and the sharpening matters.** The tell requires the figure
to be **improbable under independent generation**. $68,900 is: no two surveys land
there by chance. **A round number is not.**

The Dallas Morning News piece reports Archie Manning at **$600,000**, matching a
January UPI story exactly — which looks like the same tell and is not nearly as
strong. Round numbers are **attractors**: contracts are negotiated to them,
reporters round to them, and two independent sources can arrive at $600,000
without any shared ancestry at all.

So the check has two parts, and the first was implicit:

1. **Is the figure improbable on its own?** Count the significant digits and ask
   whether the value is a natural resting place. $68,900 and $94,948 are not.
   $600,000, $135,000 and $65,000 are.
2. Only then does an exact match across a gap indicate shared ancestry.

**Consequence: a round-number agreement is not corroboration and not evidence of
shared ancestry — it is uninformative in both directions**, and should be recorded
as such rather than counted either way. The honest reading of Manning at $600,000
in two papers is that it settles nothing about their independence.


---

## A syndicated story in two papers is one vote and two witnesses

2026-09-04. Two scans arrived of the same day's news: the *Midland
Reporter-Telegram* and the *Big Spring Herald*, both 24 February 1982, both
carrying the same AP wire story about Dallas Cowboys salaries.

**The instinct is to treat the second as corroboration. It is not** — for content.
Both are the same wire, so for **attribution** and **lineage** they are a single
source, and their agreement says nothing about whether the Morning News was right.

**But for acquisition (§3.7) they are two independent witnesses** — two physical
papers, two scans, two OCR passes over the same words. That is a free
transcription check, and it fired immediately:

| figure | Midland | Big Spring |
|---|---|---|
| Dallas average | **$89,170** | `$80,170` |
| Washington | **$89,162** | `180,162` |
| Newhouse | **$145,000** | `$146,000` |
| Ron Springs | **$65,000** | `$66,000` |

**The rule: the axes are independent, so ask which one a second copy helps with.**
A second printing of a syndicated story adds nothing to the evidence and a great
deal to the transcription. Counting it as corroboration inflates a single
source; ignoring it throws away the only cheap check available on a lossy scan.

**Two things settled the disputed cells, and neither was preferring a scan:**

1. **The article's own internal logic.** It says Dallas *"was higher than any NFC
   East team"* and names Washington at $89,162 in the same paragraph. $80,170
   would contradict that sentence; $89,170 satisfies it. Same instrument as the
   percentage column that arbitrated the 1982 hearing's twice-printed table.
2. **The error pattern is systematic, not random** — 5→6 on two figures, 89→80/180
   on two more. A character-confusion class identifies the faulty instrument, where
   scattered disagreement would not. **Averaging two transcriptions would have been
   wrong**; identifying the worse one was right.

**Generalises past newspapers.** Wire copy, syndicated columns, a table reprinted
in two volumes of one hearing, a press release carried by several outlets — all
the same shape. **One vote for what happened, N witnesses for what the page says.**

---

## A gate that fires must fire for its stated reason — the exit code does not tell you

2026-09-04, building the first real-data gate.

The gate asserts that all four resolution bases are reachable in the built corpus.
To prove it could fail, it was run against NFL 1950 alone, where the distinction
is known to be absent. **It exited 1.** That looked like the gate failing
correctly, and it was one line from being written up as a verified selftest.

It was a `ModuleNotFoundError`. The variant had been copied to `/tmp` and could no
longer import `resolve_store`. **The gate never ran at all.**

**This is the roster project's *"an anchor that FAILS for the wrong reason"*
arriving in the gate layer, and it is worse there**, because a gate's whole
contract is its exit code. Everywhere else a wrong-reason failure produces a
confusing result someone investigates. Here it produces the *expected* result and
closes the question.

**The rule: a selftest must assert on the gate's stated failure, not on its exit
status.** Read the message. The correct run prints:

    FAIL: no single predicate shows BOTH unknown and absent.

and that sentence — not the `1` — is the evidence the gate works.

**Corollary, and it is the practical form:** run the broken variant **in the same
environment as the real one**. Copying a check somewhere else to break it changes
two things at once, and the exit code cannot distinguish them.

**Both halves of the discipline are now needed.** `gate_selftest.py` proves a gate
*can* fail; this precedent says the proof is only good if the failure is the one
the gate was written to detect. A gate that cannot fail reports success; a gate
that fails for the wrong reason reports a successful selftest.

---

## A distribution over subjects-that-have-claims can never report "unknown"

2026-09-04, first resolution pass over the ingested 1950 and 1974 seasons.

Every predicate reported **`unknown: 0`**. On WFL 1974 that is not credible —
report 06 measured games-played fill at 14.9% for that league, so most players
should have no games-started value at all.

The data was fine. **The resolver built its subject list by iterating the claims**,
so a subject with no claim for a predicate was never enumerated, and the one basis
that means *"nothing was ever claimed here"* was unreachable by construction.

**The fix is a subject universe: the store records what EXISTS, not only what is
claimed.** `declare_subject()` is called for every person, person-season and stint
the ingest sees, and resolution enumerates that universe rather than the claim
index. With it, WFL games-started returns 64 observed, 756 absent and **81
unknown** — the 81 being the two teams whose pages carry no `GS` column at all.

**The general form: any measurement whose denominator is derived from its
numerator's source cannot detect absence.** Same family as the inventory that
found zero unreferenced entries because it named them in order to flag them, and
as the count assertion that is dead wherever a fallback tops up the total. Three
instances in one day, all the same shape — **the population must be established
independently of the thing being measured.**

**The tell was an implausible zero**, and it was treated as a question about the
instrument rather than a fact about the data. That ordering is the only reason it
was found.

---

## A consumer's gates encode its own era, and a historical build fails them for being historical

2026-09-04, exporting NFL 1950 to PocketGM 3 and running the roster project's own
validator against it.

Fourteen check groups failed on the first run. After fixing every defect in the
export's invented values — appearance tokens, jersey collisions, the contract
ladder, guarantee tracking remaining length, payroll scaled to the engine constant,
and attribute levels drawn from the reference — **four remained, and not one of
them is a defect in the file:**

| gate | reads | 1950 fact |
|---|---|---|
| `team count != 32` | 19 slots empty | the NFL had **13 clubs** |
| `roster under 45` | 13 clubs short | the 1950 roster limit was **32**; median exported roster is 33 |
| `CB/S ratio 2.92 outside 1.11-1.13` | far too many corners | the 1950 secondary is two **defensive halfbacks** and one safety |
| `team empty at a position every reference fills` | no K, no P, no MLB | only **9 of 13** clubs listed a punter; the 5-2 front used a **middle guard**, not a middle linebacker |

**Every one of those gates was fitted on files from 1986 to 2026.** They encode
modern football's positional structure and roster size, and they are correct for
the population they were built on. Pointed at 1950 they measure the era and report
it as failure.

**This is report 06's per-league finding arriving on a second axis.** There, a
completeness gate scoped per era read the WFL as catastrophically broken because
games-played fill is a property of the *league*. Here, positional gates scoped
across all files read 1950 as broken because positional structure is a property of
the *era*. **Same shape: a gate applied to a population it was not fitted on
manufactures findings.**

**The rule: a gate carries the population it was fitted on, and refuses — or
widens its band — outside it.** Not "turn the check off for old files", which
loses the check. The band for `CB/S` in a five-man-front era is a different band,
and it has to be measured on that era rather than inherited.

**And the split is the useful output.** Fourteen failures became four, and the four
are *the interesting ones* — they are a list of the ways 1950 football differs from
modern football, produced automatically by pointing a modern instrument at it.
**A gate that fails for a structural reason is a measurement, provided you do the
work to separate it from a gate that fails because the file is wrong.** Reporting
"4 failures" without that separation would have been worthless in both directions.

---

## A contest can be the symptom of an under-specified predicate

2026-09-04. §8.4 held a contest the design called unresolvable in principle: the
NFLPA's **$68,900** against the League's **$93,333** for the same 1979 season, two
interested parties, no external arbiter. The right handling looked like
`contested` forever.

A third document — Newman's 1987 law review article — carries the note that
explains it:

> *the Management Council pro-rates signing bonuses by the number of years a player
> is under contract; the NFLPA defers money to the year it is received*

And the hearing itself, on the same page as both figures, gives each side's
definition: the NFLPA counts salary plus deferred pay plus non-performance
bonuses; the League divides a total that **also includes medical, workmen's
compensation, payroll taxes, retirement, insurance and pre/post-season pay**.

**They were never answering the same question.** One is money a player receives in
a year; the other is what a club spends per player, benefits included, bonuses
spread.

**The rule: before recording a contest, check that both claims share a predicate.**
Two numbers under one label may be two measurements of two different quantities,
and `contested` then hides a modelling error rather than an evidential one — it
looks like honesty about the world while actually being vagueness in the schema.

**The tell is a disagreement that is large, stable, and signed** — the same two
parties differing by the same rough factor across years, rather than scattering.
Genuine evidential contests scatter; definitional ones hold their shape.

**And splitting is not resolving.** `average_salary_money_received` and
`average_player_cost_prorated` are now two predicates, and each has a single
uncontested value. What remains contested is a *different* question the split
exposed: Newman says the 1977–1981 figures were compiled by the Management
Council, and the hearing says the 1979 figure came from the NFLPA's own review of
1,500 contracts. **Two documents disagreeing about the provenance of one number
is a real contest**, and it survived precisely because the definitional layer was
peeled off first.

---

## Some predicates are set-valued, and treating them as single-valued manufactures contests

2026-09-04, first coaching ingest. Resolution reported **344 contested role
titles** out of 2,433 stints — a 14% contest rate on the predicate the media-guide
declaration calls that source's strength.

**All 344 came from a single source**, and the samples explain themselves:

    Buffalo 1990   ['Pass Game Coordinator', 'Quarterbacks']   sources=['coaching-tree']

Coaching Tree returns `roles` as a **list**. A coach holding two jobs in one season
is not two sources disagreeing; it is one source stating a set. The ingest emitted
one claim per element and the resolver, which assumes a subject holds one value per
predicate, read them as competing.

**The rule: a predicate declares whether it is single- or set-valued, and
set-valued predicates UNION within a lineage group.** They contest only when two
independent groups assert *different sets*. With `role_title` declared set-valued,
344 contests became **zero**, and the one contest that remained was real — a
compiler stating Red Grange's coaching lineage two different ways on two rows.

**Why this is the same family as the other instrumentation bugs found today**: a
false contest is the mirror of a vacuous pass. A gate that cannot fail reports
success; a resolver that cannot represent multiplicity reports disagreement. **Both
are the model failing to express the world and blaming the data.**

**And the tell was the rate.** Fourteen percent of a predicate contested, from one
source, with no second source present, is not credible — a contest needs at least
two voices and there was only one. **Check the source count before believing a
contest**; a single-source contest is either a source disagreeing with itself,
which is rare and interesting, or a modelling error, which is common and dull.

*Open, and honestly the same shape: the 11 contested positions in NFL 1950 are
mid-season movers listed differently by their two clubs, and they were written to
`person_season` scope. On the **stint** they are two single values and no contest
exists at all. Whether position belongs on the stint, the person-season, or both
is a scope question that has not been ruled — and until it is, those 11 should be
read as a scope artifact rather than as evidence of anything.*

---

## Make the wrong thing inexpressible, not forbidden

2026-09-04, recording the three salary conventions as a hard rule.

The DocDump scan (report 14) found three incompatible conventions in the sources,
and the §8.4 revision (report 11) had already shown that pooling two of them
manufactured a contest that looked factual and was definitional:

    salary_base                        base only - "contracts stripped of
                                       bonuses or incentives"        (NFLPA survey)
    salary_base_plus_prorated_bonus    base + reporting + roster + signing bonus
                                       spread over the contract      (DMN / NFLMC)
    club_cost_per_player               total club spend / headcount, INCLUDING
                                       medical, taxes, retirement    (the League)
    compensation_component             each itemised contract line as its own
                                       predicate                     (the courts)

**The obvious response is a rule: "never pool salary conventions."** That is a
convention someone has to remember, and this project's own precedent says a
convention that must be remembered is a defect waiting for the session that does
not remember it.

**What was done instead: there is no predicate called `salary`.** The convention is
part of the predicate NAME, and the store *refuses* `salary`, `pay`,
`compensation`, `wage` and `average_salary` at ingest with a message naming the
alternatives. Two figures on different conventions cannot be compared because they
are not the same predicate — pooling is not forbidden, it is **not expressible**.

Same move as a person having no name (§2.3): the failure mode is removed from the
type system rather than added to the documentation.

**It found a live instance immediately, in my own test suite.** Gate 7 — the one
proving an attributed claim cannot vote as the attributed party — used a bare
`salary` predicate to compare the League's **$93,333** against the NFLPA's
**$68,900**. Those are `club_cost_per_player` and `salary_base`: **the §8.4 error,
embedded in a gate written to catch a different error.** The new rule refused it on
the first run.

**And the selftest reproduces the symptom exactly.** Breaking the rule — an ingest
that strips the convention off the predicate name, which is how this happens in the
wild — makes the gate report:

    salary_base resolved contested/None

**A false contest, which is what §8.4 looked like for a whole day.**

**The general form: when two things must never be combined, prefer a design where
combining them is a type error over a design where it is a policy violation.** The
cost is a longer predicate vocabulary. The benefit is that the rule cannot decay,
and it audits the existing corpus for free.

*Corollary recorded with it: five figures in these sources look like salaries and
are not — a court's free-market estimate, an agent's deposition estimate, a treble
damages award, a refused counter-offer, and a contracted total of which a fraction
was paid. They are listed in `declarations/salary_conventions.json` so the next
session meets them as data rather than rediscovering them.*

---

## An empty result and a failed one are the same bytes

**Fourth instance, 2026-09-04.** Four times now, in four different mechanisms, an
absence has been indistinguishable from a breakage:

1. **archive.org 302** — a redirect to a login page, saved as a document. Recorded
   in the original handoff.
2. **The zero-byte cache** — `open(path,"wb")` ran before `urlopen()`, so a DNS
   outage created ~700 empty files that the cache then served forever as valid.
   28 NFL seasons read as "0 teams" and nothing objected.
3. **`<tbody><td>` with no `<tr>`** — a regex that dropped every per-year row.
   The conclusion nearly drawn was "1950 has no statistics."
4. **13 team pages that parse to zero rows** while a league page links them —
   CFL 1945–54 and the two WFL-1974 mid-season relocations. They contributed
   nothing, and contributed it silently.

Adjacent, same family: `AFL2 1936` and `NFLE 1997` render a league page and list
no rosters; `CFL 2020` renders and lists no teams, because the season was
cancelled. Both look exactly like a fetch that went wrong.

**The rule: nothing may report an absence it did not expect.** An empty result is
only information when something declared what a full one looks like. Concretely,
three obligations:

- **A fetch layer must never be able to cache a failure.** Fetch first, refuse
  empty, write atomically. The cache is the thing that turns a transient failure
  into a permanent fact.
- **A parse that returns nothing must say so, loudly, against a declared
  expectation.** Zero rows from a page a league links is a *deviation*, not a
  nullity. It is now recorded per league-season in
  `statscrew.json.empty_roster_pages`.
- **A real absence must be declared before it is met, or refused when it is.**
  `CFL-2020` is declared as a season not played; the ingest exits with that
  reason rather than reporting a match-rate failure that invites a retry. A
  retry would fetch the same empty page forever.

**The tell to watch for is a suspiciously round success**: 100% fill, 0 errors,
0 rows. Three of the four above announced themselves as clean results. The
denominator defect found the same day is the same shape once more — `100%` was
true, and it was computed over nothing.

---

## A declaration in the wrong place is not a declaration

**Third instance, 2026-09-04, each in a new shape.**

1. A declared value **computed and never referenced** (`JERSEY_USABLE`,
   `GP_LEAGUE_RATE`).
2. A declared value written to the right file, **the wrong block** — CFL
   predictions under a new top-level `cfl` key while the ingest reads
   `field_availability`. All 80 seasons reported *"declaration makes NO
   prediction"*.
3. A fact recorded as **prose that nothing enforces** — `league_codes` documented
   that `AFL3` is the Arena Football League, a different sport that parses
   without complaint. Documenting it did not prevent it.

Each was found by reading the code. None would have been found by a check,
because there was no check. There is now: `src/gate_declarations_are_read.py`
asserts that every declaration key is read by something in `src/`.

**Run against the existing declarations it failed on 107 of 176 keys** — the
majority of what was written as declaration was note. Wiring the enforceable
ones brought it to zero, and the exemptions live **in each declaration** under
`_documentation_only`, not in the checker, so widening one shows up in a diff.

**The worst case it exposed:** `model.py` duplicated the salary conventions as
Python literals instead of reading `salary_conventions.json`. A convention added
to the declaration was still refused — and the refusal message read *"Add it to
declarations/salary_conventions.json"*, naming a fix that had no effect. The
hardcoded system-predicate list had drifted to five entries against the
declaration's nine.

**The general form: a declaration is defined by being read, not by being
written.** A file that describes policy nothing consults is documentation with a
misleading filename, and it is more dangerous than no file, because the next
person assumes the ingest honours it.

*Corollary: the read-check is a string-literal grep, which is a proxy. It cannot
see a key that is read and then ignored — only one that nothing so much as names.
That is the failure it exists to catch, and the limit is stated in the gate.*

---

## A figure presented at a confidence its derivation does not support

**Third instance, 2026-09-04, and the three form a ladder.**

1. **The 1980 hearing's estimated column.** The document *says* it is a
   projection. Reading it as measurement takes a stated caveat and drops it.
2. **The NFLPA's flat $45,000 per assistant coach**, same hearing. The word
   *"approximately"* is right there, and the flatness is the tell: nine men at
   an identical salary is an estimating fill, not a distribution. The *count* —
   nine assistants — is plausibly a real observation of 1980 practice. One row,
   two confidences.
   *(Adjacent, same family: a `qualifying_offer` is a floor a club had to clear.
   Filed beside real salaries it would read as sixteen players earning exactly
   $30,000 — a number nobody was paid.)*
3. **StatsCrew's passer rating for 1950.** Green Bay 1950 lists Tobin Rote at
   **26.7**, Paul Christman at **49.2**. The formula was adopted in **1973**.
   Nobody in 1950 knew these numbers and no 1950 document states them.

**The ladder is in how much the source tells you.** The first announces itself.
The second hedges. **The third says nothing at all** — no footnote, no hedge, no
formatting difference. Rote's 26.7 sits in the same row as his 224 attempts, and
the attempts *were* counted in 1950. One row, one format, two epistemic statuses,
and the source draws no line between them.

So the third is the one that ships. The first two are caught by reading the
document; the third can only be caught by asking a question the document does not
prompt: **could this source have observed this, in this year?**

**The rule, and it is checkable:** where a measure has a date of introduction, a
value for a season before that date cannot be `observed`. It is `source_derived`
— someone's calculation, recorded as theirs.

`src/gate_anachronism.py` enforces it, driven by
`statscrew.json :: stat_columns.measure_introduced`. Constructed against the real
case — Rote's 26.7 filed as observed — it fires, while `Att=224` and `Yds=1231`
in the same store correctly pass. Refiled as `source_derived`, it passes.

*Recorded with its own limit: the gate is only as right as the declared year, and
1973 is currently general knowledge rather than a citation from a held document.
The declaration says so where the year is written, because a gate resting on an
unsourced fact is itself a figure presented at a confidence its derivation does
not support.*

**Corollary — the arithmetic columns.** `Comp %`, `Yds/Att`, `TD %`, `Int %` have
no introduction date because they never needed one: they are arithmetic on two
counted columns, derived in *every* era including the ones that printed them. A
source that prints a quotient has not observed a quotient.
