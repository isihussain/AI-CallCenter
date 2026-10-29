"""Admin provider and flow checks; all provider requests are mocked."""
import io
import json
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from test_api import ApiTestCase, backend


class ProviderConsoleTests(ApiTestCase):
    def test_legacy_provider_migration_preserves_the_realtime_record(self):
        path=str(Path(self.directory.name)/'legacy.db')
        with closing(backend.sqlite3.connect(path)) as conn, conn:
            conn.execute("CREATE TABLE provider_settings(provider TEXT PRIMARY KEY,api_key TEXT NOT NULL,model TEXT NOT NULL,enabled INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
            conn.execute("INSERT INTO provider_settings VALUES('openai',?,'legacy-realtime',1,100)",(backend.protect('synthetic-legacy-key'),))
        with patch.object(backend,'DB_PATH',path),closing(backend.db()) as conn:
            row=conn.execute("SELECT * FROM provider_settings WHERE provider='openai'").fetchone()
            self.assertEqual(row['model'],'legacy-realtime')
            self.assertEqual(backend.reveal(row['api_key']),'synthetic-legacy-key')
            self.assertEqual(row['voice_id'],'')
            self.assertEqual(row['check_status'],'unchecked')

    def save(self, provider, **extra):
        data={'provider':provider,'api_key':'synthetic-private-key','model':'demo-model','enabled':True}
        data.update(extra)
        return self.request('POST','/api/admin/providers',data,tenant=1)

    def test_admin_only_and_no_keys_in_read_responses(self):
        for path in ('/api/admin/system-flow','/api/admin/providers'):
            self.assertEqual(self.request('GET',path,tenant=None)[0],401)
            self.assertEqual(self.request('GET',path,tenant=2)[0],403)
        for path in ('/api/admin/providers/test','/api/admin/providers/preview','/api/admin/ai-playground'):
            self.assertEqual(self.request('POST',path,{},tenant=2)[0],403)
        self.save('openai')
        self.save('openai_ai',model='text-demo')
        self.save('elevenlabs',voice_id='synthetic-voice')
        with patch.dict(backend.os.environ,{'OPENAI_API_KEY':''}):
            data=self.get('/api/admin/system-flow',tenant=1)
        self.assertTrue(data['realtime']['configured'])
        self.assertEqual(data['realtime']['model'],'demo-model')
        self.assertEqual(data['phone_voice'],'openai')
        self.assertFalse(data['elevenlabs_phone_bridge'])
        self.assertEqual(data['counts']['tenants'],2)
        self.assertNotIn('synthetic-private-key',json.dumps(data))
        self.assertNotIn('Original greeting',json.dumps(data))

    def test_independent_encrypted_keys_preservation_removal_and_validation(self):
        self.assertEqual(self.save('openai')[0],200)
        self.assertEqual(self.save('openai_ai',api_key='another-synthetic-key')[0],200)
        self.assertEqual(self.save('elevenlabs',voice_id='demo-voice')[0],200)
        self.assertEqual(self.save('openai_ai',api_key='',model='new-model')[0],200)
        with closing(backend.db()) as conn:
            rows={r['provider']:dict(r) for r in conn.execute('SELECT * FROM provider_settings')}
        self.assertNotEqual(rows['openai_ai']['api_key'],'another-synthetic-key')
        self.assertEqual(backend.reveal(rows['openai_ai']['api_key']),'another-synthetic-key')
        self.assertEqual(backend.reveal(rows['openai']['api_key']),'synthetic-private-key')
        self.assertEqual(rows['elevenlabs']['voice_id'],'demo-voice')
        self.assertEqual(self.save('elevenlabs',api_key='',clear_key=True)[0],200)
        saved=self.get('/api/admin/providers',tenant=1)
        self.assertFalse(next(p for p in saved['items'] if p['provider']=='elevenlabs')['configured'])
        for values in ({'provider':'unknown'},{'voice_id':'../../voice'},{'model':'https://host/redirect?x=1'},{'api_key':'bad\nheader'}):
            provider=values.get('provider','elevenlabs')
            self.assertEqual(self.save(provider,**{k:v for k,v in values.items() if k!='provider'})[0],400)

    def test_preview_uses_saved_credentials_and_returns_no_secret(self):
        self.save('elevenlabs',voice_id='demo-voice',model='eleven_flash_v2_5')
        with patch.object(backend.urllib.request,'urlopen',return_value=io.BytesIO(b'ID3-synthetic-audio')) as upstream:
            status,data,_=self.request('POST','/api/admin/providers/preview',{'provider':'elevenlabs','text':'Synthetic voice preview'},tenant=1)
        self.assertEqual(status,200)
        self.assertEqual(data['content_type'],'audio/mpeg')
        req=upstream.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.elevenlabs.io/v1/text-to-speech/demo-voice?output_format=mp3_44100_128')
        self.assertEqual(req.get_header('Xi-api-key'),'synthetic-private-key')
        self.assertEqual(json.loads(req.data)['model_id'],'eleven_flash_v2_5')
        self.assertNotIn('synthetic-private-key',json.dumps(data))
        self.assertEqual(self.request('POST','/api/admin/providers/preview',{'provider':'elevenlabs','text':'x'*501},tenant=1)[0],400)
        self.save('elevenlabs',enabled=False)
        self.assertEqual(self.request('POST','/api/admin/providers/preview',{'provider':'elevenlabs','text':'hello'},tenant=1)[0],400)

    def test_openai_text_preview_is_explicit_and_not_stored(self):
        self.save('openai_ai',model='text-demo')
        body=json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'Synthetic reply'}]}]}).encode()
        with patch.object(backend.urllib.request,'urlopen',return_value=io.BytesIO(body)) as upstream:
            status,data,_=self.request('POST','/api/admin/ai-playground',{'text':'Synthetic prompt'},tenant=1)
        self.assertEqual(status,200)
        self.assertEqual(data['text'],'Synthetic reply')
        req=upstream.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.openai.com/v1/responses')
        self.assertFalse(json.loads(req.data)['store'])
        self.assertEqual(json.loads(req.data)['model'],'text-demo')

    def test_failed_checks_redact_provider_errors_and_configuration_resets_status(self):
        self.save('openai')
        error=backend.urllib.error.HTTPError('https://provider.invalid',401,'synthetic-private-key',{},io.BytesIO(b'private response'))
        with patch.object(backend.urllib.request,'urlopen',side_effect=error):
            status,data,_=self.request('POST','/api/admin/providers/test',{'provider':'openai'},tenant=1)
        self.assertEqual(status,502)
        self.assertNotIn('synthetic-private-key',json.dumps(data))
        self.assertNotIn('private response',json.dumps(data))
        p=next(p for p in self.get('/api/admin/providers',tenant=1)['items'] if p['provider']=='openai')
        self.assertEqual(p['check_status'],'error')
        self.assertIsNotNone(p['checked_at'])
        self.save('openai',api_key='')
        p=next(p for p in self.get('/api/admin/providers',tenant=1)['items'] if p['provider']=='openai')
        self.assertEqual(p['check_status'],'unchecked')
        self.assertIsNone(p['checked_at'])
