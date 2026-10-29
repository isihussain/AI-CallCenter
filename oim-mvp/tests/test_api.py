"""HTTP integration checks using temporary storage and synthetic customer data."""
import http.client
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("api_test_backend", Path(__file__).resolve().parents[1] / "backend.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = backend.hash_password("Synthetic-test-password")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_patch = patch.object(backend, "DB_PATH", str(Path(self.directory.name) / "test.db"))
        self.secret_patch = patch.object(backend, "SECRET_PATH", str(Path(self.directory.name) / "test.secret"))
        self.db_patch.start()
        self.secret_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.secret_patch.stop)
        backend.SESSIONS.clear()
        backend.LOGIN_ATTEMPTS.clear()
        self.external_calls = patch.object(backend.urllib.request, "urlopen", side_effect=AssertionError("External provider calls are forbidden in API tests"))
        self.external_calls.start()
        self.addCleanup(self.external_calls.stop)
        with closing(backend.db()) as conn, conn:
            for tid, name, role in ((1, "Demo Administrator", "admin"), (2, "Demo Studio", "customer"), (3, "Example Workshop", "customer")):
                conn.execute("INSERT INTO tenants(id,name,username,password_hash,role,credits,created_at) VALUES(?,?,?,?,?,100,?)",
                             (tid, name, f"test-{tid}", self.password_hash, role, backend.now()))
                backend.SESSIONS[f"session-{tid}"] = {"tenant_id":tid, "role":role, "expires":backend.now()+3600}
            for tid in (2, 3):
                conn.execute("INSERT INTO calls(tenant_id,call_id,caller,status,started_at,ended_at) VALUES(?,?,?,'ended',100,220)", (tid, f"call-{tid}", f"demo-caller-{tid}"))
                conn.execute("INSERT INTO appointments(tenant_id,customer_name,phone,service,appointment_at,created_at) VALUES(?,?,?,?,?,?)",
                             (tid, f"Demo Contact {tid}", "demo-phone", "Consultation", "2026-10-29T10:00:00+03:00", 100))
                conn.execute("INSERT INTO crm_contacts(id,tenant_id,name,phone,created_at,updated_at) VALUES(?,?,?,?,100,100)", (tid, tid, f"Demo Contact {tid}", "demo-phone"))
                conn.execute("INSERT INTO knowledge_documents(id,tenant_id,language,title,content,status,created_at,updated_at) VALUES(?,?,'en',?,?,'published',100,100)",
                             (tid, tid, f"Demo knowledge {tid}", f"Original customer content {tid}"))
                conn.execute("INSERT INTO tenant_ai_settings(tenant_id,greeting,updated_at) VALUES(?,?,100)", (tid, f"Original greeting {tid}"))
            for key in ("user_agreement", "kvkk_text"):
                conn.execute("INSERT OR REPLACE INTO system_settings(key,value,updated_at) VALUES(?,'Synthetic legal text',100)", (key,))
        self.server = backend.ThreadingHTTPServer(("127.0.0.1", 0), backend.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval":0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, data=None, tenant=2):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        headers = {}
        if tenant is not None:
            headers["Cookie"] = f"oim_session=session-{tenant}"
        payload = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(data)
        try:
            conn.request(method, path, payload, headers)
            response = conn.getresponse()
            result = json.loads(response.read())
            return response.status, result, dict(response.getheaders())
        finally:
            conn.close()

    def get(self, path, tenant=2):
        status, data, _ = self.request("GET", path, tenant=tenant)
        self.assertEqual(status, 200, data)
        return data


class TenantIsolationTests(ApiTestCase):
    def test_protected_endpoints_require_a_session(self):
        for path in ("/api/me", "/api/calls", "/api/appointments", "/api/contacts", "/api/knowledge", "/api/tenant/ai-settings", "/api/admin/tenants"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path, tenant=None)[0], 401)
        self.assertEqual(self.request("POST", "/api/tenant/ai-settings", {"greeting":"Test"}, tenant=None)[0], 401)

    def test_customers_cannot_override_their_read_scope(self):
        for tid in (2, 3):
            other = 3 if tid == 2 else 2
            for path in ("/api/calls", "/api/appointments", "/api/contacts", "/api/knowledge"):
                with self.subTest(tenant=tid, path=path):
                    data = self.get(f"{path}?tenant_id={other}", tenant=tid)
                    self.assertEqual(len(data["items"]), 1)
                    text = json.dumps(data["items"])
                    self.assertNotIn(f"Demo Contact {other}", text)
                    self.assertNotIn(f"Demo knowledge {other}", text)
                    self.assertNotIn(f"call-{other}", text)
            self.assertEqual(self.get(f"/api/tenant/ai-settings?tenant_id={other}", tid)["greeting"], f"Original greeting {tid}")

    def test_cross_customer_contact_reads_and_writes_are_rejected(self):
        self.assertEqual(self.request("GET", "/api/contacts/3?tenant_id=3")[0], 404)
        for action in ("update", "delete"):
            status, _, _ = self.request("POST", f"/api/contacts/3/{action}", {"tenant_id":3, "name":"Overwritten"})
            self.assertEqual(status, 404)
        self.assertEqual(self.get("/api/contacts", tenant=3)["items"][0]["name"], "Demo Contact 3")

    def test_contact_mutations_work_with_post_and_get_is_read_only(self):
        self.assertEqual(self.request("GET", "/api/contacts/2/delete")[0], 405)
        self.assertEqual(len(self.get("/api/contacts")["items"]), 1)
        self.assertEqual(self.request("POST", "/api/contacts/2/update", {"name":"Updated demo contact"})[0], 200)
        self.assertEqual(self.get("/api/contacts")["items"][0]["name"], "Updated demo contact")
        self.assertEqual(self.request("POST", "/api/contacts/2/delete", {})[0], 200)
        self.assertEqual(self.get("/api/contacts")["items"], [])

    def test_knowledge_updates_cannot_change_another_tenant(self):
        payload = {"tenant_id":3, "id":3, "language":"en", "title":"Changed", "content":"Changed", "status":"published"}
        self.assertEqual(self.request("POST", "/api/knowledge", payload)[0], 404)
        self.assertEqual(self.get("/api/knowledge", tenant=3)["items"][0]["content"], "Original customer content 3")
        payload["id"] = 2
        self.assertEqual(self.request("POST", "/api/knowledge", payload)[0], 200)
        self.assertEqual(self.get("/api/knowledge")["items"][0]["content"], "Changed")

    def test_ai_settings_writes_use_the_session_tenant(self):
        message = "Здравствуйте! Demo greeting stays in its original language."
        self.assertEqual(self.request("POST", "/api/tenant/ai-settings", {"tenant_id":3,"greeting":message,"voice":"coral"})[0], 200)
        self.assertEqual(self.get("/api/tenant/ai-settings")["greeting"], message)
        self.assertEqual(self.get("/api/tenant/ai-settings", 3)["greeting"], "Original greeting 3")

    def test_customer_created_records_stay_with_their_session(self):
        self.assertEqual(self.request("POST", "/api/contacts", {"tenant_id":3,"name":"New demo contact"})[0], 200)
        self.assertEqual(len(self.get("/api/contacts")["items"]), 2)
        self.assertEqual(len(self.get("/api/contacts", 3)["items"]), 1)

    def test_administrator_routes_reject_customer_sessions(self):
        for path in ("/api/admin/tenants", "/api/admin/providers", "/api/admin/billing", "/api/admin/legal-settings", "/api/admin/tenants/3/sip"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 403)
        for path in ("/api/admin/tenants", "/api/admin/providers", "/api/admin/billing", "/api/admin/tenants/3/credits", "/api/admin/tenants/3/password", "/api/admin/tenants/3/sip"):
            with self.subTest(path=path):
                self.assertEqual(self.request("POST", path, {})[0], 403)

    def test_administrator_can_select_and_update_a_customer(self):
        self.assertEqual(self.get("/api/calls?tenant_id=3", 1)["items"][0]["call_id"], "call-3")
        self.assertEqual(self.get("/api/contacts?tenant_id=3", 1)["items"][0]["name"], "Demo Contact 3")
        self.assertEqual(self.request("POST", "/api/contacts/3/update", {"tenant_id":3,"name":"Admin edit"}, 1)[0], 200)
        self.assertEqual(self.get("/api/contacts", 3)["items"][0]["name"], "Admin edit")
        payload = {"name":"New synthetic tenant","username":"new-demo","password":"Synthetic-unique-password","agreement_accepted":True}
        self.assertEqual(self.request("POST", "/api/admin/tenants", payload, 1)[0], 200)

    def test_real_login_issues_a_secure_http_only_cookie(self):
        status, data, headers = self.request("POST", "/api/login", {"username":"test-2","password":"Synthetic-test-password"}, None)
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["id"], 2)
        self.assertIn("Secure", headers["Set-Cookie"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])


class CallHistoryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.day = 1793232000  # 2026-10-29 00:00:00 UTC
        with closing(backend.db()) as conn, conn:
            conn.execute("DELETE FROM calls")
            for i in range(123):
                status = "failed" if i % 3 == 0 else "ended"
                caller = "demo-100" if i % 2 == 0 else "demo-200"
                started = self.day + (i // 30) * 86400
                conn.execute("INSERT INTO calls(tenant_id,call_id,caller,status,started_at,ended_at,billed_credits) VALUES(2,?,?,?,?,?,0.5)",
                             (f"history-{i}", caller, status, started, started+120))
                conn.execute("INSERT INTO call_usage(call_id,total_tokens,estimated_openai_usd,updated_at) VALUES(?,10,0.01,100)", (f"history-{i}",))
            conn.execute("INSERT INTO calls(tenant_id,call_id,caller,status,started_at) VALUES(3,'private-other-tenant','demo-100','ended',?)", (self.day,))

    def test_pages_reach_older_calls_and_have_stable_tie_ordering(self):
        first = self.get("/api/calls?page_size=50")
        self.assertEqual(first["pagination"]["total"], 123)
        self.assertEqual(first["summary"]["total_calls"], 123)
        self.assertEqual(first["summary"]["total_tokens"], 1230)
        self.assertAlmostEqual(first["summary"]["estimated_openai_usd"], 1.23)
        self.assertEqual(first["items"][0]["call_id"], "history-122")
        calls = []
        for page in (1,2,3):
            result = self.get(f"/api/calls?page_size=50&page={page}&snapshot_id={first['pagination']['snapshot_id']}")
            calls.extend(x["call_id"] for x in result["items"])
            self.assertNotIn("private-other-tenant", calls)
        self.assertEqual(len(calls), 123)
        self.assertEqual(len(set(calls)), 123)
        self.assertEqual(calls[-1], "history-0")

    def test_snapshot_keeps_new_calls_out_of_subsequent_pages(self):
        first = self.get("/api/calls?page_size=25")
        with closing(backend.db()) as conn, conn:
            conn.execute("INSERT INTO calls(tenant_id,call_id,status,started_at) VALUES(2,'new-call','incoming',?)", (self.day+999999,))
        after = self.get(f"/api/calls?page=2&page_size=25&snapshot_id={first['pagination']['snapshot_id']}")
        self.assertEqual(after["pagination"]["total"], 123)
        self.assertFalse(set(x["call_id"] for x in first["items"]) & set(x["call_id"] for x in after["items"]))
        self.assertEqual(self.get("/api/calls")["summary"]["total_calls"], 124)

    def test_filters_apply_to_full_history_with_inclusive_utc_dates(self):
        result = self.get("/api/calls?date_from=2026-10-29&date_to=2026-10-29&status=ended&caller=100&page_size=5")
        self.assertEqual(result["pagination"]["total"], 10)
        self.assertEqual(len(result["items"]), 5)
        self.assertEqual(result["summary"]["completed_calls"], 10)
        self.assertEqual(result["summary"]["average_duration_seconds"], 120)
        self.assertEqual(result["summary"]["billed_credits"], 5)
        self.assertEqual(result["traffic"], [{"day":"2026-10-29","calls":10}])

    def test_caller_wildcards_are_literal(self):
        self.assertEqual(self.get("/api/calls?caller=%25")["items"], [])
        self.assertEqual(self.get("/api/calls?caller=_")["items"], [])

    def test_bad_queries_return_validation_errors(self):
        cases = ("page=0","page=-1","page=abc","page_size=0","page_size=101","page_size=1.5",
                 "page=1&page=2","status=unknown","date_from=2026-02-30","date_to=wrong",
                 "date_from=2026-10-30&date_to=2026-10-29","snapshot_id=-1","date_from=")
        for query in cases:
            if query == "date_from=":
                self.assertEqual(self.request("GET", "/api/calls?"+query)[0], 200)
                continue
            with self.subTest(query=query):
                status, data, _ = self.request("GET", "/api/calls?"+query)
                self.assertEqual(status, 400, data)
                self.assertEqual(data["code"], "invalid_call_query")

    def test_empty_and_out_of_range_pages_keep_complete_summary(self):
        empty = self.get("/api/calls?caller=does-not-exist")
        self.assertEqual(empty["items"], [])
        self.assertEqual(empty["pagination"]["total_pages"], 0)
        self.assertEqual(empty["summary"]["total_calls"], 0)
        distant = self.get("/api/calls?page=999")
        self.assertEqual(distant["items"], [])
        self.assertEqual(distant["summary"]["total_calls"], 123)

    def test_admin_selection_is_validated_and_customer_spoofing_is_ignored(self):
        self.assertEqual(self.request("GET", "/api/calls?tenant_id=wrong", tenant=1)[0], 400)
        self.assertEqual(self.get("/api/calls?tenant_id=3")["summary"]["total_calls"], 123)
        self.assertEqual(self.get("/api/calls?tenant_id=3", 1)["summary"]["total_calls"], 1)
        self.assertEqual(self.get("/api/calls", 1)["items"], [])


if __name__ == "__main__":
    unittest.main()

