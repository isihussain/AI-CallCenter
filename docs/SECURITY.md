# Voice Platform Security

## Access control and tenant boundaries

Every administrator workspace route checks the OIM session and the administrator role. Calendar settings, appointments, tool tokens, and imported conversations are scoped to a customer tenant. The public calendar webhook resolves its tenant from an enabled token hash, not from an agent-supplied tenant ID. Post-call imports resolve ownership through the OIM assignment of the signed event's agent ID.

## Secrets and stored data

- The ElevenLabs API key uses the existing Fernet-encrypted `provider_settings` row. OIM returns only masked/configured status.
- Microsoft OAuth client credentials stay in the private server environment. OAuth access and refresh tokens are encrypted with the OIM key. Random authorization states are stored as hashes, expire after ten minutes, and are consumed once.
- A post-call signing secret can be supplied through the environment or encrypted in OIM settings. The environment value takes precedence.
- OIM calendar bearer tokens are encrypted at rest; only their SHA-256 hashes are used for request lookup.
- OIM local agent drafts and imported transcripts/summaries are encrypted with the existing OIM key.
- Provider credentials, request bodies, customer phone numbers, and request IPs are not written to voice-platform event summaries.

Back up `OIM_DB` and `OIM_SECRET` together. Restrict access to the database, environment file, logs, and backups. Do not commit API keys, webhook secrets, account data, customer transcripts, provider responses, production IPs, or access logs.

## Webhook authentication

The ElevenLabs post-call route validates the timestamped HMAC-SHA256 signature against the raw request body, rejects signatures older than 30 minutes, and deduplicates by event type, conversation, and event timestamp. Events for agents without an OIM tenant assignment are acknowledged but not imported. The request size is capped.

Calendar webhooks require the provisioned bearer token. A per-token request limit applies. Do not copy the generated tool bearer into public docs, screenshots, tickets, or provider output beyond the configured tool itself.

## Outbound URL protection

Webhook tool creation and the webhook tester require HTTPS, resolve the hostname, reject non-global addresses, and disable redirects. The tester connects to the validated address while retaining TLS hostname verification. It also caps timeouts, request sizes, and response sizes, and redacts secret-like JSON fields in response previews. Revalidate DNS and destination policy if this implementation is replaced by a proxy or asynchronous worker.

## Rate limits

The current single-process backend applies these in-memory limits:

| Request group | Limit |
| --- | ---: |
| Administrator voice-platform reads | 120 per minute per admin tenant. |
| Signed live-test URL requests | 10 per minute per admin tenant. |
| Administrator voice-platform writes | 60 per minute per admin tenant. |
| Provider test, synchronization, and calendar-tool provisioning | 10 per minute per admin tenant. |
| Calendar tool calls | 120 per minute per hashed tenant token. |
| ElevenLabs webhook deliveries | 300 per minute for the process. |

These counters are process-local and reset on restart. A multi-worker deployment needs a shared limiter before scaling out. No client IP is stored for these limits. Keep the application behind the configured HTTPS proxy and host firewall.

## Operational boundaries

Live browser tests may consume provider credits and execute the selected agent's provider-hosted webhook/system tools. Use a staging agent, test credentials, and test calendar. The browser tester does not execute client tools. Provider tools and connected Google Calendar actions are not sandboxed by OIM.

The Microsoft Outlook connection requires an Entra application and the delegated `Calendars.ReadWrite` permission. Configure its callback URI and private environment variables as described in the calendar guide. The status endpoint never returns access tokens or client credentials.
