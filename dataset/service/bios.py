"""The bio, wired in. NOT the bio itself.

Parsing owns `dataset/src/bio_select.py` (what a bio says) and `bio_write.py`
(how it says it). Nothing here reasons about either. This module does four
things and no more: it imports them, it holds the corpus-wide `Tables` object
they need, it notices when their inputs change underneath it, and it refuses to
let them take the service down.

WHY A CACHE AT ALL. The generator is corpus-wide, not per-person: `Tables()`
builds career-length percentiles, per-(league, year, column) comparator pools
and the salience map over EVERY man before it can say anything about ONE.
Measured on this machine: ~3.2 s and ~2.4 GB resident to build, then ~0.1 ms
per bio. So it is built once, lazily -- a listener that is never asked for a bio
never pays -- and kept.

WHY IT MUST EXPIRE. The generator reads the build stores DIRECTLY; the rest of
this service reads a SQLite read model built from them. The two can drift, and
three sessions rewrite those stores several times an hour. All six of its inputs
are already inputs of the read model, so the same mtime record that tells a
reader the model is behind also tells this cache to rebuild. A bio is never
served from a Tables built on inputs that have since changed without saying so.

WHAT IS NOT HERE. No fallback. `bio_select.required()` raises SystemExit when a
load-bearing input is missing -- deliberately, because a missing input does not
degrade the prose, it silently rewrites it. SystemExit is a BaseException and
would tear down the worker, so it is caught and turned into a 503 that names the
file. The service refuses to answer rather than answer from a different corpus.

READ-ONLY. Neither generator module opens a file for writing, and a gate asserts
that no bio request touches the mtime of anything under build/ or build-reports/.
"""
import os, sys, json, time, hashlib, threading
import reading_view as readings
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
BASE = os.path.normpath(os.path.join(HERE, ".."))

# The generator's own inputs, relative to dataset/. bio_select loads the first at
# import and the rest in Tables._aux(); clubs.json is reached through _club_table().
INPUTS = ["build-reports/person-index.json", "build/pfa-pre1950.json",
          "build/nflverse-rosters.json", "build/pfr-drafts.json",
          "build/nflverse-draft.json", "build/guide-pre1950-delimited.json",
          "build/clubs.json"]
MODULES = ["bio_select.py", "bio_write.py"]

_lock = threading.Lock()
_state = {"T": None, "select": None, "write": None, "built_at": None, "build_seconds": None,
          "stamp": None, "recipe": None}


class Unavailable(Exception):
    """The generator cannot run. Carries why, for a 503 that names the cause."""
    def __init__(self, why, **extra): super().__init__(why); self.extra = extra


def _stamp(paths):
    out = {}
    for rel in paths:
        fp = os.path.join(BASE, rel)
        try:
            st = os.stat(fp); out[rel] = [st.st_mtime_ns, st.st_size]
        except OSError:
            out[rel] = None
    return out


def _recipe():
    """A recipe name that CHANGES when Parsing changes the generator. A bio labelled
    with a fixed version string would claim two different prose layers were the same
    thing. The digest is over both modules' bytes."""
    h = hashlib.sha256()
    for m in MODULES:
        try: h.update(open(os.path.join(SRC, m), "rb").read())
        except OSError as e: raise Unavailable(f"the bio generator is not readable: {e}")
    return "bio/three-slot@" + h.hexdigest()[:12]


def _load():
    """Build Tables. Caller holds the lock."""
    if SRC not in sys.path: sys.path.insert(0, SRC)
    t0 = time.time()
    stamp = _stamp(INPUTS + [os.path.relpath(os.path.join(SRC, m), BASE) for m in MODULES])
    try:
        import importlib
        bs = importlib.import_module("bio_select")
        bw = importlib.import_module("bio_write")
        # Parsing edits these files while the service is up; a stale module would serve
        # prose under a recipe name that no longer describes it.
        if _state["stamp"] is not None:
            bs = importlib.reload(bs); bw = importlib.reload(bw)
        T = bs.Tables()
    except SystemExit as e:                      # bio_select.required(): a load-bearing input is gone
        raise Unavailable(str(e) or "the bio generator refused to run", kind="missing_input")
    except (OSError, ValueError, KeyError) as e:  # a store being rewritten under us, or malformed
        raise Unavailable(f"the bio generator could not read its inputs: {type(e).__name__}: {e}", kind="input_unreadable")
    _state.update(T=T, select=bs.select, write=bw.write, built_at=time.time(),
                  build_seconds=round(time.time() - t0, 2), stamp=stamp, recipe=_recipe())


