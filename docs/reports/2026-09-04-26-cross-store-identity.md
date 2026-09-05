# 26 — Cross-store identity (groundwork 1 of 4)

2026-09-04. Branch `dataset-design`.

**207,180 local person records across 220 stores collapse to 40,631 people.**

Joe Kapp is now `P_004829`, one man across twelve stores — CFL 1959–66 into NFL
1967–70. Before this he was ten different people, and `p_000190` meant Kapp,
Chick Maggioli or Greg Dortch depending on which file you opened.

---

## What may join two records, and what may not

**May: the source's own identity assertion.** A shared StatsCrew slug. This is
tier A in §2.4 — it follows what the source says, not a string we matched.

**May: a recorded bidirectional `p-`/`c-` cross-reference.** 236 applied, merging
233 people who were both player and coach. Otto Graham is now one person across
eleven stores holding both `p-grahaott001` and `c-grahaott001`.

*This was nearly missed.* The cross-reference is stored as a **claim**
(`also_played`), not a denotation. My first pass read denotations and applied
**zero** cross-references while reporting success — a silent no-op that looked
exactly like "there are none." Caught only because 236 was a number I already
knew from report 21.

**May not: a name.** Ever. And not, it turns out, a name plus a birth date
either.

---

## The tier-2 merge is refused, and the measurement is why

223 records carry no source-native id — Coaching Tree entries and court figures,
keyed `name`+`birth_date` or `name`+`club`+`case`. §2.4 ranks birth date as
discriminator #2, so merging them on it looked admissible.

It is not. Building the index from actual `birth_date` claims across all 40,638
identified people:

> **39 `name`+`birth_date` keys denote more than one StatsCrew slug.**
>
> `('eric williams', 'February 24, 1962')` → `p-willieri002`, `p-willieri003`
> `('rod jones', 'March 31, 1964')` → `p-jonesrod002`, `p-jonesrod003`
> `('michael carter', 'May 7, 1999')` → `p-cartemic003`, `p-cartemic004`

A same name *and* a same birth date is still two men, 39 times over. Merging on
tier 2 would have conflated them silently.

**And a second defect the same measurement exposed:** `('mcdonald', 'None')` and
`('bill miller', 'None')` were forming keys. A missing birth date was being used
as a *value*, so every man with no birth date matched every other man of his
name. That is an absence doing the work of an observation — the thing §3.4
exists to prevent — and it is why the key set must exclude absences rather than
stringify them.

So the 223 stay separate, each its own person. **This is also what makes CFL
1945–49 safe without a special case:** birth date there is 32.9% and college
56.7%, so nothing but the slug is available — and nothing but the slug is used.
Your constraint is satisfied by the general rule rather than by an exception that
could rot.

---

## What unification surfaced

**6,923 people appear in more than one league.**

| leagues | people |
|---|---|
| CFL + NFL | 1,755 |
| NFL + USFL | 647 |
| AFL + NFL | 473 |
| NFL + XFL | 343 |
| NFL + UFL | 319 |
| NFL + WFL | 304 |
| AAFC + NFL | 241 |
| APFA + NFL | 198 |

None of these careers existed as a career before today. The CFL/NFL figure is the
one I did not expect at that size, and it is only visible because the CFL sweep
ran four reports ago.

**A check on the source's own identity, which came back clean:** zero slugs carry
more than one birth date across all 220 stores. Had StatsCrew conflated two men
under one slug, this is where it would show, and it does not.

---

## The gate

`src/gate_identity.py`, three properties over every global person:

1. no group of more than one record without a source-native id;
2. no group holding two different slug bodies;
3. the regression case — Kapp, Maggioli and Dortch must remain three people, and
   Kapp must span more than one store.

Broken by reinstating the exact pre-fix behaviour (merge the three men who shared
`p_000190`, and add a name-only merge), all three fire independently:

```
[FAIL] P_BADNAME: 2 local records, no slug
[FAIL] P_004829: ['p-kappjoe001', 'p-maggichi001', 'p-dortcgre001']
regression p_000190 (Kapp / Maggioli / Dortch) still distinct: NO
```

---

## Note on what this is not

`build-reports/identity.json` is a **mapping**, not a rewrite. No store was
altered and no claim moved. A consumer resolves a local id to a global one
through it. That keeps the per-season stores exactly as ingested, which matters
because the mapping is a derived artefact and will be rebuilt whenever a source
is added.

**Next: name as a claim (2 of 4).** The media guide text pull is running in
parallel — 52 texts, 28 no-text, 0 zero-byte so far.
