"""The club table: one lookup for every club string every source uses.

A CLUB is a chain of code-segments -- (code, first year, last year) -- with every
name it carried and the years each applied, its league by year, every string every
source uses for it, and its lineage where the evidence is mechanical.

THE LOOKUP IS ALWAYS (string, year). There WAS a Buffalo Bisons in 1946; a 1986
Buffalo Bisons is a source calling the Bills by a name they did not have, and the
table says so rather than mapping it into silence.

THE FAILURE IS LOUD. resolve() never returns None quietly: every string it cannot
map is recorded in self.refused and reported by census(), in the shape
club_keys.census() already prints through build_dashboard.
"""
import os, re, json, collections, unicodedata

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TABLE = os.path.join(BASE, "build", "clubs.json")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def nickname(name):
    """The last word of a club name, the part that survives a relocation."""
    w = [x for x in re.split(r"[\s/]+", (name or "").strip()) if x]
    return norm(w[-1]) if w else ""


def city(name):
    w = [x for x in (name or "").split() if x]
    return norm(" ".join(w[:-1])) if len(w) > 1 else ""


class Clubs:
    def __init__(self, path=TABLE):
        self.T = json.load(open(path))
        self.by_id = {c["id"]: c for c in self.T["clubs"]}
        self.by_code = collections.defaultdict(list)          # code -> [(first,last,id)]
        self.by_name = collections.defaultdict(list)          # norm(name) -> [(first,last,id,kind)]
        self.by_string = collections.defaultdict(list)        # (source, norm(string)) -> [(first,last,id,kind,league)]
        for c in self.T["clubs"]:
            for s in c["segments"]:
                self.by_code[s["code"]].append((s["first"], s["last"], c["id"]))
            for n in c["names"]:
                self.by_name[norm(n["name"])].append((n["first"], n["last"], c["id"], n["kind"]))
            for s in c["strings"]:
                self.by_string[(s["source"], norm(s["string"]))].append(
                    (s["first"], s["last"], c["id"], s["kind"], s.get("league")))
        self.refused = collections.Counter(); self.refused_example = {}

    # ------------------------------------------------------------ lookups
    def by_code_year(self, code, year):
        for f, l, cid in self.by_code.get(code, []):
            if f <= int(year) <= l: return cid
        return None

    def code_for(self, cid, year):
        for s in self.by_id[cid]["segments"]:
            if s["first"] <= int(year) <= s["last"]: return s["code"]
        return None

    def name_for(self, cid, year):
        for n in self.by_id[cid]["names"]:
            if n["kind"] == "official" and n["first"] <= int(year) <= n["last"]: return n["name"]
        return None

    def league_for(self, cid, year):
        for s in self.by_id[cid]["segments"]:
            for lg in s["leagues"]:
                if lg["first"] <= int(year) <= lg["last"]: return lg["league"]
        # a year beyond the archive's last held season: the league the source printed on that string, if one
        lgs = {s["league"] for s in self.by_id[cid]["strings"] if s["kind"] == "beyond_archive" and s.get("league") and s["first"] <= int(year) <= s["last"]}
        return next(iter(lgs)) if len(lgs) == 1 else None

    def resolve(self, string, year, league=None, source=None):
        """-> (club_id, kind) where kind is how it resolved: code, official, alias,
        wrong_for_season, source_string. Records every refusal."""
        yr = int(str(year)[-4:]) if str(year)[-4:].isdigit() else None
        if yr is None:
            self._refuse(string, year, league, source, "no parseable year"); return None
        cid = self.by_code_year(string, yr)
        if cid: return cid, "code"
        hits = [(f, l, c, k) for f, l, c, k in self.by_name.get(norm(string), []) if f <= yr <= l]
        if league: hits = [h for h in hits if self.league_for(h[2], yr) == league] or hits
        if len({h[2] for h in hits}) == 1:
            return hits[0][2], ("official" if any(h[3] == "official" for h in hits) else hits[0][3])
        if len(hits) > 1:
            self._refuse(string, yr, league, source, "ambiguous: more than one club under that name that year"); return None
        hits = {}                                                     # club id -> (kind, has a season that year)
        for src, ns in ([(source, norm(string))] if source else []) + [(s, norm(string)) for s in self.T["sources"]]:
            for f, l, c, k, lg in self.by_string.get((src, ns), []):
                if k == "code_misprinted": continue                   # kept as printed on the club it was printed for; never a lookup key
                if f <= yr <= l and (not league or not lg or lg == league):
                    hits.setdefault(c, (k, self.code_for(c, yr) is not None))
        if hits:
            played = {c: v for c, v in hits.items() if v[1]} or hits   # a club that fielded a team that year outranks one that did not
            if len(played) == 1:
                c, (k, _) = next(iter(played.items())); return c, k
            self._refuse(string, yr, league, source, f"ambiguous: that string names {len(played)} clubs that year"); return None
        self._refuse(string, yr, league, source, "no club under that string that year"); return None

    def _refuse(self, string, year, league, source, why):
        k = (source or "?", league or "?", str(year), string, why)
        self.refused[k] += 1; self.refused_example.setdefault(k, None)

    def census(self):
        """Every refusal, in full. Same shape as club_keys.census(): a truncated
        account of what was skipped is another way of skipping it."""
        return sorted(((lg, y, s, f"{why} [{src}]", n, None) for (src, lg, y, s, why), n in self.refused.items()),
                      key=lambda r: (-r[4], r[0], r[2]))


