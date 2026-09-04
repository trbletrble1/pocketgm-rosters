# The 1950 ingest, and why one league cannot prove the four states

**2026-09-04. Report 09.** Answers three questions from the master session.
Build evidence in `dataset/build-reports/` (the full stores stay out of the repo —
see below).

---

## 1. Did the 1950 ingest run? Yes. My setup hid it.

It ran and it is clean. **`dataset/build/` was gitignored**, so the output was
invisible from outside this machine — that is why there was no `build/` to see.
My error, and the fix is in: a committed **`dataset/build-reports/`** now carries
the resolution summary and the contested list.

**The full claim stores stay out of the repo deliberately.** `nfl-1950.json` is
3,252 claims whose values are extracted StatsCrew content, and committing it is
the same shape as the `sources/` ruling of 2026-09-02 — republishing someone
else's material under this repo's name. Counts, distributions and our own analysis
are ours and are committed.

    NFL 1950   13 teams   460 rows   446 persons   3,252 claims   492 denotations
    WFL 1974   14 teams   901 rows   832 persons   6,226 claims   901 denotations

**Denotation match rate 1.0000 on both** — 460/460 and 901/901. Asserted on the
**rate**, not the count, because a fallback makes a count check dead by
construction.

**Identity through slugs, cross-reference followed, not string-matched.** 32 men
in the 1950 NFL both played and coached and carry a bidirectional `p-`/`c-` link
— Otto Graham, Bulldog Turner, Abe Gibron, Buster Ramsey, Lou Rymkus, John
Sandusky among them. Each got **one person id and two careers**, which is design
shape 8. The link was followed; the matching slug body was never treated as
evidence.

**13 mid-season movers** fell out for free — one slug, two clubs, two stints. No
coin flip, because the dataset holds both.

## 2. Did all four bases come back distinct on real 1950 data? No — and you called it.

**Not from 1950 alone.** Here is what NFL 1950 actually produces:

| predicate | observed | absent | unknown | contested |
|---|---|---|---|---|
| birth_date | 446 | | | |
| college | 446 | | | |
| games_played | **460** | | | |
| games_started | 460 | | | |
| jersey | 460 | | | |
| hometown | 445 | **1** | | |
| position | 435 | | | **11** |
| also_coached | 32 | | **414** | |

All four counts appear — but **the distinction that matters does not.** `unknown`
and `absent` never co-occur in a single predicate, so "column missing entirely"
and "column present, cell blank" are not demonstrably distinguishable from this
league. And `games_played` in 1950 **never reads zero**: minimum 1, maximum 12. A
man on a 1950 roster page always played.

So a four-state claim resting on 1950 alone would have been a vacuous pass of
exactly the kind the gate exists to prevent.

**Report 06 said the interesting case is the minor leagues, so I ingested WFL
1974.** The declaration puts its games-played fill at 14.9%.

| WFL 1974 predicate | observed | absent | unknown |
|---|---|---|---|
| games_played | 195 | **706** | |
| **games_started** | **64** | **756** | **81** |
| jersey | 809 | 92 | |
| hometown | 775 | 57 | |
| birth_date | 827 | 5 | |

**`games_started` shows three bases in one predicate**, and the 81 `unknown` are
precisely the players on **WFLCHA and WFLSHR**, whose roster pages carry no `GS`
column at all. The declaration's `column_absent_from_page` rule fires: those are
**one declaration fact, not 81 absence claims**, so no claim is written and
resolution correctly returns `unknown` — while the 756 blank cells in a column
that exists become absence claims and return `absent`.

**That is §9.6 state 1 against state 2, in real data, distinguishable.**

Corpus totals: **observed 7,518 · absent 1,617 · unknown 495 · contested 11.**

### A bug in my own instrument, found on the way

The first run reported `unknown: 0` everywhere — and that was **my resolver, not
the data.** It enumerated subjects *that have claims*, so a stint with no
games-started claim was invisible to the loop. **A distribution computed over
subjects-that-have-claims can never report `unknown`, by construction.**

Fixed by making the store record a **subject universe** — what exists, claimed or
not — and resolving over that. `Store.declare_subject()` is now called for every
person, person-season and stint the ingest sees.

### And the gate's selftest gave me a false FIRED

Running the real-data gate against NFL 1950 alone exited 1, which looked like the
gate correctly failing. It was a `ModuleNotFoundError` — the variant ran from the
wrong directory. **An anchor that fails for the wrong reason**, and it nearly went
into this report as a pass. Re-run properly, it fails for the right reason:

    FAIL: no single predicate shows BOTH unknown and absent.
          'column missing entirely' and 'column present, cell blank' are
          then not demonstrably distinguishable in the built data.

## 3. Are report 06's findings in the declaration? Yes, as data.

Not in a report only. `declarations/statscrew.json`, and the ingest **reads**
them rather than hardcoding:

    "jersey": {
      "kind": "per_era",
      "measured": {"APFA-1920": 60.4, "NFL-1925": 77.3, "NFL-1930": 87.2,
                   "NFL-1935": 97.3, ...},
      "column_absent_entirely": ["APFA-1920"],
      "usable_from": 1935,
      "verdict": "NOT usable as a discriminator before ~1935"
    }

    "games_played":  { "kind": "per_league",
                       "measured": {"NFL":100.0,"CFL":100.0,"USFL":76.9,"WFL":14.9} }
    "games_started": { "kind": "per_league",
                       "measured": {"NFL":100.0,"USFL":65.7,"CFL":4.7,"WFL":4.7} }

The `kind` field is the load-bearing part: **`per_era` and `per_league` are
different scopings**, and a completeness gate that used one for the other would
read the WFL as catastrophically broken. `discriminators` carries a matching
`era:pre-1935` scope that **excludes jersey**.

The WFL run is the proof it works: three teams reported `columns absent for this
era/league` and the ingest wrote no claims for them rather than 81 identical
absences.

## The contested value survived the round trip

**11 contested positions in NFL 1950**, all mid-season movers whose two clubs list
them differently in the era-native vocabulary:

| | club A | club B |
|---|---|---|
| p_000136 | `K` | `FB` |
| p_003655 | `LDH` | `RS-LOH` |
| p_000550 | `LDT` | `ROG` |
| p_000028 | `MLB` | `LB` |
| p_000010 | `QB` | `QB-K` |
| p_000649 | `RDH` | `ROH` |

**Neither value was chosen.** `basis: contested`, both claims retained, and the
export will have to decide — which is where that decision belongs. `K` against
`FB` is the one that will bite a PGM3 export hardest.

## State

    dataset/declarations/   statscrew.json, media-guides.json
    dataset/policy/         resolution.json
    dataset/src/            model, fetch, ingest_season, resolve_store,
                            gates, gate_selftest, gate_real_bases
    dataset/build-reports/  resolution-summary.json, contested-nfl-1950.json
    dataset/build/          full stores — on disk, NOT committed

    python3 src/gates.py            7/7 pass
    python3 src/gate_selftest.py    7/7 fire when broken
    python3 src/gate_real_bases.py  four bases in real data, states 1 and 2 distinct

**Next:** export 1950 to PGM3 and gate it. The era-native position vocabulary and
those 11 contested positions are the two things that will test whether the shape
holds.
