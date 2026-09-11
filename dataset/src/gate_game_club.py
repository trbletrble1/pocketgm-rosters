"""Gate: a game claim's club is the club its own row prints in full.

Ryan's ruling, 2026-09-11. A PFA game-log row names the man's club three ways -- a link, a full
name and a short label for phones -- and on about 22% of PLAYOFF rows the short label prints the
OPPONENT. The ingest took the short label, so 8,511 `pfa.postseason_game` claims were keyed to the
man who beat him or lost to him, 742 rosters carried their opponents, and 2,465 biographies named
clubs a man never played for. The link and the full name agree on every row checked; the short
label is the field that disagrees.

  G1  EVERY `pfa.postseason_game` AND `pfa.game_log` CLAIM WITH A CLUB SITS ON THE CLUB ITS OWN
      ROW'S FULL PRINTED NAME RESOLVES TO, in its league and year. A full name that cannot be
      resolved is a FAILURE, not a pass: a claim the gate cannot check has not been checked.
      Refuses an empty population.

  G2  A CLUB STRING THE INGEST REWROTE IS ONE PFA PRINTS RIGHTLY FOR THAT CLUB THAT YEAR.
  G3  ONE MAN'S CLUB-SEASON SITS ON ONE STRING, unless PFA printed each rightly (see g23()).
      Added the same day: the first pass took the table's code for a rewritten row and split
      652 man-club-seasons across two strings (CHIB and CHI for one Bear's one season).

  G4  A DECLARED EXCEPTION IS CHECKED, NOT EXEMPTED (declarations/pfa-log-club-exceptions.json).
      Ryan, 2026-09-11: the 66 swapped 1934 Reds/Gunners rows are held on the club their short
      label and both sides of every game agree on. G1 does not see them; G4 does -- each is held,
      on its declared club, and still shows the declared evidence, or the gate fails and says the
      exception has become wrong.
  G5  THE ROWS OF THAT SHAPE ARE EXACTLY THE DECLARED ONES, across the whole archive.

Resolves through src/clubs.py -- the one resolver -- and never through a copy of it.

    python3 src/gate_game_club.py [--selftest]
    python3 src/gate_game_club.py --stores pfa-gamelogs-1940s ...   (G2/G3 on unpublished stores)
"""
import os, sys, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))

PREDICATES = ("pfa.postseason_game", "pfa.game_log")
FAILS = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok: FAILS.append(msg)


def g1(rows, resolve):
    """rows: (predicate, year, league, club_id, club_as_printed, n). resolve(printed, year, league) -> club id or None."""
    tot = 0; bad = collections.Counter(); unres = collections.Counter(); cache = {}
    for pred, y, lg, cid, printed, n in rows:
        tot += n
        k = (printed, y, lg)
        if k not in cache: cache[k] = resolve(printed, y, lg) if printed else None
        full = cache[k]
        if full is None: unres[(pred, printed, y)] += n
        elif full != cid: bad[(pred, y, printed, cid)] += n
    if not tot:
        check(False, "G1 a game claim's club is the club its row prints in full -- NO game claim to check"); return bad, unres
    check(not bad, f"G1 all {tot:,} game claims sit on the club their own row prints in full"
          + ("" if not bad else f" -- {sum(bad.values()):,} do not, e.g. {[k for k, _ in bad.most_common(4)]}"))
    check(not unres, f"G1 every game claim's printed club resolves, so every one was checked"
          + ("" if not unres else f" -- {sum(unres.values()):,} cannot be, e.g. {[k for k, _ in unres.most_common(4)]}"))
    by = collections.Counter()
    for (pred, *_), n in bad.items(): by[pred] += n
    if by: print(f"         by predicate: {dict(by)}")
    return bad, unres


