"""The person rule for a man a document names in a role at a club (Ryan, 2026-09-13).

ONE IMPLEMENTATION, used by every ingest that holds club_staff_role lines (the Frankford
site and the Football Hunting photographs). Each ingest supplies its own reading of the
club-season's roster; the rule that decides a join is here and nowhere else.

A staff line joins a held man only on the club-season it names:
  1. his exact name on that roster (the one name reading, readings.person_name);
  2. otherwise a surname unique on that roster whose first forename does not contradict --
     an initial agrees with a name it begins. This is the 2026-09-11 surname rule; two men
     of the surname refuse.
Anything else becomes a LEAD of category `staff_lead`, which promote_players decides. The
club_staff_role claim itself stays on the club-season and names no person (ruling Four);
a joined or promoted man gets a SECOND, person-scoped claim saying which club-season.
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
from readings import person_name as _pn

DECL = json.load(open(os.path.join(BASE, "declarations", "player-promotions.json")))["staff_role_evidence"]
KIND, CATEGORY = DECL["evidence_kind"], DECL["lead_category"]
PROMOTED_TIER = "this ingest's own staff lead, promoted by promote_players.py -- the exact printed name on the exact club-season"


def toks(s):
    return _pn(s or "").split()


def forename_agrees(a, b):
    """First forename of two token lists: an initial agrees with a name it begins."""
    if len(a) < 2 or len(b) < 2: return False
    x, y = a[0], b[0]
    if len(x) == 1 or len(y) == 1: return x[0] == y[0]
    return x == y


def join(name, roster):
    """-> (tier, pid, evidence). `roster`: iterable of (pid, [names held for him])."""
    t = toks(name)
    roster = [(p, [n for n in ns if n]) for p, ns in roster]
    exact = {p for p, ns in roster if any(_pn(n) == _pn(name) for n in ns)}
    if len(exact) == 1:
        p = next(iter(exact)); return "exact name on the club-season", p, "his exact name is on the club-season's roster"
    if len(exact) > 1:
        return None, None, "two men of this exact name on the club-season: refused"
    if len(t) < 2:
        return None, None, "a bare surname: joined to nobody"
    same = {p: ns for p, ns in roster if any(toks(n) and toks(n)[-1] == t[-1] for n in ns)}
    if len(same) > 1:
        return None, None, f"{len(same)} men named {t[-1]!r} on the club-season: refused, both (Ryan, 2026-09-11)"
    if len(same) == 1:
        p, ns = next(iter(same.items()))
        if any(forename_agrees(t, toks(n)) for n in ns):
            return ("surname unique on the club-season, forename agreeing", p,
                    f"the one {t[-1]!r} on the roster is {ns[0]!r}, and the forenames agree")
        return None, None, f"the one {t[-1]!r} on the roster is {ns[0]!r}; the forename contradicts, so not this man"
    return None, None, "no man of this name or surname on the club-season"


def lead(lead_id, name, role, club_as_printed, club_season, year, source_id, source_record, why):
    return {"lead_id": lead_id, "category": CATEGORY, "IS_NOT_A_PERSON": True,
            "evidence_kind": KIND, "name_as_printed": name, "role_as_printed": role,
            "places_on": {"club_as_printed": club_as_printed, "year": year, "club_season": club_season},
            "source_id": source_id, "source_record": source_record, "why_not_joined": why,
            "_ruling": DECL["_ruled"]}


def promoted_staff(source_prefix):
    """(normalised name, year, club code) -> the person promote_players minted from a staff lead
    of this source. A staff decision records `staff_seasons`."""
    p = os.path.join(BASE, "build", "player-promotions.json")
    if not os.path.exists(p):
        raise SystemExit("REFUSING: build/player-promotions.json is absent; staff promotions are read from it")
    out = {}
    for d in json.load(open(p)).get("promotions") or []:
        if not str(d.get("source", "")).startswith(source_prefix): continue
        for s in d.get("staff_seasons") or []:
            out[(_pn(d.get("name")), int(s["year"]), s["club"])] = d["person_id"]
    return out
