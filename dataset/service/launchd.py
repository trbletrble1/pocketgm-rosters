"""Run the service under launchd so it is there when Ryan is not at the machine.
Ruled 2026-09-07. Auto-rebuild stays OFF; POST /rebuild is on demand.

TWO LISTENERS, deliberately separate rather than one bound to 0.0.0.0:

  local    127.0.0.1:8765          unauthenticated, as it has always been. Nothing off
                                   this machine can reach a loopback bind, so the local
                                   tools, curl and the stdio MCP server are unchanged.
  tailnet  <tailscale ip>:8765     EXPOSED mode: a token is required from every caller
                                   and /rebuild is refused. Reachable only from Ryan's
                                   own tailnet -- the network is the first gate and the
                                   token is the second.

One bind to 0.0.0.0 would have been simpler and would also publish the service to
whatever wifi the laptop is on. Two binds cost one plist.

    python3 launchd.py install            # local listener
    python3 launchd.py install-tailnet    # tailnet listener too (needs Tailscale up)
    python3 launchd.py uninstall | status
"""
import os, sys, time, json, subprocess, plistlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths

LABEL = "com.football-archive.service"
TAILNET_LABEL = LABEL + ".tailnet"
VENV = os.path.expanduser("~/.venvs/football-archive-service")
PORT = os.environ.get("FOOTBALL_ARCHIVE_PORT", "8765")
TAILSCALE = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


def plist_path(label): return os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")


def tailscale_names():
    """(ipv4, magicdns name) for this node, read once at install time and written into the
    plist as FOOTBALL_ARCHIVE_HOSTS. Computed here rather than by the server at runtime:
    under launchd the Tailscale binary is not reliably callable, so the server was starting
    with only loopback in its allowed-Host list and refusing every tailnet MCP request."""
    for cmd in ([TAILSCALE, "status", "--json"], ["tailscale", "status", "--json"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode: continue
            self_ = json.loads(r.stdout).get("Self") or {}
            ip = next((i for i in (self_.get("TailscaleIPs") or []) if ":" not in i), None)
            dns = (self_.get("DNSName") or "").rstrip(".") or None
            if ip: return ip, dns
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
    return None, None


def tailscale_ip():
    for cmd in ([TAILSCALE, "ip", "-4"], ["tailscale", "ip", "-4"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            ip = r.stdout.strip().splitlines()[0].strip() if r.stdout.strip() else ""
            if ip.startswith("100."): return ip
        except (OSError, IndexError, subprocess.TimeoutExpired):
            continue
    return None


def plist(label=LABEL, host="127.0.0.1", exposed=False, log="server.log", hosts=()):
    env = {"FOOTBALL_ARCHIVE_AUTOREBUILD": "0", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    if exposed: env["FOOTBALL_ARCHIVE_EXPOSED"] = "1"
    if hosts: env["FOOTBALL_ARCHIVE_HOSTS"] = ",".join(h for h in hosts if h)
    return {
        "Label": label,
        "ProgramArguments": [os.path.join(VENV, "bin", "uvicorn"), "app:app", "--host", host, "--port", PORT, "--log-level", "warning"],
        "WorkingDirectory": HERE,
        "EnvironmentVariables": env,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 30,          # the tailnet bind fails while Tailscale is down; do not spin
        "StandardOutPath": os.path.join(paths.CACHE_DIR, log),
        "StandardErrorPath": os.path.join(paths.CACHE_DIR, log),
    }


def sh(*args, check=False):
    r = subprocess.run(list(args), capture_output=True, text=True)
    if check and r.returncode: raise SystemExit(f"{' '.join(args)}\n{r.stdout}{r.stderr}")
    return r


def domain(): return f"gui/{os.getuid()}"


def _install(label, host, exposed, log, hosts=()):
    p = plist_path(label)
    os.makedirs(os.path.dirname(p), exist_ok=True); os.makedirs(paths.CACHE_DIR, exist_ok=True)
    with open(p, "wb") as f: plistlib.dump(plist(label, host, exposed, log, hosts), f)
    sh("launchctl", "bootout", f"{domain()}/{label}")            # replace a previous copy quietly
    for _ in range(10):                                          # bootout is asynchronous; bootstrap fails with EIO while the old copy is still going
        if sh("launchctl", "print", f"{domain()}/{label}").returncode: break
        time.sleep(1)
    sh("launchctl", "bootstrap", domain(), p, check=True)
    sh("launchctl", "kickstart", "-k", f"{domain()}/{label}")
    print(f"installed {p}\n  listening on http://{host}:{PORT}" + ("   [EXPOSED: token required, /rebuild refused]" if exposed else "   [local: unauthenticated loopback]"))


def install():
    _install(LABEL, "127.0.0.1", False, "server.log")


def install_tailnet():
    ip, dns = tailscale_names()
    if not ip:
        raise SystemExit("no Tailscale IPv4 address -- is Tailscale running and signed in?")
    install()
    _install(TAILNET_LABEL, ip, True, "server-tailnet.log", hosts=(ip, dns))
    import access
    print(f"\n  tailnet URL   http://{ip}:{PORT}" + (f"   or   http://{dns}:{PORT}" if dns else ""))
    print(f"  MCP endpoint  http://{ip}:{PORT}/mcp/    (Authorization: Bearer <token>)")
    print(f"  token file    {access.TOKEN_PATH}")


def uninstall():
    for label in (TAILNET_LABEL, LABEL):
        sh("launchctl", "bootout", f"{domain()}/{label}")
        if os.path.exists(plist_path(label)): os.remove(plist_path(label))
    print("uninstalled both listeners")


def status():
    rc = 1
    for label in (LABEL, TAILNET_LABEL):
        r = sh("launchctl", "print", f"{domain()}/{label}")
        if r.returncode: print(f"{label}: not loaded"); continue
        rc = 0
        bits = [line.strip() for line in r.stdout.splitlines() if any(k in line for k in ("state =", "pid =", "runs ="))]
        print(f"{label}: " + "  ".join(bits))
    return rc


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"install": install, "install-tailnet": install_tailnet, "uninstall": uninstall, "status": status}[cmd]() or 0)
