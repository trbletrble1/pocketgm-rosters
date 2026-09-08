"""One MediaWiki API call, hardened for unattended runs.

The first overnight enumeration died at 00:xx on `[Errno 51] Network is
unreachable` -- the machine lost its connection for a while and the script
raised instead of waiting. An unattended job must outlast a transient outage.

  api(params) -> (http_status, parsed_json_or_None)

  - descriptive User-Agent with contact; serial; ~1/s between calls
  - reads the HTTP status on every call and returns it
  - on a network error, a timeout, a 5xx, or a 429: sleeps and retries with
    backoff (30s, 60s, 2m, 4m, 8m, 15m, 15m ...), for up to MAX_WAIT in total,
    logging each wait; only then raises
  - a 4xx other than 429 is returned to the caller as (code, None), not retried
"""
import re
import os, ssl, json, time, socket, urllib.request, urllib.parse, urllib.error

UA = "pgm3-archive-research/1.0 (NFL historical roster research; contact: ryannecci@gmail.com)"
ENDPOINT = "https://en.wikipedia.org/w/api.php?"
DELAY = 1.0
BACKOFF = [30, 60, 120, 240, 480, 900]
MAX_WAIT = 4 * 3600          # give an outage four hours before giving up


class ApiUnavailable(Exception):
    pass


class NoCertificates(ApiUnavailable):
    """TLS cannot verify. A configuration fault, not an outage -- retrying never fixes it."""


def ssl_context():
    """A VERIFYING TLS context, on a machine whose Python may ship without a CA bundle.

    bghq-mac, 2026-09-07: the archive moved to a python.org 3.13 whose certificates were
    never installed -- etc/openssl/cert.pem does not exist -- so every HTTPS fetch raised
    CERTIFICATE_VERIFY_FAILED. That surfaces as a URLError, which this module treated as a
    transient network fault and retried on the 30s..15m backoff for up to four hours. A
    50-minute "fetch" that had made no request and would never make one.

    Verification is NEVER disabled here. The bundle is located, or the run stops.
    """
    paths = ssl.get_default_verify_paths()
    if (paths.openssl_cafile and os.path.exists(paths.openssl_cafile)) or \
       (paths.openssl_capath and os.path.isdir(paths.openssl_capath)):
        return ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        raise NoCertificates(
            "no CA bundle: this Python has no certificates (%s missing) and certifi is not "
            "installed. Fix with `python3 -m pip install --user certifi`, or run "
            "'/Applications/Python 3.13/Install Certificates.command'. Verification is not "
            "disabled to work around it." % paths.openssl_cafile)
    return ssl.create_default_context(cafile=certifi.where())


CTX = None


def api(params, timeout=120, log=print):
    global CTX
    if CTX is None: CTX = ssl_context()
    url = ENDPOINT + urllib.parse.urlencode({**params, "format": "json"})
    waited, attempt = 0, 0
    while True:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                code = r.status
                data = json.loads(r.read())
            time.sleep(DELAY)
            return code, data
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                why = f"HTTP {e.code}"
            else:
                time.sleep(DELAY)
                return e.code, None
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
            why = f"{type(e).__name__}: {getattr(e, 'reason', e)}"
            # A certificate failure is PERMANENT. Backing off on it burns hours and
            # reports nothing. Stop on the first one, naming the fix.
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(reason):
                raise NoCertificates(
                    "TLS verification failed and will not succeed on retry: %s. Not backed off "
                    "-- a misconfiguration is not an outage." % why)
        except json.JSONDecodeError as e:
            why = f"bad JSON: {e}"
        pause = BACKOFF[min(attempt, len(BACKOFF) - 1)]
        if waited + pause > MAX_WAIT:
            raise ApiUnavailable(f"gave up after {waited // 60} min: {why}")
        log(f"  [wiki_api] {why} -- waiting {pause}s (attempt {attempt + 1}, {waited // 60} min so far)", flush=True)
        time.sleep(pause)
        waited += pause; attempt += 1

# ---------------------------------------------------------------- infobox image
# THE ONE READER FOR AN INFOBOX IMAGE. It lived as a copied regex in
# ingest_wikipedia_photos.py and fetch_wiki_photo_sizes.py -- two copies of one rule,
# which is how a reader and its consumer drift apart in silence.
#
# The copied pattern required the filename to END the line and to contain no `|`, `[`
# or `]`. Measured 2026-09-07 over the 14,428 cached gridiron articles: 68 of them carry
# an infobox image the pattern could not read, and every photograph sweep therefore
# treated those men as having no image at all. Four printed forms defeated it:
#
#   Name.jpg<!-- Only free-content images are allowed ... -->   a trailing HTML comment
#   File:Long name (cropped).jpg|alt=...                        a File: prefix and an alt
#   [[File:Name.jpg|thumb|...]]                                 a full wikilink
#   Name.png <!--It is better that the photo ... -->            a space, then a comment
#
# A COMMENT IS NOT A FILENAME. `image = <!-- name.jpg -->` names nothing, and reading it
# would attach an image that is not there. The comment is removed BEFORE the filename is
# looked for, so that case returns None as it should.
_IMG_LINE = re.compile(r"(?im)^[ \t]*\|?[ \t]*image[ \t]*=[ \t]*(.+)$")
_COMMENT = re.compile(r"<!--.*?-->|<!--.*$", re.S)
_IMG_FILE = re.compile(r"^([^<>\[\]{}|=\n]{1,160}?\.(?:jpg|jpeg|png|gif|webp|tif|tiff))\s*$", re.I)


def infobox_image(text):
    """The infobox `image` filename, or None. `File:` and `[[` are stripped; a trailing
    comment, an `|alt=` and a wikilink tail are dropped; a caption with no filename, and a
    filename that exists only inside a comment, both return None."""
    m = _IMG_LINE.search(text or "")
    if not m: return None
    v = _COMMENT.sub(" ", m.group(1))
    v = v.split("|")[0]
    v = re.sub(r"^\s*\[\[", "", v).strip()
    v = re.sub(r"^(?:File|Image)\s*:", "", v, flags=re.I).strip()
    v = v.rstrip("]").strip()
    m2 = _IMG_FILE.match(v)
    return m2.group(1).strip() if m2 else None
