"""Core primitives: persons, sources, claims, denotations, resolution.

Design invariants enforced here rather than remembered:
  - a person has NO attributes. Names are claims.
  - a claim cannot exist without a source_record.
  - a source_record reaches a person only through a denotation.
  - `relayed` acquisition may never enter the store.
  - resolution is a pure function of (claims, policy).
"""
import json, hashlib, os, re
from collections import defaultdict

KINDS = {"observed", "source_derived", "derived", "absent"}

# There is no predicate called `salary`. Three incompatible conventions exist in
# the sources and pooling them manufactures disagreements out of definitions, so
# the convention is part of the predicate NAME - pooling is not expressible.
BARE_MONEY_PREDICATES = {"salary", "pay", "compensation", "wage", "average_salary"}
# Claims about the SYSTEM, not about a person. Distinct subject scope so they can
# never be averaged with player money - the subject types simply do not meet.
SYSTEM_PREDICATES = {
    "option_year_rate", "developmental_squad_weekly_wage", "roster_bonus_is_conditional",
    "league_entry_fee", "club_workers_comp_self_insured_ceiling",
}
LEAGUE_SCOPES = {"league_season", "league_era", "league"}

# A positional or service-year AVERAGE is neither a person's pay nor a league
# rule. It describes a COHORT, and it needs its own scope or it has nowhere to
# live: person-money predicates refuse a league subject, and rightly.
COHORT_SCOPES = {"cohort"}
COHORT_PREDICATES = {
    "cohort_salary_average", "cohort_salary_median",
    "cohort_salary_high", "cohort_salary_low", "cohort_size",
}

SALARY_CONVENTIONS = {
    "salary_base", "salary_base_plus_prorated_bonus",
    "salary_base_plus_bonuses_nflpa", "club_cost_per_player",
    "qualifying_offer",
    "signing_bonus", "roster_bonus", "reporting_bonus", "base_salary_year",
    "option_year_pay", "performance_incentive", "additional_compensation",
    "amount_actually_paid", "total_earnings_year", "contract_total_stated",
}

# Anything that LOOKS like money must be one of the declared conventions. Without
# this an undeclared name (e.g. `amount_actually_paid` before it was declared)
# sails past the bare-name check and lands in the store unclassified.
_ALL_MONEY = None
MONEY_SHAPED = re.compile(
    r"(salary|bonus|pay|wage|compensation|earnings|cost|fee|money|contract_total)",
    re.I)
FORBIDDEN_KINDS = {"invented"}
ACQ_ALLOWED = {"fetched", "held", "transcribed"}
ACQ_FORBIDDEN = {"relayed"}


class StoreError(Exception):
    pass


