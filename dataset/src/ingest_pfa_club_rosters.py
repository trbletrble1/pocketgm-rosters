"""PFA's club-season ROSTER tables -- the fourth thing PFA held that the archive treated
as missing.

The drafts, the box scores, the 1,469 team-season pages, and now the ROSTERS ON THOSE
SAME PAGES. Every one is a section read for one purpose and not another: the statistics
ingests read these pages for SCORING, RUSHING, PASSING and left the table above them
alone. `declarations/source-coverage.json` recorded team-seasons as 2,930 cached and 9
cited for a week and nothing read that as an alarm.

WHAT A ROSTER TABLE CARRIES: Player, No, Pos, Ht, Wt, Age, College, GP, GS. Four of the
four facts the hunting instrument counts, on club-seasons the archive holds nobody for.

THE JOIN IS THE RULED DISCIPLINE, tier by tier, and each claim records which tier placed
it. It has caught four errors this weekend and these are 1930s and 1940s men with common
names, so the tiers are held exactly:

  1  exact name on the club-season
  2  exact and unique ANYWHERE in the archive -- ADMISSIBLE ONLY for a person-scoped fact
     about a man the page is already about, NEVER for a club-season placement
  3  surname and forename initial, held TO THE CLUB-SEASON
  4  nothing looser. A man who reaches here is a LEAD.

THE COACHES COME TOO. The page prints `Head Coach: <name>` and the archive is thin on
staff for these leagues.

THE NAMES ARE TWO DIFFERENT PROBLEMS AND ARE NOT FILED TOGETHER:
  * `Charlotte Bantams` / `Charlotte Purols` -- ONE CLUB, TWO PRINTED NAMES from one
    source, the shape of Newark Bears and Newark Demons. Both go on one club and NO
    SECOND CLUB IS CREATED.
  * `Lousville` / `Louisville`, `Chiuefs` / `Chiefs`, `Benagls` / `Bengals` -- the archive
    holds PFA's OWN TYPO, read off its standings and transaction pages, and PFA's team
    page spells it correctly. A source's typo and a source's alternative name are
    different things.
Both are held AS PRINTED and each says which it is.

  python3 src/ingest_pfa_club_rosters.py            read and report
  python3 src/ingest_pfa_club_rosters.py --write    write build/pfa-club-rosters.json
"""
import os, re, sys, json, html, sqlite3, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
from readings import person_name as pname
import pfa_codes

SRC = os.path.expanduser("~/Documents/pgm3-sources")
TREES = ("pfa-team-seasons", "pfa2", "pfa", "pfa-awards")
SRC_ID = "pfa-club-rosters"
STATED = "Pro Football Archives"
OUT = os.path.join(BASE, "build", "pfa-club-rosters.json")
TARGETS = os.path.join(BASE, "build-reports", "pfa-club-season-targets.json")
COLS = ("Player", "No", "Pos", "Ht", "Wt", "Age", "College", "GP", "GS")
TYPO_PAIRS = {("lousville bourbons", "louisville bourbons"),
              ("milwaukee chiuefs", "milwaukee chiefs"),
              ("cincinnati benagls", "cincinnati bengals")}

# THE CODE TIER, Ryan's ruling of 2026-09-11. PFA links every roster name to its own
# player page, /players/<x>/<code>.html, and this ingest used to throw the link away: the
# leads never recorded a code the source printed. Where more than one held man carries the
# printed name and EXACTLY ONE of them holds this row's code, the code places him. It is a
# source-native identifier, not a judgement -- the same thing that made the gamelog join
# clean -- and it is not tier 2: tier 2 is a NAME that happens to be unique; this is PFA's
# own id for the man. Measured before it was ruled: of 395 leads whose only other evidence
# was era, era put 105 of 383 checkable ones on the WRONG man.
CODE_TIER = "PFA's own player code, held by exactly one man of that name"

# THE CODE TIER DOES NOT REACH AN EXCLUDED LEAGUE. Ryan, 2026-09-11: 126 of the 391 men
# the code would place sit on club-seasons in leagues declarations/clubs.json excludes, and
# the promotion route never read that exclusion -- 3,536 people were made on those leagues on
# 9 September. That leak is a separate ruling. This pass does not extend it: the rule is
# applied in scope and the rest is COUNTED, not placed. Read from the declaration, never typed.
EXCLUDED = set(json.load(open(os.path.join(BASE, "declarations", "clubs.json")))
               ["MINOR_LEAGUE_EXCLUSION"]["leagues"])


