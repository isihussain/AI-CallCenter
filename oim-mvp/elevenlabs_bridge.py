"""Asterisk AudioSocket transport for the OIM ElevenLabs Scribe voice path."""

import asyncio
import base64
import json
import queue
import socket
import socketserver
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


AUDIOSOCKET_UUID = 0x01
AUDIOSOCKET_HANGUP = 0x00
AUDIOSOCKET_DTMF = 0x03
AUDIOSOCKET_PCM_8000 = 0x10
PCM_FRAME_BYTES = 320  # 20 ms of signed 16-bit mono PCM at 8 kHz.
ULAW_FRAME_BYTES = 160


def ulaw_to_pcm(frame):
    """Decode 8 kHz μ-law bytes to AudioSocket's signed little-endian PCM."""
    output = bytearray(len(frame) * 2)
    for index, value in enumerate(frame):
        value = (~value) & 0xFF
        magnitude = ((value & 0x0F) << 3) + 0x84
        magnitude <<= (value & 0x70) >> 4
        sample = 0x84 - magnitude if value & 0x80 else magnitude - 0x84
        struct.pack_into('<h', output, index * 2, sample)
    return bytes(output)


def scribe_url():
    query = urllib.parse.urlencode([
        ('model_id', 'scribe_v3_live'),
        ('audio_format', 'pcm_8000'),
        ('language_code', 'en'),
        ('commit_strategy', 'vad'),
        ('vad_silence_threshold_secs', '0.55'),
        ('secondary_languages', 'tr'),
        ('secondary_languages', 'ru'),
        ('multilang_mode', 'true'),
        ('keepalive_interval_ms', '1000'),
    ])
    return 'wss://api.elevenlabs.io/v1/speech-to-text/realtime?' + query


class AudioSocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, *, claim_call, get_credentials, get_greeting, on_turn, on_finish):
        self.claim_call = claim_call
        self.get_credentials = get_credentials
        self.get_greeting = get_greeting
        self.on_turn = on_turn
        self.on_finish = on_finish
        super().__init__(address, AudioSocketHandler)


class AudioSocketHandler(socketserver.BaseRequestHandler):
    def read_frame(self):
        header = read_exact(self.request, 3)
        if not header:
            return None
        frame_type, length = struct.unpack('!BH', header)
        payload = read_exact(self.request, length)
        if payload is None:
            raise ConnectionError('Incomplete AudioSocket frame')
        return frame_type, payload

    def handle(self):
        call_id = ''
        try:
            self.request.settimeout(1)
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            first = self.read_frame()
            if not first or first[0] != AUDIOSOCKET_UUID or len(first[1]) != 16:
                return
            import uuid
            call_id = str(uuid.UUID(bytes=first[1]))
            call = self.server.claim_call(call_id)
            if not call:
                return
            AudioSocketCall(self.request, self.server, call_id, call).run()
            self.server.on_finish(call_id, False)
        except Exception:
            if call_id:
                self.server.on_finish(call_id, True)
        finally:
            try:
                self.request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.request.close()


def read_exact(stream, length):
    data = bytearray()
    deadline = time.monotonic() + 30
    while len(data) < length:
        try:
            chunk = stream.recv(length - len(data))
        except socket.timeout:
            if time.monotonic() < deadline:
                if data:
                    continue
                raise
            return None if not data else bytes(data)
        if not chunk:
            return None if not data else bytes(data)
        data.extend(chunk)
    return bytes(data)


