"""Gate: the media-guide staff records join the archive on club and season, never a name.

  A1  every join in build/assistants-identity.json is in identity.json, on a person who
      already has a source-native id, with its evidence recorded beside it
  A2  every join is corroborated: the person holds a coaching season at a club-year the
      guide names him at (recomputed here, not read from the decision)
  A3  no join rests on a name alone -- a name with two namesakes, or none holding the
      club-year, is refused and counted
  A4  the joins are reversible: undo removes exactly them and restores the file
  A5  the guide's role strings survive verbatim into the index

  python3 src/gate_assistants_identity.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import apply_assistants_identity as AA, corroborate_assistants as CA
from clubs import Clubs, norm

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def main():
    D = json.load(open(AA.DP)); idm = json.load(open(AA.IDP))
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); IDX.pop("_clubs", None)
    C = Clubs()
    print("A1  every join is in identity.json beside its evidence")
    miss = [j for j in D["joins"] if [j["store"], j["local"]] not in (idm.get(j["person"], {}).get("local") or [])]
    noev = [j for j in D["joins"] if not (idm.get(j["person"], {}).get("local_evidence") or {}).get(f"{j['store']}|{j['local']}")]
    noslug = [j for j in D["joins"] if not idm.get(j["person"], {}).get("slugs")]
    check(not miss, f"{len(D['joins'])} joins, all present in identity.json" if not miss else f"{len(miss)} missing")
    check(not noev, "every join records its evidence, its club-years and its source record" if not noev else f"{len(noev)} without evidence")
    check(not noslug, "every target already had a source-native id: gate_identity's property is untouched" if not noslug else f"{len(noslug)} targets have no slug")
    print("A2  every join is corroborated on club and season, recomputed")
    def cid(t, y):
        r = C.resolve(t, y, None, source="season_key"); return r[0] if r else None
    bad = []
    for j in D["joins"]:
        p = IDX.get(j["person"]) or {}
        cy = set()
        for k in list((p.get("coaching_seasons") or {})) + [k for k in (p.get("seasons") or {}) if k.startswith("COACHES|")]:
            lg, y, c = k.split("|", 2); yy = int(y[1:5]) if y.startswith("y") else int(y); cy.add((cid(c, yy), yy))
        if not any((m["club"], m["year"]) in cy for m in j["club_years_matched"]): bad.append((j["person"], j["name_as_printed"]))
    check(not bad, f"all {len(D['joins'])} hold a coaching season at a club-year the guide names" if not bad else f"{len(bad)} do not: {bad[:3]}")
    print("A3  nothing rests on a name alone")
    E = CA.build()
    same = {(j["local"], j["person"]) for j in E["joins"]} == {(j["local"], j["person"]) for j in D["joins"]}
    check(same, f"the decision reproduces: {len(E['joins'])} joins, {E['counts']['refused']} refused")
    # THIS CHECK COULD NOT FAIL UNTIL 2026-09-07. It read
    #     check(A and B or True, ...)
    # which is `True` whatever A and B are: the one check standing between this join set and
    # an identity resting on a name alone had never been able to fire. Ryan's ruling 6.
    #
    # It is three properties now, and each can fail on its own:
    #   a  every join names EXACTLY ONE corroborated namesake -- the decider records the count
    #      it decided on (namesakes_corroborated) and the gate holds it to that, rather than
    #      carrying a second copy of the decider and drifting from it;
    #   b  every join carries the club-year evidence that corroborated it;
    #   c  every refusal reason is one of the four the decider can give, and the two name-alone
    #      reasons are PRESENT and counted -- a decider that has stopped refusing anything is
    #      not a decider that has become certain.
    multi = [j for j in E["joins"] if j.get("namesakes_corroborated") != 1]
    check(not multi, f"all {len(E['joins'])} joins rest on exactly one corroborated namesake "
                     f"({sum(1 for j in E['joins'] if j['namesakes_considered'] > 1)} of them had a namesake to be told apart from)"
          if not multi else
          f"{len(multi)} join(s) rest on {sorted({j.get('namesakes_corroborated') for j in multi})} corroborated namesakes, not one: "
          f"{[j['name_as_printed'] for j in multi][:4]}")
    noev = [j for j in E["joins"] if not j.get("club_years_matched")]
    check(not noev, "every join carries the club-year that corroborated it"
          if not noev else f"{len(noev)} join(s) carry no club-year evidence: {[j['name_as_printed'] for j in noev][:4]}")
    REASONS = {"promoted as a new person: not an existing man",
               "no person of that name in the archive",
               "more than one namesake holds a coaching season at a guide club-year",
               "namesake(s) hold no coaching season at any club-year this guide names"}
    counts = E["REFUSED"]["counts"]
    undeclared = sorted(set(counts) - REASONS)
    check(not undeclared, f"every refusal reason is one the decider declares ({len(counts)} in use)"
          if not undeclared else f"refusal reason(s) this gate does not know: {undeclared}")
    # The two name-alone refusals are checked in OPPOSITE directions, which is what the
    # original expression was reaching for before the `or True` swallowed it:
    #   the NO-coaching-season refusal must be LIVE -- a decider that has stopped refusing
    #     anything has not become certain, it has stopped looking;
    #   the MORE-THAN-ONE-namesake refusal must be EMPTY -- while it is, every join had a
    #     unique corroborated namesake by construction. The day it is not, two men of one
    #     name both hold a guide club-year and which one the guide meant is a RULING, so
    #     the gate fails and names them rather than letting the decider pick.
    NONE_HELD = "namesake(s) hold no coaching season at any club-year this guide names"
    TWO_HELD = "more than one namesake holds a coaching season at a guide club-year"
    check(counts.get(NONE_HELD, 0) > 0,
          f"the refusal that keeps a name from becoming identity is live: {counts.get(NONE_HELD, 0)} refused"
          if counts.get(NONE_HELD, 0) > 0 else
          f"NOTHING was refused for holding no coaching season at a guide club-year. counts: {json.dumps(counts)}")
    check(not counts.get(TWO_HELD),
          "no guide name has two namesakes both holding one of its club-years"
          if not counts.get(TWO_HELD) else
          f"{counts[TWO_HELD]} guide name(s) have TWO namesakes holding a club-year the guide names -- "
          f"which man the guide meant is a ruling, not a decision for the decider: "
          f"{E['REFUSED']['examples'].get(TWO_HELD, [])[:4]}")
    print("      refusals: " + json.dumps(counts))
    print("A4  reversible")
    copy = json.loads(json.dumps(idm)); n = AA.undo(copy)
    left = [j for j in D["joins"] if [j["store"], j["local"]] in (copy.get(j["person"], {}).get("local") or [])]
    base = json.loads(json.dumps(copy)); AA.apply(base, D)
    check(n == len(D["joins"]) and not left, f"undo removes exactly the {n} joins")
    check(json.dumps(base, sort_keys=True) == json.dumps(idm, sort_keys=True), "undo then apply reproduces identity.json exactly")
    print("A5  the role strings survive verbatim")
    want = collections.Counter(m["role_as_printed"] for j in D["joins"] for m in j["club_years_matched"])
    seen = 0
    for j in D["joins"]:
        p = IDX.get(j["person"]) or {}
        roles = {(s.get("stint") or {}).get("role_title") for s in (p.get("seasons") or {}).values() if isinstance(s, dict)}
        seen += sum(1 for m in j["club_years_matched"] if m["role_as_printed"] in roles)
    check(seen > 0, f"{seen} of {sum(want.values())} corroborating role strings are on the person's seasons in the index, unrewritten"
          + ("" if seen else "  (run the rebuild: the joins are in identity.json but the index has not been rebuilt since)"))
    print()
    if fails: print(f"ASSISTANTS IDENTITY GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print(f"ASSISTANTS IDENTITY GATE: pass  ({len(D['joins'])} joins, {D['counts']['guide_seasons_joined']} guide seasons)"); return 0


def selftest():
    """A3 shown FAILING for each of its own reasons. It could not fail at all until today,
    so it is not trusted until it has been seen to."""
    import copy
    E0 = CA.build()
    print("SELFTEST -- A3, each check broken in turn\n")
    ok = []

    def probe(name, mutate):
        E = copy.deepcopy(E0); mutate(E)
        fails = []
        multi = [j for j in E["joins"] if j.get("namesakes_corroborated") != 1]
        if multi: fails.append("a")
        if [j for j in E["joins"] if not j.get("club_years_matched")]: fails.append("b")
        REASONS = {"promoted as a new person: not an existing man", "no person of that name in the archive",
                   "more than one namesake holds a coaching season at a guide club-year",
                   "namesake(s) hold no coaching season at any club-year this guide names"}
        c = E["REFUSED"]["counts"]
        if set(c) - REASONS: fails.append("c-undeclared")
        if not c.get("namesake(s) hold no coaching season at any club-year this guide names"): fails.append("c-silent")
        if c.get("more than one namesake holds a coaching season at a guide club-year"): fails.append("c-ambiguous")
        good = fails == [name]
        print(f"  {'OK  ' if good else 'BAD '} {name}: fired {fails or ['nothing']}")
        return good

    def clean(E): pass
    base = []
    multi = [j for j in E0["joins"] if j.get("namesakes_corroborated") != 1]
    print(f"  baseline: {len(E0['joins'])} joins, {len(multi)} with more than one corroborated namesake\n")
    ok.append(probe("a", lambda E: E["joins"][0].__setitem__("namesakes_corroborated", 2)))
    ok.append(probe("b", lambda E: E["joins"][0].__setitem__("club_years_matched", [])))
    ok.append(probe("c-undeclared", lambda E: E["REFUSED"]["counts"].__setitem__("a reason nobody declared", 3)))
    ok.append(probe("c-silent", lambda E: E["REFUSED"]["counts"].pop(
        "namesake(s) hold no coaching season at any club-year this guide names", None)))
    ok.append(probe("c-ambiguous", lambda E: E["REFUSED"]["counts"].__setitem__(
        "more than one namesake holds a coaching season at a guide club-year", 2)))
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    sys.exit(main())
