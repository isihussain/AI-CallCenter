const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { environment, flush, UI } = require("./helpers.cjs");

const html = fs.readFileSync(path.join(UI, "index.html"), "utf8");

test("operations panels load tenant-scoped readiness, monitoring, usage, callbacks, and retention", async () => {
  const requests = [];
  const env = environment(html, "en", async (url, options = {}) => {
    const pathName = new URL(url, "http://localhost").pathname;
    requests.push({ url: String(url), pathName, options });
    const values = {
      "/api/me": { user: { id: 2, name: "Demo tenant", role: "customer" } },
      "/api/readiness": {
        tenant_id: 2,
        tenant_name: "Demo tenant",
        checks: [
          { key: "sip", ready: true },
          { key: "provider", ready: true },
          { key: "greeting", ready: false },
          { key: "knowledge", ready: false },
        ],
      },
      "/api/tenant/ai-settings": { greeting: "Hello there", voice: "alloy" },
      "/api/usage-report": {
        filters: { date_from: "2026-10-01", date_to: "2026-10-30" },
        daily: [
          {
            day: "2026-10-29",
            calls: 2,
            billed_credits: 1.5,
            estimated_openai_usd: null,
            metered_calls: 0,
            total_tokens: 0,
          },
        ],
        tenants: [],
      },
      "/api/callbacks": {
        items: [
          {
            id: 8,
            phone: "+1 555 111 2222",
            reason: "Billing help",
            status: "pending",
            created_at: 1793232000,
          },
        ],
      },
      "/api/analytics/summary": {
        tenant_id: 2,
        filters: { date_from: "2026-10-01", date_to: "2026-10-30", timezone: "UTC" },
        kpis: {
          total_calls: 10,
          completed_calls: 9,
          failed_calls: 1,
          active_calls: 0,
          incoming_calls: 0,
          rejected_calls: 0,
          total_duration_seconds: 540,
          average_duration_seconds: 60.0,
          max_duration_seconds: 120,
          billed_credits: 5.5,
          estimated_openai_usd: 0.052,
          total_tokens: 3500,
          input_tokens: 2000,
          output_tokens: 1500,
          input_audio_tokens: 0,
          output_audio_tokens: 0,
          success_rate_percent: 90.0,
        },
        by_status: { ended: 9, failed: 1, active: 0, incoming: 0, rejected_no_credit: 0 },
        by_outcome: { resolved: 8, unresolved: 1 },
        conversion: { appointments_count: 2, callbacks_count: 1 },
      },
      "/api/privacy": {
        transcript_retention_days: 45,
        last_purged_at: null,
      },
      "/api/live-calls": {
        active: [{ call_id: "active-call-1", started_at: 1793232000 }],
        failures: [],
      },
    };
    return { ok: true, json: async () => values[pathName] || { ok: true } };
  });
  env.context.setInterval = () => 0;
  env.context.location = env.window.location;
  env.context.Option = function Option(label, value) {
    const option = env.document.createElement("option");
    option.textContent = label;
    option.value = value;
    return option;
  };
  env.run("operations.js");
  await flush();
  await flush();

  assert.equal(env.document.querySelector("#setup-tenant-name").textContent, "Demo tenant");
  assert.match(env.document.querySelector("#readiness-count").textContent, /2\/4/);
  assert.equal(env.document.querySelectorAll("#readiness-checks a").length, 4);
  assert.equal(env.document.querySelector("#greeting-preview").textContent, "Hello there");
  assert.match(env.document.querySelector("#active-call-list").textContent, /active-call-1/);
  assert.match(env.document.querySelector("#usage-status").textContent, /recorded usage only/i);
  assert.match(env.document.querySelector("#usage-daily-body").textContent, /No usage data/);
  assert.match(env.document.querySelector("#callbacks-body").textContent, /\+1 555 111 2222/);
  assert.equal(env.document.querySelector("#retention-days").value, "45");
  assert.equal(env.document.querySelector("#analytics-total-calls").textContent, "10");
  assert.equal(env.document.querySelector("#analytics-success-rate").textContent, "90%");
  assert.equal(env.document.querySelector("#analytics-avg-duration").textContent, "60s");
  assert.equal(env.document.querySelector("#analytics-conversions").textContent, "3");
  assert.ok(requests.some((entry) => entry.pathName === "/api/readiness"));
  assert.ok(requests.some((entry) => entry.pathName === "/api/callbacks"));
  assert.ok(requests.some((entry) => entry.pathName === "/api/analytics/summary"));
  assert.ok(requests.every((entry) => !entry.url.includes("tenant_id=3")));
});
