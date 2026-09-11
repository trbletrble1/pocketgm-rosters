# The archive — project context

*Written 7 September 2026. Revised 8 September. **Revised 9 September 2026**, after a
day that fixed more than it added: the archive gained 3,000 claims and lost a great
many wrong answers. Everything a new master session needs. Read it once, then work
from it rather than asking Ryan to repeat himself.*

**What was regenerated from measurement on 9 September is marked; what is Ryan's
ruling was left alone.** Where a figure has not been re-measured since 7 or 8
September it says so rather than being restated as current — §8 in particular.

**A fixed defect is struck through, never deleted**, so the change is visible and a
returning reader can see what moved. Everything in §11 and §15 was measured against
the served model on 9 September unless it says otherwise.

---

## 1. What this is

A historical archive of professional football held as data. Every player and coach from 1920 to the present, across the NFL, APFA, AAFC, all four AFLs, the CFL and its predecessor unions, the WFL, both USFLs, the XFL, the UFL, the AAF, Arena and NFL Europe.

**43,562 people. 7,897,681 claims. 501 stores.** *(Measured 9 September 2026 against
the served model `81c7b27a294ebb47`, built 12:09. Was 43,550 / 7.9M / 497 on
8 September and 5.1M / 474 stores on 7 September. The population barely moved today
because the day's work was correction, not acquisition.)*

The differentiator is not the data. It is that **every value traces to the document it came from**, that **where sources disagree the archive holds both and says so**, and that **every one of those 43,500 men gets a written biography** — most of whom have never had a paragraph written about them anywhere.

There is a second, older track: historically accurate roster files for the PocketGM 3 mobile game, published at `github.com/trbletrble1/pocketgm-rosters`. Seven seasons are out (1986, 2004, 2007, 2010, 2013, 2017, 2021). That work is dormant while the archive is built, but the repo is shared and the game's schema, face registry and validation suite still live there.

### The person

Ryan Necci. Has ADHD. **Wants short answers with detail on request.** When he says "simplify", give a genuinely simpler answer — do not restate the same thing in the same register. Plain prose, not formatted output, unless the content genuinely needs a table.

He is not comfortable at a command line. Write instructions for someone working in Finder and a browser. He will not make phone calls; his brother, an attorney, does those.

He makes the rulings. The sessions build. **Do not make a judgment call on his behalf and do not let a session make one either** — the correct behaviour when a convention is unclear is to stop and ask.

---

## 2. The values, stated once

These are not preferences. They are what makes the archive worth more than a scrape.

- **Real data over invented values.** Nothing is fabricated, ever. No generated faces, no filled-in gaps, no plausible defaults.
- **Honest counts over padded ones.** Say "unmeasured", never zero. An absence the source asserts and an absence we failed to measure are different facts and are stored differently.
- **Failures fail loudly.** A silently skipped record is worse than a crash.
- **No invented humans.** A man exists in the archive because a document says he does.
- **Disagreements are held, not resolved.** Two sources with two birth dates produce two claims. The archive does not choose.
- **A disagreement between two values that read to the same thing is not a disagreement.** `61"` and `6-1` are one fact written twice. Recording that as a conflict is fabrication, not scholarship.
- **Raw strings stay raw.** OCR damage, typos, a source's own spelling. `guide.Hionors` is held as printed. "None" as an assertion of absence is preserved as distinct from a blank.
- **Every fix ships with a gate**, and the gate catches the *property*, not the instance that bit.
- **Rulings are recorded as rulings**, with the alternatives stated, in `PGM3_PRECEDENTS.md`. Judgment calls are not silently re-opened.

---

## 3. Where everything lives

**The machine.** A Mac mini named `bghq-mac`, Tailscale `100.82.20.71`. M4 Pro, 64 GB, 903 GB free. It does not sleep and restarts after a power failure. The archive moved there from Ryan's MacBook on 7 September 2026.

**How Ryan reaches it.** Claude Code over SSH from his laptop, through Tailscale. He works on the laptop; the session runs on the mini. **This is the thing that makes the setup workable** — without it he is either standing at the mini or fighting a screen-share.

**The laptop** still holds a complete copy, renamed `pocketgm-rosters-clone-BACKUP-DO-NOT-USE` and `pgm3-sources-BACKUP-DO-NOT-USE`. **Delete nothing before 21 September.** An external drive holds a third copy; keep it until the laptop copy goes.

**Paths on the mini:**

| | |
|---|---|
| repo | `~/Documents/pocketgm-rosters-clone`, branch `dataset-design` |
| the archive itself | `dataset/build/` — gitignored, no history, 3.2 GB |
| derived index | `dataset/build-reports/person-index.json`, ~370 MB |
| sources | `~/Documents/pgm3-sources` — must sit beside the repo |
| preserved scratch | `~/Documents/session-scratch-from-laptop-2026-09-07/` |
| reports | `~/Dropbox/Football Archive/reports/` |
| session status | `~/Dropbox/Football Archive/status.json` |

**`dataset/build/` is gitignored and has no version history.** It is the only copy of five million claims. That fact drives most of the caution in this project.

**Measured 11 September: `build/` is 8.6 GB, and the mini has NO machine-level backup** —
`tmutil destinationinfo`: *"No destinations configured."* The laptop copy is from 7 September
and the external drive is not mounted here. **Store backups** (`build-reports/*-store.before-*.json`,
taken before a run overwrites a store) are **not committed and are not backups** — they are a
rollback aid that matters until that run's rebuild is verified and published, then may go.
Ryan's ruling; both halves in `DATASET_PRECEDENTS.md`, *A store backup is a rollback aid*.

### The one-time off-machine snapshot — a copy of a moment, NOT a backup

**Ryan's ruling, 11 September 2026**, as an interim measure until he is home to back the
machine up properly. **The mini still has no backup.** This is one copy of one moment, and it
ages from the day it was made.

| | |
|---|---|
| where | Dropbox, `/Football Archive/snapshots/build-2026-09-11-6975666d.tar.zst` — one file, copied once, **not a sync** (a sync of JSON the rebuilds rewrite would fight them, and would sync a corruption too) |
| what | **`build/` only** — every store, 3,302 files, 9.27 GB → **2.73 GB** zstd. Plus `MANIFEST.sha256` (every file's SHA-256) and `README.txt`, inside the archive and beside it |
| the moment | served model `6975666d5e80ba71`, git `315950c`, 11 September 10:44 |
| archive SHA-256 | `4891c10de74609d1c46432bc91c2b337fcd80b5bb54f297dd54b95b8edd9fbbb` (Dropbox content hash `4808819c92bef1d04d3e64cc735e1899f0f1568566dc068f3729f6bdf6473500`) |
| verified | full test decompression passed; the listing holds exactly 3,304 entries (3,302 + 2); three files extracted — the 891 MB `pfa-boxscores.json`, `clubs.json` and a random one — each match the manifest. **The server copy was opened, not assumed:** Dropbox's own content hash matches the one computed here; the file was downloaded back from Dropbox (2,725,854,475 bytes, about a minute), its SHA-256 matches the archive made on this machine, and it decompresses in full to the same 3,304 entries. The downloaded copy was then deleted |
| staged copy | `~/Documents/archive-snapshots/2026-09-11/` — on the same machine, so it is not a second copy |

**What it does not hold, and where that is:**
- **Code, declarations and `build-reports/` records** — in git, off-machine. `identity.json`, the
  person-id authority, is tracked.
- **The person index, the served model, the two kept models** — derived; rebuilt from `build/`
  plus committed code.
- **`~/Documents/pgm3-sources`, 9.8 GB — NOT in the snapshot and NOT in git.** Most of it can be
  fetched again. **Some cannot:** Crippen's AAFC register (sent by the author), the eBay programme
  photographs (listings close), the hand-saved PFR pages, the newspaper PDFs, `nfl-books`. Those
  exist only on the mini and on the 7 September laptop clone. The ruling excluded the sources as
  re-fetchable; that is true of most of them and not of these.

**Recovery path** (written down, **not rehearsed**): clone the repo at `315950c` or later; extract
the archive into `dataset/`; `shasum -a 256 -c MANIFEST.sha256`; `python3 src/build_person_index.py`;
`python3 service/build_read_model.py --force`. The sources are needed only to re-ingest or extend —
the stores already hold every claim. The same steps are in the README inside the archive.

**To repeat it weekly — measured, not set running; Ryan's decision.** On this machine the manifest
takes 18 seconds and the compression 7; each copy is about 2.7 GB and grows with the stores. It
would want: a repo script doing exactly these steps with `--write` (build locally, verify, then
copy into Dropbox under a dated name), refusing to run while `build/` is being written; a launchd
job, weekly; and a retention rule — four weekly copies is about 11 GB of Dropbox. **Upload time for
one copy: about a minute** (placed 15:44:27 UTC, on the server 15:45:30 — roughly 43 MB/s), so the
whole run is under two minutes of machine time. **It would still be a series of moments, not a
backup of the machine.**

**`/tmp` does not survive a restart.** Four working files were lost that way during the machine move, and two sessions put things back in `/tmp` the same day after writing themselves notes not to. Anything that matters goes in `build-reports/`.

---

## 4. The sessions

Through 7 September there were four, separated by scope: **Fetching** (external sources), **Parsing** (club table, person index, merges, bios), **Yearbooks** (reading documents), **API** (the read-only service). All four are now closed and the work runs through **one session**, reached over SSH.

The scope discipline no longer separates sessions, but it still applies as a habit: **know whose file you are in, and do not change something you have not measured.**

**Reports go to Dropbox. Status goes through `dataset/service/status.py`.** A master session reads both. A `done` status means the report is written; whether it has synced is a separate fact.

### How the sessions behaved, and why it matters

Over one weekend these sessions repeatedly caught their own errors before shipping them:

- A session's verification of the public URL went over the private network and proved nothing. It said so plainly rather than reporting success.
- A gate reported PASS against a population that already contained what it was checking. Found by asking why a count looked suspiciously round. Twice in one day, in the same session.
- A photo measurement matched 0 of 13,599 players — impossible for that league — so the session looked rather than reporting it, and found it was slicing a printed date as an ISO date.
- A parser reported 15.6% of rows as a "source defect". They were three field shapes it had read as one. Its own note: *a parser that reads one shape and reports the rest as a source defect is reporting its own gap.*
- A session found its in-flight photo ingest would silently discard five images and **stopped the run before it could write.**
- A gate was found carrying its own copy of the reader's acceptance test, so gate and reader could drift apart silently on both sides.
- Two sessions produced different figures for the same measurement. The second reported both and said its own test was cruder, rather than adopting the other's number.

**Do not erode this.** When a session offers a measured answer and a plausible one, take the measured one. When a number looks wrong, suspect the measurement first.

---

## 5. The recurring bug, in all its disguises

**An input that vanishes and reads as empty rather than raising.** It has cost, on separate occasions:

- 30,503 claims about 4,542 men silently dropped from the bios after the machine move — a missing 44 MB file behind an `os.path.exists` guard.
- The `assistants` store, 1,533 claims, never entering the person index at all.
- 2,019 stint claims skipped in silence because a subject was shaped differently.
- The dashboard dropping 73,508 claims because a predicate was unmapped.
- 60 CFL person-seasons deleted by a rebuild that didn't know a patch script existed.
- A gate self-test printing `SELFTEST OK` while one of its checks could not run.
- Five downloaded photographs — 3 WebP, 2 TIFF — dropped into `download_failures` because the size reader couldn't parse those formats. One was the largest image in the run.

**Second variant: a gate that can pass without checking.** `gate_guide_prose_corpus` samples 25 of 1,838 guides by default and 5,000 of 47,076 leads, then prints "every property holds". `gate_pfa2` and `gate_anachronism` can exit 0 having checked nothing. Four more have a check that silently no-ops. Named, mostly unfixed.

**Third variant: a measurement reading its own layer instead of the base state.** Three times in one day. Coverage reported as 432 when the archive held 2,054. A candidate pool of 1,900 when it was 2,329. "141 people hold nothing" when they held an unlicensed photograph under a different predicate in a different file.

**Fourth, and the worst: a fabricated disagreement.** Two sources cited, honestly held apart, saying the same thing in different notation. It survives every gate, because the gates check that disagreements are *held*, and they are being held faithfully, having been invented.

> *A hole you can see; a fabricated disagreement looks like scholarship.*

Known instances: **51 guide heights** (`61"` against `6-1`), and **roughly 3,200 drafts** where a parsed object and a raw string never compare equal.

**Fifth, and newest: a store that documents a discipline it did not follow.** `nflverse-rosters.json` records 1,079 people with `"ruling": "UNRESOLVED - both held"`. **For 1,021 of them the second value is held nowhere** — it exists only inside that report. PFA does the same thing correctly on identical ground, all 628 of its disagreeing people carrying a claim. A field named `ruling` asserting a discipline the store didn't follow is worse than silence, because it answers the question a reviewer would have asked.

**Sixth: a decider that classifies by reading a string.** *(9 September.)* A rule that
reads a VALUE where it should read a predicate, a scope or a declaration is right until
someone names the next thing differently, and then it is wrong silently. Four in one
file: a statistic decided by `store.startswith("stats-")` served **2,688,935 PFA
statistics as ordinary facts**; a coach decided by `league NOT IN ('COACHES',...)`
counted **41,662 of 54,908 staff claims as players** the day the coaching claims gained
real leagues; a name decided by the literal `"name"` made 1,607 names unsearchable. The
same two rules appear in 23 more files in `src/`. All four now read declarations, and
RS-G8 re-derives every one from the claims.

**Seventh: a derived id that moves when the data moves.** *(Twice in three days.)* A
club id derived from a name is only as stable as the name. `build_clubs` failed in the
chain and passed standalone for exactly this reason; then, the same day, the two
producers of a coaching row named the printed club differently and **46 clubs were
minted as `club--2000`**, taking a code off the Amsterdam Admirals and stranding 3,833
statistics claims. 45 places in `src/` name a club by a derived id.

**And the shape they share with the fifth: a second copy of one rule.** Three times in
one week. A gate that re-derived head standing while the builder had started reading
PFA's printed position reported **727 men losing a season**; not one had. A gate with
its own copy of the rule tests the copy.

The fix is always the same shape: **make the failure loud, and gate the property rather than the instance.**

---

## 6. Sources — held, tried, and closed

### Held and ingested

| source | what |
|---|---|
| **StatsCrew** | The roster spine. 3.27 M claims. Every professional league since 1920. |
| **Pro Football Archives (PFA)** | **3.79 M claims.** Player pages, boxscores 1920–59, coaches, officials, transactions, roster limits, training camps — and, since 8 September: **203 draft pages** (12,777 selections the archive did not hold), **229 award pages** (10,247 honour-team selections and 866 named awards), **4,374 team-season pages** and their **2.70 M per-player statistic cells**. |
| **PFA transactions** | 346,795 membership claims across nine predicates. |
| **nflverse** | Rosters 1920–2026, contracts, draft picks. **See §5 — its disagreement report is not backed by claims.** |
| **Wikipedia** | Ranked *below* media guides and contemporary newspapers. Claims, photographs, league and season articles. |
| **Media guides** | 2,824 documents on disk. 28,264 prose blocks extracted. |
| **PSF photo set** | 20,779 images — see §8, it is a video game mod. |
| **Coaching Tree** | Head and assistant stints, with the period vocabulary normalised away. |
| **1957 congressional hearing** | Club salary tables 1952–56, the printed Standard Players Contract. |
| **Arena** | 404 club-seasons, 5,018 players, 1987–2019. |
| **Ghosts of the Gridiron** | Preserved from the Wayback Machine, all 243 pages read. Facts ingested; **1,752 scans held pending permission, none published.** Names in prose are counted and located, not extracted. |

### Fetched, not yet used

- **60 eBay game programmes**, 1920s–1946. 48 of 55 carry a lineup or officials page. Text on disk with per-line bounding boxes. **The only per-game document class that existed before 1940**, and it carries *both* clubs' lineups — roster evidence for independent and defunct clubs nothing else holds.
- **Crippen's AAFC register** — 636 men with death date and place, sent by the author. Uningested.
- **PFR pages** saved by hand in `pgm3-sources/PFR PAGES/`. PFR blocks fetching; hand-saved pages work. Proven on 1943 Phil-Pitt, which matched the archive's derived roster 30 for 30.
- **13,596 PFA player leads**, parked by ruling.
- **PFA gamelogs and playoff logs are NOT on disk.** Corrected 8 September: the
  earlier note that 21,548 gamelogs were "fetched, not yet used" counted the pages
  PFA's own indexes LINK TO, not files. What is actually held is the **index** — 26
  alphabetical `nflgamelogs-*` pages and one top page — plus **one** per-player
  gamelog, and **no** playoff log at all. Linked from that index: 21,607 gamelogs and
  12,197 playoff logs. *The largest body of material PFA has that the archive has
  never touched*, and it needs the fetch it was thought not to need — about ten hours
  at the polite rate, and the least certain return of anything outstanding.
- **PFA leaderboards** — named by PFA's own navigation, nothing fetched.
- **2,406 post-1950 corpus documents**, unread.
- **1,469 team-season pages PFA's indexes named and the sweep never took** were
  fetched on 8 September; **25 more are named and answer 404**, including Frankford
  1923 and the 1926 Pacific Coast Wildcats. Those pages do not exist.

### Found 9 September — a source class nobody was looking for

**A CAPTIONED TEAM PHOTOGRAPH IS A ROSTER.** It was not on the hunting list, and the
reason is worth keeping: nobody knew to look. The list is derived from what the
archive knows it lacks, and it cannot name a *kind* of document nobody has thought
of. Eleven found on eBay, all of them club-seasons where the archive is thin or empty:

| club-season | why it matters |
|---|---|
| **Akron 1920** | the first APFA champions |
| **Dayton 1919** | pre-league, and the archive holds almost nothing before 1920 |
| **Canton 1922** and **1923** | |
| **Racine 1922** | |
| **New York Giants 1927** | |
| **Portsmouth 1929** and **1932** | |
| **Pittsburgh 1933** | the Pirates' first season |

**And two barnstorming programmes, 1934 and 1935** — the Giants against Ernie Nevers'
touring side. A barnstorming game is a club-season the league record does not hold at
all, which makes a programme for one worth more than its date suggests.

The precedent already exists — *a man named in a team photograph caption is a
person*, ruled on the 1926 Pacific Coast Wildcats. What is new is that the caption
names ENOUGH men to be roster evidence rather than a single placement. The rights
route is the photograph route: **the caption's facts are read and cited, the image
is not reproduced.**

**THE GHOSTS GAME PAGES CARRY LINE-UPS.** 226 game pages hold a line-up for
club-seasons where the roster survey found no roster at all. All 243 Ghosts pages
were read for facts in an earlier pass — this is not a re-fetch and not a page
anyone missed. It is the same page class read for a *different* thing: the survey
asked each page whether it was a roster, the game pages said no, and the line-up
inside them was never asked about. **A survey that asks one question of a document
gets one answer.** (The 226 is the survey's own page class; it was not re-derived
from disk, where a crude line-up grep over the mirror answers 48. The definition is
what differs, and the next session should take the survey's, not the grep's.)

### Parked, not finished — the Ghosts narrative prose

**2,444 name-shaped strings across 229 pages, measured at 1.3% carrying enough context
to be usable.**

The line-up ingest of 10 September took the seventeen pages with a printed line-up, the
two honours tables, the officials, the substitutions and one roster limit. **It did not
touch the prose**, and the prose is where most of the names on this site are — inside
sentences like *"Beck with a great effort made a beautiful tackle"*, which names a man
and a club-season and a game, in a form nothing here can read.

**It is parked because prose extraction is an undesigned capability, not because there
is nothing there.** Designing it would touch the media guides (28,264 prose blocks) and
the reference books too, and doing it badly on one site first would set the shape for
all three. That is a ruling nobody has made.

**Do not read the line-up ingest as having finished this site.** It finished one
question about it.

### The eBay programme reader is not trusted as a measurement

**Ryan's ruling, 10 September 2026.** The reader was fixed that day and the fix was
real: routed by document shape, the 1926 Bears–Tigers bio page went from 2 entries
(neither a person) to 27 found and **24 recovered against the hand transcription**.

**It is still not a measurement.** Across the class it moved 255 men to 292 — 15%, not
a transformation — and the reasons matter more than the number:

- **Only one listing in 55 has a bio page.** Page Seven is nearly unique.
- **Three of the four public-domain listings that yield zero are blocked by a document
  shape the reader has no route for** — two clubs side by side with the right-hand
  table MIRRORED, so a reader that does not know reads the college as the name on every
  row of it.
- **Two are blocked by OCR damage no reader can fix.** The Pacific Coast Wildcats front
  spread reads at 0.416: three name-shaped strings survive out of 22 known.
- **The classification of what each listing IS was done by sampling and got the Tigers
  page wrong.** It has not been replaced.

**So the corpus wants reading by eye.** A yield figure from this reader is a floor and
should never be quoted as what the class holds. The hand transcriptions — the Tigers
page, the Wildcats spread, the Gunners — are what the archive actually knows about
these documents, and they are what proved the reader wrong both times.

### 1927 EFL: one source relayed three ways

**Established 10 September 2026, and it is the shape of a question to ask of any
single-source season.**

`club-bethlehem-bears-1926` spans 1926–1927 and the archive holds **no man** on 1927.
What asserts the season:

| | |
|---|---|
| Wikipedia's 1927 standings table | cites `profootballarchives.com/1927efl.html` |
| the archive's 11 transaction cells, 6 player pages | **PFA** player pages, every one UNDATED |
| a dated 12-game schedule on PFA's club page | **PFA** |

**All three are Pro Football Archives. Wikipedia is not a second source here, it is PFA
relayed** — and for a season the archive holds no man on, that is the whole point.

**The season was played.** PFA's `1927eflbet.html` carries a dated schedule, 18
September to 27 November 1927, with venues and five attendances up to 5,000. Counting
only the EFL opponents gives exactly Wikipedia's 1-3-1. So the span is **attested, not
stretched**, and the dark-years check correctly finds nothing: `_emit_pfa_only` builds
from attested years only and never bridges a hole.

**But no page names a man.** Five 1927 EFL club pages are on disk — Bethlehem, Newark,
Coaldale, Atlantic City, Shenandoah — and **the title test says none carries a roster**:
every title reads `1927 <Club> (EFL) - Pro Football Archives` with no *"Scores, Roster,
Stats, Coaches"*. Confirmed by reading them: SCORES and, on two, Schedule Notes. The
league page Wikipedia cites, `1927efl.html`, **is not on disk at all**.

**And no Ghosts page reaches 1927.** Eleven of the 243 mention it and every one is
Frankford or Pottsville, both NFL. The seventeen game line-ups run 1902–1926.

**What the season lacks is a roster or a line-up from a second source.** Reading the
five club pages would give the archive its first dated 1927 EFL games and would still
name nobody.

### Found and not assessed — the running list

Named as they were noticed, none assessed, none fetched. Kept here so they are not
re-discovered a fourth time.

- **Wikipedia season articles** — the club-season shape, as against the player
  articles already ingested.
- **cflapedia** — Canadian, and the archive's CFL coverage is among its thinnest.
- **Chronicling America** — Library of Congress newspapers, public domain, and the
  only *contemporary* route to the 1920s that is not Neft's reconstruction. See §6's
  provenance finding: this is the one class that could break the echo.
- **The Racine Heritage Museum** — a physical local collection for a club the archive
  is thin on, and one of the captioned photographs is Racine 1922.
- **Pro Football Journal** — the PFRA's other publication, distinct from the Coffin
  Corner.
- **footballarchaeology.com** — a working researcher's site on exactly the era the
  archive is thinnest in.
- **Ohio Memory** — already named in §8 among the untried photograph routes; repeated
  here because it is a document route too, for the 1920s Ohio League clubs the archive
  holds almost nothing on.

### On disk and unread — measured 9 September

It has grown, and it is now the largest thing about the archive that no document
records.

| | |
|---|---|
| **21,552 PFA gamelog pages** and **12,195 playoff-log pages** | Only the 1970s ROWS have been read. A gamelog page is per-player-CAREER, not per-season, so **no page is finished** — the decade was taken out of pages that remain open. |
| **1,079 Coffin Corner articles** | PFRA's journal. 1,081 files on disk. |
| **226 Ghosts game pages** | See above — read for facts, never read for line-ups. |
| **69 programmes** | 1920s–1946, 162 files. The only per-game document class before 1940, and it carries BOTH clubs' lineups. |
| **151 college documents** | Pre-1950. |
| **1,517 media guides** | Of 2,824 on disk. |
| **3 reference books** | Crippen's AAFC, *Old Leather*, *The League That Didn't Exist*. |

**None of this is a hunt.** It is an ingest queue: the material is already on Ryan's
own disk and needs reading, not finding. The hunting documents mark such rows "Not a
hunt" for exactly this reason.

### Closed — do not re-tread

| | why |
|---|---|
| Wikidata | 72 coaching statements total, 3 pre-1960. |
| FamilySearch | API explicitly denies third-party access to the relevant collections. |
| Spalding Official Foot Ball Guide | A college annual, not a pro source. |
| Football card backs | No public database has transcribed them; essentially no cards before 1948. |
| Team newspapers | A 1970s–2000s class. Nothing comparable in the 1940s–60s. One catalogued run, Chicago Public Library, on site. |
| Obituaries | Every commercial route prohibits automation. Wikipedia beats them all. |
| databasefootball.com | 100% subset of PFA for the 1926 AFL, and the same reconstruction lineage. |
| Bain News Service | 5 candidates from 300 men, 4 wrong. It shot eastern *college* football. |
| archive.org for pre-1950 professional | Swept twice. Four unheld items exist. Genuinely exhausted. |
| `AFL3` on StatsCrew | Returns an identical stub for every year. The Arena code is `ARENA`. |
| nflverse headshot URLs | 15 of 20 sampled return one byte-identical generic silhouette. |
| PFR by fetch | Cloudflare-blocked, settled, do not retest. Hand-saved pages work. |

### The provenance finding that matters

**The 1920s statistical record traces to one man.** David Neft's team rebuilt the pre-1933 record from contemporary newspapers in the 1970s, published as *Pro Football: The Early Years* and later *The Football Encyclopedia*. StatsCrew, PFA and the fandom wiki all descend from it.

**So agreement between them on the 1920s is an echo, not corroboration.** Elias only became official statistician in 1961 and its historical verification covered 1932–60.

Ken Crippen named the AAFC reconstruction team too: Pete Palmer, Ken Pullis, Gary Selby. Original AAFC scoresheets survive with Palmer, Crippen and Joe Horrigan, incomplete.

---

## 7. People and correspondence

### Replied

**Ken Crippen** — `ken_crippen@kencrippen.com`. Founder, lead instructor and podcaster at the Football Learning Academy; PFRA AAFC Committee chair; co-author of *The All-America Football Conference*. **Cite him exactly that way.**

He answered generously and unprompted sent a complete AAFC player register — 636 men with death dates and places, comprehensive where his book had gaps. He confirmed:
- **There was no 1946 AAFC draft.** The first was 1947, held December 1946. PFA's 404 was correct.
- The Record and Fact Books are accurate.
- Original scoresheets exist but are incomplete.

Ryan thanked him and stated plainly that the book is used as a reference and cited, never parsed wholesale. Crippen then volunteered **David Neft's email**.

### Sent, awaiting reply

| who | what |
|---|---|
| **David Neft** — `davidsneft@yahoo.com` | Whether the working files behind the pre-1933 reconstruction survive. Sent 7 Sep, mentioning Crippen. He is in his nineties. |
| **The Pro Football Hall of Fame** | Ryan's brother is calling Jon Kendle, archivist, 330-456-8207. Two questions: would the Hall permit use of player photographs from mid-century club media guides, credited; and *is it theirs to grant* or the clubs'. The second may settle the whole class. |
| **CFLdb** | Roster data availability. |
| **Vintage Football Card Gallery** | Image reuse. Their About page already permits it with attribution. |
| **Frank Marousek**, prosportstransactions.com | Permission. Long outstanding. |
| **Ryan's brother** | Two federal records requests: the 1957 House Antitrust Subcommittee unpublished files, and the 1976 House Select Committee on Professional Sports — 14 linear feet at NARA, catalog ID 33089381, apparently untouched. The *printed* hearings are free online and probably not the prize. |

### Joined

**The PFRA**, $40, 24–48 hours to process. Members get AAFC scoresheets, gamebooks back to 1950, linescores to 1890, an assistant-coaches register, drafts from 1936, and 45 years of *The Coffin Corner*. Public forums at `profootballresearchers.com/forum/` are readable without membership.

**Note:** the 2019 PFRA announcement covered AAFC scoresheets for 1946, 1947 and 1949 — **not 1948**. A specific question worth asking.

### Physical archives, identified and unvisited

- **Pro Football Hall of Fame**, Canton. 40 M pages, 6 M photographs. Original 1920 APFA founding minutes. Spalding guides 1892–1940. Defunct-team files. Public by appointment.
- **Notre Dame, Joyce Sports Research Collection.** AAFC Record Manuals 1947–49 plus a 1950 supplement, Rare Books Small GV 955 .A453. Four boxes of official AAFC game statistical sheets, MSSP 1000, no access restrictions.
- **Historical Society of Frankford**, Philadelphia. Yellow Jackets 1923–31, two linear feet, game programmes for every season, negatives labelled by game date. **The only contemporary 1920s club archive found anywhere.**
- **Miami University**, Paul Brown Collection, 1.5 cubic feet, covers 1946–62.

---

## 8. Photographs — the biggest open problem

> **Not re-measured since 7 September.** The day of 8 September went to PFA and did
> not touch the photograph work; the model now holds 24,700 photograph claims against
> the 22,984 people this section counts, and the two are not the same quantity. Treat
> every figure below as of 7 September and re-measure before quoting one. The rulings
> in it are Ryan's and stand.

**The dashboard says 22,984 people have a photograph. The real usable, rights-clear figure is about 2,054.**

**The PSF set is a video game mod.** A readme inside it, which nobody had opened, reads: *"PICTURE PACK for Pro Strategy Football 2022-2023... thanks to Andy Fernandez at the Second and Ten mod site for permitting the Pro Strategy Football mod crew the use of the Second and Ten player and coach mod pictures."* One modding community lending files to another. No photographer, no source, no copyright statement anywhere. A `rename.bat` shows the files arrived as numeric ids and were bulk-renamed to player names — **identity in that set is a filename and nothing else.**

**And it is unusable.** 89% are 70×90 pixels. Nothing in 26,141 files reaches 400px; the largest is 330. **Before 2010 there are 26 usable images across 25,404 men.**

Ryan's ruling: **treat PSF as a reference set**, not a source. It tells you which men someone found a picture of, which helps hunting.

**Wikipedia's images are the real ones.** Median shorter side 1,153px. Licence recorded on every one. Identity confirmed by the source — the image sits on that man's article and the article names his club.

**The gap-fill rule was the mistake.** Every Wikipedia sweep skipped anyone who already held a photograph, so it never compared a 70×90 thumbnail against a 1,153px portrait. **Every single pre-2000 candidate is a gain — 731 of 731.**

### Where the photo ingest stands

| | |
|---|---|
| candidate pool | 1,898 |
| winners | 1,667 |
| dropped: fair use or unrecognised licence | 111 |
| dropped: API returned no dimensions | 120 |
| strictly larger than what is held | 1,517 |
| replaced on rights rather than size | all 1,667 |

**Every replacement is `superseded_on_rights`, none on size.** Not a contradiction — the only pairs eligible for the size rule were the 432 rights-clear holders, and every one of their candidates was the image they already held. The size rule's entire contribution was refusing.

**Ryan's rights-supersedes ruling changed the outcome for 150 people** — 145 with an unknown held size and 5 whose new image is smaller.

### Rights position, ruled

- Public domain or open Creative Commons only. **Fair use excluded**, always.
- Anything published in the US before 1 January 1931 is public domain outright.
- Never overwrite a larger image with a smaller one.
- **A rights-clear image supersedes a rights-unknown one regardless of size** — never-shrink applies only between images of the same rights status.
- Media guide headshots: **extract everything, tag by rights, publish only what is clear.** 966 of 1,061 across ten guides are attributable by structure, back to 1947. Ryan is inclined to publish them credited; the Hall of Fame call may settle it.

**One caveat that survives all of this:** dimensions overstate portrait usability. A 447px full-length 1918 photograph with a 60px face is worse than a clean 240px headshot. The store records what was measured and does not promise usability.

**Untried:** Wikimedia Commons by club and season rather than by person — a 1926 team photograph filed under the club is invisible to a person-keyed sweep. One is already in the archive by accident: *Los Angeles Buccaneers – Starting Team – 1926*, 2700×2201, **every man named in the caption**, eleven usable 1920s portraits in one file.

Also untried: Cleveland Public Library press photographs, Ohio Memory, Temple's Philadelphia Bulletin collection, and college yearbooks (Georgetown 1901–1950 fully searchable, Nebraska 37,000 human-transcribed pages, Pitt marking its 1910 volume "No Copyright").

**Ruled out:** AI-generated portraits. A generated face is an invented human wearing a real man's name. Geometric avatars seeded from a name or id, carrying no likeness claim, remain possible — but not derived from skin or hair data, since that came from the same broken measurement.

---

## 9. Rulings already made

- **Coaches are people.** Officials are people. On-field game participants is the line; it does not extend to trainers, owners or broadcasters.
- **Players who never played stay leads.** A coach with no career is missing a career; a player with no career signed a contract and got cut.
- **A person is someone who played, coached, or officiated at least one season.**
- **Merged clubs are their own clubs** — Card-Pitt, Phil-Pitt, Brooklyn-Boston, and the 1934 Cincinnati Reds distinct from the St. Louis Gunners.
- **A club's own media guide naming a man as its coach documents that he worked that season.** Absence from a different source is not evidence against.
- **Roster membership is a claim per source with its definition recorded.** The definition rides on the predicate, not the value.
- **Age and birth date are both taken.** Age is what the guide printed; the derived birth-year range is a check, never a correction.
- **Prose blocks stay whole and verbatim.** Never summarised, rewritten or OCR-corrected. The value is that a publicist in 1947 chose those words.
- **Guide labels are kept raw** — but a printed label MAY be mapped to a field, and `61"` MAY be read as `6-1`, both declared, keeping the printed string beside the reading. Same shape as `birth_date_as_printed`. This does **not** license mapping OCR damage or section headings: `guide.Aye` and `guide.GIANTS vs. PORTSMOUTH` stay as printed.
- **Two representations of the same fact are not a disagreement.** Compare on the fact, not the encoding.
- **Ethnic descent statements are captured verbatim and attributed** — 607 uses across 13 guides, and no modern source carries them.
- **Date strings are never standardised.** The store holds what the source printed; a calendar-day reading is derived, labelled, and shown beside the originals.
- **The service never resolves a disagreement.** Asking it for one value returns a 409 with the candidates. There is no policy verdict, deliberately.
- **Reference books are references.** Consulted, cited, not parsed wholesale. Ordinary scholarly use; it does not require asking every author.
- **Minor leagues are out of scope** — ACFL, COFL, PCFL, AFA, ORFU, DFL, MWFL. The Ohio League is *in*, as a gap rather than an extension.
- **`_verified_keys` is inviolable.** Any hand-set value can never be overwritten by an automated pass.

---

### Added 8 September

Six more, each with its evidence and its rejected alternative in
`docs/DATASET_PRECEDENTS.md` (19 entries to 42). Summarised, not restated:

- **A source with no denominator still has parts that have one.** Phil Flanagan, a
  1936 Giants ninth-round pick, absent because his page sat unread and nothing said so.
- **A selection with an order and no round is read as one, not given a round.**
- **A named award is its own predicate**, separate from an honour-team selection.
- **A nickname is a name, registered per man rather than read.** No string operation
  turns Blood into McNally.
- **A looser name match is safe only when a club-season holds it.** Cam Heyward, whose
  2024 teammates were Connor and Cameron Heyward.
- **An abbreviation folds only where it has exactly one possible school** — extended
  from 6 folds to 81 on measured evidence.

---

### Added 9 September

Three written into `docs/DATASET_PRECEDENTS.md` with their evidence and their
rejected alternative; the rest are rulings recorded in declarations. Summarised, not
restated:

- **A man named in a team photograph caption is a person.** Twelve promoted from the
  1926 Pacific Coast Wildcats caption, including George "Wildcat" Wilson, the man the
  club was named for, whom the archive did not hold on his own club-season because its
  roster there came from box scores. **The predicate does not move**: he was
  photographed with the club, not placed on its roster.
- **A disambiguator is evidence about which club is meant.** Stripping a source's
  `(1937–41)` before matching discards the only thing distinguishing two clubs of one
  name. Two bindings withdrawn.
- **Staff is decided by the predicate, never by the league.**
- **A coaching season is held in one shape** — `coaching_seasons`, decided by the
  predicate. The exclusivity is per CLAIM: a player-coach keeps both halves.
- **A display name prefers a forename-first form.** Surname-first is a filing
  convention. Nothing is standardised; both forms stay claims and stay searchable.
- **A coaching-only bio is its own shape.** A man who only ever coached is not a player
  with the playing part missing.
- **A club is named from the club table**, not from a map built by one source.
- **A script must not write unless it is asked.** `--write`, everywhere.
- **The previous published model is kept.** Two of them.
- **Minor leagues stay out** — reaffirmed 9 September after naming what is being
  excluded: the Norfolk Neptunes, Hartford Knights, Wheeling Ironmen, Toronto Rifles
  and 100 more, 375 men. The exclusion now covers named clubs rather than codes.
- **A printed roster is a roster.** `printed_roster` declared as a roster evidence
  kind, and 70 pre-1922 Frankford men promoted on it. **The refusal is what made the
  declaration mean anything** — the archive had already declined to treat a printed
  roster as roster evidence, so ruling that it is decides something. A declaration
  that costs nothing to make decides nothing.
- **`position` is a family, and it has a reading.** 79 codes and 77 long forms, **each
  spelt out whole** — stripping a leading `L` would turn a Long Snapper into a
  Left-something. Read into `{role, spot?, alignment?}`, the optional fields **omitted
  when unstated, so an unstated side is silence and not a difference**. The silence is
  `same()`'s own behaviour; there is no second implementation. Multi-position strings
  are **refused, not split** — whether a list of two contests a list of one is not
  ruled, and the 11,321 facts holding one are counted rather than guessed at.
- **A group name is silence about which member.** `DEFENSIVE_BACK` declared, so `DB`
  no longer contests `CB` — while the members still contest each other. **Declared
  from the data, not from football knowledge**: co-occurrence over 51,108 people, `DB`
  sharing a man-season with `CB` 113 times, `S` 44, `LCB` 29, `RCB` 20, `FS` 17, `SS`
  16, `DH` 3, `NB` 2. `LINEBACKER` was **not** declared and needed not to be — every
  linebacker code already reads to role *Linebacker* with the spot in its own field.
  **Four were stopped on rather than decided**, reasons in `declarations/positions.json`:
  `OL` (`OT`/`OG`/`LT`/`RT`/`LG`/`RG` co-occur **zero** times, and a 1920s `T` states
  no side of the ball), `DL` and `E` (`DE` co-occurs with both, so it would sit in two
  groups), and `B` (`QB` and `RB` co-occur with it **not once**).
- **Every declared family must have a reading, or be declared deliberately unread with
  a reason.** `src/gate_family_readings.py` — A1 a reading or a declared exemption, A2
  every reading names a declared family **both ways**, A3 every declared reading can
  actually be run. It exists because I declared a family *without* a reading and
  published it: 32,000 fabricated disagreements and **RS-G6 said PASS**, because a
  family with no reading was never in its population. RS-G6 now carries the numbers
  but **not** the property — two gates checking one rule is how a rule and its check
  drift apart.

### Added 10 September

- **A printed line-up from a named contemporary newspaper is roster evidence.**
  `printed_lineup` declared. It is NOT `programme.probable_lineup`: that exists because
  the Tigers programme printed its line-up BEFORE kickoff, and these are game accounts
  printed after. The distinction is the printing order.
- **A substitution is a different assertion.** A man who came on did not start. And a
  man may do both — Gaffney at Lancaster started, was replaced, and came back on.
- **`AFLNFL` is a competition between two leagues, not a league.** Super Bowls I–IV,
  declared like `IND`: it mints no league and holds no club.
- **Box scores and game logs are ingested row-shaped, per-game, never per-cell.**
- **`build_contested` keys on `(person, family, year)` where the family is about a
  season** — never on the raw `subject` column, which would undo person merging.
- **`holds()` stays person-level.** A season weight is not a man's weight. What changed
  was the hunting list's LABEL, not the test.
- **The eBay programme reader is not trusted as a measurement** — see §6.

---

## 10. Open questions Ryan has not ruled on

**The three-way birth-date split.** Measured 7 September across all 40,523 people
*(the population is 43,562 today; this split has NOT been re-measured since)*:

| | |
|---|---|
| the archive contests and the panel flags | 905 |
| the panel flags and the archive does not | 620 — of which 533 have no second claim at all, 87 are false by the same-day ruling |
| **the archive contests and the panel presents as settled** | **1,527** |

The last is the direction that **loses** information rather than inventing it, and nobody has ruled on it. Three groups, three causes, probably three different answers — do not bring it as one number.

Also open:

- `pfa.draft_allocation`, 602 claims — expansion and dispersal picks with no round or pick. A third dashboard row?
- Whether a disagreeing value must become a claim. That is the nflverse defect in §5 and it is a ruling, not a bug fix.
- Seven StatsCrew self-duplicates: the source says two men, a shared birth date says one.
- 34 unclassifiable duplicate person pairs.
- Whether the 7,278 `face_colour` claims from the broken measurement come out.
- Whether college football enters scope. Currently no; the pre-1950 college documents yielded 110 candidate men from 6,238, and only 35 with an extractable record.
- Whether media guide headshots get published credited without permission.
- What a person's page shows, and what it does when sources disagree. That is the website's question and it forces the policy-verdict decision.

---

### Added 8 September

- **`pfa.draft_allocation` is not a member of the draft family**, so 602 held claims
  and ~1,631 rounds-free selections still on disk reach nothing downstream. Measured:
  adding it creates 1,995 ordered-against-existing pairs across 580 people and folds
  **none** of them.
- **The 14 new college synonym candidates** of the non-final-word shape, measured and
  not folded.
- **The 227 PFA club strings the table refuses** — 9,088 of the 9,743 men behind them
  sit in leagues the archive holds no club-season in at all, so this is the
  minor-league exclusion and not a table defect. 478 more sit in leagues it *does*
  hold, in years it does not; **but AFL, UFL and WLAF each name several unrelated
  competitions, and only WLAF 1995 turned out to be the same league.**

### Added 9 September

- **Is an adjacent season of the same club enough to match a surname?** The ruled
  join has tier 3 as a surname on THE club-season. A surname on the club-season
  either side is not that, and it is not nothing either — clubs of this era carried
  the same men year to year, and a roster missing one season is the normal case, not
  the odd one. Loosening it would resolve a large part of the 745 ambiguous leads.
  **THE CAVEAT THAT MAKES IT A RULING AND NOT A TWEAK: brothers.** Early professional
  rosters are full of them, they share a surname, they play for the same club, and
  they frequently play in ADJACENT seasons rather than the same one — which is
  precisely the pattern the loosened rule would read as one man. The archive has
  already been bitten by a name-only lookup merging a father and a son. Not decided,
  and not to be decided by whoever next finds it convenient.

---

## 11a. Known LIMITS — not defects, and not fixable by declaring anything

A defect is something behaving other than as designed. A limit is the design. These
are recorded because they are **invisible from every gate line**, so a session that
does not know will rediscover them the expensive way.

### The contested table holds only claims whose subject carries a person

`build_contested` selects `WHERE person IS NOT NULL` on **both** its date path and its
value path. A claim whose subject is a game, a club-season, a league-season or a
document has no person in that column.

**So games, clubs and documents cannot hold a disagreement at all.** Not "do not
currently" — *cannot*. Declaring a predicate family over them changes nothing, and
this is not visible from RS-G6, which reports only on what the contested table
already holds.

**Measured 10 September 2026, and this is how it was found.** Ryan ruled that a box
score and a game log describe the same game and must be comparable, so the `game`
family was declared over `pfa.game` and `pfa.game_as_logged` with a reading. The model
was rebuilt: **contested pairs 26,335 before, 26,335 after**. The family is correct,
the reading is correct, and nothing happened.

**Ryan ruled 10 September 2026 that it stays.** Keying the contest builder on the
subject is a read-model change touching every non-person subject in the archive, and
the case that raised it had nothing to compare anyway — the two sources agreed 1,932
of 1,932 on every field both carried, because they carry almost nothing in common.

**What this means in practice.** For any subject that is not a person, two sources
that disagree will sit side by side under different predicates and nothing will say
so. If that matters for a future source, the fix is the contest builder, not a
declaration — and it is a real piece of work, not a one-line change.

### The 10 September rekeying did NOT close this

`build_contested` was rekeyed that afternoon onto `(person, family, year)` where the
family holds season-scoped members. **That fixed a different half of the same defect
and left this half exactly as it was.**

- What it fixed: some *person* subjects were contesting **wrongly**. A guard who later
  played tackle was recorded as a disagreement with himself, 17,372 times. Adding the
  year asks "what was his position *that season*", which is one question.
- What it did **not** fix: a subject with **no person at all** still cannot contest.
  The key still begins at the resolved `person`, and it begins there deliberately —
  keying on the raw `subject` column was measured and would have **undone person
  merging**, because `subject` holds the pre-merge id and only 28.2% of birth_date
  claims have the two agree.

So games, clubs and documents are exactly where they were. The `game` family is still
declared, still correct, and still holds no contested row — 35,194 claims that cannot
disagree. **A later reader should not read the rekeying as having closed this.**

The two halves want different fixes: this one wants the contest builder to key on the
subject *for subjects that have no person*, which is safe precisely because those
claims have no merge layer to undo.

---

## 11. Known defects, unfixed

| | |
|---|---|
| **nflverse disagreement report** | 1,079 people marked `"ruling": "UNRESOLVED - both held"`; **1,021 hold no second claim.** The value exists only in the report. PFA does it correctly on identical ground. Needs a ruling, and a gate comparing every store's disagreement report against its own claims. |
| ~~Draft representations~~ | **FIXED 8 September.** The reading is a dict carrying league, kind and numbering, and the fabricated disagreements are gone: RS-G6 reports 0 false disagreements across seven families. The 2,068 draft contests that remain are real. |
| ~~51 guide heights~~ | **FIXED.** The height reading folds them; 3 height contests remain and RS-G6 confirms none is false. |
| **RS-G3** | 414 `club-names` claims name source records that were never registered. Published with `--force`, WARNING on every response. **No exception list — it should stay uncomfortable.** |
| **RS-G5** | `guide-pre1950-delimited.json` nests its 1,653 claims under `runs.<club>.guides.<year>.claims` and has no top-level `claims` key, so the read model cannot see it. Correctly red, correctly not declared away — the corpus yields 38 pre-1950 claims against its 1,653. Fetching swept all 1,146 build files: **it is the only instance.** |
| **Sampling gates** | `gate_guide_prose_corpus` samples 25 of 1,838 guides by default then prints "every property holds". `gate_pfa2` and `gate_anachronism` can exit 0 having checked nothing. Four more silently no-op a check. |
| `gate_merged_clubs` M4 | Fails on `PIT\|1943`, held. |
| `gate_club_keys` G7 = 1 | `assistants.json` holds a stint whose club is a guide *title*. |
| ~~**187 impossible ages**~~ | **MOSTLY FIXED 9 September, and re-measured: 187 → 15.** On 8 September 118 men were too young for a season they held and 69 too old, and **142 of the 187 came from the PFA statistics ingest**, which had matched on a name without holding to the club-season. With the ruled join and the ±3 span guard in place: **2 too young, 13 too old.** The 15 that remain are older and are not the statistics ingest's. *(Counted with coaching club-seasons excluded BY PREDICATE, which is the shape the archive now holds them in; the first re-measurement got 218 by letting `coaches-nfl` rows through, and that was my method, not the archive.)* |
| **631 statistics claims** | Across the `stats-*` stores, naming nobody — the ingest minted an id for a row it couldn't match and wrote no name. *(Re-measured 8 September; was reported as 649.)* |
| **2,018 club-table reach keys** | Season keys placing a man on a club-season the club table cannot name: 660 where it holds the club but no name for that year (almost all 2025), 809 where the token places at another year, 549 where the token is never placed. **Every one of the 466 triples rests on exactly ONE source**, so `SPAN_EXTENSIONS` can move none of them — the blocker is evidence, not policy. `gate_club_table_reach` is a RATCHET on this number. |
| **107 of 108 unnamed club tokens, named** | *(9 September.)* Formerly "274 tokens the bios print raw". They are named from `club_as_printed` on their own claims and from the PFA pages the claims cite — the Norfolk Shamrocks, the Wheeling Ironmen. **One cannot ever be named**: a `salaries` season key that is a literal `?`. All but two fall under the minor-league exclusion. |
| **build_dashboard.py:133** | Skips 217 `stats-*.json` from the store census and shows 11 `pfa-stats-*.json` beside them. **The census is inconsistent with itself**, in the one artefact meant to say what the archive holds. The last surviving instance of the store-name test. |
| **997 coaching-only bios → 0** | ~~503 from `get_bio`~~ **FIXED 9 September.** All 2,138 render. A pre-existing writer bug it exposed is fixed with it. |
| **34 of 35 not-file-shaped declarations** | Declare no `enumerable_parts`. `gate_source_coverage` is red on them by design: an absent list cannot be told from nobody having looked. **Reported, not rewritten** — generating 34 declarations from a script would be 34 sentences nobody had thought about. Ryan's call. |
| **PFA's `TKL`** | Demoted to its own predicate on 8 September: StatsCrew's `Tackle` is its own `Def + ST` and PFA's `TKL` is its own `DT + STT`. Whether either can be reconciled to the other is unruled. |
| **28,202 → 65 misaligned statistic rows** | PFA renders rows under a fuller layout than the header it prints. 28,137 are now read by the row-length rule; **65 match no layout PFA uses anywhere** and are unread. |
| 75 of 92 court-salaries people | Cannot be traced back to the man the court named. |
| 15 scratchpad paths | Declared with owners, 5 closed. Four were under literal `/tmp` and are gone. |
| The vitals panel | Names a disagreement only from certain stores. Reported by the service as `panel_quieter_than_the_claims`. **Reports, does not correct.** |

---

## 12. The service

Read-only, on the mini, under launchd, surviving reboot and power failure.

- **Local:** `127.0.0.1:8765`, unauthenticated.
- **Tailnet:** `100.82.20.71:8765`, token required.
- **Public:** `https://bghq-mac.tailfb9ba8.ts.net` via Tailscale Funnel → `127.0.0.1:8766`, token required, `/rebuild` refused outright.

**The URL contains the token, so the URL is the password.** Rotate by deleting `~/.config/football-archive/token`; the next request writes a new one and the old dies instantly. Close it entirely with `expose.py off`.

**Fourteen MCP tools**, including `get_bio`. See `USING_THE_ARCHIVE.md`.

**When a tool is added, the connector must be removed and re-added.** A new chat is not enough — the tool list is cached from when the connector was created. This caused one false alarm where a session appeared to have invented a tool it had in fact built.

### The gates — what each holds, and which are ratchets

*Regenerated 9 September. **A gate that passes at 2,018 is not broken.** Two of these
are ratchets: they hold a number that should fall, and fail when it RISES. A gate that
demanded zero would either be a lie today or would be satisfied by looking away.*

**In the read model** — every one runs on each build, and a FAIL refuses publication
unless `--force` is given, in which case every response says so.

| | holds |
|---|---|
| RS-G1 | an unreadable date fails, unless `dates-as-printed.json` carries it |
| RS-G2 | an unresolved person fails, unless its store is declared known-unresolvable |
| RS-G3 | a claim naming a source record its store does not hold. **RED: 414**, `club-names`. No exception list — it should stay uncomfortable |
| RS-G4 | the people here reconcile with the people in the index. 43,562 both sides |
| RS-G5 | every file in `build/` is a store in the model or is explained. **RED: 1**, `guide-pre1950-delimited.json`, which nests its 1,653 claims where the reader cannot see them. Correctly red and correctly not declared away |
| RS-G6 | no FALSE disagreement — seven families, 0 false |
| RS-G7 | *(new, 8 Sept)* every league token is a league the club table holds, or one declared a non-competition. Caught a `PFA` token I fabricated myself, on 32,406 claims |
| RS-G8 | *(new, 9 Sept)* **classification is declared, not read off a name.** Statistics stores, staff predicates, name predicates and the surname-first reading, each re-derived from the claims and failing in BOTH directions. The statistics half checks a PARTITION rather than deriving the vocabulary from the declaration it is checking — the first version passed on an empty declaration |

**Outside the model.** These run on demand and are the property record for work that has
no place in the read model.

| | holds |
|---|---|
| `gate_clubs` K1–K11 | the club table. K10 *(new)*: the pseudo-league tokens are DERIVED from the declaration, not typed — `("COACHES","SALARIES")` was written out in four files and none gained `IND`. K11 *(new)*: no club is minted from an empty name |
| `gate_club_table_reach` | **A RATCHET.** Season keys placing a man on a club-season the table cannot name: **2,018 today**, in four counted classes. Fails if it RISES; when it falls it says so and names the new ceiling to write down. Zero would be a lie today and unreachable tomorrow |
| `gate_writes_are_opt_in` | **every `__main__` that can write takes `--write`. 33 opt-in, 0 by default.** Written first and allowed to fail, so the list it produced was the work list |
| `gate_coaching_season_shape` | a coaching season is in exactly one of the two dicts, decided by predicate; **and a player-coach keeps BOTH** — the half that stops "delete the coaching seasons" passing |
| `gate_coaching_only_bios` | all 2,138 coaching-only men render; each bio is a finished sentence; the lead matches the career; it does not call a span a season count; it does not give a role to a man no source gives one to |
| `gate_bio_club_names` | **a bio must not print a club token the archive can name. 1,047 → 0**, both figures from the same gate on real data. Three unjudgeable classes are counted, never passed silently |
| `gate_fandom_bindings` | a redirect must not fold one club into another on a shared word. Checks the disambiguator the matcher throws away. Its limit is in its docstring: it cannot see a reused name with no disambiguator |
| `gate_source_coverage` | a declaration that is not file-shaped must enumerate its parts. **RED on 34 of 35 by design** — an absent list cannot be told from nobody having looked. Reported, not rewritten |
| `service/gate_retention.py` | the previous published model is kept. Six properties proved on **real publishes**, not asserted. Property 0 reads the model actually being served, which is the only one a fixture cannot fake — and it caught this code's own bug |
| `service/gate_selftest.py` | **every read-model gate must FAIL when its invariant is broken.** Not ceremony: a gate that has only ever passed has not been tested. It caught its own fixture the day `staff_predicates` moved to the archive's declarations |

**Two standing reds, and they are not neglect.** RS-G3 (414) and RS-G5 (1) are each a
real thing the archive has chosen to hold rather than declare away, and the service says
so on every response.

## 12b. What is still open, plainly

*The things a new session would otherwise rediscover. Every figure measured 9 September
against `81c7b27a294ebb47`.*

**Waiting on evidence, not on a ruling:**

- **2,018 club-table reach keys.** 660 want a second source for 2025 — only PFA reaches
  past 2024 for the NFL and UFL, and `SPAN_EXTENSIONS` rightly refuses one source's
  say-so. 809 want a second source AND then 223 declarations, one year at a time. 549
  are clubs the table does not hold at all.

**Waiting on Ryan:**

- **The 549 never-placed tokens**, now named (§11). Which of these minor-league clubs,
  if any, the archive admits. The list is in
  `reports/2026-09-09-clubs-the-table-never-places.md`.
- **The two WFL 1974 relocations' other halves.** The combined printed forms are on the
  origin clubs; three of the six men are placed by a second source and three are placed
  by nothing but PFA's combined form.
- **nflverse-rosters**, 1,021 second values that exist only in a report.
- **34 of 35 not-file-shaped declarations.**

**Waiting on someone to do them:**

- **15 impossible ages**, down from 187. Not the statistics ingest's.
- **`build_dashboard.py:133`** — the last store-name test, and its census contradicts
  itself.
- **631 statistics claims naming nobody**, and **65 misaligned rows** matching no PFA
  layout.
- **The sampling gates.** `gate_guide_prose_corpus` samples 25 of 1,838 and prints
  "every property holds"; three more can exit 0 having checked nothing.
- **45 places that name a club by a derived id.** Two of them have already moved.

---

## 13. What to do next

**The sweep was done, on 7 and 8 September, and the four questions below are its
questions.** It is left here because it earned its place: every defect it found was one
nobody was looking for, and the same four questions asked again on 9 September found the
sixth and seventh disguises in §5. Ask them again.

**The original case for it.** Every defect above was found by accident — a sentence missing from a bio, a count that looked suspiciously round, a number that couldn't be right for that league. None came from a source; all came from the plumbing. A deliberate sweep looking for those same shapes on purpose converts an unknown number of latent faults into a list.

Four questions worth asking systematically:
1. Which gates can pass without checking anything?
2. Which readers drop what they cannot parse?
3. Which claims rest on a reading nobody declared?
4. Which measurements describe a build file rather than the archive?

**Then, in rough order of value.** *Reordered 8 September on measured gain, not
impression:*
*Revised 9 September: PFA's 33,750 game and playoff logs are FETCHED and unread, which
moves them to the top — the fetch was the slow part and it is done. Crippen's AAFC
register is ingested.*

1. **PFA's game and playoff logs** — 33,750 pages on disk, nothing ingested. The largest
   body of unread material the archive has ever held in hand.
2. **PFA's leaderboards** were empty and are still unfetched — five minutes of work.
3. Wikimedia Commons by club and season.
4. Media guide headshot extraction, tagged by rights.
5. The corpus inventory — 2,406 documents nobody has read.
6. Media guides as the fourth roster-membership source.
7. The eBay programme lineup pages — 48 of 55 carry one.
8. ~~Crippen's AAFC register~~ — **ingested 8 September**, 5,974 claims and 446 leads.

**And the thing the whole archive is for:** the website. One search box, a page assembled from claims at read time. The service and the bio endpoint are its spine and already exist. The design question — what a page shows, and what it does with a disagreement — is Ryan's and unmade.

---

## 14. Habits that have earned their place

- **Measure before explaining.** Never offer a plausible cause for an anomalous number before measuring it.
- **Find the real cohort first.** A distribution can pass while the internal structure is broken.
- **Read the base state, not your own layer.** Three measurements in one day described one build file rather than the archive.
- **An empty result and a failed one are the same bytes.** Read the HTTP status. Check the file. Never infer success from a file existing.
- **A gate that reimplements what it checks can pass while the thing it checks has changed.** One definition, imported by both.
- **A source not found is provisional.** Ryan has found significant material after a search declared the well dry more times than is comfortable — the 1936 Boston guide, the Rense yearbook, the eBay programmes, the fandom wiki, the "foot ball" spelling that unlocked 366 pre-1930 items.
- **Titles are wrong.** A baseball Giants yearbook filed as football. Eight Vietnam War novels matched on "Eagles". A 1945 photograph sold as 1943. Open the file.
- **Name a refusal rather than forcing it.** Every unresolvable string is counted and reported. The bank of leads, refusals and held disagreements is not lost work — it is work waiting for evidence.
- **Report what you could not establish**, not only what you found. The most useful sentences of the weekend were a session saying its own verification was worthless, or that its test was cruder than a peer's.
- **A rule that reads a value where it should read a declaration is a latent defect.**
  It agrees with the data today and disagrees the day someone names the next thing
  differently. *(Added 9 September, after four of them in one file.)*
- **Fix the root, then re-check downstream before changing anything.** Eleven of the
  twenty sites downstream of the coaching-season shape became correct without being
  touched. A file that becomes correct on its own is the sign the root was the root —
  and the ones that do not are then a short, honest list.
- **Correct your own numbers, in public, with both figures.** The day's most useful
  sentences were "43 tokens cannot be named" being wrong twice over, and "218 impossible
  ages" being my method rather than the archive.
- **Losing a fact to save a repetition is the worse trade.** A fix that tidied a repeated
  club name also deleted Jack Pardee's Rams years. Reverted, with the reason left in the
  code.
- **Nothing systematically revisits a refusal when new evidence arrives.** A real gap and a good future job.
