# 2017 Build — Week 1 Team Assignment Fallback

These 24 players appeared on more than one 2017 roster and could NOT have their
Week 1 team determined from a source. Madden 18's team field is a preseason snapshot
and resolved 45 of the 69 multi-roster players; these 24 were cut during camp, so
Madden lists them on a third team they never played for (or omits them entirely).

The JINX 2017 roster was tested and rejected as a source: it is an END-OF-SEASON
snapshot. Verified against five unambiguous in-season moves — Garoppolo (SF),
Duane Brown (SEA), Kelvin Benjamin (BUF), Jay Ajayi (PHI), Adrian Peterson (ARI) —
all five resolved to the player's final team, not his Week 1 team.

**Rule applied:** assigned to whichever team they played the most games for.
This is known to be wrong for an unknown subset. Accepted deliberately: all 24 are
deep-roster/practice-squad churn on a 2,010-player file, and per-player lookups were
not a good use of build effort. Documented rather than fixed — same posture as the
~190 players without EA appearance data in the 2010 build.

**Roster-limit interaction:** 6 of the 24 land on teams above the 69 cap. Only ONE
is caused by this choice — Jermaine Grace takes Indianapolis from 69 to 70. The
Giants (74), Texans (74) and Washington (72) exceed 69 regardless and need trimming
anyway.

| Player | Pos | Born | Assigned | Candidates (games) | Madden 18 team |
|---|---|---|---|---|---|
| Ahtyba Rubin | DT | 7/25/1986 | Atlanta Falcons | Atlanta Falcons (10), Denver Broncos (2) | Seahawks |
| Andy Jones | WR | 6/28/1994 | Detroit Lions | Detroit Lions (2), Houston Texans (1) | Cowboys |
| Ayodeji Olatoye | DB | 7/20/1991 | Tampa Bay Buccaneers | Tampa Bay Buccaneers (3), Atlanta Falcons (2) | — |
| Cassius Marsh | DE | 7/7/1992 | New England Patriots | New England Patriots (9), San Francisco 49ers (6) | Seahawks |
| Datone Jones | DE | 7/24/1990 | Dallas Cowboys | Dallas Cowboys (4), San Francisco 49ers (3) | Vikings |
| Dexter McDougle | DB | 4/8/1991 | Philadelphia Eagles | Philadelphia Eagles (8), New Orleans Saints (1) | Jets |
| Dwight Freeney | DE | 2/19/1980 | Detroit Lions | Detroit Lions (5), Seattle Seahawks (4) | — |
| George Johnson | DE | 12/11/1987 | Detroit Lions | Detroit Lions (4), New Orleans Saints (3) | Buccaneers |
| Greg Mabin | DB | 6/25/1994 | San Francisco 49ers | San Francisco 49ers (6), Buffalo Bills (1) | — |
| Hunter Sharp | WR | 4/25/1994 | New York Giants | New York Giants (2), Denver Broncos (1) | — |
| Jermaine Grace | LB | 11/8/1993 | Indianapolis Colts | Indianapolis Colts (6), Atlanta Falcons (5) | — |
| Josh Keyes | LB | 1/23/1993 | Cleveland Browns | Cleveland Browns (8), Los Angeles Chargers (2) | Falcons |
| Justin March | LB | 7/5/1993 | Dallas Cowboys | Dallas Cowboys (7), Miami Dolphins (2), Seattle Seahawks (1) | — |
| Kalif Raymond | WR | 8/8/1994 | New York Giants | New York Giants (6), New York Jets (2) | Broncos |
| Lafayette Pitts | DB | 9/24/1992 | Buffalo Bills | Buffalo Bills (10), Jacksonville Jaguars (6) | Dolphins |
| Marcus Williams | DB | 3/24/1991 | Houston Texans | Houston Texans (10), New York Jets (5) | — |
| Mike Nugent | K | 3/2/1982 | Chicago Bears | Chicago Bears (4), Dallas Cowboys (4) | — |
| Nick Rose | K | 5/5/1994 | Washington Redskins | Washington Redskins (8), Los Angeles Chargers (2) | — |
| Nigel Harris | LB | 12/7/1994 | Los Angeles Chargers | Los Angeles Chargers (5), New York Giants (2), Tampa Bay Buccaneers (1) | — |
| Nordly Capi | DE | 7/11/1992 | Buffalo Bills | Buffalo Bills (4), New York Giants (4) | — |
| Tony Bergstrom | T | 8/8/1986 | Washington Redskins | Washington Redskins (9), Baltimore Ravens (4) | Cardinals |
| Tony McRae | DB | 5/3/1993 | Baltimore Ravens | Baltimore Ravens (5), Cincinnati Bengals (4) | — |
| Travaris Cadet | RB | 2/1/1989 | Buffalo Bills | Buffalo Bills (6), New York Jets (3) | Saints |
| Xavier Cooper | DT | 11/30/1991 | New York Jets | New York Jets (8), San Francisco 49ers (5) | Browns |

---

# Known limit 2 — renamed players not recoverable

PFR displays players under their CURRENT name; Madden 18 used their 2017 name.
Three were recovered by a surname + PGM3 position + team key, requiring a unique
match and rejecting any Madden record already claimed by an exact-name match:

| PFR name | Madden 18 name | Pos | Team | Ovr |
|---|---|---|---|---|
| Lano Hill | Delano Hill | S | Seattle Seahawks | 68 |
| Evander Hood | Ziggy Hood | DT | Washington Redskins | 72 |
| Jackrabbit Jenkins | Janoris Jenkins | CB | New York Giants | 89 |

**One match was rejected**: Chris Johnson -> David Johnson (RB, Arizona, 94). Both
were 2017 Arizona running backs. This is the exact failure mode the surname rule is
vulnerable to — same surname, same position, same roster. David Johnson had already
matched by exact name; Chris Johnson has no Madden 18 record and fell to a derived
rating. Any future use of a surname key MUST reject targets already claimed.

**Not recoverable**: players whose SURNAME changed, e.g. Robby Anderson (Madden 18)
is listed by PFR as Robbie Chosen. No surname key can reach these. They fall to a
derived rating and are slightly under-rated as a result. Count unknown; at least one.

# Known limit 3 — attribute scale

Player attributes sit on PGM3's internal scale, matched to the distributions in
PGMRoster2025-06-12_3 because weights.json was fitted against that file. They will
NOT look like Madden ratings and should not be read as such. A lineman's `vision`
of ~77 is normal in PGM3 and means nothing like Madden's Ball Carrier Vision.

# Known limit 4 — the 2010 file

PGMRoster_2010.json has a milder version of the attribute-mapping problem found
here: `vision` averages 51 for tackles against the donor's 77, and `releaseLine` 38
against 79. The file plays correctly and is NOT being changed. Recorded so nobody
later mistakes those values for a correct mapping.
