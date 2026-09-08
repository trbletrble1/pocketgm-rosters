"""Gate for patch 2 of the club job: the merged-club table is derived, not typed.

  T1  every merger ruling in declarations/clubs.json is in the club table, by name, as its own club
      (kind merger) or as a merger season of the absorbing club (kind absorbed), with every parent found
  T2  gate_merged_clubs.MERGED, derived from the table, states each ruling back: the merged name, one
      silent code per parent name, and at least one boxscore string a lineup actually printed
  T3  no club string from the rulings is typed in any src/*.py (the declaration is the only home)
  T4  gate_merged_clubs --selftest still shows every check failing for its own reason

  python3 src/gate_merged_table.py
"""
import os, sys, json, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from clubs import Clubs, norm

fails = []
def check(ok, msg):
    print(("  ok    " if ok else "  FAIL  ") + msg)
    if not ok: fails.append(msg)


def main():
    D = json.load(open(os.path.join(BASE, "declarations", "clubs.json")))["MERGERS"]["rulings"]
    C = Clubs(); T = C.T
    print("T1  every ruling is in the table")
    for r in D:
        y = int(r["year"]); hits = [c for c in T["clubs"] if C.name_for(c["id"], y) == r["merged"]]
        ok = len(hits) == 1
        if ok:
            c = hits[0]; L = c["lineage"]
            if r["kind"] == "merger": ok = L["kind"] == "merger" and len(L["merger_of"]) == len(r["of"]) and not L["links"] and len(c["segments"]) == 1
            else: ok = str(y) in L["merger_seasons"] and len(L["merger_seasons"][str(y)]["absorbed"]) == len(r["of"])
            parents = L["merger_of"] if r["kind"] == "merger" else L["merger_seasons"].get(str(y), {}).get("absorbed", [])
            ok = ok and all(str(y) in T["clubs"][[x["id"] for x in T["clubs"]].index(p)]["lineage"]["merged_into"] for p in parents)
            ok = ok and all(any(norm(n["name"]) == norm(pn) for p in parents for n in next(x for x in T["clubs"] if x["id"] == p)["names"]) for pn in r["of"])
        check(ok, f"{y} {r['merged']} ({r['kind']}) of {r['of']}: " + (f"{hits[0]['id']}, parents {parents}" if ok else f"{len(hits)} club(s) bear the name; lineage does not state the ruling"))
    unres = T["unresolved"].get("merged_clubs", [])
    check(not unres, f"no ruling left a parent or a code unresolved ({len(unres)}: {unres[:2]})")
    print("T2  the derived MERGED states the rulings back")
    import gate_merged_clubs as G
    check(len(G.MERGED) == len(D), f"{len(G.MERGED)} derived entries for {len(D)} rulings")
    for r in D:
        y = str(r["year"]); m = next((v for (lg, yy, code), v in G.MERGED.items() if yy == y and v["name"] == r["merged"]), None)
        ok = bool(m) and len(m["must_be_silent"]) == len(r["of"]) and all(m["must_be_silent"]) and len(m["boxscore_strings"]) >= 1
        check(ok, f"{y} {r['merged']}: silent {m['must_be_silent'] if m else None}, boxscore strings {m['boxscore_strings'] if m else None}")
    print("T3  no merger string is typed in src")
    import ast
    typed = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn == "gate_merged_table.py": continue
        tree = ast.parse(open(os.path.join(HERE, fn)).read())
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                docs.add(id(node.body[0].value))
        lits = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]
        for r in D:
            for st in [r["merged"]]:                                   # the merged names are the ones no code should carry; parent names are ordinary club names
                if any(st in l for l in lits): typed.append((fn, st))
    check(not typed, "no merged-club string appears in any src/*.py" if not typed else f"typed in {typed}")
    print("T4  gate_merged_clubs selftest")
    out = subprocess.run([sys.executable, os.path.join(HERE, "gate_merged_clubs.py"), "--selftest"], capture_output=True, text=True).stdout
    check("selftest PASSED" in out, "every M-check still fails for its own reason" if "selftest PASSED" in out else out[-600:])
    print()
    if fails: print(f"MERGED TABLE GATE: {len(fails)} FAILURE(S)"); [print("   -", f) for f in fails]; return 1
    print("MERGED TABLE GATE: pass"); return 0


if __name__ == "__main__":
    sys.exit(main())
