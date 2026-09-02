#!/usr/bin/env python3
"""
pgm3_paths — resolve the sources tree, which is deliberately NOT in the repo.

    from pgm3_paths import sources
    open(sources('coach_birth_years.csv'))
    glob.glob(sources('1979footballdb', '*.txt'))

WHY sources/ IS NOT COMMITTED
-----------------------------
It holds third-party community files — Madden and 2K5 roster mods, Nza's Editor
draft classes, cached pages from other people's sites. They are inputs, not our
work, and publishing them in this repo republished someone else's material under
our name. Removed 2026-09-02 by Ryan's ruling. Nothing was deleted: the tree is
kept on disk and backed up, and the files remain in git history because
rewriting a published branch breaks every clone for a harm that does not warrant
it.

WHERE IT LIVES
--------------
`PGM3_SOURCES` if set, otherwise `../pgm3-sources` relative to the repo root.
Both are resolved to absolute paths, so a tool works from any working directory
— the old hardcoded 'sources/...' strings only worked when run from the repo
root, which is the second reason to route through here.

    export PGM3_SOURCES=/Volumes/backup/pgm3-sources
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(os.path.dirname(REPO_ROOT), 'pgm3-sources')


def sources_root():
    """Absolute path to the sources tree. Does not check that it exists."""
    return os.path.abspath(os.environ.get('PGM3_SOURCES') or DEFAULT)


def sources(*parts):
    """Join a path inside the sources tree."""
    return os.path.join(sources_root(), *parts)


def repo(*parts):
    """Join a path inside the REPO — for outputs (wip/, reference/, the JSONs).

    Needed because routing inputs through sources() made these tools runnable
    from any working directory, and a bare 'wip/out.csv' then writes wherever
    the caller happens to stand. Caught by running build_1979_roster.py from
    /tmp, which created /tmp/wip/. Fixing one side of a path problem exposed
    the other.
    """
    return os.path.join(REPO_ROOT, *parts)


def require(*parts):
    """Same, but fail loudly with the fix rather than a bare FileNotFoundError.

    A missing source is the single most likely failure after the move, so it
    gets a message that names the environment variable instead of a traceback
    that does not.
    """
    p = sources(*parts)
    if not os.path.exists(p):
        raise SystemExit(
            f'missing source: {p}\n'
            f'  sources/ is not in the repo. Point PGM3_SOURCES at your copy:\n'
            f'    export PGM3_SOURCES=/path/to/pgm3-sources\n'
            f'  (currently {"set to " + os.environ["PGM3_SOURCES"] if os.environ.get("PGM3_SOURCES") else "unset, defaulting to " + DEFAULT})')
    return p


if __name__ == '__main__':
    print(f'PGM3_SOURCES = {os.environ.get("PGM3_SOURCES") or "(unset)"}')
    print(f'resolved      = {sources_root()}')
    print(f'exists        = {os.path.isdir(sources_root())}')
