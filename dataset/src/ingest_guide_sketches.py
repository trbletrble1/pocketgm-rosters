"""Write LA Dons 1948 sketch claims, and a LEADS store for the men who don't match.

Six categories, six different facts, and they must reconcile to the BORN: count:

  1 resolved_written        claims written against a person in the archive
  2 unmatched_no_candidate  a man in the guide who resolves to nobody. A LEAD.
  3 normaliser_gap          the name IS on the roster; our normaliser joined it
                            (BILLFISK). Not a missing man -- a code gap.
  4 name_variant_candidate  BOB NELSON / Robert Nelson. A JUDGMENT, not a match.
  5 roster_conflict         the guide places him on this club-season and the
                            archive does not. A SOURCE CONFLICT: both are held.
  6 ambiguous_dropped       the sketch merged two men. No claims, ever.

A LEAD IS NOT A PERSON. The person index is built on StatsCrew and this does not
change that. But a lead carries THE SAME FIELD SET as a matched man, so if one is
ever confirmed nothing needs re-parsing. Promotion requires an explicit ruling and
there is no code path that does it.
"""
import os, re, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from parse_guide_sketches import parse

SOURCE = {
    "source_id": "media-guide-lad-1948",
    "name": "Los Angeles Dons (AAFC) 1948 Press and Radio Guide",
    "acquisition": "fetched",
    "stated_by": "Los Angeles Dons Football Club",
    "archive_item": "los-angeles-dons-aafc-1948-media-guide",
    "places_on": {"league": "AAFC", "year": 1948, "club": "Los Angeles Dons"},
    "_labels_are_not_normalised": "SERVICE RECORD, HIGH SCHOOL FOOTBALL and the rest "
        "are kept exactly as printed. Mapping them to modern field names is a ruling, "
        "not a parsing step.",
}
CATEGORIES = ["resolved_written", "unmatched_no_candidate", "normaliser_gap",
              "name_variant_candidate", "roster_conflict", "ambiguous_dropped"]


class LeadError(Exception):
    pass


def predicate(label, parent=None):
    if label == "HONORS":
        return "guide.HONORS@" + (parent or "UNATTACHED")
    return "guide." + label


def make_claim(sr, pid, label, value, parent=None):
    if not pid:
        raise LeadError("a claim requires a person; a lead is not a person")
    return {"source_record": sr, "source_id": SOURCE["source_id"],
            "stated_by": SOURCE["stated_by"], "attribution": [SOURCE["name"]],
            "subject": ["person", pid], "predicate": predicate(label, parent),
            "value": value, "kind": "observed", "observed_at": "guide-1948"}


def fieldset(rec):
    """The field set. IDENTICAL for a matched man and a lead -- that is the point."""
    out = collections.OrderedDict()
    for k, v in rec["fields"].items():
        out[k] = v
    for i, h in enumerate(rec["honours"]):
        out[f"HONORS@{h['parent'] or 'UNATTACHED'}#{i}"] = h["value"]
    return out


