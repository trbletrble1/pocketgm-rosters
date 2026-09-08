"""Gate the Wikipedia photograph builds. Properties over EVERY claim in EVERY
build/wikipedia-photos-*.json, not samples and not one hard-coded file.

The failures this prevents: a photograph whose licence was tested at ingest and
then not written down (indistinguishable later from one nobody checked); a face
overwriting a face; a photograph landing on the same man from two builds (the
2026-09-06 measurement double-counted 432 people exactly this way, because the
held-set was built from two named files instead of from every build file); the
weaker evidence tier being used where the declaration forbids it (before era_cut);
and a licence family the declaration does not know.

  python3 src/gate_wikipedia_photos.py      exit 1 = FAIL
"""
import os, re, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
DECL = json.load(open(os.path.join(BASE, "declarations", "wikipedia.json"), encoding="utf-8"))
OK = re.compile(DECL["PHOTOGRAPHS"]["licence_allow_pattern"], re.I)
FU = re.compile(DECL["PHOTOGRAPHS"]["licence_refuse_pattern"], re.I)
FAMILIES = set(DECL["PHOTOGRAPHS"].get("licence_families", {"public-domain": 1, "open-cc": 1}))
TIERS = set(DECL["PHOTOGRAPHS"].get("evidence_tiers", {"club-named": 1, "name-unique": 1}))
REP = DECL["PHOTOGRAPHS"]["REPLACEMENT"]
MEAS = DECL["PHOTOGRAPHS"]["MEASURED_NOT_PROMISED"]
COMPARE_ON = REP["compare_on"]                  # "shorter_side_px"
STRICTLY_LARGER = REP["strictly_larger"]
HELD_SIZE_UNKNOWN = REP["held_size_unknown"]    # refuse, never guess
HELD_CLAIM_IS_KEPT = REP["held_claim_is_kept"]  # nothing is deleted
MEASURED_FIELDS = MEAS["measured_fields"]
MEASURED_FROM = MEAS["measured_from"]
PORTRAIT_USABILITY = MEAS["portrait_usability"]
RIGHTS = DECL["PHOTOGRAPHS"]["RIGHTS_SUPERSEDES_RIGHTS_UNKNOWN"]
RIGHTS_MARK = RIGHTS["recorded_on_the_claim_as"]      # "superseded_on"
RIGHTS_CLEAR_MEANS = RIGHTS["rights_clear_means"]
RIGHTS_UNKNOWN_MEANS = RIGHTS["rights_unknown_means"]
NEVER_SHRINK_WITHIN = RIGHTS["never_shrink_applies_within"]
ERA_CUT = DECL["IDENTITY"]["era_cut"]
PHOTO_PREDS = ("has_photograph", "wikipedia.photograph")


def photo_holders_outside(exclude):
    """Every person holding a photograph in ANY build file other than `exclude`."""
    held = set()
    for f in glob.glob(os.path.join(BASE, "build", "*.json")):
        if os.path.basename(f) == exclude: continue
        try: d = json.load(open(f))
        except Exception: continue
        if not isinstance(d, dict): continue
        for c in d.get("claims") or []:
            if c.get("predicate") in PHOTO_PREDS: held.add(c["subject"][1])
    return held


def first_seasons():
    """pid -> first season, from the person index (for the era_cut tier rule)."""
    p = os.path.join(BASE, "build-reports", "person-index.json")
    out = {}
    if not os.path.exists(p): return out
    idx = json.load(open(p))
    for pid, v in idx.items():
        if pid == "_clubs" or not isinstance(v, dict): continue
        yrs = []
        for k in (v.get("seasons") or {}):
            pp = str(k).split("|")
            if len(pp) == 3 and pp[1].lstrip("yY").isdigit(): yrs.append(int(pp[1].lstrip("yY")))
        if yrs: out[pid] = min(yrs)
    return out


