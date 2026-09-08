"""A draft selection is identified by year, league, kind, and either round-and-pick
or, where the document prints none, an order.

THE DEFECT THIS GATES. The declared draft reading was `YYYY r{round} p{overall}`,
on the stated ground that an overall pick is unique within a year. Measured across
1936-2025: 72 of 90 years hold more than one draft numbering from 1. Two selections
that were not the same thing read identically and were folded into one.

RE-DERIVED FROM THE CLAIMS. Nothing here reads a store's report of itself: every
draft claim is read, the shared reader is applied, and the groupings are recomputed.

AND A SECOND PROPERTY, added 2026-09-08 with Ryan's order ruling. An expansion,
allocation or dispersal selection has an ORDER and no round -- PFA prints those pages
with no Round and no Overall column at all. A reading carrying `order` and a reading
carrying `overall` are NEVER the same selection, whatever else they share. This is
checked structurally rather than through `kind`, because a source that declines to
name the kind would otherwise slip through on year and league alone.

EMPTY DENOMINATORS ARE REFUSED. No draft claims, or no readable ones, fails rather
than passing over nothing.

  python3 src/gate_draft_key.py [--selftest]
"""
import os, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import reading_view as RV
REPORT = os.path.join(BASE, "build-reports", "draft-key.json")


def kind_of(v):
    if not isinstance(v, dict): return (None, None)
    lg = v.get("league_from_filename") or v.get("league_from_link") or v.get("league")
    lg = str(lg).upper() if lg and str(lg) != "?" else None
    k = v.get("draft_kind") or None
    return (lg, k)


def run(rows=None, quiet=False):
    """rows: [(person, value)] -- given only by the self-test. Otherwise the model."""
    fails = []
    if rows is None:
        conn = sqlite3.connect(paths.READ_MODEL)
        rows = []
        for person, val in conn.execute(
                "select person,value from claim where family='draft' and person is not null"):
            try: rows.append((person, json.loads(val)))
            except Exception: rows.append((person, val))
    if not rows:
        fails.append("no draft claims found at all -- nothing to check, which is a broken "
                     "scan and not a clean sheet")
        return fails, {"claims": 0, "fails": fails}
    per = collections.defaultdict(list)
    for person, v in rows: per[person].append(v)
    readable = folded = 0
    bad, crossed = [], []
    for person, vals in per.items():
        reads = []
        for v in vals:
            r = RV.read("draft", v)
            if r is None: continue
            readable += 1
            reads.append((r, kind_of(v)))
        for i in range(len(reads)):
            for j in range(i + 1, len(reads)):
                (ra, ka), (rb, kb) = reads[i], reads[j]
                if not RV.same("draft", ra, rb): continue
                folded += 1
                # an ordered selection and a round-and-pick selection are never one
                if ({"order"} <= set(ra)) != ({"order"} <= set(rb)) or \
                   ({"overall"} <= set(ra)) != ({"overall"} <= set(rb)):
                    crossed.append({"person": person, "a": ra, "b": rb})
                # both state a league or a kind, and they differ -> two drafts read as one
                if ((ka[0] and kb[0] and ka[0] != kb[0])
                        or (ka[1] and kb[1] and ka[1] != kb[1])):
                    bad.append({"person": person, "reads_as": ra,
                                "but_is": [list(ka), list(kb)]})
    if not readable:
        fails.append(f"{len(rows):,} draft claims and NOT ONE was readable -- the reader "
                     "is broken, and a gate over zero readings is a pass over nothing")
    if bad:
        fails.append(f"{len(bad):,} pairs of draft claims read as the same selection but "
                     f"come from different leagues or kinds")
    if crossed:
        fails.append(f"{len(crossed):,} pairs read as one selection where one carries an "
                     "ORDER and the other a ROUND AND PICK -- a document that prints no "
                     "round has been joined to one that does")
    out = {"claims": len(rows), "people": len(per), "readable": readable,
           "pairs_read_as_the_same_selection": folded,
           "two_drafts_read_as_one": len(bad), "examples": bad[:12],
           "ordered_joined_to_numbered": len(crossed), "crossed_examples": crossed[:8],
           "fails": fails}
    if not quiet:
        print(f"draft claims       {len(rows):,}   readable {readable:,}   people {len(per):,}")
        print(f"pairs read as one selection   {folded:,}")
        print(f"OF THOSE, actually two drafts {len(bad):,}")
        print(f"ordered joined to numbered    {len(crossed):,}")
        for b in bad[:8]: print(f"   {b['person']}  {b['reads_as']}  is {b['but_is']}")
    if rows is not None and not quiet:
        json.dump(out, open(REPORT, "w"), indent=1)
    return fails, out


