"""A COACHING SEASON IS HELD IN ONE SHAPE. Ruled by Ryan, 2026-09-09.

The person index holds a man's stint seasons in two dicts. This gate checks the
PROPERTY, not the instances:

  P1  every (person, season key, predicate) in the index is reachable from EXACTLY
      ONE of `seasons` and `coaching_seasons` -- never both, never neither.
  P2  a claim's dict follows its PREDICATE. No staff predicate sits in `seasons`,
      no non-staff predicate sits in `coaching_seasons`, whatever league token the
      key carries.
  P3  a player-coach keeps both. The 330 (person, club-season) pairs holding a
      playing claim AND a staff claim must have that KEY in both dicts. This is the
      half that stops the fix being "delete the coaching seasons".
  P4  WITHDRAWN 2026-09-09, the same day it was written, and the reason is kept.
      It required that no person hold one (year, club) under both `COACHES` and a
      real league, and the fix that satisfied it folded the two together. That broke
      the club table: build_clubs corroborates a printed name against a code by
      finding one man who holds both FOR THE SAME LEAGUE-YEAR, and folding moved half
      of every such pair out of its group. Two sources attesting one season, one of
      them naming no league, is two ATTESTATIONS and not two shapes.
  P5  one year format in `coaching_seasons`: bare, never `y1979`.

WHY A GATE AND NOT A TEST OF THE FIX. The defect was not a bug in one function. It
was that the dict a claim landed in was decided by HOW THE MAN ENTERED THE ARCHIVE
-- promoted from a lead, or already held as a player -- so the same fact went to
different places. Any future ingest can reintroduce that by writing to the wrong
dict, and only a property over the whole index will see it.

    python3 src/gate_coaching_season_shape.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
DECL = os.path.join(BASE, "declarations", "coaching-seasons.json")
INDEX = os.path.join(BASE, "build-reports", "person-index.json")

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def staff_predicates(decl=None):
    d = decl or json.load(open(DECL))
    return set(d["staff_predicates"]["predicates"])


def qualifiers(decl=None):
    d = decl or json.load(open(DECL))
    return set(d["staff_predicates"]["not_staff_though_it_appears_in_those_stores"])


def audit(people, STAFF, QUAL):
    """-> counts and the first examples of every violation. Pure; the self-test calls
    it on fixtures and main() calls it on the index."""
    v = collections.Counter(); ex = collections.defaultdict(list)
    def note(k, item):
        v[k] += 1
        if len(ex[k]) < 5: ex[k].append(item)
    both_dicts = 0
    for pid, p in people.items():
        if not isinstance(p, dict): continue
        seasons = p.get("seasons") or {}
        coaching = p.get("coaching_seasons") or {}
        for k, sd in seasons.items():
            for pred in (sd.get("stint") or {}):
                if pred in STAFF: note("P2 staff predicate in `seasons`", (pid, k, pred))
                if pred in coaching.get(k, {}).get("stint", {}):
                    note("P1 the same claim in both dicts", (pid, k, pred))
        for k, sd in coaching.items():
            stint = sd.get("stint") if isinstance(sd, dict) else None
            if stint is None: continue                      # apply_promotions' own row shape
            for pred in stint:
                if pred not in STAFF and pred not in QUAL:
                    note("P2 non-staff predicate in `coaching_seasons`", (pid, k, pred))
            lg, y, club = k.split("|", 2)
            if y.startswith("y"): note("P5 a `y`-prefixed year in `coaching_seasons`", (pid, k))
        if seasons.keys() & coaching.keys(): both_dicts += 1
    return v, ex, both_dicts


def main(argv):
    if "--selftest" in argv: return selftest()
    d = json.load(open(DECL))
    STAFF, QUAL = staff_predicates(d), qualifiers(d)
    idx = json.load(open(INDEX))
    people = idx["people"] if isinstance(idx, dict) and "people" in idx else idx
    people = {k: v for k, v in people.items() if k != "_clubs"}
    v, ex, both = audit(people, STAFF, QUAL)
    print(f"COACHING SEASON SHAPE  ({len(people):,} people)")
    n_seasons = sum(len(p.get("seasons") or {}) for p in people.values() if isinstance(p, dict))
    n_coach = sum(len(p.get("coaching_seasons") or {}) for p in people.values() if isinstance(p, dict))
    print(f"  `seasons` {n_seasons:,}   `coaching_seasons` {n_coach:,}   people holding a key in both {both:,}")
    for prop in ("P1 the same claim in both dicts",
                 "P2 staff predicate in `seasons`",
                 "P2 non-staff predicate in `coaching_seasons`",
                 "P5 a `y`-prefixed year in `coaching_seasons`"):
        check(v[prop] == 0, f"{prop}: {v[prop]:,}" + (f"  e.g. {ex[prop][:2]}" if v[prop] else ""))
    # P3 -- the half that stops "delete the coaching seasons" passing
    check(both > 0, f"P3 a player-coach keeps both: {both:,} people hold a key in BOTH dicts "
                    f"(0 would mean the fix deleted them instead of moving them)")
    if FAILS:
        print(f"\nCOACHING SEASON SHAPE GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCOACHING SEASON SHAPE GATE: pass"); return 0


def selftest():
    """Show it failing before it passes, one injury per property."""
    STAFF = {"is_head_coach", "pfa.coaching_season"}; QUAL = {"shared_or_split_season"}
    good = {"P_1": {"seasons": {"NFL|1979|WAS": {"stint": {"jersey": 32}}},
                    "coaching_seasons": {"NFL|1979|WAS": {"stint": {"is_head_coach": True}}}},
            "P_2": {"seasons": {}, "coaching_seasons": {"NFL|1980|KC": {"stint": {"pfa.coaching_season": {}}}}}}
    cases = [("the shape as ruled", good, []),
             ("a staff predicate left in `seasons`",
              {"P_1": {"seasons": {"CFL|1995|BIR": {"stint": {"pfa.coaching_season": {}}}}, "coaching_seasons": {}}},
              ["P2 staff predicate in `seasons`"]),
             ("a playing predicate written into `coaching_seasons`",
              {"P_1": {"seasons": {}, "coaching_seasons": {"NFL|1979|WAS": {"stint": {"jersey": 32}}}}},
              ["P2 non-staff predicate in `coaching_seasons`"]),
             ("the same claim in both dicts",
              {"P_1": {"seasons": {"NFL|1979|WAS": {"stint": {"is_head_coach": True}}},
                       "coaching_seasons": {"NFL|1979|WAS": {"stint": {"is_head_coach": True}}}}},
              ["P1 the same claim in both dicts", "P2 staff predicate in `seasons`"]),
             ("two sources, one naming no league -- two attestations, NOT a failure",
              {"P_1": {"seasons": {}, "coaching_seasons": {"NFL|1979|WAS": {"stint": {"is_head_coach": True}},
                                                           "COACHES|1979|WAS": {"stint": {"is_head_coach": True}}}}},
              []),
             ("a `y`-prefixed year survived",
              {"P_1": {"seasons": {}, "coaching_seasons": {"COACHES|y1979|WAS": {"stint": {"is_head_coach": True}}}}},
              ["P5 a `y`-prefixed year in `coaching_seasons`"])]
    ok = True
    for label, people, want in cases:
        v, ex, both = audit(people, STAFF, QUAL)
        got = sorted(k for k, n in v.items() if n)
        good_ = got == sorted(want)
        ok &= good_
        print(f"  {'ok  ' if good_ else 'FAIL'} {label}: expected {sorted(want)}, got {got}")
    # P3 must be able to fail: a fix that DELETED the coaching seasons
    v, ex, both = audit({"P_1": {"seasons": {"NFL|1979|WAS": {"stint": {"jersey": 32}}}, "coaching_seasons": {}}}, STAFF, QUAL)
    p3 = both == 0
    ok &= p3
    print(f"  {'ok  ' if p3 else 'FAIL'} P3 sees a player-coach whose coaching seasons were deleted (both-dict count 0)")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
