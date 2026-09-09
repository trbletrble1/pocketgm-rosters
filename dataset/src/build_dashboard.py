"""Coverage dashboard. Queries the store and writes a self-contained HTML page.

    python3 src/build_dashboard.py        (from dataset/)

Everything is computed at run time. No figure is hardcoded, so re-running gives
current numbers. Three rules the page must never break:

  UNMEASURED IS NOT ZERO. A field with no claims renders 0%; a field nothing
  counted renders "not measured" in a visibly different cell. A dashboard that
  drew "unknown" as 0% would be the empty-versus-failed error at its worst.

  NO RATE WITHOUT ITS COUNT. Every percentage carries the numerator and the
  denominator behind it.

  THE POPULATION ROW MUST SUM TO THE ARCHIVE. If a decade column drops people,
  the dashboard would hide exactly the thing it exists to show.
"""
import os, re, csv, sys, json, glob, html, hashlib, shutil, subprocess, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
SRC = "/Users/ryannecci/Documents/pgm3-sources"
UNMEASURED = None                     # distinct from 0 by TYPE, not by value


def log(*a): print(*a, file=sys.stderr)


# ------------------------------------------------------------------ population
YEARPART = re.compile(r"^y?(\d{4})$")


def population():
    """The archive total is the index total. Anything this function drops must be
    COUNTED and reported, not silently absent -- requiring a bare digit for the
    year dropped 493 coaches whose season keys read COACHES|y1957|Chicago Bears,
    and the population check did not catch it because it compared the grid to
    this function's own output rather than to the archive."""
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    clubs = idx.pop("_clubs", {})
    per = {}
    global DROPPED, INDEX_TOTAL
    INDEX_TOTAL = len(idx)
    DROPPED = collections.Counter()
    for g, p in idx.items():
        # RULED: a person is someone who PLAYED at least one season OR COACHED at
        # least one stint. The index was built player-shaped, so a man who only
        # ever coached had no season key and fell out of the population entirely --
        # which would have grown the coaching numerator while leaving its
        # denominator behind.
        seasons = p.get("seasons") or {}
        coaching = p.get("coaching_seasons") or {}
        # RULED: officials are people too. The line is ON-FIELD GAME PARTICIPANTS
        # -- not trainers, equipment managers, owners or broadcasters, and this is
        # not precedent for them. Without this an official falls out of the
        # denominator exactly as a coaching-only man did.
        officiating = p.get("officiating_seasons") or {}
        if not seasons and not coaching and not officiating:
            DROPPED["neither played, coached nor officiated"] += 1
            continue
        yrs, lgs = [], set()
        # the decade bucket is the first stint OF ANY KIND, playing or coaching
        for src in (seasons, coaching, officiating):
            for k in src:
                parts = k.split("|")
                m = YEARPART.match(parts[1]) if len(parts) >= 2 else None
                if m:
                    yrs.append(int(m.group(1))); lgs.add(parts[0])
        if not yrs:
            DROPPED["season key carries no parseable year"] += 1
            continue
        per[g] = {"first": min(yrs), "leagues": lgs,
                  "person": p.get("person") or {}, "seasons": seasons,
                  "coaching_seasons": coaching, "officiating_seasons": officiating,
                  "roles": p.get("roles") or (["player"] if seasons else []),
                  # a man with no playing season has no playing career to be
                  # missing. Playing fields are NOT APPLICABLE to him, which is a
                  # different cell from one that is merely unrecorded.
                  "playing_fields_apply": bool(seasons),
                  "name": p.get("name")}
    return per


