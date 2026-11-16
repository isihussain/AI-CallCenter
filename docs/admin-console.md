# Admin connections and system flow

Administrators can open **API connections** from the sidebar. Each connection has its own key, model, enabled state, and connection-check result:

| Connection | Stored provider ID | Used for |
| --- | --- | --- |
| OpenAI Realtime | `openai` | The existing SIP phone agent, including audio and tool calls |
| OpenAI AI | `openai_ai` | Text previews and the OpenAI answer engine for the optional phone bridge |
| ElevenLabs | `elevenlabs` | Scribe v3 Live phone STT, phone TTS, and panel speech previews |
| Deepgram | `deepgram` | API connection checks and Turkish Flux speech previews |

Existing Realtime settings remain under `openai`. Adding an OpenAI AI key does not replace that record. Deepgram speech previews default to `flux-dilek-tr`; model names can be changed on the Deepgram card.

## Enter credentials

1. Open the connection card and enter a model ID supported by your provider account.
2. Enter the API key. For ElevenLabs, also enter the **Voice ID** from your voice library. The initial ElevenLabs model suggestion is `eleven_flash_v2_5`; you can replace it. Deepgram uses its model field for speech synthesis: choose a `flux-` voice such as `flux-dilek-tr` for Turkish, or a supported `aura-` model. `nova-` models are speech-recognition models and cannot generate preview audio.
3. Enable the connection and save it. Keys are encrypted in SQLite using the application's existing encryption key. Keys are never returned to the browser; status responses include only a configured flag and a fixed mask.
4. Select **Check connection**. OpenAI checks the saved model, ElevenLabs checks the account endpoint and opens a Scribe v3 Live session without sending audio, and Deepgram checks the projects endpoint. These checks do not place calls or synthesize speech. Use **Try & listen** to synthesize a short audio sample with the saved ElevenLabs voice or Deepgram model. Successful API checks do not prove that the carrier route, FreePBX destination, or Realtime SIP permissions work.

Leaving the key field blank preserves its saved value. **Remove saved key** explicitly clears it. Saving settings resets the previous check result. A server-level `OPENAI_API_KEY` can still supply the existing Realtime fallback when no enabled saved key is available; the flow uses the effective Realtime configuration and identifies that environment source in the connection card. OpenAI AI, ElevenLabs, and Deepgram do not inherit that fallback.

No provider request occurs just from opening or refreshing a panel. The user enters credentials manually; installation does not create keys.

## Try text and voice

In **Try & listen**, enter a prompt and select **Generate AI response**. The server uses the enabled OpenAI AI connection, with `store: false` and a 400-token output limit. The result is editable. Select **ElevenLabs** or **Deepgram** as the speech provider, then select **Generate speech** to preview its saved model and voice.

Text prompts accept up to 1,000 characters; speech previews accept up to 500. Generation may incur provider charges. Preview and connection-check requests share a limit of six attempts per administrator per minute. Audio is returned to the browser for playback and is not saved as a recording by this application. The panel clears its temporary audio URL when another preview starts or the page closes. Provider-side retention follows the provider account's settings.

OpenAI Realtime SIP remains the existing phone route and fallback. To use ElevenLabs Scribe for live phone STT, enable the OIM AudioSocket listener and route a FreePBX inbound DID to the provided custom destination. The API connections panel reports listener and provider readiness but cannot verify the PBX route. See [the Asterisk bridge setup](elevenlabs-asterisk-bridge.md). The bridge restricts recognition to Turkish, Russian, and English; OpenAI AI generates responses and uses the existing tenant knowledge, appointment, and callback tools.

## Read the flow

The dashboard and **System flow** view show the phone path, agent tools, call records, and separate OpenAI AI → ElevenLabs/Deepgram preview paths. Select a node to see its sources, destinations, and a shortcut to the related panel.

Counters aggregate all customer accounts: active/incoming calls, calls started today in UTC, pending callbacks, and failed calls started in the last 24 hours. Configuration badges describe saved settings or the effective Realtime fallback; they are not live provider availability checks. External carrier/PBX routing is explicitly unverified. Animated dots illustrate direction, not individual packets or proof of an active connection.

The view refreshes every 30 seconds while visible. Pause, manual refresh, zoom, fit, and an accessible list view are available. A failed refresh retains the previous snapshot and marks it stale. Reduced-motion preferences stop the direction animation. Narrow screens initially use the list view.

## API endpoints

All endpoints below require an administrator session. Customer sessions receive `403`; unauthenticated requests receive `401`.

- `GET /api/admin/providers`: safe configuration metadata and blank defaults for the three primary connections.
- `POST /api/admin/providers`: saves `provider`, `model`, `enabled`, optional `api_key`, optional `voice_id`, and optional boolean `clear_key`.
- `POST /api/admin/providers/test`: checks the saved `provider`, storing `check_status` and `checked_at`.
- `POST /api/admin/ai-playground`: accepts `text`; returns generated `text` using `openai_ai`.
- `POST /api/admin/providers/preview`: accepts `provider: "elevenlabs"` and `text`; returns base64 audio and its content type.
- `GET /api/admin/system-flow`: aggregate counters and safe provider configuration, including effective Realtime and text-engine models, provider readiness, and AudioSocket listener settings.
- `POST /api/pbx/bridge-calls`: internal Asterisk call registration authenticated by `X-OIM-PBX-Secret`. It resolves the tenant from the configured called DID and checks account credit before enabling the call.

Upstream authentication, permission, model, quota, and connection errors map to fixed messages. Raw provider payloads and credentials are not sent back as diagnostics.

Reference: [OpenAI Responses text generation](https://developers.openai.com/api/docs/guides/text), [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations), and [ElevenLabs speech generation](https://elevenlabs.io/docs/api-reference/text-to-speech/convert).
