"""Gate: a photograph on disk whose dimensions cannot be read must FAIL, never drop.

THE RECURRING DEFECT, in its fourth coat. An input that is absent or unparseable is
read as nothing, and nothing looks exactly like a legitimate empty result:

  bio_select.py       a 44 MB scratchpad input behind os.path.exists  -> 30,503 claims
                      left the bios in silence
  gate_pfa.py         build/pfa-pre1950.json behind the same guard    -> G5 and G6 ran
                      over {} and PRINTED PASS
  stint subjects      a decider reading its own layer                 -> 2,019 skipped
  dims()              WebP and TIFF unknown to the reader             -> 5 downloaded
                      photographs landed in download_failures and were dropped

Each was found by a human noticing an absence. That is not a control. The property
below is the control, and it is about the SHAPE, not about WebP:

  P1  every image file a photograph build names is present on disk
  P2  every image file present in the photographs tree yields dimensions
  P3  a build records no unreadable file (the ingest refuses to write one that does)
  P4  the reader is honest about what it cannot read: a file it returns None for is
      not silently equal to a file it has not been shown

P4 is the one that matters, and it is checked by SHOWING the reader something it
cannot read and requiring the run to notice. A gate that only checks real files
passes happily on the day the reader loses a format.

  python3 src/gate_photographs_measurable.py      exit 1 = FAIL
"""
import os, sys, json, glob, tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
BASE = os.path.join(HERE, "..")
from measure_held_photographs import dims

TREE = os.path.join(BASE, "build", "photographs")


def main():
    fail, n = [], {}
    # P1 every file a build names is on disk
    named, missing = 0, []
    for f in sorted(glob.glob(os.path.join(BASE, "build", "wikipedia-photos-*.json"))):
        d = json.load(open(f))
        for c in d.get("claims") or []:
            fp = c.get("file")
            if not fp: continue
            named += 1
            if not os.path.exists(os.path.join(BASE, fp)):
                missing.append(fp)
        # P3 no build may record an unreadable file
        u = d.get("unreadable_after_download")
        if u: fail.append(f"{os.path.basename(f)}: records {len(u)} unreadable file(s)")
    if missing:
        fail.append(f"{len(missing)} file(s) named by a claim are not on disk: {missing[:3]}")
    n["named_by_a_claim"] = named

    # P2 every file in the tree yields dimensions
    files = [p for p in glob.glob(os.path.join(TREE, "**", "*"), recursive=True) if os.path.isfile(p)]
    unreadable = [os.path.basename(p) for p in files if not dims(p)]
    n["files_on_disk"] = len(files)
    n["unreadable"] = len(unreadable)
    if unreadable:
        fail.append(f"{len(unreadable)} file(s) on disk whose dimensions cannot be read: {unreadable[:5]}")
    fmts = {}
    for p in files:
        d = dims(p)
        if d: fmts[d[2]] = fmts.get(d[2], 0) + 1
    n["by_format"] = fmts

    # P4 the reader must NOTICE what it cannot read. Show it something unreadable.
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
        t.write(b"\x00\x01\x02 not an image at all, but it has a .jpg name\n")
        bogus = t.name
    try:
        if dims(bogus) is not None:
            fail.append("the reader returned dimensions for a file that is not an image")
        else:
            n["reader_rejects_a_non_image"] = True
    finally:
        os.unlink(bogus)

    for k, v in n.items(): print(f"  {k:28s} {v}")
    if fail:
        print("\nGATE FAILED:"); [print("  -", x) for x in fail[:10]]; return 1
    print(f"\nPHOTOGRAPHS MEASURABLE GATE: pass  ({n['files_on_disk']} files on disk, all readable; "
          f"{named} named by a claim, all present; no build records an unreadable file)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
