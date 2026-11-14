# Security review

**Review date:** 2026-11-14
**Method:** targeted static source review of login throttling, HTTP request handling, recording delivery, incoming Realtime webhooks, CSV exports, and GitHub security automation.

## Findings addressed

- Login throttling could lose failure counts when requests for the same account arrived together. The updated limiter serializes matching attempts, bounds its in-memory entries, and limits username and password lengths. Nginx also limits login traffic to 20 requests per minute per client address. If the in-memory cache is full, successful logins still work; new failed attempts are not recorded until capacity returns.
- The API accepted unbounded `Content-Length` values when reached without the example reverse proxy. POST bodies now have a 1 MiB limit and reject unsupported transfer encoding.
- Recording filenames without a tenant prefix were sent to tenant 2, and normal file opens followed symbolic links. The watcher now requires `t<TENANT_ID>-...wav`, opens regular files without following links, uploads from that same file descriptor, and skips files over 50 MiB.
- Duplicate incoming call webhooks could send repeated provider accept requests and use a new tenant's settings for an existing call ID. Call creation now uses a database write transaction, rejects tenant mismatches, and stores webhook IDs, body digests, and claim tokens for seven days. A duplicate receives a retryable response while the original event is still processing; completed events are acknowledged without repeating successful provider or sideband work. Stale claims can be recovered, failed provider accepts can be retried, and failed sideband startup retries without accepting the call again.
- CRM, ledger, analytics, and call-report exports could pass user-controlled strings to spreadsheet software as formulas. CSV exports now prefix formula-like text with an apostrophe and quote each cell.

## Verification

- `git diff --check` passed for the review changes.
- Regression coverage was added for concurrent login failures and cache saturation, oversized request bodies, recording filename routing and identifier bounds, symbolic links, duplicate webhooks, sideband retries, and call tenant ownership.
- Dashboard coverage was added for formula-safe CSV cell encoding.
- The application test suite was not run on the local host. The Codex Security scan worker could not start because this session did not provide its required managed filesystem profile. GitHub Actions runs the regression suite and CodeQL on the pull request; their results should be reviewed before merging.
- The repository now includes CodeQL, dependency review, and weekly Dependabot configuration.

## Limits

This is a targeted source review, not a complete security audit. It did not inspect a live deployment, production logs or secrets, the external `oim-apply-sip` helper, or host and proxy access controls. Provider-side exactly-once behavior after an ambiguous network timeout is not guaranteed by this application-level deduplication.
