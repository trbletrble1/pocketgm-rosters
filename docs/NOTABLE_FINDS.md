# Notable finds

Facts about specific people that turned up in passing and would otherwise be lost.
These are **not claims yet** — they're relayed to the master session in
conversation, so under §3.7 none of them can enter the store as-is. Each needs a
retrievable source before it becomes anything.

**What this file is for:** the input to a `notable` claim layer, if one is built.
A bio generated purely from statistics can say a man played three games in 1945.
It cannot say why that mattered. Where a story is documented, the structure should
be able to hold it — attributed, sourced, and clearly separate from derived facts.

**Format:** person, what's claimed, where it came from, and what would be needed to
verify it.

---

## Jack Sanders — Philadelphia Eagles, 1945

Lost part of his left arm in an underwater explosion in March 1945. Signed with
the Eagles that August and became **the first World War II disabled veteran to
sign an NFL contract**. Played three games in the 1945 season.

For the team's first game of 1945, the **United States Armed Forces paid to send
22,000 amputees to watch him play**.

**Status:** relayed by Ryan. **Source chain now known:** Philadelphia Eagles
History group on Facebook, citing *The Philadelphia Eagles Photo History Book*
(shibevintagesports.com). So it is **two removes** — a book, retold in a group
post, relayed in conversation — and the book itself is a retrospective photo
history rather than a contemporary document.

**In the archive already:** he should appear in the 1945 Philadelphia roster from
StatsCrew — three games, so `games_played` should carry it.

**To verify, in order of preference:** the 1945 or 1946 Philadelphia Eagles media
guide, which may be among the 1,803 texts already held — a contemporary primary
source rather than a retelling. Then contemporary newspaper coverage of the Eagles'
1945 season opener, where the 22,000 figure would have been reported at the time.
Then the photo history book itself, which is at least a named publication with a
page that could be cited.

**The 22,000 figure specifically wants checking.** Round numbers in retellings are
attractors — the same reasoning that rejected Archie Manning's $600,000 as
corroboration. A contemporary report would settle whether it was 22,000 or "about
twenty thousand" grown into a number.

**Why it matters beyond the story:** it's the clearest example so far of a person
whose significance is entirely absent from every statistical source. A bio built
from claims would say "played three games for the Philadelphia Eagles in 1945" and
stop. There is some unknown number of Jack Sanderses among the 40,745 people in
the archive.

---

## Earle "Greasy" Neale

Played eight seasons of major league baseball for Cincinnati and hit .357 in the
1919 World Series — the one the White Sox threw. Played early pro football in the
1910s, including for the Canton Bulldogs alongside Jim Thorpe. Coached the
Philadelphia Eagles to back-to-back NFL championships in 1948 and 1949. Pro
Football Hall of Fame.

**Status:** general knowledge, stated by the master session. Not sourced.

**Why it's here:** he's the case that proves the bio phrasing was worth getting
right. The archive renders him as *"appears in the record as a coach, not a
player"* — which is true of the record and not of the man, because his playing
career was in leagues this archive doesn't hold. He's also the argument for a
random-person feature: landing on him is the whole appeal of an archive.

---

---

## The war years — a cluster, not single facts

**Source:** *Football and the NFL During World War II*, Thalia Ertman, Friends of
the National World War II Memorial, 13 September 2019.
`wwiimemorialfriends.org/blog/football-and-the-nfl-during-world-war-ii`

A charity's blog post, so secondary and uncited — but it names people and events
specifically enough to verify individually, and it explains the shape of an era the
archive already holds structurally.

### League-level facts

- **994 NFL personnel served** in the armed forces.
- **21 NFL men died** — 19 active or former players, an ex-head coach, a team
  executive.
- **Three with NFL connections earned the Medal of Honor**, two of them players.
- War Bond sales at NFL games raised **$4,000,000 in 1942 alone**. Curly Lambeau,
  Cecil Isbell and Don Hutson received treasury citations for **$2,100,000 in a
  single night** at a Milwaukee rally.
- 15 exhibition games donated **$680,384.07** to service charities.

### People to attach claims to

- **Al Blozis**, Giants tackle 1942–44 — killed by machine-gun fire in the Vosges
  Mountains, **six weeks after playing in the 1944 NFL Championship Game**.
- **Jack Lummus**, Giants end 1941 — Medal of Honor, posthumous, died at Iwo Jima.
- **Maurice Britt**, Lions end 1941 — Medal of Honor, Army, North Africa and Italy.
- **Mario "Motts" Tonelli**, Cardinals fullback — captured at Bataan April 1942,
  survived the Bataan Death March and nearly three and a half years as a POW in
  Japan, weighed 90 pounds at the war's end, **and returned to the NFL with the
  1945 Chicago Cardinals**.
