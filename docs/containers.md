# Container installation

The Compose stack runs the Python API and an Nginx frontend on one HTTPS origin. Named volumes retain application data, optional recordings, and TLS files. The API runs as UID/GID 10001, has no published host port, and reads credentials at runtime.

You need Docker Engine with Docker Compose v2 or newer. Docker Desktop with its Linux engine works on Windows and macOS. Normal container installation does not require Python on the host.

## Start locally

From the repository root:

~~~sh
cp .env.compose.example .env
docker compose up --build -d --wait
~~~

In PowerShell, use `Copy-Item .env.compose.example .env` for the first command.

Open `https://localhost:8443`. The `tls` setup container creates a self-signed certificate for localhost, including the loopback address. Your browser will require you to trust this development certificate yourself. Use a trusted certificate for a public deployment. Session cookies remain `Secure`, so use the documented HTTPS origin.

If the database is empty and no bootstrap password is supplied, retrieve the generated first-login credentials through your protected local terminal:

~~~sh
docker compose exec api cat /data/bootstrap-credentials.txt
~~~

Save those credentials privately, then remove the credentials file from the data volume. It is not a public web asset. Alternatively, supply a unique `OIM_BOOTSTRAP_ADMIN_PASSWORD` in the protected `.env` before the first start; no credentials file is created in that case. Bootstrap variables do not reset an existing account.

The initial database has one administrator and no customer accounts. Add customers after configuring your agreement and privacy text. Provider accounts, SIP routes, and published business knowledge are required for actual AI telephone calls.

## Configuration and persistence

Copy `.env.compose.example` to `.env` and supply your own values privately. Compose loads that file; the Python application does not parse `.env` itself.

| Item | Container location | Persistence |
| --- | --- | --- |
| SQLite database | `/data/oim.db` | `data` named volume |
| Encryption key | `/data/.secret` | Same `data` volume; retain with the database |
| Generated first-run credentials | `/data/bootstrap-credentials.txt` | Remove after securely saving them |
| Optional recordings | `/recordings` | `recordings` volume, read-only to the API |
| Certificate and private key | `/etc/nginx/tls/cert.pem` and `key.pem` in the frontend | `tls` named volume |

Compose fixes container paths and the API's internal bind address. The bare-server host/port/path variables do not override those container paths.

`OIM_BIND_ADDRESS` defaults to loopback and `OIM_HTTPS_PORT` defaults to `8443`. Set `OIM_PUBLIC_URL` to the exact public origin, including a nonstandard port if used. Google OAuth callbacks must use that origin.

## Trusted TLS for a public deployment

Obtain a certificate for your domain through your certificate provider. Keep its files outside Git. This example copies a `fullchain.pem` and `privkey.pem` pair from a private local `tls/` folder into the TLS volume:

~~~sh
docker compose stop web
docker compose run --rm --no-deps --user 0 \
  -v "$PWD/tls:/certs:ro" tls sh -c \
  'cp /certs/fullchain.pem /tls/cert.pem && cp /certs/privkey.pem /tls/key.pem && chmod 600 /tls/key.pem'
docker compose up -d --wait
~~~

In PowerShell, put the multiline command on one line or use PowerShell continuation syntax. The setup container retains an existing complete pair. It does not renew public certificates. Repeat the copy and restart `web` after your certificate provider renews them.

To expose the service through the host's public interface, set the desired bind address and HTTPS port in `.env` and apply your host firewall/reverse-proxy rules. The API stays on the private Compose network.

## Logs, health, upgrades, and shutdown

~~~sh
docker compose ps
docker compose logs --tail=100 api web
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8787/api/health').status)"
docker compose up --build -d --wait
docker compose down
~~~

`docker compose down` retains named volumes. Adding `--volumes` removes them; only the disposable smoke test uses that option. Rebuild after pulling updates and back up the database and matching encryption key before upgrading.

Keep logs private and remove credentials, caller data, and server addresses before sharing excerpts.

## Back up and restore

Stop the API so the database and key can be copied together:

~~~sh
docker compose stop api
docker compose cp api:/data ./private-backup/
docker compose start api
~~~

Protect and encrypt this private copy using your normal backup system. It contains operational data and the encryption key; keep it outside the web root and Git.

To restore, create the target stack, stop its API, copy the backed-up `data` contents into `/data`, and restore ownership to UID/GID 10001 before starting the API. Restore the database and matching key as a pair. Check the restored login and reading an encrypted integration setting before routing calls.

## PBX and recording integration

The image does not include Asterisk, SIP trunk credentials, host sudo privileges, or the operator-specific `oim-apply-sip` helper. Provision the PBX and inbound route through your operator's supported workflow. The panel cannot apply host PBX settings until that integration is implemented for your deployment.

For recordings from a separate PBX, add an operator-specific Compose override that mounts its recording directory at `/recordings:ro`. UID 10001 needs read access. Validate recording names and call identifiers with a non-production call before enabling delivery.

## Run the container smoke check

On a development machine with Python 3.11+ and Docker:

~~~sh
python scripts/smoke_compose.py
~~~

This builds a randomly named disposable stack. It checks HTTPS, same-origin routing, secure login, the API user, and account/key persistence after container recreation. It uses synthetic credentials and a disabled fake provider setting and never makes an AI call. It removes only its own project's containers and volumes.

