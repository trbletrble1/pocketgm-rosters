"""Gate: the PFA statistics join must not place a man where nothing else does.

Two properties, both derived from declarations/pfa-stats-join.json. Neither
names a person, a club or a year -- an instance list would go stale the moment
the ingest is re-run, and the shape is what recurs.

  P1  A claim joined under tier 2 ("exact name, unique in the archive") must
      fall within the career span the archive holds for that man from stores
      OTHER than this ingest, widened by the declared band. Tier 2 is the only
      tier not held to the club-season, so it is the only one that can put a
      man in a season he has no other business in. Ungated it produced 283
      impossible placements across 141 men -- a 1978-born Andy King with 1920
      Akron Pros figures.

  P2  A claim labelled "on that club-season" must be corroborated: some store
      that is NOT this ingest must place that person on that club-season. This
      is the self-read property. Run one joined six men to Buffalo 1920 under
      tier 2; run two read its own claims back and relabelled all six as tier 1,
      so the label asserted a check made against this file's previous output.
      P2 fails on any recurrence, in any store, whatever the cause.

P2 is the general one. A label that says a check was made is worth nothing if
the thing checked was the checker's own output, and that has now happened three
times in this archive under three different names.

  python3 src/gate_stats_join.py            exit 1 = FAIL
  python3 src/gate_stats_join.py --self-test   proves it can fail
"""
import os, sys, json, glob, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

STORES = os.path.join(BASE, "build", "pfa-stats-*.json")
DECL = os.path.join(BASE, "declarations", "pfa-stats-join.json")
TIER1 = "exact name, on that club-season"
TIER2 = "exact name, unique in the archive"


def declared_span():
    return json.load(open(DECL))["tier_2_span_guard"]["years"]


def base_state(conn):
    """The archive WITHOUT this ingest. Both properties are decided against it, and
    the exclusion is the whole point of the gate -- read the model with pfa-stats
    included and the gate agrees with the defect it exists to catch."""
    span, placed = {}, set()
    for p, mn, mx in conn.execute(
            "select person, min(year), max(year) from claim where scope='stint' "
            "and store not like 'pfa-stats-%' and person is not null and year is not null "
            "group by person"):
        span[p] = (mn, mx)
    for p, y, cid in conn.execute(
            "select distinct person, year, club_id from claim where scope='stint' "
            "and store not like 'pfa-stats-%' and person is not null and club_id is not null"):
        placed.add((p, y, cid))
    return span, placed


def check(span, placed, band, extra_claims=()):
    p1, p2 = collections.Counter(), collections.Counter()
    seen = set()
    files = sorted(glob.glob(STORES))
    if not files and not extra_claims:
        # An empty denominator is not a pass. This gate has no opinion about an
        # archive whose stores are not built, and says so instead of going green.
        print("REFUSED: no build/pfa-stats-*.json to check. Build them, then run this.")
        sys.exit(2)
    def one(cl):
        s = cl.get("subject") or []
        cs = cl.get("_club_season") or {}
        if len(s) < 2 or not cs:
            return
        key = (s[1], cs.get("year"), cs.get("club_id"), cl.get("_join"))
        if key in seen:
            return
        seen.add(key)
        person, year, cid, how = key
        if how == TIER2:
            sp = span.get(person)
            if not sp or not (sp[0] - band <= year <= sp[1] + band):
                p1[(person, year, cid)] += 1
        elif how == TIER1:
            if (person, year, cid) not in placed:
                p2[(person, year, cid)] += 1
    for f in files:
        for cl in (json.load(open(f)).get("claims") or []):
            one(cl)
    for cl in extra_claims:
        one(cl)
    return p1, p2, len(seen)


def report(p1, p2, n, band):
    print(f"checked {n:,} distinct (person, season, club, tier) placements, band +/-{band}")
    print(f"  P1  tier-2 placements outside the man's held career span : {len(p1)}")
    print(f"  P2  'on that club-season' that no other store corroborates: {len(p2)}")
    for label, d in (("P1", p1), ("P2", p2)):
        for k in list(d)[:8]:
            print(f"      {label} {k[0]} {k[2]} {k[1]}")
    return len(p1) + len(p2)


def main():
    conn = sqlite3.connect(paths.READ_MODEL)
    span, placed = base_state(conn)
    band = declared_span()

    if "--self-test" in sys.argv:
        # PROVE IT CAN FAIL. Two fabricated claims, never written to any store: one
        # tier-2 placement far outside every possible span, and one tier-1 placement
        # for a person the base state does not put on that club-season.
        fake = [{"subject": ["stint", "P_SELFTEST", "XXX", "NFL-1400"],
                 "_join": TIER2, "_club_season": {"year": 1400, "club_id": "club-nowhere"}},
                {"subject": ["stint", "P_SELFTEST", "XXX", "NFL-1400"],
                 "_join": TIER1, "_club_season": {"year": 1400, "club_id": "club-nowhere"}}]
        a, b, n = check(span, placed, band, extra_claims=fake)
        ok = len(a) >= 1 and len(b) >= 1
        print(f"self-test: P1 {len(a)} P2 {len(b)} -- " + ("the gate fails when it should"
              if ok else "SELF-TEST DID NOT FAIL: the gate cannot fail and proves nothing"))
        sys.exit(0 if ok else 1)

    p1, p2, n = check(span, placed, band)
    bad = report(p1, p2, n, band)
    print("PASS" if not bad else "FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
