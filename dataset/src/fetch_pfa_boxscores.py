"""Fetch Pro Football Archives' BOX SCORES -- the whole class, not the part that
happened to be asked for.

WHY THIS RUN EXISTS, AND THE DEFECT IS THE POINT. 2,888 box scores are on disk and
every one of them is 1920-1959. Not because PFA stops there -- it runs to 2025 --
but because only the 1920-1959 SEASON INDEXES were ever cached. Nobody ever asked
for a 1960 index, so no 1960 box score was ever linked, so the denominator looked
complete. A DENOMINATOR BUILT FROM WHAT CAME BACK CAN NEVER REPORT A GAP. It is
the same defect the club-season enumeration hit, in a different costume.

ENUMERATED FROM PFA'S OWN INDEXES, FETCHED IN THIS RUN, NOT FROM THE CACHE.
  /boxscores.html          the master index -- every season index PFA publishes
  /<year><league>-boxscores.html   one per league-season, ALL of them re-fetched
  -> /nflboxscores1/... and /nflboxscores2/...   the box scores themselves

All 121 season indexes are re-fetched even though 45 are cached, so the
denominator is ONE thing measured at ONE time rather than a mixture of today and
whenever the cache was filled.

THE 2,888 ALREADY HELD ARE ADOPTED, NOT RE-FETCHED. They live in pgm3-sources/pfa2
under a flattened name; they are copied into this tree so that ONE directory and
ONE manifest cover the whole class and the verification can count both ways over
all of it. Their capture time is NOT KNOWN -- pfa2 has no manifest -- so the row
says so and records the file's mtime as evidence rather than inventing a time.
The pfa2 copies are left exactly where they are; nothing is deleted.

Politeness, kill-safety, resume, absences and verification all come from
src/polite_fetch.py, which has ONE implementation. Re-proved per caller, and
proved for THIS caller in this run rather than carried forward.

  python3 src/fetch_pfa_boxscores.py --enumerate   indexes + target list, no box scores
  python3 src/fetch_pfa_boxscores.py               fetch, resuming from the manifest
  python3 src/fetch_pfa_boxscores.py --status      what is done, what is left
  python3 src/fetch_pfa_boxscores.py --verify      re-hash everything, count both ways
"""
import os, re, sys, json, time, shutil, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import polite_fetch as PF

SITE = "https://www.profootballarchives.com"
UA = ("pgm3-archive-preservation/1.0 (personal football history archive; "
      "one request per second, no concurrency; contact ryannecci@gmail.com)")
DELAY = 1.0
OLD_CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
DEST = os.path.expanduser("~/Documents/pgm3-sources/pfa-boxscores")
MANIFEST = os.path.join(DEST, "manifest.json")
TARGETS = os.path.join(DEST, "targets.json")
MASTER = "/boxscores.html"

HEADER = {
    "_what": "Pro Football Archives box scores, and the season indexes they were "
             "enumerated from. One manifest row per page; absences are rows too.",
    "_rights": "profootballarchives.com. Held for consultation and citation, not "
               "republished. Fetched at one request per second, no concurrency.",
    "_enumeration": "from PFA's own /boxscores.html and every season index it names, "
                    "ALL re-fetched in this run. The denominator is what the site "
                    "publishes, not what a previous fetch happened to bring back.",
    "_adopted": "rows marked origin=pfa2 were already on disk from an earlier run and "
                "were COPIED, not re-fetched. Their capture time is unknown.",
}

IDX = re.compile(r'href="([^"]*?(\d{4}[a-z]+)-boxscores\.html)"')
BOX = re.compile(r'href="([^"]*/nflboxscores[12]/[^"]+\.html)"')


def path_of(href):
    """A site-relative path, whether the page wrote one or a full URL."""
    h = href.split("profootballarchives.com")[-1]
    return h if h.startswith("/") else "/" + h


def get(url, man, rel, kind, run=None):
    """Fetch one page into the tree and record it. Returns the bytes, or None."""
    body, status, err = PF.fetch(url, DELAY, UA)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    if body is not None:
        PF.write_file(DEST, rel, body)
        man["files"][rel] = {"sha256": PF.sha(body), "bytes": len(body), "fetched_at": now,
                             "url": url, "kind": kind, "http_status": status}
        if run: run["fetched"] += 1
    else:
        man["absences"][rel] = {
            "file": rel, "url": url, "kind": kind, "http_status": status, "error": err,
            "why": ("the site answered 404 for a link its own index carries: the link "
                    "exists and the page does not") if status == 404 else
                   ("did not succeed after four tries with widening back-off; recorded "
                    "rather than retried harder"),
            "when": now}
        if run: run["absent" if status == 404 else "failed"] += 1
    PF.save(man, MANIFEST)
    return body


