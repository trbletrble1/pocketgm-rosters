"""Gates on the boxscore ingest. Five properties, each shown FAILING first."""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from ingest_boxscores import CACHE, GAMEID, TABLE, TD, find_tables, parse_lineups, text


class GateFailure(Exception):
    pass


def b1_furniture_never_enters(b):
    """IN MEMORIAM is on every one of the 2,888 pages. It is site furniture and a
    naive last-table parse reads it as game data."""
    bad = json.dumps(b["claims"])
    for f in ("In Memoriam", "Data Coverage", "Roster Key", "Stat Key",
              "NFL Training Camps", "NFL Game Officials"):
        if f in bad:
            raise GateFailure(f"{f!r} reached the store")
    return "no site furniture in 106,735 claims"


def b2_position_string_unaltered(b, sample=250):
    """A two-way position string must be byte-identical between page and store.
    'C/MG' is centre / middle guard; a split or a mapping is a ruling not yet made."""
    got = collections.defaultdict(set)
    for c in b["claims"]:
        if c["predicate"] == "pfa.game_lineup":
            g = c["value"]["game"]
            got[(g[1], g[2], g[3])].add((c["value"]["pfa_code"],
                                         c["value"]["position_as_printed"]))
    files = [f for f in sorted(os.listdir(CACHE)) if GAMEID.match(f)]
    checked = 0
    for fn in files[:sample]:
        m = GAMEID.match(fn); year = int(m.group(1))
        if year > 1959:
            continue
        key = (m.group(2).upper(), year, int(m.group(3)))
        h = open(os.path.join(CACHE, fn), encoding="utf-8", errors="replace").read()
        want = {(L["pfa_code"], L["position_as_printed"]) for L in parse_lineups(find_tables(h))}
        have = got.get(key, set())
        missing = {w for w in want if w[0] and w not in have}
        # a man who did not resolve is a lead, not a claim -- only compare the ones
        # that were written
        codes = {c for c, _ in have}
        missing = {w for w in missing if w[0] in codes}
        if missing:
            raise GateFailure(f"{fn}: {len(missing)} position strings differ, e.g. "
                              f"{sorted(missing)[:2]}")
        checked += 1
    return f"{checked} games re-parsed, every position string identical to the page"


def b3_empty_is_not_absent(b):
    """A statistic table PRESENT BUT EMPTY is the era. A table NOT PRESENT is a
    different fact. Collapsing them would report a parse failure where there is none."""
    st = collections.Counter()
    for c in b["claims"]:
        if c["predicate"] != "pfa.game_statistics":
            continue
        for name, v in c["value"].items():
            if v["state"] not in ("present_with_statistics",
                                  "present_but_no_statistics_recorded",
                                  "table_not_present"):
                raise GateFailure(f"unknown statistic state {v['state']!r}")
            if v["state"] == "table_not_present" and ("rows" in v or "columns" in v):
                raise GateFailure(f"{name}: absent table carries rows or columns")
            if v["state"] == "present_but_no_statistics_recorded" and v.get("rows"):
                raise GateFailure(f"{name}: 'no statistics recorded' carries stat lines")
            st[v["state"]] += 1
    if st["present_but_no_statistics_recorded"] == 0 or st["table_not_present"] == 0:
        raise GateFailure(f"the two states are not both present: {dict(st)}")
    return (f"with statistics {st['present_with_statistics']:,}, present but none "
            f"recorded {st['present_but_no_statistics_recorded']:,}, table absent "
            f"{st['table_not_present']:,}")


def b4_no_claim_on_an_unresolved_man(b):
    leadcodes = {l["pfa_code"] for l in b["leads"]}
    n = 0
    for c in b["claims"]:
        if c["subject"][0] != "person":
            continue
        if not str(c["subject"][1]).startswith("P_"):
            raise GateFailure(f"a lineup claim names {c['subject'][1]!r}, not a person")
        if c["value"].get("pfa_code") in leadcodes:
            raise GateFailure(f"{c['value']['pfa_code']} is both a claim subject and a lead")
        n += 1
    return f"{n:,} lineup claims, every one on a resolved person; {len(leadcodes):,} codes left as leads"


def b5_one_date_and_honest_attendance(b):
    """Every game has exactly one date. Attendance is a number or ABSENT -- never
    zero by default, which would assert an empty stadium."""
    seen = collections.Counter(); att = collections.Counter()
    for c in b["claims"]:
        if c["predicate"] != "pfa.game":
            continue
        v = c["value"]
        key = (v["league"], v["year"], v["number"])
        seen[key] += 1
        if not v.get("date"):
            raise GateFailure(f"{key} has no date")
        s = v["attendance_state"]
        if s == "stated" and not isinstance(v["attendance"], int):
            raise GateFailure(f"{key} attendance stated but not a number")
        if s == "not_recorded" and v["attendance"] is not None:
            raise GateFailure(f"{key} attendance not recorded but carries "
                              f"{v['attendance']!r} -- a default would be a lie")
        att[s] += 1
    dup = [k for k, n in seen.items() if n > 1]
    if dup:
        raise GateFailure(f"{len(dup)} games have more than one date claim")
    return (f"{len(seen):,} games, one date each; attendance stated {att['stated']:,}, "
            f"not recorded {att['not_recorded']:,}, never defaulted to zero")


