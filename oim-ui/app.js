const toast = document.querySelector(".toast");
let toastTimer;
let currentUser = null;
let dashboardTenantId = 0;
document.querySelector(".chart-panel")?.remove();
const overviewGrid = document.querySelector(".content-grid");
if (overviewGrid) overviewGrid.style.gridTemplateColumns = "1fr";
document.querySelectorAll(".agent-row").forEach((row, index) => {
  if (index > 0) row.remove();
});
const pageContent = document.querySelector(".page-content");
const helpLink = document.querySelector(".help-link");
if (pageContent && !document.querySelector("#help-center")) {
  const helpBlock = document.createElement("section");
  helpBlock.id = "help-center";
  helpBlock.className = "panel help-center";
  helpBlock.dataset.viewPanel = "help";
  helpBlock.innerHTML =
    '<div class="panel-heading"><div><p class="eyebrow">DESTEK MERKEZİ</p><h1>Yardım Merkezi</h1><p>Kurulum ve günlük kullanım için kısa rehber.</p></div></div>\n<div class="help-grid">\n<article class="help-card"><h2>Açılış mesajı</h2><p>Müşteri panelinden karşılama metnini kaydedin. Yeni çağrılar, arayan kişi konuşmadan bu mesajla başlar.</p><p>Panel dilini değiştirmek, kayıtlı karşılama metnini değiştirmez.</p></article>\n<article class="help-card"><h2>Bilgi Bankası</h2><p>İşletme bilgilerinizi Türkçe, İngilizce ve Rusça Markdown dosyalarına yükleyin. Yalnızca yayınlanmış içerik yeni çağrılarda kullanılır.</p><a class="button outline" href="/knowledge-prompt.md" download>ChatGPT promptu</a></article>\n<article class="help-card"><h2>Bağlantılar</h2><p>SIP ve sağlayıcı ayarlarını yönetici yapılandırır. Müşteri kendi Google Calendar ve Telegram bağlantılarını yönetir.</p></article>\n<article class="help-card"><h2>Çağrı raporları</h2><p>Tarih, durum ve numara filtreleri tüm çağrı geçmişinde çalışır. Rapor, filtreye uyan tüm çağrıları ve en son 100 randevuyu içerir.</p><a class="button outline" href="https://github.com/isihussain/AI-CallCenter#readme" target="_blank" rel="noopener">Kurulum belgeleri</a></article>\n</div>\n';
  pageContent.appendChild(helpBlock);
  helpLink?.addEventListener("click", () => {
    setView("help");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}
const viewPanels = {
  calls: document.querySelector("#calls"),
  "usage-costs": document.querySelector("#usage-costs"),
  "live-monitoring": document.querySelector("#live-monitoring"),
  callbacks: document.querySelector("#callbacks"),
  privacy: document.querySelector("#privacy"),
  appointments: document.querySelector("#appointments"),
  agents: document.querySelector(".agents-panel")?.closest(".content-grid"),
  customers: document.querySelector("#customers"),
  knowledge: document.querySelector("#knowledge"),
  telegram: document.querySelector("#telegram"),
  settings: document.querySelector("#settings"),
  sip: document.querySelector("#settings"),
};
const appointmentsPanel = document.querySelector("#appointments");
let calendarCursor = new Date();
let calendarItems = [];
let calendarSelected = null;
if (appointmentsPanel && !document.querySelector("#oim-month-calendar")) {
  const oldTable = appointmentsPanel.querySelector(".table-wrap");
  const shell = document.createElement("div");
  shell.id = "oim-month-calendar";
  shell.innerHTML =
    '<div class="oim-calendar-toolbar"><button class="button outline" id="calendar-prev" type="button" aria-label="Önceki ay"><i class="fa-solid fa-chevron-left"></i></button><strong id="calendar-month-label"></strong><button class="button outline" id="calendar-next" type="button" aria-label="Sonraki ay"><i class="fa-solid fa-chevron-right"></i></button><button class="button secondary" id="calendar-today" type="button">Bugün</button></div><div class="oim-calendar-layout"><div class="oim-calendar-grid" id="calendar-grid"></div><aside class="oim-calendar-details"><h3 id="calendar-day-label">Günün randevuları</h3><div id="calendar-day-items"><p class="form-note">Bir gün seçin.</p></div></aside></div>';
  oldTable?.replaceWith(shell);
}
function dateKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function renderCalendar(items = calendarItems) {
  calendarItems = items || [];
  const grid = document.querySelector("#calendar-grid");
  const label = document.querySelector("#calendar-month-label");
  if (!grid || !label) return;
  const y = calendarCursor.getFullYear(),
    m = calendarCursor.getMonth();
  label.textContent = new Intl.DateTimeFormat(OIMI18n.localeTag(), {
    month: "long",
    year: "numeric",
  }).format(calendarCursor);
  const first = new Date(y, m, 1),
    start = (first.getDay() + 6) % 7,
    days = new Date(y, m + 1, 0).getDate(),
    prevDays = new Date(y, m, 0).getDate();
  const counts = {};
  calendarItems.forEach((x) => {
    const k = String(x.appointment_at || "").slice(0, 10);
    counts[k] = (counts[k] || 0) + 1;
  });
  let html = "";
  Array.from({ length: 7 }, (_, day) =>
    new Intl.DateTimeFormat(OIMI18n.localeTag(), { weekday: "short" }).format(
      new Date(2024, 0, 1 + day),
    ),
  ).forEach((x) => (html += `<div class="oim-calendar-weekday">${x}</div>`));
  for (let i = 0; i < 42; i++) {
    const n = i - start + 1;
    let day = n,
      month = m,
      year = y,
      muted = false;
    if (n < 1) {
      day = prevDays + n;
      month = m - 1;
      muted = true;
    } else if (n > days) {
      day = n - days;
      month = m + 1;
      muted = true;
    }
    const dt = new Date(year, month, day),
      key = dateKey(dt),
      count = counts[key] || 0;
    const selected = calendarSelected === key ? " selected" : "";
    const today = dateKey(new Date()) === key ? " today" : "";
    html += `<button type="button" class="oim-calendar-day${muted ? " muted" : ""}${selected}${today}" data-calendar-date="${key}"><span>${day}</span>${count ? `<em>${count}</em>` : ""}</button>`;
  }
  grid.innerHTML = html;
  grid.querySelectorAll("[data-calendar-date]").forEach((b) =>
    b.addEventListener("click", () => {
      calendarSelected = b.dataset.calendarDate;
      renderCalendar(calendarItems);
    }),
  );
  const chosen = calendarSelected || dateKey(new Date());
  const detail = calendarItems.filter(
    (x) => String(x.appointment_at || "").slice(0, 10) === chosen,
  );
  const dayLabel = document.querySelector("#calendar-day-label");
  if (dayLabel) {
    const d = new Date(`${chosen}T12:00:00`);
    dayLabel.textContent = new Intl.DateTimeFormat(OIMI18n.localeTag(), {
      weekday: "long",
      day: "numeric",
      month: "long",
    }).format(d);
  }
  const detailBox = document.querySelector("#calendar-day-items");
  if (detailBox)
    detailBox.innerHTML = detail.length
      ? detail
          .sort((a, b) =>
            String(a.appointment_at).localeCompare(String(b.appointment_at)),
          )
          .map(
            (x) =>
              `<article class="oim-calendar-event"><strong>${escapeHtml(String(x.appointment_at).slice(11, 16) || "—")} · ${escapeHtml(x.customer_name || "")}</strong><span>${escapeHtml(x.service || "")}</span><small>${escapeHtml(x.phone || "")}${x.notes ? " · " + escapeHtml(x.notes) : ""}</small></article>`,
          )
          .join("")
      : '<p class="form-note">Bu gün için randevu yok.</p>';
}
document.querySelector("#calendar-prev")?.addEventListener("click", () => {
  calendarCursor.setMonth(calendarCursor.getMonth() - 1);
  renderCalendar();
});
document.querySelector("#calendar-next")?.addEventListener("click", () => {
  calendarCursor.setMonth(calendarCursor.getMonth() + 1);
  renderCalendar();
});
document.querySelector("#calendar-today")?.addEventListener("click", () => {
  calendarCursor = new Date();
  calendarSelected = dateKey(new Date());
  renderCalendar();
});
const crmPanel = document.querySelector("#crm");
if (crmPanel && !document.querySelector("#crm-filter")) {
  const toolbar = document.createElement("div");
  toolbar.className = "crm-toolbar";
  toolbar.innerHTML =
    '<input id="crm-filter" type="search" placeholder="Müşteri adına göre filtrele" aria-label="Müşteri adına göre filtrele"><input id="crm-phone-filter" type="search" placeholder="Telefon filtrele" aria-label="Telefon filtrele"><input id="crm-email-filter" type="search" placeholder="E-posta filtrele" aria-label="E-posta filtrele"><button class="button outline" id="crm-filter-clear" type="button">Temizle</button><button class="button secondary" id="crm-export" type="button"><i class="fa-solid fa-file-excel" aria-hidden="true"></i> Excel indir</button>';
  const table = crmPanel.querySelector(".table-wrap");
  if (table) crmPanel.insertBefore(toolbar, table);
}
crmPanel
  ?.querySelector("thead tr")
  ?.insertAdjacentHTML("beforeend", "<th>İŞLEM</th>");
Object.entries(viewPanels).forEach(([name, el]) => {
  if (el && !el.dataset.viewPanel) el.dataset.viewPanel = name;
});
document
  .querySelector("#customer-telegram")
  ?.setAttribute("data-view-panel", "telegram");
document.querySelector("#crm")?.setAttribute("data-view-panel", "crm");
document
  .querySelector("#calendar")
  ?.setAttribute("data-view-panel", "calendar");
const lowerGrid = document.querySelector(".lower-grid");
const setupPanel = document.querySelector(".setup-panel");
function setView(view = "dashboard") {
  const mobileView = document.querySelector("#mobile-view");
  if (mobileView) mobileView.value = view;
  if (pageContent)
    pageContent.dataset.viewMode =
      view === "dashboard" ? "dashboard" : "detail";
  document.querySelectorAll("[data-view-panel]").forEach((el) => {
    el.classList.toggle(
      "view-hidden",
      view === "dashboard"
        ? !["agents", "calls", "system-flow"].includes(el.dataset.viewPanel)
        : el.dataset.viewPanel !== view,
    );
  });
  const settings = document.querySelector("#settings");
  if (settings) {
    settings.dataset.activeView = view;
    if (view === "telegram" || view === "sip")
      settings.classList.remove("view-hidden");
  }
  if (lowerGrid)
    lowerGrid.classList.toggle(
      "view-hidden",
      view !== "dashboard" && view !== "calls",
    );
  if (setupPanel)
    setupPanel.classList.toggle("view-hidden", view !== "dashboard");
  document
    .querySelectorAll(".nav-item")
    .forEach((nav) =>
      nav.classList.toggle(
        "active",
        (nav.dataset.view || "dashboard") === view,
      ),
    );
  const labels = {
    dashboard: "Genel Bakış",
    "system-flow": "Sistem akışı",
    integrations: "API bağlantıları",
    calls: "Çağrılar",
    "usage-costs": "Kullanım raporu",
    "live-monitoring": "Canlı izleme",
    callbacks: "Geri aramalar",
    privacy: "Veri saklama",
    appointments: "Randevular",
    agents: "AI Ajanları",
    "opening-message": "Açılış mesajı",
    customers: "Müşteriler",
    sip: "SIP Bağlantıları",
    knowledge: "Bilgi Bankası",
    telegram: "Telegram",
    settings: "Ayarlar",
    help: "Yardım Merkezi",
  };
  const crumb = document.querySelector(".breadcrumb strong");
  if (crumb) crumb.textContent = labels[view] || "Genel Bakış";
  if (location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
}
window.OIMSetView = setView;
setView(location.hash.slice(1) || "dashboard");
const loginScreen = document.querySelector("#login-screen");
const loginForm = document.querySelector("#login-form");
const loginError = document.querySelector("#login-error");
async function checkSession() {
  try {
    const response = await fetch("/api/me", { credentials: "same-origin" });
    if (response.ok) {
      const data = await response.json();
      applyUser(data.user);
      loginScreen.classList.add("hidden");
      loadOperationalData();
    }
  } catch (_) {}
}
loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  const payload = Object.fromEntries(new FormData(loginForm).entries());
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Giriş yapılamadı");
    applyUser(data.user);
    loginScreen.classList.add("hidden");
    loadOperationalData();
  } catch (error) {
    loginError.textContent = error.message;
  }
});
checkSession();
async function loadProviders() {
  return window.AdminConsole?.refresh();
}
loadProviders();
function escapeHtml(value = "") {
  return String(value).replace(
    /[&<>'"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        c
      ],
  );
}
function applyUser(user) {
  const changed =
    currentUser?.id !== user?.id || currentUser?.role !== user?.role;
  currentUser = user || null;
  document.body.dataset.role = user?.role || "guest";
  document.querySelectorAll("[data-admin-only]").forEach((el) => {
    el.hidden = user?.role !== "admin";
  });
  document.querySelectorAll("[data-customer-only]").forEach((el) => {
    el.hidden = user?.role !== "customer";
  });
  const tenantName = document.querySelector(".tenant-copy strong");
  const tenantMeta = document.querySelector(".tenant-copy small");
  const tenantAvatar = document.querySelector(".tenant-avatar");
  const greeting = document.querySelector(".welcome-row h1");
  const setupName = document.querySelector("#setup-tenant-name");
  const agentName = document.querySelector(".agents-panel .agent-info strong");
  const callTenant = document.querySelector("#calls tbody");
  if (user?.role === "admin") {
    if (tenantName) tenantName.textContent = "OIM SaaS";
    if (tenantMeta) tenantMeta.textContent = "Yönetici paneli";
    if (tenantAvatar) tenantAvatar.textContent = "OI";
    if (greeting) greeting.textContent = "Günaydın, AI Call Center";
    if (location.hash === "#knowledge") setView("dashboard");
  } else if (user) {
    const displayName = user.name || "Müşteri";
    if (tenantName) tenantName.textContent = displayName;
    if (tenantMeta) tenantMeta.textContent = "Müşteri hesabı";
    if (tenantAvatar)
      tenantAvatar.textContent = String(displayName)
        .split(/\s+/)
        .map((x) => x[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();
    if (greeting) greeting.textContent = `Günaydın, ${displayName}`;
    if (setupName) setupName.textContent = `${displayName} sesli ajanı`;
    if (agentName) agentName.textContent = displayName;
    if (
      ["#sip", "#settings", "#integrations", "#system-flow"].includes(
        location.hash,
      )
    )
      setView("dashboard");
  }
  if (changed)
    window.dispatchEvent(
      new CustomEvent("oim:sessionchange", {
        detail: { role: user?.role || "guest" },
      }),
    );
}
function formatMoment(value) {
  if (!value) return "—";
  const d =
    typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(d.getTime())
    ? escapeHtml(value)
    : new Intl.DateTimeFormat(OIMI18n.localeTag(), {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Europe/Istanbul",
      }).format(d);
}
function formatDuration(start, end) {
  if (!start) return "—";
  const seconds = Math.max(0, (end || Math.floor(Date.now() / 1000)) - start);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
const todayLabel = document.querySelector("#today-label");
if (todayLabel)
  todayLabel.textContent = new Intl.DateTimeFormat(OIMI18n.localeTag(), {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Europe/Istanbul",
  })
    .format(new Date())
    .toLocaleUpperCase(OIMI18n.localeTag());
let operationalSequence = 0;
async function loadOperationalData() {
  const active = ++operationalSequence;
  try {
    const meResponse = await fetch("/api/me", { credentials: "same-origin" });
    if (!meResponse.ok || active !== operationalSequence) return;
    const me = await meResponse.json();
    if (active !== operationalSequence) return;
    applyUser(me.user);
    let balance = Number(me.user.credits || 0);
    let tenantName = me.user.name;
    if (me.user.role === "admin") {
      const response = await fetch("/api/admin/tenants", {
        credentials: "same-origin",
      });
      if (!response.ok) throw Error("Müşteriler yüklenemedi.");
      const tenants = await response.json();
      if (active !== operationalSequence) return;
      const selected =
        tenants.items.find((x) => Number(x.id) === Number(dashboardTenantId)) ||
        tenants.items[0];
      dashboardTenantId = selected ? Number(selected.id) : 0;
      balance = Number(selected?.credits || 0);
      tenantName = selected?.name || "—";
      const picker = document.querySelector("#dashboard-tenant");
      picker.replaceChildren();
      if (!tenants.items.length) {
        const option = document.createElement("option");
        option.textContent = OIMI18n.t("Henüz müşteri yok");
        option.value = "";
        picker.append(option);
      }
      for (const customer of tenants.items) {
        const option = document.createElement("option");
        option.value = String(customer.id);
        option.textContent = customer.name;
        option.dataset.userContent = "";
        picker.append(option);
      }
      picker.value = String(dashboardTenantId);
      const setupName = document.querySelector("#setup-tenant-name");
      if (setupName)
        setupName.textContent = OIMI18n.t("{0} sesli ajanı", { 0: tenantName });
      loadCustomers(tenants.items);
    }
    const tenantId = me.user.role === "admin" ? dashboardTenantId : me.user.id;
    const tenantQuery =
      me.user.role === "admin"
        ? "?tenant_id=" + encodeURIComponent(tenantId)
        : "";
    const appointmentsResponse = await fetch(
      "/api/appointments" + tenantQuery,
      { credentials: "same-origin" },
    );
    if (active !== operationalSequence) return;
    if (appointmentsResponse.ok)
      renderCalendar((await appointmentsResponse.json()).items || []);
    await CallHistory.setContext({
      tenantId,
      tenantName,
      balance,
      role: me.user.role,
    });
  } catch (error) {
    showToast(error.message || "Veriler yüklenemedi.");
  }
  if (active !== operationalSequence) return;
  loadProviders();
  loadSip();
  loadTelegram();
  loadCustomerTelegram();
  loadContacts();
  loadGoogleCalendar();
  loadKnowledge();
}

document.querySelector("#dashboard-tenant")?.addEventListener("change", (e) => {
  dashboardTenantId = Number(e.target.value) || 0;
  loadOperationalData();
});

const settingsPanel = document.querySelector("#settings");
let creditTenantId = 0;
if (settingsPanel) {
  const creditBlock = document.createElement("div");
  creditBlock.innerHTML =
    '<div class="panel-heading"><div><h2>Kredi yönetimi</h2><p>Aktif müşteriyi seçin; kredi bakiyesine ekleme veya düzeltme yapın.</p></div><span class="pill success">SaaS yönetimi</span></div><form id="credit-form" class="provider-form"><label>Müşteri<select id="credit-tenant" required><option value="">Henüz müşteri yok</option></select></label><label>Kredi miktarı<input id="credit-amount" type="number" step="0.01" required placeholder="100"></label><label>Açıklama<input id="credit-reason" value="Manuel kredi tanımı" required></label><button class="button primary" type="submit">Krediyi uygula</button><span id="credit-status" class="form-note"></span></form><div class="billing-rate-box"><div class="panel-heading"><div><h3>Kullanım tarifesi</h3><p>Çağrı kapanırken dakika bazında kredi düşümü uygulanır.</p></div></div><form id="billing-form" class="provider-form"><label>Kredi / dakika<input id="billing-rate" type="number" min="0" step="0.01" required></label><label>AI çarpanı<input id="billing-multiplier" type="number" min="0" step="0.01" required></label><label>Sunucu / saat<input id="billing-server" type="number" min="0" step="0.01" required></label><button class="button secondary" type="submit">Tarifeyi kaydet</button><span id="billing-status" class="form-note"></span></form></div><hr>';
  settingsPanel.insertBefore(creditBlock, settingsPanel.firstChild);
}
if (settingsPanel) {
  const legalBlock = document.createElement("div");
  legalBlock.id = "legal-settings";
  legalBlock.innerHTML =
    '<div class="panel-heading"><div><h2>Sözleşme, KVKK ve e-posta</h2><p>Müşteri kaydı için sözleşme/KVKK metinlerini ve hoş geldin e-postası SMTP bağlantısını yönetin.</p></div><span class="pill success">Yönetici</span></div><form id="legal-form" class="provider-form"><label>Kullanıcı sözleşmesi<textarea id="agreement-text" rows="6" required placeholder="Müşterinin kabul edeceği kullanıcı sözleşmesi"></textarea></label><label>KVKK aydınlatma metni<textarea id="kvkk-text" rows="6" required placeholder="KVKK aydınlatma metni"></textarea></label><div class="form-grid"><label>SMTP sunucusu<input id="smtp-host" placeholder="smtp.example.com"></label><label>Port<input id="smtp-port" type="number" min="1" max="65535" value="587"></label><label>SMTP kullanıcı adı<input id="smtp-user" autocomplete="off"></label><label>Gönderen e-posta<input id="smtp-from" type="email" placeholder="info@example.com"></label></div><label>SMTP parolası<input id="smtp-password" type="password" autocomplete="new-password" placeholder="Değiştirmek için girin"></label><button class="button primary" type="submit">Metin ve e-posta ayarlarını kaydet</button><span id="legal-status" class="form-note"></span></form><hr>';
  settingsPanel.insertBefore(legalBlock, settingsPanel.firstChild);
}
async function loadLegalSettings() {
  try {
    const r = await fetch("/api/admin/legal-settings", {
      credentials: "same-origin",
    });
    if (!r.ok) return;
    const d = await r.json();
    document.querySelector("#agreement-text").value = d.user_agreement || "";
    document.querySelector("#kvkk-text").value = d.kvkk_text || "";
    document.querySelector("#smtp-host").value = d.smtp_host || "";
    document.querySelector("#smtp-port").value = d.smtp_port || 587;
    document.querySelector("#smtp-user").value = d.smtp_username || "";
    document.querySelector("#smtp-from").value = d.smtp_from || "";
    document.querySelector("#legal-status").textContent =
      d.smtp_password_configured
        ? "SMTP parolası kayıtlı."
        : "SMTP parolası tanımlı değil.";
  } catch (_) {}
}
document.querySelector("#legal-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = document.querySelector("#legal-status");
  status.textContent = "Kaydediliyor…";
  const payload = {
    user_agreement: document.querySelector("#agreement-text").value,
    kvkk_text: document.querySelector("#kvkk-text").value,
    smtp_host: document.querySelector("#smtp-host").value,
    smtp_port: Number(document.querySelector("#smtp-port").value || 587),
    smtp_username: document.querySelector("#smtp-user").value,
    smtp_from: document.querySelector("#smtp-from").value,
    smtp_password: document.querySelector("#smtp-password").value,
  };
  try {
    const r = await fetch("/api/admin/legal-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error);
    document.querySelector("#smtp-password").value = "";
    status.textContent = d.smtp_password_configured
      ? "Ayarlar kaydedildi; SMTP parolası korumalı."
      : "Metinler kaydedildi; SMTP parolası henüz tanımlı değil.";
  } catch (err) {
    status.textContent = err.message || "Ayarlar kaydedilemedi";
  }
});
loadLegalSettings();
async function loadBilling() {
  try {
    const r = await fetch("/api/admin/billing", { credentials: "same-origin" });
    if (!r.ok) return;
    const d = await r.json();
    document.querySelector("#billing-rate").value = d.credits_per_minute ?? 1;
    document.querySelector("#billing-multiplier").value = d.ai_multiplier ?? 1;
    document.querySelector("#billing-server").value = d.server_hourly_rate ?? 0;
  } catch (_) {}
}
loadBilling();
document
  .querySelector("#billing-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#billing-status");
    status.textContent = "Kaydediliyor…";
    try {
      const payload = {
        credits_per_minute: Number(
          document.querySelector("#billing-rate").value,
        ),
        ai_multiplier: Number(
          document.querySelector("#billing-multiplier").value,
        ),
        server_hourly_rate: Number(
          document.querySelector("#billing-server").value,
        ),
      };
      const r = await fetch("/api/admin/billing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      status.textContent = "Kullanım tarifesi kaydedildi.";
    } catch (err) {
      status.textContent = err.message || "Tarife kaydedilemedi";
    }
  });
if (settingsPanel) {
  const ledgerBlock = document.createElement("div");
  ledgerBlock.innerHTML =
    '<div class="panel-heading"><div><h2>Kredi hareketleri</h2><p>Müşteri bazında kredi yükleme ve kullanım dökümleri.</p></div><span class="pill success">Son 200 işlem</span></div><div class="ledger-toolbar"><label>Müşteri<select id="ledger-tenant"><option value="">Henüz müşteri yok</option></select></label><label>Tür<select id="ledger-kind"><option value="">Tümü</option><option value="credit">Kredi</option><option value="debit">Kullanım</option></select></label><button class="button secondary" id="ledger-export" type="button">CSV indir</button></div><div class="table-wrap"><table><thead><tr><th>TARİH</th><th>TÜR</th><th>TUTAR</th><th>AÇIKLAMA</th></tr></thead><tbody id="ledger-body"><tr><td colspan="4">Hareketler yükleniyor…</td></tr></tbody></table></div><hr>';
  settingsPanel.insertBefore(ledgerBlock, settingsPanel.firstChild);
}
let ledgerItems = [];
async function loadLedger() {
  const body = document.querySelector("#ledger-body");
  if (!body) return;
  const tid = document.querySelector("#ledger-tenant")?.value || "2";
  const kind = document.querySelector("#ledger-kind")?.value || "";
  try {
    const r = await fetch(
      `/api/ledger?tenant_id=${encodeURIComponent(tid)}&kind=${encodeURIComponent(kind)}`,
      { credentials: "same-origin" },
    );
    const d = await r.json();
    if (!r.ok) throw Error(d.error);
    ledgerItems = d.items || [];
    body.innerHTML = ledgerItems.length
      ? ledgerItems
          .map(
            (x) =>
              `<tr><td>${formatMoment(x.created_at)}</td><td><span class="pill ${x.kind === "credit" ? "success" : "warning"}">${x.kind === "credit" ? "Kredi" : "Kullanım"}</span></td><td class="ledger-amount ${x.amount < 0 ? "negative" : "positive"}">${x.amount > 0 ? "+" : ""}${Number(x.amount).toFixed(2)}</td><td>${escapeHtml(x.reason || "—")}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="4">Bu müşteri için hareket yok.</td></tr>';
  } catch (err) {
    body.innerHTML = `<tr><td colspan="4">${escapeHtml(err.message || "Hareketler alınamadı")}</td></tr>`;
  }
}
document
  .querySelector("#ledger-tenant")
  ?.addEventListener("change", loadLedger);
document.querySelector("#ledger-kind")?.addEventListener("change", loadLedger);
loadLedger();
document.querySelector("#ledger-export")?.addEventListener("click", () => {
  const rows = [
    ["Tarih", "Tür", "Tutar", "Açıklama"],
    ...ledgerItems.map((x) => [
      formatMoment(x.created_at),
      x.kind === "credit" ? "Kredi" : "Kullanım",
      Number(x.amount).toFixed(2),
      x.reason || "",
    ]),
  ];
  const csv =
    "\\ufeff" +
    rows
      .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(";"))
      .join("\\r\\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "oim-kredi-hareketleri.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});
document.querySelector("#credit-tenant")?.addEventListener("change", (e) => {
  creditTenantId = Number(e.target.value);
});
document
  .querySelector("#credit-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#credit-status");
    status.textContent = "Uygulanıyor…";
    try {
      const amount = Number(document.querySelector("#credit-amount").value);
      const reason = document.querySelector("#credit-reason").value;
      if (!Number.isFinite(amount) || amount === 0)
        throw Error("Sıfırdan farklı bir kredi miktarı girin.");
      const r = await fetch(`/api/admin/tenants/${creditTenantId}/credits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ amount, reason }),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      status.textContent = `${d.tenant.name}: yeni bakiye ${Number(d.tenant.credits).toFixed(2)} kredi`;
      document.querySelector("#credit-amount").value = "";
      loadOperationalData();
    } catch (err) {
      status.textContent = err.message || "Kredi işlemi başarısız";
    }
  });

