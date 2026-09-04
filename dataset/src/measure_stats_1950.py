"""Does 1950 carry enough statistics to derive ratings? Measure before deciding."""
import os,sys,re,html,json,collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import fetch_statscrew as F
BASE=os.path.join(HERE,'..')

SECTIONS=("Passing","Rushing","Receiving","Interceptions","Punt Returns","Kick Returns",
          "Defense and Fumbles","Total Scoring","Punting","Kicking")

def rows_of(seg):
    """StatsCrew emits <tbody><td> with NO opening <tr>. Split on </tr> instead of
    requiring <tr>, or every first row of every stat table is silently dropped."""
    for chunk in seg.split("</tr>"):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", chunk, re.S)]
        if cells:
            yield cells


def sections_with_1950(page):
    t = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    out = {}
    marks = [(m.start(), m.group(1).rstrip(":")) for m in re.finditer(r"<h2>([^<]+)</h2>", t)]
    marks.append((len(t), None))
    for i, (pos, name) in enumerate(marks[:-1]):
        if name not in SECTIONS:
            continue
        seg = t[pos:marks[i + 1][0]]
        for cells in rows_of(seg):
            if cells[0] == "1950":
                nums = [c for c in cells[2:] if re.fullmatch(r"-?[\d.]+", (c or "").replace("\xa0", ""))]
                if nums:
                    out[name] = cells
                break
    return out


def main():
    store=json.load(open(os.path.join(BASE,'build','nfl-1950.json')))
    # person -> exported PGM3 position
    exp=json.load(open(os.path.join(BASE,'build','PGMRoster_1950.json')))
    slug_of={}
    for d in store['denotations']:
        ma=d.get('matched_against') or ''
        m=re.search(r'statscrew:(p-[a-z0-9]+)',ma)
        if m: slug_of.setdefault(d['person'],m.group(1))
    # map person -> position via claims
    pos={}
    for c in store['claims']:
        if c['predicate']=='position':
            pos.setdefault(c['subject'][1], c['value']['code'])
    # PGM3 position from the map
    pmap=json.load(open(os.path.join(BASE,'export','position_map.json')))['tokens']
    per=collections.defaultdict(lambda: collections.Counter())
    checked=0
    for person,slug in sorted(slug_of.items()):
        p3=pmap.get(pos.get(person,'').split('-')[0])
        if not p3: continue
        try: secs=set(sections_with_1950(F.person(slug)))
        except Exception: continue
        checked+=1
        per[p3]['n']+=1
        if secs: per[p3]['any']+=1
        for s in secs: per[p3][s]+=1
    print(f"players checked: {checked}\n")
    print(f"{'pos':5s} {'n':>4} {'any stat':>9} {'%':>6}   commonest sections")
    order=sorted(per, key=lambda p:-(per[p]['any']/max(1,per[p]['n'])))
    for p in order:
        c=per[p]; n=c['n']; a=c['any']
        top=[f"{k} {v}" for k,v in c.most_common() if k not in ('n','any')][:3]
        print(f"{p:5s} {n:4d} {a:9d} {100*a/n:5.0f}%   {', '.join(top)}")
    json.dump({p:dict(c) for p,c in per.items()},
              open(os.path.join(BASE,'build-reports','stats-coverage-1950.json'),'w'),indent=1,sort_keys=True)

if __name__=="__main__": main()
