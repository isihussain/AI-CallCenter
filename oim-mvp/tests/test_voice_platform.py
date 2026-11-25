"""ElevenLabs workspace and calendar checks use synthetic data and mocked HTTP."""
import hashlib
import hmac
import io
import json
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from test_api import ApiTestCase, backend


calendar_engine = backend.calendar_engine
voice_platform = backend.voice_platform


class CalendarEngineTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.config = dict(calendar_engine.DEFAULTS)
        self.config.update({
            "timezone": "Europe/Istanbul",
            "min_notice_minutes": 0,
            "max_days_ahead": 180,
            "slot_interval_minutes": 30,
            "alternative_window_minutes": 60,
            "business_hours": {day: [["09:00", "17:00"]] for day in calendar_engine.DAY_KEYS},
            "holidays": [],
            "blocked_intervals": [],
            "staff": [],
        })
        self.day = self.future_weekday(2)
        self.next_day = self.future_weekday(3)
        with closing(backend.db()) as conn, conn:
            clean = calendar_engine.validate_settings(self.config)
            conn.execute("INSERT INTO calendar_settings(tenant_id,config_json,updated_at) VALUES(2,?,?)", (json.dumps(clean), backend.now()))

    @staticmethod
    def future_weekday(offset):
        value = datetime.now(ZoneInfo("Europe/Istanbul")).date() + timedelta(days=offset)
        while value.weekday() >= 5:
            value += timedelta(days=1)
        return value

    def start(self, day=None, hour=12, minute=0):
        return datetime.combine(day or self.day, datetime.min.time()).replace(hour=hour, minute=minute).isoformat()

    def book(self, conn, start, call_id="synthetic-call", **extra):
        callbacks = {key: extra.pop(key) for key in ("external_reserve", "external_check", "external_cancel") if key in extra}
        values = {
            "customer_name": "Synthetic Customer",
            "phone": "+1 202 555 0101",
            "service": "Synthetic consultation",
            "appointment_at": start,
            "idempotency_key": call_id,
        }
        values.update(extra)
        return calendar_engine.book(conn, 2, values, call_id, **callbacks)

    def test_requested_busy_slot_returns_one_hour_before_and_after(self):
        with closing(backend.db()) as conn:
            self.book(conn, self.start(), "busy-slot")
            result = calendar_engine.alternatives(conn, 2, self.start())
        starts = [datetime.fromisoformat(item["start"]).strftime("%H:%M") for item in result["alternatives"]]
        self.assertEqual(starts, ["11:00", "13:00"])

    def test_only_available_one_hour_alternative_is_returned(self):
        with closing(backend.db()) as conn:
            self.book(conn, self.start(), "busy-target")
            self.book(conn, self.start(hour=11), "busy-before")
            result = calendar_engine.alternatives(conn, 2, self.start())
        self.assertEqual([datetime.fromisoformat(item["start"]).strftime("%H:%M") for item in result["alternatives"]], ["13:00"])

    def test_when_nearby_pair_is_busy_the_nearest_same_day_slots_are_used(self):
        with closing(backend.db()) as conn:
            for hour, call_id in ((11, "busy-before"), (12, "busy-target"), (13, "busy-after")):
                self.book(conn, self.start(hour=hour), call_id, duration_minutes=30)
            result = calendar_engine.alternatives(conn, 2, self.start(), duration_minutes=30)
        starts = [datetime.fromisoformat(item["start"]).strftime("%H:%M") for item in result["alternatives"]]
        self.assertEqual(starts, ["11:30", "12:30"])

    def test_fully_booked_day_returns_next_open_day(self):
        hours = dict(self.config["business_hours"])
        hours["sat"] = []
        hours["sun"] = []
        config = dict(self.config, business_hours=hours)
        with closing(backend.db()) as conn:
            conn.execute("UPDATE calendar_settings SET config_json=? WHERE tenant_id=2", (json.dumps(calendar_engine.validate_settings(config)),))
            conn.commit()
            for hour in range(9, 17):
                self.book(conn, self.start(hour=hour), f"full-day-{hour}")
            result = calendar_engine.alternatives(conn, 2, self.start(hour=12))
        self.assertTrue(result["alternatives"])
        self.assertEqual(datetime.fromisoformat(result["alternatives"][0]["start"]).date(), self.next_day)

    def test_idempotent_booking_and_conflicts_never_claim_success(self):
        with closing(backend.db()) as conn:
            first = self.book(conn, self.start(), "same-conversation")
            retry = self.book(conn, self.start(), "same-conversation")
            collision = calendar_engine.availability(conn, 2, self.start())
            unavailable = self.book(conn, self.start(), "different-conversation")
            count = conn.execute("SELECT COUNT(*) FROM appointments WHERE tenant_id=2 AND status='confirmed' AND idempotency_key IS NOT NULL").fetchone()[0]
        self.assertTrue(first["success"])
        self.assertTrue(retry["duplicate"])
        self.assertFalse(unavailable["success"], f"availability={collision}; result={unavailable}")
        self.assertFalse(unavailable["available"])
        self.assertEqual(count, 1)

    def test_simultaneous_requests_for_same_slot_create_one_booking(self):
        barrier = threading.Barrier(2)
        results, failures = [], []

        def reserve(index):
            conn = sqlite3.connect(backend.DB_PATH, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                barrier.wait(timeout=5)
                results.append(self.book(conn, self.start(), f"parallel-{index}"))
            except Exception as error:
                failures.append(error)
            finally:
                conn.close()

        workers = [threading.Thread(target=reserve, args=(index,)) for index in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=12)
        with closing(backend.db()) as conn:
            count = conn.execute("SELECT COUNT(*) FROM appointments WHERE tenant_id=2 AND status='confirmed' AND idempotency_key IS NOT NULL").fetchone()[0]
        self.assertFalse(failures, failures)
        self.assertEqual(count, 1, f"Concurrent inserts were {results}")
        self.assertEqual(sorted(item["success"] for item in results), [False, True])

    def test_connected_calendar_failure_fails_closed_and_phone_matching_is_normalized(self):
        with closing(backend.db()) as conn:
            with self.assertRaisesRegex(ValueError, "Calendar unavailable"):
                calendar_engine.availability(conn, 2, self.start(), external_check=lambda *_args: {"ok": False, "message": "Calendar unavailable."})
            self.book(conn, self.start(), "phone-match")
            row = conn.execute("SELECT id FROM appointments WHERE idempotency_key='phone-match'").fetchone()
            found = calendar_engine.find_appointment(conn, 2, {"phone": "12025550101", "appointment_id": row["id"]})
        self.assertEqual(found["id"], row["id"])

    def test_natural_date_and_time_support_three_languages_and_ask_when_ambiguous(self):
        now = datetime(2026, 11, 24, 10, 0, tzinfo=ZoneInfo("Europe/Istanbul"))
        for phrase, expected in (("tomorrow at 3 pm", "2026-11-25T15:00:00+03:00"), ("yarın saat 15:00", "2026-11-25T15:00:00+03:00"), ("завтра в 15:00", "2026-11-25T15:00:00+03:00")):
            with self.subTest(phrase=phrase):
                self.assertEqual(calendar_engine.resolve_natural_datetime(phrase, "Europe/Istanbul", now)["resolved"], expected)
        for phrase, expected in (("cuma günü saat üçte", "2026-11-27T15:00:00+03:00"), ("в четверг в три часа", "2026-11-26T15:00:00+03:00"), ("one hour later", "2026-11-24T11:00:00+03:00"), ("bir saat sonra", "2026-11-24T11:00:00+03:00"), ("через час", "2026-11-24T11:00:00+03:00")):
            with self.subTest(phrase=phrase):
                self.assertEqual(calendar_engine.resolve_natural_datetime(phrase, "Europe/Istanbul", now)["resolved"], expected)
        self.assertTrue(calendar_engine.resolve_natural_datetime("yarın öğleden sonra", "Europe/Istanbul", now)["needs_clarification"])
        self.assertEqual(calendar_engine.resolve_natural_date("tomorrow", "Europe/Istanbul", now)["resolved"], "2026-11-25")

    def test_spoken_time_range_returns_every_matching_slot_instead_of_one_exact_time(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 24, 9, 0, tzinfo=tz or ZoneInfo("Europe/Istanbul"))

        with patch.object(calendar_engine, "datetime", FixedDateTime), closing(backend.db()) as conn:
            result = calendar_engine.available_slots(conn, 2, "tomorrow morning between 10 and 12", duration_minutes=60)
        self.assertEqual([datetime.fromisoformat(item["start"]).strftime("%H:%M") for item in result["slots"]], ["10:00", "10:30", "11:00"])

    def test_service_duration_capacity_and_staff_allow_list_are_enforced(self):
        config = dict(self.config)
        config["staff"] = [{"id": "staff-a", "active": True}, {"id": "staff-b", "active": True}]
        config["service_rules"] = [{"service": "Priority consult", "duration_minutes": 30, "min_duration_minutes": 30, "max_duration_minutes": 45, "capacity": 2, "staff_ids": ["staff-b"]}]
        with closing(backend.db()) as conn, conn:
            conn.execute("UPDATE calendar_settings SET config_json=? WHERE tenant_id=2", (json.dumps(calendar_engine.validate_settings(config)),))
        with closing(backend.db()) as conn:
            first = self.book(conn, self.start(hour=10), "capacity-one", service="Priority consult", duration_minutes=30)
            second = self.book(conn, self.start(hour=10), "capacity-two", service="priority CONSULT", duration_minutes=30)
            third = self.book(conn, self.start(hour=10), "capacity-three", service="Priority consult", duration_minutes=30)
            chosen = conn.execute("SELECT staff_id FROM appointments WHERE idempotency_key='capacity-one'").fetchone()["staff_id"]
            invalid_staff = calendar_engine.availability(conn, 2, self.start(hour=12), 30, "staff-a", service="Priority consult")
            with self.assertRaisesRegex(ValueError, "configured service or tenant range"):
                calendar_engine.availability(conn, 2, self.start(hour=13), 20, service="Priority consult")
        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertFalse(third["success"])
        self.assertEqual(chosen, "staff-b")
        self.assertFalse(invalid_staff["available"])
        self.assertEqual(invalid_staff["reason"], "staff_not_allowed")

    def test_department_rules_and_cancellation_notice_are_applied(self):
        config = dict(self.config)
        config["department_rules"] = [{"department": "consulting", "duration_minutes": 30, "min_duration_minutes": 30, "max_duration_minutes": 45, "business_hours": {day: [["13:00", "16:00"]] for day in calendar_engine.DAY_KEYS}}]
        config["cancellation_policy"] = {"minimum_notice_minutes": 525600}
        with closing(backend.db()) as conn, conn:
            conn.execute("UPDATE calendar_settings SET config_json=? WHERE tenant_id=2", (json.dumps(calendar_engine.validate_settings(config)),))
        with closing(backend.db()) as conn:
            booked = self.book(conn, self.start(hour=14), "department-rule", department="Consulting")
            self.assertTrue(booked["success"])
            self.assertEqual(booked["duration_minutes"], 30)
            with self.assertRaisesRegex(ValueError, "cancellation notice period"):
                calendar_engine.change_appointment(conn, 2, {"appointment_id": booked["appointment_id"], "phone": "+1 202 555 0101"}, "cancel")

    def test_weekly_recurring_booking_is_idempotent_and_records_each_occurrence(self):
        reserve_calls = []

        def reserve(values):
            event = {"ok": True, "provider": "google", "event_id": f"event-{len(reserve_calls) + 1}"}
            reserve_calls.append((values["appointment_at"], event["event_id"]))
            return event

        with closing(backend.db()) as conn:
            first = self.book(conn, self.start(hour=10), "weekly-series", recurrence={"frequency": "weekly", "interval": 1, "count": 3}, external_reserve=reserve)
            retry = self.book(conn, self.start(hour=10), "weekly-series", recurrence={"frequency": "weekly", "interval": 1, "count": 3}, external_reserve=reserve)
            rows = conn.execute("SELECT appointment_at,calendar_provider,calendar_event_id,recurrence_index FROM appointments WHERE recurrence_series_id=? ORDER BY recurrence_index", (first["series_id"],)).fetchall()
        self.assertTrue(first["success"])
        self.assertTrue(retry["duplicate"])
        self.assertEqual(len(reserve_calls), 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["calendar_provider"] for row in rows], ["google"] * 3)
        self.assertEqual([row["recurrence_index"] for row in rows], [1, 2, 3])

    def test_failed_recurring_reservation_removes_prior_external_events_and_rolls_back(self):
        reserved, cancelled = [], []

        def reserve(_values):
            if len(reserved) == 2:
                return {"ok": False, "message": "Calendar unavailable."}
            event = {"ok": True, "provider": "google", "event_id": f"event-{len(reserved) + 1}"}
            reserved.append(event["event_id"])
            return event

        def cancel(event_id, _action, _context):
            cancelled.append(event_id)
            return {"ok": True}

        with closing(backend.db()) as conn:
            with self.assertRaisesRegex(ValueError, "Calendar unavailable"):
                self.book(conn, self.start(hour=10), "failed-series", recurrence={"frequency": "weekly", "count": 3}, external_reserve=reserve, external_cancel=cancel)
            count = conn.execute("SELECT COUNT(*) FROM appointments WHERE idempotency_key='failed-series'").fetchone()[0]
        self.assertEqual(reserved, ["event-1", "event-2"])
        self.assertEqual(cancelled, ["event-2", "event-1"])
        self.assertEqual(count, 0)

    def test_cancel_uses_the_provider_saved_on_the_appointment(self):
        with closing(backend.db()) as conn:
            booked = self.book(conn, self.start(self.next_day, hour=10), "provider-persist", external_reserve=lambda _values: {"ok": True, "provider": "google", "event_id": "event-google"})
            event_calls = []
            cancelled = calendar_engine.change_appointment(conn, 2, {"appointment_id": booked["appointment_id"], "phone": "+1 202 555 0101"}, "cancel", external_modify=lambda event_id, action, appointment: event_calls.append((event_id, action, appointment["calendar_provider"])) or {"ok": True})
        self.assertTrue(cancelled["success"])
        self.assertEqual(event_calls, [("event-google", "cancel", "google")])

    def test_closed_tenant_holiday_has_no_available_slots(self):
        config = dict(self.config)
        config["holidays"] = [self.day.isoformat()]
        with closing(backend.db()) as conn, conn:
            conn.execute("UPDATE calendar_settings SET config_json=? WHERE tenant_id=2", (json.dumps(calendar_engine.validate_settings(config)),))
        with closing(backend.db()) as conn:
            result = calendar_engine.available_slots(conn, 2, self.day.isoformat())
        self.assertEqual(result["slots"], [])

    def test_staff_hours_and_holidays_are_applied_to_slot_search(self):
        config = dict(self.config)
        config["staff"] = [{"id": "staff-a", "active": True, "business_hours": {day: [["10:00", "12:00"]] for day in calendar_engine.DAY_KEYS}, "holidays": [self.day.isoformat()]}]
        with closing(backend.db()) as conn, conn:
            conn.execute("UPDATE calendar_settings SET config_json=? WHERE tenant_id=2", (json.dumps(calendar_engine.validate_settings(config)),))
        with closing(backend.db()) as conn:
            slots = calendar_engine.available_slots(conn, 2, self.day.isoformat(), staff_id="staff-a")
            unknown = calendar_engine.available_slots(conn, 2, self.next_day.isoformat(), staff_id="missing")
            open_staff_slots = calendar_engine.available_slots(conn, 2, self.next_day.isoformat(), staff_id="staff-a")
        self.assertEqual(slots["slots"], [])
        self.assertEqual(unknown["slots"], [])
        self.assertEqual([datetime.fromisoformat(item["start"]).strftime("%H:%M") for item in open_staff_slots["slots"]], ["10:00", "10:30", "11:00"])


