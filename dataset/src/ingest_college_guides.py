"""Candidate records from pre-1950 COLLEGE guides, for men already in the archive.

NOT A SCOPE RULING. See declarations/college-guides.json. 110 of 6,238 men.

THREE RULES, ENFORCED AT THE WRITE:

  NOTHING HERE IS AN IDENTIFICATION. Records carry `candidate_person`, never
  `subject`, and the build has NO `claims` key. A consumer cannot mistake one for
  an observed fact about a person, because the shape it would look for is absent.

  A FIELD READ BY POSITION IS NOT WRITTEN. A value is written only when the man's
  name is on the SAME LINE and the value is identified by its OWN PATTERN -- a
  height reads 6-1, a weight is 140-259, a class is Soph./Jr./Sr., a hometown is
  'City, State'. AGE is refused outright: a bare two-digit number in an unlabelled
  table cannot be told from a jersey number by pattern. Wisconsin 1947 and 1948 are
  dropped for fields entirely -- their OCR puts the names in one block and the data
  in another, so any join would be positional.

  PROSE STAYS WHOLE. Captured verbatim from its header to the next, attributed to
  its document, round-tripped against the source before it is written.

  python3 src/ingest_college_guides.py [--write]
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write
SRC = os.path.expanduser("~/Documents/pgm3-sources/college-pre1950")
DECL = json.load(open(os.path.join(BASE, "declarations", "college-guides.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
DROP_FIELDS = {"Wisconsin_Football,_1947", "Wisconsin_Football,_1948"}
REFUSED_FIELDS = {"age"}

STATES = (r"Ala|Ariz|Ark|Cal|Calif|Colo|Conn|Del|Fla|Ga|Ida|Idaho|Ill|Ind|Iowa|Kan|Kans|Ky|La|"
          r"Me|Md|Mass|Mich|Minn|Miss|Mo|Mont|Neb|Nebr|Nev|N\.? ?H|N\.? ?J|N\.? ?M|N\.? ?Y|"
          r"N\.? ?C|N\.? ?D|Ohio|Okla|Ore|Oreg|Pa|Penn|R\.? ?I|S\.? ?C|S\.? ?D|Tenn|Tex|Utah|"
          r"Vt|Va|Wash|W\.? ?Va|Wis|Wisc|Wyo")
HT = re.compile(r"(?<![\d.])([4-7])\s?[-'’]\s?(\d{1,2})(?![\d])")
WT = re.compile(r"(?<![\d.])(1[4-9]\d|2[0-5]\d)(?![\d])")
CLS = re.compile(r"\b(Frosh|Freshman|Sophomore|Junior|Senior|Soph|Jun|Sen|Fr|Jr|Sr)\b\.?")
TOWN = re.compile(r"([A-Z][A-Za-z.'’ ]{2,22},\s*(?:" + STATES + r")\.?)(?![A-Za-z])")
POSVOC = {"TB","FB","HB","QB","BB","WB","LE","RE","LT","RT","LG","RG","QB","OT","DE","DT"}
POS = re.compile(r"\b(" + "|".join(sorted(POSVOC)) + r")\b")


class CandidateError(Exception):
    pass


def doc_path(doc):
    for p in (f"{SRC}/text/{doc}.txt", f"{SRC}/text_container/{doc}.txt"):
        if os.path.exists(p): return p
    return None


def unique(rx, line, group=0):
    """A value is written only when its pattern matches EXACTLY ONCE on the line.
    Two candidates mean the binding is ambiguous and nothing is written."""
    m = rx.findall(line)
    if len(m) != 1: return None
    g = m[0]
    return (g if isinstance(g, str) else "-".join(str(x) for x in g)).strip()


def fields_from_row(line, doc):
    """Every value here is found by its OWN pattern on the man's OWN line."""
    if doc in DROP_FIELDS:
        raise CandidateError(f"{doc}: columns cannot be bound structurally; fields refused")
    out = collections.OrderedDict()
    h = HT.findall(line)
    if len(h) == 1: out["Ht."] = f"{h[0][0]}-{h[0][1]}"
    w = unique(WT, line)
    if w: out["Wt."] = w
    c = unique(CLS, line)
    if c: out["Class"] = c
    t = unique(TOWN, line)
    if t: out["Home Town"] = t
    p = unique(POS, line)
    if p: out["Pos."] = p
    for k in list(out):
        if k.lower().rstrip(".") in REFUSED_FIELDS: del out[k]
    return out


def prose_block(L, i, name_last):
    """From the header line to the line before the next header, verbatim."""
    HDRX = re.compile(r"^\s*[A-Z][A-Za-z.'’]+(?:\s+[A-Z][A-Za-z.'’]+){0,3}\s*[—–]{1,2}|"
                      r"^\s*[A-Z][A-Z.'’ ]{4,30}[—–-]{1,3}")
    out = [L[i]]
    for k in range(i + 1, min(i + 40, len(L))):
        if HDRX.match(L[k]) and not re.search(re.escape(name_last), L[k], re.I): break
        out.append(L[k])
    while out and not out[-1].strip(): out.pop()
    return "\n".join(out)


def roundtrip(block, L):
    """Every non-empty stored line must be a source line, in order."""
    want = [x.strip() for x in block.split("\n") if x.strip()]
    have = [x.strip() for x in L]
    i = 0
    for w in want:
        while i < len(have) and have[i] != w: i += 1
        if i >= len(have): return False
        i += 1
    return True


