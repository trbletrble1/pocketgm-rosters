import sys
"""Pass A1 -- replace the `stamina == 1` fill block in the published files.

1,622 records all-cohort (1,267 rostered) across six of seven files carry
stamina 1, which means the player gasses out. 2010 has none, which is the proof
this is a fill artifact and not a distribution: one file built the same field
with no such block.

Order of preference, per the task:
  1. re-derive from that file's own Madden source via PSTA (never PSTM), by
     position-wise quantile map onto the file's own non-1 stamina distribution
  2. where no source row covers the player, a conditional draw from that file's
     own non-1 population at the same position and a nearby rating

Not the median. Replacing 1 with the median reintroduces a fill one step less
visible than the one being removed. The conditional draw is used because
stamina genuinely tracks rating within position in the healthy population
(rho +0.35 to +0.74), so a draw conditioned on position and rating reproduces
both the marginal and that relationship without manufacturing a precision the
file never had -- a deterministic rating map would give the filled cohort a
perfect rank correlation against a real ~0.5.

Formatting is detected per file and asserted byte-identical on round-trip
before any write. The seven files do not share a convention: 1986 is spaced,
2004/2007/2010 compact, and 2013/2017/2021 compact with ASCII escaping.
"""
import json, csv, sys, os, hashlib, collections, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_2000 as b
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm3_paths import sources, require

SRC = {2004: sources('madden', '2004 - PLAY.csv'),
       2007: sources('madden', '2007 - PLAY.csv'),
       2013: sources('madden', '2013 - PLAY.csv'),
       2017: sources('madden', '2017JINXROSTER_V21.0 - PLAY.csv'),
       2021: sources('madden', '2021JINXROSTER V23 - PLAY.csv')}
FILES = [1986, 2004, 2007, 2010, 2013, 2017, 2021]
FILL  = 1


def detect_format(path):
    """Return dumps kwargs that reproduce the file byte for byte, or die."""
    raw = open(path, encoding='utf-8').read()
    d = json.loads(raw)
    for sep in ((',', ':'), (', ', ': ')):
        for asc in (False, True):
            kw = dict(ensure_ascii=asc, separators=sep)
            if json.dumps(d, **kw) == raw:
                return d, kw
    raise SystemExit(f'{path}: no dumps setting reproduces the file; '
                     f'writing it would churn the whole diff')


def load_source(path):
    idx = collections.defaultdict(list)
    for r in csv.DictReader(open(path, encoding='latin-1')):
        try:
            pos = b.PPOS[int(r['PPOS'])]
        except Exception:
            continue
        v = r.get('PSTA', '').strip()
        if v.lstrip('-').isdigit():
            idx[(b.norm(f"{r['PFNA']} {r['PLNA']}"), pos)].append(int(v))
    return idx


def quantile_map(src_vals, tgt_vals):
    """PSTA -> this file's own stamina scale, by matched percentile."""
    s = sorted(src_vals); t = sorted(tgt_vals)
    def f(x):
        lo = sum(1 for v in s if v < x); hi = sum(1 for v in s if v <= x)
        pct = ((lo + hi) / 2) / len(s)
        return t[min(len(t) - 1, max(0, int(pct * len(t))))]
    return f


def draw(pool, rating, key, band=5):
    """Conditional draw from the file's own non-1 population, seeded on name."""
    near = [v for r, v in pool if abs(r - rating) <= band]
    while len(near) < 12 and band < 40:
        band += 5
        near = [v for r, v in pool if abs(r - rating) <= band]
    if not near:
        near = [v for _, v in pool]
    h = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    return sorted(near)[h % len(near)]


