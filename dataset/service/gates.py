"""The gates. Each is a function of the built read model and returns
{name, status, counts, report}; a FAIL refuses publication.

Four were ruled on 2026-09-07 and a fifth on the same day: four was never a magic
number, it was how many properties needed checking at the time.

  G1  an unreadable date fails      -- a date-family string the reader cannot read and
                                       declarations/dates-as-printed.json does not carry
  G2  an unresolved person fails    -- a person-scoped claim whose id resolves to nobody, in a
                                       store the archive's own person-index-rebuild.json does
                                       not declare as known-unresolvable
  G3  a missing source record fails -- a claim naming a record its store's source_records table
                                       does not hold, or naming none
  G4  an unreconciled population fails -- the people here != the people in the index
  G5  an unexplained build file fails  -- a file in build/ that is not a store in the model and
                                       that declarations/build-files.json does not explain
  G6  a FALSE disagreement fails       -- a contested fact whose values all read to the same
                                       thing under dataset/declarations/readings.json
  G7  a FABRICATED league fails        -- a league token on a stint that the club table does not
                                       hold and the rebuild declaration does not name on purpose
  G8  a GUESSED classification fails   -- a statistics store, a staff predicate or a name
                                       predicate that declarations/classification.json does not
                                       name, re-derived from the claims in both directions

NOT a gate: whether any value is correct. The archive holds disagreements on purpose.

    python3 gates.py     # run G1-G3 against the published read model, G4 against the index now
"""
import os, sys, json, glob, sqlite3
import collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths

DATES_DECL = os.path.join(paths.SERVICE_DECLARATIONS, "dates-as-printed.json")
BUILD_FILES_DECL = os.path.join(paths.SERVICE_DECLARATIONS, "build-files.json")


def g1(conn, ctx):
    decl = json.load(open(DATES_DECL)) if os.path.exists(DATES_DECL) else {"accepted_as_printed": []}
    accepted = {e["string"] for e in decl.get("accepted_as_printed", [])}
    rows = conn.execute("""SELECT d.literal, d.family, c.predicate, COUNT(*), MIN(c.store||'/'||c.cid), MIN(c.source_record)
                           FROM date_reading d JOIN claim c ON c.id=d.claim WHERE d.readable=0
                           GROUP BY d.literal, d.family, c.predicate ORDER BY COUNT(*) DESC""").fetchall()
    unread = [{"string": r[0], "family": r[1], "predicate": r[2], "n": r[3], "example_claim": r[4], "source_record": r[5]} for r in rows]
    undeclared = [u for u in unread if u["string"] not in accepted]
    declared_seen = [u for u in unread if u["string"] in accepted]
    declared_unseen = sorted(accepted - {u["string"] for u in unread})
    total = conn.execute("SELECT COUNT(*) FROM date_reading").fetchone()[0]
    # Ruled 2026-09-07: if a source corrects a declared string, the entry must stop being declared rather
    # than the corrected string being silently reread -- so a declared string no longer seen FAILS too.
    return {"name": "RS-G1 unreadable dates", "status": "FAIL" if (undeclared or declared_unseen) else "PASS",
            "counts": {"date_strings_read": total, "unreadable_undeclared": sum(u["n"] for u in undeclared),
                       "unreadable_declared_as_printed": sum(u["n"] for u in declared_seen), "declared_but_no_longer_seen": len(declared_unseen)},
            "report": {"undeclared": undeclared, "declared_seen": declared_seen, "declared_unseen": declared_unseen}}


def g2(conn, ctx):
    decl = json.load(open(paths.INDEX_REBUILD_DECL)) if os.path.exists(paths.INDEX_REBUILD_DECL) else {}
    known = {k: v for k, v in (decl.get("known_unresolvable_stores") or {}).items() if not k.startswith("_")}
    held = {k: v for k, v in (decl.get("held_stores") or {}).items() if not k.startswith("_")}
    rows = conn.execute("""SELECT store, scope, COUNT(*), MIN(subject) FROM claim
                           WHERE person IS NULL AND scope IN ('person','person_season','stint','contract','transfer')
                           GROUP BY store, scope ORDER BY COUNT(*) DESC""").fetchall()
    unres = [{"store": r[0], "scope": r[1], "n": r[2], "example_subject": json.loads(r[3])} for r in rows]
    undeclared = [u for u in unres if u["store"] not in known and u["store"] not in held]
    declared = [dict(u, why=known.get(u["store"]) or held.get(u["store"])) for u in unres if u["store"] in known or u["store"] in held]
    return {"name": "RS-G2 unresolved persons", "status": "FAIL" if undeclared else "PASS",
            "counts": {"unresolved_undeclared_claims": sum(u["n"] for u in undeclared), "undeclared_stores": len({u["store"] for u in undeclared}),
                       "unresolved_declared_claims": sum(u["n"] for u in declared), "declared_stores": len({u["store"] for u in declared})},
            "report": {"undeclared": undeclared, "declared": declared, "declaration": os.path.relpath(paths.INDEX_REBUILD_DECL, paths.DATASET)}}


