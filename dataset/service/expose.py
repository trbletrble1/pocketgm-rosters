"""Put the read service on the public internet -- deliberately, in exposed mode.

access.py names this file as the thing that MUST set FOOTBALL_ARCHIVE_EXPOSED=1
before anything proxies to the app. It did not exist until now; the docstring
was writing a cheque. This is it.

THE TRAP, RESTATED, BECAUSE THIS FILE IS WHERE IT WOULD HAVE SPRUNG.
`tailscale funnel` terminates TLS on this machine and connects to the app FROM
LOOPBACK. The rule "loopback needs no token" would therefore have handed the open
internet an unauthenticated door. So Funnel never points at the ordinary local
listener on :8765. It points at a THIRD listener, on :8766, whose only reason to
exist is that it runs EXPOSED=1: a token from every caller, loopback included,
and /rebuild refused outright.

    local    127.0.0.1:8765   unauthenticated. Not funnelled. Unchanged.
    tailnet  <ts ip>:8765     EXPOSED. Reachable only from Ryan's tailnet.
    funnel   127.0.0.1:8766   EXPOSED. The public HTTPS URL proxies to this and
                              nothing else.

`on` does not trust that arrangement, it checks it: after the listener starts it
sends an unauthenticated loopback request and REFUSES TO OPEN THE FUNNEL unless
that request is turned away with 401, and unless /rebuild is turned away with 403
even holding a good token. If either check fails it tears the listener down and
exits non-zero. The door is proven shut before it is put on the street.

    python3 expose.py check    # is Ryan's admin-console step done?
    python3 expose.py on       # install the :8766 listener, verify, open Funnel, print the URL
    python3 expose.py status   # what is public right now
    python3 expose.py off      # close Funnel, remove the listener. :8765 and the tailnet are untouched.
"""
import os, sys, json, time, plistlib, subprocess, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, launchd as L, access

LABEL = L.LABEL + ".funnel"
PORT = os.environ.get("FOOTBALL_ARCHIVE_FUNNEL_PORT", "8766")
TS = L.TAILSCALE if os.path.exists(L.TAILSCALE) else "tailscale"


def ts(*args, timeout=60):
    return subprocess.run([TS, *args], capture_output=True, text=True, timeout=timeout)


def node():
    """(ipv4, magicdns name, cert_domains, may_funnel). Both of Ryan's admin-console
    changes are visible from here and neither is guessed:

      cert_domains  empty until DNS -> HTTPS Certificates is on. Funnel cannot get a
                    certificate for this node without it.
      may_funnel    the control plane grants the `funnel` node attribute, which shows
                    up in this node's capability map. Absent = the nodeAttrs entry is
                    not in the ACL policy file."""
    r = ts("status", "--json", timeout=15)
    if r.returncode: return None, None, [], False
    d = json.loads(r.stdout); s = d.get("Self") or {}
    ip = next((i for i in (s.get("TailscaleIPs") or []) if ":" not in i), None)
    dns = (s.get("DNSName") or "").rstrip(".") or None
    caps = set(s.get("CapMap") or {}) | set(s.get("Capabilities") or [])
    may = any(c == "funnel" or str(c).endswith("/cap/funnel") for c in caps)
    return ip, dns, list(d.get("CertDomains") or []), may


