"""How a store's declaration in `store_league_tokens` names a league -- ONE implementation.

The declaration is prose, written for a person:

    "assistants":        "COACHES -- the media guides' staff lists are coaching seasons..."
    "pfa-stats-1920s":   "NOT A LEAGUE -- these are person-scoped statistic claims..."

Both were read as `v.split(" ")[0]`, so the second declared a league called `NOT`.
Twelve stores say "NOT A LEAGUE" and every one of them got it; by 2026-09-08 `NOT`
was the largest league in the archive -- 132,038 stint keys against the NFL's
114,369 -- and nothing was wrong with the declaration. It reads correctly to a
person and wrongly to a parser.

Ryan's ruling, 2026-09-08: change the splitting rule, not the prose. A declaration
that reads correctly to a person should not have to be written for a parser.

THE RULE. Every entry is `<lead-in> -- <reason>`. The lead-in names a token only if
it is a SINGLE WORD. "NOT A LEAGUE" is three words and names nothing, so the store
declares no league of its own and its claims' league comes from the season key on
the subject -- which is exactly where each of those declarations already says a
consumer must look.

This module exists so there is one implementation. There were two, in
service/build_read_model.py and src/build_person_index.py, and they agreed only
because they were the same wrong line copied twice.
"""
import os, json

SEP = "--"


def lead_in(v):
    """The text before the reason. `None` if the value is not a declaration sentence."""
    if not isinstance(v, str):
        return None
    return v.split(SEP, 1)[0].strip() if SEP in v else v.strip()


def token(v):
    """The league token a declaration names, or None if it names none.

    >>> token("COACHES -- the media guides' staff lists are coaching seasons")
    'COACHES'
    >>> token("NOT A LEAGUE -- these are person-scoped statistic claims") is None
    True
    >>> token("IND -- NOT A LEAGUE. Frankford's 1922 and 1923 independent seasons")
    'IND'
    """
    t = lead_in(v)
    if not t:
        return None
    return t if len(t.split()) == 1 else None


def tokens(decl_path):
    """{store: token or None} for every declared store. A store mapped to None has
    DECLARED that it has no league, which is different from not being declared."""
    d = json.load(open(decl_path)) if os.path.exists(decl_path) else {}
    return {k: token(v) for k, v in (d.get("store_league_tokens") or {}).items()
            if not k.startswith("_")}


def declared_non_leagues(decl_path):
    """Single-word tokens that are deliberately NOT competitions -- COACHES, IND,
    DRAFT. Each is declared with its reason. The gate exempts these and nothing else."""
    return {t for t in tokens(decl_path).values() if t}


_LABELS = None


def _labels_by_year():
    """declarations/clubs.json LEAGUE_LABELS_BY_YEAR -- REQUIRED. An absent declaration
    must not read as "no labels to map": that is how a missing input becomes a confident
    wrong answer, and here it would put the 2022 USFL back in 1983's league."""
    global _LABELS
    if _LABELS is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "declarations", "clubs.json")
        d = json.load(open(p))
        if "LEAGUE_LABELS_BY_YEAR" not in d:
            raise SystemExit("declarations/clubs.json declares no LEAGUE_LABELS_BY_YEAR. Refusing to "
                             "read season keys without it: a label and a league are not the same thing.")
        _LABELS = [(x["label"], int(x["first"]), int(x.get("last") or 9999), x["token"])
                   for x in d["LEAGUE_LABELS_BY_YEAR"]["labels"]]
    return _LABELS


def read_label(label, year):
    """The archive's token for a league LABEL a source prints in a given YEAR.

    A LEAGUE ABBREVIATION IS NOT A LEAGUE, BUT AN ABBREVIATION AND A YEAR CAN BE. `USFL`
    names the 1983-85 league and the 2022-23 one; `UFL` the 2009-12 league and the 2024 one.
    PFA prints the bare label for both, so its 2022 claims were keyed to 1983's competition
    and every 2022-24 club-season was held twice -- `USFL|2022|US2BIS` beside
    `USFL2|2022|US2BIS`. Ryan's ruling, 2026-09-11: read the label with its year, at read
    time, and never rewrite the store. Declared, one entry per label and span."""
    for lab, first, last, tok in _labels_by_year():
        if label == lab and year is not None and first <= year <= last:
            return tok
    return label


def from_season_key(key, real_leagues=None):
    """A stint subject's season key carries its own league: `APFA-1920` -> `APFA`.
    Used where the store has declared it has no league. Returns None rather than a
    guess when the leading token is not a league the club table holds.

    The label is read WITH ITS YEAR (read_label): `USFL-2022` -> `USFL2`."""
    if not isinstance(key, str) or "-" not in key:
        return None
    t = key.split("-")[0].strip().upper()
    if not t:
        return None
    y = key.rsplit("-", 1)[-1].strip().lstrip("y")[:4]
    t = read_label(t, int(y) if y.isdigit() else None)
    if real_leagues is not None and t not in real_leagues:
        return None
    return t


def store_league(st, declared, real_leagues=None):
    """The league for a store: its declaration if it has one, else the filename's
    first token. `None` means the store declares it has no league of its own."""
    base = st[6:] if st.startswith("stats-") else st
    if base in declared:
        return declared[base]
    return base.split("-")[0].upper()


def pseudo_leagues(decl_path):
    """The declared single-word tokens that are NOT competitions -- COACHES, SALARIES,
    IND, DRAFT. Read from `pseudo_league_tokens` in the rebuild declaration, never
    typed. Four files used to carry `("COACHES", "SALARIES")` as a literal and none of
    them gained IND when IND was declared, so 69 season keys handed the club resolver a
    token the club table does not hold."""
    d = _load(decl_path) if "_load" in globals() else __import__("json").load(open(decl_path))
    return frozenset(d["pseudo_league_tokens"]["tokens"])