if (settingsPanel) {
  const telegramBlock = document.createElement("div");
  telegramBlock.id = "telegram";
  telegramBlock.dataset.viewPanel = "telegram";
  telegramBlock.innerHTML =
    '<div class="panel-heading"><div><h2>Telegram çağrı kayıtları</h2><p>Gelen çağrı kayıtlarını belirlediğiniz özel gruba otomatik gönderir.</p></div></div><form id="telegram-form" class="provider-form"><label>Bot tokeni<input id="telegram-token" type="password" autocomplete="new-password" placeholder="Değiştirmek için girin"></label><label>Grup Chat ID<input id="telegram-chat" placeholder="-100..."></label><label class="check"><input id="telegram-enabled" type="checkbox"> Kayıt gönderimini etkinleştir</label><button class="button primary" type="submit">Telegram ayarlarını kaydet</button><span id="telegram-status" class="form-note"></span></form><hr>';
  settingsPanel.insertBefore(telegramBlock, settingsPanel.firstChild);
}
async function loadTelegram() {
  try {
    const r = await fetch("/api/admin/telegram", {
      credentials: "same-origin",
    });
    if (!r.ok) return;
    const d = await r.json();
    document.querySelector("#telegram-chat").value = d.chat_id || "";
    document.querySelector("#telegram-enabled").checked = Boolean(d.enabled);
    document.querySelector("#telegram-status").textContent = d.configured
      ? `Kayıtlı token: ${d.masked}`
      : "Telegram botu tanımlı değil";
  } catch (_) {}
}
document
  .querySelector("#telegram-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#telegram-status");
    status.textContent = "Doğrulanıyor…";
    const payload = {
      bot_token: document.querySelector("#telegram-token").value,
      chat_id: document.querySelector("#telegram-chat").value,
      enabled: document.querySelector("#telegram-enabled").checked,
    };
    try {
      const r = await fetch("/api/admin/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      document.querySelector("#telegram-token").value = "";
      status.textContent = `@${d.bot_username} kaydedildi (${d.masked})`;
    } catch (err) {
      status.textContent = err.message || "Telegram ayarı kaydedilemedi";
    }
  });
