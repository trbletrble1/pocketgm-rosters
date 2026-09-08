"""Restore the CFL 1945 season keys that were never written.

THE BUG: the CFL 1945 ingest wrote a `person_season` for 207 men but a `stint` for
only 150. The index builds its `seasons` dict from STINTS, so 60 men -- every one
of them on a western club with roster data but no statistics -- ended up with a
person_season for 1945 and an empty season key. Nineteen of them had no other
season at all, which is the only reason the no-seasons test noticed.

THE CLUB IS RECOVERABLE and is not guessed: the denotation's source_record reads
'statscrew#roster/CFLCGY-1945#George Alexander', so the club code is in the record
that created the man. A season is restored only where that club can be read.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
IDX_PATH = os.path.join(BASE, "build-reports", "person-index.json")
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import index_io as IO  # atomic index write
ROSTER = re.compile(r"statscrew#roster/([A-Z0-9]+)-(\d{4})#")


class RestoreError(Exception):
    pass


def main(write=True):
    d = json.load(open(os.path.join(BASE, "build", "cfl-1945.json")))
    stint_people = {c["subject"][1] for c in d["claims"] if c["subject"][0] == "stint"}
    ps_people = {c["subject"][1] for c in d["claims"] if c["subject"][0] == "person_season"}
    need = ps_people - stint_people
    # legacy p_ id -> (slug, club, year) from the denotation that created him
    info = {}
    for x in d["denotations"]:
        p = x.get("person")
        if p not in need:
            continue
        m = ROSTER.match(x.get("source_record") or "")
        slug = (x.get("matched_against") or "").split(":")[-1]
        if m and slug:
            info[p] = {"slug": slug, "club": m.group(1), "year": int(m.group(2))}
    idx = json.load(open(IDX_PATH))
    by_slug = {}
    for pid, v in idx.items():
        if pid == "_clubs":
            continue
        for s in (v.get("slugs") or []):
            by_slug[s] = pid
    restored, unmatched, noclub = [], [], []
    for p in sorted(need):
        i = info.get(p)
        if not i:
            noclub.append(p); continue
        pid = by_slug.get(i["slug"])
        if not pid:
            unmatched.append((p, i["slug"])); continue
        key = f"CFL|{i['year']}|{i['club']}"
        rec = idx[pid].setdefault("seasons", {})
        if key in rec:
            continue
        rec[key] = {"stats": {}, "stint": {},
                    "_restored_from": "person_season + the denotation's roster "
                                      "source_record; the club was READ, not inferred",
                    "_no_stint_in_source": "StatsCrew has a roster line for this man "
                                           "and no statistics, so no stint exists"}
        restored.append({"person_id": pid, "legacy": p, "slug": i["slug"], "key": key})
    out = {"restored": restored, "unmatched_slug": unmatched, "no_club_in_record": noclub,
           "counts": {"person_season_without_stint": len(need),
                      "restored": len(restored),
                      "slug_not_in_index": len(unmatched),
                      "club_not_readable": len(noclub),
                      "clubs": dict(collections.Counter(r["key"] for r in restored))}}
    if write:
        IO.save_index(idx)
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store -- and this one is written DURING
        # a rebuild, as a chain step, which is precisely when another session may read.
        # A truncated store was skipped by `except Exception: continue` and cost a
        # rebuild 300+ silently dropped people.
        IO.dump_atomic(out, os.path.join(BASE, "build", "cfl1945-season-restore.json"), indent=1)
    return out


if __name__ == "__main__":
    o = main(); c = o["counts"]
    for k, v in c.items():
        print(f"  {k:28s} {v}")
