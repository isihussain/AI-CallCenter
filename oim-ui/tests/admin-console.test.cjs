const test = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
const { environment, flush, UI } = require("./helpers.cjs");
const html = fs.readFileSync(path.join(UI, "index.html"), "utf8");
function setup(role = "admin") {
  const writes = [],
    reads = [];
  const providers = ["openai", "openai_ai", "elevenlabs"].map((provider) => ({
    provider,
    configured: true,
    enabled: true,
    model: "demo-model",
    voice_id: "demo-voice",
    check_status: "unchecked",
  }));
  const flow = {
    updated_at: 1793280000,
    providers,
    realtime: { configured: true, model: "demo-realtime" },
    counts: {
      active: 3,
      today: 18,
      callbacks: 4,
      failed: 1,
      knowledge: 2,
      appointments: 5,
    },
  };
  const env = environment(html, "en", async (url, options = {}) => {
    if (options.method === "POST") {
      const body = JSON.parse(options.body);
      writes.push({ url, body });
      return {
        ok: true,
        json: async () => ({ ok: true, provider: { configured: true } }),
      };
    }
    reads.push(url);
    return {
      ok: true,
      json: async () =>
        url === "/api/me"
          ? { user: { id: 1, role } }
          : url === "/api/admin/providers"
            ? { items: providers }
            : flow,
    };
  });
  env.context.setInterval = () => 0;
  env.window.location = { hash: "#dashboard" };
  env.run("admin-console.js");
  return { ...env, writes, reads };
}
test("admin flow has real counters, selectable nodes, list view, and independent provider forms", async () => {
  const env = setup();
  await flush();
  await flush();
  assert.equal(env.document.querySelectorAll("#provider-cards form").length, 3);
  assert.match(env.document.querySelector("#flow-metrics").textContent, /18/);
  const eleven = env.document.querySelector('[data-flow-node="elevenlabs"]');
  eleven.click();
  assert.equal(eleven.getAttribute("aria-pressed"), "true");
  assert.match(
    env.document.querySelector("#flow-inspector").textContent,
    /selected ElevenLabs voice/,
  );
  env.document.querySelector("#flow-toggle").click();
  assert.equal(env.document.querySelector("#flow-list").hidden, false);
  env.document.querySelector("#flow-pause").click();
  assert.equal(
    env.document.querySelector("#flow-pause").getAttribute("aria-pressed"),
    "true",
  );
  assert.equal(env.writes.length, 0, "loading must not call a provider");
});
test("saving one provider sends only its form and clears the typed secret after success", async () => {
  const env = setup();
  await flush();
  await flush();
  const form = env.document.querySelector('form[data-provider="elevenlabs"]');
  form.querySelector("[name=api_key]").value = "synthetic-secret";
  form.querySelector("[name=voice_id]").value = "another-voice";
  form.dispatchEvent(new env.window.Event("submit"));
  await flush();
  await flush();
  assert.equal(env.writes.length, 1);
  assert.equal(env.writes[0].body.provider, "elevenlabs");
  assert.equal(env.writes[0].body.voice_id, "another-voice");
  assert.equal(form.querySelector("[name=api_key]").value, "");
  assert.equal(
    env.document.querySelector('form[data-provider="openai"] [name=model]')
      .value,
    "demo-model",
  );
});
test("customer sessions never fetch global flow or provider configuration", async () => {
  const env = setup("customer");
  await flush();
  await flush();
  assert.deepEqual(env.reads, ["/api/me"]);
  assert.equal(env.document.querySelector("#integrations").hidden, true);
  assert.equal(env.document.querySelector("#system-flow").hidden, true);
});
