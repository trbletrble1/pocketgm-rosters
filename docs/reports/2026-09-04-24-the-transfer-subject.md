# 24 — The transfer subject, and a gate that passed for the wrong reason

2026-09-04. Branch `dataset-design`. Follows report 23.

Ruling taken: `("transfer", person, from_club, to_club, year)`. The other three
predicates stay league-scoped. Kapp's $50,000 is extracted.

Two things happened on the way that are worth more than the figure.

---

## 1. The shape

`inter_club_transfer_fee` moved out of `system_rules.predicates` into a new
`transfer_payments` block. `model.py` now refuses it on a league, person or
cohort subject, refuses a transfer subject that names only one club, and refuses
a person-scoped salary on a transfer subject.

Declared alongside it, three hard rules — and per report 23's own gate, each had
to name an enforcing gate before the suite would pass. Gate 12 does.

The claim, in the store:

```
("transfer", p_000064, "CFLBC", "Minnesota Vikings", 1967)
    inter_club_transfer_fee    = 50000      observed        stated_by: the court
    governing_regime           = 'rozelle'  observed        stated_by: the court
    from_club_identification   = 'CFLBC'    source_derived
```

181 figures, 181 claims, 0 refused. No existing figure changed.

---

## 2. My own gate passed for the wrong reason

Gate 12 caught every violation I threw at it. Then I broke the scope rule —
widened `TRANSFER_SCOPES` to accept a league subject — and the gate stayed
**SILENT**.

It had not survived the break. The *arity* rule caught the league subject
instead (a 3-part league subject is not 5 parts), the gate saw a `StoreError`,
and read that as correct refusal. **It would have passed with the scope rule
deleted entirely.**

This is the precedent already on the books — *a gate that fires must fire for
its stated reason* — and I wrote a gate that violated it on the same day I
extended the suite. Catching a bare exception type is not a check; it is a check
shaped like one.

Gate 12 now asserts **which** rule refused, by marker:

| subject | must be refused by |
|---|---|
| league / person / cohort | `requires a transfer-scoped subject` |
| transfer naming one club | `names BOTH clubs` |
| `salary_base` on a transfer | `payee of a transfer fee is a club` |

Broken two ways now, it fires both times, each for its own reason:

```
[FIRED] break: transfer scope widened to accept a league subject
        a league subject was refused, but by the WRONG rule -
        expected 'requires a transfer-scoped subject', got: names BOTH clubs...
[FIRED] break: arity check accepts a one-club transfer
        inter_club_transfer_fee was ACCEPTED on a transfer subject naming ONE club
```

Both breaks are in `gate_selftest.py`. 12/12 gates pass, 12/12 fire when broken.

---

## 3. The court never names the Canadian club

The subject requires both clubs. The opinion supplies one.

> "he eventually obtained clearance to play for the Minnesota Vikings when the
> latter paid **Kapp's Canadian team** $50,000 for his release"

Measured, not assumed: across the full opinion, *Lions*, *British Columbia*,
*Vancouver*, *Calgary* and *B.C.* appear **zero times**. It says "his Canadian
team" and never resolves it.

I know which club it was. Writing that in would be the identical failure this
dataset was built to prevent — my own knowledge laundered through a federal
opinion's credibility, and it would read as `stated_by: the court` forever.

So it is **derived**, in two reproducible steps:

1. The opinion states *"Kapp's last Canadian contract expired after the 1966
   season."*
2. StatsCrew CFL 1966 — swept two reports ago — carries Joe Kapp
   (`p-kappjoe001`, born March 19 1938) on **CFLBC**, and on no other 1966 club.

Anyone with the same two sources reaches CFLBC. That is the test the brief set,
and it is the difference between derived-from-sources and drawn-from-knowledge.

**Recorded with its own caution:** Kapp appears on *both* CFLBC and CFLCGY in
1961, so club-per-season is not single-valued for him in general. 1966 happens to
be unambiguous, and the derivation would not hold for an arbitrary year.

**And the derivation is a claim, not a footnote.** `from_club_identification` sits
on the transfer subject as `source_derived` with its basis. Without it a reader
sees `CFLBC` inside a subject whose other claims say *stated_by: the court*, and
concludes the court named it. Provenance records origin, not last hop — including
when the thing derived is part of a subject rather than a value.

*The sweep paid for itself here in a way I did not anticipate: the CFL data
existed to resolve this only because the sweep ran three reports ago.*

---

## 4. State

12 gates · 12 pass · 12 fire when broken · three standalone gates passing ·
declaration keys unread 0 of 177 · 181 salary figures, 0 refused.

Owed, unchanged: assistants from the media guides (2,105 indexed, 28 on disk —
acquisition decision is yours); QB ratings from statistics; the Raiders/Rams
per-row confidence field; the Elway document; Staudohar; the Mackey Archives
request.
