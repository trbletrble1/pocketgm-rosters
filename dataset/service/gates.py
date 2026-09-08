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

NOT a gate: whether any value is correct. The archive holds disagreements on purpose.

    python3 gates.py     # run G1-G3 against the published read model, G4 against the index now
"""
import os, sys, json, glob, sqlite3
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
    for r in conn.execute("SELECT person, family, groups FROM contested"):
        fam = r[1]
        if fam not in fams: continue
        try: groups = json.loads(r[2])
        except (TypeError, ValueError): continue
        if len(groups) < 2: continue
        checked += 1
        reps = [g[0] for g in groups if g]
        reads = [RV.read(fam, v) for v in reps]
        if any(x is None for x in reads):
            unread_families.append(fam); continue          # unreadable takes no part
        for i in range(len(reads)):
            for j in range(i + 1, len(reads)):
                if RV.same(fam, reads[i], reads[j]):
                    false.append({"person": r[0], "family": fam,
                                  "group_a": groups[i], "group_b": groups[j],
                                  "both_read_as": reads[i],
                                  "why": "two groups the model records as disagreeing read to the same thing",
                                  "remedy": "the grouping must use the declared reading before it records a disagreement"})
                    break
            if false and false[-1]["person"] == r[0]: break
    return {"name": "RS-G6 no false disagreement",
            "status": "FAIL" if false else "PASS",
            "counts": {"families_with_a_reading": len(fams), "contested_facts_checked": checked,
                       "false_disagreements": len(false),
                       "facts_with_an_unreadable_value": len(unread_families)},
            "report": {"false_disagreements": false[:50],
                       "families_read_INFORMATION": [{"families": sorted(fams),
                                                      "read_by": "dataset/src/readings.py, loaded by path",
                                                      "declared_in": RV.DECL}]}}


GATES = [g1, g2, g3, g4, g5, g6]


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