def _run_never_shrink(d, chk, quiet=False):
    """The never-shrink checks, recomputed FROM THE CLAIMS. One implementation, called by
    gate_file over the real builds and by selftest over specimens -- a gate that carried a
    second copy for its self-test could pass the copy while the real one drifted."""
    claims = d["claims"]
    ns = d.get("never_shrink_proof")
    if not ns: return
    # RECOMPUTED FROM THE CLAIMS, ruled 2026-09-07 by Ryan.
    #
    # This block used to read the build's own boolean. The ingest computes it as
    # all(...) over the SIZE-DECIDED claims, and in wikipedia-photos-replacements.json
    # every one of the 1,667 claims was decided on RIGHTS -- so the boolean was all()
    # over an empty set, `smallest_margin_px` was None, and the gate accepted both.
    # A rule that was never exercised was being reported as a rule that held, and the
    # gate would have gone on saying so if the ingest's enforcement had broken.
    #
    # Three changes: the margins are re-derived here from `image_measured` and
    # `supersedes`; SHRINKS ARE COUNTED ACROSS EVERY CLAIM whatever rule took it, so a
    # rights-decided shrink is visible rather than invisible; and an empty denominator
    # is REFUSED rather than passed.
    on_size = [c for c in claims if (c.get("supersedes") or {}).get(RIGHTS_MARK) == "size"]
    on_rights = [c for c in claims if (c.get("supersedes") or {}).get(RIGHTS_MARK) == "rights"]
    def margin(c):
        new_px = (c.get("image_measured") or {}).get(COMPARE_ON)
        old_px = (c.get("supersedes") or {}).get("held_" + COMPARE_ON)
        return (new_px - old_px) if isinstance(new_px, int) and isinstance(old_px, int) else None
    margins_size = [m for m in (margin(c) for c in on_size) if m is not None]
    all_margins = [(c, margin(c)) for c in claims if c.get("supersedes")]
    comparable = [(c, m) for c, m in all_margins if m is not None]
    shrank = [(c, m) for c, m in comparable if m <= 0]
    unknowable = len(all_margins) - len(comparable)

    # (i) the size rule, re-derived -- and NOT reported as satisfied over nothing
    if not on_size:
        chk(False,
            f"the NEVER SHRINK size rule was not exercised: 0 of {len(claims)} claims were decided "
            f"on size, so the build's every_claim_strictly_larger is all() over an EMPTY SET and its "
            f"smallest_margin_px is {ns.get('smallest_margin_px')!r}. An unexercised rule is not a "
            f"satisfied one. ({len(on_rights)} claims were decided on rights, which is legal and is "
            f"a different rule -- RIGHTS_SUPERSEDES_RIGHTS_UNKNOWN.)")
    else:
        bad = [c for c, m in ((c, margin(c)) for c in on_size) if m is None or m <= 0]
        chk(not bad, f"{len(bad)} size-decided claim(s) are not strictly larger once the claim's own "
                     f"measurement is read: {[x['subject'][1] for x in bad][:4]}")
        chk(len(margins_size) == len(on_size),
            f"{len(on_size) - len(margins_size)} size-decided claim(s) cannot be compared at all "
            f"(a missing measurement or a missing held size)")
        recomputed = min(margins_size) if margins_size else None
        chk(ns.get("smallest_margin_px") == recomputed,
            f"the build reports a smallest margin of {ns.get('smallest_margin_px')!r}; recomputed from "
            f"the claims it is {recomputed!r}")
        chk(bool(ns.get("every_claim_strictly_larger")) == (not bad),
            "the build's every_claim_strictly_larger disagrees with the claims it was computed from")
    # (ii) SHRINKS ACROSS EVERY CLAIM, whatever rule took it. A rights-decided shrink is
    #      legal -- a rights-clear image supersedes a rights-unknown one whatever its size --
    #      and it must still be VISIBLE. It was not: nothing counted it.
    print(f"  never-shrink recomputed: {len(comparable)} of {len(claims)} claims comparable "
          f"({unknowable} with no knowable held size); larger {len(comparable) - len(shrank)}, "
          f"NOT larger {len(shrank)}"
          + (f" -- {[(c['subject'][1], (c['supersedes'] or {}).get('held_' + COMPARE_ON), (c['image_measured'] or {}).get(COMPARE_ON), (c['supersedes'] or {})[RIGHTS_MARK]) for c, m in shrank][:8]}" if shrank else ""))
    illegal = [(c, m) for c, m in shrank if (c.get("supersedes") or {}).get(RIGHTS_MARK) != "rights"]
    chk(not illegal, f"{len(illegal)} claim(s) are no larger than what they supersede under a rule "
                     f"that requires them to be: {[c['subject'][1] for c, _ in illegal][:4]}")
    chk(ns["claims"] == len(claims), "never_shrink_proof miscounts the claims")
    chk(ns.get("on_size", 0) == len(on_size) and ns.get("on_rights", 0) == len(on_rights),
        f"the build reports on_size={ns.get('on_size')} on_rights={ns.get('on_rights')}; "
        f"the claims say {len(on_size)} and {len(on_rights)}")
    chk(ns.get("on_size", 0) + ns.get("on_rights", 0) == len(claims),
        "the build's claims are not all accounted for by one rule or the other")


