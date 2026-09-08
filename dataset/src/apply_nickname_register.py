"""One man under two printed names, recorded per man.

NOT A READING. No string operation turns `Blood` into `McNally` or `Bruiser` into
`Frank`. A reading is a function from a printed string to a fact; there is no such
function here, and building one would mean inventing it and then applying it to
strings nobody has looked at.

A RECORDED DECISION, the shape of a merge: the two names, the club-season that
establishes them as one man, and the source that printed each.

BOTH NAMES GO ON THE PERSON AND NEITHER IS CANONICAL. `Bruiser` is what the club
called him; `Frank` is what his birth certificate said. Neither corrects the other,
neither is filed under the other, and search must find him by either.

REFUSED: an entry that cannot point at a club-season BOTH names share. Without that
this is a surname rule, and a surname is not a man.

  python3 src/apply_nickname_register.py [--write] [--selftest]
"""
import os, re, sys, json, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(BASE, "service"))
import paths

DECL = os.path.join(BASE, "declarations", "nickname-register.json")
OUT = os.path.join(BASE, "build", "nickname-register.json")


def norm(s):
    return " ".join(re.sub(r"[^a-z ]", " ", str(s or "").lower()).split())


def check(entries, conn):
    """-> (ok entries, refusals). Every refusal names the entry and the reason."""
    ok, bad = [], []
    for e in entries:
        pid = e.get("person")
        cs = e.get("shared_club_season") or {}
        names = [x.get("name") for x in (e.get("names") or [])]
        if not pid or len(names) < 2 or not all(names):
            bad.append((e, "an entry carries fewer than two names, or no person")); continue
        if not conn.execute("select 1 from person where id=?", (pid,)).fetchone():
            bad.append((e, f"no person {pid} in the archive")); continue
        if not cs.get("club_id") or not cs.get("year"):
            bad.append((e, "no club-season declared -- without one this is a surname "
                           "rule, and a surname is not a man")); continue
        held = conn.execute(
            "select 1 from claim where scope='stint' and person=? and club_id=? and year=?",
            (pid, cs["club_id"], int(cs["year"]))).fetchone()
        if not held:
            bad.append((e, f"{pid} holds no season on {cs['club_id']} in {cs['year']} -- "
                           "the club-season must be one BOTH names share")); continue
        has = {norm(n) for (n,) in conn.execute(
            "select name from person_name where person=?", (pid,))}
        if not (has & {norm(n) for n in names}):
            bad.append((e, f"{pid} holds neither of the two names; the entry does not "
                           "attach to him at all")); continue
        if all(norm(n) in has for n in names):
            bad.append((e, "the archive already holds both names for this man; there is "
                           "nothing to record")); continue
        ok.append(e)
    return ok, bad


def main():
    write = "--write" in sys.argv
    conn = sqlite3.connect(paths.READ_MODEL)
    d = json.load(open(DECL))
    entries = d.get("entries") or []
    ok, bad = check(entries, conn)

    claims, srs = [], {}
    n = collections.Counter()
    for i, e in enumerate(ok, 1):
        pid = e["person"]
        has = {norm(x) for (x,) in conn.execute(
            "select name from person_name where person=?", (pid,))}
        for nm in e["names"]:
            if norm(nm["name"]) in has:
                n["name the archive already holds"] += 1
                continue
            src = nm.get("printed_by", "?")
            rec = f"{src}#nickname-register#{pid}#{nm['name']}"
            srs[rec] = {"source_id": src, "locator": nm.get("locator", "the register")}
            claims.append({
                "id": "c_%04d" % (len(claims) + 1), "predicate": "name",
                "value": nm["name"], "subject": ["person", pid], "kind": "observed",
                "source_id": src, "source_record": rec, "stated_by": src,
                "attribution": [], "observed_at": e["shared_club_season"]["year"],
                "_neither_name_is_canonical": "the other name stands beside this one and "
                                              "neither corrects the other",
                "_the_decision": e["evidence"],
                "_shared_club_season": e["shared_club_season"]})
            n["name claim written"] += 1

    print(f"register entries {len(entries)}   accepted {len(ok)}   REFUSED {len(bad)}")
    for e, why in bad:
        print(f"   refused {e.get('person')}: {why}")
    for k, v in n.most_common():
        print(f"   {k:34s} {v:>4}")
    out = {"_what": d["_what"], "_ruled": d["_ruled"],
           "_neither_is_canonical": d["_the_names_are_equal"],
           "source_records": srs, "claims": claims,
           "refusals": [{"person": e.get("person"), "why": w} for e, w in bad],
           "counts": dict(n) | {"entries": len(entries), "accepted": len(ok),
                                "refused": len(bad), "claims": len(claims)}}
    if write:
        json.dump(out, open(OUT, "w"), indent=1); print("wrote", OUT)
    else:
        print("   (dry run; --write to store)")
    return out


def selftest():
    """THE REFUSALS MUST BE SEEN TO HAPPEN. Each case is an entry that must not pass."""
    conn = sqlite3.connect(paths.READ_MODEL)
    real = json.load(open(DECL))["entries"][0]
    def variant(**kw):
        e = json.loads(json.dumps(real)); e.update(kw); return e
    cases = [
        (variant(person="P_999999"), "a person the archive does not hold"),
        (variant(shared_club_season={}), "no club-season at all"),
        (variant(shared_club_season={"club_id": "club-chicago-bears-1920", "year": 1922}),
         "a club-season the man holds no season on"),
        (variant(names=[real["names"][0]]), "only one name"),
        (variant(person="P_000001"), "a person who holds neither name"),
        (real, "the real entry (must be ACCEPTED)"),
    ]
    ok = True
    for e, why in cases:
        good, bad = check([e], conn)
        refused = bool(bad)
        want = "must be ACCEPTED" not in why
        print(f"  {'PASS' if refused == want else 'FAIL'}  "
              f"{'refuses' if refused else 'accepts':8s} {why}")
        if refused and want: print(f"        -> {bad[0][1][:110]}")
        ok &= refused == want
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(0 if selftest() else 1)
    print("SELF-TEST first -- the refusals must be seen to happen:")
    if not selftest():
        raise SystemExit("self-test failed; the route's verdict means nothing")
    print()
    main()
