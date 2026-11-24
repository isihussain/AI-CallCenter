# Tools System

OIM's **Tools** screen manages tool resources through the ElevenLabs API. Tool definitions are provider resources and may be shared across several agents. OIM shows dependent agents before deleting a shared tool. Agent assignments are saved on the agent's provider configuration.

## Tool definitions

The JSON editor accepts provider-shaped tool configuration. Use it to create or edit the tool types supported by the connected ElevenLabs account, including webhook, client, system, code, and MCP tool configurations. OIM does not implement a second execution engine for provider-hosted code or MCP tools. MCP server registration and client-tool implementations remain provider/application responsibilities.

The visual builder collects a tool's name, description, type, HTTPS endpoint, and HTTP method. The provider-shaped JSON editor carries parameter schemas, request/response configuration, headers, and other supported fields. ElevenLabs workspace authentication connections are managed by ElevenLabs and are referenced only where the provider schema supports them. The UI supports create, edit, duplicate, delete, dependent-agent lookup, webhook testing, per-agent enable/disable, tool execution history, and assignment to an agent. Enable/disable attaches or removes the tool ID from the selected agent; it does not disable a shared provider tool for other agents. The provider validates the configuration when it is saved. Use the provider response to confirm whether the current account accepts a field or tool type.

## Webhook tools

Webhook URLs must use HTTPS and resolve only to globally routable addresses. OIM rejects local, private, loopback, link-local, reserved, and otherwise non-public IP addresses. The tester pins requests to the validated DNS result, preserves TLS hostname verification, disables redirects, caps timeouts and response size, and redacts credential-like fields from JSON previews.

The tester accepts GET, POST, PUT, PATCH, and DELETE. It sends the supplied method, headers, and JSON body to the configured endpoint. Use a non-production endpoint and synthetic request data. The tester is rate limited and is intended for administrator troubleshooting; it is not an execution proxy for end-user requests.

## OIM calendar tools

**Add 10 OIM calendar tools** creates tenant-scoped ElevenLabs webhook tools:

| Tool | Operation |
| --- | --- |
| `get_current_datetime` | Read current time and calendar timezone. |
| `check_availability` | Check a requested time against OIM and a connected Google Calendar. |
| `get_available_slots` | List free slots for a date and optional staff member. |
| `find_alternative_slots` | Return the nearest available options. |
| `book_appointment` | Reserve a slot after customer confirmation. |
| `find_appointment` | Find an appointment after phone verification. |
| `reschedule_appointment` | Move a verified appointment after a fresh availability check. |
| `cancel_appointment` | Cancel a verified appointment. |
| `get_business_hours` | Return tenant working hours, holidays, timezone, and buffers. |
| `get_staff_availability` | List slots for a selected staff member. |

Each tool uses an encrypted tenant token, stored as a hash for lookup, and calls `/api/webhooks/oim-calendar/{operation}`. Provisioning attaches the tools to the selected agent when an agent is selected. An OIM conversation ID is bound through the trusted provider system variable and used as the booking idempotency key. Tool responses are structured JSON; the agent should explain results naturally and must not expose another customer's data.

The tool assignment list is provider-owned. Calendar tools use real OIM, Google Calendar, or Microsoft Outlook data when the relevant integration is configured. The system fails closed when a selected connected calendar cannot verify availability. Booking tools accept optional service and department rules and can create explicit daily or weekly recurrence series with a bounded number of occurrences.

## Execution history and metrics

The Tools screen requests the selected tool's latest 100 execution records and dependent agents. It shows observed calls, success/error counts, average provider latency, last use, and assigned agents. The API is paginated, so these counts describe the returned sample, not lifetime totals, when `has_more` is true. A response with no execution records is shown as empty; OIM does not estimate missing data. See [Get tool executions](https://elevenlabs.io/docs/api-reference/tools/get-executions) and the [ElevenLabs tools guide](https://elevenlabs.io/docs/eleven-agents/customization/tools) for current fields and account permissions.

## Shared-tool changes

Before deleting a tool, OIM queries dependent agents and requires confirmation. Updating a tool changes the provider resource shared by its assigned agents. Review the dependent-agent list before saving changes that could alter live calls.
