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


---

## Reading `.ros` files without Windows

`tools/rosgui.py` (GUI) and `tools/rosdump.py` (command line) decode Madden
`.ros` binaries directly. Verified exact against Xtreme DB Editor's own exports
on three files — 2000, 2008 and 2020 ROJO — both `PLAY` and `COCH`, roughly
900,000 values, every one matching.

Build a double-clickable Mac app with `tools/build_mac.sh`.

**The screen is the point.** `rosgui`'s "Screen (usable?)" button runs the tests
in this document — middle-value gate on `PSKI`, dark share, `PHCL` band — in
about a second, without exporting anything. Drop a new `.ros` on it and you know
whether it is worth using before you spend any time on it. That is the check
that would have caught 2003, 2004 and 2013 before they were trusted for months.

It measures shape, not correctness. A file can pass the screen and still be
wrong. Anchor-testing remains the real check.

### All known exports share one schema

All 18 `PLAY` exports in `sources/madden/` carry an identical 110-column schema,
and all 5 `COCH` exports an identical 68-column one — 2000 through 2025, EA-derived
and fan-made alike. Community modders swap rosters inside a single game build;
they do not change the format. The decoder reads each file's own schema anyway,
so a genuinely different layout would still work, but in practice the case does
not arise.

The one different layout available is `template.dbt` shipped with Xtreme DB
Editor, which has 131 `PLAY` fields against these files' 110. It contains no
records, so it can only exercise schema reading, not value decoding.

### `2020ROJOROSTER_V22` has out-of-range coach skin

Its `CSKI` carries values of **4 and 7** on about 7% of coaches. No other file
does; 2000 and 2005 use only 0, 1 and 2. Xtreme reads the same values, so this
is real data rather than a decoding fault — a modder artefact.

It does not change ROJO's verdict. Recorded here because it looks exactly like a
parser bug and will be re-investigated as one otherwise.

**Coach skin has no middle value.** `CSKI` 0 is light and anything above it is
dark, unlike player `PSKI` where 1 means unknown and must abstain. Counting
coach dark as `>= 2` undercounts — it read ROJO at 17% against a true 20%.


## THE SKIN SOURCE TABLE — read this before the screen. `tools/skin_anchor.py`, `docs/skin_anchor_table.csv`

Every skin source this project holds, scored against one ground truth: the
**8,138 men the 2K5 archive labels unanimously across three or more of its
42 saves.** A `.ros` file is scored against the whole archive. A 2K5 save is
scored against the archive **without itself** — leave-one-out — because scoring a
save against a consensus it helped form makes every save look better than it is.
Ryan asked for this table after a five-file sample showed the screen rejecting
usable files; it now covers all 66 sources by design rather than by accident.

### The `.ros` files, 24 of them

| source | matched | accuracy | middle | screen |
|---|---|---|---|---|
| `ros/2008.ros` | 1,548 | **98%** | 6% | pass |
| `ros/2007.ros` | 1,629 | **98%** | 6% | pass |
| `ros/2016JINXROSTER_V8.1.ros` | 1,406 | **98%** | 4% | pass |
| `ros/2006.ros` | 1,561 | **98%** | 6% | pass |
| `ros/2005.ros` | 1,545 | **97%** | 7% | pass |
| `ros/2017JINXROSTER_V21.0.ros` | 1,389 | **97%** | 11% | pass |
| `ros/2020ROJOROSTER V22.ros` | 1,460 | **92%** | 25% | pass |
| `ros/2021JINXROSTER V23.ros` | 1,591 | **92%** | 25% | pass |
| `ros/2023JINXROSTER V1.0.ros` | 1,639 | **92%** | 15% | pass |
| `ros/2000.ros` | 1,380 | **90%** | 10% | pass |
| `ros/2025JINXROSTER V21.ros` | 1,070 | **90%** | 8% | pass |
| `1983madden/1983-SB-XVIII.ros` | 990 | **90%** | 24% | pass |
| `ros/2015-SB-50 (2).ros` | 3,350 | **77%** | 69% | REJECT |
| `ros/2012 - BKGiantsFan.ros` | 2,183 | **74%** | 39% | REJECT |
| `1979madden/1979-SB-XIV.ros` | 701 | **73%** | 43% | REJECT |
| `1979madden/NFL79.ros` | 701 | **73%** | 42% | REJECT |
| `ros/2013.ros` | 2,446 | **73%** | 79% | REJECT |
| `ros/2011 - NickyJ.ros` | 2,205 | **71%** | 83% | REJECT |
| `ros/2014-SB-XLIX.ros` | 2,451 | **71%** | 92% | REJECT |
| `1990madden/1990-SB-XXV.ros` | 1,654 | **70%** | 31% | REJECT |
| `ros/2004.ros` | 1,583 | **69%** | 32% | REJECT |
| `1986madden/1986_Roster_Mod_v1.0.ros` | 1,063 | **67%** | 63% | REJECT |
| `ros/2003.ros` | 1,480 | **67%** | 29% | REJECT |
| `1976madden/1976_raidermike.ros` | 429 | **57%** | 29% | REJECT |

**What the screen is, precisely.** The 28% middle-value threshold works as a
**two-bin sort and nothing more**: every file it passes scores **90–99%**
(12 files), every file it rejects scores **57–77%** (12 files), and
the two ranges do not overlap. That is a real relationship, and it corrects an
earlier line in this document — written on five files — that called middle share
and accuracy "close to unrelated." On 24 files they are not unrelated. **They
are related at the threshold and unrelated within a bin**: inside the rejected
group, 1976 at 29% middle scores 57% while 2014 at 92% middle scores 71%, and
2003 at the same 29% scores 67%. The middle share says which bin; it says nothing
about where in the bin.

**What the screen is not: a usability gate.** 67–77% is a weak source, not a dead
one. `NFL79.ros` at 73% on 701 men is real signal — weaker than the archive's 95%
and it must not outrank it, but it is corroboration, and the earlier reading of
"FAIL — unusable" was wrong for it and for eleven other files here. The `check`
command's wording has been changed to say so.

**The one file the screen rejects for the right outcome and the wrong reason** is
1976 raidermike: 57%, near a coin flip, at a middle share *lower* than three files
that score 67–71%.

### The 2K5 archive, leave-one-out

Internally consistent at **92–100%**, median 98%. The weakest:

| save | matched | leave-one-out accuracy |
|---|---|---|
| `2026SAVEGAME.DAT` | 824 | 92% |
| `1997-1998SAVEGAME.DAT` | 974 | 94% |
| `1981-1982SAVEGAME.DAT` | 804 | 94% |
| `1979-1980SAVEGAME.DAT` | 854 | 95% |
| `1986-1987AVEGAME.DAT` | 1,047 | 95% |
| `1989-1990SAVEGAME.DAT` | 1,101 | 96% |
| *(36 more)* | | 95–100% |

**Consequence for 1979's faces.** They do not rest on the archive "alone with no
cross-check": the 1979-1980 save scores **95% on 854 men** against the other 41
saves, which is a cross-check, and the two saves used for the 21 old expansion
men score 97% (1958-1980) and 99% (GOATs). The rule for the faces step is
therefore: **archive first; where archive and `NFL79.ros` disagree, the archive
wins; where the archive has no vote and `NFL79.ros` does, take it at 73% and flag
it single-source-weak.** 1976 raidermike contributes nothing at 57%.