def g3(conn, ctx):
    missing = [{"store": r[0], "n": r[1], "example_claim": r[2], "example_record": r[3]} for r in conn.execute(
        """SELECT store, COUNT(*), MIN(store||'/'||cid), MIN(source_record) FROM claim WHERE sr_in_table=0 GROUP BY store""")]
    none = [{"store": r[0], "n": r[1], "example_claim": r[2]} for r in conn.execute(
        """SELECT store, COUNT(*), MIN(store||'/'||cid) FROM claim WHERE source_record IS NULL OR source_record='' GROUP BY store""")]
    no_table = [{"store": r[0], "claims": r[1]} for r in conn.execute("SELECT name, claims FROM store WHERE has_table=0 ORDER BY name")]
    prefix = [{"store": r[0], "source_id": r[1], "n": r[2], "example_record": r[3]} for r in conn.execute(
        """SELECT store, source_id, COUNT(*), MIN(source_record) FROM claim
           WHERE source_record IS NOT NULL AND substr(source_record, 1, length(source_id)+1) != source_id||'#' GROUP BY store, source_id""")]
    undeclared = [{"store": r[0], "source_id": r[1], "n": r[2]} for r in conn.execute(
        """SELECT c.store, c.source_id, COUNT(*) FROM claim c LEFT JOIN source s ON s.source_id=c.source_id WHERE s.source_id IS NULL GROUP BY c.store, c.source_id""")]
    fail = bool(missing or none)
    return {"name": "RS-G3 source records", "status": "FAIL" if fail else "PASS",
            "counts": {"claims_naming_a_record_not_in_their_store": sum(m["n"] for m in missing), "claims_naming_no_record": sum(n["n"] for n in none),
                       "stores_without_a_record_table": len(no_table), "claims_in_stores_without_a_table": sum(s["claims"] for s in no_table),
                       "records_prefixed_by_another_source_id": sum(p["n"] for p in prefix), "claims_from_undeclared_sources": sum(u["n"] for u in undeclared)},
            "report": {"missing": missing, "no_record": none, "stores_without_a_table": no_table,
                       "prefix_differs_from_source_id_INFORMATION": prefix, "undeclared_source_ids_INFORMATION": undeclared}}


def g4(conn, ctx):
    idx = set(ctx["index_keys"]); ours = set(ctx["people"])
    a = sorted(idx - ours); b = sorted(ours - idx)
    return {"name": "RS-G4 population reconciles with the index", "status": "FAIL" if (a or b) else "PASS",
            "counts": {"ours": len(ours), "index": len(idx), "in_index_not_here": len(a), "here_not_in_index": len(b)},
            "report": {"in_index_not_here": a[:500], "here_not_in_index": b[:500]}}


