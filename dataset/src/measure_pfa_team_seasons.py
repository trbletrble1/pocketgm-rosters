"""What PFA's team-season pages hold against what the archive took from them.

MEASUREMENT ONLY. Nothing ingested, nothing written to a store, nothing fetched.
All 2,926 pages were already in the cache, fetched by the PFA sweep and never read:
2,930 on disk, nine cited by a claim.

Each page carries three tables -- SCORES, ROSTER and a DRAFT LIST. THIS READS THE
ROSTER ONLY. The other two are counted and left alone; they are a separate question
and a separate pass.

THE DENOMINATOR IS ENUMERATED, NOT INFERRED. PFA's own 106 season index pages name
the club-seasons it publishes, and that count is taken before a page is opened.

COMPARED ON THE DECLARED READINGS. college (with the synonym list), height and
weight go through src/readings.py. Comparing printed strings would count `Ohio St.`
against `Ohio State` as a disagreement; three earlier measurements did a version of
that and each was corrected the same way.

THE CLUB NAME IS RESOLVED, NEVER GUESSED. Each page states its club and league in
its own H1. That string goes through the archive's club table. A string the table
cannot place, or places ambiguously, is REFUSED AND REPORTED -- never attached to
the nearest club.

  python3 src/measure_pfa_team_seasons.py
"""
import os, re, sys, json, html, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths, reading_view as RV
from readings import READERS
import clubs as ac

CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
# pages fetched later, because PFA's own season indexes named them and the original
# sweep never took them. Read alongside the original cache, never merged into it: the
# two were acquired on different days by different scripts and the manifest for the
# second lives beside it.
LATER = os.path.expanduser("~/Documents/pgm3-sources/pfa-team-seasons")


def cache_files():
    """-> {filename: full path} across both directories. The original cache wins a
    name collision; nothing was refetched, so there should be none, and if there is
    one it is reported rather than resolved silently."""
    out, clash = {}, []
    for d in (LATER, CACHE):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f in out and out[f] != os.path.join(d, f):
                clash.append(f)
            out[f] = os.path.join(d, f)
    if clash:
        print(f"   NOTE: {len(clash)} filename(s) in both caches: {clash[:4]}")
    return out
OUT = os.path.join(BASE, "build-reports", "pfa-team-seasons.json")
TS = re.compile(r"^(\d{4})([a-z]+)\.html$")
# <year><token>.html also catches 1936awards.html and 1936nfldraft.html, which are
# not team-season pages. Excluded by name, so the enumeration counts club pages only.
NOT_A_TEAM = re.compile(r"(awards|draft|boxscores|leaders|standings|playoffs|allstar"
                        r"|probowl|schedule|transactions)")
H1 = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")
HEAD = re.compile(r"^(\d{4})\s+(.+?)\s+\(([A-Za-z0-9\- ]+)\)$")
# the ROSTER table's header, identical on all 2,926 pages
ROSTER_COLS = ["player", "no", "pos", "ht", "wt", "age", "college", "gp", "gs"]
# the page columns that belong to a declared family, and the reader for each
FAMILY_OF = {"college": "college", "ht": "height", "wt": "weight"}


def colleges(cell):
    """A ROSTER college cell -> the SET of schools it names, each on the declared
    reading. PFA prints a man's second school after a semicolon -- `Notre Dame;
    Michigan State` -- and a disambiguator in brackets -- `St. Thomas (Minnesota)`.
    Reading the whole cell as one school turns both into a disagreement with the
    archive that nobody disagrees about. Comparison is by OVERLAP: a man who
    attended two schools agrees with a source that names one of them."""
    out = set()
    for part in re.split(r"[;/]", str(cell or "")):
        part = re.sub(r"\([^)]*\)", " ", part)
        r = READERS["college"](part) if part.strip() else None
        if r:
            out.add(r)
    return out


def text(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).replace("\xa0", " ").strip()


