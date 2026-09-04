#!/usr/bin/env python3
"""
pgm3_guards — assertions that make a known defect impossible to ship silently.

STANDING RULE (Ryan, 2026-09-03): every defect fixed gets a check that catches
it, in the same commit as the fix, testing the PROPERTY and not the instance,
running on every file. This module holds the guards that belong inside the
TRANSFORM tools; the ones that belong on the OUTPUT live in pgm3_validate.py.

Import from a tool:

    from pgm3_guards import quantile_of_rank

Nothing here is stateful and nothing here writes.
"""

MIN_CELL = 5


class SmallCell(Exception):
    """A rank was about to be mapped to a quantile inside a cell too small to
    carry one."""


def quantile_of_rank(i, n, *, min_cell=MIN_CELL, label=''):
    """Plotting position (i + 0.5) / n for rank i of n, refusing small cells.

    THE DEFECT THIS EXISTS FOR (item 45, source 1, 2026-09-03). build_2026's
    assign_money mapped rank to quantile as q = i / max(1, n - 1). A cell of ONE
    gives q = 0 -- the bottom of the reference distribution -- so the only left
    tackle on a 1-year deal became the lowest-paid left tackle in the file and
    earned $0.12M while his Madden contract carried $37.1M. A cell of two sends
    one man to the floor and one to the ceiling. The shape of the whole file
    looks right throughout, which is why it survived every distribution check
    and was found by a person reading one man's salary.

    The property, not the instance: a cell with no rank to preserve is not
    mapped to a quantile. Not "no player earns less than $500K".

    (i + 0.5) / n rather than i / (n - 1) for the same reason build_1979_ratings
    and build_1979_unrated use it: the naive form sends the top man of any cell
    to the pool MAXIMUM and the bottom man to the pool MINIMUM, which is a
    claim about him that the ranking does not contain.

    Callers that have genuinely handled small cells another way pass
    min_cell=1 -- deliberately, in code, where a reader can see it.
    """
    if n <= 0:
        raise SmallCell(f'{label or "cell"}: empty cell has no rank to map')
    if n < min_cell:
        raise SmallCell(
            f'{label or "cell"}: {n} member(s), below the minimum of {min_cell} '
            f'-- a cell this small has no rank to preserve, so mapping it to a '
            f'quantile invents one. Give it a reference median instead (see '
            f'tools/fix_2026_small_cells.py), or pass min_cell=1 if the caller '
            f'has already handled it.')
    return (i + 0.5) / n


def check_cells(cells, *, min_cell=MIN_CELL, label='cells'):
    """Report small cells without raising: [(key, n), ...] for a dry run."""
    return sorted(((k, len(v)) for k, v in cells.items() if len(v) < min_cell),
                  key=lambda kv: kv[1])
