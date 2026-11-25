"""ElevenLabs API helpers and outbound-tool safety checks for OIM."""

import http.client
import ipaddress
import base64
import hashlib
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone


API_BASE = "https://api.elevenlabs.io"
MAX_PROVIDER_RESPONSE = 8 * 1024 * 1024
MAX_TOOL_RESPONSE = 1024 * 1024


class ProviderError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def provider_request(api_key, method, path, payload=None, query=None, timeout=25):
    if not api_key:
        raise ProviderError(503, "ElevenLabs API key is not configured.")
    if not isinstance(path, str) or not path.startswith("/v1/") and not path.startswith("/v2/"):
        raise ValueError("Unsupported ElevenLabs API path.")
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"xi-api-key": api_key, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_PROVIDER_RESPONSE + 1)
            if len(raw) > MAX_PROVIDER_RESPONSE:
                raise ProviderError(502, "ElevenLabs response exceeded the size limit.")
            if not raw:
                return {}
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {"content_type": response.headers.get("Content-Type", ""), "size": len(raw)}
    except urllib.error.HTTPError as error:
        try:
            error.close()
        except Exception:
            pass
        if error.code == 402:
            message = "ElevenLabs requires available credits or payment for this speech request."
        elif error.code == 403:
            message = "ElevenLabs denied this request. Check API-key permissions and plan access."
        elif error.code >= 500:
            message = "ElevenLabs is temporarily unavailable."
        else:
            message = f"ElevenLabs rejected the request (HTTP {error.code}). Check the resource configuration."
        raise ProviderError(502 if error.code >= 500 else 400, message) from None
    except (TimeoutError, OSError, urllib.error.URLError):
        raise ProviderError(502, "ElevenLabs could not be reached.") from None