def _lev(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def classify_name(held, printed, pair):
    """-> (kind, basis). THREE KINDS, AND THEY ARE NOT THE SAME THING.

    Ryan named three typos the archive holds -- Lousville, Chiuefs, Benagls -- and they
    are declared. The rest are classified by SHAPE and the basis is recorded on the claim,
    because edit distance finds typos and STRUCTURALLY CANNOT find a second printed name
    (docs/DATASET_PRECEDENTS.md). So a small distance is reported as a typo BY SHAPE, with
    its distance, and a ruling can say otherwise; it is never asserted as a correction.

      declared typo         Ryan's three
      typo by shape         the letters differ by one or two, spacing aside
      set differently       the same letters, spaced or hyphenated differently
      a second name         a different word: Purols against Bantams, Long Beach against
                            Los Angeles. Held beside, never over.
    """
    a, b = pair
    if pair in TYPO_PAIRS:
        return "declared typo: the archive holds PFA's own misspelling", "Ryan's ruling, 2026-09-09"
    sa, sb = a.replace(" ", ""), b.replace(" ", "")
    if sa == sb:
        return "set differently: the same letters, spaced or hyphenated otherwise", "identical without spacing"
    d = _lev(sa, sb)
    if d <= 2 and abs(len(sa) - len(sb)) <= 2:
        return f"typo by shape: {d} letter(s) apart", ("edit distance on the letters. Reported as a "
               "shape, not asserted as a correction -- an alternative name is not a misprint")
    return "a second name one source prints for one club", f"edit distance {d}; a different word"


def flat(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def disk():
    out = {}
    for d in TREES:
        p = os.path.join(SRC, d)
        if os.path.isdir(p):
            for f in os.listdir(p): out.setdefault(f.lower(), os.path.join(p, f))
    return out


def read_page(path):
    """-> (title, club_as_printed, head_coach, columns, rows). Nothing normalised."""
    s = open(path, encoding="utf-8", errors="replace").read()
    t = re.search(r"(?is)<title>(.*?)</title>", s)
    title = html.unescape(t.group(1)).strip() if t else None
    printed = None
    if title:
        m = re.match(r"^\d{4}\s+(.*?)\s+\([A-Z0-9]+\)", title)
        if m: printed = m.group(1).strip()
    body = re.sub(r"(?is)<script.*?</script>", " ", s)
    fl = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "|", body)))
    hc = re.search(r"Head Coach:\s*\|*\s*([^|]{2,60})", fl)
    coach = hc.group(1).strip() if hc else None
    cols, rows, codes = None, [], []
    for tab in re.findall(r"(?is)<table.*?</table>", body):
        trs = re.findall(r"(?is)<tr.*?</tr>", tab)
        pairs = [(tr, [flat(x) for x in re.findall(r"(?is)<t[hd][^>]*>(.*?)</t[hd]>", tr)]) for tr in trs]
        pairs = [(tr, c) for tr, c in pairs if any(c)]
        if pairs and pairs[0][1] and pairs[0][1][0].strip().upper() == "ROSTER":
            cols = pairs[1][1] if len(pairs) > 1 else []
            for tr, r in pairs[2:]:
                if not r or not r[0] or r[0].startswith(("Team", "Opponents")): continue
                # THE ROW'S OWN LINK, kept. `flat` reads the cell's text and drops the
                # href, and the code in it was the one identifier the source gave.
                rows.append(r); codes.append(pfa_codes.code_in_row(tr))
            break
    return title, printed, coach, cols, rows, codes


def names_elsewhere(conn):
    """{normalised name: {person}} for every name the archive holds OUTSIDE this store.
    One implementation: the ingest's candidates and gate_code_identity's are the same set."""
    everywhere = collections.defaultdict(set)
    for pid, nm in conn.execute("select person, name from person_name where store not like 'pfa-club-rosters%'"):
        n = norm(nm)
        if n: everywhere[n].add(pid)
    return everywhere


_PROM = {}


