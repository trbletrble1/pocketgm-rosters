"""A COACHING-ONLY BIO IS ITS OWN SHAPE. Ruled by Ryan, 2026-09-09.

A man who only ever coached is not a player with the playing part missing. He gets
a lead written for the career he had, and it holds every discipline the playing
bios hold.

WHY A GATE. On 2026-09-09, 997 of the 2,138 coaching-only men returned 503 from
`get_bio`: `bio_select` chose a lead fact -- `coached_one_season`, `coached_long`,
`coached_one_club`, `coached_across_leagues` -- that the writer had no branch for,
so it fell through to `coach_lead`, which reads a key only the head-coach fact
carries. The shapes had been worked out; nothing had ever matched them. A property
over every coaching-only man is the only thing that would have seen it, because each
individual bio looked fine until you asked for one of the 997.

  P1  every coaching-only man in the bio corpus renders. No exceptions, no sampling.
  P2  every bio is a finished sentence: it ends in a full stop, has no empty or
      doubled punctuation, and never trails "as ." where a role was missing.
  P3  the lead matches the career. A head coach leads on the head job; a man who
      never held one leads on what he did; a career with no shape leads on the
      career. Reading a head-coach lead for a man with no head job is how this
      broke.
  P4  it does not invent a season. Where the lead states a number of seasons it is
      the number he coached, not the distance between his first year and his last:
      Gord Ackerman was away in 1964, and the lead said ten where the next sentence
      said nine.
  P5  it says what it does not know. A man no source gives a role for is not given
      one, and the bio says so rather than leaving the sentence bare.

    python3 src/gate_coaching_only_bios.py [--selftest]
"""
import os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


BAD_PUNCT = re.compile(r",,|\s,|\s\s|\bas\s*\.|—\s*\.|:\s*\.")


def audit(T, BS, BW, ids):
    """-> (violations by property, examples). Pure over the ids given, so the
    self-test can run it on a handful and main() on every man."""
    v = collections.Counter(); ex = collections.defaultdict(list)
    def note(k, item):
        v[k] += 1
        if len(ex[k]) < 4: ex[k].append(item)
    for g in ids:
        name = (T.people[g].get("name") or g)
        try:
            F = BS.select(T, g)
        except Exception as e:
            note("P1 select raised", (g, name, f"{type(e).__name__}: {e}")); continue
        if not F:
            note("P1 no bio at all", (g, name)); continue
        try:
            t = BW.write(F)
        except Exception as e:
            note("P1 the writer raised", (g, name, f"{type(e).__name__}: {e}")); continue
        if not t or not t.strip().endswith("."):
            note("P2 the bio does not end in a full stop", (g, name, (t or "")[-60:]))
        if BAD_PUNCT.search(t or ""):
            note("P2 empty or doubled punctuation", (g, name, BAD_PUNCT.search(t).group(0), t[:80]))
        lead = F["facts"][0]
        co = (F["facts"][1] or {}).get("coaching") if len(F["facts"]) > 1 else None
        if co is not None:
            head = bool(co["was_head_coach"])
            kind = lead["kind"]
            want = "head_coach_career" if head else ("assistant_career", "coaching_career")
            ok = kind == want if head else kind in want
            if not ok: note("P3 the lead does not match the career", (g, name, kind, f"head={head}"))
            years = {y for r in co["runs"] for y in r["years"]}
            span = co["last_year"] - co["first_year"] + 1
            if len(years) != span:
                m = re.search(r"coached ([a-z\- ]+) seasons", t or "")
                if m and _word(m.group(1)) == span:
                    note("P4 the lead calls the span a season count", (g, name, span, len(years), t[:90]))
            if not co.get("role_as_printed") and t and "listed as" in t:
                note("P5 a role appears where no source gives one", (g, name, t[:90]))
    return v, ex


_W = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}


def _word(s):
    s = s.strip().replace("-", " ")
    if s in _W: return _W[s]
    parts = s.split()
    if len(parts) == 2 and parts[0] in ("twenty", "thirty", "forty", "fifty") and parts[1] in _W:
        return {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}[parts[0]] + _W[parts[1]]
    return None


def main(argv):
    if "--selftest" in argv: return selftest()
    import bio_select as BS, bio_write as BW
    T = BS.Tables()
    ids = [g for g, p in T.people.items() if p.get("coaching_seasons") and not p.get("seasons")]
    v, ex = audit(T, BS, BW, ids)
    print(f"COACHING-ONLY BIOS  ({len(ids):,} men in the bio corpus)")
    lead = collections.Counter()
    for g in ids:
        F = BS.select(T, g)
        if F: lead[F["facts"][0]["kind"]] += 1
    print("  leads: " + ", ".join(f"{k} {n:,}" for k, n in lead.most_common()))
    for prop in ("P1 select raised", "P1 no bio at all", "P1 the writer raised",
                 "P2 the bio does not end in a full stop", "P2 empty or doubled punctuation",
                 "P3 the lead does not match the career",
                 "P4 the lead calls the span a season count",
                 "P5 a role appears where no source gives one"):
        check(v[prop] == 0, f"{prop}: {v[prop]:,}" + (f"  e.g. {ex[prop][:2]}" if v[prop] else ""))
    if FAILS:
        print(f"\nCOACHING-ONLY BIO GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nCOACHING-ONLY BIO GATE: pass"); return 0


def selftest():
    """Every property, shown failing on a fixture built to break it."""
    class T:  # a corpus of one
        def __init__(self, name): self.people = {"P_1": {"name": name, "coaching_seasons": {"NFL|1980|CHI": {}}}}
    CO = {"was_head_coach": False, "role_as_printed": "Safeties", "runs": [{"years": {1980, 1982}}],
          "first_year": 1980, "last_year": 1982, "first": 1980, "last": 1982, "seasons": 2, "roles_varied": False}
    def mk(text, kind="assistant_career", co=None, raise_write=False, none=False):
        class BS:
            @staticmethod
            def select(T, g):
                return None if none else {"facts": [{"kind": kind}, {"coaching": co if co is not None else CO}]}
        class BW:
            @staticmethod
            def write(F):
                if raise_write: raise KeyError("coaching")
                return text
        return BS, BW
    cases = [
        ("the shape as ruled", *mk("P coached from 1980 to 1982 with the Bears, listed as Safeties."), []),
        ("the writer raises (the 997)", *mk("", raise_write=True), ["P1 the writer raised"]),
        ("no bio at all", *mk("", none=True), ["P1 no bio at all"]),
        ("truncated, no full stop", *mk("P coached from 1980 to 1982 with the Bears"), ["P2 the bio does not end in a full stop"]),
        ("a doubled comma", *mk("P coached with the Bears,, listed as Safeties."), ["P2 empty or doubled punctuation"]),
        ("a bare 'as .' where the role was missing", *mk("P coached with the Bears, as ."), ["P2 empty or doubled punctuation"]),
        ("a head-coach lead for a man with no head job",
         *mk("P was Head Coach of the Bears.", kind="head_coach_career"), ["P3 the lead does not match the career"]),
        ("the span called a season count",
         *mk("P coached three seasons, 1980 to 1982, with the Bears."), ["P4 the lead calls the span a season count"]),
        ("a role invented where none is held",
         *mk("P coached with the Bears, listed as Safeties.",
             co=dict(CO, role_as_printed=None)), ["P5 a role appears where no source gives one"]),
    ]
    ok = True
    for label, BS, BW, want in cases:
        v, ex = audit(T("P"), BS, BW, ["P_1"])
        got = sorted(k for k, n in v.items() if n)
        good = got == sorted(want); ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected {sorted(want)}, got {got}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
