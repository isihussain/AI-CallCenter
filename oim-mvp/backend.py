#!/usr/bin/env python3
import asyncio, base64, hashlib, hmac, json, math, os, re, secrets, sqlite3, subprocess, threading, time
import urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DB_PATH = os.environ.get('OIM_DB', '/var/lib/oim/oim.db')
HOST = os.environ.get('OIM_HOST', '127.0.0.1')
PORT = int(os.environ.get('OIM_PORT', '8787'))
SESSION_TTL = 60 * 60 * 12
SESSIONS = {}
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()
SECRET_PATH = os.environ.get('OIM_SECRET', '/var/lib/oim/.secret')
PUBLIC_URL = os.environ.get('OIM_PUBLIC_URL', 'http://localhost:8080').rstrip('/')

def cipher():
    from cryptography.fernet import Fernet
    os.makedirs(os.path.dirname(SECRET_PATH), exist_ok=True)
    if not os.path.exists(SECRET_PATH):
        with open(SECRET_PATH, 'wb') as f: f.write(Fernet.generate_key())
        os.chmod(SECRET_PATH, 0o600)
    with open(SECRET_PATH, 'rb') as f: return Fernet(f.read().strip())

def protect(value): return cipher().encrypt(value.encode()).decode() if value else ''
def reveal(value):
    try: return cipher().decrypt(value.encode()).decode() if value else ''
    except Exception: return ''

def now(): return int(time.time())

REALTIME_PRICES_USD_PER_MILLION = {
    'gpt-realtime': {'audio_input':32.0,'audio_output':64.0,'text_input':4.0,'text_output':16.0,'cached_input':0.40},
    'gpt-realtime-1.5': {'audio_input':32.0,'audio_output':64.0,'text_input':4.0,'text_output':16.0,'cached_input':0.40},
    'gpt-realtime-2': {'audio_input':32.0,'audio_output':64.0,'text_input':4.0,'text_output':24.0,'cached_input':0.40},
    'gpt-realtime-2.1': {'audio_input':32.0,'audio_output':64.0,'text_input':4.0,'text_output':24.0,'cached_input':0.40},
    'gpt-realtime-2.1-mini': {'audio_input':10.0,'audio_output':20.0,'text_input':0.60,'text_output':2.40,'cached_input':0.30},
}

def usage_number(value):
    try: return max(0,int(value or 0))
    except (TypeError,ValueError): return 0

def usage_details(usage):
    """Flatten Realtime response.done usage without assuming one event shape."""
    usage=usage or {}
    inp=usage.get('input_token_details') or usage.get('input_tokens_details') or {}
    out=usage.get('output_token_details') or usage.get('output_tokens_details') or {}
    return {
        'input_tokens':usage_number(usage.get('input_tokens')),
        'output_tokens':usage_number(usage.get('output_tokens')),
        'total_tokens':usage_number(usage.get('total_tokens')),
        'input_text_tokens':usage_number(inp.get('text_tokens')),
        'input_audio_tokens':usage_number(inp.get('audio_tokens')),
        'input_cached_tokens':usage_number(inp.get('cached_tokens') or inp.get('cached_input_tokens')),
        'output_text_tokens':usage_number(out.get('text_tokens')),
        'output_audio_tokens':usage_number(out.get('audio_tokens')),
    }

def usage_cost_usd(model, details):
    prices=REALTIME_PRICES_USD_PER_MILLION.get(model or 'gpt-realtime')
    if not prices: return None
    cached_text=min(details['input_cached_tokens'],details['input_text_tokens'])
    cached_audio=max(0,details['input_cached_tokens']-cached_text)
    uncached_text=max(0,details['input_text_tokens']-cached_text)
    uncached_audio=max(0,details['input_audio_tokens']-cached_audio)
    return round((uncached_audio*prices['audio_input'] + details['output_audio_tokens']*prices['audio_output'] + uncached_text*prices['text_input'] + details['output_text_tokens']*prices['text_output'] + details['input_cached_tokens']*prices['cached_input']) / 1_000_000, 8)

def save_usage(call_id, model, usage):
    details=usage_details(usage); cost=usage_cost_usd(model,details)
    conn=db()
    conn.execute('''INSERT INTO call_usage(call_id,model,input_tokens,output_tokens,total_tokens,input_text_tokens,input_audio_tokens,input_cached_tokens,output_text_tokens,output_audio_tokens,estimated_openai_usd,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(call_id) DO UPDATE SET model=excluded.model,input_tokens=excluded.input_tokens,output_tokens=excluded.output_tokens,total_tokens=excluded.total_tokens,input_text_tokens=excluded.input_text_tokens,input_audio_tokens=excluded.input_audio_tokens,input_cached_tokens=excluded.input_cached_tokens,output_text_tokens=excluded.output_text_tokens,output_audio_tokens=excluded.output_audio_tokens,estimated_openai_usd=excluded.estimated_openai_usd,updated_at=excluded.updated_at''',
      (call_id,model or 'gpt-realtime',details['input_tokens'],details['output_tokens'],details['total_tokens'],details['input_text_tokens'],details['input_audio_tokens'],details['input_cached_tokens'],details['output_text_tokens'],details['output_audio_tokens'],cost,now()))
    conn.commit(); conn.close()

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 180000)
    return salt.hex() + '$' + digest.hex()

def check_password(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 180000).hex()
        return hmac.compare_digest(actual, digest)
    except Exception: return False

def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript('''
      CREATE TABLE IF NOT EXISTS tenants(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer', credits REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'active', created_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, amount REAL NOT NULL, kind TEXT NOT NULL, reason TEXT NOT NULL, meta TEXT, created_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS provider_settings(provider TEXT PRIMARY KEY, api_key TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS billing_settings(id INTEGER PRIMARY KEY CHECK(id=1), credits_per_minute REAL NOT NULL DEFAULT 0.1, ai_multiplier REAL NOT NULL DEFAULT 1, server_hourly_rate REAL NOT NULL DEFAULT 0, minimum_credit REAL NOT NULL DEFAULT 10, updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS tenant_sip(tenant_id INTEGER PRIMARY KEY, username TEXT NOT NULL DEFAULT '', did TEXT NOT NULL DEFAULT '', domain TEXT NOT NULL DEFAULT '', password TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, call_id TEXT UNIQUE NOT NULL, caller TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'incoming', transcript TEXT NOT NULL DEFAULT '', started_at INTEGER NOT NULL, ended_at INTEGER, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE INDEX IF NOT EXISTS calls_tenant_started_id ON calls(tenant_id,started_at DESC,id DESC);
      CREATE TABLE IF NOT EXISTS call_usage(call_id TEXT PRIMARY KEY, model TEXT NOT NULL DEFAULT '', input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0, total_tokens INTEGER NOT NULL DEFAULT 0, input_text_tokens INTEGER NOT NULL DEFAULT 0, input_audio_tokens INTEGER NOT NULL DEFAULT 0, input_cached_tokens INTEGER NOT NULL DEFAULT 0, output_text_tokens INTEGER NOT NULL DEFAULT 0, output_audio_tokens INTEGER NOT NULL DEFAULT 0, estimated_openai_usd REAL, updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS appointments(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, call_id TEXT, customer_name TEXT NOT NULL, phone TEXT NOT NULL, service TEXT NOT NULL, appointment_at TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'confirmed', created_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS telegram_settings(tenant_id INTEGER PRIMARY KEY, bot_token TEXT NOT NULL DEFAULT '', chat_id TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS telegram_deliveries(path TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '', sent_at INTEGER);
      CREATE TABLE IF NOT EXISTS google_tokens(tenant_id INTEGER PRIMARY KEY, access_token TEXT NOT NULL DEFAULT '', refresh_token TEXT NOT NULL DEFAULT '', expires_at INTEGER NOT NULL DEFAULT 0, calendar_id TEXT NOT NULL DEFAULT 'primary', updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS knowledge_documents(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, language TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'published', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS tenant_ai_settings(tenant_id INTEGER PRIMARY KEY, greeting TEXT NOT NULL DEFAULT '', voice TEXT NOT NULL DEFAULT 'alloy', working_hours TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS knowledge_search_events(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, call_id TEXT NOT NULL, query TEXT NOT NULL, result_count INTEGER NOT NULL DEFAULT 0, results TEXT NOT NULL DEFAULT '[]', created_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS system_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS call_reviews(call_id TEXT PRIMARY KEY, tenant_id INTEGER NOT NULL, outcome TEXT NOT NULL DEFAULT 'unresolved', summary TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE TABLE IF NOT EXISTS callback_requests(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, call_id TEXT NOT NULL UNIQUE, phone TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', created_at INTEGER NOT NULL, completed_at INTEGER, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
      CREATE INDEX IF NOT EXISTS callback_tenant_status_created ON callback_requests(tenant_id,status,created_at DESC);
      CREATE TABLE IF NOT EXISTS tenant_retention(tenant_id INTEGER PRIMARY KEY, transcript_retention_days INTEGER, updated_at INTEGER NOT NULL, last_purged_at INTEGER, FOREIGN KEY(tenant_id) REFERENCES tenants(id));
    ''')
    columns={row['name'] for row in conn.execute('PRAGMA table_info(calls)').fetchall()}
    provider_columns={row['name'] for row in conn.execute('PRAGMA table_info(provider_settings)').fetchall()}
    for name,definition in [('voice_id',"TEXT NOT NULL DEFAULT ''"),('check_status',"TEXT NOT NULL DEFAULT 'unchecked'"),('checked_at','INTEGER')]:
        if name not in provider_columns: conn.execute(f'ALTER TABLE provider_settings ADD COLUMN {name} {definition}')
    if 'billed_credits' not in columns: conn.execute('ALTER TABLE calls ADD COLUMN billed_credits REAL NOT NULL DEFAULT 0')
    if 'billed_at' not in columns: conn.execute('ALTER TABLE calls ADD COLUMN billed_at INTEGER')
    if 'failure_code' not in columns: conn.execute("ALTER TABLE calls ADD COLUMN failure_code TEXT NOT NULL DEFAULT ''")
    if 'failure_message' not in columns: conn.execute("ALTER TABLE calls ADD COLUMN failure_message TEXT NOT NULL DEFAULT ''")
    billing_columns={row['name'] for row in conn.execute('PRAGMA table_info(billing_settings)').fetchall()}
    if 'minimum_credit' not in billing_columns: conn.execute('ALTER TABLE billing_settings ADD COLUMN minimum_credit REAL NOT NULL DEFAULT 10')
    sip_columns={row['name'] for row in conn.execute('PRAGMA table_info(tenant_sip)').fetchall()}
    if 'did' not in sip_columns: conn.execute("ALTER TABLE tenant_sip ADD COLUMN did TEXT NOT NULL DEFAULT ''")
    tenant_columns={row['name'] for row in conn.execute('PRAGMA table_info(tenants)').fetchall()}
    if 'agreement_accepted' not in tenant_columns: conn.execute("ALTER TABLE tenants ADD COLUMN agreement_accepted INTEGER NOT NULL DEFAULT 0")
    if 'agreement_accepted_at' not in tenant_columns: conn.execute("ALTER TABLE tenants ADD COLUMN agreement_accepted_at INTEGER")
    if 'agreement_version' not in tenant_columns: conn.execute("ALTER TABLE tenants ADD COLUMN agreement_version TEXT NOT NULL DEFAULT ''")
    conn.execute('''CREATE TABLE IF NOT EXISTS crm_contacts(id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id))''')
    conn.execute('INSERT OR IGNORE INTO billing_settings(id,credits_per_minute,ai_multiplier,server_hourly_rate,minimum_credit,updated_at) VALUES(1,?,?,?,?,?)',(float(os.environ.get('OIM_CREDITS_PER_MINUTE','0.1')),1,0,10,now()))
    conn.commit()
    return conn

def bootstrap():
    conn = db(); row = conn.execute('SELECT COUNT(*) c FROM tenants').fetchone()
    if row['c'] == 0:
        admin_username = os.environ.get('OIM_BOOTSTRAP_ADMIN_USERNAME', 'admin').strip() or 'admin'
        configured_password = os.environ.get('OIM_BOOTSTRAP_ADMIN_PASSWORD', '')
        admin_pw = configured_password or secrets.token_urlsafe(24)
        conn.execute('INSERT INTO tenants(name,email,username,password_hash,role,credits,created_at) VALUES(?,?,?,?,?,?,?)', ('AI Call Center Administrator','',admin_username,hash_password(admin_pw),'admin',0,now()))
        conn.commit()
        if not configured_password:
            path = os.path.join(os.path.dirname(DB_PATH), 'bootstrap-credentials.txt')
            with open(path,'w',encoding='utf-8') as f:
                f.write('AI Call Center first-run administrator credentials\n'+admin_username+' / '+admin_pw+'\n')
            os.chmod(path, 0o600)
    conn.close()

