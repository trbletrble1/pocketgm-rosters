# 28 — Denoting the photo set (3 of 4)

2026-09-04. Branch `dataset-design`.

**20,779 photos attached. 5,359 refused.** The refusals are the point.

---

## The source can make only one kind of claim, and it is the forbidden one

The photo set carries **no birth date, no club, no season, no id**. A filename —
`Ricky_Jean-Francois.jpg` — is the entire identity assertion available. §2.4
forbids a name as identity evidence, and the corpus proves why: **1,578 names
denote more than one person, hiding 3,710 men.**

What makes the source usable at all is narrower than a name match:

> A name that denotes **exactly one** person in the whole 40,745-person universe
> is not a name match. It is a name **plus the verified absence of an
> alternative**, and that verification is the discriminator.

Recorded as `["name", "verified_unique_in_person_universe"]`, method
`name-unique`, and declared **tier 3** — weaker than a source-native id, weaker
than name+birth_date, and resting on an assumption that is *false* for any man
who never appears in the corpus.

| | photos | |
|---|---|---|
| name denotes exactly one person | **20,779** | denoted |
| name denotes more than one | **1,263** | **refused** — they cover 2,993 men |
| name denotes nobody | **4,096** | refused |

Also written: **3,400 face-colour claims** and **3,881 face *absence* claims** —
`measured.csv` rows whose status is `no face` are an image that was processed and
yielded nothing, which is an observation, not a blank.

---

## Normalisation: measured, and declined

4,096 photos match nobody. The misses are systematic — middle initials
(`michael m_lewis`), two-part forenames (`ivy joe_hunter`), punctuation. Stripping
those would reach:

- **597** unique people — 2.3% of the set
- 207 more that land on an ambiguous name and are refused anyway
- 3,292 still matching nobody

**Declined, and recorded in the declaration as available-not-taken.** Every one of
those 597 rests on discarding the only distinguishing information the filename
carries. *Michael M Lewis* becoming *Michael Lewis* is probably the same man —
and probably is not a standard for deciding what someone looked like. The failure
mode is a face rendered on the wrong person's page with no error raised anywhere.

**A gap is recoverable. A wrong face at scale is not.** If you want the 597, it is
a ruling, not a code change.

*A correction on the way there:* I first measured the generational-suffix danger
and reported 1,579 base names that stripping `Jr`/`Sr` would merge. That was
wrong — only **6** corpus names carry a suffix at all, because StatsCrew omits
them. The 1,579 were ordinary ambiguity (eleven Mike Williamses), not suffix
merges. The conclusion did not depend on it, but the number was.

---

## The gate

`src/gate_photo_denotation.py`, two properties:

1. every denoted name resolves to exactly one person;
2. every denotation records the tier-3 discriminator, so no consumer can mistake
   a name-unique match for a source-native id.

Broken by doing the tempting thing — attaching a refused photo to the likeliest
man — both fire:

```
[FAIL] psf:Aaron_Jones.jpg -> 'aaron jones' denotes 2 men
[FAIL] psf:hidden-tier.jpg: ['name']
```

---

## One change to the store model

`Store.adopt_person()`. A store that denotes into the unified universe registers
a global id rather than minting its own — minting here would recreate exactly the
store-local collision that made `p_000190` mean three different men.

---

## State

**8 gate suites, all passing.** 12 in-store gates, 12 firing when broken.

**Media guide pull: 459 texts, 191 no-text, 0 zero-byte.** Still running.

**Next: assistants (4 of 4)**, which depends on the pull finishing, and the coach
birth-date re-measurement across decades that goes with it.
