# The archive — project context

*Written 7 September 2026. **Revised 8 September 2026**, after a day that added 2.7
million claims and six precedents. Everything a new master session needs. Read it
once, then work from it rather than asking Ryan to repeat himself.*

**What was regenerated from measurement on 8 September is marked; what is Ryan's
ruling was left alone.** Where a figure in this file has not been re-measured since
7 September it says so rather than being restated as current — §8 in particular.

---

## 1. What this is

A historical archive of professional football held as data. Every player and coach from 1920 to the present, across the NFL, APFA, AAFC, all four AFLs, the CFL and its predecessor unions, the WFL, both USFLs, the XFL, the UFL, the AAF, Arena and NFL Europe.

**43,550 people. 7.9 million claims. 497 stores.** *(Measured 8 September 2026
against the served model; was 5.1 million and 474 stores on 7 September.)*

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

## 10. Open questions Ryan has not ruled on

**The three-way birth-date split.** Measured across all 40,523 people:

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

---

## 11. Known defects, unfixed

| | |
|---|---|
| **nflverse disagreement report** | 1,079 people marked `"ruling": "UNRESOLVED - both held"`; **1,021 hold no second claim.** The value exists only in the report. PFA does it correctly on identical ground. Needs a ruling, and a gate comparing every store's disagreement report against its own claims. |
| ~~Draft representations~~ | **FIXED 8 September.** The reading is a dict carrying league, kind and numbering, and the fabricated disagreements are gone: RS-G6 reports 0 false disagreements across seven families. The 2,068 draft contests that remain are real. |
| ~~51 guide heights~~ | **FIXED.** The height reading folds them; 3 height contests remain and RS-G6 confirms none is false. |
| **G3** | 414 `club-names` claims name source records that were never registered. Published with `--force`, WARNING on every response. **No exception list — it should stay uncomfortable.** |
| **RS-G5** | `guide-pre1950-delimited.json` nests its 1,653 claims under `runs.<club>.guides.<year>.claims` and has no top-level `claims` key, so the read model cannot see it. Correctly red, correctly not declared away — the corpus yields 38 pre-1950 claims against its 1,653. Fetching swept all 1,146 build files: **it is the only instance.** |
| **Sampling gates** | `gate_guide_prose_corpus` samples 25 of 1,838 guides by default then prints "every property holds". `gate_pfa2` and `gate_anachronism` can exit 0 having checked nothing. Four more silently no-op a check. |
| `gate_merged_clubs` M4 | Fails on `PIT\|1943`, held. |
| `gate_club_keys` G7 = 1 | `assistants.json` holds a stint whose club is a guide *title*. |
| **631 statistics claims** | Across the `stats-*` stores, naming nobody — the ingest minted an id for a row it couldn't match and wrote no name. *(Re-measured 8 September; was reported as 649.)* |
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

**Six gates:** RS-G1 unreadable dates, RS-G2 unresolved persons, RS-G3 source records, RS-G4 population reconciliation, RS-G5 claim stores absent from the model, RS-G6 false contests. **RS-G3 and RS-G5 are red for stated reasons; the other four pass** *(8 September)*.

**RS-G6 now checks seven families, not two** — birth_date, birth_place, college,
death_place, draft, height, weight — over 5,507 contested facts, 0 false. It was
effectively inert while only two families were declared; it has since gone red twice
on real findings and been cleared by a rebuild each time.

**The club table has its own gate**, `gate_clubs`, now K1–K8: K7 covers a string a
source misprinted, K8 a club's span extended by one adjacent year on outside
corroboration.

---

## 13. What to do next

**The immediate case for a sweep.** Every defect above was found by accident — a sentence missing from a bio, a count that looked suspiciously round, a number that couldn't be right for that league. None came from a source; all came from the plumbing. A deliberate sweep looking for those same shapes on purpose converts an unknown number of latent faults into a list.

Four questions worth asking systematically:
1. Which gates can pass without checking anything?
2. Which readers drop what they cannot parse?
3. Which claims rest on a reading nobody declared?
4. Which measurements describe a build file rather than the archive?

**Then, in rough order of value.** *Reordered 8 September on measured gain, not
impression:*
1. **PFA's awards and leaderboards** were empty and awards is now read; **leaderboards
   is still unfetched** and is five minutes of work.
2. Wikimedia Commons by club and season.
2. Media guide headshot extraction, tagged by rights.
3. The corpus inventory — 2,406 documents nobody has read.
4. Crippen's AAFC register.
5. Media guides as the fourth roster-membership source.
6. The eBay programme lineup pages — 48 of 55 carry one.

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
- **Nothing systematically revisits a refusal when new evidence arrives.** A real gap and a good future job.
