# Shared VPS deployment

Use this deployment when the VPS already hosts other applications. It runs AI Call Center as its own Docker Compose project, keeps its database and encryption key in project-scoped volumes, and leaves the API private to the Compose network.

## Network layout

Preferred layout when the server already has Nginx, Caddy, or another reverse proxy:

```text
Browser -- HTTPS :443 --> existing reverse proxy
                           |
                           +-- this app's hostname --> 127.0.0.1:18443
                                                        |
                                                        +-- Compose web --> private API
```

The port `18443` is only an example. Check the server and Docker port mappings first, then select an unused loopback port. Compose project names isolate container and volume names; they do not prevent host port conflicts.

## Inspect the VPS before changing it

Run these read-only checks after receiving access:

```sh
docker --version
docker compose version
docker compose ls
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
sudo ss -lntup
systemctl is-active nginx caddy traefik
sudo ufw status verbose
```

Also inspect the VPS provider's firewall. Do not install or restart Docker, Nginx, Caddy, or another shared service until its current state and dependent applications are understood. Check that the deployment directory is unused before creating it.

## Prepare the isolated Compose project

Use a unique project name and path. If either already exists, inspect it and choose a different name rather than reusing it.

```sh
sudo install -d -m 0750 /opt/ai-call-center-prod
sudo chown "$USER":"$(id -gn)" /opt/ai-call-center-prod
git clone https://github.com/isihussain/AI-CallCenter.git /opt/ai-call-center-prod/source
cd /opt/ai-call-center-prod/source
cp .env.compose.example .env
chmod 600 .env
```

Set these values in the private `.env` file. Replace the domain and example port after checking DNS, the existing proxy, and listening ports:

```dotenv
OIM_PUBLIC_URL=https://callcenter.example.com
OIM_BIND_ADDRESS=127.0.0.1
OIM_HTTPS_PORT=18443
OIM_BOOTSTRAP_ADMIN_USERNAME=admin
OIM_BOOTSTRAP_ADMIN_PASSWORD=
```

Keep real provider credentials out of Git. The first start creates a one-time administrator credential file in the protected data volume when no bootstrap password is provided. Retrieve it from the server terminal, sign in, change the password, then remove the file:

```sh
docker compose -p ai-call-center-prod exec api cat /data/bootstrap-credentials.txt
docker compose -p ai-call-center-prod exec api rm /data/bootstrap-credentials.txt
```

If credentials were supplied privately through a secret manager, do not put them in shell history or a public issue.

## Start and check the app

Validate the resolved Compose configuration before starting containers. Confirm that the web mapping uses the selected loopback address and port and that the API has no published host port.

```sh
docker compose -p ai-call-center-prod --env-file .env config
docker compose -p ai-call-center-prod --env-file .env up --build -d --wait
docker compose -p ai-call-center-prod ps
curl --fail https://127.0.0.1:18443/healthz -k
```

The development certificate inside the web container is for localhost. The public reverse proxy terminates HTTPS using the valid certificate for the app's hostname and forwards requests to the loopback-only Compose web port. The [Nginx example](../deploy/shared-vps/nginx-site.example) is an additive virtual host; replace its sample hostname and certificate paths before installing it. It disables certificate verification only for the localhost upstream, which must remain loopback-bound.

For the supplied Nginx example, copy it as a new site file and edit only its placeholders. Run `nginx -t` before reloading Nginx. If validation fails, leave the running proxy and its existing sites untouched and correct or remove only the new site file.

## Firewall and ports

- Keep the Compose web port bound to `127.0.0.1`; do not open it to the internet.
- The API port `8787`, SQLite database, and Docker internal ports remain unpublished.
- Allow inbound TCP `443` only if the host or provider firewall does not already allow it for the existing reverse proxy. Do not reset firewall rules or open broad port ranges.
- Keep AudioSocket port `9019` closed unless this VPS will also connect to an Asterisk PBX and the port has been checked and configured for that specific deployment.
- If no existing reverse proxy can serve the app, stop and choose a dedicated public HTTPS port only after checking the provider firewall and Docker's forwarding rules. Do not assume a UFW allow rule filters Docker-published ports.

## Updating and stopping

Use the same unique project name for every command. Back up the database and its matching encryption key before an update. These commands target this Compose project only:

```sh
docker compose -p ai-call-center-prod ps
docker compose -p ai-call-center-prod logs --tail=100 api web
docker compose -p ai-call-center-prod up --build -d --wait
docker compose -p ai-call-center-prod down
```

Do not use `docker compose down --volumes`, `docker system prune`, or global firewall resets on a shared VPS. Keep backups and logs private; redact credentials, caller data, public IP addresses, domains, and server identifiers before creating public GitHub notes.

## Asterisk and ElevenLabs bridge

The base Compose stack leaves the ElevenLabs AudioSocket bridge disabled and does not publish its TCP listener or the API to the host. For a same-host Docker PBX, use the separately reviewed [telephony Compose deployment](docker-telephony.md), which publishes only the documented SIP/TLS/RTP ports and keeps the control API and AudioSocket listener on the private Compose network. Keep the existing inbound route until the provider checks and an approved controlled call test pass.
