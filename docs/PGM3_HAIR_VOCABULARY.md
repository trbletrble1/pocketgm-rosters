# PGM3 — Hair style vocabulary, observed

Established 2026-08-31. Ryan set one known player to each of the twenty hair
tokens in the 2004 file, screenshotted the game's render, and the tokens were
read off those images.

**This replaces the list in `PGM3_PROJECT_HANDOFF.md`, which was wrong on most
entries.** That list came from cycling the editor and inferring labels from
position in the cycle. Only three tokens had ever been anchored against a known
player — `j`, `m` and `h` — and those three are the ones that survived contact
with the screenshots.

---

## The vocabulary

Token is the suffix on `Hair{family}{token}`. The family digit is hair **colour**
(0 black, 1 blond, 2 brown, 3 red, 4 light brown), unrelated to style.

| token | what it renders as | doc previously said |
|---|---|---|
| `a` | short tapered crop, slight length on top | buzz |
| `b` | medium wavy, messy, over the ears | tousled ✓ |
| `c` | short spiky quiff, shaved sides | long swept |
| `d` | short flat crop, sharp hairline | messy |
| `e` | medium, swept back | short |
| `f` | long shaggy, layered, covers ears | receding |
| `g` | short spiky, textured on top | thin |
| `h` | short buzz, rounded hairline | buzz short ✓ |
| `i` | very short, receding at the temples | near bald ✓ |
| `j` | **fully bald, no stubble** | bald ✓ |
| `k` | **horseshoe — bald crown, hair at the sides** | short twists |
| `l` | **shaved head with faint stubble** | fade |
| `m` | short dreads or twists, standing up | braids ✓ |
| `n` | very short textured crop, sharp line | short curly |
| `o` | **cornrows, braids hanging behind** | afro |
| `p` | **short afro / high-top fade** | long dreadlocks |
| `q` | **tall curly afro** | cornrows |
| `r1` | **long dreadlocks** | slicked |
| `r2` | **long dreadlocks** (near-identical to `r1`) | medium wavy |
| `s` | **cornrows with visible parts** | spiky |

Reference players used, all from the 2004 file: Ed Reed `a`, Chad Johnson `b`,
Alan Faneca `c`, Donovan McNabb `d`, Nate Clements `e`, Steve Hutchinson `f`,
Olin Kreutz `g`, Alge Crumpler `h`, Champ Bailey `i`, Daunte Culpepper `j`,
Trent Green `k`, Chris McAlister `l`, Jonathan Ogden `m`, Antonio Gates `n`,
Ronde Barber `o`, Takeo Spikes `p`, Shaun Ellis `q`, Santana Moss `r1`,
Richard Seymour `r2`, Edgerrin James `s`.

---

## What held up from the old list

The **grouping** was right even though the labels weren't. `j` through `s` are
the textured styles; `a` through `i` are the rest. The handoff's note that
non-black hair colours carry only twelve styles is consistent with this.

---

## Four levels of head shave

These read the same at a glance and are easy to confuse. They are distinct:

- `j` — fully bald, no stubble at all
- `l` — shaved, faint stubble shadow visible
- `i` — very short, receding at the temples
- `k` — horseshoe, bald crown with hair remaining at the sides

---

## Open question

**`r1` and `r2` are both long dreadlocks and could not be separated from the
screenshots.** Seymour's `r2` read slightly fuller at the front, but not
reliably. If a future session can distinguish them, record it here.

---

## Consequence: balding styles are assigned at random

`k` is a horseshoe, not a textured style. That means four balding styles exist —
`f`, `g`, `i`, `k` — and hair style is currently assigned at random with no
relation to age.

Measured across the published files: `k` sits on 464 rostered players, **33% of
them under 25**. `f`, `g` and `i` each run about 32% under-25 as well. Roughly
2,600 players across the published seasons wear a balding style unconnected to
their age.

Nobody noticed because the labels were wrong. Face **shape** already uses age
(thresholds at 260 lb and 30 years). Hair style does not. An obvious improvement
for a future pass, not urgent, and deliberately not done as part of the skin
repair.
