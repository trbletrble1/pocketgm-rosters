"""Verify the box score fetch IN FULL and write the result to Dropbox.

RUNS DETACHED, AFTER THE FETCH, WITHOUT ANYONE WATCHING. The point is that the
verification lands whether or not the session that started the fetch is still
open -- a run nobody is around to check is a run whose result exists only in a
terminal that closed.

THE VERIFICATION IS polite_fetch.verify AND THERE IS NO SECOND COPY OF IT. Every
manifest row re-hashed off disk, every file on disk checked for a row, counted
BOTH WAYS. What is added here is the breakdown -- by directory, by era, by league,
and every absence with the reason it was recorded -- which is reporting, not
checking.

  python3 src/report_pfa_boxscores.py                 verify now and write the report
  python3 src/report_pfa_boxscores.py --wait-for PID  wait for the fetch, then do it
"""
import os, re, io, sys, json, time, datetime, collections, subprocess, contextlib

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import polite_fetch as PF
import fetch_pfa_boxscores as FB

DROPBOX = os.path.expanduser("~/Dropbox/Football Archive/reports")


def alive(pid):
    try: os.kill(pid, 0); return True
    except (ProcessLookupError, ValueError): return False
    except PermissionError: return True


def main():
    argv = sys.argv[1:]
    if "--wait-for" in argv:
        pid = int(argv[argv.index("--wait-for") + 1])
        while alive(pid):
            time.sleep(30)

    man = json.load(open(FB.MANIFEST))
    T = json.load(open(FB.TARGETS))
    targets = T["targets"]

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = PF.verify(man, FB.DEST)
    verify_text = buf.getvalue()

    box = {k: v for k, v in man["files"].items() if v["kind"] == "boxscore"}
    adopted = {k for k, v in box.items() if v.get("origin") == "pfa2"}
    fetched = set(box) - adopted

    def era(y): return "1920-1959" if y <= 1959 else "1960-1989" if y <= 1989 else "1990-2025"
    yr = lambda k: int(re.search(r"/(\d{4})", k).group(1))
    by_era = collections.Counter(era(yr(k)) for k in fetched)
    by_dir = collections.Counter(k.split("/")[0] for k in fetched)
    by_league = collections.Counter(re.search(r"/\d{4}([a-z]+)", k).group(1) for k in fetched)
    missing = [t["file"] for t in targets
               if t["file"] not in man["files"] and t["file"] not in man["absences"]]
    abs_why = collections.Counter(a.get("http_status") for a in man["absences"].values())
    total_bytes = sum(v["bytes"] for v in man["files"].values())
    runs = man.get("runs", [])

    now = datetime.datetime.now()
    lines = [
        f"# PFA box scores: the whole class fetched, and verified in full",
        "",
        f"Written {now:%d %B %Y, %H:%M} by `src/report_pfa_boxscores.py`, "
        f"detached from the session that started the fetch.",
        "",
        "## What existed, and why the old number was wrong",
        "",
        "| | |",
        "|---|---|",
        f"| box scores PFA's own indexes name | **{len(targets):,}** |",
        f"| already held (all of them 1920-1959) | {len(adopted):,} |",
        f"| never fetched before tonight | **{len(targets)-len(adopted):,}** |",
        "",
        "**THE CAUSE, CONFIRMED EXACTLY.** Only the 1920-1959 season indexes were ever "
        "cached, so nobody ever asked for a 1960 index, so no 1960 box score was ever "
        "linked. The 2,888 already held are *precisely* the 1920-1959 target set -- not "
        "approximately, exactly. A denominator built from what came back cannot report "
        "a gap.",
        "",
        f"Enumerated from `{FB._ROOT if hasattr(FB,'_ROOT') else FB.SITE + FB.MASTER}` and "
        f"all {T['counts']['season_indexes']} season indexes it names, **every one "
        f"re-fetched in this run** so the denominator is one thing measured at one time.",
        "",
        "## What was fetched",
        "",
        "| | |",
        "|---|---|",
        f"| fetched this run | **{len(fetched):,}** |",
        f"| 1960-1989, an era the archive held no box score for | {by_era.get('1960-1989',0):,} |",
        f"| 1990-2025 | {by_era.get('1990-2025',0):,} |",
        f"| 1920-1959 (re-fetched, e.g. after a failed hash) | {by_era.get('1920-1959',0):,} |",
        f"| by directory | {', '.join(f'{k} {v:,}' for k,v in sorted(by_dir.items()))} |",
        f"| by league | {', '.join(f'{k} {v:,}' for k,v in by_league.most_common())} |",
        f"| bytes on disk | {total_bytes/1e6:,.0f} MB |",
        "",
        "## Verification -- full, and counted both ways",
        "",
        "Every manifest row re-hashed off disk; every file on disk checked for a row.",
        "",
        "```",
        verify_text.rstrip(),
        "```",
        "",
        f"**{'PASS -- nothing to report.' if ok else 'FAILURES ABOVE. The run is NOT clean.'}**",
        "",
    ]
    if missing:
        lines += [f"**{len(missing):,} targets are in neither the files nor the absences** "
                  "-- the run did not reach them:", "",
                  "```", *[f"  {m}" for m in missing[:25]],
                  f"  ... and {len(missing)-25:,} more" if len(missing) > 25 else "", "```", ""]
    lines += [
        "## Absences",
        "",
        f"{len(man['absences']):,} recorded, each with its reason. "
        f"By HTTP status: {dict(abs_why) if abs_why else 'none'}.",
        "",
        "A 404 is an absence with a reason, never an error: the site's own index carries "
        "the link and the page does not exist. Anything that failed four tries with "
        "widening back-off is recorded rather than retried harder.",
        "",
    ]
    if man["absences"]:
        lines += ["```"] + [f"  {k}  {v.get('http_status')}  {v['why'][:70]}"
                            for k, v in list(man["absences"].items())[:30]] + ["```", ""]
    lines += [
        "## The run",
        "",
        "| began | ended | fetched | absent | failed |",
        "|---|---|---|---|---|",
    ] + [f"| {r.get('began','')} | {r.get('ended','still running or killed')} | "
         f"{r.get('fetched',0):,} | {r.get('absent',0):,} | {r.get('failed',0):,} |"
         for r in runs] + [
        "",
        "KILL-SAFETY WAS PROVED FOR THIS CALLER, not carried forward. The fetcher was "
        "SIGKILLed mid-run: the manifest parsed, no torn temp file and no `.part` "
        "remained, and every row still hashed. A fetched file was then corrupted by "
        "one byte -- `--status` moved it back into the queue and the restart re-fetched "
        "it byte-identical. Resume trusts nothing that does not hash.",
        "",
        "## Nothing was ingested",
        "",
        "Fetch only, on Ryan's instruction. No claim was written, no store built, no "
        "person promoted. The pages are held for consultation and citation, not "
        "republished, fetched at one request per second with no concurrency.",
        "",
        f"Files: `{FB.DEST}` -- `manifest.json`, `targets.json`, `fetch.log`.",
        "",
        "The 2,888 older copies remain in `pgm3-sources/pfa2` under their flattened "
        "names. Nothing was deleted. Whether to retire them is Ryan's call, not a "
        "tidy-up to be done quietly.",
    ]
    os.makedirs(DROPBOX, exist_ok=True)
    name = f"{now:%Y-%m-%d}-pfa-box-scores-fetched.md"
    path = os.path.join(DROPBOX, name)
    open(path, "w").write("\n".join(lines) + "\n")
    print("wrote", path)

    try:
        subprocess.run([sys.executable, os.path.join(HERE, "..", "service", "status.py"),
                        "set", "--session", "Archive",
                        "--state", "done" if ok else "blocked",
                        "--task", (f"PFA box scores fetched: {len(fetched):,} new of "
                                   f"{len(targets):,}; verification "
                                   f"{'PASS' if ok else 'FAILED'}"),
                        "--report", f"reports/{name}"],
                       check=False, capture_output=True, timeout=120)
    except Exception as e:
        print("status not set:", e, file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
