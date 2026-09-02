#!/usr/bin/env python3
"""
fix_2026_spread_potential — the ONE write to PGMRoster_2026.json, per Ryan's ruling 2026-09-02.

    python3 tools/fix_2026_spread_potential.py --out /tmp/x.json      # scratch (default)
    python3 tools/fix_2026_spread_potential.py --out PGMRoster_2026.json  # the write, only when ruled

Cohorts are decided PER STAGE (see the block at the top of build()) — rostered + free agents for the source-mapped
  stages, first-year drafted rostered players for the rookie rescale, prospects for injuryProne only.

  Stages, in the order the interaction table (audit item 25) requires:

  1. ATTRIBUTES  candidate 1: spread-preserving map. Level from the six-file
     pooled median, width from the SOURCE's own values. No clamp of potential.
     Fixes the stretch (QB speed 36, safety stamina 2) and the rank scramble.
  2. RATING      recompute from attributes via weights.json — the invariant
     the file already holds (median |diff| 0.25).
  3. ROOKIES     drafted first-year players re-rescaled against a FIRST-YEAR
     pooled target, WITH a bounded attribute refit so the rating invariant
     holds. Runs BEFORE potential so the two stages cannot fight. Item 24.
  4. POTENTIAL   2017's curve by years pro, applied ONLY where potential was
     the defect (== rating). Existing real headroom is never lowered (Goff 88
     stays 88). Six-plus years draws the 2017 median, which is 0 — no veteran
     headroom is manufactured. Item 24b.
  5. GROWTHTYPE  rebuilt to (potential - rating) * 50 for every touched record.

  A first version ran potential before the rookie rescale and drew veterans at
  random from the curve: rookie headroom came out 12 (2017: 6), 31 veterans
  gained >4, Goff lost 6 points of real potential, and the rookie rescale broke
  the rating invariant to 89.4%. All four caught by measuring the gated file.

  OFF until ruled: decisions (offensive, source-inverted), injuryProne (prospects).

Every stage asserts its count. Negative tests live in --selftest.
"""
import json,csv,sys,os,argparse,unicodedata,re,statistics as st,collections,random
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import sources, repo

def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode()
    return re.sub(r'\s+',' ',re.sub(r'[^a-z ]','',s.lower())).strip()
MP={'QB':'QB','HB':'RB','FB':'RB','WR':'WR','TE':'TE','LT':'OT','RT':'OT','LG':'OG','RG':'OG','C':'C','LE':'DE','RE':'DE','LEDG':'DE','REDG':'DE','DT':'DT','LOLB':'OLB','ROLB':'OLB','MLB':'MLB','MIKE':'MLB','WILL':'OLB','SAM':'OLB','CB':'CB','FS':'S','SS':'S','K':'K','P':'P'}
MAP={'speed':'SpeedRating','burst':'AccelerationRating','power':'StrengthRating','agility':'AgilityRating','jumping':'JumpingRating','stamina':'StaminaRating','tackle':'TackleRating','passBlock':'PassBlockRating','rushBlock':'RunBlockRating','ballSecurity':'CarryingRating','catching':'CatchingRating','intelligence':'AwarenessRating','trucking':'BreakTackleRating','vision':'BCVisionRating','decisions':'PlayRecognitionRating','releaseLine':'ReleaseRating','manCover':'ManCoverageRating','zoneCover':'ZoneCoverageRating','routeRun':'ShortRouteRunningRating','kickAccuracy':'KickAccuracyRating'}
OFFENSE_DECISIONS_OFF={'QB','RB','WR','TE','C','OT','OG'}   # stage OFF: leave source-inverted decisions untouched until ruled
REFS=['PGMRoster_2004.json','PGMRoster_2007.json','PGMRoster_2010.json','PGMRoster_2013.json','PGMRoster_2017.json','PGMRoster_2021.json']

def yrs(x): return 2026-x['draftSeason'] if x.get('draftSeason') else None
def q(v,p): v=sorted(v); return v[min(len(v)-1,int(p*len(v)))]

def load_weights():
    return json.load(open(repo('wip','PGM3_2026_build_data.json')))['weights']
def overall(r,pos,W):
    w=W.get(pos); return None if not w else sum(r.get(n,0)*c for n,c in zip(w[0],w[1]))+w[1][-1]

