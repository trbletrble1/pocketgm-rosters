# 49 — Lelands, and the clause was there in 1923

2026-09-05. **Lelands settled in one request. The answer I gave hours ago was
wrong in both halves.**

---

## The pattern

```
https://auction.lelands.com/images_items/item_{itemid}_{n}_{imageid}.jpg
```

**No 403, no bot detection, images listed directly in the lot page.** The
cleanest of the three hosts — eBay needs the browser for lot pages, Heritage
needs the `it=product` parameter, Lelands needs neither.

Four images fetched for lot 132278, up to **1357×1800**.

## And the lot is the oldest contract in the collection

> **The National Football League — UNIFORM PLAYER'S CONTRACT**
> **Chicago Bears Football Club, Inc.** and **Walter J. Pearce**, of Providence, R.I.
> *"at the rate of **$85.00 per game**"*, season 1923
> Signed 24 August 1923 by **Geo. S. Halas**

## The correction

Report 48 said the 75/25 payment clause **"spans at least 1951–1961"** and called
it *"a league-scoped system fact with a measured start and end."*

**Both halves are wrong.** Paragraph 2 of the 1923 form, as executed:

> *"~~Seventy-five per cent (75%)~~ **Ninety per cent (90%)** after each game and
> the remaining ~~twenty-five per cent (25%)~~ **ten per cent (10%)** at the close
> of the season or upon release of the player by the Club."*

**The clause is printed on the 1923 Uniform Player's Contract — twenty-eight
years before Groza. And it is negotiable.** Pearce struck it out and took 90% per
game instead of 75%.

So it is **not a league rule with a start date**. It is a **form-level default
that individual contracts could override**, and what any given player was paid on
requires reading *his* contract, not the era's.

*My error was inferring a rule from three unamended contracts. Three men who did
not negotiate the clause are not evidence that it could not be negotiated —
that is absence of variation read as absence of the possibility of variation.*

### And it explains the 1938 form

Union City's American Professional Football Association contract carries
paragraph 1 in **nearly identical wording** to the 1923 NFL form — *"As to games
scheduled but not played the player shall receive no compensation from the Club,
other than actual expenses."* **The minor league used a form derived from the
NFL's**, which is why it looked familiar and why its structure differs from the
1951 Standard contract.

---

## A deletion is data — now twice

| | |
|---|---|
| **1923 Pearce** | 75/25 struck through, **amended to 90/10** by hand |
| **1938 Franco** | paragraph 4's release proviso **struck through entirely** |

**Reading only the printed text records the opposite of what the parties agreed,
and no OCR pass catches a strike-through.** Recorded as a rule: any contract
ingest must capture the **as-executed** text, not the form's.

That is not a transcription convenience. It is the difference between what was
printed and what was signed — and in Pearce's case it is a 15-point difference in
when he got paid, and in Franco's the presence or absence of a release mechanism.

---

## Where the fetch stands

| house | status |
|---|---|
| **eBay** | 10 of 11 live lots, **58 images**. Christiansen 404 — sold and delisted. |
| **Heritage** | 2 fetched; `it=product` confirmed full resolution. Remainder is permanent and can wait. |
| **Lelands** | pattern settled, 1923 Pearce fetched. **Gregg's three lots have no lot URL in the CSV** — they need item IDs before they can be fetched. |
| **Kayfabe storefront** | six Portland players, no item IDs. Not yet found. |

**62 images held. Nothing ingested. 13 gate suites pass.**
