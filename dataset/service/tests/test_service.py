"""Tests that do not need a built read model run always; endpoint tests run when one exists.

    ~/.venvs/football-archive-service/bin/python -m unittest discover -s tests -v
"""
import os, sys, json, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); SVC = os.path.dirname(HERE); sys.path.insert(0, SVC)
import paths, dates, families, identity, snapshot


class Dates(unittest.TestCase):
    def test_reads_every_form_the_store_holds(self):
        for s, want in [("May 12, 1925", (1925, 5, 12)), ("1925-05-12", (1925, 5, 12)), ("1949-12-1", (1949, 12, 1)), ("Sept. 3, 1950", (1950, 9, 3)),
                        ("December 1977", (1977, 12, None)), ("c. 1960", (1960, None, None)), ("1937?", (1937, None, None)),
                        ("August 9, 1989 (aged 72)", (1989, 8, 9)), ("April 3, 1925 in Warren, Ohio.", (1925, 4, 3)),
                        ("August 7, 1901Avilés, Asturias, Spain", (1901, 8, 7)), ("1924-4-21)", (1924, 4, 21)), ("{{nowrap|1994-12-31", (1994, 12, 31)), ("1999-4-17 (aged 64 or 65)", (1999, 4, 17))]:
            r = dates.read(s); self.assertIsNotNone(r, s); self.assertEqual(dates.key(r), want, s)

    def test_refuses_what_is_not_a_date(self):
        for s in ["c", "1888-8-17 or 1890-5-15", "None", None, "", "May 40, 1925", "1925-13-01", "April 0, 1996", "July 32, 1932"]:
            self.assertIsNone(dates.read(s), s)

    def test_never_rewrites(self):
        s = "May 12, 1925"; dates.read(s); self.assertEqual(s, "May 12, 1925")

    def test_same_day_groups(self):
        R = dates.read
        self.assertEqual(dates.same_day_groups([("May 12, 1925", R("May 12, 1925")), ("1925-05-12", R("1925-05-12")), ("May 13, 1925", R("May 13, 1925"))]),
                         [["May 12, 1925", "1925-05-12"], ["May 13, 1925"]])
        # a year joins the one day of that year; stands alone between two
        self.assertEqual(dates.same_day_groups([("May 12, 1925", R("May 12, 1925")), ("1925", R("1925"))]), [["May 12, 1925", "1925"]])
        self.assertEqual(dates.same_day_groups([("May 12, 1925", R("May 12, 1925")), ("May 13, 1925", R("May 13, 1925")), ("1925", R("1925"))]),
                         [["May 12, 1925"], ["May 13, 1925"], ["1925"]])


class Families(unittest.TestCase):
    def test_declared_families_only(self):
        self.assertEqual(families.family_of("pfa.birth_date"), "birth_date")
        self.assertEqual(families.family_of("hometown"), "hometown")          # a family of one: not folded with birth_place
        self.assertEqual(families.family_of("pfa.birth_place"), "pfa.birth_place")
        self.assertEqual(families.kind_of("birth_date"), "date")

    def test_no_predicate_in_two_families(self):
        families.load()


