"""Replace held photographs with larger, clean-licensed ones from Wikipedia.

THE RULE THIS IMPLEMENTS, and it is a change. Until 2026-09-07 the photograph sweeps
were GAP-FILL ONLY: a man who held anything was skipped, uncompared. Measured, that
kept a 70x90 video-game-mod thumbnail over a clean-licensed photograph 2,329 times.
Ryan ruled the rule out on 2026-09-07. It is replaced by NEVER SHRINK -- see
declarations/wikipedia.json PHOTOGRAPHS.REPLACEMENT, which this file reads rather
than restates.

FOUR REFUSALS, each enforced at the write and each counted:

  FAIR USE. Inexpressible, as before. There is no path to a claim.
  LICENCE NOT RECOGNISED FREE. Held for a ruling, never ingested.
  HELD SIZE UNKNOWN. A replacement that cannot be SHOWN to be larger has not been
    shown to be a gain. The 190 people holding the older wikipedia.json ingest have
    a filename and no file, so they are refused -- not waved through on the
    assumption that anything beats a thumbnail.
  NOT LARGER. The candidate's shorter side must strictly exceed the held one's.

THE SIZE ON THE CLAIM IS MEASURED FROM THE FILE, NOT THE API. The API's size chooses
candidates; the downloaded file's own header is what gets written. Two of the 432
downloaded on 2026-09-07 disagreed with the API, which is why the check exists. A
candidate that loses its margin once measured is REFUSED after the download, not
written on the strength of the number that picked it.

WHAT IS NOT WRITTEN, DELIBERATELY. No usability verdict. The dimensions are recorded
and `portrait_usability` is recorded as unassessed, because the usable quantity in a
portrait is the face region and this measures the file. A 447px full-length 1918
photograph with a 60px face is worse than a clean 240px headshot, and nothing
downstream may read the size as a promise. PHOTOGRAPHS.MEASURED_NOT_PROMISED.

NOTHING IS DELETED. The superseded claim stays exactly where it is, in a build file
this run does not own. The new claim names it in `supersedes`.

  python3 src/ingest_wikipedia_photo_replacements.py            decide only, no network
  python3 src/ingest_wikipedia_photo_replacements.py --download --write
"""
import os, re, sys, json, time, glob, struct, collections, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO
from measure_held_photographs import dims, san
from wiki_api import ssl_context

DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
PH = DECL["PHOTOGRAPHS"]; REP = PH["REPLACEMENT"]; MEAS = PH["MEASURED_NOT_PROMISED"]
RIGHTS = PH["RIGHTS_SUPERSEDES_RIGHTS_UNKNOWN"]
RIGHTS_MARK = RIGHTS["recorded_on_the_claim_as"]        # "superseded_on"
OK_LICENCE = re.compile(PH["licence_allow_pattern"], re.I)
FAIR_USE = re.compile(PH["licence_refuse_pattern"], re.I)
PD = re.compile(r"public domain|^pd\b|^pd-", re.I)
FREE_OTHER = re.compile(r"^no restrictions$|^gfdl$", re.I)
NO_ATTRIBUTION = re.compile(r"public domain|^pd\b|^pd-|cc0|^no restrictions$", re.I)
COMPARE_ON = REP["compare_on"]            # "shorter_side_px"
STRICTLY_LARGER = REP["strictly_larger"]
IMAGES = os.path.join(BASE, "build", "photographs", "wikipedia")
OUT_NAME = "wikipedia-photos-replacements.json"
OUT = os.path.join(BASE, "build", OUT_NAME)
SIZES = os.path.join(BASE, "build-reports", "wikipedia-photo-sizes.json")
HELD = os.path.join(BASE, "build-reports", "held-photographs.json")
UA = {"User-Agent": "pgm3-archive-research/1.0 (NFL historical roster research; contact: ryannecci@gmail.com)"}
SPACING = 3.0        # measured 2026-09-07: 1/s earned HTTP 429 on 250 of 432
BACKOFF = 20


class IngestError(Exception):
    pass


