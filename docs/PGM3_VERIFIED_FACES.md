# Hand-verified faces — how to record and protect them

## What they are

Faces the project owner set **by hand, in game, against photographs**. They are the
highest-confidence appearance data in the project, and the **only real hair-style and
facial-hair data that exists anywhere in it** — every other player's hair style and beard
are assigned from a distribution, not sourced.

As of 2026-08-31 there are **78, all players, all 1986**. No staff have been hand-verified
yet.

## Where they live

`PGM3_FACE_REGISTRY.json` has two blocks for this:

- **`_verified`** — a plain-language note explaining the rule
- **`_verified_keys`** — the actual list, split into `players` and `staff`

```json
"_verified_keys": {
  "players": {
    "mike richardson|CB|CHI": {
      "season": 1986,
      "batch": "2026-08-30 batch 1",
      "fields": "skin, hair colour, hair style, facial hair"
    }
  },
  "staff": {}
}
```

Player keys are `name|position|teamID`, normalised the same way as the rest of the
registry. Staff keys are `name` alone, matching the `staff_faces` convention.

The face itself stays in whichever block it belongs to — `faces_1986` for a 1986 player,
`faces` for a modern one. `_verified_keys` is a pointer, not a copy, so there is one
source of truth for the appearance and no chance of the two drifting apart.

## The rule

**Any pass that assigns appearance must skip keys listed in `_verified_keys`.**

```python
verified = set(registry['_verified_keys']['players'])
...
key = f"{nrm(name)}|{position}|{teamID}"
if key in verified:
    continue          # hand-set from a photograph; do not touch
```

This matters more than it looks. The 1986 skin rebuild rewrote 1,440 players in one pass.
Without this guard, the next such rebuild silently destroys work that cannot be
reconstructed from any file or database.

## Recording a new batch

When the owner sends an edited save:

1. Diff the save's `appearance` against the current file, **matching on
   name + position + teamID**, and list what changed. Show him the list before applying —
   it is how he confirms the right players were picked up.
2. Apply **only** the `appearance` field. Saves carry extra generated records and
   in-game rating changes; taking a save wholesale imports both.
3. Add each changed key to `_verified_keys.players` (or `.staff`) with the season, a
   batch label, and which fields he actually checked.
4. Re-run the validator. Confirm positionally that nothing but `appearance` moved —
   compare index to index, not by a name-keyed dictionary, because duplicate names
   collapse and the diff will lie to you.

## Batches so far

| batch | n | what |
|---|---|---|
| 2026-08-30 batch 1 | 21 | league leaders — Payton, Rice, Lott, Munoz, Reggie White |
| 2026-08-31 quarterbacks | 42 | every QB in the league, Montana down to Flutie |
| 2026-08-31 batch 3 | 15 | running backs plus Lawrence Taylor, Bruce Smith, Howie Long |

## Why the coach block is empty

Coach appearance came from a separate research pass (402 coaches, skin and hair) plus a
decoded `COCH` field, not from hand editing. If the owner ever edits staff faces in game,
they go in `_verified_keys.staff` keyed on name alone.

---

## `_verified_keys` vs `_labelled_keys`

Updated 2026-08-31 (twice — see the incident at the end). The registry carries
**two** protection blocks and they mean different things.

### `_verified_keys` — LOCKED

Faces Ryan set **by hand, in game**. The highest-confidence data in the project.

**Ruling, 2026-08-31: anything Ryan hand-edits — player or coach, any season — is
verified and must never be overwritten by an automated pass, however well that
source scores.** A pass that disagrees with a verified key skips it and logs the
disagreement. It does not win. There is no source good enough to outrank a person
looking at the render.

Currently 84 players: 78 from the 1986 photo batch, plus the 6 edited in game on
2026-08-31 (Tony Gonzalez, Ray Lewis, Terrell Owens, Randy Moss, Orlando Pace,
Walter Jones). Staff: 0 so far, and the same rule applies the moment there is one.

Note these entries carry the **whole** appearance array, not just skin. Ryan's
2004 edits changed hair and beard on some players too.

### `_labelled_keys` — overwritable

Skin families reassigned from a measured or recalled source, never checked in
game. Better than what they replaced; a better source **should** overwrite them.
Currently 1,075 entries across five batches:

| batch | count | basis |
|---|---|---|
| `abstention-corrected cross-file vote` | 361 | 98.4% on 127 anchors |
| `EA-2005-2008 consensus skin pass` | ~590 | AUC 1.000 on 83 anchors |
| `top-405 skin relabel` | ~96 | Claude recall, unverified |
| `EA consensus via position-drift recovery` | 29 | EA source via a position change |
| `coach skin audit` | 0 | audit found no errors |

Only slots 0, 5 and 6 were touched in the labelled batches.

### The incident that produced the ruling

The six in-game edits were originally filed as **labelled**, with an explicit
note that a better source should overwrite them. The EA consensus pass then ran,
counted as a better source, and overwrote **Tony Gonzalez** — replacing the
`Head3b` Ryan had set by hand with `Head4c`.

The other five survived only because EA happened to agree with them. Gonzalez did
not, because he is of mixed heritage and a binary light/dark source cannot
express the family-3 call Ryan made by eye.

It was caught by accident, days of work later, while checking something else.

**The lesson is about filing, not scoring.** An automated diff *found* those
edits; Ryan *made* them. Provenance follows who made the decision, not which
process surfaced it.
