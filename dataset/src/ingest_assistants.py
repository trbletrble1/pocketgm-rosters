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
# The name must START at a boundary. Without one the regex simply takes the two
# or three capitalised words before the title, and in OCR'd multi-column text
# those are often the end of the previous line: "biographies Monte Clark",
# "coaches Don Coryell", "balas Tom Landry". Measured against StatsCrew's known
# head coaches, the unanchored version was 36% precise.
PAT = re.compile(r"(?:^|[;.\n\|]|\s{2,})\s*"
                 r"([A-Z][A-Za-z'\.\-]+(?:\s+[A-Z][A-Za-z'\.\-]+){1,2})"
                 r"\s*[,\-—:]{1,2}\s*((?i:" + TITLES + r"))", re.M)
# A word that is a job, not a name. These sit where a name sits in a header.
NOT_A_NAME = re.compile(r"\b(coach|staff|coaching|football|club|team|"
                        r"phone|city|biographies|biography|vice|jr|sr|inc|"
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


def statscrew_head_coaches():
    """year -> {head coach names}, from the StatsCrew coach store.

    This is the ONE dimension of a guide's staff list we can independently
    verify. Assistants cannot be checked against anything - that is why the
    guides are being read at all - so the head coach is used to CERTIFY the
    block: if a staff list names the head coach StatsCrew records for that
    season, the list is that season's real staff and its assistants stand with
    it. If it does not, the block is a historical retrospective or a staff
    directory, and every name in it is dropped.
    """
    import collections as _c
    p = os.path.join(BASE, "build", "coaches-nfl.json")
    if not os.path.exists(p): return {}
    d = json.load(open(p))
    nm = {c["subject"][1]: str(c["value"]).lower()
          for c in d["claims"] if c.get("predicate") == "name"}
    out = _c.defaultdict(set)
    for c in d["claims"]:
        if c.get("predicate") == "is_head_coach":
            n = nm.get(c["subject"][1])
            if n:
                out[str(c.get("observed_at"))].add(n)
                w = [x for x in re.sub(r"[^a-z ]", "", n).split() if len(x) > 1]
                if len(w) >= 2: out[str(c.get("observed_at"))].add(w[0][0] + "|" + w[-1])
    return out


def certified(found, year, sc):
    """Did this block name the season's actual head coach?"""
    hc = [n for n, t in found if t.lower() == "head coach"]
    if not hc: return None                     # no head coach in the block
    known = sc.get(str(year))
    if not known: return None                  # nothing to check against
    for n in hc:
        if n in known: return True
        w = [x for x in re.sub(r"[^a-z ]", "", n).split() if len(x) > 1]
        if len(w) >= 2 and w[0][0] + "|" + w[-1] in known: return True
    return False


def main():
    write = "--write" in sys.argv
    SC = statscrew_head_coaches()
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
        found = []
        for m in PAT.finditer(t):
            nm = " ".join(m.group(1).split())
            low = nm.lower()
            if low in stop:            rej["club name"] += 1; continue
            if NOT_A_NAME.search(nm):  rej["job word, not a name"] += 1; continue
            if len(nm) < 6:            rej["too short"] += 1; continue
            if nm.isupper() and len(nm.split()) < 2: rej["header"] += 1; continue
            if low in ("most seasons", "high school", "head coach"): rej["phrase"] += 1; continue
            found.append((low, m.group(2).title()))
        cert = certified(found, year, SC)
        if cert is False:
            rej["block REJECTED: head coach does not match StatsCrew"] += len(found)
            continue
        if cert is None:
            rej["block unverifiable: no head coach named"] += len(found)
            continue
        for low, title in found:
            stints[low].add((club, year, title))

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
