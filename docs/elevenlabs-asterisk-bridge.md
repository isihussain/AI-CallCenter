# ElevenLabs Scribe with Asterisk AudioSocket

This optional phone route streams Asterisk caller audio to ElevenLabs Scribe v3 Live, sends final transcripts to the existing OpenAI text agent, and plays ElevenLabs speech back into the call. The OpenAI agent keeps the tenant knowledge search, appointment booking, and human callback tools. The current OpenAI Realtime SIP route remains available as a separate fallback.

The live transcription session is restricted to Turkish, Russian, and English and enables Scribe's multilingual mode. Asterisk AudioSocket carries signed 16-bit mono PCM at 8 kHz, which Scribe accepts directly. ElevenLabs TTS returns 8 kHz μ-law; OIM converts it to the PCM format Asterisk expects.

## Requirements

- Asterisk 18 or newer with the `AudioSocket()` dialplan application loaded.
- OIM and Asterisk on the same host or a private network. In the Docker telephony deployment, bind the listener to the OIM API address on the private Compose network and use `api:9019` from Asterisk. Do not publish TCP `9019` on the host.
- An enabled ElevenLabs provider with a valid API key and a voice ID that supports Turkish, Russian, and English. The provider's model field is used for speech synthesis; `eleven_flash_v2_5` is the default when it is blank.
- An enabled OpenAI AI connection with a model that supports chat completions and function tools, or a configured OpenAI Realtime key/environment fallback. The fallback uses `gpt-4.1-mini` for text responses.
- A tenant SIP record whose **DID** or SIP username matches the number Asterisk passes from `${FROM_DID}`.

## Enable the OIM listener

Create a random shared secret and store it in the protected OIM service environment:

```text
OIM_AUDIOSOCKET_ENABLED=1
OIM_AUDIOSOCKET_HOST=<private-OIM-address>
OIM_AUDIOSOCKET_PORT=9019
OIM_PBX_SHARED_SECRET=<same-random-secret-as-the-AGI-config>
```

Use a long random value, for example 32 random bytes encoded as hexadecimal. Restart the OIM service after changing its environment. The backend refuses to start the bridge if it is enabled without the shared secret.

Save the same secret for the Asterisk AGI script in `/etc/oim/pbx-bridge.env`, owned by `root:asterisk` with mode `0640`:

```text
OIM_PBX_SHARED_SECRET=<same-random-secret-as-the-OIM-service>
OIM_API_ENDPOINT=http://api:8787/api/pbx/bridge-calls
```

The AGI script sends the secret only to OIM over the private container network. The registration endpoint resolves the tenant from the called DID; it does not accept a tenant ID from Asterisk. It checks provider configuration, account status, and minimum call credit before registering the AudioSocket UUID.

## Install the AGI and dialplan context

Copy `deploy/asterisk/oim-register-call.py` to the Asterisk AGI directory, usually `/var/lib/asterisk/agi-bin/oim-register-call.py`. Make it executable and ensure the Asterisk user can read it. Copy `deploy/asterisk/extensions_oim_bridge.conf.example` to `/etc/asterisk/extensions_oim_bridge.conf`, then include this line in `/etc/asterisk/extensions_custom.conf`:

```text
#include extensions_oim_bridge.conf
```

Reload the FreePBX dialplan. In FreePBX, create a **Custom Destination** with target:

```text
oim-elevenlabs-bridge,s,1
```

Assign that custom destination to the inbound route only if the carrier route does not already enter the OIM `from-verimor` context. In the Docker deployment, set `OIM_SIP_TARGET=oim-elevenlabs-bridge`; the private PBX control service applies that target when the SIP settings are saved. The context uses the full called DID to resolve the OIM tenant. Keep the previous OpenAI Realtime destination available so the route can be switched back quickly.

The sample context answers the call and starts `AudioSocket()` at `api:9019` on the private Compose network. If call registration fails before answering, it sends the call to the existing `oim-ai` Realtime context.

## Configure the panel and confirm readiness

1. In **API connections**, save and enable the ElevenLabs key. Select **Check connection**; this opens a Scribe v3 Live STT session without sending audio. The check needs no Voice ID or TTS model and does not synthesize speech. It verifies Scribe connectivity only.
2. If you use the current bridge's ElevenLabs phone TTS, configure its Voice ID and TTS model separately. **Try & listen** can test speech synthesis. The Scribe connection result does not verify outbound phone audio.
3. Enable an OpenAI AI model suitable for function calling, or keep the existing OpenAI Realtime key enabled for the text-engine fallback.
4. Open **API connections** and confirm the AudioSocket listener reports ready. This confirms OIM settings and credentials; it cannot confirm the FreePBX inbound route or successful TTS playback.
5. Place one controlled call to the migrated DID. Confirm the opening greeting, Turkish/Russian/English recognition, a knowledge-base answer, and one appointment or callback action.

Live Scribe and TTS usage follows the ElevenLabs account terms. Scribe processes the streamed call audio, including silence. Provider retention follows the ElevenLabs account settings; OIM stores the committed transcript in the tenant's call history.

## Roll back

Change the selected FreePBX inbound route back to its previous OpenAI Realtime destination. After no inbound routes use the bridge, set `OIM_AUDIOSOCKET_ENABLED=0` and restart OIM. This leaves the existing Realtime SIP path intact.

## Official references

- [Asterisk AudioSocket application](https://docs.asterisk.org/Latest_API/API_Documentation/Dialplan_Applications/AudioSocket/)
- [Asterisk AudioSocket protocol](https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/)
- [ElevenLabs realtime STT API](https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime)
- [ElevenLabs realtime language options](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/language-options)
- [ElevenLabs streaming TTS API](https://elevenlabs.io/docs/api-reference/text-to-speech/stream)
