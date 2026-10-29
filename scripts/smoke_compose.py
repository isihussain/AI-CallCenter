"""Build an isolated Compose project and verify HTTPS login and data/key persistence."""
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = "oim-smoke-" + secrets.token_hex(4)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    password = secrets.token_urlsafe(24)
    with tempfile.TemporaryDirectory(prefix=project) as directory:
        env_file = Path(directory) / "smoke.env"
        env_file.write_text(f"OIM_BOOTSTRAP_ADMIN_USERNAME=smoke-admin\nOIM_BOOTSTRAP_ADMIN_PASSWORD={password}\n", encoding="utf-8")
        env = dict(os.environ, OIM_ENV_FILE=str(env_file), OIM_HTTPS_PORT=str(port),
                   OIM_BIND_ADDRESS="127.0.0.1", OIM_PUBLIC_URL=f"https://localhost:{port}")
        command = ["docker", "compose", "-p", project]

        def compose(*args, capture=False):
            return subprocess.run(command + list(args), cwd=ROOT, env=env, check=True,
                                  stdout=subprocess.PIPE if capture else None, text=True).stdout

        try:
            compose("up", "--build", "-d", "--wait", "--wait-timeout", "180")
            cert_file = Path(directory) / "cert.pem"
            compose("cp", "web:/etc/nginx/tls/cert.pem", str(cert_file))
            context = ssl.create_default_context(cafile=str(cert_file))
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(CookieJar()))
            base = f"https://localhost:{port}"

            def request(path, data=None):
                payload = json.dumps(data).encode() if data is not None else None
                req = urllib.request.Request(base+path, payload, {"Content-Type":"application/json"})
                with opener.open(req, timeout=15) as response:
                    return json.loads(response.read())

            def login():
                result = request("/api/login", {"username":"smoke-admin","password":password})
                assert result["user"]["role"] == "admin"

            login()
            request("/api/admin/legal-settings", {"user_agreement":"Synthetic smoke agreement","kvkk_text":"Synthetic smoke privacy"})
            tenant = request("/api/admin/tenants", {"name":"Synthetic Smoke Studio","username":"smoke-customer","password":secrets.token_urlsafe(24),"agreement_accepted":True})["tenant"]
            request("/api/admin/providers", {"provider":"openai","api_key":"synthetic-disabled-smoke-value","model":"disabled-smoke-model","enabled":False})
            providers = request("/api/admin/providers")["items"]
            assert next(x for x in providers if x["provider"] == "openai")["configured"]
            uid = compose("exec", "-T", "api", "id", "-u", capture=True).strip()
            assert uid == "10001", f"Unexpected API user: {uid}"
            with opener.open(base+"/", timeout=10) as response:
                assert b"AI Call Center" in response.read()
            for path, marker in (("/admin-console.js", b"AdminConsole"), ("/admin-console.css", b".flow-panel")):
                with opener.open(base+path, timeout=10) as response:
                    assert marker in response.read(), f"Missing admin asset: {path}"
            assert request("/api/admin/system-flow")["counts"]["tenants"] == 1
            compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "120", "api", "web")
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(CookieJar()))
            login()
            assert any(x["id"] == tenant["id"] for x in request("/api/admin/tenants")["items"])
            provider = next(x for x in request("/api/admin/providers")["items"] if x["provider"] == "openai")
            assert provider["configured"] and provider["masked"] == "••••••••", "Encryption key/settings did not persist or the mask exposed key characters"
            print("PASS: HTTPS, same-origin UI/API, secure login, non-root API, account and encryption-key persistence.")
        finally:
            # This randomly named test project owns all volumes removed here.
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()