def public_tenant(row):
    return {'id':row['id'],'name':row['name'],'email':row['email'],'username':row['username'],'role':row['role'],'credits':round(row['credits'],2),'status':row['status']}

def public_provider(row):
    key = reveal(row['api_key'])
    return {'provider':row['provider'],'model':row['model'],'enabled':bool(row['enabled']),'configured':bool(key),'masked':'••••••••' if key else '', 'voice_id':row['voice_id'],'check_status':row['check_status'],'checked_at':row['checked_at']}

PROVIDER_IDS = {'openai','openai_ai','elevenlabs','deepgram'}
PROVIDER_LIMITS = {}
PROVIDER_LOCK = threading.Lock()

def provider_request(provider, key, model='', payload=None, voice_id=''):
    if provider == 'elevenlabs':
        url='https://api.elevenlabs.io/v1/text-to-speech/'+urllib.parse.quote(voice_id,safe='')+'?output_format=mp3_44100_128' if payload else 'https://api.elevenlabs.io/v1/user'
        headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg' if payload else 'application/json'}
    else:
        url=('https://api.deepgram.com/v1/projects' if provider=='deepgram' else 'https://api.openai.com/v1/responses' if payload else 'https://api.openai.com/v1/models/'+urllib.parse.quote(model,safe=''))
        headers={'Authorization':('Token ' if provider=='deepgram' else 'Bearer ')+key,'Content-Type':'application/json'}
    req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload else None,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=25) as response: body=response.read(3*1024*1024+1)
        if len(body)>3*1024*1024: raise ValueError('Sağlayıcı yanıtı çok büyük.')
        return body
    except urllib.error.HTTPError as error:
        code=error.code
        error.close()
        messages={401:'API anahtarı geçersiz.',403:'Bu anahtarın işlem izni yok.',404:'Model veya ses kimliği bulunamadı.',429:'Sağlayıcı kotası veya istek sınırı aşıldı.'}
        raise ValueError(messages.get(code,'Sağlayıcı isteği tamamlayamadı.')) from None
    except (OSError,TimeoutError): raise ValueError('Sağlayıcıya bağlanılamadı. Yeniden deneyin.') from None

def admin_system_flow(conn):
    key,model=configured_openai()
    providers={r['provider']:public_provider(r) for r in conn.execute('SELECT * FROM provider_settings')}
    counts={
        'tenants':conn.execute('SELECT COUNT(*) FROM tenants WHERE role="customer"').fetchone()[0],
        'active':conn.execute('SELECT COUNT(*) FROM calls WHERE status IN ("incoming","active")').fetchone()[0],
        'today':conn.execute('SELECT COUNT(*) FROM calls WHERE started_at>=?',(now()-now()%86400,)).fetchone()[0],
        'failed':conn.execute('SELECT COUNT(*) FROM calls WHERE status="failed" AND started_at>=?',(now()-86400,)).fetchone()[0],
        'knowledge':conn.execute('SELECT COUNT(*) FROM knowledge_documents WHERE status="published"').fetchone()[0],
        'callbacks':conn.execute('SELECT COUNT(*) FROM callback_requests WHERE status="pending"').fetchone()[0],
        'appointments':conn.execute('SELECT COUNT(*) FROM appointments').fetchone()[0],
    }
    return {'updated_at':now(),'counts':counts,'realtime':{'configured':bool(key),'model':model,'source':'saved' if providers.get('openai',{}).get('enabled') and providers.get('openai',{}).get('configured') else 'environment' if key else 'missing'},'providers':list(providers.values()),'phone_voice':'openai','elevenlabs_phone_bridge':False}

def finalize_call(call_id):
    conn=db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM calls WHERE call_id=?',(call_id,)).fetchone()
        if not row or row['billed_at']:
            conn.commit(); return
        ended=now(); seconds=max(1,ended-int(row['started_at'])); minutes=max(1,math.ceil(seconds/60))
        pricing=conn.execute('SELECT credits_per_minute,ai_multiplier,server_hourly_rate FROM billing_settings WHERE id=1').fetchone()
        rate=max(0,float(pricing['credits_per_minute'] if pricing else os.environ.get('OIM_CREDITS_PER_MINUTE','1')))
        multiplier=max(0,float(pricing['ai_multiplier'] if pricing else 1))
        server_rate=max(0,float(pricing['server_hourly_rate'] if pricing else 0))
        requested=round(minutes*rate*multiplier + (seconds/3600.0)*server_rate,2)
        tenant=conn.execute('SELECT credits FROM tenants WHERE id=?',(row['tenant_id'],)).fetchone()
        charged=round(min(float(tenant['credits'] if tenant else 0),requested),2)
        if charged:
            usage=conn.execute('SELECT model,input_tokens,output_tokens,total_tokens,input_audio_tokens,output_audio_tokens,estimated_openai_usd FROM call_usage WHERE call_id=?',(call_id,)).fetchone()
            meta=json.dumps({'call_id':call_id,'seconds':seconds,'billable_minutes':minutes,'rate':rate,'ai_multiplier':multiplier,'server_hourly_rate':server_rate,'usage':dict(usage) if usage else None},ensure_ascii=False)
            conn.execute('UPDATE tenants SET credits=credits-? WHERE id=?',(charged,row['tenant_id']))
            conn.execute('INSERT INTO ledger(tenant_id,amount,kind,reason,meta,created_at) VALUES(?,?,?,?,?,?)',(row['tenant_id'],-charged,'debit',f'AI çağrı kullanımı ({minutes} dk)',meta,ended))
        final_status='failed' if row['status']=='failed' else 'ended'
        conn.execute('UPDATE calls SET status=?,ended_at=COALESCE(ended_at,?),billed_credits=?,billed_at=? WHERE call_id=?',(final_status,ended,charged,ended,call_id))
        conn.commit()
    finally:
        conn.close()

def save_call_event(call_id, status, transcript=''):
    if status == 'ended': return finalize_call(call_id)
    conn=db()
    conn.execute('UPDATE calls SET status=CASE WHEN status="failed" THEN status ELSE ? END, transcript=CASE WHEN ?="" THEN transcript ELSE transcript || ? END WHERE call_id=?', (status,transcript,transcript,call_id))
    conn.commit(); conn.close()

CALL_FAILURE_MESSAGES = {
    'provider_error': 'AI sağlayıcısı çağrıyı tamamlayamadı. Sağlayıcı ayarlarını ve çağrı kayıtlarını kontrol edin.',
    'accept_failed': 'Çağrı AI sağlayıcısına bağlanamadı. Sağlayıcı anahtarını ve SIP yönlendirmesini kontrol edin.',
    'sideband_failed': 'Çağrı bağlantısı beklenmedik biçimde kesildi. Sağlayıcı ve sunucu bağlantısını kontrol edin.',
}

def record_call_failure(call_id, code, bill=True):
    code=code if code in CALL_FAILURE_MESSAGES else 'sideband_failed'
    conn=db()
    conn.execute('UPDATE calls SET status="failed",failure_code=?,failure_message=?,ended_at=COALESCE(ended_at,?) WHERE call_id=?',(code,CALL_FAILURE_MESSAGES[code],now(),call_id))
    conn.commit(); conn.close()
    if bill: finalize_call(call_id)

def configured_openai():
    conn=db(); row=conn.execute('SELECT * FROM provider_settings WHERE provider="openai" AND enabled=1').fetchone(); conn.close()
    key=reveal(row['api_key']) if row else ''
    return key or os.environ.get('OPENAI_API_KEY',''), ((row['model'] or '').strip() if row else '') or 'gpt-realtime'

def telegram_config(tenant_id):
    conn=db(); row=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=?',(tenant_id,)).fetchone(); conn.close()
    if not row: return {'token':'','chat_id':'','enabled':False}
    return {'token':reveal(row['bot_token']),'chat_id':row['chat_id'],'enabled':bool(row['enabled'])}

def telegram_request(method, tenant_id, fields=None, file_path=None):
    cfg=telegram_config(tenant_id); token=cfg['token']
    if not token: raise ValueError('Telegram bot tokeni tanımlı değil')
    url=f'https://api.telegram.org/bot{token}/{method}'; fields={k:str(v) for k,v in (fields or {}).items()}
    if file_path:
        boundary='----oim'+secrets.token_hex(12); chunks=[]
        for key,value in fields.items(): chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()])
        name=os.path.basename(file_path); chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{name}"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
        with open(file_path,'rb') as handle: chunks.append(handle.read())
        chunks.append(f'\r\n--{boundary}--\r\n'.encode()); body=b''.join(chunks); headers={'Content-Type':f'multipart/form-data; boundary={boundary}'}
    else:
        body=urllib.parse.urlencode(fields).encode(); headers={'Content-Type':'application/x-www-form-urlencoded'}
    req=urllib.request.Request(url,data=body,headers=headers,method='POST')
    with urllib.request.urlopen(req,timeout=30) as response: result=json.loads(response.read())
    if not result.get('ok'): raise RuntimeError(result.get('description','Telegram API hatası'))
    return result

def recording_watcher():
    root=os.environ.get('OIM_RECORDINGS','/var/spool/asterisk/monitor/oim')
    while True:
        try:
            if os.path.isdir(root):
                for name in sorted(os.listdir(root)):
                    if not name.lower().endswith('.wav'): continue
                    path=os.path.join(root,name)
                    if now()-int(os.path.getmtime(path)) < 5: continue
                    match=re.match(r'^t(\d+)-',name)
                    tenant_id=int(match.group(1)) if match else 2
                    cfg=telegram_config(tenant_id)
                    if not (cfg['enabled'] and cfg['token'] and cfg['chat_id']): continue
                    conn=db(); row=conn.execute('SELECT * FROM telegram_deliveries WHERE path=?',(path,)).fetchone(); conn.close()
                    if row and (row['status']=='sent' or row['attempts']>=5): continue
                    caller=(name.rsplit('-',2)[-2] if name.count('-')>=2 else 'Bilinmiyor') or 'Bilinmiyor'
                    try:
                        telegram_request('sendDocument',tenant_id,{'chat_id':cfg['chat_id'],'caption':f'OIM çağrı kaydı\nArayan: {caller}\nDosya: {name}'},path)
                        conn=db(); conn.execute('INSERT INTO telegram_deliveries(path,status,attempts,sent_at) VALUES(?,?,1,?) ON CONFLICT(path) DO UPDATE SET status="sent",attempts=attempts+1,error="",sent_at=excluded.sent_at',(path,'sent',now())); conn.commit(); conn.close()
                    except Exception as exc:
                        conn=db(); conn.execute('INSERT INTO telegram_deliveries(path,status,attempts,error) VALUES(?,?,1,?) ON CONFLICT(path) DO UPDATE SET status="failed",attempts=attempts+1,error=excluded.error',(path,'failed',str(exc)[:500])); conn.commit(); conn.close()
        except Exception as exc: print('Recording watcher error',repr(exc),flush=True)
        time.sleep(5)

def opening_response(tenant_id):
    conn=db()
    try:
        row=conn.execute('SELECT t.name,a.greeting FROM tenants t LEFT JOIN tenant_ai_settings a ON a.tenant_id=t.id WHERE t.id=?',(tenant_id,)).fetchone()
    finally:
        conn.close()
    greeting=(row['greeting'] or '').strip() if row else ''
    if not greeting:
        name=(row['name'] or '').strip() if row else ''
        greeting=f'Merhaba, {name}. Size nasıl yardımcı olabilirim?' if name else 'Merhaba, size nasıl yardımcı olabilirim?'
    return {'type':'response.create','response':{
        'output_modalities':['audio'],
        'tool_choice':'none',
        'metadata':{'purpose':'opening_greeting'},
        'instructions':'Start speaking now, even if the caller has not spoken. Say only the following greeting exactly as written, in its original language. Do not add information or call tools. Then wait for the caller.\n'+greeting,
    }}

