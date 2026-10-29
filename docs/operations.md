# Operations, quality, usage, and retention

All endpoints below require an authenticated dashboard session. Customer requests always use that session's tenant, even if they include a different `tenant_id`. Administrators can select a customer where the endpoint supports it. Provider keys, SIP passwords, raw provider error payloads, and caller numbers are excluded from readiness and failure diagnostics.

## Setup readiness and greeting preview

`GET /api/readiness?tenant_id=2` reports four checks: tenant SIP credentials, an enabled OpenAI key, a saved greeting, and at least one published knowledge document. For customers, the tenant query is ignored. Administrators select a tenant with `tenant_id`.

`pbx_route` is always `unverified`: the application cannot establish carrier registration or validate an operator-specific PBX dial plan. The dashboard's text and browser-speech preview does not place a phone call or verify the synthesized voice used on a real call.

## Live call monitoring and safe failure details

`GET /api/live-calls?tenant_id=2` returns active calls and the 20 most recent failed calls for the selected tenant. The dashboard polls this endpoint while the monitoring panel is open. Failure codes map to fixed, actionable text; raw provider responses are not returned or written to application logs.

## Call reviews and quality indicators

Call history includes `review_outcome`, `review_summary`, `review_notes`, `quality_score`, `quality_coverage`, and `quality_signals` for each item. `POST /api/call-review` accepts a call ID, outcome (`resolved`, `appointment_booked`, `callback_needed`, `unresolved`, or empty), summary, and team notes. Text fields are limited to 2,000 characters. Writes must refer to a call owned by the selected tenant.

The summary draft extracts up to two caller transcript lines and the latest assistant line locally. It makes no provider request; staff can edit it before saving. The quality rubric is deterministic and uses these weighted signals: call completed (35), assistant transcript present (35), a knowledge search returned at least one result (15), and a follow-up outcome/appointment/callback was recorded (15). Unknown signals are excluded from the calculation and shown as unknown. A score is omitted until at least two signals are known; the UI shows the known-signal count. This is a review aid, not a judgment of a caller, agent, or conversation quality.

## Human callback queue

The Realtime assistant may invoke `request_human_callback` after the caller confirms a return phone number. The callback request is saved once per call, and the assistant is told to confirm it only after a successful save. This requests a later callback; it does not transfer an active SIP call.

- `GET /api/callbacks?tenant_id=2` lists that tenant's requests.
- `POST /api/callbacks/{id}/complete` marks one of the selected tenant's requests completed.

Callback requests contain customer contact details. Restrict dashboard access and apply the privacy and operational policies appropriate to the deployment.

## Usage report

`GET /api/usage-report?date_from=2026-10-01&date_to=2026-10-31&tenant_id=2` returns UTC daily totals and per-tenant totals. The inclusive date range may span at most 93 days. Customers always see their own usage; administrators can omit `tenant_id` to compare customer totals or select one tenant.

Platform credits billed and estimated OpenAI provider cost are separate fields. Provider cost is `null` when no usage estimate exists; partial estimates include only calls with provider usage records. Do not interpret missing provider measurements as zero cost.

## Transcript retention

`GET /api/privacy?tenant_id=2` returns the selected tenant's policy and last cleanup timestamp. `POST /api/privacy` accepts `{"transcript_retention_days": 90, "tenant_id": 2}`. Use `null` to keep the existing no-expiry behavior or an integer from 1 through 3,650. The customer panel offers common durations and requires the user to acknowledge deletion before saving a policy.

Run `python oim-mvp/purge_transcripts.py` from the deployment checkout as the application service user. It reads the same `OIM_DB` and `OIM_SECRET` environment settings as the API. For the supplied systemd deployment, install the example service and timer as follows:

~~~sh
sudo cp deploy/ai-call-center-retention.service.example /etc/systemd/system/ai-call-center-retention.service
sudo cp deploy/ai-call-center-retention.timer.example /etc/systemd/system/ai-call-center-retention.timer
sudo systemctl daemon-reload
sudo systemctl enable --now ai-call-center-retention.timer
sudo systemctl start ai-call-center-retention.service
sudo journalctl -u ai-call-center-retention.service --no-pager
~~~

The timer runs daily at 03:15 local server time and catches up after downtime. Cleanup is idempotent. It clears transcript content plus the related review summary and notes for ended or failed calls older than the configured number of days. It preserves call metadata, billing, and usage records. It does not remove recordings stored outside this application by Asterisk or another PBX; configure recording retention separately with the PBX operator.