def fix(year, dry=False, _hook=None):
    path = f'PGMRoster_{year}.json'
    recs, kw = detect_format(path)
    n_in = len(recs)
    ones = [p for p in recs if p['stamina'] == FILL]
    if not ones:
        print(f'  {year}: no stamina-{FILL} records, skipped')
        return 0, 0, 0

    # The healthy population is NOT simply "everything that is not 1". Several
    # files carry ADDITIONAL low-value fill blocks -- 2021 has 29 wide
    # receivers at exactly 5 and 9 tackles at 16, single-position blocks at a
    # single value, which a genuine tail never is. 2010 and 2004, the two files
    # with no stamina-1 block, have no such blocks either.
    #
    # Drawing from a contaminated pool reproduces the contamination: a first
    # run of this tool pushed 2021's stamina-2 block from 37 records to 51 and
    # produced non-monotonic PSTA deciles (30 and 13 mid-range). Excluding
    # these from the pool is not scope creep, it is finding the real cohort.
    # The blocks themselves are left alone and reported -- repairing them is a
    # separate ruling.
    suspect = {v for v, n in collections.Counter(
        q['stamina'] for q in recs if q['stamina'] < 40).items() if n >= 8}
    suspect.add(FILL)
    healthy = [p for p in recs if p['stamina'] not in suspect]
    assert healthy, f'{year}: no healthy population to map onto'
    before_all = [dict(p) for p in recs]

    src = load_source(SRC[year]) if year in SRC else {}
    tgt_by_pos = collections.defaultdict(list)
    pool_by_pos = collections.defaultdict(list)
    for p in healthy:
        tgt_by_pos[p['position']].append(p['stamina'])
        pool_by_pos[p['position']].append((p['rating'], p['stamina']))

    src_by_pos = collections.defaultdict(list)
    for (nm, pos), vs in src.items():
        src_by_pos[pos].extend(vs)
    qmap = {pos: quantile_map(src_by_pos[pos], tgt_by_pos[pos])
            for pos in tgt_by_pos if src_by_pos.get(pos) and tgt_by_pos.get(pos)}

    matched = drawn = 0
    for p in recs:
        if p['stamina'] != FILL:
            continue
        k = (b.norm(f"{p['forename']} {p['surname']}"), p['position'])
        if k in src and p['position'] in qmap:
            p['stamina'] = int(qmap[p['position']](statistics.median(src[k])))
            matched += 1
        else:
            pool = pool_by_pos.get(p['position']) or [(x['rating'], x['stamina']) for x in healthy]
            p['stamina'] = int(draw(pool, p['rating'], f"{year}|{k[0]}|{k[1]}"))
            drawn += 1

    # testing seam: lets the assertion tests below mutate records AFTER the
    # repair and BEFORE the guards, which is the only way to prove the guards
    # can fail. Corrupting the input instead is caught by the snapshot and
    # proves nothing -- that mistake made four of these look toothless.
    if _hook:
        _hook(recs)

    # ---- guards -------------------------------------------------------
    assert len(recs) == n_in, f'{year}: record count moved {n_in} -> {len(recs)}'
    lo = min(p['stamina'] for p in healthy); hi = max(p['stamina'] for p in healthy)
    for old, new in zip(before_all, recs):
        if old['stamina'] != FILL:
            assert old == new, (f'{year}: a healthy record changed -- '
                                f'{new["forename"]} {new["surname"]}')
        else:
            assert lo <= new['stamina'] <= hi, \
                f'{year}: {new["forename"]} {new["surname"]} stamina {new["stamina"]} outside {lo}-{hi}'
            assert new['stamina'] != FILL, f'{year}: a record is still at the fill value'
            for f_ in new:
                if f_ != 'stamina':
                    assert old[f_] == new[f_], f'{year}: {f_} changed on a filled record'
    assert [p['appearance'] for p in before_all] == [p['appearance'] for p in recs], \
        f'{year}: appearance changed -- _verified_keys at risk'
    rate = matched / len(ones)
    other = sorted(v for v in suspect if v != FILL)
    print(f'  {year}: {len(ones):4} fixed  ({matched} from PSTA = {100*rate:.0f}% match rate, '
          f'{drawn} conditional draw)'
          + (f'   [pool excludes other fill blocks at {other}]' if other else ''))
    if not dry:
        json.dump(recs, open(path, 'w', encoding='utf-8'), **kw)
    return len(ones), matched, drawn


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    tot = collections.Counter()
    for y in FILES:
        a, m, d = fix(y, dry)
        tot['fixed'] += a; tot['matched'] += m; tot['drawn'] += d
    print(f'  TOTAL {tot["fixed"]} records: {tot["matched"]} from source '
          f'({100*tot["matched"]/max(1,tot["fixed"]):.0f}%), {tot["drawn"]} drawn')