def adopt(man, targets):
    """The 2,888 already on disk. Copied, hashed, and recorded as what they are."""
    n = 0
    for t in targets:
        if t["file"] in man["files"]: continue
        flat = t["file"].replace("/", "_")                 # nflboxscores1/x -> nflboxscores1_x
        src = os.path.join(OLD_CACHE, flat)
        if not os.path.exists(src): continue
        b = open(src, "rb").read()
        p = PF.write_file(DEST, t["file"], b)
        man["files"][t["file"]] = {
            "sha256": PF.sha(b), "bytes": len(b), "fetched_at": None,
            "url": t["url"], "kind": t["kind"], "http_status": None,
            "origin": "pfa2", "_capture_time": "NOT KNOWN -- pfa2 carries no manifest",
            "mtime_on_disk": datetime.datetime.fromtimestamp(
                os.path.getmtime(src)).isoformat(timespec="seconds")}
        n += 1
    PF.save(man, MANIFEST)
    return n


def enumerate_targets():
    os.makedirs(DEST, exist_ok=True)
    man = PF.load(MANIFEST, HEADER)
    man["started"] = man["started"] or datetime.datetime.now().isoformat(timespec="seconds")

    b = get(SITE + MASTER, man, "indexes/boxscores.html", "master_index")
    if b is None:
        print("the master index did not answer; nothing enumerated", file=sys.stderr); sys.exit(2)
    seasons = sorted({path_of(h) for h, _key in IDX.findall(b.decode("utf-8", "replace"))})
    print(f"master index names {len(seasons):,} season indexes", flush=True)

    boxes, per_season, empty = {}, {}, []
    for i, s in enumerate(seasons, 1):
        rel = "indexes/" + s.lstrip("/")
        sb = get(SITE + s, man, rel, "season_index")
        found = set()
        if sb is not None:
            found = {path_of(h) for h in BOX.findall(sb.decode("utf-8", "replace"))}
            for f in found: boxes[f] = s
        per_season[s] = len(found)
        if not found: empty.append(s)
        if i % 20 == 0 or i == len(seasons):
            print(f"  indexes {i:>3}/{len(seasons)}  box scores so far {len(boxes):,}", flush=True)
        time.sleep(DELAY)

    targets = [{"file": p.lstrip("/"), "url": SITE + p, "kind": "boxscore",
                "from_index": boxes[p]} for p in sorted(boxes)]
    adopted = adopt(man, targets)
    dirs = collections.Counter(t["file"].split("/")[0] for t in targets)
    years = collections.Counter(re.search(r"/(\d{4})", t["url"]).group(1) for t in targets)

    json.dump({"_enumerated_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "_root": SITE + MASTER,
               "_all_indexes_refetched": True,
               "counts": {"season_indexes": len(seasons), "box_scores": len(targets),
                          "already_held_and_adopted": adopted,
                          "to_fetch": len(targets) - adopted,
                          "by_directory": dict(dirs)},
               "season_indexes_naming_no_box_score": empty,
               "per_season": per_season, "targets": targets},
              open(TARGETS, "w"), indent=1)

    print(f"\nseason indexes          {len(seasons):>7,}")
    print(f"  naming no box score   {len(empty):>7,}  {empty if len(empty) < 8 else ''}")
    print(f"box scores enumerated   {len(targets):>7,}   {dict(dirs)}")
    print(f"  already held, adopted {adopted:>7,}")
    print(f"  NEVER FETCHED         {len(targets)-adopted:>7,}")
    print(f"years {min(years)}-{max(years)}")
    return targets


def main():
    argv = sys.argv[1:]
    if "--enumerate" in argv:
        enumerate_targets(); return
    if not os.path.exists(TARGETS):
        print("no target list; run --enumerate first", file=sys.stderr); sys.exit(2)
    targets = json.load(open(TARGETS))["targets"]
    man = PF.load(MANIFEST, HEADER)

    if "--verify" in argv:
        sys.exit(0 if PF.verify(man, DEST) else 1)

    left = PF.todo(man, targets, DEST)
    if "--status" in argv:
        ad = sum(1 for r in man["files"].values() if r.get("origin") == "pfa2")
        print(f"targets {len(targets):,}   done {len(targets)-len(left):,} "
              f"(adopted {ad:,})   to fetch {len(left):,}   "
              f"absences {len(man['absences']):,}")
        return

    run = {"began": datetime.datetime.now().isoformat(timespec="seconds"),
           "fetched": 0, "absent": 0, "failed": 0, "pid": os.getpid()}
    man["runs"].append(run); PF.save(man, MANIFEST)
    print(f"to fetch {len(left):,} of {len(targets):,}"
          f"  (~{len(left)*DELAY/3600:.1f}h at {DELAY}s)", flush=True)

    for i, t in enumerate(left, 1):
        get(t["url"], man, t["file"], t["kind"], run)
        if i % 250 == 0 or i == len(left):
            print(f"  {i:>6,}/{len(left):,}  fetched {run['fetched']:,}  "
                  f"absent {run['absent']:,}  failed {run['failed']:,}  "
                  f"{datetime.datetime.now():%H:%M:%S}", flush=True)
        time.sleep(DELAY)
    run["ended"] = datetime.datetime.now().isoformat(timespec="seconds")
    PF.save(man, MANIFEST)
    print("done.", flush=True)
    PF.verify(man, DEST)


if __name__ == "__main__":
    main()
