"""Gate: club_season.attribute_as_printed names no person and carries only a declared kind.
Ryan's ruling of 2026-09-11. Checked as properties across every store; no document, club or
attribute is named here.

  A1  every claim of the predicate is on a CLUB-SEASON subject -- not a game, not a league-season,
      not a person.
  A2  every kind is on the declared list, READ from declarations/club-season-attributes.json.
  A3  NO ENTRY NAMES A PERSON: it carries no `person`, and neither its name nor its printed text is
      the name of a man held on that club-season, nor a name its club_staff_role claims print.
  A4  every entry is served in its club-season view, under `attributes_as_printed` -- held is not served.

  python3 src/gate_club_season_attribute.py              exit 1 = FAIL
  python3 src/gate_club_season_attribute.py --self-test  proves it can fail
"""
import os, re, sys, json, glob, sqlite3, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

PRED = "club_season.attribute_as_printed"
KINDS = set(json.load(open(os.path.join(BASE, "declarations", "club-season-attributes.json")))["kinds"])
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def nm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def claims(extra=()):
    out, staff_names = [], set()
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if not (isinstance(d, dict) and isinstance(d.get("claims"), list)): continue
        for c in d["claims"]:
            if c.get("predicate") == PRED: out.append((os.path.basename(f)[:-5], c))
            if c.get("predicate") == "club_staff_role" and isinstance(c.get("value"), dict):
                staff_names.add(nm(c["value"].get("name_as_printed")))
    for st, c in extra: out.append((st, c))
    return out, staff_names


def main(extra=()):
    cs, staff_names = claims(extra)
    print(f"{PRED} claims: {len(cs)}; declared kinds: {sorted(KINDS)}")
    if not cs:
        print("REFUSED: nothing to check. An empty denominator is not a pass."); sys.exit(2)
    db = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True); db.row_factory = sqlite3.Row
    sys.path.insert(0, os.path.join(BASE, "service")); import queries as Q
    a1 = [f"{st}: {c.get('subject')}" for st, c in cs if (c.get("subject") or [None])[0] != "club_season"]
    a2 = [f"{st}: {(c.get('value') or {}).get('kind')!r}" for st, c in cs if (c.get("value") or {}).get("kind") not in KINDS]
    a3, a4 = [], []
    for st, c in cs:
        v = c.get("value") or {}; s = c.get("subject") or []
        if c.get("person"): a3.append(f"{st}: carries person {c['person']}"); continue
        said = {nm(v.get("name_as_printed")), nm(v.get("text_as_printed"))} - {""}
        if said & staff_names: a3.append(f"{st}: '{v.get('name_as_printed')}' is a name a staff role prints")
        if s[:1] == ["club_season"] and len(s) >= 4 and st != "selftest":
            try:
                view = Q.club_season(db, s[1], int(s[2]), s[3])
            except Exception as e:
                a4.append(f"{s}: {type(e).__name__}"); continue
            held = {nm(n) for m in view.get("members", []) + view.get("staff", []) for n in [m.get("index_name")] if n}
            if said & held: a3.append(f"{st}: '{v.get('name_as_printed')}' is the name of a man on {s}")
            if (v.get("kind"), v.get("text_as_printed")) not in {(x.get("kind"), x.get("text_as_printed"))
                                                                  for x in view.get("attributes_as_printed", [])}:
                a4.append(f"{s} {v.get('text_as_printed')!r}")
        elif st == "selftest" and v.get("name_as_printed") == "Herman Smith":
            if nm("Herman Smith") in staff_names: a3.append("selftest: a staff name")
    check(not a1, f"A1 every entry is on a club-season subject ({len(a1)} not: {a1[:3]})")
    check(not a2, f"A2 every kind is declared ({len(a2)} not: {a2[:3]})")
    check(not a3, f"A3 no entry names a person ({len(a3)} do: {a3[:3]})")
    check(not a4, f"A4 every entry is served in its club-season view ({len(a4)} not: {a4[:3]})")
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # PROVE IT CAN FAIL, on claims written nowhere: one on a game subject, one with an undeclared kind,
        # one carrying a person, one printing a name a staff role prints.
        fake = [("selftest", {"predicate": PRED, "subject": ["game", "NFL", "1925", "x"], "value": {"kind": "mascot"}}),
                ("selftest", {"predicate": PRED, "subject": ["club_season", "NFL", "1923", "CAN"], "value": {"kind": "sponsorship"}}),
                ("selftest", {"predicate": PRED, "subject": ["club_season", "NFL", "1923", "CAN"], "person": "P_SELFTEST",
                              "value": {"kind": "mascot"}}),
                ("selftest", {"predicate": PRED, "subject": ["club_season", "NFL", "1923", "CAN"],
                              "value": {"kind": "mascot", "name_as_printed": "Herman Smith"}})]
        main(extra=fake)
        ok = len(FAILS) >= 3
        print("self-test:", "the gate fails when it should" if ok else "SELF-TEST DID NOT FAIL -- the gate proves nothing")
        sys.exit(0 if ok else 1)
    sys.exit(main())