let crmItems = [];
function renderContacts() {
  const body = document.querySelector("#contacts-body");
  if (!body) return;
  const qName = (document.querySelector("#crm-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const qPhone = (document.querySelector("#crm-phone-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const qEmail = (document.querySelector("#crm-email-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const items = crmItems.filter(
    (x) =>
      (!qName ||
        String(x.name || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qName)) &&
      (!qPhone ||
        String(x.phone || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qPhone)) &&
      (!qEmail ||
        String(x.email || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qEmail)),
  );
  body.innerHTML = items.length
    ? items
        .map(
          (x) =>
            "<tr><td><strong>" +
            escapeHtml(x.name) +
            "</strong></td><td>" +
            escapeHtml(x.phone || "—") +
            "</td><td>" +
            escapeHtml(x.email || "—") +
            "</td><td>" +
            escapeHtml(x.notes || "—") +
            '</td><td><div class="crm-actions"><button class="button outline" type="button" data-edit-contact="' +
            x.id +
            '">Düzenle</button><button class="button secondary" type="button" data-delete-contact="' +
            x.id +
            '">Sil</button></div></td></tr>',
        )
        .join("")
    : '<tr><td colspan="5">' +
      (crmItems.length
        ? "Filtreye uygun müşteri yok."
        : "Henüz CRM kaydı yok.") +
      "</td></tr>";
}
async function loadContacts() {
  const body = document.querySelector("#contacts-body");
  if (!body) return;
  try {
    const r = await fetch("/api/contacts", { credentials: "same-origin" });
    if (!r.ok) return;
    const d = await r.json();
    crmItems = d.items || [];
    renderContacts();
  } catch (_) {}
}
document
  .querySelector("#crm-filter")
  ?.addEventListener("input", renderContacts);
document.querySelector("#crm-filter-clear")?.addEventListener("click", () => {
  ["#crm-filter", "#crm-phone-filter", "#crm-email-filter"].forEach((sel) => {
    const f = document.querySelector(sel);
    if (f) f.value = "";
  });
  renderContacts();
});
document
  .querySelector("#crm-phone-filter")
  ?.addEventListener("input", renderContacts);
document
  .querySelector("#crm-email-filter")
  ?.addEventListener("input", renderContacts);
document.querySelector("#crm-export")?.addEventListener("click", () => {
  const qName = (document.querySelector("#crm-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const qPhone = (document.querySelector("#crm-phone-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const qEmail = (document.querySelector("#crm-email-filter")?.value || "")
    .trim()
    .toLocaleLowerCase(OIMI18n.localeTag());
  const items = crmItems.filter(
    (x) =>
      (!qName ||
        String(x.name || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qName)) &&
      (!qPhone ||
        String(x.phone || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qPhone)) &&
      (!qEmail ||
        String(x.email || "")
          .toLocaleLowerCase(OIMI18n.localeTag())
          .includes(qEmail)),
  );
  const rows = [
    ["Ad Soyad", "Telefon", "E-posta", "Not"],
    ...items.map((x) => [
      x.name || "",
      x.phone || "",
      x.email || "",
      x.notes || "",
    ]),
  ];
  const csv =
    "\\ufeff" +
    rows
      .map((r) =>
        r.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(";"),
      )
      .join("\\r\\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "oim-crm.xls";
  a.click();
  URL.revokeObjectURL(a.href);
});
document
  .querySelector("#customer-telegram-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#customer-telegram-status");
    status.textContent = "Doğrulanıyor…";
    const payload = {
      bot_token: document.querySelector("#customer-telegram-token").value,
      chat_id: document.querySelector("#customer-telegram-chat").value,
      enabled: document.querySelector("#customer-telegram-enabled").checked,
    };
    try {
      const r = await fetch("/api/tenant/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      document.querySelector("#customer-telegram-token").value = "";
      status.textContent = `@${d.bot_username} bağlandı (${d.masked})`;
    } catch (err) {
      status.textContent = err.message || "Telegram ayarı kaydedilemedi";
    }
  });
document
  .querySelector("#contact-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#contact-status");
    status.textContent = "Kaydediliyor…";
    const payload = {
      name: document.querySelector("#contact-name").value,
      phone: document.querySelector("#contact-phone").value,
      email: document.querySelector("#contact-email").value,
      notes: document.querySelector("#contact-notes").value,
    };
    try {
      const r = await fetch("/api/contacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      e.target.reset();
      status.textContent = "CRM kaydı eklendi.";
      loadContacts();
    } catch (err) {
      status.textContent = err.message || "CRM kaydı eklenemedi";
    }
  });
document
  .querySelector("#contacts-body")
  ?.addEventListener("click", async (e) => {
    const button = e.target.closest(
      "[data-delete-contact],[data-edit-contact]",
    );
    if (!button) return;
    const id = Number(
      button.dataset.deleteContact || button.dataset.editContact,
    );
    const item = crmItems.find((x) => Number(x.id) === id);
    if (!item) return;
    if (button.dataset.deleteContact) {
      if (!confirm(OIMI18n.t("Bu CRM kaydı silinsin mi?"))) return;
      const r = await fetch("/api/contacts/" + id + "/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: "{}",
      });
      if (r.ok) {
        showToast("CRM kaydı silindi.");
        loadContacts();
      }
      return;
    }
    const name = prompt(OIMI18n.t("Ad soyad"), item.name) || item.name;
    const phone = prompt(OIMI18n.t("Telefon"), item.phone || "") ?? item.phone;
    const email = prompt(OIMI18n.t("E-posta"), item.email || "") ?? item.email;
    const notes = prompt(OIMI18n.t("Not"), item.notes || "") ?? item.notes;
    const r = await fetch("/api/contacts/" + id + "/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ name, phone, email, notes }),
    });
    if (r.ok) {
      showToast("CRM kaydı güncellendi.");
      loadContacts();
    } else {
      showToast("CRM kaydı güncellenemedi.");
    }
  });
