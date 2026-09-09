"""A BIO MUST NOT PRINT A CLUB TOKEN THE ARCHIVE CAN NAME. Ruled by Ryan, 2026-09-09.

Les Dodson's bio read "two games with the PFA:WIL in 1941". The club table names
that club -- Wilmington Clippers, code PFA:WIL, 1938 to 1941 -- and the bio printed
the raw season-key token because it was naming clubs from a different map.

THE PROPERTY. For every man in the bio corpus, take the club tokens on his season
keys, keep the ones the CLUB TABLE can name for that year, and assert that none of
those literal strings appears in his bio. A token the archive genuinely cannot name
is allowed through and counted: the bio says what the archive holds, and inventing
a name for a club-season the table does not cover would be the worse failure.

WHY A PROPERTY AND NOT A SPOT CHECK. The map that used to name clubs came from ONE
store -- StatsCrew's roster-page titles, 3,666 claims, 321 tokens, no PFA codes at
all -- and it named 204,931 season keys correctly. Every bio built on those looked
perfect. The 13,020 it could not name were spread across 3,755 men, and no sample
small enough to read was likely to contain one.

    python3 src/gate_bio_club_names.py [--selftest]
"""
import os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

FAILS = []


def check(ok, msg):
    print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    if not ok: FAILS.append(msg)
    return ok


def nameable(C, p):
    """{token: (year, name)} for every club token on this man's season keys that the
    club table names for EVERY year he holds it, and whose text a reader could tell
    apart from the name.

    THREE THINGS ARE SKIPPED, AND COUNTED RATHER THAN PASSED:

      a token the table names in one of his years and not another -- `HOU` is the
        Houston Oilers in 1994 and nothing in 1984, because the table's HOU segment
        does not reach back that far. The bio prints the token for the 1984 season
        and the name for the 1994 one, and no text test can tell which occurrence it
        is looking at. The right answer there is to extend the club table, not to
        make the bio guess;
      a token that is a WORD of its own name -- `BC` names the BC Lions, so "the BC
        Lions" contains it;
      a token that IS its own name -- some sources print `Dallas Cowboys` as the
        season-key token, and a bio naming the club correctly contains it.

    A gate that says nothing about a case is not the same as a gate that clears it,
    so main() prints how many fall into each."""
    years = collections.defaultdict(set)
    for k in list(p.get("seasons") or {}) + list(p.get("coaching_seasons") or {}):
        parts = k.split("|", 2)
        if len(parts) != 3: continue
        lg, y, tok = parts
        yr = str(y).lstrip("y")
        if yr.isdigit(): years[tok].add(int(yr))
    out, skipped, sk_toks = {}, {}, set()
    for tok, ys in years.items():
        names = {}
        for y in sorted(ys):
            r = C.resolve(tok, y, None, source="season_key")
            names[y] = C.name_for(r[0], y) if r else None
        if not any(names.values()): continue                  # the archive cannot name it at all
        if not all(names.values()):
            skipped["mixed"] = skipped.get("mixed", 0) + 1; sk_toks.add(tok); continue
        nm = names[min(ys)]
        if norm_txt(tok) == norm_txt(nm):
            skipped["token is the name"] = skipped.get("token is the name", 0) + 1; sk_toks.add(tok); continue
        if tok.upper() in {w.upper() for w in re.split(r"[\s/-]+", nm)}:
            skipped["token is a word of the name"] = skipped.get("token is a word of the name", 0) + 1; sk_toks.add(tok); continue
        out[tok] = (min(ys), nm)
    return out, skipped, sk_toks


def norm_txt(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def audit(C, people, bio_of):
    """-> (violations, examples, tokens the archive cannot name, tokens skipped).
    `bio_of(pid)` returns the bio text or None."""
    v = 0; ex = []; unnameable = collections.Counter(); skipped = collections.Counter()
    for pid, p in people.items():
        t = bio_of(pid)
        if not t: continue
        ok, sk, sk_toks = nameable(C, p)
        skipped.update(sk)
        for tok, (yr, nm) in ok.items():
            if re.search(r"(?<![\w:-])" + re.escape(tok) + r"(?![\w:-])", t):
                v += 1
                if len(ex) < 5: ex.append((pid, tok, yr, nm, t[:110]))
        for k in list(p.get("seasons") or {}) + list(p.get("coaching_seasons") or {}):
            parts = k.split("|", 2)
            if len(parts) == 3 and parts[2] not in ok and parts[2] not in sk_toks:
                unnameable[parts[2]] += 1
    return v, ex, unnameable, skipped


def main(argv):
    if "--selftest" in argv: return selftest()
    import bio_select as BS, bio_write as BW
    from clubs import Clubs
    C = Clubs(); T = BS.Tables()
    def bio_of(pid):
        try:
            F = BS.select(T, pid)
            return BW.write(F) if F else None
        except Exception:
            return None
    v, ex, un, skipped = audit(C, T.people, bio_of)
    print(f"BIO CLUB NAMES  ({len(T.people):,} men in the bio corpus)")
    check(v == 0, f"bios printing a club token the archive CAN name: {v:,}"
                  + (f"  e.g. {ex[:2]}" if v else ""))
    print(f"  INFORMATION: club tokens the archive cannot name, left as printed: "
          f"{sum(un.values()):,} season keys across {len(un)} tokens; worst {un.most_common(5)}")
    print(f"  INFORMATION: (token, man) pairs no text test can judge: {sum(skipped.values()):,} "
          f"-- {dict(skipped)}")
    if FAILS:
        print(f"\nBIO CLUB NAME GATE: {len(FAILS)} FAILURE(S)"); return 1
    print("\nBIO CLUB NAME GATE: pass"); return 0


def selftest():
    class C:
        @staticmethod
        def resolve(tok, yr, *a, **k): return ("club-x", "code") if tok == "PFA:WIL" else None
        @staticmethod
        def name_for(cid, yr): return "Wilmington Clippers"
    people = {"P_1": {"seasons": {"AA|1941|PFA:WIL": {}, "NFL|1941|PIT": {}}}}
    cases = [("the club is named", "Les Dodson played for the Wilmington Clippers in 1941.", 0),
             ("the raw token is printed", "Les Dodson's career was two games with the PFA:WIL in 1941.", 1),
             ("a token the table cannot name is allowed", "Les Dodson played for the PIT in 1941.", 0),
             ("the token inside a longer word is not a hit", "He coached the PFA:WILDCATS in 1941.", 0)]
    ok = True
    for label, text, want in cases:
        v, ex, un, _sk = audit(C, people, lambda pid, t=text: t)
        good = v == want; ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: expected {want}, got {v}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
