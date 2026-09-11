"""Every location the service reads or writes, in one place. Nothing here is a literal elsewhere."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.abspath(os.path.join(HERE, ".."))
BUILD = os.path.join(DATASET, "build")                       # the claim stores. READ ONLY.
BUILD_REPORTS = os.path.join(DATASET, "build-reports")       # identity.json, person-index.json. READ ONLY.
DECLARATIONS = os.path.join(DATASET, "declarations")         # the archive's source declarations. READ ONLY.
SERVICE_DECLARATIONS = os.path.join(HERE, "declarations")    # the service's own: predicate families, dates as printed
IDENTITY = os.path.join(BUILD_REPORTS, "identity.json")
PERSON_INDEX = os.path.join(BUILD_REPORTS, "person-index.json")
CLUBS = os.path.join(BUILD, "clubs.json")
PERSON_MERGES = os.path.join(DECLARATIONS, "person-merge-decisions.json")   # the 93 decisions, in git (2026-09-11)
INDEX_REBUILD_DECL = os.path.join(DECLARATIONS, "person-index-rebuild.json")

# The read model lives OUTSIDE the repo (ruled 2026-09-07) so no .gitignore is touched.
CACHE_DIR = os.environ.get("FOOTBALL_ARCHIVE_CACHE",
                           os.path.expanduser("~/Library/Caches/football-archive-service"))
READ_MODEL = os.path.join(CACHE_DIR, "archive.sqlite")
# THE PREVIOUS PUBLISHED MODELS. Added 2026-09-09 after a question could not be
# answered: "what did the service return before this weekend?". `os.replace`
# retained nothing and build/ is gitignored, so the model of 2026-09-08 18:57 did
# not exist in any form, and neither did the stores that would rebuild it.
PREVIOUS_MODELS = os.path.join(CACHE_DIR, "previous")
BUILD_LOG = os.path.join(CACHE_DIR, "build.log")
