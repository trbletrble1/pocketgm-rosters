"""Rebuild the read model when the build tree is quiet.

LIVES HERE, NOT IN A SCRATCHPAD. It was written to the session scratchpad first, which
is session-scoped: a successor would not have had it. Anything a later session needs to
RUN belongs in the repo, the same rule as anything a later session needs to READ.

    ~/.venvs/football-archive-service/bin/python rebuild_when_quiet.py &

Armed by the Service session at 16:34 on 2026-09-07 and still waiting when that session
closed at 18:30 -- Parsing wrote to src/ and declarations/ continuously all evening, so
the quiet window never opened, which is the watcher working rather than failing. The
process does not outlive the session that started it. If no rebuild has happened, start
it again with the line above.

QUIET means both, checked directly rather than through a tool that can fail silently:
  1. nothing under build/ or build-reports/ written for QUIET_MIN minutes -- measured
     with os.stat, because `find -newermt` errors to stderr on this machine and returns
     an empty stdout, which reads exactly like "nothing was written".
  2. no other session is in state `working` in the Dropbox status file.

Then: build_read_model.py --force. --force because G3 (414 club-names records) and now
G5 (guide-pre1950-delimited) are both red and neither is this session's to fix; every
response carries the WARNING. Forcing is how the model stays current while a red is
open -- it is not how the red gets closed.
"""
import os, sys, time, glob, json, subprocess
SERVICE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SERVICE)
import paths, status as S

QUIET_MIN = 20
GIVE_UP_AFTER_MIN = 240
ME = "Service"


def newest():
    m = 0.0; who = None
    for d in (paths.BUILD, paths.BUILD_REPORTS):
        for f in glob.glob(os.path.join(d, "*.json")):
            try: t = os.stat(f).st_mtime
            except OSError: continue
            if t > m: m, who = t, os.path.relpath(f, paths.DATASET)
    return m, who


def working_sessions():
    try:
        doc = S.read()
    except Exception as e:
        return ["(status unreadable: %s)" % e]      # unknown is not quiet
    return [s["session"] for s in doc.get("sessions", [])
            if s.get("state") == "working" and s.get("session") != ME]


started = time.time()
while True:
    m, who = newest()
    quiet_for = (time.time() - m) / 60
    busy = working_sessions()
    if quiet_for >= QUIET_MIN and not busy:
        print("QUIET: %.0f min since %s, no session working. Rebuilding." % (quiet_for, who), flush=True)
        break
    if (time.time() - started) / 60 > GIVE_UP_AFTER_MIN:
        print("GAVE UP after %d min: quiet_for=%.0f busy=%s" % (GIVE_UP_AFTER_MIN, quiet_for, busy), flush=True)
        sys.exit(3)
    time.sleep(60)

py = os.path.expanduser("~/.venvs/football-archive-service/bin/python")
t0 = time.time()
r = subprocess.run([py, os.path.join(SERVICE, "build_read_model.py"), "--force"],
                   capture_output=True, text=True, cwd=SERVICE)
print("build exit %d after %.1f min" % (r.returncode, (time.time() - t0) / 60), flush=True)
print((r.stdout or "")[-1500:], flush=True)
if r.returncode: print("STDERR:", (r.stderr or "")[-1500:], flush=True)
g = subprocess.run([py, os.path.join(SERVICE, "gates.py")], capture_output=True, text=True, cwd=SERVICE)
for line in (g.stdout or "").splitlines():
    if line.startswith(("PASS", "FAIL")): print(line, flush=True)