def gate_file(path, first):
    name = os.path.basename(path)
    d = json.load(open(path))
    claims, dens, ref = d["claims"], d["denotations"], d["refused"]
    fail = []
    def chk(c, m):
        if not c: fail.append(f"{name}: {m}")
    held = photo_holders_outside(name)
    # 1 NEVER SHRINK (RULED 2026-09-07, superseding GAP-FILL ONLY). A claim may land on
    #   a person who already holds a photograph, but only if it SAYS what it supersedes
    #   and is strictly larger on the compared side. Gap-fill's failure was keeping the
    #   thumbnail uncompared; the failure to guard against now is swapping one in silently.
    over = [c for c in claims if c["subject"][1] in held]
    for c in over:
        pid = c["subject"][1]
        sup = c.get("supersedes")
        chk(bool(sup), f"{pid}: a photograph lands on a person who already holds one "
                       f"without naming what it supersedes")
        if not sup: continue
        on = sup.get(RIGHTS_MARK)
        chk(on in ("size", "rights"),
            f"{pid}: supersedes without saying under which rule ({RIGHTS_MARK}={on!r})")
        m = c.get("image_measured") or {}
        chk(bool(m), f"{pid}: replaces a photograph without measuring the new one")
        # The two rules cover DISJOINT pairs. Neither may be used where the other applies:
        # that is what stops the rights rule being read as an exception weakening the size rule.
        if on == "size":
            chk(sup.get("held_rights") == "clear",
                f"{pid}: decided on SIZE against a rights-{sup.get('held_rights')} image. "
                f"{NEVER_SHRINK_WITHIN}")
            new, old = m.get(COMPARE_ON), sup.get("held_" + COMPARE_ON)
            ok = isinstance(new, int) and isinstance(old, int) and (new > old if STRICTLY_LARGER else new >= old)
            chk(ok, f"{pid}: replacement is not larger ({old} -> {new} {COMPARE_ON})")
        elif on == "rights":
            chk(sup.get("held_rights") == "unknown",
                f"{pid}: decided on RIGHTS against a rights-{sup.get('held_rights')} image. "
                f"{NEVER_SHRINK_WITHIN}")
            chk(not sup.get("held_licence"),
                f"{pid}: superseded on rights an image that HAS a licence ({sup.get('held_licence')!r}). "
                f"{RIGHTS_UNKNOWN_MEANS}")
            chk(bool(OK.search(c.get("licence") or "")),
                f"{pid}: superseded on rights without itself being rights-clear. {RIGHTS_CLEAR_MEANS}")
    # 2 one photograph per person in this build
    subs = [c["subject"][1] for c in claims]
    chk(len(subs) == len(set(subs)), "a person receives more than one photograph here")
    # 3 fair use is absent from the claims and present in the refusals
    chk(not [c for c in claims if FU.search(c.get("licence") or "")], "a fair-use licence reached a claim")
    chk(all(FU.search(x["licence"]) for x in ref.get("fair_use", [])), "a non-fair-use image sits in the fair_use refusals")
    # 4 every claim records a usable licence, a declared family, and an attribution condition
    for c in claims:
        lic = c.get("licence")
        chk(bool(lic), f"claim without a licence: {c.get('value')}")
        chk(bool(OK.search(lic or "")), f"claim whose licence is not recognised free: {lic!r}")
        chk(c.get("licence_family") in FAMILIES, f"claim with an undeclared licence family: {c.get('licence_family')!r} for {lic!r}")
        chk(isinstance(c.get("attribution_required"), bool), f"claim without an attribution condition: {lic}")
        if c.get("licence_family") == "free-other":
            chk(lic in ("No restrictions", "GFDL"), f"free-other family carries an unexpected raw string: {lic!r}")
            chk(c.get("attribution_required") is (lic == "GFDL"), f"attribution flag wrong for {lic!r}")
    # 5 anything held for a ruling was NOT ingested by THIS build, and is either still
    #   undecided or -- once the declaration decided it -- was applied by a LATER build.
    #   (The 09:44 backfill held six 'No restrictions'/GFDL images; the ruling of
    #   2026-09-06 decided them and the sweep build applied them. That is consistent.
    #   A decided licence still held back with no later application is not.)
    unrec = {x["image"] for x in ref.get("unrecognised_licence", [])}
    chk(not (unrec & {c["value"] for c in claims}), "an image held for a ruling was also ingested here")
    for x in ref.get("unrecognised_licence", []):
        chk(not FU.search(x["licence"]), f"a fair-use licence sits in unrecognised: {x['licence']}")
        if OK.search(x["licence"]):
            chk(x["person"] in held, f"licence {x['licence']!r} was decided free but {x['person']} "
                                     f"was never ingested by a later build")
    # 6 the evidence is recorded, says WHICH evidence, and the tier is readable without re-deriving
    chk(len(dens) == len(claims), "a photograph without a denotation")
    by_pid = {c["subject"][1]: c for c in claims}
    for dn in dens:
        chk(dn.get("discriminator") and dn["discriminator"][0] == "article_subject",
            f"denotation not recorded as the source's own association: {dn.get('discriminator')}")
        chk(dn.get("method") in ("article-subject+club-named", "article-subject+name-unique"),
            f"unknown evidence method: {dn.get('method')}")
        tier = dn.get("evidence_tier")
        if tier is not None:                       # builds after 2026-09-06 carry the tier explicitly
            chk(tier in TIERS, f"undeclared evidence tier {tier!r}")
            chk(tier == dn["method"].split("+")[-1], f"tier {tier!r} disagrees with method {dn['method']!r}")
            c = by_pid.get(dn["person"])
            chk(c is not None and c.get("evidence_tier") == tier, f"claim and denotation disagree on tier for {dn['person']}")
            # the weaker tier is forbidden before era_cut
            if tier == "name-unique" and dn["person"] in first:
                chk(first[dn["person"]] >= ERA_CUT, f"name-unique evidence used before era_cut for {dn['person']} (first season {first[dn['person']]})")
    # 7 the build's own arithmetic is true -- under whichever rule it was made
    g = d.get("gap_fill_proof")
    if g:
        chk(g["overwritten"] == 0, "the build records an overwrite")
        chk(g["people_holding_a_photograph_BEFORE"] + g["photographs_written"] == g["people_holding_a_photograph_AFTER"],
            "the gap-fill arithmetic does not hold")
    _run_never_shrink(d, chk)
    ns = d.get("never_shrink_proof")
    chk(bool(g) or bool(ns), "the build does not state which rule it was made under")
    # 7b an unknown held size is REFUSED, never guessed at
    unknown = {x["person"] for x in ref.get("held_size_unknown", [])}
    chk(not (unknown & {c["subject"][1] for c in claims}),
        f"a person whose held size was unknown was ingested anyway ({HELD_SIZE_UNKNOWN[:30]}...)")
    # 7c nothing was deleted: the superseded photograph is still in its own build file
    for c in claims:
        sup = c.get("supersedes")
        if not sup: continue
        hp = os.path.join(BASE, "build", sup["held_in"])
        chk(os.path.exists(hp), f"the superseded build file is gone: {sup['held_in']} ({HELD_CLAIM_IS_KEPT[:24]}...)")
    # 9 the college-coach extension is taken ONLY on club-named evidence (its infobox is
    #   sport-agnostic; name alone admitted basketball coaches)
    for r in (d.get("ruled_in") or {}).get("college_coach_infobox", []):
        chk(r.get("evidence_tier") == "club-named",
            f"college-coach-infobox admission on {r.get('evidence_tier')!r} evidence: {r.get('name')}")
    for r in ref.get("college_coach_not_club_named", []):
        chk(r["person"] not in by_pid, f"a college-coach refusal was also ingested: {r.get('name')}")
    # 10 the size on a claim is MEASURED, and portrait usability is recorded as unassessed.
    #    A dimension is not a promise: the usable quantity in a portrait is the face region
    #    and nothing here measures it. RULED 2026-09-07.
    for c in claims:
        m = c.get("image_measured")
        if m is None: continue                      # builds before 2026-09-07 measured nothing
        for f in MEASURED_FIELDS:
            chk(m.get(f) is not None, f"claim measures no {f}: {c.get('value')}")
        chk(m.get("measured_from") == MEASURED_FROM,
            f"claim does not say its size came from the file: {m.get('measured_from')!r}")
        chk(c.get("portrait_usability") == PORTRAIT_USABILITY,
            f"claim records portrait usability {c.get('portrait_usability')!r}, not {PORTRAIT_USABILITY!r}")
        bad = [k for k in ("usable", "is_usable", "quality", "usable_px") if k in c]
        chk(not bad, f"claim carries a usability verdict it did not earn: {bad}")
    tiers = {t: sum(1 for dn in dens if dn.get("evidence_tier") == t) for t in sorted(TIERS)}
    print(f"{name}: photographs {len(claims)}  fair-use refused {len(ref.get('fair_use', []))}  "
          f"held for a ruling {len(ref.get('unrecognised_licence', []))}  tiers {tiers}")
    if g:
        print(f"  gap-fill: {g['arithmetic']}  overwritten={g['overwritten']}")
    if ns:
        print(f"  never-shrink AS THE BUILD REPORTS IT: {ns['claims']} claims, {ns['on_size']} decided on size, "
              f"{ns['on_rights']} on rights; smallest size margin {ns['smallest_margin_px']}px; "
              f"refused after measuring {ns['refused_after_measuring']}")
    return fail


