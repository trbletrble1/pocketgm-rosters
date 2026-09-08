"""Gates on the 1957 hearing ingest. Five properties, each shown FAILING first."""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_hearing1957 import READ_BY_EYE, PARSED, QUALIFIED


class GateFailure(Exception):
    pass


def h1_eye_read_is_never_machine_read(b):
    """A value a person read off a degraded scan may never be indistinguishable
    from one a machine extracted. Every claim declares which it is."""
    if not b.get("claims"):
        raise GateFailure("no claims -- an empty store is not a pass")
    n = collections.Counter()
    for c in b["claims"]:
        a = c.get("acquisition_state")
        if a not in (READ_BY_EYE, PARSED):
            raise GateFailure(f"claim on {c['predicate']} declares no acquisition state")
        n[a] += 1
        if c["predicate"].startswith("hearing.player_salaries") and a != READ_BY_EYE:
            raise GateFailure("a salary-table value is not marked read-by-eye")
        if c["predicate"].startswith("hearing.contract") and a != PARSED:
            raise GateFailure("a contract clause is not marked parsed")
    return f"{n[READ_BY_EYE]} read by eye, {n[PARSED]} parsed, none ambiguous"


def h2_failing_cell_carries_its_flag(b):
    """A cell that fails the roster-size check cannot be written without saying so."""
    p = f = 0
    for c in b["claims"]:
        if c["predicate"] != "hearing.player_salaries" or c["kind"] == "absent":
            continue
        chk = c["value"]["roster_size_check"]
        if not chk["passes"] and not c.get("_check_failed"):
            raise GateFailure("a failing cell is written without its flag")
        if chk["passes"] and c.get("_check_failed"):
            raise GateFailure("a passing cell is flagged as failing")
        p += chk["passes"]; f += not chk["passes"]
    if f == 0:
        raise GateFailure("no failing cells recorded -- 20 were found by the reader")
    return f"{p} pass carrying their computed N, {f} fail carrying the flag"


def h3_qualified_reads_are_marked(b):
    """The check-selected Giants mean and the probable-misread Baltimore total may
    not look like clean reads."""
    seen = set()
    for c in b["claims"]:
        if c["predicate"] != "hearing.player_salaries" or c["kind"] == "absent":
            continue
        club, year = c["subject"][1], c["subject"][2]
        q = c["value"].get("read_qualification")
        if (year, club) in QUALIFIED:
            if not q:
                raise GateFailure(f"{year} {club} is a qualified read but carries no mark")
            seen.add((year, club))
        elif q:
            raise GateFailure(f"{year} {club} is marked qualified but should not be")
    if seen != set(QUALIFIED):
        raise GateFailure(f"expected {len(QUALIFIED)} qualified reads, marked {len(seen)}")
    return f"{len(seen)} qualified reads, each distinguishable from a clean read"


def h4_absent_is_not_zero(b):
    """Baltimore 1952 is an absence the SOURCE asserts. Not zero, not missing."""
    ab = [c for c in b["claims"] if c["kind"] == "absent"]
    if len(ab) != 1:
        raise GateFailure(f"expected 1 absent cell, found {len(ab)}")
    c = ab[0]
    if not c.get("_the_source_prints_nothing_here"):
        raise GateFailure("the absent cell does not say the source prints nothing")
    if c["value"] in (0, "0", None, ""):
        raise GateFailure("an asserted absence was written as zero or empty")
    return f"{c['subject'][1]} {c['subject'][2]}: absent, not zero, with its reason"


def h5_parenthesis_is_a_loss(b):
    """A parenthesised figure on 2751 is a NEGATIVE. The five annual figures must
    sum to the printed 5-year total, which fails if any sign is inverted."""
    for c in b["claims"]:
        if c["predicate"] != "hearing.receipts_over_disbursements":
            continue
        figs = c["value"]["figures"]
        for f in figs:
            if f["as_printed"].startswith("(") and f["amount"] >= 0:
                raise GateFailure(f"parenthesised {f['as_printed']} stored as positive")
        sc = c["value"]["self_check"]
        if not sc.get("reconciles"):
            raise GateFailure(f"annual figures do not sum to the stated total: {sc}")
        neg = sum(1 for f in figs if f["sign"] == "negative")
        return f"{len(figs)} figures, {neg} negative, annual sum reconciles to the total"
    raise GateFailure("no receipts claim found")


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:36s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:36s} failed: {str(e)[:58]}")
    show("H1 eye-read passed as machine-read", lambda: h1_eye_read_is_never_machine_read(
        {"claims": [{"predicate": "hearing.player_salaries", "acquisition_state": PARSED}]}))
    show("H2 failing cell with no flag", lambda: h2_failing_cell_carries_its_flag(
        {"claims": [{"predicate": "hearing.player_salaries", "kind": "observed",
                     "value": {"roster_size_check": {"passes": False}}}]}))
    show("H3 qualified read unmarked", lambda: h3_qualified_reads_are_marked(
        {"claims": [{"predicate": "hearing.player_salaries", "kind": "observed",
                     "subject": ["club_season", "New York Giants", 1952], "value": {}}]}))
    show("H4 absence written as zero", lambda: h4_absent_is_not_zero(
        {"claims": [{"kind": "absent", "value": 0, "subject": ["club_season", "x", 1952],
                     "_the_source_prints_nothing_here": True}]}))
    show("H5 loss stored as a gain", lambda: h5_parenthesis_is_a_loss(
        {"claims": [{"predicate": "hearing.receipts_over_disbursements",
                     "value": {"figures": [{"as_printed": "($68,689.89)", "amount": 68689.89,
                                            "sign": "positive"}],
                               "self_check": {"reconciles": True}}}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    b = json.load(open(os.path.join(BASE, "build", "hearing-1957.json")))
    print("\n=== against the 1957 hearing build ===")
    ok = True
    for nm, fn in (("H1 eye-read never machine-read", h1_eye_read_is_never_machine_read),
                   ("H2 failing cell carries flag", h2_failing_cell_carries_its_flag),
                   ("H3 qualified reads marked", h3_qualified_reads_are_marked),
                   ("H4 absent is not zero", h4_absent_is_not_zero),
                   ("H5 parenthesis is a loss", h5_parenthesis_is_a_loss)):
        try:
            print(f"  PASS  {nm:32s} {fn(b)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:32s} {e}")
    sys.exit(0 if ok else 1)