class AudioSocketCall:
    def __init__(self, stream, server, call_id, call):
        self.stream = stream
        self.server = server
        self.call_id = call_id
        self.call = call
        self.audio_queue = asyncio.Queue(maxsize=250)
        self.transcript_queue = asyncio.Queue()
        self.history = []
        self.cancel_speech = threading.Event()
        self.send_lock = threading.Lock()
        self.stop = asyncio.Event()

    def begin_speech(self):
        self.cancel_speech = threading.Event()
        return self.cancel_speech

    def send_audio(self, pcm):
        if not pcm:
            return
        header = struct.pack('!BH', AUDIOSOCKET_PCM_8000, len(pcm))
        with self.send_lock:
            self.stream.sendall(header + pcm)

    def say(self, text, cancel_speech):
        key, voice_id, model = self.server.get_credentials(self.call['tenant_id'])
        if not key or not voice_id:
            raise RuntimeError('ElevenLabs speech is not configured')
        url = 'https://api.elevenlabs.io/v1/text-to-speech/' + urllib.parse.quote(voice_id, safe='') + '/stream?' + urllib.parse.urlencode({'output_format': 'ulaw_8000'})
        body = json.dumps({'text': text[:4000], 'model_id': model or 'eleven_flash_v2_5'}).encode()
        request = urllib.request.Request(url, data=body, headers={
            'xi-api-key': key,
            'Content-Type': 'application/json',
            'Accept': 'audio/basic',
        }, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                try:
                    response.fp.raw._sock.settimeout(1)
                except (AttributeError, OSError):
                    pass
                pending = bytearray()
                started = time.monotonic()
                sent_frames = 0
                while not cancel_speech.is_set():
                    try:
                        chunk = response.read(ULAW_FRAME_BYTES)
                    except socket.timeout:
                        if time.monotonic() - started > 30:
                            raise RuntimeError('ElevenLabs speech stream timed out')
                        continue
                    if not chunk:
                        break
                    pending.extend(chunk)
                    while len(pending) >= ULAW_FRAME_BYTES and not cancel_speech.is_set():
                        frame = bytes(pending[:ULAW_FRAME_BYTES])
                        del pending[:ULAW_FRAME_BYTES]
                        self.send_audio(ulaw_to_pcm(frame))
                        sent_frames += 1
                        delay = started + sent_frames * 0.02 - time.monotonic()
                        if delay > 0:
                            time.sleep(delay)
                if pending and not cancel_speech.is_set():
                    self.send_audio(ulaw_to_pcm(bytes(pending)))
        except urllib.error.HTTPError as error:
            error.close()
            raise RuntimeError('ElevenLabs speech request failed') from None

    async def read_audio_socket(self):
        while not self.stop.is_set():
            try:
                packet = await asyncio.to_thread(self._read_audio_frame)
            except socket.timeout:
                continue
            if packet is None:
                self.stop.set()
                return
            frame_type, payload = packet
            if frame_type == AUDIOSOCKET_HANGUP:
                self.stop.set()
                return
            if frame_type == AUDIOSOCKET_PCM_8000 and payload:
                await self.audio_queue.put(payload)

    def _read_audio_frame(self):
        try:
            header = read_exact(self.stream, 3)
        except socket.timeout:
            raise
        if not header:
            return None
        frame_type, length = struct.unpack('!BH', header)
        payload = read_exact(self.stream, length)
        if payload is None:
            return None
        return frame_type, payload

    async def send_audio_to_scribe(self, websocket):
        while not self.stop.is_set():
            try:
                pcm = await asyncio.wait_for(self.audio_queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            chunks = [pcm]
            total = len(pcm)
            deadline = asyncio.get_running_loop().time() + 0.1
            while total < 1600:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    break
                try:
                    chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                chunks.append(chunk)
                total += len(chunk)
            await websocket.send(json.dumps({
                'message_type': 'input_audio_chunk',
                'audio_base_64': base64.b64encode(b''.join(chunks)).decode('ascii'),
            }))

    async def receive_scribe(self, websocket):
        async for raw in websocket:
            event = json.loads(raw)
            kind = event.get('message_type', '')
            if kind == 'partial_transcript' and event.get('text', '').strip():
                self.cancel_speech.set()
            elif kind == 'committed_transcript':
                transcript = str(event.get('text', '')).strip()
                if transcript:
                    await self.transcript_queue.put(transcript)
            elif kind in {'scribe_error', 'scribe_auth_error', 'scribe_quota_exceeded_error', 'scribe_throttled_error', 'scribe_rate_limited_error', 'scribe_invalid_request_error'}:
                raise RuntimeError('ElevenLabs transcription session failed')
        self.stop.set()
        raise RuntimeError('ElevenLabs transcription session closed unexpectedly')

    async def process_transcripts(self):
        while not self.stop.is_set():
            transcript = await self.transcript_queue.get()
            if not transcript:
                continue
            result = await asyncio.to_thread(self.server.on_turn, self.call_id, self.call['tenant_id'], transcript, self.history)
            answer = str((result or {}).get('text', '')).strip()
            if answer:
                await asyncio.to_thread(self.say, answer, self.begin_speech())
            if (result or {}).get('hangup'):
                try:
                    with self.send_lock:
                        self.stream.sendall(struct.pack('!BH', AUDIOSOCKET_HANGUP, 0))
                except OSError:
                    pass
                self.stop.set()
                return

    async def run_async(self):
        import websockets

        key, _, _ = self.server.get_credentials(self.call['tenant_id'])
        if not key:
            raise RuntimeError('ElevenLabs STT is not configured')
        async with websockets.connect(
            scribe_url(),
            extra_headers={'xi-api-key': key},
            ping_interval=20,
            ping_timeout=20,
            close_timeout=3,
            max_size=1024 * 1024,
        ) as websocket:
            greeting = await asyncio.wait_for(websocket.recv(), timeout=12)
            event = json.loads(greeting)
            if event.get('message_type') != 'session_started':
                raise RuntimeError('ElevenLabs did not start the transcription session')
            tasks = [
                asyncio.create_task(self.read_audio_socket()),
                asyncio.create_task(self.send_audio_to_scribe(websocket)),
                asyncio.create_task(self.receive_scribe(websocket)),
                asyncio.create_task(self.process_transcripts()),
            ]
            greeting_text = self.server.get_greeting(self.call['tenant_id'])
            watchers = [tasks[0], tasks[2], tasks[3]]
            greeting_task = asyncio.create_task(asyncio.to_thread(self.say, greeting_text, self.begin_speech())) if greeting_text else None
            if greeting_task:
                watchers.append(greeting_task)
            try:
                while True:
                    done, _ = await asyncio.wait(watchers, return_when=asyncio.FIRST_COMPLETED)
                    if greeting_task in done:
                        exception = greeting_task.exception()
                        if exception:
                            raise exception
                        watchers.remove(greeting_task)
                        done.discard(greeting_task)
                        greeting_task = None
                    if not done:
                        continue
                    for task in done:
                        exception = task.exception()
                        if exception:
                            raise exception
                    break
            finally:
                self.stop.set()
                try:
                    await websocket.close()
                except Exception:
                    pass
                for task in set(tasks + ([greeting_task] if greeting_task else [])):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks + ([greeting_task] if greeting_task else []), return_exceptions=True)

    def run(self):
        asyncio.run(self.run_async())


def start_audiosocket_bridge(host, port, **callbacks):
    server = AudioSocketServer((host, port), **callbacks)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name='oim-audiosocket')
    thread.start()
    return server