def _specimen(on_size=0, on_rights=0, shrink_on=None, held=200, new=240,
              says_larger=True, smallest=None, unknowable=0):
    """A never_shrink build, made to order. The gate must read the CLAIMS, so what the
    proof block says and what the claims say are set independently."""
    claims = []
    for i in range(on_size):
        claims.append({"subject": ["person", f"P_S{i:03d}"], "licence": "Public domain",
                       "licence_family": "public-domain", "attribution_required": False,
                       "evidence_tier": "club-named", "portrait_usability": PORTRAIT_USABILITY,
                       "image_measured": {"width_px": new, "height_px": new, COMPARE_ON: new,
                                          "bytes": 1, "format": "jpeg", "measured_from": MEASURED_FROM},
                       "supersedes": {"held_in": "x.json", "value": "v", "held_" + COMPARE_ON: held,
                                      "held_rights": "clear", RIGHTS_MARK: "size"}})
    for i in range(on_rights):
        claims.append({"subject": ["person", f"P_R{i:03d}"], "licence": "Public domain",
                       "licence_family": "public-domain", "attribution_required": False,
                       "evidence_tier": "club-named", "portrait_usability": PORTRAIT_USABILITY,
                       "image_measured": {"width_px": new, "height_px": new, COMPARE_ON: new,
                                          "bytes": 1, "format": "jpeg", "measured_from": MEASURED_FROM},
                       "supersedes": {"held_in": "x.json", "value": "v", "held_" + COMPARE_ON: held,
                                      "held_rights": "unknown", RIGHTS_MARK: "rights"}})
    if shrink_on:
        c = next(c for c in claims if c["supersedes"][RIGHTS_MARK] == shrink_on)
        c["image_measured"][COMPARE_ON] = held - 10
    for i in range(unknowable):
        claims[i]["supersedes"]["held_" + COMPARE_ON] = None
    return {"claims": claims,
            "never_shrink_proof": {"claims": len(claims), "on_size": on_size, "on_rights": on_rights,
                                   "every_claim_strictly_larger": says_larger,
                                   "smallest_margin_px": smallest, "refused_after_measuring": 0}}