@unittest.skipUnless(os.path.exists(paths.IDENTITY), "archive not present")
class Identity(unittest.TestCase):
    def test_agrees_with_the_builders_rule(self):
        """The one place a local id becomes a person: ours and build_person_index.resolve_person must agree."""
        sys.path.insert(0, os.path.join(paths.DATASET, "src"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("bpi", os.path.join(paths.DATASET, "src", "build_person_index.py"))
        src = open(spec.origin).read()
        # take only the function, not the module (its imports run gate code)
        import collections, glob
        ns = {"os": os, "sys": sys, "json": json, "collections": collections, "glob": glob}
        body = src[src.index("def resolve_person"):]; body = body[:body.index("\n\n\n")]     # the function only; what follows it is theirs to change
        exec(body, ns)
        I = identity.Identity()
        sample = list(I.loc2g.items())[:2000]
        for (store, local), g in sample:
            self.assertEqual(I.resolve(store, local), ns["resolve_person"](store, local, I.loc2g))
            self.assertEqual(I.resolve("stats-" + store, local), ns["resolve_person"]("stats-" + store, local, I.loc2g))
        self.assertEqual(I.resolve("anything", "P_000001"), "P_000001")
        self.assertIsNone(I.resolve("no-such-store", "p_000001"))


class Access(unittest.TestCase):
    """The two access rules, exercised against a client whose peer address is NOT loopback."""

    def app(self, exposed):
        import importlib, access as A, app as APP
        os.environ["FOOTBALL_ARCHIVE_EXPOSED"] = "1" if exposed else "0"
        importlib.reload(A); importlib.reload(APP)
        from fastapi.testclient import TestClient
        APP.AUTO_REBUILD = False
        return APP, A, TestClient(APP.app, client=("10.0.0.9", 1234))

    def tearDown(self):
        os.environ["FOOTBALL_ARCHIVE_EXPOSED"] = "0"
        import importlib, access as A, app as APP; importlib.reload(A); importlib.reload(APP)

    @unittest.skipUnless(os.path.exists(paths.READ_MODEL), "no read model built")
    def test_off_machine_needs_a_token(self):
        APP, A, c = self.app(exposed=False)
        self.assertEqual(c.get("/sources").status_code, 401)
        self.assertEqual(c.get("/sources", headers={"Authorization": f"Bearer {A.token()}"}).status_code, 200)
        self.assertEqual(c.get(f"/t/{A.token()}/sources").status_code, 200)      # capability URL
        self.assertEqual(c.get("/t/wrong/sources").status_code, 401)

    def test_rebuild_is_refused_off_the_machine(self):
        APP, A, c = self.app(exposed=False)
        self.assertEqual(c.post("/rebuild", headers={"Authorization": f"Bearer {A.token()}"}).status_code, 403)

    def test_exposed_mode_trusts_no_one(self):
        """A proxy in front makes every remote request look like loopback, so exposed mode
        must require the token from loopback too and refuse /rebuild outright."""
        APP, A, c = self.app(exposed=True)
        loop = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(APP.app, client=("127.0.0.1", 5555))
        self.assertFalse(A.is_loopback("127.0.0.1"))
        self.assertEqual(loop.get("/sources").status_code, 401)
        self.assertEqual(loop.post("/rebuild", headers={"Authorization": f"Bearer {A.token()}"}).status_code, 403)

    def test_token_file_is_private(self):
        import access as A
        self.assertEqual(oct(os.stat(A.TOKEN_PATH).st_mode)[-3:], "600")

    def test_discovery_paths_answer_404_not_401(self):
        """An MCP client probes for an OAuth authorization server BEFORE it has any
        credential. Answering 401 there says "I want OAuth" and refuses to say where,
        which is a dead end -- it is what stopped Claude's connector. This service has
        no OAuth, so every path under /.well-known/ must say 404, in both modes, to a
        caller with nothing. The property, not three remembered paths."""
        for exposed in (False, True):
            APP, A, c = self.app(exposed)
            for path in ("/.well-known/oauth-protected-resource",
                         "/.well-known/oauth-authorization-server",
                         "/.well-known/openid-configuration",
                         "/.well-known/oauth-protected-resource/mcp",
                         "/.well-known/anything-at-all"):
                r = c.get(path)
                self.assertEqual(r.status_code, 404, f"{path} exposed={exposed}")
                self.assertNotIn("www-authenticate", {k.lower() for k in r.headers})

    def test_no_redirect_ever_drops_the_token(self):
        """The token is stripped from the path before routing, so anything the router
        builds from that path comes back without it -- the trailing-slash redirect was
        sending a caller to a tokenless URL and straight into 401. Assert the property
        over every declared route and the mounted MCP app, not the one path that bit."""
        from urllib.parse import urlsplit
        APP, A, c = self.app(exposed=True)
        tok = A.token()
        paths = [r.path for r in APP.app.routes if getattr(r, "path", None)] + ["/mcp"]
        checked = 0
        with c:                      # runs the lifespan, so the mounted MCP app is live
            for path in paths:
                if "{" in path: continue
                for candidate in (path.rstrip("/"), path.rstrip("/") + "/"):
                    if not candidate: continue
                    r = c.request("POST", f"/t/{tok}{candidate}", follow_redirects=False)
                    if not 300 <= r.status_code < 400: continue
                    loc = r.headers.get("location", "")
                    self.assertTrue(urlsplit(loc).path.startswith(f"/t/{tok}"),
                                    f"redirect from {candidate} dropped the token: {loc}")
                    checked += 1
        self.assertGreater(checked, 0, "no redirect was exercised; the test proves nothing")


@unittest.skipUnless(os.path.exists(paths.READ_MODEL), "no read model built")
class Endpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import app as A, access
        A.AUTO_REBUILD = False
        # TestClient's peer is not loopback, so it is treated as off-machine and carries the token.
        cls.c = TestClient(A.app, headers={"Authorization": f"Bearer {access.token()}"})

    def get(self, path, **params):
        r = self.c.get(path, params=params); return r.status_code, r.json()

    def test_snapshot_on_every_response(self):
        s, b = self.get("/sources"); self.assertEqual(s, 200); self.assertIn("snapshot", b); self.assertIn("gates", b["snapshot"])

    def test_person_holds_every_value_and_never_chooses(self):
        s, b = self.get("/contested", family="birth_date", limit=1); self.assertEqual(s, 200)
        if not b["items"]: self.skipTest("no contested birth date in this model")
        pid = b["items"][0]["person"]
        s, p = self.get(f"/people/{pid}"); self.assertEqual(s, 200)
        f = p["facts"]["birth_date"]; self.assertTrue(f["contested"]); self.assertGreater(len(f["values"]), 1)
        for v in f["values"]:
            self.assertTrue(v["claims"]); self.assertTrue(all(c["source_record"] for c in v["claims"]))
        self.assertTrue(f["same_day"]["derived"])
        s, o = self.get(f"/people/{pid}", one="true"); self.assertEqual(s, 409); self.assertIn("candidates", o)

    def test_search_returns_candidates(self):
        s, b = self.get("/people", name="Chuck Noll"); self.assertEqual(s, 200); self.assertIn("candidates", b); self.assertIn("not an answer", b["note"])

    def test_empty_and_missing_are_different_bytes(self):
        s, b = self.get("/club-seasons/NFL/1950/NOSUCHCLUB"); self.assertEqual(s, 404); self.assertIn("nearest_names", b)
        s, b = self.get("/club-seasons/NFL/1950/BA1"); self.assertEqual(s, 200); self.assertGreater(b["n_members"], 0)

    def test_census_sums_to_population(self):
        s, b = self.get("/census/death_date"); self.assertEqual(s, 200)
        self.assertEqual(sum(b["basis"].values()), b["population"]["n"])

    def test_source_record_walks_to_the_document(self):
        s, p = self.get("/people/P_000001"); self.assertEqual(s, 200)
        c = next(v["claims"][0] for v in p["facts"]["birth_date"]["values"])
        from urllib.parse import quote
        sid, loc = c["source_record"].split("#", 1)        # a locator may itself contain '#': encode it, or the URL reads it as a fragment
        s, r = self.get(f"/sources/{sid}/records/{quote(loc, safe='/')}"); self.assertEqual(s, 200); self.assertTrue(r["claims"])
        self.assertEqual(r["source_record"], c["source_record"])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(os.path.exists(paths.READ_MODEL), "no read model built")
class Bio(unittest.TestCase):
    """The bio endpoint. Three properties, none of them about the prose itself --
    what a bio says is Parsing's file and Parsing's ruling."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import app as A, access
        A.AUTO_REBUILD = False
        cls.c = TestClient(A.app, headers={"Authorization": f"Bearer {access.token()}"})
        cls.people = [it["person"] for it in
                      cls.c.get("/contested", params={"family": "birth_date", "limit": 12}).json()["items"]]

    def test_a_bio_request_writes_nothing(self):
        """The generator reads the build stores directly, in this process. Assert it
        cannot have written to them: every file it touches must have the same mtime
        and size after a bio as before. The property over all of them, not a review
        of the source."""
        import bios
        before = bios._stamp(bios.INPUTS)
        for pid in self.people[:3]:
            self.c.get(f"/people/{pid}/bio")
        self.assertEqual(before, bios._stamp(bios.INPUTS))

    def test_the_bio_never_hides_a_contested_fact(self):
        """A sentence cannot hold two birth dates, so the prose says one thing. The
        page must still carry every value with its claims, or the bio has become a
        way round the contested rule. Asserted over every contested man the worklist
        offers, not the one that was checked by hand."""
        checked = 0
        for pid in self.people:
            b = self.c.get(f"/people/{pid}/bio")
            self.assertEqual(b.status_code, 200, pid)
            d = b.json()
            self.assertTrue(d.get("contested"), f"{pid}: contested list is empty on a contested man")
            for c in d["contested"]:
                fam = d["facts"].get(c["family"]) or {}
                vals = fam.get("values") or []
                self.assertGreater(len(vals), 1, f"{pid}: {c['family']} carries one value on the page")
                self.assertTrue(all(v.get("claims") for v in vals), f"{pid}: a value with no claims")
                checked += 1
        self.assertGreater(checked, 0, "no contested man was exercised; the test proves nothing")

    def test_prose_and_panel_are_both_labelled_derived(self):
        """A bio is assembled from claims at read time and is not itself a claim. It
        is labelled the way the display name and the date reading are labelled -- and
        so is the panel, which is equally derived."""
        for pid in self.people[:5]:
            d = self.c.get(f"/people/{pid}/bio").json()
            if not d.get("bio", {}).get("value"): continue
            for layer in ("bio", "panel"):
                self.assertTrue(d[layer]["derived"], f"{pid}: {layer} not marked derived")
                self.assertEqual(d[layer]["basis"], "derived", f"{pid}: {layer} basis")
                self.assertTrue(d[layer]["recipe"].startswith("bio/"), f"{pid}: {layer} recipe")

    def test_the_page_reports_both_directions_of_panel_drift(self):
        """The panel can be QUIETER than the claims (a disagreement the archive holds and
        the panel settles) or NOISIER (a disagreement the panel reports and the archive
        does not hold). Noise is the more dangerous direction -- quiet loses information,
        noise invents it -- and both must be visible on the page. Asserted as the property
        over whatever the endpoint returns, not against a remembered example."""
        import json as _json
        seen_noisy = 0
        pids = self.people[:6] + ["P_000750"]
        for pid in pids:
            d = self.c.get(f"/people/{pid}/bio").json()
            if not d.get("bio", {}).get("value"): continue
            self.assertIn("panel_quieter_than_the_claims", d, pid)
            self.assertIn("panel_noisier_than_the_claims", d, pid)
            reported = {x["field"] for x in d["panel_noisier_than_the_claims"]}
            held = {c["family"] for c in d.get("contested") or []}
            for field in d["panel"]["disagreements"]:
                fams = [f for f in (field, "pfa." + field) if f in (d.get("facts") or {})]
                vals = set()
                for f in fams:
                    for v in (d["facts"][f].get("values") or []):
                        vals.add(_json.dumps(v.get("value"), sort_keys=True))
                if field not in held and len(vals) <= 1:
                    self.assertIn(field, reported,
                                  f"{pid}: panel disagrees on {field} but the archive holds "
                                  f"{len(vals)} value(s) and the page does not say so")
                    seen_noisy += 1
        self.assertGreater(seen_noisy, 0, "no manufactured disagreement was exercised; the test proves nothing")
