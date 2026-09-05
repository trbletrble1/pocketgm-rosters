"""Index every claim in the archive by global person. Read-only.

Nothing here invents. A bio built on this can only say what a claim says.
"""
import os, sys, json, glob, collections
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main():
    idm = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
    clubs = {}
    cp = os.path.join(BASE, "build", "club-names.json")
    if os.path.exists(cp):
        for c in json.load(open(cp))["claims"]:
            s = c["subject"]                     # ("club_season", league, year, team)
            if c.get("predicate") == "club_name":
                clubs[(s[3], str(s[2]))] = c["value"]
    loc2g = {(s, p): g for g, v in idm.items() for s, p in v["local"]}
    P = collections.defaultdict(lambda: {"name": collections.Counter(), "seasons": {},
                                         "person": collections.defaultdict(list),
                                         "person_season": [], "slugs": []})
    for g, v in idm.items(): P[g]["slugs"] = v["slugs"]
    for f in sorted(glob.glob(os.path.join(BASE, "build", "*.json"))):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict) or "claims" not in d: continue
        is_stats = st.startswith("stats-")
        base = st[6:] if is_stats else st
        league = base.split("-")[0].upper()
        for c in d["claims"]:
            s = c.get("subject")
            if not isinstance(s, list) or len(s) < 2: continue
            # The statistics stores ADOPT the global id rather than minting a
            # local one, so a (store, local) lookup finds nothing and every
            # statistic silently vanished from the index - Junior Seau came out
            # "no statistics are recorded".
            pid = s[1]
            g = pid if isinstance(pid, str) and pid.startswith("P_") else loc2g.get((st, pid))
            if not g: continue
            pred, val = c.get("predicate"), c.get("value")
            if pred == "name": P[g]["name"][str(val)] += 1; continue
            if s[0] == "stint" and len(s) == 4:
                club, season = s[2], str(s[3])
                yr = season.split("-")[-1]
                k = (league, yr, club)
                sd = P[g]["seasons"].setdefault(k, {"stats": {}, "stint": {}})
                (sd["stats"] if is_stats else sd["stint"])[pred] = val
            elif s[0] == "person_season" and len(s) >= 3:
                # position lives HERE, not on the stint - and walking only stint
                # and person scopes meant no bio could say what a man played.
                yr = str(s[2]).split("-")[-1]
                lgp = str(s[2]).split("-")[0] if "-" in str(s[2]) else league
                # attach AFTER all claims are read: claims arrive in file order
                # and a person_season claim often precedes the stint it belongs
                # to, so attaching here reached only 20% of people.
                P[g]["person_season"].append((yr, pred, val))
            elif s[0] == "person":
                P[g]["person"][pred].append(val)
    # second pass: now every season exists
    for g, v in P.items():
        for yr, pred, val in v["person_season"]:
            for k2, sd in v["seasons"].items():
                if k2[1] == yr: sd["stint"].setdefault(pred, val)

    out = {g: {"name": (v["name"].most_common(1)[0][0] if v["name"] else None),
               "slugs": v["slugs"],
               "person": {k: sorted(set(map(str, vs))) for k, vs in v["person"].items()},
               "person_season": v["person_season"],
               "seasons": {"|".join(k): d for k, d in sorted(v["seasons"].items())}}
           for g, v in P.items()}
    withseasons = sum(1 for v in out.values() if v["seasons"])
    out["_clubs"] = {f"{k[0]}|{k[1]}": v for k, v in clubs.items()}
    p = os.path.join(BASE, "build-reports", "person-index.json")
    json.dump(out, open(p, "w"))
    print(f"people indexed: {len(out):,}   with at least one season: {withseasons:,}")
    print(f"wrote {p} ({os.path.getsize(p)/1e6:.0f} MB)")


if __name__ == "__main__":
    main()
