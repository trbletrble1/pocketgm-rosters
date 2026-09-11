"""PFA's own player code -- who holds it, and how to read it off a page. ONE implementation.

Read by ingest_pfa_club_rosters.py (to place a lead by code), promote_players.py (to
promote a lead as a new person only where nobody holds his code) and
gate_code_identity.py (to hold both). A gate with its own copy of this rule would test
the copy.

WHERE A CODE LIVES IN THE ARCHIVE. Two places, both read:
  * a claim's source_record, `pro-football-archives#players/m/murp03750.html` -- every
    fact read off a PFA player page. Three records sit one level deeper
    (`players/s/b/beso00200.html`); the pattern allows it, and anything else that
    claims to be a PFA player page and does not match is REFUSED, loudly, rather than
    dropped -- a dropped holder is a code "held by nobody" and a duplicate person.
  * the value of the two predicates that carry the code as a field:
    `pfa.roster_membership` and, since 2026-09-11, `pfa.club_roster_line`.
"""
import re, json, collections

SR = re.compile(r"^pro-football-archives#players/(?:[a-z]/)+([a-z0-9]+)\.html$")
ROW_LINK = re.compile(r'href="/?players/(?:[a-z]/)+([a-z0-9]+)\.html"', re.I)
CODE_PREDICATES = ("pfa.roster_membership", "pfa.club_roster_line")


def code_in_row(tr_html):
    """The PFA player code a roster row links its name to, or None."""
    m = ROW_LINK.search(tr_html or "")
    return m.group(1) if m else None


def holders(conn, exclude_stores=()):
    """-> {code: {person, ...}} from the read model. `exclude_stores` lets a decider
    leave out its own output (a decider that reads its own output decides nothing)."""
    out = collections.defaultdict(set)
    ex = set(exclude_stores)
    bad = []
    for person, store, sr in conn.execute(
            "SELECT DISTINCT person, store, source_record FROM claim WHERE person IS NOT NULL "
            "AND source_record LIKE 'pro-football-archives#players/%'"):
        if store in ex: continue
        m = SR.match(sr)
        if m: out[m.group(1)].add(person)
        else: bad.append(sr)
    if bad:
        raise SystemExit(f"{len(bad)} PFA player-page records match no code shape, e.g. "
                         f"{bad[:3]}. Refusing: a holder dropped here reads as a code nobody holds.")
    q = ("SELECT person, store, value FROM claim WHERE person IS NOT NULL AND predicate IN (%s)"
         % ",".join("?" * len(CODE_PREDICATES)))
    for person, store, value in conn.execute(q, CODE_PREDICATES):
        if store in ex: continue
        try: v = json.loads(value) if isinstance(value, str) else value
        except ValueError: continue
        c = v.get("pfa_code") if isinstance(v, dict) else None
        if c: out[c].add(person)
    return out


def codes_of(hold):
    """-> {person: {code, ...}}, the inverse of holders()."""
    inv = collections.defaultdict(set)
    for c, ps in hold.items():
        for p in ps: inv[p].add(c)
    return inv