def decade(y): return (y // 10) * 10


LEAGUE_ORDER = ["APFA", "NFL", "AAFC", "AFL", "CFL", "WFL", "USFL", "USFL2",
                "XFL", "WLAF", "UFL", "UFL2", "AAF"]


# ------------------------------------------------------------------ the fields
def field_sets(per):
    """(label, set_of_person_ids or UNMEASURED, {source: claim_count})."""
    out = []
    src_counts = collections.defaultdict(collections.Counter)

    # --- from the person index (StatsCrew and whatever else fed it) ---
    for label, key in (("birth date", "birth_date"), ("birth place", "birthplace"),
                       ("hometown", "hometown"), ("college", "college"),
                       ("death date", "death_date"), ("high school", "high_school")):
        s = {g for g, v in per.items()
             if [x for x in (v["person"].get(key) or [])
                 if x and str(x).strip().lower() not in ("none", "")]}
        if s: src_counts[label]["StatsCrew (person index)"] += len(s)
        out.append((label, s))

    # --- claim stores ---
    def find_claims(d, depth=0):
        """Claim lists, wherever they sit. A store is not always a flat
        {"claims": [...]}: guide-pre1950-delimited.json nests them
        runs -> guides -> claims, and a scanner that only checks the top level
        skips the whole file. That is worse than an unmapped predicate, because
        an unmapped predicate at least reaches the unmapped report -- a file
        never opened as a store reaches nothing and looks exactly like a file
        with no claims in it."""
        if depth > 4 or not isinstance(d, dict):
            return []
        out = []
        if isinstance(d.get("claims"), list):
            out.extend(d["claims"])
        for v in d.values():
            if isinstance(v, dict):
                out.extend(find_claims(v, depth + 1))
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, dict):
                        out.extend(find_claims(x, depth + 1))
        return out

    stores, skipped = {}, []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        b = os.path.basename(f)
        if b.startswith("stats-") or b.startswith("PGMRoster"):
            continue
        try:
            d = json.load(open(f))
        except Exception as e:
            skipped.append((b, f"unreadable: {type(e).__name__}")); continue
        cl = find_claims(d)
        if cl:
            stores[b] = {"claims": cl}
        else:
            skipped.append((b, "no claims found at any depth"))
    log(f"  claim stores read: {len(stores)}  "
        f"(claims: {sum(len(v['claims']) for v in stores.values()):,})")
    if skipped:
        # Say what was NOT counted. Silence about a skipped file is the same
        # failure as silence about a dropped predicate.
        fam = collections.Counter()
        for b, why in skipped:
            fam[re.sub(r"[-_]?\d{4}.*$", "-*", b)] += 1
        log(f"  build files contributing NO claims: {len(skipped)} "
            f"({len(fam)} name families)")
        for k, c in fam.most_common(20):
            log(f"     {c:4d}  {k}")

    byfield = collections.defaultdict(set)
    unmapped = collections.Counter()
    no_position = collections.Counter()
    non_person = collections.Counter()
    PRED = {
        "has_photograph": "photograph", "wikipedia.photograph": "photograph",
        "wikipedia.prose": "narrative prose",
        "wikipedia.death_date": "death date", "wikipedia.death_place": "death place",
        "wikipedia.birth_place": "birth place", "wikipedia.birth_date": "birth date",
        "wikipedia.high_school": "high school",
        "wikipedia.draft_round": "draft round and pick",
        "wikipedia.draft_pick": "draft round and pick",
        "wikipedia.club_career": "club-by-club career",
        "wikipedia.post_playing_career": "coaching / post-playing",
        "wikipedia.reference": "cited reference list",
        "role_title": "coaching / post-playing", "is_head_coach": "coaching / post-playing",
        "pfa.high_school": "high school", "pfa.birth_place": "birth place",
        "pfa.birth_date": "birth date", "pfa.death_date": "death date",
        "pfa.death_place": "death place", "pfa.draft": "draft round and pick",
        "pfa.military_service": "military service", "pfa.height": "height",
        "pfa.weight": "weight", "pfa.position_career": "position",
        "pfa.college_season": "college", "pfa.college": "college",
        "pfa.kin": "kinship", "pfa.transaction": "transaction log",
        # The row already exists and role_title/is_head_coach already feed it, so
        # this follows the established mapping rather than making a new ruling.
        "pfa.coaching_season": "coaching / post-playing",
        "pfa.coaching_playoffs": "coaching / post-playing",
        "nflverse.birth_date": "birth date",
        "nflverse.roster_membership": "club-by-club career",
        # RULED: two rows. A complete draft record carries round AND overall pick;
        # everything below does. They were held out of the grid until the ruling
        # existed, which is why nflverse and PFR appeared nowhere despite holding
        # ~22,000 records between them.
        "pfa.draft_selection": "draft round and pick",
        "nflverse.draft_selection": "draft round and pick",
        "pfr.draft_selection": "draft round and pick",
        "draft.selection": "draft round and pick",
        # SECOND ROW, and it must stay a second row. draft_picks_pre2001.csv has
        # no round column at all. Rendering these beside complete records would
        # let a partial fact borrow the appearance of a whole one -- the predicate
        # name already refuses that, and so does the label.
        "draft.overall_pick_only": "draft pick only, no round",
        # STILL UNMAPPED, deliberately:
        #   wikipedia.draft_year  -- a year with no round or pick adds ONE person
        #                            out of 40,649; an honest home for it needs a
        #                            third row that would carry a single man.
        #   face_colour           -- from the measured.csv that was measuring the
        #                            detector's bias rather than the men. Noted
        #                            for removal; that is its own ruling.
        #   guide.*               -- a guide's printed labels are not folded into
        #                            modern field names, and their OCR damage is a
        #                            legibility record of the source.
    }
    # Attribution comes from the claim's OWN source_id, not from the filename.
    # nflverse-draft.json and nflverse-rosters.json are different bodies from
    # different files and must not be merged into one "nflverse" row; a filename
    # guess would have done exactly that.
    SOURCE_NAME = {
        "statscrew": "StatsCrew", "pro-football-archives": "Pro Football Archives",
        "wikipedia-en": "Wikipedia", "psf-photos": "PSF photo set",
        "coaching-tree": "coaching tree", "media-guides": "media guides",
        "nflverse": "nflverse (draft records)",
        "nflverse-rosters": "nflverse (historical rosters)",
        "draft-picks-pre2001": "draft_picks_pre2001.csv",
        "draft-picks-2001-2004": "draft_picks_2001_2004.csv",
        "pfr-draft-listing": "Pro-Football-Reference draft listings",
        "pre1936-assistants": "pre-1936 assistants",
    }

    def who_of(c, b):
        sid = c.get("source_id")
        if sid in SOURCE_NAME:
            return SOURCE_NAME[sid]
        if sid and sid.startswith("media-guide-"):
            return "media guides (per-guide)"
        if sid and (sid.startswith("news/") or sid.startswith("court/")
                    or sid.startswith("sys/")):
            return "salary sources"
        return sid or b

    for b, d in stores.items():
        for c in d["claims"]:
            who = who_of(c, b)
            p = c.get("predicate")
            subj = c.get("subject")
            pid = subj[1] if isinstance(subj, (list, tuple)) and len(subj) > 1 else None
            if not isinstance(pid, str) or not pid.startswith("P_"):
                # NOT A PERSON. Every grid on this page is per-person, so these
                # cannot appear in one -- but they were being dropped BEFORE the
                # unmapped counter, which made them invisible to the very report
                # that exists to stop things going missing. A league-season roster
                # limit and a club's training camp are real claims about real
                # subjects; they are counted and named here even though no row
                # can hold them yet.
                kind = subj[0] if isinstance(subj, (list, tuple)) and subj else "malformed"
                # Two different reasons, and they must not be summed as one number:
                #   OTHER ID SPACE -- subject IS a person, but carries a lowercase
                #     p_000001 id. Those men are already counted through the
                #     archive index, so this is redundancy, not loss.
                #   OTHER SUBJECT KIND -- a league-season, a club, a stint. Not a
                #     person at all, and no per-person grid can ever hold one.
                why = ("other_id_space" if kind == "person" else "other_subject_kind")
                non_person[(why, kind, p)] += 1
                continue
            lab = PRED.get(p)
            if p and ("salary" in p or "compensation" in p or "wage" in p):
                lab = "salary"
            # A draft selection with NO ROUND goes to the pick-only row, whatever
            # predicate carried it. 30 of these exist: AAFC Special Selections and
            # NFL Bonus Picks, where no round EXISTS rather than the source having
            # omitted one. That reason differs from draft_picks_pre2001.csv, and it
            # is flagged -- but the ruling's principle is about the shape, and a
            # pick with no round must not render as a complete record either way.
            if lab == "draft round and pick" and isinstance(c.get("value"), dict) \
                    and c["value"].get("round") is None:
                if c["value"].get("overall_pick") is not None:
                    lab = "draft pick only, no round"
                else:
                    # NEITHER round NOR pick: the 16 AAFC "Special Selection"
                    # territorial picks. Row 1 would assert a round he has not
                    # got and row 2 would assert a pick. It belongs in neither,
                    # so it is excluded from both -- and COUNTED, because a
                    # silent exclusion is the failure this report exists to stop.
                    no_position[(b, c["value"].get("selection_type") or "no type")] += 1
                    continue
            if not lab:
                # A predicate this map does not know is DROPPED, and a dropped
                # claim is invisible: the grid looks identical whether a store
                # holds nothing or holds 73,508 claims under names never added
                # here. Count them and say so, so that silence is never the
                # same as absence.
                unmapped[(b, p)] += 1
                continue
            byfield[lab].add(pid)
            src_counts[lab][who] += 1
    if non_person:
        ids = sum(c for (w, k, pr), c in non_person.items() if w == "other_id_space")
        kinds = sum(c for (w, k, pr), c in non_person.items() if w == "other_subject_kind")
        log(f"  CLAIMS NOT ON THE PERSON GRID: {sum(non_person.values()):,}")
        log(f"     {ids:,} carry a lowercase p_ id -- the SAME person, counted via the "
            f"archive index. Redundant here, not lost.")
        log(f"     {kinds:,} are not a person at all:")
        agg = collections.Counter()
        for (w, k, pr), c in non_person.items():
            if w == "other_subject_kind":
                agg[(k, pr)] += c
        for (k, pr), c in agg.most_common(10):
            log(f"        {c:8,}  {pr:34s} subject kind: {k}")
    if no_position:
        log(f"  DRAFT EVENTS WITH NEITHER ROUND NOR PICK, excluded from both draft "
            f"rows: {sum(no_position.values())}")
        for (b, t), c in no_position.most_common():
            log(f"     {c:8,}  {t}   [{b}]")
    if unmapped:
        log(f"  UNMAPPED PREDICATES DROPPED: {sum(unmapped.values()):,} claims "
            f"across {len(unmapped)} predicate(s)")
        # THE FULL LIST, never a top-N. A truncated report of what was dropped
        # is itself a way to drop things quietly.
        for (b, pr), c in unmapped.most_common():
            log(f"     {c:8,}  {pr}   [{b}]")
    # The same treatment for CLUB STRINGS. A predicate nothing maps at least
    # reached the report above; a club nothing maps reached nothing at all --
    # club_keys.resolve() returned None, every caller wrote `if not code:
    # continue`, and the club simply had no men and no line saying why. The
    # 1926 AFL was invisible for exactly that reason.
    import clubs
    clubs.report_index(log=log)   # the club table's census over the index; loads its own copy
    for lab, s in byfield.items():
        out.append((lab, s))

    # --- club-by-club career: everyone with a season has one from the rosters ---
    # A club-by-club PLAYING career belongs to men who played. Handing it
    # "everyone" put 1,598 coaching-only men in the numerator while the
    # not-applicable rule correctly kept them out of the denominator, and the row
    # rendered 103.9%.
    everyone = {g for g, v in per.items() if v.get("playing_fields_apply", True)}
    out.append(("club-by-club career", everyone | byfield.get("club-by-club career", set())))
    src_counts["club-by-club career"]["StatsCrew (rosters)"] += len(everyone)

    # --- merge duplicate labels ---
    merged = collections.defaultdict(set)
    for lab, s in out:
        if s is UNMEASURED:
            merged.setdefault(lab, UNMEASURED)
        else:
            merged[lab] |= s
    # A field we intend to show but genuinely cannot compute stays UNMEASURED,
    # WITH ITS REASON. Salary is the live case: salaries.json addresses people as
    # 'p_000001' in its own local id space on stint/contract/cohort subjects, not
    # as ('person', 'P_...') in the index id space, so it cannot be placed on the
    # person axis without a mapping that does not exist yet. That is a fact about
    # the store worth showing, not a cell to leave blank.
    for lab in ("salary",):
        merged.setdefault(lab, UNMEASURED)
    return merged, src_counts


