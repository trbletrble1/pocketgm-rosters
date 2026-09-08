"""Measure duplication across the whole text corpus: the same document held twice, the
same club-season in two documents, and -- the case that matters -- one document being a
STRICT SUBSET of another.

WHY CONTAINMENT AND NOT SIMILARITY. The Eagles 1975 yearbook looked promising by every
signal and turned out to be a strict subset of the press guide already held. Jaccard
similarity is small for a subset when the two differ greatly in length (a 40 KB yearbook
inside a 400 KB guide scores ~0.1 and looks unrelated). So each document's shingle set is
sampled by hash modulus -- an unbiased sample of the SET, not of the text -- which makes
    containment(A in B) = |sample(A) & sample(B)| / |sample(A)|
estimable directly. The prose extraction found 21 cross-guide duplicates by accident;
this looks for them on purpose.

Reports pairs, never deletes or merges anything.

  python3 src/census_duplicates.py [--mod 64] [--min 0.30]
"""
import os, re, sys, csv, json, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import index_io as IO
SRC = os.path.expanduser("~/Documents/pgm3-sources")
OUT = os.path.join(BASE, "build-reports", "corpus-census-duplicates.json")
MOD = int(sys.argv[sys.argv.index("--mod") + 1]) if "--mod" in sys.argv else 64
MIN = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 0.30
WORD = re.compile(r"[a-z0-9]+")
K = 6      # shingle length in tokens
STEP = 2   # sample every other position -- halves the cost, keeps high-overlap detection


def sketch(path):
    try: t = open(path, errors="ignore").read().lower()
    except Exception: return None
    toks = WORD.findall(t)
    if len(toks) < K + 20: return set()
    s = set()
    for i in range(0, len(toks) - K, STEP):
        h = hashlib.blake2b(" ".join(toks[i:i + K]).encode(), digest_size=8).digest()
        v = int.from_bytes(h, "big")
        if v % MOD == 0: s.add(v)
    return s


def main():
    docs = []
    nb = os.path.join(SRC, "nfl-books", "text_all")
    for f in sorted(os.listdir(nb)):
        if f.endswith(".txt"): docs.append(("nfl-books", f[:-4], os.path.join(nb, f)))
    for sub in ("text", "text_container"):
        d = os.path.join(SRC, "college-pre1950", sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".txt"): docs.append(("college-pre1950", f[:-4], os.path.join(d, f)))
    print(f"{len(docs)} texts", flush=True)

    sk, sizes = {}, {}
    for i, (st, ident, p) in enumerate(docs, 1):
        s = sketch(p)
        if s is None: continue
        sk[ident] = s; sizes[ident] = len(s)
        if i % 250 == 0: print(f"  sketched {i}", flush=True)

    inv = collections.defaultdict(list)
    for ident, s in sk.items():
        for v in s: inv[v].append(ident)
    shared = collections.Counter()
    for v, ids in inv.items():
        if len(ids) < 2 or len(ids) > 60: continue   # a hash in 60+ docs is boilerplate
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                shared[(ids[a], ids[b]) if ids[a] < ids[b] else (ids[b], ids[a])] += 1

    pairs = []
    for (a, b), n in shared.items():
        na, nb_ = sizes.get(a, 0), sizes.get(b, 0)
        if not na or not nb_: continue
        cont_a, cont_b = n / na, n / nb_
        jac = n / (na + nb_ - n)
        if max(cont_a, cont_b) < MIN: continue
        pairs.append({"a": a, "b": b, "shared": n, "n_a": na, "n_b": nb_,
                      "containment_a_in_b": round(cont_a, 3), "containment_b_in_a": round(cont_b, 3),
                      "jaccard": round(jac, 3),
                      "relation": ("near-identical" if jac >= 0.6 else
                                   "subset" if max(cont_a, cont_b) >= 0.6 else "overlapping")})
    pairs.sort(key=lambda x: -max(x["containment_a_in_b"], x["containment_b_in_a"]))
    res = {"_date": "2026-09-07", "_params": {"shingle_tokens": K, "step": STEP, "hash_mod": MOD,
                                              "min_containment": MIN},
           "texts": len(sk), "pairs": len(pairs),
           "by_relation": dict(collections.Counter(p["relation"] for p in pairs)),
           "docs_in_a_pair": len({x for p in pairs for x in (p["a"], p["b"])}),
           "pairs_detail": pairs}
    IO.dump_atomic(res, OUT, indent=0)
    print(json.dumps({k: res[k] for k in ("texts", "pairs", "by_relation", "docs_in_a_pair")}, indent=1))
    for p in pairs[:25]:
        print(f"  {p['relation']:15} j={p['jaccard']:.2f} c={max(p['containment_a_in_b'],p['containment_b_in_a']):.2f}  {p['a'][:40]:40} | {p['b'][:40]}")


if __name__ == "__main__":
    main()
