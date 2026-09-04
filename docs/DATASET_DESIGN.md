# A historical record of professional football, held as data

**Design proposal, first pass. 2026-09-04.**
Nothing here is built. This document is for Ryan to rule on, section by section.
Where I am uncertain I say so, and say what measurement would settle it.

The project has no name yet; this file calls the thing "the dataset".

> **This file does not belong to the PGM3 roster project.** It is the design for
> the new dataset, parked in this repo only so it can be read. It moves to the
> new repo once Ryan points a session at it, and nothing here should be treated
> as guidance for a PGM3 build.
>
> **Companion file: `DATASET_PRECEDENTS.md`** — method rulings and documented
> failures for this project. Kept separate from `PGM3_PRECEDENTS.md` by Ryan's
> ruling (2026-09-04): different project, different lifecycle, and the roster
> project's precedents are about *building files* where these are about
> *representing knowledge*. **Cross-reference, do not merge.**

---

## 0. Before the design: what I read, and what I could not find

Read in full or in the relevant part: `PGM3_PROJECT_HANDOFF.md` (1,553 lines),
`PGM3_PRECEDENTS.md` (4,232 lines, ~40 sections read closely),
`PGM3_AUDIT_BACKLOG.md` (948 lines), `PGM3_DATA_SOURCES.md`, the repo `CLAUDE.md`,
and the 1979/2000/2026 task documents. Also opened the source tree on disk to
check that what the documents describe is actually there.

**Two corrections to the brief.**

1. The files are `docs/PGM3_DATA_SOURCES.md` and `docs/PGM3_AUDIT_BACKLOG.md`.
   There is no `DATA_SOURCES.md` or `PGM3_BACKLOG.md`.

2. **There is no list of eight namesake collisions.** The repo records at least
   twelve distinct shapes, spread across four documents and never gathered. I
   have gathered them in §2.2, and they are now the reference list. Two of the
   four cases the brief named by hand — *two Bill Walshes on 1979 staffs*, and *a
   coach and his senator son* — are in no file, no commit, and no part of the
   source tree; they came from build-session reports that were never committed
   (established with Ryan, 2026-09-04). The first is covered by shape 1 or 2. The
   second names a real boundary and is taken up in §9.8.

**One thing I found by opening the sources rather than reading about them**, which
changes §2 materially, and which is not in `PGM3_DATA_SOURCES.md`:

StatsCrew's player URLs carry a **collision counter**. The cached pages include
`p_allengeo002`, `p_gibbsjoe002` and `p_bennelee002` — the *second* George Allen,
Joe Gibbs and Lee Bennett. The slug is `{surname[:5]}{forename[:3]}{NNN}`, and the
`NNN` exists precisely because names collide. StatsCrew covers every professional
league in American history and has therefore already performed namesake resolution
across the whole population, and published its answer as a stable identifier.

That is a large, free head start on the hardest question in the project.

**It has since been tested** against the recorded collisions, and it holds — with
a second dimension the filenames did not show: **`p-` and `c-` are separate role
namespaces**, and the counters do not align across them. Method and results in
§9.1; what it means for the model in §2.4. The short version is that the source
resolves the collisions *and* answers the harder question of the man who both
played and coached, by carrying a bidirectional link between his two records —
but it does not reach assistant coaches at all.

---

## 1. The stance, in one paragraph

The dataset is **a store of claims plus a resolution policy**, not a store of
values. A source saying something is the atom. What is true is *computed* — per
query, from the claims, under a policy that is itself data and is versioned.
Nothing in the store is ever overwritten by a better answer; a better answer is a
new claim, and the resolution changes. This is not architectural taste. It is the
only structure in which "provenance records where a value came from originally"
can be enforced rather than remembered, and remembering is what failed last time.

Three consequences worth stating up front, because everything else follows:

- **A person has no name.** Names are claims attached to a person. There is no
  natural key anywhere in the model.
- **Identity is a claim too.** "This roster row denotes this person" is a claim
  with a source, a discriminator and a confidence, and it can be revised without
  touching a single fact about either man.
- **Invention cannot enter.** There is no field in the store a drawn value could
  be written into. It has nowhere to live except a build.

---

## 2. Identity

### 2.1 The problem, stated precisely

The prior project reached the same conclusion three times from three datasets and
wrote it down as a precedent:

> A composite key cannot both exclude namesakes and follow a man who moves.
> Position is exactly the field that separates two men with one name AND changes
> for one man over a career. No composite key can do both.

And separately:

> The field that resolves identity varies by dataset. 2026 needed birth date. The
> 2K5 archive needed era. The 1979 rosters needed college. Do not assume the key
> that worked on the last dataset transfers.

Both findings say the same thing: **a key is the wrong instrument.** A key is a
function of the record's fields, and the fields that separate a collision are a
property of the *source*, not of the project. So the design must not have a key.

### 2.2 The twelve shapes, and what actually separates each

Gathered from the four documents. Every row is a case the prior project hit; the
right-hand column is the field that did the work, per its own write-up.

| # | shape | instances recorded | what separates |
|---|---|---|---|
| 1 | same name, same position, same season, different teams | Larry Brown (OT, Miami, 24, KC / OT, Kansas, 30, Pitt); Gene Washington (WR, Stanford, 32, Det / WR, Georgia, 26, NYG) — both 1979 | **college** — position and era both fail inside one season |
| 2 | same name, different position, **same team**, same season | Cleveland's two Robert Jacksons 1979 (OG #68 Duke / LB #56 Texas A&M) | position, jersey, college — `name\|team` merges them |
| 3 | same name, same position, same season, same file | two James Joneses, both RB, 1986 | **team** — `name\|position` silently wrote 1,745 records from 1,746 |
| 4 | same name, different position, same season | Doug Smith 1986 (C Rams / DT Oilers); Gary Anderson 1986 (K / RB); Doug Williams 1986 (QB / OG) | position — this is the one case position genuinely resolves |
| 5 | father/son, **same** position, different eras | Kellen Winslow / Winslow II (TE); Mickey Shuler / Jr (TE); Clay Matthews / III (OLB); Stanley Morgan (WR); D.D. Lewis (OLB) | **birth date**; era only where careers do not overlap |
| 6 | father/son, **adjacent** positions | Antoine Winfield CB/S; Jon Runyan OT/G; Kris Jenkins NT/DT; Jeremiah Trotter MLB/LB; Michael Pittman | **birth date**. Position *adjacency* merged all five when tried |
| 7 | coach father/son, same name, in one file | Jim Mora Sr (2000 IND) / Jim Mora Jr (2000 SF); Frank Gansz Sr/Jr (both KC special teams) | birth date + club-season. Note Gansz's **name string itself** is malformed three different ways across three files |
| 8 | one man, two careers | Chuck Noll: player 1953–59, coach 1969–91. Bill Belichick appears in 1979 as an assistant | **nothing** — this is the inverse failure. A player table and a coach table would split him |
| 9 | modern record poisoning a historical one | D.D. Lewis reads era 2004–2009, `era_certain` **True**; Stanley Morgan reads 2021–2023 | **direct era observation** (a vote from that year's source), never a derived window |
| 10 | same name across a century, both notable | `allengeo001/002`, `gibbsjoe001/002`, `bennelee001/002` in StatsCrew; Belichick / Steve Belichick | source-native ID where one exists; otherwise birth date |
| 11 | **one man**, position changed — a namesake-safe key splits him | Brad Meester OG→C; Aeneas Williams CB→S; Cameron Jordan DE→OLB; Brian Waters TE→G; Julius Peppers DE→OLB; 61 measured cross-band cases nothing has ever flagged | **continuity evidence** — age progression, club continuity, draft slot. Not a key |
| 12 | **one man**, name spelled differently | Nickell Robey → Robey-Coleman; Will/William Compton; Trent/Trenton Robinson; Ed "Too Tall" Jones; `van den Berg`; accented characters; "Kuechly HOF" | normalisation measured against the actual keys, plus 1–11 |

Note the structure of this table. Rows 1–10 want a **wider** discriminator. Rows
11–12 want a **narrower** one. Any single key sits at one point on that axis and
is wrong at the other end. That is the whole argument for §2.3.

### 2.3 The model

**`person`** is an opaque, meaningless, permanently stable identifier. A ULID or a serial —
content-free by construction, so it cannot encode a name, a position or an era and
therefore cannot go stale when any of those turn out to be wrong.

A person record has **no attributes at all**. Not a name, not a birth date. It is
an anchor for claims and nothing else.

**`source`** — a document or dataset: `statscrew`, `mediaguide/pit-1979`,
`coaching-tree`, `nflverse/players@<sha>`, `2k5/1979-1980SAVEGAME.DAT`. Carries
retrieval date, hash, licence note, and — critically — **`derived_from`**, so
lineage is declared rather than assumed (§4.3).

**`source_record`** — an addressable thing *inside* a source: a StatsCrew player
page, one row of a roster table, page 34 line 12 of a media guide, one player
block in a `.ros`. Addressable means: given the source and the record id, you can
go back and look at exactly what was read.

**`denotation`** — the special claim: *this source_record denotes that person*.

```
denotation
  source_record   statscrew/roster/BA1-1950#row-04
  person          p_01J8QK…
  discriminator   ["name", "birth_date", "college"]   # what actually separated
  method          exact-id | attribute-match | hand
  confidence      the source's own, or the method's; never a guess
  observed_at     1950
  by              build/ingest@v3  |  ryan
  status          asserted | ambiguous | refused
```

This one table does the work that a key was doing, and it does it better in five
specific ways:

1. **It records what separated the collision.** The precedent says the
   discriminator varies by dataset. Here it is written down per record, so a later
   session does not rediscover it.
2. **It can refuse.** `status: ambiguous` is a first-class outcome. The three 1986
   players that mode got right by luck (Stephenson, Webster, White) get
   `ambiguous`, are queryable as a worklist, and are never silently resolved.
3. **Splitting and merging are cheap and reversible.** If two men turn out to be
   one, you re-point denotations. No fact about either moves. If one turns out to
   be two, likewise. Under a key model both operations are a rebuild.
4. **Disagreement between sources about *which man it is* becomes data.** This is
   the D.D. Lewis case exactly: the 2K5 archive's denotation was wrong, and its
   *facts* were fine. Separating the two lets you fix one without touching the
   other.
5. **It is the only door.** A claim cannot exist without a source_record, and a
   source_record reaches a person only through a denotation. There is no path by
   which a value arrives with a provenance that names an artifact rather than a
   source.

**Person IDs are never deleted.** A merge leaves a tombstone pointing at the
survivor, because exports already shipped may hold the old id.

### 2.4 Resolution in three tiers

**Tier A — carried identifiers.** Where a source ships its own person id that
already survived a namesake, use it. StatsCrew's slug; nflverse's `gsis_id`,
`pfr_id`, `otc_id`; PFR's player slug. A source-native id is *not* our person id —
it is a claim of the form "StatsCrew's `p-allengeo002` denotes person P", and once
asserted, every future StatsCrew record for that slug resolves for free.

**StatsCrew's identifier scheme, measured 2026-09-04** (33 live pages, plus 64
cached; details and method in §9.1). It is stronger than it first appeared and it
has three traps.

