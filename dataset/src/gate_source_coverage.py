"""Every acquired file either produces a claim or is declared unread with a reason.

THE DEFECT. The archive tracks claims well and sources badly. "Wikipedia is
ingested" reads as finished; it was read for people and not for drafts, and nobody
wrote that down. 3,110 documents were catalogued in September with a `class` field
the census's own header says is "filled by reading" -- null on all 3,110. The job
was never done and NOTHING RECORDED THAT IT WASN'T.

THE PROPERTY, which is not about the instances that found it: for a FILE-SHAPED
source, acquired minus cited must be declared, with a reason, one entry per file or
glob. It will catch the next 1,727 the same way it catches these.

WHAT IT RESTS ON. The claims' own `source_record` locators. NOT the source_record
tables -- RS-G3 is red, 27 of 481 stores declare one, and the 739,486-claim store
declares none. Resting on that coverage would be measuring the declaration twice.

WHAT IT REFUSES TO PRETEND IT CAN SEE. A source whose unit is not a file must be
DECLARED not-file-shaped, with the reason it has no denominator, and is reported as
NOT COVERED -- never as a pass. A source with claims in neither list FAILS: silence
is not an exemption, which is the defect itself.

AND A SECOND PROPERTY, added after Phil Flanagan. A not-file-shaped entry must state
which of its PARTS are enumerable. "No denominator" can be true of a source whole and
false of every part of it: PFA's entry said it, and 203 draft pages -- one per year
per league -- sat on disk unread, with a 1936 Giants ninth-round pick in them. An
`enumerable_parts` list saying `unknown` is a fine answer; an absent list is not,
because it cannot be told apart from nobody having looked.

  python3 src/gate_source_coverage.py [--selftest]
"""
import os, sys, json, glob, fnmatch, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths
DECL = os.path.join(BASE, "declarations", "source-coverage.json")
SOURCES = os.path.expanduser("~/Documents/pgm3-sources")
REPORT = os.path.join(BASE, "build-reports", "source-coverage.json")


def to_file(locator, how):
    loc = str(locator).split("@")[0].strip()
    if how == "basename": return os.path.basename(loc)
    if how == "flatten_slashes": return loc.replace("/", "_")
    return loc


def cited_by_source(conn):
    out = collections.defaultdict(set)
    for sid, sr in conn.execute(
            "select source_id, source_record from claim "
            "where source_id is not null and source_record is not null "
            "group by source_id, source_record"):
        out[sid].add(sr.split("#", 1)[1] if "#" in sr else sr)
    return out


def run(decl=None, cited=None, roots=None, quiet=False):
    fails, rows, notcov = [], [], []
    d = decl if decl is not None else json.load(open(DECL))
    fs = {k: v for k, v in (d.get("file_shaped") or {}).items() if not k.startswith("_")}
    nfs_spec = {k: v for k, v in (d.get("not_file_shaped") or {}).items()
                if not k.startswith("_")}
    nfs = set(nfs_spec)
    # ---- a not-file-shaped entry must say which of its parts ARE enumerable
    silent = sorted(k for k, v in nfs_spec.items()
                    if not isinstance(v, dict) or "enumerable_parts" not in v)
    if silent:
        fails.append(
            f"{len(silent):,} of {len(nfs_spec):,} not-file-shaped sources declare no "
            "`enumerable_parts` -- an absent list cannot be told apart from nobody "
            f"having looked: {', '.join(silent[:6])}"
            + (f" ... +{len(silent)-6} more" if len(silent) > 6 else ""))
    if cited is None:
        cited = cited_by_source(sqlite3.connect(paths.READ_MODEL))
    root = roots or SOURCES
    if not fs:
        fails.append("no file-shaped source is declared -- the gate would pass over "
                     "nothing, which is not a pass")
    # ---- every source with claims must be in one list or the other
    for sid in sorted(cited):
        if sid not in fs and sid not in nfs:
            fails.append(f"source {sid!r} has claims and is declared NEITHER file-shaped "
                         "nor not-file-shaped -- silence is not an exemption")
    # ---- the file-shaped ones are checked
    checked = 0
    for sid, spec in sorted(fs.items()):
        base = os.path.join(root, spec["dir"])
        if not os.path.isdir(base):
            fails.append(f"{sid}: declared directory {spec['dir']!r} is not on disk")
            continue
        acquired = set()
        for pat in spec.get("include") or ["*"]:
            for p in glob.glob(os.path.join(base, "**", pat), recursive=True):
                if os.path.isfile(p): acquired.add(os.path.basename(p))
        if not acquired:
            fails.append(f"{sid}: no acquired file found under {spec['dir']!r} -- an empty "
                         "denominator, refused rather than passed over")
            continue
        checked += 1
        how = spec.get("locator_to_file", "basename")
        seen = {to_file(x, how) for x in cited.get(sid, set())}
        unread = sorted(acquired - seen)
        undeclared = [f for f in unread
                      if not any(fnmatch.fnmatch(f, r["glob"])
                                 for r in (spec.get("declared_unread") or []))]
        rows.append({"source": sid, "acquired": len(acquired), "cited": len(acquired) - len(unread),
                     "unread": len(unread), "undeclared": len(undeclared),
                     "examples": undeclared[:5]})
        if undeclared:
            fails.append(f"{sid}: {len(undeclared):,} acquired files produce no claim and "
                         f"are explained by no declaration (of {len(acquired):,} acquired)")
    for sid in sorted(nfs):
        spec = nfs_spec[sid] or {}
        parts = spec.get("enumerable_parts")
        notcov.append({"source": sid, "why": spec.get("why_no_denominator", ""),
                       "enumerable_parts": len(parts) if isinstance(parts, list)
                                           else ("declared" if parts else None)})
    if not checked:
        fails.append("no file-shaped source could be checked -- nothing was measured, "
                     "which is not a clean sheet")
    out = {"_rests_on": d.get("_what_it_rests_on"), "file_shaped": rows,
           "not_covered_declared": notcov, "fails": fails}
    if not quiet:
        print(f"{'source':26s} {'acquired':>9} {'cited':>7} {'unread':>7} {'UNDECLARED':>11}")
        for r in rows:
            print(f"{r['source']:26s} {r['acquired']:>9,} {r['cited']:>7,} {r['unread']:>7,} {r['undeclared']:>11,}")
        print(f"\nNOT COVERED, declared with a reason ({len(notcov)}):")
        for r in notcov:
            p = r["enumerable_parts"]
            print(f"   {r['source']:48s}"
                  + (f"{p} enumerable parts" if isinstance(p, int)
                     else "NO enumerable_parts declared"))
        if decl is None: json.dump(out, open(REPORT, "w"), indent=1)
    return fails, out


