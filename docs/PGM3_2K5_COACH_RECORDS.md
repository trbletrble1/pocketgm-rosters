# NFL 2K5 coach records — what's in them, and why we can't read them yet

Written 2026-09-01, after the player side was decoded and indexed. Nothing here
is blocking. This exists so nobody re-derives it from scratch.

**Short version:** coaches carry no skin data, so the player archive cannot help
with coach faces. But they DO carry full career records, which is the input that
cost most of a session on the 2000 build. We know the field layout and we cannot
yet locate the records.

---

## Coaches have no appearance data

The whole appearance side of a 2K5 coach is one field:

    Photo = 0x40      a portrait ID, not a parametric face

There is no `Skin`, no `Face`, no `Dreads`, no `BodyType`. Players have all
four. `CoachEditForm.cs` confirms it — the only appearance control it offers is
a face picker that writes `Photo`.

**So `reference/PGM3_PLAYER_ARCHIVE.json` covers players only.** Coach faces stay
where they are: Ryan's `_verified_keys.staff` entries, plus whatever gets
confirmed in game. Do not go looking for a coach skin source in these files.

---

## They do carry career records, and that matters

From `EnumDefinitions.cs`, `enum CoachOffsets`. All offsets are from the start
of the coach record. The win/loss fields are 16-bit little-endian.

    FirstName        0x00    pointer to the name string, not the string
    LastName         0x04    pointer
    Body             0x18
    SeasonsWithTeam  0x1C
    totalSeasons     0x1E
    Wins             0x20
    Losses           0x22
    Ties             0x24
    WinningSeasons   0x30
    SuperBowls       0x32
    PlayoffWins      0x34
    PlayoffLosses    0x36
    SuperBowlWins    0x38
    SuperBowlLosses  0x3A
    Photo            0x40
    Overall          0x42    then per-unit and per-position ratings to 0x58
    PlaycallingRun   0x59    then play tendencies to 0x8C

**Why this is worth having.** The 2000 build needed career records through 1999
for 31 head coaches. Getting them took a Wikidata query, a research prompt built
around self-checking constraints, and a round trip through another AI — because
every public source gives *lifetime* totals and the 2000 season had to be
subtracted back out. Pro Football Reference's own season index gives Andy Reid
279 wins on a page dated 1999, when he had 5.

**A 1986-87 roster's coach records hold those figures as of 1986.** No
subtraction, no lifetime-totals trap, no hindsight. Same for every other season
in the set, which now runs 1958 to 2026.

That would remove the single most expensive manual input from any historical
build.

---

## Why we can't read them yet

The player table was found by scanning for where names decode as ASCII text.
**That trick does not transfer**, because a coach record starts with a *pointer*
to its name rather than the name itself. There is nothing to scan for.

The tool locates them with a two-step chain:

    coachPointer = m49ersPlayerPointersStart + 0x14c + teamIndex * 0x1f4
    coachRecord  = GetPointerDestination(coachPointer)

and its two documented configurations are:

    roster     player pointers 0x41c8    player data 0xAFA8
    franchise  player pointers 0x44a8    player data 0xB288

Both have a constant gap of **0x6DE0** between the pointer table and the player
data, which looked like a way to derive the pointer base from the player start
we already scan for.

**Three attempts, all zero of thirty-two readable:**

1. The documented bases 0x44a8 and 0x41c8 directly
2. A scan of 0x2000-0x9000 for a base where six consecutive coach records decode
   plausible names. Best score was 2/6 at 0x4b74, and inspection showed it had
   found the **team name table** — "Kansas City KC", "Indianapolis IND" — with
   year-like garbage in the numeric fields
3. Deriving the base as `player_start - 0x6DE0`. This failed even on a file whose
   player start is exactly the documented 0xAFA8, which is the result that says
   the assumption is wrong rather than the arithmetic

**The most likely explanation** is that `teamIndex` in `GetCoachPointer` is not a
sequential 0-31. The tool has a `GetTeamIndex(team)` lookup and a
`sTeamsDataOrder` array it uses everywhere else, and the player-pointer code
paths use them. Reading those properly is the obvious next thing to try.

Second candidate: these community files may move the pointer table the same way
they move the player table, in which case the 0x6DE0 gap is a property of stock
saves and not of modded ones.

---

## If you pick this up

Start from `GamesaveTool.cs`, `GetCoachPointer` at line 184, and follow
`m49ersPlayerPointersStart`, `GetTeamIndex` and `sTeamsDataOrder`. The source is
cloned from `github.com/BAD-AL/NFL2K5Tool`; everything about the player format
came out of it and nothing had to be reverse-engineered.

**Validate the same way the player side was validated.** Read a season we
already hold coach data for — 2000 is the obvious one, since
`sources/coaches_2000_HC_career_through_1999.csv` has verified career records for
all 31 head coaches — and check the file's figures against it. If a 1999-2000
roster reproduces Reid at 5-11 and Cowher at 77-51, the chain is right.

Do not trust it on a season we cannot check.
