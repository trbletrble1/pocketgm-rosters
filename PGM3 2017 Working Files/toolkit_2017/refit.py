"""Madden 18 -> PGM3 attributes, then refit so weights.json reproduces the target rating.

PGM3 recomputes a player's displayed overall from his position-weighted attributes.
If `rating` is set from Madden but the attributes don't support it, the number is
wrong the moment the game reads the file. This module maps Madden 18's columns onto
the PGM3 attribute vocabulary, then nudges the attributes along the weight vector
until the formula reproduces the intended rating.
"""
import json
import numpy as np

W = json.load(open('/home/claude/toolkit/weights.json'))

# Madden 18 column -> PGM3 field. Direct one-to-one mappings only.
M18 = {
    'speed': 'Speed', 'burst': 'Acceleration', 'power': 'Strength', 'agility': 'Agility',
    'jumping': 'Jumping', 'stamina': 'Stamina', 'intelligence': 'Awareness',
    'vision': 'Ball Carrier Vision', 'ballSecurity': 'Carrying',
    'sPassAcc': 'Throw Accuracy Short', 'mPassAcc': 'Throw Accuracy Mid',
    'dPassAcc': 'Throw Accuracy Deep', 'throwOnRun': 'Throw on the Run',
    'kickAccuracy': 'Kick Accuracy', 'rushBlock': 'Run Block', 'passBlock': 'Pass Block',
    'tackle': 'Tackle', 'trucking': 'Trucking', 'elusiveness': 'Elusiveness',
    'blockShedding': 'Block Shedding', 'manCover': 'Man Coverage',
    'zoneCover': 'Zone Coverage', 'routeRun': 'Route Running', 'releaseLine': 'Release',
    'catching': 'Catching',
}


def clamp(v, lo=1, hi=99):
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return None


def derive(field, m):
    """Fields with no single Madden 18 column."""
    if field == 'injuryProne':                      # PGM3 is inverted vs Madden
        iv = clamp(m.get('Injury'))
        return 100 - iv if iv else None
    if field == 'skillMove':
        vals = [clamp(m.get('Spin Move')), clamp(m.get('Juke Move'))]
        vals = [v for v in vals if v]
        return int(sum(vals) / len(vals)) if vals else None
    if field == 'ballStrip':
        return clamp(m.get('Hit Power'))
    if field == 'decisions':
        vals = [clamp(m.get('Awareness')), clamp(m.get('Play Recognition'))]
        vals = [v for v in vals if v]
        return int(sum(vals) / len(vals)) if vals else None
    if field == 'discipline':
        # no Madden analogue; Toughness is the nearest temperament proxy
        return clamp(m.get('Toughness'))
    return None


def attributes(pos, m, posmed):
    """Build the PGM3 attribute dict for one player at one position."""
    fields = W[pos][0]
    out = {}
    for f in fields:
        v = clamp(m.get(M18[f])) if f in M18 else None
        if v is None:
            v = derive(f, m)
        if v is None:
            v = posmed.get(pos, {}).get(f, 60)
        out[f] = v
    return out


def refit(pos, attrs, target, max_iter=12):
    """Move attributes along the weight vector until w.x + b == target.

    Least-norm correction: the smallest change in attribute space that lands the
    rating, so a player's profile shape is preserved. Iterates because clamping to
    1-99 can absorb part of a step.
    """
    fields, coef = W[pos][0], W[pos][1]
    w = np.array(coef[:-1], dtype=float)
    b = coef[-1]
    x = np.array([attrs[f] for f in fields], dtype=float)
    ww = float(w @ w)
    for _ in range(max_iter):
        delta = target - (float(w @ x) + b)
        if abs(delta) < 0.5:
            break
        free = (((x > 1) | (w * delta > 0)) & ((x < 99) | (w * delta < 0)))
        wf = w * free
        denom = float(wf @ wf)
        if denom < 1e-9:
            break
        x = np.clip(x + delta * wf / denom, 1, 99)
    x = np.round(x)
    achieved = float(w @ x) + b
    return {f: int(v) for f, v in zip(fields, x)}, achieved


def predict(pos, attrs):
    fields, coef = W[pos][0], W[pos][1]
    w = np.array(coef[:-1], dtype=float)
    return float(w @ np.array([attrs[f] for f in fields], dtype=float)) + coef[-1]