def g5(conn, ctx):
    """Every file in build/ is either a store in the model or explained. Not assumed.

    THE DEFECT THIS EXISTS FOR. build_read_model.py reads a file only if it is a JSON
    object with a top-level `claims` list. Everything else it skipped IN SILENCE -- a
    file that failed to parse logged one line and the build published anyway, and a
    file with an unrecognised shape logged nothing at all. A store that broke, was
    truncated, or was written in a shape the reader does not know would have vanished
    with the build still reporting success, and no gate would have counted the
    absence. Seventh instance of that shape in this project; the first six were found
    by accident.

    FOUR OUTCOMES, and only two of them are failures:

      accounted   the file is a store in the model.
      pending     it has claims and is NEWER than the build, or was not an input of
                  it. It is a new store awaiting a rebuild, not a dropped one -- SHOWN
                  on every run, never a failure. (`wikipedia-photos-replacements`,
                  written by Fetching at 16:28 against a 13:19 model, is why this
                  case exists.)
      explained   declarations/build-files.json says, by shape or by name, that it is
                  not a claim store -- and someone wrote down why.
      UNEXPLAINED it parses as a claim store the build read and did not carry, or it
                  does not parse at all, or nothing explains it. FAIL.

    AND THE DECLARATION MUST STAY TRUE. A file declared not-a-claim-store that has
    since grown a `claims` list is a store the reader is now dropping under cover of
    an old ruling: that fails too. This is the half that makes the gate notice rather
    than remember -- it shows the reader something it could not read and requires it
    to be looked at, instead of trusting a list written once.

    An unparseable file is NEVER declarable. Unreadable is fatal and named.
    """
    from build_read_model import is_claim_store          # the reader's OWN test, never a second copy
    p4 = _p4_the_reader_still_refuses(is_claim_store)      # and prove it still means what it meant
    decl = json.load(open(BUILD_FILES_DECL)) if os.path.exists(BUILD_FILES_DECL) else {}
    nacs = decl.get("not_a_claim_store") or {}
    by_name = nacs.get("by_name") or {}
    array_ok = any(r.get("when") == "top_level_is_an_array" for r in (nacs.get("by_shape") or []))

    in_model = {r[0] for r in conn.execute("SELECT name FROM store")}
    # What the build actually read, per file. Compared per path rather than against a
    # single "built at" timestamp: the question is not "is this file recent" but "is
    # this the same bytes the reader saw and dropped".
    read_at_build = {os.path.basename(r[0])[:-5]: (r[1], r[2]) for r in
                     conn.execute("SELECT path, mtime_ns, size FROM input WHERE path LIKE 'build/%.json'")}

    unexplained, pending, explained, stale, gone = [], [], [], [], []
    files = sorted(glob.glob(os.path.join(paths.BUILD, "*.json")))
    for f in files:
        st = os.path.basename(f)[:-5]
        if st in in_model: continue
        try:
            d = json.load(open(f))
        except (OSError, ValueError) as e:
            unexplained.append({"store": st, "why": f"WILL NOT PARSE: {type(e).__name__}: {e}",
                                "mb": round(os.path.getsize(f) / 1e6, 2),
                                "remedy": "an unreadable build file is never declarable; repair or remove it"})
            continue
        has_claims = is_claim_store(d)
        declared = st in by_name or (array_ok and isinstance(d, list))
        if has_claims and declared:
            stale.append({"store": st, "n_claims": len(d["claims"]),
                          "why": "declared as not a claim store, but it now carries a top-level claims list",
                          "declared_why": (by_name.get(st) or {}).get("why"),
                          "remedy": "the declaration is out of date; this is a store the reader is dropping"})
        elif has_claims:
            stat = os.stat(f)
            new_since_build = read_at_build.get(st) != (stat.st_mtime_ns, stat.st_size)
            (pending if new_since_build else unexplained).append(
                {"store": st, "n_claims": len(d["claims"]),
                 "why": ("added or rewritten since this model was built; awaiting a rebuild" if new_since_build
                         else "the build read this file and did not carry it"),
                 "remedy": "rebuild" if new_since_build else "why did the reader skip a file with claims?"})
        elif declared:
            explained.append({"store": st, "read_as": (by_name.get(st) or {}).get("read_as", "not a claim store (top level is an array)")})
        else:
            nested = 0
            if isinstance(d, dict):
                nested = sum(len(v) for v in _nested_claim_lists(d))
            unexplained.append({"store": st, "mb": round(os.path.getsize(f) / 1e6, 2),
                                "top_level_keys": sorted(d)[:8] if isinstance(d, dict) else "(array)",
                                "claims_nested_below_the_top_level": nested,
                                "why": "not a store in the model and declarations/build-files.json does not explain it",
                                "remedy": "work out why it is not a store before declaring it away"})
    for st in sorted(by_name):
        if not os.path.exists(os.path.join(paths.BUILD, st + ".json")):
            gone.append({"store": st, "why": "declared here but the file no longer exists"})

    fail = bool(unexplained or stale or gone or p4)
    return {"name": "RS-G5 every build file accounted for",
            "status": "FAIL" if fail else "PASS",
            "counts": {"files_in_build": len(files), "stores_in_the_model": len(in_model),
                       "unexplained": len(unexplained), "declaration_stale": len(stale),
                       "declared_but_gone": len(gone), "explained": len(explained),
                       "pending_a_rebuild": len(pending), "reader_no_longer_refuses": len(p4)},
            "report": {"unexplained": unexplained, "declaration_stale": stale,
                       "declared_but_gone": gone, "reader_no_longer_refuses": p4,
                       "pending_a_rebuild_INFORMATION": pending}}


