"""Build the corpus census FRAME: one row per document on disk, with CONTENT-DERIVED
evidence attached. This script does not decide what a document is.

WHY A FRAME AND NOT A CLASSIFIER. The question "what do we have" has been answered
three times from titles, file counts and label patterns, and been wrong each time.
This file therefore records only what can be counted honestly -- bytes, which years
the text actually mentions, which sport's vocabulary it uses, how many lines take a
roster or statistics shape -- and leaves `class`, `per_player_content` and
`duplicate_of` EMPTY. Those columns are filled by reading, in census_readings.py,
and every row says which method filled it (`read` or `unread`).

A signal here is a sampling frame, never a verdict:
  - the eight Vietnam War novels scored zero football vocabulary and were still
    queued as pro football on their titles
  - the Eagles 1975 yearbook looked promising on every signal and was a strict
    subset of a press guide already held

  python3 src/census_frame.py [--limit N]
"""
import os, re, sys, csv, json, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
SRC = os.path.expanduser("~/Documents/pgm3-sources")
OUT = os.path.join(BASE, "build-reports", "corpus-census-frame.json")

# ---------------------------------------------------------------- vocabularies
FOOT = re.compile(r"\b(quarterback|touchdown|linebacker|fumble|yardage|gridiron|halfback|"
                  r"fullback|punt(?:er|ing)?|field goal|end zone|scrimmage|tailback|"
                  r"placekick\w*|kickoff|interception|first down|lineman|defensive back)\b", re.I)
BASE_B = re.compile(r"\b(pitcher|infield|batting average|shortstop|home runs?|innings?|"
                    r"outfielder|earned run|bullpen|shutouts?\s+\(baseball\))\b", re.I)
HOCK = re.compile(r"\b(goaltender|power play|slap ?shot|blue ?line|face-?off|penalty box|puck)\b", re.I)
BASK = re.compile(r"\b(free throw|rebounds?|three-point|jump shot|layup|backcourt|dunk)\b", re.I)
COLLEGE = re.compile(r"\b(freshman|sophomore|junior varsity|campus|alumni|homecoming|"
                     r"university of|fraternity|dean of|undergraduate)\b", re.I)

# structural shapes -- counted per line, never used alone to decide anything
RE_ROSTER_ROW = re.compile(r"^\s*\d{1,2}\s+[A-Z][A-Za-z'\-]+.{0,40}?\b(\d-\d{1,2}|\d{3})\b")
RE_NAME_POS   = re.compile(r"^\s*[A-Z][A-Za-z'\.\-]+,?\s+[A-Z][a-z][A-Za-z'\.\-]*\s*,?\s*"
                           r"\b(QB|RB|HB|FB|WR|TE|OT|OG|C|DT|DE|LB|CB|S|K|P|T|G|E|B|DB|LH|RH|QB-K)\b")
RE_STAT_HEAD  = re.compile(r"\b(Att\.?\s+Comp|Rushing\s+Att|TC\s+YG|No\.?\s+Yds\.?\s+Avg|"
                           r"PA\s+PC\s+PI|Att\s+Yds\s+Avg\s+TD|G\s+GS\s+)", re.I)
RE_STAT_ROW   = re.compile(r"^[ \t]*[A-Z][A-Za-z'.\-]{2,}[A-Za-z '.,\-]{0,30}(?:[ \t]+-?\d+(?:\.\d+)?){4,}[ \t]*$")
RE_BIO_LABEL  = re.compile(r"^\s*(PERSONAL|COLLEGE|PRO|HIGH SCHOOL|BORN|CAREER|HONORS|"
                           r"NICKNAME|RESIDENCE|FAMILY|HOBBIES)\s*[:.—–-]", re.I | re.M)
RE_BIO_PROSE  = re.compile(r"\b(was born|born in|attended|played (?:his|for) |lettered|"
                           r"comes to the|a native of|majoring in|prior to joining|"
                           r"married|graduated from)\b", re.I)
RE_HTWT       = re.compile(r"\b(Ht\.|Wt\.|Hgt\.|Height|Weight)\b")
RE_YEAR       = re.compile(r"\b(18[5-9]\d|19\d\d|20[0-2]\d)\b")


def evidence(text):
    """Everything countable about one text. No verdicts."""
    lines = [l[:400] for l in text.split("\n")]
    years = collections.Counter(int(y) for y in RE_YEAR.findall(text))
    ev = {
        "bytes": len(text.encode("utf-8", "ignore")),
        "lines": len(lines),
        "words": len(text.split()),
        "v_football": len(FOOT.findall(text)),
        "v_baseball": len(BASE_B.findall(text)),
        "v_hockey": len(HOCK.findall(text)),
        "v_basketball": len(BASK.findall(text)),
        "v_college": len(COLLEGE.findall(text)),
        "n_roster_rows": sum(1 for l in lines if RE_ROSTER_ROW.match(l)),
        "n_name_pos": sum(1 for l in lines if RE_NAME_POS.match(l)),
        "n_stat_heads": len(RE_STAT_HEAD.findall(text)),
        "n_stat_rows": sum(1 for l in lines if RE_STAT_ROW.match(l)),
        "n_bio_labels": len(RE_BIO_LABEL.findall(text)),
        "n_bio_prose": len(RE_BIO_PROSE.findall(text)),
        "n_htwt": len(RE_HTWT.findall(text)),
        "years_top": [[y, n] for y, n in years.most_common(6)],
        "year_span": [min(years), max(years)] if years else None,
        "sha1_16": hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:16],
    }
    return ev


