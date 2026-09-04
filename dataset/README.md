# dataset/

Implementation of `docs/DATASET_DESIGN.md`. Moves to the new repo with the docs.

    declarations/   source declarations - what a source carries, per era and per league,
                    and what separates a collision in it. Data, not code.
    policy/         resolution ranking. Changing it is an edit and a re-run.
    src/            model, ingest, resolution, gates, export
    build/          outputs. Not claims.

Run the gates:

    python3 src/gates.py           # every gate must pass
    python3 src/gate_selftest.py   # every gate must FAIL when its invariant is broken

The second is not ceremony. A gate that has only ever passed has not been tested.
