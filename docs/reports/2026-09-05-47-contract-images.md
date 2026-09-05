# 47 — Contract images fetched, and holding one is not reading it

2026-09-05. **6 images fetched, 0 failed. Both hosts open — no allowlisting needed.**

---

## Access, settled in two tests

| host | result |
|---|---|
| `i.ebayimg.com` | **200.** `s-l1600` is the ceiling — `s-l2400`, `s-l1200`, `s-l960` all return **identical bytes**. The seller's upload sets the limit. |
| `dyn1.heritagestatic.com` | **200.** **`it=product` IS the full version** — 1650×3000 and 1767×3000 measured. Every other `it=` value returns HTTP 400. |

You were right to ask for one test before thirty fetches. **There is no better
Heritage parameter**; `product` is it.

Held in `pgm3-sources/contracts/`, named `1951_Lou_Groza.jpg`, hash-pinned in
`manifest.json` alongside URL, lot, byte count, dimensions and fetch date.

## The Groza contract reads cleanly, and I read it

Not Ryan's reading relayed — **mine, from a document now on disk.**

> NATIONAL FOOTBALL LEAGUE **STANDARD PLAYERS CONTRACT**
> CLEVELAND BROWNS INC. — **LOUIS R. GROZA**, 138 Edgewood Drive, Berea, Ohio
> season commencing in **1951**
> *"the Club promises to pay the Player each football season during the term of
> this contract the sum of **$10,800.00**"*
> Signed Paul Brown 6-19-51; Lou Groza 6/19/51; approved **Bert Bell** 6/23/51.

## And a structural finding on the standard form

The same clause appears in both contracts read:

> **"75% of said salary in weekly installments** commencing with the first and
> ending with the last regularly scheduled League game played by the Club during
> such season **and the balance of 25% of said sum at the end** of said last
> regularly scheduled League game."

**The archive holds 182 salary figures and no payment structure at all.** This is
printed on the standard form, so it plausibly governs every contract of the era —
which makes it a **league-scoped system fact**, not a per-player one. Recorded,
not yet claimed: it wants its own predicate and a check of how far the clause
persists before anything is written.

---

## The finding that matters: holding an image is not reading it

**Leo Sugar 1961 is 578×949, and the figure cannot be resolved.**

It reads **`13,?00.00`**. The middle digit could be 2, 8 or 0 — the typewriter
strike has filled in. And there is no better image: every eBay size variant for
that lot returns byte-identical data, so 578×949 *is* the seller's original.

**So possession does not confer legibility, and the two must not be conflated.**
The acquisition is `transcribed` because the document is held; the *confidence* is
a separate axis and belongs to the image, not to the fact of holding it.

> **A transcription carries the legibility of the image it was read from. An
> uncertain digit travels as uncertain.**

That is the `(date approximate)` rule arriving from a different direction, and the
same family as the 1980 estimated column and the 1950 passer ratings — a value
presented at a confidence its derivation does not support. Sugar's figure stays
Ryan's reading, marked uncertain; **I cannot confirm the middle digit and will not
pretend to.**

## Rights, recorded as a constraint

An auction image belongs to the auction house. **Held for private reference and
citation only** — the dataset cites the figure and the lot, never republishes the
scan. `pgm3-sources` is outside the repo and stays there. Declared in
`salary_conventions.json :: contract_images.RIGHTS`, alongside the eBay API note.

---

## What I need to finish this

**The 51-row list with lot URLs.** I have four eBay direct URLs and two Heritage
lot patterns; the remaining ~45 resolve from listing pages I do not have.

**Priority as you set it:** eBay live listings first — those vanish when the lot
sells, and the Portland Storm batch especially. Heritage and Lelands are stable.
**Lelands' pattern is untested**; Forrest Gregg's three lots would settle it in one
request, the way `it=product` settled Heritage.

`fetch_contracts.py` takes the list as-is: player, season, house, URL. Everything
else — hashing, dimensions, atomic write, rate limit, manifest — is built and
proven on these six.

**13 gate suites pass.**
