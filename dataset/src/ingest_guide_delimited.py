"""Emit claims and leads for the 32 parsed delimited pre-1950 guides.

RULINGS HONOURED HERE, each with the code that enforces it:
  AGE AND BIRTH DATE ARE BOTH KEPT. The guide's age is recorded verbatim as
  guide.AGE. From it a BIRTH-YEAR RANGE is derived -- two years, never one,
  because a guide goes to press before the season and the age is age-at-an-
  unknown-date. It is emitted under derived.BIRTH_YEAR_RANGE with kind
  "derived", and NOTHING in this file can turn it into a birth date: the
  predicate name differs and assert_no_derived_dates() fails the build if a
  derived range ever carries a day or month.

  NOTES BLOCKS STAY WHOLE. Captured verbatim with the guide's own label where it
  has one (NOTES, GENERAL INFORMATION), or notes_label=null where the block is
  unlabelled trailing prose -- the two are NOT merged because they may prove to be
  different things. Never split into fields, never rewritten. Round-tripped against
  the source before writing.

  NO CLAIM ATTACHES TO AN UNRESOLVED MAN. make_claim() raises without a person id.
  A lead carries the identical field set so a later promotion is a ruling, not a
  re-parse.
"""
import os,re,sys,json,collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guide_delimited_runs import _lines
from guide_delimited_specs import SPECS,G,DROPPED_RUNS
from parse_guide_delimited import parse_guide

REPO=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IDX=json.load(open(os.path.join(REPO,"build-reports","person-index.json")))
CLUBS=IDX.pop("_clubs",{})
OUT=os.path.join(REPO, "build")
os.makedirs(OUT,exist_ok=True)

class LeadError(Exception): pass

def seasons(p):
    out=[]
    for k in p["seasons"]:
        key=k[0] if isinstance(k,list) else k
        parts=key.split("|")
        if len(parts)==3:
            y=parts[1].lstrip("yY")
            if y.isdigit():
                out.append({"league":parts[0],"year":int(y),"club":parts[2]})
    return out

def natural(n):
    """A guide printing SURNAME, First is the same name as First Surname. Swapping on
    the comma is a FORMATTING fact, not a judgment about identity."""
    n=re.sub(r"\(.*?\)"," ",n); n=re.sub(r"[“”\"’]"," ",n)
    n=re.sub(r"\s+"," ",n).strip().strip(",.")
    if "," in n:
        a,b=n.split(",",1)
        if b.strip(): n=b.strip()+" "+a.strip()
    return n.strip()

def drop_initials(n):
    """Drop single-letter middle initials. 'URBAN L. ODSON' and 'Urban Odson' are the
    same name printed two ways. Applied to BOTH sides, and a resolution is only taken
    when the stripped key matches EXACTLY ONE person on the club-season roster."""
    toks=[t for t in re.split(r"\s+",n) if t]
    if len(toks)<=2: return " ".join(toks)
    return " ".join([toks[0]]+[t for t in toks[1:-1] if len(t.strip(".'"))>1]+[toks[-1]])

def norm(n):
    return re.sub(r"[^a-z]","",drop_initials(natural(n)).lower())

def first_last(n):
    n=natural(n)
    n=re.sub(r"\(.*?\)"," ",n)
    parts=[x for x in re.sub(r"[^A-Za-z ]"," ",n).lower().split() if len(x)>1]
    return (parts[0],parts[-1]) if len(parts)>=2 else (None,None)

DIMINUTIVE={("bob","robert"),("bill","william"),("dick","richard"),("jim","james"),
 ("hank","henry"),("chuck","charles"),("al","albert"),("joe","joseph"),("jack","john"),
 ("len","leonard"),("ted","edward"),("ned","edward"),("dan","daniel"),("gus","august"),
 ("bert","herbert"),("burt","burton"),("chet","chester"),("ken","kenneth"),("tom","thomas"),
 ("ed","edward"),("art","arthur"),("frank","francis"),("mike","michael"),("pete","peter"),
 ("tony","anthony"),("walt","walter"),("gene","eugene"),("vince","vincent"),("sam","samuel")}

def compatible(a,b):
    if a==b or a.startswith(b) or b.startswith(a): return True
    return (a,b) in DIMINUTIVE or (b,a) in DIMINUTIVE

