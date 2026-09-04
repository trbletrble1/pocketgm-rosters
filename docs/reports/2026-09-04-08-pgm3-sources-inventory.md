# `pgm3-sources` inventory

**2026-09-04. Report 08.** Requested because neither Ryan nor the master session
can see this tree, and both were tracking its contents from memory. **That is the
failure `relayed` exists to prevent (§3.7), one level up** — a directory listing
held in conversation is exactly as unreliable as a figure held in conversation,
and today produced two wrong statements about the repo before this was noticed.

    root      ~/Documents/pgm3-sources      (resolved as $PGM3_SOURCES, or
                                             ../pgm3-sources beside the repo)
    entries   35
    files     26,834
    size      476 MB
    status    NOT in the repo, gitignored, by Ryan's 2026-09-02 ruling

## Everything in it

"Referenced" means the literal name, or a sample filename from inside the
directory, appears somewhere in the repo's `.md` or `.py` files. **It is a
string match, so read it as a lower bound** — see the caveat below.

| entry | kind | files | size | newest | referenced |
|---|---|---|---|---|---|
| `1976madden` | dir | 1 | 2M | 2026-09-03 | **NO** |
| `1977footballdb` | dir | 0 | 0B | - | **NO** |
| `1978footballdb` | dir | 28 | 48K | 2026-09-02 | yes |
| `1979PFR` | dir | 78 | 45M | 2026-09-03 | yes |
| `1979footballdb` | dir | 28 | 51K | 2026-09-02 | yes |
| `1979madden` | dir | 2 | 4M | 2026-09-02 | yes (`1979-SB-XIV`) |
| `1983madden` | dir | 1 | 2M | 2026-09-02 | yes (`1983-SB-XVIII`) |
| `1986` | dir | 3 | 345K | 2026-08-31 | yes |
| `1986madden` | dir | 1 | 2M | 2026-09-02 | yes (`1986_Roster_Mod_v1.0`) |
| `1990madden` | dir | 1 | 2M | 2026-09-02 | yes (`1990-SB-XXV`) |
| `385388545-NFL-Economics-Primer-April-2002.pdf` | file | 1 | 5M | 2026-09-04 | yes |
| `385388545-NFL-Economics-Primer-April-2002.txt` | file | 1 | 313K | 2026-09-04 | yes |
| `Big_Spring_Herald_1982_02_24.pdf` | file | 1 | 47M | 2026-09-04 | yes |
| `Midland_Reporter_Telegram_1979_02_10.pdf` | file | 1 | 49M | 2026-09-04 | yes |
| `Midland_Reporter_Telegram_1982_02_24.pdf` | file | 1 | 62M | 2026-09-04 | yes |
| `NFL2k25 Year Saves` | dir | 42 | 24M | 2026-09-02 | yes |
| `README.md` | file | 1 | 8K | 2026-08-31 | yes |
| `coach_birth_years.csv` | file | 1 | 25K | 2026-08-31 | yes |
| `coach_birth_years_2026.csv` | file | 1 | 8K | 2026-09-02 | yes |
| `coaches_2000.csv` | file | 1 | 13K | 2026-08-31 | yes |
| `coaches_2000_HC.csv` | file | 1 | 1K | 2026-08-31 | yes |
| `coaches_2000_HC_career_through_1999.csv` | file | 1 | 3K | 2026-08-31 | yes |
| `coaches_2000_birth_years.csv` | file | 1 | 10K | 2026-08-31 | yes |
| `coachingtree` | dir | 136 | 319K | 2026-09-04 | yes |
| `hearings` | dir | 2 | 19M | 2026-09-04 | yes |
| `madden` | dir | 25 | 24M | 2026-09-02 | yes |
| `mdc_draft_classes` | dir | 30 | 1M | 2026-09-02 | yes |
| `mike` | dir | 10 | 21M | 2026-09-02 | yes |
| `nfl-books` | dir | 29 | 9M | 2026-09-04 | weak (`index`) |
| `nflverse` | dir | 1 | 7M | 2026-08-31 | yes |
| `photos` | dir | 26,146 | 95M | 2026-08-31 | yes |
| `ros` | dir | 18 | 37M | 2026-08-31 | weak (`2005`) |
| `staff_2026_promotions.csv` | file | 1 | 168B | 2026-09-02 | yes |
| `statscrew` | dir | 234 | 9M | 2026-09-04 | yes |
| `vanilla` | dir | 5 | 8M | 2026-09-03 | yes |

