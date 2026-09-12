"""Gate: a surname joins only where it is unique ON THAT CLUB-SEASON, and a staff role is
not a person. Ryan's rulings of 2026-09-11 (One and Four), checked as properties across every
store -- no document, man or club-season is named here.

  S1  every claim whose `_join_tier` is `surname_unique_on_the_club_season` names a club-season
      on which EXACTLY ONE man of that surname is held, counted from the read model with the
      claim's own store left out (a decider must not find the man it placed). A second man of
      the surname refuses both, so two is a failure, and so is none.
  S2  no source record joins two different printed names to one man by surname.
  S3  EVERY JOINED MAN IS ON THE CLUB-SEASON HIS CLAIM SAYS IT WAS JOINED ON (`_joined_on`), for
      every tier that asserts "on the club-season" -- exact, surname, and a ruled attachment. Found
      2026-09-11: ten PFA facts about Bill Coleman were written onto a Buffalo Smith because the
      ingest carried a person id over from the section before. S1 could not see it -- the tier was
      not the surname tier -- but the claim said where it was joined, and he was not there.
  S4  every man joined on an OPENED club-season by the neighbouring-season rule is on the
      neighbouring season his claim names.
  C1  every `club_staff_role` claim has a CLUB-SEASON subject and names no person.
  C2  no store that writes `club_staff_role` also writes `role_title` -- the bios read
      role_title, and a trainer or a president must never become a coaching season.

The count is independent of the ingest: it does not import the ingest's join and recomputes
the surname from the read model's names with its own short reading.

  python3 src/gate_surname_on_club_season.py              exit 1 = FAIL
  python3 src/gate_surname_on_club_season.py --self-test  proves it can fail
"""
import os, re, sys, json, glob, sqlite3, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from clubs import Clubs

# The PLAYING roster is counted by PREDICATE, read from the declaration -- a man held on a club-season only
# through staff predicates is its staff. Counting by league token let two caption coaches pass as players.
STAFF = sorted(json.load(open(os.path.join(BASE, "declarations", "coaching-seasons.json")))
               ["staff_predicates"]["predicates"])
NOT_STAFF = f"and predicate not in ({','.join('?' * len(STAFF))})"
TIER = "surname_unique_on_the_club_season"
ADJ = "surname_unique_on_the_adjacent_season"     # Ryan, 2026-09-11: the club does the work, not the calendar
FAILS = []


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def sur(s):
    s = str(s or "").replace("“", '"').replace("”", '"')
    s = re.sub(r'"[^"]*"|\[[^\]]*\]|\([^)]*\)', " ", s)
    if "," in s:                       # 'Hendrian, Oscar George' is surname-first
        last, rest = s.split(",", 1); s = f"{rest} {last}"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace("'", "")
    t = [x for x in re.sub(r"[^a-z\s]", " ", s).split() if x not in ("jr", "sr", "ii", "iii")]
    return t[-1] if t else ""


def stores():
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        try: d = json.load(open(f))
        except Exception: continue
        if isinstance(d, dict) and isinstance(d.get("claims"), list):
            yield os.path.basename(f)[:-5], d


