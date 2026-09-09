"""Gate: a man promoted from a team photograph, and the predicate that must not move.

Ryan's ruling of 2026-09-08 lets a team-photograph caption make a man a person.
It is a NARROW ruling and its edges are the whole of it, so they are checked as
properties. No person, club or year is named here; the instances change every time
a document is read and the shape does not.

  T1  Every team-photograph promotion sits on a club-season the archive HOLDS.
      Without this the ruling would mint people onto club-seasons that do not exist.

  T2  Every team-photograph promotion carries the club the CAPTION PRINTED. A name
      in a photograph of something else is not covered, and the printed club name is
      what distinguishes a team picture from any other photograph.

  T3  THE PREDICATE DOES NOT MOVE. No claim about a man promoted this way may be a
      roster_membership claim. He became a person; the claim still says only that he
      was photographed with the club. This is the property most likely to erode, and
      it erodes silently -- a later ingest writing him onto a roster would look like
      ordinary coverage.

  T4  Evidence kinds still refused stay refused: no promotion may cite a transaction,
      a training-camp list or a boxscore lineup. The ruling widened one kind, not the
      route.

  python3 src/gate_team_photograph_promotions.py              exit 1 = FAIL
  python3 src/gate_team_photograph_promotions.py --self-test  proves it can fail
"""
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO

PROM = os.path.join(BASE, "build", "player-promotions.json")
PHOTO = "team_photograph"
STILL_REFUSED = {"transaction", "training_camp", "boxscore_lineup"}
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok:
        FAILS.append(msg)


def held_club_seasons():
    IDX = IO.load_index(); IDX.pop("_clubs", None)
    held = collections.Counter()
    for p in IDX.values():
        if isinstance(p, dict):
            for k in (p.get("seasons") or {}):
                held[k] += 1
    return held, IDX


def photo_leads():
    """Every team-photograph lead any store still holds, by normalised-ish name."""
    out = []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for L in (d.get("leads") or []):
            if isinstance(L, dict) and L.get("evidence_kind") == PHOTO:
                out.append((os.path.basename(f)[:-5], L))
    return out


def main(extra=()):
    held, IDX = held_club_seasons()
    proms = (json.load(open(PROM))["promotions"] if os.path.exists(PROM) else []) + list(extra)
    # A promotion records its reason in `why`, and the team-photograph reason is the only
    # one that names a team photograph -- so the class identifies itself without a scope
    # key listing which stores or club-seasons are in it.
    photo = [p for p in proms if "team photograph" in str(p.get("why", "")).lower()]
    print(f"promotions: {len(proms)}   from a team photograph: {len(photo)}")
    if not proms:
        print("REFUSED: no promotion decisions to check. An empty denominator is not a pass.")
        sys.exit(2)

    # T1 / T2
    bad_cs = [p["person_id"] for p in photo
              if not held.get((p.get("playing_seasons") or [{}])[0].get("_club_season")
                              or _key(p))]
    bad_club = [p["person_id"] for p in photo
                if not str((p.get("identified_by") or {}).get("club_as_printed") or "").strip()]
    check(not bad_cs, f"T1 every team-photograph promotion is on a club-season the archive holds ({len(bad_cs)}: {bad_cs[:4]})")
    check(not bad_club, f"T2 every team-photograph promotion carries the club the caption printed ({len(bad_club)}: {bad_club[:4]})")

    # T3 -- the predicate does not move
    ids = {p["person_id"] for p in photo}
    offending = []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in (d.get("claims") or []):
            if not isinstance(c, dict): continue
            s = c.get("subject")
            who = s[1] if isinstance(s, list) and len(s) > 1 else None
            if who in ids and str(c.get("predicate", "")).startswith("roster_membership"):
                offending.append(f"{os.path.basename(f)}: {who} {c['predicate']}")
    check(not offending, f"T3 no team-photograph person carries a roster_membership claim ({len(offending)}: {offending[:3]})")

    # T4 -- what stays refused
    still = [p["person_id"] for p in proms
             if any(k in str(p.get("why", "")).lower() for k in ("transaction", "training camp", "camp list", "boxscore"))]
    check(not still, f"T4 no promotion cites an evidence kind that is still refused ({len(still)}: {still[:4]})")

    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


def _key(p):
    s = (p.get("playing_seasons") or [{}])[0]
    if s.get("league") and s.get("year") and s.get("club"):
        return f"{s['league']}|{s['year']}|{s['club']}"
    return None


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # PROVE IT CAN FAIL: three fabricated promotions, never written anywhere -- one on
        # a club-season nothing holds, one with no printed club, one citing a transaction.
        fake = [{"person_id": "P_SELFTEST_A", "why": "named in the caption to a team photograph of 'X' on NOPE|1400|NONE",
                 "playing_seasons": [{"league": "NOPE", "year": 1400, "club": "NONE"}],
                 "identified_by": {"club_as_printed": "X"}},
                {"person_id": "P_SELFTEST_B", "why": "named in the caption to a team photograph",
                 "playing_seasons": [{"league": "NOPE", "year": 1400, "club": "NONE"}],
                 "identified_by": {"club_as_printed": ""}},
                {"person_id": "P_SELFTEST_C", "why": "promoted from a transaction"}]
        main(extra=fake)
        ok = len(FAILS) >= 3
        print("self-test:", "the gate fails when it should" if ok else
              "SELF-TEST DID NOT FAIL -- the gate cannot fail and proves nothing")
        sys.exit(0 if ok else 1)
    sys.exit(main())
