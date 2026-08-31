# Task: resolve the face registry's position splits

**For:** a build session, whenever all five files are next being regenerated.
**Not urgent.** This is already how the published files look, so it isn't a regression. Don't re-push five files for this alone.

**Files you need:** `PGM3_FACE_REGISTRY.json`, `PGM3_FACE_REGISTRY_SPLITS.json` (the worklist, generated from the registry), and the five published rosters.

---

## The problem

The registry keys players on `"normalized name|position"`. That key splits anyone who changed position between seasons into two entries with two different faces — which is the exact thing the registry exists to prevent. Karlos Dansby is `OLB` in one file and `MLB` in another and gets a different face for each. So do Darnell Dockett, Keith Brooking, Leonard Davis and Roberto Garza.

262 names are affected.

The key can't simply be changed to name alone. It is doing real work: Alex Smith the 2005 quarterback and Alex Smith the tight end are two people, and so are Derrick Johnson the linebacker and Derrick Johnson the corner. Merging on name would hand one of them the other's face.

So each of the 262 has to be resolved individually: one player who changed position, or two people who share a name.

---

## The test that decides it

**Do both entries appear in the same published file?**

- **Yes → two different people.** One man cannot hold two positions in one season. Leave the entry split. Nothing to do.
- **No, they appear only in different files → one player who changed position.** Merge to a single face.

This is the decisive test. Use it on every row.

`PGM3_FACE_REGISTRY_SPLITS.json` carries a `guess` field marking rows as `same-person` or `check-namesake`, based only on whether the two positions are adjacent (OLB/MLB) or distant (DT/QB). **That guess is a convenience for ordering the work, not evidence.** It was produced without looking at the rosters. Run the same-file test on every row regardless of what the guess says, including the 215 it calls obvious.

Two known traps from the handoff, both of which the same-file test handles correctly:

- Real position changes across years are common and legitimate — Julius Peppers DE→OLB, Dan Klecko DT→FB, Lorenzo Alexander LB→DT. Don't treat a position change as a data error.
- Real namesakes exist at adjacent positions too, so a `same-person` guess is not a licence to skip the check.

---

## When merging, which face wins

Use the registry's existing priority order, unchanged:

1. Ryan's in-game export (his hand edits — these always win)
2. 2004
3. 2007
4. 2013
5. 2010
6. 2017

Keep the face from the highest-priority source the player appears in, and write it to every position key for that name. **Never pick by which face looks better.** If a hand edit is involved anywhere in the row, it wins outright.

---

## How to store the result

Keep the `name|position` key. Don't restructure the registry — other things depend on the key shape, and a namesake split still needs it.

For a merged player, write the same face array to every one of his position keys. The registry then has redundant entries that agree, which is harmless and keeps lookups working whichever position a given season lists him at.

---

## Also fix while you're in there

The registry's `_scope` field says 5,070 players. There are 5,693 distinct names and 6,008 keys. Update the line to match what's actually in the file.

---

## Definition of done

- Every one of the 262 rows resolved by the same-file test, not by the guess field
- Merged players carry one identical face across all their position keys
- Namesakes left split, and a short list of which ones you left split and why
- `_scope` corrected
- Registry re-validated: appearance family rules (slots 0/5/6 share a digit, 2/3/4 share theirs), no player wearing glasses. It passes both cleanly today at 6,546 faces — don't regress it

---

## Known and accepted, not part of this task

`staff_faces` is keyed on name alone, deliberately, because coaches change role between years. That means two staff sharing a name would collide silently and one would take the other's face. No instance is known. Leave it. Raise it if one turns up.
