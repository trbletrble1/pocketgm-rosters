# Using the archive — for the master session

*Written 7 September 2026, final revision that evening. How to actually query the thing, and what its answers mean.*

---

## What you have

**Fourteen MCP tools**, served from the mini over a public HTTPS address. They are **read-only** — nothing you can call writes to the archive, and `rebuild` is refused outright.

| tool | what it answers |
|---|---|
| `get_person` | Everything held about one man: every name claim, facts by family, stints by club-season, statistics, coaching and officiating seasons, photographs, guide prose, identity, merges |
| `get_bio` | His written biography and vitals panel |
| `search_people` | Candidates for a name — never one answer |
| `get_club_season` | A club's roster for a year, with the claims that place each man there |
| `get_club` | A club as the table holds it: names by year, leagues, every source string, lineage |
| `search_clubs` | Club names matching a string |
| `census` | Coverage for a fact family over a stated population |
| `census_club_seasons` | How many club-seasons a year holds — several honest answers |
| `list_sources` | Every source in the archive |
| `get_source` | One source's declaration: acquisition, lineage, known traps |
| `get_source_record` | Every claim one document produced |
| `list_contested` | The disagreement worklist |
| `snapshot` | What is being served, and what has changed since it was built |
| `sessions_status` | What the Claude Code session is doing |

**If you have thirteen and no `get_bio`, the connector's tool list is stale.** It is cached from when the connector was created, not when a chat opens. Remove the connector and re-add it with the same URL. This has already caused one false alarm, where a session appeared to have invented a tool it had in fact built.

---

## The one thing to understand before using any of it

**The archive never chooses.** A man with three birth dates has three birth dates, and every tool returns all of them with the document each came from.

So a fact does not come back as a value. It comes back as a **family** with a list of values, each carrying its claims, plus `contested: true` when more than one calendar day is present.

```
"birth_date": {
  "values": [
    {"value": "August 26, 1991",   "predicate": "birth_date",          "claims": [...]},
    {"value": "1991-08-26",        "predicate": "nflverse.birth_date", "claims": [...]},
    {"value": "December 28, 1993", "predicate": "pfa.birth_date",      "claims": [...]}
  ],
  "same_day": [["August 26, 1991", "1991-08-26"], ["December 28, 1993"]],
  "contested": true
}
```

`same_day` is **derived** — it reads the strings as calendar days so that one date written two ways is not reported as a conflict. It is labelled as derived and the original strings are always shown beside it.

**If you ask for a single value, the service returns a 409 with the candidates.** There is deliberately no policy verdict and no tie-breaker. Report the disagreement with its citations; do not resolve it.

---

## Reading a person

**`facts`** — grouped by family. Multiple predicates can mean the same thing (`birth_date`, `pfa.birth_date`, `nflverse.birth_date`, `wikipedia.birth_date`) and the family groups them. `hometown` is deliberately **not** folded with birthplace; where a man was born and where he was from are different facts.

**`seasons`** — his club-seasons, each with the claims that place him there. Some come from a roster page; some were derived from boxscore appearances because no source ever held a roster for that club. The store says which.

**`roster_membership.*` predicates** — these carry a **definition**, because five sources answer five different questions:

| predicate | what the source meant |
|---|---|
| `started_a_game` | named in a starting lineup, from a boxscore |
| `on_active_roster` | activated or elevated to the active roster |
| `on_reserve` | on a reserve list — injured, PUP, suspended, military |
| `practice_squad` | practice, taxi or developmental squad |
| `drafted_by` | rights acquired in a draft, not a roster spot |
| `signed` | signed to a contract; signed is not rostered |
| `acquired` | trade, waiver claim, purchase |
| `departed` | released, waived, free agent, retired |
| `rights_retained` | franchise or transition tag — the opposite of departing |
| `on_a_roster_at_any_point` | nflverse's wider definition |

A man holding several of these is normal and not a contradiction.

**`merged_into` / `merged_from`** — 93 people were merged after being held twice. An absorbed record still answers, with a pointer to the survivor. Never a silent redirect.

**Names** — 4,567 people have no name claim at all. Their name may live in a promotion decision rather than a claim. The service says so in words rather than returning null.

---

## Reading a bio

`get_bio` gives prose and a vitals panel as separate fields, both labelled `derived` with a recipe digest that changes when the generator changes. The bio is assembled from claims at read time — it is not itself a claim, and it changes when the underlying facts change.

**Structure:** a lead scored three ways so the shape varies by the man, a body covering the career, and a close carrying a human fact. **When there is no close, the bio ends.** That is deliberate. Three sentences that stop are better than four where the fourth is filler.

**Two populations:** 43,517 people in the archive, 40,523 with a bio. A bio needs a season and a name. The endpoint says which was missing rather than returning blank.