def main():
    write = "--write" in sys.argv
    X = json.load(open(SRC + "/xref_strict.json"))
    INV = {x["identifier"]: x for x in json.load(open(SRC + "/inventory.json"))}
    cands = {}
    n = collections.Counter()
    dropped_docs = collections.Counter()
    for r in X:
        if not r["strict"]: continue
        p = doc_path(r["doc"])
        if not p:
            dropped_docs[r["doc"]] = "no text on disk"; continue
        L = [l.rstrip() for l in open(p, encoding="utf-8", errors="replace")]
        year = None
        m = re.search(r"(18|19)\d{2}", r["doc"])
        if m: year = int(m.group(0))
        for nm in r["names"]:
            parts = [x for x in re.sub(r"[^A-Za-z ]", " ", nm).split() if len(x) > 2]
            if len(parts) < 2: continue
            f, l = parts[0], parts[-1]
            pats = [re.compile(rf"\b{re.escape(f)}\s+{re.escape(l)}\b", re.I),
                    re.compile(rf"\b{re.escape(l)},\s*{re.escape(f)}\b", re.I)]
            best = None
            for i, x in enumerate(L):
                if not any(pt.search(x) for pt in pats): continue
                sig = sum([bool(HT.search(x)), bool(WT.search(x)),
                           bool(CLS.search(x)), bool(TOWN.search(x))])
                hdr = bool(re.match(rf"^\s*{re.escape(f)}\s+{re.escape(l)}\b\s*[—–,\-.]", x, re.I)
                           or re.match(rf"^\s*[A-Z][A-Z.'’ ]*{re.escape(l.upper())}\b\s*[—–,\-.]", x))
                body = sum(1 for k in range(i + 1, min(i + 6, len(L))) if len(L[k].strip()) > 30)
                kind = "roster_row" if sig >= 2 else ("prose_entry" if (hdr and body >= 2) else "mention_only")
                rank = {"roster_row": 3, "prose_entry": 2, "mention_only": 1}[kind]
                if best is None or rank > best[0]: best = (rank, kind, i, x)
            if not best:
                n["name_not_relocated"] += 1; continue
            _, kind, i, line = best
            rec = {"observation_kind": kind, "document": r["doc"], "institution": r["institution"],
                   "document_year": year, "line": i,
                   "verbatim_line": line.strip()}
            if kind == "roster_row":
                try:
                    fl = fields_from_row(line, r["doc"])
                    if fl:
                        rec["fields"] = fl; n["with_fields"] += 1
                        for k in fl: n["field:" + k] += 1
                    else:
                        rec["observation_kind"] = "mention_only"
                        n["row_yielded_no_provable_field"] += 1
                except CandidateError as e:
                    rec["observation_kind"] = "mention_only"
                    rec["fields_refused"] = str(e)
                    n["fields_refused_column_binding"] += 1
                    dropped_docs[r["doc"]] = "columns cannot be bound structurally"
            elif kind == "prose_entry":
                blk = prose_block(L, i, l)
                if roundtrip(blk, L):
                    rec["prose"] = blk; rec["prose_label"] = None
                    n["prose_blocks"] += 1
                else:
                    rec["observation_kind"] = "mention_only"
                    n["prose_roundtrip_failed_dropped"] += 1
            n["obs:" + rec["observation_kind"]] += 1
            c = cands.setdefault(nm, {
                "candidate_id": f"cand-cg-{len(cands)+1:04d}",
                "name_as_matched": nm, "candidate_person": None,
                "college": r["institution"],
                "IS_NOT_A_CONFIRMED_IDENTIFICATION": True,
                "match_test": "strict: forename+surname adjacent, and archive college == document institution",
                "promotion": "requires an explicit ruling; no code path does it",
                "observations": []})
            c["observations"].append(rec)
    # attach the archive person id as a CANDIDATE, from the cross-reference
    IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
    IDX.pop("_clubs", None)
    byname = collections.defaultdict(list)
    for pid, pp in IDX.items():
        if isinstance(pp, dict) and pp.get("name"):
            byname[re.sub(r"[^a-z]", "", pp["name"].lower())].append(pid)
    for nm, c in cands.items():
        hits = byname.get(re.sub(r"[^a-z]", "", nm.lower()), [])
        c["candidate_person"] = hits[0] if len(hits) == 1 else None
        c["candidate_person_ambiguous"] = len(hits) > 1
        if len(hits) > 1: n["candidate_person_ambiguous"] += 1
    doc = {"source": {"source_id": SRC_ID, "name": DECL["name"], "acquisition": DECL["acquisition"],
                      "stated_by": DECL["stated_by"],
                      "_source_class": DECL["SOURCE_CLASS"]["what"],
                      "_not_a_scope_ruling": DECL["_THIS_IS_NOT_A_SCOPE_RULING"]},
           "candidates": sorted(cands.values(), key=lambda c: c["name_as_matched"]),
           "documents_dropped_for_field_extraction": dict(dropped_docs),
           "refused_fields": sorted(REFUSED_FIELDS),
           "counts": dict(n)}
    if write:
        # ATOMIC. json.dump(open(path,"w")) streams into the REAL file, so a rebuild
        # reading it mid-write gets a truncated store. That cost Parsing a rebuild whose
        # P3 reported "person P_040746 vanished" and 300+ others: build_person_index
        # caught the parse error with `except Exception: continue` and skipped the whole
        # store in silence. dump_atomic writes a temp file, fsyncs, os.replaces.
        IO.dump_atomic(doc, os.path.join(BASE, "build", "college-guides-candidates.json"), indent=1)
    print(f"candidates: {len(doc['candidates'])}")
    for k in sorted(n): print(f"   {k:38s} {n[k]}")
    if write: print("\nwrote build/college-guides-candidates.json")
    return doc


if __name__ == "__main__":
    main()
