"""Decide which player leads become people. Mirrors promote_coaches.py.

ONE MECHANISM, TWO SUBJECT TYPES. The coach route already answers every question
this one has -- how an id is minted, how it stays stable across runs, what the
decision record holds, how it is undone -- so this follows it rather than
inventing a second shape. The differences are two, and both are forced:

  * A COACH'S SEASONS COME FROM THE APPLIER, because no claim produces them. A
    PLAYER'S COME FROM CLAIMS: resolve_person() returns any `P_` id as itself, so
    a claim naming a freshly minted id builds the person's seasons the ordinary
    way. This route therefore mints the id and the ingest writes the seasons.
  * A player must QUALIFY. The coach route promotes a lead that names a coaching
    season; this one refuses most of what it is handed.

THE STANDING RULE: a person is someone who PLAYED, COACHED OR OFFICIATED at least
one season. So a player named on a ROSTER for a club-season THE ARCHIVE HOLDS
qualifies. A training-camp list or a transaction does NOT -- signed is not rostered,
and a camp list is who was invited. Those stay leads.

A TEAM PHOTOGRAPH QUALIFIES, narrowly. Ryan's ruling of 2026-09-08, stated as a
property and not as an instance: a man named in the caption to a team photograph,
where the CAPTION NAMES THE CLUB and the CLUB-SEASON IS ONE THE ARCHIVE HOLDS.
All three or nothing -- a name in a photograph of something else is not covered.
The reason is that PFA's box scores only see men who STARTED, so a club-season with
no roster excludes its squad by a gap in the evidence rather than by evidence of
absence. THE PREDICATE DOES NOT MOVE: `programme.team_photograph` is not roster
membership and does not become it. He becomes a person; the claim keeps saying he
was photographed with the club, not that he played.

  python3 src/promote_players.py [--write]
"""
import os, re, sys, json, glob, unicodedata, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
from readings import person_name as _person_name
OUT = os.path.join(BASE, "build", "player-promotions.json")
DECL = os.path.join(BASE, "declarations", "player-promotions.json")

# Evidence kinds that are a ROSTER. Anything else is refused, by name, so a new
# lead shape is refused by default rather than promoted by accident.
# DECLARED, NOT TYPED, since 2026-09-09. The set was written out here, which is the
# classification-by-string pattern this archive keeps meeting: a vocabulary in code
# cannot be ruled on, only edited, and Ryan's ruling that a printed roster IS a roster
# had nowhere to live. declarations/player-promotions.json _roster_evidence_kinds is
# the list, and the refusal by default is unchanged and is the point.
def _roster_kinds():
    d = json.load(open(DECL)).get("_roster_evidence_kinds")
    if not d or "kinds" not in d:
        raise PromoteError("declarations/player-promotions.json declares no roster evidence "
                           "kinds. Refusing to fall back to a typed set: the declaration is "
                           "the rule.")
    return set(d["kinds"])
# A team photograph is not a roster and never becomes one. It is a SEPARATE qualifying
# kind with its own conditions, so that widening it later means changing this rule
# rather than quietly reclassifying a photograph as a roster.
TEAM_PHOTOGRAPH = "team_photograph"
NOT_A_ROSTER = {
    "boxscore_lineup": "a boxscore-derived membership is already a playing season; a lead "
                       "from one means the man did NOT resolve, which is an identity "
                       "question and not a promotion",
    "transaction": "signed is not rostered, and the archive rules them apart",
    "training_camp": "a camp list is who was invited, not who played",
}


class PromoteError(Exception):
    pass


_INITIAL = re.compile(r"^[A-Za-z]\.?$")


def forename_unknown(nm):
    """True where the document does not give a forename. Two shapes, one meaning.

    A bare surname -- `Bucklin` -- was the only one this handled. A caption that sets
    `D. Carey` does not give a forename either: `D.` is an initial, and the man's
    forename is as lost as if the caption had printed nothing. Ryan's instruction of
    2026-09-08, keeping the flag where a caption gives only an initial.

    The flag matters because a later source completing one of these men must be able
    to FIND him rather than mint a second record beside him."""
    t = str(nm or "").strip().rstrip(",")
    if not t:
        return False
    parts = t.split()
    if len(parts) == 1:
        return True                      # a surname and nothing else
    return bool(_INITIAL.match(parts[0]))   # an initial where the forename should be


def norm(s):
    """THE one name reading -- readings.person_name. This file used to carry
    its own copy, and the copies disagreed on apostrophes, initials, hyphens
    and suffixes across about 1,200 names."""
    return _person_name(s)


def new_person_id(IDX, taken):
    """Same rule as promote_coaches.new_person_id: one past the highest held id,
    never reusing one, and never colliding with an id minted earlier in this run."""
    n = max([int(k[2:]) for k in IDX if k.startswith("P_") and k[2:].isdigit()] or [0])
    n = max(n, max([int(t[2:]) for t in taken if t[2:].isdigit()] or [0]))
    return f"P_{n + 1:06d}"


