"""Fetch the team-season pages PFA's own season indexes name and the archive does not
hold. Politely.

THE SITE IS SOMEBODY'S LIFE'S WORK AND THIS IS A FAVOUR. One request at a time, a
full second between them, a User-Agent that says who is asking, and a back-off that
gets SLOWER on 429 and 5xx rather than retrying harder. No concurrency. There is no
robots.txt at profootballarchives.com -- it 404s -- so nothing is disallowed and
nothing is permitted either; the discipline is the same as the Ghosts run.

ENUMERATED BEFORE FETCHED. `--enumerate` reads the 106 cached season index pages,
lists every team-season page they name, subtracts what is on disk, and writes
manifest.json. Fetching does not discover anything: it works through that list.

A PAGE AN INDEX NAMES THAT DOES NOT EXIST IS A REAL FACT ABOUT PFA, not a failure.
PFA answers a missing page with an honest 404, so absence is distinguishable from
error. Both are recorded, with the status, in the manifest.

RESUMES FROM THE MANIFEST. Each page is written to the manifest as soon as it lands,
by rewriting the file, so a kill at any point loses at most the request in flight.
Restarting skips everything already recorded. Run it under nohup or a launchd job so
an SSH disconnect does not take it with it.

  python3 src/fetch_pfa_team_seasons.py [--kind team-seasons|awards] --enumerate
  python3 src/fetch_pfa_team_seasons.py [--limit N] [--delay S]
  python3 src/fetch_pfa_team_seasons.py --status
"""
import os, re, sys, ssl, json, time, hashlib, urllib.request, urllib.error

# macOS's framework Python ships no CA bundle, so urllib fails every HTTPS request
# with CERTIFICATE_VERIFY_FAILED while curl succeeds. certifi's bundle is used when
# it is installed. NOT disabling verification: an unverified fetch would be a
# different document from the one the citation names, and nothing would say so.
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, "..")
CACHE = os.path.expanduser("~/Documents/pgm3-sources/pfa2")
# every directory PFA pages have been fetched into. The link graph must be read
# across all of them: the minor-league award pages are linked from team-season pages
# fetched this morning into a second directory, and reading only the first cache
# enumerated 174 of 260 while looking complete.
CACHES = [CACHE, os.path.expanduser("~/Documents/pgm3-sources/pfa-team-seasons")]


def cached():
    """-> {filename: path} across every PFA cache directory."""
    out = {}
    for d in CACHES:
        if os.path.isdir(d):
            for f in os.listdir(d):
                out.setdefault(f, os.path.join(d, f))
    return out
# ONE FETCHER, TWO PAGE KINDS. The politeness, the manifest and the resume are the
# same discipline whatever is being fetched; a second copy of them would be a second
# thing to get wrong. The kind chooses only WHICH pages the season indexes name.
KINDS = {
    "team-seasons": {
        "dest": "pfa-team-seasons",
        "what": "team-season pages named by PFA's own season indexes",
        "match": lambda b: bool(TS.match(b)) and not NOT_A_TEAM.search(b)
                           and not re.match(r"^\d{4}\.html$", b),
        "named_by": "season_index",
    },
    "awards": {
        "dest": "pfa-awards",
        "what": "award pages named by PFA's own season indexes -- one per year per league",
        "match": lambda b: bool(re.match(r"^\d{4}[a-z]*awards\.html$", b)),
        # the season indexes name only 174 of these; the other 86 are linked from
        # team-season pages -- the minor-league award pages. Using the index alone
        # would enumerate a denominator that leaves out a third of the section.
        "named_by": "any_cached_page",
    },
}
KIND = "team-seasons"
DEST = os.path.expanduser("~/Documents/pgm3-sources/pfa-team-seasons")
MANIFEST = os.path.join(DEST, "manifest.json")


def set_kind(k):
    global KIND, DEST, MANIFEST
    if k not in KINDS:
        raise SystemExit(f"unknown kind {k!r}; one of {sorted(KINDS)}")
    KIND = k
    DEST = os.path.expanduser("~/Documents/pgm3-sources/" + KINDS[k]["dest"])
    MANIFEST = os.path.join(DEST, "manifest.json")
SITE = "https://www.profootballarchives.com/"
UA = ("pgm3-archive-preservation/1.0 (personal football history archive; "
      "reading pages this site's own season indexes link to; "
      "one request at a time; contact via github.com/ryannecci)")
DELAY = 1.0
TS = re.compile(r"^(\d{4})([a-z]+)\.html$")
NOT_A_TEAM = re.compile(r"(awards|draft|boxscores|leaders|standings|playoffs|allstar"
                        r"|probowl|schedule|transactions)")


def load():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {"_what": KINDS[KIND]["what"],
            "enumerated_at": None, "named": [], "already_on_disk": [],
            "files": {}, "absent": {}, "errors": {}}


