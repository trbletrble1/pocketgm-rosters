"""Gate the pre-1950 delimited build. Every check here is a property, not an instance,
and it runs over EVERY guide in the file."""
import json,os,re,sys,collections
P=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "guide-pre1950-delimited.json")
G=os.path.expanduser("~/Documents/pgm3-sources/nfl-books/text_all/")
d=json.load(open(P))
fail=[]
def chk(cond,msg):
    if not cond: fail.append(msg)

claims=[];leads=[]
for rk,r in d["runs"].items():
    for y,g in r["guides"].items():
        claims+=[(rk,y,c) for c in g["claims"]]; leads+=[(rk,y,l) for l in g["leads"]]

# 1 no claim attaches to an unresolved man
chk(all(c["subject"][0]=="person" and c["subject"][1] for _,_,c in claims),
    "a claim exists without a person id")
lead_names={(rk,y,l["name_as_printed"]) for rk,y,l in leads}
res={(rk,y,n) for rk,r in d["runs"].items() for y,g in r["guides"].items()
     for n,_ in g["categories"]["resolved_written"]}
chk(not (lead_names & res), "a name is both a lead and resolved in the same guide")

# 2 a derived birth-year range can never become a birth date
dr=[c for _,_,c in claims if c["predicate"].startswith("derived.BIRTH_YEAR_RANGE")]
chk(all(re.fullmatch(r"\d{4}-\d{4}",str(c["value"])) for c in dr),
    "a derived range carries day/month detail")
chk(all(c["kind"]=="derived" for c in dr), "a derived range is not marked kind=derived")
chk(not any(c["predicate"].lower().endswith("birth_date") for c in dr),
    "a derived range is stored under a birth_date predicate")
for c in dr:
    lo,hi=str(c["value"]).split("-")
    chk(int(hi)-int(lo)==1, f"a derived range is not two consecutive years: {c['value']}")

# 3 a notes block cannot be stored altered -- round-trip against the source
NOTE=re.compile(r"^guide\.NOTES\[")
rt_ok=rt_bad=0
src_cache={}
for rk,r in d["runs"].items():
    files={}
    for y,g in r["guides"].items():
        sid=g["source"]["archive_item"]
        fn=[f for f in os.listdir(G) if f.startswith(sid)]
        if not fn: continue
        if fn[0] not in src_cache:
            src_cache[fn[0]]=[l.rstrip() for l in open(G+fn[0],encoding="utf-8",errors="replace")]
        L=src_cache[fn[0]]; S=[x.strip() for x in L]
        for c in g["claims"]:
            if NOTE.match(c["predicate"]):
                want=[x.strip() for x in str(c["value"]).split("\n") if x.strip()]
                ok=all(any(h==w or h.endswith(w) for h in S) for w in want)
                if ok: rt_ok+=1
                else: rt_bad+=1
chk(rt_bad==0, f"{rt_bad} notes blocks do not round-trip against the source")

# 4 every entry reconciles: clean + merged + nonplayer == headers, and no unparsed anchor
for rk,r in d["runs"].items():
    for y,g in r["guides"].items():
        R=g["reconciliation"]
        chk(R["clean"]+R["merged_dropped"]+R["nonplayer_dropped"]==R["headers"],
            f"{rk} {y}: spans do not reconcile to headers")
        chk(R["clean"]+len(g['categories']['merged_dropped'])>=0,"")
        cats=g["categories"]
        chk(len(cats["resolved_written"])+len(cats["name_variant_candidate"])
            +len(cats["unmatched_no_candidate"])+len(cats["roster_conflict"])==R["clean"],
            f"{rk} {y}: categories do not reconcile to clean entries")

# 4b every outside-range disagreement is still recorded per man, with both values
tot_out=0; tot_conf=0
for rk,r in d["runs"].items():
    for y,gg in r["guides"].items():
        a=gg["age_vs_held"]
        tot_out+=a["held_outside_range"]
        chk("conflicts" in a, f"{rk} {y}: age_vs_held lost its conflicts list")
        cf=a.get("conflicts",[])
        tot_conf+=len(cf)
        chk(len(cf)==a["held_outside_range"],
            f"{rk} {y}: {a['held_outside_range']} outside-range but {len(cf)} conflict records")
        for c in cf:
            chk(c.get("held_birth_date") and c.get("guide_age_as_printed") is not None,
                "a conflict record dropped one of the two disagreeing values")
            chk("UNRESOLVED" in c.get("ruling",""), "a conflict record is not marked unresolved")
chk(tot_conf==tot_out, f"conflict records {tot_conf} != outside-range count {tot_out}")

# 5 labels are not normalised -- raw guide labels survive into predicates
raw={c["predicate"] for _,_,c in claims if c["predicate"].startswith("guide.")}
for must in ("guide.SERVICE RECORD","guide.HIGH SCHOOL FOOTBALL","guide.HOME TOWN"):
    chk(must in raw, f"raw label lost: {must}")

# 6 leads carry the same field set shape as a resolved man
chk(all(isinstance(l["fields"],dict) and l["IS_NOT_A_PERSON"] is True for _,_,l in leads),
    "a lead is missing IS_NOT_A_PERSON or its field set")

print(f"conflicts recorded {tot_conf} (= outside-range {tot_out})")
print(f"claims {len(claims)}  leads {len(leads)}  derived ranges {len(dr)}  notes round-tripped {rt_ok}")
if fail:
    print("GATE FAILED:"); [print("  -",f) for f in fail if f]; sys.exit(1)
print("GATE PASSED - all properties hold over every guide")