# The shapes the reader MUST refuse, and the one it must accept. Held here rather than
# inferred from what happens to be on disk today: a gate that only ever sees real inputs
# passes happily on the day the reader loses a shape. Fetching's P4, carried over from
# gate_photographs_measurable.py -- show the reader something it cannot read and require
# it to notice, instead of waiting for a real file to prove it.
P4_SPECIMENS = [
    ({"claims": []},                                        True,  "the one shape the reader accepts"),
    ({"claims": [{"x": 1}], "source": {}},                  True,  "the same, with a claim in it"),
    ({"runs": {"a": {"guides": {"b": {"claims": [{}]}}}}},  False, "claims nested below the top level (guide-pre1950-delimited's shape)"),
    ([{"claims": []}],                                      False, "a bare JSON array"),
    ({"records": []},                                       False, "an object whose claim list is under another name"),
    ({"claims": {"a": 1}},                                  False, "a `claims` key that is not a list"),
    ({},                                                    False, "an empty object -- what a truncated write leaves"),
]


def _p4_the_reader_still_refuses(is_claim_store):
    """Does the reader's own predicate still mean what it meant? Every specimen, every run.

    RS-G5 answers "is every build file accounted for" by asking the reader what counts as
    a store. That answer is only worth having while the question is still the same one. If
    `is_claim_store` quietly widened -- or narrowed, and started refusing the shape the
    whole archive is written in -- this gate would keep reporting PASS over a reader that
    had changed underneath it. So it is not trusted, it is tested, and a disagreement is a
    FAIL that names the specimen rather than a silence."""
    out = []
    for spec, want, what in P4_SPECIMENS:
        got = bool(is_claim_store(spec))
        if got != want:
            out.append({"specimen": what, "reader_says_claim_store": got, "must_be": want,
                        "why": "build_read_model.is_claim_store no longer means what this gate assumes",
                        "remedy": "the reader changed; RS-G5 and declarations/build-files.json must be re-read against it"})
    return out


def _nested_claim_lists(node, depth=0):
    """Claim lists that are not at the top level -- the shape the reader cannot see.
    Reported so an absence can be sized, never ingested from here."""
    if depth > 4: return
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "claims" and isinstance(v, list) and depth: yield v
            elif isinstance(v, (dict, list)): yield from _nested_claim_lists(v, depth + 1)
    elif isinstance(node, list):
        for v in node[:200]:
            if isinstance(v, (dict, list)): yield from _nested_claim_lists(v, depth + 1)



