# `sources/pfr/` — 2000 coaching staffs

## Files

| file | what it is |
|---|---|
| `coaches_2000_HC.csv` | 31 head coaches, pre-existing and verified. Not re-derived. |
| `coaches_2000.csv` | 124 rows — 31 teams x `HC`/`OC`/`DC`/`ST`. Built 2026-08-31. |

Columns of `coaches_2000.csv`: `team, role, name, source, note`. `source` is the
page the name came off. `note` carries every ambiguity; 25 of the 124 rows have
one and they are the rows worth reading.

---

## PFR: direct fetch is blocked, search snippets are not

Two separate facts, and the distinction is the useful part.

**Every direct transport is blocked.** On 2026-08-31, `pro-football-reference.com/teams/{abbr}/2000.htm`:

- plain `curl` — HTTP 403
- `curl` with a browser User-Agent — HTTP 403
- WebFetch — HTTP 403, on two different team pages
- the in-app browser — Cloudflare "Performing security verification"

That last one is a bot check and getting past it is off-limits, so that route is
closed for good. The handoff's original blocked note was right about fetching;
the task doc's correction was wrong.

**But the coaching block is readable through web search snippets.** A
domain-restricted `WebSearch` against `pro-football-reference.com` returns PFR's
own coaching content — coordinators and the `Other Notable Asst.` list — without
ever fetching the page.

This was tested with a negative control before being relied on. Asked for the
2000 New England defensive coordinator, the search **correctly reported that
none is listed** and named Mangini (defensive backs), Rob Ryan (linebackers),
Daboll and Davidson — matching the independently fetched Wikipedia staff, and
using PFR's role labels rather than Wikipedia's. A summariser inventing an
answer would have named a coordinator. It is grounded in the page.

Practical rule: **search PFR, do not fetch it.** Snippets give you the coaching
block; they do not give you a full page, so treat what comes back as a quotable
fragment and corroborate anything load-bearing, as `ARI/DC` was corroborated
against Wikipedia's own Larry Marmie article.

Two rows in `coaches_2000.csv` carry PFR sources on this basis: `ARI/DC` and
`CIN/DC`. The other 122 came from Wikipedia season pages.

## What was used instead: Wikipedia season pages

The documented fallback, `https://en.wikipedia.org/wiki/2000_{Team}_season`, and
it turned out to be much better than the task doc expected. The doc warned that
Wikipedia "carr[ies] no special teams coach, and some (Buffalo 2000) carry no
coordinators at all". Both warnings are out of date:

- **Every one of the 31 pages has a `Staff` section with a Special teams
  subsection.** All 31 `ST` rows are filled.
- **Buffalo has both coordinators** — Joe Pendry and Ted Cottrell.