def enumerate_pages():
    """Three counts, taken before anything is parsed."""
    paths_by_name = cache_files()
    have = set(paths_by_name)
    seasons = sorted(f for f in have if re.match(r"^\d{4}\.html$", f))
    from_index, from_graph = set(), set()
    for f in have:
        if not f.endswith(".html"):
            continue
        t = open(paths_by_name[f], errors="replace").read()
        links = set()
        for h in re.findall(r'href=["\']?([^"\'> ]+)', t):
            b = os.path.basename(h.split("#")[0])
            if TS.match(b) and not NOT_A_TEAM.search(b) and not re.match(r"^\d{4}\.html$", b):
                links.add(b)
        from_graph |= links
        if f in seasons:
            from_index |= links
    on_disk = sorted(f for f in have if TS.match(f) and not NOT_A_TEAM.search(f)
                     and not re.match(r"^\d{4}\.html$", f))
    return {"season_index_pages": len(seasons),
            "named_by_a_season_index": len(from_index),
            "named_by_any_cached_page": len(from_graph),
            "on_disk": len(on_disk),
            "named_by_an_index_and_not_on_disk": len(from_index - have)}, on_disk


def parse(path):
    """-> (year, club_as_printed, league, roster rows, sections present) or None."""
    t = open(path, errors="replace").read()
    m = H1.search(t)
    if not m:
        return None
    h = HEAD.match(text(m.group(1)))
    if not h:
        return None
    year, club, league = int(h.group(1)), h.group(2).strip(), h.group(3).strip().upper()
    banners, rows = [], []
    for tb in re.findall(r"(?is)<table.*?</table>", t):
        trs = re.findall(r"(?is)<tr.*?</tr>", tb)
        cells = [[text(z) for z in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)] for tr in trs]
        for c in cells:
            if len(c) == 1 and c[0].isupper() and 2 < len(c[0]) < 30:
                banners.append(c[0])
        hdr = next((i for i, c in enumerate(cells[:3])
                    if [x.lower() for x in c] == ROSTER_COLS), None)
        if hdr is None:
            continue
        for c in cells[hdr + 1:]:
            if len(c) == len(ROSTER_COLS) and c[0]:
                rows.append(dict(zip(ROSTER_COLS, c)))
    return year, club, league, rows, banners


def norm_name(s):
    s = re.sub(r"[^a-z ]", " ", str(s or "").lower())
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(s.split())


def held_by_club_season(conn):
    """(club_id, year) -> {person -> set of normalised names}.

    Keyed on club and year, NOT on league: the page states its league as PFA prints
    it and the archive stores its own token, and a mismatch there would read as an
    empty club-season -- an absent input reading as nothing, which is the defect
    this project has hit four times. Coaching and salary scopes are excluded; they
    are not roster membership."""
    out = collections.defaultdict(dict)
    names = collections.defaultdict(set)
    for p, n in conn.execute("select person, name from person_name"):
        names[p].add(norm_name(n))
    for cid, y, p in conn.execute(
            "select club_id, year, person from claim "
            "where scope='stint' and person is not null and club_id is not null "
            "and league not in ('COACHES','ASSISTANTS','SALARIES','COACH') "
            "group by club_id, year, person"):
        out[(cid, y)][p] = names.get(p, set())
    return out


def facts_held(conn):
    """person -> {family -> set of READ values}, and separately whether the archive
    holds ANY claim in that family at all.

    The two are different states and conflating them was the first thing this
    measurement got wrong. A man whose archive record says `none` for college has a
    claim; the reader returns nothing for it, so he looks identical to a man nobody
    has ever looked up. The archive holds 1,526 college claims of kind `absent` and
    another 2,432 whose value is the literal string `none` -- it can say `he did not
    attend one`, and that is not the same as silence."""
    fam, anyclaim = {}, {}
    for f in ("college", "height", "weight"):
        fam[f] = collections.defaultdict(set)
        anyclaim[f] = set()
    q = ("select c.person, c.family, c.value from claim c "
         "where c.family in ('college','height','weight') and c.person is not null")
    for p, f, v in conn.execute(q):
        try: v = json.loads(v)
        except Exception: pass
        if isinstance(v, dict):
            v = v.get("value") or v.get("college") or v.get("school")
        anyclaim[f].add(p)
        if v is None:
            continue
        if f == "college":
            fam[f][p] |= colleges(v)
        else:
            r = READERS[f](v)
            if r: fam[f][p].add(r)
    return fam, anyclaim


