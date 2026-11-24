#!/usr/bin/env python3
"""Apply validated OIM SIP config through a private Asterisk AMI connection."""

import hmac
import json
import os
import re
import socket
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("PBX_CONFIG_DIR", "/pbx")).resolve()
CONTROL_SECRET = os.environ.get("OIM_PBX_CONTROL_SECRET", "").strip()
SIP_TARGET = os.environ.get("OIM_SIP_TARGET", "oim-ai").strip()
AMI_HOST = os.environ.get("PBX_AMI_HOST", "freepbx").strip()
AMI_PORT = int(os.environ.get("PBX_AMI_PORT", "5038"))
AMI_USERNAME = os.environ.get("PBX_AMI_USERNAME", "").strip()
AMI_PASSWORD = os.environ.get("PBX_AMI_PASSWORD", "").strip()
if not CONTROL_SECRET or not AMI_USERNAME or not AMI_PASSWORD:
    raise RuntimeError("PBX control and AMI credentials must be configured")
if SIP_TARGET not in {"oim-ai", "oim-elevenlabs-bridge"}:
    raise RuntimeError("Unsupported OIM SIP target")


def validate_entries(entries):
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ValueError("Invalid SIP entries")
    clean = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid SIP entry")
        tenant_id = int(entry["tenant_id"])
        username = str(entry["username"]).strip()
        did = str(entry.get("did") or username).strip()
        domain = str(entry["domain"]).strip().lower()
        password = str(entry["password"])
        if tenant_id < 1 or tenant_id in seen:
            raise ValueError("Invalid tenant id")
        if not re.fullmatch(r"[A-Za-z0-9_.+@-]{3,128}", username):
            raise ValueError("Invalid SIP username")
        if not re.fullmatch(r"[0-9+*#]{3,64}", did):
            raise ValueError("Invalid DID")
        if not re.fullmatch(r"(?=.{3,253}$)[A-Za-z0-9.-]+", domain):
            raise ValueError("Invalid SIP domain")
        if not password or len(password) > 256 or any(c in password for c in "\r\n"):
            raise ValueError("Invalid SIP password")
        seen.add(tenant_id)
        clean.append((tenant_id, username, did, domain, password))
    return clean


def atomic_write(name, content):
    target = CONFIG_DIR / name
    if target.parent.resolve() != CONFIG_DIR or target.is_symlink():
        raise ValueError("Invalid PBX configuration target")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    old_mode = target.stat().st_mode & 0o777 if target.exists() else 0o640
    fd, temp_name = tempfile.mkstemp(prefix=".oim-", dir=CONFIG_DIR, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, old_mode)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def ami_action(stream, action):
    stream.write((action + "\r\n\r\n").encode())
    stream.flush()
    lines = []
    while True:
        line = stream.readline()
        if not line:
            raise ConnectionError("AMI closed the connection")
        if line in (b"\r\n", b"\n"):
            break
        lines.append(line.decode("utf-8", "replace").strip())
        if len(lines) > 64:
            raise ConnectionError("Unexpected AMI response")
    if any(line.lower().startswith("response: error") for line in lines):
        raise ConnectionError("AMI rejected the action")


def ami_command(command):
    if command not in {"module reload res_pjsip.so", "dialplan reload"}:
        raise ValueError("Unsupported Asterisk command")
    with socket.create_connection((AMI_HOST, AMI_PORT), timeout=8) as sock:
        sock.settimeout(60)
        stream = sock.makefile("rwb")
        greeting = stream.readline()
        if not greeting.startswith(b"Asterisk Call Manager/"):
            raise ConnectionError("Invalid AMI greeting")
        login = "Action: Login\r\nUsername: {}\r\nSecret: {}\r\nEvents: off".format(AMI_USERNAME, AMI_PASSWORD)
        ami_action(stream, login)
        stream.write(("Action: Command\r\nCommand: {}\r\n\r\n".format(command)).encode())
        stream.flush()
        response = []
        response_type = ""
        response_message = ""
        while True:
            line = stream.readline()
            if not line:
                raise ConnectionError("AMI closed during command")
            line = line.decode("utf-8", "replace").strip()
            response.append(line)
            if len(response) > 256:
                raise ConnectionError("Unexpected AMI command output")
            if line.lower().startswith("response:"):
                response_type = line.split(":", 1)[1].strip().lower()
            elif line.lower().startswith("message:"):
                response_message = line.split(":", 1)[1].strip().lower()
            if response_type == "error":
                raise ConnectionError("AMI rejected the command")
            if response_type == "follows" and line == "--END COMMAND--":
                break
            if response_type == "success" and response_message == "command output follows" and not line:
                break
            if response_type == "success" and response_message != "command output follows" and not line:
                break
        stream.write(b"Action: Logoff\r\n\r\n")
        stream.flush()