def provider_upload(api_key, filename, content_type, file_bytes, name=""):
    if not api_key:
        raise ProviderError(503, "ElevenLabs API key is not configured.")
    if len(file_bytes) > 20 * 1024 * 1024:
        raise ValueError("Knowledge files must be 20 MiB or smaller.")
    boundary = "oim-" + uuid.uuid4().hex
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", str(filename))[:180] or "knowledge-file"
    parts = []
    if not re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", str(content_type or "")):
        content_type = "application/octet-stream"
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{safe_name}\"\r\nContent-Type: {content_type}\r\n\r\n").encode("ascii"))
    parts.append(file_bytes)
    parts.append(b"\r\n")
    if name:
        parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n{name[:200]}\r\n").encode("utf-8"))
    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    request = urllib.request.Request(
        API_BASE + "/v1/convai/knowledge-base/file",
        data=b"".join(parts),
        headers={"xi-api-key": api_key, "Accept": "application/json", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read(MAX_PROVIDER_RESPONSE + 1)
            if len(raw) > MAX_PROVIDER_RESPONSE:
                raise ProviderError(502, "ElevenLabs response exceeded the size limit.")
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        message = "ElevenLabs is temporarily unavailable." if code >= 500 else f"ElevenLabs rejected the file (HTTP {code}). Check its format, size and API-key permissions."
        raise ProviderError(502 if code >= 500 else 400, message) from None
    except (TimeoutError, OSError, urllib.error.URLError):
        raise ProviderError(502, "ElevenLabs could not be reached.") from None


def _resolve_public_https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Tool URL must be a valid public HTTPS URL.")
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Tool URL must use HTTPS and must not include credentials.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        raise ValueError("Private and local network destinations are not allowed.")
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            addresses = list({ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)})
        except (OSError, ValueError):
            raise ValueError("Tool host could not be resolved safely.") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Private and reserved network addresses are not allowed.")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, "")), addresses


def validate_public_https_url(value):
    """Reject non-public destinations before sending an outbound tool request."""
    return _resolve_public_https_url(value)[0]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def test_webhook(url, method="POST", headers=None, body=None, timeout=10):
    safe_url, candidates = _resolve_public_https_url(url)
    parsed = urllib.parse.urlsplit(safe_url)
    host = parsed.hostname.rstrip(".").lower()
    port = parsed.port or 443
    method = str(method or "POST").upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("Unsupported HTTP method.")
    if not isinstance(headers, dict) or len(headers) > 20:
        raise ValueError("Tool headers must be a JSON object with at most 20 entries.")
    safe_headers = {}
    for key, value in headers.items():
        key, value = str(key), str(value)
        if not key or len(key) > 100 or len(value) > 2048 or "\r" in key + value or "\n" in key + value:
            raise ValueError("A tool header is invalid.")
        if key.lower() in {"host", "connection", "content-length", "transfer-encoding"}:
            raise ValueError("This HTTP header cannot be overridden.")
        safe_headers[key] = value
    if body is not None and len(json.dumps(body, ensure_ascii=False).encode("utf-8")) > 64 * 1024:
        raise ValueError("Tool request body exceeds 64 KiB.")
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    if encoded is not None:
        safe_headers.setdefault("Content-Type", "application/json")
    started = time.monotonic()
    response = None
    connection = None
    try:
        # Pin the TLS socket to an address already checked above. urllib's normal
        # opener would resolve the name a second time and allow DNS rebinding.
        context = ssl.create_default_context()
        last_error = None
        for address in candidates:
            try:
                raw_socket = socket.create_connection((str(address), port), timeout=max(1, min(int(timeout), 20)))
                tls_socket = context.wrap_socket(raw_socket, server_hostname=host)
                connection = http.client.HTTPSConnection(host, port, timeout=max(1, min(int(timeout), 20)), context=context)
                connection.sock = tls_socket
                break
            except (OSError, ssl.SSLError) as error:
                last_error = error
        if connection is None:
            raise OSError("Could not connect to validated host.") from last_error
        target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        connection.request(method, target, body=encoded, headers=safe_headers)
        response = connection.getresponse()
        status = response.status
        raw = response.read(MAX_TOOL_RESPONSE + 1)
        content_type = response.headers.get("Content-Type", "")
    except (OSError, ssl.SSLError, http.client.HTTPException):
        raise ValueError("Tool endpoint could not be reached. Redirects are blocked.") from None
    finally:
        if response:
            response.close()
        if connection:
            connection.close()
    elapsed_ms = round((time.monotonic() - started) * 1000)
    if len(raw) > MAX_TOOL_RESPONSE:
        raise ValueError("Tool response exceeded the 1 MiB limit.")
    excerpt = raw[:4096].decode("utf-8", "replace")
    try:
        parsed = json.loads(excerpt)
        secret_terms = ("token", "secret", "password", "authorization", "api_key", "credential", "cookie")
        def redact(value):
            if isinstance(value, dict):
                return {key: "[redacted]" if any(secret in str(key).lower() for secret in secret_terms) else redact(item) for key, item in value.items()}
            if isinstance(value, list):
                return [redact(item) for item in value]
            return value
        parsed = redact(parsed)
        excerpt = json.dumps(parsed, ensure_ascii=False)
    except (ValueError, TypeError):
        pass
    return {"status": status, "elapsed_ms": elapsed_ms, "content_type": content_type, "body_preview": excerpt[:2000]}


def verify_webhook_signature(raw_body, signature, secret, current_time=None):
    import hashlib
    import hmac

    parts = {}
    for item in str(signature or "").split(","):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            parts[key] = value
    timestamp = parts.get("t", "")
    signed = parts.get("v0", "")
    try:
        issued = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = int(time.time() if current_time is None else current_time)
    if not secret or not signed or abs(current - issued) > 1800:
        return False
    expected = hmac.new(secret.encode("utf-8"), timestamp.encode("ascii") + b"." + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signed)


def agent_payload(value):
    if not isinstance(value, dict) or not isinstance(value.get("conversation_config"), dict):
        raise ValueError("Agent configuration must include conversation_config as an object.")
    # Preserve the full provider-shaped config in local drafts. The provider
    # remains the authority on whether a field is writable in the current API.
    result = dict(value)
    if "name" in result and (not isinstance(result["name"], str) or not result["name"].strip() or len(result["name"]) > 200):
        raise ValueError("Agent name must contain 1 to 200 characters.")
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 512 * 1024:
        raise ValueError("Agent configuration exceeds 512 KiB.")
    return result


def _safe_id(value):
    value = urllib.parse.unquote(str(value or ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid provider resource ID.")
    return urllib.parse.quote(value, safe="")


def _check_scribe_live(api_key):
    try:
        import asyncio
        import websockets
        from elevenlabs_bridge import scribe_url

        async def check_scribe():
            async with websockets.connect(
                scribe_url(),
                extra_headers={"xi-api-key": api_key},
                ping_interval=None,
                close_timeout=2,
                max_size=1024 * 1024,
            ) as websocket:
                event = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
                if event.get("message_type") != "session_started":
                    raise ValueError("ElevenLabs Scribe session did not start.")

        asyncio.run(check_scribe())
    except ValueError:
        raise
    except Exception:
        raise ProviderError(400, "ElevenLabs Scribe access failed. Check the real-time speech-to-text permission on the API key.") from None


def check_phone_capabilities(api_key, voice_id, model="eleven_flash_v2_5"):
    """Check the exact ElevenLabs capabilities used by the OIM phone bridge."""
    if not voice_id:
        raise ValueError("Save an ElevenLabs Voice ID before checking the phone bridge.")
    _check_scribe_live(api_key)

    model = str(model or "eleven_flash_v2_5").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", model):
        raise ValueError("Invalid ElevenLabs TTS model.")
    response = provider_request(
        api_key,
        "POST",
        "/v1/text-to-speech/" + _safe_id(voice_id) + "/stream",
        {"text": "Hello.", "model_id": model},
        query={"output_format": "ulaw_8000"},
    )
    if not isinstance(response, dict) or not response.get("size"):
        raise ProviderError(502, "ElevenLabs did not return speech audio for the selected voice.")
    return {"scribe": True, "speech": True}


def _remote_config(agent):
    return {key: agent[key] for key in ("conversation_config", "platform_settings", "workflow", "name", "tags", "procedures") if key in agent}


def _cache(conn, kind, item_id, name, remote, protect, tenant_id=None, local=None):
    raw = json.dumps(remote, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    remote_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT INTO voice_platform_items(kind,item_id,name,tenant_id,remote_hash,remote_config,local_config,updated_at) VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(kind,item_id) DO UPDATE SET name=excluded.name,tenant_id=COALESCE(excluded.tenant_id,voice_platform_items.tenant_id),remote_hash=excluded.remote_hash,remote_config=excluded.remote_config,local_config=CASE WHEN excluded.local_config='' THEN voice_platform_items.local_config ELSE excluded.local_config END,updated_at=excluded.updated_at",
        (kind, item_id, str(name or "")[:200], tenant_id, remote_hash, protect(raw), protect(json.dumps(local, ensure_ascii=False, sort_keys=True)) if local is not None else "", int(time.time())),
    )
    conn.commit()
    return remote_hash


def _event(conn, action, status, message):
    conn.execute("INSERT INTO voice_platform_events(action,status,message,created_at) VALUES(?,?,?,?)", (str(action)[:100], str(status)[:40], str(message)[:300], int(time.time())))
    conn.commit()


def _items_payload(conn, kind):
    return [dict(row) for row in conn.execute("SELECT item_id,name,tenant_id,remote_hash,updated_at FROM voice_platform_items WHERE kind=? ORDER BY name COLLATE NOCASE", (kind,)).fetchall()]


def get_route(path, query, conn, api_key, reveal, calendar_check=None):
    """Return (status, response) for an authenticated OIM admin GET route."""
    if path == "/api/admin/voice-platform/status":
        row = conn.execute("SELECT enabled,check_status,checked_at,api_key FROM provider_settings WHERE provider='elevenlabs'").fetchone()
        key = reveal(row["api_key"]) if row else ""
        return 200, {"configured": bool(key), "enabled": bool(row["enabled"]) if row else False, "masked": "••••••••" if key else "", "check_status": row["check_status"] if row else "unchecked", "checked_at": row["checked_at"] if row else None, "webhook_configured": bool(__import__("os").environ.get("ELEVENLABS_WEBHOOK_SECRET", "").strip() or conn.execute("SELECT 1 FROM system_settings WHERE key='elevenlabs_webhook_secret' AND value<>''").fetchone()), "public_webhook_url": __import__("os").environ.get("OIM_PUBLIC_URL", "").rstrip("/") + "/api/webhooks/elevenlabs"}
    if path == "/api/admin/voice-platform/events":
        rows = conn.execute("SELECT action,status,message,created_at FROM voice_platform_events ORDER BY id DESC LIMIT 100").fetchall()
        return 200, {"items": [dict(row) for row in rows]}
    calendar_root = "/api/admin/voice-platform/calendar"
    if path == calendar_root or path.startswith(calendar_root + "/"):
        from calendar_engine import DEFAULTS, alternatives, available_slots, availability, settings_for
        try:
            tenant_id = int((query.get("tenant_id") or [0])[0])
        except (TypeError, ValueError):
            return 400, {"error": "Select a customer before loading calendar settings."}
        if tenant_id < 1 or not conn.execute("SELECT 1 FROM tenants WHERE id=? AND role='customer'", (tenant_id,)).fetchone():
            return 400, {"error": "Select a valid customer."}
        config = settings_for(conn, tenant_id)
        if path.endswith("/appointments"):
            from datetime import date, timedelta
            from zoneinfo import ZoneInfo
            try:
                selected = date.fromisoformat((query.get("date") or [""])[0])
                view = (query.get("view") or ["day"])[0]
                if view not in {"day", "week", "month"}:
                    raise ValueError()
            except (TypeError, ValueError):
                return 400, {"error": "Choose a valid calendar date and day, week or month view."}
            if view == "week":
                period_start = selected - timedelta(days=selected.weekday())
                period_end = period_start + timedelta(days=7)
            elif view == "month":
                period_start = selected.replace(day=1)
                period_end = period_start.replace(year=period_start.year + (period_start.month == 12), month=1 if period_start.month == 12 else period_start.month + 1)
            else:
                period_start, period_end = selected, selected + timedelta(days=1)
            rows = conn.execute("SELECT id,customer_name,service,department,appointment_at,status,duration_minutes,staff_id,calendar_provider,recurrence_series_id,recurrence_index FROM appointments WHERE tenant_id=? AND substr(appointment_at,1,10)>=? AND substr(appointment_at,1,10)<? ORDER BY appointment_at LIMIT 500", (tenant_id, period_start.isoformat(), period_end.isoformat())).fetchall()
            return 200, {"tenant_id": tenant_id, "view": view, "timezone": config["timezone"], "start_date": period_start.isoformat(), "end_date": period_end.isoformat(), "items": [dict(row) for row in rows]}
        if path.endswith("/availability"):
            try:
                return 200, availability(conn, tenant_id, (query.get("start") or [""])[0], (query.get("duration_minutes") or [None])[0], (query.get("staff_id") or [None])[0], (lambda start, duration, exclude=None, provider=None: calendar_check(tenant_id, start, duration, exclude, provider)) if calendar_check else None, service=(query.get("service") or [""])[0], department=(query.get("department") or [""])[0])
            except (TypeError, ValueError) as error:
                return 400, {"error": str(error)}
        if path.endswith("/slots"):
            try:
                return 200, available_slots(conn, tenant_id, (query.get("date") or [""])[0], (query.get("duration_minutes") or [None])[0], (query.get("staff_id") or [None])[0], external_check=(lambda start, duration, exclude=None, provider=None: calendar_check(tenant_id, start, duration, exclude, provider)) if calendar_check else None, service=(query.get("service") or [""])[0], department=(query.get("department") or [""])[0])
            except (TypeError, ValueError) as error:
                return 400, {"error": str(error)}
        if path.endswith("/alternatives"):
            try:
                return 200, alternatives(conn, tenant_id, (query.get("start") or [""])[0], (query.get("duration_minutes") or [None])[0], (query.get("staff_id") or [None])[0], (lambda start, duration, exclude=None, provider=None: calendar_check(tenant_id, start, duration, exclude, provider)) if calendar_check else None, (query.get("service") or [""])[0], (query.get("department") or [""])[0])
            except (TypeError, ValueError) as error:
                return 400, {"error": str(error)}
        return 200, {"tenant_id": tenant_id, "settings": config}

    imported_prefix = "/api/admin/voice-platform/imported-conversations"
    if path == imported_prefix:
        try:
            tenant_id = int((query.get("tenant_id") or [0])[0])
        except (TypeError, ValueError):
            return 400, {"error": "Select a customer first."}
        if tenant_id < 1:
            return 400, {"error": "Select a customer first."}
        rows = conn.execute("SELECT conversation_id,agent_id,started_at,duration_seconds,status,language,summary,cost_credits,updated_at FROM elevenlabs_conversations WHERE tenant_id=? ORDER BY started_at DESC LIMIT 200", (tenant_id,)).fetchall()
        return 200, {"items": [{**dict(row), "summary": reveal(row["summary"]) if row["summary"] else ""} for row in rows]}
    if path.startswith(imported_prefix + "/"):
        conversation_id = path[len(imported_prefix) + 1:]
        row = conn.execute("SELECT * FROM elevenlabs_conversations WHERE conversation_id=?", (conversation_id,)).fetchone()
        if not row:
            return 404, {"error": "Imported conversation not found."}
        transcript = []
        if row["transcript_encrypted"]:
            try:
                transcript = json.loads(reveal(row["transcript_encrypted"]))
            except (ValueError, TypeError):
                return 500, {"error": "Stored transcript could not be decrypted."}
        return 200, {"conversation": {**dict(row), "summary": reveal(row["summary"]) if row["summary"] else "", "transcript": transcript}}

    prefix = "/api/admin/voice-platform/"
    if not path.startswith(prefix):
        return None
    resource = path[len(prefix):].strip("/").split("/")
    if not api_key:
        return 503, {"error": "Save an ElevenLabs API key in Integrations first."}
    try:
        if resource[0] == "agents":
            if len(resource) == 1:
                params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "search", "tags") if (query.get(name) or [None])[0] is not None}
                params.setdefault("page_size", 100)
                result = provider_request(api_key, "GET", "/v1/convai/agents", query=params)
                items = result.get("agents", []) if isinstance(result, dict) else []
                for item in items:
                    cached = conn.execute("SELECT tenant_id,remote_hash,updated_at FROM voice_platform_items WHERE kind='agent' AND item_id=?", (item.get("agent_id", ""),)).fetchone()
                    if cached:
                        item["oim_tenant_id"] = cached["tenant_id"]
                        item["oim_synced_at"] = cached["updated_at"]
                        item["oim_sync_status"] = "synced" if cached["remote_hash"] == hashlib.sha256(json.dumps(_remote_config(item), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest() else "pending_changes"
                return 200, result
            agent_id = _safe_id(resource[1])
            if len(resource) == 3 and resource[2] == "branches":
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id + "/branches")
            if len(resource) == 5 and resource[2] == "branches" and resource[4] == "merge-preview":
                target = (query.get("target_branch_id") or [""])[0]
                if not target:
                    return 400, {"error": "target_branch_id is required."}
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id + "/branches/" + _safe_id(resource[3]) + "/merge-preview", query={"target_branch_id": target})
            if len(resource) == 4 and resource[2] == "branches":
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id + "/branches/" + _safe_id(resource[3]))
            if len(resource) == 3 and resource[2] == "deployments":
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id + "/deployments")
            if len(resource) == 3 and resource[2] == "versions":
                version_id = (query.get("version_id") or [""])[0]
                if not version_id:
                    return 400, {"error": "version_id is required."}
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id + "/versions/" + _safe_id(version_id))
            if len(resource) == 2:
                return 200, provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id, query={name: (query.get(name) or [None])[0] for name in ("branch_id", "version_id", "include_draft") if (query.get(name) or [None])[0] is not None})
            if resource[2] == "local" and len(resource) == 3:
                row = conn.execute("SELECT remote_hash,remote_config,local_config,tenant_id,updated_at FROM voice_platform_items WHERE kind='agent' AND item_id=?", (urllib.parse.unquote(agent_id),)).fetchone()
                if not row:
                    return 404, {"error": "Agent has not been imported into OIM."}
                try:
                    remote = json.loads(reveal(row["remote_config"]))
                    local = json.loads(reveal(row["local_config"])) if row["local_config"] else remote
                except (ValueError, TypeError):
                    return 500, {"error": "Saved agent configuration could not be decrypted."}
                return 200, {"remote_hash": row["remote_hash"], "remote": remote, "local": local, "tenant_id": row["tenant_id"], "updated_at": row["updated_at"]}
        if resource[0] == "conversation-signed-url" and len(resource) == 1:
            agent_id = (query.get("agent_id") or [""])[0]
            if not agent_id:
                return 400, {"error": "An agent ID is required."}
            result = provider_request(api_key, "GET", "/v1/convai/conversation/get-signed-url", query={"agent_id": _safe_id(agent_id)}, timeout=15)
            signed_url = result.get("signed_url") if isinstance(result, dict) else None
            if not isinstance(signed_url, str) or not signed_url.startswith("wss://api.elevenlabs.io/") or len(signed_url) > 4096:
                return 502, {"error": "ElevenLabs did not return a valid conversation URL."}
            return 200, {"signed_url": signed_url, "expires_in_seconds": 900}
        if resource[0] == "tools" and len(resource) == 1:
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "search") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/tools", query=params)
        if resource[0] == "tools" and len(resource) == 3 and resource[2] == "executions":
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "agent_id", "branch_id", "start_time", "end_time", "is_error") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/tools/" + _safe_id(resource[1]) + "/executions", query=params)
        if resource[0] == "tools" and len(resource) == 3 and resource[2] == "dependent-agents":
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/tools/" + _safe_id(resource[1]) + "/dependent-agents", query=params)
        if resource[0] == "voices":
            params = {name: (query.get(name) or [None])[0] for name in ("next_page_token", "page_size", "search", "category", "gender", "language") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v2/voices", query=params)
        if resource[0] == "models":
            return 200, provider_request(api_key, "GET", "/v1/models")
        if resource[0] == "llms":
            return 200, provider_request(api_key, "GET", "/v1/convai/llm/list")
        if resource[0] == "knowledge" and len(resource) == 1:
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "search", "types") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/knowledge-base", query=params)
        if resource[0] == "knowledge" and len(resource) == 3 and resource[2] == "dependent-agents":
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "dependent_type") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            params.setdefault("dependent_type", "all")
            return 200, provider_request(api_key, "GET", "/v1/convai/knowledge-base/" + _safe_id(resource[1]) + "/dependent-agents", query=params)
        if resource[0] == "conversations" and len(resource) == 1:
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "agent_id", "status", "call_start_before_unix", "call_start_after_unix") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/conversations", query=params)
        if resource[0] == "conversations" and len(resource) == 2:
            return 200, provider_request(api_key, "GET", "/v1/convai/conversations/" + _safe_id(resource[1]))
        if resource[0] == "analytics":
            user = subscription = usage = None
            errors = []
            for endpoint, key in (("/v1/user", "user"), ("/v1/user/subscription", "subscription")):
                try:
                    value = provider_request(api_key, "GET", endpoint)
                    if key == "user": user = value
                    else: subscription = value
                except ProviderError as error:
                    errors.append({"resource": key, "message": str(error)})
            end = datetime.now(timezone.utc)
            start = datetime(end.year, end.month, 1, tzinfo=timezone.utc)
            body = {"start_time": int(start.timestamp() * 1000), "end_time": int(end.timestamp() * 1000), "interval_seconds": 86400, "time_zone": "Europe/Istanbul"}
            try:
                usage = provider_request(api_key, "POST", "/v1/workspace/analytics/query/usage-by-product-over-time", body)
            except ProviderError as credit_error:
                try:
                    usage = provider_request(api_key, "POST", "/v1/workspace/analytics/usage", {**body, "interval_seconds": 86400})
                except ProviderError as cost_error:
                    errors.append({"resource": "usage", "message": str(cost_error if cost_error.status != 404 else credit_error)})
            return 200, {"user": user, "subscription": subscription, "usage": usage, "unavailable": errors}
        if resource[0] == "tests" and len(resource) == 1:
            params = {name: (query.get(name) or [None])[0] for name in ("cursor", "page_size", "agent_id", "search") if (query.get(name) or [None])[0] is not None}
            params.setdefault("page_size", 100)
            return 200, provider_request(api_key, "GET", "/v1/convai/agent-testing", query=params)
    except ProviderError as error:
        _event(conn, "provider_read", "failed", str(error))
        return error.status, {"error": str(error)}
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return 400, {"error": str(error) or "Invalid request."}
    return 404, {"error": "Voice platform route not found."}