def g6(conn, ctx):
    """A disagreement between two values that read to the same thing is not a
    disagreement, and this is the something that refuses to record one.

    Ryan's ruling, 2026-09-07, given for drafts and for `61"` read as `6-1` and stated
    as a property: compare on the FACT, not the encoding. RS-G1 already held one
    instance of it before anyone saw it as one -- two spellings of a calendar day are
    one day -- and this generalises it to every family the archive declares a reading
    for.

    ONE DEFINITION, IMPORTED. The reading is Parsing's `dataset/src/readings.py`,
    applied through `reading_view.py`, which loads it BY FILE PATH so no module of
    another name can answer for it. This gate does not carry its own copy of the rule;
    carrying its own copy of the reader's rule is exactly how RS-G5 was found wanting
    this afternoon, and a duplicate `readings.py` in this directory took the bio
    endpoint down an hour later. Two copies of a rule is the defect; two names for one
    module is the same defect wearing a hat.

    A READER THAT CANNOT RUN IS NOT A PASS. If the shared reader is unavailable this
    FAILS with `reader_unavailable` rather than reporting a clean sheet it did not
    check. Parsing's R3 is the reason it matters in both directions: their first
    `height()` did not accept `5-10`, PFA's own format, and a reader that cannot read
    the archive does not merely fail to remove false disagreements -- it hides real
    ones, silently.

    NOT NORMALISATION. Nothing is rewritten. The store keeps what each source printed;
    the gate only refuses to let the model RECORD a disagreement that isn't one.
    """
    import reading_view as RV
    fams = set(RV.families())
    # WHAT WAS NOT CHECKED, IN THE GATE LINE. Green meaning "nothing to check" and green
    # meaning "everything checked" have been the same answer three times: this gate when
    # only two families were declared, RS-G8 when its check was derived from the
    # declaration it was checking, and `position` -- declared a family with NO reading, so
    # the builder grouped by the literal, published 32,372 fabricated disagreements, and
    # every one of them was skipped here because a family with no reading is not in
    # `fams`. The property that a declared family MUST have a reading is
    # src/gate_family_readings.py's and is not duplicated here -- two gates checking one
    # rule is how a rule and its check drift apart. What belongs here is the NUMBER, so a
    # reader of this line can see the size of what it did not look at.
    _declared, _unread = set(), []
    try:
        import json as _j, os as _o
        _d = _j.load(open(_o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))),
                                       "service", "declarations", "predicate-families.json")))
        # A DATE FAMILY IS READ BY service/dates.py, NOT BY readings.py, so it needs no
        # VALUE_READINGS entry and is not counted as unread. Same test as
        # src/gate_family_readings.py A1, which owns the property; if the two ever
        # disagree the gate that owns it is the one to change.
        _declared = {k: v for k, v in (_d.get("families") or {}).items()
                     if not k.startswith("_") and (v or {}).get("kind") != "date"}
        _declared = set(_declared)
        _unread = sorted(_declared - fams)
    except Exception:
        pass
    if not fams:
        return {"name": "RS-G6 no false disagreement", "status": "FAIL",
                "counts": {"families_with_a_reading": 0, "checked": 0, "false": 0},
                "report": {"reader_unavailable": [{"why": "dataset/declarations/readings.json declares no reading",
                                                   "declaration": RV.DECL,
                                                   "remedy": "a gate that cannot run is not a pass"}]}}
    if RV._shared_reader() is None:
        return {"name": "RS-G6 no false disagreement", "status": "FAIL",
                "counts": {"families_with_a_reading": len(fams), "checked": 0, "false": 0},
                "report": {"reader_unavailable": [{"why": "dataset/src/readings.py could not be loaded",
                                                   "remedy": "a gate that cannot run is not a pass; it never reports a clean sheet it did not check"}]}}
    false, checked, unread_families = [], 0, []
    skipped_no_reading = 0
    for r in conn.execute("SELECT person, family, groups FROM contested"):
        fam = r[1]
        if fam not in fams:
            # COUNTED, not silent. A contested row whose family has no reading is a row
            # this gate cannot judge, and its size is the difference between a clean
            # sheet and an empty one.
            if fam in _declared or _unread: skipped_no_reading += 1
            continue
        try: groups = json.loads(r[2])
        except (TypeError, ValueError): continue
        if len(groups) < 2: continue
        checked += 1
        # RE-GROUP EVERY VALUE WITH THE SHARED GROUPER, and compare the COUNT to what the
        # model recorded. Comparing one representative per group with same() is not the
        # same test and gives the wrong answer on a dict reading: same() is not transitive,
        # so a draft value stating no league matches BOTH an AFL fact and an NFL one, and
        # whichever it represents makes two real groups look like one. RV.group refines a
        # group's fact as values join it, which is what makes first-match grouping safe --
        # and this gate must use that same code, not a second reading of the same rule.
        vals = [v for g in groups for v in g]
        reads = [RV.read(fam, v) for v in vals]
        if any(x is None for x in reads):
            unread_families.append(fam); continue          # unreadable takes no part
        gs, unread = RV.group(fam, vals)
        if len(gs) + len(unread) < len(groups):
            false.append({"person": r[0], "family": fam,
                          "model_groups": len(groups), "reader_groups": len(gs) + len(unread),
                          "groups": groups[:3],
                          "why": "the model records more groups than the declared reading "
                                 "supports: values it calls different read to the same fact",
                          "remedy": "the grouping must use the declared reading -- and the "
                                    "SAME implementation of it -- before recording a disagreement"})
    return {"name": "RS-G6 no false disagreement",
            "status": "FAIL" if false else "PASS",
            "counts": {"families_needing_a_reading": len(_declared),
                       "of_those_with_one": len(_declared & fams) if _declared else len(fams),
                       "families_WITHOUT_a_reading": len(_unread),
                       "readers_available": len(fams),
                       "contested_rows_skipped_because_their_family_has_no_reading": skipped_no_reading,
                       "contested_facts_checked": checked,
                       "false_disagreements": len(false),
                       "facts_with_an_unreadable_value": len(unread_families)},
            "report": {"false_disagreements": false[:50],
                       "families_declared_with_NO_reading": [
                           {"families": _unread,
                            "why_it_matters": "the builder groups such a family by the LITERAL, so "
                                              "every notational difference becomes a disagreement, "
                                              "and this gate cannot see one of them",
                            "held_by": "src/gate_family_readings.py A1"}] if _unread else [],
                       "families_read_INFORMATION": [{"families": sorted(fams),
                                                      "read_by": "dataset/src/readings.py, loaded by path",
                                                      "declared_in": RV.DECL}]}}



