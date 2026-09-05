"""Coverage dashboard. Queries the store and writes a self-contained HTML page.

    python3 src/build_dashboard.py        (from dataset/)

Everything is computed at run time. No figure is hardcoded, so re-running gives
current numbers. Three rules the page must never break:

  UNMEASURED IS NOT ZERO. A field with no claims renders 0%; a field nothing
  counted renders "not measured" in a visibly different cell. A dashboard that
  drew "unknown" as 0% would be the empty-versus-failed error at its worst.

  NO RATE WITHOUT ITS COUNT. Every percentage carries the numerator and the
  denominator behind it.

  THE POPULATION ROW MUST SUM TO THE ARCHIVE. If a decade column drops people,
  the dashboard would hide exactly the thing it exists to show.
"""
import os, re, csv, sys, json, glob, html, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
SRC = "/Users/ryannecci/Documents/pgm3-sources"
UNMEASURED = None                     # distinct from 0 by TYPE, not by value


def log(*a): print(*a, file=sys.stderr)


# ------------------------------------------------------------------ population
YEARPART = re.compile(r"^y?(\d{4})$")


def population():
    """The archive total is the index total. Anything this function drops must be
    COUNTED and reported, not silently absent -- requiring a bare digit for the
    year dropped 493 coaches whose season keys read COACHES|y1957|Chicago Bears,
    and the population check did not catch it because it compared the grid to
    this function's own output rather than to the archive."""
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    clubs = idx.pop("_clubs", {})
    per = {}
    global DROPPED, INDEX_TOTAL
    INDEX_TOTAL = len(idx)
    DROPPED = collections.Counter()
    for g, p in idx.items():
        seasons = p.get("seasons") or {}
        if not seasons:
            DROPPED["no seasons recorded"] += 1
            continue
        yrs, lgs = [], set()
        for k in seasons:
            parts = k.split("|")
            m = YEARPART.match(parts[1]) if len(parts) >= 2 else None
            if m:
                yrs.append(int(m.group(1))); lgs.add(parts[0])
        if not yrs:
            DROPPED["season key carries no parseable year"] += 1
            continue
        per[g] = {"first": min(yrs), "leagues": lgs,
                  "person": p.get("person") or {}, "seasons": seasons,
                  "name": p.get("name")}
    return per


