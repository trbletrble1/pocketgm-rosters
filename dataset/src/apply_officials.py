"""Write the officials into the person index. The eighth writer, and the missing one.

WHAT WAS WRONG. ingest_officials.py resolved 1,052 men and mutated write_bios.IDX
IN MEMORY. Nothing ever persisted that. The 17:35 index held the officials by a
path that was never checked in, so the moment the index was rebuilt they became
978 empty shells -- the claims mint the ids, but nothing carries a name, a role or
a single officiating season. Gate P3 cannot see it: the current index already
lacks them, so it compares 0 to 0 and reports no loss. A check that can only
notice a regression is blind to a gap that is already open.

RYAN'S RULING, WHICH THIS IMPLEMENTS. Officials are people. The line drawn is
ON-FIELD GAME PARTICIPANTS and is explicitly not precedent for trainers,
equipment managers, owners or broadcasters. The 132 men whose PFA code is
reachable at more than one path are ONE person carrying two or three roles, never
two people -- so this script never creates a record for a code that already
resolves, and never overwrites a playing or coaching career it finds in place.

IDEMPOTENT IN BOTH DIRECTIONS, WHICH apply_promotions.py IS NOT.
That script guards with `if pid in idx: continue`, so a second run against an
index that already holds its ids adds nothing, builds an EMPTY claims list, and
writes that empty list over build/coach-seasons-promoted.json -- destroying its
own output while the index itself is fine. The bug is not the index write; it is
that the report was assembled from THE DELTA rather than from the source store.

Here every value is a pure function of build/pfa-officials.json:
  - fields are SET, not skipped, so a half-applied index converges;
  - the report is built from all 1,052 men every run, whatever this run changed;
  - fields owned by other steps (seasons, coaching_seasons) are never touched.
Run it once, twice or ten times and the index and the report are identical.

NOT COVERED BY ROLLBACK. build/officials-applied.json is this script's own output.
The rollback in build_person_index.py restores the INDEX from its pre-rebuild
copy; it does not restore the files the chain steps write on their way past. If a
rebuild is rolled back, this report still describes the run that was undone. Re-run
this script to bring it back into agreement -- which is safe, because it is
idempotent.

  python3 src/apply_officials.py [--dry]
"""
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic index write; also how P1 finds us
OFFICIALS = os.path.join(BASE, "build", "pfa-officials.json")
REPORT = os.path.join(BASE, "build", "officials-applied.json")
SRC_ID = "pro-football-archives"


class ApplyError(Exception):
    pass


def season_key(s):
    """LEAGUE|YEAR|ASSIGNMENT, the shape build_dashboard splits on.

    It reads parts[0] as the league and parts[1] as the year for the decade
    bucket, exactly as it does for coaching_seasons, so officiating seasons have
    to be a DICT of keys -- a list here would have the dashboard iterating
    characters of a string and finding no year at all.

    The assignment is the SOURCE'S OWN STRING and is not normalised: 'Umpire;
    Head Linesman' is one season worked in two roles, 'Vide Replay' is the
    source's typo, and '' is a season whose assignment cell was empty. Mapping
    those to a tidy vocabulary is a ruling nobody has made.
    """
    return f"{s.get('league_as_printed','')}|{s.get('year','')}|{s.get('assignment_as_printed','')}"


def group(seasons):
    out = {}
    for s in seasons:
        out.setdefault(season_key(s), []).append(s)
    return out


def collect(store):
    """-> {pid: {name, roles, officiating_seasons, created, pfa_code, source_record}}

    Built from the STORE, never from the index, so the answer does not depend on
    what any previous run happened to do."""
    created = {c["person_id"]: c for c in store["created"]}
    per = {}
    for c in store["created"]:
        per[c["person_id"]] = {
            "name": c["name"], "roles": c.get("roles") or ["official"],
            "officiating_seasons": group(c.get("officiating_seasons") or []),
            "created": True, "pfa_code": c.get("pfa_code"),
            "source_record": (c.get("identified_by") or {}).get("source_record"),
            "entered_by": c.get("entered_by", "officials_ingest"),
            "reversible": c.get("reversible"),
        }
    # The 74 who already existed have NO `created` record -- they were resolved on
    # their PFA code, so their seasons live only in the claims.
    byrole = {}
    for cl in store["claims"]:
        if cl["predicate"] == "pfa.role":
            byrole[cl["subject"][1]] = cl["value"]
    for cl in store["claims"]:
        if cl["predicate"] != "pfa.officiating_season":
            continue
        pid = cl["subject"][1]
        if pid in created:
            continue
        e = per.setdefault(pid, {"name": None, "roles": None, "officiating_seasons": {},
                                 "created": False,
                                 "pfa_code": (byrole.get(pid) or {}).get("pfa_code"),
                                 "source_record": cl["source_record"],
                                 "entered_by": "officials_ingest", "reversible": None})
        e["officiating_seasons"].setdefault(season_key(cl["value"]), []).append(cl["value"])
        e["roles"] = (byrole.get(pid) or {}).get("roles") or ["official"]
    return per


