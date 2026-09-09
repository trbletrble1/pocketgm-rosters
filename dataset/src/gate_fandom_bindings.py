"""A REDIRECT MUST NOT FOLD ONE CLUB INTO ANOTHER ON A SHARED WORD.

The 2026-09-06 fandom survey binds each of its entries to one club in the table and
then hangs that entry's variant names on it. 141 strings arrived that way. One of
them was wrong: `Rochester Tigers` -- the 1937 AFL club -- landed on
`club-brooklyn-dodgers-1930`, because the NFL Dodgers became the Brooklyn TIGERS in
1944 and the survey entry's variant list carried that name.

THE CLASS, measured 2026-09-09. Fandom disambiguates a reused name in the page
title: `Cincinnati Bengals (1937-41)`, `Chicago Bulls (AFL)`, `Brooklyn Dodgers
(NFL)`. build_clubs STRIPS that parenthesis before matching -- and the parenthesis is
often the only thing that says which club it is. So the gate checks the discarded
half against the club that was chosen:

  P1  a disambiguator naming YEARS must overlap the club's own span.
      `Cincinnati Bengals (1937-41)` on a club that lived 1968-2024 does not.
  P2  a disambiguator naming a LEAGUE must be a league the club actually held.
  P3  the loose route -- binding on a VARIANT that happens to be an archive name,
      rather than on the canonical -- is reported every run, whatever it matched.
      It is one string today and it is the one that was wrong.

WHAT THIS GATE CANNOT SEE, said rather than left to be found: a reused name with NO
disambiguator, and a league abbreviation that means two different competitions. P2
would pass `Cincinnati Bengals (AFL)` on the 1968 club, because that club really did
play in an AFL -- the 1968-69 one, not the 1937 one. Comparing tokens is what the
archive already knows not to do; here it is the best the printed title allows, and
the residue is listed under P3 and in the report.

    python3 src/gate_fandom_bindings.py [--selftest]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
TABLE = os.path.join(BASE, "build", "clubs.json")

FAILS = []
LEAGUEISH = {"NFL", "AFL", "AAFC", "APFA", "AFA", "WFL", "USFL", "XFL", "UFL", "CFL",
             "WLAF", "NFLE", "ARENA", "PCFL", "IRFU", "WIFU", "ORFU", "AAF"}


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def audit(clubs):
    """-> (findings, loose, n_checked). Pure over a club list, so the self-test can
    hand it three fixtures and main() the whole table."""
    findings = []; loose = []; n = 0
    for c in clubs:
        lgs = {L.get("league") for L in c.get("leagues", []) if L.get("league")}
        for s in c.get("strings") or []:
            if s.get("source") != "fandom_redirect" or s.get("kind") != "printed_name": continue
            n += 1
            if s.get("matched_on") == "a variant that is an archive name":
                loose.append({"club_id": c["id"], "string": s["string"],
                              "why": "bound on a VARIANT, not on the canonical name"})
            m = re.search(r"\(([^)]*)\)\s*$", s["string"])
            if not m: continue
            d = m.group(1).strip()
            yrs = [int(y) for y in re.findall(r"\d{4}", d)]
            if yrs and not any(c["first"] <= y <= c["last"] for y in yrs):
                findings.append({"what": "the disambiguator names years the club did not live",
                                 "club_id": c["id"], "string": s["string"],
                                 "club_span": [c["first"], c["last"]],
                                 "remedy": "the survey entry names a DIFFERENT club of the same name; "
                                           "withdraw the binding in declarations/clubs.json WITHDRAWN_STRINGS"})
            elif d.upper() in LEAGUEISH and d.upper() not in lgs:
                findings.append({"what": "the disambiguator names a league the club never played in",
                                 "club_id": c["id"], "string": s["string"],
                                 "club_leagues": sorted(x for x in lgs if x),
                                 "remedy": "as above"})
    return findings, loose, n


def main(argv):
    if "--selftest" in argv: return selftest()
    T = json.load(open(TABLE))
    findings, loose, n = audit(T["clubs"])
    print(f"FANDOM BINDINGS  ({n} canonical strings from the survey)")
    check(not findings, f"every disambiguator agrees with the club it was bound to: {len(findings)} do not"
          + ("" if not findings else "  " + json.dumps(findings[:2])))
    print(f"  INFORMATION: bound on a variant rather than the canonical: {len(loose)}"
          + (f"  {json.dumps(loose)}" if loose else ""))
    if FAILS:
        print(f"\nFANDOM BINDING GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nFANDOM BINDING GATE: pass"); return 0


def selftest():
    good = {"id": "club-a", "first": 1968, "last": 2024,
            "leagues": [{"league": "AFL", "first": 1968, "last": 1969}, {"league": "NFL", "first": 1970, "last": 2024}],
            "strings": [{"source": "fandom_redirect", "kind": "printed_name", "string": "Cincinnati Bengals (AFL)"}]}
    bad_year = json.loads(json.dumps(good))
    bad_year["strings"] = [{"source": "fandom_redirect", "kind": "printed_name", "string": "Cincinnati Bengals (1937-41)"}]
    bad_lg = json.loads(json.dumps(good))
    bad_lg["strings"] = [{"source": "fandom_redirect", "kind": "printed_name", "string": "Cincinnati Bengals (WFL)"}]
    loose_c = json.loads(json.dumps(good))
    loose_c["strings"] = [{"source": "fandom_redirect", "kind": "printed_name", "string": "Rochester Tigers",
                           "matched_on": "a variant that is an archive name"}]
    other = json.loads(json.dumps(good))
    other["strings"] = [{"source": "pfa_cell", "kind": "printed_name", "string": "Anything (1900)"}]
    cases = [("a disambiguator the club satisfies", [good], 0, 0),
             ("years the club did not live", [bad_year], 1, 0),
             ("a league the club never played in", [bad_lg], 1, 0),
             ("the loose route is reported, not failed", [loose_c], 0, 1),
             ("another source's string is not this gate's business", [other], 0, 0)]
    ok = True
    for label, clubs, wf, wl in cases:
        f, l, n = audit(clubs)
        good_ = len(f) == wf and len(l) == wl; ok &= good_
        print(f"  {'ok  ' if good_ else 'FAIL'} {label}: expected {wf} finding(s)/{wl} loose, got {len(f)}/{len(l)}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
