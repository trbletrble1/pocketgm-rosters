"""Inventory Pro Football Archives section by section against archive coverage.

Three quantities, kept apart:
  cached  - pages of this section on disk in ~/Documents/pgm3-sources/pfa2
  linked  - distinct pages of this section PFA's own cached pages link to
  cited   - distinct pages of this section a claim in the read model names
Sections come from PFA's own navigation (nav.html, embedded in older pages),
not from the shape of what happens to have been fetched.

Nothing is fetched. This reads the cache and the read model only.
"""
import os, re, sys, sqlite3, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
import paths

CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
# PFA's own top navigation, read from the topnav div of a cached season page.
NAV = ["Home", "Leagues", "Seasons", "Teams", "Players", "Coaches",
       "Drafts", "Awards", "Leaderboards"]
PFA_SOURCE_IDS = ("pro-football-archives", "pfa-transactions", "pfa-boxscores")


def section(path):
    """Classify a PFA path. Tests the whole path, not the basename: boxscore
    pages live under nflboxscores<n>/ with a game id for a filename."""
    p = path.replace("\\", "/").lstrip("/")
    b = os.path.basename(p)
    if "gamelog" in p:                       return "player game logs"
    if "playoffs" in p:                      return "player playoff logs"
    if "boxscore" in p:                      return "boxscores"
    if p.startswith("lineups/"):             return "boxscores (derived lineups)"
    if "players" in p:                       return "players"
    if "coaches" in p or p.startswith("staff/"): return "coaches / staff"
    if "officials" in p:                     return "officials"
    if "draft" in b:                         return "drafts"
    if "award" in b:                         return "awards"
    if "leader" in b:                        return "leaderboards"
    if re.match(r"^\d{4}\.html$", b):        return "season index"
    if re.match(r"^\d{4}[a-z]{2,10}\.html$", b): return "team-seasons"
    if b in ("leagues.html", "seasons.html", "teams.html", "players.html",
             "coaches.html", "drafts.html", "awards.html",
             "leaderboards.html", "index.html", "nav.html"): return "nav/index"
    return "unclassified"


def href(h):
    h = h.split("#")[0].split("?")[0].strip()
    if not h or h.startswith(("http", "javascript", "mailto")):
        return None
    return h.lstrip("/") if h.endswith(".html") else None


def main():
    have = set(os.listdir(CACHE))
    files = [f for f in have if f.endswith(".html")]

    linked = collections.defaultdict(set)
    for f in files:
        with open(os.path.join(CACHE, f), encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        for h in re.findall(r'href=["\']?([^"\'> ]+)', text):
            n = href(h)
            if n:
                linked[section(n)].add(n)

    conn = sqlite3.connect(paths.READ_MODEL)
    claims = collections.Counter()
    cited = collections.defaultdict(set)
    q = ("select source_record, count(*) from claim where source_id in (%s) "
         "group by source_record" % ",".join("?" * len(PFA_SOURCE_IDS)))
    for sr, n in conn.execute(q, PFA_SOURCE_IDS):
        loc = sr.split("#", 1)[1] if "#" in sr else sr
        s = section(loc)
        claims[s] += n
        cited[s].add(loc)

    def on_disk(n):
        return n in have or n.replace("/", "_") in have or os.path.basename(n) in have

    sections = sorted(set(linked) | {section(f) for f in files} | set(claims))
    rows = []
    for s in sections:
        rows.append((s,
                     sum(1 for f in files if section(f) == s),
                     len(linked.get(s, ())),
                     len([n for n in linked.get(s, ()) if not on_disk(n)]),
                     len(cited.get(s, ())),
                     claims.get(s, 0)))

    print("PFA navigation, as PFA states it: " + " | ".join(NAV))
    print()
    hdr = f"{'section':28s}{'cached':>8s}{'linked':>9s}{'not on disk':>13s}{'cited':>9s}{'claims':>12s}"
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r[0]:28s}{r[1]:>8,}{r[2]:>9,}{r[3]:>13,}{r[4]:>9,}{r[5]:>12,}")
    print("-" * len(hdr))
    print(f"{'total':28s}{len(files):>8,}{sum(r[2] for r in rows):>9,}"
          f"{sum(r[3] for r in rows):>13,}{sum(r[4] for r in rows):>9,}"
          f"{sum(claims.values()):>12,}")
    if claims.get("unclassified"):
        print("\nunclassified locator patterns:")
        pat = collections.Counter(re.sub(r"\d", "#", l) for l in cited["unclassified"])
        for p, c in pat.most_common(10):
            print(f"   {c:>6,}  {p}")


if __name__ == "__main__":
    main()