async function loadGoogleCalendar() {
  const status = document.querySelector("#google-status");
  if (!status) return;
  try {
    const r = await fetch("/api/google/status", { credentials: "same-origin" });
    const d = await r.json();
    if (!d.configured) {
      status.textContent =
        "Google OAuth yönetici tarafından henüz yapılandırılmadı.";
      return;
    }
    status.textContent = d.connected
      ? "Google Calendar bağlı. Dolu saatler korunuyor."
      : "Google Calendar bağlı değil.";
  } catch (_) {
    status.textContent = "Takvim durumu alınamadı.";
  }
}
document
  .querySelector("#google-connect")
  ?.addEventListener("click", async () => {
    const status = document.querySelector("#google-status");
    status.textContent = "Google bağlantısı hazırlanıyor…";
    try {
      const r = await fetch("/api/google/start", {
        credentials: "same-origin",
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      location.href = d.url;
    } catch (err) {
      status.textContent = err.message || "Google bağlantısı başlatılamadı";
    }
  });
async function loadKnowledge() {
  const body = document.querySelector("#knowledge-body");
  if (!body) return;
  try {
    const r = await fetch("/api/knowledge", { credentials: "same-origin" });
    if (!r.ok) return;
    const d = await r.json();
    body.innerHTML = d.items.length
      ? d.items
          .map(
            (x) =>
              `<tr><td>${escapeHtml(x.language.toUpperCase())}</td><td><strong>${escapeHtml(x.title)}</strong></td><td><span class="pill ${x.status === "published" ? "success" : "warning"}">${x.status === "published" ? "Yayında" : "Taslak"}</span></td><td>${formatMoment(x.updated_at)}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="4">Henüz bilgi bankası içeriği yok.</td></tr>';
  } catch (_) {}
}
document
  .querySelector("#knowledge-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#knowledge-status");
    status.textContent = "Kaydediliyor…";
    const payload = {
      language: document.querySelector("#knowledge-language").value,
      title: document.querySelector("#knowledge-title").value,
      content: document.querySelector("#knowledge-content").value,
      status: document.querySelector("#knowledge-published").checked
        ? "published"
        : "draft",
    };
    try {
      const r = await fetch("/api/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      status.textContent = "Bilgi bankasına kaydedildi.";
      loadKnowledge();
    } catch (err) {
      status.textContent = err.message || "Bilgi bankası kaydedilemedi";
    }
  });
const sipForm = document.querySelector("#sip-form");
const sipStatus = document.querySelector("#sip-status");
let sipTenantId = 0;
async function loadSip() {
  try {
    const r = await fetch(`/api/admin/tenants/${sipTenantId}/sip`, {
      credentials: "same-origin",
    });
    if (!r.ok) return;
    const d = await r.json();
    document.querySelector("#sip-username").value = d.username || "";
    document.querySelector("#sip-did").value = d.did || d.username || "";
    document.querySelector("#sip-domain").value = d.domain || "";
    sipStatus.textContent = d.configured
      ? `Kayıtlı parola: ${d.masked}`
      : "SIP parolası tanımlı değil";
  } catch (_) {}
}
sipForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  sipStatus.textContent = "Kaydediliyor…";
  const payload = {
    username: document.querySelector("#sip-username").value,
    did: document.querySelector("#sip-did").value,
    domain: document.querySelector("#sip-domain").value,
    password: document.querySelector("#sip-password").value,
  };
  try {
    const r = await fetch(`/api/admin/tenants/${sipTenantId}/sip`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error);
    document.querySelector("#sip-password").value = "";
    sipStatus.textContent = `Kaydedildi (${d.masked || "parola yok"})`;
  } catch (err) {
    sipStatus.textContent = err.message || "Kayıt başarısız";
  }
});
loadSip();

const customersBody = document.querySelector("#customers-body");
const customerForm = document.querySelector("#customer-form");
if (customerForm && !document.querySelector("#customer-agreement")) {
  const row = document.createElement("label");
  row.className = "check";
  row.innerHTML =
    '<input id="customer-agreement" type="checkbox" required> Kullanıcı sözleşmesi ve KVKK metinlerini müşteriye sundum ve onayını aldım';
  const submit = customerForm.querySelector('button[type="submit"]');
  submit?.parentNode.insertBefore(row, submit);
}
function loadCustomers(items = []) {
  if (!customersBody) return;
  customersBody.innerHTML = items.length
    ? items
        .map(
          (item) =>
            `<tr><td><strong>${escapeHtml(item.name)}</strong></td><td>${escapeHtml(item.username)}</td><td>${escapeHtml(item.email || "—")}</td><td>${Number(item.credits || 0).toFixed(2)}</td><td><span class="pill ${item.status === "active" ? "success" : "warning"}">${item.status === "active" ? "Aktif" : "Pasif"}</span></td><td><div class="password-reset"><input type="password" minlength="8" autocomplete="new-password" placeholder="Yeni parola" data-password-for="${item.id}"><button class="button secondary" type="button" data-reset-password="${item.id}">Değiştir</button></div></td></tr>`,
        )
        .join("")
    : '<tr><td colspan="6">Henüz müşteri hesabı yok.</td></tr>';
  const selector = document.querySelector("#sip-tenant");
  if (selector) {
    selector.innerHTML = items
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.name)} (${escapeHtml(item.username)})</option>`,
      )
      .join("");
    if (items.length) {
      selector.value = String(sipTenantId);
      if (!selector.value) sipTenantId = items[0].id;
      loadSip();
    }
  }
  const creditSelector = document.querySelector("#credit-tenant");
  if (creditSelector) {
    creditSelector.innerHTML = items
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.name)} — ${Number(item.credits || 0).toFixed(2)} kredi</option>`,
      )
      .join("");
    if (items.length) {
      creditSelector.value = String(creditTenantId);
      if (!creditSelector.value) creditTenantId = items[0].id;
    }
  }
}
document.querySelector("#sip-tenant")?.addEventListener("change", (e) => {
  sipTenantId = Number(e.target.value);
  loadSip();
});
document
  .querySelector("#customer-form")
  ?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = document.querySelector("#customer-status");
    status.textContent = "Hesap oluşturuluyor…";
    const payload = {
      name: document.querySelector("#customer-name").value,
      email: document.querySelector("#customer-email").value,
      username: document.querySelector("#customer-username").value,
      password: document.querySelector("#customer-password").value,
      credits: Number(document.querySelector("#customer-credits").value || 0),
      agreement_accepted: Boolean(
        document.querySelector("#customer-agreement")?.checked,
      ),
    };
    try {
      const r = await fetch("/api/admin/tenants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      status.textContent = `${d.tenant.name} oluşturuldu. Kullanıcı: ${d.tenant.username}`;
      e.target.reset();
      document.querySelector("#customer-credits").value = "0";
      loadOperationalData();
    } catch (err) {
      status.textContent = err.message || "Müşteri oluşturulamadı";
    }
  });
customersBody?.addEventListener("click", async (e) => {
  const button = e.target.closest("[data-reset-password]");
  if (!button) return;
  const id = button.dataset.resetPassword;
  const input = customersBody.querySelector(`[data-password-for="${id}"]`);
  const password = input?.value || "";
  if (password.length < 8) {
    showToast("Parola en az 8 karakter olmalı.");
    return;
  }
  button.disabled = true;
  try {
    const r = await fetch(`/api/admin/tenants/${id}/password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ password }),
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error);
    input.value = "";
    showToast("Müşteri parolası değiştirildi.");
  } catch (err) {
    showToast(err.message || "Parola değiştirilemedi.");
  } finally {
    button.disabled = false;
  }
});
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}
document
  .querySelector("[data-open-customers]")
  ?.addEventListener("click", () => {
    document
      .querySelector("#customers")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
    document.querySelector("#customer-name")?.focus();
  });
