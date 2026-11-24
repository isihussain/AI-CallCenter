# Agent Configuration

ElevenLabs is the source of truth for live agent settings. OIM stores the most recently imported provider configuration and an optional local draft so an administrator can compare and review changes before publishing.

## Editor and supported configuration

The **Voice Agents** screen uses the provider-shaped JSON returned by the agent API. This preserves supported fields that OIM does not have a dedicated control for, including:

- name, tags, workflow, and procedures;
- conversation language, first message, prompt, dynamic variables, and data collection;
- voice ID, model, voice settings, audio format, and pronunciation dictionaries;
- LLM model/provider settings, temperature, context, and response behavior;
- turn timing, interruption, noise, speech recognition, call limits, handoff, and transfer settings;
- privacy, recording, retention, guardrails, and platform controls;
- tool IDs, knowledge-base attachments, and conversation overrides.

Provider support and writable fields vary. The JSON editor keeps unknown fields in local drafts; the provider decides whether a field is valid when the agent is created or updated. OIM does not claim an API-only field works unless the provider accepts it. Voice preview is a separate TTS request that can use the voice selected in Integrations.

OIM can insert a marked calendar-safety block into `conversation_config.agent.prompt.prompt`. This only edits the visible draft. Review and push the draft explicitly to change the live agent.

## Compare, pull, and push

1. Select the agent and choose **Pull from ElevenLabs** to refresh OIM's remote baseline.
2. Edit the JSON or save a local draft.
3. Use **Compare editor with provider** to view changed paths and values. Credential-like fields are represented as configured/empty states in the diff.
4. Use **Push to ElevenLabs** to write the draft. OIM sends the baseline hash; if the provider changed since that baseline, OIM returns HTTP 409 with the conflict versions.

The local draft is encrypted in the OIM database. A provider configuration update is audited. The current page offers a JSON editor and a voice preview; it does not provide dedicated sliders/selects for every voice, LLM, turn-taking, privacy, and conversation parameter. Use the JSON editor for those settings and let ElevenLabs validate them.

## Versions and traffic

The editor uses the documented provider operations for branches, merge previews, merges, versions, deployments, and restore-as-new-version. Merge, restore, and live traffic allocation require explicit confirmation. Restore creates a new provider version; it does not rewrite immutable version history. Deployment percentages must sum to 100%.

## Live and automated testing

The agent page provides two test paths:

- **Provider tests:** Create test scenarios and run them through the ElevenLabs testing API. Tool execution must be acknowledged before a run.
- **Live browser test:** Connect to a short-lived signed WebSocket URL with microphone or text input. This uses the provider agent and its configured tools; select the staging environment and a test agent/calendar to avoid production effects.

The live browser tester displays provider tool events but does not execute application client tools. Simulated provider tests and live audio sessions may consume account credits.