*The shape.* `{prefix}-{surname[:5]}{forename[:3]}{NNN}`, e.g. `p-nollchu001`.
**The prefix is a role namespace**: `p-` players, `c-` coaches. The counter runs
**within** a namespace.

*What it resolves, confirmed on the recorded collisions:*

| shape | slugs | separated by |
|---|---|---|
| Larry Brown 1979 (§2.2 #1) | `p-brownlar002` T, Kansas, b.1949 (age 30) / `p-brownlar003` T, Miami (FL), b.1955 (age 24) | college **and** birth date, both present |
| Gene Washington 1979 (#1) | `p-washigen002` Stanford, b.1947 (32) / `p-washigen003` Georgia, b.1953 (26) | plus a third, Michigan St., b.1944 |
| Doug Smith 1986 (#4) | `p-smithdou001` C-G-T, Bowling Green / `p-smithdou002` NT-DT, Auburn | plus two more |
| Kellen Winslow (#5) | `p-winslkel001` TE, Missouri, b.1957 / `p-winslkel002` TE, Miami (FL), b.1983 | birth date; position identical |
| Clay Matthews (#5) | `p-matthcla001` b.1928 / `002` b.1956 LB USC / `003` b.1986 LB USC | **three** generations; `002` and `003` share position *and* college |
| Jim Mora (#7) | `c-morajim001` b.1935, Occidental / `c-morajim002` b.1961, Central Washington | birth date |

*Trap 1 — the counters do not align across namespaces.* The two real George Allens
are the **player** `p-allengeo002` (George Robert Allen, T, b.1944, West Texas A&M,
one season 1966) and the **coach** `c-allengeo001` (George Herbert Allen, b.1922,
Marquette, HOF 2002). Different men. **A matching slug body across prefixes is not
evidence of the same person.**

*What IS evidence: an explicit cross-reference.* A man who both played and coached
carries a link between his two records, and it is **bidirectional** — `p-nollchu001`
links to `c-nollchu001` and back, both stating birth date January 5, 1932. Across
the 64 cached player pages, **35 link to a coach record and all 35 have an
identical slug body; none links to a different body.** So the rule is: *follow the
link, never the string.* Neither George Allen page links to the other, correctly.

*Trap 2 — HTTP 200 does not mean the person exists.* Seven of the slugs probed
returned 200 with a well-formed page carrying no name and no birth date. Six were
one or two counter values past the last real person; **one, `p-allengeo001`, is a
hole *inside* the range** — empty, while `002` is real. So the counter is not
dense, and enumeration cannot stop at the first empty page. **Existence must be
tested on content — a name and a full birth date — never on status code.**

*Trap 3 — one empty page rendered another man's awards.* `p-allengeo001` displays
four Coach of the Year awards belonging to George Herbert Allen at
`c-allengeo001`. The other six empty pages were clean, so this is one observed
instance and not a demonstrated mechanism — but it is the phantom-match problem
one layer up, and it means a parser that scrapes an awards table off a page it has
not first confirmed is a real person will attribute a coach's honours to a player.

*Coverage limit, and it is the significant one.* **The `c-` namespace appears to
hold head coaches only.** Chuck Noll's coach record reads `1969-1991`, omitting his
1960–68 assistant years; Jim Mora Sr's reads `1983-2001`. Frank Gansz **Jr.**, a
career assistant, has no record at all — `c-ganszfra001` is his father, and `002`
and `003` are empty. So Tier A covers players and head coaches; **assistant
coaches, the bulk of the staff data this project wants, fall entirely to Tier B**,
where the discriminator is birth date from a media guide biography.

*One more subtlety.* The slug body is a truncation, not a name, so it groups
near-names: `p-brownlar004` is **Laron** Brown. The counter is per slug body, not
per person-name — so slug-body collision is broader than name collision, and a
slug body is never a name claim.

**Net: Tier A is real and carries most of the player population for free**, on the
strength of a link rather than a string. It does not carry assistant coaches.

**Tier B — declared discriminators, per source.** Where a source has no id,
attributes do the work — and *which* attributes is a property of the source. Each
source declares what it carries and what can separate:

| source | carries | primary discriminator | fails on |
|---|---|---|---|
| StatsCrew roster pages | jersey, position, **birth date**, height, weight, college, hometown, GP, GS | birth date | (unmeasured pre-1930 — §9.2) |
| footballdb 1979 rosters | jersey, position, games, age, **college** | college | two men, same college, same position |
| media guides | staff **title**, club, season, career-history prose; birth date only rarely (measured, below) | **stint continuity** — club + season + title + prior-stint narrative | men absent from the guide |
| nflverse `players.csv` | birth date (100%), college, position, `pfr_id` | birth date | pre-1974 rookies |
| Coaching Tree MCP | staff, birth dates, per-year stints | birth date | (role labels unreliable — §8.3) |
| 2K5 archive | skin band, era **votes** | presence of a season vote from that year's file | same-position cross-era namesakes |
| Madden / mods | age, position, ratings | age within ±6 of a known birth year | fathers and sons at adjacent positions |

The declaration is data, not code. Adding a source means declaring its fields and
its discriminator, and the ingest refuses to run without one.

**Media guides do not carry coach birth dates — measured 2026-09-04, and it moves
assistant-coach identity onto a different mechanism.** Across the 28 cached 1979
guide texts, matching 638 coach-title occurrences and reading the 1,200 characters
following each:

| | n | share |
|---|---|---|
| explicit `Born:` date | 17 | 2.7% |
| age in prose only ("at 36 is the youngest…") | 37 | 5.8% |
| neither | 584 | 91.5% |

**21 of the 28 guides carry no birth date anywhere near a coaching title.** That
file-level count is the robust one: the 638 denominator includes contents-page and
roster-listing mentions as well as real bios, so 2.7% is a **lower bound** on
bio-level coverage — but no plausible correction rescues a discriminator present
in a quarter of the files and absent from the rest.

*What the guides do carry, richly:* the **exact title** — Pittsburgh's 1979 entry
reads "WOODY WIDENHOFER / Defensive Coordinator" — the club, the season, and career
history in prose ("in his 15th year of coaching", "came to the Steelers in 1973").

**So the discriminator for assistant coaches is stint continuity, not birth date**
— the same mechanism §2.2 shape 11 needs for a man who changes position, reached
from the opposite direction. An assistant is identified by the chain of club-seasons
and titles his bios describe, and two men of one name are separated where their
chains do not join. Frank Gansz Sr and Jr are separable this way (KC 1981–82 and a
head-coaching spell, against Raiders 1998–2000 / Chiefs 2001–05 / Ravens 2006–07)
because the chains are decades apart. **Two assistants of one name with adjacent or
overlapping chains would not be**, and that case should be expected rather than
hoped against — it is §2.2 shape 7 with its discriminator removed.

**Tier C — refusal.** When no available field separates, emit `ambiguous` with the
candidate person ids and the reason. Do not guess, do not take a mode, do not use
position adjacency. *Being right by luck is indistinguishable from being right by
method until someone checks.*

### 2.5 Three structural guarantees

**No bare-name lookup can exist**, because the person has no name. Looking up
"Chuck Noll" queries the name-claim index and returns **a set of persons**. The
plural is in the return type, so a caller cannot forget. A single-element result
is an outcome, not a promise. This is "prefer the convention nobody has to
remember" applied at the API surface: there is no rule to recall, because the
wrong thing is not expressible.

**A person is a person, not a role.** Chuck Noll is one id with player stints and
coaching stints. So is Bill Belichick, who is a 1979 New York assistant and a 2023
head coach. Separate player and coach tables would split shape 8 by construction,
and the prior project already found that `staff_faces` is keyed on name alone
"because a coach changes role between years" — which is the right observation
solved the wrong way.

**Names are claims and carry `observed_at`.** Nickell Robey in 2013 and Nickell
Robey-Coleman in 2017 are two name-claims on one person, each dated. A 1979 export
gets the 1979 spelling. A normaliser exists but is measured against the actual
keys, never against its own description.

---

## 3. Claims

### 3.1 The unit

**One source_record asserting one predicate about one subject, at one observation
time.** Not a row of attributes — one fact. A roster row producing eight facts
produces eight claims sharing a source_record.

```
claim
  id              c_01J8QM…
  source_record   statscrew/roster/BA1-1950#row-04
  subject         (person p_01J8QK…, season NFL-1950)
  predicate       position
  value           { vocab: "statscrew", code: "MG" }
  observed_at     1950                    # when the SOURCE observed it
  recorded_at     2026-09-04T14:02Z       # when we ingested it
  kind            observed
  source_conf     null                    # the source's own, if it has one
  stated_by       "StatsCrew"             # whose voice, inside the document
  attribution     []                      # empty = first-hand. See §3.6
```

### 3.2 What a claim can attach to

Four subject scopes, and the choice of scope is the modelling decision that most
affects how much of this design works:

| scope | holds | examples |
|---|---|---|
| **person** | time-invariant, or slowly varying with a date | birth date, birthplace, death, college, high school, name |
| **person × season** | true of the man that year, across all his clubs | age, jersey where a league assigns it, position(s) played |
| **person × club_season** (a **stint**) | true of him at that club that year | games, starts, jersey, role/title, salary if ever found |
| **club_season** | not about a person | record, standings, points for/against, head coach, division |

**The stint is the load-bearing one.** A 1979 mid-season mover has two stints, and
the dataset holds both. The prior project's mover rule — assign him to the club he
played more games for — resolved 28 of 30 cases with a median margin of 2.5 games
and two exact ties, and was correctly recorded as a coin flip. **In this model
that coin flip does not exist at the dataset level.** Both stints are facts. Only
the export has to pick one, and the export records why in the build's own
provenance, where a coin flip belongs.

### 3.3 Five kinds, and the line between them

| kind | test | lives in the dataset? |
|---|---|---|
| `observed` | a source states it as a fact it witnessed or recorded | yes |
| `source_derived` | a source states it, but the *source* computed or estimated it | yes — **marked**, see below |
| `derived` | computed from claims by a named, versioned recipe; anyone with the same claims reproduces it | yes, marked, with recipe id and input claim ids |
| `absent` | a source that *would* have carried it does not | **yes** — see §3.4 |
| `invented` | drawn, seeded, or chosen to satisfy a consumer | **no. There is no field it can be written into.** |

The brief's test — *could someone else with the same sources reproduce it?* — is
exactly the observed/derived line against the invented line, and it is checkable
rather than a matter of judgement.

**`source_derived` was added 2026-09-04, and it closes a real hole.** The first
draft had four kinds and quietly assumed that if a document says a number, the
document *observed* it. Two cases from the same afternoon show that is false, and
that the difference matters:

- The 1966–1980 NFL financial table's **1980 column is an estimate**, said so in
  its own footnote ("based on results of large majority of clubs and
  projections"), and is internally inconsistent *because* of that — three cells
  fail a percentage check that all six real columns pass.
- The NFLPA's average-coaching-salary figure is built from an assumption of
  **nine assistants at a flat $45,000 each**. The staff *count* is plausibly an
  observation of 1980 practice. The **flat rate is the NFLPA's own fill**, and
  taking it as structure would import an interested party's estimating
  convention as though it were measured — which is this project's
  "a safe default is still a claim" precedent arriving from outside the project
  rather than inside it.

Without the distinction, both enter as `observed` and their method becomes our
data. It is also the general form of the `era_certain` failure: a value that
*looks* like a fact because a credible document states it, when the document
computed it. **The rule: a claim is `observed` only where the source is
reporting, not reckoning. If the source shows its arithmetic, or footnotes an
estimate, or the figure is an average the source itself computed, it is
`source_derived`** — usable, quotable, and never mistaken for a measurement.

### 3.4 Absence is a claim, and this is a bigger deal than it sounds

There is a difference between *we have not looked* and *we looked in the place
that would have it and it is not there*, and the second is a finding.

The prior project already produced the canonical instance and left it in a
document: two occurrences of "salary" in 9.4 million characters of media guide
text, both prose. That is a measurement, and under this design it is **claims** —
one per guide searched — not a paragraph. So "salaries before 1990 do not exist"
becomes queryable: *which sources were searched, when, for what, with what
result*. A later session that wonders whether anyone checked the 1981 league book
gets an answer instead of repeating the search.

The negative control that validated PFR search is the same shape: asked for New
England's 2000 defensive coordinator, the search correctly reported none listed.
A model with no way to record that has to throw it away.

### 3.5 Two fields I want to be strict about

**`observed_at` is mandatory and is not `recorded_at`.** The precedent: 41 coach
appearance rows researched for 2004–2010 joined cleanly to the 1986 staff, and 79%
read "grey or white" — describing men whose mean age *at observation* was 61 and
whose mean age in 1986 was 43. Ditka 47, Parcells 45, Belichick 34, Dungy 30. The
field was available and wrong, and passed every distribution check. Only asking
*when* exposes it. A claim whose observation time is unknown is recorded as
unknown, and resolution must be able to see that.

**`confidence` is the source's, never ours.** Ours is computed at resolution time
from policy. This is the `era_certain` precedent moved into the schema: a field
named for a conclusion, whose implementation was `bool(e['years'])` — a null check
— read `True` over a window built from the wrong man, and three separate documents
told build sessions to trust it.

**Standing naming rule, from that precedent: no field in this dataset may be named
for a conclusion. Fields are named for their computation.** `has_season_vote_1979`,
not `era_certain`. `denotation_method`, not `identity_verified`.

---

### 3.6 Attributed claims — a claim about a claim

**Added 2026-09-04 on Ryan's ruling**, after the 1979 salary contest turned out
not to be what §8.4 first said it was.

A document often does not assert a fact — it asserts that **someone else**
asserted it. The 1982 hearing does not give the League's average salary; it gives
*the NFLPA reporting* the League's figure. Modelled flat, that becomes a League
claim, and the League gets a vote it never cast.

**Two fields, and the second is a chain, not a scalar:**

```
stated_by     whose voice this is, inside the document we hold
attribution   [ordered, from that voice outward toward the origin]
```

`attribution: []` is first-hand. Its length is the number of **removes**.

**Worked, on the two cases in hand:**

```
# NFL average salary, 1979 — the League's figure
source_record  hearing-XQ8o#p61
stated_by      "NFLPA"
attribution    ["NFL Management Council"]              # 1 remove

# defensive-line salary schedule — UPI, 30 Sep 1981
source_record  upi-1981-09-30-dean#perrine-quote
stated_by      "Dave Perrine (agent, Fred Dean)"
attribution    ["NFL salary schedule"]                 # via an interested party
                                                       # reported by a wire service
                                                       # = 2 removes from origin

# Fred Dean's own 1980 salary
source_record  upi-1981-09-30-dean#published-reports
stated_by      "UPI"
attribution    ["published reports"]                   # 1 remove, origin UNNAMED
```

**The rule, and it is the point of the whole mechanism:**

> **An attributed claim never counts as an independent source for the party at the
> end of its chain.** The NFLPA's report of the League's figure is evidence about
> what the NFLPA says the League said. It is not evidence from the League.

So a claim with a non-empty `attribution` votes only in `stated_by`'s lineage
group (§4.3), never in the attributed party's. The League cannot be outvoted by
its opponent quoting it, and it cannot be corroborated by its opponent quoting it
either.

**Attribution and lineage are different axes and both cap independence.** Lineage
is *documents descending from documents* — four JINX files agreeing is one vote.
Attribution is *a document reporting another party*. A source can be
lineage-independent and still be hearsay, which is exactly the primer's position
relative to the hearing on the League's number.

**An unnamed origin is weaker than a named one.** `["published reports"]` cannot
be chased, corroborated, or dated. It is recorded verbatim rather than cleaned up,
because "published reports" is the actual state of the evidence and paraphrasing
it as a source would overstate it.

**This does not make attributed claims useless.** The Dean cell below is two
removes and is the only per-position salary structure this project has ever held.
It is held, used, and correctly labelled — which is the difference between a
dataset that knows what it has and one that does not.

### 3.7 Acquisition — how the bytes reached us, as a third axis

**Added 2026-09-04.** The Dallas Morning News piece is a document Ryan holds as a
scanned PDF with text copied out in Acrobat. There is no URL, so "fetch it rather
than log the relay" cannot apply — and it is plainly not a relay either. It is a
third thing, and the model had no name for it.

Three orthogonal axes now, and a source can be weak on any one of them
independently:

| axis | question | §  |
|---|---|---|
| **attribution** | who *asserted* it | 3.6 |
| **lineage** | which documents descend from which | 4.3 |
| **acquisition** | how faithfully the text reached *us* | here |

**Four acquisition classes:**

| class | means | may enter the store? |
|---|---|---|
| `fetched` | retrieved from a URL, hash-pinned, reproducible | yes |
| `held` | a file in the source tree, hash-pinned | yes |
| `transcribed` | a reading of a held document — OCR, or a person typing | yes, **naming the transcriber and the tool** |
| `relayed` | text in a conversation with no document behind it | **no — it is a lead, not a source** |

**`relayed` is the one that earns its place.** Four times today a figure or a repo
fact arrived as conversational memory and was treated as established; each time it
was wrong or incomplete. Giving the state a name and a rule — *a lead, never a
claim* — turns a recurring discipline failure into something the model refuses
structurally.

**`transcribed` carries two obligations:**

1. **Name the transcriber and the instrument.** "Ryan, Acrobat text copy, from
   `<file>`" is provenance about the *reading*, distinct from provenance about the
   assertion.
2. **Numerics get a plausibility pass before they are called a disagreement.**
   This is report 01's lesson exactly: a failing check may be your reading of the
   source rather than the source. OCR damage is visible in the DMN text already —
   `mewspaper`, `alltime`, `$94948` with the comma lost, `hase salary`.

**And the guard that matters most:** Ryan transcribing a document is **not** a
human verdict under §4.2. A verdict is a person adjudicating evidence; a
transcription is a person operating a lossy instrument. Conflating them would let
an OCR slip inherit rank 1 and outrank every source in the dataset.

> **Transcription is an acquisition channel, never an adjudication.**

## 4. Resolution

### 4.1 The shape

Resolution is a **pure function of (claims, policy) → resolved value**. Policy is
data, versioned, in the repo. Changing the ranking is editing a policy file and
re-running. The claims never move.

```
resolved_value
  subject         (person p_…, season NFL-1979)
  predicate       role
  value           "Defensive Backfield Coach"
  basis           observed | derived | contested | absent | unknown
  policy          policy@v4
  rule_fired      "team's own contemporaneous publication outranks aggregator"
  winning_claims  [c_…]
  losing_claims   [c_…]        # kept, and this matters — see §8.3
  computed_at     …
```

### 4.2 The ranking, as ruled

1. a human's verdict (photograph, in-game verification, a hand ruling by Ryan)
2. multi-source consensus
3. a single source
4. a draw

### 4.3 Four refinements the precedents force on that ranking

**Consensus counts lineage groups, not sources.** *"Files that descend from each
other share their errors. Four JINX files agreeing is one vote."* So every source
declares `derived_from`, and rank 2 counts independent families. A source that
does not declare its lineage does not get a consensus vote — it is treated as rank
3. This makes the declaration load-bearing rather than documentation.

**Eligibility is per `(source, predicate)`, not per source.** *"Source quality is
per field, not per file"* — a Madden CSV whose skin field collapsed still carries
usable hair colour. Seven of seventeen scored files carry no usable skin signal,
including three that had been treated as good. The policy is a table keyed on the
pair.

**A source must be scored before it votes, at scale, on a stated population.** The
precedent: a field scoring 95% against 43 anchors scored 80.7% against 1,210
players, and the best threshold moved. *Anchors skew toward the well-known, and
the well-known are the players every source gets right.* So `source_score` rows
carry predicate, method, threshold, **population and n**, result and date — and an
unscored `(source, predicate)` pair cannot vote at rank 2 or 3.

**An attributed claim cannot vote as the party it attributes (§3.6).** A claim
whose `attribution` is non-empty joins `stated_by`'s lineage group and no other.
This is separate from lineage and stacks with it: a document can be
lineage-independent of everything we hold and still be hearsay.

**Guards read provenance.** Any floor, ceiling, clamp or default checks the
resolved value's `basis` before it fires and refuses on `observed`. This is the
Jason Elam case: a rating-based salary floor pushed his real Over The Cap figure
of $1,071,167 up to $2,200,000, and *nothing looked wrong*, because a guard's
whole job is to produce plausible output. Generalised from `_verified_keys` being
locked, which is the same rule for a narrower case.

### 4.4 Refusal is an outcome, not an error

`basis: contested` and `basis: unknown` are values a consumer receives and must
handle. What a consumer does about them is the consumer's business and is recorded
in *its* provenance. The dataset never resolves a contest by inference to spare a
consumer the trouble.

### 4.5 Provenance is origin, not last hop — enforced, not remembered

The brief names the failure: a class of face data read as `registry-1986` when it
had actually been drawn from a distribution and propagated, and the defect survived
weeks and broke a design ruling.

Three structural properties prevent it here, and none of them requires anyone to
be careful:

1. A claim cannot exist without a `source_record`, and `source_record` means a
   retrievable location in a real document. There is no way to write a claim whose
   origin is an artifact.
2. A `derived` claim must name its recipe **and its input claim ids**. Provenance
   is therefore a graph you can walk to the leaves, and every leaf is a source
   record. "Where did this come from" has one answer and it is transitive.
3. An `invented` value has no field to occupy. It can only be produced by a build,
   and a build's outputs are not claims.

The related trap the prior project also hit: **guidance embedded in a generated
artifact cannot be corrected by editing documentation.** A `_README` string written
*into* `PGM3_PLAYER_ARCHIVE.json` told readers to trust `era_certain`; two
documents were corrected the same day and the third copy could not be. **Rule for
this dataset: a generated artifact may carry a pointer to where guidance lives.
It may not carry the guidance.** A stale pointer still works; a stale claim asserts.

---

## 5. Time and structure

### 5.1 Season

A season is **`(league, year)`**, never a year alone, because leagues overlap:
NFL and AAFC 1946–49; NFL and AFL 1960–69; NFL and WFL 1974–75; NFL and USFL
1983–85; the CFL runs alongside all of it. A man can hold stints in two leagues in
one calendar year and the model must not force a choice.

Each season carries its own calendar (first and last game dates), because CFL and
NFL years do not align and mid-season movement is dated against a schedule.

### 5.2 Franchise

- **`franchise`** — a continuous organisational entity, opaque id.
- **`club_season`** — `(franchise, season)` carrying **name, city, league,
  division** as they were *that year*.

So the Colts are one franchise whose club_seasons read *Baltimore* through 1983
and *Indianapolis* from 1984. Nothing back-maps. There is no "modern team id" in
the dataset at all — that is a consumer's vocabulary and belongs in an export map,
exactly like position (§5.4).

**Continuity relations are typed and explicit**, held as `franchise_event` rows:

| type | example |
|---|---|
| `relocation` | Baltimore → Indianapolis, 1984 |
| `rename` | Boston Redskins → Washington, 1937; Washington → Commanders |
| `merger` | Phil-Pitt "Steagles" 1943; Card-Pitt 1944 |
| `suspension` / `resumption` | Cleveland Browns, 1996–1998 |
| `personnel_transfer` | Cleveland's 1996 roster and staff → the new Baltimore club |
| `league_absorption` | AAFC clubs → NFL, 1950; AFL → NFL, 1970 |
| `dissolution` | most of the 1920s |

Cleveland/Baltimore is then two franchises plus a `personnel_transfer`, and
Baltimore/Indianapolis is one franchise plus a `relocation`. The distinction the
brief asks about is carried by the *type of the edge*, not by a judgement about
what counts as "the same team".

**And franchise continuity is itself contested data.** The Browns/Ravens answer is
a ruling by a league, from a source, and it is recorded as such. The 1920s
lineages (Decatur/Chicago Staleys; several Cleveland and Chicago clubs) have no
such ruling and may have to sit at `contested` permanently. That is a legitimate
resting state, not an unfinished job. See §9.5.

### 5.3 Stint

`(person, club_season, role)` with games, starts, jersey, title, and a date range
where known. Roles cover players, coaches at every level including position
coaches with no slot in any game, front office, scouts, medical staff — anything a
source records. The 94th man on a roster has a stint with `games: 0` if a source
says so, and no games claim at all if no source counted.

### 5.4 Position is era-native, and translation is a table

A position value is `{ vocab, code }`. The 1950 Baltimore Colts roster I read this
session carries `MG`, `RLB`, `MLB`, `LT` — middle guard, right linebacker, and a
tackle who played both ways. A 1920 lineman is `LE`. Stored as written, in the
source's vocabulary, with the vocabulary named.

Three tables:

- **`position_vocabulary`** — `(vocab, code) → definition, era range`. What `MG`
  meant, in prose, with a source.
- **`position_map`** — `(from_vocab, code, era, to_vocab) → code | refuse`, with a
  note and its own provenance. Versioned.
- Positions are **multi-valued and ordered**. StatsCrew gives Chuck Noll
  `LB-G-C`. Store the list.

This is the single answer to what the precedents call the boundary-translation bug
family — four instances recorded, `FB`/`HB`, `FS`/`SS`, `G`/`OG`, and a hair
vocabulary borrowed across a boundary, each of which "silently reduced a cohort
rather than raising an error, because a label that does not match simply finds
nothing." Under this design a vocabulary crosses a boundary in exactly one place,
that place is a table, and a code with no mapping **refuses loudly** instead of
finding nothing.

---

## 6. Derived values

A derived claim is a first-class dataset value, marked as derived, carrying:

```
derivation
  recipe        rating/positional-from-statistics@v3
  code_version  <git sha>
  inputs        [c_…, c_…, …]        # the actual claim ids
  parameters    { era_baseline: "NFL-1979", … }
```

Four rules:

1. **Reproducible or it is not derived.** Same claims + same recipe version = same
   value, byte-identical. The prior project shipped a non-deterministic build
   because `DERIVED_ATTRS` was a `set` and two of its members drew from
   `rng.random()`, so which draw each received depended on the hash seed; two
   builds of identical input differed on ~2,500 records. Determinism is a gate
   (§7.3), not an aspiration.

2. **Stale, not silently recomputed.** When an input claim changes, the derived
   claim is marked `stale` and is *visible*. It is not quietly rebuilt. The
   precedent — "cleaning the target is not enough, recompute everything derived
   from it" — was hit three times, and the third time in the *opposite* direction:
   an over-applied recomputation gated stamina off for the bottom 9% of several
   positions and shipped 37 players at zero. Recomputation is a decision with a
   review, so it must be surfaced.

3. **A recipe declares whether its reference already embeds its own terms.** The
   "a published reference is an output, not a specification" precedent has four
   recorded instances, and the tell is *a correlation that beats the reference*,
   which looks like a good fit and ships. A schema cannot enforce this. It is a
   review question on every recipe, and I would put it in the recipe file as a
   required field with a written answer.

4. **Seeded draws are not derived.** A hair colour drawn from a distribution and
   seeded on a name is reproducible and is still `invented`, because it is not
   *derived from claims about that man*. The reproducibility test alone is not
   sufficient; the inputs must be claims about the subject. This is the exact
   distinction the brief draws and it needs stating in the recipe contract, because
   "seeded so rebuilds don't reshuffle" is a real and reasonable build technique
   that must stay outside the dataset.

**Where a rating lives:** as a derived claim on `person × season`, recipe named,
inputs being the statistic claims plus position plus era baseline. It belongs in
the dataset because it passes the test. The known gap stays a gap: statistics reach
the ball-touching positions, and linemen and most defenders barely appear in a box
score, so a rating recipe for those positions either does not exist or is honest
about resting on very little. Recorded as absence, not filled.

---

## 7. Gates

Standing rule: every fix ships with a check in the same commit, the check is a
property and not an instance, it runs over all files, and **a check that has only
ever passed has not been tested** — find the commit where it fails or construct
the failure and watch it fail there.

Gates this design needs from the first commit:

1. **No bare-name resolution.** Structural (the person has no name) plus a lint
   over ingest code. Failure to construct: a lookup returning a scalar.
2. **Every claim resolves to a retrievable source_record.** Referential, cheap,
   always on.
3. **Determinism.** Build twice from the same claims, assert byte-identical.
   Failure to construct: iterate a `set` that consumes a random stream.
4. **Match-rate, not count.** *"Wherever a fallback exists to make up a shortfall,
   the count check is dead by construction."* Report matched / refused /
   name-not-present-in-source separately, and assert on the rate. The denominator
   is records **whose name the source holds**, because a name the source never had
   is not a lookup failure and including it measures coverage instead of
   correctness.
5. **Unscored source cannot vote.** `(source, predicate)` with no `source_score`
   row is excluded at rank 2 and 3.
6. **Guards spared observed values.** After every guard pass, re-read the
   `observed` records against their originals and fail if any moved. Test the
   assertion by corrupting a record first — *an assertion that cannot fail reports
   success.*
7. **Absence is distinguishable from silence** in every query result.
8. **Denotation ambiguity is reported, never zero by construction.** Assert the
   ambiguous set is *reachable* — a refusal counter that can only ever read zero is
   the vacuous-pass failure the precedents call this project's dominant one.
9. **Cohort stated with every count.** Enforced in the report format, because two
   correct measurements of different populations read as a disagreement.

---

## 8. Three worked examples

### 8.1 A namesake pair — two men, one name, sources that disagree about which is which

**The case: Larry Brown, 1979.** Two offensive tackles. One from Miami, aged 24,
Kansas City. One from Kansas, aged 30, Pittsburgh. Same name, same position, same
season, same league. *(From `PGM3_PRECEDENTS.md`, measured during the 1979 build.)*

Every key this project has ever proposed fails on at least one axis:

| key | result |
|---|---|
| `name` | merged |
| `name\|position` | merged |
| `name\|position\|team` | separated — but only because these two happened to be on different clubs. Cleveland's two Robert Jacksons defeat it |
| era / birth year | 24 vs 30 separates *these two*; useless against a namesake of the same age |
| **college** | Miami vs Kansas — separates, and is the only field that always does here |

**How the dataset holds it.**

Ingest reads the footballdb 1979 Kansas City roster. It produces a source_record
and a denotation attempt. The source's declared discriminators are
`[name, position, college, age]`. The name matches two existing candidate persons;
college separates:

```
denotation
  source_record  footballdb/roster/kansas-city-chiefs-1979#row-71
  person         p_larrybrown_miami
  discriminator  ["name", "college", "age"]
  method         attribute-match
  confidence     high
  status         asserted
```

The Pittsburgh row denotes `p_larrybrown_kansas`. Two persons, twelve or so claims
each, no collision.

**Now the part the brief actually asks about: a source that disagrees about which
is which.** Two are documented.

*footballdb collapses movers.* Its per-player pages render a mid-season mover as
"2 TMS" with no club order at all. A denotation from a player page therefore cannot
say which club-season a stint belongs to. Result: the page's *person-scoped* claims
(birth date, college) are asserted; its *stint-scoped* claims are `ambiguous` and
refused, with the reason recorded. Partial acceptance of a source, per record, per
scope — which a row-level join cannot express.

*The 2K5 archive asserts the wrong man with confidence.* Its `stock` flag is keyed
on **name alone**. A genuine 1979 player with a modern namesake gets an era window
built only from files that do not contain him — and `era_certain` reads `True`
anyway. D.D. Lewis, a 1979 Cowboys linebacker, reads `first_seen` 2004,
`last_seen` 2009, `era_certain` True. 1,952 entries carry at least one flagged
vote; 1,453 have a window that excludes the flagged year.

Under this design that is a **wrong denotation, not a wrong fact**. The archive's
skin claim about the man is fine. What is wrong is which person the record was
attached to. So:

- the archive's declared discriminator is **presence of a season vote from that
  year's file** — a direct observation — and explicitly *not* `first_seen` /
  `last_seen` / `era_certain`, which are derived and carry a known defect on
  exactly this cohort;
- where that vote is absent, the denotation is `ambiguous`, not a guess;
- when the archive is eventually rebuilt with a position-aware `stock_names()`,
  **re-running ingest re-points denotations and touches no claim**. Under the old
  model the same repair "rebuilds era metadata for every pre-2000 file" and needs
  its own review pass.

**What is different from last time.** The 81% cross-era false-match rate on
`name+position` is not improved by a cleverer key — it is made *visible*, because
every one of those matches now carries the discriminator that produced it, and a
denotation resting on `["name", "position"]` alone across a 68-year population is
queryable and reviewable as a class.

### 8.2 An era-specific position, exported to a consumer with fifteen fixed slots

**The case: the 1950 Baltimore Colts.** From the cached StatsCrew roster page,
read this session:

```
32  Sisto Averno     MG   May 12, 1925   5'11"  235  Muhlenberg
41  Ernie Blandin    LT   Jun 21, 1919   6'4"   248  Tulane
73  Hardy Brown      MLB  May 8,  1924   6'0"   193  SMU
77  George Buksar    RLB  Aug 12, 1926   6'0"   206  Purdue
64  George Blanda    QB   Sep 17, 1927   6'2"   215  Kentucky
```

`MG` is a middle guard — the nose of a five-man front, a position that stopped
existing when the 4-3 arrived. He is a nose tackle by alignment and an inside
linebacker by responsibility, and he is neither.

**In the dataset**, one claim:

```
subject    (person p_averno, season NFL-1950)
predicate  position
value      { vocab: "statscrew", code: "MG" }
observed_at 1950
kind       observed
```

Plus a vocabulary row saying what `MG` was, with a source. **Nothing is translated
on the way in.**

**At export**, `position_map` is consulted:

```
from_vocab  statscrew
code        MG
era         1946-1955
to_vocab    pgm3-15
code        DT
note        "Five-man front nose. Alignment maps to DT; responsibilities
             partly LB. Chosen DT because PGM3 rates DT on the traits a
             middle guard was selected for. The LB half is lost."
source      hand ruling, Ryan, <date>
```

Three properties worth naming:

1. **The map is data, versioned, with provenance and a written reason.** Changing
   `MG → DT` to `MG → MLB` is editing one row and re-exporting. The dataset does
   not move.
2. **The map can refuse.** A code with no row for the target vocabulary raises. It
   does not silently find nothing — which is precisely how four boundary bugs
   shipped.
3. **The era is in the key.** `LT` in 1950 is a two-way tackle; `LT` in 2020 is a
   blindside pass protector. Same code, different eras, different targets, and the
   map says so.

**The hard case in the same roster, and it is not the vocabulary.** Ernie Blandin
played offence *and* defence. PGM3 has one position field per man. So the export
must choose a side — and **that choice is the export's, not the dataset's.** It is
recorded in the build manifest:

```
build/pgm3-1950/manifest
  rule    "two-way players export on the side with more recorded snaps;
           where unknown, the side the source lists first"
  affected 47 of 396
  lost     the other side of each man's career
```

The dataset continues to hold both. A different consumer — one with two-platoon
support, or none at all — makes a different choice from the same claims. **This is
the whole point of the layering, and it is the concrete thing PocketGM's fifteen
slots cannot be allowed to dictate.**

### 8.3 A value only one source has, and a second source arrives later that disagrees

**The case: a 1979 coaching role.** Coaching Tree returns full staffs back to 1926
including coordinators. It is also, per `PGM3_DATA_SOURCES.md`, "unreliable on
teams that did not use them — three role errors in five 1979 teams checked against
the teams' own guides."

**Day one.** Only Coaching Tree has it:

```
c_001
  source_record  coaching-tree/team-staff/PIT-1979#staff-04
  subject        (person p_X, club_season PIT-NFL-1979)
  predicate      role
  value          "Defensive Coordinator"
  observed_at    2026          # a modern aggregator's assertion about 1979
  kind           observed
```

Resolution, under policy@v3: one eligible claim, no contest.

```
value  "Defensive Coordinator"
basis  observed
rule   "single eligible source"
```

Note `observed_at: 2026`. Coaching Tree is a *modern* source making a claim about
1979 — that is not a defect, but it is a fact about the claim, and it is the field
that will decide the contest below.

**Day sixty.** The 1979 Pittsburgh media guide is pulled from
`archive.org/stream/{id}/{filename}_djvu.txt` — following redirects, because a 302
without `-L` writes a zero-byte file that reads exactly like a book with no text.
Its staff page lists the man as **Defensive Backfield Coach**, and lists no
defensive coordinator at all.

Two claims, not one edit:

```
c_002
  source_record  mediaguide/pit-1979#p34-l12
  subject        (person p_X, club_season PIT-NFL-1979)
  predicate      role
  value          "Defensive Backfield Coach"
  observed_at    1979
  kind           observed

c_003
  source_record  mediaguide/pit-1979#p34
  subject        (club_season PIT-NFL-1979)
  predicate      has_role
  value          "Defensive Coordinator"
  kind           absent          # the guide lists the staff and has none
```

**What happens.** The contest is `role` on `(p_X, PIT-NFL-1979)`. Policy resolves
it — and the rule it needs did not exist on day one, which is the honest part of
this example:

```
policy@v4, rule "contemporaneous-over-aggregator"
  for predicate `role`, a source whose observed_at is within the season
  outranks one whose observed_at is later, regardless of source rank,
  because a modern aggregator projects modern title structures onto
  teams that did not use them. (Evidence: 3 role errors in 5 teams,
  1979, PGM3_DATA_SOURCES.md.)
```

```
value           "Defensive Backfield Coach"
basis           contested
rule_fired      "contemporaneous-over-aggregator"
policy          policy@v4
winning_claims  [c_002]
losing_claims   [c_001]
```

**Five things this buys, and the fourth is the one that matters most:**

1. **Nothing was rewritten.** `c_001` still exists and still says what Coaching
   Tree said.
2. **`basis: contested` propagates.** Any consumer sees that this value has a
   live disagreement behind it, and can choose to treat it differently from a
   clean one.
3. **Adding the rule was a policy edit and a re-run.** No ingest, no rebuild, no
   migration.
4. **The losing claims are the finding.** Query all contests where Coaching Tree
   lost to a contemporaneous guide, and you get *a measurement of Coaching Tree's
   error rate on 1979 role labels* — which is the sort of thing that was a
   sentence in a document last time. It then feeds §4.3's per-`(source,
   predicate)` eligibility, automatically. **A model that overwrites cannot
   produce this number at all.**
5. **`c_003` is the absence claim.** The team had no defensive coordinator in
   1979. That is a fact about 1979 football, not a gap in our data, and the
   distinction is only expressible because absence is a claim.

**And if Ryan later reads the guide page himself and disagrees with both** — say
the man held two titles — his verdict enters as a claim at rank 1 and wins, with
`method: hand`. Both source claims stay. This is `_verified_keys` generalised: *a
person looking at the evidence outranks any source, however well it scores*, and
provenance follows who decided, not what surfaced it.

### 8.4 A contest with no arbiter — two 1979 salary averages, both true to their source

Added 2026-09-04 at Ryan's direction, and it is the strongest of the four because
it is real, it came from a source pulled the same day, and **the disagreement is
unresolvable in principle rather than pending more work.** Examples 8.1–8.3 all
end in an answer. This one does not, and the design has to be honest about that.

**The source.** *Antitrust Policy and Professional Sports*, House Judiciary
oversight hearings 1981–82 (Google Books `XQ8oAAAAMAAJ`, sha256 `8ed1a97c…`, 685
pages, cached). Printed pp. 59–61 carry the NFLPA's analysis with the League's
figures set against it.

**Two claims about one value:**

```
c_101  source_record  hearing-XQ8o#p60          # NFLPA, 1981 salary survey
       subject        (league NFL, season NFL-1979)
       predicate      average_player_salary
       value          68900 USD
       observed_at    1981
       kind           source_derived            # a survey average, not a return
       stated_by      NFLPA                     # a party to the dispute

c_102  source_record  hearing-XQ8o#p61          # the League's figure, quoted
       subject        (league NFL, season NFL-1979)
       predicate      average_player_salary
       value          93333 USD
       observed_at    1981
       kind           source_derived            # ~$140M / 1,500 players
       stated_by      NFL Management Council
```

The same page carries the per-club version of the same disagreement — **$4.3M
against $5.2M** — and each side's own adjusted figure, "still under $75,000" and
"still stays over $85,000".

**CORRECTED 2026-09-04: this is not two parties.** `c_102` is the League's figure
**as quoted by the NFLPA**, in NFLPA testimony. There is no League-original
document in hand, and the 2002 primer is the same organisation twenty years later
(§9b), so it does not supply one. Per §3.6 the claim carries
`stated_by: NFLPA`, `attribution: ["NFL Management Council"]`, and has **no
independent standing**.

**So the contest is one party and one hearsay.** That is a weaker and more honest
thing than the symmetric dispute this section first described, and the design
should say so rather than flatter the evidence. It does not change the resolution
— `contested` either way — but it changes what a reader should conclude from it,
and it makes a League-original source an explicit debt (§9b) rather than a
nicety.

**What resolution does.** Nothing clever. The policy has no rule that separates
them, because there is no honest one: both are `source_derived`, both are dated
1981, both are lineage-independent, and **both parties have a stake in the number
being what they say it is**. So:

```
value           —
basis           contested
rule_fired      "no eligible rule separates the claims"
candidates      [c_101 (68900, NFLPA), c_102 (93333, NFLMC)]
```

**Four things this example makes concrete that the other three do not:**

1. **`contested` is a terminal state, not a queue.** 8.3's contest resolved once a
   better-placed source arrived. This one will not resolve if we read every
   remaining volume, because the disagreement *is* the historical record. A model
   that must produce one number per field cannot represent 1979 honestly.
2. **`stated_by` earns its place.** It is not decoration — it is the field that
   makes "both sources have a stake" expressible, and it is the direct descendant
   of the precedent *when a source has a stake in its own entry, check that entry
   first, and say so before you look.*
3. **The export must choose, and the choice is the export's.** A PocketGM 1979
   build needs a scale factor and cannot take "contested" for an answer. So the
   build picks one, and its manifest records which and why:
   ```
   build/pgm3-1979/manifest
     rule     "salary scale anchored on the NFLPA 1979 survey average
               ($68,900), not the League's $93,333"
     reason   "the survey counts players; the League figure divides a total
               expenditure that includes benefits and deferred pay by a
               headcount. The former is closer to what PGM3's `salary`
               field means."
     contested_source  hearing-XQ8o, both claims retained
   ```
   That is the whole layering argument in one block: **the dataset holds the
   disagreement, the consumer holds the decision, and each records its own.**
4. **It closes the project's oldest gap without pretending to more than it does.**
   Pre-1990 salary was recorded as "nothing found" across the entire prior
   project. There is now a measured league-level series for 1966, 1970, 1975,
   1977, 1979 and 1980. It sets the **level**. It says nothing about any
   individual, so per-player salary remains absent — and §3.4 means the dataset
   can now say *that* precisely, rather than by silence.

---

## 9. Where this design is uncertain

### 9.1 StatsCrew's identifiers — MEASURED 2026-09-04, largely resolved

This was the blocking question in the first draft. It has been run.

**Method.** 64 cached player pages swept for coach cross-references; 33 pages
fetched live (`curl`, plain, HTTP 200 throughout, no bot detection — the site
behaves as `PGM3_DATA_SOURCES.md` describes), covering six recorded collisions
from §2.2 plus the George Allen and Chuck Noll cases, walking the counter past
the last real person in each. Cached HTML in `/tmp/sc/`; not committed, since it
is a third-party site's content.

**Answered.** Full detail in §2.4 Tier A. In summary:

- The counter is a genuine namesake resolution and it **separates every recorded
  collision tested**, including the three-generation Clay Matthews case where two
  of the three share both position and college.
- Player and coach are **separate namespaces** (`p-` / `c-`), and the counters
  **do not align across them** — the real George Allens are `p-...002` and
  `c-...001`.
- The player/coach identity question — the more important half — is answered
  **by the source**: a man who did both carries a **bidirectional cross-reference**
  between his two records, 35 of 35 in the cached sample, with birth dates
  agreeing. Follow the link, never the matching string.

**Still open, and now the sharper questions:**

1. **Slug stability over time.** If StatsCrew renumbers when it discovers a new
   namesake, every Tier A denotation we hold becomes wrong silently. Mitigation is
   cheap and should be built in from the start: **store the slug *and* the
   identifying attributes (birth date, college, career span) on the denotation**,
   and re-verify on every re-fetch. A slug whose page now shows a different birth
   date is a renumber, and it should raise. Not measurable today — it needs two
   observations separated by months.
2. **Whether StatsCrew ever *merges* two men into one slug.** The failure this
   design cannot see, because a merged record looks like one person. Testing it
   needs a known pair that StatsCrew gets wrong, and I do not have one. Best
   available check: where a second source (nflverse birth dates, a media guide)
   splits a man StatsCrew holds as one, that disagreement is a claim and surfaces
   as `contested` rather than being averaged away.
3. **Assistant coach coverage is absent, not thin.** Confirmed on Frank Gansz Jr.
   This is the finding that actually changes the plan — see §10.

### 9.2 Birth-date coverage before about 1930

The 1950 roster page carries a birth date per player. I have not checked 1920,
1925, or the AAFC. Birth date is the discriminator §2.4 leans on hardest, and if
it thins out in the earliest era then the earliest era needs a different declared
discriminator — probably hometown plus college.

**PARTLY ANSWERED 2026-09-04, and the news is good.** Birth date is **91%**
populated on the cached Akron 1920 roster page and **100%** on 1950, 1979, 2000
and 2020 — see the table in §9.6. The earliest era is far better served than this
section feared, so birth date likely remains the primary discriminator all the way
back.

**Still owed:** one 1920 page at n=23 is indicative, not settled. Run the fill
rate across a proper sample per decade, including the AAFC and both AFLs, before
relying on it. Under an hour.

### 9.3 RULED — display name is era-scoped, with a defined fallback

**Ruling (2026-09-04): era-scoped. A 1979 export gets the 1979 spelling.**

The prior project treated cross-file inconsistency as a defect and was right to —
but that was a defect in **appearance**, and a man's face does not change between
1986 and 2004. **His name does.** Nickell Robey genuinely was Robey in 2013 and
Robey-Coleman in 2017, and a dataset that renders him one way in both is asserting
something false about one of them.

**Required with it: a query with no era must still be answerable.** "Undefined"
would be the actual defect. The fallback is:

> **The name-claim covering the largest span of the person's own attested career,
> tie-broken by the earliest.**

Chosen over "most recent" deliberately. Most-recent favours whichever source was
observed latest, which for the historical population means a modern reference work
using a modernised spelling — the same shape as the 2004-observed hair colour
applied to a 1986 coach. Career-span is era-neutral: it returns the name the man
was known by for most of the time this dataset is about. Ties break earliest,
which is deterministic and matches the era-native instinct.

It is a **`derived` value with a named recipe** (§3.3), not a stored attribute,
and it is total — a person with no name claims at all resolves to
`basis: unknown` rather than to nothing.

**The hazard this creates, named so it is not discovered later.** A "primary name"
is exactly the field §2.3 removed, and reintroducing it as a convenience
reintroduces the temptation to join on it. Three guards:

1. It is computed, never stored on the person.
2. It is marked `derived`, so anything consuming it can see what it is.
3. **Gate: no denotation may cite the display name as a discriminator.** A
   denotation whose `discriminator` list contains it fails the build. That is the
   check that keeps this from quietly becoming a key.

### 9.4 How much resolution to materialise

Resolving on read is clean and cannot drift. It is also the slow option at
100k+ persons and millions of claims. Materialising is fast and reintroduces a
second copy — this project's single most-repeated failure, with four separate
stale-artifact incidents in one session and a fifth that was entirely local.

**Proposal:** materialise, but store the policy version and a hash of the input
claim ids on every resolved row, so staleness is *detectable* rather than
invisible — the same move as marking derived claims stale rather than
recomputing them. **Unmeasured:** whether on-read resolution is actually too slow.
Worth a spike once volumes are known rather than deciding now.

### 9.5 RULED — permanently contested is acceptable; the export must still render

**Ruling (2026-09-04): a permanently-contested franchise continuity is a
legitimate resting state.** Where historians genuinely disagree and no league
ruling exists, the dataset saying so is more accurate than picking one and
presenting it as settled.

**Required with it: a rendering rule at the boundary**, so a consumer is not
handed nothing. Same shape as §8.4 — the dataset declines, the build chooses, and
the build records why.

Mechanically this is the position map (§5.4) again, and deliberately so:

```
export config: lineage_choices
  <contested franchise>  ->  chosen lineage
                             reason   (written, not computed)
                             source   (the ruling or argument relied on)
```

**A table of named cases, not an algorithm.** There are only a handful, and a rule
that resolves them automatically would be a rule nobody ever checks — where a
written entry per case forces the choice to be stated. The reason field is prose
because the reasons are not commensurable: the NFL's own ruling settles
Browns/Ravens, and nothing comparable exists for the 1920s Chicago and Cleveland
lineages.

**Gate, and it is the load-bearing part: the export fails if a contested franchise
appears in the data with no `lineage_choices` entry.** It does not fall back, pick
the first, or emit null. That is the same refusal §5.4 requires of an unmapped
position code, and for the same reason — the four boundary-translation bugs in the
prior project all "silently reduced a cohort rather than raising an error, because
a label that does not match simply finds nothing."

**The dataset abstains; the export must not; neither may do the other's job.**

### 9.6 RULED — roster presence is its own predicate, and it needs a four-state check

**Ruling (2026-09-04): explicit predicate.** A media guide's all-time roster list
is a presence claim with nothing else attached, and a model that can only express
presence through a stint would have to **invent** a stint to hold it — inventing
structure to record a fact is exactly what §3.3 forbids. The query-frequency cost
is real and is the right trade: a predicate queried constantly earns its place.

**The check Ryan asked for: does "did not play" stay distinguishable from "no
source counted his games" once presence is separate?**

**Yes — but only if blank-cell semantics are ingested, and there are four states,
not two.** Working it through:

| state | what happened | how it is stored | resolves to |
|---|---|---|---|
| 1 | no source that counts games has seen him | `on_roster: true`, no games claim | `basis: unknown` |
| 2 | a source **with a GP column** lists him, cell **blank** | `on_roster: true` + **absence claim** on games (§3.4) | `basis: absent` |
| 3 | a source states zero | `games_played: 0`, `kind: observed` | `basis: observed`, 0 |
| 4 | a source states a number | `games_played: n` | `basis: observed`, n |

**State 2 is the one that would be lost**, and it is not hypothetical. Measured on
the cached StatsCrew roster pages this session:

| page | n | birth date | hometown | college | GP |
|---|---|---|---|---|---|
| Akron 1920 | 23 | **91%** | **83%** | 100% | 100% |
| Baltimore 1950 | 41 | 100% | 100% | 100% | 100% |
| Atlanta 1979 | 50 | 100% | 100% | 100% | 100% |
| Arizona 2000 | 58 | 100% | 100% | 100% | 100% |
| Arizona 2020 | 69 | 100% | 99% | 100% | 100% |

Matt Brown, halfback, Akron 1920: blank birth date, blank hometown, GP 1. **The
column exists and the cell is empty** — the source declining, not the source
silent. Skipping blanks at ingest would collapse state 2 into state 1 and lose the
fact that a source which knew the rest of his details did not know when he was
born.

**The 1920 page also has no jersey column at all** — nine headers against 1950's
ten. That is a different absence again: *the era did not have the field*, which is
a property of the source and of 1920 football, and belongs on the **source
declaration** rather than as 23 identical absence claims.

**Gate: a games query must be able to return all four bases, and the gate asserts
each is reachable.** A refusal or absence counter that can only ever read zero is
the vacuous-pass failure the prior project calls its dominant one — so the check
is not "do these states exist in the output" but "construct one of each and watch
them come back distinct."

**And the export is where they collapse, legitimately.** PocketGM needs a number,
so states 1 and 2 become 0 on the way out — recorded in the build manifest as a
default, never written back. That is the same layering as §8.4: the collapse is the
consumer's, and it does not propagate into the store because an export is not a
claim.

*Incidental result: this partly answers §9.2. Birth date is 91% populated on a 1920
roster page and 100% from 1950 on, so the earliest era is far better served than
feared. One page, n=23 — indicative, not settled.*

### 9.7 RULED — sources vote; a human decides

**No longer open. Recorded here as a principle, per Ryan's ruling 2026-09-04.**

> **A human verdict is not a weight in the ranking. It is a different kind of
> thing, and it terminates the resolution.** No quantity of agreeing sources, of
> any independence, can reach it.

The reason it must be a principle and not a heavy weight: **sources can be wrong
together.** Agreement measures shared ancestry and shared assumptions, not truth.
Give a human verdict a numeric weight, however large, and someone eventually
tunes it, or finds a case with enough sources to exceed it — and the mechanism
that was supposed to protect the most considered judgement in the dataset becomes
the one that overrides it. A rank that cannot be reached needs no tuning and no
one has to remember its value. (§7's "prefer the convention nobody has to
remember", applied to policy.)

Verifiable support in the prior project: `_verified_keys` exists **because an
automated pass with a perfect anchor score destroyed a hand-set face**, and the
edit it destroyed was the one carrying the most human judgement. Where a human
adjudicated a contest directly, the human's side held — RFM correct on 5 of 5
decided contested cases against the archive.

*(A "the archive was 4% right across a hundred photographs" figure was cited when
this was ruled, and then corrected by the master session the same day: it is real
but unwritten — Ryan judged 100 **disagreement** cases, the Mike period layers
right on 95 of 99 decided and our archive on 4. Because the sample is drawn
entirely from conflicts, it measures **where two sources disagree**, not the
archive's accuracy. **Do not use it as evidence for anything.** The ruling does
not rest on it.)*

**Still a tuning question, and genuinely open:** can *five independent lineage
groups* agreeing outrank a *single* source at the same rank? I think yes, by
weight, within rank 2 — but that is a knob, not a principle, and it should be
fitted rather than guessed.

### 9.8 RULED — the boundary: a person whose football record is part of a larger record

The two cases the brief named by hand — *two Bill Walshes on 1979 staffs* and *a
coach and his senator son* — came from build-session reports and were never
committed, so I have designed against the twelve verified shapes in §2.2. The
first is shape 1 or 2 and needs nothing new.

**The second names a real boundary, and I want to mark it rather than solve it.**

A person in this dataset is an opaque id that football claims attach to (§2.3).
Nothing in that model stops non-football claims attaching to the same id — and
some already will: StatsCrew carries birthplace, high school and date of death,
none of which are football facts. So the boundary is not *whether* the dataset
holds non-football facts about a person. It already does.

The boundary is **where the dataset stops being a record of professional football
and starts being a biographical database**, and the answer is not obvious:

- *What is in scope by necessity.* Anything that resolves identity. Birth date,
  birthplace, college, high school, death, family relation. A father/son link is a
  **football-relevant fact** — it is the discriminator for shapes 5, 6 and 7 — and
  it happens to also be a biographical one.
- *What is plainly out.* A congressional voting record. A business career. The
  dataset is not Wikipedia and should not grow toward it.
- *What is genuinely unclear, and where the senator case sits.* A later public
  life is the thing that makes a namesake **findable and separable** — it is why a
  source has a birth date for one man and not the other, and why the two are
  documented at all. It is evidence about identity that lives outside football.

**Proposed boundary, for a ruling rather than as a decision:** the dataset holds a
non-football fact only where it is *load-bearing for identity*, and holds it as a
claim like any other, with its source. Everything else is out of scope, and where
an external identifier exists (a Wikidata QID, say) the dataset stores **the
identifier, not the biography** — a pointer, so the football record can be joined
to a wider one by someone who wants that, without this dataset becoming it.

That also inverts the §2.5 relationship usefully: *a person is a person, not a
role* was argued from Chuck Noll needing one id for two football careers. The
senator case says the same thing from outside — a person is not exhausted by their
football record either, and the model should be able to say so without trying to
hold the rest.

**RULED (2026-09-04): yes.** The dataset holds a non-football fact only where it
is load-bearing for identity, and where an external identifier exists it stores
the pointer, not the biography. The observation that settled it: birthplace, high
school and date of death are already in the store from StatsCrew, so the question
was never *whether* non-football facts enter — only where the line sits.

---

## 9b. Sources found, and the leads they open

### The pre-1990 salary gap — closed at league level, 2026-09-04

*Antitrust Policy and Professional Sports*, House Judiciary oversight hearings
1981–82. Google Books `XQ8oAAAAMAAJ`, sha256
`8ed1a97cc9a6b965a61ab5197b2fa1ad7439fb1bf959e1149f8d141678738551`, 18,570,665
bytes, 685 pages. Cached at `pgm3-sources/hearings/`, **not committed** — same
ruling as `sources/`. Full report in `HEARING_XQ8o_FINDINGS.md`.

**Attachment B, "NFL Financial Summary 1966–1980"**, printed twice (printed pp.
233 and 239), per average club, in thousands, with a percentage-of-revenue column
beside every figure:

| | 1966 AFL | 1966 NFL | 1970 | 1975 | 1977 | 1979 | 1980 est |
|---|---|---|---|---|---|---|---|
| Total income | 2,164 | 3,741 | 4,825 | 7,399 | 7,909 | 12,090 | 13,300 |
| Salaries, incl. pre/post-season | 1,193 | 1,321 | 1,661 | 2,887 | 3,435 | 4,524 | 5,065 |
| Total player cost | 1,262 | 1,471 | 1,863 | 3,137 | 3,981 | 5,190 | 5,810 |

*Transport note for whoever fetches it again:* the PDF needs `curl -L`; without
it the 302 yields 562 bytes of HTML that reads exactly like a book with no text.
The EPUB is captcha-gated; the PDF is not. Text extracts with `pypdf`.

**Coach salaries — the first ever sourced for this project, any era.** NFLPA
estimate for an average club, 1980 (printed p.60): head coach **~$100,000**, nine
assistants at **~$45,000 each**, other coaching costs **~$195,000**.

**Read the shape carefully.** The *count* — nine assistants — is plausibly an
observation of 1980 practice and is useful as such. The **flat $45,000 is the
NFLPA's own estimating assumption**, not a measured distribution, and enters as
`source_derived` per §3.3. Treating it as observed structure would import an
interested party's fill as data. It is a level, not a spread.

### NFL Economics Primer 2002 — the per-experience axis, and one party's voice

M. J. Duberstein, NFLPA Research Department, April 2002. 164 pages.
`pgm3-sources/385388545-NFL-Economics-Primer-April-2002.pdf`, sha256
`911489526cc300a1f512c79215efe763d3d1f0f5eae7c1da4cc56f5653a4ce81`. **Use the
PDF with `extraction_mode="layout"`** — the flat text extraction loses the table
geometry and the year-to-value association becomes guesswork. Printed page =
PDF page − 1, confirmed on 162 pages.

**Two questions were established before extracting anything. Both matter.**

**1. The 1933–2001 series is SPOT YEARS before 1970 and annual after.** Printed
p.20 carries the table: 1933, 1940, 1946, 1950, 1955, 1960, 1963 — seven points —
then annual 1970 through 2001. **39 of 69 years present; 30 absent**, including
every year of the 1940s except 1940 and 1946.

**The chart on printed pp.18–19 plots all 69 years on its axis.** It is drawn
over data that does not exist for 30 of them. Anyone reading the chart rather
than the table would take an interpolation for an observation — so the chart is
not a source, and the table is.

**2. It cites no sources. Zero `Source:` lines in 164 pages.** There is exactly
one provenance statement, on the cover:

> *All salary data in this report comes from the NFLPA Salary Cap Information
> System*

**That cannot be true of the historical series.** The salary cap began in 1994;
a cap information system cannot be the origin of a 1933 figure. And the document
itself calls that figure an estimate — *"an estimated 1933 actual average NFL
salary of $8,000"*.

So, by the test Ryan set — *a 2002 primer citing sources is usable; one that
doesn't is `source_derived`* — **the whole series is `source_derived`**, and the
pre-1970 spot years are estimates by the document's own word.

**Worth naming: that cover line is `registry-1986` in an external source.** A
single provenance statement covering a whole document, naming *the system the
author read from* rather than *where each value came from*. §4.5 exists to stop
us doing it; this is what it looks like when a source does it to us, and it is why
a source-level provenance claim cannot be inherited by the claims beneath it.

**3. The primer and the 1981 hearing are ONE vote, not two.** The primer gives
1979 as **$68,900**. The hearing gives $68,900 for 1979 — verified verbatim:
*"According to our review of over 1,500 player contracts for the 1979 season,
average salary … was $68,900."* Same figure, same organisation, 21 years apart,
different authors.

**This is §4.3's lineage rule with a real case attached.** Counting them as two
agreeing sources would promote one party's standing position to multi-source
consensus, in the exact dispute §8.4 declines to resolve. `derived_from` on the
source declaration is what prevents it. It does, usefully, **confirm §8.4's season
attribution** — the hearing's $68,900 is unambiguously the 1979 figure.

**4. What is genuinely new: AVERAGE SALARY BY YEARS IN LEAGUE**, printed pp.70–79.
Per season, per service year, with **headcount, share of league, and average in
actual and 1997 dollars**. Current system 1993–2001; **old system 1983–1992**.

That is **one axis of the table the hearing proved existed** — per-experience, not
per-position, from 1983. It is the first per-cohort salary structure this project
has ever had, and it is `source_derived` from one interested party, which is
exactly how it should be stored and used.

**5. Correction to the brief: printed p.11 is a coaching-CHANGES grid, not
salaries.** It gives the head coach of record for every club at the end of every
season 1980–2002 — valuable as **stint** data, worthless as compensation.
Searched all 164 pages: **no coach compensation anywhere.** The NFLPA's 1980
estimate in the hearing above remains the only coach salary figure this project
has for any era.

### UPI, 30 September 1981 — the first per-position cell, at two removes

`upi.com/Archives/1981/09/30/Chargers-six-year-defensive-end-Fred-Dean-complaining-his-salary/8038370670400/`
**Fetched and read 2026-09-04**, not taken on relay. Plain `curl` with a browser
user-agent, HTTP 200. UPI's archive is free and fetchable.

Fred Dean, Chargers defensive end, holding out. His agent Dave Perrine reads from
the league salary schedule at a press conference:

> *Perrine … said that the recent NFL salary schedule showed that top defensive
> linemen with six years experience earned $185,000 a year, with the lowest paid
> receiving $62,000. He said the average of all defensive linemen was $70,000…*

**This is the CBA table the 1981–82 hearing described** — highest, lowest and
average, by position and years of service — being read aloud. The document reached
**agents**, not only the union office, which widens where a copy might survive:
agent papers, arbitration filings, contract-dispute litigation.

**The cell, with the corrections the article forces:**

| figure | value | cohort | dated? |
|---|---|---|---|
| highest | $185,000 | defensive linemen, **six years** experience | **no** — "the recent … schedule" |
| lowest | $62,000 | defensive linemen, **six years** experience | **no** |
| average | $70,000 | **all** defensive linemen, not the six-year cohort | **no** |
| Fred Dean | $65,000 | himself | **1980** — "last year" |

**Only Dean's own figure is dated.** The relay that reached this session assigned
the whole block to 1980; the article dates only Dean's. Perrine says "recent",
which spans 1980 and 1981 and cannot be narrowed from the text. Recorded as
`observed_at: 1981-09-30`, season **unresolved** — because that is what the source
supports.

**And the article contradicts itself, which is kept rather than tidied.** Dean
says *"Last year I was the lowest paid sixth-year defensive lineman in the NFL"*,
the schedule puts the six-year floor at **$62,000**, and published reports put
Dean at **$65,000**. All three cannot hold. Three claims, one contradiction, no
forced resolution — a `contested` set, and the disagreement is itself evidence
about how loosely a figure quoted in a dispute should be read.

**Attribution — three different chains in one short article** (§3.6):

    cohort figures   UPI -> Perrine (agent, interested party) -> NFL salary schedule
                     2 removes
    Dean's $65,000   UPI -> "published reports"
                     1 remove, origin UNNAMED and unchaseable
    "lowest paid"    UPI -> Dean, about himself
                     1 remove, and it is an assertion in a negotiation

Same shape as the League figures in the hearing and the primer, and it reinforces
the ruling: **a claim about a claim has no independent standing.** Held, used,
correctly labelled.

### Dallas Morning News via AP, 1982 — PENDING, the scan is not yet on disk

Reported 1981 salaries, published 1982, with a **stated margin of error under
$4,000**. Ryan holds it as a scanned newspaper PDF with text copied out in
Acrobat. **`acquisition: transcribed`** per §3.7 — not fetchable, not a relay.

**BLOCKED, and this is the ask:** the scan is not in `pgm3-sources/`. Until it is,
the figures below reached this session as conversational text and are therefore
`relayed` — **a lead, not a source, and nothing here may become a claim.** Put the
PDF in `pgm3-sources/` so it can be hash-pinned and a claim can cite a file rather
than a paste.

**OCR damage is already visible** in the transcribed text — `mewspaper`,
`alltime`, `$94948` with the comma lost, `hase salary`. Per §3.7 every numeric
gets a plausibility pass before any figure is called a source disagreement, which
is report 01's lesson: *a failing check may be your reading of the source rather
than the source.*

**Plausibility pass run on the relayed figures, to be re-run against the scan.**
Benchmark is the primer's 1981 league average of **$82,400**.

| figure | value | vs league | reading |
|---|---|---|---|
| QB average | $160,037 | 1.94× | plausible |
| RB average | $94,948 | 1.15× | plausible |
| WR average | $85,873 | 1.04× | plausible |
| Denver (high) | $106,000 | 1.29× | plausible |
| Kansas City (low) | $64,000 | 0.78× | spread 1.66×, plausible |
| Payton | $800,000 | 9.7× | high, but he was at the top of the market |

**Three things flagged for the re-read:**

1. **Dallas $89,170 and Washington $89,162 differ by $8.** Possible — but adjacent
   numbers in a column are exactly where a transcription slips. Re-read both.
2. **The 35.5% may not be on the same basis as the averages.** 35.5% of $15.42M is
   $5.474M; the team average × 53 is $4.726M, a gap of $748k. Not necessarily a
   defect — the article's salaries **exclude performance bonuses and playoff
   shares** and "spent on players" probably does not. But the basis must be read
   off the page, not assumed.
3. **Howard Richards is quoted on a different basis from everyone else.** $165,000
   *of which $105,000 was a signing bonus* implies a $60,000 base — 0.73× league
   on base, 2.00× on total. If the other named players are base-only, he is not
   comparable to them. **He is also the only component breakdown in any 1981
   source this project holds**, which makes getting his basis right worth more
   than the figure itself.

**Manning at $600,000 matches the January UPI story exactly — and that settles
nothing.** The precedent about exact matches across a gap requires the figure to
be *improbable under independent generation*. $68,900 is; **$600,000 is a round
number and an attractor**, reached independently by negotiation and by rounding.
Recorded as uninformative in both directions rather than as corroboration.
Sharpened in `DATASET_PRECEDENTS.md`.

**Provenance:** `stated_by: Dallas Morning News`, **attribution chain unknown** —
the paper does not say where the figures came from, and the club spokesman Greg
Aiello says *"I don't even know if it's accurate."* Better than Dean's two removes
— a paper's own reporting with a stated error bound, which implies a survey it or
AP conducted — but the origin is unnamed, so it cannot be tested for lineage
against the Management Council survey.

**The non-denial is weak evidence, not none.** A club spokesman declining to
contest specific figures about his own club is worth recording, and worth almost
nothing on its own.

**Definitional note that must travel with every figure:** these exclude
**performance bonuses and playoff shares**. The primer and the hearing do not use
that basis. Any comparison across the three needs it stated, or it manufactures a
disagreement out of a definition.

### The method this opens — reconstruct the table one dispute at a time

Every holdout of 1980–83 had an agent quoting the same survey. UPI's archive is
free and fetchable, and each story yields another cell.

**Not the document — a reconstruction of it.** Search UPI 1980–83 for `NFL
salary`, `salary schedule`, `holdout`, plus position words. Ryan is running that
search; cells get logged here as they arrive, each with its own attribution chain
and its own dating problem, because "the recent schedule" will recur.

**Two cautions for whoever assembles it.** Cells gathered this way are quoted by
*agents in active disputes* — a population selected for grievance, so the figures
an agent chooses to read aloud are the ones that support a holdout. And a cell's
cohort definition must be read exactly: this article gives a **six-year** high and
low against an **all-players** average, and conflating them would put Dean's
$65,000 against the wrong benchmark.

### OWED: a League-original source

**Recorded as a debt, per Ryan's ruling 2026-09-04.** Every League figure this
project holds arrives quoted by the NFLPA or by an agent. No document in which the
**NFL states its own number** is in hand.

What would satisfy it:

- NFL Management Council material — the salary schedule itself, or any circular
  reproducing it
- League financial disclosure, in any proceeding
- **A court filing in which the League states its own figure** — *Mackey*, the
  1982 antitrust litigation, or any contract-dispute arbitration

Until one exists, §8.4's contest is **one party and one hearsay**, and the
dataset should say so.

### THE HIGHEST-VALUE OUTSTANDING SALARY LEAD

The hearing reproduces CBA language describing a document it does not contain:

> …a compilation of salary information which shall set forth the average salary
> for all players then under contract to the Member Clubs, including current and
> deferred compensation and any signing or reporting bonus, **compiled by team
> positions and years of service** of the players. This information shall also
> include **the highest and lowest salary for each team position**…

**An annual NFLMC→NFLPA return, per position, per service year, with highs and
lows, existed contractually in this era.** That is precisely the granularity an
export needs and the hearing proves it existed without printing it. Candidate
holders: NFLPA publications, *Mackey v. NFL* and later antitrust filings,
subsequent oversight hearings. **Log it as the top salary lead.**

*Garvey's prepared statement is not in this volume — printed p.597 here is
testimony attacking Rozelle, and Garvey appears around 593–594. Google collapses
the other editions into this same record, so a separate volume needs finding
rather than following a link. Not a priority; the table is the prize.*

---

## 10. What I would do next, if the design is broadly accepted

In order:

1. ~~Measure §9.1.~~ **Done 2026-09-04.** Tier A is real for players and head
   coaches, resting on a bidirectional cross-reference rather than a string.
2. **Measure §9.2** — birth-date fill rate per decade. An hour, and it decides the
   earliest era's discriminator.
3. ~~Measure assistant-coach identity in the media guides.~~ **Done 2026-09-04,
   same day, because §9.1 promoted it.** Result in §2.4: birth dates are absent
   (2.7% of coach-title bios; 21 of 28 guides have none), so assistant identity
   rests on **stint continuity** instead. The consequence to carry forward is that
   two same-named assistants with overlapping career chains have no discriminator
   at all, and the design should expect to refuse those rather than resolve them.
4. **Get rulings on §9.3, §9.5, §9.6, and §9.8's boundary.** §9.7 is ruled.
5. Write the source declarations for StatsCrew and the media guides — the two
   backbone sources — including their discriminators and their absence semantics.
6. Ingest one season end to end, chosen for difficulty rather than convenience.
   **I would propose 1950**, because it has two leagues in living memory of a
   merger, era-native positions with no modern equivalent, two-way players, a
   Baltimore Colts franchise that is almost certainly *not* the one that later
   moved to Indianapolis (from general knowledge, not measured — exactly the kind
   of continuity claim §5.2 exists to hold and §9.5 exists to doubt), and — per
   the roster page I read — full birth dates. It exercises §2, §5.1, §5.2 and
   §5.4 at once.
7. Export it to PocketGM and see what breaks. The export is a good first test
   precisely because it demands every field, but it does not get a vote on what
   the dataset holds.
