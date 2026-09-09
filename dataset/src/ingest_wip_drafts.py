"""Ingest wip/draft_picks_pre2001.csv and wip/draft_picks_2001_2004.csv.

Both fall INSIDE nflverse's 1974-2026 range, so neither is new coverage -- they are
second voices on years already spoken for, and their worth is agreement.

THE PRE-2001 FILE HAS NO ROUND. Its 6,280 rows carry name, overall pick, position
and season, and nothing else. It is written under its own predicate,
`draft.overall_pick_only`, rather than as a draft_selection with a null round:
a record that merely LOOKS complete until someone reads the field is the shape of
error this archive keeps finding. The predicate name carries the limitation, so a
consumer cannot mistake it for a full draft record without ignoring the name.
"""
import os, re, csv, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
WIP = os.path.join(BASE, "..", "wip")
from ingest_nflverse import norm, date_key, build_index

SOURCES = {
    "pre2001": {"source_id": "draft-picks-pre2001", "file": "draft_picks_pre2001.csv",
                "name": "draft_picks_pre2001.csv", "has_round": False},
    "y2001_2004": {"source_id": "draft-picks-2001-2004", "file": "draft_picks_2001_2004.csv",
                   "name": "draft_picks_2001_2004.csv", "has_round": True},
}


class WipError(Exception):
    pass


def resolve(name, season, by_name, IDX, seasons):
    """No birth date exists in either file, so identity rests on name plus the
    career window. Where more than one man of that name was active, the row is
    left UNRESOLVED -- these are second voices on years nflverse already covers,
    so a guess would buy nothing and could cost a wrong attribution."""
    cands = by_name.get(norm(name), [])
    if not cands:
        return None, "no_name_match"
    if len(cands) == 1:
        ys = [s["year"] for s in seasons(IDX[cands[0]])]
        if ys and min(ys) - 1 <= season <= max(ys) + 1:
            return cands[0], "unique_name_in_career_window"
        return None, "unique_name_but_season_outside_career"
    win = [c for c in cands
           if (lambda ys: ys and min(ys) - 1 <= season <= max(ys) + 1)(
               [s["year"] for s in seasons(IDX[c])])]
    if len(win) == 1:
        return win[0], "career_window_broke_the_namesake_tie"
    return None, "ambiguous_namesakes" if win else "no_candidate_in_career_window"


def main(write=True):
    import write_bios as W
    by_name = build_index(W.IDX, W.seasons)
    claims, unresolved = [], []
    counts = {}
    for key, S in SOURCES.items():
        rows = list(csv.DictReader(open(os.path.join(WIP, S["file"]), encoding="utf-8",
                                        errors="replace")))
        how = collections.Counter()
        for r in rows:
            nm = (r.get("name") or r.get("pfr_player_name") or "").strip()
            yr = r.get("season", "")
            if not nm or not yr.isdigit():
                how["unusable_row"] += 1
                continue
            pid, kind = resolve(nm, int(yr), by_name, W.IDX, W.seasons)
            how[kind] += 1
            if not pid:
                unresolved.append({"source_id": S["source_id"], "name_as_printed": nm,
                                   "season": int(yr), "reason": kind, "IS_NOT_RESOLVED": True})
                continue
            v = {"year": int(yr), "overall_pick": int(r["pick"]) if r["pick"].isdigit() else None,
                 "position_as_printed": (r.get("position") or "").strip()}
            if S["has_round"]:
                v["round"] = int(r["round"]) if str(r.get("round", "")).isdigit() else None
                v["team"] = (r.get("team") or "").strip()
                v["college_as_printed"] = (r.get("college") or "").strip()
                pred = "draft.selection"
            else:
                v["_round_is_not_in_this_source"] = True
                pred = "draft.overall_pick_only"
            if v["overall_pick"] is None:
                how["no_pick_value"] += 1
                continue
            claims.append({"source_record": f"{S['source_id']}#{yr}-{v['overall_pick']}",
                           "source_id": S["source_id"], "stated_by": S["name"],
                           "attribution": [S["name"]], "subject": ["person", pid],
                           "predicate": pred, "value": v, "kind": "observed",
                           "observed_at": "held-2026-09"})
        counts[S["source_id"]] = {"rows": len(rows), "by_resolution": dict(how)}
    out = {"claims": claims, "unresolved": unresolved, "counts": counts}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "wip-drafts.json"), indent=1)
    return out



# WRITING IS OPT-IN. Ruled 2026-09-09 after two incidents in one afternoon: this file
# used to write on a bare run, so the safe action was the one you had to know to ask
# for. `--write` is now required; without it the script computes and reports.
if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for sid, c in o["counts"].items():
        print(f"  {sid}  rows {c['rows']:,}")
        for k, v in sorted(c["by_resolution"].items(), key=lambda x: -x[1]):
            print(f"     {v:6,}  {k}")
    print(f"  claims written {len(o['claims']):,}   unresolved {len(o['unresolved']):,}")