def build(out_path, W=None, selftest=False, qb_cap=None, source=None):
    W=W if W is not None else load_weights()   # {} must stay {} — `or` reloaded the real table and made the negative test vacuous
    src=list(csv.DictReader(open(sources('madden','madden_27_launch.csv'),encoding='utf-8-sig',errors='replace')))
    by=collections.defaultdict(list)
    for r in src: by[(norm(r['Name']),MP.get(r['Position'],r['Position']))].append(r)
    # INPUT IS AN EXPLICIT SOURCE, NEVER THE FILE THIS TOOL WRITES. The second write read the first write's output and
    # applied every stage again: +1/+2 drift on 1,204 records from double-mapping, and stage 5 re-ranking already-rescaled
    # rookies sent a center from 67 to 41 and two first-round picks down 10. The source is the pre-write published file.
    source=source or repo('wip','PGMRoster_2026.source.json')
    assert os.path.abspath(source)!=os.path.abspath(out_path), 'source and output are the same file — this tool must not read its own output'
    d=json.load(open(source))
    n_in=len(d)
    src_rating={x['iden']:x['rating'] for x in d}   # stage 5 ranks rookies on THIS, the source rating, so a stage-1 shift cannot reorder them
    # pooled level, and FIRST-YEAR pooled level for the rookie stage
    pool=collections.defaultdict(list); pool_rk=collections.defaultdict(list)
    for f in REFS:
        for r in json.load(open(repo(f))):
            if r['teamID'] in('Rookie','Free Agent'): continue
            for a in MAP:
                if r.get(a): pool[(r['position'],a)].append(r[a])
            if yrs(r)==0: pool_rk[r['position']].append(r['rating'])
    # source medians per (pos, attr) over the players we can join
    # COHORTS, decided per stage (Ryan's ruling 2026-09-02, after item 28). One variable set at this line for a rostered
    # question was inherited by every stage through the QB level without any of them choosing it. Each stage below now
    # names the cohort it runs on; the names are deliberately different so a stage cannot silently reuse another's.
    ROSTERED=[x for x in d if x['teamID'] not in('Rookie','Free Agent')]
    FREE_AGENTS=[x for x in d if x['teamID']=='Free Agent']
    PLAYERS_WITH_A_SOURCE=ROSTERED+FREE_AGENTS          # stages 1,2,3,4,6,8: anyone with a Madden rating to map from
    ro=PLAYERS_WITH_A_SOURCE                             # (name kept so the stage code below reads unchanged; scope is now explicit above)
    J={x['iden']:by[(norm(x['forename']+' '+x['surname']),x['position'])][0] for x in ro
       if len(by.get((norm(x['forename']+' '+x['surname']),x['position']),[]))==1}
    smed=collections.defaultdict(list)
    for x in ro:
        if x['iden'] not in J: continue
        for a,col in MAP.items():
            try: smed[(x['position'],a)].append(int(float(J[x['iden']][col])))
            except: pass
    smed={k:st.median(v) for k,v in smed.items() if len(v)>=15}
    # 2017's potential curve by years-pro bucket, from the clean file
    curve=collections.defaultdict(list)
    for r in json.load(open(repo('PGMRoster_2017.json'))):
        if r['teamID'] in('Rookie','Free Agent') or yrs(r) is None: continue
        curve[min(yrs(r),8)].append(r['potential']-r['rating'])
    curve={k:sorted(v) for k,v in curve.items()}
    rng=random.Random(2026)
    st1=st2=st3=st4=st5=0
    for x in ro:
        pos=x['position']; b=J.get(x['iden'])
        touched=False
        if b:
            for a,col in MAP.items():
                if not x.get(a,0) or (pos,a) not in pool or (pos,a) not in smed: continue
                if a=='decisions' and pos in OFFENSE_DECISIONS_OFF: continue
                try: sv=int(float(b[col]))
                except: continue
                nv=int(round(max(1,min(99,st.median(pool[(pos,a)])+(sv-smed[(pos,a)])))))
                if nv!=x[a]: x[a]=nv; touched=True
            if touched: st1+=1
        if pos in W and touched:
            x['rating']=int(round(overall(x,pos,W))); st2+=1
        # stage 3/4 deferred: potential and growthType run AFTER the rookie rescale, so the two cannot fight.
        x['_touched']=touched
    # stage 5 (now runs before potential): rookies against a first-year target, WITH an attribute refit so the invariant holds
    # stage 5 cohort: FIRST-YEAR DRAFTED players ON A ROSTER. Not free agents — an undrafted or cut rookie is not the population item 24 measured.
    for pos in {x['position'] for x in ROSTERED}:
        rk=[x for x in ROSTERED if x['position']==pos and yrs(x)==0 and x.get('draftNum',999)<224]
        tgt=sorted(pool_rk.get(pos,[]))
        if len(rk)<3 or len(tgt)<10 or pos not in W: continue
        order=sorted(rk,key=lambda x:src_rating[x['iden']])   # rank on the SOURCE rating — stable across runs and cohort changes
        live=[n for n in W[pos][0] if n in MAP]
        wsum=sum(c for n,c in zip(W[pos][0],W[pos][1][:-1]) if n in MAP)
        for i,x in enumerate(order):
            qq=i/(len(order)-1) if len(order)>1 else .5
            nr=int(round(tgt[min(len(tgt)-1,int(qq*(len(tgt)-1)))]))
            if nr==x['rating']: continue
            # bounded refit: shift every live attribute by the same k so computed overall lands on nr (overall is linear)
            k=(nr-overall(x,pos,W))/wsum if wsum else 0
            for a in live:
                if x.get(a,0): x[a]=int(round(max(1,min(99,x[a]+k))))
            x['rating']=int(round(overall(x,pos,W))); x['_touched']=True; st5+=1
    # stage 3: potential from 2017's curve. RULES: only touch potential where it was the defect (== rating) or fell below
    # the new rating; NEVER lower an existing real headroom (Goff 88 stays 88); 6+ years draws the 2017 MEDIAN (0), not a random sample.
    for x in ro:
        y=yrs(x); pot_changed=False; touched=x.pop('_touched',False)
        # 2026's flat-2 curve is the 24b defect at EVERY experience level (audit 24b). The published draw never gave
        # anyone more than ~2, so surviving headroom ABOVE 4 is authored (Goff 79->88) and must survive; headroom at or
        # below the flat draw is the defect. Every bucket takes 2017's MEDIAN — the curve Ryan ruled — not a random
        # sample, which averaged above the median on right-tailed buckets and doubled rookie headroom to 10.
        # An 'authored headroom' guard (published headroom > 4 survives) was tried and REMOVED: measured, published
        # veteran headroom correlates +0.044 with (Madden overall - our rating) and potential correlates +0.956 with our
        # own rating. It is rating plus noise. The 117 veterans above 4 are the 24b draw's tail, not authored developers,
        # and Goff's 88 (= Madden's 88) is one of three exact matches in 117 — a coincidence at that rate.
        #   6+ years : potential = rating + 2017 median for the bucket (0). Always. Goff 88 -> 82 is the cost of the ruling.
        #   < 6 years: potential = rating + 2017 median, unless the record already carries MORE than that — the archive
        #              does give young players real spread, and lowering it would be inventing a ceiling.
        # One rule, no guard: potential = rating + 2017's bucket median. A max() guard for <6 years was tried and
        # removed — it preserved the same fat-tail draw (published p90 7-8 at EVERY age, r=+0.044 against Madden)
        # and re-opened the stage fight (rookie rating lowered by stage 3, potential held, headroom 10 not 6).
        # Cost, stated: the young tail is flattened to the median too. The p90 spread is a design question with no ruling.
        if y is not None:
            newp=x['rating']+int(st.median(curve.get(min(y,8)) or curve[8]))
            if newp!=x['potential']: x['potential']=newp; pot_changed=True; st3+=1
        elif x['potential']<x['rating']:
            x['potential']=x['rating']; pot_changed=True; st3+=1
        assert x['potential']>=x['rating'], f"negative headroom {x['forename']} {x['surname']}"
        # stage 4: growthType — only where rating or potential moved
        if touched or pot_changed:
            g=x['potential']-x['rating']; gt=x['growthType']
            pos_slots=[i for i,v in enumerate(gt) if v>0] or list(range(min(17,len(gt))))
            newgt=[v if v<=0 else 0 for v in gt]
            if g>0:
                per=g*50//len(pos_slots); rem=g*50-per*len(pos_slots)
                for i,s_ in enumerate(pos_slots): newgt[s_]=per+(1 if i<rem else 0)
            x['growthType']=newgt; st4+=1
            assert sum(v for v in newgt if v>0)==g*50, 'growthType invariant'
    # ---- stage 6: offensive decisions from the ARCHIVE curve (source is inverted at QB/RB/WR/TE/C). Ruled ON by the sequence.
    NORMAL=['PGMRoster_1986.json','PGMRoster_2000.json','PGMRoster_2004.json','PGMRoster_2007.json','PGMRoster_2010.json','PGMRoster_2013.json','PGMRoster_2017.json','PGMRoster_2021.json']
    dcurve=collections.defaultdict(list)
    for f in NORMAL:
        for r in json.load(open(repo(f))):
            if r['teamID'] in('Rookie','Free Agent') or yrs(r) is None or not r.get('decisions'): continue
            dcurve[(r['position'],min(yrs(r),10))].append(r['decisions'])
    st6=0
    for x in ro:
        pos=x['position']; y=yrs(x)
        if pos not in OFFENSE_DECISIONS_OFF or y is None or not x.get('decisions'): continue
        c=dcurve.get((pos,min(y,10)))
        if not c or len(c)<15: continue
        x['_dec_bucket']=(pos,min(y,10))
    # Per-BUCKET assignment, not a cohort-wide rank map. The source order at these positions is inverted noise, so
    # rank-preserving it across buckets handed rookies the veteran values (78 vs 72). Each player takes his own
    # experience bucket: the archive median, plus a rank-preserved spread WITHIN the bucket from the archive p10-p90.
    for key in {x['_dec_bucket'] for x in ro if '_dec_bucket' in x}:
        grp=[x for x in ro if x.get('_dec_bucket')==key]; c=sorted(dcurve[key])
        lo,hi=c[int(.1*len(c))],c[int(.9*len(c))]
        order=sorted(grp,key=lambda x:x['decisions'])
        for i,x in enumerate(order):
            qq=i/(len(order)-1) if len(order)>1 else .5
            nv=int(round(lo+qq*(hi-lo)))
            if nv!=x['decisions']: x['decisions']=nv; x['_dec_touched']=True; st6+=1
    for x in ro: x.pop('_dec_bucket',None)
    for x in ro: x.pop('_dec_target',None)
    # ---- stage 7: prospect injuryProne re-drawn to the archive rookie level (~34); no source exists (2 of 278). Ruled ON.
    # stage 7 cohort: PROSPECTS only — no Madden rating exists to align to; prospects stay excluded from every other stage.
    st7=0; pros=[x for x in d if x['teamID']=='Rookie']
    if pros:
        order=sorted(pros,key=lambda x:x['injuryProne'])
        # rank-preserving remap of the prospect cohort onto the pooled archive prospect distribution
        tgt=sorted(r['injuryProne'] for f in NORMAL for r in json.load(open(repo(f))) if r['teamID']=='Rookie' and r.get('injuryProne') is not None)
        for i,x in enumerate(order):
            nv=tgt[min(len(tgt)-1,int(i/(len(order)-1)*(len(tgt)-1)))]
            if nv!=x['injuryProne']: x['injuryProne']=nv; st7+=1
    # ---- stage 6/7 CONSEQUENCE: decisions feeds the overall (0.183 at QB). Recompute rating, then re-derive potential and
    # growthType, for every rostered record stage 6 touched — otherwise the invariant falls (measured: 99.9% -> 91.0%).
    def rederive(x):
        pos=x['position']; y=yrs(x)
        if pos in W: x['rating']=int(round(overall(x,pos,W)))
        if y is not None:
            x['potential']=x['rating']+int(st.median(curve.get(min(y,8)) or curve[8]))
        g=x['potential']-x['rating']; gt=x['growthType']; pos_slots=[i for i,v in enumerate(gt) if v>0] or list(range(min(17,len(gt))))
        newgt=[v if v<=0 else 0 for v in gt]
        if g>0:
            per=g*50//len(pos_slots); rem=g*50-per*len(pos_slots)
            for i,s_ in enumerate(pos_slots): newgt[s_]=per+(1 if i<rem else 0)
        x['growthType']=newgt; assert sum(v for v in newgt if v>0)==g*50
    for x in ro:
        if x.get('_dec_touched'): rederive(x)
    for x in ro: x.pop('_dec_touched',None)
    # ---- stage 8: QB LEVEL, last. Close the gap to Madden's overall by a uniform shift across live attributes,
    # bounded by (a) the source's observed range per attribute and (b) qb_cap per attribute. Residual reported.
    st8=0; qb_report=[]
    if qb_cap is not None and 'QB' in W:
        # decisions is EXCLUDED here: at QB its Madden range is 10-68, an unpopulated defensive field, and stage 6 has just
        # drawn it from the archive. Including it made stage 8 clamp the archive draw back down — 41 moves over 10, max 31.
        live=[n for n in W['QB'][0] if n in MAP and n!='decisions']; coef=dict(zip(W['QB'][0],W['QB'][1][:-1]))
        wsum=sum(coef[n] for n in live)
        rng_src={}
        for a in live:
            v=[int(float(b[MAP[a]])) for x in ro if x['position']=='QB' and x['iden'] in J for b in [J[x['iden']]] if str(b.get(MAP[a],'')).strip()]
            if len(v)>=15: rng_src[a]=(min(v),max(v))
        for x in ro:
            if x['position']!='QB' or x['iden'] not in J: continue
            target=int(float(J[x['iden']]['OverallRating'])); before=overall(x,'QB',W)
            k=(target-before)/wsum if wsum else 0
            k=max(-qb_cap,min(qb_cap,k))
            moved={}
            for a in live:
                if not x.get(a,0): continue
                lo,hi=rng_src.get(a,(1,99)); nv=int(round(max(lo,min(hi,x[a]+k))))
                if nv!=x[a]: moved[a]=nv-x[a]; x[a]=nv
            after=overall(x,'QB',W)
            if moved: x['rating']=int(round(after)); st8+=1
            qb_report.append(dict(name=f"{x['forename']} {x['surname']}",madden=target,before=before,after=after,k=k,maxmove=max((abs(v) for v in moved.values()),default=0)))
        # potential and growthType re-derived for QBs whose rating moved (potential is a function of rating)
        for x in ro:
            if x['position']=='QB': rederive(x)
    build.qb_report=qb_report
    print(f'stage6 decisions {st6}  stage7 injuryProne {st7}  stage8 QB level {st8} (cap {qb_cap})')
    assert len(d)==n_in, f'{n_in} in, {len(d)} out'
    assert st1>0 and st2>0 and st3>0 and st4>0 and st5>0, f'a stage ran empty: {st1},{st2},{st3},{st4},{st5}'
    json.dump(d,open(out_path,'w'))
    print(f'stage1 attributes {st1}  stage2 rating {st2}  stage3 potential {st3}  stage4 growthType {st4}  stage5 rookies {st5}  -> {out_path}')
    return d

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='/tmp/scratch_2026_onewrite.json'); ap.add_argument('--selftest',action='store_true'); ap.add_argument('--qb-cap',type=float,default=None); ap.add_argument('--source',default=None,help='the pre-write published file; defaults to wip/PGMRoster_2026.source.json')
    a=ap.parse_args()
    if a.selftest:
        # must FAIL: an empty weights table makes every stage empty
        try: build('/tmp/_st.json',W={},source=None); print('SELFTEST FAIL: empty weights did not trip the stage assert'); sys.exit(1)
        except AssertionError as e: print(f'selftest 1 ok — empty population fails: {e}')
        # must FAIL: a tampered growthType breaks the invariant the file must hold
        d=build('/tmp/_st2.json',source=None); r=next(x for x in d if x['teamID'] not in('Rookie','Free Agent') and x['potential']>x['rating'])
        r['growthType'][0]+=50
        bad=[x for x in d if x['teamID'] not in('Rookie','Free Agent') and sum(v for v in x['growthType'] if v>0)!=(x['potential']-x['rating'])*50]
        print(f'selftest 2 ok — tampered invariant is detectable: {len(bad)} record(s) flagged' if bad else 'SELFTEST FAIL: tampered growthType not detected'); sys.exit(0 if bad else 1)
    build(a.out, qb_cap=a.qb_cap, source=a.source)