async def realtime_sideband(call_id, tenant_id):
    import websockets
    key,_=configured_openai(); headers={'Authorization':'Bearer '+key,'OpenAI-Beta':'realtime=v1'}
    uri='wss://api.openai.com/v1/realtime?call_id='+call_id
    try:
        async with websockets.connect(uri,extra_headers=headers,ping_interval=20,ping_timeout=20) as ws:
            session_model='gpt-realtime'
            await ws.send(json.dumps(opening_response(tenant_id),ensure_ascii=False))
            print('Realtime opening requested for',call_id,flush=True)
            async for raw in ws:
                event=json.loads(raw); event_type=event.get('type','')
                if event_type == 'session.created':
                    session_model=((event.get('session') or {}).get('model') or session_model)
                if event_type == 'response.created' and ((event.get('response') or {}).get('metadata') or {}).get('purpose') == 'opening_greeting':
                    print('Realtime opening started for',call_id,flush=True)
                if event_type == 'error':
                    record_call_failure(call_id,'provider_error')
                if event_type == 'response.done':
                    response=event.get('response') or {}
                    if (response.get('metadata') or {}).get('purpose') == 'opening_greeting':
                        print('Realtime opening finished for',call_id,response.get('status',''),flush=True)
                    model=response.get('model') or session_model
                    usage=response.get('usage') or event.get('usage')
                    if usage: save_usage(call_id,model,usage)
                if event_type in {'conversation.item.input_audio_transcription.completed','response.audio_transcript.done'}:
                    text=(event.get('transcript') or '').strip()
                    if text: save_call_event(call_id,'active',('\nMüşteri: ' if event_type.startswith('conversation.') else '\nAI: ')+text)
                if event_type == 'response.function_call_arguments.done' and event.get('name') == 'search_knowledge':
                    try:
                        args=json.loads(event.get('arguments') or '{}'); query=str(args.get('query','')).strip(); results=knowledge_search(tenant_id,query); log_knowledge_search(tenant_id,call_id,query,results); result={'ok':True,'query':query,'results':results,'message':'No matching published knowledge was found.' if not results else 'Use only these retrieved tenant knowledge snippets.'}
                    except Exception as exc: result={'ok':False,'message':str(exc),'results':[]}
                    await ws.send(json.dumps({'type':'conversation.item.create','item':{'type':'function_call_output','call_id':event.get('call_id'),'output':json.dumps(result,ensure_ascii=False)}})); await ws.send(json.dumps({'type':'response.create'}))
                if event_type == 'response.function_call_arguments.done' and event.get('name') == 'create_appointment':
                    try:
                        args=json.loads(event.get('arguments') or '{}')
                        required=('customer_name','phone','service','appointment_at')
                        if not all(str(args.get(k,'')).strip() for k in required): raise ValueError('Eksik randevu bilgisi')
                        calendar_result=calendar_reserve(tenant_id,args)
                        if not calendar_result.get('ok'): raise ValueError(calendar_result.get('message','Takvim rezervasyonu başarısız'))
                        conn=db(); cur=conn.execute('INSERT INTO appointments(tenant_id,call_id,customer_name,phone,service,appointment_at,notes,created_at) VALUES(?,?,?,?,?,?,?,?)',(tenant_id,call_id,str(args['customer_name']).strip(),str(args['phone']).strip(),str(args['service']).strip(),str(args['appointment_at']).strip(),str(args.get('notes','')).strip(),now())); conn.commit(); appointment_id=cur.lastrowid; conn.close()
                        result={'ok':True,'appointment_id':appointment_id,'message':'Randevu kaydedildi','calendar_event_id':calendar_result.get('event_id','')}
                    except Exception as exc:
                        result={'ok':False,'message':str(exc)}
                    await ws.send(json.dumps({'type':'conversation.item.create','item':{'type':'function_call_output','call_id':event.get('call_id'),'output':json.dumps(result,ensure_ascii=False)}}))
                    await ws.send(json.dumps({'type':'response.create'}))
                    if result.get('ok'):
                        threading.Thread(target=hangup_realtime_call,args=(call_id,6),daemon=True,name='hangup-'+call_id[-8:]).start()
                if event_type == 'response.function_call_arguments.done' and event.get('name') == 'request_human_callback':
                    try:
                        args=json.loads(event.get('arguments') or '{}')
                        result=save_callback_request(tenant_id,call_id,args)
                        result['message']='A human callback request has been saved. Confirm the callback request to the caller; do not say the live call was transferred.'
                    except Exception:
                        result={'ok':False,'message':'The callback request could not be saved. Ask the caller to repeat or use another contact method.'}
                    await ws.send(json.dumps({'type':'conversation.item.create','item':{'type':'function_call_output','call_id':event.get('call_id'),'output':json.dumps(result,ensure_ascii=False)}}))
                    await ws.send(json.dumps({'type':'response.create'}))
                if event_type in {'session.ended','realtime.call.ended'}: save_call_event(call_id,'ended'); break
    except websockets.ConnectionClosed:
        pass
    except Exception:
        record_call_failure(call_id,'sideband_failed')
    finally:
        save_call_event(call_id,'ended')

def start_realtime_sideband(call_id, tenant_id):
    threading.Thread(target=lambda: asyncio.run(realtime_sideband(call_id,tenant_id)),daemon=True,name='realtime-'+call_id[-8:]).start()

def hangup_realtime_call(call_id, delay=6):
    """Give the assistant time to say goodbye, then terminate the SIP leg."""
    time.sleep(delay)
    try:
        key,_=configured_openai(); req=urllib.request.Request('https://api.openai.com/v1/realtime/calls/'+str(call_id)+'/hangup',headers={'Authorization':'Bearer '+key},method='POST'); urllib.request.urlopen(req,timeout=10).read()
    except Exception as exc: print('Realtime hangup error for',call_id,repr(exc),flush=True)

def normalize_phone(value):
    return re.sub(r'\D','',str(value or ''))

def tenant_from_payload(payload):
    """Resolve an incoming SIP call to a tenant using the called DID/URI."""
    candidates=[]
    def walk(value, key=''):
        if isinstance(value,dict):
            for k,v in value.items(): walk(v,str(k).lower())
        elif isinstance(value,list):
            for v in value: walk(v,key)
        elif isinstance(value,(str,int)) and any(x in key for x in ('to','did','destination','called','sip')):
            candidates.append(normalize_phone(value))
    walk(payload)
    conn=db(); rows=conn.execute('SELECT tenant_id,username,did FROM tenant_sip WHERE username<>""').fetchall(); fallback=None
    active=conn.execute('SELECT id FROM tenants WHERE role="customer" AND status="active" ORDER BY id').fetchall(); conn.close()
    if len(active)==1: fallback=active[0]['id']
    for candidate in candidates:
        for row in rows:
            if candidate and candidate in {normalize_phone(row['username']),normalize_phone(row['did'])}:
                return row['tenant_id']
    return fallback or 2

GOOGLE_SCOPE='https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/calendar.freebusy'
GOOGLE_REDIRECT=PUBLIC_URL+'/api/google/callback'

def google_credentials():
    return os.environ.get('GOOGLE_CLIENT_ID','').strip(),os.environ.get('GOOGLE_CLIENT_SECRET','').strip()

def google_access_token(tenant_id):
    client_id,client_secret=google_credentials()
    conn=db(); row=conn.execute('SELECT * FROM google_tokens WHERE tenant_id=?',(tenant_id,)).fetchone(); conn.close()
    if not row: return ''
    if row['expires_at'] > now()+60: return reveal(row['access_token'])
    refresh=reveal(row['refresh_token'])
    if not refresh or not client_id or not client_secret: return ''
    body=urllib.parse.urlencode({'client_id':client_id,'client_secret':client_secret,'refresh_token':refresh,'grant_type':'refresh_token'}).encode()
    try:
        req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')
        token=json.loads(urllib.request.urlopen(req,timeout=15).read()); access=token.get('access_token','');
        if not access: return ''
        conn=db(); conn.execute('UPDATE google_tokens SET access_token=?,expires_at=?,updated_at=? WHERE tenant_id=?',(protect(access),now()+int(token.get('expires_in',3600)),now(),tenant_id)); conn.commit(); conn.close(); return access
    except Exception: return ''

def google_api(tenant_id,method,url,payload=None):
    token=google_access_token(tenant_id)
    if not token: return None
    body=json.dumps(payload).encode() if payload is not None else None
    headers={'Authorization':'Bearer '+token}
    if body is not None: headers['Content-Type']='application/json'
    try:
        req=urllib.request.Request(url,data=body,headers=headers,method=method)
        with urllib.request.urlopen(req,timeout=15) as response: return json.loads(response.read() or '{}')
    except Exception: return None

def calendar_reserve(tenant_id,args):
    token=google_access_token(tenant_id)
    if not token: return {'ok':True,'connected':False}
    from datetime import datetime,timedelta
    raw=str(args['appointment_at']).strip()
    try:
        start=datetime.fromisoformat(raw.replace('Z','+00:00'))
        if start.tzinfo is None: start=start.replace().astimezone()
    except Exception: return {'ok':False,'message':'Rezervasyon tarihi anlaşılmadı'}
    end=start+timedelta(minutes=60)
    start_iso=start.isoformat(); end_iso=end.isoformat()
    busy=google_api(tenant_id,'POST','https://www.googleapis.com/calendar/v3/freeBusy',{'timeMin':start_iso,'timeMax':end_iso,'items':[{'id':'primary'}]})
    if busy is None: return {'ok':False,'message':'Google Calendar uygunluk kontrolü başarısız'}
    calendars=busy.get('calendars',{}); primary=calendars.get('primary',{})
    if primary.get('busy'): return {'ok':False,'message':'Seçilen saat Google Calendar’da dolu'}
    event={'summary':f"{args['service']} — {args['customer_name']}",'description':str(args.get('notes','')),'start':{'dateTime':start_iso,'timeZone':'Europe/Istanbul'},'end':{'dateTime':end_iso,'timeZone':'Europe/Istanbul'},'extendedProperties':{'private':{'oim_tenant':str(tenant_id)}}}
    created=google_api(tenant_id,'POST','https://www.googleapis.com/calendar/v3/calendars/primary/events',event)
    if not created or not created.get('id'): return {'ok':False,'message':'Google Calendar rezervasyonu oluşturulamadı'}
    return {'ok':True,'connected':True,'event_id':created['id']}

def knowledge_context(tenant_id):
    conn=db(); rows=conn.execute('SELECT language,title,content FROM knowledge_documents WHERE tenant_id=? AND status="published" ORDER BY language,updated_at DESC',(tenant_id,)).fetchall(); conn.close()
    if not rows: return 'No published knowledge-base content has been provided yet. Do not invent business details.'
    chunks=[]; total=0
    for row in rows:
        text=f"[{row['language'].upper()}] {row['title']}\n{row['content'].strip()}"
        if total+len(text)>18000: break
        chunks.append(text); total+=len(text)
    return '\n\n'.join(chunks)

def knowledge_search(tenant_id, query, limit=4):
    """Tenant-scoped lightweight RAG retrieval over published Markdown paragraphs."""
    terms=[x.lower() for x in re.findall(r'[\wçğıöşüİĞÖŞÜ]+',str(query or ''),re.UNICODE) if len(x)>1]
    if not terms: return []
    conn=db(); rows=conn.execute('SELECT language,title,content FROM knowledge_documents WHERE tenant_id=? AND status="published" ORDER BY updated_at DESC',(tenant_id,)).fetchall(); conn.close(); results=[]
    for row in rows:
        paragraphs=[p.strip() for p in re.split(r'\n\s*\n',row['content']) if p.strip()]
        for paragraph in paragraphs:
            hay=paragraph.lower(); score=sum(hay.count(term) for term in terms)
            if score: results.append((score,f"[{row['language'].upper()}] {row['title']}\n{paragraph}"))
    results.sort(key=lambda item:item[0],reverse=True)
    return [text for _,text in results[:max(1,min(limit,8))]]

def log_knowledge_search(tenant_id, call_id, query, results):
    conn=db(); conn.execute('INSERT INTO knowledge_search_events(tenant_id,call_id,query,result_count,results,created_at) VALUES(?,?,?,?,?,?)',(tenant_id,str(call_id),str(query)[:1000],len(results),json.dumps(results,ensure_ascii=False),now())); conn.commit(); conn.close()

CALL_STATUSES = {'incoming', 'active', 'ended', 'failed', 'rejected_no_credit'}

def query_value(query, name, default=''):
    values = query.get(name, [default])
    if len(values) != 1:
        raise ValueError(f'{name} must be supplied only once')
    return values[0]

def query_integer(query, name, default, minimum=1, maximum=1_000_000):
    text = str(query_value(query, name, str(default)))
    if not re.fullmatch(r'\d+', text):
        raise ValueError(f'{name} must be an integer')
    value = int(text)
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}')
    return value

def selected_tenant(session, query):
    # Customer-supplied tenant identifiers never change their session's scope.
    if session['role'] != 'admin':
        return session['tenant_id']
    return query_integer(query, 'tenant_id', 0, 0, 2**63-1)