def match(printed, held):
    """A printed roster name against the men the archive holds on this club-season.

    -> (person, how) or (None, why). THE SURNAME IS NEVER ENOUGH. `G. Wilson` and
    `Abe Wilson` share a surname and are not the same man; that trap has been walked
    into repeatedly here, so a surname-only candidate is reported as its own outcome
    and is NOT counted as held."""
    n = norm_name(printed)
    if not n:
        return None, "unreadable name"
    exact = [p for p, names in held.items() if n in names]
    if len(exact) == 1:
        return exact[0], "full name"
    if len(exact) > 1:
        return None, "ambiguous: the archive holds that exact name twice on this club-season"
    parts = n.split()
    if len(parts) >= 2:
        sur, ini = parts[-1], parts[0][0]
        # `J. Lawson` against `Jim Lawson`: surname equal AND forename initial equal
        cand = [p for p, names in held.items()
                for x in names if x.split() and x.split()[-1] == sur
                and x.split()[0][:1] == ini and len(x.split()) >= 2]
        cand = sorted(set(cand))
        if len(cand) == 1:
            return cand[0], "surname and forename initial"
        if len(cand) > 1:
            return None, "ambiguous: several men share surname and initial"
        sur_only = {p for p, names in held.items()
                    for x in names if x.split() and x.split()[-1] == sur}
        if sur_only:
            return None, "surname matches but the forename does not -- not counted as held"
    return None, "not held on this club-season"


