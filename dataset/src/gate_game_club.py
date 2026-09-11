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


def selftest():
    global FAILS
    ok = True
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

    def resolve(printed, y, lg):
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
            "WHERE predicate IN (?, ?) GROUP BY 1,2,3,4,5", PREDICATES).fetchall()
        g1(rows, resolve)
        g23(conn.execute(
            "SELECT predicate, person, year, league, club_id, club_str, "
            "json_extract(value,'$.club_short_label_as_printed'), count(*) FROM claim "
            "WHERE predicate IN (?, ?) AND club_id IS NOT NULL GROUP BY 1,2,3,4,5,6,7", PREDICATES).fetchall())
    if FAILS:
        print(f"\nGAME CLUB GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nGAME CLUB GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