def main(write=True):
    sys.path.insert(0, HERE)
    import write_bios as W
    P = parse("/Users/ryannecci/Documents/pgm3-sources/nfl-books/text_all/"
              "los-angeles-dons-aafc-1948-media-guide.txt")
    roster = {}
    for g, p in W.IDX.items():
        if g == "_clubs" or not p.get("seasons"):
            continue
        for s in W.seasons(p):
            if (s["league"] == "AAFC" and s["year"] == 1948
                    and W.CLUBS.get(f"{s['club']}|1948", "").startswith("Los Angeles Dons")):
                roster[p["name"]] = g
    allnames = collections.defaultdict(list)
    for g, p in W.IDX.items():
        if g != "_clubs" and p.get("name"):
            allnames[re.sub(r"[^a-z]", "", p["name"].lower())].append((g, p["name"]))

    def norm(n):
        n = re.sub(r"\(.*?\)", "", n)
        return re.sub(r"[^a-z]", "", n.lower())

    rn = {norm(k): (g, k) for k, g in roster.items()}
    # A name variant is detected STRUCTURALLY, not from a hand list: same surname
    # on the SAME club-season roster, with first names that are compatible -- one a
    # prefix of the other (Walt/Walter, Len/Leonard, Lin/Linwood, John/Johnny), or a
    # declared diminutive (Bob/Robert). It is still a CANDIDATE, never a resolution:
    # the archive holds the guide's spelling and the roster's, and says so.
    # A CONTRACTION IS NOT A PREFIX. "leonard".startswith("len") is FALSE -- L-E-O,
    # not L-E-N -- so Len/Leonard needs declaring, and so does Bob/Robert. These are
    # judgment aids, declared and auditable, never evidence.
    DIMINUTIVE = {("bob", "robert"), ("bill", "william"), ("dick", "richard"),
                  ("jim", "james"), ("hank", "henry"), ("chuck", "charles"),
                  ("al", "albert"), ("joe", "joseph"), ("jack", "john"),
                  ("len", "leonard"), ("ted", "edward"), ("ned", "edward"),
                  ("dan", "daniel"), ("gus", "august"), ("bert", "herbert"),
                  ("burt", "burton"), ("chet", "chester"), ("ken", "kenneth")}

    def first_last(n):
        n = re.sub(r"\(.*?\)", " ", n)
        parts = [x for x in re.sub(r"[^A-Za-z ]", " ", n).lower().split() if len(x) > 1]
        return (parts[0], parts[-1]) if len(parts) >= 2 else (None, None)

    def compatible(a, b):
        if a == b:
            return True
        if a.startswith(b) or b.startswith(a):
            return True
        return (a, b) in DIMINUTIVE or (b, a) in DIMINUTIVE

    roster_fl = {}
    for k, g in roster.items():
        f, l = first_last(k)
        if f:
            roster_fl.setdefault(l, []).append((f, k, g))

    def variant_of(nm):
        f, l = first_last(nm)
        if not f:
            return None
        cands = [(k, g) for (rf, k, g) in roster_fl.get(l, []) if compatible(f, rf)]
        return cands[0] if len(cands) == 1 else None

    ROSTER_CONFLICT = {"BERT PIGGOTT", "JIM STILL"}

    cats = collections.defaultdict(list)
    claims, leads = [], []
    sr = f"{SOURCE['source_id']}#player-sketches"

    for rec in P["clean"]:
        nm = rec["name_as_printed"]
        key = norm(nm)
        hit = rn.get(key)
        if hit:
            cats["resolved_written"].append((nm, hit[0]))
            pid = hit[0]
            for label, value in rec["fields"].items():
                if label.startswith("_") or label in ("height", "weight", "college_header"):
                    lab = {"_marital": "MARITAL STATUS", "height": "HEIGHT",
                           "weight": "WEIGHT", "college_header": "COLLEGE (HEADER)"}[label]
                else:
                    lab = label
                claims.append(make_claim(sr, pid, lab, value))
            for h in rec["honours"]:
                claims.append(make_claim(sr, pid, "HONORS", h["value"], h["parent"]))
            continue
        var = variant_of(nm)
        if var:
            cat, why, cand = ("name_variant_candidate",
                              f"the roster has {var[0]!r} -- same surname on this same "
                              f"club-season, first name compatible. Almost certainly the same "
                              f"man, but that is a JUDGMENT and is NOT resolved here.",
                              var[1])
        elif nm in ROSTER_CONFLICT:
            hits = allnames.get(key) or []
            cat, why, cand = ("roster_conflict",
                              "the guide places him on the 1948 Dons; the archive roster does "
                              "not. Both are held; neither is resolved.",
                              hits[0][0] if hits else None)
        else:
            # A near-surname is NOT a match -- one letter apart could be a different
            # man -- but burying it would hide the only lead there is. It is stated
            # in the reason, and the category stays unmatched.
            f0, l0 = first_last(nm)
            near = [k for k in roster if l0 and abs(len(first_last(k)[1] or "") - len(l0)) <= 2
                    and first_last(k)[1] and (first_last(k)[1].startswith(l0[:4])
                                              or l0.startswith((first_last(k)[1] or "")[:4]))]
            cat, why, cand = ("unmatched_no_candidate",
                              ("no person of this name on the 1948 Dons roster and none found "
                               "in the archive"
                               + (f". NEAR-SURNAME on this roster, NOT matched: {near}"
                                  if near else "")), None)
        cats[cat].append((nm, cand))
        leads.append({"lead_id": f"lead-lad1948-{len(leads)+1:03d}", "category": cat,
                      "name_as_printed": nm, "position": rec["position"],
                      "source_id": SOURCE["source_id"], "source_record": sr,
                      "places_on": SOURCE["places_on"], "why_matching_failed": why,
                      "candidate_person": cand, "IS_NOT_A_PERSON": True,
                      "fields": fieldset(rec)})
    for rec, why in P["ambiguous"]:
        cats["ambiguous_dropped"].append((rec["name_as_printed"], why))

    out = {"source": SOURCE, "claims": claims, "leads": leads,
           "categories": {c: [list(x) for x in cats[c]] for c in CATEGORIES},
           "reconciliation": {
               "born_lines": P["born_total"], "clean_sketches": len(P["clean"]),
               "ambiguous_sketches": len(P["ambiguous"]),
               "men_inside_ambiguous": sum(int(w.split()[0]) for _, w in P["ambiguous"]),
           }}
    if write:
        json.dump(out, open(os.path.join(BASE, "build", "guide-lad-1948.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    o = main()
    r = o["reconciliation"]
    print(f"BORN lines {r['born_lines']} | clean {r['clean_sketches']} | "
          f"ambiguous {r['ambiguous_sketches']} holding {r['men_inside_ambiguous']} men")
    print(f"claims written: {len(o['claims'])}   leads: {len(o['leads'])}")
    for c in CATEGORIES:
        print(f"  {c:24s} {len(o['categories'][c]):3d}")
