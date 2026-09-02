# PocketGM 3 historical rosters — working agreement

Ryan builds historically accurate NFL roster files for PocketGM 3, a mobile
football management sim. Seven seasons are published: 1986, 2004, 2007, 2010,
2013, 2017, 2021. The next build is 2000.

Read `docs/PGM3_PROJECT_HANDOFF.md` before touching any roster file. It is the
main reference. `docs/PGM3_PRECEDENTS.md` holds every ruling already made and
every documented failure — follow them or argue the case, but never quietly
diverge.

---

## Non-negotiables

**Never invent data when real data exists.** Search for it, ask for it, or say it
doesn't exist. Do not estimate and present it as fact. This is the first rule and
it has been broken more than once.

**Measure before explaining.** When a number looks anomalous, find the cause
before offering a reason for it. Plausible explanations offered ahead of a
measurement have been wrong every time they were checked.

**Find the real cohort before measuring anything.** Filler rows carrying
construction defaults dilute genuine correlations and have twice produced
confident, wrong conclusions.

**A correct marginal is the weakest evidence a derived field is right.** Matching
a distribution proves almost nothing. Check the joint structure — the relationship
between the derived field and its source, per position, against the published
files.

**Stop and ask for a ruling rather than guessing** when a convention is unclear.
Ryan verifies everything independently and corrects with specific measurements.
An honest "I don't know which convention applies" is always cheaper than a
confident wrong answer discovered three sessions later.

**The vanilla game export is the only authority on engine behaviour.** User-made
donor files are not authoritative, however plausible they look.

---

## Face registry — the rules that took a full session to learn

`reference/PGM3_FACE_REGISTRY.json` is applied last, over the top of everything.

**`_verified_keys` is LOCKED.** Anything Ryan set by hand in game — player or
coach, any season — is never overwritten by any automated pass, however well that
source scores. A pass that disagrees skips the key and logs the disagreement. This
rule exists because an automated pass with a perfect anchor score destroyed a
hand-set face, and the one edit carrying the most human judgement was the one it
destroyed.

**Apply the family digit, never the whole face.** Slots 0, 5 and 6 carry a family
digit and a variant letter. The variant is derived from age and weight and
*legitimately differs between seasons* — players age. Writing the registry array
wholesale flattens that. Rewrite the digit, keep the season's own letter.

**Staff are the exception.** Coaches have exactly one look with no aging, so the
whole array is correct for them and wrong for players.

**Rebuild every season the registry touches**, not just the ones in front of you,
or players end up inconsistent either side of the boundary.

**Provenance follows who decided, not what surfaced it.** An automated diff that
finds a hand edit did not make that edit.

---

## Sources — score before trusting

`docs/PGM3_SOURCE_QUALITY.md` carries the scored table. The short version:

- **Seven of seventeen Madden CSVs carry no usable skin signal**, including
  `2003`, `2004` and `2013`, which had previously been treated as good.
- **Provenance does not predict quality.** Fan-made JINX files beat three
  year-named EA-derived ones.
- **The `PSKI` middle value carries no information** — measured at 49% dark.
  Abstain on it. Forcing it to one side created an apparent source bias that led
  to three separate workarounds for a problem that did not exist.
- **Source quality is per field, not per file.** Files whose skin field collapsed
  still carry usable hair colour.
- **Weight by lineage, not file count.** Files descending from each other share
  their errors; four agreeing JINX files is one vote.

Before using a new source file: print the `PSKI` distribution, check the middle
value is under ~28%, then anchor-test it against known players. Report the dark
share alongside the AUC — a file can rank correctly and still be miscalibrated.

---

## Known recurring bugs

- `PSTM` vs `PSTA` — stamina. Wrong one gives a plausible distribution and zero
  per-player signal. That silence is the tell.
- `PCYL` is contract years **remaining**; `PCON` is total length. Taking `PCON`
  at face value has shipped wrong contracts before.
- `PSBO` is the full signing bonus, not the remainder. Prorate:
  `PSBO × length / PCON`.
- `injuryProne` targets: rostered ~52, FA ~49, rookie ~34. Published files once
  had this inverted.
- Madden attributes need per-position quantile mapping, not direct copy.
- `norm()` must fold accented characters to ASCII, not strip them.
- Any lookup keyed on name alone is a bug until it is position-aware — and
  position-adjacency merges fathers and sons. Use the era test on rostered
  seasons.
- Pin GitHub fetches to a commit SHA. Six incidents of reporting findings from a
  stale file.

---

## Before any push

    python3 tools/pgm3_validate.py roster NEW.json REF1.json REF2.json
    python3 tools/pgm3_validate.py faces PGMRoster_*.json
    python3 tools/pgm3_validate.py conditional NEW.json SRC.csv FIELD SRC_FIELD

All three. The `faces` pass takes a whole season set and catches the cross-file
bugs a single-file check cannot see. It found 14 overwritten hand edits in
seconds that had previously been found by accident, days later.

Assertions belong on every write, including the small ones. The only wrong write
in the session that produced this document was two rows long, and an assertion
was the only thing that caught it.

---

## Layout

    PGMRoster_YYYY.json     published rosters, repo root
    PGMStaff_YYYY.json      published staff, repo root
    docs/                   handoff, precedents, source quality, vocabularies
    reference/              face registry, schema, vanilla sample, change log
    $PGM3_SOURCES/          NOT IN THE REPO — see below
      madden/               Xtreme DB Editor CSV exports, 2000-2025
      photos/               measured.csv — NFL headshot pixel measurements
      1986/                 1986 build intermediates
    tools/                  pgm3_validate.py
    wip/                    in-progress build data

---

## `sources/` is NOT in the repo

**Removed 2026-09-02 by Ryan's ruling. Nothing was deleted.** The tree holds
third-party community files — Madden and 2K5 roster mods, Nza's Editor draft
classes, cached pages from other people's sites. They are inputs, not our work,
and committing them republished someone else's material under this repo's name.
Kept on disk and backed up; `sources/` is gitignored so it cannot return by
accident. The files remain in git history deliberately — rewriting a published
branch breaks every clone for a harm that does not warrant it.

**Resolve it through `tools/pgm3_paths.py`, never a literal path:**

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import sources, require, repo

glob.glob(sources('1979footballdb', '*.txt'))   # input
open(require('coach_birth_years.csv'))          # input; failure names the fix
open(repo('wip', 'out.csv'), 'w')               # OUTPUT — see the trap
```

`PGM3_SOURCES` if set, else `../pgm3-sources` beside the repo root.

**The trap, found during the move.** The old hardcoded `'sources/...'` strings
only worked when a tool ran from the repo root. Routing inputs through
`sources()` made the tools runnable from anywhere — so a bare
`open('wip/out.csv','w')` began writing wherever the caller stood. Running
`build_1979_roster.py` from `/tmp` created `/tmp/wip/`. **Fixing one side of a
path problem exposed the other.** Outputs go through `repo()`.

## How the work is split

**Master session (Claude chat):** review, rulings, cross-file QC, method. Produces
decisions, not files. Cannot push to this repo.

**Build session (Claude Code):** construction, validator runs, doc updates,
commits. Inherits the rulings through this file and `docs/`.

When the master session settles something, it belongs in `docs/PGM3_PRECEDENTS.md`
before the session ends. Several findings in this repo existed only inside a
conversation for hours and were nearly lost.
