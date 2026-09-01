"""Apply build_2000.scale_to_engine to a shipped roster file, in place.

PGM3's cap is a fixed ~$280M engine constant. Era-accurate dollars leave the
financial layer inert. See scale_to_engine() for the full reasoning.
Idempotence guard: refuses to run on a file already at the engine scale.
"""
import json, sys, os, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_2000 as b

def main(path):
    recs = json.load(open(path, encoding='utf-8'))
    n_in = len(recs)
    med0 = statistics.median(b._topN(recs))
    if abs(med0 - b.PGM3_ENGINE_PAYROLL) < 5_000_000:
        sys.exit(f'REFUSING: {path} is already at the engine scale '
                 f'(median ${med0/1e6:.1f}M). Nothing to do.')

    # Independent record of the anchor structure. NOTE: keyed on the OTC
    # source dict, NOT on _src_tag -- emit() strips underscore-prefixed
    # internal fields, so a _src_tag check here matches zero records and can
    # never fail. That vacuous version shipped once; this is the fix.
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'wip'))
    from otc_anchors_2000 import OTC
    idx = {}
    for p in recs:
        idx.setdefault(f"{p['forename']} {p['surname']}", []).append(p)
    def anchor_ratios(rs):
        ix = {}
        for p in rs:
            ix.setdefault(f"{p['forename']} {p['surname']}", []).append(p)
        out = {}
        for name, val in OTC.items():
            for p in ix.get(name, []):
                if p['teamID'] not in ('Free Agent', 'Rookie') and val > 0:
                    out[name] = (p['salary'] + p['guarantee']) / val
        return out
    before_r = anchor_ratios(recs)
    assert len(before_r) > 50, \
        f'only {len(before_r)} OTC anchors matched -- the check is near-vacuous'

    recs = b.scale_to_engine(recs)
    assert len(recs) == n_in, f'record count moved {n_in} -> {len(recs)}'

    after_r = anchor_ratios(recs)
    assert set(after_r) == set(before_r), 'the OTC anchor set changed'
    f = statistics.median(after_r[k] / before_r[k] for k in before_r)
    worst = max(abs((after_r[k] / before_r[k]) / f - 1) for k in before_r)
    print(f'    OTC anchors    {len(after_r)} contracts, worst proportional '
          f'drift {worst:.2e}')
    assert worst < 1e-3, f'OTC anchor proportions moved by {worst:.2e}'

    json.dump(recs, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f'    wrote {path}  ({n_in} records)')

if __name__ == '__main__':
    main(sys.argv[1])
