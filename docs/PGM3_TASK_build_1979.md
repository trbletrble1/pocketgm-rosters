# Task — 1979 season build

Build `PGMRoster_1979.json` and `PGMStaff_1979.json`.

Opened by the build session 2026-09-02 against repo commit `3e6f9a2`.
Rulings by Ryan (master session) as marked.

**Read first:** `CLAUDE.md`, `docs/PGM3_PROJECT_HANDOFF.md`,
`docs/PGM3_BUILD_FRICTION.md`, `docs/PGM3_PRECEDENTS.md`, and
`docs/PGM3_TASK_build_2000.md` + `docs/PGM3_TASK_2000_HOU.md` as the closest
analogue. Where this brief and the handoff disagree, **say so rather than
picking one** — that is an escalation, not a judgement call.

---

## What 1979 is

Last season of the 1970s. 28 teams. Pittsburgh win their fourth Super Bowl in
six years, beating the Rams 31-19. Staubach's final season. Montana is a rookie
third on San Francisco's depth chart. Earl Campbell runs for 1,697 yards.

PGM3 needs 32 team IDs, so **four franchises are invented.**

---

## Settled — do not re-derive

| item | state |
|---|---|
| Team ID mapping | Ruled. See below and the handoff's roster-record rules |
| Vacant slots | `CAR`, `IND`, `JAX`, `TEN` |
| Archive era gate | Ruled. Vote-presence, not `era_certain` — see below |
| Payroll basis | Median top-53 salary+guarantee = **$197.4M**, engine cap ~$280M |
| Contracts | Invented. No salary data exists before 2000 |
| Coordinator vacancies | Promote the senior real assistant, record in `note` |
| Scouts and physios | Generated. The standing exception to no-invented-humans |
| Head coaches | Always real, including in the free agent pool |

### Team IDs — city where a slot exists, lineage where it does not

    Houston Oilers   -> HOU    Earl Campbell displays as Houston
    Baltimore Colts  -> BAL    Bert Jones displays as Baltimore
    vacant: CAR, IND, JAX, TEN

Recorded in full in the handoff on 2026-09-02; three published files depended on
it and it had never been written down. **The Colts invert between 1979 and
1986** — real in `BAL` here, real in `IND` there, with the other slot invented
in each. Same rule, different answers, because the franchise moved.

### The archive era gate — ruled 2026-09-02

`reference/PGM3_PLAYER_ARCHIVE.json` is the appearance source. The
**`1979-1980` file is the archive's strongest single source**: 1,999 players,
1,999 edited, the only file of 42 at 100%. 1,921 entries carry a vote from it,
against a 1979 league of roughly 1,260 rostered players; 93.4% unanimous.

**Take era membership from the presence of a `1979-1980` season vote. Do NOT use
`era_certain` or `first_seen`/`last_seen`.**

```python
in_era = any(v['src'] == '1979-1980' for v in entry['votes'])
```

The window is a derived field with a known defect on exactly this cohort — the
`stock` flag is keyed on name alone, so genuine 1979 men with modern namesakes
get a window built from files that do not contain them, and `era_certain` reads
`True` anyway. D.D. Lewis reads 2004-2009. Full mechanism and measurements in
`PGM3_AUDIT_BACKLOG.md` item 18.

**Owed:** the position-aware re-test against the full ultimate70s rosters. The
archive-side half is done (name+position frees 59 of 338; recovers 29 of the 33
PFR-confirmed genuine players). The 33 is a floor — PFR stat tables cover only
the 1,144 men who recorded a stat.

---

## Sources

**Ryan fetches. The build session does not** — PFR is 403 from this transport and
`ultimate70s.com` has not been tested from it. Ask; do not try.

### Already in the repo at `3e6f9a2`

`sources/1979PFR/` — all 28 team pages, the 1979 coaches index, the 1980 draft
listing. Saved HTML, so no CDN-stale failure mode. Measured coverage of the 28
team pages:

| field | coverage |
|---|---|
| head coach + season record | 28/28 |
| defensive alignment (11× 3-4, 17× 4-3) | 28/28 |
| defensive coordinator | 26/28 — Cleveland and Detroit blank |
| **offensive coordinator** | **11/28** |
| named assistants with unit responsibility | 28/28 |
| points for/against + league rank, SRS/SOS, playoffs | 28/28 |

**There is no roster or starters table on a PFR team page.** The 17 missing OCs
are a real feature of 1979, not a research gap; every one has a real offensive
assistant on the same page to promote.

### Needed from Ryan

1. **`https://www.ultimate70s.com/nfl_roster/{CODE}/1979/N`**, one per team —
   the only source giving the full 45-man roster. Anchor-check before trusting
   it wholesale; it is a fan site.
2. **PFR coach pages** for career records through 1978. The season coaches index
   is **confirmed unusable** for career records — do not re-try it.
3. **1981, 1982, 1983 draft pages** (1980 is already in the repo).

---

## Namesake landmines specific to this file

Four documented traps land in 1979 at once. Handle deliberately; do not discover
them at gate time.