def process_post_call_webhook(raw_body, signature, secret, conn, protect, current_time=None):
    if len(raw_body) > 2 * 1024 * 1024:
        return 413, {"error": "Webhook payload is too large."}
    if not verify_webhook_signature(raw_body, signature, secret, current_time):
        return 401, {"error": "Invalid webhook signature."}
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"error": "Invalid webhook JSON."}
    if not isinstance(event, dict) or event.get("type") != "post_call_transcription":
        return 200, {"ok": True, "ignored": True}
    data = event.get("data") or {}
    if not isinstance(data, dict):
        return 400, {"error": "Invalid post-call event."}
    conversation_id = str(data.get("conversation_id") or "").strip()
    agent_id = str(data.get("agent_id") or "").strip()
    event_timestamp = str(event.get("event_timestamp") or "")
    if not conversation_id or len(conversation_id) > 200 or not agent_id or len(agent_id) > 200:
        return 400, {"error": "Conversation and agent IDs are required."}
    owner = conn.execute("SELECT tenant_id FROM voice_platform_items WHERE kind='agent' AND item_id=?", (agent_id,)).fetchone()
    if not owner or not owner["tenant_id"]:
        return 202, {"ok": True, "ignored": True, "reason": "Agent has no OIM customer assignment."}
    tenant_id = int(owner["tenant_id"])
    event_key = "post_call_transcription:" + conversation_id + ":" + event_timestamp
    conn.execute("BEGIN IMMEDIATE")
    try:
        inserted = conn.execute("INSERT OR IGNORE INTO elevenlabs_webhook_events(event_key,event_type,received_at) VALUES(?,?,?)", (event_key, "post_call_transcription", int(time.time()))).rowcount
        if not inserted:
            conn.commit()
            return 200, {"ok": True, "duplicate": True}
        transcript = []
        for item in data.get("transcript") or []:
            if not isinstance(item, dict):
                continue
            message = str(item.get("message") or "")[:4000]
            if message:
                transcript.append({"role": str(item.get("role") or "")[:40], "message": message, "time_in_call_secs": item.get("time_in_call_secs")})
        analysis = data.get("analysis") or {}
        summary = str(analysis.get("transcript_summary") or "")[:12000] if isinstance(analysis, dict) else ""
        metadata = data.get("metadata") or {}
        try:
            started_at = int((metadata.get("start_time_unix_secs") if isinstance(metadata, dict) else 0) or event_timestamp or 0)
        except (TypeError, ValueError):
            started_at = 0
        try:
            duration = max(0, int((metadata.get("call_duration_secs") if isinstance(metadata, dict) else 0) or 0))
        except (TypeError, ValueError):
            duration = 0
        try:
            cost = max(0, int((metadata.get("cost") if isinstance(metadata, dict) else 0) or 0))
        except (TypeError, ValueError):
            cost = None
        initiation = data.get("conversation_initiation_client_data") or {}
        override = initiation.get("conversation_config_override") or {} if isinstance(initiation, dict) else {}
        agent_override = override.get("agent") or {} if isinstance(override, dict) else {}
        language = str(agent_override.get("language") or "")[:20] if isinstance(agent_override, dict) else ""
        conn.execute("INSERT INTO elevenlabs_conversations(conversation_id,tenant_id,agent_id,started_at,duration_seconds,status,language,summary,transcript_encrypted,cost_credits,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET tenant_id=excluded.tenant_id,agent_id=excluded.agent_id,started_at=excluded.started_at,duration_seconds=excluded.duration_seconds,status=excluded.status,language=excluded.language,summary=excluded.summary,transcript_encrypted=excluded.transcript_encrypted,cost_credits=excluded.cost_credits,updated_at=excluded.updated_at", (conversation_id, tenant_id, agent_id, started_at, duration, str(data.get("status") or "done")[:40], language, protect(summary), protect(json.dumps(transcript, ensure_ascii=False)), cost, int(time.time())))
        conn.commit()
        return 200, {"ok": True, "imported": True, "conversation_id": conversation_id}
    except Exception:
        conn.rollback()
        raise