def g23(rows):
    """rows: (predicate, person, year, league, club_id, club_str, short_label, n).

    G2  A CLUB STRING THE INGEST REWROTE IS ONE PFA PRINTS RIGHTLY FOR THAT CLUB THAT YEAR,
        wherever PFA prints one. Where the short label named the opponent, the ingest must not
        reach for the table's code: PFA labels the Bears CHIB and the table holds CHI, and the
        first pass keyed a Bear's wrong-labelled rows CHI beside his right-labelled CHIB ones.
    G3  ONE MAN'S CLUB-SEASON SITS ON ONE STRING in these claims, unless PFA itself printed each
        of them rightly for that club that year (it prints the 1949 Brooklyn-New York Yankees
        both B-NY and BNY). Measured on the first pass: 652 split, 388 men; before it, 12."""
    right = collections.defaultdict(set)                  # (club, year, league) -> labels printed rightly
    for _p, _pe, y, lg, cid, cs, sh, n in rows:
        if sh and cs == sh: right[(cid, y, lg)].add(sh)
    bad2 = collections.Counter(); tok = collections.defaultdict(set); tot = 0
    for _p, pe, y, lg, cid, cs, sh, n in rows:
        tot += n; tok[(pe, cid, y, lg)].add(cs)
        ok_labels = right.get((cid, y, lg))
        if cs != sh and ok_labels and cs not in ok_labels: bad2[(y, lg, cs, tuple(sorted(ok_labels)))] += n
    if not tot:
        check(False, "G2 a rewritten club string is one PFA prints -- NO game claim to check"); return
    check(not bad2, f"G2 every rewritten club string among {tot:,} game claims is one PFA prints rightly for the club"
          + ("" if not bad2 else f" -- {sum(bad2.values()):,} are not, e.g. {[k for k, _ in bad2.most_common(4)]}"))
    split = collections.Counter()
    for (pe, cid, y, lg), cs in tok.items():
        if len(cs) > 1 and not cs <= right.get((cid, y, lg), set()): split[(lg, tuple(sorted(cs)))] += 1
    check(not split, f"G3 no man's club-season sits on two strings PFA did not both print"
          + ("" if not split else f" -- {sum(split.values()):,} do, e.g. {split.most_common(4)}"))


EXC_PATH = os.path.join(BASE, "declarations", "pfa-log-club-exceptions.json")
# rows for g45: (store, cid, predicate, year, league, club_id, club_str, full name printed,
#                short label printed, opponent printed, boxscore, club_held_by_declared_exception)


def shape(rows, resolve):
    """-> {(store, cid)} of claims with THE 1934 SHAPE: the short label and the opposing side's
    printed opponent agree with each other; that string is no label PFA prints rightly for the
    row's FULL-NAME club, nor one the opposing side prints rightly for itself (the 2006 Saints
    naming themselves); and the full-name club has no rightly labelled row in that game -- its
    side is not on the field. F is read from the full name, so a row held elsewhere is still found."""
    right = collections.defaultdict(set)
    for st, cid, _p, y, lg, club, cs, full, lab, opp, box, _m in rows:
        if lab and cs == lab: right[(club, y, lg)].add(lab)
    games = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    attested = collections.defaultdict(set)
    for st, cid, _p, y, lg, club, cs, full, lab, opp, box, _m in rows:
        if not box: continue
        games[box][club][opp] += 1
        if lab and lab in right.get((club, y, lg), ()): attested[box].add(club)
    hits = set()
    for st, cid, _p, y, lg, club, cs, full, lab, opp, box, _m in rows:
        if not box or not lab: continue
        F, Y = resolve(full, y, lg), resolve(opp, y, lg)
        other = games[box].get(Y) if Y else None
        if not other: continue
        O = other.most_common(1)[0][0]
        if lab == O and O not in right.get((F, y, lg), ()) and O not in right.get((Y, y, lg), ()) \
                and F not in attested[box]:
            hits.add((st, cid))
    return hits


