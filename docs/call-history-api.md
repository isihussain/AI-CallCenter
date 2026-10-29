# Call history API

`GET /api/calls` requires an authenticated cookie session. Responses retain the existing `items` field and add pagination, filter, and summary metadata.

Customers always use their authenticated tenant. A supplied `tenant_id` cannot change that scope. Administrators select a customer with `tenant_id`; omitting it returns an empty selection.

## Query parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `tenant_id` | `0` for administrators | Nonnegative ID; ignored for customer sessions |
| `page` | `1` | Integer from 1 to 1,000,000 |
| `page_size` | `50` | Integer from 1 to 100; panel default is 25 |
| `date_from` | No lower bound | `YYYY-MM-DD`, inclusive start of that UTC day |
| `date_to` | No upper bound | `YYYY-MM-DD`, inclusive through the end of that UTC day |
| `status` | All | `incoming`, `active`, `ended`, `failed`, or `rejected_no_credit` |
| `caller` | All | Literal substring, maximum 100 characters |
| `snapshot_id` | Latest call ID for the tenant | Upper call-ID boundary retained across pages |

Example request for a signed-in customer:

~~~text
/api/calls?page=1&page_size=25&date_from=2026-10-01&date_to=2026-10-31&status=ended
~~~

Invalid dates, reversed ranges, duplicate supported parameters, unknown statuses, and invalid numeric values return HTTP 400 with `code: "invalid_call_query"` and a readable `error`. An empty date field means no bound. Caller `%` and `_` characters are literal rather than SQL wildcards.

## Response

~~~json
{
  "items": [],
  "pagination": {
    "page": 1, "page_size": 25, "total": 147, "total_pages": 6,
    "has_next": true, "has_previous": false, "snapshot_id": 147
  },
  "filters": {
    "tenant_id": 2, "status": "", "caller": "", "date_from": "", "date_to": "", "timezone": "UTC"
  },
  "summary": {
    "total_calls": 147, "completed_calls": 130, "total_duration_seconds": 11700,
    "average_duration_seconds": 90, "billed_credits": 33.15,
    "estimated_openai_usd": 2.49, "total_tokens": 83250, "metered_calls": 147
  },
  "traffic": [{ "day": "2026-10-29", "calls": 15 }]
}
~~~

This abbreviated example omits item objects. Counts and costs are synthetic.

Items use `started_at DESC, id DESC` with a tie-breaker for equal timestamps. Reuse `snapshot_id` on later pages so new calls do not move existing rows between pages. Refreshing or changing filters starts a new snapshot. This fixes the insertion boundary; it does not freeze later edits or deletions.

Summary and traffic fields cover the full matching result set within the snapshot, including rows outside the current page. `completed_calls` counts `ended` calls; duration totals and averages use those completed calls. Cost values are estimates based on stored usage and the backend's price table.

## Panel and CSV report

The panel provides date, status, caller, and page-size controls with loading, empty, and retry states. Dates and call times here use UTC. Summary cards describe the same full filtered result set.

The report fetches every matching call page under one snapshot before downloading. A failed page or a final count mismatch prevents a partial export. The CSV includes filter/coverage metadata, a UTF-8 BOM, CRLF separators, and quoted fields.

For compatibility with the previous report, it also includes the selected tenant's latest 100 appointments. Those rows do not use the call filters; the file states their separate coverage. Text fields starting with spreadsheet formula characters receive an apostrophe prefix.

