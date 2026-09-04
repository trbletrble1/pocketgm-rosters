"""Export a season to PGM3. The consumer needs 52 keys; the dataset holds eight.

Everything the dataset does not know is INVENTED HERE and declared in the build
manifest. Nothing invented is written back. The export chooses where the dataset
abstains, and records the choice.
"""
import os, sys, json, uuid, random, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from resolve_store import load

BASE = os.path.join(HERE, "..")
SEASON_YEAR = int(os.environ.get("YEAR", "1950"))
STORE = os.environ.get("STORE", "nfl-1950.json")
GAME_CLOCK = 2026                     # PGM3's internal current season
REF = os.path.join(BASE, "..", "PGMRoster_1986.json")


class Manifest:
    def __init__(self):
        self.invented = collections.Counter()
        self.choices = []
        self.losses = collections.Counter()
        self.refusals = []
    def invent(self, field, n=1): self.invented[field] += n
    def choose(self, kind, subject, chose, over, why):
        self.choices.append({"kind": kind, "subject": subject, "chose": chose,
                             "over": over, "why": why})
    def lose(self, what, n=1): self.losses[what] += n


def map_position(code, pmap, man):
    toks = code.split("-")
    head = toks[0]
    t = pmap["tokens"].get(head)
    if t is None:
        raise KeyError(f"position token {head!r} (from {code!r}) has no map entry - REFUSED")
    if len(toks) > 1:
        man.lose(f"secondary position tokens ({head} kept)", 1)
    return t


