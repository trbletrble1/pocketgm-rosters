"""Assign `potential`, then build `growthType` to match it exactly.

VERIFIED MECHANIC: the positive slots of `growthType` sum to exactly
50 * (potential - rating). It is a ledger of remaining improvement, not a curve.
Borrowing a whole array from a donor (what convert.py's growth_for does) imports
that donor's potential gap and silently contradicts the potential assigned here —
the cause of the defect in the shipped 2010 file.

So: take the SHAPE from a donor matched on position and age (which slots are
positive, and the negative decline tail), then rescale the positive slots to hit
50 * gap exactly.
"""
import collections
import numpy as np

SLOTS = 31
UNITS_PER_POINT = 50


def gap_model(rostered):
    """Donor potential gaps, celled by age and rating band. Gap is mostly a
    function of age; within an age, lower-rated players have more headroom."""
    cells = collections.defaultdict(list)
    for p in rostered:
        cells[(p['age'], p['rating'] // 5)].append(p['potential'] - p['rating'])
    by_age = collections.defaultdict(list)
    for p in rostered:
        by_age[p['age']].append(p['potential'] - p['rating'])
    return cells, by_age


def sample_gap(cells, by_age, age, rating, rng):
    for da in (0, 1, -1, 2, -2):
        v = cells.get((age + da, rating // 5)) or []
        if len(v) >= 8:
            return int(rng.choice(v))
    for da in (0, 1, -1, 2, -2, 3, -3):
        v = by_age.get(age + da) or []
        if len(v) >= 8:
            return int(rng.choice(v))
    return 0


def shape_bank(rostered):
    """Donor arrays that carry positive growth, keyed by position and age, plus
    a bank of decline-only tails for players with no headroom."""
    grow = collections.defaultdict(list)
    flat = collections.defaultdict(list)
    for p in rostered:
        arr = np.array(p['growthType'], dtype=float)
        (grow if (arr > 0).any() else flat)[(p['position'], p['age'])].append(arr)
    return grow, flat


def _nearest(bank, pos, age, rng):
    for da in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5):
        v = bank.get((pos, age + da)) or []
        if v:
            return v[rng.randrange(len(v))]
    same_pos = [a for (p, _), arrs in bank.items() if p == pos for a in arrs]
    if same_pos:
        return same_pos[rng.randrange(len(same_pos))]
    allv = [a for arrs in bank.values() for a in arrs]
    return allv[rng.randrange(len(allv))] if allv else np.zeros(SLOTS)


def build_growth(pos, age, gap, grow, flat, rng):
    """Return a 31-slot array whose positive slots sum to exactly 50*gap."""
    target = UNITS_PER_POINT * int(gap)
    if target <= 0:
        arr = _nearest(flat, pos, age, rng).copy()
        arr[arr > 0] = 0                      # no headroom -> no positive slots
        return [int(round(x)) for x in arr]

    tpl = _nearest(grow, pos, age, rng).copy()
    posmask = tpl > 0
    if not posmask.any():                     # template had none; open a window
        start = max(0, min(SLOTS - 3, int(round((26 - age) + 2))))
        posmask = np.zeros(SLOTS, dtype=bool)
        posmask[start:start + 3] = True
        tpl[posmask] = 1.0

    weights = tpl[posmask]
    weights = weights / weights.sum()
    raw = weights * target
    vals = np.floor(raw).astype(int)
    short = target - int(vals.sum())           # distribute the rounding remainder
    if short > 0:
        order = np.argsort(-(raw - vals))
        for i in range(short):
            vals[order[i % len(vals)]] += 1
    elif short < 0:
        order = np.argsort(raw - vals)
        for i in range(-short):
            j = order[i % len(vals)]
            if vals[j] > 0:
                vals[j] -= 1

    out = tpl.copy()
    out[posmask] = vals
    out[~posmask] = np.minimum(out[~posmask], 0)   # keep only the decline tail
    return [int(round(x)) for x in out]


def verify(rating, potential, growth):
    """The exact check. Returns (ok, positive_sum, expected)."""
    arr = np.array(growth, dtype=float)
    got = int(arr[arr > 0].sum())
    want = UNITS_PER_POINT * (potential - rating)
    return got == want, got, want
