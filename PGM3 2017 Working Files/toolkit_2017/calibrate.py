"""Put Madden 18 attribute values onto the donor's per-position PGM3 scale.

weights.json was fitted against PGMRoster2025-06-12_3, so its coefficients only
reproduce ratings when the attributes sit on that file's distributions. Mapping
Madden columns one-to-one produced a systematic -17 bias, because several PGM3
fields do not mean what the similarly named Madden column means (lineman `vision`
and `releaseLine` are the clearest cases).

Two paths per field, chosen by whether Madden carries real signal for that
position:

  SIGNAL   - Madden orders players meaningfully. Keep the ordering, replace the
             scale: a WR at the 90th percentile of Madden Speed becomes the 90th
             percentile of the donor's WR speed.
  NO SIGNAL- Madden is near-constant or near-zero for the position (lineman
             `vision`). Ordering is noise, so draw from the donor's distribution
             for THAT POSITION keyed to the player's overall rating. Per-position
             throughout: a 90-overall tackle and a 90-overall corner must not land
             on the same vision.
"""
import collections
import json

import numpy as np

W = json.load(open('/home/claude/toolkit/weights.json'))

# Madden treats a field as position-irrelevant by pinning it near the floor
# (tackle `vision` sits at 10, `releaseLine` at 15). Low spread alone is NOT the
# test: a position's defining attributes are compressed at the top in Madden
# (every starting WR is fast) yet still order players correctly.
MIN_SIGNAL_MEDIAN = 35.0
MIN_SIGNAL_RANGE = 4.0


def donor_profiles(ref):
    """{position: {field: sorted np.array of donor values}} plus rating-keyed lookup."""
    dist = collections.defaultdict(lambda: collections.defaultdict(list))
    rated = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in ref:
        pos = p['position']
        if pos not in W:
            continue
        for f in W[pos][0]:
            dist[pos][f].append(p[f])
            rated[pos][f].append((p['rating'], p[f]))
    out = {}
    for pos in dist:
        out[pos] = {f: np.sort(np.array(v, dtype=float)) for f, v in dist[pos].items()}
    keyed = {pos: {f: sorted(v) for f, v in d.items()} for pos, d in rated.items()}
    return out, keyed


def build_source_pools(prelim, attributes_fn, posmed):
    """Raw Madden-derived values per position/field, for percentile ranking."""
    pool = collections.defaultdict(lambda: collections.defaultdict(list))
    for r, m, pos, src, team in prelim:
        if m is None:
            continue
        a = attributes_fn(pos, m, posmed)
        for f, v in a.items():
            pool[pos][f].append(v)
    return {pos: {f: np.sort(np.array(v, dtype=float)) for f, v in d.items()}
            for pos, d in pool.items()}


def has_signal(pool, pos, field):
    v = pool.get(pos, {}).get(field)
    if v is None or len(v) < 8:
        return False
    if float(np.median(v)) < MIN_SIGNAL_MEDIAN:
        return False
    spread = float(np.percentile(v, 90) - np.percentile(v, 10))
    return spread >= MIN_SIGNAL_RANGE


def map_value(raw, src_sorted, dst_sorted):
    """Percentile-map one value from the Madden distribution onto the donor's."""
    pct = float(np.searchsorted(src_sorted, raw, side='left')) / max(1, len(src_sorted) - 1)
    pct = min(1.0, max(0.0, pct))
    idx = pct * (len(dst_sorted) - 1)
    lo, hi = int(np.floor(idx)), int(np.ceil(idx))
    frac = idx - lo
    return float(dst_sorted[lo] * (1 - frac) + dst_sorted[hi] * frac)


def from_rating(keyed, pos, field, rating, rng, window=6):
    """Draw a value from donor players at the SAME POSITION with a similar rating."""
    pairs = keyed.get(pos, {}).get(field)
    if not pairs:
        return None
    near = [v for r, v in pairs if abs(r - rating) <= window]
    if len(near) < 5:
        pairs_sorted = sorted(pairs, key=lambda t: abs(t[0] - rating))
        near = [v for _, v in pairs_sorted[:25]]
    return float(np.median(near) + rng.gauss(0, max(1.0, np.std(near) * 0.5)))


def calibrate(attrs, pos, rating, pool, donor_dist, keyed, rng):
    """Return attributes on the donor's scale, plus which path each field took."""
    out, path = {}, {}
    for f, raw in attrs.items():
        dst = donor_dist.get(pos, {}).get(f)
        if dst is None or len(dst) < 8:
            out[f], path[f] = raw, 'passthrough'
            continue
        if has_signal(pool, pos, f):
            out[f] = map_value(raw, pool[pos][f], dst)
            path[f] = 'percentile'
        else:
            v = from_rating(keyed, pos, f, rating, rng)
            out[f] = v if v is not None else float(np.median(dst))
            path[f] = 'rating_keyed'
        out[f] = int(max(1, min(99, round(out[f]))))
    return out, path