# ------------------------------------------------------------------ the grids
# Fields that describe a PLAYING career. A man who only ever coached has no such
# career, so for him these are NOT APPLICABLE -- a third cell state, distinct from
# a field that is merely unrecorded. Reporting him as "missing a club-by-club
# playing career" would be reporting a gap that does not exist.
PLAYING_ONLY = {"club-by-club career", "position", "transaction log"}


def grid(per, sets, axis):
    if axis == "decade":
        keyf = lambda v: decade(v["first"])
        cols = sorted({keyf(v) for v in per.values()})
        collab = [f"{c}s" for c in cols]
    else:
        cols = [l for l in LEAGUE_ORDER if any(l in v["leagues"] for v in per.values())]
        cols += sorted({l for v in per.values() for l in v["leagues"]} - set(cols))
        collab = cols
    pop = collections.Counter()
    members = collections.defaultdict(set)
    noplay = collections.defaultdict(set)
    for g, v in per.items():
        ks = [keyf(v)] if axis == "decade" else list(v["leagues"])
        for k in ks:
            pop[k] += 1; members[k].add(g)
            if not v.get("playing_fields_apply", True):
                noplay[k].add(g)
    rows = []
    for lab in sorted(sets):
        s = sets[lab]
        cells = []
        for c in cols:
            if s is UNMEASURED:
                cells.append({"n": None, "d": pop[c]})
            elif lab in PLAYING_ONLY:
                # the denominator EXCLUDES men the field cannot apply to, and the
                # count of those men rides on the cell so the page can say so
                na = len(noplay[c])
                cells.append({"n": len(s & members[c]), "d": pop[c] - na, "na": na})
            else:
                cells.append({"n": len(s & members[c]), "d": pop[c]})
        rows.append({"field": lab, "cells": cells,
                     "not_applicable": lab in PLAYING_ONLY,
                     "total_n": None if s is UNMEASURED else len(s)})
    return {"cols": collab, "pop": [pop[c] for c in cols], "rows": rows,
            "pop_total": sum(pop[c] for c in cols) if axis == "decade" else None}