def main():
    counts, on_disk = enumerate_pages()
    print("ENUMERATED BEFORE PARSING")
    for k, v in counts.items():
        print(f"   {k.replace('_',' '):42s} {v:>7,}")

    conn = sqlite3.connect(paths.READ_MODEL)
    C = ac.Clubs()
    held_all = held_by_club_season(conn)
    fam, anyclaim = facts_held(conn)

    n = collections.Counter()
    refusals = collections.Counter()
    gain_by_family = collections.Counter()
    disagree_by_family = collections.Counter()
    college_pairs = collections.Counter()
    # rows and MEN are different numbers: a man in ten club-seasons appears ten times
    gain_people = collections.defaultdict(set)
    absence_people = set()
    unread_cell = collections.Counter()
    matched_people, notheld_names = set(), collections.Counter()
    pages, banners = [], collections.Counter()
    unmatched_reason = collections.Counter()

    paths_by_name = cache_files()
    for f in on_disk:
        got = parse(paths_by_name[f])
        if not got:
            n["page: no H1 of the team-season shape"] += 1
            continue
        year, club, league, rows, bans = got
        n["pages parsed"] += 1
        for b in bans:
            banners[b] += 1
        if not rows:
            n["pages with no ROSTER row"] += 1
        res = C.resolve(club, year, league, source="pfa-team-season")
        if not res:
            n["pages whose club the table refuses"] += 1
            refusals[(league, year, club)] += 1
            continue
        cid, via = res
        n["pages whose club resolved"] += 1
        n[f"  resolved via {via}"] += 1
        held = held_all.get((cid, year), {})
        if not held:
            n["pages on a club-season the archive holds nobody for"] += 1
        page = {"page": f, "year": year, "club": club, "league": league,
                "club_id": cid, "via": via, "men": len(rows),
                "held_on_that_club_season": len(held),
                "not_held": 0, "unresolved_name": 0,
                "adds_a_fact": 0, "second_source_only": 0}
        # first pass: who on this page matches whom, so a page's UNMATCHED HELD MEN
        # are known before any row is called missing
        matched_pids = set()
        decided = []
        for r in rows:
            pid, how = match(r["player"], held)
            decided.append((r, pid, how))
            if pid: matched_pids.add(pid)
        held_unmatched = len(set(held) - matched_pids)
        for r, pid, how in decided:
            n["roster rows"] += 1
            if not pid:
                unmatched_reason[how] += 1
                if how.startswith("ambiguous"):
                    n["rows refused as ambiguous"] += 1
                elif held_unmatched:
                    # the club-season still has men the page has not matched, so this
                    # row may be one of them under another name -- Johnny Blood is
                    # held as Johnny McNally, Charles Goldenberg as Buckets
                    # Goldenberg. Calling it missing would be a guess in the
                    # direction that flatters the finding.
                    n["ROWS THAT CANNOT BE SETTLED (a held man on this club-season "
                      "is unmatched too)"] += 1
                    page["unresolved_name"] += 1
                else:
                    n["MEN NOT HELD"] += 1
                    page["not_held"] += 1
                    notheld_names[(year, club, r["player"], r.get("pos", ""),
                                   r.get("college", ""))] += 1
                continue
            n[f"rows matched by {how}"] += 1
            matched_people.add(pid)
            adds = False
            for col, family in FAMILY_OF.items():
                cell = (r.get(col) or "").strip()
                if family == "college":
                    vs = colleges(cell)
                    # PFA prints the literal `none` for a man who attended no
                    # college. That is an ASSERTION, not a blank -- the hunting list
                    # counts these men as missing a fact when the source has
                    # answered the question.
                    if not vs and cell.lower() == "none":
                        if pid not in anyclaim[family]:
                            n["ABSENCES THE ARCHIVE DOES NOT HOLD"] += 1
                            absence_people.add(pid)
                        else:
                            n["absences the archive already holds a claim for"] += 1
                        continue
                else:
                    v = READERS[family](cell) if cell else None
                    vs = {v} if v else set()
                if not vs:
                    if cell:
                        unread_cell[(family, cell)] += 1
                    continue
                have = fam[family].get(pid, set())
                if not have:
                    if pid in anyclaim[family]:
                        n["page gives a value where the archive holds only an "
                          "unreadable one or an absence"] += 1
                    else:
                        gain_by_family[family] += 1
                        gain_people[family].add(pid)
                        adds = True
                elif not (vs & have):
                    disagree_by_family[family] += 1
                    if family == "college":
                        college_pairs[(" | ".join(sorted(vs)), " | ".join(sorted(have)))] += 1
            if adds:
                n["MEN HELD, PAGE CARRIES A FACT THE ARCHIVE LACKS"] += 1
                page["adds_a_fact"] += 1
            else:
                n["MEN HELD, PAGE ADDS ONLY A SECOND SOURCE"] += 1
                page["second_source_only"] += 1
        pages.append(page)

    print("\nPARSED")
    for k in ("pages parsed", "pages with no ROSTER row", "pages whose club resolved",
              "pages whose club the table refuses",
              "pages on a club-season the archive holds nobody for", "roster rows"):
        if k in n: print(f"   {k:52s} {n[k]:>7,}")
    for k in sorted(k for k in n if k.startswith("  resolved via")):
        print(f"   {k:52s} {n[k]:>7,}")

    print("\nTHE THREE NUMBERS, KEPT APART")
    for k in ("MEN NOT HELD",
              "MEN HELD, PAGE CARRIES A FACT THE ARCHIVE LACKS",
              "MEN HELD, PAGE ADDS ONLY A SECOND SOURCE"):
        print(f"   {k:52s} {n[k]:>7,}")
    print("\nAND WHAT COULD NOT BE ESTABLISHED")
    k = ("ROWS THAT CANNOT BE SETTLED (a held man on this club-season is unmatched too)")
    print(f"   {'rows that cannot be settled by name':52s} {n[k]:>7,}")
    print(f"   {'rows refused as ambiguous':52s} {n['rows refused as ambiguous']:>7,}")

    print("\nTHE MIDDLE NUMBER, BY FAMILY")
    print(f"   {'':20s} {'rows':>9s} {'DISTINCT MEN':>13s}")
    for f, c in gain_by_family.most_common():
        print(f"   {f:20s} {c:>9,} {len(gain_people[f]):>13,}")
    allp = set().union(*gain_people.values()) if gain_people else set()
    print(f"   {'any of the three':20s} {n['MEN HELD, PAGE CARRIES A FACT THE ARCHIVE LACKS']:>9,} {len(allp):>13,}")
    print(f"   {'(matched men in all)':20s} {'':>9s} {len(matched_people):>13,}")
    print("\nA FOURTH KIND OF GAIN, KEPT APART -- PFA PRINTS `none` FOR NO COLLEGE")
    print(f"   {'absences the archive does not hold':52s} "
          f"{n['ABSENCES THE ARCHIVE DOES NOT HOLD']:>7,} rows, {len(absence_people):,} men")
    print(f"   {'absences the archive already has a claim for':52s} "
          f"{n['absences the archive already holds a claim for']:>7,} rows")
    k2 = ("page gives a value where the archive holds only an unreadable one or an absence")
    print(f"   {'page gives a value against an archive absence':52s} {n[k2]:>7,} rows")
    print("\nWHERE THE PAGE AND THE ARCHIVE DISAGREE, ON THE DECLARED READING")
    for f, c in disagree_by_family.most_common():
        print(f"   {f:20s} {c:>7,}")
    print("\nTHE COMMONEST COLLEGE DISAGREEMENTS -- candidate synonyms, MEASURED NOT FOLDED")
    for (a, b), c in college_pairs.most_common(12):
        print(f"   {c:>6,}  page {a!r}  vs held {b!r}")

    print("\nWHY A ROW DID NOT MATCH")
    for w, c in unmatched_reason.most_common():
        print(f"   {c:>7,}  {w}")

    print("\nCLUB STRINGS THE TABLE REFUSED (reported, never guessed)")
    if not refusals:
        print("   none")
    for (lg, y, cl), c in refusals.most_common(15):
        print(f"   {y} {lg:6s} {cl}")
    if len(refusals) > 15:
        print(f"   ... {len(refusals)-15} more")

    # ---- where the archive is thin, is there a page to read at all?
    named = set()
    have = set(paths_by_name)
    for f in have:
        if not re.match(r"^\d{4}\.html$", f):
            continue
        t = open(paths_by_name[f], errors="replace").read()
        for h in re.findall(r'href=["\']?([^"\'> ]+)', t):
            b = os.path.basename(h.split("#")[0])
            if TS.match(b) and not NOT_A_TEAM.search(b) and not re.match(r"^\d{4}\.html$", b):
                named.add(b)
    covered = {(p["club_id"], p["year"]) for p in pages}
    thin = collections.Counter(); thin_cs = collections.Counter()
    for (cid, y), people in held_all.items():
        miss = sum(1 for fy in ("college", "height", "weight")
                   for pp in people if pp not in anyclaim[fy])
        if not miss:
            continue
        k = "a page is on disk and was just read" if (cid, y) in covered \
            else "NO page on disk for that club-season"
        thin[k] += miss; thin_cs[k] += 1
    print("\nWHERE THE ARCHIVE IS THIN, IS THERE A PAGE TO READ?")
    for k in sorted(thin, reverse=True):
        print(f"   {k:44s} {thin_cs[k]:>6,} club-seasons, {thin[k]:>7,} missing facts")
    absent_named = sorted(b for b in named if b not in have)
    print(f"\n   team-season pages PFA's own indexes name that were never fetched: "
          f"{len(absent_named):,}")
    pre = collections.Counter(re.sub(r"^\d{4}", "", b).replace(".html", "")[:12]
                              for b in absent_named)
    whole = collections.Counter()
    for b in absent_named:
        whole[re.sub(r"^\d{4}", "", b).replace(".html", "")] += 1
    print("   the club codes most completely missing:")
    for k, c in whole.most_common(8):
        print(f"      {k:16s} {c:>4,} seasons named, none fetched"
              if not any(f"{y}{k}.html" in have for y in range(1920, 2026))
              else f"      {k:16s} {c:>4,} seasons named and absent")

    print("\nTHE OTHER TABLES ON THESE PAGES -- counted, NOT read")
    for b, c in banners.most_common(8):
        print(f"   {b:28s} on {c:>6,} pages")

    json.dump({"enumeration": counts, "totals": dict(n),
               "gain_by_family": dict(gain_by_family),
               "disagree_by_family": dict(disagree_by_family),
               "unmatched": dict(unmatched_reason),
               "college_disagreement_pairs": [{"page": a, "held": b, "n": c}
                                              for (a, b), c in college_pairs.most_common(200)],
               "refused_club_strings": [{"year": y, "league": lg, "club": cl, "n": c}
                                        for (lg, y, cl), c in refusals.most_common()],
               "banners": dict(banners),
               "gain_distinct_people": {k: len(v) for k, v in gain_people.items()},
               "matched_people": len(matched_people),
               "absence_people": len(absence_people),
               "unread_cells": [{"family": f, "cell": c, "n": k}
                                for (f, c), k in unread_cell.most_common(40)],
               "men_not_held": [{"year": y, "club": c, "name": nm, "pos": po, "college": co}
                                for (y, c, nm, po, co) in notheld_names],
               "pages": pages}, open(OUT, "w"), indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
