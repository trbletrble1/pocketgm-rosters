"""Predicate families: which predicates ask the same question. Read from
declarations/predicate-families.json; nothing here is a literal."""
import json, os
import paths

_PATH = os.path.join(paths.SERVICE_DECLARATIONS, "predicate-families.json")


def load():
    d = json.load(open(_PATH))
    fam = {}
    for name, spec in d["families"].items():
        for p in spec["predicates"]:
            if p in fam:
                raise ValueError(f"predicate {p} declared in two families: {fam[p]} and {name}")
            fam[p] = name
    return {"families": d["families"], "of": fam, "raw": d}


_F = None
def get():
    global _F
    if _F is None: _F = load()
    return _F


def family_of(predicate):
    """The family a predicate belongs to, or the predicate itself: a family of one."""
    return get()["of"].get(predicate, predicate)


def kind_of(family):
    return get()["families"].get(family, {}).get("kind", "value")


def date_predicates():
    return {p for f, spec in get()["families"].items() if spec.get("kind") == "date" for p in spec["predicates"]}
