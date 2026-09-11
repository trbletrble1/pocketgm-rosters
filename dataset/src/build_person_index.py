"""Index every claim in the archive by global person. Read-only.

Nothing here invents. A bio built on this can only say what a claim says.
"""
import os, sys, json, glob, collections, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO                # the only way the index is written (atomic)
import gate_person_index as G        # P1/P2 before a rebuild, P3 around it
DECL = os.path.join(BASE, "declarations", "person-index-rebuild.json")
COACHING_DECL = os.path.join(BASE, "declarations", "coaching-seasons.json")


def _coaching_decl():
    return json.load(open(COACHING_DECL))


def split_coaching(seasons, staff, qual):
    """A COACHING SEASON IS HELD IN ONE SHAPE. Ruled by Ryan, 2026-09-09.

    -> (playing_seasons, coaching_seasons), both keyed (league, year, club).

    The dict a stint claim lands in is decided by its PREDICATE and by nothing else.
    Before this, it was decided by how the man ENTERED THE ARCHIVE: a man already
    held as a player got his PFA coaching seasons in `seasons` (17,067 of them, under
    a real league token), a man promoted from a coaching lead got his in
    `coaching_seasons` (12,656), and the stores that name no league got theirs in
    `seasons` under a `COACHES` token (7,201). Three shapes, no overlap. Jack Pardee's
    `CFL|1995|BIR` was a coaching claim sitting in the dict 53 files read as playing,
    and his served bio said he played for seven clubs, four of which he only coached.

    Three things happen here and each is declared:

    A PLAYER-COACH KEEPS BOTH. The split is per CLAIM, not per key: a key holding a
    jersey and a role_title appears in both dicts, carrying its own half in each. 330
    (person, club-season) pairs are like that and none of them is made to choose.

    A QUALIFIER TRAVELS. `shared_or_split_season` is not a staff claim -- it never
    stands alone -- so it follows the staff claims on its own key, and stays put where
    there are none.

    ONE LEAGUE TOKEN AND ONE YEAR FORMAT. A coaching key from a store that names no
    league carries the token `COACHES` and a `y1979` year; one from PFA carries `NFL`
    and `1979`. 3,281 (person, year, club) triples on 433 men were written both ways.
    The year is normalised bare, and a `COACHES` key MERGES into a real-league key for
    the same (year, club) where one exists -- two sources naming one club-season, one
    of which says which competition it was. Where none does, `COACHES` stays, for the
    reason person-index-rebuild.json gives for `SALARIES`: the key shape cannot write
    an empty league."""
    playing, coaching, renames = {}, {}, []
    for k, sd in seasons.items():
        stint = sd.get("stint") or {}
        staff_part = {pr: v for pr, v in stint.items() if pr in staff}
        rest = {pr: v for pr, v in stint.items() if pr not in staff}
        if staff_part:
            for q in list(rest):
                if q in qual: staff_part[q] = rest.pop(q)
        if staff_part:
            lg, y, club = k
            ck = (lg, y[1:5] if y.startswith("y") and y[1:5].isdigit() else y, club)
            tgt = coaching.setdefault(ck, {"stats": {}, "stint": {}})
            tgt["stint"].update(staff_part)
        if rest or sd.get("stats"):
            playing[k] = {"stats": sd.get("stats") or {}, "stint": rest}
    # THE LEAGUE TOKEN IS LEFT ALONE, and here is why, because it was tried the other way.
    # 3,281 (person, year, club) triples on 433 men are written twice: once by a source
    # that names the league (`NFL|1986|BUF`) and once by one that does not
    # (`COACHES|1986|BUF`). Folding the second into the first looked like "one shape" --
    # and it broke the club table. build_clubs corroborates a printed name against a code
    # by finding ONE MAN who holds both FOR THE SAME LEAGUE-YEAR: that is how the Coaching
    # Tree's "Buffalo Bisons" is known to be the Bills, from 21 person-seasons holding
    # both that string and BUF under COACHES. Folding `COACHES|1986|BUF` into
    # `NFL|1986|BUF` moved one half of every such pair into a different group, and every
    # wrong-for-season string the Coaching Tree corroborates vanished. gate_clubs K2
    # caught it.
    #
    # So a source that names no league keeps its own key. Two keys for one season is not
    # two shapes -- it is two ATTESTATIONS, which is what the index has always held when
    # two sources print a club differently, and the claims remain the record.
    merged = {}
    for (lg, y, c), sd in coaching.items():
        tgt = merged.setdefault((lg, y, c), {"stats": {}, "stint": {}})
        tgt["stint"].update(sd["stint"]); tgt["stats"].update(sd["stats"])
    # EVERY RENAME IS RECORDED, because P3 must be able to tell a key that MOVED from a
    # key that was DELETED. `y1979` -> `1979` and `COACHES` -> a real league are both
    # renames; the proof is the note, exactly as apply_club_keys writes one for a club
    # rename. Without it a rebuild that lost nothing reads as 24,268 losses.
    for k, sd in seasons.items():
        if not ({pr for pr in (sd.get("stint") or {})} & staff): continue
        lg, y, c = k
        yy = y[1:5] if y.startswith("y") and y[1:5].isdigit() else y
        to = (lg, yy, c)
        if to != k and to in merged:
            renames.append({"from": "|".join(k), "to": "|".join(to),
                            "why": "coaching season moved to `coaching_seasons` and normalised "
                                   "(declarations/coaching-seasons.json)"})
    return playing, merged, renames


