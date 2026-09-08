"""Gate for build/pfa-coaches.json. Every check is a property over the whole
build, proved against the SOURCE PAGES by an independent reading -- not through
the parser that wrote the build.

  G1  round-trip: per page, the multiset of `Position` cells read by a minimal
      regex over the raw HTML equals the multiset of position_as_printed stored
      for that page (claims for resolved men, coaching_seasons for leads).
      Equal multisets mean no string was altered AND no compound was split.
  G2  the three separators survive: a stored string containing each of '/', ';'
      and '-' exists and is byte-equal to its page cell (G1 proves the equality;
      G2 proves the examples are present, one of each).
  G3  no claim attaches to an unresolved man; every subject is a person the
      index holds; no lead code has a claim.
  G4  officials sharing a coach code: 22 codes, one record each, no record under
      /officials/.
  G5  a lead carries every field a matched man's page carries.
  G6  a route conflict resolves nobody.
  G7  no disagreement is resolved; every role_string_differs carries the flag.
  G8  the role vocabulary in the build is exactly the multiset of REGULAR SEASON
      cells over all pages.
"""
import os, re, sys, json, collections, html as H
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
CACHE = os.environ.get("PGM3_SOURCES", os.path.join(HERE, "..", "..", "..", "pgm3-sources")) + "/pfa2"
TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def fail(msg):
    print("GATE FAILED:", msg); sys.exit(1)


def cell_text(x):
    return re.sub(r"\s+", " ", H.unescape(re.sub("<[^>]+>", " ", x))).strip()


def positions_on_page(code):
    """Independent reading: every row whose first cell's short rendering starts
    with a year is a season row; its fourth cell is the Position. Section is the
    nearest preceding colspan header."""
    t = open(os.path.join(CACHE, f"coaches_{code}.html"), encoding="utf-8", errors="ignore").read()
    out = collections.Counter(); regular = collections.Counter(); section = None
    for r in TR.findall(t):
        if "colspan" in r and "<th" in r:
            section = cell_text(r); continue
        tds = TD.findall(r)
        if len(tds) < 4: continue
        m = re.search(r'd-md-none">(?:<a[^>]*>)?\s*(\d{4}) ', tds[0])
        if not m: continue
        pos = cell_text(tds[3])
        if not cell_text(tds[0]).replace(" ", ""): continue
        out[(section, pos)] += 1
        if section == "REGULAR SEASON": regular[pos] += 1
    return out, regular


def main():
    B = json.load(open(os.path.join(BASE, "build", "pfa-coaches.json")))
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    stored = collections.defaultdict(collections.Counter); vocab = collections.Counter()
    people = B["people"]; lead_codes = {l["pfa_code"] for l in B["leads"]}
    for c in B["claims"]:
        code = c["source_record"].split("#coaches/")[1][:-5]
        if c["predicate"] in ("pfa.coaching_season", "pfa.coaching_playoffs"):
            sec = "REGULAR SEASON" if c["predicate"] == "pfa.coaching_season" else "PLAYOFFS"
            stored[code][(sec, c["value"]["position_as_printed"])] += 1
            if sec == "REGULAR SEASON": vocab[c["value"]["position_as_printed"]] += 1
            if not c.get("_position_as_printed_is_verbatim_and_unsplit"): fail(f"claim without the verbatim flag: {code}")
        # G3
        if code not in people: fail(f"claim on an unresolved code {code}")
        if c["subject"][1] != people[code]["person"]: fail(f"claim subject differs from the resolution for {code}")
        if c["subject"][1] not in IDX: fail(f"claim subject {c['subject'][1]} is not a person the index holds")
        if code in lead_codes: fail(f"lead code {code} has a claim")
    for l in B["leads"]:
        for s in l["coaching_seasons"]:
            stored[l["pfa_code"]][(s["section"], s["position_as_printed"])] += 1
            if s["section"] == "REGULAR SEASON": vocab[s["position_as_printed"]] += 1
    # G1 + G8, page by page
    codes = sorted(set(people) | lead_codes); pages_checked = 0; regular_all = collections.Counter()
    for code in codes:
        page, regular = positions_on_page(code); regular_all.update(regular)
        if page != stored[code]:
            fail(f"G1 round-trip broke on {code}: page {dict(page)} vs stored {dict(stored[code])}")
        pages_checked += 1
    if regular_all != vocab: fail("G8 vocabulary multiset differs from the pages")
    if collections.Counter(B["role_vocabulary"]["counts"]) != vocab: fail("G8 build vocabulary block differs from the claims and leads")
    # G2
    seps = {}
    for s in vocab:
        for ch in "/;-":
            if ch in s and ch not in seps: seps[ch] = s
    for ch in "/;-":
        if ch not in seps: fail(f"G2 no stored role carries separator {ch!r}")
    for ex in ("Quarterbacks; Offensive Coordinator", "Secondary/Cornerbacks", "Defensive Backs-Nickels",
               "Assistant Offensive Coordinator/Offensive Line/Running Backs", "Assistant Offensive Line/Offensive Line"):
        if ex not in vocab: fail(f"G2 the declared example {ex!r} is not stored whole")
    # G4
    off = B["officials_sharing_a_coach_code"]["codes"]
    if len(off) != 22: fail(f"G4 expected 22 shared codes, build says {len(off)}")
    for code in off:
        recs = (1 if code in people else 0) + sum(1 for l in B["leads"] if l["pfa_code"] == code)
        if recs != 1: fail(f"G4 code {code} has {recs} records")
    if any("officials/" in c["source_record"] for c in B["claims"]) or any("officials/" in l["source_record"] for l in B["leads"]):
        fail("G4 a record was made under /officials/")
    # G5
    want = {"high_school", "height", "weight", "birth_place", "death_place", "birth_date", "death_date", "draft", "military_service", "position"}
    for l in B["leads"]:
        if set(l["fields"]) != want or "college_rows" not in l or "relatives" not in l or "coaching_seasons" not in l:
            fail(f"G5 lead {l['lead_id']} lacks a field")
        if not l.get("IS_NOT_A_PERSON"): fail("G5 a lead is not marked IS_NOT_A_PERSON")
    # G6
    for l in B["leads"]:
        if l["category"] == "route_conflict" and (not l["candidate_person"] or len(set(l["candidate_person"].values())) < 2):
            fail("G6 a route conflict lead does not name two candidates")
    # G7
    for d in B["disagreements"]["coaching_stores"]:
        if d.get("resolved") is not None: fail("G7 a comparison is resolved")
        if d["comparison"] == "role_string_differs" and not d.get("_not_a_conflict_about_a_fact"): fail("G7 differs without the flag")
    for d in B["disagreements"]["birth_date_vs_statscrew"] + B["disagreements"]["coach_page_vs_player_page"]:
        if d.get("resolved") is not None: fail("G7 a disagreement is resolved")
    print(json.dumps({"pages_round_tripped": pages_checked, "claims": len(B["claims"]), "leads": len(B["leads"]),
                      "distinct_roles": len(vocab), "separator_examples": seps, "officials_shared": len(off),
                      "comparisons": len(B["disagreements"]["coaching_stores"])}, indent=1))
    print("gate_pfa_coaches: all properties hold")


if __name__ == "__main__":
    main()