def main(extra=()):
    db = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    C = Clubs()
    names = collections.defaultdict(set)
    for p, n in db.execute("select person, name from person_name"): names[p].add(n)
    surname_claims, joined, staff, role_title_stores, staff_stores = [], [], [], set(), set()
    for st, d in list(stores()) + list(extra):
        for c in d["claims"]:
            v = c.get("value") if isinstance(c.get("value"), dict) else (c.get("extra") or {})
            if isinstance(v, dict) and v.get("_join_tier") == TIER:
                surname_claims.append((st, c, v))
            if isinstance(v, dict) and v.get("_join_tier"):
                joined.append((st, c, v))
            if c.get("predicate") == "club_staff_role":
                staff.append((st, c)); staff_stores.add(st)
            if c.get("predicate") == "role_title":
                role_title_stores.add(st)
    print(f"surname-tier claims: {len(surname_claims)}   club_staff_role claims: {len(staff)}")
    if not surname_claims and not staff:
        print("REFUSED: nothing to check. An empty denominator is not a pass."); sys.exit(2)

    bad, by_rec = [], collections.defaultdict(lambda: collections.defaultdict(set))
    checked = 0
    for st, c, v in surname_claims:
        s = c.get("subject") or []
        pid = c.get("person") or (s[1] if len(s) > 1 else None)
        year, code, cid = v.get("year"), v.get("club_code"), None
        if s and s[0] == "stint":
            code = s[2]; year = int(str(s[3]).split("-")[-1])
        if code and year:
            r = C.resolve(code, int(year), None, source="season_key")
            cid = r[0] if r else None
        jo = v.get("_joined_on") or {}
        if cid is None and jo.get("club_id") and jo.get("year"):
            # A PERSON-SUBJECT claim (a line-up, an honour) has no club-season in its subject; it
            # states the one its join was made on, and the gate recounts the surname there itself.
            cid, year = jo["club_id"], int(jo["year"])
        if cid is None:
            bad.append(f"{st}: {v.get('name_as_printed')} -- the club-season cannot be read from the claim"); continue
        on = {p for (p,) in db.execute("select distinct person from claim where scope='stint' and club_id=? and year=? "
                                       f"and store != ? and person is not null {NOT_STAFF}", (cid, int(year), st, *STAFF))}
        k = sur(v.get("name_as_printed"))
        holders = [p for p in on if any(sur(n) == k for n in names[p])]
        checked += 1
        if len(holders) != 1 or pid not in holders:
            bad.append(f"{st}: '{v.get('name_as_printed')}' on {cid} {year} -- {len(holders)} holder(s) of surname '{k}' "
                       f"{sorted(holders)[:3]}, claim names {pid}")
        by_rec[c.get("source_record")][pid].add(k)
    check(not bad, f"S1 every surname join is unique on its club-season ({checked} checked; {len(bad)} bad: {bad[:3]})")
    dup = [(sr, p, sorted(ks)) for sr, m in by_rec.items() for p, ks in m.items() if len(ks) > 1]
    check(not dup, f"S2 no source record joins two printed names to one man by surname ({len(dup)}: {dup[:3]})")

    cache = {}
    def roster(cid, year, st):
        k = (cid, int(year), st)
        if k not in cache:
            cache[k] = {p for (p,) in db.execute("select distinct person from claim where scope='stint' and club_id=? "
                                                 f"and year=? and store != ? and person is not null {NOT_STAFF}",
                                                 (*k, *STAFF))}
        return cache[k]
    ON = {"exact_full_name_on_the_club_season", TIER}
    off, off_nb, n3, n4 = [], [], 0, 0
    for st, c, v in joined:
        s = c.get("subject") or []
        pid = c.get("person") or (s[1] if len(s) > 1 else None)
        t, jo = str(v.get("_join_tier")), (v.get("_joined_on") or {})
        if t in ON or t.startswith("ruled_attachment"):
            if not (jo.get("club_id") and jo.get("year")):
                off.append(f"{st}: '{v.get('name_as_printed')}' states no _joined_on"); continue
            n3 += 1
            if pid not in roster(jo["club_id"], jo["year"], st):
                off.append(f"{st}: '{v.get('name_as_printed')}' -> {pid}, who is not on {jo['club_id']} {jo['year']}")
        elif t in ("exact_full_name_held_once_and_on_the_neighbouring_season", ADJ):
            # ONLY this tier asserts the man is on the neighbouring season. A man PROMOTED on an opened
            # club-season carries the neighbour too, and by construction is NOT on it -- that is why he
            # was promoted -- so he is not checked here.
            if not jo.get("neighbour"):
                off_nb.append(f"{st}: '{v.get('name_as_printed')}' states no neighbouring season"); continue
            n4 += 1
            ncid, ny = jo["neighbour"]
            if pid not in roster(ncid, ny, st):
                off_nb.append(f"{st}: '{v.get('name_as_printed')}' -> {pid}, not on the neighbouring {ncid} {ny}")
            elif t == ADJ:
                # the adjacent-season rule: the surname must be UNIQUE on the season joined to, recounted here
                k = sur(v.get("name_as_printed"))
                h = [p for p in roster(ncid, ny, st) if any(sur(n) == k for n in names[p])]
                if len(h) != 1:
                    off_nb.append(f"{st}: '{v.get('name_as_printed')}' -> {pid}: {len(h)} holders of '{k}' on {ncid} {ny}")
                by_rec[c.get("source_record")][pid].add(k)
    check(not off, f"S3 every joined man is on the club-season his claim says it was joined on ({n3} checked; "
                   f"{len(off)} bad: {off[:3]})")
    check(not off_nb, f"S4 every opened-season join is on the neighbouring season it names ({n4} checked; "
                      f"{len(off_nb)} bad: {off_nb[:3]})")

    nonclub = [f"{st}: {c.get('subject')}" for st, c in staff
               if not (isinstance(c.get("subject"), list) and c["subject"][:1] == ["club_season"]) or c.get("person")]
    check(not nonclub, f"C1 every club_staff_role claim is about a club-season and names no person ({len(nonclub)}: {nonclub[:3]})")
    both = sorted(staff_stores & role_title_stores)
    check(not both, f"C2 no store writing club_staff_role also writes role_title ({both})")
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        # PROVE IT CAN FAIL, on fabricated claims written nowhere: a surname join onto a club-season
        # holding two Smiths, one holding nobody of the name, a staff role about a person, and a
        # store writing both predicates.
        fake = {"claims": [
            {"subject": ["stint", "P_SELFTEST", "NYG", "NFL-1934"], "predicate": "x", "source_record": "t#1",
             "value": {"_join_tier": TIER, "name_as_printed": "Smith"}},
            {"subject": ["stint", "P_SELFTEST", "NYG", "NFL-1934"], "predicate": "x", "source_record": "t#1",
             "value": {"_join_tier": TIER, "name_as_printed": "Zyxwvut"}},
            {"subject": ["person", "P_SELFTEST"], "predicate": "club_staff_role", "person": "P_SELFTEST", "value": {}},
            {"subject": ["person", "P_SELFTEST"], "person": "P_SELFTEST", "predicate": "x", "source_record": "t#2",
             "value": {"_join_tier": "ruled_attachment_selftest", "name_as_printed": "Nobody Here",
                       "_joined_on": {"club_id": "club-new-york-giants-1925", "year": 1934}}},
            {"subject": ["person", "P_SELFTEST"], "person": "P_SELFTEST", "predicate": "x", "source_record": "t#3",
             "value": {"_join_tier": "exact_full_name_held_once_and_on_the_neighbouring_season",
                       "name_as_printed": "Nobody Here", "_joined_on": {"club_id": "x", "year": 1919,
                       "neighbour": ["club-new-york-giants-1925", 1934]}}},
            {"subject": ["stint", "P_SELFTEST", "NYG", "NFL-1934"], "predicate": "role_title", "value": "Trainer"}]}
        main(extra=[("selftest", fake)])
        ok = len(FAILS) >= 6
        print("self-test:", "the gate fails when it should" if ok else "SELF-TEST DID NOT FAIL -- the gate proves nothing")
        sys.exit(0 if ok else 1)
    sys.exit(main())
