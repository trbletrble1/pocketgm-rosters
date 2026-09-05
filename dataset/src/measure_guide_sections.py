"""What is IN a media guide? Section census across all 1,803 texts, per decade.

Report 11 surveyed 28 files, ALL 1979. That is a sample of one era, and the
lesson has bitten three times today: a sample tells you a field's typical value,
only a census tells you its span. A 1939 guide and a 2019 guide are different
objects.

THE VOCABULARY PROBLEM IS THE POINT. A guide that calls its staff pages
"FOOTBALL STAFF" is not missing a coaching section; our word list is missing a
word. So this reports TWO things:
  - canonical section presence, per decade, from a vocabulary that is data
  - the unmatched headers it saw, ranked - which is how the vocabulary grows

Characterisation only. Extracts nothing.
"""
import os, re, sys, csv, json, collections

ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
TEXT = os.path.join(ROOT, "text_all")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# canonical section -> the words guides actually use for it
SECTIONS = {
 "coaching_staff":   [r"COACHING STAFF", r"ASSISTANT COACHES", r"THE COACHES",
                      r"FOOTBALL STAFF", r"COACHES?\b", r"HEAD COACH"],
 "front_office":     [r"FRONT OFFICE", r"ADMINISTRATION", r"EXECUTIVE",
                      r"CLUB DIRECTORY", r"MANAGEMENT", r"OWNERSHIP"],
 "medical_staff":    [r"MEDICAL STAFF", r"TRAINERS?\b", r"TEAM PHYSICIAN",
                      r"ATHLETIC TRAINER"],
 "player_bios":      [r"PLAYER BIOGRAPHIES", r"VETERAN BIOS", r"PLAYER PROFILES",
                      r"BIOGRAPHIES", r"ROOKIE BIOS"],
 "roster":           [r"\bROSTER\b", r"ALPHABETICAL ROSTER", r"NUMERICAL ROSTER",
                      r"TRAINING CAMP ROSTER"],
 "career_statistics":[r"CAREER STATISTICS", r"INDIVIDUAL STATISTICS",
                      r"STATISTICS\b", r"YEAR-BY-YEAR"],
 "draft_history":    [r"DRAFT HISTORY", r"DRAFT CHOICES", r"\bDRAFT\b",
                      r"DRAFT SELECTIONS"],
 "transactions":     [r"TRANSACTIONS", r"PLAYER MOVEMENT", r"ACQUISITIONS"],
 "all_time_roster":  [r"ALL-TIME ROSTER", r"ALL TIME ROSTER", r"ALL-TIME PLAYERS"],
 "pronunciation":    [r"PRONUNCIATION", r"HOW TO SAY", r"NAME PRONOUNCER"],
 "records":          [r"\bRECORDS\b", r"ALL-TIME RECORDS", r"TEAM RECORDS"],
 "schedule_results": [r"\bSCHEDULE\b", r"\bRESULTS\b", r"GAME-BY-GAME"],
 "opponents":        [r"OPPONENTS", r"OPPONENT REVIEW", r"SCOUTING"],
 "stadium":          [r"STADIUM", r"\bFIELD\b", r"FACILITY", r"TRAINING FACILITY"],
 "media_info":       [r"MEDIA INFORMATION", r"PRESS", r"RADIO", r"TELEVISION",
                      r"BROADCAST"],
 "history":          [r"\bHISTORY\b", r"YEAR BY YEAR", r"CHRONOLOGY", r"HONORS"],
 "cheerleaders":     [r"CHEERLEADERS", r"DANCE TEAM"],
 "community":        [r"COMMUNITY", r"FOUNDATION", r"CHARIT"],
}
COMPILED = {k: re.compile("|".join(v), re.I) for k, v in SECTIONS.items()}
# a plausible section HEADING: a short mostly-caps line
HEADING = re.compile(r"^[ \t]*([A-Z][A-Z0-9 '&/\.\-]{5,44})[ \t]*$", re.M)


def main():
    rows = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(ROOT, "index.csv")))}
    present = collections.defaultdict(lambda: collections.Counter())   # decade -> sec -> n
    files = collections.Counter()
    unmatched = collections.Counter()
    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith(".txt"): continue
        yr = rows.get(fn[:-4], {}).get("year", "0000")
        dec = yr[:3] + "0s"
        files[dec] += 1
        t = open(os.path.join(TEXT, fn), encoding="utf-8", errors="replace").read()
        for sec, rx in COMPILED.items():
            if rx.search(t): present[dec][sec] += 1
        # what headings did we see that our vocabulary does not name?
        seen = set()
        for m in HEADING.finditer(t):
            h = " ".join(m.group(1).split())
            if len(h) < 6 or h in seen: continue
            seen.add(h)
            if not any(rx.search(h) for rx in COMPILED.values()):
                unmatched[h] += 1
    decs = sorted(files)
    print("SECTION PRESENCE, share of guides in that decade\n")
    print(f"{'section':<20}" + "".join(f"{d[:4]:>7}" for d in decs))
    print(f"{'(files)':<20}" + "".join(f"{files[d]:>7}" for d in decs))
    for sec in SECTIONS:
        line = f"{sec:<20}"
        for d in decs:
            n = present[d][sec]; line += f"{100*n//max(1,files[d]):>6}%"
        print(line)
    print(f"\nUNMATCHED HEADINGS - our vocabulary has no word for these")
    print(f"(distinct: {len(unmatched)}; the top ones are the vocabulary we are missing)")
    for h, n in unmatched.most_common(40):
        print(f"   {n:>5}  {h}")
    json.dump({"files_by_decade": dict(files),
               "presence": {d: dict(present[d]) for d in decs},
               "unmatched_headings": dict(unmatched.most_common(400))},
              open(os.path.join(BASE, "build-reports", "guide-sections.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