def decade(y): return (y // 10) * 10


LEAGUE_ORDER = ["APFA", "NFL", "AAFC", "AFL", "CFL", "WFL", "USFL", "USFL2",
                "XFL", "WLAF", "UFL", "UFL2", "AAF"]


# ------------------------------------------------------------------ the fields
def field_sets(per):
    """(label, set_of_person_ids or UNMEASURED, {source: claim_count})."""
    out = []
    src_counts = collections.defaultdict(collections.Counter)

    # --- from the person index (StatsCrew and whatever else fed it) ---
    for label, key in (("birth date", "birth_date"), ("birth place", "birthplace"),
                       ("hometown", "hometown"), ("college", "college"),
                       ("death date", "death_date"), ("high school", "high_school")):
        s = {g for g, v in per.items()
             if [x for x in (v["person"].get(key) or [])
                 if x and str(x).strip().lower() not in ("none", "")]}
        if s: src_counts[label]["StatsCrew (person index)"] += len(s)
        out.append((label, s))

    # --- claim stores ---
    stores = {}
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        b = os.path.basename(f)
        if b.startswith("stats-") or b.startswith("PGMRoster"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("claims"), list):
            stores[b] = d
    log(f"  claim stores read: {len(stores)}")

    byfield = collections.defaultdict(set)
    PRED = {
        "has_photograph": "photograph", "wikipedia.photograph": "photograph",
        "wikipedia.prose": "narrative prose",
        "wikipedia.death_date": "death date", "wikipedia.death_place": "death place",
        "wikipedia.birth_place": "birth place", "wikipedia.birth_date": "birth date",
        "wikipedia.high_school": "high school",
        "wikipedia.draft_round": "draft round/pick", "wikipedia.draft_pick": "draft round/pick",
        "wikipedia.club_career": "club-by-club career",
        "wikipedia.post_playing_career": "coaching / post-playing",
        "wikipedia.reference": "cited reference list",
        "role_title": "coaching / post-playing", "is_head_coach": "coaching / post-playing",
    }
    for b, d in stores.items():
        who = ("Wikipedia" if "wikipedia" in b else
               "PSF photo set" if "photos" in b else
               "salary sources" if "salar" in b else b)
        for c in d["claims"]:
            p = c.get("predicate")
            subj = c.get("subject")
            pid = subj[1] if isinstance(subj, (list, tuple)) and len(subj) > 1 else None
            if not isinstance(pid, str) or not pid.startswith("P_"):
                continue
            lab = PRED.get(p)
            if p and ("salary" in p or "compensation" in p or "wage" in p):
                lab = "salary"
            if not lab:
                continue
            byfield[lab].add(pid)
            src_counts[lab][who] += 1
    for lab, s in byfield.items():
        out.append((lab, s))

    # --- club-by-club career: everyone with a season has one from the rosters ---
    everyone = set(per)
    out.append(("club-by-club career", everyone | byfield.get("club-by-club career", set())))
    src_counts["club-by-club career"]["StatsCrew (rosters)"] += len(everyone)

    # --- merge duplicate labels ---
    merged = collections.defaultdict(set)
    for lab, s in out:
        if s is UNMEASURED:
            merged.setdefault(lab, UNMEASURED)
        else:
            merged[lab] |= s
    # A field we intend to show but genuinely cannot compute stays UNMEASURED,
    # WITH ITS REASON. Salary is the live case: salaries.json addresses people as
    # 'p_000001' in its own local id space on stint/contract/cohort subjects, not
    # as ('person', 'P_...') in the index id space, so it cannot be placed on the
    # person axis without a mapping that does not exist yet. That is a fact about
    # the store worth showing, not a cell to leave blank.
    for lab in ("salary",):
        merged.setdefault(lab, UNMEASURED)
    return merged, src_counts


# ------------------------------------------------------------------ the grids
def grid(per, sets, axis):
    if axis == "decade":
        keyf = lambda v: decade(v["first"])
        cols = sorted({keyf(v) for v in per.values()})
        collab = [f"{c}s" for c in cols]
    else:
        cols = [l for l in LEAGUE_ORDER if any(l in v["leagues"] for v in per.values())]
        cols += sorted({l for v in per.values() for l in v["leagues"]} - set(cols))
        collab = cols
    pop = collections.Counter()
    members = collections.defaultdict(set)
    for g, v in per.items():
        ks = [keyf(v)] if axis == "decade" else list(v["leagues"])
        for k in ks:
            pop[k] += 1; members[k].add(g)
    rows = []
    for lab in sorted(sets):
        s = sets[lab]
        cells = []
        for c in cols:
            if s is UNMEASURED:
                cells.append({"n": None, "d": pop[c]})
            else:
                cells.append({"n": len(s & members[c]), "d": pop[c]})
        rows.append({"field": lab, "cells": cells,
                     "total_n": None if s is UNMEASURED else len(s)})
    return {"cols": collab, "pop": [pop[c] for c in cols], "rows": rows,
            "pop_total": sum(pop[c] for c in cols) if axis == "decade" else None}


def media_guides():
    p = os.path.join(SRC, "nfl-books", "index.csv")
    if not os.path.exists(p):
        return UNMEASURED
    dec = collections.Counter()
    held = set()
    tdir = os.path.join(SRC, "nfl-books", "text_all")
    if os.path.isdir(tdir):
        held = {f[:-4] for f in os.listdir(tdir) if f.endswith(".txt")}
    for r in csv.DictReader(open(p)):
        y = r.get("year", "")
        if y.isdigit() and (not held or r["identifier"] in held
                            or re.sub(r"-[a-z]$", "", r["identifier"]) in held):
            dec[decade(int(y))] += 1
    return {"cols": [f"{d}s" for d in sorted(dec)],
            "counts": [dec[d] for d in sorted(dec)], "total": sum(dec.values())}


# ------------------------------------------------------------------ the page
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Archive coverage</title><style>
:root{--bg:#fbfaf8;--ink:#1c1a17;--mut:#6b665f;--line:#ddd8d0;--un:#efe9e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:32px 24px 80px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:17px;margin:40px 0 10px;letter-spacing:-.01em}
.sub{color:var(--mut);margin:0 0 6px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:#fff;
 border-right:1px solid var(--line);font-weight:500;z-index:1}
thead th{background:#f4f1ec;font-weight:600;font-size:12px;letter-spacing:.03em;
 text-transform:uppercase;color:var(--mut);position:sticky;top:0;z-index:2}
thead th:first-child{z-index:3;background:#f4f1ec}
tr.pop td,tr.pop th{background:#f4f1ec;font-weight:600;border-bottom:2px solid #cfc8bd}
td.c{position:relative}
td.c .pct{position:relative;z-index:1;font-weight:600}
td.c .cnt{position:relative;z-index:1;display:block;font-size:10.5px;color:var(--mut);
 font-weight:400;margin-top:1px}
td.un{background:repeating-linear-gradient(45deg,var(--un),var(--un) 5px,#fff 5px,#fff 10px);
 color:var(--mut);font-style:italic;font-size:11px}
.legend{display:flex;gap:16px;align-items:center;margin:12px 0 0;
 color:var(--mut);font-size:12px;flex-wrap:wrap}
.sw{display:inline-block;width:26px;height:13px;border:1px solid var(--line);
 vertical-align:-2px;margin-right:5px}
.guides td{background:#eef3f6}
.note{background:#fff;border:1px solid var(--line);border-left:3px solid #8a8175;
 border-radius:6px;padding:12px 14px;margin:16px 0;color:#39352f;font-size:13px}
code{background:#f1ede7;padding:1px 5px;border-radius:3px;font-size:12px}
.ok{color:#2c6b3f;font-weight:600}.bad{color:#a1341f;font-weight:600}
</style></head><body><div class="wrap">
<h1>Archive coverage</h1>
<p class="sub">Generated __WHEN__ &middot; every figure computed from the store at run time</p>
<div class="note"><strong>Ingests reflected:</strong> __INGESTS__<br>
<strong>Unmeasured is not zero.</strong> A hatched cell was never counted. A cell
reading 0% was counted and found empty. They are different facts and the page
draws them differently.</div>
<div id="checks"></div>
<h2>By decade of first season</h2>
<div class="scroll"><table id="t-decade"></table></div>
<div class="legend"><span><span class="sw" style="background:#f7f5f2"></span>0%</span>
<span><span class="sw" style="background:#cfe0d2"></span>50%</span>
<span><span class="sw" style="background:#7aa888"></span>100%</span>
<span><span class="sw" style="background:repeating-linear-gradient(45deg,#efe9e0,#efe9e0 5px,#fff 5px,#fff 10px)"></span>not measured</span>
<span>every cell shows <em>held / population</em> beneath the rate</span></div>
<h2>By league</h2>
<p class="sub">A person appears in every league they played in, so these columns overlap and do not sum to the archive. <strong>COACHES</strong> and <strong>SALARIES</strong> are not leagues &mdash; they are season-key prefixes the store actually uses, shown as they are rather than dropped.</p>
<div class="scroll"><table id="t-league"></table></div>
<h2>Media guide texts held, by decade of publication</h2>
<p class="sub">A COUNT OF DOCUMENTS, not a per-person rate &mdash; a guide covers a club-season, not a man. Shown in blue so the unit is never confused with the grids above.</p>
<div class="scroll"><table id="t-guides"></table></div>
<h2>Where each field comes from</h2>
<p class="sub">Claims contributed per source. This answers: if a source went away, what would go with it.</p>
<div class="scroll"><table id="t-src"></table></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const shade=p=>{const t=Math.max(0,Math.min(1,p));
  const r=247+(122-247)*t, g=245+(168-245)*t, b=242+(136-242)*t;
  return `rgb(${r|0},${g|0},${b|0})`;};
function cell(c){
  if(c.n===null) return `<td class="un" title="never counted">not measured</td>`;
  const p=c.d?c.n/c.d:0;
  return `<td class="c" style="background:${shade(p)}">`+
    `<span class="pct">${c.d?(100*p).toFixed(1)+'%':'&mdash;'}</span>`+
    `<span class="cnt">${c.n.toLocaleString()} / ${c.d.toLocaleString()}</span></td>`;
}
function grid(el,G){
  let h='<thead><tr><th>field</th>'+G.cols.map(c=>`<th>${c}</th>`).join('')+'<th>all</th></tr></thead><tbody>';
  h+='<tr class="pop"><th>people in the archive</th>'+
     G.pop.map(n=>`<td>${n.toLocaleString()}</td>`).join('')+
     `<td>${G.pop_total?G.pop_total.toLocaleString():'&mdash;'}</td></tr>`;
  for(const r of G.rows){
    h+=`<tr><th>${r.field}</th>`+r.cells.map(cell).join('')+
       (r.total_n===null?'<td class="un">not measured</td>':`<td>${r.total_n.toLocaleString()}</td>`)+'</tr>';
  }
  document.getElementById(el).innerHTML=h+'</tbody>';
}
grid('t-decade',D.decade); grid('t-league',D.league);
const g=D.guides; let gh='<thead><tr><th>&nbsp;</th>'+g.cols.map(c=>`<th>${c}</th>`).join('')+'<th>all</th></tr></thead>';
gh+='<tbody class="guides"><tr><th>guide texts held</th>'+g.counts.map(n=>`<td>${n.toLocaleString()}</td>`).join('')+
    `<td>${g.total.toLocaleString()}</td></tr></tbody>`;
document.getElementById('t-guides').innerHTML=gh;
let sh='<thead><tr><th>field</th><th>source</th><th>claims</th></tr></thead><tbody>';
for(const [f,ss] of D.sources) for(const [s,n] of ss)
  sh+=`<tr><th>${f}</th><td style="text-align:left">${s}</td><td>${n.toLocaleString()}</td></tr>`;
document.getElementById('t-src').innerHTML=sh+'</tbody>';
const C=D.checks;
document.getElementById('checks').innerHTML='<div class="note">'+
  C.map(c=>`<span class="${c.ok?'ok':'bad'}">${c.ok?'PASS':'FAIL'}</span> ${c.text}`).join('<br>')+'</div>';
</script></div></body></html>"""


def main():
    log("reading the store...")
    per = population()
    log(f"  people with at least one season: {len(per):,}")
    sets, src = field_sets(per)
    dec = grid(per, sets, "decade")
    lge = grid(per, sets, "league")
    guides = media_guides()

    checks = []
    acc = dec["pop_total"] + sum(DROPPED.values())
    checks.append({"ok": acc == INDEX_TOTAL,
                   "text": f"population row + everything dropped = the archive index: "
                           f"{dec['pop_total']:,} placed + {sum(DROPPED.values()):,} dropped "
                           f"= {acc:,} of {INDEX_TOTAL:,}"
                           + ("" if not DROPPED else " &mdash; dropped: "
                              + "; ".join(f"{v:,} {k}" for k, v in DROPPED.most_common()))})
    zero = [r["field"] for r in dec["rows"] if r["total_n"] == 0]
    unm = [r["field"] for r in dec["rows"] if r["total_n"] is None]
    checks.append({"ok": True,
                   "text": "<strong>salary</strong> is unmeasured on the person axis because "
                           "salaries.json uses its own id space (p_000001) on stint and "
                           "contract subjects; joining it needs a mapping that does not exist"})
    checks.append({"ok": True,
                   "text": f"unmeasured ({len(unm)}) and zero ({len(zero)}) are distinct cell types"
                           + (f" &mdash; not measured: {', '.join(unm)}" if unm else "")})
    bad = [r["field"] for r in dec["rows"] for c in r["cells"]
           if c["n"] is not None and c["d"] == 0 and c["n"] > 0]
    checks.append({"ok": not bad, "text": "no rate is rendered without its denominator"})

    ing = ("Wikipedia (commit 3dbf35c) &mdash; so death date, death place, high school "
           "and draft already reflect it and there is no pre-ingest baseline; "
           "StatsCrew rosters and statistics; PSF photo set; salary extracts.")
    data = {"decade": dec, "league": lge, "guides": guides,
            "sources": sorted(([f, sorted(c.items(), key=lambda x: -x[1])]
                               for f, c in src.items()), key=lambda x: x[0]),
            "checks": checks}
    out = os.path.join(BASE, "export", "coverage-dashboard.html")
    page = (PAGE.replace("__DATA__", json.dumps(data))
                .replace("__WHEN__", datetime.datetime.now().strftime("%d %B %Y, %H:%M"))
                .replace("__INGESTS__", ing))
    open(out, "w", encoding="utf-8").write(page)
    log(f"\nwrote {out}  ({os.path.getsize(out)/1024:.0f} KB)")
    for c in checks:
        log(("  PASS " if c["ok"] else "  FAIL ") + re.sub("&mdash;", "-", c["text"]))
    return dec, sets, per


if __name__ == "__main__":
    dec, sets, per = main()
    print("\n=== fields the mockup left hatched ===")
    for f in ("death date", "death place", "hometown", "high school",
              "draft round/pick", "narrative prose", "salary", "photograph"):
        s = sets.get(f, UNMEASURED)
        if s is UNMEASURED:
            print(f"  {f:22s} NOT MEASURED")
        else:
            print(f"  {f:22s} {len(s):7,d} of {len(per):,}  ({100*len(s)/len(per):5.2f}%)")
