"""The sessions' status file: one tiny JSON in the Dropbox folder, written by each
of the four sessions, read by the service (GET /status) and the MCP tool.

WHY. Ryan says "Parsing is done", the report has not synced yet, and Claude says it
does not exist. A file this small (<2 KB) arrives ahead of the report, and the
reader can say "Parsing reports done; its report is not on this disk yet".

    python3 status.py set --session Parsing --task "stage 2 transactions" --state working
    python3 status.py set --session Parsing --state done --report reports/2026-09-07-x.md
    python3 status.py show

One file, four writers: writes are read-modify-write under an OS lock held in
/tmp (never inside Dropbox, which would sync the lock), then an atomic replace.
"""
import os, sys, json, time, fcntl, hashlib, argparse, datetime

def _archive_dir():
    """Dropbox is not in the same place on every machine: the laptop syncs to
    ~/Library/CloudStorage/Dropbox, the mini to a plain ~/Dropbox. Look for the folder
    rather than assuming, so one file works on both."""
    env = os.environ.get("FOOTBALL_ARCHIVE_DROPBOX")
    if env: return env
    for base in ("~/Library/CloudStorage/Dropbox/Football Archive", "~/Dropbox/Football Archive"):
        p = os.path.expanduser(base)
        if os.path.isdir(p): return p
    return os.path.expanduser("~/Library/CloudStorage/Dropbox/Football Archive")


ARCHIVE = _archive_dir()
PATH = os.path.join(ARCHIVE, "status.json")
STATES = ("working", "done", "blocked", "idle")
SHAPE = {
    "_what": "Who each session is, what it is working on, whether it is done, and where the report is. Written by the sessions through dataset/service/status.py; read by GET /status and the MCP tool sessions_status.",
    "_rule": "state=done means the report is WRITTEN; whether it has synced to this machine is a separate fact the reader checks (report_present).",
    "sessions": {},
}


def _lock_path():
    return os.path.join("/tmp", "football-archive-status-" + hashlib.sha1(PATH.encode()).hexdigest()[:10] + ".lock")


class Placeholder(Exception):
    """The file exists and has no bytes: Dropbox is holding it online-only on this machine."""


def load():
    if not os.path.exists(PATH): return json.loads(json.dumps(SHAPE))
    if os.path.getsize(PATH) == 0:
        # An online-only Dropbox file is a 0-byte placeholder. Reading it as "no sessions"
        # and writing a fresh document over it would ERASE every other session's entry --
        # an empty result and a failed one are the same bytes, and here they differ by
        # everyone else's work. Refuse instead.
        raise Placeholder(
            f"{PATH} is 0 bytes -- Dropbox is holding it online-only on this machine. "
            f"In Finder, right-click the 'Football Archive' folder and choose "
            f"'Make Available Offline', then try again. Refusing to write over it.")
    with open(PATH) as f: return json.load(f)


def write(doc):
    doc["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    tmp = PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, PATH)


def set_status(session, task=None, state=None, report=None, note=None):
    key = session.strip().lower()
    with open(_lock_path(), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        doc = load()
        s = doc["sessions"].setdefault(key, {"session": session.strip(), "since": datetime.datetime.now().isoformat(timespec="seconds")})
        if task is not None: s["task"] = task
        if state is not None:
            if state not in STATES: raise SystemExit(f"state must be one of {STATES}")
            if state != s.get("state"): s["since"] = datetime.datetime.now().isoformat(timespec="seconds")
            s["state"] = state
        if report is not None: s["report"] = report
        if note is not None: s["note"] = note
        s["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        write(doc)
        fcntl.flock(lk, fcntl.LOCK_UN)
    return doc


def read():
    """What the reader sees: the file, plus for each session whether its report exists on THIS disk."""
    try:
        doc = load()
    except Placeholder as e:
        return {"error": str(e), "path": PATH, "dropbox_online_only": True}
    except Exception as e:
        return {"error": f"status file unreadable: {e}", "path": PATH}
    out = {"path": PATH, "updated_at": doc.get("updated_at"), "sessions": []}
    for key, s in sorted(doc.get("sessions", {}).items()):
        rep = s.get("report")
        present = bool(rep) and os.path.exists(os.path.join(ARCHIVE, rep))
        e = dict(s)
        e["report_present_on_this_machine"] = present if rep else None
        if s.get("state") == "done" and rep and not present:
            e["reading"] = "reports done; the report has not synced to this machine yet"
        out["sessions"].append(e)
    if not out["sessions"]: out["note"] = "no session has written status yet"
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set"); s.add_argument("--session", required=True); s.add_argument("--task"); s.add_argument("--state", choices=STATES)
    s.add_argument("--report", help="path relative to the Football Archive folder, e.g. reports/2026-09-07-x.md"); s.add_argument("--note")
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "set":
        doc = set_status(a.session, a.task, a.state, a.report, a.note)
        print(json.dumps(doc["sessions"][a.session.strip().lower()], indent=1))
    else:
        print(json.dumps(read(), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
