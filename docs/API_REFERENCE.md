# Voice Platform API Reference

All `/api/admin/voice-platform/*` endpoints require an active OIM administrator session. They use same-origin JSON requests and return JSON. Tenant-specific operations require a valid customer `tenant_id`. The OIM API key remains server-side.

## GET routes

| Route | Purpose |
| --- | --- |
| `/status` | Key configured/enabled state, provider status, webhook readiness, and webhook URL. No secret value is returned. |
| `/events` | Recent OIM synchronization and webhook event summaries. |
| `/agents` | Page and search provider agents; includes OIM assignment/sync metadata. |
| `/agents/{id}` | Read provider agent configuration. Optional provider branch/version query fields are passed through. |
| `/agents/{id}/local` | Read the encrypted OIM remote baseline and local draft. |
| `/agents/{id}/branches`, `/branches/{branch}` | Read branches and branch details. |
| `/agents/{id}/branches/{branch}/merge-preview?target_branch_id={id}` | Preview a merge. |
| `/agents/{id}/deployments` | Read traffic allocations. |
| `/agents/{id}/versions?version_id={id}` | Read a provider version. |
| `/tools` | Page provider tools. |
| `/tools/{id}/dependent-agents` | List agents that use a tool. |
| `/tools/{id}/executions` | Read provider tool execution records. |
| `/voices`, `/models`, `/llms` | Read provider voice, TTS model, and conversational LLM options. |
| `/knowledge` | Page provider knowledge documents. |
| `/knowledge/{id}/dependent-agents` | Read agent dependencies for a knowledge document. |
| `/conversations` and `/conversations/{id}` | Page and read provider conversation details. |
| `/analytics` | Read user, subscription, usage, and provider availability errors. |
| `/tests` | Page provider test scenarios. |
| `/calendar?tenant_id={id}` | Read tenant calendar rules. |
| `/calendar/appointments?tenant_id={id}&date=YYYY-MM-DD&view=day\|week\|month` | Read up to 500 tenant appointments in a period. |
| `/calendar/availability`, `/calendar/slots`, `/calendar/alternatives` | Check tenant calendar availability and options. |
| `/imported-conversations?tenant_id={id}` | List tenant-assigned post-call imports. |
| `/imported-conversations/{conversation_id}` | Read a stored encrypted transcript after tenant assignment. |
| `/conversation-signed-url?agent_id={id}` | Obtain a temporary signed URL for the admin live test. |

Query values are URL-encoded. Provider pagination uses the provider's cursor and page-size fields where applicable.

## POST routes

| Route | Body or effect |
| --- | --- |
| `/calendar` | `{ "tenant_id": 12, "settings": { ... } }` — validate and save tenant rules. |
| `/calendar/book` | `{ "tenant_id": 12, "appointment": { ... }, "call_id": "..." }` — transactionally recheck and book. |
| `/calendar-tools` | `{ "tenant_id": 12, "agent_id": "..." }` — provision tenant-scoped provider tools. |
| `/tools/test` | `{ "url": "https://example.org/path", "method": "POST", "headers": {}, "body": {} }` — validated webhook test. |
| `/webhook-secret` | `{ "secret": "..." }` — encrypt or clear the post-call signing secret. |
| `/connection-test` | Check provider connection. |
| `/sync` | Refresh supported OIM-tracked provider resources. |
| `/agents` | `{ "config": { "conversation_config": {} }, "tenant_id": 12 }` — create agent. |
| `/agents/{id}` | `{ "config": { ... } }` — update agent; `{ "action": "delete", "confirm_delete": true }` deletes it. |
| `/agents/{id}/local` | `{ "config": { ... } }` — save an encrypted local draft. |
| `/agents/{id}/pull`, `/push` | Pull provider state or hash-guarded push of a local draft. |
| `/agents/{id}/tenant` | `{ "tenant_id": 12 }` — assign the agent for OIM imports. |
| `/agents/{id}/clone` | `{ "name": "...", "tenant_id": 12 }` — duplicate provider agent. |
| `/agents/{id}/tools` | `{ "tool_ids": ["..."] }` — update agent tool assignment. |
| `/agents/{id}/knowledge` | `{ "documents": [{ "id": "...", "type": "text\|file\|url", "name": "...", "usage_mode": "auto" }] }`. |
| `/agents/{id}/branches` | Create a provider branch. |
| `/agents/{id}/branches/{source}/merge` | `{ "target_branch_id": "...", "confirm_merge": true }`. |
| `/agents/{id}/deployments` | `{ "deployments": [{ "branch_id": "...", "percentage": 100 }], "confirm_deployment": true }`. |
| `/agents/{id}/restore` | `{ "version_id": "...", "branch_id": "...", "confirm_restore": true }`. |
| `/tools` | `{ "tool_config": { ... } }` — create tool. |
| `/tools/{id}` | `{ "tool_config": { ... } }` — update shared tool. |
| `/tools/{id}/delete` | `{ "confirm_delete": true, "confirm_shared_delete": true }` after dependency review. |
| `/knowledge` | Create a text, URL, or supported file document. File content is base64 encoded in the authenticated request. |
| `/knowledge/{id}/delete` | `{ "confirm_delete": true }` after dependency review. |
| `/tests` | `{ "test": { ... } }` — create a provider test scenario. |
| `/run-tests/{agent_id}` | `{ "tests": [...], "confirm_external_tools": true }` — run provider tests. |

Provider mutations can return provider-specific errors. A local HTTP 409 on push indicates an agent version conflict. HTTP 429 indicates an OIM rate limit. An unavailable feature or permission remains unavailable rather than being simulated.

## Public webhooks

```text
POST /api/webhooks/elevenlabs
POST /api/webhooks/oim-calendar/{operation}
```

The post-call route verifies the provider signature. Calendar tools require the provisioned tenant bearer token and use the trusted conversation-ID header for idempotency. Neither endpoint is an administrator browser route.

## Calendar OAuth

`GET /api/google/start` and `GET /api/microsoft/start` require the customer session that owns the calendar. They return a provider authorization URL. The callbacks exchange the authorization code server-side and store encrypted tokens. `GET /api/google/status` and `GET /api/microsoft/status` return configured/connected flags only. Microsoft OAuth additionally requires server-side `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_TENANT_ID` values.