class Store:
    def __init__(self):
        self.sources = {}          # source_id -> declaration dict
        self.source_records = {}   # sr_id -> {source_id, locator}
        self.persons = set()       # opaque ids only. NO attributes.
        self.claims = []           # list of dicts
        self.denotations = []
        self.universe = set()   # subjects that EXIST, claimed or not
        self._by_subject = defaultdict(list)
        self._seq = 0

    # ---- ids -------------------------------------------------------------
    def _mint(self, prefix):
        self._seq += 1
        return f"{prefix}_{self._seq:06d}"

    def mint_person(self):
        pid = self._mint("p")
        self.persons.add(pid)
        return pid

    # ---- sources ---------------------------------------------------------
    def add_source(self, decl):
        acq = decl.get("acquisition")
        if acq in ACQ_FORBIDDEN:
            raise StoreError(
                f"source {decl['source_id']}: acquisition '{acq}' may never enter "
                f"the store. It is a lead, not a source (design 3.7).")
        if acq not in ACQ_ALLOWED:
            raise StoreError(f"source {decl['source_id']}: unknown acquisition '{acq}'")
        self.sources[decl["source_id"]] = decl
        return decl["source_id"]

    def add_source_record(self, source_id, locator):
        if source_id not in self.sources:
            raise StoreError(f"no such source: {source_id}")
        sr = f"{source_id}#{locator}"
        self.source_records[sr] = {"source_id": source_id, "locator": locator}
        return sr

    # ---- claims ----------------------------------------------------------
    def add_claim(self, source_record, subject, predicate, value, observed_at,
                  kind="observed", stated_by=None, attribution=None, note=None):
        if kind in FORBIDDEN_KINDS:
            raise StoreError(f"kind '{kind}' has no field to occupy. It belongs in a build.")
        scope = subject[0] if isinstance(subject, (tuple, list)) and subject else None
        if predicate in SYSTEM_PREDICATES and scope not in LEAGUE_SCOPES:
            raise StoreError(
                f"'{predicate}' is a SYSTEM rule and requires a league-scoped subject "
                f"({sorted(LEAGUE_SCOPES)}), not '{scope}'. It describes how the system "
                f"worked, not what a person was paid.")
        if predicate in COHORT_PREDICATES and scope not in COHORT_SCOPES:
            raise StoreError(
                f"'{predicate}' describes a COHORT and requires a cohort-scoped "
                f"subject, not '{scope}'. A positional average is not a person's pay.")
        if predicate in SALARY_CONVENTIONS and scope in COHORT_SCOPES:
            raise StoreError(
                f"'{predicate}' is a person-scoped money predicate and cannot take a "
                f"cohort subject. Use a cohort_* predicate for an aggregate.")
        if predicate in SALARY_CONVENTIONS and scope in LEAGUE_SCOPES:
            raise StoreError(
                f"'{predicate}' is a person-scoped money predicate and cannot take a "
                f"league-scoped subject. A league aggregate is its own predicate.")
        if (MONEY_SHAPED.search(predicate) and predicate not in SALARY_CONVENTIONS
                and predicate not in SYSTEM_PREDICATES
                and predicate not in COHORT_PREDICATES
                and predicate not in BARE_MONEY_PREDICATES):
            raise StoreError(
                f"'{predicate}' looks like money but is not a declared convention. "
                f"Add it to declarations/salary_conventions.json with its definition, "
                f"or use one of {sorted(SALARY_CONVENTIONS)}.")
        if predicate in BARE_MONEY_PREDICATES:
            raise StoreError(
                f"predicate '{predicate}' is REFUSED: a money figure must name its "
                f"convention. Use one of {sorted(SALARY_CONVENTIONS)} - see "
                f"declarations/salary_conventions.json.")
        if kind not in KINDS:
            raise StoreError(f"unknown kind '{kind}'")
        if source_record not in self.source_records:
            raise StoreError(f"claim without a resolvable source_record: {source_record}")
        src = self.sources[self.source_records[source_record]["source_id"]]
        c = {
            "id": self._mint("c"),
            "source_record": source_record,
            "source_id": src["source_id"],
            "subject": subject,
            "predicate": predicate,
            "value": value,
            "observed_at": observed_at,
            "kind": kind,
            "stated_by": stated_by if stated_by is not None else src.get("stated_by"),
            "attribution": list(attribution if attribution is not None
                                else src.get("attribution", [])),
            "note": note,
        }
        self.claims.append(c)
        self._by_subject[(subject, predicate)].append(c)
        return c["id"]

    def add_absence(self, source_record, subject, predicate, observed_at, note=None):
        """The source has the column / would have carried it, and does not."""
        return self.add_claim(source_record, subject, predicate, None, observed_at,
                              kind="absent", note=note)

    # ---- denotations -----------------------------------------------------
    def add_denotation(self, source_record, person, discriminator, method,
                       matched_against=None, status="asserted", note=None):
        if status == "asserted" and person not in self.persons:
            raise StoreError(f"denotation to unknown person {person}")
        if status == "asserted" and not discriminator:
            raise StoreError("a denotation must record what separated it")
        d = {
            "id": self._mint("d"),
            "source_record": source_record,
            "person": person,
            "discriminator": list(discriminator),
            "method": method,
            # WHICH source's value the match was made against. A contested
            # discriminator is inherited by the denotation resting on it.
            "matched_against": matched_against,
            "status": status,
            "note": note,
        }
        self.denotations.append(d)
        return d["id"]

    # ---- resolution ------------------------------------------------------
    def resolve(self, subject, predicate, policy):
        """Pure. Returns basis + value + the claims that produced it, winners and losers."""
        cs = self._by_subject.get((subject, predicate), [])
        if not cs:
            return {"subject": subject, "predicate": predicate, "value": None,
                    "basis": "unknown", "rule": "no claims",
                    "winning": [], "losing": [], "policy": policy["version"]}

        eligible = [c for c in cs if self._eligible(c, predicate, policy)]
        positive = [c for c in eligible if c["kind"] != "absent"]
        absences = [c for c in eligible if c["kind"] == "absent"]

        if not positive:
            return {"subject": subject, "predicate": predicate, "value": None,
                    "basis": "absent" if absences else "unknown",
                    "rule": "only absence claims" if absences else "no eligible claims",
                    "winning": [c["id"] for c in absences], "losing": [],
                    "policy": policy["version"]}

        # SET-VALUED predicates union within a lineage group rather than competing.
        if predicate in policy.get("set_valued", []):
            by_group = defaultdict(list)
            for c in positive:
                by_group[self._lineage_group(c)].append(c)
            sets = {g: tuple(sorted({json.dumps(c["value"], sort_keys=True) for c in cs}))
                    for g, cs in by_group.items()}
            distinct = set(sets.values())
            if len(distinct) == 1:
                vals = [json.loads(v) for v in next(iter(distinct))]
                return {"subject": subject, "predicate": predicate,
                        "value": vals if len(vals) > 1 else vals[0],
                        "basis": "observed",
                        "rule": "set-valued, union within lineage group",
                        "winning": [c["id"] for c in positive], "losing": [],
                        "policy": policy["version"]}
            return {"subject": subject, "predicate": predicate, "value": None,
                    "basis": "contested",
                    "rule": "set-valued, lineage groups hold different sets",
                    "winning": [], "losing": [c["id"] for c in positive],
                    "candidates": [{"value": [json.loads(v) for v in s],
                                    "stated_by": by_group[g][0]["stated_by"],
                                    "attribution": by_group[g][0]["attribution"]}
                                   for g, s in sets.items()],
                    "policy": policy["version"]}

        # group by value; a claim with a non-empty attribution votes only in
        # stated_by's group, never the attributed party's.
        groups = defaultdict(list)
        for c in positive:
            groups[json.dumps(c["value"], sort_keys=True)].append(c)

        if len(groups) == 1:
            win = positive
            return {"subject": subject, "predicate": predicate,
                    "value": win[0]["value"], "basis": "observed",
                    "rule": "uncontested", "winning": [c["id"] for c in win],
                    "losing": [], "policy": policy["version"]}

        ranked = sorted(groups.items(),
                        key=lambda kv: self._rank(kv[1], policy), reverse=True)
        top, second = ranked[0], ranked[1]
        if self._rank(top[1], policy) > self._rank(second[1], policy):
            losers = [c["id"] for k, g in ranked[1:] for c in g]
            return {"subject": subject, "predicate": predicate,
                    "value": top[1][0]["value"], "basis": "observed",
                    "rule": self._rule_name(top[1], policy),
                    "winning": [c["id"] for c in top[1]], "losing": losers,
                    "policy": policy["version"]}

        return {"subject": subject, "predicate": predicate, "value": None,
                "basis": "contested", "rule": "no eligible rule separates the claims",
                "winning": [], "losing": [c["id"] for g in groups.values() for c in g],
                "candidates": [{"value": g[0]["value"],
                                "stated_by": g[0]["stated_by"],
                                "attribution": g[0]["attribution"]} for g in groups.values()],
                "policy": policy["version"]}

    # ---- policy helpers --------------------------------------------------
    def _eligible(self, c, predicate, policy):
        key = f"{c['source_id']}|{predicate}"
        ex = policy.get("excluded", [])
        return key not in ex and c["source_id"] not in ex

    def _lineage_group(self, c):
        """Independence key. Attribution collapses a claim into stated_by's group."""
        src = self.sources.get(c["source_id"], {})
        root = src.get("derived_from") or c["source_id"]
        return (root, c["stated_by"])

    def _rank(self, group, policy):
        tiers = policy["tiers"]
        best = 0
        for c in group:
            if c["kind"] == "derived":
                t = tiers.get("derived", 2)
            elif c["stated_by"] in policy.get("human_verdict_by", []):
                t = tiers["human"]
            elif c["kind"] == "source_derived":
                t = tiers.get("source_derived", 2)
            else:
                t = tiers.get("observed", 3)
            best = max(best, t)
        # independent lineage groups add weight WITHIN a tier, never across one
        n_ind = len({self._lineage_group(c) for c in group})
        return best * 1000 + min(n_ind, 999)

    def _rule_name(self, group, policy):
        if any(c["stated_by"] in policy.get("human_verdict_by", []) for c in group):
            return "human verdict terminates resolution"
        n = len({self._lineage_group(c) for c in group})
        return f"{n} independent lineage group(s)" if n > 1 else "single source"

    # ---- persistence -----------------------------------------------------
    def declare_subject(self, subject):
        """A subject EXISTS. Without this, `unknown` is unreachable by construction:
        a distribution computed over subjects-that-have-claims can never report it."""
        self.universe.add(tuple(subject))

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump({"persons": sorted(self.persons),
                   "universe": sorted((list(x) for x in self.universe), key=lambda v: [str(i) for i in v]),
                   "source_records": self.source_records,
                   "claims": self.claims,
                   "denotations": self.denotations},
                  open(path, "w"), indent=1, sort_keys=True)
