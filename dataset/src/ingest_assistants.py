"""Assistant coaches from the media guides. StatsCrew cannot supply them at all.

IDENTITY, per design 2.4 re-measured in report 29: NOT birth date. It runs at
3.7% across 513 guides and 0% before 1940. An assistant is identified by STINT
CONTINUITY - the chain of (club, season, title) a man occupies - and two
same-named assistants with overlapping chains have no discriminator at all and
must be REFUSED rather than resolved.

  python3 src/ingest_assistants.py [--write]
"""
import os, re, csv, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
TEXT = os.path.join(ROOT, "text_all")

# THE TITLE VOCABULARY IS ERA-NATIVE, and a single list is era-biased.
# Older guides write "Backfield Coach". Modern ones write the unit alone -
# the 1999 Colts list reads "Bruce Arians, Quarterbacks" and "Gene Huey,
# Running Backs", with no word "Coach" anywhere. Requiring "Coach" silently
# undercounts every modern staff, which would have shown up as a false era
# trend in assistant coverage.
_WITH_COACH = (r"Assistant Coach|Asst\.? Coach|Line Coach|Backfield Coach|End Coach|"
               r"Defensive Coordinator|Offensive Coordinator|Linebackers? Coach|"
               r"Secondary Coach|Receivers Coach|Quarterbacks? Coach|"
               r"Running Backs? Coach|Special Teams Coach|Head Coach|"
               r"Asst\.? Head Coach")
_UNIT_ONLY = (r"Quarterbacks|Running Backs|Wide Receivers|Tight Ends|"
              r"Offensive Line|Defensive Line|Linebackers|Defensive Backs|"
              r"Special Teams|Strength (?:and|&) Conditioning|Secondary|"
              r"Offensive Assistant|Defensive Assistant")
TITLES = _WITH_COACH + "|" + _UNIT_ONLY

# A staff SECTION. A name beside a title anywhere in a guide is not that club's
# staff - guides discuss opponents and history. Tom Landry surfaced as Cincinnati
# Bengals 1979 because the Bengals guide mentions him; he coached Dallas.
STAFF_HEADER = re.compile(
    r"\b(COACHING STAFF|ASSISTANT COACHES|THE COACHES|Coaching Staff|"
    r"Assistant Coaches|THE HEAD COACH)\b")
SECTION = 6000
# NOT re.I on the whole pattern. Case-insensitivity makes [A-Z] match lowercase,
# so the name half matched at nearly every position - catastrophic backtracking,
# and it silently discarded the "a name is capitalised" constraint that is doing
# the work. The flag belongs on the TITLE only, where the era varies the casing.
PAT = re.compile(r"([A-Z][A-Za-z'\.\-]+(?:\s+[A-Z][A-Za-z'\.\-]+){1,2})"
                 r"\s*[,\-—:]{1,2}\s*((?i:" + TITLES + r"))")
# A word that is a job, not a name. These sit where a name sits in a header.
NOT_A_NAME = re.compile(r"\b(coach|staff|coaching|football|club|team|"
                        r"director|manager|trainer|scout|president|owner|coordinator|quarterbacks|linebackers|secondary|receivers|assistant)\b", re.I)


def club_stoplist(rows):
    """Club names AS THE INDEX STATES THEM - derived, not supplied from memory."""
    clubs = set()
    for r in rows:
        m = re.match(r"(.+?)\s+\d{4}\s+Media Guide", r["title"])
        if m:
            c = m.group(1).strip().lower()
            clubs.add(c)
            w = c.split()
            if len(w) > 1:
                clubs.add(w[-1]); clubs.add(" ".join(w[:-1]))
    return clubs


def main():
    write = "--write" in sys.argv
    rows = list(csv.DictReader(open(os.path.join(ROOT, "index.csv"))))
    byid = {r["identifier"]: r for r in rows}
    stop = club_stoplist(rows)

    stints = collections.defaultdict(set)      # name -> {(club, year, title)}
    rej = collections.Counter()
    files = 0
    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith(".txt"): continue
        r = byid.get(fn[:-4])
        if not r: rej["no index row"] += 1; continue
        # A LEAGUE-WIDE book asserts no club. index.csv flags these (40 items) and
        # not reading the flag made "NFL Record & Fact Book 1993" a club, so a man
        # listed in both his club's guide AND the league book looked like a man at
        # two clubs in one season - a false refusal. Two documents, one office,
        # one appointment.
        if str(r.get("league_wide", "")).strip().lower() == "true":
            rej["league-wide book: asserts no club"] += 1
            continue
        club = re.sub(r"\s+\d{4}\s+Media Guide.*", "", r["title"]).strip()
        year = r["year"]
        files += 1
        full = open(os.path.join(TEXT, fn), encoding="utf-8", errors="replace").read()
        heads = list(STAFF_HEADER.finditer(full))
        if heads:
            t = "".join(full[h.end():h.end() + SECTION] for h in heads)
        else:
            rej["no staff section - guide skipped"] += 1
            continue
        for m in PAT.finditer(t):
            nm = " ".join(m.group(1).split())
            low = nm.lower()
            if low in stop:            rej["club name"] += 1; continue
            if NOT_A_NAME.search(nm):  rej["job word, not a name"] += 1; continue
            if len(nm) < 6:            rej["too short"] += 1; continue
            if nm.isupper() and len(nm.split()) < 2: rej["header"] += 1; continue
            if low in ("most seasons", "high school", "head coach"): rej["phrase"] += 1; continue
            stints[low].add((club, year, m.group(2).title()))

    print(f"guides read {files}")
    print(f"distinct assistant/head-coach names {len(stints)}")
    print(f"stints {sum(len(v) for v in stints.values())}")
    print("rejected:")
    for k, v in rej.most_common(): print(f"   {v:6}  {k}")

    # THE REFUSAL: two men of one name whose chains OVERLAP cannot be told apart.
    refused = []
    for nm, sts in stints.items():
        byyear = collections.defaultdict(set)
        for club, yr, title in sts: byyear[yr].add(club)
        clash = {y: c for y, c in byyear.items() if len(c) > 1}
        if clash: refused.append((nm, clash))
    print(f"\nnames at two clubs in ONE season - no discriminator, REFUSED: {len(refused)}")
    for nm, c in refused[:8]:
        print(f"   {nm}: " + "; ".join(f"{y} {sorted(v)}" for y, v in sorted(c.items())))
    if write:
        json.dump({"stints": {k: sorted(v) for k, v in stints.items()},
                   "refused": [{"name": n, "clash": {y: sorted(v) for y, v in c.items()}}
                               for n, c in refused],
                   "rejected": dict(rej), "guides_read": files},
                  open(os.path.join(BASE, "build-reports", "assistants.json"), "w"), indent=1)
        print("\nwrote build-reports/assistants.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
