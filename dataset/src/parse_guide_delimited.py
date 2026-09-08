import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guide_delimited_runs import (POS,_lines,split_entries,anchor_count,read_labels,trailing_prose,
                  LBL_COLON,LBL_DASH,MARITAL)
from guide_delimited_specs import SPECS, G

def _readers(kind):
    return {"colon":[LBL_COLON],"dash":[LBL_DASH],"both":[LBL_COLON,LBL_DASH]}.get(kind,[])

def parse_guide(run, spec, fn, year):
    L=_lines(G+fn); N=len(L)
    style=spec.get("style"); recs=[]; amb=[]
    py=spec.get("per_year",{}).get(year,{})
    anchor=py.get("anchor") or spec.get("anchor")
    labels=py.get("labels") or spec.get("labels")
    notes_lbls=tuple(x.upper() for x in spec.get("notes",()))
    hp=tuple(x.upper() for x in spec.get("honour_parents",()))
    spans=[]
    if style=="packers3" or run=="packers_c":
        h2,h3=spec["hdr2"],spec["hdr3"]
        starts=[]
        for i in range(1,N-1):
            m2=h2.match(L[i])
            if not m2: continue
            m3=None
            for k in (i+1,i+2,i+3):
                if k<N and h3.match(L[k]): m3=h3.match(L[k]); k3=k; break
            if not m3: continue
            nm=None
            for k in (i-1,i-2,i-3):
                if k>=0 and L[k].strip() and not re.match(r"^\s*\d+\s",L[k]):
                    nm=L[k].strip(); break
            if not nm: continue
            starts.append((i,nm,m2,m3,k3))
        for n,(i,nm,m2,m3,k3) in enumerate(starts):
            j=starts[n+1][0]-1 if n+1<len(starts) else N
            spans.append((max(0,i-1),j,{"name":nm,"m2":m2,"m3":m3,"body_from":k3+1}))
    elif style=="rams49":
        h2=spec["hdr2"]; starts=[]
        for i in range(1,N):
            m=h2.match(L[i])
            if not m: continue
            nm=None
            for k in (i-1,i-2,i-3):
                if k>=0 and L[k].strip(): nm=L[k].strip(); break
            if nm: starts.append((i,nm,m))
        for n,(i,nm,m) in enumerate(starts):
            j=starts[n+1][0]-1 if n+1<len(starts) else N
            spans.append((max(0,i-1),j,{"name":nm,"m2":m,"body_from":i+1}))
    else:
        hdr=py.get("header") or spec.get("header")
        conf=spec.get("confirm")
        es=split_entries(L,0,N,hdr)
        if conf:
            crx,win=conf
            es=[(a,b,m) for (a,b,m) in es
                if any(crx.search(L[k]) for k in range(a+1,min(N,a+1+win)))]
        for (a,b,m) in es:
            spans.append((a,b,{"m":m,"body_from":a+1}))
    total_anchor=sum(len(anchor.findall(L[k])) for k in range(N))
    if spans:
        s0=min(a for a,_,_ in spans); s1=max(b for _,b,_ in spans)
    else:
        s0=s1=0
    sect_anchor=sum(len(anchor.findall(L[k])) for k in range(s0,s1))
    covered=0
    for (a,b,meta) in spans:
        na=anchor_count(L,a,b,anchor)
        body=L[meta["body_from"]:b]
        rec={"span":[a,b],"anchors":na,"fields":collections.OrderedDict(),
             "honours":[],"notes":None,"notes_label":None}
        if "m" in meta:
            m=meta["m"]; g=m.groups()
            rec["name_as_printed"]=g[0].strip()
            hf=py.get("hdr_fields") or spec.get("hdr_fields") or []
            for idx,lab in enumerate(hf, start=1):
                if idx<len(g)+0 and g[idx]: rec["fields"][lab]=g[idx].strip()
            if style=="niners":
                if g[1]: rec["fields"]["POSITION (HEADER)"]=g[1].strip()
                rec["fields"]["Height"]=g[2].strip(); rec["fields"]["Weight"]=g[3].strip()
            elif style=="browns":
                rec["fields"]["POSITION (HEADER)"]=g[1].strip()
            elif style=="bills":
                rec["fields"]["POSITION (HEADER)"]=g[1].strip()
                if g[2] and g[2].strip(): rec["fields"]["_hdr_tail"]=g[2].strip()
            elif style=="hornets":
                rec["fields"]["POSITION (HEADER)"]=g[1].strip(); rec["fields"]["Age"]=g[2].strip()
                rec["fields"]["Ht."]=g[3].strip(); rec["fields"]["Wt."]=g[4].strip()
                rec["fields"]["COLLEGE (HEADER)"]=g[5].strip()
            elif style=="colts49":
                rec["fields"]["Age"]=g[1].strip(); rec["fields"]["Height"]=g[2].strip()
                rec["fields"]["Weight"]=g[3].strip()
            elif style=="brooklyn":
                rec["name_as_printed"]=(g[0].strip()+", "+g[1].strip())
                rec["fields"]["Born"]=g[2].strip()
            elif spec.get("hdr_map"):
                for idx,lab in enumerate(spec["hdr_map"], start=1):
                    if idx<len(g) and g[idx]: rec["fields"][lab]=g[idx].strip()
            elif run=="dons" and year==1947:
                blob=g[0].strip()
                mh=re.search(r"[\s,(]([0-9][.\s=]{0,3}[0-9]{1,2})\s*[=~]?\s*$",blob)
                if mh:
                    rec["fields"]["HEIGHT"]=mh.group(1).strip()
                    blob=blob[:mh.start()].strip(" ,.=")
                rec["name_as_printed"]=blob
                rec["fields"]["WEIGHT"]=g[1].strip()
                rec["fields"]["POSITION (HEADER)"]=g[2].strip()
            elif run=="dons" and year==1948:
                rec["fields"]["POSITION (HEADER)"]=g[1].strip()
            elif run=="dons" and year==1949:
                rec["fields"]["POSITION (HEADER)"]=g[1].strip(); rec["fields"]["Age"]=g[2].strip()
                rec["fields"]["Ht."]=g[3].strip(); rec["fields"]["Wt."]=g[4].strip()
        else:
            rec["name_as_printed"]=meta["name"]
            if run in ("packers_c","bears_c","lions_c","steelers_c"):
                g2=meta["m2"].groups(); g3=meta["m3"].groups()
                if g2[0]: rec["fields"]["No."]=g2[0].strip()
                rec["fields"]["POSITION (HEADER)"]=g2[1].strip()
                rec["fields"]["COLLEGE (HEADER)"]=g2[2].strip()
                if run=="lions_c":
                    rec["fields"]["Weight"]=g3[0].strip(); rec["fields"]["Height"]=g3[1].strip()
                    rec["fields"]["Born in"]=g3[2].strip()
                elif run=="steelers_c":
                    rec["fields"]["Height"]=g3[0].strip(); rec["fields"]["Weight"]=g3[1].strip()
                    if g3[2]: rec["fields"]["Born"]=g3[2].strip()
                else:
                    rec["fields"]["Height"]=g3[0].strip(); rec["fields"]["Weight"]=g3[1].strip()
                    if g3[2]: rec["fields"]["Born in"]=g3[2].strip()
            elif run=="rams_1949":
                g2=meta["m2"].groups()
                rec["fields"]["COLLEGE (HEADER)"]=g2[0].strip(); rec["fields"]["Ht"]=g2[1].strip()
                rec["fields"]["Wt"]=g2[2].strip(); rec["fields"]["Age"]=g2[3].strip()
                if g2[4].strip(): rec["fields"]["_hdr_tail"]=g2[4].strip()
        rd=_readers(labels)
        if rd:
            f,h,nt,nl,last=read_labels(body,rd,hp,notes_lbls)
            for k,v in f.items(): rec["fields"].setdefault(k,v)
            rec["honours"]=h; rec["notes"]=nt; rec["notes_label"]=nl
            if rec["notes"] is None:
                # trailing prose starts AFTER the last line a label consumed, never at 0 --
                # otherwise the block would swallow the fields it sits below.
                tp=trailing_prose(body,last)
                if tp and len(tp)>40: rec["notes"]=tp; rec["notes_label"]=None
        else:
            tp=trailing_prose(body,0)
            if tp and len(tp)>40: rec["notes"]=tp; rec["notes_label"]=None
        covered+=na
        (recs if na==1 else amb).append(rec if na==1 else (rec,na))
    merged=[(r,n) for (r,n) in amb if n>1]
    empty=[(r,n) for (r,n) in amb if n==0]
    return {"clean":recs,"ambiguous":amb,"merged":merged,"empty":empty,
            "total_anchor":total_anchor,"sect_anchor":sect_anchor,
            "covered":covered,"uncovered":sect_anchor-covered,
            "section":[s0,s1],"spans":len(spans)}

if __name__=="__main__":
    only=sys.argv[1] if len(sys.argv)>1 else None
    tot=0
    for run,spec in SPECS.items():
        if only and run!=only: continue
        print(f"=== {run} ({spec['club']}) ===")
        for (fn,year,title,sid) in spec["guides"]:
            P=parse_guide(run,spec,fn,year)
            tot+=len(P["clean"])
            print(f"  {year} {fn[:40]:42s} hdrs={P['spans']:3d} clean={len(P['clean']):3d} "
                  f"merged={len(P['merged']):2d} nonplayer={len(P['empty']):2d} "
                  f"anchors(sect)={P['sect_anchor']:3d} unparsed={P['uncovered']:3d} "
                  f"anchors(file)={P['total_anchor']:3d}")
    print("total clean entries:",tot)