def promoted():
    """(normalised printed name, year, club code) -> the id promote_players minted for a
    lead THIS ingest raised.

    A promoted player's seasons come from the ingest's CLAIMS, so an ingest that raises a
    lead must run AGAIN after the promotion or its own men become people with no season.
    Learned three times on 2026-09-09 -- the Frankford book, the PFRA Annual and Fenton's
    ghosts -- and written in from the start here. The match is the lead's own identity, the
    exact printed name on the exact club-season, never a name join against the archive."""
    if _PROM: return _PROM["m"]
    m = {}
    fp = os.path.join(BASE, "build", "player-promotions.json")
    if os.path.exists(fp):
        for pr in json.load(open(fp)).get("promotions", []):
            if not str(pr.get("source", "")).startswith("pfa-club-rosters"): continue
            nm = norm((pr.get("identified_by") or {}).get("name_as_printed") or pr.get("name") or "")
            for ps in pr.get("playing_seasons") or []:
                m[(nm, int(ps["year"]), ps["club"])] = pr["person_id"]
    _PROM["m"] = m
    return m


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    have = disk()
    tg = json.load(open(TARGETS))["targets"]

    # ---- the archive, as it was BEFORE this source. A decider must not read its own output.
    on_cs = collections.defaultdict(dict)      # (club_id, year) -> {norm name: pid}
    sur_cs = collections.defaultdict(lambda: collections.defaultdict(set))
    for pid, y, cid in conn.execute("select distinct person, year, club_id from claim "
                                    "where scope='stint' and club_id is not null and person is not null"):
        for (nm,) in conn.execute("select distinct name from person_name where person=? "
                                  "and store not like 'pfa-club-rosters%'", (pid,)):
            n = norm(nm)
            if not n: continue
            on_cs[(cid, y)].setdefault(n, pid)
            w = n.split()
            if len(w) > 1: sur_cs[(cid, y)][(w[-1], w[0][:1])].add(pid)
    everywhere = names_elsewhere(conn)
    # WHO HOLDS EACH PFA CODE, from every store but this one.
    code_to = pfa_codes.holders(conn, exclude_stores={SRC_ID})

    claims, leads, names, srs = [], [], [], {}
    n = collections.Counter(); tiers = collections.Counter()
    seen_pages = set()

    def base(sr, tier=None):
        c = {"source_id": SRC_ID, "source_record": sr, "stated_by": STATED,
             "attribution": [STATED], "kind": "observed", "observed_at": "fetched-2026-09"}
        if tier: c["_joined_on"] = tier
        return c

    # SCOPE: Ryan's ruling names 414 pages and 16,422 men -- the club-seasons PFA is the
    # only source for, plus any the archive holds NOBODY on. Reading every club-season page
    # instead would place 106,539 men and write 956,315 claims, and almost all of it would
    # restate rosters the archive already holds from nflverse and StatsCrew. That is the
    # trap the cell-shaped gamelog ingest was ruled against three hours ago. The whole-
    # corpus figure is measured and reported so the rest can be ruled on; it is not written.
    T = json.load(open(os.path.join(BASE, "build", "clubs.json")))
    holds_men = set()
    for pid, y, cid in conn.execute("select distinct person, year, club_id from claim "
                                    "where scope='stint' and club_id is not null and person is not null"):
        holds_men.add((cid, y))
    in_scope = {(t["club_id"], t["year"]) for t in tg
                if t["origin"] == "pfa_only" or (t["club_id"], t["year"]) not in holds_men}
    n["club_seasons_in_scope"] = len(in_scope)

    for t in tg:
        loc = t.get("locator")
        if not loc or loc not in have or loc in seen_pages: continue
        if (t["club_id"], t["year"]) not in in_scope:
            n["out_of_scope_pages_not_read"] += 1
            continue
        title, printed, coach, cols, rows, pcodes = read_page(have[loc])
        if not rows: continue
        seen_pages.add(loc)
        n["pages"] += 1
        sr = f"{SRC_ID}#{loc}"
        srs[sr] = {"source_id": SRC_ID, "locator": loc}
        cid, y, code, lg = t["club_id"], t["year"], t["code"], t["league"]

        # ---- the club's name as this page prints it
        if printed and norm(printed) != norm(t["name"]):
            pair = (norm(t["name"]), norm(printed))
            kind, basis = classify_name(t["name"], printed, pair)
            names.append({"club_id": cid, "year": y, "held_as": t["name"],
                          "printed_here": printed, "kind": kind, "basis": basis,
                          "source_record": sr})
            claims.append({**base(sr), "subject": ["club_season", cid, str(y), code],
                           "predicate": "pfa.club_name_as_printed",
                           "value": {"name_as_printed": printed, "the_archive_holds": t["name"],
                                     "kind": kind, "_basis": basis, "league": lg},
                           "_no_second_club": "one club, two printed names. Nothing is created and "
                                              "nothing is renamed; both stand."})
            n["club_name_" + kind.split(":")[0].replace(" ", "_")] += 1

        if coach:
            claims.append({**base(sr), "subject": ["club_season", cid, str(y), code],
                           "predicate": "pfa.head_coach_as_printed",
                           "value": {"name_as_printed": coach, "club_as_printed": printed,
                                     "year": y, "league": lg}})
            n["head_coach"] += 1

        idx = {c: i for i, c in enumerate(cols or [])}
        for r, pcode in zip(rows, pcodes):
            def cell(c):
                i = idx.get(c)
                return r[i].strip() if i is not None and len(r) > i and r[i].strip() else None
            who = cell("Player")
            if not who: continue
            n["roster_rows"] += 1
            line = {c: cell(c) for c in COLS if cell(c)}
            line.update({"club_as_printed": printed, "year": y, "league": lg, "page": loc})
            # ON THE LINE, so it rides on the lead AND on the placed man's claim, and nobody
            # has to re-derive it from disk again.
            if pcode: line["pfa_code"] = pcode
            nm = norm(who)
            pid = on_cs[(cid, y)].get(nm)
            tier = "exact name on the club-season"
            if not pid:
                w = nm.split()
                hits = sur_cs[(cid, y)].get((w[-1], w[0][:1]), set()) if len(w) > 1 else set()
                if len(hits) == 1:
                    pid = next(iter(hits)); tier = "surname and forename initial, on the club-season"
            if not pid:
                pid = promoted().get((nm, y, code))
                if pid: tier = ("this ingest's own lead, promoted by promote_players.py under the "
                                "printed-roster ruling -- the exact printed name on the exact "
                                "club-season")
            if not pid and pcode:
                named = everywhere.get(nm, set())
                on = [p for p in named if p in code_to.get(pcode, ())]
                if len(named) >= 2 and len(on) == 1:
                    if lg in EXCLUDED:
                        n["code_would_place_on_an_excluded_league__held_back"] += 1
                    else:
                        pid = on[0]; tier = CODE_TIER
                elif len(named) == 1 and len(on) == 1:
                    # THE SAME EVIDENCE WOULD SETTLE A SINGLE NAMESAKE, and that is NOT
                    # ruled -- the ruling is about the ambiguous leads. Counted, not done.
                    n["code_would_settle_a_single_namesake__not_ruled"] += 1
            if not pid:
                # TIER 2 IS INADMISSIBLE FOR A CLUB-SEASON PLACEMENT and is not tried here.
                cand = sorted(everywhere.get(nm, ()))
                # A LEAD ID MUST BE STABLE ACROSS RUNS. A counter is not: the ingest is
                # re-run after promotion, the placed men stop being leads, and every id
                # below them shifts -- so `promotion_ref` on the index record, which is the
                # reversibility anchor, would point at a different man. Keyed on the club-
                # season and the normalised name, which is what the lead IS.
                leads.append({"lead_id": "lead-pfaros-%s-%s-%s" % (
                                  code.replace("PFA:", "").replace("/", "-").lower(), y,
                                  re.sub(r"[^a-z0-9]", "", nm)[:24]),
                              "category": "player_lead_unpromoted", "IS_NOT_A_PERSON": True,
                              "evidence_kind": "printed_roster",
                              "name_as_printed": who, "roster_line": line,
                              "pfa_code": pcode,
                              "places_on": {"club_as_printed": printed, "year": y,
                                            "club_season": f"{lg}|{y}|{code}"},
                              "no_archive_match_evidence": {
                                  "searched": f"every man the archive holds on {lg}|{y}|{code}",
                                  "exact_name_matches_on_the_club_season": 0,
                                  "exact_name_matches_archive_wide": len(cand),
                                  "why": ("tier 2 -- exact and unique anywhere -- is inadmissible "
                                          "for a club-season placement" if len(cand) == 1 else
                                          "no man of that name on this club-season")},
                              "source_id": SRC_ID, "source_record": sr})
                n["lead"] += 1
                continue
            tiers[tier] += 1
            subj = ["stint", pid, code, f"{lg}-{y}"]
            claims.append({**base(sr, tier), "subject": subj,
                           "predicate": "pfa.club_roster_line", "value": line})
            n["placed"] += 1
            # THE FACTS GO UNDER THE NAMES THE ARCHIVE ALREADY USES, so they join the
            # same families and can corroborate or contest what nflverse and StatsCrew
            # already say. Ryan's ruling, 2026-09-09: a fact nothing can compare is half
            # a fact. `pfa.roster.*` on the stint put 7,412 men's position, age, weight
            # and college where nothing read them, and the hunting instrument counted
            # 11,000 gaps that were not gaps.
            #
            # TWO OF THE FOUR FOLD CLEANLY AND TWO DO NOT, and the two that do not are
            # NOT FLATTENED:
            #   position -> `position` on a PERSON_SEASON subject, which is the archive's
            #               own shape for it (171,732 claims) and is already season-scoped.
            #   college  -> `pfa.college_season`, person-scoped WITH THE YEAR IN THE VALUE,
            #               which is PFA's own existing predicate (145,056 claims). The
            #               season survives the fold because the archive already carries it
            #               inside the value.
            #   weight, height -> the archive holds `pfa.weight` and `pfa.height` PERSON-
            #               scoped as CAREER values, and holds()'s own docstring says so.
            #               A roster weight is what the man weighed THAT SEASON. Folding it
            #               into the career value would assert a career figure the source
            #               never printed, so it stays season-scoped and says what it is.
            #   age      -> the archive's age fact is a BIRTH DATE. PFA's roster prints an
            #               AGE IN THAT SEASON, which is a different fact; deriving a birth
            #               year from it would be arithmetic, not evidence. It goes under
            #               `pfa.age_in_season`, beside `pfra.age_in_season`, which is the
            #               archive's own precedent for exactly this.
            pos = line.get("Pos")
            if pos:
                claims.append({**base(sr, tier), "subject": ["person_season", pid, f"{lg}-{y}"],
                               "predicate": "position",
                               "value": {"code": pos, "vocab": "pfa-roster"}})
                n["position"] += 1
            col = line.get("College")
            if col:
                # `college`, NOT `pfa.college_season`. A FAMILY IS WHAT LETS THE MODEL
                # RECORD A DISAGREEMENT, and only eight are declared:
                # service/declarations/predicate-families.json puts `college`, `pfa.college`,
                # `ghosts.college` and the guide fields in one family with a reading that
                # folds `Ohio St.` into `Ohio State`. `pfa.college_season` is in NONE of
                # them, so a college written there sits in a family of its own and can
                # never corroborate or contest anything -- which is what the first version
                # of this did. The value is the plain string so the declared reading can
                # read it; the season the roster printed rides on the claim, not inside
                # the value, so the family stays clean and the year is not lost.
                claims.append({**base(sr, tier), "subject": ["person", pid],
                               "predicate": "college", "value": col,
                               "_printed_for_the_season": f"{lg}-{y}",
                               "_what_it_is": "the college PFA's roster prints beside this man "
                                              "in this season. A college does not change by "
                                              "season, so it is held person-scoped like every "
                                              "other college in the archive."})
                n["college"] += 1
            for pred, key, note in (
                    ("pfa.age_in_season", "Age",
                     "the age PFA prints for this man in this season. NOT a birth date and not "
                     "folded into one: a birth year derived from an age is arithmetic, not evidence."),
                    ("pfa.roster.weight", "Wt",
                     "what the roster gives for THIS SEASON. The archive's `pfa.weight` is a CAREER "
                     "value, person-scoped; this is not folded into it."),
                    ("pfa.roster.height", "Ht",
                     "as above: a season figure, not the career value `pfa.height`."),
                    ("pfa.roster.jersey", "No", None),
                    ("pfa.roster.games_played", "GP", None),
                    ("pfa.roster.games_started", "GS", None)):
                v = line.get(key)
                if v:
                    cl = {**base(sr, tier), "subject": subj, "predicate": pred, "value": v}
                    if note: cl["_scope"] = note
                    claims.append(cl); n[pred] += 1

    out = {"_what": "PFA's club-season ROSTER tables. Player, No, Pos, Ht, Wt, Age, College, GP, GS.",
           "source": {"source_id": SRC_ID, "name": "Pro Football Archives — club-season rosters",
                      "stated_by": STATED, "attribution": [STATED], "acquisition": "fetched"},
           "source_records": srs, "claims": claims, "leads": leads,
           "club_names_as_printed": names, "counts": dict(n), "tiers": dict(tiers)}
    print(f"PFA CLUB ROSTERS   ({'WRITE' if write else 'dry run'})")
    print(f"  pages read                    {n['pages']:>8,}")
    print(f"  roster rows                   {n['roster_rows']:>8,}")
    print(f"  PLACED on a man               {n['placed']:>8,}")
    for k, v in tiers.most_common(): print(f"      {v:>6,}  {k}")
    print(f"  LEADS (nobody promoted)       {n['lead']:>8,}")
    print(f"  head coaches                  {n['head_coach']:>8,}")
    for k, v in sorted(n.items()):
        if k.startswith("club_name_"): print(f"  club name, {k[10:].replace('_',' '):<28} {v:>8,}")
    print(f"  claims                        {len(claims):>8,}")
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
        print(f"  -> {OUT}  ({os.path.getsize(OUT):,} bytes)")
    else:
        print("  (dry run; pass --write)")
    return out


# WRITING IS OPT-IN. Ruled 2026-09-09.
if __name__ == "__main__":
    main(write="--write" in sys.argv)
