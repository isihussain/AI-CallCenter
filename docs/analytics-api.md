# Call analytics and KPI summary API

`GET /api/analytics/summary` returns aggregated call metrics, status counts, review outcomes, and conversion statistics for reporting dashboards. The endpoint requires an authenticated cookie session.

Customers always query their authenticated tenant; supplying a different `tenant_id` does not change this scope. Administrators can provide `tenant_id` to inspect a single tenant or omit it to compute aggregate metrics across all active customer tenants.

## Query parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `tenant_id` | integer | `0` for administrators | Nonnegative ID; ignored for customer sessions |
| `date_from` | string | None | `YYYY-MM-DD`, inclusive start of UTC day |
| `date_to` | string | None | `YYYY-MM-DD`, inclusive end of UTC day |

Invalid date strings and reversed date ranges return HTTP 400 with `code: "invalid_analytics_query"`.

## Response structure

```json
{
  "tenant_id": 2,
  "filters": {
    "date_from": "2026-10-01",
    "date_to": "2026-10-31",
    "timezone": "UTC"
  },
  "kpis": {
    "total_calls": 42,
    "completed_calls": 38,
    "failed_calls": 2,
    "active_calls": 1,
    "incoming_calls": 1,
    "rejected_calls": 0,
    "total_duration_seconds": 4560,
    "average_duration_seconds": 120.0,
    "max_duration_seconds": 380,
    "billed_credits": 15.20,
    "estimated_openai_usd": 1.140000,
    "total_tokens": 38500,
    "input_tokens": 25000,
    "output_tokens": 13500,
    "input_audio_tokens": 12000,
    "output_audio_tokens": 9000,
    "success_rate_percent": 95.0
  },
  "by_status": {
    "ended": 38,
    "failed": 2,
    "active": 1,
    "incoming": 1,
    "rejected_no_credit": 0
  },
  "by_outcome": {
    "resolved": 28,
    "appointment_booked": 8,
    "callback_needed": 2,
    "unreviewed": 4
  },
  "conversion": {
    "appointments_count": 8,
    "callbacks_count": 2
  }
}
```

## Calculation rules

1. **Duration:** `total_duration_seconds` and `average_duration_seconds` evaluate completed calls (`status = 'ended'`). Calls missing an `ended_at` timestamp compute elapsed time from `started_at`.
2. **Success Rate:** `success_rate_percent` divides `completed_calls` by finished calls (`completed_calls + failed_calls`). When no finished calls exist in the query window, it evaluates to 100.0%.
3. **Usage & Cost:** Token totals and estimated USD cost aggregate records from `call_usage` matching calls within the filtered window.
4. **Conversions:** `conversion.appointments_count` and `conversion.callbacks_count` count appointment and callback rows linked by `call_id` and owned by the target tenant.
