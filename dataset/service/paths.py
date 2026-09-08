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
PERSON_MERGES = os.path.join(BUILD, "person-merges.json")
INDEX_REBUILD_DECL = os.path.join(DECLARATIONS, "person-index-rebuild.json")

# The read model lives OUTSIDE the repo (ruled 2026-09-07) so no .gitignore is touched.
CACHE_DIR = os.environ.get("FOOTBALL_ARCHIVE_CACHE",
                           os.path.expanduser("~/Library/Caches/football-archive-service"))
READ_MODEL = os.path.join(CACHE_DIR, "archive.sqlite")
BUILD_LOG = os.path.join(CACHE_DIR, "build.log")