def main(write=True, idx=None):
    store = json.load(open(OFFICIALS))
    per = collect(store)
    if len(per) != store["counts"]["created"] + store["counts"]["resolved_to_existing"]:
        raise ApplyError(
            f"collected {len(per)} men but the store counts "
            f"{store['counts']['created']} created + "
            f"{store['counts']['resolved_to_existing']} resolved. An official who "
            f"reaches neither list is an official nobody will ever see.")
    if idx is None:
        idx = IO.load_index()

    n = collections.Counter()
    acct = []                                    # every decision accounted for (Ryan, 2026-09-11)
    for pid, e in per.items():
        rec = idx.get(pid)
        if rec is None:
            # No claim minted this id. That means the officials CLAIMS are not in
            # the build -- refuse rather than invent a person the claims flow has
            # never heard of.
            raise ApplyError(
                f"{pid} is not in the index at all. apply_officials runs AFTER the "
                f"claims build, which mints these ids from pfa-officials.json's "
                f"claims; if it is absent the store was not read by the builder.")
        n["created_record" if e["created"] else "already_a_person"] += 1
        if rec.get("name") and e["name"] and rec["name"] != e["name"]:
            # Somebody else named him first. The archive's name wins; the officials
            # page's spelling is held beside it, not over it.
            rec.setdefault("_name_as_printed_by", {})["officials"] = e["name"]
            n["name_kept_from_archive"] += 1
        elif e["name"] and not rec.get("name"):
            rec["name"] = e["name"]; n["name_filled"] += 1
        # ROLES ARE A UNION. A man who played, coached and officiated is one person
        # with three roles; clobbering the list would erase the other two.
        roles = list(dict.fromkeys((rec.get("roles") or []) + (e["roles"] or [])))
        if roles != (rec.get("roles") or []):
            n["roles_updated"] += 1
        rec["roles"] = roles
        rec["officiating_seasons"] = e["officiating_seasons"]
        n["officiating_seasons"] += len(e["officiating_seasons"])
        rec.setdefault("slugs", []); rec.setdefault("person", {})
        rec.setdefault("person_season", []); rec.setdefault("seasons", {})
        rec["entered_by"] = rec.get("entered_by") or e["entered_by"]
        if e["pfa_code"]:
            rec.setdefault("identified_by", {})["officials_pfa_code"] = e["pfa_code"]
        if e["reversible"]:
            rec["officials_ref"] = e["reversible"]
        # A man with no playing season has no playing career to be missing. Set it
        # only when `seasons` is genuinely empty -- one of these 1,052 is a player
        # whose playing fields DO apply, and marking him would be a lie.
        if rec.get("seasons"):
            rec.pop("_playing_fields_do_not_apply", None)
        else:
            rec["_playing_fields_do_not_apply"] = True
        idx[pid] = rec
        acct.append({"decision": pid, "outcome": "applied", "expected": len(e["officiating_seasons"]),
                     "moved": len(e["officiating_seasons"]), "reason": None, "legitimate": True})

    IO.write_account("apply_officials", acct, run="write" if write else "dry")
    dual = {d["pfa_code"]: d for d in store["dual_role"]}
    out = {"source": {"source_id": SRC_ID, "name": "Pro Football Archives",
                      "stated_by": "Pro Football Archives", "acquisition": "fetched"},
           "_not_covered_by_rollback": "build_person_index.py's rollback restores the "
                                       "INDEX only. This file is this script's own "
                                       "output and survives a rollback describing a run "
                                       "that was undone. Re-run apply_officials.py.",
           "applied": sorted(per),
           "dual_role_men": len(dual),
           # STATE, NOT DELTA. Every number here describes what the index now
           # HOLDS, so a second run reproduces the file byte for byte.
           #
           # It did not, at first. `names_filled` and `roles_updated` counted what
           # the RUN did -- 978 and 1,052 on a fresh index, 0 and 0 on the next
           # pass -- so the report changed on the second run while the index was
           # already stable. That is apply_promotions.py's bug wearing a smaller
           # hat, in the file whose docstring criticises it. Per-run deltas print
           # to stdout, where being about the run is the whole point, and stay out
           # of the artefact that has to be reproducible.
           "counts": {"men": len(per),
                      "created_by_officials_ingest": n["created_record"],
                      "already_a_person": n["already_a_person"],
                      "officiating_season_keys": n["officiating_seasons"]}}
    if write:
        IO.save_index(idx)
        IO.dump_atomic(out, REPORT, indent=1)
    return out, idx, {"names_filled": n["name_filled"],
                      "names_kept_from_archive": n["name_kept_from_archive"],
                      "roles_updated": n["roles_updated"]}



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o, _, delta = main(write="--write" in sys.argv)
    for k, v in o["counts"].items():
        print(f"  {k:32s} {v:,}")
    print(f"  {'dual_role men in the store':32s} {o['dual_role_men']:,}")
    print("  -- this run only (not persisted; zero on a re-run is correct) --")
    for k, v in delta.items():
        print(f"  {k:32s} {v:,}")
