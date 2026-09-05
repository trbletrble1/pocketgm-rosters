# 45 — The English labels, and a source that will not let me in

2026-09-05.

---

## 1. Position labels, written as a build artefact

`export/position_labels.json` — deliberately **not** in `declarations/`, because a
declaration describes a source and this describes nothing but our own opinion.

**It carries no `source_id`, no `acquisition`, no `stated_by`.** Those are the
fields that would let a consumer treat it as evidence, and their absence is the
point.

**Written compositionally, not as 224 strings.** The codes are built from atoms
with side and phase prefixes — `L`/`R`, `O`/`D` — joined by `-`, `/` or `,`. So
`ROE-RDE` expands through the rules rather than through a lookup:

> **`ROE-RDE` → right offensive end / right defensive end**
> **`LOG-ROG` → left offensive guard / right offensive guard**
> **`RILB` → right inside linebacker**

**53 atoms cover all 224 characterised codes**, and the same rules reach the 1,818
rarer ones. Composing also makes the guesswork **visible as rules** instead of
hidden in a table — and six atoms I am least sure of (`FW`, `LONG`, `D`, `B`,
`DS`, `RS`) are flagged in the file so a reader discounts those rather than
trusting it uniformly.

### The gate

`gate_labels_are_not_evidence.py`, two properties from your instruction:

1. **Nothing may cite it.** No store references the file, and the file declares
   none of the fields that would make it citable.
2. **It must not overwrite the code.** Every position claim still carries what the
   source printed.

> **171,087 position claims checked, 0 without a source code, 0 stores
> referencing the label map.**

Broken both ways — adding `source_id` to the file, and writing a claim whose value
is `"right offensive end / right defensive end"` instead of a code — it fires for
each, by name.

---

## 2. prosportstransactions.com — characterised, not entered

**I could not reach it, and I did not try to get around what stopped me.**

| | |
|---|---|
| scripted request | **HTTP 403 Forbidden** |
| browser | Cloudflare: *"Performing security verification … protect against malicious bots"* |

I stopped there. **Bypassing bot-detection is not something this project does**,
and the data being genuinely useful does not change that. Everything below came
from the **Wayback CDX index** — a different service, requiring no evasion — and
none of it is content.

### What the structure says

**14,311 archived URLs.** Your note about compilation order is visible in them:

| sport | URLs |
|---|---|
| **basketball** | **9,604** |
| hockey | 2,019 |
| **football** | **1,613** |
| baseball | 735 |
| soccer | 280 |

Football sections: `Search` 856, `DraftTrades` 391, `Logos` 359.

**It is a query interface, not a page tree.** There are no per-player pages to
enumerate — everything arrives through `SearchResults.php`, paginated in blocks of
25. That rules out the CDX-then-fetch method that worked for Pro Football
Archives.

### The fields, from the form's own parameters

| parameter | |
|---|---|
| `Player`, `Team`, `BeginDate`, `EndDate` | who and when |
| **`PlayerMovementChkBx`** | trades, signings, waivings — **785 of 804 archived queries** |
| `InjuriesChkBx`, `ILChkBx` | injuries, injured list |
| `DisciplinaryChkBx`, `LegalChkBx`, `PersonalChkBx` | conduct |
| `NBADLChkBx` | **a basketball field, appearing in football URLs** |

That last one matters: **the form is shared across sports**, so the checkbox list
is not evidence of what the football data actually contains.

### The question that decides everything is still open

**How far back football goes: unknown.**

The tempting answer is in the data — archived queries carry `BeginDate` values
from **1920 to 2021**. That is what people **typed into a form**, not what the
database returned. Reading it as coverage would be inferring content from a
request, which is report 38's error in a new place.

**One search on the live site with a 1920s date range settles it.** That is a
minute of Ryan's time and I cannot do it.

### The ranking, recorded and wired

Your caution is now `policy/resolution.json :: source_rank`:

> **secondary compilation, rank 1, against primary's rank 3.** Where it disagrees
> with a court record or a contract, **it loses**. It may corroborate a primary
> source, and may stand alone where nothing primary exists, but it never outranks
> one.

Verified: `rank(prosportstransactions)=1`, `rank(courts)=3`, and an unranked
source returns **`None`** rather than a floor — resolution must refuse rather than
assume.

**Nothing has been taken from this source.**

---

**11 gate suites pass.**
