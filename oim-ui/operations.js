(function (root) {
  "use strict";
  const t = (key, params) => root.OIMI18n.t(key, params);
  const $ = (selector) => document.querySelector(selector);
  const status = (selector, message) => {
    const node = $(selector);
    if (node) node.textContent = message;
  };
  let context = null;
  let tenantOptions = [];
  let latestUsage = null;
  let requestSequence = 0;
  let lastLiveSignature = null;
  const dateInput = (date) => date.toISOString().slice(0, 10);

  async function request(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    const body = await response.json();
    if (!response.ok) throw Error(body.error || t("İstek tamamlanamadı."));
    return body;
  }
  async function getContext() {
    const me = await request("/api/me");
    let tenantId = Number(me.user.id);
    let tenantName = me.user.name;
    if (me.user.role === "admin") {
      const list = await request("/api/admin/tenants");
      tenantOptions = list.items || [];
      const selector = $("#dashboard-tenant");
      tenantId = Number(selector?.value) || Number(tenantOptions[0]?.id) || 0;
      tenantName =
        tenantOptions.find((item) => Number(item.id) === tenantId)?.name || "";
    }
    return { role: me.user.role, tenantId, tenantName };
  }
  function tenantQuery(value = context?.tenantId) {
    return context?.role === "admin"
      ? `?tenant_id=${encodeURIComponent(value || 0)}`
      : "";
  }
  function fillUsageTenants() {
    const select = $("#usage-tenant");
    if (!select) return;
    const isAdmin = context?.role === "admin";
    $("#usage-tenant-heading").hidden = !isAdmin;
    $("#usage-tenant-table").hidden = !isAdmin;
    if (!isAdmin) return;
    const previous = select.value;
    select.replaceChildren(new Option(t("Tüm müşteriler"), ""));
    for (const tenant of tenantOptions)
      select.add(new Option(tenant.name, String(tenant.id)));
    select.value = tenantOptions.some(
      (tenant) => String(tenant.id) === previous,
    )
      ? previous
      : "";
    $("#usage-tenant-heading").hidden = false;
    $("#usage-tenant-table").hidden = false;
  }
  function renderReadiness(data) {
    const labels = {
      sip: t("SIP hesabı bilgileri"),
      provider: t("AI sağlayıcı anahtarı"),
      greeting: t("Açılış mesajı"),
      knowledge: t("Yayınlanmış bilgi bankası"),
    };
    const routes =
      context.role === "admin"
        ? {
            sip: "sip",
            provider: "settings",
            greeting: "help",
            knowledge: "help",
          }
        : {
            sip: "help",
            provider: "help",
            greeting: "opening-message",
            knowledge: "knowledge",
          };
    const list = $("#readiness-checks");
    if (!list) return;
    list.replaceChildren();
    let readyCount = 0;
    for (const item of data.checks || []) {
      readyCount += Number(Boolean(item.ready));
      const row = document.createElement("div");
      row.className = "readiness-item";
      const icon = document.createElement("span");
      icon.className = item.ready
        ? "readiness-icon ready"
        : "readiness-icon missing";
      icon.textContent = item.ready ? "✓" : "!";
      icon.setAttribute("aria-hidden", "true");
      const name = document.createElement("span");
      name.textContent = labels[item.key] || item.key;
      const state = document.createElement("span");
      state.className = item.ready ? "pill success" : "pill warning";
      state.textContent = item.ready ? t("Hazır") : t("Eksik");
      const link = document.createElement("a");
      link.className = "readiness-action";
      link.href = `#${routes[item.key] || "help"}`;
      link.textContent = t("Ayarı aç");
      link.addEventListener("click", (event) => {
        event.preventDefault();
        root.OIMSetView?.(routes[item.key] || "help");
      });
      row.append(icon, name, state, link);
      list.append(row);
    }
    $("#setup-tenant-name").textContent =
      data.tenant_name || context.tenantName;
    $("#readiness-count").textContent = t("{0}/{1} hazır", {
      0: readyCount,
      1: (data.checks || []).length,
    });
    $("#readiness-progress").style.width =
      `${data.checks?.length ? (readyCount / data.checks.length) * 100 : 0}%`;
  }
  async function loadReadiness(active) {
    if (!context?.tenantId) return;
    const data = await request("/api/readiness" + tenantQuery());
    if (active !== requestSequence) return;
    renderReadiness(data);
    const settings = await request("/api/tenant/ai-settings" + tenantQuery());
    if (active !== requestSequence) return;
    const preview = $("#greeting-preview");
    if (preview)
      preview.textContent =
        settings.greeting || t("Henüz açılış mesajı kaydedilmedi.");
  }
  function formatTime(timestamp) {
    if (!timestamp) return "—";
    return new Intl.DateTimeFormat(root.OIMI18n.localeTag(), {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC",
    }).format(new Date(timestamp * 1000));
  }
  function lineCard(title, detail, tone = "") {
    const article = document.createElement("article");
    article.className = `monitor-item ${tone}`;
    const heading = document.createElement("strong");
    heading.textContent = title;
    const description = document.createElement("span");
    description.textContent = detail;
    article.append(heading, description);
    return article;
  }
  function failureMessage(code, fallback) {
    const known = {
      provider_error:
        "AI sağlayıcısı çağrıyı tamamlayamadı. Sağlayıcı ayarlarını ve çağrı kayıtlarını kontrol edin.",
      accept_failed:
        "Çağrı AI sağlayıcısına bağlanamadı. Sağlayıcı anahtarını ve SIP yönlendirmesini kontrol edin.",
      sideband_failed:
        "Çağrı bağlantısı beklenmedik biçimde kesildi. Sağlayıcı ve sunucu bağlantısını kontrol edin.",
    };
    return t(known[code] || fallback || "Bağlantı kurulamadı.");
  }
  async function loadLive() {
    if (!context?.tenantId) return;
    try {
      const data = await request("/api/live-calls" + tenantQuery());
      const active = $("#active-call-list"),
        failures = $("#failed-call-list");
      active.replaceChildren();
      failures.replaceChildren();
      for (const call of data.active || [])
        active.append(
          lineCard(
            `${t("Çağrı")} ${call.call_id}`,
            `${t("Başlangıç")}: ${formatTime(call.started_at)}`,
            "active",
          ),
        );
      for (const call of data.failures || [])
        failures.append(
          lineCard(
            `${t("Çağrı")} ${call.call_id}`,
            `${failureMessage(call.failure_code, call.failure_message)} · ${formatTime(call.ended_at)}`,
            "failed",
          ),
        );
      if (!active.childElementCount)
        active.append(
          lineCard(
            t("Aktif çağrı yok."),
            t("Yeni gelen çağrılar burada görünür."),
          ),
        );
      if (!failures.childElementCount)
        failures.append(
          lineCard(
            t("Son hata yok."),
            t("Başarısız bağlantı kaydı bulunmuyor."),
          ),
        );
      const signature = JSON.stringify([
        ...(data.active || []).map((x) => x.call_id),
        ...(data.failures || []).map((x) => x.call_id),
      ]);
      if (signature !== lastLiveSignature) {
        status(
          "#live-call-status",
          t("Canlı durum değişti: {0} aktif çağrı, {1} son hata.", {
            0: (data.active || []).length,
            1: (data.failures || []).length,
          }),
        );
        lastLiveSignature = signature;
      }
    } catch (error) {
      status("#live-call-status", error.message);
    }
  }
  function csvCell(value) {
    const text = String(value ?? "");
    return `"${text.replaceAll('"', '""')}"`;
  }
  function downloadCsv(rows, name) {
    const csv =
      "\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }
  function usageQuery() {
    const query = new URLSearchParams();
    if (context?.role === "admin" && $("#usage-tenant")?.value)
      query.set("tenant_id", $("#usage-tenant").value);
    const from = $("#usage-date-from")?.value,
      to = $("#usage-date-to")?.value;
    if (from) query.set("date_from", from);
    if (to) query.set("date_to", to);
    return query.toString() ? `?${query}` : "";
  }
  function renderUsage(data) {
    latestUsage = data;
    const daily = $("#usage-daily-body"),
      tenants = $("#usage-tenant-body");
    daily.replaceChildren();
    tenants.replaceChildren();
    const money = (value) =>
      value == null
        ? t("Ölçüm yok")
        : root.OIMI18n.number(value, {
            minimumFractionDigits: 4,
            maximumFractionDigits: 4,
          });
    const credits = (value) =>
      root.OIMI18n.number(value || 0, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    const makeRow = (values) => {
      const tr = document.createElement("tr");
      for (const value of values) {
        const td = document.createElement("td");
        td.textContent = String(value);
        tr.append(td);
      }
      return tr;
    };
    for (const row of data.daily || [])
      daily.append(
        makeRow([
          row.day,
          row.calls,
          credits(row.billed_credits),
          money(row.estimated_openai_usd),
          row.total_tokens,
        ]),
      );
    if (!daily.childElementCount)
      daily.append(
        makeRow([t("Veri yok"), "0", credits(0), t("Ölçüm yok"), "0"]),
      );
    for (const row of data.tenants || [])
      tenants.append(
        makeRow([
          row.tenant_name,
          row.calls,
          credits(row.billed_credits),
          money(row.estimated_openai_usd),
        ]),
      );
    const all = data.daily || [];
    const calls = all.reduce((sum, row) => sum + Number(row.calls || 0), 0);
    const tokens = all.reduce(
      (sum, row) => sum + Number(row.total_tokens || 0),
      0,
    );
    const metered = all.reduce(
      (sum, row) => sum + Number(row.metered_calls || 0),
      0,
    );
    const cost = all.reduce(
      (sum, row) => sum + Number(row.estimated_openai_usd || 0),
      0,
    );
    $("#usage-openai-usd").textContent = metered ? money(cost) : t("Ölçüm yok");
    $("#usage-total-tokens").textContent = root.OIMI18n.number(tokens);
    $("#usage-metered-calls").textContent = root.OIMI18n.number(metered);
    status(
      "#usage-status",
      t(
        "{0}–{1} UTC · {2} çağrı · Tahmin yalnızca ölçüm kaydı bulunan çağrıları kapsar.",
        { 0: data.filters.date_from, 1: data.filters.date_to, 2: calls },
      ),
    );
  }
  async function loadUsage() {
    try {
      renderUsage(await request("/api/usage-report" + usageQuery()));
    } catch (error) {
      status("#usage-status", error.message);
    }
  }
  async function loadCallbacks() {
    if (!context?.tenantId) return;
    try {
      const data = await request("/api/callbacks" + tenantQuery());
      const body = $("#callbacks-body");
      body.replaceChildren();
      for (const item of data.items || []) {
        const row = document.createElement("tr");
        for (const value of [
          formatTime(item.created_at),
          item.phone,
          item.reason || "—",
          item.status === "completed" ? t("Tamamlandı") : t("Bekliyor"),
        ]) {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.append(cell);
        }
        const actionCell = document.createElement("td");
        if (item.status === "pending") {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "button outline";
          button.textContent = t("Tamamlandı olarak işaretle");
          button.addEventListener("click", async () => {
            button.disabled = true;
            status("#callbacks-status", t("Kaydediliyor…"));
            try {
              await request(`/api/callbacks/${item.id}/complete`, {
                method: "POST",
                body: JSON.stringify(
                  context.role === "admin"
                    ? { tenant_id: context.tenantId }
                    : {},
                ),
              });
              status(
                "#callbacks-status",
                t("Geri arama tamamlandı olarak kaydedildi."),
              );
              await loadCallbacks();
            } catch (error) {
              status("#callbacks-status", error.message);
              button.disabled = false;
            }
          });
          actionCell.append(button);
        } else actionCell.textContent = "—";
        row.append(actionCell);
        body.append(row);
      }
      if (!body.childElementCount) {
        const row = document.createElement("tr"),
          cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = t("Geri arama isteği yok.");
        row.append(cell);
        body.append(row);
      }
      status(
        "#callbacks-status",
        t("{0} geri arama isteği yüklendi.", { 0: data.items.length }),
      );
    } catch (error) {
      status("#callbacks-status", error.message);
    }
  }
  async function loadRetention() {
    if (!context?.tenantId) return;
    try {
      const data = await request("/api/privacy" + tenantQuery());
      const value =
        data.transcript_retention_days == null
          ? ""
          : String(data.transcript_retention_days);
      const select = $("#retention-days");
      if (
        value &&
        ![...select.options].some((option) => option.value === value)
      )
        select.append(new Option(t("{0} gün", { 0: value }), value));
      select.value = value;
      $("#retention-last-run").textContent = data.last_purged_at
        ? t("Son temizlik: {0}", { 0: formatTime(data.last_purged_at) })
        : t("Henüz zamanlanmış temizlik çalışmadı.");
    } catch (error) {
      status("#retention-status", error.message);
    }
  }
  async function loadAll() {
    const active = ++requestSequence;
    try {
      context = await getContext();
      if (active !== requestSequence) return;
      fillUsageTenants();
      await Promise.allSettled([
        loadReadiness(active),
        loadUsage(),
        loadCallbacks(),
        loadRetention(),
        loadLive(),
      ]);
    } catch (error) {
      status("#readiness-checks", error.message);
      status("#usage-status", error.message);
    }
  }

  $("#greeting-preview-speak")?.addEventListener("click", () => {
    const text = $("#greeting-preview")?.textContent?.trim();
    if (!text || !root.speechSynthesis || !root.SpeechSynthesisUtterance) {
      status(
        "#live-call-status",
        t("Tarayıcıda sesli ön izleme desteklenmiyor."),
      );
      return;
    }
    root.speechSynthesis.cancel();
    root.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  });
  $("#live-refresh")?.addEventListener("click", loadLive);
  $("#callbacks-refresh")?.addEventListener("click", loadCallbacks);
  $("#usage-refresh")?.addEventListener("click", loadUsage);
  $("#usage-tenant")?.addEventListener("change", loadUsage);
  $("#usage-export")?.addEventListener("click", () => {
    if (!latestUsage) return;
    const rows = [
      [
        t("TARİH (UTC)"),
        t("ÇAĞRI"),
        t("KULLANILAN KREDİ"),
        t("OPENAI TAHMİNİ (USD)"),
        t("TOKEN"),
      ],
      ...(latestUsage.daily || []).map((x) => [
        x.day,
        x.calls,
        x.billed_credits,
        x.estimated_openai_usd ?? "",
        x.total_tokens,
      ]),
    ];
    downloadCsv(
      rows,
      `usage-${latestUsage.filters.date_from}-${latestUsage.filters.date_to}.csv`,
    );
  });
  $("#retention-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await request("/api/privacy", {
        method: "POST",
        body: JSON.stringify({
          transcript_retention_days: $("#retention-days").value || null,
          ...(context.role === "admin" ? { tenant_id: context.tenantId } : {}),
        }),
      });
      status("#retention-status", t("Saklama ayarı kaydedildi."));
      await loadRetention();
    } catch (error) {
      status("#retention-status", error.message);
    } finally {
      button.disabled = false;
    }
  });
  $("#dashboard-tenant")?.addEventListener("change", loadAll);
  document
    .querySelectorAll(
      '.nav-item[data-view="live-monitoring"],.nav-item[data-view="callbacks"],.nav-item[data-view="usage-costs"],.nav-item[data-view="privacy"]',
    )
    .forEach((link) =>
      link.addEventListener("click", () =>
        setTimeout(() => {
          if (link.dataset.view === "live-monitoring") loadLive();
          if (link.dataset.view === "callbacks") loadCallbacks();
          if (link.dataset.view === "usage-costs") loadUsage();
          if (link.dataset.view === "privacy") loadRetention();
        }, 0),
      ),
    );
  root.addEventListener("oim:localechange", () => {
    if (context) loadAll();
  });
  root.addEventListener("oim:ai-settings-updated", () => {
    if (context) loadReadiness(requestSequence);
  });
  setInterval(() => {
    if (location.hash === "#live-monitoring") loadLive();
  }, 15000);
  loadAll();
})(window);
