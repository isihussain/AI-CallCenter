# Docker telephony deployment

This optional Compose override runs FreePBX, Asterisk, Kamailio, a dedicated MariaDB instance, and the restricted PBX control service next to the OIM application. It does not use host networking or the Docker socket. Keep the PBX admin page on its loopback-only port and use an SSH tunnel to reach it.

FreePBX has no official Docker image. The example uses the community maintained [SavageCore FreePBX 17 image](https://github.com/SavageCore/docker-freepbx), which packages FreePBX 17 and Asterisk 22. Review its release and pin the image digest for a production deployment.

## Ports

| Host port | Protocol | Service |
| --- | --- | --- |
| `5060` | UDP | Asterisk SIP trunk signaling |
| `5061` | TCP | Kamailio TLS signaling for OpenAI Realtime SIP |
| `5062` | TCP | Asterisk PJSIP TLS |
| `10000-20000` | UDP | Asterisk RTP media |
| `18445` | TCP, loopback only | FreePBX admin page; open it through an SSH tunnel |

Kamailio UDP `5070`, Asterisk AMI `5038`, OIM AudioSocket `9019`, PBX control `9018`, MariaDB `3306`, and OIM API `8787` are not published to the host. The AudioSocket listener binds only to the OIM API address on the private Compose network.

The RTP range matches the default FreePBX configuration used by this deployment. The host forwards it directly to the PBX container, avoiding one Docker proxy process per RTP port. Change both the Asterisk RTP settings and the forwarding configuration together if you select another range. Do not publish the PBX web, AMI, database, AudioSocket, or control ports publicly.

## Prepare the deployment

1. Start the base application Compose stack and confirm its project network exists. The commands below assume the project name `oim-call-center-prod`.
2. Copy `.env.example` to `.env`, protect it with mode `0600`, and keep it out of Git. Set unique values for `OIM_PBX_SHARED_SECRET`, `OIM_PBX_CONTROL_SECRET`, `PBX_AMI_PASSWORD`, `PBX_DB_PASSWORD`, and `PBX_DB_ROOT_PASSWORD`. Use at least 32 random bytes for each secret. Set `PBX_TLS_DOMAIN` to the hostname covered by the PBX certificate.
3. Set `OIM_SIP_TARGET=oim-elevenlabs-bridge` only after the ElevenLabs key and Voice ID and the OpenAI text key are configured. Use `oim-ai` to keep the OpenAI Realtime SIP route as the active destination.
4. Create `${PBX_RUNTIME_DIR}/kamailio` and `${PBX_RUNTIME_DIR}/freepbx/etc/asterisk`. These folders contain private configuration and PBX state; do not commit or upload them.
5. Configure AMI to bind to `0.0.0.0` inside the private PBX container network; do not publish TCP `5038` on the host. In `manager_custom.conf`, create the account referenced by `PBX_AMI_USERNAME` and `PBX_AMI_PASSWORD`, put its catch-all `deny` rule before the specific `permit` rule, and grant only the `command` write class needed for the fixed reload actions.
6. Copy only the PBX hostname's `fullchain.pem` and `privkey.pem` into `${PBX_RUNTIME_DIR}/tls` and `${PBX_RUNTIME_DIR}/kamailio/tls`. Keep the parent runtime directory root-only. Do not mount the host's full `/etc/letsencrypt` directory into either container. Copy the matching Kamailio config into `${PBX_RUNTIME_DIR}/kamailio/oim.cfg` and `oim-tls.cfg`. In the Docker config, bind UDP `5070` to `0.0.0.0`, bind TLS `5061` to `0.0.0.0`, advertise the host's public SIP address on `5061`, use the private `kamailio:5070` route address, and point TLS at `/etc/kamailio/tls/fullchain.pem` and `privkey.pem`.
7. Confirm the host firewall allows the four SIP/RTP entries in the table above. The `18445` admin mapping is already restricted to loopback and must stay that way.
8. Install `deploy/asterisk/oim-pbx-rtp-forwarding.sh` as `/usr/local/sbin/oim-pbx-rtp-forwarding` and install `deploy/asterisk/oim-pbx-rtp-forwarding.service.example` as `/etc/systemd/system/oim-pbx-rtp-forwarding.service`. Create `/etc/default/oim-pbx-rtp-forwarding` with the server's public interface name and the PBX container address, then run `systemctl daemon-reload` and `systemctl enable --now oim-pbx-rtp-forwarding.service`. This adds only a scoped NAT rule and an allow rule for the PBX container.

Start the services from the project root:

```sh
docker-compose -p oim-call-center-prod -f compose.yaml -f deploy/compose.telephony.yaml up --build -d
docker-compose -p oim-call-center-prod -f compose.yaml -f deploy/compose.telephony.yaml ps
```

The first FreePBX boot downloads and installs its modules and can take several minutes. Wait for the `freepbx` health check before restoring configuration. The PBX data directory and its dedicated MariaDB volume persist across container replacement.

## Panel SIP changes

The `pbx-control` container accepts an authenticated request from the OIM API, validates the SIP entries, writes only the OIM-managed PJSIP and dialplan sections, then reloads `res_pjsip.so` and the dialplan through AMI. It has access only to `/etc/asterisk` and the private AMI connection. The API does not receive a Docker socket or host sudo access.

For the ElevenLabs path, install `deploy/asterisk/oim-register-call.py` in Asterisk's AGI directory and create `/etc/oim/pbx-bridge.env` with the same `OIM_PBX_SHARED_SECRET` as the OIM API plus `OIM_API_ENDPOINT=http://api:8787/api/pbx/bridge-calls`. Keep this file readable only by Asterisk. Install `deploy/asterisk/extensions_oim_bridge.conf.example` as `extensions_oim_bridge.conf` and include it from `extensions_custom.conf`. The dialplan example connects to `api:9019` and falls back to `oim-ai` if OIM rejects call registration.

After the SIP account exists in the administrator panel, save its settings once to apply it through `pbx-control`. To migrate existing accounts automatically, call the same private `pbx-control` endpoint with the decrypted account entries after restoring the matching OIM database and encryption key. Do not place the request body or AMI output in public logs.

## Verify and maintain

Check that FreePBX and Asterisk report healthy, the SIP registrations show the expected status, Kamailio accepts a TLS handshake on `5061`, the custom dialplan is loaded, and `https://YOUR_DOMAIN/api/health` responds. A network and service check does not replace an approved end-to-end call test. Do not call a real customer without arranging the test.

Back up the OIM SQLite database with its matching `.secret` file, the PBX MariaDB database, `runtime/pbx/freepbx`, `runtime/pbx/tls`, `runtime/kamailio`, the shared `recordings` volume, and the protected environment file. The OIM API has read-only access to recordings through its supplemental Asterisk group. Keep recordings and call logs private. Install `deploy/asterisk/certbot-deploy-hook.example` as a root-only Certbot deploy hook, set its project directory, and verify its output once after setup. It copies only this PBX hostname's certificate and reloads only the PBX containers.

Use the same Compose project and both Compose files for updates. Do not run `docker system prune`, remove the PBX database volume, restart the Docker daemon, or change firewall defaults on a shared host.
