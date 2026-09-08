"""Ken Crippen's AAFC register: 636 men, their death dates and their death places.

THE SOURCE IS A PERSON, NOT A PUBLICATION. Ken Crippen -- founder, lead instructor
and podcaster at the Football Learning Academy; PFRA AAFC Committee chair; co-author
of *The All-America Football Conference* -- compiled this himself and sent it in
correspondence. It is NOT the book. The book is a reference consulted and cited; this
is data he gave for use, and the declaration says which is which because a later
reader cannot tell from a citation alone.

WHY IT MATTERS. Death dates are among the archive's thinnest families: 8,682 observed
against 36,313 unknown. And where Crippen differs from StatsCrew or PFA, that is a
named expert against a reconstruction -- the AAFC record descends from the same Neft
lineage as everything else, and Crippen named its reconstruction team himself.

THE REGISTER CARRIES NO CLUB, so the ruled join is applied one level coarser: the
constraint is the AAFC cohort of 1946-49 rather than a single club-season. Everything
else is unchanged -- exact name in the cohort, exact unique name, surname and forename
initial within the cohort, and nothing looser.

HELD, NOT RESOLVED. Where he and the archive disagree, both stand.

  python3 src/ingest_crippen_aafc.py [--write]
"""
import os, re, sys, json, sqlite3, collections, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from readings import READERS
import dates as model_dates   # service/dates.py -- the reading the MODEL uses

DOC = os.path.expanduser("~/Documents/pgm3-sources/____Abridged Player Register.doc")
OUT = os.path.join(BASE, "build", "crippen-aafc.json")
REPORT = os.path.join(BASE, "build-reports", "crippen-aafc.json")

# `Name (Deceased: DATE, PLACE)` and the four shapes the file also uses
LINE = re.compile(r"^\s*([^()]+?)\s*\(\s*Deceased:?\s*(.+?)\s*\)?\s*$")
MDY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
LONGDATE = re.compile(r"^([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})$")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def read_for_the_report(d):
    """Crippen's `10/7/2000` as a calendar day -- FOR THE COMPARISON IN THIS REPORT
    ONLY. The value written to the store is the string he sent, untouched.

    The declared date reading REFUSES a bare numeric date, and rightly: `2001-12-10`
    and `2001-10-12` are two different dates and deciding which number is the day
    would be a correction, not a reading. That ruling is not set aside here.

    But the register's order is not a guess. Read against the death dates the archive
    already holds, his slash dates agree **520 times as month/day/year and 0 times as
    day/month/year** (14 more agree either way, being days of 12 or less). That is a
    measured fact about this one source, and it is what the counts below rest on --
    not a reading, and not applied to any other source."""
    m = MDY.match(str(d).strip())
    if not m:
        r = model_dates.read(d)
        return None if not r else (r["year"], r["month"], r["day"])
    return (int(m.group(3)), int(m.group(1)), int(m.group(2)))


def read_held(d):
    """A date the archive holds, on THE MODEL'S OWN reading -- service/dates.py, not
    src/readings.py. The two are not the same: `2005-8-14` reads as a day in the
    model and as nothing in src/readings, and comparing on the wrong one manufactured
    a dozen disagreements that were the same date written two ways. A second
    implementation of a reading, differing on real values -- the third such pair found
    today."""
    r = model_dates.read(d)
    return None if not r else (r["year"], r["month"], r["day"])