CALENDAR_TOOL_FIELDS = {
    "get_current_datetime": ({}, []),
    "check_availability": ({"appointment_at": {"type": "string", "description": "Exact ISO 8601 time or an unambiguous English, Turkish or Russian date and time in the tenant's calendar timezone. Ask the caller to clarify when a date or time is ambiguous."}, "duration_minutes": {"type": "integer"}, "staff_id": {"type": "string"}, "service": {"type": "string"}, "department": {"type": "string"}}, ["appointment_at"]),
    "get_available_slots": ({"date": {"type": "string", "description": "Date, weekday, tomorrow, this week, next month's first week or earliest available in English, Turkish or Russian"}, "duration_minutes": {"type": "integer"}, "staff_id": {"type": "string"}, "service": {"type": "string"}, "department": {"type": "string"}}, ["date"]),
    "find_alternative_slots": ({"appointment_at": {"type": "string", "description": "Requested ISO 8601 time or unambiguous natural-language date and time in the tenant's timezone"}, "duration_minutes": {"type": "integer"}, "staff_id": {"type": "string"}, "service": {"type": "string"}, "department": {"type": "string"}}, ["appointment_at"]),
    "book_appointment": ({"customer_name": {"type": "string"}, "phone": {"type": "string"}, "service": {"type": "string"}, "appointment_at": {"type": "string", "description": "Exact ISO 8601 time or unambiguous natural-language date and time in the tenant's timezone; do not book when clarification is needed"}, "notes": {"type": "string"}, "duration_minutes": {"type": "integer"}, "staff_id": {"type": "string"}, "department": {"type": "string"}, "recurrence": {"type": "object", "properties": {"frequency": {"type": "string", "enum": ["daily", "weekly"]}, "interval": {"type": "integer", "minimum": 1, "maximum": 4}, "count": {"type": "integer", "minimum": 2, "maximum": 52}}, "required": ["frequency", "count"], "additionalProperties": False}}, ["customer_name", "phone", "service", "appointment_at"]),
    "find_appointment": ({"phone": {"type": "string"}, "appointment_id": {"type": "integer"}}, ["phone"]),
    "reschedule_appointment": ({"phone": {"type": "string"}, "appointment_id": {"type": "integer"}, "appointment_at": {"type": "string", "description": "Exact ISO 8601 time or unambiguous natural-language date and time in the tenant's timezone"}}, ["phone", "appointment_at"]),
    "cancel_appointment": ({"phone": {"type": "string"}, "appointment_id": {"type": "integer"}}, ["phone"]),
    "get_business_hours": ({}, []),
    "get_staff_availability": ({"date": {"type": "string"}, "staff_id": {"type": "string"}, "duration_minutes": {"type": "integer"}}, ["date", "staff_id"]),
}


