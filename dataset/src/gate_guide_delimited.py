"""Gate the pre-1950 delimited build. Every check here is a property, not an instance,
and it runs over EVERY guide in the file.

REWRITTEN 2026-09-13 with the file (Ryan's RS-G5 ruling: rewrite the file, not the reader).
The claims sit at the top level of a normal store, beside a source_records table; the
per-guide parse record -- leads, categories, reconciliation, age checks -- stays under runs.

  G1  no claim attaches to an unresolved man; no name is both a lead and resolved
  G2  A DERIVED RANGE IS A READING, NEVER A CLAIM (Ryan, 2026-09-13). No claim carries a
      derived predicate or kind. Every range sits on the printed age claim it came from, as
      `_derived_birth_year_range`, labelled derived, naming that age -- and it is two
      consecutive years and nothing finer
  G3  a notes block round-trips against the source text
  G4  every guide reconciles: spans to headers, categories to clean entries, conflicts to the
      outside-range count
  G5  labels are not normalised: raw labels survive into predicates
  G6  leads carry their field set and IS_NOT_A_PERSON
  G7  THE NORMAL SHAPE: claims at the top level, none below it
  G8  every claim's source record is registered in the file's own table, and every source
      it names is carried in `sources`
  G9  NOTHING THAT IS NOT ABOUT THE MAN: no club statistic or prose fragment is a claim.
      Checked against THIS GATE'S OWN list, not the declaration's, so a declaration that
      forgets one still fails here
  G10 every label left as printed is counted, and the counts add up to the claims that carry
      an unmapped label
"""
import json,os,re,sys,collections
BASE=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
P=os.path.join(BASE, "build", "guide-pre1950-delimited.json")
G=os.path.expanduser("~/Documents/pgm3-sources/nfl-books/text_all/")
d=json.load(open(P))
fail=[]
def chk(cond,msg):
    if not cond: fail.append(msg)

# G9's own list: the 21 club statistics and headings and the 6 prose fragments measured 2026-09-13.
NOT_ABOUT_THE_MAN={"SCORING","Most Points","Total Points","Total Points by Opponents","Total Yards Gained",
    "Most Attempts","Most Yards Gained On Passes","Most Touchdown Passes","Longest Passes","Most Passes Caught",
    "Most Touchdown Passes Received","Most Yards Catching Passes","Most Yards One Interception",
    "Total First Downs","Longest Punt","Longest Punt Return","Total Field Goals","Longest Field Goal",
    "Total Extra Points","Most Consecutive Extra Points","GIANTS vs. PORTSMOUTH",
    "Two children. Home","Married. One child. Home","This quartet of aportacasters","Los Angeles","San Francisco"}

# G7 -- the shape
top=d.get("claims")
chk(isinstance(top,list) and top, "G7 the file has no top-level claims list")
nested=sum(len(g.get("claims") or []) for r in (d.get("runs") or {}).values() for g in r.get("guides",{}).values())
chk(nested==0, f"G7 {nested} claims still sit below the top level")
claims=top if isinstance(top,list) else []
guides={}                                        # source_id -> (run key, year, guide record)
for rk,r in (d.get("runs") or {}).items():
    for y,g in r["guides"].items():
        guides[g.get("source_id") or (g.get("source") or {}).get("source_id")]=(rk,y,g)
leads=[(rk,y,l) for rk,y,g in guides.values() for l in g.get("leads",[])]

# G1
chk(all(c["subject"][0]=="person" and c["subject"][1] for c in claims), "G1 a claim exists without a person id")
lead_names={(rk,y,l["name_as_printed"]) for rk,y,l in leads}
res={(rk,y,n) for rk,y,g in guides.values() for n,_ in g["categories"]["resolved_written"]}
chk(not (lead_names & res), "G1 a name is both a lead and resolved in the same guide")

# G2
bad_kind=[c for c in claims if c["predicate"].startswith("derived.") or c.get("kind")=="derived"]
chk(not bad_kind, f"G2 {len(bad_kind)} claims are derived -- a derived range is a reading, never a claim")
ranges=[c for c in claims if c.get("_derived_birth_year_range")]
for c in ranges:
    r=c["_derived_birth_year_range"]
    chk(r.get("derived") is True, "G2 a range is not labelled derived")
    chk(str(r.get("from_age_as_printed"))==str(c["value"]), f"G2 a range does not name the age it sits on: {r} / {c['value']}")
    chk(re.fullmatch(r"\d{4}-\d{4}",str(r.get("value",""))) is not None, f"G2 a range carries detail: {r.get('value')}")
    if re.fullmatch(r"\d{4}-\d{4}",str(r.get("value",""))):
        lo,hi=str(r["value"]).split("-"); chk(int(hi)-int(lo)==1, f"G2 not two consecutive years: {r['value']}")
    chk("age" in c["predicate"].lower() or c["predicate"].endswith(".yrs"), f"G2 a range sits on a non-age label: {c['predicate']}")

