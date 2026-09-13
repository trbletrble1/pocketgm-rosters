"""Gate: what the Frankford book ingest must not do. Held on the STORES and the club
table, so a hand-edited store fails too.

  F1  ONLY AN EXACT NAME PLACES A MAN. Every stint claim records `_joined_on` and it is
      "exact name on the club-season". Surname matching is inadmissible for a
      club-season placement -- Andy King, Jim Talbot, the 1934 Cincinnati Reds, three
      times. Reporting the 179 surname rows as fills would have claimed 27 positions
      filled where 7 is the defensible figure.
  F2  A NAME GOES IN BESIDE WHAT IS HELD. Every fyjbook.name_as_printed claim is
      person-scoped and says what the archive already holds; the archive does not choose
      between two things a source printed.
  F3  NO CLUB IS CREATED FROM AN OPPONENT STRING. Every non-league opponent is listed as
      a candidate and none of them is in the club table.
  F4  EVERY CLAIM'S SOURCE_RECORD IS IN ITS STORE'S OWN TABLE. RS-G3 is a standing red
      at 414 and a rise hides inside it -- learned the same afternoon, at a cost of one
      published model.
  F5  NO PHOTOGRAPH GOES IN. Ryan's ruling: the images are screenshots resized for the
      web, not the HSF originals, and the 1919 team photo names nobody.
  F6  A YEAR NO DOCUMENT NAMES IS DARK. The early Frankford club is declared for 1899,
      1900, 1903 and 1906; 1901, 1902, 1904 and 1905 must be dark or the table asserts
      four club-seasons no source names.

  F7  A MANAGER IS NOT A PLAYER. No stint claim carries a position cell that names a
      non-playing role (Manager, Coach, Captain, Trainer, President -- the gate's own
      list, not read from the declaration, so a declaration that forgets a role still
      fails here). Ryan, 2026-09-12: Swope and Gilmore are printed as Manager. The
      declaration said so from 2026-09-09 and both went in as playing stints anyway.
  F8  STAFF AND CAPTAIN-OR-COACH ARE ABOUT THE CLUB-SEASON. Every club_staff_role and
      fyjbook.captain_or_coach_as_printed claim has a club_season subject and names no
      person, and no Frankford store writes role_title: "Captains/Coaches" does not
      distinguish, so it must never become a coaching season.
  F9  EVERY FRONT-OFFICE LINE IS ACCOUNTED FOR: each (line, year) is either a claim on
      that year's club-season or listed NOT PLACED with its reason, and none is both.
  F10 NO PROMOTED MAN IS LEFT WITH NOTHING. Every person promoted from this site's leads
      still holds at least one claim in these stores. Moving a Manager off his stint
      without keeping his record would leave apply_player_promotions to create an empty
      one -- and Ryan ruled the record is kept.

  python3 src/gate_frankford_book.py [--selftest]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
STORES = ("frankford-book", "frankford-book-ind")
# TWO ADMISSIBLE TIERS, BOTH EXACT. A man this ingest raised as a lead and
# promote_players promoted is matched on the EXACT printed name on the EXACT club-season
# through the promotion store -- the lead's own identity, not a name join against the
# archive. What stays inadmissible is anything surname-shaped.
EXACT = "exact name on the club-season"
PROMOTED = "this ingest's own lead, promoted by promote_players.py"
ADMISSIBLE = (EXACT, PROMOTED)
FAILS = []
# F7's own list. NOT read from declarations/frankford-book.json: a gate that derives its
# check from the declaration passes whenever the declaration is wrong in the same way.
NOT_PLAYING = ("manager", "coach", "captain", "trainer", "president")


def not_playing(pos):
    return any(w in str(pos or "").lower() for w in NOT_PLAYING)


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def load():
    out = {}
    for s in STORES:
        p = os.path.join(BASE, "build", s + ".json")
        if os.path.exists(p): out[s] = json.load(open(p))
    return out


def main(argv):
    if "--selftest" in argv: return selftest()
    d = load()
    if not d:
        print("  no Frankford store is built; nothing to hold"); print("\nFRANKFORD GATE: pass"); return 0
    claims = [c for v in d.values() for c in v["claims"]]
    print(f"{len(claims):,} claims across {len(d)} stores")

    stints = [c for c in claims if c["subject"][0] == "stint"]
    off = [c for c in stints
           if not str(c.get("_joined_on", "")).startswith(ADMISSIBLE)]
    sur = [c for c in stints if "surname" in str(c.get("_joined_on", "")).lower()]
    off = off + sur
    check(not off, f"F1 all {len(stints):,} stint claims were placed by an exact name "
                   f"({sum(1 for c in stints if c.get('_joined_on') == EXACT)} on the archive's "
                   f"own name, {len(stints) - sum(1 for c in stints if c.get('_joined_on') == EXACT)} "
                   f"on this ingest's own promoted lead)"
          + ("" if not off else f" -- {len(off)} were not: {[c.get('_joined_on') for c in off[:2]]}"))

    names = [c for c in claims if c["predicate"] == "fyjbook.name_as_printed"]
    bad = [c for c in names if c["subject"][0] != "person" or not c.get("_beside_not_instead_of")]
    check(not bad, f"F2 all {len(names):,} name claims are person-scoped and say what is held "
                   f"beside them" + ("" if not bad else f" -- {len(bad)} do not"))

    opp = {o["name_as_printed"] for v in d.values()
           for o in (v.get("non_league_opponents_NOT_CREATED") or [])}
    tab = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    made = sorted(o for o in opp for c in tab["clubs"] for n in c["names"]
                  if n["name"].lower() == o.lower() and c.get("origin") == "document_only"
                  and (c.get("_document") or {}).get("source_id") == "frankford-yellow-jackets-book")
    check(not made, f"F3 none of the {len(opp)} non-league opponents became a club"
          + ("" if not made else f" -- {made[:4]} did"))

    for st, v in d.items():
        table = set(v.get("source_records") or ())
        orphan = collections.Counter(c["source_record"] for c in v["claims"]
                                     if c.get("source_record") not in table)
        check(not orphan, f"F4 {st}: every claim's source_record is in its own table"
              + ("" if not orphan else f" -- {sum(orphan.values())} name {len(orphan)} that are not"))

    # A PHOTOGRAPH IS A PREDICATE OR AN IMAGE, not the word. The first version matched the
    # substring and failed on all 415 claims, because every one carries the provenance line
    # naming HSF's "documents and photographs". A gate that fails on its own prose is noise.
    photo = [c for c in claims
             if "photo" in str(c.get("predicate", "")).lower()
             or re.search(r"\.(jpg|jpeg|png|gif|webp)\b", json.dumps(c.get("value")), re.I)]
    check(not photo, f"F5 no claim carries a photograph or an image file"
          + ("" if not photo else f" -- {len(photo)} do: {[c['predicate'] for c in photo[:3]]}"))

    early = [c for c in tab["clubs"] if c["id"] == "club-frankford-yellow-jackets-1899"]
    if early:
        seg = early[0]["segments"][0]
        want = {1901, 1902, 1904, 1905}
        got = set(seg.get("dark_years") or ())
        check(want <= got, f"F6 the years no document names are dark ({sorted(got)})"
              + ("" if want <= got else f" -- {sorted(want - got)} are not"))
    else:
        check(False, "F6 the early Frankford club is not in the table")

    staffy = [c for c in stints if c["predicate"] == "fyjbook.position" and not_playing(c.get("value"))]
    check(not staffy, f"F7 no stint carries a non-playing role as its position"
          + ("" if not staffy else f" -- {len(staffy)} do: {[(c['subject'][1], c['value']) for c in staffy[:4]]}"))

    cs_preds = ("club_staff_role", "fyjbook.captain_or_coach_as_printed")
    cs = [c for c in claims if c["predicate"] in cs_preds]
    off = [c for c in cs if c["subject"][0] != "club_season" or c.get("person")
           or (isinstance(c.get("value"), dict) and c["value"].get("person"))]
    rt = [c for c in claims if c["predicate"] == "role_title"]
    check(not off and not rt, f"F8 all {len(cs)} staff and captain-or-coach claims are about a club-season "
                              f"and name no person; no role_title written"
          + ("" if not off else f" -- {len(off)} are not") + ("" if not rt else f" -- {len(rt)} role_title"))

    fo = [c for c in cs if str(c.get("source_record", "")).endswith("#front-office")]
    placed = {(c["value"]["line_as_printed"], int(c["subject"][2])) for c in fo}
    unplaced = {(u["line_as_printed"], int(u["year"]))
                for v in d.values() for u in (v.get("front_office_NOT_PLACED") or [])}
    total = next((v["front_office_lines_by_year"] for v in d.values() if v.get("front_office_lines_by_year")), None)
    both = placed & unplaced
    if total is None:
        check(False, "F9 no store records how many front-office (line, year) pairs the page prints")
    else:
        check(not both and len(placed) + len(unplaced) == total,
              f"F9 every front-office (line, year) is placed or listed NOT PLACED: {len(placed)} + "
              f"{len(unplaced)} of {total}" + ("" if not both else f" -- {len(both)} are both"))

    prom_p = os.path.join(BASE, "build", "player-promotions.json")
    mine = {p["person_id"] for p in (json.load(open(prom_p)).get("promotions") or [])
            if str(p.get("source", "")).startswith("frankford-book")} if os.path.exists(prom_p) else set()
    holding = {c["subject"][1] for c in claims if c["subject"][0] in ("stint", "person")}
    bare = sorted(mine - holding)
    check(bool(mine) and not bare, f"F10 all {len(mine)} men promoted from this site still hold a claim here"
          + ("" if not bare else f" -- {len(bare)} hold none: {bare[:4]}"))

    # F11 -- A RE-RUN REPRODUCES THE STORES. Measured 2026-09-12: re-running the ingest against
    # the served model relabelled 202 placements and flipped nine men between candidate and
    # lead, because the join read names that exist only because this ingest ran. A decider that
    # reads its own layer is not stable, and the symptom is exactly this: a second run differs.
    if "--no-rerun" not in argv:
        import io, contextlib
        import ingest_frankford_book as ING
        with contextlib.redirect_stdout(io.StringIO()):
            rerun, _ = ING.main(write=False)
        k = lambda c: (json.dumps(c["subject"]), c["predicate"], json.dumps(c["value"], sort_keys=True),
                       str(c.get("_joined_on")))
        diff = {}
        for st, v in d.items():
            a, b = {k(c) for c in v["claims"]}, {k(c) for c in rerun[st]["claims"]}
            la = {json.dumps(x.get("name_as_printed")) + str(x.get("year")) for x in v.get("leads") or []}
            lb = {json.dumps(x.get("name_as_printed")) + str(x.get("year")) for x in rerun[st].get("leads") or []}
            if a != b or la != lb:
                diff[st] = (len(a - b), len(b - a), len(la ^ lb))
        check(not diff, "F11 a re-run of the ingest reproduces both stores, claims and leads"
              + ("" if not diff else f" -- (only in store, only in re-run, leads differing): {diff}"))

    # F12 -- HELD IS NOT SERVED. Every captain-or-coach claim appears in its club-season view,
    # under `captain_or_coach_as_printed`. Measured 2026-09-12 on the first candidate: all 12
    # were held and none served -- the list was built in queries.py and never put in the view.
    # C3 in gate_surname_on_club_season covers club_staff_role only, so nothing saw it.
    # Reads the served model, or the one named by --model.
    import sqlite3
    sys.path.insert(0, os.path.join(BASE, "service"))
    import paths, queries as Q
    model = argv[argv.index("--model") + 1] if "--model" in argv else paths.READ_MODEL
    qc = sqlite3.connect(f"file:{model}?mode=ro", uri=True); qc.row_factory = sqlite3.Row
    coc = [c for c in claims if c["predicate"] == "fyjbook.captain_or_coach_as_printed"]
    unserved = []
    for c in coc:
        s = c["subject"]
        v = Q.club_season(qc, s[1], int(s[2]), s[3])
        if not any(x.get("line_as_printed") == c["value"]["line_as_printed"]
                   for x in v.get("captain_or_coach_as_printed") or []):
            unserved.append(f"{s[2]} {c['value']['name_as_printed']}")
    check(bool(coc) and not unserved, f"F12 all {len(coc)} captain-or-coach claims are served in their "
                                      f"club-season view ({os.path.basename(model)})"
          + ("" if not unserved else f" -- {len(unserved)} are not: {unserved[:3]}"))

    if FAILS:
        print(f"\nFRANKFORD GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nFRANKFORD GATE: pass"); return 0


def selftest():
    ok = True
    for label, c, want_fail in (
            ("F1 a stint placed on a surname",
             {"subject": ["stint", "P_1", "FYJ", "NFL-1926"], "_joined_on": "surname on the club-season"}, True),
            ("F1 a stint placed on an exact name",
             {"subject": ["stint", "P_1", "FYJ", "NFL-1926"], "_joined_on": EXACT}, False),
            ("F1 a stint placed on this ingest's own promoted lead",
             {"subject": ["stint", "P_1", "FYJ", "NFL-1926"],
              "_joined_on": PROMOTED + " -- the exact printed name"}, False),
            ("F1 a tier the gate has never heard of",
             {"subject": ["stint", "P_1", "FYJ", "NFL-1926"], "_joined_on": "vibes"}, True)):
        failed = (not str(c.get("_joined_on", "")).startswith(ADMISSIBLE)
                  or "surname" in str(c.get("_joined_on", "")).lower())
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    for label, c, want_fail in (
            ("F2 a name claim on a stint",
             {"subject": ["stint", "P_1", "FYJ", "NFL-1926"], "_beside_not_instead_of": "x"}, True),
            ("F2 a name claim with nothing held beside it",
             {"subject": ["person", "P_1"]}, True),
            ("F2 a name claim done right",
             {"subject": ["person", "P_1"], "_beside_not_instead_of": "the archive holds 'Doc Elliott'"}, False)):
        failed = c["subject"][0] != "person" or not c.get("_beside_not_instead_of")
        g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    for label, dark, want_fail in (
            ("F6 a span with an unnamed year left light", [1901, 1902], True),
            ("F6 every unnamed year dark", [1901, 1902, 1904, 1905], False)):
        failed = not {1901, 1902, 1904, 1905} <= set(dark); g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    for label, pos, want_fail in (
            ("F7 a stint whose position is Manager", "Manager", True),
            ("F7 a stint whose position names a captain-coach", "Captain/Coach", True),
            ("F7 a stint whose position is Right halfback", "Right halfback", False),
            ("F7 a stint whose position cell is blank", None, False)):
        failed = not_playing(pos); g = failed == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, "
              f"got {'FAIL' if failed else 'pass'}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
