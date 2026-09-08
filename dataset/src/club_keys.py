"""The season-aware club-name to club-code map, and what it refuses.

A season key is LEAGUE|YEAR|CLUB. Most of the archive writes CLUB as a code (BUF);
the Coaching Tree store writes it as a name (Buffalo Bills), and the two forms are
different clubs to anything that compares keys. 2,607 keys carry a name.

THE MAP IS SEASON-AWARE, AND HAS TO BE. There WAS a Buffalo Bisons -- in 1946, in
the AAFC -- and there was a Cleveland Bulldogs in the 1920s. A 1946 Bisons is
right and a 1986 Bisons is wrong, and a map keyed on the name alone cannot tell
them apart. Every lookup here is (name, year).

TWO CASES, KEPT APART.

  A MAPPING GAP. The name IS the club's name in that year -- 'Minnesota Vikings'
    where MIN belongs -- or is its city with the nickname left off. Mechanical:
    2,225 of them plus 4 city-only.

  A SOURCE DEFECT. The name is not what the club was called that season. Coaching
    Tree calls Buffalo the Bisons from 1978, Cleveland the Bulldogs from 1978 and
    Oakland the Hornets in the 1960s. Normalising these silently would hide that
    the source is wrong, so they are recorded as defects and the printed name is
    kept on the season.

A SOURCE DEFECT IS ONLY ACCEPTED ON CORROBORATION: some person must hold BOTH the
printed name and the target code for one league-year, which is the archive itself
saying the two keys are one season. Without it the mapping is refused, and that
refusal earns its keep: a city match alone would have rewritten 'Chicago Cardinals
Football Club' to the Chicago BEARS.
"""
import os, re, json, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


class ClubKeys:
    def __init__(self, index=None, clubs=None):
        if index is None:
            index = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
            clubs = index.pop("_clubs", {})
        self.CL = clubs
        self.by_year = collections.defaultdict(list)
        self.exact = collections.defaultdict(set)
        for k, v in self.CL.items():
            code, y = k.split("|")
            self.by_year[y].append((code, v)); self.exact[(norm(v), y)].add(code)
        self.corroborated = self._corroborate(index)

    def is_code(self, tok, year):
        return f"{tok}|{year}" in self.CL

    def _corroborate(self, index):
        """(printed name, code) pairs some person holds together for one league-year."""
        c = collections.Counter()
        for pid, p in index.items():
            if not isinstance(p, dict): continue
            by = collections.defaultdict(set)
            for k in p.get("seasons") or {}:
                lg, y, club = k.split("|", 2); by[(lg, y)].add(club)
            for (lg, y), cs in by.items():
                yr = y[1:5] if y.startswith("y") else y
                names = [x for x in cs if not self.is_code(x, yr)]
                codes = [x for x in cs if self.is_code(x, yr)]
                for n in names:
                    for code in codes: c[(n, code)] += 1
        return c

    def _city_match(self, printed, yr):
        pt = printed.split(); best = []
        for code, nm in self.by_year.get(yr, []):
            nt = nm.split(); k = 0
            while k < len(pt) and k < len(nt) and norm(pt[k]) == norm(nt[k]): k += 1
            if k: best.append((k, code, nm))
        if not best: return []
        m = max(b[0] for b in best)
        return [(c, n) for k, c, n in best if k == m]

    def resolve(self, club, year):
        """(code, kind, archive_name, evidence) or (None, why, None, None)."""
        yr = str(year)
        if self.is_code(club, yr): return None, "already a code", None, None
        ex = self.exact.get((norm(club), yr))
        if ex and len(ex) == 1:
            code = next(iter(ex))
            return code, "mapping_gap", self.CL[f"{code}|{yr}"], "the club carried this exact name that season"
        if ex: return None, "ambiguous_exact_name", None, None
        cm = self._city_match(club, yr)
        if len(cm) > 1: return None, "ambiguous_city", None, None
        if not cm: return None, "no_club_season_to_match", None, None
        code, nm = cm[0]
        if norm(club) == norm(nm)[:len(norm(club))]:
            return code, "mapping_gap", nm, "the source gave the city and left the nickname off"
        n = self.corroborated.get((club, code), 0)
        if not n:
            return None, "source_defect_uncorroborated", nm, None
        return code, "source_defect", nm, f"{n} person-seasons hold both this name and {code}"

    def census(self, index):
        """Every club string this map REFUSES, with what it costs.

        The refusal was always there; what was missing was anybody hearing it.
        resolve() returns None and every caller writes `if not code: continue`,
        so a club nobody could map left no trace at all -- the club simply had
        no men and no page said why. The 1926 AFL sat unenumerated for exactly
        this long because nothing counted what was being stepped over.

        This is the dropped-predicate reporter applied to club strings, and it
        reports the FULL list for the same reason: a truncated account of what
        was skipped is another way of skipping it.

        -> [(league, year, club, reason, person_seasons, example_person)]
        """
        cost = collections.Counter(); who = {}
        for pid, p in index.items():
            if not isinstance(p, dict): continue
            for k in p.get("seasons") or {}:
                lg, y, club = k.split("|", 2)
                yr = y[1:5] if y.startswith("y") else y
                if not yr.isdigit():
                    cost[(lg, y, club, "season key carries no parseable year")] += 1
                    who.setdefault((lg, y, club), pid); continue
                if self.is_code(club, yr): continue
                code, kind, nm, ev = self.resolve(club, yr)
                if code: continue
                cost[(lg, yr, club, kind)] += 1
                who.setdefault((lg, yr, club), pid)
        return sorted(((lg, yr, c, why, n, who.get((lg, yr, c)))
                       for (lg, yr, c, why), n in cost.items()),
                      key=lambda r: (-r[4], r[0], r[2]))

    def normalise_key(self, key):
        """LEAGUE|YEAR|CLUB -> (new key, kind, printed club, archive name, evidence) or None."""
        lg, y, club = key.split("|", 2)
        yr = y[1:5] if y.startswith("y") else y
        if not yr.isdigit(): return None
        code, kind, nm, ev = self.resolve(club, yr)
        if not code: return None
        return f"{lg}|{y}|{code}", kind, club, nm, ev


def report(index=None, clubs=None, log=print):
    """Print the census. Wired into build_dashboard so it is seen without asking."""
    if index is None:
        index = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
        clubs = index.pop("_clubs", {})
    rows = ClubKeys(index, clubs).census(index)
    if not rows:
        log("  UNMAPPABLE CLUB STRINGS: none")
        return rows
    log(f"  UNMAPPABLE CLUB STRINGS: {sum(r[4] for r in rows):,} person-season(s) "
        f"across {len(rows)} club string(s). Each is a club-season nothing can "
        f"join on; the men keep their seasons but the club stays unresolved.")
    for lg, yr, club, why, n, ex in rows:
        log(f"     {n:6,}  {lg}|{yr}|{club}   [{why}]  e.g. {ex}")
    return rows


if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        report(); raise SystemExit(0)
    CK = ClubKeys()
    print(json.dumps(CK.resolve(*(sys.argv[1:3] if len(sys.argv) > 2 else ("Buffalo Bisons", "1986")))))