def selftest():
    """IT MUST BE SEEN TO FAIL, and the only way to make it fail is to give it the
    reading that WAS wrong. So the self-test installs the old string reading --
    `YYYY r{round} p{overall}`, with no league and no kind -- and requires the gate to
    catch the fold. Then it restores the real reader and requires a pass.

    A gate that cannot be made to fail has not been tested, and this one could not be
    made to fail by data alone: with the reading fixed there is nothing left to find.
    """
    ok = True
    nfl = {"year": 1965, "round": 1, "overall_pick": 1, "league_from_filename": "NFL"}
    afl = {"year": 1965, "round": 1, "overall_pick": 1, "league_from_filename": "AFL"}
    alloc = {"year": 1950, "round": 1, "overall_pick": 1, "league_from_filename": "NFL",
             "draft_kind": "allocationdraft"}
    reg = {"year": 1950, "round": 1, "overall_pick": 1, "league_from_filename": "NFL",
           "draft_kind": "draft"}
    unstated = "1st round (1st overall) 1965 New York Giants"
    # an allocation selection as PFA prints it: an order, no round, no overall
    ordered = {"year": 1960, "league_from_filename": "AFL",
               "draft_kind": "allocationdraft", "printed_order": 1}
    # the same year and league, kind NOT stated, with a round and a pick
    numbered_nokind = {"year": 1960, "round": 1, "overall_pick": 1,
                       "league_from_filename": "AFL"}
    ordered_nokind = {"year": 1960, "league_from_filename": "AFL", "printed_order": 1}

    real_read, real_same = RV.read, RV.same

    def old_read(family, v):
        """the reading as it was: a string, with league and kind thrown away"""
        if family != "draft": return real_read(family, v)
        r = real_read("draft", v)
        return None if r is None else "%s r%s p%s" % (r["year"], r["round"], r["overall"])

    print("  -- with the OLD reading (league and kind discarded):")
    RV.read = old_read
    try:
        for rows, why in (([("P_1", nfl), ("P_1", afl)], "two leagues at one pick number"),
                          ([("P_1", reg), ("P_1", alloc)], "a draft and an allocation draft")):
            f, _ = run(rows=rows, quiet=True)
            print(f"     {'PASS' if f else 'FAIL'}  the gate CATCHES {why}")
            ok &= bool(f)
    finally:
        RV.read = real_read

    print("  -- with the reading as it now is:")
    for rows, want, why in (
        ([("P_1", nfl), ("P_1", afl)], False, "two leagues are two selections, not a fold"),
        ([("P_1", reg), ("P_1", alloc)], False, "a draft and an allocation draft are two"),
        ([("P_1", nfl), ("P_1", unstated)], False, "an unstated league is silence, not a difference"),
        ([("P_1", nfl), ("P_1", dict(nfl))], False, "one selection stated twice is one selection"),
        ([("P_1", ordered), ("P_1", numbered_nokind)], False,
         "an ordered selection and a numbered one are two, on kind"),
        ([("P_1", ordered_nokind), ("P_1", numbered_nokind)], False,
         "and still two when NEITHER states a kind -- the structural check"),
        ([("P_1", ordered), ("P_1", dict(ordered))], False,
         "one ordered selection stated twice is one selection"),
        ([], True, "zero claims is refused, not passed over"),
    ):
        f, _ = run(rows=rows, quiet=True)
        print(f"     {'PASS' if bool(f) == want else 'FAIL'}  {why}")
        ok &= bool(f) == want
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(0 if selftest() else 1)
    print("SELF-TEST first -- the gate must be seen to fail:")
    if not selftest(): raise SystemExit("self-test failed; the gate's verdict means nothing")
    print()
    fails, _ = run()
    print()
    if fails:
        print("DRAFT KEY GATE: FAIL")
        for x in fails: print("   -", x)
        raise SystemExit(1)
    print("DRAFT KEY GATE: pass")
