"""Measurement, not a gate: ages a held birth date gives a man for the seasons he holds.

Read-only; writes nothing. Moved into src/ on 2026-09-11 from a session scratchpad
(measure3.py, 8-9 September), because the scratchpad copy had aged: it named the coaching
STORES it knew, the pfa-coaches and coach-seasons-promoted stores came later, and run as
written it counted ~60,000 coaching seasons as playing and reported 974 men "too old".

A COACHING SEASON IS KNOWN BY ITS PREDICATE, not its store: declarations/coaching-seasons.json
`staff_predicates` (Ryan, 2026-09-09). A stint claim carrying one of them is a coaching
season; every other stint claim is a playing season. A player-coach keeps both.

THE BANDS ARE NOT RULED. 16-45 playing and 20-85 coaching are this measurement's
assumptions, printed with every result. Nothing here says an age is impossible; it says
which held readings fall outside a stated band. Whether the archive should hold such a
rule is a question for Ryan, not something this file decides.

Two definitions, both printed:
  A  any held birth date puts some season outside the band
  B  NO held birth date puts any of his seasons inside it   (the stricter; the "15")

    python3 src/measure_impossible_ages.py
"""
import os, sys, json, re, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, dates

PLAY, COACH = (16, 45), (20, 85)


def lit(v):
    v = str(v)
    if v.startswith('"') and v.endswith('"'):
        try: return json.loads(v)
        except Exception: return v.strip('"')
    return v


def main():
    sp = json.load(open(os.path.join(BASE, "declarations", "coaching-seasons.json")))["staff_predicates"]
    staff = set(sp["predicates"])
    # A QUALIFIER TRAVELS WITH THE SEASON IT QUALIFIES (the declaration's own words). The first
    # version of this file sorted claim by claim, so `shared_or_split_season` -- on Greasy
    # Neale's 1943 Phil-Pitt season -- counted as a PLAYING season and made him 52 and "too old".
    # A season is sorted as a whole: coaching if any claim on it carries a staff predicate,
    # playing if any carries a predicate that is neither staff nor a qualifier. A player-coach
    # is both, as the index holds him.
    qualifiers = {k for k in sp.get("not_staff_though_it_appears_in_those_stores", {}) if not k.startswith("_")}
    c = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    birth = collections.defaultdict(set)
    for p, val, sid in c.execute("SELECT person, value, source_id FROM claim WHERE family='birth_date' AND person IS NOT NULL"):
        r = dates.read(lit(val), source_id=sid)
        if r and r["year"] and r["year"] >= 1800: birth[p].add((r["year"], lit(val), sid))
    on_key = collections.defaultdict(set)                  # (person, season key, store) -> predicates
    for p, subj, pred, st in c.execute("SELECT person, subject, predicate, store FROM claim WHERE scope='stint' AND person IS NOT NULL"):
        try: s = json.loads(subj)
        except Exception: continue
        key = s[3] if len(s) > 3 else None
        if isinstance(key, str) and re.search(r"\d{4}", key): on_key[(p, key, st)].add(pred)
    seasons = {"playing": collections.defaultdict(set), "coaching": collections.defaultdict(set)}
    for (p, key, st), preds in on_key.items():
        yr = int(re.search(r"(\d{4})", key).group(1))
        if preds & staff: seasons["coaching"][p].add((yr, st))
        if preds - staff - qualifiers: seasons["playing"][p].add((yr, st))
    print(f"coaching predicates, from the declaration: {sorted(staff)}; qualifiers: {sorted(qualifiers)}\n")
    for kind, (lo, hi) in (("playing", PLAY), ("coaching", COACH)):
        A = {"too young": set(), "too old": set()}; B = {"too young": [], "too old": []}
        for p, bs in birth.items():
            ss = seasons[kind].get(p)
            if not ss: continue
            ages = [yr - by for by, _, _ in bs for yr, _ in ss]
            if min(ages) < lo: A["too young"].add(p)
            if max(ages) > hi: A["too old"].add(p)
            if not any(lo <= a <= hi for a in ages):
                B["too young" if min(ages) < lo else "too old"].append(p)
        print(f"{kind.upper()} seasons, band {lo}-{hi} (not ruled)")
        for k in ("too young", "too old"):
            print(f"   {k:9s}  A {len(A[k]):5d}   B {len(B[k]):4d}")
            for p in sorted(B[k])[:25]:
                nm = c.execute("SELECT name FROM person_name WHERE person=? LIMIT 1", (p,)).fetchone()
                print(f"        B  {p} {nm[0] if nm else '-':26s} born {sorted(birth[p])} seasons "
                      f"{sorted({y for y, _ in seasons[kind][p]})[:6]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
