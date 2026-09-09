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

Two more properties, both learned the same day (2026-09-07) and both about a check
that cannot see the thing it checks:

**A gate must not reimplement what it checks.** One definition, imported by both.
`service/gates.py` RS-G5 carried its own copy of the reader's test for what a claim
store is, so the gate and `build_read_model.py` could drift apart -- silently, on both
sides, each still reporting success. It now imports `build_read_model.is_claim_store`
and puts specimens through it on every run. Any gate that restates its subject's rule
can pass while the subject has changed.

**Two modules must not share a name across `src/` and `service/`.** Whichever is
imported first binds the name, and every later `import X` gets that one whatever
`sys.path` says afterwards. `service/readings.py` shadowed `src/readings.py` for eleven
minutes and `bio_select.py` silently got the wrong module, with a different return
shape; every bio 503'd and the crash was reported to the wrong session as their bug.
Import a module from another tree BY FILE PATH under a distinct name, never by bare
name. Two copies of one rule and two names for one module are the same defect.

And the corollary, from `src/gate_readings.py` R3: **a reader that cannot read the
archive does not merely fail to remove false disagreements -- it hides real ones.** A
gate whose reader is unavailable must FAIL, not report a clean sheet it did not check.
