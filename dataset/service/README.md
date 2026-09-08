# service/ — the archive, read-only, over HTTP

A FastAPI service over `dataset/build/`. Every value it returns carries the
claim that holds it and the claim carries the document. Where sources disagree
it returns every value and sets `contested`; it never chooses. There is no
policy verdict, not even opt-in (ruled 2026-09-07); `?one=1` on a person with a
contested fact returns 409 with the candidates.

    ~/.venvs/football-archive-service/bin/python build_read_model.py     # build, gate, publish (~5 min)
    ~/.venvs/football-archive-service/bin/python launchd.py install      # serve under launchd on 127.0.0.1:8765 (ruled); /docs is the OpenAPI page
    ~/.venvs/football-archive-service/bin/uvicorn app:app --port 8765    # or serve by hand
    ~/.venvs/football-archive-service/bin/python gates.py                # the four gates against the published model
    ~/.venvs/football-archive-service/bin/python gate_selftest.py        # every gate must FAIL when its invariant is broken
    ~/.venvs/football-archive-service/bin/python -m unittest discover -s tests

The read model is one SQLite file in `~/Library/Caches/football-archive-service/`
(override with `FOOTBALL_ARCHIVE_CACHE`), built from the stores, `identity.json`,
`clubs.json` and `person-merges.json`, and published by `os.replace` so a reader
never sees a partial file. The index is read once per build, for gate RS-G4 only.

| route | returns |
|---|---|
| `GET /people/{id}` | everything held about a person, by predicate family, each value with its claims |
| `GET /people?name=&year=&mode=` | candidates, never one |
| `GET /club-seasons/{league}/{year}/{club}` | the roster, each man with the stint claims that place him there and the four-state games reading |
| `GET /clubs/{id}`, `GET /clubs?name=&year=` | the club table entry, its lineage as held, and every unresolved candidate touching it |
| `GET /census/{family}?population=` | observed / contested / absent / unknown over a stated population |
| `GET /census/club-seasons?year=` | the several honest answers to "how many club-seasons", not added |
| `GET /sources`, `/sources/{id}`, `/sources/{id}/records/{locator}` | the document, and every claim one record produced (a locator containing `#` must be sent as `%23`) |
| `GET /contested?family=&league=&year=` | the disagreement worklist |
| `GET /snapshot` | what is being served, the gates, what has changed since |
| `POST /rebuild` | start a rebuild now |

Every response carries `snapshot`, and `snapshot.inputs_changed_since` says when
what you are reading is behind. **Auto-rebuild is OFF** (ruled 2026-09-07: three
sessions rewrite stores several times an hour, and a rebuild is ~5 min and ~2 GB);
`POST /rebuild` starts one on demand and the old model serves until the new one
passes its gates. `FOOTBALL_ARCHIVE_AUTOREBUILD=1` turns it back on.

| also | |
|---|---|
| `GET /status` | the four sessions' status file from Dropbox, with whether each finished report has synced here |
| `mcp_server.py` | the same queries as MCP tools over stdio, for Claude — register with `claude mcp add football-archive -- ~/.venvs/football-archive-service/bin/python <this dir>/mcp_server.py` |
| `status.py` | the sessions' status-file helper: `status.py set --session X --state working\|done --report reports/…` |
| `launchd.py` | `install` (local listener) / `install-tailnet` (adds the tailnet listener) / `uninstall` / `status` |
| `access.py` | the token, and the two access rules |

## Reaching it from another machine

Two listeners, both under launchd, both surviving a reboot (they start at login):

| listener | address | access |
|---|---|---|
| local | `127.0.0.1:8765` | unauthenticated, exactly as before |
| tailnet | `<tailscale ip>:8765` | **token required from every caller**, `POST /rebuild` refused |