def g7(conn, ctx):
    """RS-G7: a league token that is not a league fails.

    REAL_LEAGUES has been computed in build_read_model.py since the club table was
    built, three functions above the code that assigned a league. Nothing compared
    the two, so twelve stores declared "NOT A LEAGUE -- ..." in prose were parsed as
    `v.split(" ")[0]` and got a league literally called NOT. By 2026-09-08 it was the
    LARGEST league in the archive -- 132,038 stint keys against the NFL's 114,369 --
    and it also handed 32,791 men the role "not". Nothing was wrong with the
    declaration; it read correctly to a person and wrongly to a parser.

    Ryan ruled the splitting rule changes, not the prose. This gate is the comparison
    that was never made: every league on a stint or person_season claim must be a
    league the CLUB TABLE holds, or one of the single-word tokens the rebuild
    declaration names deliberately (COACHES, IND, DRAFT -- each with its reason).
    The exemption set is DERIVED from the declaration and never typed here.

    NULL is not a failure. A store that declares it has no league, whose season key
    names no league the club table holds, leaves the league unknown -- and unknown is
    a fact the archive is allowed to hold. A FABRICATED league is not."""
    sys.path.insert(0, os.path.join(paths.DATASET, "src"))
    import clubs as ac, league_tokens as LT
    real = {lg["league"] for c in ac.Clubs().T["clubs"] for s in c["segments"] for lg in s["leagues"]}
    allowed = real | LT.declared_non_leagues(paths.INDEX_REBUILD_DECL)
    found = {r[0]: r[1] for r in conn.execute(
        "SELECT league, COUNT(*) FROM claim WHERE scope IN ('stint','person_season') "
        "AND league IS NOT NULL AND league != '' GROUP BY league")}
    bad = {l: n for l, n in found.items() if l not in allowed}
    return {"name": "RS-G7 every league token is a league", "status": "FAIL" if bad else "PASS",
            "counts": {"distinct_tokens": len(found),
                       "in_the_club_table": len([l for l in found if l in real]),
                       "declared_non_competitions": len([l for l in found if l in allowed and l not in real]),
                       "fabricated": len(bad), "claims_on_fabricated_tokens": sum(bad.values())},
            "report": [{"token": l, "claims": n,
                        "remedy": "either the club table holds this league, or declare it in "
                                  "store_league_tokens with its reason, or the store's league is wrong"}
                       for l, n in sorted(bad.items(), key=lambda x: -x[1])]}