def main():
    ref = json.load(open(REF))
    schema = sorted(ref[0].keys())
    pmap = json.load(open(os.path.join(BASE, "export", "position_map.json")))
    lin = json.load(open(os.path.join(BASE, "export", "lineage_choices.json")))
    pol = json.load(open(os.path.join(BASE, "policy", "resolution.json")))
    shape = json.load(open(os.path.join(BASE, "export", "pgm3_shape.json")))
    s = load(os.path.join(BASE, "build", STORE),
             [os.path.join(BASE, "declarations", "statscrew.json")])
    raw = json.load(open(os.path.join(BASE, "build", STORE)))
    s.universe = {tuple(x) for x in raw.get("universe", [])}
    man = Manifest()
    rng = random.Random(20260904)      # seeded; recorded as invented, never a claim

    stints = sorted({u for u in s.universe if u[0] == "stint"})
    # a mover has two stints; the EXPORT must pick one club
    by_person = collections.defaultdict(list)
    for st in stints: by_person[st[1]].append(st)

    # ---- gate: every club must have a lineage choice, or FAIL --------------
    clubs = sorted({st[2] for st in stints})
    missing = [c for c in clubs if c not in lin["choices"]]
    if missing:
        print(f"EXPORT FAILED: clubs with no lineage_choices entry: {missing}")
        print("  The dataset abstains; the export must choose consciously. No fallback.")
        return 1
    for c in clubs:
        if lin["choices"][c].get("contested"):
            man.choose("franchise", c, lin["choices"][c]["slot"], "unresolved",
                       lin["choices"][c]["reason"][:160])

    out = []
    for person, sts in sorted(by_person.items()):
        # club: the export picks one. Games played decides; ties recorded.
        if len(sts) > 1:
            games = {}
            for st in sts:
                r = s.resolve(st, "games_played", pol)
                games[st] = r["value"] if r["basis"] == "observed" else -1
            chosen = max(sts, key=lambda st: games[st])
            man.choose("mover_club", person, chosen[2],
                       "/".join(x[2] for x in sts if x != chosen),
                       f"most games played ({games[chosen]} vs "
                       f"{','.join(str(games[x]) for x in sts if x != chosen)})")
        else:
            chosen = sts[0]
        club = chosen[2]

        name_r = None
        # name comes from the roster row's source_record locator (StatsCrew has no
        # forename/surname split on the roster table)
        for d in s.denotations:
            if d["person"] == person and d["source_record"].startswith("statscrew#roster/"):
                nm = d["source_record"].split("#", 2)[-1]
                if f"/{club}-" in d["source_record"]:
                    name_r = nm; break
                name_r = name_r or nm
        nm = (name_r or "Unknown Unknown").strip()
        parts = nm.split(" ", 1)
        forename, surname = (parts + [""])[:2] if len(parts) > 1 else (parts[0], "")

        pos_r = s.resolve(("person_season", person, f"NFL-{SEASON_YEAR}"), "position", pol)
        if pos_r["basis"] == "contested":
            cands = [c["value"]["code"] for c in pos_r["candidates"]]
            code = cands[0]
            man.choose("contested_position", person, code, "/".join(cands[1:]),
                       "export must emit one position; first candidate taken, "
                       "dataset retains the contest")
        elif pos_r["basis"] == "observed":
            code = pos_r["value"]["code"]
        else:
            man.refusals.append((person, "position", pos_r["basis"])); continue
        try:
            position = map_position(code, pmap, man)
        except KeyError as e:
            man.refusals.append((person, "position_map", str(e))); continue

        bd = s.resolve(("person", person), "birth_date", pol)
        age = None
        if bd["basis"] == "observed":
            try:
                y = int(str(bd["value"]).split(",")[-1].strip()); age = SEASON_YEAR - y
            except Exception: pass
        if age is None or not (18 <= age <= 45):
            age = 26; man.invent("age")

        jr = s.resolve(chosen, "jersey", pol)
        teamNum = jr["value"] if jr["basis"] == "observed" else 0
        if jr["basis"] != "observed": man.invent("teamNum")

        rec = {}
        for k in schema: rec[k] = 0
        rec.update({
            "forename": forename, "surname": surname, "position": position,
            "teamID": lin["choices"][club]["slot"], "teamNum": int(teamNum) if str(teamNum).isdigit() else 0,
            "age": age, "iden": str(uuid.UUID(int=rng.getrandbits(128))).upper(),
        })
        # --- everything below is INVENTED by this export -------------------
        rating = rng.randint(45, 88); man.invent("rating")
        rec["rating"] = rating
        rec["potential"] = min(99, rating + rng.randint(0, 12)); man.invent("potential")
        # POSITION-GATED: only the attributes this position actually uses
        for a in shape["live_attributes"][position]:
            if a in ("discipline","loyalty","greed","ambition"):
                med, sd = shape["attribute_levels"][position][a]
                # personality is INDEPENDENT of rating in the references (all pairwise
                # correlations < 0.05), so it takes the level and no order at all.
                rec[a] = max(20, min(99, int(rng.gauss(med, sd))))
                man.invent("personality")
            elif a == "injuryProne":
                rec[a] = rng.randint(30, 70); man.invent("injuryProne")
            else:
                med, sd = shape["attribute_levels"][position][a]
                # order from the invented rating, level from the reference
                z = (rating - 66) / 12.0
                rec[a] = max(20, min(99, int(med + z * sd + rng.gauss(0, sd * 0.45))))
                man.invent("attributes")
        fam = rng.choice([1, 2, 3, 4, 5])
        hf  = rng.choice([1, 2, 3, 4, 5])
        av  = shape["appearance_slot_vocab"]
        def pick(slot, pref):
            opts = [t for t in av[str(slot)] if t.startswith(pref)]
            return rng.choice(opts) if opts else av[str(slot)][0]
        rec["appearance"] = [pick(0, f"Head{fam}"), rng.choice(av["1"]),
                             pick(2, f"Hair{hf}"), pick(3, f"Beard{hf}"),
                             pick(4, f"Eyebrows{hf}"), pick(5, f"Nose{fam}"),
                             pick(6, f"Mouth{fam}"), "Glasses1e", rng.choice(av["8"])]
        man.invent("appearance")
        yrs_pro = max(0, min(14, age - 22))
        rec["draftSeason"] = GAME_CLOCK - yrs_pro; man.invent("draftSeason")
        rec["draftNum"] = 224; man.invent("draftNum")
        # rookie ladder: drafted this year = 4 years left, then 3, 2, 1.
        # Veterans get a short-weighted spread. Both are the consumer's convention.
        if yrs_pro <= 3:
            rec["length"] = 4 - yrs_pro
        else:
            rec["length"] = rng.choice([1,1,1,1,2,2,3,4,5])
        man.invent("length")
        rec["salary"] = rng.randint(400000, 3000000); man.invent("salary")
        # guarantee tracks REMAINING length, not the original bonus
        ratio = {1: 0.03, 2: 0.35, 3: 0.75, 4: 1.10, 5: 1.45}[rec["length"]]
        rec["guarantee"] = int(rec["salary"] * ratio * rng.uniform(0.7, 1.3))
        man.invent("guarantee")
        gt = [0]*31
        need = (rec["potential"] - rec["rating"]) * 50
        i = 0
        while need > 0 and i < 17:
            step = min(need, rng.randint(1, 60)); gt[i] += step; need -= step; i = (i+1) % 17
        rec["growthType"] = gt; man.invent("growthType")
        out.append(rec)

    # --- de-duplicate jersey within team (a hard convention in every published file)
    used = collections.defaultdict(set); moved = 0
    for r in out:
        t = r["teamID"]; n = r["teamNum"]
        if n and n in used[t]:
            for cand in range(1, 100):
                if cand not in used[t]:
                    r["teamNum"] = cand; moved += 1; break
        used[t].add(r["teamNum"])
    if moved: man.invent("teamNum_dedup", moved); man.lose("original jersey (collided within club)", moved)

    # --- scale to the engine's payroll constant. Era accuracy governs everything
    #     EXCEPT the dollar scale, which is set by the engine (roster-project ruling).
    teams = collections.defaultdict(list)
    for r in out: teams[r["teamID"]].append(r)
    def med_top(rs, k=53):
        v = sorted((x["salary"] + x["guarantee"] for x in rs), reverse=True)[:k]
        return sum(v)
    cur = sorted(med_top(v) for v in teams.values())
    cur = cur[len(cur)//2] if cur else 0
    target = shape["payroll_target_median_top53"]
    if cur:
        f = target / cur
        for r in out:
            r["salary"] = int(r["salary"] * f); r["guarantee"] = int(r["guarantee"] * f)
        man.choose("payroll_scale", "all clubs", f"x{f:.4f}", "era-accurate dollars",
                   "PGM3's cap is a fixed engine constant with no cap field in the schema; "
                   "era-accurate 1950 dollars leave every club ~100% of the cap unused and the "
                   "financial layer inert. One uniform factor preserves every ratio.")

    os.makedirs(os.path.join(BASE, "build"), exist_ok=True)
    outp = os.path.join(BASE, "build", f"PGMRoster_{SEASON_YEAR}.json")
    json.dump(out, open(outp, "w"), separators=(",", ":"))
    manifest = {
        "built": datetime.datetime.now().isoformat(timespec="seconds"),
        "season": f"NFL-{SEASON_YEAR}", "records": len(out),
        "store": STORE, "policy": pol["version"],
        "position_map": pmap["map_id"] + "@" + pmap["version"],
        "schema_keys": len(schema),
        "fields_from_the_dataset": ["forename","surname","position","teamID","teamNum","age"],
        "fields_INVENTED_by_this_export": dict(man.invented),
        "information_lost_in_translation": dict(man.losses),
        "choices_made_by_this_export": man.choices,
        "refusals": [{"person": p, "why": w, "basis": b} for p, w, b in man.refusals],
        "seed": 20260904,
        "note": "Invented values exist ONLY here. They are not claims and are never written back to the store.",
    }
    json.dump(manifest, open(os.path.join(BASE, "build-reports", f"manifest-{SEASON_YEAR}.json"), "w"),
              indent=1, sort_keys=True)
    print(f"exported {len(out)} records -> {outp}")
    print(f"  from the dataset : {', '.join(manifest['fields_from_the_dataset'])}")
    print(f"  invented here    : {sum(man.invented.values())} values across {len(man.invented)} fields")
    print(f"  lost in mapping  : {dict(man.losses)}")
    print(f"  choices recorded : {len(man.choices)}")
    print(f"  refusals         : {len(man.refusals)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