def _changed():
    """Which of the generator's own inputs have moved since Tables was built."""
    if _state["stamp"] is None: return []
    now = _stamp(list(_state["stamp"]))
    return sorted(k for k in _state["stamp"] if now.get(k) != _state["stamp"][k])


def tables():
    with _lock:
        if _state["T"] is None or _changed():
            _load()
        return _state


def status():
    s = _state
    return {"loaded": s["T"] is not None, "built_at": s["built_at"] and time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(s["built_at"])),
            "build_seconds": s["build_seconds"], "recipe": s["recipe"],
            "people_with_a_bio": len(s["T"].people) if s["T"] else None}


def bio(person_id):
    """Prose and panel for one man, or None if the generator holds no bio for him.

    Returns the generator's own output, relabelled but not reshaped. The prose is
    derived and says so; the panel is the generator's `vitals`, which already names
    a source for every value and lists a disagreeing field under `disagreements`
    without resolving it. Nothing here chooses between values, and nothing here
    edits a sentence."""
    st = tables()
    T = st["T"]
    if person_id not in T.people:
        return None
    try:
        F = st["select"](T, person_id)
        prose = st["write"](F)
    except SystemExit as e:
        raise Unavailable(str(e) or "the bio generator refused to run", kind="missing_input")
    except Exception as e:
        # The generator is Parsing's file and Parsing edits it while this service is up.
        # A half-finished edit there must not take the service down or leak a traceback:
        # it becomes a 503 that NAMES the file, the line and the error, so whoever is
        # editing sees what broke. Proven the hard way at 16:52 on 2026-09-07, when a
        # new `_differ()` did `set().add(a dict)` and every bio 500'd.
        import traceback
        tb = traceback.extract_tb(e.__traceback__)
        where = [f"{os.path.basename(f.filename)}:{f.lineno} in {f.name}" for f in tb
                 if os.path.basename(f.filename) in ("bio_select.py", "bio_write.py")]
        raise Unavailable(
            f"the bio generator raised {type(e).__name__}: {e}",
            kind="generator_error",
            where=where or [f"{os.path.basename(f.filename)}:{f.lineno}" for f in tb[-1:]],
            owner="dataset/src/bio_select.py and bio_write.py -- not this service's to fix",
            note="the archive is untouched; every other route is unaffected")
    panel = dict(F.get("vitals") or {})
    disagreements = panel.pop("disagreements", [])
    recipe = st["recipe"]
    return {
        "prose": {"value": prose, "basis": "derived", "derived": True, "recipe": recipe,
                  "why": "assembled at read time from claims by the selection and wording layers; it is not itself a claim",
                  "lead": F.get("lead_kind"), "close": F.get("close_kind"),
                  "coaching_only": bool(F.get("coaching_only")),
                  "owner": "dataset/src/bio_select.py and bio_write.py"},
        "panel": {"basis": "derived", "derived": True, "recipe": recipe,
                  "why": "identity as data, beside the prose and never inside it; every value names its source and nothing is picked",
                  "fields": panel, "disagreements": disagreements},
        "slots": [{"slot": f.get("slot"), "kind": f.get("kind"), "score": f.get("score")} for f in F.get("facts") or []],
    }


def why_no_bio(person_id):
    """The generator's population is smaller than the archive's: it takes only men
    who have at least one season AND a name. Say which, rather than 404-ing blank."""
    st = tables(); T = st["T"]
    import bio_select as bs
    p = bs.IDX.get(person_id)
    if p is None: return "no such person in the person index the generator reads"
    if not p.get("seasons"): return "the index holds no season for him, so there is no career to describe"
    if not p.get("name"): return "the index holds no name for him"
    return "unknown"


