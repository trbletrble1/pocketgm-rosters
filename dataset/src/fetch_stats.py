"""Fetch StatsCrew team-season STATISTICS pages: stats/t-{TEAM}/y-{YEAR}.

Same host, same declared source, same cache disciplines as the roster fetch.
Team membership comes from the roster cache, so no league page is re-fetched.

  python3 src/fetch_stats.py <LEAGUE> [years...]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("SC_CACHE", os.path.expanduser("~/Documents/pgm3-sources/statscrew/sweep"))
import fetch_statscrew as F

URL = F._DECL["url_patterns"].get("team_stats",
      "https://www.statscrew.com/football/stats/t-{team}/y-{year}")


def main():
    league = sys.argv[1]
    years = [int(y) for y in sys.argv[2:]]
    got = held = fail = 0
    for y in years:
        try:
            teams = F.teams_in(league, y)
        except Exception as e:
            print(f"  {league} {y}: league page {type(e).__name__}", flush=True); continue
        for t in sorted(teams):
            key = f"S_{t}_{y}"
            p = os.path.join(F.CACHE, key + ".html")
            if os.path.exists(p) and os.path.getsize(p) > 0:
                held += 1; continue
            try:
                F._get(URL.format(team=t, year=y), key); got += 1
            except Exception as e:
                fail += 1
                print(f"    {t} {y}: {type(e).__name__}", flush=True)
        print(f"  {league} {y}: {len(teams)} teams  fetched={got} held={held} failed={fail}",
              flush=True)
    print(f"\n{league}: fetched {got}  already held {held}  failed {fail}")


if __name__ == "__main__":
    main()
