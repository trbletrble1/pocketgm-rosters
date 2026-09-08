"""Write the promoted players' metadata into the person index. Mirrors apply_promotions.py.

WHAT THIS OWNS AND WHAT IT DOES NOT. A promoted player's SEASONS come from claims,
not from here: resolve_person() returns any `P_` id as itself, so the ingest's
claims build his seasons the ordinary way. This step owns only what no claim can
say -- that he entered by promotion, which decision did it, and whether his
forename is unknown.

That is the one real difference from the coach route, and it runs the other way:
apply_promotions.py OWNS `coaching_seasons` because nothing else produces them.

IDEMPOTENT, AND THE REPORT IS STATE NOT DELTA. Every value is a pure function of
build/player-promotions.json; owned fields are SET rather than skipped, so a
half-applied index converges; per-run deltas go to stdout, where being about the
run is the point. This is the shape apply_promotions.py arrived at after a guard
of the form `if pid in idx: continue` cost a rebuild.

THE FORENAME FLAG SURVIVES INTO THE PERSON. Four of the fourteen are a surname and
nothing else. The archive already holds thirteen such men -- real people whose
forenames are lost, not defects -- and a later source completing one must be able
to FIND him rather than mint a second record beside him.

  python3 src/apply_player_promotions.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
PROM = os.path.join(BASE, "build", "player-promotions.json")
REPORT = os.path.join(BASE, "build", "player-seasons-promoted.json")
OWNED = ("entered_by", "promotion_ref", "forename_unknown", "_entered_as_a_player")


class ApplyError(Exception):
    pass


def collect(prom):
    per = {}
    for p in prom["promotions"]:
        pid = p["person_id"]
        if pid in per:
            raise ApplyError(f"{pid} is promoted twice in the store")
        per[pid] = {"name": p["name"],
                    "entered_by": p["entered_by"],
                    "promotion_ref": p["reversible"]["lead_ref"],
                    "forename_unknown": bool(p.get("forename_unknown")),
                    "source_record": p["source_record"],
                    "playing_seasons": p["playing_seasons"]}
    return per


def apply(idx, per):
    n = collections.Counter()
    for pid, e in per.items():
        rec = idx.get(pid)
        if rec is None:
            # He should already exist, built from the ingest's claims. If he does not,
            # the claims did not land -- say so rather than papering over it with an
            # empty record that would look like a successful promotion.
            n["created_without_claims"] += 1
            rec = {"name": e["name"], "slugs": [], "person": {}, "person_season": [],
                   "seasons": {}}
        else:
            n["already_present"] += 1
            if not rec.get("name"):
                rec["name"] = e["name"]; n["name_filled"] += 1
            elif rec["name"] != e["name"]:
                rec.setdefault("_name_as_printed_by", {})["promotion"] = e["name"]
                n["name_kept_from_archive"] += 1
        rec["entered_by"] = rec.get("entered_by") or e["entered_by"]
        rec["promotion_ref"] = e["promotion_ref"]
        rec["_entered_as_a_player"] = True
        if e["forename_unknown"]:
            rec["forename_unknown"] = True
            n["forename_unknown"] += 1
        else:
            rec.pop("forename_unknown", None)
        if not rec.get("seasons"):
            n["promoted_but_holds_no_season"] += 1
        for k in ("slugs", "person", "person_season", "seasons"):
            rec.setdefault(k, {} if k in ("person", "seasons") else [])
        idx[pid] = rec
    return n


def main(write=True, idx=None):
    if not os.path.exists(PROM):
        raise ApplyError(f"no decision store at {PROM}; run promote_players.py --write first")
    prom = json.load(open(PROM))
    per = collect(prom)
    if idx is None:
        idx = IO.load_index()
    delta = apply(idx, per)
    holds = sum(1 for pid in per if (idx.get(pid) or {}).get("seasons"))
    out = {"source": {"source_id": "player-promotions", "acquisition": "derived",
                      "stated_by": "this project, from document rosters"},
           "_not_covered_by_rollback": "build_person_index.py's rollback restores the INDEX "
                                       "only. This file is this script's own output. "
                                       "Re-run apply_player_promotions.py after a rollback.",
           "_seasons_are_not_here": "a promoted player's seasons come from the ingest's "
                                    "claims, not from this store. This file records the "
                                    "promotion, not the career.",
           "claims": [],
           "counts": {"promotions_in_store": len(per),
                      "people_holding_at_least_one_season": holds,
                      "promoted_but_holding_none": len(per) - holds,
                      "forename_unknown": sum(1 for e in per.values() if e["forename_unknown"]),
                      "playing_seasons_decided": sum(len(e["playing_seasons"]) for e in per.values())}}
    if write:
        IO.save_index(idx)
        IO.dump_atomic(out, REPORT, indent=1)
    return out, idx, delta


if __name__ == "__main__":
    out, _, delta = main(write="--dry" not in sys.argv)
    print("this run (stdout only, not persisted):")
    for k, v in sorted(delta.items()): print(f"  {k:32s} {v:,}")
    print("the store, as persisted:")
    for k, v in out["counts"].items(): print(f"  {k:38s} {v:,}")