def g8(conn, ctx):
    """RS-G8: what a thing IS, re-derived from the model and compared with the
    declaration -- in both directions.

    Three classifications were string tests inside queries.py until 2026-09-09, and
    all three had already gone wrong: `store.startswith("stats-")` served 2,688,935
    PFA statistics as ordinary facts because those stores are named `pfa-stats-*`;
    `league NOT IN ('COACHES',...)` counted 41,662 staff claims as players once the
    coaching subjects were given real leagues; `predicate not in ("name",)` served
    one name predicate twice and left two unsearchable.

    THIS GATE DOES NOT TRUST declarations/classification.json. It re-derives each
    classification from the claims and lists every difference, so a store or a
    predicate that arrives tomorrow fails loudly instead of being read by its name.

    HOW EACH IS DERIVED, with the property it rests on:

    1. STATISTIC STORES, as a PARTITION. Measured 2026-09-09: the predicate sets are
       disjoint -- 171 predicates appear only in the 228 declared statistics stores,
       184 only outside, and none in both. The gate checks that partition directly:
       a predicate carried by BOTH a declared statistics store and an undeclared one
       fails and names both sides. It does not derive the statistic vocabulary from
       the declaration and then test the declaration against it -- that first version
       passed on an EMPTY declaration and cascaded 227 innocent stores on a wrong one.
       Its limit is written into the code: a statistics store sharing its vocabulary
       with nothing is invisible here.
    2. STAFF PREDICATES. Every stint predicate appearing in a declared staff store
       must be declared -- either as staff, or by name in
       `not_staff_though_it_appears_in_those_stores` with its reason. "Considered and
       excluded" and "never noticed" look identical without this.
    3. NAME PREDICATES. Every person-scoped predicate whose name contains "name"
       must be declared or explicitly not a name. A name served as a fact is a name
       search cannot find.
    4. NAME FORM. Two display-name readings against declared worked examples, both
       answers each. Ruled 2026-09-09: a display name is READ, so `Fritz Pollard`
       beats `Pollard, Frederick Douglass`, and a FULLER name beats a bare surname,
       so `Joseph T. Plunkett` beats `Plunkett`. Nothing is standardised and every
       form stays a claim. The gate protects the RULES, not the recipe -- and the
       bare-surname rule is checked on its keeps as well as its sets-aside, because a
       rule tested only where it should fire is tested on half of itself."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import classification as C
    decl_stat = C.statistic_stores(); decl_staff = C.staff_predicates()
    decl_names = C.name_predicates(); staff_stores = C.staff_stores()
    excluded = C.considered_and_not_staff()
    findings = []

    # 1. STATISTIC STORES, as a PARTITION CHECK, not a bootstrapped one.
    # The first version derived the statistic-predicate set from the declared stores
    # and then asked whether an undeclared store fell inside it -- a decider reading
    # its own output. Empty the declaration and it had nothing to compare against and
    # passed; add one wrong store and 227 innocent ones cascaded into the report.
    # What is checked instead is a property of the CLAIMS: every predicate must be
    # carried either wholly by declared statistics stores or wholly by other stores.
    # A predicate that straddles the boundary names both sides and cannot cascade.
    by_store = collections.defaultdict(set); by_pred = collections.defaultdict(set)
    for st, pr in conn.execute("SELECT DISTINCT store, predicate FROM claim"):
        by_store[st].add(pr); by_pred[pr].add(st)
    straddling = 0
    for pr, stores in sorted(by_pred.items()):
        inside = sorted(s for s in stores if s in decl_stat)
        outside = sorted(s for s in stores if s not in decl_stat)
        if inside and outside:
            straddling += 1
            findings.append({"what": "a predicate carried both by a declared statistics store and by an undeclared one",
                             "predicate": pr, "declared_statistics_stores": inside[:5], "other_stores": outside[:5],
                             "remedy": "one side is misfiled: either those other stores are statistics stores and belong in "
                                       "declarations/classification.json, or this predicate does not belong in a statistics store"})
    # WHAT THIS CANNOT SEE, stated rather than left as a silent pass: a statistics store
    # whose predicates appear in NO other store is invisible to a partition check --
    # there is nothing to straddle. In practice a new statistics store shares its
    # vocabulary with the 228 already declared (`stats-nfl-2025` carries the same
    # columns as `stats-nfl-2024`), which is the case this catches. A store with a
    # wholly novel statistical vocabulary must be declared by the person who ingests it.
    stale = sorted(s for s in decl_stat if s not in by_store)

    # 2. staff predicates, derived from the stores that carry them
    if staff_stores:
        q = ",".join("?" * len(staff_stores))
        for pr, n in conn.execute(f"SELECT predicate, COUNT(*) FROM claim WHERE scope='stint' AND store IN ({q}) GROUP BY predicate", sorted(staff_stores)):
            if pr not in decl_staff and pr not in excluded:
                findings.append({"what": "a stint predicate in a staff store that is neither declared staff nor declared not-staff",
                                 "predicate": pr, "claims": n,
                                 "remedy": "add it to staff_predicates, or to not_staff_though_it_appears_in_those_stores with its reason"})

    # 3. name predicates, derived from the predicate names themselves
    declared_not_names = set(C.raw()["name_predicates"].get("_not_names", []))
    for pr, n in conn.execute("SELECT predicate, COUNT(*) FROM claim WHERE scope='person' AND lower(predicate) LIKE '%name%' GROUP BY predicate"):
        if pr not in decl_names and pr not in declared_not_names:
            findings.append({"what": "a person-scoped predicate that names a man and is not declared a name",
                             "predicate": pr, "claims": n,
                             "remedy": "add it to name_predicates, or to _not_names with its reason; a name served as a fact is one search cannot find"})

    # ORDER MATTERS. Both statistics checks rest on the SAME disjointness property, so
    # one wrong entry cascades: drop `pfa-stats-1920s` and all 227 survivors report a
    # predicate now seen "outside". The cause is always a declared store carrying a
    # predicate seen elsewhere, so that finding is listed first and the cascade after.
    ORDER = {"a predicate carried both by a declared statistics store and by an undeclared one": 0}
    findings.sort(key=lambda f: ORDER.get(f["what"], 1))
    # 4. NAME FORM. The reading that decides surname-first from forename-first is
    # checked against DECLARED WORKED EXAMPLES, both answers, every one a real string
    # in the index. This is not a tautology check on the recipe -- display_name filters
    # its own candidates and would always agree with itself. It is a check that the
    # RULE still gives the answers it was ruled to give, so editing the suffix list or
    # the split fails here instead of quietly re-sorting 2,472 names.
    ex = C.raw().get("name_forms", {}).get("worked_examples", {})
    for want, key in ((True, "surname_first"), (False, "forename_first")):
        for n in ex.get(key, []):
            got = C.is_surname_first(n)
            if got != want:
                findings.append({"what": "the name-form reading disagrees with a declared worked example",
                                 "name": n, "declared": key, "reading_says": "surname_first" if got else "forename_first",
                                 "remedy": "either the rule changed and this example must be re-ruled, or the rule is wrong"})
    # the bare-surname rule, on its own declared examples and then on the model
    for n, others in ex.get("bare_surname_set_aside", []):
        if not C.is_bare_surname(n, others):
            findings.append({"what": "a name the ruling sets aside is not set aside", "name": n,
                             "held_beside_it": others,
                             "remedy": "the rule changed and this example must be re-ruled, or the rule is wrong"})
    for n, others in ex.get("bare_surname_kept", []):
        if C.is_bare_surname(n, others):
            findings.append({"what": "a name the ruling KEEPS is being set aside", "name": n,
                             "held_beside_it": others, "remedy": "as above"})
    # THE PROPERTY, over the whole model: no man whose names include a one-word surname
    # AND a longer name ending in it may still be shown the surname. Checked on
    # person_name, which is where the served display name is derived from.
    held = collections.defaultdict(set)
    for pid, nm in conn.execute("SELECT person, name FROM person_name"): held[pid].add(nm)
    bare_pairs = sum(1 for pid, ns in held.items() if any(C.is_bare_surname(n, ns) for n in ns))

    commas = conn.execute("SELECT COUNT(*) FROM person_name WHERE name LIKE '%,%'").fetchone()[0]
    filed = sum(1 for r in conn.execute("SELECT name FROM person_name WHERE name LIKE '%,%'") if C.is_surname_first(r[0]))

    return {"name": "RS-G8 classification is declared, not read off a name",
            "status": "FAIL" if findings else "PASS",
            "counts": {"statistic_stores_declared": len(decl_stat),
                       "predicates_seen": len(by_pred),
                       "predicates_wholly_inside_a_statistics_store": len([p for p, st in by_pred.items() if st <= decl_stat]),
                       "predicates_straddling_the_boundary": straddling,
                       "staff_predicates_declared": len(decl_staff),
                       "name_predicates_declared": len(decl_names),
                       "worked_examples_checked": sum(len(v) for k, v in ex.items() if not k.startswith("_")),
                       "index_names_with_a_comma": commas,
                       "people_holding_a_bare_surname_beside_a_fuller_name": bare_pairs,
                       "of_those_read_as_surname_first": filed,
                       "differences": len(findings),
                       "declared_stores_no_longer_in_the_model": len(stale)},
            "report": findings + ([{"what": "declared statistics stores the model no longer holds",
                                    "stores": stale[:20],
                                    "remedy": "informational: a store may be renamed or retired. Remove it when that is deliberate."}] if stale else [])}


GATES = [g1, g2, g3, g4, g5, g6, g7, g8]


def run(conn, ctx):
    return [g(conn, ctx) for g in GATES]


def main():
    if not os.path.exists(paths.READ_MODEL):
        print("no read model at", paths.READ_MODEL); return 2
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    idx = json.load(open(paths.PERSON_INDEX))
    ctx = {"index_keys": {k for k, v in idx.items() if k != "_clubs" and isinstance(v, dict)},
           # claims ∪ identity ONLY. The person table also carries index-only ids so /people/{id} can answer
           # for them; a set that already contains the index cannot fail G4 (found 2026-09-07, twice).
           "people": {r[0] for r in conn.execute("SELECT id FROM person WHERE in_identity=1 OR n_claims>0")}}
    del idx
    rc = 0
    for g in run(conn, ctx):
        print(f"{g['status']:4s} {g['name']}: {json.dumps(g['counts'])}")
        if g["status"] == "FAIL":
            rc = 1
            for k, v in g["report"].items():
                if v and not k.endswith("INFORMATION") and k not in ("declared", "declared_seen", "stores_without_a_table"):
                    print(f"     {k}: {json.dumps(v)[:1500]}")
        # Ruled 2026-09-07: information that must stay visible on EVERY run, so it never becomes normal
        for k, v in g["report"].items():
            if k.endswith("INFORMATION") and v:
                print(f"     {k.replace('_INFORMATION', '')} ({len(v)}):")
                for item in v: print(f"        {json.dumps(item)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
