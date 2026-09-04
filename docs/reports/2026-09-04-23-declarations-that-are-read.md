# 23 — Every declaration must be read by something

2026-09-04. Branch `dataset-design`. Follows report 22.

You asked for a check that every declaration is read by something, not just that
it exists. It is `src/gate_declarations_are_read.py`, and it found more than the
three known instances.

---

## 1. The check, and what it found

The property: **every declaration key must appear as a string literal somewhere
in `src/`.** A key nothing reads is a note, and a note that looks like a
declaration is worse than a note, because the next reader assumes the ingest
honours it.

Run against the existing declarations, before any fix:

> **107 of 176 keys — the majority of what was written as declaration was
> note.**

That is the honest headline. Three instances were known; the check found a
population.

**The read test is a string-literal grep, and that is a proxy.** It cannot see a
key that is read and then ignored — only one that nothing so much as names. That
limit is stated in the gate rather than left for someone to discover.

---

## 2. The worst thing it found: the model duplicated the declaration

`model.py` held the salary conventions as Python literals instead of reading
`declarations/salary_conventions.json`.

**Demonstrated, not inferred.** A convention added to the declaration and
nowhere else:

```
DECLARED in the JSON, REFUSED by the code:
  'salary_base_plus_workers_comp' looks like money but is not a declared
  convention. Add it to declarations/salary_conventions.json
```

The refusal names a fix that has no effect. You do the thing it asks and it
refuses you again.

**And the drift was already real.** The hardcoded system-predicate list had
**five** entries; the declaration has **nine**. Four predicates were declared and
unknown to the code:

`draft_compensation_ladder` · `inter_club_transfer_fee` ·
`player_movement_regime` · `qualifying_offer_floor`

All three lists now come from the declaration. The fifteen salary conventions
match the old hardcoded set exactly, so no salary figure changes.

### The consequence: a figure that could not be filed

`inter_club_transfer_fee` exists for exactly one thing in the corpus, and it is
missing. Verified in the source rather than taken from conversation:

> "he eventually obtained clearance to play for the Minnesota Vikings when the
> latter paid Kapp's Canadian team **$50,000 for his release**"
> — *Kapp v. NFL*, 390 F. Supp. 73 (N.D. Cal. 1974)

`extract/courts.json` holds nine predicates across the Kapp entries. None is a
transfer or release fee. The predicate was declared, the code would have refused
it, and the figure was never extracted.

**It is still not extracted, because filing it needs a ruling — see §5.**

---

## 3. What was wired in

Thirteen keys moved from note to enforced. The three that matter:

**`league_codes` — the AFL3 trap is now inexpressible, not documented.**

```
  NFL    accepted
  CFL    accepted
  AFL3   REFUSED: league code 'AFL3' is a DECLARED TRAP: the ARENA Football League
  AFL2   REFUSED: ... page EXISTS but carries NO roster links
  XFL9   REFUSED: not in league_codes.VERIFIED_with_rosters
```

You called AFL3 the dangerous one and asked for it to be its own line. A line did
not stop it; a refusal does.

**`discriminators` — the design's claim is now true.** §2.4 said "the ingest
refuses to run without one." It said so for a while before it was true. The
ingest now reads the declared order for the era and exits if there is none.

**`season_not_played` — a cancelled season refuses itself, with its reason:**

```
REFUSED CFL-2020: the CFL cancelled its 2020 season entirely (COVID-19).
  a league-season with no teams is an ABSENCE to declare, not a sweep failure
  to retry. Retrying it would fetch the same empty page forever.
```

Also wired: `url_patterns` (the fetcher no longer hardcodes URLs) and
`absence_semantics`.

### And a gate for the rules that are prose

`salary_conventions.hard_rules` is seven prose rules. They are enforced — by
gates that never referenced them. Gate 11 now requires **every declared hard rule
to name its enforcing gate**. Adding a rule to the declaration without enforcing
it fails:

```
[FAIL] every declared hard rule names an enforcing gate
       declared hard rules with NO enforcing gate: [4]
```

