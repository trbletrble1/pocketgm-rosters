"""The service's VIEW of the archive's readings. Not a reader -- see the name.

NAMED `reading_view`, NOT `readings`, AND THAT IS THE WHOLE POINT. It was called
`readings.py` for eleven minutes on 2026-09-07 and in that time it broke Parsing's
code: `dataset/src/bio_select.py` does `import readings`, this service puts its own
directory first on `sys.path`, so bio_select got THIS module instead of
`dataset/src/readings.py`. Mine returned dicts where theirs returns strings, and
`_differ()` did `set().add(a dict)` -- every bio 503'd and I reported the crash to
Parsing as a bug in their file. It was mine. Two modules with one name inside one
`sys.path` is the same defect as two copies of one rule, wearing a different hat.

, so two encodings of one fact stop looking
like a disagreement. The store is never touched.

Ryan's ruling, 2026-09-07: *two representations of the same draft are not a
disagreement. Compare on the fact, not the encoding. Declare the reading, keep both
printed forms beside it, labelled derived, so the reading can be recomputed or
withdrawn and neither source's version is lost.* And: *do not treat it as a special
case for drafts -- the property is that a disagreement between two values that read
to the same thing is not a disagreement, and something should refuse to record one.*

So this is a TABLE, not a draft parser. `declarations/readings.json` names every
family that has a reading and what the fact consists of; RS-G6 derives from the same
file. Dates were the first instance of this property before anyone saw it as one, and
they stay where they are -- `dates.py`, recipe `date-reading@v1` -- with this table
pointing at them rather than reimplementing them. A second implementation of a rule is
how the reader and its gate drifted apart this afternoon.

THREE THINGS THIS DOES NOT DO.
  It does not normalise anything. `5th round (36th overall) 1941 New York Giants`
  stays that string in the store forever; the reading is derived at read time and
  labelled `derived` wherever it is shown.
  It does not merge what it cannot read. A value with no reading stays its own group
  and is counted as unreadable, exactly as an unreadable date does under RS-G1.
  It does not hide a real difference. A different round, pick, club or day is a real
  disagreement, and collapsing the false ones is what stops it being buried.
"""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
import paths, dates

# ONE DEFINITION, IMPORTED. The ruling lives in the ARCHIVE's declaration and the
# reader that applies it is Parsing's `src/readings.py`. This module does not carry a
# second copy of either -- within ten minutes of the same ruling we had both written
# one, which is the drift Ryan told me to carry forward as a property after RS-G5 was
# found holding its own copy of the reader's acceptance test. If the shared reader
# cannot be imported or raises, this says "no reading" and the disagreement stands. It
# NEVER falls back to a second reader that might answer differently.
DECL = os.path.join(paths.DECLARATIONS, "readings.json")
SRC = os.path.normpath(os.path.join(HERE, "..", "src"))
_T = None


def table():
    global _T
    if _T is None:
        d = json.load(open(DECL, encoding="utf-8")) if os.path.exists(DECL) else {}
        # the archive's declaration calls them VALUE_READINGS; read its own key, not a
        # name of my choosing, so a rename there is visible here rather than silent.
        _T = d.get("VALUE_READINGS") or d.get("readings") or {}
    return _T


_READER = None


def _shared_reader():
    """Parsing's reader, or None. Never a substitute, and never by bare module name.

    Loaded from its FILE PATH under a distinct module name, so it cannot be satisfied by
    something else called `readings` that happens to be earlier on `sys.path` -- which is
    exactly how this went wrong the first time. Reloaded when the file changes, because
    Parsing edits it while the service is up."""
    global _READER
    fp = os.path.join(SRC, "readings.py")
    try:
        stamp = os.stat(fp).st_mtime_ns
    except OSError:
        return None
    if _READER and _READER[0] == stamp: return _READER[1]
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("archive_readings", fp)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        fn = getattr(m, "read", None)
    except Exception:
        return None
    _READER = (stamp, fn)
    return fn


def families():
    return sorted(table())


def recipe(family):
    spec = table().get(family)
    return (spec or {}).get("recipe") or "src/readings.py@" + str(family)


