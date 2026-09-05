"""Gate: a money figure must state the unit it is a rate of, and units may not mix.

Nagurski's collection reads, in order: $5,000 (1930), $225.00 (1932), $225.00
(1933), $5,000 (1937), $3,500 (1943). Plotted naively that is a career that
collapsed by 96% and recovered. It is nothing of the kind: 1930 is a SEASON
salary and 1932-33 are PER GAME. The figures are not comparable and never were.

So `rate_unit` is required on every figure, and any operation that puts two
figures on the same axis must refuse when their units differ.

`rate_unit` is deliberately NOT called `basis`: model.py already uses `basis`
for the resolution basis (observed / absent / contested). Two meanings on one
key is the league-name collision again.

And per_game does not annualise for free. The 1933 instrument says practice
games before Sept. 23 are played WITHOUT COMPENSATION, so rate x appearances
overstates the season by every exhibition game. A per_game figure may only be
multiplied by a count of REGULARLY SCHEDULED LEAGUE games, and only when such a
count is actually held.

  python3 src/gate_salary_rate_unit.py      exit 1 = FAIL
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
DECL = os.path.join(HERE, "..", "declarations", "salary_conventions.json")

UNITS = {"season", "per_game", "unverified_total"}
MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d\d)?")


class UnitError(Exception):
    pass


def unit_of(entry):
    """The declared unit of a figure entry, or a refusal."""
    u = entry.get("rate_unit")
    if u is None:
        raise UnitError("figure %r states no rate_unit" % entry.get("figure"))
    if u not in UNITS:
        raise UnitError("rate_unit %r is not one of %s" % (u, sorted(UNITS)))
    return u


def same_axis(a, b):
    """Refuse to place two figures on one axis unless their units agree."""
    ua, ub = unit_of(a), unit_of(b)
    if ua != ub:
        raise UnitError("cannot compare %s (%s) with %s (%s): different units"
                        % (a.get("figure"), ua, b.get("figure"), ub))
    return ua


def annualise(entry, league_games=None):
    """A per_game figure becomes a season figure only against a count of
    REGULARLY SCHEDULED LEAGUE games that is actually held."""
    u = unit_of(entry)
    if u == "season":
        return entry["figure"]
    if u == "unverified_total":
        raise UnitError("%r is an unverified total; its unit is not established"
                        % entry.get("figure"))
    if league_games is None:
        raise UnitError("%r is per_game and no count of regularly scheduled "
                        "League games is held; practice games are uncompensated "
                        "under the 1933 clause, so appearances will not do"
                        % entry.get("figure"))
    return None  # deliberately not computed here; the caller states the arithmetic


def series_entries(d):
    out = []
    for key, block in (d.get("contract_images") or {}).items():
        if isinstance(block, dict):
            # both shapes: `points` (a series) and `entries` (a club batch).
            # Reading only `points` let the 1952/1955/1957 Browns figures in
            # unchecked -- a declaration the gate could not see is not declared.
            for field in ("points", "entries"):
                for pt in block.get(field) or []:
                    if isinstance(pt, dict) and "figure" in pt:
                        out.append(("%s.%s" % (key, field), pt))
    return out


def main():
    d = json.load(open(DECL, encoding="utf-8"))
    entries = series_entries(d)
    print("figure entries found in declared series: %d" % len(entries))
    fails = []
    for key, pt in entries:
        try:
            unit_of(pt)
        except UnitError as e:
            fails.append("%s: %s" % (key, e))

    # --- the gate must be shown to refuse, for its stated reasons -----------
    checks = []
    per_game = {"figure": "$225.00", "rate_unit": "per_game"}
    season = {"figure": "$5,000", "rate_unit": "season"}
    try:
        same_axis(per_game, season); checks.append("[FAIL] mixed units compared")
    except UnitError as e:
        assert "different units" in str(e), e
        checks.append("refuses mixing per_game with season: %s" % e)
    try:
        annualise(per_game); checks.append("[FAIL] per_game annualised with no game count")
    except UnitError as e:
        assert "regularly scheduled" in str(e), e
        checks.append("refuses annualising per_game without a League-game count")
    try:
        unit_of({"figure": "$3,500"}); checks.append("[FAIL] unitless figure accepted")
    except UnitError as e:
        assert "no rate_unit" in str(e), e
        checks.append("refuses a figure that states no rate_unit")
    try:
        unit_of({"figure": "$1", "rate_unit": "per_quarter"})
        checks.append("[FAIL] undeclared unit accepted")
    except UnitError as e:
        assert "not one of" in str(e), e
        checks.append("refuses a rate_unit outside the declared vocabulary")

    for c in checks:
        print("  " + c)
    bad = [c for c in checks if c.startswith("[FAIL]")]
    for f in fails:
        print("  [FAIL] " + f)
    if bad or fails:
        print("\nGATE FAILED: %d refusals did not fire, %d figures state no unit."
              % (len(bad), len(fails)))
        return 1
    print("\nGATE PASSED: every declared figure states its unit, and the four "
          "refusals fire for their stated reasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
