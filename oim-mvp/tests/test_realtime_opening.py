import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import types
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location('oim_backend', Path(__file__).resolve().parents[1] / 'backend.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class OpeningResponseTests(unittest.TestCase):
    def response_for(self, name, greeting):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.executescript('CREATE TABLE tenants(id INTEGER,name TEXT); CREATE TABLE tenant_ai_settings(tenant_id INTEGER,greeting TEXT);')
        if name is not None:
            conn.execute('INSERT INTO tenants VALUES(2,?)', (name,))
        if greeting is not None:
            conn.execute('INSERT INTO tenant_ai_settings VALUES(2,?)', (greeting,))
        with patch.object(backend, 'db', return_value=conn):
            return backend.opening_response(2)

    def test_saved_first_message_preserves_language_and_text(self):
        greeting = 'Здравствуйте! Это школа Наталии. Чем могу помочь?'
        event = self.response_for('Example Business', greeting)
        self.assertEqual(event['type'], 'response.create')
        self.assertTrue(event['response']['instructions'].endswith('\n' + greeting))
        self.assertEqual(event['response']['output_modalities'], ['audio'])
        self.assertEqual(event['response']['tool_choice'], 'none')

    def test_blank_first_message_has_a_spoken_fallback(self):
        event = self.response_for('Example Business', '  ')
        self.assertTrue(event['response']['instructions'].endswith('Merhaba, Example Business. Size nasıl yardımcı olabilirim?'))

    def test_missing_settings_still_greet(self):
        event = self.response_for('Example Business', None)
        self.assertIn('Merhaba, Example Business.', event['response']['instructions'])

    def test_missing_tenant_uses_generic_greeting(self):
        event = self.response_for(None, None)
        self.assertTrue(event['response']['instructions'].endswith('Merhaba, size nasıl yardımcı olabilirim?'))


class SidebandOpeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_silent_call_requests_audio_before_any_server_or_caller_event(self):
        timeline = []
        events = iter([
            {'type': 'session.created', 'session': {'model': 'gpt-realtime'}},
            {'type': 'session.created', 'session': {'model': 'gpt-realtime'}},
            {'type': 'response.created', 'response': {'metadata': None}},
        ])

        class Socket:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def send(self, raw):
                timeline.append(('send', json.loads(raw)))

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    event = next(events)
                except StopIteration:
                    raise StopAsyncIteration
                timeline.append(('receive', event))
                return json.dumps(event)

        opening = {'type': 'response.create', 'response': {'output_modalities': ['audio']}}
        fake_websockets = types.SimpleNamespace(connect=Mock(return_value=Socket()), ConnectionClosed=type('ConnectionClosed', (Exception,), {}))
        with patch.dict(sys.modules, {'websockets': fake_websockets}), patch.object(backend, 'configured_openai', return_value=('test-key', 'gpt-realtime')), patch.object(backend, 'opening_response', return_value=opening), patch.object(backend, 'save_call_event'), patch('builtins.print'):
            await backend.realtime_sideband('test-call', 2)
        self.assertEqual(timeline[0], ('send', opening))
        self.assertEqual(sum(kind == 'send' for kind, _ in timeline), 1)


if __name__ == '__main__':
    unittest.main()