def save(man):
    tmp = MANIFEST + ".tmp"
    json.dump(man, open(tmp, "w"), indent=1)
    os.replace(tmp, MANIFEST)            # a manifest is never half-written


def enumerate_pages():
    pb = cached()
    have = set(pb)
    seasons = sorted(f for f in have if re.match(r"^\d{4}\.html$", f))
    # WHICH PAGES ARE READ FOR LINKS depends on the kind. Team-season pages are named
    # by the season indexes and nothing else needs reading. Award pages are not: the
    # indexes name 174 of them and the other 86 -- the minor-league ones -- are linked
    # only from team-season pages. Reading the indexes alone enumerated two thirds of
    # the section while looking complete.
    src = seasons if KINDS[KIND].get("named_by") != "any_cached_page" \
        else sorted(f for f in have if f.endswith(".html"))
    named = set()
    for f in src:
        t = open(pb[f], errors="replace").read()
        for h in re.findall(r'href=["\']?([^"\'> ]+)', t):
            b = os.path.basename(h.split("#")[0])
            if KINDS[KIND]["match"](b):
                named.add(b)
    os.makedirs(DEST, exist_ok=True)
    man = load()
    man["enumerated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    man["pages_read_for_links"] = len(src)
    man["named"] = sorted(named)
    man["already_on_disk"] = sorted(named & have)
    save(man)
    todo = [b for b in sorted(named) if b not in have and b not in man["files"]
            and b not in man["absent"]]
    print(f"cache directories read            {len([d for d in CACHES if os.path.isdir(d)]):>6,}")
    print(f"pages read for links              {len(src):>6,}")
    print(f"{KIND} pages named{'':>{max(0, 17 - len(KIND))}}{len(named):>6,}")
    print(f"already on disk                   {len(named & have):>6,}")
    print(f"TO FETCH                          {len(todo):>6,}")
    return todo


def fetch(url, delay, tries=4):
    d = delay
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=90, context=SSL_CTX) as r:
                return r.read(), r.status, None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, 404, None                    # an absence, not an error
            if e.code in (429, 500, 502, 503, 504) and i < tries - 1:
                d *= 3                                    # SLOWER, not harder
                time.sleep(d); continue
            return None, e.code, str(e)
        except Exception as e:
            if i < tries - 1:
                d *= 3; time.sleep(d); continue
            return None, None, repr(e)
    return None, None, "gave up"


def main():
    argv = sys.argv[1:]
    if "--kind" in argv:
        set_kind(argv[argv.index("--kind") + 1])
    if "--enumerate" in argv:
        enumerate_pages(); return
    man = load()
    if "--status" in argv:
        print(f"enumerated   {man['enumerated_at']}")
        print(f"named        {len(man['named']):>6,}")
        print(f"on disk      {len(man['already_on_disk']):>6,}")
        print(f"fetched      {len(man['files']):>6,}")
        print(f"absent (404) {len(man['absent']):>6,}")
        print(f"errors       {len(man['errors']):>6,}")
        left = [b for b in man["named"] if b not in set(man["already_on_disk"])
                and b not in man["files"] and b not in man["absent"]]
        print(f"REMAINING    {len(left):>6,}")
        return
    if not man["named"]:
        sys.exit("nothing enumerated -- run --enumerate first")
    delay = float(argv[argv.index("--delay") + 1]) if "--delay" in argv else DELAY
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    have = set(cached())
    todo = [b for b in man["named"] if b not in have and b not in man["files"]
            and b not in man["absent"]]
    if limit: todo = todo[:limit]
    os.makedirs(DEST, exist_ok=True)
    print(f"{len(todo):,} to fetch, {delay}s between requests", flush=True)
    for i, name in enumerate(todo, 1):
        body, status, err = fetch(SITE + name, delay)
        if body is not None:
            open(os.path.join(DEST, name), "wb").write(body)
            man["files"][name] = {"status": status, "bytes": len(body),
                                  "sha256": hashlib.sha256(body).hexdigest(),
                                  "url": SITE + name,
                                  "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        elif status == 404:
            man["absent"][name] = {"status": 404,
                                   "why": "PFA's season index links to it and the site "
                                          "answers 404 -- the page does not exist",
                                   "seen_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        else:
            man["errors"][name] = {"status": status, "error": err,
                                   "seen_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        save(man)                       # after EVERY page, so a kill costs one request
        if i % 25 == 0 or i == len(todo):
            print(f"  {i:>5,}/{len(todo):,}  files {len(man['files']):,}  "
                  f"absent {len(man['absent']):,}  errors {len(man['errors']):,}",
                  flush=True)
        time.sleep(delay)
    print("done", flush=True)


if __name__ == "__main__":
    main()
