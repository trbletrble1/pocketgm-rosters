"""Assess drafthistory.com against the archive's drafts. MEASUREMENT ONLY.

Nothing is ingested and nothing is written to any store. Five sample years, fetched
politely and already on disk; this reads them.

COMPARED ON THE DECLARED READINGS, NOT THE LITERALS. The college synonym list and
the state expansion exist now, and the last comparison of this kind reported 109
disagreements of which 42 were the reading's own job. A number that measures your
own instrument reads exactly like a number that measures the world.
"""
import os, re, sys, json, html, collections, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
from readings import READERS
COLL = READERS["college"]
DH = os.path.expanduser("/private/tmp/claude-501/-Users-ryannecci-Documents/"
                        "acd72c9e-ae2e-4fc6-a7d2-d8c7cb1ab418/scratchpad/dh")
YEARS = (1936, 1950, 1965, 1980, 2000)
OUT = os.path.join(BASE, "build-reports", "drafthistory-assessment.json")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def site_year(y):
    """Round | Pick | Player | Name | Team | Position | College, POSITIONALLY.

    The round column is `&nbsp;` on every row but the first of a round -- there is no
    rowspan attribute anywhere in the page. Dropping empty cells therefore collapses
    seven columns into six and silently shifts every later field left, which is the
    COLUMN SLIP the programme census documented on a different corpus. Cells are kept
    in place and the round is carried down.
    """
    t = open(os.path.join(DH, f"y{y}.html"), errors="replace").read()
    out, rnd = [], None
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        rows = []
        for tr in re.findall(r"(?is)<tr.*?</tr>", tb):
            cells = [re.sub(r"\s+", " ",
                            html.unescape(re.sub(r"<[^>]+>", " ", z))).replace("\xa0", " ").strip()
                     for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
            if cells: rows.append(cells)
        if len(rows) < 6 or not any(len(r) >= 7 for r in rows): continue
        for r in rows:
            if len(r) < 7 or r[1].lower() == "pick": continue
            if r[0].isdigit(): rnd = int(r[0])
            if not (r[1].isdigit() and r[2].isdigit()): continue
            out.append({"year": y, "round": rnd, "pick_in_round": int(r[1]),
                        "overall": int(r[2]), "name": r[3], "team": r[4],
                        "position": r[5], "college": r[6] if len(r) > 6 else None})
        if out: break
    return out


def archive_year(conn, y):
    """-> {overall_pick: [rows]} from every draft predicate the archive holds."""
    by = collections.defaultdict(list); other = collections.Counter()
    q = """select c.predicate, c.value, c.person, p.index_name from claim c
           left join person p on p.id=c.person
           where c.family='draft' and c.value like ?"""
    for pred, val, person, nm in conn.execute(q, (f'%{y}%',)):
        try: v = json.loads(val)
        except Exception: continue
        if not isinstance(v, dict) or v.get("year") != y: continue
        # (year, overall_pick) IS NOT A UNIQUE KEY IN THE ARCHIVE. 1950 holds a regular
        # NFL draft AND an AAFC allocation draft, both numbering their overall picks from
        # 1, and the declared draft reading -- year, round, overall pick -- has no field
        # that tells them apart. Matching on (year, overall) alone put Chet Mutryn, the
        # allocation draft's first pick, against Leon Hart, the draft's. The first version
        # of this measurement did exactly that and reported 316 name disagreements.
        lg = (v.get("league_from_filename") or v.get("league_from_link")
              or v.get("league") or "?")
        if v.get("draft_kind") not in (None, "draft") or lg not in ("NFL", "?"):
            other[f"{v.get('draft_kind')}/{lg}"] += 1; continue
        ov = v.get("overall_pick")
        if ov is None: continue
        by[ov].append({"predicate": pred, "person": person, "held_name": nm,
                       "round": v.get("round"), "team": v.get("team") or v.get("club"),
                       "position": v.get("position_as_printed"),
                       "college": v.get("college_as_printed")})
    return by, other


def main():
    import sqlite3, paths
    conn = sqlite3.connect(paths.READ_MODEL)
    try: conn.execute("select 1 from person limit 1")
    except Exception: pass
    res, tot = [], collections.Counter()
    for y in YEARS:
        site = site_year(y)
        seen_ov, first, extra = set(), [], 0
        for r in site:
            if r["overall"] in seen_ov: extra += 1; continue
            seen_ov.add(r["overall"]); first.append(r)
        site, dropped_second_draft = first, extra
        arch, other_kinds = archive_year(conn, y)
        if not site:
            res.append({"year": y, "ERROR": "no rows parsed"}); continue
        rows = {"year": y, "site_picks": len(site),
                "site_rows_at_a_repeated_overall_pick": dropped_second_draft, "archive_picks_with_an_overall": len(arch),
                "archive_rows_excluded_as_another_draft": dict(other_kinds),
                "not_held": [], "disagree": [], "exact": 0}
        for s in site:
            a = arch.get(s["overall"])
            if not a:
                rows["not_held"].append(s); tot["not_held"] += 1; continue
            # compare against the BEST-informed archive row for this pick
            best = max(a, key=lambda r: sum(x is not None for x in
                                            (r["round"], r["team"], r["college"], r["position"])))
            diffs = {}
            if norm(best["held_name"]) and norm(s["name"]) != norm(best["held_name"]):
                diffs["name"] = [s["name"], best["held_name"]]
            if best["round"] is not None and s["round"] is not None and int(best["round"]) != int(s["round"]):
                diffs["round"] = [s["round"], best["round"]]
            if best["college"] and s["college"] and COLL(s["college"]) != COLL(best["college"]):
                diffs["college"] = [s["college"], best["college"]]
            if best["position"] and s["position"] and norm(s["position"]) != norm(best["position"]):
                diffs["position"] = [s["position"], best["position"]]
            if diffs:
                rows["disagree"].append({"overall": s["overall"], "site_name": s["name"],
                                         "held_name": best["held_name"],
                                         "person": best["person"], "fields": diffs,
                                         "compared_against": best["predicate"]})
                for k in diffs: tot["diff_" + k] += 1
                tot["disagree"] += 1
            else:
                rows["exact"] += 1; tot["exact"] += 1
        tot["site"] += len(site)
        res.append(rows)
    out = {"_note": "MEASUREMENT ONLY. Nothing ingested. Colleges compared on the DECLARED "
                    "reading, not the literal.",
           "years": res, "totals": dict(tot)}
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"{'year':>6} {'site':>6} {'held':>6} {'exact':>7} {'disagree':>9} {'not held':>9}")
    for r in res:
        if "ERROR" in r: print(f"{r['year']:>6}  {r['ERROR']}"); continue
        print(f"{r['year']:>6} {r['site_picks']:>6} {r['archive_picks_with_an_overall']:>6} "
              f"{r['exact']:>7} {len(r['disagree']):>9} {len(r['not_held']):>9}")
    print(f"\ntotals: {dict(tot)}")
    return out


if __name__ == "__main__":
    main()
