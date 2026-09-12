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
the gate was written to detect.

### A check's design is not evidence until it has run on the real data

**Ryan, 2026-09-11, on two of my own checks in one pass.** Both were designed carefully, both
passed their selftests, and both were wrong in a way only the live run could show:

- **A league gate flagged 195 club-seasons as split in two.** It keyed a club-season on year and
  club code. But a code is not a club across leagues: in 1926 `BKN` is the NFL Lions and the AFL
  Horsemen, two real club-seasons. The selftest had no shared code in it, so it could not see this.
- **A strict-resolver dry run would have refused 49,417 WIFU and IRFU claims.** It read a club's
  league with `league_for()`, which returns only the first league a club plays that year, and
  Regina is lawfully CFL 1945–2025 and WIFU 1946–60 at once.

**The rule: run a new check against the real data before trusting it — and before trusting a
number it produces — and read what it flags.** A selftest proves the check can fail; it cannot
prove the check's picture of the data is right, because the selftest is built from the same
picture. Only the real corpus holds the case the designer did not imagine. Both errors were in
the direction of reporting a defect that was not there, so neither would have been caught by the
check itself; both were caught by looking at the first examples it printed.

*Same family as `implausibility is a signal about your method` — 195 splits and 49,417 refusals
were both too many to be true of a table that had been gated for a week.*

---

## A page can contradict itself

**Ryan, 2026-09-11, on two PFA cases found the same afternoon.** A source that prints one fact
twice on one page may print it two ways, and the archive's answer then depends on which field a
reader happens to take — silently, because each reader is right about the field it read.

**The evidence.**