def load_leads():
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for L in (d.get("leads") or []):
            if isinstance(L, dict) and L.get("category", "").startswith("player_lead"):
                yield st, L


def held_club_seasons(IDX):
    """-> a predicate: does the archive hold this club-season?

    THE CLUB TABLE IS ASKED FIRST, ruled 2026-09-09. This counted men in the index and
    called a club-season with none "not a club-season yet", which made an EMPTY
    club-season unfillable forever -- the first man onto it could never be promoted,
    because he would be the first. Frankford 1899, 1900, 1903 and 1906 are held by the
    club table and by nothing else."""
    from clubs import Clubs
    C = Clubs()
    n = collections.Counter()
    for p in IDX.values():
        if not isinstance(p, dict): continue
        for k in (p.get("seasons") or {}): n[k] += 1

    def holds(cs):
        if n.get(cs): return True
        parts = str(cs).split("|", 2)
        if len(parts) != 3: return False
        lg, y, tok = parts
        y = str(y).lstrip("y")
        if not y.isdigit(): return False
        r = C.resolve(tok, int(y), None, source="season_key")
        return bool(r and C.name_for(r[0], int(y)))
    return holds


def qualify(lead, held):
    """-> (bool, reason). Refuses by default: an evidence kind this does not know
    is not a roster until somebody says it is."""
    ev = lead.get("evidence_kind")
    if ev in NOT_A_ROSTER:
        return False, f"not a roster -- {NOT_A_ROSTER[ev]}"
    photo = ev == TEAM_PHOTOGRAPH
    if not photo and ev not in _roster_kinds():
        return False, (f"evidence kind {ev!r} is not declared as a roster. A lead shape "
                       "this route does not know is refused, not promoted.")
    on = lead.get("places_on") or {}
    cs = on.get("club_season")
    if not cs:
        return False, ("the document places him on no club-season the archive holds -- "
                       "a club held for one game only has no club-season, by ruling")
    if not held(cs):
        return False, (f"neither the club table nor the index knows {cs}, so it is not a "
                       "club-season at all")
    if photo:
        # THE CAPTION MUST NAME THE CLUB. Without it this is a man in a photograph of
        # something, and the ruling does not reach that. Checked as a property: the
        # lead has to carry the club the caption printed, not merely a club code the
        # ingest worked out.
        if not str(on.get("club_as_printed") or "").strip():
            return False, ("a team-photograph lead whose caption does not name the club. "
                           "The ruling of 2026-09-08 covers a TEAM photograph that "
                           "identifies its club; a name in a photograph of something "
                           "else is not covered.")
        return True, (f"named in the caption to a team photograph of {on['club_as_printed']!r} "
                      f"on {cs}, which the archive holds (ruling of 2026-09-08). This is NOT "
                      "roster membership and the claim about him does not say it is.")
    return True, f"named on a roster for {cs}, which the archive holds"


