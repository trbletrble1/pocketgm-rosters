"""Re-measure coach birth-date coverage in the media guides, across decades.

Design 2.4 rests assistant-coach identity on stint continuity because birth
dates were measured at 2.7% - across 28 files, ALL of them 1979. That is a
prior, not a corpus fact. This measures it wherever text is held.

Reads local text only. No network.
"""
import os, re, csv, sys, json, collections

ROOT = os.path.expanduser("~/Documents/pgm3-sources/nfl-books")
TEXT = os.path.join(ROOT, "text_all")

# Titles that mark a coaching bio. Deliberately wide: an assistant is whatever
# the guide calls him, and the vocabulary changes by era.
# NOT the bare word "Coach". A first pass included it and reported 14.3%; a
# sample showed the matches were PLAYERS' birth dates, and in one case a coach's
# CHILDREN's ("two sons, Duey, born March 13... David, born April 15, 1951").
# "Coach" appears throughout a guide - "coached by", "coaching staff", "the
# coach said". It is not a bio marker. Only an explicit staff title is.
TITLE = re.compile(
    r"\b(Assistant Coach|Asst\.? Coach|Line Coach|Backfield Coach|End Coach|"
    r"Defensive Coordinator|Offensive Coordinator|Linebacker[s]? Coach|"
    r"Secondary Coach|Receivers Coach|Quarterback[s]? Coach|"
    r"Running Back[s]? Coach|Special Teams Coach|Head Coach)\b", re.I)
# A birth in a bio belongs to its subject unless the sentence hands it to
# somebody else.
NOT_HIS = re.compile(r"\b(son|sons|daughter|daughters|wife|child|children|"
                     r"grandson|granddaughter|nephew|niece)\b", re.I)
# A PLAYER's bio, which in these guides sits immediately beside the staff pages.
# Its tells are a listed position, a height-weight, a year-of-service or a draft
# note. If one of those falls between the coaching title and the birth date, the
# birth belongs to the player, not the coach.
PLAYER_BIO = re.compile(
    r"\b\d-\d{1,2},\s*\d{3}\b"                     # 6-3, 223
    r"|\b\d{1,2}(?:st|nd|rd|th)\s+Year\b"
    r"|\bDraft Choice\b|\bJoined\s+\w+:\s*Draft\b"
    r"|\b(?:Quarterback|Running Back|Halfback|Fullback|Offensive Guard|"
    r"Defensive Tackle|Linebacker|Cornerback|Safety|Wide Receiver|Tight End|"
    r"Defensive End|Offensive Tackle|Center|Kicker|Punter)\b(?!\s+Coach)", re.I)
BORN = re.compile(r"\b(Born|B\.)\s*[:\-]?\s*"
                  r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
                  r"|\d{1,2}/\d{1,2}/\d{2,4})", re.I)
AGE = re.compile(r"\b(?:age[ds]?|is|at)\s+(\d{2})\b|\b(\d{2})[- ]year[- ]old\b", re.I)
WINDOW = 400   # a bio header states the birth close to the title


def main():
    rows = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(ROOT, "index.csv")))}
    per_dec = collections.defaultdict(lambda: collections.Counter())
    files_with_any_born = collections.defaultdict(set)
    files_seen = collections.defaultdict(set)
    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith(".txt"):
            continue
        ident = fn[:-4]
        yr = rows.get(ident, {}).get("year", "0000")
        dec = yr[:3] + "0s"
        try:
            t = open(os.path.join(TEXT, fn), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        files_seen[dec].add(ident)
        for m in TITLE.finditer(t):
            seg = t[m.end():m.end() + WINDOW]
            per_dec[dec]["titles"] += 1
            b = BORN.search(seg)
            if b and PLAYER_BIO.search(seg[:b.start()]):
                per_dec[dec]["rejected_player_bio"] += 1
                b = None
            if b and not NOT_HIS.search(seg[max(0, b.start()-90):b.start()]):
                per_dec[dec]["born"] += 1
                files_with_any_born[dec].add(ident)
            elif AGE.search(seg):
                per_dec[dec]["age_only"] += 1
    print(f"{'decade':>8} {'files':>6} {'titles':>8} {'born':>7} {'rate':>7} "
          f"{'age-only':>9} {'files w/ any born':>18}")
    tot = collections.Counter()
    for dec in sorted(per_dec):
        c = per_dec[dec]; n = c["titles"] or 1
        tot.update(c)
        print(f"{dec:>8} {len(files_seen[dec]):>6} {c['titles']:>8} {c['born']:>7} "
              f"{100*c['born']/n:>6.1f}% {c['age_only']:>9} "
              f"{len(files_with_any_born[dec]):>7}/{len(files_seen[dec])}")
    n = tot["titles"] or 1
    print(f"\n{'ALL':>8} {sum(len(v) for v in files_seen.values()):>6} {tot['titles']:>8} "
          f"{tot['born']:>7} {100*tot['born']/n:>6.1f}% {tot['age_only']:>9}")
    json.dump({d: dict(c) for d, c in per_dec.items()},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "build-reports", "guide-coach-births.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
