# 25 — What a front end would hit

2026-09-04. Branch `dataset-design`.

Not a build. You said a front end is the likely direction and that building
against the real shape exposes gaps a mock never would, so this measures the
navigation you described — **league → team → season → player → coach** — against
what is actually in `build/`.

Five gaps. The first is the one that decides the others.

---

## 1. No person spans the archive, and the ids actively collide

**220 stores, one per league-season, each with its own person numbering.**

Joe Kapp, traced by his StatsCrew slug:

> **13 stores. 10 distinct person ids.**
>
> `cfl-1959 → p_000577` · `cfl-1960 → p_000571` · `cfl-1961 → p_000226` ·
> `cfl-1963 → p_000181` · `cfl-1966 → p_000190` · `nfl-1967 → p_003410` ·
> `nfl-1970 → p_001009` …

Worse than not unifying — the ids mean different men in different files:

| `p_000190` in | is |
|---|---|
| `cfl-1964` / `cfl-1966` | Joe Kapp |
| `nfl-1950` | Chick Maggioli |
| `nfl-2024` | Greg Dortch |

A front end that navigates *player → career* has nothing to navigate. Click Kapp
in 1966 and 1967 and you have two unrelated people.

**But the join key exists.** Every denotation carries
`matched_against: "statscrew:p-kappjoe001"`. So this is **a missing build step,
not missing data** — a cross-store identity pass that mints one id per slug and
follows the player/coach cross-reference. That is the single largest thing
standing between the dataset and anything browsable, and it is tractable.

*It also has to be done carefully rather than by slug alone: the slug is one
source's opinion. §2.4's discriminator order still governs, and CFL 1945–49 has
no discriminator beyond it — those seasons must stay unmerged.*

---

## 2. There are no name claims

A roster store holds exactly seven predicates:

```
birth_date · college · games_played · games_started · hometown · jersey · position
```

**No name.** The player's name exists only inside the denotation's
`source_record` string — `statscrew#roster/CFLBC-1966#Joe Kapp`.

A front end cannot render a player's name from claims. The design says names are
claims (§2, and the whole point of a person being an opaque id with no
attributes); the roster ingest never writes one. Parsing it back out of a record
identifier would be reading a key as data.

---

## 3. Coaches are head coaches only

2,363 stints, 478 men, and **236 of them also have a player record** — that part
will render well, and the player/coach duality is genuinely interesting to browse.

Assistants are absent entirely. That is the media guides, and of **2,105 indexed
guides only 28 are on disk** (all 1979). *Click a 1985 team and there is a head
coach and nobody else.*

---

## 4. Appearance: better than I assumed for the NFL, thin elsewhere, and joined on the worst possible key

26,145 photos. I assumed modern-only from the filenames and **was wrong** —
checking rather than asserting, Chick Maggioli (an obscure 1950 back) is present.
It is an all-time set.

| store | people | with a photo |
|---|---|---|
| NFL 1950 | 444 | 420 (94%) |
| NFL 1985 | 1,460 | 1,387 (95%) |
| NFL 2024 | 2,064 | 1,882 (91%) |
| **CFL 2024** | **724** | **82 (11%)** |

Of 9,472 rows in `measured.csv`, **5,131 are `no face`** — so even where a photo
exists, usable appearance colour lands at **4,341 (46%)**.

**This is what the polygon avatars are for, and the measurement says where:** not
the old NFL, which is well covered, but the CFL and the minor leagues, where the
honest render is a figure with no face data at all.

**The join is the problem.** Photos are keyed by `Firstname_Lastname.jpg` — a name
string, which is precisely what §2.4 forbids as identity evidence:

> 38,069 distinct names · **1,559 (4.1%) denote more than one person** · 3,665
> people behind them
>
> **1,245 of those ambiguous names have a photo — one photo that would be served
> as the face of 2,949 different men.**

Including, pleasingly, two Jim Thorpes (`p-thorpjim001`, `p-thorpjim002`) and
three Len Johnsons.

A front end that renders faces by name match will put the wrong man's face on
2,949 pages and never report an error. The photo set needs a denotation pass of
its own — same shape as any other source, discriminator and all — before it is
allowed to decide what anyone looked like.

---

## 5. Leagues that will render as gaps

Present: NFL/APFA 1920–2024, AAFC, AFL 1960–69, WFL, USFL, USFL2, XFL, WLAF,
UFL, UFL2, AAF, CFL 1945–2025.

Absent, and declared so rather than silently missing: **the first AFL (1926), the
second (1936–37), the third (1940–41), and NFL Europe.** StatsCrew cannot supply
them — `AFL3` resolves to the Arena Football League, which is now refused at the
fetcher.

Two more that a browsable timeline will surface as holes, both real: **CFL 2020**
(season cancelled, declared) and **CFL 1945–57 labelled "CFL" by the source
though the league began in 1958** — the back-mapping from report 22, still held
as a StatsCrew claim rather than an observed league identity. A front end
displaying "1945 Canadian Football League" would be repeating the source's error
in our own voice, which is a rendering decision worth making deliberately.

---

## In order, if it goes ahead

1. **Cross-store identity.** One person id per slug, discriminators honoured,
   CFL 1945–49 left unmerged. Nothing else works until this does.
2. **Name as a claim**, written by the ingest rather than recovered from a key.
3. **Denote the photo set** properly, so a face is attached to a person and not
   to a string.
4. Assistants, if the media guide acquisition happens.

Nothing here is a blocker on the dataset itself — every gap is a build step or an
acquisition, and none of them requires the stored claims to change.