def selftest():
    import tempfile
    ok = True
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "s"), exist_ok=True)
    for n in ("a.txt", "b.txt", "c.txt"):
        open(os.path.join(d, "s", n), "w").write("x")
    base = {"file_shaped": {"S": {"dir": "s", "locator_to_file": "basename",
                                  "include": ["*.txt"], "declared_unread": []}},
            "not_file_shaped": {}}
    cases = [
      (base, {"S": {"a.txt"}}, True,  "two acquired files nothing cites and nothing declares"),
      ({"file_shaped": {"S": {**base["file_shaped"]["S"],
        "declared_unread": [{"glob": "*.txt", "reason": "declared"}]}}, "not_file_shaped": {}},
       {"S": {"a.txt"}}, False, "the same two, declared with a reason"),
      (base, {"S": {"a.txt", "b.txt", "c.txt"}}, False, "everything cited"),
      (base, {"S": {"a.txt"}, "OTHER": {"z"}}, True, "a source in neither list is refused"),
      ({"file_shaped": {}, "not_file_shaped": {}}, {"S": {"a"}}, True,
       "zero declared file-shaped sources is refused, not passed over"),
      ({"file_shaped": {"S": {"dir": "empty", "include": ["*.txt"], "declared_unread": []}},
        "not_file_shaped": {}}, {"S": set()}, True, "a directory that is not there is refused"),
      # the enumerable-parts property, failing first against the shape the
      # declaration had BEFORE this gate existed
      ({"file_shaped": {"S": {**base["file_shaped"]["S"],
        "declared_unread": [{"glob": "*.txt", "reason": "d"}]}},
        "not_file_shaped": {"N": {"unit": "a URL", "why_no_denominator": "no list kept"}}},
       {"S": {"a.txt"}, "N": {"x"}}, True,
       "a not-file-shaped entry with a reason but NO enumerable_parts (the old shape)"),
      ({"file_shaped": {"S": {**base["file_shaped"]["S"],
        "declared_unread": [{"glob": "*.txt", "reason": "d"}]}},
        "not_file_shaped": {"N": {"unit": "a URL", "why_no_denominator": "no list kept",
                                  "enumerable_parts": [{"part": "drafts", "exists": 203}]}}},
       {"S": {"a.txt"}, "N": {"x"}}, False,
       "the same entry once it names one enumerable part"),
      ({"file_shaped": {"S": {**base["file_shaped"]["S"],
        "declared_unread": [{"glob": "*.txt", "reason": "d"}]}},
        "not_file_shaped": {"N": {"unit": "a URL", "why_no_denominator": "no list kept",
                                  "enumerable_parts": [{"part": "whole", "exists": "unknown"}]}}},
       {"S": {"a.txt"}, "N": {"x"}}, False,
       "`unknown` is a permitted answer -- only silence is refused"),
    ]
    for dec, cit, want, why in cases:
        f, _ = run(decl=dec, cited=cit, roots=d, quiet=True)
        got = bool(f)
        print(f"  {'PASS' if got == want else 'FAIL'}  {'refuses' if got else 'accepts':8s} {why}")
        ok &= got == want
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv: raise SystemExit(0 if selftest() else 1)
    print("SELF-TEST first -- the gate must be seen to fail:")
    if not selftest(): raise SystemExit("self-test failed; the gate's verdict means nothing")
    print()
    fails, _ = run()
    print()
    if fails:
        print("SOURCE COVERAGE GATE: FAIL")
        for x in fails[:12]: print("   -", x)
        if len(fails) > 12: print(f"   ... {len(fails)-12} more")
        raise SystemExit(1)
    print("SOURCE COVERAGE GATE: pass")
