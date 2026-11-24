# Voice Platform Testing

## Automated checks

Install Python dependencies and run the full API suite from the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s oim-mvp/tests -v
```

Install dashboard dependencies and run the browser-side checks:

```bash
pnpm install --frozen-lockfile
pnpm test
node --check oim-ui/voice-platform.js
```

The ElevenLabs and calendar tests use temporary SQLite databases and synthetic data. Provider HTTP calls are mocked. The current suite contains 65 Python tests and 15 dashboard tests. They cover:

- API key access, signed-URL route authorization, no key returned to the browser, and per-admin live-test rate limits;
- signed post-call signature verification, tenant mapping, encrypted transcript/summary storage, and event deduplication;
- available, occupied, and nearby appointment times; a single one-hour alternative; a full day that advances to the next open day; closed-day holidays and spoken time ranges;
- concurrent booking, retry idempotency, external calendar failure, weekly recurring reservations with compensating cancellation, saved-provider cancellation, normalized phone verification, staff allow-lists, service duration bounds/capacity, staff hours, holidays, timezone parsing, and ambiguous TR/EN/RU input;
- Microsoft OAuth state, encrypted tokens, Graph availability/reservation/cancellation/reschedule, and disconnected-provider failure handling;
- day, week, and month calendar views and invalid view parameters;
- existing OIM authentication, customer isolation, admin forms, SIP bridge, OpenAI Realtime opening, and dashboard regressions.

No automated test places a telephone call, requests microphone access, changes a real provider resource, or contacts Google/ElevenLabs.

## Manual staging checklist

1. Configure the ElevenLabs API key through the admin Integrations panel and run **Test connection**.
2. Load voices/models and confirm permission failures are clearly reported.
3. Import a test agent, save a local draft, compare it with the provider configuration, then push a harmless test edit.
4. Create a test webhook tool with a controlled public HTTPS endpoint. Confirm a private or loopback destination and a redirect are rejected.
5. Configure a staging agent and a staging calendar. Provision its ten OIM calendar tools and verify assignments in the provider response.
6. Open the calendar with a synthetic tenant. Test an open slot, a busy slot, alternatives, a full day, a holiday, a staff schedule, service rules, a Google Calendar outage, and an Outlook/Graph outage if those providers are connected.
7. Start the browser live test in **staging**. Grant microphone access, say a short test phrase, send a text message, and review transcript, audio, and tool events. Use the confirmation checkbox only after validating the agent and tool endpoints.
8. Configure the post-call webhook and signing secret in a staging environment. Complete a test conversation, then verify the assigned tenant sees one imported conversation and repeated event delivery does not create a duplicate.
9. Check the tool execution endpoint and provider analytics. Treat missing plan permissions as unavailable provider data.

## Production acceptance

Before routing customer calls, confirm that `OIM_PUBLIC_URL` is a public HTTPS origin, webhook verification succeeds, tenant assignments are correct, the provider account's permissions cover all required routes, and a backup of the database and OIM encryption key exists. Verify Google Calendar and Microsoft Outlook reservations and cancellation/reschedule behavior with dedicated test calendars first.

Do not use public GitHub issues or screenshots to share provider credentials, customer names, phone numbers, transcripts, API responses, public server IPs, or logs.