| person | 1979 role | the trap |
|---|---|---|
| **Frank Gansz** | Cincinnati (ST/TE) | Sr./Jr. — malformed three different ways across 1986/2004/2007. Sr. is the 1986 KC and 2000 JAX coach |
| **Jim Mora** | Seattle (DL) | Sr./Jr. — registry holds Sr. in `staff_faces_1986`, Jr. in `staff_faces`; the name-alone key cannot express it |
| **Dick LeBeau** | Green Bay (DB) | Documented validator false positive on duplicate names |
| **Bill Belichick** | NY Giants (def. asst/ST) | Earliest appearance in the archive by seven years |

On the player side, the residual same-position namesakes from the archive
re-test are **D.D. Lewis (OLB)**, **Stanley Morgan (WR)** and **Kellen Winslow
(TE)** — Winslow being the canonical father/son case the handoff already names.

---

## Build order

Follows the handoff's order. Steps 1 and 4 are the ones with open questions.

**0. Docs.** Done 2026-09-02 — this file, the team-ID rule, backlog item 18, the
archive-cohort amendment, and the stale era-scale line deleted from the 2000
brief.

**1. Anchor-check ultimate70s.** Pittsburgh, Houston, San Francisco, Tampa Bay
first. Check roster against the PFR stat tables, and jersey/position/games
agreement. **Report the number before going further.**

**2. Cohort and positions.** 28 real teams → modern IDs. Check the CB/S ratio
against the published band (1.06-1.30) before moving on.

**3. Appearances — early, not last.** From the `1979-1980` archive file under the
vote-presence rule. Run the conditional pass the moment they are built.

**4. Ratings and attributes — THE OPEN QUESTION.** There is no Madden or 2K5
attribute data for 1979; the archive is skin-band only. **Ruling (Ryan,
2026-09-02): bring a measured proposal, do not settle the method in advance.**
The proposal must carry:

- what production data actually exists **per position** — kickers and punters are
  well served, offensive linemen are not
- how players with **no stat line at all** are handled
- an **anchor test against known 1979 quality** before anything is built

**5. Contracts.** Invented, scaled to the $197.4M top-53 constant. Era-accurate
ratios and orderings; the dollar scale alone comes from the engine. K/P ceilings
from the era's real market, not from the published files — they carry a
documented inflation defect.

**6. Staff.** 9 per team × 32. Real coaches; promotions logged in `note`.

**7. The four invented franchises** — `CAR`, `IND`, `JAX`, `TEN`. See below.

**8. Draft classes 1980-1983**, then the face registry **last**, then all gates.

---

## The four invented franchises

**Do not reuse the 1986 stories.** The Baltimore Stars, Jacksonville Bulls,
Tennessee Showboats and Carolina Rattlers are established in a published file
and a published Reddit post. 1979 is a separate counterfactual with no
connection to them. New names, new owners, new coaches, new reasons to exist.

**1979 is not the 1986 premise.** The WFL folded in October 1975 — four years
cold, not four months.

| slot | the real situation |
|---|---|
| `TEN` | **Memphis** sued the NFL for a franchise and lost in court |
| `CAR` | **Birmingham** won the WFL's only completed championship, folded in debt |
| `JAX` | **Charlotte** had a team that arrived already broken, moved mid-season from New York |
| `IND` | **Indianapolis** — no professional football, no WFL history. A different kind of story from the three that lost something |

Four separate stories, not one shared premise. The 1986 post's franchises read
as separate campaigns and that is deliberate.

### The structural rule, from the 2000 Houston build

**The roster falls out of the franchise's situation rather than being designed.**
Houston 2000 had a GM with no scouting department, so he signed only players he
could already evaluate — which produced nine running backs and four receivers on
its own. Nobody chose the shape.

**Find the equivalent constraint for each of these four and let it shape who
they sign.** A constraint agreed first, a roster second. Bring the four
constraints to Ryan before building any roster.

**Every player is a real person.** Scouts and physios are the documented
exception. Head coaches are always real, including in the free agent pool.
There is no team-name field in the schema — `teamID` is the only team column, so
all naming is Reddit-post copy, not data.

---

## Before any push

    python3 tools/pgm3_validate.py roster PGMRoster_1979.json PGMRoster_1986.json PGMRoster_2000.json PGMRoster_2004.json
    python3 tools/pgm3_validate.py staff  PGMStaff_1979.json  PGMStaff_1986.json  PGMStaff_2000.json
    python3 tools/pgm3_validate.py faces  PGMRoster_*.json

Plus every conditional pass, reported alongside the validator output. **Then
stop** — the last gate is not automated. Ryan imports the file and plays it.

---

## Standing rules for this build

**Measure first, and bring the number to the question.**

**Report before writing.** The outcome changed six times in the last session,
including once where following an instruction would have wrecked 1,330 ratings.

**A contradiction between documents is an escalation, not a judgement call.**
That situation shipped a broken 2000 file.

**Never invent data when real data exists.** Leave the field empty and log it.

**Cut on the defect's signature, not the category that contains it.** A fix
scoped by position destroyed 52 real ratings last session; every assertion
passed and only a git diff caught it.

**Every check runs once against a population where it must fail, and once
against an empty one.** A green gate over an empty set reads identically to a
real pass.

**Assert the count on every keyed write.** `assert len(out) == len(inp)`.

**Say which commit you are holding.**
