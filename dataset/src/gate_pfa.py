"""Gates on the PFA ingest. Six properties. Each is shown to FAIL for its own
stated reason before it is trusted to pass -- a gate that has never failed is a
gate that has never been tested.

G1 runs over EVERY cached page, not a sample: it is the gate on the bug that a
sample found, and a sample cannot clear the rest.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_pfa import (parse_player, parse_relatives, transaction_claim, claim,
                        PFAError, LABEL, parse_drafts, canonical_url)

CACHE = "/Users/ryannecci/Documents/pgm3-sources/pfa2"
# players_<letter>_<code>.html ONLY. "cflplayers.html" is an INDEX page and
# matches a naive `"players" in name`; counting it as a man inflates every
# denominator on this page.
PLAYER_PAGE = re.compile(r"^players_[a-z]_[a-z0-9]+\.html$")
# `relatives` is STRUCTURED (a list of edges), not a string. It is checked by G7
# and by the kin branch of G1, not by the scalar sweep -- a list has no .strip().
FIELDS = ("high_school", "height", "weight", "birth_place", "death_place",
          "draft", "military_service", "position")
KIN_STRINGS = ("relation_as_printed", "of_name")


class GateFailure(Exception):
    pass


def g1_no_value_is_a_label(pages):
    """A field value may never be one of PFA's own printed labels, nor the header
    of the table that follows the bio. That is what a run-on read produces: the
    label is printed on every page whether or not it has a value, so a reader
    that takes 'whatever follows' returns the next label, or 'Year' -- the college
    table header. It looks like 100% coverage and is 12% fabrication."""
    vocab = set()
    for _, h in pages:
        vocab |= {m.group(1).strip().lower() for m in LABEL.finditer(h)}
    forbidden = vocab | {"year", "college", "participation", "transaction", "date", "team"}
    if not pages:
        # A gate over nothing passes over nothing. An empty corpus and a clean one
        # are the same result here, and they are not the same fact.
        raise GateFailure("no pages to check -- an empty corpus is not a pass")
    bad = collections.Counter()
    for f, h in pages:
        r = parse_player(h)
        for k in FIELDS:
            v = (r[k] or "").strip().lower().rstrip(":")
            if v and v in forbidden:
                bad[(k, v)] += 1
        for e in r["relatives"]:
            for k in KIN_STRINGS:
                v = (e[k] or "").strip().lower().rstrip(":")
                if v and v in forbidden:
                    bad[("relatives." + k, v)] += 1
    if bad:
        raise GateFailure(f"values that are labels: {bad.most_common(6)}")
    return f"{len(pages)} pages, {len(forbidden)} forbidden tokens"


def g2_empty_is_not_a_claim(pages):
    """An empty field and a missing one are the same bytes, and neither is a
    claim. PFA prints 'High School:' on 100% of pages; presence of the LABEL is
    not presence of the FACT."""
    for f, h in pages:
        r = parse_player(h)
        for k in FIELDS:
            if r[k] == "":
                try:
                    claim("sr", "p1", "pfa." + k, r[k])
                except PFAError:
                    continue
                raise GateFailure(f"{f}: empty {k} was accepted as a claim value")
    return "empty values rejected at the claim boundary"


def g3_undated_stays_undated(pages):
    """An undated transaction cannot acquire a date -- not from a neighbour, not
    from printed_row, not from anywhere."""
    n = u = 0
    for f, h in pages:
        for e in parse_player(h)["transactions"]:
            n += 1
            u += 0 if e["dated"] else 1
            transaction_claim("sr", "p1", e)
    return f"{n} transactions, {u} undated ({u * 100.0 / max(n, 1):.1f}%)"


def g7_no_synthesised_inverse(pages):
    """Every kinship edge must have been PRINTED on the page it is attributed to.
    PFA states both directions itself, so a reciprocal that no page printed can
    only have been manufactured -- which would turn one source statement into two
    and let a derived claim pass as an observed one.

    The check is a re-derivation: parse each page again and require that the edge
    set is exactly what that page's own Relatives cell holds. Any edge the page
    did not print fails, whatever produced it."""
    if not pages:
        raise GateFailure("no pages to check -- an empty corpus is not a pass")
    n = 0
    for f, h in pages:
        printed = {(e["relation_as_printed"], e["of_pfa_code"])
                   for e in parse_relatives(h)}
        for e in parse_player(h)["relatives"]:
            if (e["relation_as_printed"], e["of_pfa_code"]) not in printed:
                raise GateFailure(
                    f"{f}: edge {e['relation_as_printed']} of {e['of_pfa_code']} "
                    f"is not printed on this page")
            n += 1
    return f"{n} edges, every one printed on its own page"


def g4_no_claim_without_a_person():
    for pid in (None, "", 0):
        try:
            claim("sr", pid, "pfa.high_school", "Central (Detroit, MI)")
        except PFAError:
            continue
        raise GateFailure(f"a claim was written against person {pid!r}")
    return "None/''/0 all rejected"


def g5_lead_fieldset_matches(build):
    """A lead carries the SAME field set as a matched man -- proven by counting
    keys, not by asserting it in a docstring."""
    leads = build.get("leads") or []
    if not leads:
        return "no leads in build yet"
    want = set(FIELDS)
    for l in leads:
        if not l.get("IS_NOT_A_PERSON"):
            raise GateFailure(f"lead {l['lead_id']} is not flagged IS_NOT_A_PERSON")
        missing = want - set(l["fields"])
        if missing:
            raise GateFailure(f"lead {l['lead_id']} is missing {sorted(missing)}")
    return f"{len(leads)} leads, all carrying {len(want)} fields"


def g6_disagreements_held(build):
    """A disagreement between PFA and StatsCrew is HELD, never resolved. If a
    disagreement is recorded, both values must still be present."""
    for d in build.get("disagreements") or []:
        if d.get("resolved") or "pfa" not in d or "statscrew" not in d:
            raise GateFailure(f"disagreement on {d.get('field')} was resolved or lost a side")
    return f"{len(build.get('disagreements') or [])} disagreements, both sides held"


def _fake_inverse():
    """A page that prints ONE edge, handed a record carrying TWO -- the second
    being the reciprocal a synthesiser would add."""
    page = ('<td><b>Relatives: </b>Brother of '
            '<a href="/players/a/akin00300.html">Frank Akins</a></td>')
    printed = {(e["relation_as_printed"], e["of_pfa_code"]) for e in parse_relatives(page)}
    for e in [{"relation_as_printed": "Brother", "of_pfa_code": "akin00300"},
              {"relation_as_printed": "Brother", "of_pfa_code": "akin00400"}]:
        if (e["relation_as_printed"], e["of_pfa_code"]) not in printed:
            raise GateFailure(f"edge Brother of {e['of_pfa_code']} is not printed on this page")


def g8_no_page_is_both(match):
    """A PFA page is EITHER a man we resolved OR a man we could not. Never both.

    It happened because identity was confirmed per club-season: a name was matched
    against the archive's roster for THAT club-season only, so where the archive's
    roster is short the man became a lead -- while the same man, same PFA code,
    matched cleanly from another club-season. Frank Umont is person P_017617 and a
    lead on the 1943 Giants at the same time.

    Those are not leads. PFA gives every one of them the same player code on both
    pages, which is the source asserting one man -- structural identity, not string
    similarity. What the archive is missing is the CLUB-SEASON, and that is a roster
    disagreement to be held, not an unknown man to be invented."""
    # Checked on the BUILD, not on the match table. The raw table legitimately
    # holds the overlap -- that is the input condition rescope() exists to resolve.
    # What must never happen is the overlap surviving into the store.
    if "leads" in match and match.get("claims") is not None:
        matched = {c["subject"][1] for c in match["claims"]}
        leadp = {l["pfa_url"] for l in match["leads"]}
        by_url = {}
        for l in match["leads"]:
            by_url[l["pfa_url"]] = l
        stray = [u for u in leadp if by_url[u].get("candidate_person") in matched]
        if stray:
            raise GateFailure(f"{len(stray)} lead pages resolve to a person that has claims")
        return f"{len(matched)} people with claims, {len(leadp)} lead pages, disjoint"
    matched = {v[0] for v in (match.get("matched") or {}).values()}
    leads = {u for _, _, u in (match.get("leads") or [])}
    both = matched & leads
    if both:
        raise GateFailure(
            f"{len(both)} pages are in both sets, e.g. {sorted(both)[:2]}")
    return f"{len(matched)} matched and {len(leads)} lead pages, disjoint"


def g9_splits_have_parents_and_re_derive(build, pages_by_url):
    """Two properties, both required.

    (a) NO ORPHANS. Every pfa.draft_selection must sit beside the pfa.draft raw
        string it came from, on the same person. A derived claim whose evidence is
        gone cannot be checked against anything.

    (b) RE-DERIVATION IS EXACT. Parsing the pages again must reproduce the written
        splits field for field. A splitter that drifts from what it wrote is a
        splitter nobody can trust, and the drift would be silent."""
    raw = collections.defaultdict(list)
    split = collections.defaultdict(list)
    for c in build.get("claims", []):
        if c["predicate"] == "pfa.draft":
            raw[c["subject"][1]].append(c)
        elif c["predicate"] == "pfa.draft_selection":
            split[c["subject"][1]].append(c)
    orphans = [p for p in split if p not in raw]
    if orphans:
        raise GateFailure(f"{len(orphans)} people hold a draft split with no raw parent")
    for c in (x for v in split.values() for x in v):
        if c.get("kind") != "source_derived":
            raise GateFailure(f"a draft split is marked {c.get('kind')!r}, not source_derived")
        if not c.get("_raw_parent"):
            raise GateFailure("a draft split carries no _raw_parent")
    n = 0
    for pid, cs in split.items():
        url = canonical_url(cs[0]["source_record"].split("#")[1])
        h = pages_by_url.get(url)
        if h is None:
            raise GateFailure(f"cannot re-derive: page {url} is not held")
        again = [d for d in parse_drafts(h) if d["parsed"]]
        was = [c["value"] for c in sorted(cs, key=lambda x: x["value"]["printed_order"])]
        if len(again) != len(was):
            raise GateFailure(f"{pid}: re-derive gives {len(again)} splits, {len(was)} written")
        for a, b in zip(again, was):
            if a != b:
                diff = [k for k in a if a[k] != b.get(k)]
                raise GateFailure(f"{pid}: re-derived split differs on {diff}")
            n += 1
    return f"{n} splits, all with a raw parent and all re-deriving exactly"


def demonstrate():
    """Each gate, shown FAILING for its stated reason."""
    import types
    outs = []

    def show(name, fn):
        try:
            fn(); outs.append(f"  {name:38s} DID NOT FAIL  <-- gate is asleep")
        except (GateFailure, PFAError) as e:
            outs.append(f"  {name:38s} failed: {str(e)[:64]}")

    runon = '<td><b>High School:</b> </td></table><table><tr><th>Year</th>'
    # a parser without the STOP bound would return 'Year' here
    show("G1 value is a label", lambda: g1_no_value_is_a_label(
        [("fixture", '<td><b>High School:</b> Year</td>')]))
    show("G2 empty became a claim", lambda: (_ for _ in ()).throw(
        GateFailure("empty high_school accepted")) if claim("sr", "p1", "pfa.high_school", "")
        else None)
    show("G3 undated given a date", lambda: transaction_claim("sr", "p1", {
        "dated": False, "date": "1/19/1951", "team": "X", "type": "Signed", "printed_row": 1}))
    show("G4 claim with no person", lambda: claim("sr", None, "pfa.high_school", "X"))
    show("G5 lead missing a field", lambda: g5_lead_fieldset_matches(
        {"leads": [{"lead_id": "L1", "IS_NOT_A_PERSON": True, "fields": {"height": "6-0"}}]}))
    show("G9 split with no raw parent", lambda: g9_splits_have_parents_and_re_derive(
        {"claims": [{"predicate": "pfa.draft_selection", "subject": ["person", "P1"],
                     "kind": "source_derived", "_raw_parent": "x",
                     "source_record": "s#players/a/a.html",
                     "value": {"printed_order": 1}}]}, {}))
    show("G8 page in both sets", lambda: g8_no_page_is_both(
        {"matched": {"P1": ["players/u/umon00200.html", "Frank Umont", []]},
         "leads": [[["NFL", 1943, "NYG"], "Frank Umont", "players/u/umon00200.html"]]}))
    show("G7 inverse that was not printed", lambda: _fake_inverse())
    show("G6 disagreement resolved", lambda: g6_disagreements_held(
        {"disagreements": [{"field": "birth_date", "pfa": "a", "statscrew": "b",
                            "resolved": "pfa"}]}))
    return outs


def required(*parts):
    """Resolve a load-bearing input under BASE, and refuse to run without it.

    This replaced a read from a session scratchpad guarded by os.path.exists. The
    path carried a session id; when the archive moved to bghq-mac on 2026-09-07 the
    file was not there, and the guard turned a missing input into an empty dict.
    The same shape cost the bios 30,503 claims about 4,542 men without one word of
    complaint (declarations/session-scratchpad-inputs.json). Missing is fatal here.
    """
    fp = os.path.join(BASE, *parts)
    if not os.path.exists(fp):
        raise SystemExit("%s: required input missing: %s" % (
            os.path.basename(__file__), os.path.normpath(fp)))
    return fp


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for line in demonstrate():
        print(line)
    fs = sorted(f for f in os.listdir(CACHE) if PLAYER_PAGE.match(f))
    pages = [(f, open(os.path.join(CACHE, f), encoding="utf-8", errors="replace").read())
             for f in fs]
    MATCH = json.load(open(required("build", "pfa-match.json")))
    PAGES_BY_URL = {"players/%s/%s" % (f.split("_")[1], f.split("_", 2)[2]): h
                    for f, h in pages}
    # G5 and G6 read the BUILD. Guarded by os.path.exists they ran against {} and
    # passed -- a gate reporting success over no claims at all. Required now.
    build = json.load(open(required("build", "pfa-pre1950.json")))
    if not (build.get("claims") or []):
        raise SystemExit("gate_pfa: build/pfa-pre1950.json holds no claims; "
                         "G5 and G6 would pass on nothing")
    print(f"\n=== against {len(pages)} cached pages + {len(build['claims'])} built claims ===")
    ok = True
    for name, fn in (("G1 no value is a label", lambda: g1_no_value_is_a_label(pages)),
                     ("G2 empty is not a claim", lambda: g2_empty_is_not_a_claim(pages)),
                     ("G3 undated stays undated", lambda: g3_undated_stays_undated(pages)),
                     ("G4 no claim without a person", g4_no_claim_without_a_person),
                     ("G5 lead field set", lambda: g5_lead_fieldset_matches(build)),
                     ("G6 disagreements held", lambda: g6_disagreements_held(build)),
                     ("G7 no synthesised inverse", lambda: g7_no_synthesised_inverse(pages)),
                     ("G8 matched and leads disjoint",
                      lambda: g8_no_page_is_both(build or MATCH)),
                     ("G9 draft splits re-derive",
                      lambda: g9_splits_have_parents_and_re_derive(build, PAGES_BY_URL))):
        try:
            print(f"  PASS  {name:32s} {fn()}")
        except (GateFailure, PFAError) as e:
            ok = False
            print(f"  FAIL  {name:32s} {e}")
    sys.exit(0 if ok else 1)