The MCP server is mounted at `/mcp` over streamable HTTP, so the same 13 tools are
available to a client that is not on this machine. Two ways to authenticate:

    Authorization: Bearer <token>      Claude Code, curl -- anything that can set a header
    http://<host>:8765/t/<token>/mcp/  a capability URL, for Claude's custom connectors,
                                       whose UI has no header field (claude-ai-mcp#112)

The token is in `~/.config/football-archive/token` (mode 600, generated on first use).
A capability URL carries the secret in the address: treat it like a password.

**The trap that shaped this.** Any reverse proxy (`tailscale serve`, `funnel`, nginx)
connects to the app from loopback, so "loopback is trusted" would hand the whole
internet an open door. Exposure is therefore a mode: `FOOTBALL_ARCHIVE_EXPOSED=1`
requires the token from *every* caller and refuses `/rebuild` outright. Anything that
puts a proxy in front must set it. `launchd.py install-tailnet` does.

Claude Code on another machine on the tailnet:

    claude mcp add --transport http football-archive http://<tailscale-ip>:8765/mcp/ --header "Authorization: Bearer <token>"

Claude's custom connectors (claude.ai web, Desktop, mobile) **cannot** use the tailnet
address: they connect from Anthropic's cloud, not from the device. That needs a public
HTTPS URL -- see the report `2026-09-07-reaching-the-archive-remotely.md`.

## The six gates (four ruled 2026-09-07, RS-G5 and RS-G6 the same day)

- **RS-G1** a date-family string the reader cannot read, not declared in `declarations/dates-as-printed.json`, fails.
- **RS-G2** a person-scoped claim whose id resolves to nobody, in a store `declarations/person-index-rebuild.json` does not declare as known-unresolvable, fails.
- **RS-G3** a claim naming a source record its store's table does not hold, or naming none, fails.
- **RS-G4** the people here must equal the people in the index; a difference is listed and fails.
- **RS-G5** a file in `build/` that is not a store here and that `declarations/build-files.json`
  does not explain, fails -- and so does a declared file that has since grown a `claims` list,
  or one that has vanished. A file with claims that the build never read is *pending a rebuild*,
  shown on every run and not a failure.

**Why RS-G5 exists.** The reader takes a JSON object with a top-level `claims` list and
skipped everything else **in silence**: a file that failed to parse logged one line and
the build published anyway, a file with an unrecognised shape logged nothing at all. A
store that broke or was written in a shape the reader does not know would have vanished
with the build still reporting success. Ryan, 2026-09-07: *"four was never a magic
number -- it was how many properties needed checking at the time"*. It found
`guide-pre1950-delimited` on its first run: 1,653 claims nested under
`runs[].guides[].claims`, none of them in the model, and `bio_select.py` reads the same
file directly -- which is how a bio panel can show a guide height the archive does not hold.

**RS-, because the numbers collide.** Parsing's own gates are numbered G1-G9 and that
numbering is stamped into `gate_pfa.py`'s output and quoted by number in declarations.
These are the read service's, they are newer, and they were the cheap ones to renumber
(Fetching's call, and it is right).

**RS-G5 does not trust the reader, it tests it.** It imports
`build_read_model.is_claim_store` -- the reader's own and only test for what a claim
store is -- rather than restating it, because two copies of that rule would drift
silently on both sides, which is the very defect the gate exists for. And on every run it
puts seven specimens through that predicate: the shape it must accept, and six it must
refuse, including the nested-claims shape and the empty object a truncated write leaves.
A predicate that quietly widens or narrows fails the gate by name instead of changing
what the archive holds in silence. That is Fetching's P4, carried over from
`src/gate_photographs_measurable.py`: show the reader something it cannot read and
require it to notice, rather than waiting for a real file to prove it.

- **RS-G6** a contested fact whose values all read to the same thing under
  `dataset/declarations/readings.json` fails. *A disagreement between two values that
  read to the same thing is not a disagreement* (Ryan, 2026-09-07) -- given for drafts
  and for `61"` read as `6-1`, and stated as a property, not a special case. RS-G1 was
  the first instance before anyone saw it as one: two spellings of a calendar day are
  one day.

  The reading is **Parsing's** `dataset/src/readings.py`, loaded by file path through
  `reading_view.py`. This gate does not carry its own copy of it. **Nothing is
  normalised** -- the store keeps what each source printed, and the reading is derived
  at read time and labelled `derived`, with both printed forms kept beside it. A value
  the reader cannot read takes no part and is counted. If the reader cannot be loaded
  at all, RS-G6 **fails** rather than report a clean sheet it did not check.

A failing gate refuses to publish; the previous model keeps serving.
`build_read_model.py --force` publishes anyway and every response then carries a
WARNING. **There is no exception list for RS-G3, RS-G4 or RS-G5** (ruled 2026-09-07): defects in
other sessions' stores stay uncomfortable until fixed. G1 also fails on a declared
string that is no longer in the store, so a corrected source un-declares itself
loudly rather than being silently reread. Undeclared `source_id`s are information,
printed on every `gates.py` run so they never become normal. Nothing checks whether
a value is correct.

## Declarations (this directory)

- `declarations/predicate-families.json` — which predicates ask the same question. The service groups within a family and nowhere else.
- `declarations/dates-as-printed.json` — strings a source printed that are not dates, looked at and declared so G1 can tell an odd source from a broken reader.
