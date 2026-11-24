# OIM Voice Agent Platform — ISA

## Intent

Extend the existing OIM SaaS application into an administrator-operated voice-agent workspace using its existing Python HTTP API, SQLite database, static dashboard, encryption key and Docker deployment. Keep the existing customer portal and telephone paths working. Treat the existing OIM dashboard as the visual reference.

## Decisions

- Use the ElevenLabs Conversational AI API only for capabilities supported by its current API. Store the API key through the existing Fernet-encrypted provider settings.
- Keep OIM as the authoritative store for tenant ownership, calendar rules, internal tools, assignments, audit entries and synchronization history.
- Require administrator authorization for workspace-wide ElevenLabs resources. Keep customer records and appointments tenant-scoped.
- Make external changes explicit. Pull, push, publish, restore and delete actions must show their target and report provider failures without losing local state.
- Treat calendar writes as transactions with overlap checks and idempotency. A booking is confirmed only after a successful reservation.
- Reject unsafe outbound tool destinations, redirects and private-network targets. Never log secrets or full tool payloads by default.
- Preserve the current dashboard design system and Turkish, English and Russian language support.

## Criteria

| ID | Criterion | Eval |
| --- | --- | --- |
| VA-01 | Existing provider settings remain encrypted and the ElevenLabs integration never returns an API key to the browser. | API assert |
| VA-02 | Administrators can test ElevenLabs connectivity and view workspace, subscription, quota, voice and model data when the provider API permits it; unsupported or unauthorized fields are shown as unavailable. | API assert + UI review |
| VA-03 | Administrators can import, create, edit, duplicate, archive or delete agents through supported ElevenLabs endpoints, with local tenant ownership and audit records. | API assert |
| VA-04 | Agent configuration supports conversation, voice, language, prompt, dynamic variable, platform and tool fields through validated provider-shaped JSON; the editor never silently drops unknown provider fields. | API assert |
| VA-05 | Local and remote agent configurations can be compared and pulled or pushed explicitly; conflicts are surfaced without automatic overwrite. Supported branches and versions use the documented API. | API assert |
| VA-06 | The Tools module manages supported webhook, client, system and internal OIM tools, schemas, authentication, enabled state, agent assignments, tests and usage metrics. Unsupported code/MCP capabilities are identified as provider-managed rather than simulated. | API assert + UI review |
| VA-07 | Outbound tool tests validate method, schema, URL, DNS-resolved addresses, timeout, response size and redirects; requests to private, loopback, link-local or reserved networks are rejected. Secrets are encrypted and redacted. | API assert |
| VA-08 | Internal calendar tools expose structured current-time, availability, slot search, alternatives, book, find, reschedule, cancel, working-hours and staff-availability responses without exposing other customers' data. | API assert |
| VA-09 | Calendar rules support tenant time zone, staff, working days/hours, breaks, duration, buffers, advance limits, holidays and blocked intervals, with Europe/Istanbul defaults. | API assert |
| VA-10 | Concurrent or retried booking requests cannot create overlapping confirmed appointments; the backend rechecks availability in a write transaction and honors idempotency keys. | Concurrency test |
| VA-11 | Unavailable requested slots return nearby alternatives in the configured order; the backend never reports availability without checking stored and connected-calendar conflicts. | API assert |
| VA-12 | OIM knowledge items can be scoped to agents and synced to/from the ElevenLabs Knowledge Base using supported text, URL and file endpoints. Unsupported file parsing is reported clearly. | API assert |
| VA-13 | ElevenLabs conversations can be paged, opened and imported; signed post-call events are verified and deduplicated before tenant-scoped conversation data is stored. | API assert |
| VA-14 | The admin UI provides Voice Agents, Tools, Calendar, Knowledge Base, Conversations, Integrations and Analytics destinations using existing responsive components and real API state. | UI review |
| VA-15 | The live test area supports safe text simulation and exposes provider/tool timing and errors; any audio mode uses a test environment and does not mutate production appointments by default. | API assert + UI review |
| VA-16 | New routes are administrator-protected, tenant isolation is enforced, mutations are audited, webhook authentication is verified, and errors do not include keys or customer secrets. | Security tests |
| VA-17 | The seven requested technical guides document real endpoints, configuration, limitations, operations and test procedures without production identifiers or secrets. | Document review |
| VA-18 | Automated tests cover the requested calendar edge cases, concurrency/idempotency, permissions, provider errors, tool authorization, localization and synchronization conflicts. | Test suite |
| VA-19 | Existing API and dashboard regression suites pass, and the Docker production update preserves existing OIM, PBX and neighboring host services. | Regression + deployment health |

## Status

- phase: implemented-local; validation complete
- progress: automated checks pass (65 Python tests, 15 dashboard tests, JavaScript syntax check); provider staging and production deployment evidence remain to be recorded
- acceptance: pending remote ElevenLabs staging verification and isolated VPS deployment
- inferred scope: Microsoft Outlook OAuth is conditional on operator-provided Microsoft application credentials; provider-only features are exposed only when supported by the account/API.
