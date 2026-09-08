"""Who may reach this service, and with what.

Two rules, both structural rather than remembered:

  1. READ-ONLY STAYS READ-ONLY OFF THE MACHINE. `POST /rebuild` is the only route
     that changes anything (it rebuilds the service's own cache; it never writes the
     archive). It is refused for any request that did not come from loopback, so an
     exposed surface cannot start work on the machine however good its token.

  2. ANYTHING NOT FROM LOOPBACK NEEDS THE TOKEN. Loopback is unauthenticated so the
     local launchd service, the local MCP stdio server and curl on this machine keep
     working exactly as before.

     THE TRAP THIS RULE CARRIES, AND HOW IT IS CLOSED. Any reverse proxy in front --
     `tailscale serve`, `tailscale funnel`, anything else -- connects to the app FROM
     LOOPBACK, so every remote request would look local and rule 2 would let the whole
     internet in unauthenticated. So exposure is a mode, not a deployment detail:
     FOOTBALL_ARCHIVE_EXPOSED=1 requires the token from EVERY request, loopback
     included, and refuses /rebuild outright. Anything that puts a proxy in front MUST
     set it; expose.py does, and refuses to run without it.

The token lives in ~/.config/football-archive/token, mode 600, generated on first
use. It is accepted two ways, because Claude's clients differ:

  Authorization: Bearer <token>     Claude Code, curl, anything that can set a header
  /t/<token>/...  in the URL path   Claude's custom connectors, whose UI has no header
                                    field at all (anthropics/claude-ai-mcp#112) --
                                    a capability URL: the secret IS the address, so it
                                    must be treated like a password and never pasted
                                    anywhere public.
"""
import os, secrets, hmac

TOKEN_PATH = os.environ.get("FOOTBALL_ARCHIVE_TOKEN_FILE",
                            os.path.expanduser("~/.config/football-archive/token"))
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
WRITE_ROUTES = ("/rebuild",)
EXPOSED = os.environ.get("FOOTBALL_ARCHIVE_EXPOSED", "0") == "1"


def token():
    """The shared secret, created on first use. 32 bytes of urandom, base64url."""
    if os.path.exists(TOKEN_PATH):
        t = open(TOKEN_PATH).read().strip()
        if t: return t
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    t = secrets.token_urlsafe(32)
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: f.write(t + "\n")
    return t


def matches(candidate):
    return bool(candidate) and hmac.compare_digest(candidate, token())


def is_loopback(client_host):
    """True only when the request really came from this machine AND nothing is proxying:
    in exposed mode a loopback peer is a proxy hop, not a local caller."""
    return not EXPOSED and (client_host or "") in LOOPBACK


def why():
    return ("exposed: a token is required from every caller, loopback included, and /rebuild is refused"
            if EXPOSED else "local: loopback is unauthenticated, anything else needs the token")