def call_history(conn, session, query):
    tenant_id = selected_tenant(session, query)
    page = query_integer(query, 'page', 1)
    page_size = query_integer(query, 'page_size', 50, 1, 100)
    status = query_value(query, 'status').strip()
    caller = query_value(query, 'caller').strip()
    if status and status not in CALL_STATUSES:
        raise ValueError('status must be incoming, active, ended, failed, or rejected_no_credit')
    if len(caller) > 100:
        raise ValueError('caller must contain at most 100 characters')
    dates = {}
    for name in ('date_from', 'date_to'):
        value = query_value(query, name).strip()
        if value:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError(f'{name} must use YYYY-MM-DD')
            try:
                dates[name] = date.fromisoformat(value)
            except ValueError:
                raise ValueError(f'{name} must be a valid calendar date') from None
    if dates.get('date_from', date.min) > dates.get('date_to', date.max):
        raise ValueError('date_from must not be later than date_to')
    # A snapshot prevents newly inserted calls from shifting later pages/reports.
    latest_id = conn.execute('SELECT COALESCE(MAX(id),0) FROM calls WHERE tenant_id=?', (tenant_id,)).fetchone()[0]
    snapshot_id = query_integer(query, 'snapshot_id', latest_id, 0, 2**63-1)
    conditions = ['c.tenant_id=?', 'c.id<=?']
    params = [tenant_id, snapshot_id]
    if status:
        conditions.append('c.status=?')
        params.append(status)
    if caller:
        conditions.append("c.caller LIKE ? ESCAPE '\\'")
        params.append('%' + caller.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
    for name, comparison in (('date_from', '>='), ('date_to', '<')):
        if name in dates:
            day = dates[name]
            try:
                if name == 'date_to':
                    day += timedelta(days=1)
                timestamp = int(datetime.combine(day, datetime.min.time(), timezone.utc).timestamp())
            except (ValueError, OverflowError, OSError):
                raise ValueError(f'{name} is outside the supported date range') from None
            conditions.append(f'c.started_at{comparison}?')
            params.append(timestamp)
    where = ' AND '.join(conditions)
    joined = 'FROM calls c LEFT JOIN call_usage u ON u.call_id=c.call_id WHERE ' + where
    summary_row = conn.execute('''SELECT COUNT(*) AS total_calls,
        COALESCE(SUM(CASE WHEN c.status='ended' THEN 1 ELSE 0 END),0) AS completed_calls,
        COALESCE(SUM(CASE WHEN c.status='ended' THEN MAX(0,COALESCE(c.ended_at,c.started_at)-c.started_at) ELSE 0 END),0) AS total_duration_seconds,
        COALESCE(SUM(c.billed_credits),0) AS billed_credits,
        COALESCE(SUM(u.estimated_openai_usd),0) AS estimated_openai_usd,
        COALESCE(SUM(u.total_tokens),0) AS total_tokens,
        COALESCE(SUM(CASE WHEN u.estimated_openai_usd IS NOT NULL THEN 1 ELSE 0 END),0) AS metered_calls ''' + joined, params).fetchone()
    summary = dict(summary_row)
    summary['average_duration_seconds'] = round(summary['total_duration_seconds'] / summary['completed_calls']) if summary['completed_calls'] else 0
    summary['billed_credits'] = round(summary['billed_credits'], 2)
    summary['estimated_openai_usd'] = round(summary['estimated_openai_usd'], 8)
    rows = conn.execute('''SELECT c.call_id,c.caller,c.status,c.transcript,c.started_at,c.ended_at,c.billed_credits,c.failure_code,c.failure_message,
        u.model,u.input_tokens,u.output_tokens,u.total_tokens,u.input_audio_tokens,u.output_audio_tokens,u.estimated_openai_usd,
        COALESCE(r.outcome,'') AS review_outcome,COALESCE(r.summary,'') AS review_summary,COALESCE(r.notes,'') AS review_notes,
        (SELECT COUNT(*) FROM knowledge_search_events k WHERE k.call_id=c.call_id AND k.tenant_id=c.tenant_id) AS knowledge_search_count,
        (SELECT COUNT(*) FROM knowledge_search_events k WHERE k.call_id=c.call_id AND k.tenant_id=c.tenant_id AND k.result_count>0) AS knowledge_success_count,
        (SELECT COUNT(*) FROM appointments a WHERE a.call_id=c.call_id AND a.tenant_id=c.tenant_id) AS appointment_count,
        (SELECT COUNT(*) FROM callback_requests h WHERE h.call_id=c.call_id AND h.tenant_id=c.tenant_id) AS callback_count '''
        + joined.replace('WHERE ', 'LEFT JOIN call_reviews r ON r.call_id=c.call_id AND r.tenant_id=c.tenant_id WHERE ', 1)
        + ' ORDER BY c.started_at DESC,c.id DESC LIMIT ? OFFSET ?', params + [page_size, (page-1)*page_size]).fetchall()
    items=[]
    for item in rows:
        call=dict(item)
        signals=[]
        signals.append(('completed', True if call['status']=='ended' else False if call['status'] in {'failed','rejected_no_credit'} else None, 35))
        signals.append(('assistant_responded', True if re.search(r'^\s*(?:AI|Assistant)\s*:',call['transcript'] or '',re.I|re.M) else False if call['status'] in {'ended','failed'} else None, 35))
        searches=int(call.pop('knowledge_search_count') or 0); useful=int(call.pop('knowledge_success_count') or 0)
        signals.append(('knowledge_helpful', (useful>0) if searches else None, 15))
        resolved=bool(int(call.pop('appointment_count') or 0) or int(call.pop('callback_count') or 0))
        outcome=call['review_outcome']
        signals.append(('follow_up_recorded', True if resolved or outcome in {'resolved','appointment_booked','callback_needed'} else False if outcome=='unresolved' else None, 15))
        known=[signal for signal in signals if signal[1] is not None]
        call['quality_score']=round(sum(weight for _,value,weight in known if value)*100/sum(weight for _,_,weight in known)) if len(known)>=2 else None
        call['quality_coverage']=len(known)
        call['quality_signals']=[{'key':key,'value':value} for key,value,_ in signals]
        items.append(call)
    traffic = conn.execute("SELECT date(c.started_at,'unixepoch') AS day,COUNT(*) AS calls FROM calls c WHERE " + where + " GROUP BY day ORDER BY day", params).fetchall()
    total = summary['total_calls']
    return {
        'items': items,
        'pagination': {'page':page, 'page_size':page_size, 'total':total,
            'total_pages':math.ceil(total/page_size), 'has_next':page*page_size<total,
            'has_previous':page>1, 'snapshot_id':snapshot_id},
        'filters': {'tenant_id':tenant_id, 'status':status, 'caller':caller,
            'date_from':dates['date_from'].isoformat() if 'date_from' in dates else '',
            'date_to':dates['date_to'].isoformat() if 'date_to' in dates else '', 'timezone':'UTC'},
        'summary':summary, 'traffic':[dict(row) for row in traffic],
    }

def tenant_readiness(conn, tenant_id):
    tenant=conn.execute('SELECT id,name FROM tenants WHERE id=? AND role="customer"',(tenant_id,)).fetchone()
    if not tenant: return None
    sip=conn.execute('SELECT username,domain,password FROM tenant_sip WHERE tenant_id=?',(tenant_id,)).fetchone()
    settings=conn.execute('SELECT greeting FROM tenant_ai_settings WHERE tenant_id=?',(tenant_id,)).fetchone()
    docs=conn.execute('SELECT COUNT(*) FROM knowledge_documents WHERE tenant_id=? AND status="published"',(tenant_id,)).fetchone()[0]
    provider=conn.execute('SELECT api_key,enabled FROM provider_settings WHERE provider="openai"').fetchone()
    provider_ready=bool((provider and provider['enabled'] and reveal(provider['api_key'])) or os.environ.get('OPENAI_API_KEY','').strip())
    checks=[
        {'key':'sip','ready':bool(sip and sip['username'].strip() and sip['domain'].strip() and reveal(sip['password']))},
        {'key':'provider','ready':provider_ready},
        {'key':'greeting','ready':bool(settings and settings['greeting'].strip())},
        {'key':'knowledge','ready':docs>0,'published_count':docs},
    ]
    return {'tenant_id':tenant_id,'tenant_name':tenant['name'],'ready':all(x['ready'] for x in checks),'checks':checks,'pbx_route':'unverified','limitations':['The app cannot verify carrier registration or place an outbound test call. Confirm routing with your PBX operator.']}

def usage_report(conn, session, query):
    tenant_id=selected_tenant(session,query)
    today=datetime.now(timezone.utc).date()
    parsed={}
    for name,default in (('date_from',today-timedelta(days=29)),('date_to',today)):
        value=query_value(query,name).strip()
        try: parsed[name]=date.fromisoformat(value) if value else default
        except ValueError: raise ValueError(f'{name} must use YYYY-MM-DD') from None
    if parsed['date_from']>parsed['date_to']: raise ValueError('date_from must not be later than date_to')
    if (parsed['date_to']-parsed['date_from']).days>92: raise ValueError('Date range cannot exceed 93 days')
    start=int(datetime.combine(parsed['date_from'],datetime.min.time(),timezone.utc).timestamp())
    end=int(datetime.combine(parsed['date_to']+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
    sql='''SELECT c.tenant_id,date(c.started_at,'unixepoch') AS day,COUNT(*) AS calls,
        SUM(c.billed_credits) AS billed_credits,SUM(u.estimated_openai_usd) AS estimated_openai_usd,
        COUNT(u.estimated_openai_usd) AS metered_calls,SUM(u.total_tokens) AS total_tokens
        FROM calls c LEFT JOIN call_usage u ON u.call_id=c.call_id
        WHERE c.tenant_id IN (SELECT id FROM tenants WHERE role="customer") AND c.started_at>=? AND c.started_at<?'''
    params=[start,end]
    if tenant_id:
        sql+=' AND c.tenant_id=?'; params.append(tenant_id)
    rows=[dict(row) for row in conn.execute(sql+' GROUP BY c.tenant_id,day ORDER BY day,c.tenant_id',params).fetchall()]
    tenant_names={r['id']:r['name'] for r in conn.execute('SELECT id,name FROM tenants WHERE role="customer"').fetchall()}
    for row in rows:
        row['tenant_name']=tenant_names.get(row['tenant_id'],'')
        if not row['metered_calls']: row['estimated_openai_usd']=None
        row['billed_credits']=round(float(row['billed_credits'] or 0),2)
        if row['estimated_openai_usd'] is not None: row['estimated_openai_usd']=round(float(row['estimated_openai_usd']),8)
        row['total_tokens']=int(row['total_tokens'] or 0)
    by_day={}
    by_tenant={}
    for row in rows:
        daily=by_day.setdefault(row['day'],{'day':row['day'],'calls':0,'billed_credits':0.0,'estimated_openai_usd':0.0,'metered_calls':0,'total_tokens':0})
        per=by_tenant.setdefault(row['tenant_id'],{'tenant_id':row['tenant_id'],'tenant_name':row['tenant_name'],'calls':0,'billed_credits':0.0,'estimated_openai_usd':0.0,'metered_calls':0,'total_tokens':0})
        for target in (daily,per):
            target['calls']+=int(row['calls'] or 0); target['billed_credits']+=float(row['billed_credits'] or 0)
            target['total_tokens']+=int(row['total_tokens'] or 0); target['metered_calls']+=int(row['metered_calls'] or 0)
            if row['estimated_openai_usd'] is not None: target['estimated_openai_usd']+=row['estimated_openai_usd']
    def clean(target):
        for value in target.values():
            value['billed_credits']=round(value['billed_credits'],2)
            value['estimated_openai_usd']=round(value['estimated_openai_usd'],8) if value['metered_calls'] else None
    clean(by_day); clean(by_tenant)
    return {'filters':{'tenant_id':tenant_id,'date_from':parsed['date_from'].isoformat(),'date_to':parsed['date_to'].isoformat(),'timezone':'UTC'},'daily':list(by_day.values()),'tenants':list(by_tenant.values())}

def purge_expired_transcripts(timestamp=None):
    timestamp=timestamp or now(); conn=db(); results=[]
    try:
        conn.execute('BEGIN IMMEDIATE')
        policies=conn.execute('SELECT tenant_id,transcript_retention_days FROM tenant_retention WHERE transcript_retention_days IS NOT NULL').fetchall()
        for policy in policies:
            cutoff=timestamp-int(policy['transcript_retention_days'])*86400
            ids=[row['call_id'] for row in conn.execute('SELECT call_id FROM calls WHERE tenant_id=? AND status IN ("ended","failed") AND transcript<>"" AND COALESCE(ended_at,started_at)<?',(policy['tenant_id'],cutoff)).fetchall()]
            if ids:
                conn.executemany('UPDATE calls SET transcript="" WHERE tenant_id=? AND call_id=?',[(policy['tenant_id'],call_id) for call_id in ids])
                conn.executemany('UPDATE call_reviews SET summary="",notes="" WHERE tenant_id=? AND call_id=?',[(policy['tenant_id'],call_id) for call_id in ids])
            conn.execute('UPDATE tenant_retention SET last_purged_at=? WHERE tenant_id=?',(timestamp,policy['tenant_id']))
            results.append({'tenant_id':policy['tenant_id'],'purged_calls':len(ids)})
        conn.commit(); return results
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

def save_callback_request(tenant_id, call_id, args):
    phone=str(args.get('phone','')).strip(); reason=str(args.get('reason','')).strip()[:500]
    digits=re.sub(r'\D','',phone)
    if len(digits)<5 or len(phone)>32 or not re.fullmatch(r'[+0-9(). -]+',phone):
        raise ValueError('A valid callback phone number is required')
    conn=db()
    try:
        call=conn.execute('SELECT status FROM calls WHERE call_id=? AND tenant_id=?',(call_id,tenant_id)).fetchone()
        if not call: raise LookupError('Call not found')
        existing=conn.execute('SELECT id FROM callback_requests WHERE call_id=?',(call_id,)).fetchone()
        if existing: return {'ok':True,'request_id':existing['id'],'duplicate':True}
        if call['status'] not in {'incoming','active'}: raise ValueError('Callback requests can only be created during an active call')
        cur=conn.execute('INSERT OR IGNORE INTO callback_requests(tenant_id,call_id,phone,reason,created_at) VALUES(?,?,?,?,?)',(tenant_id,call_id,phone,reason,now()))
        conn.commit()
        row=conn.execute('SELECT id FROM callback_requests WHERE call_id=?',(call_id,)).fetchone()
        return {'ok':True,'request_id':row['id'],'duplicate':cur.rowcount==0}
    finally: conn.close()

class Handler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        self._database_connections=[]
        try:
            return super().handle_one_request()
        finally:
            for conn in self._database_connections:
                conn.close()
    def open_db(self):
        conn=db()
        self._database_connections.append(conn)
        return conn
    def log_message(self, fmt, *args): pass
    def send_json(self, data, status=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def body(self):
        length=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(length) or '{}')
    def session(self):
        cookie=self.headers.get('Cookie',''); token=next((x.split('=',1)[1] for x in cookie.split('; ') if x.startswith('oim_session=')),None)
        info=SESSIONS.get(token)
        if not info or info['expires'] < now(): return None
        return info
    def require(self, role=None):
        s=self.session()
        if not s: self.send_json({'error':'Oturum gerekli'},401); return None
        if role and s['role'] != role: self.send_json({'error':'Yetki yok'},403); return None
        return s
    def do_GET(self):
        path=urlparse(self.path).path
        if path == '/api/health': return self.send_json({'ok':True,'service':'oim-mvp'})
        if path == '/api/google/start':
            s=self.require()
            if not s: return
            client_id,client_secret=google_credentials()
            if not client_id or not client_secret: return self.send_json({'error':'Google OAuth henüz yapılandırılmadı'},503)
            state=protect(f"{s['tenant_id']}:{now()}")
            query=urllib.parse.urlencode({'client_id':client_id,'redirect_uri':GOOGLE_REDIRECT,'response_type':'code','access_type':'offline','prompt':'consent','scope':GOOGLE_SCOPE,'state':state})
            return self.send_json({'url':'https://accounts.google.com/o/oauth2/v2/auth?'+query})
        if path == '/api/google/callback':
            query=urllib.parse.parse_qs(urlparse(self.path).query); code=(query.get('code') or [''])[0]; state=(query.get('state') or [''])[0]
            try:
                decoded=cipher().decrypt(state.encode()).decode(); tenant_text,issued=decoded.split(':',1); tenant_id=int(tenant_text)
                if now()-int(issued)>600: raise ValueError('expired state')
                client_id,client_secret=google_credentials()
                body=urllib.parse.urlencode({'code':code,'client_id':client_id,'client_secret':client_secret,'redirect_uri':GOOGLE_REDIRECT,'grant_type':'authorization_code'}).encode()
                req=urllib.request.Request('https://oauth2.googleapis.com/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')
                token=json.loads(urllib.request.urlopen(req,timeout=20).read()); access=token.get('access_token',''); refresh=token.get('refresh_token','')
                if not access: raise ValueError('no access token')
                conn=self.open_db(); old=conn.execute('SELECT refresh_token FROM google_tokens WHERE tenant_id=?',(tenant_id,)).fetchone(); refresh=refresh or (reveal(old['refresh_token']) if old else '')
                conn.execute('INSERT INTO google_tokens(tenant_id,access_token,refresh_token,expires_at,calendar_id,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET access_token=excluded.access_token,refresh_token=excluded.refresh_token,expires_at=excluded.expires_at,updated_at=excluded.updated_at',(tenant_id,protect(access),protect(refresh),now()+int(token.get('expires_in',3600)),'primary',now())); conn.commit(); conn.close()
                location=PUBLIC_URL+'/#calendar?connected=1'
            except Exception:
                location=PUBLIC_URL+'/#calendar?connected=0'
            self.send_response(302); self.send_header('Location',location); self.end_headers(); return
        s=self.require()
        if not s: return
        conn=self.open_db(); row=conn.execute('SELECT * FROM tenants WHERE id=?',(s['tenant_id'],)).fetchone()
        if path == '/api/me': return self.send_json({'user':public_tenant(row)})
        if path == '/api/google/status':
            token_row=conn.execute('SELECT calendar_id,expires_at FROM google_tokens WHERE tenant_id=?',(s['tenant_id'],)).fetchone()
            client_id,client_secret=google_credentials()
            return self.send_json({'configured':bool(client_id and client_secret),'connected':bool(token_row),'calendar_id':token_row['calendar_id'] if token_row else 'primary'})
        if path == '/api/ledger':
            query=urllib.parse.parse_qs(urlparse(self.path).query); tid=s['tenant_id'] if s['role']!='admin' else int((query.get('tenant_id') or [0])[0]); kind=(query.get('kind') or [''])[0].strip().lower(); params=[tid]; sql='SELECT amount,kind,reason,meta,created_at FROM ledger WHERE tenant_id=?';
            if kind in {'credit','debit'}: sql+=' AND kind=?'; params.append(kind)
            sql+=' ORDER BY id DESC LIMIT 200'; rows=conn.execute(sql,tuple(params)).fetchall()
            return self.send_json({'items':[dict(x) for x in rows]})
        if path == '/api/calls':
            try:
                query=urllib.parse.parse_qs(urlparse(self.path).query, keep_blank_values=True)
                result=call_history(conn,s,query)
            except ValueError as error:
                return self.send_json({'error':str(error),'code':'invalid_call_query'},400)
            finally:
                conn.close()
            return self.send_json(result)
        query=urllib.parse.parse_qs(urlparse(self.path).query,keep_blank_values=True)
        if path == '/api/readiness':
            tid=selected_tenant(s,query)
            if not tid: return self.send_json({'error':'Select a customer first'},400)
            result=tenant_readiness(conn,tid)
            return self.send_json(result or {'error':'Customer not found'},200 if result else 404)
        if path == '/api/live-calls':
            tid=selected_tenant(s,query)
            if not tid: return self.send_json({'active':[],'failures':[]})
            active=conn.execute('SELECT call_id,status,started_at FROM calls WHERE tenant_id=? AND status IN ("incoming","active") ORDER BY started_at DESC LIMIT 100',(tid,)).fetchall()
            failures=conn.execute('SELECT call_id,status,started_at,ended_at,failure_code,failure_message FROM calls WHERE tenant_id=? AND status="failed" ORDER BY ended_at DESC LIMIT 20',(tid,)).fetchall()
            return self.send_json({'active':[dict(x) for x in active],'failures':[dict(x) for x in failures]})
        if path == '/api/usage-report':
            try: return self.send_json(usage_report(conn,s,query))
            except (ValueError,OverflowError,OSError) as error: return self.send_json({'error':str(error)},400)
        if path == '/api/callbacks':
            tid=selected_tenant(s,query)
            if not tid: return self.send_json({'items':[]})
            rows=conn.execute('SELECT id,tenant_id,call_id,phone,reason,status,created_at,completed_at FROM callback_requests WHERE tenant_id=? ORDER BY CASE status WHEN "pending" THEN 0 ELSE 1 END,created_at DESC LIMIT 200',(tid,)).fetchall()
            return self.send_json({'items':[dict(x) for x in rows]})
        if path == '/api/privacy':
            tid=selected_tenant(s,query)
            if not tid: return self.send_json({'error':'Select a customer first'},400)
            policy=conn.execute('SELECT transcript_retention_days,updated_at,last_purged_at FROM tenant_retention WHERE tenant_id=?',(tid,)).fetchone()
            return self.send_json({'tenant_id':tid,'transcript_retention_days':policy['transcript_retention_days'] if policy else None,'updated_at':policy['updated_at'] if policy else None,'last_purged_at':policy['last_purged_at'] if policy else None})
        if path == '/api/appointments':
            query=urllib.parse.parse_qs(urlparse(self.path).query); tenant_id=(int((query.get('tenant_id') or [2])[0]) if s['role']=='admin' else s['tenant_id']); rows=conn.execute('SELECT id,customer_name,phone,service,appointment_at,notes,status,created_at FROM appointments WHERE tenant_id=? ORDER BY appointment_at DESC LIMIT 100',(tenant_id,)).fetchall()
            return self.send_json({'items':[dict(x) for x in rows]})
        if path == '/api/admin/tenants':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            rows=conn.execute('SELECT * FROM tenants WHERE role="customer" ORDER BY id DESC').fetchall(); return self.send_json({'items':[public_tenant(x) for x in rows]})
        if path == '/api/admin/providers':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            items={r['provider']:public_provider(r) for r in conn.execute('SELECT * FROM provider_settings ORDER BY provider')}
            for name in ('openai','openai_ai','elevenlabs'):
                items.setdefault(name,{'provider':name,'model':'gpt-realtime' if name=='openai' else '', 'enabled':False,'configured':False,'masked':'','voice_id':'','check_status':'unchecked','checked_at':None})
            return self.send_json({'items':list(items.values())})
        if path == '/api/admin/system-flow':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            return self.send_json(admin_system_flow(conn))
        if path == '/api/admin/billing':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            row=conn.execute('SELECT credits_per_minute,ai_multiplier,server_hourly_rate,minimum_credit,updated_at FROM billing_settings WHERE id=1').fetchone()
            return self.send_json(dict(row) if row else {'credits_per_minute':0.1,'ai_multiplier':1,'server_hourly_rate':0,'minimum_credit':10})
        if path == '/api/admin/legal-settings':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            keys=('user_agreement','kvkk_text','smtp_host','smtp_port','smtp_username','smtp_from','smtp_password')
            rows={x['key']:x['value'] for x in conn.execute('SELECT key,value FROM system_settings WHERE key IN (%s)' % ','.join('?'*len(keys)),keys).fetchall()}
            return self.send_json({'user_agreement':rows.get('user_agreement',''),'kvkk_text':rows.get('kvkk_text',''),'smtp_host':rows.get('smtp_host',''),'smtp_port':rows.get('smtp_port','587'),'smtp_username':rows.get('smtp_username',''),'smtp_from':rows.get('smtp_from',''),'smtp_password_configured':bool(reveal(rows.get('smtp_password','')))})
        if path == '/api/admin/telegram':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            row=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=2').fetchone()
            if not row: return self.send_json({'configured':False,'chat_id':'','enabled':False,'masked':''})
            token=reveal(row['bot_token']); return self.send_json({'configured':bool(token),'chat_id':row['chat_id'],'enabled':bool(row['enabled']),'masked':('••••'+token[-6:] if len(token)>6 else '')})
        if path == '/api/tenant/telegram':
            tid=s['tenant_id']; row=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=?',(tid,)).fetchone()
            if not row: return self.send_json({'configured':False,'chat_id':'','enabled':False,'masked':''})
            token=reveal(row['bot_token']); return self.send_json({'configured':bool(token),'chat_id':row['chat_id'],'enabled':bool(row['enabled']),'masked':('••••'+token[-6:] if len(token)>6 else '')})
        if path.startswith('/api/contacts/') and path.endswith('/delete'):
            return self.send_json({'error':'Use POST for contact changes'},405)
        if path.startswith('/api/contacts/') and path.endswith('/update'):
            return self.send_json({'error':'Use POST for contact changes'},405)
        if path.startswith('/api/contacts/') and path.count('/') == 3 and path.rsplit('/',1)[-1].isdigit():
            query=urllib.parse.parse_qs(urlparse(self.path).query); tid=s['tenant_id'] if s['role']!='admin' else int((query.get('tenant_id') or [0])[0]); contact_id=int(path.rsplit('/',1)[-1]); contact=conn.execute('SELECT id,name,phone,email,notes,created_at,updated_at FROM crm_contacts WHERE id=? AND tenant_id=?',(contact_id,tid)).fetchone()
            if not contact: return self.send_json({'error':'CRM kaydı bulunamadı'},404)
            calls=conn.execute('SELECT call_id,caller,status,transcript,started_at,ended_at,billed_credits FROM calls WHERE tenant_id=? AND caller=? ORDER BY started_at DESC LIMIT 20',(tid,contact['phone'])).fetchall() if contact['phone'] else []
            appointments=conn.execute('SELECT id,customer_name,phone,service,appointment_at,notes,status,created_at FROM appointments WHERE tenant_id=? AND phone=? ORDER BY appointment_at DESC LIMIT 20',(tid,contact['phone'])).fetchall() if contact['phone'] else []
            return self.send_json({'contact':dict(contact),'calls':[dict(x) for x in calls],'appointments':[dict(x) for x in appointments]})
        if path == '/api/contacts':
            tid=s['tenant_id'] if s['role']!='admin' else int(urlparse(self.path).query.split('tenant_id=')[-1] or 0)
            rows=conn.execute('SELECT id,name,phone,email,notes,created_at,updated_at FROM crm_contacts WHERE tenant_id=? ORDER BY updated_at DESC LIMIT 200',(tid,)).fetchall()
            return self.send_json({'items':[dict(x) for x in rows]})
        if path == '/api/knowledge':
            query=urllib.parse.parse_qs(urlparse(self.path).query); tid=s['tenant_id'] if s['role']!='admin' else int((query.get('tenant_id') or [0])[0]); rows=conn.execute('SELECT id,language,title,content,status,created_at,updated_at FROM knowledge_documents WHERE tenant_id=? ORDER BY language,updated_at DESC',(tid,)).fetchall()
            return self.send_json({'items':[dict(x) for x in rows]})
        if path == '/api/tenant/ai-settings':
            tid=selected_tenant(s,query); row=conn.execute('SELECT greeting,voice,working_hours,updated_at FROM tenant_ai_settings WHERE tenant_id=?',(tid,)).fetchone(); return self.send_json(dict(row) if row else {'greeting':'','voice':'alloy','working_hours':'','updated_at':None})
        if path == '/api/admin/knowledge-search-events':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            query=urllib.parse.parse_qs(urlparse(self.path).query); tid=int((query.get('tenant_id') or [2])[0]); rows=conn.execute('SELECT call_id,query,result_count,created_at FROM knowledge_search_events WHERE tenant_id=? ORDER BY id DESC LIMIT 100',(tid,)).fetchall(); return self.send_json({'items':[dict(x) for x in rows]})
        if path.startswith('/api/admin/tenants/') and path.endswith('/sip'):
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            tid=int(path.split('/')[4]); row=conn.execute('SELECT username,did,domain,password FROM tenant_sip WHERE tenant_id=?',(tid,)).fetchone()
            if not row: return self.send_json({'tenant_id':tid,'configured':False,'username':'','did':'','domain':'','masked':''})
            p=reveal(row['password']); return self.send_json({'tenant_id':tid,'configured':bool(p),'username':row['username'],'did':row['did'],'domain':row['domain'],'masked':('••••'+p[-4:] if len(p)>4 else '')})
        self.send_json({'error':'Bulunamadı'},404)
    def do_POST(self):
        path=urlparse(self.path).path
        if path == '/api/login':
            data=self.body(); client_ip=self.client_address[0]; current=now()
            with LOGIN_LOCK:
                attempt=LOGIN_ATTEMPTS.get(client_ip,{'count':0,'first':current,'locked_until':0})
                if attempt.get('locked_until',0)>current: return self.send_json({'error':'Çok fazla başarısız giriş. Lütfen daha sonra tekrar deneyin.'},429)
                if current-attempt.get('first',current)>600: attempt={'count':0,'first':current,'locked_until':0}
            conn=self.open_db(); row=conn.execute('SELECT * FROM tenants WHERE username=? AND status="active"',(data.get('username','').strip(),)).fetchone()
            if not row or not check_password(data.get('password',''),row['password_hash']):
                with LOGIN_LOCK:
                    attempt['count']=attempt.get('count',0)+1; attempt['first']=attempt.get('first',current); attempt['locked_until']=current+900 if attempt['count']>=5 else 0; LOGIN_ATTEMPTS[client_ip]=attempt
                return self.send_json({'error':'Kullanıcı adı veya parola hatalı'},401)
            with LOGIN_LOCK: LOGIN_ATTEMPTS.pop(client_ip,None)
            token=secrets.token_urlsafe(32); SESSIONS[token]={'tenant_id':row['id'],'role':row['role'],'expires':now()+SESSION_TTL}
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Set-Cookie',f'oim_session={token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={SESSION_TTL}'); self.end_headers(); self.wfile.write(json.dumps({'user':public_tenant(row)},ensure_ascii=False).encode()); return
        if path == '/api/logout':
            cookie=self.headers.get('Cookie',''); token=next((x.split('=',1)[1] for x in cookie.split('; ') if x.startswith('oim_session=')),None)
            if token: SESSIONS.pop(token,None)
            body=json.dumps({'ok':True}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Set-Cookie','oim_session=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path == '/api/logout-all':
            current=self.session()
            if not current: return self.send_json({'error':'Oturum gerekli'},401)
            for key,value in list(SESSIONS.items()):
                if value.get('tenant_id')==current.get('tenant_id'): SESSIONS.pop(key,None)
            body=json.dumps({'ok':True,'message':'Tüm oturumlar kapatıldı'}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Set-Cookie','oim_session=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path == '/api/openai/webhook':
            raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
            webhook_id=self.headers.get('webhook-id',''); ts=self.headers.get('webhook-timestamp',''); sigs=self.headers.get('webhook-signature',''); secret=os.environ.get('OPENAI_WEBHOOK_SECRET','')
            valid=False
            try:
                key=base64.b64decode(secret.split('_',1)[1]); signed=(webhook_id+'.'+ts+'.').encode()+raw
                expected=base64.b64encode(hmac.new(key,signed,hashlib.sha256).digest()).decode()
                fresh=abs(int(time.time())-int(ts)) <= 300
                valid=bool(secret and webhook_id and ts and fresh and any(hmac.compare_digest(s.split(',',1)[1],expected) for s in sigs.split(' ') if s.startswith('v1,')))
            except Exception: valid=False
            if not secret or not valid: return self.send_json({'error':'Geçersiz veya yapılandırılmamış webhook imzası'},401)
            data=json.loads(raw or '{}'); event_type=data.get('type',''); payload=data.get('data') or data
            call_id=payload.get('call_id') or payload.get('session_id') or payload.get('id')
            if event_type == 'realtime.call.incoming' and call_id:
                tenant_id=tenant_from_payload(payload)
                key,model=configured_openai()
                conn=self.open_db(); tenant=conn.execute('SELECT name,credits,status FROM tenants WHERE id=?',(tenant_id,)).fetchone(); conn.execute('INSERT OR IGNORE INTO calls(tenant_id,call_id,status,started_at) VALUES(?,?,?,?)',(tenant_id,str(call_id),'incoming',now()));
                pricing=conn.execute('SELECT credits_per_minute,ai_multiplier,minimum_credit FROM billing_settings WHERE id=1').fetchone()
                minimum_credit=max(0.01,float(pricing['minimum_credit'] if pricing else 10))
                if not tenant or tenant['status']!='active' or float(tenant['credits']) < minimum_credit:
                    conn.execute('UPDATE calls SET status="rejected_no_credit",ended_at=?,billed_at=? WHERE call_id=?',(now(),now(),str(call_id))); conn.commit(); conn.close()
                    return self.send_json({'ok':True,'accepted':False,'reason':'insufficient_credits'})
                conn.commit(); conn.close()
                business_name=tenant['name'] if tenant else 'müşteri işletmesi'
                settings_conn=self.open_db(); ai_settings=settings_conn.execute('SELECT greeting,voice,working_hours FROM tenant_ai_settings WHERE tenant_id=?',(tenant_id,)).fetchone(); settings_conn.close(); greeting=(ai_settings['greeting'] if ai_settings else '').strip(); voice=(ai_settings['voice'] if ai_settings else 'alloy') or 'alloy'; working_hours=(ai_settings['working_hours'] if ai_settings else '').strip()
                knowledge=knowledge_context(tenant_id)
                instructions=f'''You are the warm, concise voice assistant for {business_name}. You support exactly three languages: Turkish (TR), English (EN), and Russian (RU).
Language policy:
- Detect the caller's language from their first clear utterance and continue in that same language.
- If the caller switches language, follow the new language.
- If the caller mixes languages or the language is unclear, ask politely: "Türkçe, English, или Русский?" and continue with the selected language.
- Keep names, phone numbers, dates, prices, and appointment details clear; repeat critical details for confirmation.
- Never invent prices, availability, policies, or business information. Use the tenant's published knowledge base when available; if the answer is missing, say that the business must confirm it.
Knowledge retrieval policy:
- For any business-specific question (price, breed/program, access, working hours, cancellation, refund, contact or policy), call search_knowledge before answering.
- Use only the retrieved tenant snippets; if no snippet answers the question, say that the business team must confirm it.
Appointment policy:
- Collect customer name, phone, service, Europe/Istanbul date-time, and optional note one by one.
- Confirm all details in the caller's language before calling create_appointment.
- Do not claim that an appointment is confirmed until the tool succeeds. If the calendar reports a busy time, offer another time.'''
                instructions += '\nCallback policy: If the caller requests a person or the issue cannot be resolved, offer a human callback, confirm the preferred phone number and a brief reason, then call request_human_callback. Only say a callback request is recorded after the tool succeeds. This does not transfer the live call.'
                instructions += '\nAfter a successful appointment, thank the caller, state that the reservation is recorded, say a brief goodbye, and do not continue asking questions.'
                if greeting: instructions += f'\nOpening greeting (use at the start of the call): {greeting}'
                if working_hours: instructions += f'\nBusiness working hours: {working_hours}. Do not offer appointments outside these hours.'
                instructions += f'''\n\nPUBLISHED KNOWLEDGE BASE (tenant-specific; treat it as the source of truth):\n{knowledge}\nUse only the relevant language section when answering. For detailed business questions, call search_knowledge first. If neither retrieved snippets nor this published context contains an answer, say so instead of guessing.'''
                tools=[
                    {'type':'function','name':'search_knowledge','description':'Müşterinin yayınlanmış tenant bilgi bankasında arama yap. Fiyat, program, çalışma saati, iade veya işletme kuralı sorularında önce bu aracı kullan.','parameters':{'type':'object','properties':{'query':{'type':'string','description':'Aranan konu veya müşteri sorusunun kısa özeti'}} ,'required':['query'],'additionalProperties':False}},
                    {'type':'function','name':'create_appointment','description':'Müşteri tüm ayrıntıları teyit ettikten sonra randevuyu OIM takvimine kaydeder.','parameters':{'type':'object','properties':{'customer_name':{'type':'string','description':'Müşterinin ad ve soyadı'},'phone':{'type':'string','description':'Telefon numarası'},'service':{'type':'string','description':'İstenen hizmet veya eğitim'},'appointment_at':{'type':'string','description':'Europe/Istanbul saat diliminde ISO 8601 tarih ve saat'},'notes':{'type':'string','description':'Kısa ek not'}},'required':['customer_name','phone','service','appointment_at'],'additionalProperties':False}},
                    {'type':'function','name':'request_human_callback','description':'Sorun çözülemediğinde veya müşteri insanla görüşmek istediğinde, onay aldığı telefon numarası ve kısa nedeni ile geri arama isteği kaydet. Canlı çağrıyı başka bir hatta aktardığını söyleme.','parameters':{'type':'object','properties':{'phone':{'type':'string','description':'Müşterinin geri aranmak için onayladığı telefon numarası'},'reason':{'type':'string','description':'Geri arama için kısa neden'}},'required':['phone'],'additionalProperties':False}}
                ]
                body=json.dumps({'type':'realtime','model':model,'output_modalities':['audio'],'instructions':instructions,'tools':tools,'tool_choice':'auto','tracing':'auto'}).encode()
                try:
                    req=urllib.request.Request('https://api.openai.com/v1/realtime/calls/'+str(call_id)+'/accept',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST'); urllib.request.urlopen(req,timeout=15)
                    save_call_event(str(call_id),'active'); start_realtime_sideband(str(call_id),tenant_id)
                    return self.send_json({'ok':True,'accepted':True})
                except Exception as exc:
                    record_call_failure(str(call_id),'accept_failed',bill=False)
                    return self.send_json({'ok':False,'accepted':False},502)
            return self.send_json({'ok':True,'ignored':True})
        s=self.require()
        if not s: return
        conn=self.open_db(); data=self.body()
        if path.startswith('/api/contacts/') and (path.endswith('/update') or path.endswith('/delete')):
            parts=path.strip('/').split('/')
            try:
                contact_id=int(parts[2]) if len(parts)==4 else 0
                tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0))
                if contact_id<1 or tid<1: raise ValueError()
            except (TypeError,ValueError,IndexError):
                return self.send_json({'error':'Geçersiz CRM kaydı'},400)
            if path.endswith('/delete'):
                cur=conn.execute('DELETE FROM crm_contacts WHERE id=? AND tenant_id=?',(contact_id,tid))
                conn.commit()
                if not cur.rowcount: return self.send_json({'error':'CRM kaydı bulunamadı'},404)
                return self.send_json({'ok':True,'deleted':True})
            name=str(data.get('name','')).strip()
            phone=str(data.get('phone','')).strip()
            email=str(data.get('email','')).strip()
            notes=str(data.get('notes','')).strip()
            if not name: return self.send_json({'error':'Kişi adı gerekli'},400)
            cur=conn.execute('UPDATE crm_contacts SET name=?,phone=?,email=?,notes=?,updated_at=? WHERE id=? AND tenant_id=?',(name,phone,email,notes,now(),contact_id,tid))
            conn.commit()
            if not cur.rowcount: return self.send_json({'error':'CRM kaydı bulunamadı'},404)
            return self.send_json({'ok':True,'id':contact_id,'name':name,'phone':phone,'email':email,'notes':notes})
        if path == '/api/call-review':
            call_id=str(data.get('call_id','')).strip(); tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0) or 0)
            outcome=str(data.get('outcome','')).strip(); summary=str(data.get('summary','')).strip(); notes=str(data.get('notes','')).strip()
            if not call_id or len(call_id)>200 or outcome not in {'','resolved','appointment_booked','callback_needed','unresolved'} or len(summary)>2000 or len(notes)>2000:
                return self.send_json({'error':'Review fields are invalid or too long'},400)
            call=conn.execute('SELECT 1 FROM calls WHERE call_id=? AND tenant_id=?',(call_id,tid)).fetchone()
            if not call: return self.send_json({'error':'Call not found'},404)
            conn.execute('''INSERT INTO call_reviews(call_id,tenant_id,outcome,summary,notes,updated_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(call_id) DO UPDATE SET outcome=excluded.outcome,summary=excluded.summary,notes=excluded.notes,updated_at=excluded.updated_at WHERE call_reviews.tenant_id=excluded.tenant_id''',
                (call_id,tid,outcome,summary,notes,now()))
            conn.commit(); return self.send_json({'ok':True,'call_id':call_id,'outcome':outcome,'summary':summary,'notes':notes})
        if path.startswith('/api/callbacks/') and path.endswith('/complete'):
            try: request_id=int(path.strip('/').split('/')[2]); tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0) or 0)
            except (TypeError,ValueError,IndexError): return self.send_json({'error':'Invalid callback request'},400)
            cur=conn.execute('UPDATE callback_requests SET status="completed",completed_at=? WHERE id=? AND tenant_id=?',(now(),request_id,tid))
            if not cur.rowcount: return self.send_json({'error':'Callback request not found'},404)
            conn.commit(); return self.send_json({'ok':True,'id':request_id,'status':'completed'})
        if path == '/api/privacy':
            tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0) or 0)
            tenant=conn.execute('SELECT 1 FROM tenants WHERE id=? AND role="customer"',(tid,)).fetchone()
            if not tenant: return self.send_json({'error':'Customer not found'},404)
            value=data.get('transcript_retention_days')
            if value in ('',None): days=None
            else:
                try: days=int(value)
                except (TypeError,ValueError): return self.send_json({'error':'Retention must be disabled or between 1 and 3650 days'},400)
                if days<1 or days>3650: return self.send_json({'error':'Retention must be disabled or between 1 and 3650 days'},400)
            conn.execute('''INSERT INTO tenant_retention(tenant_id,transcript_retention_days,updated_at) VALUES(?,?,?)
                ON CONFLICT(tenant_id) DO UPDATE SET transcript_retention_days=excluded.transcript_retention_days,updated_at=excluded.updated_at''',(tid,days,now()))
            conn.commit(); return self.send_json({'ok':True,'tenant_id':tid,'transcript_retention_days':days})
        if path in {'/api/admin/providers/test','/api/admin/providers/preview','/api/admin/ai-playground'}:
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            provider='openai_ai' if path.endswith('ai-playground') else str(data.get('provider','')).strip().lower()
            if provider not in PROVIDER_IDS: return self.send_json({'error':'Geçersiz sağlayıcı'},400)
            if path.endswith('/preview') and provider!='elevenlabs': return self.send_json({'error':'Ses denemesi için ElevenLabs seçin.'},400)
            row=conn.execute('SELECT * FROM provider_settings WHERE provider=?',(provider,)).fetchone()
            if not row: return self.send_json({'ok':False,'error':'Sağlayıcı tanımlı değil'},404)
            key=reveal(row['api_key'])
            if not key: return self.send_json({'ok':False,'error':'API anahtarı tanımlı değil'},400)
            is_test=path.endswith('/test')
            if not is_test and not row['enabled']: return self.send_json({'error':'Önce sağlayıcıyı etkinleştirin.'},400)
            if provider in {'openai','openai_ai'} and not row['model']: return self.send_json({'error':'Model kimliği gerekli.'},400)
            payload=None
            if not is_test:
                if not isinstance(data.get('text'),str): return self.send_json({'error':'Metin gerekli.'},400)
                text=str(data.get('text','')).strip()
                limit=500 if provider=='elevenlabs' else 1000
                if not text or len(text)>limit: return self.send_json({'error':f'Metin 1–{limit} karakter olmalı.'},400)
                if provider=='elevenlabs':
                    if not row['voice_id']: return self.send_json({'error':'Ses kimliği gerekli.'},400)
                    payload={'text':text,'model_id':row['model'] or 'eleven_flash_v2_5'}
                else: payload={'model':row['model'],'input':text,'max_output_tokens':400,'store':False}
            with PROVIDER_LOCK:
                recent=[x for x in PROVIDER_LIMITS.get(s['tenant_id'],[]) if x>now()-60]
                if len(recent)>=6: return self.send_json({'error':'Bir dakika içinde en fazla 6 deneme yapabilirsiniz.'},429)
                PROVIDER_LIMITS[s['tenant_id']]=recent+[now()]
            try:
                body=provider_request(provider,key,row['model'],payload,row['voice_id'])
                if is_test:
                    conn.execute('UPDATE provider_settings SET check_status="ok",checked_at=? WHERE provider=?',(now(),provider)); conn.commit()
                    return self.send_json({'ok':True,'provider':provider,'message':'Bağlantı başarılı'})
                if provider=='elevenlabs':
                    if not body: raise ValueError('Sağlayıcı ses döndürmedi.')
                    return self.send_json({'ok':True,'audio':base64.b64encode(body).decode(),'content_type':'audio/mpeg'})
                result=json.loads(body)
                if not isinstance(result,dict): raise ValueError('Sağlayıcı yanıtı okunamadı.')
                output='\n'.join(part.get('text','') for item in result.get('output',[]) if item.get('type')=='message' for part in item.get('content',[]) if part.get('type')=='output_text')
                if not output: raise ValueError('Sağlayıcı metin döndürmedi.')
                return self.send_json({'ok':True,'text':output})
            except (ValueError,OSError,TypeError,AttributeError) as error:
                if is_test:
                    conn.execute('UPDATE provider_settings SET check_status="error",checked_at=? WHERE provider=?',(now(),provider)); conn.commit()
                message=str(error) if isinstance(error,ValueError) and not isinstance(error,json.JSONDecodeError) else 'Sağlayıcı yanıtı okunamadı.'
                return self.send_json({'ok':False,'error':message},502)
        if path == '/api/admin/tenants':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            username=data.get('username','').strip(); name=data.get('name','').strip(); email=data.get('email','').strip(); credits=float(data.get('credits',0)); password=data.get('password') or secrets.token_urlsafe(10)
            if not username or not name: return self.send_json({'error':'Ad ve kullanıcı adı gerekli'},400)
            if len(password) < 8: return self.send_json({'error':'Parola en az 8 karakter olmalı'},400)
            if not data.get('agreement_accepted'): return self.send_json({'error':'Kullanıcı sözleşmesi onayı gerekli'},400)
            legal=conn.execute("SELECT key,value FROM system_settings WHERE key IN ('user_agreement','kvkk_text')").fetchall(); legal_values={x['key']:x['value'].strip() for x in legal}
            if not legal_values.get('user_agreement') or not legal_values.get('kvkk_text'): return self.send_json({'error':'Önce admin panelinden kullanıcı sözleşmesi ve KVKK metnini kaydedin'},400)
            try:
                accepted_at=now(); cur=conn.execute('INSERT INTO tenants(name,email,username,password_hash,role,credits,agreement_accepted,agreement_accepted_at,agreement_version,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,email,username,hash_password(password),'customer',credits,1,accepted_at,'v1',accepted_at)); tid=cur.lastrowid
                if credits: conn.execute('INSERT INTO ledger(tenant_id,amount,kind,reason,created_at) VALUES(?,?,?,?,?)',(tid,credits,'credit','İlk kredi tanımı',now()))
                conn.commit(); return self.send_json({'tenant':public_tenant(conn.execute('SELECT * FROM tenants WHERE id=?',(tid,)).fetchone()),'temporary_password':password})
            except sqlite3.IntegrityError: return self.send_json({'error':'Bu kullanıcı adı zaten kayıtlı'},409)
        if path == '/api/admin/legal-settings':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            agreement=str(data.get('user_agreement','')).strip(); kvkk=str(data.get('kvkk_text','')).strip(); host=str(data.get('smtp_host','')).strip(); username=str(data.get('smtp_username','')).strip(); sender=str(data.get('smtp_from','')).strip(); password=str(data.get('smtp_password',''))
            try: port=int(data.get('smtp_port',587))
            except (TypeError,ValueError): return self.send_json({'error':'SMTP portu geçersiz'},400)
            if port<1 or port>65535: return self.send_json({'error':'SMTP portu 1-65535 arasında olmalı'},400)
            values={'user_agreement':agreement,'kvkk_text':kvkk,'smtp_host':host,'smtp_port':str(port),'smtp_username':username,'smtp_from':sender}
            if password: values['smtp_password']=protect(password)
            timestamp=now()
            for key,value in values.items(): conn.execute('INSERT INTO system_settings(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(key,value,timestamp))
            conn.commit(); return self.send_json({'ok':True,'smtp_password_configured':bool(password or reveal((conn.execute('SELECT value FROM system_settings WHERE key="smtp_password"').fetchone() or {'value':''})['value']))})
        if path.startswith('/api/admin/tenants/') and path.endswith('/password'):
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            try: tid=int(path.split('/')[4])
            except (ValueError,IndexError): return self.send_json({'error':'Geçersiz müşteri'},400)
            password=str(data.get('password',''))
            if len(password) < 8: return self.send_json({'error':'Parola en az 8 karakter olmalı'},400)
            row=conn.execute('SELECT * FROM tenants WHERE id=? AND role="customer"',(tid,)).fetchone()
            if not row: return self.send_json({'error':'Müşteri bulunamadı'},404)
            conn.execute('UPDATE tenants SET password_hash=? WHERE id=?',(hash_password(password),tid)); conn.commit()
            return self.send_json({'ok':True,'tenant_id':tid})
        if path.startswith('/api/admin/tenants/') and path.endswith('/credits'):
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            tid=int(path.split('/')[4]); amount=float(data.get('amount',0)); reason=data.get('reason','Manuel kredi işlemi')
            row=conn.execute('SELECT * FROM tenants WHERE id=?',(tid,)).fetchone()
            if not row or row['role']!='customer': return self.send_json({'error':'Müşteri bulunamadı'},404)
            if row['credits']+amount < 0: return self.send_json({'error':'Yetersiz kredi'},400)
            conn.execute('UPDATE tenants SET credits=credits+? WHERE id=?',(amount,tid)); conn.execute('INSERT INTO ledger(tenant_id,amount,kind,reason,created_at) VALUES(?,?,?,?,?)',(tid,amount,'credit' if amount>=0 else 'debit',reason,now())); conn.commit(); return self.send_json({'tenant':public_tenant(conn.execute('SELECT * FROM tenants WHERE id=?',(tid,)).fetchone())})
        if path == '/api/usage':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            tid=int(data.get('tenant_id')); amount=float(data.get('amount',0)); reason=data.get('reason','Kullanım düşümü'); row=conn.execute('SELECT * FROM tenants WHERE id=?',(tid,)).fetchone()
            if not row or amount <= 0: return self.send_json({'error':'Geçerli tenant ve pozitif kullanım tutarı gerekli'},400)
            if row['credits'] < amount: return self.send_json({'error':'Yetersiz kredi','balance':row['credits']},400)
            conn.execute('UPDATE tenants SET credits=credits-? WHERE id=?',(amount,tid)); conn.execute('INSERT INTO ledger(tenant_id,amount,kind,reason,meta,created_at) VALUES(?,?,?,?,?,?)',(tid,-amount,'debit',reason,json.dumps(data,ensure_ascii=False),now())); conn.commit(); return self.send_json({'tenant':public_tenant(conn.execute('SELECT * FROM tenants WHERE id=?',(tid,)).fetchone())})
        if path == '/api/admin/providers':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            if any(not isinstance(data.get(name,''),str) for name in ('provider','api_key','model','voice_id')): return self.send_json({'error':'Geçersiz bağlantı alanı.'},400)
            provider=str(data.get('provider','')).strip().lower(); api_key=str(data.get('api_key','')); model=str(data.get('model','')).strip(); enabled=1 if data.get('enabled') else 0
            if provider not in PROVIDER_IDS: return self.send_json({'error':'Geçersiz sağlayıcı'},400)
            voice_id=str(data.get('voice_id','')).strip()
            if model and not re.fullmatch(r'[A-Za-z0-9._:/-]{1,100}',model): return self.send_json({'error':'Model kimliği geçersiz.'},400)
            if voice_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',voice_id): return self.send_json({'error':'Ses kimliği geçersiz.'},400)
            if api_key and (len(api_key)>4096 or not all(33<=ord(c)<=126 for c in api_key)): return self.send_json({'error':'API anahtarı geçersiz.'},400)
            if data.get('enabled',False) not in (True,False,0,1) or not isinstance(data.get('clear_key',False),bool): return self.send_json({'error':'Geçersiz bağlantı durumu.'},400)
            old=conn.execute('SELECT api_key,voice_id FROM provider_settings WHERE provider=?',(provider,)).fetchone()
            if old and 'voice_id' not in data: voice_id=old['voice_id']
            if not api_key:
                if old:
                    api_key=reveal(old['api_key'])
            if data.get('clear_key'): api_key=''
            conn.execute('''INSERT INTO provider_settings(provider,api_key,model,enabled,voice_id,updated_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(provider) DO UPDATE SET api_key=excluded.api_key,model=excluded.model,enabled=excluded.enabled,voice_id=excluded.voice_id,check_status='unchecked',checked_at=NULL,updated_at=excluded.updated_at''',(provider,protect(api_key),model,enabled,voice_id,now()))
            conn.commit(); return self.send_json({'provider':public_provider(conn.execute('SELECT * FROM provider_settings WHERE provider=?',(provider,)).fetchone())})
        if path == '/api/admin/billing':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            try:
                rate=float(data.get('credits_per_minute',0.1)); multiplier=float(data.get('ai_multiplier',1)); server=float(data.get('server_hourly_rate',0)); minimum=float(data.get('minimum_credit',10))
                if rate<0 or multiplier<0 or server<0 or minimum<0: raise ValueError()
            except (TypeError,ValueError): return self.send_json({'error':'Tarife değerleri sıfır veya daha büyük olmalı'},400)
            conn.execute('INSERT INTO billing_settings(id,credits_per_minute,ai_multiplier,server_hourly_rate,minimum_credit,updated_at) VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET credits_per_minute=excluded.credits_per_minute,ai_multiplier=excluded.ai_multiplier,server_hourly_rate=excluded.server_hourly_rate,minimum_credit=excluded.minimum_credit,updated_at=excluded.updated_at',(rate,multiplier,server,minimum,now())); conn.commit()
            return self.send_json({'ok':True,'credits_per_minute':rate,'ai_multiplier':multiplier,'server_hourly_rate':server,'minimum_credit':minimum})
        if path in {'/api/admin/telegram/test','/api/tenant/telegram/test'}:
            if path.startswith('/api/admin') and s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            tid=2 if s['role']=='admin' else s['tenant_id']; row=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=?',(tid,)).fetchone(); token=reveal(row['bot_token']) if row else ''; chat_id=str(row['chat_id'] if row else '').strip()
            if not token or not chat_id: return self.send_json({'error':'Önce bot tokeni ve grup Chat ID kaydedilmeli'},400)
            try:
                base=f'https://api.telegram.org/bot{token}/'; me=json.loads(urllib.request.urlopen(base+'getMe',timeout=10).read());
                if not me.get('ok'): raise ValueError()
                chat=json.loads(urllib.request.urlopen(base+'getChat?'+urllib.parse.urlencode({'chat_id':chat_id}),timeout=10).read());
                if not chat.get('ok'): raise ValueError()
                member=json.loads(urllib.request.urlopen(base+'getChatMember?'+urllib.parse.urlencode({'chat_id':chat_id,'user_id':me['result']['id']}),timeout=10).read())
                if not member.get('ok'): raise ValueError()
                role=member['result'].get('status','unknown')
                return self.send_json({'ok':True,'bot_username':me['result'].get('username',''),'chat_title':chat['result'].get('title',''),'chat_type':chat['result'].get('type',''),'bot_status':role,'can_post':role in {'administrator','creator'}})
            except Exception: return self.send_json({'error':'Bot gruba erişemiyor. Chat ID, grup üyeliği ve bot admin yetkisini kontrol edin.'},400)
        if path == '/api/admin/telegram':
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            token=str(data.get('bot_token','')).strip(); chat_id=str(data.get('chat_id','')).strip(); enabled=1 if data.get('enabled') else 0
            old=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=2').fetchone()
            if not token and old: token=reveal(old['bot_token'])
            if not token or not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}',token): return self.send_json({'error':'Geçerli Telegram bot tokeni gerekli'},400)
            if chat_id and not re.fullmatch(r'-?\d+',chat_id): return self.send_json({'error':'Chat ID yalnızca rakamlardan oluşmalı'},400)
            try:
                req=urllib.request.Request(f'https://api.telegram.org/bot{token}/getMe'); info=json.loads(urllib.request.urlopen(req,timeout=10).read())
                if not info.get('ok'): raise ValueError('Bot doğrulanamadı')
            except Exception: return self.send_json({'error':'Telegram bot tokeni doğrulanamadı'},400)
            conn.execute('INSERT INTO telegram_settings(tenant_id,bot_token,chat_id,enabled,updated_at) VALUES(2,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET bot_token=excluded.bot_token,chat_id=excluded.chat_id,enabled=excluded.enabled,updated_at=excluded.updated_at',(protect(token),chat_id,enabled,now())); conn.commit()
            return self.send_json({'configured':True,'chat_id':chat_id,'enabled':bool(enabled),'bot_username':info['result'].get('username',''),'masked':'••••'+token[-6:]})
        if path == '/api/tenant/telegram':
            tid=s['tenant_id']; token=str(data.get('bot_token','')).strip(); chat_id=str(data.get('chat_id','')).strip(); enabled=1 if data.get('enabled') else 0
            old=conn.execute('SELECT * FROM telegram_settings WHERE tenant_id=?',(tid,)).fetchone()
            if not token and old: token=reveal(old['bot_token'])
            if not token or not re.fullmatch(r'\d+:[A-Za-z0-9_-]{20,}',token): return self.send_json({'error':'Geçerli Telegram bot tokeni gerekli'},400)
            if chat_id and not re.fullmatch(r'-?\d+',chat_id): return self.send_json({'error':'Chat ID yalnızca rakamlardan oluşmalı'},400)
            try:
                req=urllib.request.Request(f'https://api.telegram.org/bot{token}/getMe'); info=json.loads(urllib.request.urlopen(req,timeout=10).read())
                if not info.get('ok'): raise ValueError('Bot doğrulanamadı')
            except Exception: return self.send_json({'error':'Telegram bot tokeni doğrulanamadı'},400)
            conn.execute('INSERT INTO telegram_settings(tenant_id,bot_token,chat_id,enabled,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET bot_token=excluded.bot_token,chat_id=excluded.chat_id,enabled=excluded.enabled,updated_at=excluded.updated_at',(tid,protect(token),chat_id,enabled,now())); conn.commit()
            return self.send_json({'configured':True,'chat_id':chat_id,'enabled':bool(enabled),'bot_username':info['result'].get('username',''),'masked':'••••'+token[-6:]})
        if path == '/api/contacts':
            tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0)); name=str(data.get('name','')).strip(); phone=str(data.get('phone','')).strip(); email=str(data.get('email','')).strip(); notes=str(data.get('notes','')).strip()
            if not tid or not name: return self.send_json({'error':'Müşteri ve kişi adı gerekli'},400)
            timestamp=now(); cur=conn.execute('INSERT INTO crm_contacts(tenant_id,name,phone,email,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(tid,name,phone,email,notes,timestamp,timestamp)); conn.commit()
            return self.send_json({'id':cur.lastrowid,'tenant_id':tid,'name':name,'phone':phone,'email':email,'notes':notes})
        if path == '/api/tenant/ai-settings':
            tid=s['tenant_id']; greeting=str(data.get('greeting','')).strip()[:1000]; voice=str(data.get('voice','alloy')).strip()[:40]; hours=str(data.get('working_hours','')).strip()[:500]
            if voice not in {'alloy','ash','ballad','coral','echo','sage','shimmer','verse'}: return self.send_json({'error':'Geçersiz ses seçimi'},400)
            conn.execute('INSERT INTO tenant_ai_settings(tenant_id,greeting,voice,working_hours,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET greeting=excluded.greeting,voice=excluded.voice,working_hours=excluded.working_hours,updated_at=excluded.updated_at',(tid,greeting,voice,hours,now())); conn.commit(); return self.send_json({'ok':True,'greeting':greeting,'voice':voice,'working_hours':hours})
        if path == '/api/knowledge':
            tid=s['tenant_id'] if s['role']!='admin' else int(data.get('tenant_id',0)); language=str(data.get('language','')).strip().lower(); title=str(data.get('title','')).strip(); content=str(data.get('content','')).strip(); status='published' if data.get('status','published')=='published' else 'draft'; doc_id=int(data.get('id') or 0)
            if not tid or language not in {'tr','en','ru'} or not title or not content: return self.send_json({'error':'Dil, başlık ve içerik zorunlu'},400)
            timestamp=now()
            if doc_id:
                existing=conn.execute('SELECT id FROM knowledge_documents WHERE id=? AND tenant_id=?',(doc_id,tid)).fetchone()
                if not existing: return self.send_json({'error':'Bilgi kaydı bulunamadı'},404)
                conn.execute('UPDATE knowledge_documents SET language=?,title=?,content=?,status=?,updated_at=? WHERE id=? AND tenant_id=?',(language,title,content,status,timestamp,doc_id,tid))
            else:
                cur=conn.execute('INSERT INTO knowledge_documents(tenant_id,language,title,content,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(tid,language,title,content,status,timestamp,timestamp)); doc_id=cur.lastrowid
            conn.commit(); return self.send_json({'id':doc_id,'tenant_id':tid,'language':language,'title':title,'status':status})
        if path.startswith('/api/admin/tenants/') and path.endswith('/sip'):
            if s['role']!='admin': return self.send_json({'error':'Yetki yok'},403)
            tid=int(path.split('/')[4]); username=str(data.get('username','')).strip(); did=str(data.get('did','')).strip() or username; domain=str(data.get('domain','')).strip(); password=str(data.get('password',''))
            if not username or not domain: return self.send_json({'error':'SIP kullanıcı adı ve domain gerekli'},400)
            if not password:
                old=conn.execute('SELECT password FROM tenant_sip WHERE tenant_id=?',(tid,)).fetchone(); password=reveal(old['password']) if old else ''
            conn.execute('INSERT INTO tenant_sip(tenant_id,username,did,domain,password,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET username=excluded.username,did=excluded.did,domain=excluded.domain,password=excluded.password,updated_at=excluded.updated_at',(tid,username,did,domain,protect(password),now())); conn.commit()
            try:
                sip_rows=conn.execute('SELECT tenant_id,username,did,domain,password FROM tenant_sip ORDER BY tenant_id').fetchall()
                entries=[{'tenant_id':x['tenant_id'],'username':x['username'],'did':x['did'],'domain':x['domain'],'password':reveal(x['password'])} for x in sip_rows if reveal(x['password'])]
                subprocess.run(['/usr/bin/sudo','/usr/local/sbin/oim-apply-sip'],input=json.dumps({'entries':entries}),text=True,capture_output=True,timeout=20,check=True)
            except Exception as exc:
                print('SIP apply error',repr(exc),flush=True)
                return self.send_json({'error':'SIP bilgisi kaydedildi ancak PBX uygulaması başarısız oldu'},502)
            return self.send_json({'tenant_id':tid,'configured':bool(password),'applied':True,'username':username,'did':did,'domain':domain,'masked':('••••'+password[-4:] if len(password)>4 else '')})
        self.send_json({'error':'Bulunamadı'},404)

if __name__ == '__main__':
    bootstrap(); threading.Thread(target=recording_watcher,daemon=True,name='telegram-recordings').start(); print(f'OIM MVP listening on {HOST}:{PORT}', flush=True); ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