def main(write=False):
    IDX = IO.load_index(); IDX.pop("_clubs", None)
    held = held_club_seasons(IDX)
    byname = collections.defaultdict(list); bysur = collections.defaultdict(list)
    for pid, p in IDX.items():
        if isinstance(p, dict) and p.get("name"):
            byname[norm(p["name"])].append(pid)
            bysur[norm(p["name"]).split()[-1]].append(pid)
    # THE DECISION STORE IS CUMULATIVE. Once a man is promoted the ingest writes claims
    # for him and he stops being a lead -- so re-deciding from the leads alone would drop
    # him, and the next rebuild would strip his entered_by and forename_unknown. A
    # decision, once made, stays in the record. coach-promotions.json holds all 1,799 the
    # same way.
    # AND SEEDED FROM THE INDEX, which is the base state. If the decision store is lost
    # or rewritten, a man already promoted must get HIS id back and not a fresh one --
    # otherwise the old id is orphaned in the index and he becomes two people. Keyed on
    # the normalised name, which is what the ingest joins on.
    prior_by_name = {}
    for pid, r in IDX.items():
        if isinstance(r, dict) and r.get("_entered_as_a_player") and r.get("name"):
            prior_by_name[norm(r["name"])] = pid
    prior, prior_rows = {}, []
    if os.path.exists(OUT):
        for p in json.load(open(OUT))["promotions"]:
            prior[(p["source"], p["reversible"]["lead_ref"])] = p["person_id"]
            prior_rows.append(p)

    prom, refused, ambiguous = [], [], []
    assigned, seen = set(), {}
    for st, L in load_leads():
        ok, why = qualify(L, held)
        nm = L.get("name_as_printed") or ""
        row = {"store": st, "lead_ref": L.get("lead_id"), "name_as_printed": nm, "why": why}
        if not ok:
            refused.append(row); continue
        # NO BATCH APPROVAL. Ryan's ruling of 2026-09-08: a qualifying man is promoted.
        # The scope keys that used to sit here are gone on purpose -- a scope key is how a
        # standing rule quietly becomes a queue again, and the queue only grows.
        k = norm(nm)
        if len(byname.get(k, [])) == 1:
            refused.append({**row, "why": "already held: one person carries this exact name"}); continue
        if len(byname.get(k, [])) > 1:
            ambiguous.append({**row, "held_candidates": byname[k],
                              "why": "REFUSED: more than one held person carries this exact "
                                     "name. Choosing between them is a per-man judgement "
                                     "this document cannot make."}); continue
        if k in seen:                                   # same man on two seasons
            pid = seen[k]
        else:
            pid = (prior.get((st, L.get("lead_id"))) or prior_by_name.get(k)
                   or new_person_id(IDX, assigned))
            assigned.add(pid); seen[k] = pid
        sur = k.split()[-1] if k else ""
        surname_only = forename_unknown(nm)
        existing = next((p for p in prom if p["person_id"] == pid), None)
        season = {"league": (L["places_on"].get("club_season") or "||").split("|")[0],
                  "year": L["places_on"].get("year"),
                  "club": (L["places_on"].get("club_season") or "||").split("|")[-1],
                  "club_as_printed": L["places_on"].get("club_as_printed")}
        if existing:
            existing["playing_seasons"].append(season); continue
        prom.append({
            "person_id": pid, "name": nm, "source": f"{st}-player-lead",
            "entered_by": "promotion_from_lead",
            "_not_a_lesser_class": "an honest record of how he entered, not a lower tier",
            "playing_seasons": [season],
            "identified_by": {"name_as_printed": nm,
                              "club_as_printed": L["places_on"].get("club_as_printed"),
                              "lists": [L.get("source_record")]},
            "no_archive_match_evidence": {"checked": [
                {"test": "exact normalised name across the whole archive", "matches": 0, "ids": []},
                {"test": "same surname held anywhere", "surname": sur,
                 "same_surname": len(bysur.get(sur, [])), "ids": bysur.get(sur, [])[:6],
                 "note": "a shared surname is not this man; recorded so the refusal can be "
                         "re-checked, not as a match"}]},
            # THE FLAG MUST SURVIVE INTO THE PERSON RECORD. Four of these men are a
            # surname and nothing else -- real people whose forenames are lost, not
            # defects. A later source completing one must be able to find him rather
            # than mint a second record beside him.
            "forename_unknown": surname_only,
            "reversible": {"undo": "delete this person_id and restore the lead",
                           "lead_ref": L.get("lead_id"),
                           "source_record": L.get("source_record")},
            "source_record": L.get("source_record"),
            "why": why})

    # carry forward every decision whose man is no longer a lead, because he was promoted
    have = {p["person_id"] for p in prom}
    carried = [p for p in prior_rows if p["person_id"] not in have]
    for p in carried: p.setdefault("_carried_forward",
        "promoted in an earlier run; he is no longer a lead because the ingest now writes "
        "claims for him. The decision stands.")
    prom = carried + prom
    out = {"_what": "PLAYER promotions. Mirrors build/coach-promotions.json.",
           "_rule": "a person is someone who played, coached or officiated at least one "
                    "season. A player named on a ROSTER for a club-season the archive "
                    "holds qualifies, and so does a man named in the caption to a TEAM "
                    "PHOTOGRAPH that names its club, on a club-season the archive holds "
                    "(Ryan, 2026-09-08). A transaction or a camp list does not. The "
                    "photograph predicate stays what it was and never becomes roster "
                    "membership.",
           "decided_at": datetime.date.today().isoformat(),
           "promotions": prom, "refusals": refused, "ambiguous": ambiguous,
           "_ambiguous_and_refused_go_to_ryan": "the rule cannot make these judgements; "
               "they are reported and never promoted",
           "counts": {"promotions": len(prom), "refused": len(refused),
                      "ambiguous": len(ambiguous),
                      "carried_forward_from_earlier_runs": len(carried),
                      "forename_unknown": sum(1 for p in prom if p.get("forename_unknown")),
                      "playing_seasons": sum(len(p.get("playing_seasons") or []) for p in prom)}}
    if write:
        IO.dump_atomic(out, OUT, indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    c = o["counts"]
    print(f"promotions {c['promotions']} ({c['forename_unknown']} with no forename), "
          f"{c['playing_seasons']} playing seasons")
    print(f"refused {c['refused']}   ambiguous {c['ambiguous']} (both go to Ryan)")
    rc = collections.Counter(r["why"].split(" -- ")[0].split(",")[0] for r in o["refusals"])
    print("\nrefusals by reason:")
    for k, v in rc.most_common(8): print(f"   {v:>3}  {k[:80]}")