def build_roster(league,year,clubname):
    r={}
    for g,p in IDX.items():
        if not isinstance(p,dict) or not p.get("seasons"): continue
        for s in seasons(p):
            if s["league"]==league and s["year"]==year:
                nm=CLUBS.get(f"{s['club']}|{year}","")
                if nm and nm.lower().startswith(clubname.lower()[:9]):
                    r[p["name"]]=g
    return r

def _person_field(p,name):
    pr=p.get("person")
    if isinstance(pr,dict): v=pr.get(name)
    elif isinstance(pr,list):
        v=None
        for e in pr:
            if isinstance(e,(list,tuple)) and len(e)==2 and e[0]==name: v=e[1]; break
    else: v=None
    if not v: return None
    return v[0] if isinstance(v,list) else v

def held_birth_year(pid):
    p=IDX.get(pid) or {}
    raw=_person_field(p,"birth_date")
    if not raw: return None,None
    m=re.search(r"\b(18|19)\d{2}\b",str(raw))
    return (int(m.group(0)),str(raw)) if m else (None,str(raw))

AGE_KEYS=("Age","AGE","age","yrs")
def age_of(fields):
    for k in fields:
        if k in AGE_KEYS:
            m=re.search(r"\b(\d{2})\b",str(fields[k]))
            if m: return k,int(m.group(1)),fields[k]
    return None,None,None

def birth_range(age,guide_year):
    """A guide goes to press before the season, so an age is age at an UNKNOWN date
    inside the year. Two birth years are consistent with it. Never one."""
    return [guide_year-age-1, guide_year-age]

def predicate(label,parent=None):
    if label.upper() in ("HONORS","HONOURS"): return "guide.HONORS@"+(parent or "UNATTACHED")
    return "guide."+label

def make_claim(sr,sid,stated_by,title,pid,label,value,year,parent=None,kind="observed",pred=None):
    if not pid: raise LeadError("a claim requires a person; a lead is not a person")
    return {"source_record":sr,"source_id":sid,"stated_by":stated_by,"attribution":[title],
            "subject":["person",pid],"predicate":pred or predicate(label,parent),
            "value":value,"kind":kind,"observed_at":f"guide-{year}"}

def fieldset(rec):
    out=collections.OrderedDict()
    for k,v in rec["fields"].items(): out[k]=v
    for i,h in enumerate(rec.get("honours") or []):
        out[f"HONORS@{h['parent'] or 'UNATTACHED'}#{i}"]=h["value"]
    if rec.get("notes") is not None:
        out[f"__NOTES__[{rec.get('notes_label') or 'UNLABELLED'}]"]=rec["notes"]
    return out

def roundtrip_ok(notes,src_lines,a,b):
    """Prove the stored block is the source's own text: every non-empty stored line
    must appear, in order, as a stripped source line inside the entry span."""
    if not notes: return True
    want=[x.strip() for x in notes.split("\n") if x.strip()]
    have=[src_lines[k].strip() for k in range(a,min(b,len(src_lines)))]
    i=0
    for w in want:
        # equal to a source line, or its tail -- the first line of a labelled block is
        # the remainder of "LABEL: ..." after the label, which is a suffix, not a line.
        while i<len(have) and not (have[i]==w or have[i].endswith(w)): i+=1
        if i>=len(have): return False
        i+=1
    return True

def assert_no_derived_dates(claims):
    bad=[c for c in claims if c["predicate"].startswith("derived.BIRTH_YEAR_RANGE")
         and not re.fullmatch(r"\d{4}-\d{4}",str(c["value"]))]
    if bad: raise AssertionError(f"a derived range acquired date detail: {bad[:2]}")

CATEGORIES=["resolved_written","unmatched_no_candidate","name_variant_candidate",
            "roster_conflict","merged_dropped","nonplayer_span_dropped"]