def census_of_index(C, index):
    """Every non-code season-key token in an index the table cannot place, with what it
    costs -- the club_keys.census() shape, so build_dashboard prints it unchanged:
    [(league, year, club, reason, person_seasons, example_person)]."""
    cost = collections.Counter(); who = {}
    for pid, p in index.items():
        if pid == "_clubs" or not isinstance(p, dict): continue
        for k in p.get("seasons") or {}:
            lg, y, club = k.split("|", 2); yr = y[1:5] if y.startswith("y") else y
            if not yr.isdigit():
                cost[(lg, y, club, "season key carries no parseable year")] += 1; who.setdefault((lg, y, club), pid); continue
            if C.by_code_year(club, int(yr)): continue
            r = C.resolve(club, int(yr), None if lg in ("COACHES", "SALARIES") else lg, source="season_key")
            if r: continue
            why = next((k_[4] for k_ in C.refused if k_[2] == yr and k_[3] == club), "unplaced")
            cost[(lg, yr, club, why)] += 1; who.setdefault((lg, yr, club), pid)
    return sorted(((lg, yr, cl, why, n, who.get((lg, yr, cl))) for (lg, yr, cl, why), n in cost.items()), key=lambda r: (-r[4], r[0], r[2]))


def report_index(log=print, index=None):
    """Print the index census. Wired into build_dashboard so it is seen without asking."""
    if index is None: index = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    rows = census_of_index(Clubs(), index)
    if not rows:
        log("  UNMAPPABLE CLUB STRINGS: none"); return rows
    log(f"  UNMAPPABLE CLUB STRINGS: {sum(r[4] for r in rows):,} person-season(s) across {len(rows)} club string(s). "
        f"Each is a club-season nothing can join on; the men keep their seasons but the club stays unresolved.")
    for lg, yr, club, why, n, ex in rows: log(f"     {n:6,}  {lg}|{yr}|{club}   [{why}]  e.g. {ex}")
    return rows


def report(C, log=print):
    rows = C.census()
    if not rows:
        log("  CLUB TABLE, unmappable strings: none"); return rows
    log(f"  CLUB TABLE, unmappable strings: {sum(r[4] for r in rows):,} lookup(s) across {len(rows)} string(s)")
    for lg, yr, s, why, n, _ in rows:
        log(f"     {n:6,}  {lg}|{yr}|{s}   [{why}]")
    return rows
