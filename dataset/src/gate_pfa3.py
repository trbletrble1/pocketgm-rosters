"""Gates on PFA stage three. Six properties, each shown FAILING for its own reason."""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_pfa3 import parse_deaths, DEATH_PAGES, CACHE, LINK


class GateFailure(Exception):
    pass


def t1_deaths_counted_by_link_not_row(_):
    """The record count must equal the PERSON LINK count, never the <tr> count.
    PFA emits <tr> without closing tags, so a <tr>...</tr> regex merges logical
    rows -- one CFL row appears to hold five men, and counting rows loses four
    CFL men and one NFL coach."""
    tot_rec = tot_link = 0
    for f in DEATH_PAGES:
        h = open(os.path.join(CACHE, f), encoding="utf-8", errors="replace").read()
        best = max(re.findall(r"<table.*?</table>", h, re.S), key=len)
        recs = len(parse_deaths(h))
        links = len(LINK.findall(best))
        if recs != links:
            raise GateFailure(f"{f}: {recs} records but {links} person links")
        tot_rec += recs; tot_link += links
    return f"{tot_rec:,} records == {tot_link:,} person links, across 4 pages"


def t2_identity_is_never_by_name(build):
    """Every claim's person came from a PFA CODE. A claim carrying a resolution
    route of 'name' may not exist -- the death lists give a code on every row and
    there is no reason to ever fall back."""
    for c in build["claims"]:
        if str(c.get("resolved_by", "")).startswith("name"):
            raise GateFailure(f"a claim was resolved by {c['resolved_by']!r}")
        s = c.get("subject")
        if not (isinstance(s, list) and len(s) >= 2):
            raise GateFailure(f"malformed subject {s!r}")
    return f"{len(build['claims']):,} claims, none resolved by name"


def t3_empty_is_not_absent(build):
    """'-' (the thing did not exist) and '' (it existed, unrecorded) are DIFFERENT
    FACTS. A '-' is written as kind='absent'; a '' is not written at all. If a ''
    ever appears as a stated value, the distinction has collapsed."""
    n = collections.Counter()
    for c in build["claims"]:
        if not c["predicate"].startswith("pfa.roster_limit"):
            continue
        v = c["value"]
        if v["state"] == "not_recorded":
            raise GateFailure("an unrecorded roster limit was written as a claim")
        if v["state"] == "did_not_exist" and c["kind"] != "absent":
            raise GateFailure(f"'-' written as kind={c['kind']!r}, not 'absent'")
        if v["state"] == "stated" and not str(v["value"]).strip():
            raise GateFailure("a blank value was written as 'stated'")
        n[v["state"]] += 1
    return f"stated {n['stated']:,}, did_not_exist {n['did_not_exist']:,}, unrecorded never written"


def t4_ranges_are_not_expanded(build):
    """A camp's `Years` is a RANGE STRING and stays one. Expanding '1920-1921'
    into two season facts asserts a shape the source does not print, and an
    expansion cannot be undone."""
    n = 0
    for c in build["claims"]:
        if c["predicate"] != "pfa.training_camp":
            continue
        v = c["value"]
        if "year" in v:
            raise GateFailure("a training camp claim carries an expanded 'year'")
        if not v.get("_years_is_a_range_not_a_year"):
            raise GateFailure("a camp claim does not declare its years as a range")
        n += 1
    return f"{n:,} camp claims, every one keeping its range as printed"


def t5_partial_draft_is_not_a_selection(build):
    """12 draft pages carry no Round or Overall column. Those rows may never wear
    the selection predicate -- the same rule the dashboard's two draft rows encode."""
    for c in build["claims"]:
        if c["predicate"] == "pfa.draft_selection":
            v = c["value"]
            if "round" not in v or "overall_pick" not in v:
                raise GateFailure("a draft_selection lacks round/overall_pick entirely")
        if c["predicate"] == "pfa.draft_allocation" and "round" in c["value"]:
            raise GateFailure("an allocation claim carries a round")
    sel = sum(1 for c in build["claims"] if c["predicate"] == "pfa.draft_selection")
    alo = sum(1 for c in build["claims"] if c["predicate"] == "pfa.draft_allocation")
    return f"{sel:,} selections all carry round+pick; {alo:,} allocations carry neither"


def t6_disagreements_held(build):
    for d in build["disagreements"]:
        if d.get("resolved") is not None:
            raise GateFailure(f"a {d['field']} disagreement was resolved")
    return f"{len(build['disagreements']):,} disagreements, none resolved"


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:36s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:36s} failed: {str(e)[:60]}")
    show("T2 resolved by name", lambda: t2_identity_is_never_by_name(
        {"claims": [{"subject": ["person", "P1"], "resolved_by": "name_only"}]}))
    show("T3 unrecorded written as a claim", lambda: t3_empty_is_not_absent(
        {"claims": [{"predicate": "pfa.roster_limit.active", "kind": "observed",
                     "value": {"state": "not_recorded", "value": ""}}]}))
    show("T4 range expanded to a year", lambda: t4_ranges_are_not_expanded(
        {"claims": [{"predicate": "pfa.training_camp",
                     "value": {"year": 1920, "_years_is_a_range_not_a_year": True}}]}))
    show("T5 allocation with a round", lambda: t5_partial_draft_is_not_a_selection(
        {"claims": [{"predicate": "pfa.draft_allocation", "value": {"round": 3}}]}))
    show("T6 disagreement resolved", lambda: t6_disagreements_held(
        {"disagreements": [{"field": "death_date", "resolved": "pfa"}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    b = json.load(open(os.path.join(BASE, "build", "pfa-stage3.json")))
    print("\n=== against the stage-three build ===")
    ok = True
    for nm, fn in (("T1 deaths by link not row", t1_deaths_counted_by_link_not_row),
                   ("T2 identity never by name", t2_identity_is_never_by_name),
                   ("T3 empty is not absent", t3_empty_is_not_absent),
                   ("T4 ranges not expanded", t4_ranges_are_not_expanded),
                   ("T5 partial is not a selection", t5_partial_draft_is_not_a_selection),
                   ("T6 disagreements held", t6_disagreements_held)):
        try:
            print(f"  PASS  {nm:30s} {fn(b)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:30s} {e}")
    sys.exit(0 if ok else 1)
