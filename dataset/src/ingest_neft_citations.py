"""Neft, Cohen & Deutsch, *Pro Football: The Early Years* (1978): the facts cited from it.

A REFERENCE WORK, CONSULTED AND CITED, NEVER PARSED WHOLESALE. This reads no page and no
text layer. It turns declarations/neft-early-years.json -- facts read by eye from named
pages of the scan, one at a time -- into claims, each naming its page, so the archive can
hold what Neft says beside what other sources say. Adding a fact means reading the page
and adding it to the declaration by hand; this file never grows a parser.

    python3 src/ingest_neft_citations.py [--write]
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
import index_io as IO                       # atomic build-store write

DECL = json.load(open(os.path.join(BASE, "declarations", "neft-early-years.json"), encoding="utf-8"))
SRC_ID = DECL["source_id"]
OUT = os.path.join(BASE, "build", "neft-early-years-1978.json")


def main(write):
    source = {"source_id": SRC_ID, "name": DECL["name"], "stated_by": DECL["stated_by"],
              "publisher": DECL["publisher"], "acquisition": DECL["acquisition"]}
    claims, records = [], {}
    for c in DECL["citations"]:
        sr = f"{SRC_ID}#pp{c['pages'].replace(' ', '')}"
        records[sr] = {"source_id": SRC_ID, "locator": f"pages {c['pages']}"}
        if not c.get("value"):
            raise SystemExit(f"{c['id']}: a citation with no value is not a claim")
        claims.append({"id": c["id"], "source_id": SRC_ID, "source_record": sr, "stated_by": DECL["stated_by"],
                       "attribution": [DECL["name"]], "kind": "observed",
                       "acquisition_state": c["acquisition_state"],
                       "subject": c["subject"], "predicate": c["predicate"], "value": c["value"]})
    out = {"_what": "Facts cited from Neft's 1978 encyclopaedia, each read by eye from a named page. "
                    "Consulted and cited, never parsed wholesale.",
           "source": source, "source_records": records, "claims": claims,
           "counts": {"claims": len(claims)}}
    print(f"NEFT CITATIONS -> {os.path.basename(OUT)}  ({'WRITE' if write else 'dry run'}): {len(claims)} claim(s)")
    for c in claims: print(f"  {c['id']}: {c['predicate']} on {c['subject']} [{c['source_record']}]")
    if write:
        IO.dump_atomic(out, OUT, indent=1)
        print(f"  -> {OUT}")
    return out


if __name__ == "__main__":
    main(write="--write" in sys.argv)
