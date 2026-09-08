"""Write the promoted coaches into the person index and their seasons as claims.

TWO SEPARATE THINGS, kept separate on purpose.

The index gains 1,799 people whose `seasons` (playing) is EMPTY and whose
`coaching_seasons` is populated. That emptiness is the point: a coaching-only man
has no playing career, and a field that does not apply to him must be
distinguishable from one that is merely unrecorded.

Each new record carries `entered_by` and `promotion_ref`, so the index write is as
reversible as the promotion store it came from -- deleting the ids named in
coach-promotions.json restores the index exactly.

IDEMPOTENT IN BOTH DIRECTIONS. The first version was not, and it blocked every
rebuild. It guarded with `if pid in idx: continue`, and on a FRESH rebuild the
claims build mints the promoted ids first -- from the very claims this script
wrote last time -- so the guard fired for all 1,799, the script set nothing, and
then wrote an EMPTY claims list over build/coach-seasons-promoted.json. A test
rebuild watched coaching_seasons fall 1,598 -> 0 and P3 rolled it back; nothing
could pass P3 until this was fixed. The stub that test left behind was 249 bytes,
down from 15,246,755.

The defect was not the index write. THE REPORT WAS ASSEMBLED FROM THE DELTA
rather than from the source store, so it described what the run did instead of
what the store holds, and a second run described nothing. apply_officials.py met
the same bug and fixed it the right way, and this follows that pattern exactly:

  - every value is a pure function of build/coach-promotions.json;
  - fields this step owns are SET, never skipped, so a half-applied index
    converges;
  - fields owned by other steps (`seasons`, `person`, `slugs`, `person_season`,
    `officiating_seasons`, `roles`) are never touched;
  - the persisted report is built from all 1,799 promotions every run, whatever
    this run changed. Per-run deltas print to stdout, where being about the run
    is the point.

Run it once, twice or ten times and the index and the report are identical.

WHAT THIS STEP DOES NOT DECIDE. demote_stintless.py runs after this and removes
the 201 promotions that carry no coaching season. This script therefore creates
those 201 records on every run -- it has to, or the demotion would find nothing
to reverse and its own report would change -- and the chain, not this step alone,
is what converges on the demoted index. Applied alone to an already-demoted index
it re-creates the 201 stintless records, and demote_stintless.py removes them
again. That is the declared order in declarations/person-index-rebuild.json.

NOT COVERED BY ROLLBACK. build/coach-seasons-promoted.json is this script's own
output. build_person_index.py's rollback restores the INDEX from its pre-rebuild
copy; it does not restore the files chain steps write on the way past. If a
rebuild is rolled back, re-run this script -- which is safe, because it is
idempotent, and which is how the 249-byte stub was regenerated.

  python3 src/apply_promotions.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic index write; also how P1 finds us
PROM = os.path.join(BASE, "build", "coach-promotions.json")
REPORT = os.path.join(BASE, "build", "coach-seasons-promoted.json")
SRC_ID = "pro-football-archives"
OWNED = ("coaching_seasons", "entered_by", "promotion_ref", "_playing_fields_do_not_apply")


class ApplyError(Exception):
    pass


def season_key(s):
    """LEAGUE|YEAR|CLUB, the shape the dashboard splits on for its decade bucket."""
    return f"{s.get('league', '')}|{s.get('year', '')}|{s.get('club', '')}"


def collect(prom):
    """-> ({pid: record fields this step owns}, [claims]), from the STORE only.

    Both are pure functions of coach-promotions.json. The claims are one per
    coaching season for every promotion, in store order, so the multiset the gate
    compares is the store's own multiset and the file is reproducible byte for
    byte."""
    per, claims = {}, []
    for p in prom["promotions"]:
        pid = p["person_id"]
        if pid in per:
            raise ApplyError(f"{pid} is promoted twice in the store")
        cs = {}
        for s in p["coaching_seasons"]:
            cs.setdefault(season_key(s), []).append(s)
        per[pid] = {"name": p["name"], "coaching_seasons": cs,
                    "entered_by": p["entered_by"],
                    "promotion_ref": p["reversible"]["lead_ref"],
                    "source_record": p["source_record"]}
        for s in p["coaching_seasons"]:
            claims.append({
                "source_record": p["source_record"], "source_id": SRC_ID,
                "stated_by": "Pro Football Archives",
                "attribution": ["Pro Football Archives"],
                "subject": ["person", pid], "predicate": "pfa.coaching_season",
                "value": s, "kind": "observed", "observed_at": "fetched-2026-09",
                "_from_promotion": p["reversible"]["lead_ref"]})
    return per, claims


def apply(idx, per):
    """SET the owned fields on every promoted man, creating him if absent. Returns
    the per-run delta, which is for stdout and nothing else."""
    n = collections.Counter()
    for pid, e in per.items():
        rec = idx.get(pid)
        if rec is None:
            rec = {"name": e["name"], "slugs": [], "person": {}, "person_season": [],
                   # EMPTY, and empty on purpose. He has no playing career.
                   "seasons": {}}
            n["created"] += 1
        else:
            n["already_present"] += 1
            if not rec.get("name"):
                rec["name"] = e["name"]; n["name_filled"] += 1
            elif rec["name"] != e["name"]:
                # the archive's name stands; the promotion's spelling is held beside it
                rec.setdefault("_name_as_printed_by", {})["promotion"] = e["name"]
                n["name_kept_from_archive"] += 1
        if rec.get("coaching_seasons") != e["coaching_seasons"]:
            n["coaching_seasons_set"] += 1
        rec["coaching_seasons"] = e["coaching_seasons"]
        rec["entered_by"] = rec.get("entered_by") or e["entered_by"]
        rec["promotion_ref"] = e["promotion_ref"]
        # A man with no playing season has no playing career to be missing. Never
        # mark a man who DOES hold one -- these fields are owned by other steps and
        # are read here, not written.
        if rec.get("seasons"):
            rec.pop("_playing_fields_do_not_apply", None)
        else:
            rec["_playing_fields_do_not_apply"] = True
        for k in ("slugs", "person", "person_season", "seasons"):
            rec.setdefault(k, [] if k != "person" and k != "seasons" else {})
        idx[pid] = rec
    return n


def main(write=True, idx=None):
    prom = json.load(open(PROM))
    per, claims = collect(prom)
    want = sum(len(p["coaching_seasons"]) for p in prom["promotions"])
    if len(claims) != want:
        raise ApplyError(f"collected {len(claims):,} claims for {want:,} seasons in the store")
    if idx is None:
        idx = IO.load_index()
    delta = apply(idx, per)
    stintless = sum(1 for e in per.values() if not e["coaching_seasons"])
    out = {"source": {"source_id": SRC_ID, "name": "Pro Football Archives",
                      "stated_by": "Pro Football Archives", "acquisition": "fetched"},
           "_not_covered_by_rollback": "build_person_index.py's rollback restores the INDEX "
                                       "only. This file is this script's own output and "
                                       "survives a rollback describing a run that was undone. "
                                       "Re-run apply_promotions.py.",
           "claims": claims,
           # STATE, NOT DELTA. Every number describes what the store holds and what
           # the index now holds for it, so a second run reproduces the file byte
           # for byte. Per-run deltas go to stdout.
           "counts": {"claims": len(claims),
                      "promotions_in_store": len(per),
                      "coaching_seasons": len(claims),
                      "people_with_coaching_seasons": len(per) - stintless,
                      "stintless_promotions_demoted_by_next_step": stintless}}
    if write:
        IO.save_index(idx)
        IO.dump_atomic(out, REPORT, indent=1)
    return out, idx, delta


if __name__ == "__main__":
    out, _, delta = main(write="--dry" not in sys.argv)
    print("this run (stdout only, not persisted):")
    for k in ("created", "already_present", "coaching_seasons_set", "name_filled", "name_kept_from_archive"):
        print(f"  {k:26s} {delta.get(k, 0):,}")
    print("the store, as persisted to the report:")
    for k, v in out["counts"].items():
        print(f"  {k:42s} {v:,}")