def _clean_club(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def read(family, value):
    """-> the shared reader's reading of this value, or None if it cannot be read.

    Delegates to `src/readings.py`. Never raises: that file is edited while this service
    is up, and a half-finished edit there must not become an error here -- it becomes
    "unreadable", which is already a first-class answer that refuses to merge anything."""
    fn = _shared_reader()
    if fn is None: return None
    try:
        return fn(family, value)
    except Exception:
        return None


def _read_locally_UNUSED(family, value):
    """Kept only to show what was deleted: the service's own draft/date reader, removed
    2026-09-07 when the ruling was converged onto one definition."""
    spec = table().get(family)
    if not spec: return None
    if spec.get("implemented_in") == "dates.py":
        r = dates.read(value if isinstance(value, str) else str(value))
        return None if r is None else {k: v for k, v in zip(("year", "month", "day"), dates.key(r) or ()) if v is not None} or None
    fact = {}
    if isinstance(value, dict):
        for field, keys in (spec.get("object_fields") or {}).items():
            for k in keys:
                if value.get(k) not in (None, ""):
                    fact[field] = value[k]; break
    elif isinstance(value, str):
        for pat in (spec.get("string_patterns") or []):
            m = re.search(pat["pattern"], value, re.I)
            if m:
                fact = {k: v for k, v in m.groupdict().items() if v not in (None, "")}
                break
    else:
        return None
    if not fact: return None
    for k in ("year", "round", "overall_pick"):
        if k in fact:
            try: fact[k] = int(str(fact[k]).strip())
            except (TypeError, ValueError): fact.pop(k)
    if "club" in fact:
        fact["club"] = _clean_club(fact["club"]) or None
        if not fact["club"]: fact.pop("club")
    required = [f for f in ("year", "overall_pick") if f in (spec.get("the_fact") or [])]
    if required and not all(f in fact for f in required): return None
    return fact or None


def same(family, a, b):
    """Two readings state the same fact when every field BOTH carry agrees; a field only
    one of them carries is silence, not a difference. A scalar reading (the shared reader
    returns one for height and weight) compares by equality."""
    if a is None or b is None: return False
    if not isinstance(a, dict) or not isinstance(b, dict): return a == b
    shared = set(a) & set(b)
    if not shared: return False
    return all(a[k] == b[k] for k in shared)


def group(family, values):
    """-> (groups, unreadable). `values` is a list of raw values as printed.

    A group is a list of indices into `values` that all read to one fact. Values with
    no reading are returned separately and are NEVER folded into a group: unreadable is
    its own answer, the same way an unreadable date is under RS-G1."""
    reads = [read(family, v) for v in values]
    groups, facts = [], []
    unreadable = [i for i, r in enumerate(reads) if r is None]
    for i, r in enumerate(reads):
        if r is None: continue
        for gi, f in enumerate(facts):
            if same(family, f, r):
                groups[gi].append(i)
                if isinstance(f, dict) and isinstance(r, dict):
                    facts[gi] = {**f, **r}      # the fuller reading of the two
                break
        else:
            groups.append([i]); facts.append(r)
    return [{"indices": g, "fact": f} for g, f in zip(groups, facts)], unreadable


def collapse(family, rows):
    """The whole ruling in one call, for a set of {value, source} rows.

    -> None when this family has no declared reading, or when the rows do not all read
    to one fact (a real disagreement, or something unreadable -- either way it stands).
    -> a derived reading block when they DO all read to one fact: the fact, and every
    printed form kept beside it with its source, so the reading can be recomputed or
    withdrawn and neither source's version is lost."""
    if family not in table(): return None
    values = [r.get("value") for r in rows]
    if len(values) < 2: return None
    groups, unreadable = group(family, values)
    if unreadable or len(groups) != 1: return None
    return {"basis": "derived", "derived": True, "recipe": recipe(family) or "readings@src",
            "read_by": "dataset/src/readings.py (Parsing's; one definition, imported)",
            "fact": groups[0]["fact"],
            "why": "these are one %s in %d encodings, not a disagreement" % (family, len(values)),
            "values_as_printed": [{"value": r.get("value"), "source": r.get("source")} for r in rows],
            "ruled": (table()[family] or {}).get("ruled"),
            "declared_in": "dataset/declarations/readings.json"}
