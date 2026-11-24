# Calendar Engine

OIM stores tenant calendar rules and internal appointments in SQLite. Calendar writes are made in a `BEGIN IMMEDIATE` transaction, recheck availability within that transaction, and use a tenant-scoped unique idempotency key. A booking is confirmed only after internal and configured external calendar checks succeed.

## Tenant settings

Each tenant has one `calendar_settings` JSON record. The default timezone is `Europe/Istanbul`, with weekday hours of 09:00–17:00. Supported fields include:

| Setting | Purpose |
| --- | --- |
| `timezone` | IANA timezone used to interpret local booking times. |
| `external_calendar_provider` | `auto`, `internal`, `google`, or `microsoft`. `auto` uses an existing Google connection first, then Microsoft; an explicitly selected but disconnected provider fails closed. |
| `duration_minutes` | Default service length. |
| `min_duration_minutes` / `max_duration_minutes` | Allowed appointment length range. Service and department rules can narrow it. |
| `buffer_minutes` | Preparation and cleanup padding around bookings. |
| `slot_interval_minutes` | Slot-search increment. |
| `alternative_window_minutes` | First before/after option to check. |
| `min_notice_minutes` | Minimum lead time for a booking. |
| `max_days_ahead` | Furthest date that may be booked. |
| `business_hours` | Up to four start/end ranges per weekday; split ranges represent breaks. |
| `holidays` | Dates on which the tenant is closed. |
| `blocked_intervals` | Date-time ranges that cannot be booked, optionally assigned to a staff ID. |
| `staff` | Staff IDs, active state, optional hours, and staff holidays. |
| `service_rules` | Per-service duration bounds and default, buffer, capacity, booking horizon, hours, holidays, staff allow-list, and cancellation notice. Names match case-insensitively. |
| `department_rules` | Per-department duration bounds and default, buffer, capacity, booking horizon, hours, and holidays. Names match case-insensitively. |
| `cancellation_policy` | Default `minimum_notice_minutes`; a service can override it with `cancel_before_minutes`. |

Settings are validated before saving. Staff IDs must be unique. Unknown staff IDs do not produce open slots when a staff list is configured. Availability respects staff hours, staff holidays, service staff allow-lists, blocking intervals, duration bounds, and configured service or department capacity. When a rule limits a service to staff IDs and no staff was requested, OIM checks eligible staff and assigns the first available one. Capacity counts confirmed OIM appointments in the same service/department scope. A connected third-party calendar may enforce a stricter single-busy-event rule; multi-seat capacity is reliable with the internal calendar unless the external calendar allows those overlaps.

## Availability and alternatives

Availability checks the tenant's hours, holidays, minimum notice, maximum booking horizon, blocked intervals, internal appointments, configured buffers, and the selected external calendar. Google Calendar uses FreeBusy; Microsoft Outlook uses Microsoft Graph `calendarView`. External calendar errors fail closed.

When a requested slot is unavailable, OIM checks the configured number of minutes before and after. If one or both are open, it returns those choices. If neither is open, it searches the nearest same-day slots; if the day is full, it searches forward up to 14 days (or the tenant's configured maximum, whichever is smaller). The returned options contain times and availability only, not other customers' identities.

`get_available_slots` accepts an ISO date, weekday, “tomorrow”, “this week”, “next month's first week”, and “earliest available” in English, Turkish, and Russian. It filters spoken time ranges and periods such as “10 ile 12 arasında” and “yarın öğleden sonra”; a slot must fit the requested range for its full duration. Appointment date-time input accepts ISO 8601 and common spoken forms such as “Friday at three”, “cuma saat üçte”, “в четверг в три часа”, “завтра в 15:00”, and “one hour later”. Date-only or incomplete booking expressions return `needs_clarification`; an agent must ask a follow-up question instead of guessing.

The agent can use `get_current_datetime` to obtain the tenant clock and timezone. The OIM prompt helper can insert rules requiring the agent to check availability, get explicit confirmation, verify the phone before appointment changes, and never claim success after a failed tool result.

## Appointment lifecycle

- **Create:** Check every requested time, insert appointments inside a write transaction, reserve Google or Microsoft events when configured, then commit. A daily or weekly series can contain 2–52 occurrences at intervals of 1–4 days or weeks. Repeated calls with the same idempotency key return the existing series. If an external event in a series fails, OIM tries to remove earlier events before rolling back internal rows.
- **Find:** Require a phone number with at least seven digits. An appointment ID is also checked against the tenant and normalized phone number.
- **Reschedule:** Verify the appointment, exclude its current calendar event during the availability check, update the external event, then update OIM.
- **Cancel:** Verify the appointment, enforce the default or service-specific notice period, cancel its external event when present, then mark it cancelled in OIM.

If an external reserve or modification fails, OIM does not report the action as successful. Each appointment stores its calendar provider so later cancellations and reschedules continue to target the original provider even when the tenant changes its current selection. Provider events and OIM appointments use separate transaction boundaries; a network failure during a remote mutation can still require an operator to reconcile an event.

## Views and endpoints

The Calendar admin screen has day, week, and month schedule views, settings, slot search, availability checks, alternatives, manual bookings, and daily/weekly recurring bookings. The appointment-list endpoint filters by tenant and period and returns at most 500 records per request.

```text
GET  /api/admin/voice-platform/calendar?tenant_id={tenant}
GET  /api/admin/voice-platform/calendar/appointments?tenant_id={tenant}&date=YYYY-MM-DD&view=day|week|month
GET  /api/admin/voice-platform/calendar/availability?tenant_id={tenant}&start={ISO8601}
GET  /api/admin/voice-platform/calendar/slots?tenant_id={tenant}&date=YYYY-MM-DD
GET  /api/admin/voice-platform/calendar/alternatives?tenant_id={tenant}&start={ISO8601}
POST /api/admin/voice-platform/calendar
POST /api/admin/voice-platform/calendar/book
```

The booking endpoint uses the same engine as the ElevenLabs tools. Availability, slot, and alternative routes accept optional `service` and `department` values for rule matching. Admin list and booking endpoints require an OIM administrator session and an explicit customer ID.

## Integrations and limits

Google Calendar and Microsoft Outlook are supported through per-tenant OAuth connections. Microsoft OAuth requires an Entra application with the callback URL `https://YOUR_PUBLIC_HOST/api/microsoft/callback`, delegated `Calendars.ReadWrite` permission, and the Graph consent for `offline_access`. Set `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_TENANT_ID` in the private server environment. The connection is owned by the customer who authorizes it. Select the external provider in `external_calendar_provider`; with `auto`, Google takes precedence when both are connected.

Public holiday dates are configured manually in tenant, service, department, or staff settings; OIM does not import an official holiday feed. Recurrences are limited to daily and weekly intervals, up to 52 appointments, without exception dates or automatic cancellation of the remaining series. Lunch breaks can be represented by splitting a day's business hours. Microsoft Entra credentials must be configured privately before customers can connect Outlook.
