"""Neft, Cohen & Deutsch, *Pro Football: The Early Years* (1978) -- PASS 2, the 1930s. Ryan's ruling of 2026-09-12.

The same ingest as pass 1 (src/ingest_neft_1920s.py), configured for the decade: ONE implementation of the reading,
the join, the refusals and the claims. Only the pages, the reading folders, the seasons and the store change.

  * 1930-32 rosters: PDF 58-60, 62-63, 65-66, in the 1920s layout.
  * 1933-39: each conference-season a FACING PAIR -- linemen by position with the club header on the even page,
    backs and ends on the odd page -- PDF 80-107. A club's lines on the two pages are one block, so a surname or
    a full name printed twice on one club is caught across the pair.
  * Colleges: the 1933-45 register (PDF 138-146, read for this pass), and for men of 1930-32 the 1920-32 register
    (PDF 67-76) that pass 1's readers read. An entry pass 1 could already reach (a 1920s season) is left to pass 1.
  * The 1934 combined Cincinnati-St. Louis block ("C-S") is one roster in Neft and two clubs in the archive. It is not
    placed on either: Ryan, 2026-09-11 -- two sources disagreeing about how a season is organised, held, not resolved.

  python3 src/ingest_neft_1930s.py [--write]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ingest_neft_1920s as I

B = os.path.join(HERE, "..", "build")
PAIRS = {1933: (80, 83), 1934: (84, 87), 1935: (88, 91), 1936: (92, 95), 1937: (96, 99), 1938: (100, 103), 1939: (104, 107)}
SEASON_OF_PAGE = {58: 1930, 59: 1930, 60: 1930, 62: 1931, 63: 1931, 65: 1932, 66: 1932,
                  **{p: y for y, (a, b) in PAIRS.items() for p in range(a, b + 1)}}
I.configure(STORE="neft-early-years-1978-1930s",
            READINGS=os.path.join(B, "neft-readings-1930s"),
            ROSTER_PAGES=sorted(SEASON_OF_PAGE),
            SEASON_OF_PAGE=SEASON_OF_PAGE,
            REGISTER_PAGES=list(range(67, 77)) + list(range(138, 147)),
            REGISTER_DIRS={p: os.path.join(B, "neft-readings-1920s") for p in range(67, 77)},
            YEARS=range(1930, 1940))

if __name__ == "__main__":
    o = I.main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"claims {c['claims']:,}  leads {c['leads']}  candidates {c['candidates']}  refusals {c['refusals']}  "
          f"held out {c['held_back']}  reader disagreements {c['reader_disagreements']}  clubs unresolved {c['clubs_unresolved']}")
    print("  by predicate:", c["by_predicate"])
    for y, s in c["by_season"].items():
        print(f"  {y}: " + "; ".join(f"{k} {v}" for k, v in sorted(s.items())))
    if "--write" not in sys.argv: print("DRY RUN -- nothing written. --write to write.")
