# Task — finish the `.ros` decoder

Goal: read Madden `.ros` roster files on macOS without Windows and without
Xtreme DB Editor, extracting the `PLAY` and `COCH` tables to CSV. Add a small
GUI once the decoder works — the GUI is the easy part and should not be started
first.

Current state: `tools/rosdump.py` reads the container correctly and decodes
**47 of 108** numeric `PLAY` fields and **34 of 67** `COCH` fields exactly, every
record. The rest do not follow the same rule yet. That is the whole task.

---

## Ground truth is already in the repo

    sources/madden/2020ROJOROSTER_V22_-_PLAY.csv     3027 rows x 110 cols
    sources/madden/2020ROJOROSTER_V22_-_COCH.csv      218 rows x  68 cols

These were produced by Xtreme DB Editor from the matching `.ros`. **Ask Ryan for
`2020ROJOROSTER_V22.ros`** — it is not in the repo (binary, ~2MB; add it under
`sources/ros/` if you want it version-controlled).

Success condition is exact: every decoded value equals the CSV, for all records.
No tolerance, no eyeballing. Record *k* of the table corresponds to row *k* of
the CSV — that mapping is confirmed.

---

## What is established (do not re-derive)

**Container.** Verified on both `template.dbt` and a real `.ros`.

    0x00  "DB" magic
    0x10  uint32  table count
    0x18  directory, 8 bytes per entry: 4-char tag + uint32 offset,
          relative to the END of the directory (0x18 + count*8)

**Table header**, at the resolved offset:

    +0x00 uint32  hash
    +0x04 uint32  version (6 everywhere seen)
    +0x08 uint32  record length in BYTES
    +0x0c uint32  record length in BITS
    +0x14 uint16  allocated capacity
    +0x16 uint16  records actually used     <-- NOT 0x14, that is capacity
    +0x1c uint32  field count
    +0x30 field definitions, 16 bytes each:
              4-char tag, uint32 bits, uint32 type, uint32 bit offset

Verified against the CSVs: `PLAY` 3027 records / 110 fields / 104 bytes,
`COCH` 218 / 68 / 68. Field tags and bit widths are correct.

**Record data starts at `field_defs_end - 8`**, i.e.
`table_offset + 0x30 + field_count*16 - 8`. Confirmed independently for `PLAY`
and `COCH`. The -8 is not understood; it may be that the last field definition
is short, or that a small footer precedes the data. Worth understanding, but the
value is right.

**Bit order is MSB-first within each byte.** `numpy.unpackbits` gives the correct
bit stream directly.

**Records are packed at `record_bytes * 8` bits**, not `record_bits`. For `PLAY`
that is 832, not 831.

**Field definitions can be corrupt.** `2020ROJOROSTER_V22` contains a `PFEx`
entry with offset 1867645653. Skip any field where `offset + bits` exceeds the
record. `rosdump.py` already does.

---

## The open problem

The bit offset in the field definition is **close to but not exactly** the real
offset. Measured deltas (real minus header) for the fields that solve:

| delta | PLAY fields | COCH fields |
|---|---|---|
| -8 | 7 | 8 |
| -6 | 9 | 6 |
| -4 | 7 | 2 |
| -2 | 7 | 0 |
| 0 | 6 | 1 |
| +2 | 2 | 1 |
| +4 | 2 | 0 |
| +6 | 1 | 0 |

All even, all within ±8 bits — that is ±1 byte. The same shape appears in both
tables, so it is a property of the format, not of one file.

A handful of larger deltas (-553, -525, +304 and similar) are almost certainly
**false positives** on near-constant fields: `PFPB` is 99.9% zero and will match
at many offsets. Ignore anything outside ±8 until the main rule is found.

`reference/ros_solved_offsets.json` holds every solved field with its header
offset, real offset and width. Use it as the fixture — any hypothesis must
reproduce all of them.

### Hypotheses already ruled out

- **Consecutive packing** in header-offset order. 0 of 107 fields match, and the
  widths sum to 814 bits against a 832-bit record.
- **Whole-record byte swapping** at 2, 4 and 8-byte word sizes, swept against
  data-start offsets ±24. Best score 7 of 16 on a five-field probe.
- **LSB-first bit order**, alone and combined with the above.
- **A single constant delta.** The deltas genuinely vary field to field.

### Where to look next

The ±1 byte spread suggests **byte-level reordering inside a small window** —
16-bit or 32-bit words stored little-endian while the offsets are quoted in
big-endian bit space, or similar. The test is cheap: for each hypothesis,
transform the record buffer, then check all 47 known-good `PLAY` offsets at once.

Also worth checking: whether the delta correlates with `type` (0, 2 or 3 in the
field definition), with the byte the field starts in, or with whether the field
crosses a byte boundary. The type word does *not* separate strings from numbers
— `CLNA` and `PSKI` are both type 3 — so it currently means something else, and
that meaning may be the answer.

---

## Strings

Unsolved and treated separately. Physically the first name precedes the surname
and they are adjacent — "Robbie" then "Gould", "Patrick" then "Mahomes" — but the
field definitions put `PLNA` at bit 0 and `PFNA` at bit 136, which does not match
that layout. Solve the numeric fields first; strings will likely fall out of the
same rule.

---

## Independent confirmation worth knowing

The solve puts `PSKI` at bit 402 in this file. `docs/PGM3_PROJECT_HANDOFF.md`
records PSKI at bit 402 for the 2003-2008 and 2016-2025 files, derived years ago
by a different route. Two independent derivations agreeing is a good sign the
approach is sound.

Note the Xtreme template (`template.dbt`) puts PSKI at 613 — layouts differ by
game year, which is why the tool must read each file's own header rather than
hardcode anything.

---

## When it works

1. `python3 tools/rosdump.py dump FILE.ros PLAY -o out.csv` must reproduce the
   Xtreme CSV exactly. Diff it.
2. Test against a second file of a different era before trusting it —
   `sources/madden/` has exports from 2000 through 2025 and the layouts differ.
3. Then wire up `check`, which already implements the screening tests from
   `docs/PGM3_SOURCE_QUALITY.md` and is the real payoff: drop a new `.ros` on it
   and get a usable / unusable verdict in a second.
4. Only then add a GUI. Tkinter ships with Python; a file picker, two checkboxes
   and a Run button is enough.