def apply_configuration(entries):
    clean = validate_entries(entries)
    pjsip_sections = ["""[oim-verimor-inbound]
type=endpoint
transport=0.0.0.0-udp
context=from-verimor
disallow=all
allow=ulaw,alaw
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes
"""]
    for tenant_id, username, did, domain, password in clean:
        section = f"oim-t{tenant_id}"
        pjsip_sections.append(f"""[{section}-auth]
type=auth
auth_type=userpass
username={username}
password={password}

[{section}-aor]
type=aor
contact=sip:{domain}:5060
qualify_frequency=60

[{section}-endpoint]
type=endpoint
transport=0.0.0.0-udp
context=from-verimor
disallow=all
allow=ulaw,alaw
outbound_auth={section}-auth
aors={section}-aor
from_user={username}
from_domain={domain}
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[{section}-registration]
type=registration
transport=0.0.0.0-udp
outbound_auth={section}-auth
server_uri=sip:{domain}
client_uri=sip:{username}@{domain}
retry_interval=60
forbidden_retry_interval=600
expiration=3600
contact_user={username}
""")

    atomic_write("pjsip_oim_tenants.conf", "".join(pjsip_sections))
    pjsip_path = CONFIG_DIR / "pjsip_custom.conf"
    pjsip_base = pjsip_path.read_text(encoding="utf-8") if pjsip_path.exists() else ""
    managed_sections = {"verimor-auth", "verimor-aor", "verimor-endpoint", "verimor-registration", "oim-verimor-inbound"}
    managed_sections.update(re.findall(r"(?m)^\[(oim-t\d+-(?:auth|aor|endpoint|registration))\]", pjsip_base))
    for section in managed_sections:
        pjsip_base = re.sub(rf"(?ms)^\[{re.escape(section)}\]\n.*?(?=^\[|\Z)", "", pjsip_base)
    pjsip_base = re.sub(r"(?m)^#include /etc/asterisk/pjsip_oim_tenants\.conf\s*\n?", "", pjsip_base)
    pjsip_base = pjsip_base.rstrip() + "\n\n" + "".join(pjsip_sections)
    atomic_write("pjsip_custom.conf", pjsip_base)

    routes = ["[oim-route]"]
    for tenant_id, username, did, domain, password in clean:
        routes.append(f'exten => {did},1,Set(OIM_TENANT={tenant_id})\n same => n,ExecIf($["${{FROM_DID}}"=""]?Set(FROM_DID=${{EXTEN}}))\n same => n,Goto({SIP_TARGET},s,1)')
    routes.append(f'exten => _X.,1,Set(OIM_TENANT=2)\n same => n,ExecIf($["${{FROM_DID}}"=""]?Set(FROM_DID=${{EXTEN}}))\n same => n,Goto({SIP_TARGET},s,1)')
    routes.append(f'exten => s,1,Set(OIM_TENANT=2)\n same => n,Goto({SIP_TARGET},s,1)')
    atomic_write("extensions_oim_tenants.conf", "\n".join(routes) + "\n")
    extension_path = CONFIG_DIR / "extensions_custom.conf"
    extension_base = extension_path.read_text(encoding="utf-8") if extension_path.exists() else ""
    extension_base = re.sub(r"(?m)^\s*#include extensions_oim_tenants\.conf\s*\n?", "", extension_base)
    extension_base = re.sub(r"(?ms)\n; OIM TENANT ROUTES BEGIN\n.*?\n; OIM TENANT ROUTES END\n?", "\n", extension_base)
    extension_base = extension_base.rstrip() + "\n\n; OIM TENANT ROUTES BEGIN\n" + "\n".join(routes) + "\n; OIM TENANT ROUTES END\n"
    extension_base = re.sub(r"(?m)^\s*#include extensions_oim_bridge\.conf\s*\n?", "", extension_base)
    if SIP_TARGET == "oim-elevenlabs-bridge":
        extension_base = extension_base.rstrip() + "\n\n#include extensions_oim_bridge.conf\n"
    atomic_write("extensions_custom.conf", extension_base)

    ami_command("module reload res_pjsip.so")
    ami_command("dialplan reload")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/healthz":
            return self.send_json(404, {"ok": False})
        return self.send_json(200, {"ok": True})

    def do_POST(self):
        if self.path != "/apply-sip":
            return self.send_json(404, {"applied": False})
        supplied = self.headers.get("X-OIM-PBX-Control-Secret", "")
        if not hmac.compare_digest(supplied, CONTROL_SECRET):
            return self.send_json(401, {"applied": False})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1_000_000:
                raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Invalid request")
            apply_configuration(body.get("entries"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return self.send_json(400, {"applied": False, "error": "Invalid SIP configuration"})
        except Exception as error:
            print("PBX apply failed:", type(error).__name__, flush=True)
            return self.send_json(502, {"applied": False, "error": "PBX configuration reload failed"})
        return self.send_json(200, {"applied": True})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9018), Handler).serve_forever()