def norm(s):
    s = re.sub(r"[^a-z ]", " ", str(s or "").lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(s.split())


def flip(name):
    """`Adamle, Tony` -> `Tony Adamle`. The register is alphabetical by surname."""
    if "," in name:
        sur, fore = name.split(",", 1)
        return f"{fore.strip()} {sur.strip()}"
    return name.strip()


def split_date_place(rest):
    """-> (date as printed, place or None, why refused). The date is held AS PRINTED;
    only the split is decided here."""
    parts = [p.strip() for p in rest.split(",")]
    if MDY.match(parts[0]):
        return parts[0], (", ".join(parts[1:]) or None), None
    # `Deceased December 31, 2026, TN` -- a written-out date the comma splits in two
    if len(parts) >= 2 and LONGDATE.match(f"{parts[0]}, {parts[1]}".replace(",", " ", 1).strip()):
        return f"{parts[0]}, {parts[1]}", (", ".join(parts[2:]) or None), None
    # `10/8/2015 Rancho Mirage` -- no comma between the two
    m = re.match(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$", parts[0])
    if m:
        return m.group(1), ", ".join([m.group(2)] + parts[1:]), None
    return None, None, f"the date does not parse: {rest!r}"


def main():
    write = "--write" in sys.argv
    txt = subprocess.run(["textutil", "-convert", "txt", "-stdout", DOC],
                         capture_output=True, text=True).stdout
    if not txt:
        sys.exit("could not convert the register")

    entries, refusals = [], []
    header = None
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("remaining:"):
            header = line
            continue
        if len(line) <= 2:            # an alphabet section letter
            continue
        m = LINE.match(line)
        if not m:
            refusals.append({"line": line, "why": "not of the register's shape"})
            continue
        name, rest = flip(m.group(1)), m.group(2)
        date, place, why = split_date_place(rest)
        if not date:
            refusals.append({"line": line, "why": why})
            continue
        entries.append({"name_as_printed": name, "death_date": date,
                        "death_place": place})

    conn = sqlite3.connect(paths.READ_MODEL)
    # the AAFC cohort: everyone the archive places in the AAFC, 1946-49
    cohort = {p for (p,) in conn.execute(
        "select distinct person from claim where scope='stint' and league='AAFC' "
        "and year between 1946 and 1949 and person is not null")}
    byname, names_of = collections.defaultdict(set), collections.defaultdict(set)
    for p, nm in conn.execute("select person, name from person_name"):
        k = norm(nm)
        if k: byname[k].add(p); names_of[p].add(k)
    held_date, held_place = collections.defaultdict(set), collections.defaultdict(set)
    for p, fam, v in conn.execute(
            "select person, family, value_text from claim where family in "
            "('death_date','death_place') and person is not null"):
        (held_date if fam == "death_date" else held_place)[p].add(str(v).strip())

    n = collections.Counter()
    claims, srs, leads, disagreements = [], {}, [], []
    sr = "crippen-aafc-register#Abridged Player Register"
    srs[sr] = {"source_id": "crippen-aafc-register",
               "locator": "Abridged Player Register.doc, sent by Ken Crippen"}
    cid = 0
    for e in entries:
        k = norm(e["name_as_printed"])
        hits = byname.get(k, set())
        inc = hits & cohort
        if len(inc) == 1:
            pid, how = next(iter(inc)), "exact name, in the AAFC cohort 1946-49"
        elif len(hits) == 1:
            pid, how = next(iter(hits)), "exact name, unique in the archive"
        elif len(inc) > 1:
            pid, how = None, "several of that exact name in the AAFC cohort"
        else:
            w = k.split()
            loose = [p for p in cohort
                     if any(x.split() and x.split()[-1] == w[-1]
                            and x.split()[0][:1] == w[0][:1]
                            for x in names_of.get(p, ()))] if len(w) >= 2 else []
            if len(loose) == 1:
                pid, how = loose[0], "surname and forename initial, in the AAFC cohort"
            else:
                pid = None
                how = ("several by surname and initial in the cohort" if len(loose) > 1
                       else "no person of that name")
        if not pid:
            n[f"lead: {how}"] += 1
            leads.append({"IS_NOT_A_PERSON": True, **e, "why": how})
            continue
        n[f"joined by {how}"] += 1

        prior = held_date.get(pid, set())
        read_mine = read_for_the_report(e["death_date"])
        agrees = any(read_held(x) == read_mine for x in prior if x) if read_mine else None
        if not prior:
            n["DEATH DATE THE ARCHIVE DOES NOT HOLD"] += 1
        elif agrees:
            n["death date the archive holds, and Crippen agrees"] += 1
        else:
            n["DEATH DATE THE ARCHIVE HOLDS AND CRIPPEN DISAGREES"] += 1
            disagreements.append({"person": pid, "name": e["name_as_printed"],
                                  "crippen": e["death_date"],
                                  "the_archive": sorted(prior)})
        rec = f"{sr}#{e['name_as_printed']}"
        srs[rec] = {"source_id": "crippen-aafc-register",
                    "locator": f"Abridged Player Register.doc#{e['name_as_printed']}"}
        for pred, val in (("death_date", e["death_date"]),
                          ("death_place", e["death_place"])):
            if not val:
                continue
            if pred == "death_place":
                n["DEATH PLACE THE ARCHIVE DOES NOT HOLD" if not held_place.get(pid)
                  else "death place the archive already holds something for"] += 1
            cid += 1
            claims.append({
                "id": "c_%04d" % cid, "predicate": pred, "value": val,
                "subject": ["person", pid], "kind": "observed",
                "source_id": "crippen-aafc-register", "source_record": rec,
                "stated_by": "Ken Crippen", "attribution": ["Ken Crippen"],
                "observed_at": "sent-to-Ryan-2026-09", "_join": how,
                "_not_the_book": "Crippen's own compilation, sent in correspondence. "
                                 "NOT `The All-America Football Conference`, which is a "
                                 "reference consulted and cited.",
                "_weight": "a named expert, not a reconstruction. Where this differs "
                           "from StatsCrew or PFA, both of which descend from Neft's "
                           "1970s work, the two are not equal voices -- and the archive "
                           "still holds both and resolves neither."})

    print(f"register entries parsed {len(entries):,}   refused {len(refusals)}")
    for r in refusals:
        print(f"   refused: {r['line'][:70]}  -- {r['why'][:50]}")
    print(f"\nheader line: {header!r}")
    print(f"\nthe AAFC cohort the archive holds: {len(cohort):,} people\n")
    for k, v in n.most_common():
        print(f"   {k:56s} {v:>5,}")
    if disagreements:
        print(f"\nDEATH DATES CRIPPEN AND THE ARCHIVE DISAGREE ON ({len(disagreements)}):")
        for d in disagreements[:20]:
            print(f"   {d['name']:26s} Crippen {d['crippen']:>12s}   archive {', '.join(d['the_archive'])}")
    out = {"source": {"source_id": "crippen-aafc-register", "stated_by": "Ken Crippen"},
           "_what": f"{len(entries)} AAFC men, death date and death place",
           "_the_register_carries_nothing_else": "name, death date, death place. No "
               "birth date, no club, no position, no season. The alphabetical section "
               "letters and one header line are all the structure there is.",
           "_header": header,
           "source_records": srs, "claims": claims, "leads": leads,
           "disagreements": disagreements,
           "counts": dict(n) | {"entries": len(entries), "claims": len(claims),
                                "leads": len(leads), "refused": len(refusals)}}
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        json.dump({"counts": dict(n), "refusals": refusals,
                   "disagreements": disagreements, "leads": leads},
                  open(REPORT, "w"), indent=1)
        print("\nwrote", OUT)
    else:
        print("\n   (dry run; --write to store)")


if __name__ == "__main__":
    main()
