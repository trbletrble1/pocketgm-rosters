"""Read every preserved Ghosts of the Gridiron page and say what is on it.

CLASSIFIED BY STRUCTURE, NOT BY FILENAME. The survey found 16 roster pages by
looking at names like `*_roster.htm`; a page is a roster because it has a header row
naming a player column and rows under it, whatever it is called.

NOTHING IS EXTRACTED FROM PROSE. Names in running text are COUNTED AND LOCATED and
nothing more: on one page alone the all-league table names Carl Beck with a club, a
year and a position, and a paragraph names Herman Meyer, a league president, and the
Pottsville Maroons, a club. Deciding which of those is a player is where a parser
invents people, and that decision is not this script's.

  python3 src/read_ghosts_pages.py
"""
import os, re, sys, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
M = os.path.expanduser("~/Documents/pgm3-sources/ghostsofthegridiron")
OUT = os.path.join(BASE, "build-reports", "ghosts-pages.json")

ROSTER_HEAD = re.compile(r"\b(player|name)\b", re.I)
POSHEAD = re.compile(r"\b(pos(ition)?s?|postion)\b", re.I)
COLHEAD = re.compile(r"\bcollege\b", re.I)
SCHEDHEAD = re.compile(r"\b(date|opponent|loc)\b", re.I)
STANDHEAD = re.compile(r"\b(w|l|t|pct|pf|pa)\b", re.I)
ALLLEAGUE = re.compile(r"all[-\s]?(eastern|american|pro|league|phila)", re.I)
# a capitalised forename-plus-surname in running text
NAME = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+(?:Mc|Mac|O')?[A-Z][a-z]+)\b")


def cells(tr):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", z))).replace("\xa0", " ").strip()
            for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]


def tables(t):
    out = []
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        rows = [cells(tr) for tr in re.findall(r"(?is)<tr.*?</tr>", tb)]
        rows = [r for r in rows if any(x for x in r)]
        if rows: out.append(rows)
    return out


def plain(t):
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<table.*?</table>", " ", t)          # prose only: tables removed
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[ \t]+", " ", html.unescape(t))


def classify(rows_list, text):
    kinds = set()
    biggest = 0
    for rows in rows_list:
        hdr = None
        for r in rows[:4]:
            j = " | ".join(r)
            if ROSTER_HEAD.search(j) and (POSHEAD.search(j) or COLHEAD.search(j)):
                hdr = r; break
        body = [r for r in rows if len(r) >= 2]
        if hdr and len(body) >= 4:
            kinds.add("roster"); biggest = max(biggest, len(body) - 1)
        j = " | ".join(" ".join(r) for r in rows[:3])
        if SCHEDHEAD.search(j) and len(rows) > 4: kinds.add("schedule")
        if len([x for x in rows[:3] for y in x if STANDHEAD.fullmatch(y or "")]) >= 3 and len(rows) > 4:
            kinds.add("standings")
        if ALLLEAGUE.search(j): kinds.add("all-league selections")
        if re.search(r"\b(td|xp|fg|pts)\b", j, re.I) and len(rows) > 3: kinds.add("scoring")
    if ALLLEAGUE.search(text): kinds.add("all-league selections")
    words = len(text.split())
    if words > 400: kinds.add("prose narrative")
    if not kinds: kinds.add("index or fragment" if words < 250 else "prose narrative")
    return sorted(kinds), biggest


def main():
    man = json.load(open(os.path.join(M, "manifest.json")))
    pages = [(os.path.basename(v["path"]), v) for v in man["files"].values()
             if not v.get("absent") and v.get("mimetype") == "text/html"]
    rows, kinds = [], collections.Counter()
    for name, v in sorted(pages, key=lambda x: x[0]):
        t = open(os.path.join(M, v["path"]), errors="replace").read()
        tb = tables(t)
        txt = plain(t)
        k, nmen = classify(tb, txt)
        for x in k: kinds[x] += 1
        names = NAME.findall(txt)
        rows.append({"page": name, "kinds": k, "tables": len(tb),
                     "roster_rows": nmen, "prose_words": len(txt.split()),
                     "distinct_names_in_prose": len(set(names)),
                     "snapshot": v["timestamp"]})
    out = {"_note": "classified by structure. Prose names are COUNTED, never extracted.",
           "pages": len(rows), "kinds": dict(kinds), "rows": rows}
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"{len(rows)} pages read\n")
    for k, n in kinds.most_common(): print(f"   {k:24s} {n:>4}")
    r = [x for x in rows if "roster" in x["kinds"]]
    print(f"\nROSTER PAGES BY STRUCTURE: {len(r)}  (the survey found 16 by filename)")
    for x in sorted(r, key=lambda x: -x["roster_rows"])[:30]:
        print(f"   {x['page']:36s} {x['roster_rows']:>3} rows")
    print(f"   ... {len(r)} total" if len(r) > 30 else "")
    tot = sum(x["distinct_names_in_prose"] for x in rows)
    withn = sum(1 for x in rows if x["distinct_names_in_prose"])
    print(f"\nNAMES IN PROSE: {tot:,} distinct occurrences across {withn} pages "
          f"(counted, NOT extracted)")
    return out


if __name__ == "__main__":
    main()