def provision_calendar_tools(conn, api_key, protect, reveal, public_url, tenant_id, agent_id=None):
    try:
        tenant_id = int(tenant_id)
    except (TypeError, ValueError):
        return 400, {"error": "Select a valid OIM customer."}
    if tenant_id < 1 or not conn.execute("SELECT 1 FROM tenants WHERE id=? AND role='customer'", (tenant_id,)).fetchone():
        return 400, {"error": "Select a valid OIM customer."}
    root = str(public_url or "").rstrip("/")
    try:
        root = validate_public_https_url(root).rstrip("/")
    except ValueError:
        return 400, {"error": "Set OIM_PUBLIC_URL to a public HTTPS URL before provisioning calendar tools."}
    existing = conn.execute("SELECT token_hash,token_cipher FROM oim_calendar_tool_tokens WHERE tenant_id=? AND enabled=1 ORDER BY created_at DESC LIMIT 1", (tenant_id,)).fetchone()
    if existing and existing["token_cipher"]:
        token = reveal(existing["token_cipher"])
        token_hash = existing["token_hash"]
    else:
        import secrets
        token = secrets.token_urlsafe(40)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        conn.execute("INSERT INTO oim_calendar_tool_tokens(token_hash,tenant_id,enabled,created_at,token_cipher) VALUES(?,?,1,?,?)", (token_hash, tenant_id, int(time.time()), protect(token)))
        conn.commit()
    result = []
    errors = []
    for operation, (properties, required) in CALENDAR_TOOL_FIELDS.items():
        name = f"oim_t{tenant_id}_{operation}"
        schema = {"type": "object", "properties": properties, "required": required, "additionalProperties": False}
        cached = conn.execute("SELECT item_id FROM voice_platform_items WHERE kind='tool' AND tenant_id=? AND name=? ORDER BY updated_at DESC LIMIT 1", (tenant_id, name)).fetchone()
        if cached:
            result.append({"name": name, "id": cached["item_id"], "operation": operation, "existing": True})
            continue
        tool = {
            "type": "webhook", "name": name,
            "description": f"Tenant-scoped OIM calendar operation: {operation}. Respond with structured data; do not reveal other customers' information.",
            "response_timeout_secs": 20,
            "api_schema": {"url": root + "/api/webhooks/oim-calendar/" + operation, "method": "POST", "request_headers": {"Authorization": "Bearer " + token, "X-OIM-Conversation-ID": "{{system__conversation_id}}"}, "request_body_schema": schema},
        }
        try:
            created = provider_request(api_key, "POST", "/v1/convai/tools", {"tool_config": tool})
            tool_id = str(created.get("id", ""))
            if not tool_id:
                raise ProviderError(502, "ElevenLabs did not return a tool ID.")
            _cache(conn, "tool", tool_id, name, created.get("tool_config", tool), protect, tenant_id, tool)
            result.append({"name": name, "id": tool_id, "operation": operation})
        except ProviderError as error:
            errors.append({"operation": operation, "message": str(error)})
    if agent_id and result:
        safe_agent_id = _safe_id(agent_id)
        current = provider_request(api_key, "GET", "/v1/convai/agents/" + safe_agent_id)
        config = _remote_config(current)
        prompt = config.setdefault("conversation_config", {}).setdefault("agent", {}).setdefault("prompt", {})
        current_ids = prompt.get("tool_ids") or []
        prompt["tool_ids"] = list(dict.fromkeys([*current_ids, *[item["id"] for item in result]]))
        provider_request(api_key, "PATCH", "/v1/convai/agents/" + safe_agent_id, agent_payload(config))
        _cache(conn, "agent", urllib.parse.unquote(safe_agent_id), current.get("name", ""), config, protect, tenant_id, config)
    _event(conn, "calendar_tools_provision", "partial" if errors else "ok", f"Provisioned {len(result)} calendar tools; {len(errors)} failed.")
    return (207 if errors else 201), {"ok": not errors, "tenant_id": tenant_id, "tools": result, "errors": errors, "agent_id": agent_id or None}


def dispatch_calendar_tool(operation, raw_body, authorization, conn, reveal, current_time=None, reserve_calendar=None, check_calendar=None, modify_calendar=None, conversation_id=""):
    import calendar_engine
    import hashlib
    import hmac
    import os
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if operation not in CALENDAR_TOOL_FIELDS:
        return 404, {"error": "Unknown calendar operation."}
    if len(raw_body) > 64 * 1024:
        return 413, {"error": "Calendar tool request is too large."}
    supplied = str(authorization or "")
    if not supplied.startswith("Bearer ") or len(supplied) > 256:
        return 401, {"error": "Calendar tool authorization required."}
    token = supplied[7:]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = conn.execute("SELECT tenant_id FROM oim_calendar_tool_tokens WHERE token_hash=? AND enabled=1", (token_hash,)).fetchone()
    if not row:
        return 401, {"error": "Calendar tool authorization failed."}
    try:
        values = json.loads(raw_body.decode("utf-8"))
        if not isinstance(values, dict):
            raise ValueError("JSON object required.")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return 400, {"error": "Invalid calendar tool request."}
    tenant_id = row["tenant_id"]
    def checked_calendar(start, duration, exclude=None, provider=None):
        if not check_calendar:
            return None
        try:
            return check_calendar(tenant_id, start, duration, exclude, provider)
        except TypeError:
            return check_calendar(tenant_id, start, duration, exclude)
    try:
        config = calendar_engine.settings_for(conn, tenant_id)
        if operation in {"check_availability", "find_alternative_slots", "book_appointment", "reschedule_appointment"}:
            parsed = calendar_engine.resolve_natural_datetime(values.get("appointment_at", ""), config["timezone"])
            if parsed.get("needs_clarification"):
                return 200, {"success": False, "needs_clarification": True, "message": parsed.get("reason", "Ask the customer for an exact date and time.")}
            values["appointment_at"] = parsed["resolved"]
        if operation == "get_current_datetime":
            zone = ZoneInfo(config["timezone"])
            current = datetime.fromtimestamp(int(time.time() if current_time is None else current_time), zone)
            return 200, {"success": True, "datetime": current.isoformat(), "timezone": config["timezone"]}
        if operation == "get_business_hours":
            return 200, {"success": True, "timezone": config["timezone"], "business_hours": config["business_hours"], "holidays": config["holidays"], "duration_minutes": config["duration_minutes"], "buffer_minutes": config["buffer_minutes"]}
        if operation == "check_availability":
            return 200, calendar_engine.availability(conn, tenant_id, values.get("appointment_at", ""), values.get("duration_minutes"), values.get("staff_id"), checked_calendar if check_calendar else None, service=values.get("service", ""), department=values.get("department", ""))
        if operation in {"get_available_slots", "get_staff_availability"}:
            return 200, calendar_engine.available_slots(conn, tenant_id, values.get("date", ""), values.get("duration_minutes"), values.get("staff_id"), 20, checked_calendar if check_calendar else None, values.get("service", ""), values.get("department", ""))
        if operation == "find_alternative_slots":
            return 200, calendar_engine.alternatives(conn, tenant_id, values.get("appointment_at", ""), values.get("duration_minutes"), values.get("staff_id"), checked_calendar if check_calendar else None, values.get("service", ""), values.get("department", ""))
        if operation == "book_appointment":
            if not all(str(values.get(key, "")).strip() for key in ("customer_name", "phone", "service", "appointment_at")):
                return 400, {"success": False, "message": "Customer name, phone, service and appointment time are required."}
            call_id = str(values.get("call_id") or values.get("system__conversation_id") or conversation_id or "").strip()
            if not call_id or len(call_id) > 200:
                return 400, {"success": False, "message": "A valid system conversation ID is required for idempotent booking."}
            values["idempotency_key"] = call_id
            booked = calendar_engine.book(conn, tenant_id, values, call_id, (lambda payload: reserve_calendar(tenant_id, payload)) if reserve_calendar else None, checked_calendar if check_calendar else None, (lambda event_id, action, details: modify_calendar(tenant_id, event_id, action, details)) if modify_calendar else None)
            return 200, booked
        if operation == "find_appointment":
            appointment = calendar_engine.find_appointment(conn, tenant_id, values)
            return 200, {"success": bool(appointment), "appointment": appointment, "message": "Appointment found." if appointment else "No matching appointment found."}
        if operation == "cancel_appointment":
            return 200, calendar_engine.change_appointment(conn, tenant_id, values, "cancel", (lambda event_id, action, details: modify_calendar(tenant_id, event_id, action, details)) if modify_calendar else None)
        if operation == "reschedule_appointment":
            return 200, calendar_engine.change_appointment(conn, tenant_id, values, "reschedule", (lambda event_id, action, details: modify_calendar(tenant_id, event_id, action, details)) if modify_calendar else None, checked_calendar if check_calendar else None)
    except (ValueError, TypeError, OverflowError) as error:
        return 400, {"success": False, "error": str(error)}
    except Exception:
        return 502, {"success": False, "error": "Calendar operation failed."}
    return 404, {"error": "Unknown calendar operation."}