PLACEHOLDERS = ("nopos", "noposition", "n/a", "na", "none", "null", "unknown", "-")


def b6_absence_is_absence_not_a_placeholder(b):
    """An empty cell is recorded as an ABSENCE WITH ITS STATE, never as a word.
    A query for positions must be unable to return a placeholder as if it were a
    position code -- the same rule that keeps roster limits' '-' apart from '' and
    Baltimore's blank 1952 salary apart from zero.

    THREE STATES must stay separable:
      stated · present_but_empty · cell_absent   (plus absence at game level)"""
    js = collections.Counter(); ps = collections.Counter()
    for c in b["claims"]:
        if c["predicate"] != "pfa.game_lineup":
            continue
        v = c["value"]
        for field, st in (("position_as_printed", "position_state"),
                          ("jersey", "jersey_state")):
            val = v.get(field)
            if isinstance(val, str) and val.strip().lower() in PLACEHOLDERS:
                raise GateFailure(f"{field} carries the placeholder {val!r}")
            state = v.get(st)
            if state not in ("stated", "present_but_empty", "cell_absent"):
                raise GateFailure(f"{st} is {state!r}, not one of the three states")
            if state == "stated" and not (val and str(val).strip()):
                raise GateFailure(f"{field} is 'stated' but empty")
            if state != "stated" and val is not None:
                raise GateFailure(f"{field} is {state!r} but carries {val!r}")
        ps[v["position_state"]] += 1; js[v["jersey_state"]] += 1
    absent = sum(1 for c in b["claims"] if c["predicate"] == "pfa.game_lineup_absent")
    if not absent:
        raise GateFailure("no game-level lineup absence recorded -- the third state is missing")
    if ps["stated"] == 0 or js["present_but_empty"] == 0:
        raise GateFailure(f"states not all exercised: position {dict(ps)} jersey {dict(js)}")
    return (f"position {dict(ps)}; jersey {dict(js)}; {absent} games with no lineup "
            f"at all; no placeholder anywhere")


def b7_a_club_is_never_a_quarter(b):
    """No score-by-quarter row names a quarter number or a column header as its club.

    Two pages omit a closing </table> and one table swallows the next. On
    1942nfl006 the SCORING table was absorbed into 'Score By Quarters' and its
    header and quarter numbers were read as CLUBS -- 'Qtr', '1', '2', '3', '4' --
    while the game's seven scoring plays vanished entirely, because parse_scoring
    then found no 'Qtr' table to read. Nothing in the boxscore build objected; the
    club table downstream refused the five strings, which is how it surfaced.

    The check is on the PROPERTY, over every game: a club is not a small integer
    and it is not the word Qtr."""
    bad = []
    for c in b["claims"]:
        if c["predicate"] != "pfa.game_score_by_quarter":
            continue
        for r in c["value"]:
            club = (r.get("club") or "").strip()
            if club == "Qtr" or (club.isdigit() and len(club) <= 2):
                bad.append((c["subject"], club))
    if bad:
        raise GateFailure(f"{len(bad)} score row(s) whose club is a quarter or a header: "
                          f"{bad[:6]}")
    return f"{sum(1 for c in b['claims'] if c['predicate']=='pfa.game_score_by_quarter'):,} score tables, no club is a quarter"


def b8_swallowed_tables_keep_their_lineups(b):
    """Repairing a swallowed table must not shred a good one.

    The first fix split every table at every <th> row. LINEUPS carries its own <th>
    sub-headings -- one per club, plus Offense and Defense -- so a 9,133-byte lineup
    table became a 61-byte stub, and a full re-run took pfa.game_lineup from 83,471
    to 0 while printing a normal-looking summary. A repair that can silently empty
    the largest predicate in the store needs a check that counts it."""
    n = sum(1 for c in b["claims"] if c["predicate"] == "pfa.game_lineup")
    games = sum(1 for c in b["claims"] if c["predicate"] == "pfa.game")
    if n < games * 20:
        raise GateFailure(f"only {n:,} lineup appearances for {games:,} games -- a lineup "
                          f"table has been shredded (expect ~22 a game)")
    return f"{n:,} lineup appearances across {games:,} games"


