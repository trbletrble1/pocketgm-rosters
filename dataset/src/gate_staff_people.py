"""Gate: the person rule for men named in a role at a club (Ryan, 2026-09-13).

Held on the STORES and the decision store, so a hand-edited store fails too.

  S1  EVERY STAFF LINE IS ACCOUNTED FOR. Each club_staff_role line -- (name, year, club) --
      is on a person, through a person-scoped staff claim, or is a standing staff lead.
      None is neither: a line that silently reaches nobody is how the rule would fail to
      apply without anybody noticing.
  S2  A ROLE IS NEVER A COACHING SEASON OR A PLAYING ONE. Every person-scoped staff claim
      uses a declared predicate, on a `person` subject; none of those predicates is in
      declarations/coaching-seasons.json staff_predicates; and no staff promotion carries a
      playing season.
  S3  A SURNAME IS NOT A MAN. No staff promotion is a bare surname.
  S4  A SURNAME JOIN AGREES. Every staff claim joined on a surname names a man whose first
      forename agrees -- an initial with a name it begins.
  S5  EVERY STAFF PROMOTION IS FINDABLE AND HOLDS HIS LINE. Each has a person-scoped staff
      claim in the stores and a name claim in build/promotion-names.json.

  python3 src/gate_staff_people.py [--selftest]      exit 1 = FAIL
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from readings import person_name as pn

DECL = json.load(open(os.path.join(BASE, "declarations", "player-promotions.json")))["staff_role_evidence"]
PREDS = set(DECL["person_predicates"])
COACHING = set(json.load(open(os.path.join(BASE, "declarations", "coaching-seasons.json")))["staff_predicates"]["predicates"])
FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)


def agrees(a, b):
    a, b = pn(a).split(), pn(b).split()
    if len(a) < 2 or len(b) < 2: return False
    x, y = a[0], b[0]
    return x[0] == y[0] if (len(x) == 1 or len(y) == 1) else x == y


def line_key(name, year, code):
    return (pn(name), int(year), str(code))


def main():
    lines, on_person, leads, pclaims = set(), set(), set(), []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or not isinstance(d.get("claims"), list): continue
        for c in d["claims"]:
            p, s, v = c.get("predicate"), c.get("subject") or [], c.get("value")
            if p == "club_staff_role" and isinstance(v, dict):
                lines.add(line_key(v["name_as_printed"], s[2], s[3]))
            elif p in PREDS or (isinstance(p, str) and p.endswith("staff_role_as_printed")):
                pclaims.append((os.path.basename(f)[:-5], c))
                if isinstance(v, dict) and v.get("club_code"):
                    on_person.add(line_key(v["name_as_printed"], v["year"], v["club_code"]))
        for L in d.get("leads") or []:
            if isinstance(L, dict) and L.get("category") == DECL["lead_category"]:
                cs = str((L.get("places_on") or {}).get("club_season") or "").split("|")
                if len(cs) == 3: leads.add(line_key(L["name_as_printed"], cs[1], cs[2]))
    print(f"staff lines {len(lines)}   on a person {len(lines & on_person)}   standing leads {len(lines & leads)}")
    if not lines:
        print("REFUSED: no club_staff_role line in any store. An empty denominator is not a pass."); return 2
    loose = sorted(lines - on_person - leads)
    check(not loose, f"S1 every staff line is on a person or a standing staff lead ({len(loose)} are neither: {loose[:4]})")

    prom = json.load(open(os.path.join(BASE, "build", "player-promotions.json")))["promotions"]
    staffp = [p for p in prom if p.get("staff_seasons")]
    bad2 = ([f"{st}: {c['predicate']} on {c['subject'][:1]}" for st, c in pclaims
             if c["predicate"] not in PREDS or c["subject"][0] != "person"]
            + [f"{x} is a coaching predicate" for x in PREDS & COACHING]
            + [f"{p['person_id']} carries playing seasons" for p in staffp if p.get("playing_seasons")])
    check(not bad2, f"S2 no role is a coaching or playing season ({len(pclaims)} person claims, {len(staffp)} staff "
                    f"promotions; {len(bad2)} bad: {bad2[:3]})")

    bare = [p["name"] for p in staffp if len(pn(p["name"]).split()) < 2]
    check(not bare, f"S3 no staff promotion is a bare surname ({len(bare)}: {bare[:4]})")

    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    sjoin = [(c["value"]["name_as_printed"], (idx.get(c["subject"][1]) or {}).get("name"))
             for _, c in pclaims if "surname" in str(c.get("_joined_on", ""))]
    bad4 = [x for x in sjoin if not agrees(x[0], x[1] or "")]
    check(not bad4, f"S4 every surname-joined staff claim agrees on the forename ({len(sjoin)} joins; {len(bad4)} do not: {bad4[:3]})")

    names = json.load(open(os.path.join(BASE, "build", "promotion-names.json")))["claims"]
    named = {c["subject"][1] for c in names}
    holding = {c["subject"][1] for _, c in pclaims}
    bad5 = [p["person_id"] for p in staffp if p["person_id"] not in named or p["person_id"] not in holding]
    check(not bad5, f"S5 every staff promotion holds his staff claim and a name claim ({len(bad5)} do not: {bad5[:4]})")

    print("\nSTAFF PEOPLE GATE:", "pass" if not FAILS else f"{len(FAILS)} FAILURE(S)")
    return 1 if FAILS else 0


def selftest():
    ok = True
    for label, a, b, want in (("an initial agrees with a name it begins", "C.E. Swope", "Clarence E. Swope", True),
                              ("the same forename agrees", "Jesse R. Purnell", "Jesse Purnell", True),
                              ("a different forename contradicts", "Herman Smith", "Russ Smith", False),
                              ("a bare surname agrees with nothing", "Storck", "Carl Storck", False)):
        g = agrees(a, b) == want; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} S4 {label}: {a!r} / {b!r} -> {agrees(a, b)}")
    print("SELFTEST", "OK" if ok else "FAILED"); return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