### The exemptions live in the declarations, not in the checker

The remaining keys are genuinely addressed to a reader — `coverage`, `scores`,
`local`, `known_conflicts`, measurement records. Each declaration names its own
under `_documentation_only`, with a reason per key. **Widening the exemption is a
change to the declaration and shows up in a diff**, rather than a quiet edit to
the gate that would turn the check into a rubber stamp.

---

## 4. CFL-1945 is now a stated limit in the design, not a report finding

§2.4 rested on a 25-sample grid: *"birth date is ≥96% in every league-year
sampled."* Report 06 later put the floor at 88.8%. The census measured **CFL 1945
at 32.9%**.

The design now carries this at the point of the claim it qualifies:

- For **CFL 1945–1949** the discriminator order is `source_native_id`,
  `birth_date`, `college`, `position` — and birth date is absent for two thirds
  of players while college is 56.7%. **There is no discriminator beyond the
  source's own id.**
- That is enough to keep one source's rows apart. It is **not** enough to merge a
  person across sources, and not enough to separate two men with the same name on
  one roster.
- **The rule: same-name pairs in those seasons are REFUSED, not resolved.**
  Anything else invents a distinction the sources do not support.
- 1950–1957 is weaker than the grid too, at 75–84%.

The grid was not wrong. It was a sample, and it did not reach 1945 because the
CFL was assumed to start in 1958 — which is also how the back-mapping went
unnoticed. Same lesson as the granularity corrections: **a sample tells you a
field's typical value; only a census tells you its range.**

---

## 5. One thing I did not do, because it needs your ruling

Kapp's $50,000 is a payment **from one club to another**, for a player's release.
`inter_club_transfer_fee` is declared under `system_rules.predicates`, and
`model.py` requires a system predicate to sit on a **league-scoped subject**.

That is wrong for this figure. A league-scoped claim says *this is how the regime
works*. The $50,000 is not a regime — it is one transaction, between Minnesota
and a named Canadian club, about one man, on one date. Filing it on the league
would state a rule where there is an instance.

So the declaration and the model disagree about what kind of thing this predicate
is, and I would be guessing at the subject shape. Three options:

1. **A new `transfer` subject** — `("transfer", person, from_club, to_club, year)`,
   the same move that fixed the two-Kapp-contracts false contest.
2. **Keep it league-scoped** and treat the $50,000 as evidence *about* the
   regime, losing which clubs and which player.
3. **A club-pair subject** without the player, if the fee is properly a fact
   about the clubs.

I lean to (1): it preserves everything the court states and it matches the
precedent already set for contracts. But it adds a subject shape, and that is
yours to rule on.

The same question governs the other three newly-usable predicates —
`draft_compensation_ladder`, `player_movement_regime`, `qualifying_offer_floor` —
which do look genuinely league-scoped. Only the transfer fee is an instance
wearing a rule's clothing.

---

## 6. Precedents recorded

Two, both at general form rather than as a fourth anecdote:

**"An empty result and a failed one are the same bytes."** Fourth instance:
archive.org's 302, the zero-byte cache, the `<tbody><td>` parse, and now 13
zero-row team pages. *Nothing may report an absence it did not expect.* The tell
is a suspiciously round success — 100% fill, 0 errors, 0 rows. Three of the four
announced themselves as clean results, and so did the denominator defect.

**"A declaration in the wrong place is not a declaration."** Third instance,
third shape: computed-and-unreferenced, right-file-wrong-block, prose-nothing-
enforces. *A declaration is defined by being read, not by being written.*

---

## 7. State

11 gates · **11 pass** · **11 fire when broken** · plus three standalone gates
(census denominator, declarations-are-read, real bases) all passing.
Declaration keys unread: **0 of 177**. No salary figure or roster row changed.

Owed: the transfer-fee ruling above; assistants from the media guides (2,105
indexed, 28 on disk); QB ratings from statistics; the Raiders/Rams per-row
confidence field; the Elway document; Staudohar; the Mackey Archives request.