def licence_family(L):
    if PD.search(L): return "public-domain"
    if FREE_OTHER.search(L): return "free-other"
    return "open-cc"


def shorter(w, h):
    return min(w, h) if w and h else None


def decide():
    """Who gains, on the API's sizes. No network, no writes."""
    S = json.load(open(SIZES)); H = json.load(open(HELD))["held"]
    cand, images = S["candidates"], S["images"]
    win, ref = {}, collections.defaultdict(list)
    n = collections.Counter()
    for pid, c in cand.items():
        img = c["image"]; meta = images.get(img)
        held = H.get(pid)
        if not meta or not meta.get("w"):
            ref["candidate_size_unknown"].append({"person": pid, "image": img}); n["candidate_size_unknown"] += 1; continue
        L = meta.get("licence") or ""
        if FAIR_USE.search(L):
            ref["fair_use"].append({"person": pid, "image": img, "licence": L}); n["refused_fair_use"] += 1; continue
        if not OK_LICENCE.search(L):
            ref["unrecognised_licence"].append({"person": pid, "image": img, "licence": L}); n["refused_unrecognised_licence"] += 1; continue
        if not held:
            ref["holds_nothing"].append({"person": pid, "image": img}); n["holds_nothing"] += 1; continue
        cs = shorter(meta["w"], meta["h"])
        hs = held.get("shorter_side")
        if held.get("rights") == "unknown":
            # RIGHTS_SUPERSEDES_RIGHTS_UNKNOWN. A rights-clear image supersedes a
            # rights-unknown one on rights alone. Size is not consulted, and this is
            # NOT an exception to never-shrink -- the two rules cover disjoint pairs.
            on = "rights"; n["superseded_on_rights"] += 1
        else:
            # NEVER SHRINK, between two images the archive may both publish.
            if not held.get("measurable"):
                ref["held_size_unknown"].append({"person": pid, "image": img, "held_in": held["held_in"],
                                                 "held_value": held["value"], "_why": held.get("why")})
                n["refused_held_size_unknown"] += 1; continue
            if not (cs > hs if STRICTLY_LARGER else cs >= hs):
                ref["not_larger"].append({"person": pid, "image": img, "held_px": hs, "candidate_px": cs})
                n["refused_not_larger"] += 1; continue
            on = "size"; n["superseded_on_size"] += 1
        win[pid] = {"title": c["title"], "image": img, "url": meta["url"], "licence": L,
                    "superseded_on": on, "held_rights": held.get("rights"),
                    "held_licence": held.get("licence"),
                    "api_w": meta["w"], "api_h": meta["h"], "api_shorter": cs,
                    "held_shorter": hs, "held_in": held["held_in"], "held_value": held["value"],
                    "artist": meta.get("artist"), "credit": meta.get("credit"),
                    "date_original": meta.get("date_original"), "licence_url": meta.get("licence_url")}
        n["would_gain"] += 1
    return win, ref, n


def download(win, log=print):
    """One request per 3s, backing off on 429. Reuses anything already on disk."""
    os.makedirs(IMAGES, exist_ok=True)
    have = collections.defaultdict(list)
    for f in sorted(os.listdir(IMAGES)):
        _, _, rest = f.partition("_"); have[rest].append(f)
    ctx = ssl_context()          # verifying; see wiki_api.ssl_context
    last, got, fail = [0.0], {}, []
    for i, (pid, w) in enumerate(sorted(win.items()), 1):
        key = san(w["image"])
        if len(have.get(key, [])) == 1:
            got[pid] = have[key][0]; continue
        fn = f"r{i:05d}_{key}"; p = os.path.join(IMAGES, fn)
        data = None
        for attempt in range(4):
            wait = SPACING - (time.time() - last[0])
            if wait > 0: time.sleep(wait)
            last[0] = time.time()
            try:
                with urllib.request.urlopen(urllib.request.Request(w["url"], headers=UA),
                                            timeout=120, context=ctx) as r:
                    if r.status != 200: raise IOError(f"HTTP {r.status}")
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(BACKOFF * (attempt + 1)); continue
                fail.append((pid, w["image"], f"HTTP {e.code}")); break
            except Exception as e:
                fail.append((pid, w["image"], f"{type(e).__name__}: {str(e)[:60]}")); break
        if not data:
            if not any(f[0] == pid for f in fail): fail.append((pid, w["image"], "no data"))
            continue
        tmp = p + ".part"; open(tmp, "wb").write(data); os.replace(tmp, p)
        got[pid] = fn; have[key] = [fn]
        if i % 50 == 0: log(f"  {i}/{len(win)} downloaded {len(got)} failed {len(fail)}", flush=True)
    return got, fail