document.querySelector(".more-button")?.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
  location.reload();
});
document
  .querySelector(".profile-chip")
  ?.addEventListener("dblclick", async () => {
    if (
      !confirm(
        OIMI18n.t("Bu kullanıcıya ait tüm aktif oturumlar kapatılsın mı?"),
      )
    )
      return;
    const r = await fetch("/api/logout-all", {
      method: "POST",
      credentials: "same-origin",
    });
    if (r.ok) location.reload();
  });
const reportButton = document.querySelector("#report-button");
async function downloadReport(event) {
  const reportButton = event.currentTarget;
  event.preventDefault();
  reportButton.disabled = true;
  const originalKey =
    reportButton.id === "call-export" ? "CSV indir" : "Rapor al";
  reportButton.textContent = OIMI18n.t("Rapor hazırlanıyor…");
  try {
    const report = await CallHistory.collectAll();
    const query =
      report.scope.role === "admin"
        ? "?tenant_id=" + encodeURIComponent(report.scope.tenantId)
        : "";
    const response = await fetch("/api/appointments" + query, {
      credentials: "same-origin",
    });
    if (!response.ok) throw Error(OIMI18n.t("Randevular yüklenemedi."));
    const appointments = (await response.json()).items || [];
    const t = OIMI18n.t;
    const rows = [
      [t("Oluşturulma zamanı (UTC)"), new Date().toISOString()],
      [t("Çağrı kapsamı"), JSON.stringify(report.filters)],
      [t("Eşleşen çağrı sayısı"), report.summary.total_calls],
      [
        t("Randevu kapsamı"),
        t("Seçili müşterinin son 100 randevusu; çağrı filtreleri uygulanmaz."),
      ],
      [],
      [
        t("Kayıt türü"),
        t("Tarih (UTC)"),
        t("Müşteri"),
        t("Telefon"),
        t("Hizmet"),
        t("Süre"),
        t("Kredi"),
        t("Durum"),
      ],
    ];
    const reportDate = (value) =>
      OIMI18n.date(
        typeof value === "number" ? new Date(value * 1000) : new Date(value),
        { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" },
      );
    for (const call of report.items)
      rows.push([
        t("Çağrı"),
        reportDate(call.started_at),
        report.scope.tenantName,
        call.caller || "",
        "",
        formatDuration(call.started_at, call.ended_at),
        Number(call.billed_credits || 0).toFixed(2),
        call.status,
      ]);
    for (const item of appointments)
      rows.push([
        t("Randevu"),
        reportDate(item.appointment_at),
        item.customer_name,
        item.phone,
        item.service,
        "",
        "",
        item.status,
      ]);
    const quote = (value) => {
      let text = String(value ?? "");
      if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
      return '"' + text.replace(/"/g, '""') + '"';
    };
    const csv =
      "\ufeff" + rows.map((row) => row.map(quote).join(";")).join("\r\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download =
      "oim-report-" + new Date().toISOString().slice(0, 10) + ".csv";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast(
      OIMI18n.t("{0} kayıt rapora aktarıldı.", {
        0: report.items.length + appointments.length,
      }),
    );
  } catch (error) {
    showToast(error.message || OIMI18n.t("Rapor oluşturulamadı."));
  } finally {
    reportButton.disabled = false;
    reportButton.textContent = OIMI18n.t(originalKey);
  }
}
for (const id of ["report-button", "call-export"])
  document.getElementById(id)?.addEventListener("click", downloadReport);

document.querySelectorAll("[data-toast]").forEach((button) => {
  button.addEventListener("click", () => {
    showToast(button.dataset.toast);
  });
});

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", (event) => {
    event.preventDefault();
    setView(item.dataset.view || "dashboard");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});
setView(location.hash.slice(1) || "dashboard");
async function loadCustomerTelegram() {
  try {
    const r = await fetch("/api/tenant/telegram", {
      credentials: "same-origin",
    });
    if (!r.ok) return;
    const d = await r.json();
    const chat = document.querySelector("#customer-telegram-chat");
    const enabled = document.querySelector("#customer-telegram-enabled");
    const status = document.querySelector("#customer-telegram-status");
    if (chat) chat.value = d.chat_id || "";
    if (enabled) enabled.checked = Boolean(d.enabled);
    if (status)
      status.textContent = d.configured
        ? `Kayıtlı token: ${d.masked}`
        : "Telegram botu tanımlı değil";
  } catch (_) {}
}
function ensureCrmControls() {
  const panel = document.querySelector("#crm");
  if (!panel || document.querySelector("#crm-filter")) return;
  const form = panel.querySelector("#contact-form");
  if (!form) return;
  const controls = document.createElement("div");
  controls.className = "crm-toolbar";
  controls.innerHTML =
    '<input id="crm-filter" placeholder="Ad soyada göre filtrele" aria-label="Ad soyada göre filtrele"><input id="crm-phone-filter" placeholder="Telefon" aria-label="Telefon filtresi"><input id="crm-email-filter" placeholder="E-posta" aria-label="E-posta filtresi"><select id="crm-sort" aria-label="CRM sıralama"><option value="updated">Son güncellenen</option><option value="name">Ada göre</option></select><button class="button outline" type="button" id="crm-filter-clear">Temizle</button><span class="form-note" id="crm-result-count"></span>';
  form.insertAdjacentElement("afterend", controls);
  const rerender = () => {
    const sort = document.querySelector("#crm-sort")?.value || "updated";
    crmItems.sort((a, b) =>
      sort === "name"
        ? String(a.name || "").localeCompare(String(b.name || ""), "tr")
        : Number(b.updated_at || 0) - Number(a.updated_at || 0),
    );
    renderContacts();
    const count = document.querySelector("#crm-result-count");
    if (count)
      count.textContent = `${document.querySelectorAll("#contacts-body tr").length} kayıt`;
  };
  [
    "#crm-filter",
    "#crm-phone-filter",
    "#crm-email-filter",
    "#crm-sort",
  ].forEach((sel) =>
    document.querySelector(sel)?.addEventListener("input", rerender),
  );
  document.querySelector("#crm-filter-clear")?.addEventListener("click", () => {
    ["#crm-filter", "#crm-phone-filter", "#crm-email-filter"].forEach((sel) => {
      const f = document.querySelector(sel);
      if (f) f.value = "";
    });
    rerender();
  });
}
ensureCrmControls();
function addTelegramTest(formId, endpoint, statusId) {
  const form = document.querySelector(formId);
  if (!form || form.querySelector("[data-telegram-test]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button outline";
  button.dataset.telegramTest = "1";
  button.textContent = "Bağlantıyı test et";
  form.appendChild(button);
  button.addEventListener("click", async () => {
    const status = document.querySelector(statusId);
    if (status) status.textContent = "Telegram bağlantısı test ediliyor…";
    try {
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: "{}",
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      if (status)
        status.textContent = `${d.bot_username} → ${d.chat_title} doğrulandı (${d.bot_status}).`;
    } catch (err) {
      if (status)
        status.textContent =
          err.message || "Telegram bağlantısı test edilemedi.";
    }
  });
}
addTelegramTest(
  "#telegram-form",
  "/api/admin/telegram/test",
  "#telegram-status",
);
addTelegramTest(
  "#customer-telegram-form",
  "/api/tenant/telegram/test",
  "#customer-telegram-status",
);
const aiSettingsForm = document.querySelector("#ai-settings-form");
const aiSettingsFields = document.querySelector("#ai-settings-fields");
const aiGreeting = document.querySelector("#ai-greeting");
const aiSettingsStatus = document.querySelector("#ai-settings-status");
const agentSettingsCard = document.querySelector(".agents-panel");
if (agentSettingsCard) {
  const shortcut = document.createElement("button");
  shortcut.type = "button";
  shortcut.className = "button secondary full";
  shortcut.dataset.customerOnly = "";
  shortcut.hidden = true;
  shortcut.textContent = "Açılış mesajını düzenle";
  shortcut.addEventListener("click", () => {
    setView("opening-message");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  agentSettingsCard.appendChild(shortcut);
}
let aiSettingsTenant = null;
let aiSettingsLoading = false;
function updateGreetingCount() {
  document.querySelector("#ai-greeting-count").textContent =
    `${aiGreeting.value.length} / 1000 karakter`;
}
async function loadAiSettings(force = false) {
  if (
    !aiSettingsForm ||
    currentUser?.role !== "customer" ||
    aiSettingsLoading ||
    (!force && aiSettingsTenant === currentUser.id)
  )
    return;
  const tenantId = currentUser.id;
  aiSettingsLoading = true;
  aiSettingsFields.disabled = true;
  aiSettingsStatus.textContent = "Mesaj yükleniyor…";
  aiSettingsStatus.dataset.state = "loading";
  document.querySelector("#ai-settings-retry").hidden = true;
  try {
    const r = await fetch("/api/tenant/ai-settings", {
      credentials: "same-origin",
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error || "Ayarlar yüklenemedi.");
    if (currentUser?.id !== tenantId) return;
    aiGreeting.value = d.greeting || "";
    document.querySelector("#ai-voice").value = d.voice || "alloy";
    document.querySelector("#ai-hours").value = d.working_hours || "";
    aiSettingsTenant = tenantId;
    updateGreetingCount();
    aiSettingsFields.disabled = false;
    aiSettingsStatus.dataset.state = "ready";
    aiSettingsStatus.textContent = aiGreeting.value
      ? "Kayıtlı açılış mesajınız yüklendi."
      : "Karşılama metninizi yazıp kaydedin.";
  } catch (err) {
    aiSettingsStatus.dataset.state = "error";
    aiSettingsStatus.textContent =
      err.message || "Mesaj yüklenemedi. Yeniden deneyin.";
    document.querySelector("#ai-settings-retry").hidden = false;
  } finally {
    aiSettingsLoading = false;
  }
}
document
  .querySelector("#ai-settings-retry")
  ?.addEventListener("click", () => loadAiSettings(true));
aiSettingsForm?.addEventListener("input", () => {
  aiGreeting.setCustomValidity("");
  updateGreetingCount();
  aiSettingsStatus.dataset.state = "dirty";
  aiSettingsStatus.textContent = "Kaydedilmemiş değişiklikler var.";
});
aiSettingsForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (aiSettingsFields.disabled || currentUser?.role !== "customer") return;
  if (!aiGreeting.value.trim()) {
    aiGreeting.setCustomValidity(
      OIMI18n.t("Lütfen bir karşılama metni yazın."),
    );
    aiGreeting.reportValidity();
    return;
  }
  const payload = {
    greeting: aiGreeting.value.trim(),
    voice: document.querySelector("#ai-voice").value,
    working_hours: document.querySelector("#ai-hours").value,
  };
  aiSettingsFields.disabled = true;
  aiSettingsStatus.dataset.state = "loading";
  aiSettingsStatus.textContent = "Kaydediliyor…";
  aiSettingsForm.setAttribute("aria-busy", "true");
  try {
    const r = await fetch("/api/tenant/ai-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error || "Mesaj kaydedilemedi.");
    aiGreeting.value = d.greeting;
    updateGreetingCount();
    aiSettingsStatus.dataset.state = "success";
    aiSettingsStatus.textContent =
      "Kaydedildi. Yeni çağrılar bu mesajla başlayacak.";
    window.dispatchEvent(new Event("oim:ai-settings-updated"));
  } catch (err) {
    aiSettingsStatus.dataset.state = "error";
    aiSettingsStatus.textContent =
      err.message ||
      "Mesaj kaydedilemedi. Metniniz korunuyor; yeniden deneyin.";
  } finally {
    aiSettingsFields.disabled = false;
    aiSettingsForm.setAttribute("aria-busy", "false");
  }
});
const knowledgeContent = document.querySelector("#knowledge-content");
if (knowledgeContent && !document.querySelector("#knowledge-file")) {
  const label = document.createElement("label");
  label.textContent = "Markdown dosyası yükle";
  label.innerHTML +=
    '<input id="knowledge-file" type="file" accept=".md,.markdown,text/markdown">';
  knowledgeContent.insertAdjacentElement("afterend", label);
  document
    .querySelector("#knowledge-file")
    .addEventListener("change", (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (!/\.(md|markdown)$/i.test(file.name)) {
        showToast("Yalnızca .md veya .markdown dosyası yükleyin.");
        event.target.value = "";
        return;
      }
      if (file.size > 512000) {
        showToast("Bilgi bankası dosyası 500 KB altında olmalı.");
        event.target.value = "";
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        knowledgeContent.value = String(reader.result || "");
        const title = document.querySelector("#knowledge-title");
        if (title && !title.value)
          title.value = file.name.replace(/\.(md|markdown)$/i, "");
      };
      reader.readAsText(file, "UTF-8");
    });
}
const crmObserver = new MutationObserver(() =>
  document.querySelectorAll("#contacts-body tr").forEach((row) => {
    const action = row.querySelector(".crm-actions");
    if (action && !action.querySelector("[data-detail-contact]")) {
      const name = row.querySelector("strong")?.textContent || "";
      const item = crmItems.find((x) => x.name === name);
      if (item) {
        const button = document.createElement("button");
        button.className = "button outline";
        button.type = "button";
        button.dataset.detailContact = item.id;
        button.textContent = "Detay";
        action.prepend(button);
      }
    }
  }),
);
const crmBody = document.querySelector("#contacts-body");
if (crmBody) crmObserver.observe(crmBody, { childList: true, subtree: true });
document
  .querySelector("#contacts-body")
  ?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-detail-contact]");
    if (!button) return;
    const id = Number(button.dataset.detailContact);
    const r = await fetch("/api/contacts/" + id, {
      credentials: "same-origin",
    });
    const d = await r.json();
    if (!r.ok) {
      showToast(d.error || "Detay alınamadı.");
      return;
    }
    const callText = d.calls.length
      ? d.calls
          .map(
            (x) =>
              `${formatMoment(x.started_at)} — ${x.status} — ${Number(x.billed_credits || 0).toFixed(2)} kredi`,
          )
          .join("\n")
      : "Çağrı kaydı yok";
    const apptText = d.appointments.length
      ? d.appointments
          .map((x) => `${x.appointment_at} — ${x.service} — ${x.status}`)
          .join("\n")
      : "Randevu yok";
    alert(
      `${d.contact.name}\n\nNot: ${d.contact.notes || "—"}\n\nÇağrılar:\n${callText}\n\nRandevular:\n${apptText}`,
    );
  });
/* üst profil menüsü */
function updateProfileLabels(user) {
  const company =
    user?.role === "admin" ? "AI Call Center" : user?.name || "Müşteri";
  const initials = String(company)
    .split(/\s+/)
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  document
    .querySelector("#top-company-name")
    ?.replaceChildren(document.createTextNode(company));
  document
    .querySelector("#sidebar-company-name")
    ?.replaceChildren(document.createTextNode(company));
  document
    .querySelector(".profile-avatar")
    ?.replaceChildren(document.createTextNode(initials));
  document
    .querySelector(".user-avatar")
    ?.replaceChildren(document.createTextNode(initials));
  const role = document.querySelector("#sidebar-user-role");
  if (role)
    role.textContent = user?.role === "admin" ? "Yönetici" : "Müşteri hesabı";
}
const _applyUser = applyUser;
applyUser = function (user) {
  _applyUser(user);
  updateProfileLabels(user);
  if (user?.role === "customer") loadAiSettings();
  else {
    aiSettingsTenant = null;
    if (location.hash === "#opening-message") setView("dashboard");
  }
};
document.querySelector(".profile-chip")?.addEventListener("click", () => {
  const menu = document.querySelector(".profile-menu");
  if (!menu) return;
  const open = menu.hidden;
  menu.hidden = !open;
  document
    .querySelector(".profile-chip")
    .setAttribute("aria-expanded", String(open));
});
document
  .querySelector("[data-profile-settings]")
  ?.addEventListener("click", () => {
    document.querySelector(".profile-menu").hidden = true;
    setView("settings");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
document
  .querySelector("[data-profile-logout]")
  ?.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
    location.reload();
  });
document
  .querySelector(".notification-button")
  ?.addEventListener("click", () => showToast("Yeni bildirim bulunmuyor."));

window.addEventListener("oim:localechange", () => {
  if (currentUser) applyUser(currentUser);
  renderCalendar(calendarItems);
  renderContacts();
  if (todayLabel)
    todayLabel.textContent = OIMI18n.date(new Date(), {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "Europe/Istanbul",
    }).toLocaleUpperCase(OIMI18n.localeTag());
});

document.querySelector("#mobile-view")?.addEventListener("change", (event) => {
  setView(event.target.value);
  window.scrollTo({ top: 0, behavior: "smooth" });
});