def selftest():
    """Every never-shrink check, shown FAILING for its own reason.

    The gate accepted a vacuous pass over 1,667 claims until 2026-09-07, so nothing here is
    trusted until it has been seen to fire."""
    print("SELFTEST -- the never-shrink checks, each broken in turn\n")
    cases = [
        ("an EMPTY denominator: no claim was decided on size",
         _specimen(on_size=0, on_rights=3, says_larger=True, smallest=None), "not exercised"),
        ("a size-decided claim that SHRANK",
         _specimen(on_size=3, on_rights=0, shrink_on="size", smallest=-10), "not strictly larger"),
        ("the build's boolean disagrees with its own claims",
         _specimen(on_size=3, on_rights=0, shrink_on="size", says_larger=True, smallest=40), "disagrees with the claims"),
        ("a size-decided claim with no knowable held size",
         _specimen(on_size=3, on_rights=0, smallest=40, unknowable=1), "cannot be compared"),
        ("the reported smallest margin is not the recomputed one",
         _specimen(on_size=3, on_rights=0, smallest=999), "recomputed from"),
        ("the proof miscounts which rule took the claims",
         dict(_specimen(on_size=2, on_rights=2, smallest=40),
              never_shrink_proof={"claims": 4, "on_size": 4, "on_rights": 0,
                                  "every_claim_strictly_larger": True, "smallest_margin_px": 40}), "the claims say"),
    ]
    ok = []
    clean = _specimen(on_size=3, on_rights=2, smallest=40)
    for name, spec, needle in cases:
        fail = []
        def chk(c, m):
            if not c: fail.append(m)
        _run_never_shrink(spec, chk, quiet=True)
        hit = any(needle in m for m in fail)
        print(f"  {'OK  ' if hit else 'BAD '} {name}\n        -> {fail[0][:150] if fail else 'NOTHING FIRED'}")
        ok.append(hit)
    fail = []
    _run_never_shrink(clean, lambda c, m: fail.append(m) if not c else None, quiet=True)
    print(f"  {'OK  ' if not fail else 'BAD '} a sound build passes: {fail or 'no failure'}")
    ok.append(not fail)
    # a rights-decided shrink is LEGAL and must be reported, not failed
    fail = []
    _run_never_shrink(_specimen(on_size=2, on_rights=2, shrink_on="rights", smallest=40),
                      lambda c, m: fail.append(m) if not c else None, quiet=True)
    print(f"  {'OK  ' if not fail else 'BAD '} a RIGHTS-decided shrink is legal and does not fail: {fail or 'no failure'}")
    ok.append(not fail)
    print(f"\nselftest {'PASSED' if all(ok) else 'FAILED'}")
    return all(ok)


def main():
    files = sorted(glob.glob(os.path.join(BASE, "build", "wikipedia-photos-*.json")))
    if not files:
        print("FAIL: no build/wikipedia-photos-*.json"); return 1
    first = first_seasons()
    fail = []
    for f in files: fail += gate_file(f, first)
    # 8 across builds: a person appears in at most one wikipedia-photos file
    seen, dup = {}, []
    for f in files:
        for c in json.load(open(f))["claims"]:
            pid = c["subject"][1]
            if pid in seen and seen[pid] != os.path.basename(f) and not c.get("supersedes"):
                dup.append(pid)
            seen[pid] = os.path.basename(f)
    if dup: fail.append(f"{len(dup)} people hold a photograph in two wikipedia-photos builds: {dup[:3]}")
    if fail:
        print("\nGATE FAILED:"); [print("  -", x) for x in fail[:12]]; return 1
    print(f"\nGATE PASSED over {len(files)} build(s): every replacement names what it supersedes and is "
          "strictly larger, nothing deleted, every licence recorded with a declared family, no fair use, "
          "evidence names its tier, no tier below era_cut, and no claim promises usability it did not measure")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    sys.exit(main())
