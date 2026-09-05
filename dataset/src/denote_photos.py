"""Attach photos to people, or refuse. Never guess.

The photo set's only key is a name, and design 2.4 forbids a name as identity
evidence. What makes it usable at all is a name that denotes EXACTLY ONE person
in the whole universe - that is a name plus the verified absence of an
alternative, and the verification is the discriminator.

Everything else is refused. 1,263 photos carry a name shared by 2,979 men; one
image served as any of their faces would be wrong on a page with no error
anywhere. A gap is recoverable. A wrong face at scale is not.

  python3 src/denote_photos.py [--write]
"""
import os, sys, csv, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from model import Store
PHOTOS = os.path.expanduser("~/Documents/pgm3-sources/photos")


def person_universe():
    """name -> {global person id}, built from name CLAIMS and the identity map."""
    idm = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
    loc2g = {(s, p): g for g, v in idm.items() for s, p in v["local"]}
    n2g = collections.defaultdict(set)
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if isinstance(c, dict) and c.get("predicate") == "name":
                g = loc2g.get((st, c["subject"][1]))
                if g: n2g[str(c["value"]).strip().lower()].add(g)
    return n2g


def main():
    write = "--write" in sys.argv
    n2g = person_universe()
    decl = json.load(open(os.path.join(BASE, "declarations", "psf-photos.json")))
    store = Store(); store.add_source(decl)

    meas = {}
    mp = os.path.join(PHOTOS, "measured.csv")
    if os.path.exists(mp):
        for r in csv.DictReader(open(mp)):
            meas[r["player"].strip().lower()] = r

    d = collections.Counter()
    refused = {"ambiguous": [], "no_match": []}
    for fn in sorted(os.listdir(os.path.join(PHOTOS, "PSFplayers"))):
        if not fn.lower().endswith(".jpg"): continue
        nm = fn.rsplit(".", 1)[0].replace("_", " ").strip()
        key = nm.lower()
        hits = n2g.get(key, set())
        if len(hits) > 1:
            d["refused_ambiguous"] += 1
            refused["ambiguous"].append({"file": fn, "name": nm, "people": len(hits)})
            continue
        if not hits:
            d["refused_no_match"] += 1
            refused["no_match"].append(fn)
            continue
        g = next(iter(hits))
        store.adopt_person(g)
        sr = store.add_source_record("psf-photos", f"image/{fn}")
        store.declare_subject(("person", g))
        store.add_denotation(sr, g, ["name", "verified_unique_in_person_universe"],
                             "name-unique",
                             matched_against=f"psf:{fn}",
                             note="the name denotes exactly one person in the "
                                  "40,745-person universe; tier 3")
        d["denoted"] += 1
        store.add_claim(sr, ("person", g), "has_photograph", fn, "held-2026",
                        kind="observed", stated_by="PSF photo set")
        m = meas.get(key)
        if not m: continue
        if m.get("status") == "no face":
            store.add_absence(sr, ("person", g), "face_colour", "held-2026",
                              note="image processed, no face detected")
            d["face_absent"] += 1
        elif m.get("cheek_r"):
            store.add_claim(sr, ("person", g), "face_colour",
                            {"cheek": [m["cheek_r"], m["cheek_g"], m["cheek_b"]],
                             "crown": [m.get("crown_r"), m.get("crown_g"), m.get("crown_b")],
                             "skin_frac": m.get("skin_frac")},
                            "held-2026", kind="observed", stated_by="PSF measurement")
            d["face_colour"] += 1

    tot = d["denoted"] + d["refused_ambiguous"] + d["refused_no_match"]
    print(f"photos seen        {tot}")
    print(f"  DENOTED          {d['denoted']}  ({100*d['denoted']//tot}%)")
    print(f"  refused ambiguous{d['refused_ambiguous']:>6}  "
          f"(covering {sum(x['people'] for x in refused['ambiguous'])} men)")
    print(f"  refused no match {d['refused_no_match']:>6}")
    print(f"  face colour claims {d['face_colour']}   face ABSENCE claims {d['face_absent']}")
    if write:
        store.save(os.path.join(BASE, "build", "photos.json"))
        json.dump(refused, open(os.path.join(BASE, "build-reports",
                  "photos-refused.json"), "w"), indent=1)
        print("\nwrote build/photos.json and build-reports/photos-refused.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
