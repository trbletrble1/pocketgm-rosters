"""Ingest nflverse draft records. Writes dataset/build/nflverse-draft.json.

12,495 complete draft records, 1974-2026. The work here is not the parsing -- the
CSV is clean -- it is the IDENTITY JOIN, which did not exist before.

Name alone is a bug in this era. The archive holds 923 names shared by two people,
172 by three, and eleven men called Mike Williams. Both sides carry a birth date on
100% of the relevant rows, so name + birth date is the join, and everything else is
about the rows where that fails.
"""
import os, re, csv, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
DECL = json.load(open(os.path.join(BASE, "declarations", "nflverse.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
CSV = "/Users/ryannecci/Documents/pgm3-sources/nflverse/players.csv"
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October "
    "November December".split())}
BLANK = ("", "NA", "None", "NULL")


class NflverseError(Exception):
    pass


def date_key(s):
    s = (s or "").strip()
    m = re.match(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})$", s)
    if m and m.group(1) in MONTHS:
        return (int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def norm(n):
    return re.sub(r"[^a-z]", "", (n or "").lower())


def cell(r, f):
    v = (r.get(f) or "").strip()
    return "" if v in BLANK else v


def claim(pid, pred, value, row, resolved_by=None):
    """A claim, and it NAMES THE ROUTE THAT RESOLVED THE MAN.

    `resolved_by` used to live only inside the draft_selection VALUE, which works while
    every claim's value is a dict and breaks the moment one is not: the birth-date claim
    added on 2026-09-07 carries a plain string, and gate_drafts D4 -- which reads
    `claim["value"]["resolved_by"]` for every claim -- crashed on it. The route belongs to
    the CLAIM, not to one shape of value, so it is written here for every claim and D4
    reads it from either place."""
    if not pid:
        raise NflverseError("a claim requires a resolved person")
    if value in (None, ""):
        raise NflverseError("an empty value is not a claim")
    c = {"source_record": f"{SRC_ID}#{cell(row, 'gsis_id')}", "source_id": SRC_ID,
         "stated_by": DECL["stated_by"], "attribution": [DECL["name"]],
         "subject": ["person", pid], "predicate": pred, "value": value,
         "kind": "observed", "observed_at": "held-2026-09",
         "gsis_id": cell(row, "gsis_id"), "pfr_id": cell(row, "pfr_id")}
    if resolved_by: c["resolved_by"] = resolved_by
    return c


def build_index(IDX, seasons):
    by_name = collections.defaultdict(list)
    for pid, p in IDX.items():
        # a person with no name normalises to "" and would collide with 126 others.
        # An empty key is not a name and must never match.
        if pid == "_clubs" or not p.get("seasons") or not p.get("name"):
            continue
        k = norm(p["name"])
        if k:
            by_name[k].append(pid)
    return by_name


def resolve(row, by_name, IDX, seasons):
    """Returns (pid, how, note). pid is None when the man is not resolved."""
    k, b = norm(cell(row, "display_name")), date_key(cell(row, "birth_date"))
    cands = by_name.get(k, [])
    if not cands:
        return None, "no_name_match", "no archive person carries this name"
    if b is None:
        return None, "no_birth_date", "nflverse row has no birth date"
    abd = {c: date_key(((IDX[c].get("person") or {}).get("birth_date") or [None])[0])
           for c in cands}
    exact = [c for c in cands if abd[c] == b]
    if len(exact) == 1:
        return exact[0], "name_and_birth_date", None
    if len(exact) > 1:
        return None, "ambiguous_same_name_and_birth_date", f"{len(exact)} people match both"
    dy = int(cell(row, "draft_year"))
    win = []
    for c in cands:
        ys = [s["year"] for s in seasons(IDX[c])]
        if ys and min(ys) - 1 <= dy <= max(ys):
            win.append(c)
    if len(win) > 1:
        return None, "ambiguous_career_window", f"{len(win)} candidates fit the draft year"
    if not win:
        return None, "no_window_contains_draft_year", f"draft year {dy} outside every candidate's career"
    c = win[0]
    d = abd[c]
    if d is None:
        return None, "archive_has_no_birth_date", "cannot corroborate"
    parts = [i for i in range(3) if b[i] != d[i]]
    if len(parts) == 1:
        # ONE component apart is the shape of a transcription slip. Two is not
        # evidence of anything, and a guess there is a wrong man forever.
        return c, "career_window_one_part_birth_date_differs", ["year", "month", "day"][parts[0]]
    return None, "birth_date_differs_in_2_or_more_parts", f"{len(parts)} components differ"


def main(write=True):
    import write_bios as W
    by_name = build_index(W.IDX, W.seasons)
    rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8", errors="replace"))
            if cell(r, "draft_year")]
    claims, disagreements, unresolved = [], [], []
    how = collections.Counter(); nfield = collections.Counter()
    for r in rows:
        pid, kind, note = resolve(r, by_name, W.IDX, W.seasons)
        how[kind] += 1
        if not pid:
            unresolved.append({"display_name": cell(r, "display_name"),
                               "gsis_id": cell(r, "gsis_id"), "reason": kind, "note": note,
                               "draft": {f: cell(r, "draft_" + f)
                                         for f in ("year", "round", "pick", "team")},
                               "IS_NOT_RESOLVED": True})
            continue
        sel = {"year": int(cell(r, "draft_year")), "round": int(cell(r, "draft_round")),
               "overall_pick": int(cell(r, "draft_pick")), "team": cell(r, "draft_team"),
               "resolved_by": kind}
        claims.append(claim(pid, "nflverse.draft_selection", sel, r, resolved_by=kind))
        nfield["draft_selection"] += 1
        if kind == "career_window_one_part_birth_date_differs":
            a = ((W.IDX[pid].get("person") or {}).get("birth_date") or [None])[0]
            # A DISAGREEING VALUE IS WRITTEN AS A CLAIM. Ruled by Ryan, 2026-09-07.
            #
            # This block said `"_both_are_held": "neither value is preferred or removed"`
            # and wrote only the archive's side -- the nflverse date it disagreed with went
            # into the report and nowhere else. Measured 2026-09-07: 164 of these 270 rows
            # named a birth date no store held, so the read model could not contest it and
            # `/contested` reported the man's birth date as settled. Nothing was preferred;
            # one side simply could not be served, which is not the same as being held.
            #
            # The man is already resolved by a PERMITTED route -- this branch IS the
            # career-window route -- so the claim rests on the identity the ingest already
            # made, and no route is widened to write it. Its `resolved_by` says which.
            #
            # SCOPE. declarations/nflverse.json says only the draft is ingested from
            # players.csv. This is the one narrow exception the ruling creates: the value
            # this ingest reports a DISAGREEMENT about, and nothing else. Height, weight,
            # college and the rest stay unwritten.
            claims.append(claim(pid, "nflverse.birth_date", cell(r, "birth_date"), r, resolved_by=kind))
            nfield["birth_date_because_it_disagrees"] += 1
            disagreements.append({"subject": ["person", pid], "field": "birth_date",
                                  "nflverse": cell(r, "birth_date"), "statscrew": a,
                                  "other_source": "statscrew", "resolved": None,
                                  "differs_in": note, "kind": "derived",
                                  "_both_are_held": "neither value is preferred or removed; "
                                                    "both are written as claims (ruled 2026-09-07)",
                                  "_nflverse_side_is_a_claim": True,
                                  "_resolved_by": kind})
    out = {"source": {"source_id": SRC_ID, "name": DECL["name"],
                      "stated_by": DECL["stated_by"], "acquisition": DECL["acquisition"]},
           "claims": claims, "disagreements": disagreements, "unresolved": unresolved,
           "counts": {"rows_read": len(rows), "resolved": len(claims),
                      "unresolved": len(unresolved),
                      "distinct_people": len({c["subject"][1] for c in claims}),
                      "disagreements": len(disagreements),
                      "by_resolution": dict(how), "by_field": dict(nfield)}}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(out, os.path.join(BASE, "build", "nflverse-draft.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main()
    c = o["counts"]
    print(f"  rows read        {c['rows_read']:,}")
    print(f"  resolved         {c['resolved']:,}  ({c['distinct_people']:,} distinct people)")
    print(f"  unresolved       {c['unresolved']:,}")
    print(f"  disagreements    {c['disagreements']:,}")
    print("  by resolution route:")
    for k, v in sorted(c["by_resolution"].items(), key=lambda x: -x[1]):
        print(f"     {v:6,}  {k}")
