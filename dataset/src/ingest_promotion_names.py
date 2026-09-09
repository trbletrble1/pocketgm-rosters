"""Write the name a promotion decision recorded as a NAME CLAIM on the person it created.

Ryan's ruling, 2026-09-09. A promotion decision knows the man's name -- it is what the
route matched on and what it refused other candidates against -- and until now it kept
that name as metadata on the person record, where `search_people` cannot reach it. 1,794
people the archive itself created could not be found by their own names.

THE CLAIM CITES THE DECISION, like any other claim cites its source. The source record is
the decision store and the decision's own reference, so an un-promotion removes the name
with the person.

WHAT IS DELIBERATELY LEFT ALONE. 2,552 people are denoted only by a PFA slug --
`cost00470`, four letters of a surname and a serial. That is a stem and an identifier, not
a name, and reading it as one would be inventing a man's name from a filename. For those
the archive genuinely holds a code and no name, and it should keep saying so.

`forename_unknown` is untouched: it lives on the person record, set by
apply_promotions.py, and writing a name claim beside it does not contradict it -- a man
recorded as `Gorman` has a surname and no forename, and both facts stand.

  python3 src/ingest_promotion_names.py [--write]
"""
import os, sys, json, sqlite3, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

OUT = os.path.join(BASE, "build", "promotion-names.json")
STORES = [("coach-promotions.json", "coach-promotions",
           "coaches promoted from a PFA coach page or a media-guide staff list"),
          ("player-promotions.json", "player-promotions",
           "players promoted from a printed roster or a team-photograph caption")]

SOURCE = {
    "source_id": "promotion-decisions",
    "name": "The archive's own promotion decisions",
    "acquisition": "derived",
    "stated_by": "this project",
    "_what": "The name each promotion decision recorded for the person it created. Not a "
             "new observation: the decision is the record, and this makes the name it "
             "already held reachable as a claim.",
    "_not_a_source_of_fact": "the NAME is the decision's; whether the man existed is the "
                             "underlying document's, cited on his other claims.",
}


def main(write=False):
    conn = sqlite3.connect(f"file:{paths.READ_MODEL}?mode=ro", uri=True)
    # EXCLUDE THIS INGEST'S OWN OUTPUT. `person_name` is built from name claims, and after
    # the first run it contains the ones this file wrote -- so every man "already has a
    # name claim" and the second run writes nothing, emptying the store. The same defect
    # ingest_crippen_aafc.py met and fixed the same way: a decider must not read its own
    # layer. Read the base state: names from every source EXCEPT this one.
    named = {p for p, in conn.execute(
        "select distinct n.person from person_name n join claim c on c.id = n.claim "
        "where c.source_id != ?", (SOURCE["source_id"],))}
    claims, srs = [], {}
    n = collections.Counter()
    for fname, sid, what in STORES:
        p = os.path.join(BASE, "build", fname)
        if not os.path.exists(p):
            n[f"{fname}: absent"] += 1; continue
        for d in json.load(open(p))["promotions"]:
            pid, nm = d.get("person_id"), (d.get("name") or "").strip()
            if not pid or not nm:
                n["decision carries no name -- nothing written"] += 1; continue
            if pid in named:
                n["already has a name claim -- left alone"] += 1; continue
            # A MAN THE CHAIN IS ABOUT TO DEMOTE GETS NO NAME. demote_stintless.py removes
            # a promoted man who carries no season -- Ryan's ruling that the archive's line
            # is a career, not a listing -- and giving him a name claim first makes him the
            # only thing standing between the rebuild and P3: he vanishes from the index
            # while still holding a claim. Five did exactly that, two of them named
            # `special teams` and `john sandusky offense`, which are not names at all.
            if not (d.get("coaching_seasons") or d.get("playing_seasons")):
                n["stintless -- the chain demotes him, so no name is written"] += 1; continue
            ref = (d.get("reversible") or {}).get("lead_ref") or d.get("source") or pid
            sr = f"{sid}#{ref}"
            srs[sr] = {"source_id": SOURCE["source_id"],
                       "locator": f"build/{fname} -> {ref}", "what": what}
            claims.append({
                "id": "c_%06d" % (len(claims) + 1),
                "subject": ["person", pid], "predicate": "name", "value": nm,
                "kind": "observed",
                "source_id": SOURCE["source_id"], "source_record": sr,
                "stated_by": SOURCE["stated_by"], "attribution": [],
                "_the_name_the_decision_recorded": True,
                "_decision": {"store": fname, "ref": ref,
                              "entered_by": d.get("entered_by"),
                              "forename_unknown": bool(d.get("forename_unknown"))},
                "_why": "the promotion that created this person recorded this name; it is "
                        "written as a claim so the archive can find him by it."})
            n[f"name claim written ({sid})"] += 1
            if d.get("forename_unknown"):
                n["  of which forename_unknown"] += 1
    out = {"source": SOURCE, "source_records": srs, "claims": claims,
           "_left_alone": ("2,552 people denoted only by a PFA slug such as `cost00470` get "
                           "nothing here. A four-letter surname stem and a serial is an "
                           "identifier, not a name, and reading it as one would invent it. "
                           "The archive holds a code for those men and should keep saying so."),
           "written_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "counts": dict(n) | {"claims": len(claims)}}
    if write:
        json.dump(out, open(OUT, "w"), indent=1)
    return out


if __name__ == "__main__":
    o = main(write="--write" in sys.argv)
    for k, v in sorted(o["counts"].items(), key=lambda x: -x[1]):
        print(f"   {v:6,d}  {k}")