def main():
    do_dl = "--download" in sys.argv; write = "--write" in sys.argv
    win, ref, n = decide()
    for k, v in sorted(n.items()): print(f"  {k:32s} {v}")
    print(f"\n  would gain a larger image: {len(win)}")
    if win:
        g = sorted(w["api_shorter"] for w in win.values())
        print(f"  candidate shorter side: median {g[len(g)//2]}  >=200 {sum(1 for x in g if x>=200)}  >=400 {sum(1 for x in g if x>=400)}")
    if not do_dl:
        print("\n(decision only -- no image fetched, nothing written. --download --write to ingest)")
        return {"win": win, "refused": ref, "counts": dict(n)}

    got, fail = download(win)
    print(f"\ndownloaded/reused {len(got)}  failed {len(fail)}")
    claims, dens, measured_out = [], [], {}
    shrank, unreadable = [], []
    for pid, w in sorted(win.items()):
        fn = got.get(pid)
        if not fn: continue
        p = os.path.join(IMAGES, fn); d = dims(p)
        if not d:
            # A downloaded file whose dimensions cannot be read is NOT a quiet skip.
            # It was landing in download_failures and being dropped with no error --
            # the same shape that cost the bios 30,503 claims. Collected here and
            # made fatal below. See gate_photographs_measurable.py.
            unreadable.append({"person": pid, "image": w["image"], "file": fn,
                               "bytes": os.path.getsize(p),
                               "magic": open(p, "rb").read(12).hex()})
            continue
        mw, mh, fmt = d; ms = shorter(mw, mh)
        # the margin must survive being MEASURED, not merely predicted
        if w["superseded_on"] == "size" and not (
                ms > w["held_shorter"] if STRICTLY_LARGER else ms >= w["held_shorter"]):
            shrank.append({"person": pid, "image": w["image"], "held_px": w["held_shorter"],
                           "api_px": w["api_shorter"], "measured_px": ms,
                           "_why": "the API's size picked it; the file's own header does not support it"})
            continue
        L = w["licence"]; sr = f"wikipedia-en#{w['title']}"
        meas = {"width_px": mw, "height_px": mh, "shorter_side_px": ms,
                "bytes": os.path.getsize(p), "format": fmt,
                "measured_from": MEAS["measured_from"],
                "api_said": {"width_px": w["api_w"], "height_px": w["api_h"]},
                "agrees_with_api": (mw, mh) == (w["api_w"], w["api_h"])}
        claims.append({
            "source_record": sr, "source_id": "wikipedia-en", "stated_by": "English Wikipedia",
            "attribution": ["English Wikipedia"] + ([w["artist"]] if w.get("artist") else []),
            "subject": ["person", pid], "predicate": "wikipedia.photograph", "value": w["image"],
            "licence": L, "licence_family": licence_family(L),
            "attribution_required": not bool(NO_ATTRIBUTION.search(L)),
            "licence_url": w.get("licence_url"), "artist": w.get("artist"),
            "credit": w.get("credit"), "date_original": w.get("date_original"),
            "evidence_tier": "club-named", "file": os.path.join("build/photographs/wikipedia", fn),
            "image_measured": meas,
            "portrait_usability": MEAS["portrait_usability"],
            "_portrait_usability_why": MEAS["_why_unassessed"],
            "supersedes": {"held_in": w["held_in"], "value": w["held_value"],
                           "held_shorter_side_px": w["held_shorter"],
                           "held_rights": w["held_rights"], "held_licence": w["held_licence"],
                           RIGHTS_MARK: w["superseded_on"],
                           "_rule": (RIGHTS["rule"] if w["superseded_on"] == "rights" else PH["rule"]),
                           "_kept": REP["held_claim_is_kept"]},
            "kind": "observed", "observed_at": "fetched-2026-09-07",
            "note": (f"licence: {L}; supersedes a rights-unknown image on rights"
                     if w["superseded_on"] == "rights" else
                     f"licence: {L}; replaces a {w['held_shorter']}px image with a {ms}px one")})
        dens.append({"person": pid, "source_record": sr, "method": "article-subject+club-named",
                     "evidence_tier": "club-named",
                     "discriminator": ["article_subject", "already_denoted_by_an_earlier_sweep"],
                     "matched_against": f"wikipedia-en:{w['title']}", "status": "asserted",
                     "note": "the person-to-article denotation is the earlier sweep's, unchanged. "
                             "This run re-uses it and decides only which IMAGE is larger."})
        measured_out[pid] = meas
    if unreadable:
        # Loud, and it names every one. A format this reader does not know is a gap in
        # the reader, not data to discard: fix dims() and run again.
        for u in unreadable:
            print(f"  UNREADABLE {u['file']}  {u['bytes']} bytes  magic {u['magic']}")
        raise SystemExit(
            f"ingest_wikipedia_photo_replacements: {len(unreadable)} downloaded file(s) whose "
            f"dimensions cannot be read. Refusing to write a build that silently drops them. "
            f"Teach measure_held_photographs.dims() the format and re-run.")
    doc = {
        "source": {"source_id": "wikipedia-en", "name": "English Wikipedia", "acquisition": "fetched",
                   "stated_by": "English Wikipedia",
                   "licence": "CC BY-SA; reuse permitted with attribution",
                   "scope": "photographs for people ALREADY holding one, where the Wikipedia image "
                            "is larger on the shorter side",
                   "_touches_no_game_file": "writes dataset/build/ only",
                   "_deletes_nothing": REP["held_claim_is_kept"]},
        "run": {"date": "2026-09-07", "session": "Fetching",
                "ruling_applied": PH["_RULING_2026_09_07_gap_fill_dropped"],
                "declaration": "declarations/wikipedia.json PHOTOGRAPHS.REPLACEMENT"},
        "claims": claims, "denotations": dens,
        "refused": {k: v for k, v in ref.items()},
        "refused_after_measuring": shrank,
        "download_failures": fail,
        "unreadable_after_download": unreadable,     # must be empty; the run refuses otherwise
        "never_shrink_proof": {
            "claims": len(claims),
            "on_size": sum(1 for c in claims if c["supersedes"][RIGHTS_MARK] == "size"),
            "on_rights": sum(1 for c in claims if c["supersedes"][RIGHTS_MARK] == "rights"),
            "every_claim_strictly_larger": all(
                c["image_measured"]["shorter_side_px"] > c["supersedes"]["held_shorter_side_px"]
                for c in claims if c["supersedes"][RIGHTS_MARK] == "size"),
            "smallest_margin_px": min((c["image_measured"]["shorter_side_px"] - c["supersedes"]["held_shorter_side_px"]
                                       for c in claims if c["supersedes"][RIGHTS_MARK] == "size"), default=None),
            "_on_size_means": "both images are rights-clear; the larger wins (NEVER SHRINK)",
            "_on_rights_means": RIGHTS["rule"],
            "refused_after_measuring": len(shrank),
            "_meaning": "every photograph written is larger than the one it supersedes, measured "
                        "from both files rather than from either API."},
        "counts": dict(n)}
    if write: IO.dump_atomic(doc, OUT, indent=1)
    p = doc["never_shrink_proof"]
    print(f"\n  claims {p['claims']}  all strictly larger: {p['every_claim_strictly_larger']}  "
          f"smallest margin {p['smallest_margin_px']}px  refused after measuring {p['refused_after_measuring']}")
    if write: print(f"wrote build/{OUT_NAME}")
    return doc


if __name__ == "__main__":
    main()
