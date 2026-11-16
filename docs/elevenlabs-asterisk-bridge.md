# ElevenLabs Scribe with Asterisk AudioSocket

This optional phone route streams Asterisk caller audio to ElevenLabs Scribe v3 Live, sends final transcripts to the existing OpenAI text agent, and plays ElevenLabs speech back into the call. The OpenAI agent keeps the tenant knowledge search, appointment booking, and human callback tools. The current OpenAI Realtime SIP route remains available as a separate fallback.

The live transcription session is restricted to Turkish, Russian, and English and enables Scribe's multilingual mode. Asterisk AudioSocket carries signed 16-bit mono PCM at 8 kHz, which Scribe accepts directly. ElevenLabs TTS returns 8 kHz μ-law; OIM converts it to the PCM format Asterisk expects.

## Requirements

- Asterisk 18 or newer with the `AudioSocket()` dialplan application loaded.
- OIM and Asterisk on the same host for the default loopback listener. If they run on separate hosts, use a private network address, restrict TCP port `9019` to the PBX, and change both listener and dialplan addresses.
- An enabled ElevenLabs provider with a valid API key and a voice ID that supports Turkish, Russian, and English. The provider's model field is used for speech synthesis; `eleven_flash_v2_5` is the default when it is blank.
- An enabled OpenAI AI connection with a model that supports chat completions and function tools, or a configured OpenAI Realtime key/environment fallback. The fallback uses `gpt-4.1-mini` for text responses.
- A tenant SIP record whose **DID** or SIP username matches the number Asterisk passes from `${FROM_DID}`.

## Enable the OIM listener

Create a random shared secret and store it in the protected OIM service environment:

```text
OIM_AUDIOSOCKET_ENABLED=1
OIM_AUDIOSOCKET_HOST=127.0.0.1
OIM_AUDIOSOCKET_PORT=9019
OIM_PBX_SHARED_SECRET=<same-random-secret-as-the-AGI-config>
```

Use a long random value, for example 32 random bytes encoded as hexadecimal. Restart the OIM service after changing its environment. The backend refuses to start the bridge if it is enabled without the shared secret.

Save the same secret for the Asterisk AGI script in `/etc/oim/pbx-bridge.env`, owned by `root:asterisk` with mode `0640`:

```text
OIM_PBX_SHARED_SECRET=<same-random-secret-as-the-OIM-service>
```

The AGI script sends the secret only to OIM over loopback. The registration endpoint resolves the tenant from the called DID; it does not accept a tenant ID from Asterisk. It checks provider configuration, account status, and minimum call credit before registering the AudioSocket UUID.

## Install the AGI and dialplan context

Copy `deploy/asterisk/oim-register-call.py` to the Asterisk AGI directory, usually `/var/lib/asterisk/agi-bin/oim-register-call.py`. Make it executable and ensure the Asterisk user can read it. Copy `deploy/asterisk/extensions_oim_bridge.conf.example` to `/etc/asterisk/extensions_oim_bridge.conf`, then include this line in `/etc/asterisk/extensions_custom.conf`:

```text
#include extensions_oim_bridge.conf
```

Reload the FreePBX dialplan. In FreePBX, create a **Custom Destination** with target:

```text
oim-elevenlabs-bridge,s,1
```

Assign that custom destination to the inbound route for the DID you want to migrate. The context uses `${FROM_DID}` to resolve the OIM tenant. Check that this variable contains the full called DID on your trunk. Keep the previous OpenAI Realtime destination available so the route can be switched back quickly.

The sample context answers the call and starts `AudioSocket()` on loopback port `9019`. It does not change other inbound routes or rewrite SIP accounts.

## Configure the panel and confirm readiness

1. In **API connections**, save and enable the ElevenLabs key and Voice ID. Select **Check connection**; this checks the account and opens a Scribe v3 Live session without sending caller audio.
2. Enable an OpenAI AI model suitable for function calling, or keep the existing OpenAI Realtime key enabled for the text-engine fallback.
3. Open **API connections** and confirm the AudioSocket listener reports ready. This confirms OIM settings and credentials; it cannot confirm the FreePBX inbound route.
4. Place one controlled call to the migrated DID. Confirm the opening greeting, Turkish/Russian/English recognition, a knowledge-base answer, and one appointment or callback action.

Scribe and TTS usage is billed by ElevenLabs. Scribe charges for streamed audio, including silence. Provider retention follows the ElevenLabs account settings; OIM stores the committed transcript in the tenant's call history.

## Roll back

Change the selected FreePBX inbound route back to its previous OpenAI Realtime destination. After no inbound routes use the bridge, set `OIM_AUDIOSOCKET_ENABLED=0` and restart OIM. This leaves the existing Realtime SIP path intact.

## Official references

- [Asterisk AudioSocket application](https://docs.asterisk.org/Latest_API/API_Documentation/Dialplan_Applications/AudioSocket/)
- [Asterisk AudioSocket protocol](https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/)
- [ElevenLabs realtime STT API](https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime)
- [ElevenLabs realtime language options](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/language-options)
- [ElevenLabs streaming TTS API](https://elevenlabs.io/docs/api-reference/text-to-speech/stream)