def media_guides():
    p = os.path.join(SRC, "nfl-books", "index.csv")
    if not os.path.exists(p):
        return UNMEASURED
    dec = collections.Counter()
    notext = collections.Counter()
    held = set(); blank = set()
    tdir = os.path.join(SRC, "nfl-books", "text_all")
    if os.path.isdir(tdir):
        for f in os.listdir(tdir):
            if f.endswith(".txt"):
                held.add(f[:-4])
            elif f.endswith(".notext"):
                # A SCAN WITH NO TEXT LAYER IS NOT A GUIDE YOU CAN READ, and it
                # is not a missing guide either -- the pages are held, the words
                # are not. Folding these into the readable count overstates what
                # is parseable; dropping them entirely loses 302 documents that
                # exist and could be OCR'd. They get their own row.
                blank.add(re.sub(r"\.txt\.notext$|\.notext$", "", f))
    for r in csv.DictReader(open(p)):
        y = r.get("year", "")
        if not y.isdigit():
            continue
        ident = r["identifier"]; stem = re.sub(r"-[a-z]$", "", ident)
        if not held or ident in held or stem in held:
            dec[decade(int(y))] += 1
        elif ident in blank or stem in blank:
            notext[decade(int(y))] += 1
    cols = sorted(set(dec) | set(notext))
    return {"cols": [f"{d}s" for d in cols],
            "counts": [dec[d] for d in cols], "total": sum(dec.values()),
            "notext": [notext[d] for d in cols], "notext_total": sum(notext.values())}