**Cost:** the generator is corpus-wide, not per-person. About 3 seconds and 2 GB on the first call, then a tenth of a millisecond per bio after.

### The panel and the claims do not always agree — in both directions

This is the most important thing on this page.

**Quieter than the claims.** The panel names a disagreement only from certain stores, so a man can show one birth date while `facts` holds three. Reported as `panel_quieter_than_the_claims`.

**Louder than the claims.** The panel can flag a disagreement the archive's own contested table does not have.

Measured across all 40,523 people, for birth dates alone:

| | |
|---|---|
| archive contests **and** panel flags | 905 |
| panel flags, archive does not | 620 |
| **archive contests, panel shows as settled** | **1,527** |

The 620 are mostly cases where the panel's second value is not a claim in the model at all. The 1,527 are the direction that **loses** information.

**If accuracy matters for what you are doing, read `facts`, not the panel.** And do not report any of these as a single number — three groups, three causes, three probable answers.

---

## Reading a club

`get_club_season` resolves the club string through the club table and tells you **how** it resolved — by code, official name, alias, or a name that was wrong for that season. That last one matters: there really was a Buffalo Bisons, in 1946, in the AAFC. A 1986 Buffalo Bisons is a source defect and the table records it as one.

**Empty and missing are different bytes.** A club-season the table holds but no roster covers returns 200 with `basis: unknown`. A club-season the table does not hold at all returns 404 with the nearest names it does hold.

**Merged clubs are their own clubs** — Card-Pitt, Phil-Pitt, Brooklyn-Boston, and the 1934 Cincinnati Reds distinct from the St. Louis Gunners. Their rosters were built from who provably appeared in games, because no source ever ingested one.

---

## Census — and why a count is never one number

`census` returns a **basis distribution over a stated population**, not a total:

- **observed** — a source says so
- **absent** — a source asserts there is nothing
- **contested** — sources disagree
- **unknown** — nobody has looked

"How many people have a death date" is 8,682 observed, 118 contested, 2 absent and 36,313 unknown. The unknown are not men who did not die; they are men no death-carrying source has been read against.

`census_club_seasons` behaves the same way. 1926 has 31 roster club-seasons, 23 coaching-season keys, and whatever the club table holds as active — **three honest answers, and the tool does not add them.**

---

## Sources

`get_source` returns a declaration: how it was acquired, who stated it, what it derives from, and its known traps. Some sources have no declaration and the tool says so rather than inventing one.

**Ranking, where it matters:** media guides and contemporary newspapers above Wikipedia. Wikipedia infobox facts are effectively uncited; its prose is better. Fandom wikis rank low and cite the same lineage as everything else.

**The lineage finding.** StatsCrew, PFA and the fandom wiki all descend from David Neft's 1970s reconstruction of the pre-1933 record from newspapers. **Their agreement on the 1920s is an echo, not corroboration.** Do not treat it as three independent sources.

**One source's disagreement report is not backed by claims.** `nflverse-rosters.json` records 1,079 people as `"ruling": "UNRESOLVED - both held"`, and for 1,021 of them the second value is held nowhere. If you are reasoning about nflverse conflicts, the report and the store do not agree, and the store is the thinner of the two.

---

## What the WARNING means

Every response currently carries a warning, because two gates are red:

- **G3** — 414 `club-names` claims name source records that were never registered.
- **RS-G5** — `guide-pre1950-delimited.json` nests its 1,653 claims where the reader does not look, so the model cannot see them. It is the **only** file in all 1,146 that does this; the red is bounded, and it is red on purpose rather than declared away.

Both stay loud. There is no exception list — making them quiet is how they get forgotten.

`snapshot.inputs_changed_since` tells you when what you are reading is behind the stores. Auto-rebuild is off deliberately.

**One caution about that field:** it reports on a window, and a brand-new store file may not be a declared input at all. An empty `inputs_changed_since` is not proof that nothing has landed.

---

## Good first questions

- `get_bio` on Chuck Noll — he was two half-men until the merges, so it tests whether the archive holds one career.
- `get_club_season` on `NFL/1943/PNP` — the Steagles, whose roster was derived from game appearances and later matched PFR's 30 for 30.
- `list_contested` with `family=birth_date` — but read the panel section above before quoting the number.
- `census` on `photograph` — and read §8 of the context document before believing it.

---

## What it cannot do

- It cannot write. Nothing here changes the archive.
- It cannot resolve a disagreement, by design.
- It cannot answer for a source that has not been ingested. "Not in the archive" means not yet held, not did not exist.
- It does not know what the session is currently mid-way through — read `sessions_status` and the Dropbox reports for that, and treat a stale status entry as stale rather than as fact.
