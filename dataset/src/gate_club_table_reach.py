"""HOW FAR THE CLUB TABLE REACHES -- counted every run, never silent.

A season key can place a man on a club-season the club table cannot name. That is
not an error: the archive holds the man, and naming the club-season on one source's
say-so is what SPAN_EXTENSIONS refuses. What it must not be is INVISIBLE. Before
2026-09-09 it was: bios printed the raw token -- "two games with the PFA:WIL in
1941" -- and nothing counted them.

THE GATE IS A RATCHET, not a zero. It fails when the number RISES above the ceiling
declared in declarations/clubs.json. Ruled by Ryan, 2026-09-09: it is 2,018 today and
should be a number that goes down.

FOUR OUTCOMES, counted separately, because they want different answers:

  named          the table names the club for that year. Nothing to do.
  no_name        the table holds the club and holds no name for THAT year -- the
                 2025 season, past every name span. The club did not end; the table
                 stops. Needs a source, not a ruling.
  span_narrow    the token places at another year but not this one -- PFA:AMS in
                 1996 against a code span beginning 1998. SPAN_EXTENSIONS is the
                 route, and it needs corroboration from a second source.
  never_placed   the table does not hold this club at all. Admitting a club, not
                 extending one, and it goes to Ryan with a list.

    python3 src/gate_club_table_reach.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
DECL = os.path.join(BASE, "declarations", "clubs.json")
INDEX = os.path.join(BASE, "build-reports", "person-index.json")

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def classify(C, people):
    """-> (counts, per-triple keys). One pass over every season key in the index."""
    n = collections.Counter(); triples = collections.Counter()
    for pid, p in people.items():
        if not isinstance(p, dict): continue
        for src in ("seasons", "coaching_seasons"):
            for k in (p.get(src) or {}):
                parts = k.split("|", 2)
                if len(parts) != 3: continue
                lg, y, tok = parts
                yr = str(y).lstrip("y")
                if not yr.isdigit(): continue
                yy = int(yr)
                r = C.resolve(tok, yy, None, source="season_key")
                if r and C.name_for(r[0], yy): n["named"] += 1; continue
                if r: cat = "no_name"
                elif any(C.resolve(tok, y2, None, source="season_key") for y2 in range(1890, 2031)):
                    cat = "span_narrow"
                else: cat = "never_placed"
                n[cat] += 1; triples[(cat, lg, tok, yy)] += 1
    return n, triples


def main(argv):
    if "--selftest" in argv: return selftest()
    from clubs import Clubs
    C = Clubs()
    idx = json.load(open(INDEX))
    people = {k: v for k, v in idx.items() if k != "_clubs"}
    n, triples = classify(C, people)
    unnamed = n["no_name"] + n["span_narrow"] + n["never_placed"]
    decl = json.load(open(DECL)).get("CLUB_TABLE_REACH") or {}
    ceiling = int(decl.get("ceiling", 0))
    print(f"CLUB TABLE REACH  ({n['named'] + unnamed:,} season keys)")
    print(f"  named by the table                     {n['named']:>8,}")
    print(f"  the club is held, no name for that year{n['no_name']:>8,}")
    print(f"  the span is too narrow for this year   {n['span_narrow']:>8,}")
    print(f"  the token is never placed              {n['never_placed']:>8,}")
    for cat in ("no_name", "span_narrow", "never_placed"):
        worst = collections.Counter({(t, y): v for (c, l, t, y), v in triples.items() if c == cat}).most_common(4)
        if worst: print(f"    {cat:<14}worst {worst}")
    check(unnamed <= ceiling,
          f"season keys the table cannot name: {unnamed:,} against a ceiling of {ceiling:,}"
          + ("" if unnamed <= ceiling else
             f" -- it ROSE by {unnamed - ceiling:,}. Either the club table lost reach, or new "
             f"season keys arrived on club-seasons it does not describe. Both want looking at "
             f"before the ceiling is raised."))
    if unnamed < ceiling:
        print(f"  NOTE: it FELL by {ceiling - unnamed:,}. Lower `ceiling` in declarations/clubs.json "
              f"to {unnamed:,} so the ground gained is held.")
    if FAILS:
        print(f"\nCLUB TABLE REACH GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCLUB TABLE REACH GATE: pass"); return 0


def selftest():
    class C:
        span = (1998, 2007)
        @staticmethod
        def resolve(tok, yr, *a, **k):
            if tok == "KNOWN": return ("club-known", "code")
            if tok == "NARROW" and 1998 <= yr <= 2007: return ("club-narrow", "code")
            return None
        @staticmethod
        def name_for(cid, yr):
            return "Known FC" if cid == "club-known" else ("Narrow FC" if cid == "club-narrow" else None)
    people = {
        "P_1": {"seasons": {"NFL|2000|KNOWN": {}}},                       # named
        "P_2": {"seasons": {"NFL|1996|NARROW": {}}},                      # span too narrow
        "P_3": {"seasons": {"NFL|1967|NEVER": {}}},                       # never placed
    }
    n, tr = classify(C, people)
    ok = True
    for want, got, label in ((1, n["named"], "named"), (1, n["span_narrow"], "span too narrow"),
                             (1, n["never_placed"], "never placed"), (0, n["no_name"], "no name")):
        good = want == got; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected {want}, got {got}")
    # the ratchet must fail when the number rises
    unnamed = n["no_name"] + n["span_narrow"] + n["never_placed"]
    for ceiling, want_fail in ((unnamed - 1, True), (unnamed, False)):
        failed = unnamed > ceiling
        good = failed == want_fail; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} ceiling {ceiling} with {unnamed} unnamed: "
              f"expected {'FAIL' if want_fail else 'pass'}, got {'FAIL' if failed else 'pass'}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
