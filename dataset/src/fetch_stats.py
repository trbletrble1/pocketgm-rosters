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
    sizes, bad = [], []
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
                h = F._get(URL.format(team=t, year=y), key); got += 1
                # A page can be non-empty, HTTP 200 and correctly cached while
                # carrying nothing - eight media-guide texts under 6KB passed
                # every zero-byte check that way. Record the size so an
                # implausible one is VISIBLE rather than counted as a success.
                sizes.append((len(h), t, y))
            except Exception as e:
                fail += 1
                bad.append((t, y, type(e).__name__))
                print(f"    {t} {y}: {type(e).__name__}", flush=True)
        print(f"  {league} {y}: {len(teams)} teams  fetched={got} held={held} failed={fail}",
              flush=True)
    print(f"\n{league}: fetched {got}  already held {held}  failed {fail}")
    if sizes:
        sizes.sort()
        med = sizes[len(sizes)//2][0]
        print(f"page size: median {med//1024}KB  smallest {sizes[0][0]}b "
              f"({sizes[0][1]} {sizes[0][2]})  largest {sizes[-1][0]//1024}KB")
        tiny = [x for x in sizes if x[0] < med // 4]
        print(f"pages under a quarter of median (LOOK AT THESE): {len(tiny)}")
        for n, t, y in tiny[:12]: print(f"   {n:>7}b  {t} {y}")
    if bad:
        print("failures:")
        for t, y, e in bad[:15]: print(f"   {t} {y}: {e}")


if __name__ == "__main__":
    main()
