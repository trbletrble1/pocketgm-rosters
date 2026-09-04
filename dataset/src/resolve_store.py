"""Resolve the built store and report the basis distribution. Real data, not a fixture."""
import os,sys,json,collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from model import Store

def load(path, decl_paths):
    s=Store()
    for d in decl_paths: s.add_source(json.load(open(d)))
    raw=json.load(open(path))
    s.persons=set(raw['persons']); s.source_records=raw['source_records']
    s.claims=raw['claims']; s.denotations=raw['denotations']
    s.universe={tuple(x) for x in raw.get('universe',[])}
    for c in s.claims:
        s._by_subject[(tuple(c['subject']) if isinstance(c['subject'],list) else c['subject'],
                       c['predicate'])].append(c)
    return s

def main():
    pass_marker=None
    base=os.path.join(HERE,'..')
    import os as _o
    store_file=_o.environ.get('STORE','nfl-1950.json')
    s=load(os.path.join(base,'build',store_file),
           [os.path.join(base,'declarations','statscrew.json')])
    pol=json.load(open(os.path.join(base,'policy','resolution.json')))
    # scope of each predicate, from the claims that exist
    scope_of={}
    for c in s.claims:
        subj=tuple(c['subject']) if isinstance(c['subject'],list) else c['subject']
        scope_of.setdefault(c['predicate'], subj[0])
    universe_by_scope=collections.defaultdict(set)
    for u in s.universe: universe_by_scope[u[0]].add(u)
    subjects={p: universe_by_scope[sc] for p,sc in scope_of.items()}
    print(f"{'predicate':16s} {'n':>5} " + " ".join(f"{b:>10s}" for b in
          ('observed','absent','unknown','contested')))
    contested=[]
    for pred in sorted(subjects):
        counts=collections.Counter()
        for subj in subjects[pred]:
            r=s.resolve(subj,pred,pol)
            counts[r['basis']]+=1
            if r['basis']=='contested': contested.append((pred,subj,r))
        print(f"{pred:16s} {sum(counts.values()):5d} " +
              " ".join(f"{counts.get(b,0):10d}" for b in ('observed','absent','unknown','contested')))
    print(f"\nCONTESTED: {len(contested)}")
    for pred,subj,r in contested[:20]:
        vals=[c['value'] for c in r['candidates']] if 'candidates' in r else []
        print(f"  {pred} {subj}")
        for cand in r.get('candidates',[]):
            print(f"      {cand['value']!r}  stated_by={cand['stated_by']}")
    json.dump([{'predicate':p,'subject':list(su),'candidates':r.get('candidates')}
               for p,su,r in contested], open(os.path.join(base,'build','contested-'+store_file),'w'), indent=1)

if __name__=="__main__": main()
