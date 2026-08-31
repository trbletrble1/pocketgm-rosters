# PGM3 — Madden source file quality

Which Madden CSV exports can be trusted for which fields, and how to test a new
one. Written 2026-08-31, the first session to hold all seventeen files at once.

Before this, files were handed over one at a time as a build needed them, and
each was assumed good because the previous one had been. Two of them were not,
and had already been used.

---

## The headline

**Seven of the seventeen files carry no usable skin signal at all.** Four are
perfect. The rest sit in between.

This is not about who made the file. Three of the seven failures are plain
year-named EA-derived files, the same class as the four that scored perfectly.

---

## Skin (`PSKI`) — scored file by file

Scored as AUC separating known-light from known-dark players on a fixed anchor
set of 154 players spanning every era. 1.000 is perfect separation, 0.500 is a
coin flip.

| file | AUC | verdict |
|---|---|---|
| `2005 - PLAY.csv` | **1.000** | authoritative |
| `2006 - PLAY.csv` | **1.000** | authoritative |
| `2007 - PLAY.csv` | **1.000** | authoritative |
| `2008 - PLAY.csv` | 0.999 | authoritative |
| `2016JINXROSTER_V8.1` | 0.982 | good |
| `2017JINXROSTER_V21.0` | 0.957 | good |
| `2021JINXROSTER V23` | 0.951 | good |
| `2000_-_PLAY.csv` | 0.950 | good — but see the middle-value note |
| `2020ROJOROSTER_V22` | 0.944 | good — **independent of JINX**, see lineage |
| `2023JINXROSTER V1.0` | 0.947 | good |
| `2025JINXROSTER V21` | 0.922 | good |
| `2015-SB-50 (2)` | 0.667 | **unusable** |
| `2003 - PLAY.csv` | 0.647 | **unusable** |
| `2013 - PLAY.csv` | 0.603 | **unusable** |
| `2004 - PLAY.csv` | 0.589 | **unusable** |
| `2011 - NickyJ` | 0.541 | **unusable** |
| `2012 - BKGiantsFan` | 0.529 | **unusable** |
| `2014-SB-XLIX` | 0.522 | **unusable** |

The 2004 file had been used as a skin source before this. In it, Marvin
Harrison, Walter Jones, Orlando Pace, Donovan McNabb, Jonathan Ogden and Ronde
Barber all carry `PSKI 0` — the same value as Peyton Manning and Jason Witten.

---

## The ten-second test: check the middle value

**Corrected 2026-08-31, same day it was written.** The first version of this rule
said "if any single value holds more than a third of the league, the field is
collapsed." That rule is wrong and fails every good file — 2005 puts 61% on
value 2 and scored 1.000, because value 2 is *dark* and the real league is
two-thirds dark. The rule was derived from the failing files without being
checked against the passing ones.

The actual discriminator is the share sitting on the **middle value** (`PSKI 1`),
the ambiguous level between light and dark.

| | value-1 share | AUC |
|---|---|---|
| 2005, 2006, 2007, 2008 | 5.5 – 7.1% | 0.999–1.000 |
| JINX 2016–2025 | 4.3 – 25.4% | 0.92–0.98 |
| 2020 ROJO | 25.3% | 0.944 |
| 2003, 2004, 2012 | 28.8 – 39.1% | 0.53–0.65 |
| 2011, 2013, 2014, 2015 | 69.3 – 91.6% | 0.52–0.67 |

Clean gap at roughly 28%. Everything below passes, everything above fails, on
all seventeen files scored so far.

**Rule: print the `PSKI` distribution and look at the share on value 1. Above
~28% the field is collapsed and the file is worthless for skin.** The largest
single value tells you nothing — it is supposed to be large, because most of the
league is dark.

This screen is cheap and it is only a screen. Anchor scoring is the confirmation.

---

## Two distinct failure modes

They need different detection and they justify different treatment.

**Collapsed field** — 2003, 2004, 2011, 2012, 2013, 2014, 2015. The field was
never populated with real variation, or was flattened somewhere in the export
chain. Detectable from the distribution alone. Unusable, not partially usable.

**Human judgement error** — the JINX family. The field is populated and mostly
right, but individual calls are wrong. Detectable only against anchors. Usable
at roughly 88%, and the errors cluster on recent stars: Burrow, Mayfield,
Crosby and Wirfs all read dark across four JINX files.

That clustering is the tell. A fan setting values by eye gets the obscure
players right by default and makes visible mistakes on the ones they have an
opinion about. The opposite of what you would expect.

---

## The middle value carries no information — abstain on it

**Added 2026-08-31, and it supersedes the bias section below.** Every `PSKI` field
has a middle value. Measured across six community files against 378 anchors:

| PSKI | anchors | % actually dark |
|---|---|---|
| 0 | 148 | 6% |
| 1 | 53 | **49%** |
| 2 | 177 | 97% |

Value 1 is a coin flip. **Skip it.** Do not assign it light, do not assign it
dark, do not treat it as a middle tone. Accuracy across the vote went 95.5% →
98.4% and registry coverage 27% → 63% from that single change.

