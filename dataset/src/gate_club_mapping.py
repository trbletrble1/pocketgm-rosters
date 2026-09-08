"""An unmappable club string must be COUNTED AND REPORTED, never skipped.

club_keys.resolve() has always refused strings it could not map. What it never
did was tell anyone. Every caller writes `if not code: continue`, so a club that
mapped to nothing produced no error, no count and no line -- it simply had no
men, and nothing anywhere said why. The 1926 AFL sat outside the archive for
that reason alone, and the only way anybody noticed was going looking.

These checks do not require the census to be EMPTY. Ryan's instruction was not
to map every string in advance; it was to make sure that when one does not map,
somebody finds out. So they test loudness, not silence:

  C1 the census sees every refusal there is
  C2 it prints all of them, never a top-N
  C3 it is DERIVED -- a club string invented right now shows up in it
  C4 the dashboard actually calls it, so it is heard without being asked for

  python3 src/gate_club_mapping.py [--selftest]
"""
import os, re, sys, json, copy, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import club_keys
from club_keys import ClubKeys


def load():
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    clubs = idx.pop("_clubs", {})
    return idx, clubs


def recount(idx, clubs):
    """Refusals counted INDEPENDENTLY of census(), by walking the keys directly.
    Two routes to one number: if they disagree, census() is not seeing everything."""
    CK = ClubKeys(dict(idx), clubs); n = 0
    for pid, p in idx.items():
        if not isinstance(p, dict): continue
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2)
            yr = y[1:5] if y.startswith("y") else y
            if not yr.isdigit(): n += 1; continue
            if CK.is_code(club, yr): continue
            if CK.resolve(club, yr)[0] is None: n += 1
    return n


def checks(idx, clubs):
    out = []
    CK = ClubKeys(dict(idx), clubs)
    rows = CK.census(idx)
    seen, want = sum(r[4] for r in rows), recount(idx, clubs)
    out.append(("C1", "the census counts every refusal there is",
                [] if seen == want else
                [f"census reports {seen} person-seasons, an independent walk finds {want}"]))

    lines = []
    club_keys.report(dict(idx), clubs, log=lines.append)
    body = [l for l in lines if l.strip().startswith(tuple("0123456789"))]
    out.append(("C2", "every refused string is printed, never a top-N",
                [] if len(body) == len(rows) else
                [f"{len(rows)} refused strings but {len(body)} printed -- "
                 f"a truncated report is another way of dropping things"]))

    probe = dict(idx)
    victim = next(k for k, p in probe.items() if isinstance(p, dict) and p.get("seasons"))
    probe[victim] = copy.deepcopy(probe[victim])
    probe[victim]["seasons"]["NFL|1931|Zzz Invented Club"] = {}
    after = ClubKeys(dict(probe), clubs).census(probe)
    out.append(("C3", "the census is derived from the data, not a fixed list",
                [] if any(r[2] == "Zzz Invented Club" for r in after) else
                ["a club string invented just now did not appear -- census() is "
                 "reporting a static list and would miss the next merged club"]))

    src = open(os.path.join(HERE, "build_dashboard.py")).read()
    out.append(("C4", "build_dashboard calls the reporter, so it is heard unasked",
                [] if re.search(r"club_keys\.report\(", src) else
                ["build_dashboard.py never calls club_keys.report -- the census "
                 "exists but nothing surfaces it"]))
    return out


def run(idx, clubs):
    res = checks(idx, clubs)
    for cid, desc, bad in res:
        print(f"  {cid} {'FAIL' if bad else 'pass'}  {desc}")
        for b in bad: print(f"        {b}")
    return res


def selftest():
    idx, clubs = load()
    base = {c for c, _, bad in checks(idx, clubs) if bad}
    print("SELFTEST -- each check must fail for its own reason and no other")
    print(f"baseline: {sorted(base) or 'all passing'}\n")
    ok = []

    # C1: blind the census to one refusal reason. It must notice it is under-counting.
    real = ClubKeys.census
    def blind(self, index):
        return [r for r in real(self, index) if r[3] != "ambiguous_city"]
    ClubKeys.census = blind
    fired = {c for c, _, bad in checks(idx, clubs) if bad} - base
    print(f"  {'OK  ' if fired == {'C1'} else 'BAD '} C1: census blinded -> {sorted(fired)}")
    ok.append(fired == {"C1"})
    ClubKeys.census = real

    # C2: truncate the report to a top-10 -- the classic quiet drop.
    realr = club_keys.report
    def trunc(index=None, clubs=None, log=print):
        rows = ClubKeys(dict(index), clubs).census(index)
        log(f"  UNMAPPABLE CLUB STRINGS: {sum(r[4] for r in rows):,}")
        for lg, yr, c, why, n, ex in rows[:10]:
            log(f"     {n:6,}  {lg}|{yr}|{c}   [{why}]  e.g. {ex}")
        return rows
    club_keys.report = trunc
    fired = {c for c, _, bad in checks(idx, clubs) if bad} - base
    print(f"  {'OK  ' if fired == {'C2'} else 'BAD '} C2: report truncated -> {sorted(fired)}")
    ok.append(fired == {"C2"})
    club_keys.report = realr

    # C3: freeze the census to today's answer. It still passes C1 and C2 and is
    # useless -- it can no longer see a club string that did not exist yet.
    frozen = real(ClubKeys(dict(idx), clubs), idx)
    ClubKeys.census = lambda self, index: frozen
    fired = {c for c, _, bad in checks(idx, clubs) if bad} - base
    print(f"  {'OK  ' if fired == {'C3'} else 'BAD '} C3: census frozen -> {sorted(fired)}")
    ok.append(fired == {"C3"})
    ClubKeys.census = real

    # C4: the wiring removed.
    p = os.path.join(HERE, "build_dashboard.py"); src = open(p).read()
    try:
        open(p, "w").write(src.replace("club_keys.report(", "club_keys.NOTCALLED("))
        fired = {c for c, _, bad in checks(idx, clubs) if bad} - base
    finally:
        open(p, "w").write(src)
    print(f"  {'OK  ' if fired == {'C4'} else 'BAD '} C4: dashboard call removed -> {sorted(fired)}")
    ok.append(fired == {"C4"})

    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    idx, clubs = load()
    res = run(idx, clubs)
    nf = sum(1 for _, _, b in res if b)
    print(f"\n{len(res)-nf} pass, {nf} FAIL")
    sys.exit(1 if nf else 0)
