"""Find people the archive holds TWICE, and say why. Read-only; decides nothing.

`merge_people.py` turns the `duplicate` verdict into decisions. Everything else
this module returns is deliberately left alone.

WHY THE ARCHIVE SPLITS A MAN
  unify_identity.py joins two local records on ONE kind of evidence, a
  source-native id, and refuses to join on a name -- rightly, since 1,586 names
  in this corpus denote more than one person. So a source arriving with no id
  produces a person who unifies with nothing. The Coaching Tree cache carries a
  StatsCrew slug for 13 of its 144 coaches; the other 131 became their own
  people, nameless, beside the men they already were.

TELLING A DUPLICATE FROM A NAMESAKE
  A namesake shares a name and nothing else, so a name never enters the
  candidate pool and is never evidence. The question is what they share that a
  coincidence could not produce, and whether anything rules one man out.

  RULES ONE MAN OUT, in this order:
    two DIFFERENT names, both present. Measured: an earlier version of this
      module let a birth date, a club-season and a college outvote a name
      difference and produced 45 pairs, every one of which was two men -- Jason
      and Devin McCourty are twins out of Rutgers at New England, and George
      Atkinson and Hubert Ginn were both born 4 January 1947 in Savannah and
      both played for Oakland.
    birth dates differing in TWO OR THREE components. ONE component is not a
      veto: it is the transcription signature declarations/nflverse.json
      declares, and George Allen is 1918-04-29 in one half and 1922-04-29 in
      the other.
    both halves holding a PLAYING season in one year at different clubs. The
      court-salaries store is exempt: its club-seasons are contract facts read
      out of an opinion, and L.C. Greenwood is at Birmingham there and at
      Pittsburgh on the roster in the same year, both true of one man.

  ARGUES FOR ONE MAN:
    same name AND an exact birth date -- the archive's own primary route
    same name, a birth date within one component, a shared club-season AND an
      agreeing origin
    a nameless half whose recovered name matches, with an exact birth date and
      a shared club-season or an agreeing origin

  A DISAGREEING COLLEGE IS NOT A VETO. It blocked 36 pairs in an earlier
  version; 35 disagreed on college alone, and the disagreement is two sources
  naming different true colleges for one man -- Bill Walsh is San Mateo JC in
  one and San Jose State in the other, Howard Mudd 'Michigan State' and
  'Michigan St.'. It is recorded, not obeyed.

  A SHARED SOURCE IDENTIFIER IS NOT EVIDENCE OF ONE MAN. All five in this
  archive are one record attached to two men, including a Wikipedia article
  covering Sam Adams father and son. They are reported as a source defect.

NAMES FOR THE NAMELESS are read back from the store each person came from -- a
Coaching Tree slug, a salaries denotation -- so the name tests can reach the 223
the index left nameless. That recovery is used for MATCHING ONLY and is never
written to the store as a name claim.
"""
import os, re, json, collections, itertools, unicodedata

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MONTH = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}