def plist():
    """Same shape as the other two listeners, with EXPOSED forced on. Not a flag a
    caller may pass: a funnel listener that is not exposed is the bug this file exists
    to prevent, so it is not expressible here."""
    ip, dns, _, _ = node()
    env = {"FOOTBALL_ARCHIVE_AUTOREBUILD": "0",
           "FOOTBALL_ARCHIVE_EXPOSED": "1",
           "FOOTBALL_ARCHIVE_PORT": PORT,
           "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    hosts = [h for h in (dns, ip, "127.0.0.1", "localhost") if h]
    env["FOOTBALL_ARCHIVE_HOSTS"] = ",".join(hosts)
    return {"Label": LABEL,
            "ProgramArguments": [os.path.join(L.VENV, "bin", "uvicorn"), "app:app",
                                 "--host", "127.0.0.1", "--port", PORT, "--log-level", "warning"],
            "WorkingDirectory": HERE,
            "EnvironmentVariables": env,
            "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 30,
            "StandardOutPath": os.path.join(paths.CACHE_DIR, "server-funnel.log"),
            "StandardErrorPath": os.path.join(paths.CACHE_DIR, "server-funnel.log")}


def get(path, token=None, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except OSError: return None


def wait_up(seconds=30):
    for _ in range(seconds):
        if get("/") is not None: return True
        time.sleep(1)
    return False


def prove_shut(token):
    """The three properties, asserted against the listener Funnel is about to face.
    Not a unit test with a fake peer -- a real request over a real socket."""
    checks = [("an unauthenticated loopback caller is refused", get("/sources"), 401),
              ("a bad token is refused",                        get("/t/wrong/sources"), 401),
              ("POST /rebuild is refused even with the token",  get("/rebuild", token, "POST"), 403),
              ("the token still reads",                         get("/sources", token), 200)]
    ok = True
    for what, got, want in checks:
        good = got == want
        ok = ok and good
        print(f"  {'ok  ' if good else 'FAIL'} {what}: {got}, wanted {want}")
    return ok


def install_listener():
    p = L.plist_path(LABEL)
    os.makedirs(os.path.dirname(p), exist_ok=True); os.makedirs(paths.CACHE_DIR, exist_ok=True)
    with open(p, "wb") as f: plistlib.dump(plist(), f)
    L.sh("launchctl", "bootout", f"{L.domain()}/{LABEL}")
    for _ in range(10):
        if L.sh("launchctl", "print", f"{L.domain()}/{LABEL}").returncode: break
        time.sleep(1)
    L.sh("launchctl", "bootstrap", L.domain(), p, check=True)
    L.sh("launchctl", "kickstart", "-k", f"{L.domain()}/{LABEL}")


def remove_listener():
    L.sh("launchctl", "bootout", f"{L.domain()}/{LABEL}")
    if os.path.exists(L.plist_path(LABEL)): os.remove(L.plist_path(LABEL))


def check():
    """Has Ryan done his half? Both admin-console changes are visible from here."""
    ip, dns, certs, may = node()
    if not ip: print("Tailscale is not up or not signed in."); return 1
    print(f"node          {dns}  ({ip})")
    print(f"{'ok     ' if certs else 'NOT YET'}  DNS -> HTTPS Certificates: " +
          (f"on, cert domain {certs}" if certs else "off -- Funnel has no certificate to serve"))
    print(f"{'ok     ' if may else 'NOT YET'}  Access controls -> funnel nodeAttrs: " +
          ("this node carries the funnel attribute" if may else "the funnel attribute is not granted to this node"))
    print("\nBoth read ok. `expose.py on` can run." if certs and may
          else "\nBoth must read ok before `expose.py on` can run.")
    return 0 if (certs and may) else 1


def on():
    ip, dns, certs, may = node()
    if not dns: raise SystemExit("no MagicDNS name -- is Tailscale up?")
    if not certs or not may:
        raise SystemExit("refusing: the admin console half is not done. Run `expose.py check`.")
    print(f"installing the exposed listener on 127.0.0.1:{PORT} ...")
    install_listener()
    if not wait_up(): remove_listener(); raise SystemExit("the listener never came up; nothing was exposed")
    print("proving the door is shut before opening it:")
    if not prove_shut(access.token()):
        remove_listener()
        raise SystemExit("REFUSED: the listener did not enforce exposed mode. Nothing was exposed; listener removed.")
    print(f"opening Funnel -> 127.0.0.1:{PORT} ...")
    r = ts("funnel", "--bg", "--yes", PORT, timeout=120)
    if r.returncode:
        remove_listener()
        raise SystemExit(f"tailscale funnel refused; nothing is exposed and the listener was removed.\n{r.stdout}{r.stderr}")
    print(r.stdout.strip())
    url = f"https://{dns}/t/{access.token()}/mcp/"
    print("\n  PUBLIC URL (this is a password -- the secret IS the address)\n")
    print(f"    {url}\n")
    print(f"  plain HTTPS root, same token:  https://{dns}/t/{access.token()}/")
    print(f"  rotate:  rm {access.TOKEN_PATH}   (a new one is made on the next request; the old URL dies)")
    return 0


def off():
    r = ts("funnel", "reset", timeout=60)
    print((r.stdout + r.stderr).strip() or "funnel reset")
    remove_listener()
    print("public listener removed. 127.0.0.1:8765 and the tailnet listener are untouched.")
    return 0


def status():
    ip, dns, certs, may = node()
    r = ts("funnel", "status")
    print((r.stdout + r.stderr).strip() or "no funnel config")
    loaded = L.sh("launchctl", "print", f"{L.domain()}/{LABEL}").returncode == 0
    print(f"\nexposed listener :{PORT}  {'loaded' if loaded else 'not loaded'}")
    if loaded and dns: print(f"public URL        https://{dns}/t/<token>/mcp/")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"check": check, "on": on, "off": off, "status": status}[cmd]() or 0)
