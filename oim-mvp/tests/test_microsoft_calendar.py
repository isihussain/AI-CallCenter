"""Microsoft OAuth and Graph calendar tests use synthetic tenant data."""

import json
import http.client
import os
import urllib.parse
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from test_api import ApiTestCase, backend


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class MicrosoftCalendarTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.environment = patch.dict(os.environ, {
            "MICROSOFT_CLIENT_ID": "synthetic-client-id",
            "MICROSOFT_CLIENT_SECRET": "synthetic-client-secret",
            "MICROSOFT_TENANT_ID": "common",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def connect_token(self, tenant_id=2):
        with closing(backend.db()) as conn, conn:
            conn.execute(
                "INSERT INTO microsoft_tokens(tenant_id,access_token,refresh_token,expires_at,calendar_id,updated_at) VALUES(?,?,?,?,?,?)",
                (tenant_id, backend.protect("synthetic-access-token"), backend.protect("synthetic-refresh-token"), backend.now() + 3600, "primary", backend.now()),
            )

    def set_calendar_provider(self, provider="microsoft"):
        config = dict(backend.calendar_engine.DEFAULTS)
        config.update({"external_calendar_provider": provider, "min_notice_minutes": 0})
        with closing(backend.db()) as conn, conn:
            conn.execute(
                "INSERT INTO calendar_settings(tenant_id,config_json,updated_at) VALUES(2,?,?)",
                (json.dumps(backend.calendar_engine.validate_settings(config)), backend.now()),
            )

    def test_status_is_customer_scoped_and_never_returns_oauth_credentials(self):
        status, payload, _ = self.request("GET", "/api/microsoft/status", tenant=2)
        self.assertEqual(status, 200)
        self.assertTrue(payload["configured"])
        self.assertFalse(payload["connected"])
        self.assertNotIn("client_secret", json.dumps(payload))
        self.assertEqual(self.request("GET", "/api/microsoft/start", tenant=1)[0], 403)

    def test_oauth_state_is_one_time_and_tokens_are_encrypted(self):
        status, payload, _ = self.request("GET", "/api/microsoft/start", tenant=2)
        self.assertEqual(status, 200)
        auth = urllib.parse.urlparse(payload["url"])
        self.assertEqual(auth.hostname, "login.microsoftonline.com")
        params = urllib.parse.parse_qs(auth.query)
        self.assertEqual(params["scope"], ["offline_access Calendars.ReadWrite"])
        state = params["state"][0]
        self.assertNotIn("synthetic-client-secret", payload["url"])

        with patch.object(backend.urllib.request, "urlopen", return_value=FakeResponse({
            "access_token": "synthetic-access-token",
            "refresh_token": "synthetic-refresh-token",
            "expires_in": 3600,
        })):
            connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
            try:
                connection.request("GET", "/api/microsoft/callback?" + urllib.parse.urlencode({"code": "synthetic-code", "state": state}))
                response = connection.getresponse()
                headers = dict(response.getheaders())
                response.read()
            finally:
                connection.close()
        self.assertEqual(response.status, 302)
        self.assertTrue(headers["Location"].endswith("/#calendar"))
        with closing(backend.db()) as conn:
            row = conn.execute("SELECT access_token,refresh_token FROM microsoft_tokens WHERE tenant_id=2").fetchone()
            state_count = conn.execute("SELECT COUNT(*) FROM calendar_oauth_states").fetchone()[0]
        self.assertEqual(backend.reveal(row["access_token"]), "synthetic-access-token")
        self.assertNotEqual(row["access_token"], "synthetic-access-token")
        self.assertEqual(state_count, 0)

    def test_graph_availability_reservation_cancellation_and_reschedule(self):
        self.connect_token()
        self.set_calendar_provider()
        with closing(backend.db()) as conn:
            config = backend.calendar_engine.settings_for(conn, 2)
        start = datetime.now(timezone.utc) + timedelta(days=3)
        event = {
            "id": "busy-event",
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (start + timedelta(minutes=60)).isoformat()},
            "isCancelled": False,
        }
        with patch.object(backend, "microsoft_calendar_events", return_value=[event]):
            busy = backend.microsoft_calendar_check(2, start, 30, config)
        self.assertFalse(busy["available"])
        self.assertTrue(busy["connected"])

        booking_start = (start + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        with patch.object(backend, "microsoft_api", side_effect=[{"value": []}, {"id": "synthetic-event"}]) as api:
            reserved = backend.calendar_reserve(2, {
                "customer_name": "Synthetic Customer",
                "service": "Synthetic Consultation",
                "appointment_at": booking_start.isoformat(),
                "duration_minutes": 60,
                "idempotency_key": "synthetic-conversation",
            })
        self.assertTrue(reserved["ok"])
        self.assertEqual(reserved["event_id"], "synthetic-event")
        self.assertEqual(api.call_args_list[1].args[1], "POST")
        self.assertEqual(api.call_args_list[1].args[3]["transactionId"], "synthetic-conversation")

        with patch.object(backend, "microsoft_api", return_value={}) as api:
            cancelled = backend.calendar_modify(2, "synthetic-event", "cancel", {})
            moved = backend.calendar_modify(2, "synthetic-event", "reschedule", {
                "appointment_at": (booking_start + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
            })
        self.assertTrue(cancelled["ok"])
        self.assertTrue(moved["ok"])
        self.assertEqual([call.args[1] for call in api.call_args_list], ["DELETE", "PATCH"])

    def test_selected_disconnected_outlook_fails_closed(self):
        self.set_calendar_provider()
        result = backend.calendar_check(2, "2026-12-01T10:00:00+03:00", 60)
        self.assertFalse(result["ok"])
        self.assertFalse(result["available"])