def dparts(s):
    s = str(s or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m: return tuple(int(x) for x in m.groups())
    m = re.match(r"^([A-Z][a-z]+) (\d{1,2}), (\d{4})$", s)
    if m and m.group(1) in MONTH: return (int(m.group(3)), MONTH[m.group(1)], int(m.group(2)))
    return None


def allv(v): return [x for x in (v if isinstance(v, list) else [v]) if x]
def first(v): return (v[0] if v else None) if isinstance(v, list) else v


def norm(n):
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


def nclub(x):
    t = re.sub(r"[^a-z0-9]", "", (x or "").lower())
    return "" if t in ("none", "null", "na", "usa") else t


def recover_names(ident, IDX):
    """The name each nameless person's OWN store holds. Matching only."""
    rec = {}
    ct = os.path.join(BASE, "build", "coaches.json")
    if os.path.exists(ct):
        loc = {l: p for p, v in ident.items() for s, l in v["local"] if s == "coaches"}
        for c in json.load(open(ct))["claims"]:
            if "#coach/" in c["source_record"] and c["subject"][1] in loc:
                rec.setdefault(loc[c["subject"][1]],
                               ("coaching-tree slug", c["source_record"].split("#coach/")[-1].replace("-", " "),
                                c["source_record"]))
    sal = os.path.join(BASE, "build", "salaries.json")
    if os.path.exists(sal):
        loc = {l: p for p, v in ident.items() for s, l in v["local"] if s == "salaries"}
        for d in json.load(open(sal))["denotations"]:
            if d["person"] in loc and "::" in (d.get("matched_against") or ""):
                rec.setdefault(loc[d["person"]],
                               ("salaries denotation", d["matched_against"].split("::")[-1].strip(),
                                d.get("source_record")))
    return {k: v for k, v in rec.items() if not IDX.get(k, {}).get("name")}


class Population:
    def __init__(self):
        self.IDX = json.load(open(os.path.join(BASE, "build-reports", "person-index.json")))
        self.CL = self.IDX.pop("_clubs", {})
        # MEASURE THE UNMERGED ARCHIVE, ALWAYS. If the merge layer has been applied
        # the index already shows merged people, and deriving decisions from that
        # would record the merged state as the state BEFORE the merge and make the
        # decisions unreversible. Undoing here, in memory, makes this module give
        # the same answer whether or not the merge has been applied. The file on
        # disk is not touched.
        # The club-name to club-code map is READ FROM THE DECISIONS, not re-derived.
        # Re-deriving it here would read an index whose merges have already folded the
        # printed names away, find no corroboration, and make detection depend on
        # whether a rewrite happened to have been applied yet -- which oscillates.
        self.club_norm = {}
        _np = os.path.join(BASE, "build", "club-key-normalisation.json")
        if os.path.exists(_np):
            _d = json.load(open(_np))
            for r in _d.get("rewrites", []) + _d.get("applied_when_merging", []):
                lg, y, _ = r["from"].split("|", 2)
                yr = y[1:5] if y.startswith("y") else y
                self.club_norm[(r["club_as_printed"], yr)] = r["to"].split("|", 2)[2]
        import apply_person_merges as _AP
        self.merges_undone = _AP.undo(self.IDX)
        self.ident = json.load(open(os.path.join(BASE, "build-reports", "identity.json")))
        self.recovered = recover_names(self.ident, self.IDX)
        self.name_to_code = collections.defaultdict(set)
        for k, nm in self.CL.items():
            code, y = k.split("|"); self.name_to_code[(nclub(nm), y)].add(code)
        self.P = {}
        for pid, v in self.IDX.items():
            per = v.get("person") or {}
            cs, yrs, coach_cs = set(), set(), set()
            for k in v.get("seasons") or {}:
                lg, y, club = k.split("|", 2)
                yr = y[1:5] if y.startswith("y") else y
                if not yr.isdigit(): continue
                yrs.add(int(yr))
                # a club-season is compared under its CODE whatever the source called
                # it. This is in memory and changes nothing on disk: without it Bud
                # Carson's two halves share no club-season, because one says CLE and
                # the other says 'Cleveland Bulldogs' for the same 1989 Browns.
                res = self.club_norm.get((club, yr))
                for c in {club} | ({res} if res else set()) | self.name_to_code.get((nclub(club), yr), set()):
                    cs.add((int(yr), c))
                    if lg == "COACHES": coach_cs.add((int(yr), c))
            nm, nsrc = v.get("name"), "index"
            if not nm and pid in self.recovered:
                nsrc, nm = "recovered: " + self.recovered[pid][0], self.recovered[pid][1]
            self.P[pid] = {
                "name": nm, "name_source": nsrc, "n": norm(nm), "index_name": v.get("name"),
                "bds": [d for d in map(dparts, allv(per.get("birth_date"))) if d],
                "bd_raw": first(per.get("birth_date")),
                "multi_valued": sorted(f for f in ("birth_date", "college", "hometown")
                                       if len(allv(per.get(f))) > 1),
                # a nameless record may still carry the man's FULL NAME as a person
                # field -- the pre-1936 assistants CSV writes 'Harold Edward Grange'
                # where the index has no name at all. It is not used as the matching
                # name, which would change the candidate pool; it is used to CHECK a
                # match made on other evidence, by surname.
                "full_name": first(per.get("full_name")),
                "surnames": {norm(x).split()[-1] for x in (nm, first(per.get("full_name")), v.get("name"))
                             if x and norm(x)},
                "college": nclub(first(per.get("college"))), "hometown": nclub(first(per.get("hometown"))),
                "birthplace": nclub(first(per.get("birthplace"))),
                "cs": cs, "coach_cs": coach_cs, "years": yrs,
                "srcs": sorted({s for s, _ in self.ident.get(pid, {}).get("local", [])})}

    # ---------------------------------------------------------------- identifiers
    def shared_source_records(self):
        """A source record on more than one person. NOT evidence of one man."""
        ids = collections.defaultdict(set)
        for pid, v in self.IDX.items():
            for s in v.get("slugs") or []: ids[("statscrew_slug", s)].add(pid)
        for fn, kind in (("pfa-pre1950.json", "pfa_player_code"), ("pfa-1950on.json", "pfa_player_code"),
                         ("wikipedia.json", "wikipedia_article")):
            fp = os.path.join(BASE, "build", fn)
            if not os.path.exists(fp): continue
            for c in json.load(open(fp))["claims"]:
                ids[(kind, c["source_record"].split("#", 1)[1])].add(c["subject"][1])
        out = {}
        for k, v in ids.items():
            if len(v) > 1: out["|".join(k)] = sorted(v)
        return out

    # ---------------------------------------------------------------- candidates
    def candidates(self):
        P, T = self.P, collections.defaultdict(set)
        for k, v in self.shared_source_records().items():
            for a, b in itertools.combinations(sorted(v), 2): T["T1_shared_source_record"].add((a, b))
        by_bd = collections.defaultdict(list)
        for pid, d in P.items():
            for bd in d["bds"]: by_bd[bd].append(pid)
        for ps in by_bd.values():
            for a, b in itertools.combinations(sorted(set(ps)), 2):
                if P[a]["cs"] & P[b]["cs"]: T["T2_birth_date_and_club_season"].add((a, b))
        by_name = collections.defaultdict(list)
        for pid, d in P.items():
            if d["n"]: by_name[d["n"]].append(pid)
        for ps in by_name.values():
            if len(ps) < 2: continue
            for a, b in itertools.combinations(sorted(ps), 2):
                if set(P[a]["bds"]) & set(P[b]["bds"]): T["T3_name_and_birth_date"].add((a, b))
                if P[a]["cs"] & P[b]["cs"]: T["T4_name_and_club_season"].add((a, b))
                if not P[a]["bds"] and not P[b]["bds"] and (P[a]["years"] & P[b]["years"]):
                    T["T5_name_and_years_no_birth_date"].add((a, b))
                if not P[a]["index_name"] or not P[b]["index_name"]:
                    T["T7_name_match_with_a_nameless_half"].add((a, b))
        return T

    # ---------------------------------------------------------------- evidence
    def evidence(self, a, b, shared):
        A, B = self.P[a], self.P[b]
        e = {"shared_source_record": sorted(k for k, v in shared.items() if a in v and b in v)}
        xs, ys = A["bds"], B["bds"]
        e["birth_date"] = "absent" if not (xs and ys) else min(
            ({0: "exact", 1: "one_component"}.get(sum(1 for i in range(3) if x[i] != y[i]), "conflict")
             for x in xs for y in ys), key=["exact", "one_component", "conflict"].index)
        e["birth_dates"] = [A["bd_raw"], B["bd_raw"]]
        e["shared_club_seasons"] = sorted(f"{y}|{c}" for y, c in (A["cs"] & B["cs"]))
        e["origin_agree"] = sorted(f for f in ("college", "hometown", "birthplace")
                                   if A[f] and B[f] and A[f] == B[f])
        e["origin_disagree"] = sorted(f for f in ("college", "hometown", "birthplace")
                                      if A[f] and B[f] and A[f] != B[f])
        e["multi_valued_fields"] = sorted(set(A["multi_valued"]) | set(B["multi_valued"]))
        e["name"] = ("both_absent" if not (A["name"] or B["name"]) else
                     "one_absent" if not (A["name"] and B["name"]) else
                     "same" if A["n"] == B["n"] else "differ")
        e["names"] = [A["name"], B["name"]]
        e["name_sources"] = [A["name_source"], B["name_source"]]
        e["full_names"] = [A["full_name"], B["full_name"]]
        e["surnames_agree"] = bool(A["surnames"] & B["surnames"])
        e["stores"] = [A["srcs"], B["srcs"]]
        pa, pb = A["cs"] - A["coach_cs"], B["cs"] - B["coach_cs"]
        contract_only = {"salaries"} & (set(A["srcs"]) | set(B["srcs"]))
        e["rosters_conflict"] = (not contract_only) and bool({y for y, _ in pa} & {y for y, _ in pb}) and not (pa & pb)
        return e

    def classify(self, e):
        if e["shared_source_record"]:
            return ("mis-attached source record",
                    "one source record is attached to both halves, so any field they share may have come from it")
        if e["name"] == "differ": return "coincidence", "two different names: not one man"
        if e["birth_date"] == "conflict": return "namesake", "birth dates differ in two or three components"
        if e["rosters_conflict"] and not (e["name"] == "same" and e["birth_date"] == "exact"):
            return "namesake", "both hold a playing season in one year at different clubs"
        near = e["birth_date"] in ("exact", "one_component")
        if e["name"] == "same":
            if e["birth_date"] == "exact" and e["multi_valued_fields"]:
                return "unclassifiable", "same name and exact birth date, but a half already holds more than one value for a field"
            if e["birth_date"] == "exact":
                return "duplicate", ("same name and exact birth date" +
                                     (f"; {len(e['origin_disagree'])} origin field(s) disagree, recorded not obeyed"
                                      if e["origin_disagree"] else ", nothing disagrees"))
            if near and e["shared_club_seasons"] and e["origin_disagree"]:
                return "unclassifiable", "same name, near birth date and a shared club-season, but an origin field disagrees"
            if near and e["shared_club_seasons"] and e["origin_agree"]:
                return "duplicate", "same name, birth date within one component, a shared club-season and an agreeing origin"
            if near and (e["shared_club_seasons"] or e["origin_agree"]):
                return "unclassifiable", "same name and a near birth date, but only one supporting fact"
            if e["birth_date"] == "absent" and e["shared_club_seasons"]:
                return "unclassifiable", "same name and a shared club-season, but no birth date to test"
            return "unclassifiable", "same name and nothing else"
        # A NAMELESS HALF STILL HAS TO AGREE ON A SURNAME. An exact birth date with a
        # shared club-season is exactly the shape that produces coincidences elsewhere
        # -- 994 such pairs in this archive are two different men -- and with no name
        # on one half there is nothing to rule that out. Where the index has no name,
        # the record's own `full_name` supplies the surname.
        if not e["surnames_agree"]:
            return "unclassifiable", "one half is nameless and no surname is available to corroborate"
        if e["birth_date"] == "exact" and (e["shared_club_seasons"] or e["origin_agree"]):
            return "duplicate", "exact birth date, an agreeing surname, and a shared club-season or origin, one half nameless"
        if near and e["shared_club_seasons"] and e["origin_agree"]:
            return "duplicate", "birth date within one component, an agreeing surname, a shared club-season and an agreeing origin, one half nameless"
        return "unclassifiable", "one half is nameless and the evidence is thin"

    def run(self):
        T = self.candidates(); shared = self.shared_source_records()
        out = collections.defaultdict(list)
        pairs = sorted({p for v in T.values() for p in v})
        for a, b in pairs:
            e = self.evidence(a, b, shared); verdict, why = self.classify(e)
            out[verdict].append({"a": a, "b": b, "verdict": verdict, "why": why, "evidence": e,
                                 "tests_passed": sorted(t for t, v in T.items() if (a, b) in v)})
        return dict(out), {t: len(v) for t, v in T.items()}, shared


if __name__ == "__main__":
    import sys
    pop = Population(); out, tests, shared = pop.run()
    print(json.dumps({"tests": tests, "verdicts": {k: len(v) for k, v in out.items()},
                      "shared_source_records": len(shared)}, indent=1))
