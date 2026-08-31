# 2000 build — the `HOU` slot

Replaces the "BLOCKING — needs a ruling" section of `PGM3_TASK_build_2000.md`.
Ruling made by Ryan, 2026-08-31.

---

## The decision

2000 had 31 teams. PGM3 needs 32 team IDs and every published file carries all
32, including 1986. The vacant slot is `HOU`.

**Ruling: fill `HOU` with the Houston Texans, arriving two years early.**

This is a smaller liberty than the 1986 precedent, which invented four franchise
identities. Here nothing is invented but the start date:

- NFL owners voted **29–0 on 6 October 1999** to award the 32nd franchise to Bob
  McNair for **$700 million**, beating a $540M Los Angeles bid.
- **Charley Casserly** was hired as EVP/GM on **19 January 2000** — 23 years with
  Washington, three Super Bowls.
- Through 2000 the club was tentatively "Houston NFL 2002", working a shortlist of
  Apollos, Bobcats, Stallions, Texans and Wildcatters. **The name was revealed on
  6 September 2000**, the week the season kicked off.

**There is no team-name field in the schema.** `teamID` is the only team column,
so `HOU` renders in game as the Houston Texans with no work at all. (This also
means 1986's "Baltimore Stars" never existed in the file — that name lived only
in the Reddit post. Same applies here: all naming is post copy, not data.)

---

## The construction rule — and why it exists

Accelerating the franchise by two years takes away the thing the real Texans
spent 2000 and 2001 building: **a scouting department.** The real club hired
fourteen scouts to prepare a board for the 2002 expansion draft.

So Casserly has a record checkbook, no expansion draft for two more years, no
draft picks, and no board. **A GM with no scouts signs what he can already
evaluate.** That means two groups:

1. **Men the Oilers drafted and the franchise left behind** — recent tape in this
   building, and the city's own.
2. **Men playing within a day's drive** — Texas colleges. Not because they are
   better, but because they are the only ones he has seen.

The lopsided roster is a *consequence* of the constraint, not a filter applied
for flavour. That distinction is the whole point — compare Kiffin's seven
defensive backs in 1986, which followed from the fact that no team leaves a pass
rusher unprotected.

### What the rule yields

Measured against the 694-player free agent pool:

- **14 ex-Oilers** — drafted by Houston, unsigned in 2000
- **49 Texas-college players**
- 3 overlap → **60 unique**, against a 53–54 man roster

Strength lands on its own: **median rating 68 against a league median of 71, and
exactly one player above 85.** Nobody has to weaken it.

### The shape it produced

| deep | thin |
|---|---|
| RB 7, DE 7, CB 7, S 6 | **WR 2, TE 2, OT 2** |

**Keep this.** Fill WR, TE and OT from the general free agent pool and let those
be the worst players on the roster. The positions Casserly could evaluate are
fine; the ones he could not are dire. Trim the surplus at RB/DE/CB/S rather than
trimming the shortage.

---

## The quarterbacks

**Andre Ware, QB, rating 72.** Heisman Trophy 1989 at the University of Houston,
first Black quarterback to win it. He and Jack Pardee arrived on campus the same
year and Pardee installed the run-and-shoot; Ware threw for 4,699 yards and 46
touchdowns as Houston averaged 53.5 points a game. Detroit took him 7th overall
and never played him — six starts in four years, with Fontes unable to choose
between Ware, Rodney Peete and Erik Kramer. Cut by the expansion Jaguars in 1995,
then the CFL, then Berlin in NFL Europe, where **his playing career ended after
the 1999 season.** Out of football, aged 32, living in Texas, in the exact year
Casserly is hiring.

He fits the rule rather than breaking it: no player in America is easier for a
Houston front office to evaluate.

**Erik Kramer, QB, rating 79.** One of the two men Detroit played ahead of Ware.
Signing both re-runs that competition ten years later in Ware's hometown, with
Ware getting the first look and Kramer the better player.

**Kramer is an explicit exception to the construction rule** — N.C. State, never
an Oiler. The stated why is the Detroit connection. Log it as an exception rather
than quietly widening the rule.

**Steve Young (96) and Dan Marino (88) are in the pool and are to be left there.**
Either would make Houston's quarterback the best or second-best in the league in
year one and destroy the premise. Neither had any reason to un-retire for an
expansion team.

---

## Head coach: Jerry Glanville

Out of the NFL since 1994, working in television. Three straight playoff teams
with the Oilers, House of Pain, the tickets for Elvis. A franchise that has just
paid $700 million for a city burned once before needs to sell season tickets
before it needs to win — this is a marketing hire and everyone involved knows it.

He is also already in `PGMStaff_1986.json` coaching Houston, so the two files
bookend: same man, same city, fourteen years and one franchise apart. **The face
registry should give him one face across both** — staff are keyed on name alone
and the whole appearance array is correct for them.

Coordinators and special teams need real coaches genuinely unemployed in 2000.
**Do not take Dom Capers (JAX DC), Chris Palmer (CLE HC) or Vic Fangio (IND DC)** —
the real first Texans staff are all employed elsewhere in `coaches_2000.csv` and
taking them strips a real team.

---

## Build notes and known defects

**The 60 are name-only matches. This is a bug until it is position-aware.** Both
joins key on normalised name alone against nflverse `draft_picks` and
`players.csv`. One false match is already confirmed — **Chris Miller** appeared as
a Baylor quarterback; the NFL Chris Miller went to Oregon. **Re-run the selection
with position-aware matching before building.** Expect the 60 to fall.

**The college filter must handle compound strings.** nflverse stores values like
`Houston; Alvin Community College`. An exact match drops them — that bug hid 10
players and nearly cost us Andre Ware, whose record reads `Houston; Alvin Co...`.
Split on `;` and test each token.

**Ages in the Madden file are stale for some players.** Ware reads 30 with 8 years
experience; born July 1968, he is 32 in September 2000. Prefer nflverse birth
dates where they exist.

**Exclude Derrick Thomas by hand.** He is in the free agent pool and died in
February 2000.

**Ratings above are post-rescale estimates**, from a per-position quantile map of
the 2000 rostered cohort onto the published 2004/2007/2021 union. Raw Madden
numbers are not usable — Greg Montgomery reads 98 raw and 81 rescaled, which is
the K/P inflation trap.

**Staff:** 9 records for `HOU`, same as every other team. Scouts and physios
generated per the standing ruling.

---

## For the Reddit post

Real anchors worth using, all verified:

- The $700M bid that beat Los Angeles, and the 29–0 vote
- The name arriving 6 September 2000, days before kickoff
- **The real ending: the Houston Texans did eventually hire Andre Ware — for the
  radio booth.** This gives him the job two years early and on the field.
- Ware and Kramer, the Detroit quarterback competition re-run
- Two wide receivers and two offensive tackles for a run-and-shoot Heisman winner

Note that Glanville and Ware never actually worked together — Glanville left the
Oilers after 1989, the season Ware won the Heisman across town. Ryan's call
(2026-08-31): this is fan fiction and the connection can be written as the post
likes. **The people and their records stay real; the narrative around them does
not have to be.** Same standing as Ron Meyer's invented press conference in the
1986 post.