def resolve_person(store, pid, loc2g):
    """The ONE place a stint subject's s[1] becomes a person: a global P_ id, or a
    (store, local) pair through identity.json -- tried under the store's own name and,
    for a stats-<store> file, under the roster store it adopts ids from. Shared with
    gate_stint_subjects.py so the gate and the builder can never disagree."""
    if isinstance(pid, str) and pid.startswith("P_"): return pid
    g = loc2g.get((store, pid))
    if g is None and store.startswith("stats-"): g = loc2g.get((store[6:], pid))
    return g


def _chain_step_outputs():
    """Every build/ file a DECLARED CHAIN STEP writes, read out of the scripts themselves.

    A name-list goes stale: the fifth report someone writes with a "claims" key would be read
    as a source again and nothing would object until P3 fired. This derives the set instead,
    and the declaration is the record -- if the two drift, the build refuses."""
    import re
    out = {}
    if not os.path.exists(DECL): return out
    d = json.load(open(DECL))
    steps = ([d.get("builder")] + [c["script"] for c in d.get("chain", [])]
             + [c["script"] for c in (d.get("derived_tables_after_the_chain", {})
                                      or {}).get("steps", [])])
    for step in steps:
        p = os.path.join(HERE, step or "")
        if not step or not os.path.exists(p): continue
        src = open(p).read()
        for m in re.finditer(r'"build",\s*"([^"]+\.json)"', src):
            if re.search(r'(dump_atomic|json\.dump)\s*\([^)]*' + re.escape(m.group(1)), src) or f'REPORT = os.path.join(BASE, "build", "{m.group(1)}")' in src \
               or re.search(r'(REPORT|OUT)\s*=\s*os\.path\.join\(BASE,\s*"build",\s*"' + re.escape(m.group(1)), src):
                out.setdefault(m.group(1), []).append(step)
    return out


_DERIVED = _chain_step_outputs()
_DECLARED = {k for k in (json.load(open(DECL)).get("report_stores_not_claim_sources", {}) if os.path.exists(DECL) else {}) if not k.startswith("_")}
_UNDECLARED = set(_DERIVED) - _DECLARED
if _UNDECLARED:
    raise SystemExit(f"REFUSING TO BUILD: chain step(s) write {sorted(_UNDECLARED)} into build/, and the builder would read "
                     f"any of them carrying a 'claims' key back in as a source. Declare them in "
                     f"report_stores_not_claim_sources (with a reason) first: {{k: _DERIVED[k] for k in sorted(_UNDECLARED)}}")
REPORT_STORES = _DECLARED | set(_DERIVED)
sys.path.insert(0, os.path.join(BASE, "service"))
import league_tokens as LT           # ONE implementation of the token rule, shared with the read model
LEAGUE_TOKENS = LT.tokens(DECL)


