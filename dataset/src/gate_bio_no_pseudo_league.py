"""Gate: no bio prints a token declared not to be a competition, and no bio asserts a lineage
the archive holds as unknown. Ryan's ruling of 2026-09-11, on how an independent season reads:
say what the archive knows -- the club played that season outside any league, and whether it is
the same club as the league entry is unknown.

  B1  no rendered bio contains a declared non-competition token as a word. The tokens are READ
      from declarations/person-index-rebuild.json `pseudo_league_tokens`, never typed here.
      96 served bios printed `IND` as a league before the fix.
  B2  no rendered bio says "a new <club>" -- a denial of a lineage the club table holds as
      unknown. 33 did.

The population is every man who can print either: anyone holding a season under a declared
non-competition token, in either dict, and anyone whose playing seasons span two or more league
families (the only men the crossed-leagues lead, which wrote "a new", can reach). Derived from
the index each run; no man is named here.

  python3 src/gate_bio_no_pseudo_league.py              exit 1 = FAIL
  python3 src/gate_bio_no_pseudo_league.py --self-test  proves it can fail
"""
import os, re, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
FAILS = []
PSEUDO = sorted(json.load(open(os.path.join(BASE, "declarations", "person-index-rebuild.json")))
                ["pseudo_league_tokens"]["tokens"])
TOKEN = re.compile(r"\b(" + "|".join(map(re.escape, PSEUDO)) + r")\b")
A_NEW = re.compile(r"\ba new\b")


def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: FAILS.append(msg)


def judge(texts):
    """texts: {pid: prose}. The properties, applied to whatever prose is handed in."""
    tok = {p: sorted(set(TOKEN.findall(t))) for p, t in texts.items() if t and TOKEN.search(t)}
    new = [p for p, t in texts.items() if t and A_NEW.search(t)]
    err = [p for p, t in texts.items() if str(t).startswith("ERROR")]
    check(not err, f"B0 every bio in the population renders ({len(texts)} rendered; {len(err)} raised: {err[:3]})")
    check(not tok, f"B1 no bio prints a declared non-competition token {PSEUDO} ({len(tok)} do: "
                   f"{[(p, tok[p], texts[p][:120]) for p in list(tok)[:3]]})")
    check(not new, f"B2 no bio says 'a new <club>' ({len(new)} do: {[(p, texts[p][:120]) for p in new[:3]]})")


def population():
    from bio_write import LEAGUE_FAMILY
    idx = json.load(open(os.path.join(BASE, "build-reports", "person-index.json"))); idx.pop("_clubs", None)
    out = set()
    for pid, r in idx.items():
        if not isinstance(r, dict): continue
        keys = list((r.get("seasons") or {})) + list((r.get("coaching_seasons") or {}))
        if any(k.split("|")[0] in PSEUDO for k in keys): out.add(pid)
        fams = {LEAGUE_FAMILY.get(k.split("|")[0], k.split("|")[0]) for k in (r.get("seasons") or {})}
        if len(fams) >= 2: out.add(pid)
    return out


def main():
    import bio_select as bs, bio_write as bw
    pop = population()
    T = bs.Tables()
    texts = {}
    for pid in sorted(pop & set(T.people)):
        try: texts[pid] = bw.write(bs.select(T, pid))
        except Exception as e: texts[pid] = "ERROR " + repr(e)[:200]
    print(f"population: {len(pop)} men who could print a non-competition token or 'a new'; {len(texts)} hold a bio")
    if not texts:
        print("REFUSED: nothing rendered. An empty denominator is not a pass."); sys.exit(2)
    judge(texts)
    print("\nGATE PASSED" if not FAILS else f"\nGATE FAILED ({len(FAILS)})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        judge({"P_A": "Dick Abrell's career crossed leagues: IND with the Dayton Triangles (1919).",
               "P_B": "He played for the NFL with a new Dayton Triangles (1920).",
               "P_C": "ERROR ValueError()"})
        ok = len(FAILS) == 3
        print("self-test:", "the gate fails when it should" if ok else "SELF-TEST DID NOT FAIL -- the gate proves nothing")
        sys.exit(0 if ok else 1)
    sys.exit(main())