# G3
NOTE=re.compile(r"^guide\.NOTES\[")
rt_ok=rt_bad=0; src_cache={}
srcs=d.get("sources") or {}
for c in claims:
    if not NOTE.match(c["predicate"]): continue
    sid=(srcs.get(c["source_id"]) or {}).get("archive_item")
    fn=[f for f in os.listdir(G) if sid and f.startswith(sid)]
    if not fn: continue
    if fn[0] not in src_cache:
        src_cache[fn[0]]=[l.strip() for l in open(G+fn[0],encoding="utf-8",errors="replace")]
    S=src_cache[fn[0]]
    want=[x.strip() for x in str(c["value"]).split("\n") if x.strip()]
    if all(any(h==w or h.endswith(w) for h in S) for w in want): rt_ok+=1
    else: rt_bad+=1
chk(rt_bad==0, f"G3 {rt_bad} notes blocks do not round-trip against the source")

# G4
tot_out=tot_conf=0
for rk,y,g in guides.values():
    R=g["reconciliation"]; cats=g["categories"]
    chk(R["clean"]+R["merged_dropped"]+R["nonplayer_dropped"]==R["headers"], f"G4 {rk} {y}: spans do not reconcile to headers")
    chk(len(cats["resolved_written"])+len(cats["name_variant_candidate"])+len(cats["unmatched_no_candidate"])
        +len(cats["roster_conflict"])==R["clean"], f"G4 {rk} {y}: categories do not reconcile to clean entries")
    a=g["age_vs_held"]; tot_out+=a["held_outside_range"]; cf=a.get("conflicts",[]); tot_conf+=len(cf)
    chk(len(cf)==a["held_outside_range"], f"G4 {rk} {y}: {a['held_outside_range']} outside-range but {len(cf)} conflict records")
    for x in cf:
        chk(x.get("held_birth_date") and x.get("guide_age_as_printed") is not None, "G4 a conflict record dropped a value")
        chk("UNRESOLVED" in x.get("ruling",""), "G4 a conflict record is not marked unresolved")
chk(tot_conf==tot_out, f"G4 conflict records {tot_conf} != outside-range count {tot_out}")

# G5
raw={c["predicate"] for c in claims if c["predicate"].startswith("guide.")}
for must in ("guide.SERVICE RECORD","guide.HIGH SCHOOL FOOTBALL","guide.HOME TOWN"):
    chk(must in raw, f"G5 raw label lost: {must}")

# G6
chk(all(isinstance(l["fields"],dict) and l["IS_NOT_A_PERSON"] is True for _,_,l in leads),
    "G6 a lead is missing IS_NOT_A_PERSON or its field set")

# G8
table=d.get("source_records") or {}
unreg=[c["source_record"] for c in claims if c["source_record"] not in table]
chk(table and not unreg, f"G8 {len(unreg)} claims cite a record the file does not register")
chk(all(c["source_id"] in srcs for c in claims), "G8 a claim names a source the file does not carry")

# G9
wrong=[c["predicate"] for c in claims if c["predicate"][len("guide."):] in NOT_ABOUT_THE_MAN]
chk(not wrong, f"G9 {len(wrong)} claims are club statistics or prose fragments: {sorted(set(wrong))[:4]}")

# G10
counted=d.get("labels_left_as_printed")
if counted is None: chk(False, "G10 the file does not count its labels left as printed")
else:
    n=collections.Counter(c["predicate"] for c in claims if c["predicate"] in counted)
    chk(dict(n)==counted, "G10 the label counts do not match the claims")

# G11 -- OUTSIDE THE FOUR FAMILIES (Ryan, 2026-09-14). In the model, no claim from this store carries the
# birth_date, college, height or weight family, and none has a date reading: its labels are served as
# printed and contest nothing. Measured before the ruling: in those families they made 171 contested rows,
# most fabricated, and 64 unreadable dates. Reads the served model, or the one named by --model.
import sqlite3
sys.path.insert(0, os.path.join(BASE, "service"))
import paths as _paths
_model = sys.argv[sys.argv.index("--model")+1] if "--model" in sys.argv else _paths.READ_MODEL
_mc = sqlite3.connect(f"file:{_model}?mode=ro", uri=True)
_inf = _mc.execute("SELECT family, COUNT(*) FROM claim WHERE store='guide-pre1950-delimited' AND family IN "
                   "('birth_date','college','height','weight') GROUP BY family").fetchall()
_dr = _mc.execute("SELECT COUNT(*) FROM date_reading d JOIN claim c ON c.id=d.claim "
                  "WHERE c.store='guide-pre1950-delimited'").fetchone()[0]
_n = _mc.execute("SELECT COUNT(*) FROM claim WHERE store='guide-pre1950-delimited'").fetchone()[0]
chk(_n > 0, f"G11 {os.path.basename(_model)} holds no claim from this store")
chk(not _inf and _dr == 0, f"G11 in {os.path.basename(_model)}: {dict(_inf)} claims inside the four families, {_dr} date readings")

print(f"claims {len(claims)}  leads {len(leads)}  derived ranges {len(ranges)}  notes round-tripped {rt_ok}  "
      f"conflicts {tot_conf} (= outside-range {tot_out})")
if fail:
    print("GATE FAILED:"); [print("  -",f) for f in fail if f]; sys.exit(1)
print("GATE PASSED - all properties hold over every guide")
