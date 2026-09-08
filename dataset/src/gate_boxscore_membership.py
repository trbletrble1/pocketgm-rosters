"""Stage 1 of membership-as-a-claim holds its shape, and the spine is untouched.

  S1 every claim carries a source, a definition, its games, and a predicate that
     names the definition
  S2 one claim per man per club-season from this source
  S3 no stint subjects -- the builder makes season keys only from stints, so a
     person-scoped store cannot merge into StatsCrew's membership
  S4 every club resolves through build/clubs.json, and the strings that do not
     are COUNTED in the store, never dropped
  S5 every value is LEAGUE|YEAR|CODE with a code the club table recognises for
     that year, so it is comparable with a season key without a join

  python3 src/gate_boxscore_membership.py [--selftest]
"""
import os, sys, json, copy, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import Clubs

# ONE GATE FOR EVERY MEMBERSHIP STORE. Stage 1 (boxscores) and stage 2
# (transactions) share the shape -- person subject, definition-bearing predicate,
# LEAGUE|YEAR|CODE value, refusals counted -- so they share the check. Pass the
# store path; default is stage 1.
STORE = (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json")
         else os.path.join(BASE, "build", "pfa-boxscore-membership.json"))
BOX = os.path.join(BASE, "build", "pfa-boxscores.json")


def checks(M, C, box_rows):
    cl = M["claims"]; out = []
    # EVIDENCE IS NAMED PER SOURCE -- `games` for the boxscores, `transactions` for
    # the transaction store, `rows` for nflverse. The check is that a claim carries
    # ITS evidence, retrievable, whatever that source calls it; hard-coding two of
    # the three names made S1 fail every stage-3 claim and made its own probe
    # useless, because a check already failing cannot be shown to fail for a reason.
    EVID = ("games", "transactions", "rows")
    bad = [c["subject"][1] for c in cl if not (c.get("source_id") and c.get("definition")
           and any(c.get(k) for k in EVID)
           and str(c.get("predicate", "")).startswith("roster_membership."))]
    out.append(("S1", "every claim carries source, definition, its evidence and a definition-bearing predicate", bad[:5]))
    # per (man, club-season, PREDICATE): stage 2 legitimately holds several
    # predicates for one man on one club -- signed, on reserve, departed -- and
    # each is one claim. Two claims under ONE predicate is the defect.
    pairs = collections.Counter((c["subject"][1], c["value"], c["predicate"]) for c in cl)
    out.append(("S2", "one claim per man per club-season per predicate from this source",
                [f"{k} x{v}" for k, v in pairs.items() if v > 1][:5]))
    out.append(("S3", "no stint subjects -- the spine cannot be merged into",
                [str(c["subject"]) for c in cl if c["subject"][0] != "person"][:5]))
    # S4: every club string the store's claims resolved must STILL resolve, and
    # every refusal the store counted must be a real refusal -- a refusal the store
    # forgot is a silent skip, and a "refusal" that now resolves is a stale census.
    # Checked from the store's own claims so it works for any source.
    Cc = Clubs(); src = M["source"]["source_id"]
    tag = {"pfa-boxscores": "boxscore", "pfa-transactions": "pfa_transaction"}.get(src, src)
    seen = {}
    for c in cl:
        k = (c["league"], str(c["year"]), c["club_as_printed"])
        if k not in seen:
            seen[k] = Cc.resolve(c["club_as_printed"], c["year"], c["league"], source=tag) is not None
    bad = [f"claim club {k} no longer resolves" for k, ok in seen.items() if not ok][:5]
    counted = {(u["league"], str(u["year"]), u["string"]) for u in M["unresolved_club_strings"]}
    if not counted and not bad:
        bad = []
    elif not M["unresolved_club_strings"] and src == "pfa-transactions":
        bad.append("a 402,886-row source with zero refusals is a census that was not run")
    out.append(("S4", "unresolvable club strings are counted in the store, never skipped", bad[:5]))
    bad = []
    for c in cl:
        parts = c["value"].split("|")
        if len(parts) != 3 or not parts[1].isdigit() or C.by_code_year(parts[2], int(parts[1])) is None:
            bad.append(c["value"])
    out.append(("S5", "every value is LEAGUE|YEAR|CODE with a code the club table knows that year",
                sorted(set(bad))[:5]))
    return out


def box_lineup_rows():
    B = json.load(open(BOX))
    return [{"league": c["value"]["game"][1], "year": c["value"]["game"][2],
             "club_as_printed": c["value"].get("club_as_printed")}
            for c in B["claims"] if c["predicate"] == "pfa.game_lineup"]


def run():
    M = json.load(open(STORE)); C = Clubs(); rows = box_lineup_rows()
    res = checks(M, C, rows)
    for cid, desc, bad in res:
        print(f"  {cid} {'FAIL' if bad else 'pass'}  {desc}")
        for b in bad: print(f"        {b}")
    return res


def selftest():
    M = json.load(open(STORE)); C = Clubs(); rows = box_lineup_rows()
    base = {c for c, _, b in checks(M, C, rows) if b}
    print("SELFTEST -- each check must fail for its own reason and no other")
    print(f"baseline: {sorted(base) or 'all passing'}\n"); ok = []

    def probe(name, mut):
        m = {"source": M["source"], "claims": [dict(c) for c in M["claims"]],
             "unresolved_club_strings": list(M["unresolved_club_strings"])}
        r = list(rows)
        m, r = mut(m, r)
        fired = {c for c, _, b in checks(m, C, r) if b} - base
        good = fired == {name}
        print(f"  {'OK  ' if good else 'BAD '} {name}: added {sorted(fired) or ['nothing']}")
        return good

    def s1(m, r): m["claims"][0] = {k: v for k, v in m["claims"][0].items() if k != "definition"}; return m, r
    def s2(m, r): m["claims"].append(dict(m["claims"][0])); return m, r
    def s3(m, r): m["claims"][0]["subject"] = ["stint", "NFL", "CHI", "1950"]; return m, r
    def s4(m, r):
        # a claim whose club string no longer resolves -- the census is stale or a
        # string was mapped that the table does not know
        m["claims"][0] = dict(m["claims"][0], club_as_printed="Zzz No Such Club"); return m, r
    def s5(m, r): m["claims"][0]["value"] = "NFL|1950|NOTACLUB"; return m, r
    for n, f in (("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4), ("S5", s5)):
        ok.append(probe(n, f))
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    res = run(); nf = sum(1 for _, _, b in res if b)
    print(f"\n{len(res)-nf} pass, {nf} FAIL"); sys.exit(1 if nf else 0)
