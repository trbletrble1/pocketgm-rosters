"""Ingest the 1957 antitrust hearing: the salary table on 2567, the Standard
Players Contract on 2748-2750, and the league receipts schedule on 2751.

THREE ACQUISITION STATES, and they must not pool.

The contract has a clean text layer and is PARSED. The salary table is printed
sideways on a 1-bit scan; its OCR is unusable and every figure was READ BY EYE
from a magnified page image. A digit a person read off a degraded scan is a
different kind of fact from one a machine extracted, and that difference survives
into every claim as `acquisition_state`.

THE 20 FAILING CELLS ARE WRITTEN. A cell that fails the roster-size check carries
the computed ratio and the flag. Dropping them would hide a finding, and adjusting
a digit to make one pass would manufacture a table that merely looks right.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
DECL = json.load(open(os.path.join(BASE, "declarations", "hearing-1957.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
SP = ("/private/tmp/claude-501/-Users-ryannecci-Documents/"
      "8d717785-5b8e-4adb-8f0e-48e0899794bb/scratchpad/")

READ_BY_EYE = "read_by_eye_from_scan"
PARSED = "parsed_text_layer"

CLUBS = ["Baltimore Colts", "Chicago Bears", "Chicago Cardinals", "Cleveland Browns",
         "Detroit Lions", "Green Bay Packers", "Los Angeles Rams", "New York Giants",
         "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
         "Washington Redskins"]
CONFERENCE = ["Western", "Western", "Eastern", "Eastern", "Western", "Western",
              "Western", "Eastern", "Eastern", "Eastern", "Western", "Eastern"]

# total, mean, median, range_low, range_high -- as READ, nothing adjusted
TABLE = {
 1952: [None,(290837,8813,7400,5650,13650),(253275,7675,7150,5000,12500),
        (279342,8300,7700,5500,20000),(294291,7954,6400,5000,20000),
        (231975,7030,5500,5000,15000),(281771,8539,7000,5625,16250),
        (244175,7399,6500,4500,16250),(218640,6625,6000,4000,11000),
        (209254,6341,5700,4000,12000),(242758,6782,6450,4200,15200),
        (217475,6590,6000,4500,13000)],
 1953: [(221699,6718,6750,5000,11000),(286885,8693,6900,5000,12500),
        (243432,7377,7212,5000,12500),(274617,8270,7500,5000,19500),
        (300156,8112,6750,5000,20000),(254737,7719,6000,5000,13000),
        (252233,7607,7000,5500,19000),(239170,7247,6250,4500,15000),
        (233688,7081,6250,4525,11000),(236442,7165,6550,5000,12350),
        (250186,6754,7485,5485,15485),(244626,7413,6500,4500,12500)],
 1954: [(231450,7012,7250,5000,12000),(341418,10347,8000,5000,12500),
        (252129,7943,6800,5000,16000),(297650,9000,8000,5000,22000),
        (311921,8654,7000,5000,23000),(244754,7417,7000,5500,14000),
        (281279,8524,7500,4800,18000),(298756,9053,6300,4700,16000),
        (238092,7215,7000,4500,11750),(251091,7700,6000,5100,13000),
        (307025,7705,8250,6250,18750),(236860,7111,7000,5000,12500)],
 1955: [(356450,7771,7500,5000,15000),(318332,9646,8100,6400,14000),
        (293783,8900,7500,5700,20000),(351267,9700,9000,5200,25000),
        (315479,8089,8000,5500,23000),(261822,7934,7000,5000,18500),
        (322458,9462,7500,5500,19000),(302764,9175,7500,5000,16000),
        (253073,7669,7250,5000,13500),(242483,7348,6700,4700,12200),
        (324545,8377,8225,5000,20100),(240794,7297,6500,5000,14000)],
 1956: [(294392,8921,8250,6000,17500),(342525,10380,8750,6500,14200),
        (318411,9650,8515,5500,20000),(368031,10000,9100,6000,19000),
        (330375,8615,8750,5500,20000),(277612,8413,7500,5000,18500),
        (352958,10696,8000,5500,20000),(321258,9523,7500,5200,16000),
        (283483,8590,7500,5750,13500),(276875,8390,7500,5250,12250),
        (332614,9058,9000,5600,20100),(275912,8300,7500,5000,14000)]}

# Cells whose read is qualified. These ride WITH the value, never replace it.
QUALIFIED = {
 (1955, "Baltimore Colts"): {
   "qualification": "probable_misread_leading_digit",
   "note": "read as 356,450, which gives 45.87. At 256,450 the check gives exactly "
           "33.00. THE VALUE IS WRITTEN AS READ. The reader did not change it."},
 (1952, "New York Giants"): {
   "qualification": "check_selected_between_two_candidate_reads",
   "note": "the scan images $7,3?? with the last two digits blobbed. 7,300 fails the "
           "check (33.45); 7,399 passes exactly (33.00). The check SELECTED this "
           "value; it is not a clean read."}}


class HearingError(Exception):
    pass


def claim(sr, subject, pred, value, acq, kind="observed", **extra):
    if subject is None or value in (None, ""):
        raise HearingError("a claim needs a subject and a non-empty value")
    if acq not in (READ_BY_EYE, PARSED):
        raise HearingError(f"unknown acquisition state {acq!r}")
    return {"source_record": sr, "source_id": SRC_ID, "stated_by": DECL["stated_by"],
            "attribution": [DECL["name"]], "subject": subject, "predicate": pred,
            "value": value, "kind": kind, "acquisition_state": acq,
            "observed_at": "held-2026-09", **extra}


def roster_check(total, mean):
    """total / mean should be the number of men paid -- an integer."""
    n = total / mean
    return {"computed_n": round(n, 4), "passes": abs(n - round(n)) < 0.02,
            "nearest_integer": round(n)}


def salary_table():
    sr = f"{SRC_ID}#p2567"
    claims, obs = [], []
    npass = nfail = 0
    for year in sorted(TABLE):
        for i, cell in enumerate(TABLE[year]):
            club = CLUBS[i]
            subj = ["club_season", club, year]
            if cell is None:
                # THE SOURCE ASSERTS THIS ABSENCE. The Baltimore franchise did not
                # exist in 1952, and the printed table leaves the column blank. That
                # is not a value we failed to read and it is not zero -- the same
                # distinction the roster-limits ingest makes between '-' and ''.
                claims.append(claim(sr, subj, "hearing.player_salaries", "no data printed",
                                    READ_BY_EYE, kind="absent",
                                    _the_source_prints_nothing_here=True,
                                    _reason="the franchise did not exist in this season"))
                continue
            total, mean, median, lo, hi = cell
            chk = roster_check(total, mean)
            npass += chk["passes"]; nfail += not chk["passes"]
            v = {"total": total, "mean": mean, "median": median,
                 "range_low": lo, "range_high": hi,
                 "conference": CONFERENCE[i],
                 "_conference_standing_not_read": True,
                 "roster_size_check": chk,
                 "range_check": {"mean_in_range": lo <= mean <= hi,
                                 "median_in_range": lo <= median <= hi}}
            q = QUALIFIED.get((year, club))
            if q:
                v["read_qualification"] = q
            claims.append(claim(sr, subj, "hearing.player_salaries", v, READ_BY_EYE,
                                _check_failed=not chk["passes"]))
    # a pattern in the failures, recorded as an OBSERVATION about the source
    byclub = collections.Counter()
    for year in TABLE:
        for i, cell in enumerate(TABLE[year]):
            if cell and not roster_check(cell[0], cell[1])["passes"]:
                byclub[CLUBS[i]] += 1
    obs.append({"subject": ["source", SRC_ID, "p2567"],
                "predicate": "hearing.observation",
                "value": {"what": "the roster-size check fails for Cleveland Browns and "
                                  "San Francisco 49ers in ALL FIVE years, 10 of 10, while "
                                  "six clubs pass nearly perfectly.",
                          "why_it_points_at_the_source": "a reader's misreads would scatter; "
                                  "these cluster in two columns. Cleveland carries a "
                                  "fiscal-year footnote, and its ratio is not even "
                                  "consistently wrong (33.66, 33.21, 33.07, 36.21, 36.80), "
                                  "so it is not a fixed alternative denominator either.",
                          "failures_by_club": dict(byclub.most_common()),
                          "resolved": None},
                "kind": "derived", "_nothing_is_resolved": True})
    return claims, obs, npass, nfail


CONTRACT_PAGES = {2748: 1530, 2749: 1531, 2750: 1532}
RECEIPTS_PAGE = (2751, 1533)
DOCS = "/Users/ryannecci/Documents/pgm3-sources/antitrust docs"


def page_text(seq):
    import glob, logging, warnings
    logging.disable(logging.CRITICAL); warnings.filterwarnings("ignore")
    from pypdf import PdfReader
    f = glob.glob(f"{DOCS}/umn-31951d03669357b-{seq}-*.pdf")[0]
    t = "".join((p.extract_text() or "") for p in PdfReader(f).pages)
    return re.sub(r"[ \t]+", " ", t).strip()


CLAUSE = re.compile(r"(?m)^\s*(\d{1,2})\.\s")


def contract():
    """The printed 1957 form, verbatim, with clause numbering kept.

    Its value is that it is UNAMENDED -- it is the baseline the ~200 individual
    contracts are read against for strikethroughs and riders, so a paraphrase
    would destroy the only thing it is for."""
    sr = f"{SRC_ID}#p2748-2750"
    full = []
    for printed in sorted(CONTRACT_PAGES):
        t = page_text(CONTRACT_PAGES[printed])
        full.append((printed, t))
    joined = "\n".join(t for _, t in full)
    claims = [claim(sr, ["document", "nfl-standard-players-contract-1957"],
                    "hearing.contract_text_verbatim",
                    {"printed_pages": "2748-2750", "text": joined,
                     "chars": len(joined),
                     "_verbatim": "stored exactly as printed; not normalised"},
                    PARSED)]
    # clause-by-clause, so a later diff against an individual instrument can
    # address the clause the archive already tracks
    for printed, t in full:
        for m in CLAUSE.finditer(t):
            num = int(m.group(1))
            nxt = CLAUSE.search(t, m.end())
            body = t[m.end():nxt.start() if nxt else len(t)].strip()
            if len(body) < 40:
                continue
            note = None
            if num == 8:
                note = ("the reserve-clause justification: 'special, exceptional and "
                        "unique knowledge, skill and ability'")
            if num == 4:
                note = ("carries the payment term the archive has tracked across "
                        "individual instruments since 1928")
            claims.append(claim(sr, ["document", "nfl-standard-players-contract-1957"],
                                "hearing.contract_clause",
                                {"clause_number": num, "printed_page": printed,
                                 "text": body, "note": note}, PARSED))
    return claims


# The OCR leaves spaces INSIDE numbers -- "35, 330. 42" -- so the patterns must
# tolerate them, and the digits are re-joined before they become a value.
NUM = r"\d[\d,\s]*\.\s*\d\d"
PAREN = re.compile(r"\(\s*\$?\s*(" + NUM + r")\s*\)")
PLAIN = re.compile(r"\$?\s*(" + NUM + r")")


def money(s):
    return float(re.sub(r"[^\d.]", "", s))


def receipts():
    """2751: NFL excess of receipts over disbursements, 1952-56.

    A PARENTHESISED FIGURE IS A NEGATIVE. The page says so itself: 'Figures
    enclosed in parentheses denote an excess of disbursements over receipts.'
    Storing ($68,689.89) as a positive would invert a loss into a profit."""
    printed, seq = RECEIPTS_PAGE
    t = page_text(seq)
    sr = f"{SRC_ID}#p2751"
    vals = []
    for m in PAREN.finditer(t):
        vals.append({"as_printed": re.sub(r"\s+", " ", m.group(0)), "amount": -money(m.group(1)),
                     "sign": "negative", "_parentheses_denote_a_loss": True})
    covered = []
    for m in PAREN.finditer(t):
        covered.append((m.start(), m.end()))
    for m in PLAIN.finditer(t):
        if any(a <= m.start() < b for a, b in covered):
            continue                     # already captured as a parenthesised loss
        vals.append({"as_printed": re.sub(r"\s+", " ", m.group(0)).strip(),
                     "amount": money(m.group(1)), "sign": "positive"})
    return [claim(sr, ["league_season_range", "NFL", "1952-1956"],
                  "hearing.receipts_over_disbursements",
                  {"printed_page": printed, "figures": vals,
                   "note_as_printed": "Figures enclosed in parentheses denote an excess "
                                      "of disbursements over receipts.",
                   "_run_is_incomplete": True,
                   "_continues_on": "printed page 2752, which is NOT held"},
                  PARSED)]


def receipts_selfcheck(figures):
    """The five annual figures should sum to the printed 5-year total. This also
    proves the SIGN handling: read the parenthesised figures as positive and the
    sum does not reconcile."""
    amts = [f["amount"] for f in figures]
    if len(amts) != 6:
        return {"ran": False, "why": f"expected 6 figures, found {len(amts)}"}
    total = amts[-1]; annual = amts[:-1]
    return {"ran": True, "annual_sum": round(sum(annual), 2), "stated_total": total,
            "reconciles": abs(sum(annual) - total) < 0.01,
            "_also_proves": "the parentheses were read as negative"}


def main(write=True):
    sal, obs, npass, nfail = salary_table()
    con = contract()
    rec = receipts()
    rec[0]["value"]["self_check"] = receipts_selfcheck(rec[0]["value"]["figures"])
    claims = sal + con + rec
    acq = collections.Counter(c["acquisition_state"] for c in claims)
    kinds = collections.Counter(c["kind"] for c in claims)
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": "held",
                      "hathitrust_item": DECL["hathitrust_item"]},
           "claims": claims, "observations": obs,
           "counts": {"claims": len(claims),
                      "by_acquisition_state": dict(acq),
                      "by_kind": dict(kinds),
                      "salary_cells_pass": npass, "salary_cells_fail": nfail,
                      "salary_cells_absent": sum(1 for c in sal if c["kind"] == "absent"),
                      "contract_clauses": sum(1 for c in con
                                              if c["predicate"] == "hearing.contract_clause"),
                      "qualified_reads": len(QUALIFIED),
                      "receipts_self_check": rec[0]["value"]["self_check"]["reconciles"]}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "hearing-1957.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    for k, v in c.items():
        print(f"  {k:26s} {v}")
