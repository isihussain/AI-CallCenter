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

test("customer history loads after sign-in and the admin queue refreshes when opened", async () => {
  const demoRequest = {
    id: 9,
    tenant_id: 2,
    name: "Natalya Kangotan (Demo)",
    email: "natalya.demo@example.com",
    contact_phone: "+1 202-555-0101",
    message: "[DEMO] Persisted contact request",
    status: "new",
    created_at: 1793879245,
  };
  const customerReads = [];
  const customer = environment(html, "tr", async (url) => {
    customerReads.push(url);
    if (url === "/api/me")
      return {
        ok: true,
        json: async () => ({
          user: {
            id: 2,
            role: "customer",
            name: "Natalya Kangotan (Demo)",
            email: "natalya.demo@example.com",
          },
        }),
      };
    if (url === "/api/appointments")
      return { ok: true, json: async () => ({ items: [] }) };
    if (url === "/api/contact-requests")
      return { ok: true, json: async () => ({ items: [demoRequest] }) };
    return {
      ok: false,
      status: 404,
      json: async () => ({ error: "Demo stub" }),
    };
  });
  customer.window.location = { hash: "#contact-admin" };
  customer.context.location = customer.window.location;
  customer.context.history = { replaceState() {} };
  customer.context.OIMI18n = customer.i18n;
  customer.context.CallHistory = { setContext: async () => {} };
  customer.context.setInterval = () => 0;
  customer.window.scrollTo = () => {};
  customer.run("app.js");
  for (let i = 0; i < 8; i++)
    await new Promise((resolve) => setImmediate(resolve));

  assert.ok(customerReads.includes("/api/contact-requests"));
  assert.match(
    customer.document.querySelector("#contact-request-history-list")
      .textContent,
    /\[DEMO\] Persisted contact request/,
  );

  const adminReads = [];
  const admin = environment(html, "tr", async (url) => {
    adminReads.push(url);
    if (url === "/api/admin/contact-requests")
      return { ok: true, json: async () => ({ items: [demoRequest] }) };
    return {
      ok: false,
      status: 404,
      json: async () => ({ error: "Demo stub" }),
    };
  });
  admin.window.location = { hash: "#dashboard" };
  admin.context.location = admin.window.location;
  admin.context.history = {
    replaceState(_state, _title, url) {
      admin.window.location.hash = url;
    },
  };
  admin.context.OIMI18n = admin.i18n;
  admin.context.CallHistory = { setContext: async () => {} };
  admin.context.setInterval = () => 0;
  admin.window.scrollTo = () => {};
  admin.run("app.js");
  admin.context.applyUser({ id: 1, role: "admin", name: "Demo Administrator" });
  admin.document.querySelector('[data-view="admin-contact-requests"]').click();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));

  assert.ok(adminReads.includes("/api/admin/contact-requests"));
  assert.match(
    admin.document.querySelector("#admin-contact-requests-body").textContent,
    /Natalya Kangotan \(Demo\).*\[DEMO\] Persisted contact request/s,
  );
});
