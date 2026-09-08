"""Candidate college abbreviations, built from measured disagreements only.

RYAN'S RULE, unchanged: an abbreviation folds ONLY where it has exactly one possible
school. Where two real schools compete for one short form it does not fold, and the
pair stays a disagreement -- which is correct.

BUILT FROM THE CORPUS, NOT FROM A LIST OF AMERICAN COLLEGES. The candidates are the
one-to-one disagreements measured between PFA's 2,926 team-season roster tables and
what the archive holds -- 18,279 rows. A list nobody measured is a list nobody can
defend.

THE AMBIGUITY TEST IS MEASURED, NOT JUDGED. A short form is refused when the corpus
itself shows a second school competing for it: another long form that the same short
form is paired with, or another value that starts with the short form as a whole
word. My opinion about how many Georgetowns there are is not evidence; two values in
the archive is.

  python3 src/measure_college_synonyms.py
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
import measure_pfa_team_seasons as M
from readings import READERS, _STATES

# the fifty states by name, from the declared place reading -- not retyped here
STATE_NAMES = set(_STATES.values()) | {"south carolina", "north carolina", "north dakota",
                                       "south dakota", "west virginia", "new mexico",
                                       "new york", "new jersey", "new hampshire",
                                       "rhode island"}

OUT = os.path.join(BASE, "build-reports", "college-synonyms.json")


def corpus_values(conn):
    """Every distinct college value the archive holds, on the declared reading."""
    vals = collections.Counter()
    for (v,) in conn.execute("select value from claim where family='college'"):
        try: v = json.loads(v)
        except Exception: pass
        if isinstance(v, dict):
            v = v.get("value") or v.get("college") or v.get("school")
        for one in M.colleges(v):
            vals[one] += 1
    return vals


def candidates():
    """One-to-one disagreements between a PFA roster cell and what the archive holds."""
    conn = sqlite3.connect(paths.READ_MODEL)
    held_all = M.held_by_club_season(conn)
    fam, anyclaim = M.facts_held(conn)
    import clubs as ac
    C = ac.Clubs()
    pairs = collections.Counter()
    pb = M.cache_files()
    for f in sorted(pb):
        if not M.TS.match(f) or M.NOT_A_TEAM.search(f):
            continue
        got = M.parse(pb[f])
        if not got:
            continue
        year, club, league, rows, _ = got
        res = C.resolve(club, year, league, source="pfa-team-season")
        if not res:
            continue
        held = held_all.get((res[0], year), {})
        matched = set()
        decided = []
        for r in rows:
            pid, how = M.match(r["player"], held)
            decided.append((r, pid))
            if pid: matched.add(pid)
        for r, pid in decided:
            if not pid:
                continue
            page = M.colleges(r.get("college", ""))
            have = fam["college"].get(pid, set())
            if not page or not have or (page & have):
                continue
            # ONE school on each side, or it is a man with two schools and tells us
            # nothing about how a short form expands
            if len(page) == 1 and len(have) == 1:
                pairs[(next(iter(page)), next(iter(have)))] += 1
    return pairs, corpus_values(conn)


# words that name what a school IS rather than which school it is. Dropping one of
# these cannot pick out a different school; dropping a place name can, and does.
GENERIC = {"state", "college", "university", "institute", "a&m", "tech", "polytechnic"}
STOP = {"of", "the", "and", "at"}


def tokens(s):
    """-> [(word, separator-that-followed)] so `tennessee-chattanooga` and
    `tenn-chattanooga` compare word by word, and a hyphen is not mistaken for part of
    a word. The separators must match too: same shape, one word shorter."""
    parts = re.findall(r"[^\s-]+|[\s-]", s)
    out, cur = [], None
    for p in parts:
        if p in (" ", "-"):
            if out: out[-1] = (out[-1][0], p)
        else:
            out.append((p, ""))
    return out


def initials(long):
    return "".join(w[0] for w in re.split(r"[\s-]+", long) if w and w not in STOP)


def how_it_abbreviates(long, short):
    """-> a NAMED category, or None. Each category is a way a short form can be the
    same school as a long one. Anything outside them is a guess, not a reading."""
    lw = long.split()
    sw = short.split()
    ini = initials(long)
    # University is not part of the corpus's long forms but is part of the initialism:
    # USC, UBC and UNLV carry it in front, LSU, SMU, TCU and BYU behind.
    flat = short.replace(" ", "").replace("-", "")
    if flat in (ini, "u" + ini, ini + "u"):
        return "the initialism of the long form, with or without the University"
    # a trailing GENERIC word dropped: `bowling green state` -> `bowling green`
    if len(lw) > 1 and lw[-1] in GENERIC and lw[:-1] == sw:
        # BUT NOT WHERE WHAT REMAINS IS A STATE'S OWN NAME. `South Carolina State` and
        # `South Carolina` are two real universities, as are South Dakota's, Michigan's
        # and Ohio's. There, `State` is the whole of the distinction and dropping it
        # merges two schools rather than expanding an abbreviation.
        if lw[-1] == "state" and " ".join(sw) in STATE_NAMES:
            return None
        return f"the long form with the generic word {lw[-1]!r} dropped"
    # ONE WORD SHORTENED, every other word identical. Ruled by Ryan, 2026-09-08:
    # a shortened NON-FINAL word is the same shape as a shortened last word --
    # `eastern michigan` and `east michigan` are one school. SHORTENING a word is not
    # DROPPING one, which is why `minnesota state-mankato` to `minnesota state` is
    # still refused: it has one token fewer, not one token shorter.
    lt, ls = tokens(long), tokens(short)
    if lt and len(lt) == len(ls) and [x[1] for x in lt] == [x[1] for x in ls]:
        diff = [i for i in range(len(lt)) if lt[i][0] != ls[i][0]]
        if len(diff) == 1:
            i = diff[0]
            a, b = lt[i][0], ls[i][0]
            if len(b) >= 3 and a.startswith(b):
                where = "the last word" if i == len(lt) - 1 else f"word {i + 1}"
                return f"{where} shortened, {a!r} to {b!r}"
    # a trailing place qualifier moved to the front or dropped is NOT here on purpose:
    # `north carolina-charlotte` -> `charlotte` keeps a place and drops a place, and
    # which school that is depends on knowing there is only one Charlotte.
    return None


def rule(long, short, vals, short2long, long2short):
    """-> (fold, reason). The reason is the evidence, not the conclusion."""
    how = how_it_abbreviates(long, short)
    if not how:
        return False, ("REFUSED: the short form is not the initialism of the long one, "
                       "nor the long one with a generic word dropped or shortened. "
                       "Folding it would be a guess about which school is meant")
    # A RIVAL IS NOT ANY OTHER SCHOOL THE SHORT FORM DISAGREES WITH. `usc` disagrees
    # with `davidson` twice -- that is one man's college disputed between two sources,
    # not evidence that USC is ambiguous. A rival counts only when it could ITSELF
    # abbreviate to this short form, which is what "two schools compete for one short
    # form" actually means.
    rivals = sorted(l for l in short2long.get(short, ())
                    if l != long and how_it_abbreviates(l, short))
    if rivals:
        return False, ("REFUSED: the corpus shows a second school this short form "
                       f"could equally be -- {', '.join(repr(r) for r in rivals[:3])}")
    # A value that is the short form plus more words may be a second real school
    # (`georgetown dc` beside `georgetown`) -- or it may be two colleges fused into one
    # cell (`tcu ohio state`). If the remainder is itself a college the archive holds,
    # it is the second kind and says nothing about ambiguity.
    def rival_prefixes(base):
        out = []
        for v in vals:
            if v in (base, short, long):
                continue
            m = re.match(r"^" + re.escape(base) + r"\s+(.+)$", v)
            if m and m.group(1) not in vals:
                out.append(v)
        return sorted(out)
    for base, side in ((short, "short"), (long, "long")):
        pref = rival_prefixes(base)
        if pref:
            return False, (f"REFUSED: the archive also holds "
                           f"{', '.join(repr(p) for p in pref[:3])} beside {base!r}, so "
                           f"the {side} form does not name exactly one school")
    return True, f"FOLDS: {how}, and no second school in the corpus competes for {short!r}"


def main():
    pairs, vals = candidates()
    short2long = collections.defaultdict(set)
    long2short = collections.defaultdict(set)
    for (lo, sh), n in pairs.items():
        short2long[sh].add(lo); long2short[lo].add(sh)
    folds, refused = [], []
    for (lo, sh), n in pairs.most_common():
        ok, why = rule(lo, sh, vals, short2long, long2short)
        row = {"long": lo, "short": sh, "rows": n, "reason": why,
               "long_held": vals.get(lo, 0), "short_held": vals.get(sh, 0)}
        (folds if ok else refused).append(row)
    print(f"one-to-one college disagreements: {sum(pairs.values()):,} rows, "
          f"{len(pairs):,} distinct pairs\n")
    print(f"FOLDS ({len(folds)} pairs, {sum(f['rows'] for f in folds):,} rows)")
    for f in folds[:40]:
        print(f"   {f['rows']:>6,}  {f['long']!r} == {f['short']!r}")
        print(f"           {f['reason']}")
    print(f"\nREFUSED ({len(refused)} pairs, {sum(r['rows'] for r in refused):,} rows)"
          " -- these stay disagreements, which is correct")
    for r in refused[:25]:
        print(f"   {r['rows']:>6,}  {r['long']!r} vs {r['short']!r}")
        print(f"           {r['reason']}")
    json.dump({"folds": folds, "refused": refused}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