Denver's staff section reproduces the PFR block quoted in the task doc exactly,
including preferring Rick Dennison ("Special teams") over Anthony Lynn ("Special
teams assistant") — which is the disambiguation rule the doc asked for.

---

## Pages fetched, all on 2026-08-31

All 31 season pages, one fetch each, extracted to
`raw.jsonl` in the session scratchpad at extraction time:

    2000_Arizona_Cardinals_season      2000_Minnesota_Vikings_season
    2000_Atlanta_Falcons_season        2000_New_England_Patriots_season
    2000_Baltimore_Ravens_season       2000_New_Orleans_Saints_season
    2000_Buffalo_Bills_season          2000_New_York_Giants_season
    2000_Carolina_Panthers_season      2000_New_York_Jets_season
    2000_Chicago_Bears_season          2000_Oakland_Raiders_season
    2000_Cincinnati_Bengals_season     2000_Philadelphia_Eagles_season
    2000_Cleveland_Browns_season       2000_Pittsburgh_Steelers_season
    2000_Dallas_Cowboys_season         2000_San_Diego_Chargers_season
    2000_Denver_Broncos_season         2000_San_Francisco_49ers_season
    2000_Detroit_Lions_season          2000_Seattle_Seahawks_season
    2000_Green_Bay_Packers_season      2000_St._Louis_Rams_season
    2000_Indianapolis_Colts_season     2000_Tampa_Bay_Buccaneers_season
    2000_Jacksonville_Jaguars_season   2000_Tennessee_Titans_season
    2000_Kansas_City_Chiefs_season     2000_Washington_Redskins_season
    2000_Miami_Dolphins_season

Re-fetched in full to resolve a specific gap: Arizona, Cincinnati, Jacksonville,
New England, Washington.

Two coach pages, for Dallas only: `Mike_Zimmer`, `Joe_Avezzano`. One more,
`Larry_Marmie`, to corroborate the Arizona DC ruling.

PFR search snippets (no page fetched), for the two DC rulings:
`teams/crd/2000.htm`, `teams/cin/2000.htm`, plus `teams/nwe/2000.htm` as the
negative control described above.

---

## Cross-checks

The five OC/DC pairings the task doc says a correct extraction must reproduce
independently were all reproduced, and the build script asserts them:

| team | OC | DC |
|---|---|---|
| ARI | Marc Trestman | Dave McGinnis |
| BAL | Matt Cavanaugh | Marvin Lewis |
| CHI | Gary Crowton | Greg Blache |
| DEN | Gary Kubiak | Greg Robinson |
| WAS | Terry Robiskie | Ray Rhodes |

Both self-consistency checks the doc points at came out right: Wikipedia has
McGinnis as Arizona's DC before his promotion, and Robiskie on Washington's
offensive staff.

All 31 `HC` names are copied from `coaches_2000_HC.csv` and asserted equal to it.
The four mid-season changes follow Ryan's ruling — the slot goes to whoever
coached the most games — and each `HC` note records the man who lost the slot.

---

## Open items

**Two rows are deliberately blank.** Both are real absences in the 2000 season,
not missing research, and both are evidenced by a complete position-coach list
with no coordinator in it:

- `JAX / OC` — Coughlin ran the offense. Source lists QB Petrino, RB Ingram,
  WR McNulty, TE Hoaglin, OL Maser, QC McGee, and no OC.
- `NE / DC` — Belichick ran the defense. Source lists DL Melvin, LB Ryan,
  asst LB Johnson, DB Mangini, asst Walker, and no DC.

**Both open DC questions are now RULED (Ryan, 2026-08-31)** and the two rows are
sourced from PFR search snippets:

- `ARI / DC` — **Larry Marmie.** McGinnis had the defence for games 1-7 and moved
  up to HC; Marmie took it for games 8-16 and held it through 2003. PFR lists
  both men as 2000 DC. Corroborated against Wikipedia's `Larry_Marmie` article,
  which gives "Arizona Cardinals (2000-2003) Defensive coordinator" — the guess I
  refused to make in the first build turned out to be right, but it is in the
  file now because it was sourced, not because it was obvious.
- `CIN / DC` — **Dick LeBeau, holding HC and DC simultaneously.** He was
  assistant HC/DC under Coslet, took over as HC after game 3, and kept calling
  the defence. Both slots carrying his name is correct and deliberate. A later
  pass must not "fix" it; the build script asserts it stays that way.

Arizona's staff box on Wikipedia shows the start-of-season staff, which is why
the first build had McGinnis at DC. That extraction was not wrong about what the
page said — see the `CONFIRMED` / `OVERRIDES` split in
`tools/build_coaches_2000.py`, which keeps the original check alive and records
the departure separately.

**One row follows the task doc over the source.** `WAS / OC` is Terry Robiskie,
which the doc's confirmed table gives as the OC. Wikipedia labels him "Pass game
coordinator" — Turner called the plays himself. The note records both.

**Namesake hazard, already live in this file.** `IND / HC` is Jim E. Mora and
`SF / DC` is Jim L. Mora, his son. Both rows carry a note pointing at the other.
Any lookup keyed on name alone will merge them — see the father-and-son
precedent in `docs/PGM3_PRECEDENTS.md`.

**Out of scope, unchanged:** scouts and physios. Whether the published files keep
generating them is Ryan's ruling and has not been made.