def read_claims(files, loc2g, held=None):
    """Read every claim store into P. Returns (P, clubs, skipped, held_counts).

    NOTHING IS SKIPPED IN SILENCE. A stint subject that resolves to nobody is counted
    by store with its shape and an example, and the caller prints the whole list and
    writes it beside the index. This is the third time a silent skip cost real data
    (Junior Seau's statistics; the 1926 AFL and the 1934 Reds put the LEAGUE in s[1]),
    and P3 cannot see it: a store that never enters is 0 -> 0 on both sides."""
    held = held or {}
    P = collections.defaultdict(lambda: {"name": collections.Counter(), "seasons": {},
                                         "person": collections.defaultdict(list),
                                         "person_absent": collections.Counter(),
                                         "person_season": [], "slugs": []})
    skipped = collections.Counter(); skipped_ex = {}; held_counts = collections.Counter()
    unreadable, no_claims, reports_skipped = [], [], []
    for f in sorted(files):
        st = os.path.basename(f)[:-5]
        try: d = json.load(open(f))
        except Exception as e:
            # A STORE THAT WILL NOT PARSE IS NOT AN EMPTY STORE. This was `except: continue`,
            # so a store being written by another session while the build read it dropped every
            # person in it in silence -- P3 caught it as people vanishing, which is late.
            unreadable.append({"store": st, "error": f"{type(e).__name__}: {e}"[:160], "bytes": os.path.getsize(f)}); continue
        if st + ".json" in REPORT_STORES:
            # A CHAIN STEP'S OWN REPORT IS NOT A SOURCE. Reading it back made the index's
            # population depend on its own last run: 1,598 empty people for the ids of the
            # previous generation of promotions, lost the moment the report was refreshed.
            reports_skipped.append({"store": st, "claims": len(d.get("claims") or []),
                                    "why": "a chain step's report, declared in report_stores_not_claim_sources"}); continue
        if not isinstance(d, dict) or "claims" not in d:
            # A store with no claims is usually a report; a store TRUNCATED to {} looks
            # identical here. Counted rather than continued, so the two can be told apart.
            no_claims.append({"store": st, "bytes": os.path.getsize(f), "top_level_keys": sorted(d)[:6] if isinstance(d, dict) else type(d).__name__}); continue
        is_stats = st.startswith("stats-")
        base = st[6:] if is_stats else st
        # store_league_tokens, via service/league_tokens.py. None means the store has
        # DECLARED it has no league; the league then comes from the season key on the
        # subject, which is where that declaration says it lives. This line and the read
        # model's used to be two copies of `v.split(" ")[0]` -- and they did not even
        # agree, this one keying on `st` where the other keyed on `base`.
        league = LT.store_league(st, LEAGUE_TOKENS)
        for c in d["claims"]:
            s = c.get("subject")
            if not isinstance(s, list) or len(s) < 2: continue
            if st in held:
                if s[0] == "stint": held_counts[st] += 1
                continue
            pid = s[1]
            g = resolve_person(st, pid, loc2g)
            if not g:
                if s[0] == "stint":
                    why = ("s[1] is not a person: the subject is [stint, league, club, season]" if isinstance(pid, str) and pid.isupper() and len(pid) <= 6
                           else "s[1] is a local id identity.json does not hold for this store")
                    skipped[(st, why)] += 1; skipped_ex.setdefault((st, why), s)
                continue
            pred, val = c.get("predicate"), c.get("value")
            if pred == "name": P[g]["name"][str(val)] += 1; continue
            if s[0] == "stint" and len(s) == 4:
                club, season = s[2], str(s[3])
                yr = season.split("-")[-1]
                # Where the store declares no league, the season key carries it.
                k = (league or LT.from_season_key(season) or "", yr, club)
                sd = P[g]["seasons"].setdefault(k, {"stats": {}, "stint": {}})
                (sd["stats"] if is_stats else sd["stint"])[pred] = val
            elif s[0] == "person_season" and len(s) >= 3:
                yr = str(s[2]).split("-")[-1]
                P[g]["person_season"].append((yr, pred, val))
            elif s[0] == "person":
                # AN ABSENCE IS NOT A VALUE, AND IT IS NOT NOTHING EITHER.
                #
                # Every person value used to be stringified into one list, so an ABSENCE
                # claim -- the source has the column and it is blank, `kind: "absent"`,
                # value None -- arrived as the four-character string "None" beside the real
                # values. 7,077 people carried one: 3,880 face_colour, 2,903 hometown,
                # 1,312 birth_date, 944 pfa.college, 303 college. Every consumer then had to
                # guess: bio_select.clean() drops the word, build_dashboard filters it, and
                # nothing anywhere could tell "the source declined" from "nobody looked".
                #
                # The store already keeps them apart -- model.add_absence exists for exactly
                # this, and statscrew's declaration calls a blank cell in a present column an
                # absence CLAIM and a missing column a declaration fact. The index was the one
                # layer that flattened them. Ruled by Ryan, 2026-09-07.
                #
                # So: `person` carries what a source STATED, and `person_absent` counts what a
                # source DECLINED, per field. A field with only absences is absent from
                # `person` and present in `person_absent`, which is the distinction restored
                # rather than a value invented.
                if c.get("kind") == "absent":
                    P[g]["person_absent"][pred] += 1
                else:
                    P[g]["person"][pred].append(val)
    report = {"unreadable_stores": unreadable, "stores_with_no_claims_block": no_claims, "chain_step_reports_not_read": reports_skipped,
              "skipped": [{"store": st, "why": why, "stints": n, "example_subject": skipped_ex[(st, why)]}
                          for (st, why), n in sorted(skipped.items(), key=lambda x: -x[1])],
              "held": [{"store": st, "stints": n, "why": held[st]} for st, n in sorted(held_counts.items())]}
    return P, report


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
    decl = json.load(open(DECL)) if os.path.exists(DECL) else {}
    for g, v in idm.items(): pass
    P, skip_report = read_claims(glob.glob(os.path.join(BASE, "build", "*.json")), loc2g, decl.get("held_stores", {}))
    for g, v in idm.items(): P[g]["slugs"] = v["slugs"]
    # LOUD: every stint claim that did not enter, by store, in full
    if skip_report["unreadable_stores"]:
        for r in skip_report["unreadable_stores"]: print(f"UNREADABLE STORE: {r['store']} ({r['bytes']:,} bytes) {r['error']}")
        raise SystemExit("REFUSING TO BUILD: a claim store could not be parsed. Every person it holds would be "
                         "dropped in silence. Another session may be writing it -- re-run when it is stable.")
    empty = [r for r in skip_report["stores_with_no_claims_block"] if not r["top_level_keys"]]
    if empty: raise SystemExit(f"REFUSING TO BUILD: {len(empty)} store(s) parse to an empty object -- truncated, not empty: {[r['store'] for r in empty]}")
    print(f"stores with no claims block (reports, not claim stores): {len(skip_report['stores_with_no_claims_block'])}")
    for r in skip_report["chain_step_reports_not_read"]: print(f"CHAIN-STEP REPORT NOT READ AS A SOURCE: {r['store']} ({r['claims']:,} claims) -- {r['why']}")
    n_sk = sum(r["stints"] for r in skip_report["skipped"]); n_held = sum(r["stints"] for r in skip_report["held"])
    print(f"STINT CLAIMS NOT INDEXED: {n_sk:,} unresolved across {len(skip_report['skipped'])} store(s); {n_held:,} in {len(skip_report['held'])} HELD store(s)")
    for r in skip_report["skipped"]: print(f"   {r['stints']:7,}  {r['store']:32} {r['why']}   e.g. {r['example_subject']}")
    for r in skip_report["held"]: print(f"   {r['stints']:7,}  {r['store']:32} HELD: {r['why'][:90]}")
    IO.dump_atomic({"_what": "every stint claim build_person_index could not index, written on every build; "
                             "gate_person_index P4 refuses a rebuild while any store here is not declared",
                    **skip_report}, os.path.join(BASE, "build-reports", "person-index-skipped.json"), indent=1)
    # second pass: now every season exists
    for g, v in P.items():
        for yr, pred, val in v["person_season"]:
            for k2, sd in v["seasons"].items():
                if k2[1] == yr: sd["stint"].setdefault(pred, val)

    _cd = _coaching_decl()
    STAFF = set(_cd["staff_predicates"]["predicates"])
    QUAL = set(_cd["staff_predicates"]["not_staff_though_it_appears_in_those_stores"])
    n_coach_keys = n_both = 0
    out = {}
    for g, v in P.items():
        play, coach, renames = split_coaching(v["seasons"], STAFF, QUAL)
        n_coach_keys += len(coach); n_both += len(set(play) & set(coach))
        rec = {"name": (v["name"].most_common(1)[0][0] if v["name"] else None),
               "slugs": v["slugs"],
               "person": {k: sorted(set(map(str, vs))) for k, vs in v["person"].items() if vs},
               "person_season": v["person_season"],
               "seasons": {"|".join(k): d for k, d in sorted(play.items())}}
        if coach:
            rec["coaching_seasons"] = {"|".join(k): d for k, d in sorted(coach.items())}
        if renames:
            rec["_coaching_key_normalisations"] = renames
        if v["person_absent"]:
            rec["person_absent"] = dict(sorted(v["person_absent"].items()))
        out[g] = rec
    n_abs = sum(len(v["person_absent"]) for v in P.values())
    print(f"absence claims kept apart from values: {sum(sum(v['person_absent'].values()) for v in P.values()):,} "
          f"across {n_abs:,} (person, field) pairs and {sum(1 for v in P.values() if v['person_absent']):,} people "
          f"-- these used to arrive as the string \"None\" in `person`")
    print(f"coaching seasons sorted out of `seasons` by predicate: {n_coach_keys:,} keys; "
          f"{n_both:,} keys are in BOTH dicts because the man played and coached that season")
    withseasons = sum(1 for v in out.values() if v["seasons"])
    out["_clubs"] = {f"{k[0]}|{k[1]}": v for k, v in clubs.items()}
    # The MERGE LAYER is applied last. build/person-merges.json records, with its
    # evidence, which two person ids are one man -- the men unify_identity.py could
    # not join because they arrived with no source-native id. Applying it here means
    # a rebuild does not silently un-merge them. Nothing is deleted: see
    # declarations/person-merges.json and src/apply_person_merges.py.
    # THE DECISIONS ARE A DECLARATION NOW (Ryan, 2026-09-11), and they are READ, NOT GUARDED: this
    # used to be `if os.path.exists(build/person-merges.json)`, so a missing decisions file would
    # have un-merged 93 men in silence. A missing declaration is an error.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import apply_person_merges as AP
    AP.undo(out)
    applied, missing = AP.apply(out, json.load(open(AP.MP)))
    print(f"person merges applied: {len(applied)}" + (f"   MISSING: {missing}" if missing else ""))
    p = IO.INDEX_PATH
    IO.save_index(out)                      # atomic: temp file, fsync, os.replace
    print(f"people indexed: {len(out):,}   with at least one season: {withseasons:,}")
    print(f"wrote {p} ({os.path.getsize(p)/1e6:.0f} MB)")


