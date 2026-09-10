"""The five hunting documents: what was taken, and what was refused on purpose.

Three properties, and the third is the one worth having.

  H1  NO CLUB-SEASON PLACEMENT RESTS ON AN ARCHIVE-WIDE NAME. A stint claim may be
      joined by an exact name on that club-season or by a surname on it, and never
      by "exact and unique in the archive" -- which would put a man on a club-season
      no source places him on because his name is unusual. The first run of
      ingest_pfr_pages.py did exactly that: 18 of the 1934 Reds joined against a
      club-season the archive holds 12 men on.
  H2  NOTHING IS PROMOTED. Every man a page names whom the archive does not hold is
      a LEAD. Admitting a person is its own act with its own route.
  H3  WHAT A SOURCE DOUBTS IS NOT HELD, and the refusal is recorded. Wikipedia calls
      the NFL-founding and Milwaukee-ownership claims unverified in its own words;
      both must be absent from the claims and present in the refusals. A refusal
      nobody wrote down is indistinguishable from not having read the sentence.

    python3 src/gate_hunting_ingests.py [--selftest]
"""
import os, sys, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

FAILS = []
STORES = ("pfr-pages.json", "wikipedia-plunkett.json", "troan-experience.json")


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def audit(stores, on_club):
    """-> findings. `on_club[(club_str, year)]` is the set of person ids the archive
    holds there; a stint claim outside it must say a surname placed it."""
    f = []
    for name, d in stores.items():
        for c in d.get("claims", []):
            s = c.get("subject") or []
            if s and s[0] == "stint" and len(s) >= 4:
                pid, club, key = s[1], s[2], str(s[3])
                yr = key.split("-")[-1]
                held = on_club.get((club, yr), set())
                if pid not in held:
                    f.append({"H1": "a stint claim on a club-season the archive does not hold the man on",
                              "store": name, "person": pid, "club": club, "season": key,
                              "joined_on": c.get("_joined_on")})
                if c.get("_joined_on") == "exact and unique in the archive":
                    f.append({"H1": "a stint claim joined archive-wide", "store": name,
                              "person": pid, "club": club, "season": key})
        for lead in d.get("leads", []):
            if lead.get("person"):
                f.append({"H2": "a lead carries a person id -- that is a promotion", "store": name,
                          "name": lead.get("name_as_printed")})
    w = stores.get("wikipedia-plunkett.json") or {}
    txt = json.dumps(w.get("claims", []))
    for phrase in ("found the National Football League", "Milwaukee"):
        if phrase in txt:
            f.append({"H3": "a claim the article calls unverified was written", "phrase": phrase})
    refused = json.dumps(w.get("refused", []))
    for phrase in ("found the National Football League", "Milwaukee"):
        if w and phrase not in refused:
            f.append({"H3": "an unverified claim was neither written NOR recorded as refused", "phrase": phrase})
    return f


def main(argv):
    if "--selftest" in argv: return selftest()
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    on_club = {}
    for r in conn.execute("SELECT DISTINCT club_str, year, person FROM claim WHERE scope='stint' AND person IS NOT NULL"):
        on_club.setdefault((r[0], str(r[1])), set()).add(r[2])
    stores = {}
    for s in STORES:
        p = os.path.join(BASE, "build", s)
        if os.path.exists(p): stores[s] = json.load(open(p))
    print(f"HUNTING INGESTS  ({len(stores)} of {len(STORES)} stores present)")
    for s, d in stores.items():
        print(f"  {s:<28}{len(d.get('claims', [])):>4} claims  {len(d.get('leads', [])):>3} leads  "
              f"{len(d.get('refused', []) or d.get('notes', [])):>3} refusals/notes")
    f = audit(stores, on_club)
    for prop, label in (("H1", "no club-season placement rests on an archive-wide name"),
                        ("H2", "nothing is promoted; every unheld man is a lead"),
                        ("H3", "what the source doubts is refused, and the refusal is recorded")):
        bad = [x for x in f if prop in x]
        check(not bad, f"{prop} {label}" + ("" if not bad else f": {len(bad)} — {json.dumps(bad[:2])}"))
    if FAILS:
        print(f"\nHUNTING INGEST GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nHUNTING INGEST GATE: pass"); return 0


def selftest():
    on_club = {("CIN", "1934"): {"P_1"}}
    good = {"a.json": {"claims": [{"subject": ["stint", "P_1", "CIN", "NFL-1934"], "_joined_on": "exact name on the club-season"}], "leads": [{"name_as_printed": "X"}]},
            "wikipedia-plunkett.json": {"claims": [{"predicate": "wikipedia.full_name", "value": "Joseph T. Plunkett"}],
                                         "refused": [{"not_held": "helping to found the National Football League"},
                                                     {"not_held": "owning the NFL's original football club in Milwaukee"}]}}
    cases = [("the ingests as ruled", good, 0)]
    bad1 = json.loads(json.dumps(good)); bad1["a.json"]["claims"][0]["subject"][1] = "P_2"
    cases.append(("a stint on a club-season the man is not held on", bad1, 1))
    bad2 = json.loads(json.dumps(good)); bad2["a.json"]["claims"][0]["_joined_on"] = "exact and unique in the archive"
    cases.append(("joined archive-wide", bad2, 1))
    bad3 = json.loads(json.dumps(good)); bad3["a.json"]["leads"][0]["person"] = "P_9"
    cases.append(("a lead that is really a promotion", bad3, 1))
    bad4 = json.loads(json.dumps(good))
    bad4["wikipedia-plunkett.json"]["claims"].append({"predicate": "wikipedia.note", "value": "helped found the National Football League"})
    cases.append(("an unverified claim written", bad4, 1))
    bad5 = json.loads(json.dumps(good)); bad5["wikipedia-plunkett.json"]["refused"] = []
    cases.append(("an unverified claim neither written nor refused", bad5, 2))
    ok = True
    for label, st, want in cases:
        got = len(audit(st, on_club)); good_ = got == want; ok &= good_
        print(f"  {'ok  ' if good_ else 'FAIL'} {label}: expected {want}, got {got}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