def panel_quieter_than_the_claims(panel_fields, contested):
    """Where the panel shows ONE value for a fact the read model holds CONTESTED.

    This reports; it does not correct. The panel is built by Parsing's `vitals()`,
    which lists a disagreement only when its own sources -- PFA, nflverse, the guides
    -- carry one. The archive holds disagreements from stores it never looks at, so
    the panel can be quieter than the claims. Measured on P_000011: three birth-date
    strings in two calendar-day groups, one value in the panel.

    Nothing here edits the panel. The endpoint carries `facts` and `contested`
    regardless, so the values are on the page either way; this only names the gap so
    a reader -- or a web page -- does not have to notice it for themselves.
    """
    by_family = {c["family"]: c for c in (contested or [])}
    out = []
    for family, rows in (panel_fields or {}).items():
        c = by_family.get(family)
        if not c: continue
        groups = len(c.get("groups") or [])
        shown = len({json.dumps(r["value"], sort_keys=True) for r in rows})
        if groups > 1 and shown <= 1:
            out.append({"family": family, "calendar_groups_in_the_claims": groups,
                        "values_in_the_panel": shown,
                        "why": "the panel names a disagreement only where its own sources carry one; this one is held by a store it does not read",
                        "where_the_values_are": "facts.%s and contested" % family,
                        "owner": "dataset/src/bio_select.py vitals(); not this service's to change"})
    return out


def panel_noisier_than_the_claims(panel_fields, panel_disagreements, facts, contested):
    """Where the panel reports a DISAGREEMENT the archive holds no contest on.

    The mirror of panel_quieter_than_the_claims, and the more dangerous direction.
    Quiet loses information; noise invents it. Parsing found the instance on
    2026-09-07: guide heights reach the panel verbatim, OCR and all, so `61"` sits
    beside PFA's `6-1` and the panel calls it a conflict between two sources that
    agree. Measured here across the 134 people holding both an unparseable guide
    height and a PFA one, 98 agree once read as digits. Genuine height and weight
    disagreements do exist and are correctly held; these are noise on top of them.

    This reports and does not correct. Reading `61"` as `6-1` is a reading decision,
    and guide-pre1950-delimited.json says in its own terms that mapping printed
    labels and values to fields is a ruling, not a parsing step. So the endpoint says
    what the archive holds and what the panel claims, and leaves the two visible.

    Matching is by family name, and by `pfa.<name>`, because the panel's field names
    and the archive's predicate families are not the same vocabulary. A field this
    cannot place is reported as unmatched rather than silently passed.
    """
    contested_families = {c["family"] for c in (contested or [])}
    out = []
    for field in (panel_disagreements or []):
        names = [field, "pfa." + field]
        held, matched = [], []
        for n in names:
            f = (facts or {}).get(n)
            if not f: continue
            matched.append(n)
            vals = f.get("values") if isinstance(f, dict) else None
            if vals: held += [v.get("value") for v in vals]
            elif isinstance(f, dict) and "value" in f: held.append(f["value"])
        shown = [r.get("value") for r in (panel_fields or {}).get(field, [])]
        if not matched:
            out.append({"field": field, "archive_families_matched": [],
                        "why": "the panel reports a disagreement on a field no predicate family of that name carries",
                        "panel_values": shown})
            continue
        # Ryan's ruling, 2026-09-07: two representations of one fact are not a
        # disagreement. Read the panel's own values on the fact before saying anything
        # about the archive -- this is the cause for ~3,200 draft "disagreements".
        reading = readings.collapse(field, (panel_fields or {}).get(field) or [])
        distinct = {json.dumps(v, sort_keys=True) for v in held}
        if reading is not None:
            out.append({"field": field, "cause": "reads_to_one_fact",
                        "archive_families_matched": matched,
                        "why": "the panel calls this a disagreement; its values read to ONE fact and differ only in encoding",
                        "reading": reading,
                        "owner": "dataset/src/bio_select.py vitals(); reported, not corrected"})
        elif field not in contested_families and len(distinct) <= 1:
            not_claims = [v for v in shown
                          if json.dumps(v, sort_keys=True) not in distinct]
            out.append({"field": field, "cause": "archive_holds_no_contest",
                        "archive_families_matched": matched,
                        "values_the_archive_holds": len(distinct),
                        "panel_values": shown,
                        "panel_values_that_are_not_claims_here": not_claims,
                        "why": "the panel reports a disagreement; the archive holds no contest on this field",
                        "owner": "dataset/src/bio_select.py vitals(); reported, not corrected"})
    return out