def rebuild():
    """The only safe entry point. Refuses if gate_person_index's static checks fail,
    builds from claims, runs every declared post-processing patch IN ORDER, then
    proves nothing was lost (P3). On any failure the pre-rebuild index is put back
    and the process exits non-zero. Running main() alone silently discards the
    patch scripts' work -- that is exactly what happened on 2026-09-06."""
    fails, _ = G.static_checks()                   # P1, P2 and P4: an unresolvable stint subject refuses a rebuild
    if fails:
        print("REFUSING TO REBUILD -- gate_person_index static checks failed:")
        for x in fails: print("  ", x)
        sys.exit(1)
    decl = json.load(open(DECL))
    p = IO.INDEX_PATH
    prev = p + ".prev"
    before = None
    if os.path.exists(p):
        # The declared transition's ids are excluded from the BASELINE, not merely
        # forgiven for vanishing -- see gate_person_index.population().
        before = G.population(json.load(open(p)), drop=G._one_time_transition())
        shutil.copy2(p, prev)                          # the rollback point
    try:
        main()
        for step in decl["chain"]:
            args = list(step.get("args", []))
            print(f"post-processing: {step['script']} {' '.join(args)}".rstrip(), flush=True)
            r = subprocess.run([sys.executable, os.path.join(HERE, step["script"])] + args, cwd=HERE)
            if r.returncode != 0:
                raise RuntimeError(f"{step['script']} exited {r.returncode}")
        after = G.population(json.load(open(p)))
        if before is not None:
            lost = G.compare(before, after)
            if lost:
                raise RuntimeError("P3 -- the rebuild LOST work:\n    " + "\n    ".join(lost[:40])
                                   + (f"\n    ... {len(lost) - 40} more" if len(lost) > 40 else ""))
        print("\nP3 before -> after (nothing may fall):")
        for k, a in after["counts"].items():
            b = before["counts"].get(k, "-") if before else "-"
            print(f"  {k:22} {str(b):>9} -> {a:>9}")
        # DERIVED TABLES, after P3. Ryan's ruling 2026-09-07: the club table must never
        # be silently older than the claims that feed it. They run inside the try, so a
        # failure here fails the rebuild and rolls the index back -- refusing to publish
        # claims against a table that could not be rebuilt is the point of the ruling.
        for step in (decl.get("derived_tables_after_the_chain", {}) or {}).get("steps", []):
            args = list(step.get("args", []))
            print(f"derived table: {step['script']} {' '.join(args)}".rstrip(), flush=True)
            r = subprocess.run([sys.executable, os.path.join(HERE, step["script"])] + args, cwd=HERE)
            if r.returncode != 0:
                raise RuntimeError(f"{step['script']} exited {r.returncode}")
        IO.dump_atomic({"counts": after["counts"], "chain": [s["script"] for s in decl["chain"]],
                        "_what": "last-known-good population of person-index.json, written by "
                                 "build_person_index.rebuild() after P3 passed"},
                       os.path.join(BASE, "build-reports", "person-index-population.json"), indent=1)
        if os.path.exists(prev): os.remove(prev)
        print("REBUILD OK")
    except Exception as e:
        print(f"\nREBUILD FAILED: {e}", file=sys.stderr)
        if os.path.exists(prev):
            os.replace(prev, p)
            print(f"rolled back: pre-rebuild index restored to {p}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    rebuild()
