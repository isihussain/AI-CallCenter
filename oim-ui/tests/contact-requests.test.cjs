const test = require("node:test"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
const { environment, UI } = require("./helpers.cjs");
const html = fs.readFileSync(path.join(UI, "index.html"), "utf8");

test("customer profile contains a separate, accessible administrator request form", () => {
  const { document } = environment(html);
  const panel = document.querySelector("#contact-admin");
  const form = panel.querySelector("#contact-request-form");
  const message = form.querySelector('[name="message"]');

  assert.equal(panel.getAttribute("data-customer-only"), "");
  assert.equal(panel.getAttribute("data-view-panel"), "contact-admin");
  assert.equal(
    document
      .querySelector("[data-profile-contact]")
      .getAttribute("data-customer-only"),
    "",
  );
  assert.equal(form.querySelector('[name="contact_phone"]').type, "tel");
  assert.equal(message.hasAttribute("required"), true);
  assert.equal(message.getAttribute("maxlength"), "2000");
  assert.equal(
    message.getAttribute("aria-describedby"),
    "contact-request-hint",
  );
  assert.equal(
    document.querySelector("#contact-request-status").getAttribute("aria-live"),
    "polite",
  );
});

test("administrator CRM requests have an independent, role-gated view and status filter", () => {
  const { document } = environment(html);
  const panel = document.querySelector("#admin-contact-requests");

  assert.equal(panel.getAttribute("data-admin-only"), "");
  assert.equal(panel.getAttribute("data-view-panel"), "admin-contact-requests");
  assert.equal(
    document
      .querySelector('[data-view="admin-contact-requests"]')
      .getAttribute("data-admin-only"),
    "",
  );
  assert.deepEqual(
    [...document.querySelectorAll("#admin-contact-request-filter option")].map(
      (option) => option.value,
    ),
    ["all", "new", "in_progress", "resolved"],
  );
  assert.equal(
    document.querySelectorAll(".admin-contact-request-table thead th").length,
    6,
  );
});

test("profile request submits only the optional callback number and message", async () => {
  const writes = [];
  const env = environment(html, "tr", async (url, options = {}) => {
    if (url === "/api/contact-requests" && options.method === "POST") {
      writes.push(JSON.parse(options.body));
      return {
        ok: true,
        status: 201,
        json: async () => ({ ok: true, id: 7, status: "new" }),
      };
    }
    if (url === "/api/contact-requests")
      return { ok: true, json: async () => ({ items: [] }) };
    return {
      ok: false,
      status: 404,
      json: async () => ({ error: "Demo stub" }),
    };
  });
  env.window.location = { hash: "#dashboard" };
  env.context.location = env.window.location;
  env.context.history = {
    replaceState(_state, _title, url) {
      env.window.location.hash = url;
    },
  };
  env.context.OIMI18n = env.i18n;
  env.context.CallHistory = { setContext: async () => {} };
  env.context.setInterval = () => 0;
  env.window.scrollTo = () => {};
  env.run("app.js");
  env.context.applyUser({
    id: 2,
    role: "customer",
    name: "Natalya Kangotan (Demo)",
    email: "natalya.demo@example.com",
  });

  env.document.querySelector(".profile-chip").click();
  env.document.querySelector("[data-profile-contact]").click();
  assert.equal(env.window.location.hash, "#contact-admin");
  env.document.querySelector("#contact-request-message").value =
    "[DEMO] I would like to speak with an administrator.";
  env.document.querySelector("#contact-request-phone").value =
    "+1 202-555-0101";
  const form = env.document.querySelector("#contact-request-form");
  form.reset = () => {
    form.querySelector('[name="message"]').value = "";
    form.querySelector('[name="contact_phone"]').value = "";
  };
  form.dispatchEvent(
    new env.window.Event("submit", { bubbles: true, cancelable: true }),
  );
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(writes, [
    {
      contact_phone: "+1 202-555-0101",
      message: "[DEMO] I would like to speak with an administrator.",
    },
  ]);
  assert.equal(
    env.document.querySelector("#contact-request-status").textContent,
    "Talebiniz yöneticiye iletildi.",
  );
});