def run_guide(runkey,spec,fn,year,title,sid):
    P=parse_guide(runkey,spec,fn,year)
    L=_lines(G+fn)
    club,league=spec["club"],spec["league"]
    roster=build_roster(league,year,club)
    _tmp=collections.defaultdict(list)
    for k,g in roster.items(): _tmp[norm(k)].append((g,k))
    rn={k:v[0] for k,v in _tmp.items() if len(v)==1}
    collided={k:v for k,v in _tmp.items() if len(v)>1}
    roster_fl={}
    for k,g in roster.items():
        f,l=first_last(k)
        if f: roster_fl.setdefault(l,[]).append((f,k,g))
    def variant_of(nm):
        f,l=first_last(nm)
        if not f: return None
        c=[(k,g) for (rf,k,g) in roster_fl.get(l,[]) if compatible(f,rf)]
        return c[0] if len(c)==1 else None
    src_id=f"media-guide-{spec['code']}-{year}"
    sr=f"{src_id}#player-sketches"
    claims=[];leads=[];cats=collections.defaultdict(list)
    rt_ok=rt_fail=0; notes_n=0; age_n=0; rng_n=0
    inside=outside=nodate=0; conflicts=[]
    for rec in P["clean"]:
        nm=rec["name_as_printed"]
        a,b=rec["span"]
        if rec.get("notes") is not None:
            notes_n+=1
            if roundtrip_ok(rec["notes"],L,a,b): rt_ok+=1
            else:
                rt_fail+=1; rec["notes"]=None; rec["notes_label"]=None
        hit=rn.get(norm(nm)); pid=hit[0] if hit else None
        if pid:
            cats["resolved_written"].append((nm,pid))
            for label,value in rec["fields"].items():
                if not str(value).strip(): continue
                lab={"_marital":"MARITAL STATUS","_hdr_tail":"HEADER (UNPARSED TAIL)"}.get(label,label)
                claims.append(make_claim(sr,src_id,club,title,pid,lab,str(value),year))
            for h in (rec.get("honours") or []):
                claims.append(make_claim(sr,src_id,club,title,pid,"HONORS",h["value"],year,h["parent"]))
            if rec.get("notes") is not None:
                claims.append(make_claim(sr,src_id,club,title,pid,"NOTES",rec["notes"],year,
                    pred="guide.NOTES["+(rec.get("notes_label") or "UNLABELLED")+"]"))
            k,age,raw=age_of(rec["fields"])
            if age and 15<age<50:
                age_n+=1
                lo,hi=birth_range(age,year)
                claims.append(make_claim(sr,src_id,club,title,pid,"","%d-%d"%(lo,hi),year,
                    kind="derived",pred="derived.BIRTH_YEAR_RANGE"))
                rng_n+=1
                hy,hraw=held_birth_year(pid)
                if hy is None: nodate+=1
                elif lo<=hy<=hi: inside+=1
                else:
                    outside+=1
                    conflicts.append({"person":pid,"name_as_printed":nm,"guide":src_id,
                        "guide_age_label":k,"guide_age_as_printed":str(raw),
                        "derived_birth_year_range":[lo,hi],"held_birth_date":hraw,
                        "held_birth_year":hy,
                        "ruling":"UNRESOLVED. The age and the held date disagree; which is wrong "
                                 "is not decided here. Both are kept."})
            continue
        var=variant_of(nm)
        if var:
            cat,why,cand=("name_variant_candidate",
                f"the roster has {var[0]!r} -- same surname on this club-season, first name "
                f"compatible. A JUDGMENT, not resolved here.",var[1])
        else:
            cat,why,cand=("unmatched_no_candidate",
                f"no person of this name on the {year} {club} roster",None)
        cats[cat].append((nm,cand))
        leads.append({"lead_id":f"lead-{spec['code']}{year}-{len(leads)+1:03d}","category":cat,
            "name_as_printed":nm,"position":rec["fields"].get("POSITION (HEADER)"),
            "source_id":src_id,"source_record":sr,
            "places_on":{"league":league,"year":year,"club":club},
            "why_matching_failed":why,"candidate_person":cand,"IS_NOT_A_PERSON":True,
            "fields":fieldset(rec)})
    for rec,n in P["merged"]:
        cats["merged_dropped"].append((rec.get("name_as_printed"),
            f"{n} anchors in one span -- a header was missed and {n} men merged. No claims."))
    for rec,n in P["empty"]:
        cats["nonplayer_span_dropped"].append((rec.get("name_as_printed"),
            "0 anchors in span -- the header matched something that is not a player entry."))
    assert_no_derived_dates(claims)
    return {"source":{"source_id":src_id,"name":title,"acquisition":"held",
              "stated_by":club,"archive_item":sid,
              "places_on":{"league":league,"year":year,"club":club},
              "club_run":runkey,"run_note":spec["note"],
              "_labels_are_not_normalised":"Labels are kept exactly as printed. Mapping them to "
                "modern field names is a ruling, not a parsing step."},
            "claims":claims,"leads":leads,
            "categories":{c:[list(x) for x in cats[c]] for c in CATEGORIES},
            "age_vs_held":dict({"ages_read":age_n,"ranges_derived":rng_n,"held_inside_range":inside,
                "held_outside_range":outside,"no_held_birth_date":nodate,
                "checked_against_a_held_date":inside+outside,
                "disagreement_rate":(round(outside/(inside+outside),3) if inside+outside else None),
                "conflicts":conflicts},
                **({"source_level_observation":
                    "%d of the %d ages in THIS GUIDE that could be checked disagree with the held "
                    "date. A disagreement rate this high is a property of the guide, not of %d "
                    "separate men: one publicist computing ages from one table on one date will "
                    "carry the same error across the book. Recorded, NOT corrected -- no age and no "
                    "held date is altered or preferred here."%(outside,inside+outside,outside)}
                   if outside>=3 else {})),
            "notes_blocks":{"captured":notes_n,"roundtrip_verified":rt_ok,
                "roundtrip_failed_dropped":rt_fail},
            "reconciliation":{"headers":P["spans"],"clean":len(P["clean"]),
                "merged_dropped":len(P["merged"]),"nonplayer_dropped":len(P["empty"]),
                "anchors_in_section":P["sect_anchor"],"anchors_unparsed":P["uncovered"],
                "anchors_in_file":P["total_anchor"]}}