class VoicePlatformApiTests(ApiTestCase):
    def test_calendar_day_week_month_views_are_admin_scoped_and_validate_filters(self):
        route = "/api/admin/voice-platform/calendar/appointments?tenant_id=2&date=2026-10-29&view=day"
        self.assertEqual(self.request("GET", route, tenant=2)[0], 403)
        status, data, _ = self.request("GET", route, tenant=1)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["timezone"], "Europe/Istanbul")
        self.assertEqual([item["customer_name"] for item in data["items"]], ["Demo Contact 2"])
        week = self.get("/api/admin/voice-platform/calendar/appointments?tenant_id=2&date=2026-10-29&view=week", tenant=1)
        self.assertEqual(week["start_date"], "2026-10-26")
        self.assertEqual(week["end_date"], "2026-11-02")
        month = self.get("/api/admin/voice-platform/calendar/appointments?tenant_id=2&date=2026-10-29&view=month", tenant=1)
        self.assertEqual(month["start_date"], "2026-10-01")
        self.assertEqual(month["end_date"], "2026-11-01")
        self.assertEqual(self.request("GET", route.replace("view=day", "view=year"), tenant=1)[0], 400)

    def save_key(self):
        status, data, _ = self.request("POST", "/api/admin/providers", {"provider": "elevenlabs", "api_key": "synthetic-elevenlabs-key", "model": "eleven_flash_v2_5", "voice_id": "synthetic-voice", "enabled": True}, tenant=1)
        self.assertEqual(status, 200, data)

    def test_connection_test_checks_phone_capabilities_without_user_read(self):
        self.save_key()
        with patch.object(voice_platform, "check_phone_capabilities", return_value={"scribe": True, "speech": True}) as check:
            status, data, _ = self.request("POST", "/api/admin/voice-platform/connection-test", {}, tenant=1)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["capabilities"], {"scribe": True, "speech": True})
        check.assert_called_once_with("synthetic-elevenlabs-key", "synthetic-voice", "eleven_flash_v2_5")

    def test_signed_url_is_admin_only_uses_server_key_and_never_returns_it(self):
        route = "/api/admin/voice-platform/conversation-signed-url?agent_id=agent_synthetic_123"
        self.assertEqual(self.request("GET", route, tenant=2)[0], 403)
        self.assertEqual(self.request("GET", route, tenant=1)[0], 503)
        self.save_key()
        signed = "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=agent_synthetic_123&token=synthetic-temporary-token"
        response = io.BytesIO(json.dumps({"signed_url": signed}).encode())
        with patch.object(backend.urllib.request, "urlopen", return_value=response) as upstream:
            status, data, _ = self.request("GET", route, tenant=1)
        self.assertEqual(status, 200, data)
        self.assertEqual(data["signed_url"], signed)
        self.assertNotIn("synthetic-elevenlabs-key", json.dumps(data))
        request = upstream.call_args.args[0]
        self.assertIn("/v1/convai/conversation/get-signed-url?agent_id=agent_synthetic_123", request.full_url)
        self.assertEqual(request.get_header("Xi-api-key"), "synthetic-elevenlabs-key")

    def test_live_signed_url_has_a_per_admin_rate_limit(self):
        self.save_key()
        signed = "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=agent_synthetic_123&token=temporary"
        with patch.object(backend.urllib.request, "urlopen", side_effect=lambda *_args, **_kwargs: io.BytesIO(json.dumps({"signed_url": signed}).encode())):
            for _ in range(10):
                self.assertEqual(self.request("GET", "/api/admin/voice-platform/conversation-signed-url?agent_id=agent_synthetic_123", tenant=1)[0], 200)
            status, data, _ = self.request("GET", "/api/admin/voice-platform/conversation-signed-url?agent_id=agent_synthetic_123", tenant=1)
        self.assertEqual(status, 429)
        self.assertNotIn("synthetic-elevenlabs-key", json.dumps(data))

    def test_signed_post_call_event_is_deduplicated_and_stored_for_assigned_tenant(self):
        with closing(backend.db()) as conn, conn:
            conn.execute("INSERT INTO voice_platform_items(kind,item_id,name,tenant_id,remote_hash,remote_config,local_config,updated_at) VALUES('agent','agent_synthetic','Demo',2,'','','',?)", (backend.now(),))
        timestamp = str(int(time.time()))
        event = {"type": "post_call_transcription", "event_timestamp": timestamp, "data": {"conversation_id": "conv_synthetic", "agent_id": "agent_synthetic", "status": "done", "transcript": [{"role": "user", "message": "Synthetic transcript"}], "analysis": {"transcript_summary": "Synthetic summary"}, "metadata": {"start_time_unix_secs": int(timestamp), "call_duration_secs": 12}}}
        raw = json.dumps(event).encode()
        signature = hmac.new(b"synthetic-webhook-secret", timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
        header = f"t={timestamp},v0={signature}"
        with closing(backend.db()) as conn:
            first = voice_platform.process_post_call_webhook(raw, header, "synthetic-webhook-secret", conn, backend.protect)
            duplicate = voice_platform.process_post_call_webhook(raw, header, "synthetic-webhook-secret", conn, backend.protect)
            row = conn.execute("SELECT tenant_id,summary,transcript_encrypted FROM elevenlabs_conversations WHERE conversation_id='conv_synthetic'").fetchone()
        self.assertEqual(first[0], 200)
        self.assertTrue(first[1]["imported"])
        self.assertTrue(duplicate[1]["duplicate"])
        self.assertEqual(row["tenant_id"], 2)
        self.assertNotIn("Synthetic summary", row["summary"])
        self.assertNotIn("Synthetic transcript", row["transcript_encrypted"])


if __name__ == "__main__":
    import unittest

    unittest.main()