## What needs attention

**`1977footballdb` is EMPTY.** Zero files, created 2026-09-02. The 1978 and 1979
equivalents each hold 28 cached roster pages; this one holds nothing. Either a
fetch that was started and abandoned, or a directory made in anticipation. **It
reads as a cached source and is not one** — the most dangerous shape in the tree,
because a build resolving `sources('1977footballdb', '*.txt')` gets an empty glob
rather than an error.

**`1976madden` — `1976_raidermike.ros`, 2.1 MB, added 2026-09-03, referenced
nowhere.** Every other `*madden` directory is discussed in
`PGM3_AUDIT_BACKLOG.md`: `1979-SB-XIV`, `1983-SB-XVIII`, `1990-SB-XXV`,
`1986_Roster_Mod_v1.0` all appear with an evaluation. This one has never been
scored, and per the standing rule a source is scored before it is trusted. **It
may be the oldest `.ros` in the collection and nobody has looked at it.**

**`coachingtree` — 136 JSON files, referenced nowhere by path.** The Coaching Tree
MCP is described in `DATASET_DESIGN.md`, but the cached responses are not, so a
session reading the docs would not know a local cache exists and would re-query
the service. **And these files carry something that turned out to matter today** —
see below.

## The coachingtree cache disagrees with StatsCrew on a birth date

Found while inspecting a sample file for this inventory, on the person §2.4 uses
as its worked example:

| | StatsCrew `c-allengeo001` | `coachingtree/` cache |
|---|---|---|
| birth date | **April 29, 1922** | **1918-04-29** |
| college | Marquette | Alma |
| career span | 1966–1984 | 1957–1984 |

Same day and month, **four years apart on the year**. George Allen's birth year is
genuinely disputed in the historical record, and he is reported to have attended
both colleges — so the college row may be two true facts and the birth-year row a
real conflict.

**Why it matters beyond one man.** §9.2 has just established that birth date is
present in ≥96% of every league-year sampled. **Presence is not agreement.** A
contested birth date is a contested *discriminator*, and a denotation resting on
it inherits that — so a denotation must record **which source's birth date it
matched against**, not merely that it matched one. Written into §9.1.

The career-span row is incidental corroboration of an earlier finding from a
second source: 1966–1984 against 1957–1984 is StatsCrew's `c-` namespace holding
head-coaching years only.

## The instrument contaminated its own measurement

Worth recording, because it took two runs to notice. The first regeneration of
this table — after report 08 had been drafted — returned **zero** unreferenced
entries, because **this report names the unreferenced entries in order to flag
them**, and the matcher then found them in the corpus.

The check now **excludes any file with `inventory` in its name** from the corpus
it searches. Without that, the report certifies the tree as fully referenced on
every run after the first, and does so more confidently the more thorough it was.

Same family as the roster project's *"a widened check reports its own reach errors
as findings"* and *"an assertion that cannot fail reports success"* — a measurement
that includes its own output in its input will converge on a clean result
regardless of the truth. **Any future regeneration must keep the exclusion.**

## Caveat on the "referenced" column

The check is a **string match** against the repo's `.md` and `.py` files, testing
the entry name and up to six sample filenames from inside each directory. It
therefore:

- **under-detects** anything referred to descriptively. `nfl-books` is used
  throughout report 01 as "the 1979 media guides" and matched only on the weak
  token `index`.
- **over-detects** on common tokens. `mike`, `1986`, `2005`, `index` and
  `madden` are flagged `weak` above because a match on those proves nothing.

Entries marked `yes` on a full filename are solid. **Treat `weak` and `NO`
together as the list worth a human eye**, which is seven entries.

## Recommendation

1. **Delete or fill `1977footballdb`.** An empty directory that looks like a
   cached source is worse than an absent one.
2. **Score `1976_raidermike.ros`** the way every other mod was scored, or record
   why it was set aside. Right now it is neither.
3. **Document the `coachingtree` cache** in the design's source list, with the
   birth-date conflict attached.
4. **Regenerate this inventory whenever a source lands**, rather than describing
   the tree in conversation.