# ------------------------------------------------------------------ the page
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>Archive coverage</title><style>
:root{--bg:#fbfaf8;--ink:#1c1a17;--mut:#6b665f;--line:#ddd8d0;--un:#efe9e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:32px 24px 80px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:17px;margin:40px 0 10px;letter-spacing:-.01em}
.sub{color:var(--mut);margin:0 0 6px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:#fff;
 border-right:1px solid var(--line);font-weight:500;z-index:1}
thead th{background:#f4f1ec;font-weight:600;font-size:12px;letter-spacing:.03em;
 text-transform:uppercase;color:var(--mut);position:sticky;top:0;z-index:2}
thead th:first-child{z-index:3;background:#f4f1ec}
tr.pop td,tr.pop th{background:#f4f1ec;font-weight:600;border-bottom:2px solid #cfc8bd}
td.c{position:relative}
td.c .pct{position:relative;z-index:1;font-weight:600}
td.c .cnt{position:relative;z-index:1;display:block;font-size:10.5px;color:var(--mut);
 font-weight:400;margin-top:1px}
td.un{background:repeating-linear-gradient(45deg,var(--un),var(--un) 5px,#fff 5px,#fff 10px);
 color:var(--mut);font-style:italic;font-size:11px}
.legend{display:flex;gap:16px;align-items:center;margin:12px 0 0;
 color:var(--mut);font-size:12px;flex-wrap:wrap}
.sw{display:inline-block;width:26px;height:13px;border:1px solid var(--line);
 vertical-align:-2px;margin-right:5px}
.guides td{background:#eef3f6}
.guides tr.notext td,.guides tr.notext th{background:var(--un);color:var(--mut);font-style:italic}
.note{background:#fff;border:1px solid var(--line);border-left:3px solid #8a8175;
 border-radius:6px;padding:12px 14px;margin:16px 0;color:#39352f;font-size:13px}
code{background:#f1ede7;padding:1px 5px;border-radius:3px;font-size:12px}
.ok{color:#2c6b3f;font-weight:600}.bad{color:#a1341f;font-weight:600}
</style></head><body><div class="wrap">
<h1>Archive coverage</h1>
<p class="sub">Generated __WHEN__ &middot; every figure computed from the store at run time</p>
<div class="note"><strong>Ingests reflected:</strong> __INGESTS__<br>
<strong>Unmeasured is not zero.</strong> A hatched cell was never counted. A cell
reading 0% was counted and found empty. They are different facts and the page
draws them differently.</div>
<div id="checks"></div>
<h2>By decade of first season</h2>
<div class="scroll"><table id="t-decade"></table></div>
<div class="legend"><span><span class="sw" style="background:#f7f5f2"></span>0%</span>
<span><span class="sw" style="background:#cfe0d2"></span>50%</span>
<span><span class="sw" style="background:#7aa888"></span>100%</span>
<span><span class="sw" style="background:repeating-linear-gradient(45deg,#efe9e0,#efe9e0 5px,#fff 5px,#fff 10px)"></span>not measured</span>
<span>every cell shows <em>held / population</em> beneath the rate</span></div>
<h2>By league</h2>
<p class="sub">A person appears in every league they played in, so these columns overlap and do not sum to the archive. <strong>COACHES</strong> and <strong>SALARIES</strong> are not leagues &mdash; they are season-key prefixes the store actually uses, shown as they are rather than dropped.</p>
<div class="scroll"><table id="t-league"></table></div>
<h2>Media guide texts held, by decade of publication</h2>
<p class="sub">A COUNT OF DOCUMENTS, not a per-person rate &mdash; a guide covers a club-season, not a man. The second row is scans whose pages are held but whose text layer is empty: not readable, and not missing either. Shown in blue so the unit is never confused with the grids above.</p>
<div class="scroll"><table id="t-guides"></table></div>
<h2>Where each field comes from</h2>
<p class="sub">Claims contributed per source. This answers: if a source went away, what would go with it.</p>
<div class="scroll"><table id="t-src"></table></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const shade=p=>{const t=Math.max(0,Math.min(1,p));
  const r=247+(122-247)*t, g=245+(168-245)*t, b=242+(136-242)*t;
  return `rgb(${r|0},${g|0},${b|0})`;};
function cell(c){
  if(c.n===null) return `<td class="un" title="never counted">not measured</td>`;
  const p=c.d?c.n/c.d:0;
  return `<td class="c" style="background:${shade(p)}">`+
    `<span class="pct">${c.d?(100*p).toFixed(1)+'%':'&mdash;'}</span>`+
    `<span class="cnt">${c.n.toLocaleString()} / ${c.d.toLocaleString()}</span></td>`;
}
function grid(el,G){
  let h='<thead><tr><th>field</th>'+G.cols.map(c=>`<th>${c}</th>`).join('')+'<th>all</th></tr></thead><tbody>';
  h+='<tr class="pop"><th>people in the archive</th>'+
     G.pop.map(n=>`<td>${n.toLocaleString()}</td>`).join('')+
     `<td>${G.pop_total?G.pop_total.toLocaleString():'&mdash;'}</td></tr>`;
  for(const r of G.rows){
    h+=`<tr><th>${r.field}</th>`+r.cells.map(cell).join('')+
       (r.total_n===null?'<td class="un">not measured</td>':`<td>${r.total_n.toLocaleString()}</td>`)+'</tr>';
  }
  document.getElementById(el).innerHTML=h+'</tbody>';
}
grid('t-decade',D.decade); grid('t-league',D.league);
const g=D.guides; let gh='<thead><tr><th>&nbsp;</th>'+g.cols.map(c=>`<th>${c}</th>`).join('')+'<th>all</th></tr></thead>';
gh+='<tbody class="guides"><tr><th>guide texts held (readable)</th>'+g.counts.map(n=>`<td>${n.toLocaleString()}</td>`).join('')+
    `<td>${g.total.toLocaleString()}</td></tr>`+
    '<tr class="notext"><th>scans held with NO text layer</th>'+g.notext.map(n=>`<td>${n?n.toLocaleString():'&mdash;'}</td>`).join('')+
    `<td>${g.notext_total.toLocaleString()}</td></tr></tbody>`;
document.getElementById('t-guides').innerHTML=gh;
let sh='<thead><tr><th>field</th><th>source</th><th>claims</th></tr></thead><tbody>';
for(const [f,ss] of D.sources) for(const [s,n] of ss)
  sh+=`<tr><th>${f}</th><td style="text-align:left">${s}</td><td>${n.toLocaleString()}</td></tr>`;
document.getElementById('t-src').innerHTML=sh+'</tbody>';
const C=D.checks;
document.getElementById('checks').innerHTML='<div class="note">'+
  C.map(c=>`<span class="${c.ok?'ok':'bad'}">${c.ok?'PASS':'FAIL'}</span> ${c.text}`).join('<br>')+'</div>';
</script></div></body></html>"""


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provider_running(pattern):
    """Is a sync client actually running for this target?

    A directory existing proves nothing: ~/Library/CloudStorage/GoogleDrive-... sat
    there for months after its client was uninstalled, and a copy into it verified
    perfectly while syncing nowhere. So look for the process too.

    This proves a CLIENT PROCESS EXISTS. It does not prove the client is signed in,
    that sync is unpaused, that the folder is included in selective sync, or that
    the upload succeeded. Those limits are stated in the target config and are not
    claimed here.
    """
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True,
                             text=True, timeout=20).stdout
    except Exception as e:
        return None, f"could not inspect the process list ({e})"
    me = {os.getpid(), os.getppid()}
    hits = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid, _, cmd = line.partition(" ")
        if not pid.isdigit() or int(pid) in me:
            continue
        # MATCH ONLY THE EXECUTABLE PATH, never the arguments. Searching the whole
        # command line makes the question answer itself: a shell or python process
        # whose ARGUMENTS mention "Dropbox.app" matched, so asking whether a client
        # was running returned True purely because the asking mentioned it. That is
        # the same false positive as `grep -i "Google Drive"` matching its own grep.
        argv0 = cmd.strip().split(" ")[0]
        if pattern in argv0:
            hits.append(cmd.strip())
    return bool(hits), (hits[0][:80] if hits else "no process whose executable path "
                        "contains %r" % pattern)


def publish(src):
    """Copy the dashboard to every configured target.

    A copy that cannot be made is REPORTED AND FATAL, never skipped. A stale
    dashboard that looks current is the failure mode this project keeps meeting,
    and a silent skip is how you get one.

    What this can prove: the file was written into the synced folder and reads
    back with a matching md5. What it CANNOT prove: that the Drive client
    uploaded it. That is outside the filesystem. The page carries its own
    generation timestamp, so a stale copy shows an old time on its face.
    """
    cfg = os.environ.get("PGM3_DASHBOARD_TARGETS",
                         os.path.join(BASE, "export", "dashboard-targets.json"))
    if not os.path.exists(cfg):
        log(f"  no target config at {cfg}; repo copy only")
        return [], True
    targets = json.load(open(cfg, encoding="utf-8")).get("targets", [])
    want = md5(src)
    results, ok = [], True
    for t in targets:
        d, name, req = t["dir"], t.get("name", t["dir"]), t.get("required", True)
        dest = os.path.join(d, os.path.basename(src))
        if not os.path.isdir(d):
            msg = f"FAILED - the folder does not exist: {d}"
            results.append((name, msg, False)); ok = ok and not req; continue
        pat = t.get("provider_process")
        if pat:
            live, detail = provider_running(pat)
            if live is None:
                results.append((name, f"FAILED - {detail}", False)); ok = ok and not req; continue
            if not live:
                results.append((name, f"FAILED - the folder exists but NO SYNC CLIENT IS "
                                      f"RUNNING for it ({detail}). A leftover folder from an "
                                      f"uninstalled client looks exactly like a live one.",
                                False))
                ok = ok and not req; continue
        existed = os.path.exists(dest)
        prev = md5(dest) if existed else None
        try:
            shutil.copy2(src, dest)
        except Exception as e:
            results.append((name, f"FAILED - {e}", False)); ok = ok and not req; continue
        got = md5(dest)
        if got != want:
            results.append((name, f"FAILED - md5 mismatch after writing "
                                  f"({got[:12]} != {want[:12]})", False))
            ok = ok and not req; continue
        live_note = f" [{t['provider_name']} running]" if t.get("provider_process") else ""
        note = ("overwrote an identical copy" if existed and prev == want else
                f"OVERWROTE a DIFFERENT existing file (was {prev[:12]})" if existed else
                "new file")
        results.append((name, f"copied, md5 verified {want[:12]}{live_note} - {note}", True))
    return results, ok


def main():
    log("reading the store...")
    per = population()
    log(f"  people with at least one season: {len(per):,}")
    sets, src = field_sets(per)
    dec = grid(per, sets, "decade")
    lge = grid(per, sets, "league")
    guides = media_guides()

    checks = []
    acc = dec["pop_total"] + sum(DROPPED.values())
    checks.append({"ok": acc == INDEX_TOTAL,
                   "text": f"population row + everything dropped = the archive index: "
                           f"{dec['pop_total']:,} placed + {sum(DROPPED.values()):,} dropped "
                           f"= {acc:,} of {INDEX_TOTAL:,}"
                           + ("" if not DROPPED else " &mdash; dropped: "
                              + "; ".join(f"{v:,} {k}" for k, v in DROPPED.most_common()))})
    zero = [r["field"] for r in dec["rows"] if r["total_n"] == 0]
    unm = [r["field"] for r in dec["rows"] if r["total_n"] is None]
    checks.append({"ok": True,
                   "text": "<strong>salary</strong> is unmeasured on the person axis because "
                           "salaries.json uses its own id space (p_000001) on stint and "
                           "contract subjects; joining it needs a mapping that does not exist"})
    checks.append({"ok": True,
                   "text": f"unmeasured ({len(unm)}) and zero ({len(zero)}) are distinct cell types"
                           + (f" &mdash; not measured: {', '.join(unm)}" if unm else "")})
    bad = [r["field"] for r in dec["rows"] for c in r["cells"]
           if c["n"] is not None and c["d"] == 0 and c["n"] > 0]
    checks.append({"ok": not bad, "text": "no rate is rendered without its denominator"})
    # A rate above 100% means the numerator counts men the denominator excludes.
    # club-by-club career rendered 103.9% the moment coaching-only men entered the
    # population, because the row was handed "everyone" while the not-applicable
    # rule correctly kept them out of its denominator.
    over = [f"{r['field']} ({c['n']:,}/{c['d']:,})" for r in dec["rows"] for c in r["cells"]
            if c["n"] is not None and c["d"] and c["n"] > c["d"]]
    checks.append({"ok": not over,
                   "text": "no row exceeds 100% &mdash; a numerator never counts men its "
                           "denominator excludes"
                           + (" &mdash; OVER: " + "; ".join(over[:4]) if over else "")})
    napp = [r["field"] for r in dec["rows"] if r.get("not_applicable")]
    nacount = sum(c.get("na", 0) for r in dec["rows"] if r.get("not_applicable")
                  for c in r["cells"][:1])
    checks.append({"ok": True,
                   "text": f"a person is someone who PLAYED a season OR COACHED a stint; "
                           f"decade is the first stint of either kind. Playing-only fields "
                           f"({', '.join(napp)}) are NOT APPLICABLE to men who only coached "
                           f"and their denominators exclude them"})

    ing = ("Wikipedia (commit 3dbf35c) &mdash; so death date, death place, high school "
           "and draft already reflect it and there is no pre-ingest baseline; "
           "StatsCrew rosters and statistics; PSF photo set; salary extracts.")
    data = {"decade": dec, "league": lge, "guides": guides,
            "sources": sorted(([f, sorted(c.items(), key=lambda x: -x[1])]
                               for f, c in src.items()), key=lambda x: x[0]),
            "checks": checks}
    out = os.path.join(BASE, "export", "coverage-dashboard.html")
    page = (PAGE.replace("__DATA__", json.dumps(data))
                .replace("__WHEN__", datetime.datetime.now().strftime("%d %B %Y, %H:%M"))
                .replace("__INGESTS__", ing))
    open(out, "w", encoding="utf-8").write(page)
    log(f"\nwrote {out}  ({os.path.getsize(out)/1024:.0f} KB)")
    for c in checks:
        log(("  PASS " if c["ok"] else "  FAIL ") + re.sub("&mdash;", "-", c["text"]))
    log("\npublishing:")
    pub, pub_ok = publish(out)
    for name, msg, good in pub:
        log(("  OK   " if good else "  FAIL ") + f"{name}: {msg}")
    if not pub:
        log("  (no targets configured)")
    if not pub_ok:
        log("\nA REQUIRED COPY FAILED. The repo dashboard is current; the target is "
            "STALE and will look current unless you read its timestamp. Exiting non-zero.")
        sys.exit(2)
    return dec, sets, per


if __name__ == "__main__":
    dec, sets, per = main()
    print("\n=== fields the mockup left hatched ===")
    for f in ("death date", "death place", "hometown", "high school",
              "draft round and pick", "draft pick only, no round",
              "narrative prose", "salary", "photograph"):
        s = sets.get(f, UNMEASURED)
        if s is UNMEASURED:
            print(f"  {f:22s} NOT MEASURED")
        else:
            print(f"  {f:22s} {len(s):7,d} of {len(per):,}  ({100*len(s)/len(per):5.2f}%)")