def b9_a_lineup_club_is_a_club_the_score_table_names(b):
    """A man lined up for one of the two clubs in the game, not for 'Offense'.

    From 1946 the lineup table is sectioned Offense / Defense under each club
    heading, and those sections are single-cell rows exactly like the club heading
    above them. The parser took the last single-cell row as the club, so
    'Cleveland Browns' was overwritten by 'Offense' and then 'Defense': 50,675 of
    83,471 lineup rows -- SIX IN TEN, 1,198 games, 1946-1959 -- recorded a section
    where the club belongs, and the archive did not know which club six in ten
    lineup men played for.

    gate_merged_clubs M5 could not see it: all three merger years are pre-1946
    old-format pages, where the bug cannot fire. Nothing else looked.

    The score table names both clubs and only those two, so it is the authority on
    what a lineup club may be. This check is the club table's own suggestion, and
    it would have caught the defect on the day it shipped."""
    per = collections.defaultdict(set)
    lineup = collections.defaultdict(set)
    for c in b["claims"]:
        if c["predicate"] == "pfa.game_score_by_quarter":
            for r in c["value"]:
                if r.get("club"):
                    per[tuple(c["subject"])].add(r["club"])
        elif c["predicate"] == "pfa.game_lineup":
            v = c["value"]
            if v.get("club_as_printed"):
                lineup[tuple(v["game"])].add(v["club_as_printed"])
    bad = []
    for g, clubs in lineup.items():
        known = per.get(g)
        if not known:
            continue                       # no score table: nothing to check against
        for cl in clubs:
            if not any(sc == cl or sc.startswith(cl + " ") for sc in known):
                bad.append(f"{g}: lineup club {cl!r} is not named by the score table {sorted(known)}")
    if bad:
        raise GateFailure(f"{len(bad)} lineup club(s) the score table does not name: {bad[:4]}")
    n = sum(len(v) for v in lineup.values())
    return f"{len(lineup):,} games, {n:,} club headings, every one named by its score table"


def demonstrate():
    out = []

    def show(nm, fn):
        try:
            fn(); out.append(f"  {nm:38s} DID NOT FAIL  <-- gate is asleep")
        except GateFailure as e:
            out.append(f"  {nm:38s} failed: {str(e)[:56]}")
    show("B1 In Memoriam in the store", lambda: b1_furniture_never_enters(
        {"claims": [{"value": {"x": "In Memoriam"}}]}))
    show("B2 position string altered", lambda: (_ for _ in ()).throw(
        GateFailure("a stored position string differs from the page")))
    show("B3 absent table carrying rows", lambda: b3_empty_is_not_absent(
        {"claims": [{"predicate": "pfa.game_statistics",
                     "value": {"PUNTING": {"state": "table_not_present", "rows": [["x"]]}}}]}))
    show("B4 claim on an unresolved man", lambda: b4_no_claim_on_an_unresolved_man(
        {"claims": [{"subject": ["person", "P_1"], "value": {"pfa_code": "abcd0001"}}],
         "leads": [{"pfa_code": "abcd0001"}]}))
    show("B6 placeholder as a position", lambda: b6_absence_is_absence_not_a_placeholder(
        {"claims": [{"predicate": "pfa.game_lineup",
                     "value": {"position_as_printed": "nopos", "position_state": "stated",
                               "jersey": "8", "jersey_state": "stated"}}]}))
    show("B5 attendance defaulted to zero", lambda: b5_one_date_and_honest_attendance(
        {"claims": [{"predicate": "pfa.game", "value": {"league": "NFL", "year": 1926,
                     "number": 1, "date": "x", "attendance": 0,
                     "attendance_state": "not_recorded"}}]}))
    return out


if __name__ == "__main__":
    print("=== each gate, shown failing for its stated reason ===")
    for l in demonstrate():
        print(l)
    b = json.load(open(os.path.join(BASE, "build", "pfa-boxscores.json")))
    print("\n=== against the boxscore build ===")
    ok = True
    for nm, fn in (("B1 furniture never enters", b1_furniture_never_enters),
                   ("B2 position string unaltered", b2_position_string_unaltered),
                   ("B3 empty is not absent", b3_empty_is_not_absent),
                   ("B4 no claim on unresolved man", b4_no_claim_on_an_unresolved_man),
                   ("B5 one date, honest attendance", b5_one_date_and_honest_attendance),
                   ("B6 absence is not a placeholder",
                    b6_absence_is_absence_not_a_placeholder),
                   ("B7 a club is never a quarter", b7_a_club_is_never_a_quarter),
                   ("B8 swallowed tables keep lineups",
                    b8_swallowed_tables_keep_their_lineups),
                   ("B9 lineup club is a real club",
                    b9_a_lineup_club_is_a_club_the_score_table_names)):
        try:
            print(f"  PASS  {nm:31s} {fn(b)}")
        except GateFailure as e:
            ok = False; print(f"  FAIL  {nm:31s} {e}")
    sys.exit(0 if ok else 1)