Roughly 8–28% of a file sits on value 1 and is simply unresolvable from that file.

---

## A file can pass the anchor test and still be badly biased

Anchor scoring measures *ordering* — whether light players read lower than dark
ones. It does not measure where the file puts the cut.

Measured share of the league each source calls dark, against a real 65–67%:

| source | calls dark |
|---|---|
| JINX 2016–2025 | **84.9%** |
| 2020 ROJO | **51.7%** |
| photo measurement (ITA) | 68.7% |

**Corrected 2026-08-31:** those figures were an artefact of forcing the middle
value, not a property of the files. JINX looked 20 points too dark because value 1
was being read as dark; ROJO looked 14 points too light because value 1 was being
read as light. With value 1 abstaining, neither file is biased.

The general caution still stands — AUC measures ordering, not calibration, so
report the dark share alongside it. But check the middle-value handling before
concluding a source is biased.

**Always report the dark share alongside the AUC.** A file that ranks well and
calibrates badly is usable in a vote and dangerous on its own.

The practical consequence: two sources biased in *opposite* directions are far
more useful than two biased the same way. They disagree exactly where the call
is genuinely uncertain. Two sources sharing a bias agree confidently and are
wrong together — which is why combining the photo measurement with JINX failed.

---

## Source lineage: agreement is not independence

Files that descend from each other do not vote independently.

- **EA family** — 2005, 2006, 2007, 2008. Pairwise agreement 99.4–99.8%.
- **JINX family** — 2016, 2017, 2021, 2023, 2025. Pairwise agreement 96.4–100%.
- **2000** — separate lineage.

Four JINX files agreeing is one vote, not four. Measured accuracy by which
families cover a player:

| coverage | anchors | accuracy |
|---|---|---|
| any EA file | 83 | **100%** |
| JINX only | 52 | 88.5% |

**Rule: weight by lineage, not by file count.** Report coverage as "EA-backed"
or "JINX-only", never as "agreed by six files".

---

## Cross-file voting: what worked

Applied 2026-08-31 to repair the face registry.

1. Score every file independently against the anchor set. Discard anything below
   ~0.9.
2. Key votes on **name + position**, never name alone.
3. Let a file abstain where its own value is known ambiguous — the 2000 file
   abstains on `PSKI 1`, which is genuinely mixed (~54% dark).
4. Vote, then report confidence by lineage.

Results: 97.3% unanimous across 6,714 players the anchor set never touched, and
100% accuracy on every anchor with EA coverage.

---

## Other fields

`PHCL` (hair colour) separates strongly in every file tested and matches the
documented mapping. It was not scored file-by-file here — do that before relying
on it from a file that fails on skin.

Anchor sets built from stars are **position-confounded**: white anchors skew
quarterback, lineman and kicker; dark anchors skew receiver and corner. A blind
scan of all 110 columns for "what separates the anchors" therefore returns
`PSPD`, `PACC` and `PAGI` near the top. Those are not skin fields. Do not
discover a field this way without controlling for position.

---

## Files not scored

`2000_-_PLAY.csv` is scored above but sits outside the archive zip. Its `PSKI`
is a genuine four-level scale: 0 light, 2 and 3 dark, **1 genuinely mixed**.
Do not treat 1 as a middle tone — it is a bimodal bucket, roughly 54% dark, and
should abstain rather than vote.

`madden_skin_groups.json` was **removed from the project on 2026-08-31**. Kept
here as a record of why. It is a derived reference, not a source file. Scored 78%
against anchors and 76% against the 2000 file. **Its `agree: 1.0` field measures
consistency across files, not correctness** — Joe Thomas has six agreeing
observations and all six are wrong. Do not use it to drive changes.


---

## Source quality is per field, not per file

The seven files whose skin field is collapsed still carry **usable hair colour**.
`PHCL` distributions in 2003, 2004, 2011, 2013, 2014 and 2015 sit in the same
61–75% black / 15–31% brown band as the files that score perfectly on skin. Only
2012 BKGiantsFan is an outlier (37% black).

**Do not discard a file because it failed on one field.** Score each field
separately.

Hair colour reliability, measured 2026-08-31:
- **black vs non-black: 98%** on 775 observations
- **shade: unusable.** Known blond players read blond 18% of the time and brown
  47%. Brown and light brown are interchangeable.

---

## Coach skin (`COCH` / `CSKI`)

Scored on the 2005 and 2008 COCH exports against 54 coach anchors: **AUC
0.92–0.93**, with `CSKI` 0 = light (5% dark) and 1 and 2 = dark (92–100%).

Unlike the player files, coach `CSKI` is **correctly calibrated** — it puts 21% of
coaches on the dark side, matching both the real coaching population of the era
and the registry's own 24.1%.

The registry's staff faces were audited against it and found correct in 135 of
135. Where the file disagreed it was the file that was wrong, including calling
Belichick dark and Leslie Frazier light.