def add(rows, **kw):
    r = {"doc_id": None, "stratum": None, "path": None, "title_as_filed": "",
         "year_as_filed": None, "has_text": False, "format": "",
         # filled by reading, never by a signal:
         "class": None, "club": None, "league": None, "year_read": None,
         "per_player_content": None, "duplicate_of": None, "method": "unread",
         "note": ""}
    r.update(kw); rows.append(r); return r


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    rows = []

    # ---- stratum: nfl-books (the guide corpus) -------------------------------
    nb = os.path.join(SRC, "nfl-books")
    idx = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(nb, "index.csv")))}
    ta = os.path.join(nb, "text_all")
    on_disk = set(os.listdir(ta))
    seen = set()
    for ident, r in idx.items():
        f = ident + ".txt"
        has = f in on_disk
        add(rows, doc_id=ident, stratum="nfl-books", path=f"nfl-books/text_all/{f}" if has else "",
            title_as_filed=r.get("title", ""), year_as_filed=r.get("year") or None,
            has_text=has, format="ocr-text" if has else "no-text-layer",
            note="" if has else "textless scan; in index, no OCR layer")
        seen.add(f)
    for f in sorted(on_disk):
        if not f.endswith(".txt") or f in seen: continue
        add(rows, doc_id=f[:-4], stratum="nfl-books-excluded", path=f"nfl-books/text_all/{f}",
            has_text=True, format="ocr-text",
            note="on disk, deliberately NOT in index.csv (sport collision or no football evidence)")

    # ---- stratum: college-pre1950 -------------------------------------------
    cp = os.path.join(SRC, "college-pre1950")
    inv = {}
    p = os.path.join(cp, "inventory.json")
    if os.path.exists(p):
        try:
            j = json.load(open(p))
            items = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
            for it in items:
                if isinstance(it, dict) and it.get("identifier"): inv[it["identifier"]] = it
        except Exception: pass
    for sub in ("text", "text_container"):
        d = os.path.join(cp, sub)
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt"): continue
            ident = f[:-4]
            m = inv.get(ident, {})
            add(rows, doc_id=ident, stratum="college-pre1950", path=f"college-pre1950/{sub}/{f}",
                title_as_filed=m.get("title", ""), year_as_filed=m.get("year"),
                has_text=True, format="ocr-text",
                note="from inside a container item" if sub == "text_container" else "")

    # ---- stratum: eBay game programmes (images only, no OCR) -----------------
    pg = os.path.join(SRC, "programs")
    if os.path.isdir(pg):
        for name in sorted(os.listdir(pg)):
            d = os.path.join(pg, name)
            if not os.path.isdir(d): continue
            imgs, zips = [], []
            for root, _, fs in os.walk(d):
                for f in fs:
                    if f.lower().endswith((".jpg", ".jpeg", ".webp", ".png")): imgs.append(os.path.join(root, f))
                    elif f.lower().endswith(".zip"): zips.append(os.path.join(root, f))
            n_zip = 0
            for z in zips:
                try:
                    import zipfile
                    n_zip += len([x for x in zipfile.ZipFile(z).namelist() if x.lower().endswith((".jpg", ".jpeg", ".webp", ".png"))])
                except Exception: pass
            y = re.match(r"^(19\d\d|20\d\d)", name)
            add(rows, doc_id="prog:" + name[:70], stratum="programs", path=f"programs/{name}",
                title_as_filed=name, year_as_filed=y.group(1) if y else None,
                has_text=False, format="photographs",
                note=f"{len(imgs)} loose images + {n_zip} in zip; eBay listing photographs, no OCR layer")

    # ---- small strata --------------------------------------------------------
    for stratum, sub, exts in (("pfr-pages", "PFR PAGES", (".html",)),
                               ("reference-books", "Reference Books", (".pdf", ".epub")),
                               ("legal-docdump", "DocDump", (".pdf", ".html", ".txt")),
                               ("hearings", "hearings", (".pdf", ".txt")),
                               ("antitrust", "Antitrust Docs", (".pdf", ".epub")),
                               ("crs", "crs", (".pdf", ".txt")),
                               ("guide-images", "guide_images", (".zip",))):
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d): continue
        for root, _, fs in os.walk(d):
            for f in sorted(fs):
                if not f.lower().endswith(exts): continue
                rel = os.path.relpath(os.path.join(root, f), SRC)
                add(rows, doc_id=f"{stratum}:{f[:80]}", stratum=stratum, path=rel,
                    title_as_filed=f, has_text=f.lower().endswith(".txt"),
                    format=f.rsplit(".", 1)[-1].lower())

    # ---- attach evidence to everything that has text -------------------------
    n = 0
    for r in rows:
        if not r["has_text"] or not r["path"]: continue
        p = os.path.join(SRC, r["path"])
        if not os.path.exists(p): r["has_text"] = False; continue
        try: t = open(p, errors="ignore").read()
        except Exception: continue
        r["evidence"] = evidence(t)
        n += 1
        if n % 100 == 0: print(f"  {n} texts read", flush=True)
        if limit and n >= limit: break

    res = {"_date": "2026-09-07", "_note": "frame only; class/per_player_content/duplicate_of are filled by reading",
           "counts": dict(collections.Counter(r["stratum"] for r in rows)),
           "with_text": sum(1 for r in rows if r.get("evidence")), "rows": rows}
    IO.dump_atomic(res, OUT, indent=0)
    print(json.dumps({"documents": len(rows), "with_evidence": res["with_text"],
                      "strata": res["counts"]}, indent=1))


if __name__ == "__main__":
    main()
