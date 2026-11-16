"""Local checks for the Asterisk and ElevenLabs bridge; no provider audio is sent."""
import importlib.util
import io
import json
from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch
import uuid

from test_api import ApiTestCase, backend


bridge_path = Path(__file__).resolve().parents[1] / "elevenlabs_bridge.py"
bridge_spec = importlib.util.spec_from_file_location("oim_elevenlabs_bridge_test", bridge_path)
bridge = importlib.util.module_from_spec(bridge_spec)
bridge_spec.loader.exec_module(bridge)


class ElevenLabsBridgeTests(ApiTestCase):
    def test_scribe_uses_phone_pcm_and_only_the_requested_languages(self):
        query = parse_qs(urlparse(bridge.scribe_url()).query)
        self.assertEqual(query["model_id"], ["scribe_v3_live"])
        self.assertEqual(query["audio_format"], ["pcm_8000"])
        self.assertEqual(query["language_code"], ["en"])
        self.assertEqual(query["secondary_languages"], ["tr", "ru"])
        self.assertEqual(query["multilang_mode"], ["true"])
        self.assertEqual(query["commit_strategy"], ["vad"])

    def test_ulaw_silence_decodes_to_audiosocket_pcm(self):
        self.assertEqual(bridge.ulaw_to_pcm(b"\xff\x7f"), b"\x00\x00\x00\x00")

    def test_bridge_registration_resolves_did_and_audio_socket_claim_is_one_time(self):
        call_id = str(uuid.uuid4())
        with closing(backend.db()) as conn, conn:
            conn.execute(
                "INSERT INTO tenant_sip(tenant_id,username,did,domain,password,updated_at) VALUES(2,?,?,?,?,?)",
                ("studio-2", "+90 555 123 4567", "sip.example.test", backend.protect("synthetic"), backend.now()),
            )
        with patch.dict(backend.os.environ, {"OIM_AUDIOSOCKET_ENABLED": "1", "OIM_PBX_SHARED_SECRET": "synthetic-shared-secret"}), \
             patch.object(backend, "elevenlabs_bridge_config", return_value=("synthetic-el-key", "synthetic-voice", "eleven_flash_v2_5")), \
             patch.object(backend, "configured_openai_text", return_value=("synthetic-openai-key", "gpt-4.1-mini")):
            result = backend.register_bridge_call(call_id, "+90 (555) 123-4567", "+1 202 555 0100")
            self.assertEqual(result, {"call_id": call_id, "tenant_id": 2})
            self.assertEqual(backend.claim_bridge_call(call_id), {"tenant_id": 2})
            self.assertIsNone(backend.claim_bridge_call(call_id))
        with closing(backend.db()) as conn:
            call = conn.execute("SELECT tenant_id,caller,status FROM calls WHERE call_id=?", (call_id,)).fetchone()
            self.assertEqual(tuple(call), (2, "+1 202 555 0100", "active"))

    def test_openai_text_turn_preserves_the_existing_knowledge_tool(self):
        call_id = "bridge-test-call"
        with closing(backend.db()) as conn, conn:
            conn.execute("INSERT INTO calls(tenant_id,call_id,status,started_at) VALUES(2,?,'active',?)", (call_id, backend.now()))
        responses = [
            {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{"id": "tool-1", "type": "function", "function": {"name": "search_knowledge", "arguments": "{\"query\":\"opening hours\"}"}}]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "We are open from nine to five."}}]},
        ]
        def provider_response(*_args, **_kwargs):
            return io.BytesIO(json.dumps(responses.pop(0)).encode())
        history = []
        with patch.object(backend, "configured_openai_text", return_value=("synthetic-openai-key", "gpt-4.1-mini")), \
             patch.object(backend, "knowledge_context", return_value="Synthetic published business facts."), \
             patch.object(backend, "knowledge_search", return_value=["[EN] Hours: 09:00–17:00"]), \
             patch.object(backend, "log_knowledge_search"), \
             patch.object(backend.urllib.request, "urlopen", side_effect=provider_response):
            result = backend.openai_bridge_turn(call_id, 2, "What are your opening hours?", history)
        self.assertEqual(result, {"text": "We are open from nine to five.", "hangup": False})
        self.assertEqual(history[0]["role"], "system")
        self.assertEqual(history[2]["tool_calls"][0]["function"]["name"], "search_knowledge")
        self.assertEqual(history[3]["role"], "tool")
        self.assertEqual(history[-1]["content"], "We are open from nine to five.")


if __name__ == "__main__":
    import unittest

    unittest.main()