def g45(rows, resolve, decl):
    """G4  A DECLARED EXCEPTION IS CHECKED, NOT EXEMPTED. Every declared row is in the model, marked,
        on its declared club and string, and STILL shows its declared evidence: the full name, the
        short label and the opponent as declared, and every row of the opposing side in that game
        still printing what the declaration says it prints. No undeclared claim carries the mark.
        If PFA corrects the page this FAILS -- the exception has become wrong and says so.
    G5  THE SHAPE IS EXACTLY THE DECLARED ROWS: no undeclared row of the archive has it, and every
        declared row still does."""
    declared = {(d["store"], d["claim_id"]): (d, ex["id"]) for ex in decl["exceptions"] for d in ex["rows"]}
    if not declared:
        check(False, "G4 a declared exception is checked -- NO declared row"); return
    games = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for r in rows:
        if r[10]: games[r[10]][r[5]][r[9]] += 1
    have = {(r[0], r[1]): r for r in rows}
    bad = collections.Counter(); eg = []
    for key, (d, ex_id) in declared.items():
        r = have.get(key)
        if r is None: why = "declared row not in the model"
        elif r[11] != ex_id: why = "not held by the exception (the page no longer prints what was declared?)"
        elif (r[5], r[6]) != (d["held_on_club_id"], d["held_on_club_string"]): why = "not on the declared club"
        elif (r[7], r[8], r[9]) != (d["full_name_as_printed"], d["short_label_as_printed"], d["opponent_as_printed"]):
            why = "the row no longer prints the declared full name, label and opponent"
        elif set(games[r[10]].get(resolve(d["opponent_as_printed"], r[3], r[4])) or {}) != {d["opponents_print"]}:
            why = "the opposing side no longer prints the declared opponent, unanimously"
        else: continue
        bad[why] += 1
        if len(eg) < 3: eg.append((key[1], why))
    stray = [(r[0], r[1]) for r in rows if r[11] and (r[0], r[1]) not in declared]
    check(not bad, f"G4 all {len(declared):,} declared exception rows are held and still show their evidence"
          + ("" if not bad else f" -- {sum(bad.values()):,} do not: {dict(bad)}, e.g. {eg}"))
    check(not stray, "G4 no undeclared claim is held by an exception"
          + ("" if not stray else f" -- {len(stray):,} are, e.g. {stray[:3]}"))
    hits = shape(rows, resolve)
    new, gone = hits - set(declared), set(declared) - hits
    check(not new and not gone, f"G5 the rows of the declared shape are exactly the {len(declared):,} declared"
          + ("" if not new else f" -- {len(new):,} UNDECLARED rows have it, e.g. {sorted(new)[:3]}")
          + ("" if not gone else f" -- {len(gone):,} declared rows no longer have it, e.g. {sorted(gone)[:3]}"))