- **Kenny Washington** — served on the USO tour as a sports ambassador; signed by
  the Rams 21 March 1946, breaking the NFL colour barrier a year before Robinson.
  **Already in the archive**: he's on the 1944 San Francisco Clippers roster.

### Structural facts the archive already holds and can now explain

- **Cleveland Rams suspended play for 1943** — insufficient players.
- **The Steagles**, Eagles/Steelers merged for 1943, already rendering correctly in
  the bios per-season.
- **Card-Pitt**, Steelers and Cardinals merged 1944, went 0–10, derided as "the
  Carpets."
- **Boston Yanks and Brooklyn Tigers merged for 1944** as "the Yanks," no city.
- **Brooklyn 1943** had only seven players available; retired men, including three
  future Hall of Famers, signed back up.

**Why this cluster matters:** the bios already render war-year gaps honestly —
*"He appears on a roster in 1941, then not again until 1946."* This is the
explanation for thousands of those gaps, and for the strange club names the archive
holds without comment.

**To verify:** each person is individually checkable — Medal of Honor citations are
public record, and the merged-club seasons are already in the roster data. The
league-level dollar figures would need a contemporary source.

---

## Stan Kostka — Brooklyn Dodgers, 1935 — VERIFIED, with the causal claim corrected

**The salary holds. The chronology in the Facebook post does not.**

### Salary — good evidence

```
  Club              Brooklyn Dodgers (NFL)
  Signed            25 August 1935
  Salary            approximately $5,000 for the season
  Structure         season salary, NOT per game
  Bonus             $500, per Kostka's own later recollection
  Status            reported as the highest-paid ROOKIE in the league
```

**Contemporary source:** a United Press report from during the 1935 season called
him the league's highest-paid rookie and described the salary as **"close to
$5,000."** It also put ordinary backs at **$200–$250 per game** — which is itself a
useful era datapoint and consistent with the per-game contracts already held
(Nagurski $225 in 1932, Stonebraker $225 in 1942).

**Retrospective source:** Kostka told historian Cliff Christl on **28 March 1979**
that he "got $5,000 and a $500 bonus." That's the player describing his own
negotiation — good, and still a recollection rather than a contract.

**Enter as two claims, not one.** ~$5,000 season salary from the contemporary UP
report; the $500 bonus separately, marked retrospective.

**Do not call it a record without qualification.** "Highest-paid rookie" is what the
1935 source says. "Largest contract in professional football history" is the modern
formulation and it isn't established — see the Bell offer below, which was higher.

### The offer, which belongs in the offer category

**Bert Bell, Philadelphia — $6,000 for 1935, offered and declined.**

From Bell's own 1957 Associated Press interview: Kostka told him his best standing
offer was $3,500; Bell offered $4,000; when Kostka still hesitated Bell went to
**$6,000 if he would sign immediately**. Kostka declined.

**Same class as Cannon, Robinson and Flowers** — contracted or offered, never
earned. And an unusually precise 1935 market datapoint.

**Kostka's own account of the bidding:** offers wired around $3,500, and he would
tell one club another had offered $4,000 to push it up. Named the Bears, Packers,
Giants, Brooklyn and Pittsburgh as serious suitors.

### The causal claim — corrected

**The Facebook version is chronologically impossible.** NFL owners approved Bell's
draft proposal on **19 May 1935**. Kostka didn't sign with Brooklyn until **25
August**, three months later. So the $5,000 contract cannot have caused the draft.

**But the underlying story survives in better form.** Bell said it was his *failed
pursuit* of Kostka — not the eventual Brooklyn deal — that convinced him. He went
to Minneapolis personally, went $4,000 to $6,000, failed, and said he decided on the
way home that the league needed a system giving every club equal access to incoming
talent. That fits the chronology if the visit preceded the May meeting.

**And Kostka agreed.** In 1979 he told Christl flatly: *"I was the instigator of the
draft."*

**Evidence hierarchy for the causal claim:**

- **Very strong** — Bell wanted the draft to stop richer clubs monopolising college
  talent. The May 1935 resolution establishes the mechanism and league histories
  are consistent.
- **Strong but retrospective** — Bell connecting his failed Kostka negotiation to
  the idea. A 1957 recollection, 22 years after.
- **Corroborating, retrospective** — Kostka's own 1979 claim.
- **Not found** — any May 1935 report or the league minutes naming Kostka as the
  cause. The minutes record Bell's proposal and its mechanics and don't say why.

**The honest phrasing:** the ongoing bidding war and Bell's failure to sign him may
have been a catalyst for the May proposal. The August contract was not.

**Sources:** packers.com, *1936 NFL Draft: Oral history — Bert Bell's brainchild*
(carries the UP report, the Christl interview and the 1957 AP account);
thedailygopher.com for the signing date.

