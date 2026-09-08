"""What PFA's award pages hold. MEASUREMENT ONLY -- nothing ingested, nothing claimed.

229 pages fetched 2026-09-08; 30 more the season indexes name and the site answers
404 for. The archive holds NOTHING from this section: not one claim.

The question is not how many rows there are. It is what an award page ASSERTS, and
what a predicate would have to express to hold it without losing something.

  python3 src/measure_pfa_awards.py
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
AWARDS = os.path.expanduser("~/Documents/pgm3-sources/pfa-awards")
OUT = os.path.join(BASE, "build-reports", "pfa-awards.json")
NAV = ("privacy policy", "nfl boxscores", "nfl game officials", "nfl training camps",
       "nfl roster limits", "pro football hall of fame", "super bowl", "in memoriam",
       "previous season", "last updated")


def text(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).replace("\xa0", " ").strip()


def main():
    files = sorted(f for f in os.listdir(AWARDS) if f.endswith(".html"))
    awards = collections.Counter()        # award name -> rows
    selectors = collections.Counter()
    allleague = collections.Counter()     # "All-NFL" etc -> rows
    per_year = collections.Counter()
    winners = collections.defaultdict(set)   # (year, award) -> {winner}
    n = collections.Counter()
    for f in files:
        m = re.match(r"^(\d{4})", f)
        year = int(m.group(1)) if m else None
        t = open(os.path.join(AWARDS, f), errors="replace").read()
        section = None
        for tb in re.findall(r"(?is)<table.*?</table>", t):
            for tr in re.findall(r"(?is)<tr.*?</tr>", tb):
                c = [text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
                if not any(c):
                    continue
                if len(c) == 1:
                    low = c[0].lower()
                    if any(k in low for k in NAV) or low.startswith("&copy"):
                        section = None; continue
                    if c[0].startswith("All-"):
                        section = c[0]
                    elif "=" in c[0] and len(c[0]) > 40:
                        for tok in re.findall(r"([A-Z][A-Za-z-]*)=", c[0]):
                            selectors[tok] += 0        # the legend, not a use
                    continue
                if len(c) < 3:
                    continue
                if c[0] in ("Offense", "Defense", "Player", "Position", "Name"):
                    continue                            # a column header
                # AN ALL-LEAGUE ROW WITHOUT ITS BANNER. Where the All-X heading sits
                # in a different table, `section` is None and the row -- `Dick Huffman |
                # DT | Los Angeles Rams | AP` -- looks like an award called `Dick
                # Huffman` won by `DT`. A position in the second column settles it.
                looks_all_league = bool(re.match(r"^[A-Z]{1,3}(-[A-Z]{1,3})?$", c[1]))
                if (section and section.startswith("All-")) or looks_all_league:
                    allleague[section] += 1
                    n["all-league selections"] += 1
                    for tok in (c[3].split() if len(c) > 3 else []):
                        selectors[tok.split("-")[0]] += 1
                else:
                    awards[c[0]] += 1
                    n["named awards"] += 1
                    winners[(year, c[0])].add(c[1])
                    for tok in (c[3].split() if len(c) > 3 else []):
                        selectors[tok.split("-")[0]] += 1
                per_year[year] += 1

    split = [k for k, v in winners.items() if len(v) > 1]
    print(f"award pages on disk                          {len(files):>7,}")
    print(f"named awards (Award | Player | Club | Selectors)   {n['named awards']:>7,}")
    print(f"all-league selections (Player | Pos | Club | Sel)  {n['all-league selections']:>7,}")
    print(f"distinct award names                         {len(awards):>7,}")
    print(f"distinct selectors named                     {len([s for s in selectors]):>7,}")
    print(f"years covered                                "
          f"{min(y for y in per_year if y)}-{max(y for y in per_year if y)}")
    print(f"\nAN AWARD WITH MORE THAN ONE WINNER IN ONE YEAR: {len(split):,} of "
          f"{len(winners):,} (year, award) pairs")
    for k in sorted(split)[:6]:
        print(f"   {k[0]} {k[1]}: {sorted(winners[k])}")
    print("\ncommonest awards:")
    for a, c in awards.most_common(12):
        print(f"   {c:>5,}  {a}")
    print("\nall-league sections:")
    for a, c in allleague.most_common(10):
        print(f"   {c:>5,}  {a}")
    print("\nselectors, by how often they are named:")
    for s, c in selectors.most_common(12):
        print(f"   {c:>6,}  {s}")
    json.dump({"pages": len(files), "counts": dict(n),
               "awards": dict(awards), "all_league": dict(allleague),
               "selectors": dict(selectors),
               "awards_with_several_winners": [[k[0], k[1], sorted(v)]
                                               for k, v in winners.items() if len(v) > 1]},
              open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