def post_route(path, data, conn, api_key, protect, reveal, public_url):
    """Return (status, response) for authenticated OIM admin POST routes."""
    if path == "/api/admin/voice-platform/calendar":
        from calendar_engine import validate_settings
        try:
            tenant_id = int(data.get("tenant_id", 0))
            if tenant_id < 1 or not conn.execute("SELECT 1 FROM tenants WHERE id=? AND role='customer'", (tenant_id,)).fetchone():
                return 400, {"error": "Select a valid customer."}
            config = validate_settings(data.get("settings"))
            conn.execute("INSERT INTO calendar_settings(tenant_id,config_json,updated_at) VALUES(?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET config_json=excluded.config_json,updated_at=excluded.updated_at", (tenant_id, json.dumps(config, ensure_ascii=False), int(time.time())))
            conn.commit()
            _event(conn, "calendar_settings", "saved", "Calendar configuration saved.")
            return 200, {"ok": True, "tenant_id": tenant_id, "settings": config}
        except (TypeError, ValueError) as error:
            return 400, {"error": str(error)}
    if path == "/api/admin/voice-platform/tools/test":
        try:
            return 200, {"ok": True, **test_webhook(data.get("url"), data.get("method", "POST"), data.get("headers", {}), data.get("body"), data.get("timeout", 10))}
        except (TypeError, ValueError) as error:
            return 400, {"error": str(error)}
    if path == "/api/admin/voice-platform/calendar-tools":
        if not api_key:
            return 503, {"error": "Save an ElevenLabs API key in Integrations first."}
        try:
            return provision_calendar_tools(conn, api_key, protect, reveal, public_url, data.get("tenant_id"), data.get("agent_id"))
        except ProviderError as error:
            _event(conn, "calendar_tools_provision", "failed", str(error))
            return error.status, {"error": str(error)}
    prefix = "/api/admin/voice-platform/"
    if not path.startswith(prefix):
        return None
    resource = path[len(prefix):].strip("/").split("/")
    if resource[0] == "webhook-secret":
        secret = str(data.get("secret", "")).strip()
        if len(secret) > 500:
            return 400, {"error": "Webhook secret is too long."}
        conn.execute("INSERT INTO system_settings(key,value,updated_at) VALUES('elevenlabs_webhook_secret',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (protect(secret), int(time.time())))
        conn.commit()
        return 200, {"ok": True, "configured": bool(secret)}
    if resource[0] == "calendar":
        return None
    if not api_key:
        return 503, {"error": "Save an ElevenLabs API key in Integrations first."}
    try:
        if resource[0] == "connection-test":
            provider = conn.execute("SELECT voice_id,model FROM provider_settings WHERE provider='elevenlabs'").fetchone()
            if not provider:
                raise ProviderError(400, "Save an enabled ElevenLabs provider before checking the phone bridge.")
            capabilities = check_phone_capabilities(api_key, provider["voice_id"], provider["model"])
            conn.execute("UPDATE provider_settings SET check_status='ok',checked_at=? WHERE provider='elevenlabs'", (int(time.time()),))
            conn.commit()
            _event(conn, "elevenlabs_connection", "ok", "ElevenLabs phone capabilities verified.")
            return 200, {"ok": True, "capabilities": capabilities}
        if resource[0] == "sync":
            synced = {}
            for kind, endpoint, collection in (("agent", "/v1/convai/agents", "agents"), ("tool", "/v1/convai/tools", "tools"), ("knowledge", "/v1/convai/knowledge-base", "documents"), ("voice", "/v2/voices", "voices")):
                response = provider_request(api_key, "GET", endpoint, query={"page_size": 100})
                items = response.get(collection, []) if isinstance(response, dict) else []
                synced[kind] = len(items) if isinstance(items, list) else 0
                for item in items if isinstance(items, list) else []:
                    if not isinstance(item, dict):
                        continue
                    item_id = item.get("agent_id") or item.get("id") or item.get("voice_id")
                    if not item_id:
                        continue
                    config = _remote_config(item) if kind == "agent" else item
                    _cache(conn, kind, str(item_id), item.get("name") or item.get("display_name") or kind, config, protect)
            _event(conn, "elevenlabs_sync", "ok", "Synchronized agents, tools, knowledge documents and voices.")
            return 200, {"ok": True, "synced": synced, "note": "Each provider response may be paginated; use the list views to load remaining pages."}
        if resource[0] == "agents":
            if len(resource) == 1:
                config = agent_payload(data.get("config", data))
                response = provider_request(api_key, "POST", "/v1/convai/agents/create", config)
                agent_id = str(response.get("agent_id", ""))
                if agent_id:
                    _cache(conn, "agent", agent_id, config.get("name", "New agent"), config, protect, int(data.get("tenant_id") or 0) or None, config)
                _event(conn, "agent_create", "ok", "Agent created in ElevenLabs.")
                return 201, {"ok": True, "agent_id": agent_id, "provider": response}
            agent_id = _safe_id(resource[1])
            decoded_id = urllib.parse.unquote(agent_id)
            if len(resource) == 3 and resource[2] == "local":
                local = agent_payload(data.get("config"))
                cached = conn.execute("SELECT remote_hash,remote_config,tenant_id FROM voice_platform_items WHERE kind='agent' AND item_id=?", (decoded_id,)).fetchone()
                if not cached:
                    current = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                    _cache(conn, "agent", decoded_id, current.get("name", ""), _remote_config(current), protect, int(data.get("tenant_id") or 0) or None, _remote_config(current))
                    cached = conn.execute("SELECT remote_hash,remote_config,tenant_id FROM voice_platform_items WHERE kind='agent' AND item_id=?", (decoded_id,)).fetchone()
                conn.execute("UPDATE voice_platform_items SET local_config=?,updated_at=? WHERE kind='agent' AND item_id=?", (protect(json.dumps(local, ensure_ascii=False, sort_keys=True)), int(time.time()), decoded_id))
                conn.commit()
                remote = json.loads(reveal(cached["remote_config"]))
                remote_hash = hashlib.sha256(json.dumps(remote, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                return 200, {"ok": True, "agent_id": decoded_id, "config": local, "remote_hash": remote_hash, "in_conflict": remote_hash != cached["remote_hash"]}
            if len(resource) == 3 and resource[2] == "branches":
                parent_version_id = str(data.get("parent_version_id", "")).strip()
                name = str(data.get("name", "")).strip()
                description = str(data.get("description", "")).strip()
                if not parent_version_id or not name or len(name) > 140 or len(description) > 4096:
                    return 400, {"error": "Branch name, parent version and description are required."}
                response = provider_request(api_key, "POST", "/v1/convai/agents/" + agent_id + "/branches", {"parent_version_id": parent_version_id, "name": name, "description": description})
                _event(conn, "agent_branch_create", "ok", "Agent branch created.")
                return 201, {"ok": True, "provider": response}
            if len(resource) == 5 and resource[2] == "branches" and resource[4] == "merge":
                source_branch = _safe_id(resource[3])
                target_branch = str(data.get("target_branch_id", "")).strip()
                if not target_branch or not data.get("confirm_merge"):
                    return 400, {"error": "Choose a target branch and confirm the merge. Merging may affect live traffic."}
                merge_payload = {key: data[key] for key in ("archive_source_branch", "force", "conflict_resolutions", "source_tip_id", "target_tip_id") if key in data}
                response = provider_request(api_key, "POST", "/v1/convai/agents/" + agent_id + "/branches/" + source_branch + "/merge", merge_payload, {"target_branch_id": target_branch})
                _event(conn, "agent_branch_merge", "ok", "Agent branch merged.")
                return 200, {"ok": True, "provider": response, "warning": "A branch merge can change live behavior. Review traffic deployments after the merge."}
            if len(resource) == 3 and resource[2] == "deployments":
                deployments = data.get("deployments")
                if not isinstance(deployments, list) or not deployments or len(deployments) > 20:
                    return 400, {"error": "Provide one or more branch traffic allocations."}
                try:
                    total = sum(float(item.get("percentage", -1)) for item in deployments if isinstance(item, dict))
                except (TypeError, ValueError):
                    return 400, {"error": "Deployment percentages are invalid."}
                if len(deployments) != sum(isinstance(item, dict) for item in deployments) or abs(total - 100) > 1e-6 or any(not item.get("branch_id") or float(item.get("percentage", -1)) < 0 for item in deployments):
                    return 400, {"error": "Deployment branch percentages must total exactly 100."}
                if not data.get("confirm_deployment"):
                    return 400, {"error": "Confirm the traffic deployment. This changes which branch serves calls."}
                response = provider_request(api_key, "POST", "/v1/convai/agents/" + agent_id + "/deployments", {"deployments": deployments})
                _event(conn, "agent_deployment", "ok", "Agent traffic deployment updated.")
                return 200, {"ok": True, "provider": response}
            if len(resource) == 3 and resource[2] == "restore":
                version_id = str(data.get("version_id", "")).strip()
                branch_id = str(data.get("branch_id", "")).strip()
                if not version_id or not branch_id or not data.get("confirm_restore"):
                    return 400, {"error": "Choose a version and target branch, then confirm restore."}
                historical = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id, query={"version_id": version_id})
                config = _remote_config(historical)
                config["version_description"] = "Restored from version " + version_id
                response = provider_request(api_key, "PATCH", "/v1/convai/agents/" + agent_id, config, {"branch_id": branch_id})
                _cache(conn, "agent", decoded_id, historical.get("name", ""), config, protect, None, config)
                _event(conn, "agent_restore", "ok", "Agent configuration restored as a new version.")
                return 200, {"ok": True, "provider": response, "note": "Restore creates a new version; it does not rewrite the immutable version history."}
            if len(resource) == 3 and resource[2] == "clone":
                name = str(data.get("name", ""))[:200]
                created = provider_request(api_key, "POST", "/v1/convai/agents/" + agent_id + "/duplicate", {"name": name} if name else {})
                new_id = str(created.get("agent_id", ""))
                if new_id:
                    cloned = provider_request(api_key, "GET", "/v1/convai/agents/" + _safe_id(new_id))
                    config = _remote_config(cloned)
                    _cache(conn, "agent", new_id, cloned.get("name", name), config, protect, int(data.get("tenant_id") or 0) or None, config)
                _event(conn, "agent_clone", "ok", "Agent cloned in ElevenLabs.")
                return 201, {"ok": True, "agent_id": new_id, "provider": created}
            if len(resource) == 3 and resource[2] in {"pull", "push"}:
                remote = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                remote_config = _remote_config(remote)
                cached = conn.execute("SELECT remote_hash,local_config,tenant_id FROM voice_platform_items WHERE kind='agent' AND item_id=?", (decoded_id,)).fetchone()
                if resource[2] == "pull":
                    _cache(conn, "agent", decoded_id, remote.get("name", ""), remote_config, protect, cached["tenant_id"] if cached else None, remote_config)
                    _event(conn, "agent_pull", "ok", "Agent configuration pulled from ElevenLabs.")
                    return 200, {"ok": True, "agent_id": decoded_id, "config": remote_config}
                if not cached:
                    return 409, {"error": "Import this agent before pushing local changes."}
                current_raw = json.dumps(remote_config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                current_hash = hashlib.sha256(current_raw.encode("utf-8")).hexdigest()
                base_hash = str(data.get("base_hash") or "")
                if not base_hash or base_hash != current_hash:
                    local = data.get("config")
                    _event(conn, "agent_push", "conflict", "Remote agent changed since the last import.")
                    return 409, {"error": "Configuration conflict. Review the remote and local versions before pushing.", "remote": remote_config, "local": local, "remote_hash": current_hash}
                local = agent_payload(data.get("config"))
                payload = dict(local)
                payload["version_description"] = str(data.get("version_description") or "Updated from OIM")[:200]
                branch_id = str(data.get("branch_id") or "").strip()
                response = provider_request(api_key, "PATCH", "/v1/convai/agents/" + agent_id, payload, {"branch_id": branch_id} if branch_id else None)
                updated = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id, query={"branch_id": branch_id} if branch_id else None)
                _cache(conn, "agent", decoded_id, updated.get("name", local.get("name", "")), _remote_config(updated), protect, cached["tenant_id"], local)
                _event(conn, "agent_push", "ok", "Agent configuration pushed to ElevenLabs.")
                return 200, {"ok": True, "agent_id": decoded_id, "provider": response, "config": _remote_config(updated)}
            if len(resource) == 3 and resource[2] == "tenant":
                tenant_id = int(data.get("tenant_id", 0))
                if tenant_id and not conn.execute("SELECT 1 FROM tenants WHERE id=? AND role='customer'", (tenant_id,)).fetchone():
                    return 400, {"error": "Select a valid customer."}
                current = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                _cache(conn, "agent", decoded_id, current.get("name", ""), _remote_config(current), protect, tenant_id or None, _remote_config(current))
                return 200, {"ok": True, "agent_id": decoded_id, "tenant_id": tenant_id or None}
            if len(resource) == 3 and resource[2] == "tools":
                current = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                config = _remote_config(current)
                prompt = config.setdefault("conversation_config", {}).setdefault("agent", {}).setdefault("prompt", {})
                ids = data.get("tool_ids")
                if not isinstance(ids, list) or len(ids) > 100 or any(not isinstance(item, str) or len(item) > 128 for item in ids):
                    return 400, {"error": "tool_ids must be a list of provider tool IDs."}
                prompt["tool_ids"] = list(dict.fromkeys(ids))
                response = provider_request(api_key, "PATCH", "/v1/convai/agents/" + agent_id, agent_payload(config))
                updated = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                _cache(conn, "agent", decoded_id, updated.get("name", ""), _remote_config(updated), protect, None, _remote_config(updated))
                _event(conn, "agent_tools", "ok", "Agent tool assignments updated.")
                return 200, {"ok": True, "provider": response, "tool_ids": prompt["tool_ids"]}
            if len(resource) == 3 and resource[2] == "knowledge":
                documents = data.get("documents")
                if not isinstance(documents, list) or len(documents) > 100:
                    return 400, {"error": "documents must be a list of at most 100 ElevenLabs knowledge documents."}
                normalized = []
                for item in documents:
                    if not isinstance(item, dict) or item.get("type") not in {"file", "text", "url"}:
                        return 400, {"error": "Each document needs a supported provider type (file, text or url)."}
                    doc_id, name = str(item.get("id", "")), str(item.get("name", ""))
                    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", doc_id) or len(name) > 200:
                        return 400, {"error": "A knowledge document ID or name is invalid."}
                    usage_mode = str(item.get("usage_mode", "auto"))
                    if usage_mode not in {"auto", "prompt"}:
                        return 400, {"error": "Knowledge usage_mode must be auto or prompt."}
                    normalized.append({"type": item["type"], "id": doc_id, "name": name, "usage_mode": usage_mode})
                current = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                config = _remote_config(current)
                prompt = config.setdefault("conversation_config", {}).setdefault("agent", {}).setdefault("prompt", {})
                prompt["knowledge_base"] = normalized
                response = provider_request(api_key, "PATCH", "/v1/convai/agents/" + agent_id, agent_payload(config))
                updated = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id)
                _cache(conn, "agent", decoded_id, updated.get("name", ""), _remote_config(updated), protect, None, _remote_config(updated))
                _event(conn, "agent_knowledge", "ok", "Agent knowledge documents updated.")
                return 200, {"ok": True, "provider": response, "documents": normalized}
            if len(resource) == 2 and str(data.get("action", "")) == "delete":
                if not data.get("confirm_delete"):
                    return 400, {"error": "Confirm permanent deletion of this ElevenLabs agent."}
                response = provider_request(api_key, "DELETE", "/v1/convai/agents/" + agent_id, query={"force": "true" if data.get("force_dependents") and data.get("confirm_force") else "false"})
                conn.execute("DELETE FROM voice_platform_items WHERE kind='agent' AND item_id=?", (decoded_id,))
                conn.commit()
                _event(conn, "agent_delete", "ok", "Agent deleted in ElevenLabs.")
                return 200, {"ok": True, "provider": response}
            if len(resource) == 2:
                config = agent_payload(data.get("config", data))
                branch_id = str(data.get("branch_id") or "").strip()
                params = {"branch_id": branch_id} if branch_id else None
                provider_request(api_key, "PATCH", "/v1/convai/agents/" + agent_id, config, params)
                updated = provider_request(api_key, "GET", "/v1/convai/agents/" + agent_id, params)
                _cache(conn, "agent", decoded_id, updated.get("name", config.get("name", "")), _remote_config(updated), protect, None, config)
                _event(conn, "agent_update", "ok", "Agent updated in ElevenLabs.")
                return 200, {"ok": True, "agent_id": decoded_id, "config": _remote_config(updated)}
        if resource[0] == "tools":
            if len(resource) == 1:
                config = data.get("tool_config")
                if not isinstance(config, dict) or not isinstance(config.get("name"), str) or len(config["name"]) > 100:
                    return 400, {"error": "A valid ElevenLabs tool_config with a name is required."}
                if config.get("type") == "webhook":
                    schema = config.get("api_schema") or {}
                    safe_url = validate_public_https_url(schema.get("url", ""))
                    schema["url"] = safe_url
                    schema["follow_redirects"] = False
                    config["api_schema"] = schema
                response = provider_request(api_key, "POST", "/v1/convai/tools", {"tool_config": config, **({"response_mocks": data["response_mocks"]} if isinstance(data.get("response_mocks"), list) else {})})
                tool_id = str(response.get("id", ""))
                if tool_id:
                    _cache(conn, "tool", tool_id, config.get("name", ""), response.get("tool_config", config), protect, None, config)
                _event(conn, "tool_create", "ok", "Tool created in ElevenLabs.")
                return 201, {"ok": True, "provider": response}
            tool_id = _safe_id(resource[1])
            if len(resource) == 3 and resource[2] == "delete":
                if not data.get("confirm_delete"):
                    return 400, {"error": "Confirm deletion of this shared ElevenLabs tool."}
                dependents = provider_request(api_key, "GET", "/v1/convai/tools/" + tool_id + "/dependent-agents")
                agents = dependents.get("agents", []) if isinstance(dependents, dict) else []
                if agents and not data.get("confirm_shared_delete"):
                    return 409, {"error": "This tool is assigned to agents. Review and confirm the shared impact before deletion.", "agents": agents}
                response = provider_request(api_key, "DELETE", "/v1/convai/tools/" + tool_id)
                conn.execute("DELETE FROM voice_platform_items WHERE kind='tool' AND item_id=?", (urllib.parse.unquote(tool_id),))
                conn.commit()
                _event(conn, "tool_delete", "ok", "Tool deleted in ElevenLabs.")
                return 200, {"ok": True, "provider": response}
            if len(resource) == 2:
                config = data.get("tool_config")
                if not isinstance(config, dict):
                    return 400, {"error": "tool_config must be a JSON object."}
                if config.get("type") == "webhook":
                    schema = config.get("api_schema") or {}
                    schema["url"] = validate_public_https_url(schema.get("url", ""))
                    schema["follow_redirects"] = False
                    config["api_schema"] = schema
                response = provider_request(api_key, "PATCH", "/v1/convai/tools/" + tool_id, {"tool_config": config})
                _cache(conn, "tool", urllib.parse.unquote(tool_id), config.get("name", ""), response.get("tool_config", config), protect, None, config)
                _event(conn, "tool_update", "ok", "Tool updated in ElevenLabs. Tool definitions are shared across agents.")
                return 200, {"ok": True, "provider": response, "warning": "ElevenLabs tool definitions are shared across all agents using this tool ID."}
        if resource[0] == "knowledge":
            if len(resource) == 1:
                kind = str(data.get("type", "text"))
                if kind == "text":
                    content = str(data.get("content", ""))
                    if not content.strip() or len(content) > 500000:
                        return 400, {"error": "Knowledge text must contain 1 to 500000 characters."}
                    payload = {"text": content, "name": str(data.get("name", "Knowledge document"))[:200]}
                    response = provider_request(api_key, "POST", "/v1/convai/knowledge-base/text", payload)
                elif kind == "url":
                    url = validate_public_https_url(data.get("url", ""))
                    response = provider_request(api_key, "POST", "/v1/convai/knowledge-base/url", {"url": url, "name": str(data.get("name", ""))[:200], "enable_auto_sync": bool(data.get("enable_auto_sync", False))})
                elif kind == "file":
                    filename = str(data.get("filename", ""))
                    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                    if extension not in {"pdf", "docx", "txt", "md", "html", "epub"}:
                        return 400, {"error": "Upload a PDF, DOCX, TXT, Markdown, HTML or EPUB file."}
                    try:
                        encoded = str(data.get("content_base64", ""))
                        if len(encoded) > 28 * 1024 * 1024:
                            return 400, {"error": "Knowledge files must be 20 MiB or smaller."}
                        file_bytes = base64.b64decode(encoded, validate=True)
                    except (ValueError, TypeError):
                        return 400, {"error": "File content must use valid base64 encoding."}
                    if not file_bytes:
                        return 400, {"error": "The selected file is empty."}
                    response = provider_upload(api_key, filename, str(data.get("content_type", "application/octet-stream")), file_bytes, str(data.get("name", "")))
                    response["type"] = "file"
                else:
                    return 400, {"error": "Choose text, file or HTTPS URL as the knowledge source."}
                _cache(conn, "knowledge", str(response.get("id", "")), response.get("name", ""), response, protect)
                _event(conn, "knowledge_create", "ok", "Knowledge document created in ElevenLabs.")
                return 201, {"ok": True, "provider": response}
            document_id = _safe_id(resource[1])
            if len(resource) == 3 and resource[2] == "delete":
                if not data.get("confirm_delete"):
                    return 400, {"error": "Confirm deletion of this knowledge document."}
                dependents = provider_request(api_key, "GET", "/v1/convai/knowledge-base/" + document_id + "/dependent-agents", query={"dependent_type": "all", "page_size": 100})
                agents = dependents.get("agents", []) if isinstance(dependents, dict) else []
                if agents:
                    return 409, {"error": "Remove this document from its dependent agents before deleting it.", "agents": agents}
                response = provider_request(api_key, "DELETE", "/v1/convai/knowledge-base/" + document_id)
                conn.execute("DELETE FROM voice_platform_items WHERE kind='knowledge' AND item_id=?", (urllib.parse.unquote(document_id),))
                conn.commit()
                _event(conn, "knowledge_delete", "ok", "Knowledge document deleted in ElevenLabs.")
                return 200, {"ok": True, "provider": response}
            if len(resource) == 2:
                payload = {key: data[key] for key in ("name", "content", "enable_auto_sync", "auto_remove", "minimum_frequency_days") if key in data}
                response = provider_request(api_key, "PATCH", "/v1/convai/knowledge-base/" + document_id, payload)
                _event(conn, "knowledge_update", "ok", "Knowledge document updated in ElevenLabs.")
                return 200, {"ok": True, "provider": response}
        if resource[0] == "tests" and len(resource) == 1:
            test = data.get("test")
            if not isinstance(test, dict) or not isinstance(test.get("agent_id"), str):
                return 400, {"error": "A provider-supported test object with agent_id is required."}
            response = provider_request(api_key, "POST", "/v1/convai/agent-testing/create", test)
            _event(conn, "agent_test_create", "ok", "ElevenLabs test scenario created.")
            return 201, {"ok": True, "provider": response}
        if resource[0] == "run-tests" and len(resource) == 2:
            agent_id = _safe_id(resource[1])
            tests = data.get("tests")
            if not isinstance(tests, list) or not tests or len(tests) > 50:
                return 400, {"error": "Select between 1 and 50 saved test IDs."}
            if not data.get("confirm_external_tools"):
                return 400, {"error": "Confirm that test scenarios can call tools attached to this agent."}
            payload = {"tests": tests, "name": str(data.get("name", "OIM safe test"))[:200], "repeat_count": max(1, min(int(data.get("repeat_count", 1)), 5))}
            if data.get("branch_id"):
                payload["branch_id"] = str(data["branch_id"])
            response = provider_request(api_key, "POST", "/v1/convai/agents/" + agent_id + "/run-tests", payload)
            _event(conn, "agent_test_run", "ok", "Provider test invocation submitted.")
            return 202, {"ok": True, "provider": response, "warning": "Review attached tool calls before running scenarios against a production agent."}
    except ProviderError as error:
        _event(conn, "provider_write", "failed", str(error))
        return error.status, {"error": str(error)}
    except (ValueError, TypeError, KeyError, IndexError) as error:
        return 400, {"error": str(error) or "Invalid request."}
    return 404, {"error": "Voice platform route not found."}
