"""Run ingest_season across many league-years, caching every page once.

Rate: one request per second or slower, and a page already on disk is never
re-fetched (fetch_statscrew.get checks the cache before the network).
"""
import os, sys, json, subprocess, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")

def run(league, year, skip_xref=True, floor="0.95"):
    env = dict(os.environ, LEAGUE=league, YEAR=str(year),
               SKIP_XREF="1" if skip_xref else "0", MATCH_FLOOR=floor,
               SC_CACHE=os.environ.get("SC_CACHE",
                   os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep")))
    r = subprocess.run([sys.executable, os.path.join(HERE, "ingest_season.py")],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr

def main():
    league = sys.argv[1]
    years = [int(y) for y in sys.argv[2:]]
    summary, devs, failures = [], [], []
    for y in years:
        t0 = time.time()
        code, out, err = run(league, y)
        if code != 0:
            failures.append((league, y, (err.strip().splitlines() or ["?"])[-1][:120]))
            print(f"  {league} {y}: FAILED  {failures[-1][2]}", flush=True); continue
        stats = {}
        for line in out.splitlines():
            if line.startswith("rows "):
                p = line.split()
                stats.update({"rows": int(p[1]), "denotations": int(p[3]),
                              "persons": int(p[6]), "absences": int(p[8])})
            if line.startswith("teams:"):
                stats["teams"] = int(line.split()[1])
        d = os.path.join(BASE, "build", f"dev-{league.lower()}-{y}.json")
        dv = json.load(open(d)) if os.path.exists(d) else []
        devs += dv
        summary.append({"league": league, "year": y, **stats, "deviations": len(dv)})
        print(f"  {league} {y}: teams={stats.get('teams','?'):>3} rows={stats.get('rows',0):>4} "
              f"persons={stats.get('persons',0):>4} dev={len(dv)}  [{time.time()-t0:.0f}s]", flush=True)
    out_p = os.path.join(BASE, "build-reports", f"sweep-{league.lower()}.json")
    json.dump({"summary": summary, "deviations": devs, "failures": failures},
              open(out_p, "w"), indent=1)
    print(f"\nseasons ok {len(summary)}  failed {len(failures)}  deviations {len(devs)}")

if __name__ == "__main__":
    main()