- **A team page's title and its header.** `1936afabkn.html` is titled `1936 Brooklyn Bay Parkways
  (AFA)` and headed `1936 Brooklyn Bay Parkways (AA)`. The club-roster reader took the title and
  filed 7,230 claims under AFA; the statistics reader took the header and filed 666 under AA — a
  token no club held, so those claims carried no league at all. It looked like a question about
  two 1930s leagues. It was two readers and one page. **Ruled: one league**, read as AFA
  (`LEAGUE_LABELS_BY_YEAR`), both strings kept as printed.
- **A game-log row's link and its short label.** Each row names the man's club as a link, a full
  name and a short label for phones. On about 22% of PLAYOFF rows — and on no regular-season row
  — the short label prints the opponent: `2013 CAR NFL` on a 49er's row whose link and full name
  both say San Francisco. The ingest took the short label: 8,511 claims on the opponent, 742
  rosters carrying their opponents, 2,465 biographies naming clubs the man never played for.
  **Ruled: read the club from the link and the full name, which always agree; keep the short label
  as printed.**

**The rule: where a page gives a fact more than once, a reader reads every form and compares
them.** Take the form that a second form on the same page agrees with, and hold the one that
disagrees as printed — it is what the source published, and holding it costs nothing. A reader
that takes one field because it was the convenient one has made a choice it never recorded.

*Related: `the row length names the layout` — the same source, the same shape: what a page prints
is not one thing, and the reader has to find out which thing it is holding.*

### The first fix was wrong too, and the diff against the old store said so

The first reader took the club from the row's link and **refused any row whose two links
disagreed**. Re-ingested and compared claim by claim with the stores it replaced, it had **lost
2,570 claims that were right**: PFA links the 2020 Raiders as `oak` beside the name "Las Vegas
Raiders"; the Phil-Pitt link `1943nflp-p` has a hyphen the pattern did not allow; the punting
blocks shift their header by one, so looking the team cell up by its label found the date. The
corrected reader compares **at the level the fact lives — the club, not the code** — reads the
link that sits with the full name, and finds the cell by position as it always had been.

**Two practical rules came out of it.** When a fix rewrites a store, compare it with the store it
replaces, claim by claim, before anything is built on it: a total that is close is not a total
that is right. And a row a reader refuses is counted **in the store**, not only in the reader's
own metadata, which nothing kept — that is how 2,570 rows came within one step of vanishing in
silence.

**And the second pass was wrong in a third way.** Where a row's short label named the opponent,
the ingest needed a string for the man's real club and took **the table's code**. PFA labels the
Bears `CHIB`, the Rams `LARM`, the AAFC Yankees `NY`; the table holds `CHI`, `LAN`, `NYA`. So a
Bear whose playoff rows were labelled rightly on some days and wrongly on others sat on `CHIB` and
`CHI` in the same season — **652 man-club-seasons split across two strings, 388 men**, where the
stores before the fix held 12 (all `B-NY`/`BNY`, which PFA itself prints both ways). Every check
that compared clubs passed, because both strings resolve to the one club; only a check on the
string itself saw it. The rewritten row now takes the string PFA prints for that club that year,
learned from its rightly labelled rows; the table's code is used only where PFA never prints one,
and counted. `gate_game_club` G2/G3 hold it, and were shown failing on the stores the second pass
wrote (168 rewritten strings, 50 split seasons, in three decades) before they passed.

**The rule underneath: a key is a string, and resolving to the right club does not make two
strings one key.** Where a fix must *write* a club string, it writes the one the source already
uses for that club — not a better one from elsewhere.

### A game's two sides are a third reading, and in 1934 they outvote the full name

A game-log row prints the man's club; the rows of the men **on the other side of the same game**
print it too, as their opponent. That is an independent reading inside PFA, and it was used to
check the fix: postseason claims contradicted by the other side fell **8,738 → 116**, and every one
of the 116 left is PFA's opponent column being wrong on the other side (the 2006 Saints' rows
printing `NO` as their own opponent; the 2025 Bears' printing `DET` in a game against Green Bay).

**It also found the one place the full name is wrong.** Fifteen 1934 men's rows print the club
the wrong way round: on the Reds' games (9 September – 6 November) the full name reads *St. Louis
Gunners* while the short label and every opponent's rows say `CIN`; on the Gunners' games (11
November – 2 December) it reads *Cincinnati Reds* while the label and the opponents say `STL`.
66 regular-season rows. Under the rule as ruled — the club is the one the row prints in full —
they go to the wrong club.

**Ruled (Ryan, 2026-09-11): declared as an exception, narrowly.** The rule takes the full name
because the full name is normally the reliable one; here it demonstrably is not, and following the
rule into a known-wrong answer is the letter beating the purpose. So the 66 rows are **named one by
one** in `declarations/pfa-log-club-exceptions.json` — with what PFA prints, what the label says,
what the opponents print (153 rows across the ten games, unanimous), the 15 men and the two
club-seasons — and held on the club the label and both sides agree on. There is no general rule
about full names. Measured over every game claim in the archive, **no other row has this shape**.

**An exception is gated, not exempted.** `gate_game_club` G4 checks every declared row is held, on
its declared club, and *still* prints the declared evidence, with the opposing side still printing
what was declared; G5 checks the rows of this shape are exactly the declared ones. If PFA corrects
these pages, the ingest stops holding them and G4 fails, saying the exception has become wrong —
it never silently overrides a source that has come to agree with itself. G4 was shown failing on
the model before the exception was applied (66 not held) and passing after.

### A date in a place field is a reading that fell through

Found through one man. Frank Moran is 28 on Neft's 1920 Hammond roster; StatsCrew's birth date
(1905) makes him 15. The archive showed that 1905 as **uncontested** — because PFA's page, which
prints `Born: 1890`, had been read with the year filed as his **birthplace**. The player-page
splitter knew one date shape, `March 5, 1905`; anything else fell through whole into the place.
**721 birth places and 45 death places** held a date that way — a bare year, a year then a town, a
month and year, a year with its month printed empty (`, 1999`), and six full dates whose day PFA
garbled (`September 256, 2001`).

**Three things were true at once, and each is the lesson:**

- **A value in the wrong family is invisible to everything that reads the right one.** No
  birth-date check, no family grouping, no `contested` flag looks in a place field. The archive
  held both readings and presented one as settled.
- **The reader was still doing it.** Fixing the 766 values alone would have left the next ingest
  re-filing them. The fix is in the one splitter every PFA reader shares.
- **The defect had been fixed once already, locally.** `pfa_coach_pages` carried its own patched
  copy — *"the player-page splitter … would file '1940' as a place"* — so coach pages were right and
  seven other readers stayed wrong. A fix made in a copy is not a fix: it makes the defect
  invisible where you are looking.

**Fixed as a reading, not a rule** (Ryan, 2026-09-11): where PFA prints a date in the Born/Died
position, it is read as the date, exactly as printed, and only what follows is the place. No age
band was needed to contest Moran; the two documents do it. `gate_place_fields` F1 — no place value
opens with a date — was shown failing on the model (760) before it passed, and its test is
deliberately looser than the reader's, so a shape the reader does not know still fails. Its first
version passed the six garbled days, and the gate's own day pattern was widened when they surfaced.

### Four ways a field goes quiet

All four surfaced on 11 September 2026, from one ruling. *A coaching season is held in one shape*
(9 September) moved every coaching key out of a person's `seasons` into `coaching_seasons`. Each shape
is the same event — data moved or grew, and nothing that depended on it was told — and each hid for
days because nothing failed.

**1. A reader looking in the old place.** Code that reads the field the data left. The coach ingest
looked for coaching keys in `seasons` and refused 18 coaches as conflicts with their own merge shells.
A sweep of about 140 readers found 30 still wrong. **Guard:** when a ruling moves data, sweep the
readers by hand, and classify each as *meant this*, *updated*, or *not the field*. A grep census is a
reminder; only reading the code is a proof.

**2. An applier skipping in silence.** An applier that does not find its target moves on without a
word. `apply_club_keys` skipped 658 of 677 decided rewrites (`if r["from"] not in ss: continue`).
`apply_person_merges` "applied" 93 merges that moved 0 of the 1,352 club-seasons they recorded.
**Guard:** every applier accounts for every decision — decided, applied, skipped, and a *legitimate*
reason for anything it did not do (`index_io.write_account`, `gate_appliers_account`). A skip because
the key sits in a dict the applier does not read is a symptom, not a reason, and fails. *"Decided 677,
applied 19, skipped 658"* would have been loud on day one.

**3. A gate passing on a shrunken population.** A check whose population silently lost what it
exists to check still passes on what is left. `gate_club_mapping` C1 compared two routes that both
read `seasons` and agreed. `gate_claim_league` L2 checked 194,518 keys; reading both dicts it checks
217,289, and the coaching keys it had never seen include real mis-leagued seasons (490 failures in 62
club-seasons, against 234 in 15). `gate_club_keys` G7's failure was hidden
behind another check's failures in a capped list. **Guard:** a gate says what it checked, every run,
whether it passes or fails. A count of zero and a count of nothing to count are different answers, and
*nothing to check* fails.

**4. A decision set going stale because the data grew.** Decisions made on 7 September covered the keys
that existed on 7 September. Two days later the PFA coach store and the promoted coaches added
coaching keys the decider would also decide — 849 of them, 398 of them PFA's `BC` for the BC Lions.
Nothing is wrong with the old decisions; they are simply no longer the whole answer. A decider re-run
to fill the gap would have overwritten them instead, which is how Joe Spencer's merge was lost to a
re-run of `merge_people`. **Guard:** decisions are a declaration, in git; the decider is a *proposer*
that reports what it would add and withdraw against them, and a new proposal is a question for Ryan,
not a change. The merge decisions (93) and the club-key decisions (2,606) are both held that way now.

**Underneath all four:** a ruling that moves or grows data must say what depends on it. Two parts of
that can be gated — the applier accounts and the gate populations. The reader sweep cannot be gated,
and pretending otherwise would be worse than saying so.

### A rewritten store is compared with its predecessor at the fact's own level

**Before anything is built on a rewritten store, compare it with the store it replaces — claim by
claim, at the level the fact lives: its id, its subject, its club, the string it is keyed on.**
Ryan, 2026-09-11. This pass rewrote 21 stores three times, and that comparison is what caught each
defect; a total would have shown none of them:

- **2,570 right claims lost** by the first reader — beside a million claims, a loss no total
  would have flagged; the comparison named every one.
- **652 man-club-seasons split across two strings** (`CHIB` and `CHI` for one Bear's one season) —
  every total and every club-level count was unchanged; only comparing the *strings* each man's
  season sat on, old against new (12 before, 652 after), showed it.
- **51 derived games labelled `OAK`** — the same games, the same count; only comparing each
  game's value with its predecessor's showed the sides had changed.

**How to apply:** back the store up (`*-store.before-*.json`, ignored), re-ingest, then diff by id:
lost, gained, subject changed — and for each change, check it moved where the ruling says it
should; then compare values, and the keys each subject sits on. Account for every difference by
name before rebuilding the index. The rebuild's own P3 is the second net, not the first: it caught
32 keys the declared transition missed, but only because a rebuild was refused. A gate that cannot fail reports success; a gate
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

**Fifth instance, 2026-09-07.** Five times now, in five different mechanisms, an
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
5. **A programme extractor reporting 2 men for a page carrying 32**, 2026-09-07.
   All 27 surnames and all 4 staff names are present in all three OCR texts, so
   nothing was lost in reading the photograph. The page is set in two columns and
   its entries are bio paragraphs, and every exit that discarded a band —
   multi-number, no-name-matched, too-few-numbers — was a bare `continue`. Both
   of the 2 it did report were false: `New`, from "New York Univefsity", and
   `DEWEY`, a forename whose surname arrived as `LYLE—29 years,`. **The true
   yield was 0 of 28, reported as 2.** Corpus-wide, 299 men reported against 407
   multi-number bands and 209 name-failed bands dropped uncounted, and 536 of 667
   images discarded before banding.

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

**And the fifth adds an obligation the first four did not need.** Those were
about a fetch or a parse that produced nothing; this is about one that produced
*a number*. **A silent zero is the most expensive value an extractor can
return** — a page that yields nothing and a page that has nothing are the same
output, and a yield report cannot tell you which it saw. **Every drop must be
counted where the count is published, not merely `continue`d.** Instrumenting the
drops changed nothing about what the extractor accepted and changed everything
about what could be believed of it.

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

**Fourth instance, 2026-09-05. The first three form a ladder; the fourth moves the
pattern off numbers entirely.**

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


### Fourth instance: a DATE, not a number

**`prosportstransactions` marks some rows `(date approximate)`.** That is the
compiler stating his own uncertainty, in his own words, about his own work — the
rarest thing a secondary source can offer and the easiest to lose, because
dropping it costs nothing and yields a clean date.

**A date promoted from approximate to exact is the same failure as a projection
read as a measurement.** Nothing about the pattern was ever specific to money;
the first three instances were numbers only because money is what we happened to
be extracting. The rule is about *any* value whose stated confidence is discarded
in transit.

**And this one runs the other way from the first three.** Those were cases where a
source's hedge had to be *noticed* — "approximately", "estimated", or in the
passer-rating case no hedge at all. Here the source hedges **explicitly, per row,
in a field of its own.** The failure would not be missing the caveat; it would be
receiving it and throwing it away.

*Recorded before the ingest exists, so the ingest is written to carry it rather
than retrofitted to.*

**Corollary — the arithmetic columns.** `Comp %`, `Yds/Att`, `TD %`, `Int %` have
no introduction date because they never needed one: they are arithmetic on two
counted columns, derived in *every* era including the ones that printed them. A
source that prints a quotient has not observed a quotient.

---

## A documentation exemption is legitimate exactly when the rule lives somewhere else

**2026-09-05.** `gate_declarations_are_read` refuses a declaration key that
nothing reads, and the escape hatch is `_documentation_only`. Four times that
hatch was covering a mistake:

1. `JERSEY_USABLE` — computed and never referenced.
2. `cfl.expected_fill` — right file, wrong block.
3. `league_codes` — prose that nothing enforced, while `AFL3` silently loaded
   the Arena Football League.
4. `stat_columns.applicability` — nested **inside** a documentation-only block
   *minutes after the rule against doing that was written down*.

Every one was a real rule hidden where nothing could read it, and marking it
documentation would have made the gate a rubber stamp.

**The fifth was different, and the difference is worth stating.**
`prosportstransactions.RANKING` describes a rule that genuinely lives elsewhere —
`policy/resolution.json :: source_rank.secondary_compilation`, rank 1 against
primary's 3, read by `resolve_store.source_rank()`. The declaration block is
*commentary on* an enforced rule, not the rule itself.

**The test is not "is this important?" — everything in a declaration is
important. The test is: can you name the file and the function that acts on it?**
If you can, the block is documentation and the exemption is honest. If you find
yourself explaining why the rule matters instead, you are looking at instance
five of the same mistake.

*Recorded because the exemption is the mechanism that lets the gate be defeated,
and after four abuses the first legitimate use needs to be visible as such — or
the next honest exemption gets refused out of superstition.*

---

## Absence of variation is not absence of the possibility of variation

**2026-09-05.** Three contracts — Groza 1951, Atkins 1954, Sugar 1961 — carry the
NFL Standard Contract's 75/25 payment clause unamended. From that I reported *"a
league-scoped system fact with a measured start and end."*

**The 1923 Uniform Player's Contract carries the same clause struck through and
amended by hand to 90/10.** So it is a **printed default individual contracts
could override**, and three men who did not negotiate it were never evidence that
it could not be negotiated.

**This is not the sample-versus-census error, and the difference matters.** A
sample tells you a field's typical value and hides its range — the fix is to
count more. Here the three documents were **read correctly**, the observation was
**accurate**, and counting more of the same would not have helped: fifty
unamended contracts would have made the wrong conclusion feel stronger. What was
wrong was the **inference from uniformity to necessity**.

**The tell is a claim about what COULD happen, drawn from records of what DID.**
"Every contract I hold says 75/25" is an observation. "The league required 75/25"
is a claim about the rule behind the observation, and no quantity of conforming
instances establishes it — only a document stating the rule, or a single
counter-example destroying it. Pearce was the counter-example, and one was enough.

**Where this bites hardest is exactly where the dataset is strongest**: a corpus
large enough that uniformity feels like proof. 3.3 million claims will contain
many patterns that hold in every case we have and were never obligatory.

**The rule: a claim about a rule needs a source that states the rule.** Derive
distributions from records; do not derive constraints from them. Where a
constraint is asserted, name the document that imposes it — and where none
exists, say "every instance we hold" rather than "the league required".

*Recorded with its own instance count: this is one, and one counter-example
found it. The precedent exists so the next uniformity is doubted before it is
promoted.*


---

## Hold a conclusion loosely while documents are still arriving

**2026-09-05.** One finding — the NFL contract's 75/25 payment clause — was
corrected **three times in a single day**, each time by a document that arrived
after the conclusion:

1. Reported as *"a league-scoped system fact spanning at least 1951–1961"*, from
   three unamended contracts.
2. **The 1923 Uniform Player's Contract** carries it as a printed default
   twenty-eight years earlier — **and struck through, amended by hand to 90/10.**
   So not a rule, and not starting in 1951.
3. **Gregg 1966** carries 75/25 **semi-monthly**, where I had recorded the
   interval changing at the same time as the split. Two variables, moving
   independently, years apart.

Nothing was misread. Each conclusion was sound on the documents then held, and
each was wrong.

**The failure mode is not carelessness — it is closure.** The pull toward
settling a question is strongest exactly when evidence starts arriving, because
the first few documents feel like the answer rather than the beginning of one.
Three contracts looked like a pattern; the fourth made them a sample.

**The rule: while a source is still being acquired, a finding is provisional and
must say so.** Not hedged into uselessness — the figures were right, and stating
them was right. What should have carried a caveat was the *shape*: "spans
1951–1961" claims an extent, and extent is precisely what an incomplete corpus
cannot support.

**Say what the documents show and name the boundary as the corpus's, not the
world's.** *"Every contract we hold, 1951 to 1961"* would have survived all three
corrections intact.

*Related but distinct: `absence of variation is not absence of the possibility of
variation` is about inferring a constraint from uniform records. This is about
inferring an EXTENT from an incomplete set — and unlike that one, more of the
same evidence does fix it. The documents were still coming.*

---

## A document may be held without becoming clubs

2026-09-07, on a page of a hobbyist website that carried better evidence about
the 1926 Eastern League of Professional Football than anything the archive
held.

`Bethlehem.htm` gives the league's full standings — ten clubs, W-L-T, points for
and against, a note that Clifton Heights withdrew on 13 October — a two-deep
22-man all-league team with clubs and positions, and a per-player scoring table
separating league from non-league play. **Real evidence about real football**,
and it could not be admitted, because admitting it meant creating ten
club-seasons the archive cannot populate and lengthening a hunting list that
already holds 128 empty ones.

**The rule: a record of clubs, seasons or results may be registered as a source
document — searchable and citable — without creating club-seasons in the club
table. Nothing derives from it.** It sits until a roster turns up, and the club
is created then, on the roster.

*Alternatives rejected.* **Admit the league**, which turns the minor-league
exclusion into *"excluded unless I happen to have a source"* — a rule that
dissolves on contact with good material, which is exactly when a rule is doing
its work. **Refuse the document entirely**, which throws away evidence because
of a scope decision it has no bearing on; the document is not asking to be a
club table, and refusing it confuses the two.

**Applies retroactively** to the 1926 AFL standings and to the St. Louis Gunners'
independent seasons 1931–33.

**The caution, and it is the whole risk in this ruling.** A held document that
starts answering *"which clubs existed in 1926"* is a club table by another
name, reached by a route with none of the club table's gates on it. **It must
stay inert.** Registered, cited, returned when asked for — and never joined,
never counted, never summed.

---

## A non-league professional club enters when a club in scope played it

2026-09-07. The 1926 Los Angeles Tigers, from a programme for a Chicago Bears
game at the Los Angeles Coliseum.

**A non-league professional club enters the archive when a club in scope played
it in a documented game. It enters for that game only — not for its season, and
not for its league.**

*Alternative rejected:* a **date cutoff** admitting minor leagues before 1930 or
1940. It reads as a modest concession and it admits hundreds of club-seasons of
precisely the material the exclusion exists to keep out. A cutoff cannot
distinguish a club a major club played from a club that merely existed at the
same time, because a year is not evidence about a club.

**This follows the merged-clubs precedent: the game is the evidence, not the
league.** Card-Pitt and Phil-Pitt are their own clubs because men provably
appeared in games for them, not because a league recognised them. The unit that
carries evidence is the unit that enters.

*Where two rulings appeared to collide — the minor-league exclusion against this
one, on a page that recorded an NFL club beating an Eastern League club —* **they
only collide if the unit is the league.** *Keep the unit the game and both hold
intact: the exclusion keeps the league's season out, its standings and its
championship with it, while this admits the one club-game and nothing else. One
club-game enters; a ten-club league does not.*

**And where a club is genuinely hard to call professional or not, stop and ask.**
Do not decide it in passing while doing something else. The ruling admits *a
professional club*; whether a given eleven was one is a judgement about that
club, and making it silently while executing something else is how a scope
decision gets made by nobody.

---

## College and service teams are named, not held

2026-09-07, alongside the ruling above and constraining it.

**A college or service team is recorded as the opponent string on a game. No
club-season is created, and its players do not become people.**

Without this, "a club in scope played it in a documented game" admits every
college a professional club scrimmaged and every service eleven it met on tour —
and with them, thousands of young men who were never professional footballers.
**It keeps *no invented humans* intact**, which is the constraint the whole
person model rests on.

---

## A probable line-up is not a boxscore line-up

2026-09-07, from a programme printed before kickoff.

`roster_membership.started_a_game` is defined as *named in a starting lineup,
from a boxscore* — an after-the-fact record of what happened. A programme's
line-up page is **a publisher's prediction, printed in advance**. They are
different assertions about different things, and one of them can be wrong in a
way the other cannot.

**Separate predicate, with its own definition.** The document proved the gap in
its own pages: it lists `22 McMillen` at right guard in the probable line-up and
does not carry McMillen in the roster at all.

**Fold them and they can never be separated again.** That is the asymmetry that
decides it — keeping them apart costs a predicate; merging them costs the
distinction permanently, because nothing downstream can recover which claim came
from which kind of page.

---

## A team photograph is a third thing

2026-09-07, from the caption to a team photograph of the 1926 Pacific Coast
Wildcats, naming 22 men.

**`programme.team_photograph` — named in the caption to a team photograph: this
man was photographed with this club, as this club.**

It is **weaker than roster membership**, which means a club or a source asserted
a man's standing on a squad. It is **weaker than a probable line-up**, which
means a publisher expected him to play in a particular game. A photograph
asserts only that he was there when it was taken.

It is worth having precisely because it is weak: `AFL|1926|AFLPC` is one of three
club-seasons in the archive that no source ever gave a roster for, its ten held
men were derived from box scores, and **a photograph is the only kind of evidence
that can show a man who never got on the field.**

*This is the second predicate in two days created rather than borrowed. The
pattern is worth naming: when a new source asserts something at a different
strength from anything held, the cost of a new predicate is one definition and
the cost of borrowing one is a distinction that cannot be rebuilt.*

---

## A disagreeing value is always written as a claim

2026-09-07, found by asking whether stores that report disagreements actually
hold both sides.

Three stores declare *"both held"* in their own reports and hold one side:
**nflverse-rosters, 1,021 and 229; nflverse-draft, 164.** Pro Football Archives
does the same job on identical ground and holds **628 of 628**, so this is not a
limit of the material.

**The rule: where a store records a disagreement, both values are written as
claims.** A disagreement the archive can describe but cannot serve is not held —
it is a note about a fact, in place of the fact.

*Alternative rejected:* let the store's report stand as the record. It reads as
economical and it means the archive's answer to *"what does this source say"*
depends on which file you open. **A value the archive cannot serve is not held**,
whatever a report beside it says.

*One qualification found while executing it, and it is a real limit: a store can
record a disagreement on an identity join it refuses to write a claim on. Where
that is so, writing the missing side answers an open identity question by
implication — and if the join is not good enough for a claim it is not good
enough for a disagreement either. Check the join before writing the side.*

---

## A gate checks the claims, not the store's report of itself

2026-09-07, after a gate that had passed for weeks turned out to be incapable of
failing.

The never-shrink photograph gate read a **boolean the build had written about
itself** — `every_claim_strictly_larger` — computed as `all()` over a set that
was empty, because none of the 1,667 claims had been decided on size. A gate
reading a source's self-report is testing that the source can write a field.

**Three requirements, and a gate meeting fewer is not a gate:**

1. **Re-derive from the base state.** Recompute the property from the claims, not
   from anything the thing being checked said about itself.
2. **Refuse an empty denominator rather than pass on one.** `all()` over nothing
   is `True`, and that is the archive's most common silent failure — it is why
   RS-G6 was green across two families while meaning nothing.
3. **Be shown failing in its own self-test.** A check nobody has watched fail is
   a check nobody has tested.

**Six further gates check a store's report of a disagreement rather than the
claims.** Recorded here as a class, not repaired one at a time.

*This generalises `a gate that fires must fire for its stated reason`. That entry
is about a gate that fails for the wrong cause; this is about one that cannot
fail at all — and the second is worse, because a wrong red gets investigated and
a vacuous green does not.*

---

## Which facts can be contested, and why high school cannot

2026-09-07. Declaring predicate families so that two spellings of one fact stop
being recorded as two facts.

**Declared: height, weight, draft, college.** College reads by expanding the
abbreviation and dropping the word *University*, so `Ohio St.` and `Ohio State`
are one school. `College` is never dropped — Boston College and Boston University
are two schools, and a fold that merges them invents an agreement, which is worse
than the two disagreements it hides.

**Birth place and death place were approved conditionally**, on the trailing
country fold measuring clean, and it did.

**High school is refused.** `Central` against `Central (Detroit, MI)` cannot be
settled by a fold, and that shape is most of the 1,350 literal disagreements.
Folding them invents agreement; leaving them unfolded records disagreements the
archive cannot judge. **Neither is an improvement on saying no.**

**This is a refusal, not an oversight, and it is recorded so nobody reopens it
quietly.** Seven families and one refusal is a worse-looking table than eight
families. **Do not add it to make a count look complete.** It comes back when
there is a real rule, not before.

---

## A state abbreviation is the same state; a qualifier is not

2026-09-07, once birth place and death place became contestable families and the
disagreements could be counted.

**`Los Angeles, CA` and `Los Angeles, California` are one place.** The reading
expands a trailing state abbreviation, and only a trailing one, and only when
something precedes it — `IN`, `OR`, `OK`, `ME`, `LA` and `DE` are English words
as well as states, and position is all that separates them.

**A qualifier is not a state name.** `near Whitesboro, TX` reads to `near
whitesboro texas` and `Whitesboro, Texas` to `whitesboro texas`, and they still
disagree — because one source says the town and the other says somewhere nearby,
and that difference was never about the state. **Nothing else is removed**, which
is what preserves it.

**Measured: 1,873 of 2,601 place contests collapsed. 728 genuine differences
stayed.** The prediction before the reading was written was 1,873; it collapsed
1,867. **Six fewer, and under-shooting is the safe direction** — a fold larger
than its prediction is reaching past the thing it was scoped to.

---

## Nothing rebuilds on an unexplained red

2026-09-07. `gate_person_merges` failed on 25 of 93 canonical people, and a
rebuild would have cleared the symptom.

**Measure before explaining, and explain before clearing.** The gate proved to be
**stale bookkeeping and not lost data** — a `counts_before` snapshot taken a day
earlier, against canonicals that had legitimately gained seasons since. Undo and
reapply were byte-identical; 93 of 93 records were whole.

**That was established, not assumed**, and the distinction is the entry. The
standing hypothesis — that a later chain step had changed keys — was *wrong*, and
would have been adopted if the red had been reasoned about instead of measured.

**A red that a rebuild would clear is the most dangerous kind**, because the
cheapest action available also destroys the evidence.

---

## An absence is not the string "None"

2026-09-07. Not a new ruling — a record of where an existing one was broken, and
of how long it survived.

**7,077 people carried the literal string `"None"` in a value position** where an
absence claim had been made. `build_person_index` was stringifying claim values
without reading `kind`, so *a source stating that a man has no recorded hometown*
and *a man whose hometown is the word None* became the same bytes.

**A builder must not drop `kind`.** The distinction between an observed value, a
stated absence and an unmeasured field is the archive's central one, and it is
lost by a `str()` call.

**How it survived:** every consumer downstream tested for the *presence of a
predicate*, and the predicate was present. A measurement written this same week
reported the pre-1934 record as complete on exactly that mistake — it counted
keys, not values — and only a hand-checked example (`Backnor`, of the 1921
Tonawanda Kardex, carrying three predicates all holding `"None"`) exposed it.

*Related: `an empty result and a failed one are the same bytes`. This is that
shape one layer in — an absent value and a present one became the same bytes, and
every check above it inherited the confusion.*

---

## The club table must never be silently older than the claims that feed it

2026-09-07, found by asking why a club that had been written, indexed, gated and
served was invisible to `search_clubs`.

`build_clubs.py` was **in no chain and run by no gate**. It had also been
**unrunnable on this machine since the archive moved to it**, because a required
input path was hardcoded to a Dropbox folder that exists only on the laptop — so
it refused on a missing input every time, and nothing noticed for a day.

**A derived table that nothing rebuilds is a cache pretending to be a table.**
It goes in the rebuild chain, and a failure to build it fails the rebuild rather
than publishing claims against a stale table.

**But it is not an index patcher**, and the gate that guards the chain was right
to refuse it: every chain step must write the index, and this one *consumes* the
index and writes something else. **It gets its own declared phase carrying the
inverse property — a derived table must not write the index — checked rather than
assumed.** Weakening the first property to admit something it was never about
would have cost more than it bought.

*The failure mode is the general one: **the omission looked exactly like
success.** Nothing was red, nothing was counted, and it surfaced only because a
person searched for a club and got nothing back.*

---

## A finding aid is cited, and never stands in for a source

2026-09-07, on a site whose author cites unevenly.

John J. Fenton's *Ghosts of the Gridiron* lists **twenty-one newspapers** on its
sources page, and its prose names individual papers against individual facts —
the *Bethlehem Globe-Times* five times on one page, once with his own hedge
attached. **Its roster pages name nothing at all.**

**Where he names a paper, the paper is the source and Fenton is the finding aid.
Where he names none, record `underlying_source: unstated` as a stated absence,
and cite him as the finding aid. Every claim carries the finding aid in both
cases** — he did the work of locating the material and the citation should say
so.

*Alternative rejected:* attribute the rosters to the global list, on the
reasoning that they must have come from one of those twenty-one papers.
**Attributing a roster to "one of these twenty-one newspapers" manufactures a
citation the author never made.** The list describes the site; it describes no
page in it. A claim whose citation is a guess cannot be checked, cannot be
corrected, and is indistinguishable from one read off the page.

**Inventing provenance is worse than admitting you have none.** `unstated` is a
stated absence, and it is the same distinction the archive already draws between
a value that is absent and one that was never measured — see *an absence is not
the string "None"*. A guessed citation collapses that distinction at the point
where it matters most.

**And the gap is useful.** *Which paper did this roster come from* is a specific
question that can be put to a living author. A fabricated citation would have
closed it forever.

*This is the first source found for the archive that does not descend from Neft's
1970s reconstruction — which makes what it is cited as, and what it is not,
matter more than usual.*

---

## The value of a source is at the edges of what other sources cover

2026-09-07, judging a hobbyist website about defunct professional football, and
the finding that outranked the one everybody was looking at.

The obvious prize on such a site is the defunct league — and it had one, with a
full standings table. **The actual prize was three club-seasons at the edges of
clubs the archive already holds:**

| | archive holds | the site has |
|---|---|---|
| Frankford Yellow Jackets 1922 | **0 men** | a roster page |
| Frankford Yellow Jackets 1923 | **0 men** | a roster page |
| Pottsville Maroons 1929 | **0 men** | a roster page |
| *Pottsville Maroons 1924* | *0 men* | *a season schedule — games, not men* |

Frankford joined the NFL in 1924 and Pottsville ran 1925–28. **Every source the
archive holds for those clubs is league-derived, so every one of them starts and
stops at the same boundary** — and the seasons on either side are invisible to
all of them at once. No amount of re-reading the sources already held will
produce them, because none of them is looking there.

**The rule: when judging a source, measure it against the boundaries of the
sources you already have, not against their volume.** The middle years were
richly held and this site would have added 36 facts, mostly weight. The edge
years were held at zero and it takes them from nothing to a team. **The same
pages, ranked by the wrong question, look like the less interesting half of the
site.**

*The corollary is a hunting rule. A gap of this kind cannot appear in any list
built from the club table, because the club-seasons are not in it — a list of
what is empty can only show you the holes someone has already framed. Finding
them takes a source that was never organised by the league, which is why one
researcher working from local newspapers produced three of them in a day.*

---

## Facts may be used before permission; scans may not

2026-09-07, on the same site, and settling what could be done with it while its
author was being contacted.

**Recording what a source says, cited, is ordinary scholarly use.** A roster of
names, positions and colleges is a set of facts about 1920s footballers; facts
are not owned, and citing where they were found is the normal obligation.

**Reproducing its images is not.** The 1,752 scans are photographs of newspapers
and programmes long out of copyright — but **the selection and the photography
are the author's work**, and what is inside a scan being free does not make the
scan free.

**In practice for Ghosts of the Gridiron: rosters ingested and cited; 1,752
images preserved, tagged `held-pending-permission`, and none published.** The
same position already taken on media-guide headshots.

*The asymmetry is the point. Preservation is not publication, and the two
decisions have different answers — a dead site's images should be kept whatever
the answer on publishing them turns out to be, because the copy may not exist to
ask about later.*

---

## A club a document establishes enters as itself, not as a league member

2026-09-07, on Frankford's 1922 and 1923 seasons, which the archive held nothing
for while a preserved roster page named 47 men on them.

The archive holds the Frankford Yellow Jackets from **1924**, when they joined the
NFL. Every source it holds for them is league-derived and therefore starts in
1924. Two seasons of professional football before that were invisible to all of
them at once.

**The rule: a professional club a document establishes is created as itself. No
league is asserted, and none is invented to hold it.** The club table already
carries independents with an empty league string, so this needed no new shape —
only the discipline not to reach for one.

*Alternative rejected:* **extend the NFL club's span backwards to 1922.** It is
one edit, it makes the seasons appear immediately, and it silently answers a
question nobody asked. Same name, same city, contiguous years and five men
carrying over are **suggestive and are not the archive's own test**, which is a
source stating the continuation or a code the sources carry across the boundary.
The club is created with `lineage: unknown` and the NFL club recorded as an
*unresolved candidate* — the evidence written down, the conclusion not drawn.

**A second-order cost worth recording.** The index builds a season key as
`(league, year, club)` and derives the league from the store filename, with no
way to write an empty one. A club asserting *no league* therefore has nowhere to
go in the key. The token `IND` was declared for it, in words that say it is **not
a competition** and may be used by no other store. *That is a workaround, and
naming it as one is the point: the key's shape assumes every club-season belongs
to a league, and this is the first that does not.*

**And the men.** 47 roster rows, 33 distinct men: 18 already held, **14 held
nowhere**, one refused because two held people share his exact name. The 14 meet
the standing rule — *a person is someone who played at least one season* — and
their promotion decisions are written with the no-match evidence recorded per
man. **They are not applied**, because the applier reads coach promotions only
and a promoted person's seasons are set by the applier rather than by claims; a
claim on a person who does not yet exist is skipped at read time. Four of the 14
are a surname and nothing else, which is a thin thing to make a person from and
is flagged on each.

---

## An abbreviation folds only where it has exactly one possible school

2026-09-07, from 28 measured rows where a source and the archive named the same
man's college differently without disagreeing about the man.

**`Penn` and `Pennsylvania` are one school. `Pitt` and `Pittsburgh` are one
school. `Miami` is two, and both played football.**

**The rule: a short form folds to a long one only when exactly one real school
competes for it. Where two do, it does not fold, and the pair stays a
disagreement — which is correct, because the sources genuinely have not said the
same thing.**

Six pairs fold: `penn`→`pennsylvania`, `pitt`→`pittsburgh`, `franklin &
marshal`→`franklin & marshall` (a one-letter printed error), `haskell`→`haskell
indian` and `detroit`→`detroit mercy` (both one institution renamed), `w va
wesleyan`→`west virginia wesleyan`.

**Four are refused, and the reasons are the entry.** `georgetown` — Georgetown
University in DC and Georgetown College in Kentucky both played football, and the
archive's own value writes `(DC)` precisely to separate them, which is evidence
the ambiguity is real rather than theoretical. `cornell` — Cornell University in
New York and Cornell College in Iowa. `nebraska` — Nebraska and Nebraska Wesleyan
are two schools.

And `lebanon` against `lebanon valley`, **refused for consistency rather than
certainty.** It is a prefix, which is exactly the shape of `nebraska` against
`nebraska wesleyan` — and there the prefix is a different school. Folding one
prefix while refusing the other would mean the rule was really *fold where I
happen to know of no competitor*, which is not a rule at all.

*Alternative rejected:* build the synonym list from a general list of American
colleges. **A list nobody measured is a list nobody can defend**, and it would
have carried hundreds of pairs the archive has never met in order to fix ten it
had. The list is built from the 28 rows that were actually observed.

**This is the third instance of one shape**, and they should be read together:
the state reading expands a trailing abbreviation *but refuses a lone `LA`*,
because `LA` is Los Angeles as often as Louisiana; the college reading drops
`University` *but never `College`*, because Boston College and Boston University
are two schools. **A fold that cannot tell two things apart must not merge them,
and the correct output is a disagreement rather than a false agreement.**

**Measured before and after, on the same model.** RS-G6, evaluated with the new
list against a model built without it: **FAIL, 9 false disagreements.** Rebuilt:
**PASS, 0.** Contested `college` rows fell from **107 to 98** — the nine that
folded — and the four refused pairs are still there, still contested, as they
should be.

### Extended 2026-09-08, and the rule survived contact with 662 pairs

The list grew from 6 folds to **42**, built from the **18,279 college disagreements**
measured between PFA's 2,926 team-season roster tables and the archive — 662 distinct
one-to-one pairs over 14,615 rows. **36 fold, covering 8,209 rows. The rest stay
disagreements.**

**Three named shapes, and nothing else folds.** A short form qualifies only as (1)
the **initialism** of the long form, with or without the University the long form
omits — USC, UBC and UNLV carry it in front, LSU, SMU, TCU and BYU behind; (2) the
long form with a trailing **generic** word dropped, `bowling green state` to `bowling
green`; or (3) the long form with its **last word shortened**, `boston college` to
`boston col`. Anything outside those three is a guess about which school is meant.

**Four things the first version of the rule got wrong, each caught by a pair it
mishandled:**

**`State` is not always generic.** An early pass folded `south carolina state` to
`south carolina` and `south dakota state` to `south dakota`. Those are two real
universities each; there `State` is the whole of the distinction. `State` is now
never dropped where what remains is a **state's own name**, taken from the fifty in
the declared place reading rather than retyped.

**A rival must be a rival.** Counting every school a short form disagreed with
refused all ten pairs Ryan had named. `usc` disagrees with `davidson` twice in the
corpus — one man's college disputed between two sources, not evidence that USC is
ambiguous. A second school competes only when **it could itself abbreviate to that
short form**.

**A fused cell is not a school.** `tcu ohio state` looks like a school beginning with
`tcu`. It is two colleges in one cell, and it refused `texas christian`. The
discriminator is the remainder: if what follows the short form is itself a college
the archive holds, the value is a fused cell. `georgetown dc` survives that test,
because `dc` is not a college — so Georgetown stays refused, correctly.

**A prefix that drops the front is not an abbreviation.** `st francis xavier` to
`xavier` and `clark atlanta` to `clark` both passed an earlier truncation test. Xavier
of Ohio and Clark of Massachusetts are real schools. Only trailing words may go.

**Measured before and after, on the same built model.** Contested `college` rows:
**104 with the 6 folds, 101 with the 42** — and RS-G6 goes **PASS → FAIL, 4 false
disagreements**, which is the gate working: the model's contested table was built
under the old reading and the new one says four of its rows are not disagreements.
It clears on the next rebuild.

### Extended again the same day: a shortened word, wherever it sits

**Ruled by Ryan, 2026-09-08.** A shortened **non-final** word is the same shape as a
shortened last word. `eastern michigan` and `east michigan` are one school. The rule
now folds where **exactly one word is shortened and every other word is identical**,
wherever that word sits — **35 more pairs, 1,905 rows**, taking the declared list to
**81 folds and 13 refusals**.

**Shortening a word is not dropping one**, and that distinction is the whole of it:
`minnesota state-mankato` → `minn state-mankato` folds; `minnesota state-mankato` →
`minnesota state` still does not. One token shorter, not one token fewer. Comparison
is token by token with hyphens split out and separators required to match, so
`tennessee-chattanooga` and `tenn-chattanooga` line up and a hyphen is never mistaken
for part of a word.

**The refusal test is unchanged and it earned its keep here.** Five pairs fit the new
shape exactly and are refused, because the corpus holds a second school the short form
could equally be: `texas a&m` vs `texas`, `northwestern state` vs `northwestern`,
`mississippi college` vs `mississippi`, `western new mexico` vs `west new mexico`,
`san diego state` vs `san diego`. A wider shape does not mean a weaker test.

**Before adding, the 36 folds declared that morning were re-run against the tightened
rule: none would now be refused.** A declaration holding a fold its own rule rejects is
the drift the declaration exists to prevent, and checking is cheap.

**Why only three rows moved when 8,209 were covered.** The contested table holds
disagreements *within* the archive. The 8,209 are between PFA's team-season pages and
the archive, and those pages are not ingested. The folds are worth having for what
they prevent on ingestion, not for what they resolve today, and reporting 8,209 as
though it were the second number would be the same error as counting rows where men
were asked for.

---

## An ingest declares what it read a source for, and what it left

2026-09-08, after measuring what is on disk against what any claim traces back to.

**The archive tracks claims well and tracks sources badly.** *"Wikipedia is
ingested"* reads as finished. It was read for **people** — every predicate in the
store is person-scoped — and never for drafts, rosters, clubs or standings. Nobody
wrote that down, so **255 of the 391 picks in the 1950 draft are missing from a
source the archive already holds and already allows**, and the gap looked like an
acquisition problem for months.

**The rule: an ingest declares what it read a source for, and what it left.** Not
what it took — the claims already say that, and a declaration of what was taken is
precisely the blind spot. What it *left*, and why.

**The evidence that the omission is invisible without this.**
`corpus-census-frame.json` catalogued **3,110 documents** in September. It carries a
`class` field, and its own header says that field is *"filled by reading"*. **It is
null on all 3,110 rows.** The reading was never done, and **nothing anywhere
recorded that it wasn't** — no red gate, no open item, no note. Measured against the
claims instead, 2,014 of those documents have never produced one, of which **1,727
are media guides**: the largest single block of unread material in the archive,
catalogued and then simply left.

*Alternative rejected:* keep a register of unread material as a document. It was
written that way first, and it is wrong for the reason every hand-maintained
inventory is wrong — **it goes stale silently, and a stale register is worse than
none because it is believed.** It is now regenerated from the disk and the stores by
`src/write_source_register.py`, the same way the hunting documents are.

### Half of this is gateable, and the half that is not must be refused out loud

`src/gate_source_coverage.py` holds the file-shaped half: enumerate the source
directory, collect the locators the claims cite, and require every unread file to be
declared with a reason. On the day it was written it went red on **1,952 files** —
1,517 media guides, 215 Ghosts pages, 151 college documents, 69 programmes — and it
will catch the next seventeen hundred the same way.

**It rests on the claims' own `source_record` locators, never on the
`source_record` tables.** RS-G3 is red: 27 of 481 stores declare a record table and
the largest store in the archive, at 739,486 claims, declares none. A check resting
on that coverage would be measuring the declaration a second time — which is the
defect, not the test for it.

**And the half it cannot see is declared, not skipped.** A source whose unit is not
a file — Wikipedia's article read for one kind of fact, StatsCrew's player-seasons
with no denominator, a source that *is* a single document — must be declared
not-file-shaped **with the reason it has no denominator**, and is then reported as
NOT COVERED. A source with claims that appears in neither list **fails**: silence is
not an exemption, and a gate that passed over what it could not see would report
green across exactly the half the rule exists for.

**The limit, stated plainly because hiding it would make the rule look stronger than
it is.** No gate can check that *"what I read this source for, and what I left"* is
**true**. It can only check that the sentence exists. A wrong declaration and an
honest one are the same bytes, and the only defence against the wrong one is that it
is written down where the next reader can disagree with it — which is worth
something, and is less than a proof.

*Related: `an empty result and a failed one are the same bytes` is the same family
one layer down — there, a mechanism reports nothing and nothing objects; here, a
source is read in part and nothing records the part that was skipped.*

---

## A source with no denominator still has parts that have one

**Ruling, 8 September 2026.** A `not_file_shaped` declaration may not stop at *"this
source cannot be measured."* It must say **which of its parts can be**, and give each
part its unit and how its denominator is obtained. `unknown` is a permitted answer.
**An absent list is not**, because an absent list and nobody having looked are the
same bytes.

### The evidence is a man

**Phil Flanagan**, a guard out of Holy Cross, ninth round, 81st overall, taken by the
New York Giants in the 1936 NFL draft. Forty men named Flanagan are in the archive.
He is not one of them.

He is on `drafts_1936nfldraft.html`, in a table headed
`Round | Overall | Team | Player | Pos | College | Notes`. That file was fetched in
the original PFA ingest and has been sitting on this disk, unread, ever since. He is
not missing because the document is lost, or hard to read, or contested. He is
missing because nothing ever said his page had not been read.

PFA's entry said this, and every word of it was true:

> 50,829 files against 44,550 pages cited. The difference may be duplicates, error
> pages, or material never parsed — **the ingest keeps no list of what it skipped**,
> so the difference cannot be attributed.

True of PFA whole. **False of PFA's draft pages**, which are one per year per league
per kind, indexed by the source itself at `drafts.html`, `cfldrafts.html`,
`usfldrafts.html` and `wfldrafts.html` — **203 of them on disk, 21 (league, kind)
combinations, 1936 to 2025**. Enumerating them took minutes and no network. Reading
them found **35,161 picks, of which 12,807 the archive does not hold**.

The declaration was not wrong. It was silent in a way that read as *cannot be
measured* when the truth was *nobody has said which half could be*.

### What the rule requires

Each part names its unit, how its denominator is obtained, and the three counts kept
apart — **exists / on disk / cited**. They are three different numbers and the
difference between them is the finding.

**Where the denominator is a lower bound, it must say so.** PFA's non-draft sections
were sized from PFA's own link graph over the cache: distinct pages of that shape
some cached page links to. That can never bound a section from above — it cannot see
a page nothing cached links to — so it is a place to look, never a denominator. It is
labelled that way in the declaration, in those words.

**It found a second thing immediately.** PFA's **2,930 team-season pages** are on
disk and **nine** are cited. Each carries a roster table with number, position,
height, weight, age, college, games played and games started. That is the largest
unread body of PFA material already in hand, and no measurement before this one had
a shape that could report it.

### The alternative, and why not

**A source-level exemption** — mark a source *not measurable* and move on — is
simpler, and it is exactly the thing that hid this. One flag cannot distinguish
*"no part of this has a denominator"* from *"nobody has checked whether any part
does."* Requiring the parts costs a paragraph per source and makes the second case
impossible to write down by accident.

### What it caught, unrewritten

`src/gate_source_coverage.py` now refuses a not-file-shaped entry that declares no
`enumerable_parts`. It goes red on **34 of 35**. `src/measure_declaration_parts.py`
sorts them by the evidence and rules on none of them:

| | |
|---|---|
| declares its parts | 1 — `pro-football-archives` |
| **same problem, regular** — many locators, few shapes | 5 — `pfa-transactions`, `nflverse-rosters`, `pfr-draft-listing`, `draft-picks-pre2001`, `draft-picks-2001-2004` |
| **same problem, irregular** — many locators, no repeating shape; the source's own index must be read | 6 — `statscrew`, `wikipedia-en`, `psf-photos`, `pfa-boxscores`, `nflverse`, `coaching-tree` |
| **one document** — the whole is the only part, and the entry should say so | 22 — the court opinions, the news clippings, the two programmes, the 1948 media guide, the 1957 hearing |
| unknown from the read model alone | 1 — `pre1936-assistants` |

The 34 are **reported, not rewritten**. Writing 34 declarations from a script would
produce 34 sentences nobody had thought about, which is the defect wearing the
rule's clothes.

*Related: `every acquired file either produces a claim or is declared unread with a
reason` — this is that rule applied one level down, to the sources that were exempt
from it.*

---

## A selection with an order and no round is read as one, not given a round

**Ruling, 8 September 2026.** An expansion, allocation or dispersal draft is not run
in rounds. Its selections have an **order**. The draft reading now carries `order`,
and `round` and `overall` are **absent** — not zero, not null.

### Why absent, and not zero or null

Three ways to say a document is silent, and only one of them is true. **Zero sorts**:
a round-0 pick takes a place in an ordering the document never printed. **Null
compares**: it is a value, and two nulls agree with each other about something nobody
asserted. **Absent** is the only one that means the document does not say, and it is
the only one `reading_view.same()` already handles correctly — a field only one side
carries is silence.

PFA prints these pages with the columns `Team | Player | Pos | College | Notes`.
There is no Round column and no Overall column on them at all. The 1960 AFL draft is
printed as two sittings, team by team, 422 selections, not one round number among
them.

### Absence alone was not enough, and the gate said so before this was written

Omitting `round` and `overall` leaves an ordered selection and a numbered one sharing
only `year` and `league` — and `same()` compares the fields **both** carry. The rule
that rightly protects a source declining to name its league would have joined a 1960
AFL allocation pick to a 1960 AFL draft pick. The gate's new property caught it on
the first run, before any of this reached a declaration.

So the reading states **how it is numbered**, in a field both forms carry and neither
can be silent about: `numbering` is `order` or `round_and_pick`. **A field only one
side carries is silence; a field both sides carry is a comparison** — and this
difference must be compared, not assumed away.

### The alternative, and why not

**Synthesising a round from printed order** — call the first eight picks round one,
and so on — would make every allocation selection joinable on the ordinary key. It
is the tempting option precisely because it costs nothing and makes the data look
uniform.

It would be a fact the document does not contain. There is no round in an expansion
draft to be right or wrong about; the number would be an artefact of how many clubs
happened to be selecting, and it would then be indistinguishable from a round a
source actually printed. The archive would hold, under the same predicate and the
same shape, some rounds that were asserted and some that were invented, with nothing
recording which was which.

### What it unlocks, and what it does not

**Now readable:** 602 `pfa.draft_allocation` claims and 91 `pfa.draft_selection`
claims, which read as nothing before. Roughly **1,631 further rounds-free selections**
sit on 26 cached PFA pages, unread.

**Still unreadable, and rightly:** 461 `pfa.draft` claims are printed strings naming
a sitting and no number at all — `First Selections 1960 Dallas Texans`. No round, no
pick, no order. An order inferred from row position would be the same invention in a
smaller disguise.

**Still needing a ruling:** `pfa.draft_allocation` is not a member of the draft
family, so nothing downstream reads these claims yet. Measured rather than done:
adding it would create **1,995 ordered-against-existing pairs across 580 people and
fold none of them**. Family membership changes what the contested table holds, so it
is Ryan's call and not a consequence of this one.

### What it broke, which is worth more than what it fixed

Making the draft reading a dict — done the day before, for the league-and-kind
collision — left **two private copies of the grouping rule** comparing readings in a
`set`. A dict is neither hashable nor equal to another dict that `same()` calls the
same fact, so `src/bio_select.py` and `src/gate_readings.py` both raised
`TypeError: unhashable type: 'dict'` the moment a draft reading reached them. Both
now call `RV.group`.

That is the **third** time this rule has had to be pulled back into one
implementation. The crash was the lucky outcome: before the reading became a dict,
the same `set` was silently counting `{year, round, overall}` against
`{year, round, overall, league}` as a disagreement, and nothing objected.

**A visible side effect:** RS-G6 now checks **seven** families where it checked two,
5,510 contested facts, zero false disagreements. The gate that "cannot fire" fires.

*Related: `a draft selection is identified by year, league and kind alongside round
and pick` — this is the same key, finished. The earlier ruling fixed which draft a
pick belongs to; this one covers the drafts that have no picks to number.*

---

## A named award is its own predicate, separate from an honour-team selection

**Ruling, 8 September 2026**, on Pro Football Archives' 229 award pages.

**They are two assertions.** An all-league selection names a man to a team **at a
position** — one of eleven, or twenty-two. A named award says he **won a singular
thing**: no position, no team, no seat.

| | |
|---|---|
| `honour_team_selection` | 10,693 rows. Year, honour as printed (`All-NFL`), position, club, selectors. |
| `award_won` | 909 rows. Year, award as printed, league, club, selectors. **No position, because there is none.** |

### The evidence is one line on one page

**1957 NFL Player of the Year: Jim Brown, Johnny Unitas and Y. A. Tittle.** Three
men, three rows, three selectors — AP, NEA and UP. Not a contested fact. Three bodies
gave three awards and PFA prints all three.

**130 of 778 (year, award) pairs have more than one winner.** So **the selector is
part of the claim and not metadata about it.** Drop it and one year in six becomes a
false disagreement the archive would then be asked to resolve — a disagreement nobody
is having.

### The alternative, and why not

**One widened predicate covering both** is simpler: one definition, one family, one
thing for a consumer to learn. It fails on the field that would have to be there and
would mean nothing. **`position` is real on 10,693 claims and meaningless on 909**,
and a reader could only tell which by testing whether it was null — which is not the
same question as *what kind of honour is this*, and would silently agree with it most
of the time.

Every consumer would carry that test. **Merging two predicates later is easy;
separating one later is not** — by then the claims are written and nothing records
which kind each was. Same shape as the probable-line-up and team-photograph rulings:
when the assertion differs, the predicate differs.

### The club is not membership, on either

Stated in both definitions, as `ghosts.honour_selection` already said it. The subject
is the **person**; neither predicate is ever scoped as a stint. `club_as_printed` says
who he was with when he was honoured — nothing more. A man can be named All-NFL by two
selectors and by neither of two others; the honour is the selector's act, not the
club's.

### Renamed, not twinned

`ghosts.honour_selection` became **`honour_team_selection`**. **Renamed** — there is
one predicate and both sources write it, rather than a `pfa.` twin beside a `ghosts.`
one. A source prefix belongs on a predicate where sources **mean different things**;
`roster_membership.*` is prefixed for exactly that reason. Fenton and PFA mean the
same thing by an all-league selection, and `source_id` already records which said it.

The Ghosts ingest was re-run rather than the store edited, so the 34 claims are
derived under the new name and nothing was rewritten in place.

### Selectors are held as printed

`AP` stays `AP`, with that page's own legend beside it in `selector_legend` —
`AP=Associated Press`, `NEA=Newspaper Enterprise Association`, `UP=United Press`.
Expanding it in the value would be the archive rewriting a source's shorthand, and
the legend differs by era: 1957 says `UP`, 1965 says `UPI`, and they are the same
agency on either side of a merger. **That is a reading, and readings are declared
elsewhere.**

### What it cost, and what it refused

**10,892 claims joined; 710 left as leads.** A name is not a person: a row whose name
matches nobody is a lead and not a join.

**Corrected the same day.** The first pass joined on the NAME ALONE and left 2,113
leads, Jim Brown's 1957 award among them — while the row said *Cleveland Browns,
1957*, and only one of the two men of that name held a season there. The club and the
season are on the claim and must be used: **1,206 ambiguous names were settled by
them**, and the leads fell from 2,113 to 710. The counts above are also corrected:
the first pass read 30 header rows (`All-AFL | Position | Team | Selectors`) as
awards.

*Related: `an honour is not club membership` — this splits that ruling in two, because
one of the two honours has no position and the other cannot do without one.*

---

## A nickname is a name, and it is registered per man rather than read

**Ruling, 8 September 2026.** Where the archive holds a man on the very club-season a
source names, and the only difference is a **playing name against a legal name**, they
are one man and a register records it.

### Why it is not a reading

**No string operation turns `Blood` into `McNally`, or `Bruiser` into `Frank`.** A
reading is a function from a printed string to a fact; there is no such function here.
Building it as one would mean inventing the function, and it would then apply itself
to strings nobody had looked at. **It is a recorded decision per man — the shape of a
merge** — carrying the two names, the club-season that establishes them as one man,
and the source that printed each.

### Neither name is canonical

**The nickname is a name, not an alias for a name.** Both go on the person as name
claims with their own sources; neither is filed under the other; search finds him by
either. `Bruiser` is what the club called him and `Frank` is what his birth
certificate said, and **neither corrects the other**. The archive does not choose
between two things a source printed — the same rule that makes it hold three birth
dates.

Confirmed on the built model before this was called done: `Johnny Blood` and `Johnny
McNally` both return `P_014605`; `Frank Kinard` and `Bruiser Kinard` both return
`P_000717`.

### What is refused, and it was seen to be refused

**An entry that cannot point at a club-season both names share.** Without it this is a
surname rule, and a surname is not a man — the trap this archive has walked into
repeatedly. The route's self-test runs first and each refusal was made to happen:

| | |
|---|---|
| a person the archive does not hold | refuses |
| no club-season at all | refuses — *"without one this is a surname rule, and a surname is not a man"* |
| a club-season the man holds no season on | refuses |
| fewer than two names | refuses |
| a person holding neither name | refuses |

Nine entries: Steamer/Clarence Horning, Bruiser/Frank Kinard, Socko/John Wiethe,
Bucko/Frank Kilroy, Goose/Austin Gonsoulin, Spider/Carl Lockhart, Buzz/Wally
Highsmith, Ezekiel/Ziggy Ansah, Johnny McNally/Johnny Blood. **It is a route, not a
list** — Frank Kinard is seven award rows today and the next source will bring more.

### What it is NOT for

**A misspelling.** `Solomon Eliminian` for Elimimian, `Aaron Doanld` for Donald, `Mark
Muprhy`, `Corey Grahm`, `Alex McGogh`, `Chris Garett`, `Fred Denfield` — seven on
PFA's award pages. **A typo is not a playing name.** The club misprint route is the
shape for those; these are reported and left alone, and the register refuses to become
a place where any two similar strings can be declared one man.

*Related: `an alternative name is not a misprint` — the club-table version of the same
distinction, one level up.*

---

## A looser name match is safe only when a club-season holds it

**Ruling, 8 September 2026.** A match on **surname plus forename initial** joins only
where the candidate **holds a season on that exact club-season**. The club-season is
what makes it safe; without it the rule is the surname trap.

**199 joined**, across 71 people — Oke/Oak Smith at Rock Island 1920, Ink/Inky
Williams at Hammond 1923, Lavern/Lavvie Dilweg at Green Bay 1927–31, Eddie/Ed Lynch,
Charley/Charlie Trippi, Clay/Clayton Tonnemaker, Gordy/Gordie Soltau.

**One was refused, and it is the whole argument for the guard.** *Cam Heyward*, 2024
Pittsburgh Steelers: the candidates are **Connor Heyward and Cameron Heyward**,
teammates on that very club-season. Surname and initial match both. The rule refuses
rather than choosing, and a rule without the club-season would not even have noticed.

**Measured effect on the award ingest: leads 710 → 511**, and with the nickname
register **→ 489**.

*Related: `a join must use every field on the row` — the same lesson, one step
earlier: the club and season settled 1,206 ambiguous names before this rule was
reached at all.*

---

## A surname unique on the club-season is enough — and only that

**Ruling, 11 September 2026 (Ryan), from the Football Hunting folder.** A caption
printing `Speck`, where exactly one Speck is held **on that club-season**, joins to
that man. A second man of the surname on the same roster refuses both, and a
document printing the surname twice in one list cannot join both to one man.

**This is narrower than the existing tiers, not looser.** "Unique in the archive" is
the trap that has bitten four times — Andy King, Talbot, the 1934 Reds, the era
join — because uniqueness among the names the archive happens to hold is satisfied
by the *absence* of the right man. Unique among twenty men already on one roster is
a different proposition. Without it a team photograph is worth almost nothing,
because captions print surnames.

**Measured on the folder: 45 exact, 175 on the surname, 41 not joined** (38 not on
the club-season, 3 refused because two men of the surname are on it — Crowther on
Frankford 1925, Owen on the 1934 Giants, Higgins on Canton 1921).

**What I got wrong first, and why it matters.** I added a forename test the ruling
did not contain: refuse when the printed forename meets none of the held forms. It
refused ten men the ruling joins, and the reason was never the forename — it was
reading. `Hendrian, Oscar George` is surname-first; `Norman Speck` is Dutch Speck;
`"Potsy" Clark` and `"Dutch" Clark` became two bare Clarks and refused each other.
A disagreeing forename is now written on the claim, not refused on (eight, all
nicknames but one: `Dick Jappe` against a held Paul Jappe).

**A spelling variant is not this** (ruling Three). `Cocoran` against Bunny Corcoran
is a spelling question; folding it would be the misprint rule in reverse. Variants
are reported as candidates and joined to nobody.

Gate: `src/gate_surname_on_club_season.py` S1/S2, counted from the read model with
the claim's own store left out.

**And a join has to say where it was made, or nobody can check the man is there.**
The first write put Pro Football Archives' ten facts about Bill Coleman — his full
name, birth and death — onto **P_002554, a Buffalo 1921 Smith**. The Coleman block
read a person id it never set, and inherited the one the Courier section had just
joined. No surname check could see it: Coleman's is a ruled attachment, not the
surname tier. I found it by asking which person the claims were on. Now every joined
claim carries `_joined_on` — the club-season its join was made on — and the gate's
S3 fails any joined man who is not on it. Run against the defective store first, it
failed on exactly those ten. The move to P_045339 is stated in the store's own loss
record as the correction it is.

---

## An empty club-season is opened by the document that names its squad

**Ruling, 11 September 2026 (Ryan).** Dayton 1919, Pottsville 1924 and Portsmouth
1929 held nobody; the document naming the squad opens each, as Bethlehem and
Gilberton were. They enter the club table under `CLUBS_NAMED_BY_A_DOCUMENT`, unlinked
to the NFL clubs that followed.

**Opening a season is not permission to mint.** Most of the 1919 Triangles are
surely the 1920 Triangles. So each man is placed by evidence written on his claim,
against the same city's *next* season, which the archive holds — a neighbour, never
a lineage:
- exact full name, one person in the archive, and he is on the neighbouring season →
  joined (3: Chuck Bennett, Buck Weaver, Chuck Braidwood);
- any namesake on the neighbouring season, an exact name held elsewhere, or a bare
  surname with a namesake playing within two years → **candidate**, neither joined
  nor promoted (31 — Mahrt beside Al Mahrt, Robb beside Harry Robb);
- nobody → a lead, promoted (18).

A score line is a third assertion: Scott and Boyd scored for Pottsville and are in
neither the eleven nor a substitution. The route refuses the evidence kind by default.

**Then the 31 were ruled (Ryan, same day): a surname unique on the club's adjacent
season places a man, as a surname unique on the club-season does.** The club does the
work, not the calendar. **It was measured before it ran.** Across every club and pair of
consecutive seasons the archive holds, a surname unique on both rosters belongs to two
different men 1.30% of the time with birth dates to prove it, plus 0.14% undated — and
for 1915–1935, 16 of 1,779 (0.90%) plus 2 undated. Rare, so the rule stands. **And the
refusal is built in:** two men of the surname on either roster — the season joined to, or
the document printing it twice — refuses. That is the single-club-season test across the
boundary, and it refuses the Nessers at Columbus, the Horweens at the Cardinals and the
Robbs at Canton without anyone naming them. What it cannot see is brothers one per season
— Steve and Bill Owen at Kansas City, 1925 and 1926 — which is the residual 1%.

**Two defects of mine, both found only after publishing, both the archive's own lessons
again.** First: the join roster read the *league token*, and PFA's coaching seasons carry
`NFL`, so the photographs captioned "Steve Owen, Coach" (1934 Giants) and "'Potsy' Clark,
Coach" (1932 Spartans) joined both men as **players** — the 1934 Giants were served with 29
members instead of 28. The roster is now the playing roster, read by predicate from the
declared staff list (`a coaching season has one shape`: read the predicate, never the
league). My first measurement of the defect made the same mistake and reported zero.
Second: once the promoted men were published, the ingest found them in the read model as
"an exact name held elsewhere" and "a namesake nearby" — themselves — and nine of eighteen
fell back to candidates (`a decider that reads its own output`). The store's loss record
caught that before any rebuild, with 11 claims lost for no stated reason.

---

## Three readers in the old place — measured before they were fixed

**2026-09-11, Ryan's three reader fixes.** None was a defect in the claims; each was the
layer that presents them, and each was measured on the *served output* before a line
changed.

1. **The bios read `IND` as a league.** `league()` printed any token its name table
   lacked, and the crossed-leagues lead said "a new" whenever two club ids shared a name.
   **96 served bios** printed `IND` — 18 from the three seasons opened that day, **78 that
   already read so before it** — and 33 said "a new", 14 of them with no `IND` at all
   (the Brooklyn Dodgers of the AAFC, the Hamilton Tigers of ORFU). Ruled: say what the
   archive knows. An independent season reads "outside any league"; the clubs are named
   in full, each with its own league, so nothing asserts or denies a lineage. Gate:
   `src/gate_bio_no_pseudo_league.py`, tokens read from the declaration, 11,446 bios.
2. **The bio read PFA facts from one file by name.** 32,662 people held PFA facts it could
   not see — and every one was already on the index record it loads, under the *prefixed*
   key `pfa.<field>` that its reader never asked for. **4,442 bios gained a close; 203
   swapped one**: the close order puts military service before death, so a man whose
   service record lived in another store now closes on his service, not his death.
3. **`club_staff_role` was held and not served.** The club-season view read `scope='stint'`
   only. Gate C3 now fails any staff claim its view does not list, and any listed among
   the coaches.

**And the comparison caught my own regression**: rendering all 50,056 bios with the old
and new code and diffing the *text*, 792 changed that no fix explained — a comma I dropped
from the one-game sentence. Measuring only the bios I meant to change would have shipped it.

---

## A column added by hand to a generated document is a column the generator will drop

**2026-09-11.** Another session added five newspaper-citation columns to the three hunting documents
by hand. `write_hunting_docs.py` regenerates all three and did not know them: the next run would have
removed them without a word — the fourth way a field goes quiet, *stale because the data around it
changed*. The writer now reads them from the sweep's published report and carries them on the one row
list; `gate_hunting_docs_citations.py` runs a writer into a scratch HOME and fails if any rendering
lacks them. **Run against the committed writer first, it failed H1–H4.**

**And reading the report, not the working files, showed what the report does not carry.** It covers
the hunt rows only: 423 of the hunt rows regenerate with the hand values exactly, cell for cell, and
**328 non-hunt rows cannot** — the report holds a page's existence only where the page cites a paper.
Those rows now say *not in the sweep's per-row report* rather than a guessed `nobody`. The honest fix is
upstream, a per-row report for every row, not a second derivation here.

**Also, the same evening: a spread operator overwrote a fact.** The club-season view built each attribute
as `{"kind": "mascot", …, **claim_view(r)}`; the claim's own `kind` (*observed*) came last and won, so
Two Bits was served as kind "observed". Gate A4 caught it — held is not served, and served wrong is not
served either.

---

## A trainer is a fact about the club-season

**Ruling, 11 September 2026 (Ryan).** `club_staff_role` holds trainer, manager,
business manager and president exactly as printed, on a **club-season subject**,
naming no person. It is kept apart from `role_title`, which the bios read. Twelve
claims: seven managers, Herman Smith (Canton 1923 trainer), John V. Mara (Giants
president) and three possible Racine trainers under a heading that may not label them.

**The archive holds a namesake for three of them and none is the man.** Herman Smith
is also P_008811, who played 1994–2003; Storck and Talbott resolve to Dayton's own
later men. A staff role that joined on a name would have been the unique-in-the-archive
tier again. Gate C1/C2.

---

## A man named in a team photograph caption is a person

**Ruling, 8 September 2026.** Stated as a property, not as an instance: a man named
in the caption to a **team photograph**, where the **caption names the club**, on a
**club-season the archive holds**, qualifies for promotion under the standing rule.
All three conditions or nothing.

**Why the narrowness is the ruling.** The twelve Pacific Coast Wildcats men failed the
old rule not because they did not play but because PFA's box scores only see men who
**started**, and no source ever gave that club a roster. `AFL|1926|AFLPC` is one of
three club-seasons in the whole archive whose men were derived from box-score
appearances. A squad man who never started was not merely unrecorded — he was
**invisible by construction**. They were excluded by a gap in the evidence, not by
evidence of absence. A man in uniform, in the team picture, named by his club's own
opponent's programme, has a stronger claim to membership than most of what places men
on 1920s clubs.

**A caption alone is not enough.** A name in a photograph of something else is not
covered, and neither is a club-season the archive does not hold. The conditions are
checked in `promote_players.qualify()` and again as properties in
`src/gate_team_photograph_promotions.py` (T1, T2), which names no man.

**The predicate does not move.** `programme.team_photograph` is not roster membership
and does not become it. The man becomes a person; the claim keeps saying exactly what
it said — that he was photographed with this club, not that he played. **T3 is the
gate for it**, and it is the property most likely to erode, because it would erode
silently: a later ingest writing one of these men onto a roster would look like
ordinary coverage. Zero of the twelve carry a `roster_membership` claim.

**Promoted: twelve.** D. Carey, H. Shipkey, C. Johnston, E. Clark, L. de Wolf,
D. Morrison, R. Reed, N. Busch, **G. Wilson**, R. Morrison, E. McRea, C. Walters.
`P_045355`–`P_045366`. Each carries the per-man no-match evidence the route already
records, and all twelve carry `forename_unknown`, because a caption that sets
`D. Carey` gives no forename any more than a bare surname does — the flag was extended
from "no space in the name" to "an initial where the forename should be".

**G. Wilson is George "Wildcat" Wilson**, the University of Washington back the club
was named after and the reason the enterprise existed at all. That the archive did not
hold him on his own club-season is the clearest possible illustration of why the
ruling is needed.

### The alternative, stated

**Refusing them is the conservative option, and it was the standing rule until today.**
It has a real argument: being photographed with a club is not playing for it, and the
archive's own predicate definition says so in as many words. A team photograph can
include men who never took the field — trainers, late signings, a squad member cut the
following week. Promoting on a photograph means the archive holds as people some men
who may never have played a down.

**What that costs is twelve men who demonstrably existed remaining invisible**, on a
club-season the archive already holds, because the only source that saw them was not a
box score. The archive would be recording not what is known about 1926 but what one
kind of document happens to preserve. The ruling accepts a weaker class of membership
evidence in exchange for not letting the shape of the surviving record decide who
counts as a person — and it keeps the two apart in the claim, so a reader can always
see which kind of evidence a man rests on.

*Related: `a join must use every field on the row` and `a looser name match is safe
only when a club-season holds it` — the club-season is doing the same work here, as
the condition that makes a weaker signal safe.*

---

## A disambiguator is evidence about which club is meant

*Ruled by Ryan, 2026-09-09, on two instances of one defect a day apart in the same
survey. `declarations/clubs.json` → `WITHDRAWN_STRINGS`; gated by
`src/gate_fandom_bindings.py`.*

**A source that disambiguates a reused club name in its own page title is telling the
archive which club it means. Stripping that parenthesis before matching discards the
only thing that distinguishes two clubs of the same name.**

The 2026-09-06 fandom club-name survey binds each entry to one club in the table and
hangs that entry's variant names on it — 141 strings. Fandom titles a reused name with a
qualifier: `Cincinnati Bengals (1937–41)`, `Chicago Bulls (AFL)`, `Brooklyn Dodgers
(NFL)`, `Philadelphia Stars (football)`. `build_clubs.py` stripped it with
`re.sub(r"\s*\([^)]*\)\s*$", "", canon)` before looking the name up, on the reasonable
assumption that it was noise. For six of the eight it is. For two it was the whole
message.

### The two instances

**`Rochester Tigers` → `club-brooklyn-dodgers-1930`.** The NFL Brooklyn Dodgers became
the Brooklyn **Tigers** in 1944; the survey entry for the 1937 AFL Rochester Tigers
carried that name among its variants, and the loose fallback route — *bind on a variant
that is an archive name, when the canonical is not* — matched it. **The archive
corroborates against it from its own holdings:** the season-key token `B/R` is printed
*"1936 Brooklyn/Rochester Tigers (AFL)"*, the second AFL's club, which moved from
Brooklyn to Rochester and is the same club as the 1937 Rochester Tigers. Two clubs, two
leagues, seven years apart.

**`Cincinnati Bengals (1937–41)` → `club-cincinnati-bengals-1968`.** Found by the gate
written for the first instance, which is why the gate exists. The years in the title say
1937–41 and the club it landed on lived 1968–2024. Its sibling `Cincinnati Bengals
(AFL)` came from the same survey entry and is wrong for the same reason — **and no gate
can see that one**, because the 1968 club really did play in an AFL: the 1968–69 one,
not the 1937 one. *A league abbreviation is not a league*, and here the abbreviation is
all the printed title offers.

### What the ruling does and does not do

**It withdraws the binding, not the source.** `WITHDRAWN_STRINGS` refuses a string at the
one place strings enter `build/clubs.json`, and records the refusal. Nothing is deleted
from the survey and the survey is not corrected: the archive simply declines to record
that name on that club. `build/clubs.json` is rebuilt from its sources every run, so an
edit would be gone by morning — a withdrawal has to be a declaration or it is nothing.

**It withdraws the NAME, not one spelling of it.** The match is on the bare form. The
first rebuild withdrew `Rochester Tigers` and left `Rochester Tigers (AFL)` sitting on
the same club, because the survey adds each name twice — the canonical as a
`printed_name` and the disambiguated variant as an `alias`. The Bengals entry had put the
same name on the club **four** ways: `(1937-41)` with a hyphen, `(1937–1941)` with an en
dash, `(1937–41)` again as a printed name, and `(AFL)`. One ruling, one name, every
spelling.

**It is scoped to the source.** The bare form `Cincinnati Bengals` is the 1968 club's own
official name. The withdrawal names `fandom_redirect` and takes only what the survey put
there; the official name and the `pfa_cell`, `coaching_tree`, `season_key` and
`media_guide` strings are untouched. `resolve("Cincinnati Bengals", 1970)` still returns
the club by its own name; `resolve(..., 1937)` returns nothing, which is true — the
archive does not hold the AFL Bengals.

**Neither withdrawal moved a claim.** `Rochester Tigers` was used by 0 claims;
`Cincinnati Bengals` by 118, every one resolving at 1968+ through the official name. What
was wrong was **provenance** — a club recording names that belonged to a different club —
and provenance is worth correcting even when nothing resolves through it, because the
next thing that asks will get a wrong answer silently.

### The alternative, stated

**Matching on the bare name is simpler, and it is what the code did.** A disambiguator is
a wiki's editorial convention, not a fact about football; it is inconsistently applied,
it is sometimes a league abbreviation that means two competitions, and parsing it invites
the archive to read meaning into someone else's punctuation. Stripping it lets a survey
of several hundred entries attach cleanly with one rule.

**What that costs is that a reused name binds to whichever club the survey happened to
reach first.** There is no tie-break and no error — the second club is simply never
considered, and the first one silently acquires a name it never bore. That is not a
matching problem the archive can detect after the fact: by the time the string is on the
club, the evidence that it belonged elsewhere has been thrown away. Reading the
disambiguator costs a comparison; not reading it costs the distinction between two clubs,
and the archive has now found that twice in the same survey.

*Related: `a league abbreviation is not a league` — the limit on how far this can be
taken, and the reason `Cincinnati Bengals (AFL)` needed a ruling rather than a gate.*

---

## A printed roster is a roster — and the refusal is what made the declaration mean anything

**Ryan, 2026-09-09.** A squad list printed in a **named published work** and attributed to
a **named archive** is roster evidence. It is the same object as page seven of the 1926
Bears–Tigers programme and the PFRA Annual's St. Louis Gunners rosters: a document naming
who was on a club. That it was set in 2025 from a 1905 scrapbook rather than in 1905
changes who set the type, not what the source asserts.

`printed_roster` is now a declared roster evidence kind. It reaches the PFRA Annual's 101
leads and frankfordyellowjacketsbook.com's 103, and 133 men became people under it.

**The half worth writing down is what happened first.** `promote_players.py` met the kind
and **refused it**, by name:

> `evidence kind 'printed_roster' is not declared as a roster. A lead shape this route
> does not know is refused, not promoted.`

That refusal was correct and it is the point. **The alternative is that any ingest can
widen what counts as roster evidence by naming its own lead shape something new** — write
`evidence_kind: "printed_roster"` into a lead and the route promotes on it, and the
declared vocabulary means nothing because anything can join it. The route stopped and
asked, and a person answered. A rule that cannot be widened without a ruling is the only
kind that survives the next ingest.

**Two things the ruling forced, both recorded where they happened.**

*The vocabulary moved into the declaration.* `ROSTER_EVIDENCE = {"roster_page", "roster",
None}` was **typed into the script**, so there was nowhere for the ruling to live — the
classification-by-string pattern again. `declarations/player-promotions.json`
`_roster_evidence_kinds` is the list now, and `promote_players.py` reads it and refuses to
fall back to a typed set if it is missing.

*"A club-season the archive holds" means the club table, not the index.* The test counted
men in the index, so a club-season with none was "not a club-season yet" — which made an
**empty club-season unfillable forever**: the first man onto it could never be promoted,
because he would be the first. Frankford 1899, 1900, 1903 and 1906 are held by the club
table and by nothing else, and not one of their 70 men could have been promoted under the
old test. Same reasoning as the team-photograph ruling of 2026-09-08: a club-season with
no roster excludes its squad by a gap in the evidence, not by evidence of absence.

*Related: `an ingest must not invent a club code`, and the team-photograph ruling — the
other place a qualifying kind was widened, and widened by a person.*

---

## Era is not identity — and a source's own id outranks a name

**Ryan, 2026-09-11**, on the 747 player leads refused because more than one held man
carries the printed name.

### The evidence is a measured error rate, not an instinct

Split by era, 395 of the 747 had exactly one candidate playing within three years of the
lead. That looks like an answer. It was about to be recommended against on principle —
tier 2, *uniqueness satisfied by absence*, is inadmissible — and Ryan asked the better
question first: **is era really the only evidence they carry?**

It was not. PFA's team pages link every roster name to PFA's own player page,
`/players/m/murp03750.html`, and the ingest had kept the text and thrown the link away.
383 of the 395 carry a code. Read against the codes the archive already holds:

| the lead's own PFA code | leads |
|---|---:|
| is the era candidate's | 260 |
| is a **different** candidate's | **9** |
| is held by nobody, while the era candidate holds a different one | **96** |
| undecided by code | 18 |

**Era put 105 of 383 checkable leads on the wrong man — 27%.** Lamar Jackson, UFL 2026,
went to the Ravens' quarterback; the code is the other Lamar Jackson's. Jon Baker, WLAF
1995–97, went to the Jon Baker of 1995–2001; the code is the 1991 man's.

### The rule

1. **A lead whose code is held by exactly one of the held men of its name is placed on
   him.** A source-native identifier, not a judgement — the same thing that made the
   gamelog join clean. It is not tier 2: tier 2 is a *name* that happens to be unique.
2. **A lead is a new person only where nobody holds its code** — and either every
   namesake played more than three years away, or every namesake holds a different code.
3. **Without a code, an ambiguous lead stays ambiguous.** Era is never enough.

### What the rule caught before it was applied

The first form of rule 2 was *every namesake more than three years away*. Measured
against the codes, **36 of those 236 leads are one of the namesakes** — Jack Roberts,
Louisville 1938–39, is the Jack Roberts held for 1932–34. A four-year gap is a career, not
a stranger. The code condition was added before anything was promoted, and
`src/gate_code_identity.py` holds both halves: a placement by code must match exactly one
candidate, a new person must match none, and each was shown failing first.

### And the cause, which is the older lesson

**The leads never recorded a code the source printed.** A fact held where nothing can
read it — the same shape as a disagreement written only into a report. The code now rides
on every lead and every roster claim, so nobody has to re-derive it from disk.

*Alternative rejected:* **decide the 395 by eye, as era judgements.** It reads as
diligence and it is tier 2 done by hand, at a measured 27% error rate. *And the one
nobody proposed but the data nearly forced:* promote all 236 as new on era alone, which
would have made 36 men twice.

*Related: `uniqueness satisfied by absence`, `a join must use every field on the row` —
and the measurement of this very queue, which on 9 September joined on the name instead
of the lead's id and reported 362/225/158 for what is 395/116/236.*

---

## A store backup is a rollback aid, not a backup

**Ryan, 2026-09-11.** Store backups are not committed. A 56.5 MB copy of the PFA club-roster
store was pushed that day and GitHub warned; **it stays in history**, because rewriting a
published branch is worse than a large blob — the roster project's own precedent.

### What a store backup is

A copy of a `build/` file taken immediately before a run overwrites it:
`build-reports/<store>-store.before-<date>.json`. It exists for **one** thing: undoing or
diffing that run, within the session that made it.

### How long it matters

**From the overwrite until the rebuild that consumes it is verified** — its gates pass, P3
holds, the model is published, the code is committed. Hours, not days. After that, the
previous state is reproducible from the committed code and declarations at the prior commit
plus the sources on disk, and its claims sit in the two previous models the service keeps.
**A store backup may be deleted after that; nothing deletes it automatically.**

### Where it is safe — the other half, and the reason for writing this down

**Nowhere durable.** `build-reports/` is on this one machine and outside git. A backup kept
only there protects against a bad run, not against losing the machine. That is fine for what
a store backup is for, and it would be a mistake to let anyone read it as more.

**None of the three taken on 2026-09-11 is the only copy of anything**: all three were committed
before this ruling and are in git history. A backup taken under the rule will not be.

### What this does NOT cover, and is Ryan's

**The only copy is `build/` itself** — 8.6 GB on 2026-09-11 (ARCHIVE_CONTEXT still says 3.2),
gitignored, no history — **and the mini has no machine-level backup at all**: `tmutil
destinationinfo` answers *"No destinations configured."* The sources, the served model and the
two kept models are on the same disk. The laptop's copy is from 7 September and is due to go
after 21 September; the external drive is not mounted here. A store backup cannot fix that and
must not be mistaken for something that does.

### A record is not a backup

A file a gate or the service **reads** — the Ghosts reader's G6 baseline, the index-orphans
reversal lists — outlives the session by design and **is tracked**. `src/gate_store_backups.py`
holds the line: B1 no store backup tracked, B2 every one on disk ignored, B3 **nothing in code
reads a store backup**, because the moment something depends on one it has become a record.

*Alternative rejected:* **keep committing them**, as the session did that morning.

---

## A join keeps its league — the fourth time, and three rulings with it

**Ryan, 2026-09-11.** HOU 1984; the disagreement claims hardcoding `NFL-{year}`; the gate's own
copy of the resolver; and then the coaching join, where `CHI` in a 1974 WFL cell became the 1920
Decatur Staleys because the code was looked up with no league. **A claim's club must play in the
claim's league that year. A refusal is better than a wrong club.** Gated as the property —
`src/gate_claim_league.py`, L1 on claims and L2 on index keys — never as the instances.

**The fix found two more places that read a league without its year**, which is the shape to
expect: the club table building PFA-only clubs, and the coaching keys. A rule fixed in the
resolver alone is fixed in one of its four readers.

**A league abbreviation and a year can be a league.** `USFL` names 1983 and 2022; `UFL` 2009 and
2024. PFA prints the bare label, so its 2022–24 claims sat in the older competitions and every
one of those club-seasons was held twice. Read at read time with its year
(`LEAGUE_LABELS_BY_YEAR`, `league_tokens.read_label`), store unchanged. *Alternative rejected:*
apply the strict resolver first — 19,883 claims whose club was right would have been refused for
a label.

**A club that moved within a season is one club under two printed names** — New York Stars/
Charlotte Hornets and Houston Texans/Shreveport Steamer, 1974 (`RELOCATIONS_WITHIN_A_SEASON`).
The destination's code-year is silenced only if it holds no man; **no man moves**, because nothing
the archive holds says which city a man played in, and guessing which half of a season is not a
placement. *Alternative rejected:* split the men by the relocation date — there is no dated
evidence placing any of the 147.

*Two of my own instruments were wrong on the way and the live runs said so:* a code shared by two
leagues' clubs is not a split club-season (1926 `BKN`), and a club lawfully plays two leagues in
one year (Regina, CFL and WIFU). It makes the
repository a slow, public, size-limited backup for 8.6 GB it was never meant to hold, and it
gives the feeling of a backup without the fact of one.
