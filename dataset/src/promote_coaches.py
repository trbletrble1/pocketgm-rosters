"""Promote coaches to people. Reversible, evidenced, and refusing on more than name.

A man who only ever coached has no roster line, so the player-shaped person index
never created him. That is the gap this closes.

THE CHECK THAT MATTERS is not "does this name exist in the archive" -- it is
"could this be someone already in the archive under a different name". The
Coaching Tree carries FORMAL BIRTH NAMES: 'Harold Edward Grange' is Red Grange and
'Ernest Alonzo Nevers' is Ernie Nevers. A full-string comparison says they match
nobody, which is true and useless. Surname plus a compatible given name says they
match somebody, which is what stops a duplicate.

Every promotion records what identified the man and what was checked to rule out
an existing person, so an un-promotion is possible from what is stored.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO       # atomic: a reader sees the old file or the new one, never half of one

DIMINUTIVE = {("bob","robert"),("bill","william"),("dick","richard"),("jim","james"),
              ("hank","henry"),("chuck","charles"),("al","albert"),("joe","joseph"),
              ("jack","john"),("len","leonard"),("ted","edward"),("ned","edward"),
              ("dan","daniel"),("gus","august"),("bert","herbert"),("burt","burton"),
              ("chet","chester"),("ken","kenneth"),("ed","edward"),("mike","michael"),
              ("tom","thomas"),("ray","raymond"),("larry","lawrence"),("laurie","lawrence"),
              ("ernie","ernest"),("pat","patrick"),("art","arthur"),("gene","eugene"),
              ("fred","frederick"),("walt","walter"),("stan","stanley"),("phil","philip"),
              ("sam","samuel"),("nick","nicholas"),("tony","anthony"),("steve","stephen"),
              ("dave","david"),("pete","peter"),("frank","francis"),("harry","harold"),
              ("hal","harold"),("jerry","gerald"),("greg","gregory"),("rick","richard"),
              ("doug","douglas"),("andy","andrew"),("charlie","charles"),("johnny","john"),
              ("tommy","thomas"),("billy","william"),("bobby","robert"),("jimmy","james")}


def norm(n):
    return re.sub(r"[^a-z]", "", (n or "").lower())


def words(n):
    return [w for w in re.sub(r"[^A-Za-z ]", " ", n or "").lower().split() if len(w) > 1]


def given_surname(n):
    w = words(n)
    return (w[0], w[-1]) if len(w) >= 2 else (None, None)


def compatible(a, b):
    """Could these two given names be the same man? Prefixes (Walt/Walter), declared
    diminutives (Bob/Robert), and identity. A NICKNAME IS NOT COVERED -- Red for
    Harold is not derivable -- which is why the surname match alone must be enough
    to refuse."""
    if not a or not b:
        return False
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    return (a, b) in DIMINUTIVE or (b, a) in DIMINUTIVE


class PromotionRefused(Exception):
    pass


def build_index(IDX):
    by_name = collections.defaultdict(list)
    by_surname = collections.defaultdict(list)
    for pid, p in IDX.items():
        if pid == "_clubs" or not p.get("name"):
            continue
        k = norm(p["name"])
        if k:
            by_name[k].append(pid)
        g, s = given_surname(p["name"])
        if s:
            by_surname[s].append(pid)
    return by_name, by_surname


def screen(name, IDX, by_name, by_surname, extra=None):
    """Returns (ok_to_promote, evidence). Evidence is recorded either way."""
    ev = {"name_as_printed": name, "checked": []}
    k = norm(name)
    exact = by_name.get(k, [])
    ev["checked"].append({"test": "exact normalised name", "matches": len(exact),
                          "ids": exact[:5]})
    if exact:
        return False, dict(ev, refused_because="a person of this exact name already exists",
                           candidates=[{"pid": p, "name": IDX[p]["name"]} for p in exact[:5]])
    g, s = given_surname(name)
    if not s:
        return False, dict(ev, refused_because="no surname could be parsed from the name")
    sur = by_surname.get(s, [])
    compat = [p for p in sur if compatible(g, given_surname(IDX[p]["name"])[0])]
    ev["checked"].append({"test": "surname + compatible given name",
                          "surname": s, "same_surname": len(sur),
                          "compatible_given_name": len(compat),
                          "ids": compat[:5]})
    if compat:
        return False, dict(ev, refused_because="an archive person shares this surname with a "
                                               "compatible given name; a variant-name duplicate "
                                               "cannot be ruled out",
                           candidates=[{"pid": p, "name": IDX[p]["name"]} for p in compat[:5]])
    # a surname match with an INCOMPATIBLE given name is not disqualifying on its
    # own -- 30 men named Berry is not evidence -- but it is recorded so the
    # decision can be re-read.
    ev["checked"].append({"test": "surname only, given name not compatible",
                          "same_surname": len(sur), "_not_disqualifying": True,
                          "ids": sur[:5]})
    if extra:
        ev["checked"].append(extra)
    return True, ev


def screen_strict(name, IDX, by_name, by_surname):
    """For a source known to print FORMAL BIRTH NAMES, a surname match alone
    disqualifies. 'Harold Edward Grange' and 'Red Grange' share a surname and
    nothing else derivable -- no given-name rule reaches a nickname, so the only
    safe rule is that a shared surname is enough to refuse."""
    ok, ev = screen(name, IDX, by_name, by_surname)
    if not ok:
        return ok, ev
    g, s = given_surname(name)
    sur = by_surname.get(s, [])
    if sur:
        ev["refused_because"] = ("this source prints formal birth names and an archive "
                                 "person shares the surname; a nickname is not derivable "
                                 "from a formal name, so a duplicate cannot be ruled out")
        ev["candidates"] = [{"pid": p, "name": IDX[p]["name"]} for p in sur[:5]]
        return False, ev
    return True, ev


ROLE_WORD = re.compile(r"^(defense|offense|defensive|offensive|head|line|backfield|"
                       r"ends|scout|trainer|equipment|coach)\b", re.I)
NEXT_ID = None


def new_person_id(IDX, taken=()):
    """The next free id -- free of the INDEX and of every id this decision has already
    handed out. Seeding from the index alone collided with the ids the previous run gave
    its leads: 60 person ids were promoted twice in build/coach-promotions.json, latent
    only because demote_stintless deleted the stintless half of each pair. apply_promotions
    refuses a store that promotes one id twice, and it was right to."""
    global NEXT_ID
    if NEXT_ID is None:
        NEXT_ID = max([int(k[2:]) for k in IDX if k.startswith("P_") and k[2:].isdigit()]
                      + [int(t[2:]) for t in taken if str(t).startswith("P_") and t[2:].isdigit()] or [0])
    NEXT_ID += 1
    while f"P_{NEXT_ID:06d}" in taken: NEXT_ID += 1
    return f"P_{NEXT_ID:06d}"


def main(write=True):
    import write_bios as W
    IDX = W.IDX
    # SCREEN AGAINST THE BASE, NOT AGAINST OUR OWN LAST RUN. The people this file
    # promoted are in the index, so screening against the live index found "a person of
    # this exact name already exists" for every one of them and promotions collapsed
    # 1,799 -> 60. The same shape as the club-key corroboration read off the normalised
    # index: a decider that reads its own output decides nothing.
    BASE_IDX = {k: v for k, v in IDX.items()
                if k == "_clubs" or not (isinstance(v, dict) and v.get("entered_by") == "promotion_from_lead")}
    # A LEAD KEEPS ITS PERSON ID -- but an id two leads both claim is kept by the one the
    # index actually holds, and the other is re-minted. The previous decision handed the
    # same id to two leads sixty times over; it survived only because demote_stintless
    # deleted the stintless half of each pair before anything read them together.
    prior, prior_dupes = {}, []
    pp = os.path.join(BASE, "build", "coach-promotions.json")
    if os.path.exists(pp):
        claimed = collections.defaultdict(list)
        for x in json.load(open(pp))["promotions"]:
            if x.get("lead_ref"): claimed[x["person_id"]].append((x["source"], str(x["lead_ref"])))
        for pid_, leads in claimed.items():
            if len(leads) == 1: prior[leads[0]] = pid_; continue
            keep = leads[0] if pid_ in IDX else leads[0]
            prior[keep] = pid_
            prior_dupes.append({"person_id": pid_, "kept_by": list(keep), "re_minted": [list(l) for l in leads[1:]],
                                "in_the_index": pid_ in IDX,
                                "why": "the previous decision gave this id to more than one lead; the first keeps it and the rest are minted fresh"})
    assigned = set(prior.values())                 # every id a prior decision handed out is taken
    by_name, by_surname = build_index(BASE_IDX)
    before_people = sum(1 for k in IDX if k != "_clubs")

    promotions, refusals = [], []
    counts = collections.Counter()

    def consider(name, source, evidence_of_identity, coaching_seasons, extra, strict=False):
        if not name or ROLE_WORD.match(name):
            refusals.append({"source": source, "name_as_printed": name,
                             "refused_because": "the name begins with a role word; the "
                                                "parse fused a heading to it and a person "
                                                "may not be created under a mangled name",
                             "evidence": {"name_as_printed": name}})
            counts[f"refused:{source}:mangled_name"] += 1
            return
        fn = screen_strict if strict else screen
        ok, ev = fn(name, IDX if False else BASE_IDX, by_name, by_surname)
        if not ok:
            refusals.append({"source": source, "name_as_printed": name,
                             "refused_because": ev["refused_because"], "evidence": ev})
            counts[f"refused:{source}"] += 1
            return
        # A LEAD KEEPS ITS PERSON ID. Minting a fresh id on every run would churn the
        # index and lose the seasons already attached to the old one.
        pid = prior.get((source, str(extra.get("lead_ref")))) or new_person_id(IDX, assigned)
        assigned.add(pid)
        promotions.append({
            "person_id": pid, "name": name, "source": source,
            "entered_by": "promotion_from_lead",
            "_not_a_lesser_class": "an honest record of how he entered, not a lower tier",
            "identified_by": evidence_of_identity,
            "no_archive_match_evidence": ev,
            "coaching_seasons": coaching_seasons,
            "reversible": {"undo": "delete this person_id and restore the lead",
                           "lead_ref": extra.get("lead_ref"),
                           "source_record": extra.get("source_record")},
            **extra})
        counts[f"promoted:{source}"] += 1

    # --- 1. PFA coach leads with no candidate
    C = json.load(open(os.path.join(BASE, "build", "pfa-coaches.json")))
    seasons_by_code = collections.defaultdict(list)
    for c in C["claims"]:
        if c["predicate"] in ("pfa.coaching_season", "pfa.coaching_playoffs"):
            code = c["source_record"].rsplit("/", 1)[-1].replace(".html", "")
            seasons_by_code[code].append(c["value"])
    for l in C["leads"]:
        if l["category"] != "unmatched_no_candidate":
            continue
        consider(l["name_as_printed"], "pfa-coach-lead",
                 {"pfa_code": l["pfa_code"], "printed_full_name": l.get("printed_full_name"),
                  "places_on": l.get("places_on"), "lists": l.get("lists")},
                 l.get("coaching_seasons") or seasons_by_code.get(l["pfa_code"], []),
                 {"lead_ref": l["lead_id"], "source_record": l["source_record"],
                  "pfa_code": l["pfa_code"], "fields": l.get("fields")})

    # --- 2. media-guide assistants
    #
    # THE GUIDE'S OWN STAFF LIST IS THE MAN'S COACHING SEASONS. Ryan's ruling of
    # 2026-09-07: a club's own media guide naming a man as its coach documents that he
    # worked that season. This passed [] for years, so every one of these promotions was
    # created with no season and demote_stintless removed all 198 of them again -- the
    # promotion looked for corroboration in PFA cells these men do not appear in, and
    # absence from a different source is not evidence against. The league comes from the
    # club table for that club-year; a club-year the table cannot place is left out and
    # counted, never guessed.
    from clubs import Clubs
    CT = Clubs()
    A = json.load(open(os.path.join(BASE, "build", "assistants.json")))
    guide_seasons = collections.defaultdict(list); no_league = []
    for c in A["claims"]:
        if c["subject"][0] != "stint": continue
        club, yr = c["subject"][2], int(c["subject"][3][1:5])
        hit = CT.resolve(club, yr, None, source="season_key")
        lg = CT.league_for(hit[0], yr) if hit else None
        if not lg: no_league.append({"club_as_printed": club, "year": yr, "role_as_printed": c["value"]}); continue
        guide_seasons[c["subject"][1]].append({"league": lg, "year": yr, "club": club,
                                               "role_as_printed": c["value"], "section": "MEDIA GUIDE STAFF LIST",
                                               "printed_long": f"{yr} {club}", "source_record": c["source_record"],
                                               "roster_evidence": "the club's own media guide staff list"})
    for c in A["claims"]:
        if c["predicate"] != "name":
            continue
        consider(c["value"], "media-guide-assistant",
                 {"legacy_id": c["subject"][1], "source_record": c["source_record"]},
                 sorted(guide_seasons.get(c["subject"][1], []), key=lambda s: (s["year"], s["club"])),
                 {"lead_ref": c["subject"][1], "source_record": c["source_record"]})

    # --- 3. coaching-tree people, STRICT: this source prints formal birth names
    CT = json.load(open(os.path.join(BASE, "build", "coaches.json")))
    ctnames = {}
    for c in CT["claims"]:
        if c["subject"][0] == "person" and c["predicate"] in ("name", "full_name"):
            ctnames.setdefault(c["subject"][1], c["value"])
    for legacy, nm in ctnames.items():
        consider(nm, "coaching-tree", {"legacy_id": legacy},
                 [], {"lead_ref": legacy, "source_record": f"coaching-tree#{legacy}"},
                 strict=True)

    out = {"decided_at": "2026-09-06",
           "checked_against": "build-reports/person-index.json AFTER the 92 merges",
           "promotions": promotions, "refusals": refusals,
           "left_alone": {}, "counts": dict(counts),
           "people_before": before_people,
           "people_after": before_people + len(promotions)}
    for cat in ("namesake_only_not_evidence", "ambiguous_candidates", "route_conflict"):
        out["left_alone"][cat] = sum(1 for l in C["leads"] if l["category"] == cat)
    out["guide_club_years_without_a_league"] = no_league
    out["person_ids_reminted"] = prior_dupes
    if write:
        IO.dump_atomic(out, os.path.join(BASE, "build", "coach-promotions.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main()
    print(f"  people before {o['people_before']:,}  after {o['people_after']:,}")
    print(f"  promotions {len(o['promotions']):,}   refusals {len(o['refusals']):,}")
    for k, v in sorted(o["counts"].items()):
        print(f"     {k:44s} {v:,}")
    print("  left alone:", o["left_alone"])
