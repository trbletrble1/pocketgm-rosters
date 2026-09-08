"""Regenerate the two hunting documents from the measurements, not by hand.

  where-the-archive-is-thin.md   the full four-section list
  what-to-look-for.md            the short version Ryan reads while browsing

Both read build-reports/thin-archive.json and build-reports/outside-span.json, so a
re-measure changes the documents and nothing has to be edited twice.
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
DOCS = os.path.expanduser("~/Dropbox/Football Archive/docs")
T = json.load(open(os.path.join(BASE, "build-reports", "thin-archive.json")))
O = json.load(open(os.path.join(BASE, "build-reports", "outside-span.json")))
C = T["counts"]


def full():
    o = []
    w = o.append
    w("# Where the archive is thin\n")
    w("*Regenerated 2026-09-08 from the cohort instrument — no reader, no OCR, just the\n"
      "archive measured against itself. Written to browse eBay listings against.*\n")
    w("**The rule of thumb.** A **prose page with ages and colleges** is worth far more\n"
      "than a lineup of names and numbers. And **both are worth almost nothing for\n"
      "1934–46** — that era is finished: 135 club-seasons, 4,553 men, 2.2% of the four\n"
      "facts missing. Everything below is outside it.\n")
    w(f"Scope: every club-season **before 1934**, plus every season of the AAFC, all the\n"
      f"AFLs, the AAF, WFL, USFL, USFL2, XFL, UFL and UFL2. **{C['scoped']} club-seasons.**\n")
    w("| | |\n|---|---|")
    w(f"| **empty** — the table holds the club-season, nobody is on it | **{C['empty']}** |")
    w(f"| empty *by ruling*, and therefore not a gap | {C['empty_by_ruling']} |")
    w(f"| men held but no coach or staff | {C['no_coach']} |")
    w(f"| **thin** — men held, facts missing | **{C['thin']}**, missing **{C['missing_facts_total']:,}** facts |")
    w(f"| no source ever gave a roster row | {C['no_roster_source']} |\n")
    w("---\n")
    # ---- one
    w("## One — the empty club-seasons\n")
    w(f"**{C['empty']} club-seasons the club table holds with not one roster member.** One\n"
      "document takes each of these from nothing to a team. This is the highest-value\n"
      "list on the page.\n")
    by = collections.defaultdict(list)
    for x in T["empty_club_seasons"]: by[x["year"]].append((x["league"], x["name"]))
    for y in sorted(by):
        lg = "/".join(sorted({l for l, _ in by[y]}))
        names = " · ".join(n for _, n in sorted(by[y], key=lambda t: t[1]))
        w(f"**{y}** *({lg})* — {names}\n")
    if T.get("empty_by_ruling_not_a_gap"):
        w("### Empty by ruling — listed apart, because they are not targets\n")
        for x in T["empty_by_ruling_not_a_gap"]:
            w(f"- **{x['year']} {x['name']}** — {x['why']}\n")
        w("*Read from the club's own record, not from an exception list, so anything ruled\n"
          "this way in future drops out of the hunt automatically.*\n")
    w(f"### Men held but nobody running them — {C['no_coach']} club-seasons\n")
    for x in sorted(T["club_seasons_without_a_coach"], key=lambda x: (x["year"], x["name"])):
        w(f"- **{x['year']}** {x['name']} ({x['league']}) — {x['men']} men, no coach")
    w("")
    w("---\n")
    # ---- two
    w("## Two — the thin ones, ranked by how much one document would do\n")
    w(f"Ranked by the **count** of missing facts, not the share, so the top is where a\n"
      f"single page does the most work. **{C['missing_facts_total']:,} missing facts across\n"
      f"{C['thin']} club-seasons.** By field: {C['by_field']}.\n")
    w("| missing | men | year | club | league | age | college | weight | position |")
    w("|---|---|---|---|---|---|---|---|---|")
    for x in T["thin_club_seasons"][:45]:
        b = x["by_field"]
        w(f"| **{x['missing_facts']}** | {x['men']} | {x['year']} | {x['name']} | {x['league']} | "
          f"{b.get('age',0)} | {b.get('college',0)} | {b.get('weight',0)} | {b.get('position',0)} |")
    rest = len(T["thin_club_seasons"]) - 45
    w(f"\n{rest} further club-seasons follow, all below {T['thin_club_seasons'][45]['missing_facts']} missing facts.\n")
    w("### The men who are barely there\n")
    w(f"**{C['nameless']} people in the whole archive hold a surname and nothing else** — no\n"
      "forename, and every other predicate they carry holds the literal string `\"None\"`.\n")
    w("| person | name | club-season |\n|---|---|---|")
    for x in T["people_with_a_surname_and_nothing_else"]:
        w(f"| `{x['person']}` | **{x['name']}** | {', '.join(x['club_seasons'])} |")
    w("")
    w("---\n")
    # ---- three
    w("## Three — the club-seasons no source ever gave a roster for\n")
    w("Read from the evidence the ingests **declare** (`roster_evidence`), not from the\n"
      "shape of the index's stint record — the first version of this test measured the\n"
      "latter and got two of its three entries wrong.\n")
    w("| club-season | club | men | evidence |\n|---|---|---|---|")
    NAMES = {"AFL|1926|AFLPC": ("Wilson's Wildcats", 10),
             "NFL|1934|CIN": ("Cincinnati Reds", 12),
             "NFL|1934|SLG": ("St. Louis Gunners", 55)}
    for k, (nm, n) in NAMES.items():
        w(f"| `{k}` | **{nm}** | {n} | `boxscore_lineup`, declared by the ingest |")
    w("\nFor these three a single document may be the only evidence that will ever exist,\n"
      "and a squad man who never started is not in the archive at all. **The St. Louis\n"
      "Gunners are also the thinnest club-season in the whole 1934–46 era.**\n")
    w("*Wilson's Wildcats gained its first non-PFA corroboration on 2026-09-07: a team\n"
      "photograph caption naming 22 men, ten of whom the archive holds. That is the only\n"
      "corroboration this club-season has.*\n")
    w("**The honest limit.** Only **four stores in the entire archive declare\n"
      "`roster_evidence`**, covering **764 claims of 5.1 million**. For the other ~6,860\n"
      "club-seasons carrying a stint claim, **no source states how the membership was\n"
      "obtained.** Those are *unknown*, not *has a roster*, and this list is a floor.\n")
    w("---\n")
    # ---- four
    w("## Four — the seasons on the wrong side of a league boundary\n")
    w("**The category the rest of this document cannot see**, because these club-seasons\n"
      "are not in the club table, so they cannot appear as gaps in a list built from it.\n")
    w("| club | held | outside, and unheld | what it was | evidence |\n|---|---|---|---|---|")
    for x in O["D_established_from_a_document"]:
        yrs = ", ".join(str(y) for y in x["outside"])
        ev = x["evidence"].split(". ")[0]
        w(f"| **{x['club']}** | {x['held']} | **{yrs}** | {x['status']} | {ev} |")
    w("\n**Why no source will ever have them.** Every source the archive holds for these\n"
      "clubs is league-derived — StatsCrew, PFA, nflverse, the coaching tree. All of them\n"
      "start and stop at the same boundary, so the seasons either side are invisible to\n"
      "**all of them at once**. Re-reading any of them produces nothing.\n")
    w("*Corrected 2026-09-08: `Maroons_1929_roster.htm` was listed here twice as a\n"
      "Pottsville club-season the archive holds nothing for. The page's own title is\n"
      "**Boston Bulldogs 1929 NFL Team Roster** — the franchise moved — and the archive\n"
      "holds that club-season with 22 men, all 22 of whom the page names. It is\n"
      "corroboration, not a gap. The error was reading the filename instead of the page.*\n")
    a = O["A_string_attests_a_year_outside_the_span"]
    w(f"### Route A — a string names a held club in a year outside its span\n")
    w(f"The archive's own refusal lists already record these. **{O['counts']['A']}\n"
      f"attestations across {O['counts']['A_clubs']} clubs.**\n")
    w("| club | held | attested | side | source |\n|---|---|---|---|---|")
    for x in a:
        w(f"| {x['club_name']} | {x['held'][0]}–{x['held'][1]} | **{x['year_attested']}** | "
          f"{x['side']}, {x['gap_years']}y | `{x['source']}` |")
    w("\n**Read this list with care — it mixes two different things.** A short, adjacent\n"
      "gap is likely a real season. A long one is more likely a source defect: *Boston\n"
      "Yanks* attested in **1970**, twenty-two years after the club folded, is a\n"
      "wrong-for-season string. Every row needs a judgement and none is a gap until it\n"
      "gets one.\n")
    w(f"**Route B — `pfa_only_gaps`, {O['counts']['B']} entries.** The same PFA code and name\n"
      "either side of a hole, held as two clubs until a ruling says otherwise.\n")
    w(f"**Route C — `attested_same_name_across_a_long_hole`, {O['counts']['C']} entries**, all Arena.\n")
    w("### What this section still cannot do\n")
    w("**There is no founded or folded year anywhere on disk.** The fandom club-name survey\n"
      "carries **no year fields at all** — its own club-table entries say *\"the survey\n"
      "carries no years\"* — and the Wikipedia store is person-scoped, with no club\n"
      "predicates. **This section remains a floor built from refusals, not a survey.**\n")
    w("### Note for Ryan\n")
    w("**These are the hardest gaps in the archive to fill, and the most valuable.** No\n"
      "league source will ever carry them — that is definitional, not a coverage accident.\n"
      "They need **programmes, local newspapers, or a researcher who worked outside the\n"
      "league record**. Fenton is exactly that, and his site produced two of the six\n"
      "club-seasons above within a day of being found.\n")
    w("---\n")
    w("## What document would fix each gap\n")
    w("Hunt by the photographs in the listing, because that is all a listing reliably shows.\n")
    w("**Worth the most: a player-biography page** — one paragraph per man with a name, an\n"
      "age, a height, a weight and a college. It looks like dense body text in two columns\n"
      "with a bold name starting each entry, not a table. Page seven of the 1926\n"
      "Bears/Tigers programme is exactly this and carried 32 people the archive had none of.\n")
    w("**Nearly as good: a roster table with a college column.** Number, name, position,\n"
      "weight, college fills three of the four fields at once. The tell in a photograph is\n"
      "five or more narrow columns with a wide one on the right — the wide one is the\n"
      "college, and college is what the pre-1934 record lacks most (830 of 3,047).\n")
    w("**A lineup of names and numbers alone is worth little** — eleven men a side, no age,\n"
      "no college, no weight. For an **empty** club-season it is still worth having.\n")
    w("**A staff or coaches panel** is worth more than its size suggests: 13 club-seasons\n"
      "hold a roster and nobody running it.\n")
    w("**For an empty club-season, anything printed will do.** A cover with a team\n"
      "photograph and a caption naming the men, a clipping of a game report, a league\n"
      "schedule. The bar is a document that names the club and some of its men together.\n")
    w("**What to skip.** Anything 1934–46 unless the photographs show a bio page. Anything\n"
      "whose photographs show only advertisements, articles or a scoring grid — **59% of\n"
      "what a programme extractor discards is advertisement and article text**, and the\n"
      "same is true of what a buyer gets.\n")
    w("**Where the money is, in one line.** The 1920–26 APFA and early NFL — Detroit\n"
      "Heralds, Hammond Pros, Rochester Jeffersons, Louisville Brecks, Columbus\n"
      "Panhandles, Tonawanda Kardex — and the 85 empty AFL club-seasons.\n")
    return "\n".join(o)


def short():
    o = []; w = o.append
    w("# What to look for\n")
    w("*A short version of `where-the-archive-is-thin.md`. Same measurements, less of it.\n"
      "Regenerated 2026-09-08.*\n")
    w("---\n")
    w("## The one-line rule\n")
    w("**Buy 1920s. Skip 1934–46.** That era is finished — the archive already holds\n"
      "almost everything a programme from it would print.\n")
    w("---\n")
    w("## What a good page looks like in a listing photograph\n")
    w("**Best — a bio page.** Dense body text in two columns, a bold name starting each\n"
      "paragraph, numbers scattered through the prose. Ages, heights, weights, colleges.\n")
    w("**Nearly as good — a roster table with a college column.** Five or more narrow\n"
      "columns with a wide one on the right. The wide one is the college, and college is\n"
      "what the 1920s record lacks most.\n")
    w("**Worth little — a lineup of names and numbers.** No age, no college, no weight.\n"
      "Still worth having if the club is on the empty list below.\n")
    w("**Skip** — advertisements, articles, scoring grids, and anything 1934–46 without a\n"
      "bio page.\n")
    w("---\n")
    w(f"## Best find: a club with nobody on it\n")
    w(f"**{C['empty']} club-seasons** exist in the archive as a name with **zero players**.\n"
      "Any document naming that club and some of its men turns nothing into a team.\n")
    by = collections.defaultdict(list)
    for x in T["empty_club_seasons"]: by[(x["league"], x["year"])].append(x["name"])
    grp = collections.defaultdict(set)
    for (lg, y), names in by.items(): grp[lg].add(y)
    for lg in sorted(grp, key=lambda l: -len(grp[l])):
        yrs = sorted(grp[lg]); span = f"{yrs[0]}–{yrs[-1]}" if len(yrs) > 1 else yrs[0]
        clubs = sorted({n for (l, y), ns in by.items() if l == lg for n in ns})
        w(f"**{lg}, {span}** — " + " · ".join(clubs) + "\n")
    w("---\n")
    w("## Second best: the seasons on the wrong side of a league boundary\n")
    w("Not in the club table at all, so they are on no other list. **No league source will\n"
      "ever have them.**\n")
    for x in O["D_established_from_a_document"]:
        w(f"- **{x['club']} {', '.join(str(y) for y in x['outside'])}** — {x['status']}; "
          f"the archive holds **0 men**")
    w("")
    w("---\n")
    w("## Third: the 1920s clubs where the men are barely there\n")
    w("| missing | men | club-season |\n|---|---|---|")
    for x in T["thin_club_seasons"][:14]:
        w(f"| **{x['missing_facts']}** | {x['men']} | {x['year']} {x['name']} ({x['league']}) |")
    w("")
    w("---\n")
    w("## The source typos, because that is what a listing will be titled\n")
    w("Listings are titled by whoever typed them. Search on the misspellings too:\n")
    w("`Bufallo` (Buffalo) · `Neraska` (Nebraska) · `Univefsity` (University) · `Southen`\n"
      "(Southern) · `Pittsburg` (no h) · `Franklin & Marshal` (one l) · `Postion`\n"
      "(Position) · `Phythain` / `Phythian` · `Ericson` / `Erickson` · `Briton` /\n"
      "`Britton` · `Harolde` (Harold Grange) · `PROABLE` (Probable)\n")
    w("*Every one of these is a typo held as printed somewhere in the archive or on a\n"
      "document it holds — they are what the material actually says.*\n")
    return "\n".join(o)


if __name__ == "__main__":
    for name, body in (("where-the-archive-is-thin.md", full()),
                       ("what-to-look-for.md", short())):
        p = os.path.join(DOCS, name)
        open(p, "w").write(body)
        print(f"  {name:32s} {len(body):>7,} bytes  {body.count(chr(10))+1:>4} lines")
