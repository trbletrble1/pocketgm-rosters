"""What PFA's draft pages hold against what the archive took from them.

MEASUREMENT ONLY. Nothing ingested, nothing written to a store, nothing fetched --
all 203 pages were already in the cache, fetched by the PFA sweep and never read.

THE DENOMINATOR IS ENUMERATED, NOT INFERRED. Every `drafts_*.html` in the cache is
listed before anything is parsed, so "what PFA has" is a count of pages that exist
rather than a count of pages that happened to come back.

COMPARED ON THE DECLARED READINGS. The draft reading now carries league and kind, so
a year holding several drafts is no longer a collision; the college reading carries
the synonym list. Two previous comparisons of this kind published the instrument
before being corrected, and the fix both times was to compare on the reading.

  python3 src/measure_pfa_drafts.py
"""
import os, re, sys, json, html, glob, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, reading_view as RV
from readings import READERS
COLL = READERS["college"]
CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
OUT = os.path.join(BASE, "build-reports", "pfa-drafts.json")

LG = re.compile(r"^(aafcspecial|aafc|aflnfl|afl|cfl|nfleu|nfl|usfl|wfl|world|xfl|ufl)")


def pages():
    out = []
    for p in sorted(glob.glob(os.path.join(CACHE, "drafts_*.html"))):
        m = re.match(r"drafts_(\d{4})([a-z]+)\.html$", os.path.basename(p))
        if not m: continue
        y, rest = int(m.group(1)), m.group(2)
        g = LG.match(rest)
        lg = (g.group(1) if g else "?").upper()
        kind = rest[len(g.group(1)):] if g else rest
        out.append((p, y, lg, kind or "draft"))
    return out


def rows_of(path):
    t = open(path, errors="replace").read()
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", tb):
            c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", z))).replace("\xa0", " ").strip()
                 for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
            if any(c): rows.append(c)
        if len(rows) < 4: continue
        hdr = next((i for i, r in enumerate(rows[:3])
                    if r and r[0].lower() in ("round", "pick", "overall")), None)
        if hdr is None: continue
        cols = [x.lower() for x in rows[hdr]]
        for r in rows[hdr + 1:]:
            if len(r) < 3: continue
            d = dict(zip(cols, r))
            yield d
        return


def norm(s):
    return " ".join(re.sub(r"[^a-z ]", " ", str(s or "").lower()).split())


def main():
    conn = sqlite3.connect(paths.READ_MODEL)
    held = collections.defaultdict(list)       # (year,league,kind,overall) -> rows
    for pred, val, person in conn.execute(
            "select predicate,value,person from claim where family='draft'"):
        try: v = json.loads(val)
        except Exception: continue
        if not isinstance(v, dict): continue
        r = RV.read("draft", v)
        if not r or r.get("overall") is None: continue
        held[(r["year"], r.get("league"), r.get("kind"), r["overall"])].append(
            {"predicate": pred, "person": person,
             "college": v.get("college_as_printed"), "name": v.get("name_as_printed"),
             "team": v.get("team") or v.get("club"), "round": r.get("round")})
    byyear = collections.defaultdict(list)
    for k, v in held.items(): byyear[(k[0], k[1], k[2])].append(k[3])

    res, tot = [], collections.Counter()
    for path, y, lg, kind in pages():
        picks = list(rows_of(path))
        if not picks:
            res.append({"page": os.path.basename(path), "year": y, "league": lg,
                        "kind": kind, "picks_on_the_page": 0,
                        "note": "no table with a Round/Pick/Overall header"})
            tot["pages_with_no_table"] += 1; continue
        miss, agree, dis = [], 0, []
        for p in picks:
            ov = p.get("overall") or p.get("pick")
            try: ov = int(re.sub(r"\D", "", ov or ""))
            except Exception: continue
            rd = p.get("round")
            try: rd = int(re.sub(r"\D", "", rd or "")) or None
            except Exception: rd = None
            mine = RV.read("draft", {"year": y, "round": rd, "overall_pick": ov,
                                     "league_from_filename": lg, "draft_kind": kind})
            hit = None
            for (hy, hl, hk, ho), rows in held.items():
                if ho != ov or hy != y: continue
                theirs = RV.read("draft", {"year": hy, "round": rows[0]["round"],
                                           "overall_pick": ho, "league_from_filename": hl,
                                           "draft_kind": hk})
                if mine and theirs and RV.same("draft", mine, theirs): hit = rows; break
            nm = p.get("player") or p.get("name")
            if not hit:
                miss.append({"overall": ov, "round": rd, "name": nm,
                             "team": p.get("team"), "college": p.get("college")}); continue
            best = hit[0]
            d = {}
            if best["name"] and nm and norm(nm) != norm(best["name"]): d["name"] = [nm, best["name"]]
            if best["college"] and p.get("college") and COLL(p["college"]) != COLL(best["college"]):
                d["college"] = [p["college"], best["college"]]
            if d: dis.append({"overall": ov, "name": nm, "fields": d})
            else: agree += 1
        tot["pfa_picks"] += len(picks); tot["missing"] += len(miss)
        tot["agree"] += agree; tot["disagree"] += len(dis)
        res.append({"page": os.path.basename(path), "year": y, "league": lg, "kind": kind,
                    "picks_on_the_page": len(picks), "not_held": len(miss),
                    "agree": agree, "disagree": len(dis),
                    "examples_not_held": miss[:3], "examples_disagree": dis[:3]})
    out = {"_note": "MEASUREMENT ONLY, from the cache. Compared on the declared readings.",
           "pages_enumerated": len(pages()), "totals": dict(tot), "pages": res}
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"pages enumerated: {len(pages())}")
    print(f"picks on PFA's pages : {tot['pfa_picks']:,}")
    print(f"  NOT HELD           : {tot['missing']:,}")
    print(f"  agree              : {tot['agree']:,}")
    print(f"  disagree           : {tot['disagree']:,}")
    worst = sorted([r for r in res if r.get("not_held")], key=lambda r: -r["not_held"])[:12]
    print("\nbiggest gaps:")
    for r in worst:
        print(f"   {r['year']} {r['league']:5s} {r['kind']:16s} {r['not_held']:>4} of {r['picks_on_the_page']:>4} not held")
    return out


if __name__ == "__main__":
    main()