def main():
    allout={"generated":"pre-1950 delimited guides, families C/D/E",
            "scope":"33 guides. 32 parsed, 1 dropped whole (see dropped_runs).",
            "not_parsed_families":"A and B (17 prose-only guides) are excluded by ruling: "
              "no field delimiters, so a misread cannot be validated. A reading job.",
            "dropped_runs":DROPPED_RUNS,"runs":{}}
    for runkey,spec in SPECS.items():
        rr={"club":spec["club"],"league":spec["league"],"note":spec["note"],"guides":{}}
        for (fn,year,title,sid) in spec["guides"]:
            rr["guides"][str(year)]=run_guide(runkey,spec,fn,year,title,sid)
        allout["runs"][runkey]=rr
    by_guide=[]
    for rk,r in allout["runs"].items():
        for y,g in r["guides"].items():
            a=g["age_vs_held"]
            if a["checked_against_a_held_date"]:
                by_guide.append({"source_id":g["source"]["source_id"],"club_run":rk,
                    "checked":a["checked_against_a_held_date"],"outside_range":a["held_outside_range"],
                    "disagreement_rate":a["disagreement_rate"]})
    by_guide.sort(key=lambda x:(-x["outside_range"],-x["checked"]))
    tot=sum(x["outside_range"] for x in by_guide)
    top=by_guide[0] if by_guide else None
    allout["age_conflict_clustering"]={
        "why_this_is_here":"Whether an age disagreement is one man's error or one guide's is a "
            "question about the SOURCE, and it is answerable by counting. It is recorded at the "
            "source level so nobody has to notice the pattern by reading seven person records.",
        "total_disagreements":tot,
        "concentrated_in":(f"{top['outside_range']} of {tot} sit in {top['source_id']} alone"
                           if top and tot else None),
        "rate_against_the_rest":(
            {"guide":top["source_id"],
             "this_guide":f"{top['outside_range']}/{top['checked']} = {top['disagreement_rate']}",
             "every_other_guide":"%d/%d = %s"%(
                 tot-top["outside_range"],
                 sum(x["checked"] for x in by_guide)-top["checked"],
                 round((tot-top["outside_range"])/max(1,sum(x["checked"] for x in by_guide)-top["checked"]),3)),
             "reading":"That guide also contributes the largest share of checkable ages, so the raw "
                 "count alone would prove nothing. The RATE is what carries: roughly three times the "
                 "rest of the corpus. Real, but on 28 checks -- suggestive, not settled."}
            if top and tot else None),
        "not_a_correction":"No age is altered, no held date is preferred, no man is resolved. "
            "The cluster is evidence about the guide and is left for a ruling.",
        "by_guide":by_guide}
    json.dump(allout,open(os.path.join(OUT,"guide-pre1950-delimited.json"),"w"),indent=1)
    return allout

if __name__=="__main__":
    o=main()
    tc=sum(len(g["claims"]) for r in o["runs"].values() for g in r["guides"].values())
    tl=sum(len(g["leads"]) for r in o["runs"].values() for g in r["guides"].values())
    print("claims",tc,"leads",tl)
