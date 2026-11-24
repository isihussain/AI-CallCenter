# ElevenLabs Integration

OIM connects to the ElevenLabs Conversational AI API from the Python backend. The administrator workspace uses real provider requests for agents, tools, knowledge documents, conversations, tests, usage data, and agent versioning. Provider responses remain subject to the API key's permissions and the account's plan.

## Configure the connection

1. Sign in as an OIM administrator and open **Voice Agents → Integrations**.
2. Enter an ElevenLabs API key, choose a default TTS model and voice, then save.
3. Use **Test connection**. OIM checks the authenticated workspace endpoints and reports permission or provider errors.
4. Use **Load voices** and **Models** to load options supported by the connected account.

The key is encrypted with OIM's existing Fernet key in `provider_settings`. It is never returned by the API or stored in browser state. Keep the OIM encryption key and database backups together. The API key is configured in the administrator panel; there is no ElevenLabs key variable in the public environment examples.

The connected key should have only the permissions needed for the enabled features. Some workspace, analytics, model, voice, test, or conversation endpoints may be unavailable to a restricted key. OIM reports unavailable results instead of filling them with sample data.

## Agent and resource synchronization

The **Voice Agents** screen lists provider agents and supports create, edit, duplicate, delete, tenant assignment, local drafts, pull, push, branches, merge, restore, deployment allocation, and provider tests. Quick voice controls select an account voice and TTS model and set the documented language, stability, similarity, speed, streaming-latency, and output-format fields. **Apply settings to JSON** preserves the rest of the provider configuration in the editor. Pull before editing a remotely changed configuration. Push uses the last imported provider hash; a changed provider configuration returns a conflict and does not silently overwrite it.

Use **Tools** to create or edit provider tool definitions and **Knowledge Base** to create text, URL, or file documents and attach them to agents. Use **Conversations** to page through provider conversations and open details. **Analytics** and the integration summary request user, subscription, usage, voice, model, and LLM data when the key permits it.

`sync` refreshes supported provider resources that OIM tracks. It does not mirror every resource or setting available in the ElevenLabs dashboard. Code tools, MCP server setup, workspace membership, billing changes, and provider-only controls remain in the provider workspace.

## Live browser test

The agent editor requests a short-lived signed conversation URL from OIM's server, then opens an authenticated ElevenLabs WebSocket from the browser. The ElevenLabs API key stays on the server. The browser requests microphone access only after an administrator selects an agent and starts a test. It shows user transcripts, agent replies, streamed audio, and provider tool events. It also allows text messages during the live session.

The signed URL is temporary and is not stored. The interface defaults to `staging`; an operator may select `production`. The confirmation checkbox warns that the provider may charge credits and assigned webhook tools may change live data. Use a staging agent with a test calendar for safe validation. The OIM live tester does not execute client-side tools; it returns an explicit unsupported result for those calls. Provider-hosted webhook and system tools follow their provider behavior.

The live test needs a modern browser, microphone permission, and an HTTPS OIM origin. It converts microphone audio to the format reported by the agent, including signed PCM formats and `ulaw_8000`. If the agent requires public access, keep the agent's domain allowlist and authentication settings aligned with the OIM origin.

## Post-call imports

Configure an ElevenLabs post-call webhook for the `post_call_transcription` event at:

```text
https://YOUR_PUBLIC_HOST/api/webhooks/elevenlabs
```

Set its signing secret either in the OIM **Settings** screen or in the server environment as `ELEVENLABS_WEBHOOK_SECRET`. The environment value takes precedence. The endpoint verifies the provider's timestamped HMAC signature, rejects stale signatures, deduplicates events, and imports a conversation only when its agent has an OIM customer assignment. Transcripts and summaries are encrypted at rest. Imported calls are visible only in the assigned tenant's OIM admin view.

Keep the public base URL in `OIM_PUBLIC_URL` as a public HTTPS origin. OIM uses it to build the webhook URL when provisioning its calendar tools. The examples use placeholder hostnames; replace them only in private deployment configuration.

## API routes

The administrator UI uses `/api/admin/voice-platform/*`. These routes require an OIM administrator session. See [API Reference](API_REFERENCE.md) for the route catalog and [Security](SECURITY.md) for authorization, rate limits, and webhook validation.

## Provider references

- [ElevenLabs Conversational AI API](https://elevenlabs.io/docs/api-reference/overview)
- [Agent API and configuration](https://elevenlabs.io/docs/api-reference/agents/create)
- [WebSocket conversations](https://elevenlabs.io/docs/eleven-agents/libraries/web-sockets)
- [Agent authentication and signed URLs](https://elevenlabs.io/docs/eleven-agents/customization/authentication)
- [Post-call webhooks](https://elevenlabs.io/docs/eleven-agents/workflows/post-call-webhooks)
