"""Ryan's ruling, made enforceable: A MERGED CLUB IS ITS OWN CLUB.

Since patch 2 of the club job (2026-09-06) the mergers are not written here: they
are rulings by NAME in declarations/clubs.json, built into build/clubs.json, and
this gate reads them from the table (merged_from_table). gate_merged_table.py
proves the derivation reproduces the rulings.

Card-Pitt, Phil-Pitt and the 1945 Boston Yanks each existed, played a season and
have a record. They are not composites of their parent clubs and must not be
resolved into either, in either direction:

  a man who played for Card-Pitt played for CARD-PITT, not for the Cardinals
  and not for the Steelers;

  and no parent code may stand in for the merged club, which is the same error
  wearing the other hat.

M4 is the one that earns its keep. CLUBS['PIT|1943'] exists and carries the
MERGED club's name while holding zero men. Nobody is harmed by it today, but
club_keys.is_code('PIT','1943') returns True because of it, so a season key
written NFL|1943|PIT would be judged 'already a code' and never normalised to
PNP -- a phantom club-season that is neither the merger nor a real Pittsburgh.
The trap is latent, not sprung. A gate is what keeps it that way.

  python3 src/gate_merged_clubs.py [--selftest]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")

# The merger, its own code, and the codes that must NOT carry a season that year,
# READ FROM THE CLUB TABLE. The rulings live in declarations/clubs.json by name;
# build_clubs.py finds the codes; this gate holds no club string of its own.
# BO4 is its own parent: Boston continued under its own code and Brooklyn folded
# into it, so BRO is the code that must fall silent, not BO4.
def merged_from_table():
    from clubs import Clubs, TABLE
    if not os.path.exists(TABLE): raise SystemExit("gate_merged_clubs: build/clubs.json is missing; run src/build_clubs.py --write")
    C = Clubs(); out = {}
    for c in C.T["clubs"]:
        L = c["lineage"]
        cases = ([(y, L["merger_of"]) for y in [c["first"]] if L["merger_of"]]
                 + [(int(y), v["absorbed"]) for y, v in L["merger_seasons"].items()])
        for y, parents in cases:
            code = C.code_for(c["id"], y); lg = C.league_for(c["id"], y)
            silent = sorted(C.code_for(p, y - 1) or C.code_for(p, y - 2) for p in parents)
            strings = sorted({s["string"] for s in c["strings"] if s["source"] == "boxscore" and s["kind"] != "code" and s.get("role") != "code" and s["first"] <= y <= s["last"]})
            out[(lg, str(y), code)] = {"name": C.name_for(c["id"], y), "must_be_silent": silent, "boxscore_strings": strings}
    if not out: raise SystemExit("gate_merged_clubs: the club table holds no merger; the rulings in declarations/clubs.json did not build")
    return out

MERGED = merged_from_table()


def load(idx_path=None, box_path=None):
    idx = json.load(open(idx_path or os.path.join(BASE, "build-reports", "person-index.json")))
    clubs = idx.pop("_clubs", {})
    box = json.load(open(box_path or os.path.join(BASE, "build", "pfa-boxscores.json")))
    return idx, clubs, box


def rosters(idx):
    """league|year|code -> set of person ids."""
    r = collections.defaultdict(set)
    for pid, p in idx.items():
        if not isinstance(p, dict): continue
        for k in (p.get("seasons") or {}):
            r[k].add(pid)
    return r


def checks(idx, clubs, box):
    R = rosters(idx)
    out = []

    # M1  the merged club exists as ITSELF: its own code, its own name, its own men.
    bad = []
    for (lg, yr, code), m in MERGED.items():
        nm = clubs.get(f"{code}|{yr}")
        men = R.get(f"{lg}|{yr}|{code}", set())
        if nm != m["name"] or not men:
            bad.append(f"{lg}|{yr}|{code}: club-map name {nm!r} (want {m['name']!r}), {len(men)} men")
    out.append(("M1", "each merged club is its own club-season with its own name and men", bad))

    # M2  nobody holds the merged season TWICE. The real duplication mode in this
    # store is not a parent code (M3 owns that) -- it is one source writing the club
    # as a CODE and another writing it as a NAME. NFL|1943|PNP and
    # NFL|1943|Philadelphia Eagles/Pittsburgh Steelers are one season wearing two
    # keys, and merge_people.py exists because of exactly this.
    bad = []
    for (lg, yr, code), m in MERGED.items():
        denote = {code, m["name"]}
        for pid, p in idx.items():
            if not isinstance(p, dict): continue
            held = [k for k in (p.get("seasons") or {})
                    if k.split("|", 2)[:2] == [lg, yr] and k.split("|", 2)[2] in denote]
            if len(held) > 1:
                bad.append(f"{pid} holds {len(held)} keys for one club-season: {held}")
    out.append(("M2", "no man holds the merged season twice under two keys", bad))

    # M3  the clubs that merged played no season of their own that year.
    bad = []
    for (lg, yr, code), m in MERGED.items():
        for c in m["must_be_silent"]:
            n = len(R.get(f"{lg}|{yr}|{c}", set()))
            if n: bad.append(f"{lg}|{yr}|{c} holds {n} men, but that club did not play in {yr}")
    out.append(("M3", "a club that merged has no separate season that year", bad))

    # M4  no OTHER code carries the merged club's name -- the latent phantom.
    bad = []
    for (lg, yr, code), m in MERGED.items():
        for k, v in clubs.items():
            c, y = k.split("|", 1)
            if y == yr and c != code and v == m["name"]:
                bad.append(f"club-map {k} carries the merged name {v!r}; only {code} may. "
                           f"is_code({c!r},{yr!r}) is now True, so {lg}|{yr}|{c} would never "
                           f"normalise to {code}")
    out.append(("M4", "only the merged club's own code carries the merged club's name", bad))

    # M5  boxscore evidence lands on the merged club, never on a parent.
    lin = [x for x in box["claims"] if x["predicate"] == "pfa.game_lineup"]
    bystr = collections.defaultdict(set)
    for x in lin:
        v = x["value"]
        bystr[(str(v["game"][2]), v["club_as_printed"])].add(x["subject"][1])
    bad = []
    for (lg, yr, code), m in MERGED.items():
        seen = set(); printed = []
        for st in m["boxscore_strings"]:
            if bystr.get((yr, st)): seen |= bystr[(yr, st)]; printed.append(st)
        if not seen:
            bad.append(f"no boxscore lineup printed any of {m['boxscore_strings']!r} in {yr}")
            continue
        off = sorted(seen - R.get(f"{lg}|{yr}|{code}", set()))
        if off:
            bad.append(f"{len(off)} men appeared for {printed!r} in {yr} without "
                       f"holding {lg}|{yr}|{code}: {off[:5]}")
    out.append(("M5", "every merged-club appearance belongs to a man holding that merged season", bad))
    return out


def run(idx, clubs, box, label=""):
    res = checks(idx, clubs, box)
    if label: print(label)
    for cid, desc, bad in res:
        print(f"  {cid} {'FAIL' if bad else 'pass'}  {desc}")
        for b in bad[:6]: print(f"        {b}")
        if len(bad) > 6: print(f"        ... and {len(bad)-6} more")
    return res


def selftest():
    """Every check shown FAILING for its own stated reason. A check never seen to
    fail is a check nobody has any reason to trust."""
    import copy
    base_idx, base_clubs, box = load()
    base = {c for c, _, bad in checks(base_idx, base_clubs, box) if bad}
    print("SELFTEST -- each check must fail for its own reason and no other")
    print(f"baseline: already failing on live data -> {sorted(base) or 'nothing'}")
    print("a probe passes if it adds EXACTLY its own check to that baseline\n")
    def probe(name, mutate):
        idx, clubs = copy.deepcopy(base_idx), dict(base_clubs)
        b = copy.deepcopy(box)
        idx, clubs, b = mutate(idx, clubs, b)
        fired = {c for c, _, bad in checks(idx, clubs, b) if bad}
        added = fired - base
        ok = added == {name}
        print(f"  {'OK  ' if ok else 'BAD '} {name}: added {sorted(added) or ['nothing']}"
              f"{'' if ok else '  <- wanted exactly {' + name + '}'}")
        return ok

    # the probes take every string from the derived table, so the selftest holds none of its own
    mergers = sorted((k, v) for k, v in MERGED.items() if len(v["must_be_silent"]) > 1)
    (lg1, y1, c1), m1v = mergers[0]; (lg2, y2, c2), m2v = mergers[-1]
    def m1(i, c, b): c[f"{c1}|{y1}"] = base_clubs[f"{m1v['must_be_silent'][-1]}|{int(y1) - 1}"]; return i, c, b
    def m2(i, c, b):
        pid = next(iter(k for k, p in i.items() if isinstance(p, dict)
                        and f"{lg1}|{y1}|{c1}" in (p.get("seasons") or {})))
        # the NAME form beside the CODE form: one season, two keys
        i[pid]["seasons"][f"{lg1}|{y1}|{m1v['name']}"] = {}
        return i, c, b
    def m3(i, c, b):
        pid = next(iter(k for k, p in i.items() if isinstance(p, dict)
                        and f"{lg2}|{y2}|{c2}" in (p.get("seasons") or {})))
        # a DIFFERENT man, so M2 stays quiet and only M3 speaks
        other = next(k for k, p in i.items() if isinstance(p, dict) and k != pid
                     and f"{lg2}|{y2}|{c2}" not in (p.get("seasons") or {}))
        i[other].setdefault("seasons", {})[f"{lg2}|{y2}|{m2v['must_be_silent'][0]}"] = {}; return i, c, b
    def m4(i, c, b): c[f"{m2v['must_be_silent'][-1]}|{y2}"] = m2v["name"]; return i, c, b

    def probe_m4():
        """M4 is ALREADY failing on live data, so injecting a second violation
        proves nothing -- it was going to fail either way. The proof has to be
        two-sided: clear the known violation and watch M4 fall silent, then put a
        DIFFERENT one back and watch it speak again. A check that cannot be made
        to pass is not a check, it is an assertion."""
        idx, clubs = copy.deepcopy(base_idx), dict(base_clubs)
        live = [k for k, v in clubs.items()
                if any(k != f"{c}|{y}" and k.endswith(f"|{y}") and v == m["name"]
                       for (lg, y, c), m in MERGED.items())]
        for k in live: clubs.pop(k)
        quiet = {c for c, _, bad in checks(idx, clubs, box) if bad}
        a = "M4" not in quiet
        clubs[f"{m2v['must_be_silent'][-1]}|{y2}"] = m2v["name"]
        loud = {c for c, _, bad in checks(idx, clubs, box) if bad}
        b_ = loud - quiet == {"M4"}
        print(f"  {'OK  ' if a and b_ else 'BAD '} M4: cleared {live} -> "
              f"{'silent' if a else 'STILL FAILING'}; re-injected -> "
              f"{'fires alone' if b_ else sorted(loud - quiet)}")
        return a and b_
    (lg5, y5, c5), m5v = sorted(MERGED.items())[0]
    def m5(i, c, b):
        for x in b["claims"]:
            if (x["predicate"] == "pfa.game_lineup"
                    and x["value"]["club_as_printed"] in m5v["boxscore_strings"]
                    and str(x["value"]["game"][2]) == y5):
                x["subject"] = ["person", "P_NOT_A_REAL_MAN"]; break
        return i, c, b

    allok = all([probe("M1", m1), probe("M2", m2), probe("M3", m3),
                 probe_m4(), probe("M5", m5)])
    print(f"\nselftest {'PASSED' if allok else 'FAILED'} -- "
          f"{'every check fails for its own reason' if allok else 'a check is not measuring what it claims'}")
    return allok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    idx, clubs, box = load()
    res = run(idx, clubs, box, "GATE: merged clubs are their own clubs")
    nf = sum(1 for _, _, b in res if b)
    print(f"\n{len(res)-nf} pass, {nf} FAIL")
    sys.exit(1 if nf else 0)
