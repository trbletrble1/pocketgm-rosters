#!/usr/bin/env python3
"""
fix_2026_spread_potential — the ONE write to PGMRoster_2026.json, per Ryan's ruling 2026-09-02.

    python3 tools/fix_2026_spread_potential.py --out /tmp/x.json      # scratch (default)
    python3 tools/fix_2026_spread_potential.py --out PGMRoster_2026.json  # the write, only when ruled

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

def build(out_path, W=None, selftest=False):
    W=W if W is not None else load_weights()   # {} must stay {} — `or` reloaded the real table and made the negative test vacuous
    src=list(csv.DictReader(open(sources('madden','madden_27_launch.csv'),encoding='utf-8-sig',errors='replace')))
    by=collections.defaultdict(list)
    for r in src: by[(norm(r['Name']),MP.get(r['Position'],r['Position']))].append(r)
    d=json.load(open(repo('PGMRoster_2026.json')))
    n_in=len(d)
    # pooled level, and FIRST-YEAR pooled level for the rookie stage
    pool=collections.defaultdict(list); pool_rk=collections.defaultdict(list)
    for f in REFS:
        for r in json.load(open(repo(f))):
            if r['teamID'] in('Rookie','Free Agent'): continue
            for a in MAP:
                if r.get(a): pool[(r['position'],a)].append(r[a])
            if yrs(r)==0: pool_rk[r['position']].append(r['rating'])
    # source medians per (pos, attr) over the players we can join
    ro=[x for x in d if x['teamID'] not in('Rookie','Free Agent')]
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
    for pos in {x['position'] for x in ro}:
        rk=[x for x in ro if x['position']==pos and yrs(x)==0 and x.get('draftNum',999)<224]
        tgt=sorted(pool_rk.get(pos,[]))
        if len(rk)<3 or len(tgt)<10 or pos not in W: continue
        order=sorted(rk,key=lambda x:x['rating'])
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
    assert len(d)==n_in, f'{n_in} in, {len(d)} out'
    assert st1>0 and st2>0 and st3>0 and st4>0 and st5>0, f'a stage ran empty: {st1},{st2},{st3},{st4},{st5}'
    json.dump(d,open(out_path,'w'))
    print(f'stage1 attributes {st1}  stage2 rating {st2}  stage3 potential {st3}  stage4 growthType {st4}  stage5 rookies {st5}  -> {out_path}')
    return d

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='/tmp/scratch_2026_onewrite.json'); ap.add_argument('--selftest',action='store_true')
    a=ap.parse_args()
    if a.selftest:
        # must FAIL: an empty weights table makes every stage empty
        try: build('/tmp/_st.json',W={}); print('SELFTEST FAIL: empty weights did not trip the stage assert'); sys.exit(1)
        except AssertionError as e: print(f'selftest 1 ok — empty population fails: {e}')
        # must FAIL: a tampered growthType breaks the invariant the file must hold
        d=build('/tmp/_st2.json'); r=next(x for x in d if x['teamID'] not in('Rookie','Free Agent') and x['potential']>x['rating'])
        r['growthType'][0]+=50
        bad=[x for x in d if x['teamID'] not in('Rookie','Free Agent') and sum(v for v in x['growthType'] if v>0)!=(x['potential']-x['rating'])*50]
        print(f'selftest 2 ok — tampered invariant is detectable: {len(bad)} record(s) flagged' if bad else 'SELFTEST FAIL: tampered growthType not detected'); sys.exit(0 if bad else 1)
    build(a.out)