def selftest():
    global FAILS
    ok = True
    R = {"Detroit Lions": "det", "DET": "det", "Cincinnati Reds": "cin", "CIN": "cin",
         "St. Louis Gunners": "stl", "SLG": "stl"}
    res = lambda s, y, lg: R.get(s)
    lions = [("s", f"d{i}", "g", 1934, "NFL", "det", "DET", "Detroit Lions", "DET", "CIN", "b", None) for i in range(2)]
    reds = [("s", "c1", "g", 1934, "NFL", "cin", "CIN", "Cincinnati Reds", "CIN", "DET", "b", None)]
    held = ("s", "x1", "g", 1934, "NFL", "cin", "CIN", "St. Louis Gunners", "CIN", "DET", "b", "ex")
    decl = {"exceptions": [{"id": "ex", "rows": [{
        "store": "s", "claim_id": "x1", "held_on_club_id": "cin", "held_on_club_string": "CIN",
        "full_name_as_printed": "St. Louis Gunners", "short_label_as_printed": "CIN",
        "opponent_as_printed": "DET", "opponents_print": "CIN"}]}]}
    corrected = ("s", "x1", "g", 1934, "NFL", "cin", "CIN", "Cincinnati Reds", "CIN", "DET", "b", None)
    another = ("s", "x2", "g", 1934, "NFL", "stl", "SLG", "St. Louis Gunners", "CIN", "DET", "b", None)
    lions_now = [r[:9] + ("PIT",) + r[10:] for r in lions]
    for label, rows, want_fail in (
            ("G4/G5 the declared 1934 row, held, its evidence intact", lions + reds + [held], False),
            ("G4/G5 PFA corrects the page: the row now prints Cincinnati Reds", lions + reds + [corrected], True),
            ("G5 a second swapped row nobody declared", lions + reds + [held, another], True),
            ("G4 the opposing side no longer prints CIN", lions_now + reds + [held], True)):
        FAILS = []; g45(rows, res, decl); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    FAILS = []
    for label, rows, want_fail in (
            ("G2/G3 a Bear's wrong-labelled row keyed on the table's CHI beside his CHIB rows",
             [("g", "P1", 2010, "NFL", "bears", "CHIB", "CHIB", 2), ("g", "P1", 2010, "NFL", "bears", "CHI", "SEA", 1)], True),
            ("G2/G3 the same row keyed on the CHIB PFA prints",
             [("g", "P1", 2010, "NFL", "bears", "CHIB", "CHIB", 2), ("g", "P1", 2010, "NFL", "bears", "CHIB", "SEA", 1)], False),
            ("G3 two strings PFA printed rightly for one club (B-NY and BNY)",
             [("g", "P1", 1949, "AAFC", "yanks", "B-NY", "B-NY", 1), ("g", "P1", 1949, "AAFC", "yanks", "BNY", "BNY", 1)], False),
            ("G2 nothing to check", [], True)):
        FAILS = []; g23(rows); got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")
    FAILS = []

    def expect(label, rows, want_fail):
        global FAILS
        nonlocal ok
        FAILS = []
        g1(rows, lambda p, y, lg: {"San Francisco 49ers": "club-sf", "Carolina Panthers": "club-car"}.get(p))
        got = bool(FAILS); g = got == want_fail; ok &= g
        print(f"  {'ok  ' if g else 'FAIL'} {label}: expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if got else 'pass'}")

    expect("G1 a 49er's 2013 playoff game keyed to Carolina",
           [("pfa.postseason_game", 2013, "NFL", "club-car", "San Francisco 49ers", 1)], True)
    expect("G1 a printed club the table cannot resolve",
           [("pfa.postseason_game", 2013, "NFL", "club-sf", "Nowhere Town", 1)], True)
    expect("G1 a Chief's Super Bowl game keyed to a club that league never held (no club id)",
           [("pfa.postseason_game", 1966, "AFL", None, "San Francisco 49ers", 1)], True)
    expect("G1 nothing to check", [], True)
    expect("G1 the same game keyed to San Francisco",
           [("pfa.postseason_game", 2013, "NFL", "club-sf", "San Francisco 49ers", 1)], False)
    FAILS = []
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv: return selftest()
    from clubs import Clubs
    C = Clubs()

    import functools

    @functools.lru_cache(maxsize=None)
    def resolve(printed, y, lg):
        if not printed: return None
        r = C.resolve(printed, y, lg, source="season_key")
        return r[0] if r else None
    if "--stores" in argv:
        # G2/G3 READ STRAIGHT FROM STORE FILES, so the property can be shown on a store before
        # it is published. The club id is resolved from the claim's own string, as the model does.
        import json
        agg = collections.Counter()
        for name in argv[argv.index("--stores") + 1:]:
            for c in json.load(open(os.path.join(BASE, "build", f"{name}.json")))["claims"]:
                if c["predicate"] not in PREDICATES: continue
                s = c["subject"]; lg, y = s[3].rsplit("-", 1); y = int(y)
                agg[(c["predicate"], s[1], y, lg, resolve(s[2], y, lg), s[2],
                     c["value"].get("club_short_label_as_printed"))] += 1
        g23([k + (n,) for k, n in agg.items()])
    else:
        import paths
        conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
        # NO `club_id IS NOT NULL`. A key that resolves to no club is not a key with nothing to
        # check -- it is a claim not on its printed club. The first version skipped them, and so
        # never saw the 32 Super Bowl and AAFC-title keys (`AFL|1966|GB`, `AAFC|1946|NYY`) that
        # P3 caught when the rebuild removed them.
        rows = conn.execute(
            "SELECT predicate, year, league, club_id, json_extract(value,'$.club_as_printed'), count(*) FROM claim "
            "WHERE predicate IN (?, ?) AND json_extract(value,'$.club_held_by_declared_exception') IS NULL "
            "GROUP BY 1,2,3,4,5", PREDICATES).fetchall()
        g1(rows, resolve)       # a claim held by a declared exception is checked by G4 instead, never skipped
        import json
        g45(conn.execute(
            "SELECT store, cid, predicate, year, league, club_id, club_str, json_extract(value,'$.club_as_printed'), "
            "json_extract(value,'$.club_short_label_as_printed'), json_extract(value,'$.opponent_as_printed'), "
            "json_extract(value,'$.boxscore'), json_extract(value,'$.club_held_by_declared_exception') "
            "FROM claim WHERE predicate IN (?, ?)", PREDICATES).fetchall(), resolve, json.load(open(EXC_PATH)))
        g23(conn.execute(
            "SELECT predicate, person, year, league, club_id, club_str, "
            "json_extract(value,'$.club_short_label_as_printed'), count(*) FROM claim "
            "WHERE predicate IN (?, ?) AND club_id IS NOT NULL GROUP BY 1,2,3,4,5,6,7", PREDICATES).fetchall())
    if FAILS:
        print(f"\nGAME CLUB GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nGAME CLUB GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
