"""Gate: what the Ghosts line-up ingest must not do. Held on the STORE.

  G1  NO STARTING PLACE COMES FROM A SUBSTITUTION. Every started_a_game claim names a
      man who is IN THAT PAGE'S ELEVEN, as measured. The 53 substitutions exist to be
      kept out of the elevens and folding them would be undetectable afterwards.

      THE FIRST VERSION OF THIS PROPERTY WAS WRONG AND THE GATE PROVED IT. It said a
      substitute is never a starter, and it failed on Eastman and Gaffney at Lancaster:
      the account reads "Heath for Gaffney" and then "Gaffney for Heath". A man STARTED,
      WAS REPLACED, AND CAME BACK ON -- re-entry was legal in 1926. Being in both lists
      is a fact about the game, not a defect. What must never happen is a man reaching
      the eleven BECAUSE he was substituted, which is what this now checks.
  G2  EVERY started_a_game LANDS ON A CLUB THE TABLE HOLDS, resolved through Clubs().
      The Eastern League stays excluded and no club is created; a claim on a club the
      table does not hold would be this ingest admitting one by the back door.
  G3  NO IMAGE IS TAKEN. No claim references a .jpg/.gif, and the Gooch photograph is
      present in `refusals` with its credit. A refusal nobody wrote down cannot be told
      from a page nobody read.
  G4  EVERY CLAIM CITES A SNAPSHOT with a sha256, and names Fenton as the FINDING AID
      rather than as the source of the fact.
  G5  EVERY MAN NAMED AS A STARTER IS ALSO PLACED ON THAT CLUB-SEASON, by a claim whose
      subject is a STINT. This is the property that was missing, and its absence cost a
      whole ingest: G2 checked that the season key RESOLVES through the club table, which
      it did, and nothing checked that the man ends up ON the club-season. He did not --
      build_person_index writes a season only from a ["stint", person, club, season]
      subject, so 25 men were promoted holding `seasons: []` and Bethlehem Bears 1926 sat
      at rank 2 of the hunting list marked EMPTY after being filled.

      A GATE THAT CHECKS A KEY IS WELL-FORMED IS NOT A GATE THAT CHECKS THE MAN ARRIVED.

    python3 src/gate_ghosts_lineups.py [--selftest]
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
STORE = os.path.join(BASE, "build", "ghosts-lineups.json")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def run(d):
    claims = d["claims"]
    starters, subs = {}, {}
    for c in claims:
        pg = c["source_record"].split("#", 1)[1]
        if c["predicate"] == "roster_membership.started_a_game":
            starters.setdefault(pg, set()).add(
                str((c.get("extra") or {}).get("name_as_printed", "")).strip().lower())
        elif c["predicate"] == "ghosts.substitution":
            subs.setdefault(pg, set()).add(
                str(c["value"]["came_on_as_printed"]).strip().lower())
    meas = json.load(open(os.path.join(BASE, "build-reports", "ghosts-lineups.json")))
    eleven = {g["page"]: {str(x).strip().lower()
                          for x in (g["away_men"] + g["home_men"]) if x}
              for g in meas["games"]}
    bad = {}
    for pg, names in starters.items():
        page = pg.split("@")[0]
        outside = sorted(n for n in names if n and n not in eleven.get(page, set()))
        if outside: bad[page] = outside
    check(not bad, f"G1 every starting place names a man in that page's eleven"
          + ("" if not bad else f" -- {bad}"))

    from clubs import Clubs
    C = Clubs()
    bad = []
    for c in claims:
        if c["predicate"] != "roster_membership.started_a_game": continue
        lg, y, code = str(c["value"]).split("|")
        if not any(s.get("code") == code for cl in C.T["clubs"] for s in cl["segments"]):
            bad.append(c["value"])
    check(not bad, f"G2 all {len(starters and [1] or [1]) and sum(len(v) for v in starters.values())} "
                   f"starting places land on a club the table holds"
          + ("" if not bad else f" -- {sorted(set(bad))[:4]}"))

    img = [c for c in claims if re.search(r"\.(jpe?g|gif|png)", json.dumps(c), re.I)]
    photo = [r for r in d.get("refusals", []) if r.get("what") == "photograph"]
    check(not img and photo and photo[0].get("credit_as_printed"),
          f"G3 no image is taken, and the photograph is refused WITH its credit"
          + ("" if not img else f" -- {len(img)} claims reference an image"))

    # G5 -- placement, not resolvability
    started, placed = {}, {}
    for c in claims:
        s = c.get("subject") or []
        if c["predicate"] == "roster_membership.started_a_game" and s and s[0] == "person":
            lg, y, code = str(c["value"]).split("|")
            started.setdefault((s[1], lg, y, code), 0)
            started[(s[1], lg, y, code)] += 1
        elif c["predicate"] == "ghosts.lineup_membership" and s and s[0] == "stint":
            lg, _, y = str(s[3]).rpartition("-")
            placed[(s[1], lg, y, s[2])] = True
    unplaced = sorted(k for k in started if k not in placed)
    check(not unplaced, f"G5 all {len(started)} men named as starters are PLACED on that "
                        f"club-season by a stint subject"
          + ("" if not unplaced else f" -- {len(unplaced)} are not: {unplaced[:3]}"))

    nosnap = [c for c in claims if not c.get("snapshot")
              or not (c.get("finding_aid") or {}).get("_is_not_the_source_of_the_fact")]
    srs = d["source_records"]
    nosha = [k for k, v in srs.items() if not v.get("sha256")]
    check(not nosnap and not nosha,
          f"G4 all {len(claims)} claims cite a snapshot and name Fenton as the finding aid"
          + ("" if not (nosnap or nosha) else f" -- {len(nosnap)} without, {len(nosha)} records without a sha256"))


def selftest():
    # a starter who is in NO eleven -- the thing G1 must refuse
    io_meas = os.path.join(BASE, "build-reports", "ghosts-lineups.json")
    # THE SELFTEST IS THIS MORNING'S STORE: a starter with no stint claim placing him,
    # which is exactly what was published and exactly what no gate refused.
    d = {"claims": [
        {"source_record": "x#p", "predicate": "roster_membership.started_a_game",
         "subject": ["person", "P_1"],
         "value": "EFL|1926|PFA:BET", "extra": {"name_as_printed": "Beck"},
         "snapshot": "u", "finding_aid": {"_is_not_the_source_of_the_fact": "y"}},
        {"source_record": "x#p", "predicate": "ghosts.substitution",
         "value": {"came_on_as_printed": "Beck", "replaced_as_printed": "Z"},
         "snapshot": "u", "finding_aid": {"_is_not_the_source_of_the_fact": "y"}}],
        "source_records": {"x#p": {"sha256": "a"}},
        "refusals": [{"what": "photograph", "credit_as_printed": "c"}]}
    global FAILS; FAILS = []
    run(d)
    ok1 = any("G1" in f for f in FAILS)
    ok5 = any("G5" in f for f in FAILS)
    print(f"  {'ok  ' if ok5 else 'FAIL'} G5 catches a starter placed by no stint subject: "
          f"expected a failure, got {'one' if ok5 else 'none'}")
    print("SELFTEST OK" if (ok1 and ok5) else "SELFTEST FAILED")
    return 0 if (ok1 and ok5) else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    run(json.load(open(STORE)))
    if FAILS:
        print(f"\nGHOSTS LINE-UP GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nGHOSTS LINE-UP GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
