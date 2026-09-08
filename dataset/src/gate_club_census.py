"""A league-year with the wrong number of clubs is a DETECTABLE CONDITION.

WHY THIS EXISTS. The Las Vegas Raiders' 2020 season was never fetched. Nothing
objected: StatsCrew's own build/nfl-2020.json holds 31 clubs, the index holds 31,
and the two agreed with each other perfectly. A store compared against itself
cannot see a season neither of them has. It surfaced only because a downstream
club table happened to notice LVR|2020 carried a name and no men.

So this does not compare the archive with its own sources. It compares the CLUB
COUNT PER LEAGUE-YEAR against an INDEPENDENT one, and a disagreement is a
club-season somebody is missing.

TWO THINGS IT FOUND ON FIRST RUN, out of 105 comparable years:

  2020  archive 31, nflverse 32   -- Las Vegas Raiders, never fetched.
  1934  archive 10, nflverse 11   -- Cincinnati Reds. Not a fetch gap: the Reds
        went 0-8, folded, and the St. Louis Gunners bought the franchise for the
        last three games. StatsCrew collapsed BOTH into one code, so 26 of the 27
        Reds are recorded in the archive as Gunners and SLG carries 55 men for a
        three-game club. A source defect, not an absence.

WHY NOT THE OBVIOUS CHECKS. Comparing club codes rather than counts is useless --
nflverse writes BOS/BRK/CHB/NY/STL where the archive writes BO3/BRO/CHI/NYG/SLG,
and normalising those is the club table's job, not this one's. Testing for a
club-map entry with no men finds LVR|2020 but never finds 1934: there is no
CIN|1934 entry to be empty. And a bare structural dip (fewer clubs than both
neighbours) fires on 1924, 1928, 1932 and 1943, all four of which are real
history -- Canton suspended, Buffalo sat out, the Depression, the war -- and
nflverse independently confirms 18, 10, 8 and 8.

ITS BLIND SPOT, STATED. nflverse covers the NFL lineage only: APFA, NFL, AAFC and
the 1960s AFL, 1920-2026. The CFL, WFL, both USFLs, XFL, UFL, AAF and Arena have
NO independent club-count source in the archive, so C1 cannot test them and does
not pretend to. C2 reports the structural dip for those leagues as a lead for a
human, never as a failure.

  python3 src/gate_club_census.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")

LINEAGE = ("APFA", "NFL", "AAFC", "AFL")        # what nflverse covers
NOT_LEAGUES = ("COACHES", "SALARIES")
# Disagreements a human has ruled on. Anything NOT here fails.
KNOWN = {
    1934: "Cincinnati Reds. RULED: their own club-season. build/nfl-1934-cincinnati.json "
          "creates NFL|1934|CIN from the boxscore lineups -- 12 held men and 8 leads across "
          "their eight games, four of whom also appear for the Gunners. This entry stays "
          "until the next successful rebuild reads that store; after it, 1934 should show "
          "11 clubs and this line should be DELETED. If it is still here and C1 still "
          "counts 10, the rebuild has not happened.",
    2020: "Las Vegas Raiders. RULED: filled from nflverse, because StatsCrew's page is "
          "blank -- empty <tbody> and a note asking for contributions -- and a hole in one "
          "source is not a fact. build/nfl-2020-lvr.json holds 86 men. PFR was preferred "
          "and is NOT on disk: the saved pages are 1979 rosters and per-year draft "
          "listings. THE DEFINITION DIFFERS: nflverse counts everyone who appeared on a "
          "roster at any point, so 86 against a peer median of 70 (range 61-84) for the "
          "other 31 clubs, which all come from StatsCrew. This entry stays until the next "
          "successful rebuild; after it, 2020 should show 32 clubs and this line should be "
          "DELETED. The club's own 2020 media guide is on disk and outranks nflverse -- "
          "the upgrade path, not done here.",
}


def archive_by_year(idx):
    per = collections.defaultdict(lambda: collections.defaultdict(set))
    for pid, v in idx.items():
        if pid == "_clubs" or not isinstance(v, dict):
            continue
        for k in (v.get("seasons") or {}):
            lg, y, club = k.split("|", 2)
            if lg in NOT_LEAGUES:
                continue
            yr = y[1:5] if y.startswith("y") else y
            if yr.isdigit():
                per[lg][int(yr)].add(club)
    return per


def nflverse_by_year(nv):
    per = collections.defaultdict(set)
    for c in nv["claims"]:
        if c["predicate"] != "nflverse.roster_membership":
            continue
        y, t = str(c["value"]).split("|", 1)
        per[int(y)].add(t)
    return per


def c1_counts_agree_with_an_independent_source(per, nvy):
    """COUNTS, never code sets. The two sources name clubs differently on purpose."""
    lineage = collections.defaultdict(set)
    for lg in LINEAGE:
        for y, cs in per.get(lg, {}).items():
            lineage[y] |= cs
    compared, bad = 0, []
    for y in sorted(nvy):
        if y not in lineage:
            continue
        compared += 1
        a, b = len(lineage[y]), len(nvy[y])
        if a != b and y not in KNOWN:
            bad.append(f"{y}: archive {a} clubs, nflverse {b} -- a club-season nobody has "
                       f"noticed is missing")
    return compared, bad


def c2_structural_dips(per):
    """A league-year with fewer clubs than BOTH neighbours. A LEAD, not a failure --
    four of the five it finds are real history. It is the only signal available for
    the eight leagues nflverse does not cover."""
    out = []
    for lg in sorted(per):
        ys = sorted(per[lg])
        for i in range(1, len(ys) - 1):
            pv, y, nx = ys[i - 1], ys[i], ys[i + 1]
            if y - pv > 1 or nx - y > 1:
                continue
            a, b, c = len(per[lg][pv]), len(per[lg][y]), len(per[lg][nx])
            if b < a and b < c:
                gone = sorted((per[lg][pv] & per[lg][nx]) - per[lg][y])
                out.append((lg, y, a, b, c, gone,
                            lg in LINEAGE and "checked by C1" or "NO INDEPENDENT SOURCE"))
    return out


def load():
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    nv = json.load(open(os.path.join(BASE, "build", "nflverse-rosters.json")))
    return idx, nv


def run(idx, nv):
    per = archive_by_year(idx); nvy = nflverse_by_year(nv)
    compared, bad = c1_counts_agree_with_an_independent_source(per, nvy)
    print(f"  C1 {'FAIL' if bad else 'pass'}  club counts agree with nflverse "
          f"across {compared} comparable years ({len(KNOWN)} disagreements ruled on)")
    for b in bad:
        print(f"        {b}")
    for y, why in sorted(KNOWN.items()):
        print(f"        known, held: {y} -- {why[:96]}...")
    dips = c2_structural_dips(per)
    unchecked = [d for d in dips if d[6] != "checked by C1"]
    print(f"  C2 lead  {len(dips)} structural dip(s); {len(unchecked)} in leagues with no "
          f"independent source")
    for lg, y, a, b, c, gone, note in dips:
        print(f"        {lg} {y}: {a} -> {b} -> {c}   missing either side: {gone or '(different clubs)'}   [{note}]")
    return bad


def selftest():
    idx, nv = load()
    per = archive_by_year(idx); nvy = nflverse_by_year(nv)
    base = c1_counts_agree_with_an_independent_source(per, nvy)[1]
    print("SELFTEST"); print(f"baseline C1 failures: {base or 'none'}\n")
    ok = []
    # C1 must fire when a club-season goes missing from a year nobody has ruled on.
    p2 = {lg: {y: set(v) for y, v in d.items()} for lg, d in per.items()}
    victim = sorted(p2["NFL"][1995])[0]
    p2["NFL"][1995].discard(victim)
    fired = c1_counts_agree_with_an_independent_source(p2, nvy)[1]
    good = len(fired) == len(base) + 1 and any("1995" in f for f in fired)
    print(f"  {'OK  ' if good else 'BAD '} C1: removed {victim} from NFL 1995 -> "
          f"{[f[:40] for f in fired if '1995' in f] or 'NOTHING FIRED'}")
    ok.append(good)
    # and must NOT fire for a year already ruled on
    p3 = {lg: {y: set(v) for y, v in d.items()} for lg, d in per.items()}
    p3["NFL"][2020].discard(sorted(p3["NFL"][2020])[0])
    fired3 = c1_counts_agree_with_an_independent_source(p3, nvy)[1]
    good3 = fired3 == base
    print(f"  {'OK  ' if good3 else 'BAD '} C1: a ruled-on year stays silent -> "
          f"{fired3 or 'silent'}")
    ok.append(good3)
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    idx, nv = load()
    bad = run(idx, nv)
    sys.exit(1 if bad else 0)
