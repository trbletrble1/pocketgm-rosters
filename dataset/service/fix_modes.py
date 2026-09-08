"""Record file and directory permissions on one machine; restore them on another.

WHY THIS EXISTS. A copy through an exFAT drive carries every byte and loses every
permission: macOS rewrote 102,861 files and their directories as 0700 on arrival, and
git then reported 263 tracked files as mode-changed (100644 => 100755) when nothing
about their contents had changed. move_manifest.py could not see it -- it hashes
content, and content was perfect -- so this is the companion check.

    python3 fix_modes.py --record modes.json          # on the source machine
    python3 fix_modes.py --apply  modes.json          # on the target: reports, changes nothing
    python3 fix_modes.py --apply  modes.json --write  # on the target: actually chmod
"""
import os, sys, json, stat, argparse

ROOTS = ["Documents/pocketgm-rosters-clone", "Documents/pgm3-sources"]
SKIP_DIR = {"__pycache__"}


def walk(home):
    out = {}
    for root in ROOTS:
        base = os.path.join(home, root)
        if not os.path.isdir(base):
            print(f"  MISSING ROOT: {base}", file=sys.stderr); continue
        out[os.path.relpath(base, home)] = stat.S_IMODE(os.stat(base).st_mode)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIR]
            for name in dn + fn:
                p = os.path.join(dp, name)
                try: out[os.path.relpath(p, home)] = stat.S_IMODE(os.lstat(p).st_mode)
                except OSError as e: print(f"  UNREADABLE {p}: {e}", file=sys.stderr)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record"); ap.add_argument("--apply"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--home", default=os.path.expanduser("~"))
    a = ap.parse_args(argv)
    if a.record:
        modes = walk(a.home)
        json.dump(modes, open(a.record, "w"))
        from collections import Counter
        c = Counter(oct(m) for m in modes.values())
        print(f"  recorded {len(modes):,} paths -> {a.record}")
        for m, n in c.most_common(6): print(f"    {n:>8,}  {m}")
        return 0
    if not a.apply: return ap.print_help() or 2
    want = json.load(open(a.apply))
    changed = missing = same = 0; examples = []
    for rel, mode in want.items():
        p = os.path.join(a.home, rel)
        try: cur = stat.S_IMODE(os.lstat(p).st_mode)
        except OSError: missing += 1; continue
        if cur == mode: same += 1; continue
        changed += 1
        if len(examples) < 5: examples.append((rel, oct(cur), oct(mode)))
        if a.write:
            try: os.chmod(p, mode)
            except OSError as e: print(f"  chmod failed {rel}: {e}", file=sys.stderr)
    print(f"  already correct {same:,}   wrong {changed:,}   not present here {missing:,}")
    for rel, c, w in examples: print(f"    {c} -> {w}   {rel}")
    print("  " + ("APPLIED" if a.write else "dry run -- add --write to apply"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
