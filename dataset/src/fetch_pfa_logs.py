"""Fetch Pro Football Archives' per-player GAME LOGS and PLAYOFF LOGS.

ENUMERATED BEFORE FETCHING, so the denominator is known and not inferred from what
came back. The list is built offline from pages the archive already holds:
  * game logs   -- the 26 cached index pages nflgamelogs-a.html .. -z.html, plus any
                   /gamelogs/ link found on any other cached page
  * playoff logs-- there is NO cached playoff index, so these are enumerated from the
                   50,829 cached player pages themselves. That is a floor, not a
                   ceiling: a playoff log for a man whose player page is not cached
                   cannot be seen from here, and the manifest says so.

Politeness, kill-safety, resume, absences and verification all come from
src/polite_fetch.py, which has ONE implementation and is re-proved per caller.

  python3 src/fetch_pfa_logs.py --enumerate    build the target list, fetch nothing
  python3 src/fetch_pfa_logs.py                fetch, resuming from the manifest
  python3 src/fetch_pfa_logs.py --status       what is done, what is left
  python3 src/fetch_pfa_logs.py --verify       re-hash every file against the manifest
"""
import os, re, sys, json, time, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import polite_fetch as PF

SITE = "https://www.profootballarchives.com"
UA = ("pgm3-archive-preservation/1.0 (personal football history archive; "
      "one request per second, no concurrency; contact ryannecci@gmail.com)")
DELAY = 1.0
CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
DEST = os.path.expanduser("~/Documents/pgm3-sources/pfa-logs")
MANIFEST = os.path.join(DEST, "manifest.json")
TARGETS = os.path.join(DEST, "targets.json")

HEADER = {
    "_what": "Pro Football Archives per-player game logs and playoff logs. One row per "
             "page; absences are rows too.",
    "_rights": "profootballarchives.com. Held for consultation and citation, not "
               "republished. Fetched at one request per second with no concurrency.",
    "_enumeration": "built offline from pages already held, before any fetch, so the "
                    "denominator is known rather than inferred from what came back.",
}
GL = re.compile(rb'href="(/gamelogs/[a-z]/[^"]+\.html)"')
PL = re.compile(rb'href="(/playoffs/[a-z]/[^"]+\.html)"')


def enumerate_targets():
    gl, pl = set(), set()
    n_idx = n_any = 0
    for f in sorted(os.listdir(CACHE)):
        p = os.path.join(CACHE, f)
        if not os.path.isfile(p): continue
        try: b = open(p, "rb").read()
        except Exception: continue
        n_any += 1
        if re.fullmatch(r"nflgamelogs-[a-z]\.html", f): n_idx += 1
        gl |= {m.decode() for m in GL.findall(b)}
        pl |= {m.decode() for m in PL.findall(b)}
    def row(path, kind):
        # /gamelogs/a/aban00100.html -> gamelogs/a/aban00100.html, kept as a tree so
        # 33,750 files do not land in one directory
        rel = path.lstrip("/")
        return {"file": rel, "url": SITE + path, "kind": kind}
    targets = [row(x, "gamelog") for x in sorted(gl)] + [row(x, "playofflog") for x in sorted(pl)]
    os.makedirs(DEST, exist_ok=True)
    json.dump({"_enumerated_at": datetime.datetime.now().isoformat(timespec="seconds"),
               "_cache_pages_read": n_any, "_gamelog_index_pages": n_idx,
               "_playoff_index": "NONE EXISTS in the cache; playoff logs are enumerated "
                                 "from player pages, which is a floor and not a ceiling",
               "counts": {"gamelogs": len(gl), "playofflogs": len(pl), "total": len(targets)},
               "targets": targets}, open(TARGETS, "w"), indent=1)
    print(f"cache pages read        {n_any:>7,}")
    print(f"  gamelog index pages   {n_idx:>7,}")
    print(f"game logs enumerated    {len(gl):>7,}")
    print(f"playoff logs enumerated {len(pl):>7,}")
    print(f"TOTAL                   {len(targets):>7,}")
    return targets


def main():
    argv = sys.argv[1:]
    if "--enumerate" in argv:
        enumerate_targets(); return
    if not os.path.exists(TARGETS):
        print("no target list; run --enumerate first", file=sys.stderr); sys.exit(2)
    T = json.load(open(TARGETS)); targets = T["targets"]
    man = PF.load(MANIFEST, HEADER)

    if "--verify" in argv:
        sys.exit(0 if PF.verify(man, DEST) else 1)

    left = PF.todo(man, targets, DEST)
    if "--status" in argv:
        print(f"targets {len(targets):,}   done {len(targets)-len(left):,}   "
              f"to fetch {len(left):,}   absences {len(man['absences']):,}")
        return

    man["started"] = man["started"] or datetime.datetime.now().isoformat(timespec="seconds")
    run = {"began": datetime.datetime.now().isoformat(timespec="seconds"),
           "fetched": 0, "absent": 0, "failed": 0}
    man["runs"].append(run); PF.save(man, MANIFEST)
    print(f"to fetch {len(left):,} of {len(targets):,}", flush=True)

    for i, t in enumerate(left, 1):
        body, status, err = PF.fetch(t["url"], DELAY, UA)
        if body is not None:
            PF.write_file(DEST, t["file"], body)
            man["files"][t["file"]] = {
                "sha256": PF.sha(body), "bytes": len(body),
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "url": t["url"], "kind": t["kind"], "http_status": status}
            run["fetched"] += 1
        elif status == 404:
            man["absences"][t["file"]] = {
                "file": t["file"], "url": t["url"], "kind": t["kind"], "http_status": 404,
                "why": "the site answered 404 for a link its own pages carry: the link "
                       "exists and the page does not",
                "when": datetime.datetime.now().isoformat(timespec="seconds")}
            run["absent"] += 1
        else:
            man["absences"][t["file"]] = {
                "file": t["file"], "url": t["url"], "kind": t["kind"],
                "http_status": status, "error": err,
                "why": "did not succeed after four tries with widening back-off; recorded "
                       "rather than retried harder",
                "when": datetime.datetime.now().isoformat(timespec="seconds")}
            run["failed"] += 1
        PF.save(man, MANIFEST)
        if i % 250 == 0 or i == len(left):
            print(f"  {i:>6,}/{len(left):,}  fetched {run['fetched']:,}  "
                  f"absent {run['absent']:,}  failed {run['failed']:,}", flush=True)
        time.sleep(DELAY)
    run["ended"] = datetime.datetime.now().isoformat(timespec="seconds")
    PF.save(man, MANIFEST)
    print("done.", flush=True)
    PF.verify(man, DEST)


if __name__ == "__main__":
    main()
